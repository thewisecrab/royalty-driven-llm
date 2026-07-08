"""Universal grounded reliance contract.

The L154 layer decides whether a provider may let users, creators, customers,
auditors, or regulators rely on an answer footer and settlement claim. L153
proves the audit trail is witnessed; L154 proves that the visible sources,
claim support, locators, freshness, confidence labels, and payout rows are
jointly grounded before the response can present them as reliable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_GROUNDED_RELIANCE_CONTRACT_VERSION = (
    "rdllm-universal-grounded-reliance-contract/v1"
)
UNIVERSAL_GROUNDED_RELIANCE_CONTRACT_SCHEMA = (
    "docs/schemas/universal_grounded_reliance_contract.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L154"
MINIMUM_WITNESS_LEVEL = "RDLLM-L153"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-grounded-reliance-contract.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "assurance_bundle",
    "proof_dependency_graph",
    "universal_accountability_witness_quorum",
    "universal_accountability_audit_trail",
    "universal_provider_wire_protocol",
    "universal_claim_provenance_envelope",
    "response_envelope",
    "answer_provenance_card",
    "source_verification_report",
    "source_confidence_report",
    "citation_footer_contract",
    "source_footer_delivery",
    "client_attribution_enforcement",
    "grounded_source_footer",
    "evidence_preview_footer",
    "evidence_locator_manifest",
    "citation_url_health",
    "answer_claim_coverage_report",
    "generation_context_closure_report",
    "evidence_sufficiency_report",
    "counterevidence_report",
    "source_freshness_audit",
    "evidence_force_calibration",
    "warranted_source_footer",
    "source_origin_lineage",
    "revenue_allocation_report",
    "finance_ledger_attestation",
)

REQUIRED_RELIANCE_CLAIMS = (
    "source_footer_is_verified",
    "claims_are_supported",
    "citations_are_materialized",
    "evidence_regions_are_bound",
    "source_freshness_is_within_policy",
    "license_and_rights_allow_display",
    "settlement_is_witnessed",
    "client_rendering_enforced",
    "privacy_preserving_public_proof",
    "regulator_export_replayable",
)

REQUIRED_FOOTER_SURFACES = (
    "answer_footer",
    "citation_footer_contract",
    "grounded_source_footer",
    "warranted_source_footer",
    "evidence_preview",
    "locator_manifest",
    "client_renderer",
    "copied_output",
)

REQUIRED_SETTLEMENT_SCOPES = (
    "creator_direct_payout",
    "unattributed_escrow",
    "rights_conflict_escrow",
    "finance_reconciliation",
    "post_correction_adjustment",
)

REQUIRED_STANDARD_CONTROLS = (
    "c2pa_content_credential_binding",
    "scitt_transparency_statement",
    "rfc9162_log_consistency",
    "rekor_artifact_transparency",
    "opentelemetry_genai_trace_binding",
    "nist_ai_rmf_traceability",
    "eu_ai_act_transparency_notice",
    "w3c_data_integrity_verifier",
)

REQUIRED_FAILURE_CASES = (
    "missing_l153_witness_quorum",
    "missing_verified_footer",
    "unsupported_claim_coverage",
    "stale_source_reliance",
    "unverifiable_locator",
    "overclaimed_confidence_label",
    "unrendered_client_footer",
    "settlement_without_reliance",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_grounded_reliance_contract_hash",
    "universal_accountability_witness_quorum_hash",
    "universal_accountability_audit_trail_hash",
    "universal_provider_wire_protocol_hash",
    "universal_claim_provenance_envelope_hash",
    "source_footer_delivery_hash",
    "client_enforcement_hash",
    "grounded_source_footer_hash",
    "evidence_preview_footer_hash",
    "evidence_locator_manifest_hash",
    "citation_url_health_hash",
    "source_freshness_audit_hash",
    "evidence_force_calibration_hash",
    "warranted_source_footer_hash",
    "source_origin_lineage_hash",
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

CONFIDENCE_LABEL_RANKS = {
    "none": 0,
    "unverified": 1,
    "located": 2,
    "supported": 3,
    "verified": 4,
    "warranted": 5,
}


def load_universal_grounded_reliance_contract_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L154 grounded reliance contract."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in contract.items()
        if key not in {"universal_grounded_reliance_contract_hash", "signature"}
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
    public_payload: dict[str, Any], contract_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in contract_input.get("private_strings", [])
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


def _component_input_map(contract_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    value = contract_input.get(key, {})
    if isinstance(value, dict):
        return {str(name): row for name, row in value.items() if isinstance(row, dict)}
    if isinstance(value, list):
        result: dict[str, dict[str, Any]] = {}
        for row in value:
            if not isinstance(row, dict):
                continue
            name = (
                row.get("claim_id")
                or row.get("surface")
                or row.get("settlement_scope")
                or row.get("control")
                or row.get("case_id")
            )
            if name:
                result[str(name)] = row
        return result
    return {}


def _policy(contract_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(contract_input.get("grounded_reliance_policy", {}))
    return {
        "profile": "rdllm-universal-grounded-reliance-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_witness_level": MINIMUM_WITNESS_LEVEL,
        "well_known_path": DEFAULT_WELL_KNOWN_PATH,
        "minimum_source_confidence": float(
            policy.get("minimum_source_confidence", 0.75) or 0.75
        ),
        "minimum_claim_confidence": float(
            policy.get("minimum_claim_confidence", 0.75) or 0.75
        ),
        "max_dynamic_source_age_seconds": int(
            policy.get("max_dynamic_source_age_seconds", 86400) or 86400
        ),
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_reliance_claims": list(
            policy.get("required_reliance_claims", REQUIRED_RELIANCE_CLAIMS)
        ),
        "required_footer_surfaces": list(
            policy.get("required_footer_surfaces", REQUIRED_FOOTER_SURFACES)
        ),
        "required_settlement_scopes": list(
            policy.get("required_settlement_scopes", REQUIRED_SETTLEMENT_SCOPES)
        ),
        "required_standard_controls": list(
            policy.get("required_standard_controls", REQUIRED_STANDARD_CONTROLS)
        ),
        "required_failure_cases": list(
            policy.get("required_failure_cases", REQUIRED_FAILURE_CASES)
        ),
        "claim_rule": "visible_or_reliable_claims_must_have_verified_source_support_and_no_unresolved_counterevidence",
        "footer_rule": "users_must_receive_visible_and_machine_readable_source_footers_with_resolvable_evidence_handles",
        "confidence_rule": "footer_labels_cannot_exceed_verified_evidence_force_and_source_confidence",
        "settlement_rule": "creator_payment_reliance_requires_source_reliance_l153_witnessing_and_finance_reconciliation",
        "privacy_rule": "public_reliance_contract_contains_hashes_counts_labels_roots_and_decisions_not_private_payloads",
    }


def _artifact_bindings(contract_input: dict[str, Any], names: list[str]) -> dict[str, Any]:
    rows = []
    for name in names:
        artifact = contract_input.get(name)
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


def _label_at_most(label: str, maximum: str) -> bool:
    return CONFIDENCE_LABEL_RANKS.get(label, -1) <= CONFIDENCE_LABEL_RANKS.get(
        maximum, -1
    )


def _reliance_claim_rows(
    contract_input: dict[str, Any], required_claims: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(contract_input, "reliance_claim_rows")
    witness_hash = _declared_hash(contract_input.get("universal_accountability_witness_quorum"))
    rows = []
    for claim_id in required_claims:
        item = row_map.get(claim_id, {})
        label = str(item.get("confidence_label", "warranted"))
        maximum_label = str(item.get("maximum_allowed_label", "warranted"))
        row = {
            "claim_id": claim_id,
            "evidence_hash": str(item.get("evidence_hash", "")),
            "witness_quorum_hash": str(item.get("witness_quorum_hash", witness_hash)),
            "controlling_artifact_hashes": list(
                item.get("controlling_artifact_hashes", [])
            ),
            "visible_source_count": int(item.get("visible_source_count", 0) or 0),
            "supported_claim_count": int(item.get("supported_claim_count", 0) or 0),
            "unsupported_claim_count": int(item.get("unsupported_claim_count", 0) or 0),
            "unresolved_counterevidence_count": int(
                item.get("unresolved_counterevidence_count", 0) or 0
            ),
            "source_confidence_floor": float(
                item.get("source_confidence_floor", 0.0) or 0.0
            ),
            "claim_confidence_floor": float(
                item.get("claim_confidence_floor", 0.0) or 0.0
            ),
            "confidence_label": label,
            "maximum_allowed_label": maximum_label,
            "verified_footer": item.get("verified_footer") is True,
            "claim_coverage_complete": item.get("claim_coverage_complete") is True,
            "factual_support_verified": item.get("factual_support_verified") is True,
            "source_locator_resolves": item.get("source_locator_resolves") is True,
            "freshness_within_policy": item.get("freshness_within_policy") is True,
            "rights_allow_display": item.get("rights_allow_display") is True,
            "relies_on_l153_witness": item.get("relies_on_l153_witness") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["label_not_overclaimed"] = _label_at_most(label, maximum_label)
        row["ready"] = (
            bool(row["evidence_hash"])
            and bool(row["witness_quorum_hash"])
            and row["witness_quorum_hash"] == witness_hash
            and len(row["controlling_artifact_hashes"]) > 0
            and row["visible_source_count"] > 0
            and row["supported_claim_count"] > 0
            and row["unsupported_claim_count"] == 0
            and row["unresolved_counterevidence_count"] == 0
            and row["source_confidence_floor"] >= 0.75
            and row["claim_confidence_floor"] >= 0.75
            and row["label_not_overclaimed"]
            and row["verified_footer"]
            and row["claim_coverage_complete"]
            and row["factual_support_verified"]
            and row["source_locator_resolves"]
            and row["freshness_within_policy"]
            and row["rights_allow_display"]
            and row["relies_on_l153_witness"]
            and row["privacy_preserving"]
            and row["fail_closed"]
        )
        row["reliance_claim_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _source_footer_reliance_rows(
    contract_input: dict[str, Any], required_surfaces: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(contract_input, "source_footer_reliance_rows")
    rows = []
    for surface in required_surfaces:
        item = row_map.get(surface, {})
        row = {
            "surface": surface,
            "surface_artifact_hash": str(item.get("surface_artifact_hash", "")),
            "renderer_hash": str(item.get("renderer_hash", "")),
            "evidence_locator_root": str(item.get("evidence_locator_root", "")),
            "delivered_source_count": int(item.get("delivered_source_count", 0) or 0),
            "delivered_claim_count": int(item.get("delivered_claim_count", 0) or 0),
            "visible_to_user": item.get("visible_to_user") is True,
            "machine_readable": item.get("machine_readable") is True,
            "source_locator_resolves": item.get("source_locator_resolves") is True,
            "evidence_preview_available": item.get("evidence_preview_available") is True,
            "confidence_label_visible": item.get("confidence_label_visible") is True,
            "copy_survival_expected": item.get("copy_survival_expected") is True,
            "client_enforced": item.get("client_enforced") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            bool(row["surface_artifact_hash"])
            and bool(row["renderer_hash"])
            and bool(row["evidence_locator_root"])
            and row["delivered_source_count"] > 0
            and row["delivered_claim_count"] > 0
            and row["visible_to_user"]
            and row["machine_readable"]
            and row["source_locator_resolves"]
            and row["evidence_preview_available"]
            and row["confidence_label_visible"]
            and row["copy_survival_expected"]
            and row["client_enforced"]
            and row["privacy_preserving"]
            and row["fail_closed"]
        )
        row["source_footer_reliance_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _settlement_reliance_rows(
    contract_input: dict[str, Any], required_scopes: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(contract_input, "settlement_reliance_rows")
    allocation_hash = _declared_hash(contract_input.get("revenue_allocation_report"))
    finance_hash = _declared_hash(contract_input.get("finance_ledger_attestation"))
    source_lineage_hash = _declared_hash(contract_input.get("source_origin_lineage"))
    witness_hash = _declared_hash(contract_input.get("universal_accountability_witness_quorum"))
    rows = []
    for scope in required_scopes:
        item = row_map.get(scope, {})
        row = {
            "settlement_scope": scope,
            "allocation_report_hash": str(
                item.get("allocation_report_hash", allocation_hash)
            ),
            "finance_attestation_hash": str(
                item.get("finance_attestation_hash", finance_hash)
            ),
            "source_lineage_hash": str(item.get("source_lineage_hash", source_lineage_hash)),
            "witness_quorum_hash": str(item.get("witness_quorum_hash", witness_hash)),
            "creator_count": int(item.get("creator_count", 0) or 0),
            "work_count": int(item.get("work_count", 0) or 0),
            "allocation_conserved": item.get("allocation_conserved") is True,
            "finance_reconciled": item.get("finance_reconciled") is True,
            "source_reliance_allowed": item.get("source_reliance_allowed") is True,
            "payout_release_allowed": item.get("payout_release_allowed") is True,
            "challenge_route_available": item.get("challenge_route_available") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            row["allocation_report_hash"] == allocation_hash
            and row["finance_attestation_hash"] == finance_hash
            and row["source_lineage_hash"] == source_lineage_hash
            and row["witness_quorum_hash"] == witness_hash
            and row["creator_count"] > 0
            and row["work_count"] > 0
            and row["allocation_conserved"]
            and row["finance_reconciled"]
            and row["source_reliance_allowed"]
            and row["payout_release_allowed"]
            and row["challenge_route_available"]
            and row["privacy_preserving"]
            and row["fail_closed"]
        )
        row["settlement_reliance_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _standard_control_rows(
    contract_input: dict[str, Any], required_controls: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(contract_input, "standard_control_rows")
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
            and row["verifier_command"] == "verify-universal-grounded-reliance-contract"
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
    contract_input: dict[str, Any], required_cases: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(contract_input, "failure_case_rows")
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
            and row["verifier_command"] == "verify-universal-grounded-reliance-contract"
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


def _artifact_summary(contract_input: dict[str, Any], name: str) -> dict[str, Any]:
    artifact = contract_input.get(name)
    return _summary(artifact if isinstance(artifact, dict) else None)


def make_universal_grounded_reliance_contract(
    contract_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create the L154 universal grounded reliance contract artifact."""

    policy = _policy(contract_input)
    required_artifacts = list(policy["required_core_artifacts"])
    artifact_bindings = _artifact_bindings(contract_input, required_artifacts)
    bindings = _binding_by_name(artifact_bindings)
    reliance_rows = _reliance_claim_rows(
        contract_input, list(policy["required_reliance_claims"])
    )
    footer_rows = _source_footer_reliance_rows(
        contract_input, list(policy["required_footer_surfaces"])
    )
    settlement_rows = _settlement_reliance_rows(
        contract_input, list(policy["required_settlement_scopes"])
    )
    standard_rows = _standard_control_rows(
        contract_input, list(policy["required_standard_controls"])
    )
    failure_rows = _failure_case_rows(
        contract_input, list(policy["required_failure_cases"])
    )

    certification_summary = _artifact_summary(contract_input, "certification_report")
    witness_summary = _artifact_summary(
        contract_input, "universal_accountability_witness_quorum"
    )
    source_verification_summary = _artifact_summary(
        contract_input, "source_verification_report"
    )
    source_confidence_summary = _artifact_summary(
        contract_input, "source_confidence_report"
    )
    citation_footer_summary = _artifact_summary(
        contract_input, "citation_footer_contract"
    )
    delivery_summary = _artifact_summary(contract_input, "source_footer_delivery")
    client_summary = _artifact_summary(contract_input, "client_attribution_enforcement")
    coverage_summary = _artifact_summary(
        contract_input, "answer_claim_coverage_report"
    )
    closure_summary = _artifact_summary(
        contract_input, "generation_context_closure_report"
    )
    sufficiency_summary = _artifact_summary(
        contract_input, "evidence_sufficiency_report"
    )
    counterevidence_summary = _artifact_summary(contract_input, "counterevidence_report")
    freshness_summary = _artifact_summary(contract_input, "source_freshness_audit")
    force_summary = _artifact_summary(contract_input, "evidence_force_calibration")
    warranted_summary = _artifact_summary(contract_input, "warranted_source_footer")
    origin_summary = _artifact_summary(contract_input, "source_origin_lineage")
    locator_summary = _artifact_summary(contract_input, "evidence_locator_manifest")
    url_health_summary = _artifact_summary(contract_input, "citation_url_health")
    allocation_summary = _artifact_summary(contract_input, "revenue_allocation_report")
    finance_summary = _artifact_summary(contract_input, "finance_ledger_attestation")
    proof_graph_summary = _artifact_summary(contract_input, "proof_dependency_graph")

    provider_card = contract_input.get("provider_attribution_card", {})
    integration_profile = contract_input.get("integration_profile", {})
    discovery_manifest = contract_input.get("discovery_manifest", {})
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
        "reliance_claim_rows": reliance_rows,
        "source_footer_reliance_rows": footer_rows,
        "settlement_reliance_rows": settlement_rows,
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
        "certification_passed_l153_or_higher": (
            certification_summary.get("status") == "passed"
            and _level_at_least(
                certification_summary.get("highest_level"), MINIMUM_WITNESS_LEVEL
            )
        ),
        "witness_quorum_ready_l153": (
            witness_summary.get("status") == "ready"
            and _level_at_least(
                witness_summary.get("target_certification_level"), MINIMUM_WITNESS_LEVEL
            )
            and int(witness_summary.get("failed_check_count", 0) or 0) == 0
            and int(witness_summary.get("independent_ready_witness_count", 0) or 0)
            >= int(witness_summary.get("minimum_independent_witnesses", 0) or 0)
        ),
        "source_verification_ready": (
            source_verification_summary.get("status") == "verified"
            and int(source_verification_summary.get("unresolved_source_count", 0) or 0)
            == 0
            and int(
                source_verification_summary.get(
                    "unverified_supported_claim_count", 0
                )
                or 0
            )
            == 0
        ),
        "source_confidence_ready": (
            source_confidence_summary.get("status") == "verified"
            and float(
                source_confidence_summary.get("minimum_source_confidence", 0.0) or 0.0
            )
            >= float(policy["minimum_source_confidence"])
            and float(
                source_confidence_summary.get("minimum_claim_confidence", 0.0) or 0.0
            )
            >= float(policy["minimum_claim_confidence"])
            and int(source_confidence_summary.get("hallucination_issue_count", 0) or 0)
            == 0
        ),
        "citation_footer_contract_ready": (
            citation_footer_summary.get("status") == "verified"
            and citation_footer_summary.get("source_footer_rendering_required") is True
            and citation_footer_summary.get("display_contract_verification_supported")
            is True
        ),
        "source_footer_delivery_ready": (
            delivery_summary.get("status") == "ready"
            and int(delivery_summary.get("failed_check_count", 0) or 0) == 0
            and delivery_summary.get("grounded_footer_delivery_enforced") is True
        ),
        "client_rendering_enforced": (
            client_summary.get("status") == "ready"
            and int(client_summary.get("failed_check_count", 0) or 0) == 0
            and client_summary.get("client_enforcement_ready") is True
        ),
        "claim_coverage_complete": (
            coverage_summary.get("status") == "verified"
            and coverage_summary.get("all_answer_claims_covered") is True
            and int(coverage_summary.get("unsupported_unit_count", 0) or 0) == 0
        ),
        "context_closure_complete": (
            closure_summary.get("status") == "verified"
            and closure_summary.get("all_supported_claims_in_generation_context") is True
            and int(closure_summary.get("missing_context_claim_count", 0) or 0) == 0
        ),
        "evidence_sufficiency_complete": (
            sufficiency_summary.get("status") == "verified"
            and sufficiency_summary.get("all_claims_have_minimal_sufficient_evidence")
            is True
            and int(sufficiency_summary.get("issue_count", 0) or 0) == 0
        ),
        "counterevidence_adjudicated": (
            counterevidence_summary.get("status") == "verified"
            and counterevidence_summary.get("all_claims_counterevidence_adjudicated")
            is True
            and int(counterevidence_summary.get("unaddressed_counterevidence_count", 0) or 0)
            == 0
        ),
        "source_freshness_ready": (
            freshness_summary.get("status") == "ready"
            and int(freshness_summary.get("stale_dynamic_claim_count", 0) or 0) == 0
        ),
        "evidence_force_calibrated": (
            force_summary.get("status") == "ready"
            and int(force_summary.get("over_warranted_claim_count", 0) or 0) == 0
            and int(
                force_summary.get("uncalibrated_verified_footer_claim_count", 0) or 0
            )
            == 0
        ),
        "warranted_footer_ready": (
            warranted_summary.get("status") == "ready"
            and int(warranted_summary.get("failed_check_count", 0) or 0) == 0
            and warranted_summary.get("user_visible_warrant_labels_supported") is True
        ),
        "source_origin_lineage_ready": (
            origin_summary.get("status") == "ready"
            and int(origin_summary.get("failed_check_count", 0) or 0) == 0
            and int(origin_summary.get("unknown_origin_source_count", 0) or 0) == 0
            and int(origin_summary.get("origin_review_escrow_source_count", 0) or 0)
            == 0
        ),
        "evidence_locator_ready": (
            locator_summary.get("status") == "ready"
            and int(locator_summary.get("failed_check_count", 0) or 0) == 0
            and locator_summary.get("exact_passage_resolution_supported") is True
        ),
        "citation_url_health_ready": (
            url_health_summary.get("status") == "ready"
            and int(url_health_summary.get("unverified_url_count", 0) or 0) == 0
            and int(url_health_summary.get("fabricated_or_never_seen_url_count", 0) or 0)
            == 0
        ),
        "settlement_finance_ready": (
            allocation_summary.get("status") == "ready"
            and finance_summary.get("status") == "ready"
            and str(allocation_summary.get("unallocated_revenue_total", "0.000000"))
            == "0.000000"
            and int(finance_summary.get("unbacked_allocation_source_count", 0) or 0)
            == 0
        ),
        "all_reliance_claims_ready": _all_ready(reliance_rows),
        "all_source_footer_surfaces_ready": _all_ready(footer_rows),
        "all_settlement_scopes_ready": _all_ready(settlement_rows),
        "all_standard_controls_ready": _all_ready(standard_rows),
        "all_failure_cases_prove_blocking": _all_ready(failure_rows),
        "publication_surfaces_declared": (
            public_surfaces.get("universal_grounded_reliance_contract") is True
            or discovery.get("universal_grounded_reliance_contract_path")
            == DEFAULT_WELL_KNOWN_PATH
        ),
        "proof_graph_acyclic": (
            int(proof_graph_summary.get("cycle_node_count", 0) or 0) == 0
            and proof_graph_summary.get("status") in {"ready", "ok"}
        ),
        "privacy_preserved": (
            not private_findings
            and _private_strings_absent(public_projection, contract_input)
        ),
    }
    failed_checks = [name for name, passed in checks.items() if passed is not True]
    failure_modes_by_check = {
        "all_required_artifacts_present": "reliance_required_artifact_missing",
        "all_required_artifact_hashes_reproducible": "reliance_artifact_hash_not_reproducible",
        "certification_passed_l153_or_higher": "reliance_certification_below_l153",
        "witness_quorum_ready_l153": "reliance_l153_witness_missing",
        "source_verification_ready": "reliance_source_verification_gap",
        "source_confidence_ready": "reliance_confidence_gap",
        "citation_footer_contract_ready": "reliance_footer_gap",
        "source_footer_delivery_ready": "reliance_footer_gap",
        "client_rendering_enforced": "reliance_client_render_gap",
        "claim_coverage_complete": "reliance_claim_gap",
        "context_closure_complete": "reliance_context_gap",
        "evidence_sufficiency_complete": "reliance_evidence_gap",
        "counterevidence_adjudicated": "reliance_counterevidence_gap",
        "source_freshness_ready": "reliance_freshness_gap",
        "evidence_force_calibrated": "reliance_label_overclaim",
        "warranted_footer_ready": "reliance_label_gap",
        "source_origin_lineage_ready": "reliance_origin_gap",
        "evidence_locator_ready": "reliance_locator_gap",
        "citation_url_health_ready": "reliance_locator_gap",
        "settlement_finance_ready": "reliance_settlement_gap",
        "all_reliance_claims_ready": "reliance_claim_gap",
        "all_source_footer_surfaces_ready": "reliance_footer_gap",
        "all_settlement_scopes_ready": "reliance_settlement_gap",
        "all_standard_controls_ready": "reliance_standard_control_gap",
        "all_failure_cases_prove_blocking": "reliance_negative_case_gap",
        "publication_surfaces_declared": "reliance_publication_gap",
        "proof_graph_acyclic": "reliance_proof_graph_cycle",
        "privacy_preserved": "reliance_private_payload_leak",
    }
    failure_modes = sorted({failure_modes_by_check[name] for name in failed_checks})
    ready = not failed_checks

    contract = {
        "grounded_reliance_version": UNIVERSAL_GROUNDED_RELIANCE_CONTRACT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "grounded_reliance_policy": policy,
        "artifact_bindings": artifact_bindings,
        "reliance_claim_rows": reliance_rows,
        "source_footer_reliance_rows": footer_rows,
        "settlement_reliance_rows": settlement_rows,
        "standard_control_rows": standard_rows,
        "failure_case_rows": failure_rows,
        "evidence_commitments": {
            "artifact_binding_root": artifact_bindings["artifact_binding_root"],
            "reliance_claim_root": merkle_root(
                [row["reliance_claim_row_hash"] for row in reliance_rows]
            ),
            "source_footer_reliance_root": merkle_root(
                [row["source_footer_reliance_row_hash"] for row in footer_rows]
            ),
            "settlement_reliance_root": merkle_root(
                [row["settlement_reliance_row_hash"] for row in settlement_rows]
            ),
            "standard_control_root": merkle_root(
                [row["standard_control_row_hash"] for row in standard_rows]
            ),
            "failure_case_root": merkle_root(
                [row["failure_case_row_hash"] for row in failure_rows]
            ),
        },
        "checks": checks,
        "reliance_decision": {
            "grounded_reliance_contract_authorized": ready,
            "source_footer_reliance_allowed": ready,
            "creator_settlement_reliance_allowed": ready,
            "customer_procurement_reliance_allowed": ready,
            "regulator_export_reliance_allowed": ready,
            "unsupported_reliance_claim_allowed": False,
            "unverified_source_footer_allowed": False,
            "posthoc_citation_substitution_allowed": False,
            "unwitnessed_settlement_reliance_allowed": False,
            "failure_modes": failure_modes,
        },
        "verifier_commands": [
            "verify-universal-grounded-reliance-contract",
            "verify-universal-accountability-witness-quorum",
            "verify-universal-accountability-audit-trail",
            "verify-universal-provider-wire-protocol",
            "verify-universal-claim-provenance-envelope",
            "verify-source-footer-delivery",
            "verify-client-attribution-enforcement",
            "verify-citation-url-health",
            "verify-evidence-locator-manifest",
            "verify-revenue-allocation-report",
            "verify-finance-ledger-attestation",
        ],
        "standards_controls": {
            "c2pa": "content_credentials_style_signed_provenance_for_source_footer_and_generated_output_binding",
            "scitt": "signed_transparency_statements_for_reliance_contract_registration",
            "rfc9162": "append_only_log_inclusion_and_consistency_for_public_reliance_roots",
            "sigstore_rekor": "artifact_signature_transparency_for_public_contracts",
            "opentelemetry_genai": "trace_context_binding_for_retrieval_tool_and_generation_events",
            "nist_ai_rmf": "traceability_and_measurement_controls_for_trustworthy_ai_risk_management",
            "eu_ai_act_article_50": "machine_readable_and_clear_transparency_for_generated_text_and_content",
            "w3c_data_integrity": "portable_verifier_model_for_signed_json_ld_style_proof_objects",
            "source_urls": {
                "datadignity": "https://arxiv.org/abs/2605.05687",
                "cited_but_not_verified": "https://arxiv.org/abs/2605.06635",
                "reflens": "https://doi.org/10.1609/aaai.v40i48.42361",
                "attribution_crisis": "https://doi.org/10.1017/dap.2026.10064",
                "c2pa": "https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html",
                "scitt": "https://www.rfc-editor.org/rfc/rfc9943.html",
                "rfc9162": "https://www.rfc-editor.org/rfc/rfc9162.html",
                "nist_ai_rmf": "https://www.nist.gov/itl/ai-risk-management-framework",
                "eu_ai_act_article_50": "https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50",
                "openai_content_provenance": "https://openai.com/index/advancing-content-provenance/",
            },
        },
        "privacy": {
            "public_contract_contains_raw_prompts": False,
            "public_contract_contains_raw_outputs": False,
            "public_contract_contains_source_text": False,
            "public_contract_contains_tool_payloads": False,
            "public_contract_contains_customer_or_payment_data": False,
            "hash_count_label_and_root_only_reliance_commitments": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_witness_level": MINIMUM_WITNESS_LEVEL,
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
            "core_artifact_count": artifact_bindings["artifact_count"],
            "reliance_claim_count": len(reliance_rows),
            "ready_reliance_claim_count": _count(reliance_rows),
            "source_footer_surface_count": len(footer_rows),
            "ready_source_footer_surface_count": _count(footer_rows),
            "settlement_scope_count": len(settlement_rows),
            "ready_settlement_scope_count": _count(settlement_rows),
            "standard_control_count": len(standard_rows),
            "ready_standard_control_count": _count(standard_rows),
            "failure_case_count": len(failure_rows),
            "offline_verification_supported": True,
            "source_footer_user_reliance_supported": ready,
            "creator_settlement_reliance_supported": ready,
            "regulator_export_reliance_supported": ready,
            "privacy_preserved": checks["privacy_preserved"],
        },
    }
    contract["universal_grounded_reliance_contract_hash"] = hash_payload(
        _hashable_contract(contract)
    )
    if signing_secret:
        contract["signature"] = sign_payload(_hashable_contract(contract), signing_secret)
    return contract


def validate_universal_grounded_reliance_contract_shape(
    contract: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    required = (
        "grounded_reliance_version",
        "issuer",
        "created_at",
        "grounded_reliance_policy",
        "artifact_bindings",
        "reliance_claim_rows",
        "source_footer_reliance_rows",
        "settlement_reliance_rows",
        "standard_control_rows",
        "failure_case_rows",
        "evidence_commitments",
        "checks",
        "reliance_decision",
        "verifier_commands",
        "standards_controls",
        "privacy",
        "summary",
        "universal_grounded_reliance_contract_hash",
    )
    for key in required:
        if key not in contract:
            errors.append(f"missing universal grounded reliance contract field: {key}")
    if errors:
        return errors
    if (
        contract.get("grounded_reliance_version")
        != UNIVERSAL_GROUNDED_RELIANCE_CONTRACT_VERSION
    ):
        errors.append("universal grounded reliance contract version is unsupported")
    if contract.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal grounded reliance contract target level is not RDLLM-L154")
    if (
        contract.get("grounded_reliance_policy", {}).get("well_known_path")
        != DEFAULT_WELL_KNOWN_PATH
    ):
        errors.append("universal grounded reliance contract well-known path is invalid")
    if contract.get("reliance_decision", {}).get("unsupported_reliance_claim_allowed") is not False:
        errors.append("universal grounded reliance contract permits unsupported reliance claims")
    if contract.get("reliance_decision", {}).get("unverified_source_footer_allowed") is not False:
        errors.append("universal grounded reliance contract permits unverified source footers")
    if contract.get("reliance_decision", {}).get("posthoc_citation_substitution_allowed") is not False:
        errors.append("universal grounded reliance contract permits posthoc citation substitution")
    if contract.get("reliance_decision", {}).get("unwitnessed_settlement_reliance_allowed") is not False:
        errors.append("universal grounded reliance contract permits unwitnessed settlement reliance")
    return errors


def verify_universal_grounded_reliance_contract(
    contract: dict[str, Any],
    *,
    contract_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L154 reliance contract artifact against private replay input."""

    errors = validate_universal_grounded_reliance_contract_shape(contract)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_contract(contract))
    if expected_hash != contract.get("universal_grounded_reliance_contract_hash"):
        errors.append("universal grounded reliance contract hash is not reproducible")

    expected = make_universal_grounded_reliance_contract(
        contract_input,
        issuer=contract.get("issuer", DEFAULT_ISSUER),
        created_at=contract.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "grounded_reliance_policy",
        "artifact_bindings",
        "reliance_claim_rows",
        "source_footer_reliance_rows",
        "settlement_reliance_rows",
        "standard_control_rows",
        "failure_case_rows",
        "evidence_commitments",
        "checks",
        "reliance_decision",
        "verifier_commands",
        "standards_controls",
        "privacy",
        "summary",
    ):
        if expected.get(key) != contract.get(key):
            errors.append(f"universal grounded reliance contract {key} does not match replay input")
    if (
        expected.get("universal_grounded_reliance_contract_hash")
        != contract.get("universal_grounded_reliance_contract_hash")
    ):
        errors.append("universal grounded reliance contract hash does not match replay input")
    if signing_secret and expected.get("signature") != contract.get("signature"):
        errors.append("universal grounded reliance contract signature is invalid")
    if contract.get("summary", {}).get("status") != "ready":
        errors.append("universal grounded reliance contract status is not ready")
    for check, passed in contract.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal grounded reliance contract check failed: {check}")
    if _contains_private_fields(contract):
        errors.append("universal grounded reliance contract exposes a private field")
    return errors
