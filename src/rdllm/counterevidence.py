"""Counterevidence adjudication reports for RDLLM claim footers."""

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

COUNTEREVIDENCE_VERSION = "rdllm-counterevidence-adjudication-report/v1"
COUNTEREVIDENCE_SCHEMA = "docs/schemas/counterevidence_report.schema.json"
COUNTEREVIDENCE_POLICY_VERSION = "rdllm-counterevidence-policy/v1"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L57"

COUNTEREVIDENCE_THRESHOLD = 0.55
MAX_UNADDRESSED_COUNTEREVIDENCE = 0
DEFAULT_CANDIDATE_LIMIT = 5

NEGATION_TERMS = {
    "no",
    "not",
    "never",
    "without",
    "cannot",
    "cant",
    "can't",
    "doesnt",
    "doesn't",
    "dont",
    "don't",
    "isnt",
    "isn't",
    "wont",
    "won't",
    "false",
    "deny",
    "denies",
    "denied",
    "blocked",
    "prohibited",
    "invalid",
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "for",
    "from",
    "have",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "should",
    "that",
    "the",
    "their",
    "this",
    "to",
    "use",
    "with",
}

ACKNOWLEDGEMENT_TERMS = {
    "although",
    "but",
    "conflict",
    "conflicting",
    "contradict",
    "contradicts",
    "counterevidence",
    "dispute",
    "disputed",
    "however",
    "mixed",
    "some sources",
    "uncertain",
}


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
        "report_hash",
        "contract_hash",
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
    evidence_sufficiency_report: dict[str, Any] | None,
    citation_footer_contract: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "answer_card_hash": _declared_hash(answer_card),
        "source_verification_report_hash": _declared_hash(source_verification_report),
        "source_availability_report_hash": _declared_hash(source_availability_report),
        "evidence_sufficiency_report_hash": _declared_hash(evidence_sufficiency_report),
        "citation_footer_contract_hash": _declared_hash(citation_footer_contract),
        "answer_card_bound": bool(answer_card),
        "source_verification_bound": bool(source_verification_report),
        "source_availability_bound": bool(source_availability_report),
        "evidence_sufficiency_bound": (
            evidence_sufficiency_report is not None
            and evidence_sufficiency_report.get("summary", {}).get("status") == "verified"
        ),
        "citation_footer_bound": bool(citation_footer_contract),
    }


def _label_set_from_artifact(artifact: dict[str, Any] | None) -> set[str]:
    if not artifact:
        return set()
    return {
        str(source.get("label", ""))
        for source in artifact.get("sources", [])
        if source.get("label")
    }


def _content_tokens(text: str) -> list[str]:
    return [
        token
        for token in tokenize(text)
        if token not in STOPWORDS and token not in NEGATION_TERMS and len(token) > 2
    ]


def _polarity(text: str) -> str:
    tokens = set(tokenize(text))
    return "negative" if tokens & NEGATION_TERMS else "positive"


def _answer_acknowledges_counterevidence(answer_text: str) -> bool:
    normalized = " ".join(tokenize(answer_text))
    return any(term in normalized for term in ACKNOWLEDGEMENT_TERMS)


def _counterevidence_score(claim_text: str, candidate_text: str) -> dict[str, Any]:
    claim_terms = _content_tokens(claim_text)
    candidate_terms = _content_tokens(candidate_text)
    overlap = jaccard_similarity(claim_terms, candidate_terms)
    longest, _ = longest_common_token_sequence(claim_terms, candidate_terms)
    sequence_score = min(1.0, longest / max(4, len(claim_terms))) if claim_terms else 0.0
    claim_polarity = _polarity(claim_text)
    candidate_polarity = _polarity(candidate_text)
    polarity_conflict = claim_polarity != candidate_polarity
    score = min(1.0, 0.7 * overlap + 0.3 * sequence_score)
    if not polarity_conflict:
        score = 0.0
    return {
        "counterevidence_score": round(score, 8),
        "term_overlap": round(overlap, 8),
        "sequence_score": round(sequence_score, 8),
        "claim_polarity": claim_polarity,
        "candidate_polarity": candidate_polarity,
        "polarity_conflict": polarity_conflict,
        "claim_term_count": len(claim_terms),
        "candidate_term_count": len(candidate_terms),
    }


def _source_by_chunk(event: UsageEvent) -> dict[str, SourceReference]:
    return {source.chunk_id: source for source in event.source_references}


def _candidate_rows(
    *,
    claim: ClaimSupport,
    event: UsageEvent,
    engine: RoyaltyDrivenLLM,
    candidate_limit: int,
) -> list[dict[str, Any]]:
    cited_sources = _source_by_chunk(event)
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for chunk in sorted(engine.chunks, key=lambda item: item.chunk_id):
        for sentence in split_sentences(chunk.text):
            if not sentence:
                continue
            span_hash = stable_hash(sentence)
            key = (chunk.chunk_id, span_hash)
            if key in seen:
                continue
            seen.add(key)
            scoring = _counterevidence_score(claim.claim, sentence)
            if (
                not scoring["polarity_conflict"]
                or float(scoring["counterevidence_score"]) < COUNTEREVIDENCE_THRESHOLD
            ):
                continue
            source = cited_sources.get(chunk.chunk_id)
            start_char = chunk.text.find(sentence)
            if start_char < 0:
                start_char = 0
            row = {
                "source_label": source.label if source else "",
                "work_id": chunk.work_id,
                "chunk_id": chunk.chunk_id,
                "creator_id": chunk.creator_id,
                "source_uri": chunk.source_uri,
                "content_hash": chunk.content_hash,
                "evidence_span_hash": span_hash,
                "evidence_span_prefix": span_hash[:12],
                "evidence_start_char": start_char,
                "evidence_end_char": start_char + len(sentence),
                "counterevidence_score": scoring["counterevidence_score"],
                "term_overlap": scoring["term_overlap"],
                "sequence_score": scoring["sequence_score"],
                "claim_polarity": scoring["claim_polarity"],
                "candidate_polarity": scoring["candidate_polarity"],
                "polarity_conflict": scoring["polarity_conflict"],
                "claim_term_count": scoring["claim_term_count"],
                "candidate_term_count": scoring["candidate_term_count"],
                "is_cited_source": source is not None,
                "is_cited_evidence_span": span_hash == claim.evidence_span_hash,
            }
            row["candidate_hash"] = hash_payload(row)
            candidates.append(row)
    candidates.sort(
        key=lambda item: (
            -float(item["counterevidence_score"]),
            not bool(item["is_cited_source"]),
            str(item["chunk_id"]),
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
    citation_footer_contract: dict[str, Any] | None,
    candidate_limit: int,
) -> list[dict[str, Any]]:
    answer_labels = _label_set_from_artifact(answer_card)
    footer_labels = _label_set_from_artifact(citation_footer_contract)
    answer_acknowledges = _answer_acknowledges_counterevidence(
        event.answer_text or event.output
    )
    rows: list[dict[str, Any]] = []
    for index, claim in enumerate(event.claim_support, start=1):
        candidates = _candidate_rows(
            claim=claim,
            event=event,
            engine=engine,
            candidate_limit=candidate_limit,
        )
        addressed_count = 0
        unaddressed_count = 0
        candidate_summaries: list[dict[str, Any]] = []
        for candidate in candidates:
            footer_bound = bool(
                candidate["source_label"]
                and candidate["source_label"] in answer_labels
                and candidate["source_label"] in footer_labels
            )
            addressed = answer_acknowledges and footer_bound
            if addressed:
                addressed_count += 1
            else:
                unaddressed_count += 1
            candidate_summaries.append(
                {
                    **candidate,
                    "counterevidence_footer_bound": footer_bound,
                    "answer_acknowledges_counterevidence": answer_acknowledges,
                    "addressed": addressed,
                }
            )
        row = {
            "claim_index": index,
            "claim_hash": stable_hash(claim.claim),
            "source_label": claim.source_label,
            "work_id": claim.work_id,
            "chunk_id": claim.chunk_id,
            "evidence_span_hash": claim.evidence_span_hash,
            "evidence_span_prefix": claim.evidence_span_hash[:12],
            "counterevidence_threshold": COUNTEREVIDENCE_THRESHOLD,
            "candidate_limit": candidate_limit,
            "counterevidence_candidate_count": len(candidates),
            "addressed_counterevidence_count": addressed_count,
            "unaddressed_counterevidence_count": unaddressed_count,
            "counterevidence_free": unaddressed_count == 0,
            "answer_acknowledges_counterevidence": answer_acknowledges,
            "candidates": candidate_summaries,
        }
        row["claim_counterevidence_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _issues(rows: list[dict[str, Any]], bindings: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for name, field in (
        ("answer provenance card", "answer_card_bound"),
        ("source verification report", "source_verification_bound"),
        ("source availability report", "source_availability_bound"),
        ("evidence sufficiency report", "evidence_sufficiency_bound"),
        ("citation footer contract", "citation_footer_bound"),
    ):
        if not bindings.get(field):
            issues.append(f"{name} is not bound")
    for row in rows:
        if row["unaddressed_counterevidence_count"] > MAX_UNADDRESSED_COUNTEREVIDENCE:
            issues.append(
                f"claim C{row['claim_index']} has unaddressed counterevidence"
            )
    return issues


def make_counterevidence_report(
    event: UsageEvent,
    engine: RoyaltyDrivenLLM,
    *,
    answer_card: dict[str, Any] | None = None,
    source_verification_report: dict[str, Any] | None = None,
    source_availability_report: dict[str, Any] | None = None,
    evidence_sufficiency_report: dict[str, Any] | None = None,
    citation_footer_contract: dict[str, Any] | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
    candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
) -> dict[str, Any]:
    """Create a report proving cited claims have no unaddressed counterevidence."""

    bindings = _artifact_bindings(
        answer_card=answer_card,
        source_verification_report=source_verification_report,
        source_availability_report=source_availability_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        citation_footer_contract=citation_footer_contract,
    )
    claim_rows = _claim_rows(
        event=event,
        engine=engine,
        answer_card=answer_card,
        citation_footer_contract=citation_footer_contract,
        candidate_limit=candidate_limit,
    )
    issue_list = _issues(claim_rows, bindings)
    unaddressed_count = sum(
        int(row["unaddressed_counterevidence_count"]) for row in claim_rows
    )
    candidate_count = sum(
        int(row["counterevidence_candidate_count"]) for row in claim_rows
    )
    report = {
        "report_version": COUNTEREVIDENCE_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": {
            "profile": COUNTEREVIDENCE_POLICY_VERSION,
            "counterevidence_threshold": COUNTEREVIDENCE_THRESHOLD,
            "max_unaddressed_counterevidence": MAX_UNADDRESSED_COUNTEREVIDENCE,
            "requires_evidence_sufficiency": True,
            "requires_source_availability": True,
            "requires_source_materialization": True,
            "requires_footer_binding_for_addressed_counterevidence": True,
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
            "counterevidence_candidate_count": candidate_count,
            "unaddressed_counterevidence_count": unaddressed_count,
            "addressed_counterevidence_count": sum(
                int(row["addressed_counterevidence_count"]) for row in claim_rows
            ),
            "counterevidence_free_claim_count": sum(
                1 for row in claim_rows if row["counterevidence_free"]
            ),
            "all_claims_counterevidence_adjudicated": bool(claim_rows)
            and unaddressed_count == 0,
            "issue_count": len(issue_list),
        },
        "commitments": {
            "claim_counterevidence_root": hash_payload(claim_rows),
            "artifact_binding_root": hash_payload(bindings),
            "issue_root": hash_payload(issue_list),
            "event_hash": event.event_hash,
        },
        "schemas": {
            "counterevidence_report": COUNTEREVIDENCE_SCHEMA,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "claim_text_disclosed": False,
            "source_text_disclosed": False,
            "counterevidence_text_disclosed": False,
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


def validate_counterevidence_report_shape(report: dict[str, Any]) -> list[str]:
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
            errors.append(f"missing counterevidence report field: {key}")
    if errors:
        return errors
    if report.get("report_version") != COUNTEREVIDENCE_VERSION:
        errors.append("counterevidence report version is unsupported")
    if report.get("policy", {}).get("profile") != COUNTEREVIDENCE_POLICY_VERSION:
        errors.append("counterevidence policy profile is unsupported")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("counterevidence target certification level is unsupported")
    for key in ("event_id", "event_hash", "rendered_output_hash", "answer_hash"):
        if key not in report.get("event", {}):
            errors.append(f"missing counterevidence event field: {key}")
    for key in (
        "claim_counterevidence_root",
        "artifact_binding_root",
        "issue_root",
        "event_hash",
    ):
        if key not in report.get("commitments", {}):
            errors.append(f"missing counterevidence commitment field: {key}")
    for claim in report.get("claims", []):
        for key in (
            "claim_index",
            "claim_hash",
            "counterevidence_candidate_count",
            "unaddressed_counterevidence_count",
            "counterevidence_free",
            "claim_counterevidence_hash",
        ):
            if key not in claim:
                errors.append(f"missing counterevidence claim field: {key}")
    return errors


def verify_counterevidence_report(
    report: dict[str, Any],
    event: UsageEvent,
    engine: RoyaltyDrivenLLM,
    *,
    answer_card: dict[str, Any] | None = None,
    source_verification_report: dict[str, Any] | None = None,
    source_availability_report: dict[str, Any] | None = None,
    evidence_sufficiency_report: dict[str, Any] | None = None,
    citation_footer_contract: dict[str, Any] | None = None,
    signing_secret: str | None = None,
    candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
) -> list[str]:
    """Replay and verify counterevidence adjudication against private source text."""

    errors = validate_counterevidence_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("counterevidence report hash is not reproducible")

    expected = make_counterevidence_report(
        event,
        engine,
        answer_card=answer_card,
        source_verification_report=source_verification_report,
        source_availability_report=source_availability_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
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
            errors.append(f"counterevidence report {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("counterevidence report hash does not match replay")

    if report.get("summary", {}).get("status") != "verified":
        errors.append("counterevidence report status is not verified")
    if report.get("summary", {}).get("all_claims_counterevidence_adjudicated") is not True:
        errors.append("counterevidence report has unadjudicated claims")
    if report.get("issues"):
        errors.append("counterevidence report contains issues")

    rendered = canonical_json(report)
    for forbidden in (event.prompt, event.answer_text):
        if forbidden and len(forbidden.strip()) >= 16 and forbidden in rendered:
            errors.append("counterevidence report leaks private prompt or answer text")
            break
    for chunk in engine.chunks:
        if len(chunk.text.strip()) >= 16 and chunk.text in rendered:
            errors.append("counterevidence report leaks source text")
            break
    for claim in event.claim_support:
        if claim.claim and len(claim.claim.strip()) >= 16 and claim.claim in rendered:
            errors.append("counterevidence report leaks claim text")
            break
        if (
            claim.evidence_text
            and len(claim.evidence_text.strip()) >= 16
            and claim.evidence_text in rendered
        ):
            errors.append("counterevidence report leaks evidence text")
            break

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("counterevidence report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("counterevidence report signature is invalid")
    return errors
