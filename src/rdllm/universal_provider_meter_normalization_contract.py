"""Universal provider meter normalization contracts.

The L185 layer binds provider-native usage and billing meters to the same
routes, verified source footers, and settlement meters used by RDLLM. It closes
the gap between "the answer is grounded" and "the grounded answer can be
settled across provider families without dropping cache, reasoning, tool, media,
batch, embedding, hosted-runtime, or router billing units."
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_PROVIDER_METER_NORMALIZATION_CONTRACT_VERSION = (
    "rdllm-universal-provider-meter-normalization-contract/v1"
)
UNIVERSAL_PROVIDER_METER_NORMALIZATION_CONTRACT_SCHEMA = (
    "docs/schemas/universal_provider_meter_normalization_contract.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L185"
MINIMUM_CLAIM_EVIDENCE_FOOTER_LEVEL = "RDLLM-L184"
MINIMUM_LIVE_CAPABILITY_DISCOVERY_LEVEL = "RDLLM-L182"
MINIMUM_RUNTIME_ROUTE_BINDING_LEVEL = "RDLLM-L179"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-provider-meter-normalization-contract.json"
)

REQUIRED_PROVIDER_METER_SURFACES = (
    "openai_responses_usage",
    "openai_chat_completions_usage",
    "openai_batch_usage",
    "openai_cached_input_usage",
    "openai_reasoning_usage",
    "anthropic_messages_usage",
    "anthropic_cache_usage",
    "anthropic_message_batches_usage",
    "gemini_usage_metadata",
    "gemini_cached_content_usage",
    "gemini_batch_usage",
    "bedrock_converse_usage",
    "bedrock_invoke_model_usage",
    "bedrock_batch_inference_usage",
    "azure_openai_usage",
    "mistral_usage",
    "cohere_billed_units_usage",
    "xai_openai_compatible_usage",
    "openrouter_pass_through_usage",
    "local_runtime_usage_manifest",
    "hosted_endpoint_runtime_meter",
    "rag_tool_meter",
    "agent_tool_meter",
    "media_generation_meter",
)

REQUIRED_NORMALIZED_METER_FIELDS = (
    "provider_family",
    "route_id",
    "model_id_hash",
    "request_id_hash",
    "input_unit_count_hash",
    "output_unit_count_hash",
    "cached_input_unit_count_hash",
    "reasoning_or_thinking_unit_count_hash",
    "tool_or_search_unit_count_hash",
    "media_unit_count_hash",
    "batch_or_async_unit_count_hash",
    "embedding_or_rerank_unit_count_hash",
    "training_or_fine_tune_unit_count_hash",
    "hosted_runtime_unit_count_hash",
    "currency_or_credit_unit_hash",
    "pricing_snapshot_hash",
    "rate_limit_quota_hash",
    "provider_invoice_row_hash",
    "rdllm_settlement_meter_hash",
)

REQUIRED_NEGATIVE_PROVIDER_METER_FAILURES = (
    "provider_usage_missing",
    "usage_without_route_binding",
    "model_usage_mismatch",
    "input_tokens_dropped",
    "output_tokens_dropped",
    "cached_tokens_ignored",
    "reasoning_tokens_ignored",
    "tool_or_search_meter_ignored",
    "media_units_ignored",
    "batch_discount_unbound",
    "embedding_or_rerank_units_ignored",
    "fine_tune_training_units_ignored",
    "hosted_endpoint_runtime_unmetered",
    "currency_conversion_unbound",
    "pricing_snapshot_stale",
    "quota_rate_limit_missing",
    "router_usage_double_counted",
    "provider_invoice_hash_mismatch",
    "settlement_without_normalized_meter",
    "private_billing_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_provider_meter_normalization_contract_hash",
    "universal_claim_evidence_footer_verification_contract_hash",
    "universal_live_capability_discovery_contract_hash",
    "universal_runtime_route_binding_contract_hash",
    "provider_meter_hash",
    "meter_surface_hash",
    "schema_hash",
    "parser_hash",
    "source_document_hash",
    "native_field_hash",
    "meter_field_hash",
    "settlement_field_hash",
    "route_binding_hash",
    "capability_discovery_hash",
    "pricing_snapshot_hash",
    "rate_limit_quota_hash",
    "normalized_meter_hash",
    "provider_invoice_row_hash",
    "rdllm_settlement_meter_hash",
    "creator_settlement_hash",
    "claim_evidence_footer_hash",
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
    "raw_provider_usage_payload",
    "provider_response_body",
    "raw_billing_payload",
    "billing_payload",
    "invoice_text",
    "billing_record",
    "provider_invoice_row",
    "customer_id",
    "customer_email",
    "tenant_id",
    "account_id",
    "organization_id",
    "payment_method",
    "bank_account",
    "api_key",
    "access_token",
    "refresh_token",
    "oauth_token",
    "secret",
    "signing_secret",
    "private_key",
}

PUBLIC_ROW_KEY_ALLOWLISTS = {
    "provider_meter_surface_rows": set(REQUIRED_PROVIDER_METER_SURFACES),
    "normalized_meter_field_rows": set(REQUIRED_NORMALIZED_METER_FIELDS),
    "negative_provider_meter_rows": set(REQUIRED_NEGATIVE_PROVIDER_METER_FAILURES),
}


def load_universal_provider_meter_normalization_contract_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L185 provider meter contract."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in contract.items()
        if key not in {"universal_provider_meter_normalization_contract_hash", "signature"}
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


def _l182_ready(artifact: dict[str, Any] | None) -> bool:
    decision = artifact.get("live_capability_discovery_decision", {}) if artifact else {}
    return (
        _summary(artifact).get("status") == "ready"
        and _artifact_level(artifact) == MINIMUM_LIVE_CAPABILITY_DISCOVERY_LEVEL
        and decision.get("universal_live_capability_discovery_ready") is True
        and decision.get("model_invocation_allowed") is True
        and decision.get("source_footer_reliance_allowed") is True
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
        "meter_surface_hash",
        "schema_hash",
        "parser_hash",
        "provider_family",
        "source_document_hash",
    )
    required_bools = (
        "official_or_attested_shape_observed",
        "native_usage_present_or_zero_metered",
        "input_units_extractable",
        "output_units_extractable",
        "cache_or_reasoning_units_supported_or_explicitly_absent",
        "tool_media_or_batch_units_supported_or_explicitly_absent",
        "pricing_snapshot_bound",
        "invoice_reconciliation_supported",
        "no_private_payloads",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _field_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "meter_field_hash",
        "native_field_hash",
        "settlement_field_hash",
        "verifier_hash",
    )
    required_bools = (
        "field_required",
        "mapped_from_native_or_declared_zero",
        "hash_bound",
        "privacy_safe",
        "settlement_ledger_projected",
        "no_private_payloads",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _route_provider_meter_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "route_id",
        "provider_family",
        "provider_meter_hash",
        "route_binding_hash",
        "capability_discovery_hash",
        "pricing_snapshot_hash",
        "verifier_hash",
    )
    required_bools = (
        "l182_route_discovered",
        "l179_route_bound",
        "provider_usage_observed",
        "normalized_meter_projected",
        "provider_invoice_row_projected",
        "no_double_counting",
        "no_private_payloads",
    )
    return all(_string(row.get(field)) for field in required_strings) and all(
        _bool(row.get(field)) for field in required_bools
    )


def _settlement_meter_row_ready(row: dict[str, Any]) -> bool:
    required_strings = (
        "route_id",
        "rdllm_settlement_meter_hash",
        "provider_invoice_row_hash",
        "normalized_meter_hash",
        "creator_settlement_hash",
        "claim_evidence_footer_hash",
        "verifier_hash",
    )
    required_bools = (
        "l184_footer_bound",
        "usage_cost_attribution_bound",
        "invoice_reconciled",
        "creator_pool_inputs_preserved",
        "response_release_gate_bound",
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
            _bool(row.get("model_invocation_blocked")),
            _bool(row.get("response_release_blocked")),
            _bool(row.get("creator_settlement_held")),
            _bool(row.get("public_status_marked_failed")),
            _bool(row.get("no_private_payloads")),
        )
    )


def _required_route_ids(
    live_capability_discovery: dict[str, Any] | None,
    runtime_route_binding: dict[str, Any] | None,
    claim_evidence_footer: dict[str, Any] | None,
) -> list[str]:
    if isinstance(live_capability_discovery, dict):
        rows = live_capability_discovery.get("route_discovery_rows", {})
        if isinstance(rows, dict) and rows:
            return sorted(str(route_id) for route_id in rows)
    if isinstance(runtime_route_binding, dict):
        rows = runtime_route_binding.get("runtime_route_binding_rows", {})
        if isinstance(rows, dict) and rows:
            return sorted(str(route_id) for route_id in rows)
    if isinstance(claim_evidence_footer, dict):
        coverage = claim_evidence_footer.get("coverage", {})
        if isinstance(coverage, dict):
            route_ids = coverage.get("l183_route_ids", [])
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
        missing.append("at_least_one_l182_or_l179_route")
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


def make_universal_provider_meter_normalization_contract(
    contract_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L185 universal provider meter normalization contract."""

    claim_evidence_footer = contract_input.get(
        "universal_claim_evidence_footer_verification_contract"
    )
    live_capability_discovery = contract_input.get(
        "universal_live_capability_discovery_contract"
    )
    runtime_route_binding = contract_input.get(
        "universal_runtime_route_binding_contract"
    )
    surface_rows = _row_map(contract_input, "provider_meter_surface_rows")
    field_rows = _row_map(contract_input, "normalized_meter_field_rows")
    route_rows = _row_map(contract_input, "route_provider_meter_rows")
    settlement_rows = _row_map(contract_input, "settlement_meter_rows")
    negative_rows = _row_map(contract_input, "negative_provider_meter_rows")

    missing_surfaces, incomplete_surfaces = _complete_rows(
        surface_rows,
        REQUIRED_PROVIDER_METER_SURFACES,
        _surface_row_ready,
    )
    missing_fields, incomplete_fields = _complete_rows(
        field_rows,
        REQUIRED_NORMALIZED_METER_FIELDS,
        _field_row_ready,
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows,
        REQUIRED_NEGATIVE_PROVIDER_METER_FAILURES,
        _negative_row_ready,
    )
    route_ids = _required_route_ids(
        live_capability_discovery if isinstance(live_capability_discovery, dict) else None,
        runtime_route_binding if isinstance(runtime_route_binding, dict) else None,
        claim_evidence_footer if isinstance(claim_evidence_footer, dict) else None,
    )
    missing_routes, incomplete_routes, mismatched_routes = _route_rows_complete(
        route_rows, route_ids, _route_provider_meter_row_ready
    )
    missing_settlements, incomplete_settlements, mismatched_settlements = (
        _route_rows_complete(settlement_rows, route_ids, _settlement_meter_row_ready)
    )

    l184_ready = _l184_ready(
        claim_evidence_footer if isinstance(claim_evidence_footer, dict) else None
    )
    l182_ready = _l182_ready(
        live_capability_discovery
        if isinstance(live_capability_discovery, dict)
        else None
    )
    l179_ready = _l179_ready(
        runtime_route_binding if isinstance(runtime_route_binding, dict) else None
    )
    checks = {
        "claim_evidence_footer_l184_ready": l184_ready
        and _artifact_hash_is_reproducible(
            claim_evidence_footer
            if isinstance(claim_evidence_footer, dict)
            else None
        ),
        "live_capability_discovery_l182_ready": l182_ready
        and _artifact_hash_is_reproducible(
            live_capability_discovery
            if isinstance(live_capability_discovery, dict)
            else None
        ),
        "runtime_route_binding_l179_ready": l179_ready
        and _artifact_hash_is_reproducible(
            runtime_route_binding if isinstance(runtime_route_binding, dict) else None
        ),
        "provider_meter_surface_rows_complete": not missing_surfaces
        and not incomplete_surfaces,
        "normalized_meter_field_rows_complete": not missing_fields
        and not incomplete_fields,
        "route_provider_meter_rows_complete": (
            not missing_routes and not incomplete_routes and not mismatched_routes
        ),
        "settlement_meter_rows_complete": (
            not missing_settlements
            and not incomplete_settlements
            and not mismatched_settlements
        ),
        "negative_provider_meter_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "contract_signed": signing_secret is not None,
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    ready = not failure_modes

    surface_root = merkle_root([
        hash_payload({"meter_surface": name, "row": surface_rows.get(name, {})})
        for name in REQUIRED_PROVIDER_METER_SURFACES
    ])
    field_root = merkle_root([
        hash_payload({"normalized_meter_field": name, "row": field_rows.get(name, {})})
        for name in REQUIRED_NORMALIZED_METER_FIELDS
    ])
    route_root = merkle_root([
        hash_payload({"route_id": route_id, "row": route_rows.get(route_id, {})})
        for route_id in route_ids
    ])
    settlement_root = merkle_root([
        hash_payload(
            {"route_id": route_id, "row": settlement_rows.get(route_id, {})}
        )
        for route_id in route_ids
    ])
    negative_root = merkle_root([
        hash_payload({"failure": failure, "row": negative_rows.get(failure, {})})
        for failure in REQUIRED_NEGATIVE_PROVIDER_METER_FAILURES
    ])

    public = {
        "universal_provider_meter_normalization_contract_version": (
            UNIVERSAL_PROVIDER_METER_NORMALIZATION_CONTRACT_VERSION
        ),
        "schema": UNIVERSAL_PROVIDER_METER_NORMALIZATION_CONTRACT_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": (
                "rdllm-universal-provider-meter-normalization-policy/v1"
            ),
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_claim_evidence_footer_level": (
                MINIMUM_CLAIM_EVIDENCE_FOOTER_LEVEL
            ),
            "minimum_live_capability_discovery_level": (
                MINIMUM_LIVE_CAPABILITY_DISCOVERY_LEVEL
            ),
            "minimum_runtime_route_binding_level": MINIMUM_RUNTIME_ROUTE_BINDING_LEVEL,
            "provider_usage_must_be_observed_or_zero_metered": True,
            "native_usage_fields_must_map_to_settlement_meter": True,
            "pricing_snapshot_must_be_bound": True,
            "provider_invoice_rows_must_reconcile": True,
            "router_pass_through_usage_must_not_double_count": True,
            "missing_or_stale_metering_fails_closed": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_PROVIDER_METER_NORMALIZATION_CONTRACT_VERSION,
        },
        "artifact_bindings": {
            "universal_claim_evidence_footer_verification_contract": _artifact_binding(
                claim_evidence_footer
                if isinstance(claim_evidence_footer, dict)
                else None,
                minimum_level=MINIMUM_CLAIM_EVIDENCE_FOOTER_LEVEL,
                ready=l184_ready,
            ),
            "universal_live_capability_discovery_contract": _artifact_binding(
                live_capability_discovery
                if isinstance(live_capability_discovery, dict)
                else None,
                minimum_level=MINIMUM_LIVE_CAPABILITY_DISCOVERY_LEVEL,
                ready=l182_ready,
            ),
            "universal_runtime_route_binding_contract": _artifact_binding(
                runtime_route_binding
                if isinstance(runtime_route_binding, dict)
                else None,
                minimum_level=MINIMUM_RUNTIME_ROUTE_BINDING_LEVEL,
                ready=l179_ready,
            ),
        },
        "provider_meter_surface_rows": {
            name: surface_rows.get(name, {})
            for name in REQUIRED_PROVIDER_METER_SURFACES
        },
        "normalized_meter_field_rows": {
            name: field_rows.get(name, {})
            for name in REQUIRED_NORMALIZED_METER_FIELDS
        },
        "route_provider_meter_rows": {
            route_id: route_rows.get(route_id, {}) for route_id in route_ids
        },
        "settlement_meter_rows": {
            route_id: settlement_rows.get(route_id, {}) for route_id in route_ids
        },
        "negative_provider_meter_rows": {
            failure: negative_rows.get(failure, {})
            for failure in REQUIRED_NEGATIVE_PROVIDER_METER_FAILURES
        },
        "evidence_roots": {
            "provider_meter_surface_root": surface_root,
            "normalized_meter_field_root": field_root,
            "route_provider_meter_root": route_root,
            "settlement_meter_root": settlement_root,
            "negative_provider_meter_root": negative_root,
            "combined_provider_meter_root": merkle_root(
                [surface_root, field_root, route_root, settlement_root, negative_root]
            ),
        },
        "checks": checks,
        "provider_meter_normalization_decision": {
            "universal_provider_meter_normalization_ready": ready,
            "provider_usage_meters_normalized": ready,
            "model_invocation_allowed": ready,
            "response_release_allowed": ready,
            "source_footer_reliance_allowed": ready,
            "creator_settlement_allowed": ready,
            "missing_usage_blocked": True,
            "stale_pricing_blocked": True,
            "double_counted_usage_blocked": True,
            "private_billing_payload_blocked": True,
            "failure_modes": failure_modes,
        },
        "coverage": {
            "route_ids": route_ids,
            "missing_provider_meter_surfaces": missing_surfaces,
            "incomplete_provider_meter_surfaces": incomplete_surfaces,
            "missing_normalized_meter_fields": missing_fields,
            "incomplete_normalized_meter_fields": incomplete_fields,
            "missing_route_provider_meter_rows": missing_routes,
            "incomplete_route_provider_meter_rows": incomplete_routes,
            "mismatched_route_provider_meter_rows": mismatched_routes,
            "missing_settlement_meter_rows": missing_settlements,
            "incomplete_settlement_meter_rows": incomplete_settlements,
            "mismatched_settlement_meter_rows": mismatched_settlements,
            "missing_negative_provider_meter_failures": missing_negative,
            "incomplete_negative_provider_meter_failures": incomplete_negative,
        },
        "privacy": {
            "private_payloads_excluded": True,
            "private_prompts_excluded": True,
            "private_outputs_excluded": True,
            "private_source_text_excluded": True,
            "private_billing_payloads_excluded": True,
            "private_provider_usage_payloads_excluded": True,
            "public_contract_uses_hashes_routes_meter_classes_and_verdicts": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_claim_evidence_footer_level": (
                MINIMUM_CLAIM_EVIDENCE_FOOTER_LEVEL
            ),
            "minimum_live_capability_discovery_level": (
                MINIMUM_LIVE_CAPABILITY_DISCOVERY_LEVEL
            ),
            "minimum_runtime_route_binding_level": MINIMUM_RUNTIME_ROUTE_BINDING_LEVEL,
            "provider_meter_surface_count": len(REQUIRED_PROVIDER_METER_SURFACES),
            "ready_provider_meter_surface_count": len(REQUIRED_PROVIDER_METER_SURFACES)
            - len(missing_surfaces)
            - len(incomplete_surfaces),
            "normalized_meter_field_count": len(REQUIRED_NORMALIZED_METER_FIELDS),
            "ready_normalized_meter_field_count": len(REQUIRED_NORMALIZED_METER_FIELDS)
            - len(missing_fields)
            - len(incomplete_fields),
            "route_count": len(route_ids),
            "ready_route_provider_meter_count": len(route_ids)
            - len(missing_routes)
            - len(incomplete_routes)
            - len(mismatched_routes),
            "ready_settlement_meter_count": len(route_ids)
            - len(missing_settlements)
            - len(incomplete_settlements)
            - len(mismatched_settlements),
            "negative_provider_meter_failure_count": len(
                REQUIRED_NEGATIVE_PROVIDER_METER_FAILURES
            ),
            "ready_negative_provider_meter_failure_count": len(
                REQUIRED_NEGATIVE_PROVIDER_METER_FAILURES
            )
            - len(missing_negative)
            - len(incomplete_negative),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": True,
            "signed_provider_meter_normalization_contract": signing_secret is not None,
        },
    }
    public["universal_provider_meter_normalization_contract_hash"] = hash_payload(
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


def validate_universal_provider_meter_normalization_contract_shape(
    contract: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for an L185 provider meter contract."""

    errors: list[str] = []
    required = (
        "universal_provider_meter_normalization_contract_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "artifact_bindings",
        "provider_meter_surface_rows",
        "normalized_meter_field_rows",
        "route_provider_meter_rows",
        "settlement_meter_rows",
        "negative_provider_meter_rows",
        "evidence_roots",
        "checks",
        "provider_meter_normalization_decision",
        "coverage",
        "privacy",
        "summary",
        "universal_provider_meter_normalization_contract_hash",
    )
    for key in required:
        if key not in contract:
            errors.append(f"missing provider meter field: {key}")
    if (
        contract.get("universal_provider_meter_normalization_contract_version")
        != UNIVERSAL_PROVIDER_METER_NORMALIZATION_CONTRACT_VERSION
    ):
        errors.append(
            "unexpected universal_provider_meter_normalization_contract_version"
        )
    if contract.get("schema") != UNIVERSAL_PROVIDER_METER_NORMALIZATION_CONTRACT_SCHEMA:
        errors.append("unexpected provider meter normalization schema")
    for surface in REQUIRED_PROVIDER_METER_SURFACES:
        if surface not in contract.get("provider_meter_surface_rows", {}):
            errors.append(f"missing provider meter surface row: {surface}")
    for field in REQUIRED_NORMALIZED_METER_FIELDS:
        if field not in contract.get("normalized_meter_field_rows", {}):
            errors.append(f"missing normalized meter field row: {field}")
    for failure in REQUIRED_NEGATIVE_PROVIDER_METER_FAILURES:
        if failure not in contract.get("negative_provider_meter_rows", {}):
            errors.append(f"missing negative provider meter row: {failure}")
    for check in (
        "claim_evidence_footer_l184_ready",
        "live_capability_discovery_l182_ready",
        "runtime_route_binding_l179_ready",
        "provider_meter_surface_rows_complete",
        "normalized_meter_field_rows_complete",
        "route_provider_meter_rows_complete",
        "settlement_meter_rows_complete",
        "negative_provider_meter_fixtures_reject",
        "contract_signed",
    ):
        if check not in contract.get("checks", {}):
            errors.append(f"missing provider meter check: {check}")
    return errors


def verify_universal_provider_meter_normalization_contract(
    contract_input: dict[str, Any],
    contract: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L185 provider meter contract against replay input."""

    errors = validate_universal_provider_meter_normalization_contract_shape(contract)
    expected_hash = hash_payload(_hashable_contract(contract))
    if contract.get("universal_provider_meter_normalization_contract_hash") != expected_hash:
        errors.append("universal_provider_meter_normalization_contract_hash mismatch")
    private_fields = _contains_private_fields(contract)
    if private_fields:
        errors.append(
            "provider meter normalization contract exposes private fields: "
            + ", ".join(private_fields)
        )
    if not _private_strings_absent(contract, contract_input):
        errors.append("provider meter normalization contract exposes private input strings")
    replayed = make_universal_provider_meter_normalization_contract(
        contract_input,
        issuer=contract.get("issuer", DEFAULT_ISSUER),
        created_at=contract.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get("universal_provider_meter_normalization_contract_hash") != contract.get(
        "universal_provider_meter_normalization_contract_hash"
    ):
        errors.append("provider meter normalization contract does not match replay inputs")
    if contract.get("summary", {}).get("status") != "ready":
        errors.append("provider meter normalization contract is not ready")
    if (
        contract.get("provider_meter_normalization_decision", {}).get(
            "universal_provider_meter_normalization_ready"
        )
        is not True
    ):
        errors.append("provider meter normalization decision is not ready")
    if contract.get("privacy", {}).get("private_payloads_excluded") is not True:
        errors.append("provider meter normalization privacy is not preserved")
    if signing_secret:
        signature = contract.get("signature", {})
        expected_signature = sign_payload(_hashable_contract(contract), signing_secret)
        if not signature:
            errors.append("provider meter normalization contract is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("provider meter normalization contract signature is invalid")
    return errors
