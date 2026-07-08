"""Universal negotiated invocation enforcement.

The L160 layer proves the L159 attribution negotiation was not advisory. Every
actual foundation-model invocation path must carry the negotiated contract before
model execution, source-footer display, copied-output reliance, or creator
settlement release.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root
from rdllm.universal_foundation_adoption_kernel import REQUIRED_PROVIDER_FAMILIES

UNIVERSAL_NEGOTIATED_INVOCATION_ENFORCEMENT_VERSION = (
    "rdllm-universal-negotiated-invocation-enforcement/v1"
)
UNIVERSAL_NEGOTIATED_INVOCATION_ENFORCEMENT_SCHEMA = (
    "docs/schemas/universal_negotiated_invocation_enforcement.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L160"
MINIMUM_NEGOTIATION_LEVEL = "RDLLM-L159"
MINIMUM_DRIFT_SENTINEL_LEVEL = "RDLLM-L158"
MINIMUM_ADAPTER_HARNESS_LEVEL = "RDLLM-L157"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-negotiated-invocation-enforcement.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "universal_attribution_negotiation_handshake",
    "universal_provider_drift_sentinel",
    "universal_provider_adapter_harness",
    "universal_foundation_adoption_kernel",
    "universal_provider_wire_protocol",
    "universal_claim_provenance_envelope",
    "source_footer_delivery",
    "client_attribution_enforcement",
    "response_envelope",
    "citation_url_health",
    "source_freshness_audit",
    "evidence_locator_manifest",
    "warranted_source_footer",
    "trust_registry",
    "foundation_runtime_router",
    "foundation_model_deployment_attestation",
)

REQUIRED_INVOCATION_SURFACES = (
    "direct_sync_api",
    "streaming_api",
    "sdk_wrapper",
    "gateway_proxy",
    "agent_runtime",
    "tool_call",
    "mcp_tool_call",
    "retrieval_context",
    "batch_job",
    "webhook_callback",
    "semantic_cache_reuse",
    "fallback_route",
)

REQUIRED_ENFORCEMENT_CONTROLS = (
    "preflight_token_required",
    "sdk_middleware_gate",
    "gateway_proxy_gate",
    "streaming_first_chunk_hold",
    "tool_call_gate",
    "mcp_schema_gate",
    "retrieval_context_gate",
    "batch_job_gate",
    "webhook_callback_gate",
    "fallback_route_block",
    "cache_reuse_revalidation_gate",
    "settlement_release_gate",
    "audit_export_gate",
)

REQUIRED_TELEMETRY_FIELDS = (
    "trace_id_hash",
    "span_id_hash",
    "parent_span_hash",
    "provider_family_hash",
    "model_id_hash",
    "model_alias_hash",
    "rdllm_negotiation_hash",
    "rdllm_invocation_receipt_hash",
    "response_envelope_hash",
    "claim_provenance_hash",
    "source_footer_hash",
    "settlement_meter_hash",
    "copy_status_link_hash",
    "policy_decision_hash",
)

REQUIRED_BYPASS_FAILURES = (
    "direct_provider_call_without_handshake",
    "sdk_retry_drops_preflight_token",
    "proxy_strips_negotiation_header",
    "stream_starts_before_contract_lock",
    "tool_call_without_claim_binding",
    "mcp_tool_schema_substitution",
    "retrieval_context_without_source_locator",
    "batch_callback_without_invocation_receipt",
    "fallback_model_without_negotiation",
    "cache_reuse_without_revalidation",
    "settlement_release_without_invocation_receipt",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_negotiated_invocation_enforcement_hash",
    "universal_attribution_negotiation_handshake_hash",
    "universal_provider_drift_sentinel_hash",
    "universal_provider_adapter_harness_hash",
    "universal_foundation_adoption_kernel_hash",
    "universal_provider_wire_protocol_hash",
    "universal_claim_provenance_envelope_hash",
    "foundation_model_deployment_attestation_hash",
    "foundation_runtime_router_hash",
    "source_footer_delivery_hash",
    "client_enforcement_hash",
    "citation_url_health_hash",
    "source_freshness_audit_hash",
    "evidence_locator_manifest_hash",
    "warranted_source_footer_hash",
    "trust_registry_hash",
    "attestation_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "contract_hash",
    "graph_hash",
    "report_hash",
    "bundle_hash",
    "summary_hash",
    "receipt_hash",
    "envelope_hash",
    "event_hash",
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
    "source_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
    "tool_payload",
    "raw_tool_output",
    "memory_value",
    "raw_memory",
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


def load_universal_negotiated_invocation_enforcement_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L160 invocation enforcement artifact."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_enforcement(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_negotiated_invocation_enforcement_hash", "signature"}
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


def _private_strings_absent(
    public_payload: dict[str, Any], enforcement_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in enforcement_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    summary = artifact.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def _artifact_status(artifact: dict[str, Any] | None) -> str:
    return str(_summary(artifact).get("status", ""))


def _artifact_target_level(artifact: dict[str, Any] | None) -> str:
    summary = _summary(artifact)
    return str(
        summary.get("target_certification_level")
        or summary.get("highest_level")
        or summary.get("attested_highest_level")
        or ""
    )


def _artifact_version(artifact: dict[str, Any] | None) -> str:
    if not artifact:
        return ""
    for key, value in artifact.items():
        if key.endswith("_version") and isinstance(value, str):
            return value
    return ""


def _level_number(level: Any) -> int:
    if not isinstance(level, str):
        return -1
    try:
        return int(level.removeprefix("RDLLM-L"))
    except ValueError:
        return -1


def _level_at_least(level: Any, minimum: str) -> bool:
    return _level_number(level) >= _level_number(minimum)


def _policy(enforcement_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(enforcement_input.get("invocation_enforcement_policy", {}))
    return {
        "profile": "rdllm-universal-negotiated-invocation-enforcement-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_negotiation_level": MINIMUM_NEGOTIATION_LEVEL,
        "minimum_drift_sentinel_level": MINIMUM_DRIFT_SENTINEL_LEVEL,
        "minimum_adapter_harness_level": MINIMUM_ADAPTER_HARNESS_LEVEL,
        "well_known_path": DEFAULT_WELL_KNOWN_PATH,
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_provider_families": list(
            policy.get("required_provider_families", REQUIRED_PROVIDER_FAMILIES)
        ),
        "required_invocation_surfaces": list(
            policy.get("required_invocation_surfaces", REQUIRED_INVOCATION_SURFACES)
        ),
        "required_enforcement_controls": list(
            policy.get(
                "required_enforcement_controls", REQUIRED_ENFORCEMENT_CONTROLS
            )
        ),
        "required_telemetry_fields": list(
            policy.get("required_telemetry_fields", REQUIRED_TELEMETRY_FIELDS)
        ),
        "required_bypass_failures": list(
            policy.get("required_bypass_failures", REQUIRED_BYPASS_FAILURES)
        ),
        "on_missing_negotiation": "block_model_invocation",
        "on_bypass_detected": "revoke_route_hold_settlement_and_publish_status",
        "on_private_text_leak": "block_publication",
    }


def _component_input_map(enforcement_input: dict[str, Any], key: str) -> dict[str, Any]:
    value = enforcement_input.get(key, {})
    return value if isinstance(value, dict) else {}


def _artifact_bindings(
    enforcement_input: dict[str, Any], required_artifacts: list[str]
) -> dict[str, Any]:
    rows = []
    for name in required_artifacts:
        artifact = enforcement_input.get(name)
        if not isinstance(artifact, dict):
            artifact = None
        row = {
            "name": name,
            "version": _artifact_version(artifact),
            "declared_hash": _declared_hash(artifact),
            "payload_hash": hash_payload(artifact) if artifact else "",
            "hash_reproducible": _artifact_hash_is_reproducible(artifact),
            "status": _artifact_status(artifact),
            "target_level": _artifact_target_level(artifact),
            "present": bool(artifact),
        }
        row["artifact_binding_hash"] = hash_payload(row)
        rows.append(row)
    root = merkle_root([row["artifact_binding_hash"] for row in rows])
    return {"bindings": rows, "binding_root": root}


def _invocation_enforcement_rows(
    enforcement_input: dict[str, Any],
    required_families: list[str],
    required_surfaces: list[str],
) -> dict[str, Any]:
    row_map = _component_input_map(enforcement_input, "invocation_enforcement_rows")
    rows = []
    for family in required_families:
        for surface in required_surfaces:
            raw = dict(row_map.get(f"{family}:{surface}", {}))
            row = {
                "provider_family": family,
                "invocation_surface": surface,
                "negotiation_hash": str(raw.get("negotiation_hash", "")),
                "invocation_receipt_hash": str(raw.get("invocation_receipt_hash", "")),
                "model_request_hash": str(raw.get("model_request_hash", "")),
                "route_policy_hash": str(raw.get("route_policy_hash", "")),
                "response_envelope_hash": str(raw.get("response_envelope_hash", "")),
                "claim_provenance_hash": str(raw.get("claim_provenance_hash", "")),
                "source_footer_hash": str(raw.get("source_footer_hash", "")),
                "telemetry_span_hash": str(raw.get("telemetry_span_hash", "")),
                "settlement_meter_hash": str(raw.get("settlement_meter_hash", "")),
                "bypass_guard_hash": str(raw.get("bypass_guard_hash", "")),
                "negotiated_before_invocation": (
                    raw.get("negotiated_before_invocation") is True
                ),
                "blocked_on_missing_negotiation": (
                    raw.get("blocked_on_missing_negotiation") is True
                ),
                "emitted_after_gate": raw.get("emitted_after_gate") is True,
                "privacy_preserving": raw.get("privacy_preserving") is True,
                "fail_closed": raw.get("fail_closed") is True,
            }
            row["ready"] = (
                row["negotiated_before_invocation"]
                and row["blocked_on_missing_negotiation"]
                and row["emitted_after_gate"]
                and row["privacy_preserving"]
                and row["fail_closed"]
                and all(
                    row[field]
                    for field in (
                        "negotiation_hash",
                        "invocation_receipt_hash",
                        "model_request_hash",
                        "route_policy_hash",
                        "response_envelope_hash",
                        "claim_provenance_hash",
                        "source_footer_hash",
                        "telemetry_span_hash",
                        "settlement_meter_hash",
                        "bypass_guard_hash",
                    )
                )
            )
            row["enforcement_hash"] = hash_payload(row)
            rows.append(row)
    return {
        "rows": rows,
        "row_count": len(rows),
        "ready_count": sum(1 for row in rows if row["ready"]),
        "root": merkle_root([row["enforcement_hash"] for row in rows]),
    }


def _control_rows(
    enforcement_input: dict[str, Any],
    required_controls: list[str],
    required_families: list[str],
    required_surfaces: list[str],
) -> dict[str, Any]:
    row_map = _component_input_map(enforcement_input, "enforcement_control_rows")
    rows = []
    for control in required_controls:
        raw = dict(row_map.get(control, {}))
        row = {
            "control": control,
            "control_hash": str(raw.get("control_hash", "")),
            "verifier_command": str(raw.get("verifier_command", "")),
            "covered_provider_family_count": int(
                raw.get("covered_provider_family_count", 0)
            ),
            "covered_invocation_surface_count": int(
                raw.get("covered_invocation_surface_count", 0)
            ),
            "blocks_bypass": raw.get("blocks_bypass") is True,
            "holds_settlement": raw.get("holds_settlement") is True,
            "public_projection_safe": raw.get("public_projection_safe") is True,
        }
        row["ready"] = (
            bool(row["control_hash"])
            and bool(row["verifier_command"])
            and row["covered_provider_family_count"] >= len(required_families)
            and row["covered_invocation_surface_count"] >= len(required_surfaces)
            and row["blocks_bypass"]
            and row["holds_settlement"]
            and row["public_projection_safe"]
        )
        row["control_row_hash"] = hash_payload(row)
        rows.append(row)
    return {
        "rows": rows,
        "row_count": len(rows),
        "ready_count": sum(1 for row in rows if row["ready"]),
        "root": merkle_root([row["control_row_hash"] for row in rows]),
    }


def _telemetry_field_rows(
    enforcement_input: dict[str, Any],
    required_fields: list[str],
    required_families: list[str],
    required_surfaces: list[str],
) -> dict[str, Any]:
    row_map = _component_input_map(enforcement_input, "telemetry_field_rows")
    rows = []
    for field in required_fields:
        raw = dict(row_map.get(field, {}))
        row = {
            "field": field,
            "field_path_hash": str(raw.get("field_path_hash", "")),
            "covered_provider_family_count": int(
                raw.get("covered_provider_family_count", 0)
            ),
            "covered_invocation_surface_count": int(
                raw.get("covered_invocation_surface_count", 0)
            ),
            "required_in_invocation_span": (
                raw.get("required_in_invocation_span") is True
            ),
            "required_in_audit_export": raw.get("required_in_audit_export") is True,
            "privacy_preserving": raw.get("privacy_preserving") is True,
        }
        row["ready"] = (
            bool(row["field_path_hash"])
            and row["covered_provider_family_count"] >= len(required_families)
            and row["covered_invocation_surface_count"] >= len(required_surfaces)
            and row["required_in_invocation_span"]
            and row["required_in_audit_export"]
            and row["privacy_preserving"]
        )
        row["telemetry_field_hash"] = hash_payload(row)
        rows.append(row)
    return {
        "rows": rows,
        "row_count": len(rows),
        "ready_count": sum(1 for row in rows if row["ready"]),
        "root": merkle_root([row["telemetry_field_hash"] for row in rows]),
    }


def _bypass_failure_rows(
    enforcement_input: dict[str, Any], required_failures: list[str]
) -> dict[str, Any]:
    row_map = _component_input_map(enforcement_input, "bypass_failure_rows")
    rows = []
    for case_id in required_failures:
        raw = dict(row_map.get(case_id, {}))
        row = {
            "case_id": case_id,
            "fixture_hash": str(raw.get("fixture_hash", "")),
            "verifier_command": str(raw.get("verifier_command", "")),
            "bypass_detected": raw.get("bypass_detected") is True,
            "invocation_blocked": raw.get("invocation_blocked") is True,
            "route_revoked": raw.get("route_revoked") is True,
            "settlement_held": raw.get("settlement_held") is True,
        }
        row["ready"] = (
            row["bypass_detected"]
            and row["invocation_blocked"]
            and row["route_revoked"]
            and row["settlement_held"]
            and bool(row["fixture_hash"])
            and bool(row["verifier_command"])
        )
        row["bypass_hash"] = hash_payload(row)
        rows.append(row)
    return {
        "rows": rows,
        "row_count": len(rows),
        "ready_count": sum(1 for row in rows if row["ready"]),
        "root": merkle_root([row["bypass_hash"] for row in rows]),
    }


def _artifact_summary(enforcement_input: dict[str, Any], name: str) -> dict[str, Any]:
    artifact = enforcement_input.get(name)
    return _summary(artifact if isinstance(artifact, dict) else None)


def make_universal_negotiated_invocation_enforcement(
    enforcement_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L160 negotiated invocation enforcement artifact."""

    created_at = created_at or now_iso()
    policy = _policy(enforcement_input)
    required_artifacts = [str(name) for name in policy["required_core_artifacts"]]
    required_families = [str(name) for name in policy["required_provider_families"]]
    required_surfaces = [str(name) for name in policy["required_invocation_surfaces"]]
    required_controls = [str(name) for name in policy["required_enforcement_controls"]]
    required_telemetry = [str(name) for name in policy["required_telemetry_fields"]]
    required_failures = [str(name) for name in policy["required_bypass_failures"]]

    artifact_bindings = _artifact_bindings(enforcement_input, required_artifacts)
    invocation_rows = _invocation_enforcement_rows(
        enforcement_input, required_families, required_surfaces
    )
    control_rows = _control_rows(
        enforcement_input, required_controls, required_families, required_surfaces
    )
    telemetry_rows = _telemetry_field_rows(
        enforcement_input, required_telemetry, required_families, required_surfaces
    )
    bypass_rows = _bypass_failure_rows(enforcement_input, required_failures)

    certification_summary = _artifact_summary(enforcement_input, "certification_report")
    provider_card = enforcement_input.get("provider_attribution_card", {})
    integration_profile = enforcement_input.get("integration_profile", {})
    discovery_manifest = enforcement_input.get("discovery_manifest", {})
    negotiation_summary = _artifact_summary(
        enforcement_input, "universal_attribution_negotiation_handshake"
    )
    drift_summary = _artifact_summary(
        enforcement_input, "universal_provider_drift_sentinel"
    )
    harness_summary = _artifact_summary(
        enforcement_input, "universal_provider_adapter_harness"
    )

    core_artifacts_ready = all(
        row["present"] and row["hash_reproducible"]
        for row in artifact_bindings["bindings"]
    )
    public_projection = {
        "policy": policy,
        "artifact_bindings": artifact_bindings,
        "invocation_enforcement_rows": invocation_rows,
        "enforcement_control_rows": control_rows,
        "telemetry_field_rows": telemetry_rows,
        "bypass_failure_rows": bypass_rows,
    }
    private_findings = _contains_private_fields(public_projection)

    checks = {
        "all_core_artifacts_present_and_hash_reproducible": core_artifacts_ready,
        "certification_level_at_least_l159": (
            certification_summary.get("status") == "passed"
            and _level_at_least(
                certification_summary.get("highest_level", ""),
                MINIMUM_NEGOTIATION_LEVEL,
            )
        ),
        "provider_card_declares_invocation_enforcement": (
            provider_card.get("public_disclosure_surfaces", {}).get(
                "universal_negotiated_invocation_enforcement"
            )
            is True
            and provider_card.get("supported_evidence_channels", {}).get(
                "universal_negotiated_invocation_enforcement"
            )
            is True
        ),
        "integration_profile_declares_invocation_enforcement": (
            integration_profile.get("public_surfaces", {}).get(
                "universal_negotiated_invocation_enforcement"
            )
            is True
            and "universal_negotiated_invocation_enforcement"
            in integration_profile.get("schemas", {})
        ),
        "discovery_manifest_exposes_invocation_enforcement_path": (
            discovery_manifest.get("discovery", {}).get(
                "universal_negotiated_invocation_enforcement_path"
            )
            == DEFAULT_WELL_KNOWN_PATH
        ),
        "negotiation_handshake_ready_l159": (
            negotiation_summary.get("status") == "ready"
            and negotiation_summary.get("target_certification_level")
            == MINIMUM_NEGOTIATION_LEVEL
        ),
        "drift_sentinel_ready_l158": (
            drift_summary.get("status") == "ready"
            and drift_summary.get("target_certification_level")
            == MINIMUM_DRIFT_SENTINEL_LEVEL
        ),
        "adapter_harness_ready_l157": (
            harness_summary.get("status") == "ready"
            and harness_summary.get("target_certification_level")
            == MINIMUM_ADAPTER_HARNESS_LEVEL
        ),
        "all_invocation_surfaces_enforced": (
            invocation_rows["ready_count"] == invocation_rows["row_count"]
        ),
        "all_enforcement_controls_ready": (
            control_rows["ready_count"] == control_rows["row_count"]
        ),
        "all_telemetry_fields_bound": (
            telemetry_rows["ready_count"] == telemetry_rows["row_count"]
        ),
        "bypass_fixtures_fail_closed": (
            bypass_rows["ready_count"] == bypass_rows["row_count"]
        ),
        "public_projection_omits_private_payloads": (
            not private_findings
            and _private_strings_absent(public_projection, enforcement_input)
        ),
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    enforcement_decision = {
        "universal_negotiated_invocation_enforcement_authorized": not failure_modes,
        "failure_modes": failure_modes,
        "on_failure": "block_invocation_revoke_route_hold_settlement_and_publish_status",
        "model_invocation_without_negotiated_contract_allowed": False,
        "revocation_required_for": [
            "model_invocation",
            "streaming_output",
            "tool_execution",
            "copied_output_reliance",
            "source_footer_display",
            "creator_settlement_release",
        ],
    }

    report = {
        "universal_negotiated_invocation_enforcement_version": (
            UNIVERSAL_NEGOTIATED_INVOCATION_ENFORCEMENT_VERSION
        ),
        "schema": UNIVERSAL_NEGOTIATED_INVOCATION_ENFORCEMENT_SCHEMA,
        "issuer": issuer,
        "created_at": created_at,
        "policy": policy,
        "artifact_bindings": artifact_bindings,
        "invocation_enforcement_rows": invocation_rows,
        "enforcement_control_rows": control_rows,
        "telemetry_field_rows": telemetry_rows,
        "bypass_failure_rows": bypass_rows,
        "checks": checks,
        "enforcement_decision": enforcement_decision,
        "privacy": {
            "public_artifact_uses_hashes_only": True,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "native_provider_payload_disclosed": False,
            "tool_payload_disclosed": False,
            "private_field_count": len(private_findings),
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "schema": UNIVERSAL_NEGOTIATED_INVOCATION_ENFORCEMENT_SCHEMA,
            "create": "universal-negotiated-invocation-enforcement",
            "verify": "verify-universal-negotiated-invocation-enforcement",
        },
        "summary": {
            "status": (
                "ready"
                if enforcement_decision[
                    "universal_negotiated_invocation_enforcement_authorized"
                ]
                else "blocked"
            ),
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_negotiation_level": MINIMUM_NEGOTIATION_LEVEL,
            "minimum_drift_sentinel_level": MINIMUM_DRIFT_SENTINEL_LEVEL,
            "minimum_adapter_harness_level": MINIMUM_ADAPTER_HARNESS_LEVEL,
            "provider_family_count": len(required_families),
            "invocation_surface_count": len(required_surfaces),
            "provider_surface_count": invocation_rows["row_count"],
            "ready_provider_surface_count": invocation_rows["ready_count"],
            "enforcement_control_count": control_rows["row_count"],
            "ready_enforcement_control_count": control_rows["ready_count"],
            "telemetry_field_count": telemetry_rows["row_count"],
            "ready_telemetry_field_count": telemetry_rows["ready_count"],
            "bypass_failure_count": bypass_rows["row_count"],
            "ready_bypass_failure_count": bypass_rows["ready_count"],
            "core_artifact_count": len(required_artifacts),
            "failure_mode_count": len(failure_modes),
            "invocation_gate_required": True,
            "model_invocation_without_negotiation_blocked": True,
            "settlement_release_requires_invocation_receipt": True,
            "offline_verification_supported": True,
            "privacy_preserved": checks["public_projection_omits_private_payloads"],
        },
    }
    report["universal_negotiated_invocation_enforcement_hash"] = hash_payload(
        _hashable_enforcement(report)
    )
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(
                report["universal_negotiated_invocation_enforcement_hash"],
                signing_secret,
            )
            if signing_secret
            else ""
        ),
    }
    return report


def validate_universal_negotiated_invocation_enforcement_shape(
    report: dict[str, Any],
) -> list[str]:
    """Validate required public fields for an L160 invocation enforcement artifact."""

    errors: list[str] = []
    required = (
        "universal_negotiated_invocation_enforcement_version",
        "schema",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "invocation_enforcement_rows",
        "enforcement_control_rows",
        "telemetry_field_rows",
        "bypass_failure_rows",
        "checks",
        "enforcement_decision",
        "privacy",
        "well_known",
        "summary",
        "universal_negotiated_invocation_enforcement_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing universal negotiated invocation enforcement field: {key}")
    if errors:
        return errors
    if (
        report.get("universal_negotiated_invocation_enforcement_version")
        != UNIVERSAL_NEGOTIATED_INVOCATION_ENFORCEMENT_VERSION
    ):
        errors.append("universal negotiated invocation enforcement version is unsupported")
    if report.get("schema") != UNIVERSAL_NEGOTIATED_INVOCATION_ENFORCEMENT_SCHEMA:
        errors.append("universal negotiated invocation enforcement schema is unsupported")
    summary = report.get("summary", {})
    if summary.get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal negotiated invocation enforcement target level is not RDLLM-L160")
    if summary.get("minimum_negotiation_level") != MINIMUM_NEGOTIATION_LEVEL:
        errors.append("universal negotiated invocation enforcement minimum negotiation level is not RDLLM-L159")
    if summary.get("minimum_drift_sentinel_level") != MINIMUM_DRIFT_SENTINEL_LEVEL:
        errors.append("universal negotiated invocation enforcement minimum drift sentinel level is not RDLLM-L158")
    if summary.get("minimum_adapter_harness_level") != MINIMUM_ADAPTER_HARNESS_LEVEL:
        errors.append("universal negotiated invocation enforcement minimum adapter harness level is not RDLLM-L157")
    if report.get("well_known", {}).get("path") != DEFAULT_WELL_KNOWN_PATH:
        errors.append("universal negotiated invocation enforcement well-known path is incorrect")
    return errors


def verify_universal_negotiated_invocation_enforcement(
    report: dict[str, Any],
    *,
    enforcement_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L160 invocation enforcement artifact against private replay input."""

    errors = validate_universal_negotiated_invocation_enforcement_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_enforcement(report))
    if expected_hash != report.get("universal_negotiated_invocation_enforcement_hash"):
        errors.append("universal negotiated invocation enforcement hash is not reproducible")

    expected = make_universal_negotiated_invocation_enforcement(
        enforcement_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "invocation_enforcement_rows",
        "enforcement_control_rows",
        "telemetry_field_rows",
        "bypass_failure_rows",
        "checks",
        "enforcement_decision",
        "privacy",
        "well_known",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(
                f"universal negotiated invocation enforcement {key} does not match input"
            )
    if (
        expected.get("universal_negotiated_invocation_enforcement_hash")
        != report.get("universal_negotiated_invocation_enforcement_hash")
    ):
        errors.append("universal negotiated invocation enforcement hash does not match input")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("universal negotiated invocation enforcement status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal negotiated invocation enforcement check failed: {check}")

    private_findings = _contains_private_fields(report)
    if private_findings:
        errors.append(
            "universal negotiated invocation enforcement exposes private field(s): "
            + ", ".join(private_findings[:5])
        )
    if not _private_strings_absent(report, enforcement_input):
        errors.append("universal negotiated invocation enforcement leaked private replay text")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(
            report.get("universal_negotiated_invocation_enforcement_hash", ""),
            signing_secret,
        )
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("universal negotiated invocation enforcement is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("universal negotiated invocation enforcement signature is invalid")

    return errors
