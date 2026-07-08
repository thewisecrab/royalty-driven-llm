"""Portable attribution capsules for copied or reposted RDLLM outputs."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from rdllm.federation_handshake import (
    HANDSHAKE_SCHEMA_MAP,
    verify_federation_handshake,
)
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.response_envelope import verify_response_envelope
from rdllm.text import stable_hash

ATTRIBUTION_CAPSULE_VERSION = "rdllm-attribution-capsule/v1"

DECLARED_HASH_FIELDS = (
    "trust_registry_hash",
    "publication_witness_hash",
    "publication_monitor_hash",
    "capsule_hash",
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
    "receipt_hash",
    "event_hash",
)

REQUIRED_CAPSULE_ARTIFACTS = (
    "response_envelope",
    "federation_handshake",
    "attribution_exchange",
    "conformance_vector_pack",
    "provider_attribution_card",
    "certification_report",
    "integration_profile",
    "discovery_manifest",
    "assurance_bundle",
    "semantic_text_attribution_report",
    "creator_license_contract",
)

CAPSULE_RUNTIME_HEADERS = (
    "RDLLM-Capsule-ID",
    "RDLLM-Capsule-Hash",
    "RDLLM-Output-Hash",
    "RDLLM-Handshake-Hash",
    "RDLLM-Signature",
)

CAPSULE_SCHEMA_MAP = {
    **HANDSHAKE_SCHEMA_MAP,
    "attribution_capsule": "docs/schemas/attribution_capsule.schema.json",
}


def _hashable_capsule(capsule: dict[str, Any]) -> dict[str, Any]:
    payload = {
        key: value
        for key, value in capsule.items()
        if key not in {"capsule_hash", "signature"}
    }
    surfaces = payload.get("portable_surfaces")
    if isinstance(surfaces, dict):
        surfaces = deepcopy(surfaces)
        headers = surfaces.get("http_headers")
        if isinstance(headers, dict):
            headers.pop("RDLLM-Capsule-Hash", None)
        payload["portable_surfaces"] = surfaces
    return payload


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
        "schema": CAPSULE_SCHEMA_MAP.get(name, ""),
        "required": required,
        "declared_hash": _declared_hash(payload),
        "payload_hash": hash_payload(payload),
        "hash_reproducible": _artifact_hash_is_reproducible(payload),
    }
    entry["entry_hash"] = hash_payload(entry)
    return entry


def _artifact_catalog(
    *,
    response_envelope: dict[str, Any],
    federation_handshake: dict[str, Any],
    attribution_exchange: dict[str, Any],
    conformance_vector_pack: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    integration_profile: dict[str, Any],
    discovery_manifest: dict[str, Any],
    assurance_bundle: dict[str, Any],
    semantic_text_attribution_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
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
        ("response_envelope", "rdllm-response-envelope/v1", response_envelope, True),
        (
            "federation_handshake",
            "rdllm-federation-handshake/v1",
            federation_handshake,
            True,
        ),
        ("attribution_exchange", "rdllm-attribution-exchange/v1", attribution_exchange, True),
        (
            "conformance_vector_pack",
            "rdllm-conformance-vector-pack/v1",
            conformance_vector_pack,
            True,
        ),
        ("provider_attribution_card", "rdllm-provider-attribution-card/v1", provider_card, True),
        ("certification_report", "rdllm-certification/v1", certification_report, True),
        ("integration_profile", "rdllm-integration-profile/v1", integration_profile, True),
        ("discovery_manifest", "rdllm-discovery-manifest/v1", discovery_manifest, True),
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


def _subject(response_envelope: dict[str, Any]) -> dict[str, Any]:
    response = response_envelope.get("response", {})
    commitments = response_envelope.get("commitments", {})
    return {
        "content_kind": "text",
        "event_id": response.get("event_id", ""),
        "event_hash": response.get("event_hash", ""),
        "rendered_output_hash": response.get(
            "rendered_output_hash", commitments.get("rendered_output_hash", "")
        ),
        "answer_hash": response.get("answer_hash", ""),
        "source_label_root": commitments.get("footer_label_root", ""),
        "claim_span_root": commitments.get("footer_span_root", ""),
        "source_count": response_envelope.get("summary", {}).get("source_count", 0),
        "claim_count": response_envelope.get("summary", {}).get("claim_count", 0),
    }


def _capsule_id(commitments: dict[str, str]) -> str:
    return f"rdllm-cap-{hash_payload(commitments)[:24]}"


def _copy_surfaces(
    *,
    capsule_id: str,
    subject: dict[str, Any],
    discovery_manifest: dict[str, Any],
    federation_handshake: dict[str, Any],
) -> dict[str, Any]:
    capsule_path = discovery_manifest.get("discovery", {}).get(
        "attribution_capsule_path", "/.well-known/rdllm/attribution-capsule.json"
    )
    output_hash = str(subject.get("rendered_output_hash", ""))
    handshake_hash = federation_handshake.get("handshake_hash", "")
    text_footer = (
        f"RDLLM attribution capsule: {capsule_id} | verify {capsule_path} | "
        f"output_hash={output_hash[:16]} | handshake={handshake_hash[:16]}"
    )
    markdown_comment = (
        f"<!-- RDLLM-CAPSULE id={capsule_id} output={output_hash[:16]} "
        f"handshake={handshake_hash[:16]} -->"
    )
    return {
        "capsule_id": capsule_id,
        "text_footer": text_footer,
        "markdown_comment": markdown_comment,
        "http_headers": {
            "RDLLM-Capsule-ID": capsule_id,
            "RDLLM-Capsule-Hash": "",
            "RDLLM-Output-Hash": output_hash,
            "RDLLM-Handshake-Hash": handshake_hash,
            "RDLLM-Signature": "detached",
        },
        "well_known_path": capsule_path,
        "c2pa_assertion": {
            "label": "org.rdllm.attribution.v1",
            "ai_generated": True,
            "content_binding": "rendered_output_hash",
            "provenance_pointer": capsule_path,
            "not_a_tdm_rights_assertion": True,
        },
        "scitt_statement_subject": {
            "name": capsule_id,
            "digest": {"sha256": output_hash},
            "rdllm_handshake_hash": handshake_hash,
        },
        "delivery_contract": {
            "contract_version": "rdllm-delivered-output/v1",
            "body_hash_algorithm": "sha256-utf8",
            "body_hash": output_hash,
            "body_hash_prefix": output_hash[:16],
            "footer_marker_hash": stable_hash(text_footer),
            "markdown_marker_hash": stable_hash(markdown_comment),
            "canonicalization": (
                "normalize CRLF to LF, remove one trailing RDLLM text footer or "
                "markdown capsule marker, trim trailing whitespace, then hash body"
            ),
            "verification_requirement": (
                "a copied output is valid only when the marker is present and the "
                "body before the marker hashes to body_hash"
            ),
        },
    }


def _normalise_copied_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _copied_body_hash_candidates(
    copied_output: str, surfaces: dict[str, Any]
) -> list[str]:
    copied = _normalise_copied_text(copied_output)
    candidates: list[str] = []
    for marker_name in ("text_footer", "markdown_comment"):
        marker = surfaces.get(marker_name, "")
        if not isinstance(marker, str) or not marker:
            continue
        marker = _normalise_copied_text(marker)
        if marker not in copied:
            continue
        body = copied.split(marker, 1)[0].rstrip()
        candidates.append(stable_hash(body))
    return candidates


def make_attribution_capsule(
    *,
    response_envelope: dict[str, Any],
    federation_handshake: dict[str, Any],
    attribution_exchange: dict[str, Any],
    conformance_vector_pack: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    integration_profile: dict[str, Any],
    discovery_manifest: dict[str, Any],
    assurance_bundle: dict[str, Any],
    semantic_text_attribution_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
    training_summary: dict[str, Any] | None = None,
    provenance_evaluation_report: dict[str, Any] | None = None,
    counterfactual_report: dict[str, Any] | None = None,
    media_attribution_report: dict[str, Any] | None = None,
    model_signal_report: dict[str, Any] | None = None,
    rights_remediation_report: dict[str, Any] | None = None,
    source_confidence_report: dict[str, Any] | None = None,
    citation_footer_contract: dict[str, Any] | None = None,
    private_audit_challenge: dict[str, Any] | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a compact attribution capsule that can travel with copied outputs."""

    provider = provider_card.get("provider", {})
    subject = _subject(response_envelope)
    artifacts = _artifact_catalog(
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
    commitments = {
        "subject_hash": hash_payload(subject),
        "artifact_binding_root": hash_payload(artifacts),
        "schema_root": hash_payload(CAPSULE_SCHEMA_MAP),
        "response_envelope_hash": response_envelope.get("envelope_hash", ""),
        "federation_handshake_hash": federation_handshake.get("handshake_hash", ""),
        "attribution_exchange_hash": attribution_exchange.get("exchange_hash", ""),
        "conformance_vector_pack_hash": conformance_vector_pack.get("vector_pack_hash", ""),
        "provider_card_hash": provider_card.get("card_hash", ""),
        "certification_report_hash": certification_report.get("report_hash", ""),
        "integration_profile_hash": integration_profile.get("profile_hash", ""),
        "discovery_manifest_hash": discovery_manifest.get("manifest_hash", ""),
        "assurance_bundle_hash": assurance_bundle.get("bundle_hash", ""),
        "semantic_text_attribution_report_hash": semantic_text_attribution_report.get(
            "report_hash", ""
        ),
        "creator_license_contract_hash": creator_license_contract.get(
            "contract_hash", ""
        ),
        "private_audit_challenge_hash": (
            private_audit_challenge or {}
        ).get("report_hash", ""),
    }
    capsule_id = _capsule_id(commitments)
    copy_surfaces = _copy_surfaces(
        capsule_id=capsule_id,
        subject=subject,
        discovery_manifest=discovery_manifest,
        federation_handshake=federation_handshake,
    )
    public_surfaces = provider_card.get("public_disclosure_surfaces", {})
    profile_verifiers = integration_profile.get("verifier_contract", {}).get(
        "reference_cli_commands", []
    )
    profile_endpoints = {
        endpoint.get("name", "")
        for endpoint in integration_profile.get("api_contract", {}).get("endpoints", [])
    }
    certification_summary = certification_report.get("summary", {})
    readiness_checks = {
        "all_required_artifacts_bound": set(REQUIRED_CAPSULE_ARTIFACTS).issubset(
            {entry["name"] for entry in artifacts}
        ),
        "response_envelope_verified": response_envelope.get("summary", {}).get("status")
        == "verified",
        "federation_handshake_ready": federation_handshake.get("summary", {}).get(
            "status"
        )
        == "ready",
        "attribution_exchange_ready": attribution_exchange.get("summary", {}).get(
            "cross_provider_ready"
        )
        is True,
        "conformance_vector_pack_ready": conformance_vector_pack.get("summary", {}).get(
            "status"
        )
        == "ready",
        "creator_license_contract_bound": creator_license_contract.get(
            "summary", {}
        ).get("status")
        == "ready",
        "certification_reaches_l33": (
            certification_summary.get("status") == "passed"
            and _level_number(str(certification_summary.get("highest_level", ""))) >= 33
        ),
        "provider_declares_capsule_surface": public_surfaces.get("attribution_capsule")
        is True,
        "integration_declares_capsule_schema": "attribution_capsule"
        in integration_profile.get("schemas", {}),
        "integration_declares_capsule_endpoint": "attribution_capsule"
        in profile_endpoints,
        "integration_declares_capsule_verifier": "verify-attribution-capsule"
        in profile_verifiers,
        "discovery_declares_capsule_path": bool(
            discovery_manifest.get("discovery", {}).get("attribution_capsule_path")
        ),
        "copy_marker_present": capsule_id in copy_surfaces["text_footer"]
        and capsule_id in copy_surfaces["markdown_comment"],
        "delivery_body_hash_declared": copy_surfaces["delivery_contract"].get(
            "body_hash"
        )
        == subject.get("rendered_output_hash"),
        "runtime_headers_declared": set(CAPSULE_RUNTIME_HEADERS).issubset(
            set(copy_surfaces.get("http_headers", {}))
        ),
        "c2pa_compatibility_declared": copy_surfaces["c2pa_assertion"][
            "not_a_tdm_rights_assertion"
        ]
        is True,
        "artifact_hashes_reproducible": all(
            entry.get("hash_reproducible") is True for entry in artifacts
        ),
        "privacy_promises_preserved": (
            federation_handshake.get("privacy", {}).get("prompt_text_disclosed")
            is False
            and federation_handshake.get("privacy", {}).get("source_text_disclosed")
            is False
        ),
    }
    capsule = {
        "capsule_version": ATTRIBUTION_CAPSULE_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "provider": {
            "id": provider.get("id", "provider:unspecified"),
            "model_id": provider.get("model_id", "model:unspecified"),
            "model_version": provider.get("model_version", "unknown"),
        },
        "subject": subject,
        "portable_surfaces": copy_surfaces,
        "artifact_bindings": artifacts,
        "schemas": CAPSULE_SCHEMA_MAP,
        "commitments": commitments,
        "readiness_checks": readiness_checks,
        "summary": {
            "status": "ready" if all(readiness_checks.values()) else "failed",
            "target_certification_level": "RDLLM-L34",
            "minimum_upstream_level": "RDLLM-L33",
            "capsule_id": capsule_id,
            "artifact_count": len(artifacts),
            "required_artifact_count": len(REQUIRED_CAPSULE_ARTIFACTS),
            "runtime_header_count": len(CAPSULE_RUNTIME_HEADERS),
            "schema_count": len(CAPSULE_SCHEMA_MAP),
            "copyable": True,
            "content_credentials_compatible": True,
            "offline_verification_supported": True,
        },
        "privacy": {
            "artifact_payloads_embedded": False,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "matched_text_disclosed": False,
            "hidden_state_disclosed": False,
            "capsule_uses_hashes_markers_and_provenance_pointers": True,
        },
    }
    capsule["capsule_hash"] = hash_payload(_hashable_capsule(capsule))
    capsule["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_capsule(capsule), signing_secret)
            if signing_secret
            else ""
        ),
    }
    capsule["portable_surfaces"]["http_headers"]["RDLLM-Capsule-Hash"] = capsule[
        "capsule_hash"
    ]
    return capsule


def validate_attribution_capsule_shape(capsule: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "capsule_version",
        "issuer",
        "created_at",
        "provider",
        "subject",
        "portable_surfaces",
        "artifact_bindings",
        "schemas",
        "commitments",
        "readiness_checks",
        "summary",
        "privacy",
        "capsule_hash",
        "signature",
    )
    for key in required:
        if key not in capsule:
            errors.append(f"missing attribution capsule field: {key}")
    if errors:
        return errors
    if capsule.get("capsule_version") != ATTRIBUTION_CAPSULE_VERSION:
        errors.append("attribution capsule version is unsupported")
    names = {entry.get("name", "") for entry in capsule.get("artifact_bindings", [])}
    for name in REQUIRED_CAPSULE_ARTIFACTS:
        if name not in names:
            errors.append(f"missing attribution capsule artifact binding: {name}")
    if "attribution_capsule" not in capsule.get("schemas", {}):
        errors.append("missing attribution capsule schema")
    surfaces = capsule.get("portable_surfaces", {})
    if not surfaces.get("capsule_id"):
        errors.append("missing attribution capsule id")
    for key in (
        "text_footer",
        "markdown_comment",
        "http_headers",
        "c2pa_assertion",
        "delivery_contract",
    ):
        if key not in surfaces:
            errors.append(f"missing attribution capsule portable surface: {key}")
    delivery_contract = surfaces.get("delivery_contract", {})
    if isinstance(delivery_contract, dict):
        for key in ("contract_version", "body_hash", "footer_marker_hash"):
            if key not in delivery_contract:
                errors.append(f"missing attribution capsule delivery contract field: {key}")
    return errors


def verify_attribution_capsule(
    capsule: dict[str, Any],
    *,
    response_envelope: dict[str, Any],
    federation_handshake: dict[str, Any],
    attribution_exchange: dict[str, Any],
    conformance_vector_pack: dict[str, Any],
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    integration_profile: dict[str, Any],
    discovery_manifest: dict[str, Any],
    assurance_bundle: dict[str, Any],
    semantic_text_attribution_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
    training_summary: dict[str, Any] | None = None,
    provenance_evaluation_report: dict[str, Any] | None = None,
    counterfactual_report: dict[str, Any] | None = None,
    media_attribution_report: dict[str, Any] | None = None,
    model_signal_report: dict[str, Any] | None = None,
    rights_remediation_report: dict[str, Any] | None = None,
    source_confidence_report: dict[str, Any] | None = None,
    citation_footer_contract: dict[str, Any] | None = None,
    private_audit_challenge: dict[str, Any] | None = None,
    copied_output: str | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a portable attribution capsule against the full public proof chain."""

    errors = validate_attribution_capsule_shape(capsule)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_capsule(capsule))
    if expected_hash != capsule.get("capsule_hash"):
        errors.append("attribution capsule hash is not reproducible")

    errors.extend(
        f"response envelope: {error}"
        for error in verify_response_envelope(
            response_envelope,
            signing_secret=signing_secret,
        )
    )
    errors.extend(
        f"federation handshake: {error}"
        for error in verify_federation_handshake(
            federation_handshake,
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
            signing_secret=signing_secret,
        )
    )

    expected = make_attribution_capsule(
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
        training_summary=training_summary,
        provenance_evaluation_report=provenance_evaluation_report,
        counterfactual_report=counterfactual_report,
        media_attribution_report=media_attribution_report,
        model_signal_report=model_signal_report,
        rights_remediation_report=rights_remediation_report,
        source_confidence_report=source_confidence_report,
        citation_footer_contract=citation_footer_contract,
        private_audit_challenge=private_audit_challenge,
        issuer=capsule.get("issuer", DEFAULT_ISSUER),
        created_at=capsule.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "provider",
        "subject",
        "portable_surfaces",
        "artifact_bindings",
        "schemas",
        "commitments",
        "readiness_checks",
        "summary",
        "privacy",
    ):
        if expected.get(key) != capsule.get(key):
            errors.append(f"attribution capsule {key} does not match artifacts")
    if expected.get("capsule_hash") != capsule.get("capsule_hash"):
        errors.append("attribution capsule hash does not match artifacts")

    if capsule.get("summary", {}).get("status") != "ready":
        errors.append("attribution capsule status is not ready")
    for check, passed in capsule.get("readiness_checks", {}).items():
        if passed is not True:
            errors.append(f"attribution capsule readiness check failed: {check}")
    if (
        capsule.get("privacy", {}).get(
            "capsule_uses_hashes_markers_and_provenance_pointers"
        )
        is not True
    ):
        errors.append("attribution capsule must use hashes, markers, and provenance pointers")
    if copied_output is not None:
        rendered = response_envelope.get("response", {}).get("rendered_output", "")
        surfaces = capsule.get("portable_surfaces", {})
        marker = surfaces.get("text_footer", "")
        markdown_marker = surfaces.get("markdown_comment", "")
        delivery_contract = surfaces.get("delivery_contract", {})
        subject_output_hash = capsule.get("subject", {}).get("rendered_output_hash", "")
        if stable_hash(rendered) != capsule.get("subject", {}).get("rendered_output_hash"):
            errors.append("attribution capsule subject output hash is not reproducible")
        if isinstance(delivery_contract, dict):
            if delivery_contract.get("body_hash") != subject_output_hash:
                errors.append("attribution capsule delivery body hash does not match subject")
            if marker and delivery_contract.get("footer_marker_hash") != stable_hash(marker):
                errors.append("attribution capsule footer marker hash is not reproducible")
            if (
                markdown_marker
                and delivery_contract.get("markdown_marker_hash")
                != stable_hash(markdown_marker)
            ):
                errors.append("attribution capsule markdown marker hash is not reproducible")
        copied = _normalise_copied_text(copied_output)
        marker_present = (
            isinstance(marker, str)
            and marker
            and _normalise_copied_text(marker) in copied
        ) or (
            isinstance(markdown_marker, str)
            and markdown_marker
            and _normalise_copied_text(markdown_marker) in copied
        )
        if not marker_present:
            errors.append("copied output is missing attribution capsule marker")
        elif subject_output_hash not in _copied_body_hash_candidates(
            copied_output, surfaces
        ):
            errors.append(
                "copied output body hash does not match attribution capsule subject"
            )

    capsule_json = canonical_json(capsule)
    for field in ("prompt", "output", "source_text", "matched_text", "hidden_state"):
        if f'"{field}"' in capsule_json:
            errors.append(f"attribution capsule discloses private {field} field")

    signature = capsule.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_capsule(capsule), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("attribution capsule is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("attribution capsule signature is invalid")

    return errors
