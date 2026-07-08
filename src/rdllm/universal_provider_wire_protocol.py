"""Universal provider wire protocol.

The L151 layer makes L150 portable across real foundation-model transports. It
binds provider API requests, responses, streaming events, proxy transforms, SDK
metadata, batch callbacks, and export surfaces to the same claim provenance
envelope before a provider can claim universal RDLLM compatibility.
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
from rdllm.universal_composite_rdllm_profile import (
    REQUIRED_API_BINDING_PROVIDER_FAMILIES,
    REQUIRED_API_BINDINGS,
    REQUIRED_PROVIDER_FAMILIES,
)

UNIVERSAL_PROVIDER_WIRE_PROTOCOL_VERSION = (
    "rdllm-universal-provider-wire-protocol/v1"
)
UNIVERSAL_PROVIDER_WIRE_PROTOCOL_SCHEMA = (
    "docs/schemas/universal_provider_wire_protocol.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L151"
MINIMUM_CLAIM_PROVENANCE_LEVEL = "RDLLM-L150"
MINIMUM_RUNTIME_LEVEL = "RDLLM-L149"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-provider-wire-protocol.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "assurance_bundle",
    "proof_dependency_graph",
    "universal_claim_provenance_envelope",
    "universal_runtime_conformance_receipt",
    "universal_composite_rdllm_profile",
    "universal_emission_enforcement_gateway",
    "universal_rdllm_root",
    "foundation_api_profile",
    "foundation_runtime_adapter",
    "foundation_runtime_router",
    "composite_foundation_adapter",
    "foundation_provider_conformance",
    "foundation_model_deployment_attestation",
    "universal_invocation_guard",
    "universal_invocation_coverage",
    "universal_invocation_witness",
    "response_envelope",
    "proof_carrying_response",
    "serving_gateway_report",
    "source_footer_delivery",
    "client_attribution_enforcement",
    "agent_tool_attribution_ledger",
    "conversation_attribution_ledger",
    "revenue_allocation_report",
    "finance_ledger_attestation",
    "trust_registry",
)

REQUIRED_WIRE_SURFACES = (
    "request_headers",
    "response_headers",
    "json_body",
    "sse_stream",
    "tool_call_message",
    "batch_callback",
    "webhook",
    "sdk_metadata",
    "gateway_proxy",
    "export_copy",
)

REQUIRED_TRANSFORM_MODES = (
    "direct_provider_call",
    "trusted_proxy_passthrough",
    "aggregator_routing",
    "request_normalization",
    "response_normalization",
    "streaming_checkpoint",
    "output_rewrite_or_summarization",
    "batch_async_delivery",
    "client_export",
    "error_response",
)

REQUIRED_FAILURE_CASES = (
    "missing_rdllm_request_header",
    "missing_l150_envelope_hash",
    "stream_prefix_without_checkpoint",
    "proxy_rewrite_without_transform_receipt",
    "provider_family_mismatch",
    "unsupported_api_binding",
    "sdk_drops_footer_metadata",
    "batch_callback_missing_receipt",
    "error_response_missing_lineage",
    "stale_wire_version_policy",
    "unsigned_wire_attestation",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_provider_wire_protocol_hash",
    "universal_claim_provenance_envelope_hash",
    "universal_runtime_conformance_receipt_hash",
    "universal_composite_rdllm_profile_hash",
    "universal_emission_enforcement_gateway_hash",
    "universal_rdllm_root_hash",
    "foundation_model_deployment_attestation_hash",
    "foundation_runtime_router_hash",
    "foundation_runtime_adapter_hash",
    "foundation_provider_conformance_hash",
    "foundation_profile_hash",
    "composite_foundation_adapter_hash",
    "source_footer_delivery_hash",
    "client_enforcement_hash",
    "conversation_ledger_hash",
    "tool_ledger_hash",
    "trust_registry_hash",
    "attestation_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "graph_hash",
    "report_hash",
    "bundle_hash",
    "summary_hash",
    "contract_hash",
    "receipt_hash",
    "gateway_report_hash",
    "proof_response_hash",
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
    "claim_text",
    "source_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
    "tool_payload",
    "raw_tool_output",
    "raw_native_request",
    "raw_native_response",
    "authorization",
    "access_token",
    "api_key",
    "secret",
    "signing_secret",
    "private_key",
    "customer_id",
    "customer_email",
    "billing_record",
    "bank_account",
    "tax_id",
}


def load_universal_provider_wire_protocol_input(path: str | Path) -> dict[str, Any]:
    """Load private replay input for an L151 provider wire protocol."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_protocol(protocol: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in protocol.items()
        if key not in {"universal_provider_wire_protocol_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    hashable = {
        key: value
        for key, value in artifact.items()
        if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
    }
    metadata = hashable.get("response_metadata_contract")
    if isinstance(metadata, dict) and "foundation_profile_hash" in artifact:
        header_values = dict(metadata.get("header_values", {}))
        header_values["RDLLM-Foundation-Profile-Hash"] = "<foundation_profile_hash>"
        metadata = dict(metadata)
        metadata["header_values"] = header_values
        hashable["response_metadata_contract"] = metadata
    return hashable


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
    if artifact.get("receipt_hash") and isinstance(artifact.get("payload"), dict):
        return artifact["receipt_hash"] == hash_payload(artifact["payload"])
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
    public_payload: dict[str, Any], protocol_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in protocol_input.get("private_strings", [])
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
    protocol_input: dict[str, Any], key: str
) -> dict[str, dict[str, Any]]:
    value = protocol_input.get(key, {})
    if isinstance(value, dict):
        return {str(name): row for name, row in value.items() if isinstance(row, dict)}
    if isinstance(value, list):
        result: dict[str, dict[str, Any]] = {}
        for row in value:
            if not isinstance(row, dict):
                continue
            name = (
                row.get("api_binding")
                or row.get("surface")
                or row.get("transform_mode")
                or row.get("case_id")
            )
            if name:
                result[str(name)] = row
        return result
    return {}


def _policy(protocol_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(protocol_input.get("provider_wire_policy", {}))
    return {
        "profile": "rdllm-universal-provider-wire-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_claim_provenance_level": MINIMUM_CLAIM_PROVENANCE_LEVEL,
        "minimum_runtime_level": MINIMUM_RUNTIME_LEVEL,
        "well_known_path": DEFAULT_WELL_KNOWN_PATH,
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_provider_families": list(
            policy.get("required_provider_families", REQUIRED_PROVIDER_FAMILIES)
        ),
        "required_api_bindings": list(
            policy.get("required_api_bindings", REQUIRED_API_BINDINGS)
        ),
        "required_wire_surfaces": list(
            policy.get("required_wire_surfaces", REQUIRED_WIRE_SURFACES)
        ),
        "required_transform_modes": list(
            policy.get("required_transform_modes", REQUIRED_TRANSFORM_MODES)
        ),
        "required_failure_cases": list(
            policy.get("required_failure_cases", REQUIRED_FAILURE_CASES)
        ),
        "wire_rule": "every_provider_transport_must_carry_l150_and_l149_hashes",
        "stream_rule": "stream_prefixes_require_checkpoint_hashes_or_complete_lineage",
        "proxy_rule": "rewrites_and_aggregators_require_transform_receipts",
        "sdk_rule": "sdk_and_client_surfaces_must_preserve_footer_and_proof_metadata",
        "privacy_rule": "public_wire_protocol_contains_hashes_paths_and_capabilities_not_raw_payloads",
    }


def _artifact_bindings(protocol_input: dict[str, Any], names: list[str]) -> dict[str, Any]:
    rows = []
    for name in names:
        artifact = protocol_input.get(name)
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


def _provider_wire_rows(
    protocol_input: dict[str, Any], required_bindings: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(protocol_input, "provider_wire_rows")
    rows = []
    for api_binding in sorted(required_bindings):
        item = row_map.get(api_binding, {})
        expected_family = REQUIRED_API_BINDING_PROVIDER_FAMILIES.get(api_binding, "")
        row = {
            "api_binding": api_binding,
            "provider_family": str(item.get("provider_family", "")),
            "expected_provider_family": expected_family,
            "wire_profile_hash": str(item.get("wire_profile_hash", "")),
            "request_header_hash": str(item.get("request_header_hash", "")),
            "response_header_hash": str(item.get("response_header_hash", "")),
            "json_body_pointer_hash": str(item.get("json_body_pointer_hash", "")),
            "stream_event_hash": str(item.get("stream_event_hash", "")),
            "tool_call_mapping_hash": str(item.get("tool_call_mapping_hash", "")),
            "l150_envelope_hash": str(item.get("l150_envelope_hash", "")),
            "l149_receipt_hash": str(item.get("l149_receipt_hash", "")),
            "transform_receipt_hash": str(item.get("transform_receipt_hash", "")),
            "telemetry_span_hash": str(item.get("telemetry_span_hash", "")),
            "settlement_meter_hash": str(item.get("settlement_meter_hash", "")),
            "supports_streaming": item.get("supports_streaming") is True,
            "supports_tool_calls": item.get("supports_tool_calls") is True,
            "preserves_footer_metadata": item.get("preserves_footer_metadata") is True,
            "preserves_claim_provenance": item.get("preserves_claim_provenance") is True,
            "supports_error_lineage": item.get("supports_error_lineage") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            row["provider_family"] == expected_family
            and bool(row["wire_profile_hash"])
            and bool(row["request_header_hash"])
            and bool(row["response_header_hash"])
            and bool(row["json_body_pointer_hash"])
            and bool(row["stream_event_hash"])
            and bool(row["tool_call_mapping_hash"])
            and bool(row["l150_envelope_hash"])
            and bool(row["l149_receipt_hash"])
            and bool(row["transform_receipt_hash"])
            and bool(row["telemetry_span_hash"])
            and bool(row["settlement_meter_hash"])
            and row["supports_streaming"]
            and row["supports_tool_calls"]
            and row["preserves_footer_metadata"]
            and row["preserves_claim_provenance"]
            and row["supports_error_lineage"]
            and row["fail_closed"]
        )
        row["provider_wire_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _wire_surface_rows(
    protocol_input: dict[str, Any], required_surfaces: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(protocol_input, "wire_surface_rows")
    rows = []
    for surface in sorted(required_surfaces):
        item = row_map.get(surface, {})
        row = {
            "surface": surface,
            "carrier_path_hash": str(item.get("carrier_path_hash", "")),
            "l150_envelope_hash": str(item.get("l150_envelope_hash", "")),
            "l149_receipt_hash": str(item.get("l149_receipt_hash", "")),
            "footer_metadata_hash": str(item.get("footer_metadata_hash", "")),
            "proof_download_hash": str(item.get("proof_download_hash", "")),
            "stream_checkpoint_hash": str(item.get("stream_checkpoint_hash", "")),
            "client_render_test_hash": str(item.get("client_render_test_hash", "")),
            "required": item.get("required") is True,
            "preserved": item.get("preserved") is True,
            "downloadable": item.get("downloadable") is True,
            "blocks_on_missing_wire_proof": item.get("blocks_on_missing_wire_proof")
            is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
        }
        row["ready"] = (
            bool(row["carrier_path_hash"])
            and bool(row["l150_envelope_hash"])
            and bool(row["l149_receipt_hash"])
            and bool(row["footer_metadata_hash"])
            and bool(row["proof_download_hash"])
            and bool(row["stream_checkpoint_hash"])
            and bool(row["client_render_test_hash"])
            and row["required"]
            and row["preserved"]
            and row["downloadable"]
            and row["blocks_on_missing_wire_proof"]
            and row["privacy_preserving"]
        )
        row["wire_surface_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _transform_rows(
    protocol_input: dict[str, Any], required_modes: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(protocol_input, "transform_rows")
    rows = []
    for mode in sorted(required_modes):
        item = row_map.get(mode, {})
        row = {
            "transform_mode": mode,
            "request_projection_hash": str(item.get("request_projection_hash", "")),
            "source_output_hash": str(item.get("source_output_hash", "")),
            "transformed_output_hash": str(item.get("transformed_output_hash", "")),
            "transform_receipt_hash": str(item.get("transform_receipt_hash", "")),
            "lineage_receipt_hash": str(item.get("lineage_receipt_hash", "")),
            "claim_provenance_root": str(item.get("claim_provenance_root", "")),
            "issuer_key_hash": str(item.get("issuer_key_hash", "")),
            "request_bound": item.get("request_bound") is True,
            "output_bound": item.get("output_bound") is True,
            "streaming_safe": item.get("streaming_safe") is True,
            "footer_preserved": item.get("footer_preserved") is True,
            "settlement_preserved": item.get("settlement_preserved") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
        }
        row["ready"] = (
            bool(row["request_projection_hash"])
            and bool(row["source_output_hash"])
            and bool(row["transformed_output_hash"])
            and bool(row["transform_receipt_hash"])
            and bool(row["lineage_receipt_hash"])
            and bool(row["claim_provenance_root"])
            and bool(row["issuer_key_hash"])
            and row["request_bound"]
            and row["output_bound"]
            and row["streaming_safe"]
            and row["footer_preserved"]
            and row["settlement_preserved"]
            and row["privacy_preserving"]
        )
        row["transform_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _failure_case_rows(
    protocol_input: dict[str, Any], required_cases: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(protocol_input, "failure_case_rows")
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
            and row["verifier_command"] == "verify-universal-provider-wire-protocol"
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


def _artifact_summary(protocol_input: dict[str, Any], name: str) -> dict[str, Any]:
    artifact = protocol_input.get(name)
    return _summary(artifact if isinstance(artifact, dict) else None)


def make_universal_provider_wire_protocol(
    protocol_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create the L151 universal provider wire protocol."""

    policy = _policy(protocol_input)
    required_artifacts = list(policy["required_core_artifacts"])
    artifact_bindings = _artifact_bindings(protocol_input, required_artifacts)
    bindings = _binding_by_name(artifact_bindings)
    provider_rows = _provider_wire_rows(
        protocol_input, list(policy["required_api_bindings"])
    )
    surface_rows = _wire_surface_rows(
        protocol_input, list(policy["required_wire_surfaces"])
    )
    transform_rows = _transform_rows(
        protocol_input, list(policy["required_transform_modes"])
    )
    failure_rows = _failure_case_rows(
        protocol_input, list(policy["required_failure_cases"])
    )

    certification_summary = _artifact_summary(protocol_input, "certification_report")
    l150_summary = _artifact_summary(
        protocol_input, "universal_claim_provenance_envelope"
    )
    l149_summary = _artifact_summary(
        protocol_input, "universal_runtime_conformance_receipt"
    )
    profile_summary = _artifact_summary(
        protocol_input, "universal_composite_rdllm_profile"
    )
    adapter_summary = _artifact_summary(protocol_input, "foundation_runtime_adapter")
    router_summary = _artifact_summary(protocol_input, "foundation_runtime_router")
    deployment_summary = _artifact_summary(
        protocol_input, "foundation_model_deployment_attestation"
    )
    proof_graph_summary = _artifact_summary(protocol_input, "proof_dependency_graph")

    provider_card = protocol_input.get("provider_attribution_card", {})
    integration_profile = protocol_input.get("integration_profile", {})
    discovery_manifest = protocol_input.get("discovery_manifest", {})
    public_surfaces = {}
    if isinstance(provider_card, dict):
        public_surfaces.update(provider_card.get("public_disclosure_surfaces", {}))
    if isinstance(integration_profile, dict):
        public_surfaces.update(integration_profile.get("public_surfaces", {}))
    discovery = (
        discovery_manifest.get("discovery", {})
        if isinstance(discovery_manifest, dict)
        else {}
    )

    provider_coverage = {
        family: any(
            row.get("expected_provider_family") == family and row.get("ready") is True
            for row in provider_rows
        )
        for family in policy["required_provider_families"]
    }

    public_projection = {
        "artifact_bindings": artifact_bindings,
        "provider_wire_rows": provider_rows,
        "wire_surface_rows": surface_rows,
        "transform_rows": transform_rows,
        "failure_case_rows": failure_rows,
    }
    private_findings = _contains_private_fields(public_projection)

    checks = {
        "all_required_artifacts_present": all(
            bindings.get(name, {}).get("present") is True for name in required_artifacts
        ),
        "all_required_artifact_hashes_reproducible": all(
            bindings.get(name, {}).get("hash_reproducible") is True
            for name in required_artifacts
        ),
        "certification_passed_l150_or_higher": (
            certification_summary.get("status") == "passed"
            and _level_at_least(
                certification_summary.get("highest_level"),
                MINIMUM_CLAIM_PROVENANCE_LEVEL,
            )
        ),
        "claim_provenance_ready_l150": (
            l150_summary.get("status") == "ready"
            and _level_at_least(
                l150_summary.get("target_certification_level"),
                MINIMUM_CLAIM_PROVENANCE_LEVEL,
            )
            and int(l150_summary.get("failed_check_count", 0) or 0) == 0
        ),
        "runtime_conformance_ready_l149": (
            l149_summary.get("status") == "ready"
            and _level_at_least(
                l149_summary.get("target_certification_level"), MINIMUM_RUNTIME_LEVEL
            )
            and int(l149_summary.get("failed_check_count", 0) or 0) == 0
        ),
        "composite_profile_ready": (
            profile_summary.get("status") == "ready"
            and _level_at_least(
                profile_summary.get("target_certification_level"), "RDLLM-L148"
            )
        ),
        "runtime_adapter_router_ready": (
            adapter_summary.get("status") in {"ready", "released", "verified"}
            and router_summary.get("status") in {"ready", "released", "verified"}
            and deployment_summary.get("status")
            in {"ready", "released", "attested", "verified"}
        ),
        "all_provider_bindings_ready": _all_ready(provider_rows),
        "all_required_provider_families_covered": all(provider_coverage.values()),
        "all_wire_surfaces_ready": _all_ready(surface_rows),
        "all_transform_modes_ready": _all_ready(transform_rows),
        "all_failure_cases_prove_blocking": _all_ready(failure_rows),
        "wire_protocol_publication_declared": (
            public_surfaces.get("universal_provider_wire_protocol") is True
            or discovery.get("universal_provider_wire_protocol_path")
            == DEFAULT_WELL_KNOWN_PATH
        ),
        "proof_graph_acyclic": (
            int(proof_graph_summary.get("cycle_node_count", 0) or 0) == 0
            and proof_graph_summary.get("status") in {"ready", "ok"}
        ),
        "privacy_preserved": (
            not private_findings
            and _private_strings_absent(public_projection, protocol_input)
        ),
    }
    failed_checks = [name for name, passed in checks.items() if passed is not True]
    failure_modes_by_check = {
        "all_required_artifacts_present": "provider_wire_required_artifact_missing",
        "all_required_artifact_hashes_reproducible": "provider_wire_artifact_hash_not_reproducible",
        "certification_passed_l150_or_higher": "provider_wire_certification_below_l150",
        "claim_provenance_ready_l150": "provider_wire_l150_not_ready",
        "runtime_conformance_ready_l149": "provider_wire_l149_not_ready",
        "composite_profile_ready": "provider_wire_l148_profile_not_ready",
        "runtime_adapter_router_ready": "provider_wire_runtime_route_gap",
        "all_provider_bindings_ready": "provider_wire_binding_gap",
        "all_required_provider_families_covered": "provider_wire_provider_family_gap",
        "all_wire_surfaces_ready": "provider_wire_surface_gap",
        "all_transform_modes_ready": "provider_wire_transform_gap",
        "all_failure_cases_prove_blocking": "provider_wire_negative_case_gap",
        "wire_protocol_publication_declared": "provider_wire_publication_gap",
        "proof_graph_acyclic": "provider_wire_proof_graph_cycle",
        "privacy_preserved": "provider_wire_private_payload_leak",
    }
    failure_modes = [failure_modes_by_check[name] for name in failed_checks]
    ready = not failed_checks

    protocol = {
        "wire_protocol_version": UNIVERSAL_PROVIDER_WIRE_PROTOCOL_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "provider_wire_policy": policy,
        "artifact_bindings": artifact_bindings,
        "provider_wire_rows": provider_rows,
        "wire_surface_rows": surface_rows,
        "transform_rows": transform_rows,
        "failure_case_rows": failure_rows,
        "evidence_commitments": {
            "artifact_binding_root": artifact_bindings["artifact_binding_root"],
            "provider_wire_root": merkle_root(
                [row["provider_wire_row_hash"] for row in provider_rows]
            ),
            "wire_surface_root": merkle_root(
                [row["wire_surface_row_hash"] for row in surface_rows]
            ),
            "transform_root": merkle_root(
                [row["transform_row_hash"] for row in transform_rows]
            ),
            "failure_case_root": merkle_root(
                [row["failure_case_row_hash"] for row in failure_rows]
            ),
        },
        "checks": checks,
        "provider_family_coverage": provider_coverage,
        "wire_decision": {
            "universal_wire_protocol_authorized": ready,
            "provider_invocation_allowed": ready,
            "streaming_display_allowed": ready,
            "proxy_or_aggregator_routing_allowed": ready,
            "direct_creator_settlement_allowed": ready,
            "out_of_band_attribution_allowed": False,
            "failure_modes": failure_modes,
        },
        "verifier_commands": [
            "verify-universal-provider-wire-protocol",
            "verify-universal-claim-provenance-envelope",
            "verify-universal-runtime-conformance-receipt",
            "verify-universal-composite-rdllm-profile",
            "verify-foundation-runtime-adapter",
            "verify-foundation-runtime-router",
            "verify-source-footer-delivery",
            "verify-client-attribution-enforcement",
        ],
        "research_controls": {
            "api_boundary_attestation": "wire_attestation_binds_client_visible_request_to_response_or_stream_lineage",
            "multi_hop_transform_receipts": "proxies_aggregators_and_rewriters_must_publish_request_and_output_transform_receipts",
            "creator_data_access_protocol": "creator_owned_data_access_must_be_logged_licensed_and_attributable_by_default",
            "streaming_semantics": "stream_prefixes_and_rewrites_are_distinct_verification_modes",
            "research_urls": {
                "aex_llm_api_attestation": "https://arxiv.org/abs/2603.14283",
                "sovereign_context_protocol": "https://arxiv.org/abs/2603.27094",
                "opentelemetry_genai": "https://opentelemetry.io/docs/specs/semconv/gen-ai/",
                "openai_responses": "https://platform.openai.com/docs/api-reference/responses",
                "openai_responses_streaming": "https://platform.openai.com/docs/api-reference/responses-streaming/response",
                "anthropic_messages": "https://docs.anthropic.com/en/api/messages",
                "google_gemini_generate_content": "https://ai.google.dev/gemini-api/docs/text-generation",
                "amazon_bedrock_converse": "https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html",
                "openrouter_chat_completions": "https://openrouter.ai/docs/api-reference/chat-completion",
            },
        },
        "privacy": {
            "public_protocol_contains_raw_prompts": False,
            "public_protocol_contains_raw_outputs": False,
            "public_protocol_contains_raw_provider_payloads": False,
            "public_protocol_contains_tool_payloads": False,
            "hash_only_wire_commitments": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_claim_provenance_level": MINIMUM_CLAIM_PROVENANCE_LEVEL,
            "minimum_runtime_level": MINIMUM_RUNTIME_LEVEL,
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
            "core_artifact_count": artifact_bindings["artifact_count"],
            "provider_binding_count": len(provider_rows),
            "ready_provider_binding_count": _count(provider_rows),
            "provider_family_count": len(provider_coverage),
            "covered_provider_family_count": sum(
                1 for covered in provider_coverage.values() if covered
            ),
            "wire_surface_count": len(surface_rows),
            "ready_wire_surface_count": _count(surface_rows),
            "transform_mode_count": len(transform_rows),
            "ready_transform_mode_count": _count(transform_rows),
            "failure_case_count": len(failure_rows),
            "offline_verification_supported": True,
            "privacy_preserved": checks["privacy_preserved"],
        },
    }
    protocol["universal_provider_wire_protocol_hash"] = hash_payload(
        _hashable_protocol(protocol)
    )
    if signing_secret:
        protocol["signature"] = sign_payload(_hashable_protocol(protocol), signing_secret)
    return protocol


def validate_universal_provider_wire_protocol_shape(
    protocol: dict[str, Any],
) -> list[str]:
    """Validate the public L151 wire protocol shape."""

    errors: list[str] = []
    required = (
        "wire_protocol_version",
        "issuer",
        "created_at",
        "provider_wire_policy",
        "artifact_bindings",
        "provider_wire_rows",
        "wire_surface_rows",
        "transform_rows",
        "failure_case_rows",
        "evidence_commitments",
        "checks",
        "provider_family_coverage",
        "wire_decision",
        "verifier_commands",
        "research_controls",
        "privacy",
        "summary",
        "universal_provider_wire_protocol_hash",
    )
    for key in required:
        if key not in protocol:
            errors.append(f"missing universal provider wire protocol field: {key}")
    if errors:
        return errors
    if protocol.get("wire_protocol_version") != UNIVERSAL_PROVIDER_WIRE_PROTOCOL_VERSION:
        errors.append("universal provider wire protocol version is unsupported")
    if protocol.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal provider wire protocol target level is not RDLLM-L151")
    if protocol.get("provider_wire_policy", {}).get("well_known_path") != DEFAULT_WELL_KNOWN_PATH:
        errors.append("universal provider wire protocol well-known path is incorrect")
    return errors


def verify_universal_provider_wire_protocol(
    protocol: dict[str, Any],
    *,
    protocol_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L151 provider wire protocol against its replay input."""

    errors = validate_universal_provider_wire_protocol_shape(protocol)
    if errors:
        return errors

    private_paths = _contains_private_fields(protocol)
    if private_paths:
        errors.append(
            "universal provider wire protocol exposes private field(s): "
            + ", ".join(private_paths[:10])
        )
    if not _private_strings_absent(protocol, protocol_input):
        errors.append("universal provider wire protocol leaks private replay text")

    expected_hash = hash_payload(_hashable_protocol(protocol))
    if expected_hash != protocol.get("universal_provider_wire_protocol_hash"):
        errors.append("universal provider wire protocol hash is not reproducible")

    expected = make_universal_provider_wire_protocol(
        protocol_input,
        issuer=protocol.get("issuer", DEFAULT_ISSUER),
        created_at=protocol.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "provider_wire_policy",
        "artifact_bindings",
        "provider_wire_rows",
        "wire_surface_rows",
        "transform_rows",
        "failure_case_rows",
        "evidence_commitments",
        "checks",
        "provider_family_coverage",
        "wire_decision",
        "verifier_commands",
        "research_controls",
        "privacy",
        "summary",
    ):
        if expected.get(key) != protocol.get(key):
            errors.append(
                f"universal provider wire protocol {key} does not match replay input"
            )
    if (
        expected.get("universal_provider_wire_protocol_hash")
        != protocol.get("universal_provider_wire_protocol_hash")
    ):
        errors.append("universal provider wire protocol hash does not match replay input")
    if signing_secret:
        expected_signature = sign_payload(_hashable_protocol(protocol), signing_secret)
        if protocol.get("signature") != expected_signature:
            errors.append("universal provider wire protocol signature is invalid")
    return errors
