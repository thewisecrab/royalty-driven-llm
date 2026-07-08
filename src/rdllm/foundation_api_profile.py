"""Foundation-model API attribution profiles.

This layer defines the smallest vendor-neutral response contract a model API
can expose while still making attribution verifiable by generic clients. It
binds the public discovery surface and L103 source-footer delivery receipt to
required response metadata, embedded proof fields, verifier commands, and
failure policy.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.artifact_refs import resolve_artifact_refs
from rdllm.discovery_manifest import validate_discovery_manifest_shape
from rdllm.integration_profile import verify_integration_profile
from rdllm.provider_card import validate_provider_card_shape
from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)
from rdllm.response_envelope import verify_response_envelope
from rdllm.source_footer_delivery import verify_source_footer_delivery_receipt

FOUNDATION_API_PROFILE_VERSION = "rdllm-foundation-attribution-profile/v1"
FOUNDATION_API_PROFILE_SCHEMA = (
    "docs/schemas/foundation_attribution_profile.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L104"
MINIMUM_SOURCE_LEVEL = "RDLLM-L103"

REQUIRED_HEADERS = (
    "RDLLM-Attribution-Level",
    "RDLLM-Foundation-Profile-Hash",
    "RDLLM-Discovery-Manifest-Hash",
    "RDLLM-Response-Envelope-Hash",
    "RDLLM-Source-Footer-Delivery-Hash",
    "RDLLM-Verification-Endpoint",
)

REQUIRED_JSON_FIELDS = (
    "response.rendered_output",
    "response.source_labels",
    "embedded_artifacts.response_envelope",
    "embedded_artifacts.source_footer_delivery",
    "verification.foundation_attribution_profile",
    "verification.verifier_commands",
)

REQUIRED_DISCOVERY_PATHS = (
    "provider_card_path",
    "certification_report_path",
    "integration_profile_path",
    "sample_response_envelope_path",
    "source_footer_delivery_path",
    "foundation_api_profile_path",
)

REQUIRED_INTEGRATION_ENDPOINTS = (
    "generate",
    "verify_response_envelope",
    "source_footer_delivery",
    "source_footer_delivery_manifest",
    "foundation_api_profile",
    "foundation_api_profile_manifest",
)

REQUIRED_PROVIDER_SURFACES = (
    "response_envelope",
    "integration_profile",
    "discovery_manifest",
    "source_footer_delivery",
    "foundation_api_profile",
)

DECLARED_HASH_FIELDS = (
    "foundation_profile_hash",
    "source_footer_delivery_hash",
    "grounded_source_footer_hash",
    "gateway_report_hash",
    "proof_response_hash",
    "envelope_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "report_hash",
    "bundle_hash",
    "summary_hash",
    "receipt_hash",
    "trace_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "raw_model_output",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "raw_license_token",
    "license_server_secret",
    "customer_id",
    "customer_email",
    "invoice_text",
    "payment_method",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "secret",
    "signing_secret",
    "private_key",
}


def load_foundation_api_profile_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for a foundation API profile."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _level_number(level: str) -> int:
    if not level.startswith("RDLLM-L"):
        return -1
    try:
        return int(level.removeprefix("RDLLM-L"))
    except ValueError:
        return -1


def _hashable_profile(profile: dict[str, Any]) -> dict[str, Any]:
    hashable = {
        key: value
        for key, value in profile.items()
        if key not in {"foundation_profile_hash", "signature"}
    }
    metadata = hashable.get("response_metadata_contract")
    if isinstance(metadata, dict):
        header_values = dict(metadata.get("header_values", {}))
        header_values["RDLLM-Foundation-Profile-Hash"] = "<foundation_profile_hash>"
        metadata = dict(metadata)
        metadata["header_values"] = header_values
        hashable["response_metadata_contract"] = metadata
    return hashable


def _hashable_artifact(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    return {
        key: value
        for key, value in artifact.items()
        if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
    }


def _declared_hash(artifact: dict[str, Any] | None) -> str:
    if not artifact:
        return ""
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(_hashable_artifact(artifact))


def _artifact_hash_is_reproducible(artifact: dict[str, Any] | None) -> bool:
    if not artifact:
        return False
    declared = _declared_hash(artifact)
    return bool(declared) and declared == hash_payload(_hashable_artifact(artifact))


def _contains_private_fields(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in PRIVATE_FIELD_NAMES:
                return True
            if _contains_private_fields(child):
                return True
    if isinstance(value, list):
        return any(_contains_private_fields(child) for child in value)
    return False


def _private_strings_absent(profile: dict[str, Any], profile_input: dict[str, Any]) -> bool:
    public_json = canonical_json(profile)
    private_strings = [
        str(item)
        for item in profile_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _artifact_bindings(profile_input: dict[str, Any]) -> dict[str, Any]:
    artifacts = {
        "provider_attribution_card": profile_input.get("provider_card"),
        "certification_report": profile_input.get("certification_report"),
        "integration_profile": profile_input.get("integration_profile"),
        "discovery_manifest": profile_input.get("discovery_manifest"),
        "response_envelope": profile_input.get("response_envelope"),
        "source_footer_delivery": profile_input.get("source_footer_delivery"),
    }
    bindings: dict[str, Any] = {}
    for name, artifact in artifacts.items():
        bindings[f"{name}_hash"] = _declared_hash(artifact)
        bindings[f"{name}_hash_reproducible"] = _artifact_hash_is_reproducible(
            artifact
        )
    delivery = profile_input.get("source_footer_delivery", {})
    bindings["delivered_output_hash"] = delivery.get("delivery_subject", {}).get(
        "delivered_output_hash", ""
    )
    bindings["grounded_source_footer_hash"] = delivery.get("delivery_subject", {}).get(
        "grounded_source_footer_hash", ""
    )
    return bindings


def _response_metadata_contract(
    *,
    discovery_manifest: dict[str, Any],
    source_footer_delivery: dict[str, Any],
    response_envelope: dict[str, Any],
) -> dict[str, Any]:
    discovery = discovery_manifest.get("discovery", {})
    header_values = {
        "RDLLM-Attribution-Level": MINIMUM_SOURCE_LEVEL,
        "RDLLM-Foundation-Profile-Hash": "<foundation_profile_hash>",
        "RDLLM-Discovery-Manifest-Hash": discovery_manifest.get("manifest_hash", ""),
        "RDLLM-Response-Envelope-Hash": response_envelope.get("envelope_hash", ""),
        "RDLLM-Source-Footer-Delivery-Hash": source_footer_delivery.get(
            "source_footer_delivery_hash", ""
        ),
        "RDLLM-Verification-Endpoint": discovery.get(
            "foundation_api_profile_path",
            "/.well-known/rdllm/foundation-attribution-profile.json",
        ),
    }
    return {
        "profile": "rdllm-foundation-api-minimum/2026-06",
        "minimum_certification_level": MINIMUM_SOURCE_LEVEL,
        "required_http_headers": list(REQUIRED_HEADERS),
        "header_values": header_values,
        "required_json_fields": list(REQUIRED_JSON_FIELDS),
        "required_embedded_artifacts": [
            "response_envelope",
            "source_footer_delivery",
        ],
        "streaming_requirement": (
            "final stream message must carry the same response envelope hash and "
            "source footer delivery hash"
        ),
    }


def _verification_contract(discovery_manifest: dict[str, Any]) -> dict[str, Any]:
    discovery = discovery_manifest.get("discovery", {})
    return {
        "well_known_path": discovery.get(
            "foundation_api_profile_path",
            "/.well-known/rdllm/foundation-attribution-profile.json",
        ),
        "client_verifier_flow": [
            "fetch /.well-known/rdllm.json",
            "verify discovery manifest hash and signature",
            "verify integration profile and response envelope",
            "verify source footer delivery receipt",
            "compare response headers to embedded artifact hashes",
            "render answer only if all checks pass",
        ],
        "verifier_commands": [
            "verify-discovery-manifest",
            "verify-integration-profile",
            "verify-response-envelope",
            "verify-source-footer-delivery",
            "verify-foundation-api-profile",
        ],
        "required_failure_modes": [
            "block_display_on_missing_profile",
            "block_display_on_source_footer_delivery_failure",
            "block_display_on_response_hash_drift",
            "label_unattributed_below_minimum_level",
            "route_license_or_reliance_gap_to_escrow",
        ],
        "public_paths": {
            key: discovery.get(key, "")
            for key in REQUIRED_DISCOVERY_PATHS
        },
    }


def _response_subject(
    *,
    provider_card: dict[str, Any],
    response_envelope: dict[str, Any],
    source_footer_delivery: dict[str, Any],
) -> dict[str, Any]:
    provider = provider_card.get("provider", {})
    response = response_envelope.get("response", {})
    delivery_subject = source_footer_delivery.get("delivery_subject", {})
    return {
        "provider": provider.get("id", ""),
        "model_id": provider.get("model_id", ""),
        "model_version": provider.get("model_version", ""),
        "event_id": response.get("event_id", ""),
        "event_hash": response.get("event_hash", ""),
        "rendered_output_hash": response.get("rendered_output_hash", ""),
        "response_envelope_hash": response_envelope.get("envelope_hash", ""),
        "source_footer_delivery_hash": source_footer_delivery.get(
            "source_footer_delivery_hash", ""
        ),
        "delivered_output_hash": delivery_subject.get("delivered_output_hash", ""),
        "grounded_source_footer_hash": delivery_subject.get(
            "grounded_source_footer_hash", ""
        ),
    }


def _discovery_has_required_paths(discovery_manifest: dict[str, Any]) -> bool:
    discovery = discovery_manifest.get("discovery", {})
    return all(bool(discovery.get(path)) for path in REQUIRED_DISCOVERY_PATHS)


def _integration_has_required_endpoints(integration_profile: dict[str, Any]) -> bool:
    names = {
        str(endpoint.get("name", ""))
        for endpoint in integration_profile.get("api_contract", {}).get("endpoints", [])
    }
    return all(name in names for name in REQUIRED_INTEGRATION_ENDPOINTS)


def _provider_declares_required_surfaces(provider_card: dict[str, Any]) -> bool:
    surfaces = provider_card.get("public_disclosure_surfaces", {})
    supported = provider_card.get("supported_evidence_channels", {})
    settlement = provider_card.get("rights_and_settlement", {})
    return (
        all(surfaces.get(name) is True for name in REQUIRED_PROVIDER_SURFACES)
        and supported.get("foundation_api_profile") is True
        and settlement.get("foundation_api_profile_supported") is True
    )


def _checks(
    *,
    profile_input: dict[str, Any],
    artifact_bindings: dict[str, Any],
    response_metadata_contract: dict[str, Any],
    verification_contract: dict[str, Any],
    provider_errors: list[str],
    integration_errors: list[str],
    discovery_errors: list[str],
    response_errors: list[str],
    delivery_errors: list[str],
) -> dict[str, bool]:
    provider_card = profile_input.get("provider_card", {})
    certification_report = profile_input.get("certification_report", {})
    integration_profile = profile_input.get("integration_profile", {})
    discovery_manifest = profile_input.get("discovery_manifest", {})
    response_envelope = profile_input.get("response_envelope", {})
    source_footer_delivery = profile_input.get("source_footer_delivery", {})
    certification_level = str(
        certification_report.get("summary", {}).get("highest_level", "")
    )
    delivery_subject = source_footer_delivery.get("delivery_subject", {})
    public_report = {
        "artifact_bindings": artifact_bindings,
        "response_metadata_contract": response_metadata_contract,
        "verification_contract": verification_contract,
    }
    return {
        "artifact_hashes_reproducible": all(
            bool(value)
            for key, value in artifact_bindings.items()
            if key.endswith("_reproducible")
        ),
        "provider_card_shape_valid": not provider_errors,
        "certification_passed_l103_or_higher": (
            certification_report.get("summary", {}).get("status") == "passed"
            and (
                _level_number(certification_level) >= _level_number(MINIMUM_SOURCE_LEVEL)
                or (
                    _level_number(certification_level) >= 36
                    and profile_input.get("source_footer_delivery", {})
                    .get("summary", {})
                    .get("target_certification_level")
                    == MINIMUM_SOURCE_LEVEL
                )
            )
        ),
        "integration_profile_verified": not integration_errors
        and integration_profile.get("summary", {}).get("status") == "ready",
        "discovery_manifest_ready": not discovery_errors
        and discovery_manifest.get("summary", {}).get("status") == "ready",
        "response_envelope_verified": not response_errors,
        "source_footer_delivery_verified": not delivery_errors
        and source_footer_delivery.get("summary", {}).get("status") == "ready",
        "source_footer_delivery_targets_l103": (
            source_footer_delivery.get("summary", {}).get("target_certification_level")
            == MINIMUM_SOURCE_LEVEL
        ),
        "response_envelope_hash_bound_to_delivery": (
            artifact_bindings.get("response_envelope_hash")
            == source_footer_delivery.get("artifact_bindings", {}).get(
                "response_envelope_hash", ""
            )
        ),
        "delivered_output_hash_bound_to_response_subject": (
            delivery_subject.get("delivered_output_hash", "")
            == artifact_bindings.get("delivered_output_hash", "")
        ),
        "discovery_exposes_required_paths": _discovery_has_required_paths(
            discovery_manifest
        ),
        "integration_exposes_required_endpoints": _integration_has_required_endpoints(
            integration_profile
        ),
        "provider_card_declares_required_surfaces": _provider_declares_required_surfaces(
            provider_card
        ),
        "minimum_response_headers_declared": (
            tuple(response_metadata_contract.get("required_http_headers", ()))
            == REQUIRED_HEADERS
            and all(
                bool(response_metadata_contract.get("header_values", {}).get(header))
                for header in REQUIRED_HEADERS
                if header != "RDLLM-Foundation-Profile-Hash"
            )
        ),
        "minimum_json_fields_declared": (
            tuple(response_metadata_contract.get("required_json_fields", ()))
            == REQUIRED_JSON_FIELDS
        ),
        "verifier_commands_declared": all(
            command in verification_contract.get("verifier_commands", [])
            for command in (
                "verify-discovery-manifest",
                "verify-source-footer-delivery",
                "verify-foundation-api-profile",
            )
        ),
        "private_text_not_disclosed": (
            not _contains_private_fields(public_report)
            and _private_strings_absent(public_report, profile_input)
        ),
    }


def make_foundation_api_profile(
    profile_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    issued_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a foundation-model API attribution profile."""

    profile_input = resolve_artifact_refs(profile_input)
    provider_card = profile_input.get("provider_card", {})
    certification_report = profile_input.get("certification_report", {})
    integration_profile = profile_input.get("integration_profile", {})
    discovery_manifest = profile_input.get("discovery_manifest", {})
    response_envelope = profile_input.get("response_envelope", {})
    source_footer_delivery = profile_input.get("source_footer_delivery", {})
    source_footer_delivery_input = profile_input.get("source_footer_delivery_input", {})

    artifact_bindings = _artifact_bindings(profile_input)
    response_metadata_contract = _response_metadata_contract(
        discovery_manifest=discovery_manifest,
        source_footer_delivery=source_footer_delivery,
        response_envelope=response_envelope,
    )
    verification_contract = _verification_contract(discovery_manifest)
    response_subject = _response_subject(
        provider_card=provider_card,
        response_envelope=response_envelope,
        source_footer_delivery=source_footer_delivery,
    )

    provider_errors = validate_provider_card_shape(provider_card)
    bound_artifacts = integration_profile.get("bound_artifacts", {})
    expected_assurance_bundle = (
        profile_input.get("assurance_bundle")
        if bound_artifacts.get("assurance_bundle_hash")
        else None
    )
    expected_certification_attestation = (
        profile_input.get("certification_attestation")
        if bound_artifacts.get("certification_attestation_hash")
        else None
    )
    integration_errors = verify_integration_profile(
        integration_profile,
        provider_card=provider_card,
        certification_report=certification_report,
        response_envelope=response_envelope,
        assurance_bundle=expected_assurance_bundle,
        certification_attestation=expected_certification_attestation,
        signing_secret=signing_secret,
    )
    discovery_errors = validate_discovery_manifest_shape(discovery_manifest)
    response_errors = verify_response_envelope(
        response_envelope,
        signing_secret=signing_secret,
    )
    delivery_errors = verify_source_footer_delivery_receipt(
        source_footer_delivery,
        source_footer_delivery_input,
        signing_secret=signing_secret,
    )
    checks = _checks(
        profile_input=profile_input,
        artifact_bindings=artifact_bindings,
        response_metadata_contract=response_metadata_contract,
        verification_contract=verification_contract,
        provider_errors=provider_errors,
        integration_errors=integration_errors,
        discovery_errors=discovery_errors,
        response_errors=response_errors,
        delivery_errors=delivery_errors,
    )
    failed = [key for key, value in checks.items() if value is not True]
    status = "ready" if not failed else "needs_review"
    profile = {
        "version": FOUNDATION_API_PROFILE_VERSION,
        "issued_at": issued_at or now_iso(),
        "issuer": issuer,
        "case": {
            "case_id": str(profile_input.get("case_id", "case:foundation-api-profile")),
            "status": status,
        },
        "response_subject": response_subject,
        "artifact_bindings": artifact_bindings,
        "response_metadata_contract": response_metadata_contract,
        "verification_contract": verification_contract,
        "client_failure_policy": {
            "missing_profile": "block_display",
            "missing_or_failed_source_footer_delivery": "block_display",
            "response_hash_drift": "block_display",
            "below_minimum_level": "label_unattributed_or_refuse",
            "license_or_reliance_gap": "route_to_escrow",
        },
        "interoperability_targets": {
            "generic_model_api": True,
            "streaming_api": True,
            "search_answer_engine": True,
            "agent_tool_runtime": True,
            "content_credentials_or_scitt_bridge": True,
            "cross_provider_relay": True,
        },
        "verification_errors": {
            "provider_card_error_count": len(provider_errors),
            "integration_profile_error_count": len(integration_errors),
            "discovery_manifest_error_count": len(discovery_errors),
            "response_envelope_error_count": len(response_errors),
            "source_footer_delivery_error_count": len(delivery_errors),
        },
        "checks": checks,
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "evidence_text_disclosed": False,
            "payment_data_disclosed": False,
            "hash_only_response_commitments": True,
        },
        "schemas": {
            "foundation_api_profile": FOUNDATION_API_PROFILE_SCHEMA,
            "discovery_manifest": "docs/schemas/discovery_manifest.schema.json",
            "integration_profile": "docs/schemas/integration_profile.schema.json",
            "provider_attribution_card": "docs/schemas/provider_attribution_card.schema.json",
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "source_footer_delivery": "docs/schemas/source_footer_delivery.schema.json",
        },
        "summary": {
            "status": status,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_source_level": MINIMUM_SOURCE_LEVEL,
            "required_header_count": len(REQUIRED_HEADERS),
            "required_json_field_count": len(REQUIRED_JSON_FIELDS),
            "verifier_command_count": len(
                verification_contract.get("verifier_commands", [])
            ),
            "failed_check_count": len(failed),
            "foundation_api_ready": not failed,
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    profile["foundation_profile_hash"] = hash_payload(_hashable_profile(profile))
    profile["response_metadata_contract"]["header_values"][
        "RDLLM-Foundation-Profile-Hash"
    ] = profile["foundation_profile_hash"]
    profile["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_profile(profile), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return profile


def validate_foundation_api_profile_shape(profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "version",
        "issued_at",
        "issuer",
        "case",
        "response_subject",
        "artifact_bindings",
        "response_metadata_contract",
        "verification_contract",
        "client_failure_policy",
        "interoperability_targets",
        "verification_errors",
        "checks",
        "privacy",
        "schemas",
        "summary",
        "foundation_profile_hash",
        "signature",
    )
    for key in required:
        if key not in profile:
            errors.append(f"missing foundation API profile field: {key}")
    if errors:
        return errors
    if profile.get("version") != FOUNDATION_API_PROFILE_VERSION:
        errors.append("foundation API profile version is unsupported")
    if profile.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("foundation API profile target level is not RDLLM-L104")
    if "foundation_api_profile" not in profile.get("schemas", {}):
        errors.append("missing foundation API profile schema")
    for header in REQUIRED_HEADERS:
        if header not in profile.get("response_metadata_contract", {}).get(
            "required_http_headers", []
        ):
            errors.append(f"missing foundation API header: {header}")
    for field in REQUIRED_JSON_FIELDS:
        if field not in profile.get("response_metadata_contract", {}).get(
            "required_json_fields", []
        ):
            errors.append(f"missing foundation API json field: {field}")
    return errors


def verify_foundation_api_profile(
    profile: dict[str, Any],
    profile_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a foundation API profile by replaying its public inputs."""

    errors = validate_foundation_api_profile_shape(profile)
    expected = make_foundation_api_profile(
        profile_input,
        issuer=str(profile.get("issuer", DEFAULT_ISSUER)),
        issued_at=str(profile.get("issued_at", "")) or None,
        signing_secret=signing_secret,
    )
    for key in (
        "case",
        "response_subject",
        "artifact_bindings",
        "response_metadata_contract",
        "verification_contract",
        "client_failure_policy",
        "interoperability_targets",
        "verification_errors",
        "checks",
        "privacy",
        "schemas",
        "summary",
    ):
        if profile.get(key) != expected.get(key):
            errors.append(f"foundation API profile {key} mismatch")
    if profile.get("foundation_profile_hash") != expected.get("foundation_profile_hash"):
        errors.append("foundation API profile hash mismatch")
    if profile.get("signature", {}).get("value") != expected.get("signature", {}).get("value"):
        errors.append("foundation API profile signature mismatch")
    if any(value is not True for value in profile.get("checks", {}).values()):
        errors.append("foundation API profile has failing checks")
    return errors
