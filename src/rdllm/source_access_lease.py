"""Source-issued access leases for attribution-aware content consumption.

This layer closes a provider-side blind spot: a model can prove after-the-fact
that it cited and paid a source, while still leaving creators unable to verify
whether access was licensed before retrieval, training, or generation.  The public
report binds consumed source rows to source-issued lease commitments and access
logs without exposing raw prompt, answer, source, customer, or payment text.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)

SOURCE_ACCESS_LEASE_VERSION = "rdllm-source-access-lease/v1"
SOURCE_ACCESS_LEASE_SCHEMA = "docs/schemas/source_access_lease_report.schema.json"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L98"

DECLARED_HASH_FIELDS = (
    "lease_report_hash",
    "binding_report_hash",
    "report_hash",
    "contract_hash",
    "envelope_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "bundle_hash",
    "summary_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "region_text",
    "quote",
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
    "source_signing_secret",
    "secret",
    "signing_secret",
    "private_key",
}

ESCROW_STATUSES = {
    "escrow",
    "held",
    "rights_conflict_escrow",
    "source_access_lease_escrow",
    "license_escrow",
}
DIRECT_STATUSES = {"direct", "accepted", "payable", "paid", "settled"}


def load_source_access_lease_input(path: str | Path) -> dict[str, Any]:
    """Load private inputs used to replay a source-access lease report."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"lease_report_hash", "signature"}
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
        return True
    declared = _declared_hash(artifact)
    return bool(declared) and declared == hash_payload(_hashable_artifact(artifact))


def _hashable_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key not in {"row_hash", "lease_row_hash", "access_row_hash"}
    }


def _source_signature_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key
        not in {
            "source_signature",
            "lease_row_hash",
            "row_hash",
            "source_signature_valid",
        }
    }


def _contains_private_fields(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in PRIVATE_FIELD_NAMES:
                return True
            if _contains_private_fields(child):
                return True
    if isinstance(value, list):
        return any(_contains_private_fields(child) for child in value)
    return False


def _private_strings_absent(report: dict[str, Any], lease_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in lease_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _policy(lease_input: dict[str, Any]) -> dict[str, Any]:
    configured = dict(lease_input.get("policy", {}))
    return {
        "require_source_issued_leases": bool(
            configured.get("require_source_issued_leases", True)
        ),
        "require_access_logs": bool(configured.get("require_access_logs", True)),
        "require_license_contract_terms": bool(
            configured.get("require_license_contract_terms", True)
        ),
        "require_lease_before_access": bool(
            configured.get("require_lease_before_access", True)
        ),
        "require_usage_purpose_allowed": bool(
            configured.get("require_usage_purpose_allowed", True)
        ),
        "require_minimum_creator_pool_rate": bool(
            configured.get("require_minimum_creator_pool_rate", True)
        ),
        "require_region_binding_for_direct_sources": bool(
            configured.get("require_region_binding_for_direct_sources", True)
        ),
        "require_denied_sources_escrowed": bool(
            configured.get("require_denied_sources_escrowed", True)
        ),
    }


def _usage_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("work_id", "")),
        str(row.get("chunk_id", "")),
        str(row.get("source_uri", "")),
    )


def _matches_usage(lease: dict[str, Any], usage: dict[str, Any]) -> bool:
    work_ok = not usage.get("work_id") or lease.get("work_id") == usage.get("work_id")
    chunk_ok = not usage.get("chunk_id") or lease.get("chunk_id") == usage.get("chunk_id")
    uri_ok = (
        not usage.get("source_uri")
        or lease.get("source_uri") == usage.get("source_uri")
        or lease.get("canonical_uri") == usage.get("source_uri")
    )
    return bool(work_ok and chunk_ok and uri_ok)


def _is_escrow(row: dict[str, Any]) -> bool:
    status = str(row.get("settlement_status", row.get("royalty_status", "")))
    route = str(row.get("escrow_account", row.get("settlement_route", "")))
    return status in ESCROW_STATUSES or route.endswith("escrow") or "escrow" in route


def _is_direct(row: dict[str, Any]) -> bool:
    status = str(row.get("settlement_status", row.get("royalty_status", "")))
    return status in DIRECT_STATUSES and not _is_escrow(row)


def _allowed(lease: dict[str, Any], usage: dict[str, Any]) -> bool:
    purpose = str(usage.get("usage_purpose", "retrieval_inference"))
    allowed = {str(item) for item in lease.get("allowed_uses", [])}
    prohibited = {str(item) for item in lease.get("prohibited_uses", [])}
    return purpose in allowed and purpose not in prohibited


def _within_window(lease: dict[str, Any], access: dict[str, Any]) -> bool:
    accessed_at = str(access.get("accessed_at", ""))
    issued_at = str(lease.get("issued_at", ""))
    valid_from = str(lease.get("valid_from", ""))
    valid_until = str(lease.get("valid_until", ""))
    if issued_at and accessed_at and issued_at > accessed_at:
        return False
    if valid_from and accessed_at and valid_from > accessed_at:
        return False
    if valid_until and accessed_at and accessed_at > valid_until:
        return False
    return True


def _lease_active_for_usage(
    lease: dict[str, Any],
    usage: dict[str, Any],
    access: dict[str, Any],
    creator_pool_rate: Decimal,
) -> bool:
    return bool(
        not lease.get("revoked", False)
        and _allowed(lease, usage)
        and _within_window(lease, access)
        and str(lease.get("content_hash", "")) == str(usage.get("content_hash", ""))
        and creator_pool_rate >= _decimal(lease.get("minimum_creator_pool_rate", "0"))
    )


def _contract_terms_by_work(contract: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    terms = (contract or {}).get("terms", [])
    return {
        str(term.get("work_id", "")): term
        for term in terms
        if term.get("work_id")
    }


def _region_labels(report: dict[str, Any] | None) -> set[str]:
    if not report:
        return set()
    labels = {
        str(row.get("source_label", ""))
        for row in report.get("claim_region_rows", [])
        if row.get("source_label")
    }
    labels.update(
        str(row.get("source_label", ""))
        for row in report.get("source_region_rows", [])
        if row.get("source_label")
    )
    return labels


def _source_signature(row: dict[str, Any], source_secret: str | None) -> dict[str, Any]:
    provided = row.get("source_signature")
    if isinstance(provided, dict) and provided.get("value") and not source_secret:
        return {
            "algorithm": str(provided.get("algorithm", "HMAC-SHA256")),
            "issuer": str(provided.get("issuer", row.get("lease_issuer", ""))),
            "value": str(provided.get("value", "")),
        }
    return {
        "algorithm": "HMAC-SHA256" if source_secret else "UNSIGNED",
        "issuer": str(row.get("lease_issuer", row.get("issuer", ""))),
        "value": (
            sign_payload(_source_signature_payload(row), source_secret)
            if source_secret
            else str((provided or {}).get("value", ""))
        ),
    }


def _normalized_lease_rows(
    lease_input: dict[str, Any],
    *,
    source_signing_secret: str | None,
) -> list[dict[str, Any]]:
    rows = []
    for index, row in enumerate(lease_input.get("lease_rows", []), start=1):
        public = {
            "lease_id": str(row.get("lease_id", f"lease:{index}")),
            "lease_issuer": str(row.get("lease_issuer", row.get("issuer", ""))),
            "creator_id": str(row.get("creator_id", "")),
            "work_id": str(row.get("work_id", "")),
            "chunk_id": str(row.get("chunk_id", "")),
            "source_uri": str(row.get("source_uri", "")),
            "canonical_uri": str(row.get("canonical_uri", row.get("source_uri", ""))),
            "content_hash": str(row.get("content_hash", "")),
            "allowed_uses": sorted(str(item) for item in row.get("allowed_uses", [])),
            "prohibited_uses": sorted(
                str(item) for item in row.get("prohibited_uses", [])
            ),
            "valid_from": str(row.get("valid_from", "")),
            "valid_until": str(row.get("valid_until", "")),
            "issued_at": str(row.get("issued_at", "")),
            "revoked": bool(row.get("revoked", False)),
            "minimum_creator_pool_rate": str(row.get("minimum_creator_pool_rate", "0")),
            "access_method": str(row.get("access_method", "")),
            "access_nonce_hash": str(row.get("access_nonce_hash", "")),
            "royalty_required": bool(row.get("royalty_required", True)),
            "attribution_required": bool(row.get("attribution_required", True)),
            "region_binding_required": bool(row.get("region_binding_required", True)),
            "source_text_disclosed": False,
            "payout_account_disclosed": False,
        }
        public["source_signature"] = _source_signature(public, source_signing_secret)
        public["source_signature_present"] = bool(public["source_signature"]["value"])
        public["lease_row_hash"] = hash_payload(_hashable_row(public))
        rows.append(public)
    return rows


def _normalized_access_rows(lease_input: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for index, row in enumerate(lease_input.get("access_log_rows", []), start=1):
        public = {
            "access_event_id": str(row.get("access_event_id", f"access:{index}")),
            "lease_id": str(row.get("lease_id", "")),
            "provider_id": str(row.get("provider_id", "")),
            "access_method": str(row.get("access_method", row.get("method", ""))),
            "usage_purpose": str(row.get("usage_purpose", "retrieval_inference")),
            "accessed_at": str(row.get("accessed_at", "")),
            "work_id": str(row.get("work_id", "")),
            "chunk_id": str(row.get("chunk_id", "")),
            "source_uri": str(row.get("source_uri", "")),
            "content_hash": str(row.get("content_hash", "")),
            "request_nonce_hash": str(row.get("request_nonce_hash", "")),
            "response_snapshot_hash": str(row.get("response_snapshot_hash", "")),
            "metering_event_hash": str(row.get("metering_event_hash", "")),
            "raw_request_disclosed": False,
            "raw_response_disclosed": False,
        }
        public["access_row_hash"] = hash_payload(_hashable_row(public))
        rows.append(public)
    return rows


def _normalized_usage_rows(lease_input: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for index, row in enumerate(lease_input.get("source_usage_rows", []), start=1):
        public = {
            "source_usage_id": str(row.get("source_usage_id", f"source-use:{index}")),
            "source_label": str(row.get("source_label", "")),
            "work_id": str(row.get("work_id", "")),
            "chunk_id": str(row.get("chunk_id", "")),
            "source_uri": str(row.get("source_uri", "")),
            "content_hash": str(row.get("content_hash", "")),
            "usage_purpose": str(row.get("usage_purpose", "retrieval_inference")),
            "settlement_status": str(row.get("settlement_status", "direct")),
            "escrow_account": str(row.get("escrow_account", "")),
            "creator_pool_rate": str(row.get("creator_pool_rate", "")),
            "source_text_disclosed": False,
        }
        public["direct_settlement"] = _is_direct(public)
        public["escrowed"] = _is_escrow(public)
        public["usage_row_hash"] = hash_payload(_hashable_row(public))
        rows.append(public)
    return rows


def _coverage_rows(
    *,
    usage_rows: list[dict[str, Any]],
    lease_rows: list[dict[str, Any]],
    access_rows: list[dict[str, Any]],
    creator_license_contract: dict[str, Any] | None,
    evidence_region_binding_report: dict[str, Any] | None,
    creator_pool_rate: Decimal,
) -> list[dict[str, Any]]:
    terms_by_work = _contract_terms_by_work(creator_license_contract)
    labels_with_regions = _region_labels(evidence_region_binding_report)
    access_by_lease = {row["lease_id"]: row for row in access_rows}
    rows = []
    for usage in usage_rows:
        matching_leases = [lease for lease in lease_rows if _matches_usage(lease, usage)]
        matching_access = [
            access
            for access in access_rows
            if any(access["lease_id"] == lease["lease_id"] for lease in matching_leases)
            and access.get("work_id") == usage.get("work_id")
            and access.get("chunk_id") == usage.get("chunk_id")
            and access.get("content_hash") == usage.get("content_hash")
        ]
        active_leases = [
            lease
            for lease in matching_leases
            if _lease_active_for_usage(
                lease,
                usage,
                access_by_lease.get(lease["lease_id"], {}),
                creator_pool_rate,
            )
        ]
        contract_term = terms_by_work.get(str(usage.get("work_id", "")), {})
        term_allowed = bool(
            contract_term
            and contract_term.get("consent_status") == "active"
            and usage["usage_purpose"] in set(contract_term.get("allowed_uses", []))
            and usage["usage_purpose"] not in set(contract_term.get("prohibited_uses", []))
            and str(contract_term.get("content_hash", usage["content_hash"]))
            == usage["content_hash"]
        )
        row = {
            "source_usage_id": usage["source_usage_id"],
            "source_label": usage["source_label"],
            "work_id": usage["work_id"],
            "chunk_id": usage["chunk_id"],
            "usage_purpose": usage["usage_purpose"],
            "direct_settlement": usage["direct_settlement"],
            "escrowed": usage["escrowed"],
            "matching_lease_count": len(matching_leases),
            "matching_access_log_count": len(matching_access),
            "active_lease_count": len(active_leases),
            "accepted_lease_ids": [lease["lease_id"] for lease in active_leases],
            "license_contract_term_present": bool(contract_term),
            "license_contract_term_allows_use": term_allowed,
            "region_binding_present": (
                not usage["source_label"] or usage["source_label"] in labels_with_regions
            ),
            "covered_for_direct_settlement": bool(
                usage["direct_settlement"]
                and active_leases
                and matching_access
                and term_allowed
                and (
                    not usage["source_label"]
                    or usage["source_label"] in labels_with_regions
                )
            ),
            "denied_or_unleased_escrowed": bool(
                (not active_leases or not term_allowed) and usage["escrowed"]
            ),
        }
        row["coverage_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _artifact_bindings(lease_input: dict[str, Any]) -> dict[str, Any]:
    return {
        "response_envelope_hash": _declared_hash(
            lease_input.get("response_envelope")
        ),
        "creator_license_contract_hash": _declared_hash(
            lease_input.get("creator_license_contract")
        ),
        "source_availability_report_hash": _declared_hash(
            lease_input.get("source_availability_report")
        ),
        "evidence_region_binding_report_hash": _declared_hash(
            lease_input.get("evidence_region_binding_report")
        ),
        "response_envelope_hash_reproducible": _artifact_hash_is_reproducible(
            lease_input.get("response_envelope")
        ),
        "creator_license_contract_hash_reproducible": _artifact_hash_is_reproducible(
            lease_input.get("creator_license_contract")
        ),
        "source_availability_hash_reproducible": _artifact_hash_is_reproducible(
            lease_input.get("source_availability_report")
        ),
        "evidence_region_binding_hash_reproducible": _artifact_hash_is_reproducible(
            lease_input.get("evidence_region_binding_report")
        ),
    }


def _checks(
    *,
    lease_input: dict[str, Any],
    policy: dict[str, Any],
    artifact_bindings: dict[str, Any],
    usage_rows: list[dict[str, Any]],
    lease_rows: list[dict[str, Any]],
    access_rows: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
) -> dict[str, bool]:
    direct_rows = [row for row in usage_rows if row["direct_settlement"]]
    return {
        "artifact_hashes_reproducible": all(
            bool(value)
            for key, value in artifact_bindings.items()
            if key.endswith("_reproducible")
        ),
        "source_issued_leases_present": (
            not policy["require_source_issued_leases"]
            or bool(lease_rows)
            and all(row["source_signature_present"] for row in lease_rows)
        ),
        "access_logs_present": (
            not policy["require_access_logs"]
            or bool(access_rows)
            and all(row["matching_access_log_count"] > 0 for row in coverage_rows)
        ),
        "license_contract_terms_present": (
            not policy["require_license_contract_terms"]
            or all(row["license_contract_term_present"] for row in coverage_rows)
        ),
        "license_contract_terms_allow_use": all(
            row["license_contract_term_allows_use"] or row["escrowed"]
            for row in coverage_rows
        ),
        "direct_sources_have_active_leases": all(
            row["active_lease_count"] > 0 for row in coverage_rows if row["direct_settlement"]
        ),
        "direct_sources_have_region_binding": (
            not policy["require_region_binding_for_direct_sources"]
            or all(row["region_binding_present"] for row in coverage_rows if row["direct_settlement"])
        ),
        "direct_sources_have_access_logs": all(
            row["matching_access_log_count"] > 0
            for row in coverage_rows
            if row["direct_settlement"]
        ),
        "no_direct_settlement_without_active_lease": all(
            row["covered_for_direct_settlement"] for row in coverage_rows if row["direct_settlement"]
        ),
        "denied_or_unleased_sources_escrowed": (
            not policy["require_denied_sources_escrowed"]
            or all(
                row["direct_settlement"] or row["denied_or_unleased_escrowed"] or row["active_lease_count"] > 0
                for row in coverage_rows
            )
        ),
        "private_text_not_disclosed": (
            not _contains_private_fields(
                {
                    "usage_rows": usage_rows,
                    "lease_rows": lease_rows,
                    "access_rows": access_rows,
                    "coverage_rows": coverage_rows,
                }
            )
            and _private_strings_absent(
                {
                    "usage_rows": usage_rows,
                    "lease_rows": lease_rows,
                    "access_rows": access_rows,
                    "coverage_rows": coverage_rows,
                },
                lease_input,
            )
        ),
        "direct_source_count_positive": bool(direct_rows),
    }


def make_source_access_lease_report(
    lease_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    issued_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a replayable source-access lease report."""

    source_secret = lease_input.get("source_signing_secret") or signing_secret
    policy = _policy(lease_input)
    usage_rows = _normalized_usage_rows(lease_input)
    lease_rows = _normalized_lease_rows(
        lease_input,
        source_signing_secret=str(source_secret) if source_secret else None,
    )
    access_rows = _normalized_access_rows(lease_input)
    creator_pool_rate = _decimal(
        lease_input.get("creator_pool_rate")
        or max([row.get("creator_pool_rate") for row in usage_rows] or ["0"])
    )
    artifact_bindings = _artifact_bindings(lease_input)
    coverage_rows = _coverage_rows(
        usage_rows=usage_rows,
        lease_rows=lease_rows,
        access_rows=access_rows,
        creator_license_contract=lease_input.get("creator_license_contract"),
        evidence_region_binding_report=lease_input.get("evidence_region_binding_report"),
        creator_pool_rate=creator_pool_rate,
    )
    checks = _checks(
        lease_input=lease_input,
        policy=policy,
        artifact_bindings=artifact_bindings,
        usage_rows=usage_rows,
        lease_rows=lease_rows,
        access_rows=access_rows,
        coverage_rows=coverage_rows,
    )
    failed = [key for key, value in checks.items() if value is not True]
    status = "ready" if not failed else "needs_review"
    report = {
        "version": SOURCE_ACCESS_LEASE_VERSION,
        "issued_at": issued_at or now_iso(),
        "issuer": issuer,
        "case": {
            "case_id": str(lease_input.get("case_id", "case:source-access-lease")),
            "status": status,
        },
        "policy": policy,
        "artifact_bindings": artifact_bindings,
        "source_usage_rows": usage_rows,
        "lease_rows": lease_rows,
        "access_log_rows": access_rows,
        "coverage_rows": coverage_rows,
        "checks": checks,
        "privacy": {
            "prompt_disclosed": False,
            "output_disclosed": False,
            "source_text_disclosed": False,
            "payment_data_disclosed": False,
            "source_secret_disclosed": False,
            "hash_only_access_logs": True,
        },
        "schemas": {
            "source_access_lease_report": SOURCE_ACCESS_LEASE_SCHEMA,
            "creator_license_contract": "docs/schemas/creator_license_contract.schema.json",
            "source_availability_report": "docs/schemas/source_availability_report.schema.json",
            "evidence_region_binding_report": "docs/schemas/evidence_region_binding_report.schema.json",
        },
        "summary": {
            "status": status,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "source_usage_count": len(usage_rows),
            "direct_source_usage_count": sum(1 for row in usage_rows if row["direct_settlement"]),
            "lease_count": len(lease_rows),
            "access_log_count": len(access_rows),
            "coverage_row_count": len(coverage_rows),
            "covered_direct_source_count": sum(
                1 for row in coverage_rows if row["covered_for_direct_settlement"]
            ),
            "escrowed_denied_or_unleased_count": sum(
                1 for row in coverage_rows if row["denied_or_unleased_escrowed"]
            ),
            "failed_check_count": len(failed),
            "source_access_lease_supported": True,
            "creator_side_access_audit_supported": True,
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    report["lease_report_hash"] = hash_payload(_hashable_report(report))
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


def validate_source_access_lease_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "version",
        "issued_at",
        "issuer",
        "case",
        "policy",
        "artifact_bindings",
        "source_usage_rows",
        "lease_rows",
        "access_log_rows",
        "coverage_rows",
        "checks",
        "privacy",
        "schemas",
        "summary",
        "lease_report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing source access lease report field: {key}")
    if report.get("version") != SOURCE_ACCESS_LEASE_VERSION:
        errors.append("source access lease report version is unsupported")
    if "source_access_lease_report" not in report.get("schemas", {}):
        errors.append("missing source access lease report schema")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("source access lease report target level is not RDLLM-L98")
    for index, row in enumerate(report.get("coverage_rows", [])):
        for key in (
            "source_usage_id",
            "matching_lease_count",
            "matching_access_log_count",
            "active_lease_count",
            "covered_for_direct_settlement",
            "coverage_row_hash",
        ):
            if key not in row:
                errors.append(f"coverage row {index} missing {key}")
    return errors


def verify_source_access_lease_report(
    report: dict[str, Any],
    lease_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a source-access lease report by replaying it from private inputs."""

    errors = validate_source_access_lease_report_shape(report)
    expected = make_source_access_lease_report(
        lease_input,
        issuer=str(report.get("issuer", DEFAULT_ISSUER)),
        issued_at=str(report.get("issued_at", "")) or None,
        signing_secret=signing_secret,
    )
    if report.get("lease_report_hash") != expected.get("lease_report_hash"):
        errors.append("source access lease report hash mismatch")
    if report.get("signature", {}).get("value") != expected.get("signature", {}).get("value"):
        errors.append("source access lease report signature mismatch")
    if report.get("checks") != expected.get("checks"):
        errors.append("source access lease checks mismatch")
    if report.get("summary") != expected.get("summary"):
        errors.append("source access lease summary mismatch")
    if report.get("coverage_rows") != expected.get("coverage_rows"):
        errors.append("source access lease coverage rows mismatch")
    if any(value is not True for value in report.get("checks", {}).values()):
        errors.append("source access lease report has failing checks")
    return errors
