"""Universal context provenance bridge for model, agent, and tool runtimes.

The L140 layer closes the runtime gap between provider-neutral RDLLM adoption
and the external context systems that modern foundation models use: MCP-style
tool calls, retrieval connectors, vector stores, file search, browser search,
publisher feeds, enterprise connectors, and creator license endpoints. The
bridge requires every external context access to become a signed source claim
that can be replayed into visible footers, private reasoning commitments, agent
step attribution, and royalty settlement.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_CONTEXT_PROVENANCE_BRIDGE_VERSION = (
    "rdllm-universal-context-provenance-bridge/v1"
)
UNIVERSAL_CONTEXT_PROVENANCE_BRIDGE_SCHEMA = (
    "docs/schemas/universal_context_provenance_bridge.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L140"
MINIMUM_INPUT_LEVEL = "RDLLM-L139"
DEFAULT_WELL_KNOWN_PATH = "/.well-known/rdllm/universal-context-provenance-bridge.json"

REQUIRED_CORE_ARTIFACTS = (
    "universal_interop_test_kit",
    "universal_adoption_standard",
    "universal_rdllm_passport",
    "integration_profile",
    "discovery_manifest",
    "provider_attribution_card",
    "certification_report",
    "foundation_runtime_adapter",
    "universal_invocation_guard",
    "source_footer_delivery",
    "response_envelope",
    "private_reasoning_attribution",
    "persistent_memory_provenance",
    "post_training_signal_provenance",
    "trust_registry",
)

REQUIRED_CONTEXT_PROTOCOLS = (
    "model_context_protocol_http",
    "model_context_protocol_stdio",
    "web_retrieval",
    "vector_database",
    "file_search",
    "browser_search",
    "agent_tool_call",
    "creator_license_endpoint",
    "enterprise_connector",
    "media_content_credential",
)

REQUIRED_BRIDGE_SURFACES = (
    "context_access_manifest",
    "context_license_negotiation",
    "source_claim_projection",
    "footer_delivery_projection",
    "royalty_event_projection",
    "agent_step_attribution",
    "consent_revocation_projection",
    "audit_log_export",
    "zero_trust_authorization",
    "offline_replay_fixture",
)

REQUIRED_STANDARDS_MAPPINGS = (
    "model_context_protocol",
    "oauth2_1_audience_bound_tokens",
    "w3c_verifiable_credentials_data_integrity",
    "w3c_prov",
    "c2pa_content_credentials",
    "eu_gpai_copyright_transparency",
    "rdllm_source_footer",
)

REQUIRED_FAILURE_CASES = (
    "unauthorized_context_access",
    "tool_result_without_source_claim",
    "retrieval_used_without_footer_citation",
    "hallucinated_tool_citation",
    "stale_context_lease",
    "rights_denied_context",
    "mcp_token_audience_mismatch",
    "agent_step_not_attributed",
    "private_context_text_leak",
    "connector_without_audit_log",
)

REQUIRED_VERIFIER_COMMANDS = (
    "verify-universal-interop-test-kit",
    "verify-universal-adoption-standard",
    "verify-universal-rdllm-passport",
    "verify-foundation-runtime-adapter",
    "verify-universal-invocation-guard",
    "verify-source-footer-delivery",
    "verify-response-envelope",
    "verify-private-reasoning-attribution",
    "verify-post-training-signal-provenance",
    "verify-universal-context-provenance-bridge",
)

DECLARED_HASH_FIELDS = (
    "universal_context_provenance_bridge_hash",
    "universal_interop_test_kit_hash",
    "universal_adoption_standard_hash",
    "universal_rdllm_passport_hash",
    "foundation_runtime_adapter_hash",
    "universal_invocation_guard_hash",
    "source_footer_delivery_hash",
    "private_reasoning_attribution_hash",
    "persistent_memory_provenance_hash",
    "post_training_signal_provenance_hash",
    "trust_registry_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "report_hash",
    "envelope_hash",
    "bundle_hash",
    "summary_hash",
    "statement_hash",
    "receipt_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "raw_context",
    "raw_context_text",
    "context_text",
    "tool_result",
    "raw_tool_result",
    "raw_model_output",
    "raw_native_response",
    "native_response_body",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "raw_answer_text",
    "rendered_output",
    "source_text",
    "training_text",
    "document_text",
    "full_source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
    "customer_id",
    "customer_email",
    "license_server_secret",
    "raw_license_token",
    "access_token",
    "refresh_token",
    "secret",
    "signing_secret",
    "private_key",
}

ALLOWED_RIGHTS_STATES = {"licensed", "public_domain", "creator_owned", "consented"}
DENIED_RIGHTS_STATES = {"denied", "expired", "revoked", "unknown"}


def load_universal_context_provenance_bridge_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L140 universal context provenance bridge."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_context_provenance_bridge_hash", "signature"}
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


def _private_strings_absent(report: dict[str, Any], bridge_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item) for item in bridge_input.get("private_strings", []) if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _level_number(level: Any) -> int:
    if not isinstance(level, str):
        return -1
    try:
        return int(level.removeprefix("RDLLM-L"))
    except ValueError:
        return -1


def _level_at_least(level: Any, minimum: str) -> bool:
    return _level_number(level) >= _level_number(minimum)


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


def _as_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _source_labels_from_footer(delivery: dict[str, Any]) -> set[str]:
    labels: set[str] = set()
    for row in delivery.get("source_delivery_rows", []):
        if not isinstance(row, dict):
            continue
        label = row.get("source_label") or row.get("label")
        if label:
            labels.add(str(label))
    for row in delivery.get("claim_delivery_rows", []):
        if not isinstance(row, dict):
            continue
        for label in row.get("source_labels", []):
            labels.add(str(label))
    return labels


def _source_labels_from_response(envelope: dict[str, Any]) -> set[str]:
    response = envelope.get("response", {})
    labels = set()
    for label in response.get("source_labels", []):
        labels.add(str(label))
    return labels


def _component_input_map(bridge_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    value = bridge_input.get(key, {})
    if isinstance(value, dict):
        return {
            str(name): row
            for name, row in value.items()
            if isinstance(row, dict)
        }
    if isinstance(value, list):
        return {
            str(
                row.get("name")
                or row.get("surface")
                or row.get("protocol")
                or row.get("standard_id")
                or row.get("case_id")
            ): row
            for row in value
            if isinstance(row, dict)
        }
    return {}


def _policy(bridge_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(bridge_input.get("bridge_policy", {}))
    return {
        "profile": "rdllm-universal-context-provenance-bridge-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_context_protocols": list(
            policy.get("required_context_protocols", REQUIRED_CONTEXT_PROTOCOLS)
        ),
        "required_bridge_surfaces": list(
            policy.get("required_bridge_surfaces", REQUIRED_BRIDGE_SURFACES)
        ),
        "required_standards_mappings": list(
            policy.get("required_standards_mappings", REQUIRED_STANDARDS_MAPPINGS)
        ),
        "required_failure_cases": list(
            policy.get("required_failure_cases", REQUIRED_FAILURE_CASES)
        ),
        "required_verifier_commands": list(
            policy.get("required_verifier_commands", REQUIRED_VERIFIER_COMMANDS)
        ),
        "on_missing_l139_kit": "reject_runtime_context_adoption_claim",
        "on_unattributed_context_access": "block_model_response_release",
        "on_denied_or_expired_context_rights": "block_context_use_and_route_to_escrow",
        "on_unbound_agent_step": "block_agent_trace_publication",
        "on_private_context_leak": "block_publication",
    }


def _artifact_bindings(bridge_input: dict[str, Any], names: list[str]) -> dict[str, Any]:
    rows = []
    for name in names:
        artifact = bridge_input.get(name)
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


def _bridge_surface_rows(
    bridge_input: dict[str, Any], required_surfaces: list[str]
) -> list[dict[str, Any]]:
    surface_map = _component_input_map(bridge_input, "bridge_surface_rows")
    rows = []
    for surface in sorted(required_surfaces):
        item = surface_map.get(surface, {})
        row = {
            "surface": surface,
            "schema_hash": str(item.get("schema_hash", "")),
            "endpoint_path": str(item.get("endpoint_path", "")),
            "verifier_command": str(item.get("verifier_command", "")),
            "offline_replay_supported": item.get("offline_replay_supported") is True,
            "fail_closed": item.get("fail_closed") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["schema_hash"])
            and bool(row["endpoint_path"])
            and bool(row["verifier_command"])
            and row["offline_replay_supported"]
            and row["fail_closed"]
        )
        row["bridge_surface_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _protocol_adapter_rows(
    bridge_input: dict[str, Any], required_protocols: list[str]
) -> list[dict[str, Any]]:
    adapter_map = _component_input_map(bridge_input, "protocol_adapter_rows")
    rows = []
    for protocol in sorted(required_protocols):
        item = adapter_map.get(protocol, {})
        row = {
            "protocol": protocol,
            "adapter_hash": str(item.get("adapter_hash", "")),
            "access_event_schema_hash": str(item.get("access_event_schema_hash", "")),
            "source_claim_schema_hash": str(item.get("source_claim_schema_hash", "")),
            "license_projection_hash": str(item.get("license_projection_hash", "")),
            "authorization_profile": str(item.get("authorization_profile", "")),
            "token_audience_bound": item.get("token_audience_bound") is True,
            "least_privilege_scope": item.get("least_privilege_scope") is True,
            "audit_log_hash": str(item.get("audit_log_hash", "")),
            "fail_closed": item.get("fail_closed") is True,
            "status": str(item.get("status", "")),
            "required": True,
        }
        row["ready"] = (
            bool(row["adapter_hash"])
            and bool(row["access_event_schema_hash"])
            and bool(row["source_claim_schema_hash"])
            and bool(row["license_projection_hash"])
            and bool(row["authorization_profile"])
            and row["authorization_profile"] != "token_passthrough"
            and row["token_audience_bound"]
            and row["least_privilege_scope"]
            and bool(row["audit_log_hash"])
            and row["fail_closed"]
            and row["status"] == "passed"
        )
        row["protocol_adapter_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _standards_mapping_rows(
    bridge_input: dict[str, Any], required_mappings: list[str]
) -> list[dict[str, Any]]:
    mapping_map = _component_input_map(bridge_input, "standards_mapping_rows")
    rows = []
    for standard_id in sorted(required_mappings):
        item = mapping_map.get(standard_id, {})
        row = {
            "standard_id": standard_id,
            "mapping_hash": str(item.get("mapping_hash", "")),
            "bridge_surface": str(item.get("bridge_surface", "")),
            "covered": item.get("covered") is True,
            "normative_reference_url": str(item.get("normative_reference_url", "")),
            "required": True,
        }
        row["ready"] = (
            bool(row["mapping_hash"])
            and bool(row["bridge_surface"])
            and row["covered"]
            and bool(row["normative_reference_url"])
        )
        row["standards_mapping_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _context_access_rows(bridge_input: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in sorted(
        bridge_input.get("context_access_rows", []),
        key=lambda row: (int(row.get("sequence", 0) or 0), str(row.get("context_id", ""))),
    ):
        if not isinstance(item, dict):
            continue
        row = {
            "context_id": str(item.get("context_id", "")),
            "sequence": int(item.get("sequence", 0) or 0),
            "protocol": str(item.get("protocol", "")),
            "source_label": str(item.get("source_label", "")),
            "creator_id": str(item.get("creator_id", "")),
            "work_id": str(item.get("work_id", "")),
            "access_event_hash": str(item.get("access_event_hash", "")),
            "license_token_hash": str(item.get("license_token_hash", "")),
            "rights_state": str(item.get("rights_state", "")),
            "consent_state": str(item.get("consent_state", "")),
            "lease_state": str(item.get("lease_state", "")),
            "usage_purpose": str(item.get("usage_purpose", "answer_generation")),
            "claim_span_hash": str(item.get("claim_span_hash", "")),
            "footer_source_label": str(item.get("footer_source_label", "")),
            "royalty_share": str(item.get("royalty_share", "0")),
            "agent_step_id": str(item.get("agent_step_id", "")),
            "retrieval_rank": int(item.get("retrieval_rank", 0) or 0),
            "audit_log_hash": str(item.get("audit_log_hash", "")),
            "authorized": item.get("authorized") is True,
            "public_proof_hash": str(item.get("public_proof_hash", "")),
        }
        row["ready"] = (
            bool(row["context_id"])
            and bool(row["protocol"])
            and bool(row["source_label"])
            and row["source_label"] == row["footer_source_label"]
            and bool(row["creator_id"])
            and bool(row["work_id"])
            and bool(row["access_event_hash"])
            and bool(row["license_token_hash"])
            and row["rights_state"] in ALLOWED_RIGHTS_STATES
            and row["consent_state"] == "active"
            and row["lease_state"] == "fresh"
            and bool(row["claim_span_hash"])
            and bool(row["agent_step_id"])
            and bool(row["audit_log_hash"])
            and row["authorized"]
            and _as_decimal(row["royalty_share"]) > Decimal("0")
            and bool(row["public_proof_hash"])
        )
        row["context_access_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _agent_step_rows(
    bridge_input: dict[str, Any], context_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    context_hashes = {row["context_access_row_hash"] for row in context_rows}
    response_hash = _declared_hash(bridge_input.get("response_envelope", {}))
    rendered_hash = str(
        bridge_input.get("response_envelope", {})
        .get("response", {})
        .get("rendered_output_hash", "")
    )
    rows = []
    for item in sorted(
        bridge_input.get("agent_step_rows", []),
        key=lambda row: (int(row.get("sequence", 0) or 0), str(row.get("step_id", ""))),
    ):
        if not isinstance(item, dict):
            continue
        access_hashes = sorted(
            {str(value) for value in item.get("context_access_hashes", []) if value}
        )
        source_labels = sorted(
            {str(value) for value in item.get("source_labels", []) if value}
        )
        row = {
            "step_id": str(item.get("step_id", "")),
            "sequence": int(item.get("sequence", 0) or 0),
            "step_type": str(item.get("step_type", "")),
            "protocol": str(item.get("protocol", "")),
            "context_access_hashes": access_hashes,
            "source_labels": source_labels,
            "tool_result_hash": str(item.get("tool_result_hash", "")),
            "rendered_output_hash": str(item.get("rendered_output_hash", "")),
            "response_envelope_hash": str(item.get("response_envelope_hash", response_hash)),
            "hallucination_risk_control": str(item.get("hallucination_risk_control", "")),
            "decision": str(item.get("decision", "")),
            "status": str(item.get("status", "")),
        }
        row["ready"] = (
            bool(row["step_id"])
            and bool(row["step_type"])
            and bool(row["protocol"])
            and bool(access_hashes)
            and set(access_hashes) <= context_hashes
            and bool(source_labels)
            and bool(row["tool_result_hash"])
            and row["rendered_output_hash"] == rendered_hash
            and row["response_envelope_hash"] == response_hash
            and row["hallucination_risk_control"] == "cite_only_bound_context"
            and row["decision"] == "use_with_attribution"
            and row["status"] == "passed"
        )
        row["agent_step_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _royalty_projection_rows(
    bridge_input: dict[str, Any], context_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    context_hash_by_label = {
        row["source_label"]: row["context_access_row_hash"] for row in context_rows
    }
    rows = []
    for item in sorted(
        bridge_input.get("royalty_projection_rows", []),
        key=lambda row: (str(row.get("source_label", "")), str(row.get("creator_id", ""))),
    ):
        if not isinstance(item, dict):
            continue
        source_label = str(item.get("source_label", ""))
        context_hashes = sorted(
            {str(value) for value in item.get("context_access_hashes", []) if value}
        )
        row = {
            "source_label": source_label,
            "creator_id": str(item.get("creator_id", "")),
            "work_id": str(item.get("work_id", "")),
            "context_access_hashes": context_hashes,
            "royalty_event_hash": str(item.get("royalty_event_hash", "")),
            "settlement_state": str(item.get("settlement_state", "")),
            "share": str(item.get("share", "0")),
            "settlement_sink": str(item.get("settlement_sink", "")),
        }
        row["ready"] = (
            bool(row["source_label"])
            and bool(row["creator_id"])
            and bool(row["work_id"])
            and bool(context_hashes)
            and context_hash_by_label.get(source_label) in context_hashes
            and bool(row["royalty_event_hash"])
            and row["settlement_state"] in {"direct", "licensed", "escrow"}
            and _as_decimal(row["share"]) > Decimal("0")
            and bool(row["settlement_sink"])
        )
        row["royalty_projection_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _failure_case_rows(
    bridge_input: dict[str, Any], required_cases: list[str]
) -> list[dict[str, Any]]:
    case_map = _component_input_map(bridge_input, "failure_case_rows")
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
            and bool(row["verifier_command"])
            and row["expected_block"]
            and row["observed_block"]
        )
        row["failure_case_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _verifier_command_rows(
    bridge_input: dict[str, Any], required_commands: list[str]
) -> list[dict[str, Any]]:
    integration = bridge_input.get("integration_profile", {})
    declared = set(
        integration.get("verifier_contract", {}).get("reference_cli_commands", [])
    ) | {str(command) for command in bridge_input.get("verifier_commands", [])}
    rows = []
    for command in sorted(required_commands):
        row = {
            "command": command,
            "declared": command in declared,
            "required": True,
        }
        row["verifier_command_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def make_universal_context_provenance_bridge(
    bridge_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L140 universal context provenance bridge report."""

    created_at = created_at or now_iso()
    policy = _policy(bridge_input)
    required_artifacts = [str(name) for name in policy["required_core_artifacts"]]
    required_protocols = [str(name) for name in policy["required_context_protocols"]]
    required_surfaces = [str(name) for name in policy["required_bridge_surfaces"]]
    required_mappings = [str(name) for name in policy["required_standards_mappings"]]
    required_cases = [str(name) for name in policy["required_failure_cases"]]
    required_commands = [str(name) for name in policy["required_verifier_commands"]]

    interop_kit = bridge_input.get("universal_interop_test_kit", {})
    certification = bridge_input.get("certification_report", {})
    discovery = bridge_input.get("discovery_manifest", {})
    integration = bridge_input.get("integration_profile", {})
    source_footer_delivery = bridge_input.get("source_footer_delivery", {})
    response_envelope = bridge_input.get("response_envelope", {})

    artifact_bindings = _artifact_bindings(bridge_input, required_artifacts)
    bridge_surface_rows = _bridge_surface_rows(bridge_input, required_surfaces)
    protocol_adapter_rows = _protocol_adapter_rows(bridge_input, required_protocols)
    standards_mapping_rows = _standards_mapping_rows(bridge_input, required_mappings)
    context_access_rows = _context_access_rows(bridge_input)
    agent_step_rows = _agent_step_rows(bridge_input, context_access_rows)
    royalty_projection_rows = _royalty_projection_rows(bridge_input, context_access_rows)
    failure_case_rows = _failure_case_rows(bridge_input, required_cases)
    verifier_command_rows = _verifier_command_rows(bridge_input, required_commands)

    footer_labels = _source_labels_from_footer(source_footer_delivery)
    response_labels = _source_labels_from_response(response_envelope)
    visible_labels = footer_labels | response_labels
    context_labels = {row["source_label"] for row in context_access_rows}
    agent_labels = {label for row in agent_step_rows for label in row["source_labels"]}
    royalty_labels = {row["source_label"] for row in royalty_projection_rows}
    denied_rows = [
        row
        for row in bridge_input.get("context_access_rows", [])
        if isinstance(row, dict) and str(row.get("rights_state", "")) in DENIED_RIGHTS_STATES
    ]

    public_projection = {
        "artifact_bindings": artifact_bindings,
        "bridge_surface_rows": bridge_surface_rows,
        "protocol_adapter_rows": protocol_adapter_rows,
        "standards_mapping_rows": standards_mapping_rows,
        "context_access_rows": context_access_rows,
        "agent_step_rows": agent_step_rows,
        "royalty_projection_rows": royalty_projection_rows,
        "failure_case_rows": failure_case_rows,
        "verifier_command_rows": verifier_command_rows,
    }
    private_findings = _contains_private_fields(public_projection)
    discovery_path = discovery.get("discovery", {}).get(
        "universal_context_provenance_bridge_path"
    )

    checks = {
        "required_core_artifacts_present": all(
            row["present"] for row in artifact_bindings["bindings"]
        ),
        "artifact_hashes_reproducible": all(
            row["hash_reproducible"] for row in artifact_bindings["bindings"]
        ),
        "certification_level_at_least_l139": (
            _summary(certification).get("status") == "passed"
            and _level_at_least(_summary(certification).get("highest_level", ""), "RDLLM-L139")
        ),
        "universal_interop_kit_ready_l139": (
            _artifact_status(interop_kit) == "ready"
            and _artifact_target_level(interop_kit) == "RDLLM-L139"
            and _summary(interop_kit).get("offline_verification_supported") is True
            and _summary(interop_kit).get("privacy_preserved") is True
        ),
        "bridge_surfaces_complete": all(row["ready"] for row in bridge_surface_rows),
        "protocol_adapter_coverage_complete": all(
            row["ready"] for row in protocol_adapter_rows
        ),
        "standards_mappings_complete": all(
            row["ready"] for row in standards_mapping_rows
        ),
        "context_access_events_authorized_and_licensed": bool(context_access_rows)
        and all(row["ready"] for row in context_access_rows),
        "context_claims_project_to_visible_footers": bool(context_labels)
        and context_labels <= visible_labels,
        "agent_steps_bind_context_and_response": bool(agent_step_rows)
        and all(row["ready"] for row in agent_step_rows)
        and agent_labels <= context_labels,
        "royalty_events_cover_context_sources": bool(royalty_projection_rows)
        and context_labels <= royalty_labels
        and all(row["ready"] for row in royalty_projection_rows),
        "denied_context_cases_fail_closed": all(
            not row.get("authorized", False) for row in denied_rows
        )
        and any(row["case_id"] == "rights_denied_context" and row["passed"] for row in failure_case_rows),
        "public_verifier_commands_declared": all(
            row["declared"] for row in verifier_command_rows
        ),
        "discovery_manifest_exposes_bridge_path": discovery_path == DEFAULT_WELL_KNOWN_PATH,
        "offline_verification_supported": (
            integration.get("verifier_contract", {}).get(
                "offline_verification_supported"
            )
            is True
            and _summary(interop_kit).get("offline_verification_supported") is True
        ),
        "public_report_has_no_private_field_names": not private_findings,
    }
    checks["private_strings_absent"] = _private_strings_absent(
        public_projection,
        bridge_input,
    )

    failed_checks = [name for name, passed in checks.items() if passed is not True]
    failure_modes_by_check = {
        "required_core_artifacts_present": "required_context_bridge_artifact_missing",
        "artifact_hashes_reproducible": "context_bridge_artifact_hash_not_reproducible",
        "certification_level_at_least_l139": "certification_level_too_low",
        "universal_interop_kit_ready_l139": "interop_kit_missing_or_blocked",
        "bridge_surfaces_complete": "context_bridge_surface_missing",
        "protocol_adapter_coverage_complete": "context_protocol_adapter_gap",
        "standards_mappings_complete": "context_standards_mapping_gap",
        "context_access_events_authorized_and_licensed": "context_access_not_authorized_or_licensed",
        "context_claims_project_to_visible_footers": "context_source_not_visible_in_footer",
        "agent_steps_bind_context_and_response": "agent_step_context_binding_gap",
        "royalty_events_cover_context_sources": "context_royalty_projection_gap",
        "denied_context_cases_fail_closed": "denied_context_not_fail_closed",
        "public_verifier_commands_declared": "context_bridge_verifier_command_missing",
        "discovery_manifest_exposes_bridge_path": "discovery_context_bridge_path_missing",
        "offline_verification_supported": "offline_context_bridge_verification_not_supported",
        "public_report_has_no_private_field_names": "private_field_name_leak",
        "private_strings_absent": "private_string_leak",
    }
    failure_modes = [failure_modes_by_check[name] for name in failed_checks]
    ready = not failed_checks

    commitments = {
        "artifact_binding_root": artifact_bindings["artifact_binding_root"],
        "bridge_surface_root": merkle_root(
            [row["bridge_surface_row_hash"] for row in bridge_surface_rows]
        ),
        "protocol_adapter_root": merkle_root(
            [row["protocol_adapter_row_hash"] for row in protocol_adapter_rows]
        ),
        "standards_mapping_root": merkle_root(
            [row["standards_mapping_row_hash"] for row in standards_mapping_rows]
        ),
        "context_access_root": merkle_root(
            [row["context_access_row_hash"] for row in context_access_rows]
        ),
        "agent_step_root": merkle_root(
            [row["agent_step_row_hash"] for row in agent_step_rows]
        ),
        "royalty_projection_root": merkle_root(
            [row["royalty_projection_row_hash"] for row in royalty_projection_rows]
        ),
        "failure_case_root": merkle_root(
            [row["failure_case_row_hash"] for row in failure_case_rows]
        ),
        "verifier_command_root": merkle_root(
            [row["verifier_command_row_hash"] for row in verifier_command_rows]
        ),
        "universal_interop_test_kit_hash": _declared_hash(interop_kit),
        "certification_report_hash": _declared_hash(certification),
        "source_footer_delivery_hash": _declared_hash(source_footer_delivery),
        "response_envelope_hash": _declared_hash(response_envelope),
    }
    commitments["context_bridge_commitment_hash"] = hash_payload(commitments)

    report: dict[str, Any] = {
        "context_bridge_version": UNIVERSAL_CONTEXT_PROVENANCE_BRIDGE_VERSION,
        "issuer": issuer,
        "created_at": created_at,
        "bridge_policy": policy,
        "artifact_bindings": artifact_bindings,
        "bridge_surface_rows": bridge_surface_rows,
        "protocol_adapter_rows": protocol_adapter_rows,
        "standards_mapping_rows": standards_mapping_rows,
        "context_access_rows": context_access_rows,
        "agent_step_rows": agent_step_rows,
        "royalty_projection_rows": royalty_projection_rows,
        "failure_case_rows": failure_case_rows,
        "verifier_command_rows": verifier_command_rows,
        "commitments": commitments,
        "checks": checks,
        "bridge_decision": {
            "decision": "publish_universal_context_provenance_bridge"
            if ready
            else "block_universal_context_provenance_bridge",
            "publication_authorized": ready,
            "runtime_context_access_authorized": ready,
            "agent_response_release_approved": ready,
            "failed_checks": failed_checks,
            "failure_modes": failure_modes,
            "safe_output_policy": "publish_l140_context_bridge_and_require_context_bound_footers"
            if ready
            else "block_context_bridge_publication",
        },
        "schemas": {
            "universal_context_provenance_bridge": UNIVERSAL_CONTEXT_PROVENANCE_BRIDGE_SCHEMA,
            "universal_interop_test_kit": "docs/schemas/universal_interop_test_kit.schema.json",
            "universal_adoption_standard": "docs/schemas/universal_adoption_standard.schema.json",
            "integration_profile": "docs/schemas/integration_profile.schema.json",
            "discovery_manifest": "docs/schemas/discovery_manifest.schema.json",
            "source_footer_delivery": "docs/schemas/source_footer_delivery.schema.json",
            "response_envelope": "docs/schemas/response_envelope.schema.json",
        },
        "privacy": {
            "raw_context_text_disclosed": False,
            "raw_tool_result_disclosed": False,
            "raw_prompt_text_disclosed": False,
            "raw_output_text_disclosed": False,
            "raw_token_or_secret_disclosed": False,
            "hash_only_context_bindings": True,
            "private_field_findings": private_findings,
            "private_strings_absent": checks["private_strings_absent"],
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "context_protocol_count": len(protocol_adapter_rows),
            "bridge_surface_count": len(bridge_surface_rows),
            "standards_mapping_count": len(standards_mapping_rows),
            "context_access_count": len(context_access_rows),
            "agent_step_count": len(agent_step_rows),
            "royalty_projection_count": len(royalty_projection_rows),
            "failure_case_count": len(failure_case_rows),
            "verifier_command_count": len(verifier_command_rows),
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
            "offline_verification_supported": checks[
                "offline_verification_supported"
            ],
            "privacy_preserved": not private_findings
            and checks["private_strings_absent"] is True,
            "universal_interop_test_kit_hash": _declared_hash(interop_kit),
            "context_bridge_commitment_hash": commitments[
                "context_bridge_commitment_hash"
            ],
        },
    }
    report["universal_context_provenance_bridge_hash"] = hash_payload(
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


def validate_universal_context_provenance_bridge_shape(
    report: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    required = (
        "context_bridge_version",
        "issuer",
        "created_at",
        "bridge_policy",
        "artifact_bindings",
        "bridge_surface_rows",
        "protocol_adapter_rows",
        "standards_mapping_rows",
        "context_access_rows",
        "agent_step_rows",
        "royalty_projection_rows",
        "failure_case_rows",
        "verifier_command_rows",
        "commitments",
        "checks",
        "bridge_decision",
        "schemas",
        "privacy",
        "summary",
        "universal_context_provenance_bridge_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing universal context provenance bridge field: {key}")
    if errors:
        return errors
    if report.get("context_bridge_version") != UNIVERSAL_CONTEXT_PROVENANCE_BRIDGE_VERSION:
        errors.append("universal context provenance bridge version is unsupported")
    if (
        report.get("schemas", {}).get("universal_context_provenance_bridge")
        != UNIVERSAL_CONTEXT_PROVENANCE_BRIDGE_SCHEMA
    ):
        errors.append("universal context provenance bridge schema path is not declared")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal context provenance bridge target level is not RDLLM-L140")
    for finding in _contains_private_fields(report):
        errors.append(f"universal context provenance bridge contains private field: {finding}")
    return errors


def verify_universal_context_provenance_bridge(
    report: dict[str, Any],
    *,
    bridge_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L140 universal context provenance bridge by replaying inputs."""

    errors = validate_universal_context_provenance_bridge_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("universal_context_provenance_bridge_hash"):
        errors.append("universal context provenance bridge hash is not reproducible")

    expected = make_universal_context_provenance_bridge(
        bridge_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "bridge_policy",
        "artifact_bindings",
        "bridge_surface_rows",
        "protocol_adapter_rows",
        "standards_mapping_rows",
        "context_access_rows",
        "agent_step_rows",
        "royalty_projection_rows",
        "failure_case_rows",
        "verifier_command_rows",
        "commitments",
        "checks",
        "bridge_decision",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"universal context provenance bridge {key} does not match replay")
    if expected.get("universal_context_provenance_bridge_hash") != report.get(
        "universal_context_provenance_bridge_hash"
    ):
        errors.append("universal context provenance bridge hash does not match replay")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("universal context provenance bridge status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal context provenance bridge check failed: {check}")

    if not _private_strings_absent(report, bridge_input):
        errors.append("universal context provenance bridge leaks a private input string")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("universal context provenance bridge is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("universal context provenance bridge signature is invalid")

    return errors
