"""Source materialization reports for cited RDLLM answers."""

from __future__ import annotations

from typing import Any

from rdllm.conformance import source_labels_in_output, span_hash_prefixes_in_output
from rdllm.engine import RoyaltyDrivenLLM
from rdllm.models import UsageEvent
from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash

SOURCE_VERIFICATION_VERSION = "rdllm-source-verification-report/v1"


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _registered_chunk_root(engine: RoyaltyDrivenLLM) -> str:
    return hash_payload(
        [
            {
                "chunk_id": chunk.chunk_id,
                "work_id": chunk.work_id,
                "creator_id": chunk.creator_id,
                "title": chunk.title,
                "source_uri": chunk.source_uri,
                "content_hash": chunk.content_hash,
                "license": chunk.license,
            }
            for chunk in sorted(engine.chunks, key=lambda item: item.chunk_id)
        ]
    )


def _source_entries(event: UsageEvent, engine: RoyaltyDrivenLLM) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for source in event.source_references:
        chunk = engine.chunk_by_id.get(source.chunk_id)
        content_hash_reproducible = (
            bool(chunk) and stable_hash(chunk.text) == source.content_hash
        )
        entry = {
            "label": source.label,
            "work_id": source.work_id,
            "chunk_id": source.chunk_id,
            "creator_id": source.creator_id,
            "title": source.title,
            "source_uri": source.source_uri,
            "license": source.license,
            "content_hash": source.content_hash,
            "registered_chunk_found": chunk is not None,
            "registered_content_hash": chunk.content_hash if chunk else "",
            "content_hash_matches_registry": bool(chunk)
            and chunk.content_hash == source.content_hash,
            "content_hash_reproducible": content_hash_reproducible,
            "work_identity_matches_registry": bool(chunk)
            and chunk.work_id == source.work_id,
            "creator_matches_registry": bool(chunk)
            and chunk.creator_id == source.creator_id,
            "title_matches_registry": bool(chunk) and chunk.title == source.title,
            "source_uri_matches_registry": bool(chunk)
            and chunk.source_uri == source.source_uri,
            "license_matches_registry": bool(chunk) and chunk.license == source.license,
            "source_uri_present": bool(source.source_uri),
            "quote_hash": stable_hash(source.quote) if source.quote else "",
            "quote_present_in_registered_chunk": bool(
                chunk and source.quote and source.quote in chunk.text
            ),
            "evidence_span_hashes": list(source.evidence_span_hashes),
        }
        entry["materialized"] = all(
            bool(entry[key])
            for key in (
                "registered_chunk_found",
                "content_hash_matches_registry",
                "content_hash_reproducible",
                "work_identity_matches_registry",
                "creator_matches_registry",
                "title_matches_registry",
                "source_uri_matches_registry",
                "license_matches_registry",
                "source_uri_present",
                "quote_present_in_registered_chunk",
            )
        )
        entry["source_entry_hash"] = hash_payload(entry)
        entries.append(entry)
    return entries


def _claim_entries(event: UsageEvent, engine: RoyaltyDrivenLLM) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    source_by_label = {
        source.label: source for source in event.source_references
    }
    footer_labels = set(source_labels_in_output(event.output))
    footer_span_prefixes = set(span_hash_prefixes_in_output(event.output))

    for index, claim in enumerate(event.claim_support, start=1):
        source = source_by_label.get(claim.source_label)
        chunk = engine.chunk_by_id.get(claim.chunk_id)
        offset_text = ""
        if (
            chunk
            and claim.evidence_start_char >= 0
            and claim.evidence_end_char >= claim.evidence_start_char
        ):
            offset_text = chunk.text[
                claim.evidence_start_char : claim.evidence_end_char
            ]
        evidence_hash_reproducible = (
            bool(claim.evidence_text)
            and stable_hash(claim.evidence_text) == claim.evidence_span_hash
        )
        evidence_offsets_match = (
            bool(offset_text)
            and bool(claim.evidence_text)
            and offset_text == claim.evidence_text
        )
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
            "registered_chunk_found": chunk is not None,
            "source_label_resolves": source is not None,
            "source_chunk_matches_claim": bool(source)
            and source.chunk_id == claim.chunk_id,
            "evidence_hash_reproducible": evidence_hash_reproducible,
            "evidence_span_in_registered_chunk": bool(
                chunk and claim.evidence_text and claim.evidence_text in chunk.text
            ),
            "evidence_offsets_match_registered_chunk": evidence_offsets_match,
            "visible_footer_source_label": claim.source_label in footer_labels,
            "visible_footer_span_prefix": (
                bool(claim.evidence_span_hash)
                and claim.evidence_span_hash[:12] in footer_span_prefixes
            ),
        }
        if claim.supported:
            entry["materialized"] = all(
                bool(entry[key])
                for key in (
                    "registered_chunk_found",
                    "source_label_resolves",
                    "source_chunk_matches_claim",
                    "evidence_hash_reproducible",
                    "evidence_span_in_registered_chunk",
                    "evidence_offsets_match_registered_chunk",
                    "visible_footer_source_label",
                    "visible_footer_span_prefix",
                )
            )
        else:
            entry["materialized"] = False
        entry["claim_entry_hash"] = hash_payload(entry)
        entries.append(entry)
    return entries


def _answer_card_binding(
    event: UsageEvent,
    answer_card: dict[str, Any] | None,
) -> dict[str, Any]:
    if not answer_card:
        return {
            "answer_card_hash": "",
            "answer_card_bound": False,
            "event_id_matches_card": False,
            "event_hash_matches_card": False,
            "rendered_output_hash_matches_card": False,
        }
    card_event = answer_card.get("event", {})
    return {
        "answer_card_hash": answer_card.get("card_hash", ""),
        "answer_card_bound": (
            card_event.get("event_id") == event.event_id
            and card_event.get("event_hash") == event.event_hash
            and card_event.get("rendered_output_hash") == stable_hash(event.output)
        ),
        "event_id_matches_card": card_event.get("event_id") == event.event_id,
        "event_hash_matches_card": card_event.get("event_hash") == event.event_hash,
        "rendered_output_hash_matches_card": (
            card_event.get("rendered_output_hash") == stable_hash(event.output)
        ),
    }


def _issues(
    sources: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    binding: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    for source in sources:
        if not source["materialized"]:
            issues.append(f"source {source['label']} is not materialized")
    for claim in claims:
        if claim["supported"] and not claim["materialized"]:
            issues.append(f"claim C{claim['claim_index']} is not materialized")
    if binding["answer_card_hash"] and not binding["answer_card_bound"]:
        issues.append("answer card does not bind to the event")
    return issues


def make_source_verification_report(
    event: UsageEvent,
    engine: RoyaltyDrivenLLM,
    *,
    answer_card: dict[str, Any] | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public report proving cited sources resolve to registered content."""

    sources = _source_entries(event, engine)
    claims = _claim_entries(event, engine)
    binding = _answer_card_binding(event, answer_card)
    issue_list = _issues(sources, claims, binding)
    footer_labels = source_labels_in_output(event.output)
    footer_span_prefixes = span_hash_prefixes_in_output(event.output)
    source_count = len(sources)
    supported_claim_count = sum(1 for claim in claims if claim["supported"])
    report = {
        "report_version": SOURCE_VERIFICATION_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "event": {
            "event_id": event.event_id,
            "event_hash": event.event_hash,
            "rendered_output_hash": stable_hash(event.output),
            "answer_hash": stable_hash(event.answer_text or event.output),
        },
        "answer_card": binding,
        "summary": {
            "status": "verified" if not issue_list else "failed",
            "source_count": source_count,
            "claim_count": len(claims),
            "supported_claim_count": supported_claim_count,
            "materialized_source_count": sum(
                1 for source in sources if source["materialized"]
            ),
            "materialized_supported_claim_count": sum(
                1
                for claim in claims
                if claim["supported"] and claim["materialized"]
            ),
            "unresolved_source_count": sum(
                1 for source in sources if not source["materialized"]
            ),
            "unverified_supported_claim_count": sum(
                1
                for claim in claims
                if claim["supported"] and not claim["materialized"]
            ),
            "all_sources_materialized": all(
                source["materialized"] for source in sources
            )
            if sources
            else True,
            "all_supported_claims_materialized": all(
                claim["materialized"] for claim in claims if claim["supported"]
            )
            if supported_claim_count
            else True,
            "visible_footer_source_count": len(footer_labels),
            "visible_footer_span_count": len(footer_span_prefixes),
            "answer_card_bound": binding["answer_card_bound"],
        },
        "sources": sources,
        "claims": claims,
        "commitments": {
            "registered_chunk_root": _registered_chunk_root(engine),
            "source_materialization_root": hash_payload(sources),
            "claim_materialization_root": hash_payload(claims),
            "visible_footer_label_root": hash_payload(footer_labels),
            "visible_footer_span_root": hash_payload(footer_span_prefixes),
            "answer_card_hash": binding["answer_card_hash"],
        },
        "verification": {
            "registered_source_corpus_checked": True,
            "source_hashes_recomputed_from_registered_text": True,
            "claim_evidence_hashes_recomputed_from_registered_text": True,
            "visible_footer_checked": True,
            "answer_card_bound": binding["answer_card_bound"],
            "requires_private_prompt": False,
            "requires_public_source_text_in_report": False,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "source_quote_text_disclosed": False,
            "claim_text_disclosed": False,
            "claim_evidence_text_disclosed": False,
            "report_uses_hashes_and_booleans": True,
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


def validate_source_verification_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "event",
        "answer_card",
        "summary",
        "sources",
        "claims",
        "commitments",
        "verification",
        "privacy",
        "issues",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing source verification report field: {key}")
    if errors:
        return errors
    if report.get("report_version") != SOURCE_VERIFICATION_VERSION:
        errors.append("source verification report version is unsupported")
    for key in ("event_id", "event_hash", "rendered_output_hash", "answer_hash"):
        if key not in report.get("event", {}):
            errors.append(f"missing source verification event field: {key}")
    for key in (
        "registered_chunk_root",
        "source_materialization_root",
        "claim_materialization_root",
    ):
        if key not in report.get("commitments", {}):
            errors.append(f"missing source verification commitment field: {key}")
    return errors


def verify_source_verification_report(
    event: UsageEvent,
    engine: RoyaltyDrivenLLM,
    report: dict[str, Any],
    *,
    answer_card: dict[str, Any] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a source materialization report against an event and corpus."""

    errors = validate_source_verification_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("source verification report hash is not reproducible")

    expected = make_source_verification_report(
        event,
        engine,
        answer_card=answer_card,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "event",
        "answer_card",
        "summary",
        "sources",
        "claims",
        "commitments",
        "verification",
        "privacy",
        "issues",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"source verification report {key} does not match event")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("source verification report hash does not match corpus")

    summary = report.get("summary", {})
    if summary.get("status") != "verified":
        errors.append("source verification report status is not verified")
    if summary.get("all_sources_materialized") is not True:
        errors.append("source verification report has unresolved sources")
    if summary.get("all_supported_claims_materialized") is not True:
        errors.append("source verification report has unmaterialized claims")
    if report.get("issues"):
        errors.append("source verification report contains issues")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("source verification report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("source verification report signature is invalid")

    return errors
