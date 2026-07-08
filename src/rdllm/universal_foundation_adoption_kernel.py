"""Universal foundation adoption kernel.

The L156 layer turns the RDLLM proof stack into a provider-facing adoption
kernel. L155 proves that reliance and payout claims can be corrected after
publication; L156 proves that every supported foundation-model family exposes
the same source footer, status resolver, metadata, telemetry, conformance, and
fail-closed behavior needed for clients to rely on those corrections.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_FOUNDATION_ADOPTION_KERNEL_VERSION = (
    "rdllm-universal-foundation-adoption-kernel/v1"
)
UNIVERSAL_FOUNDATION_ADOPTION_KERNEL_SCHEMA = (
    "docs/schemas/universal_foundation_adoption_kernel.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L156"
MINIMUM_CORRECTION_LEVEL = "RDLLM-L155"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-foundation-adoption-kernel.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "assurance_bundle",
    "proof_dependency_graph",
    "universal_composite_rdllm_profile",
    "universal_runtime_conformance_receipt",
    "universal_claim_provenance_envelope",
    "universal_provider_wire_protocol",
    "universal_accountability_audit_trail",
    "universal_accountability_witness_quorum",
    "universal_grounded_reliance_contract",
    "universal_reliance_correction_ledger",
    "response_envelope",
    "source_footer_delivery",
    "client_attribution_enforcement",
    "citation_url_health",
    "source_freshness_audit",
    "evidence_locator_manifest",
    "warranted_source_footer",
    "revenue_allocation_report",
    "finance_ledger_attestation",
    "trust_registry",
)

REQUIRED_PROVIDER_FAMILIES = (
    "openai",
    "anthropic",
    "google_gemini",
    "azure_openai",
    "aws_bedrock",
    "meta",
    "mistral",
    "cohere",
    "xai",
    "deepseek",
    "openrouter_compatible",
    "local_open_weights",
    "enterprise_gateway",
)

REQUIRED_KERNEL_ENDPOINTS = (
    "well_known_discovery",
    "adoption_kernel",
    "response_envelope",
    "source_status_resolver",
    "correction_feed",
    "proof_bundle",
    "challenge_endpoint",
    "settlement_meter",
    "creator_query",
    "regulator_export",
)

REQUIRED_RESPONSE_BINDINGS = (
    "response_headers",
    "json_body_proofs",
    "streaming_events",
    "tool_call_results",
    "sdk_metadata",
    "gateway_proxy_transforms",
    "batch_callbacks",
    "webhooks",
    "exported_copy_capsules",
    "rendered_footer_rows",
)

REQUIRED_CLIENT_GATES = (
    "verify_before_render",
    "render_source_footer",
    "resolve_live_status",
    "block_revoked_footer",
    "invalidate_stale_cache",
    "preserve_copy_status_link",
    "show_confidence_downgrade",
    "route_creator_challenge",
    "hold_settlement_on_revocation",
    "regulator_export_on_notice",
)

REQUIRED_TEXT_ATTRIBUTION_GUARANTEES = (
    "claim_extraction_before_footer",
    "claim_to_source_support",
    "citation_identity_verification",
    "evidence_locator_resolution",
    "retrieval_reliance_trace",
    "counterfactual_reliance_check",
    "source_quality_scoring",
    "freshness_and_url_health",
    "unsupported_claim_refusal",
    "copy_export_footer_persistence",
)

REQUIRED_STANDARD_MAPPINGS = (
    "opentelemetry_genai_semconv",
    "model_context_protocol",
    "c2pa_content_credentials_2_4",
    "w3c_bitstring_status_list",
    "ietf_scitt_rfc9943",
    "rfc9162_transparency_log",
    "sigstore_rekor",
    "nist_ai_rmf_generative_profile",
    "eu_ai_act_gpai_transparency_copyright",
    "spdx_cyclonedx_attribution_bom",
)

REQUIRED_FAILURE_CASES = (
    "provider_family_missing_adapter",
    "metadata_stripped_by_proxy",
    "stream_event_missing_proof",
    "source_footer_without_status_resolver",
    "revoked_source_still_rendered",
    "citation_url_unverified",
    "claim_provenance_missing",
    "text_claim_without_support_rendered",
    "posthoc_citation_laundering",
    "telemetry_span_missing",
    "settlement_meter_unbound",
    "negative_fixture_passes_unexpectedly",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_foundation_adoption_kernel_hash",
    "universal_reliance_correction_ledger_hash",
    "universal_grounded_reliance_contract_hash",
    "universal_accountability_witness_quorum_hash",
    "universal_accountability_audit_trail_hash",
    "universal_provider_wire_protocol_hash",
    "universal_claim_provenance_envelope_hash",
    "universal_runtime_conformance_receipt_hash",
    "universal_composite_rdllm_profile_hash",
    "source_footer_delivery_hash",
    "client_enforcement_hash",
    "citation_url_health_hash",
    "source_freshness_audit_hash",
    "evidence_locator_manifest_hash",
    "warranted_source_footer_hash",
    "trust_registry_hash",
    "attestation_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "contract_hash",
    "graph_hash",
    "report_hash",
    "bundle_hash",
    "summary_hash",
    "receipt_hash",
    "envelope_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "query_text",
    "output",
    "output_text",
    "answer_text",
    "raw_answer_text",
    "raw_model_output",
    "raw_native_request",
    "raw_native_response",
    "native_response_body",
    "source_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
    "tool_payload",
    "raw_tool_output",
    "memory_value",
    "raw_memory",
    "customer_id",
    "customer_email",
    "billing_record",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "authorization",
    "access_token",
    "refresh_token",
    "oauth_token",
    "api_key",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_foundation_adoption_kernel_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L156 adoption kernel."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_kernel(kernel: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in kernel.items()
        if key not in {"universal_foundation_adoption_kernel_hash", "signature"}
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


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}" if path else f"/{key}"
            if str(key) in PRIVATE_FIELD_NAMES:
                findings.append(child_path)
            findings.extend(_contains_private_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_contains_private_fields(child, f"{path}/{index}"))
    return findings


def _private_strings_absent(
    public_payload: dict[str, Any], kernel_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in kernel_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    summary = artifact.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def _artifact_status(artifact: dict[str, Any] | None) -> str:
    return str(_summary(artifact).get("status", ""))


def _artifact_target_level(artifact: dict[str, Any] | None) -> str:
    summary = _summary(artifact)
    return str(
        summary.get("target_certification_level")
        or summary.get("highest_level")
        or summary.get("attested_highest_level")
        or ""
    )


def _artifact_version(artifact: dict[str, Any] | None) -> str:
    if not artifact:
        return ""
    for key, value in artifact.items():
        if key.endswith("_version") and isinstance(value, str):
            return value
    return ""


def _level_number(level: Any) -> int:
    if not isinstance(level, str):
        return -1
    try:
        return int(level.removeprefix("RDLLM-L"))
    except ValueError:
        return -1


def _level_at_least(level: Any, minimum: str) -> bool:
    return _level_number(level) >= _level_number(minimum)


def _component_input_map(
    kernel_input: dict[str, Any], key: str
) -> dict[str, dict[str, Any]]:
    value = kernel_input.get(key, {})
    if isinstance(value, dict):
        return {str(name): row for name, row in value.items() if isinstance(row, dict)}
    if isinstance(value, list):
        result: dict[str, dict[str, Any]] = {}
        for row in value:
            if not isinstance(row, dict):
                continue
            name = (
                row.get("provider_family")
                or row.get("endpoint")
                or row.get("binding")
                or row.get("gate")
                or row.get("guarantee")
                or row.get("standard")
                or row.get("case_id")
            )
            if name:
                result[str(name)] = row
        return result
    return {}


def _policy(kernel_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(kernel_input.get("foundation_adoption_policy", {}))
    return {
        "profile": "rdllm-universal-foundation-adoption-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_correction_level": MINIMUM_CORRECTION_LEVEL,
        "well_known_path": DEFAULT_WELL_KNOWN_PATH,
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_provider_families": list(
            policy.get("required_provider_families", REQUIRED_PROVIDER_FAMILIES)
        ),
        "required_kernel_endpoints": list(
            policy.get("required_kernel_endpoints", REQUIRED_KERNEL_ENDPOINTS)
        ),
        "required_response_bindings": list(
            policy.get("required_response_bindings", REQUIRED_RESPONSE_BINDINGS)
        ),
        "required_client_gates": list(
            policy.get("required_client_gates", REQUIRED_CLIENT_GATES)
        ),
        "required_text_attribution_guarantees": list(
            policy.get(
                "required_text_attribution_guarantees",
                REQUIRED_TEXT_ATTRIBUTION_GUARANTEES,
            )
        ),
        "required_standard_mappings": list(
            policy.get("required_standard_mappings", REQUIRED_STANDARD_MAPPINGS)
        ),
        "required_failure_cases": list(
            policy.get("required_failure_cases", REQUIRED_FAILURE_CASES)
        ),
        "provider_rule": "every_supported_foundation_model_family_must_expose_the_same_rdllm_metadata_footer_status_and_conformance_contract",
        "client_rule": "clients_must_verify_the_kernel_response_bindings_and_live_source_status_before_rendering_grounded_output",
        "text_attribution_rule": "every_user_visible_text_claim_or_sentence_must_bind_to_generation_time_claim_provenance_source_support_reliance_status_and_footer_rows_before_display",
        "citation_reliance_rule": "source_footers_must_prove_support_and_reliance_not_posthoc_source_lookup_or_decorative_citation_generation",
        "settlement_rule": "provider_api_routes_must_bind_source_status_and_settlement_meters_to_the_same_response_identity",
        "privacy_rule": "public_kernel_contains_hashes_roots_counts_statuses_and_paths_not_private_prompts_outputs_sources_or_accounts",
    }


def _artifact_bindings(kernel_input: dict[str, Any], names: list[str]) -> dict[str, Any]:
    rows = []
    for name in names:
        artifact = kernel_input.get(name)
        if not isinstance(artifact, dict):
            artifact = None
        row = {
            "name": name,
            "version": _artifact_version(artifact),
            "declared_hash": _declared_hash(artifact),
            "payload_hash": hash_payload(artifact) if artifact else "",
            "hash_reproducible": _artifact_hash_is_reproducible(artifact),
            "status": _artifact_status(artifact),
            "target_level": _artifact_target_level(artifact),
            "present": bool(artifact),
        }
        row["artifact_binding_hash"] = hash_payload(row)
        rows.append(row)
    return {
        "artifact_count": len(rows),
        "artifact_binding_root": merkle_root(
            [row["artifact_binding_hash"] for row in rows]
        ),
        "bindings": rows,
    }


def _binding_by_name(artifact_bindings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("name", "")): row
        for row in artifact_bindings.get("bindings", [])
        if isinstance(row, dict)
    }


def _provider_family_rows(
    kernel_input: dict[str, Any], required_families: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(kernel_input, "provider_family_rows")
    wire_hash = _declared_hash(kernel_input.get("universal_provider_wire_protocol"))
    correction_hash = _declared_hash(
        kernel_input.get("universal_reliance_correction_ledger")
    )
    rows = []
    for family in required_families:
        item = row_map.get(family, {})
        row = {
            "provider_family": family,
            "native_route_hash": str(item.get("native_route_hash", "")),
            "adapter_hash": str(item.get("adapter_hash", "")),
            "conformance_fixture_hash": str(
                item.get("conformance_fixture_hash", "")
            ),
            "negative_fixture_root": str(item.get("negative_fixture_root", "")),
            "wire_protocol_hash": str(item.get("wire_protocol_hash", wire_hash)),
            "correction_ledger_hash": str(
                item.get("correction_ledger_hash", correction_hash)
            ),
            "status_resolver_endpoint_hash": str(
                item.get("status_resolver_endpoint_hash", "")
            ),
            "supports_sync": item.get("supports_sync") is True,
            "supports_stream": item.get("supports_stream") is True,
            "supports_tools_or_context": item.get("supports_tools_or_context") is True,
            "preserves_rdllm_metadata": item.get("preserves_rdllm_metadata") is True,
            "exposes_source_status": item.get("exposes_source_status") is True,
            "renders_status_link": item.get("renders_status_link") is True,
            "telemetry_mapped": item.get("telemetry_mapped") is True,
            "settlement_meter_bound": item.get("settlement_meter_bound") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            bool(row["native_route_hash"])
            and bool(row["adapter_hash"])
            and bool(row["conformance_fixture_hash"])
            and bool(row["negative_fixture_root"])
            and row["wire_protocol_hash"] == wire_hash
            and row["correction_ledger_hash"] == correction_hash
            and bool(row["status_resolver_endpoint_hash"])
            and row["supports_sync"]
            and row["supports_stream"]
            and row["supports_tools_or_context"]
            and row["preserves_rdllm_metadata"]
            and row["exposes_source_status"]
            and row["renders_status_link"]
            and row["telemetry_mapped"]
            and row["settlement_meter_bound"]
            and row["fail_closed"]
        )
        row["provider_family_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _kernel_endpoint_rows(
    kernel_input: dict[str, Any], required_endpoints: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(kernel_input, "kernel_endpoint_rows")
    rows = []
    for endpoint in required_endpoints:
        item = row_map.get(endpoint, {})
        row = {
            "endpoint": endpoint,
            "path": str(item.get("path", "")),
            "method": str(item.get("method", "GET")),
            "schema": str(item.get("schema", "")),
            "endpoint_hash": str(item.get("endpoint_hash", "")),
            "verifier_command": str(item.get("verifier_command", "")),
            "public_or_customer_visible": item.get("public_or_customer_visible")
            is True,
            "machine_readable": item.get("machine_readable") is True,
            "cache_controlled": item.get("cache_controlled") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            bool(row["path"])
            and row["method"] in {"GET", "POST"}
            and bool(row["schema"])
            and bool(row["endpoint_hash"])
            and row["verifier_command"]
            == "verify-universal-foundation-adoption-kernel"
            and row["public_or_customer_visible"]
            and row["machine_readable"]
            and row["cache_controlled"]
            and row["privacy_preserving"]
            and row["fail_closed"]
        )
        row["kernel_endpoint_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _response_binding_rows(
    kernel_input: dict[str, Any], required_bindings: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(kernel_input, "response_binding_rows")
    envelope_hash = _declared_hash(kernel_input.get("response_envelope"))
    wire_hash = _declared_hash(kernel_input.get("universal_provider_wire_protocol"))
    claim_hash = _declared_hash(kernel_input.get("universal_claim_provenance_envelope"))
    correction_hash = _declared_hash(
        kernel_input.get("universal_reliance_correction_ledger")
    )
    rows = []
    for binding in required_bindings:
        item = row_map.get(binding, {})
        row = {
            "binding": binding,
            "field_path_hash": str(item.get("field_path_hash", "")),
            "envelope_hash": str(item.get("envelope_hash", envelope_hash)),
            "wire_protocol_hash": str(item.get("wire_protocol_hash", wire_hash)),
            "claim_provenance_hash": str(
                item.get("claim_provenance_hash", claim_hash)
            ),
            "correction_ledger_hash": str(
                item.get("correction_ledger_hash", correction_hash)
            ),
            "required_in_sync": item.get("required_in_sync") is True,
            "required_in_stream": item.get("required_in_stream") is True,
            "survives_proxy_or_sdk": item.get("survives_proxy_or_sdk") is True,
            "client_visible_or_verifiable": item.get("client_visible_or_verifiable")
            is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            bool(row["field_path_hash"])
            and row["envelope_hash"] == envelope_hash
            and row["wire_protocol_hash"] == wire_hash
            and row["claim_provenance_hash"] == claim_hash
            and row["correction_ledger_hash"] == correction_hash
            and row["required_in_sync"]
            and row["required_in_stream"]
            and row["survives_proxy_or_sdk"]
            and row["client_visible_or_verifiable"]
            and row["privacy_preserving"]
            and row["fail_closed"]
        )
        row["response_binding_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _client_gate_rows(
    kernel_input: dict[str, Any], required_gates: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(kernel_input, "client_gate_rows")
    client_hash = _declared_hash(kernel_input.get("client_attribution_enforcement"))
    correction_hash = _declared_hash(
        kernel_input.get("universal_reliance_correction_ledger")
    )
    footer_hash = _declared_hash(kernel_input.get("source_footer_delivery"))
    rows = []
    for gate in required_gates:
        item = row_map.get(gate, {})
        row = {
            "gate": gate,
            "client_enforcement_hash": str(
                item.get("client_enforcement_hash", client_hash)
            ),
            "correction_ledger_hash": str(
                item.get("correction_ledger_hash", correction_hash)
            ),
            "source_footer_delivery_hash": str(
                item.get("source_footer_delivery_hash", footer_hash)
            ),
            "gate_evidence_hash": str(item.get("gate_evidence_hash", "")),
            "verifies_before_render": item.get("verifies_before_render") is True,
            "blocks_on_missing": item.get("blocks_on_missing") is True,
            "blocks_on_revoked": item.get("blocks_on_revoked") is True,
            "updates_or_invalidates_cache": item.get("updates_or_invalidates_cache")
            is True,
            "preserves_copy_status": item.get("preserves_copy_status") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            row["client_enforcement_hash"] == client_hash
            and row["correction_ledger_hash"] == correction_hash
            and row["source_footer_delivery_hash"] == footer_hash
            and bool(row["gate_evidence_hash"])
            and row["verifies_before_render"]
            and row["blocks_on_missing"]
            and row["blocks_on_revoked"]
            and row["updates_or_invalidates_cache"]
            and row["preserves_copy_status"]
            and row["privacy_preserving"]
            and row["fail_closed"]
        )
        row["client_gate_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _text_attribution_rows(
    kernel_input: dict[str, Any], required_guarantees: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(kernel_input, "text_attribution_rows")
    claim_hash = _declared_hash(kernel_input.get("universal_claim_provenance_envelope"))
    footer_hash = _declared_hash(kernel_input.get("source_footer_delivery"))
    warranted_hash = _declared_hash(kernel_input.get("warranted_source_footer"))
    citation_url_hash = _declared_hash(kernel_input.get("citation_url_health"))
    freshness_hash = _declared_hash(kernel_input.get("source_freshness_audit"))
    locator_hash = _declared_hash(kernel_input.get("evidence_locator_manifest"))
    correction_hash = _declared_hash(
        kernel_input.get("universal_reliance_correction_ledger")
    )
    rows = []
    for guarantee in required_guarantees:
        item = row_map.get(guarantee, {})
        row = {
            "guarantee": guarantee,
            "claim_provenance_hash": str(
                item.get("claim_provenance_hash", claim_hash)
            ),
            "source_footer_delivery_hash": str(
                item.get("source_footer_delivery_hash", footer_hash)
            ),
            "warranted_source_footer_hash": str(
                item.get("warranted_source_footer_hash", warranted_hash)
            ),
            "citation_url_health_hash": str(
                item.get("citation_url_health_hash", citation_url_hash)
            ),
            "source_freshness_audit_hash": str(
                item.get("source_freshness_audit_hash", freshness_hash)
            ),
            "evidence_locator_manifest_hash": str(
                item.get("evidence_locator_manifest_hash", locator_hash)
            ),
            "correction_ledger_hash": str(
                item.get("correction_ledger_hash", correction_hash)
            ),
            "verifier_evidence_hash": str(item.get("verifier_evidence_hash", "")),
            "claim_granularity": str(
                item.get("claim_granularity", "claim_or_sentence")
            ),
            "source_support_verified": item.get("source_support_verified") is True,
            "citation_identity_verified": item.get("citation_identity_verified")
            is True,
            "locator_live_or_status_bound": item.get("locator_live_or_status_bound")
            is True,
            "retrieval_reliance_recorded": item.get("retrieval_reliance_recorded")
            is True,
            "causal_or_counterfactual_reliance_recorded": item.get(
                "causal_or_counterfactual_reliance_recorded"
            )
            is True,
            "source_quality_scored": item.get("source_quality_scored") is True,
            "unsupported_claim_blocked": item.get("unsupported_claim_blocked")
            is True,
            "posthoc_citation_blocked": item.get("posthoc_citation_blocked") is True,
            "rendered_footer_row_bound": item.get("rendered_footer_row_bound")
            is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            row["claim_provenance_hash"] == claim_hash
            and row["source_footer_delivery_hash"] == footer_hash
            and row["warranted_source_footer_hash"] == warranted_hash
            and row["citation_url_health_hash"] == citation_url_hash
            and row["source_freshness_audit_hash"] == freshness_hash
            and row["evidence_locator_manifest_hash"] == locator_hash
            and row["correction_ledger_hash"] == correction_hash
            and bool(row["verifier_evidence_hash"])
            and row["claim_granularity"] in {"claim", "sentence", "claim_or_sentence"}
            and row["source_support_verified"]
            and row["citation_identity_verified"]
            and row["locator_live_or_status_bound"]
            and row["retrieval_reliance_recorded"]
            and row["causal_or_counterfactual_reliance_recorded"]
            and row["source_quality_scored"]
            and row["unsupported_claim_blocked"]
            and row["posthoc_citation_blocked"]
            and row["rendered_footer_row_bound"]
            and row["privacy_preserving"]
            and row["fail_closed"]
        )
        row["text_attribution_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _standard_mapping_rows(
    kernel_input: dict[str, Any], required_standards: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(kernel_input, "standard_mapping_rows")
    rows = []
    for standard in sorted(required_standards):
        item = row_map.get(standard, {})
        row = {
            "standard": standard,
            "reference_url": str(item.get("reference_url", "")),
            "mapped_surface_count": int(item.get("mapped_surface_count", 0) or 0),
            "implementation_hash": str(item.get("implementation_hash", "")),
            "verifier_command": str(item.get("verifier_command", "")),
            "machine_readable": item.get("machine_readable") is True,
            "externally_auditable": item.get("externally_auditable") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            row["reference_url"].startswith("https://")
            and row["mapped_surface_count"] > 0
            and bool(row["implementation_hash"])
            and row["verifier_command"]
            == "verify-universal-foundation-adoption-kernel"
            and row["machine_readable"]
            and row["externally_auditable"]
            and row["fail_closed"]
        )
        row["standard_mapping_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _failure_case_rows(
    kernel_input: dict[str, Any], required_cases: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(kernel_input, "failure_case_rows")
    rows = []
    for case_id in sorted(required_cases):
        item = row_map.get(case_id, {})
        row = {
            "case_id": case_id,
            "fixture_hash": str(item.get("fixture_hash", "")),
            "verifier_command": str(item.get("verifier_command", "")),
            "expected_block": item.get("expected_block") is True,
            "observed_block": item.get("observed_block") is True,
        }
        row["ready"] = (
            bool(row["fixture_hash"])
            and row["verifier_command"]
            == "verify-universal-foundation-adoption-kernel"
            and row["expected_block"]
            and row["observed_block"]
        )
        row["failure_case_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _all_ready(rows: list[dict[str, Any]]) -> bool:
    return bool(rows) and all(row.get("ready") is True for row in rows)


def _count(rows: list[dict[str, Any]], key: str = "ready") -> int:
    return sum(1 for row in rows if row.get(key) is True)


def _artifact_summary(kernel_input: dict[str, Any], name: str) -> dict[str, Any]:
    artifact = kernel_input.get(name)
    return _summary(artifact if isinstance(artifact, dict) else None)


def make_universal_foundation_adoption_kernel(
    kernel_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create the L156 universal foundation adoption kernel artifact."""

    policy = _policy(kernel_input)
    required_artifacts = list(policy["required_core_artifacts"])
    artifact_bindings = _artifact_bindings(kernel_input, required_artifacts)
    bindings = _binding_by_name(artifact_bindings)
    provider_family_rows = _provider_family_rows(
        kernel_input, list(policy["required_provider_families"])
    )
    kernel_endpoint_rows = _kernel_endpoint_rows(
        kernel_input, list(policy["required_kernel_endpoints"])
    )
    response_binding_rows = _response_binding_rows(
        kernel_input, list(policy["required_response_bindings"])
    )
    client_gate_rows = _client_gate_rows(
        kernel_input, list(policy["required_client_gates"])
    )
    text_attribution_rows = _text_attribution_rows(
        kernel_input, list(policy["required_text_attribution_guarantees"])
    )
    standard_mapping_rows = _standard_mapping_rows(
        kernel_input, list(policy["required_standard_mappings"])
    )
    failure_case_rows = _failure_case_rows(
        kernel_input, list(policy["required_failure_cases"])
    )

    provider_card = kernel_input.get("provider_attribution_card", {})
    if not isinstance(provider_card, dict):
        provider_card = {}
    integration_profile = kernel_input.get("integration_profile", {})
    if not isinstance(integration_profile, dict):
        integration_profile = {}
    discovery_manifest = kernel_input.get("discovery_manifest", {})
    if not isinstance(discovery_manifest, dict):
        discovery_manifest = {}
    correction_summary = _artifact_summary(
        kernel_input, "universal_reliance_correction_ledger"
    )
    certification_summary = _artifact_summary(kernel_input, "certification_report")
    proof_summary = _artifact_summary(kernel_input, "proof_dependency_graph")

    core_artifacts_ready = all(
        row.get("present") is True
        and row.get("hash_reproducible") is True
        and row.get("status") in {"", "ready", "passed", "verified", "attested"}
        for row in bindings.values()
    )
    checks = {
        "all_core_artifacts_present_and_hash_reproducible": core_artifacts_ready,
        "certification_reaches_l155": _level_at_least(
            certification_summary.get("highest_level"), MINIMUM_CORRECTION_LEVEL
        ),
        "l155_correction_ledger_ready": (
            correction_summary.get("status") == "ready"
            and correction_summary.get("target_certification_level")
            == MINIMUM_CORRECTION_LEVEL
        ),
        "proof_graph_ready_l155": (
            proof_summary.get("status") == "ready"
            and _level_at_least(
                proof_summary.get("target_certification_level"),
                MINIMUM_CORRECTION_LEVEL,
            )
            and int(proof_summary.get("cycle_node_count", 0) or 0) == 0
        ),
        "all_provider_families_ready": _all_ready(provider_family_rows),
        "all_kernel_endpoints_ready": _all_ready(kernel_endpoint_rows),
        "all_response_bindings_ready": _all_ready(response_binding_rows),
        "all_client_gates_ready": _all_ready(client_gate_rows),
        "all_text_attribution_guarantees_ready": _all_ready(text_attribution_rows),
        "all_standard_mappings_ready": _all_ready(standard_mapping_rows),
        "all_negative_failure_cases_ready": _all_ready(failure_case_rows),
        "provider_card_declares_kernel": provider_card.get(
            "public_disclosure_surfaces", {}
        ).get("universal_foundation_adoption_kernel")
        is True,
        "integration_profile_declares_kernel": (
            integration_profile.get("public_surfaces", {}).get(
                "universal_foundation_adoption_kernel"
            )
            is True
            and integration_profile.get("schemas", {}).get(
                "universal_foundation_adoption_kernel"
            )
            == UNIVERSAL_FOUNDATION_ADOPTION_KERNEL_SCHEMA
        ),
        "discovery_manifest_exposes_kernel": (
            discovery_manifest.get("discovery", {}).get(
                "universal_foundation_adoption_kernel_path"
            )
            == DEFAULT_WELL_KNOWN_PATH
            and discovery_manifest.get("schemas", {}).get(
                "universal_foundation_adoption_kernel"
            )
            == UNIVERSAL_FOUNDATION_ADOPTION_KERNEL_SCHEMA
        ),
    }

    failure_modes = []
    if not checks["all_core_artifacts_present_and_hash_reproducible"]:
        failure_modes.append("kernel_artifact_gap")
    if not checks["certification_reaches_l155"] or not checks[
        "l155_correction_ledger_ready"
    ]:
        failure_modes.append("kernel_correction_level_gap")
    if not checks["proof_graph_ready_l155"]:
        failure_modes.append("kernel_proof_graph_gap")
    if not checks["all_provider_families_ready"]:
        failure_modes.append("kernel_provider_family_gap")
    if not checks["all_kernel_endpoints_ready"]:
        failure_modes.append("kernel_endpoint_gap")
    if not checks["all_response_bindings_ready"]:
        failure_modes.append("kernel_response_binding_gap")
    if not checks["all_client_gates_ready"]:
        failure_modes.append("kernel_client_gate_gap")
    if not checks["all_text_attribution_guarantees_ready"]:
        failure_modes.append("kernel_text_attribution_gap")
    if not checks["all_standard_mappings_ready"]:
        failure_modes.append("kernel_standard_mapping_gap")
    if not checks["all_negative_failure_cases_ready"]:
        failure_modes.append("kernel_negative_fixture_gap")
    if not (
        checks["provider_card_declares_kernel"]
        and checks["integration_profile_declares_kernel"]
        and checks["discovery_manifest_exposes_kernel"]
    ):
        failure_modes.append("kernel_public_surface_gap")

    evidence_commitments = {
        "artifact_binding_root": artifact_bindings["artifact_binding_root"],
        "provider_family_root": merkle_root(
            [row["provider_family_row_hash"] for row in provider_family_rows]
        ),
        "kernel_endpoint_root": merkle_root(
            [row["kernel_endpoint_row_hash"] for row in kernel_endpoint_rows]
        ),
        "response_binding_root": merkle_root(
            [row["response_binding_row_hash"] for row in response_binding_rows]
        ),
        "client_gate_root": merkle_root(
            [row["client_gate_row_hash"] for row in client_gate_rows]
        ),
        "text_attribution_root": merkle_root(
            [row["text_attribution_row_hash"] for row in text_attribution_rows]
        ),
        "standard_mapping_root": merkle_root(
            [row["standard_mapping_row_hash"] for row in standard_mapping_rows]
        ),
        "failure_case_root": merkle_root(
            [row["failure_case_row_hash"] for row in failure_case_rows]
        ),
    }
    adoption_decision = {
        "foundation_adoption_kernel_authorized": not failure_modes,
        "unverified_foundation_model_output_allowed": False,
        "source_footer_without_status_resolver_allowed": False,
        "metadata_stripping_proxy_allowed": False,
        "provider_family_without_adapter_allowed": False,
        "posthoc_citation_laundering_allowed": False,
        "unsupported_claim_rendering_allowed": False,
        "direct_settlement_without_status_binding_allowed": False,
        "failure_modes": failure_modes,
    }
    privacy = {
        "private_field_paths": _contains_private_fields(
            {
                "foundation_adoption_policy": policy,
                "artifact_bindings": artifact_bindings,
                "provider_family_rows": provider_family_rows,
                "kernel_endpoint_rows": kernel_endpoint_rows,
                "response_binding_rows": response_binding_rows,
                "client_gate_rows": client_gate_rows,
                "text_attribution_rows": text_attribution_rows,
                "standard_mapping_rows": standard_mapping_rows,
                "failure_case_rows": failure_case_rows,
            }
        ),
        "private_strings_absent": True,
        "raw_prompts_outputs_sources_or_accounts_embedded": False,
    }
    summary = {
        "status": "ready" if adoption_decision["foundation_adoption_kernel_authorized"] else "blocked",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_correction_level": MINIMUM_CORRECTION_LEVEL,
        "core_artifact_count": artifact_bindings["artifact_count"],
        "provider_family_count": len(provider_family_rows),
        "ready_provider_family_count": _count(provider_family_rows),
        "kernel_endpoint_count": len(kernel_endpoint_rows),
        "ready_kernel_endpoint_count": _count(kernel_endpoint_rows),
        "response_binding_count": len(response_binding_rows),
        "ready_response_binding_count": _count(response_binding_rows),
        "client_gate_count": len(client_gate_rows),
        "ready_client_gate_count": _count(client_gate_rows),
        "text_attribution_guarantee_count": len(text_attribution_rows),
        "ready_text_attribution_guarantee_count": _count(text_attribution_rows),
        "standard_mapping_count": len(standard_mapping_rows),
        "ready_standard_mapping_count": _count(standard_mapping_rows),
        "failure_case_count": len(failure_case_rows),
        "failure_mode_count": len(failure_modes),
        "offline_verification_supported": True,
        "provider_neutral_adoption_supported": not failure_modes,
        "source_status_resolver_required": True,
        "client_footer_grounding_required": True,
        "claim_level_text_attribution_required": True,
        "privacy_preserved": not privacy["private_field_paths"],
    }
    kernel = {
        "foundation_adoption_kernel_version": UNIVERSAL_FOUNDATION_ADOPTION_KERNEL_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "foundation_adoption_policy": policy,
        "artifact_bindings": artifact_bindings,
        "provider_family_rows": provider_family_rows,
        "kernel_endpoint_rows": kernel_endpoint_rows,
        "response_binding_rows": response_binding_rows,
        "client_gate_rows": client_gate_rows,
        "text_attribution_rows": text_attribution_rows,
        "standard_mapping_rows": standard_mapping_rows,
        "failure_case_rows": failure_case_rows,
        "evidence_commitments": evidence_commitments,
        "checks": checks,
        "adoption_decision": adoption_decision,
        "verifier_commands": {
            "create": "universal-foundation-adoption-kernel",
            "verify": "verify-universal-foundation-adoption-kernel",
            "well_known_path": DEFAULT_WELL_KNOWN_PATH,
            "schema": UNIVERSAL_FOUNDATION_ADOPTION_KERNEL_SCHEMA,
        },
        "standards_controls": {
            "opentelemetry_genai_semconv": "https://opentelemetry.io/docs/specs/semconv/gen-ai/",
            "model_context_protocol": "https://modelcontextprotocol.io/specification/2025-11-25/",
            "c2pa_content_credentials_2_4": "https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html",
            "w3c_bitstring_status_list": "https://www.w3.org/TR/vc-bitstring-status-list/",
            "ietf_scitt_rfc9943": "https://www.rfc-editor.org/rfc/rfc9943.html",
            "rfc9162_transparency_log": "https://www.rfc-editor.org/rfc/rfc9162.html",
            "sigstore_rekor": "https://docs.sigstore.dev/logging/overview/",
            "nist_ai_rmf_generative_profile": "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf",
            "eu_ai_act_gpai_transparency_copyright": "https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai",
            "spdx_cyclonedx_attribution_bom": "https://cyclonedx.org/",
        },
        "privacy": privacy,
        "summary": summary,
    }
    kernel["privacy"]["private_strings_absent"] = _private_strings_absent(
        kernel, kernel_input
    )
    if not kernel["privacy"]["private_strings_absent"]:
        kernel["adoption_decision"]["failure_modes"].append("kernel_private_string_leak")
        kernel["summary"]["status"] = "blocked"
        kernel["summary"]["failure_mode_count"] = len(
            kernel["adoption_decision"]["failure_modes"]
        )
        kernel["summary"]["privacy_preserved"] = False
    kernel["universal_foundation_adoption_kernel_hash"] = hash_payload(
        _hashable_kernel(kernel)
    )
    if signing_secret:
        kernel["signature"] = sign_payload(
            kernel["universal_foundation_adoption_kernel_hash"], signing_secret
        )
    return kernel


def validate_universal_foundation_adoption_kernel_shape(
    kernel: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    required = (
        "foundation_adoption_kernel_version",
        "issuer",
        "created_at",
        "foundation_adoption_policy",
        "artifact_bindings",
        "provider_family_rows",
        "kernel_endpoint_rows",
        "response_binding_rows",
        "client_gate_rows",
        "text_attribution_rows",
        "standard_mapping_rows",
        "failure_case_rows",
        "evidence_commitments",
        "checks",
        "adoption_decision",
        "verifier_commands",
        "standards_controls",
        "privacy",
        "summary",
        "universal_foundation_adoption_kernel_hash",
    )
    for key in required:
        if key not in kernel:
            errors.append(f"missing universal foundation adoption kernel field: {key}")
    if errors:
        return errors
    if (
        kernel.get("foundation_adoption_kernel_version")
        != UNIVERSAL_FOUNDATION_ADOPTION_KERNEL_VERSION
    ):
        errors.append("universal foundation adoption kernel version is unsupported")
    if kernel.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal foundation adoption kernel target level is not RDLLM-L156")
    if (
        kernel.get("foundation_adoption_policy", {}).get("well_known_path")
        != DEFAULT_WELL_KNOWN_PATH
    ):
        errors.append("universal foundation adoption kernel well-known path is invalid")
    decision = kernel.get("adoption_decision", {})
    if decision.get("unverified_foundation_model_output_allowed") is not False:
        errors.append("universal foundation adoption kernel permits unverified output")
    if decision.get("source_footer_without_status_resolver_allowed") is not False:
        errors.append("universal foundation adoption kernel permits footer without resolver")
    if decision.get("metadata_stripping_proxy_allowed") is not False:
        errors.append("universal foundation adoption kernel permits metadata stripping")
    if decision.get("provider_family_without_adapter_allowed") is not False:
        errors.append("universal foundation adoption kernel permits provider without adapter")
    if decision.get("posthoc_citation_laundering_allowed") is not False:
        errors.append("universal foundation adoption kernel permits posthoc citation laundering")
    if decision.get("unsupported_claim_rendering_allowed") is not False:
        errors.append("universal foundation adoption kernel permits unsupported claim rendering")
    return errors


def verify_universal_foundation_adoption_kernel(
    kernel: dict[str, Any],
    *,
    kernel_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L156 adoption kernel artifact against private replay input."""

    errors = validate_universal_foundation_adoption_kernel_shape(kernel)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_kernel(kernel))
    if expected_hash != kernel.get("universal_foundation_adoption_kernel_hash"):
        errors.append("universal foundation adoption kernel hash is not reproducible")

    expected = make_universal_foundation_adoption_kernel(
        kernel_input,
        issuer=kernel.get("issuer", DEFAULT_ISSUER),
        created_at=kernel.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "foundation_adoption_policy",
        "artifact_bindings",
        "provider_family_rows",
        "kernel_endpoint_rows",
        "response_binding_rows",
        "client_gate_rows",
        "standard_mapping_rows",
        "failure_case_rows",
        "evidence_commitments",
        "checks",
        "adoption_decision",
        "verifier_commands",
        "standards_controls",
        "privacy",
        "summary",
    ):
        if expected.get(key) != kernel.get(key):
            errors.append(f"universal foundation adoption kernel {key} does not match replay input")
    if (
        expected.get("universal_foundation_adoption_kernel_hash")
        != kernel.get("universal_foundation_adoption_kernel_hash")
    ):
        errors.append("universal foundation adoption kernel hash does not match replay input")
    if signing_secret and expected.get("signature") != kernel.get("signature"):
        errors.append("universal foundation adoption kernel signature is invalid")
    if kernel.get("summary", {}).get("status") != "ready":
        errors.append("universal foundation adoption kernel status is not ready")
    for check, passed in kernel.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal foundation adoption kernel check failed: {check}")
    if _contains_private_fields(kernel):
        errors.append("universal foundation adoption kernel exposes a private field")
    return errors
