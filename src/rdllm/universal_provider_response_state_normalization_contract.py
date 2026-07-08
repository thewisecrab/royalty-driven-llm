"""Universal provider response-state normalization contracts.

The L186 layer binds provider-native stop, finish, refusal, safety, guardrail,
tool, stream-final, and error states to RDLLM release and settlement gates. It
prevents blocked, truncated, refused, tool-only, errored, or unknown responses
from being rendered as grounded answers with normal source-footer reliance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_PROVIDER_RESPONSE_STATE_NORMALIZATION_CONTRACT_VERSION = (
    "rdllm-universal-provider-response-state-normalization-contract/v1"
)
UNIVERSAL_PROVIDER_RESPONSE_STATE_NORMALIZATION_CONTRACT_SCHEMA = (
    "docs/schemas/universal_provider_response_state_normalization_contract.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L186"
MINIMUM_PROVIDER_METER_NORMALIZATION_LEVEL = "RDLLM-L185"
MINIMUM_CLAIM_EVIDENCE_FOOTER_LEVEL = "RDLLM-L184"
MINIMUM_RUNTIME_ROUTE_BINDING_LEVEL = "RDLLM-L179"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-provider-response-state-normalization-contract.json"
)

REQUIRED_PROVIDER_RESPONSE_STATE_SURFACES = (
    "openai_responses_status",
    "openai_responses_incomplete_reason",
    "openai_responses_refusal_output",
    "openai_chat_finish_reason",
    "openai_content_filter_finish",
    "anthropic_messages_stop_reason",
    "anthropic_streaming_refusal",
    "anthropic_tool_use_pause",
    "gemini_finish_reason",
    "gemini_prompt_feedback_block_reason",
    "gemini_safety_ratings",
    "bedrock_converse_stop_reason",
    "bedrock_guardrail_trace",
    "bedrock_converse_stream_stop_event",
    "azure_openai_content_filter_results",
    "mistral_finish_reason",
    "mistral_moderation_guardrail",
    "cohere_finish_reason",
    "cohere_safety_error",
    "xai_response_status_finish_reason",
    "openrouter_finish_reason_native_finish_reason",
    "router_gateway_error_finish_reason",
    "local_runtime_exit_status",
    "streaming_final_state",
)

REQUIRED_NORMALIZED_RESPONSE_STATE_FIELDS = (
    "provider_family",
    "route_id",
    "request_id_hash",
    "native_status_hash",
    "native_finish_reason_hash",
    "native_refusal_hash",
    "native_safety_signal_hash",
    "native_guardrail_signal_hash",
    "native_truncation_signal_hash",
    "native_tool_state_hash",
    "native_stream_final_state_hash",
    "normalized_response_state",
    "normalized_abstention_hash",
    "response_release_gate_hash",
    "source_footer_reliance_gate_hash",
    "creator_settlement_gate_hash",
    "retry_or_fallback_policy_hash",
    "public_user_status_hash",
    "rdllm_response_state_hash",
)

REQUIRED_NEGATIVE_RESPONSE_STATE_FAILURES = (
    "safety_block_rendered_as_answer",
    "refusal_stripped_by_router",
    "content_filter_finish_ignored",
    "max_tokens_truncation_treated_complete",
    "tool_call_finish_rendered_as_text",
    "incomplete_stream_committed",
    "provider_error_treated_as_model_answer",
    "prompt_block_without_prompt_feedback",
    "safety_rating_omitted",
    "guardrail_intervention_hidden",
    "native_finish_reason_dropped",
    "unknown_finish_reason_allowed",
    "local_runtime_crash_rendered_answer",
    "fallback_response_without_state_reset",
    "refusal_context_replayed_without_reset",
    "unsupported_abstention_footer",
    "settlement_released_for_blocked_response",
    "private_safety_payload_leak",
    "rate_limit_error_rendered_answer",
    "moderation_error_not_user_visible",
)

DECLARED_HASH_FIELDS = (
    "universal_provider_response_state_normalization_contract_hash",
    "universal_provider_meter_normalization_contract_hash",
    "universal_claim_evidence_footer_verification_contract_hash",
    "universal_runtime_route_binding_contract_hash",
    "response_state_hash",
    "state_surface_hash",
    "state_field_hash",
    "native_field_hash",
    "schema_hash",
    "parser_hash",
    "source_document_hash",
    "runtime_route_binding_hash",
    "provider_meter_hash",
    "native_status_hash",
    "native_finish_reason_hash",
    "native_refusal_hash",
    "native_safety_signal_hash",
    "native_guardrail_signal_hash",
    "native_truncation_signal_hash",
    "native_tool_state_hash",
    "native_stream_final_state_hash",
    "normalized_abstention_hash",
    "response_release_gate_hash",
    "source_footer_reliance_gate_hash",
    "creator_settlement_gate_hash",
    "retry_or_fallback_policy_hash",
    "public_user_status_hash",
    "rdllm_response_state_hash",
    "fixture_hash",
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
    "raw_native_request",
    "raw_native_response",
    "native_response_body",
    "provider_response_body",
    "raw_provider_response_payload",
    "raw_safety_payload",
    "raw_guardrail_payload",
    "raw_refusal_payload",
    "raw_error_payload",
    "safety_payload",
    "guardrail_payload",
    "refusal_payload",
    "error_payload",
    "safety_trace",
    "guardrail_trace",
    "moderation_trace",
    "customer_id",
    "customer_email",
    "tenant_id",
    "account_id",
    "organization_id",
    "api_key",
    "access_token",
    "refresh_token",
    "oauth_token",
    "secret",
    "signing_secret",
    "private_key",
}

PUBLIC_ROW_KEY_ALLOWLISTS = {
    "provider_response_state_surface_rows": set(REQUIRED_PROVIDER_RESPONSE_STATE_SURFACES),
    "normalized_response_state_field_rows": set(REQUIRED_NORMALIZED_RESPONSE_STATE_FIELDS),
    "negative_response_state_rows": set(REQUIRED_NEGATIVE_RESPONSE_STATE_FAILURES),
}


def load_universal_provider_response_state_normalization_contract_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L186 provider response-state contract."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in contract.items()
        if key
        not in {
            "universal_provider_response_state_normalization_contract_hash",
            "signature",
        }
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


def _l185_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("provider_meter_normalization_decision", {}) if artifact else {}
    return (
        _summary(artifact).get("status") == "ready"
        and _artifact_level(artifact) == MINIMUM_PROVIDER_METER_NORMALIZATION_LEVEL
        and decision.get("universal_provider_meter_normalization_ready") is True
        and decision.get("provider_usage_meters_normalized") is True
        and decision.get("response_release_allowed") is True
        and decision.get("source_footer_reliance_allowed") is True
        and decision.get("creator_settlement_allowed") is True
    )


def _l184_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("claim_evidence_footer_decision", {}) if artifact else {}
    return (
        _summary(artifact).get("status") == "ready"
        and _artifact_level(artifact) == MINIMUM_CLAIM_EVIDENCE_FOOTER_LEVEL
        and decision.get("universal_claim_evidence_footer_verification_ready") is True
        and decision.get("source_footer_reliance_allowed") is True
        and decision.get("response_release_allowed") is True
        and decision.get("creator_settlement_allowed") is True
    )


def _l179_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("runtime_route_binding_decision", {}) if artifact else {}
    return (
        _summary(artifact).get("status") == "ready"
        and _artifact_level(artifact) == MINIMUM_RUNTIME_ROUTE_BINDING_LEVEL
        and decision.get("universal_runtime_route_binding_ready") is True
        and decision.get("live_model_invocation_allowed") is True
        and decision.get("response_release_allowed") is True
        and decision.get("creator_settlement_allowed") is True
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


def _surface_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "state_surface_hash",
        "schema_hash",
        "parser_hash",
        "provider_family",
        "source_document_hash",
    )
    required_bools = (
        "official_or_attested_shape_observed",
        "finish_or_status_extractable",
        "refusal_or_safety_extractable_or_explicitly_absent",
        "stream_final_state_extractable",
        "tool_or_error_state_extractable_or_explicitly_absent",
        "normalization_defined",
        "no_private_payloads",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _field_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "state_field_hash",
        "native_field_hash",
        "release_gate_field_hash",
        "verifier_hash",
    )
    required_bools = (
        "field_required",
        "mapped_from_native_or_declared_absent",
        "hash_bound",
        "privacy_safe",
        "release_gate_projected",
        "no_private_payloads",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _route_response_state_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "route_id",
        "provider_family",
        "response_state_hash",
        "runtime_route_binding_hash",
        "provider_meter_hash",
        "verifier_hash",
        "normalized_response_state",
    )
    required_bools = (
        "l179_route_bound",
        "l185_meter_bound",
        "native_terminal_state_observed",
        "normalized_state_projected",
        "unknown_states_fail_closed",
        "no_private_payloads",
    )
    return (
        row.get("normalized_response_state") == "complete_supported"
        and all(_string(row.get(field)) for field in required_strings)
        and all(_bool(row.get(field)) for field in required_bools)
    )


def _release_gate_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "route_id",
        "response_release_gate_hash",
        "source_footer_reliance_gate_hash",
        "creator_settlement_gate_hash",
        "public_user_status_hash",
        "retry_or_fallback_policy_hash",
        "verifier_hash",
    )
    required_bools = (
        "complete_supported_releases",
        "blocked_or_filtered_holds_answer_release",
        "truncated_or_tool_only_holds_footer_reliance",
        "refusal_or_abstention_publicly_labeled",
        "settlement_held_when_not_supported",
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
            _bool(row.get("response_release_blocked")),
            _bool(row.get("footer_reliance_blocked")),
            _bool(row.get("creator_settlement_held")),
            _bool(row.get("public_status_marked_failed")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _required_route_ids(
    provider_meter_normalization: dict[str, Any] | None,
    runtime_route_binding: dict[str, Any] | None,
    claim_evidence_footer: dict[str, Any] | None,
) -> list[str]:
    if isinstance(provider_meter_normalization, dict):
        coverage = provider_meter_normalization.get("coverage", {})
        route_ids = coverage.get("route_ids", []) if isinstance(coverage, dict) else []
        if isinstance(route_ids, list) and route_ids:
            return sorted(str(route_id) for route_id in route_ids if route_id)
    if isinstance(runtime_route_binding, dict):
        rows = runtime_route_binding.get("runtime_route_binding_rows", {})
        if isinstance(rows, dict) and rows:
            return sorted(str(route_id) for route_id in rows)
    if isinstance(claim_evidence_footer, dict):
        coverage = claim_evidence_footer.get("coverage", {})
        route_ids = coverage.get("l183_route_ids", []) if isinstance(coverage, dict) else []
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
        missing.append("at_least_one_l185_or_l179_route")
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


def make_universal_provider_response_state_normalization_contract(
    contract_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L186 universal provider response-state normalization contract."""

    provider_meter_normalization = contract_input.get(
        "universal_provider_meter_normalization_contract"
    )
    claim_evidence_footer = contract_input.get(
        "universal_claim_evidence_footer_verification_contract"
    )
    runtime_route_binding = contract_input.get(
        "universal_runtime_route_binding_contract"
    )
    surface_rows = _row_map(contract_input, "provider_response_state_surface_rows")
    field_rows = _row_map(contract_input, "normalized_response_state_field_rows")
    route_rows = _row_map(contract_input, "route_response_state_rows")
    release_gate_rows = _row_map(contract_input, "release_gate_rows")
    negative_rows = _row_map(contract_input, "negative_response_state_rows")

    missing_surfaces, incomplete_surfaces = _complete_rows(
        surface_rows,
        REQUIRED_PROVIDER_RESPONSE_STATE_SURFACES,
        _surface_row_ready,
    )
    missing_fields, incomplete_fields = _complete_rows(
        field_rows,
        REQUIRED_NORMALIZED_RESPONSE_STATE_FIELDS,
        _field_row_ready,
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows,
        REQUIRED_NEGATIVE_RESPONSE_STATE_FAILURES,
        _negative_row_ready,
    )
    route_ids = _required_route_ids(
        provider_meter_normalization
        if isinstance(provider_meter_normalization, dict)
        else None,
        runtime_route_binding if isinstance(runtime_route_binding, dict) else None,
        claim_evidence_footer if isinstance(claim_evidence_footer, dict) else None,
    )
    missing_routes, incomplete_routes, mismatched_routes = _route_rows_complete(
        route_rows, route_ids, _route_response_state_row_ready
    )
    missing_release_gates, incomplete_release_gates, mismatched_release_gates = (
        _route_rows_complete(release_gate_rows, route_ids, _release_gate_row_ready)
    )

    l185_ready = _l185_ready(
        provider_meter_normalization
        if isinstance(provider_meter_normalization, dict)
        else None
    )
    l184_ready = _l184_ready(
        claim_evidence_footer if isinstance(claim_evidence_footer, dict) else None
    )
    l179_ready = _l179_ready(
        runtime_route_binding if isinstance(runtime_route_binding, dict) else None
    )
    checks = {
        "provider_meter_normalization_l185_ready": l185_ready
        and _artifact_hash_is_reproducible(
            provider_meter_normalization
            if isinstance(provider_meter_normalization, dict)
            else None
        ),
        "claim_evidence_footer_l184_ready": l184_ready
        and _artifact_hash_is_reproducible(
            claim_evidence_footer
            if isinstance(claim_evidence_footer, dict)
            else None
        ),
        "runtime_route_binding_l179_ready": l179_ready
        and _artifact_hash_is_reproducible(
            runtime_route_binding if isinstance(runtime_route_binding, dict) else None
        ),
        "provider_response_state_surface_rows_complete": not missing_surfaces
        and not incomplete_surfaces,
        "normalized_response_state_field_rows_complete": not missing_fields
        and not incomplete_fields,
        "route_response_state_rows_complete": (
            not missing_routes and not incomplete_routes and not mismatched_routes
        ),
        "release_gate_rows_complete": (
            not missing_release_gates
            and not incomplete_release_gates
            and not mismatched_release_gates
        ),
        "negative_response_state_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "contract_signed": signing_secret is not None,
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    ready = not failure_modes

    surface_root = merkle_root([
        hash_payload({"response_state_surface": name, "row": surface_rows.get(name, {})})
        for name in REQUIRED_PROVIDER_RESPONSE_STATE_SURFACES
    ])
    field_root = merkle_root([
        hash_payload({"normalized_response_state_field": name, "row": field_rows.get(name, {})})
        for name in REQUIRED_NORMALIZED_RESPONSE_STATE_FIELDS
    ])
    route_root = merkle_root([
        hash_payload({"route_id": route_id, "row": route_rows.get(route_id, {})})
        for route_id in route_ids
    ])
    release_gate_root = merkle_root([
        hash_payload({"route_id": route_id, "row": release_gate_rows.get(route_id, {})})
        for route_id in route_ids
    ])
    negative_root = merkle_root([
        hash_payload({"failure": failure, "row": negative_rows.get(failure, {})})
        for failure in REQUIRED_NEGATIVE_RESPONSE_STATE_FAILURES
    ])

    public = {
        "universal_provider_response_state_normalization_contract_version": (
            UNIVERSAL_PROVIDER_RESPONSE_STATE_NORMALIZATION_CONTRACT_VERSION
        ),
        "schema": UNIVERSAL_PROVIDER_RESPONSE_STATE_NORMALIZATION_CONTRACT_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": (
                "rdllm-universal-provider-response-state-normalization-policy/v1"
            ),
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_provider_meter_normalization_level": (
                MINIMUM_PROVIDER_METER_NORMALIZATION_LEVEL
            ),
            "minimum_claim_evidence_footer_level": (
                MINIMUM_CLAIM_EVIDENCE_FOOTER_LEVEL
            ),
            "minimum_runtime_route_binding_level": MINIMUM_RUNTIME_ROUTE_BINDING_LEVEL,
            "provider_terminal_state_must_be_observed": True,
            "native_finish_or_status_must_normalize": True,
            "safe_release_requires_complete_supported_state": True,
            "source_footer_reliance_requires_complete_supported_state": True,
            "creator_settlement_requires_complete_supported_state": True,
            "refusal_or_abstention_requires_state_receipt": True,
            "blocked_refused_truncated_tool_error_states_fail_closed": True,
            "unknown_terminal_states_fail_closed": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_PROVIDER_RESPONSE_STATE_NORMALIZATION_CONTRACT_VERSION,
        },
        "artifact_bindings": {
            "universal_provider_meter_normalization_contract": _artifact_binding(
                provider_meter_normalization
                if isinstance(provider_meter_normalization, dict)
                else None,
                minimum_level=MINIMUM_PROVIDER_METER_NORMALIZATION_LEVEL,
                ready=l185_ready,
            ),
            "universal_claim_evidence_footer_verification_contract": _artifact_binding(
                claim_evidence_footer
                if isinstance(claim_evidence_footer, dict)
                else None,
                minimum_level=MINIMUM_CLAIM_EVIDENCE_FOOTER_LEVEL,
                ready=l184_ready,
            ),
            "universal_runtime_route_binding_contract": _artifact_binding(
                runtime_route_binding
                if isinstance(runtime_route_binding, dict)
                else None,
                minimum_level=MINIMUM_RUNTIME_ROUTE_BINDING_LEVEL,
                ready=l179_ready,
            ),
        },
        "provider_response_state_surface_rows": {
            name: surface_rows.get(name, {})
            for name in REQUIRED_PROVIDER_RESPONSE_STATE_SURFACES
        },
        "normalized_response_state_field_rows": {
            name: field_rows.get(name, {})
            for name in REQUIRED_NORMALIZED_RESPONSE_STATE_FIELDS
        },
        "route_response_state_rows": {
            route_id: route_rows.get(route_id, {}) for route_id in route_ids
        },
        "release_gate_rows": {
            route_id: release_gate_rows.get(route_id, {}) for route_id in route_ids
        },
        "negative_response_state_rows": {
            failure: negative_rows.get(failure, {})
            for failure in REQUIRED_NEGATIVE_RESPONSE_STATE_FAILURES
        },
        "evidence_roots": {
            "provider_response_state_surface_root": surface_root,
            "normalized_response_state_field_root": field_root,
            "route_response_state_root": route_root,
            "release_gate_root": release_gate_root,
            "negative_response_state_root": negative_root,
            "combined_response_state_root": merkle_root(
                [surface_root, field_root, route_root, release_gate_root, negative_root]
            ),
        },
        "checks": checks,
        "provider_response_state_normalization_decision": {
            "universal_provider_response_state_normalization_ready": ready,
            "provider_response_states_normalized": ready,
            "model_invocation_allowed": ready,
            "safe_response_release_allowed": ready,
            "source_footer_reliance_allowed": ready,
            "creator_settlement_allowed": ready,
            "abstention_or_refusal_release_allowed_with_state_receipt": ready,
            "blocked_or_filtered_answer_release_blocked": True,
            "truncated_answer_reliance_blocked": True,
            "unknown_finish_reason_blocked": True,
            "private_safety_payload_blocked": True,
            "failure_modes": failure_modes,
        },
        "coverage": {
            "route_ids": route_ids,
            "missing_provider_response_state_surfaces": missing_surfaces,
            "incomplete_provider_response_state_surfaces": incomplete_surfaces,
            "missing_normalized_response_state_fields": missing_fields,
            "incomplete_normalized_response_state_fields": incomplete_fields,
            "missing_route_response_state_rows": missing_routes,
            "incomplete_route_response_state_rows": incomplete_routes,
            "mismatched_route_response_state_rows": mismatched_routes,
            "missing_release_gate_rows": missing_release_gates,
            "incomplete_release_gate_rows": incomplete_release_gates,
            "mismatched_release_gate_rows": mismatched_release_gates,
            "missing_negative_response_state_failures": missing_negative,
            "incomplete_negative_response_state_failures": incomplete_negative,
        },
        "privacy": {
            "private_payloads_excluded": True,
            "private_prompts_excluded": True,
            "private_outputs_excluded": True,
            "private_source_text_excluded": True,
            "private_refusal_payloads_excluded": True,
            "private_safety_payloads_excluded": True,
            "private_guardrail_payloads_excluded": True,
            "private_provider_error_payloads_excluded": True,
            "public_contract_uses_hashes_routes_state_classes_gates_and_verdicts": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_provider_meter_normalization_level": (
                MINIMUM_PROVIDER_METER_NORMALIZATION_LEVEL
            ),
            "minimum_claim_evidence_footer_level": (
                MINIMUM_CLAIM_EVIDENCE_FOOTER_LEVEL
            ),
            "minimum_runtime_route_binding_level": MINIMUM_RUNTIME_ROUTE_BINDING_LEVEL,
            "provider_response_state_surface_count": len(
                REQUIRED_PROVIDER_RESPONSE_STATE_SURFACES
            ),
            "ready_provider_response_state_surface_count": len(
                REQUIRED_PROVIDER_RESPONSE_STATE_SURFACES
            )
            - len(missing_surfaces)
            - len(incomplete_surfaces),
            "normalized_response_state_field_count": len(
                REQUIRED_NORMALIZED_RESPONSE_STATE_FIELDS
            ),
            "ready_normalized_response_state_field_count": len(
                REQUIRED_NORMALIZED_RESPONSE_STATE_FIELDS
            )
            - len(missing_fields)
            - len(incomplete_fields),
            "route_count": len(route_ids),
            "ready_route_response_state_count": len(route_ids)
            - len(missing_routes)
            - len(incomplete_routes)
            - len(mismatched_routes),
            "ready_release_gate_count": len(route_ids)
            - len(missing_release_gates)
            - len(incomplete_release_gates)
            - len(mismatched_release_gates),
            "negative_response_state_failure_count": len(
                REQUIRED_NEGATIVE_RESPONSE_STATE_FAILURES
            ),
            "ready_negative_response_state_failure_count": len(
                REQUIRED_NEGATIVE_RESPONSE_STATE_FAILURES
            )
            - len(missing_negative)
            - len(incomplete_negative),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": True,
            "signed_provider_response_state_normalization_contract": (
                signing_secret is not None
            ),
        },
    }
    public["universal_provider_response_state_normalization_contract_hash"] = (
        hash_payload(_hashable_contract(public))
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


def validate_universal_provider_response_state_normalization_contract_shape(
    contract: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for an L186 response-state contract."""

    errors: list[str] = []
    required = (
        "universal_provider_response_state_normalization_contract_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "artifact_bindings",
        "provider_response_state_surface_rows",
        "normalized_response_state_field_rows",
        "route_response_state_rows",
        "release_gate_rows",
        "negative_response_state_rows",
        "evidence_roots",
        "checks",
        "provider_response_state_normalization_decision",
        "coverage",
        "privacy",
        "summary",
        "universal_provider_response_state_normalization_contract_hash",
    )
    for key in required:
        if key not in contract:
            errors.append(f"missing provider response-state field: {key}")
    if (
        contract.get("universal_provider_response_state_normalization_contract_version")
        != UNIVERSAL_PROVIDER_RESPONSE_STATE_NORMALIZATION_CONTRACT_VERSION
    ):
        errors.append(
            "unexpected universal_provider_response_state_normalization_contract_version"
        )
    if contract.get("schema") != UNIVERSAL_PROVIDER_RESPONSE_STATE_NORMALIZATION_CONTRACT_SCHEMA:
        errors.append("unexpected provider response-state normalization schema")
    for surface in REQUIRED_PROVIDER_RESPONSE_STATE_SURFACES:
        if surface not in contract.get("provider_response_state_surface_rows", {}):
            errors.append(f"missing provider response-state surface row: {surface}")
    for field in REQUIRED_NORMALIZED_RESPONSE_STATE_FIELDS:
        if field not in contract.get("normalized_response_state_field_rows", {}):
            errors.append(f"missing normalized response-state field row: {field}")
    for failure in REQUIRED_NEGATIVE_RESPONSE_STATE_FAILURES:
        if failure not in contract.get("negative_response_state_rows", {}):
            errors.append(f"missing negative response-state row: {failure}")
    for check in (
        "provider_meter_normalization_l185_ready",
        "claim_evidence_footer_l184_ready",
        "runtime_route_binding_l179_ready",
        "provider_response_state_surface_rows_complete",
        "normalized_response_state_field_rows_complete",
        "route_response_state_rows_complete",
        "release_gate_rows_complete",
        "negative_response_state_fixtures_reject",
        "contract_signed",
    ):
        if check not in contract.get("checks", {}):
            errors.append(f"missing provider response-state check: {check}")
    return errors


def verify_universal_provider_response_state_normalization_contract(
    contract_input: dict[str, Any],
    contract: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L186 response-state contract against replay input."""

    errors = validate_universal_provider_response_state_normalization_contract_shape(
        contract
    )
    expected_hash = hash_payload(_hashable_contract(contract))
    if (
        contract.get("universal_provider_response_state_normalization_contract_hash")
        != expected_hash
    ):
        errors.append(
            "universal_provider_response_state_normalization_contract_hash mismatch"
        )
    private_fields = _contains_private_fields(contract)
    if private_fields:
        errors.append(
            "provider response-state normalization contract exposes private fields: "
            + ", ".join(private_fields)
        )
    if not _private_strings_absent(contract, contract_input):
        errors.append(
            "provider response-state normalization contract exposes private input strings"
        )
    replayed = make_universal_provider_response_state_normalization_contract(
        contract_input,
        issuer=contract.get("issuer", DEFAULT_ISSUER),
        created_at=contract.get("created_at"),
        signing_secret=signing_secret,
    )
    if (
        replayed.get("universal_provider_response_state_normalization_contract_hash")
        != contract.get("universal_provider_response_state_normalization_contract_hash")
    ):
        errors.append(
            "provider response-state normalization contract does not match replay inputs"
        )
    if contract.get("summary", {}).get("status") != "ready":
        errors.append("provider response-state normalization contract is not ready")
    if (
        contract.get("provider_response_state_normalization_decision", {}).get(
            "universal_provider_response_state_normalization_ready"
        )
        is not True
    ):
        errors.append("provider response-state normalization decision is not ready")
    if contract.get("privacy", {}).get("private_payloads_excluded") is not True:
        errors.append("provider response-state normalization privacy is not preserved")
    if signing_secret:
        signature = contract.get("signature", {})
        expected_signature = sign_payload(_hashable_contract(contract), signing_secret)
        if not signature:
            errors.append("provider response-state normalization contract is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("provider response-state normalization contract signature is invalid")
    return errors
