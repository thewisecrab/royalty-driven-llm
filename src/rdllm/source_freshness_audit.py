"""Source freshness and temporal-validity audit reports.

A citation can be real, reachable, and factually supportive while still being
stale for a current, latest, or as-of claim. This module adds a replayable
public proof that dynamic claims used temporally valid sources, that retrieval
was close enough to answer time, and that a stronger fresher candidate was not
ignored.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)
from rdllm.text import stable_hash

SOURCE_FRESHNESS_AUDIT_VERSION = "rdllm-source-freshness-audit/v1"
SOURCE_FRESHNESS_AUDIT_SCHEMA = "docs/schemas/source_freshness_audit.schema.json"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L116"
MINIMUM_INPUT_LEVEL = "RDLLM-L115"
DEFAULT_MIN_RELEVANCE_SCORE = 0.70
DEFAULT_MIN_FACTUAL_SUPPORT_SCORE = 0.70
DEFAULT_MAX_SOURCE_AGE_DAYS = 30.0
DEFAULT_MAX_RETRIEVAL_LAG_HOURS = 24.0
DEFAULT_CANDIDATE_SUPPORT_MARGIN = 0.05
SUPPORTED_STATUSES = {"supported", "verified", "entailed"}
LINK_OK_STATUSES = {"accessible", "archived", "mirrored", "available"}
STATIC_TEMPORAL_REQUIREMENTS = {"static", "historical", "timeless"}
DYNAMIC_TEMPORAL_REQUIREMENTS = {
    "recent",
    "current",
    "latest",
    "as_of",
    "rapidly_changing",
}
ALLOWED_TEMPORAL_REQUIREMENTS = STATIC_TEMPORAL_REQUIREMENTS | DYNAMIC_TEMPORAL_REQUIREMENTS

DECLARED_HASH_FIELDS = (
    "source_freshness_audit_hash",
    "deep_research_citation_audit_hash",
    "source_footer_delivery_hash",
    "grounded_source_footer_hash",
    "rendered_attribution_audit_hash",
    "claim_source_attribution_hash",
    "source_availability_hash",
    "source_confidence_hash",
    "citation_reliance_hash",
    "source_access_lease_hash",
    "report_hash",
    "card_hash",
    "receipt_hash",
    "trace_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "raw_model_output",
    "raw_output",
    "answer_text",
    "output_text",
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "source_excerpt",
    "raw_license_token",
    "license_server_secret",
    "customer_id",
    "customer_email",
    "invoice_text",
    "payment_method",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "secret",
    "signing_secret",
    "private_key",
}


def load_source_freshness_audit_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for a source freshness audit."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"source_freshness_audit_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
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
    return hash_payload(_hashable_artifact(artifact))


def _artifact_hash_is_reproducible(artifact: dict[str, Any] | None) -> bool:
    if not artifact:
        return False
    declared = _declared_hash(artifact)
    return bool(declared) and declared == hash_payload(_hashable_artifact(artifact))


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}" if path else f"/{key}"
            if str(key) in PRIVATE_FIELD_NAMES:
                findings.append(child_path)
            findings.extend(_contains_private_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_contains_private_fields(child, f"{path}/{index}"))
    return findings


def _private_strings_absent(report: dict[str, Any], audit_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in audit_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalise_label(label: Any) -> str:
    return str(label or "").strip().strip("[]")


def _source_label(row: dict[str, Any], index: int) -> str:
    return _normalise_label(row.get("label") or row.get("source_label") or f"S{index + 1}")


def _float(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def _bounded_score(row: dict[str, Any], key: str) -> float:
    try:
        return max(0.0, min(1.0, float(row.get(key, 0.0) or 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _policy(audit_input: dict[str, Any]) -> dict[str, float]:
    policy = audit_input.get("policy", {})
    return {
        "min_relevance_score": _float(
            policy, "min_relevance_score", DEFAULT_MIN_RELEVANCE_SCORE
        ),
        "min_factual_support_score": _float(
            policy, "min_factual_support_score", DEFAULT_MIN_FACTUAL_SUPPORT_SCORE
        ),
        "default_max_source_age_days": _float(
            policy, "default_max_source_age_days", DEFAULT_MAX_SOURCE_AGE_DAYS
        ),
        "default_max_retrieval_lag_hours": _float(
            policy,
            "default_max_retrieval_lag_hours",
            DEFAULT_MAX_RETRIEVAL_LAG_HOURS,
        ),
        "candidate_support_margin": _float(
            policy,
            "candidate_support_margin",
            DEFAULT_CANDIDATE_SUPPORT_MARGIN,
        ),
    }


def _effective_source_time(source: dict[str, Any]) -> datetime | None:
    return (
        _parse_datetime(source.get("last_modified_at"))
        or _parse_datetime(source.get("published_at"))
        or _parse_datetime(source.get("valid_from"))
    )


def _effective_candidate_time(candidate: dict[str, Any]) -> datetime | None:
    return (
        _parse_datetime(candidate.get("candidate_last_modified_at"))
        or _parse_datetime(candidate.get("candidate_published_at"))
        or _parse_datetime(candidate.get("published_at"))
        or _parse_datetime(candidate.get("last_modified_at"))
    )


def _age_days(reference: datetime | None, observed: datetime | None) -> float | None:
    if reference is None or observed is None or observed > reference:
        return None
    return (reference - observed).total_seconds() / 86400.0


def _lag_hours(reference: datetime | None, retrieved: datetime | None) -> float | None:
    if reference is None or retrieved is None or retrieved > reference:
        return None
    return (reference - retrieved).total_seconds() / 3600.0


def _valid_at(source: dict[str, Any], reference: datetime | None) -> bool:
    if reference is None:
        return False
    valid_from = _parse_datetime(source.get("valid_from"))
    valid_until = _parse_datetime(source.get("valid_until"))
    if valid_from is not None and valid_from > reference:
        return False
    if valid_until is not None and valid_until < reference:
        return False
    return True


def _temporal_requirement(row: dict[str, Any]) -> str:
    value = str(row.get("temporal_requirement") or "static").strip().lower()
    return value if value in ALLOWED_TEMPORAL_REQUIREMENTS else value


def _is_dynamic(requirement: str) -> bool:
    return requirement in DYNAMIC_TEMPORAL_REQUIREMENTS


def _public_source_rows(
    audit_input: dict[str, Any], answer_time: datetime | None
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, source in enumerate(audit_input.get("source_rows", [])):
        if not isinstance(source, dict):
            continue
        label = _source_label(source, index)
        retrieval_status = str(
            source.get("retrieval_status")
            or source.get("availability_status")
            or source.get("link_status")
            or ""
        ).lower()
        content_hash = str(
            source.get("content_hash")
            or source.get("snapshot_hash")
            or stable_hash(str(source.get("source_excerpt", "")))
        )
        source_version_hash = str(
            source.get("source_version_hash")
            or source.get("version_hash")
            or stable_hash(
                ":".join(
                    [
                        str(source.get("source_uri") or source.get("url") or ""),
                        str(source.get("published_at") or ""),
                        str(source.get("last_modified_at") or ""),
                        content_hash,
                    ]
                )
            )
        )
        retrieved_at = _parse_datetime(source.get("retrieved_at") or source.get("fetched_at"))
        published_at = _parse_datetime(source.get("published_at"))
        last_modified_at = _parse_datetime(source.get("last_modified_at"))
        valid_from = _parse_datetime(source.get("valid_from"))
        valid_until = _parse_datetime(source.get("valid_until"))
        effective_at = _effective_source_time(source)
        row = {
            "label": label,
            "title": str(source.get("title") or source.get("source_title") or ""),
            "source_uri": str(source.get("source_uri") or source.get("url") or ""),
            "archive_uri": str(source.get("archive_uri") or ""),
            "retrieval_status": retrieval_status,
            "retrieved_at": _iso(retrieved_at),
            "published_at": _iso(published_at),
            "last_modified_at": _iso(last_modified_at),
            "valid_from": _iso(valid_from),
            "valid_until": _iso(valid_until),
            "effective_at": _iso(effective_at),
            "content_hash": content_hash,
            "source_version_hash": source_version_hash,
            "license_status": str(
                source.get("license_status") or source.get("rights_status") or ""
            ),
            "link_materialized": retrieval_status in LINK_OK_STATUSES,
        }
        row["temporal_metadata_present"] = bool(
            row["retrieved_at"]
            and row["effective_at"]
            and row["content_hash"]
            and row["source_version_hash"]
        )
        row["valid_at_answer_time"] = _valid_at(source, answer_time)
        row["source_row_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: row["label"])


def _source_temporal_status(
    source: dict[str, Any],
    *,
    reference_time: datetime | None,
    max_source_age_days: float,
    max_retrieval_lag_hours: float,
) -> dict[str, Any]:
    effective_at = _parse_datetime(source.get("effective_at"))
    retrieved_at = _parse_datetime(source.get("retrieved_at"))
    source_age_days = _age_days(reference_time, effective_at)
    retrieval_lag_hours = _lag_hours(reference_time, retrieved_at)
    row = {
        "label": source["label"],
        "source_row_hash": source["source_row_hash"],
        "effective_at": source["effective_at"],
        "retrieved_at": source["retrieved_at"],
        "source_age_days": (
            round(source_age_days, 8) if source_age_days is not None else None
        ),
        "retrieval_lag_hours": (
            round(retrieval_lag_hours, 8) if retrieval_lag_hours is not None else None
        ),
        "max_source_age_days": max_source_age_days,
        "max_retrieval_lag_hours": max_retrieval_lag_hours,
        "source_fresh_enough": (
            source_age_days is not None and source_age_days <= max_source_age_days
        ),
        "retrieved_within_lag": (
            retrieval_lag_hours is not None
            and retrieval_lag_hours <= max_retrieval_lag_hours
        ),
        "link_materialized": bool(source.get("link_materialized")),
        "valid_at_reference_time": _valid_at(source, reference_time),
        "temporal_metadata_present": bool(source.get("temporal_metadata_present")),
    }
    row["source_temporal_hash"] = hash_payload(row)
    return row


def _artifact_bindings(audit_input: dict[str, Any]) -> dict[str, Any]:
    artifacts = {
        "deep_research_citation_audit": audit_input.get("deep_research_citation_audit"),
        "source_footer_delivery": audit_input.get("source_footer_delivery"),
        "grounded_source_footer": audit_input.get("grounded_source_footer"),
        "claim_source_attribution_report": audit_input.get("claim_source_attribution_report"),
        "source_availability_report": audit_input.get("source_availability_report"),
        "source_confidence_report": audit_input.get("source_confidence_report"),
        "citation_reliance_receipt": audit_input.get("citation_reliance_receipt"),
        "source_access_lease_report": audit_input.get("source_access_lease_report"),
    }
    bindings: dict[str, Any] = {}
    for name, artifact in artifacts.items():
        if artifact is None:
            continue
        bindings[f"{name}_hash"] = _declared_hash(artifact)
        bindings[f"{name}_hash_reproducible"] = _artifact_hash_is_reproducible(artifact)
    return bindings


def _claim_temporal_rows(
    audit_input: dict[str, Any],
    source_by_label: dict[str, dict[str, Any]],
    answer_time: datetime | None,
    policy: dict[str, float],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, claim in enumerate(audit_input.get("claim_rows", [])):
        if not isinstance(claim, dict):
            continue
        labels = [
            _normalise_label(label)
            for label in claim.get("citation_labels", claim.get("source_labels", []))
            if _normalise_label(label)
        ]
        resolved_labels = [label for label in labels if label in source_by_label]
        requirement = _temporal_requirement(claim)
        is_dynamic = _is_dynamic(requirement)
        as_of = _parse_datetime(claim.get("as_of")) or answer_time
        max_source_age_days = _float(
            claim,
            "max_source_age_days",
            policy["default_max_source_age_days"],
        )
        max_retrieval_lag_hours = _float(
            claim,
            "max_retrieval_lag_hours",
            policy["default_max_retrieval_lag_hours"],
        )
        source_status_rows = [
            _source_temporal_status(
                source_by_label[label],
                reference_time=as_of,
                max_source_age_days=max_source_age_days,
                max_retrieval_lag_hours=max_retrieval_lag_hours,
            )
            for label in resolved_labels
        ]
        support_status = str(claim.get("support_status") or claim.get("verdict") or "").lower()
        relevance = _bounded_score(claim, "relevance_score")
        factual = _bounded_score(claim, "factual_support_score")
        support_ok = (
            support_status in SUPPORTED_STATUSES
            and relevance >= policy["min_relevance_score"]
            and factual >= policy["min_factual_support_score"]
        )
        hash_present = bool(
            str(claim.get("evidence_span_hash") or "")
            and str(claim.get("source_quote_hash") or claim.get("quote_hash") or "")
        )
        dynamic_sources_fresh = all(
            row["source_fresh_enough"] for row in source_status_rows
        )
        dynamic_sources_retrieved = all(
            row["retrieved_within_lag"] for row in source_status_rows
        )
        dynamic_sources_valid = all(
            row["valid_at_reference_time"] for row in source_status_rows
        )
        dynamic_sources_materialized = all(
            row["link_materialized"] for row in source_status_rows
        )
        has_fresh_supported_source = any(
            row["source_fresh_enough"]
            and row["retrieved_within_lag"]
            and row["valid_at_reference_time"]
            and row["link_materialized"]
            for row in source_status_rows
        )
        row = {
            "claim_id": str(claim.get("claim_id") or f"claim_{index + 1}"),
            "claim_hash": str(
                claim.get("claim_hash") or stable_hash(str(claim.get("claim_text", "")))
            ),
            "temporal_requirement": requirement,
            "temporal_requirement_recognized": requirement in ALLOWED_TEMPORAL_REQUIREMENTS,
            "dynamic_temporal_claim": is_dynamic,
            "as_of": _iso(as_of),
            "max_source_age_days": max_source_age_days,
            "max_retrieval_lag_hours": max_retrieval_lag_hours,
            "citation_labels": sorted(labels),
            "resolved_citation_labels": sorted(resolved_labels),
            "unresolved_citation_labels": sorted(set(labels) - set(resolved_labels)),
            "support_status": support_status,
            "relevance_score": relevance,
            "factual_support_score": factual,
            "claim_support_hashes_present": hash_present,
            "source_temporal_rows": source_status_rows,
            "all_citations_resolved": bool(labels) and len(labels) == len(resolved_labels),
            "support_status_accepted": support_ok,
            "has_fresh_supported_source": (
                support_ok and hash_present and has_fresh_supported_source
            )
            if is_dynamic
            else support_ok and hash_present and bool(resolved_labels),
            "all_selected_sources_fresh": dynamic_sources_fresh if is_dynamic else True,
            "all_selected_sources_retrieved_within_lag": (
                dynamic_sources_retrieved if is_dynamic else True
            ),
            "all_selected_sources_valid_at_as_of": (
                dynamic_sources_valid if is_dynamic else True
            ),
            "all_selected_sources_materialized": (
                dynamic_sources_materialized if is_dynamic else True
            ),
        }
        row["claim_temporal_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: row["claim_id"])


def _candidate_temporal_rows(
    audit_input: dict[str, Any],
    claim_rows: list[dict[str, Any]],
    policy: dict[str, float],
) -> list[dict[str, Any]]:
    claim_by_id = {row["claim_id"]: row for row in claim_rows}
    selected_best_time: dict[str, datetime | None] = {}
    selected_best_support: dict[str, float] = {}
    for claim_id, claim in claim_by_id.items():
        times = [
            _parse_datetime(row["effective_at"])
            for row in claim.get("source_temporal_rows", [])
            if _parse_datetime(row["effective_at"]) is not None
        ]
        selected_best_time[claim_id] = max(times) if times else None
        selected_best_support[claim_id] = min(
            float(claim.get("relevance_score", 0.0) or 0.0),
            float(claim.get("factual_support_score", 0.0) or 0.0),
        )

    rows: list[dict[str, Any]] = []
    for index, candidate in enumerate(audit_input.get("candidate_rows", [])):
        if not isinstance(candidate, dict):
            continue
        claim_id = str(candidate.get("claim_id") or "")
        claim = claim_by_id.get(claim_id)
        effective_at = _effective_candidate_time(candidate)
        support_status = str(candidate.get("support_status") or candidate.get("verdict") or "").lower()
        relevance = _bounded_score(candidate, "candidate_relevance_score")
        if "candidate_factual_support_score" in candidate:
            factual = _bounded_score(candidate, "candidate_factual_support_score")
        else:
            factual = relevance
        support_score = min(relevance, factual)
        supported = (
            support_status in SUPPORTED_STATUSES
            and relevance >= policy["min_relevance_score"]
            and factual >= policy["min_factual_support_score"]
        )
        selected = bool(candidate.get("selected"))
        baseline_time = selected_best_time.get(claim_id)
        baseline_support = selected_best_support.get(claim_id, 0.0)
        fresher_than_selected = bool(
            effective_at is not None
            and baseline_time is not None
            and effective_at > baseline_time
        )
        not_weaker_than_selected = (
            support_score + policy["candidate_support_margin"] >= baseline_support
        )
        displaces_selected = bool(
            claim
            and claim.get("dynamic_temporal_claim")
            and not selected
            and supported
            and fresher_than_selected
            and not_weaker_than_selected
        )
        row = {
            "candidate_id": str(candidate.get("candidate_id") or f"candidate_{index + 1}"),
            "claim_id": claim_id,
            "label": _normalise_label(
                candidate.get("label") or candidate.get("source_label") or ""
            ),
            "selected": selected,
            "candidate_source_uri_hash": hash_payload(
                str(candidate.get("source_uri") or candidate.get("url") or "")
            ),
            "candidate_effective_at": _iso(effective_at),
            "candidate_relevance_score": relevance,
            "candidate_factual_support_score": factual,
            "support_status": support_status,
            "supported_candidate": supported,
            "fresher_than_selected": fresher_than_selected,
            "not_weaker_than_selected": not_weaker_than_selected,
            "displaces_selected_source": displaces_selected,
        }
        row["candidate_temporal_hash"] = hash_payload(row)
        rows.append(row)
    return sorted(rows, key=lambda row: (row["claim_id"], row["candidate_id"]))


def make_source_freshness_audit_report(
    audit_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L116 audit for source freshness and temporal validity."""

    answer_time = _parse_datetime(audit_input.get("answer_time") or created_at)
    policy_values = _policy(audit_input)
    source_rows = _public_source_rows(audit_input, answer_time)
    source_by_label = {row["label"]: row for row in source_rows}
    claim_rows = _claim_temporal_rows(
        audit_input,
        source_by_label,
        answer_time,
        policy_values,
    )
    candidate_rows = _candidate_temporal_rows(audit_input, claim_rows, policy_values)
    public_payload = {
        "source_rows": source_rows,
        "claim_temporal_rows": claim_rows,
        "candidate_temporal_rows": candidate_rows,
    }
    dynamic_claim_rows = [
        row for row in claim_rows if row.get("dynamic_temporal_claim") is True
    ]
    checks = {
        "answer_time_present": answer_time is not None,
        "source_rows_present": bool(source_rows),
        "source_rows_have_temporal_metadata": all(
            row["temporal_metadata_present"] for row in source_rows
        ),
        "claim_rows_present": bool(claim_rows),
        "temporal_requirements_recognized": all(
            row["temporal_requirement_recognized"] for row in claim_rows
        ),
        "every_claim_has_resolved_sources": all(
            row["all_citations_resolved"] for row in claim_rows
        ),
        "every_temporal_claim_has_policy": all(
            not row["dynamic_temporal_claim"]
            or (
                row["max_source_age_days"] > 0
                and row["max_retrieval_lag_hours"] > 0
            )
            for row in claim_rows
        ),
        "every_dynamic_claim_has_fresh_source": all(
            row["has_fresh_supported_source"] for row in dynamic_claim_rows
        ),
        "every_selected_temporal_source_is_fresh": all(
            row["all_selected_sources_fresh"] for row in dynamic_claim_rows
        ),
        "every_dynamic_claim_retrieved_within_lag": all(
            row["all_selected_sources_retrieved_within_lag"]
            for row in dynamic_claim_rows
        ),
        "every_temporal_claim_valid_at_answer_time": all(
            row["all_selected_sources_valid_at_as_of"] for row in dynamic_claim_rows
        ),
        "every_selected_temporal_source_materialized": all(
            row["all_selected_sources_materialized"] for row in dynamic_claim_rows
        ),
        "freshest_supported_candidate_selected": not any(
            row["displaces_selected_source"] for row in candidate_rows
        ),
        "claim_support_hashes_present": all(
            row["claim_support_hashes_present"] for row in claim_rows
        ),
        "artifact_bindings_hash_reproducible": all(
            value is True
            for key, value in _artifact_bindings(audit_input).items()
            if key.endswith("_hash_reproducible")
        ),
        "public_report_has_no_private_field_names": not _contains_private_fields(
            public_payload
        ),
    }
    report: dict[str, Any] = {
        "audit_version": SOURCE_FRESHNESS_AUDIT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": {
            "profile": "rdllm-source-freshness-audit-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "dynamic_requirements": sorted(DYNAMIC_TEMPORAL_REQUIREMENTS),
            "static_requirements": sorted(STATIC_TEMPORAL_REQUIREMENTS),
            "source_metadata_must_include_retrieved_and_effective_time": True,
            "retrieval_must_precede_or_equal_answer_time": True,
            "fresher_supported_candidates_must_not_be_ignored": True,
            "min_relevance_score": policy_values["min_relevance_score"],
            "min_factual_support_score": policy_values["min_factual_support_score"],
            "default_max_source_age_days": policy_values["default_max_source_age_days"],
            "default_max_retrieval_lag_hours": policy_values[
                "default_max_retrieval_lag_hours"
            ],
            "candidate_support_margin": policy_values["candidate_support_margin"],
        },
        "answer_binding": {
            "answer_id_hash": hash_payload(str(audit_input.get("answer_id", ""))),
            "answer_time": _iso(answer_time),
            "source_count": len(source_rows),
            "claim_count": len(claim_rows),
            "dynamic_claim_count": len(dynamic_claim_rows),
            "candidate_count": len(candidate_rows),
        },
        "artifact_bindings": _artifact_bindings(audit_input),
        "source_rows": source_rows,
        "claim_temporal_rows": claim_rows,
        "candidate_temporal_rows": candidate_rows,
        "checks": checks,
        "commitments": {
            "source_temporal_root": hash_payload(
                [row["source_row_hash"] for row in source_rows]
            ),
            "claim_temporal_root": hash_payload(
                [row["claim_temporal_hash"] for row in claim_rows]
            ),
            "candidate_temporal_root": hash_payload(
                [row["candidate_temporal_hash"] for row in candidate_rows]
            ),
            "schema": SOURCE_FRESHNESS_AUDIT_SCHEMA,
        },
        "schemas": {
            "source_freshness_audit": SOURCE_FRESHNESS_AUDIT_SCHEMA,
            "deep_research_citation_audit": "docs/schemas/deep_research_citation_audit.schema.json",
            "source_availability_report": "docs/schemas/source_availability_report.schema.json",
            "source_confidence_report": "docs/schemas/source_confidence_report.schema.json",
        },
        "summary": {
            "status": "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "source_count": len(source_rows),
            "claim_count": len(claim_rows),
            "dynamic_claim_count": len(dynamic_claim_rows),
            "fresh_dynamic_claim_count": sum(
                1 for row in dynamic_claim_rows if row["has_fresh_supported_source"]
            ),
            "stale_dynamic_claim_count": sum(
                1 for row in dynamic_claim_rows if not row["has_fresh_supported_source"]
            ),
            "selected_candidate_count": sum(
                1 for row in candidate_rows if row["selected"]
            ),
            "fresher_supported_candidate_count": sum(
                1 for row in candidate_rows if row["displaces_selected_source"]
            ),
        },
        "privacy": {
            "raw_prompt_text_disclosed": False,
            "raw_answer_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_evidence_text_disclosed": False,
            "public_report_uses_hashes_scores_uris_titles_and_timestamps": True,
        },
    }
    report["checks"]["private_strings_absent"] = _private_strings_absent(
        report, audit_input
    )
    report["summary"]["status"] = "ready" if all(report["checks"].values()) else "failed"
    report["source_freshness_audit_hash"] = hash_payload(_hashable_report(report))
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


def validate_source_freshness_audit_shape(report: dict[str, Any]) -> list[str]:
    """Validate the public shape of an L116 source freshness audit."""

    errors: list[str] = []
    required = (
        "audit_version",
        "issuer",
        "created_at",
        "policy",
        "answer_binding",
        "artifact_bindings",
        "source_rows",
        "claim_temporal_rows",
        "candidate_temporal_rows",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
        "source_freshness_audit_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing source freshness audit field: {key}")
    if errors:
        return errors
    if report.get("audit_version") != SOURCE_FRESHNESS_AUDIT_VERSION:
        errors.append("source freshness audit version is unsupported")
    if report.get("policy", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("source freshness audit target certification level is unsupported")
    if "source_freshness_audit" not in report.get("schemas", {}):
        errors.append("missing source freshness audit schema")
    private_paths = _contains_private_fields(report)
    if private_paths:
        errors.append("source freshness audit contains private field")
    return errors


def verify_source_freshness_audit_report(
    report: dict[str, Any],
    *,
    audit_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L116 source freshness audit against its private replay input."""

    errors = validate_source_freshness_audit_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get(
        "source_freshness_audit_hash"
    ):
        errors.append("source freshness audit hash is not reproducible")
    expected = make_source_freshness_audit_report(
        audit_input,
        issuer=str(report.get("issuer", DEFAULT_ISSUER)),
        created_at=str(report.get("created_at", "")) or None,
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "answer_binding",
        "artifact_bindings",
        "source_rows",
        "claim_temporal_rows",
        "candidate_temporal_rows",
        "checks",
        "commitments",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"source freshness audit {key} does not match inputs")
    if expected.get("source_freshness_audit_hash") != report.get(
        "source_freshness_audit_hash"
    ):
        errors.append("source freshness audit hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("source freshness audit status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"source freshness audit check failed: {check}")
    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("source freshness audit is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("source freshness audit signature is invalid")
    return errors
