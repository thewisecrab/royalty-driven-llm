"""Acyclic replay graphs for RDLLM public proof packs."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload

PROOF_DEPENDENCY_GRAPH_VERSION = "rdllm-proof-dependency-graph/v1"
PROOF_DEPENDENCY_GRAPH_SCHEMA = "docs/schemas/proof_dependency_graph.schema.json"

DECLARED_HASH_FIELDS = (
    "trust_registry_hash",
    "publication_witness_hash",
    "publication_monitor_hash",
    "foundation_provider_conformance_hash",
    "foundation_runtime_adapter_hash",
    "foundation_runtime_router_hash",
    "foundation_model_deployment_attestation_hash",
    "foundation_profile_hash",
    "universal_composition_receipt_hash",
    "universal_composition_settlement_hash",
    "universal_foundation_model_contract_hash",
    "universal_invocation_guard_hash",
    "universal_invocation_coverage_hash",
    "universal_invocation_witness_hash",
    "universal_content_credential_hash",
    "universal_rdllm_passport_hash",
    "universal_adoption_standard_hash",
    "universal_interop_test_kit_hash",
    "universal_context_provenance_bridge_hash",
    "universal_citation_verification_contract_hash",
    "universal_grounded_reuse_contract_hash",
    "universal_training_serving_contract_hash",
    "universal_confidential_attribution_audit_hash",
    "universal_attribution_authority_control_plane_hash",
    "universal_rdllm_root_hash",
    "universal_emission_enforcement_gateway_hash",
    "universal_composite_rdllm_profile_hash",
    "universal_runtime_conformance_receipt_hash",
    "universal_claim_provenance_envelope_hash",
    "universal_provider_wire_protocol_hash",
    "universal_accountability_audit_trail_hash",
    "universal_accountability_witness_quorum_hash",
    "universal_grounded_reliance_contract_hash",
    "universal_reliance_correction_ledger_hash",
    "universal_foundation_adoption_kernel_hash",
    "universal_provider_adapter_harness_hash",
    "universal_provider_drift_sentinel_hash",
    "universal_attribution_negotiation_handshake_hash",
    "universal_negotiated_invocation_enforcement_hash",
    "universal_certification_trust_federation_hash",
    "universal_foundation_provider_adoption_pack_hash",
    "universal_industry_adoption_root_hash",
    "universal_reference_implementation_distribution_hash",
    "universal_live_attribution_proof_hash",
    "universal_foundation_model_release_passport_hash",
    "universal_composite_rdllm_contract_hash",
    "universal_foundation_provider_binding_matrix_hash",
    "universal_provider_conformance_runner_receipt_hash",
    "universal_production_invocation_admission_hash",
    "universal_source_grounded_response_receipt_hash",
    "universal_distribution_reliance_passport_hash",
    "universal_adversarial_provenance_quorum_hash",
    "universal_procurement_regulatory_reliance_contract_hash",
    "universal_provider_onboarding_migration_covenant_hash",
    "universal_model_provider_registry_hash",
    "universal_source_footer_enforcement_contract_hash",
    "universal_provider_catalog_coverage_contract_hash",
    "universal_runtime_route_binding_contract_hash",
    "universal_verified_source_footer_contract_hash",
    "universal_model_capability_coverage_contract_hash",
    "universal_live_capability_discovery_contract_hash",
    "universal_native_source_annotation_contract_hash",
    "universal_claim_evidence_footer_verification_contract_hash",
    "universal_provider_meter_normalization_contract_hash",
    "universal_provider_response_state_normalization_contract_hash",
    "composite_foundation_adapter_hash",
    "citation_url_health_hash",
    "evidence_locator_manifest_hash",
    "evidence_preview_footer_hash",
    "source_origin_lineage_hash",
    "warranted_source_footer_hash",
    "evidence_force_calibration_hash",
    "consent_revocation_propagation_hash",
    "royalty_abuse_audit_hash",
    "source_freshness_audit_hash",
    "attested_runtime_hash",
    "post_release_report_hash",
    "binding_report_hash",
    "watchtower_report_hash",
    "graph_hash",
    "attestation_hash",
    "gateway_report_hash",
    "proof_response_hash",
    "gate_hash",
    "contract_hash",
    "capsule_hash",
    "handshake_hash",
    "vector_pack_hash",
    "exchange_hash",
    "manifest_hash",
    "streaming_manifest_hash",
    "conversation_ledger_hash",
    "tool_ledger_hash",
    "profile_hash",
    "card_hash",
    "summary_hash",
    "envelope_hash",
    "report_hash",
    "bundle_hash",
    "package_hash",
    "trace_hash",
    "statement_hash",
    "receipt_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "output",
    "answer_text",
    "source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "customer_id",
    "customer_email",
    "invoice_text",
    "payment_method",
    "bank_account",
    "account_number",
    "tax_id",
}


def _level_number(level: str) -> int | None:
    if not level.startswith("RDLLM-L"):
        return None
    try:
        return int(level.removeprefix("RDLLM-L"))
    except ValueError:
        return None


def _target_certification_level(
    artifacts: list[tuple[str, str, dict[str, Any]]],
) -> str:
    levels: list[str] = []
    for _, _, payload in artifacts:
        summary = payload.get("summary")
        if not isinstance(summary, dict):
            continue
        for key in ("highest_level", "target_certification_level"):
            value = summary.get(key)
            if isinstance(value, str) and _level_number(value) is not None:
                levels.append(value)
    if not levels:
        return "RDLLM-L48"
    return max(levels, key=lambda level: _level_number(level) or -1)


DEFAULT_REPLAY_DEPENDENCIES = {
    "provider_card": ["certification"],
    "provider_attribution_card": ["certification_report"],
    "training_summary": ["provider_card", "certification"],
    "training_content_summary": ["provider_attribution_card", "certification_report"],
    "certification_attestation": ["certification_report"],
    "universal_adoption_standard": [
        "universal_rdllm_passport",
        "conformance_vector_pack",
        "integration_profile",
        "discovery_manifest",
        "provider_attribution_card",
        "certification_report",
        "attribution_exchange",
        "federation_handshake",
        "trust_registry",
    ],
    "universal_interop_test_kit": [
        "universal_adoption_standard",
        "universal_rdllm_passport",
        "conformance_vector_pack",
        "integration_profile",
        "discovery_manifest",
        "provider_attribution_card",
        "certification_report",
        "foundation_provider_conformance",
        "foundation_runtime_adapter",
        "universal_invocation_guard",
        "universal_invocation_coverage",
        "source_footer_delivery",
        "response_envelope",
        "trust_registry",
    ],
    "universal_context_provenance_bridge": [
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
    ],
    "universal_citation_verification_contract": [
        "universal_context_provenance_bridge",
        "source_footer_delivery",
        "response_envelope",
        "source_verification_report",
        "citation_url_health",
        "evidence_locator_manifest",
        "answer_claim_coverage_report",
        "evidence_force_calibration",
        "source_confidence_report",
        "warranted_source_footer",
        "rendered_attribution_audit",
        "trust_registry",
    ],
    "universal_grounded_reuse_contract": [
        "universal_citation_verification_contract",
        "response_envelope",
        "source_footer_delivery",
        "answer_claim_coverage_report",
        "source_freshness_audit",
        "consent_revocation_propagation",
        "citation_url_health",
        "evidence_locator_manifest",
        "source_access_lease_report",
        "trust_registry",
    ],
    "universal_training_serving_contract": [
        "universal_grounded_reuse_contract",
        "universal_citation_verification_contract",
        "training_content_summary",
        "training_memory_provenance",
        "post_training_signal_provenance",
        "model_lineage_attribution_report",
        "residual_corpus_royalty_report",
        "valuation_method_audit_report",
        "consent_revocation_propagation",
        "source_freshness_audit",
        "foundation_model_deployment_attestation",
        "foundation_runtime_router",
        "foundation_runtime_adapter",
        "foundation_provider_conformance",
        "composite_foundation_adapter",
        "foundation_api_profile",
        "provider_attribution_card",
        "integration_profile",
        "discovery_manifest",
        "assurance_bundle",
        "trust_registry",
    ],
    "universal_confidential_attribution_audit": [
        "universal_training_serving_contract",
        "universal_grounded_reuse_contract",
        "universal_citation_verification_contract",
        "certification_report",
        "certification_attestation",
        "provider_attribution_card",
        "integration_profile",
        "trust_registry",
        "training_content_summary",
        "training_memory_provenance",
        "post_training_signal_provenance",
        "residual_corpus_royalty_report",
        "valuation_method_audit_report",
        "foundation_model_deployment_attestation",
    ],
    "universal_attribution_authority_control_plane": [
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
    ],
    "universal_rdllm_root": [
        "certification_report",
        "certification_attestation",
        "provider_attribution_card",
        "integration_profile",
        "discovery_manifest",
        "assurance_bundle",
        "proof_dependency_graph",
        "universal_training_serving_contract",
        "universal_confidential_attribution_audit",
        "universal_attribution_authority_control_plane",
        "universal_context_provenance_bridge",
        "universal_citation_verification_contract",
        "universal_grounded_reuse_contract",
        "source_footer_delivery",
        "proof_carrying_response",
        "response_envelope",
        "trust_registry",
        "foundation_model_deployment_attestation",
        "foundation_runtime_router",
        "foundation_runtime_adapter",
        "composite_foundation_adapter",
        "foundation_api_profile",
        "agent_tool_attribution_ledger",
        "persistent_memory_provenance",
        "private_reasoning_attribution",
    ],
    "universal_emission_enforcement_gateway": [
        "universal_rdllm_root",
        "release_gate",
        "proof_carrying_response",
        "serving_gateway_report",
        "response_envelope",
        "source_footer_delivery",
        "emission_evidence_enforcement",
        "live_emission_witness",
        "live_emission_transparency",
        "universal_invocation_guard",
        "universal_invocation_coverage",
        "universal_invocation_witness",
        "foundation_runtime_router",
        "foundation_runtime_adapter",
        "foundation_api_profile",
        "foundation_model_deployment_attestation",
        "client_attribution_enforcement",
        "trust_registry",
    ],
    "universal_composite_rdllm_profile": [
        "certification_report",
        "certification_attestation",
        "provider_attribution_card",
        "integration_profile",
        "discovery_manifest",
        "assurance_bundle",
        "proof_dependency_graph",
        "universal_rdllm_passport",
        "universal_adoption_standard",
        "universal_interop_test_kit",
        "universal_rdllm_root",
        "universal_emission_enforcement_gateway",
        "source_footer_delivery",
        "client_attribution_enforcement",
        "foundation_api_profile",
        "foundation_runtime_adapter",
        "foundation_runtime_router",
        "foundation_model_deployment_attestation",
        "universal_invocation_guard",
        "universal_invocation_coverage",
        "universal_invocation_witness",
        "trust_registry",
    ],
    "universal_runtime_conformance_receipt": [
        "certification_report",
        "certification_attestation",
        "provider_attribution_card",
        "integration_profile",
        "discovery_manifest",
        "assurance_bundle",
        "proof_dependency_graph",
        "universal_composite_rdllm_profile",
        "universal_emission_enforcement_gateway",
        "universal_rdllm_root",
        "source_footer_delivery",
        "client_attribution_enforcement",
        "response_envelope",
        "proof_carrying_response",
        "serving_gateway_report",
        "grounded_source_footer",
        "rendered_attribution_audit",
        "claim_source_attribution_report",
        "evidence_region_binding_report",
        "deep_research_citation_audit",
        "citation_identity_report",
        "citation_reliance_receipt",
        "source_access_lease_report",
        "foundation_api_profile",
        "foundation_runtime_adapter",
        "foundation_runtime_router",
        "foundation_model_deployment_attestation",
        "universal_invocation_guard",
        "universal_invocation_coverage",
        "universal_invocation_witness",
        "revenue_allocation_report",
        "finance_ledger_attestation",
        "trust_registry",
    ],
    "universal_claim_provenance_envelope": [
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
    ],
    "universal_provider_wire_protocol": [
        "certification_report",
        "provider_attribution_card",
        "integration_profile",
        "discovery_manifest",
        "assurance_bundle",
        "proof_dependency_graph",
        "universal_claim_provenance_envelope",
        "universal_runtime_conformance_receipt",
        "universal_composite_rdllm_profile",
        "universal_emission_enforcement_gateway",
        "universal_rdllm_root",
        "foundation_api_profile",
        "foundation_runtime_adapter",
        "foundation_runtime_router",
        "composite_foundation_adapter",
        "foundation_provider_conformance",
        "foundation_model_deployment_attestation",
        "universal_invocation_guard",
        "universal_invocation_coverage",
        "universal_invocation_witness",
        "response_envelope",
        "proof_carrying_response",
        "serving_gateway_report",
        "source_footer_delivery",
        "client_attribution_enforcement",
        "agent_tool_attribution_ledger",
        "conversation_attribution_ledger",
        "revenue_allocation_report",
        "finance_ledger_attestation",
        "trust_registry",
    ],
    "universal_accountability_audit_trail": [
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
    ],
    "universal_accountability_witness_quorum": [
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
    ],
    "universal_grounded_reliance_contract": [
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
    ],
    "universal_reliance_correction_ledger": [
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
    ],
    "universal_foundation_adoption_kernel": [
        "certification_report",
        "provider_attribution_card",
        "integration_profile",
        "discovery_manifest",
        "assurance_bundle",
        "proof_dependency_graph",
        "universal_composite_rdllm_profile",
        "universal_runtime_conformance_receipt",
        "universal_claim_provenance_envelope",
        "universal_provider_wire_protocol",
        "universal_accountability_audit_trail",
        "universal_accountability_witness_quorum",
        "universal_grounded_reliance_contract",
        "universal_reliance_correction_ledger",
        "response_envelope",
        "source_footer_delivery",
        "client_attribution_enforcement",
        "citation_url_health",
        "source_freshness_audit",
        "evidence_locator_manifest",
        "warranted_source_footer",
        "revenue_allocation_report",
        "finance_ledger_attestation",
        "trust_registry",
    ],
    "universal_provider_adapter_harness": [
        "certification_report",
        "provider_attribution_card",
        "integration_profile",
        "discovery_manifest",
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
        "composite_foundation_adapter",
        "foundation_provider_conformance",
        "foundation_runtime_adapter",
    ],
    "universal_provider_drift_sentinel": [
        "certification_report",
        "provider_attribution_card",
        "integration_profile",
        "discovery_manifest",
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
    ],
    "universal_attribution_negotiation_handshake": [
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
    ],
    "universal_negotiated_invocation_enforcement": [
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
    ],
    "universal_certification_trust_federation": [
        "certification_report",
        "certification_attestation",
        "provider_attribution_card",
        "integration_profile",
        "discovery_manifest",
        "assurance_bundle",
        "trust_registry",
        "universal_negotiated_invocation_enforcement",
        "universal_attribution_negotiation_handshake",
        "universal_provider_drift_sentinel",
        "universal_provider_adapter_harness",
    ],
    "universal_foundation_provider_adoption_pack": [
        "certification_report",
        "certification_attestation",
        "provider_attribution_card",
        "integration_profile",
        "discovery_manifest",
        "assurance_bundle",
        "proof_dependency_graph",
        "trust_registry",
        "universal_certification_trust_federation",
        "universal_negotiated_invocation_enforcement",
        "universal_attribution_negotiation_handshake",
        "universal_provider_drift_sentinel",
        "universal_provider_adapter_harness",
        "universal_foundation_adoption_kernel",
        "universal_composite_rdllm_profile",
        "universal_rdllm_root",
        "universal_provider_wire_protocol",
        "universal_claim_provenance_envelope",
        "universal_content_credential",
        "response_envelope",
        "source_footer_delivery",
        "revenue_allocation_report",
        "finance_ledger_attestation",
    ],
    "universal_industry_adoption_root": [
        "certification_report",
        "certification_attestation",
        "provider_attribution_card",
        "integration_profile",
        "discovery_manifest",
        "assurance_bundle",
        "proof_dependency_graph",
        "trust_registry",
        "universal_foundation_provider_adoption_pack",
        "universal_certification_trust_federation",
        "universal_negotiated_invocation_enforcement",
        "response_envelope",
        "source_footer_delivery",
        "revenue_allocation_report",
        "finance_ledger_attestation",
    ],
    "universal_reference_implementation_distribution": [
        "certification_report",
        "certification_attestation",
        "provider_attribution_card",
        "integration_profile",
        "discovery_manifest",
        "assurance_bundle",
        "proof_dependency_graph",
        "trust_registry",
        "universal_industry_adoption_root",
        "universal_foundation_provider_adoption_pack",
        "response_envelope",
        "source_footer_delivery",
        "revenue_allocation_report",
        "finance_ledger_attestation",
    ],
    "universal_live_attribution_proof": [
        "certification_report",
        "provider_attribution_card",
        "integration_profile",
        "discovery_manifest",
        "universal_reference_implementation_distribution",
        "response_envelope",
        "universal_claim_provenance_envelope",
        "grounded_source_footer",
        "source_footer_delivery",
        "citation_reliance_receipt",
        "claim_source_attribution_report",
        "evidence_utility_attribution_report",
        "parametric_memory_attribution_report",
        "source_confidence_report",
        "source_availability_report",
        "citation_identity_report",
        "revenue_allocation_report",
        "finance_ledger_attestation",
    ],
    "universal_foundation_model_release_passport": [
        "certification_report",
        "certification_attestation",
        "provider_attribution_card",
        "integration_profile",
        "discovery_manifest",
        "proof_dependency_graph",
        "trust_registry",
        "universal_reference_implementation_distribution",
        "universal_live_attribution_proof",
        "universal_foundation_model_contract",
        "universal_training_serving_contract",
        "universal_composite_rdllm_profile",
        "universal_runtime_conformance_receipt",
        "universal_provider_wire_protocol",
        "universal_grounded_reliance_contract",
        "universal_reliance_correction_ledger",
        "revenue_allocation_report",
        "finance_ledger_attestation",
    ],
    "answer_card": ["receipt", "trace"],
    "answer_provenance_card": ["attribution_receipt", "trace_exchange"],
    "source_verification": ["answer_card"],
    "source_verification_report": ["answer_provenance_card"],
    "source_confidence": ["answer_card", "source_verification", "creator_license"],
    "source_confidence_report": [
        "answer_provenance_card",
        "source_verification_report",
        "creator_license_contract",
    ],
    "citation_footer": ["source_confidence"],
    "citation_footer_contract": ["source_confidence_report"],
    "source_availability_report": [
        "source_verification_report",
        "citation_footer_contract",
    ],
    "evidence_sufficiency_report": [
        "source_verification_report",
        "source_availability_report",
        "citation_footer_contract",
    ],
    "counterevidence_report": [
        "source_verification_report",
        "source_availability_report",
        "evidence_sufficiency_report",
        "citation_footer_contract",
    ],
    "answer_claim_coverage_report": [
        "answer_provenance_card",
        "source_verification_report",
        "evidence_sufficiency_report",
        "counterevidence_report",
        "citation_footer_contract",
    ],
    "generation_context_closure_report": [
        "trace_exchange",
        "source_verification_report",
        "answer_claim_coverage_report",
    ],
    "source_boundary_report": [
        "trace_exchange",
        "source_verification_report",
        "generation_context_closure_report",
    ],
    "source_authenticity_report": [
        "source_availability_report",
        "source_boundary_report",
        "creator_license_contract",
        "source_confidence_report",
    ],
    "decision_provenance_report": [
        "response_envelope",
        "release_gate",
        "trace_exchange",
        "attribution_capsule",
        "source_boundary_report",
    ],
    "calibrated_attribution_report": [
        "response_envelope",
        "source_confidence_report",
        "evidence_sufficiency_report",
        "provenance_evaluation_report",
        "decision_provenance_report",
    ],
    "response_envelope": [
        "answer_card",
        "source_verification",
        "source_confidence",
        "citation_footer_contract",
        "source_availability_report",
        "evidence_sufficiency_report",
        "counterevidence_report",
        "answer_claim_coverage_report",
        "trace_exchange",
        "generation_context_closure_report",
        "source_boundary_report",
        "source_authenticity_report",
        "creator_license",
        "provider_card",
        "certification",
    ],
    "integration_profile": [
        "provider_card",
        "provider_attribution_card",
        "certification",
        "certification_report",
        "response_envelope",
    ],
    "discovery_manifest": [
        "provider_card",
        "provider_attribution_card",
        "certification",
        "certification_report",
        "integration_profile",
        "response_envelope",
        "assurance_bundle",
    ],
    "attribution_exchange": [
        "provider_attribution_card",
        "certification_report",
        "integration_profile",
        "discovery_manifest",
        "response_envelope",
        "assurance_bundle",
        "semantic_text",
        "semantic_text_attribution_report",
        "creator_license",
        "creator_license_contract",
    ],
    "conformance_vector_pack": [
        "response_envelope",
        "discovery_manifest",
        "semantic_text",
        "semantic_text_attribution_report",
        "attribution_exchange",
    ],
    "federation_handshake": [
        "provider_attribution_card",
        "certification_report",
        "integration_profile",
        "discovery_manifest",
        "response_envelope",
        "assurance_bundle",
        "semantic_text",
        "semantic_text_attribution_report",
        "creator_license",
        "creator_license_contract",
        "attribution_exchange",
        "conformance_vector_pack",
    ],
    "attribution_capsule": [
        "response_envelope",
        "federation_handshake",
        "attribution_exchange",
        "conformance_vector_pack",
    ],
    "release_gate": [
        "response_envelope",
        "source_verification",
        "source_verification_report",
        "source_availability_report",
        "evidence_sufficiency_report",
        "counterevidence_report",
        "answer_claim_coverage_report",
        "generation_context_closure_report",
        "source_boundary_report",
        "source_authenticity_report",
        "attribution_capsule",
        "provider_card",
        "provider_attribution_card",
        "certification",
        "certification_report",
    ],
    "proof_carrying_response": [
        "release_gate",
        "response_envelope",
        "attribution_capsule",
        "provider_card",
        "provider_attribution_card",
        "certification",
        "certification_report",
    ],
    "serving_gateway": ["proof_carrying_response", "release_gate"],
    "serving_gateway_report": ["proof_carrying_response", "release_gate"],
    "streaming_attribution_manifest": [
        "proof_carrying_response",
        "serving_gateway_report",
    ],
    "conversation_attribution_ledger": [
        "proof_carrying_response",
        "serving_gateway_report",
        "streaming_attribution_manifest",
    ],
    "agent_tool_attribution_ledger": [
        "proof_carrying_response",
        "trace_exchange",
        "conversation_attribution_ledger",
    ],
    "pinpoint_provenance_report": [
        "proof_carrying_response",
        "agent_tool_attribution_ledger",
        "model_signal_attribution_report",
        "semantic_text_attribution_report",
    ],
    "citation_identity_report": [
        "pinpoint_provenance_report",
        "citation_footer_contract",
        "source_availability_report",
        "source_authenticity_report",
    ],
    "attribution_consensus_report": [
        "source_confidence_report",
        "evidence_sufficiency_report",
        "counterevidence_report",
        "source_authenticity_report",
        "pinpoint_provenance_report",
        "citation_identity_report",
    ],
    "verifier_quorum_report": [
        "attribution_consensus_report",
        "provider_attribution_card",
        "certification_report",
        "integration_profile",
    ],
    "verifier_accountability_report": [
        "verifier_quorum_report",
        "trust_registry",
        "provider_attribution_card",
        "certification_report",
    ],
    "receipt_transparency_consistency_report": [
        "verifier_accountability_report",
        "provider_attribution_card",
        "certification_report",
        "attribution_receipt",
        "transparency_log",
    ],
    "watchtower_challenge_settlement_report": [
        "receipt_transparency_consistency_report",
        "verifier_accountability_report",
        "trust_registry",
        "provider_attribution_card",
        "certification_report",
    ],
    "output_provenance_binding_report": [
        "proof_carrying_response",
        "serving_gateway_report",
        "attribution_capsule",
        "watchtower_challenge_settlement_report",
        "provider_attribution_card",
        "certification_report",
    ],
    "post_release_discovery_report": [
        "discovery_manifest",
        "output_provenance_binding_report",
        "proof_carrying_response",
        "serving_gateway_report",
        "attribution_capsule",
        "watchtower_challenge_settlement_report",
        "provider_attribution_card",
        "certification_report",
        "integration_profile",
    ],
    "statement": ["receipt", "trace"],
    "royalty_statement": ["attribution_receipt", "trace_exchange"],
    "challenge": ["statement", "receipt"],
    "attribution_challenge": ["royalty_statement", "attribution_receipt"],
    "private_audit": ["receipt"],
    "private_audit_challenge": ["attribution_receipt"],
    "transitive_attribution": ["attribution_capsule", "response_envelope", "answer_card"],
    "transitive_attribution_report": [
        "attribution_capsule",
        "response_envelope",
        "answer_provenance_card",
    ],
    "clearinghouse": ["statement", "transitive_attribution"],
    "clearinghouse_report": ["royalty_statement", "transitive_attribution_report"],
    "remittance": ["clearinghouse", "creator_license"],
    "remittance_report": ["clearinghouse_report", "creator_license_contract"],
    "payment_execution_report": ["remittance_report"],
    "payment_rail_attestation": ["payment_execution_report", "trust_registry"],
    "creator_payout_receipt_report": [
        "clearinghouse_report",
        "remittance_report",
        "payment_execution_report",
        "payment_rail_attestation",
    ],
    "rendered_attribution_audit": [
        "response_envelope",
        "citation_footer_contract",
        "source_availability_report",
        "evidence_sufficiency_report",
        "counterevidence_report",
        "answer_claim_coverage_report",
    ],
    "training_memory_provenance": [
        "response_envelope",
        "answer_claim_coverage_report",
        "generation_context_closure_report",
        "citation_footer_contract",
        "rendered_attribution_audit",
        "creator_license_contract",
        "training_content_summary",
    ],
    "evidence_locked_generation": [
        "response_envelope",
        "answer_claim_coverage_report",
        "generation_context_closure_report",
        "citation_footer_contract",
        "rendered_attribution_audit",
        "training_memory_provenance",
    ],
    "emission_evidence_enforcement": [
        "response_envelope",
        "answer_claim_coverage_report",
        "evidence_locked_generation",
        "proof_carrying_response",
        "serving_gateway_report",
        "streaming_attribution_manifest",
    ],
    "live_emission_witness": [
        "emission_evidence_enforcement",
        "streaming_attribution_manifest",
    ],
    "live_emission_transparency": ["live_emission_witness"],
    "attested_runtime": [
        "live_emission_transparency",
        "proof_carrying_response",
        "serving_gateway_report",
        "evidence_locked_generation",
    ],
    "claim_source_attribution_report": [
        "response_envelope",
        "citation_footer_contract",
        "answer_claim_coverage_report",
        "source_availability_report",
        "evidence_sufficiency_report",
        "attested_runtime",
    ],
    "evidence_region_binding_report": [
        "response_envelope",
        "rendered_attribution_audit",
        "claim_source_attribution_report",
        "citation_footer_contract",
        "source_availability_report",
    ],
    "source_access_lease_report": [
        "creator_license_contract",
        "source_availability_report",
        "evidence_region_binding_report",
        "response_envelope",
    ],
    "content_protocol_ingestion_report": [
        "creator_license_contract",
        "source_access_lease_report",
        "source_availability_report",
        "evidence_region_binding_report",
    ],
    "citation_reliance_receipt": [
        "rendered_attribution_audit",
        "evidence_locked_generation",
        "claim_source_attribution_report",
        "evidence_utility_attribution_report",
        "source_access_lease_report",
        "content_protocol_ingestion_report",
        "citation_footer_contract",
        "answer_claim_coverage_report",
    ],
    "license_transaction_receipt": [
        "source_access_lease_report",
        "content_protocol_ingestion_report",
        "citation_reliance_receipt",
        "creator_license_contract",
    ],
    "grounded_source_footer": [
        "citation_footer_contract",
        "rendered_attribution_audit",
        "source_confidence_report",
        "source_availability_report",
        "evidence_region_binding_report",
        "citation_reliance_receipt",
        "license_transaction_receipt",
    ],
    "source_footer_delivery": [
        "grounded_source_footer",
        "response_envelope",
        "proof_carrying_response",
        "serving_gateway_report",
    ],
    "foundation_api_profile": [
        "provider_attribution_card",
        "certification_report",
        "integration_profile",
        "discovery_manifest",
        "response_envelope",
        "source_footer_delivery",
    ],
    "client_attribution_enforcement": [
        "foundation_api_profile",
        "response_envelope",
        "source_footer_delivery",
        "integration_profile",
        "discovery_manifest",
    ],
    "persistent_memory_provenance": [
        "client_attribution_enforcement",
        "source_footer_delivery",
        "foundation_api_profile",
        "conversation_attribution_ledger",
        "agent_tool_attribution_ledger",
    ],
    "private_reasoning_attribution": [
        "persistent_memory_provenance",
        "client_attribution_enforcement",
        "source_footer_delivery",
        "agent_tool_attribution_ledger",
        "conversation_attribution_ledger",
        "proof_carrying_response",
    ],
    "post_training_signal_provenance": [
        "private_reasoning_attribution",
        "model_lineage_attribution_report",
        "training_content_summary",
        "creator_license_contract",
    ],
    "attribution_bom": [
        "provider_attribution_card",
        "certification_report",
        "proof_dependency_graph",
        "post_training_signal_provenance",
        "model_lineage_attribution_report",
        "creator_license_contract",
        "training_content_summary",
    ],
    "creator_attribution_audit_index": [
        "attribution_bom",
        "provider_attribution_card",
        "certification_report",
        "proof_dependency_graph",
        "grounded_source_footer",
        "source_footer_delivery",
        "post_training_signal_provenance",
        "model_lineage_attribution_report",
        "creator_payout_receipt_report",
        "training_content_summary",
        "source_access_lease_report",
        "license_transaction_receipt",
        "citation_reliance_receipt",
    ],
    "creator_attribution_audit_federation": [
        "creator_attribution_audit_index",
        "provider_attribution_card",
        "certification_report",
        "discovery_manifest",
        "attribution_exchange",
        "federation_handshake",
        "trust_registry",
    ],
    "creator_attribution_audit_federation_transparency": [
        "creator_attribution_audit_federation",
        "creator_attribution_audit_index",
        "discovery_manifest",
        "trust_registry",
    ],
    "creator_audit_transparency_monitor": [
        "creator_attribution_audit_federation_transparency",
        "creator_attribution_audit_federation",
        "creator_attribution_audit_index",
        "discovery_manifest",
        "trust_registry",
    ],
    "creator_audit_private_watch": [
        "creator_audit_transparency_monitor",
        "creator_attribution_audit_federation_transparency",
        "discovery_manifest",
        "trust_registry",
    ],
    "deep_research_citation_audit": [
        "source_footer_delivery",
        "grounded_source_footer",
        "rendered_attribution_audit",
        "claim_source_attribution_report",
        "source_availability_report",
        "source_confidence_report",
        "proof_carrying_response",
    ],
    "source_freshness_audit": [
        "deep_research_citation_audit",
        "source_footer_delivery",
        "grounded_source_footer",
        "source_availability_report",
        "source_confidence_report",
        "citation_reliance_receipt",
        "source_access_lease_report",
        "proof_carrying_response",
    ],
    "royalty_abuse_audit": [
        "source_freshness_audit",
        "source_authenticity_report",
        "source_confidence_report",
        "attribution_consensus_report",
        "creator_attribution_audit_index",
        "valuation_method_audit_report",
        "watchtower_challenge_settlement_report",
        "payment_execution_report",
    ],
    "consent_revocation_propagation": [
        "royalty_abuse_audit",
        "rights_remediation_report",
        "creator_license_contract",
        "source_access_lease_report",
        "license_transaction_receipt",
        "grounded_source_footer",
        "source_footer_delivery",
        "persistent_memory_provenance",
        "private_reasoning_attribution",
        "post_training_signal_provenance",
        "attribution_exchange",
        "creator_attribution_audit_federation",
    ],
    "evidence_force_calibration": [
        "consent_revocation_propagation",
        "source_freshness_audit",
        "deep_research_citation_audit",
        "evidence_sufficiency_report",
        "counterevidence_report",
        "source_confidence_report",
        "citation_footer_contract",
        "grounded_source_footer",
        "claim_source_attribution_report",
        "calibrated_attribution_report",
    ],
    "warranted_source_footer": [
        "evidence_force_calibration",
        "grounded_source_footer",
        "citation_footer_contract",
        "rendered_attribution_audit",
    ],
    "source_origin_lineage": [
        "warranted_source_footer",
        "grounded_source_footer",
        "source_authenticity_report",
        "creator_license_contract",
    ],
    "evidence_preview_footer": [
        "source_origin_lineage",
        "warranted_source_footer",
        "grounded_source_footer",
        "source_freshness_audit",
        "deep_research_citation_audit",
    ],
    "evidence_locator_manifest": [
        "evidence_preview_footer",
        "evidence_region_binding_report",
        "source_availability_report",
        "source_freshness_audit",
        "deep_research_citation_audit",
    ],
    "citation_url_health": [
        "evidence_locator_manifest",
        "source_availability_report",
        "source_freshness_audit",
        "deep_research_citation_audit",
    ],
    "composite_foundation_adapter": [
        "foundation_api_profile",
        "response_envelope",
        "source_footer_delivery",
        "citation_url_health",
        "discovery_manifest",
        "integration_profile",
        "provider_attribution_card",
    ],
    "foundation_provider_conformance": [
        "composite_foundation_adapter",
        "foundation_api_profile",
        "source_footer_delivery",
        "citation_url_health",
        "integration_profile",
        "discovery_manifest",
        "provider_attribution_card",
        "conformance_vector_pack",
    ],
    "foundation_runtime_adapter": [
        "foundation_provider_conformance",
        "composite_foundation_adapter",
        "foundation_api_profile",
        "response_envelope",
        "source_footer_delivery",
        "citation_url_health",
        "discovery_manifest",
    ],
    "foundation_runtime_router": [
        "foundation_runtime_adapter",
        "foundation_provider_conformance",
        "composite_foundation_adapter",
        "foundation_api_profile",
        "discovery_manifest",
    ],
    "foundation_model_deployment_attestation": [
        "foundation_runtime_router",
        "foundation_runtime_adapter",
        "attested_runtime",
        "trust_registry",
        "discovery_manifest",
    ],
    "universal_composition_receipt": [
        "foundation_model_deployment_attestation",
        "composite_foundation_adapter",
        "foundation_provider_conformance",
        "response_envelope",
        "source_footer_delivery",
        "trace_exchange",
        "discovery_manifest",
    ],
    "universal_composition_settlement": [
        "universal_composition_receipt",
        "revenue_allocation_report",
        "clearinghouse_report",
        "response_envelope",
        "source_footer_delivery",
        "trust_registry",
        "discovery_manifest",
    ],
    "universal_foundation_model_contract": [
        "provider_attribution_card",
        "integration_profile",
        "discovery_manifest",
        "proof_dependency_graph",
        "composite_foundation_adapter",
        "foundation_provider_conformance",
        "foundation_runtime_adapter",
        "foundation_runtime_router",
        "foundation_model_deployment_attestation",
        "universal_composition_receipt",
        "universal_composition_settlement",
    ],
    "universal_foundation_provider_binding_matrix": [
        "universal_composite_rdllm_contract",
        "universal_foundation_model_release_passport",
        "universal_negotiated_invocation_enforcement",
        "universal_provider_adapter_harness",
        "universal_provider_drift_sentinel",
        "integration_profile",
        "discovery_manifest",
        "provider_attribution_card",
    ],
    "universal_provider_conformance_runner_receipt": [
        "universal_foundation_provider_binding_matrix",
        "universal_composite_rdllm_contract",
        "universal_reference_implementation_distribution",
        "universal_certification_trust_federation",
        "universal_live_attribution_proof",
    ],
    "universal_production_invocation_admission": [
        "universal_provider_conformance_runner_receipt",
        "universal_foundation_provider_binding_matrix",
        "universal_negotiated_invocation_enforcement",
        "universal_provider_drift_sentinel",
        "universal_live_attribution_proof",
        "integration_profile",
        "discovery_manifest",
    ],
    "universal_source_grounded_response_receipt": [
        "universal_production_invocation_admission",
        "universal_live_attribution_proof",
        "universal_claim_provenance_envelope",
        "grounded_source_footer",
        "source_footer_delivery",
        "citation_reliance_receipt",
        "claim_source_attribution_report",
        "source_confidence_report",
        "source_availability_report",
        "revenue_allocation_report",
        "finance_ledger_attestation",
    ],
    "universal_distribution_reliance_passport": [
        "universal_source_grounded_response_receipt",
        "universal_content_credential",
        "grounded_source_footer",
        "source_footer_delivery",
        "evidence_locator_manifest",
        "citation_url_health",
        "universal_reliance_correction_ledger",
        "revenue_allocation_report",
        "finance_ledger_attestation",
    ],
    "universal_adversarial_provenance_quorum": [
        "universal_distribution_reliance_passport",
        "universal_accountability_witness_quorum",
        "universal_content_credential",
        "publication_witness",
        "receipt_transparency_consistency_report",
        "evidence_locator_manifest",
        "citation_url_health",
        "universal_reliance_correction_ledger",
    ],
    "universal_procurement_regulatory_reliance_contract": [
        "universal_adversarial_provenance_quorum",
        "provider_attribution_card",
        "integration_profile",
    ],
    "universal_provider_onboarding_migration_covenant": [
        "universal_procurement_regulatory_reliance_contract",
        "universal_foundation_provider_binding_matrix",
        "universal_provider_conformance_runner_receipt",
        "integration_profile",
        "discovery_manifest",
    ],
    "universal_model_provider_registry": [
        "universal_provider_onboarding_migration_covenant",
        "universal_foundation_provider_binding_matrix",
        "universal_provider_conformance_runner_receipt",
        "integration_profile",
        "discovery_manifest",
    ],
    "universal_source_footer_enforcement_contract": [
        "universal_model_provider_registry",
        "universal_source_grounded_response_receipt",
        "universal_claim_provenance_envelope",
        "source_footer_delivery",
        "evidence_locator_manifest",
        "citation_url_health",
        "integration_profile",
        "discovery_manifest",
    ],
    "universal_provider_catalog_coverage_contract": [
        "universal_model_provider_registry",
        "universal_source_footer_enforcement_contract",
        "universal_provider_adapter_harness",
        "universal_provider_drift_sentinel",
        "integration_profile",
        "discovery_manifest",
    ],
    "universal_runtime_route_binding_contract": [
        "universal_production_invocation_admission",
        "universal_provider_catalog_coverage_contract",
        "universal_provider_drift_sentinel",
        "universal_negotiated_invocation_enforcement",
        "integration_profile",
        "discovery_manifest",
    ],
    "universal_verified_source_footer_contract": [
        "universal_runtime_route_binding_contract",
        "universal_source_footer_enforcement_contract",
        "universal_source_grounded_response_receipt",
        "universal_citation_verification_contract",
        "deep_research_citation_audit",
        "citation_url_health",
        "source_confidence_report",
        "integration_profile",
        "discovery_manifest",
    ],
    "universal_model_capability_coverage_contract": [
        "universal_model_provider_registry",
        "universal_provider_catalog_coverage_contract",
        "universal_runtime_route_binding_contract",
        "universal_verified_source_footer_contract",
        "foundation_provider_conformance",
        "universal_provider_adapter_harness",
        "integration_profile",
        "discovery_manifest",
    ],
    "universal_live_capability_discovery_contract": [
        "universal_model_capability_coverage_contract",
        "universal_provider_catalog_coverage_contract",
        "universal_model_provider_registry",
        "integration_profile",
        "discovery_manifest",
    ],
    "universal_native_source_annotation_contract": [
        "universal_live_capability_discovery_contract",
        "universal_verified_source_footer_contract",
        "universal_source_grounded_response_receipt",
        "universal_runtime_route_binding_contract",
        "integration_profile",
        "discovery_manifest",
    ],
    "universal_claim_evidence_footer_verification_contract": [
        "universal_native_source_annotation_contract",
        "universal_verified_source_footer_contract",
        "universal_source_grounded_response_receipt",
        "universal_runtime_route_binding_contract",
        "integration_profile",
        "discovery_manifest",
    ],
    "universal_provider_meter_normalization_contract": [
        "universal_claim_evidence_footer_verification_contract",
        "universal_live_capability_discovery_contract",
        "universal_runtime_route_binding_contract",
        "universal_source_grounded_response_receipt",
        "revenue_allocation_report",
        "finance_ledger_attestation",
        "integration_profile",
        "discovery_manifest",
    ],
    "universal_provider_response_state_normalization_contract": [
        "universal_provider_meter_normalization_contract",
        "universal_claim_evidence_footer_verification_contract",
        "universal_runtime_route_binding_contract",
        "universal_source_grounded_response_receipt",
        "response_envelope",
        "integration_profile",
        "discovery_manifest",
    ],
    "universal_invocation_guard": [
        "universal_foundation_model_contract",
        "foundation_runtime_adapter",
        "foundation_runtime_router",
        "foundation_model_deployment_attestation",
    ],
    "universal_invocation_coverage": [
        "universal_invocation_guard",
        "source_footer_delivery",
        "response_envelope",
        "revenue_allocation_report",
        "finance_ledger_attestation",
    ],
    "universal_invocation_witness": [
        "universal_invocation_coverage",
        "provider_attribution_card",
        "integration_profile",
        "discovery_manifest",
    ],
    "universal_content_credential": [
        "certification",
        "certification_report",
        "response_envelope",
        "answer_card",
        "answer_provenance_card",
        "grounded_source_footer",
        "source_footer_delivery",
        "evidence_preview_footer",
        "evidence_locator_manifest",
        "citation_url_health",
        "output_provenance_binding_report",
        "universal_invocation_witness",
        "royalty_statement",
        "provider_card",
        "provider_attribution_card",
        "integration_profile",
        "discovery_manifest",
    ],
    "universal_rdllm_passport": [
        "certification_report",
        "certification_attestation",
        "provider_attribution_card",
        "training_content_summary",
        "integration_profile",
        "discovery_manifest",
        "assurance_bundle",
        "proof_dependency_graph",
        "composite_foundation_adapter",
        "foundation_provider_conformance",
        "foundation_runtime_adapter",
        "foundation_runtime_router",
        "foundation_model_deployment_attestation",
        "universal_composition_receipt",
        "universal_composition_settlement",
        "universal_foundation_model_contract",
        "universal_invocation_guard",
        "universal_invocation_coverage",
        "universal_invocation_witness",
        "universal_content_credential",
    ],
    "evidence_utility_attribution_report": [
        "claim_source_attribution_report",
        "decision_provenance_report",
        "generation_context_closure_report",
        "attested_runtime",
    ],
    "parametric_memory_attribution_report": [
        "training_content_summary",
        "model_signal_attribution_report",
        "training_memory_provenance",
        "claim_source_attribution_report",
        "evidence_utility_attribution_report",
        "attested_runtime",
    ],
    "style_influence_attribution_report": [
        "creator_license_contract",
        "semantic_text_attribution_report",
        "media_attribution_report",
        "claim_source_attribution_report",
        "parametric_memory_attribution_report",
        "attested_runtime",
    ],
    "model_lineage_attribution_report": [
        "training_content_summary",
        "creator_license_contract",
        "parametric_memory_attribution_report",
        "style_influence_attribution_report",
        "attested_runtime",
    ],
    "black_box_model_provenance_report": [
        "model_lineage_attribution_report",
        "output_provenance_binding_report",
        "watchtower_challenge_settlement_report",
        "creator_license_contract",
        "attested_runtime",
    ],
    "attribution_dispute_adjudication_report": [
        "black_box_model_provenance_report",
        "model_lineage_attribution_report",
        "watchtower_challenge_settlement_report",
        "verifier_accountability_report",
        "trust_registry",
        "payment_execution_report",
        "creator_license_contract",
    ],
    "post_adjudication_settlement_adjustment_report": [
        "attribution_dispute_adjudication_report",
        "payment_execution_report",
        "payment_rail_attestation",
        "creator_payout_receipt_report",
        "trust_registry",
        "creator_license_contract",
    ],
    "residual_corpus_royalty_report": [
        "training_content_summary",
        "creator_license_contract",
        "revenue_allocation_report",
        "finance_ledger_attestation",
        "trust_registry",
    ],
    "valuation_method_audit_report": [
        "residual_corpus_royalty_report",
        "training_content_summary",
        "creator_license_contract",
        "provenance_evaluation_report",
    ],
    "revenue_allocation": ["receipt"],
    "revenue_allocation_report": ["attribution_receipt"],
    "finance_ledger": ["revenue_allocation"],
    "finance_ledger_attestation": ["revenue_allocation_report"],
    "audit_attestation": [
        "provider_attribution_card",
        "certification_report",
        "integration_profile",
        "discovery_manifest",
        "assurance_bundle",
        "response_envelope",
        "source_confidence_report",
        "citation_footer_contract",
        "clearinghouse_report",
        "remittance_report",
        "payment_execution_report",
        "payment_rail_attestation",
        "creator_payout_receipt_report",
        "rendered_attribution_audit",
        "training_memory_provenance",
        "evidence_locked_generation",
        "emission_evidence_enforcement",
        "live_emission_witness",
        "live_emission_transparency",
        "attested_runtime",
        "claim_source_attribution_report",
        "evidence_utility_attribution_report",
        "parametric_memory_attribution_report",
        "style_influence_attribution_report",
        "model_lineage_attribution_report",
        "black_box_model_provenance_report",
        "attribution_dispute_adjudication_report",
        "post_adjudication_settlement_adjustment_report",
        "residual_corpus_royalty_report",
        "valuation_method_audit_report",
        "evidence_region_binding_report",
        "source_access_lease_report",
        "content_protocol_ingestion_report",
        "citation_reliance_receipt",
        "license_transaction_receipt",
        "grounded_source_footer",
        "warranted_source_footer",
        "source_origin_lineage",
        "evidence_preview_footer",
        "evidence_locator_manifest",
        "citation_url_health",
        "composite_foundation_adapter",
        "source_footer_delivery",
        "revenue_allocation_report",
        "finance_ledger_attestation",
        "universal_foundation_provider_binding_matrix",
        "universal_provider_conformance_runner_receipt",
        "universal_production_invocation_admission",
        "universal_source_grounded_response_receipt",
        "universal_distribution_reliance_passport",
        "universal_adversarial_provenance_quorum",
        "universal_procurement_regulatory_reliance_contract",
        "universal_provider_onboarding_migration_covenant",
        "universal_model_provider_registry",
        "universal_source_footer_enforcement_contract",
        "universal_provider_catalog_coverage_contract",
        "universal_runtime_route_binding_contract",
        "universal_verified_source_footer_contract",
        "universal_model_capability_coverage_contract",
        "universal_live_capability_discovery_contract",
        "universal_native_source_annotation_contract",
        "universal_claim_evidence_footer_verification_contract",
        "universal_provider_meter_normalization_contract",
        "universal_provider_response_state_normalization_contract",
    ],
    "publication_monitor": [
        "certification_report",
        "provider_attribution_card",
        "integration_profile",
        "response_envelope",
        "assurance_bundle",
        "proof_dependency_graph",
        "universal_production_invocation_admission",
        "universal_source_grounded_response_receipt",
        "universal_distribution_reliance_passport",
        "universal_adversarial_provenance_quorum",
        "universal_procurement_regulatory_reliance_contract",
        "universal_provider_onboarding_migration_covenant",
        "universal_model_provider_registry",
        "universal_source_footer_enforcement_contract",
        "universal_provider_catalog_coverage_contract",
        "universal_runtime_route_binding_contract",
        "universal_verified_source_footer_contract",
        "universal_model_capability_coverage_contract",
        "universal_live_capability_discovery_contract",
        "universal_native_source_annotation_contract",
        "universal_claim_evidence_footer_verification_contract",
        "universal_provider_meter_normalization_contract",
        "universal_provider_response_state_normalization_contract",
    ],
    "publication_witness": [
        "publication_monitor",
        "certification_report",
    ],
    "trust_registry": [
        "publication_witness",
        "publication_monitor",
        "audit_attestation",
    ],
}


def _hashable_graph(graph: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in graph.items()
        if key not in {"graph_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
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


def _declared_hash(payload: dict[str, Any]) -> str:
    for field in DECLARED_HASH_FIELDS:
        value = payload.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(payload)


def _artifact_hash_is_reproducible(payload: dict[str, Any]) -> bool:
    for field in DECLARED_HASH_FIELDS:
        if payload.get(field):
            if field == "receipt_hash" and isinstance(payload.get("payload"), dict):
                return hash_payload(payload["payload"]) == payload[field]
            hashable = {
                key: value
                for key, value in payload.items()
                if key not in {field, "signature"}
            }
            if field == "capsule_hash":
                surfaces = hashable.get("portable_surfaces")
                if isinstance(surfaces, dict):
                    surfaces = deepcopy(surfaces)
                    headers = surfaces.get("http_headers")
                    if isinstance(headers, dict):
                        headers.pop("RDLLM-Capsule-Hash", None)
                    hashable["portable_surfaces"] = surfaces
            if field == "foundation_profile_hash":
                metadata = hashable.get("response_metadata_contract")
                if isinstance(metadata, dict):
                    header_values = dict(metadata.get("header_values", {}))
                    header_values[
                        "RDLLM-Foundation-Profile-Hash"
                    ] = "<foundation_profile_hash>"
                    metadata = dict(metadata)
                    metadata["header_values"] = header_values
                    hashable["response_metadata_contract"] = metadata
            return hash_payload(hashable) == payload[field]
    return True


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}" if path else f"/{key}"
            if key in PRIVATE_FIELD_NAMES:
                findings.append(child_path)
            findings.extend(_contains_private_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_contains_private_fields(child, f"{path}/{index}"))
    return findings


def _node_row(name: str, artifact_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    row = {
        "name": name,
        "artifact_type": artifact_type,
        "declared_hash": _declared_hash(payload),
        "payload_hash": hash_payload(payload),
        "hash_reproducible": _artifact_hash_is_reproducible(payload),
    }
    row["node_hash"] = hash_payload(row)
    return row


def _edge_row(
    dependent: str,
    dependency: str,
    *,
    edge_class: str,
    reason: str,
) -> dict[str, Any]:
    row = {
        "dependent": dependent,
        "dependency": dependency,
        "edge_class": edge_class,
        "reason": reason,
    }
    row["edge_hash"] = hash_payload(row)
    return row


def _normalise_dependency_rows(
    artifacts: list[tuple[str, str, dict[str, Any]]],
    dependencies: list[dict[str, str]] | None,
    *,
    include_publication_edges: bool,
) -> tuple[list[dict[str, Any]], list[str]]:
    names = {name for name, _, _ in artifacts}
    rows: list[dict[str, Any]] = []
    unknowns: list[str] = []

    if dependencies is None:
        for dependent in sorted(names):
            for dependency in DEFAULT_REPLAY_DEPENDENCIES.get(dependent, []):
                if dependency in names:
                    rows.append(
                        _edge_row(
                            dependent,
                            dependency,
                            edge_class="replay_dependency",
                            reason="default_verifier_prerequisite",
                        )
                    )
        if include_publication_edges and "assurance_bundle" in names:
            assurance_payload = next(
                (
                    payload
                    for name, _, payload in artifacts
                    if name == "assurance_bundle"
                ),
                {},
            )
            assured_names = {
                str(entry.get("name", ""))
                for entry in assurance_payload.get("artifacts", [])
                if isinstance(entry, dict)
            }
            for name in sorted(assured_names & names):
                if name != "assurance_bundle":
                    rows.append(
                        _edge_row(
                            "assurance_bundle",
                            name,
                            edge_class="publication_commitment",
                            reason="merkle_bundle_inclusion",
                        )
                    )
    else:
        for item in dependencies:
            dependent = str(item.get("dependent", ""))
            dependency = str(item.get("dependency", ""))
            edge_class = str(item.get("edge_class", "replay_dependency"))
            reason = str(item.get("reason", "declared_dependency"))
            if dependent not in names:
                unknowns.append(dependent)
            if dependency not in names:
                unknowns.append(dependency)
            rows.append(
                _edge_row(
                    dependent,
                    dependency,
                    edge_class=edge_class,
                    reason=reason,
                )
            )

    deduped = {
        (
            row["dependent"],
            row["dependency"],
            row["edge_class"],
            row["reason"],
        ): row
        for row in rows
    }
    return (
        sorted(deduped.values(), key=lambda row: (row["edge_class"], row["dependent"], row["dependency"], row["reason"])),
        sorted(set(unknowns)),
    )


def _topological_order(
    names: set[str],
    replay_edges: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    dependencies = {name: set() for name in names}
    dependents = {name: set() for name in names}
    for edge in replay_edges:
        dependent = str(edge.get("dependent", ""))
        dependency = str(edge.get("dependency", ""))
        if dependent not in names or dependency not in names:
            continue
        dependencies[dependent].add(dependency)
        dependents[dependency].add(dependent)

    ready = sorted(name for name, deps in dependencies.items() if not deps)
    order: list[str] = []
    while ready:
        name = ready.pop(0)
        order.append(name)
        for dependent in sorted(dependents[name]):
            dependencies[dependent].discard(name)
            if not dependencies[dependent] and dependent not in order and dependent not in ready:
                ready.append(dependent)
        ready.sort()

    cycle_nodes = sorted(name for name, deps in dependencies.items() if deps)
    return order, cycle_nodes


def _replay_steps(order: list[str], nodes_by_name: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for index, name in enumerate(order):
        node = nodes_by_name[name]
        steps.append(
            {
                "step": index + 1,
                "artifact": name,
                "artifact_type": node["artifact_type"],
                "declared_hash": node["declared_hash"],
                "payload_hash": node["payload_hash"],
                "verifier_command": f"verify-{name.replace('_', '-')}",
                "step_hash": hash_payload(
                    {
                        "step": index + 1,
                        "artifact": name,
                        "declared_hash": node["declared_hash"],
                    }
                ),
            }
        )
    return steps


def make_proof_dependency_graph(
    artifacts: list[tuple[str, str, dict[str, Any]]],
    *,
    dependencies: list[dict[str, str]] | None = None,
    include_publication_edges: bool = True,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed proof-pack replay DAG without embedding artifact payloads."""

    nodes = [
        _node_row(name, artifact_type, payload)
        for name, artifact_type, payload in sorted(artifacts, key=lambda item: item[0])
    ]
    node_names = {node["name"] for node in nodes}
    duplicate_names = sorted(
        name for name in node_names if [node["name"] for node in nodes].count(name) > 1
    )
    edge_rows, unknowns = _normalise_dependency_rows(
        artifacts,
        dependencies,
        include_publication_edges=include_publication_edges,
    )
    replay_edges = [
        edge for edge in edge_rows if edge.get("edge_class") == "replay_dependency"
    ]
    self_dependencies = sorted(
        edge["dependent"] for edge in edge_rows if edge.get("dependent") == edge.get("dependency")
    )
    replay_order, cycle_nodes = _topological_order(node_names, replay_edges)
    nodes_by_name = {node["name"]: node for node in nodes}
    replay_steps = _replay_steps(replay_order, nodes_by_name)
    roots = sorted(node for node in node_names if node not in {edge["dependent"] for edge in replay_edges})
    leaves = sorted(node for node in node_names if node not in {edge["dependency"] for edge in replay_edges})
    private_input_paths = _contains_private_fields(
        {
            "artifacts": nodes,
            "dependencies": edge_rows,
            "replay_steps": replay_steps,
        }
    )
    checks = {
        "artifact_names_unique": not duplicate_names,
        "all_dependencies_known": not unknowns,
        "no_self_dependencies": not self_dependencies,
        "replay_graph_acyclic": not cycle_nodes and len(replay_order) == len(node_names),
        "topological_order_covers_all_artifacts": len(replay_order) == len(node_names),
        "artifact_hashes_reproducible": all(node["hash_reproducible"] for node in nodes),
        "artifact_payloads_not_embedded": True,
        "private_input_fields_absent": not private_input_paths,
    }
    graph = {
        "graph_version": PROOF_DEPENDENCY_GRAPH_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "graph_profile": {
            "replay_edges_are_hard_dependencies": True,
            "publication_edges_are_commitments_not_replay_prerequisites": True,
            "topological_replay_required": True,
            "artifact_payloads_redacted": True,
        },
        "artifacts": nodes,
        "dependencies": edge_rows,
        "replay_order": replay_order,
        "replay_steps": replay_steps,
        "cycle_break_policy": {
            "allowed_publication_edge_class": "publication_commitment",
            "replay_cycles_allowed": False,
            "publication_back_references_do_not_define_replay_order": True,
        },
        "checks": checks,
        "commitments": {
            "artifact_root": hash_payload([node["node_hash"] for node in nodes]),
            "dependency_root": hash_payload([edge["edge_hash"] for edge in edge_rows]),
            "replay_order_hash": hash_payload(replay_order),
            "replay_step_root": hash_payload([step["step_hash"] for step in replay_steps]),
            "schema": PROOF_DEPENDENCY_GRAPH_SCHEMA,
        },
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": _target_certification_level(artifacts),
            "artifact_count": len(nodes),
            "dependency_count": len(edge_rows),
            "replay_dependency_count": len(replay_edges),
            "publication_commitment_count": len(edge_rows) - len(replay_edges),
            "root_count": len(roots),
            "leaf_count": len(leaves),
            "cycle_node_count": len(cycle_nodes),
            "unknown_dependency_count": len(unknowns),
            "duplicate_artifact_name_count": len(duplicate_names),
            "private_input_field_count": len(private_input_paths),
            "root_artifacts": roots,
            "leaf_artifacts": leaves,
            "cycle_nodes": cycle_nodes,
            "unknown_dependencies": unknowns,
            "duplicate_artifact_names": duplicate_names,
        },
        "privacy": {
            "artifact_payloads_disclosed": False,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "evidence_text_disclosed": False,
            "customer_or_payment_text_disclosed": False,
            "graph_uses_hashes_and_dependency_metadata": True,
        },
    }
    graph["graph_hash"] = hash_payload(_hashable_graph(graph))
    graph["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_graph(graph), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return graph


def validate_proof_dependency_graph_shape(graph: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "graph_version",
        "issuer",
        "created_at",
        "graph_profile",
        "artifacts",
        "dependencies",
        "replay_order",
        "replay_steps",
        "cycle_break_policy",
        "checks",
        "commitments",
        "summary",
        "privacy",
        "graph_hash",
        "signature",
    )
    for key in required:
        if key not in graph:
            errors.append(f"missing proof dependency graph field: {key}")
    if errors:
        return errors
    if graph.get("graph_version") != PROOF_DEPENDENCY_GRAPH_VERSION:
        errors.append("proof dependency graph version is unsupported")
    for node in graph.get("artifacts", []):
        for key in ("name", "artifact_type", "declared_hash", "payload_hash", "node_hash"):
            if key not in node:
                errors.append(f"missing proof dependency graph artifact field: {key}")
    for edge in graph.get("dependencies", []):
        for key in ("dependent", "dependency", "edge_class", "reason", "edge_hash"):
            if key not in edge:
                errors.append(f"missing proof dependency graph edge field: {key}")
    for check in (
        "artifact_names_unique",
        "all_dependencies_known",
        "no_self_dependencies",
        "replay_graph_acyclic",
        "topological_order_covers_all_artifacts",
        "artifact_hashes_reproducible",
        "artifact_payloads_not_embedded",
        "private_input_fields_absent",
    ):
        if check not in graph.get("checks", {}):
            errors.append(f"missing proof dependency graph check: {check}")
    return errors


def verify_proof_dependency_graph(
    graph: dict[str, Any],
    artifacts: list[tuple[str, str, dict[str, Any]]],
    *,
    dependencies: list[dict[str, str]] | None = None,
    include_publication_edges: bool = True,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a proof dependency graph against artifact payloads and edge policy."""

    errors = validate_proof_dependency_graph_shape(graph)
    if errors:
        return errors

    if hash_payload(_hashable_graph(graph)) != graph.get("graph_hash"):
        errors.append("proof dependency graph hash is not reproducible")

    expected = make_proof_dependency_graph(
        artifacts,
        dependencies=dependencies,
        include_publication_edges=include_publication_edges,
        issuer=graph.get("issuer", DEFAULT_ISSUER),
        created_at=graph.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "graph_profile",
        "artifacts",
        "dependencies",
        "replay_order",
        "replay_steps",
        "cycle_break_policy",
        "checks",
        "commitments",
        "summary",
        "privacy",
    ):
        if expected.get(key) != graph.get(key):
            errors.append(f"proof dependency graph {key} does not match artifacts")
    if expected.get("graph_hash") != graph.get("graph_hash"):
        errors.append("proof dependency graph hash does not match artifacts")

    if graph.get("summary", {}).get("status") != "ready":
        errors.append("proof dependency graph status is not ready")
    for check, passed in graph.get("checks", {}).items():
        if passed is not True:
            errors.append(f"proof dependency graph check failed: {check}")

    if graph.get("privacy", {}).get("graph_uses_hashes_and_dependency_metadata") is not True:
        errors.append("proof dependency graph must use hashes and dependency metadata")
    private_paths = _contains_private_fields(graph)
    if private_paths:
        errors.append(
            "proof dependency graph exposes private fields: "
            + ", ".join(private_paths[:5])
        )

    signature = graph.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_graph(graph), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("proof dependency graph is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("proof dependency graph signature is invalid")

    return errors
