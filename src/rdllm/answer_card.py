"""User-facing answer provenance cards for RDLLM responses."""

from __future__ import annotations

from typing import Any

from rdllm.conformance import (
    source_labels_in_output,
    span_hash_prefixes_in_output,
    verify_event_receipt,
)
from rdllm.models import UsageEvent
from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload
from rdllm.telemetry import verify_trace_exchange
from rdllm.text import stable_hash

ANSWER_PROVENANCE_CARD_VERSION = "rdllm-answer-provenance-card/v1"


def _hashable_card(card: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in card.items()
        if key not in {"card_hash", "signature"}
    }


def _source_entries(event: UsageEvent) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for source in event.source_references:
        entry = {
            "label": source.label,
            "title": source.title,
            "creator_id": source.creator_id,
            "creator_name": source.creator_name,
            "work_id": source.work_id,
            "chunk_id": source.chunk_id,
            "source_uri": source.source_uri,
            "license": source.license,
            "content_hash": source.content_hash,
            "evidence_span_hashes": list(source.evidence_span_hashes),
            "support_score": round(source.output_support, 8),
            "retrieval_score": round(source.retrieval_score, 8),
            "text_match_score": round(source.text_match_score, 8),
            "contribution_weight": str(source.contribution_weight),
        }
        entry["source_entry_hash"] = hash_payload(entry)
        entries.append(entry)
    return entries


def _claim_entries(event: UsageEvent) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for index, claim in enumerate(event.claim_support, start=1):
        entry = {
            "claim_index": index,
            "claim_hash": stable_hash(claim.claim),
            "source_label": claim.source_label,
            "support_score": round(claim.support_score, 8),
            "supported": claim.supported,
            "work_id": claim.work_id,
            "chunk_id": claim.chunk_id,
            "evidence_span_hash": claim.evidence_span_hash,
            "evidence_span_prefix": claim.evidence_span_hash[:12],
            "evidence_start_char": claim.evidence_start_char,
            "evidence_end_char": claim.evidence_end_char,
        }
        entry["claim_entry_hash"] = hash_payload(entry)
        entries.append(entry)
    return entries


def _footer_checks(event: UsageEvent) -> dict[str, Any]:
    footer_labels = source_labels_in_output(event.output)
    expected_labels = [source.label for source in event.source_references]
    omitted_labels = [label for label in expected_labels if label not in footer_labels]
    unexpected_labels = [label for label in footer_labels if label not in expected_labels]
    footer_span_prefixes = span_hash_prefixes_in_output(event.output)
    expected_span_prefixes = [
        claim.evidence_span_hash[:12]
        for claim in event.claim_support
        if claim.supported and claim.evidence_span_hash
    ]
    return {
        "source_labels": footer_labels,
        "expected_source_labels": expected_labels,
        "source_labels_match": footer_labels == expected_labels,
        "omitted_source_labels": omitted_labels,
        "unexpected_source_labels": unexpected_labels,
        "attribution_suppression_detected": bool(omitted_labels),
        "attribution_suppression_count": len(omitted_labels),
        "source_labels_hash": hash_payload(footer_labels),
        "claim_span_prefixes": footer_span_prefixes,
        "expected_claim_span_prefixes": expected_span_prefixes,
        "claim_span_prefixes_match": all(
            prefix in footer_span_prefixes for prefix in expected_span_prefixes
        ),
        "claim_span_prefixes_hash": hash_payload(footer_span_prefixes),
        "sources_section_present": "Sources" in event.output,
        "claim_evidence_section_present": (
            "Claim Evidence" in event.output or not expected_span_prefixes
        ),
    }


def make_answer_provenance_card(
    event: UsageEvent,
    *,
    receipt: dict[str, Any] | None = None,
    trace: dict[str, Any] | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public card that proves the visible answer footer is grounded."""

    source_entries = _source_entries(event)
    claim_entries = _claim_entries(event)
    footer_checks = _footer_checks(event)
    supported_claims = sum(1 for claim in event.claim_support if claim.supported)
    receipt_hash = receipt.get("receipt_hash", "") if receipt else ""
    trace_hash = trace.get("trace_hash", "") if trace else ""
    card = {
        "card_version": ANSWER_PROVENANCE_CARD_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "event": {
            "event_id": event.event_id,
            "event_hash": event.event_hash,
            "answer_hash": stable_hash(event.answer_text or event.output),
            "rendered_output_hash": stable_hash(event.output),
            "receipt_hash": receipt_hash,
            "trace_hash": trace_hash,
        },
        "grounding": {
            "status": event.grounding_report.get("status", ""),
            "quality_verdict": event.grounding_quality.get("verdict", ""),
            "quality_score": event.grounding_quality.get("overall_score", 0.0),
            "attribution_gap_verdict": event.attribution_gap.get("verdict", ""),
            "policy_status": event.grounding_report.get("policy_status", ""),
            "registry_status": event.grounding_report.get("registry_status", ""),
            "source_count": len(event.source_references),
            "claim_count": len(event.claim_support),
            "supported_claim_count": supported_claims,
            "unsupported_claim_count": len(event.claim_support) - supported_claims,
        },
        "sources": source_entries,
        "claims": claim_entries,
        "footer_checks": footer_checks,
        "commitments": {
            "source_root": hash_payload(source_entries),
            "claim_root": hash_payload(claim_entries),
            "footer_checks_hash": hash_payload(footer_checks),
            "rendered_output_hash": stable_hash(event.output),
            "receipt_hash": receipt_hash,
            "trace_hash": trace_hash,
        },
        "verification": {
            "receipt_bound": bool(receipt_hash),
            "trace_bound": bool(trace_hash),
            "sources_match_visible_footer": footer_checks["source_labels_match"],
            "claims_match_visible_footer": footer_checks["claim_span_prefixes_match"],
            "requires_private_prompt": False,
            "requires_private_source_text": False,
            "public_user_can_verify_footer": True,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_quote_text_disclosed": False,
            "claim_text_disclosed": False,
            "evidence_text_disclosed": False,
            "full_receipt_payload_disclosed": False,
        },
    }
    card["card_hash"] = hash_payload(_hashable_card(card))
    card["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_card(card), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return card


def validate_answer_provenance_card_shape(card: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "card_version",
        "issuer",
        "created_at",
        "event",
        "grounding",
        "sources",
        "claims",
        "footer_checks",
        "commitments",
        "verification",
        "privacy",
        "card_hash",
        "signature",
    )
    for key in required:
        if key not in card:
            errors.append(f"missing answer provenance card field: {key}")
    if errors:
        return errors
    if card.get("card_version") != ANSWER_PROVENANCE_CARD_VERSION:
        errors.append("answer provenance card version is unsupported")
    for key in (
        "event_id",
        "event_hash",
        "answer_hash",
        "rendered_output_hash",
        "receipt_hash",
        "trace_hash",
    ):
        if key not in card.get("event", {}):
            errors.append(f"missing answer provenance event field: {key}")
    for key in ("source_root", "claim_root", "footer_checks_hash"):
        if key not in card.get("commitments", {}):
            errors.append(f"missing answer provenance commitment field: {key}")
    return errors


def verify_answer_provenance_card(
    event: UsageEvent,
    card: dict[str, Any],
    *,
    receipt: dict[str, Any] | None = None,
    trace: dict[str, Any] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a public answer card against an event and optional receipt/trace."""

    errors = validate_answer_provenance_card_shape(card)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_card(card))
    if expected_hash != card.get("card_hash"):
        errors.append("answer provenance card hash is not reproducible")

    expected = make_answer_provenance_card(
        event,
        receipt=receipt,
        trace=trace,
        issuer=card.get("issuer", DEFAULT_ISSUER),
        created_at=card.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "event",
        "grounding",
        "sources",
        "claims",
        "footer_checks",
        "commitments",
        "verification",
        "privacy",
    ):
        if expected.get(key) != card.get(key):
            errors.append(f"answer provenance card {key} does not match event")
    if expected.get("card_hash") != card.get("card_hash"):
        errors.append("answer provenance card hash does not match event")

    footer_checks = card.get("footer_checks", {})
    if footer_checks.get("source_labels_match") is not True:
        errors.append("answer provenance card source labels do not match footer")
    if footer_checks.get("claim_span_prefixes_match") is not True:
        errors.append("answer provenance card claim spans do not match footer")
    if card.get("verification", {}).get("public_user_can_verify_footer") is not True:
        errors.append("answer provenance card must be public-user verifiable")

    if receipt:
        receipt_errors = verify_event_receipt(
            event,
            receipt,
            signing_secret=signing_secret,
        )
        errors.extend(f"receipt: {error}" for error in receipt_errors)
        if card.get("event", {}).get("receipt_hash") != receipt.get("receipt_hash"):
            errors.append("answer provenance card receipt hash does not match receipt")

    if trace:
        trace_errors = verify_trace_exchange(trace, event=event, receipt=receipt)
        errors.extend(f"trace: {error}" for error in trace_errors)
        if card.get("event", {}).get("trace_hash") != trace.get("trace_hash"):
            errors.append("answer provenance card trace hash does not match trace")

    if signing_secret:
        signature = card.get("signature", {})
        expected_signature = sign_payload(_hashable_card(card), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("answer provenance card is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("answer provenance card signature is invalid")

    return errors
