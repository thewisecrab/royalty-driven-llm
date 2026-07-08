"""Universal composite RDLLM profile.

The L148 layer is the provider-neutral deployment contract. It binds the
passport, adoption standard, interop kit, L146 root, L147 emission gateway,
runtime adapters, public discovery, assurance, proof graph, client display,
source footer, and settlement/audit obligations into one composite profile.
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

UNIVERSAL_COMPOSITE_RDLLM_PROFILE_VERSION = (
    "rdllm-universal-composite-rdllm-profile/v1"
)
UNIVERSAL_COMPOSITE_RDLLM_PROFILE_SCHEMA = (
    "docs/schemas/universal_composite_rdllm_profile.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L148"
MINIMUM_GATEWAY_LEVEL = "RDLLM-L147"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-composite-rdllm-profile.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "certification_attestation",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "assurance_bundle",
    "proof_dependency_graph",
    "universal_rdllm_passport",
    "universal_adoption_standard",
    "universal_interop_test_kit",
    "universal_rdllm_root",
    "universal_emission_enforcement_gateway",
    "source_footer_delivery",
    "client_attribution_enforcement",
    "foundation_api_profile",
    "foundation_runtime_adapter",
    "foundation_runtime_router",
    "foundation_model_deployment_attestation",
    "universal_invocation_guard",
    "universal_invocation_coverage",
    "universal_invocation_witness",
    "trust_registry",
)

REQUIRED_PROVIDER_FAMILIES = (
    "openai",
    "anthropic",
    "google",
    "meta",
    "mistral",
    "cohere",
    "xai",
    "deepseek",
    "amazon_bedrock",
    "azure_openai",
    "openrouter_aggregator",
    "local_open_weights",
    "enterprise_gateway",
)

REQUIRED_API_BINDINGS = (
    "openai_responses",
    "openai_chat_completions",
    "anthropic_messages",
    "google_generate_content",
    "meta_llama_stack",
    "mistral_chat",
    "cohere_chat",
    "xai_chat",
    "deepseek_chat",
    "amazon_bedrock_converse",
    "azure_openai_responses",
    "openrouter_chat_completions",
    "local_openai_compatible",
    "enterprise_proxy",
)

REQUIRED_API_BINDING_PROVIDER_FAMILIES = {
    "openai_responses": "openai",
    "openai_chat_completions": "openai",
    "anthropic_messages": "anthropic",
    "google_generate_content": "google",
    "meta_llama_stack": "meta",
    "mistral_chat": "mistral",
    "cohere_chat": "cohere",
    "xai_chat": "xai",
    "deepseek_chat": "deepseek",
    "amazon_bedrock_converse": "amazon_bedrock",
    "azure_openai_responses": "azure_openai",
    "openrouter_chat_completions": "openrouter_aggregator",
    "local_openai_compatible": "local_open_weights",
    "enterprise_proxy": "enterprise_gateway",
}

REQUIRED_COMPOSITE_PLANES = (
    "identity_and_registry",
    "rights_and_license",
    "training_and_memory",
    "retrieval_and_grounding",
    "context_and_reasoning_boundary",
    "generation_and_emission",
    "tool_and_agent_actions",
    "source_footer_and_client_display",
    "settlement_and_metering",
    "audit_dispute_and_remediation",
    "telemetry_and_observability",
    "interop_sdk_and_procurement",
)

REQUIRED_CUSTOMER_SURFACES = (
    "visible_source_footer",
    "proof_receipt_download",
    "attribution_breakdown",
    "creator_pool_statement",
    "challenge_link",
    "verifier_bundle",
    "privacy_notice",
)

REQUIRED_STANDARD_MAPPINGS = (
    "opentelemetry_genai",
    "c2pa_content_credentials",
    "w3c_verifiable_credentials_data_integrity",
    "ietf_scitt_transparency",
    "warrant_certificate_authority",
    "model_context_protocol",
    "iso20022_payment_status",
    "robots_tdm_rsl_rights_signals",
)

REQUIRED_FAILURE_CASES = (
    "missing_l147_gateway",
    "missing_l146_root",
    "provider_family_uncovered",
    "api_binding_uncovered",
    "composite_plane_uncovered",
    "source_footer_surface_missing",
    "settlement_surface_missing",
    "telemetry_mapping_missing",
    "weak_interop_kit",
    "stale_certification",
    "proof_graph_cycle",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_composite_rdllm_profile_hash",
    "universal_emission_enforcement_gateway_hash",
    "universal_rdllm_root_hash",
    "universal_rdllm_passport_hash",
    "universal_adoption_standard_hash",
    "universal_interop_test_kit_hash",
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


def load_universal_composite_rdllm_profile_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L148 composite RDLLM profile."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in profile.items()
        if key not in {"universal_composite_rdllm_profile_hash", "signature"}
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
    report_or_projection: dict[str, Any], profile_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(report_or_projection)
    private_strings = [
        str(item)
        for item in profile_input.get("private_strings", [])
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
    profile_input: dict[str, Any], key: str
) -> dict[str, dict[str, Any]]:
    value = profile_input.get(key, {})
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
                or row.get("plane")
                or row.get("surface")
                or row.get("standard")
                or row.get("case_id")
            )
            if name:
                result[str(name)] = row
        return result
    return {}


def _policy(profile_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(profile_input.get("composite_policy", {}))
    return {
        "profile": "rdllm-universal-composite-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
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
        "required_composite_planes": list(
            policy.get("required_composite_planes", REQUIRED_COMPOSITE_PLANES)
        ),
        "required_customer_surfaces": list(
            policy.get("required_customer_surfaces", REQUIRED_CUSTOMER_SURFACES)
        ),
        "required_standard_mappings": list(
            policy.get("required_standard_mappings", REQUIRED_STANDARD_MAPPINGS)
        ),
        "required_failure_cases": list(
            policy.get("required_failure_cases", REQUIRED_FAILURE_CASES)
        ),
        "provider_adoption_rule": "no_composite_profile_no_universal_rdllm_claim",
        "model_invocation_rule": "no_l147_gateway_no_provider_call",
        "response_rule": "no_visible_source_footer_no_answer_display",
        "settlement_rule": "no_metered_invocation_and_claim_support_no_creator_payout",
        "privacy_rule": "public_profile_contains_hashes_and_controls_not_private_payloads",
    }


def _artifact_bindings(profile_input: dict[str, Any], names: list[str]) -> dict[str, Any]:
    rows = []
    for name in names:
        artifact = profile_input.get(name)
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
    profile_input: dict[str, Any], required_families: list[str]
) -> list[dict[str, Any]]:
    family_map = _component_input_map(profile_input, "provider_family_rows")
    rows = []
    for family in sorted(required_families):
        item = family_map.get(family, {})
        row = {
            "provider_family": family,
            "native_api_binding_hash": str(item.get("native_api_binding_hash", "")),
            "runtime_adapter_hash": str(item.get("runtime_adapter_hash", "")),
            "emission_gateway_hash": str(item.get("emission_gateway_hash", "")),
            "source_footer_policy_hash": str(item.get("source_footer_policy_hash", "")),
            "settlement_policy_hash": str(item.get("settlement_policy_hash", "")),
            "public_verifier_command": str(item.get("public_verifier_command", "")),
            "sdk_binding_available": item.get("sdk_binding_available") is True,
            "supports_native_api_interception": item.get("supports_native_api_interception")
            is True,
            "supports_streaming_metering": item.get("supports_streaming_metering")
            is True,
            "supports_tool_and_agent_metering": item.get(
                "supports_tool_and_agent_metering"
            )
            is True,
            "supports_enterprise_gateway": item.get("supports_enterprise_gateway")
            is True,
            "fail_closed": item.get("fail_closed") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["native_api_binding_hash"])
            and bool(row["runtime_adapter_hash"])
            and bool(row["emission_gateway_hash"])
            and bool(row["source_footer_policy_hash"])
            and bool(row["settlement_policy_hash"])
            and row["public_verifier_command"]
            == "verify-universal-composite-rdllm-profile"
            and row["sdk_binding_available"]
            and row["supports_native_api_interception"]
            and row["supports_streaming_metering"]
            and row["supports_tool_and_agent_metering"]
            and row["supports_enterprise_gateway"]
            and row["fail_closed"]
        )
        row["provider_family_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _api_binding_rows(
    profile_input: dict[str, Any], required_bindings: list[str]
) -> list[dict[str, Any]]:
    binding_map = _component_input_map(profile_input, "api_binding_rows")
    rows = []
    for binding in sorted(required_bindings):
        item = binding_map.get(binding, {})
        row = {
            "api_binding": binding,
            "request_normalizer_hash": str(item.get("request_normalizer_hash", "")),
            "response_normalizer_hash": str(item.get("response_normalizer_hash", "")),
            "stream_meter_hash": str(item.get("stream_meter_hash", "")),
            "tool_call_meter_hash": str(item.get("tool_call_meter_hash", "")),
            "footer_injector_hash": str(item.get("footer_injector_hash", "")),
            "provider_family": str(item.get("provider_family", "")),
            "expected_provider_family": REQUIRED_API_BINDING_PROVIDER_FAMILIES.get(
                binding, ""
            ),
            "covered": item.get("covered") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            bool(row["request_normalizer_hash"])
            and bool(row["response_normalizer_hash"])
            and bool(row["stream_meter_hash"])
            and bool(row["tool_call_meter_hash"])
            and bool(row["footer_injector_hash"])
            and bool(row["provider_family"])
            and row["provider_family"] == row["expected_provider_family"]
            and row["covered"]
            and row["fail_closed"]
        )
        row["api_binding_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _composite_plane_rows(
    profile_input: dict[str, Any], required_planes: list[str]
) -> list[dict[str, Any]]:
    plane_map = _component_input_map(profile_input, "composite_plane_rows")
    rows = []
    for plane in sorted(required_planes):
        item = plane_map.get(plane, {})
        row = {
            "plane": plane,
            "control_hash": str(item.get("control_hash", "")),
            "artifact_hash": str(item.get("artifact_hash", "")),
            "verifier_command": str(item.get("verifier_command", "")),
            "public_surface": str(item.get("public_surface", "")),
            "settlement_relevant": item.get("settlement_relevant") is True,
            "customer_visible_when_relevant": item.get("customer_visible_when_relevant")
            is True,
            "covered": item.get("covered") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            bool(row["control_hash"])
            and bool(row["artifact_hash"])
            and bool(row["verifier_command"])
            and bool(row["public_surface"])
            and row["covered"]
            and row["fail_closed"]
            and (
                not row["settlement_relevant"]
                or row["customer_visible_when_relevant"]
            )
        )
        row["composite_plane_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _customer_surface_rows(
    profile_input: dict[str, Any], required_surfaces: list[str]
) -> list[dict[str, Any]]:
    surface_map = _component_input_map(profile_input, "customer_surface_rows")
    rows = []
    for surface in sorted(required_surfaces):
        item = surface_map.get(surface, {})
        row = {
            "surface": surface,
            "surface_contract_hash": str(item.get("surface_contract_hash", "")),
            "public_path": str(item.get("public_path", "")),
            "client_enforcement_hash": str(item.get("client_enforcement_hash", "")),
            "visible_or_downloadable": item.get("visible_or_downloadable") is True,
            "tamper_evident": item.get("tamper_evident") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
            "covered": item.get("covered") is True,
        }
        row["ready"] = (
            bool(row["surface_contract_hash"])
            and bool(row["public_path"])
            and bool(row["client_enforcement_hash"])
            and row["visible_or_downloadable"]
            and row["tamper_evident"]
            and row["privacy_preserving"]
            and row["covered"]
        )
        row["customer_surface_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _standard_mapping_rows(
    profile_input: dict[str, Any], required_standards: list[str]
) -> list[dict[str, Any]]:
    standard_map = _component_input_map(profile_input, "standard_mapping_rows")
    rows = []
    for standard in sorted(required_standards):
        item = standard_map.get(standard, {})
        row = {
            "standard": standard,
            "mapping_hash": str(item.get("mapping_hash", "")),
            "version_or_url": str(item.get("version_or_url", "")),
            "mapped_artifact": str(item.get("mapped_artifact", "")),
            "validator_command": str(item.get("validator_command", "")),
            "covered": item.get("covered") is True,
            "normative_or_compatibility": str(
                item.get("normative_or_compatibility", "")
            ),
        }
        row["ready"] = (
            bool(row["mapping_hash"])
            and bool(row["version_or_url"])
            and bool(row["mapped_artifact"])
            and bool(row["validator_command"])
            and row["covered"]
            and row["normative_or_compatibility"]
            in {"normative", "compatibility", "bridge"}
        )
        row["standard_mapping_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _failure_case_rows(
    profile_input: dict[str, Any], required_cases: list[str]
) -> list[dict[str, Any]]:
    case_map = _component_input_map(profile_input, "failure_case_rows")
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
            and row["verifier_command"] == "verify-universal-composite-rdllm-profile"
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


def _artifact_summary(profile_input: dict[str, Any], name: str) -> dict[str, Any]:
    artifact = profile_input.get(name)
    return _summary(artifact if isinstance(artifact, dict) else None)


def make_universal_composite_rdllm_profile(
    profile_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create the L148 universal composite RDLLM deployment profile."""

    policy = _policy(profile_input)
    required_artifacts = list(policy["required_core_artifacts"])
    artifact_bindings = _artifact_bindings(profile_input, required_artifacts)
    bindings = _binding_by_name(artifact_bindings)
    provider_rows = _provider_family_rows(
        profile_input, list(policy["required_provider_families"])
    )
    api_rows = _api_binding_rows(profile_input, list(policy["required_api_bindings"]))
    plane_rows = _composite_plane_rows(
        profile_input, list(policy["required_composite_planes"])
    )
    surface_rows = _customer_surface_rows(
        profile_input, list(policy["required_customer_surfaces"])
    )
    standard_rows = _standard_mapping_rows(
        profile_input, list(policy["required_standard_mappings"])
    )
    failure_rows = _failure_case_rows(
        profile_input, list(policy["required_failure_cases"])
    )

    certification_summary = _artifact_summary(profile_input, "certification_report")
    root_summary = _artifact_summary(profile_input, "universal_rdllm_root")
    gateway_summary = _artifact_summary(
        profile_input, "universal_emission_enforcement_gateway"
    )
    passport_summary = _artifact_summary(profile_input, "universal_rdllm_passport")
    standard_summary = _artifact_summary(profile_input, "universal_adoption_standard")
    interop_summary = _artifact_summary(profile_input, "universal_interop_test_kit")
    proof_graph_summary = _artifact_summary(profile_input, "proof_dependency_graph")
    assurance_summary = _artifact_summary(profile_input, "assurance_bundle")
    provider_card = profile_input.get("provider_attribution_card", {})
    integration_profile = profile_input.get("integration_profile", {})
    discovery_manifest = profile_input.get("discovery_manifest", {})

    assurance_artifact_types = set(assurance_summary.get("artifact_types", []))
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
        "provider_family_rows": provider_rows,
        "api_binding_rows": api_rows,
        "composite_plane_rows": plane_rows,
        "customer_surface_rows": surface_rows,
        "standard_mapping_rows": standard_rows,
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
        "certification_passed_l147_or_higher": (
            certification_summary.get("status") == "passed"
            and _level_at_least(certification_summary.get("highest_level"), "RDLLM-L147")
        ),
        "passport_ready_l137": (
            passport_summary.get("status") == "ready"
            and _level_at_least(
                passport_summary.get("target_certification_level"), "RDLLM-L137"
            )
        ),
        "adoption_standard_ready_l138": (
            standard_summary.get("status") == "ready"
            and _level_at_least(
                standard_summary.get("target_certification_level"), "RDLLM-L138"
            )
        ),
        "interop_kit_ready_l139": (
            interop_summary.get("status") == "ready"
            and _level_at_least(
                interop_summary.get("target_certification_level"), "RDLLM-L139"
            )
        ),
        "root_ready_l146": (
            root_summary.get("status") == "ready"
            and _level_at_least(
                root_summary.get("target_certification_level"), "RDLLM-L146"
            )
            and int(root_summary.get("failed_check_count", 0) or 0) == 0
        ),
        "emission_gateway_ready_l147": (
            gateway_summary.get("status") == "ready"
            and _level_at_least(
                gateway_summary.get("target_certification_level"), "RDLLM-L147"
            )
            and int(gateway_summary.get("failed_check_count", 0) or 0) == 0
        ),
        "all_provider_families_ready": _all_ready(provider_rows),
        "all_api_bindings_ready": _all_ready(api_rows),
        "all_composite_planes_ready": _all_ready(plane_rows),
        "all_customer_surfaces_ready": _all_ready(surface_rows),
        "all_standard_mappings_ready": _all_ready(standard_rows),
        "all_failure_cases_prove_blocking": _all_ready(failure_rows),
        "source_footer_surface_public": (
            public_surfaces.get("source_footer_delivery") is True
            or public_surfaces.get("source_footer") is True
        ),
        "composite_profile_publication_declared": (
            public_surfaces.get("universal_composite_rdllm_profile") is True
            or bool(discovery.get("universal_composite_rdllm_profile_path"))
        ),
        "discovery_advertises_composite_profile": (
            discovery.get("universal_composite_rdllm_profile_path")
            == DEFAULT_WELL_KNOWN_PATH
            or public_surfaces.get("universal_composite_rdllm_profile") is True
        ),
        "assurance_binds_runtime_gateway_or_post_release": (
            "universal_emission_enforcement_gateway" in assurance_artifact_types
            or "universal_rdllm_root" in assurance_artifact_types
            or bool(gateway_summary)
        ),
        "proof_graph_acyclic": (
            int(proof_graph_summary.get("cycle_node_count", 0) or 0) == 0
            and proof_graph_summary.get("status") in {"ready", "ok"}
        ),
        "privacy_preserved": (
            not private_findings
            and _private_strings_absent(
                public_projection,
                profile_input,
            )
        ),
    }

    failure_modes = []
    if not checks["all_required_artifacts_present"]:
        failure_modes.append("composite_required_artifact_missing")
    if not checks["all_required_artifact_hashes_reproducible"]:
        failure_modes.append("composite_artifact_hash_not_reproducible")
    if not checks["certification_passed_l147_or_higher"]:
        failure_modes.append("composite_certification_below_l147")
    if not checks["root_ready_l146"]:
        failure_modes.append("composite_l146_root_not_ready")
    if not checks["emission_gateway_ready_l147"]:
        failure_modes.append("composite_l147_gateway_not_ready")
    if not checks["all_provider_families_ready"]:
        failure_modes.append("composite_provider_family_gap")
    if not checks["all_api_bindings_ready"]:
        failure_modes.append("composite_api_binding_gap")
    if not checks["all_composite_planes_ready"]:
        failure_modes.append("composite_control_plane_gap")
    if not checks["all_customer_surfaces_ready"]:
        failure_modes.append("composite_customer_surface_gap")
    if not checks["all_standard_mappings_ready"]:
        failure_modes.append("composite_standard_mapping_gap")
    if not checks["source_footer_surface_public"]:
        failure_modes.append("composite_source_footer_surface_missing")
    if not checks["proof_graph_acyclic"]:
        failure_modes.append("composite_proof_graph_cycle")
    if not checks["privacy_preserved"]:
        failure_modes.append("composite_private_payload_leak")

    authorized = all(checks.values())
    profile = {
        "profile_version": UNIVERSAL_COMPOSITE_RDLLM_PROFILE_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "composite_policy": policy,
        "artifact_bindings": artifact_bindings,
        "provider_family_rows": provider_rows,
        "api_binding_rows": api_rows,
        "composite_plane_rows": plane_rows,
        "customer_surface_rows": surface_rows,
        "standard_mapping_rows": standard_rows,
        "failure_case_rows": failure_rows,
        "evidence_commitments": {
            "artifact_binding_root": artifact_bindings["artifact_binding_root"],
            "provider_family_root": merkle_root(
                [row["provider_family_row_hash"] for row in provider_rows]
            ),
            "api_binding_root": merkle_root(
                [row["api_binding_row_hash"] for row in api_rows]
            ),
            "composite_plane_root": merkle_root(
                [row["composite_plane_row_hash"] for row in plane_rows]
            ),
            "customer_surface_root": merkle_root(
                [row["customer_surface_row_hash"] for row in surface_rows]
            ),
            "standard_mapping_root": merkle_root(
                [row["standard_mapping_row_hash"] for row in standard_rows]
            ),
            "failure_case_root": merkle_root(
                [row["failure_case_row_hash"] for row in failure_rows]
            ),
        },
        "checks": checks,
        "deployment_decision": {
            "universal_composite_authorized": authorized,
            "provider_claim_allowed": authorized,
            "native_model_invocation_allowed": authorized,
            "customer_response_display_allowed": authorized,
            "creator_settlement_allowed": authorized,
            "failure_modes": failure_modes,
        },
        "verifier_commands": [
            "verify-universal-composite-rdllm-profile",
            "verify-universal-emission-enforcement-gateway",
            "verify-universal-rdllm-root",
            "verify-universal-interop-test-kit",
            "verify-universal-adoption-standard",
            "verify-universal-rdllm-passport",
            "verify-proof-dependency-graph",
            "verify-assurance-bundle",
            "verify-discovery-manifest",
            "verify-integration-profile",
            "verify-provider-card",
            "verify-certification-attestation",
        ],
        "research_controls": {
            "citation_validity_relevance_support": "cited_but_not_verified_and_deep_research_citation_audit",
            "source_footer_fact_verification": "link_accessibility_relevance_and_fact_support_are_checked_before_customer_display",
            "rag_document_attribution": "retrieved_documents_are_ranked_by_claim_utility_not_only_by_top_k_retrieval_position",
            "argument_level_runtime_provenance": "pact_style_argument_and_tool_provenance",
            "runtime_agent_protection": "safeagent_style_fail_closed_runtime_guard",
            "attested_pipeline_release": "attesting_llm_pipelines_and_l146_root",
            "tool_call_warrants": "warrant_certificate_authority_tool_chain_receipts",
            "creator_runtime_access_attribution": "sovereign_context_protocol_style_access_events_are_logged_licensed_and_attributable",
            "runtime_governance_receipts": "verifiable_runtime_governance",
            "dual_attribution_verification": "davinci_internal_external_claim_verification",
            "training_origin_attribution": "mechanistic_data_attribution_style_training_origin_evidence_is_separated_from_runtime_citations",
            "provider_neutral_observability": "opentelemetry_genai_semantic_conventions",
            "cross_provider_api_translation": "hub_and_spoke_ir_style_request_response_and_stream_mapping_for_provider_apis",
            "content_credentials": "c2pa_content_credentials",
            "code_provenance": "hybrid_source_tracker_style_code_attribution",
            "research_urls": {
                "cited_but_not_verified": "https://arxiv.org/abs/2605.06635",
                "source_attribution_in_rag": "https://arxiv.org/abs/2507.04480",
                "mechanistic_data_attribution": "https://arxiv.org/abs/2601.21996",
                "sovereign_context_protocol": "https://arxiv.org/abs/2603.27094",
                "hybrid_source_tracker": "https://arxiv.org/abs/2605.28510",
                "llm_rosetta_cross_provider_ir": "https://arxiv.org/abs/2604.09360",
                "opentelemetry_genai": "https://opentelemetry.io/docs/specs/semconv/gen-ai/",
                "c2pa_content_credentials": "https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html",
                "ietf_scitt": "https://www.rfc-editor.org/rfc/rfc9943.html",
                "amazon_bedrock_converse": "https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html",
                "azure_openai_responses": "https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/responses",
                "openrouter_chat_completions": "https://openrouter.ai/docs/api-reference/chat-completion",
            },
        },
        "privacy": {
            "public_profile_contains_private_prompts": False,
            "public_profile_contains_private_outputs": False,
            "public_profile_contains_source_text": False,
            "public_profile_contains_customer_identifiers": False,
            "hash_only_artifact_commitments": True,
        },
        "summary": {
            "status": "ready" if authorized else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_gateway_level": MINIMUM_GATEWAY_LEVEL,
            "failed_check_count": sum(1 for value in checks.values() if not value),
            "failure_mode_count": len(failure_modes),
            "core_artifact_count": artifact_bindings["artifact_count"],
            "provider_family_count": len(provider_rows),
            "covered_provider_family_count": _count(provider_rows),
            "api_binding_count": len(api_rows),
            "covered_api_binding_count": _count(api_rows),
            "composite_plane_count": len(plane_rows),
            "covered_composite_plane_count": _count(plane_rows),
            "customer_surface_count": len(surface_rows),
            "covered_customer_surface_count": _count(surface_rows),
            "standard_mapping_count": len(standard_rows),
            "covered_standard_mapping_count": _count(standard_rows),
            "failure_case_count": len(failure_rows),
            "offline_verification_supported": True,
            "privacy_preserved": checks["privacy_preserved"],
        },
    }
    profile["universal_composite_rdllm_profile_hash"] = hash_payload(
        _hashable_profile(profile)
    )
    if signing_secret:
        profile["signature"] = sign_payload(
            _hashable_profile(profile), signing_secret
        )
    return profile


def validate_universal_composite_rdllm_profile_shape(
    profile: dict[str, Any],
) -> list[str]:
    """Validate the public L148 profile shape."""

    errors: list[str] = []
    required = (
        "profile_version",
        "issuer",
        "created_at",
        "composite_policy",
        "artifact_bindings",
        "provider_family_rows",
        "api_binding_rows",
        "composite_plane_rows",
        "customer_surface_rows",
        "standard_mapping_rows",
        "failure_case_rows",
        "evidence_commitments",
        "checks",
        "deployment_decision",
        "verifier_commands",
        "research_controls",
        "privacy",
        "summary",
        "universal_composite_rdllm_profile_hash",
    )
    for key in required:
        if key not in profile:
            errors.append(f"missing universal composite RDLLM profile field: {key}")
    if errors:
        return errors
    if profile.get("profile_version") != UNIVERSAL_COMPOSITE_RDLLM_PROFILE_VERSION:
        errors.append("universal composite RDLLM profile version is unsupported")
    if profile.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal composite RDLLM profile target level is not RDLLM-L148")
    if profile.get("composite_policy", {}).get("well_known_path") != DEFAULT_WELL_KNOWN_PATH:
        errors.append("universal composite RDLLM profile well-known path is incorrect")
    return errors


def verify_universal_composite_rdllm_profile(
    profile: dict[str, Any],
    *,
    profile_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L148 profile against its replay input."""

    errors = validate_universal_composite_rdllm_profile_shape(profile)
    if errors:
        return errors

    private_paths = _contains_private_fields(profile)
    if private_paths:
        errors.append(
            "universal composite RDLLM profile exposes private field(s): "
            + ", ".join(private_paths[:10])
        )
    if not _private_strings_absent(profile, profile_input):
        errors.append("universal composite RDLLM profile leaks private replay text")

    expected_hash = hash_payload(_hashable_profile(profile))
    if expected_hash != profile.get("universal_composite_rdllm_profile_hash"):
        errors.append("universal composite RDLLM profile hash is not reproducible")

    expected = make_universal_composite_rdllm_profile(
        profile_input,
        issuer=profile.get("issuer", DEFAULT_ISSUER),
        created_at=profile.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "composite_policy",
        "artifact_bindings",
        "provider_family_rows",
        "api_binding_rows",
        "composite_plane_rows",
        "customer_surface_rows",
        "standard_mapping_rows",
        "failure_case_rows",
        "evidence_commitments",
        "checks",
        "deployment_decision",
        "verifier_commands",
        "research_controls",
        "privacy",
        "summary",
    ):
        if expected.get(key) != profile.get(key):
            errors.append(f"universal composite RDLLM profile {key} does not match replay input")
    if (
        expected.get("universal_composite_rdllm_profile_hash")
        != profile.get("universal_composite_rdllm_profile_hash")
    ):
        errors.append("universal composite RDLLM profile hash does not match replay input")
    if signing_secret:
        expected_signature = sign_payload(_hashable_profile(profile), signing_secret)
        if profile.get("signature") != expected_signature:
            errors.append("universal composite RDLLM profile signature is invalid")
    return errors
