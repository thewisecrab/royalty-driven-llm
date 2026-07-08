"""Command line interface for the Royalty Driven LLM prototype."""

from __future__ import annotations

import argparse
from importlib import resources
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from rdllm.assurance import make_assurance_bundle, verify_assurance_bundle
from rdllm.audit_attestation import (
    make_audit_attestation,
    verify_audit_attestation,
)
from rdllm.answer_card import (
    make_answer_provenance_card,
    verify_answer_provenance_card,
)
from rdllm.answer_coverage import (
    make_answer_claim_coverage_report,
    verify_answer_claim_coverage_report,
)
from rdllm.calibrated_attribution import (
    make_calibrated_attribution_report,
    verify_calibrated_attribution_report,
)
from rdllm.context_closure import (
    make_generation_context_closure_report,
    verify_generation_context_closure_report,
)
from rdllm.decision_provenance import (
    make_decision_provenance_report,
    verify_decision_provenance_report,
)
from rdllm.attribution_gap import evaluate_event_attribution_gap
from rdllm.attribution_exchange import (
    make_attribution_exchange_manifest,
    verify_attribution_exchange_manifest,
)
from rdllm.attribution_capsule import (
    make_attribution_capsule,
    verify_attribution_capsule,
)
from rdllm.attribution_consensus import (
    make_attribution_consensus_report,
    verify_attribution_consensus_report,
)
from rdllm.verifier_quorum import (
    make_verifier_quorum_report,
    verify_verifier_quorum_report,
)
from rdllm.verifier_accountability import (
    make_verifier_accountability_report,
    verify_verifier_accountability_report,
)
from rdllm.receipt_transparency_consistency import (
    make_receipt_transparency_consistency_report,
    verify_receipt_transparency_consistency_report,
)
from rdllm.watchtower_challenge_settlement import (
    make_watchtower_challenge_settlement_report,
    verify_watchtower_challenge_settlement_report,
)
from rdllm.output_provenance_binding import (
    make_output_provenance_binding_report,
    verify_output_provenance_binding_report,
)
from rdllm.post_release_discovery import (
    make_post_release_discovery_report,
    verify_post_release_discovery_report,
)
from rdllm.certification import run_certification
from rdllm.certification_attestation import (
    make_certification_attestation,
    verify_certification_attestation,
)
from rdllm.challenges import (
    make_attribution_challenge,
    verify_attribution_challenge,
)
from rdllm.clearinghouse import (
    make_clearinghouse_report,
    verify_clearinghouse_report,
)
from rdllm.citation_footer import (
    make_citation_footer_contract,
    verify_citation_footer_contract,
)
from rdllm.citation_identity import (
    load_citation_identity_input,
    make_citation_identity_report,
    verify_citation_identity_report,
)
from rdllm.code_attribution import (
    load_code_attribution_inputs,
    make_code_attribution_report,
    verify_code_attribution_report,
)
from rdllm.claim_verification import (
    load_claim_verification_inputs,
    make_claim_verification_report,
    verify_claim_verification_report,
)
from rdllm.claim_source_attribution import (
    load_claim_source_attribution_input,
    make_claim_source_attribution_report,
    verify_claim_source_attribution_report,
)
from rdllm.evidence_utility_attribution import (
    load_evidence_utility_input,
    make_evidence_utility_attribution_report,
    verify_evidence_utility_attribution_report,
)
from rdllm.parametric_memory_attribution import (
    load_parametric_memory_input,
    make_parametric_memory_attribution_report,
    verify_parametric_memory_attribution_report,
)
from rdllm.style_influence_attribution import (
    load_style_influence_input,
    make_style_influence_attribution_report,
    verify_style_influence_attribution_report,
)
from rdllm.model_lineage_attribution import (
    load_model_lineage_input,
    make_model_lineage_attribution_report,
    verify_model_lineage_attribution_report,
)
from rdllm.black_box_model_provenance import (
    load_black_box_model_provenance_input,
    make_black_box_model_provenance_report,
    verify_black_box_model_provenance_report,
)
from rdllm.attribution_dispute_adjudication import (
    load_attribution_dispute_adjudication_input,
    make_attribution_dispute_adjudication_report,
    verify_attribution_dispute_adjudication_report,
)
from rdllm.post_adjudication_settlement_adjustment import (
    load_post_adjudication_settlement_adjustment_input,
    make_post_adjudication_settlement_adjustment_report,
    verify_post_adjudication_settlement_adjustment_report,
)
from rdllm.residual_corpus_royalty import (
    load_residual_corpus_royalty_input,
    make_residual_corpus_royalty_report,
    verify_residual_corpus_royalty_report,
)
from rdllm.valuation_method_audit import (
    load_valuation_method_audit_input,
    make_valuation_method_audit_report,
    verify_valuation_method_audit_report,
)
from rdllm.evidence_region_binding import (
    load_evidence_region_binding_input,
    make_evidence_region_binding_report,
    verify_evidence_region_binding_report,
)
from rdllm.source_access_lease import (
    load_source_access_lease_input,
    make_source_access_lease_report,
    verify_source_access_lease_report,
)
from rdllm.content_protocol_ingestion import (
    load_content_protocol_ingestion_input,
    make_content_protocol_ingestion_report,
    verify_content_protocol_ingestion_report,
)
from rdllm.citation_reliance_receipt import (
    load_citation_reliance_input,
    make_citation_reliance_receipt,
    verify_citation_reliance_receipt,
)
from rdllm.license_transaction_receipt import (
    load_license_transaction_input,
    make_license_transaction_receipt,
    verify_license_transaction_receipt,
)
from rdllm.grounded_source_footer import (
    load_grounded_source_footer_input,
    make_grounded_source_footer,
    verify_grounded_source_footer,
)
from rdllm.source_footer_delivery import (
    load_source_footer_delivery_input,
    make_source_footer_delivery_receipt,
    verify_source_footer_delivery_receipt,
)
from rdllm.foundation_api_profile import (
    load_foundation_api_profile_input,
    make_foundation_api_profile,
    verify_foundation_api_profile,
)
from rdllm.client_attribution_enforcement import (
    load_client_attribution_input,
    make_client_attribution_enforcement_receipt,
    verify_client_attribution_enforcement_receipt,
)
from rdllm.persistent_memory_provenance import (
    load_persistent_memory_provenance_input,
    make_persistent_memory_provenance_receipt,
    verify_persistent_memory_provenance_receipt,
)
from rdllm.private_reasoning_attribution import (
    load_private_reasoning_attribution_input,
    make_private_reasoning_attribution_receipt,
    verify_private_reasoning_attribution_receipt,
)
from rdllm.post_training_signal_provenance import (
    load_post_training_signal_input,
    make_post_training_signal_provenance_receipt,
    verify_post_training_signal_provenance_receipt,
)
from rdllm.attribution_bill_of_materials import (
    load_attribution_bom_input,
    make_attribution_bill_of_materials,
    verify_attribution_bill_of_materials,
)
from rdllm.creator_attribution_audit_index import (
    load_creator_attribution_audit_index_input,
    make_creator_attribution_audit_index,
    verify_creator_attribution_audit_index,
)
from rdllm.creator_attribution_audit_federation import (
    load_creator_attribution_audit_federation_input,
    make_creator_attribution_audit_federation,
    verify_creator_attribution_audit_federation,
)
from rdllm.creator_attribution_audit_federation_transparency import (
    make_creator_audit_federation_transparency_log,
    make_creator_audit_federation_transparency_report,
    verify_creator_audit_federation_transparency_report,
)
from rdllm.creator_audit_transparency_monitor import (
    make_creator_audit_transparency_monitor_report,
    verify_creator_audit_transparency_monitor_report,
)
from rdllm.creator_audit_private_watch import (
    make_creator_audit_private_watch_report,
    verify_creator_audit_private_watch_report,
)
from rdllm.deep_research_citation_audit import (
    load_deep_research_citation_audit_input,
    make_deep_research_citation_audit_report,
    verify_deep_research_citation_audit_report,
)
from rdllm.source_freshness_audit import (
    load_source_freshness_audit_input,
    make_source_freshness_audit_report,
    verify_source_freshness_audit_report,
)
from rdllm.royalty_abuse_audit import (
    load_royalty_abuse_audit_input,
    make_royalty_abuse_audit_report,
    verify_royalty_abuse_audit_report,
)
from rdllm.consent_revocation_propagation import (
    load_consent_revocation_propagation_input,
    make_consent_revocation_propagation_report,
    verify_consent_revocation_propagation_report,
)
from rdllm.evidence_force_calibration import (
    load_evidence_force_calibration_input,
    make_evidence_force_calibration_report,
    verify_evidence_force_calibration_report,
)
from rdllm.warranted_source_footer import (
    load_warranted_source_footer_input,
    make_warranted_source_footer,
    verify_warranted_source_footer,
)
from rdllm.source_origin_lineage import (
    load_source_origin_lineage_input,
    make_source_origin_lineage_report,
    verify_source_origin_lineage_report,
)
from rdllm.evidence_preview_footer import (
    load_evidence_preview_footer_input,
    make_evidence_preview_footer,
    verify_evidence_preview_footer,
)
from rdllm.evidence_locator_manifest import (
    load_evidence_locator_manifest_input,
    make_evidence_locator_manifest,
    verify_evidence_locator_manifest,
)
from rdllm.citation_url_health import (
    load_citation_url_health_input,
    make_citation_url_health_report,
    verify_citation_url_health_report,
)
from rdllm.composite_foundation_adapter import (
    load_composite_foundation_adapter_input,
    make_composite_foundation_adapter_report,
    verify_composite_foundation_adapter_report,
)
from rdllm.foundation_provider_conformance import (
    load_foundation_provider_conformance_input,
    make_foundation_provider_conformance_report,
    verify_foundation_provider_conformance_report,
)
from rdllm.foundation_runtime_adapter import (
    load_foundation_runtime_adapter_input,
    make_foundation_runtime_adapter_report,
    verify_foundation_runtime_adapter_report,
)
from rdllm.foundation_runtime_router import (
    load_foundation_runtime_router_input,
    make_foundation_runtime_router_report,
    verify_foundation_runtime_router_report,
)
from rdllm.foundation_model_deployment_attestation import (
    load_foundation_model_deployment_attestation_input,
    make_foundation_model_deployment_attestation_report,
    verify_foundation_model_deployment_attestation_report,
)
from rdllm.universal_composition_receipt import (
    load_universal_composition_receipt_input,
    make_universal_composition_receipt,
    verify_universal_composition_receipt,
)
from rdllm.universal_composition_settlement import (
    load_universal_composition_settlement_input,
    make_universal_composition_settlement,
    verify_universal_composition_settlement,
)
from rdllm.universal_foundation_model_contract import (
    load_universal_foundation_model_contract_input,
    make_universal_foundation_model_contract,
    verify_universal_foundation_model_contract,
)
from rdllm.universal_invocation_guard import (
    load_universal_invocation_guard_input,
    make_universal_invocation_guard,
    verify_universal_invocation_guard,
)
from rdllm.universal_invocation_coverage import (
    load_universal_invocation_coverage_input,
    make_universal_invocation_coverage,
    verify_universal_invocation_coverage,
)
from rdllm.universal_invocation_witness import (
    load_universal_invocation_witness_input,
    make_universal_invocation_witness,
    verify_universal_invocation_witness,
)
from rdllm.universal_content_credential import (
    load_universal_content_credential_input,
    make_universal_content_credential,
    verify_universal_content_credential,
)
from rdllm.universal_rdllm_passport import (
    load_universal_rdllm_passport_input,
    make_universal_rdllm_passport,
    verify_universal_rdllm_passport,
)
from rdllm.universal_adoption_standard import (
    load_universal_adoption_standard_input,
    make_universal_adoption_standard,
    verify_universal_adoption_standard,
)
from rdllm.universal_interop_test_kit import (
    load_universal_interop_test_kit_input,
    make_universal_interop_test_kit,
    verify_universal_interop_test_kit,
)
from rdllm.universal_context_provenance_bridge import (
    load_universal_context_provenance_bridge_input,
    make_universal_context_provenance_bridge,
    verify_universal_context_provenance_bridge,
)
from rdllm.universal_citation_verification_contract import (
    load_universal_citation_verification_contract_input,
    make_universal_citation_verification_contract,
    verify_universal_citation_verification_contract,
)
from rdllm.universal_grounded_reuse_contract import (
    load_universal_grounded_reuse_contract_input,
    make_universal_grounded_reuse_contract,
    verify_universal_grounded_reuse_contract,
)
from rdllm.universal_training_serving_contract import (
    load_universal_training_serving_contract_input,
    make_universal_training_serving_contract,
    verify_universal_training_serving_contract,
)
from rdllm.universal_confidential_attribution_audit import (
    load_universal_confidential_attribution_audit_input,
    make_universal_confidential_attribution_audit,
    verify_universal_confidential_attribution_audit,
)
from rdllm.universal_attribution_authority_control_plane import (
    load_universal_attribution_authority_control_plane_input,
    make_universal_attribution_authority_control_plane,
    verify_universal_attribution_authority_control_plane,
)
from rdllm.universal_rdllm_root import (
    load_universal_rdllm_root_input,
    make_universal_rdllm_root,
    verify_universal_rdllm_root,
)
from rdllm.universal_emission_enforcement_gateway import (
    load_universal_emission_enforcement_gateway_input,
    make_universal_emission_enforcement_gateway,
    verify_universal_emission_enforcement_gateway,
)
from rdllm.universal_composite_rdllm_profile import (
    load_universal_composite_rdllm_profile_input,
    make_universal_composite_rdllm_profile,
    verify_universal_composite_rdllm_profile,
)
from rdllm.universal_runtime_conformance_receipt import (
    load_universal_runtime_conformance_receipt_input,
    make_universal_runtime_conformance_receipt,
    verify_universal_runtime_conformance_receipt,
)
from rdllm.universal_claim_provenance_envelope import (
    load_universal_claim_provenance_envelope_input,
    make_universal_claim_provenance_envelope,
    verify_universal_claim_provenance_envelope,
)
from rdllm.universal_provider_wire_protocol import (
    load_universal_provider_wire_protocol_input,
    make_universal_provider_wire_protocol,
    verify_universal_provider_wire_protocol,
)
from rdllm.universal_accountability_audit_trail import (
    load_universal_accountability_audit_trail_input,
    make_universal_accountability_audit_trail,
    verify_universal_accountability_audit_trail,
)
from rdllm.universal_accountability_witness_quorum import (
    load_universal_accountability_witness_quorum_input,
    make_universal_accountability_witness_quorum,
    verify_universal_accountability_witness_quorum,
)
from rdllm.universal_grounded_reliance_contract import (
    load_universal_grounded_reliance_contract_input,
    make_universal_grounded_reliance_contract,
    verify_universal_grounded_reliance_contract,
)
from rdllm.universal_reliance_correction_ledger import (
    load_universal_reliance_correction_ledger_input,
    make_universal_reliance_correction_ledger,
    verify_universal_reliance_correction_ledger,
)
from rdllm.universal_foundation_adoption_kernel import (
    load_universal_foundation_adoption_kernel_input,
    make_universal_foundation_adoption_kernel,
    verify_universal_foundation_adoption_kernel,
)
from rdllm.universal_provider_adapter_harness import (
    load_universal_provider_adapter_harness_input,
    make_universal_provider_adapter_harness,
    verify_universal_provider_adapter_harness,
)
from rdllm.universal_provider_drift_sentinel import (
    load_universal_provider_drift_sentinel_input,
    make_universal_provider_drift_sentinel,
    verify_universal_provider_drift_sentinel,
)
from rdllm.universal_attribution_negotiation_handshake import (
    load_universal_attribution_negotiation_handshake_input,
    make_universal_attribution_negotiation_handshake,
    verify_universal_attribution_negotiation_handshake,
)
from rdllm.universal_negotiated_invocation_enforcement import (
    load_universal_negotiated_invocation_enforcement_input,
    make_universal_negotiated_invocation_enforcement,
    verify_universal_negotiated_invocation_enforcement,
)
from rdllm.universal_certification_trust_federation import (
    load_universal_certification_trust_federation_input,
    make_universal_certification_trust_federation,
    verify_universal_certification_trust_federation,
)
from rdllm.universal_foundation_provider_adoption_pack import (
    load_universal_foundation_provider_adoption_pack_input,
    make_universal_foundation_provider_adoption_pack,
    verify_universal_foundation_provider_adoption_pack,
)
from rdllm.universal_industry_adoption_root import (
    load_universal_industry_adoption_root_input,
    make_universal_industry_adoption_root,
    verify_universal_industry_adoption_root,
)
from rdllm.universal_reference_implementation_distribution import (
    load_universal_reference_implementation_distribution_input,
    make_universal_reference_implementation_distribution,
    verify_universal_reference_implementation_distribution,
)
from rdllm.universal_live_attribution_proof import (
    load_universal_live_attribution_proof_input,
    make_universal_live_attribution_proof,
    verify_universal_live_attribution_proof,
)
from rdllm.universal_foundation_model_release_passport import (
    load_universal_foundation_model_release_passport_input,
    make_universal_foundation_model_release_passport,
    verify_universal_foundation_model_release_passport,
)
from rdllm.universal_composite_rdllm_contract import (
    load_universal_composite_rdllm_contract_input,
    make_universal_composite_rdllm_contract,
    verify_universal_composite_rdllm_contract,
)
from rdllm.universal_foundation_provider_binding_matrix import (
    load_universal_foundation_provider_binding_matrix_input,
    make_universal_foundation_provider_binding_matrix,
    verify_universal_foundation_provider_binding_matrix,
)
from rdllm.universal_provider_conformance_runner_receipt import (
    load_universal_provider_conformance_runner_receipt_input,
    make_universal_provider_conformance_runner_receipt,
    verify_universal_provider_conformance_runner_receipt,
)
from rdllm.universal_production_invocation_admission import (
    load_universal_production_invocation_admission_input,
    make_universal_production_invocation_admission,
    verify_universal_production_invocation_admission,
)
from rdllm.universal_source_grounded_response_receipt import (
    load_universal_source_grounded_response_receipt_input,
    make_universal_source_grounded_response_receipt,
    verify_universal_source_grounded_response_receipt,
)
from rdllm.universal_distribution_reliance_passport import (
    load_universal_distribution_reliance_passport_input,
    make_universal_distribution_reliance_passport,
    verify_universal_distribution_reliance_passport,
)
from rdllm.universal_adversarial_provenance_quorum import (
    load_universal_adversarial_provenance_quorum_input,
    make_universal_adversarial_provenance_quorum,
    verify_universal_adversarial_provenance_quorum,
)
from rdllm.universal_procurement_regulatory_reliance_contract import (
    load_universal_procurement_regulatory_reliance_contract_input,
    make_universal_procurement_regulatory_reliance_contract,
    verify_universal_procurement_regulatory_reliance_contract,
)
from rdllm.universal_provider_onboarding_migration_covenant import (
    load_universal_provider_onboarding_migration_covenant_input,
    make_universal_provider_onboarding_migration_covenant,
    verify_universal_provider_onboarding_migration_covenant,
)
from rdllm.universal_model_provider_registry import (
    load_universal_model_provider_registry_input,
    make_universal_model_provider_registry,
    verify_universal_model_provider_registry,
)
from rdllm.universal_source_footer_enforcement_contract import (
    load_universal_source_footer_enforcement_contract_input,
    make_universal_source_footer_enforcement_contract,
    verify_universal_source_footer_enforcement_contract,
)
from rdllm.universal_provider_catalog_coverage_contract import (
    load_universal_provider_catalog_coverage_contract_input,
    make_universal_provider_catalog_coverage_contract,
    verify_universal_provider_catalog_coverage_contract,
)
from rdllm.universal_runtime_route_binding_contract import (
    load_universal_runtime_route_binding_contract_input,
    make_universal_runtime_route_binding_contract,
    verify_universal_runtime_route_binding_contract,
)
from rdllm.universal_verified_source_footer_contract import (
    load_universal_verified_source_footer_contract_input,
    make_universal_verified_source_footer_contract,
    verify_universal_verified_source_footer_contract,
)
from rdllm.universal_model_capability_coverage_contract import (
    load_universal_model_capability_coverage_contract_input,
    make_universal_model_capability_coverage_contract,
    verify_universal_model_capability_coverage_contract,
)
from rdllm.universal_live_capability_discovery_contract import (
    load_universal_live_capability_discovery_contract_input,
    make_universal_live_capability_discovery_contract,
    verify_universal_live_capability_discovery_contract,
)
from rdllm.universal_native_source_annotation_contract import (
    load_universal_native_source_annotation_contract_input,
    make_universal_native_source_annotation_contract,
    verify_universal_native_source_annotation_contract,
)
from rdllm.universal_claim_evidence_footer_verification_contract import (
    load_universal_claim_evidence_footer_verification_contract_input,
    make_universal_claim_evidence_footer_verification_contract,
    verify_universal_claim_evidence_footer_verification_contract,
)
from rdllm.universal_provider_meter_normalization_contract import (
    load_universal_provider_meter_normalization_contract_input,
    make_universal_provider_meter_normalization_contract,
    verify_universal_provider_meter_normalization_contract,
)
from rdllm.universal_provider_response_state_normalization_contract import (
    load_universal_provider_response_state_normalization_contract_input,
    make_universal_provider_response_state_normalization_contract,
    verify_universal_provider_response_state_normalization_contract,
)
from rdllm.conformance import verify_conformance_bundle
from rdllm.conformance_vectors import (
    make_conformance_vector_pack,
    verify_conformance_vector_pack,
)
from rdllm.counterfactual import (
    make_counterfactual_report,
    verify_counterfactual_report,
)
from rdllm.counterevidence import (
    make_counterevidence_report,
    verify_counterevidence_report,
)
from rdllm.disclosure import (
    make_selective_disclosure_package,
    verify_selective_disclosure_package,
)
from rdllm.discovery_manifest import (
    make_discovery_manifest,
    verify_discovery_manifest,
)
from rdllm.evidence_sufficiency import (
    make_evidence_sufficiency_report,
    verify_evidence_sufficiency_report,
)
from rdllm.federation_handshake import (
    make_federation_handshake,
    verify_federation_handshake,
)
from rdllm.finance_ledger import (
    make_finance_ledger_attestation,
    verify_finance_ledger_attestation,
)
from rdllm.payment_execution import (
    make_payment_execution_report,
    verify_payment_execution_report,
)
from rdllm.payment_rail import (
    make_payment_rail_attestation,
    make_processor_batch_attestations,
    verify_payment_rail_attestation,
)
from rdllm.creator_payout_receipt import (
    make_creator_payout_receipt_report,
    verify_creator_payout_receipt_report,
)
from rdllm.rendered_attribution_audit import (
    make_rendered_attribution_audit,
    verify_rendered_attribution_audit,
)
from rdllm.training_memory_provenance import (
    load_training_memory_snapshots,
    make_training_memory_provenance_report,
    verify_training_memory_provenance_report,
)
from rdllm.evidence_locked_generation import (
    make_evidence_locked_generation_report,
    verify_evidence_locked_generation_report,
)
from rdllm.emission_enforcement import (
    make_emission_evidence_enforcement_report,
    verify_emission_evidence_enforcement_report,
)
from rdllm.live_emission_witness import (
    make_live_emission_witness_report,
    verify_live_emission_witness_report,
)
from rdllm.live_emission_transparency import (
    make_live_emission_transparency_log,
    make_live_emission_transparency_report,
    verify_live_emission_transparency_report,
)
from rdllm.attested_runtime import (
    make_attested_runtime_report,
    make_runtime_attestation_quote,
    make_runtime_measurement,
    verify_attested_runtime_report,
)
from rdllm.engine import RoyaltyDrivenLLM
from rdllm.grounding import evaluate_event_grounding_quality
from rdllm.interop import make_interop_bundle, verify_interop_bundle
from rdllm.integration_profile import (
    make_integration_profile,
    verify_integration_profile,
)
from rdllm.license_contract import (
    make_creator_license_contract,
    verify_creator_license_contract,
)
from rdllm.ledger import RoyaltyLedger
from rdllm.lineage import make_lineage_report, verify_lineage_report
from rdllm.media_attribution import (
    load_media_corpus,
    load_media_inputs,
    make_media_attribution_report,
    verify_media_attribution_report,
)
from rdllm.models import UsageEvent
from rdllm.model_signal import (
    load_model_signal_input,
    make_model_signal_report,
    verify_model_signal_report,
)
from rdllm.pinpoint_provenance import (
    load_pinpoint_provenance_input,
    make_pinpoint_provenance_report,
    verify_pinpoint_provenance_report,
)
from rdllm.private_audit import (
    make_private_audit_challenge_report,
    verify_private_audit_challenge_report,
)
from rdllm.provider_card import (
    make_provider_attribution_card,
    verify_provider_attribution_card,
)
from rdllm.proof_carrying_response import (
    make_proof_carrying_response,
    verify_proof_carrying_response,
)
from rdllm.proof_dependency_graph import (
    make_proof_dependency_graph,
    verify_proof_dependency_graph,
)
from rdllm.publication_monitor import (
    make_publication_monitor_report,
    verify_publication_monitor_report,
)
from rdllm.publication_witness import (
    make_publication_witness_report,
    verify_publication_witness_report,
)
from rdllm.trust_registry import (
    make_trust_registry_report,
    verify_trust_registry_report,
)
from rdllm.serving_gateway import (
    make_serving_gateway_report,
    verify_serving_gateway_report,
)
from rdllm.streaming_attribution import (
    make_streaming_attribution_manifest,
    verify_streaming_attribution_manifest,
)
from rdllm.conversation_attribution import (
    make_conversation_attribution_ledger,
    verify_conversation_attribution_ledger,
)
from rdllm.agent_tool_attribution import (
    make_agent_tool_attribution_ledger,
    verify_agent_tool_attribution_ledger,
)
from rdllm.provenance_eval import (
    load_provenance_benchmark,
    make_provenance_evaluation_report,
    verify_provenance_evaluation_report,
)
from rdllm.receipts import (
    make_attribution_receipt,
    public_receipt,
    verify_receipt,
)
from rdllm.revenue_allocation import (
    make_revenue_allocation_report,
    verify_revenue_allocation_report,
)
from rdllm.remittance import make_remittance_report, verify_remittance_report
from rdllm.response_envelope import (
    make_response_envelope,
    verify_response_envelope,
)
from rdllm.release_gate import (
    make_release_gate_report,
    verify_release_gate_report,
)
from rdllm.rights_remediation import (
    load_ledger,
    make_rights_remediation_report,
    verify_rights_remediation_report,
)
from rdllm.semantic_text_attribution import (
    load_semantic_text_inputs,
    make_semantic_text_attribution_report,
    verify_semantic_text_attribution_report,
)
from rdllm.settlement import (
    load_resolution,
    resolve_registry_escrow,
    verify_escrow_resolution,
)
from rdllm.source_verification import (
    make_source_verification_report,
    verify_source_verification_report,
)
from rdllm.source_confidence import (
    make_source_confidence_report,
    verify_source_confidence_report,
)
from rdllm.source_availability import (
    load_source_availability_snapshots,
    make_source_availability_report,
    verify_source_availability_report,
)
from rdllm.source_authenticity import (
    load_source_authenticity_signals,
    make_source_authenticity_report,
    verify_source_authenticity_report,
)
from rdllm.source_boundary import (
    make_source_boundary_report,
    verify_source_boundary_report,
)
from rdllm.statements import (
    make_royalty_statement,
    statement_summary,
    verify_royalty_statement,
)
from rdllm.telemetry import make_trace_exchange, verify_trace_exchange
from rdllm.training_summary import (
    make_training_content_summary,
    verify_training_content_summary,
)
from rdllm.transitive_attribution import (
    make_transitive_attribution_report,
    verify_transitive_attribution_report,
)
from rdllm.transparency import TransparencyLog, verify_inclusion


DEFAULT_PROMPTS = [
    "How should any AI system prove creator attribution for an answer?",
    "How can creators be paid from a usage based revenue share?",
    "What governance process handles disputes and licensing for AI training data?",
]

TEXT_ATTRIBUTION_OUTPUT = (
    "Every royalty bearing AI answer should have a provenance record. "
    "The record should include source identifiers, content hashes, retrieval scores, "
    "output citations, payout weights, and an event hash that allows auditors to "
    "replay the attribution."
)


def _verifier_secrets_from_args(values: list[str] | None) -> dict[str, str]:
    secrets: dict[str, str] = {}
    for value in values or []:
        if "=" not in value:
            raise SystemExit(
                "--verifier-secret must use verifier_id=secret format"
            )
        verifier_id, secret = value.split("=", 1)
        verifier_id = verifier_id.strip()
        if not verifier_id or not secret:
            raise SystemExit(
                "--verifier-secret must include a non-empty verifier id and secret"
            )
        secrets[verifier_id] = secret
    return secrets


def _watchtower_secrets_from_args(values: list[str] | None) -> dict[str, str]:
    secrets: dict[str, str] = {}
    for value in values or []:
        if "=" not in value:
            raise SystemExit(
                "--watchtower-secret must use watchtower_id=secret format"
            )
        watchtower_id, secret = value.split("=", 1)
        watchtower_id = watchtower_id.strip()
        if not watchtower_id or not secret:
            raise SystemExit(
                "--watchtower-secret must include a non-empty watchtower id and secret"
            )
        secrets[watchtower_id] = secret
    return secrets


def _processor_secrets_from_args(values: list[str] | None) -> dict[str, str]:
    secrets: dict[str, str] = {}
    for value in values or []:
        if "=" not in value:
            raise SystemExit(
                "--processor-secret must use processor_id=secret format"
            )
        processor_id, secret = value.split("=", 1)
        processor_id = processor_id.strip()
        if not processor_id or not secret:
            raise SystemExit(
                "--processor-secret must include a non-empty processor id and secret"
            )
        secrets[processor_id] = secret
    return secrets


def _bond_specs_from_args(values: list[str] | None) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for value in values or []:
        if "=" not in value:
            raise SystemExit(
                "--bond must use verifier_id=amount[:currency[:escrow_hash[:conflict_status]]] format"
            )
        verifier_id, payload = value.split("=", 1)
        parts = payload.split(":")
        if not verifier_id.strip() or not parts[0]:
            raise SystemExit("--bond must include a verifier id and amount")
        spec: dict[str, Any] = {
            "verifier_id": verifier_id.strip(),
            "bond_amount": parts[0],
        }
        if len(parts) > 1 and parts[1]:
            spec["bond_currency"] = parts[1]
        if len(parts) > 2 and parts[2]:
            spec["bond_escrow_account_hash"] = parts[2]
        if len(parts) > 3 and parts[3]:
            spec["conflict_status"] = parts[3]
        specs.append(spec)
    return specs


def _challenge_rows_from_args(values: list[str] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for value in values or []:
        if "=" not in value:
            raise SystemExit(
                "--challenge must use challenge_id=verifier_id:status:reason_code:evidence_hash format"
            )
        challenge_id, payload = value.split("=", 1)
        parts = payload.split(":")
        if len(parts) < 4:
            raise SystemExit(
                "--challenge must include verifier_id, status, reason_code, and evidence_hash"
            )
        rows.append(
            {
                "challenge_id": challenge_id.strip(),
                "verifier_id": parts[0],
                "status": parts[1],
                "reason_code": parts[2],
                "evidence_hash": parts[3],
                "blocking": True,
            }
        )
    return rows


def _named_json_from_args(values: list[str] | None) -> list[tuple[str, dict[str, Any]]]:
    rows: list[tuple[str, dict[str, Any]]] = []
    for index, value in enumerate(values or []):
        if "=" in value:
            name, path_value = value.split("=", 1)
            name = name.strip()
        else:
            path_value = value
            name = f"log-{index}"
        if not name:
            raise SystemExit("--transparency-log name must be non-empty")
        payload = json.loads(Path(path_value).read_text(encoding="utf-8"))
        rows.append((name, payload))
    return rows


def _json_payloads_from_args(values: list[str] | None) -> list[dict[str, Any]]:
    return [
        json.loads(Path(value).read_text(encoding="utf-8"))
        for value in values or []
    ]


def _trusted_attestors_from_args(
    values: list[str] | None,
) -> list[tuple[str, str, str] | tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str] | tuple[str, str, str, str]] = []
    for value in values or []:
        parts = value.split(":")
        if len(parts) not in (3, 4) or not all(parts[:3]):
            raise SystemExit(
                "--trusted-attestor must use attestor_id:platform_id:secret[:platform_type]"
            )
        if len(parts) == 4:
            rows.append((parts[0], parts[1], parts[2], parts[3]))
        else:
            rows.append((parts[0], parts[1], parts[2]))
    return rows


def _engine_from_args(args: argparse.Namespace) -> RoyaltyDrivenLLM:
    return RoyaltyDrivenLLM.from_corpus_file(
        args.corpus,
        creator_pool_rate=Decimal(args.creator_pool_rate),
        top_k=args.top_k,
        jurisdiction=args.jurisdiction,
        attestations_path=args.attestations,
        registry_report_path=args.registry_report,
        enforce_registry=args.enforce_registry,
    )


def run_demo(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    ledger = RoyaltyLedger()

    for prompt in DEFAULT_PROMPTS:
        event = engine.generate(prompt, gross_revenue=Decimal(args.gross_revenue))
        errors = engine.audit_event(event)
        if errors:
            raise SystemExit(f"audit failed for {event.event_id}: {errors}")
        ledger.record(event)

    text_event = engine.attribute_text(
        "External AI output submitted for owner attribution",
        TEXT_ATTRIBUTION_OUTPUT,
        gross_revenue=Decimal(args.gross_revenue),
    )
    errors = engine.audit_event(text_event)
    if errors:
        raise SystemExit(f"audit failed for {text_event.event_id}: {errors}")
    ledger.record(text_event)

    if args.ledger:
        ledger.write_json(args.ledger)

    print(json.dumps(ledger.to_dict(), indent=2, sort_keys=True))
    return 0


def run_once(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    if args.output:
        event = engine.attribute_text(
            args.prompt,
            args.output,
            gross_revenue=Decimal(args.gross_revenue),
        )
    else:
        event = engine.generate(args.prompt, gross_revenue=Decimal(args.gross_revenue))
    errors = engine.audit_event(event)
    result = event.to_dict()
    result["audit_errors"] = errors
    if args.ledger:
        ledger = RoyaltyLedger()
        ledger.record(event)
        ledger.write_json(args.ledger)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_answer(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    if args.output:
        event = engine.attribute_text(
            args.prompt,
            args.output,
            gross_revenue=Decimal(args.gross_revenue),
        )
    else:
        event = engine.generate(args.prompt, gross_revenue=Decimal(args.gross_revenue))
    errors = engine.audit_event(event)
    if errors:
        print(json.dumps({"audit_errors": errors}, indent=2, sort_keys=True))
        return 1
    print(event.output)
    return 0


def run_answer_card(args: argparse.Namespace) -> int:
    receipt: dict[str, object] | None = None
    trace: dict[str, object] | None = None
    if args.ledger:
        receipt = (
            json.loads(Path(args.receipt).read_text(encoding="utf-8"))
            if args.receipt
            else None
        )
        event_id = args.event_id or (
            receipt.get("payload", {}).get("event", {}).get("event_id")
            if receipt
            else None
        )
        if not event_id:
            raise SystemExit("--event-id is required when --ledger is used without --receipt")
        event = _event_from_ledger(args.ledger, str(event_id))
        trace = (
            json.loads(Path(args.trace).read_text(encoding="utf-8"))
            if args.trace
            else None
        )
    else:
        if not args.prompt:
            raise SystemExit("prompt is required when --ledger is not supplied")
        engine, event = _event_from_args(args)
        errors = engine.audit_event(event)
        if errors:
            print(json.dumps({"audit_errors": errors}, indent=2, sort_keys=True))
            return 1
        receipt = make_attribution_receipt(
            event,
            issuer=args.issuer,
            model_id=args.model_id,
            model_version=args.model_version,
            route_id=args.route_id,
            signing_secret=args.signing_secret,
        )
        trace = make_trace_exchange(event, receipt=receipt)
        if args.ledger_output:
            ledger = RoyaltyLedger()
            ledger.record(event)
            ledger.write_json(args.ledger_output)
        if args.receipt:
            Path(args.receipt).parent.mkdir(parents=True, exist_ok=True)
            Path(args.receipt).write_text(
                json.dumps(receipt, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        if args.trace:
            Path(args.trace).parent.mkdir(parents=True, exist_ok=True)
            Path(args.trace).write_text(
                json.dumps(trace, indent=2, sort_keys=True),
                encoding="utf-8",
            )

    card = make_answer_provenance_card(
        event,
        receipt=receipt,
        trace=trace,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.card:
        Path(args.card).parent.mkdir(parents=True, exist_ok=True)
        Path(args.card).write_text(
            json.dumps(card, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": "ok",
            "card": args.card,
            "card_hash": card["card_hash"],
            "event_id": event.event_id,
            "receipt_hash": card["event"]["receipt_hash"],
            "trace_hash": card["event"]["trace_hash"],
            "source_count": card["grounding"]["source_count"],
            "claim_count": card["grounding"]["claim_count"],
        }
    else:
        result = card
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_verify_answer_card(args: argparse.Namespace) -> int:
    card = json.loads(Path(args.card).read_text(encoding="utf-8"))
    receipt = (
        json.loads(Path(args.receipt).read_text(encoding="utf-8"))
        if args.receipt
        else None
    )
    trace = (
        json.loads(Path(args.trace).read_text(encoding="utf-8"))
        if args.trace
        else None
    )
    event_id = args.event_id or (
        receipt.get("payload", {}).get("event", {}).get("event_id")
        if receipt
        else card.get("event", {}).get("event_id")
    )
    event = _event_from_ledger(args.ledger, str(event_id))
    errors = verify_answer_provenance_card(
        event,
        card,
        receipt=receipt,
        trace=trace,
        signing_secret=args.signing_secret,
    )
    result = {
        "card": args.card,
        "ledger": args.ledger,
        "event_id": event.event_id,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "card_hash": card.get("card_hash", ""),
        "receipt_hash": card.get("event", {}).get("receipt_hash", ""),
        "trace_hash": card.get("event", {}).get("trace_hash", ""),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def _event_id_for_artifact(
    ledger_path: str | Path,
    *,
    event_id: str | None = None,
    answer_card: dict[str, object] | None = None,
) -> str:
    if event_id:
        return event_id
    if answer_card:
        card_event_id = answer_card.get("event", {}).get("event_id")  # type: ignore[union-attr]
        if card_event_id:
            return str(card_event_id)
    ledger_data = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
    events = ledger_data.get("events", [])
    if len(events) == 1 and events[0].get("event_id"):
        return str(events[0]["event_id"])
    raise SystemExit("--event-id is required when the ledger has multiple events")


def run_source_verification(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    answer_card = (
        json.loads(Path(args.answer_card).read_text(encoding="utf-8"))
        if args.answer_card
        else None
    )
    event_id = _event_id_for_artifact(
        args.ledger,
        event_id=args.event_id,
        answer_card=answer_card,
    )
    event = _event_from_ledger(args.ledger, event_id)
    report = make_source_verification_report(
        event,
        engine,
        answer_card=answer_card,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "event_id": event.event_id,
            "source_count": report["summary"]["source_count"],
            "claim_count": report["summary"]["claim_count"],
            "answer_card_bound": report["summary"]["answer_card_bound"],
            "issues": report["issues"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "verified" else 1


def run_verify_source_verification(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    answer_card = (
        json.loads(Path(args.answer_card).read_text(encoding="utf-8"))
        if args.answer_card
        else None
    )
    event_id = _event_id_for_artifact(
        args.ledger,
        event_id=args.event_id or report.get("event", {}).get("event_id"),
        answer_card=answer_card,
    )
    event = _event_from_ledger(args.ledger, event_id)
    errors = verify_source_verification_report(
        event,
        engine,
        report,
        answer_card=answer_card,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "ledger": args.ledger,
        "event_id": event.event_id,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_source_confidence_report(args: argparse.Namespace) -> int:
    answer_card = json.loads(Path(args.answer_card).read_text(encoding="utf-8"))
    source_report = json.loads(Path(args.source_report).read_text(encoding="utf-8"))
    creator_license_contract = json.loads(
        Path(args.creator_license_contract).read_text(encoding="utf-8")
    )
    report = make_source_confidence_report(
        answer_card=answer_card,
        source_verification_report=source_report,
        creator_license_contract=creator_license_contract,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "source_count": report["summary"]["source_count"],
            "claim_count": report["summary"]["claim_count"],
            "hallucination_issue_count": report["summary"][
                "hallucination_issue_count"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "verified" else 1


def run_verify_source_confidence_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    answer_card = json.loads(Path(args.answer_card).read_text(encoding="utf-8"))
    source_report = json.loads(Path(args.source_report).read_text(encoding="utf-8"))
    creator_license_contract = json.loads(
        Path(args.creator_license_contract).read_text(encoding="utf-8")
    )
    errors = verify_source_confidence_report(
        report,
        answer_card=answer_card,
        source_verification_report=source_report,
        creator_license_contract=creator_license_contract,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_citation_footer_contract(args: argparse.Namespace) -> int:
    response_envelope = json.loads(Path(args.response_envelope).read_text(encoding="utf-8"))
    contract = make_citation_footer_contract(
        response_envelope=response_envelope,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(contract, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": contract["summary"]["status"],
            "output": args.output,
            "contract_hash": contract["contract_hash"],
            "source_count": contract["summary"]["source_count"],
            "claim_count": contract["summary"]["claim_count"],
            "footer_line_count": contract["summary"]["footer_line_count"],
        }
    else:
        result = contract
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if contract["summary"]["status"] == "verified" else 1


def run_verify_citation_footer_contract(args: argparse.Namespace) -> int:
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    response_envelope = json.loads(Path(args.response_envelope).read_text(encoding="utf-8"))
    errors = verify_citation_footer_contract(
        contract,
        response_envelope=response_envelope,
        signing_secret=args.signing_secret,
    )
    result = {
        "contract": args.contract,
        "response_envelope": args.response_envelope,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "contract_hash": contract.get("contract_hash", ""),
        "summary": contract.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_source_availability_report(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    snapshots = load_source_availability_snapshots(args.snapshots)
    answer_card = json.loads(Path(args.answer_card).read_text(encoding="utf-8"))
    source_report = json.loads(Path(args.source_report).read_text(encoding="utf-8"))
    citation_footer_contract = json.loads(
        Path(args.citation_footer_contract).read_text(encoding="utf-8")
    )
    event_id = _event_id_for_artifact(
        args.ledger,
        event_id=args.event_id,
        answer_card=answer_card,
    )
    event = _event_from_ledger(args.ledger, event_id)
    report = make_source_availability_report(
        event,
        engine,
        snapshots,
        answer_card=answer_card,
        source_verification_report=source_report,
        citation_footer_contract=citation_footer_contract,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "event_id": event.event_id,
            "source_count": report["summary"]["source_count"],
            "inspectable_source_count": report["summary"][
                "inspectable_source_count"
            ],
            "issue_count": report["summary"]["issue_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "verified" else 1


def run_verify_source_availability_report(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    snapshots = load_source_availability_snapshots(args.snapshots)
    answer_card = json.loads(Path(args.answer_card).read_text(encoding="utf-8"))
    source_report = json.loads(Path(args.source_report).read_text(encoding="utf-8"))
    citation_footer_contract = json.loads(
        Path(args.citation_footer_contract).read_text(encoding="utf-8")
    )
    event_id = _event_id_for_artifact(
        args.ledger,
        event_id=args.event_id or report.get("event", {}).get("event_id"),
        answer_card=answer_card,
    )
    event = _event_from_ledger(args.ledger, event_id)
    errors = verify_source_availability_report(
        report,
        event,
        engine,
        snapshots,
        answer_card=answer_card,
        source_verification_report=source_report,
        citation_footer_contract=citation_footer_contract,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "ledger": args.ledger,
        "event_id": event.event_id,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_evidence_sufficiency_report(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    answer_card = json.loads(Path(args.answer_card).read_text(encoding="utf-8"))
    source_report = json.loads(Path(args.source_report).read_text(encoding="utf-8"))
    source_availability_report = json.loads(
        Path(args.source_availability_report).read_text(encoding="utf-8")
    )
    citation_footer_contract = json.loads(
        Path(args.citation_footer_contract).read_text(encoding="utf-8")
    )
    event_id = _event_id_for_artifact(
        args.ledger,
        event_id=args.event_id,
        answer_card=answer_card,
    )
    event = _event_from_ledger(args.ledger, event_id)
    report = make_evidence_sufficiency_report(
        event,
        engine,
        answer_card=answer_card,
        source_verification_report=source_report,
        source_availability_report=source_availability_report,
        citation_footer_contract=citation_footer_contract,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
        candidate_limit=args.candidate_limit,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "event_id": event.event_id,
            "claim_count": report["summary"]["claim_count"],
            "sufficient_claim_count": report["summary"]["sufficient_claim_count"],
            "issue_count": report["summary"]["issue_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "verified" else 1


def run_verify_evidence_sufficiency_report(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    answer_card = json.loads(Path(args.answer_card).read_text(encoding="utf-8"))
    source_report = json.loads(Path(args.source_report).read_text(encoding="utf-8"))
    source_availability_report = json.loads(
        Path(args.source_availability_report).read_text(encoding="utf-8")
    )
    citation_footer_contract = json.loads(
        Path(args.citation_footer_contract).read_text(encoding="utf-8")
    )
    event_id = _event_id_for_artifact(
        args.ledger,
        event_id=args.event_id or report.get("event", {}).get("event_id"),
        answer_card=answer_card,
    )
    event = _event_from_ledger(args.ledger, event_id)
    errors = verify_evidence_sufficiency_report(
        report,
        event,
        engine,
        answer_card=answer_card,
        source_verification_report=source_report,
        source_availability_report=source_availability_report,
        citation_footer_contract=citation_footer_contract,
        signing_secret=args.signing_secret,
        candidate_limit=args.candidate_limit,
    )
    result = {
        "report": args.report,
        "ledger": args.ledger,
        "event_id": event.event_id,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_counterevidence_report(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    answer_card = json.loads(Path(args.answer_card).read_text(encoding="utf-8"))
    source_report = json.loads(Path(args.source_report).read_text(encoding="utf-8"))
    source_availability_report = json.loads(
        Path(args.source_availability_report).read_text(encoding="utf-8")
    )
    evidence_sufficiency_report = json.loads(
        Path(args.evidence_sufficiency_report).read_text(encoding="utf-8")
    )
    citation_footer_contract = json.loads(
        Path(args.citation_footer_contract).read_text(encoding="utf-8")
    )
    event_id = _event_id_for_artifact(
        args.ledger,
        event_id=args.event_id,
        answer_card=answer_card,
    )
    event = _event_from_ledger(args.ledger, event_id)
    report = make_counterevidence_report(
        event,
        engine,
        answer_card=answer_card,
        source_verification_report=source_report,
        source_availability_report=source_availability_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        citation_footer_contract=citation_footer_contract,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
        candidate_limit=args.candidate_limit,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "event_id": event.event_id,
            "claim_count": report["summary"]["claim_count"],
            "counterevidence_candidate_count": report["summary"][
                "counterevidence_candidate_count"
            ],
            "unaddressed_counterevidence_count": report["summary"][
                "unaddressed_counterevidence_count"
            ],
            "issue_count": report["summary"]["issue_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "verified" else 1


def run_verify_counterevidence_report(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    answer_card = json.loads(Path(args.answer_card).read_text(encoding="utf-8"))
    source_report = json.loads(Path(args.source_report).read_text(encoding="utf-8"))
    source_availability_report = json.loads(
        Path(args.source_availability_report).read_text(encoding="utf-8")
    )
    evidence_sufficiency_report = json.loads(
        Path(args.evidence_sufficiency_report).read_text(encoding="utf-8")
    )
    citation_footer_contract = json.loads(
        Path(args.citation_footer_contract).read_text(encoding="utf-8")
    )
    event_id = _event_id_for_artifact(
        args.ledger,
        event_id=args.event_id or report.get("event", {}).get("event_id"),
        answer_card=answer_card,
    )
    event = _event_from_ledger(args.ledger, event_id)
    errors = verify_counterevidence_report(
        report,
        event,
        engine,
        answer_card=answer_card,
        source_verification_report=source_report,
        source_availability_report=source_availability_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        citation_footer_contract=citation_footer_contract,
        signing_secret=args.signing_secret,
        candidate_limit=args.candidate_limit,
    )
    result = {
        "report": args.report,
        "ledger": args.ledger,
        "event_id": event.event_id,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def _coverage_inputs_from_envelope(path: str) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any] | None,
    dict[str, Any] | None,
    dict[str, Any] | None,
]:
    envelope = json.loads(Path(path).read_text(encoding="utf-8"))
    artifacts = envelope.get("embedded_artifacts", {})
    return (
        envelope,
        artifacts.get("answer_provenance_card", {}),
        artifacts.get("source_verification_report", {}),
        artifacts.get("evidence_sufficiency_report"),
        artifacts.get("counterevidence_report"),
        artifacts.get("citation_footer_contract"),
    )


def run_answer_claim_coverage_report(args: argparse.Namespace) -> int:
    (
        envelope,
        answer_card,
        source_report,
        evidence_sufficiency_report,
        counterevidence_report,
        citation_footer_contract,
    ) = _coverage_inputs_from_envelope(args.response_envelope)
    response = envelope.get("response", {})
    report = make_answer_claim_coverage_report(
        rendered_output=str(response.get("rendered_output", "")),
        event_id=str(response.get("event_id", "")),
        event_hash=str(response.get("event_hash", "")),
        answer_hash=str(response.get("answer_hash", "")),
        answer_card=answer_card,
        source_verification_report=source_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
        citation_footer_contract=citation_footer_contract,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "answer_unit_count": report["summary"]["answer_unit_count"],
            "unsupported_unit_count": report["summary"]["unsupported_unit_count"],
            "issue_count": report["summary"]["issue_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "verified" else 1


def run_verify_answer_claim_coverage_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    (
        envelope,
        answer_card,
        source_report,
        evidence_sufficiency_report,
        counterevidence_report,
        citation_footer_contract,
    ) = _coverage_inputs_from_envelope(args.response_envelope)
    response = envelope.get("response", {})
    errors = verify_answer_claim_coverage_report(
        report,
        rendered_output=str(response.get("rendered_output", "")),
        event_id=str(response.get("event_id", "")),
        event_hash=str(response.get("event_hash", "")),
        answer_hash=str(response.get("answer_hash", "")),
        answer_card=answer_card,
        source_verification_report=source_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
        citation_footer_contract=citation_footer_contract,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "response_envelope": args.response_envelope,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def _context_closure_inputs_from_envelope(
    path: str,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any] | None,
]:
    envelope = json.loads(Path(path).read_text(encoding="utf-8"))
    artifacts = envelope.get("embedded_artifacts", {})
    return (
        artifacts.get("source_verification_report", {}),
        artifacts.get("answer_claim_coverage_report"),
        artifacts.get("generation_context_closure_report"),
    )


def _load_context_blocks(path: str | None) -> list[dict[str, Any]] | None:
    if not path:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("context_blocks", [])
    if not isinstance(data, list):
        raise ValueError("context blocks file must contain a list or object.context_blocks")
    return data


def run_generation_context_closure_report(args: argparse.Namespace) -> int:
    trace_exchange = json.loads(Path(args.trace_exchange).read_text(encoding="utf-8"))
    source_report, answer_coverage, _ = _context_closure_inputs_from_envelope(
        args.response_envelope
    )
    report = make_generation_context_closure_report(
        trace_exchange=trace_exchange,
        source_verification_report=source_report,
        answer_claim_coverage_report=answer_coverage,
        context_blocks=_load_context_blocks(args.context_blocks),
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "context_block_count": report["summary"]["context_block_count"],
            "missing_context_claim_count": report["summary"][
                "missing_context_claim_count"
            ],
            "issue_count": report["summary"]["issue_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "verified" else 1


def run_verify_generation_context_closure_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    trace_exchange = json.loads(Path(args.trace_exchange).read_text(encoding="utf-8"))
    source_report, answer_coverage, _ = _context_closure_inputs_from_envelope(
        args.response_envelope
    )
    errors = verify_generation_context_closure_report(
        report,
        trace_exchange=trace_exchange,
        source_verification_report=source_report,
        answer_claim_coverage_report=answer_coverage,
        context_blocks=_load_context_blocks(args.context_blocks),
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "response_envelope": args.response_envelope,
        "trace_exchange": args.trace_exchange,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_source_boundary_report(args: argparse.Namespace) -> int:
    trace_exchange = json.loads(Path(args.trace_exchange).read_text(encoding="utf-8"))
    source_report, _, context_closure = _context_closure_inputs_from_envelope(
        args.response_envelope
    )
    if not context_closure:
        raise ValueError("response envelope must embed generation_context_closure_report")
    report = make_source_boundary_report(
        trace_exchange=trace_exchange,
        source_verification_report=source_report,
        generation_context_closure_report=context_closure,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "context_block_count": report["summary"]["context_block_count"],
            "boundary_violation_count": report["summary"][
                "boundary_violation_count"
            ],
            "issue_count": report["summary"]["issue_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "verified" else 1


def run_verify_source_boundary_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    trace_exchange = json.loads(Path(args.trace_exchange).read_text(encoding="utf-8"))
    source_report, answer_coverage, context_closure = _context_closure_inputs_from_envelope(
        args.response_envelope
    )
    if not context_closure:
        raise ValueError("response envelope must embed generation_context_closure_report")
    errors = verify_source_boundary_report(
        report,
        trace_exchange=trace_exchange,
        source_verification_report=source_report,
        generation_context_closure_report=context_closure,
        answer_claim_coverage_report=answer_coverage,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "response_envelope": args.response_envelope,
        "trace_exchange": args.trace_exchange,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_source_authenticity_report(args: argparse.Namespace) -> int:
    source_availability_report = json.loads(
        Path(args.source_availability_report).read_text(encoding="utf-8")
    )
    source_boundary_report = json.loads(
        Path(args.source_boundary_report).read_text(encoding="utf-8")
    )
    creator_license_contract = json.loads(
        Path(args.creator_license_contract).read_text(encoding="utf-8")
    )
    source_confidence_report = (
        json.loads(Path(args.source_confidence_report).read_text(encoding="utf-8"))
        if args.source_confidence_report
        else None
    )
    signals = load_source_authenticity_signals(args.source_authenticity_signals)
    report = make_source_authenticity_report(
        source_availability_report=source_availability_report,
        source_boundary_report=source_boundary_report,
        creator_license_contract=creator_license_contract,
        source_confidence_report=source_confidence_report,
        source_authenticity_signals=signals,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "source_count": report["summary"]["source_count"],
            "verified_source_count": report["summary"]["verified_source_count"],
            "escrow_recommended_count": report["summary"][
                "escrow_recommended_count"
            ],
            "issue_count": report["summary"]["issue_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "verified" else 1


def run_verify_source_authenticity_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    source_availability_report = json.loads(
        Path(args.source_availability_report).read_text(encoding="utf-8")
    )
    source_boundary_report = json.loads(
        Path(args.source_boundary_report).read_text(encoding="utf-8")
    )
    creator_license_contract = json.loads(
        Path(args.creator_license_contract).read_text(encoding="utf-8")
    )
    source_confidence_report = (
        json.loads(Path(args.source_confidence_report).read_text(encoding="utf-8"))
        if args.source_confidence_report
        else None
    )
    signals = load_source_authenticity_signals(args.source_authenticity_signals)
    errors = verify_source_authenticity_report(
        report,
        source_availability_report=source_availability_report,
        source_boundary_report=source_boundary_report,
        creator_license_contract=creator_license_contract,
        source_confidence_report=source_confidence_report,
        source_authenticity_signals=signals,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "source_availability_report": args.source_availability_report,
        "source_boundary_report": args.source_boundary_report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_decision_provenance_report(args: argparse.Namespace) -> int:
    response_envelope = json.loads(
        Path(args.response_envelope).read_text(encoding="utf-8")
    )
    release_gate = json.loads(Path(args.release_gate).read_text(encoding="utf-8"))
    trace_exchange = json.loads(Path(args.trace_exchange).read_text(encoding="utf-8"))
    attribution_capsule = json.loads(
        Path(args.attribution_capsule).read_text(encoding="utf-8")
    )
    report = make_decision_provenance_report(
        response_envelope=response_envelope,
        release_gate=release_gate,
        trace_exchange=trace_exchange,
        attribution_capsule=attribution_capsule,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "decision_node_count": report["summary"]["decision_node_count"],
            "influence_edge_count": report["summary"]["influence_edge_count"],
            "issue_count": report["summary"]["issue_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "verified" else 1


def run_verify_decision_provenance_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    response_envelope = json.loads(
        Path(args.response_envelope).read_text(encoding="utf-8")
    )
    release_gate = json.loads(Path(args.release_gate).read_text(encoding="utf-8"))
    trace_exchange = json.loads(Path(args.trace_exchange).read_text(encoding="utf-8"))
    attribution_capsule = json.loads(
        Path(args.attribution_capsule).read_text(encoding="utf-8")
    )
    errors = verify_decision_provenance_report(
        report,
        response_envelope=response_envelope,
        release_gate=release_gate,
        trace_exchange=trace_exchange,
        attribution_capsule=attribution_capsule,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "response_envelope": args.response_envelope,
        "release_gate": args.release_gate,
        "trace_exchange": args.trace_exchange,
        "attribution_capsule": args.attribution_capsule,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_calibrated_attribution_report(args: argparse.Namespace) -> int:
    response_envelope = json.loads(
        Path(args.response_envelope).read_text(encoding="utf-8")
    )
    source_confidence_report = json.loads(
        Path(args.source_confidence_report).read_text(encoding="utf-8")
    )
    evidence_sufficiency_report = json.loads(
        Path(args.evidence_sufficiency_report).read_text(encoding="utf-8")
    )
    provenance_evaluation_report = json.loads(
        Path(args.provenance_evaluation_report).read_text(encoding="utf-8")
    )
    decision_provenance_report = json.loads(
        Path(args.decision_provenance_report).read_text(encoding="utf-8")
    )
    release_gate = json.loads(Path(args.release_gate).read_text(encoding="utf-8"))
    trace_exchange = json.loads(Path(args.trace_exchange).read_text(encoding="utf-8"))
    attribution_capsule = json.loads(
        Path(args.attribution_capsule).read_text(encoding="utf-8")
    )
    report = make_calibrated_attribution_report(
        response_envelope=response_envelope,
        source_confidence_report=source_confidence_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        provenance_evaluation_report=provenance_evaluation_report,
        decision_provenance_report=decision_provenance_report,
        release_gate=release_gate,
        trace_exchange=trace_exchange,
        attribution_capsule=attribution_capsule,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "claim_count": report["summary"]["claim_count"],
            "source_count": report["summary"]["source_count"],
            "issue_count": report["summary"]["issue_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "verified" else 1


def run_verify_calibrated_attribution_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    response_envelope = json.loads(
        Path(args.response_envelope).read_text(encoding="utf-8")
    )
    source_confidence_report = json.loads(
        Path(args.source_confidence_report).read_text(encoding="utf-8")
    )
    evidence_sufficiency_report = json.loads(
        Path(args.evidence_sufficiency_report).read_text(encoding="utf-8")
    )
    provenance_evaluation_report = json.loads(
        Path(args.provenance_evaluation_report).read_text(encoding="utf-8")
    )
    decision_provenance_report = json.loads(
        Path(args.decision_provenance_report).read_text(encoding="utf-8")
    )
    release_gate = json.loads(Path(args.release_gate).read_text(encoding="utf-8"))
    trace_exchange = json.loads(Path(args.trace_exchange).read_text(encoding="utf-8"))
    attribution_capsule = json.loads(
        Path(args.attribution_capsule).read_text(encoding="utf-8")
    )
    errors = verify_calibrated_attribution_report(
        report,
        response_envelope=response_envelope,
        source_confidence_report=source_confidence_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        provenance_evaluation_report=provenance_evaluation_report,
        decision_provenance_report=decision_provenance_report,
        release_gate=release_gate,
        trace_exchange=trace_exchange,
        attribution_capsule=attribution_capsule,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "response_envelope": args.response_envelope,
        "decision_provenance_report": args.decision_provenance_report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_private_audit_challenge(args: argparse.Namespace) -> int:
    package = json.loads(Path(args.package).read_text(encoding="utf-8"))
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    report = make_private_audit_challenge_report(
        package=package,
        receipt=receipt,
        requested_paths=args.path,
        auditor_id=args.auditor_id,
        challenge_nonce=args.challenge_nonce,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "requested_path_count": report["summary"]["requested_path_count"],
            "redacted_path_count": report["summary"]["redacted_path_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "verified" else 1


def run_verify_private_audit_challenge(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    package = json.loads(Path(args.package).read_text(encoding="utf-8"))
    receipt = (
        json.loads(Path(args.receipt).read_text(encoding="utf-8"))
        if args.receipt
        else None
    )
    errors = verify_private_audit_challenge_report(
        report,
        package=package,
        receipt=receipt,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "package": args.package,
        "receipt": args.receipt,
        "verification_mode": "private" if receipt else "public",
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_lineage_report(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    event_id = _event_id_for_artifact(args.ledger, event_id=args.event_id)
    event = _event_from_ledger(args.ledger, event_id)
    report = make_lineage_report(
        event,
        works=engine.works,
        creators=engine.creators,
        pass_through_rate=args.pass_through_rate,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "event_id": event.event_id,
            "derivative_source_count": report["summary"]["derivative_source_count"],
            "upstream_obligation_count": report["summary"][
                "upstream_obligation_count"
            ],
            "payout_conserved": report["summary"]["payout_conserved"],
            "issues": report["issues"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_lineage_report(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    event_id = _event_id_for_artifact(
        args.ledger,
        event_id=args.event_id or report.get("event", {}).get("event_id"),
    )
    event = _event_from_ledger(args.ledger, event_id)
    errors = verify_lineage_report(
        report,
        event,
        works=engine.works,
        creators=engine.creators,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "ledger": args.ledger,
        "event_id": event.event_id,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def _copied_output_from_args(args: argparse.Namespace) -> str:
    if getattr(args, "copied_output_file", None):
        return Path(args.copied_output_file).read_text(encoding="utf-8")
    if getattr(args, "copied_output", None):
        return str(args.copied_output)
    raise SystemExit("--copied-output or --copied-output-file is required")


def run_transitive_attribution_report(args: argparse.Namespace) -> int:
    upstream_capsule = json.loads(
        Path(args.upstream_capsule).read_text(encoding="utf-8")
    )
    upstream_response_envelope = json.loads(
        Path(args.upstream_response_envelope).read_text(encoding="utf-8")
    )
    event_id = _event_id_for_artifact(args.downstream_ledger, event_id=args.event_id)
    downstream_event = _event_from_ledger(args.downstream_ledger, event_id)
    copied_output = _copied_output_from_args(args)
    report = make_transitive_attribution_report(
        upstream_capsule=upstream_capsule,
        upstream_response_envelope=upstream_response_envelope,
        downstream_event=downstream_event,
        copied_output=copied_output,
        pass_through_rate=args.pass_through_rate,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "downstream_event_id": downstream_event.event_id,
            "upstream_source_count": report["summary"]["upstream_source_count"],
            "transitive_obligation_count": report["summary"][
                "transitive_obligation_count"
            ],
            "transitive_pool": report["summary"]["transitive_pool"],
            "anti_laundering_enforced": report["summary"][
                "anti_laundering_enforced"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_transitive_attribution_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    upstream_capsule = json.loads(
        Path(args.upstream_capsule).read_text(encoding="utf-8")
    )
    upstream_response_envelope = json.loads(
        Path(args.upstream_response_envelope).read_text(encoding="utf-8")
    )
    event_id = _event_id_for_artifact(
        args.downstream_ledger,
        event_id=args.event_id or report.get("downstream", {}).get("event_id"),
    )
    downstream_event = _event_from_ledger(args.downstream_ledger, event_id)
    copied_output = _copied_output_from_args(args)
    errors = verify_transitive_attribution_report(
        report,
        upstream_capsule=upstream_capsule,
        upstream_response_envelope=upstream_response_envelope,
        downstream_event=downstream_event,
        copied_output=copied_output,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "downstream_ledger": args.downstream_ledger,
        "event_id": downstream_event.event_id,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_clearinghouse_report(args: argparse.Namespace) -> int:
    royalty_statements = _load_json_many(args.statement)
    transitive_reports = _load_json_many(args.transitive_report)
    report = make_clearinghouse_report(
        royalty_statements=royalty_statements,
        transitive_reports=transitive_reports,
        issuer=args.issuer,
        settlement_currency=args.settlement_currency,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "input_artifact_count": report["summary"]["input_artifact_count"],
            "normalized_obligation_count": report["summary"][
                "normalized_obligation_count"
            ],
            "payable_total": report["summary"]["payable_total"],
            "escrow_total": report["summary"]["escrow_total"],
            "held_total": report["summary"]["held_total"],
            "double_payment_prevented": report["summary"][
                "double_payment_prevented"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_clearinghouse_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_clearinghouse_report(
        report,
        royalty_statements=_load_json_many(args.statement),
        transitive_reports=_load_json_many(args.transitive_report),
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_remittance_report(args: argparse.Namespace) -> int:
    clearinghouse_report = json.loads(
        Path(args.clearinghouse_report).read_text(encoding="utf-8")
    )
    creator_license_contract = json.loads(
        Path(args.creator_license_contract).read_text(encoding="utf-8")
    )
    report = make_remittance_report(
        clearinghouse_report=clearinghouse_report,
        creator_license_contract=creator_license_contract,
        issuer=args.issuer,
        payment_rail=args.payment_rail,
        escrow_account_id=args.escrow_account_id,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "payment_instruction_count": report["summary"][
                "payment_instruction_count"
            ],
            "payment_total": report["summary"]["payment_total"],
            "escrow_instruction_total": report["summary"][
                "escrow_instruction_total"
            ],
            "remittance_hold_count": report["summary"]["remittance_hold_count"],
            "instruction_only": report["summary"]["instruction_only"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_remittance_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    clearinghouse_report = json.loads(
        Path(args.clearinghouse_report).read_text(encoding="utf-8")
    )
    creator_license_contract = json.loads(
        Path(args.creator_license_contract).read_text(encoding="utf-8")
    )
    errors = verify_remittance_report(
        report,
        clearinghouse_report=clearinghouse_report,
        creator_license_contract=creator_license_contract,
        escrow_account_id=args.escrow_account_id,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_payment_execution_report(args: argparse.Namespace) -> int:
    remittance_report = json.loads(
        Path(args.remittance_report).read_text(encoding="utf-8")
    )
    processor_records = json.loads(
        Path(args.processor_records).read_text(encoding="utf-8")
    )
    report = make_payment_execution_report(
        remittance_report=remittance_report,
        processor_records=processor_records,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "payment_execution_count": report["summary"][
                "payment_execution_count"
            ],
            "escrow_execution_count": report["summary"][
                "escrow_execution_count"
            ],
            "hold_carryforward_count": report["summary"][
                "hold_carryforward_count"
            ],
            "executed_payment_total": report["summary"]["executed_payment_total"],
            "executed_escrow_total": report["summary"]["executed_escrow_total"],
            "external_payment_execution_attested": report["summary"][
                "external_payment_execution_attested"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_payment_execution_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    remittance_report = json.loads(
        Path(args.remittance_report).read_text(encoding="utf-8")
    )
    processor_records = json.loads(
        Path(args.processor_records).read_text(encoding="utf-8")
    )
    errors = verify_payment_execution_report(
        report,
        remittance_report=remittance_report,
        processor_records=processor_records,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_processor_batch_attestations(args: argparse.Namespace) -> int:
    payment_execution_report = json.loads(
        Path(args.payment_execution_report).read_text(encoding="utf-8")
    )
    attestations = make_processor_batch_attestations(
        payment_execution_report=payment_execution_report,
        processor_secrets=_processor_secrets_from_args(args.processor_secret),
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(attestations, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": "ready",
            "output": args.output,
            "attestation_count": len(attestations),
            "processor_ids": sorted(
                {str(row.get("processor_id", "")) for row in attestations}
            ),
        }
    else:
        result = attestations
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_payment_rail_attestation(args: argparse.Namespace) -> int:
    payment_execution_report = json.loads(
        Path(args.payment_execution_report).read_text(encoding="utf-8")
    )
    trust_registry = json.loads(Path(args.trust_registry).read_text(encoding="utf-8"))
    processor_attestations = json.loads(
        Path(args.processor_attestations).read_text(encoding="utf-8")
    )
    report = make_payment_rail_attestation(
        payment_execution_report=payment_execution_report,
        trust_registry=trust_registry,
        processor_attestations=processor_attestations,
        processor_secrets=_processor_secrets_from_args(args.processor_secret),
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "required_processor_count": report["summary"][
                "required_processor_count"
            ],
            "processor_attestation_count": report["summary"][
                "processor_attestation_count"
            ],
            "covered_batch_count": report["summary"]["covered_batch_count"],
            "signed_external_payment_rail_attested": report["summary"][
                "signed_external_payment_rail_attested"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_payment_rail_attestation(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    payment_execution_report = json.loads(
        Path(args.payment_execution_report).read_text(encoding="utf-8")
    )
    trust_registry = json.loads(Path(args.trust_registry).read_text(encoding="utf-8"))
    processor_attestations = json.loads(
        Path(args.processor_attestations).read_text(encoding="utf-8")
    )
    errors = verify_payment_rail_attestation(
        report,
        payment_execution_report=payment_execution_report,
        trust_registry=trust_registry,
        processor_attestations=processor_attestations,
        processor_secrets=_processor_secrets_from_args(args.processor_secret),
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_creator_payout_receipts(args: argparse.Namespace) -> int:
    clearinghouse_report = json.loads(
        Path(args.clearinghouse_report).read_text(encoding="utf-8")
    )
    remittance_report = json.loads(
        Path(args.remittance_report).read_text(encoding="utf-8")
    )
    payment_execution_report = json.loads(
        Path(args.payment_execution_report).read_text(encoding="utf-8")
    )
    payment_rail_attestation = json.loads(
        Path(args.payment_rail_attestation).read_text(encoding="utf-8")
    )
    report = make_creator_payout_receipt_report(
        clearinghouse_report=clearinghouse_report,
        remittance_report=remittance_report,
        payment_execution_report=payment_execution_report,
        payment_rail_attestation=payment_rail_attestation,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "creator_count": report["summary"]["creator_count"],
            "creator_payout_receipt_count": report["summary"][
                "creator_payout_receipt_count"
            ],
            "creator_payout_total": report["summary"]["creator_payout_total"],
            "creator_visible_payouts_verified": report["summary"][
                "creator_visible_payouts_verified"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_creator_payout_receipts(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    clearinghouse_report = json.loads(
        Path(args.clearinghouse_report).read_text(encoding="utf-8")
    )
    remittance_report = json.loads(
        Path(args.remittance_report).read_text(encoding="utf-8")
    )
    payment_execution_report = json.loads(
        Path(args.payment_execution_report).read_text(encoding="utf-8")
    )
    payment_rail_attestation = json.loads(
        Path(args.payment_rail_attestation).read_text(encoding="utf-8")
    )
    errors = verify_creator_payout_receipt_report(
        report,
        clearinghouse_report=clearinghouse_report,
        remittance_report=remittance_report,
        payment_execution_report=payment_execution_report,
        payment_rail_attestation=payment_rail_attestation,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_rendered_attribution_audit(args: argparse.Namespace) -> int:
    response_envelope = json.loads(Path(args.response_envelope).read_text(encoding="utf-8"))
    citation_footer_contract = json.loads(
        Path(args.citation_footer_contract).read_text(encoding="utf-8")
    )
    source_availability_report = json.loads(
        Path(args.source_availability_report).read_text(encoding="utf-8")
    )
    evidence_sufficiency_report = json.loads(
        Path(args.evidence_sufficiency_report).read_text(encoding="utf-8")
    )
    counterevidence_report = json.loads(
        Path(args.counterevidence_report).read_text(encoding="utf-8")
    )
    answer_claim_coverage_report = json.loads(
        Path(args.answer_claim_coverage_report).read_text(encoding="utf-8")
    )
    report = make_rendered_attribution_audit(
        response_envelope=response_envelope,
        citation_footer_contract=citation_footer_contract,
        source_availability_report=source_availability_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
        answer_claim_coverage_report=answer_claim_coverage_report,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "body_citation_label_count": report["summary"][
                "body_citation_label_count"
            ],
            "footer_source_count": report["summary"]["footer_source_count"],
            "claim_evidence_row_count": report["summary"][
                "claim_evidence_row_count"
            ],
            "rendered_markdown_attribution_verified": report["summary"][
                "rendered_markdown_attribution_verified"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_rendered_attribution_audit(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    response_envelope = json.loads(Path(args.response_envelope).read_text(encoding="utf-8"))
    citation_footer_contract = json.loads(
        Path(args.citation_footer_contract).read_text(encoding="utf-8")
    )
    source_availability_report = json.loads(
        Path(args.source_availability_report).read_text(encoding="utf-8")
    )
    evidence_sufficiency_report = json.loads(
        Path(args.evidence_sufficiency_report).read_text(encoding="utf-8")
    )
    counterevidence_report = json.loads(
        Path(args.counterevidence_report).read_text(encoding="utf-8")
    )
    answer_claim_coverage_report = json.loads(
        Path(args.answer_claim_coverage_report).read_text(encoding="utf-8")
    )
    errors = verify_rendered_attribution_audit(
        report,
        response_envelope=response_envelope,
        citation_footer_contract=citation_footer_contract,
        source_availability_report=source_availability_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
        answer_claim_coverage_report=answer_claim_coverage_report,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_training_memory_provenance(args: argparse.Namespace) -> int:
    response_envelope = json.loads(Path(args.response_envelope).read_text(encoding="utf-8"))
    rendered_attribution_audit = json.loads(
        Path(args.rendered_attribution_audit).read_text(encoding="utf-8")
    )
    creator_license_contract = json.loads(
        Path(args.creator_license_contract).read_text(encoding="utf-8")
    )
    training_content_summary = json.loads(
        Path(args.training_content_summary).read_text(encoding="utf-8")
    )
    source_snapshots = load_training_memory_snapshots(args.source_snapshots)
    report = make_training_memory_provenance_report(
        response_envelope=response_envelope,
        rendered_attribution_audit=rendered_attribution_audit,
        creator_license_contract=creator_license_contract,
        training_content_summary=training_content_summary,
        source_snapshots=source_snapshots,
        min_match_tokens=args.min_match_tokens,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "detected_memory_span_count": report["summary"][
                "detected_memory_span_count"
            ],
            "hidden_memory_span_count": report["summary"][
                "hidden_memory_span_count"
            ],
            "training_memory_provenance_verified": report["summary"][
                "training_memory_provenance_verified"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_training_memory_provenance(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    response_envelope = json.loads(Path(args.response_envelope).read_text(encoding="utf-8"))
    rendered_attribution_audit = json.loads(
        Path(args.rendered_attribution_audit).read_text(encoding="utf-8")
    )
    creator_license_contract = json.loads(
        Path(args.creator_license_contract).read_text(encoding="utf-8")
    )
    training_content_summary = json.loads(
        Path(args.training_content_summary).read_text(encoding="utf-8")
    )
    source_snapshots = load_training_memory_snapshots(args.source_snapshots)
    errors = verify_training_memory_provenance_report(
        report,
        response_envelope=response_envelope,
        rendered_attribution_audit=rendered_attribution_audit,
        creator_license_contract=creator_license_contract,
        training_content_summary=training_content_summary,
        source_snapshots=source_snapshots,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_evidence_locked_generation(args: argparse.Namespace) -> int:
    response_envelope = json.loads(Path(args.response_envelope).read_text(encoding="utf-8"))
    answer_claim_coverage_report = json.loads(
        Path(args.answer_claim_coverage_report).read_text(encoding="utf-8")
    )
    generation_context_closure_report = json.loads(
        Path(args.generation_context_closure_report).read_text(encoding="utf-8")
    )
    citation_footer_contract = json.loads(
        Path(args.citation_footer_contract).read_text(encoding="utf-8")
    )
    rendered_attribution_audit = json.loads(
        Path(args.rendered_attribution_audit).read_text(encoding="utf-8")
    )
    training_memory_provenance = json.loads(
        Path(args.training_memory_provenance).read_text(encoding="utf-8")
    )
    report = make_evidence_locked_generation_report(
        response_envelope=response_envelope,
        answer_claim_coverage_report=answer_claim_coverage_report,
        generation_context_closure_report=generation_context_closure_report,
        citation_footer_contract=citation_footer_contract,
        rendered_attribution_audit=rendered_attribution_audit,
        training_memory_provenance=training_memory_provenance,
        lock_created_at=args.lock_created_at,
        generation_started_at=args.generation_started_at,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "evidence_lock_count": report["summary"]["evidence_lock_count"],
            "satisfied_lock_count": report["summary"]["satisfied_lock_count"],
            "post_hoc_rationalization_blocked": report["summary"][
                "post_hoc_rationalization_blocked"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_evidence_locked_generation(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    response_envelope = json.loads(Path(args.response_envelope).read_text(encoding="utf-8"))
    answer_claim_coverage_report = json.loads(
        Path(args.answer_claim_coverage_report).read_text(encoding="utf-8")
    )
    generation_context_closure_report = json.loads(
        Path(args.generation_context_closure_report).read_text(encoding="utf-8")
    )
    citation_footer_contract = json.loads(
        Path(args.citation_footer_contract).read_text(encoding="utf-8")
    )
    rendered_attribution_audit = json.loads(
        Path(args.rendered_attribution_audit).read_text(encoding="utf-8")
    )
    training_memory_provenance = json.loads(
        Path(args.training_memory_provenance).read_text(encoding="utf-8")
    )
    errors = verify_evidence_locked_generation_report(
        report,
        response_envelope=response_envelope,
        answer_claim_coverage_report=answer_claim_coverage_report,
        generation_context_closure_report=generation_context_closure_report,
        citation_footer_contract=citation_footer_contract,
        rendered_attribution_audit=rendered_attribution_audit,
        training_memory_provenance=training_memory_provenance,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_emission_evidence_enforcement(args: argparse.Namespace) -> int:
    response_envelope = json.loads(Path(args.response_envelope).read_text(encoding="utf-8"))
    answer_claim_coverage_report = json.loads(
        Path(args.answer_claim_coverage_report).read_text(encoding="utf-8")
    )
    evidence_locked_generation = json.loads(
        Path(args.evidence_locked_generation).read_text(encoding="utf-8")
    )
    proof_carrying_response = json.loads(
        Path(args.proof_carrying_response).read_text(encoding="utf-8")
    )
    serving_gateway_report = json.loads(
        Path(args.serving_gateway_report).read_text(encoding="utf-8")
    )
    streaming_attribution_manifest = json.loads(
        Path(args.streaming_attribution_manifest).read_text(encoding="utf-8")
    )
    report = make_emission_evidence_enforcement_report(
        response_envelope=response_envelope,
        answer_claim_coverage_report=answer_claim_coverage_report,
        evidence_locked_generation=evidence_locked_generation,
        proof_carrying_response=proof_carrying_response,
        serving_gateway_report=serving_gateway_report,
        streaming_attribution_manifest=streaming_attribution_manifest,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "emission_unit_count": report["summary"]["emission_unit_count"],
            "authorized_emission_unit_count": report["summary"][
                "authorized_emission_unit_count"
            ],
            "serving_emission_enforced": report["summary"][
                "serving_emission_enforced"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_emission_evidence_enforcement(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    response_envelope = json.loads(Path(args.response_envelope).read_text(encoding="utf-8"))
    answer_claim_coverage_report = json.loads(
        Path(args.answer_claim_coverage_report).read_text(encoding="utf-8")
    )
    evidence_locked_generation = json.loads(
        Path(args.evidence_locked_generation).read_text(encoding="utf-8")
    )
    proof_carrying_response = json.loads(
        Path(args.proof_carrying_response).read_text(encoding="utf-8")
    )
    serving_gateway_report = json.loads(
        Path(args.serving_gateway_report).read_text(encoding="utf-8")
    )
    streaming_attribution_manifest = json.loads(
        Path(args.streaming_attribution_manifest).read_text(encoding="utf-8")
    )
    errors = verify_emission_evidence_enforcement_report(
        report,
        response_envelope=response_envelope,
        answer_claim_coverage_report=answer_claim_coverage_report,
        evidence_locked_generation=evidence_locked_generation,
        proof_carrying_response=proof_carrying_response,
        serving_gateway_report=serving_gateway_report,
        streaming_attribution_manifest=streaming_attribution_manifest,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_live_emission_witness(args: argparse.Namespace) -> int:
    emission_evidence_enforcement = json.loads(
        Path(args.emission_evidence_enforcement).read_text(encoding="utf-8")
    )
    streaming_attribution_manifest = json.loads(
        Path(args.streaming_attribution_manifest).read_text(encoding="utf-8")
    )
    report = make_live_emission_witness_report(
        emission_evidence_enforcement=emission_evidence_enforcement,
        streaming_attribution_manifest=streaming_attribution_manifest,
        witnesses=_load_witnesses(args.witness),
        required_quorum=args.required_quorum,
        minimum_independent_organizations=args.minimum_independent_organizations,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "live_witness_hash": report["live_witness_hash"],
            "witness_count": report["summary"]["witness_count"],
            "required_quorum": report["summary"]["required_quorum"],
            "chunk_subject_count": report["summary"]["chunk_subject_count"],
            "live_emission_witnessed": report["summary"][
                "live_emission_witnessed"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_live_emission_witness(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    emission_evidence_enforcement = json.loads(
        Path(args.emission_evidence_enforcement).read_text(encoding="utf-8")
    )
    streaming_attribution_manifest = json.loads(
        Path(args.streaming_attribution_manifest).read_text(encoding="utf-8")
    )
    errors = verify_live_emission_witness_report(
        report,
        emission_evidence_enforcement=emission_evidence_enforcement,
        streaming_attribution_manifest=streaming_attribution_manifest,
        witnesses=_load_witnesses(args.witness),
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "live_witness_hash": report.get("live_witness_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_live_emission_transparency_log(args: argparse.Namespace) -> int:
    live_emission_witness = json.loads(
        Path(args.live_emission_witness).read_text(encoding="utf-8")
    )
    existing_entries = []
    if args.existing_log:
        existing_log = json.loads(Path(args.existing_log).read_text(encoding="utf-8"))
        existing_entries = list(existing_log.get("entries", []))
    log = make_live_emission_transparency_log(
        live_emission_witness,
        log_id=args.log_id,
        existing_entries=existing_entries,
        include_attestations=not args.report_only,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(log, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": "ready",
            "output": args.output,
            "log_id": log["log_id"],
            "tree_size": log["tree_size"],
            "root": log["root"],
        }
    else:
        result = log
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_live_emission_transparency(args: argparse.Namespace) -> int:
    live_emission_witness = json.loads(
        Path(args.live_emission_witness).read_text(encoding="utf-8")
    )
    report = make_live_emission_transparency_report(
        live_emission_witness=live_emission_witness,
        transparency_logs=_named_json_from_args(args.transparency_log),
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "live_emission_transparency_hash": report[
                "live_emission_transparency_hash"
            ],
            "required_subject_count": report["summary"]["required_subject_count"],
            "latest_tree_size": report["summary"]["latest_tree_size"],
            "live_emission_transparency_included": report["summary"][
                "live_emission_transparency_included"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_live_emission_transparency(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    live_emission_witness = json.loads(
        Path(args.live_emission_witness).read_text(encoding="utf-8")
    )
    errors = verify_live_emission_transparency_report(
        report,
        live_emission_witness=live_emission_witness,
        transparency_logs=_named_json_from_args(args.transparency_log),
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "live_emission_transparency_hash": report.get(
            "live_emission_transparency_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_runtime_measurement(args: argparse.Namespace) -> int:
    measurement = make_runtime_measurement(
        runtime_id=args.runtime_id,
        runtime_version=args.runtime_version,
        source_commit_hash=args.source_commit_hash,
        container_image_hash=args.container_image_hash,
        enforcement_binary_hash=args.enforcement_binary_hash,
        policy_bundle_hash=args.policy_bundle_hash,
        model_binding_hash=args.model_binding_hash,
        verifier_bundle_hash=args.verifier_bundle_hash,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(measurement, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": "ready",
            "output": args.output,
            "runtime_id": measurement["runtime_id"],
            "measurement_hash": measurement["measurement_hash"],
        }
    else:
        result = measurement
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_runtime_attestation_quote(args: argparse.Namespace) -> int:
    runtime_measurement = json.loads(
        Path(args.runtime_measurement).read_text(encoding="utf-8")
    )
    live_emission_transparency = json.loads(
        Path(args.live_emission_transparency).read_text(encoding="utf-8")
    )
    proof_carrying_response = json.loads(
        Path(args.proof_carrying_response).read_text(encoding="utf-8")
    )
    serving_gateway_report = json.loads(
        Path(args.serving_gateway_report).read_text(encoding="utf-8")
    )
    evidence_locked_generation = json.loads(
        Path(args.evidence_locked_generation).read_text(encoding="utf-8")
    )
    quote = make_runtime_attestation_quote(
        runtime_measurement=runtime_measurement,
        live_emission_transparency=live_emission_transparency,
        proof_carrying_response=proof_carrying_response,
        serving_gateway_report=serving_gateway_report,
        evidence_locked_generation=evidence_locked_generation,
        attestor_id=args.attestor_id,
        platform_id=args.platform_id,
        platform_type=args.platform_type,
        attestor_secret=args.attestor_secret,
        created_at=args.created_at,
        expires_at=args.expires_at,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(quote, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": "ready",
            "output": args.output,
            "quote_hash": quote["quote_hash"],
            "runtime_measurement_hash": quote["runtime_measurement"].get(
                "measurement_hash", ""
            ),
            "subject_binding_root": quote["subject_bindings"].get(
                "subject_binding_root", ""
            ),
        }
    else:
        result = quote
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_attested_runtime(args: argparse.Namespace) -> int:
    live_emission_transparency = json.loads(
        Path(args.live_emission_transparency).read_text(encoding="utf-8")
    )
    proof_carrying_response = json.loads(
        Path(args.proof_carrying_response).read_text(encoding="utf-8")
    )
    serving_gateway_report = json.loads(
        Path(args.serving_gateway_report).read_text(encoding="utf-8")
    )
    evidence_locked_generation = json.loads(
        Path(args.evidence_locked_generation).read_text(encoding="utf-8")
    )
    runtime_measurement = json.loads(
        Path(args.runtime_measurement).read_text(encoding="utf-8")
    )
    report = make_attested_runtime_report(
        live_emission_transparency=live_emission_transparency,
        proof_carrying_response=proof_carrying_response,
        serving_gateway_report=serving_gateway_report,
        evidence_locked_generation=evidence_locked_generation,
        runtime_measurement=runtime_measurement,
        runtime_quotes=_json_payloads_from_args(args.runtime_quote),
        trusted_attestors=_trusted_attestors_from_args(args.trusted_attestor),
        minimum_quote_count=args.minimum_quote_count,
        issuer=args.issuer,
        created_at=args.created_at,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "attested_runtime_hash": report["attested_runtime_hash"],
            "accepted_quote_count": report["summary"]["accepted_quote_count"],
            "runtime_measurement_hash": report["summary"]["runtime_measurement_hash"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_attested_runtime(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    live_emission_transparency = json.loads(
        Path(args.live_emission_transparency).read_text(encoding="utf-8")
    )
    proof_carrying_response = json.loads(
        Path(args.proof_carrying_response).read_text(encoding="utf-8")
    )
    serving_gateway_report = json.loads(
        Path(args.serving_gateway_report).read_text(encoding="utf-8")
    )
    evidence_locked_generation = json.loads(
        Path(args.evidence_locked_generation).read_text(encoding="utf-8")
    )
    runtime_measurement = json.loads(
        Path(args.runtime_measurement).read_text(encoding="utf-8")
    )
    errors = verify_attested_runtime_report(
        report,
        live_emission_transparency=live_emission_transparency,
        proof_carrying_response=proof_carrying_response,
        serving_gateway_report=serving_gateway_report,
        evidence_locked_generation=evidence_locked_generation,
        runtime_measurement=runtime_measurement,
        runtime_quotes=_json_payloads_from_args(args.runtime_quote),
        trusted_attestors=_trusted_attestors_from_args(args.trusted_attestor),
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "attested_runtime_hash": report.get("attested_runtime_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_provenance_evaluation(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    benchmark_cases = load_provenance_benchmark(args.benchmark)
    report = make_provenance_evaluation_report(
        engine,
        benchmark_cases,
        issuer=args.issuer,
        provider=args.provider,
        model_id=args.model_id,
        model_version=args.model_version,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "case_count": report["summary"]["case_count"],
            "score": report["summary"]["score"],
            "top1_accuracy": report["summary"]["top1_accuracy"],
            "decoy_resistance_rate": report["summary"]["decoy_resistance_rate"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "passed" else 1


def run_verify_provenance_evaluation(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    benchmark_cases = load_provenance_benchmark(args.benchmark)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_provenance_evaluation_report(
        engine,
        report,
        benchmark_cases,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "benchmark": args.benchmark,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_counterfactual_report(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    event_id = _event_id_for_artifact(args.ledger, event_id=args.event_id)
    event = _event_from_ledger(args.ledger, event_id)
    report = make_counterfactual_report(
        event,
        engine,
        min_impact_margin=args.min_impact_margin,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "event_id": event.event_id,
            "subject_work_count": report["summary"]["subject_work_count"],
            "decisive_source_count": report["summary"]["decisive_source_count"],
            "average_impact_margin": report["summary"]["average_impact_margin"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_counterfactual_report(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    event_id = _event_id_for_artifact(
        args.ledger,
        event_id=args.event_id or report.get("event", {}).get("event_id"),
    )
    event = _event_from_ledger(args.ledger, event_id)
    errors = verify_counterfactual_report(
        report,
        event,
        engine,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "ledger": args.ledger,
        "event_id": event.event_id,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_media_attribution(args: argparse.Namespace) -> int:
    media_corpus = load_media_corpus(args.media_corpus)
    submitted_media = load_media_inputs(args.submitted_media)
    report = make_media_attribution_report(
        media_corpus,
        submitted_media,
        gross_revenue=Decimal(args.media_gross_revenue),
        creator_pool_rate=Decimal(args.media_creator_pool_rate),
        accept_threshold=args.accept_threshold,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "input_count": report["summary"]["input_count"],
            "matched_count": report["summary"]["matched_count"],
            "escrow_count": report["summary"]["escrow_count"],
            "creator_pool": report["economics"]["creator_pool"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_media_attribution(args: argparse.Namespace) -> int:
    media_corpus = load_media_corpus(args.media_corpus)
    submitted_media = load_media_inputs(args.submitted_media)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_media_attribution_report(
        report,
        media_corpus,
        submitted_media,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "media_corpus": args.media_corpus,
        "submitted_media": args.submitted_media,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_model_signal_report(args: argparse.Namespace) -> int:
    signal_input = load_model_signal_input(args.signal_input)
    report = make_model_signal_report(
        signal_input,
        gross_revenue=Decimal(args.signal_gross_revenue),
        creator_pool_rate=Decimal(args.signal_creator_pool_rate),
        accept_threshold=args.accept_threshold,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "signal_count": report["summary"]["signal_count"],
            "accepted_signal_count": report["summary"]["accepted_signal_count"],
            "escrow_signal_count": report["summary"]["escrow_signal_count"],
            "creator_pool": report["economics"]["creator_pool"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_model_signal_report(args: argparse.Namespace) -> int:
    signal_input = load_model_signal_input(args.signal_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_model_signal_report(
        report,
        signal_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "signal_input": args.signal_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_pinpoint_provenance_report(args: argparse.Namespace) -> int:
    provenance_input = load_pinpoint_provenance_input(args.pinpoint_input)
    report = make_pinpoint_provenance_report(
        provenance_input,
        gross_revenue=Decimal(args.pinpoint_gross_revenue),
        creator_pool_rate=Decimal(args.pinpoint_creator_pool_rate),
        accept_threshold=args.accept_threshold,
        min_margin=args.min_margin,
        min_critical_recall=args.min_critical_recall,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "claim_count": report["summary"]["claim_count"],
            "accepted_claim_count": report["summary"]["accepted_claim_count"],
            "escrow_claim_count": report["summary"]["escrow_claim_count"],
            "anti_document_rejected_count": report["summary"][
                "anti_document_rejected_count"
            ],
            "creator_pool": report["economics"]["creator_pool"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_pinpoint_provenance_report(args: argparse.Namespace) -> int:
    provenance_input = load_pinpoint_provenance_input(args.pinpoint_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_pinpoint_provenance_report(
        report,
        provenance_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "pinpoint_input": args.pinpoint_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_claim_source_attribution_report(args: argparse.Namespace) -> int:
    attribution_input = load_claim_source_attribution_input(args.attribution_input)
    report = make_claim_source_attribution_report(
        attribution_input,
        gross_revenue=Decimal(args.gross_revenue),
        creator_pool_rate=Decimal(args.creator_pool_rate),
        accept_threshold=args.accept_threshold,
        min_margin=args.min_margin,
        min_anti_margin=args.min_anti_margin,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "claim_count": report["summary"]["claim_count"],
            "grounded_claim_count": report["summary"]["grounded_claim_count"],
            "escrow_claim_count": report["summary"]["escrow_claim_count"],
            "accepted_source_count": report["summary"]["accepted_source_count"],
            "footer_hash": report["summary"]["footer_hash"],
            "creator_pool": report["economics"]["creator_pool"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_claim_source_attribution_report(args: argparse.Namespace) -> int:
    attribution_input = load_claim_source_attribution_input(args.attribution_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_claim_source_attribution_report(
        report,
        attribution_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "attribution_input": args.attribution_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_evidence_utility_attribution_report(args: argparse.Namespace) -> int:
    utility_input = load_evidence_utility_input(args.utility_input)
    report = make_evidence_utility_attribution_report(
        utility_input,
        gross_revenue=Decimal(args.gross_revenue),
        creator_pool_rate=Decimal(args.creator_pool_rate),
        min_utility=args.min_utility,
        max_duplicate_credit_inflation=args.max_duplicate_credit_inflation,
        max_duplicate_trace_drift=args.max_duplicate_trace_drift,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "claim_count": report["summary"]["claim_count"],
            "causally_grounded_claim_count": report["summary"][
                "causally_grounded_claim_count"
            ],
            "accepted_source_count": report["summary"]["accepted_source_count"],
            "spurious_source_rejection_count": report["summary"][
                "spurious_source_rejection_count"
            ],
            "context_drift_rejection_count": report["summary"][
                "context_drift_rejection_count"
            ],
            "footer_hash": report["summary"]["footer_hash"],
            "creator_pool": report["economics"]["creator_pool"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_evidence_utility_attribution_report(args: argparse.Namespace) -> int:
    utility_input = load_evidence_utility_input(args.utility_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_evidence_utility_attribution_report(
        report,
        utility_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "utility_input": args.utility_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_parametric_memory_attribution_report(args: argparse.Namespace) -> int:
    attribution_input = load_parametric_memory_input(args.parametric_input)
    report = make_parametric_memory_attribution_report(
        attribution_input,
        gross_revenue=Decimal(args.gross_revenue),
        creator_pool_rate=Decimal(args.creator_pool_rate),
        min_support=args.min_support,
        min_memory=args.min_memory,
        min_influence=args.min_influence,
        min_anti_margin=args.min_anti_margin,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "claim_count": report["summary"]["claim_count"],
            "parametric_grounded_claim_count": report["summary"][
                "parametric_grounded_claim_count"
            ],
            "accepted_source_count": report["summary"]["accepted_source_count"],
            "anti_document_rejection_count": report["summary"][
                "anti_document_rejection_count"
            ],
            "context_contamination_rejection_count": report["summary"][
                "context_contamination_rejection_count"
            ],
            "footer_hash": report["summary"]["footer_hash"],
            "creator_pool": report["economics"]["creator_pool"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_parametric_memory_attribution_report(args: argparse.Namespace) -> int:
    attribution_input = load_parametric_memory_input(args.parametric_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_parametric_memory_attribution_report(
        report,
        attribution_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "parametric_input": args.parametric_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_style_influence_attribution_report(args: argparse.Namespace) -> int:
    style_input = load_style_influence_input(args.style_input)
    report = make_style_influence_attribution_report(
        style_input,
        gross_revenue=Decimal(args.gross_revenue),
        creator_pool_rate=Decimal(args.creator_pool_rate),
        accept_threshold=args.accept_threshold,
        min_style_margin=args.min_style_margin,
        min_anti_margin=args.min_anti_margin,
        max_content_overlap=args.max_content_overlap,
        blend_window=args.blend_window,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "output_count": report["summary"]["output_count"],
            "style_profile_count": report["summary"]["style_profile_count"],
            "accepted_style_count": report["summary"]["accepted_style_count"],
            "style_footer_count": report["summary"]["style_footer_count"],
            "anti_style_rejection_count": report["summary"][
                "anti_style_rejection_count"
            ],
            "copy_overlap_rejection_count": report["summary"][
                "copy_overlap_rejection_count"
            ],
            "license_block_count": report["summary"]["license_block_count"],
            "creator_pool": report["economics"]["creator_pool"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_style_influence_attribution_report(args: argparse.Namespace) -> int:
    style_input = load_style_influence_input(args.style_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_style_influence_attribution_report(
        report,
        style_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "style_input": args.style_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_model_lineage_attribution_report(args: argparse.Namespace) -> int:
    model_input = load_model_lineage_input(args.model_lineage_input)
    report = make_model_lineage_attribution_report(
        model_input,
        gross_revenue=Decimal(args.gross_revenue),
        creator_pool_rate=Decimal(args.creator_pool_rate),
        model_lineage_rate=Decimal(args.model_lineage_rate),
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "student_model_id": report["summary"]["student_model_id"],
            "training_item_count": report["summary"]["training_item_count"],
            "accepted_training_item_count": report["summary"][
                "accepted_training_item_count"
            ],
            "settlement_obligation_count": report["summary"][
                "settlement_obligation_count"
            ],
            "duplicate_training_item_count": report["summary"][
                "duplicate_training_item_count"
            ],
            "escrow_item_count": report["summary"]["escrow_item_count"],
            "model_lineage_pool": report["summary"]["model_lineage_pool"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_model_lineage_attribution_report(args: argparse.Namespace) -> int:
    model_input = load_model_lineage_input(args.model_lineage_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_model_lineage_attribution_report(
        report,
        model_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "model_lineage_input": args.model_lineage_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_black_box_model_provenance_report(args: argparse.Namespace) -> int:
    provenance_input = load_black_box_model_provenance_input(
        args.black_box_model_provenance_input
    )
    report = make_black_box_model_provenance_report(
        provenance_input,
        gross_revenue=Decimal(args.gross_revenue),
        creator_pool_rate=Decimal(args.creator_pool_rate),
        provenance_challenge_rate=Decimal(args.provenance_challenge_rate),
        confidence_level=Decimal(args.confidence_level),
        min_effect=Decimal(args.min_effect),
        min_challenge_count=args.min_challenge_count,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "challenge_decision": report["summary"]["challenge_decision"],
            "challenge_count": report["summary"]["challenge_count"],
            "candidate_model_count": report["summary"]["candidate_model_count"],
            "model_provenance_set_count": report["summary"][
                "model_provenance_set_count"
            ],
            "settlement_obligation_count": report["summary"][
                "settlement_obligation_count"
            ],
            "escrow_row_count": report["summary"]["escrow_row_count"],
            "provenance_challenge_pool": report["summary"][
                "provenance_challenge_pool"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] in {"ready", "ready_no_derivative_signal"} else 1


def run_verify_black_box_model_provenance_report(args: argparse.Namespace) -> int:
    provenance_input = load_black_box_model_provenance_input(
        args.black_box_model_provenance_input
    )
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_black_box_model_provenance_report(
        report,
        provenance_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "black_box_model_provenance_input": args.black_box_model_provenance_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_attribution_dispute_adjudication_report(args: argparse.Namespace) -> int:
    dispute_input = load_attribution_dispute_adjudication_input(
        args.attribution_dispute_input
    )
    report = make_attribution_dispute_adjudication_report(
        dispute_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "case_id": report["summary"]["case_id"],
            "accepted_claim_count": report["summary"]["accepted_claim_count"],
            "settlement_release_count": report["summary"]["settlement_release_count"],
            "escrow_freeze_count": report["summary"]["escrow_freeze_count"],
            "appeal_state": report["summary"]["appeal_state"],
            "released_total": report["summary"]["released_total"],
            "frozen_total": report["summary"]["frozen_total"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] in {"ready", "appeal_pending"} else 1


def run_verify_attribution_dispute_adjudication_report(
    args: argparse.Namespace,
) -> int:
    dispute_input = load_attribution_dispute_adjudication_input(
        args.attribution_dispute_input
    )
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_attribution_dispute_adjudication_report(
        report,
        dispute_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "attribution_dispute_input": args.attribution_dispute_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_post_adjudication_settlement_adjustment_report(
    args: argparse.Namespace,
) -> int:
    adjustment_input = load_post_adjudication_settlement_adjustment_input(
        args.post_adjudication_settlement_adjustment_input
    )
    report = make_post_adjudication_settlement_adjustment_report(
        adjustment_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "adjustment_case_id": report["summary"]["adjustment_case_id"],
            "adjusted_creator_count": report["summary"]["adjusted_creator_count"],
            "top_up_count": report["summary"]["top_up_count"],
            "recoupment_count": report["summary"]["recoupment_count"],
            "future_netting_count": report["summary"]["future_netting_count"],
            "freeze_count": report["summary"]["freeze_count"],
            "top_up_total": report["summary"]["top_up_total"],
            "recoupment_total": report["summary"]["recoupment_total"],
            "frozen_total": report["summary"]["frozen_total"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] in {"ready", "appeal_pending"} else 1


def run_verify_post_adjudication_settlement_adjustment_report(
    args: argparse.Namespace,
) -> int:
    adjustment_input = load_post_adjudication_settlement_adjustment_input(
        args.post_adjudication_settlement_adjustment_input
    )
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_post_adjudication_settlement_adjustment_report(
        report,
        adjustment_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "post_adjudication_settlement_adjustment_input": (
            args.post_adjudication_settlement_adjustment_input
        ),
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_residual_corpus_royalty_report(args: argparse.Namespace) -> int:
    residual_input = load_residual_corpus_royalty_input(
        args.residual_corpus_royalty_input
    )
    report = make_residual_corpus_royalty_report(
        residual_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "residual_corpus_pool": report["summary"]["residual_corpus_pool"],
            "payable_total": report["summary"]["payable_total"],
            "escrow_total": report["summary"]["escrow_total"],
            "creator_count": report["summary"]["creator_count"],
            "valuation_row_count": report["summary"]["valuation_row_count"],
            "creator_pool_conserved": report["summary"]["creator_pool_conserved"],
            "direct_attribution_separated": report["summary"][
                "direct_attribution_separated"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_residual_corpus_royalty_report(args: argparse.Namespace) -> int:
    residual_input = load_residual_corpus_royalty_input(
        args.residual_corpus_royalty_input
    )
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_residual_corpus_royalty_report(
        report,
        residual_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "residual_corpus_royalty_input": args.residual_corpus_royalty_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_valuation_method_audit_report(args: argparse.Namespace) -> int:
    audit_input = load_valuation_method_audit_input(args.valuation_method_audit_input)
    report = make_valuation_method_audit_report(
        audit_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "benchmark_case_count": report["summary"]["benchmark_case_count"],
            "mean_absolute_error": report["summary"]["mean_absolute_error"],
            "rank_agreement": report["summary"]["rank_agreement"],
            "anti_gaming_guards_passed": report["summary"][
                "anti_gaming_guards_passed"
            ],
            "privacy_verifiability_supported": report["summary"][
                "privacy_verifiability_supported"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_valuation_method_audit_report(args: argparse.Namespace) -> int:
    audit_input = load_valuation_method_audit_input(args.valuation_method_audit_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_valuation_method_audit_report(
        report,
        audit_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "valuation_method_audit_input": args.valuation_method_audit_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_citation_identity_report(args: argparse.Namespace) -> int:
    citation_input = load_citation_identity_input(args.citation_input)
    report = make_citation_identity_report(
        citation_input,
        gross_revenue=Decimal(args.citation_gross_revenue),
        creator_pool_rate=Decimal(args.citation_creator_pool_rate),
        accept_threshold=args.accept_threshold,
        min_title_similarity=args.min_title_similarity,
        min_author_overlap=args.min_author_overlap,
        min_claim_support=args.min_claim_support,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "citation_count": report["summary"]["citation_count"],
            "verified_citation_row_count": report["summary"][
                "verified_citation_row_count"
            ],
            "escrow_citation_row_count": report["summary"][
                "escrow_citation_row_count"
            ],
            "metadata_mismatch_count": report["summary"][
                "metadata_mismatch_count"
            ],
            "fabricated_citation_count": report["summary"][
                "fabricated_citation_count"
            ],
            "creator_pool": report["economics"]["creator_pool"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_citation_identity_report(args: argparse.Namespace) -> int:
    citation_input = load_citation_identity_input(args.citation_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_citation_identity_report(
        report,
        citation_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "citation_input": args.citation_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_attribution_consensus_report(args: argparse.Namespace) -> int:
    source_confidence_report = json.loads(
        Path(args.source_confidence_report).read_text(encoding="utf-8")
    )
    evidence_sufficiency_report = json.loads(
        Path(args.evidence_sufficiency_report).read_text(encoding="utf-8")
    )
    counterevidence_report = json.loads(
        Path(args.counterevidence_report).read_text(encoding="utf-8")
    )
    source_authenticity_report = json.loads(
        Path(args.source_authenticity_report).read_text(encoding="utf-8")
    )
    pinpoint_provenance_report = json.loads(
        Path(args.pinpoint_provenance_report).read_text(encoding="utf-8")
    )
    citation_identity_report = json.loads(
        Path(args.citation_identity_report).read_text(encoding="utf-8")
    )
    report = make_attribution_consensus_report(
        source_confidence_report=source_confidence_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
        source_authenticity_report=source_authenticity_report,
        pinpoint_provenance_report=pinpoint_provenance_report,
        citation_identity_report=citation_identity_report,
        gross_revenue=Decimal(args.consensus_gross_revenue),
        creator_pool_rate=Decimal(args.consensus_creator_pool_rate),
        minimum_quorum=args.minimum_quorum,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "source_count": report["summary"]["source_count"],
            "accepted_source_count": report["summary"]["accepted_source_count"],
            "escrow_source_count": report["summary"]["escrow_source_count"],
            "creator_pool": report["economics"]["creator_pool"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_attribution_consensus_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    source_confidence_report = json.loads(
        Path(args.source_confidence_report).read_text(encoding="utf-8")
    )
    evidence_sufficiency_report = json.loads(
        Path(args.evidence_sufficiency_report).read_text(encoding="utf-8")
    )
    counterevidence_report = json.loads(
        Path(args.counterevidence_report).read_text(encoding="utf-8")
    )
    source_authenticity_report = json.loads(
        Path(args.source_authenticity_report).read_text(encoding="utf-8")
    )
    pinpoint_provenance_report = json.loads(
        Path(args.pinpoint_provenance_report).read_text(encoding="utf-8")
    )
    citation_identity_report = json.loads(
        Path(args.citation_identity_report).read_text(encoding="utf-8")
    )
    errors = verify_attribution_consensus_report(
        report,
        source_confidence_report=source_confidence_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
        source_authenticity_report=source_authenticity_report,
        pinpoint_provenance_report=pinpoint_provenance_report,
        citation_identity_report=citation_identity_report,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_verifier_quorum_report(args: argparse.Namespace) -> int:
    attribution_consensus_report = json.loads(
        Path(args.attribution_consensus_report).read_text(encoding="utf-8")
    )
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    integration_profile = json.loads(
        Path(args.integration_profile).read_text(encoding="utf-8")
    )
    verifier_secrets = _verifier_secrets_from_args(args.verifier_secret)
    report = make_verifier_quorum_report(
        attribution_consensus_report=attribution_consensus_report,
        provider_card=provider_card,
        certification_report=certification_report,
        integration_profile=integration_profile,
        verifier_secrets=verifier_secrets,
        minimum_quorum=args.minimum_quorum,
        minimum_independent_organizations=args.minimum_independent_organizations,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "accepted_verifier_count": report["summary"][
                "accepted_verifier_count"
            ],
            "settlement_decision": report["summary"]["settlement_decision"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_verifier_quorum_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    attribution_consensus_report = json.loads(
        Path(args.attribution_consensus_report).read_text(encoding="utf-8")
    )
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    integration_profile = json.loads(
        Path(args.integration_profile).read_text(encoding="utf-8")
    )
    errors = verify_verifier_quorum_report(
        report,
        attribution_consensus_report=attribution_consensus_report,
        provider_card=provider_card,
        certification_report=certification_report,
        integration_profile=integration_profile,
        verifier_secrets=_verifier_secrets_from_args(args.verifier_secret),
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_verifier_accountability_report(args: argparse.Namespace) -> int:
    verifier_quorum_report = json.loads(
        Path(args.verifier_quorum_report).read_text(encoding="utf-8")
    )
    trust_registry = json.loads(Path(args.trust_registry).read_text(encoding="utf-8"))
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    report = make_verifier_accountability_report(
        verifier_quorum_report=verifier_quorum_report,
        trust_registry=trust_registry,
        provider_card=provider_card,
        certification_report=certification_report,
        bond_specs=_bond_specs_from_args(args.bond) or None,
        challenge_rows=_challenge_rows_from_args(args.challenge),
        minimum_bond_amount=args.minimum_bond_amount,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "bonded_verifier_count": report["summary"]["bonded_verifier_count"],
            "settlement_decision": report["summary"]["settlement_decision"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_verifier_accountability_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    verifier_quorum_report = json.loads(
        Path(args.verifier_quorum_report).read_text(encoding="utf-8")
    )
    trust_registry = json.loads(Path(args.trust_registry).read_text(encoding="utf-8"))
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    errors = verify_verifier_accountability_report(
        report,
        verifier_quorum_report=verifier_quorum_report,
        trust_registry=trust_registry,
        provider_card=provider_card,
        certification_report=certification_report,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_receipt_transparency_consistency_report(args: argparse.Namespace) -> int:
    verifier_accountability_report = json.loads(
        Path(args.verifier_accountability_report).read_text(encoding="utf-8")
    )
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    report = make_receipt_transparency_consistency_report(
        transparency_logs=_named_json_from_args(args.transparency_log),
        receipts=_json_payloads_from_args(args.receipt),
        verifier_accountability_report=verifier_accountability_report,
        provider_card=provider_card,
        certification_report=certification_report,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "latest_tree_size": report["summary"]["latest_tree_size"],
            "settlement_decision": report["summary"]["settlement_decision"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_receipt_transparency_consistency_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    verifier_accountability_report = json.loads(
        Path(args.verifier_accountability_report).read_text(encoding="utf-8")
    )
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    errors = verify_receipt_transparency_consistency_report(
        report,
        transparency_logs=_named_json_from_args(args.transparency_log),
        receipts=_json_payloads_from_args(args.receipt),
        verifier_accountability_report=verifier_accountability_report,
        provider_card=provider_card,
        certification_report=certification_report,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_watchtower_challenge_settlement_report(args: argparse.Namespace) -> int:
    receipt_report = json.loads(
        Path(args.receipt_transparency_consistency_report).read_text(encoding="utf-8")
    )
    verifier_accountability_report = json.loads(
        Path(args.verifier_accountability_report).read_text(encoding="utf-8")
    )
    trust_registry = json.loads(Path(args.trust_registry).read_text(encoding="utf-8"))
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    report = make_watchtower_challenge_settlement_report(
        receipt_transparency_consistency_report=receipt_report,
        verifier_accountability_report=verifier_accountability_report,
        trust_registry=trust_registry,
        provider_card=provider_card,
        certification_report=certification_report,
        watchtower_secrets=_watchtower_secrets_from_args(args.watchtower_secret),
        challenge_rows=_json_payloads_from_args(args.challenge_row),
        required_quorum=args.required_quorum,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "watchtower_report_hash": report["watchtower_report_hash"],
            "attestation_count": report["summary"]["attestation_count"],
            "settlement_decision": report["summary"]["settlement_decision"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_watchtower_challenge_settlement_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    receipt_report = json.loads(
        Path(args.receipt_transparency_consistency_report).read_text(encoding="utf-8")
    )
    verifier_accountability_report = json.loads(
        Path(args.verifier_accountability_report).read_text(encoding="utf-8")
    )
    trust_registry = json.loads(Path(args.trust_registry).read_text(encoding="utf-8"))
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    errors = verify_watchtower_challenge_settlement_report(
        report,
        receipt_transparency_consistency_report=receipt_report,
        verifier_accountability_report=verifier_accountability_report,
        trust_registry=trust_registry,
        provider_card=provider_card,
        certification_report=certification_report,
        watchtower_secrets=_watchtower_secrets_from_args(args.watchtower_secret),
        challenge_rows=_json_payloads_from_args(args.challenge_row),
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "watchtower_report_hash": report.get("watchtower_report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_output_provenance_binding_report(args: argparse.Namespace) -> int:
    proof_carrying_response = json.loads(
        Path(args.proof_carrying_response).read_text(encoding="utf-8")
    )
    serving_gateway_report = json.loads(
        Path(args.serving_gateway_report).read_text(encoding="utf-8")
    )
    attribution_capsule = json.loads(
        Path(args.attribution_capsule).read_text(encoding="utf-8")
    )
    watchtower_report = json.loads(
        Path(args.watchtower_challenge_settlement_report).read_text(encoding="utf-8")
    )
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    report = make_output_provenance_binding_report(
        proof_carrying_response=proof_carrying_response,
        serving_gateway_report=serving_gateway_report,
        attribution_capsule=attribution_capsule,
        watchtower_challenge_settlement_report=watchtower_report,
        provider_card=provider_card,
        certification_report=certification_report,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "binding_report_hash": report["binding_report_hash"],
            "credential_count": report["summary"]["credential_count"],
            "durable_signal_count": report["summary"]["durable_signal_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_output_provenance_binding_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    proof_carrying_response = json.loads(
        Path(args.proof_carrying_response).read_text(encoding="utf-8")
    )
    serving_gateway_report = json.loads(
        Path(args.serving_gateway_report).read_text(encoding="utf-8")
    )
    attribution_capsule = json.loads(
        Path(args.attribution_capsule).read_text(encoding="utf-8")
    )
    watchtower_report = json.loads(
        Path(args.watchtower_challenge_settlement_report).read_text(encoding="utf-8")
    )
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    errors = verify_output_provenance_binding_report(
        report,
        proof_carrying_response=proof_carrying_response,
        serving_gateway_report=serving_gateway_report,
        attribution_capsule=attribution_capsule,
        watchtower_challenge_settlement_report=watchtower_report,
        provider_card=provider_card,
        certification_report=certification_report,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "binding_report_hash": report.get("binding_report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_post_release_discovery_report(args: argparse.Namespace) -> int:
    discovery_manifest = json.loads(
        Path(args.discovery_manifest).read_text(encoding="utf-8")
    )
    output_binding = json.loads(
        Path(args.output_provenance_binding_report).read_text(encoding="utf-8")
    )
    proof_graph = json.loads(Path(args.proof_dependency_graph).read_text(encoding="utf-8"))
    proof_carrying_response = json.loads(
        Path(args.proof_carrying_response).read_text(encoding="utf-8")
    )
    serving_gateway_report = json.loads(
        Path(args.serving_gateway_report).read_text(encoding="utf-8")
    )
    attribution_capsule = json.loads(
        Path(args.attribution_capsule).read_text(encoding="utf-8")
    )
    watchtower_report = json.loads(
        Path(args.watchtower_challenge_settlement_report).read_text(encoding="utf-8")
    )
    integration_profile = json.loads(
        Path(args.integration_profile).read_text(encoding="utf-8")
    )
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    report = make_post_release_discovery_report(
        discovery_manifest=discovery_manifest,
        output_provenance_binding_report=output_binding,
        proof_dependency_graph=proof_graph,
        proof_carrying_response=proof_carrying_response,
        serving_gateway_report=serving_gateway_report,
        attribution_capsule=attribution_capsule,
        watchtower_challenge_settlement_report=watchtower_report,
        integration_profile=integration_profile,
        provider_card=provider_card,
        certification_report=certification_report,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "post_release_report_hash": report["post_release_report_hash"],
            "artifact_count": report["summary"]["artifact_count"],
            "post_release_artifact_count": report["summary"][
                "post_release_artifact_count"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_post_release_discovery_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    discovery_manifest = json.loads(
        Path(args.discovery_manifest).read_text(encoding="utf-8")
    )
    output_binding = json.loads(
        Path(args.output_provenance_binding_report).read_text(encoding="utf-8")
    )
    proof_graph = json.loads(Path(args.proof_dependency_graph).read_text(encoding="utf-8"))
    proof_carrying_response = json.loads(
        Path(args.proof_carrying_response).read_text(encoding="utf-8")
    )
    serving_gateway_report = json.loads(
        Path(args.serving_gateway_report).read_text(encoding="utf-8")
    )
    attribution_capsule = json.loads(
        Path(args.attribution_capsule).read_text(encoding="utf-8")
    )
    watchtower_report = json.loads(
        Path(args.watchtower_challenge_settlement_report).read_text(encoding="utf-8")
    )
    integration_profile = json.loads(
        Path(args.integration_profile).read_text(encoding="utf-8")
    )
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    errors = verify_post_release_discovery_report(
        report,
        discovery_manifest=discovery_manifest,
        output_provenance_binding_report=output_binding,
        proof_dependency_graph=proof_graph,
        proof_carrying_response=proof_carrying_response,
        serving_gateway_report=serving_gateway_report,
        attribution_capsule=attribution_capsule,
        watchtower_challenge_settlement_report=watchtower_report,
        integration_profile=integration_profile,
        provider_card=provider_card,
        certification_report=certification_report,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "post_release_report_hash": report.get("post_release_report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_rights_remediation(args: argparse.Namespace) -> int:
    previous_engine = RoyaltyDrivenLLM.from_corpus_file(
        args.previous_corpus,
        creator_pool_rate=Decimal(args.remediation_creator_pool_rate),
        jurisdiction=args.jurisdiction,
        top_k=args.top_k,
    )
    updated_engine = RoyaltyDrivenLLM.from_corpus_file(
        args.updated_corpus,
        creator_pool_rate=Decimal(args.remediation_creator_pool_rate),
        jurisdiction=args.jurisdiction,
        top_k=args.top_k,
    )
    ledger_data = load_ledger(args.ledger)
    report = make_rights_remediation_report(
        previous_engine,
        updated_engine,
        ledger_data,
        gross_revenue=Decimal(args.remediation_gross_revenue),
        creator_pool_rate=Decimal(args.remediation_creator_pool_rate),
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "changed_work_count": report["summary"]["changed_work_count"],
            "historical_event_count": report["summary"]["historical_event_count"],
            "future_denial_count": report["summary"]["future_denial_count"],
            "rights_conflict_escrow_verified": report["summary"][
                "rights_conflict_escrow_verified"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_rights_remediation(args: argparse.Namespace) -> int:
    previous_engine = RoyaltyDrivenLLM.from_corpus_file(
        args.previous_corpus,
        creator_pool_rate=Decimal(args.remediation_creator_pool_rate),
        jurisdiction=args.jurisdiction,
        top_k=args.top_k,
    )
    updated_engine = RoyaltyDrivenLLM.from_corpus_file(
        args.updated_corpus,
        creator_pool_rate=Decimal(args.remediation_creator_pool_rate),
        jurisdiction=args.jurisdiction,
        top_k=args.top_k,
    )
    ledger_data = load_ledger(args.ledger)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_rights_remediation_report(
        report,
        previous_engine,
        updated_engine,
        ledger_data,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "previous_corpus": args.previous_corpus,
        "updated_corpus": args.updated_corpus,
        "ledger": args.ledger,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_semantic_text_attribution(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    inputs = load_semantic_text_inputs(args.semantic_input)
    report = make_semantic_text_attribution_report(
        engine,
        inputs,
        gross_revenue=Decimal(args.semantic_gross_revenue),
        creator_pool_rate=Decimal(args.semantic_creator_pool_rate),
        accept_threshold=args.accept_threshold,
        min_margin=args.min_margin,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "input_count": report["summary"]["input_count"],
            "accepted_input_count": report["summary"]["accepted_input_count"],
            "escrow_input_count": report["summary"]["escrow_input_count"],
            "source_footer_count": report["summary"]["source_footer_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_semantic_text_attribution(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    inputs = load_semantic_text_inputs(args.semantic_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_semantic_text_attribution_report(
        report,
        engine,
        inputs,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "semantic_input": args.semantic_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_code_attribution_report(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    inputs = load_code_attribution_inputs(args.code_input)
    report = make_code_attribution_report(
        engine,
        inputs,
        gross_revenue=Decimal(args.code_gross_revenue),
        creator_pool_rate=Decimal(args.code_creator_pool_rate),
        accept_threshold=args.accept_threshold,
        strong_copy_threshold=args.strong_copy_threshold,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "output_count": report["summary"]["output_count"],
            "accepted_share_count": report["summary"]["accepted_share_count"],
            "license_conflict_count": report["summary"]["license_conflict_count"],
            "escrow_total": report["summary"]["escrow_total"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_code_attribution_report(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    inputs = load_code_attribution_inputs(args.code_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_code_attribution_report(
        report,
        engine,
        inputs,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "code_input": args.code_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_claim_verification_report(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    inputs = load_claim_verification_inputs(args.claim_input)
    report = make_claim_verification_report(
        engine.works,
        inputs["attestations"],
        trusted_issuers=inputs["trusted_issuers"],
        issuer_keys=inputs["issuer_keys"],
        duplicate_threshold=args.duplicate_threshold,
        direct_settlement_threshold=args.direct_settlement_threshold,
        review_threshold=args.review_threshold,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "direct_settlement_work_count": report["summary"][
                "direct_settlement_work_count"
            ],
            "review_or_escrow_work_count": report["summary"][
                "review_or_escrow_work_count"
            ],
            "duplicate_conflict_count": report["summary"]["duplicate_conflict_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_claim_verification_report(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    inputs = load_claim_verification_inputs(args.claim_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_claim_verification_report(
        report,
        engine.works,
        inputs["attestations"],
        trusted_issuers=inputs["trusted_issuers"],
        issuer_keys=inputs["issuer_keys"],
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "claim_input": args.claim_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_response_envelope(args: argparse.Namespace) -> int:
    answer_card = json.loads(Path(args.answer_card).read_text(encoding="utf-8"))
    source_report = json.loads(Path(args.source_report).read_text(encoding="utf-8"))
    public_receipt_data = (
        json.loads(Path(args.public_receipt).read_text(encoding="utf-8"))
        if args.public_receipt
        else None
    )
    provider_card = (
        json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
        if args.provider_card
        else None
    )
    certification_report = (
        json.loads(Path(args.certification_report).read_text(encoding="utf-8"))
        if args.certification_report
        else None
    )
    source_confidence_report = (
        json.loads(Path(args.source_confidence_report).read_text(encoding="utf-8"))
        if args.source_confidence_report
        else None
    )
    creator_license_contract = (
        json.loads(Path(args.creator_license_contract).read_text(encoding="utf-8"))
        if args.creator_license_contract
        else None
    )
    citation_footer_contract = (
        json.loads(Path(args.citation_footer_contract).read_text(encoding="utf-8"))
        if args.citation_footer_contract
        else None
    )
    source_availability_report = (
        json.loads(Path(args.source_availability_report).read_text(encoding="utf-8"))
        if args.source_availability_report
        else None
    )
    evidence_sufficiency_report = (
        json.loads(Path(args.evidence_sufficiency_report).read_text(encoding="utf-8"))
        if args.evidence_sufficiency_report
        else None
    )
    counterevidence_report = (
        json.loads(Path(args.counterevidence_report).read_text(encoding="utf-8"))
        if args.counterevidence_report
        else None
    )
    answer_claim_coverage_report = (
        json.loads(Path(args.answer_claim_coverage_report).read_text(encoding="utf-8"))
        if args.answer_claim_coverage_report
        else None
    )
    trace_exchange = (
        json.loads(Path(args.trace_exchange).read_text(encoding="utf-8"))
        if args.trace_exchange
        else None
    )
    generation_context_closure_report = (
        json.loads(
            Path(args.generation_context_closure_report).read_text(encoding="utf-8")
        )
        if args.generation_context_closure_report
        else None
    )
    source_boundary_report = (
        json.loads(Path(args.source_boundary_report).read_text(encoding="utf-8"))
        if args.source_boundary_report
        else None
    )
    source_authenticity_report = (
        json.loads(Path(args.source_authenticity_report).read_text(encoding="utf-8"))
        if args.source_authenticity_report
        else None
    )
    event_id = _event_id_for_artifact(
        args.ledger,
        event_id=args.event_id,
        answer_card=answer_card,
    )
    event = _event_from_ledger(args.ledger, event_id)
    envelope = make_response_envelope(
        event,
        answer_card=answer_card,
        source_verification_report=source_report,
        source_confidence_report=source_confidence_report,
        creator_license_contract=creator_license_contract,
        citation_footer_contract=citation_footer_contract,
        source_availability_report=source_availability_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
        answer_claim_coverage_report=answer_claim_coverage_report,
        trace_exchange=trace_exchange,
        generation_context_closure_report=generation_context_closure_report,
        source_boundary_report=source_boundary_report,
        source_authenticity_report=source_authenticity_report,
        public_receipt=public_receipt_data,
        provider_card=provider_card,
        certification_report=certification_report,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(envelope, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": envelope["summary"]["status"],
            "output": args.output,
            "envelope_hash": envelope["envelope_hash"],
            "event_id": event.event_id,
            "artifact_count": envelope["summary"]["artifact_count"],
            "source_count": envelope["summary"]["source_count"],
            "claim_count": envelope["summary"]["claim_count"],
        }
    else:
        result = envelope
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if envelope["summary"]["status"] == "verified" else 1


def run_verify_response_envelope(args: argparse.Namespace) -> int:
    envelope = json.loads(Path(args.envelope).read_text(encoding="utf-8"))
    errors = verify_response_envelope(
        envelope,
        signing_secret=args.signing_secret,
    )
    result = {
        "envelope": args.envelope,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "envelope_hash": envelope.get("envelope_hash", ""),
        "event_id": envelope.get("response", {}).get("event_id", ""),
        "summary": envelope.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_integration_profile(args: argparse.Namespace) -> int:
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    response_envelope = json.loads(
        Path(args.response_envelope).read_text(encoding="utf-8")
    )
    assurance_bundle = (
        json.loads(Path(args.assurance_bundle).read_text(encoding="utf-8"))
        if args.assurance_bundle
        else None
    )
    certification_attestation = (
        json.loads(Path(args.certification_attestation).read_text(encoding="utf-8"))
        if args.certification_attestation
        else None
    )
    profile = make_integration_profile(
        provider_card=provider_card,
        certification_report=certification_report,
        response_envelope=response_envelope,
        assurance_bundle=assurance_bundle,
        certification_attestation=certification_attestation,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(profile, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": profile["summary"]["status"],
            "output": args.output,
            "profile_hash": profile["profile_hash"],
            "provider": profile["provider"],
            "endpoint_count": profile["summary"]["endpoint_count"],
            "schema_count": profile["summary"]["schema_count"],
        }
    else:
        result = profile
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if profile["summary"]["status"] == "ready" else 1


def run_verify_integration_profile(args: argparse.Namespace) -> int:
    profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    response_envelope = json.loads(
        Path(args.response_envelope).read_text(encoding="utf-8")
    )
    assurance_bundle = (
        json.loads(Path(args.assurance_bundle).read_text(encoding="utf-8"))
        if args.assurance_bundle
        else None
    )
    certification_attestation = (
        json.loads(Path(args.certification_attestation).read_text(encoding="utf-8"))
        if args.certification_attestation
        else None
    )
    errors = verify_integration_profile(
        profile,
        provider_card=provider_card,
        certification_report=certification_report,
        response_envelope=response_envelope,
        assurance_bundle=assurance_bundle,
        certification_attestation=certification_attestation,
        signing_secret=args.signing_secret,
    )
    result = {
        "profile": args.profile,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "profile_hash": profile.get("profile_hash", ""),
        "summary": profile.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_discovery_manifest(args: argparse.Namespace) -> int:
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    integration_profile = json.loads(
        Path(args.integration_profile).read_text(encoding="utf-8")
    )
    response_envelope = json.loads(
        Path(args.response_envelope).read_text(encoding="utf-8")
    )
    assurance_bundle = json.loads(Path(args.assurance_bundle).read_text(encoding="utf-8"))
    training_summary = (
        json.loads(Path(args.training_summary).read_text(encoding="utf-8"))
        if args.training_summary
        else None
    )
    provenance_evaluation_report = (
        json.loads(Path(args.provenance_evaluation_report).read_text(encoding="utf-8"))
        if args.provenance_evaluation_report
        else None
    )
    counterfactual_report = (
        json.loads(Path(args.counterfactual_report).read_text(encoding="utf-8"))
        if args.counterfactual_report
        else None
    )
    media_attribution_report = (
        json.loads(Path(args.media_attribution_report).read_text(encoding="utf-8"))
        if args.media_attribution_report
        else None
    )
    model_signal_report = (
        json.loads(Path(args.model_signal_report).read_text(encoding="utf-8"))
        if args.model_signal_report
        else None
    )
    pinpoint_provenance_report = (
        json.loads(Path(args.pinpoint_provenance_report).read_text(encoding="utf-8"))
        if args.pinpoint_provenance_report
        else None
    )
    citation_identity_report = (
        json.loads(Path(args.citation_identity_report).read_text(encoding="utf-8"))
        if args.citation_identity_report
        else None
    )
    attribution_consensus_report = (
        json.loads(Path(args.attribution_consensus_report).read_text(encoding="utf-8"))
        if args.attribution_consensus_report
        else None
    )
    verifier_quorum_report = (
        json.loads(Path(args.verifier_quorum_report).read_text(encoding="utf-8"))
        if args.verifier_quorum_report
        else None
    )
    verifier_accountability_report = (
        json.loads(Path(args.verifier_accountability_report).read_text(encoding="utf-8"))
        if args.verifier_accountability_report
        else None
    )
    receipt_transparency_consistency_report = (
        json.loads(
            Path(args.receipt_transparency_consistency_report).read_text(
                encoding="utf-8"
            )
        )
        if args.receipt_transparency_consistency_report
        else None
    )
    watchtower_challenge_settlement_report = (
        json.loads(
            Path(args.watchtower_challenge_settlement_report).read_text(
                encoding="utf-8"
            )
        )
        if args.watchtower_challenge_settlement_report
        else None
    )
    output_provenance_binding_report = (
        json.loads(
            Path(args.output_provenance_binding_report).read_text(encoding="utf-8")
        )
        if args.output_provenance_binding_report
        else None
    )
    rights_remediation_report = (
        json.loads(Path(args.rights_remediation_report).read_text(encoding="utf-8"))
        if args.rights_remediation_report
        else None
    )
    semantic_text_attribution_report = (
        json.loads(Path(args.semantic_text_attribution_report).read_text(encoding="utf-8"))
        if args.semantic_text_attribution_report
        else None
    )
    code_attribution_report = (
        json.loads(Path(args.code_attribution_report).read_text(encoding="utf-8"))
        if args.code_attribution_report
        else None
    )
    claim_verification_report = (
        json.loads(Path(args.claim_verification_report).read_text(encoding="utf-8"))
        if args.claim_verification_report
        else None
    )
    source_availability_report = (
        json.loads(Path(args.source_availability_report).read_text(encoding="utf-8"))
        if args.source_availability_report
        else None
    )
    evidence_sufficiency_report = (
        json.loads(Path(args.evidence_sufficiency_report).read_text(encoding="utf-8"))
        if args.evidence_sufficiency_report
        else None
    )
    counterevidence_report = (
        json.loads(Path(args.counterevidence_report).read_text(encoding="utf-8"))
        if args.counterevidence_report
        else None
    )
    answer_claim_coverage_report = (
        json.loads(Path(args.answer_claim_coverage_report).read_text(encoding="utf-8"))
        if args.answer_claim_coverage_report
        else None
    )
    generation_context_closure_report = (
        json.loads(
            Path(args.generation_context_closure_report).read_text(encoding="utf-8")
        )
        if args.generation_context_closure_report
        else None
    )
    source_boundary_report = (
        json.loads(Path(args.source_boundary_report).read_text(encoding="utf-8"))
        if args.source_boundary_report
        else None
    )
    source_authenticity_report = (
        json.loads(Path(args.source_authenticity_report).read_text(encoding="utf-8"))
        if args.source_authenticity_report
        else None
    )
    decision_provenance_report = (
        json.loads(Path(args.decision_provenance_report).read_text(encoding="utf-8"))
        if args.decision_provenance_report
        else None
    )
    calibrated_attribution_report = (
        json.loads(Path(args.calibrated_attribution_report).read_text(encoding="utf-8"))
        if args.calibrated_attribution_report
        else None
    )
    streaming_attribution_manifest = (
        json.loads(Path(args.streaming_attribution_manifest).read_text(encoding="utf-8"))
        if args.streaming_attribution_manifest
        else None
    )
    conversation_attribution_ledger = (
        json.loads(Path(args.conversation_attribution_ledger).read_text(encoding="utf-8"))
        if args.conversation_attribution_ledger
        else None
    )
    agent_tool_attribution_ledger = (
        json.loads(Path(args.agent_tool_attribution_ledger).read_text(encoding="utf-8"))
        if args.agent_tool_attribution_ledger
        else None
    )
    creator_license_contract = (
        json.loads(Path(args.creator_license_contract).read_text(encoding="utf-8"))
        if args.creator_license_contract
        else None
    )
    source_confidence_report = (
        json.loads(Path(args.source_confidence_report).read_text(encoding="utf-8"))
        if args.source_confidence_report
        else None
    )
    citation_footer_contract = (
        json.loads(Path(args.citation_footer_contract).read_text(encoding="utf-8"))
        if args.citation_footer_contract
        else None
    )
    private_audit_challenge = (
        json.loads(Path(args.private_audit_challenge).read_text(encoding="utf-8"))
        if args.private_audit_challenge
        else None
    )
    transitive_attribution_report = (
        json.loads(Path(args.transitive_attribution_report).read_text(encoding="utf-8"))
        if args.transitive_attribution_report
        else None
    )
    clearinghouse_report = (
        json.loads(Path(args.clearinghouse_report).read_text(encoding="utf-8"))
        if args.clearinghouse_report
        else None
    )
    remittance_report = (
        json.loads(Path(args.remittance_report).read_text(encoding="utf-8"))
        if args.remittance_report
        else None
    )
    payment_execution_report = (
        json.loads(Path(args.payment_execution_report).read_text(encoding="utf-8"))
        if args.payment_execution_report
        else None
    )
    payment_rail_attestation = (
        json.loads(Path(args.payment_rail_attestation).read_text(encoding="utf-8"))
        if args.payment_rail_attestation
        else None
    )
    creator_payout_receipt_report = (
        json.loads(Path(args.creator_payout_receipt_report).read_text(encoding="utf-8"))
        if args.creator_payout_receipt_report
        else None
    )
    rendered_attribution_audit = (
        json.loads(Path(args.rendered_attribution_audit).read_text(encoding="utf-8"))
        if args.rendered_attribution_audit
        else None
    )
    training_memory_provenance = (
        json.loads(Path(args.training_memory_provenance).read_text(encoding="utf-8"))
        if args.training_memory_provenance
        else None
    )
    post_training_signal_provenance = (
        json.loads(
            Path(args.post_training_signal_provenance).read_text(encoding="utf-8")
        )
        if args.post_training_signal_provenance
        else None
    )
    evidence_locked_generation = (
        json.loads(Path(args.evidence_locked_generation).read_text(encoding="utf-8"))
        if args.evidence_locked_generation
        else None
    )
    emission_evidence_enforcement = (
        json.loads(Path(args.emission_evidence_enforcement).read_text(encoding="utf-8"))
        if args.emission_evidence_enforcement
        else None
    )
    live_emission_witness = (
        json.loads(Path(args.live_emission_witness).read_text(encoding="utf-8"))
        if args.live_emission_witness
        else None
    )
    live_emission_transparency = (
        json.loads(Path(args.live_emission_transparency).read_text(encoding="utf-8"))
        if args.live_emission_transparency
        else None
    )
    attested_runtime = (
        json.loads(Path(args.attested_runtime).read_text(encoding="utf-8"))
        if args.attested_runtime
        else None
    )
    claim_source_attribution_report = (
        json.loads(Path(args.claim_source_attribution_report).read_text(encoding="utf-8"))
        if args.claim_source_attribution_report
        else None
    )
    evidence_utility_attribution_report = (
        json.loads(Path(args.evidence_utility_attribution_report).read_text(encoding="utf-8"))
        if args.evidence_utility_attribution_report
        else None
    )
    parametric_memory_attribution_report = (
        json.loads(Path(args.parametric_memory_attribution_report).read_text(encoding="utf-8"))
        if args.parametric_memory_attribution_report
        else None
    )
    style_influence_attribution_report = (
        json.loads(Path(args.style_influence_attribution_report).read_text(encoding="utf-8"))
        if args.style_influence_attribution_report
        else None
    )
    model_lineage_attribution_report = (
        json.loads(Path(args.model_lineage_attribution_report).read_text(encoding="utf-8"))
        if args.model_lineage_attribution_report
        else None
    )
    black_box_model_provenance_report = (
        json.loads(Path(args.black_box_model_provenance_report).read_text(encoding="utf-8"))
        if args.black_box_model_provenance_report
        else None
    )
    attribution_dispute_adjudication_report = (
        json.loads(Path(args.attribution_dispute_adjudication_report).read_text(encoding="utf-8"))
        if args.attribution_dispute_adjudication_report
        else None
    )
    post_adjudication_settlement_adjustment_report = (
        json.loads(
            Path(args.post_adjudication_settlement_adjustment_report).read_text(
                encoding="utf-8"
            )
        )
        if args.post_adjudication_settlement_adjustment_report
        else None
    )
    residual_corpus_royalty_report = (
        json.loads(Path(args.residual_corpus_royalty_report).read_text(encoding="utf-8"))
        if args.residual_corpus_royalty_report
        else None
    )
    valuation_method_audit_report = (
        json.loads(Path(args.valuation_method_audit_report).read_text(encoding="utf-8"))
        if args.valuation_method_audit_report
        else None
    )
    evidence_region_binding_report = (
        json.loads(
            Path(args.evidence_region_binding_report).read_text(encoding="utf-8")
        )
        if args.evidence_region_binding_report
        else None
    )
    source_access_lease_report = (
        json.loads(Path(args.source_access_lease_report).read_text(encoding="utf-8"))
        if args.source_access_lease_report
        else None
    )
    content_protocol_ingestion_report = (
        json.loads(
            Path(args.content_protocol_ingestion_report).read_text(encoding="utf-8")
        )
        if args.content_protocol_ingestion_report
        else None
    )
    citation_reliance_receipt = (
        json.loads(Path(args.citation_reliance_receipt).read_text(encoding="utf-8"))
        if args.citation_reliance_receipt
        else None
    )
    license_transaction_receipt = (
        json.loads(Path(args.license_transaction_receipt).read_text(encoding="utf-8"))
        if args.license_transaction_receipt
        else None
    )
    grounded_source_footer = (
        json.loads(Path(args.grounded_source_footer).read_text(encoding="utf-8"))
        if args.grounded_source_footer
        else None
    )
    source_footer_delivery = (
        json.loads(Path(args.source_footer_delivery).read_text(encoding="utf-8"))
        if args.source_footer_delivery
        else None
    )
    deep_research_citation_audit = (
        json.loads(Path(args.deep_research_citation_audit).read_text(encoding="utf-8"))
        if args.deep_research_citation_audit
        else None
    )
    source_freshness_audit = (
        json.loads(Path(args.source_freshness_audit).read_text(encoding="utf-8"))
        if args.source_freshness_audit
        else None
    )
    royalty_abuse_audit = (
        json.loads(Path(args.royalty_abuse_audit).read_text(encoding="utf-8"))
        if args.royalty_abuse_audit
        else None
    )
    consent_revocation_propagation = (
        json.loads(
            Path(args.consent_revocation_propagation).read_text(encoding="utf-8")
        )
        if args.consent_revocation_propagation
        else None
    )
    evidence_force_calibration = (
        json.loads(Path(args.evidence_force_calibration).read_text(encoding="utf-8"))
        if args.evidence_force_calibration
        else None
    )
    warranted_source_footer = (
        json.loads(Path(args.warranted_source_footer).read_text(encoding="utf-8"))
        if args.warranted_source_footer
        else None
    )
    source_origin_lineage = (
        json.loads(Path(args.source_origin_lineage).read_text(encoding="utf-8"))
        if args.source_origin_lineage
        else None
    )
    evidence_preview_footer = (
        json.loads(Path(args.evidence_preview_footer).read_text(encoding="utf-8"))
        if args.evidence_preview_footer
        else None
    )
    evidence_locator_manifest = (
        json.loads(Path(args.evidence_locator_manifest).read_text(encoding="utf-8"))
        if args.evidence_locator_manifest
        else None
    )
    citation_url_health = (
        json.loads(Path(args.citation_url_health).read_text(encoding="utf-8"))
        if args.citation_url_health
        else None
    )
    foundation_api_profile = (
        json.loads(Path(args.foundation_api_profile).read_text(encoding="utf-8"))
        if args.foundation_api_profile
        else None
    )
    composite_foundation_adapter = (
        json.loads(Path(args.composite_foundation_adapter).read_text(encoding="utf-8"))
        if args.composite_foundation_adapter
        else None
    )
    foundation_provider_conformance = (
        json.loads(Path(args.foundation_provider_conformance).read_text(encoding="utf-8"))
        if args.foundation_provider_conformance
        else None
    )
    foundation_runtime_adapter = (
        json.loads(Path(args.foundation_runtime_adapter).read_text(encoding="utf-8"))
        if args.foundation_runtime_adapter
        else None
    )
    foundation_runtime_router = (
        json.loads(Path(args.foundation_runtime_router).read_text(encoding="utf-8"))
        if args.foundation_runtime_router
        else None
    )
    foundation_model_deployment_attestation = (
        json.loads(
            Path(args.foundation_model_deployment_attestation).read_text(
                encoding="utf-8"
            )
        )
        if args.foundation_model_deployment_attestation
        else None
    )
    universal_composition_receipt = (
        json.loads(Path(args.universal_composition_receipt).read_text(encoding="utf-8"))
        if args.universal_composition_receipt
        else None
    )
    universal_composition_settlement = (
        json.loads(
            Path(args.universal_composition_settlement).read_text(encoding="utf-8")
        )
        if args.universal_composition_settlement
        else None
    )
    universal_foundation_model_contract = (
        json.loads(
            Path(args.universal_foundation_model_contract).read_text(
                encoding="utf-8"
            )
        )
        if args.universal_foundation_model_contract
        else None
    )
    universal_invocation_guard = (
        json.loads(Path(args.universal_invocation_guard).read_text(encoding="utf-8"))
        if args.universal_invocation_guard
        else None
    )
    universal_invocation_coverage = (
        json.loads(
            Path(args.universal_invocation_coverage).read_text(encoding="utf-8")
        )
        if args.universal_invocation_coverage
        else None
    )
    universal_invocation_witness = (
        json.loads(
            Path(args.universal_invocation_witness).read_text(encoding="utf-8")
        )
        if args.universal_invocation_witness
        else None
    )
    universal_content_credential = (
        json.loads(
            Path(args.universal_content_credential).read_text(encoding="utf-8")
        )
        if args.universal_content_credential
        else None
    )
    universal_rdllm_passport = (
        json.loads(Path(args.universal_rdllm_passport).read_text(encoding="utf-8"))
        if args.universal_rdllm_passport
        else None
    )
    universal_adoption_standard = (
        json.loads(Path(args.universal_adoption_standard).read_text(encoding="utf-8"))
        if args.universal_adoption_standard
        else None
    )
    universal_interop_test_kit = (
        json.loads(Path(args.universal_interop_test_kit).read_text(encoding="utf-8"))
        if args.universal_interop_test_kit
        else None
    )
    universal_context_provenance_bridge = (
        json.loads(
            Path(args.universal_context_provenance_bridge).read_text(encoding="utf-8")
        )
        if args.universal_context_provenance_bridge
        else None
    )
    universal_citation_verification_contract = (
        json.loads(
            Path(args.universal_citation_verification_contract).read_text(
                encoding="utf-8"
            )
        )
        if args.universal_citation_verification_contract
        else None
    )
    universal_grounded_reuse_contract = (
        json.loads(
            Path(args.universal_grounded_reuse_contract).read_text(encoding="utf-8")
        )
        if args.universal_grounded_reuse_contract
        else None
    )
    universal_training_serving_contract = (
        json.loads(
            Path(args.universal_training_serving_contract).read_text(encoding="utf-8")
        )
        if args.universal_training_serving_contract
        else None
    )
    universal_confidential_attribution_audit = (
        json.loads(
            Path(args.universal_confidential_attribution_audit).read_text(
                encoding="utf-8"
            )
        )
        if args.universal_confidential_attribution_audit
        else None
    )
    universal_attribution_authority_control_plane = (
        json.loads(
            Path(args.universal_attribution_authority_control_plane).read_text(
                encoding="utf-8"
            )
        )
        if args.universal_attribution_authority_control_plane
        else None
    )
    revenue_allocation_report = (
        json.loads(Path(args.revenue_allocation_report).read_text(encoding="utf-8"))
        if args.revenue_allocation_report
        else None
    )
    finance_ledger_attestation = (
        json.loads(Path(args.finance_ledger_attestation).read_text(encoding="utf-8"))
        if args.finance_ledger_attestation
        else None
    )
    proof_dependency_graph = (
        json.loads(Path(args.proof_dependency_graph).read_text(encoding="utf-8"))
        if args.proof_dependency_graph
        else None
    )
    publication_monitor = (
        json.loads(Path(args.publication_monitor).read_text(encoding="utf-8"))
        if args.publication_monitor
        else None
    )
    publication_witness = (
        json.loads(Path(args.publication_witness).read_text(encoding="utf-8"))
        if args.publication_witness
        else None
    )
    trust_registry = (
        json.loads(Path(args.trust_registry).read_text(encoding="utf-8"))
        if args.trust_registry
        else None
    )
    certification_attestation = (
        json.loads(Path(args.certification_attestation).read_text(encoding="utf-8"))
        if args.certification_attestation
        else None
    )
    manifest = make_discovery_manifest(
        provider_card=provider_card,
        certification_report=certification_report,
        integration_profile=integration_profile,
        response_envelope=response_envelope,
        assurance_bundle=assurance_bundle,
        training_summary=training_summary,
        provenance_evaluation_report=provenance_evaluation_report,
        counterfactual_report=counterfactual_report,
        media_attribution_report=media_attribution_report,
        model_signal_report=model_signal_report,
        pinpoint_provenance_report=pinpoint_provenance_report,
        citation_identity_report=citation_identity_report,
        attribution_consensus_report=attribution_consensus_report,
        verifier_quorum_report=verifier_quorum_report,
        verifier_accountability_report=verifier_accountability_report,
        receipt_transparency_consistency_report=receipt_transparency_consistency_report,
        watchtower_challenge_settlement_report=watchtower_challenge_settlement_report,
        output_provenance_binding_report=output_provenance_binding_report,
        rights_remediation_report=rights_remediation_report,
        semantic_text_attribution_report=semantic_text_attribution_report,
        code_attribution_report=code_attribution_report,
        claim_verification_report=claim_verification_report,
        source_availability_report=source_availability_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
        answer_claim_coverage_report=answer_claim_coverage_report,
        generation_context_closure_report=generation_context_closure_report,
        source_boundary_report=source_boundary_report,
        source_authenticity_report=source_authenticity_report,
        decision_provenance_report=decision_provenance_report,
        calibrated_attribution_report=calibrated_attribution_report,
        streaming_attribution_manifest=streaming_attribution_manifest,
        conversation_attribution_ledger=conversation_attribution_ledger,
        agent_tool_attribution_ledger=agent_tool_attribution_ledger,
        creator_license_contract=creator_license_contract,
        source_confidence_report=source_confidence_report,
        citation_footer_contract=citation_footer_contract,
        private_audit_challenge=private_audit_challenge,
        transitive_attribution_report=transitive_attribution_report,
        clearinghouse_report=clearinghouse_report,
        remittance_report=remittance_report,
        payment_execution_report=payment_execution_report,
        payment_rail_attestation=payment_rail_attestation,
        creator_payout_receipt_report=creator_payout_receipt_report,
        rendered_attribution_audit=rendered_attribution_audit,
        training_memory_provenance=training_memory_provenance,
        post_training_signal_provenance=post_training_signal_provenance,
        evidence_locked_generation=evidence_locked_generation,
        emission_evidence_enforcement=emission_evidence_enforcement,
        live_emission_witness=live_emission_witness,
        live_emission_transparency=live_emission_transparency,
        attested_runtime=attested_runtime,
        claim_source_attribution_report=claim_source_attribution_report,
        evidence_utility_attribution_report=evidence_utility_attribution_report,
        parametric_memory_attribution_report=parametric_memory_attribution_report,
        style_influence_attribution_report=style_influence_attribution_report,
        model_lineage_attribution_report=model_lineage_attribution_report,
        black_box_model_provenance_report=black_box_model_provenance_report,
        attribution_dispute_adjudication_report=attribution_dispute_adjudication_report,
        post_adjudication_settlement_adjustment_report=(
            post_adjudication_settlement_adjustment_report
        ),
        residual_corpus_royalty_report=residual_corpus_royalty_report,
        valuation_method_audit_report=valuation_method_audit_report,
        evidence_region_binding_report=evidence_region_binding_report,
        source_access_lease_report=source_access_lease_report,
        content_protocol_ingestion_report=content_protocol_ingestion_report,
        citation_reliance_receipt=citation_reliance_receipt,
        license_transaction_receipt=license_transaction_receipt,
        grounded_source_footer=grounded_source_footer,
        source_footer_delivery=source_footer_delivery,
        deep_research_citation_audit=deep_research_citation_audit,
        source_freshness_audit=source_freshness_audit,
        royalty_abuse_audit=royalty_abuse_audit,
        consent_revocation_propagation=consent_revocation_propagation,
        evidence_force_calibration=evidence_force_calibration,
        warranted_source_footer=warranted_source_footer,
        source_origin_lineage=source_origin_lineage,
        evidence_preview_footer=evidence_preview_footer,
        evidence_locator_manifest=evidence_locator_manifest,
        citation_url_health=citation_url_health,
        foundation_api_profile=foundation_api_profile,
        composite_foundation_adapter=composite_foundation_adapter,
        foundation_provider_conformance=foundation_provider_conformance,
        foundation_runtime_adapter=foundation_runtime_adapter,
        foundation_runtime_router=foundation_runtime_router,
        foundation_model_deployment_attestation=foundation_model_deployment_attestation,
        universal_composition_receipt=universal_composition_receipt,
        universal_composition_settlement=universal_composition_settlement,
        universal_foundation_model_contract=universal_foundation_model_contract,
        universal_invocation_guard=universal_invocation_guard,
        universal_invocation_coverage=universal_invocation_coverage,
        universal_invocation_witness=universal_invocation_witness,
        universal_content_credential=universal_content_credential,
        universal_rdllm_passport=universal_rdllm_passport,
        universal_adoption_standard=universal_adoption_standard,
        universal_interop_test_kit=universal_interop_test_kit,
        universal_context_provenance_bridge=universal_context_provenance_bridge,
        universal_citation_verification_contract=universal_citation_verification_contract,
        universal_grounded_reuse_contract=universal_grounded_reuse_contract,
        universal_training_serving_contract=universal_training_serving_contract,
        universal_confidential_attribution_audit=universal_confidential_attribution_audit,
        universal_attribution_authority_control_plane=universal_attribution_authority_control_plane,
        revenue_allocation_report=revenue_allocation_report,
        finance_ledger_attestation=finance_ledger_attestation,
        proof_dependency_graph=proof_dependency_graph,
        publication_monitor=publication_monitor,
        publication_witness=publication_witness,
        trust_registry=trust_registry,
        certification_attestation=certification_attestation,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": manifest["summary"]["status"],
            "output": args.output,
            "manifest_hash": manifest["manifest_hash"],
            "provider": manifest["provider"],
            "artifact_count": manifest["summary"]["artifact_count"],
            "schema_count": manifest["summary"]["schema_count"],
        }
    else:
        result = manifest
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if manifest["summary"]["status"] == "ready" else 1


def run_verify_discovery_manifest(args: argparse.Namespace) -> int:
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    integration_profile = json.loads(
        Path(args.integration_profile).read_text(encoding="utf-8")
    )
    response_envelope = json.loads(
        Path(args.response_envelope).read_text(encoding="utf-8")
    )
    assurance_bundle = json.loads(Path(args.assurance_bundle).read_text(encoding="utf-8"))
    training_summary = (
        json.loads(Path(args.training_summary).read_text(encoding="utf-8"))
        if args.training_summary
        else None
    )
    provenance_evaluation_report = (
        json.loads(Path(args.provenance_evaluation_report).read_text(encoding="utf-8"))
        if args.provenance_evaluation_report
        else None
    )
    counterfactual_report = (
        json.loads(Path(args.counterfactual_report).read_text(encoding="utf-8"))
        if args.counterfactual_report
        else None
    )
    media_attribution_report = (
        json.loads(Path(args.media_attribution_report).read_text(encoding="utf-8"))
        if args.media_attribution_report
        else None
    )
    model_signal_report = (
        json.loads(Path(args.model_signal_report).read_text(encoding="utf-8"))
        if args.model_signal_report
        else None
    )
    pinpoint_provenance_report = (
        json.loads(Path(args.pinpoint_provenance_report).read_text(encoding="utf-8"))
        if args.pinpoint_provenance_report
        else None
    )
    citation_identity_report = (
        json.loads(Path(args.citation_identity_report).read_text(encoding="utf-8"))
        if args.citation_identity_report
        else None
    )
    attribution_consensus_report = (
        json.loads(Path(args.attribution_consensus_report).read_text(encoding="utf-8"))
        if args.attribution_consensus_report
        else None
    )
    verifier_quorum_report = (
        json.loads(Path(args.verifier_quorum_report).read_text(encoding="utf-8"))
        if args.verifier_quorum_report
        else None
    )
    verifier_accountability_report = (
        json.loads(Path(args.verifier_accountability_report).read_text(encoding="utf-8"))
        if args.verifier_accountability_report
        else None
    )
    receipt_transparency_consistency_report = (
        json.loads(
            Path(args.receipt_transparency_consistency_report).read_text(
                encoding="utf-8"
            )
        )
        if args.receipt_transparency_consistency_report
        else None
    )
    watchtower_challenge_settlement_report = (
        json.loads(
            Path(args.watchtower_challenge_settlement_report).read_text(
                encoding="utf-8"
            )
        )
        if args.watchtower_challenge_settlement_report
        else None
    )
    output_provenance_binding_report = (
        json.loads(
            Path(args.output_provenance_binding_report).read_text(encoding="utf-8")
        )
        if args.output_provenance_binding_report
        else None
    )
    rights_remediation_report = (
        json.loads(Path(args.rights_remediation_report).read_text(encoding="utf-8"))
        if args.rights_remediation_report
        else None
    )
    semantic_text_attribution_report = (
        json.loads(Path(args.semantic_text_attribution_report).read_text(encoding="utf-8"))
        if args.semantic_text_attribution_report
        else None
    )
    code_attribution_report = (
        json.loads(Path(args.code_attribution_report).read_text(encoding="utf-8"))
        if args.code_attribution_report
        else None
    )
    claim_verification_report = (
        json.loads(Path(args.claim_verification_report).read_text(encoding="utf-8"))
        if args.claim_verification_report
        else None
    )
    source_availability_report = (
        json.loads(Path(args.source_availability_report).read_text(encoding="utf-8"))
        if args.source_availability_report
        else None
    )
    evidence_sufficiency_report = (
        json.loads(Path(args.evidence_sufficiency_report).read_text(encoding="utf-8"))
        if args.evidence_sufficiency_report
        else None
    )
    counterevidence_report = (
        json.loads(Path(args.counterevidence_report).read_text(encoding="utf-8"))
        if args.counterevidence_report
        else None
    )
    answer_claim_coverage_report = (
        json.loads(Path(args.answer_claim_coverage_report).read_text(encoding="utf-8"))
        if args.answer_claim_coverage_report
        else None
    )
    generation_context_closure_report = (
        json.loads(
            Path(args.generation_context_closure_report).read_text(encoding="utf-8")
        )
        if args.generation_context_closure_report
        else None
    )
    source_boundary_report = (
        json.loads(Path(args.source_boundary_report).read_text(encoding="utf-8"))
        if args.source_boundary_report
        else None
    )
    source_authenticity_report = (
        json.loads(Path(args.source_authenticity_report).read_text(encoding="utf-8"))
        if args.source_authenticity_report
        else None
    )
    decision_provenance_report = (
        json.loads(Path(args.decision_provenance_report).read_text(encoding="utf-8"))
        if args.decision_provenance_report
        else None
    )
    calibrated_attribution_report = (
        json.loads(Path(args.calibrated_attribution_report).read_text(encoding="utf-8"))
        if args.calibrated_attribution_report
        else None
    )
    streaming_attribution_manifest = (
        json.loads(Path(args.streaming_attribution_manifest).read_text(encoding="utf-8"))
        if args.streaming_attribution_manifest
        else None
    )
    conversation_attribution_ledger = (
        json.loads(Path(args.conversation_attribution_ledger).read_text(encoding="utf-8"))
        if args.conversation_attribution_ledger
        else None
    )
    agent_tool_attribution_ledger = (
        json.loads(Path(args.agent_tool_attribution_ledger).read_text(encoding="utf-8"))
        if args.agent_tool_attribution_ledger
        else None
    )
    creator_license_contract = (
        json.loads(Path(args.creator_license_contract).read_text(encoding="utf-8"))
        if args.creator_license_contract
        else None
    )
    source_confidence_report = (
        json.loads(Path(args.source_confidence_report).read_text(encoding="utf-8"))
        if args.source_confidence_report
        else None
    )
    citation_footer_contract = (
        json.loads(Path(args.citation_footer_contract).read_text(encoding="utf-8"))
        if args.citation_footer_contract
        else None
    )
    private_audit_challenge = (
        json.loads(Path(args.private_audit_challenge).read_text(encoding="utf-8"))
        if args.private_audit_challenge
        else None
    )
    transitive_attribution_report = (
        json.loads(Path(args.transitive_attribution_report).read_text(encoding="utf-8"))
        if args.transitive_attribution_report
        else None
    )
    clearinghouse_report = (
        json.loads(Path(args.clearinghouse_report).read_text(encoding="utf-8"))
        if args.clearinghouse_report
        else None
    )
    remittance_report = (
        json.loads(Path(args.remittance_report).read_text(encoding="utf-8"))
        if args.remittance_report
        else None
    )
    payment_execution_report = (
        json.loads(Path(args.payment_execution_report).read_text(encoding="utf-8"))
        if args.payment_execution_report
        else None
    )
    payment_rail_attestation = (
        json.loads(Path(args.payment_rail_attestation).read_text(encoding="utf-8"))
        if args.payment_rail_attestation
        else None
    )
    creator_payout_receipt_report = (
        json.loads(Path(args.creator_payout_receipt_report).read_text(encoding="utf-8"))
        if args.creator_payout_receipt_report
        else None
    )
    rendered_attribution_audit = (
        json.loads(Path(args.rendered_attribution_audit).read_text(encoding="utf-8"))
        if args.rendered_attribution_audit
        else None
    )
    training_memory_provenance = (
        json.loads(Path(args.training_memory_provenance).read_text(encoding="utf-8"))
        if args.training_memory_provenance
        else None
    )
    post_training_signal_provenance = (
        json.loads(
            Path(args.post_training_signal_provenance).read_text(encoding="utf-8")
        )
        if args.post_training_signal_provenance
        else None
    )
    evidence_locked_generation = (
        json.loads(Path(args.evidence_locked_generation).read_text(encoding="utf-8"))
        if args.evidence_locked_generation
        else None
    )
    emission_evidence_enforcement = (
        json.loads(Path(args.emission_evidence_enforcement).read_text(encoding="utf-8"))
        if args.emission_evidence_enforcement
        else None
    )
    live_emission_witness = (
        json.loads(Path(args.live_emission_witness).read_text(encoding="utf-8"))
        if args.live_emission_witness
        else None
    )
    live_emission_transparency = (
        json.loads(Path(args.live_emission_transparency).read_text(encoding="utf-8"))
        if args.live_emission_transparency
        else None
    )
    attested_runtime = (
        json.loads(Path(args.attested_runtime).read_text(encoding="utf-8"))
        if args.attested_runtime
        else None
    )
    claim_source_attribution_report = (
        json.loads(Path(args.claim_source_attribution_report).read_text(encoding="utf-8"))
        if args.claim_source_attribution_report
        else None
    )
    evidence_utility_attribution_report = (
        json.loads(Path(args.evidence_utility_attribution_report).read_text(encoding="utf-8"))
        if args.evidence_utility_attribution_report
        else None
    )
    parametric_memory_attribution_report = (
        json.loads(Path(args.parametric_memory_attribution_report).read_text(encoding="utf-8"))
        if args.parametric_memory_attribution_report
        else None
    )
    style_influence_attribution_report = (
        json.loads(Path(args.style_influence_attribution_report).read_text(encoding="utf-8"))
        if args.style_influence_attribution_report
        else None
    )
    model_lineage_attribution_report = (
        json.loads(Path(args.model_lineage_attribution_report).read_text(encoding="utf-8"))
        if args.model_lineage_attribution_report
        else None
    )
    black_box_model_provenance_report = (
        json.loads(Path(args.black_box_model_provenance_report).read_text(encoding="utf-8"))
        if args.black_box_model_provenance_report
        else None
    )
    attribution_dispute_adjudication_report = (
        json.loads(Path(args.attribution_dispute_adjudication_report).read_text(encoding="utf-8"))
        if args.attribution_dispute_adjudication_report
        else None
    )
    post_adjudication_settlement_adjustment_report = (
        json.loads(
            Path(args.post_adjudication_settlement_adjustment_report).read_text(
                encoding="utf-8"
            )
        )
        if args.post_adjudication_settlement_adjustment_report
        else None
    )
    residual_corpus_royalty_report = (
        json.loads(Path(args.residual_corpus_royalty_report).read_text(encoding="utf-8"))
        if args.residual_corpus_royalty_report
        else None
    )
    valuation_method_audit_report = (
        json.loads(Path(args.valuation_method_audit_report).read_text(encoding="utf-8"))
        if args.valuation_method_audit_report
        else None
    )
    evidence_region_binding_report = (
        json.loads(
            Path(args.evidence_region_binding_report).read_text(encoding="utf-8")
        )
        if args.evidence_region_binding_report
        else None
    )
    source_access_lease_report = (
        json.loads(Path(args.source_access_lease_report).read_text(encoding="utf-8"))
        if args.source_access_lease_report
        else None
    )
    content_protocol_ingestion_report = (
        json.loads(
            Path(args.content_protocol_ingestion_report).read_text(encoding="utf-8")
        )
        if args.content_protocol_ingestion_report
        else None
    )
    citation_reliance_receipt = (
        json.loads(Path(args.citation_reliance_receipt).read_text(encoding="utf-8"))
        if args.citation_reliance_receipt
        else None
    )
    license_transaction_receipt = (
        json.loads(Path(args.license_transaction_receipt).read_text(encoding="utf-8"))
        if args.license_transaction_receipt
        else None
    )
    grounded_source_footer = (
        json.loads(Path(args.grounded_source_footer).read_text(encoding="utf-8"))
        if args.grounded_source_footer
        else None
    )
    source_footer_delivery = (
        json.loads(Path(args.source_footer_delivery).read_text(encoding="utf-8"))
        if args.source_footer_delivery
        else None
    )
    deep_research_citation_audit = (
        json.loads(Path(args.deep_research_citation_audit).read_text(encoding="utf-8"))
        if args.deep_research_citation_audit
        else None
    )
    source_freshness_audit = (
        json.loads(Path(args.source_freshness_audit).read_text(encoding="utf-8"))
        if args.source_freshness_audit
        else None
    )
    royalty_abuse_audit = (
        json.loads(Path(args.royalty_abuse_audit).read_text(encoding="utf-8"))
        if args.royalty_abuse_audit
        else None
    )
    consent_revocation_propagation = (
        json.loads(
            Path(args.consent_revocation_propagation).read_text(encoding="utf-8")
        )
        if args.consent_revocation_propagation
        else None
    )
    evidence_force_calibration = (
        json.loads(Path(args.evidence_force_calibration).read_text(encoding="utf-8"))
        if args.evidence_force_calibration
        else None
    )
    warranted_source_footer = (
        json.loads(Path(args.warranted_source_footer).read_text(encoding="utf-8"))
        if args.warranted_source_footer
        else None
    )
    source_origin_lineage = (
        json.loads(Path(args.source_origin_lineage).read_text(encoding="utf-8"))
        if args.source_origin_lineage
        else None
    )
    evidence_preview_footer = (
        json.loads(Path(args.evidence_preview_footer).read_text(encoding="utf-8"))
        if args.evidence_preview_footer
        else None
    )
    evidence_locator_manifest = (
        json.loads(Path(args.evidence_locator_manifest).read_text(encoding="utf-8"))
        if args.evidence_locator_manifest
        else None
    )
    citation_url_health = (
        json.loads(Path(args.citation_url_health).read_text(encoding="utf-8"))
        if args.citation_url_health
        else None
    )
    foundation_api_profile = (
        json.loads(Path(args.foundation_api_profile).read_text(encoding="utf-8"))
        if args.foundation_api_profile
        else None
    )
    composite_foundation_adapter = (
        json.loads(Path(args.composite_foundation_adapter).read_text(encoding="utf-8"))
        if args.composite_foundation_adapter
        else None
    )
    foundation_provider_conformance = (
        json.loads(Path(args.foundation_provider_conformance).read_text(encoding="utf-8"))
        if args.foundation_provider_conformance
        else None
    )
    foundation_runtime_adapter = (
        json.loads(Path(args.foundation_runtime_adapter).read_text(encoding="utf-8"))
        if args.foundation_runtime_adapter
        else None
    )
    foundation_runtime_router = (
        json.loads(Path(args.foundation_runtime_router).read_text(encoding="utf-8"))
        if args.foundation_runtime_router
        else None
    )
    foundation_model_deployment_attestation = (
        json.loads(
            Path(args.foundation_model_deployment_attestation).read_text(
                encoding="utf-8"
            )
        )
        if args.foundation_model_deployment_attestation
        else None
    )
    universal_composition_receipt = (
        json.loads(Path(args.universal_composition_receipt).read_text(encoding="utf-8"))
        if args.universal_composition_receipt
        else None
    )
    universal_composition_settlement = (
        json.loads(
            Path(args.universal_composition_settlement).read_text(encoding="utf-8")
        )
        if args.universal_composition_settlement
        else None
    )
    universal_foundation_model_contract = (
        json.loads(
            Path(args.universal_foundation_model_contract).read_text(
                encoding="utf-8"
            )
        )
        if args.universal_foundation_model_contract
        else None
    )
    universal_invocation_guard = (
        json.loads(Path(args.universal_invocation_guard).read_text(encoding="utf-8"))
        if args.universal_invocation_guard
        else None
    )
    universal_invocation_coverage = (
        json.loads(
            Path(args.universal_invocation_coverage).read_text(encoding="utf-8")
        )
        if args.universal_invocation_coverage
        else None
    )
    universal_invocation_witness = (
        json.loads(
            Path(args.universal_invocation_witness).read_text(encoding="utf-8")
        )
        if args.universal_invocation_witness
        else None
    )
    universal_content_credential = (
        json.loads(
            Path(args.universal_content_credential).read_text(encoding="utf-8")
        )
        if args.universal_content_credential
        else None
    )
    universal_rdllm_passport = (
        json.loads(Path(args.universal_rdllm_passport).read_text(encoding="utf-8"))
        if args.universal_rdllm_passport
        else None
    )
    universal_adoption_standard = (
        json.loads(Path(args.universal_adoption_standard).read_text(encoding="utf-8"))
        if args.universal_adoption_standard
        else None
    )
    universal_interop_test_kit = (
        json.loads(Path(args.universal_interop_test_kit).read_text(encoding="utf-8"))
        if args.universal_interop_test_kit
        else None
    )
    universal_context_provenance_bridge = (
        json.loads(
            Path(args.universal_context_provenance_bridge).read_text(encoding="utf-8")
        )
        if args.universal_context_provenance_bridge
        else None
    )
    universal_citation_verification_contract = (
        json.loads(
            Path(args.universal_citation_verification_contract).read_text(
                encoding="utf-8"
            )
        )
        if args.universal_citation_verification_contract
        else None
    )
    universal_grounded_reuse_contract = (
        json.loads(
            Path(args.universal_grounded_reuse_contract).read_text(encoding="utf-8")
        )
        if args.universal_grounded_reuse_contract
        else None
    )
    universal_training_serving_contract = (
        json.loads(
            Path(args.universal_training_serving_contract).read_text(encoding="utf-8")
        )
        if args.universal_training_serving_contract
        else None
    )
    universal_confidential_attribution_audit = (
        json.loads(
            Path(args.universal_confidential_attribution_audit).read_text(
                encoding="utf-8"
            )
        )
        if args.universal_confidential_attribution_audit
        else None
    )
    universal_attribution_authority_control_plane = (
        json.loads(
            Path(args.universal_attribution_authority_control_plane).read_text(
                encoding="utf-8"
            )
        )
        if args.universal_attribution_authority_control_plane
        else None
    )
    revenue_allocation_report = (
        json.loads(Path(args.revenue_allocation_report).read_text(encoding="utf-8"))
        if args.revenue_allocation_report
        else None
    )
    finance_ledger_attestation = (
        json.loads(Path(args.finance_ledger_attestation).read_text(encoding="utf-8"))
        if args.finance_ledger_attestation
        else None
    )
    proof_dependency_graph = (
        json.loads(Path(args.proof_dependency_graph).read_text(encoding="utf-8"))
        if args.proof_dependency_graph
        else None
    )
    publication_monitor = (
        json.loads(Path(args.publication_monitor).read_text(encoding="utf-8"))
        if args.publication_monitor
        else None
    )
    publication_witness = (
        json.loads(Path(args.publication_witness).read_text(encoding="utf-8"))
        if args.publication_witness
        else None
    )
    trust_registry = (
        json.loads(Path(args.trust_registry).read_text(encoding="utf-8"))
        if args.trust_registry
        else None
    )
    certification_attestation = (
        json.loads(Path(args.certification_attestation).read_text(encoding="utf-8"))
        if args.certification_attestation
        else None
    )
    errors = verify_discovery_manifest(
        manifest,
        provider_card=provider_card,
        certification_report=certification_report,
        integration_profile=integration_profile,
        response_envelope=response_envelope,
        assurance_bundle=assurance_bundle,
        training_summary=training_summary,
        provenance_evaluation_report=provenance_evaluation_report,
        counterfactual_report=counterfactual_report,
        media_attribution_report=media_attribution_report,
        model_signal_report=model_signal_report,
        pinpoint_provenance_report=pinpoint_provenance_report,
        citation_identity_report=citation_identity_report,
        attribution_consensus_report=attribution_consensus_report,
        verifier_quorum_report=verifier_quorum_report,
        verifier_accountability_report=verifier_accountability_report,
        receipt_transparency_consistency_report=receipt_transparency_consistency_report,
        watchtower_challenge_settlement_report=watchtower_challenge_settlement_report,
        output_provenance_binding_report=output_provenance_binding_report,
        rights_remediation_report=rights_remediation_report,
        semantic_text_attribution_report=semantic_text_attribution_report,
        code_attribution_report=code_attribution_report,
        claim_verification_report=claim_verification_report,
        source_availability_report=source_availability_report,
        evidence_sufficiency_report=evidence_sufficiency_report,
        counterevidence_report=counterevidence_report,
        answer_claim_coverage_report=answer_claim_coverage_report,
        generation_context_closure_report=generation_context_closure_report,
        source_boundary_report=source_boundary_report,
        source_authenticity_report=source_authenticity_report,
        decision_provenance_report=decision_provenance_report,
        calibrated_attribution_report=calibrated_attribution_report,
        streaming_attribution_manifest=streaming_attribution_manifest,
        conversation_attribution_ledger=conversation_attribution_ledger,
        agent_tool_attribution_ledger=agent_tool_attribution_ledger,
        creator_license_contract=creator_license_contract,
        source_confidence_report=source_confidence_report,
        citation_footer_contract=citation_footer_contract,
        private_audit_challenge=private_audit_challenge,
        transitive_attribution_report=transitive_attribution_report,
        clearinghouse_report=clearinghouse_report,
        remittance_report=remittance_report,
        payment_execution_report=payment_execution_report,
        payment_rail_attestation=payment_rail_attestation,
        creator_payout_receipt_report=creator_payout_receipt_report,
        rendered_attribution_audit=rendered_attribution_audit,
        training_memory_provenance=training_memory_provenance,
        post_training_signal_provenance=post_training_signal_provenance,
        evidence_locked_generation=evidence_locked_generation,
        emission_evidence_enforcement=emission_evidence_enforcement,
        live_emission_witness=live_emission_witness,
        live_emission_transparency=live_emission_transparency,
        attested_runtime=attested_runtime,
        claim_source_attribution_report=claim_source_attribution_report,
        evidence_utility_attribution_report=evidence_utility_attribution_report,
        parametric_memory_attribution_report=parametric_memory_attribution_report,
        style_influence_attribution_report=style_influence_attribution_report,
        model_lineage_attribution_report=model_lineage_attribution_report,
        black_box_model_provenance_report=black_box_model_provenance_report,
        attribution_dispute_adjudication_report=attribution_dispute_adjudication_report,
        post_adjudication_settlement_adjustment_report=(
            post_adjudication_settlement_adjustment_report
        ),
        residual_corpus_royalty_report=residual_corpus_royalty_report,
        valuation_method_audit_report=valuation_method_audit_report,
        evidence_region_binding_report=evidence_region_binding_report,
        source_access_lease_report=source_access_lease_report,
        content_protocol_ingestion_report=content_protocol_ingestion_report,
        citation_reliance_receipt=citation_reliance_receipt,
        license_transaction_receipt=license_transaction_receipt,
        grounded_source_footer=grounded_source_footer,
        source_footer_delivery=source_footer_delivery,
        deep_research_citation_audit=deep_research_citation_audit,
        source_freshness_audit=source_freshness_audit,
        royalty_abuse_audit=royalty_abuse_audit,
        consent_revocation_propagation=consent_revocation_propagation,
        evidence_force_calibration=evidence_force_calibration,
        warranted_source_footer=warranted_source_footer,
        source_origin_lineage=source_origin_lineage,
        evidence_preview_footer=evidence_preview_footer,
        evidence_locator_manifest=evidence_locator_manifest,
        citation_url_health=citation_url_health,
        foundation_api_profile=foundation_api_profile,
        composite_foundation_adapter=composite_foundation_adapter,
        foundation_provider_conformance=foundation_provider_conformance,
        foundation_runtime_adapter=foundation_runtime_adapter,
        foundation_runtime_router=foundation_runtime_router,
        foundation_model_deployment_attestation=foundation_model_deployment_attestation,
        universal_composition_receipt=universal_composition_receipt,
        universal_composition_settlement=universal_composition_settlement,
        universal_foundation_model_contract=universal_foundation_model_contract,
        universal_invocation_guard=universal_invocation_guard,
        universal_invocation_coverage=universal_invocation_coverage,
        universal_invocation_witness=universal_invocation_witness,
        universal_content_credential=universal_content_credential,
        universal_rdllm_passport=universal_rdllm_passport,
        universal_adoption_standard=universal_adoption_standard,
        universal_interop_test_kit=universal_interop_test_kit,
        universal_context_provenance_bridge=universal_context_provenance_bridge,
        universal_citation_verification_contract=universal_citation_verification_contract,
        universal_grounded_reuse_contract=universal_grounded_reuse_contract,
        universal_training_serving_contract=universal_training_serving_contract,
        universal_confidential_attribution_audit=universal_confidential_attribution_audit,
        universal_attribution_authority_control_plane=universal_attribution_authority_control_plane,
        revenue_allocation_report=revenue_allocation_report,
        finance_ledger_attestation=finance_ledger_attestation,
        proof_dependency_graph=proof_dependency_graph,
        publication_monitor=publication_monitor,
        publication_witness=publication_witness,
        trust_registry=trust_registry,
        certification_attestation=certification_attestation,
        signing_secret=args.signing_secret,
    )
    result = {
        "manifest": args.manifest,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "manifest_hash": manifest.get("manifest_hash", ""),
        "summary": manifest.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_attribution_exchange(args: argparse.Namespace) -> int:
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    integration_profile = json.loads(
        Path(args.integration_profile).read_text(encoding="utf-8")
    )
    discovery_manifest = json.loads(
        Path(args.discovery_manifest).read_text(encoding="utf-8")
    )
    response_envelope = json.loads(
        Path(args.response_envelope).read_text(encoding="utf-8")
    )
    assurance_bundle = json.loads(Path(args.assurance_bundle).read_text(encoding="utf-8"))
    semantic_text_attribution_report = json.loads(
        Path(args.semantic_text_attribution_report).read_text(encoding="utf-8")
    )
    creator_license_contract = json.loads(
        Path(args.creator_license_contract).read_text(encoding="utf-8")
    )
    source_confidence_report = (
        json.loads(Path(args.source_confidence_report).read_text(encoding="utf-8"))
        if args.source_confidence_report
        else None
    )
    citation_footer_contract = (
        json.loads(Path(args.citation_footer_contract).read_text(encoding="utf-8"))
        if args.citation_footer_contract
        else None
    )
    private_audit_challenge = (
        json.loads(Path(args.private_audit_challenge).read_text(encoding="utf-8"))
        if args.private_audit_challenge
        else None
    )
    exchange = make_attribution_exchange_manifest(
        provider_card=provider_card,
        certification_report=certification_report,
        integration_profile=integration_profile,
        discovery_manifest=discovery_manifest,
        response_envelope=response_envelope,
        assurance_bundle=assurance_bundle,
        semantic_text_attribution_report=semantic_text_attribution_report,
        creator_license_contract=creator_license_contract,
        source_confidence_report=source_confidence_report,
        citation_footer_contract=citation_footer_contract,
        private_audit_challenge=private_audit_challenge,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(exchange, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": exchange["summary"]["status"],
            "output": args.output,
            "exchange_hash": exchange["exchange_hash"],
            "provider": exchange["provider"],
            "artifact_count": exchange["summary"]["artifact_count"],
            "source_footer_count": exchange["summary"]["source_footer_count"],
        }
    else:
        result = exchange
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if exchange["summary"]["status"] == "ready" else 1


def run_verify_attribution_exchange(args: argparse.Namespace) -> int:
    exchange = json.loads(Path(args.exchange).read_text(encoding="utf-8"))
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    integration_profile = json.loads(
        Path(args.integration_profile).read_text(encoding="utf-8")
    )
    discovery_manifest = json.loads(
        Path(args.discovery_manifest).read_text(encoding="utf-8")
    )
    response_envelope = json.loads(
        Path(args.response_envelope).read_text(encoding="utf-8")
    )
    assurance_bundle = json.loads(Path(args.assurance_bundle).read_text(encoding="utf-8"))
    semantic_text_attribution_report = json.loads(
        Path(args.semantic_text_attribution_report).read_text(encoding="utf-8")
    )
    creator_license_contract = json.loads(
        Path(args.creator_license_contract).read_text(encoding="utf-8")
    )
    training_summary = (
        json.loads(Path(args.training_summary).read_text(encoding="utf-8"))
        if args.training_summary
        else None
    )
    provenance_evaluation_report = (
        json.loads(Path(args.provenance_evaluation_report).read_text(encoding="utf-8"))
        if args.provenance_evaluation_report
        else None
    )
    counterfactual_report = (
        json.loads(Path(args.counterfactual_report).read_text(encoding="utf-8"))
        if args.counterfactual_report
        else None
    )
    media_attribution_report = (
        json.loads(Path(args.media_attribution_report).read_text(encoding="utf-8"))
        if args.media_attribution_report
        else None
    )
    model_signal_report = (
        json.loads(Path(args.model_signal_report).read_text(encoding="utf-8"))
        if args.model_signal_report
        else None
    )
    rights_remediation_report = (
        json.loads(Path(args.rights_remediation_report).read_text(encoding="utf-8"))
        if args.rights_remediation_report
        else None
    )
    source_confidence_report = (
        json.loads(Path(args.source_confidence_report).read_text(encoding="utf-8"))
        if args.source_confidence_report
        else None
    )
    citation_footer_contract = (
        json.loads(Path(args.citation_footer_contract).read_text(encoding="utf-8"))
        if args.citation_footer_contract
        else None
    )
    private_audit_challenge = (
        json.loads(Path(args.private_audit_challenge).read_text(encoding="utf-8"))
        if args.private_audit_challenge
        else None
    )
    errors = verify_attribution_exchange_manifest(
        exchange,
        provider_card=provider_card,
        certification_report=certification_report,
        integration_profile=integration_profile,
        discovery_manifest=discovery_manifest,
        response_envelope=response_envelope,
        assurance_bundle=assurance_bundle,
        semantic_text_attribution_report=semantic_text_attribution_report,
        creator_license_contract=creator_license_contract,
        training_summary=training_summary,
        provenance_evaluation_report=provenance_evaluation_report,
        counterfactual_report=counterfactual_report,
        media_attribution_report=media_attribution_report,
        model_signal_report=model_signal_report,
        rights_remediation_report=rights_remediation_report,
        source_confidence_report=source_confidence_report,
        citation_footer_contract=citation_footer_contract,
        private_audit_challenge=private_audit_challenge,
        signing_secret=args.signing_secret,
    )
    result = {
        "exchange": args.exchange,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "exchange_hash": exchange.get("exchange_hash", ""),
        "summary": exchange.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_conformance_vector_pack(args: argparse.Namespace) -> int:
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    integration_profile = json.loads(
        Path(args.integration_profile).read_text(encoding="utf-8")
    )
    discovery_manifest = json.loads(
        Path(args.discovery_manifest).read_text(encoding="utf-8")
    )
    response_envelope = json.loads(
        Path(args.response_envelope).read_text(encoding="utf-8")
    )
    assurance_bundle = json.loads(Path(args.assurance_bundle).read_text(encoding="utf-8"))
    semantic_text_attribution_report = json.loads(
        Path(args.semantic_text_attribution_report).read_text(encoding="utf-8")
    )
    creator_license_contract = json.loads(
        Path(args.creator_license_contract).read_text(encoding="utf-8")
    )
    attribution_exchange = json.loads(
        Path(args.attribution_exchange).read_text(encoding="utf-8")
    )
    training_summary = (
        json.loads(Path(args.training_summary).read_text(encoding="utf-8"))
        if args.training_summary
        else None
    )
    provenance_evaluation_report = (
        json.loads(Path(args.provenance_evaluation_report).read_text(encoding="utf-8"))
        if args.provenance_evaluation_report
        else None
    )
    counterfactual_report = (
        json.loads(Path(args.counterfactual_report).read_text(encoding="utf-8"))
        if args.counterfactual_report
        else None
    )
    media_attribution_report = (
        json.loads(Path(args.media_attribution_report).read_text(encoding="utf-8"))
        if args.media_attribution_report
        else None
    )
    model_signal_report = (
        json.loads(Path(args.model_signal_report).read_text(encoding="utf-8"))
        if args.model_signal_report
        else None
    )
    rights_remediation_report = (
        json.loads(Path(args.rights_remediation_report).read_text(encoding="utf-8"))
        if args.rights_remediation_report
        else None
    )
    source_confidence_report = (
        json.loads(Path(args.source_confidence_report).read_text(encoding="utf-8"))
        if args.source_confidence_report
        else None
    )
    citation_footer_contract = (
        json.loads(Path(args.citation_footer_contract).read_text(encoding="utf-8"))
        if args.citation_footer_contract
        else None
    )
    private_audit_challenge = (
        json.loads(Path(args.private_audit_challenge).read_text(encoding="utf-8"))
        if args.private_audit_challenge
        else None
    )
    pack = make_conformance_vector_pack(
        provider_card=provider_card,
        certification_report=certification_report,
        integration_profile=integration_profile,
        discovery_manifest=discovery_manifest,
        response_envelope=response_envelope,
        assurance_bundle=assurance_bundle,
        semantic_text_attribution_report=semantic_text_attribution_report,
        creator_license_contract=creator_license_contract,
        attribution_exchange=attribution_exchange,
        training_summary=training_summary,
        provenance_evaluation_report=provenance_evaluation_report,
        counterfactual_report=counterfactual_report,
        media_attribution_report=media_attribution_report,
        model_signal_report=model_signal_report,
        rights_remediation_report=rights_remediation_report,
        source_confidence_report=source_confidence_report,
        citation_footer_contract=citation_footer_contract,
        private_audit_challenge=private_audit_challenge,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(pack, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": pack["summary"]["status"],
            "output": args.output,
            "vector_pack_hash": pack["vector_pack_hash"],
            "test_vector_count": pack["summary"]["test_vector_count"],
            "negative_mutation_count": pack["summary"]["negative_mutation_count"],
            "target_certification_level": pack["summary"]["target_certification_level"],
        }
    else:
        result = pack
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if pack["summary"]["status"] == "ready" else 1


def run_verify_conformance_vector_pack(args: argparse.Namespace) -> int:
    pack = json.loads(Path(args.pack).read_text(encoding="utf-8"))
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    integration_profile = json.loads(
        Path(args.integration_profile).read_text(encoding="utf-8")
    )
    discovery_manifest = json.loads(
        Path(args.discovery_manifest).read_text(encoding="utf-8")
    )
    response_envelope = json.loads(
        Path(args.response_envelope).read_text(encoding="utf-8")
    )
    assurance_bundle = json.loads(Path(args.assurance_bundle).read_text(encoding="utf-8"))
    semantic_text_attribution_report = json.loads(
        Path(args.semantic_text_attribution_report).read_text(encoding="utf-8")
    )
    creator_license_contract = json.loads(
        Path(args.creator_license_contract).read_text(encoding="utf-8")
    )
    attribution_exchange = json.loads(
        Path(args.attribution_exchange).read_text(encoding="utf-8")
    )
    training_summary = (
        json.loads(Path(args.training_summary).read_text(encoding="utf-8"))
        if args.training_summary
        else None
    )
    provenance_evaluation_report = (
        json.loads(Path(args.provenance_evaluation_report).read_text(encoding="utf-8"))
        if args.provenance_evaluation_report
        else None
    )
    counterfactual_report = (
        json.loads(Path(args.counterfactual_report).read_text(encoding="utf-8"))
        if args.counterfactual_report
        else None
    )
    media_attribution_report = (
        json.loads(Path(args.media_attribution_report).read_text(encoding="utf-8"))
        if args.media_attribution_report
        else None
    )
    model_signal_report = (
        json.loads(Path(args.model_signal_report).read_text(encoding="utf-8"))
        if args.model_signal_report
        else None
    )
    rights_remediation_report = (
        json.loads(Path(args.rights_remediation_report).read_text(encoding="utf-8"))
        if args.rights_remediation_report
        else None
    )
    source_confidence_report = (
        json.loads(Path(args.source_confidence_report).read_text(encoding="utf-8"))
        if args.source_confidence_report
        else None
    )
    citation_footer_contract = (
        json.loads(Path(args.citation_footer_contract).read_text(encoding="utf-8"))
        if args.citation_footer_contract
        else None
    )
    private_audit_challenge = (
        json.loads(Path(args.private_audit_challenge).read_text(encoding="utf-8"))
        if args.private_audit_challenge
        else None
    )
    errors = verify_conformance_vector_pack(
        pack,
        provider_card=provider_card,
        certification_report=certification_report,
        integration_profile=integration_profile,
        discovery_manifest=discovery_manifest,
        response_envelope=response_envelope,
        assurance_bundle=assurance_bundle,
        semantic_text_attribution_report=semantic_text_attribution_report,
        creator_license_contract=creator_license_contract,
        attribution_exchange=attribution_exchange,
        training_summary=training_summary,
        provenance_evaluation_report=provenance_evaluation_report,
        counterfactual_report=counterfactual_report,
        media_attribution_report=media_attribution_report,
        model_signal_report=model_signal_report,
        rights_remediation_report=rights_remediation_report,
        source_confidence_report=source_confidence_report,
        citation_footer_contract=citation_footer_contract,
        private_audit_challenge=private_audit_challenge,
        signing_secret=args.signing_secret,
    )
    result = {
        "pack": args.pack,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "vector_pack_hash": pack.get("vector_pack_hash", ""),
        "summary": pack.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_federation_handshake(args: argparse.Namespace) -> int:
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    integration_profile = json.loads(
        Path(args.integration_profile).read_text(encoding="utf-8")
    )
    discovery_manifest = json.loads(
        Path(args.discovery_manifest).read_text(encoding="utf-8")
    )
    response_envelope = json.loads(
        Path(args.response_envelope).read_text(encoding="utf-8")
    )
    assurance_bundle = json.loads(Path(args.assurance_bundle).read_text(encoding="utf-8"))
    semantic_text_attribution_report = json.loads(
        Path(args.semantic_text_attribution_report).read_text(encoding="utf-8")
    )
    creator_license_contract = json.loads(
        Path(args.creator_license_contract).read_text(encoding="utf-8")
    )
    attribution_exchange = json.loads(
        Path(args.attribution_exchange).read_text(encoding="utf-8")
    )
    conformance_vector_pack = json.loads(
        Path(args.conformance_vector_pack).read_text(encoding="utf-8")
    )
    training_summary = (
        json.loads(Path(args.training_summary).read_text(encoding="utf-8"))
        if args.training_summary
        else None
    )
    provenance_evaluation_report = (
        json.loads(Path(args.provenance_evaluation_report).read_text(encoding="utf-8"))
        if args.provenance_evaluation_report
        else None
    )
    counterfactual_report = (
        json.loads(Path(args.counterfactual_report).read_text(encoding="utf-8"))
        if args.counterfactual_report
        else None
    )
    media_attribution_report = (
        json.loads(Path(args.media_attribution_report).read_text(encoding="utf-8"))
        if args.media_attribution_report
        else None
    )
    model_signal_report = (
        json.loads(Path(args.model_signal_report).read_text(encoding="utf-8"))
        if args.model_signal_report
        else None
    )
    rights_remediation_report = (
        json.loads(Path(args.rights_remediation_report).read_text(encoding="utf-8"))
        if args.rights_remediation_report
        else None
    )
    source_confidence_report = (
        json.loads(Path(args.source_confidence_report).read_text(encoding="utf-8"))
        if args.source_confidence_report
        else None
    )
    citation_footer_contract = (
        json.loads(Path(args.citation_footer_contract).read_text(encoding="utf-8"))
        if args.citation_footer_contract
        else None
    )
    private_audit_challenge = (
        json.loads(Path(args.private_audit_challenge).read_text(encoding="utf-8"))
        if args.private_audit_challenge
        else None
    )
    handshake = make_federation_handshake(
        provider_card=provider_card,
        certification_report=certification_report,
        integration_profile=integration_profile,
        discovery_manifest=discovery_manifest,
        response_envelope=response_envelope,
        assurance_bundle=assurance_bundle,
        semantic_text_attribution_report=semantic_text_attribution_report,
        creator_license_contract=creator_license_contract,
        attribution_exchange=attribution_exchange,
        conformance_vector_pack=conformance_vector_pack,
        training_summary=training_summary,
        provenance_evaluation_report=provenance_evaluation_report,
        counterfactual_report=counterfactual_report,
        media_attribution_report=media_attribution_report,
        model_signal_report=model_signal_report,
        rights_remediation_report=rights_remediation_report,
        source_confidence_report=source_confidence_report,
        citation_footer_contract=citation_footer_contract,
        private_audit_challenge=private_audit_challenge,
        requester=args.requester,
        requester_model_id=args.requester_model_id,
        requester_model_version=args.requester_model_version,
        minimum_certification_level=args.minimum_level,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(handshake, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": handshake["summary"]["status"],
            "output": args.output,
            "handshake_hash": handshake["handshake_hash"],
            "negotiated_level": handshake["summary"]["negotiated_level"],
            "artifact_count": handshake["summary"]["artifact_count"],
            "runtime_header_count": handshake["summary"]["runtime_header_count"],
        }
    else:
        result = handshake
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if handshake["summary"]["status"] == "ready" else 1


def run_verify_federation_handshake(args: argparse.Namespace) -> int:
    handshake = json.loads(Path(args.handshake).read_text(encoding="utf-8"))
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    integration_profile = json.loads(
        Path(args.integration_profile).read_text(encoding="utf-8")
    )
    discovery_manifest = json.loads(
        Path(args.discovery_manifest).read_text(encoding="utf-8")
    )
    response_envelope = json.loads(
        Path(args.response_envelope).read_text(encoding="utf-8")
    )
    assurance_bundle = json.loads(Path(args.assurance_bundle).read_text(encoding="utf-8"))
    semantic_text_attribution_report = json.loads(
        Path(args.semantic_text_attribution_report).read_text(encoding="utf-8")
    )
    creator_license_contract = json.loads(
        Path(args.creator_license_contract).read_text(encoding="utf-8")
    )
    attribution_exchange = json.loads(
        Path(args.attribution_exchange).read_text(encoding="utf-8")
    )
    conformance_vector_pack = json.loads(
        Path(args.conformance_vector_pack).read_text(encoding="utf-8")
    )
    training_summary = (
        json.loads(Path(args.training_summary).read_text(encoding="utf-8"))
        if args.training_summary
        else None
    )
    provenance_evaluation_report = (
        json.loads(Path(args.provenance_evaluation_report).read_text(encoding="utf-8"))
        if args.provenance_evaluation_report
        else None
    )
    counterfactual_report = (
        json.loads(Path(args.counterfactual_report).read_text(encoding="utf-8"))
        if args.counterfactual_report
        else None
    )
    media_attribution_report = (
        json.loads(Path(args.media_attribution_report).read_text(encoding="utf-8"))
        if args.media_attribution_report
        else None
    )
    model_signal_report = (
        json.loads(Path(args.model_signal_report).read_text(encoding="utf-8"))
        if args.model_signal_report
        else None
    )
    rights_remediation_report = (
        json.loads(Path(args.rights_remediation_report).read_text(encoding="utf-8"))
        if args.rights_remediation_report
        else None
    )
    source_confidence_report = (
        json.loads(Path(args.source_confidence_report).read_text(encoding="utf-8"))
        if args.source_confidence_report
        else None
    )
    citation_footer_contract = (
        json.loads(Path(args.citation_footer_contract).read_text(encoding="utf-8"))
        if args.citation_footer_contract
        else None
    )
    private_audit_challenge = (
        json.loads(Path(args.private_audit_challenge).read_text(encoding="utf-8"))
        if args.private_audit_challenge
        else None
    )
    errors = verify_federation_handshake(
        handshake,
        provider_card=provider_card,
        certification_report=certification_report,
        integration_profile=integration_profile,
        discovery_manifest=discovery_manifest,
        response_envelope=response_envelope,
        assurance_bundle=assurance_bundle,
        semantic_text_attribution_report=semantic_text_attribution_report,
        creator_license_contract=creator_license_contract,
        attribution_exchange=attribution_exchange,
        conformance_vector_pack=conformance_vector_pack,
        training_summary=training_summary,
        provenance_evaluation_report=provenance_evaluation_report,
        counterfactual_report=counterfactual_report,
        media_attribution_report=media_attribution_report,
        model_signal_report=model_signal_report,
        rights_remediation_report=rights_remediation_report,
        source_confidence_report=source_confidence_report,
        citation_footer_contract=citation_footer_contract,
        private_audit_challenge=private_audit_challenge,
        signing_secret=args.signing_secret,
    )
    result = {
        "handshake": args.handshake,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "handshake_hash": handshake.get("handshake_hash", ""),
        "summary": handshake.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def _capsule_optional_artifacts(args: argparse.Namespace) -> dict[str, dict[str, object] | None]:
    return {
        "training_summary": (
            json.loads(Path(args.training_summary).read_text(encoding="utf-8"))
            if args.training_summary
            else None
        ),
        "provenance_evaluation_report": (
            json.loads(Path(args.provenance_evaluation_report).read_text(encoding="utf-8"))
            if args.provenance_evaluation_report
            else None
        ),
        "counterfactual_report": (
            json.loads(Path(args.counterfactual_report).read_text(encoding="utf-8"))
            if args.counterfactual_report
            else None
        ),
        "media_attribution_report": (
            json.loads(Path(args.media_attribution_report).read_text(encoding="utf-8"))
            if args.media_attribution_report
            else None
        ),
        "model_signal_report": (
            json.loads(Path(args.model_signal_report).read_text(encoding="utf-8"))
            if args.model_signal_report
            else None
        ),
        "rights_remediation_report": (
            json.loads(Path(args.rights_remediation_report).read_text(encoding="utf-8"))
            if args.rights_remediation_report
            else None
        ),
        "private_audit_challenge": (
            json.loads(Path(args.private_audit_challenge).read_text(encoding="utf-8"))
            if args.private_audit_challenge
            else None
        ),
    }


def run_attribution_capsule(args: argparse.Namespace) -> int:
    response_envelope = json.loads(
        Path(args.response_envelope).read_text(encoding="utf-8")
    )
    federation_handshake = json.loads(
        Path(args.federation_handshake).read_text(encoding="utf-8")
    )
    attribution_exchange = json.loads(
        Path(args.attribution_exchange).read_text(encoding="utf-8")
    )
    conformance_vector_pack = json.loads(
        Path(args.conformance_vector_pack).read_text(encoding="utf-8")
    )
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    integration_profile = json.loads(
        Path(args.integration_profile).read_text(encoding="utf-8")
    )
    discovery_manifest = json.loads(
        Path(args.discovery_manifest).read_text(encoding="utf-8")
    )
    assurance_bundle = json.loads(Path(args.assurance_bundle).read_text(encoding="utf-8"))
    semantic_text_attribution_report = json.loads(
        Path(args.semantic_text_attribution_report).read_text(encoding="utf-8")
    )
    creator_license_contract = json.loads(
        Path(args.creator_license_contract).read_text(encoding="utf-8")
    )
    source_confidence_report = (
        json.loads(Path(args.source_confidence_report).read_text(encoding="utf-8"))
        if args.source_confidence_report
        else None
    )
    citation_footer_contract = (
        json.loads(Path(args.citation_footer_contract).read_text(encoding="utf-8"))
        if args.citation_footer_contract
        else None
    )
    optional = _capsule_optional_artifacts(args)
    capsule = make_attribution_capsule(
        response_envelope=response_envelope,
        federation_handshake=federation_handshake,
        attribution_exchange=attribution_exchange,
        conformance_vector_pack=conformance_vector_pack,
        provider_card=provider_card,
        certification_report=certification_report,
        integration_profile=integration_profile,
        discovery_manifest=discovery_manifest,
        assurance_bundle=assurance_bundle,
        semantic_text_attribution_report=semantic_text_attribution_report,
        creator_license_contract=creator_license_contract,
        source_confidence_report=source_confidence_report,
        citation_footer_contract=citation_footer_contract,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
        **optional,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(capsule, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": capsule["summary"]["status"],
            "output": args.output,
            "capsule_hash": capsule["capsule_hash"],
            "capsule_id": capsule["summary"]["capsule_id"],
            "target_certification_level": capsule["summary"][
                "target_certification_level"
            ],
            "artifact_count": capsule["summary"]["artifact_count"],
            "text_footer": capsule["portable_surfaces"]["text_footer"],
        }
    else:
        result = capsule
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if capsule["summary"]["status"] == "ready" else 1


def run_verify_attribution_capsule(args: argparse.Namespace) -> int:
    capsule = json.loads(Path(args.capsule).read_text(encoding="utf-8"))
    response_envelope = json.loads(
        Path(args.response_envelope).read_text(encoding="utf-8")
    )
    federation_handshake = json.loads(
        Path(args.federation_handshake).read_text(encoding="utf-8")
    )
    attribution_exchange = json.loads(
        Path(args.attribution_exchange).read_text(encoding="utf-8")
    )
    conformance_vector_pack = json.loads(
        Path(args.conformance_vector_pack).read_text(encoding="utf-8")
    )
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    integration_profile = json.loads(
        Path(args.integration_profile).read_text(encoding="utf-8")
    )
    discovery_manifest = json.loads(
        Path(args.discovery_manifest).read_text(encoding="utf-8")
    )
    assurance_bundle = json.loads(Path(args.assurance_bundle).read_text(encoding="utf-8"))
    semantic_text_attribution_report = json.loads(
        Path(args.semantic_text_attribution_report).read_text(encoding="utf-8")
    )
    creator_license_contract = json.loads(
        Path(args.creator_license_contract).read_text(encoding="utf-8")
    )
    source_confidence_report = (
        json.loads(Path(args.source_confidence_report).read_text(encoding="utf-8"))
        if args.source_confidence_report
        else None
    )
    citation_footer_contract = (
        json.loads(Path(args.citation_footer_contract).read_text(encoding="utf-8"))
        if args.citation_footer_contract
        else None
    )
    copied_output = args.copied_output
    if args.copied_output_file:
        copied_output = Path(args.copied_output_file).read_text(encoding="utf-8")
    optional = _capsule_optional_artifacts(args)
    errors = verify_attribution_capsule(
        capsule,
        response_envelope=response_envelope,
        federation_handshake=federation_handshake,
        attribution_exchange=attribution_exchange,
        conformance_vector_pack=conformance_vector_pack,
        provider_card=provider_card,
        certification_report=certification_report,
        integration_profile=integration_profile,
        discovery_manifest=discovery_manifest,
        assurance_bundle=assurance_bundle,
        semantic_text_attribution_report=semantic_text_attribution_report,
        creator_license_contract=creator_license_contract,
        source_confidence_report=source_confidence_report,
        citation_footer_contract=citation_footer_contract,
        copied_output=copied_output,
        signing_secret=args.signing_secret,
        **optional,
    )
    result = {
        "capsule": args.capsule,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "capsule_hash": capsule.get("capsule_hash", ""),
        "capsule_id": capsule.get("summary", {}).get("capsule_id", ""),
        "summary": capsule.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_release_gate(args: argparse.Namespace) -> int:
    response_envelope = json.loads(
        Path(args.response_envelope).read_text(encoding="utf-8")
    )
    attribution_capsule = json.loads(
        Path(args.attribution_capsule).read_text(encoding="utf-8")
    )
    creator_license_contract = json.loads(
        Path(args.creator_license_contract).read_text(encoding="utf-8")
    )
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    gate = make_release_gate_report(
        response_envelope=response_envelope,
        attribution_capsule=attribution_capsule,
        creator_license_contract=creator_license_contract,
        provider_card=provider_card,
        certification_report=certification_report,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(gate, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "decision": gate["summary"]["decision"],
            "output": args.output,
            "gate_hash": gate["gate_hash"],
            "release_mode": gate["summary"]["release_mode"],
            "passed_check_count": gate["summary"]["passed_check_count"],
            "check_count": gate["summary"]["check_count"],
        }
    else:
        result = gate
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if gate["summary"]["decision"] == "emit" else 1


def run_verify_release_gate(args: argparse.Namespace) -> int:
    gate = json.loads(Path(args.gate).read_text(encoding="utf-8"))
    response_envelope = json.loads(
        Path(args.response_envelope).read_text(encoding="utf-8")
    )
    attribution_capsule = json.loads(
        Path(args.attribution_capsule).read_text(encoding="utf-8")
    )
    creator_license_contract = json.loads(
        Path(args.creator_license_contract).read_text(encoding="utf-8")
    )
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    errors = verify_release_gate_report(
        gate,
        response_envelope=response_envelope,
        attribution_capsule=attribution_capsule,
        creator_license_contract=creator_license_contract,
        provider_card=provider_card,
        certification_report=certification_report,
        signing_secret=args.signing_secret,
    )
    result = {
        "gate": args.gate,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "gate_hash": gate.get("gate_hash", ""),
        "summary": gate.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_proof_carrying_response(args: argparse.Namespace) -> int:
    response_envelope = json.loads(
        Path(args.response_envelope).read_text(encoding="utf-8")
    )
    attribution_capsule = json.loads(
        Path(args.attribution_capsule).read_text(encoding="utf-8")
    )
    release_gate = json.loads(Path(args.release_gate).read_text(encoding="utf-8"))
    creator_license_contract = json.loads(
        Path(args.creator_license_contract).read_text(encoding="utf-8")
    )
    provider_card = json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    proof_response = make_proof_carrying_response(
        response_envelope=response_envelope,
        attribution_capsule=attribution_capsule,
        release_gate=release_gate,
        creator_license_contract=creator_license_contract,
        provider_card=provider_card,
        certification_report=certification_report,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(proof_response, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": proof_response["summary"]["status"],
            "decision": proof_response["summary"]["decision"],
            "output": args.output,
            "proof_response_hash": proof_response["proof_response_hash"],
            "passed_check_count": proof_response["summary"]["passed_check_count"],
            "check_count": proof_response["summary"]["check_count"],
        }
    else:
        result = proof_response
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if proof_response["summary"]["status"] == "released" else 1


def run_verify_proof_carrying_response(args: argparse.Namespace) -> int:
    proof_response = json.loads(Path(args.response).read_text(encoding="utf-8"))
    errors = verify_proof_carrying_response(
        proof_response,
        signing_secret=args.signing_secret,
    )
    result = {
        "response": args.response,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "proof_response_hash": proof_response.get("proof_response_hash", ""),
        "summary": proof_response.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def _text_arg(value: str | None, file_path: str | None) -> str | None:
    if file_path:
        return Path(file_path).read_text(encoding="utf-8")
    return value


def run_serving_gateway_report(args: argparse.Namespace) -> int:
    proof_response = json.loads(Path(args.proof_response).read_text(encoding="utf-8"))
    prompt = _text_arg(args.prompt, args.prompt_file)
    raw_model_output = _text_arg(args.raw_model_output, args.raw_model_output_file)
    delivered_output = _text_arg(args.delivered_output, args.delivered_output_file)
    report = make_serving_gateway_report(
        proof_carrying_response=proof_response,
        request_id=args.request_id,
        provider=args.provider,
        model_id=args.model_id,
        model_version=args.model_version,
        route_id=args.route_id,
        prompt=prompt,
        raw_model_output=raw_model_output,
        delivered_output=delivered_output,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "delivery_status": report["summary"]["delivery_status"],
            "output": args.output,
            "gateway_report_hash": report["gateway_report_hash"],
            "proof_response_hash": report["summary"]["proof_response_hash"],
            "passed_check_count": report["summary"]["passed_check_count"],
            "check_count": report["summary"]["check_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "served" else 1


def run_verify_serving_gateway_report(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    prompt = _text_arg(args.prompt, args.prompt_file)
    raw_model_output = _text_arg(args.raw_model_output, args.raw_model_output_file)
    delivered_output = _text_arg(args.delivered_output, args.delivered_output_file)
    errors = verify_serving_gateway_report(
        report,
        prompt=prompt,
        raw_model_output=raw_model_output,
        delivered_output=delivered_output,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "gateway_report_hash": report.get("gateway_report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def _stream_chunks_arg(chunks_file: str | None) -> list[str] | None:
    if not chunks_file:
        return None
    payload = json.loads(Path(chunks_file).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("--chunks-file must contain a JSON array of strings")
    return [str(item) for item in payload]


def run_streaming_attribution_manifest(args: argparse.Namespace) -> int:
    proof_response = json.loads(Path(args.proof_response).read_text(encoding="utf-8"))
    gateway_report = json.loads(Path(args.serving_gateway_report).read_text(encoding="utf-8"))
    streamed_chunks = _stream_chunks_arg(args.chunks_file)
    manifest = make_streaming_attribution_manifest(
        proof_carrying_response=proof_response,
        serving_gateway_report=gateway_report,
        streamed_chunks=streamed_chunks,
        chunk_size=args.chunk_size,
        issuer=args.issuer,
        proof_verified_at=args.proof_verified_at,
        gateway_verified_at=args.gateway_verified_at,
        stream_started_at=args.stream_started_at,
        stream_completed_at=args.stream_completed_at,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": manifest["summary"]["status"],
            "output": args.output,
            "streaming_manifest_hash": manifest["streaming_manifest_hash"],
            "proof_response_hash": manifest["summary"]["proof_response_hash"],
            "gateway_report_hash": manifest["summary"]["gateway_report_hash"],
            "chunk_count": manifest["summary"]["chunk_count"],
            "passed_check_count": manifest["summary"]["passed_check_count"],
            "check_count": manifest["summary"]["check_count"],
        }
    else:
        result = manifest
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if manifest["summary"]["status"] == "committed" else 1


def run_verify_streaming_attribution_manifest(args: argparse.Namespace) -> int:
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    errors = verify_streaming_attribution_manifest(
        manifest,
        signing_secret=args.signing_secret,
    )
    result = {
        "manifest": args.manifest,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "streaming_manifest_hash": manifest.get("streaming_manifest_hash", ""),
        "summary": manifest.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def _conversation_turns_arg(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.turns_file:
        payload = json.loads(Path(args.turns_file).read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("--turns-file must contain a JSON array")
        turns: list[dict[str, Any]] = []
        for index, item in enumerate(payload):
            if not isinstance(item, dict):
                raise ValueError("--turns-file entries must be JSON objects")
            turn_id = str(item.get("turn_id") or f"turn-{index + 1}")
            depends = [str(value) for value in item.get("depends_on_turn_ids", [])]
            proof_path = item.get("proof_response") or item.get("proof_carrying_response")
            gateway_path = item.get("serving_gateway_report")
            stream_path = item.get("streaming_attribution_manifest")
            if not proof_path or not gateway_path or not stream_path:
                raise ValueError("turns-file entries require proof, gateway, and stream paths")
            turns.append(
                {
                    "turn_id": turn_id,
                    "depends_on_turn_ids": depends,
                    "proof_carrying_response": json.loads(
                        Path(str(proof_path)).read_text(encoding="utf-8")
                    ),
                    "serving_gateway_report": json.loads(
                        Path(str(gateway_path)).read_text(encoding="utf-8")
                    ),
                    "streaming_attribution_manifest": json.loads(
                        Path(str(stream_path)).read_text(encoding="utf-8")
                    ),
                }
            )
        return turns
    turns = []
    for raw in args.turn or []:
        parts = raw.split(":", 4)
        if len(parts) != 5:
            raise ValueError(
                "--turn must be turn_id:proof_response:serving_gateway:streaming_manifest:depends_csv_or_-"
            )
        turn_id, proof_path, gateway_path, stream_path, depends_raw = parts
        turns.append(
            {
                "turn_id": turn_id,
                "depends_on_turn_ids": []
                if depends_raw == "-"
                else [item for item in depends_raw.split(",") if item],
                "proof_carrying_response": json.loads(
                    Path(proof_path).read_text(encoding="utf-8")
                ),
                "serving_gateway_report": json.loads(
                    Path(gateway_path).read_text(encoding="utf-8")
                ),
                "streaming_attribution_manifest": json.loads(
                    Path(stream_path).read_text(encoding="utf-8")
                ),
            }
        )
    return turns


def run_conversation_attribution_ledger(args: argparse.Namespace) -> int:
    turns = _conversation_turns_arg(args)
    ledger = make_conversation_attribution_ledger(
        conversation_id=args.conversation_id,
        session_state_id=args.session_state_id,
        turns=turns,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(ledger, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": ledger["summary"]["status"],
            "output": args.output,
            "conversation_ledger_hash": ledger["conversation_ledger_hash"],
            "turn_count": ledger["summary"]["turn_count"],
            "unique_source_obligation_count": ledger["summary"][
                "unique_source_obligation_count"
            ],
            "passed_check_count": ledger["summary"]["passed_check_count"],
            "check_count": ledger["summary"]["check_count"],
        }
    else:
        result = ledger
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if ledger["summary"]["status"] == "continued" else 1


def run_verify_conversation_attribution_ledger(args: argparse.Namespace) -> int:
    ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    errors = verify_conversation_attribution_ledger(
        ledger,
        signing_secret=args.signing_secret,
    )
    result = {
        "ledger": args.ledger,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "conversation_ledger_hash": ledger.get("conversation_ledger_hash", ""),
        "summary": ledger.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_agent_tool_attribution_ledger(args: argparse.Namespace) -> int:
    proof_response = json.loads(Path(args.proof_response).read_text(encoding="utf-8"))
    trace_exchange = json.loads(Path(args.trace_exchange).read_text(encoding="utf-8"))
    conversation_ledger = json.loads(
        Path(args.conversation_attribution_ledger).read_text(encoding="utf-8")
    )
    ledger = make_agent_tool_attribution_ledger(
        proof_carrying_response=proof_response,
        trace_exchange=trace_exchange,
        conversation_attribution_ledger=conversation_ledger,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(ledger, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": ledger["summary"]["status"],
            "output": args.output,
            "tool_ledger_hash": ledger["tool_ledger_hash"],
            "tool_call_count": ledger["summary"]["tool_call_count"],
            "visible_source_count": ledger["summary"]["visible_source_count"],
            "claim_count": ledger["summary"]["claim_count"],
            "passed_check_count": ledger["summary"]["passed_check_count"],
            "check_count": ledger["summary"]["check_count"],
        }
    else:
        result = ledger
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if ledger["summary"]["status"] == "bound" else 1


def run_verify_agent_tool_attribution_ledger(args: argparse.Namespace) -> int:
    ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    errors = verify_agent_tool_attribution_ledger(
        ledger,
        signing_secret=args.signing_secret,
    )
    result = {
        "ledger": args.ledger,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "tool_ledger_hash": ledger.get("tool_ledger_hash", ""),
        "summary": ledger.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_match_text(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    matches = [match.to_dict() for match in engine.match_text(args.output, limit=args.limit)]
    print(json.dumps({"matches": matches}, indent=2, sort_keys=True))
    return 0


def run_value_training(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    prompts = args.prompt or None
    values = engine.estimate_training_values(prompts)
    print(json.dumps({"training_value_priors": values}, indent=2, sort_keys=True))
    return 0


def run_evaluate_grounding(args: argparse.Namespace) -> int:
    engine, event = _event_from_args(args)
    audit_errors = engine.audit_event(event)
    quality = evaluate_event_grounding_quality(event)
    result = {
        "event_id": event.event_id,
        "event_hash": event.event_hash,
        "grounding_report": event.grounding_report,
        "grounding_quality": quality,
        "audit_errors": audit_errors,
    }
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if audit_errors or quality.get("verdict") == "failed" else 0


def run_attribution_gap(args: argparse.Namespace) -> int:
    engine, event = _event_from_args(args)
    audit_errors = engine.audit_event(event)
    report = evaluate_event_attribution_gap(event)
    result = {
        "event_id": event.event_id,
        "event_hash": event.event_hash,
        "attribution_gap": report,
        "audit_errors": audit_errors,
    }
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if audit_errors or report.get("verdict") == "open_gap" else 0


def _event_from_args(args: argparse.Namespace) -> tuple[RoyaltyDrivenLLM, UsageEvent]:
    engine = _engine_from_args(args)
    if getattr(args, "output", None):
        event = engine.attribute_text(
            args.prompt,
            args.output,
            gross_revenue=Decimal(args.gross_revenue),
        )
    else:
        event = engine.generate(args.prompt, gross_revenue=Decimal(args.gross_revenue))
    return engine, event


def run_receipt(args: argparse.Namespace) -> int:
    engine, event = _event_from_args(args)
    errors = engine.audit_event(event)
    if errors:
        print(json.dumps({"audit_errors": errors}, indent=2, sort_keys=True))
        return 1

    receipt = make_attribution_receipt(
        event,
        issuer=args.issuer,
        model_id=args.model_id,
        model_version=args.model_version,
        route_id=args.route_id,
        signing_secret=args.signing_secret,
    )

    result: dict[str, object] = {"receipt": receipt}
    if args.log:
        log = TransparencyLog.read_json(args.log)
        entry = log.append(receipt)
        proof = log.proof_for(receipt["receipt_hash"])
        log.write_json(args.log)
        result["transparency_entry"] = entry
        result["transparency_proof"] = proof
        if args.proof:
            Path(args.proof).parent.mkdir(parents=True, exist_ok=True)
            Path(args.proof).write_text(
                json.dumps(proof, indent=2, sort_keys=True),
                encoding="utf-8",
            )

    if args.receipt:
        Path(args.receipt).parent.mkdir(parents=True, exist_ok=True)
        Path(args.receipt).write_text(
            json.dumps(receipt, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    if args.ledger:
        ledger = RoyaltyLedger()
        ledger.record(event)
        ledger.write_json(args.ledger)
    if args.public_receipt:
        Path(args.public_receipt).parent.mkdir(parents=True, exist_ok=True)
        Path(args.public_receipt).write_text(
            json.dumps(public_receipt(receipt), indent=2, sort_keys=True),
            encoding="utf-8",
        )

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_verify_receipt(args: argparse.Namespace) -> int:
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    errors = verify_receipt(receipt, signing_secret=args.signing_secret)
    proof_status = None
    if args.proof:
        proof = json.loads(Path(args.proof).read_text(encoding="utf-8"))
        proof_status = verify_inclusion(proof)
        if proof["leaf_hash"] != receipt["receipt_hash"]:
            errors.append("proof leaf hash does not match receipt")
        if not proof_status:
            errors.append("transparency inclusion proof is invalid")
    if args.log:
        log = TransparencyLog.read_json(args.log)
        receipt_hashes = [entry["receipt_hash"] for entry in log.entries]
        if receipt["receipt_hash"] not in receipt_hashes:
            errors.append("receipt hash not found in transparency log")

    result = {
        "receipt": args.receipt,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "proof_verified": proof_status,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_disclose(args: argparse.Namespace) -> int:
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    package = make_selective_disclosure_package(
        receipt,
        disclose_paths=args.disclose_path,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(package, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": "ok",
            "output": args.output,
            "receipt_hash": package["receipt_hash"],
            "payload_disclosure_root": package["payload_disclosure_root"],
            "summary": package["summary"],
        }
    else:
        result = package
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_verify_disclosure(args: argparse.Namespace) -> int:
    package = json.loads(Path(args.package).read_text(encoding="utf-8"))
    receipt = (
        json.loads(Path(args.receipt).read_text(encoding="utf-8"))
        if args.receipt
        else None
    )
    errors = verify_selective_disclosure_package(
        package,
        receipt,
        signing_secret=args.signing_secret,
    )
    result = {
        "package": args.package,
        "receipt": args.receipt,
        "status": "ok" if not errors else "failed",
        "errors": errors,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_trace(args: argparse.Namespace) -> int:
    receipt = None
    if args.receipt:
        receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
        trace = make_trace_exchange(
            receipt=receipt,
            provider_name=args.provider_name,
        )
    else:
        if not args.prompt:
            raise SystemExit("trace requires a prompt unless --receipt is provided")
        engine = _engine_from_args(args)
        if args.external_output:
            event = engine.attribute_text(
                args.prompt,
                args.external_output,
                gross_revenue=Decimal(args.gross_revenue),
            )
        else:
            event = engine.generate(
                args.prompt,
                gross_revenue=Decimal(args.gross_revenue),
            )
        errors = engine.audit_event(event)
        if errors:
            print(json.dumps({"audit_errors": errors}, indent=2, sort_keys=True))
            return 1
        trace_receipt = make_attribution_receipt(
            event,
            issuer=args.issuer,
            model_id=args.model_id,
            model_version=args.model_version,
            route_id=args.route_id,
            signing_secret=args.signing_secret,
        )
        trace = make_trace_exchange(
            event,
            receipt=trace_receipt,
            provider_name=args.provider_name,
        )
        if args.generated_receipt:
            Path(args.generated_receipt).parent.mkdir(parents=True, exist_ok=True)
            Path(args.generated_receipt).write_text(
                json.dumps(trace_receipt, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        if args.ledger:
            ledger = RoyaltyLedger()
            ledger.record(event)
            ledger.write_json(args.ledger)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(trace, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": "ok",
            "output": args.output,
            "trace_hash": trace["trace_hash"],
            "event_id": trace["event_id"],
            "summary": trace["summary"],
        }
    else:
        result = trace
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_verify_trace(args: argparse.Namespace) -> int:
    trace = json.loads(Path(args.trace).read_text(encoding="utf-8"))
    receipt = (
        json.loads(Path(args.receipt).read_text(encoding="utf-8"))
        if args.receipt
        else None
    )
    event_id = args.event_id or trace.get("event_id")
    event = _event_from_ledger(args.ledger, event_id) if args.ledger else None
    errors = verify_trace_exchange(trace, event=event, receipt=receipt)
    result = {
        "trace": args.trace,
        "receipt": args.receipt,
        "ledger": args.ledger,
        "status": "ok" if not errors else "failed",
        "errors": errors,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def _load_json_many(paths: list[str] | None) -> list[dict[str, object]]:
    return [
        json.loads(Path(path).read_text(encoding="utf-8"))
        for path in (paths or [])
    ]


def _load_assurance_artifacts(specs: list[str] | None) -> list[tuple[str, str, dict[str, object]]]:
    artifacts: list[tuple[str, str, dict[str, object]]] = []
    for spec in specs or []:
        parts = spec.split(":", 2)
        if len(parts) != 3:
            raise SystemExit(
                "--artifact must use name:type:path, for example certification:certification_report:artifacts/certification_report.json"
            )
        name, artifact_type, path = parts
        artifacts.append(
            (
                name,
                artifact_type,
                json.loads(Path(path).read_text(encoding="utf-8")),
            )
        )
    return artifacts


def _load_dependency_edges(specs: list[str] | None) -> list[dict[str, str]] | None:
    if not specs:
        return None
    edges: list[dict[str, str]] = []
    for spec in specs:
        if spec.endswith(".json"):
            payload = json.loads(Path(spec).read_text(encoding="utf-8"))
            if isinstance(payload, dict) and isinstance(payload.get("dependencies"), list):
                payload = payload["dependencies"]
            if not isinstance(payload, list):
                raise SystemExit(
                    "--dependency JSON must be an array or object with dependencies"
                )
            for item in payload:
                if not isinstance(item, dict):
                    raise SystemExit("--dependency JSON rows must be objects")
                edges.append(
                    {
                        "dependent": str(item.get("dependent", "")),
                        "dependency": str(item.get("dependency", "")),
                        "edge_class": str(item.get("edge_class", "replay_dependency")),
                        "reason": str(item.get("reason", "declared_dependency")),
                    }
                )
            continue
        parts = spec.split(":", 3)
        if len(parts) < 2:
            raise SystemExit(
                "--dependency must use dependent:dependency[:edge_class[:reason]] or point to JSON"
            )
        edges.append(
            {
                "dependent": parts[0],
                "dependency": parts[1],
                "edge_class": parts[2] if len(parts) >= 3 and parts[2] else "replay_dependency",
                "reason": parts[3] if len(parts) >= 4 and parts[3] else "declared_dependency",
            }
        )
    return edges


def run_statement(args: argparse.Namespace) -> int:
    ledger_data = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    statement = make_royalty_statement(
        ledger_data,
        issuer=args.issuer,
        period_start=args.period_start,
        period_end=args.period_end,
        receipts=_load_json_many(args.receipt),
        traces=_load_json_many(args.trace),
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(statement, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": "ok",
            "output": args.output,
            **statement_summary(statement),
        }
    else:
        result = statement
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_verify_statement(args: argparse.Namespace) -> int:
    ledger_data = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    statement = json.loads(Path(args.statement).read_text(encoding="utf-8"))
    errors = verify_royalty_statement(
        ledger_data,
        statement,
        receipts=_load_json_many(args.receipt),
        traces=_load_json_many(args.trace),
        signing_secret=args.signing_secret,
    )
    result = {
        "statement": args.statement,
        "ledger": args.ledger,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "summary": statement.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def _load_revenue_sources(path: str) -> list[dict[str, object]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("revenue_sources"), list):
        return payload["revenue_sources"]
    raise SystemExit(
        "--revenue-sources must point to a JSON array or object with revenue_sources"
    )


def _load_finance_records(path: str) -> list[dict[str, object]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("finance_records"), list):
        return payload["finance_records"]
    raise SystemExit(
        "--finance-records must point to a JSON array or object with finance_records"
    )


def _allocation_policy_from_args(args: argparse.Namespace) -> dict[str, object]:
    policy: dict[str, object] = {
        "policy_id": args.allocation_policy_id,
        "allocation_mode": args.allocation_mode,
        "currency": args.currency,
    }
    if args.allocation_policy:
        policy.update(json.loads(Path(args.allocation_policy).read_text(encoding="utf-8")))
    return policy


def run_revenue_allocation_report(args: argparse.Namespace) -> int:
    ledger_data = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    report = make_revenue_allocation_report(
        ledger_data,
        revenue_sources=_load_revenue_sources(args.revenue_sources),
        receipts=_load_json_many(args.receipt),
        allocation_policy=_allocation_policy_from_args(args),
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "report_hash": report["report_hash"],
            "revenue_source_count": report["summary"]["revenue_source_count"],
            "event_count": report["summary"]["event_count"],
            "gross_revenue_total": report["summary"]["gross_revenue_total"],
            "creator_pool_total": report["summary"]["creator_pool_total"],
            "allocation_mode": report["summary"]["allocation_mode"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_revenue_allocation_report(args: argparse.Namespace) -> int:
    ledger_data = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_revenue_allocation_report(
        report,
        ledger_data,
        revenue_sources=_load_revenue_sources(args.revenue_sources),
        receipts=_load_json_many(args.receipt),
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "ledger": args.ledger,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "report_hash": report.get("report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_finance_ledger_attestation(args: argparse.Namespace) -> int:
    revenue_allocation_report = json.loads(
        Path(args.revenue_allocation_report).read_text(encoding="utf-8")
    )
    attestation = make_finance_ledger_attestation(
        _load_finance_records(args.finance_records),
        revenue_allocation_report=revenue_allocation_report,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(attestation, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": attestation["summary"]["status"],
            "output": args.output,
            "attestation_hash": attestation["attestation_hash"],
            "finance_record_count": attestation["summary"]["finance_record_count"],
            "revenue_source_count": attestation["summary"]["revenue_source_count"],
            "finance_gross_revenue_total": attestation["summary"][
                "finance_gross_revenue_total"
            ],
        }
    else:
        result = attestation
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if attestation["summary"]["status"] == "ready" else 1


def run_verify_finance_ledger_attestation(args: argparse.Namespace) -> int:
    attestation = json.loads(Path(args.attestation).read_text(encoding="utf-8"))
    revenue_allocation_report = json.loads(
        Path(args.revenue_allocation_report).read_text(encoding="utf-8")
    )
    errors = verify_finance_ledger_attestation(
        attestation,
        finance_records=_load_finance_records(args.finance_records),
        revenue_allocation_report=revenue_allocation_report,
        signing_secret=args.signing_secret,
    )
    result = {
        "attestation": args.attestation,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "attestation_hash": attestation.get("attestation_hash", ""),
        "summary": attestation.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def _chunk_from_args(engine: RoyaltyDrivenLLM, args: argparse.Namespace):
    chunk_id = args.chunk_id
    if not chunk_id and args.work_id:
        chunk_id = f"{args.work_id}:c1"
    if not chunk_id:
        raise SystemExit("challenge requires --chunk-id or --work-id")
    chunk = engine.chunk_by_id.get(chunk_id)
    if not chunk:
        raise SystemExit(f"chunk {chunk_id} not found")
    return chunk


def run_challenge(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    event = _event_from_ledger(args.ledger, args.event_id)
    chunk = _chunk_from_args(engine, args)
    statement = (
        json.loads(Path(args.statement).read_text(encoding="utf-8"))
        if args.statement
        else None
    )
    report = make_attribution_challenge(
        event,
        chunk,
        issuer=args.issuer,
        claimant_id=args.claimant_id,
        reason=args.reason,
        statement=statement,
        accept_threshold=args.accept_threshold,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": "ok",
            "output": args.output,
            "challenge_id": report["challenge_id"],
            "report_hash": report["report_hash"],
            "verdict": report["evaluation"]["verdict"],
            "remedy": report["remedy"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_verify_challenge(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    event = _event_from_ledger(args.ledger, args.event_id)
    chunk = _chunk_from_args(engine, args)
    report = json.loads(Path(args.challenge).read_text(encoding="utf-8"))
    statement = (
        json.loads(Path(args.statement).read_text(encoding="utf-8"))
        if args.statement
        else None
    )
    errors = verify_attribution_challenge(
        event,
        chunk,
        report,
        statement=statement,
        signing_secret=args.signing_secret,
    )
    result = {
        "challenge": args.challenge,
        "ledger": args.ledger,
        "event_id": args.event_id,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "verdict": report.get("evaluation", {}).get("verdict", ""),
        "remedy": report.get("remedy", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_provider_card(args: argparse.Namespace) -> int:
    ledger_data = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    certification_report = (
        json.loads(Path(args.certification_report).read_text(encoding="utf-8"))
        if args.certification_report
        else None
    )
    card = make_provider_attribution_card(
        ledger_data,
        certification_report=certification_report,
        issuer=args.issuer,
        provider=args.provider,
        model_id=args.model_id,
        model_version=args.model_version,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(card, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": "ok",
            "output": args.output,
            "card_hash": card["card_hash"],
            "highest_level": card["certification"].get("highest_level", ""),
            "accounted_access_ratio": card["coverage"]["accounted_access_ratio"],
        }
    else:
        result = card
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_verify_provider_card(args: argparse.Namespace) -> int:
    ledger_data = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    card = json.loads(Path(args.card).read_text(encoding="utf-8"))
    certification_report = (
        json.loads(Path(args.certification_report).read_text(encoding="utf-8"))
        if args.certification_report
        else None
    )
    errors = verify_provider_attribution_card(
        ledger_data,
        card,
        certification_report=certification_report,
        signing_secret=args.signing_secret,
    )
    result = {
        "card": args.card,
        "ledger": args.ledger,
        "certification_report": args.certification_report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "card_hash": card.get("card_hash", ""),
        "coverage": card.get("coverage", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_training_summary(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    certification_report = (
        json.loads(Path(args.certification_report).read_text(encoding="utf-8"))
        if args.certification_report
        else None
    )
    provider_card = (
        json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
        if args.provider_card
        else None
    )
    summary = make_training_content_summary(
        engine,
        certification_report=certification_report,
        provider_card=provider_card,
        issuer=args.issuer,
        provider=args.provider,
        model_id=args.model_id,
        model_version=args.model_version,
        training_stage=args.training_stage,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": "ok",
            "output": args.output,
            "summary_hash": summary["summary_hash"],
            "training_rights_coverage": summary["training_content"]["aggregate"][
                "training_rights_coverage"
            ],
            "work_count": summary["training_content"]["aggregate"]["work_count"],
        }
    else:
        result = summary
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_verify_training_summary(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    summary = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    certification_report = (
        json.loads(Path(args.certification_report).read_text(encoding="utf-8"))
        if args.certification_report
        else None
    )
    provider_card = (
        json.loads(Path(args.provider_card).read_text(encoding="utf-8"))
        if args.provider_card
        else None
    )
    errors = verify_training_content_summary(
        engine,
        summary,
        certification_report=certification_report,
        provider_card=provider_card,
        signing_secret=args.signing_secret,
    )
    result = {
        "summary": args.summary,
        "certification_report": args.certification_report,
        "provider_card": args.provider_card,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "summary_hash": summary.get("summary_hash", ""),
        "aggregate": summary.get("training_content", {}).get("aggregate", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_assurance_bundle(args: argparse.Namespace) -> int:
    artifacts = _load_assurance_artifacts(args.artifact)
    bundle = make_assurance_bundle(
        artifacts,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(bundle, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": "ok",
            "output": args.output,
            "bundle_hash": bundle["bundle_hash"],
            "artifact_count": bundle["summary"]["artifact_count"],
            "root": bundle["summary"]["root"],
        }
    else:
        result = bundle
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_verify_assurance_bundle(args: argparse.Namespace) -> int:
    artifacts = _load_assurance_artifacts(args.artifact)
    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    errors = verify_assurance_bundle(
        artifacts,
        bundle,
        signing_secret=args.signing_secret,
    )
    result = {
        "bundle": args.bundle,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "bundle_hash": bundle.get("bundle_hash", ""),
        "summary": bundle.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_proof_dependency_graph(args: argparse.Namespace) -> int:
    artifacts = _load_assurance_artifacts(args.artifact)
    graph = make_proof_dependency_graph(
        artifacts,
        dependencies=_load_dependency_edges(args.dependency),
        include_publication_edges=not args.no_publication_edges,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(graph, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": graph["summary"]["status"],
            "output": args.output,
            "graph_hash": graph["graph_hash"],
            "artifact_count": graph["summary"]["artifact_count"],
            "replay_dependency_count": graph["summary"]["replay_dependency_count"],
            "publication_commitment_count": graph["summary"][
                "publication_commitment_count"
            ],
            "cycle_node_count": graph["summary"]["cycle_node_count"],
        }
    else:
        result = graph
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if graph["summary"]["status"] == "ready" else 1


def run_verify_proof_dependency_graph(args: argparse.Namespace) -> int:
    artifacts = _load_assurance_artifacts(args.artifact)
    graph = json.loads(Path(args.graph).read_text(encoding="utf-8"))
    errors = verify_proof_dependency_graph(
        graph,
        artifacts,
        dependencies=_load_dependency_edges(args.dependency),
        include_publication_edges=not args.no_publication_edges,
        signing_secret=args.signing_secret,
    )
    result = {
        "graph": args.graph,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "graph_hash": graph.get("graph_hash", ""),
        "summary": graph.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_evidence_region_binding_report(args: argparse.Namespace) -> int:
    binding_input = load_evidence_region_binding_input(
        args.evidence_region_binding_input
    )
    report = make_evidence_region_binding_report(
        binding_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "binding_report_hash": report["binding_report_hash"],
            "source_region_count": report["summary"]["source_region_count"],
            "claim_region_link_count": report["summary"]["claim_region_link_count"],
            "rendered_claim_region_coverage": report["summary"][
                "rendered_claim_region_coverage"
            ],
            "public_location_binding_supported": report["summary"][
                "public_location_binding_supported"
            ],
            "anti_wrong_region_controls_passed": report["summary"][
                "anti_wrong_region_controls_passed"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_evidence_region_binding_report(args: argparse.Namespace) -> int:
    binding_input = load_evidence_region_binding_input(
        args.evidence_region_binding_input
    )
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_evidence_region_binding_report(
        report,
        binding_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "evidence_region_binding_input": args.evidence_region_binding_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "binding_report_hash": report.get("binding_report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_source_access_lease_report(args: argparse.Namespace) -> int:
    lease_input = load_source_access_lease_input(args.source_access_lease_input)
    report = make_source_access_lease_report(
        lease_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "lease_report_hash": report["lease_report_hash"],
            "source_usage_count": report["summary"]["source_usage_count"],
            "lease_count": report["summary"]["lease_count"],
            "access_log_count": report["summary"]["access_log_count"],
            "covered_direct_source_count": report["summary"][
                "covered_direct_source_count"
            ],
            "creator_side_access_audit_supported": report["summary"][
                "creator_side_access_audit_supported"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_source_access_lease_report(args: argparse.Namespace) -> int:
    lease_input = load_source_access_lease_input(args.source_access_lease_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_source_access_lease_report(
        report,
        lease_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "source_access_lease_input": args.source_access_lease_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "lease_report_hash": report.get("lease_report_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_content_protocol_ingestion_report(args: argparse.Namespace) -> int:
    protocol_input = load_content_protocol_ingestion_input(
        args.content_protocol_ingestion_input
    )
    report = make_content_protocol_ingestion_report(
        protocol_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "protocol_ingestion_report_hash": report[
                "protocol_ingestion_report_hash"
            ],
            "protocol_record_count": report["summary"]["protocol_record_count"],
            "supported_protocols": report["summary"]["supported_protocols"],
            "covered_direct_source_count": report["summary"][
                "covered_direct_source_count"
            ],
            "rsl_comp_scp_bridge_supported": report["summary"][
                "rsl_comp_scp_bridge_supported"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_content_protocol_ingestion_report(args: argparse.Namespace) -> int:
    protocol_input = load_content_protocol_ingestion_input(
        args.content_protocol_ingestion_input
    )
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_content_protocol_ingestion_report(
        report,
        protocol_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "content_protocol_ingestion_input": args.content_protocol_ingestion_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "protocol_ingestion_report_hash": report.get(
            "protocol_ingestion_report_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_citation_reliance_receipt(args: argparse.Namespace) -> int:
    receipt_input = load_citation_reliance_input(args.citation_reliance_input)
    receipt = make_citation_reliance_receipt(
        receipt_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(receipt, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": receipt["summary"]["status"],
            "output": args.output,
            "citation_reliance_receipt_hash": receipt[
                "citation_reliance_receipt_hash"
            ],
            "visible_source_count": receipt["summary"]["visible_source_count"],
            "faithfully_covered_source_count": receipt["summary"][
                "faithfully_covered_source_count"
            ],
            "faithfully_covered_claim_count": receipt["summary"][
                "faithfully_covered_claim_count"
            ],
            "post_hoc_citation_blocked": receipt["summary"][
                "post_hoc_citation_blocked"
            ],
        }
    else:
        result = receipt
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if receipt["summary"]["status"] == "ready" else 1


def run_verify_citation_reliance_receipt(args: argparse.Namespace) -> int:
    receipt_input = load_citation_reliance_input(args.citation_reliance_input)
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    errors = verify_citation_reliance_receipt(
        receipt,
        receipt_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "receipt": args.receipt,
        "citation_reliance_input": args.citation_reliance_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "citation_reliance_receipt_hash": receipt.get(
            "citation_reliance_receipt_hash", ""
        ),
        "summary": receipt.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_license_transaction_receipt(args: argparse.Namespace) -> int:
    receipt_input = load_license_transaction_input(args.license_transaction_input)
    receipt = make_license_transaction_receipt(
        receipt_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(receipt, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": receipt["summary"]["status"],
            "output": args.output,
            "license_transaction_receipt_hash": receipt[
                "license_transaction_receipt_hash"
            ],
            "license_transaction_count": receipt["summary"][
                "license_transaction_count"
            ],
            "covered_direct_source_count": receipt["summary"][
                "covered_direct_source_count"
            ],
            "license_ledger_inclusion_supported": receipt["summary"][
                "license_ledger_inclusion_supported"
            ],
        }
    else:
        result = receipt
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if receipt["summary"]["status"] == "ready" else 1


def run_verify_license_transaction_receipt(args: argparse.Namespace) -> int:
    receipt_input = load_license_transaction_input(args.license_transaction_input)
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    errors = verify_license_transaction_receipt(
        receipt,
        receipt_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "receipt": args.receipt,
        "license_transaction_input": args.license_transaction_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "license_transaction_receipt_hash": receipt.get(
            "license_transaction_receipt_hash", ""
        ),
        "summary": receipt.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_grounded_source_footer(args: argparse.Namespace) -> int:
    receipt_input = load_grounded_source_footer_input(args.grounded_source_footer_input)
    receipt = make_grounded_source_footer(
        receipt_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(receipt, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": receipt["summary"]["status"],
            "output": args.output,
            "grounded_source_footer_hash": receipt["grounded_source_footer_hash"],
            "visible_source_count": receipt["summary"]["visible_source_count"],
            "claim_row_count": receipt["summary"]["claim_row_count"],
            "verified_source_count": receipt["summary"]["verified_source_count"],
        }
    else:
        result = receipt
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if receipt["summary"]["status"] == "ready" else 1


def run_verify_grounded_source_footer(args: argparse.Namespace) -> int:
    receipt_input = load_grounded_source_footer_input(args.grounded_source_footer_input)
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    errors = verify_grounded_source_footer(
        receipt,
        receipt_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "receipt": args.receipt,
        "grounded_source_footer_input": args.grounded_source_footer_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "grounded_source_footer_hash": receipt.get(
            "grounded_source_footer_hash", ""
        ),
        "summary": receipt.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_source_footer_delivery(args: argparse.Namespace) -> int:
    receipt_input = load_source_footer_delivery_input(args.source_footer_delivery_input)
    receipt = make_source_footer_delivery_receipt(
        receipt_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(receipt, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": receipt["summary"]["status"],
            "output": args.output,
            "source_footer_delivery_hash": receipt["source_footer_delivery_hash"],
            "visible_source_count": receipt["summary"]["visible_source_count"],
            "delivered_source_count": receipt["summary"]["delivered_source_count"],
            "claim_span_count": receipt["summary"]["claim_span_count"],
        }
    else:
        result = receipt
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if receipt["summary"]["status"] == "ready" else 1


def run_verify_source_footer_delivery(args: argparse.Namespace) -> int:
    receipt_input = load_source_footer_delivery_input(args.source_footer_delivery_input)
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    errors = verify_source_footer_delivery_receipt(
        receipt,
        receipt_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "receipt": args.receipt,
        "source_footer_delivery_input": args.source_footer_delivery_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "source_footer_delivery_hash": receipt.get(
            "source_footer_delivery_hash", ""
        ),
        "summary": receipt.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_foundation_api_profile(args: argparse.Namespace) -> int:
    profile_input = load_foundation_api_profile_input(args.foundation_api_profile_input)
    profile = make_foundation_api_profile(
        profile_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(profile, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": profile["summary"]["status"],
            "output": args.output,
            "foundation_profile_hash": profile["foundation_profile_hash"],
            "minimum_source_level": profile["summary"]["minimum_source_level"],
            "required_header_count": profile["summary"]["required_header_count"],
        }
    else:
        result = profile
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if profile["summary"]["status"] == "ready" else 1


def run_verify_foundation_api_profile(args: argparse.Namespace) -> int:
    profile_input = load_foundation_api_profile_input(args.foundation_api_profile_input)
    profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    errors = verify_foundation_api_profile(
        profile,
        profile_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "profile": args.profile,
        "foundation_api_profile_input": args.foundation_api_profile_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "foundation_profile_hash": profile.get("foundation_profile_hash", ""),
        "summary": profile.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_client_attribution_enforcement(args: argparse.Namespace) -> int:
    receipt_input = load_client_attribution_input(args.client_attribution_input)
    receipt = make_client_attribution_enforcement_receipt(
        receipt_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(receipt, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": receipt["summary"]["status"],
            "output": args.output,
            "client_enforcement_hash": receipt["client_enforcement_hash"],
            "decision": receipt["client_decision"]["decision"],
            "failed_check_count": receipt["summary"]["failed_check_count"],
        }
    else:
        result = receipt
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if receipt["summary"]["status"] == "ready" else 1


def run_verify_client_attribution_enforcement(args: argparse.Namespace) -> int:
    receipt_input = load_client_attribution_input(args.client_attribution_input)
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    errors = verify_client_attribution_enforcement_receipt(
        receipt,
        receipt_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "receipt": args.receipt,
        "client_attribution_input": args.client_attribution_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "client_enforcement_hash": receipt.get("client_enforcement_hash", ""),
        "summary": receipt.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_persistent_memory_provenance(args: argparse.Namespace) -> int:
    receipt_input = load_persistent_memory_provenance_input(
        args.persistent_memory_input
    )
    receipt = make_persistent_memory_provenance_receipt(
        receipt_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(receipt, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": receipt["summary"]["status"],
            "output": args.output,
            "persistent_memory_provenance_hash": receipt[
                "persistent_memory_provenance_hash"
            ],
            "memory_entry_count": receipt["summary"]["memory_entry_count"],
            "memory_read_count": receipt["summary"]["memory_read_count"],
            "failed_check_count": receipt["summary"]["failed_check_count"],
        }
    else:
        result = receipt
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if receipt["summary"]["status"] == "ready" else 1


def run_verify_persistent_memory_provenance(args: argparse.Namespace) -> int:
    receipt_input = load_persistent_memory_provenance_input(
        args.persistent_memory_input
    )
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    errors = verify_persistent_memory_provenance_receipt(
        receipt,
        receipt_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "receipt": args.receipt,
        "persistent_memory_input": args.persistent_memory_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "persistent_memory_provenance_hash": receipt.get(
            "persistent_memory_provenance_hash", ""
        ),
        "summary": receipt.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_private_reasoning_attribution(args: argparse.Namespace) -> int:
    receipt_input = load_private_reasoning_attribution_input(
        args.private_reasoning_input
    )
    receipt = make_private_reasoning_attribution_receipt(
        receipt_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(receipt, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": receipt["summary"]["status"],
            "output": args.output,
            "private_reasoning_attribution_hash": receipt[
                "private_reasoning_attribution_hash"
            ],
            "reasoning_step_count": receipt["summary"]["reasoning_step_count"],
            "source_label_count": receipt["summary"]["source_label_count"],
            "failed_check_count": receipt["summary"]["failed_check_count"],
        }
    else:
        result = receipt
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if receipt["summary"]["status"] == "ready" else 1


def run_verify_private_reasoning_attribution(args: argparse.Namespace) -> int:
    receipt_input = load_private_reasoning_attribution_input(
        args.private_reasoning_input
    )
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    errors = verify_private_reasoning_attribution_receipt(
        receipt,
        receipt_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "receipt": args.receipt,
        "private_reasoning_input": args.private_reasoning_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "private_reasoning_attribution_hash": receipt.get(
            "private_reasoning_attribution_hash", ""
        ),
        "summary": receipt.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_post_training_signal_provenance(args: argparse.Namespace) -> int:
    receipt_input = load_post_training_signal_input(args.post_training_signal_input)
    receipt = make_post_training_signal_provenance_receipt(
        receipt_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(receipt, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": receipt["summary"]["status"],
            "output": args.output,
            "post_training_signal_provenance_hash": receipt[
                "post_training_signal_provenance_hash"
            ],
            "signal_count": receipt["summary"]["signal_count"],
            "source_label_count": receipt["summary"]["source_label_count"],
            "failed_check_count": receipt["summary"]["failed_check_count"],
        }
    else:
        result = receipt
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if receipt["summary"]["status"] == "ready" else 1


def run_verify_post_training_signal_provenance(args: argparse.Namespace) -> int:
    receipt_input = load_post_training_signal_input(args.post_training_signal_input)
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    errors = verify_post_training_signal_provenance_receipt(
        receipt,
        receipt_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "receipt": args.receipt,
        "post_training_signal_input": args.post_training_signal_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "post_training_signal_provenance_hash": receipt.get(
            "post_training_signal_provenance_hash", ""
        ),
        "summary": receipt.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_attribution_bom(args: argparse.Namespace) -> int:
    bom_input = load_attribution_bom_input(args.attribution_bom_input)
    bom = make_attribution_bill_of_materials(
        bom_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(bom, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": bom["summary"]["status"],
            "output": args.output,
            "attribution_bom_hash": bom["attribution_bom_hash"],
            "component_count": bom["summary"]["component_count"],
            "source_component_count": bom["summary"]["source_component_count"],
            "proof_artifact_component_count": bom["summary"][
                "proof_artifact_component_count"
            ],
            "failed_check_count": bom["summary"]["failed_check_count"],
        }
    else:
        result = bom
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if bom["summary"]["status"] == "ready" else 1


def run_verify_attribution_bom(args: argparse.Namespace) -> int:
    bom_input = load_attribution_bom_input(args.attribution_bom_input)
    bom = json.loads(Path(args.bom).read_text(encoding="utf-8"))
    errors = verify_attribution_bill_of_materials(
        bom,
        bom_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "bom": args.bom,
        "attribution_bom_input": args.attribution_bom_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "attribution_bom_hash": bom.get("attribution_bom_hash", ""),
        "summary": bom.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_creator_attribution_audit_index(args: argparse.Namespace) -> int:
    audit_input = load_creator_attribution_audit_index_input(args.audit_input)
    index = make_creator_attribution_audit_index(
        audit_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(index, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": index["summary"]["status"],
            "output": args.output,
            "creator_attribution_audit_index_hash": index[
                "creator_attribution_audit_index_hash"
            ],
            "creator_work_count": index["summary"]["creator_work_count"],
            "surface_row_count": index["summary"]["surface_row_count"],
            "failed_check_count": index["summary"]["failed_check_count"],
        }
    else:
        result = index
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if index["summary"]["status"] == "ready" else 1


def run_verify_creator_attribution_audit_index(args: argparse.Namespace) -> int:
    audit_input = load_creator_attribution_audit_index_input(args.audit_input)
    index = json.loads(Path(args.index).read_text(encoding="utf-8"))
    errors = verify_creator_attribution_audit_index(
        index,
        audit_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "index": args.index,
        "audit_input": args.audit_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "creator_attribution_audit_index_hash": index.get(
            "creator_attribution_audit_index_hash", ""
        ),
        "summary": index.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_creator_attribution_audit_federation(args: argparse.Namespace) -> int:
    federation_input = load_creator_attribution_audit_federation_input(
        args.federation_input
    )
    report = make_creator_attribution_audit_federation(
        federation_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "creator_attribution_audit_federation_hash": report[
                "creator_attribution_audit_federation_hash"
            ],
            "participant_count": report["summary"]["participant_count"],
            "provider_count": report["summary"]["provider_count"],
            "federated_surface_row_count": report["summary"][
                "federated_surface_row_count"
            ],
            "failed_check_count": report["summary"]["failed_check_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_creator_attribution_audit_federation(args: argparse.Namespace) -> int:
    federation_input = load_creator_attribution_audit_federation_input(
        args.federation_input
    )
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_creator_attribution_audit_federation(
        report,
        federation_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "federation_input": args.federation_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "creator_attribution_audit_federation_hash": report.get(
            "creator_attribution_audit_federation_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_creator_audit_federation_transparency_log(args: argparse.Namespace) -> int:
    federation_report = json.loads(Path(args.federation_report).read_text(encoding="utf-8"))
    existing_entries = None
    if args.existing_log:
        existing_log = json.loads(Path(args.existing_log).read_text(encoding="utf-8"))
        existing_entries = existing_log.get("entries", [])
    log = make_creator_audit_federation_transparency_log(
        federation_report,
        log_id=args.log_id,
        existing_entries=existing_entries,
        include_participant_indexes=not args.exclude_participant_indexes,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(log, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": "ok",
            "output": args.output,
            "root": log["root"],
            "tree_size": log["tree_size"],
            "entry_count": len(log.get("entries", [])),
        }
    else:
        result = log
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_creator_audit_federation_transparency(args: argparse.Namespace) -> int:
    federation_report = json.loads(Path(args.federation_report).read_text(encoding="utf-8"))
    report = make_creator_audit_federation_transparency_report(
        federation_report=federation_report,
        transparency_logs=_named_json_from_args(args.transparency_log),
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "creator_attribution_audit_federation_transparency_hash": report[
                "creator_attribution_audit_federation_transparency_hash"
            ],
            "subject_count": report["summary"]["subject_count"],
            "transparency_log_count": report["summary"]["transparency_log_count"],
            "split_view_conflict_count": report["summary"][
                "split_view_conflict_count"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_creator_audit_federation_transparency(args: argparse.Namespace) -> int:
    federation_report = json.loads(Path(args.federation_report).read_text(encoding="utf-8"))
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_creator_audit_federation_transparency_report(
        report,
        federation_report=federation_report,
        transparency_logs=_named_json_from_args(args.transparency_log),
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "federation_report": args.federation_report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "creator_attribution_audit_federation_transparency_hash": report.get(
            "creator_attribution_audit_federation_transparency_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_creator_audit_transparency_monitor(args: argparse.Namespace) -> int:
    monitor_query = json.loads(Path(args.monitor_query).read_text(encoding="utf-8"))
    previous_report = (
        json.loads(Path(args.previous_monitor).read_text(encoding="utf-8"))
        if args.previous_monitor
        else None
    )
    report = make_creator_audit_transparency_monitor_report(
        monitor_query=monitor_query,
        transparency_reports=_json_payloads_from_args(args.transparency_report),
        transparency_logs=_named_json_from_args(args.transparency_log),
        previous_report=previous_report,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "creator_audit_transparency_monitor_hash": report[
                "creator_audit_transparency_monitor_hash"
            ],
            "matching_observation_count": report["summary"][
                "matching_observation_count"
            ],
            "new_observation_count": report["summary"]["new_observation_count"],
            "conflict_count": report["summary"]["conflict_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_creator_audit_transparency_monitor(args: argparse.Namespace) -> int:
    monitor_query = json.loads(Path(args.monitor_query).read_text(encoding="utf-8"))
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    previous_report = (
        json.loads(Path(args.previous_monitor).read_text(encoding="utf-8"))
        if args.previous_monitor
        else None
    )
    errors = verify_creator_audit_transparency_monitor_report(
        report,
        monitor_query=monitor_query,
        transparency_reports=_json_payloads_from_args(args.transparency_report),
        transparency_logs=_named_json_from_args(args.transparency_log),
        previous_report=previous_report,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "monitor_query": args.monitor_query,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "creator_audit_transparency_monitor_hash": report.get(
            "creator_audit_transparency_monitor_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_creator_audit_private_watch(args: argparse.Namespace) -> int:
    watch_input = json.loads(Path(args.watch_input).read_text(encoding="utf-8"))
    monitor_report = json.loads(Path(args.monitor_report).read_text(encoding="utf-8"))
    report = make_creator_audit_private_watch_report(
        watch_input=watch_input,
        monitor_report=monitor_report,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "creator_audit_private_watch_hash": report[
                "creator_audit_private_watch_hash"
            ],
            "query_token_count": report["summary"]["query_token_count"],
            "observation_token_count": report["summary"][
                "observation_token_count"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_creator_audit_private_watch(args: argparse.Namespace) -> int:
    watch_input = json.loads(Path(args.watch_input).read_text(encoding="utf-8"))
    monitor_report = json.loads(Path(args.monitor_report).read_text(encoding="utf-8"))
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_creator_audit_private_watch_report(
        report,
        watch_input=watch_input,
        monitor_report=monitor_report,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "watch_input": args.watch_input,
        "monitor_report": args.monitor_report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "creator_audit_private_watch_hash": report.get(
            "creator_audit_private_watch_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_deep_research_citation_audit(args: argparse.Namespace) -> int:
    audit_input = load_deep_research_citation_audit_input(args.audit_input)
    report = make_deep_research_citation_audit_report(
        audit_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "deep_research_citation_audit_hash": report[
                "deep_research_citation_audit_hash"
            ],
            "citation_marker_count": report["summary"]["citation_marker_count"],
            "supported_claim_count": report["summary"]["supported_claim_count"],
            "verified_source_count": report["summary"]["verified_source_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_deep_research_citation_audit(args: argparse.Namespace) -> int:
    audit_input = load_deep_research_citation_audit_input(args.audit_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_deep_research_citation_audit_report(
        report,
        audit_input=audit_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "audit_input": args.audit_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "deep_research_citation_audit_hash": report.get(
            "deep_research_citation_audit_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_source_freshness_audit(args: argparse.Namespace) -> int:
    audit_input = load_source_freshness_audit_input(args.audit_input)
    report = make_source_freshness_audit_report(
        audit_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "source_freshness_audit_hash": report["source_freshness_audit_hash"],
            "dynamic_claim_count": report["summary"]["dynamic_claim_count"],
            "fresh_dynamic_claim_count": report["summary"][
                "fresh_dynamic_claim_count"
            ],
            "fresher_supported_candidate_count": report["summary"][
                "fresher_supported_candidate_count"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_source_freshness_audit(args: argparse.Namespace) -> int:
    audit_input = load_source_freshness_audit_input(args.audit_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_source_freshness_audit_report(
        report,
        audit_input=audit_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "audit_input": args.audit_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "source_freshness_audit_hash": report.get(
            "source_freshness_audit_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_royalty_abuse_audit(args: argparse.Namespace) -> int:
    audit_input = load_royalty_abuse_audit_input(args.audit_input)
    report = make_royalty_abuse_audit_report(
        audit_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "royalty_abuse_audit_hash": report["royalty_abuse_audit_hash"],
            "suspicious_source_count": report["summary"][
                "suspicious_source_count"
            ],
            "suspicious_creator_count": report["summary"][
                "suspicious_creator_count"
            ],
            "escrow_total": report["summary"]["escrow_total"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_royalty_abuse_audit(args: argparse.Namespace) -> int:
    audit_input = load_royalty_abuse_audit_input(args.audit_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_royalty_abuse_audit_report(
        report,
        audit_input=audit_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "audit_input": args.audit_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "royalty_abuse_audit_hash": report.get("royalty_abuse_audit_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_consent_revocation_propagation(args: argparse.Namespace) -> int:
    propagation_input = load_consent_revocation_propagation_input(
        args.propagation_input
    )
    report = make_consent_revocation_propagation_report(
        propagation_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "consent_revocation_propagation_hash": report[
                "consent_revocation_propagation_hash"
            ],
            "rights_event_count": report["summary"]["rights_event_count"],
            "missing_surface_event_count": report["summary"][
                "missing_surface_event_count"
            ],
            "missing_downstream_acknowledgement_count": report["summary"][
                "missing_downstream_acknowledgement_count"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_consent_revocation_propagation(args: argparse.Namespace) -> int:
    propagation_input = load_consent_revocation_propagation_input(
        args.propagation_input
    )
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_consent_revocation_propagation_report(
        report,
        propagation_input=propagation_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "propagation_input": args.propagation_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "consent_revocation_propagation_hash": report.get(
            "consent_revocation_propagation_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_evidence_force_calibration(args: argparse.Namespace) -> int:
    calibration_input = load_evidence_force_calibration_input(args.calibration_input)
    report = make_evidence_force_calibration_report(
        calibration_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "evidence_force_calibration_hash": report[
                "evidence_force_calibration_hash"
            ],
            "claim_count": report["summary"]["claim_count"],
            "calibrated_claim_count": report["summary"]["calibrated_claim_count"],
            "over_warranted_claim_count": report["summary"][
                "over_warranted_claim_count"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_evidence_force_calibration(args: argparse.Namespace) -> int:
    calibration_input = load_evidence_force_calibration_input(args.calibration_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_evidence_force_calibration_report(
        report,
        calibration_input=calibration_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "calibration_input": args.calibration_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "evidence_force_calibration_hash": report.get(
            "evidence_force_calibration_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_warranted_source_footer(args: argparse.Namespace) -> int:
    footer_input = load_warranted_source_footer_input(args.footer_input)
    report = make_warranted_source_footer(
        footer_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "warranted_source_footer_hash": report["warranted_source_footer_hash"],
            "visible_claim_count": report["summary"]["visible_claim_count"],
            "calibrated_visible_claim_count": report["summary"][
                "calibrated_visible_claim_count"
            ],
            "warrant_line_count": report["summary"]["warrant_line_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_warranted_source_footer(args: argparse.Namespace) -> int:
    footer_input = load_warranted_source_footer_input(args.footer_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_warranted_source_footer(
        report,
        footer_input=footer_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "footer_input": args.footer_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "warranted_source_footer_hash": report.get(
            "warranted_source_footer_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_source_origin_lineage(args: argparse.Namespace) -> int:
    lineage_input = load_source_origin_lineage_input(args.lineage_input)
    report = make_source_origin_lineage_report(
        lineage_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "source_origin_lineage_hash": report["source_origin_lineage_hash"],
            "visible_source_count": report["summary"]["visible_source_count"],
            "direct_payout_source_count": report["summary"][
                "direct_payout_source_count"
            ],
            "origin_review_escrow_source_count": report["summary"][
                "origin_review_escrow_source_count"
            ],
            "upstream_royalty_row_count": report["summary"][
                "upstream_royalty_row_count"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_source_origin_lineage(args: argparse.Namespace) -> int:
    lineage_input = load_source_origin_lineage_input(args.lineage_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_source_origin_lineage_report(
        report,
        lineage_input=lineage_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "lineage_input": args.lineage_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "source_origin_lineage_hash": report.get("source_origin_lineage_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_evidence_preview_footer(args: argparse.Namespace) -> int:
    preview_input = load_evidence_preview_footer_input(args.preview_input)
    report = make_evidence_preview_footer(
        preview_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "evidence_preview_footer_hash": report["evidence_preview_footer_hash"],
            "visible_source_count": report["summary"]["visible_source_count"],
            "claim_preview_count": report["summary"]["claim_preview_count"],
            "permissioned_excerpt_count": report["summary"][
                "permissioned_excerpt_count"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_evidence_preview_footer(args: argparse.Namespace) -> int:
    preview_input = load_evidence_preview_footer_input(args.preview_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_evidence_preview_footer(
        report,
        preview_input=preview_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "preview_input": args.preview_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "evidence_preview_footer_hash": report.get("evidence_preview_footer_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_evidence_locator_manifest(args: argparse.Namespace) -> int:
    locator_input = load_evidence_locator_manifest_input(args.locator_input)
    report = make_evidence_locator_manifest(
        locator_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "evidence_locator_manifest_hash": report[
                "evidence_locator_manifest_hash"
            ],
            "preview_claim_count": report["summary"]["preview_claim_count"],
            "locator_count": report["summary"]["locator_count"],
            "exact_locator_count": report["summary"]["exact_locator_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_evidence_locator_manifest(args: argparse.Namespace) -> int:
    locator_input = load_evidence_locator_manifest_input(args.locator_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_evidence_locator_manifest(
        report,
        locator_input=locator_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "locator_input": args.locator_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "evidence_locator_manifest_hash": report.get(
            "evidence_locator_manifest_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_citation_url_health(args: argparse.Namespace) -> int:
    health_input = load_citation_url_health_input(args.health_input)
    report = make_citation_url_health_report(
        health_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "citation_url_health_hash": report["citation_url_health_hash"],
            "locator_count": report["summary"]["locator_count"],
            "live_url_count": report["summary"]["live_url_count"],
            "archived_only_url_count": report["summary"]["archived_only_url_count"],
            "fabricated_or_never_seen_url_count": report["summary"][
                "fabricated_or_never_seen_url_count"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_citation_url_health(args: argparse.Namespace) -> int:
    health_input = load_citation_url_health_input(args.health_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_citation_url_health_report(
        report,
        health_input=health_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "health_input": args.health_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "citation_url_health_hash": report.get("citation_url_health_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_composite_foundation_adapter(args: argparse.Namespace) -> int:
    adapter_input = load_composite_foundation_adapter_input(args.adapter_input)
    report = make_composite_foundation_adapter_report(
        adapter_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "composite_foundation_adapter_hash": report[
                "composite_foundation_adapter_hash"
            ],
            "provider_adapter_count": report["summary"]["provider_adapter_count"],
            "covered_provider_family_count": report["summary"][
                "covered_provider_family_count"
            ],
            "required_provider_family_count": report["summary"][
                "required_provider_family_count"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_composite_foundation_adapter(args: argparse.Namespace) -> int:
    adapter_input = load_composite_foundation_adapter_input(args.adapter_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_composite_foundation_adapter_report(
        report,
        adapter_input=adapter_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "adapter_input": args.adapter_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "composite_foundation_adapter_hash": report.get(
            "composite_foundation_adapter_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_foundation_provider_conformance(args: argparse.Namespace) -> int:
    conformance_input = load_foundation_provider_conformance_input(
        args.conformance_input
    )
    report = make_foundation_provider_conformance_report(
        conformance_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "foundation_provider_conformance_hash": report[
                "foundation_provider_conformance_hash"
            ],
            "provider_conformance_row_count": report["summary"][
                "provider_conformance_row_count"
            ],
            "covered_provider_family_count": report["summary"][
                "covered_provider_family_count"
            ],
            "required_provider_family_count": report["summary"][
                "required_provider_family_count"
            ],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_foundation_provider_conformance(args: argparse.Namespace) -> int:
    conformance_input = load_foundation_provider_conformance_input(
        args.conformance_input
    )
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_foundation_provider_conformance_report(
        report,
        conformance_input=conformance_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "conformance_input": args.conformance_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "foundation_provider_conformance_hash": report.get(
            "foundation_provider_conformance_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_foundation_runtime_adapter(args: argparse.Namespace) -> int:
    adapter_input = load_foundation_runtime_adapter_input(args.adapter_input)
    report = make_foundation_runtime_adapter_report(
        adapter_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "foundation_runtime_adapter_hash": report[
                "foundation_runtime_adapter_hash"
            ],
            "provider_family": report["summary"]["provider_family"],
            "runtime_release_authorized": report["summary"][
                "runtime_release_authorized"
            ],
            "failed_check_count": report["summary"]["failed_check_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_verify_foundation_runtime_adapter(args: argparse.Namespace) -> int:
    adapter_input = load_foundation_runtime_adapter_input(args.adapter_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_foundation_runtime_adapter_report(
        report,
        adapter_input=adapter_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "adapter_input": args.adapter_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "foundation_runtime_adapter_hash": report.get(
            "foundation_runtime_adapter_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_foundation_runtime_router(args: argparse.Namespace) -> int:
    router_input = load_foundation_runtime_router_input(args.router_input)
    report = make_foundation_runtime_router_report(
        router_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "foundation_runtime_router_hash": report[
                "foundation_runtime_router_hash"
            ],
            "selected_provider_family": report["summary"][
                "selected_provider_family"
            ],
            "router_release_authorized": report["summary"][
                "router_release_authorized"
            ],
            "failed_check_count": report["summary"]["failed_check_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_verify_foundation_runtime_router(args: argparse.Namespace) -> int:
    router_input = load_foundation_runtime_router_input(args.router_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_foundation_runtime_router_report(
        report,
        router_input=router_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "router_input": args.router_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "foundation_runtime_router_hash": report.get(
            "foundation_runtime_router_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_foundation_model_deployment_attestation(args: argparse.Namespace) -> int:
    attestation_input = load_foundation_model_deployment_attestation_input(
        args.attestation_input
    )
    report = make_foundation_model_deployment_attestation_report(
        attestation_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "foundation_model_deployment_attestation_hash": report[
                "foundation_model_deployment_attestation_hash"
            ],
            "provider_family": report["summary"]["provider_family"],
            "native_model": report["summary"]["native_model"],
            "deployment_release_authorized": report["summary"][
                "deployment_release_authorized"
            ],
            "failed_check_count": report["summary"]["failed_check_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_verify_foundation_model_deployment_attestation(args: argparse.Namespace) -> int:
    attestation_input = load_foundation_model_deployment_attestation_input(
        args.attestation_input
    )
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_foundation_model_deployment_attestation_report(
        report,
        attestation_input=attestation_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "attestation_input": args.attestation_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "foundation_model_deployment_attestation_hash": report.get(
            "foundation_model_deployment_attestation_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_composition_receipt(args: argparse.Namespace) -> int:
    composition_input = load_universal_composition_receipt_input(
        args.composition_input
    )
    report = make_universal_composition_receipt(
        composition_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "universal_composition_receipt_hash": report[
                "universal_composition_receipt_hash"
            ],
            "provider_segment_count": report["summary"][
                "provider_segment_count"
            ],
            "provider_family_count": report["summary"]["provider_family_count"],
            "composite_answer_release_authorized": report["summary"][
                "composite_answer_release_authorized"
            ],
            "failed_check_count": report["summary"]["failed_check_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_verify_universal_composition_receipt(args: argparse.Namespace) -> int:
    composition_input = load_universal_composition_receipt_input(
        args.composition_input
    )
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_universal_composition_receipt(
        report,
        composition_input=composition_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "composition_input": args.composition_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_composition_receipt_hash": report.get(
            "universal_composition_receipt_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_composition_settlement(args: argparse.Namespace) -> int:
    settlement_input = load_universal_composition_settlement_input(
        args.settlement_input
    )
    report = make_universal_composition_settlement(
        settlement_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "universal_composition_settlement_hash": report[
                "universal_composition_settlement_hash"
            ],
            "provider_segment_count": report["summary"][
                "provider_segment_count"
            ],
            "creator_obligation_count": report["summary"][
                "creator_obligation_count"
            ],
            "payable_total": report["summary"]["payable_total"],
            "escrow_total": report["summary"]["escrow_total"],
            "held_total": report["summary"]["held_total"],
            "composition_settlement_authorized": report["summary"][
                "composition_settlement_authorized"
            ],
            "failed_check_count": report["summary"]["failed_check_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_verify_universal_composition_settlement(args: argparse.Namespace) -> int:
    settlement_input = load_universal_composition_settlement_input(
        args.settlement_input
    )
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_universal_composition_settlement(
        report,
        settlement_input=settlement_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "settlement_input": args.settlement_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_composition_settlement_hash": report.get(
            "universal_composition_settlement_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_foundation_model_contract(args: argparse.Namespace) -> int:
    contract_input = load_universal_foundation_model_contract_input(
        args.contract_input
    )
    report = make_universal_foundation_model_contract(
        contract_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "universal_foundation_model_contract_hash": report[
                "universal_foundation_model_contract_hash"
            ],
            "required_provider_family_count": report["summary"][
                "required_provider_family_count"
            ],
            "covered_provider_family_count": report["summary"][
                "covered_provider_family_count"
            ],
            "selected_provider_family": report["summary"][
                "selected_provider_family"
            ],
            "universal_contract_release_authorized": report["summary"][
                "universal_contract_release_authorized"
            ],
            "failed_check_count": report["summary"]["failed_check_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_verify_universal_foundation_model_contract(args: argparse.Namespace) -> int:
    contract_input = load_universal_foundation_model_contract_input(
        args.contract_input
    )
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_universal_foundation_model_contract(
        report,
        contract_input=contract_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "contract_input": args.contract_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_foundation_model_contract_hash": report.get(
            "universal_foundation_model_contract_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_invocation_guard(args: argparse.Namespace) -> int:
    guard_input = load_universal_invocation_guard_input(args.guard_input)
    report = make_universal_invocation_guard(
        guard_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "universal_invocation_guard_hash": report[
                "universal_invocation_guard_hash"
            ],
            "selected_provider_family": report["summary"][
                "selected_provider_family"
            ],
            "selected_route_id": report["summary"]["selected_route_id"],
            "preflight_authorized": report["summary"]["preflight_authorized"],
            "native_provider_call_allowed": report["summary"][
                "native_provider_call_allowed"
            ],
            "failed_check_count": report["summary"]["failed_check_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_verify_universal_invocation_guard(args: argparse.Namespace) -> int:
    guard_input = load_universal_invocation_guard_input(args.guard_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_universal_invocation_guard(
        report,
        guard_input=guard_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "guard_input": args.guard_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_invocation_guard_hash": report.get(
            "universal_invocation_guard_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_invocation_coverage(args: argparse.Namespace) -> int:
    coverage_input = load_universal_invocation_coverage_input(args.coverage_input)
    report = make_universal_invocation_coverage(
        coverage_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "universal_invocation_coverage_hash": report[
                "universal_invocation_coverage_hash"
            ],
            "metered_call_count": report["summary"]["metered_call_count"],
            "guarded_call_count": report["summary"]["guarded_call_count"],
            "uncovered_call_count": report["summary"]["uncovered_call_count"],
            "field_mismatch_count": report["summary"]["field_mismatch_count"],
            "coverage_complete": report["summary"]["coverage_complete"],
            "failed_check_count": report["summary"]["failed_check_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_universal_invocation_coverage(args: argparse.Namespace) -> int:
    coverage_input = load_universal_invocation_coverage_input(args.coverage_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_universal_invocation_coverage(
        report,
        coverage_input=coverage_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "coverage_input": args.coverage_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_invocation_coverage_hash": report.get(
            "universal_invocation_coverage_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_invocation_witness(args: argparse.Namespace) -> int:
    witness_input = load_universal_invocation_witness_input(args.witness_input)
    report = make_universal_invocation_witness(
        witness_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "universal_invocation_witness_hash": report[
                "universal_invocation_witness_hash"
            ],
            "covered_call_count": report["summary"]["covered_call_count"],
            "provider_receipt_count": report["summary"]["provider_receipt_count"],
            "egress_event_count": report["summary"]["egress_event_count"],
            "witness_event_count": report["summary"]["witness_event_count"],
            "nonrepudiation_complete": report["summary"][
                "nonrepudiation_complete"
            ],
            "failed_check_count": report["summary"]["failed_check_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_universal_invocation_witness(args: argparse.Namespace) -> int:
    witness_input = load_universal_invocation_witness_input(args.witness_input)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify_universal_invocation_witness(
        report,
        witness_input=witness_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "report": args.report,
        "witness_input": args.witness_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_invocation_witness_hash": report.get(
            "universal_invocation_witness_hash", ""
        ),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_content_credential(args: argparse.Namespace) -> int:
    credential_input = load_universal_content_credential_input(args.credential_input)
    credential = make_universal_content_credential(
        credential_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(credential, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": credential["summary"]["status"],
            "output": args.output,
            "universal_content_credential_hash": credential[
                "universal_content_credential_hash"
            ],
            "content_subject_hash": credential["summary"][
                "content_subject_hash"
            ],
            "source_count": credential["summary"]["source_count"],
            "payout_row_count": credential["summary"]["payout_row_count"],
            "provider_invocation_count": credential["summary"][
                "provider_invocation_count"
            ],
            "durable_signal_count": credential["summary"]["durable_signal_count"],
            "failed_check_count": credential["summary"]["failed_check_count"],
        }
    else:
        result = credential
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if credential["summary"]["status"] == "ready" else 1


def run_verify_universal_content_credential(args: argparse.Namespace) -> int:
    credential_input = load_universal_content_credential_input(args.credential_input)
    credential = json.loads(Path(args.credential).read_text(encoding="utf-8"))
    errors = verify_universal_content_credential(
        credential,
        credential_input=credential_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "credential": args.credential,
        "credential_input": args.credential_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_content_credential_hash": credential.get(
            "universal_content_credential_hash", ""
        ),
        "summary": credential.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_rdllm_passport(args: argparse.Namespace) -> int:
    passport_input = load_universal_rdllm_passport_input(args.passport_input)
    passport = make_universal_rdllm_passport(
        passport_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(passport, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": passport["summary"]["status"],
            "output": args.output,
            "universal_rdllm_passport_hash": passport[
                "universal_rdllm_passport_hash"
            ],
            "provider_family_count": passport["summary"]["provider_family_count"],
            "covered_provider_family_count": passport["summary"][
                "covered_provider_family_count"
            ],
            "core_artifact_count": passport["summary"]["core_artifact_count"],
            "public_surface_count": passport["summary"]["public_surface_count"],
            "verifier_command_count": passport["summary"]["verifier_command_count"],
            "failed_check_count": passport["summary"]["failed_check_count"],
        }
    else:
        result = passport
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if passport["summary"]["status"] == "ready" else 1


def run_verify_universal_rdllm_passport(args: argparse.Namespace) -> int:
    passport_input = load_universal_rdllm_passport_input(args.passport_input)
    passport = json.loads(Path(args.passport).read_text(encoding="utf-8"))
    errors = verify_universal_rdllm_passport(
        passport,
        passport_input=passport_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "passport": args.passport,
        "passport_input": args.passport_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_rdllm_passport_hash": passport.get(
            "universal_rdllm_passport_hash", ""
        ),
        "summary": passport.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_adoption_standard(args: argparse.Namespace) -> int:
    standard_input = load_universal_adoption_standard_input(args.standard_input)
    standard = make_universal_adoption_standard(
        standard_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(standard, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": standard["summary"]["status"],
            "output": args.output,
            "universal_adoption_standard_hash": standard[
                "universal_adoption_standard_hash"
            ],
            "provider_family_count": standard["summary"]["provider_family_count"],
            "sdk_surface_count": standard["summary"]["sdk_surface_count"],
            "implementer_role_count": standard["summary"]["implementer_role_count"],
            "procurement_gate_count": standard["summary"]["procurement_gate_count"],
            "public_surface_count": standard["summary"]["public_surface_count"],
            "failed_check_count": standard["summary"]["failed_check_count"],
        }
    else:
        result = standard
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if standard["summary"]["status"] == "ready" else 1


def run_verify_universal_adoption_standard(args: argparse.Namespace) -> int:
    standard_input = load_universal_adoption_standard_input(args.standard_input)
    standard = json.loads(Path(args.standard).read_text(encoding="utf-8"))
    errors = verify_universal_adoption_standard(
        standard,
        standard_input=standard_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "standard": args.standard,
        "standard_input": args.standard_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_adoption_standard_hash": standard.get(
            "universal_adoption_standard_hash", ""
        ),
        "summary": standard.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_interop_test_kit(args: argparse.Namespace) -> int:
    kit_input = load_universal_interop_test_kit_input(args.kit_input)
    kit = make_universal_interop_test_kit(
        kit_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(kit, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": kit["summary"]["status"],
            "output": args.output,
            "universal_interop_test_kit_hash": kit[
                "universal_interop_test_kit_hash"
            ],
            "provider_family_count": kit["summary"]["provider_family_count"],
            "kit_component_count": kit["summary"]["kit_component_count"],
            "sdk_binding_count": kit["summary"]["sdk_binding_count"],
            "execution_target_count": kit["summary"]["execution_target_count"],
            "failure_case_count": kit["summary"]["failure_case_count"],
            "failed_check_count": kit["summary"]["failed_check_count"],
        }
    else:
        result = kit
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if kit["summary"]["status"] == "ready" else 1


def run_verify_universal_interop_test_kit(args: argparse.Namespace) -> int:
    kit_input = load_universal_interop_test_kit_input(args.kit_input)
    kit = json.loads(Path(args.kit).read_text(encoding="utf-8"))
    errors = verify_universal_interop_test_kit(
        kit,
        kit_input=kit_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "kit": args.kit,
        "kit_input": args.kit_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_interop_test_kit_hash": kit.get(
            "universal_interop_test_kit_hash", ""
        ),
        "summary": kit.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_context_provenance_bridge(args: argparse.Namespace) -> int:
    bridge_input = load_universal_context_provenance_bridge_input(args.bridge_input)
    bridge = make_universal_context_provenance_bridge(
        bridge_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(bridge, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": bridge["summary"]["status"],
            "output": args.output,
            "universal_context_provenance_bridge_hash": bridge[
                "universal_context_provenance_bridge_hash"
            ],
            "context_protocol_count": bridge["summary"]["context_protocol_count"],
            "context_access_count": bridge["summary"]["context_access_count"],
            "agent_step_count": bridge["summary"]["agent_step_count"],
            "royalty_projection_count": bridge["summary"]["royalty_projection_count"],
            "failed_check_count": bridge["summary"]["failed_check_count"],
        }
    else:
        result = bridge
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if bridge["summary"]["status"] == "ready" else 1


def run_verify_universal_context_provenance_bridge(args: argparse.Namespace) -> int:
    bridge_input = load_universal_context_provenance_bridge_input(args.bridge_input)
    bridge = json.loads(Path(args.bridge).read_text(encoding="utf-8"))
    errors = verify_universal_context_provenance_bridge(
        bridge,
        bridge_input=bridge_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "bridge": args.bridge,
        "bridge_input": args.bridge_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_context_provenance_bridge_hash": bridge.get(
            "universal_context_provenance_bridge_hash", ""
        ),
        "summary": bridge.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_citation_verification_contract(args: argparse.Namespace) -> int:
    contract_input = load_universal_citation_verification_contract_input(
        args.contract_input
    )
    contract = make_universal_citation_verification_contract(
        contract_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(contract, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": contract["summary"]["status"],
            "output": args.output,
            "universal_citation_verification_contract_hash": contract[
                "universal_citation_verification_contract_hash"
            ],
            "citation_verification_count": contract["summary"][
                "citation_verification_count"
            ],
            "displayed_footer_label_count": contract["summary"][
                "displayed_footer_label_count"
            ],
            "failed_check_count": contract["summary"]["failed_check_count"],
        }
    else:
        result = contract
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if contract["summary"]["status"] == "ready" else 1


def run_verify_universal_citation_verification_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_citation_verification_contract_input(
        args.contract_input
    )
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    errors = verify_universal_citation_verification_contract(
        contract,
        contract_input=contract_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "contract": args.contract,
        "contract_input": args.contract_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_citation_verification_contract_hash": contract.get(
            "universal_citation_verification_contract_hash", ""
        ),
        "summary": contract.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_grounded_reuse_contract(args: argparse.Namespace) -> int:
    reuse_input = load_universal_grounded_reuse_contract_input(args.reuse_input)
    contract = make_universal_grounded_reuse_contract(
        reuse_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(contract, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": contract["summary"]["status"],
            "output": args.output,
            "universal_grounded_reuse_contract_hash": contract[
                "universal_grounded_reuse_contract_hash"
            ],
            "provider_family_count": contract["summary"]["provider_family_count"],
            "reuse_decision_count": contract["summary"]["reuse_decision_count"],
            "failed_check_count": contract["summary"]["failed_check_count"],
        }
    else:
        result = contract
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if contract["summary"]["status"] == "ready" else 1


def run_verify_universal_grounded_reuse_contract(args: argparse.Namespace) -> int:
    reuse_input = load_universal_grounded_reuse_contract_input(args.reuse_input)
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    errors = verify_universal_grounded_reuse_contract(
        contract,
        reuse_input=reuse_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "contract": args.contract,
        "reuse_input": args.reuse_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_grounded_reuse_contract_hash": contract.get(
            "universal_grounded_reuse_contract_hash", ""
        ),
        "summary": contract.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_training_serving_contract(args: argparse.Namespace) -> int:
    contract_input = load_universal_training_serving_contract_input(args.contract_input)
    contract = make_universal_training_serving_contract(
        contract_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(contract, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": contract["summary"]["status"],
            "output": args.output,
            "universal_training_serving_contract_hash": contract[
                "universal_training_serving_contract_hash"
            ],
            "provider_family_count": contract["summary"]["provider_family_count"],
            "training_stage_count": contract["summary"]["training_stage_count"],
            "training_serving_obligation_count": contract["summary"][
                "training_serving_obligation_count"
            ],
            "failed_check_count": contract["summary"]["failed_check_count"],
        }
    else:
        result = contract
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if contract["summary"]["status"] == "ready" else 1


def run_verify_universal_training_serving_contract(args: argparse.Namespace) -> int:
    contract_input = load_universal_training_serving_contract_input(args.contract_input)
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    errors = verify_universal_training_serving_contract(
        contract,
        contract_input=contract_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "contract": args.contract,
        "contract_input": args.contract_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_training_serving_contract_hash": contract.get(
            "universal_training_serving_contract_hash", ""
        ),
        "summary": contract.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_confidential_attribution_audit(args: argparse.Namespace) -> int:
    audit_input = load_universal_confidential_attribution_audit_input(args.audit_input)
    audit = make_universal_confidential_attribution_audit(
        audit_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(audit, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": audit["summary"]["status"],
            "output": args.output,
            "universal_confidential_attribution_audit_hash": audit[
                "universal_confidential_attribution_audit_hash"
            ],
            "provider_family_count": audit["summary"]["provider_family_count"],
            "audit_domain_count": audit["summary"]["audit_domain_count"],
            "confidential_audit_obligation_count": audit["summary"][
                "confidential_audit_obligation_count"
            ],
            "failed_check_count": audit["summary"]["failed_check_count"],
        }
    else:
        result = audit
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if audit["summary"]["status"] == "ready" else 1


def run_verify_universal_confidential_attribution_audit(
    args: argparse.Namespace,
) -> int:
    audit_input = load_universal_confidential_attribution_audit_input(args.audit_input)
    audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))
    errors = verify_universal_confidential_attribution_audit(
        audit,
        audit_input=audit_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "audit": args.audit,
        "audit_input": args.audit_input,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_confidential_attribution_audit_hash": audit.get(
            "universal_confidential_attribution_audit_hash", ""
        ),
        "summary": audit.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_attribution_authority_control_plane(
    args: argparse.Namespace,
) -> int:
    control_input = load_universal_attribution_authority_control_plane_input(
        args.control_input
    )
    control_plane = make_universal_attribution_authority_control_plane(
        control_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(control_plane, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": control_plane["summary"]["status"],
            "output": args.output,
            "universal_attribution_authority_control_plane_hash": control_plane[
                "universal_attribution_authority_control_plane_hash"
            ],
            "provider_family_count": control_plane["summary"][
                "provider_family_count"
            ],
            "runtime_surface_count": control_plane["summary"][
                "runtime_surface_count"
            ],
            "authority_obligation_count": control_plane["summary"][
                "authority_obligation_count"
            ],
            "failed_check_count": control_plane["summary"]["failed_check_count"],
        }
    else:
        result = control_plane
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if control_plane["summary"]["status"] == "ready" else 1


def run_verify_universal_attribution_authority_control_plane(
    args: argparse.Namespace,
) -> int:
    control_input = load_universal_attribution_authority_control_plane_input(
        args.control_input
    )
    control_plane = json.loads(Path(args.control_plane).read_text(encoding="utf-8"))
    errors = verify_universal_attribution_authority_control_plane(
        control_plane,
        control_input=control_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "control_input": args.control_input,
        "control_plane": args.control_plane,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_attribution_authority_control_plane_hash": control_plane.get(
            "universal_attribution_authority_control_plane_hash", ""
        ),
        "summary": control_plane.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_rdllm_root(args: argparse.Namespace) -> int:
    root_input = load_universal_rdllm_root_input(args.root_input)
    root = make_universal_rdllm_root(
        root_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(root, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": root["summary"]["status"],
            "output": args.output,
            "universal_rdllm_root_hash": root["universal_rdllm_root_hash"],
            "provider_family_count": root["summary"]["provider_family_count"],
            "composite_surface_count": root["summary"]["composite_surface_count"],
            "root_obligation_count": root["summary"]["root_obligation_count"],
            "failed_check_count": root["summary"]["failed_check_count"],
        }
    else:
        result = root
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if root["summary"]["status"] == "ready" else 1


def run_verify_universal_rdllm_root(args: argparse.Namespace) -> int:
    root_input = load_universal_rdllm_root_input(args.root_input)
    root = json.loads(Path(args.root).read_text(encoding="utf-8"))
    errors = verify_universal_rdllm_root(
        root,
        root_input=root_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "root_input": args.root_input,
        "root": args.root,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_rdllm_root_hash": root.get("universal_rdllm_root_hash", ""),
        "summary": root.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_emission_enforcement_gateway(args: argparse.Namespace) -> int:
    gateway_input = load_universal_emission_enforcement_gateway_input(
        args.gateway_input
    )
    gateway = make_universal_emission_enforcement_gateway(
        gateway_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(gateway, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": gateway["summary"]["status"],
            "output": args.output,
            "universal_emission_enforcement_gateway_hash": gateway[
                "universal_emission_enforcement_gateway_hash"
            ],
            "provider_family_count": gateway["summary"]["provider_family_count"],
            "emission_channel_count": gateway["summary"]["emission_channel_count"],
            "enforcement_stage_count": gateway["summary"]["enforcement_stage_count"],
            "failed_check_count": gateway["summary"]["failed_check_count"],
        }
    else:
        result = gateway
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if gateway["summary"]["status"] == "ready" else 1


def run_verify_universal_emission_enforcement_gateway(
    args: argparse.Namespace,
) -> int:
    gateway_input = load_universal_emission_enforcement_gateway_input(
        args.gateway_input
    )
    gateway = json.loads(Path(args.gateway).read_text(encoding="utf-8"))
    errors = verify_universal_emission_enforcement_gateway(
        gateway,
        gateway_input=gateway_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "gateway_input": args.gateway_input,
        "gateway": args.gateway,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_emission_enforcement_gateway_hash": gateway.get(
            "universal_emission_enforcement_gateway_hash", ""
        ),
        "summary": gateway.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_composite_rdllm_profile(args: argparse.Namespace) -> int:
    profile_input = load_universal_composite_rdllm_profile_input(
        args.profile_input
    )
    profile = make_universal_composite_rdllm_profile(
        profile_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(profile, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": profile["summary"]["status"],
            "output": args.output,
            "universal_composite_rdllm_profile_hash": profile[
                "universal_composite_rdllm_profile_hash"
            ],
            "provider_family_count": profile["summary"]["provider_family_count"],
            "api_binding_count": profile["summary"]["api_binding_count"],
            "composite_plane_count": profile["summary"]["composite_plane_count"],
            "customer_surface_count": profile["summary"]["customer_surface_count"],
            "standard_mapping_count": profile["summary"]["standard_mapping_count"],
            "failed_check_count": profile["summary"]["failed_check_count"],
        }
    else:
        result = profile
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if profile["summary"]["status"] == "ready" else 1


def run_verify_universal_composite_rdllm_profile(
    args: argparse.Namespace,
) -> int:
    profile_input = load_universal_composite_rdllm_profile_input(
        args.profile_input
    )
    profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    errors = verify_universal_composite_rdllm_profile(
        profile,
        profile_input=profile_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "profile_input": args.profile_input,
        "profile": args.profile,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_composite_rdllm_profile_hash": profile.get(
            "universal_composite_rdllm_profile_hash", ""
        ),
        "summary": profile.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_runtime_conformance_receipt(args: argparse.Namespace) -> int:
    receipt_input = load_universal_runtime_conformance_receipt_input(
        args.receipt_input
    )
    receipt = make_universal_runtime_conformance_receipt(
        receipt_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(receipt, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": receipt["summary"]["status"],
            "output": args.output,
            "universal_runtime_conformance_receipt_hash": receipt[
                "universal_runtime_conformance_receipt_hash"
            ],
            "provider_family_count": receipt["summary"]["provider_family_count"],
            "api_binding_count": receipt["summary"]["api_binding_count"],
            "runtime_entrypoint_count": receipt["summary"][
                "runtime_entrypoint_count"
            ],
            "source_attribution_mode_count": receipt["summary"][
                "source_attribution_mode_count"
            ],
            "enforcement_control_count": receipt["summary"][
                "enforcement_control_count"
            ],
            "failed_check_count": receipt["summary"]["failed_check_count"],
        }
    else:
        result = receipt
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if receipt["summary"]["status"] == "ready" else 1


def run_verify_universal_runtime_conformance_receipt(
    args: argparse.Namespace,
) -> int:
    receipt_input = load_universal_runtime_conformance_receipt_input(
        args.receipt_input
    )
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    errors = verify_universal_runtime_conformance_receipt(
        receipt,
        receipt_input=receipt_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "receipt_input": args.receipt_input,
        "receipt": args.receipt,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_runtime_conformance_receipt_hash": receipt.get(
            "universal_runtime_conformance_receipt_hash", ""
        ),
        "summary": receipt.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_claim_provenance_envelope(args: argparse.Namespace) -> int:
    envelope_input = load_universal_claim_provenance_envelope_input(
        args.envelope_input
    )
    envelope = make_universal_claim_provenance_envelope(
        envelope_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(envelope, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": envelope["summary"]["status"],
            "output": args.output,
            "universal_claim_provenance_envelope_hash": envelope[
                "universal_claim_provenance_envelope_hash"
            ],
            "claim_provenance_row_count": envelope["summary"][
                "claim_provenance_row_count"
            ],
            "support_relation_count": envelope["summary"]["support_relation_count"],
            "render_surface_count": envelope["summary"]["render_surface_count"],
            "failed_check_count": envelope["summary"]["failed_check_count"],
        }
    else:
        result = envelope
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if envelope["summary"]["status"] == "ready" else 1


def run_verify_universal_claim_provenance_envelope(
    args: argparse.Namespace,
) -> int:
    envelope_input = load_universal_claim_provenance_envelope_input(
        args.envelope_input
    )
    envelope = json.loads(Path(args.envelope).read_text(encoding="utf-8"))
    errors = verify_universal_claim_provenance_envelope(
        envelope,
        envelope_input=envelope_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "envelope_input": args.envelope_input,
        "envelope": args.envelope,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_claim_provenance_envelope_hash": envelope.get(
            "universal_claim_provenance_envelope_hash", ""
        ),
        "summary": envelope.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_provider_wire_protocol(args: argparse.Namespace) -> int:
    protocol_input = load_universal_provider_wire_protocol_input(
        args.protocol_input
    )
    protocol = make_universal_provider_wire_protocol(
        protocol_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(protocol, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": protocol["summary"]["status"],
            "output": args.output,
            "universal_provider_wire_protocol_hash": protocol[
                "universal_provider_wire_protocol_hash"
            ],
            "provider_binding_count": protocol["summary"][
                "provider_binding_count"
            ],
            "wire_surface_count": protocol["summary"]["wire_surface_count"],
            "transform_mode_count": protocol["summary"]["transform_mode_count"],
            "failed_check_count": protocol["summary"]["failed_check_count"],
        }
    else:
        result = protocol
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if protocol["summary"]["status"] == "ready" else 1


def run_verify_universal_provider_wire_protocol(
    args: argparse.Namespace,
) -> int:
    protocol_input = load_universal_provider_wire_protocol_input(
        args.protocol_input
    )
    protocol = json.loads(Path(args.protocol).read_text(encoding="utf-8"))
    errors = verify_universal_provider_wire_protocol(
        protocol,
        protocol_input=protocol_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "protocol_input": args.protocol_input,
        "protocol": args.protocol,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_provider_wire_protocol_hash": protocol.get(
            "universal_provider_wire_protocol_hash", ""
        ),
        "summary": protocol.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_accountability_audit_trail(args: argparse.Namespace) -> int:
    audit_input = load_universal_accountability_audit_trail_input(args.audit_input)
    trail = make_universal_accountability_audit_trail(
        audit_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(trail, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": trail["summary"]["status"],
            "output": args.output,
            "universal_accountability_audit_trail_hash": trail[
                "universal_accountability_audit_trail_hash"
            ],
            "audit_event_count": trail["summary"]["audit_event_count"],
            "governance_record_count": trail["summary"][
                "governance_record_count"
            ],
            "integrity_control_count": trail["summary"][
                "integrity_control_count"
            ],
            "failed_check_count": trail["summary"]["failed_check_count"],
        }
    else:
        result = trail
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if trail["summary"]["status"] == "ready" else 1


def run_verify_universal_accountability_audit_trail(
    args: argparse.Namespace,
) -> int:
    audit_input = load_universal_accountability_audit_trail_input(args.audit_input)
    trail = json.loads(Path(args.audit_trail).read_text(encoding="utf-8"))
    errors = verify_universal_accountability_audit_trail(
        trail,
        audit_input=audit_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "audit_input": args.audit_input,
        "audit_trail": args.audit_trail,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_accountability_audit_trail_hash": trail.get(
            "universal_accountability_audit_trail_hash", ""
        ),
        "summary": trail.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_accountability_witness_quorum(args: argparse.Namespace) -> int:
    quorum_input = load_universal_accountability_witness_quorum_input(
        args.quorum_input
    )
    quorum = make_universal_accountability_witness_quorum(
        quorum_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(quorum, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": quorum["summary"]["status"],
            "output": args.output,
            "universal_accountability_witness_quorum_hash": quorum[
                "universal_accountability_witness_quorum_hash"
            ],
            "checkpoint_count": quorum["summary"]["checkpoint_count"],
            "transparency_log_count": quorum["summary"][
                "transparency_log_count"
            ],
            "independent_ready_witness_count": quorum["summary"][
                "independent_ready_witness_count"
            ],
            "failed_check_count": quorum["summary"]["failed_check_count"],
        }
    else:
        result = quorum
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if quorum["summary"]["status"] == "ready" else 1


def run_verify_universal_accountability_witness_quorum(
    args: argparse.Namespace,
) -> int:
    quorum_input = load_universal_accountability_witness_quorum_input(
        args.quorum_input
    )
    quorum = json.loads(Path(args.quorum).read_text(encoding="utf-8"))
    errors = verify_universal_accountability_witness_quorum(
        quorum,
        quorum_input=quorum_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "quorum_input": args.quorum_input,
        "quorum": args.quorum,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_accountability_witness_quorum_hash": quorum.get(
            "universal_accountability_witness_quorum_hash", ""
        ),
        "summary": quorum.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_grounded_reliance_contract(args: argparse.Namespace) -> int:
    contract_input = load_universal_grounded_reliance_contract_input(
        args.contract_input
    )
    contract = make_universal_grounded_reliance_contract(
        contract_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(contract, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": contract["summary"]["status"],
            "output": args.output,
            "universal_grounded_reliance_contract_hash": contract[
                "universal_grounded_reliance_contract_hash"
            ],
            "reliance_claim_count": contract["summary"]["reliance_claim_count"],
            "source_footer_surface_count": contract["summary"][
                "source_footer_surface_count"
            ],
            "settlement_scope_count": contract["summary"]["settlement_scope_count"],
            "failed_check_count": contract["summary"]["failed_check_count"],
        }
    else:
        result = contract
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if contract["summary"]["status"] == "ready" else 1


def run_verify_universal_grounded_reliance_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_grounded_reliance_contract_input(
        args.contract_input
    )
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    errors = verify_universal_grounded_reliance_contract(
        contract,
        contract_input=contract_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "contract_input": args.contract_input,
        "contract": args.contract,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_grounded_reliance_contract_hash": contract.get(
            "universal_grounded_reliance_contract_hash", ""
        ),
        "summary": contract.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_reliance_correction_ledger(args: argparse.Namespace) -> int:
    ledger_input = load_universal_reliance_correction_ledger_input(
        args.ledger_input
    )
    ledger = make_universal_reliance_correction_ledger(
        ledger_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(ledger, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": ledger["summary"]["status"],
            "output": args.output,
            "universal_reliance_correction_ledger_hash": ledger[
                "universal_reliance_correction_ledger_hash"
            ],
            "reliance_status_count": ledger["summary"]["reliance_status_count"],
            "correction_broadcast_channel_count": ledger["summary"][
                "correction_broadcast_channel_count"
            ],
            "revalidation_check_count": ledger["summary"]["revalidation_check_count"],
            "settlement_correction_scope_count": ledger["summary"][
                "settlement_correction_scope_count"
            ],
            "failed_check_count": ledger["summary"]["failed_check_count"],
        }
    else:
        result = ledger
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if ledger["summary"]["status"] == "ready" else 1


def run_verify_universal_reliance_correction_ledger(
    args: argparse.Namespace,
) -> int:
    ledger_input = load_universal_reliance_correction_ledger_input(
        args.ledger_input
    )
    ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    errors = verify_universal_reliance_correction_ledger(
        ledger,
        ledger_input=ledger_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "ledger_input": args.ledger_input,
        "ledger": args.ledger,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_reliance_correction_ledger_hash": ledger.get(
            "universal_reliance_correction_ledger_hash", ""
        ),
        "summary": ledger.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_foundation_adoption_kernel(args: argparse.Namespace) -> int:
    kernel_input = load_universal_foundation_adoption_kernel_input(
        args.kernel_input
    )
    kernel = make_universal_foundation_adoption_kernel(
        kernel_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(kernel, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": kernel["summary"]["status"],
            "output": args.output,
            "universal_foundation_adoption_kernel_hash": kernel[
                "universal_foundation_adoption_kernel_hash"
            ],
            "provider_family_count": kernel["summary"]["provider_family_count"],
            "kernel_endpoint_count": kernel["summary"]["kernel_endpoint_count"],
            "response_binding_count": kernel["summary"]["response_binding_count"],
            "client_gate_count": kernel["summary"]["client_gate_count"],
            "text_attribution_guarantee_count": kernel["summary"][
                "text_attribution_guarantee_count"
            ],
            "standard_mapping_count": kernel["summary"]["standard_mapping_count"],
            "failed_check_count": kernel["summary"]["failure_mode_count"],
        }
    else:
        result = kernel
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if kernel["summary"]["status"] == "ready" else 1


def run_verify_universal_foundation_adoption_kernel(
    args: argparse.Namespace,
) -> int:
    kernel_input = load_universal_foundation_adoption_kernel_input(
        args.kernel_input
    )
    kernel = json.loads(Path(args.kernel).read_text(encoding="utf-8"))
    errors = verify_universal_foundation_adoption_kernel(
        kernel,
        kernel_input=kernel_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "kernel_input": args.kernel_input,
        "kernel": args.kernel,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_foundation_adoption_kernel_hash": kernel.get(
            "universal_foundation_adoption_kernel_hash", ""
        ),
        "summary": kernel.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_provider_adapter_harness(args: argparse.Namespace) -> int:
    harness_input = load_universal_provider_adapter_harness_input(
        args.harness_input
    )
    harness = make_universal_provider_adapter_harness(
        harness_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(harness, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": harness["summary"]["status"],
            "output": args.output,
            "universal_provider_adapter_harness_hash": harness[
                "universal_provider_adapter_harness_hash"
            ],
            "provider_mode_count": harness["summary"]["provider_mode_count"],
            "normalized_field_count": harness["summary"][
                "normalized_field_count"
            ],
            "negative_fixture_count": harness["summary"]["negative_fixture_count"],
            "failed_check_count": harness["summary"]["failure_mode_count"],
        }
    else:
        result = harness
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if harness["summary"]["status"] == "ready" else 1


def run_verify_universal_provider_adapter_harness(
    args: argparse.Namespace,
) -> int:
    harness_input = load_universal_provider_adapter_harness_input(
        args.harness_input
    )
    harness = json.loads(Path(args.harness).read_text(encoding="utf-8"))
    errors = verify_universal_provider_adapter_harness(
        harness,
        harness_input=harness_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "harness_input": args.harness_input,
        "harness": args.harness,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_provider_adapter_harness_hash": harness.get(
            "universal_provider_adapter_harness_hash", ""
        ),
        "summary": harness.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_provider_drift_sentinel(args: argparse.Namespace) -> int:
    sentinel_input = load_universal_provider_drift_sentinel_input(
        args.sentinel_input
    )
    sentinel = make_universal_provider_drift_sentinel(
        sentinel_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(sentinel, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": sentinel["summary"]["status"],
            "output": args.output,
            "universal_provider_drift_sentinel_hash": sentinel[
                "universal_provider_drift_sentinel_hash"
            ],
            "provider_surface_count": sentinel["summary"][
                "provider_surface_count"
            ],
            "canary_replay_count": sentinel["summary"]["canary_replay_count"],
            "negative_drift_fixture_count": sentinel["summary"][
                "negative_drift_fixture_count"
            ],
            "failed_check_count": sentinel["summary"]["failure_mode_count"],
        }
    else:
        result = sentinel
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if sentinel["summary"]["status"] == "ready" else 1


def run_verify_universal_provider_drift_sentinel(
    args: argparse.Namespace,
) -> int:
    sentinel_input = load_universal_provider_drift_sentinel_input(
        args.sentinel_input
    )
    sentinel = json.loads(Path(args.sentinel).read_text(encoding="utf-8"))
    errors = verify_universal_provider_drift_sentinel(
        sentinel,
        sentinel_input=sentinel_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "sentinel_input": args.sentinel_input,
        "sentinel": args.sentinel,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_provider_drift_sentinel_hash": sentinel.get(
            "universal_provider_drift_sentinel_hash", ""
        ),
        "summary": sentinel.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_attribution_negotiation_handshake(
    args: argparse.Namespace,
) -> int:
    handshake_input = load_universal_attribution_negotiation_handshake_input(
        args.handshake_input
    )
    handshake = make_universal_attribution_negotiation_handshake(
        handshake_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(handshake, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": handshake["summary"]["status"],
            "output": args.output,
            "universal_attribution_negotiation_handshake_hash": handshake[
                "universal_attribution_negotiation_handshake_hash"
            ],
            "provider_family_count": handshake["summary"][
                "provider_family_count"
            ],
            "negotiation_phase_count": handshake["summary"][
                "negotiation_phase_count"
            ],
            "client_capability_count": handshake["summary"][
                "client_capability_count"
            ],
            "negative_negotiation_fixture_count": handshake["summary"][
                "negative_negotiation_fixture_count"
            ],
            "failed_check_count": handshake["summary"]["failure_mode_count"],
        }
    else:
        result = handshake
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if handshake["summary"]["status"] == "ready" else 1


def run_verify_universal_attribution_negotiation_handshake(
    args: argparse.Namespace,
) -> int:
    handshake_input = load_universal_attribution_negotiation_handshake_input(
        args.handshake_input
    )
    handshake = json.loads(Path(args.handshake).read_text(encoding="utf-8"))
    errors = verify_universal_attribution_negotiation_handshake(
        handshake,
        handshake_input=handshake_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "handshake_input": args.handshake_input,
        "handshake": args.handshake,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_attribution_negotiation_handshake_hash": handshake.get(
            "universal_attribution_negotiation_handshake_hash", ""
        ),
        "summary": handshake.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_negotiated_invocation_enforcement(
    args: argparse.Namespace,
) -> int:
    enforcement_input = load_universal_negotiated_invocation_enforcement_input(
        args.enforcement_input
    )
    enforcement = make_universal_negotiated_invocation_enforcement(
        enforcement_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(enforcement, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": enforcement["summary"]["status"],
            "output": args.output,
            "universal_negotiated_invocation_enforcement_hash": enforcement[
                "universal_negotiated_invocation_enforcement_hash"
            ],
            "provider_family_count": enforcement["summary"][
                "provider_family_count"
            ],
            "invocation_surface_count": enforcement["summary"][
                "invocation_surface_count"
            ],
            "enforcement_control_count": enforcement["summary"][
                "enforcement_control_count"
            ],
            "telemetry_field_count": enforcement["summary"][
                "telemetry_field_count"
            ],
            "bypass_failure_count": enforcement["summary"][
                "bypass_failure_count"
            ],
            "failed_check_count": enforcement["summary"]["failure_mode_count"],
        }
    else:
        result = enforcement
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if enforcement["summary"]["status"] == "ready" else 1


def run_verify_universal_negotiated_invocation_enforcement(
    args: argparse.Namespace,
) -> int:
    enforcement_input = load_universal_negotiated_invocation_enforcement_input(
        args.enforcement_input
    )
    enforcement = json.loads(Path(args.enforcement).read_text(encoding="utf-8"))
    errors = verify_universal_negotiated_invocation_enforcement(
        enforcement,
        enforcement_input=enforcement_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "enforcement_input": args.enforcement_input,
        "enforcement": args.enforcement,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_negotiated_invocation_enforcement_hash": enforcement.get(
            "universal_negotiated_invocation_enforcement_hash", ""
        ),
        "summary": enforcement.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_certification_trust_federation(args: argparse.Namespace) -> int:
    federation_input = load_universal_certification_trust_federation_input(
        args.federation_input
    )
    federation = make_universal_certification_trust_federation(
        federation_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(federation, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": federation["summary"]["status"],
            "output": args.output,
            "universal_certification_trust_federation_hash": federation[
                "universal_certification_trust_federation_hash"
            ],
            "federation_role_count": federation["summary"][
                "federation_role_count"
            ],
            "trust_mark_count": federation["summary"]["trust_mark_count"],
            "credential_claim_count": federation["summary"][
                "credential_claim_count"
            ],
            "transparency_channel_count": federation["summary"][
                "transparency_channel_count"
            ],
            "negative_federation_failure_count": federation["summary"][
                "negative_federation_failure_count"
            ],
            "failed_check_count": federation["summary"]["failure_mode_count"],
        }
    else:
        result = federation
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if federation["summary"]["status"] == "ready" else 1


def run_verify_universal_certification_trust_federation(
    args: argparse.Namespace,
) -> int:
    federation_input = load_universal_certification_trust_federation_input(
        args.federation_input
    )
    federation = json.loads(Path(args.federation).read_text(encoding="utf-8"))
    errors = verify_universal_certification_trust_federation(
        federation,
        federation_input=federation_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "federation_input": args.federation_input,
        "federation": args.federation,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_certification_trust_federation_hash": federation.get(
            "universal_certification_trust_federation_hash", ""
        ),
        "summary": federation.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_foundation_provider_adoption_pack(args: argparse.Namespace) -> int:
    pack_input = load_universal_foundation_provider_adoption_pack_input(
        args.pack_input
    )
    pack = make_universal_foundation_provider_adoption_pack(
        pack_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(pack, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": pack["summary"]["status"],
            "output": args.output,
            "universal_foundation_provider_adoption_pack_hash": pack[
                "universal_foundation_provider_adoption_pack_hash"
            ],
            "provider_family_count": pack["summary"]["provider_family_count"],
            "standard_export_count": pack["summary"]["standard_export_count"],
            "adoption_gate_count": pack["summary"]["adoption_gate_count"],
            "negative_adoption_failure_count": pack["summary"][
                "negative_adoption_failure_count"
            ],
            "failed_check_count": pack["summary"]["failure_mode_count"],
        }
    else:
        result = pack
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if pack["summary"]["status"] == "ready" else 1


def run_verify_universal_foundation_provider_adoption_pack(
    args: argparse.Namespace,
) -> int:
    pack_input = load_universal_foundation_provider_adoption_pack_input(
        args.pack_input
    )
    pack = json.loads(Path(args.pack).read_text(encoding="utf-8"))
    errors = verify_universal_foundation_provider_adoption_pack(
        pack,
        pack_input=pack_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "pack_input": args.pack_input,
        "pack": args.pack,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_foundation_provider_adoption_pack_hash": pack.get(
            "universal_foundation_provider_adoption_pack_hash", ""
        ),
        "summary": pack.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_industry_adoption_root(args: argparse.Namespace) -> int:
    root_input = load_universal_industry_adoption_root_input(args.root_input)
    root = make_universal_industry_adoption_root(
        root_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(root, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": root["summary"]["status"],
            "output": args.output,
            "universal_industry_adoption_root_hash": root[
                "universal_industry_adoption_root_hash"
            ],
            "publication_endpoint_count": root["summary"][
                "publication_endpoint_count"
            ],
            "adoption_role_count": root["summary"]["adoption_role_count"],
            "negative_root_failure_count": root["summary"][
                "negative_root_failure_count"
            ],
            "failed_check_count": root["summary"]["failure_mode_count"],
        }
    else:
        result = root
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if root["summary"]["status"] == "ready" else 1


def run_verify_universal_industry_adoption_root(args: argparse.Namespace) -> int:
    root_input = load_universal_industry_adoption_root_input(args.root_input)
    root = json.loads(Path(args.root).read_text(encoding="utf-8"))
    errors = verify_universal_industry_adoption_root(
        root,
        root_input=root_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "root_input": args.root_input,
        "root": args.root,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_industry_adoption_root_hash": root.get(
            "universal_industry_adoption_root_hash", ""
        ),
        "summary": root.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_reference_implementation_distribution(
    args: argparse.Namespace,
) -> int:
    distribution_input = load_universal_reference_implementation_distribution_input(
        args.distribution_input
    )
    distribution = make_universal_reference_implementation_distribution(
        distribution_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(distribution, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": distribution["summary"]["status"],
            "output": args.output,
            "universal_reference_implementation_distribution_hash": distribution[
                "universal_reference_implementation_distribution_hash"
            ],
            "component_count": distribution["summary"]["component_count"],
            "install_target_count": distribution["summary"]["install_target_count"],
            "negative_distribution_failure_count": distribution["summary"][
                "negative_distribution_failure_count"
            ],
            "failed_check_count": distribution["summary"]["failure_mode_count"],
        }
    else:
        result = distribution
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if distribution["summary"]["status"] == "ready" else 1


def run_verify_universal_reference_implementation_distribution(
    args: argparse.Namespace,
) -> int:
    distribution_input = load_universal_reference_implementation_distribution_input(
        args.distribution_input
    )
    distribution = json.loads(Path(args.distribution).read_text(encoding="utf-8"))
    errors = verify_universal_reference_implementation_distribution(
        distribution,
        distribution_input=distribution_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "distribution_input": args.distribution_input,
        "distribution": args.distribution,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_reference_implementation_distribution_hash": distribution.get(
            "universal_reference_implementation_distribution_hash", ""
        ),
        "summary": distribution.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_live_attribution_proof(args: argparse.Namespace) -> int:
    proof_input = load_universal_live_attribution_proof_input(args.proof_input)
    proof = make_universal_live_attribution_proof(
        proof_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(proof, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": proof["summary"]["status"],
            "output": args.output,
            "universal_live_attribution_proof_hash": proof[
                "universal_live_attribution_proof_hash"
            ],
            "live_source_count": proof["summary"]["live_source_count"],
            "knowledge_source_mode_count": proof["summary"][
                "knowledge_source_mode_count"
            ],
            "footer_surface_count": proof["summary"]["footer_surface_count"],
            "negative_live_failure_count": proof["summary"][
                "negative_live_failure_count"
            ],
            "failed_check_count": proof["summary"]["failure_mode_count"],
        }
    else:
        result = proof
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if proof["summary"]["status"] == "ready" else 1


def run_verify_universal_live_attribution_proof(args: argparse.Namespace) -> int:
    proof_input = load_universal_live_attribution_proof_input(args.proof_input)
    proof = json.loads(Path(args.proof).read_text(encoding="utf-8"))
    errors = verify_universal_live_attribution_proof(
        proof,
        proof_input=proof_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "proof_input": args.proof_input,
        "proof": args.proof,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_live_attribution_proof_hash": proof.get(
            "universal_live_attribution_proof_hash", ""
        ),
        "summary": proof.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_foundation_model_release_passport(
    args: argparse.Namespace,
) -> int:
    passport_input = load_universal_foundation_model_release_passport_input(
        args.passport_input
    )
    passport = make_universal_foundation_model_release_passport(
        passport_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(passport, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": passport["summary"]["status"],
            "output": args.output,
            "universal_foundation_model_release_passport_hash": passport[
                "universal_foundation_model_release_passport_hash"
            ],
            "model_release_count": passport["summary"]["model_release_count"],
            "provider_route_count": passport["summary"]["provider_route_count"],
            "release_lifecycle_domain_count": passport["summary"][
                "release_lifecycle_domain_count"
            ],
            "compliance_mapping_count": passport["summary"][
                "compliance_mapping_count"
            ],
            "negative_release_failure_count": passport["summary"][
                "negative_release_failure_count"
            ],
            "failed_check_count": passport["summary"]["failure_mode_count"],
        }
    else:
        result = passport
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if passport["summary"]["status"] == "ready" else 1


def run_verify_universal_foundation_model_release_passport(
    args: argparse.Namespace,
) -> int:
    passport_input = load_universal_foundation_model_release_passport_input(
        args.passport_input
    )
    passport = json.loads(Path(args.passport).read_text(encoding="utf-8"))
    errors = verify_universal_foundation_model_release_passport(
        passport,
        passport_input=passport_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "passport_input": args.passport_input,
        "passport": args.passport,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_foundation_model_release_passport_hash": passport.get(
            "universal_foundation_model_release_passport_hash", ""
        ),
        "summary": passport.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_composite_rdllm_contract(args: argparse.Namespace) -> int:
    contract_input = load_universal_composite_rdllm_contract_input(
        args.contract_input
    )
    contract = make_universal_composite_rdllm_contract(
        contract_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(contract, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": contract["summary"]["status"],
            "output": args.output,
            "universal_composite_rdllm_contract_hash": contract[
                "universal_composite_rdllm_contract_hash"
            ],
            "core_artifact_count": contract["summary"]["core_artifact_count"],
            "contract_role_count": contract["summary"]["contract_role_count"],
            "canonical_api_surface_count": contract["summary"][
                "canonical_api_surface_count"
            ],
            "decision_gate_count": contract["summary"]["decision_gate_count"],
            "standard_binding_count": contract["summary"]["standard_binding_count"],
            "negative_composite_failure_count": contract["summary"][
                "negative_composite_failure_count"
            ],
            "failed_check_count": contract["summary"]["failure_mode_count"],
        }
    else:
        result = contract
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if contract["summary"]["status"] == "ready" else 1


def run_verify_universal_composite_rdllm_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_composite_rdllm_contract_input(
        args.contract_input
    )
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    errors = verify_universal_composite_rdllm_contract(
        contract,
        contract_input=contract_input,
        signing_secret=args.signing_secret,
    )
    result = {
        "contract_input": args.contract_input,
        "contract": args.contract,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_composite_rdllm_contract_hash": contract.get(
            "universal_composite_rdllm_contract_hash", ""
        ),
        "summary": contract.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_foundation_provider_binding_matrix(
    args: argparse.Namespace,
) -> int:
    matrix_input = load_universal_foundation_provider_binding_matrix_input(
        args.matrix_input
    )
    matrix = make_universal_foundation_provider_binding_matrix(
        matrix_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(matrix, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": matrix["summary"]["status"],
            "output": args.output,
            "universal_foundation_provider_binding_matrix_hash": matrix[
                "universal_foundation_provider_binding_matrix_hash"
            ],
            "provider_family_count": matrix["summary"]["provider_family_count"],
            "ready_provider_family_count": matrix["summary"][
                "ready_provider_family_count"
            ],
            "binding_domain_count": matrix["summary"]["binding_domain_count"],
            "native_capability_count": matrix["summary"]["native_capability_count"],
            "negative_provider_failure_count": matrix["summary"][
                "negative_provider_failure_count"
            ],
            "failed_check_count": matrix["summary"]["failure_mode_count"],
        }
    else:
        result = matrix
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if matrix["summary"]["status"] == "ready" else 1


def run_verify_universal_foundation_provider_binding_matrix(
    args: argparse.Namespace,
) -> int:
    matrix_input = load_universal_foundation_provider_binding_matrix_input(
        args.matrix_input
    )
    matrix = json.loads(Path(args.matrix).read_text(encoding="utf-8"))
    errors = verify_universal_foundation_provider_binding_matrix(
        matrix_input,
        matrix,
        signing_secret=args.signing_secret,
    )
    result = {
        "matrix_input": args.matrix_input,
        "matrix": args.matrix,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_foundation_provider_binding_matrix_hash": matrix.get(
            "universal_foundation_provider_binding_matrix_hash", ""
        ),
        "summary": matrix.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_provider_conformance_runner_receipt(
    args: argparse.Namespace,
) -> int:
    receipt_input = load_universal_provider_conformance_runner_receipt_input(
        args.receipt_input
    )
    receipt = make_universal_provider_conformance_runner_receipt(
        receipt_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(receipt, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": receipt["summary"]["status"],
            "output": args.output,
            "universal_provider_conformance_runner_receipt_hash": receipt[
                "universal_provider_conformance_runner_receipt_hash"
            ],
            "provider_family_count": receipt["summary"]["provider_family_count"],
            "ready_provider_run_count": receipt["summary"][
                "ready_provider_run_count"
            ],
            "fixture_suite_count": receipt["summary"]["fixture_suite_count"],
            "runner_stage_count": receipt["summary"]["runner_stage_count"],
            "ready_runner_stage_count": receipt["summary"][
                "ready_runner_stage_count"
            ],
            "negative_runner_failure_count": receipt["summary"][
                "negative_runner_failure_count"
            ],
            "failed_check_count": receipt["summary"]["failure_mode_count"],
        }
    else:
        result = receipt
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if receipt["summary"]["status"] == "ready" else 1


def run_verify_universal_provider_conformance_runner_receipt(
    args: argparse.Namespace,
) -> int:
    receipt_input = load_universal_provider_conformance_runner_receipt_input(
        args.receipt_input
    )
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    errors = verify_universal_provider_conformance_runner_receipt(
        receipt_input,
        receipt,
        signing_secret=args.signing_secret,
    )
    result = {
        "receipt_input": args.receipt_input,
        "receipt": args.receipt,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_provider_conformance_runner_receipt_hash": receipt.get(
            "universal_provider_conformance_runner_receipt_hash", ""
        ),
        "summary": receipt.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_production_invocation_admission(
    args: argparse.Namespace,
) -> int:
    admission_input = load_universal_production_invocation_admission_input(
        args.admission_input
    )
    admission = make_universal_production_invocation_admission(
        admission_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(admission, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": admission["summary"]["status"],
            "output": args.output,
            "universal_production_invocation_admission_hash": admission[
                "universal_production_invocation_admission_hash"
            ],
            "provider_family_count": admission["summary"]["provider_family_count"],
            "ready_provider_admission_count": admission["summary"][
                "ready_provider_admission_count"
            ],
            "admission_gate_count": admission["summary"]["admission_gate_count"],
            "ready_admission_gate_count": admission["summary"][
                "ready_admission_gate_count"
            ],
            "invocation_surface_count": admission["summary"][
                "invocation_surface_count"
            ],
            "negative_admission_failure_count": admission["summary"][
                "negative_admission_failure_count"
            ],
            "failed_check_count": admission["summary"]["failure_mode_count"],
        }
    else:
        result = admission
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if admission["summary"]["status"] == "ready" else 1


def run_verify_universal_production_invocation_admission(
    args: argparse.Namespace,
) -> int:
    admission_input = load_universal_production_invocation_admission_input(
        args.admission_input
    )
    admission = json.loads(Path(args.admission).read_text(encoding="utf-8"))
    errors = verify_universal_production_invocation_admission(
        admission_input,
        admission,
        signing_secret=args.signing_secret,
    )
    result = {
        "admission_input": args.admission_input,
        "admission": args.admission,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_production_invocation_admission_hash": admission.get(
            "universal_production_invocation_admission_hash", ""
        ),
        "summary": admission.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_source_grounded_response_receipt(
    args: argparse.Namespace,
) -> int:
    receipt_input = load_universal_source_grounded_response_receipt_input(
        args.receipt_input
    )
    receipt = make_universal_source_grounded_response_receipt(
        receipt_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(receipt, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": receipt["summary"]["status"],
            "output": args.output,
            "universal_source_grounded_response_receipt_hash": receipt[
                "universal_source_grounded_response_receipt_hash"
            ],
            "source_category_count": receipt["summary"]["source_category_count"],
            "ready_source_category_count": receipt["summary"][
                "ready_source_category_count"
            ],
            "claim_type_count": receipt["summary"]["claim_type_count"],
            "ready_claim_type_count": receipt["summary"]["ready_claim_type_count"],
            "response_surface_count": receipt["summary"]["response_surface_count"],
            "ready_response_surface_count": receipt["summary"][
                "ready_response_surface_count"
            ],
            "settlement_scope_count": receipt["summary"]["settlement_scope_count"],
            "ready_settlement_scope_count": receipt["summary"][
                "ready_settlement_scope_count"
            ],
            "negative_response_failure_count": receipt["summary"][
                "negative_response_failure_count"
            ],
            "failed_check_count": receipt["summary"]["failure_mode_count"],
        }
    else:
        result = receipt
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if receipt["summary"]["status"] == "ready" else 1


def run_verify_universal_source_grounded_response_receipt(
    args: argparse.Namespace,
) -> int:
    receipt_input = load_universal_source_grounded_response_receipt_input(
        args.receipt_input
    )
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    errors = verify_universal_source_grounded_response_receipt(
        receipt_input,
        receipt,
        signing_secret=args.signing_secret,
    )
    result = {
        "receipt_input": args.receipt_input,
        "receipt": args.receipt,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_source_grounded_response_receipt_hash": receipt.get(
            "universal_source_grounded_response_receipt_hash", ""
        ),
        "summary": receipt.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_distribution_reliance_passport(
    args: argparse.Namespace,
) -> int:
    passport_input = load_universal_distribution_reliance_passport_input(
        args.passport_input
    )
    passport = make_universal_distribution_reliance_passport(
        passport_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(passport, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": passport["summary"]["status"],
            "output": args.output,
            "universal_distribution_reliance_passport_hash": passport[
                "universal_distribution_reliance_passport_hash"
            ],
            "distribution_surface_count": passport["summary"][
                "distribution_surface_count"
            ],
            "ready_distribution_surface_count": passport["summary"][
                "ready_distribution_surface_count"
            ],
            "portable_binding_count": passport["summary"][
                "portable_binding_count"
            ],
            "ready_portable_binding_count": passport["summary"][
                "ready_portable_binding_count"
            ],
            "status_channel_count": passport["summary"]["status_channel_count"],
            "ready_status_channel_count": passport["summary"][
                "ready_status_channel_count"
            ],
            "negative_distribution_failure_count": passport["summary"][
                "negative_distribution_failure_count"
            ],
            "failed_check_count": passport["summary"]["failure_mode_count"],
        }
    else:
        result = passport
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if passport["summary"]["status"] == "ready" else 1


def run_verify_universal_distribution_reliance_passport(
    args: argparse.Namespace,
) -> int:
    passport_input = load_universal_distribution_reliance_passport_input(
        args.passport_input
    )
    passport = json.loads(Path(args.passport).read_text(encoding="utf-8"))
    errors = verify_universal_distribution_reliance_passport(
        passport_input,
        passport,
        signing_secret=args.signing_secret,
    )
    result = {
        "passport_input": args.passport_input,
        "passport": args.passport,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_distribution_reliance_passport_hash": passport.get(
            "universal_distribution_reliance_passport_hash", ""
        ),
        "summary": passport.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_adversarial_provenance_quorum(
    args: argparse.Namespace,
) -> int:
    quorum_input = load_universal_adversarial_provenance_quorum_input(
        args.quorum_input
    )
    quorum = make_universal_adversarial_provenance_quorum(
        quorum_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(quorum, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": quorum["summary"]["status"],
            "output": args.output,
            "universal_adversarial_provenance_quorum_hash": quorum[
                "universal_adversarial_provenance_quorum_hash"
            ],
            "provenance_signal_count": quorum["summary"][
                "provenance_signal_count"
            ],
            "ready_provenance_signal_count": quorum["summary"][
                "ready_provenance_signal_count"
            ],
            "attack_class_count": quorum["summary"]["attack_class_count"],
            "ready_attack_class_count": quorum["summary"][
                "ready_attack_class_count"
            ],
            "reliance_context_count": quorum["summary"]["reliance_context_count"],
            "ready_reliance_context_count": quorum["summary"][
                "ready_reliance_context_count"
            ],
            "failed_check_count": quorum["summary"]["failure_mode_count"],
        }
    else:
        result = quorum
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if quorum["summary"]["status"] == "ready" else 1


def run_verify_universal_adversarial_provenance_quorum(
    args: argparse.Namespace,
) -> int:
    quorum_input = load_universal_adversarial_provenance_quorum_input(
        args.quorum_input
    )
    quorum = json.loads(Path(args.quorum).read_text(encoding="utf-8"))
    errors = verify_universal_adversarial_provenance_quorum(
        quorum_input,
        quorum,
        signing_secret=args.signing_secret,
    )
    result = {
        "quorum_input": args.quorum_input,
        "quorum": args.quorum,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_adversarial_provenance_quorum_hash": quorum.get(
            "universal_adversarial_provenance_quorum_hash", ""
        ),
        "summary": quorum.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_procurement_regulatory_reliance_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_procurement_regulatory_reliance_contract_input(
        args.contract_input
    )
    contract = make_universal_procurement_regulatory_reliance_contract(
        contract_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(contract, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": contract["summary"]["status"],
            "output": args.output,
            "universal_procurement_regulatory_reliance_contract_hash": contract[
                "universal_procurement_regulatory_reliance_contract_hash"
            ],
            "adoption_role_count": contract["summary"]["adoption_role_count"],
            "ready_adoption_role_count": contract["summary"][
                "ready_adoption_role_count"
            ],
            "contractual_control_count": contract["summary"][
                "contractual_control_count"
            ],
            "ready_contractual_control_count": contract["summary"][
                "ready_contractual_control_count"
            ],
            "jurisdiction_mapping_count": contract["summary"][
                "jurisdiction_mapping_count"
            ],
            "ready_jurisdiction_mapping_count": contract["summary"][
                "ready_jurisdiction_mapping_count"
            ],
            "negative_procurement_failure_count": contract["summary"][
                "negative_procurement_failure_count"
            ],
            "ready_negative_procurement_failure_count": contract["summary"][
                "ready_negative_procurement_failure_count"
            ],
            "failed_check_count": contract["summary"]["failure_mode_count"],
        }
    else:
        result = contract
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if contract["summary"]["status"] == "ready" else 1


def run_verify_universal_procurement_regulatory_reliance_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_procurement_regulatory_reliance_contract_input(
        args.contract_input
    )
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    errors = verify_universal_procurement_regulatory_reliance_contract(
        contract_input,
        contract,
        signing_secret=args.signing_secret,
    )
    result = {
        "contract_input": args.contract_input,
        "contract": args.contract,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_procurement_regulatory_reliance_contract_hash": contract.get(
            "universal_procurement_regulatory_reliance_contract_hash", ""
        ),
        "summary": contract.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_provider_onboarding_migration_covenant(
    args: argparse.Namespace,
) -> int:
    covenant_input = load_universal_provider_onboarding_migration_covenant_input(
        args.covenant_input
    )
    covenant = make_universal_provider_onboarding_migration_covenant(
        covenant_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(covenant, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": covenant["summary"]["status"],
            "output": args.output,
            "universal_provider_onboarding_migration_covenant_hash": covenant[
                "universal_provider_onboarding_migration_covenant_hash"
            ],
            "provider_family_count": covenant["summary"]["provider_family_count"],
            "ready_provider_family_count": covenant["summary"][
                "ready_provider_family_count"
            ],
            "native_api_surface_count": covenant["summary"][
                "native_api_surface_count"
            ],
            "ready_native_api_surface_count": covenant["summary"][
                "ready_native_api_surface_count"
            ],
            "migration_artifact_count": covenant["summary"][
                "migration_artifact_count"
            ],
            "ready_migration_artifact_count": covenant["summary"][
                "ready_migration_artifact_count"
            ],
            "rollout_gate_count": covenant["summary"]["rollout_gate_count"],
            "ready_rollout_gate_count": covenant["summary"][
                "ready_rollout_gate_count"
            ],
            "failed_check_count": covenant["summary"]["failure_mode_count"],
        }
    else:
        result = covenant
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if covenant["summary"]["status"] == "ready" else 1


def run_verify_universal_provider_onboarding_migration_covenant(
    args: argparse.Namespace,
) -> int:
    covenant_input = load_universal_provider_onboarding_migration_covenant_input(
        args.covenant_input
    )
    covenant = json.loads(Path(args.covenant).read_text(encoding="utf-8"))
    errors = verify_universal_provider_onboarding_migration_covenant(
        covenant_input,
        covenant,
        signing_secret=args.signing_secret,
    )
    result = {
        "covenant_input": args.covenant_input,
        "covenant": args.covenant,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_provider_onboarding_migration_covenant_hash": covenant.get(
            "universal_provider_onboarding_migration_covenant_hash", ""
        ),
        "summary": covenant.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_model_provider_registry(args: argparse.Namespace) -> int:
    registry_input = load_universal_model_provider_registry_input(
        args.registry_input
    )
    registry = make_universal_model_provider_registry(
        registry_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(registry, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": registry["summary"]["status"],
            "output": args.output,
            "universal_model_provider_registry_hash": registry[
                "universal_model_provider_registry_hash"
            ],
            "registry_source_count": registry["summary"]["registry_source_count"],
            "provider_namespace_count": registry["summary"][
                "provider_namespace_count"
            ],
            "model_route_class_count": registry["summary"][
                "model_route_class_count"
            ],
            "declared_model_route_count": registry["summary"][
                "declared_model_route_count"
            ],
            "failed_check_count": registry["summary"]["failure_mode_count"],
        }
    else:
        result = registry
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if registry["summary"]["status"] == "ready" else 1


def run_verify_universal_model_provider_registry(args: argparse.Namespace) -> int:
    registry_input = load_universal_model_provider_registry_input(
        args.registry_input
    )
    registry = json.loads(Path(args.registry).read_text(encoding="utf-8"))
    errors = verify_universal_model_provider_registry(
        registry_input,
        registry,
        signing_secret=args.signing_secret,
    )
    result = {
        "registry_input": args.registry_input,
        "registry": args.registry,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_model_provider_registry_hash": registry.get(
            "universal_model_provider_registry_hash", ""
        ),
        "summary": registry.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_source_footer_enforcement_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_source_footer_enforcement_contract_input(
        args.contract_input
    )
    contract = make_universal_source_footer_enforcement_contract(
        contract_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(contract, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": contract["summary"]["status"],
            "output": args.output,
            "universal_source_footer_enforcement_contract_hash": contract[
                "universal_source_footer_enforcement_contract_hash"
            ],
            "declared_model_route_count": contract["summary"][
                "declared_model_route_count"
            ],
            "ready_route_enforcement_count": contract["summary"][
                "ready_route_enforcement_count"
            ],
            "response_surface_count": contract["summary"][
                "response_surface_count"
            ],
            "failed_check_count": contract["summary"]["failure_mode_count"],
        }
    else:
        result = contract
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if contract["summary"]["status"] == "ready" else 1


def run_verify_universal_source_footer_enforcement_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_source_footer_enforcement_contract_input(
        args.contract_input
    )
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    errors = verify_universal_source_footer_enforcement_contract(
        contract_input,
        contract,
        signing_secret=args.signing_secret,
    )
    result = {
        "contract_input": args.contract_input,
        "contract": args.contract,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_source_footer_enforcement_contract_hash": contract.get(
            "universal_source_footer_enforcement_contract_hash", ""
        ),
        "summary": contract.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_provider_catalog_coverage_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_provider_catalog_coverage_contract_input(
        args.contract_input
    )
    contract = make_universal_provider_catalog_coverage_contract(
        contract_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(contract, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": contract["summary"]["status"],
            "output": args.output,
            "universal_provider_catalog_coverage_contract_hash": contract[
                "universal_provider_catalog_coverage_contract_hash"
            ],
            "catalog_channel_count": contract["summary"][
                "catalog_channel_count"
            ],
            "discovered_model_count": contract["summary"][
                "discovered_model_count"
            ],
            "catalog_covered_route_count": contract["summary"][
                "catalog_covered_route_count"
            ],
            "failed_check_count": contract["summary"]["failure_mode_count"],
        }
    else:
        result = contract
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if contract["summary"]["status"] == "ready" else 1


def run_verify_universal_provider_catalog_coverage_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_provider_catalog_coverage_contract_input(
        args.contract_input
    )
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    errors = verify_universal_provider_catalog_coverage_contract(
        contract_input,
        contract,
        signing_secret=args.signing_secret,
    )
    result = {
        "contract_input": args.contract_input,
        "contract": args.contract,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_provider_catalog_coverage_contract_hash": contract.get(
            "universal_provider_catalog_coverage_contract_hash", ""
        ),
        "summary": contract.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_runtime_route_binding_contract(args: argparse.Namespace) -> int:
    contract_input = load_universal_runtime_route_binding_contract_input(
        args.contract_input
    )
    contract = make_universal_runtime_route_binding_contract(
        contract_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(contract, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": contract["summary"]["status"],
            "output": args.output,
            "universal_runtime_route_binding_contract_hash": contract[
                "universal_runtime_route_binding_contract_hash"
            ],
            "catalog_covered_route_count": contract["summary"][
                "catalog_covered_route_count"
            ],
            "ready_runtime_route_binding_count": contract["summary"][
                "ready_runtime_route_binding_count"
            ],
            "runtime_surface_count": contract["summary"]["runtime_surface_count"],
            "failed_check_count": contract["summary"]["failure_mode_count"],
        }
    else:
        result = contract
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if contract["summary"]["status"] == "ready" else 1


def run_verify_universal_runtime_route_binding_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_runtime_route_binding_contract_input(
        args.contract_input
    )
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    errors = verify_universal_runtime_route_binding_contract(
        contract_input,
        contract,
        signing_secret=args.signing_secret,
    )
    result = {
        "contract_input": args.contract_input,
        "contract": args.contract,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_runtime_route_binding_contract_hash": contract.get(
            "universal_runtime_route_binding_contract_hash", ""
        ),
        "summary": contract.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_verified_source_footer_contract(args: argparse.Namespace) -> int:
    contract_input = load_universal_verified_source_footer_contract_input(
        args.contract_input
    )
    contract = make_universal_verified_source_footer_contract(
        contract_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(contract, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": contract["summary"]["status"],
            "output": args.output,
            "universal_verified_source_footer_contract_hash": contract[
                "universal_verified_source_footer_contract_hash"
            ],
            "verified_footer_row_count": contract["summary"][
                "verified_footer_row_count"
            ],
            "support_dimension_count": contract["summary"][
                "support_dimension_count"
            ],
            "footer_response_surface_count": contract["summary"][
                "footer_response_surface_count"
            ],
            "failed_check_count": contract["summary"]["failure_mode_count"],
        }
    else:
        result = contract
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if contract["summary"]["status"] == "ready" else 1


def run_verify_universal_verified_source_footer_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_verified_source_footer_contract_input(
        args.contract_input
    )
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    errors = verify_universal_verified_source_footer_contract(
        contract_input,
        contract,
        signing_secret=args.signing_secret,
    )
    result = {
        "contract_input": args.contract_input,
        "contract": args.contract,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_verified_source_footer_contract_hash": contract.get(
            "universal_verified_source_footer_contract_hash", ""
        ),
        "summary": contract.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_model_capability_coverage_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_model_capability_coverage_contract_input(
        args.contract_input
    )
    contract = make_universal_model_capability_coverage_contract(
        contract_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(contract, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": contract["summary"]["status"],
            "output": args.output,
            "universal_model_capability_coverage_contract_hash": contract[
                "universal_model_capability_coverage_contract_hash"
            ],
            "model_capability_count": contract["summary"][
                "model_capability_count"
            ],
            "modality_pair_count": contract["summary"]["modality_pair_count"],
            "operation_surface_count": contract["summary"][
                "operation_surface_count"
            ],
            "catalog_covered_route_count": contract["summary"][
                "catalog_covered_route_count"
            ],
            "failed_check_count": contract["summary"]["failure_mode_count"],
        }
    else:
        result = contract
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if contract["summary"]["status"] == "ready" else 1


def run_verify_universal_model_capability_coverage_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_model_capability_coverage_contract_input(
        args.contract_input
    )
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    errors = verify_universal_model_capability_coverage_contract(
        contract_input,
        contract,
        signing_secret=args.signing_secret,
    )
    result = {
        "contract_input": args.contract_input,
        "contract": args.contract,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_model_capability_coverage_contract_hash": contract.get(
            "universal_model_capability_coverage_contract_hash", ""
        ),
        "summary": contract.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_live_capability_discovery_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_live_capability_discovery_contract_input(
        args.contract_input
    )
    contract = make_universal_live_capability_discovery_contract(
        contract_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(contract, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": contract["summary"]["status"],
            "output": args.output,
            "universal_live_capability_discovery_contract_hash": contract[
                "universal_live_capability_discovery_contract_hash"
            ],
            "provider_family_count": contract["summary"]["provider_family_count"],
            "discovery_channel_count": contract["summary"][
                "discovery_channel_count"
            ],
            "capability_discovery_count": contract["summary"][
                "capability_discovery_count"
            ],
            "l181_route_count": contract["summary"]["l181_route_count"],
            "failed_check_count": contract["summary"]["failure_mode_count"],
        }
    else:
        result = contract
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if contract["summary"]["status"] == "ready" else 1


def run_verify_universal_live_capability_discovery_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_live_capability_discovery_contract_input(
        args.contract_input
    )
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    errors = verify_universal_live_capability_discovery_contract(
        contract_input,
        contract,
        signing_secret=args.signing_secret,
    )
    result = {
        "contract_input": args.contract_input,
        "contract": args.contract,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_live_capability_discovery_contract_hash": contract.get(
            "universal_live_capability_discovery_contract_hash", ""
        ),
        "summary": contract.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_native_source_annotation_contract(args: argparse.Namespace) -> int:
    contract_input = load_universal_native_source_annotation_contract_input(
        args.contract_input
    )
    contract = make_universal_native_source_annotation_contract(
        contract_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(contract, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": contract["summary"]["status"],
            "output": args.output,
            "universal_native_source_annotation_contract_hash": contract[
                "universal_native_source_annotation_contract_hash"
            ],
            "native_annotation_format_count": contract["summary"][
                "native_annotation_format_count"
            ],
            "normalization_field_count": contract["summary"][
                "normalization_field_count"
            ],
            "l182_route_count": contract["summary"]["l182_route_count"],
            "failed_check_count": contract["summary"]["failure_mode_count"],
        }
    else:
        result = contract
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if contract["summary"]["status"] == "ready" else 1


def run_verify_universal_native_source_annotation_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_native_source_annotation_contract_input(
        args.contract_input
    )
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    errors = verify_universal_native_source_annotation_contract(
        contract_input,
        contract,
        signing_secret=args.signing_secret,
    )
    result = {
        "contract_input": args.contract_input,
        "contract": args.contract,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_native_source_annotation_contract_hash": contract.get(
            "universal_native_source_annotation_contract_hash", ""
        ),
        "summary": contract.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_claim_evidence_footer_verification_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_claim_evidence_footer_verification_contract_input(
        args.contract_input
    )
    contract = make_universal_claim_evidence_footer_verification_contract(
        contract_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(contract, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": contract["summary"]["status"],
            "output": args.output,
            "universal_claim_evidence_footer_verification_contract_hash": contract[
                "universal_claim_evidence_footer_verification_contract_hash"
            ],
            "verification_dimension_count": contract["summary"][
                "verification_dimension_count"
            ],
            "verified_footer_field_count": contract["summary"][
                "verified_footer_field_count"
            ],
            "l183_route_count": contract["summary"]["l183_route_count"],
            "failed_check_count": contract["summary"]["failure_mode_count"],
        }
    else:
        result = contract
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if contract["summary"]["status"] == "ready" else 1


def run_verify_universal_claim_evidence_footer_verification_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_claim_evidence_footer_verification_contract_input(
        args.contract_input
    )
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    errors = verify_universal_claim_evidence_footer_verification_contract(
        contract_input,
        contract,
        signing_secret=args.signing_secret,
    )
    result = {
        "contract_input": args.contract_input,
        "contract": args.contract,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_claim_evidence_footer_verification_contract_hash": contract.get(
            "universal_claim_evidence_footer_verification_contract_hash", ""
        ),
        "summary": contract.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_provider_meter_normalization_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_provider_meter_normalization_contract_input(
        args.contract_input
    )
    contract = make_universal_provider_meter_normalization_contract(
        contract_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(contract, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": contract["summary"]["status"],
            "output": args.output,
            "universal_provider_meter_normalization_contract_hash": contract[
                "universal_provider_meter_normalization_contract_hash"
            ],
            "provider_meter_surface_count": contract["summary"][
                "provider_meter_surface_count"
            ],
            "normalized_meter_field_count": contract["summary"][
                "normalized_meter_field_count"
            ],
            "route_count": contract["summary"]["route_count"],
            "failed_check_count": contract["summary"]["failure_mode_count"],
        }
    else:
        result = contract
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if contract["summary"]["status"] == "ready" else 1


def run_verify_universal_provider_meter_normalization_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_provider_meter_normalization_contract_input(
        args.contract_input
    )
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    errors = verify_universal_provider_meter_normalization_contract(
        contract_input,
        contract,
        signing_secret=args.signing_secret,
    )
    result = {
        "contract_input": args.contract_input,
        "contract": args.contract,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_provider_meter_normalization_contract_hash": contract.get(
            "universal_provider_meter_normalization_contract_hash", ""
        ),
        "summary": contract.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_universal_provider_response_state_normalization_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_provider_response_state_normalization_contract_input(
        args.contract_input
    )
    contract = make_universal_provider_response_state_normalization_contract(
        contract_input,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(contract, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": contract["summary"]["status"],
            "output": args.output,
            "universal_provider_response_state_normalization_contract_hash": contract[
                "universal_provider_response_state_normalization_contract_hash"
            ],
            "provider_response_state_surface_count": contract["summary"][
                "provider_response_state_surface_count"
            ],
            "normalized_response_state_field_count": contract["summary"][
                "normalized_response_state_field_count"
            ],
            "route_count": contract["summary"]["route_count"],
            "failed_check_count": contract["summary"]["failure_mode_count"],
        }
    else:
        result = contract
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if contract["summary"]["status"] == "ready" else 1


def run_verify_universal_provider_response_state_normalization_contract(
    args: argparse.Namespace,
) -> int:
    contract_input = load_universal_provider_response_state_normalization_contract_input(
        args.contract_input
    )
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    errors = verify_universal_provider_response_state_normalization_contract(
        contract_input,
        contract,
        signing_secret=args.signing_secret,
    )
    result = {
        "contract_input": args.contract_input,
        "contract": args.contract,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "universal_provider_response_state_normalization_contract_hash": contract.get(
            "universal_provider_response_state_normalization_contract_hash", ""
        ),
        "summary": contract.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_publication_monitor(args: argparse.Namespace) -> int:
    artifacts = _load_assurance_artifacts(args.artifact)
    previous_report = (
        json.loads(Path(args.previous_monitor).read_text(encoding="utf-8"))
        if args.previous_monitor
        else None
    )
    report = make_publication_monitor_report(
        artifacts,
        previous_report=previous_report,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "publication_monitor_hash": report["publication_monitor_hash"],
            "checkpoint_count": report["summary"]["checkpoint_count"],
            "artifact_count": report["summary"]["artifact_count"],
            "current_certification_level": report["summary"][
                "current_certification_level"
            ],
            "changed_artifact_count": report["summary"]["changed_artifact_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_publication_monitor(args: argparse.Namespace) -> int:
    artifacts = _load_assurance_artifacts(args.artifact)
    report = json.loads(Path(args.monitor).read_text(encoding="utf-8"))
    previous_report = (
        json.loads(Path(args.previous_monitor).read_text(encoding="utf-8"))
        if args.previous_monitor
        else None
    )
    errors = verify_publication_monitor_report(
        report,
        artifacts,
        previous_report=previous_report,
        signing_secret=args.signing_secret,
    )
    result = {
        "monitor": args.monitor,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "publication_monitor_hash": report.get("publication_monitor_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def _load_publication_monitors(paths: list[str] | None) -> list[dict[str, object]]:
    return [
        json.loads(Path(path).read_text(encoding="utf-8"))
        for path in (paths or [])
    ]


def _load_witnesses(specs: list[str] | None) -> list[tuple[str, str]]:
    witnesses: list[tuple[str, str]] = []
    for spec in specs or []:
        if ":" not in spec:
            raise ValueError("witness spec must be witness_id:secret")
        witness_id, secret = spec.split(":", 1)
        if not witness_id or not secret:
            raise ValueError("witness spec must be witness_id:secret")
        witnesses.append((witness_id, secret))
    return witnesses


def _load_principals(specs: list[str] | None) -> list[tuple[str, str, str]]:
    principals: list[tuple[str, str, str]] = []
    for spec in specs or []:
        parts = spec.split(":", 2)
        if len(parts) != 3:
            raise ValueError("principal spec must be principal_id:role:secret")
        principal_id, role, secret = parts
        if not principal_id or not role or not secret:
            raise ValueError("principal spec must be principal_id:role:secret")
        principals.append((principal_id, role, secret))
    return principals


def _load_rotations(specs: list[str] | None) -> list[tuple[str, str, str, str]]:
    rotations: list[tuple[str, str, str, str]] = []
    for spec in specs or []:
        parts = spec.split(":", 3)
        if len(parts) != 4:
            raise ValueError(
                "rotation spec must be principal_id:role:previous_secret:new_secret"
            )
        principal_id, role, previous_secret, new_secret = parts
        if not principal_id or not role or not previous_secret or not new_secret:
            raise ValueError(
                "rotation spec must be principal_id:role:previous_secret:new_secret"
            )
        rotations.append((principal_id, role, previous_secret, new_secret))
    return rotations


def run_publication_witness(args: argparse.Namespace) -> int:
    monitors = _load_publication_monitors(args.monitor)
    witnesses = _load_witnesses(args.witness)
    report = make_publication_witness_report(
        monitors,
        witnesses=witnesses,
        required_quorum=args.required_quorum,
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "publication_witness_hash": report["publication_witness_hash"],
            "monitor_count": report["summary"]["monitor_count"],
            "witness_count": report["summary"]["witness_count"],
            "required_quorum": report["summary"]["required_quorum"],
            "equivocation_count": report["summary"]["equivocation_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_publication_witness(args: argparse.Namespace) -> int:
    monitors = _load_publication_monitors(args.monitor)
    witnesses = _load_witnesses(args.witness)
    report = json.loads(Path(args.witness_report).read_text(encoding="utf-8"))
    errors = verify_publication_witness_report(
        report,
        monitors,
        witnesses=witnesses,
        signing_secret=args.signing_secret,
    )
    result = {
        "witness_report": args.witness_report,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "publication_witness_hash": report.get("publication_witness_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_trust_registry(args: argparse.Namespace) -> int:
    artifacts = _load_assurance_artifacts(args.artifact)
    publication_witnesses = _load_json_many(args.publication_witness)
    report = make_trust_registry_report(
        artifacts,
        principals=_load_principals(args.principal),
        publication_witnesses=publication_witnesses,
        rotations=_load_rotations(args.rotation),
        revoked_keys=_load_principals(args.revoked_key),
        issuer=args.issuer,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": report["summary"]["status"],
            "output": args.output,
            "trust_registry_hash": report["trust_registry_hash"],
            "principal_count": report["summary"]["principal_count"],
            "artifact_binding_count": report["summary"]["artifact_binding_count"],
            "witness_binding_count": report["summary"]["witness_binding_count"],
        }
    else:
        result = report
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "ready" else 1


def run_verify_trust_registry(args: argparse.Namespace) -> int:
    artifacts = _load_assurance_artifacts(args.artifact)
    publication_witnesses = _load_json_many(args.publication_witness)
    report = json.loads(Path(args.registry).read_text(encoding="utf-8"))
    errors = verify_trust_registry_report(
        report,
        artifacts,
        principals=_load_principals(args.principal),
        publication_witnesses=publication_witnesses,
        rotations=_load_rotations(args.rotation),
        revoked_keys=_load_principals(args.revoked_key),
        signing_secret=args.signing_secret,
    )
    result = {
        "registry": args.registry,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "trust_registry_hash": report.get("trust_registry_hash", ""),
        "summary": report.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_certification_attestation(args: argparse.Namespace) -> int:
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    attestation = make_certification_attestation(
        certification_report,
        certifier_id=args.certifier_id,
        target_provider=args.target_provider,
        issuer=args.issuer,
        valid_until=args.valid_until,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(attestation, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": attestation["summary"]["status"],
            "output": args.output,
            "attestation_hash": attestation["attestation_hash"],
            "certification_report_hash": attestation["subject"][
                "certification_report_hash"
            ],
            "attested_highest_level": attestation["summary"][
                "attested_highest_level"
            ],
            "target_certification_level": attestation["summary"][
                "target_certification_level"
            ],
        }
    else:
        result = attestation
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if attestation["summary"]["status"] == "attested" else 1


def run_verify_certification_attestation(args: argparse.Namespace) -> int:
    certification_report = json.loads(
        Path(args.certification_report).read_text(encoding="utf-8")
    )
    attestation = json.loads(Path(args.attestation).read_text(encoding="utf-8"))
    errors = verify_certification_attestation(
        attestation,
        certification_report,
        signing_secret=args.signing_secret,
    )
    result = {
        "attestation": args.attestation,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "attestation_hash": attestation.get("attestation_hash", ""),
        "summary": attestation.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def _load_audit_attestation_inputs(args: argparse.Namespace) -> dict[str, dict[str, object] | None]:
    inputs: dict[str, dict[str, object] | None] = {
        "provider_card": json.loads(Path(args.provider_card).read_text(encoding="utf-8")),
        "certification_report": json.loads(
            Path(args.certification_report).read_text(encoding="utf-8")
        ),
        "integration_profile": json.loads(
            Path(args.integration_profile).read_text(encoding="utf-8")
        ),
        "discovery_manifest": json.loads(
            Path(args.discovery_manifest).read_text(encoding="utf-8")
        ),
        "assurance_bundle": json.loads(
            Path(args.assurance_bundle).read_text(encoding="utf-8")
        ),
        "response_envelope": json.loads(
            Path(args.response_envelope).read_text(encoding="utf-8")
        ),
        "source_confidence_report": json.loads(
            Path(args.source_confidence_report).read_text(encoding="utf-8")
        ),
        "citation_footer_contract": json.loads(
            Path(args.citation_footer_contract).read_text(encoding="utf-8")
        ),
        "clearinghouse_report": json.loads(
            Path(args.clearinghouse_report).read_text(encoding="utf-8")
        ),
        "remittance_report": json.loads(
            Path(args.remittance_report).read_text(encoding="utf-8")
        ),
    }
    if getattr(args, "revenue_allocation_report", None):
        inputs["revenue_allocation_report"] = json.loads(
            Path(args.revenue_allocation_report).read_text(encoding="utf-8")
        )
    if getattr(args, "finance_ledger_attestation", None):
        inputs["finance_ledger_attestation"] = json.loads(
            Path(args.finance_ledger_attestation).read_text(encoding="utf-8")
        )
    if getattr(args, "payment_execution_report", None):
        inputs["payment_execution_report"] = json.loads(
            Path(args.payment_execution_report).read_text(encoding="utf-8")
        )
    if getattr(args, "payment_processor_records", None):
        inputs["payment_processor_records"] = json.loads(
            Path(args.payment_processor_records).read_text(encoding="utf-8")
        )
    if getattr(args, "certification_attestation", None):
        inputs["certification_attestation"] = json.loads(
            Path(args.certification_attestation).read_text(encoding="utf-8")
        )
    return inputs


def run_audit_attestation(args: argparse.Namespace) -> int:
    inputs = _load_audit_attestation_inputs(args)
    attestation = make_audit_attestation(
        **inputs,
        auditor_id=args.auditor_id,
        auditor_name=args.auditor_name,
        verifier_id=args.verifier_id,
        issuer=args.issuer,
        audit_period_start=args.audit_period_start,
        audit_period_end=args.audit_period_end,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(attestation, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": attestation["summary"]["status"],
            "output": args.output,
            "attestation_hash": attestation["attestation_hash"],
            "audited_artifact_count": attestation["summary"][
                "audited_artifact_count"
            ],
            "failed_check_count": attestation["summary"]["failed_check_count"],
            "target_certification_level": attestation["summary"][
                "target_certification_level"
            ],
        }
    else:
        result = attestation
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if attestation["summary"]["status"] == "attested" else 1


def run_verify_audit_attestation(args: argparse.Namespace) -> int:
    inputs = _load_audit_attestation_inputs(args)
    attestation = json.loads(Path(args.attestation).read_text(encoding="utf-8"))
    errors = verify_audit_attestation(
        attestation,
        **inputs,
        signing_secret=args.signing_secret,
    )
    result = {
        "attestation": args.attestation,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "attestation_hash": attestation.get("attestation_hash", ""),
        "summary": attestation.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_policy_manifest(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    manifest = engine.policy_manifest()
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def run_creator_license_contract(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    contract = make_creator_license_contract(
        creators=engine.creators,
        works=engine.works,
        issuer=args.issuer,
        provider=args.provider,
        effective_at=args.effective_at,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(contract, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result = {
            "status": contract["summary"]["status"],
            "output": args.output,
            "contract_hash": contract["contract_hash"],
            "term_count": contract["summary"]["term_count"],
            "active_term_count": contract["summary"]["active_term_count"],
            "revoked_term_count": contract["summary"]["revoked_term_count"],
        }
    else:
        result = contract
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if contract["summary"]["status"] == "ready" else 1


def run_verify_creator_license_contract(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    errors = verify_creator_license_contract(
        contract,
        creators=engine.creators,
        works=engine.works,
        signing_secret=args.signing_secret,
    )
    result = {
        "contract": args.contract,
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "contract_hash": contract.get("contract_hash", ""),
        "summary": contract.get("summary", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def run_policy_check(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    if args.chunk_id:
        chunk = engine.chunk_by_id.get(args.chunk_id)
        if not chunk:
            raise SystemExit(f"chunk {args.chunk_id} not found")
        decision = engine.policy_engine.evaluate_chunk(
            chunk,
            args.use,
            jurisdiction=args.jurisdiction,
            creator_pool_rate=engine.creator_pool_rate,
        )
    else:
        work = engine.works.get(args.work_id)
        if not work:
            raise SystemExit(f"work {args.work_id} not found")
        decision = engine.policy_engine.evaluate_work(
            work,
            args.use,
            jurisdiction=args.jurisdiction,
            creator_pool_rate=engine.creator_pool_rate,
        )
    result = decision.to_dict()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if decision.allowed else 1


def _event_from_ledger(path: str | Path, event_id: str) -> UsageEvent:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for event_data in data.get("events", []):
        if event_data.get("event_id") == event_id:
            return UsageEvent.from_dict(event_data)
    raise SystemExit(f"event {event_id} not found in ledger {path}")


def run_conformance(args: argparse.Namespace) -> int:
    ledger_data = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    event_id = args.event_id or receipt["payload"]["event"]["event_id"]
    event = _event_from_ledger(args.ledger, event_id)
    proof = (
        json.loads(Path(args.proof).read_text(encoding="utf-8"))
        if args.proof
        else None
    )
    trace = (
        json.loads(Path(args.trace).read_text(encoding="utf-8"))
        if args.trace
        else None
    )
    statement = (
        json.loads(Path(args.statement).read_text(encoding="utf-8"))
        if args.statement
        else None
    )
    statement_receipts = _load_json_many(args.statement_receipt) if args.statement_receipt else None
    statement_traces = _load_json_many(args.statement_trace) if args.statement_trace else None
    transparency_log = TransparencyLog.read_json(args.log) if args.log else None
    result = verify_conformance_bundle(
        event=event,
        receipt=receipt,
        signing_secret=args.signing_secret,
        transparency_log=transparency_log,
        proof=proof,
        trace_exchange=trace,
        ledger_data=ledger_data,
        royalty_statement=statement,
        statement_receipts=statement_receipts,
        statement_traces=statement_traces,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "ok" else 1


def run_certify(args: argparse.Namespace) -> int:
    report = run_certification(
        args.corpus,
        restricted_corpus_path=args.restricted_corpus,
        conflict_corpus_path=args.conflict_corpus,
        signing_secret=args.signing_secret,
        jurisdiction=args.jurisdiction,
        creator_pool_rate=Decimal(args.creator_pool_rate),
        top_k=args.top_k,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["summary"]["status"] == "passed" else 1


def audit_ledger(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    data = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    failures: dict[str, list[str]] = {}
    for event_data in data.get("events", []):
        event = UsageEvent.from_dict(event_data)
        errors = engine.audit_event(event)
        if errors:
            failures[event.event_id] = errors

    result = {
        "ledger": args.ledger,
        "events_checked": len(data.get("events", [])),
        "status": "ok" if not failures else "failed",
        "failures": failures,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if failures else 0


def run_registry_audit(args: argparse.Namespace) -> int:
    engine = _engine_from_args(args)
    report = engine.registry_report
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    open_conflicts = int(report.get("summary", {}).get("open_conflict_count", 0))
    return 1 if args.fail_on_conflict and open_conflicts else 0


def run_resolve_escrow(args: argparse.Namespace) -> int:
    ledger_data = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    resolution = load_resolution(args.resolution)
    report = resolve_registry_escrow(
        ledger_data,
        resolution,
        signing_secret=args.signing_secret,
    )
    verify_errors = verify_escrow_resolution(
        ledger_data,
        report,
        signing_secret=args.signing_secret,
    )
    report["verification_errors"] = verify_errors
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["status"] != "ok" or verify_errors else 0


def run_interop(args: argparse.Namespace) -> int:
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    settlement_report = (
        json.loads(Path(args.settlement_report).read_text(encoding="utf-8"))
        if args.settlement_report
        else None
    )
    bundle = make_interop_bundle(
        receipt,
        settlement_report=settlement_report,
        signing_secret=args.signing_secret,
    )
    verification_errors = verify_interop_bundle(
        bundle,
        receipt,
        settlement_report=settlement_report,
        signing_secret=args.signing_secret,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(bundle, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    result = {
        "status": "ok" if not verification_errors else "failed",
        "bundle": bundle,
        "verification_errors": verification_errors,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if verification_errors else 0


def run_verify_interop(args: argparse.Namespace) -> int:
    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    settlement_report = (
        json.loads(Path(args.settlement_report).read_text(encoding="utf-8"))
        if args.settlement_report
        else None
    )
    errors = verify_interop_bundle(
        bundle,
        receipt,
        settlement_report=settlement_report,
        signing_secret=args.signing_secret,
    )
    result = {
        "bundle": args.bundle,
        "status": "ok" if not errors else "failed",
        "errors": errors,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


def _default_corpus_path() -> str:
    return str(resources.files("rdllm.data").joinpath("sample_corpus.json"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Royalty Driven LLM prototype")
    parser.add_argument(
        "--corpus",
        default=_default_corpus_path(),
        help="Path to creator/work corpus JSON.",
    )
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--gross-revenue", default="1.00")
    parser.add_argument("--creator-pool-rate", default="0.55")
    parser.add_argument("--jurisdiction", default="GLOBAL")
    parser.add_argument(
        "--attestations",
        help="Optional JSON file of ownership attestations to bind into registry checks.",
    )
    parser.add_argument(
        "--registry-report",
        help="Optional precomputed registry report JSON to enforce during settlement.",
    )
    parser.add_argument(
        "--enforce-registry",
        action="store_true",
        help="Route payout to registry-dispute escrow when matched works have open ownership conflicts.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="Run the bundled demo prompts.")
    demo.add_argument("--ledger", help="Optional path to write the demo ledger JSON.")
    demo.set_defaults(func=run_demo)

    once = subparsers.add_parser("run", help="Run one prompt.")
    once.add_argument("prompt")
    once.add_argument(
        "--output",
        help="Externally generated text to attribute instead of using the demo composer.",
    )
    once.add_argument("--ledger", help="Optional path to write a one-event ledger JSON.")
    once.set_defaults(func=run_once)

    answer = subparsers.add_parser(
        "answer", help="Print a grounded answer with a source footer."
    )
    answer.add_argument("prompt")
    answer.add_argument(
        "--output",
        help="Externally generated text to source and render with a footer.",
    )
    answer.set_defaults(func=run_answer)

    answer_card = subparsers.add_parser(
        "answer-card",
        help="Create a public answer provenance card bound to footer, receipt, and trace.",
    )
    answer_card.add_argument("prompt", nargs="?")
    answer_card.add_argument(
        "--output",
        help="Externally generated text to source and render with a footer.",
    )
    answer_card.add_argument("--ledger", help="Existing ledger to read an event from.")
    answer_card.add_argument("--event-id")
    answer_card.add_argument("--ledger-output", help="Write a generated event ledger.")
    answer_card.add_argument("--receipt", help="Receipt path to read or write.")
    answer_card.add_argument("--trace", help="Trace path to read or write.")
    answer_card.add_argument("--card", help="Output answer provenance card path.")
    answer_card.add_argument("--issuer", default="rdllm-local-demo")
    answer_card.add_argument("--model-id", default="model:unspecified")
    answer_card.add_argument("--model-version", default="unknown")
    answer_card.add_argument("--route-id", default="route:default")
    answer_card.add_argument("--signing-secret")
    answer_card.set_defaults(func=run_answer_card)

    verify_answer_card = subparsers.add_parser(
        "verify-answer-card",
        help="Verify an answer provenance card against a ledger event.",
    )
    verify_answer_card.add_argument("--ledger", required=True)
    verify_answer_card.add_argument("--card", required=True)
    verify_answer_card.add_argument("--event-id")
    verify_answer_card.add_argument("--receipt")
    verify_answer_card.add_argument("--trace")
    verify_answer_card.add_argument("--signing-secret")
    verify_answer_card.set_defaults(func=run_verify_answer_card)

    source_verification = subparsers.add_parser(
        "source-verification",
        help="Create a public source materialization report for cited answer sources.",
    )
    source_verification.add_argument("--ledger", required=True)
    source_verification.add_argument("--event-id")
    source_verification.add_argument(
        "--answer-card",
        help="Optional answer provenance card to bind into the source report.",
    )
    source_verification.add_argument("--issuer", default="rdllm-local-demo")
    source_verification.add_argument("--signing-secret")
    source_verification.add_argument("--output")
    source_verification.set_defaults(func=run_source_verification)

    verify_source_verification = subparsers.add_parser(
        "verify-source-verification",
        help="Verify a source materialization report against corpus and ledger.",
    )
    verify_source_verification.add_argument("--ledger", required=True)
    verify_source_verification.add_argument("--report", required=True)
    verify_source_verification.add_argument("--event-id")
    verify_source_verification.add_argument("--answer-card")
    verify_source_verification.add_argument("--signing-secret")
    verify_source_verification.set_defaults(func=run_verify_source_verification)

    source_confidence = subparsers.add_parser(
        "source-confidence-report",
        help="Create a public confidence report for answer footer sources and claim evidence.",
    )
    source_confidence.add_argument("--answer-card", required=True)
    source_confidence.add_argument("--source-report", required=True)
    source_confidence.add_argument("--creator-license-contract", required=True)
    source_confidence.add_argument("--issuer", default="rdllm-local-demo")
    source_confidence.add_argument("--signing-secret")
    source_confidence.add_argument("--output")
    source_confidence.set_defaults(func=run_source_confidence_report)

    verify_source_confidence = subparsers.add_parser(
        "verify-source-confidence-report",
        help="Verify a source confidence report using public RDLLM proof artifacts.",
    )
    verify_source_confidence.add_argument("--report", required=True)
    verify_source_confidence.add_argument("--answer-card", required=True)
    verify_source_confidence.add_argument("--source-report", required=True)
    verify_source_confidence.add_argument("--creator-license-contract", required=True)
    verify_source_confidence.add_argument("--signing-secret")
    verify_source_confidence.set_defaults(func=run_verify_source_confidence_report)

    citation_footer = subparsers.add_parser(
        "citation-footer-contract",
        help="Create a verifiable client-rendering contract for a response source footer.",
    )
    citation_footer.add_argument("--response-envelope", required=True)
    citation_footer.add_argument("--issuer", default="rdllm-local-demo")
    citation_footer.add_argument("--signing-secret")
    citation_footer.add_argument("--output")
    citation_footer.set_defaults(func=run_citation_footer_contract)

    verify_citation_footer = subparsers.add_parser(
        "verify-citation-footer-contract",
        help="Verify a citation footer rendering contract against response proofs.",
    )
    verify_citation_footer.add_argument("--contract", required=True)
    verify_citation_footer.add_argument("--response-envelope", required=True)
    verify_citation_footer.add_argument("--signing-secret")
    verify_citation_footer.set_defaults(func=run_verify_citation_footer_contract)

    source_availability = subparsers.add_parser(
        "source-availability-report",
        help="Create a report proving cited footer sources remain reachable or archived.",
    )
    source_availability.add_argument("--ledger", required=True)
    source_availability.add_argument("--event-id")
    source_availability.add_argument("--snapshots", required=True)
    source_availability.add_argument("--answer-card", required=True)
    source_availability.add_argument("--source-report", required=True)
    source_availability.add_argument("--citation-footer-contract", required=True)
    source_availability.add_argument("--issuer", default="rdllm-local-demo")
    source_availability.add_argument("--signing-secret")
    source_availability.add_argument("--output")
    source_availability.set_defaults(func=run_source_availability_report)

    verify_source_availability = subparsers.add_parser(
        "verify-source-availability-report",
        help="Verify a source availability report against corpus, ledger, snapshots, and footer proof.",
    )
    verify_source_availability.add_argument("--ledger", required=True)
    verify_source_availability.add_argument("--event-id")
    verify_source_availability.add_argument("--report", required=True)
    verify_source_availability.add_argument("--snapshots", required=True)
    verify_source_availability.add_argument("--answer-card", required=True)
    verify_source_availability.add_argument("--source-report", required=True)
    verify_source_availability.add_argument("--citation-footer-contract", required=True)
    verify_source_availability.add_argument("--signing-secret")
    verify_source_availability.set_defaults(func=run_verify_source_availability_report)

    evidence_sufficiency = subparsers.add_parser(
        "evidence-sufficiency-report",
        help="Create a report proving cited claim spans are top-ranked sufficient evidence.",
    )
    evidence_sufficiency.add_argument("--ledger", required=True)
    evidence_sufficiency.add_argument("--event-id")
    evidence_sufficiency.add_argument("--answer-card", required=True)
    evidence_sufficiency.add_argument("--source-report", required=True)
    evidence_sufficiency.add_argument("--source-availability-report", required=True)
    evidence_sufficiency.add_argument("--citation-footer-contract", required=True)
    evidence_sufficiency.add_argument("--candidate-limit", type=int, default=5)
    evidence_sufficiency.add_argument("--issuer", default="rdllm-local-demo")
    evidence_sufficiency.add_argument("--signing-secret")
    evidence_sufficiency.add_argument("--output")
    evidence_sufficiency.set_defaults(func=run_evidence_sufficiency_report)

    verify_evidence_sufficiency = subparsers.add_parser(
        "verify-evidence-sufficiency-report",
        help="Verify claim-level evidence sufficiency against corpus, ledger, and public proof artifacts.",
    )
    verify_evidence_sufficiency.add_argument("--ledger", required=True)
    verify_evidence_sufficiency.add_argument("--event-id")
    verify_evidence_sufficiency.add_argument("--report", required=True)
    verify_evidence_sufficiency.add_argument("--answer-card", required=True)
    verify_evidence_sufficiency.add_argument("--source-report", required=True)
    verify_evidence_sufficiency.add_argument("--source-availability-report", required=True)
    verify_evidence_sufficiency.add_argument("--citation-footer-contract", required=True)
    verify_evidence_sufficiency.add_argument("--candidate-limit", type=int, default=5)
    verify_evidence_sufficiency.add_argument("--signing-secret")
    verify_evidence_sufficiency.set_defaults(func=run_verify_evidence_sufficiency_report)

    counterevidence = subparsers.add_parser(
        "counterevidence-report",
        help="Create a report proving cited claims have no unaddressed counterevidence.",
    )
    counterevidence.add_argument("--ledger", required=True)
    counterevidence.add_argument("--event-id")
    counterevidence.add_argument("--answer-card", required=True)
    counterevidence.add_argument("--source-report", required=True)
    counterevidence.add_argument("--source-availability-report", required=True)
    counterevidence.add_argument("--evidence-sufficiency-report", required=True)
    counterevidence.add_argument("--citation-footer-contract", required=True)
    counterevidence.add_argument("--candidate-limit", type=int, default=5)
    counterevidence.add_argument("--issuer", default="rdllm-local-demo")
    counterevidence.add_argument("--signing-secret")
    counterevidence.add_argument("--output")
    counterevidence.set_defaults(func=run_counterevidence_report)

    verify_counterevidence = subparsers.add_parser(
        "verify-counterevidence-report",
        help="Verify counterevidence adjudication against corpus, ledger, and public proof artifacts.",
    )
    verify_counterevidence.add_argument("--ledger", required=True)
    verify_counterevidence.add_argument("--event-id")
    verify_counterevidence.add_argument("--report", required=True)
    verify_counterevidence.add_argument("--answer-card", required=True)
    verify_counterevidence.add_argument("--source-report", required=True)
    verify_counterevidence.add_argument("--source-availability-report", required=True)
    verify_counterevidence.add_argument("--evidence-sufficiency-report", required=True)
    verify_counterevidence.add_argument("--citation-footer-contract", required=True)
    verify_counterevidence.add_argument("--candidate-limit", type=int, default=5)
    verify_counterevidence.add_argument("--signing-secret")
    verify_counterevidence.set_defaults(func=run_verify_counterevidence_report)

    answer_coverage = subparsers.add_parser(
        "answer-claim-coverage-report",
        help="Create a report proving every public answer claim maps to a verified claim row.",
    )
    answer_coverage.add_argument("--response-envelope", required=True)
    answer_coverage.add_argument("--issuer", default="rdllm-local-demo")
    answer_coverage.add_argument("--signing-secret")
    answer_coverage.add_argument("--output")
    answer_coverage.set_defaults(func=run_answer_claim_coverage_report)

    verify_answer_coverage = subparsers.add_parser(
        "verify-answer-claim-coverage-report",
        help="Verify answer claim coverage against a response envelope and embedded proofs.",
    )
    verify_answer_coverage.add_argument("--report", required=True)
    verify_answer_coverage.add_argument("--response-envelope", required=True)
    verify_answer_coverage.add_argument("--signing-secret")
    verify_answer_coverage.set_defaults(func=run_verify_answer_claim_coverage_report)

    context_closure = subparsers.add_parser(
        "generation-context-closure-report",
        help="Create a report proving cited claims were present in generation context.",
    )
    context_closure.add_argument("--response-envelope", required=True)
    context_closure.add_argument("--trace-exchange", required=True)
    context_closure.add_argument("--context-blocks")
    context_closure.add_argument("--issuer", default="rdllm-local-demo")
    context_closure.add_argument("--signing-secret")
    context_closure.add_argument("--output")
    context_closure.set_defaults(func=run_generation_context_closure_report)

    verify_context_closure = subparsers.add_parser(
        "verify-generation-context-closure-report",
        help="Verify generation context closure against trace and response proofs.",
    )
    verify_context_closure.add_argument("--report", required=True)
    verify_context_closure.add_argument("--response-envelope", required=True)
    verify_context_closure.add_argument("--trace-exchange", required=True)
    verify_context_closure.add_argument("--context-blocks")
    verify_context_closure.add_argument("--signing-secret")
    verify_context_closure.set_defaults(
        func=run_verify_generation_context_closure_report
    )

    source_boundary = subparsers.add_parser(
        "source-boundary-report",
        help="Create a report proving generation context sources were evidence-only.",
    )
    source_boundary.add_argument("--response-envelope", required=True)
    source_boundary.add_argument("--trace-exchange", required=True)
    source_boundary.add_argument("--issuer", default="rdllm-local-demo")
    source_boundary.add_argument("--signing-secret")
    source_boundary.add_argument("--output")
    source_boundary.set_defaults(func=run_source_boundary_report)

    verify_source_boundary = subparsers.add_parser(
        "verify-source-boundary-report",
        help="Verify source boundary isolation against trace and response proofs.",
    )
    verify_source_boundary.add_argument("--report", required=True)
    verify_source_boundary.add_argument("--response-envelope", required=True)
    verify_source_boundary.add_argument("--trace-exchange", required=True)
    verify_source_boundary.add_argument("--signing-secret")
    verify_source_boundary.set_defaults(func=run_verify_source_boundary_report)

    source_authenticity = subparsers.add_parser(
        "source-authenticity-report",
        help="Create an L64 report proving cited sources are authentic and poisoning-resistant.",
    )
    source_authenticity.add_argument("--source-availability-report", required=True)
    source_authenticity.add_argument("--source-boundary-report", required=True)
    source_authenticity.add_argument("--creator-license-contract", required=True)
    source_authenticity.add_argument("--source-authenticity-signals", required=True)
    source_authenticity.add_argument("--source-confidence-report")
    source_authenticity.add_argument("--output")
    source_authenticity.add_argument("--issuer", default="rdllm-local-demo")
    source_authenticity.add_argument("--signing-secret")
    source_authenticity.set_defaults(func=run_source_authenticity_report)

    verify_source_authenticity = subparsers.add_parser(
        "verify-source-authenticity-report",
        help="Verify an L64 source-authenticity and poisoning-resilience report.",
    )
    verify_source_authenticity.add_argument("--report", required=True)
    verify_source_authenticity.add_argument("--source-availability-report", required=True)
    verify_source_authenticity.add_argument("--source-boundary-report", required=True)
    verify_source_authenticity.add_argument("--creator-license-contract", required=True)
    verify_source_authenticity.add_argument("--source-authenticity-signals", required=True)
    verify_source_authenticity.add_argument("--source-confidence-report")
    verify_source_authenticity.add_argument("--signing-secret")
    verify_source_authenticity.set_defaults(
        func=run_verify_source_authenticity_report
    )

    decision_provenance = subparsers.add_parser(
        "decision-provenance-report",
        help="Create an L62 decision provenance influence graph.",
    )
    decision_provenance.add_argument("--response-envelope", required=True)
    decision_provenance.add_argument("--release-gate", required=True)
    decision_provenance.add_argument("--trace-exchange", required=True)
    decision_provenance.add_argument("--attribution-capsule", required=True)
    decision_provenance.add_argument("--output")
    decision_provenance.add_argument("--issuer", default="rdllm-local-demo")
    decision_provenance.add_argument("--signing-secret")
    decision_provenance.set_defaults(func=run_decision_provenance_report)

    verify_decision_provenance = subparsers.add_parser(
        "verify-decision-provenance-report",
        help="Verify an L62 decision provenance influence graph.",
    )
    verify_decision_provenance.add_argument("--report", required=True)
    verify_decision_provenance.add_argument("--response-envelope", required=True)
    verify_decision_provenance.add_argument("--release-gate", required=True)
    verify_decision_provenance.add_argument("--trace-exchange", required=True)
    verify_decision_provenance.add_argument("--attribution-capsule", required=True)
    verify_decision_provenance.add_argument("--signing-secret")
    verify_decision_provenance.set_defaults(
        func=run_verify_decision_provenance_report
    )

    calibrated_attribution = subparsers.add_parser(
        "calibrated-attribution-report",
        help="Create an L63 calibrated attribution-confidence report.",
    )
    calibrated_attribution.add_argument("--response-envelope", required=True)
    calibrated_attribution.add_argument("--source-confidence-report", required=True)
    calibrated_attribution.add_argument("--evidence-sufficiency-report", required=True)
    calibrated_attribution.add_argument("--provenance-evaluation-report", required=True)
    calibrated_attribution.add_argument("--decision-provenance-report", required=True)
    calibrated_attribution.add_argument("--release-gate", required=True)
    calibrated_attribution.add_argument("--trace-exchange", required=True)
    calibrated_attribution.add_argument("--attribution-capsule", required=True)
    calibrated_attribution.add_argument("--output")
    calibrated_attribution.add_argument("--issuer", default="rdllm-local-demo")
    calibrated_attribution.add_argument("--signing-secret")
    calibrated_attribution.set_defaults(func=run_calibrated_attribution_report)

    verify_calibrated_attribution = subparsers.add_parser(
        "verify-calibrated-attribution-report",
        help="Verify an L63 calibrated attribution-confidence report.",
    )
    verify_calibrated_attribution.add_argument("--report", required=True)
    verify_calibrated_attribution.add_argument("--response-envelope", required=True)
    verify_calibrated_attribution.add_argument("--source-confidence-report", required=True)
    verify_calibrated_attribution.add_argument("--evidence-sufficiency-report", required=True)
    verify_calibrated_attribution.add_argument("--provenance-evaluation-report", required=True)
    verify_calibrated_attribution.add_argument("--decision-provenance-report", required=True)
    verify_calibrated_attribution.add_argument("--release-gate", required=True)
    verify_calibrated_attribution.add_argument("--trace-exchange", required=True)
    verify_calibrated_attribution.add_argument("--attribution-capsule", required=True)
    verify_calibrated_attribution.add_argument("--signing-secret")
    verify_calibrated_attribution.set_defaults(
        func=run_verify_calibrated_attribution_report
    )

    private_audit = subparsers.add_parser(
        "private-audit-challenge",
        help="Create a nonce-bound private audit challenge over hidden receipt paths.",
    )
    private_audit.add_argument("--package", required=True)
    private_audit.add_argument("--receipt", required=True)
    private_audit.add_argument("--auditor-id", required=True)
    private_audit.add_argument("--challenge-nonce", required=True)
    private_audit.add_argument(
        "--path",
        action="append",
        required=True,
        help="Exact selective-disclosure JSON-pointer path to challenge.",
    )
    private_audit.add_argument("--issuer", default="rdllm-local-demo")
    private_audit.add_argument("--signing-secret")
    private_audit.add_argument("--output")
    private_audit.set_defaults(func=run_private_audit_challenge)

    verify_private_audit = subparsers.add_parser(
        "verify-private-audit-challenge",
        help="Verify a private audit challenge against a disclosure package and optional private receipt.",
    )
    verify_private_audit.add_argument("--report", required=True)
    verify_private_audit.add_argument("--package", required=True)
    verify_private_audit.add_argument("--receipt")
    verify_private_audit.add_argument("--signing-secret")
    verify_private_audit.set_defaults(func=run_verify_private_audit_challenge)

    lineage_report = subparsers.add_parser(
        "lineage-report",
        help="Create a derivative-work lineage report with pass-through royalty obligations.",
    )
    lineage_report.add_argument("--ledger", required=True)
    lineage_report.add_argument("--event-id")
    lineage_report.add_argument("--pass-through-rate", default="0.30")
    lineage_report.add_argument("--issuer", default="rdllm-local-demo")
    lineage_report.add_argument("--signing-secret")
    lineage_report.add_argument("--output")
    lineage_report.set_defaults(func=run_lineage_report)

    verify_lineage_report = subparsers.add_parser(
        "verify-lineage-report",
        help="Verify a derivative-work lineage report against corpus and ledger.",
    )
    verify_lineage_report.add_argument("--ledger", required=True)
    verify_lineage_report.add_argument("--report", required=True)
    verify_lineage_report.add_argument("--event-id")
    verify_lineage_report.add_argument("--signing-secret")
    verify_lineage_report.set_defaults(func=run_verify_lineage_report)

    transitive_attribution = subparsers.add_parser(
        "transitive-attribution-report",
        help="Create an anti-laundering report for downstream reuse of a copied RDLLM output.",
    )
    transitive_attribution.add_argument("--upstream-capsule", required=True)
    transitive_attribution.add_argument("--upstream-response-envelope", required=True)
    transitive_attribution.add_argument("--downstream-ledger", required=True)
    transitive_attribution.add_argument("--event-id")
    transitive_attribution.add_argument("--copied-output")
    transitive_attribution.add_argument("--copied-output-file")
    transitive_attribution.add_argument("--pass-through-rate", default="0.70")
    transitive_attribution.add_argument("--issuer", default="rdllm-local-demo")
    transitive_attribution.add_argument("--signing-secret")
    transitive_attribution.add_argument("--output")
    transitive_attribution.set_defaults(func=run_transitive_attribution_report)

    verify_transitive_attribution = subparsers.add_parser(
        "verify-transitive-attribution-report",
        help="Verify a transitive attribution report against upstream capsule and downstream usage.",
    )
    verify_transitive_attribution.add_argument("--report", required=True)
    verify_transitive_attribution.add_argument("--upstream-capsule", required=True)
    verify_transitive_attribution.add_argument(
        "--upstream-response-envelope",
        required=True,
    )
    verify_transitive_attribution.add_argument("--downstream-ledger", required=True)
    verify_transitive_attribution.add_argument("--event-id")
    verify_transitive_attribution.add_argument("--copied-output")
    verify_transitive_attribution.add_argument("--copied-output-file")
    verify_transitive_attribution.add_argument("--signing-secret")
    verify_transitive_attribution.set_defaults(
        func=run_verify_transitive_attribution_report
    )

    clearinghouse = subparsers.add_parser(
        "clearinghouse-report",
        help="Create a cross-provider clearinghouse settlement report from statements and transitive reports.",
    )
    clearinghouse.add_argument(
        "--statement",
        action="append",
        help="RDLLM royalty statement JSON to include in clearing.",
    )
    clearinghouse.add_argument(
        "--transitive-report",
        action="append",
        help="RDLLM transitive attribution report JSON to include in clearing.",
    )
    clearinghouse.add_argument("--issuer", default="rdllm-local-demo")
    clearinghouse.add_argument("--settlement-currency", default="USD")
    clearinghouse.add_argument("--signing-secret")
    clearinghouse.add_argument("--output")
    clearinghouse.set_defaults(func=run_clearinghouse_report)

    verify_clearinghouse = subparsers.add_parser(
        "verify-clearinghouse-report",
        help="Verify a clearinghouse report against its submitted public settlement artifacts.",
    )
    verify_clearinghouse.add_argument("--report", required=True)
    verify_clearinghouse.add_argument("--statement", action="append")
    verify_clearinghouse.add_argument("--transitive-report", action="append")
    verify_clearinghouse.add_argument("--signing-secret")
    verify_clearinghouse.set_defaults(func=run_verify_clearinghouse_report)

    remittance = subparsers.add_parser(
        "remittance-report",
        help="Create payment-file-ready remittance instructions from a clearinghouse report.",
    )
    remittance.add_argument("--clearinghouse-report", required=True)
    remittance.add_argument("--creator-license-contract", required=True)
    remittance.add_argument("--payment-rail", default="iso20022-pain001-compatible")
    remittance.add_argument("--escrow-account-id", default="rdllm-registry-escrow")
    remittance.add_argument("--issuer", default="rdllm-local-demo")
    remittance.add_argument("--signing-secret")
    remittance.add_argument("--output")
    remittance.set_defaults(func=run_remittance_report)

    verify_remittance = subparsers.add_parser(
        "verify-remittance-report",
        help="Verify remittance instructions against clearinghouse and license artifacts.",
    )
    verify_remittance.add_argument("--report", required=True)
    verify_remittance.add_argument("--clearinghouse-report", required=True)
    verify_remittance.add_argument("--creator-license-contract", required=True)
    verify_remittance.add_argument("--escrow-account-id", default="rdllm-registry-escrow")
    verify_remittance.add_argument("--signing-secret")
    verify_remittance.set_defaults(func=run_verify_remittance_report)

    payment_execution = subparsers.add_parser(
        "payment-execution-report",
        help="Bind remittance instructions to external processor and escrow settlement records.",
    )
    payment_execution.add_argument("--remittance-report", required=True)
    payment_execution.add_argument("--processor-records", required=True)
    payment_execution.add_argument("--issuer", default="rdllm-local-demo")
    payment_execution.add_argument("--signing-secret")
    payment_execution.add_argument("--output")
    payment_execution.set_defaults(func=run_payment_execution_report)

    verify_payment_execution = subparsers.add_parser(
        "verify-payment-execution-report",
        help="Verify payment execution against remittance and processor records.",
    )
    verify_payment_execution.add_argument("--report", required=True)
    verify_payment_execution.add_argument("--remittance-report", required=True)
    verify_payment_execution.add_argument("--processor-records", required=True)
    verify_payment_execution.add_argument("--signing-secret")
    verify_payment_execution.set_defaults(func=run_verify_payment_execution_report)

    processor_batch_attestations = subparsers.add_parser(
        "processor-batch-attestations",
        help="Create signed hash-only processor batch attestations for a payment execution report.",
    )
    processor_batch_attestations.add_argument(
        "--payment-execution-report",
        required=True,
    )
    processor_batch_attestations.add_argument(
        "--processor-secret",
        action="append",
        help="Processor signing secret in processor_id=secret format.",
    )
    processor_batch_attestations.add_argument("--output")
    processor_batch_attestations.set_defaults(func=run_processor_batch_attestations)

    payment_rail_attestation = subparsers.add_parser(
        "payment-rail-attestation",
        help="Bind payment execution to registered external processor signatures.",
    )
    payment_rail_attestation.add_argument("--payment-execution-report", required=True)
    payment_rail_attestation.add_argument("--trust-registry", required=True)
    payment_rail_attestation.add_argument("--processor-attestations", required=True)
    payment_rail_attestation.add_argument(
        "--processor-secret",
        action="append",
        help="Processor signing secret in processor_id=secret format.",
    )
    payment_rail_attestation.add_argument("--issuer", default="rdllm-local-demo")
    payment_rail_attestation.add_argument("--signing-secret")
    payment_rail_attestation.add_argument("--output")
    payment_rail_attestation.set_defaults(func=run_payment_rail_attestation)

    verify_payment_rail_attestation = subparsers.add_parser(
        "verify-payment-rail-attestation",
        help="Verify a payment-rail attestation against execution, registry, and processor signatures.",
    )
    verify_payment_rail_attestation.add_argument("--report", required=True)
    verify_payment_rail_attestation.add_argument(
        "--payment-execution-report",
        required=True,
    )
    verify_payment_rail_attestation.add_argument("--trust-registry", required=True)
    verify_payment_rail_attestation.add_argument(
        "--processor-attestations",
        required=True,
    )
    verify_payment_rail_attestation.add_argument(
        "--processor-secret",
        action="append",
        help="Processor signing secret in processor_id=secret format.",
    )
    verify_payment_rail_attestation.add_argument("--signing-secret")
    verify_payment_rail_attestation.set_defaults(
        func=run_verify_payment_rail_attestation
    )

    creator_payout_receipts = subparsers.add_parser(
        "creator-payout-receipts",
        help="Create creator-facing payout receipts bound to clearing, remittance, execution, and rail proof.",
    )
    creator_payout_receipts.add_argument("--clearinghouse-report", required=True)
    creator_payout_receipts.add_argument("--remittance-report", required=True)
    creator_payout_receipts.add_argument("--payment-execution-report", required=True)
    creator_payout_receipts.add_argument("--payment-rail-attestation", required=True)
    creator_payout_receipts.add_argument("--issuer", default="rdllm-local-demo")
    creator_payout_receipts.add_argument("--signing-secret")
    creator_payout_receipts.add_argument("--output")
    creator_payout_receipts.set_defaults(func=run_creator_payout_receipts)

    verify_creator_payout_receipts = subparsers.add_parser(
        "verify-creator-payout-receipts",
        help="Verify creator-facing payout receipts against settlement proof artifacts.",
    )
    verify_creator_payout_receipts.add_argument("--report", required=True)
    verify_creator_payout_receipts.add_argument("--clearinghouse-report", required=True)
    verify_creator_payout_receipts.add_argument("--remittance-report", required=True)
    verify_creator_payout_receipts.add_argument(
        "--payment-execution-report",
        required=True,
    )
    verify_creator_payout_receipts.add_argument(
        "--payment-rail-attestation",
        required=True,
    )
    verify_creator_payout_receipts.add_argument("--signing-secret")
    verify_creator_payout_receipts.set_defaults(
        func=run_verify_creator_payout_receipts
    )

    rendered_attribution_audit = subparsers.add_parser(
        "rendered-attribution-audit",
        help="Audit the exact rendered Markdown answer, inline citations, source footer, and claim evidence rows.",
    )
    rendered_attribution_audit.add_argument("--response-envelope", required=True)
    rendered_attribution_audit.add_argument("--citation-footer-contract", required=True)
    rendered_attribution_audit.add_argument("--source-availability-report", required=True)
    rendered_attribution_audit.add_argument("--evidence-sufficiency-report", required=True)
    rendered_attribution_audit.add_argument("--counterevidence-report", required=True)
    rendered_attribution_audit.add_argument("--answer-claim-coverage-report", required=True)
    rendered_attribution_audit.add_argument("--issuer", default="rdllm-local-demo")
    rendered_attribution_audit.add_argument("--signing-secret")
    rendered_attribution_audit.add_argument("--output")
    rendered_attribution_audit.set_defaults(func=run_rendered_attribution_audit)

    verify_rendered_attribution_audit = subparsers.add_parser(
        "verify-rendered-attribution-audit",
        help="Verify a rendered attribution audit against response and source proof artifacts.",
    )
    verify_rendered_attribution_audit.add_argument("--report", required=True)
    verify_rendered_attribution_audit.add_argument("--response-envelope", required=True)
    verify_rendered_attribution_audit.add_argument("--citation-footer-contract", required=True)
    verify_rendered_attribution_audit.add_argument(
        "--source-availability-report",
        required=True,
    )
    verify_rendered_attribution_audit.add_argument(
        "--evidence-sufficiency-report",
        required=True,
    )
    verify_rendered_attribution_audit.add_argument("--counterevidence-report", required=True)
    verify_rendered_attribution_audit.add_argument(
        "--answer-claim-coverage-report",
        required=True,
    )
    verify_rendered_attribution_audit.add_argument("--signing-secret")
    verify_rendered_attribution_audit.set_defaults(
        func=run_verify_rendered_attribution_audit
    )

    training_memory_provenance = subparsers.add_parser(
        "training-memory-provenance",
        help="Detect registered training-memory spans in the exact rendered answer surface.",
    )
    training_memory_provenance.add_argument("--response-envelope", required=True)
    training_memory_provenance.add_argument("--rendered-attribution-audit", required=True)
    training_memory_provenance.add_argument("--creator-license-contract", required=True)
    training_memory_provenance.add_argument("--training-content-summary", required=True)
    training_memory_provenance.add_argument("--source-snapshots", required=True)
    training_memory_provenance.add_argument(
        "--min-match-tokens",
        type=int,
        default=8,
    )
    training_memory_provenance.add_argument("--issuer", default="rdllm-local-demo")
    training_memory_provenance.add_argument("--signing-secret")
    training_memory_provenance.add_argument("--output")
    training_memory_provenance.set_defaults(func=run_training_memory_provenance)

    verify_training_memory_provenance = subparsers.add_parser(
        "verify-training-memory-provenance",
        help="Verify a training-memory provenance report against response and source snapshots.",
    )
    verify_training_memory_provenance.add_argument("--report", required=True)
    verify_training_memory_provenance.add_argument("--response-envelope", required=True)
    verify_training_memory_provenance.add_argument(
        "--rendered-attribution-audit",
        required=True,
    )
    verify_training_memory_provenance.add_argument(
        "--creator-license-contract",
        required=True,
    )
    verify_training_memory_provenance.add_argument(
        "--training-content-summary",
        required=True,
    )
    verify_training_memory_provenance.add_argument("--source-snapshots", required=True)
    verify_training_memory_provenance.add_argument("--signing-secret")
    verify_training_memory_provenance.set_defaults(
        func=run_verify_training_memory_provenance
    )

    evidence_locked_generation = subparsers.add_parser(
        "evidence-locked-generation",
        help="Bind each support-required answer unit to evidence locked before generation.",
    )
    evidence_locked_generation.add_argument("--response-envelope", required=True)
    evidence_locked_generation.add_argument(
        "--answer-claim-coverage-report",
        required=True,
    )
    evidence_locked_generation.add_argument(
        "--generation-context-closure-report",
        required=True,
    )
    evidence_locked_generation.add_argument(
        "--citation-footer-contract",
        required=True,
    )
    evidence_locked_generation.add_argument(
        "--rendered-attribution-audit",
        required=True,
    )
    evidence_locked_generation.add_argument(
        "--training-memory-provenance",
        required=True,
    )
    evidence_locked_generation.add_argument("--lock-created-at")
    evidence_locked_generation.add_argument("--generation-started-at")
    evidence_locked_generation.add_argument("--issuer", default="rdllm-local-demo")
    evidence_locked_generation.add_argument("--signing-secret")
    evidence_locked_generation.add_argument("--output")
    evidence_locked_generation.set_defaults(func=run_evidence_locked_generation)

    verify_evidence_locked_generation = subparsers.add_parser(
        "verify-evidence-locked-generation",
        help="Verify an L82 evidence-locked generation report against public proof inputs.",
    )
    verify_evidence_locked_generation.add_argument("--report", required=True)
    verify_evidence_locked_generation.add_argument("--response-envelope", required=True)
    verify_evidence_locked_generation.add_argument(
        "--answer-claim-coverage-report",
        required=True,
    )
    verify_evidence_locked_generation.add_argument(
        "--generation-context-closure-report",
        required=True,
    )
    verify_evidence_locked_generation.add_argument(
        "--citation-footer-contract",
        required=True,
    )
    verify_evidence_locked_generation.add_argument(
        "--rendered-attribution-audit",
        required=True,
    )
    verify_evidence_locked_generation.add_argument(
        "--training-memory-provenance",
        required=True,
    )
    verify_evidence_locked_generation.add_argument("--signing-secret")
    verify_evidence_locked_generation.set_defaults(
        func=run_verify_evidence_locked_generation
    )

    emission_enforcement = subparsers.add_parser(
        "emission-evidence-enforcement",
        help="Bind served and streamed output to satisfied pre-generation evidence locks.",
    )
    emission_enforcement.add_argument("--response-envelope", required=True)
    emission_enforcement.add_argument("--answer-claim-coverage-report", required=True)
    emission_enforcement.add_argument("--evidence-locked-generation", required=True)
    emission_enforcement.add_argument("--proof-carrying-response", required=True)
    emission_enforcement.add_argument("--serving-gateway-report", required=True)
    emission_enforcement.add_argument(
        "--streaming-attribution-manifest",
        required=True,
    )
    emission_enforcement.add_argument("--issuer", default="rdllm-local-demo")
    emission_enforcement.add_argument("--signing-secret")
    emission_enforcement.add_argument("--output")
    emission_enforcement.set_defaults(func=run_emission_evidence_enforcement)

    verify_emission_enforcement = subparsers.add_parser(
        "verify-emission-evidence-enforcement",
        help="Verify an L83 serving-time emission enforcement report.",
    )
    verify_emission_enforcement.add_argument("--report", required=True)
    verify_emission_enforcement.add_argument("--response-envelope", required=True)
    verify_emission_enforcement.add_argument(
        "--answer-claim-coverage-report",
        required=True,
    )
    verify_emission_enforcement.add_argument(
        "--evidence-locked-generation",
        required=True,
    )
    verify_emission_enforcement.add_argument(
        "--proof-carrying-response",
        required=True,
    )
    verify_emission_enforcement.add_argument(
        "--serving-gateway-report",
        required=True,
    )
    verify_emission_enforcement.add_argument(
        "--streaming-attribution-manifest",
        required=True,
    )
    verify_emission_enforcement.add_argument("--signing-secret")
    verify_emission_enforcement.set_defaults(
        func=run_verify_emission_evidence_enforcement
    )

    live_emission_witness = subparsers.add_parser(
        "live-emission-witness",
        help="Create an L84 live emission witness quorum report.",
    )
    live_emission_witness.add_argument(
        "--emission-evidence-enforcement",
        required=True,
    )
    live_emission_witness.add_argument(
        "--streaming-attribution-manifest",
        required=True,
    )
    live_emission_witness.add_argument(
        "--witness",
        action="append",
        required=True,
        help="Witness signing spec witness_id:secret.",
    )
    live_emission_witness.add_argument("--required-quorum", type=int, default=2)
    live_emission_witness.add_argument(
        "--minimum-independent-organizations",
        type=int,
        default=2,
    )
    live_emission_witness.add_argument("--issuer", default="rdllm-local-demo")
    live_emission_witness.add_argument("--signing-secret")
    live_emission_witness.add_argument("--output")
    live_emission_witness.set_defaults(func=run_live_emission_witness)

    verify_live_emission_witness = subparsers.add_parser(
        "verify-live-emission-witness",
        help="Verify an L84 live emission witness quorum report.",
    )
    verify_live_emission_witness.add_argument("--report", required=True)
    verify_live_emission_witness.add_argument(
        "--emission-evidence-enforcement",
        required=True,
    )
    verify_live_emission_witness.add_argument(
        "--streaming-attribution-manifest",
        required=True,
    )
    verify_live_emission_witness.add_argument(
        "--witness",
        action="append",
        required=True,
        help="Witness signing spec witness_id:secret.",
    )
    verify_live_emission_witness.add_argument("--signing-secret")
    verify_live_emission_witness.set_defaults(func=run_verify_live_emission_witness)

    live_emission_transparency_log = subparsers.add_parser(
        "live-emission-transparency-log",
        help="Create an L85 append-only transparency log for live witness subjects.",
    )
    live_emission_transparency_log.add_argument(
        "--live-emission-witness",
        required=True,
    )
    live_emission_transparency_log.add_argument(
        "--existing-log",
        help="Optional prior live-emission transparency log whose entries are preserved as a prefix.",
    )
    live_emission_transparency_log.add_argument(
        "--log-id",
        default="live-emission-transparency",
    )
    live_emission_transparency_log.add_argument(
        "--report-only",
        action="store_true",
        help="Include only the live witness report subject, not individual attestations.",
    )
    live_emission_transparency_log.add_argument("--output")
    live_emission_transparency_log.set_defaults(
        func=run_live_emission_transparency_log
    )

    live_emission_transparency = subparsers.add_parser(
        "live-emission-transparency",
        help="Create an L85 transparency inclusion report for live emission witness artifacts.",
    )
    live_emission_transparency.add_argument(
        "--live-emission-witness",
        required=True,
    )
    live_emission_transparency.add_argument(
        "--transparency-log",
        action="append",
        required=True,
        help="Transparency log spec name=path or path.",
    )
    live_emission_transparency.add_argument("--issuer", default="rdllm-local-demo")
    live_emission_transparency.add_argument("--signing-secret")
    live_emission_transparency.add_argument("--output")
    live_emission_transparency.set_defaults(func=run_live_emission_transparency)

    verify_live_emission_transparency = subparsers.add_parser(
        "verify-live-emission-transparency",
        help="Verify an L85 live emission transparency inclusion report.",
    )
    verify_live_emission_transparency.add_argument("--report", required=True)
    verify_live_emission_transparency.add_argument(
        "--live-emission-witness",
        required=True,
    )
    verify_live_emission_transparency.add_argument(
        "--transparency-log",
        action="append",
        required=True,
        help="Transparency log spec name=path or path.",
    )
    verify_live_emission_transparency.add_argument("--signing-secret")
    verify_live_emission_transparency.set_defaults(
        func=run_verify_live_emission_transparency
    )

    runtime_measurement = subparsers.add_parser(
        "runtime-measurement",
        help="Create an L86 runtime measurement commitment for attribution-enforcing code.",
    )
    runtime_measurement.add_argument("--runtime-id", required=True)
    runtime_measurement.add_argument(
        "--runtime-version",
        default="rdllm-reference-runtime/2026-06",
    )
    runtime_measurement.add_argument("--source-commit-hash", required=True)
    runtime_measurement.add_argument("--container-image-hash", required=True)
    runtime_measurement.add_argument("--enforcement-binary-hash", required=True)
    runtime_measurement.add_argument("--policy-bundle-hash", required=True)
    runtime_measurement.add_argument("--model-binding-hash", required=True)
    runtime_measurement.add_argument("--verifier-bundle-hash", required=True)
    runtime_measurement.add_argument("--output")
    runtime_measurement.set_defaults(func=run_runtime_measurement)

    runtime_quote = subparsers.add_parser(
        "runtime-attestation-quote",
        help="Create an L86 attestor quote over a measured attribution runtime and live output path.",
    )
    runtime_quote.add_argument("--runtime-measurement", required=True)
    runtime_quote.add_argument("--live-emission-transparency", required=True)
    runtime_quote.add_argument("--proof-carrying-response", required=True)
    runtime_quote.add_argument("--serving-gateway-report", required=True)
    runtime_quote.add_argument("--evidence-locked-generation", required=True)
    runtime_quote.add_argument("--attestor-id", required=True)
    runtime_quote.add_argument("--platform-id", required=True)
    runtime_quote.add_argument(
        "--platform-type",
        default="rdllm-conformance-tee",
    )
    runtime_quote.add_argument("--attestor-secret", required=True)
    runtime_quote.add_argument("--created-at")
    runtime_quote.add_argument("--expires-at")
    runtime_quote.add_argument("--output")
    runtime_quote.set_defaults(func=run_runtime_attestation_quote)

    attested_runtime = subparsers.add_parser(
        "attested-runtime",
        help="Create an L86 attested attribution runtime report.",
    )
    attested_runtime.add_argument("--live-emission-transparency", required=True)
    attested_runtime.add_argument("--proof-carrying-response", required=True)
    attested_runtime.add_argument("--serving-gateway-report", required=True)
    attested_runtime.add_argument("--evidence-locked-generation", required=True)
    attested_runtime.add_argument("--runtime-measurement", required=True)
    attested_runtime.add_argument(
        "--runtime-quote",
        action="append",
        required=True,
        help="Runtime attestation quote JSON path. Repeat for quorum.",
    )
    attested_runtime.add_argument(
        "--trusted-attestor",
        action="append",
        required=True,
        help="Trusted attestor spec attestor_id:platform_id:secret[:platform_type].",
    )
    attested_runtime.add_argument("--minimum-quote-count", type=int, default=1)
    attested_runtime.add_argument("--issuer", default="rdllm-local-demo")
    attested_runtime.add_argument("--created-at")
    attested_runtime.add_argument("--signing-secret")
    attested_runtime.add_argument("--output")
    attested_runtime.set_defaults(func=run_attested_runtime)

    verify_attested_runtime = subparsers.add_parser(
        "verify-attested-runtime",
        help="Verify an L86 attested attribution runtime report.",
    )
    verify_attested_runtime.add_argument("--report", required=True)
    verify_attested_runtime.add_argument("--live-emission-transparency", required=True)
    verify_attested_runtime.add_argument("--proof-carrying-response", required=True)
    verify_attested_runtime.add_argument("--serving-gateway-report", required=True)
    verify_attested_runtime.add_argument("--evidence-locked-generation", required=True)
    verify_attested_runtime.add_argument("--runtime-measurement", required=True)
    verify_attested_runtime.add_argument(
        "--runtime-quote",
        action="append",
        required=True,
        help="Runtime attestation quote JSON path. Repeat for quorum.",
    )
    verify_attested_runtime.add_argument(
        "--trusted-attestor",
        action="append",
        required=True,
        help="Trusted attestor spec attestor_id:platform_id:secret[:platform_type].",
    )
    verify_attested_runtime.add_argument("--signing-secret")
    verify_attested_runtime.set_defaults(func=run_verify_attested_runtime)

    provenance_eval = subparsers.add_parser(
        "provenance-evaluation",
        help="Run a portable source-provenance benchmark and emit a signed report.",
    )
    provenance_eval.add_argument("--benchmark", required=True)
    provenance_eval.add_argument("--issuer", default="rdllm-local-demo")
    provenance_eval.add_argument("--provider", default="provider:unspecified")
    provenance_eval.add_argument("--model-id", default="model:unspecified")
    provenance_eval.add_argument("--model-version", default="unknown")
    provenance_eval.add_argument("--signing-secret")
    provenance_eval.add_argument("--output")
    provenance_eval.set_defaults(func=run_provenance_evaluation)

    verify_provenance_eval = subparsers.add_parser(
        "verify-provenance-evaluation",
        help="Verify a source-provenance benchmark report by replaying benchmark cases.",
    )
    verify_provenance_eval.add_argument("--benchmark", required=True)
    verify_provenance_eval.add_argument("--report", required=True)
    verify_provenance_eval.add_argument("--signing-secret")
    verify_provenance_eval.set_defaults(func=run_verify_provenance_evaluation)

    counterfactual = subparsers.add_parser(
        "counterfactual-report",
        help="Create a source-influence report by ablating each credited work.",
    )
    counterfactual.add_argument("--ledger", required=True)
    counterfactual.add_argument("--event-id")
    counterfactual.add_argument("--min-impact-margin", type=float, default=0.05)
    counterfactual.add_argument("--issuer", default="rdllm-local-demo")
    counterfactual.add_argument("--signing-secret")
    counterfactual.add_argument("--output")
    counterfactual.set_defaults(func=run_counterfactual_report)

    verify_counterfactual = subparsers.add_parser(
        "verify-counterfactual-report",
        help="Verify a source-influence report by replaying credited-work ablations.",
    )
    verify_counterfactual.add_argument("--ledger", required=True)
    verify_counterfactual.add_argument("--report", required=True)
    verify_counterfactual.add_argument("--event-id")
    verify_counterfactual.add_argument("--signing-secret")
    verify_counterfactual.set_defaults(func=run_verify_counterfactual_report)

    media_attribution = subparsers.add_parser(
        "media-attribution",
        help="Create a privacy-safe media attribution report for image/audio/video inputs.",
    )
    media_attribution.add_argument("--media-corpus", required=True)
    media_attribution.add_argument("--submitted-media", required=True)
    media_attribution.add_argument("--media-gross-revenue", default="1.00")
    media_attribution.add_argument("--media-creator-pool-rate", default="0.55")
    media_attribution.add_argument("--accept-threshold", type=float, default=0.65)
    media_attribution.add_argument("--issuer", default="rdllm-local-demo")
    media_attribution.add_argument("--signing-secret")
    media_attribution.add_argument("--output")
    media_attribution.set_defaults(func=run_media_attribution)

    verify_media_attribution = subparsers.add_parser(
        "verify-media-attribution",
        help="Verify a media attribution report against private media signatures.",
    )
    verify_media_attribution.add_argument("--media-corpus", required=True)
    verify_media_attribution.add_argument("--submitted-media", required=True)
    verify_media_attribution.add_argument("--report", required=True)
    verify_media_attribution.add_argument("--signing-secret")
    verify_media_attribution.set_defaults(func=run_verify_media_attribution)

    model_signal = subparsers.add_parser(
        "model-signal-report",
        help="Create a privacy-safe attribution report from provider model-internal signals.",
    )
    model_signal.add_argument("--signal-input", required=True)
    model_signal.add_argument("--signal-gross-revenue", default="1.00")
    model_signal.add_argument("--signal-creator-pool-rate", default="0.55")
    model_signal.add_argument("--accept-threshold", type=float, default=0.50)
    model_signal.add_argument("--issuer", default="rdllm-local-demo")
    model_signal.add_argument("--signing-secret")
    model_signal.add_argument("--output")
    model_signal.set_defaults(func=run_model_signal_report)

    verify_model_signal = subparsers.add_parser(
        "verify-model-signal-report",
        help="Verify a provider model-signal attribution report against private telemetry.",
    )
    verify_model_signal.add_argument("--signal-input", required=True)
    verify_model_signal.add_argument("--report", required=True)
    verify_model_signal.add_argument("--signing-secret")
    verify_model_signal.set_defaults(func=run_verify_model_signal_report)

    pinpoint_provenance = subparsers.add_parser(
        "pinpoint-provenance-report",
        help="Create a pinpoint provenance report that rejects topical anti-documents.",
    )
    pinpoint_provenance.add_argument("--pinpoint-input", required=True)
    pinpoint_provenance.add_argument("--pinpoint-gross-revenue", default="1.00")
    pinpoint_provenance.add_argument("--pinpoint-creator-pool-rate", default="0.55")
    pinpoint_provenance.add_argument("--accept-threshold", type=float, default=0.34)
    pinpoint_provenance.add_argument("--min-margin", type=float, default=0.04)
    pinpoint_provenance.add_argument(
        "--min-critical-recall",
        type=float,
        default=0.80,
    )
    pinpoint_provenance.add_argument("--issuer", default="rdllm-local-demo")
    pinpoint_provenance.add_argument("--signing-secret")
    pinpoint_provenance.add_argument("--output")
    pinpoint_provenance.set_defaults(func=run_pinpoint_provenance_report)

    verify_pinpoint_provenance = subparsers.add_parser(
        "verify-pinpoint-provenance-report",
        help="Verify a pinpoint provenance report against private candidate documents.",
    )
    verify_pinpoint_provenance.add_argument("--pinpoint-input", required=True)
    verify_pinpoint_provenance.add_argument("--report", required=True)
    verify_pinpoint_provenance.add_argument("--signing-secret")
    verify_pinpoint_provenance.set_defaults(
        func=run_verify_pinpoint_provenance_report
    )

    claim_source_attribution = subparsers.add_parser(
        "claim-source-attribution-report",
        help="Create a claim-level source attribution report with footers, anti-documents, and LOO contribution.",
    )
    claim_source_attribution.add_argument("--attribution-input", required=True)
    claim_source_attribution.add_argument("--gross-revenue", default="1.00")
    claim_source_attribution.add_argument("--creator-pool-rate", default="0.55")
    claim_source_attribution.add_argument("--accept-threshold", type=float, default=0.48)
    claim_source_attribution.add_argument("--min-margin", type=float, default=0.04)
    claim_source_attribution.add_argument("--min-anti-margin", type=float, default=0.08)
    claim_source_attribution.add_argument("--issuer", default="rdllm-local-demo")
    claim_source_attribution.add_argument("--signing-secret")
    claim_source_attribution.add_argument("--output")
    claim_source_attribution.set_defaults(func=run_claim_source_attribution_report)

    verify_claim_source_attribution = subparsers.add_parser(
        "verify-claim-source-attribution-report",
        help="Verify a claim-source attribution report against private candidate evidence.",
    )
    verify_claim_source_attribution.add_argument("--attribution-input", required=True)
    verify_claim_source_attribution.add_argument("--report", required=True)
    verify_claim_source_attribution.add_argument("--signing-secret")
    verify_claim_source_attribution.set_defaults(
        func=run_verify_claim_source_attribution_report
    )

    evidence_utility_attribution = subparsers.add_parser(
        "evidence-utility-attribution-report",
        help="Create a causal evidence-utility report using source intervention trials.",
    )
    evidence_utility_attribution.add_argument("--utility-input", required=True)
    evidence_utility_attribution.add_argument("--gross-revenue", default="1.00")
    evidence_utility_attribution.add_argument("--creator-pool-rate", default="0.55")
    evidence_utility_attribution.add_argument("--min-utility", type=float, default=0.35)
    evidence_utility_attribution.add_argument(
        "--max-duplicate-credit-inflation", type=float, default=0.02
    )
    evidence_utility_attribution.add_argument(
        "--max-duplicate-trace-drift", type=float, default=0.12
    )
    evidence_utility_attribution.add_argument("--issuer", default="rdllm-local-demo")
    evidence_utility_attribution.add_argument("--signing-secret")
    evidence_utility_attribution.add_argument("--output")
    evidence_utility_attribution.set_defaults(
        func=run_evidence_utility_attribution_report
    )

    verify_evidence_utility_attribution = subparsers.add_parser(
        "verify-evidence-utility-attribution-report",
        help="Verify a causal evidence-utility report against private intervention trials.",
    )
    verify_evidence_utility_attribution.add_argument("--utility-input", required=True)
    verify_evidence_utility_attribution.add_argument("--report", required=True)
    verify_evidence_utility_attribution.add_argument("--signing-secret")
    verify_evidence_utility_attribution.set_defaults(
        func=run_verify_evidence_utility_attribution_report
    )

    parametric_memory_attribution = subparsers.add_parser(
        "parametric-memory-attribution-report",
        help="Create a parametric-memory attribution report for claims sourced from model weights.",
    )
    parametric_memory_attribution.add_argument("--parametric-input", required=True)
    parametric_memory_attribution.add_argument("--gross-revenue", default="1.00")
    parametric_memory_attribution.add_argument("--creator-pool-rate", default="0.55")
    parametric_memory_attribution.add_argument("--min-support", type=float, default=0.34)
    parametric_memory_attribution.add_argument("--min-memory", type=float, default=0.45)
    parametric_memory_attribution.add_argument("--min-influence", type=float, default=0.25)
    parametric_memory_attribution.add_argument(
        "--min-anti-margin", type=float, default=0.20
    )
    parametric_memory_attribution.add_argument("--issuer", default="rdllm-local-demo")
    parametric_memory_attribution.add_argument("--signing-secret")
    parametric_memory_attribution.add_argument("--output")
    parametric_memory_attribution.set_defaults(
        func=run_parametric_memory_attribution_report
    )

    verify_parametric_memory_attribution = subparsers.add_parser(
        "verify-parametric-memory-attribution-report",
        help="Verify a parametric-memory attribution report against private training probes.",
    )
    verify_parametric_memory_attribution.add_argument("--parametric-input", required=True)
    verify_parametric_memory_attribution.add_argument("--report", required=True)
    verify_parametric_memory_attribution.add_argument("--signing-secret")
    verify_parametric_memory_attribution.set_defaults(
        func=run_verify_parametric_memory_attribution_report
    )

    style_influence_attribution = subparsers.add_parser(
        "style-influence-attribution-report",
        help="Create a style or voice influence attribution report for non-verbatim generated outputs.",
    )
    style_influence_attribution.add_argument("--style-input", required=True)
    style_influence_attribution.add_argument("--gross-revenue", default="1.00")
    style_influence_attribution.add_argument("--creator-pool-rate", default="0.55")
    style_influence_attribution.add_argument(
        "--accept-threshold", type=float, default=0.42
    )
    style_influence_attribution.add_argument(
        "--min-style-margin", type=float, default=0.04
    )
    style_influence_attribution.add_argument(
        "--min-anti-margin", type=float, default=0.08
    )
    style_influence_attribution.add_argument(
        "--max-content-overlap", type=float, default=0.35
    )
    style_influence_attribution.add_argument("--blend-window", type=float, default=0.08)
    style_influence_attribution.add_argument("--issuer", default="rdllm-local-demo")
    style_influence_attribution.add_argument("--signing-secret")
    style_influence_attribution.add_argument("--output")
    style_influence_attribution.set_defaults(
        func=run_style_influence_attribution_report
    )

    verify_style_influence_attribution = subparsers.add_parser(
        "verify-style-influence-attribution-report",
        help="Verify a style or voice influence attribution report against private style profiles.",
    )
    verify_style_influence_attribution.add_argument("--style-input", required=True)
    verify_style_influence_attribution.add_argument("--report", required=True)
    verify_style_influence_attribution.add_argument("--signing-secret")
    verify_style_influence_attribution.set_defaults(
        func=run_verify_style_influence_attribution_report
    )

    model_lineage_attribution = subparsers.add_parser(
        "model-lineage-attribution-report",
        help="Create a model-lineage attribution report for fine-tuned or distilled downstream models.",
    )
    model_lineage_attribution.add_argument("--model-lineage-input", required=True)
    model_lineage_attribution.add_argument("--gross-revenue", default="1.00")
    model_lineage_attribution.add_argument("--creator-pool-rate", default="0.55")
    model_lineage_attribution.add_argument("--model-lineage-rate", default="0.20")
    model_lineage_attribution.add_argument("--issuer", default="rdllm-local-demo")
    model_lineage_attribution.add_argument("--signing-secret")
    model_lineage_attribution.add_argument("--output")
    model_lineage_attribution.set_defaults(
        func=run_model_lineage_attribution_report
    )

    verify_model_lineage_attribution = subparsers.add_parser(
        "verify-model-lineage-attribution-report",
        help="Verify a model-lineage attribution report against private training and distillation evidence.",
    )
    verify_model_lineage_attribution.add_argument(
        "--model-lineage-input", required=True
    )
    verify_model_lineage_attribution.add_argument("--report", required=True)
    verify_model_lineage_attribution.add_argument("--signing-secret")
    verify_model_lineage_attribution.set_defaults(
        func=run_verify_model_lineage_attribution_report
    )

    black_box_model_provenance = subparsers.add_parser(
        "black-box-model-provenance-report",
        help="Create a black-box provenance challenge report for an undisclosed derivative model.",
    )
    black_box_model_provenance.add_argument(
        "--black-box-model-provenance-input", required=True
    )
    black_box_model_provenance.add_argument("--gross-revenue", default="1.00")
    black_box_model_provenance.add_argument("--creator-pool-rate", default="0.55")
    black_box_model_provenance.add_argument(
        "--provenance-challenge-rate", default="0.10"
    )
    black_box_model_provenance.add_argument("--confidence-level", default="0.95")
    black_box_model_provenance.add_argument("--min-effect", default="0.10")
    black_box_model_provenance.add_argument("--min-challenge-count", type=int, default=3)
    black_box_model_provenance.add_argument("--issuer", default="rdllm-local-demo")
    black_box_model_provenance.add_argument("--signing-secret")
    black_box_model_provenance.add_argument("--output")
    black_box_model_provenance.set_defaults(
        func=run_black_box_model_provenance_report
    )

    verify_black_box_model_provenance = subparsers.add_parser(
        "verify-black-box-model-provenance-report",
        help="Verify a black-box provenance challenge report against private API challenge evidence.",
    )
    verify_black_box_model_provenance.add_argument(
        "--black-box-model-provenance-input", required=True
    )
    verify_black_box_model_provenance.add_argument("--report", required=True)
    verify_black_box_model_provenance.add_argument("--signing-secret")
    verify_black_box_model_provenance.set_defaults(
        func=run_verify_black_box_model_provenance_report
    )

    attribution_dispute = subparsers.add_parser(
        "attribution-dispute-adjudication-report",
        help="Create a public adjudication report for disputed attribution and creator escrow.",
    )
    attribution_dispute.add_argument("--attribution-dispute-input", required=True)
    attribution_dispute.add_argument("--issuer", default="rdllm-local-demo")
    attribution_dispute.add_argument("--signing-secret")
    attribution_dispute.add_argument("--output")
    attribution_dispute.set_defaults(
        func=run_attribution_dispute_adjudication_report
    )

    verify_attribution_dispute = subparsers.add_parser(
        "verify-attribution-dispute-adjudication-report",
        help="Verify an attribution dispute adjudication report against private case evidence.",
    )
    verify_attribution_dispute.add_argument("--attribution-dispute-input", required=True)
    verify_attribution_dispute.add_argument("--report", required=True)
    verify_attribution_dispute.add_argument("--signing-secret")
    verify_attribution_dispute.set_defaults(
        func=run_verify_attribution_dispute_adjudication_report
    )

    post_adjudication_adjustment = subparsers.add_parser(
        "post-adjudication-settlement-adjustment-report",
        help="Create a forward-only correction report after attribution adjudication changes payout.",
    )
    post_adjudication_adjustment.add_argument(
        "--post-adjudication-settlement-adjustment-input", required=True
    )
    post_adjudication_adjustment.add_argument("--issuer", default="rdllm-local-demo")
    post_adjudication_adjustment.add_argument("--signing-secret")
    post_adjudication_adjustment.add_argument("--output")
    post_adjudication_adjustment.set_defaults(
        func=run_post_adjudication_settlement_adjustment_report
    )

    verify_post_adjudication_adjustment = subparsers.add_parser(
        "verify-post-adjudication-settlement-adjustment-report",
        help="Verify a post-adjudication settlement adjustment report against private correction evidence.",
    )
    verify_post_adjudication_adjustment.add_argument(
        "--post-adjudication-settlement-adjustment-input", required=True
    )
    verify_post_adjudication_adjustment.add_argument("--report", required=True)
    verify_post_adjudication_adjustment.add_argument("--signing-secret")
    verify_post_adjudication_adjustment.set_defaults(
        func=run_verify_post_adjudication_settlement_adjustment_report
    )

    residual_corpus_royalty = subparsers.add_parser(
        "residual-corpus-royalty-report",
        help="Create a residual training-corpus royalty report for diffuse model value.",
    )
    residual_corpus_royalty.add_argument(
        "--residual-corpus-royalty-input", required=True
    )
    residual_corpus_royalty.add_argument("--issuer", default="rdllm-local-demo")
    residual_corpus_royalty.add_argument("--signing-secret")
    residual_corpus_royalty.add_argument("--output")
    residual_corpus_royalty.set_defaults(func=run_residual_corpus_royalty_report)

    verify_residual_corpus_royalty = subparsers.add_parser(
        "verify-residual-corpus-royalty-report",
        help="Verify a residual training-corpus royalty report against private valuation evidence.",
    )
    verify_residual_corpus_royalty.add_argument(
        "--residual-corpus-royalty-input", required=True
    )
    verify_residual_corpus_royalty.add_argument("--report", required=True)
    verify_residual_corpus_royalty.add_argument("--signing-secret")
    verify_residual_corpus_royalty.set_defaults(
        func=run_verify_residual_corpus_royalty_report
    )

    valuation_method_audit = subparsers.add_parser(
        "valuation-method-audit-report",
        help="Create a benchmarked audit report for a residual-corpus valuation method.",
    )
    valuation_method_audit.add_argument(
        "--valuation-method-audit-input", required=True
    )
    valuation_method_audit.add_argument("--issuer", default="rdllm-local-demo")
    valuation_method_audit.add_argument("--signing-secret")
    valuation_method_audit.add_argument("--output")
    valuation_method_audit.set_defaults(func=run_valuation_method_audit_report)

    verify_valuation_method_audit = subparsers.add_parser(
        "verify-valuation-method-audit-report",
        help="Verify a residual-corpus valuation method audit against benchmark evidence.",
    )
    verify_valuation_method_audit.add_argument(
        "--valuation-method-audit-input", required=True
    )
    verify_valuation_method_audit.add_argument("--report", required=True)
    verify_valuation_method_audit.add_argument("--signing-secret")
    verify_valuation_method_audit.set_defaults(
        func=run_verify_valuation_method_audit_report
    )

    evidence_region_binding = subparsers.add_parser(
        "evidence-region-binding-report",
        help="Create a report binding rendered citation spans to exact source regions.",
    )
    evidence_region_binding.add_argument(
        "--evidence-region-binding-input", required=True
    )
    evidence_region_binding.add_argument("--issuer", default="rdllm-local-demo")
    evidence_region_binding.add_argument("--signing-secret")
    evidence_region_binding.add_argument("--output")
    evidence_region_binding.set_defaults(func=run_evidence_region_binding_report)

    verify_evidence_region_binding = subparsers.add_parser(
        "verify-evidence-region-binding-report",
        help="Verify rendered citation spans against private source-region snapshots.",
    )
    verify_evidence_region_binding.add_argument(
        "--evidence-region-binding-input", required=True
    )
    verify_evidence_region_binding.add_argument("--report", required=True)
    verify_evidence_region_binding.add_argument("--signing-secret")
    verify_evidence_region_binding.set_defaults(
        func=run_verify_evidence_region_binding_report
    )

    source_access_lease = subparsers.add_parser(
        "source-access-lease-report",
        help="Create a creator/source-issued access lease report for consumed content.",
    )
    source_access_lease.add_argument("--source-access-lease-input", required=True)
    source_access_lease.add_argument("--issuer", default="rdllm-local-demo")
    source_access_lease.add_argument("--signing-secret")
    source_access_lease.add_argument("--output")
    source_access_lease.set_defaults(func=run_source_access_lease_report)

    verify_source_access_lease = subparsers.add_parser(
        "verify-source-access-lease-report",
        help="Verify source-issued leases, access logs, and escrow routing.",
    )
    verify_source_access_lease.add_argument("--source-access-lease-input", required=True)
    verify_source_access_lease.add_argument("--report", required=True)
    verify_source_access_lease.add_argument("--signing-secret")
    verify_source_access_lease.set_defaults(
        func=run_verify_source_access_lease_report
    )

    content_protocol_ingestion = subparsers.add_parser(
        "content-protocol-ingestion-report",
        help="Create a report that maps RSL, CoMP, SCP, and related external rights signals into RDLLM contracts and leases.",
    )
    content_protocol_ingestion.add_argument(
        "--content-protocol-ingestion-input", required=True
    )
    content_protocol_ingestion.add_argument("--issuer", default="rdllm-local-demo")
    content_protocol_ingestion.add_argument("--signing-secret")
    content_protocol_ingestion.add_argument("--output")
    content_protocol_ingestion.set_defaults(
        func=run_content_protocol_ingestion_report
    )

    verify_content_protocol_ingestion = subparsers.add_parser(
        "verify-content-protocol-ingestion-report",
        help="Verify external content-protocol rights signals against RDLLM contracts, source leases, and escrow routing.",
    )
    verify_content_protocol_ingestion.add_argument(
        "--content-protocol-ingestion-input", required=True
    )
    verify_content_protocol_ingestion.add_argument("--report", required=True)
    verify_content_protocol_ingestion.add_argument("--signing-secret")
    verify_content_protocol_ingestion.set_defaults(
        func=run_verify_content_protocol_ingestion_report
    )

    citation_reliance = subparsers.add_parser(
        "citation-reliance-receipt",
        help="Create a receipt proving visible footer sources were relied on, not added post hoc.",
    )
    citation_reliance.add_argument("--citation-reliance-input", required=True)
    citation_reliance.add_argument("--issuer", default="rdllm-local-demo")
    citation_reliance.add_argument("--signing-secret")
    citation_reliance.add_argument("--output")
    citation_reliance.set_defaults(func=run_citation_reliance_receipt)

    verify_citation_reliance = subparsers.add_parser(
        "verify-citation-reliance-receipt",
        help="Verify source-footer reliance against evidence locks, claim replay, causal utility, leases, and protocol ingestion.",
    )
    verify_citation_reliance.add_argument("--citation-reliance-input", required=True)
    verify_citation_reliance.add_argument("--receipt", required=True)
    verify_citation_reliance.add_argument("--signing-secret")
    verify_citation_reliance.set_defaults(func=run_verify_citation_reliance_receipt)

    license_transaction = subparsers.add_parser(
        "license-transaction-receipt",
        help="Create a receipt proving license-server transactions authorize direct source settlement.",
    )
    license_transaction.add_argument("--license-transaction-input", required=True)
    license_transaction.add_argument("--issuer", default="rdllm-local-demo")
    license_transaction.add_argument("--signing-secret")
    license_transaction.add_argument("--output")
    license_transaction.set_defaults(func=run_license_transaction_receipt)

    verify_license_transaction = subparsers.add_parser(
        "verify-license-transaction-receipt",
        help="Verify license-server transaction tokens against source access, protocol ingestion, reliance, and settlement.",
    )
    verify_license_transaction.add_argument("--license-transaction-input", required=True)
    verify_license_transaction.add_argument("--receipt", required=True)
    verify_license_transaction.add_argument("--signing-secret")
    verify_license_transaction.set_defaults(func=run_verify_license_transaction_receipt)

    grounded_source_footer = subparsers.add_parser(
        "grounded-source-footer",
        help="Create a compact user-facing footer receipt backed by source confidence, availability, reliance, and license transactions.",
    )
    grounded_source_footer.add_argument("--grounded-source-footer-input", required=True)
    grounded_source_footer.add_argument("--issuer", default="rdllm-local-demo")
    grounded_source_footer.add_argument("--signing-secret")
    grounded_source_footer.add_argument("--output")
    grounded_source_footer.set_defaults(func=run_grounded_source_footer)

    verify_grounded_source_footer = subparsers.add_parser(
        "verify-grounded-source-footer",
        help="Verify a grounded source footer receipt against the public proof stack.",
    )
    verify_grounded_source_footer.add_argument(
        "--grounded-source-footer-input", required=True
    )
    verify_grounded_source_footer.add_argument("--receipt", required=True)
    verify_grounded_source_footer.add_argument("--signing-secret")
    verify_grounded_source_footer.set_defaults(func=run_verify_grounded_source_footer)

    source_footer_delivery = subparsers.add_parser(
        "source-footer-delivery",
        help="Create a delivery receipt proving a grounded source footer survived response and gateway egress.",
    )
    source_footer_delivery.add_argument("--source-footer-delivery-input", required=True)
    source_footer_delivery.add_argument("--issuer", default="rdllm-local-demo")
    source_footer_delivery.add_argument("--signing-secret")
    source_footer_delivery.add_argument("--output")
    source_footer_delivery.set_defaults(func=run_source_footer_delivery)

    verify_source_footer_delivery = subparsers.add_parser(
        "verify-source-footer-delivery",
        help="Verify a source footer delivery receipt against response and gateway artifacts.",
    )
    verify_source_footer_delivery.add_argument(
        "--source-footer-delivery-input", required=True
    )
    verify_source_footer_delivery.add_argument("--receipt", required=True)
    verify_source_footer_delivery.add_argument("--signing-secret")
    verify_source_footer_delivery.set_defaults(func=run_verify_source_footer_delivery)

    foundation_api_profile = subparsers.add_parser(
        "foundation-api-profile",
        help="Create the minimum foundation-model API attribution profile for generic client verification.",
    )
    foundation_api_profile.add_argument("--foundation-api-profile-input", required=True)
    foundation_api_profile.add_argument("--issuer", default="rdllm-local-demo")
    foundation_api_profile.add_argument("--signing-secret")
    foundation_api_profile.add_argument("--output")
    foundation_api_profile.set_defaults(func=run_foundation_api_profile)

    verify_foundation_api_profile = subparsers.add_parser(
        "verify-foundation-api-profile",
        help="Verify a foundation-model API attribution profile against its public proof inputs.",
    )
    verify_foundation_api_profile.add_argument(
        "--foundation-api-profile-input", required=True
    )
    verify_foundation_api_profile.add_argument("--profile", required=True)
    verify_foundation_api_profile.add_argument("--signing-secret")
    verify_foundation_api_profile.set_defaults(func=run_verify_foundation_api_profile)

    client_attribution = subparsers.add_parser(
        "client-attribution-enforcement",
        help="Create a relying-client receipt proving L104 attribution was verified before rendering.",
    )
    client_attribution.add_argument("--client-attribution-input", required=True)
    client_attribution.add_argument("--issuer", default="rdllm-local-demo")
    client_attribution.add_argument("--signing-secret")
    client_attribution.add_argument("--output")
    client_attribution.set_defaults(func=run_client_attribution_enforcement)

    verify_client_attribution = subparsers.add_parser(
        "verify-client-attribution-enforcement",
        help="Verify a relying-client attribution enforcement receipt.",
    )
    verify_client_attribution.add_argument("--client-attribution-input", required=True)
    verify_client_attribution.add_argument("--receipt", required=True)
    verify_client_attribution.add_argument("--signing-secret")
    verify_client_attribution.set_defaults(
        func=run_verify_client_attribution_enforcement
    )

    persistent_memory = subparsers.add_parser(
        "persistent-memory-provenance",
        help="Create a receipt proving persistent assistant memory carries source, license, and royalty provenance into later answers.",
    )
    persistent_memory.add_argument("--persistent-memory-input", required=True)
    persistent_memory.add_argument("--issuer", default="rdllm-local-demo")
    persistent_memory.add_argument("--signing-secret")
    persistent_memory.add_argument("--output")
    persistent_memory.set_defaults(func=run_persistent_memory_provenance)

    verify_persistent_memory = subparsers.add_parser(
        "verify-persistent-memory-provenance",
        help="Verify a persistent memory provenance receipt.",
    )
    verify_persistent_memory.add_argument("--persistent-memory-input", required=True)
    verify_persistent_memory.add_argument("--receipt", required=True)
    verify_persistent_memory.add_argument("--signing-secret")
    verify_persistent_memory.set_defaults(
        func=run_verify_persistent_memory_provenance
    )

    private_reasoning = subparsers.add_parser(
        "private-reasoning-attribution",
        help="Create a receipt proving private reasoning commitments carry source labels, memory provenance, and royalties into visible footers.",
    )
    private_reasoning.add_argument("--private-reasoning-input", required=True)
    private_reasoning.add_argument("--issuer", default="rdllm-local-demo")
    private_reasoning.add_argument("--signing-secret")
    private_reasoning.add_argument("--output")
    private_reasoning.set_defaults(func=run_private_reasoning_attribution)

    verify_private_reasoning = subparsers.add_parser(
        "verify-private-reasoning-attribution",
        help="Verify a private reasoning attribution receipt.",
    )
    verify_private_reasoning.add_argument("--private-reasoning-input", required=True)
    verify_private_reasoning.add_argument("--receipt", required=True)
    verify_private_reasoning.add_argument("--signing-secret")
    verify_private_reasoning.set_defaults(
        func=run_verify_private_reasoning_attribution
    )

    post_training_signal = subparsers.add_parser(
        "post-training-signal-provenance",
        help="Create a receipt proving RLHF/RLAIF/RLVR preference, reward, and verifier signals preserve source lineage and royalty obligations.",
    )
    post_training_signal.add_argument("--post-training-signal-input", required=True)
    post_training_signal.add_argument("--issuer", default="rdllm-local-demo")
    post_training_signal.add_argument("--signing-secret")
    post_training_signal.add_argument("--output")
    post_training_signal.set_defaults(func=run_post_training_signal_provenance)

    verify_post_training_signal = subparsers.add_parser(
        "verify-post-training-signal-provenance",
        help="Verify a post-training signal provenance receipt.",
    )
    verify_post_training_signal.add_argument(
        "--post-training-signal-input", required=True
    )
    verify_post_training_signal.add_argument("--receipt", required=True)
    verify_post_training_signal.add_argument("--signing-secret")
    verify_post_training_signal.set_defaults(
        func=run_verify_post_training_signal_provenance
    )

    attribution_bom = subparsers.add_parser(
        "attribution-bom",
        help="Create a CycloneDX-aligned attribution bill of materials for model releases and proof supply chains.",
    )
    attribution_bom.add_argument("--attribution-bom-input", required=True)
    attribution_bom.add_argument("--issuer", default="rdllm-local-demo")
    attribution_bom.add_argument("--signing-secret")
    attribution_bom.add_argument("--output")
    attribution_bom.set_defaults(func=run_attribution_bom)

    verify_attribution_bom = subparsers.add_parser(
        "verify-attribution-bom",
        help="Verify an attribution bill of materials.",
    )
    verify_attribution_bom.add_argument("--attribution-bom-input", required=True)
    verify_attribution_bom.add_argument("--bom", required=True)
    verify_attribution_bom.add_argument("--signing-secret")
    verify_attribution_bom.set_defaults(func=run_verify_attribution_bom)

    creator_audit_index = subparsers.add_parser(
        "creator-attribution-audit-index",
        help="Create a creator-facing attribution audit index across proof surfaces.",
    )
    creator_audit_index.add_argument("--audit-input", required=True)
    creator_audit_index.add_argument("--issuer", default="rdllm-local-demo")
    creator_audit_index.add_argument("--signing-secret")
    creator_audit_index.add_argument("--output")
    creator_audit_index.set_defaults(func=run_creator_attribution_audit_index)

    verify_creator_audit_index = subparsers.add_parser(
        "verify-creator-attribution-audit-index",
        help="Verify a creator-facing attribution audit index.",
    )
    verify_creator_audit_index.add_argument("--audit-input", required=True)
    verify_creator_audit_index.add_argument("--index", required=True)
    verify_creator_audit_index.add_argument("--signing-secret")
    verify_creator_audit_index.set_defaults(
        func=run_verify_creator_attribution_audit_index
    )

    creator_audit_federation = subparsers.add_parser(
        "creator-attribution-audit-federation",
        help="Create a cross-provider creator attribution audit federation report.",
    )
    creator_audit_federation.add_argument("--federation-input", required=True)
    creator_audit_federation.add_argument("--issuer", default="rdllm-local-demo")
    creator_audit_federation.add_argument("--signing-secret")
    creator_audit_federation.add_argument("--output")
    creator_audit_federation.set_defaults(
        func=run_creator_attribution_audit_federation
    )

    verify_creator_audit_federation = subparsers.add_parser(
        "verify-creator-attribution-audit-federation",
        help="Verify a cross-provider creator attribution audit federation report.",
    )
    verify_creator_audit_federation.add_argument("--federation-input", required=True)
    verify_creator_audit_federation.add_argument("--report", required=True)
    verify_creator_audit_federation.add_argument("--signing-secret")
    verify_creator_audit_federation.set_defaults(
        func=run_verify_creator_attribution_audit_federation
    )

    creator_audit_federation_transparency_log = subparsers.add_parser(
        "creator-audit-federation-transparency-log",
        help="Create an append-only transparency log for an L111 creator audit federation.",
    )
    creator_audit_federation_transparency_log.add_argument(
        "--federation-report", required=True
    )
    creator_audit_federation_transparency_log.add_argument(
        "--existing-log",
        help="Optional prior creator audit federation transparency log whose entries are preserved as a prefix.",
    )
    creator_audit_federation_transparency_log.add_argument(
        "--log-id", default="creator-audit-federation-transparency"
    )
    creator_audit_federation_transparency_log.add_argument(
        "--exclude-participant-indexes", action="store_true"
    )
    creator_audit_federation_transparency_log.add_argument("--output")
    creator_audit_federation_transparency_log.set_defaults(
        func=run_creator_audit_federation_transparency_log
    )

    creator_audit_federation_transparency = subparsers.add_parser(
        "creator-audit-federation-transparency",
        help="Create an L112 transparency inclusion report for a creator audit federation.",
    )
    creator_audit_federation_transparency.add_argument(
        "--federation-report", required=True
    )
    creator_audit_federation_transparency.add_argument(
        "--transparency-log",
        action="append",
        required=True,
        help="Repeatable name=path or path to a federation transparency log snapshot.",
    )
    creator_audit_federation_transparency.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    creator_audit_federation_transparency.add_argument("--signing-secret")
    creator_audit_federation_transparency.add_argument("--output")
    creator_audit_federation_transparency.set_defaults(
        func=run_creator_audit_federation_transparency
    )

    verify_creator_audit_federation_transparency = subparsers.add_parser(
        "verify-creator-audit-federation-transparency",
        help="Verify an L112 creator audit federation transparency report.",
    )
    verify_creator_audit_federation_transparency.add_argument(
        "--federation-report", required=True
    )
    verify_creator_audit_federation_transparency.add_argument("--report", required=True)
    verify_creator_audit_federation_transparency.add_argument(
        "--transparency-log",
        action="append",
        required=True,
        help="Repeatable name=path or path to a federation transparency log snapshot.",
    )
    verify_creator_audit_federation_transparency.add_argument("--signing-secret")
    verify_creator_audit_federation_transparency.set_defaults(
        func=run_verify_creator_audit_federation_transparency
    )

    creator_audit_transparency_monitor = subparsers.add_parser(
        "creator-audit-transparency-monitor",
        help="Create an L113 creator-side monitor over L112 transparency logs.",
    )
    creator_audit_transparency_monitor.add_argument("--monitor-query", required=True)
    creator_audit_transparency_monitor.add_argument(
        "--transparency-report",
        action="append",
        required=True,
        help="Repeatable path to an L112 creator audit federation transparency report.",
    )
    creator_audit_transparency_monitor.add_argument(
        "--transparency-log",
        action="append",
        required=True,
        help="Repeatable name=path or path to a federation transparency log snapshot.",
    )
    creator_audit_transparency_monitor.add_argument(
        "--previous-monitor",
        help="Optional prior L113 monitor report for append-only continuity.",
    )
    creator_audit_transparency_monitor.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    creator_audit_transparency_monitor.add_argument("--signing-secret")
    creator_audit_transparency_monitor.add_argument("--output")
    creator_audit_transparency_monitor.set_defaults(
        func=run_creator_audit_transparency_monitor
    )

    verify_creator_audit_transparency_monitor = subparsers.add_parser(
        "verify-creator-audit-transparency-monitor",
        help="Verify an L113 creator audit transparency monitor report.",
    )
    verify_creator_audit_transparency_monitor.add_argument(
        "--monitor-query", required=True
    )
    verify_creator_audit_transparency_monitor.add_argument("--report", required=True)
    verify_creator_audit_transparency_monitor.add_argument(
        "--transparency-report",
        action="append",
        required=True,
        help="Repeatable path to an L112 creator audit federation transparency report.",
    )
    verify_creator_audit_transparency_monitor.add_argument(
        "--transparency-log",
        action="append",
        required=True,
        help="Repeatable name=path or path to a federation transparency log snapshot.",
    )
    verify_creator_audit_transparency_monitor.add_argument(
        "--previous-monitor",
        help="Optional prior L113 monitor report for append verification.",
    )
    verify_creator_audit_transparency_monitor.add_argument("--signing-secret")
    verify_creator_audit_transparency_monitor.set_defaults(
        func=run_verify_creator_audit_transparency_monitor
    )

    creator_audit_private_watch = subparsers.add_parser(
        "creator-audit-private-watch",
        help="Create an L114 redacted private watch-token receipt over an L113 monitor.",
    )
    creator_audit_private_watch.add_argument("--watch-input", required=True)
    creator_audit_private_watch.add_argument("--monitor-report", required=True)
    creator_audit_private_watch.add_argument("--issuer", default="rdllm-local-demo")
    creator_audit_private_watch.add_argument("--signing-secret")
    creator_audit_private_watch.add_argument("--output")
    creator_audit_private_watch.set_defaults(func=run_creator_audit_private_watch)

    verify_creator_audit_private_watch = subparsers.add_parser(
        "verify-creator-audit-private-watch",
        help="Verify an L114 creator audit private watch-token receipt.",
    )
    verify_creator_audit_private_watch.add_argument("--watch-input", required=True)
    verify_creator_audit_private_watch.add_argument("--monitor-report", required=True)
    verify_creator_audit_private_watch.add_argument("--report", required=True)
    verify_creator_audit_private_watch.add_argument("--signing-secret")
    verify_creator_audit_private_watch.set_defaults(
        func=run_verify_creator_audit_private_watch
    )

    deep_research_citation_audit = subparsers.add_parser(
        "deep-research-citation-audit",
        help="Create an L115 audit over rendered long-form citations, source materialization, and claim support.",
    )
    deep_research_citation_audit.add_argument("--audit-input", required=True)
    deep_research_citation_audit.add_argument("--issuer", default="rdllm-local-demo")
    deep_research_citation_audit.add_argument("--signing-secret")
    deep_research_citation_audit.add_argument("--output")
    deep_research_citation_audit.set_defaults(
        func=run_deep_research_citation_audit
    )

    verify_deep_research_citation_audit = subparsers.add_parser(
        "verify-deep-research-citation-audit",
        help="Verify an L115 deep-research citation audit.",
    )
    verify_deep_research_citation_audit.add_argument("--audit-input", required=True)
    verify_deep_research_citation_audit.add_argument("--report", required=True)
    verify_deep_research_citation_audit.add_argument("--signing-secret")
    verify_deep_research_citation_audit.set_defaults(
        func=run_verify_deep_research_citation_audit
    )

    source_freshness_audit = subparsers.add_parser(
        "source-freshness-audit",
        help="Create an L116 audit over source recency, temporal validity, retrieval lag, and fresher supported candidates.",
    )
    source_freshness_audit.add_argument("--audit-input", required=True)
    source_freshness_audit.add_argument("--issuer", default="rdllm-local-demo")
    source_freshness_audit.add_argument("--signing-secret")
    source_freshness_audit.add_argument("--output")
    source_freshness_audit.set_defaults(func=run_source_freshness_audit)

    verify_source_freshness_audit = subparsers.add_parser(
        "verify-source-freshness-audit",
        help="Verify an L116 source freshness and temporal-validity audit.",
    )
    verify_source_freshness_audit.add_argument("--audit-input", required=True)
    verify_source_freshness_audit.add_argument("--report", required=True)
    verify_source_freshness_audit.add_argument("--signing-secret")
    verify_source_freshness_audit.set_defaults(func=run_verify_source_freshness_audit)

    royalty_abuse_audit = subparsers.add_parser(
        "royalty-abuse-audit",
        help="Create an L117 audit over source farms, sybil creators, duplicate works, collusion, and payout concentration before direct settlement.",
    )
    royalty_abuse_audit.add_argument("--audit-input", required=True)
    royalty_abuse_audit.add_argument("--issuer", default="rdllm-local-demo")
    royalty_abuse_audit.add_argument("--signing-secret")
    royalty_abuse_audit.add_argument("--output")
    royalty_abuse_audit.set_defaults(func=run_royalty_abuse_audit)

    verify_royalty_abuse_audit = subparsers.add_parser(
        "verify-royalty-abuse-audit",
        help="Verify an L117 royalty-abuse and settlement-integrity audit.",
    )
    verify_royalty_abuse_audit.add_argument("--audit-input", required=True)
    verify_royalty_abuse_audit.add_argument("--report", required=True)
    verify_royalty_abuse_audit.add_argument("--signing-secret")
    verify_royalty_abuse_audit.set_defaults(func=run_verify_royalty_abuse_audit)

    consent_revocation_propagation = subparsers.add_parser(
        "consent-revocation-propagation",
        help="Create an L118 audit proving rights changes propagated across serving, memory, exchange, and settlement surfaces.",
    )
    consent_revocation_propagation.add_argument("--propagation-input", required=True)
    consent_revocation_propagation.add_argument("--issuer", default="rdllm-local-demo")
    consent_revocation_propagation.add_argument("--signing-secret")
    consent_revocation_propagation.add_argument("--output")
    consent_revocation_propagation.set_defaults(
        func=run_consent_revocation_propagation
    )

    verify_consent_revocation_propagation = subparsers.add_parser(
        "verify-consent-revocation-propagation",
        help="Verify an L118 consent and revocation propagation audit.",
    )
    verify_consent_revocation_propagation.add_argument(
        "--propagation-input", required=True
    )
    verify_consent_revocation_propagation.add_argument("--report", required=True)
    verify_consent_revocation_propagation.add_argument("--signing-secret")
    verify_consent_revocation_propagation.set_defaults(
        func=run_verify_consent_revocation_propagation
    )

    evidence_force_calibration = subparsers.add_parser(
        "evidence-force-calibration",
        help="Create an L119 audit proving cited claim wording is no stronger than the supporting evidence warrants.",
    )
    evidence_force_calibration.add_argument("--calibration-input", required=True)
    evidence_force_calibration.add_argument("--issuer", default="rdllm-local-demo")
    evidence_force_calibration.add_argument("--signing-secret")
    evidence_force_calibration.add_argument("--output")
    evidence_force_calibration.set_defaults(func=run_evidence_force_calibration)

    verify_evidence_force_calibration = subparsers.add_parser(
        "verify-evidence-force-calibration",
        help="Verify an L119 evidence-force calibration audit.",
    )
    verify_evidence_force_calibration.add_argument("--calibration-input", required=True)
    verify_evidence_force_calibration.add_argument("--report", required=True)
    verify_evidence_force_calibration.add_argument("--signing-secret")
    verify_evidence_force_calibration.set_defaults(
        func=run_verify_evidence_force_calibration
    )

    warranted_source_footer = subparsers.add_parser(
        "warranted-source-footer",
        help="Create an L120 visible source footer with evidence-force warrant labels.",
    )
    warranted_source_footer.add_argument("--footer-input", required=True)
    warranted_source_footer.add_argument("--issuer", default="rdllm-local-demo")
    warranted_source_footer.add_argument("--signing-secret")
    warranted_source_footer.add_argument("--output")
    warranted_source_footer.set_defaults(func=run_warranted_source_footer)

    verify_warranted_source_footer = subparsers.add_parser(
        "verify-warranted-source-footer",
        help="Verify an L120 warranted source footer.",
    )
    verify_warranted_source_footer.add_argument("--footer-input", required=True)
    verify_warranted_source_footer.add_argument("--report", required=True)
    verify_warranted_source_footer.add_argument("--signing-secret")
    verify_warranted_source_footer.set_defaults(
        func=run_verify_warranted_source_footer
    )

    source_origin_lineage = subparsers.add_parser(
        "source-origin-lineage",
        help="Create an L121 source-origin lineage report that blocks synthetic-source royalty laundering.",
    )
    source_origin_lineage.add_argument("--lineage-input", required=True)
    source_origin_lineage.add_argument("--issuer", default="rdllm-local-demo")
    source_origin_lineage.add_argument("--signing-secret")
    source_origin_lineage.add_argument("--output")
    source_origin_lineage.set_defaults(func=run_source_origin_lineage)

    verify_source_origin_lineage = subparsers.add_parser(
        "verify-source-origin-lineage",
        help="Verify an L121 source-origin lineage report.",
    )
    verify_source_origin_lineage.add_argument("--lineage-input", required=True)
    verify_source_origin_lineage.add_argument("--report", required=True)
    verify_source_origin_lineage.add_argument("--signing-secret")
    verify_source_origin_lineage.set_defaults(func=run_verify_source_origin_lineage)

    evidence_preview_footer = subparsers.add_parser(
        "evidence-preview-footer",
        help="Create an L122 evidence-preview source footer with short permissioned snippets.",
    )
    evidence_preview_footer.add_argument("--preview-input", required=True)
    evidence_preview_footer.add_argument("--issuer", default="rdllm-local-demo")
    evidence_preview_footer.add_argument("--signing-secret")
    evidence_preview_footer.add_argument("--output")
    evidence_preview_footer.set_defaults(func=run_evidence_preview_footer)

    verify_evidence_preview_footer = subparsers.add_parser(
        "verify-evidence-preview-footer",
        help="Verify an L122 evidence-preview source footer.",
    )
    verify_evidence_preview_footer.add_argument("--preview-input", required=True)
    verify_evidence_preview_footer.add_argument("--report", required=True)
    verify_evidence_preview_footer.add_argument("--signing-secret")
    verify_evidence_preview_footer.set_defaults(func=run_verify_evidence_preview_footer)

    evidence_locator_manifest = subparsers.add_parser(
        "evidence-locator-manifest",
        help="Create an L123 exact evidence-locator manifest for preview footer snippets.",
    )
    evidence_locator_manifest.add_argument("--locator-input", required=True)
    evidence_locator_manifest.add_argument("--issuer", default="rdllm-local-demo")
    evidence_locator_manifest.add_argument("--signing-secret")
    evidence_locator_manifest.add_argument("--output")
    evidence_locator_manifest.set_defaults(func=run_evidence_locator_manifest)

    verify_evidence_locator_manifest = subparsers.add_parser(
        "verify-evidence-locator-manifest",
        help="Verify an L123 exact evidence-locator manifest.",
    )
    verify_evidence_locator_manifest.add_argument("--locator-input", required=True)
    verify_evidence_locator_manifest.add_argument("--report", required=True)
    verify_evidence_locator_manifest.add_argument("--signing-secret")
    verify_evidence_locator_manifest.set_defaults(
        func=run_verify_evidence_locator_manifest
    )

    citation_url_health = subparsers.add_parser(
        "citation-url-health",
        help="Create an L124 URL-health report for exact evidence locator URLs.",
    )
    citation_url_health.add_argument("--health-input", required=True)
    citation_url_health.add_argument("--issuer", default="rdllm-local-demo")
    citation_url_health.add_argument("--signing-secret")
    citation_url_health.add_argument("--output")
    citation_url_health.set_defaults(func=run_citation_url_health)

    verify_citation_url_health = subparsers.add_parser(
        "verify-citation-url-health",
        help="Verify an L124 URL-health report for exact evidence locator URLs.",
    )
    verify_citation_url_health.add_argument("--health-input", required=True)
    verify_citation_url_health.add_argument("--report", required=True)
    verify_citation_url_health.add_argument("--signing-secret")
    verify_citation_url_health.set_defaults(func=run_verify_citation_url_health)

    composite_adapter = subparsers.add_parser(
        "composite-foundation-adapter",
        help="Create an L125 provider-neutral adapter report for foundation-model APIs.",
    )
    composite_adapter.add_argument("--adapter-input", required=True)
    composite_adapter.add_argument("--issuer", default="rdllm-local-demo")
    composite_adapter.add_argument("--signing-secret")
    composite_adapter.add_argument("--output")
    composite_adapter.set_defaults(func=run_composite_foundation_adapter)

    verify_composite_adapter = subparsers.add_parser(
        "verify-composite-foundation-adapter",
        help="Verify an L125 provider-neutral foundation adapter report.",
    )
    verify_composite_adapter.add_argument("--adapter-input", required=True)
    verify_composite_adapter.add_argument("--report", required=True)
    verify_composite_adapter.add_argument("--signing-secret")
    verify_composite_adapter.set_defaults(func=run_verify_composite_foundation_adapter)

    provider_conformance = subparsers.add_parser(
        "foundation-provider-conformance",
        help="Create an L126 conformance matrix for attribution-capable provider APIs.",
    )
    provider_conformance.add_argument("--conformance-input", required=True)
    provider_conformance.add_argument("--issuer", default="rdllm-local-demo")
    provider_conformance.add_argument("--signing-secret")
    provider_conformance.add_argument("--output")
    provider_conformance.set_defaults(func=run_foundation_provider_conformance)

    verify_provider_conformance = subparsers.add_parser(
        "verify-foundation-provider-conformance",
        help="Verify an L126 foundation-provider conformance matrix.",
    )
    verify_provider_conformance.add_argument("--conformance-input", required=True)
    verify_provider_conformance.add_argument("--report", required=True)
    verify_provider_conformance.add_argument("--signing-secret")
    verify_provider_conformance.set_defaults(
        func=run_verify_foundation_provider_conformance
    )

    runtime_adapter = subparsers.add_parser(
        "foundation-runtime-adapter",
        help="Create an L127 runtime adapter receipt for one native provider response.",
    )
    runtime_adapter.add_argument("--adapter-input", required=True)
    runtime_adapter.add_argument("--issuer", default="rdllm-local-demo")
    runtime_adapter.add_argument("--signing-secret")
    runtime_adapter.add_argument("--output")
    runtime_adapter.set_defaults(func=run_foundation_runtime_adapter)

    verify_runtime_adapter = subparsers.add_parser(
        "verify-foundation-runtime-adapter",
        help="Verify an L127 native-response runtime adapter receipt.",
    )
    verify_runtime_adapter.add_argument("--adapter-input", required=True)
    verify_runtime_adapter.add_argument("--report", required=True)
    verify_runtime_adapter.add_argument("--signing-secret")
    verify_runtime_adapter.set_defaults(func=run_verify_foundation_runtime_adapter)

    runtime_router = subparsers.add_parser(
        "foundation-runtime-router",
        help="Create an L128 router receipt for a multi-provider foundation-model stack.",
    )
    runtime_router.add_argument("--router-input", required=True)
    runtime_router.add_argument("--issuer", default="rdllm-local-demo")
    runtime_router.add_argument("--signing-secret")
    runtime_router.add_argument("--output")
    runtime_router.set_defaults(func=run_foundation_runtime_router)

    verify_runtime_router = subparsers.add_parser(
        "verify-foundation-runtime-router",
        help="Verify an L128 multi-provider runtime router receipt.",
    )
    verify_runtime_router.add_argument("--router-input", required=True)
    verify_runtime_router.add_argument("--report", required=True)
    verify_runtime_router.add_argument("--signing-secret")
    verify_runtime_router.set_defaults(func=run_verify_foundation_runtime_router)

    deployment_attestation = subparsers.add_parser(
        "foundation-model-deployment-attestation",
        help="Create an L129 attestation binding a selected provider route to a signed model deployment.",
    )
    deployment_attestation.add_argument("--attestation-input", required=True)
    deployment_attestation.add_argument("--issuer", default="rdllm-local-demo")
    deployment_attestation.add_argument("--signing-secret")
    deployment_attestation.add_argument("--output")
    deployment_attestation.set_defaults(
        func=run_foundation_model_deployment_attestation
    )

    verify_deployment_attestation = subparsers.add_parser(
        "verify-foundation-model-deployment-attestation",
        help="Verify an L129 selected-route model deployment attestation.",
    )
    verify_deployment_attestation.add_argument("--attestation-input", required=True)
    verify_deployment_attestation.add_argument("--report", required=True)
    verify_deployment_attestation.add_argument("--signing-secret")
    verify_deployment_attestation.set_defaults(
        func=run_verify_foundation_model_deployment_attestation
    )

    universal_composition = subparsers.add_parser(
        "universal-composition-receipt",
        help="Create an L130 receipt for a multi-provider composite foundation-model answer.",
    )
    universal_composition.add_argument("--composition-input", required=True)
    universal_composition.add_argument("--issuer", default="rdllm-local-demo")
    universal_composition.add_argument("--signing-secret")
    universal_composition.add_argument("--output")
    universal_composition.set_defaults(func=run_universal_composition_receipt)

    verify_universal_composition = subparsers.add_parser(
        "verify-universal-composition-receipt",
        help="Verify an L130 multi-provider universal composition receipt.",
    )
    verify_universal_composition.add_argument("--composition-input", required=True)
    verify_universal_composition.add_argument("--report", required=True)
    verify_universal_composition.add_argument("--signing-secret")
    verify_universal_composition.set_defaults(
        func=run_verify_universal_composition_receipt
    )

    universal_composition_settlement = subparsers.add_parser(
        "universal-composition-settlement",
        help="Create an L131 settlement receipt for a multi-provider composite answer.",
    )
    universal_composition_settlement.add_argument("--settlement-input", required=True)
    universal_composition_settlement.add_argument("--issuer", default="rdllm-local-demo")
    universal_composition_settlement.add_argument("--signing-secret")
    universal_composition_settlement.add_argument("--output")
    universal_composition_settlement.set_defaults(
        func=run_universal_composition_settlement
    )

    verify_universal_composition_settlement = subparsers.add_parser(
        "verify-universal-composition-settlement",
        help="Verify an L131 universal composition settlement receipt.",
    )
    verify_universal_composition_settlement.add_argument(
        "--settlement-input", required=True
    )
    verify_universal_composition_settlement.add_argument("--report", required=True)
    verify_universal_composition_settlement.add_argument("--signing-secret")
    verify_universal_composition_settlement.set_defaults(
        func=run_verify_universal_composition_settlement
    )

    universal_foundation_model_contract = subparsers.add_parser(
        "universal-foundation-model-contract",
        help="Create an L132 universal foundation-model RDLLM contract.",
    )
    universal_foundation_model_contract.add_argument("--contract-input", required=True)
    universal_foundation_model_contract.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_foundation_model_contract.add_argument("--signing-secret")
    universal_foundation_model_contract.add_argument("--output")
    universal_foundation_model_contract.set_defaults(
        func=run_universal_foundation_model_contract
    )

    verify_universal_foundation_model_contract = subparsers.add_parser(
        "verify-universal-foundation-model-contract",
        help="Verify an L132 universal foundation-model RDLLM contract.",
    )
    verify_universal_foundation_model_contract.add_argument(
        "--contract-input", required=True
    )
    verify_universal_foundation_model_contract.add_argument("--report", required=True)
    verify_universal_foundation_model_contract.add_argument("--signing-secret")
    verify_universal_foundation_model_contract.set_defaults(
        func=run_verify_universal_foundation_model_contract
    )

    universal_invocation_guard = subparsers.add_parser(
        "universal-invocation-guard",
        help="Create an L133 preflight guard for a universal foundation-model invocation.",
    )
    universal_invocation_guard.add_argument("--guard-input", required=True)
    universal_invocation_guard.add_argument("--issuer", default="rdllm-local-demo")
    universal_invocation_guard.add_argument("--signing-secret")
    universal_invocation_guard.add_argument("--output")
    universal_invocation_guard.set_defaults(func=run_universal_invocation_guard)

    verify_universal_invocation_guard = subparsers.add_parser(
        "verify-universal-invocation-guard",
        help="Verify an L133 universal foundation-model invocation guard.",
    )
    verify_universal_invocation_guard.add_argument("--guard-input", required=True)
    verify_universal_invocation_guard.add_argument("--report", required=True)
    verify_universal_invocation_guard.add_argument("--signing-secret")
    verify_universal_invocation_guard.set_defaults(
        func=run_verify_universal_invocation_guard
    )

    universal_invocation_coverage = subparsers.add_parser(
        "universal-invocation-coverage",
        help="Create an L134 deployment-wide coverage report for universal provider invocations.",
    )
    universal_invocation_coverage.add_argument("--coverage-input", required=True)
    universal_invocation_coverage.add_argument("--issuer", default="rdllm-local-demo")
    universal_invocation_coverage.add_argument("--signing-secret")
    universal_invocation_coverage.add_argument("--output")
    universal_invocation_coverage.set_defaults(
        func=run_universal_invocation_coverage
    )

    verify_universal_invocation_coverage = subparsers.add_parser(
        "verify-universal-invocation-coverage",
        help="Verify an L134 universal invocation coverage report.",
    )
    verify_universal_invocation_coverage.add_argument(
        "--coverage-input", required=True
    )
    verify_universal_invocation_coverage.add_argument("--report", required=True)
    verify_universal_invocation_coverage.add_argument("--signing-secret")
    verify_universal_invocation_coverage.set_defaults(
        func=run_verify_universal_invocation_coverage
    )

    universal_invocation_witness = subparsers.add_parser(
        "universal-invocation-witness",
        help="Create an L135 non-repudiation witness report for universal provider invocations.",
    )
    universal_invocation_witness.add_argument("--witness-input", required=True)
    universal_invocation_witness.add_argument("--issuer", default="rdllm-local-demo")
    universal_invocation_witness.add_argument("--signing-secret")
    universal_invocation_witness.add_argument("--output")
    universal_invocation_witness.set_defaults(func=run_universal_invocation_witness)

    verify_universal_invocation_witness = subparsers.add_parser(
        "verify-universal-invocation-witness",
        help="Verify an L135 universal invocation witness report.",
    )
    verify_universal_invocation_witness.add_argument("--witness-input", required=True)
    verify_universal_invocation_witness.add_argument("--report", required=True)
    verify_universal_invocation_witness.add_argument("--signing-secret")
    verify_universal_invocation_witness.set_defaults(
        func=run_verify_universal_invocation_witness
    )

    universal_content_credential = subparsers.add_parser(
        "universal-content-credential",
        help="Create an L136 portable content credential binding attribution, payout, provenance, and invocation witness evidence.",
    )
    universal_content_credential.add_argument("--credential-input", required=True)
    universal_content_credential.add_argument("--issuer", default="rdllm-local-demo")
    universal_content_credential.add_argument("--signing-secret")
    universal_content_credential.add_argument("--output")
    universal_content_credential.set_defaults(
        func=run_universal_content_credential
    )

    verify_universal_content_credential = subparsers.add_parser(
        "verify-universal-content-credential",
        help="Verify an L136 universal content credential against replay inputs.",
    )
    verify_universal_content_credential.add_argument(
        "--credential-input", required=True
    )
    verify_universal_content_credential.add_argument("--credential", required=True)
    verify_universal_content_credential.add_argument("--signing-secret")
    verify_universal_content_credential.set_defaults(
        func=run_verify_universal_content_credential
    )

    universal_rdllm_passport = subparsers.add_parser(
        "universal-rdllm-passport",
        help="Create an L137 universal RDLLM deployment passport for provider adoption.",
    )
    universal_rdllm_passport.add_argument("--passport-input", required=True)
    universal_rdllm_passport.add_argument("--issuer", default="rdllm-local-demo")
    universal_rdllm_passport.add_argument("--signing-secret")
    universal_rdllm_passport.add_argument("--output")
    universal_rdllm_passport.set_defaults(func=run_universal_rdllm_passport)

    verify_universal_rdllm_passport = subparsers.add_parser(
        "verify-universal-rdllm-passport",
        help="Verify an L137 universal RDLLM passport against replay inputs.",
    )
    verify_universal_rdllm_passport.add_argument("--passport-input", required=True)
    verify_universal_rdllm_passport.add_argument("--passport", required=True)
    verify_universal_rdllm_passport.add_argument("--signing-secret")
    verify_universal_rdllm_passport.set_defaults(
        func=run_verify_universal_rdllm_passport
    )

    universal_adoption_standard = subparsers.add_parser(
        "universal-adoption-standard",
        help="Create an L138 implementer-facing universal RDLLM adoption standard.",
    )
    universal_adoption_standard.add_argument("--standard-input", required=True)
    universal_adoption_standard.add_argument("--issuer", default="rdllm-local-demo")
    universal_adoption_standard.add_argument("--signing-secret")
    universal_adoption_standard.add_argument("--output")
    universal_adoption_standard.set_defaults(
        func=run_universal_adoption_standard
    )

    verify_universal_adoption_standard = subparsers.add_parser(
        "verify-universal-adoption-standard",
        help="Verify an L138 universal RDLLM adoption standard against replay inputs.",
    )
    verify_universal_adoption_standard.add_argument(
        "--standard-input", required=True
    )
    verify_universal_adoption_standard.add_argument("--standard", required=True)
    verify_universal_adoption_standard.add_argument("--signing-secret")
    verify_universal_adoption_standard.set_defaults(
        func=run_verify_universal_adoption_standard
    )

    universal_interop_test_kit = subparsers.add_parser(
        "universal-interop-test-kit",
        help="Create an L139 universal RDLLM interoperability test kit.",
    )
    universal_interop_test_kit.add_argument("--kit-input", required=True)
    universal_interop_test_kit.add_argument("--issuer", default="rdllm-local-demo")
    universal_interop_test_kit.add_argument("--signing-secret")
    universal_interop_test_kit.add_argument("--output")
    universal_interop_test_kit.set_defaults(
        func=run_universal_interop_test_kit
    )

    verify_universal_interop_test_kit = subparsers.add_parser(
        "verify-universal-interop-test-kit",
        help="Verify an L139 universal RDLLM interop test kit against replay inputs.",
    )
    verify_universal_interop_test_kit.add_argument("--kit-input", required=True)
    verify_universal_interop_test_kit.add_argument("--kit", required=True)
    verify_universal_interop_test_kit.add_argument("--signing-secret")
    verify_universal_interop_test_kit.set_defaults(
        func=run_verify_universal_interop_test_kit
    )

    universal_context_bridge = subparsers.add_parser(
        "universal-context-provenance-bridge",
        help="Create an L140 universal RDLLM context provenance bridge.",
    )
    universal_context_bridge.add_argument("--bridge-input", required=True)
    universal_context_bridge.add_argument("--issuer", default="rdllm-local-demo")
    universal_context_bridge.add_argument("--signing-secret")
    universal_context_bridge.add_argument("--output")
    universal_context_bridge.set_defaults(
        func=run_universal_context_provenance_bridge
    )

    verify_universal_context_bridge = subparsers.add_parser(
        "verify-universal-context-provenance-bridge",
        help="Verify an L140 universal RDLLM context provenance bridge against replay inputs.",
    )
    verify_universal_context_bridge.add_argument("--bridge-input", required=True)
    verify_universal_context_bridge.add_argument("--bridge", required=True)
    verify_universal_context_bridge.add_argument("--signing-secret")
    verify_universal_context_bridge.set_defaults(
        func=run_verify_universal_context_provenance_bridge
    )

    universal_citation_contract = subparsers.add_parser(
        "universal-citation-verification-contract",
        help="Create an L141 universal RDLLM citation verification contract.",
    )
    universal_citation_contract.add_argument("--contract-input", required=True)
    universal_citation_contract.add_argument("--issuer", default="rdllm-local-demo")
    universal_citation_contract.add_argument("--signing-secret")
    universal_citation_contract.add_argument("--output")
    universal_citation_contract.set_defaults(
        func=run_universal_citation_verification_contract
    )

    verify_universal_citation_contract = subparsers.add_parser(
        "verify-universal-citation-verification-contract",
        help="Verify an L141 universal RDLLM citation verification contract against replay inputs.",
    )
    verify_universal_citation_contract.add_argument("--contract-input", required=True)
    verify_universal_citation_contract.add_argument("--contract", required=True)
    verify_universal_citation_contract.add_argument("--signing-secret")
    verify_universal_citation_contract.set_defaults(
        func=run_verify_universal_citation_verification_contract
    )

    universal_grounded_reuse_contract = subparsers.add_parser(
        "universal-grounded-reuse-contract",
        help="Create an L142 universal RDLLM grounded reuse contract.",
    )
    universal_grounded_reuse_contract.add_argument("--reuse-input", required=True)
    universal_grounded_reuse_contract.add_argument("--issuer", default="rdllm-local-demo")
    universal_grounded_reuse_contract.add_argument("--signing-secret")
    universal_grounded_reuse_contract.add_argument("--output")
    universal_grounded_reuse_contract.set_defaults(
        func=run_universal_grounded_reuse_contract
    )

    verify_universal_grounded_reuse_contract = subparsers.add_parser(
        "verify-universal-grounded-reuse-contract",
        help="Verify an L142 universal RDLLM grounded reuse contract against replay inputs.",
    )
    verify_universal_grounded_reuse_contract.add_argument("--reuse-input", required=True)
    verify_universal_grounded_reuse_contract.add_argument("--contract", required=True)
    verify_universal_grounded_reuse_contract.add_argument("--signing-secret")
    verify_universal_grounded_reuse_contract.set_defaults(
        func=run_verify_universal_grounded_reuse_contract
    )

    universal_training_serving_contract = subparsers.add_parser(
        "universal-training-serving-contract",
        help="Create an L143 universal RDLLM training-to-serving attribution contract.",
    )
    universal_training_serving_contract.add_argument("--contract-input", required=True)
    universal_training_serving_contract.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_training_serving_contract.add_argument("--signing-secret")
    universal_training_serving_contract.add_argument("--output")
    universal_training_serving_contract.set_defaults(
        func=run_universal_training_serving_contract
    )

    verify_universal_training_serving_contract = subparsers.add_parser(
        "verify-universal-training-serving-contract",
        help="Verify an L143 universal RDLLM training-to-serving contract against replay inputs.",
    )
    verify_universal_training_serving_contract.add_argument(
        "--contract-input", required=True
    )
    verify_universal_training_serving_contract.add_argument("--contract", required=True)
    verify_universal_training_serving_contract.add_argument("--signing-secret")
    verify_universal_training_serving_contract.set_defaults(
        func=run_verify_universal_training_serving_contract
    )

    universal_confidential_attribution_audit = subparsers.add_parser(
        "universal-confidential-attribution-audit",
        help="Create an L144 confidential attribution audit contract for universal RDLLM deployments.",
    )
    universal_confidential_attribution_audit.add_argument(
        "--audit-input", required=True
    )
    universal_confidential_attribution_audit.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_confidential_attribution_audit.add_argument("--signing-secret")
    universal_confidential_attribution_audit.add_argument("--output")
    universal_confidential_attribution_audit.set_defaults(
        func=run_universal_confidential_attribution_audit
    )

    verify_universal_confidential_attribution_audit = subparsers.add_parser(
        "verify-universal-confidential-attribution-audit",
        help="Verify an L144 confidential attribution audit against replay inputs.",
    )
    verify_universal_confidential_attribution_audit.add_argument(
        "--audit-input", required=True
    )
    verify_universal_confidential_attribution_audit.add_argument(
        "--audit", required=True
    )
    verify_universal_confidential_attribution_audit.add_argument("--signing-secret")
    verify_universal_confidential_attribution_audit.set_defaults(
        func=run_verify_universal_confidential_attribution_audit
    )

    universal_attribution_authority_control_plane = subparsers.add_parser(
        "universal-attribution-authority-control-plane",
        help="Create an L145 universal attribution authority control plane for foundation-model and agent runtimes.",
    )
    universal_attribution_authority_control_plane.add_argument(
        "--control-input", required=True
    )
    universal_attribution_authority_control_plane.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_attribution_authority_control_plane.add_argument("--signing-secret")
    universal_attribution_authority_control_plane.add_argument("--output")
    universal_attribution_authority_control_plane.set_defaults(
        func=run_universal_attribution_authority_control_plane
    )

    verify_universal_attribution_authority_control_plane = subparsers.add_parser(
        "verify-universal-attribution-authority-control-plane",
        help="Verify an L145 authority control plane against replay inputs.",
    )
    verify_universal_attribution_authority_control_plane.add_argument(
        "--control-input", required=True
    )
    verify_universal_attribution_authority_control_plane.add_argument(
        "--control-plane", required=True
    )
    verify_universal_attribution_authority_control_plane.add_argument(
        "--signing-secret"
    )
    verify_universal_attribution_authority_control_plane.set_defaults(
        func=run_verify_universal_attribution_authority_control_plane
    )

    universal_rdllm_root = subparsers.add_parser(
        "universal-rdllm-root",
        help="Create an L146 universal RDLLM root of trust for provider-neutral attribution, source-footer, audit, authority, and settlement proof.",
    )
    universal_rdllm_root.add_argument("--root-input", required=True)
    universal_rdllm_root.add_argument("--issuer", default="rdllm-local-demo")
    universal_rdllm_root.add_argument("--signing-secret")
    universal_rdllm_root.add_argument("--output")
    universal_rdllm_root.set_defaults(func=run_universal_rdllm_root)

    verify_universal_rdllm_root = subparsers.add_parser(
        "verify-universal-rdllm-root",
        help="Verify an L146 universal RDLLM root against replay inputs.",
    )
    verify_universal_rdllm_root.add_argument("--root-input", required=True)
    verify_universal_rdllm_root.add_argument("--root", required=True)
    verify_universal_rdllm_root.add_argument("--signing-secret")
    verify_universal_rdllm_root.set_defaults(func=run_verify_universal_rdllm_root)

    universal_emission_enforcement_gateway = subparsers.add_parser(
        "universal-emission-enforcement-gateway",
        help="Create an L147 per-response enforcement proof that binds the L146 root, proof response, source footer, invocation witness, live witness, transparency, gateway egress, and client display enforcement.",
    )
    universal_emission_enforcement_gateway.add_argument(
        "--gateway-input", required=True
    )
    universal_emission_enforcement_gateway.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_emission_enforcement_gateway.add_argument("--signing-secret")
    universal_emission_enforcement_gateway.add_argument("--output")
    universal_emission_enforcement_gateway.set_defaults(
        func=run_universal_emission_enforcement_gateway
    )

    verify_universal_emission_enforcement_gateway = subparsers.add_parser(
        "verify-universal-emission-enforcement-gateway",
        help="Verify an L147 universal emission enforcement gateway against replay inputs.",
    )
    verify_universal_emission_enforcement_gateway.add_argument(
        "--gateway-input", required=True
    )
    verify_universal_emission_enforcement_gateway.add_argument(
        "--gateway", required=True
    )
    verify_universal_emission_enforcement_gateway.add_argument("--signing-secret")
    verify_universal_emission_enforcement_gateway.set_defaults(
        func=run_verify_universal_emission_enforcement_gateway
    )

    universal_composite_rdllm_profile = subparsers.add_parser(
        "universal-composite-rdllm-profile",
        help="Create an L148 universal composite RDLLM profile for provider-neutral foundation-model adoption.",
    )
    universal_composite_rdllm_profile.add_argument(
        "--profile-input", required=True
    )
    universal_composite_rdllm_profile.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_composite_rdllm_profile.add_argument("--signing-secret")
    universal_composite_rdllm_profile.add_argument("--output")
    universal_composite_rdllm_profile.set_defaults(
        func=run_universal_composite_rdllm_profile
    )

    verify_universal_composite_rdllm_profile = subparsers.add_parser(
        "verify-universal-composite-rdllm-profile",
        help="Verify an L148 universal composite RDLLM profile against replay inputs.",
    )
    verify_universal_composite_rdllm_profile.add_argument(
        "--profile-input", required=True
    )
    verify_universal_composite_rdllm_profile.add_argument(
        "--profile", required=True
    )
    verify_universal_composite_rdllm_profile.add_argument("--signing-secret")
    verify_universal_composite_rdllm_profile.set_defaults(
        func=run_verify_universal_composite_rdllm_profile
    )

    universal_runtime_conformance_receipt = subparsers.add_parser(
        "universal-runtime-conformance-receipt",
        help="Create an L149 deployable runtime conformance receipt for source-footered, metered, telemetry-bound foundation-model routes.",
    )
    universal_runtime_conformance_receipt.add_argument(
        "--receipt-input", required=True
    )
    universal_runtime_conformance_receipt.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_runtime_conformance_receipt.add_argument("--signing-secret")
    universal_runtime_conformance_receipt.add_argument("--output")
    universal_runtime_conformance_receipt.set_defaults(
        func=run_universal_runtime_conformance_receipt
    )

    verify_universal_runtime_conformance_receipt = subparsers.add_parser(
        "verify-universal-runtime-conformance-receipt",
        help="Verify an L149 universal runtime conformance receipt against replay inputs.",
    )
    verify_universal_runtime_conformance_receipt.add_argument(
        "--receipt-input", required=True
    )
    verify_universal_runtime_conformance_receipt.add_argument(
        "--receipt", required=True
    )
    verify_universal_runtime_conformance_receipt.add_argument("--signing-secret")
    verify_universal_runtime_conformance_receipt.set_defaults(
        func=run_verify_universal_runtime_conformance_receipt
    )

    universal_claim_provenance_envelope = subparsers.add_parser(
        "universal-claim-provenance-envelope",
        help="Create an L150 claim-level generative provenance envelope that blocks post-hoc citation-only answers.",
    )
    universal_claim_provenance_envelope.add_argument(
        "--envelope-input", required=True
    )
    universal_claim_provenance_envelope.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_claim_provenance_envelope.add_argument("--signing-secret")
    universal_claim_provenance_envelope.add_argument("--output")
    universal_claim_provenance_envelope.set_defaults(
        func=run_universal_claim_provenance_envelope
    )

    verify_universal_claim_provenance_envelope = subparsers.add_parser(
        "verify-universal-claim-provenance-envelope",
        help="Verify an L150 claim provenance envelope against replay inputs.",
    )
    verify_universal_claim_provenance_envelope.add_argument(
        "--envelope-input", required=True
    )
    verify_universal_claim_provenance_envelope.add_argument(
        "--envelope", required=True
    )
    verify_universal_claim_provenance_envelope.add_argument("--signing-secret")
    verify_universal_claim_provenance_envelope.set_defaults(
        func=run_verify_universal_claim_provenance_envelope
    )

    universal_provider_wire_protocol = subparsers.add_parser(
        "universal-provider-wire-protocol",
        help="Create an L151 provider-neutral wire protocol binding provider APIs, streams, proxies, SDK metadata, and callbacks to L150 provenance.",
    )
    universal_provider_wire_protocol.add_argument(
        "--protocol-input", required=True
    )
    universal_provider_wire_protocol.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_provider_wire_protocol.add_argument("--signing-secret")
    universal_provider_wire_protocol.add_argument("--output")
    universal_provider_wire_protocol.set_defaults(
        func=run_universal_provider_wire_protocol
    )

    verify_universal_provider_wire_protocol = subparsers.add_parser(
        "verify-universal-provider-wire-protocol",
        help="Verify an L151 provider wire protocol against replay inputs.",
    )
    verify_universal_provider_wire_protocol.add_argument(
        "--protocol-input", required=True
    )
    verify_universal_provider_wire_protocol.add_argument(
        "--protocol", required=True
    )
    verify_universal_provider_wire_protocol.add_argument("--signing-secret")
    verify_universal_provider_wire_protocol.set_defaults(
        func=run_verify_universal_provider_wire_protocol
    )

    universal_accountability_audit_trail = subparsers.add_parser(
        "universal-accountability-audit-trail",
        help="Create an L152 append-only accountability audit trail binding provider wire calls, agents, tools, governance, exports, and settlement.",
    )
    universal_accountability_audit_trail.add_argument(
        "--audit-input", required=True
    )
    universal_accountability_audit_trail.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_accountability_audit_trail.add_argument("--signing-secret")
    universal_accountability_audit_trail.add_argument("--output")
    universal_accountability_audit_trail.set_defaults(
        func=run_universal_accountability_audit_trail
    )

    verify_universal_accountability_audit_trail = subparsers.add_parser(
        "verify-universal-accountability-audit-trail",
        help="Verify an L152 accountability audit trail against private replay inputs.",
    )
    verify_universal_accountability_audit_trail.add_argument(
        "--audit-input", required=True
    )
    verify_universal_accountability_audit_trail.add_argument(
        "--audit-trail", required=True
    )
    verify_universal_accountability_audit_trail.add_argument("--signing-secret")
    verify_universal_accountability_audit_trail.set_defaults(
        func=run_verify_universal_accountability_audit_trail
    )

    universal_accountability_witness_quorum = subparsers.add_parser(
        "universal-accountability-witness-quorum",
        help="Create an L153 witness quorum over L152 accountability audit-trail checkpoints.",
    )
    universal_accountability_witness_quorum.add_argument(
        "--quorum-input", required=True
    )
    universal_accountability_witness_quorum.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_accountability_witness_quorum.add_argument("--signing-secret")
    universal_accountability_witness_quorum.add_argument("--output")
    universal_accountability_witness_quorum.set_defaults(
        func=run_universal_accountability_witness_quorum
    )

    verify_universal_accountability_witness_quorum = subparsers.add_parser(
        "verify-universal-accountability-witness-quorum",
        help="Verify an L153 accountability witness quorum against replay inputs.",
    )
    verify_universal_accountability_witness_quorum.add_argument(
        "--quorum-input", required=True
    )
    verify_universal_accountability_witness_quorum.add_argument(
        "--quorum", required=True
    )
    verify_universal_accountability_witness_quorum.add_argument("--signing-secret")
    verify_universal_accountability_witness_quorum.set_defaults(
        func=run_verify_universal_accountability_witness_quorum
    )

    universal_grounded_reliance_contract = subparsers.add_parser(
        "universal-grounded-reliance-contract",
        help="Create an L154 grounded reliance contract for source footers, evidence support, and settlement claims.",
    )
    universal_grounded_reliance_contract.add_argument(
        "--contract-input", required=True
    )
    universal_grounded_reliance_contract.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_grounded_reliance_contract.add_argument("--signing-secret")
    universal_grounded_reliance_contract.add_argument("--output")
    universal_grounded_reliance_contract.set_defaults(
        func=run_universal_grounded_reliance_contract
    )

    verify_universal_grounded_reliance_contract = subparsers.add_parser(
        "verify-universal-grounded-reliance-contract",
        help="Verify an L154 grounded reliance contract against replay inputs.",
    )
    verify_universal_grounded_reliance_contract.add_argument(
        "--contract-input", required=True
    )
    verify_universal_grounded_reliance_contract.add_argument(
        "--contract", required=True
    )
    verify_universal_grounded_reliance_contract.add_argument("--signing-secret")
    verify_universal_grounded_reliance_contract.set_defaults(
        func=run_verify_universal_grounded_reliance_contract
    )

    universal_reliance_correction_ledger = subparsers.add_parser(
        "universal-reliance-correction-ledger",
        help="Create an L155 correction ledger for live source, footer, copied-output, cache, and settlement status.",
    )
    universal_reliance_correction_ledger.add_argument(
        "--ledger-input", required=True
    )
    universal_reliance_correction_ledger.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_reliance_correction_ledger.add_argument("--signing-secret")
    universal_reliance_correction_ledger.add_argument("--output")
    universal_reliance_correction_ledger.set_defaults(
        func=run_universal_reliance_correction_ledger
    )

    verify_universal_reliance_correction_ledger = subparsers.add_parser(
        "verify-universal-reliance-correction-ledger",
        help="Verify an L155 correction ledger against replay inputs.",
    )
    verify_universal_reliance_correction_ledger.add_argument(
        "--ledger-input", required=True
    )
    verify_universal_reliance_correction_ledger.add_argument(
        "--ledger", required=True
    )
    verify_universal_reliance_correction_ledger.add_argument("--signing-secret")
    verify_universal_reliance_correction_ledger.set_defaults(
        func=run_verify_universal_reliance_correction_ledger
    )

    universal_foundation_adoption_kernel = subparsers.add_parser(
        "universal-foundation-adoption-kernel",
        help="Create an L156 provider-neutral adoption kernel for source footers, status resolvers, metadata, telemetry, fixtures, and fail-closed foundation-model APIs.",
    )
    universal_foundation_adoption_kernel.add_argument(
        "--kernel-input", required=True
    )
    universal_foundation_adoption_kernel.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_foundation_adoption_kernel.add_argument("--signing-secret")
    universal_foundation_adoption_kernel.add_argument("--output")
    universal_foundation_adoption_kernel.set_defaults(
        func=run_universal_foundation_adoption_kernel
    )

    verify_universal_foundation_adoption_kernel = subparsers.add_parser(
        "verify-universal-foundation-adoption-kernel",
        help="Verify an L156 universal foundation adoption kernel against replay inputs.",
    )
    verify_universal_foundation_adoption_kernel.add_argument(
        "--kernel-input", required=True
    )
    verify_universal_foundation_adoption_kernel.add_argument(
        "--kernel", required=True
    )
    verify_universal_foundation_adoption_kernel.add_argument("--signing-secret")
    verify_universal_foundation_adoption_kernel.set_defaults(
        func=run_verify_universal_foundation_adoption_kernel
    )

    universal_provider_adapter_harness = subparsers.add_parser(
        "universal-provider-adapter-harness",
        help="Create an L157 provider adapter harness proving native provider fixtures normalize into one source-footered, claim-bound RDLLM response contract.",
    )
    universal_provider_adapter_harness.add_argument(
        "--harness-input", required=True
    )
    universal_provider_adapter_harness.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_provider_adapter_harness.add_argument("--signing-secret")
    universal_provider_adapter_harness.add_argument("--output")
    universal_provider_adapter_harness.set_defaults(
        func=run_universal_provider_adapter_harness
    )

    verify_universal_provider_adapter_harness = subparsers.add_parser(
        "verify-universal-provider-adapter-harness",
        help="Verify an L157 universal provider adapter harness against replay inputs.",
    )
    verify_universal_provider_adapter_harness.add_argument(
        "--harness-input", required=True
    )
    verify_universal_provider_adapter_harness.add_argument(
        "--harness", required=True
    )
    verify_universal_provider_adapter_harness.add_argument("--signing-secret")
    verify_universal_provider_adapter_harness.set_defaults(
        func=run_verify_universal_provider_adapter_harness
    )

    universal_provider_drift_sentinel = subparsers.add_parser(
        "universal-provider-drift-sentinel",
        help="Create an L158 provider drift sentinel proving provider API, SDK, model-alias, stream, gateway, citation, and settlement drift are continuously replayed and revoked before grounded display or payout.",
    )
    universal_provider_drift_sentinel.add_argument(
        "--sentinel-input", required=True
    )
    universal_provider_drift_sentinel.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_provider_drift_sentinel.add_argument("--signing-secret")
    universal_provider_drift_sentinel.add_argument("--output")
    universal_provider_drift_sentinel.set_defaults(
        func=run_universal_provider_drift_sentinel
    )

    verify_universal_provider_drift_sentinel = subparsers.add_parser(
        "verify-universal-provider-drift-sentinel",
        help="Verify an L158 universal provider drift sentinel against replay inputs.",
    )
    verify_universal_provider_drift_sentinel.add_argument(
        "--sentinel-input", required=True
    )
    verify_universal_provider_drift_sentinel.add_argument(
        "--sentinel", required=True
    )
    verify_universal_provider_drift_sentinel.add_argument("--signing-secret")
    verify_universal_provider_drift_sentinel.set_defaults(
        func=run_verify_universal_provider_drift_sentinel
    )

    universal_attribution_negotiation_handshake = subparsers.add_parser(
        "universal-attribution-negotiation-handshake",
        help="Create an L159 request-time attribution negotiation handshake proving a client and provider route agreed on source-footer, citation-locator, drift, telemetry, copy/export, and settlement contracts before generation.",
    )
    universal_attribution_negotiation_handshake.add_argument(
        "--handshake-input", required=True
    )
    universal_attribution_negotiation_handshake.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_attribution_negotiation_handshake.add_argument("--signing-secret")
    universal_attribution_negotiation_handshake.add_argument("--output")
    universal_attribution_negotiation_handshake.set_defaults(
        func=run_universal_attribution_negotiation_handshake
    )

    verify_universal_attribution_negotiation_handshake = subparsers.add_parser(
        "verify-universal-attribution-negotiation-handshake",
        help="Verify an L159 universal attribution negotiation handshake against replay inputs.",
    )
    verify_universal_attribution_negotiation_handshake.add_argument(
        "--handshake-input", required=True
    )
    verify_universal_attribution_negotiation_handshake.add_argument(
        "--handshake", required=True
    )
    verify_universal_attribution_negotiation_handshake.add_argument(
        "--signing-secret"
    )
    verify_universal_attribution_negotiation_handshake.set_defaults(
        func=run_verify_universal_attribution_negotiation_handshake
    )

    universal_negotiated_invocation_enforcement = subparsers.add_parser(
        "universal-negotiated-invocation-enforcement",
        help="Create an L160 invocation enforcement artifact proving every SDK, proxy, stream, tool, MCP, retrieval, batch, fallback, and cache route used the negotiated attribution contract before model invocation.",
    )
    universal_negotiated_invocation_enforcement.add_argument(
        "--enforcement-input", required=True
    )
    universal_negotiated_invocation_enforcement.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_negotiated_invocation_enforcement.add_argument("--signing-secret")
    universal_negotiated_invocation_enforcement.add_argument("--output")
    universal_negotiated_invocation_enforcement.set_defaults(
        func=run_universal_negotiated_invocation_enforcement
    )

    verify_universal_negotiated_invocation_enforcement = subparsers.add_parser(
        "verify-universal-negotiated-invocation-enforcement",
        help="Verify an L160 universal negotiated invocation enforcement artifact against replay inputs.",
    )
    verify_universal_negotiated_invocation_enforcement.add_argument(
        "--enforcement-input", required=True
    )
    verify_universal_negotiated_invocation_enforcement.add_argument(
        "--enforcement", required=True
    )
    verify_universal_negotiated_invocation_enforcement.add_argument(
        "--signing-secret"
    )
    verify_universal_negotiated_invocation_enforcement.set_defaults(
        func=run_verify_universal_negotiated_invocation_enforcement
    )

    universal_certification_trust_federation = subparsers.add_parser(
        "universal-certification-trust-federation",
        help="Create an L161 trust-federation artifact binding L160 proof packs to trust anchors, accredited certifiers, trust marks, verifiable credentials, transparency logs, revocation status, and relying-party policy.",
    )
    universal_certification_trust_federation.add_argument(
        "--federation-input", required=True
    )
    universal_certification_trust_federation.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_certification_trust_federation.add_argument("--signing-secret")
    universal_certification_trust_federation.add_argument("--output")
    universal_certification_trust_federation.set_defaults(
        func=run_universal_certification_trust_federation
    )

    verify_universal_certification_trust_federation = subparsers.add_parser(
        "verify-universal-certification-trust-federation",
        help="Verify an L161 universal certification trust federation artifact against replay inputs.",
    )
    verify_universal_certification_trust_federation.add_argument(
        "--federation-input", required=True
    )
    verify_universal_certification_trust_federation.add_argument(
        "--federation", required=True
    )
    verify_universal_certification_trust_federation.add_argument("--signing-secret")
    verify_universal_certification_trust_federation.set_defaults(
        func=run_verify_universal_certification_trust_federation
    )

    universal_foundation_provider_adoption_pack = subparsers.add_parser(
        "universal-foundation-provider-adoption-pack",
        help="Create an L162 universal foundation provider adoption pack binding L161 trust federation, provider-family coverage, standard exports, runtime gates, and negative fixtures into one provider-neutral RDLLM implementation package.",
    )
    universal_foundation_provider_adoption_pack.add_argument(
        "--pack-input", required=True
    )
    universal_foundation_provider_adoption_pack.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_foundation_provider_adoption_pack.add_argument("--signing-secret")
    universal_foundation_provider_adoption_pack.add_argument("--output")
    universal_foundation_provider_adoption_pack.set_defaults(
        func=run_universal_foundation_provider_adoption_pack
    )

    verify_universal_foundation_provider_adoption_pack = subparsers.add_parser(
        "verify-universal-foundation-provider-adoption-pack",
        help="Verify an L162 universal foundation provider adoption pack against replay inputs.",
    )
    verify_universal_foundation_provider_adoption_pack.add_argument(
        "--pack-input", required=True
    )
    verify_universal_foundation_provider_adoption_pack.add_argument(
        "--pack", required=True
    )
    verify_universal_foundation_provider_adoption_pack.add_argument(
        "--signing-secret"
    )
    verify_universal_foundation_provider_adoption_pack.set_defaults(
        func=run_verify_universal_foundation_provider_adoption_pack
    )

    universal_industry_adoption_root = subparsers.add_parser(
        "universal-industry-adoption-root",
        help="Create an L163 universal industry adoption root binding the L162 adoption pack, proof graph, public endpoints, role obligations, and negative root fixtures into one acyclic provider-neutral trust root.",
    )
    universal_industry_adoption_root.add_argument("--root-input", required=True)
    universal_industry_adoption_root.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_industry_adoption_root.add_argument("--signing-secret")
    universal_industry_adoption_root.add_argument("--output")
    universal_industry_adoption_root.set_defaults(
        func=run_universal_industry_adoption_root
    )

    verify_universal_industry_adoption_root = subparsers.add_parser(
        "verify-universal-industry-adoption-root",
        help="Verify an L163 universal industry adoption root against replay inputs.",
    )
    verify_universal_industry_adoption_root.add_argument(
        "--root-input", required=True
    )
    verify_universal_industry_adoption_root.add_argument("--root", required=True)
    verify_universal_industry_adoption_root.add_argument("--signing-secret")
    verify_universal_industry_adoption_root.set_defaults(
        func=run_verify_universal_industry_adoption_root
    )

    universal_reference_implementation_distribution = subparsers.add_parser(
        "universal-reference-implementation-distribution",
        help="Create an L164 signed reproducible reference implementation distribution binding the L163 industry root to installable SDK, gateway, MCP, telemetry, content-credential, settlement, verifier, SBOM, and provenance packages.",
    )
    universal_reference_implementation_distribution.add_argument(
        "--distribution-input", required=True
    )
    universal_reference_implementation_distribution.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_reference_implementation_distribution.add_argument(
        "--signing-secret"
    )
    universal_reference_implementation_distribution.add_argument("--output")
    universal_reference_implementation_distribution.set_defaults(
        func=run_universal_reference_implementation_distribution
    )

    verify_universal_reference_implementation_distribution = (
        subparsers.add_parser(
            "verify-universal-reference-implementation-distribution",
            help="Verify an L164 universal reference implementation distribution against replay inputs.",
        )
    )
    verify_universal_reference_implementation_distribution.add_argument(
        "--distribution-input", required=True
    )
    verify_universal_reference_implementation_distribution.add_argument(
        "--distribution", required=True
    )
    verify_universal_reference_implementation_distribution.add_argument(
        "--signing-secret"
    )
    verify_universal_reference_implementation_distribution.set_defaults(
        func=run_verify_universal_reference_implementation_distribution
    )

    universal_live_attribution_proof = subparsers.add_parser(
        "universal-live-attribution-proof",
        help="Create an L165 live attribution proof binding visible source footers to identity, claim support, evidence utility, factual confidence, knowledge-source classification, and settlement participation.",
    )
    universal_live_attribution_proof.add_argument("--proof-input", required=True)
    universal_live_attribution_proof.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_live_attribution_proof.add_argument("--signing-secret")
    universal_live_attribution_proof.add_argument("--output")
    universal_live_attribution_proof.set_defaults(
        func=run_universal_live_attribution_proof
    )

    verify_universal_live_attribution_proof = subparsers.add_parser(
        "verify-universal-live-attribution-proof",
        help="Verify an L165 universal live attribution proof against replay inputs.",
    )
    verify_universal_live_attribution_proof.add_argument(
        "--proof-input", required=True
    )
    verify_universal_live_attribution_proof.add_argument("--proof", required=True)
    verify_universal_live_attribution_proof.add_argument("--signing-secret")
    verify_universal_live_attribution_proof.set_defaults(
        func=run_verify_universal_live_attribution_proof
    )

    universal_foundation_model_release_passport = subparsers.add_parser(
        "universal-foundation-model-release-passport",
        help="Create an L166 model-release passport binding a named foundation-model version to training transparency, provider routes, live attribution, revocation, and settlement.",
    )
    universal_foundation_model_release_passport.add_argument(
        "--passport-input", required=True
    )
    universal_foundation_model_release_passport.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_foundation_model_release_passport.add_argument("--signing-secret")
    universal_foundation_model_release_passport.add_argument("--output")
    universal_foundation_model_release_passport.set_defaults(
        func=run_universal_foundation_model_release_passport
    )

    verify_universal_foundation_model_release_passport = subparsers.add_parser(
        "verify-universal-foundation-model-release-passport",
        help="Verify an L166 model-release passport against replay inputs.",
    )
    verify_universal_foundation_model_release_passport.add_argument(
        "--passport-input", required=True
    )
    verify_universal_foundation_model_release_passport.add_argument(
        "--passport", required=True
    )
    verify_universal_foundation_model_release_passport.add_argument(
        "--signing-secret"
    )
    verify_universal_foundation_model_release_passport.set_defaults(
        func=run_verify_universal_foundation_model_release_passport
    )

    universal_composite_rdllm_contract = subparsers.add_parser(
        "universal-composite-rdllm-contract",
        help="Create an L167 single composite RDLLM contract binding model claims, invocation, response release, footer reliance, procurement reliance, and settlement to one verifier decision.",
    )
    universal_composite_rdllm_contract.add_argument(
        "--contract-input", required=True
    )
    universal_composite_rdllm_contract.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_composite_rdllm_contract.add_argument("--signing-secret")
    universal_composite_rdllm_contract.add_argument("--output")
    universal_composite_rdllm_contract.set_defaults(
        func=run_universal_composite_rdllm_contract
    )

    verify_universal_composite_rdllm_contract = subparsers.add_parser(
        "verify-universal-composite-rdllm-contract",
        help="Verify an L167 universal composite RDLLM contract against replay inputs.",
    )
    verify_universal_composite_rdllm_contract.add_argument(
        "--contract-input", required=True
    )
    verify_universal_composite_rdllm_contract.add_argument(
        "--contract", required=True
    )
    verify_universal_composite_rdllm_contract.add_argument("--signing-secret")
    verify_universal_composite_rdllm_contract.set_defaults(
        func=run_verify_universal_composite_rdllm_contract
    )

    universal_foundation_provider_binding_matrix = subparsers.add_parser(
        "universal-foundation-provider-binding-matrix",
        help="Create an L168 provider binding matrix proving named foundation provider families map their native routes into the L167 composite RDLLM contract.",
    )
    universal_foundation_provider_binding_matrix.add_argument(
        "--matrix-input", required=True
    )
    universal_foundation_provider_binding_matrix.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_foundation_provider_binding_matrix.add_argument("--signing-secret")
    universal_foundation_provider_binding_matrix.add_argument("--output")
    universal_foundation_provider_binding_matrix.set_defaults(
        func=run_universal_foundation_provider_binding_matrix
    )

    verify_universal_foundation_provider_binding_matrix = subparsers.add_parser(
        "verify-universal-foundation-provider-binding-matrix",
        help="Verify an L168 foundation provider binding matrix against replay inputs.",
    )
    verify_universal_foundation_provider_binding_matrix.add_argument(
        "--matrix-input", required=True
    )
    verify_universal_foundation_provider_binding_matrix.add_argument(
        "--matrix", required=True
    )
    verify_universal_foundation_provider_binding_matrix.add_argument(
        "--signing-secret"
    )
    verify_universal_foundation_provider_binding_matrix.set_defaults(
        func=run_verify_universal_foundation_provider_binding_matrix
    )

    universal_provider_conformance_runner_receipt = subparsers.add_parser(
        "universal-provider-conformance-runner-receipt",
        help="Create an L169 provider conformance runner receipt proving official fixtures were replayed against each bound foundation provider route.",
    )
    universal_provider_conformance_runner_receipt.add_argument(
        "--receipt-input", required=True
    )
    universal_provider_conformance_runner_receipt.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_provider_conformance_runner_receipt.add_argument("--signing-secret")
    universal_provider_conformance_runner_receipt.add_argument("--output")
    universal_provider_conformance_runner_receipt.set_defaults(
        func=run_universal_provider_conformance_runner_receipt
    )

    verify_universal_provider_conformance_runner_receipt = subparsers.add_parser(
        "verify-universal-provider-conformance-runner-receipt",
        help="Verify an L169 provider conformance runner receipt against replay inputs.",
    )
    verify_universal_provider_conformance_runner_receipt.add_argument(
        "--receipt-input", required=True
    )
    verify_universal_provider_conformance_runner_receipt.add_argument(
        "--receipt", required=True
    )
    verify_universal_provider_conformance_runner_receipt.add_argument(
        "--signing-secret"
    )
    verify_universal_provider_conformance_runner_receipt.set_defaults(
        func=run_verify_universal_provider_conformance_runner_receipt
    )

    universal_production_invocation_admission = subparsers.add_parser(
        "universal-production-invocation-admission",
        help="Create an L170 production admission artifact proving live provider invocations are admitted against L169 conformance, drift, telemetry, source-footer, revocation, and settlement gates.",
    )
    universal_production_invocation_admission.add_argument(
        "--admission-input", required=True
    )
    universal_production_invocation_admission.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_production_invocation_admission.add_argument("--signing-secret")
    universal_production_invocation_admission.add_argument("--output")
    universal_production_invocation_admission.set_defaults(
        func=run_universal_production_invocation_admission
    )

    verify_universal_production_invocation_admission = subparsers.add_parser(
        "verify-universal-production-invocation-admission",
        help="Verify an L170 production invocation admission artifact against replay inputs.",
    )
    verify_universal_production_invocation_admission.add_argument(
        "--admission-input", required=True
    )
    verify_universal_production_invocation_admission.add_argument(
        "--admission", required=True
    )
    verify_universal_production_invocation_admission.add_argument("--signing-secret")
    verify_universal_production_invocation_admission.set_defaults(
        func=run_verify_universal_production_invocation_admission
    )

    universal_source_grounded_response_receipt = subparsers.add_parser(
        "universal-source-grounded-response-receipt",
        help="Create an L171 receipt proving final responses bind L170 admission to grounded source footers, claim support, citation checks, copy/export preservation, and settlement release.",
    )
    universal_source_grounded_response_receipt.add_argument(
        "--receipt-input", required=True
    )
    universal_source_grounded_response_receipt.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_source_grounded_response_receipt.add_argument("--signing-secret")
    universal_source_grounded_response_receipt.add_argument("--output")
    universal_source_grounded_response_receipt.set_defaults(
        func=run_universal_source_grounded_response_receipt
    )

    verify_universal_source_grounded_response_receipt = subparsers.add_parser(
        "verify-universal-source-grounded-response-receipt",
        help="Verify an L171 source-grounded response receipt against replay inputs.",
    )
    verify_universal_source_grounded_response_receipt.add_argument(
        "--receipt-input", required=True
    )
    verify_universal_source_grounded_response_receipt.add_argument(
        "--receipt", required=True
    )
    verify_universal_source_grounded_response_receipt.add_argument("--signing-secret")
    verify_universal_source_grounded_response_receipt.set_defaults(
        func=run_verify_universal_source_grounded_response_receipt
    )

    universal_distribution_reliance_passport = subparsers.add_parser(
        "universal-distribution-reliance-passport",
        help="Create an L172 passport proving source footers, status resolvers, content credentials, reuse meters, and settlement obligations survive copied, exported, relayed, and downstream AI reuse.",
    )
    universal_distribution_reliance_passport.add_argument(
        "--passport-input", required=True
    )
    universal_distribution_reliance_passport.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_distribution_reliance_passport.add_argument("--signing-secret")
    universal_distribution_reliance_passport.add_argument("--output")
    universal_distribution_reliance_passport.set_defaults(
        func=run_universal_distribution_reliance_passport
    )

    verify_universal_distribution_reliance_passport = subparsers.add_parser(
        "verify-universal-distribution-reliance-passport",
        help="Verify an L172 distribution reliance passport against replay inputs.",
    )
    verify_universal_distribution_reliance_passport.add_argument(
        "--passport-input", required=True
    )
    verify_universal_distribution_reliance_passport.add_argument(
        "--passport", required=True
    )
    verify_universal_distribution_reliance_passport.add_argument("--signing-secret")
    verify_universal_distribution_reliance_passport.set_defaults(
        func=run_verify_universal_distribution_reliance_passport
    )

    universal_adversarial_provenance_quorum = subparsers.add_parser(
        "universal-adversarial-provenance-quorum",
        help="Create an L173 quorum proving distributed attribution survives spoofing, stripping, replay, split-view, proxy rewrite, and downstream poisoning attacks before reliance or settlement.",
    )
    universal_adversarial_provenance_quorum.add_argument(
        "--quorum-input", required=True
    )
    universal_adversarial_provenance_quorum.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_adversarial_provenance_quorum.add_argument("--signing-secret")
    universal_adversarial_provenance_quorum.add_argument("--output")
    universal_adversarial_provenance_quorum.set_defaults(
        func=run_universal_adversarial_provenance_quorum
    )

    verify_universal_adversarial_provenance_quorum = subparsers.add_parser(
        "verify-universal-adversarial-provenance-quorum",
        help="Verify an L173 adversarial provenance quorum against replay inputs.",
    )
    verify_universal_adversarial_provenance_quorum.add_argument(
        "--quorum-input", required=True
    )
    verify_universal_adversarial_provenance_quorum.add_argument(
        "--quorum", required=True
    )
    verify_universal_adversarial_provenance_quorum.add_argument("--signing-secret")
    verify_universal_adversarial_provenance_quorum.set_defaults(
        func=run_verify_universal_adversarial_provenance_quorum
    )

    universal_procurement_regulatory_reliance_contract = subparsers.add_parser(
        "universal-procurement-regulatory-reliance-contract",
        help="Create an L174 procurement and regulatory reliance contract that binds provider claims, marketplace listing, enterprise buying, regulator export, source-footers, and creator settlement to the L173 adversarial provenance quorum.",
    )
    universal_procurement_regulatory_reliance_contract.add_argument(
        "--contract-input", required=True
    )
    universal_procurement_regulatory_reliance_contract.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_procurement_regulatory_reliance_contract.add_argument(
        "--signing-secret"
    )
    universal_procurement_regulatory_reliance_contract.add_argument("--output")
    universal_procurement_regulatory_reliance_contract.set_defaults(
        func=run_universal_procurement_regulatory_reliance_contract
    )

    verify_universal_procurement_regulatory_reliance_contract = (
        subparsers.add_parser(
            "verify-universal-procurement-regulatory-reliance-contract",
            help="Verify an L174 procurement and regulatory reliance contract against replay inputs.",
        )
    )
    verify_universal_procurement_regulatory_reliance_contract.add_argument(
        "--contract-input", required=True
    )
    verify_universal_procurement_regulatory_reliance_contract.add_argument(
        "--contract", required=True
    )
    verify_universal_procurement_regulatory_reliance_contract.add_argument(
        "--signing-secret"
    )
    verify_universal_procurement_regulatory_reliance_contract.set_defaults(
        func=run_verify_universal_procurement_regulatory_reliance_contract
    )

    universal_provider_onboarding_migration_covenant = subparsers.add_parser(
        "universal-provider-onboarding-migration-covenant",
        help="Create an L175 provider onboarding and migration covenant that binds native API mappings, SDKs, gateways, customer migration, rollout gates, and rollback controls to the L174 procurement reliance contract.",
    )
    universal_provider_onboarding_migration_covenant.add_argument(
        "--covenant-input", required=True
    )
    universal_provider_onboarding_migration_covenant.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_provider_onboarding_migration_covenant.add_argument(
        "--signing-secret"
    )
    universal_provider_onboarding_migration_covenant.add_argument("--output")
    universal_provider_onboarding_migration_covenant.set_defaults(
        func=run_universal_provider_onboarding_migration_covenant
    )

    verify_universal_provider_onboarding_migration_covenant = (
        subparsers.add_parser(
            "verify-universal-provider-onboarding-migration-covenant",
            help="Verify an L175 provider onboarding and migration covenant against replay inputs.",
        )
    )
    verify_universal_provider_onboarding_migration_covenant.add_argument(
        "--covenant-input", required=True
    )
    verify_universal_provider_onboarding_migration_covenant.add_argument(
        "--covenant", required=True
    )
    verify_universal_provider_onboarding_migration_covenant.add_argument(
        "--signing-secret"
    )
    verify_universal_provider_onboarding_migration_covenant.set_defaults(
        func=run_verify_universal_provider_onboarding_migration_covenant
    )

    universal_model_provider_registry = subparsers.add_parser(
        "universal-model-provider-registry",
        help="Create an L176 model/provider registry that binds every declared model route, catalog source, provider namespace, adapter manifest, lifecycle event, and negative fixture to the L175 onboarding covenant.",
    )
    universal_model_provider_registry.add_argument(
        "--registry-input", required=True
    )
    universal_model_provider_registry.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_model_provider_registry.add_argument("--signing-secret")
    universal_model_provider_registry.add_argument("--output")
    universal_model_provider_registry.set_defaults(
        func=run_universal_model_provider_registry
    )

    verify_universal_model_provider_registry = subparsers.add_parser(
        "verify-universal-model-provider-registry",
        help="Verify an L176 model/provider registry against replay inputs.",
    )
    verify_universal_model_provider_registry.add_argument(
        "--registry-input", required=True
    )
    verify_universal_model_provider_registry.add_argument(
        "--registry", required=True
    )
    verify_universal_model_provider_registry.add_argument("--signing-secret")
    verify_universal_model_provider_registry.set_defaults(
        func=run_verify_universal_model_provider_registry
    )

    universal_source_footer_enforcement_contract = subparsers.add_parser(
        "universal-source-footer-enforcement-contract",
        help="Create an L177 source-footer enforcement contract that binds all L176 model routes to L171 source-grounded response receipts before answer release.",
    )
    universal_source_footer_enforcement_contract.add_argument(
        "--contract-input", required=True
    )
    universal_source_footer_enforcement_contract.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_source_footer_enforcement_contract.add_argument("--signing-secret")
    universal_source_footer_enforcement_contract.add_argument("--output")
    universal_source_footer_enforcement_contract.set_defaults(
        func=run_universal_source_footer_enforcement_contract
    )

    verify_universal_source_footer_enforcement_contract = subparsers.add_parser(
        "verify-universal-source-footer-enforcement-contract",
        help="Verify an L177 source-footer enforcement contract against replay inputs.",
    )
    verify_universal_source_footer_enforcement_contract.add_argument(
        "--contract-input", required=True
    )
    verify_universal_source_footer_enforcement_contract.add_argument(
        "--contract", required=True
    )
    verify_universal_source_footer_enforcement_contract.add_argument("--signing-secret")
    verify_universal_source_footer_enforcement_contract.set_defaults(
        func=run_verify_universal_source_footer_enforcement_contract
    )

    universal_provider_catalog_coverage_contract = subparsers.add_parser(
        "universal-provider-catalog-coverage-contract",
        help="Create an L178 provider catalog coverage contract that proves every discovered provider catalog model is either admitted into L176 with L177 source-footer enforcement or explicitly blocked.",
    )
    universal_provider_catalog_coverage_contract.add_argument(
        "--contract-input", required=True
    )
    universal_provider_catalog_coverage_contract.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_provider_catalog_coverage_contract.add_argument("--signing-secret")
    universal_provider_catalog_coverage_contract.add_argument("--output")
    universal_provider_catalog_coverage_contract.set_defaults(
        func=run_universal_provider_catalog_coverage_contract
    )

    verify_universal_provider_catalog_coverage_contract = subparsers.add_parser(
        "verify-universal-provider-catalog-coverage-contract",
        help="Verify an L178 provider catalog coverage contract against replay inputs.",
    )
    verify_universal_provider_catalog_coverage_contract.add_argument(
        "--contract-input", required=True
    )
    verify_universal_provider_catalog_coverage_contract.add_argument(
        "--contract", required=True
    )
    verify_universal_provider_catalog_coverage_contract.add_argument(
        "--signing-secret"
    )
    verify_universal_provider_catalog_coverage_contract.set_defaults(
        func=run_verify_universal_provider_catalog_coverage_contract
    )

    universal_runtime_route_binding_contract = subparsers.add_parser(
        "universal-runtime-route-binding-contract",
        help="Create an L179 runtime route binding contract that proves actual runtime model calls, aliases, fallbacks, streams, callbacks, telemetry, footers, and settlement meters bind to L178 catalog-covered routes.",
    )
    universal_runtime_route_binding_contract.add_argument(
        "--contract-input", required=True
    )
    universal_runtime_route_binding_contract.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_runtime_route_binding_contract.add_argument("--signing-secret")
    universal_runtime_route_binding_contract.add_argument("--output")
    universal_runtime_route_binding_contract.set_defaults(
        func=run_universal_runtime_route_binding_contract
    )

    verify_universal_runtime_route_binding_contract = subparsers.add_parser(
        "verify-universal-runtime-route-binding-contract",
        help="Verify an L179 runtime route binding contract against replay inputs.",
    )
    verify_universal_runtime_route_binding_contract.add_argument(
        "--contract-input", required=True
    )
    verify_universal_runtime_route_binding_contract.add_argument(
        "--contract", required=True
    )
    verify_universal_runtime_route_binding_contract.add_argument("--signing-secret")
    verify_universal_runtime_route_binding_contract.set_defaults(
        func=run_verify_universal_runtime_route_binding_contract
    )

    universal_verified_source_footer_contract = subparsers.add_parser(
        "universal-verified-source-footer-contract",
        help="Create an L180 verified source-footer reliance contract that binds live runtime routes to link health, relevance, factual support, visible footer rows, copy preservation, and settlement holds.",
    )
    universal_verified_source_footer_contract.add_argument(
        "--contract-input", required=True
    )
    universal_verified_source_footer_contract.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_verified_source_footer_contract.add_argument("--signing-secret")
    universal_verified_source_footer_contract.add_argument("--output")
    universal_verified_source_footer_contract.set_defaults(
        func=run_universal_verified_source_footer_contract
    )

    verify_universal_verified_source_footer_contract = subparsers.add_parser(
        "verify-universal-verified-source-footer-contract",
        help="Verify an L180 verified source-footer reliance contract against replay inputs.",
    )
    verify_universal_verified_source_footer_contract.add_argument(
        "--contract-input", required=True
    )
    verify_universal_verified_source_footer_contract.add_argument(
        "--contract", required=True
    )
    verify_universal_verified_source_footer_contract.add_argument("--signing-secret")
    verify_universal_verified_source_footer_contract.set_defaults(
        func=run_verify_universal_verified_source_footer_contract
    )

    universal_model_capability_coverage_contract = subparsers.add_parser(
        "universal-model-capability-coverage-contract",
        help="Create an L181 model capability coverage contract that binds every declared capability, modality pair, operation surface, catalog-covered route, source-footer behavior, and settlement meter.",
    )
    universal_model_capability_coverage_contract.add_argument(
        "--contract-input", required=True
    )
    universal_model_capability_coverage_contract.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_model_capability_coverage_contract.add_argument("--signing-secret")
    universal_model_capability_coverage_contract.add_argument("--output")
    universal_model_capability_coverage_contract.set_defaults(
        func=run_universal_model_capability_coverage_contract
    )

    verify_universal_model_capability_coverage_contract = subparsers.add_parser(
        "verify-universal-model-capability-coverage-contract",
        help="Verify an L181 model capability coverage contract against replay inputs.",
    )
    verify_universal_model_capability_coverage_contract.add_argument(
        "--contract-input", required=True
    )
    verify_universal_model_capability_coverage_contract.add_argument(
        "--contract", required=True
    )
    verify_universal_model_capability_coverage_contract.add_argument(
        "--signing-secret"
    )
    verify_universal_model_capability_coverage_contract.set_defaults(
        func=run_verify_universal_model_capability_coverage_contract
    )

    universal_live_capability_discovery_contract = subparsers.add_parser(
        "universal-live-capability-discovery-contract",
        help="Create an L182 live capability discovery contract that binds provider capability declarations to fresh official or attested sources, endpoint compatibility, lifecycle state, and L181 coverage.",
    )
    universal_live_capability_discovery_contract.add_argument(
        "--contract-input", required=True
    )
    universal_live_capability_discovery_contract.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_live_capability_discovery_contract.add_argument("--signing-secret")
    universal_live_capability_discovery_contract.add_argument("--output")
    universal_live_capability_discovery_contract.set_defaults(
        func=run_universal_live_capability_discovery_contract
    )

    verify_universal_live_capability_discovery_contract = subparsers.add_parser(
        "verify-universal-live-capability-discovery-contract",
        help="Verify an L182 live capability discovery contract against replay inputs.",
    )
    verify_universal_live_capability_discovery_contract.add_argument(
        "--contract-input", required=True
    )
    verify_universal_live_capability_discovery_contract.add_argument(
        "--contract", required=True
    )
    verify_universal_live_capability_discovery_contract.add_argument(
        "--signing-secret"
    )
    verify_universal_live_capability_discovery_contract.set_defaults(
        func=run_verify_universal_live_capability_discovery_contract
    )

    universal_native_source_annotation_contract = subparsers.add_parser(
        "universal-native-source-annotation-contract",
        help="Create an L183 native source annotation contract that normalizes provider-native citation and grounding metadata into RDLLM footer rows.",
    )
    universal_native_source_annotation_contract.add_argument(
        "--contract-input", required=True
    )
    universal_native_source_annotation_contract.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_native_source_annotation_contract.add_argument("--signing-secret")
    universal_native_source_annotation_contract.add_argument("--output")
    universal_native_source_annotation_contract.set_defaults(
        func=run_universal_native_source_annotation_contract
    )

    verify_universal_native_source_annotation_contract = subparsers.add_parser(
        "verify-universal-native-source-annotation-contract",
        help="Verify an L183 native source annotation contract against replay inputs.",
    )
    verify_universal_native_source_annotation_contract.add_argument(
        "--contract-input", required=True
    )
    verify_universal_native_source_annotation_contract.add_argument(
        "--contract", required=True
    )
    verify_universal_native_source_annotation_contract.add_argument(
        "--signing-secret"
    )
    verify_universal_native_source_annotation_contract.set_defaults(
        func=run_verify_universal_native_source_annotation_contract
    )

    universal_claim_evidence_footer_verification_contract = subparsers.add_parser(
        "universal-claim-evidence-footer-verification-contract",
        help="Create an L184 claim-evidence footer contract that verifies cited sources support displayed answer claims.",
    )
    universal_claim_evidence_footer_verification_contract.add_argument(
        "--contract-input", required=True
    )
    universal_claim_evidence_footer_verification_contract.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_claim_evidence_footer_verification_contract.add_argument(
        "--signing-secret"
    )
    universal_claim_evidence_footer_verification_contract.add_argument("--output")
    universal_claim_evidence_footer_verification_contract.set_defaults(
        func=run_universal_claim_evidence_footer_verification_contract
    )

    verify_universal_claim_evidence_footer_verification_contract = (
        subparsers.add_parser(
            "verify-universal-claim-evidence-footer-verification-contract",
            help="Verify an L184 claim-evidence footer contract against replay inputs.",
        )
    )
    verify_universal_claim_evidence_footer_verification_contract.add_argument(
        "--contract-input", required=True
    )
    verify_universal_claim_evidence_footer_verification_contract.add_argument(
        "--contract", required=True
    )
    verify_universal_claim_evidence_footer_verification_contract.add_argument(
        "--signing-secret"
    )
    verify_universal_claim_evidence_footer_verification_contract.set_defaults(
        func=run_verify_universal_claim_evidence_footer_verification_contract
    )

    universal_provider_meter_normalization_contract = subparsers.add_parser(
        "universal-provider-meter-normalization-contract",
        help="Create an L185 provider meter normalization contract that binds native usage and billing meters to RDLLM settlement meters.",
    )
    universal_provider_meter_normalization_contract.add_argument(
        "--contract-input", required=True
    )
    universal_provider_meter_normalization_contract.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_provider_meter_normalization_contract.add_argument("--signing-secret")
    universal_provider_meter_normalization_contract.add_argument("--output")
    universal_provider_meter_normalization_contract.set_defaults(
        func=run_universal_provider_meter_normalization_contract
    )

    verify_universal_provider_meter_normalization_contract = subparsers.add_parser(
        "verify-universal-provider-meter-normalization-contract",
        help="Verify an L185 provider meter normalization contract against replay inputs.",
    )
    verify_universal_provider_meter_normalization_contract.add_argument(
        "--contract-input", required=True
    )
    verify_universal_provider_meter_normalization_contract.add_argument(
        "--contract", required=True
    )
    verify_universal_provider_meter_normalization_contract.add_argument(
        "--signing-secret"
    )
    verify_universal_provider_meter_normalization_contract.set_defaults(
        func=run_verify_universal_provider_meter_normalization_contract
    )

    universal_provider_response_state_normalization_contract = (
        subparsers.add_parser(
            "universal-provider-response-state-normalization-contract",
            help="Create an L186 provider response-state normalization contract that gates blocked, refused, truncated, tool-only, errored, or unknown native states before footer reliance or settlement.",
        )
    )
    universal_provider_response_state_normalization_contract.add_argument(
        "--contract-input", required=True
    )
    universal_provider_response_state_normalization_contract.add_argument(
        "--issuer", default="rdllm-local-demo"
    )
    universal_provider_response_state_normalization_contract.add_argument(
        "--signing-secret"
    )
    universal_provider_response_state_normalization_contract.add_argument("--output")
    universal_provider_response_state_normalization_contract.set_defaults(
        func=run_universal_provider_response_state_normalization_contract
    )

    verify_universal_provider_response_state_normalization_contract = (
        subparsers.add_parser(
            "verify-universal-provider-response-state-normalization-contract",
            help="Verify an L186 provider response-state normalization contract against replay inputs.",
        )
    )
    verify_universal_provider_response_state_normalization_contract.add_argument(
        "--contract-input", required=True
    )
    verify_universal_provider_response_state_normalization_contract.add_argument(
        "--contract", required=True
    )
    verify_universal_provider_response_state_normalization_contract.add_argument(
        "--signing-secret"
    )
    verify_universal_provider_response_state_normalization_contract.set_defaults(
        func=run_verify_universal_provider_response_state_normalization_contract
    )

    citation_identity = subparsers.add_parser(
        "citation-identity-report",
        help="Create a citation identity report that rejects fabricated or metadata-swapped citations.",
    )
    citation_identity.add_argument("--citation-input", required=True)
    citation_identity.add_argument("--citation-gross-revenue", default="1.00")
    citation_identity.add_argument("--citation-creator-pool-rate", default="0.55")
    citation_identity.add_argument("--accept-threshold", type=float, default=0.72)
    citation_identity.add_argument("--min-title-similarity", type=float, default=0.72)
    citation_identity.add_argument("--min-author-overlap", type=float, default=0.50)
    citation_identity.add_argument("--min-claim-support", type=float, default=0.55)
    citation_identity.add_argument("--issuer", default="rdllm-local-demo")
    citation_identity.add_argument("--signing-secret")
    citation_identity.add_argument("--output")
    citation_identity.set_defaults(func=run_citation_identity_report)

    verify_citation_identity = subparsers.add_parser(
        "verify-citation-identity-report",
        help="Verify a citation identity report against authority records.",
    )
    verify_citation_identity.add_argument("--citation-input", required=True)
    verify_citation_identity.add_argument("--report", required=True)
    verify_citation_identity.add_argument("--signing-secret")
    verify_citation_identity.set_defaults(
        func=run_verify_citation_identity_report
    )

    attribution_consensus = subparsers.add_parser(
        "attribution-consensus-report",
        help="Create a public consensus report across attribution, provenance, citation, authenticity, sufficiency, and counterevidence artifacts.",
    )
    attribution_consensus.add_argument("--source-confidence-report", required=True)
    attribution_consensus.add_argument("--evidence-sufficiency-report", required=True)
    attribution_consensus.add_argument("--counterevidence-report", required=True)
    attribution_consensus.add_argument("--source-authenticity-report", required=True)
    attribution_consensus.add_argument("--pinpoint-provenance-report", required=True)
    attribution_consensus.add_argument("--citation-identity-report", required=True)
    attribution_consensus.add_argument("--consensus-gross-revenue", default="1.00")
    attribution_consensus.add_argument("--consensus-creator-pool-rate", default="0.55")
    attribution_consensus.add_argument("--minimum-quorum", type=int, default=6)
    attribution_consensus.add_argument("--issuer", default="rdllm-local-demo")
    attribution_consensus.add_argument("--signing-secret")
    attribution_consensus.add_argument("--output")
    attribution_consensus.set_defaults(func=run_attribution_consensus_report)

    verify_attribution_consensus = subparsers.add_parser(
        "verify-attribution-consensus-report",
        help="Verify a public attribution consensus report from its bound public artifacts.",
    )
    verify_attribution_consensus.add_argument("--report", required=True)
    verify_attribution_consensus.add_argument("--source-confidence-report", required=True)
    verify_attribution_consensus.add_argument(
        "--evidence-sufficiency-report", required=True
    )
    verify_attribution_consensus.add_argument("--counterevidence-report", required=True)
    verify_attribution_consensus.add_argument(
        "--source-authenticity-report", required=True
    )
    verify_attribution_consensus.add_argument(
        "--pinpoint-provenance-report", required=True
    )
    verify_attribution_consensus.add_argument("--citation-identity-report", required=True)
    verify_attribution_consensus.add_argument("--signing-secret")
    verify_attribution_consensus.set_defaults(
        func=run_verify_attribution_consensus_report
    )

    verifier_quorum = subparsers.add_parser(
        "verifier-quorum-report",
        help="Create an independent verifier quorum report that gates direct settlement after attribution consensus.",
    )
    verifier_quorum.add_argument("--attribution-consensus-report", required=True)
    verifier_quorum.add_argument("--provider-card", required=True)
    verifier_quorum.add_argument("--certification-report", required=True)
    verifier_quorum.add_argument("--integration-profile", required=True)
    verifier_quorum.add_argument(
        "--verifier-secret",
        action="append",
        default=[],
        help="Repeatable verifier_id=secret HMAC material for reference signatures.",
    )
    verifier_quorum.add_argument("--minimum-quorum", type=int, default=3)
    verifier_quorum.add_argument(
        "--minimum-independent-organizations",
        type=int,
        default=2,
    )
    verifier_quorum.add_argument("--issuer", default="rdllm-local-demo")
    verifier_quorum.add_argument("--signing-secret")
    verifier_quorum.add_argument("--output")
    verifier_quorum.set_defaults(func=run_verifier_quorum_report)

    verify_verifier_quorum = subparsers.add_parser(
        "verify-verifier-quorum-report",
        help="Verify an independent verifier quorum report from its public artifacts and verifier signatures.",
    )
    verify_verifier_quorum.add_argument("--report", required=True)
    verify_verifier_quorum.add_argument("--attribution-consensus-report", required=True)
    verify_verifier_quorum.add_argument("--provider-card", required=True)
    verify_verifier_quorum.add_argument("--certification-report", required=True)
    verify_verifier_quorum.add_argument("--integration-profile", required=True)
    verify_verifier_quorum.add_argument(
        "--verifier-secret",
        action="append",
        default=[],
        help="Repeatable verifier_id=secret HMAC material for reference signatures.",
    )
    verify_verifier_quorum.add_argument("--signing-secret")
    verify_verifier_quorum.set_defaults(func=run_verify_verifier_quorum_report)

    verifier_accountability = subparsers.add_parser(
        "verifier-accountability-report",
        help="Create a bonded verifier accountability report that gates verifier-approved settlement on registry identity, bond coverage, conflicts, and challenges.",
    )
    verifier_accountability.add_argument("--verifier-quorum-report", required=True)
    verifier_accountability.add_argument("--trust-registry", required=True)
    verifier_accountability.add_argument("--provider-card", required=True)
    verifier_accountability.add_argument("--certification-report", required=True)
    verifier_accountability.add_argument(
        "--bond",
        action="append",
        default=[],
        help="Repeatable verifier_id=amount[:currency[:escrow_hash[:conflict_status]]] bond declaration.",
    )
    verifier_accountability.add_argument(
        "--challenge",
        action="append",
        default=[],
        help="Repeatable challenge_id=verifier_id:status:reason_code:evidence_hash declaration.",
    )
    verifier_accountability.add_argument("--minimum-bond-amount", default="1000.00")
    verifier_accountability.add_argument("--issuer", default="rdllm-local-demo")
    verifier_accountability.add_argument("--signing-secret")
    verifier_accountability.add_argument("--output")
    verifier_accountability.set_defaults(func=run_verifier_accountability_report)

    verify_verifier_accountability = subparsers.add_parser(
        "verify-verifier-accountability-report",
        help="Verify a bonded verifier accountability report from public artifacts.",
    )
    verify_verifier_accountability.add_argument("--report", required=True)
    verify_verifier_accountability.add_argument("--verifier-quorum-report", required=True)
    verify_verifier_accountability.add_argument("--trust-registry", required=True)
    verify_verifier_accountability.add_argument("--provider-card", required=True)
    verify_verifier_accountability.add_argument("--certification-report", required=True)
    verify_verifier_accountability.add_argument("--signing-secret")
    verify_verifier_accountability.set_defaults(
        func=run_verify_verifier_accountability_report
    )

    receipt_consistency = subparsers.add_parser(
        "receipt-transparency-consistency-report",
        help="Create a receipt transparency consistency report that detects append-only violations and split-view usage logs before settlement.",
    )
    receipt_consistency.add_argument(
        "--transparency-log",
        action="append",
        default=[],
        required=True,
        help="Repeatable name=path or path to a transparency log snapshot.",
    )
    receipt_consistency.add_argument(
        "--receipt",
        action="append",
        default=[],
        required=True,
        help="Repeatable attribution receipt path that must be included in the latest log snapshot.",
    )
    receipt_consistency.add_argument("--verifier-accountability-report", required=True)
    receipt_consistency.add_argument("--provider-card", required=True)
    receipt_consistency.add_argument("--certification-report", required=True)
    receipt_consistency.add_argument("--issuer", default="rdllm-local-demo")
    receipt_consistency.add_argument("--signing-secret")
    receipt_consistency.add_argument("--output")
    receipt_consistency.set_defaults(
        func=run_receipt_transparency_consistency_report
    )

    verify_receipt_consistency = subparsers.add_parser(
        "verify-receipt-transparency-consistency-report",
        help="Verify a receipt transparency consistency report from public logs, required receipts, and settlement artifacts.",
    )
    verify_receipt_consistency.add_argument("--report", required=True)
    verify_receipt_consistency.add_argument(
        "--transparency-log",
        action="append",
        default=[],
        required=True,
        help="Repeatable name=path or path to a transparency log snapshot.",
    )
    verify_receipt_consistency.add_argument(
        "--receipt",
        action="append",
        default=[],
        required=True,
        help="Repeatable attribution receipt path that must be included in the latest log snapshot.",
    )
    verify_receipt_consistency.add_argument(
        "--verifier-accountability-report", required=True
    )
    verify_receipt_consistency.add_argument("--provider-card", required=True)
    verify_receipt_consistency.add_argument("--certification-report", required=True)
    verify_receipt_consistency.add_argument("--signing-secret")
    verify_receipt_consistency.set_defaults(
        func=run_verify_receipt_transparency_consistency_report
    )

    watchtower_settlement = subparsers.add_parser(
        "watchtower-challenge-settlement-report",
        help="Create an independent watchtower challenge settlement report over receipt-transparent settlement.",
    )
    watchtower_settlement.add_argument(
        "--receipt-transparency-consistency-report", required=True
    )
    watchtower_settlement.add_argument("--verifier-accountability-report", required=True)
    watchtower_settlement.add_argument("--trust-registry", required=True)
    watchtower_settlement.add_argument("--provider-card", required=True)
    watchtower_settlement.add_argument("--certification-report", required=True)
    watchtower_settlement.add_argument(
        "--watchtower-secret",
        action="append",
        default=[],
        help="Repeatable watchtower_id=secret HMAC material for reference signatures.",
    )
    watchtower_settlement.add_argument(
        "--challenge-row",
        action="append",
        default=[],
        help="Repeatable path to a JSON watchtower challenge row.",
    )
    watchtower_settlement.add_argument("--required-quorum", type=int)
    watchtower_settlement.add_argument("--issuer", default="rdllm-local-demo")
    watchtower_settlement.add_argument("--signing-secret")
    watchtower_settlement.add_argument("--output")
    watchtower_settlement.set_defaults(
        func=run_watchtower_challenge_settlement_report
    )

    verify_watchtower_settlement = subparsers.add_parser(
        "verify-watchtower-challenge-settlement-report",
        help="Verify a watchtower challenge settlement report from public artifacts and watchtower signatures.",
    )
    verify_watchtower_settlement.add_argument("--report", required=True)
    verify_watchtower_settlement.add_argument(
        "--receipt-transparency-consistency-report", required=True
    )
    verify_watchtower_settlement.add_argument(
        "--verifier-accountability-report", required=True
    )
    verify_watchtower_settlement.add_argument("--trust-registry", required=True)
    verify_watchtower_settlement.add_argument("--provider-card", required=True)
    verify_watchtower_settlement.add_argument("--certification-report", required=True)
    verify_watchtower_settlement.add_argument(
        "--watchtower-secret",
        action="append",
        default=[],
        help="Repeatable watchtower_id=secret HMAC material for reference signatures.",
    )
    verify_watchtower_settlement.add_argument(
        "--challenge-row",
        action="append",
        default=[],
        help="Repeatable path to a JSON watchtower challenge row.",
    )
    verify_watchtower_settlement.add_argument("--signing-secret")
    verify_watchtower_settlement.set_defaults(
        func=run_verify_watchtower_challenge_settlement_report
    )

    output_binding = subparsers.add_parser(
        "output-provenance-binding-report",
        help="Create a durable output provenance binding report for copied or exported RDLLM content.",
    )
    output_binding.add_argument("--proof-carrying-response", required=True)
    output_binding.add_argument("--serving-gateway-report", required=True)
    output_binding.add_argument("--attribution-capsule", required=True)
    output_binding.add_argument("--watchtower-challenge-settlement-report", required=True)
    output_binding.add_argument("--provider-card", required=True)
    output_binding.add_argument("--certification-report", required=True)
    output_binding.add_argument("--issuer", default="rdllm-local-demo")
    output_binding.add_argument("--signing-secret")
    output_binding.add_argument("--output")
    output_binding.set_defaults(func=run_output_provenance_binding_report)

    verify_output_binding = subparsers.add_parser(
        "verify-output-provenance-binding-report",
        help="Verify an output provenance binding report against copied-output proof artifacts.",
    )
    verify_output_binding.add_argument("--report", required=True)
    verify_output_binding.add_argument("--proof-carrying-response", required=True)
    verify_output_binding.add_argument("--serving-gateway-report", required=True)
    verify_output_binding.add_argument("--attribution-capsule", required=True)
    verify_output_binding.add_argument(
        "--watchtower-challenge-settlement-report", required=True
    )
    verify_output_binding.add_argument("--provider-card", required=True)
    verify_output_binding.add_argument("--certification-report", required=True)
    verify_output_binding.add_argument("--signing-secret")
    verify_output_binding.set_defaults(func=run_verify_output_provenance_binding_report)

    post_release = subparsers.add_parser(
        "post-release-discovery-report",
        help="Create a two-phase post-release discovery report for late output proof artifacts.",
    )
    post_release.add_argument("--discovery-manifest", required=True)
    post_release.add_argument("--output-provenance-binding-report", required=True)
    post_release.add_argument("--proof-dependency-graph", required=True)
    post_release.add_argument("--proof-carrying-response", required=True)
    post_release.add_argument("--serving-gateway-report", required=True)
    post_release.add_argument("--attribution-capsule", required=True)
    post_release.add_argument("--watchtower-challenge-settlement-report", required=True)
    post_release.add_argument("--integration-profile", required=True)
    post_release.add_argument("--provider-card", required=True)
    post_release.add_argument("--certification-report", required=True)
    post_release.add_argument("--issuer", default="rdllm-local-demo")
    post_release.add_argument("--signing-secret")
    post_release.add_argument("--output")
    post_release.set_defaults(func=run_post_release_discovery_report)

    verify_post_release = subparsers.add_parser(
        "verify-post-release-discovery-report",
        help="Verify a post-release discovery report against late-bound public proof artifacts.",
    )
    verify_post_release.add_argument("--report", required=True)
    verify_post_release.add_argument("--discovery-manifest", required=True)
    verify_post_release.add_argument(
        "--output-provenance-binding-report", required=True
    )
    verify_post_release.add_argument("--proof-dependency-graph", required=True)
    verify_post_release.add_argument("--proof-carrying-response", required=True)
    verify_post_release.add_argument("--serving-gateway-report", required=True)
    verify_post_release.add_argument("--attribution-capsule", required=True)
    verify_post_release.add_argument(
        "--watchtower-challenge-settlement-report", required=True
    )
    verify_post_release.add_argument("--integration-profile", required=True)
    verify_post_release.add_argument("--provider-card", required=True)
    verify_post_release.add_argument("--certification-report", required=True)
    verify_post_release.add_argument("--signing-secret")
    verify_post_release.set_defaults(func=run_verify_post_release_discovery_report)

    rights_remediation = subparsers.add_parser(
        "rights-remediation",
        help="Create a post-publication rights remediation report for changed consent or revocation.",
    )
    rights_remediation.add_argument("--previous-corpus", required=True)
    rights_remediation.add_argument("--updated-corpus", required=True)
    rights_remediation.add_argument("--ledger", required=True)
    rights_remediation.add_argument("--remediation-gross-revenue", default="1.00")
    rights_remediation.add_argument("--remediation-creator-pool-rate", default="0.55")
    rights_remediation.add_argument("--jurisdiction", default="GLOBAL")
    rights_remediation.add_argument("--top-k", type=int, default=3)
    rights_remediation.add_argument("--issuer", default="rdllm-local-demo")
    rights_remediation.add_argument("--signing-secret")
    rights_remediation.add_argument("--output")
    rights_remediation.set_defaults(func=run_rights_remediation)

    verify_rights_remediation = subparsers.add_parser(
        "verify-rights-remediation",
        help="Verify a rights remediation report against previous and updated corpora.",
    )
    verify_rights_remediation.add_argument("--previous-corpus", required=True)
    verify_rights_remediation.add_argument("--updated-corpus", required=True)
    verify_rights_remediation.add_argument("--ledger", required=True)
    verify_rights_remediation.add_argument("--report", required=True)
    verify_rights_remediation.add_argument("--remediation-creator-pool-rate", default="0.55")
    verify_rights_remediation.add_argument("--jurisdiction", default="GLOBAL")
    verify_rights_remediation.add_argument("--top-k", type=int, default=3)
    verify_rights_remediation.add_argument("--signing-secret")
    verify_rights_remediation.set_defaults(func=run_verify_rights_remediation)

    semantic_text = subparsers.add_parser(
        "semantic-text-attribution",
        help="Create a semantic/paraphrase text attribution report with public source footers.",
    )
    semantic_text.add_argument("--semantic-input", required=True)
    semantic_text.add_argument("--semantic-gross-revenue", default="1.00")
    semantic_text.add_argument("--semantic-creator-pool-rate", default="0.55")
    semantic_text.add_argument("--accept-threshold", type=float, default=0.24)
    semantic_text.add_argument("--min-margin", type=float, default=0.03)
    semantic_text.add_argument("--issuer", default="rdllm-local-demo")
    semantic_text.add_argument("--signing-secret")
    semantic_text.add_argument("--output")
    semantic_text.set_defaults(func=run_semantic_text_attribution)

    verify_semantic_text = subparsers.add_parser(
        "verify-semantic-text-attribution",
        help="Verify a semantic/paraphrase text attribution report by replaying private inputs.",
    )
    verify_semantic_text.add_argument("--semantic-input", required=True)
    verify_semantic_text.add_argument("--report", required=True)
    verify_semantic_text.add_argument("--signing-secret")
    verify_semantic_text.set_defaults(func=run_verify_semantic_text_attribution)

    code_attribution = subparsers.add_parser(
        "code-attribution-report",
        help="Create a license-aware attribution report for generated code snippets.",
    )
    code_attribution.add_argument("--code-input", required=True)
    code_attribution.add_argument("--code-gross-revenue", default="1.00")
    code_attribution.add_argument("--code-creator-pool-rate", default="0.55")
    code_attribution.add_argument("--accept-threshold", type=float, default=0.34)
    code_attribution.add_argument("--strong-copy-threshold", type=float, default=0.67)
    code_attribution.add_argument("--issuer", default="rdllm-local-demo")
    code_attribution.add_argument("--signing-secret")
    code_attribution.add_argument("--output")
    code_attribution.set_defaults(func=run_code_attribution_report)

    verify_code_attribution = subparsers.add_parser(
        "verify-code-attribution-report",
        help="Verify a generated-code attribution report by replaying private code inputs.",
    )
    verify_code_attribution.add_argument("--code-input", required=True)
    verify_code_attribution.add_argument("--report", required=True)
    verify_code_attribution.add_argument("--signing-secret")
    verify_code_attribution.set_defaults(func=run_verify_code_attribution_report)

    claim_verification = subparsers.add_parser(
        "claim-verification-report",
        help="Create a pre-settlement ownership claim verification report.",
    )
    claim_verification.add_argument("--claim-input", required=True)
    claim_verification.add_argument("--duplicate-threshold", type=float, default=0.92)
    claim_verification.add_argument(
        "--direct-settlement-threshold", type=float, default=0.75
    )
    claim_verification.add_argument("--review-threshold", type=float, default=0.40)
    claim_verification.add_argument("--issuer", default="rdllm-local-demo")
    claim_verification.add_argument("--signing-secret")
    claim_verification.add_argument("--output")
    claim_verification.set_defaults(func=run_claim_verification_report)

    verify_claim_verification = subparsers.add_parser(
        "verify-claim-verification-report",
        help="Verify a claim verification report against private corpus and attestations.",
    )
    verify_claim_verification.add_argument("--claim-input", required=True)
    verify_claim_verification.add_argument("--report", required=True)
    verify_claim_verification.add_argument("--signing-secret")
    verify_claim_verification.set_defaults(func=run_verify_claim_verification_report)

    response_envelope = subparsers.add_parser(
        "response-envelope",
        help="Create a portable API response envelope with embedded public proofs.",
    )
    response_envelope.add_argument("--ledger", required=True)
    response_envelope.add_argument("--event-id")
    response_envelope.add_argument("--answer-card", required=True)
    response_envelope.add_argument("--source-report", required=True)
    response_envelope.add_argument("--source-confidence-report")
    response_envelope.add_argument("--creator-license-contract")
    response_envelope.add_argument("--citation-footer-contract")
    response_envelope.add_argument("--source-availability-report")
    response_envelope.add_argument("--evidence-sufficiency-report")
    response_envelope.add_argument("--counterevidence-report")
    response_envelope.add_argument("--answer-claim-coverage-report")
    response_envelope.add_argument("--trace-exchange")
    response_envelope.add_argument("--generation-context-closure-report")
    response_envelope.add_argument("--source-boundary-report")
    response_envelope.add_argument("--source-authenticity-report")
    response_envelope.add_argument("--public-receipt")
    response_envelope.add_argument("--provider-card")
    response_envelope.add_argument("--certification-report")
    response_envelope.add_argument("--issuer", default="rdllm-local-demo")
    response_envelope.add_argument("--signing-secret")
    response_envelope.add_argument("--output")
    response_envelope.set_defaults(func=run_response_envelope)

    verify_response_envelope = subparsers.add_parser(
        "verify-response-envelope",
        help="Verify a response envelope using only its public embedded artifacts.",
    )
    verify_response_envelope.add_argument("--envelope", required=True)
    verify_response_envelope.add_argument("--signing-secret")
    verify_response_envelope.set_defaults(func=run_verify_response_envelope)

    integration_profile = subparsers.add_parser(
        "integration-profile",
        help="Create a provider integration profile for RDLLM-compatible APIs.",
    )
    integration_profile.add_argument("--provider-card", required=True)
    integration_profile.add_argument("--certification-report", required=True)
    integration_profile.add_argument("--response-envelope", required=True)
    integration_profile.add_argument("--assurance-bundle")
    integration_profile.add_argument("--certification-attestation")
    integration_profile.add_argument("--issuer", default="rdllm-local-demo")
    integration_profile.add_argument("--signing-secret")
    integration_profile.add_argument("--output")
    integration_profile.set_defaults(func=run_integration_profile)

    verify_integration_profile = subparsers.add_parser(
        "verify-integration-profile",
        help="Verify an RDLLM provider integration profile against public artifacts.",
    )
    verify_integration_profile.add_argument("--profile", required=True)
    verify_integration_profile.add_argument("--provider-card", required=True)
    verify_integration_profile.add_argument("--certification-report", required=True)
    verify_integration_profile.add_argument("--response-envelope", required=True)
    verify_integration_profile.add_argument("--assurance-bundle")
    verify_integration_profile.add_argument("--certification-attestation")
    verify_integration_profile.add_argument("--signing-secret")
    verify_integration_profile.set_defaults(func=run_verify_integration_profile)

    discovery_manifest = subparsers.add_parser(
        "discovery-manifest",
        help="Create a well-known RDLLM discovery manifest for provider artifacts.",
    )
    discovery_manifest.add_argument("--provider-card", required=True)
    discovery_manifest.add_argument("--certification-report", required=True)
    discovery_manifest.add_argument("--integration-profile", required=True)
    discovery_manifest.add_argument("--response-envelope", required=True)
    discovery_manifest.add_argument("--assurance-bundle", required=True)
    discovery_manifest.add_argument("--training-summary")
    discovery_manifest.add_argument("--provenance-evaluation-report")
    discovery_manifest.add_argument("--counterfactual-report")
    discovery_manifest.add_argument("--media-attribution-report")
    discovery_manifest.add_argument("--model-signal-report")
    discovery_manifest.add_argument("--pinpoint-provenance-report")
    discovery_manifest.add_argument("--citation-identity-report")
    discovery_manifest.add_argument("--attribution-consensus-report")
    discovery_manifest.add_argument("--verifier-quorum-report")
    discovery_manifest.add_argument("--verifier-accountability-report")
    discovery_manifest.add_argument("--receipt-transparency-consistency-report")
    discovery_manifest.add_argument("--watchtower-challenge-settlement-report")
    discovery_manifest.add_argument("--output-provenance-binding-report")
    discovery_manifest.add_argument("--rights-remediation-report")
    discovery_manifest.add_argument("--semantic-text-attribution-report")
    discovery_manifest.add_argument("--code-attribution-report")
    discovery_manifest.add_argument("--claim-verification-report")
    discovery_manifest.add_argument("--source-availability-report")
    discovery_manifest.add_argument("--evidence-sufficiency-report")
    discovery_manifest.add_argument("--counterevidence-report")
    discovery_manifest.add_argument("--answer-claim-coverage-report")
    discovery_manifest.add_argument("--generation-context-closure-report")
    discovery_manifest.add_argument("--source-boundary-report")
    discovery_manifest.add_argument("--source-authenticity-report")
    discovery_manifest.add_argument("--decision-provenance-report")
    discovery_manifest.add_argument("--calibrated-attribution-report")
    discovery_manifest.add_argument("--streaming-attribution-manifest")
    discovery_manifest.add_argument("--conversation-attribution-ledger")
    discovery_manifest.add_argument("--agent-tool-attribution-ledger")
    discovery_manifest.add_argument("--creator-license-contract")
    discovery_manifest.add_argument("--source-confidence-report")
    discovery_manifest.add_argument("--citation-footer-contract")
    discovery_manifest.add_argument("--private-audit-challenge")
    discovery_manifest.add_argument("--transitive-attribution-report")
    discovery_manifest.add_argument("--clearinghouse-report")
    discovery_manifest.add_argument("--remittance-report")
    discovery_manifest.add_argument("--payment-execution-report")
    discovery_manifest.add_argument("--payment-rail-attestation")
    discovery_manifest.add_argument("--creator-payout-receipt-report")
    discovery_manifest.add_argument("--rendered-attribution-audit")
    discovery_manifest.add_argument("--training-memory-provenance")
    discovery_manifest.add_argument("--post-training-signal-provenance")
    discovery_manifest.add_argument("--evidence-locked-generation")
    discovery_manifest.add_argument("--emission-evidence-enforcement")
    discovery_manifest.add_argument("--live-emission-witness")
    discovery_manifest.add_argument("--live-emission-transparency")
    discovery_manifest.add_argument("--attested-runtime")
    discovery_manifest.add_argument("--claim-source-attribution-report")
    discovery_manifest.add_argument("--evidence-utility-attribution-report")
    discovery_manifest.add_argument("--parametric-memory-attribution-report")
    discovery_manifest.add_argument("--style-influence-attribution-report")
    discovery_manifest.add_argument("--model-lineage-attribution-report")
    discovery_manifest.add_argument("--black-box-model-provenance-report")
    discovery_manifest.add_argument("--attribution-dispute-adjudication-report")
    discovery_manifest.add_argument("--post-adjudication-settlement-adjustment-report")
    discovery_manifest.add_argument("--residual-corpus-royalty-report")
    discovery_manifest.add_argument("--valuation-method-audit-report")
    discovery_manifest.add_argument("--evidence-region-binding-report")
    discovery_manifest.add_argument("--source-access-lease-report")
    discovery_manifest.add_argument("--content-protocol-ingestion-report")
    discovery_manifest.add_argument("--citation-reliance-receipt")
    discovery_manifest.add_argument("--license-transaction-receipt")
    discovery_manifest.add_argument("--grounded-source-footer")
    discovery_manifest.add_argument("--source-footer-delivery")
    discovery_manifest.add_argument("--deep-research-citation-audit")
    discovery_manifest.add_argument("--source-freshness-audit")
    discovery_manifest.add_argument("--royalty-abuse-audit")
    discovery_manifest.add_argument("--consent-revocation-propagation")
    discovery_manifest.add_argument("--evidence-force-calibration")
    discovery_manifest.add_argument("--warranted-source-footer")
    discovery_manifest.add_argument("--source-origin-lineage")
    discovery_manifest.add_argument("--evidence-preview-footer")
    discovery_manifest.add_argument("--evidence-locator-manifest")
    discovery_manifest.add_argument("--citation-url-health")
    discovery_manifest.add_argument("--foundation-api-profile")
    discovery_manifest.add_argument("--composite-foundation-adapter")
    discovery_manifest.add_argument("--foundation-provider-conformance")
    discovery_manifest.add_argument("--foundation-runtime-adapter")
    discovery_manifest.add_argument("--foundation-runtime-router")
    discovery_manifest.add_argument("--foundation-model-deployment-attestation")
    discovery_manifest.add_argument("--universal-composition-receipt")
    discovery_manifest.add_argument("--universal-composition-settlement")
    discovery_manifest.add_argument("--universal-foundation-model-contract")
    discovery_manifest.add_argument("--universal-invocation-guard")
    discovery_manifest.add_argument("--universal-invocation-coverage")
    discovery_manifest.add_argument("--universal-invocation-witness")
    discovery_manifest.add_argument("--universal-content-credential")
    discovery_manifest.add_argument("--universal-rdllm-passport")
    discovery_manifest.add_argument("--universal-adoption-standard")
    discovery_manifest.add_argument("--universal-interop-test-kit")
    discovery_manifest.add_argument("--universal-context-provenance-bridge")
    discovery_manifest.add_argument("--universal-citation-verification-contract")
    discovery_manifest.add_argument("--universal-grounded-reuse-contract")
    discovery_manifest.add_argument("--universal-training-serving-contract")
    discovery_manifest.add_argument("--universal-confidential-attribution-audit")
    discovery_manifest.add_argument("--universal-attribution-authority-control-plane")
    discovery_manifest.add_argument("--revenue-allocation-report")
    discovery_manifest.add_argument("--finance-ledger-attestation")
    discovery_manifest.add_argument("--proof-dependency-graph")
    discovery_manifest.add_argument("--publication-monitor")
    discovery_manifest.add_argument("--publication-witness")
    discovery_manifest.add_argument("--trust-registry")
    discovery_manifest.add_argument("--certification-attestation")
    discovery_manifest.add_argument("--issuer", default="rdllm-local-demo")
    discovery_manifest.add_argument("--signing-secret")
    discovery_manifest.add_argument("--output")
    discovery_manifest.set_defaults(func=run_discovery_manifest)

    verify_discovery_manifest = subparsers.add_parser(
        "verify-discovery-manifest",
        help="Verify an RDLLM discovery manifest against provider artifacts.",
    )
    verify_discovery_manifest.add_argument("--manifest", required=True)
    verify_discovery_manifest.add_argument("--provider-card", required=True)
    verify_discovery_manifest.add_argument("--certification-report", required=True)
    verify_discovery_manifest.add_argument("--integration-profile", required=True)
    verify_discovery_manifest.add_argument("--response-envelope", required=True)
    verify_discovery_manifest.add_argument("--assurance-bundle", required=True)
    verify_discovery_manifest.add_argument("--training-summary")
    verify_discovery_manifest.add_argument("--provenance-evaluation-report")
    verify_discovery_manifest.add_argument("--counterfactual-report")
    verify_discovery_manifest.add_argument("--media-attribution-report")
    verify_discovery_manifest.add_argument("--model-signal-report")
    verify_discovery_manifest.add_argument("--pinpoint-provenance-report")
    verify_discovery_manifest.add_argument("--citation-identity-report")
    verify_discovery_manifest.add_argument("--attribution-consensus-report")
    verify_discovery_manifest.add_argument("--verifier-quorum-report")
    verify_discovery_manifest.add_argument("--verifier-accountability-report")
    verify_discovery_manifest.add_argument("--receipt-transparency-consistency-report")
    verify_discovery_manifest.add_argument("--watchtower-challenge-settlement-report")
    verify_discovery_manifest.add_argument("--output-provenance-binding-report")
    verify_discovery_manifest.add_argument("--rights-remediation-report")
    verify_discovery_manifest.add_argument("--semantic-text-attribution-report")
    verify_discovery_manifest.add_argument("--code-attribution-report")
    verify_discovery_manifest.add_argument("--claim-verification-report")
    verify_discovery_manifest.add_argument("--source-availability-report")
    verify_discovery_manifest.add_argument("--evidence-sufficiency-report")
    verify_discovery_manifest.add_argument("--counterevidence-report")
    verify_discovery_manifest.add_argument("--answer-claim-coverage-report")
    verify_discovery_manifest.add_argument("--generation-context-closure-report")
    verify_discovery_manifest.add_argument("--source-boundary-report")
    verify_discovery_manifest.add_argument("--source-authenticity-report")
    verify_discovery_manifest.add_argument("--decision-provenance-report")
    verify_discovery_manifest.add_argument("--calibrated-attribution-report")
    verify_discovery_manifest.add_argument("--streaming-attribution-manifest")
    verify_discovery_manifest.add_argument("--conversation-attribution-ledger")
    verify_discovery_manifest.add_argument("--agent-tool-attribution-ledger")
    verify_discovery_manifest.add_argument("--creator-license-contract")
    verify_discovery_manifest.add_argument("--source-confidence-report")
    verify_discovery_manifest.add_argument("--citation-footer-contract")
    verify_discovery_manifest.add_argument("--private-audit-challenge")
    verify_discovery_manifest.add_argument("--transitive-attribution-report")
    verify_discovery_manifest.add_argument("--clearinghouse-report")
    verify_discovery_manifest.add_argument("--remittance-report")
    verify_discovery_manifest.add_argument("--payment-execution-report")
    verify_discovery_manifest.add_argument("--payment-rail-attestation")
    verify_discovery_manifest.add_argument("--creator-payout-receipt-report")
    verify_discovery_manifest.add_argument("--rendered-attribution-audit")
    verify_discovery_manifest.add_argument("--training-memory-provenance")
    verify_discovery_manifest.add_argument("--post-training-signal-provenance")
    verify_discovery_manifest.add_argument("--evidence-locked-generation")
    verify_discovery_manifest.add_argument("--emission-evidence-enforcement")
    verify_discovery_manifest.add_argument("--live-emission-witness")
    verify_discovery_manifest.add_argument("--live-emission-transparency")
    verify_discovery_manifest.add_argument("--attested-runtime")
    verify_discovery_manifest.add_argument("--claim-source-attribution-report")
    verify_discovery_manifest.add_argument("--evidence-utility-attribution-report")
    verify_discovery_manifest.add_argument("--parametric-memory-attribution-report")
    verify_discovery_manifest.add_argument("--style-influence-attribution-report")
    verify_discovery_manifest.add_argument("--model-lineage-attribution-report")
    verify_discovery_manifest.add_argument("--black-box-model-provenance-report")
    verify_discovery_manifest.add_argument("--attribution-dispute-adjudication-report")
    verify_discovery_manifest.add_argument(
        "--post-adjudication-settlement-adjustment-report"
    )
    verify_discovery_manifest.add_argument("--residual-corpus-royalty-report")
    verify_discovery_manifest.add_argument("--valuation-method-audit-report")
    verify_discovery_manifest.add_argument("--evidence-region-binding-report")
    verify_discovery_manifest.add_argument("--source-access-lease-report")
    verify_discovery_manifest.add_argument("--content-protocol-ingestion-report")
    verify_discovery_manifest.add_argument("--citation-reliance-receipt")
    verify_discovery_manifest.add_argument("--license-transaction-receipt")
    verify_discovery_manifest.add_argument("--grounded-source-footer")
    verify_discovery_manifest.add_argument("--source-footer-delivery")
    verify_discovery_manifest.add_argument("--deep-research-citation-audit")
    verify_discovery_manifest.add_argument("--source-freshness-audit")
    verify_discovery_manifest.add_argument("--royalty-abuse-audit")
    verify_discovery_manifest.add_argument("--consent-revocation-propagation")
    verify_discovery_manifest.add_argument("--evidence-force-calibration")
    verify_discovery_manifest.add_argument("--warranted-source-footer")
    verify_discovery_manifest.add_argument("--source-origin-lineage")
    verify_discovery_manifest.add_argument("--evidence-preview-footer")
    verify_discovery_manifest.add_argument("--evidence-locator-manifest")
    verify_discovery_manifest.add_argument("--citation-url-health")
    verify_discovery_manifest.add_argument("--foundation-api-profile")
    verify_discovery_manifest.add_argument("--composite-foundation-adapter")
    verify_discovery_manifest.add_argument("--foundation-provider-conformance")
    verify_discovery_manifest.add_argument("--foundation-runtime-adapter")
    verify_discovery_manifest.add_argument("--foundation-runtime-router")
    verify_discovery_manifest.add_argument("--foundation-model-deployment-attestation")
    verify_discovery_manifest.add_argument("--universal-composition-receipt")
    verify_discovery_manifest.add_argument("--universal-composition-settlement")
    verify_discovery_manifest.add_argument("--universal-foundation-model-contract")
    verify_discovery_manifest.add_argument("--universal-invocation-guard")
    verify_discovery_manifest.add_argument("--universal-invocation-coverage")
    verify_discovery_manifest.add_argument("--universal-invocation-witness")
    verify_discovery_manifest.add_argument("--universal-content-credential")
    verify_discovery_manifest.add_argument("--universal-rdllm-passport")
    verify_discovery_manifest.add_argument("--universal-adoption-standard")
    verify_discovery_manifest.add_argument("--universal-interop-test-kit")
    verify_discovery_manifest.add_argument("--universal-context-provenance-bridge")
    verify_discovery_manifest.add_argument("--universal-citation-verification-contract")
    verify_discovery_manifest.add_argument("--universal-grounded-reuse-contract")
    verify_discovery_manifest.add_argument("--universal-training-serving-contract")
    verify_discovery_manifest.add_argument("--universal-confidential-attribution-audit")
    verify_discovery_manifest.add_argument("--universal-attribution-authority-control-plane")
    verify_discovery_manifest.add_argument("--revenue-allocation-report")
    verify_discovery_manifest.add_argument("--finance-ledger-attestation")
    verify_discovery_manifest.add_argument("--proof-dependency-graph")
    verify_discovery_manifest.add_argument("--publication-monitor")
    verify_discovery_manifest.add_argument("--publication-witness")
    verify_discovery_manifest.add_argument("--trust-registry")
    verify_discovery_manifest.add_argument("--certification-attestation")
    verify_discovery_manifest.add_argument("--signing-secret")
    verify_discovery_manifest.set_defaults(func=run_verify_discovery_manifest)

    attribution_exchange = subparsers.add_parser(
        "attribution-exchange",
        help="Create a cross-provider attribution exchange manifest.",
    )
    attribution_exchange.add_argument("--provider-card", required=True)
    attribution_exchange.add_argument("--certification-report", required=True)
    attribution_exchange.add_argument("--integration-profile", required=True)
    attribution_exchange.add_argument("--discovery-manifest", required=True)
    attribution_exchange.add_argument("--response-envelope", required=True)
    attribution_exchange.add_argument("--assurance-bundle", required=True)
    attribution_exchange.add_argument("--semantic-text-attribution-report", required=True)
    attribution_exchange.add_argument("--creator-license-contract", required=True)
    attribution_exchange.add_argument("--source-confidence-report")
    attribution_exchange.add_argument("--citation-footer-contract")
    attribution_exchange.add_argument("--private-audit-challenge")
    attribution_exchange.add_argument("--issuer", default="rdllm-local-demo")
    attribution_exchange.add_argument("--signing-secret")
    attribution_exchange.add_argument("--output")
    attribution_exchange.set_defaults(func=run_attribution_exchange)

    verify_attribution_exchange = subparsers.add_parser(
        "verify-attribution-exchange",
        help="Verify a cross-provider attribution exchange manifest.",
    )
    verify_attribution_exchange.add_argument("--exchange", required=True)
    verify_attribution_exchange.add_argument("--provider-card", required=True)
    verify_attribution_exchange.add_argument("--certification-report", required=True)
    verify_attribution_exchange.add_argument("--integration-profile", required=True)
    verify_attribution_exchange.add_argument("--discovery-manifest", required=True)
    verify_attribution_exchange.add_argument("--response-envelope", required=True)
    verify_attribution_exchange.add_argument("--assurance-bundle", required=True)
    verify_attribution_exchange.add_argument(
        "--semantic-text-attribution-report", required=True
    )
    verify_attribution_exchange.add_argument("--creator-license-contract", required=True)
    verify_attribution_exchange.add_argument("--source-confidence-report")
    verify_attribution_exchange.add_argument("--citation-footer-contract")
    verify_attribution_exchange.add_argument("--private-audit-challenge")
    verify_attribution_exchange.add_argument("--training-summary")
    verify_attribution_exchange.add_argument("--provenance-evaluation-report")
    verify_attribution_exchange.add_argument("--counterfactual-report")
    verify_attribution_exchange.add_argument("--media-attribution-report")
    verify_attribution_exchange.add_argument("--model-signal-report")
    verify_attribution_exchange.add_argument("--rights-remediation-report")
    verify_attribution_exchange.add_argument("--signing-secret")
    verify_attribution_exchange.set_defaults(func=run_verify_attribution_exchange)

    conformance_vectors = subparsers.add_parser(
        "conformance-vector-pack",
        help="Create a portable RDLLM conformance vector pack.",
    )
    conformance_vectors.add_argument("--provider-card", required=True)
    conformance_vectors.add_argument("--certification-report", required=True)
    conformance_vectors.add_argument("--integration-profile", required=True)
    conformance_vectors.add_argument("--discovery-manifest", required=True)
    conformance_vectors.add_argument("--response-envelope", required=True)
    conformance_vectors.add_argument("--assurance-bundle", required=True)
    conformance_vectors.add_argument("--semantic-text-attribution-report", required=True)
    conformance_vectors.add_argument("--creator-license-contract", required=True)
    conformance_vectors.add_argument("--attribution-exchange", required=True)
    conformance_vectors.add_argument("--source-confidence-report")
    conformance_vectors.add_argument("--citation-footer-contract")
    conformance_vectors.add_argument("--private-audit-challenge")
    conformance_vectors.add_argument("--training-summary")
    conformance_vectors.add_argument("--provenance-evaluation-report")
    conformance_vectors.add_argument("--counterfactual-report")
    conformance_vectors.add_argument("--media-attribution-report")
    conformance_vectors.add_argument("--model-signal-report")
    conformance_vectors.add_argument("--rights-remediation-report")
    conformance_vectors.add_argument("--issuer", default="rdllm-local-demo")
    conformance_vectors.add_argument("--signing-secret")
    conformance_vectors.add_argument("--output")
    conformance_vectors.set_defaults(func=run_conformance_vector_pack)

    verify_conformance_vectors = subparsers.add_parser(
        "verify-conformance-vector-pack",
        help="Verify a portable RDLLM conformance vector pack.",
    )
    verify_conformance_vectors.add_argument("--pack", required=True)
    verify_conformance_vectors.add_argument("--provider-card", required=True)
    verify_conformance_vectors.add_argument("--certification-report", required=True)
    verify_conformance_vectors.add_argument("--integration-profile", required=True)
    verify_conformance_vectors.add_argument("--discovery-manifest", required=True)
    verify_conformance_vectors.add_argument("--response-envelope", required=True)
    verify_conformance_vectors.add_argument("--assurance-bundle", required=True)
    verify_conformance_vectors.add_argument("--semantic-text-attribution-report", required=True)
    verify_conformance_vectors.add_argument("--creator-license-contract", required=True)
    verify_conformance_vectors.add_argument("--attribution-exchange", required=True)
    verify_conformance_vectors.add_argument("--training-summary")
    verify_conformance_vectors.add_argument("--provenance-evaluation-report")
    verify_conformance_vectors.add_argument("--counterfactual-report")
    verify_conformance_vectors.add_argument("--media-attribution-report")
    verify_conformance_vectors.add_argument("--model-signal-report")
    verify_conformance_vectors.add_argument("--rights-remediation-report")
    verify_conformance_vectors.add_argument("--source-confidence-report")
    verify_conformance_vectors.add_argument("--citation-footer-contract")
    verify_conformance_vectors.add_argument("--private-audit-challenge")
    verify_conformance_vectors.add_argument("--signing-secret")
    verify_conformance_vectors.set_defaults(func=run_verify_conformance_vector_pack)

    federation_handshake = subparsers.add_parser(
        "federation-handshake",
        help="Create a signed runtime federation handshake for RDLLM providers.",
    )
    federation_handshake.add_argument("--provider-card", required=True)
    federation_handshake.add_argument("--certification-report", required=True)
    federation_handshake.add_argument("--integration-profile", required=True)
    federation_handshake.add_argument("--discovery-manifest", required=True)
    federation_handshake.add_argument("--response-envelope", required=True)
    federation_handshake.add_argument("--assurance-bundle", required=True)
    federation_handshake.add_argument("--semantic-text-attribution-report", required=True)
    federation_handshake.add_argument("--creator-license-contract", required=True)
    federation_handshake.add_argument("--attribution-exchange", required=True)
    federation_handshake.add_argument("--conformance-vector-pack", required=True)
    federation_handshake.add_argument("--training-summary")
    federation_handshake.add_argument("--provenance-evaluation-report")
    federation_handshake.add_argument("--counterfactual-report")
    federation_handshake.add_argument("--media-attribution-report")
    federation_handshake.add_argument("--model-signal-report")
    federation_handshake.add_argument("--rights-remediation-report")
    federation_handshake.add_argument("--source-confidence-report")
    federation_handshake.add_argument("--citation-footer-contract")
    federation_handshake.add_argument("--private-audit-challenge")
    federation_handshake.add_argument("--requester", default="requester:unspecified")
    federation_handshake.add_argument("--requester-model-id", default="model:unspecified")
    federation_handshake.add_argument("--requester-model-version", default="unknown")
    federation_handshake.add_argument("--minimum-level", default="RDLLM-L32")
    federation_handshake.add_argument("--issuer", default="rdllm-local-demo")
    federation_handshake.add_argument("--signing-secret")
    federation_handshake.add_argument("--output")
    federation_handshake.set_defaults(func=run_federation_handshake)

    verify_federation_handshake = subparsers.add_parser(
        "verify-federation-handshake",
        help="Verify a signed runtime federation handshake against public artifacts.",
    )
    verify_federation_handshake.add_argument("--handshake", required=True)
    verify_federation_handshake.add_argument("--provider-card", required=True)
    verify_federation_handshake.add_argument("--certification-report", required=True)
    verify_federation_handshake.add_argument("--integration-profile", required=True)
    verify_federation_handshake.add_argument("--discovery-manifest", required=True)
    verify_federation_handshake.add_argument("--response-envelope", required=True)
    verify_federation_handshake.add_argument("--assurance-bundle", required=True)
    verify_federation_handshake.add_argument(
        "--semantic-text-attribution-report", required=True
    )
    verify_federation_handshake.add_argument("--creator-license-contract", required=True)
    verify_federation_handshake.add_argument("--attribution-exchange", required=True)
    verify_federation_handshake.add_argument("--conformance-vector-pack", required=True)
    verify_federation_handshake.add_argument("--training-summary")
    verify_federation_handshake.add_argument("--provenance-evaluation-report")
    verify_federation_handshake.add_argument("--counterfactual-report")
    verify_federation_handshake.add_argument("--media-attribution-report")
    verify_federation_handshake.add_argument("--model-signal-report")
    verify_federation_handshake.add_argument("--rights-remediation-report")
    verify_federation_handshake.add_argument("--source-confidence-report")
    verify_federation_handshake.add_argument("--citation-footer-contract")
    verify_federation_handshake.add_argument("--private-audit-challenge")
    verify_federation_handshake.add_argument("--signing-secret")
    verify_federation_handshake.set_defaults(func=run_verify_federation_handshake)

    attribution_capsule = subparsers.add_parser(
        "attribution-capsule",
        help="Create a portable attribution capsule for copied or reposted RDLLM outputs.",
    )
    attribution_capsule.add_argument("--response-envelope", required=True)
    attribution_capsule.add_argument("--federation-handshake", required=True)
    attribution_capsule.add_argument("--attribution-exchange", required=True)
    attribution_capsule.add_argument("--conformance-vector-pack", required=True)
    attribution_capsule.add_argument("--provider-card", required=True)
    attribution_capsule.add_argument("--certification-report", required=True)
    attribution_capsule.add_argument("--integration-profile", required=True)
    attribution_capsule.add_argument("--discovery-manifest", required=True)
    attribution_capsule.add_argument("--assurance-bundle", required=True)
    attribution_capsule.add_argument("--semantic-text-attribution-report", required=True)
    attribution_capsule.add_argument("--creator-license-contract", required=True)
    attribution_capsule.add_argument("--training-summary")
    attribution_capsule.add_argument("--provenance-evaluation-report")
    attribution_capsule.add_argument("--counterfactual-report")
    attribution_capsule.add_argument("--media-attribution-report")
    attribution_capsule.add_argument("--model-signal-report")
    attribution_capsule.add_argument("--rights-remediation-report")
    attribution_capsule.add_argument("--source-confidence-report")
    attribution_capsule.add_argument("--citation-footer-contract")
    attribution_capsule.add_argument("--private-audit-challenge")
    attribution_capsule.add_argument("--issuer", default="rdllm-local-demo")
    attribution_capsule.add_argument("--signing-secret")
    attribution_capsule.add_argument("--output")
    attribution_capsule.set_defaults(func=run_attribution_capsule)

    verify_attribution_capsule = subparsers.add_parser(
        "verify-attribution-capsule",
        help="Verify a portable attribution capsule against public RDLLM artifacts.",
    )
    verify_attribution_capsule.add_argument("--capsule", required=True)
    verify_attribution_capsule.add_argument("--response-envelope", required=True)
    verify_attribution_capsule.add_argument("--federation-handshake", required=True)
    verify_attribution_capsule.add_argument("--attribution-exchange", required=True)
    verify_attribution_capsule.add_argument("--conformance-vector-pack", required=True)
    verify_attribution_capsule.add_argument("--provider-card", required=True)
    verify_attribution_capsule.add_argument("--certification-report", required=True)
    verify_attribution_capsule.add_argument("--integration-profile", required=True)
    verify_attribution_capsule.add_argument("--discovery-manifest", required=True)
    verify_attribution_capsule.add_argument("--assurance-bundle", required=True)
    verify_attribution_capsule.add_argument(
        "--semantic-text-attribution-report", required=True
    )
    verify_attribution_capsule.add_argument("--creator-license-contract", required=True)
    verify_attribution_capsule.add_argument("--training-summary")
    verify_attribution_capsule.add_argument("--provenance-evaluation-report")
    verify_attribution_capsule.add_argument("--counterfactual-report")
    verify_attribution_capsule.add_argument("--media-attribution-report")
    verify_attribution_capsule.add_argument("--model-signal-report")
    verify_attribution_capsule.add_argument("--rights-remediation-report")
    verify_attribution_capsule.add_argument("--source-confidence-report")
    verify_attribution_capsule.add_argument("--citation-footer-contract")
    verify_attribution_capsule.add_argument("--private-audit-challenge")
    verify_attribution_capsule.add_argument("--copied-output")
    verify_attribution_capsule.add_argument("--copied-output-file")
    verify_attribution_capsule.add_argument("--signing-secret")
    verify_attribution_capsule.set_defaults(func=run_verify_attribution_capsule)

    release_gate = subparsers.add_parser(
        "release-gate",
        help="Create an emit-time RDLLM response release gate.",
    )
    release_gate.add_argument("--response-envelope", required=True)
    release_gate.add_argument("--attribution-capsule", required=True)
    release_gate.add_argument("--creator-license-contract", required=True)
    release_gate.add_argument("--provider-card", required=True)
    release_gate.add_argument("--certification-report", required=True)
    release_gate.add_argument("--issuer", default="rdllm-local-demo")
    release_gate.add_argument("--signing-secret")
    release_gate.add_argument("--output")
    release_gate.set_defaults(func=run_release_gate)

    verify_release_gate = subparsers.add_parser(
        "verify-release-gate",
        help="Verify an emit-time RDLLM response release gate.",
    )
    verify_release_gate.add_argument("--gate", required=True)
    verify_release_gate.add_argument("--response-envelope", required=True)
    verify_release_gate.add_argument("--attribution-capsule", required=True)
    verify_release_gate.add_argument("--creator-license-contract", required=True)
    verify_release_gate.add_argument("--provider-card", required=True)
    verify_release_gate.add_argument("--certification-report", required=True)
    verify_release_gate.add_argument("--signing-secret")
    verify_release_gate.set_defaults(func=run_verify_release_gate)

    proof_response = subparsers.add_parser(
        "proof-carrying-response",
        help="Create a proof-carrying response that enforces the release gate.",
    )
    proof_response.add_argument("--response-envelope", required=True)
    proof_response.add_argument("--attribution-capsule", required=True)
    proof_response.add_argument("--release-gate", required=True)
    proof_response.add_argument("--creator-license-contract", required=True)
    proof_response.add_argument("--provider-card", required=True)
    proof_response.add_argument("--certification-report", required=True)
    proof_response.add_argument("--issuer", default="rdllm-local-demo")
    proof_response.add_argument("--signing-secret")
    proof_response.add_argument("--output")
    proof_response.set_defaults(func=run_proof_carrying_response)

    verify_proof_response = subparsers.add_parser(
        "verify-proof-carrying-response",
        help="Verify a proof-carrying response using embedded public artifacts.",
    )
    verify_proof_response.add_argument("--response", required=True)
    verify_proof_response.add_argument("--signing-secret")
    verify_proof_response.set_defaults(func=run_verify_proof_carrying_response)

    gateway = subparsers.add_parser(
        "serving-gateway-report",
        help="Create a serving gateway report that proves API egress used the proof-carrying response.",
    )
    gateway.add_argument("--proof-response", required=True)
    gateway.add_argument("--request-id", required=True)
    gateway.add_argument("--provider", default="provider:unspecified")
    gateway.add_argument("--model-id", default="model:unspecified")
    gateway.add_argument("--model-version", default="unknown")
    gateway.add_argument("--route-id", default="route:default")
    gateway.add_argument("--prompt")
    gateway.add_argument("--prompt-file")
    gateway.add_argument("--raw-model-output")
    gateway.add_argument("--raw-model-output-file")
    gateway.add_argument("--delivered-output")
    gateway.add_argument("--delivered-output-file")
    gateway.add_argument("--issuer", default="rdllm-local-demo")
    gateway.add_argument("--signing-secret")
    gateway.add_argument("--output")
    gateway.set_defaults(func=run_serving_gateway_report)

    verify_gateway = subparsers.add_parser(
        "verify-serving-gateway-report",
        help="Verify a serving gateway report and its embedded proof-carrying response.",
    )
    verify_gateway.add_argument("--report", required=True)
    verify_gateway.add_argument("--prompt")
    verify_gateway.add_argument("--prompt-file")
    verify_gateway.add_argument("--raw-model-output")
    verify_gateway.add_argument("--raw-model-output-file")
    verify_gateway.add_argument("--delivered-output")
    verify_gateway.add_argument("--delivered-output-file")
    verify_gateway.add_argument("--signing-secret")
    verify_gateway.set_defaults(func=run_verify_serving_gateway_report)

    streaming = subparsers.add_parser(
        "streaming-attribution-manifest",
        help="Create a hash-chain manifest that binds streamed chunks to a proof-carrying response and serving gateway report.",
    )
    streaming.add_argument("--proof-response", required=True)
    streaming.add_argument("--serving-gateway-report", required=True)
    streaming.add_argument("--chunks-file")
    streaming.add_argument("--chunk-size", type=int, default=96)
    streaming.add_argument("--proof-verified-at")
    streaming.add_argument("--gateway-verified-at")
    streaming.add_argument("--stream-started-at")
    streaming.add_argument("--stream-completed-at")
    streaming.add_argument("--issuer", default="rdllm-local-demo")
    streaming.add_argument("--signing-secret")
    streaming.add_argument("--output")
    streaming.set_defaults(func=run_streaming_attribution_manifest)

    verify_streaming = subparsers.add_parser(
        "verify-streaming-attribution-manifest",
        help="Verify a streaming attribution manifest and its chunk hash chain.",
    )
    verify_streaming.add_argument("--manifest", required=True)
    verify_streaming.add_argument("--signing-secret")
    verify_streaming.set_defaults(func=run_verify_streaming_attribution_manifest)

    conversation = subparsers.add_parser(
        "conversation-attribution-ledger",
        help="Create a turn-chain ledger that preserves source attribution obligations across an LLM conversation.",
    )
    conversation.add_argument("--conversation-id", required=True)
    conversation.add_argument("--session-state-id", default="session:default")
    conversation.add_argument(
        "--turn",
        action="append",
        help="turn_id:proof_response:serving_gateway:streaming_manifest:depends_csv_or_-",
    )
    conversation.add_argument("--turns-file")
    conversation.add_argument("--issuer", default="rdllm-local-demo")
    conversation.add_argument("--signing-secret")
    conversation.add_argument("--output")
    conversation.set_defaults(func=run_conversation_attribution_ledger)

    verify_conversation = subparsers.add_parser(
        "verify-conversation-attribution-ledger",
        help="Verify a conversation attribution ledger and its inherited source obligations.",
    )
    verify_conversation.add_argument("--ledger", required=True)
    verify_conversation.add_argument("--signing-secret")
    verify_conversation.set_defaults(func=run_verify_conversation_attribution_ledger)

    agent_tool = subparsers.add_parser(
        "agent-tool-attribution-ledger",
        help="Create a ledger binding agent/tool observations to trace spans, claims, visible sources, and royalty obligations.",
    )
    agent_tool.add_argument("--proof-response", required=True)
    agent_tool.add_argument("--trace-exchange", required=True)
    agent_tool.add_argument("--conversation-attribution-ledger", required=True)
    agent_tool.add_argument("--issuer", default="rdllm-local-demo")
    agent_tool.add_argument("--signing-secret")
    agent_tool.add_argument("--output")
    agent_tool.set_defaults(func=run_agent_tool_attribution_ledger)

    verify_agent_tool = subparsers.add_parser(
        "verify-agent-tool-attribution-ledger",
        help="Verify an agent/tool attribution ledger against its embedded proof response, trace, and conversation ledger.",
    )
    verify_agent_tool.add_argument("--ledger", required=True)
    verify_agent_tool.add_argument("--signing-secret")
    verify_agent_tool.set_defaults(func=run_verify_agent_tool_attribution_ledger)

    match = subparsers.add_parser(
        "match-text", help="Find registered owners whose text appears in an output."
    )
    match.add_argument("output")
    match.add_argument("--limit", type=int)
    match.set_defaults(func=run_match_text)

    value = subparsers.add_parser(
        "value-training", help="Compute Shapley-style training value priors."
    )
    value.add_argument("--prompt", action="append")
    value.set_defaults(func=run_value_training)

    grounding = subparsers.add_parser(
        "evaluate-grounding",
        help="Score whether source labels, evidence spans, rights, and payouts agree.",
    )
    grounding.add_argument("prompt")
    grounding.add_argument("--output")
    grounding.add_argument("--report", help="Optional path to write grounding quality JSON.")
    grounding.set_defaults(func=run_evaluate_grounding)

    gap = subparsers.add_parser(
        "attribution-gap",
        help="Report consumed-vs-cited-vs-paid source attribution gaps.",
    )
    gap.add_argument("prompt")
    gap.add_argument("--output")
    gap.add_argument("--report", help="Optional path to write attribution-gap JSON.")
    gap.set_defaults(func=run_attribution_gap)

    receipt = subparsers.add_parser(
        "receipt", help="Create an attribution receipt and optional transparency proof."
    )
    receipt.add_argument("prompt")
    receipt.add_argument("--output")
    receipt.add_argument("--issuer", default="rdllm-local-demo")
    receipt.add_argument("--model-id", default="model:unspecified")
    receipt.add_argument("--model-version", default="unknown")
    receipt.add_argument("--route-id", default="route:default")
    receipt.add_argument("--signing-secret")
    receipt.add_argument("--receipt", help="Write full receipt JSON to this path.")
    receipt.add_argument("--ledger", help="Write a matching one-event ledger JSON.")
    receipt.add_argument(
        "--public-receipt", help="Write privacy-reduced public receipt JSON."
    )
    receipt.add_argument("--log", help="Append receipt to this transparency log JSON.")
    receipt.add_argument("--proof", help="Write transparency inclusion proof JSON.")
    receipt.set_defaults(func=run_receipt)

    verify = subparsers.add_parser(
        "verify-receipt", help="Verify a receipt hash/signature and optional inclusion proof."
    )
    verify.add_argument("--receipt", required=True)
    verify.add_argument("--signing-secret")
    verify.add_argument("--log")
    verify.add_argument("--proof")
    verify.set_defaults(func=run_verify_receipt)

    disclose = subparsers.add_parser(
        "disclose",
        help="Create a selective-disclosure package from a full attribution receipt.",
    )
    disclose.add_argument("--receipt", required=True)
    disclose.add_argument("--output", help="Optional path to write disclosure JSON.")
    disclose.add_argument(
        "--disclose-path",
        action="append",
        default=None,
        help="Optional additional JSON-pointer path or prefix to disclose.",
    )
    disclose.set_defaults(func=run_disclose)

    verify_disclosure = subparsers.add_parser(
        "verify-disclosure",
        help="Verify a selective-disclosure package and optional private receipt.",
    )
    verify_disclosure.add_argument("--package", required=True)
    verify_disclosure.add_argument("--receipt")
    verify_disclosure.add_argument("--signing-secret")
    verify_disclosure.set_defaults(func=run_verify_disclosure)

    trace = subparsers.add_parser(
        "trace",
        help="Export an OpenTelemetry-aligned RDLLM trace exchange.",
    )
    trace.add_argument("prompt", nargs="?")
    trace.add_argument("--output")
    trace.add_argument("--receipt", help="Build trace from an existing receipt JSON.")
    trace.add_argument(
        "--generated-receipt",
        help="When tracing a prompt, write the matching generated receipt JSON.",
    )
    trace.add_argument("--ledger", help="When tracing a prompt, write a matching one-event ledger JSON.")
    trace.add_argument("--external-output")
    trace.add_argument("--issuer", default="rdllm-local-demo")
    trace.add_argument("--model-id", default="model:unspecified")
    trace.add_argument("--model-version", default="unknown")
    trace.add_argument("--route-id", default="route:default")
    trace.add_argument("--provider-name", default="rdllm.reference")
    trace.add_argument("--signing-secret")
    trace.set_defaults(func=run_trace)

    verify_trace = subparsers.add_parser(
        "verify-trace",
        help="Verify a trace exchange against a receipt and/or ledger event.",
    )
    verify_trace.add_argument("--trace", required=True)
    verify_trace.add_argument("--receipt")
    verify_trace.add_argument("--ledger")
    verify_trace.add_argument("--event-id")
    verify_trace.set_defaults(func=run_verify_trace)

    statement = subparsers.add_parser(
        "statement",
        help="Create a privacy-preserving aggregate royalty statement from a ledger.",
    )
    statement.add_argument("--ledger", required=True)
    statement.add_argument("--receipt", action="append", help="Receipt JSON to bind into the rollup.")
    statement.add_argument("--trace", action="append", help="Trace exchange JSON to bind into the rollup.")
    statement.add_argument("--issuer", default="rdllm-local-demo")
    statement.add_argument("--period-start", default="")
    statement.add_argument("--period-end", default="")
    statement.add_argument("--signing-secret")
    statement.add_argument("--output", help="Optional path to write statement JSON.")
    statement.set_defaults(func=run_statement)

    verify_statement = subparsers.add_parser(
        "verify-statement",
        help="Verify an aggregate royalty statement against its ledger and optional receipts/traces.",
    )
    verify_statement.add_argument("--ledger", required=True)
    verify_statement.add_argument("--statement", required=True)
    verify_statement.add_argument("--receipt", action="append")
    verify_statement.add_argument("--trace", action="append")
    verify_statement.add_argument("--signing-secret")
    verify_statement.set_defaults(func=run_verify_statement)

    revenue_allocation = subparsers.add_parser(
        "revenue-allocation-report",
        help="Create a report proving how billing, ad, subscription, API, or marketplace revenue was allocated into usage events.",
    )
    revenue_allocation.add_argument("--ledger", required=True)
    revenue_allocation.add_argument("--revenue-sources", required=True)
    revenue_allocation.add_argument("--receipt", action="append")
    revenue_allocation.add_argument(
        "--allocation-mode",
        default="ledger_gross_revenue",
        choices=[
            "ledger_gross_revenue",
            "equal_event_split",
            "event_count",
            "request_count",
            "source_access_count",
            "visible_source_count",
            "supported_claim_count",
            "output_token_count",
            "total_token_count",
            "output_character_count",
            "subscription_usage",
            "ad_impression",
            "api_metered_tokens",
            "weighted_engagement",
        ],
    )
    revenue_allocation.add_argument(
        "--allocation-policy-id",
        default="revenue-allocation:ledger-gross",
    )
    revenue_allocation.add_argument("--allocation-policy")
    revenue_allocation.add_argument("--currency", default="USD")
    revenue_allocation.add_argument("--issuer", default="rdllm-local-demo")
    revenue_allocation.add_argument("--signing-secret")
    revenue_allocation.add_argument("--output")
    revenue_allocation.set_defaults(func=run_revenue_allocation_report)

    verify_revenue_allocation = subparsers.add_parser(
        "verify-revenue-allocation-report",
        help="Verify a revenue allocation report against ledger events, receipts, and source revenue pools.",
    )
    verify_revenue_allocation.add_argument("--report", required=True)
    verify_revenue_allocation.add_argument("--ledger", required=True)
    verify_revenue_allocation.add_argument("--revenue-sources", required=True)
    verify_revenue_allocation.add_argument("--receipt", action="append")
    verify_revenue_allocation.add_argument("--signing-secret")
    verify_revenue_allocation.set_defaults(func=run_verify_revenue_allocation_report)

    finance_ledger = subparsers.add_parser(
        "finance-ledger-attestation",
        help="Create a hash-only attestation linking private finance exports to revenue allocation source pools.",
    )
    finance_ledger.add_argument("--finance-records", required=True)
    finance_ledger.add_argument("--revenue-allocation-report", required=True)
    finance_ledger.add_argument("--issuer", default="rdllm-local-demo")
    finance_ledger.add_argument("--signing-secret")
    finance_ledger.add_argument("--output")
    finance_ledger.set_defaults(func=run_finance_ledger_attestation)

    verify_finance_ledger = subparsers.add_parser(
        "verify-finance-ledger-attestation",
        help="Verify a finance ledger attestation against finance records and a revenue allocation report.",
    )
    verify_finance_ledger.add_argument("--attestation", required=True)
    verify_finance_ledger.add_argument("--finance-records", required=True)
    verify_finance_ledger.add_argument("--revenue-allocation-report", required=True)
    verify_finance_ledger.add_argument("--signing-secret")
    verify_finance_ledger.set_defaults(func=run_verify_finance_ledger_attestation)

    challenge = subparsers.add_parser(
        "challenge",
        help="Create a creator attribution challenge and correction report.",
    )
    challenge.add_argument("--ledger", required=True)
    challenge.add_argument("--event-id", required=True)
    challenge_target = challenge.add_mutually_exclusive_group(required=True)
    challenge_target.add_argument("--work-id")
    challenge_target.add_argument("--chunk-id")
    challenge.add_argument("--statement")
    challenge.add_argument("--issuer", default="rdllm-local-demo")
    challenge.add_argument("--claimant-id")
    challenge.add_argument("--reason", default="missing_attribution")
    challenge.add_argument("--accept-threshold", type=float, default=0.20)
    challenge.add_argument("--signing-secret")
    challenge.add_argument("--output")
    challenge.set_defaults(func=run_challenge)

    verify_challenge = subparsers.add_parser(
        "verify-challenge",
        help="Verify a creator attribution challenge against the ledger and source chunk.",
    )
    verify_challenge.add_argument("--ledger", required=True)
    verify_challenge.add_argument("--event-id", required=True)
    verify_challenge.add_argument("--challenge", required=True)
    verify_challenge_target = verify_challenge.add_mutually_exclusive_group(required=True)
    verify_challenge_target.add_argument("--work-id")
    verify_challenge_target.add_argument("--chunk-id")
    verify_challenge.add_argument("--statement")
    verify_challenge.add_argument("--signing-secret")
    verify_challenge.set_defaults(func=run_verify_challenge)

    provider_card = subparsers.add_parser(
        "provider-card",
        help="Create a provider-level attribution disclosure card.",
    )
    provider_card.add_argument("--ledger", required=True)
    provider_card.add_argument("--certification-report")
    provider_card.add_argument("--issuer", default="rdllm-local-demo")
    provider_card.add_argument("--provider", default="provider:unspecified")
    provider_card.add_argument("--model-id", default="model:unspecified")
    provider_card.add_argument("--model-version", default="unknown")
    provider_card.add_argument("--signing-secret")
    provider_card.add_argument("--output")
    provider_card.set_defaults(func=run_provider_card)

    verify_provider_card = subparsers.add_parser(
        "verify-provider-card",
        help="Verify a provider attribution card against a ledger and certification report.",
    )
    verify_provider_card.add_argument("--ledger", required=True)
    verify_provider_card.add_argument("--card", required=True)
    verify_provider_card.add_argument("--certification-report")
    verify_provider_card.add_argument("--signing-secret")
    verify_provider_card.set_defaults(func=run_verify_provider_card)

    training_summary = subparsers.add_parser(
        "training-summary",
        help="Create a public training-content summary for the registered corpus.",
    )
    training_summary.add_argument("--certification-report")
    training_summary.add_argument("--provider-card")
    training_summary.add_argument("--issuer", default="rdllm-local-demo")
    training_summary.add_argument("--provider", default="provider:unspecified")
    training_summary.add_argument("--model-id", default="model:unspecified")
    training_summary.add_argument("--model-version", default="unknown")
    training_summary.add_argument("--training-stage", default="reference_corpus")
    training_summary.add_argument("--signing-secret")
    training_summary.add_argument("--output")
    training_summary.set_defaults(func=run_training_summary)

    verify_training_summary = subparsers.add_parser(
        "verify-training-summary",
        help="Verify a training-content summary against the registered corpus.",
    )
    verify_training_summary.add_argument("--summary", required=True)
    verify_training_summary.add_argument("--certification-report")
    verify_training_summary.add_argument("--provider-card")
    verify_training_summary.add_argument("--signing-secret")
    verify_training_summary.set_defaults(func=run_verify_training_summary)

    assurance = subparsers.add_parser(
        "assurance-bundle",
        help="Create a public assurance bundle over RDLLM artifact hashes.",
    )
    assurance.add_argument(
        "--artifact",
        action="append",
        required=True,
        help="Artifact spec in name:type:path form.",
    )
    assurance.add_argument("--issuer", default="rdllm-local-demo")
    assurance.add_argument("--signing-secret")
    assurance.add_argument("--output")
    assurance.set_defaults(func=run_assurance_bundle)

    verify_assurance = subparsers.add_parser(
        "verify-assurance-bundle",
        help="Verify an assurance bundle against its artifact payloads.",
    )
    verify_assurance.add_argument("--bundle", required=True)
    verify_assurance.add_argument(
        "--artifact",
        action="append",
        required=True,
        help="Artifact spec in name:type:path form.",
    )
    verify_assurance.add_argument("--signing-secret")
    verify_assurance.set_defaults(func=run_verify_assurance_bundle)

    proof_graph = subparsers.add_parser(
        "proof-dependency-graph",
        help="Create a hash-only acyclic replay graph over RDLLM proof artifacts.",
    )
    proof_graph.add_argument(
        "--artifact",
        action="append",
        required=True,
        help="Artifact spec in name:type:path form.",
    )
    proof_graph.add_argument(
        "--dependency",
        action="append",
        help="Dependency spec dependent:dependency[:edge_class[:reason]] or JSON file.",
    )
    proof_graph.add_argument(
        "--no-publication-edges",
        action="store_true",
        help="Do not infer publication commitment edges for assurance bundles.",
    )
    proof_graph.add_argument("--issuer", default="rdllm-local-demo")
    proof_graph.add_argument("--signing-secret")
    proof_graph.add_argument("--output")
    proof_graph.set_defaults(func=run_proof_dependency_graph)

    verify_proof_graph = subparsers.add_parser(
        "verify-proof-dependency-graph",
        help="Verify a proof dependency graph against artifact payloads and dependency policy.",
    )
    verify_proof_graph.add_argument("--graph", required=True)
    verify_proof_graph.add_argument(
        "--artifact",
        action="append",
        required=True,
        help="Artifact spec in name:type:path form.",
    )
    verify_proof_graph.add_argument(
        "--dependency",
        action="append",
        help="Dependency spec dependent:dependency[:edge_class[:reason]] or JSON file.",
    )
    verify_proof_graph.add_argument(
        "--no-publication-edges",
        action="store_true",
        help="Do not infer publication commitment edges for assurance bundles.",
    )
    verify_proof_graph.add_argument("--signing-secret")
    verify_proof_graph.set_defaults(func=run_verify_proof_dependency_graph)

    publication_monitor = subparsers.add_parser(
        "publication-monitor",
        help="Create an append-only monitor checkpoint over public RDLLM artifacts.",
    )
    publication_monitor.add_argument(
        "--artifact",
        action="append",
        required=True,
        help="Artifact spec in name:type:path form.",
    )
    publication_monitor.add_argument(
        "--previous-monitor",
        help="Previous rdllm-publication-monitor/v1 report to extend.",
    )
    publication_monitor.add_argument("--issuer", default="rdllm-local-demo")
    publication_monitor.add_argument("--signing-secret")
    publication_monitor.add_argument("--output")
    publication_monitor.set_defaults(func=run_publication_monitor)

    verify_publication_monitor = subparsers.add_parser(
        "verify-publication-monitor",
        help="Verify an append-only publication monitor checkpoint against artifacts.",
    )
    verify_publication_monitor.add_argument("--monitor", required=True)
    verify_publication_monitor.add_argument(
        "--artifact",
        action="append",
        required=True,
        help="Artifact spec in name:type:path form.",
    )
    verify_publication_monitor.add_argument(
        "--previous-monitor",
        help="Previous rdllm-publication-monitor/v1 report required for append mode.",
    )
    verify_publication_monitor.add_argument("--signing-secret")
    verify_publication_monitor.set_defaults(func=run_verify_publication_monitor)

    publication_witness = subparsers.add_parser(
        "publication-witness",
        help="Create a witness quorum report over publication monitor checkpoints.",
    )
    publication_witness.add_argument(
        "--monitor",
        action="append",
        required=True,
        help="Path to an rdllm-publication-monitor/v1 report.",
    )
    publication_witness.add_argument(
        "--witness",
        action="append",
        required=True,
        help="Witness signing spec witness_id:secret.",
    )
    publication_witness.add_argument("--required-quorum", type=int)
    publication_witness.add_argument("--issuer", default="rdllm-local-demo")
    publication_witness.add_argument("--signing-secret")
    publication_witness.add_argument("--output")
    publication_witness.set_defaults(func=run_publication_witness)

    verify_publication_witness = subparsers.add_parser(
        "verify-publication-witness",
        help="Verify a publication witness quorum report against monitor checkpoints.",
    )
    verify_publication_witness.add_argument("--witness-report", required=True)
    verify_publication_witness.add_argument(
        "--monitor",
        action="append",
        required=True,
        help="Path to an rdllm-publication-monitor/v1 report.",
    )
    verify_publication_witness.add_argument(
        "--witness",
        action="append",
        required=True,
        help="Witness signing spec witness_id:secret.",
    )
    verify_publication_witness.add_argument("--signing-secret")
    verify_publication_witness.set_defaults(func=run_verify_publication_witness)

    trust_registry = subparsers.add_parser(
        "trust-registry",
        help="Create a public trust registry for RDLLM signers and witnesses.",
    )
    trust_registry.add_argument(
        "--artifact",
        action="append",
        required=True,
        help="Artifact spec in name:type:path form.",
    )
    trust_registry.add_argument(
        "--principal",
        action="append",
        required=True,
        help="Principal signing spec principal_id:role:secret.",
    )
    trust_registry.add_argument(
        "--publication-witness",
        action="append",
        help="Path to an rdllm-publication-witness/v1 report whose witness keys must be bound.",
    )
    trust_registry.add_argument(
        "--rotation",
        action="append",
        help="Rotation spec principal_id:role:previous_secret:new_secret.",
    )
    trust_registry.add_argument(
        "--revoked-key",
        action="append",
        help="Revoked-key spec principal_id:role:secret.",
    )
    trust_registry.add_argument("--issuer", default="rdllm-local-demo")
    trust_registry.add_argument("--signing-secret")
    trust_registry.add_argument("--output")
    trust_registry.set_defaults(func=run_trust_registry)

    verify_trust_registry = subparsers.add_parser(
        "verify-trust-registry",
        help="Verify a trust registry against artifacts, principals, rotations, and witness keys.",
    )
    verify_trust_registry.add_argument("--registry", required=True)
    verify_trust_registry.add_argument(
        "--artifact",
        action="append",
        required=True,
        help="Artifact spec in name:type:path form.",
    )
    verify_trust_registry.add_argument(
        "--principal",
        action="append",
        required=True,
        help="Principal signing spec principal_id:role:secret.",
    )
    verify_trust_registry.add_argument(
        "--publication-witness",
        action="append",
        help="Path to an rdllm-publication-witness/v1 report whose witness keys must be bound.",
    )
    verify_trust_registry.add_argument(
        "--rotation",
        action="append",
        help="Rotation spec principal_id:role:previous_secret:new_secret.",
    )
    verify_trust_registry.add_argument(
        "--revoked-key",
        action="append",
        help="Revoked-key spec principal_id:role:secret.",
    )
    verify_trust_registry.add_argument("--signing-secret")
    verify_trust_registry.set_defaults(func=run_verify_trust_registry)

    certification_attestation = subparsers.add_parser(
        "certification-attestation",
        help="Create a signed attestation over an RDLLM certification report.",
    )
    certification_attestation.add_argument("--certification-report", required=True)
    certification_attestation.add_argument(
        "--certifier-id",
        default="certifier:rdllm-reference",
    )
    certification_attestation.add_argument(
        "--target-provider",
        default="provider:unspecified",
    )
    certification_attestation.add_argument("--issuer", default="rdllm-local-demo")
    certification_attestation.add_argument("--valid-until", default="")
    certification_attestation.add_argument("--signing-secret")
    certification_attestation.add_argument("--output")
    certification_attestation.set_defaults(func=run_certification_attestation)

    verify_certification_attestation = subparsers.add_parser(
        "verify-certification-attestation",
        help="Verify a certification attestation against its certification report.",
    )
    verify_certification_attestation.add_argument("--attestation", required=True)
    verify_certification_attestation.add_argument("--certification-report", required=True)
    verify_certification_attestation.add_argument("--signing-secret")
    verify_certification_attestation.set_defaults(
        func=run_verify_certification_attestation
    )

    audit_attestation = subparsers.add_parser(
        "audit-attestation",
        help="Create a third-party hash-only audit attestation over the RDLLM proof pack.",
    )
    audit_attestation.add_argument("--provider-card", required=True)
    audit_attestation.add_argument("--certification-report", required=True)
    audit_attestation.add_argument("--certification-attestation")
    audit_attestation.add_argument("--integration-profile", required=True)
    audit_attestation.add_argument("--discovery-manifest", required=True)
    audit_attestation.add_argument("--assurance-bundle", required=True)
    audit_attestation.add_argument("--response-envelope", required=True)
    audit_attestation.add_argument("--source-confidence-report", required=True)
    audit_attestation.add_argument("--citation-footer-contract", required=True)
    audit_attestation.add_argument("--clearinghouse-report", required=True)
    audit_attestation.add_argument("--remittance-report", required=True)
    audit_attestation.add_argument("--payment-execution-report")
    audit_attestation.add_argument("--payment-processor-records")
    audit_attestation.add_argument("--revenue-allocation-report")
    audit_attestation.add_argument("--finance-ledger-attestation")
    audit_attestation.add_argument("--auditor-id", required=True)
    audit_attestation.add_argument("--auditor-name", default="")
    audit_attestation.add_argument("--verifier-id", default="rdllm-reference-verifier")
    audit_attestation.add_argument("--audit-period-start", default="")
    audit_attestation.add_argument("--audit-period-end", default="")
    audit_attestation.add_argument("--issuer", default="rdllm-independent-auditor")
    audit_attestation.add_argument("--signing-secret")
    audit_attestation.add_argument("--output")
    audit_attestation.set_defaults(func=run_audit_attestation)

    verify_audit_attestation = subparsers.add_parser(
        "verify-audit-attestation",
        help="Verify a third-party audit attestation against public RDLLM artifacts.",
    )
    verify_audit_attestation.add_argument("--attestation", required=True)
    verify_audit_attestation.add_argument("--provider-card", required=True)
    verify_audit_attestation.add_argument("--certification-report", required=True)
    verify_audit_attestation.add_argument("--certification-attestation")
    verify_audit_attestation.add_argument("--integration-profile", required=True)
    verify_audit_attestation.add_argument("--discovery-manifest", required=True)
    verify_audit_attestation.add_argument("--assurance-bundle", required=True)
    verify_audit_attestation.add_argument("--response-envelope", required=True)
    verify_audit_attestation.add_argument("--source-confidence-report", required=True)
    verify_audit_attestation.add_argument("--citation-footer-contract", required=True)
    verify_audit_attestation.add_argument("--clearinghouse-report", required=True)
    verify_audit_attestation.add_argument("--remittance-report", required=True)
    verify_audit_attestation.add_argument("--payment-execution-report")
    verify_audit_attestation.add_argument("--payment-processor-records")
    verify_audit_attestation.add_argument("--revenue-allocation-report")
    verify_audit_attestation.add_argument("--finance-ledger-attestation")
    verify_audit_attestation.add_argument("--signing-secret")
    verify_audit_attestation.set_defaults(func=run_verify_audit_attestation)

    conformance = subparsers.add_parser(
        "conformance", help="Verify ledger, receipt, source footer, and transparency proof together."
    )
    conformance.add_argument("--ledger", required=True)
    conformance.add_argument("--receipt", required=True)
    conformance.add_argument("--event-id")
    conformance.add_argument("--signing-secret")
    conformance.add_argument("--log")
    conformance.add_argument("--proof")
    conformance.add_argument("--trace")
    conformance.add_argument("--statement")
    conformance.add_argument(
        "--statement-receipt",
        action="append",
        help="Receipt JSON to use when verifying the statement rollup.",
    )
    conformance.add_argument(
        "--statement-trace",
        action="append",
        help="Trace exchange JSON to use when verifying the statement rollup.",
    )
    conformance.set_defaults(func=run_conformance)

    certify = subparsers.add_parser(
        "certify",
        help="Run the reference RDLLM certification suite and emit a report.",
    )
    certify.add_argument(
        "--restricted-corpus",
        default=str(Path("examples") / "restricted_corpus.json"),
        help="Corpus containing a source that should be blocked for generation.",
    )
    certify.add_argument(
        "--conflict-corpus",
        default=str(Path("examples") / "conflict_corpus.json"),
        help="Corpus containing duplicate ownership claims for registry-dispute certification.",
    )
    certify.add_argument("--signing-secret")
    certify.add_argument("--output", help="Optional path to write certification JSON.")
    certify.set_defaults(func=run_certify)

    registry = subparsers.add_parser(
        "registry-audit",
        help="Detect duplicate or near-duplicate ownership claims before settlement.",
    )
    registry.add_argument("--output", help="Optional path to write registry report JSON.")
    registry.add_argument(
        "--fail-on-conflict",
        action="store_true",
        help="Exit non-zero when the registry report contains open conflicts.",
    )
    registry.set_defaults(func=run_registry_audit)

    resolve = subparsers.add_parser(
        "resolve-escrow",
        help="Release registry-dispute escrow using a signed dispute resolution.",
    )
    resolve.add_argument("--ledger", required=True)
    resolve.add_argument("--resolution", required=True)
    resolve.add_argument("--signing-secret")
    resolve.add_argument("--output", help="Optional path to write settlement report JSON.")
    resolve.set_defaults(func=run_resolve_escrow)

    interop = subparsers.add_parser(
        "interop",
        help="Export a receipt as VC-shaped credentials and a PROV-shaped graph.",
    )
    interop.add_argument("--receipt", required=True)
    interop.add_argument("--settlement-report")
    interop.add_argument("--signing-secret")
    interop.add_argument("--output", help="Optional path to write interop bundle JSON.")
    interop.set_defaults(func=run_interop)

    verify_interop = subparsers.add_parser(
        "verify-interop",
        help="Verify an RDLLM interop bundle against its source receipt/report.",
    )
    verify_interop.add_argument("--bundle", required=True)
    verify_interop.add_argument("--receipt", required=True)
    verify_interop.add_argument("--settlement-report")
    verify_interop.add_argument("--signing-secret")
    verify_interop.set_defaults(func=run_verify_interop)

    manifest = subparsers.add_parser(
        "policy-manifest",
        help="Export an ODRL/Croissant/SPDX-aligned rights manifest.",
    )
    manifest.add_argument("--output", help="Optional path to write manifest JSON.")
    manifest.set_defaults(func=run_policy_manifest)

    license_contract = subparsers.add_parser(
        "creator-license-contract",
        help="Create a signed creator license contract for registered source use.",
    )
    license_contract.add_argument("--provider", default="provider:unspecified")
    license_contract.add_argument("--effective-at")
    license_contract.add_argument("--issuer", default="rdllm-local-demo")
    license_contract.add_argument("--signing-secret")
    license_contract.add_argument("--output")
    license_contract.set_defaults(func=run_creator_license_contract)

    verify_license_contract = subparsers.add_parser(
        "verify-creator-license-contract",
        help="Verify a creator license contract against the registered private corpus.",
    )
    verify_license_contract.add_argument("--contract", required=True)
    verify_license_contract.add_argument("--signing-secret")
    verify_license_contract.set_defaults(func=run_verify_creator_license_contract)

    policy_check = subparsers.add_parser(
        "policy-check",
        help="Evaluate whether a work or chunk is licensed for a use.",
    )
    policy_target = policy_check.add_mutually_exclusive_group(required=True)
    policy_target.add_argument("--work-id")
    policy_target.add_argument("--chunk-id")
    policy_check.add_argument("--use", required=True)
    policy_check.set_defaults(func=run_policy_check)

    audit = subparsers.add_parser("audit", help="Audit a saved ledger JSON file.")
    audit.add_argument("--ledger", required=True)
    audit.set_defaults(func=audit_ledger)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
