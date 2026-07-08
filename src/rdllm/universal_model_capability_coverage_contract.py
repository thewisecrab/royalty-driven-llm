"""Universal model capability coverage contracts.

The L181 layer closes the gap between model/route coverage and capability-level
operation. A provider can have a catalog-covered model route and still expose
untested feature surfaces such as realtime audio, image generation, embeddings,
reranking, tool use, code execution, or batch jobs. L181 requires every declared
model capability and modality pair to map to tested RDLLM behavior before
model invocation, source-footer reliance, response release, or creator
settlement can be claimed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_MODEL_CAPABILITY_COVERAGE_CONTRACT_VERSION = (
    "rdllm-universal-model-capability-coverage-contract/v1"
)
UNIVERSAL_MODEL_CAPABILITY_COVERAGE_CONTRACT_SCHEMA = (
    "docs/schemas/universal_model_capability_coverage_contract.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L181"
MINIMUM_MODEL_PROVIDER_REGISTRY_LEVEL = "RDLLM-L176"
MINIMUM_PROVIDER_CATALOG_COVERAGE_LEVEL = "RDLLM-L178"
MINIMUM_RUNTIME_ROUTE_BINDING_LEVEL = "RDLLM-L179"
MINIMUM_VERIFIED_SOURCE_FOOTER_LEVEL = "RDLLM-L180"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-model-capability-coverage-contract.json"
)

REQUIRED_MODEL_CAPABILITY_CLASSES = (
    "text_generation",
    "reasoning",
    "long_context",
    "structured_output",
    "tool_calling",
    "agentic_tool_use",
    "retrieval_grounding",
    "web_search",
    "code_generation",
    "code_execution",
    "computer_use",
    "vision_input",
    "image_generation",
    "image_editing",
    "audio_input",
    "speech_output",
    "transcription",
    "realtime_multimodal",
    "video_generation",
    "embedding",
    "reranking",
    "fine_tuning",
    "batch_async",
    "safety_moderation",
)

REQUIRED_MODALITY_PAIRS = (
    "text_to_text",
    "text_image_to_text",
    "audio_to_text",
    "text_to_audio",
    "audio_to_audio",
    "text_to_image",
    "image_to_image",
    "text_image_to_image",
    "text_to_video",
    "image_to_video",
    "text_to_embedding",
    "image_to_embedding",
    "text_to_score",
    "multimodal_to_tool_call",
)

REQUIRED_OPERATION_SURFACES = (
    "sync_api",
    "streaming_api",
    "realtime_session",
    "batch_api",
    "tool_callback",
    "server_tool",
    "client_tool",
    "files_api",
    "fine_tuning_job",
    "embedding_endpoint",
    "rerank_endpoint",
    "moderation_endpoint",
    "image_endpoint",
    "audio_endpoint",
    "video_endpoint",
    "local_runtime",
)

REQUIRED_NEGATIVE_CAPABILITY_FAILURES = (
    "declared_capability_without_fixture",
    "catalog_capability_not_in_registry",
    "modality_pair_uncovered",
    "structured_output_schema_not_bound",
    "tool_call_without_source_context",
    "server_tool_unattributed",
    "computer_use_unattested",
    "web_search_without_verified_sources",
    "image_generation_without_media_attribution",
    "audio_transcription_without_source_boundary",
    "realtime_session_missing_final_footer",
    "embedding_without_attribution_policy",
    "rerank_score_without_source_binding",
    "fine_tune_route_without_lineage",
    "batch_job_strips_capability_receipt",
    "safety_moderation_bypasses_meter",
    "capability_downgrade_after_admission",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_model_capability_coverage_contract_hash",
    "universal_model_provider_registry_hash",
    "universal_provider_catalog_coverage_contract_hash",
    "universal_runtime_route_binding_contract_hash",
    "universal_verified_source_footer_contract_hash",
    "capability_hash",
    "schema_hash",
    "fixture_hash",
    "verifier_hash",
    "modality_pair_hash",
    "input_schema_hash",
    "output_schema_hash",
    "surface_hash",
    "adapter_hash",
    "runtime_verifier_hash",
    "telemetry_span_hash",
    "route_capability_hash",
    "catalog_entry_hash",
    "model_identity_hash",
    "runtime_route_binding_hash",
    "verified_footer_hash",
    "capability_fixture_hash",
    "capability_manifest_hash",
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
    "raw_answer_text",
    "output_text",
    "raw_output",
    "raw_model_output",
    "rendered_output",
    "source_text",
    "document_text",
    "full_source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "claim_text",
    "raw_claim",
    "reasoning",
    "chain_of_thought",
    "retrieval_payload",
    "tool_payload",
    "raw_tool_output",
    "raw_native_request",
    "raw_native_response",
    "native_response_body",
    "streaming_transcript",
    "audio_payload",
    "image_payload",
    "video_payload",
    "embedding_vector",
    "fine_tune_dataset",
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
    "model_capability_rows": set(REQUIRED_MODEL_CAPABILITY_CLASSES),
    "modality_pair_rows": set(REQUIRED_MODALITY_PAIRS),
    "operation_surface_rows": set(REQUIRED_OPERATION_SURFACES),
    "negative_capability_rows": set(REQUIRED_NEGATIVE_CAPABILITY_FAILURES),
}


def load_universal_model_capability_coverage_contract_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L181 capability coverage contract."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in contract.items()
        if key not in {"universal_model_capability_coverage_contract_hash", "signature"}
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


def _model_provider_registry_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("registry_decision", {}) if artifact else {}
    return (
        _summary(artifact).get("status") == "ready"
        and _artifact_level(artifact) == MINIMUM_MODEL_PROVIDER_REGISTRY_LEVEL
        and decision.get("universal_model_provider_registry_ready") is True
        and decision.get("unregistered_routes_blocked") is True
    )


def _provider_catalog_coverage_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("catalog_coverage_decision", {}) if artifact else {}
    return (
        _summary(artifact).get("status") == "ready"
        and _artifact_level(artifact) == MINIMUM_PROVIDER_CATALOG_COVERAGE_LEVEL
        and decision.get("universal_provider_catalog_coverage_ready") is True
        and decision.get("catalog_exhaustiveness_attested") is True
        and decision.get("unknown_catalog_models_blocked") is True
    )


def _runtime_route_binding_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("runtime_route_binding_decision", {}) if artifact else {}
    return (
        _summary(artifact).get("status") == "ready"
        and _artifact_level(artifact) == MINIMUM_RUNTIME_ROUTE_BINDING_LEVEL
        and decision.get("universal_runtime_route_binding_ready") is True
        and decision.get("response_release_allowed") is True
        and decision.get("source_footer_reliance_allowed") is True
    )


def _verified_source_footer_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("source_footer_reliance_decision", {}) if artifact else {}
    return (
        _summary(artifact).get("status") == "ready"
        and _artifact_level(artifact) == MINIMUM_VERIFIED_SOURCE_FOOTER_LEVEL
        and decision.get("universal_verified_source_footer_ready") is True
        and decision.get("user_source_footer_reliance_allowed") is True
        and decision.get("response_release_allowed") is True
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


def _capability_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "capability_hash",
        "schema_hash",
        "fixture_hash",
        "verifier_hash",
    )
    required_bools = (
        "catalog_declared",
        "registry_supported",
        "runtime_route_bound",
        "footer_or_abstention_bound",
        "settlement_meter_bound",
        "negative_fixture_covered",
        "fail_closed",
        "no_private_payloads",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _modality_pair_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "modality_pair_hash",
        "input_schema_hash",
        "output_schema_hash",
        "verifier_hash",
    )
    required_bools = (
        "input_modalities_bound",
        "output_modalities_bound",
        "source_boundary_bound",
        "attribution_policy_bound",
        "privacy_safe",
        "fail_closed",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _operation_surface_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "surface_hash",
        "adapter_hash",
        "runtime_verifier_hash",
        "telemetry_span_hash",
    )
    required_bools = (
        "available_if_declared",
        "rdllm_headers_or_metadata_bound",
        "stream_or_callback_finalized",
        "source_footer_or_abstention_preserved",
        "settlement_meter_bound",
        "fail_closed",
        "no_private_payloads",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _route_capability_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "route_id",
        "capability_name",
        "route_capability_hash",
        "catalog_entry_hash",
        "model_identity_hash",
        "runtime_route_binding_hash",
        "verified_footer_hash",
        "capability_fixture_hash",
        "verifier_hash",
    )
    required_bools = (
        "catalog_capability_declared",
        "registry_route_supported",
        "runtime_route_matched",
        "capability_fixture_passed",
        "modality_pair_covered",
        "operation_surface_covered",
        "source_footer_or_abstention_enforced",
        "settlement_meter_bound",
        "no_private_payloads",
    )
    return (
        all(_string(row.get(field)) for field in required_strings)
        and row.get("capability_name") in REQUIRED_MODEL_CAPABILITY_CLASSES
        and all(_bool(row.get(field)) for field in required_bools)
    )


def _negative_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("fixture_hash")),
            _string(row.get("verifier_hash")),
            _bool(row.get("expected_reject")),
            _bool(row.get("observed_reject")),
            _bool(row.get("capability_invocation_blocked")),
            _bool(row.get("response_release_blocked")),
            _bool(row.get("source_footer_reliance_blocked")),
            _bool(row.get("settlement_held")),
            _bool(row.get("public_status_marked_failed")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _catalog_admitted_route_ids(catalog_coverage: dict[str, Any] | None) -> list[str]:
    if not isinstance(catalog_coverage, dict):
        return []
    route_rows = catalog_coverage.get("registry_route_coverage_rows", {})
    if isinstance(route_rows, dict) and route_rows:
        return sorted(
            str(route_id)
            for route_id, row in route_rows.items()
            if isinstance(row, dict)
            and row.get("l176_route_present") is True
            and row.get("l177_route_enforced") is True
            and row.get("discovered_or_exempted") is True
        )
    discovered_rows = catalog_coverage.get("discovered_model_rows", [])
    if isinstance(discovered_rows, list):
        route_ids: list[str] = []
        for row in discovered_rows:
            if not isinstance(row, dict):
                continue
            if row.get("l176_route_registered") is not True:
                continue
            if row.get("l177_footer_enforced") is not True:
                continue
            route_id = row.get("normalized_route_id")
            if isinstance(route_id, str) and route_id:
                route_ids.append(route_id)
        return sorted(set(route_ids))
    return []


def _route_capability_rows_complete(
    rows: dict[str, dict[str, Any]],
    required_route_ids: list[str],
) -> tuple[list[str], list[str], list[str], list[str]]:
    missing = [route_id for route_id in required_route_ids if route_id not in rows]
    incomplete = [
        route_id
        for route_id in required_route_ids
        if route_id in rows and not _route_capability_row_ready(rows[route_id])
    ]
    mismatched = [
        route_id
        for route_id in required_route_ids
        if route_id in rows and rows[route_id].get("route_id") != route_id
    ]
    unsupported_capabilities = [
        route_id
        for route_id in required_route_ids
        if route_id in rows
        and rows[route_id].get("capability_name")
        not in REQUIRED_MODEL_CAPABILITY_CLASSES
    ]
    if not required_route_ids:
        missing.append("at_least_one_catalog_covered_route")
    return missing, incomplete, mismatched, unsupported_capabilities


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


def make_universal_model_capability_coverage_contract(
    contract_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L181 universal model capability coverage contract."""

    model_provider_registry = contract_input.get("universal_model_provider_registry")
    provider_catalog_coverage = contract_input.get(
        "universal_provider_catalog_coverage_contract"
    )
    runtime_route_binding = contract_input.get("universal_runtime_route_binding_contract")
    verified_source_footer = contract_input.get(
        "universal_verified_source_footer_contract"
    )

    capability_rows = _row_map(contract_input, "model_capability_rows")
    modality_pair_rows = _row_map(contract_input, "modality_pair_rows")
    operation_surface_rows = _row_map(contract_input, "operation_surface_rows")
    route_capability_rows = _row_map(contract_input, "route_capability_rows")
    negative_rows = _row_map(contract_input, "negative_capability_rows")

    missing_capabilities, incomplete_capabilities = _complete_rows(
        capability_rows,
        REQUIRED_MODEL_CAPABILITY_CLASSES,
        _capability_row_ready,
    )
    missing_modalities, incomplete_modalities = _complete_rows(
        modality_pair_rows,
        REQUIRED_MODALITY_PAIRS,
        _modality_pair_row_ready,
    )
    missing_surfaces, incomplete_surfaces = _complete_rows(
        operation_surface_rows,
        REQUIRED_OPERATION_SURFACES,
        _operation_surface_row_ready,
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows,
        REQUIRED_NEGATIVE_CAPABILITY_FAILURES,
        _negative_row_ready,
    )

    required_route_ids = _catalog_admitted_route_ids(
        provider_catalog_coverage
        if isinstance(provider_catalog_coverage, dict)
        else None
    )
    (
        missing_route_capabilities,
        incomplete_route_capabilities,
        mismatched_route_capabilities,
        unsupported_route_capabilities,
    ) = _route_capability_rows_complete(route_capability_rows, required_route_ids)

    registry_ready = _model_provider_registry_ready(
        model_provider_registry if isinstance(model_provider_registry, dict) else None
    )
    catalog_ready = _provider_catalog_coverage_ready(
        provider_catalog_coverage
        if isinstance(provider_catalog_coverage, dict)
        else None
    )
    runtime_ready = _runtime_route_binding_ready(
        runtime_route_binding if isinstance(runtime_route_binding, dict) else None
    )
    footer_ready = _verified_source_footer_ready(
        verified_source_footer if isinstance(verified_source_footer, dict) else None
    )

    checks = {
        "model_provider_registry_l176_ready": registry_ready
        and _artifact_hash_is_reproducible(
            model_provider_registry
            if isinstance(model_provider_registry, dict)
            else None
        ),
        "provider_catalog_coverage_l178_ready": catalog_ready
        and _artifact_hash_is_reproducible(
            provider_catalog_coverage
            if isinstance(provider_catalog_coverage, dict)
            else None
        ),
        "runtime_route_binding_l179_ready": runtime_ready
        and _artifact_hash_is_reproducible(
            runtime_route_binding
            if isinstance(runtime_route_binding, dict)
            else None
        ),
        "verified_source_footer_l180_ready": footer_ready
        and _artifact_hash_is_reproducible(
            verified_source_footer
            if isinstance(verified_source_footer, dict)
            else None
        ),
        "model_capability_rows_complete": not missing_capabilities
        and not incomplete_capabilities,
        "modality_pair_rows_complete": not missing_modalities
        and not incomplete_modalities,
        "operation_surface_rows_complete": not missing_surfaces
        and not incomplete_surfaces,
        "catalog_covered_route_capability_rows_complete": (
            not missing_route_capabilities
            and not incomplete_route_capabilities
            and not mismatched_route_capabilities
            and not unsupported_route_capabilities
        ),
        "negative_capability_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "contract_signed": signing_secret is not None,
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    ready = not failure_modes

    capability_root = merkle_root([
        hash_payload({"capability": name, "row": capability_rows.get(name, {})})
        for name in REQUIRED_MODEL_CAPABILITY_CLASSES
    ])
    modality_root = merkle_root([
        hash_payload({"modality_pair": name, "row": modality_pair_rows.get(name, {})})
        for name in REQUIRED_MODALITY_PAIRS
    ])
    operation_surface_root = merkle_root([
        hash_payload({"operation_surface": name, "row": operation_surface_rows.get(name, {})})
        for name in REQUIRED_OPERATION_SURFACES
    ])
    route_capability_root = merkle_root([
        hash_payload({"route_id": route_id, "row": route_capability_rows.get(route_id, {})})
        for route_id in required_route_ids
    ])
    negative_root = merkle_root([
        hash_payload({"failure": failure, "row": negative_rows.get(failure, {})})
        for failure in REQUIRED_NEGATIVE_CAPABILITY_FAILURES
    ])

    public = {
        "universal_model_capability_coverage_contract_version": (
            UNIVERSAL_MODEL_CAPABILITY_COVERAGE_CONTRACT_VERSION
        ),
        "schema": UNIVERSAL_MODEL_CAPABILITY_COVERAGE_CONTRACT_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": "rdllm-universal-model-capability-coverage-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_model_provider_registry_level": (
                MINIMUM_MODEL_PROVIDER_REGISTRY_LEVEL
            ),
            "minimum_provider_catalog_coverage_level": (
                MINIMUM_PROVIDER_CATALOG_COVERAGE_LEVEL
            ),
            "minimum_runtime_route_binding_level": (
                MINIMUM_RUNTIME_ROUTE_BINDING_LEVEL
            ),
            "minimum_verified_source_footer_level": (
                MINIMUM_VERIFIED_SOURCE_FOOTER_LEVEL
            ),
            "every_declared_capability_requires_fixture": True,
            "capability_modality_and_operation_surfaces_must_be_bound": True,
            "uncertified_capabilities_fail_closed": True,
            "source_footer_or_abstention_required_per_capability": True,
            "creator_settlement_requires_capability_receipt": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_MODEL_CAPABILITY_COVERAGE_CONTRACT_VERSION,
        },
        "artifact_bindings": {
            "universal_model_provider_registry": _artifact_binding(
                model_provider_registry
                if isinstance(model_provider_registry, dict)
                else None,
                minimum_level=MINIMUM_MODEL_PROVIDER_REGISTRY_LEVEL,
                ready=registry_ready,
            ),
            "universal_provider_catalog_coverage_contract": _artifact_binding(
                provider_catalog_coverage
                if isinstance(provider_catalog_coverage, dict)
                else None,
                minimum_level=MINIMUM_PROVIDER_CATALOG_COVERAGE_LEVEL,
                ready=catalog_ready,
            ),
            "universal_runtime_route_binding_contract": _artifact_binding(
                runtime_route_binding
                if isinstance(runtime_route_binding, dict)
                else None,
                minimum_level=MINIMUM_RUNTIME_ROUTE_BINDING_LEVEL,
                ready=runtime_ready,
            ),
            "universal_verified_source_footer_contract": _artifact_binding(
                verified_source_footer
                if isinstance(verified_source_footer, dict)
                else None,
                minimum_level=MINIMUM_VERIFIED_SOURCE_FOOTER_LEVEL,
                ready=footer_ready,
            ),
        },
        "model_capability_rows": {
            name: capability_rows.get(name, {})
            for name in REQUIRED_MODEL_CAPABILITY_CLASSES
        },
        "modality_pair_rows": {
            name: modality_pair_rows.get(name, {})
            for name in REQUIRED_MODALITY_PAIRS
        },
        "operation_surface_rows": {
            name: operation_surface_rows.get(name, {})
            for name in REQUIRED_OPERATION_SURFACES
        },
        "route_capability_rows": {
            route_id: route_capability_rows.get(route_id, {})
            for route_id in required_route_ids
        },
        "negative_capability_rows": {
            failure: negative_rows.get(failure, {})
            for failure in REQUIRED_NEGATIVE_CAPABILITY_FAILURES
        },
        "evidence_roots": {
            "model_capability_root": capability_root,
            "modality_pair_root": modality_root,
            "operation_surface_root": operation_surface_root,
            "route_capability_root": route_capability_root,
            "negative_capability_root": negative_root,
            "combined_model_capability_coverage_root": merkle_root(
                [
                    capability_root,
                    modality_root,
                    operation_surface_root,
                    route_capability_root,
                    negative_root,
                ]
            ),
        },
        "checks": checks,
        "model_capability_coverage_decision": {
            "universal_model_capability_coverage_ready": ready,
            "all_declared_model_capabilities_covered": ready,
            "model_invocation_allowed": ready,
            "response_release_allowed": ready,
            "source_footer_reliance_allowed": ready,
            "creator_settlement_allowed": ready,
            "uncertified_capability_blocked": True,
            "capability_downgrade_blocked": True,
            "failure_modes": failure_modes,
        },
        "coverage": {
            "catalog_covered_route_ids": required_route_ids,
            "missing_model_capabilities": missing_capabilities,
            "incomplete_model_capabilities": incomplete_capabilities,
            "missing_modality_pairs": missing_modalities,
            "incomplete_modality_pairs": incomplete_modalities,
            "missing_operation_surfaces": missing_surfaces,
            "incomplete_operation_surfaces": incomplete_surfaces,
            "missing_route_capabilities": missing_route_capabilities,
            "incomplete_route_capabilities": incomplete_route_capabilities,
            "mismatched_route_capabilities": mismatched_route_capabilities,
            "unsupported_route_capabilities": unsupported_route_capabilities,
            "missing_negative_capability_failures": missing_negative,
            "incomplete_negative_capability_failures": incomplete_negative,
        },
        "privacy": {
            "private_payloads_excluded": True,
            "private_prompts_excluded": True,
            "private_outputs_excluded": True,
            "private_media_payloads_excluded": True,
            "private_vectors_excluded": True,
            "public_contract_uses_hashes_routes_capabilities_and_modes": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_model_provider_registry_level": (
                MINIMUM_MODEL_PROVIDER_REGISTRY_LEVEL
            ),
            "minimum_provider_catalog_coverage_level": (
                MINIMUM_PROVIDER_CATALOG_COVERAGE_LEVEL
            ),
            "minimum_runtime_route_binding_level": (
                MINIMUM_RUNTIME_ROUTE_BINDING_LEVEL
            ),
            "minimum_verified_source_footer_level": (
                MINIMUM_VERIFIED_SOURCE_FOOTER_LEVEL
            ),
            "model_capability_count": len(REQUIRED_MODEL_CAPABILITY_CLASSES),
            "ready_model_capability_count": len(REQUIRED_MODEL_CAPABILITY_CLASSES)
            - len(missing_capabilities)
            - len(incomplete_capabilities),
            "modality_pair_count": len(REQUIRED_MODALITY_PAIRS),
            "ready_modality_pair_count": len(REQUIRED_MODALITY_PAIRS)
            - len(missing_modalities)
            - len(incomplete_modalities),
            "operation_surface_count": len(REQUIRED_OPERATION_SURFACES),
            "ready_operation_surface_count": len(REQUIRED_OPERATION_SURFACES)
            - len(missing_surfaces)
            - len(incomplete_surfaces),
            "catalog_covered_route_count": len(required_route_ids),
            "ready_route_capability_count": len(required_route_ids)
            - len(missing_route_capabilities)
            - len(incomplete_route_capabilities)
            - len(mismatched_route_capabilities)
            - len(unsupported_route_capabilities),
            "negative_capability_failure_count": len(
                REQUIRED_NEGATIVE_CAPABILITY_FAILURES
            ),
            "ready_negative_capability_failure_count": len(
                REQUIRED_NEGATIVE_CAPABILITY_FAILURES
            )
            - len(missing_negative)
            - len(incomplete_negative),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": True,
            "signed_model_capability_coverage_contract": signing_secret is not None,
        },
    }
    public["universal_model_capability_coverage_contract_hash"] = hash_payload(
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


def validate_universal_model_capability_coverage_contract_shape(
    contract: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for an L181 capability contract."""

    errors: list[str] = []
    required = (
        "universal_model_capability_coverage_contract_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "artifact_bindings",
        "model_capability_rows",
        "modality_pair_rows",
        "operation_surface_rows",
        "route_capability_rows",
        "negative_capability_rows",
        "evidence_roots",
        "checks",
        "model_capability_coverage_decision",
        "coverage",
        "privacy",
        "summary",
        "universal_model_capability_coverage_contract_hash",
    )
    for key in required:
        if key not in contract:
            errors.append(f"missing model capability coverage field: {key}")
    if contract.get("universal_model_capability_coverage_contract_version") != (
        UNIVERSAL_MODEL_CAPABILITY_COVERAGE_CONTRACT_VERSION
    ):
        errors.append("unexpected universal_model_capability_coverage_contract_version")
    if contract.get("schema") != UNIVERSAL_MODEL_CAPABILITY_COVERAGE_CONTRACT_SCHEMA:
        errors.append("unexpected model capability coverage schema")
    for capability in REQUIRED_MODEL_CAPABILITY_CLASSES:
        if capability not in contract.get("model_capability_rows", {}):
            errors.append(f"missing model capability row: {capability}")
    for modality_pair in REQUIRED_MODALITY_PAIRS:
        if modality_pair not in contract.get("modality_pair_rows", {}):
            errors.append(f"missing modality pair row: {modality_pair}")
    for surface in REQUIRED_OPERATION_SURFACES:
        if surface not in contract.get("operation_surface_rows", {}):
            errors.append(f"missing operation surface row: {surface}")
    for failure in REQUIRED_NEGATIVE_CAPABILITY_FAILURES:
        if failure not in contract.get("negative_capability_rows", {}):
            errors.append(f"missing negative capability row: {failure}")
    for check in (
        "model_provider_registry_l176_ready",
        "provider_catalog_coverage_l178_ready",
        "runtime_route_binding_l179_ready",
        "verified_source_footer_l180_ready",
        "model_capability_rows_complete",
        "modality_pair_rows_complete",
        "operation_surface_rows_complete",
        "catalog_covered_route_capability_rows_complete",
        "negative_capability_fixtures_reject",
        "contract_signed",
    ):
        if check not in contract.get("checks", {}):
            errors.append(f"missing model capability coverage check: {check}")
    return errors


def verify_universal_model_capability_coverage_contract(
    contract_input: dict[str, Any],
    contract: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L181 capability coverage contract against replay input."""

    errors = validate_universal_model_capability_coverage_contract_shape(contract)
    expected_hash = hash_payload(_hashable_contract(contract))
    if contract.get("universal_model_capability_coverage_contract_hash") != expected_hash:
        errors.append("universal_model_capability_coverage_contract_hash mismatch")
    private_fields = _contains_private_fields(contract)
    if private_fields:
        errors.append(
            "model capability coverage contract exposes private fields: "
            + ", ".join(private_fields)
        )
    if not _private_strings_absent(contract, contract_input):
        errors.append("model capability coverage contract exposes private input strings")
    replayed = make_universal_model_capability_coverage_contract(
        contract_input,
        issuer=contract.get("issuer", DEFAULT_ISSUER),
        created_at=contract.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get("universal_model_capability_coverage_contract_hash") != contract.get(
        "universal_model_capability_coverage_contract_hash"
    ):
        errors.append("model capability coverage contract does not match replay inputs")
    if contract.get("summary", {}).get("status") != "ready":
        errors.append("model capability coverage contract is not ready")
    if (
        contract.get("model_capability_coverage_decision", {}).get(
            "universal_model_capability_coverage_ready"
        )
        is not True
    ):
        errors.append("model capability coverage decision is not ready")
    if contract.get("privacy", {}).get("private_payloads_excluded") is not True:
        errors.append("model capability coverage privacy is not preserved")
    if signing_secret:
        signature = contract.get("signature", {})
        expected_signature = sign_payload(_hashable_contract(contract), signing_secret)
        if not signature:
            errors.append("model capability coverage contract is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("model capability coverage contract signature is invalid")
    return errors
