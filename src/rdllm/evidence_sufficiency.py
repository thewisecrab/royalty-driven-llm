"""Claim-level evidence sufficiency reports for RDLLM citation footers."""

from __future__ import annotations

from typing import Any

from rdllm.engine import RoyaltyDrivenLLM
from rdllm.models import ClaimSupport, SourceReference, UsageEvent
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.text import (
    jaccard_similarity,
    longest_common_token_sequence,
    split_sentences,
    stable_hash,
    tokenize,
)

EVIDENCE_SUFFICIENCY_VERSION = "rdllm-evidence-sufficiency-report/v1"
EVIDENCE_SUFFICIENCY_SCHEMA = "docs/schemas/evidence_sufficiency_report.schema.json"
EVIDENCE_SUFFICIENCY_POLICY_VERSION = "rdllm-evidence-sufficiency-policy/v1"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L56"

SUPPORT_THRESHOLD = 0.75
MIN_DECOY_MARGIN = 0.15
MAX_MINIMAL_PREFIX_SIZE = 1
DEFAULT_CANDIDATE_LIMIT = 5


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _declared_hash(artifact: dict[str, Any] | None) -> str:
    if not artifact:
        return ""
    for field in (
        "contract_hash",
        "report_hash",
        "card_hash",
        "envelope_hash",
        "receipt_hash",
    ):
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(artifact)


def _artifact_bindings(
    *,
    answer_card: dict[str, Any] | None,
    source_verification_report: dict[str, Any] | None,
    source_availability_report: dict[str, Any] | None,
    citation_footer_contract: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "answer_card_hash": _declared_hash(answer_card),
        "source_verification_report_hash": _declared_hash(source_verification_report),
        "source_availability_report_hash": _declared_hash(source_availability_report),
        "citation_footer_contract_hash": _declared_hash(citation_footer_contract),
        "answer_card_bound": bool(answer_card),
        "source_verification_bound": bool(source_verification_report),
        "source_availability_bound": bool(source_availability_report),
        "citation_footer_bound": bool(citation_footer_contract),
    }


def _label_set_from_answer_card(answer_card: dict[str, Any] | None) -> set[str]:
    if not answer_card:
        return set()
    return {
        str(source.get("label", ""))
        for source in answer_card.get("sources", [])
        if source.get("label")
    }


def _claim_span_prefix_set_from_answer_card(answer_card: dict[str, Any] | None) -> set[str]:
    if not answer_card:
        return set()
    return {
        str(claim.get("evidence_span_prefix", ""))
        for claim in answer_card.get("claims", [])
        if claim.get("evidence_span_prefix")
    }


def _label_set_from_footer_contract(contract: dict[str, Any] | None) -> set[str]:
    if not contract:
        return set()
    return {
        str(source.get("label", ""))
        for source in contract.get("sources", [])
        if source.get("label")
    }


def _claim_span_prefix_set_from_footer_contract(contract: dict[str, Any] | None) -> set[str]:
    if not contract:
        return set()
    return {
        str(claim.get("evidence_span_prefix", ""))
        for claim in contract.get("claims", [])
        if claim.get("evidence_span_prefix")
    }


def _availability_by_label(report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not report:
        return {}
    return {
        str(source.get("label", "")): source
        for source in report.get("sources", [])
        if source.get("label")
    }


def _source_verification_claims_by_index(
    report: dict[str, Any] | None,
) -> dict[int, dict[str, Any]]:
    if not report:
        return {}
    rows: dict[int, dict[str, Any]] = {}
    for claim in report.get("claims", []):
        index = int(claim.get("claim_index", 0) or 0)
        if index:
            rows[index] = claim
    return rows


def _evidence_score(claim_text: str, evidence_text: str) -> dict[str, Any]:
    claim_tokens = tokenize(claim_text)
    evidence_tokens = tokenize(evidence_text)
    overlap = jaccard_similarity(claim_tokens, evidence_tokens)
    longest, _ = longest_common_token_sequence(claim_tokens, evidence_tokens)
    sequence_score = min(1.0, longest / max(6, len(claim_tokens))) if claim_tokens else 0.0
    score = min(1.0, 0.6 * overlap + 0.4 * sequence_score)
    return {
        "support_score": round(score, 8),
        "token_overlap": round(overlap, 8),
        "sequence_score": round(sequence_score, 8),
        "claim_token_count": len(claim_tokens),
        "evidence_token_count": len(evidence_tokens),
    }


def _candidate_rows(
    *,
    claim: ClaimSupport,
    sources: list[SourceReference],
    engine: RoyaltyDrivenLLM,
    candidate_limit: int,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for source in sources:
        chunk = engine.chunk_by_id.get(source.chunk_id)
        if not chunk:
            continue
        for sentence in split_sentences(chunk.text):
            if not sentence:
                continue
            span_hash = stable_hash(sentence)
            key = (source.label, source.chunk_id, span_hash)
            if key in seen:
                continue
            seen.add(key)
            start_char = chunk.text.find(sentence)
            if start_char < 0:
                start_char = 0
            scoring = _evidence_score(claim.claim, sentence)
            row = {
                "source_label": source.label,
                "work_id": source.work_id,
                "chunk_id": source.chunk_id,
                "creator_id": source.creator_id,
                "source_uri": source.source_uri,
                "evidence_span_hash": span_hash,
                "evidence_span_prefix": span_hash[:12],
                "evidence_start_char": start_char,
                "evidence_end_char": start_char + len(sentence),
                "content_hash": source.content_hash,
                "support_score": scoring["support_score"],
                "token_overlap": scoring["token_overlap"],
                "sequence_score": scoring["sequence_score"],
                "claim_token_count": scoring["claim_token_count"],
                "evidence_token_count": scoring["evidence_token_count"],
                "is_cited_evidence_span": (
                    source.label == claim.source_label
                    and span_hash == claim.evidence_span_hash
                ),
                "is_cited_source": source.label == claim.source_label,
            }
            row["candidate_hash"] = hash_payload(row)
            candidates.append(row)
    candidates.sort(
        key=lambda item: (
            -float(item["support_score"]),
            not bool(item["is_cited_evidence_span"]),
            str(item["source_label"]),
            str(item["evidence_span_hash"]),
        )
    )
    limited: list[dict[str, Any]] = []
    for rank, row in enumerate(candidates[: max(1, candidate_limit)], start=1):
        ranked = dict(row)
        ranked["rank"] = rank
        ranked["candidate_hash"] = hash_payload(
            {key: value for key, value in ranked.items() if key != "candidate_hash"}
        )
        limited.append(ranked)
    return limited


def _claim_rows(
    *,
    event: UsageEvent,
    engine: RoyaltyDrivenLLM,
    answer_card: dict[str, Any] | None,
    source_verification_report: dict[str, Any] | None,
    source_availability_report: dict[str, Any] | None,
    citation_footer_contract: dict[str, Any] | None,
    candidate_limit: int,
) -> list[dict[str, Any]]:
    answer_labels = _label_set_from_answer_card(answer_card)
    answer_spans = _claim_span_prefix_set_from_answer_card(answer_card)
    footer_labels = _label_set_from_footer_contract(citation_footer_contract)
    footer_spans = _claim_span_prefix_set_from_footer_contract(citation_footer_contract)
    availability_by_label = _availability_by_label(source_availability_report)
    source_claims = _source_verification_claims_by_index(source_verification_report)
    rows: list[dict[str, Any]] = []

    for index, claim in enumerate(event.claim_support, start=1):
        candidates = _candidate_rows(
            claim=claim,
            sources=list(event.source_references),
            engine=engine,
            candidate_limit=candidate_limit,
        )
        top = candidates[0] if candidates else {}
        cited_rank = 0
        for candidate in candidates:
            if candidate.get("is_cited_evidence_span"):
                cited_rank = int(candidate.get("rank", 0) or 0)
                break
        top_score = float(top.get("support_score", 0.0) or 0.0)
        best_non_cited_score = max(
            [
                float(candidate.get("support_score", 0.0) or 0.0)
                for candidate in candidates
                if not candidate.get("is_cited_evidence_span")
            ]
            or [0.0]
        )
        decoy_margin = round(max(0.0, top_score - best_non_cited_score), 8)
        source_available = (
            availability_by_label.get(claim.source_label, {}).get("inspectable") is True
        )
        source_verified_claim = source_claims.get(index, {}).get("materialized") is True
        span_prefix = claim.evidence_span_hash[:12] if claim.evidence_span_hash else ""
        source_footer_bound = (
            bool(claim.source_label)
            and claim.source_label in answer_labels
            and claim.source_label in footer_labels
        )
        span_footer_bound = (
            bool(span_prefix)
            and span_prefix in answer_spans
            and span_prefix in footer_spans
        )
        sufficient = bool(
            claim.supported
            and cited_rank > 0
            and cited_rank <= MAX_MINIMAL_PREFIX_SIZE
            and top.get("is_cited_evidence_span") is True
            and top_score >= SUPPORT_THRESHOLD
            and decoy_margin >= MIN_DECOY_MARGIN
            and source_available
            and source_verified_claim
            and source_footer_bound
            and span_footer_bound
        )
        row = {
            "claim_index": index,
            "claim_hash": stable_hash(claim.claim),
            "source_label": claim.source_label,
            "work_id": claim.work_id,
            "chunk_id": claim.chunk_id,
            "evidence_span_hash": claim.evidence_span_hash,
            "evidence_span_prefix": span_prefix,
            "claim_support_score": round(float(claim.support_score), 8),
            "support_threshold": SUPPORT_THRESHOLD,
            "minimum_decoy_margin": MIN_DECOY_MARGIN,
            "candidate_count": len(candidates),
            "candidate_limit": candidate_limit,
            "cited_evidence_rank": cited_rank,
            "minimal_sufficient_prefix_size": cited_rank if sufficient else 0,
            "top_candidate_is_cited_span": top.get("is_cited_evidence_span") is True,
            "top_support_score": round(top_score, 8),
            "best_non_cited_support_score": round(best_non_cited_score, 8),
            "decoy_margin": decoy_margin,
            "ambiguous_decoy": best_non_cited_score > 0.0
            and decoy_margin < MIN_DECOY_MARGIN,
            "source_available": source_available,
            "source_verified_claim": source_verified_claim,
            "source_footer_bound": source_footer_bound,
            "span_footer_bound": span_footer_bound,
            "sufficient": sufficient,
            "inspection_order": [
                {
                    "rank": candidate["rank"],
                    "source_label": candidate["source_label"],
                    "evidence_span_prefix": candidate["evidence_span_prefix"],
                    "support_score": candidate["support_score"],
                }
                for candidate in candidates
            ],
            "candidates": candidates,
        }
        row["claim_sufficiency_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _issues(rows: list[dict[str, Any]], bindings: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for name, field in (
        ("answer provenance card", "answer_card_bound"),
        ("source verification report", "source_verification_bound"),
        ("source availability report", "source_availability_bound"),
        ("citation footer contract", "citation_footer_bound"),
    ):
        if not bindings.get(field):
            issues.append(f"{name} is not bound")
    for row in rows:
        claim_index = row["claim_index"]
        if not row["sufficient"]:
            issues.append(f"claim C{claim_index} lacks sufficient top-ranked evidence")
        if not row["top_candidate_is_cited_span"]:
            issues.append(f"claim C{claim_index} cited span is not top-ranked evidence")
        if row["ambiguous_decoy"]:
            issues.append(f"claim C{claim_index} has an ambiguous decoy evidence span")
        if not row["source_available"]:
            issues.append(f"claim C{claim_index} source is not availability verified")
        if not row["source_verified_claim"]:
            issues.append(f"claim C{claim_index} is not materialized by source verification")
        if not row["source_footer_bound"] or not row["span_footer_bound"]:
            issues.append(f"claim C{claim_index} is not bound to the rendered footer")
    return issues


def make_evidence_sufficiency_report(
    event: UsageEvent,
    engine: RoyaltyDrivenLLM,
    *,
    answer_card: dict[str, Any] | None = None,
    source_verification_report: dict[str, Any] | None = None,
    source_availability_report: dict[str, Any] | None = None,
    citation_footer_contract: dict[str, Any] | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
    candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
) -> dict[str, Any]:
    """Create a report proving cited claim spans are sufficient and non-ambiguous."""

    bindings = _artifact_bindings(
        answer_card=answer_card,
        source_verification_report=source_verification_report,
        source_availability_report=source_availability_report,
        citation_footer_contract=citation_footer_contract,
    )
    claim_rows = _claim_rows(
        event=event,
        engine=engine,
        answer_card=answer_card,
        source_verification_report=source_verification_report,
        source_availability_report=source_availability_report,
        citation_footer_contract=citation_footer_contract,
        candidate_limit=candidate_limit,
    )
    issue_list = _issues(claim_rows, bindings)
    sufficient_count = sum(1 for row in claim_rows if row["sufficient"])
    report = {
        "report_version": EVIDENCE_SUFFICIENCY_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": {
            "profile": EVIDENCE_SUFFICIENCY_POLICY_VERSION,
            "requires_top_ranked_cited_span": True,
            "requires_minimal_sufficient_prefix": True,
            "max_minimal_prefix_size": MAX_MINIMAL_PREFIX_SIZE,
            "support_threshold": SUPPORT_THRESHOLD,
            "minimum_decoy_margin": MIN_DECOY_MARGIN,
            "requires_source_availability": True,
            "requires_source_materialization": True,
            "requires_footer_binding": True,
        },
        "event": {
            "event_id": event.event_id,
            "event_hash": event.event_hash,
            "rendered_output_hash": stable_hash(event.output),
            "answer_hash": stable_hash(event.answer_text or event.output),
        },
        "artifact_bindings": bindings,
        "claims": claim_rows,
        "summary": {
            "status": "verified" if not issue_list else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "claim_count": len(claim_rows),
            "sufficient_claim_count": sufficient_count,
            "top_ranked_cited_span_count": sum(
                1 for row in claim_rows if row["top_candidate_is_cited_span"]
            ),
            "footer_bound_claim_count": sum(
                1
                for row in claim_rows
                if row["source_footer_bound"] and row["span_footer_bound"]
            ),
            "source_available_claim_count": sum(
                1 for row in claim_rows if row["source_available"]
            ),
            "ambiguous_decoy_claim_count": sum(
                1 for row in claim_rows if row["ambiguous_decoy"]
            ),
            "minimum_decoy_margin_observed": min(
                [float(row["decoy_margin"]) for row in claim_rows] or [1.0]
            ),
            "all_claims_have_minimal_sufficient_evidence": bool(claim_rows)
            and sufficient_count == len(claim_rows),
            "issue_count": len(issue_list),
        },
        "commitments": {
            "claim_sufficiency_root": hash_payload(claim_rows),
            "artifact_binding_root": hash_payload(bindings),
            "issue_root": hash_payload(issue_list),
            "event_hash": event.event_hash,
        },
        "schemas": {
            "evidence_sufficiency_report": EVIDENCE_SUFFICIENCY_SCHEMA,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "claim_text_disclosed": False,
            "source_text_disclosed": False,
            "candidate_evidence_text_disclosed": False,
            "claim_evidence_text_disclosed": False,
            "report_uses_hashes_scores_and_offsets": True,
        },
        "issues": issue_list,
    }
    report["report_hash"] = hash_payload(_hashable_report(report))
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_report(report), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return report


def validate_evidence_sufficiency_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "event",
        "artifact_bindings",
        "claims",
        "summary",
        "commitments",
        "schemas",
        "privacy",
        "issues",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing evidence sufficiency report field: {key}")
    if errors:
        return errors
    if report.get("report_version") != EVIDENCE_SUFFICIENCY_VERSION:
        errors.append("evidence sufficiency report version is unsupported")
    if report.get("policy", {}).get("profile") != EVIDENCE_SUFFICIENCY_POLICY_VERSION:
        errors.append("evidence sufficiency policy profile is unsupported")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("evidence sufficiency target certification level is unsupported")
    for key in ("event_id", "event_hash", "rendered_output_hash", "answer_hash"):
        if key not in report.get("event", {}):
            errors.append(f"missing evidence sufficiency event field: {key}")
    for key in (
        "claim_sufficiency_root",
        "artifact_binding_root",
        "issue_root",
        "event_hash",
    ):
        if key not in report.get("commitments", {}):
            errors.append(f"missing evidence sufficiency commitment field: {key}")
    for claim in report.get("claims", []):
        for key in (
            "claim_index",
            "claim_hash",
            "source_label",
            "evidence_span_hash",
            "candidate_count",
            "cited_evidence_rank",
            "top_candidate_is_cited_span",
            "decoy_margin",
            "sufficient",
            "claim_sufficiency_hash",
        ):
            if key not in claim:
                errors.append(f"missing evidence sufficiency claim field: {key}")
    return errors


def verify_evidence_sufficiency_report(
    report: dict[str, Any],
    event: UsageEvent,
    engine: RoyaltyDrivenLLM,
    *,
    answer_card: dict[str, Any] | None = None,
    source_verification_report: dict[str, Any] | None = None,
    source_availability_report: dict[str, Any] | None = None,
    citation_footer_contract: dict[str, Any] | None = None,
    signing_secret: str | None = None,
    candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
) -> list[str]:
    """Replay and verify claim evidence sufficiency against private source text."""

    errors = validate_evidence_sufficiency_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("evidence sufficiency report hash is not reproducible")

    expected = make_evidence_sufficiency_report(
        event,
        engine,
        answer_card=answer_card,
        source_verification_report=source_verification_report,
        source_availability_report=source_availability_report,
        citation_footer_contract=citation_footer_contract,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
        candidate_limit=candidate_limit,
    )
    for key in (
        "policy",
        "event",
        "artifact_bindings",
        "claims",
        "summary",
        "commitments",
        "schemas",
        "privacy",
        "issues",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"evidence sufficiency report {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("evidence sufficiency report hash does not match replay")

    if report.get("summary", {}).get("status") != "verified":
        errors.append("evidence sufficiency report status is not verified")
    if report.get("summary", {}).get("all_claims_have_minimal_sufficient_evidence") is not True:
        errors.append("evidence sufficiency report has insufficient claims")
    if report.get("issues"):
        errors.append("evidence sufficiency report contains issues")

    rendered = canonical_json(report)
    for forbidden in (event.prompt, event.answer_text):
        if forbidden and len(forbidden.strip()) >= 16 and forbidden in rendered:
            errors.append("evidence sufficiency report leaks private prompt or answer text")
            break
    for chunk in engine.chunks:
        if len(chunk.text.strip()) >= 16 and chunk.text in rendered:
            errors.append("evidence sufficiency report leaks source text")
            break
    for claim in event.claim_support:
        if claim.claim and len(claim.claim.strip()) >= 16 and claim.claim in rendered:
            errors.append("evidence sufficiency report leaks claim text")
            break
        if (
            claim.evidence_text
            and len(claim.evidence_text.strip()) >= 16
            and claim.evidence_text in rendered
        ):
            errors.append("evidence sufficiency report leaks evidence text")
            break

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("evidence sufficiency report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("evidence sufficiency report signature is invalid")
    return errors
