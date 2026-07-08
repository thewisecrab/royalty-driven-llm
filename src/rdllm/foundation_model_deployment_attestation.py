"""Model-deployment attestations for selected foundation-model routes.

L128 proves that a multi-provider router can only release an RDLLM-normalized
provider response. This L129 layer proves that the selected route is bound to a
provider-signed model deployment identity, opaque model commitments, and the
request/response boundary for the concrete native response.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload

FOUNDATION_MODEL_DEPLOYMENT_ATTESTATION_VERSION = (
    "rdllm-foundation-model-deployment-attestation/v1"
)
FOUNDATION_MODEL_DEPLOYMENT_STATEMENT_VERSION = (
    "rdllm-foundation-model-deployment-statement/v1"
)
FOUNDATION_MODEL_DEPLOYMENT_ATTESTATION_SCHEMA = (
    "docs/schemas/foundation_model_deployment_attestation.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L129"
MINIMUM_INPUT_LEVEL = "RDLLM-L128"

REQUIRED_MODEL_COMMITMENTS = (
    "model_manifest_hash",
    "weights_commitment_hash",
    "tokenizer_hash",
    "inference_stack_hash",
    "safety_policy_hash",
    "attribution_policy_hash",
)

ACCEPTED_ATTESTATION_TYPES = (
    "provider_signed_deployment",
    "api_boundary_attestation",
    "tee_remote_attestation",
    "third_party_deployment_audit",
    "aex_api_boundary",
)

DECLARED_HASH_FIELDS = (
    "foundation_model_deployment_attestation_hash",
    "foundation_runtime_router_hash",
    "foundation_runtime_adapter_hash",
    "foundation_provider_conformance_hash",
    "composite_foundation_adapter_hash",
    "foundation_profile_hash",
    "statement_hash",
    "attested_runtime_hash",
    "report_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "bundle_hash",
    "summary_hash",
    "receipt_hash",
    "trace_hash",
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
    "raw_weights",
    "weights",
    "model_weights",
    "raw_tokenizer",
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
    "verification_secret",
    "deployment_secret",
    "signing_secret",
    "private_key",
}


def load_foundation_model_deployment_attestation_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay inputs for an L129 model-deployment attestation."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"foundation_model_deployment_attestation_hash", "signature"}
    }


def _hashable_statement(statement: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in statement.items()
        if key not in {"statement_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any] | None) -> dict[str, Any]:
    return {
        key: value
        for key, value in (artifact or {}).items()
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
    attestation_input: dict[str, Any],
) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in attestation_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def make_deployment_key_hash(
    provider_id: str,
    deployment_key_id: str,
    deployment_secret: str,
) -> str:
    """Return the reference deployment-key commitment for HMAC verification."""

    return hash_payload(
        "rdllm-foundation-model-deployment-key:"
        f"{provider_id}:{deployment_key_id}:{deployment_secret}"
    )


def make_model_deployment_statement(
    *,
    provider_id: str,
    provider_family: str,
    deployment_id: str,
    native_model: str,
    model_version: str,
    model_manifest_hash: str,
    weights_commitment_hash: str,
    tokenizer_hash: str,
    inference_stack_hash: str,
    safety_policy_hash: str,
    attribution_policy_hash: str,
    selected_route_id: str,
    route_decision_hash: str,
    foundation_runtime_router_hash: str,
    foundation_runtime_adapter_hash: str,
    request_projection_hash: str,
    response_binding_hash: str,
    api_boundary_attestation_hash: str,
    deployment_key_id: str,
    deployment_secret: str,
    attestation_type: str = "provider_signed_deployment",
    created_at: str | None = None,
    valid_from: str | None = None,
    valid_until: str | None = None,
) -> dict[str, Any]:
    """Create a provider-signed deployment statement for a selected route."""

    timestamp = created_at or now_iso()
    statement: dict[str, Any] = {
        "statement_version": FOUNDATION_MODEL_DEPLOYMENT_STATEMENT_VERSION,
        "provider_id": provider_id,
        "provider_family": provider_family,
        "deployment_id": deployment_id,
        "native_model": native_model,
        "model_version": model_version,
        "attestation_type": attestation_type,
        "model_manifest_hash": model_manifest_hash,
        "weights_commitment_hash": weights_commitment_hash,
        "tokenizer_hash": tokenizer_hash,
        "inference_stack_hash": inference_stack_hash,
        "safety_policy_hash": safety_policy_hash,
        "attribution_policy_hash": attribution_policy_hash,
        "selected_route_id": selected_route_id,
        "route_decision_hash": route_decision_hash,
        "foundation_runtime_router_hash": foundation_runtime_router_hash,
        "foundation_runtime_adapter_hash": foundation_runtime_adapter_hash,
        "request_projection_hash": request_projection_hash,
        "response_binding_hash": response_binding_hash,
        "api_boundary_attestation_hash": api_boundary_attestation_hash,
        "deployment_key_id": deployment_key_id,
        "created_at": timestamp,
        "valid_from": valid_from or timestamp,
        "valid_until": valid_until or "9999-12-31T23:59:59Z",
    }
    statement["statement_hash"] = hash_payload(_hashable_statement(statement))
    statement["signature"] = {
        "algorithm": "HMAC-SHA256",
        "key_id": deployment_key_id,
        "value": sign_payload(_hashable_statement(statement), deployment_secret),
    }
    return statement


def _policy(attestation_input: dict[str, Any]) -> dict[str, Any]:
    policy = attestation_input.get("deployment_policy", {})
    return {
        "profile": "rdllm-foundation-model-deployment-attestation-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "accepted_attestation_types": list(
            policy.get("accepted_attestation_types", ACCEPTED_ATTESTATION_TYPES)
        ),
        "required_model_commitments": list(
            policy.get("required_model_commitments", REQUIRED_MODEL_COMMITMENTS)
        ),
        "on_unattested_deployment": "block_display",
        "on_model_identity_mismatch": "block_display",
        "on_request_response_boundary_mismatch": "block_display",
        "raw_model_weights_disclosure_allowed": False,
        "raw_request_or_response_disclosure_allowed": False,
    }


def _public_key_rows(attestation_input: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in attestation_input.get("trusted_deployment_keys", []):
        public = {
            "provider_id": str(row.get("provider_id", "")),
            "provider_family": str(row.get("provider_family", "")),
            "deployment_key_id": str(row.get("deployment_key_id", "")),
            "deployment_key_hash": str(row.get("deployment_key_hash", "")),
            "status": str(row.get("status", "")),
            "valid_from": str(row.get("valid_from", "")),
            "valid_until": str(row.get("valid_until", "")),
        }
        public["trusted_deployment_key_row_hash"] = hash_payload(public)
        rows.append(public)
    return rows


def _matching_key(
    attestation_input: dict[str, Any],
    statement: dict[str, Any],
) -> dict[str, Any]:
    for row in attestation_input.get("trusted_deployment_keys", []):
        if (
            str(row.get("provider_id", "")) == str(statement.get("provider_id", ""))
            and str(row.get("provider_family", ""))
            == str(statement.get("provider_family", ""))
            and str(row.get("deployment_key_id", ""))
            == str(statement.get("deployment_key_id", ""))
        ):
            return row
    return {}


def _key_hash_matches(row: dict[str, Any]) -> bool:
    secret = str(row.get("verification_secret", ""))
    return bool(secret) and row.get("deployment_key_hash") == make_deployment_key_hash(
        str(row.get("provider_id", "")),
        str(row.get("deployment_key_id", "")),
        secret,
    )


def _signature_valid(statement: dict[str, Any], key_row: dict[str, Any]) -> bool:
    secret = str(key_row.get("verification_secret", ""))
    signature = statement.get("signature", {})
    return (
        bool(secret)
        and signature.get("algorithm") == "HMAC-SHA256"
        and signature.get("key_id") == statement.get("deployment_key_id")
        and signature.get("value") == sign_payload(_hashable_statement(statement), secret)
    )


def _selected_route(router: dict[str, Any]) -> dict[str, Any]:
    return router.get("selected_route_binding", {})


def _native_response(runtime_adapter: dict[str, Any]) -> dict[str, Any]:
    return runtime_adapter.get("native_response_observation", {})


def _request_response_binding(attestation_input: dict[str, Any]) -> dict[str, Any]:
    binding = attestation_input.get("request_response_binding", {})
    return {
        "native_response_id": str(binding.get("native_response_id", "")),
        "native_output_hash": str(binding.get("native_output_hash", "")),
        "response_envelope_hash": str(binding.get("response_envelope_hash", "")),
        "request_projection_hash": str(binding.get("request_projection_hash", "")),
        "response_binding_hash": str(binding.get("response_binding_hash", "")),
        "api_boundary_attestation_hash": str(
            binding.get("api_boundary_attestation_hash", "")
        ),
    }


def _created_within_statement_window(
    created_at: str,
    statement: dict[str, Any],
) -> bool:
    valid_from = str(statement.get("valid_from", ""))
    valid_until = str(statement.get("valid_until", ""))
    return bool(valid_from and valid_until and valid_from <= created_at <= valid_until)


def _artifact_bindings(attestation_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = {
        "foundation_runtime_router": attestation_input.get("foundation_runtime_router"),
        "foundation_runtime_adapter": attestation_input.get(
            "foundation_runtime_adapter"
        ),
        "attested_runtime": attestation_input.get("attested_runtime"),
    }
    bindings: dict[str, dict[str, Any]] = {}
    for name, artifact in artifacts.items():
        artifact_type = (
            (artifact or {}).get("deployment_attestation_version")
            or (artifact or {}).get("runtime_router_version")
            or (artifact or {}).get("runtime_adapter_version")
            or (artifact or {}).get("report_version")
            or (artifact or {}).get("version")
            or ""
        )
        bindings[name] = {
            "present": bool(artifact),
            "declared_hash": _declared_hash(artifact),
            "hash_reproducible": _artifact_hash_is_reproducible(artifact),
            "artifact_type": str(artifact_type),
        }
    return bindings


def _checks(
    *,
    attestation_input: dict[str, Any],
    policy: dict[str, Any],
    artifact_bindings: dict[str, dict[str, Any]],
    key_row: dict[str, Any],
    statement: dict[str, Any],
    request_response_binding: dict[str, Any],
    created_at: str,
) -> dict[str, bool]:
    router = attestation_input.get("foundation_runtime_router", {})
    runtime_adapter = attestation_input.get("foundation_runtime_adapter", {})
    selected_route = _selected_route(router)
    native_response = _native_response(runtime_adapter)
    router_hash = _declared_hash(router)
    adapter_hash = _declared_hash(runtime_adapter)
    required_commitments = policy["required_model_commitments"]
    statement_hashable = _hashable_statement(statement)
    statement_hash = hash_payload(statement_hashable) if statement else ""
    response_binding = {
        "native_response_id": request_response_binding["native_response_id"],
        "native_output_hash": request_response_binding["native_output_hash"],
        "response_envelope_hash": request_response_binding["response_envelope_hash"],
    }
    expected_response_binding_hash = hash_payload(response_binding)
    return {
        "artifact_hashes_reproducible": all(
            binding["hash_reproducible"]
            for binding in artifact_bindings.values()
            if binding["present"]
        )
        and artifact_bindings["foundation_runtime_router"]["present"]
        and artifact_bindings["foundation_runtime_adapter"]["present"],
        "foundation_runtime_router_released_l128": (
            router.get("summary", {}).get("status") == "released"
            and router.get("summary", {}).get("target_certification_level")
            == MINIMUM_INPUT_LEVEL
            and router.get("router_decision", {}).get("release_authorized") is True
        ),
        "selected_route_binds_runtime_adapter": (
            bool(selected_route)
            and selected_route.get("foundation_runtime_adapter_hash") == adapter_hash
            and selected_route.get("provider_id") == native_response.get("provider_id")
            and selected_route.get("provider_family")
            == native_response.get("provider_family")
            and selected_route.get("native_model") == native_response.get("native_model")
        ),
        "trusted_deployment_key_active": (
            bool(key_row)
            and key_row.get("status") == "active"
            and _key_hash_matches(key_row)
        ),
        "deployment_statement_version_supported": (
            statement.get("statement_version")
            == FOUNDATION_MODEL_DEPLOYMENT_STATEMENT_VERSION
        ),
        "deployment_statement_hash_reproducible": (
            bool(statement)
            and statement.get("statement_hash") == statement_hash
        ),
        "deployment_statement_signature_valid": _signature_valid(statement, key_row),
        "deployment_statement_attestation_type_allowed": statement.get(
            "attestation_type"
        )
        in policy["accepted_attestation_types"],
        "deployment_statement_model_commitments_present": all(
            bool(statement.get(field)) for field in required_commitments
        ),
        "deployment_statement_valid_for_report_time": _created_within_statement_window(
            created_at,
            statement,
        ),
        "deployment_statement_matches_selected_route": (
            bool(selected_route)
            and statement.get("provider_id") == selected_route.get("provider_id")
            and statement.get("provider_family")
            == selected_route.get("provider_family")
            and statement.get("native_model") == selected_route.get("native_model")
            and statement.get("selected_route_id") == selected_route.get("route_id")
            and statement.get("route_decision_hash")
            == selected_route.get("route_decision_hash")
            and statement.get("foundation_runtime_router_hash") == router_hash
            and statement.get("foundation_runtime_adapter_hash") == adapter_hash
        ),
        "request_response_binding_complete": all(
            request_response_binding.get(field)
            for field in (
                "native_response_id",
                "native_output_hash",
                "response_envelope_hash",
                "request_projection_hash",
                "response_binding_hash",
                "api_boundary_attestation_hash",
            )
        ),
        "request_response_binding_matches_runtime_adapter": (
            request_response_binding.get("native_response_id")
            == native_response.get("native_response_id")
            and request_response_binding.get("native_output_hash")
            == native_response.get("native_output_hash")
            and request_response_binding.get("response_envelope_hash")
            == runtime_adapter.get("normalized_rdllm_contract", {}).get(
                "response_envelope_hash", ""
            )
            and request_response_binding.get("response_binding_hash")
            == expected_response_binding_hash
        ),
        "deployment_statement_binds_request_response_boundary": (
            statement.get("request_projection_hash")
            == request_response_binding.get("request_projection_hash")
            and statement.get("response_binding_hash")
            == request_response_binding.get("response_binding_hash")
            and statement.get("api_boundary_attestation_hash")
            == request_response_binding.get("api_boundary_attestation_hash")
        ),
        "api_boundary_attestation_present": bool(
            request_response_binding.get("api_boundary_attestation_hash")
        ),
        "private_text_not_disclosed": (
            not _contains_private_fields(
                {
                    "trusted_deployment_key_rows": _public_key_rows(
                        attestation_input
                    ),
                    "model_deployment_statement": statement,
                    "request_response_binding": request_response_binding,
                }
            )
            and _private_strings_absent(
                {
                    "model_deployment_statement": statement,
                    "request_response_binding": request_response_binding,
                },
                attestation_input,
            )
        ),
    }


def _failure_modes(checks: dict[str, bool]) -> list[str]:
    mapping = {
        "artifact_hashes_reproducible": "artifact_hash_drift",
        "foundation_runtime_router_released_l128": "runtime_router_failure",
        "selected_route_binds_runtime_adapter": "selected_route_model_mismatch",
        "trusted_deployment_key_active": "untrusted_deployment_key",
        "deployment_statement_version_supported": "unsupported_deployment_statement",
        "deployment_statement_hash_reproducible": "deployment_statement_hash_drift",
        "deployment_statement_signature_valid": "deployment_statement_signature_invalid",
        "deployment_statement_attestation_type_allowed": "unsupported_deployment_attestation_type",
        "deployment_statement_model_commitments_present": "missing_model_commitment",
        "deployment_statement_valid_for_report_time": "deployment_statement_not_fresh",
        "deployment_statement_matches_selected_route": "deployment_route_mismatch",
        "request_response_binding_complete": "request_response_boundary_incomplete",
        "request_response_binding_matches_runtime_adapter": "request_response_boundary_mismatch",
        "deployment_statement_binds_request_response_boundary": "deployment_boundary_mismatch",
        "api_boundary_attestation_present": "missing_api_boundary_attestation",
        "private_text_not_disclosed": "private_text_leak",
    }
    return sorted(
        {mode for check, mode in mapping.items() if checks.get(check) is not True}
    )


def make_foundation_model_deployment_attestation_report(
    attestation_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L129 attestation for the selected foundation-model deployment."""

    timestamp = created_at or now_iso()
    policy = _policy(attestation_input)
    artifact_bindings = _artifact_bindings(attestation_input)
    statement = dict(attestation_input.get("model_deployment_statement", {}))
    request_response_binding = _request_response_binding(attestation_input)
    key_row = _matching_key(attestation_input, statement)
    checks = _checks(
        attestation_input=attestation_input,
        policy=policy,
        artifact_bindings=artifact_bindings,
        key_row=key_row,
        statement=statement,
        request_response_binding=request_response_binding,
        created_at=timestamp,
    )
    failed = [key for key, value in checks.items() if value is not True]
    blocked = bool(failed)
    failure_modes = _failure_modes(checks)
    public_key_rows = _public_key_rows(attestation_input)
    router = attestation_input.get("foundation_runtime_router", {})
    runtime_adapter = attestation_input.get("foundation_runtime_adapter", {})
    selected_route = _selected_route(router)
    report: dict[str, Any] = {
        "deployment_attestation_version": FOUNDATION_MODEL_DEPLOYMENT_ATTESTATION_VERSION,
        "issuer": issuer,
        "created_at": timestamp,
        "deployment_policy": policy,
        "artifact_bindings": artifact_bindings,
        "trusted_deployment_key_rows": public_key_rows,
        "selected_route_binding": {
            "route_id": selected_route.get("route_id", ""),
            "provider_id": selected_route.get("provider_id", ""),
            "provider_family": selected_route.get("provider_family", ""),
            "native_model": selected_route.get("native_model", ""),
            "route_decision_hash": selected_route.get("route_decision_hash", ""),
            "foundation_runtime_router_hash": _declared_hash(router),
            "foundation_runtime_adapter_hash": _declared_hash(runtime_adapter),
        },
        "model_deployment_statement": statement,
        "request_response_binding": request_response_binding,
        "deployment_decision": {
            "decision": "block_display" if blocked else "release",
            "release_authorized": not blocked,
            "failed_checks": failed,
            "failure_modes": failure_modes,
            "safe_output_policy": (
                "suppress_unattested_model_output"
                if blocked
                else "emit_attested_foundation_model_output"
            ),
        },
        "checks": checks,
        "coverage_gaps": {
            "failed_checks": failed,
            "failure_modes": failure_modes,
            "missing_model_commitments": [
                field
                for field in policy["required_model_commitments"]
                if not statement.get(field)
            ],
            "matched_deployment_key_id": str(key_row.get("deployment_key_id", "")),
        },
        "commitments": {
            "foundation_runtime_router_hash": _declared_hash(router),
            "foundation_runtime_adapter_hash": _declared_hash(runtime_adapter),
            "trusted_deployment_key_root": hash_payload(public_key_rows),
            "model_deployment_statement_hash": str(
                statement.get("statement_hash", "")
            ),
            "request_response_binding_hash": hash_payload(request_response_binding),
            "schema": FOUNDATION_MODEL_DEPLOYMENT_ATTESTATION_SCHEMA,
        },
        "schemas": {
            "foundation_model_deployment_attestation": FOUNDATION_MODEL_DEPLOYMENT_ATTESTATION_SCHEMA,
            "foundation_runtime_router": "docs/schemas/foundation_runtime_router.schema.json",
            "foundation_runtime_adapter": "docs/schemas/foundation_runtime_adapter.schema.json",
            "attested_runtime": "docs/schemas/attested_runtime.schema.json",
        },
        "privacy": {
            "raw_model_weights_disclosed": False,
            "raw_request_disclosed": False,
            "raw_response_disclosed": False,
            "raw_router_payload_disclosed": False,
            "deployment_key_secret_disclosed": False,
            "hash_only_model_commitments": True,
        },
        "summary": {
            "status": "blocked" if blocked else "released",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "provider_id": selected_route.get("provider_id", ""),
            "provider_family": selected_route.get("provider_family", ""),
            "native_model": selected_route.get("native_model", ""),
            "deployment_id": statement.get("deployment_id", ""),
            "attestation_type": statement.get("attestation_type", ""),
            "failed_check_count": len(failed),
            "failure_mode_count": len(failure_modes),
            "deployment_release_authorized": not blocked,
            "model_identity_bound": checks["deployment_statement_matches_selected_route"],
            "request_response_boundary_bound": checks[
                "deployment_statement_binds_request_response_boundary"
            ],
            "api_boundary_attested": checks["api_boundary_attestation_present"],
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    report["foundation_model_deployment_attestation_hash"] = hash_payload(
        _hashable_report(report)
    )
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


def validate_foundation_model_deployment_attestation_shape(
    report: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = (
        "deployment_attestation_version",
        "issuer",
        "created_at",
        "deployment_policy",
        "artifact_bindings",
        "trusted_deployment_key_rows",
        "selected_route_binding",
        "model_deployment_statement",
        "request_response_binding",
        "deployment_decision",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
        "foundation_model_deployment_attestation_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing foundation model deployment attestation field: {key}")
    if errors:
        return errors
    if (
        report.get("deployment_attestation_version")
        != FOUNDATION_MODEL_DEPLOYMENT_ATTESTATION_VERSION
    ):
        errors.append("foundation model deployment attestation version is unsupported")
    if (
        report.get("schemas", {}).get("foundation_model_deployment_attestation")
        != FOUNDATION_MODEL_DEPLOYMENT_ATTESTATION_SCHEMA
    ):
        errors.append("foundation model deployment attestation schema is not declared")
    if not isinstance(report.get("trusted_deployment_key_rows"), list):
        errors.append("foundation model deployment trusted key rows are not a list")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append(
            "foundation model deployment attestation target level is not RDLLM-L129"
        )
    return errors


def verify_foundation_model_deployment_attestation_report(
    report: dict[str, Any],
    *,
    attestation_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L129 deployment attestation against replay inputs."""

    errors = validate_foundation_model_deployment_attestation_shape(report)
    if errors:
        return errors

    if hash_payload(_hashable_report(report)) != report.get(
        "foundation_model_deployment_attestation_hash"
    ):
        errors.append("foundation model deployment attestation hash is not reproducible")

    expected = make_foundation_model_deployment_attestation_report(
        attestation_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "deployment_policy",
        "artifact_bindings",
        "trusted_deployment_key_rows",
        "selected_route_binding",
        "model_deployment_statement",
        "request_response_binding",
        "deployment_decision",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(
                f"foundation model deployment attestation {key} does not match inputs"
            )
    if expected.get("foundation_model_deployment_attestation_hash") != report.get(
        "foundation_model_deployment_attestation_hash"
    ):
        errors.append("foundation model deployment attestation hash does not match inputs")

    decision = report.get("deployment_decision", {})
    if report.get("summary", {}).get("status") == "blocked":
        if decision.get("decision") != "block_display" or decision.get(
            "release_authorized"
        ):
            errors.append(
                "foundation model deployment blocked report is not fail-closed"
            )
    elif report.get("summary", {}).get("status") == "released":
        if decision.get("decision") != "release" or not decision.get(
            "release_authorized"
        ):
            errors.append(
                "foundation model deployment released report is not releasable"
            )
    else:
        errors.append("foundation model deployment attestation status is unsupported")

    if _contains_private_fields(report):
        errors.append("foundation model deployment attestation exposes private field names")
    if not _private_strings_absent(report, attestation_input):
        errors.append("foundation model deployment attestation exposes private replay text")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("foundation model deployment attestation is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("foundation model deployment attestation signature is invalid")

    return errors
