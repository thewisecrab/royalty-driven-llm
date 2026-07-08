"""Universal production invocation admission.

The L170 layer turns L169 provider conformance runner receipts into live
production admission control. A provider route can pass conformance fixtures and
still be bypassed at runtime by a stale model alias, direct native API call,
missing telemetry span, missing source-footer gate, or settlement meter that is
not bound to the actual response. This artifact requires a signed admission
token for every production provider family before invocation, response release,
source-footer reliance, tool/MCP execution, retrieval grounding, or creator
settlement is allowed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.provider_family_registry import CANONICAL_PROVIDER_FAMILIES
from rdllm.transparency import merkle_root

UNIVERSAL_PRODUCTION_INVOCATION_ADMISSION_VERSION = (
    "rdllm-universal-production-invocation-admission/v1"
)
UNIVERSAL_PRODUCTION_INVOCATION_ADMISSION_SCHEMA = (
    "docs/schemas/universal_production_invocation_admission.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L170"
MINIMUM_PROVIDER_CONFORMANCE_LEVEL = "RDLLM-L169"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-production-invocation-admission.json"
)

REQUIRED_PROVIDER_FAMILIES = CANONICAL_PROVIDER_FAMILIES

REQUIRED_ADMISSION_GATES = (
    "preflight_admission_token",
    "provider_route_resolution",
    "model_alias_resolution",
    "tenant_auth_scope",
    "retrieval_source_gate",
    "tool_mcp_authorization",
    "streaming_chunk_gate",
    "response_footer_gate",
    "copy_export_gate",
    "settlement_meter_gate",
    "revocation_gate",
    "telemetry_trace_gate",
    "auditor_witness_gate",
    "public_status_gate",
)

REQUIRED_INVOCATION_SURFACES = (
    "sync_generation",
    "streaming_generation",
    "tool_calls",
    "mcp_tool_calls",
    "retrieval_or_grounding",
    "batch_job",
    "webhook_callback",
    "fallback_model",
    "cache_reuse",
    "copy_export",
    "client_sdk",
    "gateway_proxy",
    "local_runtime",
    "rag_native",
    "auditor_export",
)

REQUIRED_NEGATIVE_ADMISSION_FAILURES = (
    "missing_l169_conformance_receipt",
    "stale_l169_conformance_receipt",
    "provider_family_mismatch",
    "route_not_in_l168_matrix",
    "model_alias_drift",
    "missing_negotiated_contract",
    "missing_invocation_guard",
    "telemetry_span_missing",
    "source_footer_gate_missing",
    "settlement_meter_unbound",
    "revocation_snapshot_stale",
    "streaming_chunk_without_admission",
    "tool_call_without_scope",
    "cache_reuse_without_admission",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_production_invocation_admission_hash",
    "universal_provider_conformance_runner_receipt_hash",
    "universal_foundation_provider_binding_matrix_hash",
    "universal_negotiated_invocation_enforcement_hash",
    "universal_invocation_guard_hash",
    "universal_invocation_coverage_hash",
    "universal_invocation_witness_hash",
    "universal_emission_enforcement_gateway_hash",
    "universal_provider_drift_sentinel_hash",
    "admission_token_hash",
    "route_admission_hash",
    "trace_hash",
    "span_hash",
    "receipt_hash",
    "attestation_hash",
    "report_hash",
    "manifest_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "query_text",
    "output",
    "output_text",
    "answer_text",
    "raw_answer_text",
    "raw_model_output",
    "raw_native_request",
    "raw_native_response",
    "native_response_body",
    "streaming_transcript",
    "source_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
    "customer_id",
    "customer_email",
    "billing_record",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "authorization",
    "access_token",
    "refresh_token",
    "oauth_token",
    "api_key",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_production_invocation_admission_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L170 production admission artifact."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_admission(admission: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in admission.items()
        if key not in {"universal_production_invocation_admission_hash", "signature"}
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


def _summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact, dict):
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
    current = _level_number(level)
    required = _level_number(minimum)
    return current is not None and required is not None and current >= required


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


def _private_strings_absent(
    public_payload: dict[str, Any],
    admission_input: dict[str, Any],
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in admission_input.get("private_strings", [])
        if isinstance(item, str) and len(item) >= 8
    ]
    return all(item not in public_json for item in private_strings)


def _provider_conformance_l169_ready(receipt: dict[str, Any] | None) -> bool:
    if not isinstance(receipt, dict):
        return False
    summary = _summary(receipt)
    decision = receipt.get("conformance_runner_decision", {})
    return (
        summary.get("status") == "ready"
        and _level_at_least(
            summary.get("target_certification_level", ""),
            MINIMUM_PROVIDER_CONFORMANCE_LEVEL,
        )
        and isinstance(decision, dict)
        and decision.get("conformance_runner_receipt_ready") is True
        and decision.get("provider_onboarding_allowed") is True
        and decision.get("bound_route_invocation_allowed") is True
        and decision.get("source_footer_reliance_allowed") is True
        and decision.get("creator_settlement_allowed_for_replayed_routes") is True
    )


def _gate_ready(row: dict[str, Any]) -> bool:
    required_hashes = ("gate_hash", "policy_hash", "evidence_hash", "verifier_hash")
    required_flags = (
        "configured",
        "enforced",
        "l169_bound",
        "telemetry_bound",
        "fail_closed",
        "public_or_auditor_accessible",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _provider_admission_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "admission_token_hash",
        "provider_route_hash",
        "model_alias_hash",
        "tenant_scope_hash",
        "l169_receipt_hash",
        "l168_matrix_hash",
        "negotiated_contract_hash",
        "invocation_guard_hash",
        "drift_sentinel_hash",
        "telemetry_span_hash",
        "source_footer_gate_hash",
        "settlement_meter_hash",
        "revocation_snapshot_hash",
        "admission_decision_hash",
        "verifier_hash",
    )
    required_flags = (
        "provider_identity_matched",
        "route_in_l168_matrix",
        "l169_receipt_bound",
        "l169_receipt_fresh",
        "drift_sentinel_green",
        "negotiated_contract_bound",
        "invocation_guard_bound",
        "telemetry_span_opened",
        "source_footer_gate_bound",
        "settlement_hold_until_footer",
        "revocation_checked",
        "all_invocation_surfaces_admitted",
        "fail_closed",
        "private_payloads_excluded",
    )
    if not all(str(row.get(field, "")) for field in required_hashes):
        return False
    if not all(row.get(flag) is True for flag in required_flags):
        return False
    surfaces = row.get("invocation_surfaces", {})
    if not isinstance(surfaces, dict):
        return False
    return all(surfaces.get(surface) == "admitted" for surface in REQUIRED_INVOCATION_SURFACES)


def _negative_failure_ready(row: dict[str, Any]) -> bool:
    return bool(row.get("fixture_hash")) and all(
        row.get(flag) is True
        for flag in (
            "expected_reject",
            "observed_reject",
            "admission_token_denied",
            "provider_invocation_blocked",
            "response_release_blocked",
            "source_footer_reliance_blocked",
            "tool_mcp_execution_blocked",
            "settlement_held",
            "public_status_marked_failed",
        )
    )


def _complete_rows(
    rows: dict[str, dict[str, Any]],
    required: tuple[str, ...],
    predicate: Any,
) -> tuple[list[str], list[str]]:
    missing = [name for name in required if name not in rows]
    incomplete = [
        name
        for name in required
        if name in rows and not predicate(rows.get(name, {}))
    ]
    return missing, incomplete


def _row_map(admission_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    rows = admission_input.get(key, {})
    return rows if isinstance(rows, dict) else {}


def make_universal_production_invocation_admission(
    admission_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L170 universal production invocation admission artifact."""

    conformance_receipt = admission_input.get(
        "universal_provider_conformance_runner_receipt"
    )
    provider_rows = _row_map(admission_input, "provider_admission_rows")
    gate_rows = _row_map(admission_input, "admission_gate_rows")
    negative_rows = _row_map(admission_input, "negative_admission_rows")

    missing_providers, incomplete_providers = _complete_rows(
        provider_rows, REQUIRED_PROVIDER_FAMILIES, _provider_admission_ready
    )
    missing_gates, incomplete_gates = _complete_rows(
        gate_rows, REQUIRED_ADMISSION_GATES, _gate_ready
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows, REQUIRED_NEGATIVE_ADMISSION_FAILURES, _negative_failure_ready
    )

    provider_surface_coverage = {
        provider: sorted(
            surface
            for surface in REQUIRED_INVOCATION_SURFACES
            if provider_rows.get(provider, {})
            .get("invocation_surfaces", {})
            .get(surface)
            == "admitted"
        )
        for provider in REQUIRED_PROVIDER_FAMILIES
    }
    gate_coverage = sorted(
        gate for gate in REQUIRED_ADMISSION_GATES if _gate_ready(gate_rows.get(gate, {}))
    )

    checks = {
        "provider_conformance_receipt_bound": _artifact_hash_is_reproducible(
            conformance_receipt if isinstance(conformance_receipt, dict) else None
        ),
        "provider_conformance_receipt_l169_ready": _provider_conformance_l169_ready(
            conformance_receipt if isinstance(conformance_receipt, dict) else None
        ),
        "provider_admission_rows_complete": not missing_providers
        and not incomplete_providers,
        "admission_gate_rows_complete": not missing_gates and not incomplete_gates,
        "provider_invocation_surface_coverage_complete": all(
            len(provider_surface_coverage.get(provider, []))
            == len(REQUIRED_INVOCATION_SURFACES)
            for provider in REQUIRED_PROVIDER_FAMILIES
        ),
        "negative_admission_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "production_invocation_admission_signed": bool(signing_secret),
    }
    failure_modes = [name for name, passed in checks.items() if not passed]

    admission_without_privacy: dict[str, Any] = {
        "universal_production_invocation_admission_version": (
            UNIVERSAL_PRODUCTION_INVOCATION_ADMISSION_VERSION
        ),
        "schema": UNIVERSAL_PRODUCTION_INVOCATION_ADMISSION_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": "rdllm-universal-production-invocation-admission-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_provider_conformance_level": MINIMUM_PROVIDER_CONFORMANCE_LEVEL,
            "per_invocation_admission_required": True,
            "l169_receipt_required": True,
            "live_drift_check_required": True,
            "telemetry_span_required_before_provider_call": True,
            "source_footer_gate_required_before_response_release": True,
            "settlement_hold_required_until_footer_release": True,
            "private_payloads_forbidden_in_public_admission": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_PRODUCTION_INVOCATION_ADMISSION_VERSION,
        },
        "provider_conformance_receipt_binding": {
            "present": isinstance(conformance_receipt, dict) and bool(conformance_receipt),
            "artifact_hash": _declared_hash(
                conformance_receipt if isinstance(conformance_receipt, dict) else None
            ),
            "payload_hash": hash_payload(
                _hashable_artifact(
                    conformance_receipt if isinstance(conformance_receipt, dict) else None
                )
            ),
            "hash_reproducible": _artifact_hash_is_reproducible(
                conformance_receipt if isinstance(conformance_receipt, dict) else None
            ),
            "status": str(_summary(conformance_receipt).get("status", "")),
            "level": str(
                _summary(conformance_receipt).get("target_certification_level", "")
            ),
        },
        "provider_admission_rows": {
            provider: provider_rows.get(provider, {})
            for provider in REQUIRED_PROVIDER_FAMILIES
        },
        "admission_gate_rows": {
            gate: gate_rows.get(gate, {}) for gate in REQUIRED_ADMISSION_GATES
        },
        "negative_admission_rows": {
            failure: negative_rows.get(failure, {})
            for failure in REQUIRED_NEGATIVE_ADMISSION_FAILURES
        },
        "evidence_roots": {
            "provider_admission_root": merkle_root(
                [
                    hash_payload(
                        {"provider": provider, "row": provider_rows.get(provider, {})}
                    )
                    for provider in REQUIRED_PROVIDER_FAMILIES
                ]
            ),
            "admission_gate_root": merkle_root(
                [
                    hash_payload({"gate": gate, "row": gate_rows.get(gate, {})})
                    for gate in REQUIRED_ADMISSION_GATES
                ]
            ),
            "invocation_surface_root": merkle_root(
                [
                    hash_payload(
                        {
                            "provider": provider,
                            "surface": surface,
                            "status": provider_rows.get(provider, {})
                            .get("invocation_surfaces", {})
                            .get(surface, ""),
                        }
                    )
                    for provider in REQUIRED_PROVIDER_FAMILIES
                    for surface in REQUIRED_INVOCATION_SURFACES
                ]
            ),
            "negative_admission_root": merkle_root(
                [
                    hash_payload(
                        {"failure": failure, "row": negative_rows.get(failure, {})}
                    )
                    for failure in REQUIRED_NEGATIVE_ADMISSION_FAILURES
                ]
            ),
        },
        "checks": checks,
        "admission_decision": {
            "production_invocation_admission_ready": not failure_modes,
            "live_provider_invocation_allowed": not failure_modes,
            "response_release_allowed": not failure_modes,
            "source_footer_reliance_allowed": not failure_modes,
            "tool_mcp_execution_allowed": not failure_modes,
            "retrieval_grounding_allowed": not failure_modes,
            "settlement_metering_allowed": not failure_modes,
            "provider_procurement_reliance_allowed": not failure_modes,
            "unadmitted_provider_routes_blocked": True,
            "failure_modes": failure_modes,
            "missing_provider_admissions": missing_providers,
            "incomplete_provider_admissions": incomplete_providers,
            "missing_admission_gates": missing_gates,
            "incomplete_admission_gates": incomplete_gates,
            "missing_negative_admission_failures": missing_negative,
            "incomplete_negative_admission_failures": incomplete_negative,
        },
        "admission_coverage": {
            "required_provider_family_count": len(REQUIRED_PROVIDER_FAMILIES),
            "ready_provider_admission_count": sum(
                1
                for provider in REQUIRED_PROVIDER_FAMILIES
                if _provider_admission_ready(provider_rows.get(provider, {}))
            ),
            "required_admission_gate_count": len(REQUIRED_ADMISSION_GATES),
            "ready_admission_gate_count": len(gate_coverage),
            "required_invocation_surface_count": len(REQUIRED_INVOCATION_SURFACES),
            "provider_surface_coverage": provider_surface_coverage,
            "admission_gate_coverage": gate_coverage,
        },
        "standards_and_research": {
            "runtime_observability": (
                "OpenTelemetry GenAI motivates production spans for model calls, "
                "tool calls, and agent sessions."
            ),
            "tool_authorization": (
                "MCP authorization and resource indicators motivate scoped "
                "tool/MCP admission before execution."
            ),
            "workflow_replay": (
                "OpenAPI and Arazzo motivate explicit API workflow and route "
                "admission surfaces."
            ),
            "attested_admission": (
                "SLSA, in-toto, and SCITT motivate signed admission evidence and "
                "transparent publication."
            ),
        },
    }
    privacy = {
        "private_payload_fields": _contains_private_fields(admission_without_privacy),
        "private_strings_absent": _private_strings_absent(
            admission_without_privacy, admission_input
        ),
    }
    admission = {
        **admission_without_privacy,
        "privacy": {
            **privacy,
            "private_payloads_excluded": not privacy["private_payload_fields"]
            and privacy["private_strings_absent"],
        },
    }
    admission["summary"] = {
        "status": "ready"
        if not failure_modes and admission["privacy"]["private_payloads_excluded"]
        else "blocked",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_provider_conformance_level": MINIMUM_PROVIDER_CONFORMANCE_LEVEL,
        "provider_family_count": len(REQUIRED_PROVIDER_FAMILIES),
        "ready_provider_admission_count": admission["admission_coverage"][
            "ready_provider_admission_count"
        ],
        "admission_gate_count": len(REQUIRED_ADMISSION_GATES),
        "ready_admission_gate_count": admission["admission_coverage"][
            "ready_admission_gate_count"
        ],
        "invocation_surface_count": len(REQUIRED_INVOCATION_SURFACES),
        "negative_admission_failure_count": len(REQUIRED_NEGATIVE_ADMISSION_FAILURES),
        "failure_mode_count": len(failure_modes),
        "privacy_preserved": admission["privacy"]["private_payloads_excluded"],
        "signed_production_invocation_admission": bool(signing_secret),
    }
    admission["universal_production_invocation_admission_hash"] = hash_payload(
        _hashable_admission(admission)
    )
    if signing_secret:
        admission["signature"] = {
            "issuer": issuer,
            "algorithm": "HMAC-SHA256",
            "value": sign_payload(_hashable_admission(admission), signing_secret),
        }
    return admission


def validate_universal_production_invocation_admission_shape(
    admission: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for an L170 admission artifact."""

    errors: list[str] = []
    required = (
        "universal_production_invocation_admission_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "provider_conformance_receipt_binding",
        "provider_admission_rows",
        "admission_gate_rows",
        "negative_admission_rows",
        "evidence_roots",
        "checks",
        "admission_decision",
        "admission_coverage",
        "privacy",
        "summary",
        "universal_production_invocation_admission_hash",
    )
    for key in required:
        if key not in admission:
            errors.append(f"missing {key}")
    if admission.get("universal_production_invocation_admission_version") != (
        UNIVERSAL_PRODUCTION_INVOCATION_ADMISSION_VERSION
    ):
        errors.append("unexpected universal_production_invocation_admission_version")
    if admission.get("schema") != UNIVERSAL_PRODUCTION_INVOCATION_ADMISSION_SCHEMA:
        errors.append("unexpected schema")
    if _contains_private_fields(admission):
        errors.append("public admission contains private field names")
    provider_rows = admission.get("provider_admission_rows", {})
    if not isinstance(provider_rows, dict):
        errors.append("provider_admission_rows must be object")
    else:
        missing, incomplete = _complete_rows(
            provider_rows, REQUIRED_PROVIDER_FAMILIES, _provider_admission_ready
        )
        errors.extend(f"missing provider admission {name}" for name in missing)
        errors.extend(f"incomplete provider admission {name}" for name in incomplete)
    gate_rows = admission.get("admission_gate_rows", {})
    if not isinstance(gate_rows, dict):
        errors.append("admission_gate_rows must be object")
    else:
        missing, incomplete = _complete_rows(
            gate_rows, REQUIRED_ADMISSION_GATES, _gate_ready
        )
        errors.extend(f"missing admission gate {name}" for name in missing)
        errors.extend(f"incomplete admission gate {name}" for name in incomplete)
    negative_rows = admission.get("negative_admission_rows", {})
    if not isinstance(negative_rows, dict):
        errors.append("negative_admission_rows must be object")
    else:
        missing, incomplete = _complete_rows(
            negative_rows, REQUIRED_NEGATIVE_ADMISSION_FAILURES, _negative_failure_ready
        )
        errors.extend(f"missing negative admission fixture {name}" for name in missing)
        errors.extend(f"incomplete negative admission fixture {name}" for name in incomplete)
    return errors


def verify_universal_production_invocation_admission(
    admission_input: dict[str, Any],
    admission: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L170 production admission artifact against replay input."""

    errors = validate_universal_production_invocation_admission_shape(admission)
    expected_hash = hash_payload(_hashable_admission(admission))
    if admission.get("universal_production_invocation_admission_hash") != expected_hash:
        errors.append("universal_production_invocation_admission_hash mismatch")
    if signing_secret and "signature" not in admission:
        errors.append("missing signature")
    if signing_secret:
        signature = admission.get("signature", {})
        expected_signature = sign_payload(_hashable_admission(admission), signing_secret)
        if signature.get("value") != expected_signature:
            errors.append("signature mismatch")
    replayed = make_universal_production_invocation_admission(
        admission_input,
        issuer=admission.get("issuer", DEFAULT_ISSUER),
        created_at=admission.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get("universal_production_invocation_admission_hash") != admission.get(
        "universal_production_invocation_admission_hash"
    ):
        errors.append("replay hash mismatch")
    if replayed.get("summary", {}).get("status") != admission.get("summary", {}).get("status"):
        errors.append("replay status mismatch")
    if admission.get("summary", {}).get("status") != "ready":
        errors.append("production invocation admission is not ready")
    if admission.get("privacy", {}).get("private_payloads_excluded") is not True:
        errors.append("private payloads are not excluded")
    return errors
