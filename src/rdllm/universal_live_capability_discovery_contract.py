"""Universal live capability discovery contracts.

The L182 layer closes the gap between fixture-backed capability coverage and the
provider sources that declare those capabilities. L181 proves that declared model
capabilities have RDLLM fixtures. L182 proves those declarations came from fresh
provider capability evidence, endpoint matrices, lifecycle sources, and route
projections before model invocation, source-footer reliance, response release, or
creator settlement can be claimed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.provider_family_registry import CANONICAL_PROVIDER_FAMILIES
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root
from rdllm.universal_model_capability_coverage_contract import (
    REQUIRED_MODEL_CAPABILITY_CLASSES,
)

UNIVERSAL_LIVE_CAPABILITY_DISCOVERY_CONTRACT_VERSION = (
    "rdllm-universal-live-capability-discovery-contract/v1"
)
UNIVERSAL_LIVE_CAPABILITY_DISCOVERY_CONTRACT_SCHEMA = (
    "docs/schemas/universal_live_capability_discovery_contract.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L182"
MINIMUM_MODEL_CAPABILITY_COVERAGE_LEVEL = "RDLLM-L181"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-live-capability-discovery-contract.json"
)

REQUIRED_PROVIDER_FAMILIES = CANONICAL_PROVIDER_FAMILIES

REQUIRED_DISCOVERY_CHANNELS = (
    "official_model_catalog",
    "official_api_reference",
    "endpoint_compatibility_matrix",
    "model_capability_matrix",
    "region_availability_matrix",
    "lifecycle_deprecation_feed",
    "pricing_and_metering_surface",
    "rate_limit_quota_surface",
    "tool_capability_docs",
    "multimodal_capability_docs",
    "batch_async_docs",
    "fine_tuning_docs",
    "embeddings_rerank_docs",
    "local_or_private_manifest",
)

REQUIRED_NEGATIVE_DISCOVERY_FAILURES = (
    "stale_provider_capability_source",
    "provider_model_missing_from_live_catalog",
    "undocumented_capability_declared",
    "endpoint_incompatible_capability_admitted",
    "region_unavailable_model_admitted",
    "deprecated_model_capability_admitted",
    "removed_model_alias_admitted",
    "beta_capability_without_disclosure",
    "pricing_meter_missing_for_capability",
    "rate_limit_surface_missing",
    "tool_capability_without_source_policy",
    "multimodal_capability_without_attribution_boundary",
    "batch_or_async_surface_strips_receipt",
    "fine_tune_capability_without_lineage_policy",
    "embedding_or_rerank_without_attribution_policy",
    "local_runtime_without_capability_manifest",
    "provider_docs_hash_mismatch",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_live_capability_discovery_contract_hash",
    "universal_model_capability_coverage_contract_hash",
    "provider_family_hash",
    "official_catalog_hash",
    "capability_matrix_hash",
    "endpoint_matrix_hash",
    "lifecycle_feed_hash",
    "channel_hash",
    "snapshot_hash",
    "source_document_hash",
    "source_url_hash",
    "provider_matrix_hash",
    "route_discovery_hash",
    "provider_source_hash",
    "l181_route_capability_hash",
    "verifier_hash",
    "fixture_hash",
    "receipt_hash",
    "report_hash",
    "manifest_hash",
    "profile_hash",
    "bundle_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "query_text",
    "answer_text",
    "output_text",
    "raw_model_output",
    "source_text",
    "document_text",
    "full_source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "raw_native_request",
    "raw_native_response",
    "native_response_body",
    "catalog_export_text",
    "provider_doc_text",
    "private_model_weights",
    "private_fine_tune_data",
    "tool_payload",
    "audio_payload",
    "image_payload",
    "video_payload",
    "embedding_vector",
    "customer_id",
    "customer_email",
    "tenant_id",
    "billing_record",
    "api_key",
    "access_token",
    "refresh_token",
    "oauth_token",
    "secret",
    "signing_secret",
    "private_key",
}

PUBLIC_ROW_KEY_ALLOWLISTS = {
    "provider_family_rows": set(REQUIRED_PROVIDER_FAMILIES),
    "discovery_channel_rows": set(REQUIRED_DISCOVERY_CHANNELS),
    "capability_discovery_rows": set(REQUIRED_MODEL_CAPABILITY_CLASSES),
    "negative_discovery_rows": set(REQUIRED_NEGATIVE_DISCOVERY_FAILURES),
}


def load_universal_live_capability_discovery_contract_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L182 live capability discovery contract."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in contract.items()
        if key
        not in {"universal_live_capability_discovery_contract_hash", "signature"}
    }


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


def _summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact, dict):
        return {}
    summary = artifact.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def _artifact_level(artifact: dict[str, Any] | None) -> str:
    summary = _summary(artifact)
    return str(
        summary.get("target_certification_level")
        or summary.get("highest_level")
        or summary.get("attested_highest_level")
        or ""
    )


def _artifact_binding(
    artifact: dict[str, Any] | None,
    *,
    minimum_level: str,
    ready: bool,
) -> dict[str, Any]:
    return {
        "present": isinstance(artifact, dict),
        "artifact_hash": _declared_hash(artifact),
        "payload_hash": hash_payload(_hashable_artifact(artifact)),
        "hash_reproducible": _artifact_hash_is_reproducible(artifact),
        "status": _summary(artifact).get("status", ""),
        "level": _artifact_level(artifact),
        "minimum_level": minimum_level,
        "ready": ready,
    }


def _l181_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("model_capability_coverage_decision", {}) if artifact else {}
    return (
        _summary(artifact).get("status") == "ready"
        and _artifact_level(artifact) == MINIMUM_MODEL_CAPABILITY_COVERAGE_LEVEL
        and decision.get("universal_model_capability_coverage_ready") is True
        and decision.get("model_invocation_allowed") is True
        and decision.get("source_footer_reliance_allowed") is True
    )


def _string(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _bool(value: Any) -> bool:
    return value is True


def _row_map(payload: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    rows = payload.get(key, {})
    if not isinstance(rows, dict):
        return {}
    return {str(name): row for name, row in rows.items() if isinstance(row, dict)}


def _complete_rows(
    rows: dict[str, dict[str, Any]],
    required: tuple[str, ...],
    predicate,
) -> tuple[list[str], list[str]]:
    missing = [name for name in required if name not in rows]
    incomplete = [name for name in required if name in rows and not predicate(rows[name])]
    return missing, incomplete


def _provider_family_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "provider_family_hash",
        "official_catalog_hash",
        "capability_matrix_hash",
        "endpoint_matrix_hash",
        "lifecycle_feed_hash",
    )
    required_bools = (
        "official_source_bound",
        "model_list_observed",
        "endpoints_checked",
        "capability_rows_projected",
        "lifecycle_checked",
        "region_scope_checked",
        "stale_or_unknown_models_blocked",
        "no_private_payloads",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _discovery_channel_row_ready(row: dict[str, Any]) -> bool:
    required_strings = ("channel_hash", "snapshot_hash", "verifier_hash", "observed_at")
    required_bools = (
        "first_party_or_attested",
        "freshness_sla_met",
        "schema_or_doc_hash_bound",
        "replayable_fetch_or_attestation",
        "no_private_payloads",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _capability_discovery_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "capability_hash",
        "source_document_hash",
        "source_url_hash",
        "provider_matrix_hash",
        "observed_at",
    )
    required_bools = (
        "current_source_observed",
        "provider_declares_or_exempts",
        "l181_capability_bound",
        "source_footer_policy_declared",
        "endpoint_compatibility_checked",
        "lifecycle_not_deprecated",
        "region_or_tenant_scope_declared",
        "no_private_payloads",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _route_discovery_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "route_id",
        "capability_name",
        "provider_family",
        "source_channel",
        "route_discovery_hash",
        "provider_source_hash",
        "l181_route_capability_hash",
        "verifier_hash",
    )
    required_bools = (
        "l181_route_covered",
        "provider_capability_observed",
        "endpoint_support_observed",
        "lifecycle_active_or_blocked",
        "region_scope_observed",
        "no_private_payloads",
    )
    return (
        all(_string(row.get(field)) for field in required_strings)
        and row.get("capability_name") in REQUIRED_MODEL_CAPABILITY_CLASSES
        and row.get("provider_family") in REQUIRED_PROVIDER_FAMILIES
        and row.get("source_channel") in REQUIRED_DISCOVERY_CHANNELS
        and all(_bool(row.get(field)) for field in required_bools)
    )


def _negative_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("fixture_hash")),
            _string(row.get("verifier_hash")),
            _bool(row.get("expected_reject")),
            _bool(row.get("observed_reject")),
            _bool(row.get("capability_claim_blocked")),
            _bool(row.get("model_invocation_blocked")),
            _bool(row.get("response_release_blocked")),
            _bool(row.get("source_footer_reliance_blocked")),
            _bool(row.get("settlement_held")),
            _bool(row.get("public_status_marked_failed")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _l181_route_ids(model_capability_coverage: dict[str, Any] | None) -> list[str]:
    if not isinstance(model_capability_coverage, dict):
        return []
    rows = model_capability_coverage.get("route_capability_rows", {})
    if isinstance(rows, dict) and rows:
        return sorted(str(route_id) for route_id in rows)
    coverage = model_capability_coverage.get("coverage", {})
    if isinstance(coverage, dict):
        route_ids = coverage.get("catalog_covered_route_ids", [])
        if isinstance(route_ids, list):
            return sorted(str(route_id) for route_id in route_ids if route_id)
    return []


def _route_rows_complete(
    rows: dict[str, dict[str, Any]],
    required_route_ids: list[str],
) -> tuple[list[str], list[str], list[str], list[str]]:
    missing = [route_id for route_id in required_route_ids if route_id not in rows]
    incomplete = [
        route_id
        for route_id in required_route_ids
        if route_id in rows and not _route_discovery_row_ready(rows[route_id])
    ]
    mismatched = [
        route_id
        for route_id in required_route_ids
        if route_id in rows and rows[route_id].get("route_id") != route_id
    ]
    unsupported_providers = [
        route_id
        for route_id in required_route_ids
        if route_id in rows
        and rows[route_id].get("provider_family") not in REQUIRED_PROVIDER_FAMILIES
    ]
    if not required_route_ids:
        missing.append("at_least_one_l181_route")
    return missing, incomplete, mismatched, unsupported_providers


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            key_str = str(key)
            next_path = f"{path}.{key_str}" if path else key_str
            allowlisted_row_keys = PUBLIC_ROW_KEY_ALLOWLISTS.get(path, set())
            if key_str in PRIVATE_FIELD_NAMES and key_str not in allowlisted_row_keys:
                found.append(next_path)
            found.extend(_contains_private_fields(nested, next_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(_contains_private_fields(nested, f"{path}[{index}]"))
    return found


def _private_strings_absent(public: Any, private_input: dict[str, Any]) -> bool:
    private_strings = private_input.get("private_strings", [])
    if not isinstance(private_strings, list):
        return True
    rendered = canonical_json(public)
    return all(
        not isinstance(value, str) or not value or value not in rendered
        for value in private_strings
    )


def make_universal_live_capability_discovery_contract(
    contract_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L182 universal live capability discovery contract."""

    model_capability_coverage = contract_input.get(
        "universal_model_capability_coverage_contract"
    )
    provider_family_rows = _row_map(contract_input, "provider_family_rows")
    discovery_channel_rows = _row_map(contract_input, "discovery_channel_rows")
    capability_discovery_rows = _row_map(contract_input, "capability_discovery_rows")
    route_discovery_rows = _row_map(contract_input, "route_discovery_rows")
    negative_rows = _row_map(contract_input, "negative_discovery_rows")

    missing_providers, incomplete_providers = _complete_rows(
        provider_family_rows,
        REQUIRED_PROVIDER_FAMILIES,
        _provider_family_row_ready,
    )
    missing_channels, incomplete_channels = _complete_rows(
        discovery_channel_rows,
        REQUIRED_DISCOVERY_CHANNELS,
        _discovery_channel_row_ready,
    )
    missing_capabilities, incomplete_capabilities = _complete_rows(
        capability_discovery_rows,
        REQUIRED_MODEL_CAPABILITY_CLASSES,
        _capability_discovery_row_ready,
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows,
        REQUIRED_NEGATIVE_DISCOVERY_FAILURES,
        _negative_row_ready,
    )
    required_route_ids = _l181_route_ids(
        model_capability_coverage
        if isinstance(model_capability_coverage, dict)
        else None
    )
    (
        missing_routes,
        incomplete_routes,
        mismatched_routes,
        unsupported_route_providers,
    ) = _route_rows_complete(route_discovery_rows, required_route_ids)

    l181_ready = _l181_ready(
        model_capability_coverage
        if isinstance(model_capability_coverage, dict)
        else None
    )
    checks = {
        "model_capability_coverage_l181_ready": l181_ready
        and _artifact_hash_is_reproducible(
            model_capability_coverage
            if isinstance(model_capability_coverage, dict)
            else None
        ),
        "provider_family_rows_complete": not missing_providers
        and not incomplete_providers,
        "discovery_channel_rows_complete": not missing_channels
        and not incomplete_channels,
        "capability_discovery_rows_complete": not missing_capabilities
        and not incomplete_capabilities,
        "route_discovery_rows_complete": (
            not missing_routes
            and not incomplete_routes
            and not mismatched_routes
            and not unsupported_route_providers
        ),
        "negative_live_capability_discovery_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "contract_signed": signing_secret is not None,
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    ready = not failure_modes

    provider_root = merkle_root([
        hash_payload({"provider_family": name, "row": provider_family_rows.get(name, {})})
        for name in REQUIRED_PROVIDER_FAMILIES
    ])
    channel_root = merkle_root([
        hash_payload({"discovery_channel": name, "row": discovery_channel_rows.get(name, {})})
        for name in REQUIRED_DISCOVERY_CHANNELS
    ])
    capability_root = merkle_root([
        hash_payload({"capability": name, "row": capability_discovery_rows.get(name, {})})
        for name in REQUIRED_MODEL_CAPABILITY_CLASSES
    ])
    route_root = merkle_root([
        hash_payload({"route_id": route_id, "row": route_discovery_rows.get(route_id, {})})
        for route_id in required_route_ids
    ])
    negative_root = merkle_root([
        hash_payload({"failure": failure, "row": negative_rows.get(failure, {})})
        for failure in REQUIRED_NEGATIVE_DISCOVERY_FAILURES
    ])

    public = {
        "universal_live_capability_discovery_contract_version": (
            UNIVERSAL_LIVE_CAPABILITY_DISCOVERY_CONTRACT_VERSION
        ),
        "schema": UNIVERSAL_LIVE_CAPABILITY_DISCOVERY_CONTRACT_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": "rdllm-universal-live-capability-discovery-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_model_capability_coverage_level": (
                MINIMUM_MODEL_CAPABILITY_COVERAGE_LEVEL
            ),
            "provider_capability_claims_require_current_sources": True,
            "endpoint_compatibility_must_match_capability_rows": True,
            "deprecated_or_removed_capabilities_fail_closed": True,
            "undocumented_capabilities_fail_closed": True,
            "region_and_tenant_scope_must_be_declared": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_LIVE_CAPABILITY_DISCOVERY_CONTRACT_VERSION,
        },
        "artifact_bindings": {
            "universal_model_capability_coverage_contract": _artifact_binding(
                model_capability_coverage
                if isinstance(model_capability_coverage, dict)
                else None,
                minimum_level=MINIMUM_MODEL_CAPABILITY_COVERAGE_LEVEL,
                ready=l181_ready,
            )
        },
        "provider_family_rows": {
            name: provider_family_rows.get(name, {})
            for name in REQUIRED_PROVIDER_FAMILIES
        },
        "discovery_channel_rows": {
            name: discovery_channel_rows.get(name, {})
            for name in REQUIRED_DISCOVERY_CHANNELS
        },
        "capability_discovery_rows": {
            name: capability_discovery_rows.get(name, {})
            for name in REQUIRED_MODEL_CAPABILITY_CLASSES
        },
        "route_discovery_rows": {
            route_id: route_discovery_rows.get(route_id, {})
            for route_id in required_route_ids
        },
        "negative_discovery_rows": {
            failure: negative_rows.get(failure, {})
            for failure in REQUIRED_NEGATIVE_DISCOVERY_FAILURES
        },
        "evidence_roots": {
            "provider_family_root": provider_root,
            "discovery_channel_root": channel_root,
            "capability_discovery_root": capability_root,
            "route_discovery_root": route_root,
            "negative_discovery_root": negative_root,
            "combined_live_capability_discovery_root": merkle_root(
                [provider_root, channel_root, capability_root, route_root, negative_root]
            ),
        },
        "checks": checks,
        "live_capability_discovery_decision": {
            "universal_live_capability_discovery_ready": ready,
            "all_capability_declarations_source_bound": ready,
            "provider_capability_claims_allowed": ready,
            "model_invocation_allowed": ready,
            "response_release_allowed": ready,
            "source_footer_reliance_allowed": ready,
            "creator_settlement_allowed": ready,
            "stale_capability_blocked": True,
            "undocumented_capability_blocked": True,
            "deprecated_capability_blocked": True,
            "failure_modes": failure_modes,
        },
        "coverage": {
            "l181_route_ids": required_route_ids,
            "missing_provider_families": missing_providers,
            "incomplete_provider_families": incomplete_providers,
            "missing_discovery_channels": missing_channels,
            "incomplete_discovery_channels": incomplete_channels,
            "missing_capability_discoveries": missing_capabilities,
            "incomplete_capability_discoveries": incomplete_capabilities,
            "missing_route_discoveries": missing_routes,
            "incomplete_route_discoveries": incomplete_routes,
            "mismatched_route_discoveries": mismatched_routes,
            "unsupported_route_provider_families": unsupported_route_providers,
            "missing_negative_discovery_failures": missing_negative,
            "incomplete_negative_discovery_failures": incomplete_negative,
        },
        "privacy": {
            "private_payloads_excluded": True,
            "private_prompts_excluded": True,
            "private_outputs_excluded": True,
            "private_provider_transcripts_excluded": True,
            "private_customer_data_excluded": True,
            "public_contract_uses_hashes_sources_routes_capabilities_and_freshness": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_model_capability_coverage_level": (
                MINIMUM_MODEL_CAPABILITY_COVERAGE_LEVEL
            ),
            "provider_family_count": len(REQUIRED_PROVIDER_FAMILIES),
            "ready_provider_family_count": len(REQUIRED_PROVIDER_FAMILIES)
            - len(missing_providers)
            - len(incomplete_providers),
            "discovery_channel_count": len(REQUIRED_DISCOVERY_CHANNELS),
            "ready_discovery_channel_count": len(REQUIRED_DISCOVERY_CHANNELS)
            - len(missing_channels)
            - len(incomplete_channels),
            "capability_discovery_count": len(REQUIRED_MODEL_CAPABILITY_CLASSES),
            "ready_capability_discovery_count": len(REQUIRED_MODEL_CAPABILITY_CLASSES)
            - len(missing_capabilities)
            - len(incomplete_capabilities),
            "l181_route_count": len(required_route_ids),
            "ready_route_discovery_count": len(required_route_ids)
            - len(missing_routes)
            - len(incomplete_routes)
            - len(mismatched_routes)
            - len(unsupported_route_providers),
            "negative_discovery_failure_count": len(REQUIRED_NEGATIVE_DISCOVERY_FAILURES),
            "ready_negative_discovery_failure_count": len(
                REQUIRED_NEGATIVE_DISCOVERY_FAILURES
            )
            - len(missing_negative)
            - len(incomplete_negative),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": True,
            "signed_live_capability_discovery_contract": signing_secret is not None,
        },
    }
    public["universal_live_capability_discovery_contract_hash"] = hash_payload(
        _hashable_contract(public)
    )
    public["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_contract(public), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return public


def validate_universal_live_capability_discovery_contract_shape(
    contract: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for an L182 discovery contract."""

    errors: list[str] = []
    required = (
        "universal_live_capability_discovery_contract_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "artifact_bindings",
        "provider_family_rows",
        "discovery_channel_rows",
        "capability_discovery_rows",
        "route_discovery_rows",
        "negative_discovery_rows",
        "evidence_roots",
        "checks",
        "live_capability_discovery_decision",
        "coverage",
        "privacy",
        "summary",
        "universal_live_capability_discovery_contract_hash",
    )
    for key in required:
        if key not in contract:
            errors.append(f"missing live capability discovery field: {key}")
    if contract.get("universal_live_capability_discovery_contract_version") != (
        UNIVERSAL_LIVE_CAPABILITY_DISCOVERY_CONTRACT_VERSION
    ):
        errors.append("unexpected universal_live_capability_discovery_contract_version")
    if contract.get("schema") != UNIVERSAL_LIVE_CAPABILITY_DISCOVERY_CONTRACT_SCHEMA:
        errors.append("unexpected live capability discovery schema")
    for provider in REQUIRED_PROVIDER_FAMILIES:
        if provider not in contract.get("provider_family_rows", {}):
            errors.append(f"missing provider family row: {provider}")
    for channel in REQUIRED_DISCOVERY_CHANNELS:
        if channel not in contract.get("discovery_channel_rows", {}):
            errors.append(f"missing discovery channel row: {channel}")
    for capability in REQUIRED_MODEL_CAPABILITY_CLASSES:
        if capability not in contract.get("capability_discovery_rows", {}):
            errors.append(f"missing capability discovery row: {capability}")
    for failure in REQUIRED_NEGATIVE_DISCOVERY_FAILURES:
        if failure not in contract.get("negative_discovery_rows", {}):
            errors.append(f"missing negative discovery row: {failure}")
    for check in (
        "model_capability_coverage_l181_ready",
        "provider_family_rows_complete",
        "discovery_channel_rows_complete",
        "capability_discovery_rows_complete",
        "route_discovery_rows_complete",
        "negative_live_capability_discovery_fixtures_reject",
        "contract_signed",
    ):
        if check not in contract.get("checks", {}):
            errors.append(f"missing live capability discovery check: {check}")
    return errors


def verify_universal_live_capability_discovery_contract(
    contract_input: dict[str, Any],
    contract: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L182 capability discovery contract against replay input."""

    errors = validate_universal_live_capability_discovery_contract_shape(contract)
    expected_hash = hash_payload(_hashable_contract(contract))
    if contract.get("universal_live_capability_discovery_contract_hash") != expected_hash:
        errors.append("universal_live_capability_discovery_contract_hash mismatch")
    private_fields = _contains_private_fields(contract)
    if private_fields:
        errors.append(
            "live capability discovery contract exposes private fields: "
            + ", ".join(private_fields)
        )
    if not _private_strings_absent(contract, contract_input):
        errors.append("live capability discovery contract exposes private input strings")
    replayed = make_universal_live_capability_discovery_contract(
        contract_input,
        issuer=contract.get("issuer", DEFAULT_ISSUER),
        created_at=contract.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get("universal_live_capability_discovery_contract_hash") != contract.get(
        "universal_live_capability_discovery_contract_hash"
    ):
        errors.append("live capability discovery contract does not match replay inputs")
    if contract.get("summary", {}).get("status") != "ready":
        errors.append("live capability discovery contract is not ready")
    if (
        contract.get("live_capability_discovery_decision", {}).get(
            "universal_live_capability_discovery_ready"
        )
        is not True
    ):
        errors.append("live capability discovery decision is not ready")
    if contract.get("privacy", {}).get("private_payloads_excluded") is not True:
        errors.append("live capability discovery privacy is not preserved")
    if signing_secret:
        signature = contract.get("signature", {})
        expected_signature = sign_payload(_hashable_contract(contract), signing_secret)
        if not signature:
            errors.append("live capability discovery contract is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("live capability discovery contract signature is invalid")
    return errors
