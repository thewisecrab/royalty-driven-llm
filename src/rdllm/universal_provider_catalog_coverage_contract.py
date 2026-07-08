"""Universal provider catalog coverage contracts.

The L178 layer closes the gap between a declared model registry and the live
catalogs exposed by providers, gateways, marketplaces, local runtimes, and
private deployments. L176 proves declared routes are well formed. L177 proves
those routes cannot release unfootnoted answers. L178 proves catalog snapshots
are exhaustively normalized so every discovered model is either bound to an
L176 route with L177 footer enforcement or explicitly blocked before provider
coverage, answer release, or settlement can be claimed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_PROVIDER_CATALOG_COVERAGE_CONTRACT_VERSION = (
    "rdllm-universal-provider-catalog-coverage-contract/v1"
)
UNIVERSAL_PROVIDER_CATALOG_COVERAGE_CONTRACT_SCHEMA = (
    "docs/schemas/universal_provider_catalog_coverage_contract.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L178"
MINIMUM_MODEL_PROVIDER_REGISTRY_LEVEL = "RDLLM-L176"
MINIMUM_SOURCE_FOOTER_ENFORCEMENT_LEVEL = "RDLLM-L177"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-provider-catalog-coverage-contract.json"
)

REQUIRED_CATALOG_DISCOVERY_CHANNELS = (
    "first_party_models_endpoint",
    "openai_compatible_models_endpoint",
    "cloud_catalog_api",
    "marketplace_listing_api",
    "hosted_open_weight_registry",
    "router_gateway_catalog",
    "enterprise_private_catalog",
    "local_runtime_manifest",
    "regional_sovereign_catalog",
    "sdk_static_catalog",
    "billing_meter_catalog",
    "lifecycle_deprecation_feed",
)

REQUIRED_NORMALIZED_MODEL_FIELDS = (
    "provider_namespace",
    "provider_model_id",
    "public_aliases",
    "model_route_class",
    "endpoint_protocol",
    "input_modalities",
    "output_modalities",
    "context_window",
    "tool_call_support",
    "streaming_support",
    "batch_support",
    "pricing_meter",
    "region_availability",
    "lifecycle_status",
    "source_footer_profile",
    "settlement_meter",
)

REQUIRED_COVERAGE_DECISIONS = (
    "admitted_registered_route",
    "explicitly_unsupported_model",
    "quarantined_unknown_model",
    "deprecated_or_removed_model",
    "region_blocked_model",
    "private_attested_route",
    "router_alias_resolved",
    "local_runtime_attested",
)

ADMISSION_DECISIONS = {
    "admitted_registered_route",
    "private_attested_route",
    "router_alias_resolved",
    "local_runtime_attested",
}

BLOCK_DECISIONS = {
    "explicitly_unsupported_model",
    "quarantined_unknown_model",
    "deprecated_or_removed_model",
    "region_blocked_model",
}

REQUIRED_NEGATIVE_CATALOG_FAILURES = (
    "catalog_entry_not_in_l176_registry",
    "l176_route_not_seen_in_catalog_snapshot",
    "stale_catalog_snapshot_accepted",
    "partial_catalog_claims_complete",
    "provider_alias_unresolved",
    "capability_mismatch_ignored",
    "modality_mismatch_ignored",
    "context_limit_mismatch_ignored",
    "price_meter_missing",
    "source_footer_profile_missing",
    "settlement_meter_missing",
    "lifecycle_deprecation_ignored",
    "region_availability_mismatch",
    "private_model_unattested",
    "router_fallback_not_disclosed",
    "local_runtime_unhashed",
    "removed_model_still_admitted",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_provider_catalog_coverage_contract_hash",
    "universal_model_provider_registry_hash",
    "universal_source_footer_enforcement_contract_hash",
    "catalog_snapshot_hash",
    "catalog_channel_hash",
    "catalog_entry_hash",
    "provider_model_id_hash",
    "normalized_route_hash",
    "coverage_status_hash",
    "model_identity_hash",
    "capability_manifest_hash",
    "pricing_meter_hash",
    "lifecycle_state_hash",
    "source_footer_profile_hash",
    "settlement_meter_hash",
    "verifier_hash",
    "fixture_hash",
    "attestation_hash",
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
    "evidence_text",
    "matched_text",
    "quote",
    "raw_native_request",
    "raw_native_response",
    "native_response_body",
    "catalog_export_text",
    "registry_payload_text",
    "private_model_weights",
    "private_fine_tune_data",
    "customer_id",
    "customer_email",
    "tenant_id",
    "billing_record",
    "tool_payload",
    "api_key",
    "access_token",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_provider_catalog_coverage_contract_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L178 catalog coverage contract."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in contract.items()
        if key
        not in {"universal_provider_catalog_coverage_contract_hash", "signature"}
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
    if not artifact:
        return {}
    summary = artifact.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def _registry_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("registry_decision", {}) if artifact else {}
    summary = _summary(artifact)
    return (
        summary.get("status") == "ready"
        and summary.get("target_certification_level")
        == MINIMUM_MODEL_PROVIDER_REGISTRY_LEVEL
        and decision.get("universal_model_provider_registry_ready") is True
        and decision.get("unregistered_routes_blocked") is True
    )


def _footer_contract_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("footer_enforcement_decision", {}) if artifact else {}
    summary = _summary(artifact)
    return (
        summary.get("status") == "ready"
        and summary.get("target_certification_level")
        == MINIMUM_SOURCE_FOOTER_ENFORCEMENT_LEVEL
        and decision.get("universal_source_footer_enforcement_ready") is True
        and decision.get("final_answer_release_allowed") is True
        and decision.get("source_payment_without_attribution_blocked") is True
    )


def _string(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _bool(value: Any) -> bool:
    return value is True


def _row_map(payload: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    rows = payload.get(key, {})
    if not isinstance(rows, dict):
        return {}
    return {
        str(name): row
        for name, row in rows.items()
        if isinstance(row, dict)
    }


def _list_rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = payload.get(key, [])
    if isinstance(rows, dict):
        rows = list(rows.values())
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _complete_rows(
    rows: dict[str, dict[str, Any]],
    required: tuple[str, ...],
    predicate,
) -> tuple[list[str], list[str]]:
    missing = [name for name in required if name not in rows]
    incomplete = [name for name in required if name in rows and not predicate(rows[name])]
    return missing, incomplete


def _channel_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("catalog_channel_hash")),
            _string(row.get("schema_hash")),
            _string(row.get("fetcher_hash")),
            _string(row.get("normalizer_hash")),
            _bool(row.get("complete_export_attested")),
            _bool(row.get("fresh_within_sla")),
            _bool(row.get("pagination_exhausted")),
            _bool(row.get("supports_delta_events")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _normalization_field_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("field_hash")),
            _string(row.get("normalizer_hash")),
            _string(row.get("verifier_hash")),
            _bool(row.get("field_required")),
            _bool(row.get("field_normalized")),
            _bool(row.get("capability_safe")),
            _bool(row.get("public_metadata_only")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _snapshot_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("catalog_snapshot_hash")),
            _string(row.get("catalog_channel_hash")),
            _string(row.get("entry_count_hash")),
            _string(row.get("freshness_hash")),
            _bool(row.get("complete_snapshot")),
            _bool(row.get("signed_snapshot")),
            _bool(row.get("pagination_exhausted")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _discovered_model_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "catalog_model_id",
        "provider_namespace",
        "registry_source",
        "model_route_class",
        "catalog_entry_hash",
        "provider_model_id_hash",
        "normalized_route_id",
        "capability_manifest_hash",
        "pricing_meter_hash",
        "lifecycle_state_hash",
        "source_footer_profile_hash",
        "settlement_meter_hash",
        "coverage_decision",
    )
    required_bools = (
        "catalog_entry_seen",
        "capability_metadata_normalized",
        "catalog_snapshot_current",
        "lifecycle_status_current",
        "source_footer_profile_bound",
        "settlement_meter_bound",
        "registered_or_blocked",
        "source_footer_enforced_or_blocked",
        "settlement_allowed_or_held",
        "public_status_marked",
        "no_private_payloads",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _route_coverage_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("route_id")),
            _string(row.get("catalog_coverage_hash")),
            _string(row.get("catalog_entry_hash")),
            _string(row.get("route_identity_hash")),
            _string(row.get("verifier_hash")),
            _bool(row.get("l176_route_present")),
            _bool(row.get("l177_route_enforced")),
            _bool(row.get("discovered_or_exempted")),
            _bool(row.get("catalog_snapshot_current")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _negative_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("fixture_hash")),
            _string(row.get("verifier_hash")),
            _bool(row.get("expected_reject")),
            _bool(row.get("observed_reject")),
            _bool(row.get("catalog_claim_blocked")),
            _bool(row.get("route_admission_blocked")),
            _bool(row.get("source_footer_reliance_blocked")),
            _bool(row.get("settlement_held")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _declared_route_ids(registry: dict[str, Any] | None) -> list[str]:
    if not isinstance(registry, dict):
        return []
    routes = registry.get("declared_model_routes", [])
    if isinstance(routes, dict):
        routes = list(routes.values())
    if not isinstance(routes, list):
        return []
    return [
        str(row.get("route_id"))
        for row in routes
        if isinstance(row, dict) and row.get("route_id")
    ]


def _registry_sets(
    registry: dict[str, Any] | None,
) -> tuple[set[str], set[str], set[str]]:
    if not isinstance(registry, dict):
        return set(), set(), set()
    namespaces = set(registry.get("provider_namespace_rows", {}) or {})
    sources = set(registry.get("registry_source_rows", {}) or {})
    route_classes = set(registry.get("model_route_class_rows", {}) or {})
    return namespaces, sources, route_classes


def _footer_route_ids(contract: dict[str, Any] | None) -> set[str]:
    if not isinstance(contract, dict):
        return set()
    rows = contract.get("route_enforcement_rows", {})
    if not isinstance(rows, dict):
        return set()
    found: set[str] = set()
    for key, row in rows.items():
        if isinstance(row, dict):
            found.add(str(row.get("route_id") or key))
        else:
            found.add(str(key))
    return found


def _catalog_model_id(row: dict[str, Any], fallback: str) -> str:
    return _string(row.get("catalog_model_id")) or fallback


def _catalog_entry_consistency(
    rows: list[dict[str, Any]],
    *,
    route_ids: set[str],
    footer_route_ids: set[str],
    namespaces: set[str],
    sources: set[str],
    route_classes: set[str],
) -> tuple[list[str], list[str], list[str], list[str], list[str]]:
    incomplete: list[str] = []
    invalid_decisions: list[str] = []
    invalid_bindings: list[str] = []
    invalid_taxonomy: list[str] = []
    duplicate_ids: list[str] = []
    ids = [_catalog_model_id(row, f"catalog-entry:{index}") for index, row in enumerate(rows)]
    duplicate_ids = sorted(model_id for model_id in set(ids) if ids.count(model_id) > 1)

    for index, row in enumerate(rows):
        model_id = _catalog_model_id(row, f"catalog-entry:{index}")
        if not _discovered_model_row_ready(row):
            incomplete.append(model_id)
        decision = _string(row.get("coverage_decision"))
        route_id = _string(row.get("normalized_route_id"))
        if decision not in REQUIRED_COVERAGE_DECISIONS:
            invalid_decisions.append(model_id)
            continue
        if (
            row.get("provider_namespace") not in namespaces
            or row.get("registry_source") not in sources
            or row.get("model_route_class") not in route_classes
        ):
            invalid_taxonomy.append(model_id)
        if decision in ADMISSION_DECISIONS:
            if (
                route_id not in route_ids
                or route_id not in footer_route_ids
                or row.get("l176_route_registered") is not True
                or row.get("l177_footer_enforced") is not True
                or row.get("registration_blocked") is True
            ):
                invalid_bindings.append(model_id)
        elif decision in BLOCK_DECISIONS:
            if (
                row.get("registration_blocked") is not True
                or row.get("settlement_held") is not True
                or row.get("public_status_marked") is not True
            ):
                invalid_bindings.append(model_id)
    return (
        incomplete,
        invalid_decisions,
        invalid_bindings,
        invalid_taxonomy,
        duplicate_ids,
    )


def _route_coverage_consistency(
    rows: dict[str, dict[str, Any]],
    route_ids: list[str],
    footer_route_ids: set[str],
) -> tuple[list[str], list[str], list[str]]:
    missing = [route_id for route_id in route_ids if route_id not in rows]
    incomplete: list[str] = []
    invalid: list[str] = []
    for route_id in route_ids:
        if route_id not in rows:
            continue
        row = rows[route_id]
        if not _route_coverage_row_ready(row):
            incomplete.append(route_id)
        if (
            row.get("route_id") != route_id
            or route_id not in footer_route_ids
            or row.get("l176_route_present") is not True
            or row.get("l177_route_enforced") is not True
        ):
            invalid.append(route_id)
    return missing, incomplete, invalid


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            key_str = str(key)
            next_path = f"{path}.{key_str}" if path else key_str
            if key_str in PRIVATE_FIELD_NAMES:
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


def _public_discovered_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    public_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        public_rows.append(
            {
                "catalog_model_id": _catalog_model_id(row, f"catalog-entry:{index}"),
                "provider_namespace": _string(row.get("provider_namespace")),
                "registry_source": _string(row.get("registry_source")),
                "model_route_class": _string(row.get("model_route_class")),
                "catalog_entry_hash": _string(row.get("catalog_entry_hash")),
                "provider_model_id_hash": _string(row.get("provider_model_id_hash")),
                "normalized_route_id": _string(row.get("normalized_route_id")),
                "capability_manifest_hash": _string(
                    row.get("capability_manifest_hash")
                ),
                "pricing_meter_hash": _string(row.get("pricing_meter_hash")),
                "lifecycle_state_hash": _string(row.get("lifecycle_state_hash")),
                "source_footer_profile_hash": _string(
                    row.get("source_footer_profile_hash")
                ),
                "settlement_meter_hash": _string(row.get("settlement_meter_hash")),
                "coverage_decision": _string(row.get("coverage_decision")),
                "catalog_entry_seen": _bool(row.get("catalog_entry_seen")),
                "capability_metadata_normalized": _bool(
                    row.get("capability_metadata_normalized")
                ),
                "catalog_snapshot_current": _bool(
                    row.get("catalog_snapshot_current")
                ),
                "lifecycle_status_current": _bool(
                    row.get("lifecycle_status_current")
                ),
                "l176_route_registered": _bool(row.get("l176_route_registered")),
                "l177_footer_enforced": _bool(row.get("l177_footer_enforced")),
                "registration_blocked": _bool(row.get("registration_blocked")),
                "source_footer_profile_bound": _bool(
                    row.get("source_footer_profile_bound")
                ),
                "settlement_meter_bound": _bool(row.get("settlement_meter_bound")),
                "settlement_held": _bool(row.get("settlement_held")),
                "registered_or_blocked": _bool(row.get("registered_or_blocked")),
                "source_footer_enforced_or_blocked": _bool(
                    row.get("source_footer_enforced_or_blocked")
                ),
                "settlement_allowed_or_held": _bool(
                    row.get("settlement_allowed_or_held")
                ),
                "public_status_marked": _bool(row.get("public_status_marked")),
                "no_private_payloads": _bool(row.get("no_private_payloads")),
            }
        )
    return sorted(public_rows, key=lambda item: item["catalog_model_id"])


def make_universal_provider_catalog_coverage_contract(
    contract_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L178 provider catalog coverage contract."""

    registry = contract_input.get("universal_model_provider_registry")
    footer_contract = contract_input.get("universal_source_footer_enforcement_contract")
    catalog_channel_rows = _row_map(contract_input, "catalog_channel_rows")
    normalization_field_rows = _row_map(contract_input, "normalization_field_rows")
    catalog_snapshot_rows = _row_map(contract_input, "catalog_snapshot_rows")
    route_coverage_rows = _row_map(contract_input, "registry_route_coverage_rows")
    negative_rows = _row_map(contract_input, "negative_catalog_rows")
    discovered_rows = _list_rows(contract_input, "discovered_model_rows")

    route_ids = _declared_route_ids(registry if isinstance(registry, dict) else None)
    footer_route_ids = _footer_route_ids(
        footer_contract if isinstance(footer_contract, dict) else None
    )
    namespaces, sources, route_classes = _registry_sets(
        registry if isinstance(registry, dict) else None
    )

    missing_channels, incomplete_channels = _complete_rows(
        catalog_channel_rows,
        REQUIRED_CATALOG_DISCOVERY_CHANNELS,
        _channel_row_ready,
    )
    missing_fields, incomplete_fields = _complete_rows(
        normalization_field_rows,
        REQUIRED_NORMALIZED_MODEL_FIELDS,
        _normalization_field_row_ready,
    )
    missing_snapshots, incomplete_snapshots = _complete_rows(
        catalog_snapshot_rows,
        REQUIRED_CATALOG_DISCOVERY_CHANNELS,
        _snapshot_row_ready,
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows,
        REQUIRED_NEGATIVE_CATALOG_FAILURES,
        _negative_row_ready,
    )
    (
        incomplete_discovered,
        invalid_decisions,
        invalid_bindings,
        invalid_taxonomy,
        duplicate_catalog_model_ids,
    ) = _catalog_entry_consistency(
        discovered_rows,
        route_ids=set(route_ids),
        footer_route_ids=footer_route_ids,
        namespaces=namespaces,
        sources=sources,
        route_classes=route_classes,
    )
    (
        missing_route_coverage,
        incomplete_route_coverage,
        invalid_route_coverage,
    ) = _route_coverage_consistency(route_coverage_rows, route_ids, footer_route_ids)

    checks = {
        "model_provider_registry_bound": _artifact_hash_is_reproducible(
            registry if isinstance(registry, dict) else None
        ),
        "model_provider_registry_l176_ready": _registry_ready(
            registry if isinstance(registry, dict) else None
        ),
        "source_footer_enforcement_contract_bound": _artifact_hash_is_reproducible(
            footer_contract if isinstance(footer_contract, dict) else None
        ),
        "source_footer_enforcement_contract_l177_ready": _footer_contract_ready(
            footer_contract if isinstance(footer_contract, dict) else None
        ),
        "catalog_channel_rows_complete": not missing_channels
        and not incomplete_channels,
        "normalization_field_rows_complete": not missing_fields
        and not incomplete_fields,
        "catalog_snapshot_rows_complete": not missing_snapshots
        and not incomplete_snapshots,
        "discovered_catalog_entries_present": bool(discovered_rows),
        "discovered_catalog_entries_exhaustive": not incomplete_discovered
        and not invalid_decisions
        and not invalid_bindings
        and not invalid_taxonomy
        and not duplicate_catalog_model_ids,
        "all_l176_routes_catalog_covered": bool(route_ids)
        and not missing_route_coverage
        and not incomplete_route_coverage
        and not invalid_route_coverage,
        "negative_catalog_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "contract_signed": signing_secret is not None,
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    ready = not failure_modes

    catalog_channel_root = merkle_root([
        hash_payload({"name": name, "row": catalog_channel_rows.get(name, {})})
        for name in REQUIRED_CATALOG_DISCOVERY_CHANNELS
    ])
    normalization_field_root = merkle_root([
        hash_payload({"name": name, "row": normalization_field_rows.get(name, {})})
        for name in REQUIRED_NORMALIZED_MODEL_FIELDS
    ])
    snapshot_root = merkle_root([
        hash_payload({"name": name, "row": catalog_snapshot_rows.get(name, {})})
        for name in REQUIRED_CATALOG_DISCOVERY_CHANNELS
    ])
    discovered_model_root = merkle_root([
        hash_payload({"catalog_model_id": row["catalog_model_id"], "row": row})
        for row in _public_discovered_rows(discovered_rows)
    ])
    route_coverage_root = merkle_root([
        hash_payload({"route_id": route_id, "row": route_coverage_rows.get(route_id, {})})
        for route_id in route_ids
    ])
    negative_root = merkle_root([
        hash_payload({"name": name, "row": negative_rows.get(name, {})})
        for name in REQUIRED_NEGATIVE_CATALOG_FAILURES
    ])

    public = {
        "universal_provider_catalog_coverage_contract_version": (
            UNIVERSAL_PROVIDER_CATALOG_COVERAGE_CONTRACT_VERSION
        ),
        "schema": UNIVERSAL_PROVIDER_CATALOG_COVERAGE_CONTRACT_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": (
                "rdllm-universal-provider-catalog-coverage-policy/v1"
            ),
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_model_provider_registry_level": (
                MINIMUM_MODEL_PROVIDER_REGISTRY_LEVEL
            ),
            "minimum_source_footer_enforcement_level": (
                MINIMUM_SOURCE_FOOTER_ENFORCEMENT_LEVEL
            ),
            "provider_catalogs_must_be_exhaustively_normalized": True,
            "every_discovered_model_must_be_admitted_or_blocked": True,
            "declared_routes_must_be_catalog_covered_or_exempted": True,
            "unknown_catalog_entries_fail_closed": True,
            "catalog_coverage_required_before_universal_provider_claim": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_PROVIDER_CATALOG_COVERAGE_CONTRACT_VERSION,
        },
        "model_provider_registry_binding": {
            "present": isinstance(registry, dict),
            "artifact_hash": _declared_hash(registry if isinstance(registry, dict) else None),
            "payload_hash": hash_payload(
                _hashable_artifact(registry if isinstance(registry, dict) else None)
            ),
            "hash_reproducible": checks["model_provider_registry_bound"],
            "status": _summary(registry if isinstance(registry, dict) else None).get(
                "status", ""
            ),
            "level": _summary(registry if isinstance(registry, dict) else None).get(
                "target_certification_level", ""
            ),
            "declared_model_route_count": len(route_ids),
        },
        "source_footer_enforcement_binding": {
            "present": isinstance(footer_contract, dict),
            "artifact_hash": _declared_hash(
                footer_contract if isinstance(footer_contract, dict) else None
            ),
            "payload_hash": hash_payload(
                _hashable_artifact(
                    footer_contract if isinstance(footer_contract, dict) else None
                )
            ),
            "hash_reproducible": checks[
                "source_footer_enforcement_contract_bound"
            ],
            "status": _summary(
                footer_contract if isinstance(footer_contract, dict) else None
            ).get("status", ""),
            "level": _summary(
                footer_contract if isinstance(footer_contract, dict) else None
            ).get("target_certification_level", ""),
            "route_enforcement_count": len(footer_route_ids),
        },
        "catalog_channel_rows": {
            name: catalog_channel_rows.get(name, {})
            for name in REQUIRED_CATALOG_DISCOVERY_CHANNELS
        },
        "normalization_field_rows": {
            name: normalization_field_rows.get(name, {})
            for name in REQUIRED_NORMALIZED_MODEL_FIELDS
        },
        "catalog_snapshot_rows": {
            name: catalog_snapshot_rows.get(name, {})
            for name in REQUIRED_CATALOG_DISCOVERY_CHANNELS
        },
        "discovered_model_rows": _public_discovered_rows(discovered_rows),
        "registry_route_coverage_rows": {
            route_id: route_coverage_rows.get(route_id, {}) for route_id in route_ids
        },
        "coverage_decision_classes": list(REQUIRED_COVERAGE_DECISIONS),
        "negative_catalog_rows": {
            name: negative_rows.get(name, {})
            for name in REQUIRED_NEGATIVE_CATALOG_FAILURES
        },
        "evidence_roots": {
            "catalog_channel_root": catalog_channel_root,
            "normalization_field_root": normalization_field_root,
            "catalog_snapshot_root": snapshot_root,
            "discovered_model_root": discovered_model_root,
            "registry_route_coverage_root": route_coverage_root,
            "negative_catalog_root": negative_root,
            "combined_catalog_coverage_root": merkle_root(
                [
                    catalog_channel_root,
                    normalization_field_root,
                    snapshot_root,
                    discovered_model_root,
                    route_coverage_root,
                    negative_root,
                ]
            ),
        },
        "checks": checks,
        "catalog_coverage_decision": {
            "universal_provider_catalog_coverage_ready": ready,
            "universal_provider_claim_allowed": ready,
            "catalog_exhaustiveness_attested": ready,
            "new_model_admission_allowed": ready,
            "unknown_catalog_models_blocked": True,
            "declared_routes_without_catalog_coverage_blocked": True,
            "source_footer_reliance_allowed": ready,
            "creator_settlement_allowed": ready,
            "failure_modes": failure_modes,
        },
        "coverage": {
            "missing_catalog_channels": missing_channels,
            "incomplete_catalog_channels": incomplete_channels,
            "missing_normalization_fields": missing_fields,
            "incomplete_normalization_fields": incomplete_fields,
            "missing_catalog_snapshots": missing_snapshots,
            "incomplete_catalog_snapshots": incomplete_snapshots,
            "incomplete_discovered_model_entries": incomplete_discovered,
            "invalid_catalog_coverage_decisions": invalid_decisions,
            "invalid_catalog_route_bindings": invalid_bindings,
            "invalid_catalog_taxonomy_bindings": invalid_taxonomy,
            "duplicate_catalog_model_ids": duplicate_catalog_model_ids,
            "missing_registry_route_coverage": missing_route_coverage,
            "incomplete_registry_route_coverage": incomplete_route_coverage,
            "invalid_registry_route_coverage": invalid_route_coverage,
            "missing_negative_catalog_failures": missing_negative,
            "incomplete_negative_catalog_failures": incomplete_negative,
        },
        "privacy": {
            "private_payloads_excluded": True,
            "private_prompts_excluded": True,
            "private_outputs_excluded": True,
            "private_catalog_exports_excluded": True,
            "public_contract_uses_hashes_and_metadata": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_model_provider_registry_level": (
                MINIMUM_MODEL_PROVIDER_REGISTRY_LEVEL
            ),
            "minimum_source_footer_enforcement_level": (
                MINIMUM_SOURCE_FOOTER_ENFORCEMENT_LEVEL
            ),
            "catalog_channel_count": len(REQUIRED_CATALOG_DISCOVERY_CHANNELS),
            "ready_catalog_channel_count": len(REQUIRED_CATALOG_DISCOVERY_CHANNELS)
            - len(missing_channels)
            - len(incomplete_channels),
            "normalization_field_count": len(REQUIRED_NORMALIZED_MODEL_FIELDS),
            "ready_normalization_field_count": len(REQUIRED_NORMALIZED_MODEL_FIELDS)
            - len(missing_fields)
            - len(incomplete_fields),
            "catalog_snapshot_count": len(REQUIRED_CATALOG_DISCOVERY_CHANNELS),
            "ready_catalog_snapshot_count": len(REQUIRED_CATALOG_DISCOVERY_CHANNELS)
            - len(missing_snapshots)
            - len(incomplete_snapshots),
            "discovered_model_count": len(discovered_rows),
            "ready_discovered_model_count": len(discovered_rows)
            - len(set(incomplete_discovered))
            - len(set(invalid_decisions))
            - len(set(invalid_bindings))
            - len(set(invalid_taxonomy)),
            "declared_model_route_count": len(route_ids),
            "catalog_covered_route_count": len(route_ids)
            - len(set(missing_route_coverage))
            - len(set(incomplete_route_coverage))
            - len(set(invalid_route_coverage)),
            "coverage_decision_count": len(REQUIRED_COVERAGE_DECISIONS),
            "negative_catalog_failure_count": len(REQUIRED_NEGATIVE_CATALOG_FAILURES),
            "ready_negative_catalog_failure_count": len(
                REQUIRED_NEGATIVE_CATALOG_FAILURES
            )
            - len(missing_negative)
            - len(incomplete_negative),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": True,
            "signed_provider_catalog_coverage_contract": signing_secret is not None,
        },
    }
    public["universal_provider_catalog_coverage_contract_hash"] = hash_payload(
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


def validate_universal_provider_catalog_coverage_contract_shape(
    contract: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for an L178 catalog coverage contract."""

    errors: list[str] = []
    required = (
        "universal_provider_catalog_coverage_contract_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "model_provider_registry_binding",
        "source_footer_enforcement_binding",
        "catalog_channel_rows",
        "normalization_field_rows",
        "catalog_snapshot_rows",
        "discovered_model_rows",
        "registry_route_coverage_rows",
        "coverage_decision_classes",
        "negative_catalog_rows",
        "evidence_roots",
        "checks",
        "catalog_coverage_decision",
        "coverage",
        "privacy",
        "summary",
        "universal_provider_catalog_coverage_contract_hash",
    )
    for key in required:
        if key not in contract:
            errors.append(f"missing provider catalog coverage field: {key}")
    if contract.get("universal_provider_catalog_coverage_contract_version") != (
        UNIVERSAL_PROVIDER_CATALOG_COVERAGE_CONTRACT_VERSION
    ):
        errors.append("unexpected universal_provider_catalog_coverage_contract_version")
    if contract.get("schema") != UNIVERSAL_PROVIDER_CATALOG_COVERAGE_CONTRACT_SCHEMA:
        errors.append("unexpected provider catalog coverage schema")
    for name in REQUIRED_CATALOG_DISCOVERY_CHANNELS:
        if name not in contract.get("catalog_channel_rows", {}):
            errors.append(f"missing catalog channel row: {name}")
        if name not in contract.get("catalog_snapshot_rows", {}):
            errors.append(f"missing catalog snapshot row: {name}")
    for name in REQUIRED_NORMALIZED_MODEL_FIELDS:
        if name not in contract.get("normalization_field_rows", {}):
            errors.append(f"missing normalization field row: {name}")
    for decision in REQUIRED_COVERAGE_DECISIONS:
        if decision not in contract.get("coverage_decision_classes", []):
            errors.append(f"missing coverage decision class: {decision}")
    for name in REQUIRED_NEGATIVE_CATALOG_FAILURES:
        if name not in contract.get("negative_catalog_rows", {}):
            errors.append(f"missing negative catalog row: {name}")
    for check in (
        "model_provider_registry_bound",
        "model_provider_registry_l176_ready",
        "source_footer_enforcement_contract_bound",
        "source_footer_enforcement_contract_l177_ready",
        "catalog_channel_rows_complete",
        "normalization_field_rows_complete",
        "catalog_snapshot_rows_complete",
        "discovered_catalog_entries_present",
        "discovered_catalog_entries_exhaustive",
        "all_l176_routes_catalog_covered",
        "negative_catalog_fixtures_reject",
        "contract_signed",
    ):
        if check not in contract.get("checks", {}):
            errors.append(f"missing provider catalog coverage check: {check}")
    return errors


def verify_universal_provider_catalog_coverage_contract(
    contract_input: dict[str, Any],
    contract: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L178 provider catalog coverage contract against replay input."""

    errors = validate_universal_provider_catalog_coverage_contract_shape(contract)
    expected_hash = hash_payload(_hashable_contract(contract))
    if contract.get("universal_provider_catalog_coverage_contract_hash") != expected_hash:
        errors.append("universal_provider_catalog_coverage_contract_hash mismatch")
    private_fields = _contains_private_fields(contract)
    if private_fields:
        errors.append(
            "provider catalog coverage contract exposes private fields: "
            + ", ".join(private_fields)
        )
    if not _private_strings_absent(contract, contract_input):
        errors.append("provider catalog coverage contract exposes private input strings")
    replayed = make_universal_provider_catalog_coverage_contract(
        contract_input,
        issuer=contract.get("issuer", DEFAULT_ISSUER),
        created_at=contract.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get("universal_provider_catalog_coverage_contract_hash") != contract.get(
        "universal_provider_catalog_coverage_contract_hash"
    ):
        errors.append("provider catalog coverage contract does not match replay inputs")
    if contract.get("summary", {}).get("status") != "ready":
        errors.append("provider catalog coverage contract is not ready")
    if (
        contract.get("catalog_coverage_decision", {}).get(
            "universal_provider_catalog_coverage_ready"
        )
        is not True
    ):
        errors.append("provider catalog coverage decision is not ready")
    if contract.get("privacy", {}).get("private_payloads_excluded") is not True:
        errors.append("provider catalog coverage privacy is not preserved")
    if signing_secret:
        signature = contract.get("signature", {})
        expected_signature = sign_payload(_hashable_contract(contract), signing_secret)
        if not signature:
            errors.append("provider catalog coverage contract is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("provider catalog coverage contract signature is invalid")
    return errors
