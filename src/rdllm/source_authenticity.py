"""Source-authenticity and poisoning-resilience reports for RDLLM sources."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.license_contract import verify_creator_license_contract_public
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.source_availability import validate_source_availability_report_shape
from rdllm.source_boundary import validate_source_boundary_report_shape
from rdllm.source_confidence import validate_source_confidence_report_shape

SOURCE_AUTHENTICITY_VERSION = "rdllm-source-authenticity-report/v1"
SOURCE_AUTHENTICITY_SCHEMA = "docs/schemas/source_authenticity_report.schema.json"
SOURCE_AUTHENTICITY_POLICY_VERSION = "rdllm-source-authenticity-policy/v1"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L64"

MAX_SOURCE_FARM_RISK = 0.20
MAX_POISONING_RISK = 0.20
MIN_DOMAIN_REPUTATION = 0.60
MIN_CONTENT_STABILITY = 0.75

DECLARED_HASH_FIELDS = (
    "report_hash",
    "contract_hash",
    "card_hash",
    "envelope_hash",
    "trace_hash",
    "receipt_hash",
    "summary_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "output",
    "answer_text",
    "source_text",
    "body_text",
    "content",
    "evidence_text",
    "matched_text",
    "quote",
    "private_trace",
    "hidden_state",
    "token_logits",
    "customer_email",
    "bank_account",
    "account_number",
    "tax_id",
    "payout_account",
}


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in artifact.items()
        if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
    }


def _declared_hash(artifact: dict[str, Any] | None) -> str:
    if not artifact:
        return ""
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(artifact)


def _artifact_hash_is_reproducible(artifact: dict[str, Any] | None) -> bool:
    if not artifact:
        return False
    for field in DECLARED_HASH_FIELDS:
        if artifact.get(field):
            if field == "receipt_hash" and isinstance(artifact.get("payload"), dict):
                return hash_payload(artifact["payload"]) == artifact[field]
            return hash_payload(_hashable_artifact(artifact)) == artifact[field]
    return True


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}" if path else f"/{key}"
            if key in PRIVATE_FIELD_NAMES:
                findings.append(child_path)
            findings.extend(_contains_private_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_contains_private_fields(child, f"{path}/{index}"))
    return findings


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_source_authenticity_signals(path: str | Path) -> list[dict[str, Any]]:
    """Load signed/trusted origin and poisoning-risk signals from JSON."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [dict(item) for item in data]
    return [dict(item) for item in data.get("signals", [])]


def _normalized_signal(signal: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "work_id": str(signal.get("work_id", "")),
        "chunk_id": str(signal.get("chunk_id", "")),
        "content_hash": str(signal.get("content_hash", "")),
        "origin_evidence_id": str(signal.get("origin_evidence_id", "")),
        "origin_evidence_type": str(signal.get("origin_evidence_type", "")),
        "origin_evidence_hash": str(signal.get("origin_evidence_hash", "")),
        "origin_registry_entry_hash": str(
            signal.get("origin_registry_entry_hash", "")
        ),
        "issuer": str(signal.get("issuer", "")),
        "signature_algorithm": str(signal.get("signature_algorithm", "")),
        "signature_verified": signal.get("signature_verified") is True,
        "issuer_trusted": signal.get("issuer_trusted") is True,
        "first_publication_at": str(signal.get("first_publication_at", "")),
        "human_origin_attested": signal.get("human_origin_attested") is True,
        "ai_generated_disclosed": signal.get("ai_generated_disclosed") is True,
        "synthetic_source": signal.get("synthetic_source") is True,
        "source_farm_risk_score": round(_float(signal.get("source_farm_risk_score")), 8),
        "poisoning_risk_score": round(_float(signal.get("poisoning_risk_score")), 8),
        "domain_reputation_score": round(
            _float(signal.get("domain_reputation_score")),
            8,
        ),
        "citation_gaming_signal_count": _int(
            signal.get("citation_gaming_signal_count")
        ),
        "cross_archive_consensus": signal.get("cross_archive_consensus") is True,
        "content_stability_score": round(
            _float(signal.get("content_stability_score"), 1.0),
            8,
        ),
    }
    normalized["authenticity_signal_hash"] = hash_payload(normalized)
    return normalized


def _signal_maps(
    signals: list[dict[str, Any]],
) -> tuple[
    dict[tuple[str, str, str], dict[str, Any]],
    dict[tuple[str, str], dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    by_exact: dict[tuple[str, str, str], dict[str, Any]] = {}
    by_chunk: dict[tuple[str, str], dict[str, Any]] = {}
    by_work: dict[str, dict[str, Any]] = {}
    for signal in signals:
        normalized = _normalized_signal(signal)
        work_id = normalized["work_id"]
        chunk_id = normalized["chunk_id"]
        content_hash = normalized["content_hash"]
        if work_id and chunk_id and content_hash:
            by_exact[(work_id, chunk_id, content_hash)] = normalized
        if work_id and chunk_id:
            by_chunk[(work_id, chunk_id)] = normalized
        if work_id:
            by_work[work_id] = normalized
    return by_exact, by_chunk, by_work


def _signal_for_source(
    row: dict[str, Any],
    maps: tuple[
        dict[tuple[str, str, str], dict[str, Any]],
        dict[tuple[str, str], dict[str, Any]],
        dict[str, dict[str, Any]],
    ],
) -> dict[str, Any] | None:
    by_exact, by_chunk, by_work = maps
    work_id = str(row.get("work_id", ""))
    chunk_id = str(row.get("chunk_id", ""))
    content_hash = str(row.get("content_hash", ""))
    return (
        by_exact.get((work_id, chunk_id, content_hash))
        or by_chunk.get((work_id, chunk_id))
        or by_work.get(work_id)
    )


def _availability_rows(report: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in report.get("sources", []):
        rows[
            (
                str(row.get("work_id", "")),
                str(row.get("chunk_id", "")),
                str(row.get("content_hash", "")),
            )
        ] = row
    return rows


def _boundary_rows(report: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in report.get("source_boundary_rows", []):
        rows[
            (
                str(row.get("work_id", "")),
                str(row.get("chunk_id", "")),
                str(row.get("content_hash", "")),
            )
        ] = row
    return rows


def _license_terms(contract: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    terms: dict[tuple[str, str], dict[str, Any]] = {}
    for term in contract.get("terms", []):
        terms[
            (
                str(term.get("work_id", "")),
                str(term.get("content_hash", "")),
            )
        ] = term
    return terms


def _artifact_bindings(
    *,
    source_availability_report: dict[str, Any],
    source_boundary_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
    source_confidence_report: dict[str, Any] | None,
) -> dict[str, Any]:
    availability_event = source_availability_report.get("event", {})
    boundary_event = source_boundary_report.get("event", {})
    return {
        "source_availability_report_hash": _declared_hash(
            source_availability_report
        ),
        "source_boundary_report_hash": _declared_hash(source_boundary_report),
        "creator_license_contract_hash": _declared_hash(creator_license_contract),
        "source_confidence_report_hash": _declared_hash(source_confidence_report),
        "source_availability_bound": bool(source_availability_report),
        "source_boundary_bound": bool(source_boundary_report),
        "creator_license_contract_bound": bool(creator_license_contract),
        "source_confidence_bound": bool(source_confidence_report),
        "availability_boundary_event_match": (
            availability_event.get("event_id") == boundary_event.get("event_id")
            and availability_event.get("event_hash") == boundary_event.get("event_hash")
            and availability_event.get("rendered_output_hash")
            == boundary_event.get("rendered_output_hash")
            and availability_event.get("answer_hash")
            == boundary_event.get("answer_hash")
        ),
    }


def _artifact_status(
    *,
    source_availability_report: dict[str, Any],
    source_boundary_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
    source_confidence_report: dict[str, Any] | None,
    signing_secret: str | None,
) -> dict[str, Any]:
    contract_errors = verify_creator_license_contract_public(
        creator_license_contract,
        signing_secret=signing_secret,
    )
    confidence_errors = (
        validate_source_confidence_report_shape(source_confidence_report)
        if source_confidence_report
        else []
    )
    return {
        "source_availability_shape_valid": not validate_source_availability_report_shape(
            source_availability_report
        ),
        "source_availability_hash_reproducible": _artifact_hash_is_reproducible(
            source_availability_report
        ),
        "source_availability_status_verified": source_availability_report.get(
            "summary", {}
        ).get("status")
        == "verified",
        "source_boundary_shape_valid": not validate_source_boundary_report_shape(
            source_boundary_report
        ),
        "source_boundary_hash_reproducible": _artifact_hash_is_reproducible(
            source_boundary_report
        ),
        "source_boundary_status_verified": source_boundary_report.get("summary", {}).get(
            "status"
        )
        == "verified",
        "creator_license_contract_public_verified": not contract_errors,
        "creator_license_contract_errors": contract_errors,
        "creator_license_contract_status_ready": creator_license_contract.get(
            "summary", {}
        ).get("status")
        == "ready",
        "source_confidence_shape_valid": not confidence_errors,
        "source_confidence_status_verified": (
            not source_confidence_report
            or source_confidence_report.get("summary", {}).get("status")
            == "verified"
        ),
        "source_confidence_errors": confidence_errors,
    }


def _source_status(row: dict[str, Any]) -> str:
    if row["source_authenticity_verified"]:
        return "verified_human_origin"
    if not row["authenticity_signal_present"]:
        return "unverified_origin"
    if (
        not row["source_farm_risk_below_threshold"]
        or not row["poisoning_risk_below_threshold"]
        or row["citation_gaming_signal_count"] > 0
    ):
        return "quarantine_high_risk"
    if row["synthetic_source"] or row["ai_generated_disclosed"]:
        return "escrow_synthetic_or_ai_generated"
    return "failed_integrity_checks"


def _source_rows(
    *,
    source_availability_report: dict[str, Any],
    source_boundary_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
    source_confidence_report: dict[str, Any] | None,
    source_authenticity_signals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    boundary_by_key = _boundary_rows(source_boundary_report)
    terms_by_key = _license_terms(creator_license_contract)
    signal_maps = _signal_maps(source_authenticity_signals)
    confidence_sources = {
        str(source.get("label", "")): source
        for source in (source_confidence_report or {}).get("sources", [])
        if source.get("label")
    }
    rows: list[dict[str, Any]] = []
    for source in sorted(
        source_availability_report.get("sources", []),
        key=lambda item: (
            int(item.get("display_order", 0) or 0),
            str(item.get("label", "")),
        ),
    ):
        key = (
            str(source.get("work_id", "")),
            str(source.get("chunk_id", "")),
            str(source.get("content_hash", "")),
        )
        boundary = boundary_by_key.get(key, {})
        term = terms_by_key.get((key[0], key[2]), {})
        signal = _signal_for_source(source, signal_maps) or {}
        confidence = confidence_sources.get(str(source.get("label", "")), {})
        source_available = source.get("inspectable") is True
        boundary_closed = boundary.get("source_boundary_closed") is True
        term_active = term.get("consent_status") == "active" and term.get("revoked") is not True
        content_hash_matches_term = bool(term) and term.get("content_hash") == key[2]
        signal_present = bool(signal)
        source_farm_risk = _float(signal.get("source_farm_risk_score"))
        poisoning_risk = _float(signal.get("poisoning_risk_score"))
        domain_reputation = _float(signal.get("domain_reputation_score"))
        stability_score = _float(signal.get("content_stability_score"), 1.0)
        citation_gaming_count = _int(signal.get("citation_gaming_signal_count"))
        source_farm_ok = source_farm_risk <= MAX_SOURCE_FARM_RISK
        poisoning_ok = poisoning_risk <= MAX_POISONING_RISK
        domain_ok = domain_reputation >= MIN_DOMAIN_REPUTATION
        stability_ok = stability_score >= MIN_CONTENT_STABILITY
        disclosure_complete = (
            signal.get("human_origin_attested") is True
            or signal.get("ai_generated_disclosed") is True
        )
        human_not_synthetic = (
            signal.get("human_origin_attested") is True
            and signal.get("synthetic_source") is not True
            and signal.get("ai_generated_disclosed") is not True
        )
        verified = all(
            (
                source_available,
                boundary_closed,
                term_active,
                content_hash_matches_term,
                signal_present,
                signal.get("signature_verified") is True,
                signal.get("issuer_trusted") is True,
                disclosure_complete,
                human_not_synthetic,
                source_farm_ok,
                poisoning_ok,
                domain_ok,
                stability_ok,
                citation_gaming_count == 0,
                signal.get("cross_archive_consensus") is True,
            )
        )
        row = {
            "display_order": int(source.get("display_order", 0) or 0),
            "label": str(source.get("label", "")),
            "title": str(source.get("title", "")),
            "creator_id": str(source.get("creator_id", "")),
            "work_id": key[0],
            "chunk_id": key[1],
            "content_hash": key[2],
            "source_uri": str(source.get("source_uri", "")),
            "canonical_uri": str(source.get("canonical_uri", "")),
            "availability_row_hash": str(source.get("availability_row_hash", "")),
            "source_boundary_hash": str(boundary.get("source_boundary_hash", "")),
            "license_term_hash": str(term.get("term_hash", "")),
            "authenticity_signal_hash": str(
                signal.get("authenticity_signal_hash", "")
            ),
            "source_confidence_level": str(confidence.get("confidence_level", "")),
            "origin_evidence_id": str(signal.get("origin_evidence_id", "")),
            "origin_evidence_type": str(signal.get("origin_evidence_type", "")),
            "origin_evidence_hash": str(signal.get("origin_evidence_hash", "")),
            "origin_registry_entry_hash": str(
                signal.get("origin_registry_entry_hash", "")
            ),
            "origin_issuer": str(signal.get("issuer", "")),
            "origin_signature_algorithm": str(signal.get("signature_algorithm", "")),
            "origin_signature_verified": signal.get("signature_verified") is True,
            "origin_issuer_trusted": signal.get("issuer_trusted") is True,
            "first_publication_at": str(signal.get("first_publication_at", "")),
            "human_origin_attested": signal.get("human_origin_attested") is True,
            "ai_generated_disclosed": signal.get("ai_generated_disclosed") is True,
            "synthetic_source": signal.get("synthetic_source") is True,
            "source_farm_risk_score": round(source_farm_risk, 8),
            "poisoning_risk_score": round(poisoning_risk, 8),
            "domain_reputation_score": round(domain_reputation, 8),
            "citation_gaming_signal_count": citation_gaming_count,
            "cross_archive_consensus": signal.get("cross_archive_consensus") is True,
            "content_stability_score": round(stability_score, 8),
            "source_available_and_inspectable": source_available,
            "source_boundary_closed": boundary_closed,
            "license_term_active": term_active,
            "content_hash_matches_license": content_hash_matches_term,
            "authenticity_signal_present": signal_present,
            "origin_disclosure_complete": disclosure_complete,
            "human_non_synthetic_origin": human_not_synthetic,
            "source_farm_risk_below_threshold": source_farm_ok,
            "poisoning_risk_below_threshold": poisoning_ok,
            "domain_reputation_above_threshold": domain_ok,
            "content_stability_above_threshold": stability_ok,
            "source_authenticity_verified": verified,
            "direct_payout_eligible": verified,
            "payout_mode": (
                "eligible_direct_payout" if verified else "escrow_until_origin_review"
            ),
            "footer_mode": (
                "display_verified_source"
                if verified
                else "display_with_origin_or_poisoning_warning"
            ),
        }
        row["source_authenticity_status"] = _source_status(row)
        row["source_authenticity_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _issues(
    *,
    rows: list[dict[str, Any]],
    bindings: dict[str, Any],
    artifact_status: dict[str, Any],
    private_field_paths: list[str],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for key, value in bindings.items():
        if key.endswith("_bound") and value is not True:
            issues.append(
                {
                    "issue_type": "artifact_not_bound",
                    "severity": "high",
                    "artifact": key.removesuffix("_bound"),
                }
            )
    if bindings.get("availability_boundary_event_match") is not True:
        issues.append(
            {
                "issue_type": "artifact_event_mismatch",
                "severity": "high",
                "detail": "source availability and source boundary events differ",
            }
        )
    for key, value in artifact_status.items():
        if key.endswith("_errors"):
            continue
        if value is not True:
            issues.append(
                {
                    "issue_type": "artifact_status_failure",
                    "severity": "high",
                    "check": key,
                }
            )
    if private_field_paths:
        issues.append(
            {
                "issue_type": "private_field_leak",
                "severity": "high",
                "paths": private_field_paths,
            }
        )
    for row in rows:
        if row["source_authenticity_verified"]:
            continue
        issues.append(
            {
                "issue_type": row["source_authenticity_status"],
                "severity": (
                    "critical"
                    if row["source_authenticity_status"] == "quarantine_high_risk"
                    else "high"
                ),
                "source_label": row["label"],
                "work_id": row["work_id"],
                "payout_mode": row["payout_mode"],
            }
        )
    return issues


def make_source_authenticity_report(
    *,
    source_availability_report: dict[str, Any],
    source_boundary_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
    source_authenticity_signals: list[dict[str, Any]],
    source_confidence_report: dict[str, Any] | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed report proving cited sources are authentic, not poisoned."""

    bindings = _artifact_bindings(
        source_availability_report=source_availability_report,
        source_boundary_report=source_boundary_report,
        creator_license_contract=creator_license_contract,
        source_confidence_report=source_confidence_report,
    )
    artifact_status = _artifact_status(
        source_availability_report=source_availability_report,
        source_boundary_report=source_boundary_report,
        creator_license_contract=creator_license_contract,
        source_confidence_report=source_confidence_report,
        signing_secret=signing_secret,
    )
    rows = _source_rows(
        source_availability_report=source_availability_report,
        source_boundary_report=source_boundary_report,
        creator_license_contract=creator_license_contract,
        source_confidence_report=source_confidence_report,
        source_authenticity_signals=source_authenticity_signals,
    )
    normalized_signals = sorted(
        (_normalized_signal(signal) for signal in source_authenticity_signals),
        key=lambda signal: (
            signal.get("work_id", ""),
            signal.get("chunk_id", ""),
            signal.get("content_hash", ""),
            signal.get("authenticity_signal_hash", ""),
        ),
    )
    private_field_paths = _contains_private_fields(
        {
            "source_authenticity_rows": rows,
            "source_authenticity_signals": normalized_signals,
        }
    )
    checks = {
        "artifact_statuses_verified": all(
            value is True
            for key, value in artifact_status.items()
            if not key.endswith("_errors")
        ),
        "availability_boundary_event_match": bindings.get(
            "availability_boundary_event_match"
        )
        is True,
        "all_sources_have_origin_signals": all(
            row["authenticity_signal_present"] for row in rows
        ),
        "all_origin_signatures_verified": all(
            row["origin_signature_verified"] for row in rows
        ),
        "all_origin_issuers_trusted": all(row["origin_issuer_trusted"] for row in rows),
        "all_sources_are_human_non_synthetic": all(
            row["human_non_synthetic_origin"] for row in rows
        ),
        "all_source_farm_risks_below_threshold": all(
            row["source_farm_risk_below_threshold"] for row in rows
        ),
        "all_poisoning_risks_below_threshold": all(
            row["poisoning_risk_below_threshold"] for row in rows
        ),
        "all_domains_reputable": all(
            row["domain_reputation_above_threshold"] for row in rows
        ),
        "all_sources_have_archive_consensus": all(
            row["cross_archive_consensus"] for row in rows
        ),
        "all_sources_stable": all(
            row["content_stability_above_threshold"] for row in rows
        ),
        "all_sources_authenticity_verified": bool(rows)
        and all(row["source_authenticity_verified"] for row in rows),
        "private_fields_absent": not private_field_paths,
    }
    issue_list = _issues(
        rows=rows,
        bindings=bindings,
        artifact_status=artifact_status,
        private_field_paths=private_field_paths,
    )
    status = "verified" if all(checks.values()) and not issue_list else "failed"
    event = source_availability_report.get("event", {})
    report = {
        "report_version": SOURCE_AUTHENTICITY_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "event": {
            "event_id": event.get("event_id", ""),
            "event_hash": event.get("event_hash", ""),
            "rendered_output_hash": event.get("rendered_output_hash", ""),
            "answer_hash": event.get("answer_hash", ""),
            "source_availability_report_hash": _declared_hash(
                source_availability_report
            ),
            "source_boundary_report_hash": _declared_hash(source_boundary_report),
            "creator_license_contract_hash": _declared_hash(
                creator_license_contract
            ),
            "source_confidence_report_hash": _declared_hash(source_confidence_report),
        },
        "policy": {
            "policy_version": SOURCE_AUTHENTICITY_POLICY_VERSION,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "maximum_source_farm_risk": MAX_SOURCE_FARM_RISK,
            "maximum_poisoning_risk": MAX_POISONING_RISK,
            "minimum_domain_reputation": MIN_DOMAIN_REPUTATION,
            "minimum_content_stability": MIN_CONTENT_STABILITY,
            "requires_signed_origin_evidence": True,
            "requires_trusted_origin_issuer": True,
            "requires_human_non_synthetic_origin_for_direct_payout": True,
            "escrows_unverified_synthetic_or_high_risk_sources": True,
        },
        "artifact_bindings": bindings,
        "artifact_status": artifact_status,
        "source_authenticity_rows": rows,
        "authenticity_signal_commitments": [
            {
                "work_id": signal["work_id"],
                "chunk_id": signal["chunk_id"],
                "content_hash": signal["content_hash"],
                "origin_evidence_hash": signal["origin_evidence_hash"],
                "issuer": signal["issuer"],
                "authenticity_signal_hash": signal["authenticity_signal_hash"],
            }
            for signal in normalized_signals
        ],
        "checks": checks,
        "issues": issue_list,
        "commitments": {
            "source_authenticity_root": hash_payload(rows),
            "authenticity_signal_root": hash_payload(normalized_signals),
            "artifact_binding_root": hash_payload(bindings),
            "artifact_status_hash": hash_payload(artifact_status),
            "issue_root": hash_payload(issue_list),
            "schema": SOURCE_AUTHENTICITY_SCHEMA,
        },
        "summary": {
            "status": status,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "source_count": len(rows),
            "verified_source_count": sum(
                1 for row in rows if row["source_authenticity_verified"]
            ),
            "synthetic_or_unverified_count": sum(
                1
                for row in rows
                if row["synthetic_source"]
                or row["ai_generated_disclosed"]
                or not row["authenticity_signal_present"]
            ),
            "high_poisoning_risk_count": sum(
                1 for row in rows if not row["poisoning_risk_below_threshold"]
            ),
            "high_source_farm_risk_count": sum(
                1 for row in rows if not row["source_farm_risk_below_threshold"]
            ),
            "direct_payout_eligible_count": sum(
                1 for row in rows if row["direct_payout_eligible"]
            ),
            "escrow_recommended_count": sum(
                1 for row in rows if row["payout_mode"] != "eligible_direct_payout"
            ),
            "issue_count": len(issue_list),
            "all_sources_authentic": bool(rows)
            and all(row["source_authenticity_verified"] for row in rows),
        },
        "schemas": {
            "source_authenticity_report": SOURCE_AUTHENTICITY_SCHEMA,
            "source_availability_report": "docs/schemas/source_availability_report.schema.json",
            "source_boundary_report": "docs/schemas/source_boundary_report.schema.json",
            "creator_license_contract": "docs/schemas/creator_license_contract.schema.json",
            "source_confidence_report": "docs/schemas/source_confidence_report.schema.json",
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "claim_text_disclosed": False,
            "evidence_text_disclosed": False,
            "payout_account_disclosed": False,
            "origin_evidence_text_disclosed": False,
            "report_uses_hashes_origin_booleans_and_risk_scores": True,
        },
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


def validate_source_authenticity_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "event",
        "policy",
        "artifact_bindings",
        "artifact_status",
        "source_authenticity_rows",
        "authenticity_signal_commitments",
        "checks",
        "issues",
        "commitments",
        "summary",
        "schemas",
        "privacy",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing source authenticity report field: {key}")
    if errors:
        return errors
    if report.get("report_version") != SOURCE_AUTHENTICITY_VERSION:
        errors.append("source authenticity report version is unsupported")
    if report.get("policy", {}).get("policy_version") != SOURCE_AUTHENTICITY_POLICY_VERSION:
        errors.append("source authenticity policy version is unsupported")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("source authenticity target certification level is unsupported")
    for key in (
        "event_id",
        "event_hash",
        "rendered_output_hash",
        "answer_hash",
        "source_availability_report_hash",
        "source_boundary_report_hash",
        "creator_license_contract_hash",
        "source_confidence_report_hash",
    ):
        if key not in report.get("event", {}):
            errors.append(f"missing source authenticity event field: {key}")
    for row in report.get("source_authenticity_rows", []):
        for key in (
            "label",
            "work_id",
            "chunk_id",
            "content_hash",
            "availability_row_hash",
            "source_boundary_hash",
            "license_term_hash",
            "authenticity_signal_hash",
            "origin_signature_verified",
            "origin_issuer_trusted",
            "human_non_synthetic_origin",
            "source_farm_risk_below_threshold",
            "poisoning_risk_below_threshold",
            "source_authenticity_verified",
            "direct_payout_eligible",
            "payout_mode",
            "source_authenticity_hash",
        ):
            if key not in row:
                errors.append(f"missing source authenticity row field: {key}")
    if "source_authenticity_report" not in report.get("schemas", {}):
        errors.append("missing source authenticity schema")
    return errors


def verify_source_authenticity_report(
    report: dict[str, Any],
    *,
    source_availability_report: dict[str, Any],
    source_boundary_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
    source_authenticity_signals: list[dict[str, Any]],
    source_confidence_report: dict[str, Any] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify source authenticity against public proof artifacts."""

    errors = validate_source_authenticity_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("source authenticity report hash is not reproducible")

    expected = make_source_authenticity_report(
        source_availability_report=source_availability_report,
        source_boundary_report=source_boundary_report,
        creator_license_contract=creator_license_contract,
        source_confidence_report=source_confidence_report,
        source_authenticity_signals=source_authenticity_signals,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "event",
        "policy",
        "artifact_bindings",
        "artifact_status",
        "source_authenticity_rows",
        "authenticity_signal_commitments",
        "checks",
        "issues",
        "commitments",
        "summary",
        "schemas",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"source authenticity report {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("source authenticity report hash does not match replay")

    if report.get("summary", {}).get("status") != "verified":
        errors.append("source authenticity report status is not verified")
    if report.get("summary", {}).get("all_sources_authentic") is not True:
        errors.append("source authenticity report has unauthentic sources")
    if report.get("summary", {}).get("escrow_recommended_count") not in (0, None):
        errors.append("source authenticity report recommends escrow")
    if report.get("issues"):
        errors.append("source authenticity report contains issues")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"source authenticity check failed: {check}")

    rendered = canonical_json(report)
    for private_literal in (
        "source text",
        "body_text",
        "evidence text",
        "bank account",
        "acct_",
    ):
        if private_literal in rendered:
            errors.append(
                f"source authenticity report exposes private literal {private_literal}"
            )
            break

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("source authenticity report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("source authenticity report signature is invalid")
    return errors
