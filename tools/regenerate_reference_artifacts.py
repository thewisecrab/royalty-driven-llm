#!/usr/bin/env python3
"""Regenerate the reference RDLLM proof pack after certification-level changes."""

from __future__ import annotations

import inspect
import json
import shutil
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PACKAGED_REFERENCE_ARTIFACTS = (
    "certification_report",
    "discovery_manifest",
    "production_readiness_report",
    "provider_attribution_card",
    "universal_production_invocation_admission",
    "universal_runtime_conformance_receipt",
    "universal_source_grounded_response_receipt",
)
PACKAGED_REFERENCE_ARTIFACT_DIR = (
    SRC / "rdllm" / "data" / "reference_artifacts"
)
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rdllm.artifact_refs import ARTIFACT_REF_KEY, resolve_artifact_refs
from rdllm.answer_card import make_answer_provenance_card
from rdllm.answer_coverage import make_answer_claim_coverage_report
from rdllm.assurance import make_assurance_bundle
from rdllm.attribution_capsule import make_attribution_capsule
from rdllm.calibrated_attribution import make_calibrated_attribution_report
from rdllm.certification import run_certification
from rdllm.certification_attestation import make_certification_attestation
from rdllm.citation_footer import make_citation_footer_contract
from rdllm.client_attribution_enforcement import (
    make_client_attribution_enforcement_receipt,
)
from rdllm.cli import _load_assurance_artifacts
from rdllm.context_closure import make_generation_context_closure_report
from rdllm.counterevidence import make_counterevidence_report
from rdllm.discovery_manifest import make_discovery_manifest
from rdllm.engine import RoyaltyDrivenLLM
from rdllm.emission_enforcement import make_emission_evidence_enforcement_report
from rdllm.evidence_locked_generation import make_evidence_locked_generation_report
from rdllm.evidence_region_binding import make_evidence_region_binding_report
from rdllm.evidence_sufficiency import make_evidence_sufficiency_report
from rdllm.foundation_api_profile import make_foundation_api_profile
from rdllm.grounded_source_footer import make_grounded_source_footer
from rdllm.integration_profile import make_integration_profile
from rdllm.agent_tool_attribution import make_agent_tool_attribution_ledger
from rdllm.conversation_attribution import make_conversation_attribution_ledger
from rdllm.ledger import RoyaltyLedger
from rdllm.license_contract import make_creator_license_contract
from rdllm.live_emission_transparency import (
    make_live_emission_transparency_log,
    make_live_emission_transparency_report,
)
from rdllm.live_emission_witness import make_live_emission_witness_report
from rdllm.persistent_memory_provenance import (
    make_persistent_memory_provenance_receipt,
)
from rdllm.post_training_signal_provenance import (
    make_post_training_signal_provenance_receipt,
)
from rdllm.private_reasoning_attribution import (
    make_private_reasoning_attribution_receipt,
)
from rdllm.proof_carrying_response import make_proof_carrying_response
from rdllm.provider_card import make_provider_attribution_card
from rdllm.proof_dependency_graph import make_proof_dependency_graph
from rdllm.receipts import hash_payload, make_attribution_receipt, public_receipt
from rdllm.release_gate import make_release_gate_report
from rdllm.rendered_attribution_audit import make_rendered_attribution_audit
from rdllm.response_envelope import make_response_envelope
from rdllm.serving_gateway import make_serving_gateway_report
from rdllm.source_authenticity import make_source_authenticity_report
from rdllm.source_availability import make_source_availability_report
from rdllm.source_boundary import make_source_boundary_report
from rdllm.source_confidence import make_source_confidence_report
from rdllm.source_footer_delivery import make_source_footer_delivery_receipt
from rdllm.source_verification import make_source_verification_report
from rdllm.streaming_attribution import make_streaming_attribution_manifest
from rdllm.telemetry import make_trace_exchange
from rdllm.text import stable_hash
from rdllm.universal_attribution_negotiation_handshake import (
    make_universal_attribution_negotiation_handshake,
)
from rdllm.universal_certification_trust_federation import (
    REQUIRED_CORE_ARTIFACTS as L161_REQUIRED_CORE_ARTIFACTS,
    REQUIRED_CREDENTIAL_CLAIMS as L161_REQUIRED_CREDENTIAL_CLAIMS,
    REQUIRED_FEDERATION_ROLES as L161_REQUIRED_FEDERATION_ROLES,
    REQUIRED_NEGATIVE_FEDERATION_FAILURES as L161_REQUIRED_NEGATIVE_FEDERATION_FAILURES,
    REQUIRED_TRANSPARENCY_CHANNELS as L161_REQUIRED_TRANSPARENCY_CHANNELS,
    REQUIRED_TRUST_MARKS as L161_REQUIRED_TRUST_MARKS,
    make_universal_certification_trust_federation,
)
from rdllm.universal_foundation_provider_adoption_pack import (
    REQUIRED_ADOPTION_GATES as L162_REQUIRED_ADOPTION_GATES,
    REQUIRED_CORE_ARTIFACTS as L162_REQUIRED_CORE_ARTIFACTS,
    REQUIRED_NEGATIVE_ADOPTION_FAILURES as L162_REQUIRED_NEGATIVE_ADOPTION_FAILURES,
    REQUIRED_PROVIDER_FAMILIES as L162_REQUIRED_PROVIDER_FAMILIES,
    REQUIRED_STANDARD_EXPORTS as L162_REQUIRED_STANDARD_EXPORTS,
    make_universal_foundation_provider_adoption_pack,
)
from rdllm.universal_industry_adoption_root import (
    REQUIRED_ADOPTION_ROLES as L163_REQUIRED_ADOPTION_ROLES,
    REQUIRED_CORE_ARTIFACTS as L163_REQUIRED_CORE_ARTIFACTS,
    REQUIRED_NEGATIVE_ROOT_FAILURES as L163_REQUIRED_NEGATIVE_ROOT_FAILURES,
    REQUIRED_PUBLICATION_ENDPOINTS as L163_REQUIRED_PUBLICATION_ENDPOINTS,
    make_universal_industry_adoption_root,
)
from rdllm.universal_reference_implementation_distribution import (
    REQUIRED_DISTRIBUTION_COMPONENTS as L164_REQUIRED_DISTRIBUTION_COMPONENTS,
    REQUIRED_INSTALL_TARGETS as L164_REQUIRED_INSTALL_TARGETS,
    REQUIRED_NEGATIVE_DISTRIBUTION_FAILURES as L164_REQUIRED_NEGATIVE_DISTRIBUTION_FAILURES,
    make_universal_reference_implementation_distribution,
)
from rdllm.universal_live_attribution_proof import (
    REQUIRED_FOOTER_SURFACES as L165_REQUIRED_FOOTER_SURFACES,
    REQUIRED_KNOWLEDGE_SOURCE_MODES as L165_REQUIRED_KNOWLEDGE_SOURCE_MODES,
    REQUIRED_NEGATIVE_LIVE_FAILURES as L165_REQUIRED_NEGATIVE_LIVE_FAILURES,
    make_universal_live_attribution_proof,
)
from rdllm.universal_foundation_model_release_passport import (
    REQUIRED_COMPLIANCE_MAPPINGS as L166_REQUIRED_COMPLIANCE_MAPPINGS,
    REQUIRED_NEGATIVE_RELEASE_FAILURES as L166_REQUIRED_NEGATIVE_RELEASE_FAILURES,
    REQUIRED_PROVIDER_RELEASE_ROUTES as L166_REQUIRED_PROVIDER_RELEASE_ROUTES,
    REQUIRED_RELEASE_LIFECYCLE_DOMAINS as L166_REQUIRED_RELEASE_LIFECYCLE_DOMAINS,
    make_universal_foundation_model_release_passport,
)
from rdllm.universal_composite_rdllm_contract import (
    REQUIRED_CANONICAL_API_SURFACES as L167_REQUIRED_CANONICAL_API_SURFACES,
    REQUIRED_CONTRACT_ROLES as L167_REQUIRED_CONTRACT_ROLES,
    REQUIRED_DECISION_GATES as L167_REQUIRED_DECISION_GATES,
    REQUIRED_NEGATIVE_COMPOSITE_FAILURES as L167_REQUIRED_NEGATIVE_COMPOSITE_FAILURES,
    REQUIRED_STANDARD_BINDINGS as L167_REQUIRED_STANDARD_BINDINGS,
    make_universal_composite_rdllm_contract,
)
from rdllm.universal_foundation_provider_binding_matrix import (
    REQUIRED_BINDING_DOMAINS as L168_REQUIRED_BINDING_DOMAINS,
    REQUIRED_NATIVE_CAPABILITIES as L168_REQUIRED_NATIVE_CAPABILITIES,
    REQUIRED_NEGATIVE_PROVIDER_FAILURES as L168_REQUIRED_NEGATIVE_PROVIDER_FAILURES,
    REQUIRED_PROVIDER_FAMILIES as L168_REQUIRED_PROVIDER_FAMILIES,
    make_universal_foundation_provider_binding_matrix,
)
from rdllm.universal_provider_conformance_runner_receipt import (
    REQUIRED_FIXTURE_SUITES as L169_REQUIRED_FIXTURE_SUITES,
    REQUIRED_NEGATIVE_RUNNER_FAILURES as L169_REQUIRED_NEGATIVE_RUNNER_FAILURES,
    REQUIRED_PROVIDER_FAMILIES as L169_REQUIRED_PROVIDER_FAMILIES,
    REQUIRED_RUNNER_STAGES as L169_REQUIRED_RUNNER_STAGES,
    make_universal_provider_conformance_runner_receipt,
)
from rdllm.universal_production_invocation_admission import (
    REQUIRED_ADMISSION_GATES as L170_REQUIRED_ADMISSION_GATES,
    REQUIRED_INVOCATION_SURFACES as L170_REQUIRED_INVOCATION_SURFACES,
    REQUIRED_NEGATIVE_ADMISSION_FAILURES as L170_REQUIRED_NEGATIVE_ADMISSION_FAILURES,
    REQUIRED_PROVIDER_FAMILIES as L170_REQUIRED_PROVIDER_FAMILIES,
    make_universal_production_invocation_admission,
)
from rdllm.universal_source_grounded_response_receipt import (
    REQUIRED_CLAIM_TYPES as L171_REQUIRED_CLAIM_TYPES,
    REQUIRED_NEGATIVE_RESPONSE_FAILURES as L171_REQUIRED_NEGATIVE_RESPONSE_FAILURES,
    REQUIRED_RESPONSE_SURFACES as L171_REQUIRED_RESPONSE_SURFACES,
    REQUIRED_SETTLEMENT_SCOPES as L171_REQUIRED_SETTLEMENT_SCOPES,
    REQUIRED_SOURCE_CATEGORIES as L171_REQUIRED_SOURCE_CATEGORIES,
    make_universal_source_grounded_response_receipt,
)
from rdllm.universal_distribution_reliance_passport import (
    REQUIRED_DISTRIBUTION_SURFACES as L172_REQUIRED_DISTRIBUTION_SURFACES,
    REQUIRED_NEGATIVE_DISTRIBUTION_FAILURES as L172_REQUIRED_NEGATIVE_DISTRIBUTION_FAILURES,
    REQUIRED_PORTABLE_BINDINGS as L172_REQUIRED_PORTABLE_BINDINGS,
    REQUIRED_STATUS_CHANNELS as L172_REQUIRED_STATUS_CHANNELS,
    make_universal_distribution_reliance_passport,
)
from rdllm.universal_adversarial_provenance_quorum import (
    REQUIRED_ATTACK_CLASSES as L173_REQUIRED_ATTACK_CLASSES,
    REQUIRED_PROVENANCE_SIGNALS as L173_REQUIRED_PROVENANCE_SIGNALS,
    REQUIRED_RELIANCE_CONTEXTS as L173_REQUIRED_RELIANCE_CONTEXTS,
    make_universal_adversarial_provenance_quorum,
)
from rdllm.universal_procurement_regulatory_reliance_contract import (
    REQUIRED_ADOPTION_ROLES as L174_REQUIRED_ADOPTION_ROLES,
    REQUIRED_CONTRACTUAL_CONTROLS as L174_REQUIRED_CONTRACTUAL_CONTROLS,
    REQUIRED_JURISDICTION_MAPPINGS as L174_REQUIRED_JURISDICTION_MAPPINGS,
    REQUIRED_NEGATIVE_PROCUREMENT_FAILURES as L174_REQUIRED_NEGATIVE_PROCUREMENT_FAILURES,
    make_universal_procurement_regulatory_reliance_contract,
)
from rdllm.universal_provider_onboarding_migration_covenant import (
    REQUIRED_MIGRATION_ARTIFACTS as L175_REQUIRED_MIGRATION_ARTIFACTS,
    REQUIRED_NATIVE_API_SURFACES as L175_REQUIRED_NATIVE_API_SURFACES,
    REQUIRED_NEGATIVE_ONBOARDING_FAILURES as L175_REQUIRED_NEGATIVE_ONBOARDING_FAILURES,
    REQUIRED_PROVIDER_FAMILIES as L175_REQUIRED_PROVIDER_FAMILIES,
    REQUIRED_ROLLOUT_GATES as L175_REQUIRED_ROLLOUT_GATES,
    make_universal_provider_onboarding_migration_covenant,
)
from rdllm.universal_model_provider_registry import (
    REQUIRED_MODEL_LIFECYCLE_EVENTS as L176_REQUIRED_MODEL_LIFECYCLE_EVENTS,
    REQUIRED_MODEL_ROUTE_CLASSES as L176_REQUIRED_MODEL_ROUTE_CLASSES,
    REQUIRED_NEGATIVE_REGISTRY_FAILURES as L176_REQUIRED_NEGATIVE_REGISTRY_FAILURES,
    REQUIRED_PROVIDER_NAMESPACE_CLASSES as L176_REQUIRED_PROVIDER_NAMESPACE_CLASSES,
    REQUIRED_REGISTRY_SOURCES as L176_REQUIRED_REGISTRY_SOURCES,
    make_universal_model_provider_registry,
)
from rdllm.universal_source_footer_enforcement_contract import (
    REQUIRED_ENFORCEMENT_STAGES as L177_REQUIRED_ENFORCEMENT_STAGES,
    REQUIRED_FOOTER_ROW_FIELDS as L177_REQUIRED_FOOTER_ROW_FIELDS,
    REQUIRED_NEGATIVE_FOOTER_FAILURES as L177_REQUIRED_NEGATIVE_FOOTER_FAILURES,
    REQUIRED_RESPONSE_SURFACES as L177_REQUIRED_RESPONSE_SURFACES,
    REQUIRED_SOURCE_TYPES as L177_REQUIRED_SOURCE_TYPES,
    make_universal_source_footer_enforcement_contract,
)
from rdllm.universal_provider_catalog_coverage_contract import (
    REQUIRED_CATALOG_DISCOVERY_CHANNELS as L178_REQUIRED_CATALOG_DISCOVERY_CHANNELS,
    REQUIRED_NEGATIVE_CATALOG_FAILURES as L178_REQUIRED_NEGATIVE_CATALOG_FAILURES,
    REQUIRED_NORMALIZED_MODEL_FIELDS as L178_REQUIRED_NORMALIZED_MODEL_FIELDS,
    make_universal_provider_catalog_coverage_contract,
)
from rdllm.universal_runtime_route_binding_contract import (
    REQUIRED_NEGATIVE_RUNTIME_FAILURES as L179_REQUIRED_NEGATIVE_RUNTIME_FAILURES,
    REQUIRED_RUNTIME_BINDING_STAGES as L179_REQUIRED_RUNTIME_BINDING_STAGES,
    REQUIRED_RUNTIME_MODEL_FIELDS as L179_REQUIRED_RUNTIME_MODEL_FIELDS,
    REQUIRED_RUNTIME_SURFACES as L179_REQUIRED_RUNTIME_SURFACES,
    make_universal_runtime_route_binding_contract,
)
from rdllm.universal_verified_source_footer_contract import (
    REQUIRED_FOOTER_RESPONSE_SURFACES as L180_REQUIRED_FOOTER_RESPONSE_SURFACES,
    REQUIRED_FOOTER_VERIFICATION_STAGES as L180_REQUIRED_FOOTER_VERIFICATION_STAGES,
    REQUIRED_NEGATIVE_FOOTER_RELIANCE_FAILURES as L180_REQUIRED_NEGATIVE_FOOTER_RELIANCE_FAILURES,
    REQUIRED_SUPPORT_DIMENSIONS as L180_REQUIRED_SUPPORT_DIMENSIONS,
    REQUIRED_VERIFIED_FOOTER_FIELDS as L180_REQUIRED_VERIFIED_FOOTER_FIELDS,
    make_universal_verified_source_footer_contract,
)
from rdllm.universal_model_capability_coverage_contract import (
    REQUIRED_MODALITY_PAIRS as L181_REQUIRED_MODALITY_PAIRS,
    REQUIRED_MODEL_CAPABILITY_CLASSES as L181_REQUIRED_MODEL_CAPABILITY_CLASSES,
    REQUIRED_NEGATIVE_CAPABILITY_FAILURES as L181_REQUIRED_NEGATIVE_CAPABILITY_FAILURES,
    REQUIRED_OPERATION_SURFACES as L181_REQUIRED_OPERATION_SURFACES,
    make_universal_model_capability_coverage_contract,
)
from rdllm.universal_live_capability_discovery_contract import (
    REQUIRED_DISCOVERY_CHANNELS as L182_REQUIRED_DISCOVERY_CHANNELS,
    REQUIRED_NEGATIVE_DISCOVERY_FAILURES as L182_REQUIRED_NEGATIVE_DISCOVERY_FAILURES,
    REQUIRED_PROVIDER_FAMILIES as L182_REQUIRED_PROVIDER_FAMILIES,
    make_universal_live_capability_discovery_contract,
)
from rdllm.universal_native_source_annotation_contract import (
    REQUIRED_NATIVE_ANNOTATION_FORMATS as L183_REQUIRED_NATIVE_ANNOTATION_FORMATS,
    REQUIRED_NEGATIVE_NATIVE_ANNOTATION_FAILURES as L183_REQUIRED_NEGATIVE_NATIVE_ANNOTATION_FAILURES,
    REQUIRED_NORMALIZED_FOOTER_FIELDS as L183_REQUIRED_NORMALIZED_FOOTER_FIELDS,
    make_universal_native_source_annotation_contract,
)
from rdllm.universal_claim_evidence_footer_verification_contract import (
    REQUIRED_NEGATIVE_CLAIM_EVIDENCE_FAILURES as L184_REQUIRED_NEGATIVE_CLAIM_EVIDENCE_FAILURES,
    REQUIRED_VERIFICATION_DIMENSIONS as L184_REQUIRED_VERIFICATION_DIMENSIONS,
    REQUIRED_VERIFIED_FOOTER_FIELDS as L184_REQUIRED_VERIFIED_FOOTER_FIELDS,
    make_universal_claim_evidence_footer_verification_contract,
)
from rdllm.universal_provider_meter_normalization_contract import (
    REQUIRED_NEGATIVE_PROVIDER_METER_FAILURES as L185_REQUIRED_NEGATIVE_PROVIDER_METER_FAILURES,
    REQUIRED_NORMALIZED_METER_FIELDS as L185_REQUIRED_NORMALIZED_METER_FIELDS,
    REQUIRED_PROVIDER_METER_SURFACES as L185_REQUIRED_PROVIDER_METER_SURFACES,
    make_universal_provider_meter_normalization_contract,
)
from rdllm.universal_provider_response_state_normalization_contract import (
    REQUIRED_NEGATIVE_RESPONSE_STATE_FAILURES as L186_REQUIRED_NEGATIVE_RESPONSE_STATE_FAILURES,
    REQUIRED_NORMALIZED_RESPONSE_STATE_FIELDS as L186_REQUIRED_NORMALIZED_RESPONSE_STATE_FIELDS,
    REQUIRED_PROVIDER_RESPONSE_STATE_SURFACES as L186_REQUIRED_PROVIDER_RESPONSE_STATE_SURFACES,
    make_universal_provider_response_state_normalization_contract,
)
from rdllm.universal_negotiated_invocation_enforcement import (
    make_universal_negotiated_invocation_enforcement,
)
from rdllm.universal_provider_adapter_harness import (
    make_universal_provider_adapter_harness,
)
from rdllm.universal_provider_drift_sentinel import (
    make_universal_provider_drift_sentinel,
)


ARTIFACTS = ROOT / "artifacts"
SIGNING_SECRET = "secret"
ISSUER = "rdllm-local-demo"
CREATED_AT = "2026-06-03T00:00:00Z"
REPLAY_ISSUED_AT = "2026-05-31T00:00:00Z"
L168_TO_L186_PUBLIC_ARTIFACTS = (
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
)


def load(name: str) -> dict[str, Any]:
    return json.loads((ARTIFACTS / f"{name}.json").read_text(encoding="utf-8"))


def save(name: str, payload: dict[str, Any]) -> None:
    (ARTIFACTS / f"{name}.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sync_packaged_reference_artifacts() -> None:
    """Keep installable reference data aligned with regenerated public artifacts."""
    PACKAGED_REFERENCE_ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    for name in PACKAGED_REFERENCE_ARTIFACTS:
        shutil.copyfile(
            ARTIFACTS / f"{name}.json",
            PACKAGED_REFERENCE_ARTIFACT_DIR / f"{name}.json",
        )


def artifact_ref(name: str) -> dict[str, str]:
    return {ARTIFACT_REF_KEY: f"artifacts/{name}.json"}


def compact_replay_refs(
    payload: dict[str, Any],
    refs: dict[str, str],
) -> dict[str, Any]:
    compact = dict(payload)
    for key, artifact_name in refs.items():
        if key in compact:
            compact[key] = artifact_ref(artifact_name)
    return compact


def regenerate_certification_report() -> dict[str, Any]:
    report = run_certification(
        ROOT / "examples" / "sample_corpus.json",
        restricted_corpus_path=ROOT / "examples" / "restricted_corpus.json",
        signing_secret=SIGNING_SECRET,
    )
    save("certification_report", report)
    return report


def regenerate_certification_attestation(
    certification_report: dict[str, Any],
) -> dict[str, Any]:
    attestation = make_certification_attestation(
        certification_report,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("certification_attestation", attestation)
    return attestation


def regenerate_provider_card(certification_report: dict[str, Any]) -> dict[str, Any]:
    card = make_provider_attribution_card(
        load("demo_ledger"),
        certification_report=certification_report,
        issuer=ISSUER,
        provider="provider:rdllm-reference",
        model_id="rdllm-reference-model",
        model_version="2026-06",
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("provider_attribution_card", card)
    return card


def artifact_specs_from_bundle(bundle: dict[str, Any]) -> list[str]:
    specs: list[str] = []
    for artifact in bundle.get("artifacts", []):
        name = str(artifact["name"])
        artifact_type = str(artifact["artifact_type"])
        path = ARTIFACTS / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(path)
        specs.append(f"{name}:{artifact_type}:{path}")
    return specs


def append_existing_artifact_specs(
    specs: list[str],
    artifact_names: tuple[str, ...],
) -> list[str]:
    appended = list(specs)
    existing = {spec.split(":", 1)[0] for spec in appended}
    for name in artifact_names:
        path = ARTIFACTS / f"{name}.json"
        if path.exists() and name not in existing:
            appended.append(f"{name}:{name}:{path}")
            existing.add(name)
    return appended


def refresh_embedded_artifacts(payload: dict[str, Any]) -> dict[str, Any]:
    refreshed = dict(payload)
    for path in ARTIFACTS.glob("*.json"):
        name = path.stem
        if name in refreshed and isinstance(refreshed[name], dict):
            refreshed[name] = load(name)
    return refreshed


def _load_example(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "examples" / f"{name}.json").read_text(encoding="utf-8"))


def bootstrap_certification_report() -> dict[str, Any]:
    """Create a temporary passed certification object to break fixture cycles."""

    report = load("certification_report") if (ARTIFACTS / "certification_report.json").exists() else {}
    report = dict(report)
    report.setdefault("certification_version", "rdllm-certification/v1")
    report.setdefault("suite", "rdllm-reference-conformance")
    report.setdefault("issued_at", REPLAY_ISSUED_AT)
    report.setdefault("levels", {})
    report.setdefault("cases", [])
    report["summary"] = {
        "status": "passed",
        "case_count": int(report.get("summary", {}).get("case_count", 187) or 187),
        "passed": int(report.get("summary", {}).get("case_count", 187) or 187),
        "failed": 0,
        "score": 1.0,
        "highest_level": "RDLLM-L186",
    }
    report["report_hash"] = hash_payload(
        {key: value for key, value in report.items() if key not in {"report_hash", "signature"}}
    )
    return report


def _evidence_region_binding_parts(event: Any) -> dict[str, list[dict[str, Any]]]:
    references = {reference.label: reference for reference in event.source_references}
    snapshots_by_label: dict[str, dict[str, Any]] = {}
    region_counts: dict[str, int] = {}
    claim_region_links: list[dict[str, Any]] = []
    negative_region_links: list[dict[str, Any]] = []
    for claim_index, support in enumerate(event.claim_support, start=1):
        if not support.supported or not support.source_label or not support.evidence_span_hash:
            continue
        reference = references.get(support.source_label)
        if reference is None:
            continue
        region_counts[support.source_label] = region_counts.get(support.source_label, 0) + 1
        region_number = region_counts[support.source_label]
        source_id = support.chunk_id
        region_id = f"region:{source_id}:{region_number}"
        claim_id = f"claim_{claim_index}"
        snapshot = snapshots_by_label.setdefault(
            support.source_label,
            {
                "source_id": source_id,
                "source_label": support.source_label,
                "work_id": support.work_id,
                "chunk_id": support.chunk_id,
                "source_uri": reference.source_uri,
                "content_hash": reference.content_hash,
                "source_version_hash": reference.content_hash,
                "regions": [],
            },
        )
        snapshot["regions"].append(
            {
                "region_id": region_id,
                "region_type": "text_span",
                "page": 1,
                "line_start": 1,
                "line_end": 1,
                "start_char": support.evidence_start_char,
                "end_char": support.evidence_end_char,
                "evidence_span_prefixes": [support.evidence_span_hash[:12]],
                "claim_ids": [claim_id],
                "region_text_hash": support.evidence_span_hash,
            }
        )
        link = {
            "claim_id": claim_id,
            "claim_index": claim_index,
            "source_label": support.source_label,
            "source_id": source_id,
            "chunk_id": support.chunk_id,
            "evidence_span_prefix": support.evidence_span_hash[:12],
            "region_id": region_id,
            "expected_support": True,
            "evidence_hash": support.evidence_span_hash,
            "start_char": support.evidence_start_char,
            "end_char": support.evidence_end_char,
        }
        claim_region_links.append(link)
        negative_region_links.append(
            {
                **link,
                "control_id": f"wrong-region:{source_id}:{region_number}",
                "region_id": f"region:{source_id}:wrong:{region_number}",
                "evidence_hash": stable_hash(f"wrong-region:{support.evidence_span_hash}"),
                "expected_rejected": True,
            }
        )
    return {
        "source_snapshots": list(snapshots_by_label.values()),
        "claim_region_links": claim_region_links,
        "negative_region_links": negative_region_links,
    }


def regenerate_core_response_chain(
    certification_report: dict[str, Any],
) -> dict[str, Any]:
    """Rebuild the demo response, footer, envelope, proof, and gateway chain."""

    engine = RoyaltyDrivenLLM.from_corpus_file(ROOT / "examples" / "sample_corpus.json")
    event = engine.generate(
        "How should AI systems prove attribution and pay creators when using text sources?",
        gross_revenue="1.00",
    )
    ledger = RoyaltyLedger()
    ledger.record(event)
    save("demo_ledger", ledger.to_dict())

    receipt = make_attribution_receipt(
        event,
        issuer=ISSUER,
        model_id="rdllm-reference-model",
        model_version="2026-06",
        signing_secret=SIGNING_SECRET,
    )
    save("receipt", receipt)
    save("public_receipt", public_receipt(receipt))
    trace = make_trace_exchange(event, receipt=receipt)
    save("trace_exchange", trace)
    save("conformance_trace_exchange", trace)

    answer_card = make_answer_provenance_card(
        event,
        receipt=receipt,
        trace=trace,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("answer_provenance_card", answer_card)
    source_report = make_source_verification_report(
        event,
        engine,
        answer_card=answer_card,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("source_verification_report", source_report)
    license_contract = make_creator_license_contract(
        creators=engine.creators,
        works=engine.works,
        issuer=ISSUER,
        provider="provider:rdllm-reference",
        effective_at=CREATED_AT,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("creator_license_contract", license_contract)
    source_confidence = make_source_confidence_report(
        answer_card=answer_card,
        source_verification_report=source_report,
        creator_license_contract=license_contract,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("source_confidence_report", source_confidence)

    provider_card = make_provider_attribution_card(
        ledger.to_dict(),
        certification_report=certification_report,
        issuer=ISSUER,
        provider="provider:rdllm-reference",
        model_id="rdllm-reference-model",
        model_version="2026-06",
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("provider_attribution_card", provider_card)
    base_envelope = make_response_envelope(
        event,
        answer_card=answer_card,
        source_verification_report=source_report,
        source_confidence_report=source_confidence,
        creator_license_contract=license_contract,
        public_receipt=public_receipt(receipt),
        provider_card=provider_card,
        certification_report=certification_report,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("response_envelope_base", base_envelope)
    citation_footer = make_citation_footer_contract(
        response_envelope=base_envelope,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("citation_footer_contract", citation_footer)
    snapshots = _load_example("source_availability_snapshots").get("snapshots", [])
    source_availability = make_source_availability_report(
        event,
        engine,
        snapshots,
        answer_card=answer_card,
        source_verification_report=source_report,
        citation_footer_contract=citation_footer,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("source_availability_report", source_availability)
    evidence_sufficiency = make_evidence_sufficiency_report(
        event,
        engine,
        answer_card=answer_card,
        source_verification_report=source_report,
        source_availability_report=source_availability,
        citation_footer_contract=citation_footer,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("evidence_sufficiency_report", evidence_sufficiency)
    counterevidence = make_counterevidence_report(
        event,
        engine,
        answer_card=answer_card,
        source_verification_report=source_report,
        source_availability_report=source_availability,
        evidence_sufficiency_report=evidence_sufficiency,
        citation_footer_contract=citation_footer,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("counterevidence_report", counterevidence)
    late_envelope = make_response_envelope(
        event,
        answer_card=answer_card,
        source_verification_report=source_report,
        source_confidence_report=source_confidence,
        creator_license_contract=license_contract,
        citation_footer_contract=citation_footer,
        source_availability_report=source_availability,
        evidence_sufficiency_report=evidence_sufficiency,
        counterevidence_report=counterevidence,
        trace_exchange=trace,
        public_receipt=public_receipt(receipt),
        provider_card=provider_card,
        certification_report=certification_report,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("response_envelope_late_base", late_envelope)
    answer_coverage = make_answer_claim_coverage_report(
        rendered_output=event.output,
        event_id=event.event_id,
        event_hash=event.event_hash,
        answer_hash=stable_hash(event.answer_text),
        answer_card=answer_card,
        source_verification_report=source_report,
        evidence_sufficiency_report=evidence_sufficiency,
        counterevidence_report=counterevidence,
        citation_footer_contract=citation_footer,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("answer_claim_coverage_report", answer_coverage)
    coverage_envelope = make_response_envelope(
        event,
        answer_card=answer_card,
        source_verification_report=source_report,
        source_confidence_report=source_confidence,
        creator_license_contract=license_contract,
        citation_footer_contract=citation_footer,
        source_availability_report=source_availability,
        evidence_sufficiency_report=evidence_sufficiency,
        counterevidence_report=counterevidence,
        answer_claim_coverage_report=answer_coverage,
        trace_exchange=trace,
        public_receipt=public_receipt(receipt),
        provider_card=provider_card,
        certification_report=certification_report,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("response_envelope_coverage_base", coverage_envelope)
    context_closure = make_generation_context_closure_report(
        trace_exchange=trace,
        source_verification_report=source_report,
        answer_claim_coverage_report=answer_coverage,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("generation_context_closure_report", context_closure)
    context_envelope = make_response_envelope(
        event,
        answer_card=answer_card,
        source_verification_report=source_report,
        source_confidence_report=source_confidence,
        creator_license_contract=license_contract,
        citation_footer_contract=citation_footer,
        source_availability_report=source_availability,
        evidence_sufficiency_report=evidence_sufficiency,
        counterevidence_report=counterevidence,
        answer_claim_coverage_report=answer_coverage,
        trace_exchange=trace,
        generation_context_closure_report=context_closure,
        public_receipt=public_receipt(receipt),
        provider_card=provider_card,
        certification_report=certification_report,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("response_envelope_context_base", context_envelope)
    source_boundary = make_source_boundary_report(
        trace_exchange=trace,
        source_verification_report=source_report,
        generation_context_closure_report=context_closure,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("source_boundary_report", source_boundary)
    boundary_envelope = make_response_envelope(
        event,
        answer_card=answer_card,
        source_verification_report=source_report,
        source_confidence_report=source_confidence,
        creator_license_contract=license_contract,
        citation_footer_contract=citation_footer,
        source_availability_report=source_availability,
        evidence_sufficiency_report=evidence_sufficiency,
        counterevidence_report=counterevidence,
        answer_claim_coverage_report=answer_coverage,
        trace_exchange=trace,
        generation_context_closure_report=context_closure,
        source_boundary_report=source_boundary,
        public_receipt=public_receipt(receipt),
        provider_card=provider_card,
        certification_report=certification_report,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("response_envelope_boundary_base", boundary_envelope)
    source_authenticity = make_source_authenticity_report(
        source_availability_report=source_availability,
        source_boundary_report=source_boundary,
        creator_license_contract=license_contract,
        source_authenticity_signals=_load_example("source_authenticity_signals").get(
            "signals",
            [],
        ),
        source_confidence_report=source_confidence,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("source_authenticity_report", source_authenticity)
    response_envelope = make_response_envelope(
        event,
        answer_card=answer_card,
        source_verification_report=source_report,
        source_confidence_report=source_confidence,
        creator_license_contract=license_contract,
        citation_footer_contract=citation_footer,
        source_availability_report=source_availability,
        evidence_sufficiency_report=evidence_sufficiency,
        counterevidence_report=counterevidence,
        answer_claim_coverage_report=answer_coverage,
        trace_exchange=trace,
        generation_context_closure_report=context_closure,
        source_boundary_report=source_boundary,
        source_authenticity_report=source_authenticity,
        public_receipt=public_receipt(receipt),
        provider_card=provider_card,
        certification_report=certification_report,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("response_envelope", response_envelope)
    rendered_audit = make_rendered_attribution_audit(
        response_envelope=response_envelope,
        citation_footer_contract=citation_footer,
        source_availability_report=source_availability,
        evidence_sufficiency_report=evidence_sufficiency,
        counterevidence_report=counterevidence,
        answer_claim_coverage_report=answer_coverage,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("rendered_attribution_audit", rendered_audit)
    region_input = refresh_embedded_artifacts(load("evidence_region_binding_input"))
    region_input["response_envelope"] = response_envelope
    region_input["citation_footer_contract"] = citation_footer
    region_input["rendered_attribution_audit"] = rendered_audit
    region_parts = _evidence_region_binding_parts(event)
    region_input["source_snapshots"] = region_parts["source_snapshots"]
    region_input["claim_region_links"] = region_parts["claim_region_links"]
    region_input["negative_region_links"] = region_parts["negative_region_links"]
    save("evidence_region_binding_input", region_input)
    save(
        "evidence_region_binding_report",
        make_evidence_region_binding_report(
            region_input,
            issuer=ISSUER,
            created_at=CREATED_AT,
            signing_secret=SIGNING_SECRET,
        ),
    )

    capsule = make_attribution_capsule(
        response_envelope=response_envelope,
        federation_handshake=load("federation_handshake"),
        attribution_exchange=load("attribution_exchange"),
        conformance_vector_pack=load("conformance_vector_pack"),
        provider_card=provider_card,
        certification_report=certification_report,
        integration_profile=load("integration_profile"),
        discovery_manifest=load("discovery_manifest"),
        assurance_bundle=load("assurance_bundle"),
        semantic_text_attribution_report=load("semantic_text_attribution_report"),
        creator_license_contract=license_contract,
        training_summary=load("training_content_summary"),
        provenance_evaluation_report=load("provenance_evaluation_report"),
        counterfactual_report=load("counterfactual_report"),
        media_attribution_report=load("media_attribution_report"),
        model_signal_report=load("model_signal_report"),
        rights_remediation_report=load("rights_remediation_report"),
        source_confidence_report=source_confidence,
        citation_footer_contract=citation_footer,
        private_audit_challenge=load("private_audit_challenge"),
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("attribution_capsule", capsule)
    release_gate = make_release_gate_report(
        response_envelope=response_envelope,
        attribution_capsule=capsule,
        creator_license_contract=license_contract,
        provider_card=provider_card,
        certification_report=certification_report,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("release_gate", release_gate)
    proof_response = make_proof_carrying_response(
        response_envelope=response_envelope,
        attribution_capsule=capsule,
        release_gate=release_gate,
        creator_license_contract=license_contract,
        provider_card=provider_card,
        certification_report=certification_report,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("proof_carrying_response", proof_response)
    gateway = make_serving_gateway_report(
        proof_carrying_response=proof_response,
        request_id="req:rdllm-reference-demo",
        provider="provider:rdllm-reference",
        model_id="rdllm-reference-model",
        model_version="2026-06",
        route_id="route:demo",
        prompt=event.prompt,
        raw_model_output=event.answer_text,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("serving_gateway_report", gateway)
    return {
        "event": event.to_dict(),
        "response_envelope": response_envelope,
        "citation_footer_contract": citation_footer,
        "source_footer_ready_input": rendered_audit,
        "proof_carrying_response": proof_response,
        "serving_gateway_report": gateway,
    }


def regenerate_grounded_source_footer() -> dict[str, Any]:
    footer_input = refresh_embedded_artifacts(load("grounded_source_footer_input"))
    footer_input["citation_footer_contract"] = load("citation_footer_contract")
    footer_input["source_confidence_report"] = load("source_confidence_report")
    footer_input["source_availability_report"] = load("source_availability_report")
    footer_input["rendered_attribution_audit"] = load("rendered_attribution_audit")
    footer_input["evidence_region_binding_report"] = load(
        "evidence_region_binding_report"
    )
    footer_input["citation_reliance_receipt"] = load("citation_reliance_receipt")
    footer_input["license_transaction_receipt"] = load("license_transaction_receipt")
    save("grounded_source_footer_input", footer_input)
    receipt = make_grounded_source_footer(
        footer_input,
        issuer=ISSUER,
        issued_at=REPLAY_ISSUED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("grounded_source_footer", receipt)
    return receipt


def regenerate_source_footer_delivery() -> dict[str, Any]:
    delivery_input = refresh_embedded_artifacts(load("source_footer_delivery_input"))
    delivery_input["grounded_source_footer"] = regenerate_grounded_source_footer()
    delivery_input["response_envelope"] = load("response_envelope")
    delivery_input["proof_carrying_response"] = load("proof_carrying_response")
    delivery_input["serving_gateway_report"] = load("serving_gateway_report")
    save("source_footer_delivery_input", delivery_input)
    receipt = make_source_footer_delivery_receipt(
        delivery_input,
        issuer=ISSUER,
        issued_at=REPLAY_ISSUED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("source_footer_delivery", receipt)
    return receipt


def regenerate_streaming_conversation_tool_artifacts() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    proof_response = load("proof_carrying_response")
    gateway_report = load("serving_gateway_report")
    stream = make_streaming_attribution_manifest(
        proof_carrying_response=proof_response,
        serving_gateway_report=gateway_report,
        chunk_size=96,
        issuer=ISSUER,
        created_at=REPLAY_ISSUED_AT,
        proof_verified_at=REPLAY_ISSUED_AT,
        gateway_verified_at=REPLAY_ISSUED_AT,
        stream_started_at=REPLAY_ISSUED_AT,
        stream_completed_at=REPLAY_ISSUED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("streaming_attribution_manifest", stream)
    conversation = make_conversation_attribution_ledger(
        conversation_id="conv_demo_1",
        session_state_id="session:demo",
        turns=[
            {
                "turn_id": "turn-1",
                "depends_on_turn_ids": [],
                "proof_carrying_response": proof_response,
                "serving_gateway_report": gateway_report,
                "streaming_attribution_manifest": stream,
            },
            {
                "turn_id": "turn-2",
                "depends_on_turn_ids": ["turn-1"],
                "proof_carrying_response": proof_response,
                "serving_gateway_report": gateway_report,
                "streaming_attribution_manifest": stream,
            },
        ],
        issuer=ISSUER,
        created_at=REPLAY_ISSUED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("conversation_attribution_ledger", conversation)
    tool = make_agent_tool_attribution_ledger(
        proof_carrying_response=proof_response,
        trace_exchange=load("conformance_trace_exchange"),
        conversation_attribution_ledger=conversation,
        issuer=ISSUER,
        created_at=REPLAY_ISSUED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("agent_tool_attribution_ledger", tool)
    return stream, conversation, tool


def regenerate_l82_to_l85_emission_chain() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    """Refresh evidence locks, emission enforcement, witness, and transparency."""

    evidence_lock = make_evidence_locked_generation_report(
        response_envelope=load("response_envelope"),
        answer_claim_coverage_report=load("answer_claim_coverage_report"),
        generation_context_closure_report=load("generation_context_closure_report"),
        citation_footer_contract=load("citation_footer_contract"),
        rendered_attribution_audit=load("rendered_attribution_audit"),
        training_memory_provenance=load("training_memory_provenance"),
        lock_created_at="2026-05-30T23:59:59Z",
        generation_started_at=REPLAY_ISSUED_AT,
        issuer=ISSUER,
        created_at=REPLAY_ISSUED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("evidence_locked_generation", evidence_lock)

    emission = make_emission_evidence_enforcement_report(
        response_envelope=load("response_envelope"),
        answer_claim_coverage_report=load("answer_claim_coverage_report"),
        evidence_locked_generation=evidence_lock,
        proof_carrying_response=load("proof_carrying_response"),
        serving_gateway_report=load("serving_gateway_report"),
        streaming_attribution_manifest=load("streaming_attribution_manifest"),
        issuer=ISSUER,
        created_at=REPLAY_ISSUED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("emission_evidence_enforcement", emission)

    streaming = load("streaming_attribution_manifest")
    witnesses = [
        ("witness-a", "secret-a"),
        ("witness-b", "secret-b"),
        ("witness-c", "secret-c"),
    ]
    live_witness = make_live_emission_witness_report(
        emission_evidence_enforcement=emission,
        streaming_attribution_manifest=streaming,
        witnesses=witnesses,
        required_quorum=2,
        minimum_independent_organizations=2,
        issuer=ISSUER,
        created_at=REPLAY_ISSUED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("live_emission_witness", live_witness)

    prefix_log = make_live_emission_transparency_log(
        live_witness,
        log_id="live-prefix",
        include_attestations=False,
    )
    latest_log = make_live_emission_transparency_log(
        live_witness,
        log_id="live-latest",
        existing_entries=prefix_log["entries"],
    )
    save("live_emission_transparency_prefix_log", prefix_log)
    save("live_emission_transparency_log", latest_log)
    transparency = make_live_emission_transparency_report(
        live_emission_witness=live_witness,
        transparency_logs=[("live-prefix", prefix_log), ("live-latest", latest_log)],
        issuer=ISSUER,
        created_at=REPLAY_ISSUED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("live_emission_transparency", transparency)
    return emission, live_witness, transparency


def regenerate_l104_to_l108_replay_chain() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    """Refresh the replay fixtures that carry source footers into client use.

    These artifacts intentionally form a narrow public chain:
    L104 validates the current provider/discovery/integration surface, L105
    proves the client enforced that surface before rendering, and L106-L108
    carry those source labels through memory, hidden reasoning, and
    post-training signals.
    """

    foundation_input = resolve_artifact_refs(
        refresh_embedded_artifacts(load("foundation_api_profile_input")),
        base_path=ROOT,
    )
    foundation_input["provider_card"] = load("provider_attribution_card")
    foundation_input["assurance_bundle"] = load("assurance_bundle")
    foundation_input["certification_attestation"] = load("certification_attestation")
    foundation_profile = make_foundation_api_profile(
        foundation_input,
        issuer=ISSUER,
        issued_at=REPLAY_ISSUED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save(
        "foundation_api_profile_input",
        compact_replay_refs(
            foundation_input,
            {"source_footer_delivery_input": "source_footer_delivery_input"},
        ),
    )
    save("foundation_api_profile", foundation_profile)

    client_input = resolve_artifact_refs(
        refresh_embedded_artifacts(load("client_attribution_input")),
        base_path=ROOT,
    )
    client_input["foundation_api_profile_input"] = foundation_input
    client_input["foundation_api_profile"] = foundation_profile
    client_input["response_headers"] = dict(
        foundation_profile["response_metadata_contract"]["header_values"]
    )
    response_envelope = load("response_envelope")
    source_footer_delivery = load("source_footer_delivery")
    response_payload = client_input.setdefault("response_payload", {})
    response_payload.setdefault("embedded_artifacts", {})[
        "response_envelope"
    ] = response_envelope
    response_payload.setdefault("embedded_artifacts", {})[
        "source_footer_delivery"
    ] = source_footer_delivery
    response_payload.setdefault("response", {})["rendered_output"] = response_envelope[
        "response"
    ]["rendered_output"]
    response_payload.setdefault("response", {})["source_labels"] = response_envelope[
        "response"
    ].get("source_labels", [])
    response_payload.setdefault("verification", {})[
        "foundation_attribution_profile"
    ] = foundation_profile
    client_receipt = make_client_attribution_enforcement_receipt(
        client_input,
        issuer=ISSUER,
        issued_at=REPLAY_ISSUED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save(
        "client_attribution_input",
        compact_replay_refs(
            client_input,
            {
                "foundation_api_profile_input": "foundation_api_profile_input",
                "source_footer_delivery_input": "source_footer_delivery_input",
            },
        ),
    )
    save("client_attribution_enforcement", client_receipt)

    memory_input = resolve_artifact_refs(
        refresh_embedded_artifacts(load("persistent_memory_input")),
        base_path=ROOT,
    )
    memory_input["client_attribution_input"] = client_input
    memory_input["client_attribution_enforcement"] = client_receipt
    memory_input["foundation_api_profile"] = foundation_profile
    client_hash = client_receipt["client_enforcement_hash"]
    rendered_output_hash = client_receipt["client_decision"]["rendered_output_hash"]
    source_footer_hash = load("source_footer_delivery")["source_footer_delivery_hash"]
    for entry in memory_input.get("memory_entries", []):
        for origin in entry.get("origin_artifacts", []):
            if origin.get("artifact_type") == "client_attribution_enforcement":
                origin["artifact_hash"] = client_hash
            if origin.get("artifact_type") == "source_footer_delivery":
                origin["artifact_hash"] = source_footer_hash
        entry["origin_artifact_hashes"] = [
            origin["artifact_hash"]
            for origin in entry.get("origin_artifacts", [])
            if origin.get("artifact_hash")
        ]
    for read in memory_input.get("memory_reads", []):
        read["client_enforcement_hash"] = client_hash
        read["rendered_output_hash"] = rendered_output_hash
    memory_receipt = make_persistent_memory_provenance_receipt(
        memory_input,
        issuer=ISSUER,
        issued_at=REPLAY_ISSUED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save(
        "persistent_memory_input",
        compact_replay_refs(
            memory_input,
            {
                "client_attribution_input": "client_attribution_input",
                "source_footer_delivery_input": "source_footer_delivery_input",
            },
        ),
    )
    save("persistent_memory_provenance", memory_receipt)

    private_input = resolve_artifact_refs(
        refresh_embedded_artifacts(load("private_reasoning_input")),
        base_path=ROOT,
    )
    private_input["client_attribution_input"] = client_input
    private_input["client_attribution_enforcement"] = client_receipt
    private_input["persistent_memory_input"] = memory_input
    private_input["persistent_memory_provenance"] = memory_receipt
    memory_hash = memory_receipt["persistent_memory_provenance_hash"]
    reasoning_input_hashes = [source_footer_hash, client_hash, memory_hash]
    for step in private_input.get("reasoning_steps", []):
        step["input_artifact_hashes"] = reasoning_input_hashes
        step["rendered_output_hash"] = rendered_output_hash
    private_receipt = make_private_reasoning_attribution_receipt(
        private_input,
        issuer=ISSUER,
        issued_at=REPLAY_ISSUED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save(
        "private_reasoning_input",
        compact_replay_refs(
            private_input,
            {
                "client_attribution_input": "client_attribution_input",
                "persistent_memory_input": "persistent_memory_input",
                "source_footer_delivery_input": "source_footer_delivery_input",
            },
        ),
    )
    save("private_reasoning_attribution", private_receipt)

    post_training_input = resolve_artifact_refs(
        refresh_embedded_artifacts(load("post_training_signal_input")),
        base_path=ROOT,
    )
    post_training_input["private_reasoning_input"] = private_input
    post_training_input["private_reasoning_attribution"] = private_receipt
    private_hash = private_receipt["private_reasoning_attribution_hash"]
    model_lineage_hash = post_training_input.get(
        "model_lineage_attribution_report", {}
    ).get("report_hash", "")
    signal_input_hashes = [
        value for value in (private_hash, model_lineage_hash) if value
    ]
    for signal in post_training_input.get("post_training_signals", []):
        signal["input_artifact_hashes"] = signal_input_hashes
        signal["upstream_artifact_hashes"] = signal_input_hashes
    post_training_receipt = make_post_training_signal_provenance_receipt(
        post_training_input,
        issuer=ISSUER,
        issued_at=REPLAY_ISSUED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save(
        "post_training_signal_input",
        compact_replay_refs(
            post_training_input,
            {"private_reasoning_input": "private_reasoning_input"},
        ),
    )
    save("post_training_signal_provenance", post_training_receipt)

    return (
        foundation_profile,
        client_receipt,
        memory_receipt,
        private_receipt,
        post_training_receipt,
    )


def regenerate_assurance_bundle(
    extra_artifact_names: tuple[str, ...] = (),
) -> dict[str, Any]:
    previous = load("assurance_bundle")
    specs = append_existing_artifact_specs(
        artifact_specs_from_bundle(previous),
        extra_artifact_names,
    )
    bundle = make_assurance_bundle(
        _load_assurance_artifacts(specs),
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("assurance_bundle", bundle)
    return bundle


def regenerate_integration_profile(assurance_bundle: dict[str, Any]) -> dict[str, Any]:
    profile = make_integration_profile(
        provider_card=load("provider_attribution_card"),
        certification_report=load("certification_report"),
        response_envelope=load("response_envelope"),
        assurance_bundle=assurance_bundle,
        certification_attestation=load("certification_attestation"),
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("integration_profile", profile)
    return profile


def regenerate_discovery_manifest(
    assurance_bundle: dict[str, Any],
    integration_profile: dict[str, Any],
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "provider_card": load("provider_attribution_card"),
        "certification_report": load("certification_report"),
        "integration_profile": integration_profile,
        "response_envelope": load("response_envelope"),
        "assurance_bundle": assurance_bundle,
        "issuer": ISSUER,
        "created_at": CREATED_AT,
        "signing_secret": SIGNING_SECRET,
    }
    excluded = {
        "provider_card",
        "certification_report",
        "integration_profile",
        "response_envelope",
        "assurance_bundle",
        "issuer",
        "created_at",
        "signing_secret",
        "proof_dependency_graph",
    }
    for name in inspect.signature(make_discovery_manifest).parameters:
        if name in excluded:
            continue
        path = ARTIFACTS / f"{name}.json"
        if path.exists():
            kwargs[name] = json.loads(path.read_text(encoding="utf-8"))
    manifest = make_discovery_manifest(**kwargs)
    save("discovery_manifest", manifest)
    return manifest


def regenerate_calibrated_attribution_report() -> dict[str, Any]:
    report = make_calibrated_attribution_report(
        response_envelope=load("response_envelope"),
        source_confidence_report=load("source_confidence_report"),
        evidence_sufficiency_report=load("evidence_sufficiency_report"),
        provenance_evaluation_report=load("provenance_evaluation_report"),
        decision_provenance_report=load("decision_provenance_report"),
        release_gate=load("release_gate"),
        trace_exchange=load("trace_exchange"),
        attribution_capsule=load("attribution_capsule"),
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("calibrated_attribution_report", report)
    return report


def regenerate_l157_to_l160() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    harness_input = refresh_embedded_artifacts(load("universal_provider_adapter_harness_input"))
    provider_mode_hashes = {
        "kernel_hash": load("universal_foundation_adoption_kernel")[
            "universal_foundation_adoption_kernel_hash"
        ],
        "wire_protocol_hash": load("universal_provider_wire_protocol")[
            "universal_provider_wire_protocol_hash"
        ],
        "claim_provenance_hash": load("universal_claim_provenance_envelope")[
            "universal_claim_provenance_envelope_hash"
        ],
        "source_footer_delivery_hash": load("source_footer_delivery")[
            "source_footer_delivery_hash"
        ],
        "client_enforcement_hash": load("client_attribution_enforcement")[
            "client_enforcement_hash"
        ],
    }
    for row in harness_input.get("provider_mode_rows", {}).values():
        row.update(provider_mode_hashes)
    save("universal_provider_adapter_harness_input", harness_input)
    harness = make_universal_provider_adapter_harness(
        harness_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_provider_adapter_harness", harness)

    sentinel_input = refresh_embedded_artifacts(load("universal_provider_drift_sentinel_input"))
    sentinel_input["universal_provider_adapter_harness"] = harness
    save("universal_provider_drift_sentinel_input", sentinel_input)
    sentinel = make_universal_provider_drift_sentinel(
        sentinel_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_provider_drift_sentinel", sentinel)

    handshake_input = refresh_embedded_artifacts(
        load("universal_attribution_negotiation_handshake_input")
    )
    handshake_input["universal_provider_adapter_harness"] = harness
    handshake_input["universal_provider_drift_sentinel"] = sentinel
    save("universal_attribution_negotiation_handshake_input", handshake_input)
    handshake = make_universal_attribution_negotiation_handshake(
        handshake_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_attribution_negotiation_handshake", handshake)

    enforcement_input = refresh_embedded_artifacts(
        load("universal_negotiated_invocation_enforcement_input")
    )
    enforcement_input["universal_provider_adapter_harness"] = harness
    enforcement_input["universal_provider_drift_sentinel"] = sentinel
    enforcement_input["universal_attribution_negotiation_handshake"] = handshake
    save("universal_negotiated_invocation_enforcement_input", enforcement_input)
    enforcement = make_universal_negotiated_invocation_enforcement(
        enforcement_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_negotiated_invocation_enforcement", enforcement)

    return harness, sentinel, handshake, enforcement


def regenerate_l161_federation() -> dict[str, Any]:
    federation_input: dict[str, Any] = {
        name: load(name) for name in L161_REQUIRED_CORE_ARTIFACTS
    }
    federation_input["federation_role_rows"] = {
        role: {
            "entity_id_hash": stable_hash(f"reference-l161:entity:{role}"),
            "jwks_thumbprint_hash": stable_hash(f"reference-l161:jwks:{role}"),
            "metadata_policy_hash": stable_hash(f"reference-l161:metadata:{role}"),
            "trust_anchor_hash": stable_hash(f"reference-l161:trust-anchor:{role}"),
            "status_endpoint_hash": stable_hash(f"reference-l161:status:{role}"),
            "role_authorized": True,
            "public_metadata_safe": True,
        }
        for role in L161_REQUIRED_FEDERATION_ROLES
    }
    federation_input["trust_mark_rows"] = {
        mark: {
            "trust_mark_hash": stable_hash(f"reference-l161:trust-mark:{mark}"),
            "issuer_chain_hash": stable_hash(f"reference-l161:issuer-chain:{mark}"),
            "subject_hash": stable_hash(f"reference-l161:subject:{mark}"),
            "scope_hash": stable_hash(f"reference-l161:scope:{mark}"),
            "expires_at_hash": stable_hash(f"reference-l161:expires:{mark}"),
            "status_hash": stable_hash(f"reference-l161:status:{mark}"),
            "accreditation_hash": stable_hash(f"reference-l161:accreditation:{mark}"),
            "issued_by_accredited_authority": True,
            "matches_policy": True,
            "not_expired": True,
            "not_revoked": True,
            "public_projection_safe": True,
        }
        for mark in L161_REQUIRED_TRUST_MARKS
    }
    federation_input["credential_claim_rows"] = {
        claim: {
            "claim_path_hash": stable_hash(f"reference-l161:claim-path:{claim}"),
            "credential_hash": stable_hash(f"reference-l161:credential:{claim}"),
            "proof_hash": stable_hash(f"reference-l161:proof:{claim}"),
            "subject_binding_hash": stable_hash(f"reference-l161:subject-binding:{claim}"),
            "required_in_vc": True,
            "required_in_trust_mark": True,
            "privacy_preserving": True,
        }
        for claim in L161_REQUIRED_CREDENTIAL_CLAIMS
    }
    federation_input["transparency_channel_rows"] = {
        channel: {
            "statement_hash": stable_hash(f"reference-l161:statement:{channel}"),
            "inclusion_proof_hash": stable_hash(f"reference-l161:inclusion:{channel}"),
            "log_root_hash": stable_hash(f"reference-l161:log-root:{channel}"),
            "verifier_command": "verify-universal-certification-trust-federation",
            "published": True,
            "inclusion_verified": True,
            "consistency_verified": True,
            "public_projection_safe": True,
        }
        for channel in L161_REQUIRED_TRANSPARENCY_CHANNELS
    }
    federation_input["negative_federation_rows"] = {
        case_id: {
            "fixture_hash": stable_hash(f"reference-l161:negative-fixture:{case_id}"),
            "verifier_command": "verify-universal-certification-trust-federation",
            "expected_reject": True,
            "observed_reject": True,
            "trust_mark_revoked": True,
            "relying_party_blocked": True,
            "settlement_held": True,
        }
        for case_id in L161_REQUIRED_NEGATIVE_FEDERATION_FAILURES
    }
    federation_input["private_strings"] = [
        "private reference l161 certifier evidence fixture"
    ]
    save("universal_certification_trust_federation_input", federation_input)
    federation = make_universal_certification_trust_federation(
        federation_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_certification_trust_federation", federation)
    return federation


def regenerate_l162_adoption_pack() -> dict[str, Any]:
    pack_input: dict[str, Any] = {
        name: load(name) for name in L162_REQUIRED_CORE_ARTIFACTS
    }
    pack_input["provider_family_rows"] = {
        family: {
            "native_route_hash": stable_hash(f"reference-l162:native-route:{family}"),
            "adapter_profile_hash": stable_hash(
                f"reference-l162:adapter-profile:{family}"
            ),
            "negotiation_profile_hash": stable_hash(
                f"reference-l162:negotiation:{family}"
            ),
            "invocation_enforcement_hash": stable_hash(
                f"reference-l162:invocation:{family}"
            ),
            "certification_federation_hash": stable_hash(
                f"reference-l162:certification:{family}"
            ),
            "source_footer_profile_hash": stable_hash(
                f"reference-l162:source-footer:{family}"
            ),
            "settlement_meter_hash": stable_hash(f"reference-l162:settlement:{family}"),
            "telemetry_mapping_hash": stable_hash(f"reference-l162:telemetry:{family}"),
            "status_endpoint_hash": stable_hash(f"reference-l162:status:{family}"),
            "public_docs_hash": stable_hash(f"reference-l162:docs:{family}"),
            "adapter_verified": True,
            "drift_sentinel_green": True,
            "negotiation_required": True,
            "invocation_enforced": True,
            "certification_federated": True,
            "source_footer_required": True,
            "settlement_metered": True,
            "telemetry_exportable": True,
            "revocation_checked": True,
            "public_discovery_available": True,
        }
        for family in L162_REQUIRED_PROVIDER_FAMILIES
    }
    pack_input["standard_export_rows"] = {
        export: {
            "export_hash": stable_hash(f"reference-l162:export:{export}"),
            "schema_hash": stable_hash(f"reference-l162:schema:{export}"),
            "publication_path_hash": stable_hash(
                f"reference-l162:publication:{export}"
            ),
            "compatibility_hash": stable_hash(f"reference-l162:compat:{export}"),
            "version_hash": stable_hash(f"reference-l162:version:{export}"),
            "implemented": True,
            "published": True,
            "verifier_available": True,
            "privacy_preserving": True,
        }
        for export in L162_REQUIRED_STANDARD_EXPORTS
    }
    pack_input["adoption_gate_rows"] = {
        gate: {
            "gate_hash": stable_hash(f"reference-l162:gate:{gate}"),
            "input_contract_hash": stable_hash(f"reference-l162:input:{gate}"),
            "output_contract_hash": stable_hash(f"reference-l162:output:{gate}"),
            "failure_policy_hash": stable_hash(f"reference-l162:failure:{gate}"),
            "owner_role_hash": stable_hash(f"reference-l162:owner:{gate}"),
            "blocks_on_failure": True,
            "settlement_hold_on_failure": True,
            "audit_visible": True,
            "public_status_safe": True,
        }
        for gate in L162_REQUIRED_ADOPTION_GATES
    }
    pack_input["negative_adoption_rows"] = {
        failure: {
            "fixture_hash": stable_hash(f"reference-l162:negative:{failure}"),
            "expected_reject": True,
            "observed_reject": True,
            "display_blocked": True,
            "settlement_held": True,
            "provider_route_revoked": True,
        }
        for failure in L162_REQUIRED_NEGATIVE_ADOPTION_FAILURES
    }
    pack_input["private_strings"] = [
        "private reference l162 provider adoption fixture"
    ]
    save("universal_foundation_provider_adoption_pack_input", pack_input)
    pack = make_universal_foundation_provider_adoption_pack(
        pack_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_foundation_provider_adoption_pack", pack)
    return pack


def regenerate_l163_industry_root() -> dict[str, Any]:
    root_input: dict[str, Any] = {
        name: load(name) for name in L163_REQUIRED_CORE_ARTIFACTS
    }
    root_input["publication_endpoint_rows"] = {
        endpoint: {
            "endpoint_hash": stable_hash(f"reference-l163:endpoint:{endpoint}"),
            "schema_hash": stable_hash(f"reference-l163:schema:{endpoint}"),
            "status_hash": stable_hash(f"reference-l163:status:{endpoint}"),
            "verifier_command_hash": stable_hash(
                f"reference-l163:verifier:{endpoint}"
            ),
            "version_hash": stable_hash(f"reference-l163:version:{endpoint}"),
            "published": True,
            "verifier_available": True,
            "privacy_preserving": True,
            "revocation_status_available": True,
        }
        for endpoint in L163_REQUIRED_PUBLICATION_ENDPOINTS
    }
    root_input["role_obligation_rows"] = {
        role: {
            "role_hash": stable_hash(f"reference-l163:role:{role}"),
            "adoption_policy_hash": stable_hash(f"reference-l163:policy:{role}"),
            "responsibility_hash": stable_hash(
                f"reference-l163:responsibility:{role}"
            ),
            "verifier_hash": stable_hash(f"reference-l163:verifier:{role}"),
            "status_endpoint_hash": stable_hash(f"reference-l163:status:{role}"),
            "required": True,
            "blocks_on_failure": True,
            "settlement_hold_on_failure": True,
            "audit_visible": True,
            "public_discovery_safe": True,
        }
        for role in L163_REQUIRED_ADOPTION_ROLES
    }
    root_input["negative_root_rows"] = {
        failure: {
            "fixture_hash": stable_hash(f"reference-l163:negative:{failure}"),
            "expected_reject": True,
            "observed_reject": True,
            "root_reliance_blocked": True,
            "settlement_held": True,
            "public_status_marked_failed": True,
        }
        for failure in L163_REQUIRED_NEGATIVE_ROOT_FAILURES
    }
    root_input["private_strings"] = [
        "private reference l163 industry adoption fixture"
    ]
    save("universal_industry_adoption_root_input", root_input)
    root = make_universal_industry_adoption_root(
        root_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_industry_adoption_root", root)
    return root


def regenerate_l164_reference_distribution() -> dict[str, Any]:
    distribution_input: dict[str, Any] = {
        name: load(name)
        for name in (
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
        )
    }
    industry_root_hash = distribution_input["universal_industry_adoption_root"][
        "universal_industry_adoption_root_hash"
    ]
    distribution_input["distribution_component_rows"] = {
        component: {
            "component_hash": stable_hash(f"reference-l164:component:{component}"),
            "package_hash": stable_hash(f"reference-l164:package:{component}"),
            "version_hash": stable_hash(f"reference-l164:version:{component}"),
            "sbom_hash": stable_hash(f"reference-l164:sbom:{component}"),
            "slsa_provenance_hash": stable_hash(f"reference-l164:slsa:{component}"),
            "build_recipe_hash": stable_hash(f"reference-l164:build:{component}"),
            "signature_hash": stable_hash(f"reference-l164:signature:{component}"),
            "transparency_log_entry_hash": stable_hash(
                f"reference-l164:transparency:{component}"
            ),
            "verifier_command_hash": stable_hash(
                f"reference-l164:verifier:{component}"
            ),
            "public_path_hash": stable_hash(f"reference-l164:path:{component}"),
            "reproducible_build": True,
            "signed": True,
            "sbom_available": True,
            "slsa_provenance_available": True,
            "transparency_logged": True,
            "verifier_available": True,
            "fail_closed_default": True,
            "private_payloads_excluded": True,
        }
        for component in L164_REQUIRED_DISTRIBUTION_COMPONENTS
    }
    distribution_input["install_target_rows"] = {
        target: {
            "target_hash": stable_hash(f"reference-l164:target:{target}"),
            "adapter_hash": stable_hash(f"reference-l164:adapter:{target}"),
            "fixture_hash": stable_hash(f"reference-l164:fixture:{target}"),
            "ci_result_hash": stable_hash(f"reference-l164:ci:{target}"),
            "verifier_command_hash": stable_hash(f"reference-l164:verifier:{target}"),
            "negative_fixture_hash": stable_hash(f"reference-l164:negative:{target}"),
            "root_binding_hash": industry_root_hash,
            "adapter_available": True,
            "fixture_available": True,
            "ci_passed": True,
            "offline_verifier_available": True,
            "fail_closed_default": True,
            "source_footer_preserved": True,
            "telemetry_mapping_bound": True,
            "settlement_meter_bound": True,
            "root_requirement_enforced": True,
        }
        for target in L164_REQUIRED_INSTALL_TARGETS
    }
    distribution_input["negative_distribution_rows"] = {
        failure: {
            "fixture_hash": stable_hash(f"reference-l164:negative:{failure}"),
            "expected_reject": True,
            "observed_reject": True,
            "installation_blocked": True,
            "root_reliance_blocked": True,
            "settlement_held": True,
            "public_status_marked_failed": True,
        }
        for failure in L164_REQUIRED_NEGATIVE_DISTRIBUTION_FAILURES
    }
    distribution_input["private_strings"] = [
        "private reference l164 distribution fixture"
    ]
    save("universal_reference_implementation_distribution_input", distribution_input)
    distribution = make_universal_reference_implementation_distribution(
        distribution_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_reference_implementation_distribution", distribution)
    return distribution


def regenerate_l165_live_attribution_proof() -> dict[str, Any]:
    proof_input: dict[str, Any] = {
        name: load(name)
        for name in (
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
        )
    }
    proof_input["hidden_payable_source_count"] = 0
    proof_input["attribution_suppression_count"] = 0
    proof_input["live_source_rows"] = {
        "source:retrieval": {
            "source_hash": stable_hash("reference-l165:source:retrieval"),
            "footer_row_hash": stable_hash("reference-l165:footer:retrieval"),
            "claim_provenance_hash": stable_hash("reference-l165:claim:retrieval"),
            "influence_hash": stable_hash("reference-l165:influence:retrieval"),
            "source_identity_hash": stable_hash("reference-l165:identity:retrieval"),
            "confidence_hash": stable_hash("reference-l165:confidence:retrieval"),
            "settlement_hash": stable_hash("reference-l165:settlement:retrieval"),
            "knowledge_source_mode": "current_turn_retrieval",
            "visible_in_footer": True,
            "identity_verified": True,
            "claim_support_verified": True,
            "current_turn_or_memory_path_verified": True,
            "causal_utility_verified": True,
            "factual_confidence_accepted": True,
            "license_or_escrow_resolved": True,
            "settlement_weight_bound": True,
            "private_payloads_excluded": True,
            "factual_confidence": 0.93,
            "utility_score": 0.74,
            "attribution_weight": 0.61,
            "settlement_weight": 0.61,
        },
        "source:parametric": {
            "source_hash": stable_hash("reference-l165:source:parametric"),
            "footer_row_hash": stable_hash("reference-l165:footer:parametric"),
            "claim_provenance_hash": stable_hash("reference-l165:claim:parametric"),
            "influence_hash": stable_hash("reference-l165:influence:parametric"),
            "source_identity_hash": stable_hash("reference-l165:identity:parametric"),
            "confidence_hash": stable_hash("reference-l165:confidence:parametric"),
            "settlement_hash": stable_hash("reference-l165:settlement:parametric"),
            "knowledge_source_mode": "parametric_memory",
            "visible_in_footer": True,
            "identity_verified": True,
            "claim_support_verified": True,
            "current_turn_or_memory_path_verified": True,
            "causal_utility_verified": True,
            "factual_confidence_accepted": True,
            "license_or_escrow_resolved": True,
            "settlement_weight_bound": True,
            "private_payloads_excluded": True,
            "factual_confidence": 0.84,
            "utility_score": 0.49,
            "attribution_weight": 0.22,
            "settlement_weight": 0.22,
        },
    }
    proof_input["knowledge_source_mode_rows"] = {
        mode: {
            "classifier_hash": stable_hash(f"reference-l165:classifier:{mode}"),
            "calibration_hash": stable_hash(f"reference-l165:calibration:{mode}"),
            "evidence_path_hash": stable_hash(f"reference-l165:path:{mode}"),
            "negative_control_hash": stable_hash(f"reference-l165:negative:{mode}"),
            "mode_supported": True,
            "classifier_calibrated": True,
            "negative_control_passed": True,
            "footer_policy_enforced": True,
            "settlement_policy_bound": True,
        }
        for mode in L165_REQUIRED_KNOWLEDGE_SOURCE_MODES
    }
    proof_input["footer_surface_rows"] = {
        surface: {
            "surface_hash": stable_hash(f"reference-l165:surface:{surface}"),
            "rendered_footer_hash": stable_hash(
                f"reference-l165:rendered:{surface}"
            ),
            "live_proof_binding_hash": stable_hash(
                f"reference-l165:binding:{surface}"
            ),
            "copy_export_hash": stable_hash(f"reference-l165:copy:{surface}"),
            "source_footer_visible": True,
            "live_proof_hash_embedded": True,
            "claim_markers_preserved": True,
            "source_order_preserved": True,
            "verification_link_available": True,
            "copy_export_preserves_footer": True,
        }
        for surface in L165_REQUIRED_FOOTER_SURFACES
    }
    proof_input["negative_live_attribution_rows"] = {
        failure: {
            "fixture_hash": stable_hash(f"reference-l165:negative:{failure}"),
            "expected_reject": True,
            "observed_reject": True,
            "response_blocked": True,
            "footer_reliance_blocked": True,
            "settlement_held": True,
            "public_status_marked_failed": True,
        }
        for failure in L165_REQUIRED_NEGATIVE_LIVE_FAILURES
    }
    proof_input["private_strings"] = [
        "private reference l165 live attribution fixture"
    ]
    save("universal_live_attribution_proof_input", proof_input)
    proof = make_universal_live_attribution_proof(
        proof_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_live_attribution_proof", proof)
    return proof


def regenerate_l166_model_release_passport() -> dict[str, Any]:
    passport_input = {
        name: load(name)
        for name in (
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
        )
    }
    live_hash = passport_input["universal_live_attribution_proof"][
        "universal_live_attribution_proof_hash"
    ]
    passport_input["model_release_rows"] = {
        "model:rdllm-reference:2026-06": {
            "provider_family": "openai_compatible_reference",
            "model_id": "rdllm-reference-model",
            "model_version": "2026-06",
            "release_status": "ready",
            "provider_subject_hash": stable_hash("reference-l166:provider"),
            "model_identity_hash": stable_hash("reference-l166:model"),
            "model_artifact_or_attestation_hash": stable_hash(
                "reference-l166:model-artifact"
            ),
            "model_signing_hash": stable_hash("reference-l166:signing"),
            "training_summary_hash": stable_hash("reference-l166:training"),
            "copyright_policy_hash": stable_hash("reference-l166:copyright"),
            "tdm_reservation_policy_hash": stable_hash("reference-l166:tdm"),
            "post_training_lineage_hash": stable_hash("reference-l166:post-training"),
            "live_attribution_proof_hash": live_hash,
            "settlement_contract_hash": stable_hash("reference-l166:settlement"),
            "revocation_status_hash": stable_hash("reference-l166:revocation"),
            "downstream_documentation_hash": stable_hash(
                "reference-l166:downstream-docs"
            ),
            "model_id_bound": True,
            "provider_subject_verified": True,
            "model_version_bound": True,
            "signed_model_or_closed_weight_attested": True,
            "training_content_summary_published": True,
            "copyright_policy_bound": True,
            "tdm_opt_out_policy_enforced": True,
            "post_training_lineage_bound": True,
            "live_attribution_required_for_all_outputs": True,
            "downstream_docs_available": True,
            "settlement_policy_bound": True,
            "revocation_policy_bound": True,
            "private_payloads_excluded": True,
        }
    }
    passport_input["provider_route_rows"] = {
        route: {
            "route_contract_hash": stable_hash(f"reference-l166:contract:{route}"),
            "adapter_hash": stable_hash(f"reference-l166:adapter:{route}"),
            "telemetry_hash": stable_hash(f"reference-l166:telemetry:{route}"),
            "source_footer_hash": stable_hash(f"reference-l166:footer:{route}"),
            "live_proof_hash": stable_hash(f"reference-l166:live:{route}"),
            "settlement_meter_hash": stable_hash(f"reference-l166:meter:{route}"),
            "refusal_path_hash": stable_hash(f"reference-l166:refusal:{route}"),
            "route_supported": True,
            "adapter_verified": True,
            "live_attribution_enforced": True,
            "streaming_and_batch_covered": True,
            "copy_export_covered": True,
            "fallback_routes_blocked": True,
            "settlement_meter_bound": True,
            "private_payloads_excluded": True,
        }
        for route in L166_REQUIRED_PROVIDER_RELEASE_ROUTES
    }
    passport_input["release_lifecycle_rows"] = {
        domain: {
            "control_hash": stable_hash(f"reference-l166:control:{domain}"),
            "evidence_hash": stable_hash(f"reference-l166:evidence:{domain}"),
            "verifier_hash": stable_hash(f"reference-l166:verifier:{domain}"),
            "policy_hash": stable_hash(f"reference-l166:policy:{domain}"),
            "control_supported": True,
            "evidence_bound": True,
            "verifier_available": True,
            "release_gate_bound": True,
            "failure_holds_release": True,
            "private_payloads_excluded": True,
        }
        for domain in L166_REQUIRED_RELEASE_LIFECYCLE_DOMAINS
    }
    passport_input["compliance_mapping_rows"] = {
        mapping: {
            "mapping_hash": stable_hash(f"reference-l166:mapping:{mapping}"),
            "evidence_hash": stable_hash(
                f"reference-l166:mapping-evidence:{mapping}"
            ),
            "control_owner_hash": stable_hash(f"reference-l166:owner:{mapping}"),
            "export_hash": stable_hash(f"reference-l166:export:{mapping}"),
            "mapped": True,
            "machine_readable": True,
            "public_or_auditor_accessible": True,
            "release_gate_bound": True,
            "drift_review_bound": True,
        }
        for mapping in L166_REQUIRED_COMPLIANCE_MAPPINGS
    }
    passport_input["negative_model_release_rows"] = {
        failure: {
            "fixture_hash": stable_hash(f"reference-l166:negative:{failure}"),
            "expected_reject": True,
            "observed_reject": True,
            "model_release_blocked": True,
            "invocation_blocked": True,
            "footer_reliance_blocked": True,
            "settlement_held": True,
            "public_status_marked_failed": True,
        }
        for failure in L166_REQUIRED_NEGATIVE_RELEASE_FAILURES
    }
    passport_input["private_strings"] = [
        "private reference l166 model release fixture"
    ]
    save("universal_foundation_model_release_passport_input", passport_input)
    passport = make_universal_foundation_model_release_passport(
        passport_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_foundation_model_release_passport", passport)
    return passport


def regenerate_l167_composite_contract() -> dict[str, Any]:
    contract_input = {
        name: load(name)
        for name in (
            "certification_report",
            "certification_attestation",
            "provider_attribution_card",
            "integration_profile",
            "discovery_manifest",
            "assurance_bundle",
            "proof_dependency_graph_post_release",
            "trust_registry",
            "universal_foundation_model_release_passport",
            "universal_live_attribution_proof",
            "universal_reference_implementation_distribution",
            "universal_industry_adoption_root",
            "universal_foundation_provider_adoption_pack",
            "universal_certification_trust_federation",
            "universal_composite_rdllm_profile",
            "universal_runtime_conformance_receipt",
            "universal_claim_provenance_envelope",
            "universal_provider_wire_protocol",
            "universal_grounded_reliance_contract",
            "universal_reliance_correction_ledger",
            "revenue_allocation_report",
            "finance_ledger_attestation",
        )
    }
    contract_input["contract_role_rows"] = {
        role: {
            "role_hash": stable_hash(f"reference-l167:role:{role}"),
            "obligation_hash": stable_hash(f"reference-l167:obligation:{role}"),
            "verifier_hash": stable_hash(f"reference-l167:verifier:{role}"),
            "settlement_hold_hash": stable_hash(f"reference-l167:hold:{role}"),
            "public_endpoint_hash": stable_hash(f"reference-l167:endpoint:{role}"),
            "role_supported": True,
            "obligations_bound": True,
            "verifier_available": True,
            "fail_closed": True,
            "settlement_hold_bound": True,
            "private_payloads_excluded": True,
        }
        for role in L167_REQUIRED_CONTRACT_ROLES
    }
    contract_input["canonical_api_surface_rows"] = {
        surface: {
            "endpoint_hash": stable_hash(f"reference-l167:endpoint:{surface}"),
            "schema_hash": stable_hash(f"reference-l167:schema:{surface}"),
            "verifier_hash": stable_hash(f"reference-l167:verifier:{surface}"),
            "telemetry_hash": stable_hash(f"reference-l167:telemetry:{surface}"),
            "policy_hash": stable_hash(f"reference-l167:policy:{surface}"),
            "surface_available": True,
            "machine_readable": True,
            "versioned": True,
            "fail_closed": True,
            "settlement_bound": True,
            "private_payloads_excluded": True,
        }
        for surface in L167_REQUIRED_CANONICAL_API_SURFACES
    }
    contract_input["decision_gate_rows"] = {
        gate: {
            "policy_hash": stable_hash(f"reference-l167:gate-policy:{gate}"),
            "precondition_hash": stable_hash(f"reference-l167:gate-pre:{gate}"),
            "enforcement_hash": stable_hash(f"reference-l167:gate-enforce:{gate}"),
            "negative_fixture_hash": stable_hash(f"reference-l167:gate-neg:{gate}"),
            "precondition_checked": True,
            "enforcement_available": True,
            "violation_blocks_release": True,
            "settlement_held_on_failure": True,
            "public_status_available": True,
        }
        for gate in L167_REQUIRED_DECISION_GATES
    }
    contract_input["standard_binding_rows"] = {
        standard: {
            "mapping_hash": stable_hash(f"reference-l167:map:{standard}"),
            "schema_hash": stable_hash(f"reference-l167:schema:{standard}"),
            "test_vector_hash": stable_hash(f"reference-l167:vector:{standard}"),
            "export_hash": stable_hash(f"reference-l167:export:{standard}"),
            "mapped": True,
            "test_vector_available": True,
            "public_or_auditor_accessible": True,
            "contract_bound": True,
            "drift_review_bound": True,
        }
        for standard in L167_REQUIRED_STANDARD_BINDINGS
    }
    contract_input["negative_composite_rows"] = {
        failure: {
            "fixture_hash": stable_hash(f"reference-l167:negative:{failure}"),
            "expected_reject": True,
            "observed_reject": True,
            "rdllm_claim_blocked": True,
            "invocation_blocked": True,
            "response_release_blocked": True,
            "settlement_held": True,
            "public_status_marked_failed": True,
        }
        for failure in L167_REQUIRED_NEGATIVE_COMPOSITE_FAILURES
    }
    contract_input["private_strings"] = [
        "private reference l167 composite contract fixture"
    ]
    save("universal_composite_rdllm_contract_input", contract_input)
    contract = make_universal_composite_rdllm_contract(
        contract_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_composite_rdllm_contract", contract)
    return contract


def regenerate_l168_provider_binding_matrix() -> dict[str, Any]:
    composite_contract = load("universal_composite_rdllm_contract")

    def domain_row(provider: str, domain: str) -> dict[str, Any]:
        return {
            "domain_hash": stable_hash(f"reference-l168:domain:{provider}:{domain}"),
            "fixture_hash": stable_hash(f"reference-l168:fixture:{provider}:{domain}"),
            "verifier_hash": stable_hash(f"reference-l168:verifier:{provider}:{domain}"),
            "drift_hash": stable_hash(f"reference-l168:drift:{provider}:{domain}"),
            "mapped": True,
            "tested": True,
            "l167_bound": True,
            "fail_closed": True,
        }

    def provider_row(provider: str) -> dict[str, Any]:
        return {
            "provider_binding_hash": stable_hash(f"reference-l168:provider:{provider}"),
            "native_api_contract_hash": stable_hash(
                f"reference-l168:native-api:{provider}"
            ),
            "adapter_hash": stable_hash(f"reference-l168:adapter:{provider}"),
            "conformance_fixture_hash": stable_hash(
                f"reference-l168:conformance:{provider}"
            ),
            "drift_canary_hash": stable_hash(f"reference-l168:canary:{provider}"),
            "telemetry_mapping_hash": stable_hash(
                f"reference-l168:telemetry:{provider}"
            ),
            "settlement_meter_hash": stable_hash(
                f"reference-l168:settlement:{provider}"
            ),
            "revocation_status_hash": stable_hash(
                f"reference-l168:revocation:{provider}"
            ),
            "public_verifier_hash": stable_hash(
                f"reference-l168:public-verifier:{provider}"
            ),
            "capabilities": {
                capability: True for capability in L168_REQUIRED_NATIVE_CAPABILITIES
            },
            "domain_bindings": {
                domain: domain_row(provider, domain)
                for domain in L168_REQUIRED_BINDING_DOMAINS
            },
            "provider_family_supported": True,
            "native_api_bound_to_l167": True,
            "all_required_capabilities_supported": True,
            "domain_bindings_complete": True,
            "fail_closed": True,
            "private_payloads_excluded": True,
        }

    matrix_input: dict[str, Any] = {
        "universal_composite_rdllm_contract": composite_contract,
        "provider_binding_rows": {
            provider: provider_row(provider)
            for provider in L168_REQUIRED_PROVIDER_FAMILIES
        },
        "negative_provider_binding_rows": {
            failure: {
                "fixture_hash": stable_hash(f"reference-l168:negative:{failure}"),
                "expected_reject": True,
                "observed_reject": True,
                "provider_claim_blocked": True,
                "invocation_blocked": True,
                "response_release_blocked": True,
                "source_footer_reliance_blocked": True,
                "settlement_held": True,
                "public_status_marked_failed": True,
            }
            for failure in L168_REQUIRED_NEGATIVE_PROVIDER_FAILURES
        },
        "private_strings": ["private reference l168 provider binding fixture"],
    }
    save("universal_foundation_provider_binding_matrix_input", matrix_input)
    matrix = make_universal_foundation_provider_binding_matrix(
        matrix_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_foundation_provider_binding_matrix", matrix)
    return matrix


def regenerate_l169_provider_conformance_runner_receipt() -> dict[str, Any]:
    provider_binding_matrix = load("universal_foundation_provider_binding_matrix")

    def fixture_suite_row(suite: str) -> dict[str, Any]:
        return {
            "suite_hash": stable_hash(f"reference-l169:suite:{suite}"),
            "fixture_hash": stable_hash(f"reference-l169:fixture:{suite}"),
            "transcript_hash": stable_hash(f"reference-l169:transcript:{suite}"),
            "expected_result_hash": stable_hash(f"reference-l169:expected:{suite}"),
            "observed_result_hash": stable_hash(f"reference-l169:observed:{suite}"),
            "verifier_hash": stable_hash(f"reference-l169:verifier:{suite}"),
            "executed": True,
            "passed": True,
            "l168_bound": True,
            "public_or_auditor_accessible": True,
            "fail_closed_on_error": True,
        }

    def runner_stage_row(stage: str) -> dict[str, Any]:
        return {
            "stage_hash": stable_hash(f"reference-l169:stage:{stage}"),
            "evidence_hash": stable_hash(f"reference-l169:evidence:{stage}"),
            "verifier_hash": stable_hash(f"reference-l169:stage-verifier:{stage}"),
            "executed": True,
            "passed": True,
            "public_or_auditor_accessible": True,
            "fail_closed_on_error": True,
        }

    def provider_run_row(provider: str) -> dict[str, Any]:
        return {
            "run_hash": stable_hash(f"reference-l169:run:{provider}"),
            "provider_binding_hash": stable_hash(f"reference-l169:binding:{provider}"),
            "runner_image_digest": stable_hash(
                f"reference-l169:runner-image:{provider}"
            ),
            "fixture_pack_hash": stable_hash(
                f"reference-l169:fixture-pack:{provider}"
            ),
            "native_transcript_hash": stable_hash(
                f"reference-l169:native-transcript:{provider}"
            ),
            "result_log_hash": stable_hash(f"reference-l169:result-log:{provider}"),
            "public_result_hash": stable_hash(
                f"reference-l169:public-result:{provider}"
            ),
            "attestation_hash": stable_hash(f"reference-l169:attestation:{provider}"),
            "verifier_hash": stable_hash(
                f"reference-l169:provider-verifier:{provider}"
            ),
            "fixture_suite_results": {
                suite: "passed" for suite in L169_REQUIRED_FIXTURE_SUITES
            },
            "provider_identity_verified": True,
            "binding_matrix_matched": True,
            "runner_image_verified": True,
            "official_fixtures_executed": True,
            "all_fixture_suites_passed": True,
            "negative_canaries_rejected": True,
            "fresh_within_sla": True,
            "public_result_published": True,
            "fail_closed": True,
            "private_payloads_excluded": True,
        }

    receipt_input: dict[str, Any] = {
        "universal_foundation_provider_binding_matrix": provider_binding_matrix,
        "fixture_suite_rows": {
            suite: fixture_suite_row(suite) for suite in L169_REQUIRED_FIXTURE_SUITES
        },
        "runner_stage_rows": {
            stage: runner_stage_row(stage) for stage in L169_REQUIRED_RUNNER_STAGES
        },
        "provider_run_rows": {
            provider: provider_run_row(provider)
            for provider in L169_REQUIRED_PROVIDER_FAMILIES
        },
        "negative_runner_rows": {
            failure: {
                "fixture_hash": stable_hash(f"reference-l169:negative:{failure}"),
                "expected_reject": True,
                "observed_reject": True,
                "provider_claim_blocked": True,
                "invocation_blocked": True,
                "response_release_blocked": True,
                "source_footer_reliance_blocked": True,
                "settlement_held": True,
                "public_status_marked_failed": True,
            }
            for failure in L169_REQUIRED_NEGATIVE_RUNNER_FAILURES
        },
        "private_strings": ["private reference l169 provider runner fixture"],
    }
    save("universal_provider_conformance_runner_receipt_input", receipt_input)
    receipt = make_universal_provider_conformance_runner_receipt(
        receipt_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_provider_conformance_runner_receipt", receipt)
    return receipt


def regenerate_l170_production_invocation_admission() -> dict[str, Any]:
    provider_conformance_runner_receipt = load(
        "universal_provider_conformance_runner_receipt"
    )

    def gate_row(gate: str) -> dict[str, Any]:
        return {
            "gate_hash": stable_hash(f"reference-l170:gate:{gate}"),
            "policy_hash": stable_hash(f"reference-l170:policy:{gate}"),
            "evidence_hash": stable_hash(f"reference-l170:evidence:{gate}"),
            "verifier_hash": stable_hash(f"reference-l170:gate-verifier:{gate}"),
            "configured": True,
            "enforced": True,
            "l169_bound": True,
            "telemetry_bound": True,
            "fail_closed": True,
            "public_or_auditor_accessible": True,
        }

    def provider_row(provider: str) -> dict[str, Any]:
        return {
            "admission_token_hash": stable_hash(f"reference-l170:token:{provider}"),
            "provider_route_hash": stable_hash(f"reference-l170:route:{provider}"),
            "model_alias_hash": stable_hash(
                f"reference-l170:model-alias:{provider}"
            ),
            "tenant_scope_hash": stable_hash(f"reference-l170:tenant:{provider}"),
            "l169_receipt_hash": stable_hash(f"reference-l170:l169:{provider}"),
            "l168_matrix_hash": stable_hash(f"reference-l170:l168:{provider}"),
            "negotiated_contract_hash": stable_hash(
                f"reference-l170:negotiated:{provider}"
            ),
            "invocation_guard_hash": stable_hash(f"reference-l170:guard:{provider}"),
            "drift_sentinel_hash": stable_hash(f"reference-l170:drift:{provider}"),
            "telemetry_span_hash": stable_hash(f"reference-l170:span:{provider}"),
            "source_footer_gate_hash": stable_hash(
                f"reference-l170:footer:{provider}"
            ),
            "settlement_meter_hash": stable_hash(
                f"reference-l170:settlement:{provider}"
            ),
            "revocation_snapshot_hash": stable_hash(
                f"reference-l170:revocation:{provider}"
            ),
            "admission_decision_hash": stable_hash(
                f"reference-l170:decision:{provider}"
            ),
            "verifier_hash": stable_hash(f"reference-l170:verifier:{provider}"),
            "invocation_surfaces": {
                surface: "admitted" for surface in L170_REQUIRED_INVOCATION_SURFACES
            },
            "provider_identity_matched": True,
            "route_in_l168_matrix": True,
            "l169_receipt_bound": True,
            "l169_receipt_fresh": True,
            "drift_sentinel_green": True,
            "negotiated_contract_bound": True,
            "invocation_guard_bound": True,
            "telemetry_span_opened": True,
            "source_footer_gate_bound": True,
            "settlement_hold_until_footer": True,
            "revocation_checked": True,
            "all_invocation_surfaces_admitted": True,
            "fail_closed": True,
            "private_payloads_excluded": True,
        }

    admission_input: dict[str, Any] = {
        "universal_provider_conformance_runner_receipt": (
            provider_conformance_runner_receipt
        ),
        "provider_admission_rows": {
            provider: provider_row(provider)
            for provider in L170_REQUIRED_PROVIDER_FAMILIES
        },
        "admission_gate_rows": {
            gate: gate_row(gate) for gate in L170_REQUIRED_ADMISSION_GATES
        },
        "negative_admission_rows": {
            failure: {
                "fixture_hash": stable_hash(f"reference-l170:negative:{failure}"),
                "expected_reject": True,
                "observed_reject": True,
                "admission_token_denied": True,
                "provider_invocation_blocked": True,
                "response_release_blocked": True,
                "source_footer_reliance_blocked": True,
                "tool_mcp_execution_blocked": True,
                "settlement_held": True,
                "public_status_marked_failed": True,
            }
            for failure in L170_REQUIRED_NEGATIVE_ADMISSION_FAILURES
        },
        "private_strings": ["private reference l170 production admission fixture"],
    }
    save("universal_production_invocation_admission_input", admission_input)
    admission = make_universal_production_invocation_admission(
        admission_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_production_invocation_admission", admission)
    return admission


def regenerate_l171_source_grounded_response_receipt() -> dict[str, Any]:
    production_admission = load("universal_production_invocation_admission")
    live_attribution_proof = load("universal_live_attribution_proof")

    def source_row(category: str) -> dict[str, Any]:
        return {
            "source_row_hash": stable_hash(f"reference-l171:source-row:{category}"),
            "source_identity_hash": stable_hash(f"reference-l171:source-id:{category}"),
            "locator_hash": stable_hash(f"reference-l171:locator:{category}"),
            "license_hash": stable_hash(f"reference-l171:license:{category}"),
            "creator_hash": stable_hash(f"reference-l171:creator:{category}"),
            "evidence_hash": stable_hash(f"reference-l171:evidence:{category}"),
            "confidence_hash": stable_hash(f"reference-l171:confidence:{category}"),
            "footer_label_hash": stable_hash(
                f"reference-l171:footer-label:{category}"
            ),
            "settlement_share_hash": stable_hash(
                f"reference-l171:settlement:{category}"
            ),
            "verifier_hash": stable_hash(
                f"reference-l171:source-verifier:{category}"
            ),
            "source_available": True,
            "claim_support_verified": True,
            "footer_visible": True,
            "rights_allow_display": True,
            "confidence_calibrated": True,
            "settlement_bound": True,
            "no_private_payloads": True,
        }

    def claim_row(claim_type: str) -> dict[str, Any]:
        return {
            "claim_row_hash": stable_hash(f"reference-l171:claim-row:{claim_type}"),
            "claim_hash": stable_hash(f"reference-l171:claim:{claim_type}"),
            "claim_type": claim_type,
            "source_row_hash": stable_hash(
                f"reference-l171:claim-source:{claim_type}"
            ),
            "evidence_span_hash": stable_hash(f"reference-l171:span:{claim_type}"),
            "citation_locator_hash": stable_hash(
                f"reference-l171:citation:{claim_type}"
            ),
            "confidence_hash": stable_hash(
                f"reference-l171:claim-confidence:{claim_type}"
            ),
            "verifier_hash": stable_hash(f"reference-l171:claim-verifier:{claim_type}"),
            "supported_by_source": True,
            "source_visible_in_footer": True,
            "evidence_span_bound": True,
            "citation_metadata_verified": True,
            "unsupported_claim_blocked": True,
            "no_private_payloads": True,
        }

    def surface_row(surface: str) -> dict[str, Any]:
        return {
            "response_surface_hash": stable_hash(f"reference-l171:surface:{surface}"),
            "rendered_footer_hash": stable_hash(f"reference-l171:footer:{surface}"),
            "admission_token_hash": stable_hash(
                f"reference-l171:admission:{surface}"
            ),
            "live_proof_hash": stable_hash(f"reference-l171:live-proof:{surface}"),
            "claim_root_hash": stable_hash(f"reference-l171:claim-root:{surface}"),
            "copy_export_hash": stable_hash(f"reference-l171:copy:{surface}"),
            "verifier_hash": stable_hash(
                f"reference-l171:surface-verifier:{surface}"
            ),
            "surface_rendered": True,
            "source_footer_visible": True,
            "l170_admission_bound": True,
            "live_proof_bound": True,
            "claim_rows_bound": True,
            "copy_export_preserves_sources": True,
            "fail_closed": True,
            "public_or_auditor_accessible": True,
        }

    def settlement_row(scope: str) -> dict[str, Any]:
        return {
            "settlement_row_hash": stable_hash(
                f"reference-l171:settlement-row:{scope}"
            ),
            "creator_hash": stable_hash(f"reference-l171:settlement-creator:{scope}"),
            "source_row_hash": stable_hash(f"reference-l171:settlement-source:{scope}"),
            "license_hash": stable_hash(f"reference-l171:settlement-license:{scope}"),
            "usage_meter_hash": stable_hash(f"reference-l171:meter:{scope}"),
            "allocation_hash": stable_hash(f"reference-l171:allocation:{scope}"),
            "remittance_hold_hash": stable_hash(f"reference-l171:hold:{scope}"),
            "verifier_hash": stable_hash(
                f"reference-l171:settlement-verifier:{scope}"
            ),
            "source_visible_in_footer": True,
            "claim_support_verified": True,
            "l170_admission_bound": True,
            "footer_release_bound": True,
            "settlement_held_until_footer": True,
            "no_hidden_payable_source": True,
            "no_private_payloads": True,
        }

    receipt_input: dict[str, Any] = {
        "universal_production_invocation_admission": production_admission,
        "universal_live_attribution_proof": live_attribution_proof,
        "source_category_rows": {
            category: source_row(category)
            for category in L171_REQUIRED_SOURCE_CATEGORIES
        },
        "claim_grounding_rows": {
            claim_type: claim_row(claim_type)
            for claim_type in L171_REQUIRED_CLAIM_TYPES
        },
        "response_surface_rows": {
            surface: surface_row(surface)
            for surface in L171_REQUIRED_RESPONSE_SURFACES
        },
        "settlement_release_rows": {
            scope: settlement_row(scope)
            for scope in L171_REQUIRED_SETTLEMENT_SCOPES
        },
        "negative_response_rows": {
            failure: {
                "fixture_hash": stable_hash(f"reference-l171:negative:{failure}"),
                "expected_reject": True,
                "observed_reject": True,
                "response_release_blocked": True,
                "footer_reliance_blocked": True,
                "source_reliance_blocked": True,
                "citation_reliance_blocked": True,
                "copy_export_blocked": True,
                "settlement_held": True,
                "public_status_marked_failed": True,
            }
            for failure in L171_REQUIRED_NEGATIVE_RESPONSE_FAILURES
        },
        "private_strings": ["private reference l171 source grounded response fixture"],
    }
    save("universal_source_grounded_response_receipt_input", receipt_input)
    receipt = make_universal_source_grounded_response_receipt(
        receipt_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_source_grounded_response_receipt", receipt)
    return receipt


def regenerate_l172_distribution_reliance_passport() -> dict[str, Any]:
    source_receipt = load("universal_source_grounded_response_receipt")
    content_credential = load("universal_content_credential")

    def surface_row(surface: str) -> dict[str, Any]:
        return {
            "distribution_surface_hash": stable_hash(
                f"reference-l172:surface:{surface}"
            ),
            "artifact_body_hash": stable_hash(f"reference-l172:body:{surface}"),
            "l171_receipt_hash": stable_hash(f"reference-l172:l171:{surface}"),
            "visible_footer_hash": stable_hash(f"reference-l172:footer:{surface}"),
            "source_locator_manifest_hash": stable_hash(
                f"reference-l172:locator:{surface}"
            ),
            "status_resolver_hash": stable_hash(
                f"reference-l172:resolver:{surface}"
            ),
            "content_credential_hash": stable_hash(
                f"reference-l172:credential:{surface}"
            ),
            "reuse_meter_hash": stable_hash(f"reference-l172:reuse:{surface}"),
            "settlement_carry_forward_hash": stable_hash(
                f"reference-l172:settlement:{surface}"
            ),
            "verifier_hash": stable_hash(
                f"reference-l172:surface-verifier:{surface}"
            ),
            "surface_exported": True,
            "attribution_visible_or_embedded": True,
            "l171_receipt_bound": True,
            "source_locators_preserved": True,
            "status_resolver_reachable": True,
            "revocation_checked": True,
            "reuse_metered": True,
            "settlement_obligation_preserved": True,
            "fail_closed_if_stripped": True,
            "no_private_payloads": True,
        }

    def binding_row(binding: str) -> dict[str, Any]:
        return {
            "binding_hash": stable_hash(f"reference-l172:binding:{binding}"),
            "subject_hash": stable_hash(f"reference-l172:subject:{binding}"),
            "l171_receipt_hash": stable_hash(
                f"reference-l172:binding-l171:{binding}"
            ),
            "binding_target_hash": stable_hash(f"reference-l172:target:{binding}"),
            "proof_graph_hash": stable_hash(f"reference-l172:graph:{binding}"),
            "resolver_hash": stable_hash(
                f"reference-l172:binding-resolver:{binding}"
            ),
            "verifier_hash": stable_hash(
                f"reference-l172:binding-verifier:{binding}"
            ),
            "publicly_verifiable": True,
            "tamper_evident": True,
            "survives_copy_or_transform": True,
            "resolves_to_current_status": True,
            "binds_settlement_obligation": True,
            "no_private_payloads": True,
        }

    def channel_row(channel: str) -> dict[str, Any]:
        return {
            "channel_hash": stable_hash(f"reference-l172:channel:{channel}"),
            "endpoint_hash": stable_hash(f"reference-l172:endpoint:{channel}"),
            "discovery_manifest_hash": stable_hash(
                f"reference-l172:discovery:{channel}"
            ),
            "last_observed_root_hash": stable_hash(f"reference-l172:root:{channel}"),
            "verifier_hash": stable_hash(
                f"reference-l172:channel-verifier:{channel}"
            ),
            "endpoint_published": True,
            "current_status_resolves": True,
            "revocation_status_included": True,
            "correction_status_included": True,
            "settlement_status_included": True,
            "no_split_view_observed": True,
            "no_private_payloads": True,
        }

    passport_input: dict[str, Any] = {
        "universal_source_grounded_response_receipt": source_receipt,
        "universal_content_credential": content_credential,
        "distribution_surface_rows": {
            surface: surface_row(surface)
            for surface in L172_REQUIRED_DISTRIBUTION_SURFACES
        },
        "portable_binding_rows": {
            binding: binding_row(binding)
            for binding in L172_REQUIRED_PORTABLE_BINDINGS
        },
        "status_channel_rows": {
            channel: channel_row(channel)
            for channel in L172_REQUIRED_STATUS_CHANNELS
        },
        "negative_distribution_rows": {
            failure: {
                "fixture_hash": stable_hash(f"reference-l172:negative:{failure}"),
                "expected_reject": True,
                "observed_reject": True,
                "distribution_blocked": True,
                "third_party_reliance_blocked": True,
                "downstream_reuse_blocked": True,
                "settlement_carry_forward_held": True,
                "public_status_marked_failed": True,
            }
            for failure in L172_REQUIRED_NEGATIVE_DISTRIBUTION_FAILURES
        },
        "private_strings": ["private reference l172 distribution reliance fixture"],
    }
    save("universal_distribution_reliance_passport_input", passport_input)
    passport = make_universal_distribution_reliance_passport(
        passport_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_distribution_reliance_passport", passport)
    return passport


def regenerate_l173_adversarial_provenance_quorum() -> dict[str, Any]:
    distribution_passport = load("universal_distribution_reliance_passport")
    witness_quorum = load("universal_accountability_witness_quorum")

    def signal_row(signal: str) -> dict[str, Any]:
        return {
            "signal_hash": stable_hash(f"reference-l173:signal:{signal}"),
            "l172_passport_hash": stable_hash(f"reference-l173:l172:{signal}"),
            "witness_quorum_hash": stable_hash(
                f"reference-l173:witness:{signal}"
            ),
            "independent_observation_hash": stable_hash(
                f"reference-l173:observe:{signal}"
            ),
            "status_resolver_hash": stable_hash(
                f"reference-l173:resolver:{signal}"
            ),
            "adversarial_test_hash": stable_hash(f"reference-l173:test:{signal}"),
            "verifier_hash": stable_hash(
                f"reference-l173:signal-verifier:{signal}"
            ),
            "signal_present": True,
            "signal_independent": True,
            "signal_matches_l172": True,
            "witness_observed": True,
            "current_status_resolves": True,
            "spoof_resistant": True,
            "no_private_payloads": True,
        }

    def attack_row(attack: str) -> dict[str, Any]:
        return {
            "fixture_hash": stable_hash(f"reference-l173:fixture:{attack}"),
            "attack_trace_hash": stable_hash(f"reference-l173:attack:{attack}"),
            "expected_reject": True,
            "observed_reject": True,
            "signal_quorum_failed_closed": True,
            "reliance_blocked": True,
            "settlement_held": True,
            "public_status_marked_failed": True,
            "no_private_payloads": True,
        }

    def context_row(context: str) -> dict[str, Any]:
        return {
            "context_hash": stable_hash(f"reference-l173:context:{context}"),
            "minimum_signal_root_hash": stable_hash(
                f"reference-l173:signal-root:{context}"
            ),
            "attack_root_hash": stable_hash(
                f"reference-l173:attack-root:{context}"
            ),
            "l172_passport_hash": stable_hash(
                f"reference-l173:context-l172:{context}"
            ),
            "witness_quorum_hash": stable_hash(
                f"reference-l173:context-witness:{context}"
            ),
            "verifier_hash": stable_hash(
                f"reference-l173:context-verifier:{context}"
            ),
            "context_supported": True,
            "quorum_threshold_met": True,
            "current_status_checked": True,
            "high_stakes_policy_applied": True,
            "reliance_allowed_only_on_quorum": True,
            "settlement_release_bound": True,
            "no_private_payloads": True,
        }

    quorum_input: dict[str, Any] = {
        "universal_distribution_reliance_passport": distribution_passport,
        "universal_accountability_witness_quorum": witness_quorum,
        "provenance_signal_rows": {
            signal: signal_row(signal)
            for signal in L173_REQUIRED_PROVENANCE_SIGNALS
        },
        "attack_resistance_rows": {
            attack: attack_row(attack) for attack in L173_REQUIRED_ATTACK_CLASSES
        },
        "reliance_context_rows": {
            context: context_row(context)
            for context in L173_REQUIRED_RELIANCE_CONTEXTS
        },
        "private_strings": ["private reference l173 adversarial provenance fixture"],
    }
    save("universal_adversarial_provenance_quorum_input", quorum_input)
    quorum = make_universal_adversarial_provenance_quorum(
        quorum_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_adversarial_provenance_quorum", quorum)
    return quorum


def regenerate_l174_procurement_regulatory_reliance_contract() -> dict[str, Any]:
    adversarial_quorum = load("universal_adversarial_provenance_quorum")
    industry_root = load("universal_industry_adoption_root")

    def role_row(role: str) -> dict[str, Any]:
        return {
            "role_hash": stable_hash(f"reference-l174:role:{role}"),
            "contract_hash": stable_hash(f"reference-l174:role-contract:{role}"),
            "l173_quorum_hash": stable_hash(f"reference-l174:l173:{role}"),
            "authority_hash": stable_hash(f"reference-l174:authority:{role}"),
            "endpoint_hash": stable_hash(f"reference-l174:endpoint:{role}"),
            "verifier_hash": stable_hash(f"reference-l174:role-verifier:{role}"),
            "accepts_rdllm_standard": True,
            "binds_l173_quorum": True,
            "publishes_well_known_contract": True,
            "blocks_unbound_claims": True,
            "preserves_footer_or_machine_readable_sources": True,
            "supports_creator_challenge": True,
            "no_private_payloads": True,
        }

    def control_row(control: str) -> dict[str, Any]:
        return {
            "control_hash": stable_hash(f"reference-l174:control:{control}"),
            "obligation_hash": stable_hash(f"reference-l174:obligation:{control}"),
            "evidence_hash": stable_hash(f"reference-l174:evidence:{control}"),
            "enforcement_hash": stable_hash(
                f"reference-l174:enforcement:{control}"
            ),
            "remedy_hash": stable_hash(f"reference-l174:remedy:{control}"),
            "verifier_hash": stable_hash(
                f"reference-l174:control-verifier:{control}"
            ),
            "obligation_binding": True,
            "measurable_sla": True,
            "audit_evidence_exported": True,
            "breach_blocks_reliance": True,
            "settlement_or_display_remedy": True,
            "no_private_payloads": True,
        }

    def jurisdiction_row(mapping: str) -> dict[str, Any]:
        return {
            "jurisdiction_hash": stable_hash(
                f"reference-l174:jurisdiction:{mapping}"
            ),
            "obligation_hash": stable_hash(
                f"reference-l174:j-obligation:{mapping}"
            ),
            "mapping_hash": stable_hash(f"reference-l174:mapping:{mapping}"),
            "evidence_export_hash": stable_hash(f"reference-l174:export:{mapping}"),
            "verifier_hash": stable_hash(f"reference-l174:j-verifier:{mapping}"),
            "maps_to_provider_duty": True,
            "maps_to_customer_duty": True,
            "regulator_readable": True,
            "creator_readable": True,
            "footer_and_machine_readable_attribution_supported": True,
            "no_private_payloads": True,
        }

    def negative_row(failure: str) -> dict[str, Any]:
        return {
            "fixture_hash": stable_hash(f"reference-l174:fixture:{failure}"),
            "route_trace_hash": stable_hash(f"reference-l174:trace:{failure}"),
            "contract_hash": stable_hash(
                f"reference-l174:negative-contract:{failure}"
            ),
            "verifier_hash": stable_hash(
                f"reference-l174:negative-verifier:{failure}"
            ),
            "expected_reject": True,
            "observed_reject": True,
            "procurement_blocked": True,
            "marketplace_delisted": True,
            "regulator_warning_emitted": True,
            "settlement_held": True,
            "creator_challenge_routed": True,
            "no_private_payloads": True,
        }

    contract_input: dict[str, Any] = {
        "universal_adversarial_provenance_quorum": adversarial_quorum,
        "universal_industry_adoption_root": industry_root,
        "adoption_role_rows": {
            role: role_row(role) for role in L174_REQUIRED_ADOPTION_ROLES
        },
        "contractual_control_rows": {
            control: control_row(control)
            for control in L174_REQUIRED_CONTRACTUAL_CONTROLS
        },
        "jurisdiction_mapping_rows": {
            mapping: jurisdiction_row(mapping)
            for mapping in L174_REQUIRED_JURISDICTION_MAPPINGS
        },
        "negative_procurement_rows": {
            failure: negative_row(failure)
            for failure in L174_REQUIRED_NEGATIVE_PROCUREMENT_FAILURES
        },
        "private_strings": ["private reference l174 procurement reliance fixture"],
    }
    save("universal_procurement_regulatory_reliance_contract_input", contract_input)
    contract = make_universal_procurement_regulatory_reliance_contract(
        contract_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_procurement_regulatory_reliance_contract", contract)
    return contract


def regenerate_l175_provider_onboarding_migration_covenant() -> dict[str, Any]:
    procurement_contract = load("universal_procurement_regulatory_reliance_contract")
    provider_binding_matrix = load("universal_foundation_provider_binding_matrix")
    provider_conformance_runner = load("universal_provider_conformance_runner_receipt")

    def provider_row(provider: str) -> dict[str, Any]:
        return {
            "provider_family_hash": stable_hash(f"reference-l175:provider:{provider}"),
            "native_api_contract_hash": stable_hash(
                f"reference-l175:native-api:{provider}"
            ),
            "adapter_release_hash": stable_hash(f"reference-l175:adapter:{provider}"),
            "sdk_release_hash": stable_hash(f"reference-l175:sdk:{provider}"),
            "gateway_policy_hash": stable_hash(f"reference-l175:gateway:{provider}"),
            "telemetry_hash": stable_hash(f"reference-l175:telemetry:{provider}"),
            "settlement_hash": stable_hash(f"reference-l175:settlement:{provider}"),
            "rollback_hash": stable_hash(f"reference-l175:rollback:{provider}"),
            "l174_contract_accepted": True,
            "native_surface_mapped": True,
            "conformance_runner_green": True,
            "customer_migration_supported": True,
            "legacy_route_fail_closed": True,
            "no_private_payloads": True,
        }

    def surface_row(surface: str) -> dict[str, Any]:
        return {
            "surface_mapping_hash": stable_hash(f"reference-l175:surface:{surface}"),
            "test_fixture_hash": stable_hash(f"reference-l175:fixture:{surface}"),
            "verifier_hash": stable_hash(f"reference-l175:verifier:{surface}"),
            "footer_contract_hash": stable_hash(f"reference-l175:footer:{surface}"),
            "telemetry_mapping_hash": stable_hash(
                f"reference-l175:telemetry-map:{surface}"
            ),
            "mapped_for_all_required_provider_families": True,
            "source_footer_preserved": True,
            "machine_readable_sources_preserved": True,
            "settlement_meter_bound": True,
            "negative_fixture_covered": True,
            "no_private_payloads": True,
        }

    def migration_row(artifact: str) -> dict[str, Any]:
        return {
            "migration_artifact_hash": stable_hash(
                f"reference-l175:migration:{artifact}"
            ),
            "version_hash": stable_hash(f"reference-l175:version:{artifact}"),
            "publication_hash": stable_hash(
                f"reference-l175:publication:{artifact}"
            ),
            "support_hash": stable_hash(f"reference-l175:support:{artifact}"),
            "rollback_hash": stable_hash(
                f"reference-l175:migration-rollback:{artifact}"
            ),
            "published": True,
            "customer_executable": True,
            "binds_l174_contract": True,
            "covers_all_required_provider_families": True,
            "no_private_payloads": True,
        }

    def rollout_row(gate: str) -> dict[str, Any]:
        return {
            "rollout_gate_hash": stable_hash(f"reference-l175:gate:{gate}"),
            "owner_hash": stable_hash(f"reference-l175:owner:{gate}"),
            "evidence_hash": stable_hash(f"reference-l175:evidence:{gate}"),
            "verifier_hash": stable_hash(f"reference-l175:gate-verifier:{gate}"),
            "sla_hash": stable_hash(f"reference-l175:sla:{gate}"),
            "gate_passed": True,
            "blocks_ga_on_failure": True,
            "rollback_on_failure": True,
            "audit_visible": True,
            "no_private_payloads": True,
        }

    def negative_row(failure: str) -> dict[str, Any]:
        return {
            "fixture_hash": stable_hash(f"reference-l175:negative:{failure}"),
            "native_route_hash": stable_hash(f"reference-l175:native-route:{failure}"),
            "verifier_hash": stable_hash(
                f"reference-l175:negative-verifier:{failure}"
            ),
            "expected_reject": True,
            "observed_reject": True,
            "migration_blocked": True,
            "provider_claim_blocked": True,
            "rollback_triggered": True,
            "settlement_held": True,
            "no_private_payloads": True,
        }

    covenant_input: dict[str, Any] = {
        "universal_procurement_regulatory_reliance_contract": procurement_contract,
        "universal_foundation_provider_binding_matrix": provider_binding_matrix,
        "universal_provider_conformance_runner_receipt": provider_conformance_runner,
        "provider_family_rows": {
            provider: provider_row(provider)
            for provider in L175_REQUIRED_PROVIDER_FAMILIES
        },
        "native_api_surface_rows": {
            surface: surface_row(surface)
            for surface in L175_REQUIRED_NATIVE_API_SURFACES
        },
        "migration_artifact_rows": {
            artifact: migration_row(artifact)
            for artifact in L175_REQUIRED_MIGRATION_ARTIFACTS
        },
        "rollout_gate_rows": {
            gate: rollout_row(gate) for gate in L175_REQUIRED_ROLLOUT_GATES
        },
        "negative_onboarding_rows": {
            failure: negative_row(failure)
            for failure in L175_REQUIRED_NEGATIVE_ONBOARDING_FAILURES
        },
        "private_strings": [
            "private reference l175 provider onboarding migration fixture"
        ],
    }
    save("universal_provider_onboarding_migration_covenant_input", covenant_input)
    covenant = make_universal_provider_onboarding_migration_covenant(
        covenant_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_provider_onboarding_migration_covenant", covenant)
    return covenant


def regenerate_l176_model_provider_registry() -> dict[str, Any]:
    onboarding_covenant = load("universal_provider_onboarding_migration_covenant")

    def registry_source_row(source: str) -> dict[str, Any]:
        return {
            "registry_source_hash": stable_hash(f"reference-l176:source:{source}"),
            "catalog_snapshot_hash": stable_hash(f"reference-l176:snapshot:{source}"),
            "schema_hash": stable_hash(f"reference-l176:schema:{source}"),
            "fetch_verifier_hash": stable_hash(f"reference-l176:fetch:{source}"),
            "freshness_sla_hash": stable_hash(f"reference-l176:freshness:{source}"),
            "source_available": True,
            "snapshot_signed": True,
            "supports_model_ids": True,
            "supports_capability_metadata": True,
            "supports_lifecycle_events": True,
            "no_private_payloads": True,
        }

    def namespace_row(namespace: str) -> dict[str, Any]:
        return {
            "namespace_hash": stable_hash(f"reference-l176:namespace:{namespace}"),
            "owner_attestation_hash": stable_hash(
                f"reference-l176:owner:{namespace}"
            ),
            "adapter_policy_hash": stable_hash(
                f"reference-l176:adapter-policy:{namespace}"
            ),
            "namespace_unique": True,
            "publisher_identity_bound": True,
            "hosting_provider_bound": True,
            "route_ids_globally_unique": True,
            "no_private_payloads": True,
        }

    def route_class_row(route_class: str) -> dict[str, Any]:
        return {
            "model_route_hash": stable_hash(
                f"reference-l176:route-class:{route_class}"
            ),
            "capability_manifest_hash": stable_hash(
                f"reference-l176:capability:{route_class}"
            ),
            "modality_manifest_hash": stable_hash(
                f"reference-l176:modality:{route_class}"
            ),
            "context_limit_hash": stable_hash(
                f"reference-l176:context:{route_class}"
            ),
            "pricing_meter_hash": stable_hash(
                f"reference-l176:pricing:{route_class}"
            ),
            "source_footer_required": True,
            "machine_readable_sources_required": True,
            "settlement_meter_required": True,
            "negative_fixture_required": True,
            "no_private_payloads": True,
        }

    def adapter_row(route_class: str) -> dict[str, Any]:
        return {
            "adapter_manifest_hash": stable_hash(
                f"reference-l176:adapter:{route_class}"
            ),
            "schema_hash": stable_hash(
                f"reference-l176:adapter-schema:{route_class}"
            ),
            "verifier_hash": stable_hash(
                f"reference-l176:adapter-verifier:{route_class}"
            ),
            "source_footer_contract_hash": stable_hash(
                f"reference-l176:footer-contract:{route_class}"
            ),
            "conformance_receipt_hash": stable_hash(
                f"reference-l176:conformance:{route_class}"
            ),
            "adapter_discoverable": True,
            "maps_native_request_response": True,
            "maps_streaming_final_event": True,
            "maps_tool_and_batch_outputs": True,
            "conformance_green": True,
            "no_private_payloads": True,
        }

    def lifecycle_row(event: str) -> dict[str, Any]:
        return {
            "lifecycle_event_hash": stable_hash(f"reference-l176:lifecycle:{event}"),
            "catalog_snapshot_hash": stable_hash(
                f"reference-l176:lifecycle-snapshot:{event}"
            ),
            "notification_hash": stable_hash(
                f"reference-l176:notification:{event}"
            ),
            "migration_policy_hash": stable_hash(
                f"reference-l176:migration-policy:{event}"
            ),
            "event_supported": True,
            "breaks_reliance_on_stale_state": True,
            "blocks_settlement_on_unhandled_event": True,
            "no_private_payloads": True,
        }

    def negative_row(failure: str) -> dict[str, Any]:
        return {
            "fixture_hash": stable_hash(f"reference-l176:negative:{failure}"),
            "verifier_hash": stable_hash(
                f"reference-l176:negative-verifier:{failure}"
            ),
            "expected_reject": True,
            "observed_reject": True,
            "provider_claim_blocked": True,
            "route_registration_blocked": True,
            "settlement_held": True,
            "no_private_payloads": True,
        }

    def declared_route(index: int, route_class: str) -> dict[str, Any]:
        namespace = L176_REQUIRED_PROVIDER_NAMESPACE_CLASSES[
            index % len(L176_REQUIRED_PROVIDER_NAMESPACE_CLASSES)
        ]
        source = L176_REQUIRED_REGISTRY_SOURCES[
            index % len(L176_REQUIRED_REGISTRY_SOURCES)
        ]
        return {
            "route_id": f"reference-route:{namespace}:{route_class}:{index}",
            "provider_namespace": namespace,
            "registry_source": source,
            "model_route_class": route_class,
            "endpoint_protocol": "openai-compatible-json",
            "model_identity_hash": stable_hash(
                f"reference-l176:model:{route_class}:{index}"
            ),
            "service_object_hash": stable_hash(
                f"reference-l176:service:{route_class}:{index}"
            ),
            "catalog_snapshot_hash": stable_hash(
                f"reference-l176:route-snapshot:{route_class}:{index}"
            ),
            "adapter_manifest_hash": stable_hash(
                f"reference-l176:route-adapter:{route_class}:{index}"
            ),
            "conformance_receipt_hash": stable_hash(
                f"reference-l176:route-conformance:{route_class}:{index}"
            ),
            "source_footer_contract_hash": stable_hash(
                f"reference-l176:route-footer:{route_class}:{index}"
            ),
            "settlement_meter_hash": stable_hash(
                f"reference-l176:route-settlement:{route_class}:{index}"
            ),
            "lifecycle_state_hash": stable_hash(
                f"reference-l176:route-lifecycle:{route_class}:{index}"
            ),
            "registered": True,
            "adapter_discoverable": True,
            "capability_metadata_complete": True,
            "modalities_declared": True,
            "context_limit_declared": True,
            "pricing_meter_bound": True,
            "source_footer_supported": True,
            "machine_readable_sources_supported": True,
            "settlement_meter_bound": True,
            "conformance_green": True,
            "lifecycle_state_current": True,
            "no_private_payloads": True,
        }

    registry_input: dict[str, Any] = {
        "universal_provider_onboarding_migration_covenant": onboarding_covenant,
        "registry_source_rows": {
            source: registry_source_row(source)
            for source in L176_REQUIRED_REGISTRY_SOURCES
        },
        "provider_namespace_rows": {
            namespace: namespace_row(namespace)
            for namespace in L176_REQUIRED_PROVIDER_NAMESPACE_CLASSES
        },
        "model_route_class_rows": {
            route_class: route_class_row(route_class)
            for route_class in L176_REQUIRED_MODEL_ROUTE_CLASSES
        },
        "adapter_discovery_rows": {
            route_class: adapter_row(route_class)
            for route_class in L176_REQUIRED_MODEL_ROUTE_CLASSES
        },
        "lifecycle_event_rows": {
            event: lifecycle_row(event)
            for event in L176_REQUIRED_MODEL_LIFECYCLE_EVENTS
        },
        "declared_model_routes": [
            declared_route(index, route_class)
            for index, route_class in enumerate(L176_REQUIRED_MODEL_ROUTE_CLASSES)
        ],
        "negative_registry_rows": {
            failure: negative_row(failure)
            for failure in L176_REQUIRED_NEGATIVE_REGISTRY_FAILURES
        },
        "private_strings": ["private reference l176 model provider registry fixture"],
    }
    save("universal_model_provider_registry_input", registry_input)
    registry = make_universal_model_provider_registry(
        registry_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_model_provider_registry", registry)
    return registry


def regenerate_l177_source_footer_enforcement_contract() -> dict[str, Any]:
    model_provider_registry = load("universal_model_provider_registry")
    source_grounded_response_receipt = load(
        "universal_source_grounded_response_receipt"
    )
    declared_routes = model_provider_registry.get("declared_model_routes", [])

    def stage_row(stage: str) -> dict[str, Any]:
        return {
            "stage_hash": stable_hash(f"reference-l177:stage:{stage}"),
            "policy_hash": stable_hash(f"reference-l177:stage-policy:{stage}"),
            "verifier_hash": stable_hash(f"reference-l177:stage-verifier:{stage}"),
            "enabled": True,
            "telemetry_bound": True,
            "auditable": True,
            "fail_closed": True,
            "no_private_payloads": True,
        }

    def source_type_row(source_type: str) -> dict[str, Any]:
        return {
            "source_type_hash": stable_hash(
                f"reference-l177:source-type:{source_type}"
            ),
            "identity_resolver_hash": stable_hash(
                f"reference-l177:identity:{source_type}"
            ),
            "locator_verifier_hash": stable_hash(
                f"reference-l177:locator:{source_type}"
            ),
            "rights_policy_hash": stable_hash(
                f"reference-l177:rights:{source_type}"
            ),
            "confidence_policy_hash": stable_hash(
                f"reference-l177:confidence:{source_type}"
            ),
            "discoverable": True,
            "citable_or_abstainable": True,
            "visible_footer_allowed": True,
            "machine_readable_source_allowed": True,
            "no_private_payloads": True,
        }

    def footer_field_row(field: str) -> dict[str, Any]:
        return {
            "footer_field_hash": stable_hash(
                f"reference-l177:footer-field:{field}"
            ),
            "schema_hash": stable_hash(
                f"reference-l177:footer-field-schema:{field}"
            ),
            "render_verifier_hash": stable_hash(
                f"reference-l177:footer-render:{field}"
            ),
            "field_required": True,
            "rendered_when_applicable": True,
            "machine_readable": True,
            "privacy_safe": True,
            "no_private_payloads": True,
        }

    def surface_row(surface: str) -> dict[str, Any]:
        return {
            "surface_hash": stable_hash(f"reference-l177:surface:{surface}"),
            "footer_renderer_hash": stable_hash(
                f"reference-l177:surface-renderer:{surface}"
            ),
            "verifier_hash": stable_hash(
                f"reference-l177:surface-verifier:{surface}"
            ),
            "copy_export_hash": stable_hash(
                f"reference-l177:surface-copy:{surface}"
            ),
            "footer_visible": True,
            "machine_readable_sources_visible": True,
            "final_response_gate_enabled": True,
            "copy_export_preserves_footer": True,
            "no_private_payloads": True,
        }

    def route_row(route: dict[str, Any]) -> dict[str, Any]:
        route_id = str(route.get("route_id", ""))
        return {
            "route_id": route_id,
            "provider_namespace": str(route.get("provider_namespace", "")),
            "model_route_class": str(route.get("model_route_class", "")),
            "model_identity_hash": str(route.get("model_identity_hash", "")),
            "registry_route_hash": stable_hash(
                f"reference-l177:registry-route:{route_id}"
            ),
            "route_enforcement_hash": stable_hash(
                f"reference-l177:route:{route_id}"
            ),
            "source_grounded_response_receipt_hash": (
                source_grounded_response_receipt[
                    "universal_source_grounded_response_receipt_hash"
                ]
            ),
            "answer_release_gate_hash": stable_hash(
                f"reference-l177:release-gate:{route_id}"
            ),
            "footer_renderer_hash": stable_hash(
                f"reference-l177:footer-renderer:{route_id}"
            ),
            "source_verifier_hash": stable_hash(
                f"reference-l177:source-verifier:{route_id}"
            ),
            "no_source_abstention_hash": stable_hash(
                f"reference-l177:abstention:{route_id}"
            ),
            "settlement_hold_hash": stable_hash(
                f"reference-l177:settlement:{route_id}"
            ),
            "telemetry_span_hash": stable_hash(
                f"reference-l177:telemetry:{route_id}"
            ),
            "conformance_verifier_hash": stable_hash(
                f"reference-l177:conformance:{route_id}"
            ),
            "route_registered_l176": True,
            "source_grounded_response_l171_bound": True,
            "answer_release_gate_enabled": True,
            "footer_injection_enabled": True,
            "machine_readable_sources_emitted": True,
            "claim_source_support_required": True,
            "unsupported_claims_refused": True,
            "posthoc_citations_rejected": True,
            "no_source_abstention_enabled": True,
            "copy_export_preserves_sources": True,
            "settlement_hold_enforced": True,
            "no_private_payloads": True,
        }

    def negative_row(failure: str) -> dict[str, Any]:
        return {
            "fixture_hash": stable_hash(f"reference-l177:negative:{failure}"),
            "verifier_hash": stable_hash(
                f"reference-l177:negative-verifier:{failure}"
            ),
            "expected_reject": True,
            "observed_reject": True,
            "answer_release_blocked": True,
            "footer_reliance_blocked": True,
            "source_reliance_blocked": True,
            "settlement_held": True,
            "public_status_marked_failed": True,
            "no_private_payloads": True,
        }

    contract_input: dict[str, Any] = {
        "universal_model_provider_registry": model_provider_registry,
        "universal_source_grounded_response_receipt": (
            source_grounded_response_receipt
        ),
        "enforcement_stage_rows": {
            stage: stage_row(stage) for stage in L177_REQUIRED_ENFORCEMENT_STAGES
        },
        "source_type_rows": {
            source_type: source_type_row(source_type)
            for source_type in L177_REQUIRED_SOURCE_TYPES
        },
        "footer_row_field_rows": {
            field: footer_field_row(field) for field in L177_REQUIRED_FOOTER_ROW_FIELDS
        },
        "response_surface_rows": {
            surface: surface_row(surface) for surface in L177_REQUIRED_RESPONSE_SURFACES
        },
        "route_enforcement_rows": {
            str(route.get("route_id", "")): route_row(route)
            for route in declared_routes
            if route.get("route_id")
        },
        "negative_footer_rows": {
            failure: negative_row(failure)
            for failure in L177_REQUIRED_NEGATIVE_FOOTER_FAILURES
        },
        "private_strings": [
            "private reference l177 source footer enforcement fixture"
        ],
    }
    save("universal_source_footer_enforcement_contract_input", contract_input)
    contract = make_universal_source_footer_enforcement_contract(
        contract_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_source_footer_enforcement_contract", contract)
    return contract


def regenerate_l178_provider_catalog_coverage_contract() -> dict[str, Any]:
    model_provider_registry = load("universal_model_provider_registry")
    source_footer_enforcement_contract = load(
        "universal_source_footer_enforcement_contract"
    )
    declared_routes = model_provider_registry.get("declared_model_routes", [])

    def channel_row(channel: str) -> dict[str, Any]:
        return {
            "catalog_channel_hash": stable_hash(f"reference-l178:channel:{channel}"),
            "schema_hash": stable_hash(f"reference-l178:channel-schema:{channel}"),
            "fetcher_hash": stable_hash(f"reference-l178:fetcher:{channel}"),
            "normalizer_hash": stable_hash(f"reference-l178:normalizer:{channel}"),
            "complete_export_attested": True,
            "fresh_within_sla": True,
            "pagination_exhausted": True,
            "supports_delta_events": True,
            "no_private_payloads": True,
        }

    def field_row(field: str) -> dict[str, Any]:
        return {
            "field_hash": stable_hash(f"reference-l178:field:{field}"),
            "normalizer_hash": stable_hash(
                f"reference-l178:field-normalizer:{field}"
            ),
            "verifier_hash": stable_hash(f"reference-l178:field-verifier:{field}"),
            "field_required": True,
            "field_normalized": True,
            "capability_safe": True,
            "public_metadata_only": True,
            "no_private_payloads": True,
        }

    def snapshot_row(channel: str) -> dict[str, Any]:
        return {
            "catalog_snapshot_hash": stable_hash(f"reference-l178:snapshot:{channel}"),
            "catalog_channel_hash": stable_hash(f"reference-l178:channel:{channel}"),
            "entry_count_hash": stable_hash(f"reference-l178:entry-count:{channel}"),
            "freshness_hash": stable_hash(f"reference-l178:freshness:{channel}"),
            "complete_snapshot": True,
            "signed_snapshot": True,
            "pagination_exhausted": True,
            "no_private_payloads": True,
        }

    def discovered_row(route: dict[str, Any]) -> dict[str, Any]:
        route_id = str(route.get("route_id", ""))
        return {
            "catalog_model_id": f"reference-catalog:{route_id}",
            "provider_namespace": str(route.get("provider_namespace", "")),
            "registry_source": str(route.get("registry_source", "")),
            "model_route_class": str(route.get("model_route_class", "")),
            "catalog_entry_hash": stable_hash(
                f"reference-l178:catalog-entry:{route_id}"
            ),
            "provider_model_id_hash": stable_hash(
                f"reference-l178:provider-model:{route_id}"
            ),
            "normalized_route_id": route_id,
            "capability_manifest_hash": stable_hash(
                f"reference-l178:capability:{route_id}"
            ),
            "pricing_meter_hash": stable_hash(f"reference-l178:pricing:{route_id}"),
            "lifecycle_state_hash": stable_hash(
                f"reference-l178:lifecycle:{route_id}"
            ),
            "source_footer_profile_hash": stable_hash(
                f"reference-l178:footer-profile:{route_id}"
            ),
            "settlement_meter_hash": stable_hash(
                f"reference-l178:settlement:{route_id}"
            ),
            "coverage_decision": "admitted_registered_route",
            "catalog_entry_seen": True,
            "capability_metadata_normalized": True,
            "catalog_snapshot_current": True,
            "lifecycle_status_current": True,
            "l176_route_registered": True,
            "l177_footer_enforced": True,
            "registration_blocked": False,
            "source_footer_profile_bound": True,
            "settlement_meter_bound": True,
            "settlement_held": False,
            "registered_or_blocked": True,
            "source_footer_enforced_or_blocked": True,
            "settlement_allowed_or_held": True,
            "public_status_marked": True,
            "no_private_payloads": True,
        }

    def blocked_discovered_row() -> dict[str, Any]:
        return {
            "catalog_model_id": "reference-catalog:quarantined-unknown-model",
            "provider_namespace": L176_REQUIRED_PROVIDER_NAMESPACE_CLASSES[0],
            "registry_source": L176_REQUIRED_REGISTRY_SOURCES[0],
            "model_route_class": L176_REQUIRED_MODEL_ROUTE_CLASSES[0],
            "catalog_entry_hash": stable_hash("reference-l178:catalog-entry:blocked"),
            "provider_model_id_hash": stable_hash(
                "reference-l178:provider-model:blocked"
            ),
            "normalized_route_id": "blocked:quarantined-unknown-model",
            "capability_manifest_hash": stable_hash(
                "reference-l178:capability:blocked"
            ),
            "pricing_meter_hash": stable_hash("reference-l178:pricing:blocked"),
            "lifecycle_state_hash": stable_hash("reference-l178:lifecycle:blocked"),
            "source_footer_profile_hash": stable_hash(
                "reference-l178:footer-profile:blocked"
            ),
            "settlement_meter_hash": stable_hash(
                "reference-l178:settlement:blocked"
            ),
            "coverage_decision": "quarantined_unknown_model",
            "catalog_entry_seen": True,
            "capability_metadata_normalized": True,
            "catalog_snapshot_current": True,
            "lifecycle_status_current": True,
            "l176_route_registered": False,
            "l177_footer_enforced": False,
            "registration_blocked": True,
            "source_footer_profile_bound": True,
            "settlement_meter_bound": True,
            "settlement_held": True,
            "registered_or_blocked": True,
            "source_footer_enforced_or_blocked": True,
            "settlement_allowed_or_held": True,
            "public_status_marked": True,
            "no_private_payloads": True,
        }

    def route_coverage_row(route: dict[str, Any]) -> dict[str, Any]:
        route_id = str(route.get("route_id", ""))
        return {
            "route_id": route_id,
            "catalog_coverage_hash": stable_hash(
                f"reference-l178:coverage:{route_id}"
            ),
            "catalog_entry_hash": stable_hash(
                f"reference-l178:catalog-entry:{route_id}"
            ),
            "route_identity_hash": str(route.get("model_identity_hash", "")),
            "verifier_hash": stable_hash(
                f"reference-l178:coverage-verifier:{route_id}"
            ),
            "l176_route_present": True,
            "l177_route_enforced": True,
            "discovered_or_exempted": True,
            "catalog_snapshot_current": True,
            "no_private_payloads": True,
        }

    def negative_row(failure: str) -> dict[str, Any]:
        return {
            "fixture_hash": stable_hash(f"reference-l178:negative:{failure}"),
            "verifier_hash": stable_hash(
                f"reference-l178:negative-verifier:{failure}"
            ),
            "expected_reject": True,
            "observed_reject": True,
            "catalog_claim_blocked": True,
            "route_admission_blocked": True,
            "source_footer_reliance_blocked": True,
            "settlement_held": True,
            "no_private_payloads": True,
        }

    contract_input: dict[str, Any] = {
        "universal_model_provider_registry": model_provider_registry,
        "universal_source_footer_enforcement_contract": (
            source_footer_enforcement_contract
        ),
        "catalog_channel_rows": {
            channel: channel_row(channel)
            for channel in L178_REQUIRED_CATALOG_DISCOVERY_CHANNELS
        },
        "normalization_field_rows": {
            field: field_row(field) for field in L178_REQUIRED_NORMALIZED_MODEL_FIELDS
        },
        "catalog_snapshot_rows": {
            channel: snapshot_row(channel)
            for channel in L178_REQUIRED_CATALOG_DISCOVERY_CHANNELS
        },
        "discovered_model_rows": [
            discovered_row(route) for route in declared_routes if route.get("route_id")
        ]
        + [blocked_discovered_row()],
        "registry_route_coverage_rows": {
            str(route.get("route_id", "")): route_coverage_row(route)
            for route in declared_routes
            if route.get("route_id")
        },
        "negative_catalog_rows": {
            failure: negative_row(failure)
            for failure in L178_REQUIRED_NEGATIVE_CATALOG_FAILURES
        },
        "private_strings": [
            "private reference l178 provider catalog coverage fixture"
        ],
    }
    save("universal_provider_catalog_coverage_contract_input", contract_input)
    contract = make_universal_provider_catalog_coverage_contract(
        contract_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_provider_catalog_coverage_contract", contract)
    return contract


def regenerate_l179_runtime_route_binding_contract() -> dict[str, Any]:
    production_admission = load("universal_production_invocation_admission")
    catalog_coverage = load("universal_provider_catalog_coverage_contract")
    route_ids = sorted(
        str(row.get("route_id") or route_id)
        for route_id, row in catalog_coverage.get(
            "registry_route_coverage_rows", {}
        ).items()
        if isinstance(row, dict) and (row.get("route_id") or route_id)
    )

    def stage_row(stage: str) -> dict[str, Any]:
        return {
            "stage_hash": stable_hash(f"reference-l179:stage:{stage}"),
            "policy_hash": stable_hash(f"reference-l179:stage-policy:{stage}"),
            "verifier_hash": stable_hash(f"reference-l179:stage-verifier:{stage}"),
            "enabled": True,
            "telemetry_bound": True,
            "fail_closed": True,
            "auditable": True,
            "no_private_payloads": True,
        }

    def field_row(field: str) -> dict[str, Any]:
        return {
            "field_hash": stable_hash(f"reference-l179:field:{field}"),
            "schema_hash": stable_hash(f"reference-l179:field-schema:{field}"),
            "verifier_hash": stable_hash(f"reference-l179:field-verifier:{field}"),
            "field_required": True,
            "request_bound": True,
            "response_bound": True,
            "telemetry_bound": True,
            "privacy_safe": True,
            "no_private_payloads": True,
        }

    def surface_row(surface: str) -> dict[str, Any]:
        return {
            "surface_hash": stable_hash(f"reference-l179:surface:{surface}"),
            "route_binding_policy_hash": stable_hash(
                f"reference-l179:surface-policy:{surface}"
            ),
            "verifier_hash": stable_hash(
                f"reference-l179:surface-verifier:{surface}"
            ),
            "request_model_echo_required": True,
            "response_model_echo_required": True,
            "telemetry_required": True,
            "source_footer_route_required": True,
            "settlement_meter_required": True,
            "fail_closed": True,
            "no_private_payloads": True,
        }

    def route_row(route_id: str) -> dict[str, Any]:
        return {
            "route_id": route_id,
            "runtime_binding_hash": stable_hash(f"reference-l179:runtime:{route_id}"),
            "catalog_coverage_hash": stable_hash(
                f"reference-l179:catalog-coverage:{route_id}"
            ),
            "production_admission_hash": production_admission[
                "universal_production_invocation_admission_hash"
            ],
            "admission_token_hash": stable_hash(f"reference-l179:token:{route_id}"),
            "request_model_lock_hash": stable_hash(
                f"reference-l179:request-lock:{route_id}"
            ),
            "response_model_echo_hash": stable_hash(
                f"reference-l179:response-echo:{route_id}"
            ),
            "telemetry_span_hash": stable_hash(
                f"reference-l179:telemetry:{route_id}"
            ),
            "source_footer_route_hash": stable_hash(
                f"reference-l179:footer:{route_id}"
            ),
            "settlement_meter_route_hash": stable_hash(
                f"reference-l179:settlement:{route_id}"
            ),
            "verifier_hash": stable_hash(f"reference-l179:verifier:{route_id}"),
            "l178_catalog_covered": True,
            "l170_admission_bound": True,
            "requested_model_locked": True,
            "response_model_echo_matched": True,
            "alias_resolution_checked": True,
            "fallback_blocked_or_bound": True,
            "streaming_final_bound": True,
            "tool_batch_callbacks_bound": True,
            "telemetry_route_bound": True,
            "source_footer_route_bound": True,
            "settlement_meter_route_bound": True,
            "response_release_gate_enabled": True,
            "no_private_payloads": True,
        }

    def negative_row(failure: str) -> dict[str, Any]:
        return {
            "fixture_hash": stable_hash(f"reference-l179:negative:{failure}"),
            "verifier_hash": stable_hash(
                f"reference-l179:negative-verifier:{failure}"
            ),
            "expected_reject": True,
            "observed_reject": True,
            "runtime_route_blocked": True,
            "response_release_blocked": True,
            "source_footer_reliance_blocked": True,
            "settlement_held": True,
            "public_status_marked_failed": True,
            "no_private_payloads": True,
        }

    contract_input: dict[str, Any] = {
        "universal_production_invocation_admission": production_admission,
        "universal_provider_catalog_coverage_contract": catalog_coverage,
        "runtime_binding_stage_rows": {
            stage: stage_row(stage) for stage in L179_REQUIRED_RUNTIME_BINDING_STAGES
        },
        "runtime_model_field_rows": {
            field: field_row(field) for field in L179_REQUIRED_RUNTIME_MODEL_FIELDS
        },
        "runtime_surface_rows": {
            surface: surface_row(surface) for surface in L179_REQUIRED_RUNTIME_SURFACES
        },
        "runtime_route_binding_rows": {
            route_id: route_row(route_id) for route_id in route_ids
        },
        "negative_runtime_rows": {
            failure: negative_row(failure)
            for failure in L179_REQUIRED_NEGATIVE_RUNTIME_FAILURES
        },
        "private_strings": [
            "private reference l179 runtime route binding fixture"
        ],
    }
    save("universal_runtime_route_binding_contract_input", contract_input)
    contract = make_universal_runtime_route_binding_contract(
        contract_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_runtime_route_binding_contract", contract)
    return contract


def regenerate_l180_verified_source_footer_contract() -> dict[str, Any]:
    runtime_route_binding = load("universal_runtime_route_binding_contract")
    source_footer_enforcement = load("universal_source_footer_enforcement_contract")
    source_grounded_response = load("universal_source_grounded_response_receipt")
    citation_verification = load("universal_citation_verification_contract")
    source_labels = ("S1", "S2", "S3")

    def stage_row(stage: str) -> dict[str, Any]:
        return {
            "stage_hash": stable_hash(f"reference-l180:stage:{stage}"),
            "policy_hash": stable_hash(f"reference-l180:stage-policy:{stage}"),
            "verifier_hash": stable_hash(f"reference-l180:stage-verifier:{stage}"),
            "enabled": True,
            "footer_reliance_gate": True,
            "fail_closed": True,
            "auditable": True,
            "no_private_payloads": True,
        }

    def field_row(field: str) -> dict[str, Any]:
        return {
            "field_hash": stable_hash(f"reference-l180:field:{field}"),
            "schema_hash": stable_hash(f"reference-l180:field-schema:{field}"),
            "renderer_hash": stable_hash(f"reference-l180:field-renderer:{field}"),
            "field_required": True,
            "user_visible_or_machine_readable": True,
            "claim_bound": True,
            "source_bound": True,
            "privacy_safe": True,
        }

    def surface_row(surface: str) -> dict[str, Any]:
        return {
            "surface_hash": stable_hash(f"reference-l180:surface:{surface}"),
            "footer_hash": stable_hash(f"reference-l180:surface-footer:{surface}"),
            "verifier_hash": stable_hash(
                f"reference-l180:surface-verifier:{surface}"
            ),
            "exact_footer_required": True,
            "citation_markers_preserved": True,
            "source_rows_preserved": True,
            "claim_rows_preserved": True,
            "copy_or_stream_preserved": True,
            "fail_closed": True,
            "no_private_payloads": True,
        }

    def dimension_row(dimension: str) -> dict[str, Any]:
        return {
            "dimension_hash": stable_hash(f"reference-l180:dimension:{dimension}"),
            "verifier_hash": stable_hash(
                f"reference-l180:dimension-verifier:{dimension}"
            ),
            "measured": True,
            "threshold_met": True,
            "claim_level": True,
            "footer_level": True,
            "negative_fixture_covered": True,
        }

    def footer_row(label: str) -> dict[str, Any]:
        return {
            "source_label": label,
            "source_title_hash": stable_hash(f"reference-l180:title:{label}"),
            "creator_or_publisher_hash": stable_hash(
                f"reference-l180:creator:{label}"
            ),
            "source_uri_or_locator_hash": stable_hash(
                f"reference-l180:locator:{label}"
            ),
            "source_type": "web_source",
            "source_content_hash": stable_hash(f"reference-l180:content:{label}"),
            "footer_row_hash": stable_hash(f"reference-l180:footer-row:{label}"),
            "source_identity_hash": stable_hash(
                f"reference-l180:identity:{label}"
            ),
            "locator_health_hash": stable_hash(f"reference-l180:health:{label}"),
            "metadata_fidelity_hash": stable_hash(
                f"reference-l180:metadata:{label}"
            ),
            "claim_support_hash": stable_hash(f"reference-l180:support:{label}"),
            "evidence_span_hash": stable_hash(f"reference-l180:span:{label}"),
            "rendered_footer_hash": stable_hash(f"reference-l180:rendered:{label}"),
            "runtime_route_binding_hash": runtime_route_binding[
                "universal_runtime_route_binding_contract_hash"
            ],
            "verifier_hash": stable_hash(f"reference-l180:verifier:{label}"),
            "claim_hashes": [stable_hash(f"reference-l180:claim:{label}:0")],
            "link_health_status": "live",
            "relevance_score": "0.94",
            "factual_support_score": "0.91",
            "confidence_label": "verified",
            "attribution_reason": "claim_supported_by_materialized_source",
            "license_or_rights_status": "active",
            "settlement_state": "eligible",
            "source_materialized": True,
            "locator_live_or_archived": True,
            "metadata_matches": True,
            "relevant_to_claims": True,
            "factually_supports_claims": True,
            "claim_hashes_bound": True,
            "evidence_span_bound": True,
            "visible_in_footer": True,
            "copy_export_preserved": True,
            "route_binding_matched": True,
            "settlement_state_visible": True,
            "no_private_payloads": True,
        }

    def negative_row(failure: str) -> dict[str, Any]:
        return {
            "fixture_hash": stable_hash(f"reference-l180:negative:{failure}"),
            "verifier_hash": stable_hash(
                f"reference-l180:negative-verifier:{failure}"
            ),
            "expected_reject": True,
            "observed_reject": True,
            "footer_reliance_blocked": True,
            "response_release_blocked": True,
            "copy_export_blocked": True,
            "settlement_held": True,
            "public_status_marked_failed": True,
            "no_private_payloads": True,
        }

    contract_input: dict[str, Any] = {
        "universal_runtime_route_binding_contract": runtime_route_binding,
        "universal_source_footer_enforcement_contract": source_footer_enforcement,
        "universal_source_grounded_response_receipt": source_grounded_response,
        "universal_citation_verification_contract": citation_verification,
        "footer_verification_stage_rows": {
            stage: stage_row(stage)
            for stage in L180_REQUIRED_FOOTER_VERIFICATION_STAGES
        },
        "verified_footer_field_rows": {
            field: field_row(field) for field in L180_REQUIRED_VERIFIED_FOOTER_FIELDS
        },
        "footer_response_surface_rows": {
            surface: surface_row(surface)
            for surface in L180_REQUIRED_FOOTER_RESPONSE_SURFACES
        },
        "support_dimension_rows": {
            dimension: dimension_row(dimension)
            for dimension in L180_REQUIRED_SUPPORT_DIMENSIONS
        },
        "verified_footer_rows": {
            label: footer_row(label) for label in source_labels
        },
        "negative_footer_reliance_rows": {
            failure: negative_row(failure)
            for failure in L180_REQUIRED_NEGATIVE_FOOTER_RELIANCE_FAILURES
        },
        "private_strings": [
            "private reference l180 verified source footer fixture"
        ],
    }
    save("universal_verified_source_footer_contract_input", contract_input)
    contract = make_universal_verified_source_footer_contract(
        contract_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_verified_source_footer_contract", contract)
    return contract


def regenerate_l181_model_capability_coverage_contract() -> dict[str, Any]:
    model_provider_registry = load("universal_model_provider_registry")
    provider_catalog_coverage = load("universal_provider_catalog_coverage_contract")
    runtime_route_binding = load("universal_runtime_route_binding_contract")
    verified_source_footer = load("universal_verified_source_footer_contract")

    declared_routes = {
        str(route.get("route_id")): route
        for route in model_provider_registry.get("declared_model_routes", [])
        if isinstance(route, dict) and route.get("route_id")
    }
    catalog_route_rows = provider_catalog_coverage.get(
        "registry_route_coverage_rows", {}
    )
    route_ids = sorted(
        str(row.get("route_id") or route_id)
        for route_id, row in catalog_route_rows.items()
        if isinstance(row, dict)
        and row.get("l176_route_present") is True
        and row.get("l177_route_enforced") is True
        and row.get("discovered_or_exempted") is True
        and (row.get("route_id") or route_id)
    )

    route_capability_map = {
        "text_chat": "text_generation",
        "reasoning": "reasoning",
        "long_context": "long_context",
        "multimodal_vision": "vision_input",
        "image_generation": "image_generation",
        "audio_speech": "speech_output",
        "video_generation": "video_generation",
        "embedding": "embedding",
        "reranking": "reranking",
        "code_generation": "code_generation",
        "tool_calling_agent": "agentic_tool_use",
        "batch_generation": "batch_async",
        "streaming": "text_generation",
        "fine_tuning": "fine_tuning",
        "retrieval_augmented": "retrieval_grounding",
        "safety_moderation": "safety_moderation",
        "local_inference": "text_generation",
        "gateway_router": "tool_calling",
    }

    def route_class(route_id: str) -> str:
        route = declared_routes.get(route_id, {})
        if isinstance(route, dict) and route.get("model_route_class"):
            return str(route["model_route_class"])
        parts = route_id.split(":")
        return parts[-2] if len(parts) >= 2 else "text_chat"

    def capability_for_route(route_id: str) -> str:
        return route_capability_map.get(route_class(route_id), "text_generation")

    def capability_row(capability: str) -> dict[str, Any]:
        return {
            "capability_hash": stable_hash(f"reference-l181:capability:{capability}"),
            "schema_hash": stable_hash(f"reference-l181:schema:{capability}"),
            "fixture_hash": stable_hash(f"reference-l181:fixture:{capability}"),
            "verifier_hash": stable_hash(f"reference-l181:verifier:{capability}"),
            "catalog_declared": True,
            "registry_supported": True,
            "runtime_route_bound": True,
            "footer_or_abstention_bound": True,
            "settlement_meter_bound": True,
            "negative_fixture_covered": True,
            "fail_closed": True,
            "no_private_payloads": True,
        }

    def modality_row(modality_pair: str) -> dict[str, Any]:
        return {
            "modality_pair_hash": stable_hash(
                f"reference-l181:modality:{modality_pair}"
            ),
            "input_schema_hash": stable_hash(
                f"reference-l181:modality-input:{modality_pair}"
            ),
            "output_schema_hash": stable_hash(
                f"reference-l181:modality-output:{modality_pair}"
            ),
            "verifier_hash": stable_hash(
                f"reference-l181:modality-verifier:{modality_pair}"
            ),
            "input_modalities_bound": True,
            "output_modalities_bound": True,
            "source_boundary_bound": True,
            "attribution_policy_bound": True,
            "privacy_safe": True,
            "fail_closed": True,
        }

    def operation_surface_row(surface: str) -> dict[str, Any]:
        return {
            "surface_hash": stable_hash(f"reference-l181:surface:{surface}"),
            "adapter_hash": stable_hash(
                f"reference-l181:surface-adapter:{surface}"
            ),
            "runtime_verifier_hash": stable_hash(
                f"reference-l181:surface-runtime-verifier:{surface}"
            ),
            "telemetry_span_hash": stable_hash(
                f"reference-l181:surface-telemetry:{surface}"
            ),
            "available_if_declared": True,
            "rdllm_headers_or_metadata_bound": True,
            "stream_or_callback_finalized": True,
            "source_footer_or_abstention_preserved": True,
            "settlement_meter_bound": True,
            "fail_closed": True,
            "no_private_payloads": True,
        }

    def route_capability_row(route_id: str) -> dict[str, Any]:
        route = declared_routes.get(route_id, {})
        catalog_row = catalog_route_rows.get(route_id, {})
        capability = capability_for_route(route_id)
        return {
            "route_id": route_id,
            "capability_name": capability,
            "route_capability_hash": stable_hash(
                f"reference-l181:route-capability:{route_id}"
            ),
            "catalog_entry_hash": str(catalog_row.get("catalog_entry_hash", "")),
            "model_identity_hash": str(
                route.get("model_identity_hash")
                or catalog_row.get("route_identity_hash", "")
            ),
            "runtime_route_binding_hash": runtime_route_binding[
                "universal_runtime_route_binding_contract_hash"
            ],
            "verified_footer_hash": verified_source_footer[
                "universal_verified_source_footer_contract_hash"
            ],
            "capability_fixture_hash": stable_hash(
                f"reference-l181:route-fixture:{route_id}"
            ),
            "verifier_hash": stable_hash(
                f"reference-l181:route-verifier:{route_id}"
            ),
            "catalog_capability_declared": True,
            "registry_route_supported": True,
            "runtime_route_matched": True,
            "capability_fixture_passed": True,
            "modality_pair_covered": True,
            "operation_surface_covered": True,
            "source_footer_or_abstention_enforced": True,
            "settlement_meter_bound": True,
            "no_private_payloads": True,
        }

    def negative_row(failure: str) -> dict[str, Any]:
        return {
            "fixture_hash": stable_hash(f"reference-l181:negative:{failure}"),
            "verifier_hash": stable_hash(
                f"reference-l181:negative-verifier:{failure}"
            ),
            "expected_reject": True,
            "observed_reject": True,
            "capability_invocation_blocked": True,
            "response_release_blocked": True,
            "source_footer_reliance_blocked": True,
            "settlement_held": True,
            "public_status_marked_failed": True,
            "no_private_payloads": True,
        }

    contract_input: dict[str, Any] = {
        "universal_model_provider_registry": model_provider_registry,
        "universal_provider_catalog_coverage_contract": provider_catalog_coverage,
        "universal_runtime_route_binding_contract": runtime_route_binding,
        "universal_verified_source_footer_contract": verified_source_footer,
        "model_capability_rows": {
            capability: capability_row(capability)
            for capability in L181_REQUIRED_MODEL_CAPABILITY_CLASSES
        },
        "modality_pair_rows": {
            modality_pair: modality_row(modality_pair)
            for modality_pair in L181_REQUIRED_MODALITY_PAIRS
        },
        "operation_surface_rows": {
            surface: operation_surface_row(surface)
            for surface in L181_REQUIRED_OPERATION_SURFACES
        },
        "route_capability_rows": {
            route_id: route_capability_row(route_id) for route_id in route_ids
        },
        "negative_capability_rows": {
            failure: negative_row(failure)
            for failure in L181_REQUIRED_NEGATIVE_CAPABILITY_FAILURES
        },
        "private_strings": [
            "private reference l181 model capability coverage fixture"
        ],
    }
    save("universal_model_capability_coverage_contract_input", contract_input)
    contract = make_universal_model_capability_coverage_contract(
        contract_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_model_capability_coverage_contract", contract)
    return contract


def regenerate_l182_live_capability_discovery_contract() -> dict[str, Any]:
    model_capability_coverage = load("universal_model_capability_coverage_contract")
    route_capability_rows = model_capability_coverage.get("route_capability_rows", {})
    route_items = [
        (str(route_id), row)
        for route_id, row in sorted(route_capability_rows.items())
        if isinstance(row, dict)
    ]
    provider_cycle = tuple(L182_REQUIRED_PROVIDER_FAMILIES)
    channel_cycle = tuple(L182_REQUIRED_DISCOVERY_CHANNELS)

    def provider_row(provider_family: str) -> dict[str, Any]:
        return {
            "provider_family_hash": stable_hash(
                f"reference-l182:provider:{provider_family}"
            ),
            "official_catalog_hash": stable_hash(
                f"reference-l182:catalog:{provider_family}"
            ),
            "capability_matrix_hash": stable_hash(
                f"reference-l182:matrix:{provider_family}"
            ),
            "endpoint_matrix_hash": stable_hash(
                f"reference-l182:endpoint:{provider_family}"
            ),
            "lifecycle_feed_hash": stable_hash(
                f"reference-l182:lifecycle:{provider_family}"
            ),
            "official_source_bound": True,
            "model_list_observed": True,
            "endpoints_checked": True,
            "capability_rows_projected": True,
            "lifecycle_checked": True,
            "region_scope_checked": True,
            "stale_or_unknown_models_blocked": True,
            "no_private_payloads": True,
        }

    def channel_row(channel: str) -> dict[str, Any]:
        return {
            "channel_hash": stable_hash(f"reference-l182:channel:{channel}"),
            "snapshot_hash": stable_hash(f"reference-l182:snapshot:{channel}"),
            "verifier_hash": stable_hash(
                f"reference-l182:channel-verifier:{channel}"
            ),
            "observed_at": CREATED_AT,
            "first_party_or_attested": True,
            "freshness_sla_met": True,
            "schema_or_doc_hash_bound": True,
            "replayable_fetch_or_attestation": True,
            "no_private_payloads": True,
        }

    def capability_row(capability: str) -> dict[str, Any]:
        return {
            "capability_hash": stable_hash(
                f"reference-l182:capability:{capability}"
            ),
            "source_document_hash": stable_hash(
                f"reference-l182:source-document:{capability}"
            ),
            "source_url_hash": stable_hash(
                f"reference-l182:source-url:{capability}"
            ),
            "provider_matrix_hash": stable_hash(
                f"reference-l182:provider-matrix:{capability}"
            ),
            "observed_at": CREATED_AT,
            "current_source_observed": True,
            "provider_declares_or_exempts": True,
            "l181_capability_bound": True,
            "source_footer_policy_declared": True,
            "endpoint_compatibility_checked": True,
            "lifecycle_not_deprecated": True,
            "region_or_tenant_scope_declared": True,
            "no_private_payloads": True,
        }

    def route_row(index: int, route_id: str, row: dict[str, Any]) -> dict[str, Any]:
        provider = provider_cycle[index % len(provider_cycle)]
        channel = channel_cycle[index % len(channel_cycle)]
        capability = str(row.get("capability_name") or "text_generation")
        return {
            "route_id": route_id,
            "capability_name": capability,
            "provider_family": provider,
            "source_channel": channel,
            "route_discovery_hash": stable_hash(f"reference-l182:route:{route_id}"),
            "provider_source_hash": stable_hash(
                f"reference-l182:provider-source:{route_id}"
            ),
            "l181_route_capability_hash": str(row.get("route_capability_hash", "")),
            "verifier_hash": stable_hash(
                f"reference-l182:route-verifier:{route_id}"
            ),
            "l181_route_covered": True,
            "provider_capability_observed": True,
            "endpoint_support_observed": True,
            "lifecycle_active_or_blocked": True,
            "region_scope_observed": True,
            "no_private_payloads": True,
        }

    def negative_row(failure: str) -> dict[str, Any]:
        return {
            "fixture_hash": stable_hash(f"reference-l182:negative:{failure}"),
            "verifier_hash": stable_hash(
                f"reference-l182:negative-verifier:{failure}"
            ),
            "expected_reject": True,
            "observed_reject": True,
            "capability_claim_blocked": True,
            "model_invocation_blocked": True,
            "response_release_blocked": True,
            "source_footer_reliance_blocked": True,
            "settlement_held": True,
            "public_status_marked_failed": True,
            "no_private_payloads": True,
        }

    contract_input: dict[str, Any] = {
        "universal_model_capability_coverage_contract": model_capability_coverage,
        "provider_family_rows": {
            provider: provider_row(provider)
            for provider in L182_REQUIRED_PROVIDER_FAMILIES
        },
        "discovery_channel_rows": {
            channel: channel_row(channel)
            for channel in L182_REQUIRED_DISCOVERY_CHANNELS
        },
        "capability_discovery_rows": {
            capability: capability_row(capability)
            for capability in L181_REQUIRED_MODEL_CAPABILITY_CLASSES
        },
        "route_discovery_rows": {
            route_id: route_row(index, route_id, row)
            for index, (route_id, row) in enumerate(route_items)
        },
        "negative_discovery_rows": {
            failure: negative_row(failure)
            for failure in L182_REQUIRED_NEGATIVE_DISCOVERY_FAILURES
        },
        "private_strings": [
            "private reference l182 live capability discovery fixture"
        ],
    }
    save("universal_live_capability_discovery_contract_input", contract_input)
    contract = make_universal_live_capability_discovery_contract(
        contract_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_live_capability_discovery_contract", contract)
    return contract


def regenerate_l183_native_source_annotation_contract() -> dict[str, Any]:
    live_capability_discovery = load("universal_live_capability_discovery_contract")
    verified_source_footer = load("universal_verified_source_footer_contract")
    route_discovery_rows = live_capability_discovery.get("route_discovery_rows", {})
    route_items = [
        (str(route_id), row)
        for route_id, row in sorted(route_discovery_rows.items())
        if isinstance(row, dict)
    ]
    provider_cycle = tuple(L182_REQUIRED_PROVIDER_FAMILIES)
    format_cycle = tuple(L183_REQUIRED_NATIVE_ANNOTATION_FORMATS)

    def annotation_format_row(index: int, annotation_format: str) -> dict[str, Any]:
        return {
            "annotation_format_hash": stable_hash(
                f"reference-l183:annotation-format:{annotation_format}"
            ),
            "parser_hash": stable_hash(f"reference-l183:parser:{annotation_format}"),
            "fixture_hash": stable_hash(f"reference-l183:fixture:{annotation_format}"),
            "provider_family": provider_cycle[index % len(provider_cycle)],
            "source_capability": "retrieval_grounding",
            "official_or_attested_shape_observed": True,
            "parser_replays_native_locator": True,
            "source_identity_extractable": True,
            "claim_span_locator_extractable": True,
            "footer_mapping_defined": True,
            "streaming_or_batch_finalized": True,
            "no_private_payloads": True,
        }

    def normalization_field_row(field: str) -> dict[str, Any]:
        return {
            "field_hash": stable_hash(f"reference-l183:field:{field}"),
            "source_field_hash": stable_hash(f"reference-l183:source-field:{field}"),
            "footer_field_hash": stable_hash(f"reference-l183:footer-field:{field}"),
            "verifier_hash": stable_hash(f"reference-l183:field-verifier:{field}"),
            "field_populated_from_native_annotation": True,
            "field_hash_bound": True,
            "footer_field_bound": True,
            "redacted_if_private": True,
            "no_private_payloads": True,
        }

    def route_annotation_row(index: int, route_id: str, row: dict[str, Any]) -> dict[str, Any]:
        annotation_format = format_cycle[index % len(format_cycle)]
        return {
            "route_id": route_id,
            "provider_family": str(
                row.get("provider_family")
                or provider_cycle[index % len(provider_cycle)]
            ),
            "native_annotation_format": annotation_format,
            "route_annotation_hash": stable_hash(f"reference-l183:route:{route_id}"),
            "native_payload_hash": stable_hash(
                f"reference-l183:native-payload:{route_id}"
            ),
            "rdllm_annotation_hash": stable_hash(
                f"reference-l183:rdllm-annotation:{route_id}"
            ),
            "l182_route_discovery_hash": str(row.get("route_discovery_hash", "")),
            "verifier_hash": stable_hash(
                f"reference-l183:route-verifier:{route_id}"
            ),
            "l182_route_discovered": True,
            "native_annotations_observed_or_abstained": True,
            "all_native_annotations_normalized": True,
            "unsupported_native_annotations_blocked": True,
            "footer_rows_projected": True,
            "no_private_payloads": True,
        }

    def footer_binding_row(route_id: str) -> dict[str, Any]:
        return {
            "route_id": route_id,
            "footer_binding_hash": stable_hash(
                f"reference-l183:footer-binding:{route_id}"
            ),
            "native_annotation_hash": stable_hash(
                f"reference-l183:native-annotation:{route_id}"
            ),
            "footer_row_hash": stable_hash(f"reference-l183:footer-row:{route_id}"),
            "verified_footer_hash": verified_source_footer[
                "universal_verified_source_footer_contract_hash"
            ],
            "claim_span_hash": stable_hash(f"reference-l183:claim-span:{route_id}"),
            "source_identity_hash": stable_hash(f"reference-l183:source-id:{route_id}"),
            "verifier_hash": stable_hash(
                f"reference-l183:footer-verifier:{route_id}"
            ),
            "native_annotation_bound": True,
            "footer_row_visible_or_abstained": True,
            "claim_span_preserved": True,
            "source_locator_preserved": True,
            "metadata_fidelity_checked": True,
            "no_private_payloads": True,
        }

    def negative_row(failure: str) -> dict[str, Any]:
        return {
            "fixture_hash": stable_hash(f"reference-l183:negative:{failure}"),
            "verifier_hash": stable_hash(
                f"reference-l183:negative-verifier:{failure}"
            ),
            "expected_reject": True,
            "observed_reject": True,
            "normalization_blocked": True,
            "response_release_blocked": True,
            "source_footer_reliance_blocked": True,
            "settlement_held": True,
            "public_status_marked_failed": True,
            "no_private_payloads": True,
        }

    contract_input: dict[str, Any] = {
        "universal_live_capability_discovery_contract": live_capability_discovery,
        "universal_verified_source_footer_contract": verified_source_footer,
        "native_annotation_format_rows": {
            annotation_format: annotation_format_row(index, annotation_format)
            for index, annotation_format in enumerate(
                L183_REQUIRED_NATIVE_ANNOTATION_FORMATS
            )
        },
        "normalization_field_rows": {
            field: normalization_field_row(field)
            for field in L183_REQUIRED_NORMALIZED_FOOTER_FIELDS
        },
        "route_annotation_rows": {
            route_id: route_annotation_row(index, route_id, row)
            for index, (route_id, row) in enumerate(route_items)
        },
        "footer_binding_rows": {
            route_id: footer_binding_row(route_id) for route_id, _ in route_items
        },
        "negative_native_annotation_rows": {
            failure: negative_row(failure)
            for failure in L183_REQUIRED_NEGATIVE_NATIVE_ANNOTATION_FAILURES
        },
        "private_strings": [
            "private reference l183 native source annotation fixture"
        ],
    }
    save("universal_native_source_annotation_contract_input", contract_input)
    contract = make_universal_native_source_annotation_contract(
        contract_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_native_source_annotation_contract", contract)
    return contract


def regenerate_l184_claim_evidence_footer_verification_contract() -> dict[str, Any]:
    native_source_annotation = load("universal_native_source_annotation_contract")
    verified_source_footer = load("universal_verified_source_footer_contract")
    route_annotation_rows = native_source_annotation.get("route_annotation_rows", {})
    route_ids = [
        str(route_id)
        for route_id, row in sorted(route_annotation_rows.items())
        if isinstance(row, dict)
    ]
    source_labels = ("S1", "S2", "S3")

    def dimension_row(dimension: str) -> dict[str, Any]:
        return {
            "dimension_hash": stable_hash(f"reference-l184:dimension:{dimension}"),
            "rubric_hash": stable_hash(f"reference-l184:rubric:{dimension}"),
            "verifier_hash": stable_hash(f"reference-l184:verifier:{dimension}"),
            "measured": True,
            "threshold_met": True,
            "claim_level": True,
            "source_level": True,
            "footer_gate": True,
            "negative_fixture_covered": True,
            "no_private_payloads": True,
        }

    def field_row(field: str) -> dict[str, Any]:
        return {
            "field_hash": stable_hash(f"reference-l184:field:{field}"),
            "schema_hash": stable_hash(f"reference-l184:schema:{field}"),
            "renderer_hash": stable_hash(f"reference-l184:renderer:{field}"),
            "field_required": True,
            "claim_bound": True,
            "source_bound": True,
            "footer_visible_or_machine_readable": True,
            "privacy_safe": True,
        }

    def route_claim_evidence_row(route_id: str) -> dict[str, Any]:
        return {
            "route_id": route_id,
            "claim_evidence_hash": stable_hash(
                f"reference-l184:claim-evidence:{route_id}"
            ),
            "native_annotation_hash": stable_hash(
                f"reference-l184:native-annotation:{route_id}"
            ),
            "footer_row_hash": stable_hash(f"reference-l184:footer:{route_id}"),
            "claim_hash": stable_hash(f"reference-l184:claim:{route_id}"),
            "evidence_span_hash": stable_hash(f"reference-l184:evidence:{route_id}"),
            "verifier_hash": stable_hash(
                f"reference-l184:route-verifier:{route_id}"
            ),
            "claim_decomposed": True,
            "citation_ast_parsed": True,
            "cited_content_materialized": True,
            "source_supports_claim": True,
            "intent_purpose_aligned": True,
            "source_suitable": True,
            "answer_source_fidelity_passed": True,
            "footer_row_projected": True,
            "no_private_payloads": True,
        }

    def footer_source_row(label: str) -> dict[str, Any]:
        return {
            "source_label": label,
            "source_identity_hash": stable_hash(f"reference-l184:source-id:{label}"),
            "source_access_hash": stable_hash(
                f"reference-l184:source-access:{label}"
            ),
            "source_title_hash": stable_hash(
                f"reference-l184:source-title:{label}"
            ),
            "source_uri_or_locator_hash": stable_hash(
                f"reference-l184:source-uri:{label}"
            ),
            "claim_hash": stable_hash(f"reference-l184:claim:{label}"),
            "evidence_span_hash": stable_hash(f"reference-l184:evidence:{label}"),
            "intent_purpose_alignment_hash": stable_hash(
                f"reference-l184:ipa:{label}"
            ),
            "source_suitability_hash": stable_hash(
                f"reference-l184:suitability:{label}"
            ),
            "answer_source_fidelity_hash": stable_hash(
                f"reference-l184:fidelity:{label}"
            ),
            "support_verdict_hash": stable_hash(f"reference-l184:support:{label}"),
            "footer_row_hash": stable_hash(
                f"reference-l184:footer-source:{label}"
            ),
            "verifier_hash": stable_hash(
                f"reference-l184:footer-verifier:{label}"
            ),
            "support_verdict": "supported",
            "confidence_label": "verified",
            "source_exists_or_archived": True,
            "access_checked": True,
            "metadata_matches": True,
            "claim_hashes_bound": True,
            "evidence_span_bound": True,
            "support_verdict_verified": True,
            "footer_visible": True,
            "source_suitability_verified": True,
            "answer_source_fidelity_verified": True,
            "no_private_payloads": True,
        }

    def negative_row(failure: str) -> dict[str, Any]:
        return {
            "fixture_hash": stable_hash(f"reference-l184:negative:{failure}"),
            "verifier_hash": stable_hash(
                f"reference-l184:negative-verifier:{failure}"
            ),
            "expected_reject": True,
            "observed_reject": True,
            "response_release_blocked": True,
            "source_footer_reliance_blocked": True,
            "creator_settlement_held": True,
            "public_status_marked_failed": True,
            "no_private_payloads": True,
        }

    contract_input: dict[str, Any] = {
        "universal_native_source_annotation_contract": native_source_annotation,
        "universal_verified_source_footer_contract": verified_source_footer,
        "verification_dimension_rows": {
            dimension: dimension_row(dimension)
            for dimension in L184_REQUIRED_VERIFICATION_DIMENSIONS
        },
        "verified_footer_field_rows": {
            field: field_row(field) for field in L184_REQUIRED_VERIFIED_FOOTER_FIELDS
        },
        "route_claim_evidence_rows": {
            route_id: route_claim_evidence_row(route_id) for route_id in route_ids
        },
        "verified_footer_source_rows": {
            label: footer_source_row(label) for label in source_labels
        },
        "negative_claim_evidence_rows": {
            failure: negative_row(failure)
            for failure in L184_REQUIRED_NEGATIVE_CLAIM_EVIDENCE_FAILURES
        },
        "private_strings": [
            "private reference l184 claim evidence footer verification fixture"
        ],
    }
    save("universal_claim_evidence_footer_verification_contract_input", contract_input)
    contract = make_universal_claim_evidence_footer_verification_contract(
        contract_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_claim_evidence_footer_verification_contract", contract)
    return contract


def regenerate_l185_provider_meter_normalization_contract() -> dict[str, Any]:
    live_capability_discovery = load("universal_live_capability_discovery_contract")
    runtime_route_binding = load("universal_runtime_route_binding_contract")
    claim_evidence_footer = load("universal_claim_evidence_footer_verification_contract")

    route_rows = live_capability_discovery.get("route_discovery_rows", {})
    route_ids = sorted(route_rows)
    provider_cycle = tuple(L182_REQUIRED_PROVIDER_FAMILIES)

    def surface_row(index: int, surface: str) -> dict[str, Any]:
        return {
            "meter_surface_hash": stable_hash(f"reference-l185:surface:{surface}"),
            "schema_hash": stable_hash(f"reference-l185:surface-schema:{surface}"),
            "parser_hash": stable_hash(f"reference-l185:surface-parser:{surface}"),
            "provider_family": provider_cycle[index % len(provider_cycle)],
            "source_document_hash": stable_hash(f"reference-l185:surface-doc:{surface}"),
            "official_or_attested_shape_observed": True,
            "native_usage_present_or_zero_metered": True,
            "input_units_extractable": True,
            "output_units_extractable": True,
            "cache_or_reasoning_units_supported_or_explicitly_absent": True,
            "tool_media_or_batch_units_supported_or_explicitly_absent": True,
            "pricing_snapshot_bound": True,
            "invoice_reconciliation_supported": True,
            "no_private_payloads": True,
        }

    def field_row(field: str) -> dict[str, Any]:
        return {
            "meter_field_hash": stable_hash(f"reference-l185:field:{field}"),
            "native_field_hash": stable_hash(f"reference-l185:native-field:{field}"),
            "settlement_field_hash": stable_hash(
                f"reference-l185:settlement-field:{field}"
            ),
            "verifier_hash": stable_hash(f"reference-l185:field-verifier:{field}"),
            "field_required": True,
            "mapped_from_native_or_declared_zero": True,
            "hash_bound": True,
            "privacy_safe": True,
            "settlement_ledger_projected": True,
            "no_private_payloads": True,
        }

    def route_meter_row(route_id: str) -> dict[str, Any]:
        provider_family = route_rows[route_id].get("provider_family", "unknown")
        runtime_row = runtime_route_binding.get("runtime_route_binding_rows", {}).get(
            route_id, {}
        )
        return {
            "route_id": route_id,
            "provider_family": provider_family,
            "provider_meter_hash": stable_hash(f"reference-l185:meter:{route_id}"),
            "route_binding_hash": runtime_row.get(
                "runtime_binding_hash",
                stable_hash(f"reference-l185:runtime:{route_id}"),
            ),
            "capability_discovery_hash": route_rows[route_id].get(
                "route_discovery_hash",
                stable_hash(f"reference-l185:capability:{route_id}"),
            ),
            "pricing_snapshot_hash": stable_hash(
                f"reference-l185:pricing:{provider_family}"
            ),
            "verifier_hash": stable_hash(f"reference-l185:route-verifier:{route_id}"),
            "l182_route_discovered": True,
            "l179_route_bound": True,
            "provider_usage_observed": True,
            "normalized_meter_projected": True,
            "provider_invoice_row_projected": True,
            "no_double_counting": True,
            "no_private_payloads": True,
        }

    def settlement_row(route_id: str) -> dict[str, Any]:
        return {
            "route_id": route_id,
            "rdllm_settlement_meter_hash": stable_hash(
                f"reference-l185:settlement:{route_id}"
            ),
            "provider_invoice_row_hash": stable_hash(
                f"reference-l185:invoice:{route_id}"
            ),
            "normalized_meter_hash": stable_hash(
                f"reference-l185:normalized:{route_id}"
            ),
            "creator_settlement_hash": stable_hash(
                f"reference-l185:creator-settlement:{route_id}"
            ),
            "claim_evidence_footer_hash": claim_evidence_footer[
                "universal_claim_evidence_footer_verification_contract_hash"
            ],
            "verifier_hash": stable_hash(
                f"reference-l185:settlement-verifier:{route_id}"
            ),
            "l184_footer_bound": True,
            "usage_cost_attribution_bound": True,
            "invoice_reconciled": True,
            "creator_pool_inputs_preserved": True,
            "response_release_gate_bound": True,
            "no_private_payloads": True,
        }

    def negative_row(failure: str) -> dict[str, Any]:
        return {
            "fixture_hash": stable_hash(f"reference-l185:negative:{failure}"),
            "verifier_hash": stable_hash(
                f"reference-l185:negative-verifier:{failure}"
            ),
            "expected_reject": True,
            "observed_reject": True,
            "model_invocation_blocked": True,
            "response_release_blocked": True,
            "creator_settlement_held": True,
            "public_status_marked_failed": True,
            "no_private_payloads": True,
        }

    contract_input: dict[str, Any] = {
        "universal_claim_evidence_footer_verification_contract": claim_evidence_footer,
        "universal_live_capability_discovery_contract": live_capability_discovery,
        "universal_runtime_route_binding_contract": runtime_route_binding,
        "provider_meter_surface_rows": {
            surface: surface_row(index, surface)
            for index, surface in enumerate(L185_REQUIRED_PROVIDER_METER_SURFACES)
        },
        "normalized_meter_field_rows": {
            field: field_row(field) for field in L185_REQUIRED_NORMALIZED_METER_FIELDS
        },
        "route_provider_meter_rows": {
            route_id: route_meter_row(route_id) for route_id in route_ids
        },
        "settlement_meter_rows": {
            route_id: settlement_row(route_id) for route_id in route_ids
        },
        "negative_provider_meter_rows": {
            failure: negative_row(failure)
            for failure in L185_REQUIRED_NEGATIVE_PROVIDER_METER_FAILURES
        },
        "private_strings": [
            "private reference l185 provider meter normalization billing fixture"
        ],
    }
    save("universal_provider_meter_normalization_contract_input", contract_input)
    contract = make_universal_provider_meter_normalization_contract(
        contract_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_provider_meter_normalization_contract", contract)
    return contract


def regenerate_l186_provider_response_state_normalization_contract() -> dict[str, Any]:
    provider_meter_normalization = load("universal_provider_meter_normalization_contract")
    claim_evidence_footer = load("universal_claim_evidence_footer_verification_contract")
    runtime_route_binding = load("universal_runtime_route_binding_contract")
    route_ids = [
        str(route_id)
        for route_id in provider_meter_normalization.get("coverage", {}).get(
            "route_ids", []
        )
        if route_id
    ]
    if not route_ids:
        route_ids = list(runtime_route_binding.get("runtime_route_binding_rows", {}))
    route_ids = sorted(route_ids)
    provider_cycle = tuple(L182_REQUIRED_PROVIDER_FAMILIES)

    def provider_family_for(index: int, route_id: str) -> str:
        row = provider_meter_normalization.get("route_provider_meter_rows", {}).get(
            route_id,
            {},
        )
        if row.get("provider_family"):
            return str(row["provider_family"])
        return provider_cycle[index % len(provider_cycle)]

    def runtime_binding_hash(route_id: str) -> str:
        row = runtime_route_binding.get("runtime_route_binding_rows", {}).get(
            route_id,
            {},
        )
        return str(row.get("runtime_binding_hash") or stable_hash(f"reference-l186:runtime:{route_id}"))

    def provider_meter_hash(route_id: str) -> str:
        row = provider_meter_normalization.get("route_provider_meter_rows", {}).get(
            route_id,
            {},
        )
        return str(row.get("provider_meter_hash") or stable_hash(f"reference-l186:meter:{route_id}"))

    def surface_row(index: int, surface: str) -> dict[str, Any]:
        return {
            "state_surface_hash": stable_hash(f"reference-l186:surface:{surface}"),
            "schema_hash": stable_hash(f"reference-l186:surface-schema:{surface}"),
            "parser_hash": stable_hash(f"reference-l186:surface-parser:{surface}"),
            "provider_family": provider_cycle[index % len(provider_cycle)],
            "source_document_hash": stable_hash(f"reference-l186:surface-doc:{surface}"),
            "official_or_attested_shape_observed": True,
            "finish_or_status_extractable": True,
            "refusal_or_safety_extractable_or_explicitly_absent": True,
            "stream_final_state_extractable": True,
            "tool_or_error_state_extractable_or_explicitly_absent": True,
            "normalization_defined": True,
            "no_private_payloads": True,
        }

    def field_row(field: str) -> dict[str, Any]:
        return {
            "state_field_hash": stable_hash(f"reference-l186:field:{field}"),
            "native_field_hash": stable_hash(f"reference-l186:native-field:{field}"),
            "release_gate_field_hash": stable_hash(
                f"reference-l186:release-field:{field}"
            ),
            "verifier_hash": stable_hash(f"reference-l186:field-verifier:{field}"),
            "field_required": True,
            "mapped_from_native_or_declared_absent": True,
            "hash_bound": True,
            "privacy_safe": True,
            "release_gate_projected": True,
            "no_private_payloads": True,
        }

    def route_response_state_row(index: int, route_id: str) -> dict[str, Any]:
        provider_family = provider_family_for(index, route_id)
        return {
            "route_id": route_id,
            "provider_family": provider_family,
            "response_state_hash": stable_hash(
                f"reference-l186:response-state:{route_id}"
            ),
            "runtime_route_binding_hash": runtime_binding_hash(route_id),
            "provider_meter_hash": provider_meter_hash(route_id),
            "verifier_hash": stable_hash(
                f"reference-l186:route-state-verifier:{route_id}"
            ),
            "normalized_response_state": "complete_supported",
            "l179_route_bound": True,
            "l185_meter_bound": True,
            "native_terminal_state_observed": True,
            "normalized_state_projected": True,
            "unknown_states_fail_closed": True,
            "no_private_payloads": True,
        }

    def release_gate_row(route_id: str) -> dict[str, Any]:
        return {
            "route_id": route_id,
            "response_release_gate_hash": stable_hash(
                f"reference-l186:release-gate:{route_id}"
            ),
            "source_footer_reliance_gate_hash": stable_hash(
                f"reference-l186:footer-gate:{route_id}"
            ),
            "creator_settlement_gate_hash": stable_hash(
                f"reference-l186:settlement-gate:{route_id}"
            ),
            "public_user_status_hash": stable_hash(
                f"reference-l186:user-status:{route_id}"
            ),
            "retry_or_fallback_policy_hash": stable_hash(
                f"reference-l186:retry-policy:{route_id}"
            ),
            "verifier_hash": stable_hash(
                f"reference-l186:release-verifier:{route_id}"
            ),
            "complete_supported_releases": True,
            "blocked_or_filtered_holds_answer_release": True,
            "truncated_or_tool_only_holds_footer_reliance": True,
            "refusal_or_abstention_publicly_labeled": True,
            "settlement_held_when_not_supported": True,
            "no_private_payloads": True,
        }

    def negative_row(failure: str) -> dict[str, Any]:
        return {
            "fixture_hash": stable_hash(f"reference-l186:negative:{failure}"),
            "verifier_hash": stable_hash(
                f"reference-l186:negative-verifier:{failure}"
            ),
            "expected_reject": True,
            "observed_reject": True,
            "response_release_blocked": True,
            "footer_reliance_blocked": True,
            "creator_settlement_held": True,
            "public_status_marked_failed": True,
            "no_private_payloads": True,
        }

    contract_input: dict[str, Any] = {
        "universal_provider_meter_normalization_contract": provider_meter_normalization,
        "universal_claim_evidence_footer_verification_contract": claim_evidence_footer,
        "universal_runtime_route_binding_contract": runtime_route_binding,
        "provider_response_state_surface_rows": {
            surface: surface_row(index, surface)
            for index, surface in enumerate(L186_REQUIRED_PROVIDER_RESPONSE_STATE_SURFACES)
        },
        "normalized_response_state_field_rows": {
            field: field_row(field)
            for field in L186_REQUIRED_NORMALIZED_RESPONSE_STATE_FIELDS
        },
        "route_response_state_rows": {
            route_id: route_response_state_row(index, route_id)
            for index, route_id in enumerate(route_ids)
        },
        "release_gate_rows": {
            route_id: release_gate_row(route_id) for route_id in route_ids
        },
        "negative_response_state_rows": {
            failure: negative_row(failure)
            for failure in L186_REQUIRED_NEGATIVE_RESPONSE_STATE_FAILURES
        },
        "private_strings": [
            "private reference l186 provider response state safety payload fixture"
        ],
    }
    save(
        "universal_provider_response_state_normalization_contract_input",
        contract_input,
    )
    contract = make_universal_provider_response_state_normalization_contract(
        contract_input,
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("universal_provider_response_state_normalization_contract", contract)
    return contract


def regenerate_proof_graph(extra_artifact_names: tuple[str, ...] = ()) -> dict[str, Any]:
    previous = load("proof_dependency_graph")
    names = [(row["name"], row["artifact_type"]) for row in previous["artifacts"]]
    if not any(name == "universal_certification_trust_federation" for name, _ in names):
        names.append(
            (
                "universal_certification_trust_federation",
                "universal_certification_trust_federation",
            )
        )
    for name in extra_artifact_names:
        if not any(existing == name for existing, _ in names):
            names.append((name, name))
    specs = []
    for name, artifact_type in names:
        path = ARTIFACTS / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(path)
        specs.append(f"{name}:{artifact_type}:{path}")
    graph = make_proof_dependency_graph(
        _load_assurance_artifacts(specs),
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("proof_dependency_graph", graph)
    return graph


def regenerate_post_release_proof_graph(
    extra_artifact_names: tuple[str, ...] = (),
) -> dict[str, Any]:
    base = load("proof_dependency_graph")
    names = [(row["name"], row["artifact_type"]) for row in base["artifacts"]]
    for name in (
        "universal_reference_implementation_distribution",
        "universal_live_attribution_proof",
        "universal_foundation_model_release_passport",
        *extra_artifact_names,
    ):
        if not any(existing == name for existing, _ in names):
            names.append((name, name))
    specs = []
    for name, artifact_type in names:
        path = ARTIFACTS / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(path)
        specs.append(f"{name}:{artifact_type}:{path}")
    graph = make_proof_dependency_graph(
        _load_assurance_artifacts(specs),
        issuer=ISSUER,
        created_at=CREATED_AT,
        signing_secret=SIGNING_SECRET,
    )
    save("proof_dependency_graph_post_release", graph)
    return graph


def main() -> int:
    bootstrap_report = bootstrap_certification_report()
    regenerate_core_response_chain(bootstrap_report)
    source_footer_delivery = regenerate_source_footer_delivery()
    certification_report = regenerate_certification_report()
    regenerate_certification_attestation(certification_report)
    regenerate_provider_card(certification_report)
    regenerate_calibrated_attribution_report()
    assurance_bundle = regenerate_assurance_bundle()
    integration_profile = regenerate_integration_profile(assurance_bundle)
    regenerate_discovery_manifest(assurance_bundle, integration_profile)
    regenerate_core_response_chain(certification_report)
    source_footer_delivery = regenerate_source_footer_delivery()
    assurance_bundle = regenerate_assurance_bundle(
        extra_artifact_names=L168_TO_L186_PUBLIC_ARTIFACTS
    )
    integration_profile = regenerate_integration_profile(assurance_bundle)
    regenerate_discovery_manifest(assurance_bundle, integration_profile)
    (
        streaming_attribution_manifest,
        conversation_attribution_ledger,
        agent_tool_attribution_ledger,
    ) = regenerate_streaming_conversation_tool_artifacts()
    regenerate_l82_to_l85_emission_chain()
    regenerate_l104_to_l108_replay_chain()
    regenerate_l157_to_l160()
    regenerate_l161_federation()
    graph = regenerate_proof_graph()
    adoption_pack = regenerate_l162_adoption_pack()
    industry_root = regenerate_l163_industry_root()
    reference_distribution = regenerate_l164_reference_distribution()
    live_attribution_proof = regenerate_l165_live_attribution_proof()
    model_release_passport = regenerate_l166_model_release_passport()
    post_release_graph = regenerate_post_release_proof_graph()
    composite_contract = regenerate_l167_composite_contract()
    provider_binding_matrix = regenerate_l168_provider_binding_matrix()
    provider_conformance_runner_receipt = (
        regenerate_l169_provider_conformance_runner_receipt()
    )
    production_invocation_admission = regenerate_l170_production_invocation_admission()
    source_grounded_response_receipt = (
        regenerate_l171_source_grounded_response_receipt()
    )
    distribution_reliance_passport = regenerate_l172_distribution_reliance_passport()
    adversarial_provenance_quorum = regenerate_l173_adversarial_provenance_quorum()
    procurement_regulatory_reliance_contract = (
        regenerate_l174_procurement_regulatory_reliance_contract()
    )
    provider_onboarding_migration_covenant = (
        regenerate_l175_provider_onboarding_migration_covenant()
    )
    model_provider_registry = regenerate_l176_model_provider_registry()
    source_footer_enforcement_contract = (
        regenerate_l177_source_footer_enforcement_contract()
    )
    provider_catalog_coverage_contract = (
        regenerate_l178_provider_catalog_coverage_contract()
    )
    runtime_route_binding_contract = (
        regenerate_l179_runtime_route_binding_contract()
    )
    verified_source_footer_contract = (
        regenerate_l180_verified_source_footer_contract()
    )
    model_capability_coverage_contract = (
        regenerate_l181_model_capability_coverage_contract()
    )
    live_capability_discovery_contract = (
        regenerate_l182_live_capability_discovery_contract()
    )
    native_source_annotation_contract = (
        regenerate_l183_native_source_annotation_contract()
    )
    claim_evidence_footer_verification_contract = (
        regenerate_l184_claim_evidence_footer_verification_contract()
    )
    provider_meter_normalization_contract = (
        regenerate_l185_provider_meter_normalization_contract()
    )
    provider_response_state_normalization_contract = (
        regenerate_l186_provider_response_state_normalization_contract()
    )
    regenerate_core_response_chain(certification_report)
    source_footer_delivery = regenerate_source_footer_delivery()
    assurance_bundle = regenerate_assurance_bundle(
        extra_artifact_names=L168_TO_L186_PUBLIC_ARTIFACTS
    )
    integration_profile = regenerate_integration_profile(assurance_bundle)
    regenerate_discovery_manifest(assurance_bundle, integration_profile)
    (
        foundation_api_profile,
        client_attribution_enforcement,
        persistent_memory_provenance,
        private_reasoning_attribution,
        post_training_signal_provenance,
    ) = regenerate_l104_to_l108_replay_chain()
    regenerate_l157_to_l160()
    regenerate_l161_federation()
    graph = regenerate_proof_graph(
        extra_artifact_names=L168_TO_L186_PUBLIC_ARTIFACTS
    )
    adoption_pack = regenerate_l162_adoption_pack()
    industry_root = regenerate_l163_industry_root()
    reference_distribution = regenerate_l164_reference_distribution()
    live_attribution_proof = regenerate_l165_live_attribution_proof()
    model_release_passport = regenerate_l166_model_release_passport()
    post_release_graph = regenerate_post_release_proof_graph(
        extra_artifact_names=L168_TO_L186_PUBLIC_ARTIFACTS
    )
    composite_contract = regenerate_l167_composite_contract()
    provider_binding_matrix = regenerate_l168_provider_binding_matrix()
    provider_conformance_runner_receipt = (
        regenerate_l169_provider_conformance_runner_receipt()
    )
    production_invocation_admission = regenerate_l170_production_invocation_admission()
    source_grounded_response_receipt = (
        regenerate_l171_source_grounded_response_receipt()
    )
    distribution_reliance_passport = regenerate_l172_distribution_reliance_passport()
    adversarial_provenance_quorum = regenerate_l173_adversarial_provenance_quorum()
    procurement_regulatory_reliance_contract = (
        regenerate_l174_procurement_regulatory_reliance_contract()
    )
    provider_onboarding_migration_covenant = (
        regenerate_l175_provider_onboarding_migration_covenant()
    )
    model_provider_registry = regenerate_l176_model_provider_registry()
    source_footer_enforcement_contract = (
        regenerate_l177_source_footer_enforcement_contract()
    )
    provider_catalog_coverage_contract = (
        regenerate_l178_provider_catalog_coverage_contract()
    )
    runtime_route_binding_contract = (
        regenerate_l179_runtime_route_binding_contract()
    )
    verified_source_footer_contract = (
        regenerate_l180_verified_source_footer_contract()
    )
    model_capability_coverage_contract = (
        regenerate_l181_model_capability_coverage_contract()
    )
    live_capability_discovery_contract = (
        regenerate_l182_live_capability_discovery_contract()
    )
    native_source_annotation_contract = (
        regenerate_l183_native_source_annotation_contract()
    )
    claim_evidence_footer_verification_contract = (
        regenerate_l184_claim_evidence_footer_verification_contract()
    )
    provider_meter_normalization_contract = (
        regenerate_l185_provider_meter_normalization_contract()
    )
    provider_response_state_normalization_contract = (
        regenerate_l186_provider_response_state_normalization_contract()
    )
    regenerate_core_response_chain(certification_report)
    source_footer_delivery = regenerate_source_footer_delivery()
    assurance_bundle = regenerate_assurance_bundle(
        extra_artifact_names=L168_TO_L186_PUBLIC_ARTIFACTS
    )
    integration_profile = regenerate_integration_profile(assurance_bundle)
    regenerate_discovery_manifest(assurance_bundle, integration_profile)
    (
        streaming_attribution_manifest,
        conversation_attribution_ledger,
        agent_tool_attribution_ledger,
    ) = regenerate_streaming_conversation_tool_artifacts()
    regenerate_l82_to_l85_emission_chain()
    (
        foundation_api_profile,
        client_attribution_enforcement,
        persistent_memory_provenance,
        private_reasoning_attribution,
        post_training_signal_provenance,
    ) = regenerate_l104_to_l108_replay_chain()
    regenerate_l157_to_l160()
    regenerate_l161_federation()
    graph = regenerate_proof_graph(
        extra_artifact_names=L168_TO_L186_PUBLIC_ARTIFACTS
    )
    adoption_pack = regenerate_l162_adoption_pack()
    industry_root = regenerate_l163_industry_root()
    reference_distribution = regenerate_l164_reference_distribution()
    live_attribution_proof = regenerate_l165_live_attribution_proof()
    model_release_passport = regenerate_l166_model_release_passport()
    post_release_graph = regenerate_post_release_proof_graph(
        extra_artifact_names=L168_TO_L186_PUBLIC_ARTIFACTS
    )
    composite_contract = regenerate_l167_composite_contract()
    provider_binding_matrix = regenerate_l168_provider_binding_matrix()
    provider_conformance_runner_receipt = (
        regenerate_l169_provider_conformance_runner_receipt()
    )
    production_invocation_admission = regenerate_l170_production_invocation_admission()
    source_grounded_response_receipt = (
        regenerate_l171_source_grounded_response_receipt()
    )
    distribution_reliance_passport = regenerate_l172_distribution_reliance_passport()
    adversarial_provenance_quorum = regenerate_l173_adversarial_provenance_quorum()
    procurement_regulatory_reliance_contract = (
        regenerate_l174_procurement_regulatory_reliance_contract()
    )
    provider_onboarding_migration_covenant = (
        regenerate_l175_provider_onboarding_migration_covenant()
    )
    model_provider_registry = regenerate_l176_model_provider_registry()
    source_footer_enforcement_contract = (
        regenerate_l177_source_footer_enforcement_contract()
    )
    provider_catalog_coverage_contract = (
        regenerate_l178_provider_catalog_coverage_contract()
    )
    runtime_route_binding_contract = (
        regenerate_l179_runtime_route_binding_contract()
    )
    verified_source_footer_contract = (
        regenerate_l180_verified_source_footer_contract()
    )
    model_capability_coverage_contract = (
        regenerate_l181_model_capability_coverage_contract()
    )
    live_capability_discovery_contract = (
        regenerate_l182_live_capability_discovery_contract()
    )
    native_source_annotation_contract = (
        regenerate_l183_native_source_annotation_contract()
    )
    claim_evidence_footer_verification_contract = (
        regenerate_l184_claim_evidence_footer_verification_contract()
    )
    provider_meter_normalization_contract = (
        regenerate_l185_provider_meter_normalization_contract()
    )
    provider_response_state_normalization_contract = (
        regenerate_l186_provider_response_state_normalization_contract()
    )
    graph = regenerate_proof_graph(
        extra_artifact_names=L168_TO_L186_PUBLIC_ARTIFACTS
    )
    post_release_graph = regenerate_post_release_proof_graph(
        extra_artifact_names=L168_TO_L186_PUBLIC_ARTIFACTS
    )
    assurance_bundle = regenerate_assurance_bundle(
        extra_artifact_names=L168_TO_L186_PUBLIC_ARTIFACTS
    )
    integration_profile = regenerate_integration_profile(assurance_bundle)
    regenerate_discovery_manifest(assurance_bundle, integration_profile)
    sync_packaged_reference_artifacts()
    print(
        json.dumps(
            {
                "certification_report": certification_report["report_hash"],
                "assurance_bundle": load("assurance_bundle")["bundle_hash"],
                "integration_profile": load("integration_profile")["profile_hash"],
                "discovery_manifest": load("discovery_manifest")["manifest_hash"],
                "source_footer_delivery": source_footer_delivery[
                    "source_footer_delivery_hash"
                ],
                "streaming_attribution_manifest": streaming_attribution_manifest[
                    "streaming_manifest_hash"
                ],
                "conversation_attribution_ledger": conversation_attribution_ledger[
                    "conversation_ledger_hash"
                ],
                "agent_tool_attribution_ledger": agent_tool_attribution_ledger[
                    "tool_ledger_hash"
                ],
                "universal_certification_trust_federation": load(
                    "universal_certification_trust_federation"
                )["universal_certification_trust_federation_hash"],
                "foundation_api_profile": foundation_api_profile[
                    "foundation_profile_hash"
                ],
                "client_attribution_enforcement": client_attribution_enforcement[
                    "client_enforcement_hash"
                ],
                "persistent_memory_provenance": persistent_memory_provenance[
                    "persistent_memory_provenance_hash"
                ],
                "private_reasoning_attribution": private_reasoning_attribution[
                    "private_reasoning_attribution_hash"
                ],
                "post_training_signal_provenance": post_training_signal_provenance[
                    "post_training_signal_provenance_hash"
                ],
                "universal_foundation_provider_adoption_pack": adoption_pack[
                    "universal_foundation_provider_adoption_pack_hash"
                ],
                "universal_industry_adoption_root": industry_root[
                    "universal_industry_adoption_root_hash"
                ],
                "universal_reference_implementation_distribution": (
                    reference_distribution[
                        "universal_reference_implementation_distribution_hash"
                    ]
                ),
                "universal_live_attribution_proof": (
                    live_attribution_proof["universal_live_attribution_proof_hash"]
                ),
                "universal_foundation_model_release_passport": (
                    model_release_passport[
                        "universal_foundation_model_release_passport_hash"
                    ]
                ),
                "universal_composite_rdllm_contract": (
                    composite_contract["universal_composite_rdllm_contract_hash"]
                ),
                "universal_foundation_provider_binding_matrix": (
                    provider_binding_matrix[
                        "universal_foundation_provider_binding_matrix_hash"
                    ]
                ),
                "universal_provider_conformance_runner_receipt": (
                    provider_conformance_runner_receipt[
                        "universal_provider_conformance_runner_receipt_hash"
                    ]
                ),
                "universal_production_invocation_admission": (
                    production_invocation_admission[
                        "universal_production_invocation_admission_hash"
                    ]
                ),
                "universal_source_grounded_response_receipt": (
                    source_grounded_response_receipt[
                        "universal_source_grounded_response_receipt_hash"
                    ]
                ),
                "universal_distribution_reliance_passport": (
                    distribution_reliance_passport[
                        "universal_distribution_reliance_passport_hash"
                    ]
                ),
                "universal_adversarial_provenance_quorum": (
                    adversarial_provenance_quorum[
                        "universal_adversarial_provenance_quorum_hash"
                    ]
                ),
                "universal_procurement_regulatory_reliance_contract": (
                    procurement_regulatory_reliance_contract[
                        "universal_procurement_regulatory_reliance_contract_hash"
                    ]
                ),
                "universal_provider_onboarding_migration_covenant": (
                    provider_onboarding_migration_covenant[
                        "universal_provider_onboarding_migration_covenant_hash"
                    ]
                ),
                "universal_model_provider_registry": (
                    model_provider_registry[
                        "universal_model_provider_registry_hash"
                    ]
                ),
                "universal_source_footer_enforcement_contract": (
                    source_footer_enforcement_contract[
                        "universal_source_footer_enforcement_contract_hash"
                    ]
                ),
                "universal_provider_catalog_coverage_contract": (
                    provider_catalog_coverage_contract[
                        "universal_provider_catalog_coverage_contract_hash"
                    ]
                ),
                "universal_runtime_route_binding_contract": (
                    runtime_route_binding_contract[
                        "universal_runtime_route_binding_contract_hash"
                    ]
                ),
                "universal_verified_source_footer_contract": (
                    verified_source_footer_contract[
                        "universal_verified_source_footer_contract_hash"
                    ]
                ),
                "universal_model_capability_coverage_contract": (
                    model_capability_coverage_contract[
                        "universal_model_capability_coverage_contract_hash"
                    ]
                ),
                "universal_live_capability_discovery_contract": (
                    live_capability_discovery_contract[
                        "universal_live_capability_discovery_contract_hash"
                    ]
                ),
                "universal_native_source_annotation_contract": (
                    native_source_annotation_contract[
                        "universal_native_source_annotation_contract_hash"
                    ]
                ),
                "universal_claim_evidence_footer_verification_contract": (
                    claim_evidence_footer_verification_contract[
                        "universal_claim_evidence_footer_verification_contract_hash"
                    ]
                ),
                "universal_provider_meter_normalization_contract": (
                    provider_meter_normalization_contract[
                        "universal_provider_meter_normalization_contract_hash"
                    ]
                ),
                "universal_provider_response_state_normalization_contract": (
                    provider_response_state_normalization_contract[
                        "universal_provider_response_state_normalization_contract_hash"
                    ]
                ),
                "proof_dependency_graph": graph["graph_hash"],
                "proof_graph_status": graph["summary"]["status"],
                "proof_dependency_graph_post_release": (
                    post_release_graph["graph_hash"]
                ),
                "post_release_proof_graph_status": post_release_graph["summary"][
                    "status"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return (
        0
        if graph["summary"]["status"] == "ready"
        and post_release_graph["summary"]["status"] == "ready"
        and provider_binding_matrix["summary"]["status"] == "ready"
        and provider_conformance_runner_receipt["summary"]["status"] == "ready"
        and production_invocation_admission["summary"]["status"] == "ready"
        and source_grounded_response_receipt["summary"]["status"] == "ready"
        and distribution_reliance_passport["summary"]["status"] == "ready"
        and adversarial_provenance_quorum["summary"]["status"] == "ready"
        and procurement_regulatory_reliance_contract["summary"]["status"] == "ready"
        and provider_onboarding_migration_covenant["summary"]["status"] == "ready"
        and model_provider_registry["summary"]["status"] == "ready"
        and source_footer_enforcement_contract["summary"]["status"] == "ready"
        and provider_catalog_coverage_contract["summary"]["status"] == "ready"
        and runtime_route_binding_contract["summary"]["status"] == "ready"
        and verified_source_footer_contract["summary"]["status"] == "ready"
        and live_capability_discovery_contract["summary"]["status"] == "ready"
        and native_source_annotation_contract["summary"]["status"] == "ready"
        and claim_evidence_footer_verification_contract["summary"]["status"] == "ready"
        and provider_meter_normalization_contract["summary"]["status"] == "ready"
        and provider_response_state_normalization_contract["summary"]["status"]
        == "ready"
        and source_footer_delivery["summary"]["status"] == "ready"
        and streaming_attribution_manifest["summary"]["status"] == "committed"
        and conversation_attribution_ledger["summary"]["status"] == "continued"
        and agent_tool_attribution_ledger["summary"]["status"] == "bound"
        and foundation_api_profile["summary"]["status"] == "ready"
        and client_attribution_enforcement["summary"]["status"] == "ready"
        and persistent_memory_provenance["summary"]["status"] == "ready"
        and private_reasoning_attribution["summary"]["status"] == "ready"
        and post_training_signal_provenance["summary"]["status"] == "ready"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
