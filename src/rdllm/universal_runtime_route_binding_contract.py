"""Universal runtime route binding contracts.

The L179 layer binds live model calls back to catalog-covered RDLLM routes.
L170 proves production invocation admission at provider-family level. L178 proves
catalog entries are exhaustively normalized and admitted or blocked. L179 proves
the actual runtime request and response metadata, including aliases, fallbacks,
streams, tool callbacks, cache reuse, telemetry spans, source footers, and
settlement meters, remain bound to an L178-covered route before response release
or creator settlement.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_RUNTIME_ROUTE_BINDING_CONTRACT_VERSION = (
    "rdllm-universal-runtime-route-binding-contract/v1"
)
UNIVERSAL_RUNTIME_ROUTE_BINDING_CONTRACT_SCHEMA = (
    "docs/schemas/universal_runtime_route_binding_contract.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L179"
MINIMUM_PRODUCTION_INVOCATION_LEVEL = "RDLLM-L170"
MINIMUM_PROVIDER_CATALOG_COVERAGE_LEVEL = "RDLLM-L178"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-runtime-route-binding-contract.json"
)

REQUIRED_RUNTIME_BINDING_STAGES = (
    "preflight_route_resolution",
    "catalog_coverage_lookup",
    "admission_token_binding",
    "request_model_id_lock",
    "provider_response_model_echo",
    "alias_fallback_detection",
    "streaming_final_model_echo",
    "tool_batch_callback_route_echo",
    "telemetry_span_route_binding",
    "source_footer_route_binding",
    "settlement_meter_route_binding",
    "post_response_replay",
)

REQUIRED_RUNTIME_MODEL_FIELDS = (
    "requested_model_id",
    "resolved_model_id",
    "provider_namespace",
    "route_id",
    "catalog_entry_hash",
    "model_identity_hash",
    "endpoint_protocol",
    "api_version",
    "region",
    "tenant_scope",
    "response_model_id",
    "finish_surface",
    "source_footer_hash",
    "settlement_meter_hash",
)

REQUIRED_RUNTIME_SURFACES = (
    "sync_generation",
    "streaming_generation",
    "tool_call",
    "mcp_tool_call",
    "retrieval_grounding",
    "batch_job",
    "webhook_callback",
    "fallback_model",
    "cache_reuse",
    "copy_export",
    "client_sdk",
    "gateway_proxy",
    "local_runtime",
    "auditor_export",
)

REQUIRED_NEGATIVE_RUNTIME_FAILURES = (
    "runtime_model_not_in_l178_catalog",
    "admission_token_missing",
    "response_model_mismatch",
    "alias_resolves_to_unregistered_route",
    "router_fallback_after_preflight",
    "streaming_final_model_missing",
    "tool_callback_route_missing",
    "cache_reuse_stale_route",
    "batch_callback_wrong_model",
    "region_route_mismatch",
    "tenant_scope_mismatch",
    "provider_sdk_strips_model_id",
    "telemetry_span_unbound_to_route",
    "source_footer_route_mismatch",
    "settlement_meter_route_mismatch",
    "catalog_coverage_revoked_midflight",
    "response_release_without_route_binding",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_runtime_route_binding_contract_hash",
    "universal_production_invocation_admission_hash",
    "universal_provider_catalog_coverage_contract_hash",
    "runtime_binding_hash",
    "catalog_coverage_hash",
    "production_admission_hash",
    "admission_token_hash",
    "request_model_lock_hash",
    "response_model_echo_hash",
    "telemetry_span_hash",
    "source_footer_route_hash",
    "settlement_meter_route_hash",
    "surface_hash",
    "field_hash",
    "stage_hash",
    "verifier_hash",
    "fixture_hash",
    "attestation_hash",
    "receipt_hash",
    "report_hash",
    "manifest_hash",
    "profile_hash",
    "bundle_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "query_text",
    "answer_text",
    "output_text",
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
    "tool_payload",
    "raw_tool_output",
    "customer_id",
    "customer_email",
    "tenant_id",
    "billing_record",
    "api_key",
    "access_token",
    "refresh_token",
    "oauth_token",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_runtime_route_binding_contract_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L179 runtime route binding contract."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in contract.items()
        if key not in {"universal_runtime_route_binding_contract_hash", "signature"}
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


def _production_admission_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("admission_decision", {}) if artifact else {}
    summary = _summary(artifact)
    return (
        summary.get("status") == "ready"
        and summary.get("target_certification_level")
        == MINIMUM_PRODUCTION_INVOCATION_LEVEL
        and decision.get("production_invocation_admission_ready") is True
        and decision.get("live_provider_invocation_allowed") is True
        and decision.get("response_release_allowed") is True
    )


def _catalog_coverage_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("catalog_coverage_decision", {}) if artifact else {}
    summary = _summary(artifact)
    return (
        summary.get("status") == "ready"
        and summary.get("target_certification_level")
        == MINIMUM_PROVIDER_CATALOG_COVERAGE_LEVEL
        and decision.get("universal_provider_catalog_coverage_ready") is True
        and decision.get("catalog_exhaustiveness_attested") is True
        and decision.get("unknown_catalog_models_blocked") is True
    )


def _string(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _bool(value: Any) -> bool:
    return value is True


def _row_map(payload: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    rows = payload.get(key, {})
    if not isinstance(rows, dict):
        return {}
    return {
        str(name): row
        for name, row in rows.items()
        if isinstance(row, dict)
    }


def _complete_rows(
    rows: dict[str, dict[str, Any]],
    required: tuple[str, ...],
    predicate,
) -> tuple[list[str], list[str]]:
    missing = [name for name in required if name not in rows]
    incomplete = [name for name in required if name in rows and not predicate(rows[name])]
    return missing, incomplete


def _stage_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("stage_hash")),
            _string(row.get("policy_hash")),
            _string(row.get("verifier_hash")),
            _bool(row.get("enabled")),
            _bool(row.get("telemetry_bound")),
            _bool(row.get("fail_closed")),
            _bool(row.get("auditable")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _field_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("field_hash")),
            _string(row.get("schema_hash")),
            _string(row.get("verifier_hash")),
            _bool(row.get("field_required")),
            _bool(row.get("request_bound")),
            _bool(row.get("response_bound")),
            _bool(row.get("telemetry_bound")),
            _bool(row.get("privacy_safe")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _surface_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("surface_hash")),
            _string(row.get("route_binding_policy_hash")),
            _string(row.get("verifier_hash")),
            _bool(row.get("request_model_echo_required")),
            _bool(row.get("response_model_echo_required")),
            _bool(row.get("telemetry_required")),
            _bool(row.get("source_footer_route_required")),
            _bool(row.get("settlement_meter_required")),
            _bool(row.get("fail_closed")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _route_binding_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "route_id",
        "runtime_binding_hash",
        "catalog_coverage_hash",
        "production_admission_hash",
        "admission_token_hash",
        "request_model_lock_hash",
        "response_model_echo_hash",
        "telemetry_span_hash",
        "source_footer_route_hash",
        "settlement_meter_route_hash",
        "verifier_hash",
    )
    required_bools = (
        "l178_catalog_covered",
        "l170_admission_bound",
        "requested_model_locked",
        "response_model_echo_matched",
        "alias_resolution_checked",
        "fallback_blocked_or_bound",
        "streaming_final_bound",
        "tool_batch_callbacks_bound",
        "telemetry_route_bound",
        "source_footer_route_bound",
        "settlement_meter_route_bound",
        "response_release_gate_enabled",
        "no_private_payloads",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _negative_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("fixture_hash")),
            _string(row.get("verifier_hash")),
            _bool(row.get("expected_reject")),
            _bool(row.get("observed_reject")),
            _bool(row.get("runtime_route_blocked")),
            _bool(row.get("response_release_blocked")),
            _bool(row.get("source_footer_reliance_blocked")),
            _bool(row.get("settlement_held")),
            _bool(row.get("public_status_marked_failed")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _catalog_route_ids(catalog_coverage: dict[str, Any] | None) -> list[str]:
    if not isinstance(catalog_coverage, dict):
        return []
    rows = catalog_coverage.get("registry_route_coverage_rows", {})
    if not isinstance(rows, dict):
        return []
    route_ids: list[str] = []
    for key, row in rows.items():
        if isinstance(row, dict):
            route_ids.append(_string(row.get("route_id")) or str(key))
        else:
            route_ids.append(str(key))
    return sorted(route_id for route_id in route_ids if route_id)


def _admitted_catalog_route_ids(catalog_coverage: dict[str, Any] | None) -> set[str]:
    if not isinstance(catalog_coverage, dict):
        return set()
    rows = catalog_coverage.get("discovered_model_rows", [])
    if not isinstance(rows, list):
        return set()
    route_ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("coverage_decision") == "admitted_registered_route":
            route_id = _string(row.get("normalized_route_id"))
            if route_id:
                route_ids.add(route_id)
    return route_ids


def _route_bindings_complete(
    rows: dict[str, dict[str, Any]],
    required_route_ids: list[str],
    admitted_route_ids: set[str],
) -> tuple[list[str], list[str], list[str], list[str]]:
    missing = [route_id for route_id in required_route_ids if route_id not in rows]
    incomplete: list[str] = []
    mismatched: list[str] = []
    missing_admitted: list[str] = []
    for route_id in required_route_ids:
        if route_id not in rows:
            continue
        row = rows[route_id]
        if not _route_binding_row_ready(row):
            incomplete.append(route_id)
        if row.get("route_id") != route_id:
            mismatched.append(route_id)
    for route_id in sorted(admitted_route_ids):
        if route_id not in rows:
            missing_admitted.append(route_id)
    return missing, incomplete, mismatched, missing_admitted


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            key_str = str(key)
            next_path = f"{path}.{key_str}" if path else key_str
            if key_str in PRIVATE_FIELD_NAMES:
                found.append(next_path)
            found.extend(_contains_private_fields(nested, next_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(_contains_private_fields(nested, f"{path}[{index}]"))
    return found


def _private_strings_absent(public: Any, private_input: dict[str, Any]) -> bool:
    private_strings = private_input.get("private_strings", [])
    if not isinstance(private_strings, list):
        return True
    rendered = canonical_json(public)
    return all(
        not isinstance(value, str) or not value or value not in rendered
        for value in private_strings
    )


def make_universal_runtime_route_binding_contract(
    contract_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L179 runtime route binding contract."""

    production_admission = contract_input.get("universal_production_invocation_admission")
    catalog_coverage = contract_input.get("universal_provider_catalog_coverage_contract")
    stage_rows = _row_map(contract_input, "runtime_binding_stage_rows")
    field_rows = _row_map(contract_input, "runtime_model_field_rows")
    surface_rows = _row_map(contract_input, "runtime_surface_rows")
    route_binding_rows = _row_map(contract_input, "runtime_route_binding_rows")
    negative_rows = _row_map(contract_input, "negative_runtime_rows")

    catalog_route_ids = _catalog_route_ids(
        catalog_coverage if isinstance(catalog_coverage, dict) else None
    )
    admitted_route_ids = _admitted_catalog_route_ids(
        catalog_coverage if isinstance(catalog_coverage, dict) else None
    )

    missing_stages, incomplete_stages = _complete_rows(
        stage_rows,
        REQUIRED_RUNTIME_BINDING_STAGES,
        _stage_row_ready,
    )
    missing_fields, incomplete_fields = _complete_rows(
        field_rows,
        REQUIRED_RUNTIME_MODEL_FIELDS,
        _field_row_ready,
    )
    missing_surfaces, incomplete_surfaces = _complete_rows(
        surface_rows,
        REQUIRED_RUNTIME_SURFACES,
        _surface_row_ready,
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows,
        REQUIRED_NEGATIVE_RUNTIME_FAILURES,
        _negative_row_ready,
    )
    (
        missing_route_bindings,
        incomplete_route_bindings,
        mismatched_route_bindings,
        missing_admitted_bindings,
    ) = _route_bindings_complete(
        route_binding_rows,
        catalog_route_ids,
        admitted_route_ids,
    )

    checks = {
        "production_invocation_admission_bound": _artifact_hash_is_reproducible(
            production_admission if isinstance(production_admission, dict) else None
        ),
        "production_invocation_admission_l170_ready": _production_admission_ready(
            production_admission if isinstance(production_admission, dict) else None
        ),
        "provider_catalog_coverage_bound": _artifact_hash_is_reproducible(
            catalog_coverage if isinstance(catalog_coverage, dict) else None
        ),
        "provider_catalog_coverage_l178_ready": _catalog_coverage_ready(
            catalog_coverage if isinstance(catalog_coverage, dict) else None
        ),
        "runtime_binding_stage_rows_complete": not missing_stages
        and not incomplete_stages,
        "runtime_model_field_rows_complete": not missing_fields
        and not incomplete_fields,
        "runtime_surface_rows_complete": not missing_surfaces
        and not incomplete_surfaces,
        "all_catalog_routes_have_runtime_binding": bool(catalog_route_ids)
        and not missing_route_bindings
        and not incomplete_route_bindings
        and not mismatched_route_bindings
        and not missing_admitted_bindings,
        "negative_runtime_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "contract_signed": signing_secret is not None,
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    ready = not failure_modes

    stage_root = merkle_root([
        hash_payload({"stage": stage, "row": stage_rows.get(stage, {})})
        for stage in REQUIRED_RUNTIME_BINDING_STAGES
    ])
    field_root = merkle_root([
        hash_payload({"field": field, "row": field_rows.get(field, {})})
        for field in REQUIRED_RUNTIME_MODEL_FIELDS
    ])
    surface_root = merkle_root([
        hash_payload({"surface": surface, "row": surface_rows.get(surface, {})})
        for surface in REQUIRED_RUNTIME_SURFACES
    ])
    route_binding_root = merkle_root([
        hash_payload({"route_id": route_id, "row": route_binding_rows.get(route_id, {})})
        for route_id in catalog_route_ids
    ])
    negative_root = merkle_root([
        hash_payload({"failure": failure, "row": negative_rows.get(failure, {})})
        for failure in REQUIRED_NEGATIVE_RUNTIME_FAILURES
    ])

    public = {
        "universal_runtime_route_binding_contract_version": (
            UNIVERSAL_RUNTIME_ROUTE_BINDING_CONTRACT_VERSION
        ),
        "schema": UNIVERSAL_RUNTIME_ROUTE_BINDING_CONTRACT_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": "rdllm-universal-runtime-route-binding-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_production_invocation_level": MINIMUM_PRODUCTION_INVOCATION_LEVEL,
            "minimum_provider_catalog_coverage_level": (
                MINIMUM_PROVIDER_CATALOG_COVERAGE_LEVEL
            ),
            "runtime_model_must_match_catalog_covered_route": True,
            "provider_response_model_echo_required": True,
            "alias_and_fallback_changes_fail_closed": True,
            "source_footer_route_binding_required": True,
            "settlement_meter_route_binding_required": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_RUNTIME_ROUTE_BINDING_CONTRACT_VERSION,
        },
        "production_invocation_admission_binding": {
            "present": isinstance(production_admission, dict),
            "artifact_hash": _declared_hash(
                production_admission
                if isinstance(production_admission, dict)
                else None
            ),
            "payload_hash": hash_payload(
                _hashable_artifact(
                    production_admission
                    if isinstance(production_admission, dict)
                    else None
                )
            ),
            "hash_reproducible": checks["production_invocation_admission_bound"],
            "status": _summary(
                production_admission if isinstance(production_admission, dict) else None
            ).get("status", ""),
            "level": _summary(
                production_admission if isinstance(production_admission, dict) else None
            ).get("target_certification_level", ""),
        },
        "provider_catalog_coverage_binding": {
            "present": isinstance(catalog_coverage, dict),
            "artifact_hash": _declared_hash(
                catalog_coverage if isinstance(catalog_coverage, dict) else None
            ),
            "payload_hash": hash_payload(
                _hashable_artifact(
                    catalog_coverage if isinstance(catalog_coverage, dict) else None
                )
            ),
            "hash_reproducible": checks["provider_catalog_coverage_bound"],
            "status": _summary(
                catalog_coverage if isinstance(catalog_coverage, dict) else None
            ).get("status", ""),
            "level": _summary(
                catalog_coverage if isinstance(catalog_coverage, dict) else None
            ).get("target_certification_level", ""),
            "catalog_covered_route_count": len(catalog_route_ids),
        },
        "runtime_binding_stage_rows": {
            stage: stage_rows.get(stage, {})
            for stage in REQUIRED_RUNTIME_BINDING_STAGES
        },
        "runtime_model_field_rows": {
            field: field_rows.get(field, {})
            for field in REQUIRED_RUNTIME_MODEL_FIELDS
        },
        "runtime_surface_rows": {
            surface: surface_rows.get(surface, {}) for surface in REQUIRED_RUNTIME_SURFACES
        },
        "runtime_route_binding_rows": {
            route_id: route_binding_rows.get(route_id, {}) for route_id in catalog_route_ids
        },
        "negative_runtime_rows": {
            failure: negative_rows.get(failure, {})
            for failure in REQUIRED_NEGATIVE_RUNTIME_FAILURES
        },
        "evidence_roots": {
            "runtime_binding_stage_root": stage_root,
            "runtime_model_field_root": field_root,
            "runtime_surface_root": surface_root,
            "runtime_route_binding_root": route_binding_root,
            "negative_runtime_root": negative_root,
            "combined_runtime_route_binding_root": merkle_root(
                [stage_root, field_root, surface_root, route_binding_root, negative_root]
            ),
        },
        "checks": checks,
        "runtime_route_binding_decision": {
            "universal_runtime_route_binding_ready": ready,
            "live_model_invocation_allowed": ready,
            "response_release_allowed": ready,
            "source_footer_reliance_allowed": ready,
            "creator_settlement_allowed": ready,
            "runtime_alias_or_fallback_without_binding_blocked": True,
            "uncataloged_runtime_model_blocked": True,
            "failure_modes": failure_modes,
        },
        "coverage": {
            "missing_runtime_binding_stages": missing_stages,
            "incomplete_runtime_binding_stages": incomplete_stages,
            "missing_runtime_model_fields": missing_fields,
            "incomplete_runtime_model_fields": incomplete_fields,
            "missing_runtime_surfaces": missing_surfaces,
            "incomplete_runtime_surfaces": incomplete_surfaces,
            "missing_route_bindings": missing_route_bindings,
            "incomplete_route_bindings": incomplete_route_bindings,
            "mismatched_route_bindings": mismatched_route_bindings,
            "missing_admitted_catalog_route_bindings": missing_admitted_bindings,
            "missing_negative_runtime_failures": missing_negative,
            "incomplete_negative_runtime_failures": incomplete_negative,
        },
        "privacy": {
            "private_payloads_excluded": True,
            "private_prompts_excluded": True,
            "private_outputs_excluded": True,
            "private_provider_payloads_excluded": True,
            "public_contract_uses_hashes_and_route_metadata": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_production_invocation_level": MINIMUM_PRODUCTION_INVOCATION_LEVEL,
            "minimum_provider_catalog_coverage_level": (
                MINIMUM_PROVIDER_CATALOG_COVERAGE_LEVEL
            ),
            "runtime_binding_stage_count": len(REQUIRED_RUNTIME_BINDING_STAGES),
            "ready_runtime_binding_stage_count": len(
                REQUIRED_RUNTIME_BINDING_STAGES
            )
            - len(missing_stages)
            - len(incomplete_stages),
            "runtime_model_field_count": len(REQUIRED_RUNTIME_MODEL_FIELDS),
            "ready_runtime_model_field_count": len(REQUIRED_RUNTIME_MODEL_FIELDS)
            - len(missing_fields)
            - len(incomplete_fields),
            "runtime_surface_count": len(REQUIRED_RUNTIME_SURFACES),
            "ready_runtime_surface_count": len(REQUIRED_RUNTIME_SURFACES)
            - len(missing_surfaces)
            - len(incomplete_surfaces),
            "catalog_covered_route_count": len(catalog_route_ids),
            "ready_runtime_route_binding_count": len(catalog_route_ids)
            - len(set(missing_route_bindings))
            - len(set(incomplete_route_bindings))
            - len(set(mismatched_route_bindings)),
            "negative_runtime_failure_count": len(REQUIRED_NEGATIVE_RUNTIME_FAILURES),
            "ready_negative_runtime_failure_count": len(
                REQUIRED_NEGATIVE_RUNTIME_FAILURES
            )
            - len(missing_negative)
            - len(incomplete_negative),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": True,
            "signed_runtime_route_binding_contract": signing_secret is not None,
        },
    }
    public["universal_runtime_route_binding_contract_hash"] = hash_payload(
        _hashable_contract(public)
    )
    public["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_contract(public), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return public


def validate_universal_runtime_route_binding_contract_shape(
    contract: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for an L179 route binding contract."""

    errors: list[str] = []
    required = (
        "universal_runtime_route_binding_contract_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "production_invocation_admission_binding",
        "provider_catalog_coverage_binding",
        "runtime_binding_stage_rows",
        "runtime_model_field_rows",
        "runtime_surface_rows",
        "runtime_route_binding_rows",
        "negative_runtime_rows",
        "evidence_roots",
        "checks",
        "runtime_route_binding_decision",
        "coverage",
        "privacy",
        "summary",
        "universal_runtime_route_binding_contract_hash",
    )
    for key in required:
        if key not in contract:
            errors.append(f"missing runtime route binding field: {key}")
    if contract.get("universal_runtime_route_binding_contract_version") != (
        UNIVERSAL_RUNTIME_ROUTE_BINDING_CONTRACT_VERSION
    ):
        errors.append("unexpected universal_runtime_route_binding_contract_version")
    if contract.get("schema") != UNIVERSAL_RUNTIME_ROUTE_BINDING_CONTRACT_SCHEMA:
        errors.append("unexpected runtime route binding schema")
    for stage in REQUIRED_RUNTIME_BINDING_STAGES:
        if stage not in contract.get("runtime_binding_stage_rows", {}):
            errors.append(f"missing runtime binding stage row: {stage}")
    for field in REQUIRED_RUNTIME_MODEL_FIELDS:
        if field not in contract.get("runtime_model_field_rows", {}):
            errors.append(f"missing runtime model field row: {field}")
    for surface in REQUIRED_RUNTIME_SURFACES:
        if surface not in contract.get("runtime_surface_rows", {}):
            errors.append(f"missing runtime surface row: {surface}")
    for failure in REQUIRED_NEGATIVE_RUNTIME_FAILURES:
        if failure not in contract.get("negative_runtime_rows", {}):
            errors.append(f"missing negative runtime row: {failure}")
    for check in (
        "production_invocation_admission_bound",
        "production_invocation_admission_l170_ready",
        "provider_catalog_coverage_bound",
        "provider_catalog_coverage_l178_ready",
        "runtime_binding_stage_rows_complete",
        "runtime_model_field_rows_complete",
        "runtime_surface_rows_complete",
        "all_catalog_routes_have_runtime_binding",
        "negative_runtime_fixtures_reject",
        "contract_signed",
    ):
        if check not in contract.get("checks", {}):
            errors.append(f"missing runtime route binding check: {check}")
    return errors


def verify_universal_runtime_route_binding_contract(
    contract_input: dict[str, Any],
    contract: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L179 runtime route binding contract against replay input."""

    errors = validate_universal_runtime_route_binding_contract_shape(contract)
    expected_hash = hash_payload(_hashable_contract(contract))
    if contract.get("universal_runtime_route_binding_contract_hash") != expected_hash:
        errors.append("universal_runtime_route_binding_contract_hash mismatch")
    private_fields = _contains_private_fields(contract)
    if private_fields:
        errors.append(
            "runtime route binding contract exposes private fields: "
            + ", ".join(private_fields)
        )
    if not _private_strings_absent(contract, contract_input):
        errors.append("runtime route binding contract exposes private input strings")
    replayed = make_universal_runtime_route_binding_contract(
        contract_input,
        issuer=contract.get("issuer", DEFAULT_ISSUER),
        created_at=contract.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get("universal_runtime_route_binding_contract_hash") != contract.get(
        "universal_runtime_route_binding_contract_hash"
    ):
        errors.append("runtime route binding contract does not match replay inputs")
    if contract.get("summary", {}).get("status") != "ready":
        errors.append("runtime route binding contract is not ready")
    if (
        contract.get("runtime_route_binding_decision", {}).get(
            "universal_runtime_route_binding_ready"
        )
        is not True
    ):
        errors.append("runtime route binding decision is not ready")
    if contract.get("privacy", {}).get("private_payloads_excluded") is not True:
        errors.append("runtime route binding privacy is not preserved")
    if signing_secret:
        signature = contract.get("signature", {})
        expected_signature = sign_payload(_hashable_contract(contract), signing_secret)
        if not signature:
            errors.append("runtime route binding contract is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("runtime route binding contract signature is invalid")
    return errors
