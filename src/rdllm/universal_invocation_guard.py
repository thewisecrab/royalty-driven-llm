"""Universal invocation guards for foundation-model provider calls.

L132 proves that a provider-neutral foundation-model proof chain exists. This
L133 layer proves that a concrete provider invocation was admitted through that
chain before the native model call, so attribution is not attached after the fact.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_INVOCATION_GUARD_VERSION = "rdllm-universal-invocation-guard/v1"
UNIVERSAL_INVOCATION_GUARD_SCHEMA = (
    "docs/schemas/universal_invocation_guard.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L133"
MINIMUM_INPUT_LEVEL = "RDLLM-L132"

REQUIRED_PRECALL_HEADERS = (
    "RDLLM-Attribution-Level",
    "RDLLM-Universal-Foundation-Contract-Hash",
    "RDLLM-Foundation-Runtime-Router-Hash",
    "RDLLM-Foundation-Deployment-Attestation-Hash",
    "RDLLM-Selected-Provider-Family",
    "RDLLM-Selected-Route-ID",
    "RDLLM-Request-Projection-Hash",
    "RDLLM-Response-Binding-Hash",
    "RDLLM-Fail-Closed",
)

REQUIRED_PRECALL_CHECKS = (
    "l132_contract_ready",
    "route_bound_to_contract",
    "deployment_attestation_released",
    "request_projection_bound",
    "response_binding_bound",
    "source_footer_required",
    "fail_closed_policy_bound",
)

DECLARED_HASH_FIELDS = (
    "universal_invocation_guard_hash",
    "universal_foundation_model_contract_hash",
    "foundation_model_deployment_attestation_hash",
    "foundation_runtime_router_hash",
    "foundation_runtime_adapter_hash",
    "universal_composition_settlement_hash",
    "universal_composition_receipt_hash",
    "proof_response_hash",
    "gateway_report_hash",
    "gate_hash",
    "capsule_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "graph_hash",
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
    "raw_router_payload",
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


def load_universal_invocation_guard_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L133 universal invocation guard."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_invocation_guard_hash", "signature"}
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
    guard_input: dict[str, Any],
) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in guard_input.get("private_strings", [])
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


def _artifact_status(artifact: dict[str, Any] | None) -> str:
    return str(_summary(artifact).get("status", ""))


def _artifact_target_level(artifact: dict[str, Any] | None) -> str:
    summary = _summary(artifact)
    return str(
        summary.get("target_certification_level")
        or summary.get("highest_level")
        or ""
    )


def _artifact_binding(name: str, artifact: dict[str, Any] | None) -> dict[str, Any]:
    version = ""
    if artifact:
        for key, value in artifact.items():
            if key.endswith("_version") and isinstance(value, str):
                version = value
                break
    return {
        "name": name,
        "version": version,
        "declared_hash": _declared_hash(artifact),
        "hash_reproducible": _artifact_hash_is_reproducible(artifact),
        "status": _artifact_status(artifact),
        "target_level": _artifact_target_level(artifact),
        "present": bool(artifact),
    }


def _policy(guard_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(guard_input.get("guard_policy", {}))
    return {
        "profile": "rdllm-universal-invocation-guard-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "required_precall_headers": list(
            policy.get("required_precall_headers", REQUIRED_PRECALL_HEADERS)
        ),
        "required_precall_checks": list(
            policy.get("required_precall_checks", REQUIRED_PRECALL_CHECKS)
        ),
        "required_telemetry_attributes": list(
            policy.get(
                "required_telemetry_attributes",
                [
                    "gen_ai.provider.name",
                    "gen_ai.request.model",
                    "gen_ai.response.model",
                    "rdllm.contract_hash",
                    "rdllm.route_id",
                    "rdllm.request_projection_hash",
                ],
            )
        ),
        "on_missing_contract": "block_provider_call",
        "on_header_drift": "block_provider_call",
        "on_route_drift": "block_provider_call",
        "on_boundary_drift": "block_provider_call",
        "on_private_text_leak": "block_publication",
    }


def _artifact_bindings(guard_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = {
        "universal_foundation_model_contract": guard_input.get(
            "universal_foundation_model_contract"
        ),
        "foundation_runtime_router": guard_input.get("foundation_runtime_router"),
        "foundation_runtime_adapter": guard_input.get("foundation_runtime_adapter"),
        "foundation_model_deployment_attestation": guard_input.get(
            "foundation_model_deployment_attestation"
        ),
    }
    return {
        name: _artifact_binding(name, artifact)
        for name, artifact in artifacts.items()
    }


def _expected_header_values(guard_input: dict[str, Any]) -> dict[str, str]:
    contract = guard_input.get("universal_foundation_model_contract", {})
    router = guard_input.get("foundation_runtime_router", {})
    deployment = guard_input.get("foundation_model_deployment_attestation", {})
    selected_route = contract.get("selected_route_binding", {})
    boundary = deployment.get("request_response_binding", {})
    return {
        "RDLLM-Attribution-Level": TARGET_CERTIFICATION_LEVEL,
        "RDLLM-Universal-Foundation-Contract-Hash": _declared_hash(contract),
        "RDLLM-Foundation-Runtime-Router-Hash": _declared_hash(router),
        "RDLLM-Foundation-Deployment-Attestation-Hash": _declared_hash(deployment),
        "RDLLM-Selected-Provider-Family": str(
            selected_route.get("selected_provider_family", "")
        ),
        "RDLLM-Selected-Route-ID": str(selected_route.get("selected_route_id", "")),
        "RDLLM-Request-Projection-Hash": str(
            boundary.get("request_projection_hash", "")
        ),
        "RDLLM-Response-Binding-Hash": str(boundary.get("response_binding_hash", "")),
        "RDLLM-Fail-Closed": "true",
    }


def _invocation_subject(guard_input: dict[str, Any]) -> dict[str, Any]:
    invocation = dict(guard_input.get("invocation", {}))
    contract = guard_input.get("universal_foundation_model_contract", {})
    router = guard_input.get("foundation_runtime_router", {})
    deployment = guard_input.get("foundation_model_deployment_attestation", {})
    adapter = guard_input.get("foundation_runtime_adapter", {})

    contract_route = contract.get("selected_route_binding", {})
    router_route = router.get("selected_route_binding", {})
    deployment_route = deployment.get("selected_route_binding", {})
    boundary = deployment.get("request_response_binding", {})
    observation = adapter.get("native_response_observation", {})

    request_headers = {
        str(key): str(value)
        for key, value in invocation.get("request_headers", {}).items()
    }
    response_artifact_hashes = {
        str(key): str(value)
        for key, value in invocation.get("required_response_artifact_hashes", {}).items()
    }
    precall_checks = [
        str(item) for item in invocation.get("precall_checks_completed", [])
    ]
    telemetry = {
        str(key): str(value)
        for key, value in invocation.get("telemetry_span", {}).items()
    }

    return {
        "invocation_id": str(invocation.get("invocation_id", "")),
        "request_id": str(invocation.get("request_id", "")),
        "route_id": str(invocation.get("route_id", "")),
        "provider_family": str(invocation.get("provider_family", "")),
        "provider_id": str(invocation.get("provider_id", "")),
        "native_model": str(invocation.get("native_model", "")),
        "native_api_version": str(invocation.get("native_api_version", "")),
        "request_projection_hash": str(
            invocation.get(
                "request_projection_hash",
                boundary.get("request_projection_hash", ""),
            )
        ),
        "response_binding_hash": str(
            invocation.get(
                "response_binding_hash",
                boundary.get("response_binding_hash", ""),
            )
        ),
        "contract_selected_route_id": str(contract_route.get("selected_route_id", "")),
        "contract_selected_provider_family": str(
            contract_route.get("selected_provider_family", "")
        ),
        "router_selected_route_id": str(router_route.get("route_id", "")),
        "router_selected_provider_family": str(router_route.get("provider_family", "")),
        "deployment_route_id": str(deployment_route.get("route_id", "")),
        "deployment_provider_family": str(deployment_route.get("provider_family", "")),
        "deployment_native_model": str(deployment_route.get("native_model", "")),
        "runtime_native_output_hash": str(observation.get("native_output_hash", "")),
        "deployment_native_output_hash": str(boundary.get("native_output_hash", "")),
        "source_footer_delivery_hash": str(
            adapter.get("normalized_rdllm_contract", {}).get(
                "source_footer_delivery_hash", ""
            )
        ),
        "response_envelope_hash": str(boundary.get("response_envelope_hash", "")),
        "request_headers": request_headers,
        "expected_request_headers": _expected_header_values(guard_input),
        "required_response_artifact_hashes": response_artifact_hashes,
        "precall_checks_completed": precall_checks,
        "telemetry_span": telemetry,
        "fail_closed": invocation.get("fail_closed") is True,
        "preflight_decision": str(invocation.get("preflight_decision", "")),
    }


def _header_contract(subject: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    expected = {
        key: subject["expected_request_headers"].get(key, "")
        for key in policy["required_precall_headers"]
    }
    observed = subject["request_headers"]
    missing = [key for key in expected if key not in observed]
    mismatched = [
        key for key, value in expected.items() if observed.get(key, "") != value
    ]
    return {
        "profile": "rdllm-universal-invocation-header-contract/v1",
        "required_headers": list(policy["required_precall_headers"]),
        "expected_header_values": expected,
        "observed_header_values": {
            key: observed.get(key, "") for key in policy["required_precall_headers"]
        },
        "missing_headers": missing,
        "mismatched_headers": mismatched,
        "header_contract_hash": hash_payload(
            {
                "expected_header_values": expected,
                "observed_header_values": {
                    key: observed.get(key, "")
                    for key in policy["required_precall_headers"]
                },
                "missing_headers": missing,
                "mismatched_headers": mismatched,
            }
        ),
    }


def _telemetry_binding(subject: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    telemetry = subject["telemetry_span"]
    required = list(policy["required_telemetry_attributes"])
    expected = {
        "gen_ai.provider.name": subject["provider_family"],
        "gen_ai.request.model": subject["native_model"],
        "gen_ai.response.model": subject["deployment_native_model"],
        "rdllm.contract_hash": subject["expected_request_headers"][
            "RDLLM-Universal-Foundation-Contract-Hash"
        ],
        "rdllm.route_id": subject["route_id"],
        "rdllm.request_projection_hash": subject["request_projection_hash"],
    }
    missing = [key for key in required if key not in telemetry]
    mismatched = [
        key
        for key in required
        if key in expected and telemetry.get(key, "") != expected[key]
    ]
    return {
        "profile": "rdllm-universal-invocation-telemetry-binding/v1",
        "required_attributes": required,
        "expected_attributes": expected,
        "observed_attributes": {key: telemetry.get(key, "") for key in required},
        "missing_attributes": missing,
        "mismatched_attributes": mismatched,
        "telemetry_binding_hash": hash_payload(
            {
                "required_attributes": required,
                "expected_attributes": expected,
                "observed_attributes": {
                    key: telemetry.get(key, "") for key in required
                },
                "missing_attributes": missing,
                "mismatched_attributes": mismatched,
            }
        ),
    }


def _boundary_binding(subject: dict[str, Any]) -> dict[str, Any]:
    route_ids = {
        subject["route_id"],
        subject["contract_selected_route_id"],
        subject["router_selected_route_id"],
        subject["deployment_route_id"],
    }
    provider_families = {
        subject["provider_family"],
        subject["contract_selected_provider_family"],
        subject["router_selected_provider_family"],
        subject["deployment_provider_family"],
    }
    return {
        "profile": "rdllm-universal-invocation-boundary-binding/v1",
        "route_ids": sorted(route_ids),
        "provider_families": sorted(provider_families),
        "request_projection_hash": subject["request_projection_hash"],
        "expected_request_projection_hash": subject["expected_request_headers"][
            "RDLLM-Request-Projection-Hash"
        ],
        "response_binding_hash": subject["response_binding_hash"],
        "expected_response_binding_hash": subject["expected_request_headers"][
            "RDLLM-Response-Binding-Hash"
        ],
        "runtime_native_output_hash": subject["runtime_native_output_hash"],
        "deployment_native_output_hash": subject["deployment_native_output_hash"],
        "source_footer_delivery_hash": subject["source_footer_delivery_hash"],
        "response_envelope_hash": subject["response_envelope_hash"],
        "boundary_binding_hash": hash_payload(
            {
                "route_ids": sorted(route_ids),
                "provider_families": sorted(provider_families),
                "request_projection_hash": subject["request_projection_hash"],
                "response_binding_hash": subject["response_binding_hash"],
                "runtime_native_output_hash": subject["runtime_native_output_hash"],
                "deployment_native_output_hash": subject[
                    "deployment_native_output_hash"
                ],
                "source_footer_delivery_hash": subject[
                    "source_footer_delivery_hash"
                ],
                "response_envelope_hash": subject["response_envelope_hash"],
            }
        ),
    }


def make_universal_invocation_guard(
    guard_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a verifiable L133 preflight guard for one provider invocation."""

    created_at = created_at or now_iso()
    policy = _policy(guard_input)
    contract = guard_input.get("universal_foundation_model_contract", {})
    router = guard_input.get("foundation_runtime_router", {})
    adapter = guard_input.get("foundation_runtime_adapter", {})
    deployment = guard_input.get("foundation_model_deployment_attestation", {})
    artifact_bindings = _artifact_bindings(guard_input)
    subject = _invocation_subject(guard_input)
    header_contract = _header_contract(subject, policy)
    telemetry_binding = _telemetry_binding(subject, policy)
    boundary_binding = _boundary_binding(subject)

    required_checks = set(policy["required_precall_checks"])
    completed_checks = set(subject["precall_checks_completed"])
    response_hashes = subject["required_response_artifact_hashes"]

    checks = {
        "required_artifacts_present": all(
            binding["present"] for binding in artifact_bindings.values()
        ),
        "artifact_hashes_reproducible": all(
            binding["hash_reproducible"] for binding in artifact_bindings.values()
        ),
        "l132_contract_ready": _artifact_status(contract) == "ready"
        and _level_at_least(_artifact_target_level(contract), MINIMUM_INPUT_LEVEL)
        and bool(_summary(contract).get("universal_contract_release_authorized")),
        "route_bound_to_contract": len(
            {
                item
                for item in boundary_binding["route_ids"]
                if item
            }
        )
        == 1
        and len(
            {
                item
                for item in boundary_binding["provider_families"]
                if item
            }
        )
        == 1,
        "deployment_attestation_released": _artifact_status(deployment) == "released"
        and _level_at_least(_artifact_target_level(deployment), "RDLLM-L129")
        and bool(_summary(deployment).get("deployment_release_authorized")),
        "runtime_router_released": _artifact_status(router) == "released"
        and bool(_summary(router).get("router_release_authorized")),
        "runtime_adapter_released": _artifact_status(adapter) == "released"
        and bool(_summary(adapter).get("runtime_release_authorized")),
        "request_projection_bound": subject["request_projection_hash"]
        == boundary_binding["expected_request_projection_hash"],
        "response_binding_bound": subject["response_binding_hash"]
        == boundary_binding["expected_response_binding_hash"],
        "native_response_bound_to_deployment": subject["runtime_native_output_hash"]
        == subject["deployment_native_output_hash"],
        "required_headers_present_and_bound": not header_contract["missing_headers"]
        and not header_contract["mismatched_headers"],
        "precall_checks_completed": required_checks.issubset(completed_checks),
        "preflight_allows_only_after_contract_ready": subject["preflight_decision"]
        == "allow_provider_call"
        and subject["fail_closed"] is True,
        "source_footer_requirement_bound": bool(subject["source_footer_delivery_hash"])
        and response_hashes.get("source_footer_delivery_hash")
        == subject["source_footer_delivery_hash"],
        "response_envelope_requirement_bound": bool(subject["response_envelope_hash"])
        and response_hashes.get("response_envelope_hash")
        == subject["response_envelope_hash"],
        "otel_genai_span_bound": not telemetry_binding["missing_attributes"]
        and not telemetry_binding["mismatched_attributes"],
        "private_text_not_disclosed": True,
    }
    checks["private_text_not_disclosed"] = (
        not _contains_private_fields(
            {
                "artifact_bindings": artifact_bindings,
                "invocation_subject": subject,
                "header_contract": header_contract,
                "telemetry_binding": telemetry_binding,
                "boundary_binding": boundary_binding,
            }
        )
    )

    failure_modes_by_check = {
        "required_artifacts_present": "required_artifact_missing",
        "artifact_hashes_reproducible": "artifact_hash_not_reproducible",
        "l132_contract_ready": "l132_contract_not_ready",
        "route_bound_to_contract": "selected_route_contract_mismatch",
        "deployment_attestation_released": "deployment_not_released",
        "runtime_router_released": "runtime_router_not_released",
        "runtime_adapter_released": "runtime_adapter_not_released",
        "request_projection_bound": "request_response_boundary_mismatch",
        "response_binding_bound": "request_response_boundary_mismatch",
        "native_response_bound_to_deployment": "native_response_boundary_mismatch",
        "required_headers_present_and_bound": "invocation_header_contract_failure",
        "precall_checks_completed": "preflight_check_missing",
        "preflight_allows_only_after_contract_ready": "preflight_not_fail_closed",
        "source_footer_requirement_bound": "source_footer_requirement_missing",
        "response_envelope_requirement_bound": "response_envelope_requirement_missing",
        "otel_genai_span_bound": "genai_telemetry_binding_failure",
        "private_text_not_disclosed": "private_text_leak",
    }
    failed_checks = [key for key, passed in checks.items() if not passed]
    failure_modes = sorted({failure_modes_by_check[key] for key in failed_checks})
    guard_ready = not failed_checks

    commitments = {
        "artifact_binding_root": merkle_root(
            [hash_payload(binding) for binding in artifact_bindings.values()]
        ),
        "header_contract_hash": header_contract["header_contract_hash"],
        "telemetry_binding_hash": telemetry_binding["telemetry_binding_hash"],
        "boundary_binding_hash": boundary_binding["boundary_binding_hash"],
        "precall_check_root": merkle_root(sorted(completed_checks)),
        "l132_contract_hash": _declared_hash(contract),
        "deployment_attestation_hash": _declared_hash(deployment),
    }
    guard_binding = {
        "profile": "rdllm-universal-invocation-guard-binding/v1",
        "invocation_id": subject["invocation_id"],
        "request_id": subject["request_id"],
        "l132_contract_hash": commitments["l132_contract_hash"],
        "foundation_runtime_router_hash": _declared_hash(router),
        "foundation_runtime_adapter_hash": _declared_hash(adapter),
        "foundation_model_deployment_attestation_hash": _declared_hash(deployment),
        "header_contract_hash": commitments["header_contract_hash"],
        "telemetry_binding_hash": commitments["telemetry_binding_hash"],
        "boundary_binding_hash": commitments["boundary_binding_hash"],
        "precall_check_root": commitments["precall_check_root"],
    }
    guard_binding["guard_binding_hash"] = hash_payload(guard_binding)

    report = {
        "guard_version": UNIVERSAL_INVOCATION_GUARD_VERSION,
        "issuer": issuer,
        "created_at": created_at,
        "guard_policy": policy,
        "artifact_bindings": artifact_bindings,
        "invocation_subject": subject,
        "preflight_header_contract": header_contract,
        "telemetry_binding": telemetry_binding,
        "request_response_boundary_binding": boundary_binding,
        "universal_invocation_guard_binding": guard_binding,
        "guard_decision": {
            "decision": "allow_provider_call" if guard_ready else "block_provider_call",
            "release_authorized": guard_ready,
            "failed_checks": failed_checks,
            "failure_modes": failure_modes,
            "safe_call_policy": "invoke_only_with_l133_preflight_guard"
            if guard_ready
            else "block_native_provider_invocation",
        },
        "checks": checks,
        "coverage_gaps": {
            "missing_headers": header_contract["missing_headers"],
            "mismatched_headers": header_contract["mismatched_headers"],
            "missing_telemetry_attributes": telemetry_binding["missing_attributes"],
            "mismatched_telemetry_attributes": telemetry_binding[
                "mismatched_attributes"
            ],
            "missing_precall_checks": sorted(required_checks - completed_checks),
            "failed_checks": failed_checks,
        },
        "commitments": commitments,
        "schemas": {
            "universal_invocation_guard": UNIVERSAL_INVOCATION_GUARD_SCHEMA,
            "universal_foundation_model_contract": "docs/schemas/universal_foundation_model_contract.schema.json",
            "foundation_model_deployment_attestation": "docs/schemas/foundation_model_deployment_attestation.schema.json",
            "foundation_runtime_router": "docs/schemas/foundation_runtime_router.schema.json",
        },
        "privacy": {
            "private_text_fields_excluded": True,
            "raw_prompts_outputs_sources_excluded": True,
            "hash_only_request_response_boundary": True,
            "private_strings_absent": True,
        },
        "summary": {
            "status": "ready" if guard_ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "invocation_id": subject["invocation_id"],
            "request_id": subject["request_id"],
            "selected_provider_family": subject["provider_family"],
            "selected_route_id": subject["route_id"],
            "l132_contract_hash": _declared_hash(contract),
            "deployment_attestation_hash": _declared_hash(deployment),
            "request_projection_hash": subject["request_projection_hash"],
            "response_binding_hash": subject["response_binding_hash"],
            "preflight_authorized": guard_ready,
            "native_provider_call_allowed": guard_ready,
            "source_footer_required": checks["source_footer_requirement_bound"],
            "privacy_preserved": True,
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
        },
    }
    report["privacy"]["private_strings_absent"] = _private_strings_absent(
        report, guard_input
    )
    report["checks"]["private_text_not_disclosed"] = (
        report["checks"]["private_text_not_disclosed"]
        and report["privacy"]["private_strings_absent"]
    )
    if not report["checks"]["private_text_not_disclosed"]:
        if "private_text_not_disclosed" not in report["guard_decision"]["failed_checks"]:
            report["guard_decision"]["failed_checks"].append(
                "private_text_not_disclosed"
            )
            report["guard_decision"]["failure_modes"].append("private_text_leak")
        report["guard_decision"]["decision"] = "block_provider_call"
        report["guard_decision"]["release_authorized"] = False
        report["summary"]["status"] = "blocked"
        report["summary"]["preflight_authorized"] = False
        report["summary"]["native_provider_call_allowed"] = False
        report["summary"]["privacy_preserved"] = False
        report["summary"]["failed_check_count"] = len(
            report["guard_decision"]["failed_checks"]
        )
        report["summary"]["failure_mode_count"] = len(
            report["guard_decision"]["failure_modes"]
        )

    report["universal_invocation_guard_hash"] = hash_payload(
        _hashable_report(report)
    )
    report["signature"] = sign_payload(
        report["universal_invocation_guard_hash"], signing_secret
    )
    return report


def validate_universal_invocation_guard_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "guard_version",
        "issuer",
        "created_at",
        "guard_policy",
        "artifact_bindings",
        "invocation_subject",
        "preflight_header_contract",
        "telemetry_binding",
        "request_response_boundary_binding",
        "universal_invocation_guard_binding",
        "guard_decision",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
        "universal_invocation_guard_hash",
        "signature",
    ]
    for key in required:
        if key not in report:
            errors.append(f"missing universal invocation guard field: {key}")
    if report.get("guard_version") != UNIVERSAL_INVOCATION_GUARD_VERSION:
        errors.append("universal invocation guard version is unsupported")
    if (
        report.get("schemas", {}).get("universal_invocation_guard")
        != UNIVERSAL_INVOCATION_GUARD_SCHEMA
    ):
        errors.append("universal invocation guard schema is not declared")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal invocation guard target level is not RDLLM-L133")
    if _contains_private_fields(report):
        errors.append("universal invocation guard exposes private field names")
    return errors


def verify_universal_invocation_guard(
    report: dict[str, Any],
    *,
    guard_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L133 universal invocation guard by replaying inputs."""

    errors = validate_universal_invocation_guard_shape(report)
    declared_hash = report.get("universal_invocation_guard_hash")
    if declared_hash != hash_payload(_hashable_report(report)):
        errors.append("universal invocation guard hash is not reproducible")
    expected = make_universal_invocation_guard(
        guard_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at"),
        signing_secret=signing_secret,
    )
    if expected.get("universal_invocation_guard_hash") != report.get(
        "universal_invocation_guard_hash"
    ):
        errors.append("universal invocation guard hash does not match inputs")
    if expected.get("guard_decision") != report.get("guard_decision"):
        errors.append("universal invocation guard decision does not match inputs")
    if expected.get("invocation_subject") != report.get("invocation_subject"):
        errors.append("universal invocation guard subject does not match inputs")
    if expected.get("signature") != report.get("signature"):
        errors.append("universal invocation guard signature is invalid")
    if not _private_strings_absent(report, guard_input):
        errors.append("universal invocation guard leaks private replay strings")
    return errors
