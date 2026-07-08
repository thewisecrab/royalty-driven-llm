"""Universal accountability audit trails.

The L152 layer closes the gap between provider-wire provenance and organizational
accountability. It binds provider calls, agent/tool actions, memory updates,
governance approvals, policy versions, exported copies, and settlement meters
into one append-only audit trail before a deployment can claim that attribution
and royalty decisions are reconstructable by an auditor.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)
from rdllm.transparency import merkle_root

UNIVERSAL_ACCOUNTABILITY_AUDIT_TRAIL_VERSION = (
    "rdllm-universal-accountability-audit-trail/v1"
)
UNIVERSAL_ACCOUNTABILITY_AUDIT_TRAIL_SCHEMA = (
    "docs/schemas/universal_accountability_audit_trail.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L152"
MINIMUM_PROVIDER_WIRE_LEVEL = "RDLLM-L151"
MINIMUM_CLAIM_PROVENANCE_LEVEL = "RDLLM-L150"
MINIMUM_RUNTIME_LEVEL = "RDLLM-L149"
MINIMUM_AUTHORITY_LEVEL = "RDLLM-L145"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-accountability-audit-trail.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "assurance_bundle",
    "proof_dependency_graph",
    "universal_provider_wire_protocol",
    "universal_claim_provenance_envelope",
    "universal_runtime_conformance_receipt",
    "universal_attribution_authority_control_plane",
    "universal_composite_rdllm_profile",
    "universal_emission_enforcement_gateway",
    "universal_rdllm_root",
    "foundation_runtime_adapter",
    "foundation_runtime_router",
    "foundation_model_deployment_attestation",
    "agent_tool_attribution_ledger",
    "conversation_attribution_ledger",
    "source_footer_delivery",
    "client_attribution_enforcement",
    "response_envelope",
    "proof_carrying_response",
    "serving_gateway_report",
    "revenue_allocation_report",
    "finance_ledger_attestation",
    "trust_registry",
)

REQUIRED_AUDIT_EVENT_TYPES = (
    "governance_approval",
    "policy_version_binding",
    "actor_delegation",
    "context_ingestion",
    "source_access",
    "retrieval_or_search",
    "memory_read",
    "memory_write",
    "agent_tool_call",
    "model_invocation",
    "provider_wire_call",
    "claim_generation",
    "footer_render",
    "proxy_or_gateway_transform",
    "batch_callback",
    "webhook_delivery",
    "export_copy",
    "settlement_meter",
    "challenge_or_correction",
    "revocation_or_intervention",
)

REQUIRED_ACTOR_ROLES = (
    "end_user",
    "enterprise_admin",
    "application_provider",
    "agent_runtime",
    "tool_provider",
    "retrieval_provider",
    "memory_store",
    "model_gateway",
    "foundation_provider",
    "settlement_operator",
    "independent_auditor",
    "regulator",
)

REQUIRED_GOVERNANCE_RECORDS = (
    "model_release_approval",
    "policy_version_approval",
    "rights_policy_waiver",
    "tool_scope_approval",
    "memory_scope_approval",
    "provider_route_approval",
    "export_policy_approval",
    "settlement_policy_approval",
    "auditor_access_grant",
    "incident_or_challenge_review",
)

REQUIRED_INTEGRITY_CONTROLS = (
    "append_only_event_chain",
    "cross_organization_trace_export",
    "policy_version_replay",
    "actor_identity_attestation",
    "delegation_contract_binding",
    "tool_action_causal_attribution",
    "memory_write_lineage",
    "provider_wire_replay",
    "auditor_redaction_log",
    "split_view_detection",
)

REQUIRED_FAILURE_CASES = (
    "missing_previous_event_hash",
    "non_monotonic_event_sequence",
    "missing_actor_authority",
    "missing_policy_version",
    "unbound_l151_provider_call",
    "tool_call_without_causal_attribution",
    "memory_write_without_source_lineage",
    "source_access_without_license_scope",
    "export_copy_without_footer_proof",
    "settlement_without_audit_event",
    "governance_waiver_without_attestation",
    "split_view_audit_log",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_accountability_audit_trail_hash",
    "universal_provider_wire_protocol_hash",
    "universal_claim_provenance_envelope_hash",
    "universal_runtime_conformance_receipt_hash",
    "universal_attribution_authority_control_plane_hash",
    "universal_composite_rdllm_profile_hash",
    "universal_emission_enforcement_gateway_hash",
    "universal_rdllm_root_hash",
    "foundation_model_deployment_attestation_hash",
    "foundation_runtime_router_hash",
    "foundation_runtime_adapter_hash",
    "source_footer_delivery_hash",
    "client_enforcement_hash",
    "conversation_ledger_hash",
    "tool_ledger_hash",
    "trust_registry_hash",
    "attestation_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "graph_hash",
    "report_hash",
    "bundle_hash",
    "summary_hash",
    "contract_hash",
    "receipt_hash",
    "gateway_report_hash",
    "proof_response_hash",
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
    "raw_native_request",
    "raw_native_response",
    "authorization",
    "access_token",
    "api_key",
    "secret",
    "signing_secret",
    "private_key",
    "customer_id",
    "customer_email",
    "billing_record",
    "bank_account",
    "tax_id",
}


def load_universal_accountability_audit_trail_input(path: str | Path) -> dict[str, Any]:
    """Load private replay input for an L152 accountability audit trail."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_trail(trail: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in trail.items()
        if key not in {"universal_accountability_audit_trail_hash", "signature"}
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
    if artifact.get("receipt_hash") and isinstance(artifact.get("payload"), dict):
        return artifact["receipt_hash"] == hash_payload(artifact["payload"])
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
    public_payload: dict[str, Any], audit_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in audit_input.get("private_strings", [])
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


def _component_input_map(audit_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    value = audit_input.get(key, {})
    if isinstance(value, dict):
        return {str(name): row for name, row in value.items() if isinstance(row, dict)}
    if isinstance(value, list):
        result: dict[str, dict[str, Any]] = {}
        for row in value:
            if not isinstance(row, dict):
                continue
            name = (
                row.get("event_type")
                or row.get("record_type")
                or row.get("control")
                or row.get("case_id")
            )
            if name:
                result[str(name)] = row
        return result
    return {}


def _policy(audit_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(audit_input.get("accountability_audit_policy", {}))
    return {
        "profile": "rdllm-universal-accountability-audit-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_provider_wire_level": MINIMUM_PROVIDER_WIRE_LEVEL,
        "minimum_claim_provenance_level": MINIMUM_CLAIM_PROVENANCE_LEVEL,
        "minimum_runtime_level": MINIMUM_RUNTIME_LEVEL,
        "minimum_authority_level": MINIMUM_AUTHORITY_LEVEL,
        "well_known_path": DEFAULT_WELL_KNOWN_PATH,
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_audit_event_types": list(
            policy.get("required_audit_event_types", REQUIRED_AUDIT_EVENT_TYPES)
        ),
        "required_actor_roles": list(
            policy.get("required_actor_roles", REQUIRED_ACTOR_ROLES)
        ),
        "required_governance_records": list(
            policy.get("required_governance_records", REQUIRED_GOVERNANCE_RECORDS)
        ),
        "required_integrity_controls": list(
            policy.get("required_integrity_controls", REQUIRED_INTEGRITY_CONTROLS)
        ),
        "required_failure_cases": list(
            policy.get("required_failure_cases", REQUIRED_FAILURE_CASES)
        ),
        "audit_rule": "every_attribution_relevant_decision_must_be_append_only_and_replayable",
        "governance_rule": "approvals_waivers_policy_versions_and_attestations_must_bind_to_provider_wire_events",
        "agent_rule": "tool_memory_and_delegation_events_require_causal_attribution_and_authority",
        "privacy_rule": "public_audit_trail_contains_hashes_roles_and_commitments_not_raw_payloads",
    }


def _artifact_bindings(audit_input: dict[str, Any], names: list[str]) -> dict[str, Any]:
    rows = []
    for name in names:
        artifact = audit_input.get(name)
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


def _binding_by_name(artifact_bindings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("name", "")): row
        for row in artifact_bindings.get("bindings", [])
        if isinstance(row, dict)
    }


def _audit_event_rows(
    audit_input: dict[str, Any],
    required_event_types: list[str],
    required_actor_roles: list[str],
) -> list[dict[str, Any]]:
    row_map = _component_input_map(audit_input, "audit_event_rows")
    prev = hash_payload("rdllm-accountability-audit-trail-genesis")
    rows = []
    for index, event_type in enumerate(required_event_types):
        item = row_map.get(event_type, {})
        actor_role = str(item.get("actor_role", ""))
        previous_event_hash = str(item.get("previous_event_hash", prev))
        row = {
            "event_type": event_type,
            "event_sequence": int(item.get("event_sequence", index) or 0),
            "previous_event_hash": previous_event_hash,
            "expected_previous_event_hash": prev,
            "actor_role": actor_role,
            "actor_hash": str(item.get("actor_hash", "")),
            "subject_hash": str(item.get("subject_hash", "")),
            "timestamp_commitment_hash": str(
                item.get("timestamp_commitment_hash", "")
            ),
            "policy_version_hash": str(item.get("policy_version_hash", "")),
            "authority_receipt_hash": str(item.get("authority_receipt_hash", "")),
            "l151_protocol_hash": str(item.get("l151_protocol_hash", "")),
            "l150_envelope_hash": str(item.get("l150_envelope_hash", "")),
            "source_or_tool_trace_hash": str(
                item.get("source_or_tool_trace_hash", "")
            ),
            "telemetry_span_hash": str(item.get("telemetry_span_hash", "")),
            "governance_record_hash": str(item.get("governance_record_hash", "")),
            "settlement_meter_hash": str(item.get("settlement_meter_hash", "")),
            "append_only_linked": item.get("append_only_linked") is True,
            "actor_authorized": item.get("actor_authorized") is True,
            "policy_bound": item.get("policy_bound") is True,
            "provenance_bound": item.get("provenance_bound") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
        }
        row["chain_contiguous"] = previous_event_hash == prev
        row["sequence_monotonic"] = row["event_sequence"] == index
        row["ready"] = (
            row["chain_contiguous"]
            and row["sequence_monotonic"]
            and actor_role in required_actor_roles
            and bool(row["actor_hash"])
            and bool(row["subject_hash"])
            and bool(row["timestamp_commitment_hash"])
            and bool(row["policy_version_hash"])
            and bool(row["authority_receipt_hash"])
            and bool(row["l151_protocol_hash"])
            and bool(row["l150_envelope_hash"])
            and bool(row["source_or_tool_trace_hash"])
            and bool(row["telemetry_span_hash"])
            and bool(row["governance_record_hash"])
            and bool(row["settlement_meter_hash"])
            and row["append_only_linked"]
            and row["actor_authorized"]
            and row["policy_bound"]
            and row["provenance_bound"]
            and row["privacy_preserving"]
        )
        row["audit_event_row_hash"] = hash_payload(row)
        prev = row["audit_event_row_hash"]
        rows.append(row)
    return rows


def _governance_record_rows(
    audit_input: dict[str, Any], required_records: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(audit_input, "governance_record_rows")
    rows = []
    for record_type in sorted(required_records):
        item = row_map.get(record_type, {})
        row = {
            "record_type": record_type,
            "record_hash": str(item.get("record_hash", "")),
            "approver_hash": str(item.get("approver_hash", "")),
            "policy_version_hash": str(item.get("policy_version_hash", "")),
            "attestation_hash": str(item.get("attestation_hash", "")),
            "l151_protocol_hash": str(item.get("l151_protocol_hash", "")),
            "auditor_export_hash": str(item.get("auditor_export_hash", "")),
            "required": item.get("required") is True,
            "approved_or_recorded": item.get("approved_or_recorded") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
        }
        row["ready"] = (
            bool(row["record_hash"])
            and bool(row["approver_hash"])
            and bool(row["policy_version_hash"])
            and bool(row["attestation_hash"])
            and bool(row["l151_protocol_hash"])
            and bool(row["auditor_export_hash"])
            and row["required"]
            and row["approved_or_recorded"]
            and row["privacy_preserving"]
        )
        row["governance_record_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _integrity_control_rows(
    audit_input: dict[str, Any], required_controls: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(audit_input, "integrity_control_rows")
    rows = []
    for control in sorted(required_controls):
        item = row_map.get(control, {})
        row = {
            "control": control,
            "control_evidence_hash": str(item.get("control_evidence_hash", "")),
            "verifier_hash": str(item.get("verifier_hash", "")),
            "auditor_export_hash": str(item.get("auditor_export_hash", "")),
            "failure_action": str(item.get("failure_action", "")),
            "implemented": item.get("implemented") is True,
            "fail_closed": item.get("fail_closed") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
        }
        row["ready"] = (
            bool(row["control_evidence_hash"])
            and bool(row["verifier_hash"])
            and bool(row["auditor_export_hash"])
            and row["failure_action"] == "block_grounded_display_and_settlement"
            and row["implemented"]
            and row["fail_closed"]
            and row["privacy_preserving"]
        )
        row["integrity_control_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _failure_case_rows(
    audit_input: dict[str, Any], required_cases: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(audit_input, "failure_case_rows")
    rows = []
    for case_id in sorted(required_cases):
        item = row_map.get(case_id, {})
        row = {
            "case_id": case_id,
            "fixture_hash": str(item.get("fixture_hash", "")),
            "verifier_command": str(item.get("verifier_command", "")),
            "expected_block": item.get("expected_block") is True,
            "observed_block": item.get("observed_block") is True,
        }
        row["ready"] = (
            bool(row["fixture_hash"])
            and row["verifier_command"] == "verify-universal-accountability-audit-trail"
            and row["expected_block"]
            and row["observed_block"]
        )
        row["failure_case_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _all_ready(rows: list[dict[str, Any]]) -> bool:
    return bool(rows) and all(row.get("ready") is True for row in rows)


def _count(rows: list[dict[str, Any]], key: str = "ready") -> int:
    return sum(1 for row in rows if row.get(key) is True)


def _artifact_summary(audit_input: dict[str, Any], name: str) -> dict[str, Any]:
    artifact = audit_input.get(name)
    return _summary(artifact if isinstance(artifact, dict) else None)


def make_universal_accountability_audit_trail(
    audit_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create the L152 universal accountability audit trail."""

    policy = _policy(audit_input)
    required_artifacts = list(policy["required_core_artifacts"])
    artifact_bindings = _artifact_bindings(audit_input, required_artifacts)
    bindings = _binding_by_name(artifact_bindings)
    audit_rows = _audit_event_rows(
        audit_input,
        list(policy["required_audit_event_types"]),
        list(policy["required_actor_roles"]),
    )
    governance_rows = _governance_record_rows(
        audit_input, list(policy["required_governance_records"])
    )
    integrity_rows = _integrity_control_rows(
        audit_input, list(policy["required_integrity_controls"])
    )
    failure_rows = _failure_case_rows(
        audit_input, list(policy["required_failure_cases"])
    )

    certification_summary = _artifact_summary(audit_input, "certification_report")
    l151_summary = _artifact_summary(audit_input, "universal_provider_wire_protocol")
    l150_summary = _artifact_summary(
        audit_input, "universal_claim_provenance_envelope"
    )
    l149_summary = _artifact_summary(
        audit_input, "universal_runtime_conformance_receipt"
    )
    authority_summary = _artifact_summary(
        audit_input, "universal_attribution_authority_control_plane"
    )
    proof_graph_summary = _artifact_summary(audit_input, "proof_dependency_graph")

    provider_card = audit_input.get("provider_attribution_card", {})
    integration_profile = audit_input.get("integration_profile", {})
    discovery_manifest = audit_input.get("discovery_manifest", {})
    public_surfaces = {}
    if isinstance(provider_card, dict):
        public_surfaces.update(provider_card.get("public_disclosure_surfaces", {}))
    if isinstance(integration_profile, dict):
        public_surfaces.update(integration_profile.get("public_surfaces", {}))
    discovery = (
        discovery_manifest.get("discovery", {})
        if isinstance(discovery_manifest, dict)
        else {}
    )

    actor_role_coverage = {
        role: any(row.get("actor_role") == role and row.get("ready") for row in audit_rows)
        for role in policy["required_actor_roles"]
    }
    public_projection = {
        "artifact_bindings": artifact_bindings,
        "audit_event_rows": audit_rows,
        "governance_record_rows": governance_rows,
        "integrity_control_rows": integrity_rows,
        "failure_case_rows": failure_rows,
    }
    private_findings = _contains_private_fields(public_projection)

    checks = {
        "all_required_artifacts_present": all(
            bindings.get(name, {}).get("present") is True for name in required_artifacts
        ),
        "all_required_artifact_hashes_reproducible": all(
            bindings.get(name, {}).get("hash_reproducible") is True
            for name in required_artifacts
        ),
        "certification_passed_l151_or_higher": (
            certification_summary.get("status") == "passed"
            and _level_at_least(
                certification_summary.get("highest_level"),
                MINIMUM_PROVIDER_WIRE_LEVEL,
            )
        ),
        "provider_wire_ready_l151": (
            l151_summary.get("status") == "ready"
            and _level_at_least(
                l151_summary.get("target_certification_level"),
                MINIMUM_PROVIDER_WIRE_LEVEL,
            )
            and int(l151_summary.get("failed_check_count", 0) or 0) == 0
        ),
        "claim_provenance_ready_l150": (
            l150_summary.get("status") == "ready"
            and _level_at_least(
                l150_summary.get("target_certification_level"),
                MINIMUM_CLAIM_PROVENANCE_LEVEL,
            )
            and int(l150_summary.get("failed_check_count", 0) or 0) == 0
        ),
        "runtime_conformance_ready_l149": (
            l149_summary.get("status") == "ready"
            and _level_at_least(
                l149_summary.get("target_certification_level"), MINIMUM_RUNTIME_LEVEL
            )
            and int(l149_summary.get("failed_check_count", 0) or 0) == 0
        ),
        "authority_control_ready_l145": (
            authority_summary.get("status") == "ready"
            and _level_at_least(
                authority_summary.get("target_certification_level"),
                MINIMUM_AUTHORITY_LEVEL,
            )
        ),
        "all_audit_events_ready": _all_ready(audit_rows),
        "all_required_actor_roles_covered": all(actor_role_coverage.values()),
        "all_governance_records_ready": _all_ready(governance_rows),
        "all_integrity_controls_ready": _all_ready(integrity_rows),
        "all_failure_cases_prove_blocking": _all_ready(failure_rows),
        "audit_trail_publication_declared": (
            public_surfaces.get("universal_accountability_audit_trail") is True
            or discovery.get("universal_accountability_audit_trail_path")
            == DEFAULT_WELL_KNOWN_PATH
        ),
        "proof_graph_acyclic": (
            int(proof_graph_summary.get("cycle_node_count", 0) or 0) == 0
            and proof_graph_summary.get("status") in {"ready", "ok"}
        ),
        "privacy_preserved": (
            not private_findings and _private_strings_absent(public_projection, audit_input)
        ),
    }
    failed_checks = [name for name, passed in checks.items() if passed is not True]
    failure_modes_by_check = {
        "all_required_artifacts_present": "accountability_required_artifact_missing",
        "all_required_artifact_hashes_reproducible": "accountability_artifact_hash_not_reproducible",
        "certification_passed_l151_or_higher": "accountability_certification_below_l151",
        "provider_wire_ready_l151": "accountability_l151_not_ready",
        "claim_provenance_ready_l150": "accountability_l150_not_ready",
        "runtime_conformance_ready_l149": "accountability_l149_not_ready",
        "authority_control_ready_l145": "accountability_l145_authority_not_ready",
        "all_audit_events_ready": "accountability_audit_event_gap",
        "all_required_actor_roles_covered": "accountability_actor_role_gap",
        "all_governance_records_ready": "accountability_governance_record_gap",
        "all_integrity_controls_ready": "accountability_integrity_control_gap",
        "all_failure_cases_prove_blocking": "accountability_negative_case_gap",
        "audit_trail_publication_declared": "accountability_publication_gap",
        "proof_graph_acyclic": "accountability_proof_graph_cycle",
        "privacy_preserved": "accountability_private_payload_leak",
    }
    failure_modes = [failure_modes_by_check[name] for name in failed_checks]
    ready = not failed_checks

    trail = {
        "audit_trail_version": UNIVERSAL_ACCOUNTABILITY_AUDIT_TRAIL_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "accountability_audit_policy": policy,
        "artifact_bindings": artifact_bindings,
        "audit_event_rows": audit_rows,
        "governance_record_rows": governance_rows,
        "integrity_control_rows": integrity_rows,
        "failure_case_rows": failure_rows,
        "evidence_commitments": {
            "artifact_binding_root": artifact_bindings["artifact_binding_root"],
            "audit_event_root": merkle_root(
                [row["audit_event_row_hash"] for row in audit_rows]
            ),
            "governance_record_root": merkle_root(
                [row["governance_record_row_hash"] for row in governance_rows]
            ),
            "integrity_control_root": merkle_root(
                [row["integrity_control_row_hash"] for row in integrity_rows]
            ),
            "failure_case_root": merkle_root(
                [row["failure_case_row_hash"] for row in failure_rows]
            ),
        },
        "checks": checks,
        "actor_role_coverage": actor_role_coverage,
        "audit_decision": {
            "universal_accountability_audit_authorized": ready,
            "provider_use_allowed": ready,
            "app_builder_integration_allowed": ready,
            "auditor_export_allowed": ready,
            "direct_creator_settlement_allowed": ready,
            "unverifiable_trace_allowed": False,
            "failure_modes": failure_modes,
        },
        "verifier_commands": [
            "verify-universal-accountability-audit-trail",
            "verify-universal-provider-wire-protocol",
            "verify-universal-claim-provenance-envelope",
            "verify-universal-runtime-conformance-receipt",
            "verify-universal-attribution-authority-control-plane",
            "verify-agent-tool-attribution-ledger",
            "verify-conversation-attribution-ledger",
            "verify-proof-dependency-graph",
        ],
        "research_controls": {
            "llm_audit_trails": "chronological_tamper_evident_lifecycle_events_and_governance_records",
            "action_level_causal_attribution": "tool_calls_require_intent_supported_causal_attribution",
            "agentic_prov": "agent_interactions_bind_to_end_to_end_workflow_provenance",
            "verifiable_inference_chain": "agent_computational_provenance_exports_are_hash_linked",
            "delegation_contracts": "delegated_agents_require_attested_identity_and_scope",
            "research_urls": {
                "audit_trails_for_llms": "https://arxiv.org/abs/2601.20727",
                "attriguard": "https://arxiv.org/abs/2603.10749",
                "prov_agent": "https://arxiv.org/abs/2508.02866",
                "ietf_spice_inference_chain": "https://www.ietf.org/archive/id/draft-mw-spice-inference-chain-00.html",
                "ldp_delegation_contracts": "https://arxiv.org/abs/2603.18043",
                "human_delegation_provenance": "https://arxiv.org/abs/2604.04522",
            },
        },
        "privacy": {
            "public_audit_contains_raw_prompts": False,
            "public_audit_contains_raw_outputs": False,
            "public_audit_contains_tool_payloads": False,
            "public_audit_contains_customer_or_payment_data": False,
            "hash_only_audit_commitments": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_provider_wire_level": MINIMUM_PROVIDER_WIRE_LEVEL,
            "minimum_claim_provenance_level": MINIMUM_CLAIM_PROVENANCE_LEVEL,
            "minimum_runtime_level": MINIMUM_RUNTIME_LEVEL,
            "minimum_authority_level": MINIMUM_AUTHORITY_LEVEL,
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
            "core_artifact_count": artifact_bindings["artifact_count"],
            "audit_event_count": len(audit_rows),
            "ready_audit_event_count": _count(audit_rows),
            "actor_role_count": len(actor_role_coverage),
            "covered_actor_role_count": sum(
                1 for covered in actor_role_coverage.values() if covered
            ),
            "governance_record_count": len(governance_rows),
            "ready_governance_record_count": _count(governance_rows),
            "integrity_control_count": len(integrity_rows),
            "ready_integrity_control_count": _count(integrity_rows),
            "failure_case_count": len(failure_rows),
            "offline_verification_supported": True,
            "privacy_preserved": checks["privacy_preserved"],
        },
    }
    trail["universal_accountability_audit_trail_hash"] = hash_payload(
        _hashable_trail(trail)
    )
    if signing_secret:
        trail["signature"] = sign_payload(_hashable_trail(trail), signing_secret)
    return trail


def validate_universal_accountability_audit_trail_shape(
    trail: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    required = (
        "audit_trail_version",
        "issuer",
        "created_at",
        "accountability_audit_policy",
        "artifact_bindings",
        "audit_event_rows",
        "governance_record_rows",
        "integrity_control_rows",
        "failure_case_rows",
        "evidence_commitments",
        "checks",
        "actor_role_coverage",
        "audit_decision",
        "verifier_commands",
        "research_controls",
        "privacy",
        "summary",
        "universal_accountability_audit_trail_hash",
    )
    for key in required:
        if key not in trail:
            errors.append(f"missing universal accountability audit trail field: {key}")
    if errors:
        return errors
    if trail.get("audit_trail_version") != UNIVERSAL_ACCOUNTABILITY_AUDIT_TRAIL_VERSION:
        errors.append("universal accountability audit trail version is unsupported")
    if trail.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal accountability audit trail target level is not RDLLM-L152")
    if (
        trail.get("accountability_audit_policy", {}).get("well_known_path")
        != DEFAULT_WELL_KNOWN_PATH
    ):
        errors.append("universal accountability audit trail well-known path is invalid")
    return errors


def verify_universal_accountability_audit_trail(
    trail: dict[str, Any],
    *,
    audit_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L152 accountability audit trail against private replay input."""

    errors = validate_universal_accountability_audit_trail_shape(trail)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_trail(trail))
    if expected_hash != trail.get("universal_accountability_audit_trail_hash"):
        errors.append("universal accountability audit trail hash is not reproducible")

    expected = make_universal_accountability_audit_trail(
        audit_input,
        issuer=trail.get("issuer", DEFAULT_ISSUER),
        created_at=trail.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "accountability_audit_policy",
        "artifact_bindings",
        "audit_event_rows",
        "governance_record_rows",
        "integrity_control_rows",
        "failure_case_rows",
        "evidence_commitments",
        "checks",
        "actor_role_coverage",
        "audit_decision",
        "verifier_commands",
        "research_controls",
        "privacy",
        "summary",
    ):
        if expected.get(key) != trail.get(key):
            errors.append(f"universal accountability audit trail {key} does not match replay input")
    if (
        expected.get("universal_accountability_audit_trail_hash")
        != trail.get("universal_accountability_audit_trail_hash")
    ):
        errors.append("universal accountability audit trail hash does not match replay input")
    if signing_secret and expected.get("signature") != trail.get("signature"):
        errors.append("universal accountability audit trail signature is invalid")
    if trail.get("summary", {}).get("status") != "ready":
        errors.append("universal accountability audit trail status is not ready")
    for check, passed in trail.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal accountability audit trail check failed: {check}")
    if _contains_private_fields(trail):
        errors.append("universal accountability audit trail exposes a private field")
    return errors
