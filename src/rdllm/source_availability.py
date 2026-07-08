"""Source availability reports for user-facing RDLLM citation footers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.citation_footer import CITATION_FOOTER_VERSION
from rdllm.engine import RoyaltyDrivenLLM
from rdllm.models import ClaimSupport, SourceReference, UsageEvent
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash

SOURCE_AVAILABILITY_VERSION = "rdllm-source-availability-report/v1"
SOURCE_AVAILABILITY_SCHEMA = "docs/schemas/source_availability_report.schema.json"
SOURCE_AVAILABILITY_POLICY_VERSION = "rdllm-source-availability-policy/v1"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L55"


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


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_source_availability_snapshots(path: str | Path) -> list[dict[str, Any]]:
    """Load deterministic source-resolution snapshots from JSON."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [dict(item) for item in data]
    return [dict(item) for item in data.get("snapshots", [])]


def _body_text(snapshot: dict[str, Any]) -> str:
    for key in ("body_text", "source_text", "content"):
        value = snapshot.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _normalized_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    body = _body_text(snapshot)
    declared_content_hash = str(snapshot.get("content_hash", ""))
    computed_content_hash = stable_hash(body) if body else declared_content_hash
    content_hash = declared_content_hash or computed_content_hash
    row = {
        "source_uri": str(snapshot.get("source_uri", "")),
        "canonical_uri": str(snapshot.get("canonical_uri", snapshot.get("source_uri", ""))),
        "archived_uri": str(snapshot.get("archived_uri", "")),
        "retrieved_at": str(snapshot.get("retrieved_at", "")),
        "http_status": _int(snapshot.get("http_status")),
        "media_type": str(snapshot.get("media_type", "")),
        "retrieval_method": str(snapshot.get("retrieval_method", "provider_snapshot")),
        "resolver_id": str(snapshot.get("resolver_id", "")),
        "work_id": str(snapshot.get("work_id", "")),
        "chunk_id": str(snapshot.get("chunk_id", "")),
        "content_hash": content_hash,
        "body_hash": computed_content_hash if body else str(snapshot.get("body_hash", "")),
        "declared_content_hash_matches_body": (
            not body or not declared_content_hash or declared_content_hash == computed_content_hash
        ),
        "evidence_span_hashes": sorted(
            str(item) for item in snapshot.get("evidence_span_hashes", [])
        ),
    }
    row["snapshot_hash"] = hash_payload(row)
    return row


def _snapshot_maps(
    snapshots: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_uri: dict[str, dict[str, Any]] = {}
    by_chunk: dict[str, dict[str, Any]] = {}
    by_work: dict[str, dict[str, Any]] = {}
    for snapshot in snapshots:
        normalized = _normalized_snapshot(snapshot)
        for uri_key in ("source_uri", "canonical_uri", "archived_uri"):
            uri = normalized.get(uri_key)
            if uri:
                by_uri[str(uri)] = normalized
        if normalized.get("chunk_id"):
            by_chunk[str(normalized["chunk_id"])] = normalized
        if normalized.get("work_id"):
            by_work[str(normalized["work_id"])] = normalized
    return by_uri, by_chunk, by_work


def _raw_snapshot_for_source(
    source: SourceReference,
    snapshots: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for snapshot in snapshots:
        if snapshot.get("source_uri") == source.source_uri:
            return snapshot
        if snapshot.get("canonical_uri") == source.source_uri:
            return snapshot
        if snapshot.get("chunk_id") == source.chunk_id:
            return snapshot
        if snapshot.get("work_id") == source.work_id:
            return snapshot
    return None


def _find_snapshot(
    source: SourceReference,
    maps: tuple[
        dict[str, dict[str, Any]],
        dict[str, dict[str, Any]],
        dict[str, dict[str, Any]],
    ],
) -> dict[str, Any] | None:
    by_uri, by_chunk, by_work = maps
    return (
        by_uri.get(source.source_uri)
        or by_chunk.get(source.chunk_id)
        or by_work.get(source.work_id)
    )


def _claims_by_source(event: UsageEvent) -> dict[str, list[ClaimSupport]]:
    claims: dict[str, list[ClaimSupport]] = {}
    for claim in event.claim_support:
        if claim.supported and claim.source_label:
            claims.setdefault(claim.source_label, []).append(claim)
    return claims


def _artifact_bindings(
    *,
    answer_card: dict[str, Any] | None,
    source_verification_report: dict[str, Any] | None,
    citation_footer_contract: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "answer_card_hash": _declared_hash(answer_card),
        "source_verification_report_hash": _declared_hash(source_verification_report),
        "citation_footer_contract_hash": _declared_hash(citation_footer_contract),
        "citation_footer_version": (
            citation_footer_contract.get("contract_version", "")
            if citation_footer_contract
            else ""
        ),
        "answer_card_bound": bool(answer_card),
        "source_verification_bound": bool(source_verification_report),
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


def _label_set_from_footer_contract(contract: dict[str, Any] | None) -> set[str]:
    if not contract:
        return set()
    return {
        str(source.get("label", ""))
        for source in contract.get("sources", [])
        if source.get("label")
    }


def _source_verification_by_label(report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not report:
        return {}
    return {
        str(source.get("label", "")): source
        for source in report.get("sources", [])
        if source.get("label")
    }


def _claim_span_coverage(
    *,
    raw_snapshot: dict[str, Any] | None,
    normalized_snapshot: dict[str, Any] | None,
    claims: list[ClaimSupport],
) -> tuple[bool, list[str]]:
    if not claims:
        return True, []
    evidence_hashes = set(
        normalized_snapshot.get("evidence_span_hashes", [])
        if normalized_snapshot
        else []
    )
    body = _body_text(raw_snapshot or {})
    covered: list[str] = []
    for claim in claims:
        span_hash = claim.evidence_span_hash
        if not span_hash:
            continue
        present_by_body = bool(
            body
            and claim.evidence_text
            and claim.evidence_text in body
            and stable_hash(claim.evidence_text) == span_hash
        )
        present_by_hash = span_hash in evidence_hashes
        if present_by_body or present_by_hash:
            covered.append(span_hash[:12])
    return len(covered) == len([claim for claim in claims if claim.evidence_span_hash]), covered


def _source_rows(
    *,
    event: UsageEvent,
    engine: RoyaltyDrivenLLM,
    snapshots: list[dict[str, Any]],
    answer_card: dict[str, Any] | None,
    source_verification_report: dict[str, Any] | None,
    citation_footer_contract: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    maps = _snapshot_maps(snapshots)
    claims_by_label = _claims_by_source(event)
    answer_card_labels = _label_set_from_answer_card(answer_card)
    footer_labels = _label_set_from_footer_contract(citation_footer_contract)
    source_report_by_label = _source_verification_by_label(source_verification_report)
    rows: list[dict[str, Any]] = []

    for index, source in enumerate(event.source_references, start=1):
        snapshot = _find_snapshot(source, maps)
        raw_snapshot = _raw_snapshot_for_source(source, snapshots)
        chunk = engine.chunk_by_id.get(source.chunk_id)
        source_report_row = source_report_by_label.get(source.label, {})
        source_claims = claims_by_label.get(source.label, [])
        span_coverage, covered_span_prefixes = _claim_span_coverage(
            raw_snapshot=raw_snapshot,
            normalized_snapshot=snapshot,
            claims=source_claims,
        )
        reachable = bool(snapshot and 200 <= int(snapshot.get("http_status", 0)) <= 299)
        archived = bool(snapshot and snapshot.get("archived_uri"))
        registry_hash = chunk.content_hash if chunk else ""
        content_hash_matches_registry = bool(
            chunk
            and source.content_hash == registry_hash
            and snapshot
            and snapshot.get("content_hash") == registry_hash
            and snapshot.get("declared_content_hash_matches_body") is True
        )
        footer_bound = source.label in answer_card_labels and source.label in footer_labels
        materialized = source_report_row.get("materialized") is True
        inspectable = bool(
            snapshot
            and (reachable or archived)
            and content_hash_matches_registry
            and span_coverage
            and footer_bound
            and materialized
        )
        if inspectable:
            status = "inspectable"
        elif snapshot and archived:
            status = "archived_but_unverified"
        elif snapshot and reachable:
            status = "reachable_but_unverified"
        else:
            status = "unavailable"
        row = {
            "display_order": index,
            "label": source.label,
            "title": source.title,
            "creator_id": source.creator_id,
            "work_id": source.work_id,
            "chunk_id": source.chunk_id,
            "source_uri": source.source_uri,
            "canonical_uri": snapshot.get("canonical_uri", "") if snapshot else "",
            "archived_uri": snapshot.get("archived_uri", "") if snapshot else "",
            "retrieved_at": snapshot.get("retrieved_at", "") if snapshot else "",
            "http_status": int(snapshot.get("http_status", 0)) if snapshot else 0,
            "media_type": snapshot.get("media_type", "") if snapshot else "",
            "retrieval_method": snapshot.get("retrieval_method", "") if snapshot else "",
            "resolver_id": snapshot.get("resolver_id", "") if snapshot else "",
            "content_hash": source.content_hash,
            "snapshot_content_hash": snapshot.get("content_hash", "") if snapshot else "",
            "snapshot_hash": snapshot.get("snapshot_hash", "") if snapshot else "",
            "source_report_materialized": materialized,
            "answer_card_source_bound": source.label in answer_card_labels,
            "citation_footer_source_bound": source.label in footer_labels,
            "footer_bound": footer_bound,
            "reachable": reachable,
            "archived": archived,
            "content_hash_matches_registry": content_hash_matches_registry,
            "claim_span_coverage": span_coverage,
            "claim_span_prefixes": [
                claim.evidence_span_hash[:12]
                for claim in source_claims
                if claim.evidence_span_hash
            ],
            "covered_claim_span_prefixes": covered_span_prefixes,
            "inspectable": inspectable,
            "resolution_status": status,
        }
        row["availability_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _issues(rows: list[dict[str, Any]], bindings: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not bindings.get("answer_card_bound"):
        issues.append("answer provenance card is not bound")
    if not bindings.get("source_verification_bound"):
        issues.append("source verification report is not bound")
    if not bindings.get("citation_footer_bound"):
        issues.append("citation footer contract is not bound")
    if (
        bindings.get("citation_footer_contract_hash")
        and bindings.get("citation_footer_version") != CITATION_FOOTER_VERSION
    ):
        issues.append("citation footer contract version is unsupported")
    for row in rows:
        label = row["label"]
        if not row["snapshot_hash"]:
            issues.append(f"source {label} has no availability snapshot")
        if not (row["reachable"] or row["archived"]):
            issues.append(f"source {label} is neither reachable nor archived")
        if not row["content_hash_matches_registry"]:
            issues.append(f"source {label} snapshot content does not match registry")
        if not row["claim_span_coverage"]:
            issues.append(f"source {label} does not cover all cited claim spans")
        if not row["footer_bound"]:
            issues.append(f"source {label} is not bound to the visible footer")
        if not row["source_report_materialized"]:
            issues.append(f"source {label} is not materialized by source verification")
    return issues


def make_source_availability_report(
    event: UsageEvent,
    engine: RoyaltyDrivenLLM,
    snapshots: list[dict[str, Any]],
    *,
    answer_card: dict[str, Any] | None = None,
    source_verification_report: dict[str, Any] | None = None,
    citation_footer_contract: dict[str, Any] | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a report proving user-visible citation sources remain inspectable."""

    normalized_snapshots = sorted(
        (_normalized_snapshot(snapshot) for snapshot in snapshots),
        key=lambda item: (
            str(item.get("source_uri", "")),
            str(item.get("chunk_id", "")),
            str(item.get("work_id", "")),
        ),
    )
    bindings = _artifact_bindings(
        answer_card=answer_card,
        source_verification_report=source_verification_report,
        citation_footer_contract=citation_footer_contract,
    )
    rows = _source_rows(
        event=event,
        engine=engine,
        snapshots=snapshots,
        answer_card=answer_card,
        source_verification_report=source_verification_report,
        citation_footer_contract=citation_footer_contract,
    )
    issue_list = _issues(rows, bindings)
    report = {
        "report_version": SOURCE_AVAILABILITY_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": {
            "profile": SOURCE_AVAILABILITY_POLICY_VERSION,
            "requires_reachable_or_archived_source": True,
            "requires_registered_content_hash_match": True,
            "requires_claim_span_coverage": True,
            "requires_footer_binding": True,
            "requires_source_materialization": True,
        },
        "event": {
            "event_id": event.event_id,
            "event_hash": event.event_hash,
            "rendered_output_hash": stable_hash(event.output),
            "answer_hash": stable_hash(event.answer_text or event.output),
        },
        "artifact_bindings": bindings,
        "summary": {
            "status": "verified" if not issue_list else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "source_count": len(rows),
            "snapshot_count": len(normalized_snapshots),
            "inspectable_source_count": sum(1 for row in rows if row["inspectable"]),
            "reachable_source_count": sum(1 for row in rows if row["reachable"]),
            "archived_source_count": sum(1 for row in rows if row["archived"]),
            "unavailable_source_count": sum(
                1 for row in rows if not (row["reachable"] or row["archived"])
            ),
            "footer_bound_source_count": sum(1 for row in rows if row["footer_bound"]),
            "content_hash_match_count": sum(
                1 for row in rows if row["content_hash_matches_registry"]
            ),
            "claim_span_coverage_count": sum(
                1 for row in rows if row["claim_span_coverage"]
            ),
            "all_public_sources_inspectable": bool(rows)
            and all(row["inspectable"] for row in rows),
            "issue_count": len(issue_list),
        },
        "sources": rows,
        "snapshot_commitments": [
            {
                "source_uri": snapshot["source_uri"],
                "canonical_uri": snapshot["canonical_uri"],
                "archived_uri": snapshot["archived_uri"],
                "retrieved_at": snapshot["retrieved_at"],
                "http_status": snapshot["http_status"],
                "media_type": snapshot["media_type"],
                "content_hash": snapshot["content_hash"],
                "snapshot_hash": snapshot["snapshot_hash"],
            }
            for snapshot in normalized_snapshots
        ],
        "commitments": {
            "source_availability_root": hash_payload(rows),
            "snapshot_root": hash_payload(normalized_snapshots),
            "event_hash": event.event_hash,
            "artifact_binding_root": hash_payload(bindings),
            "issue_root": hash_payload(issue_list),
        },
        "schemas": {
            "source_availability_report": SOURCE_AVAILABILITY_SCHEMA,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "claim_evidence_text_disclosed": False,
            "raw_snapshot_body_disclosed": False,
            "full_snapshot_payload_disclosed": False,
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


def validate_source_availability_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "event",
        "artifact_bindings",
        "summary",
        "sources",
        "snapshot_commitments",
        "commitments",
        "schemas",
        "privacy",
        "issues",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing source availability report field: {key}")
    if errors:
        return errors
    if report.get("report_version") != SOURCE_AVAILABILITY_VERSION:
        errors.append("source availability report version is unsupported")
    if report.get("policy", {}).get("profile") != SOURCE_AVAILABILITY_POLICY_VERSION:
        errors.append("source availability policy profile is unsupported")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("source availability target certification level is unsupported")
    for key in ("event_id", "event_hash", "rendered_output_hash", "answer_hash"):
        if key not in report.get("event", {}):
            errors.append(f"missing source availability event field: {key}")
    for key in (
        "source_availability_root",
        "snapshot_root",
        "event_hash",
        "artifact_binding_root",
        "issue_root",
    ):
        if key not in report.get("commitments", {}):
            errors.append(f"missing source availability commitment field: {key}")
    return errors


def verify_source_availability_report(
    report: dict[str, Any],
    event: UsageEvent,
    engine: RoyaltyDrivenLLM,
    snapshots: list[dict[str, Any]],
    *,
    answer_card: dict[str, Any] | None = None,
    source_verification_report: dict[str, Any] | None = None,
    citation_footer_contract: dict[str, Any] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify source availability against private snapshots."""

    errors = validate_source_availability_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("source availability report hash is not reproducible")

    expected = make_source_availability_report(
        event,
        engine,
        snapshots,
        answer_card=answer_card,
        source_verification_report=source_verification_report,
        citation_footer_contract=citation_footer_contract,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "event",
        "artifact_bindings",
        "summary",
        "sources",
        "snapshot_commitments",
        "commitments",
        "schemas",
        "privacy",
        "issues",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"source availability report {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("source availability report hash does not match replay")

    if report.get("summary", {}).get("status") != "verified":
        errors.append("source availability report status is not verified")
    if report.get("summary", {}).get("all_public_sources_inspectable") is not True:
        errors.append("source availability report has uninspectable public sources")
    if report.get("issues"):
        errors.append("source availability report contains issues")

    rendered = canonical_json(report)
    if '"body_text"' in rendered or '"source_text"' in rendered or '"content"' in rendered:
        errors.append("source availability report leaks raw snapshot body")
    for chunk in engine.chunks:
        if len(chunk.text.strip()) >= 16 and chunk.text in rendered:
            errors.append("source availability report leaks source text")
            break
    for claim in event.claim_support:
        if (
            claim.evidence_text
            and len(claim.evidence_text.strip()) >= 16
            and claim.evidence_text in rendered
        ):
            errors.append("source availability report leaks claim evidence text")
            break

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("source availability report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("source availability report signature is invalid")
    return errors
