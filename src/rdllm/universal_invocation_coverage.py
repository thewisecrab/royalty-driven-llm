"""Deployment-wide coverage for universal foundation-model invocations.

L133 proves one native provider call was authorized before invocation. This
L134 layer proves that the provider's deployment logs, gateway logs, and billing
meters contain no native foundation-model calls outside those L133 guards.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_INVOCATION_COVERAGE_VERSION = "rdllm-universal-invocation-coverage/v1"
UNIVERSAL_INVOCATION_COVERAGE_SCHEMA = (
    "docs/schemas/universal_invocation_coverage.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L134"
MINIMUM_INPUT_LEVEL = "RDLLM-L133"

DECLARED_HASH_FIELDS = (
    "universal_invocation_coverage_hash",
    "universal_invocation_guard_hash",
    "universal_foundation_model_contract_hash",
    "foundation_model_deployment_attestation_hash",
    "foundation_runtime_router_hash",
    "foundation_runtime_adapter_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "report_hash",
    "bundle_hash",
    "summary_hash",
    "envelope_hash",
    "trace_hash",
    "statement_hash",
    "receipt_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "raw_model_output",
    "raw_native_response",
    "native_response_body",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
    "raw_request",
    "raw_response",
    "raw_gateway_payload",
    "raw_meter_payload",
    "raw_invoice_payload",
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


def load_universal_invocation_coverage_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L134 invocation-coverage report."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_invocation_coverage_hash", "signature"}
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


def _contains_private_fields(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key) in PRIVATE_FIELD_NAMES or _contains_private_fields(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_private_fields(child) for child in value)
    return False


def _private_strings_absent(
    report: dict[str, Any],
    coverage_input: dict[str, Any],
) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in coverage_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    summary = artifact.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def _subject(guard: dict[str, Any]) -> dict[str, Any]:
    subject = guard.get("invocation_subject", {})
    return subject if isinstance(subject, dict) else {}


def _level_number(level: Any) -> int | None:
    if not isinstance(level, str) or not level.startswith("RDLLM-L"):
        return None
    try:
        return int(level.removeprefix("RDLLM-L"))
    except ValueError:
        return None


def _level_at_least(level: Any, minimum: str) -> bool:
    level_num = _level_number(level)
    minimum_num = _level_number(minimum)
    return (
        level_num is not None
        and minimum_num is not None
        and level_num >= minimum_num
    )


def _to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _decimal_string(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000001")))


def _string_row(row: dict[str, Any], fields: tuple[str, ...]) -> dict[str, str]:
    return {field: str(row.get(field, "")) for field in fields}


def _bool_row(row: dict[str, Any], fields: tuple[str, ...]) -> dict[str, bool]:
    return {field: row.get(field) is True for field in fields}


def _duplicates(values: list[str]) -> list[str]:
    counts = Counter(value for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def _rows_by_key(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key, ""))].append(row)
    return grouped


def _coverage_policy(coverage_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(coverage_input.get("coverage_policy", {}))
    return {
        "profile": "rdllm-universal-invocation-coverage-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "strict_meter_to_guard_reconciliation": bool(
            policy.get("strict_meter_to_guard_reconciliation", True)
        ),
        "strict_guard_to_meter_reconciliation": bool(
            policy.get("strict_guard_to_meter_reconciliation", True)
        ),
        "require_gateway_log": bool(policy.get("require_gateway_log", True)),
        "require_invoice_rows": bool(policy.get("require_invoice_rows", True)),
        "require_source_footer_for_all_calls": bool(
            policy.get("require_source_footer_for_all_calls", True)
        ),
        "require_response_envelope_for_all_calls": bool(
            policy.get("require_response_envelope_for_all_calls", True)
        ),
        "on_unguarded_native_call": "block_deployment_coverage",
        "on_duplicate_guard": "block_deployment_coverage",
        "on_meter_gateway_drift": "block_deployment_coverage",
        "on_revenue_mismatch": "block_settlement_release",
        "on_private_text_leak": "block_publication",
    }


def _guard_binding(guard: dict[str, Any]) -> dict[str, Any]:
    summary = _summary(guard)
    subject = _subject(guard)
    declared_hash = _declared_hash(guard)
    return {
        "guard_hash": declared_hash,
        "hash_reproducible": _artifact_hash_is_reproducible(guard),
        "status": str(summary.get("status", "")),
        "target_level": str(summary.get("target_certification_level", "")),
        "invocation_id": str(summary.get("invocation_id") or subject.get("invocation_id", "")),
        "request_id": str(summary.get("request_id") or subject.get("request_id", "")),
        "provider_family": str(
            summary.get("selected_provider_family")
            or subject.get("provider_family", "")
        ),
        "route_id": str(summary.get("selected_route_id") or subject.get("route_id", "")),
        "native_model": str(subject.get("native_model", "")),
        "request_projection_hash": str(
            summary.get("request_projection_hash")
            or subject.get("request_projection_hash", "")
        ),
        "response_binding_hash": str(
            summary.get("response_binding_hash")
            or subject.get("response_binding_hash", "")
        ),
        "source_footer_delivery_hash": str(
            subject.get("source_footer_delivery_hash", "")
        ),
        "response_envelope_hash": str(subject.get("response_envelope_hash", "")),
        "preflight_authorized": summary.get("preflight_authorized") is True,
        "native_provider_call_allowed": summary.get("native_provider_call_allowed") is True,
        "source_footer_required": summary.get("source_footer_required") is True,
    }


def _meter_binding(row: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "meter_event_id",
        "invocation_id",
        "request_id",
        "guard_hash",
        "provider_family",
        "route_id",
        "native_model",
        "request_projection_hash",
        "response_binding_hash",
        "billed_units",
        "gross_revenue",
        "creator_pool",
    )
    binding = _string_row(row, fields)
    binding["native_provider_call_observed"] = str(
        row.get("native_provider_call_observed", True) is not False
    ).lower()
    binding["meter_hash"] = str(row.get("meter_hash") or hash_payload(binding))
    return binding


def _gateway_binding(row: dict[str, Any]) -> dict[str, Any]:
    binding = _string_row(
        row,
        (
            "gateway_event_id",
            "invocation_id",
            "request_id",
            "guard_hash",
            "response_envelope_hash",
            "source_footer_delivery_hash",
        ),
    )
    binding.update(
        _bool_row(
            row,
            (
                "preflight_authorized",
                "native_provider_call_allowed",
                "source_footer_required",
            ),
        )
    )
    binding["gateway_hash"] = str(row.get("gateway_hash") or hash_payload(binding))
    return binding


def _invoice_binding(row: dict[str, Any]) -> dict[str, Any]:
    binding = _string_row(
        row,
        (
            "invoice_row_id",
            "meter_event_id",
            "invocation_id",
            "provider_family",
            "billed_units",
            "gross_revenue",
            "creator_pool",
        ),
    )
    binding["invoice_hash"] = str(row.get("invoice_hash") or hash_payload(binding))
    return binding


def _row_mismatches(
    meter: dict[str, Any],
    guard: dict[str, Any] | None,
    gateway: dict[str, Any] | None,
    invoice: dict[str, Any] | None,
) -> list[dict[str, str]]:
    mismatches: list[dict[str, str]] = []
    if guard:
        for field in (
            "request_id",
            "provider_family",
            "route_id",
            "native_model",
            "request_projection_hash",
            "response_binding_hash",
        ):
            if str(meter.get(field, "")) != str(guard.get(field, "")):
                mismatches.append(
                    {
                        "field": field,
                        "meter": str(meter.get(field, "")),
                        "guard": str(guard.get(field, "")),
                    }
                )
        if meter.get("guard_hash") and meter.get("guard_hash") != guard.get("guard_hash"):
            mismatches.append(
                {
                    "field": "guard_hash",
                    "meter": str(meter.get("guard_hash", "")),
                    "guard": str(guard.get("guard_hash", "")),
                }
            )
    if gateway and guard:
        for field in ("request_id", "guard_hash"):
            if str(gateway.get(field, "")) != str(guard.get(field, "")):
                mismatches.append(
                    {
                        "field": f"gateway.{field}",
                        "gateway": str(gateway.get(field, "")),
                        "guard": str(guard.get(field, "")),
                    }
                )
        for field in ("response_envelope_hash", "source_footer_delivery_hash"):
            if str(gateway.get(field, "")) != str(guard.get(field, "")):
                mismatches.append(
                    {
                        "field": f"gateway.{field}",
                        "gateway": str(gateway.get(field, "")),
                        "guard": str(guard.get(field, "")),
                    }
                )
        for field in (
            "preflight_authorized",
            "native_provider_call_allowed",
            "source_footer_required",
        ):
            if gateway.get(field) is not True:
                mismatches.append(
                    {
                        "field": f"gateway.{field}",
                        "gateway": str(gateway.get(field, "")),
                        "guard": "true",
                    }
                )
    if invoice:
        for field in (
            "meter_event_id",
            "invocation_id",
            "provider_family",
            "billed_units",
            "gross_revenue",
        ):
            if str(invoice.get(field, "")) != str(meter.get(field, "")):
                mismatches.append(
                    {
                        "field": f"invoice.{field}",
                        "invoice": str(invoice.get(field, "")),
                        "meter": str(meter.get(field, "")),
                    }
                )
        if invoice.get("creator_pool") and str(invoice.get("creator_pool", "")) != str(
            meter.get("creator_pool", "")
        ):
            mismatches.append(
                {
                    "field": "invoice.creator_pool",
                    "invoice": str(invoice.get("creator_pool", "")),
                    "meter": str(meter.get("creator_pool", "")),
                }
            )
    return mismatches


def make_universal_invocation_coverage(
    coverage_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a verifiable L134 coverage report for all provider invocations."""

    created_at = created_at or now_iso()
    policy = _coverage_policy(coverage_input)
    guards = [
        guard
        for guard in coverage_input.get("universal_invocation_guards", [])
        if isinstance(guard, dict)
    ]
    meter_rows = [
        row for row in coverage_input.get("native_provider_meter_log", []) if isinstance(row, dict)
    ]
    gateway_rows = [
        row for row in coverage_input.get("gateway_access_log", []) if isinstance(row, dict)
    ]
    invoice_rows = [
        row for row in coverage_input.get("provider_invoice_rows", []) if isinstance(row, dict)
    ]

    guard_bindings = [_guard_binding(guard) for guard in guards]
    meter_bindings = [_meter_binding(row) for row in meter_rows]
    gateway_bindings = [_gateway_binding(row) for row in gateway_rows]
    invoice_bindings = [_invoice_binding(row) for row in invoice_rows]

    guards_by_invocation = _rows_by_key(guard_bindings, "invocation_id")
    meters_by_invocation = _rows_by_key(meter_bindings, "invocation_id")
    gateways_by_invocation = _rows_by_key(gateway_bindings, "invocation_id")
    invoices_by_meter = _rows_by_key(invoice_bindings, "meter_event_id")

    guard_invocations = {row["invocation_id"] for row in guard_bindings if row["invocation_id"]}
    meter_invocations = {row["invocation_id"] for row in meter_bindings if row["invocation_id"]}
    gateway_invocations = {
        row["invocation_id"] for row in gateway_bindings if row["invocation_id"]
    }
    invoice_meter_ids = {
        row["meter_event_id"] for row in invoice_bindings if row["meter_event_id"]
    }
    meter_event_ids = {
        row["meter_event_id"] for row in meter_bindings if row["meter_event_id"]
    }

    duplicate_guard_invocations = sorted(
        invocation_id
        for invocation_id, rows in guards_by_invocation.items()
        if invocation_id and len(rows) != 1
    )
    duplicate_meter_invocations = sorted(
        invocation_id
        for invocation_id, rows in meters_by_invocation.items()
        if invocation_id and len(rows) != 1
    )
    duplicate_gateway_invocations = sorted(
        invocation_id
        for invocation_id, rows in gateways_by_invocation.items()
        if invocation_id and len(rows) != 1
    )
    duplicate_invoice_meter_ids = sorted(
        meter_event_id
        for meter_event_id, rows in invoices_by_meter.items()
        if meter_event_id and len(rows) != 1
    )

    matched: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    for meter in meter_bindings:
        invocation_id = meter["invocation_id"]
        guard = guards_by_invocation.get(invocation_id, [None])[0]
        gateway = gateways_by_invocation.get(invocation_id, [None])[0]
        invoice = invoices_by_meter.get(meter["meter_event_id"], [None])[0]
        row_mismatches = _row_mismatches(meter, guard, gateway, invoice)
        if guard and not row_mismatches:
            matched.append(
                {
                    "invocation_id": invocation_id,
                    "meter_event_id": meter["meter_event_id"],
                    "guard_hash": guard["guard_hash"],
                    "gateway_event_id": gateway.get("gateway_event_id", "") if gateway else "",
                    "invoice_row_id": invoice.get("invoice_row_id", "") if invoice else "",
                    "gross_revenue": meter["gross_revenue"],
                    "creator_pool": meter["creator_pool"],
                }
            )
        for mismatch in row_mismatches:
            mismatches.append(
                {
                    "invocation_id": invocation_id,
                    "meter_event_id": meter["meter_event_id"],
                    **mismatch,
                }
            )

    unmatched_meter_invocations = sorted(meter_invocations - guard_invocations)
    unmatched_guard_invocations = sorted(guard_invocations - meter_invocations)
    missing_gateway_invocations = sorted(meter_invocations - gateway_invocations)
    missing_invoice_meter_ids = sorted(meter_event_ids - invoice_meter_ids)
    orphan_invoice_meter_ids = sorted(invoice_meter_ids - meter_event_ids)
    invoice_mismatches = [
        mismatch
        for mismatch in mismatches
        if str(mismatch.get("field", "")).startswith("invoice.")
    ]
    meter_gateway_guard_mismatches = [
        mismatch
        for mismatch in mismatches
        if not str(mismatch.get("field", "")).startswith("invoice.")
    ]
    duplicate_meter_event_ids = _duplicates([row["meter_event_id"] for row in meter_bindings])
    duplicate_gateway_event_ids = _duplicates(
        [row["gateway_event_id"] for row in gateway_bindings]
    )
    duplicate_invoice_row_ids = _duplicates(
        [row["invoice_row_id"] for row in invoice_bindings]
    )

    meter_gross_total = sum(
        (_to_decimal(row.get("gross_revenue")) for row in meter_bindings),
        Decimal("0"),
    )
    invoice_gross_total = sum(
        (_to_decimal(row.get("gross_revenue")) for row in invoice_bindings),
        Decimal("0"),
    )
    creator_pool_total = sum(
        (_to_decimal(row.get("creator_pool")) for row in meter_bindings),
        Decimal("0"),
    )

    checks = {
        "required_guard_artifacts_present": bool(guard_bindings),
        "guard_hashes_reproducible": all(
            row["hash_reproducible"] for row in guard_bindings
        ),
        "guards_ready_l133": all(
            row["status"] == "ready"
            and _level_at_least(row["target_level"], MINIMUM_INPUT_LEVEL)
            and row["preflight_authorized"]
            and row["native_provider_call_allowed"]
            for row in guard_bindings
        ),
        "meter_log_present": bool(meter_bindings),
        "gateway_log_present": bool(gateway_bindings)
        if policy["require_gateway_log"]
        else True,
        "invoice_rows_present": bool(invoice_bindings)
        if policy["require_invoice_rows"]
        else True,
        "every_metered_call_has_guard": not unmatched_meter_invocations,
        "every_guard_has_metered_call": not unmatched_guard_invocations
        if policy["strict_guard_to_meter_reconciliation"]
        else True,
        "one_guard_per_invocation": not duplicate_guard_invocations,
        "one_meter_event_per_invocation": not duplicate_meter_invocations,
        "one_gateway_event_per_invocation": not duplicate_gateway_invocations
        if policy["require_gateway_log"]
        else True,
        "meter_gateway_guard_fields_match": not meter_gateway_guard_mismatches
        and not missing_gateway_invocations
        if policy["require_gateway_log"]
        else not meter_gateway_guard_mismatches,
        "invoice_rows_match_meter_log": not missing_invoice_meter_ids
        and not orphan_invoice_meter_ids
        and not duplicate_invoice_meter_ids
        and not duplicate_invoice_row_ids
        and not invoice_mismatches
        if policy["require_invoice_rows"]
        else True,
        "source_footer_required_for_all_calls": all(
            row["source_footer_required"] and bool(row["source_footer_delivery_hash"])
            for row in guard_bindings
        )
        if policy["require_source_footer_for_all_calls"]
        else True,
        "response_envelope_bound_for_all_calls": all(
            bool(row["response_envelope_hash"]) for row in guard_bindings
        )
        if policy["require_response_envelope_for_all_calls"]
        else True,
        "gross_revenue_conserved": meter_gross_total == invoice_gross_total
        if policy["require_invoice_rows"]
        else True,
        "creator_pool_not_missing": bool(meter_bindings)
        and all(_to_decimal(row.get("creator_pool")) > Decimal("0") for row in meter_bindings),
        "private_text_not_disclosed": True,
    }

    reconciliation = {
        "matched_invocations": matched,
        "unmatched_meter_invocations": unmatched_meter_invocations,
        "unmatched_guard_invocations": unmatched_guard_invocations,
        "missing_gateway_invocations": missing_gateway_invocations,
        "missing_invoice_meter_ids": missing_invoice_meter_ids,
        "orphan_invoice_meter_ids": orphan_invoice_meter_ids,
        "duplicate_guard_invocations": duplicate_guard_invocations,
        "duplicate_meter_invocations": duplicate_meter_invocations,
        "duplicate_gateway_invocations": duplicate_gateway_invocations,
        "duplicate_invoice_meter_ids": duplicate_invoice_meter_ids,
        "duplicate_meter_event_ids": duplicate_meter_event_ids,
        "duplicate_gateway_event_ids": duplicate_gateway_event_ids,
        "duplicate_invoice_row_ids": duplicate_invoice_row_ids,
        "field_mismatches": mismatches,
        "meter_gross_revenue_total": _decimal_string(meter_gross_total),
        "invoice_gross_revenue_total": _decimal_string(invoice_gross_total),
        "creator_pool_total": _decimal_string(creator_pool_total),
    }

    checks["private_text_not_disclosed"] = not _contains_private_fields(
        {
            "guard_bindings": guard_bindings,
            "meter_rows": meter_bindings,
            "gateway_rows": gateway_bindings,
            "invoice_rows": invoice_bindings,
            "reconciliation": reconciliation,
        }
    )

    failure_modes_by_check = {
        "required_guard_artifacts_present": "guard_artifact_missing",
        "guard_hashes_reproducible": "guard_hash_not_reproducible",
        "guards_ready_l133": "guard_not_ready_l133",
        "meter_log_present": "provider_meter_log_missing",
        "gateway_log_present": "gateway_log_missing",
        "invoice_rows_present": "invoice_rows_missing",
        "every_metered_call_has_guard": "unguarded_native_provider_call",
        "every_guard_has_metered_call": "orphan_guard_without_meter_event",
        "one_guard_per_invocation": "duplicate_guard_for_invocation",
        "one_meter_event_per_invocation": "duplicate_meter_for_invocation",
        "one_gateway_event_per_invocation": "duplicate_gateway_for_invocation",
        "meter_gateway_guard_fields_match": "meter_gateway_guard_mismatch",
        "invoice_rows_match_meter_log": "invoice_meter_mismatch",
        "source_footer_required_for_all_calls": "source_footer_coverage_missing",
        "response_envelope_bound_for_all_calls": "response_envelope_coverage_missing",
        "gross_revenue_conserved": "gross_revenue_not_conserved",
        "creator_pool_not_missing": "creator_pool_missing",
        "private_text_not_disclosed": "private_text_leak",
    }
    failed_checks = [key for key, passed in checks.items() if not passed]
    failure_modes = sorted({failure_modes_by_check[key] for key in failed_checks})
    coverage_ready = not failed_checks

    commitments = {
        "guard_binding_root": merkle_root(
            [hash_payload(binding) for binding in guard_bindings]
        ),
        "meter_log_root": merkle_root(
            [hash_payload(binding) for binding in meter_bindings]
        ),
        "gateway_log_root": merkle_root(
            [hash_payload(binding) for binding in gateway_bindings]
        ),
        "invoice_row_root": merkle_root(
            [hash_payload(binding) for binding in invoice_bindings]
        ),
        "reconciliation_root": hash_payload(reconciliation),
    }

    report = {
        "coverage_version": UNIVERSAL_INVOCATION_COVERAGE_VERSION,
        "issuer": issuer,
        "created_at": created_at,
        "coverage_policy": policy,
        "guard_bindings": guard_bindings,
        "meter_rows": meter_bindings,
        "gateway_rows": gateway_bindings,
        "invoice_rows": invoice_bindings,
        "reconciliation": reconciliation,
        "coverage_decision": {
            "decision": "certify_coverage" if coverage_ready else "block_deployment_coverage",
            "coverage_complete": coverage_ready,
            "failed_checks": failed_checks,
            "failure_modes": failure_modes,
            "safe_call_policy": "every_native_provider_call_requires_one_l133_guard"
            if coverage_ready
            else "block_uncovered_native_provider_invocations",
        },
        "checks": checks,
        "commitments": commitments,
        "schemas": {
            "universal_invocation_coverage": UNIVERSAL_INVOCATION_COVERAGE_SCHEMA,
            "universal_invocation_guard": "docs/schemas/universal_invocation_guard.schema.json",
        },
        "privacy": {
            "private_text_fields_excluded": True,
            "raw_prompts_outputs_sources_excluded": True,
            "meter_gateway_invoice_rows_are_hash_and_id_only": True,
            "private_strings_absent": True,
        },
        "summary": {
            "status": "ready" if coverage_ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "metered_call_count": len(meter_bindings),
            "guarded_call_count": len(guard_bindings),
            "matched_call_count": len(matched),
            "uncovered_call_count": len(unmatched_meter_invocations),
            "orphan_guard_count": len(unmatched_guard_invocations),
            "duplicate_guard_count": len(duplicate_guard_invocations),
            "field_mismatch_count": len(mismatches),
            "gross_revenue_total": _decimal_string(meter_gross_total),
            "creator_pool_total": _decimal_string(creator_pool_total),
            "coverage_complete": coverage_ready,
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
        },
    }
    report["privacy"]["private_strings_absent"] = _private_strings_absent(
        report, coverage_input
    )
    report["checks"]["private_text_not_disclosed"] = (
        report["checks"]["private_text_not_disclosed"]
        and report["privacy"]["private_strings_absent"]
    )
    if not report["checks"]["private_text_not_disclosed"]:
        if "private_text_not_disclosed" not in report["coverage_decision"]["failed_checks"]:
            report["coverage_decision"]["failed_checks"].append(
                "private_text_not_disclosed"
            )
            report["coverage_decision"]["failure_modes"].append("private_text_leak")
        report["coverage_decision"]["decision"] = "block_deployment_coverage"
        report["coverage_decision"]["coverage_complete"] = False
        report["summary"]["status"] = "blocked"
        report["summary"]["coverage_complete"] = False
        report["summary"]["failed_check_count"] = len(
            report["coverage_decision"]["failed_checks"]
        )
        report["summary"]["failure_mode_count"] = len(
            report["coverage_decision"]["failure_modes"]
        )

    report["universal_invocation_coverage_hash"] = hash_payload(
        _hashable_report(report)
    )
    report["signature"] = sign_payload(
        report["universal_invocation_coverage_hash"], signing_secret
    )
    return report


def validate_universal_invocation_coverage_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "coverage_version",
        "issuer",
        "created_at",
        "coverage_policy",
        "guard_bindings",
        "meter_rows",
        "gateway_rows",
        "invoice_rows",
        "reconciliation",
        "coverage_decision",
        "checks",
        "commitments",
        "schemas",
        "privacy",
        "summary",
        "universal_invocation_coverage_hash",
        "signature",
    ]
    for key in required:
        if key not in report:
            errors.append(f"missing universal invocation coverage field: {key}")
    if report.get("coverage_version") != UNIVERSAL_INVOCATION_COVERAGE_VERSION:
        errors.append("universal invocation coverage version is unsupported")
    if (
        report.get("schemas", {}).get("universal_invocation_coverage")
        != UNIVERSAL_INVOCATION_COVERAGE_SCHEMA
    ):
        errors.append("universal invocation coverage schema is not declared")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal invocation coverage target level is not RDLLM-L134")
    if _contains_private_fields(report):
        errors.append("universal invocation coverage exposes private field names")
    return errors


def verify_universal_invocation_coverage(
    report: dict[str, Any],
    *,
    coverage_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L134 coverage report by replaying provider logs and guards."""

    errors = validate_universal_invocation_coverage_shape(report)
    declared_hash = report.get("universal_invocation_coverage_hash")
    if declared_hash != hash_payload(_hashable_report(report)):
        errors.append("universal invocation coverage hash is not reproducible")
    expected = make_universal_invocation_coverage(
        coverage_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at"),
        signing_secret=signing_secret,
    )
    if expected.get("universal_invocation_coverage_hash") != report.get(
        "universal_invocation_coverage_hash"
    ):
        errors.append("universal invocation coverage hash does not match inputs")
    if expected.get("coverage_decision") != report.get("coverage_decision"):
        errors.append("universal invocation coverage decision does not match inputs")
    if expected.get("reconciliation") != report.get("reconciliation"):
        errors.append("universal invocation coverage reconciliation does not match inputs")
    if expected.get("signature") != report.get("signature"):
        errors.append("universal invocation coverage signature is invalid")
    if not _private_strings_absent(report, coverage_input):
        errors.append("universal invocation coverage leaks private replay strings")
    return errors
