"""Universal attribution negotiation handshake.

The L159 layer makes universal adoption request-time enforceable. L158 proves
provider behavior stays current; L159 proves a specific client/provider route
negotiated the exact attribution, source-footer, citation-locator, revocation,
telemetry, copy/export, and settlement contract before generation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root
from rdllm.universal_foundation_adoption_kernel import REQUIRED_PROVIDER_FAMILIES

UNIVERSAL_ATTRIBUTION_NEGOTIATION_HANDSHAKE_VERSION = (
    "rdllm-universal-attribution-negotiation-handshake/v1"
)
UNIVERSAL_ATTRIBUTION_NEGOTIATION_HANDSHAKE_SCHEMA = (
    "docs/schemas/universal_attribution_negotiation_handshake.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L159"
MINIMUM_DRIFT_SENTINEL_LEVEL = "RDLLM-L158"
MINIMUM_ADAPTER_HARNESS_LEVEL = "RDLLM-L157"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-attribution-negotiation-handshake.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
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

REQUIRED_NEGOTIATION_PHASES = (
    "discovery_fetch",
    "capability_offer",
    "policy_request",
    "attribution_contract_selection",
    "model_route_binding",
    "source_locator_binding",
    "citation_footer_binding",
    "settlement_meter_binding",
    "privacy_redaction_binding",
    "client_render_commitment",
    "revocation_status_check",
    "signed_preflight_receipt",
)

REQUIRED_CONTRACT_FIELDS = (
    "negotiation_id_hash",
    "client_identity_hash",
    "provider_identity_hash",
    "provider_family",
    "model_alias_hash",
    "resolved_model_id_hash",
    "rdllm_level",
    "adapter_harness_hash",
    "drift_sentinel_hash",
    "response_contract_hash",
    "claim_provenance_schema_hash",
    "source_footer_schema_hash",
    "evidence_locator_schema_hash",
    "citation_health_policy_hash",
    "freshness_policy_hash",
    "settlement_meter_hash",
    "copy_export_policy_hash",
    "telemetry_semconv_hash",
    "status_resolver_hash",
    "fail_closed_policy_hash",
    "receipt_signature_hash",
)

REQUIRED_CLIENT_CAPABILITIES = (
    "render_source_footer",
    "preserve_inline_citations",
    "preserve_copy_status_link",
    "verify_response_envelope",
    "verify_claim_provenance",
    "verify_status_resolver",
    "block_unverified_answer",
    "show_citation_locator",
    "surface_license_status",
    "surface_royalty_status",
    "support_user_audit_export",
    "support_creator_challenge_route",
)

REQUIRED_NEGOTIATION_FAILURES = (
    "client_omits_footer_render_commitment",
    "provider_does_not_resolve_model_alias",
    "stale_drift_sentinel",
    "missing_response_contract_hash",
    "source_locator_unavailable",
    "citation_health_unverified",
    "settlement_meter_absent",
    "copy_export_status_link_absent",
    "private_prompt_leak_in_public_receipt",
    "unsupported_provider_family",
)

DECLARED_HASH_FIELDS = (
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


def load_universal_attribution_negotiation_handshake_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L159 attribution negotiation handshake."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_handshake(handshake: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in handshake.items()
        if key not in {"universal_attribution_negotiation_handshake_hash", "signature"}
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
    public_payload: dict[str, Any], handshake_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in handshake_input.get("private_strings", [])
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


def _policy(handshake_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(handshake_input.get("negotiation_policy", {}))
    return {
        "profile": "rdllm-universal-attribution-negotiation-handshake-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_drift_sentinel_level": MINIMUM_DRIFT_SENTINEL_LEVEL,
        "minimum_adapter_harness_level": MINIMUM_ADAPTER_HARNESS_LEVEL,
        "well_known_path": DEFAULT_WELL_KNOWN_PATH,
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_provider_families": list(
            policy.get("required_provider_families", REQUIRED_PROVIDER_FAMILIES)
        ),
        "required_negotiation_phases": list(
            policy.get("required_negotiation_phases", REQUIRED_NEGOTIATION_PHASES)
        ),
        "required_contract_fields": list(
            policy.get("required_contract_fields", REQUIRED_CONTRACT_FIELDS)
        ),
        "required_client_capabilities": list(
            policy.get("required_client_capabilities", REQUIRED_CLIENT_CAPABILITIES)
        ),
        "required_negotiation_failures": list(
            policy.get(
                "required_negotiation_failures", REQUIRED_NEGOTIATION_FAILURES
            )
        ),
        "on_negotiation_failure": "block_generation_before_model_invocation",
        "on_drift_or_revocation": "re_negotiate_or_block_grounded_display",
        "on_private_text_leak": "block_publication",
    }


def _component_input_map(handshake_input: dict[str, Any], key: str) -> dict[str, Any]:
    value = handshake_input.get(key, {})
    return value if isinstance(value, dict) else {}


def _artifact_bindings(
    handshake_input: dict[str, Any], required_artifacts: list[str]
) -> dict[str, Any]:
    rows = []
    for name in required_artifacts:
        artifact = handshake_input.get(name)
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


def _provider_negotiation_rows(
    handshake_input: dict[str, Any], required_families: list[str]
) -> dict[str, Any]:
    row_map = _component_input_map(handshake_input, "provider_negotiation_rows")
    rows = []
    for family in required_families:
        raw = dict(row_map.get(family, {}))
        row = {
            "provider_family": family,
            "capability_offer_hash": str(raw.get("capability_offer_hash", "")),
            "policy_request_hash": str(raw.get("policy_request_hash", "")),
            "selected_contract_hash": str(raw.get("selected_contract_hash", "")),
            "resolved_model_id_hash": str(raw.get("resolved_model_id_hash", "")),
            "adapter_harness_hash": str(raw.get("adapter_harness_hash", "")),
            "drift_sentinel_hash": str(raw.get("drift_sentinel_hash", "")),
            "response_contract_hash": str(raw.get("response_contract_hash", "")),
            "settlement_meter_hash": str(raw.get("settlement_meter_hash", "")),
            "status_resolver_hash": str(raw.get("status_resolver_hash", "")),
            "telemetry_trace_hash": str(raw.get("telemetry_trace_hash", "")),
            "negotiated": raw.get("negotiated") is True,
            "privacy_preserving": raw.get("privacy_preserving") is True,
            "fail_closed": raw.get("fail_closed") is True,
        }
        row["ready"] = (
            row["negotiated"]
            and row["privacy_preserving"]
            and row["fail_closed"]
            and all(
                row[field]
                for field in (
                    "capability_offer_hash",
                    "policy_request_hash",
                    "selected_contract_hash",
                    "resolved_model_id_hash",
                    "adapter_harness_hash",
                    "drift_sentinel_hash",
                    "response_contract_hash",
                    "settlement_meter_hash",
                    "status_resolver_hash",
                    "telemetry_trace_hash",
                )
            )
        )
        row["negotiation_hash"] = hash_payload(row)
        rows.append(row)
    return {
        "rows": rows,
        "row_count": len(rows),
        "ready_count": sum(1 for row in rows if row["ready"]),
        "root": merkle_root([row["negotiation_hash"] for row in rows]),
    }


def _handshake_phase_rows(
    handshake_input: dict[str, Any], required_phases: list[str]
) -> dict[str, Any]:
    row_map = _component_input_map(handshake_input, "handshake_phase_rows")
    rows = []
    for phase in required_phases:
        raw = dict(row_map.get(phase, {}))
        row = {
            "phase": phase,
            "phase_evidence_hash": str(raw.get("phase_evidence_hash", "")),
            "client_commitment_hash": str(raw.get("client_commitment_hash", "")),
            "provider_commitment_hash": str(raw.get("provider_commitment_hash", "")),
            "verifier_command": str(raw.get("verifier_command", "")),
            "completed": raw.get("completed") is True,
            "signed": raw.get("signed") is True,
        }
        row["ready"] = (
            row["completed"]
            and row["signed"]
            and bool(row["phase_evidence_hash"])
            and bool(row["client_commitment_hash"])
            and bool(row["provider_commitment_hash"])
            and bool(row["verifier_command"])
        )
        row["phase_hash"] = hash_payload(row)
        rows.append(row)
    return {
        "rows": rows,
        "row_count": len(rows),
        "ready_count": sum(1 for row in rows if row["ready"]),
        "root": merkle_root([row["phase_hash"] for row in rows]),
    }


def _contract_field_rows(
    handshake_input: dict[str, Any],
    required_fields: list[str],
    required_families: list[str],
) -> dict[str, Any]:
    row_map = _component_input_map(handshake_input, "contract_field_rows")
    rows = []
    provider_count = len(required_families)
    for field in required_fields:
        raw = dict(row_map.get(field, {}))
        row = {
            "field": field,
            "field_path_hash": str(raw.get("field_path_hash", "")),
            "covered_provider_family_count": int(
                raw.get("covered_provider_family_count", 0)
            ),
            "required_in_preflight": raw.get("required_in_preflight") is True,
            "required_in_response_envelope": (
                raw.get("required_in_response_envelope") is True
            ),
            "public_projection_safe": raw.get("public_projection_safe") is True,
        }
        row["ready"] = (
            bool(row["field_path_hash"])
            and row["covered_provider_family_count"] >= provider_count
            and row["required_in_preflight"]
            and row["required_in_response_envelope"]
            and row["public_projection_safe"]
        )
        row["field_hash"] = hash_payload(row)
        rows.append(row)
    return {
        "rows": rows,
        "row_count": len(rows),
        "ready_count": sum(1 for row in rows if row["ready"]),
        "root": merkle_root([row["field_hash"] for row in rows]),
    }


def _client_capability_rows(
    handshake_input: dict[str, Any], required_capabilities: list[str]
) -> dict[str, Any]:
    row_map = _component_input_map(handshake_input, "client_capability_rows")
    rows = []
    for capability in required_capabilities:
        raw = dict(row_map.get(capability, {}))
        row = {
            "capability": capability,
            "capability_hash": str(raw.get("capability_hash", "")),
            "enforcement_receipt_hash": str(raw.get("enforcement_receipt_hash", "")),
            "test_vector_hash": str(raw.get("test_vector_hash", "")),
            "render_or_block_bound": raw.get("render_or_block_bound") is True,
            "copy_export_bound": raw.get("copy_export_bound") is True,
            "fail_closed": raw.get("fail_closed") is True,
        }
        row["ready"] = (
            row["render_or_block_bound"]
            and row["copy_export_bound"]
            and row["fail_closed"]
            and bool(row["capability_hash"])
            and bool(row["enforcement_receipt_hash"])
            and bool(row["test_vector_hash"])
        )
        row["client_capability_hash"] = hash_payload(row)
        rows.append(row)
    return {
        "rows": rows,
        "row_count": len(rows),
        "ready_count": sum(1 for row in rows if row["ready"]),
        "root": merkle_root([row["client_capability_hash"] for row in rows]),
    }


def _negative_negotiation_rows(
    handshake_input: dict[str, Any], required_failures: list[str]
) -> dict[str, Any]:
    row_map = _component_input_map(handshake_input, "negative_negotiation_rows")
    rows = []
    for case_id in required_failures:
        raw = dict(row_map.get(case_id, {}))
        row = {
            "case_id": case_id,
            "fixture_hash": str(raw.get("fixture_hash", "")),
            "verifier_command": str(raw.get("verifier_command", "")),
            "expected_block": raw.get("expected_block") is True,
            "observed_block": raw.get("observed_block") is True,
            "route_revoked": raw.get("route_revoked") is True,
            "settlement_held": raw.get("settlement_held") is True,
        }
        row["ready"] = (
            row["expected_block"]
            and row["observed_block"]
            and row["route_revoked"]
            and row["settlement_held"]
            and bool(row["fixture_hash"])
            and bool(row["verifier_command"])
        )
        row["negative_hash"] = hash_payload(row)
        rows.append(row)
    return {
        "rows": rows,
        "row_count": len(rows),
        "ready_count": sum(1 for row in rows if row["ready"]),
        "root": merkle_root([row["negative_hash"] for row in rows]),
    }


def _artifact_summary(handshake_input: dict[str, Any], name: str) -> dict[str, Any]:
    artifact = handshake_input.get(name)
    return _summary(artifact if isinstance(artifact, dict) else None)


def make_universal_attribution_negotiation_handshake(
    handshake_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L159 request-time attribution negotiation handshake."""

    created_at = created_at or now_iso()
    policy = _policy(handshake_input)
    required_artifacts = [str(name) for name in policy["required_core_artifacts"]]
    required_families = [str(name) for name in policy["required_provider_families"]]
    required_phases = [str(name) for name in policy["required_negotiation_phases"]]
    required_fields = [str(name) for name in policy["required_contract_fields"]]
    required_capabilities = [
        str(name) for name in policy["required_client_capabilities"]
    ]
    required_failures = [
        str(name) for name in policy["required_negotiation_failures"]
    ]

    artifact_bindings = _artifact_bindings(handshake_input, required_artifacts)
    provider_negotiations = _provider_negotiation_rows(
        handshake_input, required_families
    )
    phase_rows = _handshake_phase_rows(handshake_input, required_phases)
    field_rows = _contract_field_rows(
        handshake_input, required_fields, required_families
    )
    capability_rows = _client_capability_rows(
        handshake_input, required_capabilities
    )
    negative_rows = _negative_negotiation_rows(handshake_input, required_failures)

    certification_summary = _artifact_summary(handshake_input, "certification_report")
    provider_card = handshake_input.get("provider_attribution_card", {})
    integration_profile = handshake_input.get("integration_profile", {})
    discovery_manifest = handshake_input.get("discovery_manifest", {})
    drift_summary = _artifact_summary(
        handshake_input, "universal_provider_drift_sentinel"
    )
    harness_summary = _artifact_summary(
        handshake_input, "universal_provider_adapter_harness"
    )

    core_artifacts_ready = all(
        row["present"] and row["hash_reproducible"]
        for row in artifact_bindings["bindings"]
    )
    public_projection = {
        "policy": policy,
        "artifact_bindings": artifact_bindings,
        "provider_negotiation_rows": provider_negotiations,
        "handshake_phase_rows": phase_rows,
        "contract_field_rows": field_rows,
        "client_capability_rows": capability_rows,
        "negative_negotiation_rows": negative_rows,
    }
    private_findings = _contains_private_fields(public_projection)

    checks = {
        "all_core_artifacts_present_and_hash_reproducible": core_artifacts_ready,
        "certification_level_at_least_l158": (
            certification_summary.get("status") == "passed"
            and _level_at_least(
                certification_summary.get("highest_level", ""),
                MINIMUM_DRIFT_SENTINEL_LEVEL,
            )
        ),
        "provider_card_declares_negotiation_handshake": (
            provider_card.get("public_disclosure_surfaces", {}).get(
                "universal_attribution_negotiation_handshake"
            )
            is True
            and provider_card.get("supported_evidence_channels", {}).get(
                "universal_attribution_negotiation_handshake"
            )
            is True
        ),
        "integration_profile_declares_negotiation_handshake": (
            integration_profile.get("public_surfaces", {}).get(
                "universal_attribution_negotiation_handshake"
            )
            is True
            and "universal_attribution_negotiation_handshake"
            in integration_profile.get("schemas", {})
        ),
        "discovery_manifest_exposes_negotiation_handshake_path": (
            discovery_manifest.get("discovery", {}).get(
                "universal_attribution_negotiation_handshake_path"
            )
            == DEFAULT_WELL_KNOWN_PATH
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
        "all_provider_families_negotiated": (
            provider_negotiations["ready_count"] == provider_negotiations["row_count"]
        ),
        "all_negotiation_phases_complete": (
            phase_rows["ready_count"] == phase_rows["row_count"]
        ),
        "all_contract_fields_bound": (
            field_rows["ready_count"] == field_rows["row_count"]
        ),
        "all_client_capabilities_enforced": (
            capability_rows["ready_count"] == capability_rows["row_count"]
        ),
        "negative_negotiation_fixtures_fail_closed": (
            negative_rows["ready_count"] == negative_rows["row_count"]
        ),
        "public_projection_omits_private_payloads": (
            not private_findings
            and _private_strings_absent(public_projection, handshake_input)
        ),
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    handshake_decision = {
        "universal_attribution_negotiation_handshake_authorized": not failure_modes,
        "failure_modes": failure_modes,
        "on_failure": "block_generation_before_model_invocation_and_hold_settlement",
        "generation_without_negotiation_allowed": False,
        "revocation_required_for": [
            "model_invocation",
            "source_footer_display",
            "claim_provenance_trust",
            "copy_status_reliance",
            "creator_settlement_release",
            "customer_procurement_claim",
        ],
    }

    handshake = {
        "universal_attribution_negotiation_handshake_version": (
            UNIVERSAL_ATTRIBUTION_NEGOTIATION_HANDSHAKE_VERSION
        ),
        "schema": UNIVERSAL_ATTRIBUTION_NEGOTIATION_HANDSHAKE_SCHEMA,
        "issuer": issuer,
        "created_at": created_at,
        "policy": policy,
        "artifact_bindings": artifact_bindings,
        "provider_negotiation_rows": provider_negotiations,
        "handshake_phase_rows": phase_rows,
        "contract_field_rows": field_rows,
        "client_capability_rows": capability_rows,
        "negative_negotiation_rows": negative_rows,
        "checks": checks,
        "handshake_decision": handshake_decision,
        "privacy": {
            "public_artifact_uses_hashes_only": True,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "native_provider_payload_disclosed": False,
            "customer_identity_disclosed": False,
            "private_field_count": len(private_findings),
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "schema": UNIVERSAL_ATTRIBUTION_NEGOTIATION_HANDSHAKE_SCHEMA,
            "create": "universal-attribution-negotiation-handshake",
            "verify": "verify-universal-attribution-negotiation-handshake",
        },
        "summary": {
            "status": (
                "ready"
                if handshake_decision[
                    "universal_attribution_negotiation_handshake_authorized"
                ]
                else "blocked"
            ),
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_drift_sentinel_level": MINIMUM_DRIFT_SENTINEL_LEVEL,
            "minimum_adapter_harness_level": MINIMUM_ADAPTER_HARNESS_LEVEL,
            "provider_family_count": len(required_families),
            "ready_provider_family_count": provider_negotiations["ready_count"],
            "negotiation_phase_count": phase_rows["row_count"],
            "ready_negotiation_phase_count": phase_rows["ready_count"],
            "contract_field_count": field_rows["row_count"],
            "ready_contract_field_count": field_rows["ready_count"],
            "client_capability_count": capability_rows["row_count"],
            "ready_client_capability_count": capability_rows["ready_count"],
            "negative_negotiation_fixture_count": negative_rows["row_count"],
            "ready_negative_negotiation_fixture_count": negative_rows["ready_count"],
            "core_artifact_count": len(required_artifacts),
            "failure_mode_count": len(failure_modes),
            "request_time_negotiation_required": True,
            "generation_without_negotiation_blocked": True,
            "source_footer_contract_negotiated": True,
            "settlement_contract_negotiated": True,
            "offline_verification_supported": True,
            "privacy_preserved": checks["public_projection_omits_private_payloads"],
        },
    }
    handshake["universal_attribution_negotiation_handshake_hash"] = hash_payload(
        _hashable_handshake(handshake)
    )
    handshake["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(
                handshake["universal_attribution_negotiation_handshake_hash"],
                signing_secret,
            )
            if signing_secret
            else ""
        ),
    }
    return handshake


def validate_universal_attribution_negotiation_handshake_shape(
    handshake: dict[str, Any],
) -> list[str]:
    """Validate required public fields for an L159 negotiation handshake."""

    errors: list[str] = []
    required = (
        "universal_attribution_negotiation_handshake_version",
        "schema",
        "issuer",
        "created_at",
        "policy",
        "artifact_bindings",
        "provider_negotiation_rows",
        "handshake_phase_rows",
        "contract_field_rows",
        "client_capability_rows",
        "negative_negotiation_rows",
        "checks",
        "handshake_decision",
        "privacy",
        "well_known",
        "summary",
        "universal_attribution_negotiation_handshake_hash",
        "signature",
    )
    for key in required:
        if key not in handshake:
            errors.append(f"missing universal attribution negotiation handshake field: {key}")
    if errors:
        return errors
    if (
        handshake.get("universal_attribution_negotiation_handshake_version")
        != UNIVERSAL_ATTRIBUTION_NEGOTIATION_HANDSHAKE_VERSION
    ):
        errors.append("universal attribution negotiation handshake version is unsupported")
    if handshake.get("schema") != UNIVERSAL_ATTRIBUTION_NEGOTIATION_HANDSHAKE_SCHEMA:
        errors.append("universal attribution negotiation handshake schema is unsupported")
    summary = handshake.get("summary", {})
    if summary.get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal attribution negotiation handshake target level is not RDLLM-L159")
    if summary.get("minimum_drift_sentinel_level") != MINIMUM_DRIFT_SENTINEL_LEVEL:
        errors.append("universal attribution negotiation handshake minimum drift sentinel level is not RDLLM-L158")
    if summary.get("minimum_adapter_harness_level") != MINIMUM_ADAPTER_HARNESS_LEVEL:
        errors.append("universal attribution negotiation handshake minimum adapter harness level is not RDLLM-L157")
    if handshake.get("well_known", {}).get("path") != DEFAULT_WELL_KNOWN_PATH:
        errors.append("universal attribution negotiation handshake well-known path is incorrect")
    return errors


def verify_universal_attribution_negotiation_handshake(
    handshake: dict[str, Any],
    *,
    handshake_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L159 negotiation handshake against private replay input."""

    errors = validate_universal_attribution_negotiation_handshake_shape(handshake)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_handshake(handshake))
    if expected_hash != handshake.get("universal_attribution_negotiation_handshake_hash"):
        errors.append("universal attribution negotiation handshake hash is not reproducible")

    expected = make_universal_attribution_negotiation_handshake(
        handshake_input,
        issuer=handshake.get("issuer", DEFAULT_ISSUER),
        created_at=handshake.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "artifact_bindings",
        "provider_negotiation_rows",
        "handshake_phase_rows",
        "contract_field_rows",
        "client_capability_rows",
        "negative_negotiation_rows",
        "checks",
        "handshake_decision",
        "privacy",
        "well_known",
        "summary",
    ):
        if expected.get(key) != handshake.get(key):
            errors.append(
                f"universal attribution negotiation handshake {key} does not match input"
            )
    if (
        expected.get("universal_attribution_negotiation_handshake_hash")
        != handshake.get("universal_attribution_negotiation_handshake_hash")
    ):
        errors.append("universal attribution negotiation handshake hash does not match input")

    if handshake.get("summary", {}).get("status") != "ready":
        errors.append("universal attribution negotiation handshake status is not ready")
    for check, passed in handshake.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal attribution negotiation handshake check failed: {check}")

    private_findings = _contains_private_fields(handshake)
    if private_findings:
        errors.append(
            "universal attribution negotiation handshake exposes private field(s): "
            + ", ".join(private_findings[:5])
        )
    if not _private_strings_absent(handshake, handshake_input):
        errors.append("universal attribution negotiation handshake leaked private replay text")

    signature = handshake.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(
            handshake.get("universal_attribution_negotiation_handshake_hash", ""),
            signing_secret,
        )
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("universal attribution negotiation handshake is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("universal attribution negotiation handshake signature is invalid")

    return errors
