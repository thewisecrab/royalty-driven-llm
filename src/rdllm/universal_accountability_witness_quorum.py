"""Universal accountability witness quorum.

The L153 layer prevents split-view accountability. L152 proves that a provider
can build an append-only audit trail; L153 proves that the same trail checkpoint
was published to transparency services and independently witnessed before users,
creators, auditors, or regulators rely on attribution or settlement claims.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_ACCOUNTABILITY_WITNESS_QUORUM_VERSION = (
    "rdllm-universal-accountability-witness-quorum/v1"
)
UNIVERSAL_ACCOUNTABILITY_WITNESS_QUORUM_SCHEMA = (
    "docs/schemas/universal_accountability_witness_quorum.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L153"
MINIMUM_ACCOUNTABILITY_LEVEL = "RDLLM-L152"
MINIMUM_PROVIDER_WIRE_LEVEL = "RDLLM-L151"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-accountability-witness-quorum.json"
)
MINIMUM_INDEPENDENT_WITNESSES = 4

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "assurance_bundle",
    "proof_dependency_graph",
    "universal_accountability_audit_trail",
    "universal_provider_wire_protocol",
    "universal_claim_provenance_envelope",
    "universal_runtime_conformance_receipt",
    "universal_attribution_authority_control_plane",
    "publication_monitor",
    "publication_witness",
    "trust_registry",
    "response_envelope",
    "source_footer_delivery",
    "client_attribution_enforcement",
    "revenue_allocation_report",
    "finance_ledger_attestation",
)

REQUIRED_CHECKPOINT_TYPES = (
    "l152_audit_trail_root",
    "artifact_bundle_root",
    "discovery_manifest_root",
    "governance_policy_root",
    "provider_wire_root",
    "source_footer_delivery_root",
    "settlement_meter_root",
    "challenge_correction_root",
    "redaction_manifest_root",
    "revocation_state_root",
)

REQUIRED_TRANSPARENCY_LOGS = (
    "provider_public_log",
    "independent_auditor_log",
    "creator_collective_log",
    "customer_tenant_log",
    "regulator_export_log",
    "industry_federation_log",
)

REQUIRED_WITNESS_ROLES = (
    "independent_auditor",
    "creator_collective",
    "customer_representative",
    "regulator_observer",
    "public_interest_monitor",
)

REQUIRED_MONITOR_TYPES = (
    "provider_self_monitor",
    "creator_watch_monitor",
    "customer_reliance_monitor",
    "auditor_consistency_monitor",
    "regulator_export_monitor",
)

REQUIRED_INTEGRITY_CONTROLS = (
    "signed_checkpoint",
    "merkle_inclusion_proof",
    "merkle_consistency_proof",
    "scitt_receipt_binding",
    "rekor_or_equivalent_entry_binding",
    "c2sp_checkpoint_format_binding",
    "witness_cosignature_quorum",
    "monitor_continuity",
    "split_view_challenge",
    "witness_identity_registry_binding",
    "redaction_manifest_binding",
    "privacy_payload_filter",
)

REQUIRED_FAILURE_CASES = (
    "missing_l152_audit_trail",
    "missing_transparency_inclusion",
    "missing_consistency_proof",
    "insufficient_witness_quorum",
    "provider_only_witness_set",
    "untrusted_witness_identity",
    "stale_checkpoint",
    "split_view_log_roots",
    "unsigned_checkpoint",
    "missing_monitor_continuity",
    "redaction_manifest_missing",
    "settlement_without_witnessed_checkpoint",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_accountability_witness_quorum_hash",
    "universal_accountability_audit_trail_hash",
    "universal_provider_wire_protocol_hash",
    "universal_claim_provenance_envelope_hash",
    "universal_runtime_conformance_receipt_hash",
    "universal_attribution_authority_control_plane_hash",
    "publication_witness_hash",
    "publication_monitor_hash",
    "trust_registry_hash",
    "source_footer_delivery_hash",
    "client_enforcement_hash",
    "attestation_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
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


def load_universal_accountability_witness_quorum_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L153 witness quorum artifact."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_quorum(quorum: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in quorum.items()
        if key not in {"universal_accountability_witness_quorum_hash", "signature"}
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
    public_payload: dict[str, Any], quorum_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in quorum_input.get("private_strings", [])
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


def _component_input_map(quorum_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    value = quorum_input.get(key, {})
    if isinstance(value, dict):
        return {str(name): row for name, row in value.items() if isinstance(row, dict)}
    if isinstance(value, list):
        result: dict[str, dict[str, Any]] = {}
        for row in value:
            if not isinstance(row, dict):
                continue
            name = (
                row.get("checkpoint_type")
                or row.get("log_id")
                or row.get("witness_role")
                or row.get("monitor_type")
                or row.get("control")
                or row.get("case_id")
            )
            if name:
                result[str(name)] = row
        return result
    return {}


def _policy(quorum_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(quorum_input.get("witness_quorum_policy", {}))
    return {
        "profile": "rdllm-universal-accountability-witness-quorum-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_accountability_level": MINIMUM_ACCOUNTABILITY_LEVEL,
        "minimum_provider_wire_level": MINIMUM_PROVIDER_WIRE_LEVEL,
        "well_known_path": DEFAULT_WELL_KNOWN_PATH,
        "minimum_independent_witnesses": int(
            policy.get("minimum_independent_witnesses", MINIMUM_INDEPENDENT_WITNESSES)
            or MINIMUM_INDEPENDENT_WITNESSES
        ),
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_checkpoint_types": list(
            policy.get("required_checkpoint_types", REQUIRED_CHECKPOINT_TYPES)
        ),
        "required_transparency_logs": list(
            policy.get("required_transparency_logs", REQUIRED_TRANSPARENCY_LOGS)
        ),
        "required_witness_roles": list(
            policy.get("required_witness_roles", REQUIRED_WITNESS_ROLES)
        ),
        "required_monitor_types": list(
            policy.get("required_monitor_types", REQUIRED_MONITOR_TYPES)
        ),
        "required_integrity_controls": list(
            policy.get("required_integrity_controls", REQUIRED_INTEGRITY_CONTROLS)
        ),
        "required_failure_cases": list(
            policy.get("required_failure_cases", REQUIRED_FAILURE_CASES)
        ),
        "checkpoint_rule": "every_l152_audit_root_must_be_logged_with_inclusion_and_consistency_proofs",
        "witness_rule": "provider_only_witness_sets_cannot_authorize_grounded_display_or_settlement",
        "monitor_rule": "independent_monitors_must_detect_split_views_and_stale_checkpoints",
        "privacy_rule": "public_witness_artifact_contains_hashes_roles_roots_and_receipts_not_payloads",
    }


def _artifact_bindings(quorum_input: dict[str, Any], names: list[str]) -> dict[str, Any]:
    rows = []
    for name in names:
        artifact = quorum_input.get(name)
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


def _checkpoint_rows(
    quorum_input: dict[str, Any], required_checkpoint_types: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(quorum_input, "checkpoint_rows")
    l152_hash = _declared_hash(quorum_input.get("universal_accountability_audit_trail"))
    previous_checkpoint_hash = hash_payload("rdllm-accountability-witness-genesis")
    rows = []
    for index, checkpoint_type in enumerate(required_checkpoint_types):
        item = row_map.get(checkpoint_type, {})
        checkpoint_hash = str(item.get("checkpoint_hash", ""))
        row = {
            "checkpoint_type": checkpoint_type,
            "checkpoint_sequence": int(item.get("checkpoint_sequence", index) or 0),
            "previous_checkpoint_hash": str(
                item.get("previous_checkpoint_hash", previous_checkpoint_hash)
            ),
            "expected_previous_checkpoint_hash": previous_checkpoint_hash,
            "l152_audit_trail_hash": str(
                item.get("l152_audit_trail_hash", l152_hash)
            ),
            "checkpoint_hash": checkpoint_hash,
            "signed_checkpoint_hash": str(item.get("signed_checkpoint_hash", "")),
            "log_root_hash": str(item.get("log_root_hash", "")),
            "tree_size": int(item.get("tree_size", 0) or 0),
            "inclusion_proof_hash": str(item.get("inclusion_proof_hash", "")),
            "consistency_proof_hash": str(item.get("consistency_proof_hash", "")),
            "redaction_manifest_hash": str(item.get("redaction_manifest_hash", "")),
            "timestamp_commitment_hash": str(
                item.get("timestamp_commitment_hash", "")
            ),
            "append_only": item.get("append_only") is True,
            "included": item.get("included") is True,
            "consistent_with_previous": item.get("consistent_with_previous") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
        }
        row["chain_contiguous"] = row["previous_checkpoint_hash"] == previous_checkpoint_hash
        row["sequence_monotonic"] = row["checkpoint_sequence"] == index
        row["ready"] = (
            row["chain_contiguous"]
            and row["sequence_monotonic"]
            and bool(row["l152_audit_trail_hash"])
            and row["l152_audit_trail_hash"] == l152_hash
            and bool(row["checkpoint_hash"])
            and bool(row["signed_checkpoint_hash"])
            and bool(row["log_root_hash"])
            and row["tree_size"] > 0
            and bool(row["inclusion_proof_hash"])
            and bool(row["consistency_proof_hash"])
            and bool(row["redaction_manifest_hash"])
            and bool(row["timestamp_commitment_hash"])
            and row["append_only"]
            and row["included"]
            and row["consistent_with_previous"]
            and row["privacy_preserving"]
        )
        row["checkpoint_row_hash"] = hash_payload(row)
        previous_checkpoint_hash = row["checkpoint_row_hash"]
        rows.append(row)
    return rows


def _transparency_log_rows(
    quorum_input: dict[str, Any], required_logs: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(quorum_input, "transparency_log_rows")
    l152_hash = _declared_hash(quorum_input.get("universal_accountability_audit_trail"))
    rows = []
    for log_id in required_logs:
        item = row_map.get(log_id, {})
        row = {
            "log_id": log_id,
            "log_operator_hash": str(item.get("log_operator_hash", "")),
            "log_type": str(item.get("log_type", "")),
            "public_endpoint_hash": str(item.get("public_endpoint_hash", "")),
            "identity_hash": str(item.get("identity_hash", "")),
            "l152_audit_trail_hash": str(item.get("l152_audit_trail_hash", l152_hash)),
            "checkpoint_hash": str(item.get("checkpoint_hash", "")),
            "signed_tree_head_hash": str(item.get("signed_tree_head_hash", "")),
            "tree_size": int(item.get("tree_size", 0) or 0),
            "tree_root_hash": str(item.get("tree_root_hash", "")),
            "inclusion_proof_hash": str(item.get("inclusion_proof_hash", "")),
            "consistency_proof_hash": str(item.get("consistency_proof_hash", "")),
            "append_only": item.get("append_only") is True,
            "inclusion_verified": item.get("inclusion_verified") is True,
            "consistency_verified": item.get("consistency_verified") is True,
            "public_discoverable": item.get("public_discoverable") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
        }
        row["ready"] = (
            bool(row["log_operator_hash"])
            and row["log_type"] in {"rfc9162", "scitt", "rekor", "c2sp", "trillian", "equivalent_vds"}
            and bool(row["public_endpoint_hash"])
            and bool(row["identity_hash"])
            and row["l152_audit_trail_hash"] == l152_hash
            and bool(row["checkpoint_hash"])
            and bool(row["signed_tree_head_hash"])
            and row["tree_size"] > 0
            and bool(row["tree_root_hash"])
            and bool(row["inclusion_proof_hash"])
            and bool(row["consistency_proof_hash"])
            and row["append_only"]
            and row["inclusion_verified"]
            and row["consistency_verified"]
            and row["public_discoverable"]
            and row["privacy_preserving"]
        )
        row["transparency_log_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _witness_signature_rows(
    quorum_input: dict[str, Any], required_roles: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(quorum_input, "witness_signature_rows")
    l152_hash = _declared_hash(quorum_input.get("universal_accountability_audit_trail"))
    rows = []
    for role in required_roles:
        item = row_map.get(role, {})
        row = {
            "witness_role": role,
            "witness_identity_hash": str(item.get("witness_identity_hash", "")),
            "trust_registry_entry_hash": str(item.get("trust_registry_entry_hash", "")),
            "observed_l152_audit_trail_hash": str(
                item.get("observed_l152_audit_trail_hash", l152_hash)
            ),
            "observed_log_root_hash": str(item.get("observed_log_root_hash", "")),
            "signed_checkpoint_hash": str(item.get("signed_checkpoint_hash", "")),
            "signature_hash": str(item.get("signature_hash", "")),
            "conflict_disclosure_hash": str(item.get("conflict_disclosure_hash", "")),
            "active_identity": item.get("active_identity") is True,
            "independent_from_provider": item.get("independent_from_provider") is True,
            "signature_verified": item.get("signature_verified") is True,
            "no_open_conflict": item.get("no_open_conflict") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
        }
        row["ready"] = (
            bool(row["witness_identity_hash"])
            and bool(row["trust_registry_entry_hash"])
            and row["observed_l152_audit_trail_hash"] == l152_hash
            and bool(row["observed_log_root_hash"])
            and bool(row["signed_checkpoint_hash"])
            and bool(row["signature_hash"])
            and bool(row["conflict_disclosure_hash"])
            and row["active_identity"]
            and row["independent_from_provider"]
            and row["signature_verified"]
            and row["no_open_conflict"]
            and row["privacy_preserving"]
        )
        row["witness_signature_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _monitor_rows(
    quorum_input: dict[str, Any], required_monitor_types: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(quorum_input, "monitor_rows")
    rows = []
    for monitor_type in required_monitor_types:
        item = row_map.get(monitor_type, {})
        row = {
            "monitor_type": monitor_type,
            "monitor_identity_hash": str(item.get("monitor_identity_hash", "")),
            "checkpoint_hash": str(item.get("checkpoint_hash", "")),
            "observed_log_root_hash": str(item.get("observed_log_root_hash", "")),
            "query_commitment_hash": str(item.get("query_commitment_hash", "")),
            "consistency_proof_hash": str(item.get("consistency_proof_hash", "")),
            "alert_channel_hash": str(item.get("alert_channel_hash", "")),
            "continuity_verified": item.get("continuity_verified") is True,
            "no_split_view_detected": item.get("no_split_view_detected") is True,
            "public_or_auditor_accessible": item.get("public_or_auditor_accessible") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
        }
        row["ready"] = (
            bool(row["monitor_identity_hash"])
            and bool(row["checkpoint_hash"])
            and bool(row["observed_log_root_hash"])
            and bool(row["query_commitment_hash"])
            and bool(row["consistency_proof_hash"])
            and bool(row["alert_channel_hash"])
            and row["continuity_verified"]
            and row["no_split_view_detected"]
            and row["public_or_auditor_accessible"]
            and row["privacy_preserving"]
        )
        row["monitor_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _integrity_control_rows(
    quorum_input: dict[str, Any], required_controls: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(quorum_input, "integrity_control_rows")
    rows = []
    for control in sorted(required_controls):
        item = row_map.get(control, {})
        row = {
            "control": control,
            "control_evidence_hash": str(item.get("control_evidence_hash", "")),
            "verifier_hash": str(item.get("verifier_hash", "")),
            "audit_export_hash": str(item.get("audit_export_hash", "")),
            "failure_action": str(item.get("failure_action", "")),
            "implemented": item.get("implemented") is True,
            "fail_closed": item.get("fail_closed") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
        }
        row["ready"] = (
            bool(row["control_evidence_hash"])
            and bool(row["verifier_hash"])
            and bool(row["audit_export_hash"])
            and row["failure_action"] == "block_unwitnessed_display_and_settlement"
            and row["implemented"]
            and row["fail_closed"]
            and row["privacy_preserving"]
        )
        row["integrity_control_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _failure_case_rows(
    quorum_input: dict[str, Any], required_cases: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(quorum_input, "failure_case_rows")
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
            and row["verifier_command"] == "verify-universal-accountability-witness-quorum"
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


def _artifact_summary(quorum_input: dict[str, Any], name: str) -> dict[str, Any]:
    artifact = quorum_input.get(name)
    return _summary(artifact if isinstance(artifact, dict) else None)


def make_universal_accountability_witness_quorum(
    quorum_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create the L153 universal accountability witness quorum artifact."""

    policy = _policy(quorum_input)
    required_artifacts = list(policy["required_core_artifacts"])
    artifact_bindings = _artifact_bindings(quorum_input, required_artifacts)
    bindings = _binding_by_name(artifact_bindings)
    checkpoint_rows = _checkpoint_rows(
        quorum_input, list(policy["required_checkpoint_types"])
    )
    log_rows = _transparency_log_rows(
        quorum_input, list(policy["required_transparency_logs"])
    )
    witness_rows = _witness_signature_rows(
        quorum_input, list(policy["required_witness_roles"])
    )
    monitor_rows = _monitor_rows(
        quorum_input, list(policy["required_monitor_types"])
    )
    integrity_rows = _integrity_control_rows(
        quorum_input, list(policy["required_integrity_controls"])
    )
    failure_rows = _failure_case_rows(
        quorum_input, list(policy["required_failure_cases"])
    )

    certification_summary = _artifact_summary(quorum_input, "certification_report")
    l152_summary = _artifact_summary(
        quorum_input, "universal_accountability_audit_trail"
    )
    l151_summary = _artifact_summary(
        quorum_input, "universal_provider_wire_protocol"
    )
    proof_graph_summary = _artifact_summary(quorum_input, "proof_dependency_graph")
    publication_monitor_summary = _artifact_summary(quorum_input, "publication_monitor")
    publication_witness_summary = _artifact_summary(quorum_input, "publication_witness")
    trust_registry_summary = _artifact_summary(quorum_input, "trust_registry")

    provider_card = quorum_input.get("provider_attribution_card", {})
    integration_profile = quorum_input.get("integration_profile", {})
    discovery_manifest = quorum_input.get("discovery_manifest", {})
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

    independent_ready_witness_count = sum(
        1
        for row in witness_rows
        if row.get("ready") is True and row.get("independent_from_provider") is True
    )
    witness_role_coverage = {
        role: any(row.get("witness_role") == role and row.get("ready") for row in witness_rows)
        for role in policy["required_witness_roles"]
    }
    public_projection = {
        "artifact_bindings": artifact_bindings,
        "checkpoint_rows": checkpoint_rows,
        "transparency_log_rows": log_rows,
        "witness_signature_rows": witness_rows,
        "monitor_rows": monitor_rows,
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
        "certification_passed_l152_or_higher": (
            certification_summary.get("status") == "passed"
            and _level_at_least(
                certification_summary.get("highest_level"),
                MINIMUM_ACCOUNTABILITY_LEVEL,
            )
        ),
        "accountability_audit_ready_l152": (
            l152_summary.get("status") == "ready"
            and _level_at_least(
                l152_summary.get("target_certification_level"),
                MINIMUM_ACCOUNTABILITY_LEVEL,
            )
            and int(l152_summary.get("failed_check_count", 0) or 0) == 0
        ),
        "provider_wire_ready_l151": (
            l151_summary.get("status") == "ready"
            and _level_at_least(
                l151_summary.get("target_certification_level"),
                MINIMUM_PROVIDER_WIRE_LEVEL,
            )
            and int(l151_summary.get("failed_check_count", 0) or 0) == 0
        ),
        "all_checkpoints_ready": _all_ready(checkpoint_rows),
        "all_transparency_logs_ready": _all_ready(log_rows),
        "all_witness_roles_ready": _all_ready(witness_rows),
        "independent_witness_quorum_met": (
            independent_ready_witness_count
            >= int(policy["minimum_independent_witnesses"])
        ),
        "all_required_witness_roles_covered": all(witness_role_coverage.values()),
        "all_monitors_ready": _all_ready(monitor_rows),
        "all_integrity_controls_ready": _all_ready(integrity_rows),
        "all_failure_cases_prove_blocking": _all_ready(failure_rows),
        "publication_surfaces_declared": (
            public_surfaces.get("universal_accountability_witness_quorum") is True
            or discovery.get("universal_accountability_witness_quorum_path")
            == DEFAULT_WELL_KNOWN_PATH
        ),
        "proof_graph_acyclic": (
            int(proof_graph_summary.get("cycle_node_count", 0) or 0) == 0
            and proof_graph_summary.get("status") in {"ready", "ok"}
        ),
        "publication_monitor_ready": publication_monitor_summary.get("status")
        in {"ready", "ok"},
        "publication_witness_ready": publication_witness_summary.get("status")
        in {"ready", "ok"},
        "trust_registry_ready": trust_registry_summary.get("status") in {"ready", "ok"},
        "privacy_preserved": (
            not private_findings
            and _private_strings_absent(public_projection, quorum_input)
        ),
    }
    failed_checks = [name for name, passed in checks.items() if passed is not True]
    failure_modes_by_check = {
        "all_required_artifacts_present": "witness_required_artifact_missing",
        "all_required_artifact_hashes_reproducible": "witness_artifact_hash_not_reproducible",
        "certification_passed_l152_or_higher": "witness_certification_below_l152",
        "accountability_audit_ready_l152": "witness_l152_audit_not_ready",
        "provider_wire_ready_l151": "witness_l151_wire_not_ready",
        "all_checkpoints_ready": "witness_checkpoint_gap",
        "all_transparency_logs_ready": "witness_transparency_log_gap",
        "all_witness_roles_ready": "witness_signature_gap",
        "independent_witness_quorum_met": "witness_quorum_insufficient",
        "all_required_witness_roles_covered": "witness_role_gap",
        "all_monitors_ready": "witness_monitor_gap",
        "all_integrity_controls_ready": "witness_integrity_control_gap",
        "all_failure_cases_prove_blocking": "witness_negative_case_gap",
        "publication_surfaces_declared": "witness_publication_gap",
        "proof_graph_acyclic": "witness_proof_graph_cycle",
        "publication_monitor_ready": "witness_publication_monitor_not_ready",
        "publication_witness_ready": "witness_publication_witness_not_ready",
        "trust_registry_ready": "witness_trust_registry_not_ready",
        "privacy_preserved": "witness_private_payload_leak",
    }
    failure_modes = [failure_modes_by_check[name] for name in failed_checks]
    ready = not failed_checks

    quorum = {
        "witness_quorum_version": UNIVERSAL_ACCOUNTABILITY_WITNESS_QUORUM_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "witness_quorum_policy": policy,
        "artifact_bindings": artifact_bindings,
        "checkpoint_rows": checkpoint_rows,
        "transparency_log_rows": log_rows,
        "witness_signature_rows": witness_rows,
        "monitor_rows": monitor_rows,
        "integrity_control_rows": integrity_rows,
        "failure_case_rows": failure_rows,
        "evidence_commitments": {
            "artifact_binding_root": artifact_bindings["artifact_binding_root"],
            "checkpoint_root": merkle_root(
                [row["checkpoint_row_hash"] for row in checkpoint_rows]
            ),
            "transparency_log_root": merkle_root(
                [row["transparency_log_row_hash"] for row in log_rows]
            ),
            "witness_signature_root": merkle_root(
                [row["witness_signature_row_hash"] for row in witness_rows]
            ),
            "monitor_root": merkle_root([row["monitor_row_hash"] for row in monitor_rows]),
            "integrity_control_root": merkle_root(
                [row["integrity_control_row_hash"] for row in integrity_rows]
            ),
            "failure_case_root": merkle_root(
                [row["failure_case_row_hash"] for row in failure_rows]
            ),
        },
        "checks": checks,
        "witness_role_coverage": witness_role_coverage,
        "witness_decision": {
            "universal_accountability_witness_quorum_authorized": ready,
            "provider_publication_trusted": ready,
            "customer_acceptance_allowed": ready,
            "creator_query_settlement_allowed": ready,
            "regulator_reliance_allowed": ready,
            "unwitnessed_audit_trail_allowed": False,
            "split_view_risk_accepted": False,
            "failure_modes": failure_modes,
        },
        "verifier_commands": [
            "verify-universal-accountability-witness-quorum",
            "verify-universal-accountability-audit-trail",
            "verify-universal-provider-wire-protocol",
            "verify-publication-monitor",
            "verify-publication-witness",
            "verify-proof-dependency-graph",
            "verify-trust-registry",
        ],
        "standards_controls": {
            "ct_rfc9162": "signed_tree_heads_inclusion_proofs_and_consistency_proofs",
            "scitt_rfc9943": "signed_statement_receipts_from_transparency_services",
            "sigstore_rekor": "artifact_signature_transparency_entry_and_monitoring",
            "c2sp_checkpoints": "portable_signed_log_checkpoint_format",
            "c2sp_witness": "http_witness_cosignature_protocol_for_checkpoints",
            "trillian": "verifiable_log_consistency_and_monitoring",
            "cosi": "witness_cosigning_against_split_view_authorities",
            "source_urls": {
                "rfc9162": "https://www.rfc-editor.org/rfc/rfc9162.html",
                "rfc9943_scitt": "https://www.rfc-editor.org/rfc/rfc9943.html",
                "sigstore_rekor": "https://docs.sigstore.dev/logging/overview/",
                "c2sp_checkpoint_witness": "https://github.com/C2SP/C2SP/",
                "trillian_vds": "https://transparency.dev/verifiable-data-structures/",
                "cosi": "https://arxiv.org/abs/1503.08768",
            },
        },
        "privacy": {
            "public_witness_contains_raw_prompts": False,
            "public_witness_contains_raw_outputs": False,
            "public_witness_contains_source_text": False,
            "public_witness_contains_tool_payloads": False,
            "public_witness_contains_customer_or_payment_data": False,
            "hash_only_witness_commitments": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_accountability_level": MINIMUM_ACCOUNTABILITY_LEVEL,
            "minimum_provider_wire_level": MINIMUM_PROVIDER_WIRE_LEVEL,
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
            "core_artifact_count": artifact_bindings["artifact_count"],
            "checkpoint_count": len(checkpoint_rows),
            "ready_checkpoint_count": _count(checkpoint_rows),
            "transparency_log_count": len(log_rows),
            "ready_transparency_log_count": _count(log_rows),
            "witness_role_count": len(witness_role_coverage),
            "ready_witness_role_count": _count(witness_rows),
            "covered_witness_role_count": sum(
                1 for covered in witness_role_coverage.values() if covered
            ),
            "independent_ready_witness_count": independent_ready_witness_count,
            "minimum_independent_witnesses": int(
                policy["minimum_independent_witnesses"]
            ),
            "monitor_count": len(monitor_rows),
            "ready_monitor_count": _count(monitor_rows),
            "integrity_control_count": len(integrity_rows),
            "ready_integrity_control_count": _count(integrity_rows),
            "failure_case_count": len(failure_rows),
            "offline_verification_supported": True,
            "privacy_preserved": checks["privacy_preserved"],
        },
    }
    quorum["universal_accountability_witness_quorum_hash"] = hash_payload(
        _hashable_quorum(quorum)
    )
    if signing_secret:
        quorum["signature"] = sign_payload(_hashable_quorum(quorum), signing_secret)
    return quorum


def validate_universal_accountability_witness_quorum_shape(
    quorum: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    required = (
        "witness_quorum_version",
        "issuer",
        "created_at",
        "witness_quorum_policy",
        "artifact_bindings",
        "checkpoint_rows",
        "transparency_log_rows",
        "witness_signature_rows",
        "monitor_rows",
        "integrity_control_rows",
        "failure_case_rows",
        "evidence_commitments",
        "checks",
        "witness_role_coverage",
        "witness_decision",
        "verifier_commands",
        "standards_controls",
        "privacy",
        "summary",
        "universal_accountability_witness_quorum_hash",
    )
    for key in required:
        if key not in quorum:
            errors.append(f"missing universal accountability witness quorum field: {key}")
    if errors:
        return errors
    if (
        quorum.get("witness_quorum_version")
        != UNIVERSAL_ACCOUNTABILITY_WITNESS_QUORUM_VERSION
    ):
        errors.append("universal accountability witness quorum version is unsupported")
    if quorum.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal accountability witness quorum target level is not RDLLM-L153")
    if (
        quorum.get("witness_quorum_policy", {}).get("well_known_path")
        != DEFAULT_WELL_KNOWN_PATH
    ):
        errors.append("universal accountability witness quorum well-known path is invalid")
    if quorum.get("witness_decision", {}).get("unwitnessed_audit_trail_allowed") is not False:
        errors.append("universal accountability witness quorum permits unwitnessed trails")
    if quorum.get("witness_decision", {}).get("split_view_risk_accepted") is not False:
        errors.append("universal accountability witness quorum accepts split-view risk")
    return errors


def verify_universal_accountability_witness_quorum(
    quorum: dict[str, Any],
    *,
    quorum_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L153 witness quorum artifact against private replay input."""

    errors = validate_universal_accountability_witness_quorum_shape(quorum)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_quorum(quorum))
    if expected_hash != quorum.get("universal_accountability_witness_quorum_hash"):
        errors.append("universal accountability witness quorum hash is not reproducible")

    expected = make_universal_accountability_witness_quorum(
        quorum_input,
        issuer=quorum.get("issuer", DEFAULT_ISSUER),
        created_at=quorum.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "witness_quorum_policy",
        "artifact_bindings",
        "checkpoint_rows",
        "transparency_log_rows",
        "witness_signature_rows",
        "monitor_rows",
        "integrity_control_rows",
        "failure_case_rows",
        "evidence_commitments",
        "checks",
        "witness_role_coverage",
        "witness_decision",
        "verifier_commands",
        "standards_controls",
        "privacy",
        "summary",
    ):
        if expected.get(key) != quorum.get(key):
            errors.append(f"universal accountability witness quorum {key} does not match replay input")
    if (
        expected.get("universal_accountability_witness_quorum_hash")
        != quorum.get("universal_accountability_witness_quorum_hash")
    ):
        errors.append("universal accountability witness quorum hash does not match replay input")
    if signing_secret and expected.get("signature") != quorum.get("signature"):
        errors.append("universal accountability witness quorum signature is invalid")
    if quorum.get("summary", {}).get("status") != "ready":
        errors.append("universal accountability witness quorum status is not ready")
    for check, passed in quorum.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal accountability witness quorum check failed: {check}")
    if _contains_private_fields(quorum):
        errors.append("universal accountability witness quorum exposes a private field")
    return errors
