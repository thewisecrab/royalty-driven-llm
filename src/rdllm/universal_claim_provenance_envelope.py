"""Universal claim provenance envelope.

The L150 layer makes attribution generation-time, not post-hoc. It requires each
displayed answer claim or sentence to carry a verified provenance record that
binds support relation, source proof, visible footer row, exact evidence region,
locator health, and settlement eligibility before display or payout.
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

UNIVERSAL_CLAIM_PROVENANCE_ENVELOPE_VERSION = (
    "rdllm-universal-claim-provenance-envelope/v1"
)
UNIVERSAL_CLAIM_PROVENANCE_ENVELOPE_SCHEMA = (
    "docs/schemas/universal_claim_provenance_envelope.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L150"
MINIMUM_RUNTIME_LEVEL = "RDLLM-L149"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-claim-provenance-envelope.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "assurance_bundle",
    "proof_dependency_graph",
    "universal_runtime_conformance_receipt",
    "universal_composite_rdllm_profile",
    "universal_emission_enforcement_gateway",
    "universal_rdllm_root",
    "response_envelope",
    "proof_carrying_response",
    "serving_gateway_report",
    "grounded_source_footer",
    "source_footer_delivery",
    "client_attribution_enforcement",
    "claim_source_attribution_report",
    "evidence_region_binding_report",
    "deep_research_citation_audit",
    "citation_identity_report",
    "evidence_locator_manifest",
    "citation_url_health",
    "source_access_lease_report",
    "agent_tool_attribution_ledger",
    "conversation_attribution_ledger",
    "revenue_allocation_report",
    "finance_ledger_attestation",
    "trust_registry",
)

REQUIRED_SUPPORT_RELATIONS = (
    "quotation",
    "compression",
    "inference",
    "retrieval",
    "tool_observation",
    "conversation_memory",
    "parametric_memory",
    "residual_corpus_value",
)

REQUIRED_RENDER_SURFACES = (
    "api_json",
    "markdown",
    "html",
    "streaming_chunk",
    "mobile_client",
    "export_copy",
)

REQUIRED_FAILURE_CASES = (
    "missing_claim_provenance_record",
    "posthoc_citation_only",
    "unsupported_generated_claim",
    "support_relation_mismatch",
    "footer_row_stripped",
    "fabricated_locator",
    "unresolved_citation_identity",
    "unbound_evidence_region",
    "tool_observation_unlinked",
    "settlement_without_verified_claim_support",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_claim_provenance_envelope_hash",
    "universal_runtime_conformance_receipt_hash",
    "universal_composite_rdllm_profile_hash",
    "universal_emission_enforcement_gateway_hash",
    "universal_rdllm_root_hash",
    "source_footer_delivery_hash",
    "grounded_source_footer_hash",
    "client_enforcement_hash",
    "claim_source_attribution_hash",
    "citation_identity_hash",
    "binding_report_hash",
    "deep_research_citation_audit_hash",
    "citation_url_health_hash",
    "evidence_locator_manifest_hash",
    "source_access_lease_hash",
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
    "claim_text",
    "sentence_text",
    "source_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
    "tool_payload",
    "raw_tool_output",
    "raw_native_response",
    "customer_id",
    "customer_email",
    "billing_record",
    "bank_account",
    "tax_id",
    "access_token",
    "api_key",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_claim_provenance_envelope_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L150 claim provenance envelope."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in envelope.items()
        if key not in {"universal_claim_provenance_envelope_hash", "signature"}
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
    public_payload: dict[str, Any], envelope_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in envelope_input.get("private_strings", [])
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
    envelope_input: dict[str, Any], key: str
) -> dict[str, dict[str, Any]]:
    value = envelope_input.get(key, {})
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
                or row.get("case_id")
                or row.get("relation")
            )
            if name:
                result[str(name)] = row
        return result
    return {}


def _policy(envelope_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(envelope_input.get("claim_provenance_policy", {}))
    return {
        "profile": "rdllm-universal-claim-provenance-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_runtime_level": MINIMUM_RUNTIME_LEVEL,
        "well_known_path": DEFAULT_WELL_KNOWN_PATH,
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_support_relations": list(
            policy.get("required_support_relations", REQUIRED_SUPPORT_RELATIONS)
        ),
        "required_render_surfaces": list(
            policy.get("required_render_surfaces", REQUIRED_RENDER_SURFACES)
        ),
        "required_failure_cases": list(
            policy.get("required_failure_cases", REQUIRED_FAILURE_CASES)
        ),
        "generation_rule": "no_generated_claim_without_generated_provenance_record",
        "footer_rule": "no_visible_claim_without_visible_verified_footer_row",
        "relation_rule": "support_relation_must_be_declared_and_verified_before_display",
        "tool_rule": "tool_observations_must_bind_to_claims_not_only_to_trajectory_logs",
        "settlement_rule": "no_claim_support_no_direct_settlement",
        "privacy_rule": "public_envelope_contains_hashes_relations_counts_and_handles_not_private_text",
    }


def _artifact_bindings(envelope_input: dict[str, Any], names: list[str]) -> dict[str, Any]:
    rows = []
    for name in names:
        artifact = envelope_input.get(name)
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


def _claim_provenance_rows(
    envelope_input: dict[str, Any], required_relations: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(envelope_input, "claim_provenance_rows")
    rows = []
    for claim_id in sorted(row_map):
        item = row_map[claim_id]
        row = {
            "claim_id": claim_id,
            "claim_hash": str(item.get("claim_hash", "")),
            "response_segment_hash": str(item.get("response_segment_hash", "")),
            "provenance_record_hash": str(item.get("provenance_record_hash", "")),
            "support_relation": str(item.get("support_relation", "")),
            "source_id_hash": str(item.get("source_id_hash", "")),
            "source_proof_hash": str(item.get("source_proof_hash", "")),
            "tool_or_memory_trace_hash": str(
                item.get("tool_or_memory_trace_hash", "")
            ),
            "footer_row_hash": str(item.get("footer_row_hash", "")),
            "evidence_region_hash": str(item.get("evidence_region_hash", "")),
            "citation_identity_hash": str(item.get("citation_identity_hash", "")),
            "locator_hash": str(item.get("locator_hash", "")),
            "payout_basis_hash": str(item.get("payout_basis_hash", "")),
            "settlement_meter_hash": str(item.get("settlement_meter_hash", "")),
            "generated_with_provenance": item.get("generated_with_provenance")
            is True,
            "support_verified": item.get("support_verified") is True,
            "relation_verified": item.get("relation_verified") is True,
            "footer_visible": item.get("footer_visible") is True,
            "locator_resolvable": item.get("locator_resolvable") is True,
            "settlement_eligible": item.get("settlement_eligible") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
        }
        row["ready"] = (
            bool(row["claim_hash"])
            and bool(row["response_segment_hash"])
            and bool(row["provenance_record_hash"])
            and row["support_relation"] in required_relations
            and bool(row["source_id_hash"])
            and bool(row["source_proof_hash"])
            and bool(row["tool_or_memory_trace_hash"])
            and bool(row["footer_row_hash"])
            and bool(row["evidence_region_hash"])
            and bool(row["citation_identity_hash"])
            and bool(row["locator_hash"])
            and bool(row["payout_basis_hash"])
            and bool(row["settlement_meter_hash"])
            and row["generated_with_provenance"]
            and row["support_verified"]
            and row["relation_verified"]
            and row["footer_visible"]
            and row["locator_resolvable"]
            and row["settlement_eligible"]
            and row["privacy_preserving"]
        )
        row["claim_provenance_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _render_surface_rows(
    envelope_input: dict[str, Any], required_surfaces: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(envelope_input, "render_surface_rows")
    rows = []
    for surface in sorted(required_surfaces):
        item = row_map.get(surface, {})
        row = {
            "surface": surface,
            "response_envelope_hash": str(item.get("response_envelope_hash", "")),
            "client_enforcement_hash": str(item.get("client_enforcement_hash", "")),
            "footer_render_hash": str(item.get("footer_render_hash", "")),
            "claim_provenance_root": str(item.get("claim_provenance_root", "")),
            "proof_download_hash": str(item.get("proof_download_hash", "")),
            "display_test_hash": str(item.get("display_test_hash", "")),
            "visible_source_footer": item.get("visible_source_footer") is True,
            "claim_provenance_downloadable": item.get(
                "claim_provenance_downloadable"
            )
            is True,
            "blocks_on_missing_provenance": item.get(
                "blocks_on_missing_provenance"
            )
            is True,
            "blocks_on_unsupported_claim": item.get(
                "blocks_on_unsupported_claim"
            )
            is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
        }
        row["ready"] = (
            bool(row["response_envelope_hash"])
            and bool(row["client_enforcement_hash"])
            and bool(row["footer_render_hash"])
            and bool(row["claim_provenance_root"])
            and bool(row["proof_download_hash"])
            and bool(row["display_test_hash"])
            and row["visible_source_footer"]
            and row["claim_provenance_downloadable"]
            and row["blocks_on_missing_provenance"]
            and row["blocks_on_unsupported_claim"]
            and row["privacy_preserving"]
        )
        row["render_surface_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _failure_case_rows(
    envelope_input: dict[str, Any], required_cases: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(envelope_input, "failure_case_rows")
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
            and row["verifier_command"]
            == "verify-universal-claim-provenance-envelope"
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


def _artifact_summary(envelope_input: dict[str, Any], name: str) -> dict[str, Any]:
    artifact = envelope_input.get(name)
    return _summary(artifact if isinstance(artifact, dict) else None)


def make_universal_claim_provenance_envelope(
    envelope_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create the L150 universal claim provenance envelope."""

    policy = _policy(envelope_input)
    required_artifacts = list(policy["required_core_artifacts"])
    required_relations = list(policy["required_support_relations"])
    artifact_bindings = _artifact_bindings(envelope_input, required_artifacts)
    bindings = _binding_by_name(artifact_bindings)
    claim_rows = _claim_provenance_rows(envelope_input, required_relations)
    claim_root = merkle_root([row["claim_provenance_row_hash"] for row in claim_rows])
    render_rows = _render_surface_rows(
        envelope_input, list(policy["required_render_surfaces"])
    )
    failure_rows = _failure_case_rows(
        envelope_input, list(policy["required_failure_cases"])
    )

    certification_summary = _artifact_summary(envelope_input, "certification_report")
    runtime_summary = _artifact_summary(
        envelope_input, "universal_runtime_conformance_receipt"
    )
    response_summary = _artifact_summary(envelope_input, "response_envelope")
    proof_summary = _artifact_summary(envelope_input, "proof_carrying_response")
    serving_summary = _artifact_summary(envelope_input, "serving_gateway_report")
    footer_summary = _artifact_summary(envelope_input, "source_footer_delivery")
    grounded_footer_summary = _artifact_summary(envelope_input, "grounded_source_footer")
    client_summary = _artifact_summary(envelope_input, "client_attribution_enforcement")
    claim_source_summary = _artifact_summary(
        envelope_input, "claim_source_attribution_report"
    )
    region_summary = _artifact_summary(
        envelope_input, "evidence_region_binding_report"
    )
    deep_research_summary = _artifact_summary(
        envelope_input, "deep_research_citation_audit"
    )
    citation_identity_summary = _artifact_summary(
        envelope_input, "citation_identity_report"
    )
    locator_summary = _artifact_summary(envelope_input, "evidence_locator_manifest")
    url_health_summary = _artifact_summary(envelope_input, "citation_url_health")
    tool_summary = _artifact_summary(envelope_input, "agent_tool_attribution_ledger")
    conversation_summary = _artifact_summary(
        envelope_input, "conversation_attribution_ledger"
    )
    finance_summary = _artifact_summary(envelope_input, "finance_ledger_attestation")
    proof_graph_summary = _artifact_summary(envelope_input, "proof_dependency_graph")

    provider_card = envelope_input.get("provider_attribution_card", {})
    integration_profile = envelope_input.get("integration_profile", {})
    discovery_manifest = envelope_input.get("discovery_manifest", {})
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

    relation_coverage = {
        relation: any(
            row.get("support_relation") == relation and row.get("ready") is True
            for row in claim_rows
        )
        for relation in required_relations
    }

    public_projection = {
        "artifact_bindings": artifact_bindings,
        "claim_provenance_rows": claim_rows,
        "render_surface_rows": render_rows,
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
        "certification_passed_l149_or_higher": (
            certification_summary.get("status") == "passed"
            and _level_at_least(
                certification_summary.get("highest_level"), MINIMUM_RUNTIME_LEVEL
            )
        ),
        "runtime_conformance_ready_l149": (
            runtime_summary.get("status") == "ready"
            and _level_at_least(
                runtime_summary.get("target_certification_level"),
                MINIMUM_RUNTIME_LEVEL,
            )
            and int(runtime_summary.get("failed_check_count", 0) or 0) == 0
        ),
        "response_delivery_stack_ready": (
            response_summary.get("status") in {"ready", "verified"}
            and proof_summary.get("status") in {"ready", "released"}
            and serving_summary.get("status") in {"ready", "served"}
            and footer_summary.get("status") == "ready"
            and grounded_footer_summary.get("status") == "ready"
            and client_summary.get("status") == "ready"
        ),
        "claim_source_stack_ready": (
            claim_source_summary.get("status") in {"ready", "verified"}
            and region_summary.get("status") in {"ready", "verified"}
            and deep_research_summary.get("status") in {"ready", "passed", "verified"}
            and citation_identity_summary.get("status") in {"ready", "verified"}
            and locator_summary.get("status") in {"ready", "verified"}
            and url_health_summary.get("status") in {"ready", "verified"}
        ),
        "tool_and_memory_provenance_ready": (
            tool_summary.get("status") in {"ready", "bound", "verified"}
            and conversation_summary.get("status")
            in {"ready", "continued", "verified"}
        ),
        "settlement_meter_ready": (
            finance_summary.get("status") in {"ready", "attested", "verified"}
            and int(finance_summary.get("failed_check_count", 0) or 0) == 0
        ),
        "all_claim_provenance_rows_ready": _all_ready(claim_rows),
        "all_required_support_relations_covered": all(relation_coverage.values()),
        "all_render_surfaces_ready": _all_ready(render_rows),
        "all_failure_cases_prove_blocking": _all_ready(failure_rows),
        "claim_provenance_publication_declared": (
            public_surfaces.get("universal_claim_provenance_envelope") is True
            or discovery.get("universal_claim_provenance_envelope_path")
            == DEFAULT_WELL_KNOWN_PATH
        ),
        "proof_graph_acyclic": (
            int(proof_graph_summary.get("cycle_node_count", 0) or 0) == 0
            and proof_graph_summary.get("status") in {"ready", "ok"}
        ),
        "privacy_preserved": (
            not private_findings
            and _private_strings_absent(public_projection, envelope_input)
        ),
    }

    failed_checks = [name for name, passed in checks.items() if passed is not True]
    failure_modes_by_check = {
        "all_required_artifacts_present": "claim_provenance_required_artifact_missing",
        "all_required_artifact_hashes_reproducible": "claim_provenance_artifact_hash_not_reproducible",
        "certification_passed_l149_or_higher": "claim_provenance_certification_below_l149",
        "runtime_conformance_ready_l149": "claim_provenance_runtime_not_ready",
        "response_delivery_stack_ready": "claim_provenance_response_delivery_gap",
        "claim_source_stack_ready": "claim_provenance_source_proof_gap",
        "tool_and_memory_provenance_ready": "claim_provenance_tool_or_memory_gap",
        "settlement_meter_ready": "claim_provenance_settlement_meter_gap",
        "all_claim_provenance_rows_ready": "claim_provenance_row_gap",
        "all_required_support_relations_covered": "claim_provenance_relation_gap",
        "all_render_surfaces_ready": "claim_provenance_render_surface_gap",
        "all_failure_cases_prove_blocking": "claim_provenance_negative_case_gap",
        "claim_provenance_publication_declared": "claim_provenance_publication_gap",
        "proof_graph_acyclic": "claim_provenance_proof_graph_cycle",
        "privacy_preserved": "claim_provenance_private_payload_leak",
    }
    failure_modes = [failure_modes_by_check[name] for name in failed_checks]
    ready = not failed_checks

    envelope = {
        "envelope_version": UNIVERSAL_CLAIM_PROVENANCE_ENVELOPE_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "claim_provenance_policy": policy,
        "artifact_bindings": artifact_bindings,
        "claim_provenance_rows": claim_rows,
        "render_surface_rows": render_rows,
        "failure_case_rows": failure_rows,
        "evidence_commitments": {
            "artifact_binding_root": artifact_bindings["artifact_binding_root"],
            "claim_provenance_root": claim_root,
            "render_surface_root": merkle_root(
                [row["render_surface_row_hash"] for row in render_rows]
            ),
            "failure_case_root": merkle_root(
                [row["failure_case_row_hash"] for row in failure_rows]
            ),
        },
        "checks": checks,
        "relation_coverage": relation_coverage,
        "display_decision": {
            "claim_provenance_envelope_authorized": ready,
            "answer_display_allowed": ready,
            "verified_source_footer_allowed": ready,
            "direct_creator_settlement_allowed": ready,
            "posthoc_citation_only_allowed": False,
            "failure_modes": failure_modes,
        },
        "verifier_commands": [
            "verify-universal-claim-provenance-envelope",
            "verify-universal-runtime-conformance-receipt",
            "verify-claim-source-attribution-report",
            "verify-evidence-region-binding-report",
            "verify-citation-identity-report",
            "verify-evidence-locator-manifest",
            "verify-citation-url-health",
            "verify-source-footer-delivery",
            "verify-client-attribution-enforcement",
        ],
        "research_controls": {
            "generation_time_provenance": "emit_claim_or_sentence_provenance_with_the_answer_not_after_generation",
            "support_relation_taxonomy": "quotation_compression_inference_retrieval_tool_memory_parametric_and_residual_value_are_distinct_relations",
            "claim_evidence_interface": "claim_level_evidence_and_omission_mapping_is_required_for_user_trust",
            "citation_hallucination_guard": "footer_rows_require_identity_locator_health_and_region_binding",
            "tool_observation_credit": "tool_trajectory_logs_are_insufficient_without_claim_to_observation_links",
            "research_urls": {
                "tracer_verifiable_generative_provenance": "https://arxiv.org/abs/2605.09934",
                "papertrail_claim_evidence_interface": "https://arxiv.org/abs/2602.21045",
                "datadignity_training_data_attribution": "https://arxiv.org/abs/2605.05687",
                "source_attribution_in_rag": "https://arxiv.org/abs/2507.04480",
                "llm_hallucinated_citations_in_the_wild": "https://arxiv.org/abs/2605.07723",
                "agent_sim_verifiable_traces": "https://arxiv.org/abs/2604.26653",
            },
        },
        "privacy": {
            "public_envelope_contains_private_prompts": False,
            "public_envelope_contains_private_outputs": False,
            "public_envelope_contains_source_text": False,
            "public_envelope_contains_tool_payloads": False,
            "hash_only_claim_and_source_commitments": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_runtime_level": MINIMUM_RUNTIME_LEVEL,
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
            "core_artifact_count": artifact_bindings["artifact_count"],
            "claim_provenance_row_count": len(claim_rows),
            "ready_claim_provenance_row_count": _count(claim_rows),
            "support_relation_count": len(required_relations),
            "covered_support_relation_count": sum(
                1 for covered in relation_coverage.values() if covered
            ),
            "render_surface_count": len(render_rows),
            "covered_render_surface_count": _count(render_rows),
            "failure_case_count": len(failure_rows),
            "offline_verification_supported": True,
            "privacy_preserved": checks["privacy_preserved"],
        },
    }
    envelope["universal_claim_provenance_envelope_hash"] = hash_payload(
        _hashable_envelope(envelope)
    )
    if signing_secret:
        envelope["signature"] = sign_payload(_hashable_envelope(envelope), signing_secret)
    return envelope


def validate_universal_claim_provenance_envelope_shape(
    envelope: dict[str, Any],
) -> list[str]:
    """Validate the public L150 envelope shape."""

    errors: list[str] = []
    required = (
        "envelope_version",
        "issuer",
        "created_at",
        "claim_provenance_policy",
        "artifact_bindings",
        "claim_provenance_rows",
        "render_surface_rows",
        "failure_case_rows",
        "evidence_commitments",
        "checks",
        "relation_coverage",
        "display_decision",
        "verifier_commands",
        "research_controls",
        "privacy",
        "summary",
        "universal_claim_provenance_envelope_hash",
    )
    for key in required:
        if key not in envelope:
            errors.append(f"missing universal claim provenance envelope field: {key}")
    if errors:
        return errors
    if envelope.get("envelope_version") != UNIVERSAL_CLAIM_PROVENANCE_ENVELOPE_VERSION:
        errors.append("universal claim provenance envelope version is unsupported")
    if envelope.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal claim provenance envelope target level is not RDLLM-L150")
    if envelope.get("claim_provenance_policy", {}).get("well_known_path") != DEFAULT_WELL_KNOWN_PATH:
        errors.append("universal claim provenance envelope well-known path is incorrect")
    return errors


def verify_universal_claim_provenance_envelope(
    envelope: dict[str, Any],
    *,
    envelope_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L150 claim provenance envelope against its replay input."""

    errors = validate_universal_claim_provenance_envelope_shape(envelope)
    if errors:
        return errors

    private_paths = _contains_private_fields(envelope)
    if private_paths:
        errors.append(
            "universal claim provenance envelope exposes private field(s): "
            + ", ".join(private_paths[:10])
        )
    if not _private_strings_absent(envelope, envelope_input):
        errors.append("universal claim provenance envelope leaks private replay text")

    expected_hash = hash_payload(_hashable_envelope(envelope))
    if expected_hash != envelope.get("universal_claim_provenance_envelope_hash"):
        errors.append("universal claim provenance envelope hash is not reproducible")

    expected = make_universal_claim_provenance_envelope(
        envelope_input,
        issuer=envelope.get("issuer", DEFAULT_ISSUER),
        created_at=envelope.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "claim_provenance_policy",
        "artifact_bindings",
        "claim_provenance_rows",
        "render_surface_rows",
        "failure_case_rows",
        "evidence_commitments",
        "checks",
        "relation_coverage",
        "display_decision",
        "verifier_commands",
        "research_controls",
        "privacy",
        "summary",
    ):
        if expected.get(key) != envelope.get(key):
            errors.append(
                f"universal claim provenance envelope {key} does not match replay input"
            )
    if (
        expected.get("universal_claim_provenance_envelope_hash")
        != envelope.get("universal_claim_provenance_envelope_hash")
    ):
        errors.append(
            "universal claim provenance envelope hash does not match replay input"
        )
    if signing_secret:
        expected_signature = sign_payload(_hashable_envelope(envelope), signing_secret)
        if envelope.get("signature") != expected_signature:
            errors.append("universal claim provenance envelope signature is invalid")
    return errors
