"""Production-grade Royalty Driven LLM reference package."""

from rdllm.assurance import (
    make_assurance_bundle,
    validate_assurance_bundle_shape,
    verify_assurance_bundle,
)
from rdllm.audit_attestation import (
    make_audit_attestation,
    validate_audit_attestation_shape,
    verify_audit_attestation,
)
from rdllm.attribution_exchange import (
    make_attribution_exchange_manifest,
    validate_attribution_exchange_shape,
    verify_attribution_exchange_manifest,
)
from rdllm.answer_card import (
    make_answer_provenance_card,
    validate_answer_provenance_card_shape,
    verify_answer_provenance_card,
)
from rdllm.answer_coverage import (
    make_answer_claim_coverage_report,
    validate_answer_claim_coverage_report_shape,
    verify_answer_claim_coverage_report,
)
from rdllm.calibrated_attribution import (
    make_calibrated_attribution_report,
    validate_calibrated_attribution_report_shape,
    verify_calibrated_attribution_report,
)
from rdllm.context_closure import (
    derive_generation_context_blocks,
    make_generation_context_closure_report,
    validate_generation_context_closure_report_shape,
    verify_generation_context_closure_report,
)
from rdllm.decision_provenance import (
    make_decision_provenance_report,
    validate_decision_provenance_report_shape,
    verify_decision_provenance_report,
)
from rdllm.source_boundary import (
    make_source_boundary_report,
    validate_source_boundary_report_shape,
    verify_source_boundary_report,
)
from rdllm.attribution_gap import (
    evaluate_attribution_gap,
    evaluate_event_attribution_gap,
    verify_attribution_gap_report,
)
from rdllm.attribution_capsule import (
    make_attribution_capsule,
    validate_attribution_capsule_shape,
    verify_attribution_capsule,
)
from rdllm.attribution_consensus import (
    make_attribution_consensus_report,
    validate_attribution_consensus_report_shape,
    verify_attribution_consensus_report,
)
from rdllm.verifier_quorum import (
    make_verifier_quorum_report,
    validate_verifier_quorum_report_shape,
    verify_verifier_quorum_report,
)
from rdllm.verifier_accountability import (
    make_verifier_accountability_report,
    validate_verifier_accountability_report_shape,
    verify_verifier_accountability_report,
)
from rdllm.receipt_transparency_consistency import (
    make_receipt_transparency_consistency_report,
    validate_receipt_transparency_consistency_report_shape,
    verify_receipt_transparency_consistency_report,
)
from rdllm.watchtower_challenge_settlement import (
    make_watchtower_challenge_settlement_report,
    validate_watchtower_challenge_settlement_report_shape,
    verify_watchtower_challenge_settlement_report,
)
from rdllm.output_provenance_binding import (
    make_output_provenance_binding_report,
    validate_output_provenance_binding_report_shape,
    verify_output_provenance_binding_report,
)
from rdllm.post_release_discovery import (
    make_post_release_discovery_report,
    validate_post_release_discovery_report_shape,
    verify_post_release_discovery_report,
)
from rdllm.certification import run_certification
from rdllm.certification_attestation import (
    make_certification_attestation,
    validate_certification_attestation_shape,
    verify_certification_attestation,
)
from rdllm.challenges import (
    make_attribution_challenge,
    validate_challenge_shape,
    verify_attribution_challenge,
)
from rdllm.clearinghouse import (
    make_clearinghouse_report,
    validate_clearinghouse_report_shape,
    verify_clearinghouse_report,
)
from rdllm.citation_footer import (
    make_citation_footer_contract,
    validate_citation_footer_contract_shape,
    verify_citation_footer_contract,
)
from rdllm.citation_identity import (
    load_citation_identity_input,
    make_citation_identity_report,
    validate_citation_identity_report_shape,
    verify_citation_identity_report,
)
from rdllm.citation_reliance_receipt import (
    load_citation_reliance_input,
    make_citation_reliance_receipt,
    validate_citation_reliance_receipt_shape,
    verify_citation_reliance_receipt,
)
from rdllm.license_transaction_receipt import (
    load_license_transaction_input,
    make_license_transaction_receipt,
    validate_license_transaction_receipt_shape,
    verify_license_transaction_receipt,
)
from rdllm.grounded_source_footer import (
    load_grounded_source_footer_input,
    make_grounded_source_footer,
    validate_grounded_source_footer_shape,
    verify_grounded_source_footer,
)
from rdllm.source_footer_delivery import (
    load_source_footer_delivery_input,
    make_source_footer_delivery_receipt,
    validate_source_footer_delivery_shape,
    verify_source_footer_delivery_receipt,
)
from rdllm.foundation_api_profile import (
    load_foundation_api_profile_input,
    make_foundation_api_profile,
    validate_foundation_api_profile_shape,
    verify_foundation_api_profile,
)
from rdllm.client_attribution_enforcement import (
    load_client_attribution_input,
    make_client_attribution_enforcement_receipt,
    validate_client_attribution_enforcement_shape,
    verify_client_attribution_enforcement_receipt,
)
from rdllm.persistent_memory_provenance import (
    load_persistent_memory_provenance_input,
    make_persistent_memory_provenance_receipt,
    validate_persistent_memory_provenance_shape,
    verify_persistent_memory_provenance_receipt,
)
from rdllm.private_reasoning_attribution import (
    load_private_reasoning_attribution_input,
    make_private_reasoning_attribution_receipt,
    validate_private_reasoning_attribution_shape,
    verify_private_reasoning_attribution_receipt,
)
from rdllm.post_training_signal_provenance import (
    load_post_training_signal_input,
    make_post_training_signal_provenance_receipt,
    validate_post_training_signal_provenance_shape,
    verify_post_training_signal_provenance_receipt,
)
from rdllm.attribution_bill_of_materials import (
    load_attribution_bom_input,
    make_attribution_bill_of_materials,
    validate_attribution_bill_of_materials_shape,
    verify_attribution_bill_of_materials,
)
from rdllm.creator_attribution_audit_index import (
    load_creator_attribution_audit_index_input,
    make_creator_attribution_audit_index,
    validate_creator_attribution_audit_index_shape,
    verify_creator_attribution_audit_index,
)
from rdllm.creator_attribution_audit_federation import (
    load_creator_attribution_audit_federation_input,
    make_creator_attribution_audit_federation,
    validate_creator_attribution_audit_federation_shape,
    verify_creator_attribution_audit_federation,
)
from rdllm.creator_attribution_audit_federation_transparency import (
    make_creator_audit_federation_transparency_log,
    make_creator_audit_federation_transparency_report,
    validate_creator_audit_federation_transparency_shape,
    verify_creator_audit_federation_transparency_report,
)
from rdllm.creator_audit_transparency_monitor import (
    make_creator_audit_transparency_monitor_report,
    validate_creator_audit_transparency_monitor_shape,
    verify_creator_audit_transparency_monitor_report,
)
from rdllm.creator_audit_private_watch import (
    make_creator_audit_private_watch_report,
    validate_creator_audit_private_watch_shape,
    verify_creator_audit_private_watch_report,
)
from rdllm.deep_research_citation_audit import (
    load_deep_research_citation_audit_input,
    make_deep_research_citation_audit_report,
    validate_deep_research_citation_audit_shape,
    verify_deep_research_citation_audit_report,
)
from rdllm.source_freshness_audit import (
    load_source_freshness_audit_input,
    make_source_freshness_audit_report,
    validate_source_freshness_audit_shape,
    verify_source_freshness_audit_report,
)
from rdllm.royalty_abuse_audit import (
    load_royalty_abuse_audit_input,
    make_royalty_abuse_audit_report,
    validate_royalty_abuse_audit_shape,
    verify_royalty_abuse_audit_report,
)
from rdllm.consent_revocation_propagation import (
    load_consent_revocation_propagation_input,
    make_consent_revocation_propagation_report,
    validate_consent_revocation_propagation_shape,
    verify_consent_revocation_propagation_report,
)
from rdllm.evidence_force_calibration import (
    load_evidence_force_calibration_input,
    make_evidence_force_calibration_report,
    validate_evidence_force_calibration_shape,
    verify_evidence_force_calibration_report,
)
from rdllm.warranted_source_footer import (
    load_warranted_source_footer_input,
    make_warranted_source_footer,
    validate_warranted_source_footer_shape,
    verify_warranted_source_footer,
)
from rdllm.source_origin_lineage import (
    load_source_origin_lineage_input,
    make_source_origin_lineage_report,
    validate_source_origin_lineage_shape,
    verify_source_origin_lineage_report,
)
from rdllm.evidence_preview_footer import (
    load_evidence_preview_footer_input,
    make_evidence_preview_footer,
    validate_evidence_preview_footer_shape,
    verify_evidence_preview_footer,
)
from rdllm.evidence_locator_manifest import (
    load_evidence_locator_manifest_input,
    make_evidence_locator_manifest,
    validate_evidence_locator_manifest_shape,
    verify_evidence_locator_manifest,
)
from rdllm.citation_url_health import (
    load_citation_url_health_input,
    make_citation_url_health_report,
    validate_citation_url_health_shape,
    verify_citation_url_health_report,
)
from rdllm.composite_foundation_adapter import (
    load_composite_foundation_adapter_input,
    make_composite_foundation_adapter_report,
    validate_composite_foundation_adapter_shape,
    verify_composite_foundation_adapter_report,
)
from rdllm.foundation_provider_conformance import (
    load_foundation_provider_conformance_input,
    make_foundation_provider_conformance_report,
    validate_foundation_provider_conformance_shape,
    verify_foundation_provider_conformance_report,
)
from rdllm.foundation_runtime_adapter import (
    load_foundation_runtime_adapter_input,
    make_foundation_runtime_adapter_report,
    validate_foundation_runtime_adapter_shape,
    verify_foundation_runtime_adapter_report,
)
from rdllm.foundation_runtime_router import (
    load_foundation_runtime_router_input,
    make_foundation_runtime_router_report,
    validate_foundation_runtime_router_shape,
    verify_foundation_runtime_router_report,
)
from rdllm.foundation_model_deployment_attestation import (
    load_foundation_model_deployment_attestation_input,
    make_deployment_key_hash,
    make_foundation_model_deployment_attestation_report,
    make_model_deployment_statement,
    validate_foundation_model_deployment_attestation_shape,
    verify_foundation_model_deployment_attestation_report,
)
from rdllm.universal_composition_receipt import (
    load_universal_composition_receipt_input,
    make_universal_composition_receipt,
    validate_universal_composition_receipt_shape,
    verify_universal_composition_receipt,
)
from rdllm.universal_composition_settlement import (
    load_universal_composition_settlement_input,
    make_universal_composition_settlement,
    validate_universal_composition_settlement_shape,
    verify_universal_composition_settlement,
)
from rdllm.universal_foundation_model_contract import (
    load_universal_foundation_model_contract_input,
    make_universal_foundation_model_contract,
    validate_universal_foundation_model_contract_shape,
    verify_universal_foundation_model_contract,
)
from rdllm.universal_invocation_guard import (
    load_universal_invocation_guard_input,
    make_universal_invocation_guard,
    validate_universal_invocation_guard_shape,
    verify_universal_invocation_guard,
)
from rdllm.universal_invocation_coverage import (
    load_universal_invocation_coverage_input,
    make_universal_invocation_coverage,
    validate_universal_invocation_coverage_shape,
    verify_universal_invocation_coverage,
)
from rdllm.universal_invocation_witness import (
    load_universal_invocation_witness_input,
    make_universal_invocation_witness,
    validate_universal_invocation_witness_shape,
    verify_universal_invocation_witness,
)
from rdllm.universal_content_credential import (
    load_universal_content_credential_input,
    make_universal_content_credential,
    validate_universal_content_credential_shape,
    verify_universal_content_credential,
)
from rdllm.universal_rdllm_passport import (
    load_universal_rdllm_passport_input,
    make_universal_rdllm_passport,
    validate_universal_rdllm_passport_shape,
    verify_universal_rdllm_passport,
)
from rdllm.universal_adoption_standard import (
    load_universal_adoption_standard_input,
    make_universal_adoption_standard,
    validate_universal_adoption_standard_shape,
    verify_universal_adoption_standard,
)
from rdllm.universal_interop_test_kit import (
    load_universal_interop_test_kit_input,
    make_universal_interop_test_kit,
    validate_universal_interop_test_kit_shape,
    verify_universal_interop_test_kit,
)
from rdllm.universal_context_provenance_bridge import (
    load_universal_context_provenance_bridge_input,
    make_universal_context_provenance_bridge,
    validate_universal_context_provenance_bridge_shape,
    verify_universal_context_provenance_bridge,
)
from rdllm.universal_citation_verification_contract import (
    load_universal_citation_verification_contract_input,
    make_universal_citation_verification_contract,
    validate_universal_citation_verification_contract_shape,
    verify_universal_citation_verification_contract,
)
from rdllm.universal_grounded_reuse_contract import (
    load_universal_grounded_reuse_contract_input,
    make_universal_grounded_reuse_contract,
    validate_universal_grounded_reuse_contract_shape,
    verify_universal_grounded_reuse_contract,
)
from rdllm.universal_training_serving_contract import (
    load_universal_training_serving_contract_input,
    make_universal_training_serving_contract,
    validate_universal_training_serving_contract_shape,
    verify_universal_training_serving_contract,
)
from rdllm.universal_confidential_attribution_audit import (
    load_universal_confidential_attribution_audit_input,
    make_universal_confidential_attribution_audit,
    validate_universal_confidential_attribution_audit_shape,
    verify_universal_confidential_attribution_audit,
)
from rdllm.universal_attribution_authority_control_plane import (
    load_universal_attribution_authority_control_plane_input,
    make_universal_attribution_authority_control_plane,
    validate_universal_attribution_authority_control_plane_shape,
    verify_universal_attribution_authority_control_plane,
)
from rdllm.universal_rdllm_root import (
    load_universal_rdllm_root_input,
    make_universal_rdllm_root,
    validate_universal_rdllm_root_shape,
    verify_universal_rdllm_root,
)
from rdllm.universal_emission_enforcement_gateway import (
    load_universal_emission_enforcement_gateway_input,
    make_universal_emission_enforcement_gateway,
    validate_universal_emission_enforcement_gateway_shape,
    verify_universal_emission_enforcement_gateway,
)
from rdllm.universal_composite_rdllm_profile import (
    load_universal_composite_rdllm_profile_input,
    make_universal_composite_rdllm_profile,
    validate_universal_composite_rdllm_profile_shape,
    verify_universal_composite_rdllm_profile,
)
from rdllm.universal_runtime_conformance_receipt import (
    load_universal_runtime_conformance_receipt_input,
    make_universal_runtime_conformance_receipt,
    validate_universal_runtime_conformance_receipt_shape,
    verify_universal_runtime_conformance_receipt,
)
from rdllm.universal_claim_provenance_envelope import (
    load_universal_claim_provenance_envelope_input,
    make_universal_claim_provenance_envelope,
    validate_universal_claim_provenance_envelope_shape,
    verify_universal_claim_provenance_envelope,
)
from rdllm.universal_provider_wire_protocol import (
    load_universal_provider_wire_protocol_input,
    make_universal_provider_wire_protocol,
    validate_universal_provider_wire_protocol_shape,
    verify_universal_provider_wire_protocol,
)
from rdllm.universal_accountability_audit_trail import (
    load_universal_accountability_audit_trail_input,
    make_universal_accountability_audit_trail,
    validate_universal_accountability_audit_trail_shape,
    verify_universal_accountability_audit_trail,
)
from rdllm.universal_accountability_witness_quorum import (
    load_universal_accountability_witness_quorum_input,
    make_universal_accountability_witness_quorum,
    validate_universal_accountability_witness_quorum_shape,
    verify_universal_accountability_witness_quorum,
)
from rdllm.universal_grounded_reliance_contract import (
    load_universal_grounded_reliance_contract_input,
    make_universal_grounded_reliance_contract,
    validate_universal_grounded_reliance_contract_shape,
    verify_universal_grounded_reliance_contract,
)
from rdllm.universal_reliance_correction_ledger import (
    load_universal_reliance_correction_ledger_input,
    make_universal_reliance_correction_ledger,
    validate_universal_reliance_correction_ledger_shape,
    verify_universal_reliance_correction_ledger,
)
from rdllm.universal_foundation_adoption_kernel import (
    load_universal_foundation_adoption_kernel_input,
    make_universal_foundation_adoption_kernel,
    validate_universal_foundation_adoption_kernel_shape,
    verify_universal_foundation_adoption_kernel,
)
from rdllm.universal_provider_adapter_harness import (
    load_universal_provider_adapter_harness_input,
    make_universal_provider_adapter_harness,
    validate_universal_provider_adapter_harness_shape,
    verify_universal_provider_adapter_harness,
)
from rdllm.universal_provider_drift_sentinel import (
    load_universal_provider_drift_sentinel_input,
    make_universal_provider_drift_sentinel,
    validate_universal_provider_drift_sentinel_shape,
    verify_universal_provider_drift_sentinel,
)
from rdllm.universal_attribution_negotiation_handshake import (
    load_universal_attribution_negotiation_handshake_input,
    make_universal_attribution_negotiation_handshake,
    validate_universal_attribution_negotiation_handshake_shape,
    verify_universal_attribution_negotiation_handshake,
)
from rdllm.universal_negotiated_invocation_enforcement import (
    load_universal_negotiated_invocation_enforcement_input,
    make_universal_negotiated_invocation_enforcement,
    validate_universal_negotiated_invocation_enforcement_shape,
    verify_universal_negotiated_invocation_enforcement,
)
from rdllm.universal_certification_trust_federation import (
    load_universal_certification_trust_federation_input,
    make_universal_certification_trust_federation,
    validate_universal_certification_trust_federation_shape,
    verify_universal_certification_trust_federation,
)
from rdllm.universal_foundation_provider_adoption_pack import (
    load_universal_foundation_provider_adoption_pack_input,
    make_universal_foundation_provider_adoption_pack,
    validate_universal_foundation_provider_adoption_pack_shape,
    verify_universal_foundation_provider_adoption_pack,
)
from rdllm.universal_industry_adoption_root import (
    load_universal_industry_adoption_root_input,
    make_universal_industry_adoption_root,
    validate_universal_industry_adoption_root_shape,
    verify_universal_industry_adoption_root,
)
from rdllm.universal_reference_implementation_distribution import (
    load_universal_reference_implementation_distribution_input,
    make_universal_reference_implementation_distribution,
    validate_universal_reference_implementation_distribution_shape,
    verify_universal_reference_implementation_distribution,
)
from rdllm.universal_live_attribution_proof import (
    load_universal_live_attribution_proof_input,
    make_universal_live_attribution_proof,
    validate_universal_live_attribution_proof_shape,
    verify_universal_live_attribution_proof,
)
from rdllm.universal_foundation_model_release_passport import (
    load_universal_foundation_model_release_passport_input,
    make_universal_foundation_model_release_passport,
    validate_universal_foundation_model_release_passport_shape,
    verify_universal_foundation_model_release_passport,
)
from rdllm.universal_composite_rdllm_contract import (
    load_universal_composite_rdllm_contract_input,
    make_universal_composite_rdllm_contract,
    validate_universal_composite_rdllm_contract_shape,
    verify_universal_composite_rdllm_contract,
)
from rdllm.universal_foundation_provider_binding_matrix import (
    load_universal_foundation_provider_binding_matrix_input,
    make_universal_foundation_provider_binding_matrix,
    validate_universal_foundation_provider_binding_matrix_shape,
    verify_universal_foundation_provider_binding_matrix,
)
from rdllm.universal_provider_conformance_runner_receipt import (
    load_universal_provider_conformance_runner_receipt_input,
    make_universal_provider_conformance_runner_receipt,
    validate_universal_provider_conformance_runner_receipt_shape,
    verify_universal_provider_conformance_runner_receipt,
)
from rdllm.universal_production_invocation_admission import (
    load_universal_production_invocation_admission_input,
    make_universal_production_invocation_admission,
    validate_universal_production_invocation_admission_shape,
    verify_universal_production_invocation_admission,
)
from rdllm.universal_source_grounded_response_receipt import (
    load_universal_source_grounded_response_receipt_input,
    make_universal_source_grounded_response_receipt,
    validate_universal_source_grounded_response_receipt_shape,
    verify_universal_source_grounded_response_receipt,
)
from rdllm.universal_distribution_reliance_passport import (
    load_universal_distribution_reliance_passport_input,
    make_universal_distribution_reliance_passport,
    validate_universal_distribution_reliance_passport_shape,
    verify_universal_distribution_reliance_passport,
)
from rdllm.universal_adversarial_provenance_quorum import (
    load_universal_adversarial_provenance_quorum_input,
    make_universal_adversarial_provenance_quorum,
    validate_universal_adversarial_provenance_quorum_shape,
    verify_universal_adversarial_provenance_quorum,
)
from rdllm.universal_procurement_regulatory_reliance_contract import (
    load_universal_procurement_regulatory_reliance_contract_input,
    make_universal_procurement_regulatory_reliance_contract,
    validate_universal_procurement_regulatory_reliance_contract_shape,
    verify_universal_procurement_regulatory_reliance_contract,
)
from rdllm.universal_provider_onboarding_migration_covenant import (
    load_universal_provider_onboarding_migration_covenant_input,
    make_universal_provider_onboarding_migration_covenant,
    validate_universal_provider_onboarding_migration_covenant_shape,
    verify_universal_provider_onboarding_migration_covenant,
)
from rdllm.universal_model_provider_registry import (
    load_universal_model_provider_registry_input,
    make_universal_model_provider_registry,
    validate_universal_model_provider_registry_shape,
    verify_universal_model_provider_registry,
)
from rdllm.universal_source_footer_enforcement_contract import (
    load_universal_source_footer_enforcement_contract_input,
    make_universal_source_footer_enforcement_contract,
    validate_universal_source_footer_enforcement_contract_shape,
    verify_universal_source_footer_enforcement_contract,
)
from rdllm.universal_provider_catalog_coverage_contract import (
    load_universal_provider_catalog_coverage_contract_input,
    make_universal_provider_catalog_coverage_contract,
    validate_universal_provider_catalog_coverage_contract_shape,
    verify_universal_provider_catalog_coverage_contract,
)
from rdllm.universal_runtime_route_binding_contract import (
    load_universal_runtime_route_binding_contract_input,
    make_universal_runtime_route_binding_contract,
    validate_universal_runtime_route_binding_contract_shape,
    verify_universal_runtime_route_binding_contract,
)
from rdllm.universal_verified_source_footer_contract import (
    load_universal_verified_source_footer_contract_input,
    make_universal_verified_source_footer_contract,
    validate_universal_verified_source_footer_contract_shape,
    verify_universal_verified_source_footer_contract,
)
from rdllm.universal_model_capability_coverage_contract import (
    load_universal_model_capability_coverage_contract_input,
    make_universal_model_capability_coverage_contract,
    validate_universal_model_capability_coverage_contract_shape,
    verify_universal_model_capability_coverage_contract,
)
from rdllm.universal_live_capability_discovery_contract import (
    load_universal_live_capability_discovery_contract_input,
    make_universal_live_capability_discovery_contract,
    validate_universal_live_capability_discovery_contract_shape,
    verify_universal_live_capability_discovery_contract,
)
from rdllm.universal_native_source_annotation_contract import (
    load_universal_native_source_annotation_contract_input,
    make_universal_native_source_annotation_contract,
    validate_universal_native_source_annotation_contract_shape,
    verify_universal_native_source_annotation_contract,
)
from rdllm.universal_claim_evidence_footer_verification_contract import (
    load_universal_claim_evidence_footer_verification_contract_input,
    make_universal_claim_evidence_footer_verification_contract,
    validate_universal_claim_evidence_footer_verification_contract_shape,
    verify_universal_claim_evidence_footer_verification_contract,
)
from rdllm.universal_provider_meter_normalization_contract import (
    load_universal_provider_meter_normalization_contract_input,
    make_universal_provider_meter_normalization_contract,
    validate_universal_provider_meter_normalization_contract_shape,
    verify_universal_provider_meter_normalization_contract,
)
from rdllm.universal_provider_response_state_normalization_contract import (
    load_universal_provider_response_state_normalization_contract_input,
    make_universal_provider_response_state_normalization_contract,
    validate_universal_provider_response_state_normalization_contract_shape,
    verify_universal_provider_response_state_normalization_contract,
)
from rdllm.code_attribution import (
    load_code_attribution_inputs,
    make_code_attribution_report,
    validate_code_attribution_report_shape,
    verify_code_attribution_report,
)
from rdllm.claim_verification import (
    load_claim_verification_inputs,
    make_claim_verification_report,
    sign_ownership_attestation,
    validate_claim_verification_report_shape,
    verify_claim_verification_report,
)
from rdllm.claim_source_attribution import (
    load_claim_source_attribution_input,
    make_claim_source_attribution_report,
    validate_claim_source_attribution_report_shape,
    verify_claim_source_attribution_report,
)
from rdllm.evidence_utility_attribution import (
    load_evidence_utility_input,
    make_evidence_utility_attribution_report,
    validate_evidence_utility_attribution_report_shape,
    verify_evidence_utility_attribution_report,
)
from rdllm.parametric_memory_attribution import (
    load_parametric_memory_input,
    make_parametric_memory_attribution_report,
    validate_parametric_memory_attribution_report_shape,
    verify_parametric_memory_attribution_report,
)
from rdllm.style_influence_attribution import (
    load_style_influence_input,
    make_style_influence_attribution_report,
    validate_style_influence_attribution_report_shape,
    verify_style_influence_attribution_report,
)
from rdllm.model_lineage_attribution import (
    load_model_lineage_input,
    make_model_lineage_attribution_report,
    validate_model_lineage_attribution_report_shape,
    verify_model_lineage_attribution_report,
)
from rdllm.black_box_model_provenance import (
    load_black_box_model_provenance_input,
    make_black_box_model_provenance_report,
    validate_black_box_model_provenance_report_shape,
    verify_black_box_model_provenance_report,
)
from rdllm.attribution_dispute_adjudication import (
    load_attribution_dispute_adjudication_input,
    make_attribution_dispute_adjudication_report,
    validate_attribution_dispute_adjudication_report_shape,
    verify_attribution_dispute_adjudication_report,
)
from rdllm.post_adjudication_settlement_adjustment import (
    load_post_adjudication_settlement_adjustment_input,
    make_post_adjudication_settlement_adjustment_report,
    validate_post_adjudication_settlement_adjustment_report_shape,
    verify_post_adjudication_settlement_adjustment_report,
)
from rdllm.residual_corpus_royalty import (
    load_residual_corpus_royalty_input,
    make_residual_corpus_royalty_report,
    validate_residual_corpus_royalty_report_shape,
    verify_residual_corpus_royalty_report,
)
from rdllm.valuation_method_audit import (
    load_valuation_method_audit_input,
    make_valuation_method_audit_report,
    validate_valuation_method_audit_report_shape,
    verify_valuation_method_audit_report,
)
from rdllm.evidence_region_binding import (
    load_evidence_region_binding_input,
    make_evidence_region_binding_report,
    validate_evidence_region_binding_report_shape,
    verify_evidence_region_binding_report,
)
from rdllm.source_access_lease import (
    load_source_access_lease_input,
    make_source_access_lease_report,
    validate_source_access_lease_report_shape,
    verify_source_access_lease_report,
)
from rdllm.content_protocol_ingestion import (
    load_content_protocol_ingestion_input,
    make_content_protocol_ingestion_report,
    validate_content_protocol_ingestion_report_shape,
    verify_content_protocol_ingestion_report,
)
from rdllm.conformance_vectors import (
    make_conformance_vector_pack,
    validate_conformance_vector_pack_shape,
    verify_conformance_vector_pack,
)
from rdllm.disclosure import (
    make_selective_disclosure_package,
    verify_selective_disclosure_package,
)
from rdllm.discovery_manifest import (
    make_discovery_manifest,
    validate_discovery_manifest_shape,
    verify_discovery_manifest,
)
from rdllm.evidence_sufficiency import (
    make_evidence_sufficiency_report,
    validate_evidence_sufficiency_report_shape,
    verify_evidence_sufficiency_report,
)
from rdllm.federation_handshake import (
    make_federation_handshake,
    validate_federation_handshake_shape,
    verify_federation_handshake,
)
from rdllm.finance_ledger import (
    make_finance_ledger_attestation,
    validate_finance_ledger_attestation_shape,
    verify_finance_ledger_attestation,
)
from rdllm.payment_execution import (
    make_payment_execution_report,
    validate_payment_execution_report_shape,
    verify_payment_execution_report,
)
from rdllm.payment_rail import (
    make_payment_rail_attestation,
    make_processor_batch_attestations,
    validate_payment_rail_attestation_shape,
    verify_payment_rail_attestation,
)
from rdllm.creator_payout_receipt import (
    make_creator_payout_receipt_report,
    validate_creator_payout_receipt_report_shape,
    verify_creator_payout_receipt_report,
)
from rdllm.rendered_attribution_audit import (
    make_rendered_attribution_audit,
    validate_rendered_attribution_audit_shape,
    verify_rendered_attribution_audit,
)
from rdllm.training_memory_provenance import (
    load_training_memory_snapshots,
    make_training_memory_provenance_report,
    validate_training_memory_provenance_shape,
    verify_training_memory_provenance_report,
)
from rdllm.evidence_locked_generation import (
    make_evidence_locked_generation_report,
    validate_evidence_locked_generation_shape,
    verify_evidence_locked_generation_report,
)
from rdllm.emission_enforcement import (
    make_emission_evidence_enforcement_report,
    validate_emission_evidence_enforcement_shape,
    verify_emission_evidence_enforcement_report,
)
from rdllm.live_emission_witness import (
    make_live_emission_witness_report,
    validate_live_emission_witness_shape,
    verify_live_emission_witness_report,
)
from rdllm.live_emission_transparency import (
    make_live_emission_transparency_log,
    make_live_emission_transparency_report,
    validate_live_emission_transparency_shape,
    verify_live_emission_transparency_report,
)
from rdllm.attested_runtime import (
    make_attested_runtime_report,
    make_attestor_key_hash,
    make_runtime_attestation_nonce,
    make_runtime_attestation_quote,
    make_runtime_measurement,
    validate_attested_runtime_shape,
    verify_attested_runtime_report,
)
from rdllm.proof_dependency_graph import (
    make_proof_dependency_graph,
    validate_proof_dependency_graph_shape,
    verify_proof_dependency_graph,
)
from rdllm.publication_monitor import (
    make_publication_monitor_report,
    validate_publication_monitor_shape,
    verify_publication_monitor_report,
)
from rdllm.publication_witness import (
    make_publication_witness_report,
    validate_publication_witness_shape,
    verify_publication_witness_report,
)
from rdllm.trust_registry import (
    make_trust_registry_report,
    validate_trust_registry_shape,
    verify_trust_registry_report,
)
from rdllm.engine import RoyaltyDrivenLLM
from rdllm.grounding import evaluate_event_grounding_quality, evaluate_grounding_quality
from rdllm.interop import (
    make_interop_bundle,
    receipt_credential,
    receipt_prov_graph,
    settlement_credential,
    verify_credential,
    verify_interop_bundle,
    verify_prov_graph,
)
from rdllm.integration_profile import (
    make_integration_profile,
    validate_integration_profile_shape,
    verify_integration_profile,
)
from rdllm.license_contract import (
    make_creator_license_contract,
    validate_creator_license_contract_shape,
    verify_creator_license_contract,
    verify_creator_license_contract_public,
)
from rdllm.ledger import RoyaltyLedger
from rdllm.lineage import (
    make_lineage_report,
    validate_lineage_report_shape,
    verify_lineage_report,
)
from rdllm.media_attribution import (
    load_media_corpus,
    load_media_inputs,
    make_media_attribution_report,
    validate_media_attribution_report_shape,
    verify_media_attribution_report,
)
from rdllm.model_signal import (
    load_model_signal_input,
    make_model_signal_report,
    validate_model_signal_report_shape,
    verify_model_signal_report,
)
from rdllm.pinpoint_provenance import (
    load_pinpoint_provenance_input,
    make_pinpoint_provenance_report,
    validate_pinpoint_provenance_report_shape,
    verify_pinpoint_provenance_report,
)
from rdllm.conformance import verify_conformance_bundle, verify_event_receipt
from rdllm.counterfactual import (
    make_counterfactual_report,
    validate_counterfactual_report_shape,
    verify_counterfactual_report,
)
from rdllm.counterevidence import (
    make_counterevidence_report,
    validate_counterevidence_report_shape,
    verify_counterevidence_report,
)
from rdllm.models import (
    ClaimSupport,
    Creator,
    RoyaltyShare,
    SourceAccess,
    SourceReference,
    TextMatch,
    UsageEvent,
    Work,
)
from rdllm.policy import PolicyDecision, RightsPolicyEngine
from rdllm.private_audit import (
    make_private_audit_challenge_report,
    validate_private_audit_challenge_shape,
    verify_private_audit_challenge_report,
)
from rdllm.provider_card import (
    make_provider_attribution_card,
    validate_provider_card_shape,
    verify_provider_attribution_card,
)
from rdllm.proof_carrying_response import (
    make_proof_carrying_response,
    validate_proof_carrying_response_shape,
    verify_proof_carrying_response,
)
from rdllm.serving_gateway import (
    make_serving_gateway_report,
    validate_serving_gateway_report_shape,
    verify_serving_gateway_report,
)
from rdllm.streaming_attribution import (
    make_streaming_attribution_manifest,
    validate_streaming_attribution_manifest_shape,
    verify_streaming_attribution_manifest,
)
from rdllm.conversation_attribution import (
    make_conversation_attribution_ledger,
    validate_conversation_attribution_ledger_shape,
    verify_conversation_attribution_ledger,
)
from rdllm.agent_tool_attribution import (
    make_agent_tool_attribution_ledger,
    validate_agent_tool_attribution_ledger_shape,
    verify_agent_tool_attribution_ledger,
)
from rdllm.provenance_eval import (
    load_provenance_benchmark,
    make_provenance_evaluation_report,
    validate_provenance_evaluation_shape,
    verify_provenance_evaluation_report,
)
from rdllm.registry import (
    OwnershipAttestation,
    RegistryConflict,
    registry_report_for_works,
)
from rdllm.receipts import (
    make_attribution_receipt,
    public_receipt,
    validate_receipt_shape,
    verify_receipt,
)
from rdllm.response_envelope import (
    make_response_envelope,
    validate_response_envelope_shape,
    verify_response_envelope,
)
from rdllm.revenue_allocation import (
    make_revenue_allocation_report,
    validate_revenue_allocation_report_shape,
    verify_revenue_allocation_report,
)
from rdllm.remittance import (
    make_remittance_report,
    validate_remittance_report_shape,
    verify_remittance_report,
)
from rdllm.release_gate import (
    make_release_gate_report,
    validate_release_gate_shape,
    verify_release_gate_report,
)
from rdllm.rights_remediation import (
    load_ledger,
    make_rights_remediation_report,
    validate_rights_remediation_report_shape,
    verify_rights_remediation_report,
)
from rdllm.semantic_text_attribution import (
    load_semantic_text_inputs,
    make_semantic_text_attribution_report,
    validate_semantic_text_attribution_report_shape,
    verify_semantic_text_attribution_report,
)
from rdllm.settlement import (
    DisputeResolution,
    resolve_registry_escrow,
    verify_escrow_resolution,
)
from rdllm.source_verification import (
    make_source_verification_report,
    validate_source_verification_report_shape,
    verify_source_verification_report,
)
from rdllm.source_confidence import (
    make_source_confidence_report,
    validate_source_confidence_report_shape,
    verify_source_confidence_report,
)
from rdllm.source_availability import (
    load_source_availability_snapshots,
    make_source_availability_report,
    validate_source_availability_report_shape,
    verify_source_availability_report,
)
from rdllm.source_authenticity import (
    load_source_authenticity_signals,
    make_source_authenticity_report,
    validate_source_authenticity_report_shape,
    verify_source_authenticity_report,
)
from rdllm.statements import (
    make_royalty_statement,
    statement_summary,
    verify_royalty_statement,
)
from rdllm.telemetry import make_trace_exchange, verify_trace_exchange
from rdllm.training_summary import (
    make_training_content_summary,
    validate_training_summary_shape,
    verify_training_content_summary,
)
from rdllm.transitive_attribution import (
    make_transitive_attribution_report,
    validate_transitive_attribution_report_shape,
    verify_transitive_attribution_report,
)
from rdllm.transparency import TransparencyLog, verify_inclusion

__all__ = [
    "ClaimSupport",
    "Creator",
    "DisputeResolution",
    "RoyaltyDrivenLLM",
    "RoyaltyLedger",
    "RoyaltyShare",
    "OwnershipAttestation",
    "PolicyDecision",
    "RegistryConflict",
    "RightsPolicyEngine",
    "SourceAccess",
    "SourceReference",
    "TextMatch",
    "TransparencyLog",
    "UsageEvent",
    "Work",
    "evaluate_attribution_gap",
    "evaluate_event_attribution_gap",
    "evaluate_event_grounding_quality",
    "evaluate_grounding_quality",
    "make_attribution_challenge",
    "make_attribution_capsule",
    "make_attribution_consensus_report",
    "make_assurance_bundle",
    "make_audit_attestation",
    "make_answer_provenance_card",
    "make_agent_tool_attribution_ledger",
    "make_attribution_exchange_manifest",
    "make_clearinghouse_report",
    "make_claim_verification_report",
    "make_claim_source_attribution_report",
    "make_evidence_utility_attribution_report",
    "make_code_attribution_report",
    "make_citation_footer_contract",
    "make_citation_identity_report",
    "make_counterfactual_report",
    "make_counterevidence_report",
    "make_calibrated_attribution_report",
    "make_conversation_attribution_ledger",
    "make_decision_provenance_report",
    "make_generation_context_closure_report",
    "make_source_boundary_report",
    "make_conformance_vector_pack",
    "make_discovery_manifest",
    "make_evidence_sufficiency_report",
    "make_federation_handshake",
    "make_finance_ledger_attestation",
    "make_interop_bundle",
    "make_integration_profile",
    "make_creator_license_contract",
    "make_lineage_report",
    "make_media_attribution_report",
    "make_model_signal_report",
    "make_output_provenance_binding_report",
    "make_payment_execution_report",
    "make_payment_rail_attestation",
    "make_creator_payout_receipt_report",
    "make_rendered_attribution_audit",
    "make_training_memory_provenance_report",
    "make_evidence_locked_generation_report",
    "make_emission_evidence_enforcement_report",
    "make_live_emission_witness_report",
    "make_live_emission_transparency_log",
    "make_live_emission_transparency_report",
    "make_attested_runtime_report",
    "make_attestor_key_hash",
    "make_runtime_attestation_nonce",
    "make_runtime_attestation_quote",
    "make_runtime_measurement",
    "make_processor_batch_attestations",
    "make_pinpoint_provenance_report",
    "make_post_release_discovery_report",
    "make_attribution_receipt",
    "make_provider_attribution_card",
    "make_private_audit_challenge_report",
    "make_proof_carrying_response",
    "make_proof_dependency_graph",
    "make_publication_monitor_report",
    "make_publication_witness_report",
    "make_residual_corpus_royalty_report",
    "make_valuation_method_audit_report",
    "make_evidence_region_binding_report",
    "make_source_access_lease_report",
    "make_content_protocol_ingestion_report",
    "make_citation_reliance_receipt",
    "make_license_transaction_receipt",
    "make_grounded_source_footer",
    "make_source_footer_delivery_receipt",
    "make_foundation_api_profile",
    "make_client_attribution_enforcement_receipt",
    "make_persistent_memory_provenance_receipt",
    "make_private_reasoning_attribution_receipt",
    "make_post_training_signal_provenance_receipt",
    "make_attribution_bill_of_materials",
    "make_creator_attribution_audit_index",
    "make_creator_attribution_audit_federation",
    "make_creator_audit_federation_transparency_log",
    "make_creator_audit_federation_transparency_report",
    "make_creator_audit_transparency_monitor_report",
    "make_creator_audit_private_watch_report",
    "make_deep_research_citation_audit_report",
    "make_source_freshness_audit_report",
    "make_royalty_abuse_audit_report",
    "make_consent_revocation_propagation_report",
    "make_evidence_force_calibration_report",
    "make_warranted_source_footer",
    "make_source_origin_lineage_report",
    "make_evidence_preview_footer",
    "make_evidence_locator_manifest",
    "make_citation_url_health_report",
    "make_composite_foundation_adapter_report",
    "make_foundation_provider_conformance_report",
    "make_foundation_runtime_adapter_report",
    "make_foundation_runtime_router_report",
    "make_foundation_model_deployment_attestation_report",
    "make_universal_composition_receipt",
    "make_universal_composition_settlement",
    "make_universal_foundation_model_contract",
    "make_universal_invocation_guard",
    "make_universal_invocation_coverage",
    "make_universal_invocation_witness",
    "make_universal_content_credential",
    "make_universal_rdllm_passport",
    "make_universal_adoption_standard",
    "make_universal_interop_test_kit",
    "make_universal_context_provenance_bridge",
    "make_universal_citation_verification_contract",
    "make_universal_grounded_reuse_contract",
    "make_universal_training_serving_contract",
    "make_universal_confidential_attribution_audit",
    "make_universal_attribution_authority_control_plane",
    "make_universal_rdllm_root",
    "make_universal_emission_enforcement_gateway",
    "make_universal_composite_rdllm_profile",
    "make_universal_runtime_conformance_receipt",
    "make_universal_claim_provenance_envelope",
    "make_universal_provider_wire_protocol",
    "make_universal_accountability_audit_trail",
    "make_universal_accountability_witness_quorum",
    "make_universal_grounded_reliance_contract",
    "make_universal_reliance_correction_ledger",
    "make_universal_foundation_adoption_kernel",
    "make_universal_provider_adapter_harness",
    "make_universal_provider_drift_sentinel",
    "make_universal_attribution_negotiation_handshake",
    "make_universal_negotiated_invocation_enforcement",
    "make_universal_certification_trust_federation",
    "make_universal_foundation_provider_adoption_pack",
    "make_universal_industry_adoption_root",
    "make_universal_reference_implementation_distribution",
    "make_universal_live_attribution_proof",
    "make_universal_foundation_model_release_passport",
    "make_universal_composite_rdllm_contract",
    "make_universal_foundation_provider_binding_matrix",
    "make_universal_provider_conformance_runner_receipt",
    "make_universal_production_invocation_admission",
    "make_universal_source_grounded_response_receipt",
    "make_universal_distribution_reliance_passport",
    "make_universal_adversarial_provenance_quorum",
    "make_universal_procurement_regulatory_reliance_contract",
    "make_universal_provider_onboarding_migration_covenant",
    "make_universal_model_provider_registry",
    "make_universal_source_footer_enforcement_contract",
    "make_universal_provider_catalog_coverage_contract",
    "make_universal_runtime_route_binding_contract",
    "make_universal_verified_source_footer_contract",
    "make_universal_model_capability_coverage_contract",
    "make_universal_live_capability_discovery_contract",
    "make_universal_native_source_annotation_contract",
    "make_universal_claim_evidence_footer_verification_contract",
    "make_universal_provider_meter_normalization_contract",
    "make_universal_provider_response_state_normalization_contract",
    "make_model_deployment_statement",
    "make_deployment_key_hash",
    "make_trust_registry_report",
    "make_provenance_evaluation_report",
    "make_remittance_report",
    "make_receipt_transparency_consistency_report",
    "make_release_gate_report",
    "make_response_envelope",
    "make_revenue_allocation_report",
    "make_rights_remediation_report",
    "make_semantic_text_attribution_report",
    "make_style_influence_attribution_report",
    "make_model_lineage_attribution_report",
    "make_black_box_model_provenance_report",
    "make_serving_gateway_report",
    "make_streaming_attribution_manifest",
    "make_selective_disclosure_package",
    "make_royalty_statement",
    "make_source_verification_report",
    "make_source_confidence_report",
    "make_source_availability_report",
    "make_source_authenticity_report",
    "make_trace_exchange",
    "make_training_content_summary",
    "make_transitive_attribution_report",
    "make_verifier_accountability_report",
    "public_receipt",
    "receipt_credential",
    "receipt_prov_graph",
    "registry_report_for_works",
    "resolve_registry_escrow",
    "run_certification",
    "settlement_credential",
    "sign_ownership_attestation",
    "statement_summary",
    "validate_receipt_shape",
    "validate_release_gate_shape",
    "validate_response_envelope_shape",
    "validate_rights_remediation_report_shape",
    "validate_semantic_text_attribution_report_shape",
    "validate_style_influence_attribution_report_shape",
    "validate_model_lineage_attribution_report_shape",
    "validate_black_box_model_provenance_report_shape",
    "validate_challenge_shape",
    "validate_claim_verification_report_shape",
    "validate_claim_source_attribution_report_shape",
    "validate_creator_audit_private_watch_shape",
    "validate_deep_research_citation_audit_shape",
    "validate_source_freshness_audit_shape",
    "validate_royalty_abuse_audit_shape",
    "validate_consent_revocation_propagation_shape",
    "validate_evidence_force_calibration_shape",
    "validate_warranted_source_footer_shape",
    "validate_source_origin_lineage_shape",
    "validate_evidence_preview_footer_shape",
    "validate_evidence_locator_manifest_shape",
    "validate_citation_url_health_shape",
    "validate_composite_foundation_adapter_shape",
    "validate_foundation_provider_conformance_shape",
    "validate_foundation_runtime_adapter_shape",
    "validate_foundation_runtime_router_shape",
    "validate_foundation_model_deployment_attestation_shape",
    "validate_universal_composition_receipt_shape",
    "validate_universal_composition_settlement_shape",
    "validate_universal_foundation_model_contract_shape",
    "validate_universal_invocation_guard_shape",
    "validate_universal_invocation_coverage_shape",
    "validate_universal_invocation_witness_shape",
    "validate_universal_content_credential_shape",
    "validate_universal_rdllm_passport_shape",
    "validate_universal_adoption_standard_shape",
    "validate_universal_interop_test_kit_shape",
    "validate_universal_context_provenance_bridge_shape",
    "validate_universal_citation_verification_contract_shape",
    "validate_universal_grounded_reuse_contract_shape",
    "validate_universal_training_serving_contract_shape",
    "validate_universal_confidential_attribution_audit_shape",
    "validate_universal_attribution_authority_control_plane_shape",
    "validate_universal_rdllm_root_shape",
    "validate_universal_emission_enforcement_gateway_shape",
    "validate_universal_composite_rdllm_profile_shape",
    "validate_universal_runtime_conformance_receipt_shape",
    "validate_universal_claim_provenance_envelope_shape",
    "validate_universal_provider_wire_protocol_shape",
    "validate_universal_accountability_audit_trail_shape",
    "validate_universal_accountability_witness_quorum_shape",
    "validate_universal_grounded_reliance_contract_shape",
    "validate_universal_reliance_correction_ledger_shape",
    "validate_universal_foundation_adoption_kernel_shape",
    "validate_universal_provider_adapter_harness_shape",
    "validate_universal_provider_drift_sentinel_shape",
    "validate_universal_attribution_negotiation_handshake_shape",
    "validate_universal_negotiated_invocation_enforcement_shape",
    "validate_universal_certification_trust_federation_shape",
    "validate_universal_foundation_provider_adoption_pack_shape",
    "validate_universal_industry_adoption_root_shape",
    "validate_universal_reference_implementation_distribution_shape",
    "validate_universal_live_attribution_proof_shape",
    "validate_universal_foundation_model_release_passport_shape",
    "validate_universal_composite_rdllm_contract_shape",
    "validate_universal_foundation_provider_binding_matrix_shape",
    "validate_universal_provider_conformance_runner_receipt_shape",
    "validate_universal_production_invocation_admission_shape",
    "validate_universal_source_grounded_response_receipt_shape",
    "validate_universal_distribution_reliance_passport_shape",
    "validate_universal_adversarial_provenance_quorum_shape",
    "validate_universal_procurement_regulatory_reliance_contract_shape",
    "validate_universal_provider_onboarding_migration_covenant_shape",
    "validate_universal_model_provider_registry_shape",
    "validate_universal_source_footer_enforcement_contract_shape",
    "validate_universal_provider_catalog_coverage_contract_shape",
    "validate_universal_runtime_route_binding_contract_shape",
    "validate_universal_verified_source_footer_contract_shape",
    "validate_universal_model_capability_coverage_contract_shape",
    "validate_universal_live_capability_discovery_contract_shape",
    "validate_universal_native_source_annotation_contract_shape",
    "validate_universal_claim_evidence_footer_verification_contract_shape",
    "validate_universal_provider_meter_normalization_contract_shape",
    "validate_universal_provider_response_state_normalization_contract_shape",
    "validate_creator_audit_transparency_monitor_shape",
    "validate_evidence_utility_attribution_report_shape",
    "validate_clearinghouse_report_shape",
    "validate_citation_footer_contract_shape",
    "validate_citation_identity_report_shape",
    "validate_code_attribution_report_shape",
    "validate_assurance_bundle_shape",
    "validate_audit_attestation_shape",
    "validate_answer_provenance_card_shape",
    "validate_agent_tool_attribution_ledger_shape",
    "validate_attribution_exchange_shape",
    "validate_attribution_capsule_shape",
    "validate_attribution_consensus_report_shape",
    "validate_conformance_vector_pack_shape",
    "validate_conversation_attribution_ledger_shape",
    "validate_counterfactual_report_shape",
    "validate_counterevidence_report_shape",
    "validate_calibrated_attribution_report_shape",
    "validate_decision_provenance_report_shape",
    "validate_generation_context_closure_report_shape",
    "validate_source_boundary_report_shape",
    "validate_discovery_manifest_shape",
    "validate_evidence_sufficiency_report_shape",
    "validate_federation_handshake_shape",
    "validate_finance_ledger_attestation_shape",
    "validate_payment_execution_report_shape",
    "validate_payment_rail_attestation_shape",
    "validate_creator_payout_receipt_report_shape",
    "validate_rendered_attribution_audit_shape",
    "validate_training_memory_provenance_shape",
    "validate_evidence_locked_generation_shape",
    "validate_emission_evidence_enforcement_shape",
    "validate_live_emission_witness_shape",
    "validate_live_emission_transparency_shape",
    "validate_attested_runtime_shape",
    "validate_provider_card_shape",
    "validate_private_audit_challenge_shape",
    "validate_proof_carrying_response_shape",
    "validate_proof_dependency_graph_shape",
    "validate_publication_monitor_shape",
    "validate_publication_witness_shape",
    "validate_residual_corpus_royalty_report_shape",
    "validate_valuation_method_audit_report_shape",
    "validate_evidence_region_binding_report_shape",
    "validate_source_access_lease_report_shape",
    "validate_content_protocol_ingestion_report_shape",
    "validate_citation_reliance_receipt_shape",
    "validate_license_transaction_receipt_shape",
    "validate_grounded_source_footer_shape",
    "validate_source_footer_delivery_shape",
    "validate_foundation_api_profile_shape",
    "validate_client_attribution_enforcement_shape",
    "validate_persistent_memory_provenance_shape",
    "validate_private_reasoning_attribution_shape",
    "validate_post_training_signal_provenance_shape",
    "validate_attribution_bill_of_materials_shape",
    "validate_creator_attribution_audit_index_shape",
    "validate_creator_attribution_audit_federation_shape",
    "validate_creator_audit_federation_transparency_shape",
    "validate_trust_registry_shape",
    "validate_provenance_evaluation_shape",
    "validate_remittance_report_shape",
    "validate_receipt_transparency_consistency_report_shape",
    "validate_serving_gateway_report_shape",
    "validate_streaming_attribution_manifest_shape",
    "validate_training_summary_shape",
    "validate_transitive_attribution_report_shape",
    "validate_verifier_accountability_report_shape",
    "validate_source_verification_report_shape",
    "validate_source_confidence_report_shape",
    "validate_source_availability_report_shape",
    "validate_source_authenticity_report_shape",
    "validate_integration_profile_shape",
    "validate_creator_license_contract_shape",
    "validate_lineage_report_shape",
    "validate_media_attribution_report_shape",
    "validate_model_signal_report_shape",
    "validate_output_provenance_binding_report_shape",
    "validate_pinpoint_provenance_report_shape",
    "validate_post_release_discovery_report_shape",
    "validate_revenue_allocation_report_shape",
    "verify_attribution_gap_report",
    "verify_assurance_bundle",
    "verify_audit_attestation",
    "verify_answer_provenance_card",
    "verify_agent_tool_attribution_ledger",
    "verify_attribution_exchange_manifest",
    "verify_attribution_capsule",
    "verify_attribution_consensus_report",
    "verify_attribution_challenge",
    "verify_claim_verification_report",
    "verify_claim_source_attribution_report",
    "verify_evidence_utility_attribution_report",
    "verify_clearinghouse_report",
    "verify_citation_footer_contract",
    "verify_citation_identity_report",
    "verify_code_attribution_report",
    "verify_conformance_bundle",
    "verify_conformance_vector_pack",
    "verify_conversation_attribution_ledger",
    "verify_counterfactual_report",
    "verify_counterevidence_report",
    "verify_calibrated_attribution_report",
    "verify_decision_provenance_report",
    "verify_generation_context_closure_report",
    "verify_source_boundary_report",
    "verify_credential",
    "verify_discovery_manifest",
    "verify_evidence_sufficiency_report",
    "verify_federation_handshake",
    "verify_finance_ledger_attestation",
    "verify_event_receipt",
    "verify_escrow_resolution",
    "verify_inclusion",
    "verify_interop_bundle",
    "verify_payment_execution_report",
    "verify_payment_rail_attestation",
    "verify_creator_payout_receipt_report",
    "verify_rendered_attribution_audit",
    "verify_training_memory_provenance_report",
    "verify_evidence_locked_generation_report",
    "verify_emission_evidence_enforcement_report",
    "verify_live_emission_witness_report",
    "verify_live_emission_transparency_report",
    "verify_attested_runtime_report",
    "verify_creator_license_contract",
    "verify_creator_license_contract_public",
    "verify_integration_profile",
    "verify_lineage_report",
    "verify_media_attribution_report",
    "verify_model_signal_report",
    "verify_output_provenance_binding_report",
    "verify_pinpoint_provenance_report",
    "verify_post_release_discovery_report",
    "verify_prov_graph",
    "verify_provider_attribution_card",
    "verify_private_audit_challenge_report",
    "verify_proof_carrying_response",
    "verify_proof_dependency_graph",
    "verify_publication_monitor_report",
    "verify_publication_witness_report",
    "verify_residual_corpus_royalty_report",
    "verify_valuation_method_audit_report",
    "verify_evidence_region_binding_report",
    "verify_source_access_lease_report",
    "verify_content_protocol_ingestion_report",
    "verify_citation_reliance_receipt",
    "verify_license_transaction_receipt",
    "verify_grounded_source_footer",
    "verify_source_footer_delivery_receipt",
    "verify_foundation_api_profile",
    "verify_client_attribution_enforcement_receipt",
    "verify_persistent_memory_provenance_receipt",
    "verify_private_reasoning_attribution_receipt",
    "verify_post_training_signal_provenance_receipt",
    "verify_attribution_bill_of_materials",
    "verify_creator_attribution_audit_index",
    "verify_creator_attribution_audit_federation",
    "verify_creator_audit_federation_transparency_report",
    "verify_creator_audit_transparency_monitor_report",
    "verify_creator_audit_private_watch_report",
    "verify_deep_research_citation_audit_report",
    "verify_source_freshness_audit_report",
    "verify_royalty_abuse_audit_report",
    "verify_consent_revocation_propagation_report",
    "verify_evidence_force_calibration_report",
    "verify_warranted_source_footer",
    "verify_source_origin_lineage_report",
    "verify_evidence_preview_footer",
    "verify_evidence_locator_manifest",
    "verify_citation_url_health_report",
    "verify_composite_foundation_adapter_report",
    "verify_foundation_provider_conformance_report",
    "verify_foundation_runtime_adapter_report",
    "verify_foundation_runtime_router_report",
    "verify_foundation_model_deployment_attestation_report",
    "verify_universal_composition_receipt",
    "verify_universal_composition_settlement",
    "verify_universal_foundation_model_contract",
    "verify_universal_invocation_guard",
    "verify_universal_invocation_coverage",
    "verify_universal_invocation_witness",
    "verify_universal_content_credential",
    "verify_universal_rdllm_passport",
    "verify_universal_adoption_standard",
    "verify_universal_interop_test_kit",
    "verify_universal_context_provenance_bridge",
    "verify_universal_citation_verification_contract",
    "verify_universal_grounded_reuse_contract",
    "verify_universal_training_serving_contract",
    "verify_universal_confidential_attribution_audit",
    "verify_universal_attribution_authority_control_plane",
    "verify_universal_rdllm_root",
    "verify_universal_emission_enforcement_gateway",
    "verify_universal_composite_rdllm_profile",
    "verify_universal_runtime_conformance_receipt",
    "verify_universal_claim_provenance_envelope",
    "verify_universal_provider_wire_protocol",
    "verify_universal_accountability_audit_trail",
    "verify_universal_accountability_witness_quorum",
    "verify_universal_grounded_reliance_contract",
    "verify_universal_reliance_correction_ledger",
    "verify_universal_foundation_adoption_kernel",
    "verify_universal_provider_adapter_harness",
    "verify_universal_provider_drift_sentinel",
    "verify_universal_attribution_negotiation_handshake",
    "verify_universal_negotiated_invocation_enforcement",
    "verify_universal_certification_trust_federation",
    "verify_universal_foundation_provider_adoption_pack",
    "verify_universal_industry_adoption_root",
    "verify_universal_reference_implementation_distribution",
    "verify_universal_live_attribution_proof",
    "verify_universal_foundation_model_release_passport",
    "verify_universal_composite_rdllm_contract",
    "verify_universal_foundation_provider_binding_matrix",
    "verify_universal_provider_conformance_runner_receipt",
    "verify_universal_production_invocation_admission",
    "verify_universal_source_grounded_response_receipt",
    "verify_universal_distribution_reliance_passport",
    "verify_universal_adversarial_provenance_quorum",
    "verify_universal_procurement_regulatory_reliance_contract",
    "verify_universal_provider_onboarding_migration_covenant",
    "verify_universal_model_provider_registry",
    "verify_universal_source_footer_enforcement_contract",
    "verify_universal_provider_catalog_coverage_contract",
    "verify_universal_runtime_route_binding_contract",
    "verify_universal_verified_source_footer_contract",
    "verify_universal_model_capability_coverage_contract",
    "verify_universal_live_capability_discovery_contract",
    "verify_universal_native_source_annotation_contract",
    "verify_universal_claim_evidence_footer_verification_contract",
    "verify_universal_provider_meter_normalization_contract",
    "verify_universal_provider_response_state_normalization_contract",
    "verify_trust_registry_report",
    "verify_provenance_evaluation_report",
    "verify_receipt",
    "verify_remittance_report",
    "verify_receipt_transparency_consistency_report",
    "verify_release_gate_report",
    "verify_response_envelope",
    "verify_revenue_allocation_report",
    "verify_rights_remediation_report",
    "verify_semantic_text_attribution_report",
    "verify_style_influence_attribution_report",
    "verify_model_lineage_attribution_report",
    "verify_black_box_model_provenance_report",
    "verify_serving_gateway_report",
    "verify_streaming_attribution_manifest",
    "verify_selective_disclosure_package",
    "verify_source_verification_report",
    "verify_source_confidence_report",
    "verify_source_availability_report",
    "verify_source_authenticity_report",
    "verify_royalty_statement",
    "verify_trace_exchange",
    "verify_training_content_summary",
    "verify_transitive_attribution_report",
    "verify_verifier_accountability_report",
    "load_provenance_benchmark",
    "load_media_corpus",
    "load_media_inputs",
    "load_claim_verification_inputs",
    "load_claim_source_attribution_input",
    "load_evidence_utility_input",
    "load_source_availability_snapshots",
    "load_source_authenticity_signals",
    "load_model_signal_input",
    "load_pinpoint_provenance_input",
    "load_citation_identity_input",
    "load_ledger",
    "load_semantic_text_inputs",
    "load_style_influence_input",
    "load_model_lineage_input",
    "load_black_box_model_provenance_input",
    "load_code_attribution_inputs",
    "load_training_memory_snapshots",
    "load_residual_corpus_royalty_input",
    "load_valuation_method_audit_input",
    "load_evidence_region_binding_input",
    "load_source_access_lease_input",
    "load_content_protocol_ingestion_input",
    "load_citation_reliance_input",
    "load_license_transaction_input",
    "load_grounded_source_footer_input",
    "load_source_footer_delivery_input",
    "load_foundation_api_profile_input",
    "load_client_attribution_input",
    "load_persistent_memory_provenance_input",
    "load_private_reasoning_attribution_input",
    "load_post_training_signal_input",
    "load_attribution_bom_input",
    "load_creator_attribution_audit_index_input",
    "load_creator_attribution_audit_federation_input",
    "load_deep_research_citation_audit_input",
    "load_source_freshness_audit_input",
    "load_royalty_abuse_audit_input",
    "load_consent_revocation_propagation_input",
    "load_evidence_force_calibration_input",
    "load_warranted_source_footer_input",
    "load_source_origin_lineage_input",
    "load_evidence_preview_footer_input",
    "load_evidence_locator_manifest_input",
    "load_citation_url_health_input",
    "load_composite_foundation_adapter_input",
    "load_foundation_provider_conformance_input",
    "load_foundation_runtime_adapter_input",
    "load_foundation_runtime_router_input",
    "load_foundation_model_deployment_attestation_input",
    "load_universal_composition_receipt_input",
    "load_universal_composition_settlement_input",
    "load_universal_foundation_model_contract_input",
    "load_universal_invocation_guard_input",
    "load_universal_invocation_coverage_input",
    "load_universal_invocation_witness_input",
    "load_universal_content_credential_input",
    "load_universal_rdllm_passport_input",
    "load_universal_adoption_standard_input",
    "load_universal_interop_test_kit_input",
    "load_universal_context_provenance_bridge_input",
    "load_universal_citation_verification_contract_input",
    "load_universal_grounded_reuse_contract_input",
    "load_universal_training_serving_contract_input",
    "load_universal_confidential_attribution_audit_input",
    "load_universal_attribution_authority_control_plane_input",
    "load_universal_rdllm_root_input",
    "load_universal_emission_enforcement_gateway_input",
    "load_universal_composite_rdllm_profile_input",
    "load_universal_runtime_conformance_receipt_input",
    "load_universal_claim_provenance_envelope_input",
    "load_universal_provider_wire_protocol_input",
    "load_universal_accountability_audit_trail_input",
    "load_universal_accountability_witness_quorum_input",
    "load_universal_grounded_reliance_contract_input",
    "load_universal_reliance_correction_ledger_input",
    "load_universal_foundation_adoption_kernel_input",
    "load_universal_provider_adapter_harness_input",
    "load_universal_provider_drift_sentinel_input",
    "load_universal_attribution_negotiation_handshake_input",
    "load_universal_negotiated_invocation_enforcement_input",
    "load_universal_certification_trust_federation_input",
    "load_universal_foundation_provider_adoption_pack_input",
    "load_universal_industry_adoption_root_input",
    "load_universal_reference_implementation_distribution_input",
    "load_universal_live_attribution_proof_input",
    "load_universal_foundation_model_release_passport_input",
    "load_universal_composite_rdllm_contract_input",
    "load_universal_foundation_provider_binding_matrix_input",
    "load_universal_provider_conformance_runner_receipt_input",
    "load_universal_production_invocation_admission_input",
    "load_universal_source_grounded_response_receipt_input",
    "load_universal_distribution_reliance_passport_input",
    "load_universal_adversarial_provenance_quorum_input",
    "load_universal_procurement_regulatory_reliance_contract_input",
    "load_universal_provider_onboarding_migration_covenant_input",
    "load_universal_model_provider_registry_input",
    "load_universal_source_footer_enforcement_contract_input",
    "load_universal_provider_catalog_coverage_contract_input",
    "load_universal_runtime_route_binding_contract_input",
    "load_universal_verified_source_footer_contract_input",
    "load_universal_model_capability_coverage_contract_input",
    "load_universal_live_capability_discovery_contract_input",
    "load_universal_native_source_annotation_contract_input",
    "load_universal_claim_evidence_footer_verification_contract_input",
    "load_universal_provider_meter_normalization_contract_input",
    "load_universal_provider_response_state_normalization_contract_input",
    "derive_generation_context_blocks",
]
