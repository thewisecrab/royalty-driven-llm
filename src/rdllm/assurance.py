"""Public assurance bundles for RDLLM artifact publication."""

from __future__ import annotations

from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload
from rdllm.transparency import inclusion_proof, merkle_root, verify_inclusion

ASSURANCE_BUNDLE_VERSION = "rdllm-assurance-bundle/v1"

DECLARED_HASH_FIELDS = (
    "trust_registry_hash",
    "publication_witness_hash",
    "publication_monitor_hash",
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
    "universal_attribution_authority_control_plane_hash",
    "universal_confidential_attribution_audit_hash",
    "universal_training_serving_contract_hash",
    "universal_grounded_reuse_contract_hash",
    "universal_citation_verification_contract_hash",
    "universal_context_provenance_bridge_hash",
    "universal_interop_test_kit_hash",
    "universal_adoption_standard_hash",
    "universal_rdllm_passport_hash",
    "universal_content_credential_hash",
    "universal_invocation_witness_hash",
    "universal_invocation_coverage_hash",
    "universal_invocation_guard_hash",
    "universal_foundation_model_contract_hash",
    "universal_composition_settlement_hash",
    "universal_composition_receipt_hash",
    "foundation_model_deployment_attestation_hash",
    "foundation_runtime_router_hash",
    "foundation_runtime_adapter_hash",
    "foundation_provider_conformance_hash",
    "composite_foundation_adapter_hash",
    "graph_hash",
    "report_hash",
    "gate_hash",
    "proof_response_hash",
    "gateway_report_hash",
    "contract_hash",
    "capsule_hash",
    "handshake_hash",
    "card_hash",
    "summary_hash",
    "profile_hash",
    "envelope_hash",
    "trace_hash",
    "statement_hash",
    "receipt_hash",
    "bundle_hash",
    "package_hash",
    "manifest_hash",
    "exchange_hash",
    "vector_pack_hash",
    "event_hash",
)


def _declared_hash(payload: dict[str, Any]) -> str:
    for field in DECLARED_HASH_FIELDS:
        value = payload.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(payload)


def _hashable_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in bundle.items()
        if key not in {"bundle_hash", "signature"}
    }


def artifact_entry(
    name: str,
    artifact_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Create the hash-only publication entry for one artifact."""

    payload_hash = hash_payload(payload)
    declared_hash = _declared_hash(payload)
    leaf = {
        "name": name,
        "artifact_type": artifact_type,
        "declared_hash": declared_hash,
        "payload_hash": payload_hash,
    }
    leaf["leaf_hash"] = hash_payload(leaf)
    return leaf


def make_assurance_bundle(
    artifacts: list[tuple[str, str, dict[str, Any]]],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Publish artifact hashes and inclusion proofs as one signed assurance bundle."""

    entries = [
        artifact_entry(name, artifact_type, payload)
        for name, artifact_type, payload in sorted(artifacts, key=lambda item: item[0])
    ]
    leaves = [entry["leaf_hash"] for entry in entries]
    root = merkle_root(leaves)
    proofs = {
        entry["name"]: inclusion_proof(leaves, index)
        for index, entry in enumerate(entries)
    }
    bundle = {
        "assurance_version": ASSURANCE_BUNDLE_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "publication_profile": {
            "scitt_like_signed_statements": True,
            "rekor_like_merkle_inclusion": True,
            "in_toto_like_attestation_subjects": True,
            "c2pa_like_conformance_assurance": True,
        },
        "summary": {
            "artifact_count": len(entries),
            "artifact_types": sorted({entry["artifact_type"] for entry in entries}),
            "tree_size": len(entries),
            "root": root,
        },
        "artifacts": entries,
        "inclusion_proofs": proofs,
        "privacy": {
            "artifact_payloads_disclosed": False,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "work_text_disclosed": False,
            "public_bundle_uses_hashes_and_inclusion_proofs": True,
        },
    }
    bundle["bundle_hash"] = hash_payload(_hashable_bundle(bundle))
    bundle["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_bundle(bundle), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return bundle


def validate_assurance_bundle_shape(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "assurance_version",
        "issuer",
        "created_at",
        "publication_profile",
        "summary",
        "artifacts",
        "inclusion_proofs",
        "privacy",
        "bundle_hash",
        "signature",
    )
    for key in required:
        if key not in bundle:
            errors.append(f"missing assurance bundle field: {key}")
    if errors:
        return errors
    if bundle.get("assurance_version") != ASSURANCE_BUNDLE_VERSION:
        errors.append("assurance bundle version is unsupported")
    for entry in bundle.get("artifacts", []):
        for key in ("name", "artifact_type", "declared_hash", "payload_hash", "leaf_hash"):
            if key not in entry:
                errors.append(f"missing assurance artifact field: {key}")
    return errors


def verify_assurance_bundle(
    artifacts: list[tuple[str, str, dict[str, Any]]],
    bundle: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an assurance bundle against the provided artifact payloads."""

    errors = validate_assurance_bundle_shape(bundle)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_bundle(bundle))
    if expected_hash != bundle.get("bundle_hash"):
        errors.append("assurance bundle hash is not reproducible")

    expected = make_assurance_bundle(
        artifacts,
        issuer=bundle.get("issuer", DEFAULT_ISSUER),
        created_at=bundle.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "publication_profile",
        "summary",
        "artifacts",
        "inclusion_proofs",
        "privacy",
    ):
        if expected.get(key) != bundle.get(key):
            errors.append(f"assurance bundle {key} does not match recomputed artifacts")
    if expected.get("bundle_hash") != bundle.get("bundle_hash"):
        errors.append("assurance bundle hash does not match artifacts")

    leaves = [entry["leaf_hash"] for entry in bundle.get("artifacts", [])]
    root = merkle_root(leaves)
    if root != bundle.get("summary", {}).get("root"):
        errors.append("assurance bundle Merkle root is not reproducible")
    for entry in bundle.get("artifacts", []):
        proof = bundle.get("inclusion_proofs", {}).get(entry.get("name", ""))
        if not proof:
            errors.append(f"missing assurance inclusion proof for {entry.get('name', '')}")
            continue
        if proof.get("leaf_hash") != entry.get("leaf_hash"):
            errors.append(f"assurance proof leaf hash mismatch for {entry.get('name', '')}")
        if proof.get("root") != root:
            errors.append(f"assurance proof root mismatch for {entry.get('name', '')}")
        if not verify_inclusion(proof):
            errors.append(f"assurance inclusion proof is invalid for {entry.get('name', '')}")

    if bundle.get("privacy", {}).get("public_bundle_uses_hashes_and_inclusion_proofs") is not True:
        errors.append("assurance bundle must use hashes and inclusion proofs")

    signature = bundle.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_bundle(bundle), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("assurance bundle is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("assurance bundle signature is invalid")

    return errors
