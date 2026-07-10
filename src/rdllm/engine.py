"""Royalty attribution engine for LLM generation events."""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import replace
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from rdllm.attribution_gap import (
    evaluate_attribution_gap,
    verify_attribution_gap_report,
)
from rdllm.claim_warrant import claim_warrant_report
from rdllm.grounding import evaluate_event_grounding_quality, evaluate_grounding_quality
from rdllm.matching import TextAttributor
from rdllm.models import (
    Chunk,
    ClaimSupport,
    Creator,
    RetrievalHit,
    RoyaltyShare,
    SourceAccess,
    SourceReference,
    TextMatch,
    UsageEvent,
    Work,
)
from rdllm.policy import RightsPolicyEngine
from rdllm.registry import (
    OwnershipAttestation,
    conflicts_by_work_id,
    load_attestations,
    registry_report_for_works,
)
from rdllm.source_disagreement import claim_source_disagreement_report
from rdllm.text import (
    chunk_text,
    cosine_similarity,
    jaccard_similarity,
    longest_common_token_sequence,
    split_sentences,
    stable_hash,
    term_counts,
    tokenize,
)
from rdllm.valuation import exact_shapley_values

MONEY_QUANT = Decimal("0.000001")
EXTERNAL_RETRIEVAL_RELEVANCE_FLOOR = 0.15
FOOTER_VERIFIED_SUPPORT_FLOOR = 0.75
CLAIM_SUPPORT_FLOOR = FOOTER_VERIFIED_SUPPORT_FLOOR


def _label_list(values: list[Any]) -> str:
    labels = sorted({str(value) for value in values if str(value)})
    return ",".join(labels) if labels else "none"


class RoyaltyDrivenLLM:
    """A model-agnostic attribution layer for royalty-bearing generation."""

    def __init__(
        self,
        creators: list[Creator],
        works: list[Work],
        creator_pool_rate: Decimal | str | float = Decimal("0.55"),
        top_k: int = 3,
        jurisdiction: str = "GLOBAL",
        attestations: list[OwnershipAttestation] | None = None,
        registry_report: dict[str, Any] | None = None,
        enforce_registry: bool = False,
    ) -> None:
        self.creators = {creator.creator_id: creator for creator in creators}
        self.works = {work.work_id: work for work in works}
        self.creator_pool_rate = Decimal(str(creator_pool_rate))
        self.top_k = top_k
        self.jurisdiction = jurisdiction
        self.attestations = attestations or []
        self.registry_report = registry_report or registry_report_for_works(
            works, attestations=self.attestations
        )
        self.enforce_registry = enforce_registry
        self.registry_conflicts_by_work_id = (
            conflicts_by_work_id(self.registry_report) if enforce_registry else {}
        )
        self.policy_engine = RightsPolicyEngine(default_jurisdiction=jurisdiction)
        self.chunks = self._build_chunks(works)
        self.chunk_by_id = {chunk.chunk_id: chunk for chunk in self.chunks}
        self.idf = self._build_idf(self.chunks)
        self.chunk_vectors = {
            chunk.chunk_id: self._tfidf_vector(tokenize(chunk.text)) for chunk in self.chunks
        }
        self.text_attributor = TextAttributor(self.chunks)
        self.training_value_priors = self.estimate_training_values(
            self._default_benchmark_prompts()
        )

    @classmethod
    def from_corpus_file(
        cls,
        path: str | Path,
        creator_pool_rate: Decimal | str | float = Decimal("0.55"),
        top_k: int = 3,
        jurisdiction: str = "GLOBAL",
        attestations_path: str | Path | None = None,
        registry_report_path: str | Path | None = None,
        enforce_registry: bool = False,
    ) -> "RoyaltyDrivenLLM":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        creators = [Creator.from_dict(item) for item in data["creators"]]
        works = [Work.from_dict(item) for item in data["works"]]
        attestations = [
            OwnershipAttestation.from_dict(item)
            for item in data.get("attestations", [])
        ]
        attestations.extend(load_attestations(attestations_path))
        registry_report = (
            json.loads(Path(registry_report_path).read_text(encoding="utf-8"))
            if registry_report_path
            else None
        )
        return cls(
            creators,
            works,
            creator_pool_rate=creator_pool_rate,
            top_k=top_k,
            jurisdiction=jurisdiction,
            attestations=attestations,
            registry_report=registry_report,
            enforce_registry=enforce_registry,
        )

    def retrieve(
        self,
        prompt: str,
        top_k: int | None = None,
        *,
        use: str = "retrieval",
    ) -> list[RetrievalHit]:
        query_vector = self._tfidf_vector(tokenize(prompt))
        hits: list[RetrievalHit] = []

        candidate_chunks = self.policy_engine.allowed_chunks(
            self.chunks,
            use,
            jurisdiction=self.jurisdiction,
            creator_pool_rate=self.creator_pool_rate,
        )
        for chunk in candidate_chunks:
            score = cosine_similarity(query_vector, self.chunk_vectors[chunk.chunk_id])
            if score > 0:
                hits.append(RetrievalHit(chunk=chunk, score=score, rank=0))

        hits.sort(key=lambda hit: hit.score, reverse=True)
        limit = top_k or self.top_k
        return [
            RetrievalHit(chunk=hit.chunk, score=hit.score, rank=index + 1)
            for index, hit in enumerate(hits[:limit])
        ]

    def generate(self, prompt: str, gross_revenue: Decimal | str | float) -> UsageEvent:
        hits = self.retrieve(prompt, use="retrieval")
        output = self._compose_answer(prompt, hits)
        return self._build_event(
            prompt,
            output,
            gross_revenue,
            hits,
            text_use="generation",
            generation_evidence=self._generation_evidence(
                "internal_retrieval",
                hits,
                pre_generation_context_bound=True,
            ),
        )

    def attribute_text(
        self,
        prompt: str,
        output: str,
        gross_revenue: Decimal | str | float,
    ) -> UsageEvent:
        """Attribute an externally generated text output to registered owners."""

        hits = self._external_source_hits(output)
        return self._build_event(
            prompt,
            output,
            gross_revenue,
            hits,
            text_use="external_attribution",
            generation_evidence=self._generation_evidence(
                "post_hoc_observable_match",
                hits,
                pre_generation_context_bound=False,
            ),
        )

    def attribute_grounded_text(
        self,
        prompt: str,
        output: str,
        gross_revenue: Decimal | str | float,
        hits: list[RetrievalHit],
        *,
        provider_evidence: dict[str, Any],
    ) -> UsageEvent:
        """Attribute output to sources bound into the provider context before generation."""

        evidence = self._generation_evidence(
            "provider_context_grounded",
            hits,
            pre_generation_context_bound=True,
        )
        evidence.update(provider_evidence)
        return self._build_event(
            prompt,
            output,
            gross_revenue,
            hits,
            text_use="generation",
            generation_evidence=evidence,
        )

    def _external_source_hits(self, output: str) -> list[RetrievalHit]:
        """Find candidate sources from generated text, not from prompt intent alone."""

        text_matches = self.match_text(output, use="external_attribution")
        matched_chunk_ids = {match.chunk.chunk_id for match in text_matches}
        return [
            hit
            for hit in self.retrieve(output, use="retrieval")
            if hit.score >= EXTERNAL_RETRIEVAL_RELEVANCE_FLOOR
            or hit.chunk.chunk_id in matched_chunk_ids
        ]

    def _attribution_hits(
        self,
        hits: list[RetrievalHit],
        generation_evidence: dict[str, Any],
    ) -> list[RetrievalHit]:
        if generation_evidence.get("mode") != "provider_context_grounded":
            return hits
        cited = {
            int(source_id[1:])
            for source_id in generation_evidence.get("grounding_source_ids", [])
            if isinstance(source_id, str)
            and source_id.startswith("S")
            and source_id[1:].isdigit()
        }
        return [hit for index, hit in enumerate(hits, start=1) if index in cited]

    def match_text(
        self,
        output: str,
        limit: int | None = None,
        *,
        use: str = "external_attribution",
        include_blocked: bool = False,
    ) -> list[TextMatch]:
        matches = self.text_attributor.match(output, limit=None)
        if include_blocked:
            allowed_matches = matches
        else:
            allowed_matches = [
                match
                for match in matches
                if self.policy_engine.evaluate_chunk(
                    match.chunk,
                    use,
                    jurisdiction=self.jurisdiction,
                    creator_pool_rate=self.creator_pool_rate,
                ).allowed
            ]
        if limit is not None:
            allowed_matches = allowed_matches[:limit]
        return [
            TextMatch(
                chunk=match.chunk,
                score=match.score,
                rank=index + 1,
                exact_score=match.exact_score,
                ngram_score=match.ngram_score,
                longest_sequence_tokens=match.longest_sequence_tokens,
                matched_text=match.matched_text,
            )
            for index, match in enumerate(allowed_matches)
        ]

    def estimate_training_values(
        self, benchmark_prompts: list[str] | None = None
    ) -> dict[str, float]:
        prompts = benchmark_prompts or self._default_benchmark_prompts()

        def score_fn(prompt: str, subset: list[Chunk]) -> float:
            query_vector = self._tfidf_vector(tokenize(prompt))
            scores = [
                cosine_similarity(query_vector, self.chunk_vectors[chunk.chunk_id])
                for chunk in subset
            ]
            return sum(sorted(scores, reverse=True)[: self.top_k])

        training_chunks = self.policy_engine.allowed_chunks(
            self.chunks,
            "training",
            jurisdiction=self.jurisdiction,
            creator_pool_rate=self.creator_pool_rate,
        )
        values = exact_shapley_values(training_chunks, prompts, score_fn)
        return {
            chunk.chunk_id: values.get(chunk.chunk_id, 1.0) * chunk.data_value_prior
            for chunk in self.chunks
        }

    def _build_event(
        self,
        prompt: str,
        output: str,
        gross_revenue: Decimal | str | float,
        hits: list[RetrievalHit],
        text_use: str,
        generation_evidence: dict[str, Any] | None = None,
    ) -> UsageEvent:
        answer_text = output
        all_text_matches = self.match_text(
            answer_text,
            use=text_use,
            include_blocked=True,
        )
        policy_decisions = self._policy_decisions(hits, all_text_matches, text_use)
        registry_decisions = self._registry_decisions(hits, all_text_matches)
        source_accesses = self._source_accesses(
            hits,
            all_text_matches,
            text_use,
            policy_decisions,
            registry_decisions,
        )
        attribution_hits = self._attribution_hits(hits, generation_evidence or {})
        denied_match_ids = {
            decision["chunk_id"]
            for decision in policy_decisions
            if not decision["allowed"] and decision["use"] == text_use
        }
        text_matches = [
            match for match in all_text_matches if match.chunk.chunk_id not in denied_match_ids
        ]
        labels_by_chunk = self._source_labels(hits, text_matches)
        creator_pool = (
            Decimal(str(gross_revenue)) * self.creator_pool_rate
        ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        shares = self._allocate(
            prompt,
            answer_text,
            attribution_hits,
            text_matches,
            labels_by_chunk,
            creator_pool,
            policy_decisions,
            registry_decisions,
            text_use,
        )
        source_references = self._build_source_references(
            labels_by_chunk,
            hits,
            text_matches,
            shares,
            text_use,
            registry_decisions,
        )
        claim_support = self._claim_support(answer_text, source_references)
        if self._requires_evidence_escrow(
            claim_support,
            source_references,
            shares,
            policy_decisions,
            registry_decisions,
        ):
            shares = [self._escrow_share(creator_pool)] if creator_pool else []
            source_references = self._build_source_references(
                labels_by_chunk,
                hits,
                text_matches,
                shares,
                text_use,
                registry_decisions,
            )
        source_references = self._attach_evidence_spans(source_references, claim_support)
        grounding_report = self._grounding_report(
            claim_support,
            source_references,
            policy_decisions,
            registry_decisions,
        )
        rendered_output = self._render_grounded_output(
            answer_text, source_references, claim_support, grounding_report
        )
        grounding_quality = evaluate_grounding_quality(
            output=rendered_output,
            sources=source_references,
            claims=claim_support,
            grounding_report=grounding_report,
            policy_decisions=policy_decisions,
            royalty_shares=shares,
        )
        attribution_gap = evaluate_attribution_gap(
            source_accesses=source_accesses,
            source_references=source_references,
            royalty_shares=shares,
            grounding_report=grounding_report,
        )
        bound_generation_evidence = generation_evidence or {}
        settlement_decision = self._settlement_decision(
            generation_evidence=bound_generation_evidence,
            claim_support=claim_support,
            grounding_quality=grounding_quality,
            shares=shares,
        )
        event_hash = self._event_hash(
            prompt,
            answer_text,
            rendered_output,
            gross_revenue,
            creator_pool,
            shares,
            source_references,
            claim_support,
            grounding_report,
            grounding_quality,
            attribution_gap,
            bound_generation_evidence,
            settlement_decision,
            policy_decisions,
            registry_decisions,
        )
        event_id = f"evt_{event_hash[:16]}"
        return UsageEvent(
            event_id=event_id,
            event_hash=event_hash,
            prompt=prompt,
            output=rendered_output,
            gross_revenue=Decimal(str(gross_revenue)).quantize(
                MONEY_QUANT, rounding=ROUND_HALF_UP
            ),
            creator_pool_rate=self.creator_pool_rate,
            creator_pool=creator_pool,
            retrieval_hits=hits,
            text_matches=text_matches,
            royalty_shares=shares,
            answer_text=answer_text,
            source_accesses=source_accesses,
            source_references=source_references,
            claim_support=claim_support,
            grounding_report=grounding_report,
            grounding_quality=grounding_quality,
            attribution_gap=attribution_gap,
            generation_evidence=bound_generation_evidence,
            settlement_decision=settlement_decision,
            policy_decisions=policy_decisions,
            registry_decisions=registry_decisions,
        )

    def audit_event(self, event: UsageEvent) -> list[str]:
        errors: list[str] = []
        payout_total = sum((share.payout for share in event.royalty_shares), Decimal("0"))
        if payout_total != event.creator_pool:
            errors.append(
                f"payout_total {payout_total} does not equal creator_pool {event.creator_pool}"
            )

        weight_total = sum(
            (share.contribution_weight for share in event.royalty_shares), Decimal("0")
        )
        if event.royalty_shares and abs(weight_total - Decimal("1")) > Decimal("0.00001"):
            errors.append(f"contribution weights sum to {weight_total}, not 1")

        for share in event.royalty_shares:
            if share.chunk_id.startswith("escrow:"):
                continue
            chunk = self.chunk_by_id.get(share.chunk_id)
            if chunk is None:
                errors.append(f"missing chunk {share.chunk_id}")
            elif chunk.content_hash != share.content_hash:
                errors.append(f"hash mismatch for chunk {share.chunk_id}")

        for reference in event.source_references:
            chunk = self.chunk_by_id.get(reference.chunk_id)
            if chunk is None:
                errors.append(f"missing source reference chunk {reference.chunk_id}")
            elif chunk.content_hash != reference.content_hash:
                errors.append(f"source reference hash mismatch for {reference.chunk_id}")

        for support in event.claim_support:
            if not support.supported:
                continue
            chunk = self.chunk_by_id.get(support.chunk_id)
            if chunk is None:
                errors.append(f"missing claim support chunk {support.chunk_id}")
                continue
            if support.evidence_text not in chunk.text:
                errors.append(f"claim evidence text missing from {support.chunk_id}")
            if stable_hash(support.evidence_text) != support.evidence_span_hash:
                errors.append(
                    f"claim evidence span hash mismatch for {support.chunk_id}"
                )

        expected_quality = evaluate_event_grounding_quality(event)
        if expected_quality != event.grounding_quality:
            errors.append("grounding quality report is not reproducible")

        errors.extend(verify_attribution_gap_report(event))

        if (
            event.grounding_report.get("registry_status") == "disputed"
            and not event.registry_decisions
        ):
            errors.append("registry-disputed event has no registry decisions")
        for decision in event.registry_decisions:
            if decision.get("registry_report_hash") != self.registry_report.get(
                "report_hash"
            ):
                errors.append("registry decision report hash does not match current registry")
            conflict_id = decision.get("conflict_id", "")
            work_id = decision.get("work_id", "")
            conflicts = self.registry_conflicts_by_work_id.get(work_id, [])
            if not any(
                conflict.get("conflict_id") == conflict_id for conflict in conflicts
            ):
                errors.append(
                    f"registry decision conflict {conflict_id} is not reproducible"
                )

        expected_hash = self._event_hash(
            event.prompt,
            event.answer_text or event.output,
            event.output,
            event.gross_revenue,
            event.creator_pool,
            event.royalty_shares,
            event.source_references,
            event.claim_support,
            event.grounding_report,
            event.grounding_quality,
            event.attribution_gap,
            event.generation_evidence,
            event.settlement_decision,
            event.policy_decisions,
            event.registry_decisions,
        )
        if expected_hash != event.event_hash:
            errors.append("event hash is not reproducible")
        return errors

    def _build_chunks(self, works: list[Work]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for work in works:
            if work.creator_id not in self.creators:
                raise ValueError(f"work {work.work_id} has unknown creator {work.creator_id}")
            for index, text in enumerate(chunk_text(work.content), start=1):
                chunk_id = f"{work.work_id}:c{index}"
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        work_id=work.work_id,
                        creator_id=work.creator_id,
                        title=work.title,
                        text=text,
                        content_hash=stable_hash(text),
                        license=work.license,
                        data_value_prior=work.data_value_prior,
                        source_uri=work.source_uri
                        or f"registered://works/{work.work_id}#{chunk_id}",
                        policy_id=work.policy_id or f"policy:{work.work_id}",
                        license_uri=work.license_uri,
                        allowed_uses=work.allowed_uses,
                        prohibited_uses=work.prohibited_uses,
                        jurisdictions=work.jurisdictions,
                        requires_attribution=work.requires_attribution,
                        requires_royalty=work.requires_royalty,
                        minimum_creator_pool_rate=work.minimum_creator_pool_rate,
                        revoked=work.revoked,
                        revoked_at=work.revoked_at,
                    )
                )
        return chunks

    def _policy_decisions(
        self,
        hits: list[RetrievalHit],
        text_matches: list[TextMatch],
        text_use: str,
    ) -> list[dict[str, Any]]:
        decisions: dict[tuple[str, str], dict[str, Any]] = {}
        for hit in hits:
            decision = self.policy_engine.evaluate_chunk(
                hit.chunk,
                "retrieval",
                jurisdiction=self.jurisdiction,
                creator_pool_rate=self.creator_pool_rate,
            ).to_dict()
            decisions[(decision["chunk_id"], decision["use"])] = decision
        for match in text_matches:
            decision = self.policy_engine.evaluate_chunk(
                match.chunk,
                text_use,
                jurisdiction=self.jurisdiction,
                creator_pool_rate=self.creator_pool_rate,
            ).to_dict()
            decision["text_match_score"] = round(match.score, 8)
            decisions[(decision["chunk_id"], decision["use"])] = decision
        return [
            decisions[key]
            for key in sorted(decisions, key=lambda item: (item[0], item[1]))
        ]

    def _registry_decisions(
        self,
        hits: list[RetrievalHit],
        text_matches: list[TextMatch],
    ) -> list[dict[str, Any]]:
        if not self.enforce_registry:
            return []

        decisions: dict[tuple[str, str], dict[str, Any]] = {}
        chunks = [hit.chunk for hit in hits] + [match.chunk for match in text_matches]
        for chunk in chunks:
            for conflict in self.registry_conflicts_by_work_id.get(chunk.work_id, []):
                decision = {
                    "allowed": False,
                    "action": "escrow",
                    "escrow_account": "registry_dispute_escrow",
                    "reason": "registered work has an open ownership claim conflict",
                    "registry_report_version": self.registry_report.get(
                        "registry_report_version"
                    ),
                    "registry_report_hash": self.registry_report.get("report_hash"),
                    "conflict_id": conflict.get("conflict_id", ""),
                    "conflict_type": conflict.get("conflict_type", ""),
                    "conflict_score": conflict.get("score", 0.0),
                    "conflicted_work_ids": list(conflict.get("work_ids", [])),
                    "work_id": chunk.work_id,
                    "chunk_id": chunk.chunk_id,
                    "creator_id": chunk.creator_id,
                    "content_hash": chunk.content_hash,
                }
                decisions[(chunk.chunk_id, decision["conflict_id"])] = decision
        return [
            decisions[key]
            for key in sorted(decisions, key=lambda item: (item[0], item[1]))
        ]

    def _source_accesses(
        self,
        hits: list[RetrievalHit],
        text_matches: list[TextMatch],
        text_use: str,
        policy_decisions: list[dict[str, Any]],
        registry_decisions: list[dict[str, Any]],
    ) -> list[SourceAccess]:
        policy_by_chunk_use = {
            (decision["chunk_id"], decision["use"]): decision
            for decision in policy_decisions
        }
        registry_blocked_chunks = {
            decision["chunk_id"]
            for decision in registry_decisions
            if not decision.get("allowed", True)
        }
        accesses: list[SourceAccess] = []
        for hit in hits:
            decision = policy_by_chunk_use.get((hit.chunk.chunk_id, "retrieval"), {})
            accesses.append(
                self._source_access(
                    access_type="retrieval",
                    use="retrieval",
                    chunk=hit.chunk,
                    score=hit.score,
                    rank=hit.rank,
                    policy_allowed=bool(decision.get("allowed", True)),
                    registry_allowed=hit.chunk.chunk_id not in registry_blocked_chunks,
                )
            )
        for match in text_matches:
            decision = policy_by_chunk_use.get((match.chunk.chunk_id, text_use), {})
            accesses.append(
                self._source_access(
                    access_type="text_match",
                    use=text_use,
                    chunk=match.chunk,
                    score=match.score,
                    rank=match.rank,
                    policy_allowed=bool(decision.get("allowed", True)),
                    registry_allowed=match.chunk.chunk_id not in registry_blocked_chunks,
                    matched_text=match.matched_text,
                )
            )
        return sorted(
            accesses,
            key=lambda access: (
                access.chunk_id,
                access.access_type,
                access.use,
                access.rank,
            ),
        )

    def _source_access(
        self,
        *,
        access_type: str,
        use: str,
        chunk: Chunk,
        score: float,
        rank: int,
        policy_allowed: bool,
        registry_allowed: bool,
        matched_text: str = "",
    ) -> SourceAccess:
        if not policy_allowed:
            status = "blocked_by_policy"
        elif not registry_allowed:
            status = "blocked_by_registry"
        else:
            status = "allowed"
        seed = (
            f"{access_type}:{use}:{chunk.chunk_id}:{rank}:"
            f"{score:.8f}:{chunk.content_hash}"
        )
        return SourceAccess(
            access_id=f"srcacc_{stable_hash(seed)[:16]}",
            access_type=access_type,
            use=use,
            chunk_id=chunk.chunk_id,
            work_id=chunk.work_id,
            creator_id=chunk.creator_id,
            title=chunk.title,
            source_uri=chunk.source_uri,
            content_hash=chunk.content_hash,
            score=score,
            rank=rank,
            policy_allowed=policy_allowed,
            registry_allowed=registry_allowed,
            decision_status=status,
            matched_text_hash=stable_hash(matched_text) if matched_text else "",
        )

    def _build_idf(self, chunks: list[Chunk]) -> dict[str, float]:
        document_frequency: Counter[str] = Counter()
        for chunk in chunks:
            document_frequency.update(set(tokenize(chunk.text)))

        total = len(chunks)
        return {
            token: math.log((1 + total) / (1 + count)) + 1
            for token, count in document_frequency.items()
        }

    def _tfidf_vector(self, tokens: list[str]) -> dict[str, float]:
        counts = term_counts(tokens)
        if not counts:
            return {}
        total = sum(counts.values())
        return {
            token: (count / total) * self.idf.get(token, 1.0)
            for token, count in counts.items()
        }

    def _default_benchmark_prompts(self) -> list[str]:
        prompts: list[str] = []
        for work in self.works.values():
            prompts.append(work.title)
            prompts.append(chunk_text(work.content, max_tokens=28)[0])
        return prompts

    def _compose_answer(self, prompt: str, hits: list[RetrievalHit]) -> str:
        if not hits:
            return (
                "No royalty-bearing registered source was retrieved for this prompt, "
                "so no creator payout was allocated."
            )

        parts = [
            "Royalty-aware answer:",
            "The strongest registered sources say:",
        ]
        for hit in hits:
            sentence = chunk_text(hit.chunk.text, max_tokens=35)[0]
            parts.append(f"- {sentence} [S{hit.rank}]")
        return "\n".join(parts)

    def _allocate(
        self,
        prompt: str,
        output: str,
        hits: list[RetrievalHit],
        text_matches: list[TextMatch],
        labels_by_chunk: dict[str, str],
        creator_pool: Decimal,
        policy_decisions: list[dict[str, Any]],
        registry_decisions: list[dict[str, Any]],
        text_use: str,
    ) -> list[RoyaltyShare]:
        if creator_pool == Decimal("0"):
            return []
        denied_text_matches = [
            decision
            for decision in policy_decisions
            if not decision["allowed"]
            and decision["use"] in {"generation", "external_attribution"}
            and float(decision.get("text_match_score", 0.0)) >= 0.08
        ]
        if denied_text_matches:
            return [self._rights_conflict_share(creator_pool)]

        registry_blocks = [
            decision for decision in registry_decisions if not decision.get("allowed", True)
        ]
        if registry_blocks:
            return [self._registry_dispute_share(creator_pool)]

        output_tokens = tokenize(output)
        prompt_tokens = tokenize(prompt)
        retrieval_by_chunk = {hit.chunk.chunk_id: hit for hit in hits}
        text_match_by_chunk = {match.chunk.chunk_id: match for match in text_matches}
        candidate_ids = set(retrieval_by_chunk) | set(text_match_by_chunk)

        raw_scores: list[tuple[Chunk, float, dict[str, float]]] = []
        for chunk_id in sorted(candidate_ids):
            chunk = self.chunk_by_id[chunk_id]
            hit = retrieval_by_chunk.get(chunk_id)
            text_match = text_match_by_chunk.get(chunk_id)
            chunk_tokens = tokenize(chunk.text)
            retrieval_score = hit.score if hit else 0.0
            text_match_score = text_match.score if text_match else 0.0
            citation_score = self._citation_score(
                output, chunk, labels_by_chunk.get(chunk.chunk_id, "")
            )
            query_relevance = jaccard_similarity(prompt_tokens, chunk_tokens)
            output_support = jaccard_similarity(output_tokens, chunk_tokens)
            if (
                text_use == "external_attribution"
                and text_match_score < 0.08
                and output_support < EXTERNAL_RETRIEVAL_RELEVANCE_FLOOR
                and citation_score == 0.0
            ):
                continue
            training_value_score = self.training_value_priors.get(
                chunk.chunk_id, chunk.data_value_prior
            )
            attribution_basis = {
                "retrieval": retrieval_score,
                "output_support": output_support,
                "prompt_overlap": query_relevance,
                "text_match": text_match_score,
                "citation": citation_score,
                "training_value": training_value_score,
            }
            raw = (
                0.15 * retrieval_score
                + 0.15 * output_support
                + 0.05 * query_relevance
                + 0.55 * text_match_score
                + 0.10 * citation_score
            ) * max(training_value_score, 0.05)
            if raw > 0:
                raw_scores.append((chunk, raw, attribution_basis))

        total_raw = sum(raw for _, raw, _ in raw_scores)
        if total_raw <= 0:
            return [self._escrow_share(creator_pool)]

        shares: list[RoyaltyShare] = []
        paid_so_far = Decimal("0")

        for index, (chunk, raw, basis) in enumerate(raw_scores):
            if index == len(raw_scores) - 1:
                payout = creator_pool - paid_so_far
                weight = Decimal("1") - sum(
                    (share.contribution_weight for share in shares), Decimal("0")
                )
            else:
                weight = Decimal(str(raw / total_raw)).quantize(
                    MONEY_QUANT, rounding=ROUND_HALF_UP
                )
                payout = (creator_pool * weight).quantize(
                    MONEY_QUANT, rounding=ROUND_HALF_UP
                )
                paid_so_far += payout

            shares.append(
                RoyaltyShare(
                    creator_id=chunk.creator_id,
                    work_id=chunk.work_id,
                    chunk_id=chunk.chunk_id,
                    contribution_weight=weight,
                    payout=payout,
                    query_relevance=basis["prompt_overlap"],
                    output_support=basis["output_support"],
                    data_value_prior=chunk.data_value_prior,
                    content_hash=chunk.content_hash,
                    retrieval_score=basis["retrieval"],
                    text_match_score=basis["text_match"],
                    citation_score=basis["citation"],
                    training_value_score=basis["training_value"],
                    attribution_basis=basis,
                )
            )

        return shares

    def _source_labels(
        self, hits: list[RetrievalHit], text_matches: list[TextMatch]
    ) -> dict[str, str]:
        labels: dict[str, str] = {}
        for hit in hits:
            labels[hit.chunk.chunk_id] = f"S{len(labels) + 1}"
        for match in text_matches:
            if match.chunk.chunk_id not in labels:
                labels[match.chunk.chunk_id] = f"S{len(labels) + 1}"
        return labels

    def _citation_score(self, output: str, chunk: Chunk, label: str) -> float:
        if label and f"[{label}]" in output:
            return 1.0
        if f"[{chunk.chunk_id}]" in output or f"[{chunk.work_id}]" in output:
            return 1.0
        return 0.0

    def _build_source_references(
        self,
        labels_by_chunk: dict[str, str],
        hits: list[RetrievalHit],
        text_matches: list[TextMatch],
        shares: list[RoyaltyShare],
        policy_use: str,
        registry_decisions: list[dict[str, Any]],
    ) -> list[SourceReference]:
        hit_by_chunk = {hit.chunk.chunk_id: hit for hit in hits}
        match_by_chunk = {match.chunk.chunk_id: match for match in text_matches}
        share_by_chunk = {share.chunk_id: share for share in shares}
        registry_blocked_chunks = {
            decision["chunk_id"]
            for decision in registry_decisions
            if not decision.get("allowed", True)
        }
        references: list[SourceReference] = []

        for chunk_id, label in sorted(
            labels_by_chunk.items(), key=lambda item: int(item[1].removeprefix("S"))
        ):
            if chunk_id in registry_blocked_chunks:
                continue
            chunk = self.chunk_by_id[chunk_id]
            if not self.policy_engine.evaluate_chunk(
                chunk,
                policy_use,
                jurisdiction=self.jurisdiction,
                creator_pool_rate=self.creator_pool_rate,
            ).allowed:
                continue
            creator = self.creators[chunk.creator_id]
            hit = hit_by_chunk.get(chunk_id)
            match = match_by_chunk.get(chunk_id)
            share = share_by_chunk.get(chunk_id)
            if policy_use == "external_attribution":
                source_is_supported_by_output = bool(match) or (
                    share is not None and self._is_user_visible_source(share)
                )
                if not source_is_supported_by_output:
                    continue
            elif share and not self._is_user_visible_source(share):
                continue
            references.append(
                SourceReference(
                    label=label,
                    creator_id=chunk.creator_id,
                    creator_name=creator.name,
                    work_id=chunk.work_id,
                    chunk_id=chunk.chunk_id,
                    title=chunk.title,
                    source_uri=chunk.source_uri,
                    license=chunk.license,
                    policy_id=chunk.policy_id,
                    policy_use=policy_use,
                    jurisdiction=self.jurisdiction,
                    license_uri=chunk.license_uri,
                    quote=chunk_text(chunk.text, max_tokens=32)[0],
                    content_hash=chunk.content_hash,
                    retrieval_score=hit.score if hit else 0.0,
                    text_match_score=match.score if match else 0.0,
                    output_support=share.output_support if share else 0.0,
                    citation_score=share.citation_score if share else 0.0,
                    contribution_weight=share.contribution_weight if share else Decimal("0"),
                    payout=share.payout if share else Decimal("0"),
                )
            )

        return references

    def _is_user_visible_source(self, share: RoyaltyShare) -> bool:
        return (
            share.payout > Decimal("0")
            or share.citation_score > 0
            or share.text_match_score >= 0.08
            or share.output_support >= 0.15
        )

    def _claim_support(
        self, answer_text: str, references: list[SourceReference]
    ) -> list[ClaimSupport]:
        claims = self._extract_claims(answer_text)
        support: list[ClaimSupport] = []
        reference_chunks = [
            (reference, self.chunk_by_id[reference.chunk_id]) for reference in references
        ]

        for claim in claims:
            best_label = ""
            best_work_id = ""
            best_chunk_id = ""
            best_span = {
                "text": "",
                "span_hash": "",
                "start_char": -1,
                "end_char": -1,
            }
            best_score = 0.0
            claim_tokens = tokenize(claim)
            for reference, chunk in reference_chunks:
                span = self._best_evidence_span(claim, chunk)
                span_tokens = tokenize(span["text"])
                overlap = jaccard_similarity(claim_tokens, span_tokens)
                longest, _ = longest_common_token_sequence(claim_tokens, span_tokens)
                sequence_score = min(1.0, longest / max(6, len(claim_tokens)))
                citation_bonus = 0.2 if f"[{reference.label}]" in claim else 0.0
                score = min(1.0, 0.55 * overlap + 0.35 * sequence_score + citation_bonus)
                if score > best_score:
                    best_score = score
                    best_label = reference.label
                    best_work_id = reference.work_id
                    best_chunk_id = reference.chunk_id
                    best_span = span

            supported = best_score >= CLAIM_SUPPORT_FLOOR
            if supported:
                warrant = claim_warrant_report(
                    claim=claim,
                    evidence=best_span["text"],
                    supported=True,
                )
                disagreement = claim_source_disagreement_report(
                    claim=claim,
                    source_label=best_label,
                    source_rows=[
                        {
                            "label": best_label,
                            "evidence_preview": best_span["text"],
                        }
                    ],
                    supported=True,
                )
                supported = (
                    warrant["warrant_strength_status"] == "passed"
                    and disagreement["source_disagreement_status"] == "passed"
                )
            support.append(
                ClaimSupport(
                    claim=claim,
                    source_label=best_label,
                    support_score=best_score,
                    supported=supported,
                    work_id=best_work_id if supported else "",
                    chunk_id=best_chunk_id if supported else "",
                    evidence_text=best_span["text"] if supported else "",
                    evidence_span_hash=best_span["span_hash"] if supported else "",
                    evidence_start_char=best_span["start_char"] if supported else -1,
                    evidence_end_char=best_span["end_char"] if supported else -1,
                )
            )
        return support

    def _requires_evidence_escrow(
        self,
        claims: list[ClaimSupport],
        references: list[SourceReference],
        shares: list[RoyaltyShare],
        policy_decisions: list[dict[str, Any]],
        registry_decisions: list[dict[str, Any]],
    ) -> bool:
        if not shares or not references:
            return False
        if any(not decision.get("allowed", True) for decision in policy_decisions):
            return False
        if any(not decision.get("allowed", True) for decision in registry_decisions):
            return False
        source_shares = [share for share in shares if not share.chunk_id.startswith("escrow:")]
        return bool(source_shares) and (not claims or any(not claim.supported for claim in claims))

    def _generation_evidence(
        self,
        mode: str,
        hits: list[RetrievalHit],
        *,
        pre_generation_context_bound: bool,
    ) -> dict[str, Any]:
        rows = [
            {
                "source_id": f"S{index}",
                "work_id": hit.chunk.work_id,
                "chunk_id": hit.chunk.chunk_id,
                "content_hash": hit.chunk.content_hash,
                "source_uri": hit.chunk.source_uri,
                "rank": hit.rank,
            }
            for index, hit in enumerate(hits, start=1)
        ]
        return {
            "schema": "rdllm-generation-evidence/v1",
            "mode": mode,
            "pre_generation_context_bound": pre_generation_context_bound,
            "source_count": len(rows),
            "source_rows": rows,
            "context_hash": stable_hash(json.dumps(rows, sort_keys=True)),
        }

    def _settlement_decision(
        self,
        *,
        generation_evidence: dict[str, Any],
        claim_support: list[ClaimSupport],
        grounding_quality: dict[str, Any],
        shares: list[RoyaltyShare],
    ) -> dict[str, Any]:
        mode = str(generation_evidence.get("mode", "unknown"))
        escrowed = any(share.chunk_id.startswith("escrow:") for share in shares)
        evidence_bound = generation_evidence.get("pre_generation_context_bound") is True
        if mode == "provider_context_grounded":
            evidence_bound = (
                evidence_bound
                and generation_evidence.get("provider_evidence_verified") is True
            )
        claims_verified = bool(claim_support) and all(
            claim.supported for claim in claim_support
        )
        grounding_verified = grounding_quality.get("verdict") == "verified"
        eligible = evidence_bound and claims_verified and grounding_verified and not escrowed
        reasons: list[str] = []
        if not evidence_bound:
            reasons.append("pre_generation_source_context_or_provider_citation_not_proven")
        if not claims_verified:
            reasons.append("one_or_more_claims_not_verified")
        if not grounding_verified:
            reasons.append("grounding_quality_not_verified")
        if escrowed:
            reasons.append("creator_pool_escrowed")
        return {
            "schema": "rdllm-settlement-decision/v1",
            "status": (
                "eligible_for_processor_instruction"
                if eligible
                else "escrowed"
                if escrowed
                else "held_for_review"
            ),
            "generation_evidence_mode": mode,
            "eligible_for_settlement_instruction": eligible,
            "direct_execution_allowed": False,
            "external_processor_attestation_required": True,
            "reasons": reasons,
        }

    def _best_evidence_span(self, claim: str, chunk: Chunk) -> dict[str, Any]:
        claim_tokens = tokenize(claim)
        best_text = chunk_text(chunk.text, max_tokens=32)[0]
        best_score = -1.0
        for sentence in split_sentences(chunk.text) or [chunk.text]:
            span_tokens = tokenize(sentence)
            if not span_tokens:
                continue
            overlap = jaccard_similarity(claim_tokens, span_tokens)
            longest, _ = longest_common_token_sequence(claim_tokens, span_tokens)
            sequence_score = min(1.0, longest / max(6, len(claim_tokens)))
            score = 0.6 * overlap + 0.4 * sequence_score
            if score > best_score:
                best_score = score
                best_text = sentence

        start_char = chunk.text.find(best_text)
        if start_char < 0:
            start_char = 0
        end_char = start_char + len(best_text)
        return {
            "text": best_text,
            "span_hash": stable_hash(best_text),
            "start_char": start_char,
            "end_char": end_char,
        }

    def _attach_evidence_spans(
        self,
        references: list[SourceReference],
        claim_support: list[ClaimSupport],
    ) -> list[SourceReference]:
        span_hashes_by_label: dict[str, set[str]] = defaultdict(set)
        for support in claim_support:
            if support.supported and support.source_label and support.evidence_span_hash:
                span_hashes_by_label[support.source_label].add(support.evidence_span_hash)
        return [
            replace(
                reference,
                evidence_span_hashes=tuple(
                    sorted(span_hashes_by_label.get(reference.label, set()))
                ),
            )
            for reference in references
        ]

    def _extract_claims(self, answer_text: str) -> list[str]:
        claims: list[str] = []
        for line in answer_text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("Royalty-aware answer:") or line.startswith(
                "The strongest registered sources say:"
            ):
                continue
            if line.startswith("- "):
                line = line[2:].strip()
            for sentence in split_sentences(line):
                sentence = re.sub(r"^\[[A-Z]\d+\]\s*-?\s*", "", sentence.strip())
                sentence = re.sub(r"\s*\[[A-Z]\d+\]\s*$", "", sentence).strip()
                if tokenize(sentence):
                    claims.append(sentence)
        return claims

    def _grounding_report(
        self,
        claim_support: list[ClaimSupport],
        references: list[SourceReference],
        policy_decisions: list[dict[str, Any]],
        registry_decisions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        total_claims = len(claim_support)
        supported_claims = sum(1 for claim in claim_support if claim.supported)
        unsupported_claims = total_claims - supported_claims
        coverage = supported_claims / total_claims if total_claims else 0.0
        denied = [decision for decision in policy_decisions if not decision["allowed"]]
        registry_blocks = [
            decision for decision in registry_decisions if not decision.get("allowed", True)
        ]
        registry_conflict_ids = {
            decision.get("conflict_id", "") for decision in registry_blocks
        }
        registry_conflict_ids.discard("")
        status = "grounded" if total_claims and unsupported_claims == 0 else "partial"
        if denied:
            status = "rights_blocked"
        elif registry_blocks:
            status = "registry_disputed"
        return {
            "total_claims": total_claims,
            "supported_claims": supported_claims,
            "unsupported_claims": unsupported_claims,
            "coverage": round(coverage, 8),
            "source_count": len(references),
            "policy_denials": len(denied),
            "policy_status": "blocked" if denied else "allowed",
            "registry_conflicts": len(registry_conflict_ids),
            "registry_status": "disputed" if registry_blocks else "clear",
            "registry_report_hash": (
                self.registry_report.get("report_hash") if registry_blocks else ""
            ),
            "status": status,
        }

    def _render_grounded_output(
        self,
        answer_text: str,
        references: list[SourceReference],
        claim_support: list[ClaimSupport],
        grounding_report: dict[str, Any],
    ) -> str:
        registry_disputed = grounding_report.get("registry_conflicts", 0) > 0
        if grounding_report.get("policy_denials", 0):
            lines = [
                "This response is blocked by rights policy for the requested use.",
                "",
                "Sources",
            ]
        elif registry_disputed:
            lines = [
                "This response is held by ownership registry policy for the requested use.",
                "",
                "Sources",
            ]
        else:
            lines = [answer_text.rstrip(), "", "Sources"]
        if not references:
            if grounding_report.get("policy_denials", 0):
                lines.append(
                    "[R1] Registered source match(es) were found but blocked by rights policy; "
                    "creator pool assigned to rights-conflict escrow."
                )
            elif registry_disputed:
                lines.append(
                    "[D1] Registered source match(es) are under ownership dispute; "
                    "creator pool assigned to registry-dispute escrow."
                )
            else:
                lines.append(
                    "[U1] No registered source matched this output; creator pool assigned to unattributed escrow."
                )
        else:
            supported_counts: dict[str, int] = defaultdict(int)
            minimum_support_by_label: dict[str, float] = {}
            for support in claim_support:
                if not support.supported or not support.source_label:
                    continue
                supported_counts[support.source_label] += 1
                current = minimum_support_by_label.get(
                    support.source_label,
                    support.support_score,
                )
                minimum_support_by_label[support.source_label] = min(
                    current,
                    support.support_score,
                )
            for reference in references:
                supported_claims = supported_counts.get(reference.label, 0)
                minimum_support = minimum_support_by_label.get(reference.label, 0.0)
                confidence = (
                    "verified"
                    if supported_claims
                    and minimum_support >= FOOTER_VERIFIED_SUPPORT_FLOOR
                    and reference.source_uri
                    and reference.content_hash
                    and reference.quote
                    else "warning"
                )
                why = (
                    "verified_claim_support_identity_rights_royalty"
                    if confidence == "verified" and reference.payout > Decimal("0")
                    else "claim_support_needs_review"
                )
                lines.append(
                    f"[{reference.label}] {reference.title} - {reference.creator_name}; "
                    f"chunk={reference.chunk_id}; uri={reference.source_uri}; "
                    f"claims={supported_claims}; confidence={confidence}; "
                    f"support={reference.output_support:.3f}; "
                    f"text_match={reference.text_match_score:.3f}; "
                    f"why={why}; "
                    f"payout={reference.payout}; "
                    f"hash={reference.content_hash[:12]}."
                )
                span_text = ""
                if reference.evidence_span_hashes:
                    span_text = (
                        " span_hashes="
                        + ",".join(
                            span_hash[:12]
                            for span_hash in reference.evidence_span_hashes
                        )
                        + "."
                    )
                lines.append(f"    Evidence:{span_text} {reference.quote}")
        lines.append(
            "Grounding: "
            f"{grounding_report.get('supported_claims', 0)}/"
            f"{grounding_report.get('total_claims', 0)} claims supported; "
            f"status={grounding_report.get('status', 'partial')}."
        )
        supported_claims = [
            support
            for support in claim_support
            if support.supported and support.evidence_span_hash
        ]
        if (
            supported_claims
            and not grounding_report.get("policy_denials", 0)
            and not registry_disputed
        ):
            source_rows = [
                {
                    "label": reference.label,
                    "evidence_preview": reference.quote,
                }
                for reference in references
            ]
            lines.append("Claim Evidence")
            for index, support in enumerate(supported_claims, start=1):
                disagreement = claim_source_disagreement_report(
                    claim=support.claim,
                    source_label=support.source_label,
                    source_rows=source_rows,
                    supported=support.supported,
                )
                lines.append(
                    f"[C{index}] {support.source_label}; "
                    f"claim_hash={stable_hash(support.claim)[:12]}; "
                    f"support={support.support_score:.3f}; "
                    f"span={support.evidence_span_hash[:12]}; "
                    f"chars={support.evidence_start_char}-{support.evidence_end_char}. "
                    f"disagreement={disagreement['source_disagreement_status']}; "
                    f"agreements={_label_list(disagreement['agreement_source_labels'])}; "
                    f"conflicts={_label_list(disagreement['disagreement_source_labels'])}; "
                    f"disagreement_profile={disagreement['source_disagreement_profile']}. "
                    f"Evidence: {support.evidence_text}"
                )
        unsupported_claims = [
            support for support in claim_support if not support.supported
        ]
        if (
            unsupported_claims
            and not grounding_report.get("policy_denials", 0)
            and not registry_disputed
        ):
            lines.append("Unsupported Claims")
            for index, support in enumerate(unsupported_claims, start=1):
                lines.append(
                    f"[U{index}] claim_hash={stable_hash(support.claim)[:12]}; "
                    f"support={support.support_score:.3f}; "
                    "reason=no_registered_evidence."
                )
        if grounding_report.get("policy_denials", 0):
            lines.append(
                "Rights: "
                f"{grounding_report['policy_denials']} registered source match(es) "
                "were blocked by policy; creator pool assigned to rights-conflict escrow."
            )
        if registry_disputed:
            lines.append(
                "Registry: "
                f"{grounding_report['registry_conflicts']} ownership conflict(s) "
                "were open; creator pool assigned to registry-dispute escrow."
            )
        return "\n".join(lines)

    def _escrow_share(self, creator_pool: Decimal) -> RoyaltyShare:
        return RoyaltyShare(
            creator_id="unattributed_escrow",
            work_id="unattributed",
            chunk_id="escrow:unattributed",
            contribution_weight=Decimal("1"),
            payout=creator_pool,
            query_relevance=0.0,
            output_support=0.0,
            data_value_prior=0.0,
            content_hash=stable_hash("unattributed_escrow"),
            retrieval_score=0.0,
            text_match_score=0.0,
            citation_score=0.0,
            training_value_score=0.0,
            attribution_basis={"escrow": 1.0},
        )

    def _rights_conflict_share(self, creator_pool: Decimal) -> RoyaltyShare:
        return RoyaltyShare(
            creator_id="rights_conflict_escrow",
            work_id="rights_conflict",
            chunk_id="escrow:rights_conflict",
            contribution_weight=Decimal("1"),
            payout=creator_pool,
            query_relevance=0.0,
            output_support=0.0,
            data_value_prior=0.0,
            content_hash=stable_hash("rights_conflict_escrow"),
            retrieval_score=0.0,
            text_match_score=0.0,
            citation_score=0.0,
            training_value_score=0.0,
            attribution_basis={"rights_conflict_escrow": 1.0},
        )

    def _registry_dispute_share(self, creator_pool: Decimal) -> RoyaltyShare:
        return RoyaltyShare(
            creator_id="registry_dispute_escrow",
            work_id="registry_dispute",
            chunk_id="escrow:registry_dispute",
            contribution_weight=Decimal("1"),
            payout=creator_pool,
            query_relevance=0.0,
            output_support=0.0,
            data_value_prior=0.0,
            content_hash=stable_hash("registry_dispute_escrow"),
            retrieval_score=0.0,
            text_match_score=0.0,
            citation_score=0.0,
            training_value_score=0.0,
            attribution_basis={"registry_dispute_escrow": 1.0},
        )

    def _event_hash(
        self,
        prompt: str,
        answer_text: str,
        output: str,
        gross_revenue: Decimal | str | float,
        creator_pool: Decimal,
        shares: list[RoyaltyShare],
        source_references: list[SourceReference],
        claim_support: list[ClaimSupport],
        grounding_report: dict[str, Any],
        grounding_quality: dict[str, Any],
        attribution_gap: dict[str, Any],
        generation_evidence: dict[str, Any],
        settlement_decision: dict[str, Any],
        policy_decisions: list[dict[str, Any]],
        registry_decisions: list[dict[str, Any]],
    ) -> str:
        payload: dict[str, Any] = {
            "prompt": prompt,
            "answer_text": answer_text,
            "output": output,
            "gross_revenue": str(Decimal(str(gross_revenue)).quantize(MONEY_QUANT)),
            "creator_pool": str(creator_pool),
            "shares": [share.to_dict() for share in shares],
            "source_references": [
                reference.to_dict() for reference in source_references
            ],
            "claim_support": [support.to_dict() for support in claim_support],
            "grounding_report": grounding_report,
            "grounding_quality": grounding_quality,
            "attribution_gap": attribution_gap,
            "generation_evidence": generation_evidence,
            "settlement_decision": settlement_decision,
            "policy_decisions": policy_decisions,
            "registry_decisions": registry_decisions,
        }
        return stable_hash(json.dumps(payload, sort_keys=True))

    def aggregate_creator_payouts(self, event: UsageEvent) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = defaultdict(Decimal)
        for share in event.royalty_shares:
            totals[share.creator_id] += share.payout
        return dict(totals)

    def policy_manifest(self) -> dict[str, Any]:
        return self.policy_engine.rights_manifest(
            creators=self.creators,
            works=self.works,
            chunks=self.chunks,
        )
