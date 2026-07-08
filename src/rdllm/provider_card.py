"""Provider-level attribution disclosure cards."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from rdllm.models import UsageEvent
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload

PROVIDER_CARD_VERSION = "rdllm-provider-attribution-card/v1"


def _events_from_ledger(ledger_data: dict[str, Any]) -> list[UsageEvent]:
    return [UsageEvent.from_dict(item) for item in ledger_data.get("events", [])]


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000001")))


def _certification_hash(report: dict[str, Any] | None) -> str:
    if not report:
        return ""
    return str(report.get("report_hash") or hash_payload(report))


def _certification_hash_errors(report: dict[str, Any] | None) -> list[str]:
    if not report:
        return []
    expected = dict(report)
    declared = expected.pop("report_hash", "")
    if declared and hash_payload(expected) != declared:
        return ["certification report hash is not reproducible"]
    return []


def _round_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 1.0
    return round(numerator / denominator, 8)


def _level_number(level: str) -> int:
    try:
        return int(level.rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _private_strings(events: list[UsageEvent]) -> list[str]:
    values: list[str] = []
    for event in events:
        values.extend([event.prompt, event.output, event.answer_text])
        values.extend(source.quote for source in event.source_references)
        values.extend(claim.evidence_text for claim in event.claim_support)
    return [value for value in values if value]


def _ledger_summary(events: list[UsageEvent]) -> dict[str, Any]:
    total_gross = sum((event.gross_revenue for event in events), Decimal("0"))
    total_creator_pool = sum((event.creator_pool for event in events), Decimal("0"))
    creators = set()
    works = set()
    source_access_count = 0
    source_reference_count = 0
    claim_support_count = 0
    royalty_share_count = 0
    paid_source_count = 0
    escrow_share_count = 0
    gap_summary: defaultdict[str, int] = defaultdict(int)
    quality_scores: list[float] = []
    verdicts: defaultdict[str, int] = defaultdict(int)

    for event in events:
        source_access_count += len(event.source_accesses)
        source_reference_count += len(event.source_references)
        claim_support_count += len(event.claim_support)
        royalty_share_count += len(event.royalty_shares)
        for source in event.source_references:
            creators.add(source.creator_id)
            works.add(source.work_id)
        for share in event.royalty_shares:
            if share.creator_id.endswith("_escrow") or share.chunk_id.startswith("escrow:"):
                escrow_share_count += 1
            elif share.payout > Decimal("0"):
                paid_source_count += 1
                creators.add(share.creator_id)
                works.add(share.work_id)
        quality = event.grounding_quality or {}
        if quality.get("overall_score") is not None:
            quality_scores.append(float(quality["overall_score"]))
        if quality.get("verdict"):
            verdicts[str(quality["verdict"])] += 1
        for key, value in (event.attribution_gap or {}).get("summary", {}).items():
            if isinstance(value, int):
                gap_summary[key] += value

    gap_issue_count = (
        gap_summary["consumed_without_credit_count"]
        + gap_summary["paid_hidden_count"]
        + gap_summary["cited_without_access_count"]
    )
    access_record_count = gap_summary.get("access_record_count", source_access_count)
    accounted_access_count = max(0, access_record_count - gap_issue_count)
    average_quality = (
        round(sum(quality_scores) / len(quality_scores), 8) if quality_scores else None
    )

    return {
        "event_count": len(events),
        "gross_revenue_total": _money(total_gross),
        "creator_pool_total": _money(total_creator_pool),
        "creator_count": len(creators),
        "work_count": len(works),
        "source_access_count": source_access_count,
        "source_reference_count": source_reference_count,
        "claim_support_count": claim_support_count,
        "royalty_share_count": royalty_share_count,
        "paid_source_count": paid_source_count,
        "escrow_share_count": escrow_share_count,
        "gap_issue_count": gap_issue_count,
        "accounted_access_count": accounted_access_count,
        "accounted_access_ratio": _round_ratio(accounted_access_count, access_record_count),
        "average_grounding_quality": average_quality,
        "grounding_verdicts": dict(sorted(verdicts.items())),
    }


def _evidence_roots(ledger_data: dict[str, Any], events: list[UsageEvent]) -> dict[str, str]:
    return {
        "ledger_root": hash_payload(ledger_data),
        "event_root": hash_payload([event.event_hash for event in events]),
        "source_access_root": hash_payload(
            [access.to_dict() for event in events for access in event.source_accesses]
        ),
        "source_reference_root": hash_payload(
            [source.to_dict() for event in events for source in event.source_references]
        ),
        "claim_support_root": hash_payload(
            [claim.to_dict() for event in events for claim in event.claim_support]
        ),
        "royalty_share_root": hash_payload(
            [share.to_dict() for event in events for share in event.royalty_shares]
        ),
        "grounding_quality_root": hash_payload(
            [event.grounding_quality for event in events]
        ),
        "attribution_gap_root": hash_payload([event.attribution_gap for event in events]),
    }


def _hashable_card(card: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in card.items()
        if key not in {"card_hash", "signature"}
    }


def _certification_summary(report: dict[str, Any] | None) -> dict[str, Any]:
    summary = dict((report or {}).get("summary", {}))
    return {
        "certification_version": (report or {}).get("certification_version", ""),
        "suite": (report or {}).get("suite", ""),
        "report_hash": _certification_hash(report),
        "status": summary.get("status", ""),
        "highest_level": summary.get("highest_level", ""),
        "case_count": int(summary.get("case_count", 0) or 0),
        "passed": int(summary.get("passed", 0) or 0),
        "failed": int(summary.get("failed", 0) or 0),
        "score": float(summary.get("score", 0.0) or 0.0),
    }


def make_provider_attribution_card(
    ledger_data: dict[str, Any],
    *,
    certification_report: dict[str, Any] | None = None,
    issuer: str = DEFAULT_ISSUER,
    provider: str = "provider:unspecified",
    model_id: str = "model:unspecified",
    model_version: str = "unknown",
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed provider-level attribution disclosure card."""

    events = _events_from_ledger(ledger_data)
    card = {
        "card_version": PROVIDER_CARD_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "provider": {
            "id": provider,
            "model_id": model_id,
            "model_version": model_version,
        },
        "certification": _certification_summary(certification_report),
        "supported_evidence_channels": {
            "retrieval": True,
            "text_match": True,
            "claim_support": True,
            "source_access_trace": True,
            "training_value_prior": True,
            "provenance_benchmark": True,
            "counterfactual_ablation": True,
            "model_internal_signal": True,
            "pinpoint_provenance": True,
            "citation_identity": True,
            "attribution_consensus": True,
            "independent_verifier_quorum": True,
            "bonded_verifier_accountability": True,
            "receipt_transparency_consistency": True,
            "watchtower_challenge_settlement": True,
            "output_provenance_binding": True,
            "post_release_discovery": True,
            "multimodal_source_attribution": True,
            "post_publication_rights_remediation": True,
            "semantic_text_attribution": True,
            "code_attribution": True,
            "pre_settlement_claim_verification": True,
            "source_availability_report": True,
            "evidence_sufficiency_report": True,
            "counterevidence_report": True,
            "answer_claim_coverage_report": True,
            "generation_context_closure_report": True,
            "source_boundary_report": True,
            "source_authenticity_report": True,
            "decision_provenance_report": True,
            "calibrated_attribution_report": True,
            "release_grounding_closure": True,
            "cross_provider_attribution_exchange": True,
            "portable_conformance_vectors": True,
            "runtime_federation_handshake": True,
            "portable_attribution_capsule": True,
            "response_release_gate": True,
            "proof_carrying_response": True,
            "serving_gateway_report": True,
            "streaming_attribution_manifest": True,
            "conversation_attribution_ledger": True,
            "agent_tool_attribution_ledger": True,
            "creator_license_contract": True,
            "source_confidence_report": True,
            "citation_footer_contract": True,
            "private_audit_challenge": True,
            "transitive_attribution_flow": True,
            "cross_provider_royalty_clearing": True,
            "verifiable_remittance_instructions": True,
            "payment_execution_attestation": True,
            "payment_rail_authenticity": True,
            "creator_payout_receipts": True,
            "rendered_attribution_audit": True,
            "training_memory_provenance": True,
            "evidence_locked_generation": True,
            "emission_evidence_enforcement": True,
            "live_emission_witness": True,
            "live_emission_transparency": True,
            "attested_attribution_runtime": True,
            "claim_source_attribution": True,
            "causal_evidence_utility_attribution": True,
            "parametric_memory_attribution": True,
            "style_influence_attribution": True,
            "model_lineage_attribution": True,
            "black_box_model_provenance": True,
            "attribution_dispute_adjudication": True,
            "post_adjudication_settlement_adjustment": True,
            "residual_corpus_royalty": True,
            "valuation_method_audit": True,
            "evidence_region_binding": True,
            "source_access_lease": True,
            "content_protocol_ingestion": True,
            "citation_reliance_receipt": True,
            "license_transaction_receipt": True,
            "grounded_source_footer": True,
            "source_footer_delivery": True,
            "foundation_api_profile": True,
            "client_attribution_enforcement": True,
            "persistent_memory_provenance": True,
            "private_reasoning_attribution": True,
            "post_training_signal_provenance": True,
            "attribution_bom": True,
            "creator_attribution_audit_index": True,
            "creator_attribution_audit_federation": True,
            "creator_attribution_audit_federation_transparency": True,
            "creator_audit_transparency_monitor": True,
            "creator_audit_private_watch": True,
            "deep_research_citation_audit": True,
            "source_freshness_audit": True,
            "royalty_abuse_audit": True,
            "consent_revocation_propagation": True,
            "evidence_force_calibration": True,
            "warranted_source_footer": True,
            "source_origin_lineage": True,
            "evidence_preview_footer": True,
            "evidence_locator_manifest": True,
            "citation_url_health": True,
            "composite_foundation_adapter": True,
            "foundation_provider_conformance": True,
            "foundation_runtime_adapter": True,
            "foundation_runtime_router": True,
            "foundation_model_deployment_attestation": True,
            "universal_composition_receipt": True,
            "universal_composition_settlement": True,
            "universal_foundation_model_contract": True,
            "universal_invocation_guard": True,
            "universal_invocation_coverage": True,
            "universal_invocation_witness": True,
            "universal_content_credential": True,
            "universal_rdllm_passport": True,
            "universal_adoption_standard": True,
            "universal_interop_test_kit": True,
            "universal_context_provenance_bridge": True,
            "universal_citation_verification_contract": True,
            "universal_grounded_reuse_contract": True,
            "universal_training_serving_contract": True,
            "universal_confidential_attribution_audit": True,
            "universal_attribution_authority_control_plane": True,
            "universal_rdllm_root": True,
            "universal_emission_enforcement_gateway": True,
            "universal_composite_rdllm_profile": True,
            "universal_runtime_conformance_receipt": True,
            "universal_claim_provenance_envelope": True,
            "universal_provider_wire_protocol": True,
            "universal_accountability_audit_trail": True,
            "universal_accountability_witness_quorum": True,
            "universal_grounded_reliance_contract": True,
            "universal_reliance_correction_ledger": True,
            "universal_foundation_adoption_kernel": True,
            "universal_provider_adapter_harness": True,
            "universal_provider_drift_sentinel": True,
            "universal_attribution_negotiation_handshake": True,
            "universal_negotiated_invocation_enforcement": True,
            "universal_certification_trust_federation": True,
            "universal_foundation_provider_adoption_pack": True,
            "universal_industry_adoption_root": True,
            "universal_reference_implementation_distribution": True,
            "universal_live_attribution_proof": True,
            "universal_foundation_model_release_passport": True,
            "universal_composite_rdllm_contract": True,
            "universal_foundation_provider_binding_matrix": True,
            "universal_provider_conformance_runner_receipt": True,
            "universal_production_invocation_admission": True,
            "universal_source_grounded_response_receipt": True,
            "universal_distribution_reliance_passport": True,
            "universal_adversarial_provenance_quorum": True,
            "universal_procurement_regulatory_reliance_contract": True,
            "universal_provider_onboarding_migration_covenant": True,
            "universal_model_provider_registry": True,
            "universal_source_footer_enforcement_contract": True,
            "universal_provider_catalog_coverage_contract": True,
            "universal_runtime_route_binding_contract": True,
            "universal_verified_source_footer_contract": True,
            "universal_model_capability_coverage_contract": True,
            "universal_live_capability_discovery_contract": True,
            "universal_native_source_annotation_contract": True,
            "universal_claim_evidence_footer_verification_contract": True,
            "universal_provider_meter_normalization_contract": True,
            "universal_provider_response_state_normalization_contract": True,
            "third_party_audit_attestation": True,
            "usage_revenue_allocation": True,
            "finance_ledger_attestation": True,
            "proof_dependency_graph": True,
            "publication_monitor": True,
            "publication_witness": True,
            "trust_registry": True,
            "certification_attestation": True,
        },
        "public_disclosure_surfaces": {
            "provider_attribution_card": True,
            "source_footer": True,
            "attribution_receipt": True,
            "public_receipt": True,
            "selective_disclosure_package": True,
            "trace_exchange": True,
            "royalty_statement": True,
            "attribution_challenge": True,
            "lineage_report": True,
            "provenance_evaluation_report": True,
            "counterfactual_influence_report": True,
            "media_attribution_report": True,
            "model_signal_attribution_report": True,
            "pinpoint_provenance_report": True,
            "citation_identity_report": True,
            "attribution_consensus_report": True,
            "verifier_quorum_report": True,
            "verifier_accountability_report": True,
            "receipt_transparency_consistency_report": True,
            "watchtower_challenge_settlement_report": True,
            "output_provenance_binding_report": True,
            "post_release_discovery_report": True,
            "rights_remediation_report": True,
            "semantic_text_attribution_report": True,
            "code_attribution_report": True,
            "claim_verification_report": True,
            "source_availability_report": True,
            "evidence_sufficiency_report": True,
            "counterevidence_report": True,
            "answer_claim_coverage_report": True,
            "generation_context_closure_report": True,
            "source_boundary_report": True,
            "source_authenticity_report": True,
            "decision_provenance_report": True,
            "calibrated_attribution_report": True,
            "release_grounding_closure": True,
            "answer_provenance_card": True,
            "source_verification_report": True,
            "source_confidence_report": True,
            "citation_footer_contract": True,
            "private_audit_challenge": True,
            "transitive_attribution_report": True,
            "clearinghouse_report": True,
            "remittance_report": True,
            "payment_execution_report": True,
            "payment_rail_attestation": True,
            "creator_payout_receipt_report": True,
            "rendered_attribution_audit": True,
            "training_memory_provenance": True,
            "evidence_locked_generation": True,
            "emission_evidence_enforcement": True,
            "live_emission_witness": True,
            "live_emission_transparency": True,
            "attested_runtime": True,
            "claim_source_attribution_report": True,
            "evidence_utility_attribution_report": True,
            "parametric_memory_attribution_report": True,
            "style_influence_attribution_report": True,
            "model_lineage_attribution_report": True,
            "black_box_model_provenance_report": True,
            "attribution_dispute_adjudication_report": True,
            "post_adjudication_settlement_adjustment_report": True,
            "residual_corpus_royalty_report": True,
            "valuation_method_audit_report": True,
            "evidence_region_binding_report": True,
            "source_access_lease_report": True,
            "content_protocol_ingestion_report": True,
            "citation_reliance_receipt": True,
            "license_transaction_receipt": True,
            "grounded_source_footer": True,
            "source_footer_delivery": True,
            "foundation_api_profile": True,
            "client_attribution_enforcement": True,
            "persistent_memory_provenance": True,
            "private_reasoning_attribution": True,
            "post_training_signal_provenance": True,
            "attribution_bom": True,
            "creator_attribution_audit_index": True,
            "creator_attribution_audit_federation": True,
            "creator_attribution_audit_federation_transparency": True,
            "creator_audit_transparency_monitor": True,
            "creator_audit_private_watch": True,
            "deep_research_citation_audit": True,
            "source_freshness_audit": True,
            "royalty_abuse_audit": True,
            "consent_revocation_propagation": True,
            "evidence_force_calibration": True,
            "warranted_source_footer": True,
            "source_origin_lineage": True,
            "evidence_preview_footer": True,
            "evidence_locator_manifest": True,
            "citation_url_health": True,
            "composite_foundation_adapter": True,
            "foundation_provider_conformance": True,
            "foundation_runtime_adapter": True,
            "foundation_runtime_router": True,
            "foundation_model_deployment_attestation": True,
            "universal_composition_receipt": True,
            "universal_composition_settlement": True,
            "universal_foundation_model_contract": True,
            "universal_invocation_guard": True,
            "universal_invocation_coverage": True,
            "universal_invocation_witness": True,
            "universal_content_credential": True,
            "universal_rdllm_passport": True,
            "universal_adoption_standard": True,
            "universal_interop_test_kit": True,
            "universal_context_provenance_bridge": True,
            "universal_citation_verification_contract": True,
            "universal_grounded_reuse_contract": True,
            "universal_training_serving_contract": True,
            "universal_confidential_attribution_audit": True,
            "universal_attribution_authority_control_plane": True,
            "universal_rdllm_root": True,
            "universal_emission_enforcement_gateway": True,
            "universal_composite_rdllm_profile": True,
            "universal_runtime_conformance_receipt": True,
            "universal_claim_provenance_envelope": True,
            "universal_provider_wire_protocol": True,
            "universal_accountability_audit_trail": True,
            "universal_accountability_witness_quorum": True,
            "universal_grounded_reliance_contract": True,
            "universal_reliance_correction_ledger": True,
            "universal_foundation_adoption_kernel": True,
            "universal_provider_adapter_harness": True,
            "universal_provider_drift_sentinel": True,
            "universal_attribution_negotiation_handshake": True,
            "universal_negotiated_invocation_enforcement": True,
            "universal_certification_trust_federation": True,
            "universal_foundation_provider_adoption_pack": True,
            "universal_industry_adoption_root": True,
            "universal_reference_implementation_distribution": True,
            "universal_live_attribution_proof": True,
            "universal_foundation_model_release_passport": True,
            "universal_composite_rdllm_contract": True,
            "universal_foundation_provider_binding_matrix": True,
            "universal_provider_conformance_runner_receipt": True,
            "universal_production_invocation_admission": True,
            "universal_source_grounded_response_receipt": True,
            "universal_distribution_reliance_passport": True,
            "universal_adversarial_provenance_quorum": True,
            "universal_procurement_regulatory_reliance_contract": True,
            "universal_provider_onboarding_migration_covenant": True,
            "universal_model_provider_registry": True,
            "universal_source_footer_enforcement_contract": True,
            "universal_provider_catalog_coverage_contract": True,
            "universal_runtime_route_binding_contract": True,
            "universal_verified_source_footer_contract": True,
            "universal_model_capability_coverage_contract": True,
            "universal_live_capability_discovery_contract": True,
            "universal_native_source_annotation_contract": True,
            "universal_claim_evidence_footer_verification_contract": True,
            "universal_provider_meter_normalization_contract": True,
            "universal_provider_response_state_normalization_contract": True,
            "audit_attestation": True,
            "revenue_allocation_report": True,
            "finance_ledger_attestation": True,
            "proof_dependency_graph": True,
            "publication_monitor": True,
            "publication_witness": True,
            "trust_registry": True,
            "certification_attestation": True,
            "response_envelope": True,
            "integration_profile": True,
            "discovery_manifest": True,
            "assurance_bundle": True,
            "attribution_exchange": True,
            "conformance_vector_pack": True,
            "federation_handshake": True,
            "attribution_capsule": True,
            "response_release_gate": True,
            "proof_carrying_response": True,
            "serving_gateway_report": True,
            "streaming_attribution_manifest": True,
            "conversation_attribution_ledger": True,
            "agent_tool_attribution_ledger": True,
            "creator_license_contract": True,
            "interop_bundle": True,
        },
        "rights_and_settlement": {
            "rights_policy_enforced_before_generation": True,
            "ownership_conflicts_route_to_registry_escrow": True,
            "unattributed_value_routes_to_unattributed_escrow": True,
            "unlicensed_influence_routes_to_rights_conflict_escrow": True,
            "post_revocation_remediation_report_supported": True,
            "cross_provider_clearinghouse_supported": True,
            "verifiable_remittance_instructions_supported": True,
            "payment_execution_attestation_supported": True,
            "payment_rail_authenticity_supported": True,
            "creator_payout_receipts_supported": True,
            "rendered_attribution_audit_supported": True,
            "training_memory_provenance_supported": True,
            "evidence_locked_generation_supported": True,
            "emission_evidence_enforcement_supported": True,
            "live_emission_witness_supported": True,
            "live_emission_transparency_supported": True,
            "attested_attribution_runtime_supported": True,
            "claim_source_attribution_supported": True,
            "causal_evidence_utility_attribution_supported": True,
            "parametric_memory_attribution_supported": True,
            "style_influence_attribution_supported": True,
            "model_lineage_attribution_supported": True,
            "black_box_model_provenance_supported": True,
            "attribution_dispute_adjudication_supported": True,
            "post_adjudication_settlement_adjustment_supported": True,
            "residual_corpus_royalty_supported": True,
            "diffuse_training_value_pool_supported": True,
            "valuation_method_audit_supported": True,
            "residual_valuation_benchmarking_supported": True,
            "evidence_region_binding_supported": True,
            "wrong_region_controls_supported": True,
            "source_access_lease_supported": True,
            "creator_side_access_audit_supported": True,
            "unleased_source_use_escrow_supported": True,
            "external_content_protocol_ingestion_supported": True,
            "rsl_comp_scp_bridge_supported": True,
            "content_protocol_denial_escrow_supported": True,
            "citation_reliance_receipts_supported": True,
            "post_hoc_citation_blocking_supported": True,
            "license_server_transactions_supported": True,
            "license_ledger_inclusion_supported": True,
            "grounded_source_footer_supported": True,
            "footer_proof_handles_supported": True,
            "source_footer_delivery_supported": True,
            "gateway_footer_egress_binding_supported": True,
            "foundation_api_profile_supported": True,
            "minimum_api_attribution_metadata_supported": True,
            "client_attribution_enforcement_supported": True,
            "client_render_fail_closed_supported": True,
            "persistent_memory_provenance_supported": True,
            "memory_royalty_carry_forward_supported": True,
            "private_reasoning_attribution_supported": True,
            "chain_of_thought_privacy_preserving_attribution_supported": True,
            "post_training_signal_provenance_supported": True,
            "rlhf_rlaif_rlvr_signal_royalty_carry_forward_supported": True,
            "attribution_bom_supported": True,
            "notice_and_license_carry_forward_supported": True,
            "creator_attribution_audit_index_supported": True,
            "creator_queryable_proof_surface_supported": True,
            "creator_attribution_audit_federation_supported": True,
            "cross_provider_creator_query_supported": True,
            "creator_audit_federation_transparency_supported": True,
            "creator_query_anti_equivocation_supported": True,
            "creator_audit_transparency_monitor_supported": True,
            "creator_query_monitoring_supported": True,
            "creator_audit_private_watch_supported": True,
            "private_creator_query_watch_tokens_supported": True,
            "deep_research_citation_audit_supported": True,
            "long_form_citation_fact_support_supported": True,
            "source_freshness_audit_supported": True,
            "temporal_validity_attribution_supported": True,
            "royalty_abuse_audit_supported": True,
            "source_farm_and_sybil_settlement_review_supported": True,
            "consent_revocation_propagation_supported": True,
            "revocation_reaches_memory_exchange_footer_and_settlement_supported": True,
            "evidence_force_calibration_supported": True,
            "verified_footer_requires_claim_force_within_evidence_force_supported": True,
            "warranted_source_footer_supported": True,
            "visible_warrant_labels_supported": True,
            "source_origin_lineage_supported": True,
            "synthetic_source_laundering_guard_supported": True,
            "evidence_preview_footer_supported": True,
            "permissioned_source_snippet_footer_supported": True,
            "evidence_locator_manifest_supported": True,
            "exact_evidence_clickthrough_supported": True,
            "citation_url_health_supported": True,
            "fabricated_url_guard_supported": True,
            "link_rot_snapshot_fallback_supported": True,
            "composite_foundation_adapter_supported": True,
            "provider_neutral_foundation_contract_supported": True,
            "foundation_provider_conformance_supported": True,
            "provider_api_attribution_conformance_supported": True,
            "foundation_runtime_adapter_supported": True,
            "native_response_runtime_fail_closed_supported": True,
            "foundation_runtime_router_supported": True,
            "multi_provider_router_fail_closed_supported": True,
            "foundation_model_deployment_attestation_supported": True,
            "provider_backend_substitution_guard_supported": True,
            "universal_composition_receipt_supported": True,
            "multi_provider_composite_answer_supported": True,
            "universal_composition_settlement_supported": True,
            "multi_provider_creator_pool_clearing_supported": True,
            "universal_foundation_model_contract_supported": True,
            "universal_invocation_guard_supported": True,
            "universal_invocation_coverage_supported": True,
            "universal_invocation_witness_supported": True,
            "universal_content_credential_supported": True,
            "universal_rdllm_passport_supported": True,
            "universal_adoption_standard_supported": True,
            "universal_interop_test_kit_supported": True,
            "universal_context_provenance_bridge_supported": True,
            "universal_citation_verification_contract_supported": True,
            "universal_grounded_reuse_contract_supported": True,
            "universal_training_serving_contract_supported": True,
            "universal_confidential_attribution_audit_supported": True,
            "universal_attribution_authority_control_plane_supported": True,
            "universal_rdllm_root_supported": True,
            "universal_emission_enforcement_gateway_supported": True,
            "universal_composite_rdllm_profile_supported": True,
            "universal_runtime_conformance_receipt_supported": True,
            "universal_claim_provenance_envelope_supported": True,
            "universal_provider_wire_protocol_supported": True,
            "universal_accountability_audit_trail_supported": True,
            "universal_accountability_witness_quorum_supported": True,
            "universal_grounded_reliance_contract_supported": True,
            "universal_reliance_correction_ledger_supported": True,
            "universal_foundation_adoption_kernel_supported": True,
            "universal_provider_adapter_harness_supported": True,
            "universal_provider_drift_sentinel_supported": True,
            "universal_attribution_negotiation_handshake_supported": True,
            "universal_negotiated_invocation_enforcement_supported": True,
            "universal_certification_trust_federation_supported": True,
            "universal_foundation_provider_adoption_pack_supported": True,
            "universal_industry_adoption_root_supported": True,
            "universal_reference_implementation_distribution_supported": True,
            "universal_live_attribution_proof_supported": True,
            "universal_foundation_model_release_passport_supported": True,
            "universal_composite_rdllm_contract_supported": True,
            "universal_foundation_provider_binding_matrix_supported": True,
            "universal_provider_conformance_runner_receipt_supported": True,
            "universal_production_invocation_admission_supported": True,
            "universal_source_grounded_response_receipt_supported": True,
            "universal_distribution_reliance_passport_supported": True,
            "universal_adversarial_provenance_quorum_supported": True,
            "universal_procurement_regulatory_reliance_contract_supported": True,
            "universal_provider_onboarding_migration_covenant_supported": True,
            "universal_model_provider_registry_supported": True,
            "universal_source_footer_enforcement_contract_supported": True,
            "universal_provider_catalog_coverage_contract_supported": True,
            "universal_runtime_route_binding_contract_supported": True,
            "universal_verified_source_footer_contract_supported": True,
            "universal_model_capability_coverage_contract_supported": True,
            "universal_live_capability_discovery_contract_supported": True,
            "universal_native_source_annotation_contract_supported": True,
            "universal_claim_evidence_footer_verification_contract_supported": True,
            "universal_provider_meter_normalization_contract_supported": True,
            "universal_provider_response_state_normalization_contract_supported": True,
            "provider_neutral_foundation_adoption_supported": True,
            "industry_adoption_root_supported": True,
            "reference_implementation_distribution_supported": True,
            "live_attribution_proof_required_for_response_release": True,
            "model_release_passport_required_for_model_claim": True,
            "single_composite_rdllm_contract_required": True,
            "native_provider_binding_matrix_required": True,
            "native_provider_conformance_runner_required": True,
            "production_invocation_admission_required": True,
            "source_grounded_response_receipt_required": True,
            "distribution_reliance_passport_required": True,
            "adversarial_provenance_quorum_required": True,
            "federated_conformance_trust_mark_supported": True,
            "third_party_certification_status_revocation_supported": True,
            "negotiated_invocation_bypass_block_supported": True,
            "live_reliance_status_correction_supported": True,
            "copied_output_status_link_supported": True,
            "revoked_footer_settlement_hold_supported": True,
            "source_status_resolver_required_for_all_provider_families_supported": True,
            "provider_neutral_footer_rendering_kernel_supported": True,
            "foundation_api_negative_fixture_fail_closed_supported": True,
            "native_provider_fixture_normalization_supported": True,
            "stream_tool_copy_adapter_fixture_fail_closed_supported": True,
            "provider_api_model_drift_revocation_supported": True,
            "request_time_attribution_negotiation_supported": True,
            "provider_neutral_confidential_attribution_audit_supported": True,
            "provider_neutral_authority_control_plane_supported": True,
            "provider_neutral_root_of_trust_supported": True,
            "root_bound_response_emission_supported": True,
            "universal_composite_provider_contract_supported": True,
            "runtime_receipt_source_footer_telemetry_settlement_supported": True,
            "generation_time_claim_provenance_supported": True,
            "posthoc_citation_only_blocking_supported": True,
            "provider_wire_protocol_supported": True,
            "wire_transport_provenance_supported": True,
            "single_composite_rdllm_root_supported": True,
            "agent_runtime_authority_control_supported": True,
            "tool_and_context_authority_control_supported": True,
            "settlement_authority_control_supported": True,
            "confidential_private_evidence_room_supported": True,
            "creator_challenge_route_for_private_evidence_supported": True,
            "regulator_export_for_private_evidence_supported": True,
            "native_provider_meter_reconciliation_supported": True,
            "provider_receipt_egress_witness_nonrepudiation_supported": True,
            "portable_content_credential_source_payout_and_invocation_binding_supported": True,
            "provider_deployment_passport_supported": True,
            "provider_neutral_rdllm_standard_supported": True,
            "provider_neutral_interop_test_kit_supported": True,
            "provider_neutral_citation_verification_contract_supported": True,
            "provider_neutral_context_provenance_bridge_supported": True,
            "provider_neutral_grounded_reuse_contract_supported": True,
            "provider_neutral_training_serving_contract_supported": True,
            "provider_neutral_private_evidence_audit_supported": True,
            "third_party_audit_attestation_supported": True,
            "usage_revenue_allocation_supported": True,
            "finance_ledger_attestation_supported": True,
            "proof_dependency_graph_supported": True,
            "publication_monitor_supported": True,
            "publication_witness_supported": True,
            "trust_registry_supported": True,
            "certification_attestation_supported": True,
            "code_attribution_supported": True,
            "code_license_conflict_escrow_supported": True,
            "pre_settlement_claim_verification_supported": True,
            "weak_or_duplicate_claim_escrow_supported": True,
            "citation_source_availability_supported": True,
            "claim_evidence_sufficiency_supported": True,
            "counterevidence_adjudication_supported": True,
            "answer_claim_coverage_supported": True,
            "generation_context_closure_supported": True,
            "source_boundary_integrity_supported": True,
            "source_authenticity_poisoning_resilience_supported": True,
            "streaming_attribution_commitment_supported": True,
            "conversation_attribution_continuity_supported": True,
            "agent_tool_attribution_supported": True,
            "pinpoint_provenance_supported": True,
            "citation_identity_supported": True,
            "attribution_consensus_supported": True,
            "independent_verifier_quorum_supported": True,
            "bonded_verifier_accountability_supported": True,
            "receipt_transparency_consistency_supported": True,
            "watchtower_challenge_settlement_supported": True,
            "output_provenance_binding_supported": True,
            "post_release_discovery_supported": True,
            "decision_provenance_supported": True,
            "calibrated_attribution_confidence_supported": True,
            "release_grounding_closure_supported": True,
            "creator_pool_conservation_required": True,
        },
        "challenge_policy": {
            "accepted_protocol": "rdllm-attribution-challenge/v1",
            "default_accept_threshold": 0.20,
            "remedies": [
                "pay_claimant",
                "escrow_unlicensed",
                "reject_weak_evidence",
                "no_action_already_credited",
            ],
            "historical_events_are_not_rewritten": True,
        },
        "coverage": _ledger_summary(events),
        "evidence_roots": _evidence_roots(ledger_data, events),
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "claim_evidence_text_disclosed": False,
            "matched_text_disclosed": False,
            "public_card_uses_counts_and_hash_roots": True,
        },
        "limitations": [
            "reference implementation verifies provider-supplied model signal telemetry but does not compute production hidden states",
            "reference implementation supports media signature attribution for image/audio/video assets but does not decode raw media bytes",
            "reference implementation uses deterministic lexical and concept features for semantic text attribution; production deployments can substitute stronger embedding or model-native evidence if they preserve replayable commitments",
            "reference implementation publishes cross-provider exchange manifests as hash-bound contracts; production deployments should pair them with provider authentication and live registry resolution",
            "reference implementation publishes conformance vectors for public artifact behavior but does not certify external provider uptime or throughput",
            "reference implementation publishes runtime federation handshakes as signed negotiation artifacts but does not operate a production provider network",
            "reference implementation publishes portable attribution capsules for copied outputs but cannot force third-party platforms to preserve the marker",
            "reference implementation publishes response release gates for public proof artifacts but production deployments must enforce the gate at every serving boundary",
            "reference implementation emits proof-carrying responses that enforce the gate locally; production deployments must make this the only delivery path for attributable answers",
            "reference implementation emits serving gateway reports that prove API egress used the proof-carrying response; production deployments must place the gateway on every model route",
            "reference implementation emits streaming attribution manifests that bind every streamed chunk length, hash, and chain link to the proof-carrying response and serving gateway output; production deployments must emit these commitments for all streaming model routes",
            "reference implementation emits agent-tool attribution ledgers that bind tool observations to trace spans, visible source rows, supported claims, and conversation-level royalty obligations; production deployments must capture every retrieval, web, file, function, code, MCP, or remote tool observation before synthesis",
            "reference implementation emits pinpoint provenance reports that reject topical anti-documents and require answer-critical fact support before a source can appear in a public footer or receive direct payout; production deployments should pair this with stronger entailment models and training-data attribution telemetry while preserving replayable commitments",
            "reference implementation emits citation identity reports that reject fabricated, unresolved, or metadata-swapped citation records before public footer display or citation-linked payout; production deployments should bind authority records to Crossref, arXiv, DOI, ISBN, archival, and publisher registries while preserving replayable commitments",
            "reference implementation emits attribution consensus reports that require independent provenance, citation identity, authenticity, sufficiency, counterevidence, and source-confidence channels to agree before direct settlement; production deployments should pair this with external verifiers and dispute-resolution workflows",
            "reference implementation emits independent verifier quorum reports that require multiple external replay signatures before accepted attribution consensus rows can release direct settlement; production deployments should bind verifier identities to accredited public-key infrastructure and conflict-of-interest controls",
            "reference implementation emits bonded verifier accountability reports that require active registry identities, slashable bond coverage, conflict disclosures, and no open accountability challenges before verifier-approved settlement can leave escrow",
            "reference implementation emits receipt transparency consistency reports that require append-only usage receipt logs, valid receipt inclusion proofs, and no split-view roots before verifier-approved settlement can leave escrow",
            "reference implementation emits watchtower challenge settlement reports that require independent registered watchtower attestations and no open or accepted public challenges before receipt-transparent settlement can leave escrow",
            "reference implementation emits output provenance binding reports that bind proof-carrying responses, serving-gateway output hashes, attribution capsules, watchtower-cleared settlement, content credentials, watermark commitments, fingerprint commitments, and public verification paths without embedding raw output text",
            "reference implementation emits post-release discovery reports that publish late-bound output proof artifacts without mutating the base discovery manifest or creating self-referential hash cycles",
            "reference implementation emits universal grounded reliance contracts that block source footers, user confidence labels, procurement claims, regulator exports, and creator settlement unless the cited sources, evidence locators, freshness checks, L153 witness roots, client rendering, and finance reconciliation are all replayably verified",
            "reference implementation emits claim-source attribution reports that independently replay visible claims against candidate sources, Q&A nuggets, anti-documents, visual-region commitments, and LOO-style source contribution before footer display or direct payout",
            "reference implementation emits style influence attribution reports that credit licensed creator style or voice profiles only when style similarity, declared style intent, anti-style decoy separation, copy-overlap guards, and payout conservation pass; production deployments should replace the deterministic demo stylometry with stronger modality-specific attribution models while preserving replayable commitments",
            "reference implementation emits model-lineage attribution reports that preserve upstream attribution obligations when attributed outputs or synthetic data train or distill downstream models; production deployments should bind this to real training pipelines, teacher traces, dataset manifests, and future usage billing",
            "reference implementation emits black-box model provenance challenge reports for likely undisclosed derivative models; production deployments should bind challenge prompts, baseline distributions, watermark or fingerprint keys, and independent auditor evidence to a dispute and settlement workflow",
            "reference implementation emits attribution dispute adjudication reports that freeze disputed value, accept claimant and respondent evidence by hash commitment, require bonded independent verifier quorum, enforce appeals, and release or preserve escrow without exposing raw prompts, outputs, or source text",
            "reference implementation emits residual corpus royalty reports that settle diffuse licensed training-corpus value separately from visible answer attribution, with valuation evidence hashes, creator-level caps, rights gating, and payable-or-escrow conservation",
            "reference implementation emits valuation-method audit reports that benchmark residual-corpus valuation methods against known contributors, hard anti-documents, duplicate guards, calibration rows, stability rows, method commitments, and privacy commitments; production deployments should publish larger domain-specific benchmark commitments and independent audit roots",
            "reference implementation emits evidence-region binding reports that bind every rendered claim span and footer span prefix to exact page, line, char, bbox, or timecode commitments and reject wrong-region controls without exposing raw source text",
            "reference implementation emits citation URL-health reports that classify every visible evidence locator as live, content-addressed, DOI-resolved, archived link rot, fabricated, or unverified; production deployments must bind these checks to live resolvers, archival services, and authority registries",
            "reference implementation emits composite foundation adapter reports that map native OpenAI, Anthropic, Google, Meta, Mistral, or OpenAI-compatible response objects into the same RDLLM envelope, footer, and verifier contract; production deployments must maintain adapter conformance as native APIs evolve",
            "reference implementation emits source-access lease reports that require source-issued leases and access logs before direct settlement; production deployments should integrate creator/source endpoints, MCP-compatible access, and collective-license registries before content is consumed",
            "reference implementation emits creator license contracts as hash-bound rights terms; production deployments must bind these contracts to procurement, registry, and billing systems before source use",
            "reference implementation emits citation footer rendering contracts so client UI rows can be verified before display; production deployments must enforce them in every first- and third-party response client",
            "reference implementation emits transitive attribution reports for downstream copied-output reuse; production deployments must require downstream providers and platforms to submit copied inputs or capsule headers for settlement",
            "reference implementation emits clearinghouse reports for cross-provider settlement; production deployments must bind the report to payment rails, tax handling, and registry identity resolution",
            "reference implementation emits instruction-only remittance reports with ISO 20022-compatible reconciliation fields; production deployments must bind them to licensed payment processors before funds move",
            "reference implementation emits payment execution reports that reconcile remittance instructions against hash-only processor and escrow settlement records; production deployments must bind these hashes to licensed payment processors, escrow agents, sanctions screening, tax withholding, and ledger controls",
            "reference implementation emits payment rail attestations that require registered external processor signatures over the execution batches; production deployments should bind those signatures to regulated payment or escrow processor public keys",
            "reference implementation emits training-memory provenance reports that detect registered memorized spans in the exact rendered answer and require visible attribution before display; production deployments should pair this with suffix-array, activation, or model-native training-data tracing over full training corpora",
            "reference implementation emits evidence-locked generation reports that bind support-required answer units to pre-generation evidence locks; production deployments must create these locks inside the serving path before token emission",
            "reference implementation emits emission evidence enforcement reports that prove served and streamed output used satisfied pre-generation evidence locks; production deployments should enforce this check at every chunk or token boundary",
            "reference implementation emits live emission witness reports that require independent preflight and completion quorum signatures over the streaming boundary; production deployments should replace HMAC demo witnesses with registered external keys, TEEs, or equivalent verifier infrastructure",
            "reference implementation emits live emission transparency reports that require live witness reports and witness attestations to be included in append-only transparency logs with valid inclusion proofs and no split-view roots; production deployments should anchor these logs in independent transparency services",
            "reference implementation emits attested attribution runtime reports with HMAC conformance quotes over measured runtime, model, policy, verifier bundle, and live output path bindings; production deployments should replace those quotes with hardware TEE, ZKML, or hybrid attestation evidence",
            "reference implementation emits third-party audit attestations as hash-only external replay summaries; production deployments must bind auditor identity to real accreditation, conflict-of-interest controls, and legal audit duties",
            "reference implementation emits universal runtime conformance receipts that bind provider API routes, source-footers, client renderers, telemetry spans, and settlement meters to the L148 composite profile; production deployments must make the receipt a required precondition for grounded answer display and creator settlement",
            "reference implementation emits universal claim provenance envelopes that bind each displayed claim to generation-time provenance, support relation, source proof, visible footer row, evidence region, locator health, and settlement meter; production deployments must reject post-hoc citation-only answers",
            "reference implementation emits universal provider wire protocols that bind provider API requests, response bodies, streaming events, proxy transforms, SDK metadata, batch callbacks, and exported copies to L150 claim provenance; production deployments must reject wire transports that drop or rewrite attribution metadata",
            "reference implementation emits universal accountability audit trails that hash-chain provider-wire calls, governance approvals, delegated agents, tool calls, memory events, exports, challenges, and settlement meters; production deployments must make unverifiable traces ineligible for grounded display or direct creator settlement",
            "reference implementation emits universal accountability witness quorum reports that require L152 audit-trail checkpoints to be logged, consistency-proven, monitored, and cosigned by independent witnesses; production deployments must reject provider-only or split-view accountability histories",
            "reference implementation emits revenue allocation reports that prove usage-event gross revenue against declared billing, ad, subscription, API, enterprise, or marketplace revenue pools; production deployments must bind source hashes to finance ledgers and tax records",
            "reference implementation emits finance ledger attestations that bind hash-only finance exports to revenue allocation pools; production deployments must pair the hashes with SOC, tax, payment-processor, and auditor controls",
            "reference implementation emits proof dependency graphs that make public artifact replay order explicit and cycle-checked; production deployments must keep publication bundles and discovery surfaces aligned to that graph",
            "reference implementation emits publication monitor reports that snapshot public proof surfaces into append-only checkpoints; production deployments should mirror them in external transparency logs and alert on regressions",
            "reference implementation emits publication witness reports that cosign monitor checkpoints under a quorum; production deployments should use independent witnesses to detect split-view proof histories",
            "reference implementation emits certification attestations that sign the certification report hash and case-status roots; production deployments should require accredited certifier identities and revocation-aware trust registries",
            "reference implementation emits universal invocation coverage reports that reconcile native provider meter logs, serving-gateway logs, L133 guard receipts, source-footer bindings, response-envelope bindings, and invoice rows; production deployments must bind this to every OpenAI, Anthropic, Google, Meta, Mistral, Cohere, xAI, Bedrock, Azure OpenAI, or compatible provider route",
            "reference implementation emits universal invocation witness reports that bind each L134-covered native provider call to provider-signed usage receipts, independently observed egress events, and an independent witness quorum; production deployments should use external collectors or provider-native receipt APIs to make omitted calls independently detectable",
            "reference implementation emits universal content credentials that bind source attribution, payout eligibility, output provenance credentials, durable watermark/fingerprint signals, public verifier surfaces, and L135 invocation witnesses; production deployments should map these rows into C2PA manifests, W3C credentials, SCITT statements, and platform-specific watermark detectors",
            "reference implementation emits generated-code attribution reports with line/token commitments and SPDX-style license checks; production deployments should pair exact fingerprints with vector retrieval over full code corpora",
            "reference implementation emits pre-settlement claim verification reports; production deployments should bind trusted issuers to external identity, copyright, publisher, collective-management, or court records",
            "reference implementation emits source availability reports from deterministic source snapshots; production deployments should bind snapshots to live resolvers, archival systems, and uptime monitoring",
            "reference implementation emits evidence sufficiency reports with deterministic lexical ranking and decoy margins; production deployments can add stronger entailment or domain-specific verifiers if they preserve replayable commitments",
            "reference implementation emits counterevidence reports using deterministic polarity-conflict probes; production deployments should add stronger natural-language-inference and domain-specific contradiction checks while preserving replayable commitments",
            "reference implementation emits answer claim coverage reports that require every support-bearing public answer sentence to replay against a verified claim row; production deployments should replace deterministic sentence splitting with domain-aware claim extraction where needed while preserving hash commitments",
            "reference implementation emits generation context closure reports that require each verified claim to bind to a trace-backed context block; production deployments should capture these blocks at the serving gateway before the model call",
            "reference implementation emits source boundary reports that require every generation context block to bind to evidence-only source spans; production deployments should enforce source data and instruction separation before model invocation",
            "reference implementation emits source-authenticity reports that escrow synthetic, untrusted, citation-farm, or high-poisoning-risk sources; production deployments should bind origin signals to independent provenance registries and source-quality monitoring",
            "reference implementation emits consent and revocation propagation audits that require opt-outs, license changes, and lease expiry to reach retrieval, leases, transactions, footers, memory, post-training signals, downstream exchange, and settlement before future use",
            "reference implementation emits evidence-force calibration reports that block over-warranted claims from verified footers and direct payout when cited evidence is relevant but weaker than the answer wording",
            "reference implementation emits warranted source footers that publish relation, modality, scope, temporal, and numeric warrant labels for each verified visible footer claim without exposing raw claim or evidence text",
            "reference implementation emits source-origin lineage reports that route unknown or unattributed synthetic sources to origin-review escrow and split synthetic-with-lineage value to upstream creators before direct settlement",
            "reference implementation emits evidence-preview footers that publish only short permissioned evidence snippets with source URLs, warrant labels, origin labels, and proof hashes; production deployments should enforce publisher-specific excerpt policies and jurisdictional quote limits",
            "reference implementation emits evidence-locator manifests that bind each public preview snippet to an exact resolver URL plus snapshot or text-fragment proof; production deployments should operate durable resolvers and preserve independent snapshots for link rot and publisher redesigns",
            "reference implementation emits decision provenance reports that prove claims, footer rows, payout participation, and release decisions use only authorized proof, policy, and accounting channels; production deployments should make this graph part of every emitted attribution bundle",
            "reference implementation emits calibrated attribution-confidence reports with benchmark-backed lower bounds for claims, footers, and payout participation; production deployments should increase benchmark scale and publish domain-specific calibration policies",
            "reference implementation enforces release grounding closure only for providers claiming L55 or higher; production deployments should make L58-style closed envelopes mandatory on attributable model routes",
            "reference implementation emits universal certification trust federations that make RDLLM conformance claims dependent on trust anchors, accredited certification authorities, conformance labs, trust marks, verifiable credentials, transparency inclusion, revocation status, and relying-party policy",
            "provider card proves current ledger and certification posture, not market adoption",
        ],
    }
    card["card_hash"] = hash_payload(_hashable_card(card))
    card["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_card(card), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return card


def validate_provider_card_shape(card: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "card_version",
        "issuer",
        "created_at",
        "provider",
        "certification",
        "supported_evidence_channels",
        "public_disclosure_surfaces",
        "rights_and_settlement",
        "challenge_policy",
        "coverage",
        "evidence_roots",
        "privacy",
        "limitations",
        "card_hash",
        "signature",
    )
    for key in required:
        if key not in card:
            errors.append(f"missing provider card field: {key}")
    if errors:
        return errors
    if card.get("card_version") != PROVIDER_CARD_VERSION:
        errors.append("provider card version is unsupported")
    for key in ("id", "model_id", "model_version"):
        if key not in card.get("provider", {}):
            errors.append(f"missing provider field: {key}")
    for key in ("event_count", "accounted_access_ratio", "creator_pool_total"):
        if key not in card.get("coverage", {}):
            errors.append(f"missing provider coverage field: {key}")
    for key in ("ledger_root", "event_root", "source_access_root"):
        if key not in card.get("evidence_roots", {}):
            errors.append(f"missing provider evidence root: {key}")
    return errors


def verify_provider_attribution_card(
    ledger_data: dict[str, Any],
    card: dict[str, Any],
    *,
    certification_report: dict[str, Any] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a provider attribution card against a ledger and optional certification."""

    errors = validate_provider_card_shape(card)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_card(card))
    if expected_hash != card.get("card_hash"):
        errors.append("provider card hash is not reproducible")

    expected = make_provider_attribution_card(
        ledger_data,
        certification_report=certification_report,
        issuer=card.get("issuer", DEFAULT_ISSUER),
        provider=card.get("provider", {}).get("id", "provider:unspecified"),
        model_id=card.get("provider", {}).get("model_id", "model:unspecified"),
        model_version=card.get("provider", {}).get("model_version", "unknown"),
        created_at=card.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "provider",
        "certification",
        "supported_evidence_channels",
        "public_disclosure_surfaces",
        "rights_and_settlement",
        "challenge_policy",
        "coverage",
        "evidence_roots",
        "privacy",
        "limitations",
    ):
        if expected.get(key) != card.get(key):
            errors.append(f"provider card {key} does not match recomputed ledger posture")
    if expected.get("card_hash") != card.get("card_hash"):
        errors.append("provider card hash does not match ledger posture")

    errors.extend(_certification_hash_errors(certification_report))

    if card.get("privacy", {}).get("public_card_uses_counts_and_hash_roots") is not True:
        errors.append("provider card must use counts and hash roots for public disclosure")
    card_json = canonical_json(card)
    for private in _private_strings(_events_from_ledger(ledger_data)):
        if private in card_json:
            errors.append("provider card discloses private event text")
            break

    signature = card.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_card(card), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("provider card is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("provider card signature is invalid")

    if certification_report:
        summary = certification_report.get("summary", {})
        if summary.get("status") != "passed":
            errors.append("provider card is bound to a failing certification report")
        if _level_number(str(summary.get("highest_level", ""))) < 15:
            errors.append("provider card requires at least RDLLM-L15 certification evidence")

    return errors
