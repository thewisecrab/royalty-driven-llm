"""Universal reliance correction ledger.

The L155 layer keeps answer attribution reliable after publication. L154 proves
that a source footer and settlement row are grounded at release time; L155 proves
that later corrections, revocations, stale-source findings, copied-output status
links, cache invalidations, client notices, and settlement holds are published as
append-only status rows before users or creators keep relying on them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_RELIANCE_CORRECTION_LEDGER_VERSION = (
    "rdllm-universal-reliance-correction-ledger/v1"
)
UNIVERSAL_RELIANCE_CORRECTION_LEDGER_SCHEMA = (
    "docs/schemas/universal_reliance_correction_ledger.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L155"
MINIMUM_RELIANCE_LEVEL = "RDLLM-L154"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-reliance-correction-ledger.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "assurance_bundle",
    "proof_dependency_graph",
    "universal_grounded_reliance_contract",
    "universal_accountability_witness_quorum",
    "universal_accountability_audit_trail",
    "universal_provider_wire_protocol",
    "universal_claim_provenance_envelope",
    "response_envelope",
    "source_footer_delivery",
    "client_attribution_enforcement",
    "citation_url_health",
    "source_freshness_audit",
    "counterevidence_report",
    "evidence_force_calibration",
    "warranted_source_footer",
    "source_origin_lineage",
    "post_release_discovery_report",
    "output_provenance_binding_report",
    "attribution_challenge_report",
    "revenue_allocation_report",
    "finance_ledger_attestation",
    "publication_monitor",
    "publication_witness",
    "trust_registry",
)

REQUIRED_RELIANCE_STATUS_TYPES = (
    "active_verified_answer",
    "corrected_answer",
    "revoked_source_footer",
    "downgraded_confidence_label",
    "superseded_evidence_locator",
    "settlement_hold",
    "settlement_adjustment",
    "regulator_notice",
)

REQUIRED_CORRECTION_BROADCAST_CHANNELS = (
    "well_known_status_feed",
    "response_metadata_status_endpoint",
    "client_sdk_push",
    "cache_invalidation",
    "copy_capsule_update",
    "creator_notice",
    "customer_procurement_notice",
    "regulator_export_notice",
)

REQUIRED_REVALIDATION_CHECKS = (
    "citation_retraction_check",
    "source_url_revalidation",
    "freshness_revalidation",
    "counterevidence_scan",
    "license_revocation_check",
    "confidence_downgrade_check",
    "client_render_recheck",
    "settlement_hold_recheck",
)

REQUIRED_SETTLEMENT_CORRECTION_SCOPES = (
    "direct_payout_hold",
    "creator_debit_credit_adjustment",
    "escrow_reallocation",
    "finance_ledger_reversal",
    "tax_report_correction",
    "challenge_resolution_settlement",
)

REQUIRED_STANDARD_CONTROLS = (
    "c2pa_update_manifest",
    "c2pa_ocsp_revocation_status",
    "w3c_vc_status_list",
    "scitt_status_receipt",
    "rfc9162_append_only_status_log",
    "sigstore_rekor_status_entry",
    "nist_ai_rmf_incident_response",
    "eu_ai_act_correction_transparency",
)

REQUIRED_FAILURE_CASES = (
    "stale_retraction_not_detected",
    "revoked_source_still_displayed",
    "corrected_footer_not_broadcast",
    "cache_serves_revoked_footer",
    "copied_output_missing_status_link",
    "settlement_released_after_revocation",
    "client_ignores_status_downgrade",
    "status_feed_split_view",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_reliance_correction_ledger_hash",
    "universal_grounded_reliance_contract_hash",
    "universal_accountability_witness_quorum_hash",
    "universal_accountability_audit_trail_hash",
    "universal_provider_wire_protocol_hash",
    "universal_claim_provenance_envelope_hash",
    "source_footer_delivery_hash",
    "client_enforcement_hash",
    "citation_url_health_hash",
    "source_freshness_audit_hash",
    "evidence_force_calibration_hash",
    "warranted_source_footer_hash",
    "source_origin_lineage_hash",
    "trust_registry_hash",
    "publication_witness_hash",
    "publication_monitor_hash",
    "post_release_report_hash",
    "binding_report_hash",
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

STATUS_BY_TYPE = {
    "active_verified_answer": "active",
    "corrected_answer": "corrected",
    "revoked_source_footer": "revoked",
    "downgraded_confidence_label": "downgraded",
    "superseded_evidence_locator": "superseded",
    "settlement_hold": "held",
    "settlement_adjustment": "adjusted",
    "regulator_notice": "corrected",
}

DISPLAY_ACTIONS_BY_STATUS = {
    "active": {"show_current"},
    "corrected": {"show_correction", "show_corrected_footer", "replace_footer"},
    "revoked": {"block", "show_revocation", "block_or_replace"},
    "downgraded": {"downgrade_label", "show_downgrade"},
    "superseded": {"replace_locator", "show_supersession"},
    "held": {"show_hold_notice", "block_settlement_claim"},
    "adjusted": {"show_adjustment", "show_settlement_adjustment"},
}

SETTLEMENT_ACTIONS_BY_STATUS = {
    "active": {"release"},
    "corrected": {"hold", "adjust", "notice"},
    "revoked": {"hold"},
    "downgraded": {"hold", "adjust"},
    "superseded": {"hold", "adjust"},
    "held": {"hold"},
    "adjusted": {"adjust"},
}


def load_universal_reliance_correction_ledger_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L155 reliance correction ledger."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in ledger.items()
        if key not in {"universal_reliance_correction_ledger_hash", "signature"}
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
    public_payload: dict[str, Any], ledger_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in ledger_input.get("private_strings", [])
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


def _component_input_map(
    ledger_input: dict[str, Any], key: str
) -> dict[str, dict[str, Any]]:
    value = ledger_input.get(key, {})
    if isinstance(value, dict):
        return {str(name): row for name, row in value.items() if isinstance(row, dict)}
    if isinstance(value, list):
        result: dict[str, dict[str, Any]] = {}
        for row in value:
            if not isinstance(row, dict):
                continue
            name = (
                row.get("status_type")
                or row.get("channel")
                or row.get("check_id")
                or row.get("scope")
                or row.get("control")
                or row.get("case_id")
            )
            if name:
                result[str(name)] = row
        return result
    return {}


def _policy(ledger_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(ledger_input.get("reliance_correction_policy", {}))
    return {
        "profile": "rdllm-universal-reliance-correction-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_reliance_level": MINIMUM_RELIANCE_LEVEL,
        "well_known_path": DEFAULT_WELL_KNOWN_PATH,
        "maximum_correction_delivery_seconds": int(
            policy.get("maximum_correction_delivery_seconds", 86400) or 86400
        ),
        "maximum_revalidation_interval_seconds": int(
            policy.get("maximum_revalidation_interval_seconds", 86400) or 86400
        ),
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_reliance_status_types": list(
            policy.get("required_reliance_status_types", REQUIRED_RELIANCE_STATUS_TYPES)
        ),
        "required_correction_broadcast_channels": list(
            policy.get(
                "required_correction_broadcast_channels",
                REQUIRED_CORRECTION_BROADCAST_CHANNELS,
            )
        ),
        "required_revalidation_checks": list(
            policy.get("required_revalidation_checks", REQUIRED_REVALIDATION_CHECKS)
        ),
        "required_settlement_correction_scopes": list(
            policy.get(
                "required_settlement_correction_scopes",
                REQUIRED_SETTLEMENT_CORRECTION_SCOPES,
            )
        ),
        "required_standard_controls": list(
            policy.get("required_standard_controls", REQUIRED_STANDARD_CONTROLS)
        ),
        "required_failure_cases": list(
            policy.get("required_failure_cases", REQUIRED_FAILURE_CASES)
        ),
        "status_rule": "every_reliance_contract_footer_claim_locator_and_settlement_row_requires_a_live_hash_bound_status",
        "correction_rule": "revoked_corrected_stale_or_downgraded_statuses_must_be_broadcast_to_clients_caches_copies_creators_customers_and_regulators",
        "settlement_rule": "source_or_footer_revocation_blocks_or_adjusts_creator_settlement_until_the_correction_is_reconciled",
        "privacy_rule": "public_correction_ledger_contains_hashes_roots_counts_statuses_and_actions_not_private_payloads",
    }


def _artifact_bindings(ledger_input: dict[str, Any], names: list[str]) -> dict[str, Any]:
    rows = []
    for name in names:
        artifact = ledger_input.get(name)
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


def _reliance_status_rows(
    ledger_input: dict[str, Any], required_status_types: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(ledger_input, "reliance_status_rows")
    contract_hash = _declared_hash(ledger_input.get("universal_grounded_reliance_contract"))
    rows = []
    for status_type in required_status_types:
        item = row_map.get(status_type, {})
        status = str(item.get("status", STATUS_BY_TYPE.get(status_type, "")))
        display_action = str(item.get("display_action", ""))
        settlement_action = str(item.get("settlement_action", ""))
        row = {
            "status_type": status_type,
            "subject_type": str(item.get("subject_type", status_type)),
            "subject_hash": str(item.get("subject_hash", "")),
            "previous_status_hash": str(item.get("previous_status_hash", "")),
            "l154_contract_hash": str(item.get("l154_contract_hash", contract_hash)),
            "status_list_hash": str(item.get("status_list_hash", "")),
            "status": status,
            "reason_code": str(item.get("reason_code", "")),
            "effective_at_hash": str(item.get("effective_at_hash", "")),
            "evidence_hash": str(item.get("evidence_hash", "")),
            "display_action": display_action,
            "settlement_action": settlement_action,
            "revision": int(item.get("revision", 0) or 0),
            "client_status_link_required": item.get("client_status_link_required")
            is True,
            "transparency_log_included": item.get("transparency_log_included") is True,
            "append_only": item.get("append_only") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["display_action_valid"] = display_action in DISPLAY_ACTIONS_BY_STATUS.get(
            status, set()
        )
        row["settlement_action_valid"] = settlement_action in (
            SETTLEMENT_ACTIONS_BY_STATUS.get(status, set())
        )
        row["revoked_or_held_blocks_release"] = not (
            status in {"revoked", "held"} and settlement_action == "release"
        )
        row["revoked_or_downgraded_blocks_current_display"] = not (
            status in {"revoked", "downgraded"} and display_action == "show_current"
        )
        row["ready"] = (
            bool(row["subject_hash"])
            and bool(row["previous_status_hash"])
            and row["l154_contract_hash"] == contract_hash
            and bool(row["status_list_hash"])
            and status in set(STATUS_BY_TYPE.values())
            and bool(row["reason_code"])
            and bool(row["effective_at_hash"])
            and bool(row["evidence_hash"])
            and row["display_action_valid"]
            and row["settlement_action_valid"]
            and row["revision"] > 0
            and row["client_status_link_required"]
            and row["transparency_log_included"]
            and row["append_only"]
            and row["privacy_preserving"]
            and row["fail_closed"]
            and row["revoked_or_held_blocks_release"]
            and row["revoked_or_downgraded_blocks_current_display"]
        )
        row["reliance_status_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _correction_broadcast_rows(
    ledger_input: dict[str, Any], required_channels: list[str], maximum_seconds: int
) -> list[dict[str, Any]]:
    row_map = _component_input_map(ledger_input, "correction_broadcast_rows")
    contract_hash = _declared_hash(ledger_input.get("universal_grounded_reliance_contract"))
    rows = []
    for channel in required_channels:
        item = row_map.get(channel, {})
        row = {
            "channel": channel,
            "endpoint_hash": str(item.get("endpoint_hash", "")),
            "l154_contract_hash": str(item.get("l154_contract_hash", contract_hash)),
            "status_list_hash": str(item.get("status_list_hash", "")),
            "latest_checkpoint_hash": str(item.get("latest_checkpoint_hash", "")),
            "acknowledgement_proof_hash": str(
                item.get("acknowledgement_proof_hash", "")
            ),
            "maximum_delivery_seconds": int(
                item.get("maximum_delivery_seconds", maximum_seconds) or maximum_seconds
            ),
            "subscriber_scope_hash": str(item.get("subscriber_scope_hash", "")),
            "delivered": item.get("delivered") is True,
            "machine_readable": item.get("machine_readable") is True,
            "public_or_auditor_accessible": item.get("public_or_auditor_accessible")
            is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            bool(row["endpoint_hash"])
            and row["l154_contract_hash"] == contract_hash
            and bool(row["status_list_hash"])
            and bool(row["latest_checkpoint_hash"])
            and bool(row["acknowledgement_proof_hash"])
            and row["maximum_delivery_seconds"] <= maximum_seconds
            and bool(row["subscriber_scope_hash"])
            and row["delivered"]
            and row["machine_readable"]
            and row["public_or_auditor_accessible"]
            and row["privacy_preserving"]
            and row["fail_closed"]
        )
        row["correction_broadcast_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _revalidation_rows(
    ledger_input: dict[str, Any], required_checks: list[str], maximum_interval: int
) -> list[dict[str, Any]]:
    row_map = _component_input_map(ledger_input, "revalidation_rows")
    contract_hash = _declared_hash(ledger_input.get("universal_grounded_reliance_contract"))
    rows = []
    for check_id in required_checks:
        item = row_map.get(check_id, {})
        row = {
            "check_id": check_id,
            "evidence_hash": str(item.get("evidence_hash", "")),
            "l154_contract_hash": str(item.get("l154_contract_hash", contract_hash)),
            "last_run_hash": str(item.get("last_run_hash", "")),
            "next_due_hash": str(item.get("next_due_hash", "")),
            "interval_seconds": int(
                item.get("interval_seconds", maximum_interval) or maximum_interval
            ),
            "passed": item.get("passed") is True,
            "continuous": item.get("continuous") is True,
            "writes_status_rows": item.get("writes_status_rows") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            bool(row["evidence_hash"])
            and row["l154_contract_hash"] == contract_hash
            and bool(row["last_run_hash"])
            and bool(row["next_due_hash"])
            and row["interval_seconds"] <= maximum_interval
            and row["passed"]
            and row["continuous"]
            and row["writes_status_rows"]
            and row["privacy_preserving"]
            and row["fail_closed"]
        )
        row["revalidation_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _settlement_correction_rows(
    ledger_input: dict[str, Any], required_scopes: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(ledger_input, "settlement_correction_rows")
    allocation_hash = _declared_hash(ledger_input.get("revenue_allocation_report"))
    finance_hash = _declared_hash(ledger_input.get("finance_ledger_attestation"))
    contract_hash = _declared_hash(ledger_input.get("universal_grounded_reliance_contract"))
    rows = []
    for scope in required_scopes:
        item = row_map.get(scope, {})
        row = {
            "scope": scope,
            "allocation_report_hash": str(
                item.get("allocation_report_hash", allocation_hash)
            ),
            "finance_attestation_hash": str(
                item.get("finance_attestation_hash", finance_hash)
            ),
            "l154_contract_hash": str(item.get("l154_contract_hash", contract_hash)),
            "status_list_hash": str(item.get("status_list_hash", "")),
            "affected_creator_count": int(item.get("affected_creator_count", 0) or 0),
            "affected_work_count": int(item.get("affected_work_count", 0) or 0),
            "funds_held_or_adjusted": item.get("funds_held_or_adjusted") is True,
            "finance_reconciled": item.get("finance_reconciled") is True,
            "creator_notice_sent": item.get("creator_notice_sent") is True,
            "challenge_route_available": item.get("challenge_route_available") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            row["allocation_report_hash"] == allocation_hash
            and row["finance_attestation_hash"] == finance_hash
            and row["l154_contract_hash"] == contract_hash
            and bool(row["status_list_hash"])
            and row["affected_creator_count"] > 0
            and row["affected_work_count"] > 0
            and row["funds_held_or_adjusted"]
            and row["finance_reconciled"]
            and row["creator_notice_sent"]
            and row["challenge_route_available"]
            and row["privacy_preserving"]
            and row["fail_closed"]
        )
        row["settlement_correction_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _standard_control_rows(
    ledger_input: dict[str, Any], required_controls: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(ledger_input, "standard_control_rows")
    rows = []
    for control in sorted(required_controls):
        item = row_map.get(control, {})
        row = {
            "control": control,
            "control_evidence_hash": str(item.get("control_evidence_hash", "")),
            "verifier_command": str(item.get("verifier_command", "")),
            "implementation_reference_hash": str(
                item.get("implementation_reference_hash", "")
            ),
            "implemented": item.get("implemented") is True,
            "externally_auditable": item.get("externally_auditable") is True,
            "machine_readable": item.get("machine_readable") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            bool(row["control_evidence_hash"])
            and row["verifier_command"] == "verify-universal-reliance-correction-ledger"
            and bool(row["implementation_reference_hash"])
            and row["implemented"]
            and row["externally_auditable"]
            and row["machine_readable"]
            and row["fail_closed"]
        )
        row["standard_control_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _failure_case_rows(
    ledger_input: dict[str, Any], required_cases: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(ledger_input, "failure_case_rows")
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
            and row["verifier_command"] == "verify-universal-reliance-correction-ledger"
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


def _artifact_summary(ledger_input: dict[str, Any], name: str) -> dict[str, Any]:
    artifact = ledger_input.get(name)
    return _summary(artifact if isinstance(artifact, dict) else None)


def make_universal_reliance_correction_ledger(
    ledger_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create the L155 universal reliance correction ledger artifact."""

    policy = _policy(ledger_input)
    required_artifacts = list(policy["required_core_artifacts"])
    artifact_bindings = _artifact_bindings(ledger_input, required_artifacts)
    bindings = _binding_by_name(artifact_bindings)
    status_rows = _reliance_status_rows(
        ledger_input, list(policy["required_reliance_status_types"])
    )
    broadcast_rows = _correction_broadcast_rows(
        ledger_input,
        list(policy["required_correction_broadcast_channels"]),
        int(policy["maximum_correction_delivery_seconds"]),
    )
    revalidation_rows = _revalidation_rows(
        ledger_input,
        list(policy["required_revalidation_checks"]),
        int(policy["maximum_revalidation_interval_seconds"]),
    )
    settlement_rows = _settlement_correction_rows(
        ledger_input, list(policy["required_settlement_correction_scopes"])
    )
    standard_rows = _standard_control_rows(
        ledger_input, list(policy["required_standard_controls"])
    )
    failure_rows = _failure_case_rows(
        ledger_input, list(policy["required_failure_cases"])
    )

    certification_summary = _artifact_summary(ledger_input, "certification_report")
    reliance_summary = _artifact_summary(
        ledger_input, "universal_grounded_reliance_contract"
    )
    url_health_summary = _artifact_summary(ledger_input, "citation_url_health")
    freshness_summary = _artifact_summary(ledger_input, "source_freshness_audit")
    counterevidence_summary = _artifact_summary(ledger_input, "counterevidence_report")
    force_summary = _artifact_summary(ledger_input, "evidence_force_calibration")
    delivery_summary = _artifact_summary(ledger_input, "source_footer_delivery")
    client_summary = _artifact_summary(ledger_input, "client_attribution_enforcement")
    post_release_summary = _artifact_summary(
        ledger_input, "post_release_discovery_report"
    )
    binding_summary = _artifact_summary(
        ledger_input, "output_provenance_binding_report"
    )
    allocation_summary = _artifact_summary(ledger_input, "revenue_allocation_report")
    finance_summary = _artifact_summary(ledger_input, "finance_ledger_attestation")
    publication_monitor_summary = _artifact_summary(ledger_input, "publication_monitor")
    publication_witness_summary = _artifact_summary(ledger_input, "publication_witness")
    trust_registry_summary = _artifact_summary(ledger_input, "trust_registry")
    proof_graph_summary = _artifact_summary(ledger_input, "proof_dependency_graph")

    provider_card = ledger_input.get("provider_attribution_card", {})
    integration_profile = ledger_input.get("integration_profile", {})
    discovery_manifest = ledger_input.get("discovery_manifest", {})
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

    public_projection = {
        "artifact_bindings": artifact_bindings,
        "reliance_status_rows": status_rows,
        "correction_broadcast_rows": broadcast_rows,
        "revalidation_rows": revalidation_rows,
        "settlement_correction_rows": settlement_rows,
        "standard_control_rows": standard_rows,
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
        "certification_passed_l154_or_higher": (
            certification_summary.get("status") == "passed"
            and _level_at_least(
                certification_summary.get("highest_level"), MINIMUM_RELIANCE_LEVEL
            )
        ),
        "grounded_reliance_contract_ready_l154": (
            reliance_summary.get("status") == "ready"
            and _level_at_least(
                reliance_summary.get("target_certification_level"),
                MINIMUM_RELIANCE_LEVEL,
            )
            and int(reliance_summary.get("failed_check_count", 0) or 0) == 0
        ),
        "source_url_health_continuously_checked": (
            url_health_summary.get("status") == "ready"
            and int(url_health_summary.get("fabricated_or_never_seen_url_count", 0) or 0)
            == 0
        ),
        "freshness_and_counterevidence_rechecked": (
            freshness_summary.get("status") == "ready"
            and int(freshness_summary.get("stale_dynamic_claim_count", 0) or 0) == 0
            and counterevidence_summary.get("status") == "verified"
            and int(counterevidence_summary.get("unaddressed_counterevidence_count", 0) or 0)
            == 0
        ),
        "confidence_downgrades_enforced": (
            force_summary.get("status") == "ready"
            and int(force_summary.get("over_warranted_claim_count", 0) or 0) == 0
        ),
        "source_footer_and_client_updates_enforced": (
            delivery_summary.get("status") == "ready"
            and int(delivery_summary.get("failed_check_count", 0) or 0) == 0
            and client_summary.get("status") == "ready"
            and int(client_summary.get("failed_check_count", 0) or 0) == 0
        ),
        "post_release_and_copy_binding_ready": (
            post_release_summary.get("status") == "ready"
            and binding_summary.get("status") == "ready"
        ),
        "settlement_finance_correction_ready": (
            allocation_summary.get("status") == "ready"
            and finance_summary.get("status") == "ready"
        ),
        "publication_status_infrastructure_ready": (
            publication_monitor_summary.get("status") == "ready"
            and publication_witness_summary.get("status") == "ready"
            and trust_registry_summary.get("status") == "ready"
        ),
        "all_reliance_status_rows_ready": _all_ready(status_rows),
        "all_correction_broadcast_channels_ready": _all_ready(broadcast_rows),
        "all_revalidation_checks_ready": _all_ready(revalidation_rows),
        "all_settlement_correction_scopes_ready": _all_ready(settlement_rows),
        "all_standard_controls_ready": _all_ready(standard_rows),
        "all_failure_cases_prove_blocking": _all_ready(failure_rows),
        "publication_surfaces_declared": (
            public_surfaces.get("universal_reliance_correction_ledger") is True
            or discovery.get("universal_reliance_correction_ledger_path")
            == DEFAULT_WELL_KNOWN_PATH
        ),
        "proof_graph_acyclic": (
            int(proof_graph_summary.get("cycle_node_count", 0) or 0) == 0
            and proof_graph_summary.get("status") in {"ready", "ok"}
        ),
        "privacy_preserved": (
            not private_findings
            and _private_strings_absent(public_projection, ledger_input)
        ),
    }
    failed_checks = [name for name, passed in checks.items() if passed is not True]
    failure_modes_by_check = {
        "all_required_artifacts_present": "correction_required_artifact_missing",
        "all_required_artifact_hashes_reproducible": "correction_artifact_hash_not_reproducible",
        "certification_passed_l154_or_higher": "correction_certification_below_l154",
        "grounded_reliance_contract_ready_l154": "correction_l154_contract_missing",
        "source_url_health_continuously_checked": "correction_revalidation_gap",
        "freshness_and_counterevidence_rechecked": "correction_revalidation_gap",
        "confidence_downgrades_enforced": "correction_revalidation_gap",
        "source_footer_and_client_updates_enforced": "correction_broadcast_gap",
        "post_release_and_copy_binding_ready": "correction_copy_status_gap",
        "settlement_finance_correction_ready": "correction_settlement_gap",
        "publication_status_infrastructure_ready": "correction_publication_gap",
        "all_reliance_status_rows_ready": "correction_status_gap",
        "all_correction_broadcast_channels_ready": "correction_broadcast_gap",
        "all_revalidation_checks_ready": "correction_revalidation_gap",
        "all_settlement_correction_scopes_ready": "correction_settlement_gap",
        "all_standard_controls_ready": "correction_standard_control_gap",
        "all_failure_cases_prove_blocking": "correction_negative_case_gap",
        "publication_surfaces_declared": "correction_publication_gap",
        "proof_graph_acyclic": "correction_proof_graph_cycle",
        "privacy_preserved": "correction_private_payload_leak",
    }
    failure_modes = sorted({failure_modes_by_check[name] for name in failed_checks})
    ready = not failed_checks

    ledger = {
        "reliance_correction_version": UNIVERSAL_RELIANCE_CORRECTION_LEDGER_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "reliance_correction_policy": policy,
        "artifact_bindings": artifact_bindings,
        "reliance_status_rows": status_rows,
        "correction_broadcast_rows": broadcast_rows,
        "revalidation_rows": revalidation_rows,
        "settlement_correction_rows": settlement_rows,
        "standard_control_rows": standard_rows,
        "failure_case_rows": failure_rows,
        "evidence_commitments": {
            "artifact_binding_root": artifact_bindings["artifact_binding_root"],
            "reliance_status_root": merkle_root(
                [row["reliance_status_row_hash"] for row in status_rows]
            ),
            "correction_broadcast_root": merkle_root(
                [row["correction_broadcast_row_hash"] for row in broadcast_rows]
            ),
            "revalidation_root": merkle_root(
                [row["revalidation_row_hash"] for row in revalidation_rows]
            ),
            "settlement_correction_root": merkle_root(
                [row["settlement_correction_row_hash"] for row in settlement_rows]
            ),
            "standard_control_root": merkle_root(
                [row["standard_control_row_hash"] for row in standard_rows]
            ),
            "failure_case_root": merkle_root(
                [row["failure_case_row_hash"] for row in failure_rows]
            ),
        },
        "checks": checks,
        "correction_decision": {
            "reliance_correction_ledger_authorized": ready,
            "live_reliance_status_required": True,
            "source_footer_reuse_allowed": ready,
            "copied_output_reliance_allowed": ready,
            "settlement_release_allowed": ready,
            "regulator_export_reliance_allowed": ready,
            "revoked_footer_display_allowed": False,
            "uncorrected_cache_reuse_allowed": False,
            "settlement_after_revocation_allowed": False,
            "copied_output_without_status_link_allowed": False,
            "private_payload_publication_allowed": False,
            "failure_modes": failure_modes,
        },
        "verifier_commands": [
            "verify-universal-reliance-correction-ledger",
            "verify-universal-grounded-reliance-contract",
            "verify-universal-accountability-witness-quorum",
            "verify-universal-accountability-audit-trail",
            "verify-citation-url-health",
            "verify-source-freshness-audit",
            "verify-counterevidence-report",
            "verify-source-footer-delivery",
            "verify-client-attribution-enforcement",
            "verify-output-provenance-binding-report",
            "verify-revenue-allocation-report",
            "verify-finance-ledger-attestation",
        ],
        "standards_controls": {
            "c2pa_update_manifest": "update_manifests_and_revocation_values_for_post_publication_credential_status",
            "c2pa_ocsp_revocation_status": "ocsp_style_not_revoked_revoked_or_unknown_status_for_signed_manifest_credentials",
            "w3c_vc_status_list": "bitstring_status_lists_for_portable_verifiable_status_revocation_or_suspension",
            "scitt_status_receipt": "signed_statement_receipts_for_auditable_status_registration",
            "rfc9162": "append_only_log_consistency_for_correction_status_checkpoints",
            "sigstore_rekor": "artifact_signature_transparency_for_status_entries",
            "nist_ai_rmf": "incident_response_measurement_and_monitoring_for_ai_risk_controls",
            "eu_ai_act_article_50": "transparent_machine_readable_disclosure_and_correction_for_ai_output_reliance",
            "source_urls": {
                "datadignity": "https://arxiv.org/abs/2605.05687",
                "llm_hallucinations_in_the_wild": "https://arxiv.org/abs/2605.07723",
                "reference_hallucination_detection": "https://arxiv.org/abs/2604.03173",
                "fineref": "https://ojs.aaai.org/index.php/AAAI/article/view/40547",
                "reflens": "https://doi.org/10.1609/aaai.v40i48.42361",
                "c2pa": "https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html",
                "w3c_vc_status_list": "https://www.w3.org/TR/vc-bitstring-status-list/",
                "scitt": "https://www.rfc-editor.org/rfc/rfc9943.html",
                "rfc9162": "https://www.rfc-editor.org/rfc/rfc9162.html",
                "sigstore_rekor": "https://docs.sigstore.dev/logging/overview/",
                "nist_ai_rmf": "https://www.nist.gov/itl/ai-risk-management-framework",
                "eu_ai_act_article_50": "https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50",
            },
        },
        "privacy": {
            "public_ledger_contains_raw_prompts": False,
            "public_ledger_contains_raw_outputs": False,
            "public_ledger_contains_source_text": False,
            "public_ledger_contains_tool_payloads": False,
            "public_ledger_contains_customer_or_payment_data": False,
            "hash_count_status_action_and_root_only_correction_commitments": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_reliance_level": MINIMUM_RELIANCE_LEVEL,
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
            "core_artifact_count": artifact_bindings["artifact_count"],
            "reliance_status_count": len(status_rows),
            "ready_reliance_status_count": _count(status_rows),
            "correction_broadcast_channel_count": len(broadcast_rows),
            "ready_correction_broadcast_channel_count": _count(broadcast_rows),
            "revalidation_check_count": len(revalidation_rows),
            "ready_revalidation_check_count": _count(revalidation_rows),
            "settlement_correction_scope_count": len(settlement_rows),
            "ready_settlement_correction_scope_count": _count(settlement_rows),
            "standard_control_count": len(standard_rows),
            "ready_standard_control_count": _count(standard_rows),
            "failure_case_count": len(failure_rows),
            "offline_verification_supported": True,
            "live_status_corrections_supported": ready,
            "copied_output_status_links_supported": ready,
            "creator_settlement_corrections_supported": ready,
            "regulator_export_correction_supported": ready,
            "privacy_preserved": checks["privacy_preserved"],
        },
    }
    ledger["universal_reliance_correction_ledger_hash"] = hash_payload(
        _hashable_ledger(ledger)
    )
    if signing_secret:
        ledger["signature"] = sign_payload(_hashable_ledger(ledger), signing_secret)
    return ledger


def validate_universal_reliance_correction_ledger_shape(
    ledger: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    required = (
        "reliance_correction_version",
        "issuer",
        "created_at",
        "reliance_correction_policy",
        "artifact_bindings",
        "reliance_status_rows",
        "correction_broadcast_rows",
        "revalidation_rows",
        "settlement_correction_rows",
        "standard_control_rows",
        "failure_case_rows",
        "evidence_commitments",
        "checks",
        "correction_decision",
        "verifier_commands",
        "standards_controls",
        "privacy",
        "summary",
        "universal_reliance_correction_ledger_hash",
    )
    for key in required:
        if key not in ledger:
            errors.append(f"missing universal reliance correction ledger field: {key}")
    if errors:
        return errors
    if (
        ledger.get("reliance_correction_version")
        != UNIVERSAL_RELIANCE_CORRECTION_LEDGER_VERSION
    ):
        errors.append("universal reliance correction ledger version is unsupported")
    if ledger.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal reliance correction ledger target level is not RDLLM-L155")
    if (
        ledger.get("reliance_correction_policy", {}).get("well_known_path")
        != DEFAULT_WELL_KNOWN_PATH
    ):
        errors.append("universal reliance correction ledger well-known path is invalid")
    decision = ledger.get("correction_decision", {})
    if decision.get("revoked_footer_display_allowed") is not False:
        errors.append("universal reliance correction ledger permits revoked footer display")
    if decision.get("uncorrected_cache_reuse_allowed") is not False:
        errors.append("universal reliance correction ledger permits uncorrected cache reuse")
    if decision.get("settlement_after_revocation_allowed") is not False:
        errors.append("universal reliance correction ledger permits settlement after revocation")
    if decision.get("copied_output_without_status_link_allowed") is not False:
        errors.append("universal reliance correction ledger permits copied output without status link")
    return errors


def verify_universal_reliance_correction_ledger(
    ledger: dict[str, Any],
    *,
    ledger_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L155 correction ledger artifact against private replay input."""

    errors = validate_universal_reliance_correction_ledger_shape(ledger)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_ledger(ledger))
    if expected_hash != ledger.get("universal_reliance_correction_ledger_hash"):
        errors.append("universal reliance correction ledger hash is not reproducible")

    expected = make_universal_reliance_correction_ledger(
        ledger_input,
        issuer=ledger.get("issuer", DEFAULT_ISSUER),
        created_at=ledger.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "reliance_correction_policy",
        "artifact_bindings",
        "reliance_status_rows",
        "correction_broadcast_rows",
        "revalidation_rows",
        "settlement_correction_rows",
        "standard_control_rows",
        "failure_case_rows",
        "evidence_commitments",
        "checks",
        "correction_decision",
        "verifier_commands",
        "standards_controls",
        "privacy",
        "summary",
    ):
        if expected.get(key) != ledger.get(key):
            errors.append(f"universal reliance correction ledger {key} does not match replay input")
    if (
        expected.get("universal_reliance_correction_ledger_hash")
        != ledger.get("universal_reliance_correction_ledger_hash")
    ):
        errors.append("universal reliance correction ledger hash does not match replay input")
    if signing_secret and expected.get("signature") != ledger.get("signature"):
        errors.append("universal reliance correction ledger signature is invalid")
    if ledger.get("summary", {}).get("status") != "ready":
        errors.append("universal reliance correction ledger status is not ready")
    for check, passed in ledger.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal reliance correction ledger check failed: {check}")
    if _contains_private_fields(ledger):
        errors.append("universal reliance correction ledger exposes a private field")
    return errors
