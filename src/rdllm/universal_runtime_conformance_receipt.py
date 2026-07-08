"""Universal runtime conformance receipt.

The L149 layer turns the L148 composite profile into a deployable runtime
contract. It proves that provider calls, response entrypoints, source-footer
grounding, client rendering, telemetry, and settlement metering are actually
enforced for the routes that emit model answers.
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

UNIVERSAL_RUNTIME_CONFORMANCE_RECEIPT_VERSION = (
    "rdllm-universal-runtime-conformance-receipt/v1"
)
UNIVERSAL_RUNTIME_CONFORMANCE_RECEIPT_SCHEMA = (
    "docs/schemas/universal_runtime_conformance_receipt.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L149"
MINIMUM_PROFILE_LEVEL = "RDLLM-L148"
MINIMUM_GATEWAY_LEVEL = "RDLLM-L147"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-runtime-conformance-receipt.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "certification_attestation",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "assurance_bundle",
    "proof_dependency_graph",
    "universal_composite_rdllm_profile",
    "universal_emission_enforcement_gateway",
    "universal_rdllm_root",
    "source_footer_delivery",
    "client_attribution_enforcement",
    "response_envelope",
    "proof_carrying_response",
    "serving_gateway_report",
    "grounded_source_footer",
    "rendered_attribution_audit",
    "claim_source_attribution_report",
    "evidence_region_binding_report",
    "deep_research_citation_audit",
    "citation_identity_report",
    "citation_reliance_receipt",
    "source_access_lease_report",
    "foundation_api_profile",
    "foundation_runtime_adapter",
    "foundation_runtime_router",
    "foundation_model_deployment_attestation",
    "universal_invocation_guard",
    "universal_invocation_coverage",
    "universal_invocation_witness",
    "revenue_allocation_report",
    "finance_ledger_attestation",
    "trust_registry",
)

REQUIRED_RUNTIME_ENTRYPOINTS = (
    "sync_generation",
    "streaming_generation",
    "tool_call",
    "agent_action",
    "retrieval_augmented_answer",
    "memory_influenced_answer",
    "batch_generation",
    "enterprise_proxy",
    "client_rendering",
)

REQUIRED_SOURCE_ATTRIBUTION_MODES = (
    "retrieved_text",
    "semantic_text_paraphrase",
    "citation_identity",
    "claim_source_replay",
    "evidence_region_binding",
    "deep_research_longform",
    "parametric_memory",
    "tool_observation",
    "conversation_memory",
    "training_or_post_training_signal",
    "residual_corpus_value",
)

REQUIRED_ENFORCEMENT_CONTROLS = (
    "preflight_l148_profile",
    "api_binding_route_match",
    "invocation_guard",
    "runtime_adapter_normalization",
    "evidence_lock_before_generation",
    "source_footer_injection",
    "claim_source_verification",
    "client_display_enforcement",
    "opentelemetry_genai_export",
    "settlement_meter",
    "proof_receipt_download",
    "challenge_route",
    "privacy_filter",
    "post_release_transparency",
)

REQUIRED_SDK_SURFACES = (
    "python",
    "typescript",
    "http_gateway",
    "openapi",
    "sidecar_proxy",
    "browser_client",
)

REQUIRED_FAILURE_CASES = (
    "missing_l148_profile",
    "api_provider_family_mismatch",
    "unguarded_provider_call",
    "missing_source_footer",
    "unsupported_claim_footer",
    "client_display_bypass",
    "missing_telemetry_span",
    "missing_settlement_meter",
    "stale_runtime_router",
    "proof_receipt_unavailable",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_runtime_conformance_receipt_hash",
    "universal_composite_rdllm_profile_hash",
    "universal_emission_enforcement_gateway_hash",
    "universal_rdllm_root_hash",
    "universal_attribution_authority_control_plane_hash",
    "universal_confidential_attribution_audit_hash",
    "universal_training_serving_contract_hash",
    "universal_grounded_reuse_contract_hash",
    "universal_citation_verification_contract_hash",
    "universal_context_provenance_bridge_hash",
    "universal_content_credential_hash",
    "universal_invocation_witness_hash",
    "universal_invocation_coverage_hash",
    "universal_invocation_guard_hash",
    "foundation_model_deployment_attestation_hash",
    "foundation_runtime_router_hash",
    "foundation_runtime_adapter_hash",
    "foundation_profile_hash",
    "client_enforcement_hash",
    "source_footer_delivery_hash",
    "grounded_source_footer_hash",
    "deep_research_citation_audit_hash",
    "citation_identity_hash",
    "claim_source_attribution_hash",
    "citation_reliance_hash",
    "source_access_lease_hash",
    "binding_report_hash",
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
    "statement_hash",
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
    "raw_query",
    "query_text",
    "output",
    "output_text",
    "answer_text",
    "raw_answer_text",
    "raw_model_output",
    "raw_native_response",
    "native_response_body",
    "raw_training_record",
    "training_text",
    "dataset_sample",
    "source_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
    "hidden_state",
    "activation",
    "gradient",
    "model_weight",
    "model_weights",
    "model_parameters",
    "serving_log",
    "customer_log",
    "billing_record",
    "customer_id",
    "customer_email",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "raw_gateway_payload",
    "raw_emission_payload",
    "raw_artifact",
    "private_settlement_record",
    "access_token",
    "refresh_token",
    "oauth_token",
    "api_key",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_runtime_conformance_receipt_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L149 runtime conformance receipt."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in receipt.items()
        if key not in {"universal_runtime_conformance_receipt_hash", "signature"}
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
    public_payload: dict[str, Any], receipt_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in receipt_input.get("private_strings", [])
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
    receipt_input: dict[str, Any], key: str
) -> dict[str, dict[str, Any]]:
    value = receipt_input.get(key, {})
    if isinstance(value, dict):
        return {str(name): row for name, row in value.items() if isinstance(row, dict)}
    if isinstance(value, list):
        result: dict[str, dict[str, Any]] = {}
        for row in value:
            if not isinstance(row, dict):
                continue
            name = (
                row.get("provider_family")
                or row.get("api_binding")
                or row.get("entrypoint")
                or row.get("mode")
                or row.get("control")
                or row.get("surface")
                or row.get("case_id")
            )
            if name:
                result[str(name)] = row
        return result
    return {}


def _policy(receipt_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(receipt_input.get("runtime_conformance_policy", {}))
    return {
        "profile": "rdllm-universal-runtime-conformance-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_profile_level": MINIMUM_PROFILE_LEVEL,
        "minimum_gateway_level": MINIMUM_GATEWAY_LEVEL,
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
        "required_runtime_entrypoints": list(
            policy.get("required_runtime_entrypoints", REQUIRED_RUNTIME_ENTRYPOINTS)
        ),
        "required_source_attribution_modes": list(
            policy.get(
                "required_source_attribution_modes",
                REQUIRED_SOURCE_ATTRIBUTION_MODES,
            )
        ),
        "required_enforcement_controls": list(
            policy.get(
                "required_enforcement_controls", REQUIRED_ENFORCEMENT_CONTROLS
            )
        ),
        "required_sdk_surfaces": list(
            policy.get("required_sdk_surfaces", REQUIRED_SDK_SURFACES)
        ),
        "required_failure_cases": list(
            policy.get("required_failure_cases", REQUIRED_FAILURE_CASES)
        ),
        "runtime_rule": "no_l149_receipt_no_universal_rdllm_runtime_claim",
        "provider_call_rule": "no_guarded_route_no_native_provider_call",
        "source_footer_rule": "no_verified_footer_no_answer_display",
        "citation_rule": "no_claim_support_no_verified_source_footer",
        "settlement_rule": "no_metered_guarded_attributed_invocation_no_creator_settlement",
        "privacy_rule": "public_receipt_contains_hashes_controls_and_counts_not_private_payloads",
    }


def _artifact_bindings(receipt_input: dict[str, Any], names: list[str]) -> dict[str, Any]:
    rows = []
    for name in names:
        artifact = receipt_input.get(name)
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


def _provider_runtime_rows(
    receipt_input: dict[str, Any], required_families: list[str]
) -> list[dict[str, Any]]:
    family_map = _component_input_map(receipt_input, "provider_runtime_rows")
    rows = []
    for family in sorted(required_families):
        item = family_map.get(family, {})
        row = {
            "provider_family": family,
            "l148_provider_row_hash": str(item.get("l148_provider_row_hash", "")),
            "l147_gateway_row_hash": str(item.get("l147_gateway_row_hash", "")),
            "runtime_adapter_hash": str(item.get("runtime_adapter_hash", "")),
            "invocation_guard_hash": str(item.get("invocation_guard_hash", "")),
            "source_footer_delivery_hash": str(
                item.get("source_footer_delivery_hash", "")
            ),
            "client_enforcement_hash": str(item.get("client_enforcement_hash", "")),
            "telemetry_span_template_hash": str(
                item.get("telemetry_span_template_hash", "")
            ),
            "settlement_meter_hash": str(item.get("settlement_meter_hash", "")),
            "public_verifier_command": str(item.get("public_verifier_command", "")),
            "entrypoints_guarded": item.get("entrypoints_guarded") is True,
            "source_footer_enforced": item.get("source_footer_enforced") is True,
            "settlement_metered": item.get("settlement_metered") is True,
            "telemetry_exported": item.get("telemetry_exported") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            bool(row["l148_provider_row_hash"])
            and bool(row["l147_gateway_row_hash"])
            and bool(row["runtime_adapter_hash"])
            and bool(row["invocation_guard_hash"])
            and bool(row["source_footer_delivery_hash"])
            and bool(row["client_enforcement_hash"])
            and bool(row["telemetry_span_template_hash"])
            and bool(row["settlement_meter_hash"])
            and row["public_verifier_command"]
            == "verify-universal-runtime-conformance-receipt"
            and row["entrypoints_guarded"]
            and row["source_footer_enforced"]
            and row["settlement_metered"]
            and row["telemetry_exported"]
            and row["fail_closed"]
        )
        row["provider_runtime_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _api_route_rows(
    receipt_input: dict[str, Any], required_bindings: list[str]
) -> list[dict[str, Any]]:
    route_map = _component_input_map(receipt_input, "api_route_rows")
    rows = []
    for binding in sorted(required_bindings):
        item = route_map.get(binding, {})
        row = {
            "api_binding": binding,
            "provider_family": str(item.get("provider_family", "")),
            "expected_provider_family": REQUIRED_API_BINDING_PROVIDER_FAMILIES.get(
                binding, ""
            ),
            "route_adapter_hash": str(item.get("route_adapter_hash", "")),
            "request_normalizer_hash": str(item.get("request_normalizer_hash", "")),
            "response_normalizer_hash": str(item.get("response_normalizer_hash", "")),
            "invocation_guard_hash": str(item.get("invocation_guard_hash", "")),
            "source_footer_injector_hash": str(
                item.get("source_footer_injector_hash", "")
            ),
            "telemetry_span_hash": str(item.get("telemetry_span_hash", "")),
            "settlement_meter_hash": str(item.get("settlement_meter_hash", "")),
            "covered": item.get("covered") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            bool(row["provider_family"])
            and row["provider_family"] == row["expected_provider_family"]
            and bool(row["route_adapter_hash"])
            and bool(row["request_normalizer_hash"])
            and bool(row["response_normalizer_hash"])
            and bool(row["invocation_guard_hash"])
            and bool(row["source_footer_injector_hash"])
            and bool(row["telemetry_span_hash"])
            and bool(row["settlement_meter_hash"])
            and row["covered"]
            and row["fail_closed"]
        )
        row["api_route_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _runtime_entrypoint_rows(
    receipt_input: dict[str, Any], required_entrypoints: list[str]
) -> list[dict[str, Any]]:
    entrypoint_map = _component_input_map(receipt_input, "runtime_entrypoint_rows")
    rows = []
    for entrypoint in sorted(required_entrypoints):
        item = entrypoint_map.get(entrypoint, {})
        row = {
            "entrypoint": entrypoint,
            "entrypoint_hash": str(item.get("entrypoint_hash", "")),
            "api_binding": str(item.get("api_binding", "")),
            "provider_family": str(item.get("provider_family", "")),
            "route_hash": str(item.get("route_hash", "")),
            "guard_hash": str(item.get("guard_hash", "")),
            "invocation_witness_hash": str(item.get("invocation_witness_hash", "")),
            "source_footer_delivery_hash": str(
                item.get("source_footer_delivery_hash", "")
            ),
            "client_surface_hash": str(item.get("client_surface_hash", "")),
            "telemetry_span_hash": str(item.get("telemetry_span_hash", "")),
            "settlement_meter_hash": str(item.get("settlement_meter_hash", "")),
            "covered": item.get("covered") is True,
            "source_footer_required": item.get("source_footer_required") is True,
            "claim_source_verification_required": item.get(
                "claim_source_verification_required"
            )
            is True,
            "metering_required": item.get("metering_required") is True,
            "telemetry_required": item.get("telemetry_required") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            bool(row["entrypoint_hash"])
            and bool(row["api_binding"])
            and bool(row["provider_family"])
            and bool(row["route_hash"])
            and bool(row["guard_hash"])
            and bool(row["invocation_witness_hash"])
            and bool(row["source_footer_delivery_hash"])
            and bool(row["client_surface_hash"])
            and bool(row["telemetry_span_hash"])
            and bool(row["settlement_meter_hash"])
            and row["covered"]
            and row["source_footer_required"]
            and row["claim_source_verification_required"]
            and row["metering_required"]
            and row["telemetry_required"]
            and row["fail_closed"]
        )
        row["runtime_entrypoint_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _source_attribution_rows(
    receipt_input: dict[str, Any], required_modes: list[str]
) -> list[dict[str, Any]]:
    mode_map = _component_input_map(receipt_input, "source_attribution_rows")
    rows = []
    for mode in sorted(required_modes):
        item = mode_map.get(mode, {})
        row = {
            "mode": mode,
            "source_proof_artifact": str(item.get("source_proof_artifact", "")),
            "source_proof_hash": str(item.get("source_proof_hash", "")),
            "claim_binding_hash": str(item.get("claim_binding_hash", "")),
            "footer_surface_hash": str(item.get("footer_surface_hash", "")),
            "evidence_region_hash": str(item.get("evidence_region_hash", "")),
            "citation_identity_hash": str(item.get("citation_identity_hash", "")),
            "payout_basis_hash": str(item.get("payout_basis_hash", "")),
            "supports_text": item.get("supports_text") is True,
            "public_footer_required": item.get("public_footer_required") is True,
            "unsupported_claims_blocked": item.get("unsupported_claims_blocked") is True,
            "direct_settlement_or_escrow": item.get("direct_settlement_or_escrow")
            is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
        }
        row["ready"] = (
            bool(row["source_proof_artifact"])
            and bool(row["source_proof_hash"])
            and bool(row["claim_binding_hash"])
            and bool(row["footer_surface_hash"])
            and bool(row["evidence_region_hash"])
            and bool(row["citation_identity_hash"])
            and bool(row["payout_basis_hash"])
            and row["supports_text"]
            and row["public_footer_required"]
            and row["unsupported_claims_blocked"]
            and row["direct_settlement_or_escrow"]
            and row["privacy_preserving"]
        )
        row["source_attribution_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _enforcement_control_rows(
    receipt_input: dict[str, Any], required_controls: list[str]
) -> list[dict[str, Any]]:
    control_map = _component_input_map(receipt_input, "enforcement_control_rows")
    rows = []
    for control in sorted(required_controls):
        item = control_map.get(control, {})
        row = {
            "control": control,
            "control_hash": str(item.get("control_hash", "")),
            "artifact_hash": str(item.get("artifact_hash", "")),
            "telemetry_attribute_hash": str(item.get("telemetry_attribute_hash", "")),
            "verifier_command": str(item.get("verifier_command", "")),
            "observed": item.get("observed") is True,
            "blocks_on_failure": item.get("blocks_on_failure") is True,
            "publicly_verifiable": item.get("publicly_verifiable") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
        }
        row["ready"] = (
            bool(row["control_hash"])
            and bool(row["artifact_hash"])
            and bool(row["telemetry_attribute_hash"])
            and row["verifier_command"]
            == "verify-universal-runtime-conformance-receipt"
            and row["observed"]
            and row["blocks_on_failure"]
            and row["publicly_verifiable"]
            and row["privacy_preserving"]
        )
        row["enforcement_control_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _sdk_surface_rows(
    receipt_input: dict[str, Any], required_surfaces: list[str]
) -> list[dict[str, Any]]:
    surface_map = _component_input_map(receipt_input, "sdk_surface_rows")
    rows = []
    for surface in sorted(required_surfaces):
        item = surface_map.get(surface, {})
        row = {
            "surface": surface,
            "sdk_contract_hash": str(item.get("sdk_contract_hash", "")),
            "conformance_fixture_hash": str(item.get("conformance_fixture_hash", "")),
            "source_footer_render_test_hash": str(
                item.get("source_footer_render_test_hash", "")
            ),
            "receipt_download_test_hash": str(
                item.get("receipt_download_test_hash", "")
            ),
            "telemetry_test_hash": str(item.get("telemetry_test_hash", "")),
            "covered": item.get("covered") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            bool(row["sdk_contract_hash"])
            and bool(row["conformance_fixture_hash"])
            and bool(row["source_footer_render_test_hash"])
            and bool(row["receipt_download_test_hash"])
            and bool(row["telemetry_test_hash"])
            and row["covered"]
            and row["fail_closed"]
        )
        row["sdk_surface_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _failure_case_rows(
    receipt_input: dict[str, Any], required_cases: list[str]
) -> list[dict[str, Any]]:
    case_map = _component_input_map(receipt_input, "failure_case_rows")
    rows = []
    for case_id in sorted(required_cases):
        item = case_map.get(case_id, {})
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
            == "verify-universal-runtime-conformance-receipt"
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


def _artifact_summary(receipt_input: dict[str, Any], name: str) -> dict[str, Any]:
    artifact = receipt_input.get(name)
    return _summary(artifact if isinstance(artifact, dict) else None)


def make_universal_runtime_conformance_receipt(
    receipt_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create the L149 universal runtime conformance receipt."""

    policy = _policy(receipt_input)
    required_artifacts = list(policy["required_core_artifacts"])
    artifact_bindings = _artifact_bindings(receipt_input, required_artifacts)
    bindings = _binding_by_name(artifact_bindings)
    provider_rows = _provider_runtime_rows(
        receipt_input, list(policy["required_provider_families"])
    )
    api_rows = _api_route_rows(receipt_input, list(policy["required_api_bindings"]))
    entrypoint_rows = _runtime_entrypoint_rows(
        receipt_input, list(policy["required_runtime_entrypoints"])
    )
    source_rows = _source_attribution_rows(
        receipt_input, list(policy["required_source_attribution_modes"])
    )
    control_rows = _enforcement_control_rows(
        receipt_input, list(policy["required_enforcement_controls"])
    )
    sdk_rows = _sdk_surface_rows(receipt_input, list(policy["required_sdk_surfaces"]))
    failure_rows = _failure_case_rows(
        receipt_input, list(policy["required_failure_cases"])
    )

    certification_summary = _artifact_summary(receipt_input, "certification_report")
    profile_summary = _artifact_summary(
        receipt_input, "universal_composite_rdllm_profile"
    )
    gateway_summary = _artifact_summary(
        receipt_input, "universal_emission_enforcement_gateway"
    )
    root_summary = _artifact_summary(receipt_input, "universal_rdllm_root")
    footer_summary = _artifact_summary(receipt_input, "source_footer_delivery")
    client_summary = _artifact_summary(receipt_input, "client_attribution_enforcement")
    response_summary = _artifact_summary(receipt_input, "response_envelope")
    proof_summary = _artifact_summary(receipt_input, "proof_carrying_response")
    serving_summary = _artifact_summary(receipt_input, "serving_gateway_report")
    coverage_summary = _artifact_summary(receipt_input, "universal_invocation_coverage")
    witness_summary = _artifact_summary(receipt_input, "universal_invocation_witness")
    router_summary = _artifact_summary(receipt_input, "foundation_runtime_router")
    adapter_summary = _artifact_summary(receipt_input, "foundation_runtime_adapter")
    deployment_summary = _artifact_summary(
        receipt_input, "foundation_model_deployment_attestation"
    )
    deep_research_summary = _artifact_summary(
        receipt_input, "deep_research_citation_audit"
    )
    citation_identity_summary = _artifact_summary(receipt_input, "citation_identity_report")
    claim_source_summary = _artifact_summary(
        receipt_input, "claim_source_attribution_report"
    )
    proof_graph_summary = _artifact_summary(receipt_input, "proof_dependency_graph")

    provider_card = receipt_input.get("provider_attribution_card", {})
    integration_profile = receipt_input.get("integration_profile", {})
    discovery_manifest = receipt_input.get("discovery_manifest", {})
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

    public_projection = {
        "artifact_bindings": artifact_bindings,
        "provider_runtime_rows": provider_rows,
        "api_route_rows": api_rows,
        "runtime_entrypoint_rows": entrypoint_rows,
        "source_attribution_rows": source_rows,
        "enforcement_control_rows": control_rows,
        "sdk_surface_rows": sdk_rows,
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
        "certification_passed_l148_or_higher": (
            certification_summary.get("status") == "passed"
            and _level_at_least(
                certification_summary.get("highest_level"), MINIMUM_PROFILE_LEVEL
            )
        ),
        "composite_profile_ready_l148": (
            profile_summary.get("status") == "ready"
            and _level_at_least(
                profile_summary.get("target_certification_level"),
                MINIMUM_PROFILE_LEVEL,
            )
            and int(profile_summary.get("failed_check_count", 0) or 0) == 0
        ),
        "emission_gateway_ready_l147": (
            gateway_summary.get("status") == "ready"
            and _level_at_least(
                gateway_summary.get("target_certification_level"),
                MINIMUM_GATEWAY_LEVEL,
            )
            and int(gateway_summary.get("failed_check_count", 0) or 0) == 0
        ),
        "root_ready_l146": (
            root_summary.get("status") == "ready"
            and _level_at_least(
                root_summary.get("target_certification_level"), "RDLLM-L146"
            )
            and int(root_summary.get("failed_check_count", 0) or 0) == 0
        ),
        "provider_family_coverage_matches_l148": (
            _all_ready(provider_rows)
            and int(profile_summary.get("provider_family_count", len(provider_rows)) or 0)
            <= len(provider_rows)
        ),
        "api_binding_coverage_matches_l148": (
            _all_ready(api_rows)
            and int(profile_summary.get("api_binding_count", len(api_rows)) or 0)
            <= len(api_rows)
        ),
        "all_runtime_entrypoints_ready": _all_ready(entrypoint_rows),
        "all_source_attribution_modes_ready": _all_ready(source_rows),
        "all_enforcement_controls_ready": _all_ready(control_rows),
        "all_sdk_surfaces_ready": _all_ready(sdk_rows),
        "all_failure_cases_prove_blocking": _all_ready(failure_rows),
        "source_footer_delivery_runtime_ready": (
            footer_summary.get("status") == "ready"
            and int(footer_summary.get("failed_check_count", 0) or 0) == 0
            and (
                footer_summary.get("grounded_footer_delivery_enforced") is True
                or int(footer_summary.get("delivered_source_count", 1) or 0) > 0
            )
        ),
        "client_display_enforcement_ready": (
            client_summary.get("status") == "ready"
            and int(client_summary.get("failed_check_count", 0) or 0) == 0
            and (
                client_summary.get("client_enforcement_ready") is True
                or int(client_summary.get("source_label_count", 1) or 0) > 0
            )
        ),
        "answer_source_proof_stack_ready": (
            response_summary.get("status") in {"ready", "verified"}
            and proof_summary.get("status") in {"ready", "released"}
            and serving_summary.get("status") in {"ready", "served"}
            and deep_research_summary.get("status") in {"ready", "passed", "verified"}
            and citation_identity_summary.get("status") in {"ready", "verified"}
            and claim_source_summary.get("status") in {"ready", "verified"}
        ),
        "invocation_nonrepudiation_ready": (
            coverage_summary.get("status") == "ready"
            and witness_summary.get("status") == "ready"
            and (
                coverage_summary.get("coverage_complete") is True
                or int(coverage_summary.get("uncovered_call_count", 0) or 0) == 0
            )
            and (
                witness_summary.get("nonrepudiation_complete") is True
                or int(witness_summary.get("missing_witness_count", 0) or 0) == 0
            )
        ),
        "foundation_runtime_route_ready": (
            router_summary.get("status") in {"ready", "released"}
            and adapter_summary.get("status") in {"ready", "released"}
            and deployment_summary.get("status") in {"ready", "released"}
            and int(router_summary.get("failed_check_count", 0) or 0) == 0
            and int(adapter_summary.get("failed_check_count", 0) or 0) == 0
        ),
        "runtime_receipt_publication_declared": (
            public_surfaces.get("universal_runtime_conformance_receipt") is True
            or discovery.get("universal_runtime_conformance_receipt_path")
            == DEFAULT_WELL_KNOWN_PATH
        ),
        "proof_graph_acyclic": (
            int(proof_graph_summary.get("cycle_node_count", 0) or 0) == 0
            and proof_graph_summary.get("status") in {"ready", "ok"}
        ),
        "privacy_preserved": (
            not private_findings
            and _private_strings_absent(public_projection, receipt_input)
        ),
    }

    failed_checks = [name for name, passed in checks.items() if passed is not True]
    failure_modes_by_check = {
        "all_required_artifacts_present": "runtime_required_artifact_missing",
        "all_required_artifact_hashes_reproducible": "runtime_artifact_hash_not_reproducible",
        "certification_passed_l148_or_higher": "runtime_certification_below_l148",
        "composite_profile_ready_l148": "runtime_l148_profile_not_ready",
        "emission_gateway_ready_l147": "runtime_l147_gateway_not_ready",
        "root_ready_l146": "runtime_l146_root_not_ready",
        "provider_family_coverage_matches_l148": "runtime_provider_family_gap",
        "api_binding_coverage_matches_l148": "runtime_api_route_gap",
        "all_runtime_entrypoints_ready": "runtime_entrypoint_gap",
        "all_source_attribution_modes_ready": "runtime_source_attribution_gap",
        "all_enforcement_controls_ready": "runtime_enforcement_control_gap",
        "all_sdk_surfaces_ready": "runtime_sdk_surface_gap",
        "all_failure_cases_prove_blocking": "runtime_negative_case_gap",
        "source_footer_delivery_runtime_ready": "runtime_source_footer_delivery_gap",
        "client_display_enforcement_ready": "runtime_client_enforcement_gap",
        "answer_source_proof_stack_ready": "runtime_answer_source_proof_gap",
        "invocation_nonrepudiation_ready": "runtime_invocation_nonrepudiation_gap",
        "foundation_runtime_route_ready": "runtime_foundation_route_gap",
        "runtime_receipt_publication_declared": "runtime_receipt_publication_gap",
        "proof_graph_acyclic": "runtime_proof_graph_cycle",
        "privacy_preserved": "runtime_private_payload_leak",
    }
    failure_modes = [failure_modes_by_check[name] for name in failed_checks]
    ready = not failed_checks

    receipt = {
        "receipt_version": UNIVERSAL_RUNTIME_CONFORMANCE_RECEIPT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "runtime_conformance_policy": policy,
        "artifact_bindings": artifact_bindings,
        "provider_runtime_rows": provider_rows,
        "api_route_rows": api_rows,
        "runtime_entrypoint_rows": entrypoint_rows,
        "source_attribution_rows": source_rows,
        "enforcement_control_rows": control_rows,
        "sdk_surface_rows": sdk_rows,
        "failure_case_rows": failure_rows,
        "evidence_commitments": {
            "artifact_binding_root": artifact_bindings["artifact_binding_root"],
            "provider_runtime_root": merkle_root(
                [row["provider_runtime_row_hash"] for row in provider_rows]
            ),
            "api_route_root": merkle_root(
                [row["api_route_row_hash"] for row in api_rows]
            ),
            "runtime_entrypoint_root": merkle_root(
                [row["runtime_entrypoint_row_hash"] for row in entrypoint_rows]
            ),
            "source_attribution_root": merkle_root(
                [row["source_attribution_row_hash"] for row in source_rows]
            ),
            "enforcement_control_root": merkle_root(
                [row["enforcement_control_row_hash"] for row in control_rows]
            ),
            "sdk_surface_root": merkle_root(
                [row["sdk_surface_row_hash"] for row in sdk_rows]
            ),
            "failure_case_root": merkle_root(
                [row["failure_case_row_hash"] for row in failure_rows]
            ),
        },
        "checks": checks,
        "runtime_decision": {
            "runtime_conformance_authorized": ready,
            "provider_invocation_allowed": ready,
            "response_display_allowed": ready,
            "verified_source_footer_allowed": ready,
            "creator_settlement_allowed": ready,
            "failure_modes": failure_modes,
        },
        "verifier_commands": [
            "verify-universal-runtime-conformance-receipt",
            "verify-universal-composite-rdllm-profile",
            "verify-universal-emission-enforcement-gateway",
            "verify-source-footer-delivery",
            "verify-client-attribution-enforcement",
            "verify-deep-research-citation-audit",
            "verify-citation-identity-report",
            "verify-claim-source-attribution-report",
            "verify-universal-invocation-coverage",
            "verify-universal-invocation-witness",
            "verify-proof-dependency-graph",
        ],
        "research_controls": {
            "pinpoint_training_data_attribution": "rank_candidate_documents_that_support_the_response_not_just_lexical_matches",
            "claim_evidence_interface": "decompose_answers_and_sources_into_claims_evidence_and_omissions_before_display",
            "evidence_utility": "perturb_retrieved_evidence_to_measure_per_item_operational_utility",
            "citation_hallucination_guard": "verify_citation_identity_url_health_and_claim_support_before_footer_publication",
            "provider_neutral_runtime_ir": "normalize_cross_provider_messages_content_parts_tool_calls_reasoning_traces_and_stream_events",
            "genai_observability": "export_provider_model_token_tool_and_response_spans_using_standard_genai_semantics",
            "content_provenance_interop": "map_hash_only_output_receipts_to_c2pa_style_content_credentials_without_exposing_private_text",
            "context_protocol_interop": "bind_mcp_style_resources_tools_and_prompts_to_source_authority_and_consent_controls",
            "research_urls": {
                "datadignity_training_data_attribution": "https://arxiv.org/abs/2605.05687",
                "papertrail_claim_evidence_interface": "https://arxiv.org/abs/2602.21045",
                "cue_r_evidence_utility": "https://arxiv.org/abs/2604.05467",
                "source_attribution_in_rag": "https://arxiv.org/abs/2507.04480",
                "llm_hallucinated_citations_in_the_wild": "https://arxiv.org/abs/2605.07723",
                "mechanistic_data_attribution": "https://arxiv.org/abs/2601.21996",
                "low_rank_influence_functions": "https://arxiv.org/abs/2601.21929",
                "llm_rosetta_cross_provider_ir": "https://arxiv.org/abs/2604.09360",
                "opentelemetry_genai": "https://opentelemetry.io/docs/specs/semconv/gen-ai/",
                "model_context_protocol": "https://modelcontextprotocol.io/specification/2025-06-18/basic/index",
                "c2pa_content_credentials": "https://c2pa.wiki/specifications/",
                "openai_responses": "https://platform.openai.com/docs/api-reference/responses",
                "amazon_bedrock_converse_batch": "https://aws.amazon.com/about-aws/whats-new/2026/02/amazon-bedrock-batch-inference-supports-converse-api-format/",
                "azure_openai_responses": "https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/responses",
                "openrouter_chat_completions": "https://openrouter.ai/docs/api-reference/chat-completion",
            },
        },
        "privacy": {
            "public_receipt_contains_private_prompts": False,
            "public_receipt_contains_private_outputs": False,
            "public_receipt_contains_source_text": False,
            "public_receipt_contains_customer_identifiers": False,
            "hash_only_artifact_commitments": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_profile_level": MINIMUM_PROFILE_LEVEL,
            "minimum_gateway_level": MINIMUM_GATEWAY_LEVEL,
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
            "core_artifact_count": artifact_bindings["artifact_count"],
            "provider_family_count": len(provider_rows),
            "covered_provider_family_count": _count(provider_rows),
            "api_binding_count": len(api_rows),
            "covered_api_binding_count": _count(api_rows),
            "runtime_entrypoint_count": len(entrypoint_rows),
            "covered_runtime_entrypoint_count": _count(entrypoint_rows),
            "source_attribution_mode_count": len(source_rows),
            "covered_source_attribution_mode_count": _count(source_rows),
            "enforcement_control_count": len(control_rows),
            "covered_enforcement_control_count": _count(control_rows),
            "sdk_surface_count": len(sdk_rows),
            "covered_sdk_surface_count": _count(sdk_rows),
            "failure_case_count": len(failure_rows),
            "offline_verification_supported": True,
            "privacy_preserved": checks["privacy_preserved"],
        },
    }
    receipt["universal_runtime_conformance_receipt_hash"] = hash_payload(
        _hashable_receipt(receipt)
    )
    if signing_secret:
        receipt["signature"] = sign_payload(
            _hashable_receipt(receipt), signing_secret
        )
    return receipt


def validate_universal_runtime_conformance_receipt_shape(
    receipt: dict[str, Any],
) -> list[str]:
    """Validate the public L149 receipt shape."""

    errors: list[str] = []
    required = (
        "receipt_version",
        "issuer",
        "created_at",
        "runtime_conformance_policy",
        "artifact_bindings",
        "provider_runtime_rows",
        "api_route_rows",
        "runtime_entrypoint_rows",
        "source_attribution_rows",
        "enforcement_control_rows",
        "sdk_surface_rows",
        "failure_case_rows",
        "evidence_commitments",
        "checks",
        "runtime_decision",
        "verifier_commands",
        "research_controls",
        "privacy",
        "summary",
        "universal_runtime_conformance_receipt_hash",
    )
    for key in required:
        if key not in receipt:
            errors.append(f"missing universal runtime conformance receipt field: {key}")
    if errors:
        return errors
    if receipt.get("receipt_version") != UNIVERSAL_RUNTIME_CONFORMANCE_RECEIPT_VERSION:
        errors.append("universal runtime conformance receipt version is unsupported")
    if receipt.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal runtime conformance receipt target level is not RDLLM-L149")
    if receipt.get("runtime_conformance_policy", {}).get("well_known_path") != DEFAULT_WELL_KNOWN_PATH:
        errors.append("universal runtime conformance receipt well-known path is incorrect")
    return errors


def verify_universal_runtime_conformance_receipt(
    receipt: dict[str, Any],
    *,
    receipt_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L149 runtime conformance receipt against its replay input."""

    errors = validate_universal_runtime_conformance_receipt_shape(receipt)
    if errors:
        return errors

    private_paths = _contains_private_fields(receipt)
    if private_paths:
        errors.append(
            "universal runtime conformance receipt exposes private field(s): "
            + ", ".join(private_paths[:10])
        )
    if not _private_strings_absent(receipt, receipt_input):
        errors.append("universal runtime conformance receipt leaks private replay text")

    expected_hash = hash_payload(_hashable_receipt(receipt))
    if expected_hash != receipt.get("universal_runtime_conformance_receipt_hash"):
        errors.append("universal runtime conformance receipt hash is not reproducible")

    expected = make_universal_runtime_conformance_receipt(
        receipt_input,
        issuer=receipt.get("issuer", DEFAULT_ISSUER),
        created_at=receipt.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "runtime_conformance_policy",
        "artifact_bindings",
        "provider_runtime_rows",
        "api_route_rows",
        "runtime_entrypoint_rows",
        "source_attribution_rows",
        "enforcement_control_rows",
        "sdk_surface_rows",
        "failure_case_rows",
        "evidence_commitments",
        "checks",
        "runtime_decision",
        "verifier_commands",
        "research_controls",
        "privacy",
        "summary",
    ):
        if expected.get(key) != receipt.get(key):
            errors.append(
                f"universal runtime conformance receipt {key} does not match replay input"
            )
    if (
        expected.get("universal_runtime_conformance_receipt_hash")
        != receipt.get("universal_runtime_conformance_receipt_hash")
    ):
        errors.append(
            "universal runtime conformance receipt hash does not match replay input"
        )
    if signing_secret:
        expected_signature = sign_payload(_hashable_receipt(receipt), signing_secret)
        if receipt.get("signature") != expected_signature:
            errors.append("universal runtime conformance receipt signature is invalid")
    return errors
