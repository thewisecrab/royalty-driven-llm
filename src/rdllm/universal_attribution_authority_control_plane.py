"""Universal attribution authority control planes for foundation-model runtimes.

The L145 layer closes the gap between publishable attribution proof and runtime
authority. It binds who delegated an AI action, what scope the action had, which
context/tool/model/memory path was authorized, which inference chain executed,
which settlement authority applied, and which intervention or revocation checks
ran before an attributed answer, agent action, or creator settlement can be
trusted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_ATTRIBUTION_AUTHORITY_CONTROL_PLANE_VERSION = (
    "rdllm-universal-attribution-authority-control-plane/v1"
)
UNIVERSAL_ATTRIBUTION_AUTHORITY_CONTROL_PLANE_SCHEMA = (
    "docs/schemas/universal_attribution_authority_control_plane.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L145"
MINIMUM_INPUT_LEVEL = "RDLLM-L144"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-attribution-authority-control-plane.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "universal_confidential_attribution_audit",
    "universal_training_serving_contract",
    "universal_context_provenance_bridge",
    "universal_invocation_guard",
    "universal_invocation_coverage",
    "universal_invocation_witness",
    "foundation_model_deployment_attestation",
    "foundation_runtime_router",
    "foundation_runtime_adapter",
    "composite_foundation_adapter",
    "foundation_api_profile",
    "agent_tool_attribution_ledger",
    "persistent_memory_provenance",
    "private_reasoning_attribution",
    "source_footer_delivery",
    "proof_carrying_response",
    "response_envelope",
    "certification_report",
    "certification_attestation",
    "provider_attribution_card",
    "integration_profile",
    "trust_registry",
)

REQUIRED_PROVIDER_FAMILIES = (
    "openai",
    "anthropic",
    "google",
    "meta",
    "mistral",
    "cohere",
    "xai",
    "deepseek",
    "local_open_weights",
    "enterprise_gateway",
)

REQUIRED_RUNTIME_SURFACES = (
    "model_api",
    "agent_runtime",
    "mcp_tool",
    "retrieval_connector",
    "memory_store",
    "browser_or_web_search",
    "file_connector",
    "code_execution_tool",
    "enterprise_gateway",
    "settlement_gateway",
)

REQUIRED_AUTHORITY_CHAINS = (
    "actor_chain",
    "intent_chain",
    "context_chain",
    "tool_chain",
    "model_invocation_chain",
    "inference_chain",
    "memory_chain",
    "settlement_chain",
    "publication_chain",
    "challenge_chain",
)

REQUIRED_ENFORCEMENT_GATES = (
    "preflight_authorization",
    "context_admission",
    "tool_authority",
    "model_route_authority",
    "private_evidence_authority",
    "citation_footer_authority",
    "settlement_authority",
    "egress_release_authority",
    "intervention_recording",
    "revocation_abort",
)

REQUIRED_STAKEHOLDER_ROLES = (
    "creator",
    "content_owner",
    "end_user",
    "enterprise_admin",
    "foundation_provider",
    "model_gateway",
    "agent_runtime_operator",
    "tool_provider",
    "independent_auditor",
    "regulator",
)

REQUIRED_FAILURE_CASES = (
    "missing_actor_delegation",
    "stale_intent_scope",
    "tool_call_without_authority",
    "context_source_without_license_scope",
    "model_invocation_not_bound",
    "inference_chain_missing",
    "memory_read_without_provenance",
    "citation_footer_after_authority_denial",
    "settlement_without_authorized_payee",
    "private_evidence_authority_gap",
    "intervention_not_recorded",
    "revoked_authority_still_used",
    "unsupported_provider_family",
    "split_view_authority_log",
)

REQUIRED_VERIFIER_COMMANDS = (
    "verify-universal-confidential-attribution-audit",
    "verify-universal-training-serving-contract",
    "verify-universal-context-provenance-bridge",
    "verify-universal-invocation-guard",
    "verify-universal-invocation-coverage",
    "verify-universal-invocation-witness",
    "verify-foundation-model-deployment-attestation",
    "verify-agent-tool-attribution-ledger",
    "verify-private-reasoning-attribution",
    "verify-persistent-memory-provenance",
    "verify-source-footer-delivery",
    "verify-proof-carrying-response",
    "verify-response-envelope",
    "verify-universal-attribution-authority-control-plane",
)

DECLARED_HASH_FIELDS = (
    "universal_attribution_authority_control_plane_hash",
    "universal_confidential_attribution_audit_hash",
    "universal_training_serving_contract_hash",
    "universal_context_provenance_bridge_hash",
    "universal_invocation_guard_hash",
    "universal_invocation_coverage_hash",
    "universal_invocation_witness_hash",
    "foundation_model_deployment_attestation_hash",
    "foundation_runtime_router_hash",
    "foundation_runtime_adapter_hash",
    "foundation_profile_hash",
    "composite_foundation_adapter_hash",
    "tool_ledger_hash",
    "agent_tool_attribution_ledger_hash",
    "persistent_memory_provenance_hash",
    "private_reasoning_attribution_hash",
    "source_footer_delivery_hash",
    "proof_response_hash",
    "envelope_hash",
    "report_hash",
    "attestation_hash",
    "card_hash",
    "profile_hash",
    "trust_registry_hash",
    "summary_hash",
    "contract_hash",
    "bundle_hash",
    "graph_hash",
    "manifest_hash",
    "receipt_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "raw_query",
    "query_text",
    "output",
    "output_text",
    "answer_text",
    "raw_model_output",
    "raw_training_record",
    "training_text",
    "dataset_sample",
    "source_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reward_text",
    "preference_text",
    "critique_text",
    "hidden_state",
    "activation",
    "gradient",
    "model_weight",
    "model_weights",
    "model_parameters",
    "serving_log",
    "customer_log",
    "billing_record",
    "customer_id",
    "customer_email",
    "raw_authority_payload",
    "delegation_secret",
    "actor_private_key",
    "tool_secret",
    "session_token",
    "oauth_token",
    "api_key",
    "raw_tool_result",
    "raw_memory_cell",
    "raw_context",
    "raw_instruction",
    "system_prompt",
    "developer_prompt",
    "customer_record",
    "access_token",
    "refresh_token",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_attribution_authority_control_plane_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L145 authority control plane."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_attribution_authority_control_plane_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    hashable = {
        key: value
        for key, value in artifact.items()
        if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
    }
    metadata = hashable.get("response_metadata_contract")
    if isinstance(metadata, dict) and "foundation_profile_hash" in artifact:
        header_values = dict(metadata.get("header_values", {}))
        header_values["RDLLM-Foundation-Profile-Hash"] = "<foundation_profile_hash>"
        metadata = dict(metadata)
        metadata["header_values"] = header_values
        hashable["response_metadata_contract"] = metadata
    return hashable


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


def _private_strings_absent(report: dict[str, Any], control_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item) for item in control_input.get("private_strings", []) if str(item).strip()
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


def _component_input_map(control_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    value = control_input.get(key, {})
    if isinstance(value, dict):
        return {str(name): row for name, row in value.items() if isinstance(row, dict)}
    if isinstance(value, list):
        result: dict[str, dict[str, Any]] = {}
        for row in value:
            if not isinstance(row, dict):
                continue
            name = (
                row.get("provider_family")
                or row.get("runtime_surface")
                or row.get("authority_chain")
                or row.get("enforcement_gate")
                or row.get("role")
                or row.get("case_id")
                or row.get("command")
            )
            if name:
                result[str(name)] = row
        return result
    return {}


def _obligation_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get("provider_family", "")), str(row.get("runtime_surface", "")))


def _policy(control_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(control_input.get("authority_control_policy", {}))
    return {
        "profile": "rdllm-universal-attribution-authority-control-plane-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_provider_families": list(
            policy.get("required_provider_families", REQUIRED_PROVIDER_FAMILIES)
        ),
        "required_runtime_surfaces": list(
            policy.get("required_runtime_surfaces", REQUIRED_RUNTIME_SURFACES)
        ),
        "required_authority_chains": list(
            policy.get("required_authority_chains", REQUIRED_AUTHORITY_CHAINS)
        ),
        "required_enforcement_gates": list(
            policy.get("required_enforcement_gates", REQUIRED_ENFORCEMENT_GATES)
        ),
        "required_stakeholder_roles": list(
            policy.get("required_stakeholder_roles", REQUIRED_STAKEHOLDER_ROLES)
        ),
        "required_failure_cases": list(
            policy.get("required_failure_cases", REQUIRED_FAILURE_CASES)
        ),
        "required_verifier_commands": list(
            policy.get("required_verifier_commands", REQUIRED_VERIFIER_COMMANDS)
        ),
        "on_missing_delegation": "block_model_or_agent_action",
        "on_intent_scope_expiry": "deny_context_tool_and_settlement_authority",
        "on_missing_inference_chain": "block_attributed_output_release",
        "on_revoked_authority": "abort_runtime_and_preserve_audit_log",
        "on_authority_log_split_view": "block_public_assurance_and_open_challenge",
        "on_private_payload_leak": "block_publication",
    }


def _artifact_bindings(control_input: dict[str, Any], names: list[str]) -> dict[str, Any]:
    rows = []
    for name in names:
        artifact = control_input.get(name)
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
    return {
        "artifact_count": len(rows),
        "artifact_binding_root": merkle_root(
            [row["artifact_binding_hash"] for row in rows]
        ),
        "bindings": rows,
    }


def _provider_family_rows(
    control_input: dict[str, Any], required_families: list[str]
) -> list[dict[str, Any]]:
    family_map = _component_input_map(control_input, "provider_family_rows")
    rows = []
    for family in sorted(required_families):
        item = family_map.get(family, {})
        row = {
            "provider_family": family,
            "authority_registry_hash": str(item.get("authority_registry_hash", "")),
            "policy_engine_hash": str(item.get("policy_engine_hash", "")),
            "delegation_verifier_hash": str(item.get("delegation_verifier_hash", "")),
            "inference_chain_verifier_hash": str(
                item.get("inference_chain_verifier_hash", "")
            ),
            "intervention_log_hash": str(item.get("intervention_log_hash", "")),
            "public_verifier_command": str(item.get("public_verifier_command", "")),
            "supports_authority_control_plane": item.get("supports_authority_control_plane") is True,
            "supports_agentic_runtime_authority": item.get("supports_agentic_runtime_authority") is True,
            "supports_tool_authority": item.get("supports_tool_authority") is True,
            "supports_settlement_authority": item.get("supports_settlement_authority") is True,
            "fail_closed": item.get("fail_closed") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["authority_registry_hash"])
            and bool(row["policy_engine_hash"])
            and bool(row["delegation_verifier_hash"])
            and bool(row["inference_chain_verifier_hash"])
            and bool(row["intervention_log_hash"])
            and row["public_verifier_command"]
            == "verify-universal-attribution-authority-control-plane"
            and row["supports_authority_control_plane"]
            and row["supports_agentic_runtime_authority"]
            and row["supports_tool_authority"]
            and row["supports_settlement_authority"]
            and row["fail_closed"]
        )
        row["provider_family_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _runtime_surface_rows(
    control_input: dict[str, Any], required_surfaces: list[str]
) -> list[dict[str, Any]]:
    surface_map = _component_input_map(control_input, "runtime_surface_rows")
    rows = []
    for surface in sorted(required_surfaces):
        item = surface_map.get(surface, {})
        row = {
            "runtime_surface": surface,
            "surface_policy_hash": str(item.get("surface_policy_hash", "")),
            "admission_schema_hash": str(item.get("admission_schema_hash", "")),
            "authority_log_hash": str(item.get("authority_log_hash", "")),
            "evidence_projection_hash": str(item.get("evidence_projection_hash", "")),
            "replay_fixture_hash": str(item.get("replay_fixture_hash", "")),
            "covered": item.get("covered") is True,
            "fail_closed": item.get("fail_closed") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["surface_policy_hash"])
            and bool(row["admission_schema_hash"])
            and bool(row["authority_log_hash"])
            and bool(row["evidence_projection_hash"])
            and bool(row["replay_fixture_hash"])
            and row["covered"]
            and row["fail_closed"]
        )
        row["runtime_surface_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _authority_chain_rows(
    control_input: dict[str, Any], required_chains: list[str]
) -> list[dict[str, Any]]:
    chain_map = _component_input_map(control_input, "authority_chain_rows")
    rows = []
    for chain in sorted(required_chains):
        item = chain_map.get(chain, {})
        row = {
            "authority_chain": chain,
            "chain_root": str(item.get("chain_root", "")),
            "verifier_hash": str(item.get("verifier_hash", "")),
            "delegation_scope_hash": str(item.get("delegation_scope_hash", "")),
            "expiry_policy_hash": str(item.get("expiry_policy_hash", "")),
            "revocation_channel_hash": str(item.get("revocation_channel_hash", "")),
            "covered": item.get("covered") is True,
            "fail_closed": item.get("fail_closed") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["chain_root"])
            and bool(row["verifier_hash"])
            and bool(row["delegation_scope_hash"])
            and bool(row["expiry_policy_hash"])
            and bool(row["revocation_channel_hash"])
            and row["covered"]
            and row["fail_closed"]
        )
        row["authority_chain_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _enforcement_gate_rows(
    control_input: dict[str, Any], required_gates: list[str]
) -> list[dict[str, Any]]:
    gate_map = _component_input_map(control_input, "enforcement_gate_rows")
    rows = []
    for gate in sorted(required_gates):
        item = gate_map.get(gate, {})
        row = {
            "enforcement_gate": gate,
            "precondition_hash": str(item.get("precondition_hash", "")),
            "decision_schema_hash": str(item.get("decision_schema_hash", "")),
            "denial_fixture_hash": str(item.get("denial_fixture_hash", "")),
            "intervention_policy_hash": str(item.get("intervention_policy_hash", "")),
            "telemetry_binding_hash": str(item.get("telemetry_binding_hash", "")),
            "covered": item.get("covered") is True,
            "fail_closed": item.get("fail_closed") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["precondition_hash"])
            and bool(row["decision_schema_hash"])
            and bool(row["denial_fixture_hash"])
            and bool(row["intervention_policy_hash"])
            and bool(row["telemetry_binding_hash"])
            and row["covered"]
            and row["fail_closed"]
        )
        row["enforcement_gate_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _stakeholder_role_rows(
    control_input: dict[str, Any], required_roles: list[str]
) -> list[dict[str, Any]]:
    role_map = _component_input_map(control_input, "stakeholder_role_rows")
    rows = []
    for role in sorted(required_roles):
        item = role_map.get(role, {})
        row = {
            "role": role,
            "delegation_policy_hash": str(item.get("delegation_policy_hash", "")),
            "authority_scope_hash": str(item.get("authority_scope_hash", "")),
            "challenge_route_hash": str(item.get("challenge_route_hash", "")),
            "audit_visibility_hash": str(item.get("audit_visibility_hash", "")),
            "revocation_route_hash": str(item.get("revocation_route_hash", "")),
            "authorized": item.get("authorized") is True,
            "fail_closed": item.get("fail_closed") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["delegation_policy_hash"])
            and bool(row["authority_scope_hash"])
            and bool(row["challenge_route_hash"])
            and bool(row["audit_visibility_hash"])
            and bool(row["revocation_route_hash"])
            and row["authorized"]
            and row["fail_closed"]
        )
        row["stakeholder_role_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _authority_obligation_rows(
    control_input: dict[str, Any],
    required_families: list[str],
    required_surfaces: list[str],
) -> list[dict[str, Any]]:
    rows = []
    for item in sorted(
        control_input.get("authority_obligation_rows", []),
        key=lambda row: (
            str(row.get("provider_family", "")),
            str(row.get("runtime_surface", "")),
        ),
    ):
        if not isinstance(item, dict):
            continue
        row = {
            "provider_family": str(item.get("provider_family", "")),
            "runtime_surface": str(item.get("runtime_surface", "")),
            "authority_chain_root": str(item.get("authority_chain_root", "")),
            "actor_delegation_hash": str(item.get("actor_delegation_hash", "")),
            "intent_scope_hash": str(item.get("intent_scope_hash", "")),
            "context_scope_hash": str(item.get("context_scope_hash", "")),
            "tool_scope_hash": str(item.get("tool_scope_hash", "")),
            "model_invocation_hash": str(item.get("model_invocation_hash", "")),
            "inference_chain_hash": str(item.get("inference_chain_hash", "")),
            "memory_scope_hash": str(item.get("memory_scope_hash", "")),
            "settlement_scope_hash": str(item.get("settlement_scope_hash", "")),
            "intervention_log_hash": str(item.get("intervention_log_hash", "")),
            "revocation_check_hash": str(item.get("revocation_check_hash", "")),
            "confidential_audit_hash": str(item.get("confidential_audit_hash", "")),
            "actor_authorized": item.get("actor_authorized") is True,
            "intent_in_scope": item.get("intent_in_scope") is True,
            "context_authorized": item.get("context_authorized") is True,
            "tool_authorized": item.get("tool_authorized") is True,
            "model_invocation_bound": item.get("model_invocation_bound") is True,
            "inference_chain_bound": item.get("inference_chain_bound") is True,
            "memory_provenance_bound": item.get("memory_provenance_bound") is True,
            "settlement_authorized": item.get("settlement_authorized") is True,
            "intervention_recorded": item.get("intervention_recorded") is True,
            "revocation_checked": item.get("revocation_checked") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["required"] = (
            row["provider_family"] in required_families
            and row["runtime_surface"] in required_surfaces
        )
        row["ready"] = (
            row["required"]
            and bool(row["authority_chain_root"])
            and bool(row["actor_delegation_hash"])
            and bool(row["intent_scope_hash"])
            and bool(row["context_scope_hash"])
            and bool(row["tool_scope_hash"])
            and bool(row["model_invocation_hash"])
            and bool(row["inference_chain_hash"])
            and bool(row["memory_scope_hash"])
            and bool(row["settlement_scope_hash"])
            and bool(row["intervention_log_hash"])
            and bool(row["revocation_check_hash"])
            and bool(row["confidential_audit_hash"])
            and row["actor_authorized"]
            and row["intent_in_scope"]
            and row["context_authorized"]
            and row["tool_authorized"]
            and row["model_invocation_bound"]
            and row["inference_chain_bound"]
            and row["memory_provenance_bound"]
            and row["settlement_authorized"]
            and row["intervention_recorded"]
            and row["revocation_checked"]
            and row["fail_closed"]
        )
        row["authority_obligation_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _failure_case_rows(
    control_input: dict[str, Any], required_cases: list[str]
) -> list[dict[str, Any]]:
    case_map = _component_input_map(control_input, "failure_case_rows")
    rows = []
    for case_id in sorted(required_cases):
        item = case_map.get(case_id, {})
        row = {
            "case_id": case_id,
            "fixture_hash": str(item.get("fixture_hash", "")),
            "verifier_command": str(item.get("verifier_command", "")),
            "expected_block": item.get("expected_block") is True,
            "observed_block": item.get("observed_block") is True,
            "required": True,
        }
        row["passed"] = (
            bool(row["fixture_hash"])
            and row["verifier_command"]
            == "verify-universal-attribution-authority-control-plane"
            and row["expected_block"]
            and row["observed_block"]
        )
        row["failure_case_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _verifier_command_rows(
    control_input: dict[str, Any], required_commands: list[str]
) -> list[dict[str, Any]]:
    declared = {str(command) for command in control_input.get("verifier_commands", [])}
    integration = control_input.get("integration_profile", {})
    declared |= set(
        integration.get("verifier_contract", {}).get("reference_cli_commands", [])
    )
    rows = []
    for command in sorted(required_commands):
        row = {"command": command, "declared": command in declared, "required": True}
        row["verifier_command_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _discovery_manifest_exposes_control_path(control_input: dict[str, Any]) -> bool:
    discovery_manifest = control_input.get("discovery_manifest", {})
    if not isinstance(discovery_manifest, dict) or not discovery_manifest:
        return True
    discovery = discovery_manifest.get("discovery", {})
    if not isinstance(discovery, dict):
        return False
    path = discovery.get("universal_attribution_authority_control_plane_path")
    return path in {"", None, DEFAULT_WELL_KNOWN_PATH}


def make_universal_attribution_authority_control_plane(
    control_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L145 universal authority control-plane contract."""

    created_at = created_at or now_iso()
    policy = _policy(control_input)
    required_artifacts = [str(name) for name in policy["required_core_artifacts"]]
    required_families = [str(name) for name in policy["required_provider_families"]]
    required_surfaces = [str(name) for name in policy["required_runtime_surfaces"]]
    required_chains = [str(name) for name in policy["required_authority_chains"]]
    required_gates = [str(name) for name in policy["required_enforcement_gates"]]
    required_roles = [str(name) for name in policy["required_stakeholder_roles"]]
    required_cases = [str(name) for name in policy["required_failure_cases"]]
    required_commands = [str(name) for name in policy["required_verifier_commands"]]

    confidential_audit = control_input.get("universal_confidential_attribution_audit", {})

    artifact_bindings = _artifact_bindings(control_input, required_artifacts)
    provider_family_rows = _provider_family_rows(control_input, required_families)
    runtime_surface_rows = _runtime_surface_rows(control_input, required_surfaces)
    authority_chain_rows = _authority_chain_rows(control_input, required_chains)
    enforcement_gate_rows = _enforcement_gate_rows(control_input, required_gates)
    stakeholder_role_rows = _stakeholder_role_rows(control_input, required_roles)
    obligation_rows = _authority_obligation_rows(
        control_input, required_families, required_surfaces
    )
    failure_case_rows = _failure_case_rows(control_input, required_cases)
    verifier_command_rows = _verifier_command_rows(control_input, required_commands)

    required_matrix = {
        (provider_family, surface)
        for provider_family in required_families
        for surface in required_surfaces
    }
    observed_matrix = {_obligation_key(row) for row in obligation_rows}

    public_projection = {
        "artifact_bindings": artifact_bindings,
        "provider_family_rows": provider_family_rows,
        "runtime_surface_rows": runtime_surface_rows,
        "authority_chain_rows": authority_chain_rows,
        "enforcement_gate_rows": enforcement_gate_rows,
        "stakeholder_role_rows": stakeholder_role_rows,
        "authority_obligation_rows": obligation_rows,
        "failure_case_rows": failure_case_rows,
        "verifier_command_rows": verifier_command_rows,
    }
    private_findings = _contains_private_fields(public_projection)

    checks = {
        "required_core_artifacts_present": all(
            row["present"] for row in artifact_bindings["bindings"]
        ),
        "artifact_hashes_reproducible": all(
            row["hash_reproducible"] for row in artifact_bindings["bindings"]
        ),
        "confidential_attribution_audit_ready_l144": (
            _artifact_status(confidential_audit) == "ready"
            and _artifact_target_level(confidential_audit) == MINIMUM_INPUT_LEVEL
            and _summary(confidential_audit).get("privacy_preserved") is True
        ),
        "provider_family_coverage_complete": all(
            row["ready"] for row in provider_family_rows
        ),
        "runtime_surface_coverage_complete": all(
            row["ready"] for row in runtime_surface_rows
        ),
        "authority_chains_complete": all(row["ready"] for row in authority_chain_rows),
        "enforcement_gates_complete": all(row["ready"] for row in enforcement_gate_rows),
        "stakeholder_roles_complete": all(row["ready"] for row in stakeholder_role_rows),
        "authority_obligations_present": bool(obligation_rows),
        "authority_obligation_matrix_complete": (
            bool(required_matrix) and required_matrix <= observed_matrix
        ),
        "authority_obligations_ready": bool(obligation_rows)
        and all(row["ready"] for row in obligation_rows),
        "actor_intent_context_authority_bound": bool(obligation_rows)
        and all(
            row["actor_authorized"]
            and row["intent_in_scope"]
            and row["context_authorized"]
            for row in obligation_rows
        ),
        "tool_model_inference_authority_bound": bool(obligation_rows)
        and all(
            row["tool_authorized"]
            and row["model_invocation_bound"]
            and row["inference_chain_bound"]
            for row in obligation_rows
        ),
        "memory_settlement_authority_bound": bool(obligation_rows)
        and all(
            row["memory_provenance_bound"] and row["settlement_authorized"]
            for row in obligation_rows
        ),
        "intervention_and_revocation_bound": bool(obligation_rows)
        and all(
            row["intervention_recorded"] and row["revocation_checked"]
            for row in obligation_rows
        ),
        "failure_cases_fail_closed": all(row["passed"] for row in failure_case_rows),
        "public_verifier_commands_declared": all(
            row["declared"] for row in verifier_command_rows
        ),
        "discovery_manifest_exposes_control_path": (
            _discovery_manifest_exposes_control_path(control_input)
        ),
        "public_report_has_no_private_field_names": not private_findings,
    }
    checks["private_strings_absent"] = _private_strings_absent(
        public_projection, control_input
    )

    failed_checks = [name for name, passed in checks.items() if passed is not True]
    failure_modes_by_check = {
        "required_core_artifacts_present": "authority_control_artifact_missing",
        "artifact_hashes_reproducible": "authority_control_artifact_hash_not_reproducible",
        "confidential_attribution_audit_ready_l144": "confidential_attribution_audit_not_ready_l144",
        "provider_family_coverage_complete": "authority_control_provider_family_gap",
        "runtime_surface_coverage_complete": "authority_control_runtime_surface_gap",
        "authority_chains_complete": "authority_control_chain_gap",
        "enforcement_gates_complete": "authority_control_gate_gap",
        "stakeholder_roles_complete": "authority_control_stakeholder_gap",
        "authority_obligations_present": "authority_control_obligation_missing",
        "authority_obligation_matrix_complete": "authority_control_obligation_matrix_gap",
        "authority_obligations_ready": "authority_control_obligation_gate_failed",
        "actor_intent_context_authority_bound": "actor_intent_context_authority_gap",
        "tool_model_inference_authority_bound": "tool_model_inference_authority_gap",
        "memory_settlement_authority_bound": "memory_settlement_authority_gap",
        "intervention_and_revocation_bound": "intervention_or_revocation_gap",
        "failure_cases_fail_closed": "authority_control_negative_case_not_blocked",
        "public_verifier_commands_declared": "authority_control_verifier_command_missing",
        "discovery_manifest_exposes_control_path": "authority_control_discovery_path_missing",
        "public_report_has_no_private_field_names": "private_field_name_leak",
        "private_strings_absent": "private_string_leak",
    }
    failure_modes = [failure_modes_by_check[name] for name in failed_checks]
    ready = not failed_checks

    commitments = {
        "artifact_binding_root": artifact_bindings["artifact_binding_root"],
        "provider_family_root": merkle_root(
            [row["provider_family_row_hash"] for row in provider_family_rows]
        ),
        "runtime_surface_root": merkle_root(
            [row["runtime_surface_row_hash"] for row in runtime_surface_rows]
        ),
        "authority_chain_root": merkle_root(
            [row["authority_chain_row_hash"] for row in authority_chain_rows]
        ),
        "enforcement_gate_root": merkle_root(
            [row["enforcement_gate_row_hash"] for row in enforcement_gate_rows]
        ),
        "stakeholder_role_root": merkle_root(
            [row["stakeholder_role_row_hash"] for row in stakeholder_role_rows]
        ),
        "authority_obligation_root": merkle_root(
            [row["authority_obligation_row_hash"] for row in obligation_rows]
        ),
        "failure_case_root": merkle_root(
            [row["failure_case_row_hash"] for row in failure_case_rows]
        ),
        "verifier_command_root": merkle_root(
            [row["verifier_command_row_hash"] for row in verifier_command_rows]
        ),
        "universal_confidential_attribution_audit_hash": _declared_hash(
            confidential_audit
        ),
    }
    commitments["authority_control_commitment_hash"] = hash_payload(commitments)

    report: dict[str, Any] = {
        "authority_control_version": UNIVERSAL_ATTRIBUTION_AUTHORITY_CONTROL_PLANE_VERSION,
        "issuer": issuer,
        "created_at": created_at,
        "authority_control_policy": policy,
        "artifact_bindings": artifact_bindings,
        "provider_family_rows": provider_family_rows,
        "runtime_surface_rows": runtime_surface_rows,
        "authority_chain_rows": authority_chain_rows,
        "enforcement_gate_rows": enforcement_gate_rows,
        "stakeholder_role_rows": stakeholder_role_rows,
        "authority_obligation_rows": obligation_rows,
        "failure_case_rows": failure_case_rows,
        "verifier_command_rows": verifier_command_rows,
        "commitments": commitments,
        "checks": checks,
        "control_decision": {
            "decision": "publish_universal_attribution_authority_control_plane"
            if ready
            else "block_universal_attribution_authority_control_plane",
            "publication_authorized": ready,
            "runtime_authority_approved": ready,
            "agentic_action_authorized": ready,
            "direct_settlement_authorized": ready,
            "failed_checks": failed_checks,
            "failure_modes": failure_modes,
            "safe_runtime_policy": "serve_agentic_or_foundation_model_outputs_only_when_actor_intent_context_tool_model_inference_memory_settlement_and_revocation_authority_all_verify"
            if ready
            else "block_runtime_authority_and_preserve_audit_challenge",
        },
        "schemas": {
            "universal_attribution_authority_control_plane": (
                UNIVERSAL_ATTRIBUTION_AUTHORITY_CONTROL_PLANE_SCHEMA
            ),
            "universal_confidential_attribution_audit": (
                "docs/schemas/universal_confidential_attribution_audit.schema.json"
            ),
            "universal_training_serving_contract": (
                "docs/schemas/universal_training_serving_contract.schema.json"
            ),
            "integration_profile": "docs/schemas/integration_profile.schema.json",
            "trust_registry": "docs/schemas/trust_registry.schema.json",
        },
        "privacy": {
            "raw_prompt_text_disclosed": False,
            "raw_answer_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_training_text_disclosed": False,
            "raw_tool_payload_disclosed": False,
            "raw_memory_payload_disclosed": False,
            "raw_customer_or_billing_logs_disclosed": False,
            "model_weights_or_hidden_states_disclosed": False,
            "hash_only_authority_bindings": True,
            "private_field_findings": private_findings,
            "private_strings_absent": checks["private_strings_absent"],
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "provider_family_count": len(provider_family_rows),
            "runtime_surface_count": len(runtime_surface_rows),
            "authority_chain_count": len(authority_chain_rows),
            "enforcement_gate_count": len(enforcement_gate_rows),
            "stakeholder_role_count": len(stakeholder_role_rows),
            "authority_obligation_count": len(obligation_rows),
            "required_obligation_count": len(required_matrix),
            "failure_case_count": len(failure_case_rows),
            "verifier_command_count": len(verifier_command_rows),
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": not private_findings
            and checks["private_strings_absent"] is True,
            "universal_confidential_attribution_audit_hash": _declared_hash(
                confidential_audit
            ),
            "authority_control_commitment_hash": commitments[
                "authority_control_commitment_hash"
            ],
        },
    }
    report["universal_attribution_authority_control_plane_hash"] = hash_payload(
        _hashable_report(report)
    )
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "unsigned",
        "issuer": issuer,
        "value": sign_payload(_hashable_report(report), signing_secret)
        if signing_secret
        else "",
    }
    return report


def validate_universal_attribution_authority_control_plane_shape(
    report: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = (
        "authority_control_version",
        "issuer",
        "created_at",
        "authority_control_policy",
        "artifact_bindings",
        "provider_family_rows",
        "runtime_surface_rows",
        "authority_chain_rows",
        "enforcement_gate_rows",
        "stakeholder_role_rows",
        "authority_obligation_rows",
        "failure_case_rows",
        "verifier_command_rows",
        "commitments",
        "checks",
        "control_decision",
        "schemas",
        "privacy",
        "summary",
        "universal_attribution_authority_control_plane_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing authority control plane field: {key}")
    if errors:
        return errors
    if (
        report.get("authority_control_version")
        != UNIVERSAL_ATTRIBUTION_AUTHORITY_CONTROL_PLANE_VERSION
    ):
        errors.append("authority control plane version is unsupported")
    if (
        report.get("schemas", {}).get("universal_attribution_authority_control_plane")
        != UNIVERSAL_ATTRIBUTION_AUTHORITY_CONTROL_PLANE_SCHEMA
    ):
        errors.append("authority control plane schema path is not declared")
    if (
        report.get("summary", {}).get("target_certification_level")
        != TARGET_CERTIFICATION_LEVEL
    ):
        errors.append("authority control plane target level is not RDLLM-L145")
    for finding in _contains_private_fields(report):
        errors.append(f"authority control plane contains private field: {finding}")
    return errors


def verify_universal_attribution_authority_control_plane(
    report: dict[str, Any],
    *,
    control_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L145 authority control plane by replaying inputs."""

    errors = validate_universal_attribution_authority_control_plane_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("universal_attribution_authority_control_plane_hash"):
        errors.append("authority control plane hash is not reproducible")

    expected = make_universal_attribution_authority_control_plane(
        control_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "authority_control_policy",
        "artifact_bindings",
        "provider_family_rows",
        "runtime_surface_rows",
        "authority_chain_rows",
        "enforcement_gate_rows",
        "stakeholder_role_rows",
        "authority_obligation_rows",
        "failure_case_rows",
        "verifier_command_rows",
        "commitments",
        "checks",
        "control_decision",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"authority control plane {key} does not match replay")
    if expected.get("universal_attribution_authority_control_plane_hash") != report.get(
        "universal_attribution_authority_control_plane_hash"
    ):
        errors.append("authority control plane hash does not match replay")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("authority control plane status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"authority control plane check failed: {check}")

    if not _private_strings_absent(report, control_input):
        errors.append("authority control plane leaks a private input string")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("authority control plane is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("authority control plane signature is invalid")

    return errors
