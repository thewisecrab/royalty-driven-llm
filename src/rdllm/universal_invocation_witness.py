"""Non-repudiation witnesses for universal foundation-model invocations.

L134 reconciles deployment logs. This L135 layer adds independently replayable
evidence that those covered native provider calls were observed outside the
operator's own accounting system: provider usage receipts, egress observations,
and independent witness attestations must all bind to the same invocation.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_INVOCATION_WITNESS_VERSION = "rdllm-universal-invocation-witness/v1"
UNIVERSAL_INVOCATION_WITNESS_SCHEMA = "docs/schemas/universal_invocation_witness.schema.json"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L135"
MINIMUM_INPUT_LEVEL = "RDLLM-L134"

DECLARED_HASH_FIELDS = (
    "universal_invocation_witness_hash",
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
    "raw_provider_receipt",
    "raw_egress_payload",
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
    "provider_secret",
    "witness_secret",
    "private_key",
}


def load_universal_invocation_witness_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L135 invocation-witness report."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_invocation_witness_hash", "signature"}
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
    witness_input: dict[str, Any],
) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in witness_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    summary = artifact.get("summary", {})
    return summary if isinstance(summary, dict) else {}


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


def _string_row(row: dict[str, Any], fields: tuple[str, ...]) -> dict[str, str]:
    return {field: str(row.get(field, "")) for field in fields}


def _bool(row: dict[str, Any], field: str, default: bool = False) -> bool:
    value = row.get(field, default)
    return value is True or str(value).lower() == "true"


def _rows_by_key(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key, ""))].append(row)
    return grouped


def _duplicates(values: list[str]) -> list[str]:
    counts = Counter(value for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def _witness_policy(witness_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(witness_input.get("witness_policy", {}))
    return {
        "profile": "rdllm-universal-invocation-witness-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "require_provider_signed_receipts": bool(
            policy.get("require_provider_signed_receipts", True)
        ),
        "require_network_egress_observations": bool(
            policy.get("require_network_egress_observations", True)
        ),
        "required_witness_quorum": int(policy.get("required_witness_quorum", 2) or 2),
        "required_independent_organizations": int(
            policy.get("required_independent_organizations", 2) or 2
        ),
        "on_missing_provider_receipt": "block_nonrepudiation",
        "on_missing_egress_observation": "block_nonrepudiation",
        "on_missing_witness_quorum": "block_nonrepudiation",
        "on_private_text_leak": "block_publication",
    }


def _coverage_call_rows(coverage: dict[str, Any]) -> list[dict[str, Any]]:
    guard_by_invocation = _rows_by_key(
        [
            row
            for row in coverage.get("guard_bindings", [])
            if isinstance(row, dict)
        ],
        "invocation_id",
    )
    gateway_by_invocation = _rows_by_key(
        [
            row
            for row in coverage.get("gateway_rows", [])
            if isinstance(row, dict)
        ],
        "invocation_id",
    )
    calls: list[dict[str, Any]] = []
    for meter in coverage.get("meter_rows", []):
        if not isinstance(meter, dict):
            continue
        invocation_id = str(meter.get("invocation_id", ""))
        guard = guard_by_invocation.get(invocation_id, [{}])[0]
        gateway = gateway_by_invocation.get(invocation_id, [{}])[0]
        call = {
            "invocation_id": invocation_id,
            "request_id": str(meter.get("request_id", "")),
            "meter_event_id": str(meter.get("meter_event_id", "")),
            "guard_hash": str(meter.get("guard_hash") or guard.get("guard_hash", "")),
            "gateway_event_id": str(gateway.get("gateway_event_id", "")),
            "provider_family": str(meter.get("provider_family", "")),
            "route_id": str(meter.get("route_id", "")),
            "native_model": str(meter.get("native_model", "")),
            "request_projection_hash": str(meter.get("request_projection_hash", "")),
            "response_binding_hash": str(meter.get("response_binding_hash", "")),
            "source_footer_delivery_hash": str(
                gateway.get("source_footer_delivery_hash")
                or guard.get("source_footer_delivery_hash", "")
            ),
            "response_envelope_hash": str(
                gateway.get("response_envelope_hash")
                or guard.get("response_envelope_hash", "")
            ),
            "gross_revenue": str(meter.get("gross_revenue", "")),
            "creator_pool": str(meter.get("creator_pool", "")),
        }
        call["coverage_call_hash"] = hash_payload(call)
        calls.append(call)
    return sorted(calls, key=lambda row: row["invocation_id"])


def _coverage_binding(coverage: dict[str, Any] | None) -> dict[str, Any]:
    summary = _summary(coverage)
    return {
        "universal_invocation_coverage_hash": _declared_hash(coverage),
        "hash_reproducible": _artifact_hash_is_reproducible(coverage),
        "status": str(summary.get("status", "")),
        "target_level": str(summary.get("target_certification_level", "")),
        "minimum_input_level": str(summary.get("minimum_input_level", "")),
        "coverage_complete": summary.get("coverage_complete") is True,
        "metered_call_count": int(summary.get("metered_call_count", 0) or 0),
        "guarded_call_count": int(summary.get("guarded_call_count", 0) or 0),
        "uncovered_call_count": int(summary.get("uncovered_call_count", 0) or 0),
    }


def _provider_key_hash(row: dict[str, Any]) -> str:
    if row.get("provider_key_hash"):
        return str(row["provider_key_hash"])
    return hash_payload(
        {
            "provider_id": str(row.get("provider_id", "")),
            "provider_secret": str(row.get("provider_secret", "")),
        }
    )


def _provider_receipt_binding(row: dict[str, Any]) -> dict[str, Any]:
    binding = _string_row(
        row,
        (
            "provider_receipt_id",
            "provider_id",
            "invocation_id",
            "request_id",
            "meter_event_id",
            "guard_hash",
            "provider_family",
            "route_id",
            "native_model",
            "billed_units",
            "usage_units",
            "provider_usage_hash",
            "provider_account_hash",
            "issued_at",
        ),
    )
    binding["provider_key_hash"] = _provider_key_hash(row)
    binding["provider_receipt_hash"] = str(
        row.get("provider_receipt_hash") or hash_payload(binding)
    )
    signature_payload = {
        key: value for key, value in binding.items() if key != "provider_signature"
    }
    binding["provider_signature"] = str(
        row.get("provider_signature")
        or sign_payload(signature_payload, str(row.get("provider_secret", "unsigned-provider")))
    )
    return binding


def _egress_binding(row: dict[str, Any]) -> dict[str, Any]:
    binding = _string_row(
        row,
        (
            "egress_event_id",
            "invocation_id",
            "request_id",
            "guard_hash",
            "provider_family",
            "route_id",
            "native_model",
            "destination_endpoint_hash",
            "observer_id",
            "egress_policy_id",
            "observed_at",
        ),
    )
    binding["allowed_by_gateway"] = _bool(row, "allowed_by_gateway")
    binding["observed_by_independent_collector"] = _bool(
        row, "observed_by_independent_collector"
    )
    binding["egress_hash"] = str(row.get("egress_hash") or hash_payload(binding))
    return binding


def _witness_key_hash(row: dict[str, Any]) -> str:
    if row.get("witness_key_hash"):
        return str(row["witness_key_hash"])
    return hash_payload(
        {
            "witness_id": str(row.get("witness_id", "")),
            "organization_id": str(row.get("organization_id", "")),
            "witness_secret": str(row.get("witness_secret", "")),
        }
    )


def _witness_binding(row: dict[str, Any]) -> dict[str, Any]:
    binding = _string_row(
        row,
        (
            "witness_event_id",
            "witness_id",
            "organization_id",
            "trust_tier",
            "invocation_id",
            "request_id",
            "meter_event_id",
            "guard_hash",
            "provider_receipt_id",
            "egress_event_id",
            "observed_at",
            "replay_verdict",
        ),
    )
    binding["independent"] = _bool(row, "independent")
    binding["saw_provider_receipt"] = _bool(row, "saw_provider_receipt")
    binding["saw_egress_event"] = _bool(row, "saw_egress_event")
    binding["saw_l134_coverage"] = _bool(row, "saw_l134_coverage")
    binding["witness_key_hash"] = _witness_key_hash(row)
    binding["witness_event_hash"] = str(
        row.get("witness_event_hash") or hash_payload(binding)
    )
    signature_payload = {
        key: value for key, value in binding.items() if key != "witness_signature"
    }
    binding["witness_signature"] = str(
        row.get("witness_signature")
        or sign_payload(signature_payload, str(row.get("witness_secret", "unsigned-witness")))
    )
    return binding


def _provider_mismatches(
    call: dict[str, Any],
    receipt: dict[str, Any] | None,
) -> list[dict[str, str]]:
    if receipt is None:
        return []
    mismatches: list[dict[str, str]] = []
    for field in (
        "invocation_id",
        "request_id",
        "meter_event_id",
        "guard_hash",
        "provider_family",
        "route_id",
        "native_model",
    ):
        if str(receipt.get(field, "")) != str(call.get(field, "")):
            mismatches.append(
                {
                    "field": f"provider_receipt.{field}",
                    "coverage": str(call.get(field, "")),
                    "provider_receipt": str(receipt.get(field, "")),
                }
            )
    return mismatches


def _egress_mismatches(
    call: dict[str, Any],
    egress: dict[str, Any] | None,
) -> list[dict[str, str]]:
    if egress is None:
        return []
    mismatches: list[dict[str, str]] = []
    for field in (
        "invocation_id",
        "request_id",
        "guard_hash",
        "provider_family",
        "route_id",
        "native_model",
    ):
        if str(egress.get(field, "")) != str(call.get(field, "")):
            mismatches.append(
                {
                    "field": f"egress_event.{field}",
                    "coverage": str(call.get(field, "")),
                    "egress_event": str(egress.get(field, "")),
                }
            )
    if egress.get("allowed_by_gateway") is not True:
        mismatches.append(
            {
                "field": "egress_event.allowed_by_gateway",
                "coverage": "true",
                "egress_event": str(egress.get("allowed_by_gateway", "")),
            }
        )
    if egress.get("observed_by_independent_collector") is not True:
        mismatches.append(
            {
                "field": "egress_event.observed_by_independent_collector",
                "coverage": "true",
                "egress_event": str(
                    egress.get("observed_by_independent_collector", "")
                ),
            }
        )
    return mismatches


def _witness_mismatches(
    call: dict[str, Any],
    witness: dict[str, Any],
    receipt: dict[str, Any] | None,
    egress: dict[str, Any] | None,
) -> list[dict[str, str]]:
    mismatches: list[dict[str, str]] = []
    for field in ("invocation_id", "request_id", "meter_event_id", "guard_hash"):
        if str(witness.get(field, "")) != str(call.get(field, "")):
            mismatches.append(
                {
                    "field": f"witness.{field}",
                    "coverage": str(call.get(field, "")),
                    "witness": str(witness.get(field, "")),
                }
            )
    if receipt and witness.get("provider_receipt_id") != receipt.get(
        "provider_receipt_id"
    ):
        mismatches.append(
            {
                "field": "witness.provider_receipt_id",
                "provider_receipt": str(receipt.get("provider_receipt_id", "")),
                "witness": str(witness.get("provider_receipt_id", "")),
            }
        )
    if egress and witness.get("egress_event_id") != egress.get("egress_event_id"):
        mismatches.append(
            {
                "field": "witness.egress_event_id",
                "egress_event": str(egress.get("egress_event_id", "")),
                "witness": str(witness.get("egress_event_id", "")),
            }
        )
    for field in ("saw_provider_receipt", "saw_egress_event", "saw_l134_coverage"):
        if witness.get(field) is not True:
            mismatches.append(
                {
                    "field": f"witness.{field}",
                    "required": "true",
                    "witness": str(witness.get(field, "")),
                }
            )
    if witness.get("replay_verdict") != "accepted":
        mismatches.append(
            {
                "field": "witness.replay_verdict",
                "required": "accepted",
                "witness": str(witness.get("replay_verdict", "")),
            }
        )
    return mismatches


def make_universal_invocation_witness(
    witness_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a verifiable L135 non-repudiation report for provider calls."""

    created_at = created_at or now_iso()
    policy = _witness_policy(witness_input)
    coverage = witness_input.get("universal_invocation_coverage", {})
    coverage = coverage if isinstance(coverage, dict) else {}
    coverage_binding = _coverage_binding(coverage)
    coverage_call_rows = _coverage_call_rows(coverage)
    provider_receipt_rows = [
        _provider_receipt_binding(row)
        for row in witness_input.get("provider_signed_receipts", [])
        if isinstance(row, dict)
    ]
    egress_event_rows = [
        _egress_binding(row)
        for row in witness_input.get("network_egress_events", [])
        if isinstance(row, dict)
    ]
    witness_rows = [
        _witness_binding(row)
        for row in witness_input.get("independent_witness_events", [])
        if isinstance(row, dict)
    ]

    calls_by_invocation = _rows_by_key(coverage_call_rows, "invocation_id")
    receipts_by_invocation = _rows_by_key(provider_receipt_rows, "invocation_id")
    egress_by_invocation = _rows_by_key(egress_event_rows, "invocation_id")
    witnesses_by_invocation = _rows_by_key(witness_rows, "invocation_id")

    covered_invocations = {
        row["invocation_id"] for row in coverage_call_rows if row["invocation_id"]
    }
    receipt_invocations = {
        row["invocation_id"] for row in provider_receipt_rows if row["invocation_id"]
    }
    egress_invocations = {
        row["invocation_id"] for row in egress_event_rows if row["invocation_id"]
    }
    witness_invocations = {
        row["invocation_id"] for row in witness_rows if row["invocation_id"]
    }

    duplicate_receipt_invocations = sorted(
        invocation_id
        for invocation_id, rows in receipts_by_invocation.items()
        if invocation_id and len(rows) != 1
    )
    duplicate_egress_invocations = sorted(
        invocation_id
        for invocation_id, rows in egress_by_invocation.items()
        if invocation_id and len(rows) != 1
    )
    duplicate_provider_receipt_ids = _duplicates(
        [row["provider_receipt_id"] for row in provider_receipt_rows]
    )
    duplicate_egress_event_ids = _duplicates(
        [row["egress_event_id"] for row in egress_event_rows]
    )
    duplicate_witness_event_ids = _duplicates(
        [row["witness_event_id"] for row in witness_rows]
    )

    missing_provider_receipt_invocations = sorted(
        covered_invocations - receipt_invocations
    )
    missing_egress_invocations = sorted(covered_invocations - egress_invocations)
    missing_witness_invocations = sorted(covered_invocations - witness_invocations)
    orphan_provider_receipt_invocations = sorted(
        receipt_invocations - covered_invocations
    )
    orphan_egress_invocations = sorted(egress_invocations - covered_invocations)
    orphan_witness_invocations = sorted(witness_invocations - covered_invocations)

    matched: list[dict[str, Any]] = []
    field_mismatches: list[dict[str, str]] = []
    quorum_failures: list[dict[str, Any]] = []
    for call in coverage_call_rows:
        invocation_id = call["invocation_id"]
        receipt = receipts_by_invocation.get(invocation_id, [None])[0]
        egress = egress_by_invocation.get(invocation_id, [None])[0]
        witnesses = witnesses_by_invocation.get(invocation_id, [])
        mismatches = []
        mismatches.extend(_provider_mismatches(call, receipt))
        mismatches.extend(_egress_mismatches(call, egress))
        for witness in witnesses:
            mismatches.extend(_witness_mismatches(call, witness, receipt, egress))

        independent_witnesses = [
            witness
            for witness in witnesses
            if witness.get("independent") is True
            and witness.get("trust_tier") in {"independent", "external", "regulator"}
        ]
        independent_orgs = sorted(
            {
                str(witness.get("organization_id", ""))
                for witness in independent_witnesses
                if witness.get("organization_id")
            }
        )
        call_quorum_failed = (
            len(independent_witnesses) < policy["required_witness_quorum"]
            or len(independent_orgs) < policy["required_independent_organizations"]
        )
        if call_quorum_failed:
            quorum_failures.append(
                {
                    "invocation_id": invocation_id,
                    "independent_witness_count": len(independent_witnesses),
                    "independent_organization_count": len(independent_orgs),
                    "required_witness_quorum": policy["required_witness_quorum"],
                    "required_independent_organizations": policy[
                        "required_independent_organizations"
                    ],
                }
            )
        if receipt and egress and not mismatches and not call_quorum_failed:
            matched.append(
                {
                    "invocation_id": invocation_id,
                    "meter_event_id": call["meter_event_id"],
                    "provider_receipt_id": receipt["provider_receipt_id"],
                    "egress_event_id": egress["egress_event_id"],
                    "witness_event_ids": [
                        witness["witness_event_id"] for witness in witnesses
                    ],
                    "independent_organization_count": len(independent_orgs),
                }
            )
        for mismatch in mismatches:
            field_mismatches.append({"invocation_id": invocation_id, **mismatch})

    provider_signatures_present = all(
        bool(row.get("provider_key_hash"))
        and bool(row.get("provider_receipt_hash"))
        and bool(row.get("provider_signature"))
        for row in provider_receipt_rows
    )
    witness_signatures_present = all(
        bool(row.get("witness_key_hash"))
        and bool(row.get("witness_event_hash"))
        and bool(row.get("witness_signature"))
        for row in witness_rows
    )

    checks = {
        "coverage_report_present": bool(coverage),
        "coverage_hash_reproducible": coverage_binding["hash_reproducible"],
        "coverage_ready_l134": coverage_binding["status"] == "ready"
        and coverage_binding["coverage_complete"] is True
        and _level_at_least(coverage_binding["target_level"], MINIMUM_INPUT_LEVEL),
        "coverage_call_rows_present": bool(coverage_call_rows),
        "provider_signed_receipts_present": bool(provider_receipt_rows)
        if policy["require_provider_signed_receipts"]
        else True,
        "every_covered_call_has_provider_receipt": not missing_provider_receipt_invocations,
        "no_uncovered_provider_receipts": not orphan_provider_receipt_invocations,
        "one_provider_receipt_per_invocation": not duplicate_receipt_invocations,
        "provider_receipt_ids_unique": not duplicate_provider_receipt_ids,
        "provider_receipt_fields_match_coverage": not [
            mismatch
            for mismatch in field_mismatches
            if mismatch["field"].startswith("provider_receipt.")
        ],
        "provider_receipts_signed": provider_signatures_present,
        "network_egress_observations_present": bool(egress_event_rows)
        if policy["require_network_egress_observations"]
        else True,
        "every_covered_call_has_egress_observation": not missing_egress_invocations,
        "no_uncovered_egress_observations": not orphan_egress_invocations,
        "one_egress_event_per_invocation": not duplicate_egress_invocations,
        "egress_event_ids_unique": not duplicate_egress_event_ids,
        "egress_fields_match_coverage": not [
            mismatch
            for mismatch in field_mismatches
            if mismatch["field"].startswith("egress_event.")
        ],
        "independent_witness_events_present": bool(witness_rows),
        "every_covered_call_has_witness_event": not missing_witness_invocations,
        "no_uncovered_witness_events": not orphan_witness_invocations,
        "witness_event_ids_unique": not duplicate_witness_event_ids,
        "witness_quorum_satisfied": not quorum_failures,
        "witnesses_bind_provider_receipt_and_egress": not [
            mismatch
            for mismatch in field_mismatches
            if mismatch["field"].startswith("witness.")
        ],
        "witnesses_signed": witness_signatures_present,
        "private_text_not_disclosed": True,
    }

    reconciliation = {
        "matched_invocations": matched,
        "missing_provider_receipt_invocations": missing_provider_receipt_invocations,
        "missing_egress_invocations": missing_egress_invocations,
        "missing_witness_invocations": missing_witness_invocations,
        "orphan_provider_receipt_invocations": orphan_provider_receipt_invocations,
        "orphan_egress_invocations": orphan_egress_invocations,
        "orphan_witness_invocations": orphan_witness_invocations,
        "duplicate_receipt_invocations": duplicate_receipt_invocations,
        "duplicate_egress_invocations": duplicate_egress_invocations,
        "duplicate_provider_receipt_ids": duplicate_provider_receipt_ids,
        "duplicate_egress_event_ids": duplicate_egress_event_ids,
        "duplicate_witness_event_ids": duplicate_witness_event_ids,
        "quorum_failures": quorum_failures,
        "field_mismatches": field_mismatches,
    }
    checks["private_text_not_disclosed"] = not _contains_private_fields(
        {
            "coverage_binding": coverage_binding,
            "coverage_call_rows": coverage_call_rows,
            "provider_receipt_rows": provider_receipt_rows,
            "egress_event_rows": egress_event_rows,
            "witness_rows": witness_rows,
            "reconciliation": reconciliation,
        }
    )

    failure_modes_by_check = {
        "coverage_report_present": "coverage_report_missing",
        "coverage_hash_reproducible": "coverage_hash_not_reproducible",
        "coverage_ready_l134": "coverage_not_ready_l134",
        "coverage_call_rows_present": "coverage_call_rows_missing",
        "provider_signed_receipts_present": "provider_receipts_missing",
        "every_covered_call_has_provider_receipt": "missing_provider_receipt",
        "no_uncovered_provider_receipts": "uncovered_provider_receipt",
        "one_provider_receipt_per_invocation": "duplicate_provider_receipt_for_invocation",
        "provider_receipt_ids_unique": "duplicate_provider_receipt_id",
        "provider_receipt_fields_match_coverage": "provider_receipt_coverage_mismatch",
        "provider_receipts_signed": "provider_receipt_signature_missing",
        "network_egress_observations_present": "egress_observations_missing",
        "every_covered_call_has_egress_observation": "missing_egress_observation",
        "no_uncovered_egress_observations": "uncovered_egress_observation",
        "one_egress_event_per_invocation": "duplicate_egress_for_invocation",
        "egress_event_ids_unique": "duplicate_egress_event_id",
        "egress_fields_match_coverage": "egress_coverage_mismatch",
        "independent_witness_events_present": "witness_events_missing",
        "every_covered_call_has_witness_event": "missing_witness_event",
        "no_uncovered_witness_events": "uncovered_witness_event",
        "witness_event_ids_unique": "duplicate_witness_event_id",
        "witness_quorum_satisfied": "witness_quorum_missing",
        "witnesses_bind_provider_receipt_and_egress": "witness_binding_mismatch",
        "witnesses_signed": "witness_signature_missing",
        "private_text_not_disclosed": "private_text_leak",
    }
    failed_checks = [key for key, passed in checks.items() if not passed]
    failure_modes = sorted({failure_modes_by_check[key] for key in failed_checks})
    nonrepudiation_ready = not failed_checks

    commitments = {
        "coverage_call_root": merkle_root(
            [hash_payload(row) for row in coverage_call_rows]
        ),
        "provider_receipt_root": merkle_root(
            [hash_payload(row) for row in provider_receipt_rows]
        ),
        "egress_observation_root": merkle_root(
            [hash_payload(row) for row in egress_event_rows]
        ),
        "witness_event_root": merkle_root(
            [hash_payload(row) for row in witness_rows]
        ),
        "reconciliation_root": hash_payload(reconciliation),
    }

    report = {
        "witness_version": UNIVERSAL_INVOCATION_WITNESS_VERSION,
        "issuer": issuer,
        "created_at": created_at,
        "witness_policy": policy,
        "coverage_binding": coverage_binding,
        "coverage_call_rows": coverage_call_rows,
        "provider_receipt_rows": provider_receipt_rows,
        "egress_event_rows": egress_event_rows,
        "witness_rows": witness_rows,
        "nonrepudiation_reconciliation": reconciliation,
        "witness_decision": {
            "decision": "certify_nonrepudiation"
            if nonrepudiation_ready
            else "block_nonrepudiation",
            "nonrepudiation_complete": nonrepudiation_ready,
            "failed_checks": failed_checks,
            "failure_modes": failure_modes,
            "safe_call_policy": "every_l134_covered_call_requires_provider_receipt_egress_and_witness_quorum"
            if nonrepudiation_ready
            else "block_unwitnessed_foundation_provider_invocations",
        },
        "checks": checks,
        "commitments": commitments,
        "schemas": {
            "universal_invocation_witness": UNIVERSAL_INVOCATION_WITNESS_SCHEMA,
            "universal_invocation_coverage": "docs/schemas/universal_invocation_coverage.schema.json",
        },
        "privacy": {
            "private_text_fields_excluded": True,
            "raw_prompts_outputs_sources_excluded": True,
            "provider_and_witness_secrets_excluded": True,
            "provider_receipt_egress_and_witness_rows_are_hash_and_id_only": True,
            "private_strings_absent": True,
        },
        "summary": {
            "status": "ready" if nonrepudiation_ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "covered_call_count": len(coverage_call_rows),
            "provider_receipt_count": len(provider_receipt_rows),
            "egress_event_count": len(egress_event_rows),
            "witness_event_count": len(witness_rows),
            "matched_invocation_count": len(matched),
            "missing_provider_receipt_count": len(missing_provider_receipt_invocations),
            "missing_egress_count": len(missing_egress_invocations),
            "missing_witness_count": len(missing_witness_invocations),
            "quorum_failure_count": len(quorum_failures),
            "field_mismatch_count": len(field_mismatches),
            "nonrepudiation_complete": nonrepudiation_ready,
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
        },
    }
    report["privacy"]["private_strings_absent"] = _private_strings_absent(
        report, witness_input
    )
    report["checks"]["private_text_not_disclosed"] = (
        report["checks"]["private_text_not_disclosed"]
        and report["privacy"]["private_strings_absent"]
    )
    if not report["checks"]["private_text_not_disclosed"]:
        if "private_text_not_disclosed" not in report["witness_decision"]["failed_checks"]:
            report["witness_decision"]["failed_checks"].append(
                "private_text_not_disclosed"
            )
            report["witness_decision"]["failure_modes"].append("private_text_leak")
        report["witness_decision"]["decision"] = "block_nonrepudiation"
        report["witness_decision"]["nonrepudiation_complete"] = False
        report["summary"]["status"] = "blocked"
        report["summary"]["nonrepudiation_complete"] = False
        report["summary"]["failed_check_count"] = len(
            report["witness_decision"]["failed_checks"]
        )
        report["summary"]["failure_mode_count"] = len(
            report["witness_decision"]["failure_modes"]
        )

    report["universal_invocation_witness_hash"] = hash_payload(
        _hashable_report(report)
    )
    report["signature"] = sign_payload(
        report["universal_invocation_witness_hash"], signing_secret or "unsigned"
    )
    return report


def validate_universal_invocation_witness_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "witness_version",
        "issuer",
        "created_at",
        "witness_policy",
        "coverage_binding",
        "coverage_call_rows",
        "provider_receipt_rows",
        "egress_event_rows",
        "witness_rows",
        "nonrepudiation_reconciliation",
        "witness_decision",
        "checks",
        "commitments",
        "schemas",
        "privacy",
        "summary",
        "universal_invocation_witness_hash",
        "signature",
    ]
    for key in required:
        if key not in report:
            errors.append(f"missing universal invocation witness field: {key}")
    if report.get("witness_version") != UNIVERSAL_INVOCATION_WITNESS_VERSION:
        errors.append("universal invocation witness version is unsupported")
    if (
        report.get("schemas", {}).get("universal_invocation_witness")
        != UNIVERSAL_INVOCATION_WITNESS_SCHEMA
    ):
        errors.append("universal invocation witness schema is not declared")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal invocation witness target level is not RDLLM-L135")
    if _contains_private_fields(report):
        errors.append("universal invocation witness exposes private field names")
    return errors


def verify_universal_invocation_witness(
    report: dict[str, Any],
    *,
    witness_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L135 witness report by replaying coverage and witness inputs."""

    errors = validate_universal_invocation_witness_shape(report)
    declared_hash = report.get("universal_invocation_witness_hash")
    if declared_hash != hash_payload(_hashable_report(report)):
        errors.append("universal invocation witness hash is not reproducible")
    expected = make_universal_invocation_witness(
        witness_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at"),
        signing_secret=signing_secret,
    )
    if expected.get("universal_invocation_witness_hash") != report.get(
        "universal_invocation_witness_hash"
    ):
        errors.append("universal invocation witness hash does not match inputs")
    if expected.get("witness_decision") != report.get("witness_decision"):
        errors.append("universal invocation witness decision does not match inputs")
    if expected.get("nonrepudiation_reconciliation") != report.get(
        "nonrepudiation_reconciliation"
    ):
        errors.append("universal invocation witness reconciliation does not match inputs")
    if expected.get("signature") != report.get("signature"):
        errors.append("universal invocation witness signature is invalid")
    if not _private_strings_absent(report, witness_input):
        errors.append("universal invocation witness leaks private replay strings")
    return errors
