"""Well-known discovery manifests for RDLLM provider adoption."""

from __future__ import annotations

from typing import Any

from rdllm.assurance import validate_assurance_bundle_shape
from rdllm.integration_profile import SCHEMA_MAP, verify_integration_profile
from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload

DISCOVERY_MANIFEST_VERSION = "rdllm-discovery-manifest/v1"
DISCOVERY_WELL_KNOWN_PATH = "/.well-known/rdllm.json"

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
    "protocol_ingestion_report_hash",
    "attested_runtime_hash",
    "live_emission_transparency_hash",
    "live_witness_hash",
    "post_release_report_hash",
    "binding_report_hash",
    "watchtower_report_hash",
    "attestation_hash",
    "graph_hash",
    "manifest_hash",
    "conversation_ledger_hash",
    "tool_ledger_hash",
    "streaming_manifest_hash",
    "profile_hash",
    "card_hash",
    "summary_hash",
    "envelope_hash",
    "report_hash",
    "bundle_hash",
    "contract_hash",
    "trace_hash",
    "statement_hash",
    "receipt_hash",
    "event_hash",
)

REQUIRED_ARTIFACTS = (
    "provider_attribution_card",
    "certification_report",
    "integration_profile",
    "response_envelope",
    "assurance_bundle",
)

WELL_KNOWN_PATHS = {
    "provider_attribution_card": "/.well-known/rdllm/provider-attribution-card.json",
    "certification_report": "/.well-known/rdllm/certification-report.json",
    "integration_profile": "/.well-known/rdllm/integration-profile.json",
    "assurance_bundle": "/.well-known/rdllm/assurance-bundle.json",
    "training_content_summary": "/.well-known/rdllm/training-content-summary.json",
    "provenance_evaluation_report": "/.well-known/rdllm/provenance-evaluation-report.json",
    "counterfactual_influence_report": "/.well-known/rdllm/counterfactual-influence-report.json",
    "media_attribution_report": "/.well-known/rdllm/media-attribution-report.json",
    "model_signal_attribution_report": "/.well-known/rdllm/model-signal-attribution-report.json",
    "pinpoint_provenance_report": "/.well-known/rdllm/pinpoint-provenance-report.json",
    "citation_identity_report": "/.well-known/rdllm/citation-identity-report.json",
    "attribution_consensus_report": "/.well-known/rdllm/attribution-consensus-report.json",
    "verifier_quorum_report": "/.well-known/rdllm/verifier-quorum-report.json",
    "verifier_accountability_report": "/.well-known/rdllm/verifier-accountability-report.json",
    "receipt_transparency_consistency_report": "/.well-known/rdllm/receipt-transparency-consistency-report.json",
    "watchtower_challenge_settlement_report": "/.well-known/rdllm/watchtower-challenge-settlement-report.json",
    "output_provenance_binding_report": "/.well-known/rdllm/output-provenance-binding-report.json",
    "post_release_discovery_report": "/.well-known/rdllm/post-release-discovery-report.json",
    "rights_remediation_report": "/.well-known/rdllm/rights-remediation-report.json",
    "semantic_text_attribution_report": "/.well-known/rdllm/semantic-text-attribution-report.json",
    "code_attribution_report": "/.well-known/rdllm/code-attribution-report.json",
    "claim_verification_report": "/.well-known/rdllm/claim-verification-report.json",
    "source_availability_report": "/.well-known/rdllm/source-availability-report.json",
    "evidence_sufficiency_report": "/.well-known/rdllm/evidence-sufficiency-report.json",
    "counterevidence_report": "/.well-known/rdllm/counterevidence-report.json",
    "answer_claim_coverage_report": "/.well-known/rdllm/answer-claim-coverage-report.json",
    "generation_context_closure_report": "/.well-known/rdllm/generation-context-closure-report.json",
    "source_boundary_report": "/.well-known/rdllm/source-boundary-report.json",
    "source_authenticity_report": "/.well-known/rdllm/source-authenticity-report.json",
    "decision_provenance_report": "/.well-known/rdllm/decision-provenance-report.json",
    "calibrated_attribution_report": "/.well-known/rdllm/calibrated-attribution-report.json",
    "attribution_exchange": "/.well-known/rdllm/attribution-exchange.json",
    "conformance_vector_pack": "/.well-known/rdllm/conformance-vector-pack.json",
    "federation_handshake": "/.well-known/rdllm/federation-handshake.json",
    "attribution_capsule": "/.well-known/rdllm/attribution-capsule.json",
    "response_release_gate": "/.well-known/rdllm/release-gate.json",
    "proof_carrying_response": "/.well-known/rdllm/proof-carrying-response.json",
    "serving_gateway_report": "/.well-known/rdllm/serving-gateway-report.json",
    "streaming_attribution_manifest": "/.well-known/rdllm/streaming-attribution-manifest.json",
    "conversation_attribution_ledger": "/.well-known/rdllm/conversation-attribution-ledger.json",
    "agent_tool_attribution_ledger": "/.well-known/rdllm/agent-tool-attribution-ledger.json",
    "creator_license_contract": "/.well-known/rdllm/creator-license-contract.json",
    "source_confidence_report": "/.well-known/rdllm/source-confidence-report.json",
    "citation_footer_contract": "/.well-known/rdllm/citation-footer-contract.json",
    "private_audit_challenge": "/.well-known/rdllm/private-audit-challenge.json",
    "transitive_attribution_report": "/.well-known/rdllm/transitive-attribution-report.json",
    "clearinghouse_report": "/.well-known/rdllm/clearinghouse-report.json",
    "remittance_report": "/.well-known/rdllm/remittance-report.json",
    "payment_execution_report": "/.well-known/rdllm/payment-execution-report.json",
    "payment_rail_attestation": "/.well-known/rdllm/payment-rail-attestation.json",
    "creator_payout_receipt_report": "/.well-known/rdllm/creator-payout-receipt-report.json",
    "rendered_attribution_audit": "/.well-known/rdllm/rendered-attribution-audit.json",
    "training_memory_provenance": "/.well-known/rdllm/training-memory-provenance.json",
    "evidence_locked_generation": "/.well-known/rdllm/evidence-locked-generation.json",
    "emission_evidence_enforcement": "/.well-known/rdllm/emission-evidence-enforcement.json",
    "live_emission_witness": "/.well-known/rdllm/live-emission-witness.json",
    "live_emission_transparency": "/.well-known/rdllm/live-emission-transparency.json",
    "attested_runtime": "/.well-known/rdllm/attested-runtime.json",
    "claim_source_attribution_report": "/.well-known/rdllm/claim-source-attribution-report.json",
    "evidence_utility_attribution_report": "/.well-known/rdllm/evidence-utility-attribution-report.json",
    "parametric_memory_attribution_report": "/.well-known/rdllm/parametric-memory-attribution-report.json",
    "style_influence_attribution_report": "/.well-known/rdllm/style-influence-attribution-report.json",
    "model_lineage_attribution_report": "/.well-known/rdllm/model-lineage-attribution-report.json",
    "black_box_model_provenance_report": "/.well-known/rdllm/black-box-model-provenance-report.json",
    "attribution_dispute_adjudication_report": "/.well-known/rdllm/attribution-dispute-adjudication-report.json",
    "post_adjudication_settlement_adjustment_report": "/.well-known/rdllm/post-adjudication-settlement-adjustment-report.json",
    "residual_corpus_royalty_report": "/.well-known/rdllm/residual-corpus-royalty-report.json",
    "valuation_method_audit_report": "/.well-known/rdllm/valuation-method-audit-report.json",
    "evidence_region_binding_report": "/.well-known/rdllm/evidence-region-binding-report.json",
    "source_access_lease_report": "/.well-known/rdllm/source-access-lease-report.json",
    "content_protocol_ingestion_report": "/.well-known/rdllm/content-protocol-ingestion-report.json",
    "citation_reliance_receipt": "/.well-known/rdllm/citation-reliance-receipt.json",
    "license_transaction_receipt": "/.well-known/rdllm/license-transaction-receipt.json",
    "grounded_source_footer": "/.well-known/rdllm/grounded-source-footer.json",
    "source_footer_delivery": "/.well-known/rdllm/source-footer-delivery.json",
    "foundation_api_profile": "/.well-known/rdllm/foundation-attribution-profile.json",
    "client_attribution_enforcement": "/.well-known/rdllm/client-attribution-enforcement.json",
    "persistent_memory_provenance": "/.well-known/rdllm/persistent-memory-provenance.json",
    "private_reasoning_attribution": "/.well-known/rdllm/private-reasoning-attribution.json",
    "post_training_signal_provenance": "/.well-known/rdllm/post-training-signal-provenance.json",
    "attribution_bom": "/.well-known/rdllm/attribution-bom.json",
    "creator_attribution_audit_index": "/.well-known/rdllm/creator-attribution-audit-index.json",
    "creator_attribution_audit_federation": "/.well-known/rdllm/creator-attribution-audit-federation.json",
    "creator_attribution_audit_federation_transparency": "/.well-known/rdllm/creator-audit-federation-transparency.json",
    "creator_audit_transparency_monitor": "/.well-known/rdllm/creator-audit-transparency-monitor.json",
    "creator_audit_private_watch": "/.well-known/rdllm/creator-audit-private-watch.json",
    "deep_research_citation_audit": "/.well-known/rdllm/deep-research-citation-audit.json",
    "source_freshness_audit": "/.well-known/rdllm/source-freshness-audit.json",
    "royalty_abuse_audit": "/.well-known/rdllm/royalty-abuse-audit.json",
    "consent_revocation_propagation": "/.well-known/rdllm/consent-revocation-propagation.json",
    "evidence_force_calibration": "/.well-known/rdllm/evidence-force-calibration.json",
    "warranted_source_footer": "/.well-known/rdllm/warranted-source-footer.json",
    "source_origin_lineage": "/.well-known/rdllm/source-origin-lineage.json",
    "evidence_preview_footer": "/.well-known/rdllm/evidence-preview-footer.json",
    "evidence_locator_manifest": "/.well-known/rdllm/evidence-locator-manifest.json",
    "citation_url_health": "/.well-known/rdllm/citation-url-health.json",
    "composite_foundation_adapter": "/.well-known/rdllm/composite-foundation-adapter.json",
    "foundation_provider_conformance": "/.well-known/rdllm/foundation-provider-conformance.json",
    "foundation_runtime_adapter": "/.well-known/rdllm/foundation-runtime-adapter.json",
    "foundation_runtime_router": "/.well-known/rdllm/foundation-runtime-router.json",
    "foundation_model_deployment_attestation": "/.well-known/rdllm/foundation-model-deployment-attestation.json",
    "universal_composition_receipt": "/.well-known/rdllm/universal-composition-receipt.json",
    "universal_composition_settlement": "/.well-known/rdllm/universal-composition-settlement.json",
    "universal_foundation_model_contract": "/.well-known/rdllm/universal-foundation-model-contract.json",
    "universal_invocation_guard": "/.well-known/rdllm/universal-invocation-guard.json",
    "universal_invocation_coverage": "/.well-known/rdllm/universal-invocation-coverage.json",
    "universal_invocation_witness": "/.well-known/rdllm/universal-invocation-witness.json",
    "universal_content_credential": "/.well-known/rdllm/universal-content-credential.json",
    "universal_rdllm_passport": "/.well-known/rdllm/universal-rdllm-passport.json",
    "universal_adoption_standard": "/.well-known/rdllm/universal-adoption-standard.json",
    "universal_interop_test_kit": "/.well-known/rdllm/universal-interop-test-kit.json",
    "universal_context_provenance_bridge": "/.well-known/rdllm/universal-context-provenance-bridge.json",
    "universal_citation_verification_contract": "/.well-known/rdllm/universal-citation-verification-contract.json",
    "universal_grounded_reuse_contract": "/.well-known/rdllm/universal-grounded-reuse-contract.json",
    "universal_training_serving_contract": "/.well-known/rdllm/universal-training-serving-contract.json",
    "universal_confidential_attribution_audit": "/.well-known/rdllm/universal-confidential-attribution-audit.json",
    "universal_attribution_authority_control_plane": "/.well-known/rdllm/universal-attribution-authority-control-plane.json",
    "universal_rdllm_root": "/.well-known/rdllm/universal-rdllm-root.json",
    "universal_emission_enforcement_gateway": "/.well-known/rdllm/universal-emission-enforcement-gateway.json",
    "universal_composite_rdllm_profile": "/.well-known/rdllm/universal-composite-rdllm-profile.json",
    "universal_runtime_conformance_receipt": "/.well-known/rdllm/universal-runtime-conformance-receipt.json",
    "universal_claim_provenance_envelope": "/.well-known/rdllm/universal-claim-provenance-envelope.json",
    "universal_provider_wire_protocol": "/.well-known/rdllm/universal-provider-wire-protocol.json",
    "universal_accountability_audit_trail": "/.well-known/rdllm/universal-accountability-audit-trail.json",
    "universal_accountability_witness_quorum": "/.well-known/rdllm/universal-accountability-witness-quorum.json",
    "universal_grounded_reliance_contract": "/.well-known/rdllm/universal-grounded-reliance-contract.json",
    "universal_reliance_correction_ledger": "/.well-known/rdllm/universal-reliance-correction-ledger.json",
    "universal_foundation_adoption_kernel": "/.well-known/rdllm/universal-foundation-adoption-kernel.json",
    "universal_provider_adapter_harness": "/.well-known/rdllm/universal-provider-adapter-harness.json",
    "universal_provider_drift_sentinel": "/.well-known/rdllm/universal-provider-drift-sentinel.json",
    "universal_attribution_negotiation_handshake": "/.well-known/rdllm/universal-attribution-negotiation-handshake.json",
    "universal_negotiated_invocation_enforcement": "/.well-known/rdllm/universal-negotiated-invocation-enforcement.json",
    "universal_certification_trust_federation": "/.well-known/rdllm/universal-certification-trust-federation.json",
    "universal_foundation_provider_adoption_pack": "/.well-known/rdllm/universal-foundation-provider-adoption-pack.json",
    "universal_industry_adoption_root": "/.well-known/rdllm/universal-industry-adoption-root.json",
    "universal_reference_implementation_distribution": "/.well-known/rdllm/universal-reference-implementation-distribution.json",
    "universal_live_attribution_proof": "/.well-known/rdllm/universal-live-attribution-proof.json",
    "universal_foundation_model_release_passport": "/.well-known/rdllm/universal-foundation-model-release-passport.json",
    "universal_composite_rdllm_contract": "/.well-known/rdllm/universal-composite-rdllm-contract.json",
    "universal_foundation_provider_binding_matrix": "/.well-known/rdllm/universal-foundation-provider-binding-matrix.json",
    "universal_provider_conformance_runner_receipt": "/.well-known/rdllm/universal-provider-conformance-runner-receipt.json",
    "universal_production_invocation_admission": "/.well-known/rdllm/universal-production-invocation-admission.json",
    "universal_source_grounded_response_receipt": "/.well-known/rdllm/universal-source-grounded-response-receipt.json",
    "universal_distribution_reliance_passport": "/.well-known/rdllm/universal-distribution-reliance-passport.json",
    "universal_adversarial_provenance_quorum": "/.well-known/rdllm/universal-adversarial-provenance-quorum.json",
    "universal_procurement_regulatory_reliance_contract": "/.well-known/rdllm/universal-procurement-regulatory-reliance-contract.json",
    "universal_provider_onboarding_migration_covenant": "/.well-known/rdllm/universal-provider-onboarding-migration-covenant.json",
    "universal_model_provider_registry": "/.well-known/rdllm/universal-model-provider-registry.json",
    "universal_source_footer_enforcement_contract": "/.well-known/rdllm/universal-source-footer-enforcement-contract.json",
    "universal_provider_catalog_coverage_contract": "/.well-known/rdllm/universal-provider-catalog-coverage-contract.json",
    "universal_runtime_route_binding_contract": "/.well-known/rdllm/universal-runtime-route-binding-contract.json",
    "universal_verified_source_footer_contract": "/.well-known/rdllm/universal-verified-source-footer-contract.json",
    "universal_model_capability_coverage_contract": "/.well-known/rdllm/universal-model-capability-coverage-contract.json",
    "universal_live_capability_discovery_contract": "/.well-known/rdllm/universal-live-capability-discovery-contract.json",
    "universal_native_source_annotation_contract": "/.well-known/rdllm/universal-native-source-annotation-contract.json",
    "universal_claim_evidence_footer_verification_contract": "/.well-known/rdllm/universal-claim-evidence-footer-verification-contract.json",
    "universal_provider_meter_normalization_contract": "/.well-known/rdllm/universal-provider-meter-normalization-contract.json",
    "universal_provider_response_state_normalization_contract": "/.well-known/rdllm/universal-provider-response-state-normalization-contract.json",
    "audit_attestation": "/.well-known/rdllm/audit-attestation.json",
    "revenue_allocation_report": "/.well-known/rdllm/revenue-allocation-report.json",
    "finance_ledger_attestation": "/.well-known/rdllm/finance-ledger-attestation.json",
    "proof_dependency_graph": "/.well-known/rdllm/proof-dependency-graph.json",
    "publication_monitor": "/.well-known/rdllm/publication-monitor.json",
    "publication_witness": "/.well-known/rdllm/publication-witness.json",
    "trust_registry": "/.well-known/rdllm/trust-registry.json",
    "certification_attestation": "/.well-known/rdllm/certification-attestation.json",
    "response_envelope": "/.well-known/rdllm/sample-response-envelope.json",
}


def _hashable_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in manifest.items()
        if key not in {"manifest_hash", "signature"}
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


def _declared_hash(artifact: dict[str, Any]) -> str:
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(artifact)


def _artifact_hash_is_reproducible(artifact: dict[str, Any]) -> bool:
    for field in DECLARED_HASH_FIELDS:
        if artifact.get(field):
            if field == "trace_hash":
                return (
                    hash_payload(
                        {
                            key: value
                            for key, value in artifact.items()
                            if key not in {"trace_hash", "signature"}
                        }
                    )
                    == artifact[field]
                )
            if field == "receipt_hash" and isinstance(artifact.get("payload"), dict):
                return hash_payload(artifact["payload"]) == artifact[field]
            return hash_payload(_hashable_artifact(artifact)) == artifact[field]
    return True


def _artifact_entry(
    name: str,
    artifact_type: str,
    payload: dict[str, Any],
    *,
    required: bool,
) -> dict[str, Any]:
    entry = {
        "name": name,
        "artifact_type": artifact_type,
        "well_known_path": WELL_KNOWN_PATHS[name],
        "required": required,
        "declared_hash": _declared_hash(payload),
        "payload_hash": hash_payload(payload),
    }
    entry["entry_hash"] = hash_payload(entry)
    return entry


def _artifact_catalog(
    *,
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    integration_profile: dict[str, Any],
    response_envelope: dict[str, Any],
    assurance_bundle: dict[str, Any],
    training_summary: dict[str, Any] | None,
    provenance_evaluation_report: dict[str, Any] | None,
    counterfactual_report: dict[str, Any] | None,
    media_attribution_report: dict[str, Any] | None,
    model_signal_report: dict[str, Any] | None,
    pinpoint_provenance_report: dict[str, Any] | None,
    citation_identity_report: dict[str, Any] | None,
    attribution_consensus_report: dict[str, Any] | None,
    verifier_quorum_report: dict[str, Any] | None,
    verifier_accountability_report: dict[str, Any] | None,
    receipt_transparency_consistency_report: dict[str, Any] | None,
    watchtower_challenge_settlement_report: dict[str, Any] | None,
    output_provenance_binding_report: dict[str, Any] | None,
    rights_remediation_report: dict[str, Any] | None,
    semantic_text_attribution_report: dict[str, Any] | None,
    code_attribution_report: dict[str, Any] | None,
    claim_verification_report: dict[str, Any] | None,
    source_availability_report: dict[str, Any] | None,
    evidence_sufficiency_report: dict[str, Any] | None,
    counterevidence_report: dict[str, Any] | None,
    answer_claim_coverage_report: dict[str, Any] | None,
    generation_context_closure_report: dict[str, Any] | None,
    source_boundary_report: dict[str, Any] | None,
    source_authenticity_report: dict[str, Any] | None,
    decision_provenance_report: dict[str, Any] | None,
    calibrated_attribution_report: dict[str, Any] | None,
    streaming_attribution_manifest: dict[str, Any] | None,
    conversation_attribution_ledger: dict[str, Any] | None,
    agent_tool_attribution_ledger: dict[str, Any] | None,
    creator_license_contract: dict[str, Any] | None,
    source_confidence_report: dict[str, Any] | None,
    citation_footer_contract: dict[str, Any] | None,
    private_audit_challenge: dict[str, Any] | None,
    transitive_attribution_report: dict[str, Any] | None,
    clearinghouse_report: dict[str, Any] | None,
    remittance_report: dict[str, Any] | None,
    payment_execution_report: dict[str, Any] | None,
    payment_rail_attestation: dict[str, Any] | None,
    creator_payout_receipt_report: dict[str, Any] | None,
    rendered_attribution_audit: dict[str, Any] | None,
    training_memory_provenance: dict[str, Any] | None,
    post_training_signal_provenance: dict[str, Any] | None,
    evidence_locked_generation: dict[str, Any] | None,
    emission_evidence_enforcement: dict[str, Any] | None,
    live_emission_witness: dict[str, Any] | None,
    live_emission_transparency: dict[str, Any] | None,
    attested_runtime: dict[str, Any] | None,
    claim_source_attribution_report: dict[str, Any] | None,
    evidence_utility_attribution_report: dict[str, Any] | None,
    parametric_memory_attribution_report: dict[str, Any] | None,
    style_influence_attribution_report: dict[str, Any] | None,
    model_lineage_attribution_report: dict[str, Any] | None,
    black_box_model_provenance_report: dict[str, Any] | None,
    attribution_dispute_adjudication_report: dict[str, Any] | None,
    post_adjudication_settlement_adjustment_report: dict[str, Any] | None,
    residual_corpus_royalty_report: dict[str, Any] | None,
    valuation_method_audit_report: dict[str, Any] | None,
    evidence_region_binding_report: dict[str, Any] | None,
    source_access_lease_report: dict[str, Any] | None,
    content_protocol_ingestion_report: dict[str, Any] | None,
    citation_reliance_receipt: dict[str, Any] | None,
    license_transaction_receipt: dict[str, Any] | None,
    grounded_source_footer: dict[str, Any] | None,
    source_footer_delivery: dict[str, Any] | None,
    deep_research_citation_audit: dict[str, Any] | None,
    source_freshness_audit: dict[str, Any] | None,
    royalty_abuse_audit: dict[str, Any] | None,
    consent_revocation_propagation: dict[str, Any] | None,
    evidence_force_calibration: dict[str, Any] | None,
    warranted_source_footer: dict[str, Any] | None,
    source_origin_lineage: dict[str, Any] | None,
    evidence_preview_footer: dict[str, Any] | None,
    evidence_locator_manifest: dict[str, Any] | None,
    citation_url_health: dict[str, Any] | None,
    foundation_api_profile: dict[str, Any] | None,
    composite_foundation_adapter: dict[str, Any] | None,
    foundation_provider_conformance: dict[str, Any] | None,
    foundation_runtime_adapter: dict[str, Any] | None,
    foundation_runtime_router: dict[str, Any] | None,
    foundation_model_deployment_attestation: dict[str, Any] | None,
    universal_composition_receipt: dict[str, Any] | None,
    universal_composition_settlement: dict[str, Any] | None,
    universal_foundation_model_contract: dict[str, Any] | None,
    universal_invocation_guard: dict[str, Any] | None,
    universal_invocation_coverage: dict[str, Any] | None,
    universal_invocation_witness: dict[str, Any] | None,
    universal_content_credential: dict[str, Any] | None,
    universal_rdllm_passport: dict[str, Any] | None,
    universal_adoption_standard: dict[str, Any] | None,
    universal_interop_test_kit: dict[str, Any] | None,
    universal_context_provenance_bridge: dict[str, Any] | None,
    universal_citation_verification_contract: dict[str, Any] | None,
    universal_grounded_reuse_contract: dict[str, Any] | None,
    universal_training_serving_contract: dict[str, Any] | None,
    universal_confidential_attribution_audit: dict[str, Any] | None,
    universal_attribution_authority_control_plane: dict[str, Any] | None,
    universal_foundation_provider_binding_matrix: dict[str, Any] | None,
    universal_provider_conformance_runner_receipt: dict[str, Any] | None,
    universal_production_invocation_admission: dict[str, Any] | None,
    universal_source_grounded_response_receipt: dict[str, Any] | None,
    universal_distribution_reliance_passport: dict[str, Any] | None,
    universal_adversarial_provenance_quorum: dict[str, Any] | None,
    universal_procurement_regulatory_reliance_contract: dict[str, Any] | None,
    universal_provider_onboarding_migration_covenant: dict[str, Any] | None,
    universal_model_provider_registry: dict[str, Any] | None,
    universal_source_footer_enforcement_contract: dict[str, Any] | None,
    universal_provider_catalog_coverage_contract: dict[str, Any] | None,
    universal_runtime_route_binding_contract: dict[str, Any] | None,
    universal_verified_source_footer_contract: dict[str, Any] | None,
    universal_model_capability_coverage_contract: dict[str, Any] | None,
    universal_live_capability_discovery_contract: dict[str, Any] | None,
    universal_native_source_annotation_contract: dict[str, Any] | None,
    universal_claim_evidence_footer_verification_contract: dict[str, Any] | None,
    universal_provider_meter_normalization_contract: dict[str, Any] | None,
    universal_provider_response_state_normalization_contract: dict[str, Any] | None,
    revenue_allocation_report: dict[str, Any] | None,
    finance_ledger_attestation: dict[str, Any] | None,
    proof_dependency_graph: dict[str, Any] | None,
    publication_monitor: dict[str, Any] | None,
    publication_witness: dict[str, Any] | None,
    trust_registry: dict[str, Any] | None,
    certification_attestation: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    artifacts: list[tuple[str, str, dict[str, Any], bool]] = [
        ("provider_attribution_card", "rdllm-provider-attribution-card/v1", provider_card, True),
        ("certification_report", "rdllm-certification/v1", certification_report, True),
        ("integration_profile", "rdllm-integration-profile/v1", integration_profile, True),
        ("response_envelope", "rdllm-response-envelope/v1", response_envelope, True),
        ("assurance_bundle", "rdllm-assurance-bundle/v1", assurance_bundle, True),
    ]
    if training_summary is not None:
        artifacts.append(
            (
                "training_content_summary",
                "rdllm-training-content-summary/v1",
                training_summary,
                False,
            )
        )
    if provenance_evaluation_report is not None:
        artifacts.append(
            (
                "provenance_evaluation_report",
                "rdllm-provenance-evaluation/v1",
                provenance_evaluation_report,
                False,
            )
        )
    if counterfactual_report is not None:
        artifacts.append(
            (
                "counterfactual_influence_report",
                "rdllm-counterfactual-influence/v1",
                counterfactual_report,
                False,
            )
        )
    if media_attribution_report is not None:
        artifacts.append(
            (
                "media_attribution_report",
                "rdllm-media-attribution/v1",
                media_attribution_report,
                False,
            )
        )
    if model_signal_report is not None:
        artifacts.append(
            (
                "model_signal_attribution_report",
                "rdllm-model-signal-attribution/v1",
                model_signal_report,
                False,
            )
        )
    if pinpoint_provenance_report is not None:
        artifacts.append(
            (
                "pinpoint_provenance_report",
                "rdllm-pinpoint-provenance-report/v1",
                pinpoint_provenance_report,
                False,
            )
        )
    if citation_identity_report is not None:
        artifacts.append(
            (
                "citation_identity_report",
                "rdllm-citation-identity-report/v1",
                citation_identity_report,
                False,
            )
        )
    if attribution_consensus_report is not None:
        artifacts.append(
            (
                "attribution_consensus_report",
                "rdllm-attribution-consensus-report/v1",
                attribution_consensus_report,
                False,
            )
        )
    if verifier_quorum_report is not None:
        artifacts.append(
            (
                "verifier_quorum_report",
                "rdllm-verifier-quorum-report/v1",
                verifier_quorum_report,
                False,
            )
        )
    if verifier_accountability_report is not None:
        artifacts.append(
            (
                "verifier_accountability_report",
                "rdllm-verifier-accountability-report/v1",
                verifier_accountability_report,
                False,
            )
        )
    if receipt_transparency_consistency_report is not None:
        artifacts.append(
            (
                "receipt_transparency_consistency_report",
                "rdllm-receipt-transparency-consistency-report/v1",
                receipt_transparency_consistency_report,
                False,
            )
        )
    if watchtower_challenge_settlement_report is not None:
        artifacts.append(
            (
                "watchtower_challenge_settlement_report",
                "rdllm-watchtower-challenge-settlement-report/v1",
                watchtower_challenge_settlement_report,
                False,
            )
        )
    if output_provenance_binding_report is not None:
        artifacts.append(
            (
                "output_provenance_binding_report",
                "rdllm-output-provenance-binding-report/v1",
                output_provenance_binding_report,
                False,
            )
        )
    if rights_remediation_report is not None:
        artifacts.append(
            (
                "rights_remediation_report",
                "rdllm-rights-remediation/v1",
                rights_remediation_report,
                False,
            )
        )
    if semantic_text_attribution_report is not None:
        artifacts.append(
            (
                "semantic_text_attribution_report",
                "rdllm-semantic-text-attribution/v1",
                semantic_text_attribution_report,
                False,
            )
        )
    if code_attribution_report is not None:
        artifacts.append(
            (
                "code_attribution_report",
                "rdllm-code-attribution-report/v1",
                code_attribution_report,
                False,
            )
        )
    if claim_verification_report is not None:
        artifacts.append(
            (
                "claim_verification_report",
                "rdllm-claim-verification-report/v1",
                claim_verification_report,
                False,
            )
        )
    if source_availability_report is not None:
        artifacts.append(
            (
                "source_availability_report",
                "rdllm-source-availability-report/v1",
                source_availability_report,
                False,
            )
        )
    if evidence_sufficiency_report is not None:
        artifacts.append(
            (
                "evidence_sufficiency_report",
                "rdllm-evidence-sufficiency-report/v1",
                evidence_sufficiency_report,
                False,
            )
        )
    if counterevidence_report is not None:
        artifacts.append(
            (
                "counterevidence_report",
                "rdllm-counterevidence-adjudication-report/v1",
                counterevidence_report,
                False,
            )
        )
    if answer_claim_coverage_report is not None:
        artifacts.append(
            (
                "answer_claim_coverage_report",
                "rdllm-answer-claim-coverage-report/v1",
                answer_claim_coverage_report,
                False,
            )
        )
    if generation_context_closure_report is not None:
        artifacts.append(
            (
                "generation_context_closure_report",
                "rdllm-generation-context-closure-report/v1",
                generation_context_closure_report,
                False,
            )
        )
    if source_boundary_report is not None:
        artifacts.append(
            (
                "source_boundary_report",
                "rdllm-source-boundary-report/v1",
                source_boundary_report,
                False,
            )
        )
    if source_authenticity_report is not None:
        artifacts.append(
            (
                "source_authenticity_report",
                "rdllm-source-authenticity-report/v1",
                source_authenticity_report,
                False,
            )
        )
    if decision_provenance_report is not None:
        artifacts.append(
            (
                "decision_provenance_report",
                "rdllm-decision-provenance-report/v1",
                decision_provenance_report,
                False,
            )
        )
    if calibrated_attribution_report is not None:
        artifacts.append(
            (
                "calibrated_attribution_report",
                "rdllm-calibrated-attribution-confidence/v1",
                calibrated_attribution_report,
                False,
            )
        )
    if streaming_attribution_manifest is not None:
        artifacts.append(
            (
                "streaming_attribution_manifest",
                "rdllm-streaming-attribution-manifest/v1",
                streaming_attribution_manifest,
                False,
            )
        )
    if conversation_attribution_ledger is not None:
        artifacts.append(
            (
                "conversation_attribution_ledger",
                "rdllm-conversation-attribution-ledger/v1",
                conversation_attribution_ledger,
                False,
            )
        )
    if agent_tool_attribution_ledger is not None:
        artifacts.append(
            (
                "agent_tool_attribution_ledger",
                "rdllm-agent-tool-attribution-ledger/v1",
                agent_tool_attribution_ledger,
                False,
            )
        )
    if creator_license_contract is not None:
        artifacts.append(
            (
                "creator_license_contract",
                "rdllm-creator-license-contract/v1",
                creator_license_contract,
                False,
            )
        )
    if source_confidence_report is not None:
        artifacts.append(
            (
                "source_confidence_report",
                "rdllm-source-confidence-report/v1",
                source_confidence_report,
                False,
            )
        )
    if citation_footer_contract is not None:
        artifacts.append(
            (
                "citation_footer_contract",
                "rdllm-citation-footer-contract/v1",
                citation_footer_contract,
                False,
            )
        )
    if private_audit_challenge is not None:
        artifacts.append(
            (
                "private_audit_challenge",
                "rdllm-private-audit-challenge/v1",
                private_audit_challenge,
                False,
            )
        )
    if transitive_attribution_report is not None:
        artifacts.append(
            (
                "transitive_attribution_report",
                "rdllm-transitive-attribution-report/v1",
                transitive_attribution_report,
                False,
            )
        )
    if clearinghouse_report is not None:
        artifacts.append(
            (
                "clearinghouse_report",
                "rdllm-clearinghouse-report/v1",
                clearinghouse_report,
                False,
            )
        )
    if remittance_report is not None:
        artifacts.append(
            (
                "remittance_report",
                "rdllm-remittance-report/v1",
                remittance_report,
                False,
            )
        )
    if payment_execution_report is not None:
        artifacts.append(
            (
                "payment_execution_report",
                "rdllm-payment-execution-report/v1",
                payment_execution_report,
                False,
            )
        )
    if payment_rail_attestation is not None:
        artifacts.append(
            (
                "payment_rail_attestation",
                "rdllm-payment-rail-attestation/v1",
                payment_rail_attestation,
                False,
            )
        )
    if creator_payout_receipt_report is not None:
        artifacts.append(
            (
                "creator_payout_receipt_report",
                "rdllm-creator-payout-receipt-report/v1",
                creator_payout_receipt_report,
                False,
            )
        )
    if rendered_attribution_audit is not None:
        artifacts.append(
            (
                "rendered_attribution_audit",
                "rdllm-rendered-attribution-audit/v1",
                rendered_attribution_audit,
                False,
            )
        )
    if training_memory_provenance is not None:
        artifacts.append(
            (
                "training_memory_provenance",
                "rdllm-training-memory-provenance/v1",
                training_memory_provenance,
                False,
            )
        )
    if post_training_signal_provenance is not None:
        artifacts.append(
            (
                "post_training_signal_provenance",
                "rdllm-post-training-signal-provenance/v1",
                post_training_signal_provenance,
                False,
            )
        )
    if evidence_locked_generation is not None:
        artifacts.append(
            (
                "evidence_locked_generation",
                "rdllm-evidence-locked-generation/v1",
                evidence_locked_generation,
                False,
            )
        )
    if emission_evidence_enforcement is not None:
        artifacts.append(
            (
                "emission_evidence_enforcement",
                "rdllm-emission-evidence-enforcement/v1",
                emission_evidence_enforcement,
                False,
            )
        )
    if live_emission_witness is not None:
        artifacts.append(
            (
                "live_emission_witness",
                "rdllm-live-emission-witness/v1",
                live_emission_witness,
                False,
            )
        )
    if live_emission_transparency is not None:
        artifacts.append(
            (
                "live_emission_transparency",
                "rdllm-live-emission-transparency/v1",
                live_emission_transparency,
                False,
            )
        )
    if attested_runtime is not None:
        artifacts.append(
            (
                "attested_runtime",
                "rdllm-attested-attribution-runtime/v1",
                attested_runtime,
                False,
            )
        )
    if claim_source_attribution_report is not None:
        artifacts.append(
            (
                "claim_source_attribution_report",
                "rdllm-claim-source-attribution/v1",
                claim_source_attribution_report,
                False,
            )
        )
    if evidence_utility_attribution_report is not None:
        artifacts.append(
            (
                "evidence_utility_attribution_report",
                "rdllm-causal-evidence-utility/v1",
                evidence_utility_attribution_report,
                False,
            )
        )
    if parametric_memory_attribution_report is not None:
        artifacts.append(
            (
                "parametric_memory_attribution_report",
                "rdllm-parametric-memory-attribution/v1",
                parametric_memory_attribution_report,
                False,
            )
        )
    if style_influence_attribution_report is not None:
        artifacts.append(
            (
                "style_influence_attribution_report",
                "rdllm-style-influence-attribution/v1",
                style_influence_attribution_report,
                False,
            )
        )
    if model_lineage_attribution_report is not None:
        artifacts.append(
            (
                "model_lineage_attribution_report",
                "rdllm-model-lineage-attribution/v1",
                model_lineage_attribution_report,
                False,
            )
        )
    if black_box_model_provenance_report is not None:
        artifacts.append(
            (
                "black_box_model_provenance_report",
                "rdllm-black-box-model-provenance/v1",
                black_box_model_provenance_report,
                False,
            )
        )
    if attribution_dispute_adjudication_report is not None:
        artifacts.append(
            (
                "attribution_dispute_adjudication_report",
                "rdllm-attribution-dispute-adjudication-report/v1",
                attribution_dispute_adjudication_report,
                False,
            )
        )
    if post_adjudication_settlement_adjustment_report is not None:
        artifacts.append(
            (
                "post_adjudication_settlement_adjustment_report",
                "rdllm-post-adjudication-settlement-adjustment-report/v1",
                post_adjudication_settlement_adjustment_report,
                False,
            )
        )
    if residual_corpus_royalty_report is not None:
        artifacts.append(
            (
                "residual_corpus_royalty_report",
                "rdllm-residual-corpus-royalty-report/v1",
                residual_corpus_royalty_report,
                False,
            )
        )
    if valuation_method_audit_report is not None:
        artifacts.append(
            (
                "valuation_method_audit_report",
                "rdllm-valuation-method-audit/v1",
                valuation_method_audit_report,
                False,
            )
        )
    if evidence_region_binding_report is not None:
        artifacts.append(
            (
                "evidence_region_binding_report",
                "rdllm-evidence-region-binding/v1",
                evidence_region_binding_report,
                False,
            )
        )
    if source_access_lease_report is not None:
        artifacts.append(
            (
                "source_access_lease_report",
                "rdllm-source-access-lease/v1",
                source_access_lease_report,
                False,
            )
        )
    if content_protocol_ingestion_report is not None:
        artifacts.append(
            (
                "content_protocol_ingestion_report",
                "rdllm-content-protocol-ingestion/v1",
                content_protocol_ingestion_report,
                False,
            )
        )
    if citation_reliance_receipt is not None:
        artifacts.append(
            (
                "citation_reliance_receipt",
                "rdllm-citation-reliance-receipt/v1",
                citation_reliance_receipt,
                False,
            )
        )
    if license_transaction_receipt is not None:
        artifacts.append(
            (
                "license_transaction_receipt",
                "rdllm-license-transaction-receipt/v1",
                license_transaction_receipt,
                False,
            )
        )
    if grounded_source_footer is not None:
        artifacts.append(
            (
                "grounded_source_footer",
                "rdllm-grounded-source-footer/v1",
                grounded_source_footer,
                False,
            )
        )
    if source_footer_delivery is not None:
        artifacts.append(
            (
                "source_footer_delivery",
                "rdllm-source-footer-delivery/v1",
                source_footer_delivery,
                False,
            )
        )
    if deep_research_citation_audit is not None:
        artifacts.append(
            (
                "deep_research_citation_audit",
                "rdllm-deep-research-citation-audit/v1",
                deep_research_citation_audit,
                False,
            )
        )
    if source_freshness_audit is not None:
        artifacts.append(
            (
                "source_freshness_audit",
                "rdllm-source-freshness-audit/v1",
                source_freshness_audit,
                False,
            )
        )
    if royalty_abuse_audit is not None:
        artifacts.append(
            (
                "royalty_abuse_audit",
                "rdllm-royalty-abuse-audit/v1",
                royalty_abuse_audit,
                False,
            )
        )
    if consent_revocation_propagation is not None:
        artifacts.append(
            (
                "consent_revocation_propagation",
                "rdllm-consent-revocation-propagation/v1",
                consent_revocation_propagation,
                False,
            )
        )
    if evidence_force_calibration is not None:
        artifacts.append(
            (
                "evidence_force_calibration",
                "rdllm-evidence-force-calibration/v1",
                evidence_force_calibration,
                False,
            )
        )
    if warranted_source_footer is not None:
        artifacts.append(
            (
                "warranted_source_footer",
                "rdllm-warranted-source-footer/v1",
                warranted_source_footer,
                False,
            )
        )
    if source_origin_lineage is not None:
        artifacts.append(
            (
                "source_origin_lineage",
                "rdllm-source-origin-lineage/v1",
                source_origin_lineage,
                False,
            )
        )
    if evidence_preview_footer is not None:
        artifacts.append(
            (
                "evidence_preview_footer",
                "rdllm-evidence-preview-footer/v1",
                evidence_preview_footer,
                False,
            )
        )
    if evidence_locator_manifest is not None:
        artifacts.append(
            (
                "evidence_locator_manifest",
                "rdllm-evidence-locator-manifest/v1",
                evidence_locator_manifest,
                False,
            )
        )
    if citation_url_health is not None:
        artifacts.append(
            (
                "citation_url_health",
                "rdllm-citation-url-health/v1",
                citation_url_health,
                False,
            )
        )
    if foundation_api_profile is not None:
        artifacts.append(
            (
                "foundation_api_profile",
                "rdllm-foundation-attribution-profile/v1",
                foundation_api_profile,
                False,
            )
        )
    if composite_foundation_adapter is not None:
        artifacts.append(
            (
                "composite_foundation_adapter",
                "rdllm-composite-foundation-adapter/v1",
                composite_foundation_adapter,
                False,
            )
        )
    if foundation_provider_conformance is not None:
        artifacts.append(
            (
                "foundation_provider_conformance",
                "rdllm-foundation-provider-conformance/v1",
                foundation_provider_conformance,
                False,
            )
        )
    if foundation_runtime_adapter is not None:
        artifacts.append(
            (
                "foundation_runtime_adapter",
                "rdllm-foundation-runtime-adapter/v1",
                foundation_runtime_adapter,
                False,
            )
        )
    if foundation_runtime_router is not None:
        artifacts.append(
            (
                "foundation_runtime_router",
                "rdllm-foundation-runtime-router/v1",
                foundation_runtime_router,
                False,
            )
        )
    if foundation_model_deployment_attestation is not None:
        artifacts.append(
            (
                "foundation_model_deployment_attestation",
                "rdllm-foundation-model-deployment-attestation/v1",
                foundation_model_deployment_attestation,
                False,
            )
        )
    if universal_composition_receipt is not None:
        artifacts.append(
            (
                "universal_composition_receipt",
                "rdllm-universal-composition-receipt/v1",
                universal_composition_receipt,
                False,
            )
        )
    if universal_composition_settlement is not None:
        artifacts.append(
            (
                "universal_composition_settlement",
                "rdllm-universal-composition-settlement/v1",
                universal_composition_settlement,
                False,
            )
        )
    if universal_foundation_model_contract is not None:
        artifacts.append(
            (
                "universal_foundation_model_contract",
                "rdllm-universal-foundation-model-contract/v1",
                universal_foundation_model_contract,
                False,
            )
        )
    if universal_invocation_guard is not None:
        artifacts.append(
            (
                "universal_invocation_guard",
                "rdllm-universal-invocation-guard/v1",
                universal_invocation_guard,
                False,
            )
        )
    if universal_invocation_coverage is not None:
        artifacts.append(
            (
                "universal_invocation_coverage",
                "rdllm-universal-invocation-coverage/v1",
                universal_invocation_coverage,
                False,
            )
        )
    if universal_invocation_witness is not None:
        artifacts.append(
            (
                "universal_invocation_witness",
                "rdllm-universal-invocation-witness/v1",
                universal_invocation_witness,
                False,
            )
        )
    if universal_content_credential is not None:
        artifacts.append(
            (
                "universal_content_credential",
                "rdllm-universal-content-credential/v1",
                universal_content_credential,
                False,
            )
        )
    if universal_rdllm_passport is not None:
        artifacts.append(
            (
                "universal_rdllm_passport",
                "rdllm-universal-rdllm-passport/v1",
                universal_rdllm_passport,
                False,
            )
        )
    if universal_adoption_standard is not None:
        artifacts.append(
            (
                "universal_adoption_standard",
                "rdllm-universal-adoption-standard/v1",
                universal_adoption_standard,
                False,
            )
        )
    if universal_interop_test_kit is not None:
        artifacts.append(
            (
                "universal_interop_test_kit",
                "rdllm-universal-interop-test-kit/v1",
                universal_interop_test_kit,
                False,
            )
        )
    if universal_context_provenance_bridge is not None:
        artifacts.append(
            (
                "universal_context_provenance_bridge",
                "rdllm-universal-context-provenance-bridge/v1",
                universal_context_provenance_bridge,
                False,
            )
        )
    if universal_citation_verification_contract is not None:
        artifacts.append(
            (
                "universal_citation_verification_contract",
                "rdllm-universal-citation-verification-contract/v1",
                universal_citation_verification_contract,
                False,
            )
        )
    if universal_grounded_reuse_contract is not None:
        artifacts.append(
            (
                "universal_grounded_reuse_contract",
                "rdllm-universal-grounded-reuse-contract/v1",
                universal_grounded_reuse_contract,
                False,
            )
        )
    if universal_training_serving_contract is not None:
        artifacts.append(
            (
                "universal_training_serving_contract",
                "rdllm-universal-training-serving-contract/v1",
                universal_training_serving_contract,
                False,
            )
        )
    if universal_confidential_attribution_audit is not None:
        artifacts.append(
            (
                "universal_confidential_attribution_audit",
                "rdllm-universal-confidential-attribution-audit/v1",
                universal_confidential_attribution_audit,
                False,
            )
        )
    if universal_attribution_authority_control_plane is not None:
        artifacts.append(
            (
                "universal_attribution_authority_control_plane",
                "rdllm-universal-attribution-authority-control-plane/v1",
                universal_attribution_authority_control_plane,
                False,
            )
        )
    if universal_foundation_provider_binding_matrix is not None:
        artifacts.append(
            (
                "universal_foundation_provider_binding_matrix",
                "rdllm-universal-foundation-provider-binding-matrix/v1",
                universal_foundation_provider_binding_matrix,
                False,
            )
        )
    if universal_provider_conformance_runner_receipt is not None:
        artifacts.append(
            (
                "universal_provider_conformance_runner_receipt",
                "rdllm-universal-provider-conformance-runner-receipt/v1",
                universal_provider_conformance_runner_receipt,
                False,
            )
        )
    if universal_production_invocation_admission is not None:
        artifacts.append(
            (
                "universal_production_invocation_admission",
                "rdllm-universal-production-invocation-admission/v1",
                universal_production_invocation_admission,
                False,
            )
        )
    if universal_source_grounded_response_receipt is not None:
        artifacts.append(
            (
                "universal_source_grounded_response_receipt",
                "rdllm-universal-source-grounded-response-receipt/v1",
                universal_source_grounded_response_receipt,
                False,
            )
        )
    if universal_distribution_reliance_passport is not None:
        artifacts.append(
            (
                "universal_distribution_reliance_passport",
                "rdllm-universal-distribution-reliance-passport/v1",
                universal_distribution_reliance_passport,
                False,
            )
        )
    if universal_adversarial_provenance_quorum is not None:
        artifacts.append(
            (
                "universal_adversarial_provenance_quorum",
                "rdllm-universal-adversarial-provenance-quorum/v1",
                universal_adversarial_provenance_quorum,
                False,
            )
        )
    if universal_procurement_regulatory_reliance_contract is not None:
        artifacts.append(
            (
                "universal_procurement_regulatory_reliance_contract",
                "rdllm-universal-procurement-regulatory-reliance-contract/v1",
                universal_procurement_regulatory_reliance_contract,
                False,
            )
        )
    if universal_provider_onboarding_migration_covenant is not None:
        artifacts.append(
            (
                "universal_provider_onboarding_migration_covenant",
                "rdllm-universal-provider-onboarding-migration-covenant/v1",
                universal_provider_onboarding_migration_covenant,
                False,
            )
        )
    if universal_model_provider_registry is not None:
        artifacts.append(
            (
                "universal_model_provider_registry",
                "rdllm-universal-model-provider-registry/v1",
                universal_model_provider_registry,
                False,
            )
        )
    if universal_source_footer_enforcement_contract is not None:
        artifacts.append(
            (
                "universal_source_footer_enforcement_contract",
                "rdllm-universal-source-footer-enforcement-contract/v1",
                universal_source_footer_enforcement_contract,
                False,
            )
        )
    if universal_provider_catalog_coverage_contract is not None:
        artifacts.append(
            (
                "universal_provider_catalog_coverage_contract",
                "rdllm-universal-provider-catalog-coverage-contract/v1",
                universal_provider_catalog_coverage_contract,
                False,
            )
        )
    if universal_runtime_route_binding_contract is not None:
        artifacts.append(
            (
                "universal_runtime_route_binding_contract",
                "rdllm-universal-runtime-route-binding-contract/v1",
                universal_runtime_route_binding_contract,
                False,
            )
        )
    if universal_verified_source_footer_contract is not None:
        artifacts.append(
            (
                "universal_verified_source_footer_contract",
                "rdllm-universal-verified-source-footer-contract/v1",
                universal_verified_source_footer_contract,
                False,
            )
        )
    if universal_model_capability_coverage_contract is not None:
        artifacts.append(
            (
                "universal_model_capability_coverage_contract",
                "rdllm-universal-model-capability-coverage-contract/v1",
                universal_model_capability_coverage_contract,
                False,
            )
        )
    if universal_live_capability_discovery_contract is not None:
        artifacts.append(
            (
                "universal_live_capability_discovery_contract",
                "rdllm-universal-live-capability-discovery-contract/v1",
                universal_live_capability_discovery_contract,
                False,
            )
        )
    if universal_native_source_annotation_contract is not None:
        artifacts.append(
            (
                "universal_native_source_annotation_contract",
                "rdllm-universal-native-source-annotation-contract/v1",
                universal_native_source_annotation_contract,
                False,
            )
        )
    if universal_claim_evidence_footer_verification_contract is not None:
        artifacts.append(
            (
                "universal_claim_evidence_footer_verification_contract",
                "rdllm-universal-claim-evidence-footer-verification-contract/v1",
                universal_claim_evidence_footer_verification_contract,
                False,
            )
        )
    if universal_provider_meter_normalization_contract is not None:
        artifacts.append(
            (
                "universal_provider_meter_normalization_contract",
                "rdllm-universal-provider-meter-normalization-contract/v1",
                universal_provider_meter_normalization_contract,
                False,
            )
        )
    if universal_provider_response_state_normalization_contract is not None:
        artifacts.append(
            (
                "universal_provider_response_state_normalization_contract",
                "rdllm-universal-provider-response-state-normalization-contract/v1",
                universal_provider_response_state_normalization_contract,
                False,
            )
        )
    if revenue_allocation_report is not None:
        artifacts.append(
            (
                "revenue_allocation_report",
                "rdllm-revenue-allocation-report/v1",
                revenue_allocation_report,
                False,
            )
        )
    if finance_ledger_attestation is not None:
        artifacts.append(
            (
                "finance_ledger_attestation",
                "rdllm-finance-ledger-attestation/v1",
                finance_ledger_attestation,
                False,
            )
        )
    if proof_dependency_graph is not None:
        artifacts.append(
            (
                "proof_dependency_graph",
                "rdllm-proof-dependency-graph/v1",
                proof_dependency_graph,
                False,
            )
        )
    if publication_monitor is not None:
        artifacts.append(
            (
                "publication_monitor",
                "rdllm-publication-monitor/v1",
                publication_monitor,
                False,
            )
        )
    if publication_witness is not None:
        artifacts.append(
            (
                "publication_witness",
                "rdllm-publication-witness/v1",
                publication_witness,
                False,
            )
        )
    if trust_registry is not None:
        artifacts.append(
            (
                "trust_registry",
                "rdllm-trust-registry/v1",
                trust_registry,
                False,
            )
        )
    if certification_attestation is not None:
        artifacts.append(
            (
                "certification_attestation",
                "rdllm-certification-attestation/v1",
                certification_attestation,
                False,
            )
        )
    return [
        _artifact_entry(name, artifact_type, payload, required=required)
        for name, artifact_type, payload, required in artifacts
    ]


def _level_number(level: str) -> int:
    try:
        return int(level.rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _artifact_types(assurance_bundle: dict[str, Any]) -> set[str]:
    return set(assurance_bundle.get("summary", {}).get("artifact_types", []))


def make_discovery_manifest(
    *,
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    integration_profile: dict[str, Any],
    response_envelope: dict[str, Any],
    assurance_bundle: dict[str, Any],
    training_summary: dict[str, Any] | None = None,
    provenance_evaluation_report: dict[str, Any] | None = None,
    counterfactual_report: dict[str, Any] | None = None,
    media_attribution_report: dict[str, Any] | None = None,
    model_signal_report: dict[str, Any] | None = None,
    pinpoint_provenance_report: dict[str, Any] | None = None,
    citation_identity_report: dict[str, Any] | None = None,
    attribution_consensus_report: dict[str, Any] | None = None,
    verifier_quorum_report: dict[str, Any] | None = None,
    verifier_accountability_report: dict[str, Any] | None = None,
    receipt_transparency_consistency_report: dict[str, Any] | None = None,
    watchtower_challenge_settlement_report: dict[str, Any] | None = None,
    output_provenance_binding_report: dict[str, Any] | None = None,
    rights_remediation_report: dict[str, Any] | None = None,
    semantic_text_attribution_report: dict[str, Any] | None = None,
    code_attribution_report: dict[str, Any] | None = None,
    claim_verification_report: dict[str, Any] | None = None,
    source_availability_report: dict[str, Any] | None = None,
    evidence_sufficiency_report: dict[str, Any] | None = None,
    counterevidence_report: dict[str, Any] | None = None,
    answer_claim_coverage_report: dict[str, Any] | None = None,
    generation_context_closure_report: dict[str, Any] | None = None,
    source_boundary_report: dict[str, Any] | None = None,
    source_authenticity_report: dict[str, Any] | None = None,
    decision_provenance_report: dict[str, Any] | None = None,
    calibrated_attribution_report: dict[str, Any] | None = None,
    streaming_attribution_manifest: dict[str, Any] | None = None,
    conversation_attribution_ledger: dict[str, Any] | None = None,
    agent_tool_attribution_ledger: dict[str, Any] | None = None,
    creator_license_contract: dict[str, Any] | None = None,
    source_confidence_report: dict[str, Any] | None = None,
    citation_footer_contract: dict[str, Any] | None = None,
    private_audit_challenge: dict[str, Any] | None = None,
    transitive_attribution_report: dict[str, Any] | None = None,
    clearinghouse_report: dict[str, Any] | None = None,
    remittance_report: dict[str, Any] | None = None,
    payment_execution_report: dict[str, Any] | None = None,
    payment_rail_attestation: dict[str, Any] | None = None,
    creator_payout_receipt_report: dict[str, Any] | None = None,
    rendered_attribution_audit: dict[str, Any] | None = None,
    training_memory_provenance: dict[str, Any] | None = None,
    post_training_signal_provenance: dict[str, Any] | None = None,
    evidence_locked_generation: dict[str, Any] | None = None,
    emission_evidence_enforcement: dict[str, Any] | None = None,
    live_emission_witness: dict[str, Any] | None = None,
    live_emission_transparency: dict[str, Any] | None = None,
    attested_runtime: dict[str, Any] | None = None,
    claim_source_attribution_report: dict[str, Any] | None = None,
    evidence_utility_attribution_report: dict[str, Any] | None = None,
    parametric_memory_attribution_report: dict[str, Any] | None = None,
    style_influence_attribution_report: dict[str, Any] | None = None,
    model_lineage_attribution_report: dict[str, Any] | None = None,
    black_box_model_provenance_report: dict[str, Any] | None = None,
    attribution_dispute_adjudication_report: dict[str, Any] | None = None,
    post_adjudication_settlement_adjustment_report: dict[str, Any] | None = None,
    residual_corpus_royalty_report: dict[str, Any] | None = None,
    valuation_method_audit_report: dict[str, Any] | None = None,
    evidence_region_binding_report: dict[str, Any] | None = None,
    source_access_lease_report: dict[str, Any] | None = None,
    content_protocol_ingestion_report: dict[str, Any] | None = None,
    citation_reliance_receipt: dict[str, Any] | None = None,
    license_transaction_receipt: dict[str, Any] | None = None,
    grounded_source_footer: dict[str, Any] | None = None,
    source_footer_delivery: dict[str, Any] | None = None,
    deep_research_citation_audit: dict[str, Any] | None = None,
    source_freshness_audit: dict[str, Any] | None = None,
    royalty_abuse_audit: dict[str, Any] | None = None,
    consent_revocation_propagation: dict[str, Any] | None = None,
    evidence_force_calibration: dict[str, Any] | None = None,
    warranted_source_footer: dict[str, Any] | None = None,
    source_origin_lineage: dict[str, Any] | None = None,
    evidence_preview_footer: dict[str, Any] | None = None,
    evidence_locator_manifest: dict[str, Any] | None = None,
    citation_url_health: dict[str, Any] | None = None,
    foundation_api_profile: dict[str, Any] | None = None,
    composite_foundation_adapter: dict[str, Any] | None = None,
    foundation_provider_conformance: dict[str, Any] | None = None,
    foundation_runtime_adapter: dict[str, Any] | None = None,
    foundation_runtime_router: dict[str, Any] | None = None,
    foundation_model_deployment_attestation: dict[str, Any] | None = None,
    universal_composition_receipt: dict[str, Any] | None = None,
    universal_composition_settlement: dict[str, Any] | None = None,
    universal_foundation_model_contract: dict[str, Any] | None = None,
    universal_invocation_guard: dict[str, Any] | None = None,
    universal_invocation_coverage: dict[str, Any] | None = None,
    universal_invocation_witness: dict[str, Any] | None = None,
    universal_content_credential: dict[str, Any] | None = None,
    universal_rdllm_passport: dict[str, Any] | None = None,
    universal_adoption_standard: dict[str, Any] | None = None,
    universal_interop_test_kit: dict[str, Any] | None = None,
    universal_context_provenance_bridge: dict[str, Any] | None = None,
    universal_citation_verification_contract: dict[str, Any] | None = None,
    universal_grounded_reuse_contract: dict[str, Any] | None = None,
    universal_training_serving_contract: dict[str, Any] | None = None,
    universal_confidential_attribution_audit: dict[str, Any] | None = None,
    universal_attribution_authority_control_plane: dict[str, Any] | None = None,
    universal_foundation_provider_binding_matrix: dict[str, Any] | None = None,
    universal_provider_conformance_runner_receipt: dict[str, Any] | None = None,
    universal_production_invocation_admission: dict[str, Any] | None = None,
    universal_source_grounded_response_receipt: dict[str, Any] | None = None,
    universal_distribution_reliance_passport: dict[str, Any] | None = None,
    universal_adversarial_provenance_quorum: dict[str, Any] | None = None,
    universal_procurement_regulatory_reliance_contract: dict[str, Any] | None = None,
    universal_provider_onboarding_migration_covenant: dict[str, Any] | None = None,
    universal_model_provider_registry: dict[str, Any] | None = None,
    universal_source_footer_enforcement_contract: dict[str, Any] | None = None,
    universal_provider_catalog_coverage_contract: dict[str, Any] | None = None,
    universal_runtime_route_binding_contract: dict[str, Any] | None = None,
    universal_verified_source_footer_contract: dict[str, Any] | None = None,
    universal_model_capability_coverage_contract: dict[str, Any] | None = None,
    universal_live_capability_discovery_contract: dict[str, Any] | None = None,
    universal_native_source_annotation_contract: dict[str, Any] | None = None,
    universal_claim_evidence_footer_verification_contract: dict[str, Any] | None = None,
    universal_provider_meter_normalization_contract: dict[str, Any] | None = None,
    universal_provider_response_state_normalization_contract: dict[str, Any] | None = None,
    revenue_allocation_report: dict[str, Any] | None = None,
    finance_ledger_attestation: dict[str, Any] | None = None,
    proof_dependency_graph: dict[str, Any] | None = None,
    publication_monitor: dict[str, Any] | None = None,
    publication_witness: dict[str, Any] | None = None,
    trust_registry: dict[str, Any] | None = None,
    certification_attestation: dict[str, Any] | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed well-known manifest for discovering RDLLM provider surfaces."""

    provider = integration_profile.get("provider", provider_card.get("provider", {}))
    api_contract = integration_profile.get("api_contract", {})
    certification_summary = integration_profile.get("certification", {})
    catalog = _artifact_catalog(
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
        universal_foundation_provider_binding_matrix=universal_foundation_provider_binding_matrix,
        universal_provider_conformance_runner_receipt=(
            universal_provider_conformance_runner_receipt
        ),
        universal_production_invocation_admission=universal_production_invocation_admission,
        universal_source_grounded_response_receipt=(
            universal_source_grounded_response_receipt
        ),
        universal_distribution_reliance_passport=universal_distribution_reliance_passport,
        universal_adversarial_provenance_quorum=universal_adversarial_provenance_quorum,
        universal_procurement_regulatory_reliance_contract=(
            universal_procurement_regulatory_reliance_contract
        ),
        universal_provider_onboarding_migration_covenant=(
            universal_provider_onboarding_migration_covenant
        ),
        universal_model_provider_registry=universal_model_provider_registry,
        universal_source_footer_enforcement_contract=(
            universal_source_footer_enforcement_contract
        ),
        universal_provider_catalog_coverage_contract=(
            universal_provider_catalog_coverage_contract
        ),
        universal_runtime_route_binding_contract=(
            universal_runtime_route_binding_contract
        ),
        universal_verified_source_footer_contract=(
            universal_verified_source_footer_contract
        ),
        universal_model_capability_coverage_contract=(
            universal_model_capability_coverage_contract
        ),
        universal_live_capability_discovery_contract=(
            universal_live_capability_discovery_contract
        ),
        universal_native_source_annotation_contract=(
            universal_native_source_annotation_contract
        ),
        universal_claim_evidence_footer_verification_contract=(
            universal_claim_evidence_footer_verification_contract
        ),
        universal_provider_meter_normalization_contract=(
            universal_provider_meter_normalization_contract
        ),
        universal_provider_response_state_normalization_contract=(
            universal_provider_response_state_normalization_contract
        ),
        revenue_allocation_report=revenue_allocation_report,
        finance_ledger_attestation=finance_ledger_attestation,
        proof_dependency_graph=proof_dependency_graph,
        publication_monitor=publication_monitor,
        publication_witness=publication_witness,
        trust_registry=trust_registry,
        certification_attestation=certification_attestation,
    )
    artifact_names = {entry["name"] for entry in catalog}
    assurance_types = _artifact_types(assurance_bundle)
    schemas = dict(SCHEMA_MAP)
    schemas["discovery_manifest"] = "docs/schemas/discovery_manifest.schema.json"
    public_surfaces = dict(provider_card.get("public_disclosure_surfaces", {}))
    readiness_checks = {
        "integration_profile_ready": integration_profile.get("summary", {}).get("status")
        == "ready",
        "certification_level_at_least_l22": (
            certification_summary.get("status") == "passed"
            and _level_number(str(certification_summary.get("highest_level", ""))) >= 22
        ),
        "provider_declares_discovery_surface": public_surfaces.get("discovery_manifest")
        is True,
        "all_required_artifacts_cataloged": set(REQUIRED_ARTIFACTS).issubset(
            artifact_names
        ),
        "artifact_hashes_reproducible": all(
            _artifact_hash_is_reproducible(artifact)
            for artifact in (
                provider_card,
                certification_report,
                integration_profile,
                response_envelope,
                assurance_bundle,
            )
        )
        and (training_summary is None or _artifact_hash_is_reproducible(training_summary)),
        "provenance_evaluation_hash_reproducible": (
            provenance_evaluation_report is None
            or _artifact_hash_is_reproducible(provenance_evaluation_report)
        ),
        "counterfactual_influence_hash_reproducible": (
            counterfactual_report is None
            or _artifact_hash_is_reproducible(counterfactual_report)
        ),
        "media_attribution_hash_reproducible": (
            media_attribution_report is None
            or _artifact_hash_is_reproducible(media_attribution_report)
        ),
        "model_signal_hash_reproducible": (
            model_signal_report is None
            or _artifact_hash_is_reproducible(model_signal_report)
        ),
        "pinpoint_provenance_hash_reproducible": (
            pinpoint_provenance_report is None
            or _artifact_hash_is_reproducible(pinpoint_provenance_report)
        ),
        "citation_identity_hash_reproducible": (
            citation_identity_report is None
            or _artifact_hash_is_reproducible(citation_identity_report)
        ),
        "attribution_consensus_hash_reproducible": (
            attribution_consensus_report is None
            or _artifact_hash_is_reproducible(attribution_consensus_report)
        ),
        "verifier_quorum_hash_reproducible": (
            verifier_quorum_report is None
            or _artifact_hash_is_reproducible(verifier_quorum_report)
        ),
        "verifier_accountability_hash_reproducible": (
            verifier_accountability_report is None
            or _artifact_hash_is_reproducible(verifier_accountability_report)
        ),
        "receipt_transparency_consistency_hash_reproducible": (
            receipt_transparency_consistency_report is None
            or _artifact_hash_is_reproducible(receipt_transparency_consistency_report)
        ),
        "watchtower_challenge_settlement_hash_reproducible": (
            watchtower_challenge_settlement_report is None
            or _artifact_hash_is_reproducible(watchtower_challenge_settlement_report)
        ),
        "output_provenance_binding_hash_reproducible": (
            output_provenance_binding_report is None
            or _artifact_hash_is_reproducible(output_provenance_binding_report)
        ),
        "rights_remediation_hash_reproducible": (
            rights_remediation_report is None
            or _artifact_hash_is_reproducible(rights_remediation_report)
        ),
        "semantic_text_attribution_hash_reproducible": (
            semantic_text_attribution_report is None
            or _artifact_hash_is_reproducible(semantic_text_attribution_report)
        ),
        "code_attribution_hash_reproducible": (
            code_attribution_report is None
            or _artifact_hash_is_reproducible(code_attribution_report)
        ),
        "claim_verification_hash_reproducible": (
            claim_verification_report is None
            or _artifact_hash_is_reproducible(claim_verification_report)
        ),
        "source_availability_hash_reproducible": (
            source_availability_report is None
            or _artifact_hash_is_reproducible(source_availability_report)
        ),
        "evidence_sufficiency_hash_reproducible": (
            evidence_sufficiency_report is None
            or _artifact_hash_is_reproducible(evidence_sufficiency_report)
        ),
        "counterevidence_hash_reproducible": (
            counterevidence_report is None
            or _artifact_hash_is_reproducible(counterevidence_report)
        ),
        "answer_claim_coverage_hash_reproducible": (
            answer_claim_coverage_report is None
            or _artifact_hash_is_reproducible(answer_claim_coverage_report)
        ),
        "generation_context_closure_hash_reproducible": (
            generation_context_closure_report is None
            or _artifact_hash_is_reproducible(generation_context_closure_report)
        ),
        "source_boundary_hash_reproducible": (
            source_boundary_report is None
            or _artifact_hash_is_reproducible(source_boundary_report)
        ),
        "source_authenticity_hash_reproducible": (
            source_authenticity_report is None
            or _artifact_hash_is_reproducible(source_authenticity_report)
        ),
        "decision_provenance_hash_reproducible": (
            decision_provenance_report is None
            or _artifact_hash_is_reproducible(decision_provenance_report)
        ),
        "calibrated_attribution_hash_reproducible": (
            calibrated_attribution_report is None
            or _artifact_hash_is_reproducible(calibrated_attribution_report)
        ),
        "streaming_attribution_manifest_hash_reproducible": (
            streaming_attribution_manifest is None
            or _artifact_hash_is_reproducible(streaming_attribution_manifest)
        ),
        "conversation_attribution_ledger_hash_reproducible": (
            conversation_attribution_ledger is None
            or _artifact_hash_is_reproducible(conversation_attribution_ledger)
        ),
        "agent_tool_attribution_ledger_hash_reproducible": (
            agent_tool_attribution_ledger is None
            or _artifact_hash_is_reproducible(agent_tool_attribution_ledger)
        ),
        "creator_license_contract_hash_reproducible": (
            creator_license_contract is None
            or _artifact_hash_is_reproducible(creator_license_contract)
        ),
        "source_confidence_report_hash_reproducible": (
            source_confidence_report is None
            or _artifact_hash_is_reproducible(source_confidence_report)
        ),
        "citation_footer_contract_hash_reproducible": (
            citation_footer_contract is None
            or _artifact_hash_is_reproducible(citation_footer_contract)
        ),
        "private_audit_challenge_hash_reproducible": (
            private_audit_challenge is None
            or _artifact_hash_is_reproducible(private_audit_challenge)
        ),
        "transitive_attribution_report_hash_reproducible": (
            transitive_attribution_report is None
            or _artifact_hash_is_reproducible(transitive_attribution_report)
        ),
        "clearinghouse_report_hash_reproducible": (
            clearinghouse_report is None
            or _artifact_hash_is_reproducible(clearinghouse_report)
        ),
        "remittance_report_hash_reproducible": (
            remittance_report is None
            or _artifact_hash_is_reproducible(remittance_report)
        ),
        "payment_execution_report_hash_reproducible": (
            payment_execution_report is None
            or _artifact_hash_is_reproducible(payment_execution_report)
        ),
        "payment_rail_attestation_hash_reproducible": (
            payment_rail_attestation is None
            or _artifact_hash_is_reproducible(payment_rail_attestation)
        ),
        "creator_payout_receipt_report_hash_reproducible": (
            creator_payout_receipt_report is None
            or _artifact_hash_is_reproducible(creator_payout_receipt_report)
        ),
        "rendered_attribution_audit_hash_reproducible": (
            rendered_attribution_audit is None
            or _artifact_hash_is_reproducible(rendered_attribution_audit)
        ),
        "training_memory_provenance_hash_reproducible": (
            training_memory_provenance is None
            or _artifact_hash_is_reproducible(training_memory_provenance)
        ),
        "post_training_signal_provenance_hash_reproducible": (
            post_training_signal_provenance is None
            or _artifact_hash_is_reproducible(post_training_signal_provenance)
        ),
        "evidence_locked_generation_hash_reproducible": (
            evidence_locked_generation is None
            or _artifact_hash_is_reproducible(evidence_locked_generation)
        ),
        "emission_evidence_enforcement_hash_reproducible": (
            emission_evidence_enforcement is None
            or _artifact_hash_is_reproducible(emission_evidence_enforcement)
        ),
        "live_emission_witness_hash_reproducible": (
            live_emission_witness is None
            or _artifact_hash_is_reproducible(live_emission_witness)
        ),
        "live_emission_transparency_hash_reproducible": (
            live_emission_transparency is None
            or _artifact_hash_is_reproducible(live_emission_transparency)
        ),
        "attested_runtime_hash_reproducible": (
            attested_runtime is None
            or _artifact_hash_is_reproducible(attested_runtime)
        ),
        "claim_source_attribution_hash_reproducible": (
            claim_source_attribution_report is None
            or _artifact_hash_is_reproducible(claim_source_attribution_report)
        ),
        "evidence_utility_attribution_hash_reproducible": (
            evidence_utility_attribution_report is None
            or _artifact_hash_is_reproducible(evidence_utility_attribution_report)
        ),
        "parametric_memory_attribution_hash_reproducible": (
            parametric_memory_attribution_report is None
            or _artifact_hash_is_reproducible(parametric_memory_attribution_report)
        ),
        "style_influence_attribution_hash_reproducible": (
            style_influence_attribution_report is None
            or _artifact_hash_is_reproducible(style_influence_attribution_report)
        ),
        "model_lineage_attribution_hash_reproducible": (
            model_lineage_attribution_report is None
            or _artifact_hash_is_reproducible(model_lineage_attribution_report)
        ),
        "black_box_model_provenance_hash_reproducible": (
            black_box_model_provenance_report is None
            or _artifact_hash_is_reproducible(black_box_model_provenance_report)
        ),
        "attribution_dispute_adjudication_hash_reproducible": (
            attribution_dispute_adjudication_report is None
            or _artifact_hash_is_reproducible(attribution_dispute_adjudication_report)
        ),
        "post_adjudication_settlement_adjustment_hash_reproducible": (
            post_adjudication_settlement_adjustment_report is None
            or _artifact_hash_is_reproducible(
                post_adjudication_settlement_adjustment_report
            )
        ),
        "residual_corpus_royalty_hash_reproducible": (
            residual_corpus_royalty_report is None
            or _artifact_hash_is_reproducible(residual_corpus_royalty_report)
        ),
        "valuation_method_audit_hash_reproducible": (
            valuation_method_audit_report is None
            or _artifact_hash_is_reproducible(valuation_method_audit_report)
        ),
        "evidence_region_binding_hash_reproducible": (
            evidence_region_binding_report is None
            or _artifact_hash_is_reproducible(evidence_region_binding_report)
        ),
        "source_access_lease_hash_reproducible": (
            source_access_lease_report is None
            or _artifact_hash_is_reproducible(source_access_lease_report)
        ),
        "content_protocol_ingestion_hash_reproducible": (
            content_protocol_ingestion_report is None
            or _artifact_hash_is_reproducible(content_protocol_ingestion_report)
        ),
        "citation_reliance_receipt_hash_reproducible": (
            citation_reliance_receipt is None
            or _artifact_hash_is_reproducible(citation_reliance_receipt)
        ),
        "license_transaction_receipt_hash_reproducible": (
            license_transaction_receipt is None
            or _artifact_hash_is_reproducible(license_transaction_receipt)
        ),
        "grounded_source_footer_hash_reproducible": (
            grounded_source_footer is None
            or _artifact_hash_is_reproducible(grounded_source_footer)
        ),
        "source_footer_delivery_hash_reproducible": (
            source_footer_delivery is None
            or _artifact_hash_is_reproducible(source_footer_delivery)
        ),
        "deep_research_citation_audit_hash_reproducible": (
            deep_research_citation_audit is None
            or _artifact_hash_is_reproducible(deep_research_citation_audit)
        ),
        "source_freshness_audit_hash_reproducible": (
            source_freshness_audit is None
            or _artifact_hash_is_reproducible(source_freshness_audit)
        ),
        "royalty_abuse_audit_hash_reproducible": (
            royalty_abuse_audit is None
            or _artifact_hash_is_reproducible(royalty_abuse_audit)
        ),
        "consent_revocation_propagation_hash_reproducible": (
            consent_revocation_propagation is None
            or _artifact_hash_is_reproducible(consent_revocation_propagation)
        ),
        "evidence_force_calibration_hash_reproducible": (
            evidence_force_calibration is None
            or _artifact_hash_is_reproducible(evidence_force_calibration)
        ),
        "warranted_source_footer_hash_reproducible": (
            warranted_source_footer is None
            or _artifact_hash_is_reproducible(warranted_source_footer)
        ),
        "source_origin_lineage_hash_reproducible": (
            source_origin_lineage is None
            or _artifact_hash_is_reproducible(source_origin_lineage)
        ),
        "evidence_preview_footer_hash_reproducible": (
            evidence_preview_footer is None
            or _artifact_hash_is_reproducible(evidence_preview_footer)
        ),
        "evidence_locator_manifest_hash_reproducible": (
            evidence_locator_manifest is None
            or _artifact_hash_is_reproducible(evidence_locator_manifest)
        ),
        "citation_url_health_hash_reproducible": (
            citation_url_health is None
            or _artifact_hash_is_reproducible(citation_url_health)
        ),
        "foundation_api_profile_hash_reproducible": (
            foundation_api_profile is None
            or _artifact_hash_is_reproducible(foundation_api_profile)
        ),
        "composite_foundation_adapter_hash_reproducible": (
            composite_foundation_adapter is None
            or _artifact_hash_is_reproducible(composite_foundation_adapter)
        ),
        "foundation_provider_conformance_hash_reproducible": (
            foundation_provider_conformance is None
            or _artifact_hash_is_reproducible(foundation_provider_conformance)
        ),
        "foundation_runtime_adapter_hash_reproducible": (
            foundation_runtime_adapter is None
            or _artifact_hash_is_reproducible(foundation_runtime_adapter)
        ),
        "foundation_runtime_router_hash_reproducible": (
            foundation_runtime_router is None
            or _artifact_hash_is_reproducible(foundation_runtime_router)
        ),
        "foundation_model_deployment_attestation_hash_reproducible": (
            foundation_model_deployment_attestation is None
            or _artifact_hash_is_reproducible(foundation_model_deployment_attestation)
        ),
        "universal_composition_receipt_hash_reproducible": (
            universal_composition_receipt is None
            or _artifact_hash_is_reproducible(universal_composition_receipt)
        ),
        "universal_composition_settlement_hash_reproducible": (
            universal_composition_settlement is None
            or _artifact_hash_is_reproducible(universal_composition_settlement)
        ),
        "universal_foundation_model_contract_hash_reproducible": (
            universal_foundation_model_contract is None
            or _artifact_hash_is_reproducible(universal_foundation_model_contract)
        ),
        "universal_invocation_guard_hash_reproducible": (
            universal_invocation_guard is None
            or _artifact_hash_is_reproducible(universal_invocation_guard)
        ),
        "universal_invocation_coverage_hash_reproducible": (
            universal_invocation_coverage is None
            or _artifact_hash_is_reproducible(universal_invocation_coverage)
        ),
        "universal_invocation_witness_hash_reproducible": (
            universal_invocation_witness is None
            or _artifact_hash_is_reproducible(universal_invocation_witness)
        ),
        "universal_content_credential_hash_reproducible": (
            universal_content_credential is None
            or _artifact_hash_is_reproducible(universal_content_credential)
        ),
        "universal_rdllm_passport_hash_reproducible": (
            universal_rdllm_passport is None
            or _artifact_hash_is_reproducible(universal_rdllm_passport)
        ),
        "universal_adoption_standard_hash_reproducible": (
            universal_adoption_standard is None
            or _artifact_hash_is_reproducible(universal_adoption_standard)
        ),
        "universal_interop_test_kit_hash_reproducible": (
            universal_interop_test_kit is None
            or _artifact_hash_is_reproducible(universal_interop_test_kit)
        ),
        "universal_context_provenance_bridge_hash_reproducible": (
            universal_context_provenance_bridge is None
            or _artifact_hash_is_reproducible(universal_context_provenance_bridge)
        ),
        "universal_citation_verification_contract_hash_reproducible": (
            universal_citation_verification_contract is None
            or _artifact_hash_is_reproducible(universal_citation_verification_contract)
        ),
        "universal_grounded_reuse_contract_hash_reproducible": (
            universal_grounded_reuse_contract is None
            or _artifact_hash_is_reproducible(universal_grounded_reuse_contract)
        ),
        "universal_training_serving_contract_hash_reproducible": (
            universal_training_serving_contract is None
            or _artifact_hash_is_reproducible(universal_training_serving_contract)
        ),
        "universal_confidential_attribution_audit_hash_reproducible": (
            universal_confidential_attribution_audit is None
            or _artifact_hash_is_reproducible(universal_confidential_attribution_audit)
        ),
        "universal_attribution_authority_control_plane_hash_reproducible": (
            universal_attribution_authority_control_plane is None
            or _artifact_hash_is_reproducible(universal_attribution_authority_control_plane)
        ),
        "universal_foundation_provider_binding_matrix_hash_reproducible": (
            universal_foundation_provider_binding_matrix is None
            or _artifact_hash_is_reproducible(universal_foundation_provider_binding_matrix)
        ),
        "universal_provider_conformance_runner_receipt_hash_reproducible": (
            universal_provider_conformance_runner_receipt is None
            or _artifact_hash_is_reproducible(
                universal_provider_conformance_runner_receipt
            )
        ),
        "universal_production_invocation_admission_hash_reproducible": (
            universal_production_invocation_admission is None
            or _artifact_hash_is_reproducible(universal_production_invocation_admission)
        ),
        "universal_source_grounded_response_receipt_hash_reproducible": (
            universal_source_grounded_response_receipt is None
            or _artifact_hash_is_reproducible(
                universal_source_grounded_response_receipt
            )
        ),
        "universal_distribution_reliance_passport_hash_reproducible": (
            universal_distribution_reliance_passport is None
            or _artifact_hash_is_reproducible(universal_distribution_reliance_passport)
        ),
        "universal_adversarial_provenance_quorum_hash_reproducible": (
            universal_adversarial_provenance_quorum is None
            or _artifact_hash_is_reproducible(universal_adversarial_provenance_quorum)
        ),
        "universal_procurement_regulatory_reliance_contract_hash_reproducible": (
            universal_procurement_regulatory_reliance_contract is None
            or _artifact_hash_is_reproducible(
                universal_procurement_regulatory_reliance_contract
            )
        ),
        "universal_provider_onboarding_migration_covenant_hash_reproducible": (
            universal_provider_onboarding_migration_covenant is None
            or _artifact_hash_is_reproducible(
                universal_provider_onboarding_migration_covenant
            )
        ),
        "universal_model_provider_registry_hash_reproducible": (
            universal_model_provider_registry is None
            or _artifact_hash_is_reproducible(universal_model_provider_registry)
        ),
        "universal_source_footer_enforcement_contract_hash_reproducible": (
            universal_source_footer_enforcement_contract is None
            or _artifact_hash_is_reproducible(
                universal_source_footer_enforcement_contract
            )
        ),
        "universal_provider_catalog_coverage_contract_hash_reproducible": (
            universal_provider_catalog_coverage_contract is None
            or _artifact_hash_is_reproducible(
                universal_provider_catalog_coverage_contract
            )
        ),
        "universal_runtime_route_binding_contract_hash_reproducible": (
            universal_runtime_route_binding_contract is None
            or _artifact_hash_is_reproducible(
                universal_runtime_route_binding_contract
            )
        ),
        "universal_verified_source_footer_contract_hash_reproducible": (
            universal_verified_source_footer_contract is None
            or _artifact_hash_is_reproducible(
                universal_verified_source_footer_contract
            )
        ),
        "universal_model_capability_coverage_contract_hash_reproducible": (
            universal_model_capability_coverage_contract is None
            or _artifact_hash_is_reproducible(
                universal_model_capability_coverage_contract
            )
        ),
        "universal_live_capability_discovery_contract_hash_reproducible": (
            universal_live_capability_discovery_contract is None
            or _artifact_hash_is_reproducible(
                universal_live_capability_discovery_contract
            )
        ),
        "universal_native_source_annotation_contract_hash_reproducible": (
            universal_native_source_annotation_contract is None
            or _artifact_hash_is_reproducible(
                universal_native_source_annotation_contract
            )
        ),
        "universal_claim_evidence_footer_verification_contract_hash_reproducible": (
            universal_claim_evidence_footer_verification_contract is None
            or _artifact_hash_is_reproducible(
                universal_claim_evidence_footer_verification_contract
            )
        ),
        "universal_provider_meter_normalization_contract_hash_reproducible": (
            universal_provider_meter_normalization_contract is None
            or _artifact_hash_is_reproducible(
                universal_provider_meter_normalization_contract
            )
        ),
        "universal_provider_response_state_normalization_contract_hash_reproducible": (
            universal_provider_response_state_normalization_contract is None
            or _artifact_hash_is_reproducible(
                universal_provider_response_state_normalization_contract
            )
        ),
        "revenue_allocation_report_hash_reproducible": (
            revenue_allocation_report is None
            or _artifact_hash_is_reproducible(revenue_allocation_report)
        ),
        "finance_ledger_attestation_hash_reproducible": (
            finance_ledger_attestation is None
            or _artifact_hash_is_reproducible(finance_ledger_attestation)
        ),
        "proof_dependency_graph_hash_reproducible": (
            proof_dependency_graph is None
            or _artifact_hash_is_reproducible(proof_dependency_graph)
        ),
        "publication_monitor_hash_reproducible": (
            publication_monitor is None
            or _artifact_hash_is_reproducible(publication_monitor)
        ),
        "publication_witness_hash_reproducible": (
            publication_witness is None
            or _artifact_hash_is_reproducible(publication_witness)
        ),
        "trust_registry_hash_reproducible": (
            trust_registry is None
            or _artifact_hash_is_reproducible(trust_registry)
        ),
        "certification_attestation_hash_reproducible": (
            certification_attestation is None
            or _artifact_hash_is_reproducible(certification_attestation)
        ),
        "assurance_bundle_includes_integration_profile": (
            "integration_profile" in assurance_types
            or (
                "integration_profile" in artifact_names
                and _artifact_hash_is_reproducible(integration_profile)
            )
        ),
        "assurance_bundle_includes_response_envelope": "response_envelope"
        in assurance_types,
        "discovery_schema_declared": "discovery_manifest" in schemas,
        "well_known_paths_declared": all(
            WELL_KNOWN_PATHS[name] for name in artifact_names
        )
        and bool(DISCOVERY_WELL_KNOWN_PATH),
    }
    manifest = {
        "manifest_version": DISCOVERY_MANIFEST_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "provider": {
            "id": provider.get("id", "provider:unspecified"),
            "model_id": provider.get("model_id", "model:unspecified"),
            "model_version": provider.get("model_version", "unknown"),
        },
        "discovery": {
            "well_known_path": DISCOVERY_WELL_KNOWN_PATH,
            "integration_profile_path": WELL_KNOWN_PATHS["integration_profile"],
            "provider_card_path": WELL_KNOWN_PATHS["provider_attribution_card"],
            "certification_report_path": WELL_KNOWN_PATHS["certification_report"],
            "assurance_bundle_path": WELL_KNOWN_PATHS["assurance_bundle"],
            "sample_response_envelope_path": WELL_KNOWN_PATHS["response_envelope"],
            "training_content_summary_path": WELL_KNOWN_PATHS[
                "training_content_summary"
            ],
            "provenance_evaluation_report_path": WELL_KNOWN_PATHS[
                "provenance_evaluation_report"
            ],
            "counterfactual_influence_report_path": WELL_KNOWN_PATHS[
                "counterfactual_influence_report"
            ],
            "media_attribution_report_path": WELL_KNOWN_PATHS[
                "media_attribution_report"
            ],
            "model_signal_attribution_report_path": WELL_KNOWN_PATHS[
                "model_signal_attribution_report"
            ],
            "pinpoint_provenance_report_path": WELL_KNOWN_PATHS[
                "pinpoint_provenance_report"
            ],
            "citation_identity_report_path": WELL_KNOWN_PATHS[
                "citation_identity_report"
            ],
            "attribution_consensus_report_path": WELL_KNOWN_PATHS[
                "attribution_consensus_report"
            ],
            "verifier_quorum_report_path": WELL_KNOWN_PATHS[
                "verifier_quorum_report"
            ],
            "verifier_accountability_report_path": WELL_KNOWN_PATHS[
                "verifier_accountability_report"
            ],
            "receipt_transparency_consistency_report_path": WELL_KNOWN_PATHS[
                "receipt_transparency_consistency_report"
            ],
            "watchtower_challenge_settlement_report_path": WELL_KNOWN_PATHS[
                "watchtower_challenge_settlement_report"
            ],
            "output_provenance_binding_report_path": WELL_KNOWN_PATHS[
                "output_provenance_binding_report"
            ],
            "post_release_discovery_report_path": WELL_KNOWN_PATHS[
                "post_release_discovery_report"
            ],
            "rights_remediation_report_path": WELL_KNOWN_PATHS[
                "rights_remediation_report"
            ],
            "semantic_text_attribution_report_path": WELL_KNOWN_PATHS[
                "semantic_text_attribution_report"
            ],
            "code_attribution_report_path": WELL_KNOWN_PATHS[
                "code_attribution_report"
            ],
            "claim_verification_report_path": WELL_KNOWN_PATHS[
                "claim_verification_report"
            ],
            "source_availability_report_path": WELL_KNOWN_PATHS[
                "source_availability_report"
            ],
            "evidence_sufficiency_report_path": WELL_KNOWN_PATHS[
                "evidence_sufficiency_report"
            ],
            "counterevidence_report_path": WELL_KNOWN_PATHS[
                "counterevidence_report"
            ],
            "answer_claim_coverage_report_path": WELL_KNOWN_PATHS[
                "answer_claim_coverage_report"
            ],
            "generation_context_closure_report_path": WELL_KNOWN_PATHS[
                "generation_context_closure_report"
            ],
            "source_boundary_report_path": WELL_KNOWN_PATHS[
                "source_boundary_report"
            ],
            "source_authenticity_report_path": WELL_KNOWN_PATHS[
                "source_authenticity_report"
            ],
            "decision_provenance_report_path": WELL_KNOWN_PATHS[
                "decision_provenance_report"
            ],
            "calibrated_attribution_report_path": WELL_KNOWN_PATHS[
                "calibrated_attribution_report"
            ],
            "attribution_exchange_path": WELL_KNOWN_PATHS[
                "attribution_exchange"
            ],
            "conformance_vector_pack_path": WELL_KNOWN_PATHS[
                "conformance_vector_pack"
            ],
            "federation_handshake_path": WELL_KNOWN_PATHS[
                "federation_handshake"
            ],
            "attribution_capsule_path": WELL_KNOWN_PATHS[
                "attribution_capsule"
            ],
            "response_release_gate_path": WELL_KNOWN_PATHS[
                "response_release_gate"
            ],
            "proof_carrying_response_path": WELL_KNOWN_PATHS[
                "proof_carrying_response"
            ],
            "serving_gateway_report_path": WELL_KNOWN_PATHS[
                "serving_gateway_report"
            ],
            "streaming_attribution_manifest_path": WELL_KNOWN_PATHS[
                "streaming_attribution_manifest"
            ],
            "conversation_attribution_ledger_path": WELL_KNOWN_PATHS[
                "conversation_attribution_ledger"
            ],
            "agent_tool_attribution_ledger_path": WELL_KNOWN_PATHS[
                "agent_tool_attribution_ledger"
            ],
            "creator_license_contract_path": WELL_KNOWN_PATHS[
                "creator_license_contract"
            ],
            "source_confidence_report_path": WELL_KNOWN_PATHS[
                "source_confidence_report"
            ],
            "citation_footer_contract_path": WELL_KNOWN_PATHS[
                "citation_footer_contract"
            ],
            "private_audit_challenge_path": WELL_KNOWN_PATHS[
                "private_audit_challenge"
            ],
            "transitive_attribution_report_path": WELL_KNOWN_PATHS[
                "transitive_attribution_report"
            ],
            "clearinghouse_report_path": WELL_KNOWN_PATHS[
                "clearinghouse_report"
            ],
            "remittance_report_path": WELL_KNOWN_PATHS[
                "remittance_report"
            ],
            "payment_execution_report_path": WELL_KNOWN_PATHS[
                "payment_execution_report"
            ],
            "payment_rail_attestation_path": WELL_KNOWN_PATHS[
                "payment_rail_attestation"
            ],
            "creator_payout_receipt_report_path": WELL_KNOWN_PATHS[
                "creator_payout_receipt_report"
            ],
            "rendered_attribution_audit_path": WELL_KNOWN_PATHS[
                "rendered_attribution_audit"
            ],
            "training_memory_provenance_path": WELL_KNOWN_PATHS[
                "training_memory_provenance"
            ],
            "evidence_locked_generation_path": WELL_KNOWN_PATHS[
                "evidence_locked_generation"
            ],
            "emission_evidence_enforcement_path": WELL_KNOWN_PATHS[
                "emission_evidence_enforcement"
            ],
            "live_emission_witness_path": WELL_KNOWN_PATHS[
                "live_emission_witness"
            ],
            "live_emission_transparency_path": WELL_KNOWN_PATHS[
                "live_emission_transparency"
            ],
            "attested_runtime_path": WELL_KNOWN_PATHS[
                "attested_runtime"
            ],
            "claim_source_attribution_report_path": WELL_KNOWN_PATHS[
                "claim_source_attribution_report"
            ],
            "evidence_utility_attribution_report_path": WELL_KNOWN_PATHS[
                "evidence_utility_attribution_report"
            ],
            "parametric_memory_attribution_report_path": WELL_KNOWN_PATHS[
                "parametric_memory_attribution_report"
            ],
            "style_influence_attribution_report_path": WELL_KNOWN_PATHS[
                "style_influence_attribution_report"
            ],
            "model_lineage_attribution_report_path": WELL_KNOWN_PATHS[
                "model_lineage_attribution_report"
            ],
            "black_box_model_provenance_report_path": WELL_KNOWN_PATHS[
                "black_box_model_provenance_report"
            ],
            "attribution_dispute_adjudication_report_path": WELL_KNOWN_PATHS[
                "attribution_dispute_adjudication_report"
            ],
            "post_adjudication_settlement_adjustment_report_path": WELL_KNOWN_PATHS[
                "post_adjudication_settlement_adjustment_report"
            ],
            "residual_corpus_royalty_report_path": WELL_KNOWN_PATHS[
                "residual_corpus_royalty_report"
            ],
            "valuation_method_audit_report_path": WELL_KNOWN_PATHS[
                "valuation_method_audit_report"
            ],
            "evidence_region_binding_report_path": WELL_KNOWN_PATHS[
                "evidence_region_binding_report"
            ],
            "source_access_lease_report_path": WELL_KNOWN_PATHS[
                "source_access_lease_report"
            ],
            "content_protocol_ingestion_report_path": WELL_KNOWN_PATHS[
                "content_protocol_ingestion_report"
            ],
            "citation_reliance_receipt_path": WELL_KNOWN_PATHS[
                "citation_reliance_receipt"
            ],
            "license_transaction_receipt_path": WELL_KNOWN_PATHS[
                "license_transaction_receipt"
            ],
            "grounded_source_footer_path": WELL_KNOWN_PATHS[
                "grounded_source_footer"
            ],
            "source_footer_delivery_path": WELL_KNOWN_PATHS[
                "source_footer_delivery"
            ],
            "foundation_api_profile_path": WELL_KNOWN_PATHS[
                "foundation_api_profile"
            ],
            "client_attribution_enforcement_path": WELL_KNOWN_PATHS[
                "client_attribution_enforcement"
            ],
            "persistent_memory_provenance_path": WELL_KNOWN_PATHS[
                "persistent_memory_provenance"
            ],
            "private_reasoning_attribution_path": WELL_KNOWN_PATHS[
                "private_reasoning_attribution"
            ],
            "post_training_signal_provenance_path": WELL_KNOWN_PATHS[
                "post_training_signal_provenance"
            ],
            "attribution_bom_path": WELL_KNOWN_PATHS[
                "attribution_bom"
            ],
            "creator_attribution_audit_index_path": WELL_KNOWN_PATHS[
                "creator_attribution_audit_index"
            ],
            "creator_attribution_audit_federation_path": WELL_KNOWN_PATHS[
                "creator_attribution_audit_federation"
            ],
            "creator_attribution_audit_federation_transparency_path": WELL_KNOWN_PATHS[
                "creator_attribution_audit_federation_transparency"
            ],
            "creator_audit_transparency_monitor_path": WELL_KNOWN_PATHS[
                "creator_audit_transparency_monitor"
            ],
            "creator_audit_private_watch_path": WELL_KNOWN_PATHS[
                "creator_audit_private_watch"
            ],
            "deep_research_citation_audit_path": WELL_KNOWN_PATHS[
                "deep_research_citation_audit"
            ],
            "source_freshness_audit_path": WELL_KNOWN_PATHS[
                "source_freshness_audit"
            ],
            "royalty_abuse_audit_path": WELL_KNOWN_PATHS[
                "royalty_abuse_audit"
            ],
            "consent_revocation_propagation_path": WELL_KNOWN_PATHS[
                "consent_revocation_propagation"
            ],
            "evidence_force_calibration_path": WELL_KNOWN_PATHS[
                "evidence_force_calibration"
            ],
            "warranted_source_footer_path": WELL_KNOWN_PATHS[
                "warranted_source_footer"
            ],
            "source_origin_lineage_path": WELL_KNOWN_PATHS[
                "source_origin_lineage"
            ],
            "evidence_preview_footer_path": WELL_KNOWN_PATHS[
                "evidence_preview_footer"
            ],
            "evidence_locator_manifest_path": WELL_KNOWN_PATHS[
                "evidence_locator_manifest"
            ],
            "citation_url_health_path": WELL_KNOWN_PATHS["citation_url_health"],
            "composite_foundation_adapter_path": WELL_KNOWN_PATHS[
                "composite_foundation_adapter"
            ],
            "foundation_provider_conformance_path": WELL_KNOWN_PATHS[
                "foundation_provider_conformance"
            ],
            "foundation_runtime_adapter_path": WELL_KNOWN_PATHS[
                "foundation_runtime_adapter"
            ],
            "foundation_runtime_router_path": WELL_KNOWN_PATHS[
                "foundation_runtime_router"
            ],
            "foundation_model_deployment_attestation_path": WELL_KNOWN_PATHS[
                "foundation_model_deployment_attestation"
            ],
            "universal_composition_receipt_path": WELL_KNOWN_PATHS[
                "universal_composition_receipt"
            ],
            "universal_composition_settlement_path": WELL_KNOWN_PATHS[
                "universal_composition_settlement"
            ],
            "universal_foundation_model_contract_path": WELL_KNOWN_PATHS[
                "universal_foundation_model_contract"
            ],
            "universal_invocation_guard_path": WELL_KNOWN_PATHS[
                "universal_invocation_guard"
            ],
            "universal_invocation_coverage_path": WELL_KNOWN_PATHS[
                "universal_invocation_coverage"
            ],
            "universal_invocation_witness_path": WELL_KNOWN_PATHS[
                "universal_invocation_witness"
            ],
            "universal_content_credential_path": WELL_KNOWN_PATHS[
                "universal_content_credential"
            ],
            "universal_rdllm_passport_path": WELL_KNOWN_PATHS[
                "universal_rdllm_passport"
            ],
            "universal_adoption_standard_path": WELL_KNOWN_PATHS[
                "universal_adoption_standard"
            ],
            "universal_interop_test_kit_path": WELL_KNOWN_PATHS[
                "universal_interop_test_kit"
            ],
            "universal_context_provenance_bridge_path": WELL_KNOWN_PATHS[
                "universal_context_provenance_bridge"
            ],
            "universal_citation_verification_contract_path": WELL_KNOWN_PATHS[
                "universal_citation_verification_contract"
            ],
            "universal_grounded_reuse_contract_path": WELL_KNOWN_PATHS[
                "universal_grounded_reuse_contract"
            ],
            "universal_training_serving_contract_path": WELL_KNOWN_PATHS[
                "universal_training_serving_contract"
            ],
            "universal_confidential_attribution_audit_path": WELL_KNOWN_PATHS[
                "universal_confidential_attribution_audit"
            ],
            "universal_attribution_authority_control_plane_path": WELL_KNOWN_PATHS[
                "universal_attribution_authority_control_plane"
            ],
            "universal_rdllm_root_path": WELL_KNOWN_PATHS[
                "universal_rdllm_root"
            ],
            "universal_emission_enforcement_gateway_path": WELL_KNOWN_PATHS[
                "universal_emission_enforcement_gateway"
            ],
            "universal_composite_rdllm_profile_path": WELL_KNOWN_PATHS[
                "universal_composite_rdllm_profile"
            ],
            "universal_runtime_conformance_receipt_path": WELL_KNOWN_PATHS[
                "universal_runtime_conformance_receipt"
            ],
            "universal_claim_provenance_envelope_path": WELL_KNOWN_PATHS[
                "universal_claim_provenance_envelope"
            ],
            "universal_provider_wire_protocol_path": WELL_KNOWN_PATHS[
                "universal_provider_wire_protocol"
            ],
            "universal_accountability_audit_trail_path": WELL_KNOWN_PATHS[
                "universal_accountability_audit_trail"
            ],
            "universal_accountability_witness_quorum_path": WELL_KNOWN_PATHS[
                "universal_accountability_witness_quorum"
            ],
            "universal_grounded_reliance_contract_path": WELL_KNOWN_PATHS[
                "universal_grounded_reliance_contract"
            ],
            "universal_reliance_correction_ledger_path": WELL_KNOWN_PATHS[
                "universal_reliance_correction_ledger"
            ],
            "universal_foundation_adoption_kernel_path": WELL_KNOWN_PATHS[
                "universal_foundation_adoption_kernel"
            ],
            "universal_provider_adapter_harness_path": WELL_KNOWN_PATHS[
                "universal_provider_adapter_harness"
            ],
            "universal_provider_drift_sentinel_path": WELL_KNOWN_PATHS[
                "universal_provider_drift_sentinel"
            ],
            "universal_attribution_negotiation_handshake_path": WELL_KNOWN_PATHS[
                "universal_attribution_negotiation_handshake"
            ],
            "universal_negotiated_invocation_enforcement_path": WELL_KNOWN_PATHS[
                "universal_negotiated_invocation_enforcement"
            ],
            "universal_certification_trust_federation_path": WELL_KNOWN_PATHS[
                "universal_certification_trust_federation"
            ],
            "universal_foundation_provider_adoption_pack_path": WELL_KNOWN_PATHS[
                "universal_foundation_provider_adoption_pack"
            ],
            "universal_industry_adoption_root_path": WELL_KNOWN_PATHS[
                "universal_industry_adoption_root"
            ],
            "universal_reference_implementation_distribution_path": WELL_KNOWN_PATHS[
                "universal_reference_implementation_distribution"
            ],
            "universal_live_attribution_proof_path": WELL_KNOWN_PATHS[
                "universal_live_attribution_proof"
            ],
            "universal_foundation_model_release_passport_path": WELL_KNOWN_PATHS[
                "universal_foundation_model_release_passport"
            ],
            "universal_composite_rdllm_contract_path": WELL_KNOWN_PATHS[
                "universal_composite_rdllm_contract"
            ],
            "universal_foundation_provider_binding_matrix_path": WELL_KNOWN_PATHS[
                "universal_foundation_provider_binding_matrix"
            ],
            "universal_provider_conformance_runner_receipt_path": WELL_KNOWN_PATHS[
                "universal_provider_conformance_runner_receipt"
            ],
            "universal_production_invocation_admission_path": WELL_KNOWN_PATHS[
                "universal_production_invocation_admission"
            ],
            "universal_source_grounded_response_receipt_path": WELL_KNOWN_PATHS[
                "universal_source_grounded_response_receipt"
            ],
            "universal_distribution_reliance_passport_path": WELL_KNOWN_PATHS[
                "universal_distribution_reliance_passport"
            ],
            "universal_adversarial_provenance_quorum_path": WELL_KNOWN_PATHS[
                "universal_adversarial_provenance_quorum"
            ],
            "universal_procurement_regulatory_reliance_contract_path": WELL_KNOWN_PATHS[
                "universal_procurement_regulatory_reliance_contract"
            ],
            "universal_provider_onboarding_migration_covenant_path": WELL_KNOWN_PATHS[
                "universal_provider_onboarding_migration_covenant"
            ],
            "universal_model_provider_registry_path": WELL_KNOWN_PATHS[
                "universal_model_provider_registry"
            ],
            "universal_source_footer_enforcement_contract_path": WELL_KNOWN_PATHS[
                "universal_source_footer_enforcement_contract"
            ],
            "universal_provider_catalog_coverage_contract_path": WELL_KNOWN_PATHS[
                "universal_provider_catalog_coverage_contract"
            ],
            "universal_runtime_route_binding_contract_path": WELL_KNOWN_PATHS[
                "universal_runtime_route_binding_contract"
            ],
            "universal_verified_source_footer_contract_path": WELL_KNOWN_PATHS[
                "universal_verified_source_footer_contract"
            ],
            "universal_model_capability_coverage_contract_path": WELL_KNOWN_PATHS[
                "universal_model_capability_coverage_contract"
            ],
            "universal_live_capability_discovery_contract_path": WELL_KNOWN_PATHS[
                "universal_live_capability_discovery_contract"
            ],
            "universal_native_source_annotation_contract_path": WELL_KNOWN_PATHS[
                "universal_native_source_annotation_contract"
            ],
            "universal_claim_evidence_footer_verification_contract_path": (
                WELL_KNOWN_PATHS[
                    "universal_claim_evidence_footer_verification_contract"
                ]
            ),
            "universal_provider_meter_normalization_contract_path": (
                WELL_KNOWN_PATHS[
                    "universal_provider_meter_normalization_contract"
                ]
            ),
            "universal_provider_response_state_normalization_contract_path": (
                WELL_KNOWN_PATHS[
                    "universal_provider_response_state_normalization_contract"
                ]
            ),
            "audit_attestation_path": WELL_KNOWN_PATHS["audit_attestation"],
            "revenue_allocation_report_path": WELL_KNOWN_PATHS[
                "revenue_allocation_report"
            ],
            "finance_ledger_attestation_path": WELL_KNOWN_PATHS[
                "finance_ledger_attestation"
            ],
            "proof_dependency_graph_path": WELL_KNOWN_PATHS[
                "proof_dependency_graph"
            ],
            "publication_monitor_path": WELL_KNOWN_PATHS[
                "publication_monitor"
            ],
            "publication_witness_path": WELL_KNOWN_PATHS[
                "publication_witness"
            ],
            "trust_registry_path": WELL_KNOWN_PATHS[
                "trust_registry"
            ],
            "certification_attestation_path": WELL_KNOWN_PATHS[
                "certification_attestation"
            ],
            "change_policy": "material proof changes require a new manifest_hash",
        },
        "api_contract": {
            "well_known_path": api_contract.get("well_known_path", ""),
            "required_response_format": api_contract.get("required_response_format", ""),
            "endpoint_count": len(api_contract.get("endpoints", [])),
            "endpoints": api_contract.get("endpoints", []),
            "required_headers": api_contract.get("required_headers", []),
            "required_embedded_artifacts": api_contract.get(
                "required_embedded_artifacts", []
            ),
            "api_contract_hash": hash_payload(api_contract),
        },
        "artifact_catalog": catalog,
        "schemas": schemas,
        "verification": {
            "offline_verification_supported": True,
            "minimum_certification_level": "RDLLM-L22",
            "reference_cli_commands": [
                "verify-discovery-manifest",
                "verify-integration-profile",
                "verify-response-envelope",
                "verify-source-verification",
                "verify-answer-card",
                "verify-provider-card",
                "verify-provenance-evaluation",
                "verify-counterfactual-report",
                "verify-media-attribution",
                "verify-model-signal-report",
                "verify-pinpoint-provenance-report",
                "verify-citation-identity-report",
                "verify-attribution-consensus-report",
                "verify-verifier-quorum-report",
                "verify-verifier-accountability-report",
                "verify-receipt-transparency-consistency-report",
                "verify-watchtower-challenge-settlement-report",
                "verify-output-provenance-binding-report",
                "verify-post-release-discovery-report",
                "verify-rights-remediation",
                "verify-semantic-text-attribution",
                "verify-code-attribution-report",
                "verify-claim-verification-report",
                "verify-source-availability-report",
                "verify-evidence-sufficiency-report",
                "verify-counterevidence-report",
                "verify-answer-claim-coverage-report",
                "verify-generation-context-closure-report",
                "verify-source-boundary-report",
                "verify-source-authenticity-report",
                "verify-decision-provenance-report",
                "verify-calibrated-attribution-report",
                "verify-attribution-exchange",
                "verify-conformance-vector-pack",
                "verify-federation-handshake",
                "verify-attribution-capsule",
                "verify-release-gate",
                "verify-proof-carrying-response",
                "verify-serving-gateway-report",
                "verify-streaming-attribution-manifest",
                "verify-conversation-attribution-ledger",
                "verify-agent-tool-attribution-ledger",
                "verify-creator-license-contract",
                "verify-source-confidence-report",
                "verify-citation-footer-contract",
                "verify-private-audit-challenge",
                "verify-transitive-attribution-report",
                "verify-clearinghouse-report",
                "verify-remittance-report",
                "verify-payment-execution-report",
                "verify-payment-rail-attestation",
                "verify-creator-payout-receipts",
                "verify-rendered-attribution-audit",
                "verify-training-memory-provenance",
                "verify-evidence-locked-generation",
                "verify-emission-evidence-enforcement",
                "verify-live-emission-witness",
                "verify-live-emission-transparency",
                "verify-attested-runtime",
                "verify-claim-source-attribution-report",
                "verify-evidence-utility-attribution-report",
                "verify-parametric-memory-attribution-report",
                "verify-style-influence-attribution-report",
                "verify-model-lineage-attribution-report",
                "verify-black-box-model-provenance-report",
                "verify-attribution-dispute-adjudication-report",
                "verify-audit-attestation",
                "verify-valuation-method-audit-report",
                "verify-evidence-region-binding-report",
                "verify-source-access-lease-report",
                "verify-content-protocol-ingestion-report",
                "verify-grounded-source-footer",
                "verify-source-footer-delivery",
                "verify-foundation-api-profile",
                "verify-client-attribution-enforcement",
                "verify-persistent-memory-provenance",
                "verify-private-reasoning-attribution",
                "verify-post-training-signal-provenance",
                "verify-attribution-bom",
                "verify-creator-attribution-audit-index",
                "verify-creator-attribution-audit-federation",
                "verify-creator-audit-federation-transparency",
                "verify-creator-audit-transparency-monitor",
                "verify-creator-audit-private-watch",
                "verify-consent-revocation-propagation",
                "verify-evidence-force-calibration",
                "verify-warranted-source-footer",
                "verify-universal-composition-receipt",
                "verify-universal-composition-settlement",
                "verify-universal-foundation-model-contract",
                "verify-universal-invocation-guard",
                "verify-universal-invocation-coverage",
                "verify-universal-invocation-witness",
                "verify-universal-content-credential",
                "verify-universal-rdllm-passport",
                "verify-universal-adoption-standard",
                "verify-universal-confidential-attribution-audit",
                "verify-universal-attribution-authority-control-plane",
                "verify-universal-rdllm-root",
                "verify-universal-emission-enforcement-gateway",
                "verify-universal-composite-rdllm-profile",
                "verify-universal-runtime-conformance-receipt",
                "verify-universal-claim-provenance-envelope",
                "verify-universal-reliance-correction-ledger",
                "verify-universal-foundation-adoption-kernel",
                "verify-universal-provider-adapter-harness",
                "verify-revenue-allocation-report",
                "verify-finance-ledger-attestation",
                "verify-proof-dependency-graph",
                "verify-publication-monitor",
                "verify-publication-witness",
                "verify-trust-registry",
                "verify-certification-attestation",
                "verify-assurance-bundle",
                "conformance",
            ],
            "required_failure_modes": [
                "missing_well_known_surface",
                "artifact_hash_drift",
                "api_contract_drift",
                "profile_readiness_regression",
                "certification_regression",
                "assurance_publication_gap",
                "runtime_federation_downgrade",
                "portable_capsule_marker_loss",
                "response_release_gate_failure",
                "proof_carrying_response_failure",
                "serving_gateway_egress_failure",
                "streaming_attribution_chunk_commitment_failure",
                "conversation_attribution_continuity_failure",
                "agent_tool_attribution_trajectory_failure",
                "pinpoint_provenance_antidocument_or_fact_support_failure",
                "citation_identity_or_metadata_swap_failure",
                "attribution_consensus_quorum_or_conflict_failure",
                "verifier_quorum_or_signature_failure",
                "verifier_accountability_bond_or_conflict_failure",
                "receipt_transparency_consistency_or_split_view_failure",
                "watchtower_challenge_quorum_or_settlement_failure",
                "output_provenance_binding_or_copy_survival_failure",
                "post_release_discovery_or_late_artifact_publication_failure",
                "creator_license_contract_drift",
                "source_confidence_drift",
                "citation_footer_contract_drift",
                "source_availability_or_archive_failure",
                "evidence_sufficiency_or_decoy_failure",
                "counterevidence_adjudication_failure",
                "answer_claim_coverage_failure",
                "generation_context_closure_failure",
                "source_boundary_integrity_failure",
                "source_authenticity_or_poisoning_failure",
                "decision_provenance_influence_graph_failure",
                "calibrated_attribution_confidence_failure",
                "private_audit_challenge_replay_or_opening_failure",
                "transitive_attribution_marker_or_body_hash_failure",
                "clearinghouse_duplicate_or_conservation_failure",
                "remittance_instruction_or_privacy_failure",
                "payment_execution_or_processor_reconciliation_failure",
                "payment_rail_signature_or_registry_failure",
                "creator_payout_receipt_mismatch_or_privacy_failure",
                "rendered_markdown_attribution_or_footer_failure",
                "training_memory_provenance_or_hidden_memorization_failure",
                "evidence_lock_or_post_hoc_citation_failure",
                "emission_evidence_enforcement_or_unlocked_chunk_failure",
                "live_emission_witness_quorum_or_timing_failure",
                "live_emission_transparency_inclusion_or_split_view_failure",
                "attested_runtime_measurement_or_quote_failure",
                "claim_source_attribution_footer_or_visual_anchor_failure",
                "evidence_utility_intervention_or_context_drift_failure",
                "parametric_memory_training_or_probe_attribution_failure",
            "style_influence_license_copy_or_decoy_failure",
            "model_lineage_training_distillation_or_synthetic_disclosure_failure",
            "black_box_model_provenance_challenge_or_false_positive_control_failure",
            "attribution_dispute_quorum_appeal_or_escrow_failure",
            "post_adjudication_adjustment_conservation_or_netting_failure",
            "residual_corpus_royalty_conservation_or_rights_failure",
            "valuation_method_audit_benchmark_or_privacy_failure",
            "evidence_region_binding_location_or_wrong_region_failure",
            "source_access_lease_or_access_log_failure",
            "content_protocol_ingestion_or_external_rights_signal_failure",
            "citation_reliance_or_post_hoc_footer_failure",
            "license_transaction_or_dynamic_authorization_failure",
                "grounded_source_footer_or_user_proof_handle_failure",
                "source_footer_delivery_or_egress_metadata_failure",
                "foundation_api_profile_or_minimum_metadata_failure",
                "client_attribution_enforcement_or_render_policy_failure",
                "persistent_memory_provenance_or_carry_forward_failure",
                "private_reasoning_attribution_or_hidden_source_failure",
                "post_training_signal_provenance_or_signal_lineage_failure",
                "attribution_bom_or_notice_carry_forward_failure",
                "creator_attribution_audit_index_or_creator_query_failure",
                "creator_attribution_audit_federation_or_cross_provider_query_failure",
                "creator_audit_federation_transparency_or_split_view_failure",
                "consent_revocation_propagation_or_stale_rights_surface_failure",
            "evidence_force_calibration_or_overclaiming_failure",
            "warranted_source_footer_or_visible_warrant_label_failure",
            "source_origin_lineage_or_synthetic_laundering_failure",
            "evidence_preview_footer_or_missing_user_inspectable_source_failure",
            "evidence_locator_manifest_or_unresolvable_preview_failure",
            "citation_url_health_or_fabricated_locator_failure",
            "composite_foundation_adapter_or_native_api_mapping_failure",
            "foundation_provider_conformance_or_fixture_failure",
            "foundation_runtime_adapter_or_native_response_failure",
            "foundation_runtime_router_or_provider_fallback_failure",
            "foundation_model_deployment_attestation_or_backend_substitution_failure",
            "universal_composition_receipt_or_segment_merge_failure",
            "universal_composition_settlement_or_creator_pool_clearing_failure",
            "universal_foundation_model_contract_or_provider_neutral_adoption_failure",
            "universal_invocation_guard_or_raw_provider_call_failure",
            "universal_invocation_coverage_or_meter_reconciliation_failure",
            "universal_invocation_witness_or_nonrepudiation_failure",
            "universal_content_credential_or_portable_provenance_failure",
            "universal_rdllm_passport_or_composite_adoption_failure",
            "universal_adoption_standard_or_procurement_adoption_failure",
            "universal_interop_test_kit_or_sdk_conformance_failure",
            "universal_context_provenance_bridge_or_runtime_context_failure",
            "universal_citation_verification_contract_or_unverified_citation_failure",
            "universal_grounded_reuse_contract_or_unmetered_cache_reuse_failure",
            "universal_training_serving_contract_or_training_serving_attribution_failure",
            "universal_confidential_attribution_audit_or_private_evidence_failure",
            "universal_attribution_authority_control_plane_or_runtime_authority_failure",
            "universal_rdllm_root_or_composite_root_failure",
            "universal_emission_enforcement_gateway_or_runtime_emission_failure",
            "universal_composite_rdllm_profile_or_provider_adoption_failure",
            "universal_runtime_conformance_receipt_or_deployment_runtime_failure",
            "universal_claim_provenance_envelope_or_posthoc_citation_failure",
            "universal_provider_wire_protocol_or_transport_metadata_failure",
            "universal_accountability_audit_trail_or_unreplayable_trace_failure",
            "universal_accountability_witness_quorum_or_split_view_failure",
            "universal_grounded_reliance_contract_or_untrusted_footer_failure",
            "universal_reliance_correction_ledger_or_stale_reliance_failure",
            "universal_foundation_adoption_kernel_or_provider_api_adoption_failure",
            "universal_provider_adapter_harness_or_native_normalization_failure",
            "universal_provider_drift_sentinel_or_stale_provider_change_failure",
            "universal_attribution_negotiation_handshake_or_unnegotiated_request_failure",
            "universal_negotiated_invocation_enforcement_or_invocation_bypass_failure",
            "universal_certification_trust_federation_or_untrusted_conformance_claim_failure",
            "universal_foundation_provider_adoption_pack_or_nonportable_provider_adoption_failure",
            "universal_industry_adoption_root_or_unpublished_root_failure",
            "universal_reference_implementation_distribution_or_unsigned_distribution_failure",
            "universal_live_attribution_proof_or_decorative_source_failure",
            "universal_foundation_model_release_passport_or_unbound_model_release_failure",
            "universal_composite_rdllm_contract_or_fragmented_claim_failure",
            "universal_foundation_provider_binding_matrix_or_unbound_provider_route_failure",
            "universal_provider_conformance_runner_receipt_or_unreplayed_provider_route_failure",
            "universal_production_invocation_admission_or_unadmitted_live_provider_call_failure",
            "universal_source_grounded_response_receipt_or_ungrounded_response_footer_failure",
            "universal_distribution_reliance_passport_or_stripped_distributed_output_failure",
            "universal_adversarial_provenance_quorum_or_spoofed_provenance_failure",
            "universal_procurement_regulatory_reliance_contract_or_unbound_provider_terms_failure",
            "universal_provider_onboarding_migration_covenant_or_unmigrated_provider_route_failure",
            "universal_model_provider_registry_or_unregistered_model_route_failure",
            "universal_source_footer_enforcement_contract_or_unfootnoted_answer_failure",
            "universal_provider_catalog_coverage_contract_or_uncovered_catalog_model_failure",
            "universal_runtime_route_binding_contract_or_unbound_runtime_model_failure",
            "universal_verified_source_footer_contract_or_unverified_source_footer_failure",
            "universal_model_capability_coverage_contract_or_uncovered_model_capability_failure",
            "universal_live_capability_discovery_contract_or_stale_capability_source_failure",
            "universal_native_source_annotation_contract_or_dropped_native_citation_failure",
            "universal_claim_evidence_footer_verification_contract_or_misleading_citation_failure",
            "universal_provider_meter_normalization_contract_or_unmetered_provider_usage_failure",
            "universal_provider_response_state_normalization_contract_or_unsafe_terminal_state_failure",
            "third_party_audit_attestation_failure",
                "usage_revenue_allocation_failure",
                "finance_ledger_attestation_failure",
                "proof_dependency_cycle_or_replay_order_failure",
                "publication_monitor_regression_or_append_only_failure",
                "publication_witness_quorum_or_equivocation_failure",
                "trust_registry_key_revocation_or_signature_failure",
                "certification_attestation_signature_or_report_hash_failure",
                "generated_code_source_or_license_attribution_failure",
                "ownership_claim_verification_or_escrow_failure",
            ],
        },
        "readiness_checks": readiness_checks,
        "summary": {
            "status": "ready" if all(readiness_checks.values()) else "failed",
            "highest_level": certification_summary.get("highest_level", ""),
            "artifact_count": len(catalog),
            "required_artifact_count": len(
                [entry for entry in catalog if entry["required"]]
            ),
            "schema_count": len(schemas),
            "endpoint_count": len(api_contract.get("endpoints", [])),
            "public_surface_count": len(public_surfaces),
            "provider_public_surface_count": len(public_surfaces),
            "integration_public_surface_count": len(
                integration_profile.get("public_surfaces", {})
            ),
            "assurance_root": assurance_bundle.get("summary", {}).get("root", ""),
            "offline_verification_supported": True,
        },
        "privacy": {
            "private_ledger_disclosed": False,
            "private_source_corpus_disclosed": False,
            "private_prompt_payload_disclosed": False,
            "artifact_payloads_embedded": False,
            "manifest_uses_hashes_paths_and_contract_metadata": True,
        },
    }
    manifest["manifest_hash"] = hash_payload(_hashable_manifest(manifest))
    manifest["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_manifest(manifest), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return manifest


def validate_discovery_manifest_shape(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "manifest_version",
        "issuer",
        "created_at",
        "provider",
        "discovery",
        "api_contract",
        "artifact_catalog",
        "schemas",
        "verification",
        "readiness_checks",
        "summary",
        "privacy",
        "manifest_hash",
        "signature",
    )
    for key in required:
        if key not in manifest:
            errors.append(f"missing discovery manifest field: {key}")
    if errors:
        return errors
    if manifest.get("manifest_version") != DISCOVERY_MANIFEST_VERSION:
        errors.append("discovery manifest version is unsupported")
    if manifest.get("discovery", {}).get("well_known_path") != DISCOVERY_WELL_KNOWN_PATH:
        errors.append("discovery manifest well-known path is incorrect")
    names = {entry.get("name", "") for entry in manifest.get("artifact_catalog", [])}
    for name in REQUIRED_ARTIFACTS:
        if name not in names:
            errors.append(f"missing discovery artifact: {name}")
    if "discovery_manifest" not in manifest.get("schemas", {}):
        errors.append("missing discovery manifest schema")
    return errors


def verify_discovery_manifest(
    manifest: dict[str, Any],
    *,
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    integration_profile: dict[str, Any],
    response_envelope: dict[str, Any],
    assurance_bundle: dict[str, Any],
    training_summary: dict[str, Any] | None = None,
    provenance_evaluation_report: dict[str, Any] | None = None,
    counterfactual_report: dict[str, Any] | None = None,
    media_attribution_report: dict[str, Any] | None = None,
    model_signal_report: dict[str, Any] | None = None,
    pinpoint_provenance_report: dict[str, Any] | None = None,
    citation_identity_report: dict[str, Any] | None = None,
    attribution_consensus_report: dict[str, Any] | None = None,
    verifier_quorum_report: dict[str, Any] | None = None,
    verifier_accountability_report: dict[str, Any] | None = None,
    receipt_transparency_consistency_report: dict[str, Any] | None = None,
    watchtower_challenge_settlement_report: dict[str, Any] | None = None,
    output_provenance_binding_report: dict[str, Any] | None = None,
    rights_remediation_report: dict[str, Any] | None = None,
    semantic_text_attribution_report: dict[str, Any] | None = None,
    code_attribution_report: dict[str, Any] | None = None,
    claim_verification_report: dict[str, Any] | None = None,
    source_availability_report: dict[str, Any] | None = None,
    evidence_sufficiency_report: dict[str, Any] | None = None,
    counterevidence_report: dict[str, Any] | None = None,
    answer_claim_coverage_report: dict[str, Any] | None = None,
    generation_context_closure_report: dict[str, Any] | None = None,
    source_boundary_report: dict[str, Any] | None = None,
    source_authenticity_report: dict[str, Any] | None = None,
    decision_provenance_report: dict[str, Any] | None = None,
    calibrated_attribution_report: dict[str, Any] | None = None,
    streaming_attribution_manifest: dict[str, Any] | None = None,
    conversation_attribution_ledger: dict[str, Any] | None = None,
    agent_tool_attribution_ledger: dict[str, Any] | None = None,
    creator_license_contract: dict[str, Any] | None = None,
    source_confidence_report: dict[str, Any] | None = None,
    citation_footer_contract: dict[str, Any] | None = None,
    private_audit_challenge: dict[str, Any] | None = None,
    transitive_attribution_report: dict[str, Any] | None = None,
    clearinghouse_report: dict[str, Any] | None = None,
    remittance_report: dict[str, Any] | None = None,
    payment_execution_report: dict[str, Any] | None = None,
    payment_rail_attestation: dict[str, Any] | None = None,
    creator_payout_receipt_report: dict[str, Any] | None = None,
    rendered_attribution_audit: dict[str, Any] | None = None,
    training_memory_provenance: dict[str, Any] | None = None,
    post_training_signal_provenance: dict[str, Any] | None = None,
    evidence_locked_generation: dict[str, Any] | None = None,
    emission_evidence_enforcement: dict[str, Any] | None = None,
    live_emission_witness: dict[str, Any] | None = None,
    live_emission_transparency: dict[str, Any] | None = None,
    attested_runtime: dict[str, Any] | None = None,
    claim_source_attribution_report: dict[str, Any] | None = None,
    evidence_utility_attribution_report: dict[str, Any] | None = None,
    parametric_memory_attribution_report: dict[str, Any] | None = None,
    style_influence_attribution_report: dict[str, Any] | None = None,
    model_lineage_attribution_report: dict[str, Any] | None = None,
    black_box_model_provenance_report: dict[str, Any] | None = None,
    attribution_dispute_adjudication_report: dict[str, Any] | None = None,
    post_adjudication_settlement_adjustment_report: dict[str, Any] | None = None,
    residual_corpus_royalty_report: dict[str, Any] | None = None,
    valuation_method_audit_report: dict[str, Any] | None = None,
    evidence_region_binding_report: dict[str, Any] | None = None,
    source_access_lease_report: dict[str, Any] | None = None,
    content_protocol_ingestion_report: dict[str, Any] | None = None,
    citation_reliance_receipt: dict[str, Any] | None = None,
    license_transaction_receipt: dict[str, Any] | None = None,
    grounded_source_footer: dict[str, Any] | None = None,
    source_footer_delivery: dict[str, Any] | None = None,
    deep_research_citation_audit: dict[str, Any] | None = None,
    source_freshness_audit: dict[str, Any] | None = None,
    royalty_abuse_audit: dict[str, Any] | None = None,
    consent_revocation_propagation: dict[str, Any] | None = None,
    evidence_force_calibration: dict[str, Any] | None = None,
    warranted_source_footer: dict[str, Any] | None = None,
    source_origin_lineage: dict[str, Any] | None = None,
    evidence_preview_footer: dict[str, Any] | None = None,
    evidence_locator_manifest: dict[str, Any] | None = None,
    citation_url_health: dict[str, Any] | None = None,
    foundation_api_profile: dict[str, Any] | None = None,
    composite_foundation_adapter: dict[str, Any] | None = None,
    foundation_provider_conformance: dict[str, Any] | None = None,
    foundation_runtime_adapter: dict[str, Any] | None = None,
    foundation_runtime_router: dict[str, Any] | None = None,
    foundation_model_deployment_attestation: dict[str, Any] | None = None,
    universal_composition_receipt: dict[str, Any] | None = None,
    universal_composition_settlement: dict[str, Any] | None = None,
    universal_foundation_model_contract: dict[str, Any] | None = None,
    universal_invocation_guard: dict[str, Any] | None = None,
    universal_invocation_coverage: dict[str, Any] | None = None,
    universal_invocation_witness: dict[str, Any] | None = None,
    universal_content_credential: dict[str, Any] | None = None,
    universal_rdllm_passport: dict[str, Any] | None = None,
    universal_adoption_standard: dict[str, Any] | None = None,
    universal_interop_test_kit: dict[str, Any] | None = None,
    universal_context_provenance_bridge: dict[str, Any] | None = None,
    universal_citation_verification_contract: dict[str, Any] | None = None,
    universal_grounded_reuse_contract: dict[str, Any] | None = None,
    universal_training_serving_contract: dict[str, Any] | None = None,
    universal_confidential_attribution_audit: dict[str, Any] | None = None,
    universal_attribution_authority_control_plane: dict[str, Any] | None = None,
    universal_foundation_provider_binding_matrix: dict[str, Any] | None = None,
    universal_provider_conformance_runner_receipt: dict[str, Any] | None = None,
    universal_production_invocation_admission: dict[str, Any] | None = None,
    universal_source_grounded_response_receipt: dict[str, Any] | None = None,
    universal_distribution_reliance_passport: dict[str, Any] | None = None,
    universal_adversarial_provenance_quorum: dict[str, Any] | None = None,
    universal_procurement_regulatory_reliance_contract: dict[str, Any] | None = None,
    universal_provider_onboarding_migration_covenant: dict[str, Any] | None = None,
    universal_model_provider_registry: dict[str, Any] | None = None,
    universal_source_footer_enforcement_contract: dict[str, Any] | None = None,
    universal_provider_catalog_coverage_contract: dict[str, Any] | None = None,
    universal_runtime_route_binding_contract: dict[str, Any] | None = None,
    universal_verified_source_footer_contract: dict[str, Any] | None = None,
    universal_model_capability_coverage_contract: dict[str, Any] | None = None,
    universal_live_capability_discovery_contract: dict[str, Any] | None = None,
    universal_native_source_annotation_contract: dict[str, Any] | None = None,
    universal_claim_evidence_footer_verification_contract: dict[str, Any] | None = None,
    universal_provider_meter_normalization_contract: dict[str, Any] | None = None,
    universal_provider_response_state_normalization_contract: dict[str, Any] | None = None,
    revenue_allocation_report: dict[str, Any] | None = None,
    finance_ledger_attestation: dict[str, Any] | None = None,
    proof_dependency_graph: dict[str, Any] | None = None,
    publication_monitor: dict[str, Any] | None = None,
    publication_witness: dict[str, Any] | None = None,
    trust_registry: dict[str, Any] | None = None,
    certification_attestation: dict[str, Any] | None = None,
    strict_artifact_catalog: bool = True,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a discovery manifest against public RDLLM provider artifacts."""

    errors = validate_discovery_manifest_shape(manifest)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_manifest(manifest))
    if expected_hash != manifest.get("manifest_hash"):
        errors.append("discovery manifest hash is not reproducible")

    profile_assurance = (
        assurance_bundle
        if integration_profile.get("bound_artifacts", {}).get("assurance_bundle_hash")
        else None
    )
    profile_certification_attestation = (
        certification_attestation
        if integration_profile.get("bound_artifacts", {}).get(
            "certification_attestation_hash"
        )
        else None
    )
    errors.extend(
        f"integration profile: {error}"
        for error in verify_integration_profile(
            integration_profile,
            provider_card=provider_card,
            certification_report=certification_report,
            response_envelope=response_envelope,
            assurance_bundle=profile_assurance,
            certification_attestation=profile_certification_attestation,
            signing_secret=signing_secret,
        )
    )
    errors.extend(
        f"assurance bundle: {error}"
        for error in validate_assurance_bundle_shape(assurance_bundle)
    )

    expected = make_discovery_manifest(
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
        universal_foundation_provider_binding_matrix=universal_foundation_provider_binding_matrix,
        universal_provider_conformance_runner_receipt=(
            universal_provider_conformance_runner_receipt
        ),
        universal_production_invocation_admission=universal_production_invocation_admission,
        universal_source_grounded_response_receipt=(
            universal_source_grounded_response_receipt
        ),
        universal_distribution_reliance_passport=universal_distribution_reliance_passport,
        universal_adversarial_provenance_quorum=universal_adversarial_provenance_quorum,
        universal_procurement_regulatory_reliance_contract=(
            universal_procurement_regulatory_reliance_contract
        ),
        universal_provider_onboarding_migration_covenant=(
            universal_provider_onboarding_migration_covenant
        ),
        universal_model_provider_registry=universal_model_provider_registry,
        universal_source_footer_enforcement_contract=(
            universal_source_footer_enforcement_contract
        ),
        universal_provider_catalog_coverage_contract=(
            universal_provider_catalog_coverage_contract
        ),
        universal_runtime_route_binding_contract=(
            universal_runtime_route_binding_contract
        ),
        universal_verified_source_footer_contract=(
            universal_verified_source_footer_contract
        ),
        universal_model_capability_coverage_contract=(
            universal_model_capability_coverage_contract
        ),
        universal_live_capability_discovery_contract=(
            universal_live_capability_discovery_contract
        ),
        universal_native_source_annotation_contract=(
            universal_native_source_annotation_contract
        ),
        universal_claim_evidence_footer_verification_contract=(
            universal_claim_evidence_footer_verification_contract
        ),
        universal_provider_meter_normalization_contract=(
            universal_provider_meter_normalization_contract
        ),
        universal_provider_response_state_normalization_contract=(
            universal_provider_response_state_normalization_contract
        ),
        revenue_allocation_report=revenue_allocation_report,
        finance_ledger_attestation=finance_ledger_attestation,
        proof_dependency_graph=proof_dependency_graph,
        publication_monitor=publication_monitor,
        publication_witness=publication_witness,
        trust_registry=trust_registry,
        certification_attestation=certification_attestation,
        issuer=manifest.get("issuer", DEFAULT_ISSUER),
        created_at=manifest.get("created_at", ""),
        signing_secret=signing_secret,
    )
    if strict_artifact_catalog:
        for key in (
            "provider",
            "discovery",
            "api_contract",
            "artifact_catalog",
            "schemas",
            "verification",
            "readiness_checks",
            "summary",
            "privacy",
        ):
            if expected.get(key) != manifest.get(key):
                errors.append(f"discovery manifest {key} does not match artifacts")
        if expected.get("manifest_hash") != manifest.get("manifest_hash"):
            errors.append("discovery manifest hash does not match artifacts")
    else:
        for key in (
            "provider",
            "discovery",
            "api_contract",
            "schemas",
            "verification",
            "privacy",
        ):
            if expected.get(key) != manifest.get(key):
                errors.append(f"discovery manifest {key} does not match artifacts")
        manifest_catalog = {
            entry.get("name", ""): entry
            for entry in manifest.get("artifact_catalog", [])
        }
        for entry in expected.get("artifact_catalog", []):
            if manifest_catalog.get(entry.get("name", "")) != entry:
                errors.append(
                    f"discovery manifest missing matching artifact entry: {entry.get('name', '')}"
                )
        manifest_checks = manifest.get("readiness_checks", {})
        for check, passed in expected.get("readiness_checks", {}).items():
            if manifest_checks.get(check) != passed:
                errors.append(f"discovery manifest readiness check drift: {check}")
        if expected.get("summary", {}).get("highest_level") != manifest.get(
            "summary", {}
        ).get("highest_level"):
            errors.append("discovery manifest highest level does not match artifacts")

    if manifest.get("summary", {}).get("status") != "ready":
        errors.append("discovery manifest status is not ready")
    for check, passed in manifest.get("readiness_checks", {}).items():
        if passed is not True:
            errors.append(f"discovery readiness check failed: {check}")

    signature = manifest.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_manifest(manifest), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("discovery manifest is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("discovery manifest signature is invalid")

    return errors
