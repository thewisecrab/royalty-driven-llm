"""Universal native source annotation contracts.

The L183 layer closes the gap between provider-native citation or grounding
metadata and the RDLLM source footer users see. L182 proves provider capability
claims are source-bound. L183 proves every native URL, file, document, grounding,
streaming, router, RAG, local-runtime, or media source annotation is normalized
into hash-bound RDLLM footer rows or fails closed before response release,
source-footer reliance, or creator settlement.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_NATIVE_SOURCE_ANNOTATION_CONTRACT_VERSION = (
    "rdllm-universal-native-source-annotation-contract/v1"
)
UNIVERSAL_NATIVE_SOURCE_ANNOTATION_CONTRACT_SCHEMA = (
    "docs/schemas/universal_native_source_annotation_contract.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L183"
MINIMUM_LIVE_CAPABILITY_DISCOVERY_LEVEL = "RDLLM-L182"
MINIMUM_VERIFIED_SOURCE_FOOTER_LEVEL = "RDLLM-L180"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-native-source-annotation-contract.json"
)

REQUIRED_NATIVE_ANNOTATION_FORMATS = (
    "openai_url_citation",
    "openai_file_citation",
    "openai_container_file_citation",
    "openai_file_path",
    "anthropic_char_location",
    "anthropic_page_location",
    "anthropic_content_block_location",
    "anthropic_streaming_citations_delta",
    "gemini_grounding_chunks",
    "gemini_grounding_supports",
    "gemini_search_entry_point",
    "bedrock_document_citations",
    "bedrock_s3_document_source",
    "router_forwarded_annotations",
    "rag_retrieved_context",
    "local_manifest_source_map",
    "media_generation_source_metadata",
)

REQUIRED_NORMALIZED_FOOTER_FIELDS = (
    "provider_annotation_type",
    "provider_family",
    "route_id",
    "source_identity_hash",
    "source_title_hash",
    "source_uri_or_file_hash",
    "native_locator_hash",
    "claim_span_hash",
    "evidence_span_hash",
    "annotation_payload_hash",
    "rdllm_footer_row_hash",
    "verification_status",
)

REQUIRED_NEGATIVE_NATIVE_ANNOTATION_FAILURES = (
    "native_annotation_dropped",
    "unknown_annotation_type_admitted",
    "url_citation_without_url",
    "file_citation_without_file_id",
    "container_file_citation_without_container",
    "char_location_without_indices",
    "page_location_without_page_numbers",
    "content_block_location_without_indices",
    "gemini_grounding_support_without_chunk",
    "gemini_search_entry_point_without_supports",
    "bedrock_document_citation_without_document_source",
    "streaming_citation_delta_not_finalized",
    "router_strips_upstream_citations",
    "rag_context_without_source_identity",
    "local_manifest_without_source_map",
    "media_generation_without_source_metadata",
    "footer_row_without_native_annotation_binding",
    "native_annotation_footer_hash_mismatch",
    "posthoc_footer_without_native_annotation",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_native_source_annotation_contract_hash",
    "universal_live_capability_discovery_contract_hash",
    "universal_verified_source_footer_contract_hash",
    "annotation_format_hash",
    "parser_hash",
    "fixture_hash",
    "field_hash",
    "source_field_hash",
    "footer_field_hash",
    "route_annotation_hash",
    "native_payload_hash",
    "rdllm_annotation_hash",
    "l182_route_discovery_hash",
    "footer_binding_hash",
    "native_annotation_hash",
    "footer_row_hash",
    "verified_footer_hash",
    "claim_span_hash",
    "source_identity_hash",
    "verifier_hash",
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
    "native_annotation_payload",
    "grounding_metadata_raw",
    "citation_text",
    "cited_text",
    "tool_payload",
    "audio_payload",
    "image_payload",
    "video_payload",
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
    "native_annotation_format_rows": set(REQUIRED_NATIVE_ANNOTATION_FORMATS),
    "normalization_field_rows": set(REQUIRED_NORMALIZED_FOOTER_FIELDS),
    "negative_native_annotation_rows": set(
        REQUIRED_NEGATIVE_NATIVE_ANNOTATION_FAILURES
    ),
}


def load_universal_native_source_annotation_contract_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L183 native annotation contract."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in contract.items()
        if key not in {"universal_native_source_annotation_contract_hash", "signature"}
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


def _l182_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("live_capability_discovery_decision", {}) if artifact else {}
    return (
        _summary(artifact).get("status") == "ready"
        and _artifact_level(artifact) == MINIMUM_LIVE_CAPABILITY_DISCOVERY_LEVEL
        and decision.get("universal_live_capability_discovery_ready") is True
        and decision.get("source_footer_reliance_allowed") is True
    )


def _l180_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("source_footer_reliance_decision", {}) if artifact else {}
    return (
        _summary(artifact).get("status") == "ready"
        and _artifact_level(artifact) == MINIMUM_VERIFIED_SOURCE_FOOTER_LEVEL
        and decision.get("universal_verified_source_footer_ready") is True
        and (
            decision.get("source_footer_reliance_allowed") is True
            or decision.get("user_source_footer_reliance_allowed") is True
        )
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


def _annotation_format_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "annotation_format_hash",
        "parser_hash",
        "fixture_hash",
        "provider_family",
        "source_capability",
    )
    required_bools = (
        "official_or_attested_shape_observed",
        "parser_replays_native_locator",
        "source_identity_extractable",
        "claim_span_locator_extractable",
        "footer_mapping_defined",
        "streaming_or_batch_finalized",
        "no_private_payloads",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _normalization_field_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "field_hash",
        "source_field_hash",
        "footer_field_hash",
        "verifier_hash",
    )
    required_bools = (
        "field_populated_from_native_annotation",
        "field_hash_bound",
        "footer_field_bound",
        "redacted_if_private",
        "no_private_payloads",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _route_annotation_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "route_id",
        "provider_family",
        "native_annotation_format",
        "route_annotation_hash",
        "native_payload_hash",
        "rdllm_annotation_hash",
        "l182_route_discovery_hash",
        "verifier_hash",
    )
    required_bools = (
        "l182_route_discovered",
        "native_annotations_observed_or_abstained",
        "all_native_annotations_normalized",
        "unsupported_native_annotations_blocked",
        "footer_rows_projected",
        "no_private_payloads",
    )
    return (
        all(_string(row.get(field)) for field in required_strings)
        and row.get("native_annotation_format") in REQUIRED_NATIVE_ANNOTATION_FORMATS
        and all(_bool(row.get(field)) for field in required_bools)
    )


def _footer_binding_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "route_id",
        "footer_binding_hash",
        "native_annotation_hash",
        "footer_row_hash",
        "verified_footer_hash",
        "claim_span_hash",
        "source_identity_hash",
        "verifier_hash",
    )
    required_bools = (
        "native_annotation_bound",
        "footer_row_visible_or_abstained",
        "claim_span_preserved",
        "source_locator_preserved",
        "metadata_fidelity_checked",
        "no_private_payloads",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _negative_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            _string(row.get("fixture_hash")),
            _string(row.get("verifier_hash")),
            _bool(row.get("expected_reject")),
            _bool(row.get("observed_reject")),
            _bool(row.get("normalization_blocked")),
            _bool(row.get("response_release_blocked")),
            _bool(row.get("source_footer_reliance_blocked")),
            _bool(row.get("settlement_held")),
            _bool(row.get("public_status_marked_failed")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _l182_route_ids(live_capability_discovery: dict[str, Any] | None) -> list[str]:
    if not isinstance(live_capability_discovery, dict):
        return []
    rows = live_capability_discovery.get("route_discovery_rows", {})
    if isinstance(rows, dict) and rows:
        return sorted(str(route_id) for route_id in rows)
    coverage = live_capability_discovery.get("coverage", {})
    if isinstance(coverage, dict):
        route_ids = coverage.get("l181_route_ids", [])
        if isinstance(route_ids, list):
            return sorted(str(route_id) for route_id in route_ids if route_id)
    return []


def _route_rows_complete(
    rows: dict[str, dict[str, Any]],
    required_route_ids: list[str],
    predicate,
) -> tuple[list[str], list[str], list[str]]:
    missing = [route_id for route_id in required_route_ids if route_id not in rows]
    incomplete = [
        route_id
        for route_id in required_route_ids
        if route_id in rows and not predicate(rows[route_id])
    ]
    mismatched = [
        route_id
        for route_id in required_route_ids
        if route_id in rows and rows[route_id].get("route_id") != route_id
    ]
    if not required_route_ids:
        missing.append("at_least_one_l182_route")
    return missing, incomplete, mismatched


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


def make_universal_native_source_annotation_contract(
    contract_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L183 universal native source annotation contract."""

    live_capability_discovery = contract_input.get(
        "universal_live_capability_discovery_contract"
    )
    verified_source_footer = contract_input.get(
        "universal_verified_source_footer_contract"
    )
    annotation_format_rows = _row_map(contract_input, "native_annotation_format_rows")
    normalization_field_rows = _row_map(contract_input, "normalization_field_rows")
    route_annotation_rows = _row_map(contract_input, "route_annotation_rows")
    footer_binding_rows = _row_map(contract_input, "footer_binding_rows")
    negative_rows = _row_map(contract_input, "negative_native_annotation_rows")

    missing_formats, incomplete_formats = _complete_rows(
        annotation_format_rows,
        REQUIRED_NATIVE_ANNOTATION_FORMATS,
        _annotation_format_row_ready,
    )
    missing_fields, incomplete_fields = _complete_rows(
        normalization_field_rows,
        REQUIRED_NORMALIZED_FOOTER_FIELDS,
        _normalization_field_row_ready,
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows,
        REQUIRED_NEGATIVE_NATIVE_ANNOTATION_FAILURES,
        _negative_row_ready,
    )
    required_route_ids = _l182_route_ids(
        live_capability_discovery
        if isinstance(live_capability_discovery, dict)
        else None
    )
    (
        missing_route_annotations,
        incomplete_route_annotations,
        mismatched_route_annotations,
    ) = _route_rows_complete(
        route_annotation_rows,
        required_route_ids,
        _route_annotation_row_ready,
    )
    (
        missing_footer_bindings,
        incomplete_footer_bindings,
        mismatched_footer_bindings,
    ) = _route_rows_complete(
        footer_binding_rows,
        required_route_ids,
        _footer_binding_row_ready,
    )

    l182_ready = _l182_ready(
        live_capability_discovery
        if isinstance(live_capability_discovery, dict)
        else None
    )
    l180_ready = _l180_ready(
        verified_source_footer
        if isinstance(verified_source_footer, dict)
        else None
    )
    checks = {
        "live_capability_discovery_l182_ready": l182_ready
        and _artifact_hash_is_reproducible(
            live_capability_discovery
            if isinstance(live_capability_discovery, dict)
            else None
        ),
        "verified_source_footer_l180_ready": l180_ready
        and _artifact_hash_is_reproducible(
            verified_source_footer
            if isinstance(verified_source_footer, dict)
            else None
        ),
        "native_annotation_format_rows_complete": not missing_formats
        and not incomplete_formats,
        "normalization_field_rows_complete": not missing_fields
        and not incomplete_fields,
        "route_annotation_rows_complete": (
            not missing_route_annotations
            and not incomplete_route_annotations
            and not mismatched_route_annotations
        ),
        "footer_binding_rows_complete": (
            not missing_footer_bindings
            and not incomplete_footer_bindings
            and not mismatched_footer_bindings
        ),
        "negative_native_annotation_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "contract_signed": signing_secret is not None,
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    ready = not failure_modes

    format_root = merkle_root([
        hash_payload({"annotation_format": name, "row": annotation_format_rows.get(name, {})})
        for name in REQUIRED_NATIVE_ANNOTATION_FORMATS
    ])
    field_root = merkle_root([
        hash_payload({"normalized_field": name, "row": normalization_field_rows.get(name, {})})
        for name in REQUIRED_NORMALIZED_FOOTER_FIELDS
    ])
    route_root = merkle_root([
        hash_payload({"route_id": route_id, "row": route_annotation_rows.get(route_id, {})})
        for route_id in required_route_ids
    ])
    footer_root = merkle_root([
        hash_payload({"route_id": route_id, "row": footer_binding_rows.get(route_id, {})})
        for route_id in required_route_ids
    ])
    negative_root = merkle_root([
        hash_payload({"failure": failure, "row": negative_rows.get(failure, {})})
        for failure in REQUIRED_NEGATIVE_NATIVE_ANNOTATION_FAILURES
    ])

    public = {
        "universal_native_source_annotation_contract_version": (
            UNIVERSAL_NATIVE_SOURCE_ANNOTATION_CONTRACT_VERSION
        ),
        "schema": UNIVERSAL_NATIVE_SOURCE_ANNOTATION_CONTRACT_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": "rdllm-universal-native-source-annotation-policy/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_live_capability_discovery_level": (
                MINIMUM_LIVE_CAPABILITY_DISCOVERY_LEVEL
            ),
            "minimum_verified_source_footer_level": (
                MINIMUM_VERIFIED_SOURCE_FOOTER_LEVEL
            ),
            "provider_native_annotations_must_be_normalized": True,
            "footer_rows_must_bind_native_annotation_hashes": True,
            "streaming_citation_deltas_must_finalize": True,
            "router_and_rag_annotations_must_preserve_source_identity": True,
            "posthoc_footer_insertion_fails_closed": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_NATIVE_SOURCE_ANNOTATION_CONTRACT_VERSION,
        },
        "artifact_bindings": {
            "universal_live_capability_discovery_contract": _artifact_binding(
                live_capability_discovery
                if isinstance(live_capability_discovery, dict)
                else None,
                minimum_level=MINIMUM_LIVE_CAPABILITY_DISCOVERY_LEVEL,
                ready=l182_ready,
            ),
            "universal_verified_source_footer_contract": _artifact_binding(
                verified_source_footer
                if isinstance(verified_source_footer, dict)
                else None,
                minimum_level=MINIMUM_VERIFIED_SOURCE_FOOTER_LEVEL,
                ready=l180_ready,
            ),
        },
        "native_annotation_format_rows": {
            name: annotation_format_rows.get(name, {})
            for name in REQUIRED_NATIVE_ANNOTATION_FORMATS
        },
        "normalization_field_rows": {
            name: normalization_field_rows.get(name, {})
            for name in REQUIRED_NORMALIZED_FOOTER_FIELDS
        },
        "route_annotation_rows": {
            route_id: route_annotation_rows.get(route_id, {})
            for route_id in required_route_ids
        },
        "footer_binding_rows": {
            route_id: footer_binding_rows.get(route_id, {})
            for route_id in required_route_ids
        },
        "negative_native_annotation_rows": {
            failure: negative_rows.get(failure, {})
            for failure in REQUIRED_NEGATIVE_NATIVE_ANNOTATION_FAILURES
        },
        "evidence_roots": {
            "native_annotation_format_root": format_root,
            "normalization_field_root": field_root,
            "route_annotation_root": route_root,
            "footer_binding_root": footer_root,
            "negative_native_annotation_root": negative_root,
            "combined_native_source_annotation_root": merkle_root(
                [format_root, field_root, route_root, footer_root, negative_root]
            ),
        },
        "checks": checks,
        "native_source_annotation_decision": {
            "universal_native_source_annotation_ready": ready,
            "provider_native_annotations_normalized": ready,
            "source_footer_binding_allowed": ready,
            "model_invocation_allowed": ready,
            "response_release_allowed": ready,
            "source_footer_reliance_allowed": ready,
            "creator_settlement_allowed": ready,
            "native_annotation_drop_blocked": True,
            "posthoc_footer_blocked": True,
            "unsupported_annotation_blocked": True,
            "failure_modes": failure_modes,
        },
        "coverage": {
            "l182_route_ids": required_route_ids,
            "missing_native_annotation_formats": missing_formats,
            "incomplete_native_annotation_formats": incomplete_formats,
            "missing_normalization_fields": missing_fields,
            "incomplete_normalization_fields": incomplete_fields,
            "missing_route_annotations": missing_route_annotations,
            "incomplete_route_annotations": incomplete_route_annotations,
            "mismatched_route_annotations": mismatched_route_annotations,
            "missing_footer_bindings": missing_footer_bindings,
            "incomplete_footer_bindings": incomplete_footer_bindings,
            "mismatched_footer_bindings": mismatched_footer_bindings,
            "missing_negative_native_annotation_failures": missing_negative,
            "incomplete_negative_native_annotation_failures": incomplete_negative,
        },
        "privacy": {
            "private_payloads_excluded": True,
            "private_prompts_excluded": True,
            "private_outputs_excluded": True,
            "private_provider_annotations_excluded": True,
            "private_source_text_excluded": True,
            "public_contract_uses_hashes_annotation_types_routes_and_footer_rows": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_live_capability_discovery_level": (
                MINIMUM_LIVE_CAPABILITY_DISCOVERY_LEVEL
            ),
            "minimum_verified_source_footer_level": (
                MINIMUM_VERIFIED_SOURCE_FOOTER_LEVEL
            ),
            "native_annotation_format_count": len(REQUIRED_NATIVE_ANNOTATION_FORMATS),
            "ready_native_annotation_format_count": len(
                REQUIRED_NATIVE_ANNOTATION_FORMATS
            )
            - len(missing_formats)
            - len(incomplete_formats),
            "normalization_field_count": len(REQUIRED_NORMALIZED_FOOTER_FIELDS),
            "ready_normalization_field_count": len(REQUIRED_NORMALIZED_FOOTER_FIELDS)
            - len(missing_fields)
            - len(incomplete_fields),
            "l182_route_count": len(required_route_ids),
            "ready_route_annotation_count": len(required_route_ids)
            - len(missing_route_annotations)
            - len(incomplete_route_annotations)
            - len(mismatched_route_annotations),
            "ready_footer_binding_count": len(required_route_ids)
            - len(missing_footer_bindings)
            - len(incomplete_footer_bindings)
            - len(mismatched_footer_bindings),
            "negative_native_annotation_failure_count": len(
                REQUIRED_NEGATIVE_NATIVE_ANNOTATION_FAILURES
            ),
            "ready_negative_native_annotation_failure_count": len(
                REQUIRED_NEGATIVE_NATIVE_ANNOTATION_FAILURES
            )
            - len(missing_negative)
            - len(incomplete_negative),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": True,
            "signed_native_source_annotation_contract": signing_secret is not None,
        },
    }
    public["universal_native_source_annotation_contract_hash"] = hash_payload(
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


def validate_universal_native_source_annotation_contract_shape(
    contract: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for an L183 annotation contract."""

    errors: list[str] = []
    required = (
        "universal_native_source_annotation_contract_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "artifact_bindings",
        "native_annotation_format_rows",
        "normalization_field_rows",
        "route_annotation_rows",
        "footer_binding_rows",
        "negative_native_annotation_rows",
        "evidence_roots",
        "checks",
        "native_source_annotation_decision",
        "coverage",
        "privacy",
        "summary",
        "universal_native_source_annotation_contract_hash",
    )
    for key in required:
        if key not in contract:
            errors.append(f"missing native source annotation field: {key}")
    if contract.get("universal_native_source_annotation_contract_version") != (
        UNIVERSAL_NATIVE_SOURCE_ANNOTATION_CONTRACT_VERSION
    ):
        errors.append("unexpected universal_native_source_annotation_contract_version")
    if contract.get("schema") != UNIVERSAL_NATIVE_SOURCE_ANNOTATION_CONTRACT_SCHEMA:
        errors.append("unexpected native source annotation schema")
    for annotation_format in REQUIRED_NATIVE_ANNOTATION_FORMATS:
        if annotation_format not in contract.get("native_annotation_format_rows", {}):
            errors.append(f"missing native annotation format row: {annotation_format}")
    for field in REQUIRED_NORMALIZED_FOOTER_FIELDS:
        if field not in contract.get("normalization_field_rows", {}):
            errors.append(f"missing normalization field row: {field}")
    for failure in REQUIRED_NEGATIVE_NATIVE_ANNOTATION_FAILURES:
        if failure not in contract.get("negative_native_annotation_rows", {}):
            errors.append(f"missing negative native annotation row: {failure}")
    for check in (
        "live_capability_discovery_l182_ready",
        "verified_source_footer_l180_ready",
        "native_annotation_format_rows_complete",
        "normalization_field_rows_complete",
        "route_annotation_rows_complete",
        "footer_binding_rows_complete",
        "negative_native_annotation_fixtures_reject",
        "contract_signed",
    ):
        if check not in contract.get("checks", {}):
            errors.append(f"missing native source annotation check: {check}")
    return errors


def verify_universal_native_source_annotation_contract(
    contract_input: dict[str, Any],
    contract: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L183 native source annotation contract against replay input."""

    errors = validate_universal_native_source_annotation_contract_shape(contract)
    expected_hash = hash_payload(_hashable_contract(contract))
    if contract.get("universal_native_source_annotation_contract_hash") != expected_hash:
        errors.append("universal_native_source_annotation_contract_hash mismatch")
    private_fields = _contains_private_fields(contract)
    if private_fields:
        errors.append(
            "native source annotation contract exposes private fields: "
            + ", ".join(private_fields)
        )
    if not _private_strings_absent(contract, contract_input):
        errors.append("native source annotation contract exposes private input strings")
    replayed = make_universal_native_source_annotation_contract(
        contract_input,
        issuer=contract.get("issuer", DEFAULT_ISSUER),
        created_at=contract.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get("universal_native_source_annotation_contract_hash") != contract.get(
        "universal_native_source_annotation_contract_hash"
    ):
        errors.append("native source annotation contract does not match replay inputs")
    if contract.get("summary", {}).get("status") != "ready":
        errors.append("native source annotation contract is not ready")
    if (
        contract.get("native_source_annotation_decision", {}).get(
            "universal_native_source_annotation_ready"
        )
        is not True
    ):
        errors.append("native source annotation decision is not ready")
    if contract.get("privacy", {}).get("private_payloads_excluded") is not True:
        errors.append("native source annotation privacy is not preserved")
    if signing_secret:
        signature = contract.get("signature", {})
        expected_signature = sign_payload(_hashable_contract(contract), signing_secret)
        if not signature:
            errors.append("native source annotation contract is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("native source annotation contract signature is invalid")
    return errors
