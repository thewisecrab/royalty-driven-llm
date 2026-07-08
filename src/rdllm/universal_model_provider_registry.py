"""Universal model/provider registries.

The L176 layer extends L175 from fixed provider onboarding into dynamic model and
route coverage. A provider can support the right native API surfaces and still
miss the goal of "every model" if new model IDs, hosted open-weight services,
routers, private deployments, local runtimes, regional catalogs, or marketplace
aliases are not registered as concrete service routes with adapter manifests,
capability metadata, lifecycle state, conformance evidence, source-footer
support, and negative fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)
from rdllm.transparency import merkle_root

UNIVERSAL_MODEL_PROVIDER_REGISTRY_VERSION = (
    "rdllm-universal-model-provider-registry/v1"
)
UNIVERSAL_MODEL_PROVIDER_REGISTRY_SCHEMA = (
    "docs/schemas/universal_model_provider_registry.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L176"
MINIMUM_PROVIDER_ONBOARDING_LEVEL = "RDLLM-L175"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-model-provider-registry.json"
)

REQUIRED_REGISTRY_SOURCES = (
    "first_party_provider_catalog",
    "cloud_model_catalog",
    "marketplace_model_catalog",
    "hosted_open_weight_catalog",
    "router_gateway_catalog",
    "open_weight_hub_catalog",
    "enterprise_private_catalog",
    "local_runtime_catalog",
    "regional_sovereign_catalog",
    "agent_tool_runtime_catalog",
)

REQUIRED_PROVIDER_NAMESPACE_CLASSES = (
    "foundation_provider",
    "cloud_hosted_provider",
    "model_marketplace",
    "router_or_gateway",
    "hosted_open_weight_service",
    "enterprise_private_model",
    "local_runtime",
    "open_weight_registry",
    "regional_sovereign_provider",
    "multimodal_media_provider",
    "embedding_provider",
    "fine_tuning_provider",
)

REQUIRED_MODEL_ROUTE_CLASSES = (
    "text_chat",
    "reasoning",
    "long_context",
    "multimodal_vision",
    "image_generation",
    "audio_speech",
    "video_generation",
    "embedding",
    "reranking",
    "code_generation",
    "tool_calling_agent",
    "batch_generation",
    "streaming",
    "fine_tuning",
    "retrieval_augmented",
    "safety_moderation",
    "local_inference",
    "gateway_router",
)

REQUIRED_MODEL_LIFECYCLE_EVENTS = (
    "model_added",
    "version_updated",
    "alias_changed",
    "capability_changed",
    "context_limit_changed",
    "price_or_meter_changed",
    "region_availability_changed",
    "safety_policy_changed",
    "deprecation_announced",
    "model_removed",
    "provider_owner_changed",
    "endpoint_protocol_changed",
)

REQUIRED_NEGATIVE_REGISTRY_FAILURES = (
    "unregistered_provider_route",
    "unknown_model_alias",
    "stale_catalog_snapshot",
    "catalog_source_unreachable",
    "adapter_manifest_missing",
    "capability_overclaim",
    "modality_mismatch",
    "context_window_mismatch",
    "price_or_meter_unbound",
    "hosted_open_weight_service_drift",
    "router_silent_fallback",
    "private_model_without_attestation",
    "lifecycle_deprecation_ignored",
    "private_payload_in_registry_entry",
)

DECLARED_HASH_FIELDS = (
    "universal_model_provider_registry_hash",
    "universal_provider_onboarding_migration_covenant_hash",
    "catalog_snapshot_hash",
    "registry_source_hash",
    "namespace_hash",
    "model_route_hash",
    "model_identity_hash",
    "service_object_hash",
    "adapter_manifest_hash",
    "capability_manifest_hash",
    "modality_manifest_hash",
    "pricing_meter_hash",
    "context_limit_hash",
    "lifecycle_event_hash",
    "conformance_receipt_hash",
    "source_footer_contract_hash",
    "settlement_meter_hash",
    "verifier_hash",
    "fixture_hash",
    "attestation_hash",
    "evidence_hash",
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
    "customer_id",
    "customer_email",
    "tenant_id",
    "billing_record",
    "private_model_weights",
    "private_fine_tune_data",
    "registry_payload_text",
    "catalog_export_text",
    "tool_payload",
    "api_key",
    "access_token",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_model_provider_registry_input(path: str | Path) -> dict[str, Any]:
    """Load private replay input for an L176 model/provider registry."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_registry(registry: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in registry.items()
        if key not in {"universal_model_provider_registry_hash", "signature"}
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
    for field in DECLARED_HASH_FIELDS:
        if artifact.get(field):
            return hash_payload(_hashable_artifact(artifact)) == artifact[field]
    return True


def _summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    summary = artifact.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def _provider_onboarding_ready(artifact: dict[str, Any] | None) -> bool:
    summary = _summary(artifact)
    decision = artifact.get("onboarding_decision", {}) if artifact else {}
    return (
        summary.get("status") == "ready"
        and summary.get("target_certification_level") == MINIMUM_PROVIDER_ONBOARDING_LEVEL
        and decision.get("provider_onboarding_ready") is True
        and decision.get("legacy_routes_blocked") is True
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


def _registry_source_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("registry_source_hash")),
            _string(row.get("catalog_snapshot_hash")),
            _string(row.get("schema_hash")),
            _string(row.get("fetch_verifier_hash")),
            _string(row.get("freshness_sla_hash")),
            _bool(row.get("source_available")),
            _bool(row.get("snapshot_signed")),
            _bool(row.get("supports_model_ids")),
            _bool(row.get("supports_capability_metadata")),
            _bool(row.get("supports_lifecycle_events")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _namespace_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("namespace_hash")),
            _string(row.get("owner_attestation_hash")),
            _string(row.get("adapter_policy_hash")),
            _bool(row.get("namespace_unique")),
            _bool(row.get("publisher_identity_bound")),
            _bool(row.get("hosting_provider_bound")),
            _bool(row.get("route_ids_globally_unique")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _route_class_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("model_route_hash")),
            _string(row.get("capability_manifest_hash")),
            _string(row.get("modality_manifest_hash")),
            _string(row.get("context_limit_hash")),
            _string(row.get("pricing_meter_hash")),
            _bool(row.get("source_footer_required")),
            _bool(row.get("machine_readable_sources_required")),
            _bool(row.get("settlement_meter_required")),
            _bool(row.get("negative_fixture_required")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _adapter_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("adapter_manifest_hash")),
            _string(row.get("schema_hash")),
            _string(row.get("verifier_hash")),
            _string(row.get("source_footer_contract_hash")),
            _string(row.get("conformance_receipt_hash")),
            _bool(row.get("adapter_discoverable")),
            _bool(row.get("maps_native_request_response")),
            _bool(row.get("maps_streaming_final_event")),
            _bool(row.get("maps_tool_and_batch_outputs")),
            _bool(row.get("conformance_green")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _lifecycle_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("lifecycle_event_hash")),
            _string(row.get("catalog_snapshot_hash")),
            _string(row.get("notification_hash")),
            _string(row.get("migration_policy_hash")),
            _bool(row.get("event_supported")),
            _bool(row.get("breaks_reliance_on_stale_state")),
            _bool(row.get("blocks_settlement_on_unhandled_event")),
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
            _bool(row.get("provider_claim_blocked")),
            _bool(row.get("route_registration_blocked")),
            _bool(row.get("settlement_held")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _declared_route_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "route_id",
        "provider_namespace",
        "registry_source",
        "model_route_class",
        "model_identity_hash",
        "service_object_hash",
        "catalog_snapshot_hash",
        "adapter_manifest_hash",
        "conformance_receipt_hash",
        "source_footer_contract_hash",
        "settlement_meter_hash",
        "lifecycle_state_hash",
    )
    required_bools = (
        "registered",
        "adapter_discoverable",
        "capability_metadata_complete",
        "modalities_declared",
        "context_limit_declared",
        "pricing_meter_bound",
        "source_footer_supported",
        "machine_readable_sources_supported",
        "settlement_meter_bound",
        "conformance_green",
        "lifecycle_state_current",
        "no_private_payloads",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _route_id(row: dict[str, Any], fallback: str) -> str:
    return _string(row.get("route_id")) or fallback


def _route_ids(route_rows: list[dict[str, Any]]) -> list[str]:
    return [_route_id(row, f"route:{index}") for index, row in enumerate(route_rows)]


def _routes_registered(
    route_rows: list[dict[str, Any]],
    registry_source_rows: dict[str, dict[str, Any]],
    namespace_rows: dict[str, dict[str, Any]],
    route_class_rows: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str], list[str], list[str]]:
    incomplete: list[str] = []
    missing_sources: list[str] = []
    missing_namespaces: list[str] = []
    missing_route_classes: list[str] = []
    source_keys = set(registry_source_rows)
    namespace_keys = set(namespace_rows)
    route_class_keys = set(route_class_rows)
    for index, row in enumerate(route_rows):
        route_id = _route_id(row, f"route:{index}")
        if not _declared_route_ready(row):
            incomplete.append(route_id)
        if row.get("registry_source") not in source_keys:
            missing_sources.append(route_id)
        if row.get("provider_namespace") not in namespace_keys:
            missing_namespaces.append(route_id)
        if row.get("model_route_class") not in route_class_keys:
            missing_route_classes.append(route_id)
    return incomplete, missing_sources, missing_namespaces, missing_route_classes


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


def _public_route_rows(route_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    public_rows: list[dict[str, Any]] = []
    for index, row in enumerate(route_rows):
        public_rows.append(
            {
                "route_id": _route_id(row, f"route:{index}"),
                "provider_namespace": _string(row.get("provider_namespace")),
                "registry_source": _string(row.get("registry_source")),
                "model_route_class": _string(row.get("model_route_class")),
                "endpoint_protocol": _string(row.get("endpoint_protocol")),
                "model_identity_hash": _string(row.get("model_identity_hash")),
                "service_object_hash": _string(row.get("service_object_hash")),
                "catalog_snapshot_hash": _string(row.get("catalog_snapshot_hash")),
                "adapter_manifest_hash": _string(row.get("adapter_manifest_hash")),
                "conformance_receipt_hash": _string(row.get("conformance_receipt_hash")),
                "source_footer_contract_hash": _string(
                    row.get("source_footer_contract_hash")
                ),
                "settlement_meter_hash": _string(row.get("settlement_meter_hash")),
                "lifecycle_state_hash": _string(row.get("lifecycle_state_hash")),
                "registered": _bool(row.get("registered")),
                "adapter_discoverable": _bool(row.get("adapter_discoverable")),
                "capability_metadata_complete": _bool(
                    row.get("capability_metadata_complete")
                ),
                "modalities_declared": _bool(row.get("modalities_declared")),
                "context_limit_declared": _bool(row.get("context_limit_declared")),
                "pricing_meter_bound": _bool(row.get("pricing_meter_bound")),
                "source_footer_supported": _bool(row.get("source_footer_supported")),
                "machine_readable_sources_supported": _bool(
                    row.get("machine_readable_sources_supported")
                ),
                "settlement_meter_bound": _bool(row.get("settlement_meter_bound")),
                "conformance_green": _bool(row.get("conformance_green")),
                "lifecycle_state_current": _bool(row.get("lifecycle_state_current")),
                "no_private_payloads": _bool(row.get("no_private_payloads")),
            }
        )
    return sorted(public_rows, key=lambda item: item["route_id"])


def make_universal_model_provider_registry(
    registry_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L176 universal model/provider registry."""

    onboarding_covenant = registry_input.get(
        "universal_provider_onboarding_migration_covenant"
    )
    registry_source_rows = _row_map(registry_input, "registry_source_rows")
    namespace_rows = _row_map(registry_input, "provider_namespace_rows")
    route_class_rows = _row_map(registry_input, "model_route_class_rows")
    adapter_rows = _row_map(registry_input, "adapter_discovery_rows")
    lifecycle_rows = _row_map(registry_input, "lifecycle_event_rows")
    negative_rows = _row_map(registry_input, "negative_registry_rows")
    declared_routes = _list_rows(registry_input, "declared_model_routes")

    missing_sources, incomplete_sources = _complete_rows(
        registry_source_rows,
        REQUIRED_REGISTRY_SOURCES,
        _registry_source_row_ready,
    )
    missing_namespaces, incomplete_namespaces = _complete_rows(
        namespace_rows,
        REQUIRED_PROVIDER_NAMESPACE_CLASSES,
        _namespace_row_ready,
    )
    missing_route_classes, incomplete_route_classes = _complete_rows(
        route_class_rows,
        REQUIRED_MODEL_ROUTE_CLASSES,
        _route_class_row_ready,
    )
    missing_adapters, incomplete_adapters = _complete_rows(
        adapter_rows,
        REQUIRED_MODEL_ROUTE_CLASSES,
        _adapter_row_ready,
    )
    missing_lifecycle, incomplete_lifecycle = _complete_rows(
        lifecycle_rows,
        REQUIRED_MODEL_LIFECYCLE_EVENTS,
        _lifecycle_row_ready,
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows,
        REQUIRED_NEGATIVE_REGISTRY_FAILURES,
        _negative_row_ready,
    )
    (
        incomplete_declared_routes,
        routes_missing_sources,
        routes_missing_namespaces,
        routes_missing_classes,
    ) = _routes_registered(
        declared_routes,
        registry_source_rows,
        namespace_rows,
        route_class_rows,
    )

    route_ids = _route_ids(declared_routes)
    duplicate_route_ids = sorted(
        route_id for route_id in set(route_ids) if route_ids.count(route_id) > 1
    )

    checks = {
        "provider_onboarding_covenant_bound": _artifact_hash_is_reproducible(
            onboarding_covenant if isinstance(onboarding_covenant, dict) else None
        ),
        "provider_onboarding_covenant_l175_ready": _provider_onboarding_ready(
            onboarding_covenant if isinstance(onboarding_covenant, dict) else None
        ),
        "registry_source_rows_complete": not missing_sources
        and not incomplete_sources,
        "provider_namespace_rows_complete": not missing_namespaces
        and not incomplete_namespaces,
        "model_route_class_rows_complete": not missing_route_classes
        and not incomplete_route_classes,
        "adapter_discovery_rows_complete": not missing_adapters
        and not incomplete_adapters,
        "lifecycle_event_rows_complete": not missing_lifecycle
        and not incomplete_lifecycle,
        "declared_model_routes_present": bool(declared_routes),
        "declared_model_routes_registered": not incomplete_declared_routes
        and not routes_missing_sources
        and not routes_missing_namespaces
        and not routes_missing_classes
        and not duplicate_route_ids,
        "negative_registry_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "registry_signed": signing_secret is not None,
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    ready = not failure_modes

    registry_source_root = merkle_root([
        hash_payload({"name": name, "row": registry_source_rows.get(name, {})})
        for name in REQUIRED_REGISTRY_SOURCES
    ])
    namespace_root = merkle_root([
        hash_payload({"name": name, "row": namespace_rows.get(name, {})})
        for name in REQUIRED_PROVIDER_NAMESPACE_CLASSES
    ])
    route_class_root = merkle_root([
        hash_payload({"name": name, "row": route_class_rows.get(name, {})})
        for name in REQUIRED_MODEL_ROUTE_CLASSES
    ])
    adapter_root = merkle_root([
        hash_payload({"name": name, "row": adapter_rows.get(name, {})})
        for name in REQUIRED_MODEL_ROUTE_CLASSES
    ])
    lifecycle_root = merkle_root([
        hash_payload({"name": name, "row": lifecycle_rows.get(name, {})})
        for name in REQUIRED_MODEL_LIFECYCLE_EVENTS
    ])
    declared_route_root = merkle_root([
        hash_payload({"route_id": _route_id(row, f"route:{index}"), "row": row})
        for index, row in enumerate(declared_routes)
    ])
    negative_root = merkle_root([
        hash_payload({"name": name, "row": negative_rows.get(name, {})})
        for name in REQUIRED_NEGATIVE_REGISTRY_FAILURES
    ])

    public = {
        "universal_model_provider_registry_version": (
            UNIVERSAL_MODEL_PROVIDER_REGISTRY_VERSION
        ),
        "schema": UNIVERSAL_MODEL_PROVIDER_REGISTRY_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": "rdllm-universal-model-provider-registry-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_provider_onboarding_level": MINIMUM_PROVIDER_ONBOARDING_LEVEL,
            "all_model_routes_must_be_registered": True,
            "model_service_object_is_operational_unit": True,
            "catalog_drift_blocks_reliance": True,
            "unregistered_routes_fail_closed": True,
            "private_payloads_forbidden_in_public_registry": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_MODEL_PROVIDER_REGISTRY_VERSION,
        },
        "provider_onboarding_covenant_binding": {
            "present": isinstance(onboarding_covenant, dict),
            "artifact_hash": _declared_hash(
                onboarding_covenant if isinstance(onboarding_covenant, dict) else None
            ),
            "payload_hash": hash_payload(
                _hashable_artifact(
                    onboarding_covenant
                    if isinstance(onboarding_covenant, dict)
                    else None
                )
            ),
            "hash_reproducible": checks["provider_onboarding_covenant_bound"],
            "status": _summary(
                onboarding_covenant if isinstance(onboarding_covenant, dict) else None
            ).get("status", ""),
            "level": _summary(
                onboarding_covenant if isinstance(onboarding_covenant, dict) else None
            ).get("target_certification_level", ""),
        },
        "registry_source_rows": {
            name: registry_source_rows.get(name, {}) for name in REQUIRED_REGISTRY_SOURCES
        },
        "provider_namespace_rows": {
            name: namespace_rows.get(name, {})
            for name in REQUIRED_PROVIDER_NAMESPACE_CLASSES
        },
        "model_route_class_rows": {
            name: route_class_rows.get(name, {}) for name in REQUIRED_MODEL_ROUTE_CLASSES
        },
        "adapter_discovery_rows": {
            name: adapter_rows.get(name, {}) for name in REQUIRED_MODEL_ROUTE_CLASSES
        },
        "lifecycle_event_rows": {
            name: lifecycle_rows.get(name, {}) for name in REQUIRED_MODEL_LIFECYCLE_EVENTS
        },
        "declared_model_routes": _public_route_rows(declared_routes),
        "negative_registry_rows": {
            name: negative_rows.get(name, {})
            for name in REQUIRED_NEGATIVE_REGISTRY_FAILURES
        },
        "evidence_roots": {
            "registry_source_root": registry_source_root,
            "provider_namespace_root": namespace_root,
            "model_route_class_root": route_class_root,
            "adapter_discovery_root": adapter_root,
            "lifecycle_event_root": lifecycle_root,
            "declared_model_route_root": declared_route_root,
            "negative_registry_root": negative_root,
            "combined_registry_root": merkle_root(
                [
                    registry_source_root,
                    namespace_root,
                    route_class_root,
                    adapter_root,
                    lifecycle_root,
                    declared_route_root,
                    negative_root,
                ]
            ),
        },
        "checks": checks,
        "registry_decision": {
            "universal_model_provider_registry_ready": ready,
            "any_model_claim_allowed": ready,
            "dynamic_provider_admission_allowed": ready,
            "declared_model_routes_claimable": ready,
            "unregistered_routes_blocked": True,
            "catalog_drift_blocks_reliance": True,
            "source_footer_required_for_all_routes": True,
            "settlement_release_allowed": ready,
            "failure_modes": failure_modes,
        },
        "coverage": {
            "missing_registry_sources": missing_sources,
            "incomplete_registry_sources": incomplete_sources,
            "missing_provider_namespaces": missing_namespaces,
            "incomplete_provider_namespaces": incomplete_namespaces,
            "missing_model_route_classes": missing_route_classes,
            "incomplete_model_route_classes": incomplete_route_classes,
            "missing_adapter_discovery_rows": missing_adapters,
            "incomplete_adapter_discovery_rows": incomplete_adapters,
            "missing_lifecycle_events": missing_lifecycle,
            "incomplete_lifecycle_events": incomplete_lifecycle,
            "incomplete_declared_model_routes": incomplete_declared_routes,
            "routes_missing_registry_source": routes_missing_sources,
            "routes_missing_provider_namespace": routes_missing_namespaces,
            "routes_missing_model_route_class": routes_missing_classes,
            "duplicate_declared_route_ids": duplicate_route_ids,
            "missing_negative_registry_failures": missing_negative,
            "incomplete_negative_registry_failures": incomplete_negative,
        },
        "privacy": {
            "private_payloads_excluded": True,
            "private_prompts_excluded": True,
            "private_model_weights_excluded": True,
            "private_catalog_exports_excluded": True,
            "public_registry_uses_hashes_and_metadata": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_provider_onboarding_level": MINIMUM_PROVIDER_ONBOARDING_LEVEL,
            "registry_source_count": len(REQUIRED_REGISTRY_SOURCES),
            "ready_registry_source_count": len(REQUIRED_REGISTRY_SOURCES)
            - len(missing_sources)
            - len(incomplete_sources),
            "provider_namespace_count": len(REQUIRED_PROVIDER_NAMESPACE_CLASSES),
            "ready_provider_namespace_count": len(REQUIRED_PROVIDER_NAMESPACE_CLASSES)
            - len(missing_namespaces)
            - len(incomplete_namespaces),
            "model_route_class_count": len(REQUIRED_MODEL_ROUTE_CLASSES),
            "ready_model_route_class_count": len(REQUIRED_MODEL_ROUTE_CLASSES)
            - len(missing_route_classes)
            - len(incomplete_route_classes),
            "adapter_discovery_count": len(REQUIRED_MODEL_ROUTE_CLASSES),
            "ready_adapter_discovery_count": len(REQUIRED_MODEL_ROUTE_CLASSES)
            - len(missing_adapters)
            - len(incomplete_adapters),
            "lifecycle_event_count": len(REQUIRED_MODEL_LIFECYCLE_EVENTS),
            "ready_lifecycle_event_count": len(REQUIRED_MODEL_LIFECYCLE_EVENTS)
            - len(missing_lifecycle)
            - len(incomplete_lifecycle),
            "declared_model_route_count": len(declared_routes),
            "ready_declared_model_route_count": len(declared_routes)
            - len(set(incomplete_declared_routes)),
            "negative_registry_failure_count": len(REQUIRED_NEGATIVE_REGISTRY_FAILURES),
            "ready_negative_registry_failure_count": len(
                REQUIRED_NEGATIVE_REGISTRY_FAILURES
            )
            - len(missing_negative)
            - len(incomplete_negative),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": True,
            "signed_model_provider_registry": signing_secret is not None,
        },
    }
    public["universal_model_provider_registry_hash"] = hash_payload(
        _hashable_registry(public)
    )
    public["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_registry(public), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return public


def validate_universal_model_provider_registry_shape(
    registry: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for an L176 model/provider registry."""

    errors: list[str] = []
    required = (
        "universal_model_provider_registry_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "provider_onboarding_covenant_binding",
        "registry_source_rows",
        "provider_namespace_rows",
        "model_route_class_rows",
        "adapter_discovery_rows",
        "lifecycle_event_rows",
        "declared_model_routes",
        "negative_registry_rows",
        "evidence_roots",
        "checks",
        "registry_decision",
        "coverage",
        "privacy",
        "summary",
        "universal_model_provider_registry_hash",
    )
    for key in required:
        if key not in registry:
            errors.append(f"missing model provider registry field: {key}")
    if registry.get("universal_model_provider_registry_version") != (
        UNIVERSAL_MODEL_PROVIDER_REGISTRY_VERSION
    ):
        errors.append("unexpected universal_model_provider_registry_version")
    if registry.get("schema") != UNIVERSAL_MODEL_PROVIDER_REGISTRY_SCHEMA:
        errors.append("unexpected model provider registry schema")
    for name in REQUIRED_REGISTRY_SOURCES:
        if name not in registry.get("registry_source_rows", {}):
            errors.append(f"missing registry source row: {name}")
    for name in REQUIRED_PROVIDER_NAMESPACE_CLASSES:
        if name not in registry.get("provider_namespace_rows", {}):
            errors.append(f"missing provider namespace row: {name}")
    for name in REQUIRED_MODEL_ROUTE_CLASSES:
        if name not in registry.get("model_route_class_rows", {}):
            errors.append(f"missing model route class row: {name}")
        if name not in registry.get("adapter_discovery_rows", {}):
            errors.append(f"missing adapter discovery row: {name}")
    for name in REQUIRED_MODEL_LIFECYCLE_EVENTS:
        if name not in registry.get("lifecycle_event_rows", {}):
            errors.append(f"missing lifecycle event row: {name}")
    for name in REQUIRED_NEGATIVE_REGISTRY_FAILURES:
        if name not in registry.get("negative_registry_rows", {}):
            errors.append(f"missing negative registry row: {name}")
    for check in (
        "provider_onboarding_covenant_bound",
        "provider_onboarding_covenant_l175_ready",
        "registry_source_rows_complete",
        "provider_namespace_rows_complete",
        "model_route_class_rows_complete",
        "adapter_discovery_rows_complete",
        "lifecycle_event_rows_complete",
        "declared_model_routes_present",
        "declared_model_routes_registered",
        "negative_registry_fixtures_reject",
        "registry_signed",
    ):
        if check not in registry.get("checks", {}):
            errors.append(f"missing model provider registry check: {check}")
    return errors


def verify_universal_model_provider_registry(
    registry_input: dict[str, Any],
    registry: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L176 model/provider registry against replay input."""

    errors = validate_universal_model_provider_registry_shape(registry)
    expected_hash = hash_payload(_hashable_registry(registry))
    if registry.get("universal_model_provider_registry_hash") != expected_hash:
        errors.append("universal_model_provider_registry_hash mismatch")
    private_fields = _contains_private_fields(registry)
    if private_fields:
        errors.append(
            "model provider registry exposes private fields: "
            + ", ".join(private_fields)
        )
    if not _private_strings_absent(registry, registry_input):
        errors.append("model provider registry exposes private input strings")
    replayed = make_universal_model_provider_registry(
        registry_input,
        issuer=registry.get("issuer", DEFAULT_ISSUER),
        created_at=registry.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get("universal_model_provider_registry_hash") != registry.get(
        "universal_model_provider_registry_hash"
    ):
        errors.append("model provider registry does not match replay inputs")
    if registry.get("summary", {}).get("status") != "ready":
        errors.append("model provider registry is not ready")
    if (
        registry.get("registry_decision", {}).get(
            "universal_model_provider_registry_ready"
        )
        is not True
    ):
        errors.append("model provider registry decision is not ready")
    if registry.get("privacy", {}).get("private_payloads_excluded") is not True:
        errors.append("model provider registry privacy is not preserved")
    if signing_secret:
        signature = registry.get("signature", {})
        expected_signature = sign_payload(_hashable_registry(registry), signing_secret)
        if not signature:
            errors.append("model provider registry is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("model provider registry signature is invalid")
    return errors
