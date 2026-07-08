"""Runtime federation handshakes for cross-provider RDLLM attribution."""

from __future__ import annotations

from typing import Any

from rdllm.assurance import validate_assurance_bundle_shape
from rdllm.attribution_exchange import verify_attribution_exchange_manifest
from rdllm.conformance_vectors import verify_conformance_vector_pack
from rdllm.discovery_manifest import verify_discovery_manifest
from rdllm.integration_profile import SCHEMA_MAP, verify_integration_profile
from rdllm.license_contract import verify_creator_license_contract_public
from rdllm.provider_card import validate_provider_card_shape
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.response_envelope import verify_response_envelope
from rdllm.semantic_text_attribution import validate_semantic_text_attribution_report_shape

FEDERATION_HANDSHAKE_VERSION = "rdllm-federation-handshake/v1"

DECLARED_HASH_FIELDS = (
    "trust_registry_hash",
    "publication_witness_hash",
    "publication_monitor_hash",
    "handshake_hash",
    "vector_pack_hash",
    "exchange_hash",
    "manifest_hash",
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

REQUIRED_HANDSHAKE_ARTIFACTS = (
    "provider_attribution_card",
    "certification_report",
    "integration_profile",
    "discovery_manifest",
    "response_envelope",
    "assurance_bundle",
    "semantic_text_attribution_report",
    "creator_license_contract",
    "attribution_exchange",
    "conformance_vector_pack",
)

RUNTIME_REQUIRED_HEADERS = (
    "RDLLM-Handshake-Hash",
    "RDLLM-Certification-Level",
    "RDLLM-Exchange-Hash",
    "RDLLM-Vector-Pack-Hash",
    "RDLLM-License-Contract-Hash",
    "RDLLM-Signature",
)

HANDSHAKE_SCHEMA_MAP = {
    **SCHEMA_MAP,
    "attribution_exchange": "docs/schemas/attribution_exchange.schema.json",
    "conformance_vector_pack": "docs/schemas/conformance_vector_pack.schema.json",
    "federation_handshake": "docs/schemas/federation_handshake.schema.json",
}


def _hashable_handshake(handshake: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in handshake.items()
        if key not in {"handshake_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in artifact.items()
        if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
    }


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


def _level_number(level: str) -> int:
    try:
        return int(level.rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


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
        "schema": HANDSHAKE_SCHEMA_MAP.get(name, ""),
        "required": required,
        "declared_hash": _declared_hash(payload),
        "payload_hash": hash_payload(payload),
        "hash_reproducible": _artifact_hash_is_reproducible(payload),
    }
    entry["entry_hash"] = hash_payload(entry)
    return entry


def _artifact_catalog(
    *,
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    integration_profile: dict[str, Any],
    discovery_manifest: dict[str, Any],
    response_envelope: dict[str, Any],
    assurance_bundle: dict[str, Any],
    semantic_text_attribution_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
    attribution_exchange: dict[str, Any],
    conformance_vector_pack: dict[str, Any],
    training_summary: dict[str, Any] | None,
    provenance_evaluation_report: dict[str, Any] | None,
    counterfactual_report: dict[str, Any] | None,
    media_attribution_report: dict[str, Any] | None,
    model_signal_report: dict[str, Any] | None,
    rights_remediation_report: dict[str, Any] | None,
    source_confidence_report: dict[str, Any] | None,
    citation_footer_contract: dict[str, Any] | None,
    private_audit_challenge: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    artifacts: list[tuple[str, str, dict[str, Any], bool]] = [
        ("provider_attribution_card", "rdllm-provider-attribution-card/v1", provider_card, True),
        ("certification_report", "rdllm-certification/v1", certification_report, True),
        ("integration_profile", "rdllm-integration-profile/v1", integration_profile, True),
        ("discovery_manifest", "rdllm-discovery-manifest/v1", discovery_manifest, True),
        ("response_envelope", "rdllm-response-envelope/v1", response_envelope, True),
        ("assurance_bundle", "rdllm-assurance-bundle/v1", assurance_bundle, True),
        (
            "semantic_text_attribution_report",
            "rdllm-semantic-text-attribution/v1",
            semantic_text_attribution_report,
            True,
        ),
        (
            "creator_license_contract",
            "rdllm-creator-license-contract/v1",
            creator_license_contract,
            True,
        ),
        ("attribution_exchange", "rdllm-attribution-exchange/v1", attribution_exchange, True),
        (
            "conformance_vector_pack",
            "rdllm-conformance-vector-pack/v1",
            conformance_vector_pack,
            True,
        ),
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
    if rights_remediation_report is not None:
        artifacts.append(
            (
                "rights_remediation_report",
                "rdllm-rights-remediation/v1",
                rights_remediation_report,
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
    return [
        _artifact_entry(name, artifact_type, payload, required=required)
        for name, artifact_type, payload, required in artifacts
    ]


def _runtime_contract(
    *,
    minimum_certification_level: str,
    integration_profile: dict[str, Any],
    discovery_manifest: dict[str, Any],
) -> dict[str, Any]:
    discovery = discovery_manifest.get("discovery", {})
    return {
        "profile": "rdllm-runtime-federation-contract/v1",
        "well_known_path": discovery.get(
            "federation_handshake_path",
            "/.well-known/rdllm/federation-handshake.json",
        ),
        "api_endpoint": "/v1/rdllm/federation-handshake",
        "required_response_format": "rdllm-response-envelope/v1",
        "minimum_accepted_certification_level": minimum_certification_level,
        "required_headers": list(RUNTIME_REQUIRED_HEADERS),
        "required_artifacts": list(REQUIRED_HANDSHAKE_ARTIFACTS),
        "required_verifier_commands": [
            "verify-federation-handshake",
            "verify-conformance-vector-pack",
            "verify-attribution-exchange",
            "verify-creator-license-contract",
            "verify-response-envelope",
        ],
        "relay_obligations": [
            "preserve_upstream_declared_hashes",
            "preserve_public_source_footer_rows",
            "relay_escrow_obligations_without_relabeling_owner",
            "relay_creator_license_contract_terms_without_rewriting_hashes",
            "append_downstream_provider_identity_without_rewriting_upstream_hashes",
            "emit_new_exchange_and_handshake_hashes_after_material_proof_changes",
        ],
        "downgrade_policy": {
            "reject_lower_certification_level": True,
            "reject_missing_required_artifacts": True,
            "reject_missing_attribution_exchange": True,
            "reject_missing_conformance_vector_pack": True,
            "reject_missing_creator_license_contract": True,
            "reject_missing_source_footer_relay": True,
            "reject_missing_escrow_relay": True,
            "reject_unsigned_material_handshake_changes": True,
        },
        "provider_declared_headers": integration_profile.get("api_contract", {}).get(
            "required_headers", []
        ),
    }


def _request_contract(
    *,
    requester: str,
    requester_model_id: str,
    requester_model_version: str,
    minimum_certification_level: str,
) -> dict[str, Any]:
    return {
        "requester": {
            "id": requester,
            "model_id": requester_model_id,
            "model_version": requester_model_version,
        },
        "minimum_certification_level": minimum_certification_level,
        "accepted_protocol_versions": {
            "federation_handshake": FEDERATION_HANDSHAKE_VERSION,
            "attribution_exchange": "rdllm-attribution-exchange/v1",
            "conformance_vector_pack": "rdllm-conformance-vector-pack/v1",
            "creator_license_contract": "rdllm-creator-license-contract/v1",
            "response_envelope": "rdllm-response-envelope/v1",
        },
        "required_capabilities": [
            "source_footer_relay",
            "escrow_relay",
            "offline_verification",
            "creator_license_relay",
            "downgrade_rejection",
            "hash_bound_artifact_publication",
        ],
    }


def make_federation_handshake(
    *,
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    integration_profile: dict[str, Any],
    discovery_manifest: dict[str, Any],
    response_envelope: dict[str, Any],
    assurance_bundle: dict[str, Any],
    semantic_text_attribution_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
    attribution_exchange: dict[str, Any],
    conformance_vector_pack: dict[str, Any],
    training_summary: dict[str, Any] | None = None,
    provenance_evaluation_report: dict[str, Any] | None = None,
    counterfactual_report: dict[str, Any] | None = None,
    media_attribution_report: dict[str, Any] | None = None,
    model_signal_report: dict[str, Any] | None = None,
    rights_remediation_report: dict[str, Any] | None = None,
    source_confidence_report: dict[str, Any] | None = None,
    citation_footer_contract: dict[str, Any] | None = None,
    private_audit_challenge: dict[str, Any] | None = None,
    requester: str = "requester:unspecified",
    requester_model_id: str = "model:unspecified",
    requester_model_version: str = "unknown",
    minimum_certification_level: str = "RDLLM-L32",
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed runtime handshake for RDLLM federation."""

    provider = provider_card.get("provider", {})
    certification_summary = certification_report.get("summary", {})
    artifacts = _artifact_catalog(
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
    )
    artifact_names = {entry["name"] for entry in artifacts}
    runtime_contract = _runtime_contract(
        minimum_certification_level=minimum_certification_level,
        integration_profile=integration_profile,
        discovery_manifest=discovery_manifest,
    )
    highest_level = str(certification_summary.get("highest_level", ""))
    level_ok = (
        certification_summary.get("status") == "passed"
        and _level_number(highest_level) >= _level_number(minimum_certification_level)
    )
    public_surfaces = provider_card.get("public_disclosure_surfaces", {})
    supported_channels = provider_card.get("supported_evidence_channels", {})
    profile_verifiers = integration_profile.get("verifier_contract", {}).get(
        "reference_cli_commands", []
    )
    profile_endpoints = {
        endpoint.get("name", "")
        for endpoint in integration_profile.get("api_contract", {}).get("endpoints", [])
    }
    provider_headers = set(runtime_contract["provider_declared_headers"])
    exchange_interop = attribution_exchange.get("interoperability", {})
    contract_policy = runtime_contract["downgrade_policy"]
    readiness_checks = {
        "all_required_artifacts_bound": set(REQUIRED_HANDSHAKE_ARTIFACTS).issubset(
            artifact_names
        ),
        "certification_meets_requested_minimum": level_ok,
        "provider_declares_federation_surface": public_surfaces.get(
            "federation_handshake"
        )
        is True,
        "provider_declares_runtime_federation_channel": supported_channels.get(
            "runtime_federation_handshake"
        )
        is True,
        "integration_declares_federation_schema": "federation_handshake"
        in integration_profile.get("schemas", {}),
        "integration_declares_federation_endpoint": "federation_handshake"
        in profile_endpoints,
        "integration_declares_federation_verifier": "verify-federation-handshake"
        in profile_verifiers,
        "discovery_declares_federation_path": bool(
            discovery_manifest.get("discovery", {}).get("federation_handshake_path")
        ),
        "response_envelope_verified": response_envelope.get("summary", {}).get("status")
        == "verified",
        "attribution_exchange_ready": attribution_exchange.get("summary", {}).get(
            "cross_provider_ready"
        )
        is True,
        "creator_license_contract_verified": not verify_creator_license_contract_public(
            creator_license_contract,
            signing_secret=signing_secret,
        ),
        "conformance_vector_pack_ready": conformance_vector_pack.get("summary", {}).get(
            "status"
        )
        == "ready",
        "source_footer_relay_enabled": exchange_interop.get(
            "source_footer_relay_supported"
        )
        is True,
        "escrow_relay_enabled": exchange_interop.get("escrow_relay_supported") is True,
        "runtime_headers_declared": set(RUNTIME_REQUIRED_HEADERS).issubset(
            provider_headers
        ),
        "downgrade_protection_enabled": all(contract_policy.values()),
        "artifact_hashes_reproducible": all(
            entry.get("hash_reproducible") is True for entry in artifacts
        ),
        "privacy_promises_preserved": (
            attribution_exchange.get("privacy", {}).get("prompt_text_disclosed")
            is False
            and attribution_exchange.get("privacy", {}).get("source_text_disclosed")
            is False
            and conformance_vector_pack.get("privacy", {}).get("prompt_text_disclosed")
            is False
            and conformance_vector_pack.get("privacy", {}).get("source_text_disclosed")
            is False
        ),
    }
    accepted = all(readiness_checks.values())
    handshake = {
        "handshake_version": FEDERATION_HANDSHAKE_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "request": _request_contract(
            requester=requester,
            requester_model_id=requester_model_id,
            requester_model_version=requester_model_version,
            minimum_certification_level=minimum_certification_level,
        ),
        "acceptance": {
            "accepted": accepted,
            "provider": {
                "id": provider.get("id", "provider:unspecified"),
                "model_id": provider.get("model_id", "model:unspecified"),
                "model_version": provider.get("model_version", "unknown"),
            },
            "provider_highest_certification_level": highest_level,
            "negotiated_certification_level": (
                minimum_certification_level if level_ok else highest_level
            ),
            "rejection_reason": "" if accepted else "runtime federation readiness checks failed",
        },
        "runtime_contract": runtime_contract,
        "artifact_bindings": artifacts,
        "schemas": HANDSHAKE_SCHEMA_MAP,
        "commitments": {
            "artifact_binding_root": hash_payload(artifacts),
            "runtime_contract_hash": hash_payload(runtime_contract),
            "schema_root": hash_payload(HANDSHAKE_SCHEMA_MAP),
            "request_hash": hash_payload(
                _request_contract(
                    requester=requester,
                    requester_model_id=requester_model_id,
                    requester_model_version=requester_model_version,
                    minimum_certification_level=minimum_certification_level,
                )
            ),
            "provider_card_hash": provider_card.get("card_hash", ""),
            "certification_report_hash": certification_report.get("report_hash", ""),
            "integration_profile_hash": integration_profile.get("profile_hash", ""),
            "discovery_manifest_hash": discovery_manifest.get("manifest_hash", ""),
            "response_envelope_hash": response_envelope.get("envelope_hash", ""),
            "assurance_bundle_hash": assurance_bundle.get("bundle_hash", ""),
            "semantic_text_attribution_report_hash": semantic_text_attribution_report.get(
                "report_hash", ""
            ),
            "creator_license_contract_hash": creator_license_contract.get(
                "contract_hash", ""
            ),
            "attribution_exchange_hash": attribution_exchange.get("exchange_hash", ""),
            "conformance_vector_pack_hash": conformance_vector_pack.get(
                "vector_pack_hash", ""
            ),
            "private_audit_challenge_hash": (
                private_audit_challenge or {}
            ).get("report_hash", ""),
        },
        "readiness_checks": readiness_checks,
        "summary": {
            "status": "ready" if accepted else "failed",
            "target_certification_level": "RDLLM-L33",
            "minimum_requested_level": minimum_certification_level,
            "negotiated_level": minimum_certification_level if level_ok else highest_level,
            "provider_highest_level": highest_level,
            "artifact_count": len(artifacts),
            "required_artifact_count": len(REQUIRED_HANDSHAKE_ARTIFACTS),
            "runtime_header_count": len(RUNTIME_REQUIRED_HEADERS),
            "schema_count": len(HANDSHAKE_SCHEMA_MAP),
            "offline_verification_supported": True,
            "downgrade_protection": all(contract_policy.values()),
        },
        "privacy": {
            "artifact_payloads_embedded": False,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "matched_text_disclosed": False,
            "hidden_state_disclosed": False,
            "handshake_uses_hashes_headers_and_contract_metadata": True,
        },
    }
    handshake["handshake_hash"] = hash_payload(_hashable_handshake(handshake))
    handshake["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_handshake(handshake), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return handshake


def validate_federation_handshake_shape(handshake: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "handshake_version",
        "issuer",
        "created_at",
        "request",
        "acceptance",
        "runtime_contract",
        "artifact_bindings",
        "schemas",
        "commitments",
        "readiness_checks",
        "summary",
        "privacy",
        "handshake_hash",
        "signature",
    )
    for key in required:
        if key not in handshake:
            errors.append(f"missing federation handshake field: {key}")
    if errors:
        return errors
    if handshake.get("handshake_version") != FEDERATION_HANDSHAKE_VERSION:
        errors.append("federation handshake version is unsupported")
    names = {entry.get("name", "") for entry in handshake.get("artifact_bindings", [])}
    for name in REQUIRED_HANDSHAKE_ARTIFACTS:
        if name not in names:
            errors.append(f"missing handshake artifact binding: {name}")
    if "federation_handshake" not in handshake.get("schemas", {}):
        errors.append("missing federation handshake schema")
    for header in RUNTIME_REQUIRED_HEADERS:
        if header not in handshake.get("runtime_contract", {}).get(
            "required_headers", []
        ):
            errors.append(f"missing runtime handshake header: {header}")
    for entry in handshake.get("artifact_bindings", []):
        for key in (
            "name",
            "artifact_type",
            "schema",
            "required",
            "declared_hash",
            "payload_hash",
            "hash_reproducible",
            "entry_hash",
        ):
            if key not in entry:
                errors.append(f"missing handshake artifact field: {key}")
    return errors


def verify_federation_handshake(
    handshake: dict[str, Any],
    *,
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    integration_profile: dict[str, Any],
    discovery_manifest: dict[str, Any],
    response_envelope: dict[str, Any],
    assurance_bundle: dict[str, Any],
    semantic_text_attribution_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
    attribution_exchange: dict[str, Any],
    conformance_vector_pack: dict[str, Any],
    training_summary: dict[str, Any] | None = None,
    provenance_evaluation_report: dict[str, Any] | None = None,
    counterfactual_report: dict[str, Any] | None = None,
    media_attribution_report: dict[str, Any] | None = None,
    model_signal_report: dict[str, Any] | None = None,
    rights_remediation_report: dict[str, Any] | None = None,
    source_confidence_report: dict[str, Any] | None = None,
    citation_footer_contract: dict[str, Any] | None = None,
    private_audit_challenge: dict[str, Any] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a runtime federation handshake against public RDLLM artifacts."""

    errors = validate_federation_handshake_shape(handshake)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_handshake(handshake))
    if expected_hash != handshake.get("handshake_hash"):
        errors.append("federation handshake hash is not reproducible")

    errors.extend(
        f"provider card: {error}" for error in validate_provider_card_shape(provider_card)
    )
    errors.extend(
        f"integration profile: {error}"
        for error in verify_integration_profile(
            integration_profile,
            provider_card=provider_card,
            certification_report=certification_report,
            response_envelope=response_envelope,
            assurance_bundle=(
                assurance_bundle
                if integration_profile.get("bound_artifacts", {}).get(
                    "assurance_bundle_hash"
                )
                else None
            ),
            signing_secret=signing_secret,
        )
    )
    errors.extend(
        f"response envelope: {error}"
        for error in verify_response_envelope(
            response_envelope,
            signing_secret=signing_secret,
        )
    )
    errors.extend(
        f"assurance bundle: {error}"
        for error in validate_assurance_bundle_shape(assurance_bundle)
    )
    errors.extend(
        f"semantic text attribution: {error}"
        for error in validate_semantic_text_attribution_report_shape(
            semantic_text_attribution_report
        )
    )
    errors.extend(
        f"creator license contract: {error}"
        for error in verify_creator_license_contract_public(
            creator_license_contract,
            signing_secret=signing_secret,
        )
    )
    errors.extend(
        f"discovery manifest: {error}"
        for error in verify_discovery_manifest(
            discovery_manifest,
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
            rights_remediation_report=rights_remediation_report,
            semantic_text_attribution_report=semantic_text_attribution_report,
            creator_license_contract=creator_license_contract,
            source_confidence_report=source_confidence_report,
            citation_footer_contract=citation_footer_contract,
            private_audit_challenge=private_audit_challenge,
            strict_artifact_catalog=False,
            signing_secret=signing_secret,
        )
    )
    errors.extend(
        f"attribution exchange: {error}"
        for error in verify_attribution_exchange_manifest(
            attribution_exchange,
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
            signing_secret=signing_secret,
        )
    )
    errors.extend(
        f"conformance vector pack: {error}"
        for error in verify_conformance_vector_pack(
            conformance_vector_pack,
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
            signing_secret=signing_secret,
        )
    )

    request = handshake.get("request", {})
    requester = request.get("requester", {})
    expected = make_federation_handshake(
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
        requester=str(requester.get("id", "requester:unspecified")),
        requester_model_id=str(requester.get("model_id", "model:unspecified")),
        requester_model_version=str(requester.get("model_version", "unknown")),
        minimum_certification_level=str(
            request.get("minimum_certification_level", "RDLLM-L32")
        ),
        issuer=handshake.get("issuer", DEFAULT_ISSUER),
        created_at=handshake.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "request",
        "acceptance",
        "runtime_contract",
        "artifact_bindings",
        "schemas",
        "commitments",
        "readiness_checks",
        "summary",
        "privacy",
    ):
        if expected.get(key) != handshake.get(key):
            errors.append(f"federation handshake {key} does not match artifacts")
    if expected.get("handshake_hash") != handshake.get("handshake_hash"):
        errors.append("federation handshake hash does not match artifacts")

    if handshake.get("summary", {}).get("status") != "ready":
        errors.append("federation handshake status is not ready")
    if handshake.get("acceptance", {}).get("accepted") is not True:
        errors.append("federation handshake was not accepted")
    for check, passed in handshake.get("readiness_checks", {}).items():
        if passed is not True:
            errors.append(f"federation handshake readiness check failed: {check}")
    if handshake.get("summary", {}).get("downgrade_protection") is not True:
        errors.append("federation handshake downgrade protection is not enabled")
    if (
        handshake.get("privacy", {}).get(
            "handshake_uses_hashes_headers_and_contract_metadata"
        )
        is not True
    ):
        errors.append("federation handshake must use hashes, headers, and metadata")

    handshake_json = canonical_json(handshake)
    for field in ("prompt", "output", "source_text", "matched_text", "hidden_state"):
        if f'"{field}"' in handshake_json:
            errors.append(f"federation handshake discloses private {field} field")

    signature = handshake.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_handshake(handshake), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("federation handshake is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("federation handshake signature is invalid")

    return errors
