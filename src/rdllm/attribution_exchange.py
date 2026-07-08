"""Cross-provider attribution exchange manifests for RDLLM proofs."""

from __future__ import annotations

from typing import Any

from rdllm.assurance import validate_assurance_bundle_shape
from rdllm.discovery_manifest import verify_discovery_manifest
from rdllm.integration_profile import SCHEMA_MAP, verify_integration_profile
from rdllm.license_contract import (
    validate_creator_license_contract_shape,
    verify_creator_license_contract_public,
)
from rdllm.provider_card import validate_provider_card_shape
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.response_envelope import verify_response_envelope
from rdllm.semantic_text_attribution import validate_semantic_text_attribution_report_shape

ATTRIBUTION_EXCHANGE_VERSION = "rdllm-attribution-exchange/v1"

DECLARED_HASH_FIELDS = (
    "trust_registry_hash",
    "publication_witness_hash",
    "publication_monitor_hash",
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

REQUIRED_EXCHANGE_ARTIFACTS = (
    "provider_attribution_card",
    "certification_report",
    "integration_profile",
    "discovery_manifest",
    "response_envelope",
    "assurance_bundle",
    "semantic_text_attribution_report",
    "creator_license_contract",
)

EXCHANGE_SCHEMA_MAP = {
    **SCHEMA_MAP,
    "attribution_exchange": "docs/schemas/attribution_exchange.schema.json",
}


def _hashable_exchange(exchange: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in exchange.items()
        if key not in {"exchange_hash", "signature"}
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


def _catalog_paths(discovery_manifest: dict[str, Any]) -> dict[str, str]:
    paths = dict(discovery_manifest.get("discovery", {}))
    for entry in discovery_manifest.get("artifact_catalog", []):
        name = str(entry.get("name", ""))
        path = str(entry.get("well_known_path", ""))
        if name and path:
            paths[f"{name}_path"] = path
    return paths


def _artifact_entry(
    *,
    name: str,
    artifact_type: str,
    payload: dict[str, Any],
    discovery_paths: dict[str, str],
    required: bool,
) -> dict[str, Any]:
    schema = EXCHANGE_SCHEMA_MAP.get(name, "")
    well_known_path = discovery_paths.get(f"{name}_path", "")
    entry = {
        "name": name,
        "artifact_type": artifact_type,
        "schema": schema,
        "well_known_path": well_known_path,
        "required": required,
        "portable": True,
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
    source_confidence_report: dict[str, Any] | None = None,
    citation_footer_contract: dict[str, Any] | None = None,
    private_audit_challenge: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    discovery_paths = _catalog_paths(discovery_manifest)
    artifacts = [
        (
            "provider_attribution_card",
            "rdllm-provider-attribution-card/v1",
            provider_card,
        ),
        ("certification_report", "rdllm-certification/v1", certification_report),
        (
            "integration_profile",
            "rdllm-integration-profile/v1",
            integration_profile,
        ),
        (
            "discovery_manifest",
            "rdllm-discovery-manifest/v1",
            discovery_manifest,
        ),
        ("response_envelope", "rdllm-response-envelope/v1", response_envelope),
        ("assurance_bundle", "rdllm-assurance-bundle/v1", assurance_bundle),
        (
            "semantic_text_attribution_report",
            "rdllm-semantic-text-attribution/v1",
            semantic_text_attribution_report,
        ),
        (
            "creator_license_contract",
            "rdllm-creator-license-contract/v1",
            creator_license_contract,
        ),
    ]
    if source_confidence_report is not None:
        artifacts.append(
            (
                "source_confidence_report",
                "rdllm-source-confidence-report/v1",
                source_confidence_report,
            )
        )
    if citation_footer_contract is not None:
        artifacts.append(
            (
                "citation_footer_contract",
                "rdllm-citation-footer-contract/v1",
                citation_footer_contract,
            )
        )
    if private_audit_challenge is not None:
        artifacts.append(
            (
                "private_audit_challenge",
                "rdllm-private-audit-challenge/v1",
                private_audit_challenge,
            )
        )
    return [
        _artifact_entry(
            name=name,
            artifact_type=artifact_type,
            payload=payload,
            discovery_paths=discovery_paths,
            required=True,
        )
        for name, artifact_type, payload in artifacts
    ]


def _public_source_footers(
    semantic_text_attribution_report: dict[str, Any],
) -> list[dict[str, Any]]:
    footers: list[dict[str, Any]] = []
    for footer in semantic_text_attribution_report.get("source_footers", []):
        public_sources = []
        for source in footer.get("sources", []):
            public_sources.append(
                {
                    "label": source.get("label", ""),
                    "creator_id": source.get("creator_id", ""),
                    "work_id": source.get("work_id", ""),
                    "title": source.get("title", ""),
                    "source_uri": source.get("source_uri", ""),
                    "chunk_hash_prefix": source.get("chunk_hash_prefix", ""),
                    "score": source.get("score", 0.0),
                    "decision": source.get("decision", ""),
                }
            )
        footers.append(
            {
                "input_id": footer.get("input_id", ""),
                "footer_status": footer.get("footer_status", ""),
                "footer_text_hash": footer.get("footer_text_hash", ""),
                "sources": public_sources,
            }
        )
    return footers


def _license_terms_cover_public_footers(
    *,
    creator_license_contract: dict[str, Any],
    source_footers: list[dict[str, Any]],
) -> bool:
    terms = {
        str(term.get("work_id", "")): term
        for term in creator_license_contract.get("terms", [])
    }
    for footer in source_footers:
        for source in footer.get("sources", []):
            work_id = str(source.get("work_id", ""))
            if not work_id:
                return False
            term = terms.get(work_id)
            if not term:
                return False
            if term.get("consent_status") != "active" or term.get("revoked") is True:
                return False
            if "generation" not in set(term.get("allowed_uses", [])):
                return False
            if term.get("requires_attribution") is not True:
                return False
            if term.get("requires_royalty") is not True:
                return False
    return True


def _verification_matrix(
    *,
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    integration_profile: dict[str, Any],
    discovery_manifest: dict[str, Any],
    response_envelope: dict[str, Any],
    assurance_bundle: dict[str, Any],
    semantic_text_attribution_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
    source_footers: list[dict[str, Any]],
    imported_artifacts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    certification_summary = certification_report.get("summary", {})
    semantic_summary = semantic_text_attribution_report.get("summary", {})
    assurance_types = set(assurance_bundle.get("summary", {}).get("artifact_types", []))
    rows = [
        {
            "check": "provider_card_declares_exchange_surface",
            "artifact": "provider_attribution_card",
            "passed": provider_card.get("public_disclosure_surfaces", {}).get(
                "attribution_exchange"
            )
            is True,
        },
        {
            "check": "integration_profile_declares_exchange_schema",
            "artifact": "integration_profile",
            "passed": "attribution_exchange" in integration_profile.get("schemas", {}),
        },
        {
            "check": "integration_profile_declares_exchange_verifier",
            "artifact": "integration_profile",
            "passed": "verify-attribution-exchange"
            in integration_profile.get("verifier_contract", {}).get(
                "reference_cli_commands", []
            ),
        },
        {
            "check": "discovery_manifest_declares_exchange_path",
            "artifact": "discovery_manifest",
            "passed": bool(
                discovery_manifest.get("discovery", {}).get(
                    "attribution_exchange_path", ""
                )
            ),
        },
        {
            "check": "certification_level_at_least_l30",
            "artifact": "certification_report",
            "passed": (
                certification_summary.get("status") == "passed"
                and _level_number(str(certification_summary.get("highest_level", "")))
                >= 30
            ),
        },
        {
            "check": "response_envelope_verified",
            "artifact": "response_envelope",
            "passed": response_envelope.get("summary", {}).get("status") == "verified",
        },
        {
            "check": "assurance_bundle_covers_public_provider_artifacts",
            "artifact": "assurance_bundle",
            "passed": {
                "response_envelope",
                "integration_profile",
                "provider_attribution_card",
                "certification_report",
                "creator_license_contract",
            }.issubset(assurance_types),
        },
        {
            "check": "creator_license_contract_publicly_verifies",
            "artifact": "creator_license_contract",
            "passed": not validate_creator_license_contract_shape(
                creator_license_contract
            ),
        },
        {
            "check": "creator_license_terms_cover_public_footer_sources",
            "artifact": "creator_license_contract",
            "passed": _license_terms_cover_public_footers(
                creator_license_contract=creator_license_contract,
                source_footers=source_footers,
            ),
        },
        {
            "check": "semantic_text_source_footers_present",
            "artifact": "semantic_text_attribution_report",
            "passed": int(semantic_summary.get("source_footer_count", 0) or 0) > 0,
        },
        {
            "check": "semantic_text_creator_pool_conserved",
            "artifact": "semantic_text_attribution_report",
            "passed": semantic_summary.get("creator_pool_conserved") is True,
        },
        {
            "check": "all_imported_artifact_hashes_reproducible",
            "artifact": "imported_artifacts",
            "passed": all(entry.get("hash_reproducible") is True for entry in imported_artifacts),
        },
    ]
    for row in rows:
        row["status"] = "ok" if row["passed"] else "failed"
        row["row_hash"] = hash_payload(row)
    return rows


def make_attribution_exchange_manifest(
    *,
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    integration_profile: dict[str, Any],
    discovery_manifest: dict[str, Any],
    response_envelope: dict[str, Any],
    assurance_bundle: dict[str, Any],
    semantic_text_attribution_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
    source_confidence_report: dict[str, Any] | None = None,
    citation_footer_contract: dict[str, Any] | None = None,
    private_audit_challenge: dict[str, Any] | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a portable manifest for relaying attribution across providers."""

    provider = provider_card.get("provider", {})
    imported_artifacts = _artifact_catalog(
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
    )
    source_footers = _public_source_footers(semantic_text_attribution_report)
    matrix = _verification_matrix(
        provider_card=provider_card,
        certification_report=certification_report,
        integration_profile=integration_profile,
        discovery_manifest=discovery_manifest,
        response_envelope=response_envelope,
        assurance_bundle=assurance_bundle,
        semantic_text_attribution_report=semantic_text_attribution_report,
        creator_license_contract=creator_license_contract,
        source_footers=source_footers,
        imported_artifacts=imported_artifacts,
    )
    imported_names = {entry["name"] for entry in imported_artifacts}
    semantic_privacy = semantic_text_attribution_report.get("privacy", {})
    readiness_checks = {
        "all_required_artifacts_imported": set(REQUIRED_EXCHANGE_ARTIFACTS).issubset(
            imported_names
        ),
        "verification_matrix_passed": all(row["passed"] is True for row in matrix),
        "source_footers_portable": bool(source_footers)
        and all(footer.get("footer_text_hash") for footer in source_footers),
        "privacy_promises_preserved": (
            semantic_privacy.get("source_text_disclosed") is False
            and semantic_privacy.get("output_text_disclosed") is False
            and semantic_privacy.get("prompt_text_disclosed") is False
        ),
        "exchange_schema_declared": "attribution_exchange" in EXCHANGE_SCHEMA_MAP,
        "offline_verifier_declared": "verify-attribution-exchange"
        in integration_profile.get("verifier_contract", {}).get(
            "reference_cli_commands", []
        ),
    }
    exchange = {
        "exchange_version": ATTRIBUTION_EXCHANGE_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "provider": {
            "id": provider.get("id", "provider:unspecified"),
            "model_id": provider.get("model_id", "model:unspecified"),
            "model_version": provider.get("model_version", "unknown"),
        },
        "exchange_contract": {
            "profile": "rdllm-cross-provider-attribution-exchange/v1",
            "well_known_path": "/.well-known/rdllm/attribution-exchange.json",
            "minimum_upstream_certification_level": "RDLLM-L30",
            "required_response_format": "rdllm-response-envelope/v1",
            "required_imported_artifacts": list(REQUIRED_EXCHANGE_ARTIFACTS),
            "downstream_relay_rules": [
                "preserve_upstream_declared_hashes",
                "preserve_public_source_footer_rows",
                "append_downstream_provider_identity_without_rewriting_upstream_hashes",
                "route_ambiguous_or_unlicensed_claims_to_escrow",
                "preserve_creator_license_contract_hashes_and_terms",
                "publish_a_new_exchange_hash_after_material_proof_changes",
            ],
        },
        "imported_artifacts": imported_artifacts,
        "public_source_footers": source_footers,
        "schemas": EXCHANGE_SCHEMA_MAP,
        "verification_matrix": matrix,
        "interoperability": {
            "supported_consumers": [
                "model_provider",
                "ai_answer_engine",
                "dataset_marketplace",
                "rights_registry",
                "auditor",
                "regulator",
            ],
            "source_footer_relay_supported": True,
            "hash_only_import_supported": True,
            "escrow_relay_supported": True,
            "creator_license_contract_relay_supported": True,
            "downstream_extension_supported": True,
        },
        "commitments": {
            "imported_artifact_root": hash_payload(imported_artifacts),
            "source_footer_root": hash_payload(source_footers),
            "verification_matrix_root": hash_payload(matrix),
            "schema_root": hash_payload(EXCHANGE_SCHEMA_MAP),
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
            "source_confidence_report_hash": (
                source_confidence_report or {}
            ).get("report_hash", ""),
            "citation_footer_contract_hash": (
                citation_footer_contract or {}
            ).get("contract_hash", ""),
            "private_audit_challenge_hash": (
                private_audit_challenge or {}
            ).get("report_hash", ""),
        },
        "readiness_checks": readiness_checks,
        "summary": {
            "status": "ready" if all(readiness_checks.values()) else "failed",
            "cross_provider_ready": all(readiness_checks.values()),
            "artifact_count": len(imported_artifacts),
            "required_artifact_count": len(REQUIRED_EXCHANGE_ARTIFACTS),
            "source_footer_count": len(source_footers),
            "schema_count": len(EXCHANGE_SCHEMA_MAP),
            "verification_check_count": len(matrix),
            "verification_passed": sum(1 for row in matrix if row["passed"]),
            "minimum_upstream_certification_level": "RDLLM-L30",
            "offline_verification_supported": True,
        },
        "privacy": {
            "artifact_payloads_embedded": False,
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "matched_text_disclosed": False,
            "exchange_uses_hashes_footers_and_contract_metadata": True,
        },
    }
    exchange["exchange_hash"] = hash_payload(_hashable_exchange(exchange))
    exchange["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_exchange(exchange), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return exchange


def validate_attribution_exchange_shape(exchange: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "exchange_version",
        "issuer",
        "created_at",
        "provider",
        "exchange_contract",
        "imported_artifacts",
        "public_source_footers",
        "schemas",
        "verification_matrix",
        "interoperability",
        "commitments",
        "readiness_checks",
        "summary",
        "privacy",
        "exchange_hash",
        "signature",
    )
    for key in required:
        if key not in exchange:
            errors.append(f"missing attribution exchange field: {key}")
    if errors:
        return errors
    if exchange.get("exchange_version") != ATTRIBUTION_EXCHANGE_VERSION:
        errors.append("attribution exchange version is unsupported")
    names = {entry.get("name", "") for entry in exchange.get("imported_artifacts", [])}
    for name in REQUIRED_EXCHANGE_ARTIFACTS:
        if name not in names:
            errors.append(f"missing exchange imported artifact: {name}")
    if "attribution_exchange" not in exchange.get("schemas", {}):
        errors.append("missing attribution exchange schema")
    for entry in exchange.get("imported_artifacts", []):
        for key in (
            "name",
            "artifact_type",
            "schema",
            "well_known_path",
            "required",
            "portable",
            "declared_hash",
            "payload_hash",
            "hash_reproducible",
            "entry_hash",
        ):
            if key not in entry:
                errors.append(f"missing exchange artifact field: {key}")
    return errors


def verify_attribution_exchange_manifest(
    exchange: dict[str, Any],
    *,
    provider_card: dict[str, Any],
    certification_report: dict[str, Any],
    integration_profile: dict[str, Any],
    discovery_manifest: dict[str, Any],
    response_envelope: dict[str, Any],
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
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an attribution exchange against imported public proof artifacts."""

    errors = validate_attribution_exchange_shape(exchange)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_exchange(exchange))
    if expected_hash != exchange.get("exchange_hash"):
        errors.append("attribution exchange hash is not reproducible")

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

    expected = make_attribution_exchange_manifest(
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
        issuer=exchange.get("issuer", DEFAULT_ISSUER),
        created_at=exchange.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "provider",
        "exchange_contract",
        "imported_artifacts",
        "public_source_footers",
        "schemas",
        "verification_matrix",
        "interoperability",
        "commitments",
        "readiness_checks",
        "summary",
        "privacy",
    ):
        if expected.get(key) != exchange.get(key):
            errors.append(f"attribution exchange {key} does not match artifacts")
    if expected.get("exchange_hash") != exchange.get("exchange_hash"):
        errors.append("attribution exchange hash does not match artifacts")

    if exchange.get("summary", {}).get("status") != "ready":
        errors.append("attribution exchange status is not ready")
    for check, passed in exchange.get("readiness_checks", {}).items():
        if passed is not True:
            errors.append(f"attribution exchange readiness check failed: {check}")
    if exchange.get("privacy", {}).get("exchange_uses_hashes_footers_and_contract_metadata") is not True:
        errors.append("attribution exchange must use hashes, footers, and contract metadata")
    exchange_json = canonical_json(exchange)
    for field in ("prompt", "output", "source_text", "matched_text"):
        if f'"{field}"' in exchange_json:
            errors.append(f"attribution exchange discloses private {field} field")

    signature = exchange.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_exchange(exchange), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("attribution exchange is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("attribution exchange signature is invalid")

    return errors
