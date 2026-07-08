"""Universal provider adapter harness.

The L157 layer makes provider adoption replayable. L156 proves that every
supported foundation-model family must expose the same RDLLM contract; L157
proves that provider-native fixture shapes normalize into that contract across
sync, stream, tool, retrieval, batch, webhook, and copied-output modes before
display or settlement.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root
from rdllm.universal_foundation_adoption_kernel import (
    REQUIRED_PROVIDER_FAMILIES,
)

UNIVERSAL_PROVIDER_ADAPTER_HARNESS_VERSION = (
    "rdllm-universal-provider-adapter-harness/v1"
)
UNIVERSAL_PROVIDER_ADAPTER_HARNESS_SCHEMA = (
    "docs/schemas/universal_provider_adapter_harness.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L157"
MINIMUM_ADOPTION_LEVEL = "RDLLM-L156"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-provider-adapter-harness.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "universal_foundation_adoption_kernel",
    "universal_provider_wire_protocol",
    "universal_claim_provenance_envelope",
    "source_footer_delivery",
    "client_attribution_enforcement",
    "response_envelope",
    "citation_url_health",
    "source_freshness_audit",
    "evidence_locator_manifest",
    "warranted_source_footer",
    "trust_registry",
    "composite_foundation_adapter",
    "foundation_provider_conformance",
    "foundation_runtime_adapter",
)

REQUIRED_FIXTURE_MODES = (
    "sync_text",
    "streaming_text",
    "tool_call",
    "retrieval_context",
    "batch_callback",
    "webhook",
    "copy_export",
)

REQUIRED_NORMALIZED_RESPONSE_FIELDS = (
    "response_id",
    "provider_family",
    "model_id",
    "output_hash",
    "claim_provenance_hash",
    "source_footer_hash",
    "status_resolver_hash",
    "kernel_hash",
    "wire_protocol_hash",
    "settlement_meter_hash",
    "telemetry_trace_hash",
    "copy_status_link_hash",
)

REQUIRED_NEGATIVE_FIXTURES = (
    "native_output_missing_kernel_hash",
    "stream_final_missing_footer_hash",
    "tool_call_unbound_to_claim",
    "copy_export_missing_status_link",
    "unsupported_claim_passed",
    "provider_family_unmapped",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_provider_adapter_harness_hash",
    "universal_foundation_adoption_kernel_hash",
    "universal_provider_wire_protocol_hash",
    "universal_claim_provenance_envelope_hash",
    "foundation_runtime_adapter_hash",
    "foundation_provider_conformance_hash",
    "composite_foundation_adapter_hash",
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


def load_universal_provider_adapter_harness_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L157 adapter harness."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_harness(harness: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in harness.items()
        if key not in {"universal_provider_adapter_harness_hash", "signature"}
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
    public_payload: dict[str, Any], harness_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in harness_input.get("private_strings", [])
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
    harness_input: dict[str, Any], key: str
) -> dict[str, dict[str, Any]]:
    value = harness_input.get(key, {})
    if isinstance(value, dict):
        return {str(name): row for name, row in value.items() if isinstance(row, dict)}
    if isinstance(value, list):
        result: dict[str, dict[str, Any]] = {}
        for row in value:
            if not isinstance(row, dict):
                continue
            if row.get("provider_family") and row.get("fixture_mode"):
                name = f"{row['provider_family']}:{row['fixture_mode']}"
            else:
                name = row.get("field") or row.get("case_id")
            if name:
                result[str(name)] = row
        return result
    return {}


def _policy(harness_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(harness_input.get("adapter_harness_policy", {}))
    return {
        "profile": "rdllm-universal-provider-adapter-harness-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_adoption_level": MINIMUM_ADOPTION_LEVEL,
        "well_known_path": DEFAULT_WELL_KNOWN_PATH,
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_provider_families": list(
            policy.get("required_provider_families", REQUIRED_PROVIDER_FAMILIES)
        ),
        "required_fixture_modes": list(
            policy.get("required_fixture_modes", REQUIRED_FIXTURE_MODES)
        ),
        "required_normalized_response_fields": list(
            policy.get(
                "required_normalized_response_fields",
                REQUIRED_NORMALIZED_RESPONSE_FIELDS,
            )
        ),
        "required_negative_fixtures": list(
            policy.get("required_negative_fixtures", REQUIRED_NEGATIVE_FIXTURES)
        ),
        "native_fixture_rule": "provider_native_sync_stream_tool_retrieval_batch_webhook_and_copy_export_fixtures_must_normalize_to_one_rdllm_response_contract",
        "text_attribution_rule": "normalized_claim_rows_must_bind_generation_time_claim_provenance_source_support_status_resolver_footer_and_copy_status_link_before_user_visible_text",
        "footer_rule": "rendered_and_exported_source_footers_must_derive_from_the_normalized_response_contract_not_posthoc_citation_lookup",
        "settlement_rule": "provider_native_usage_can_meter_creator_royalties_only_after_the_adapter_harness_binds_output_identity_sources_and_settlement_meter",
        "privacy_rule": "public_adapter_harness_contains_hashes_roots_counts_statuses_and_paths_not_private_prompts_outputs_sources_or_provider_payloads",
    }


def _artifact_bindings(harness_input: dict[str, Any], names: list[str]) -> dict[str, Any]:
    rows = []
    for name in names:
        artifact = harness_input.get(name)
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


def _provider_mode_rows(
    harness_input: dict[str, Any],
    required_families: list[str],
    required_modes: list[str],
) -> list[dict[str, Any]]:
    row_map = _component_input_map(harness_input, "provider_mode_rows")
    kernel_hash = _declared_hash(harness_input.get("universal_foundation_adoption_kernel"))
    wire_hash = _declared_hash(harness_input.get("universal_provider_wire_protocol"))
    claim_hash = _declared_hash(harness_input.get("universal_claim_provenance_envelope"))
    footer_hash = _declared_hash(harness_input.get("source_footer_delivery"))
    client_hash = _declared_hash(harness_input.get("client_attribution_enforcement"))
    rows = []
    for family in required_families:
        for mode in required_modes:
            item = row_map.get(f"{family}:{mode}", {})
            row = {
                "provider_family": family,
                "fixture_mode": mode,
                "native_fixture_hash": str(item.get("native_fixture_hash", "")),
                "adapter_spec_hash": str(item.get("adapter_spec_hash", "")),
                "normalized_response_hash": str(
                    item.get("normalized_response_hash", "")
                ),
                "kernel_hash": str(item.get("kernel_hash", kernel_hash)),
                "wire_protocol_hash": str(item.get("wire_protocol_hash", wire_hash)),
                "claim_provenance_hash": str(
                    item.get("claim_provenance_hash", claim_hash)
                ),
                "source_footer_delivery_hash": str(
                    item.get("source_footer_delivery_hash", footer_hash)
                ),
                "status_resolver_hash": str(item.get("status_resolver_hash", "")),
                "client_enforcement_hash": str(
                    item.get("client_enforcement_hash", client_hash)
                ),
                "settlement_meter_hash": str(item.get("settlement_meter_hash", "")),
                "telemetry_trace_hash": str(item.get("telemetry_trace_hash", "")),
                "copy_status_link_hash": str(item.get("copy_status_link_hash", "")),
                "extracts_output": item.get("extracts_output") is True,
                "extracts_claims": item.get("extracts_claims") is True,
                "extracts_sources": item.get("extracts_sources") is True,
                "binds_footer": item.get("binds_footer") is True,
                "binds_status_resolver": item.get("binds_status_resolver") is True,
                "binds_tool_or_context": item.get("binds_tool_or_context") is True,
                "preserves_stream_final": item.get("preserves_stream_final") is True,
                "preserves_copy_export": item.get("preserves_copy_export") is True,
                "privacy_preserving": item.get("privacy_preserving") is True,
                "fail_closed": item.get("fail_closed") is True,
            }
            row["ready"] = (
                bool(row["native_fixture_hash"])
                and bool(row["adapter_spec_hash"])
                and bool(row["normalized_response_hash"])
                and row["kernel_hash"] == kernel_hash
                and row["wire_protocol_hash"] == wire_hash
                and row["claim_provenance_hash"] == claim_hash
                and row["source_footer_delivery_hash"] == footer_hash
                and bool(row["status_resolver_hash"])
                and row["client_enforcement_hash"] == client_hash
                and bool(row["settlement_meter_hash"])
                and bool(row["telemetry_trace_hash"])
                and bool(row["copy_status_link_hash"])
                and row["extracts_output"]
                and row["extracts_claims"]
                and row["extracts_sources"]
                and row["binds_footer"]
                and row["binds_status_resolver"]
                and row["binds_tool_or_context"]
                and row["preserves_stream_final"]
                and row["preserves_copy_export"]
                and row["privacy_preserving"]
                and row["fail_closed"]
            )
            row["provider_mode_row_hash"] = hash_payload(row)
            rows.append(row)
    return rows


def _normalized_field_rows(
    harness_input: dict[str, Any],
    required_fields: list[str],
    required_family_count: int,
    required_mode_count: int,
) -> list[dict[str, Any]]:
    row_map = _component_input_map(harness_input, "normalized_field_rows")
    rows = []
    for field in required_fields:
        item = row_map.get(field, {})
        row = {
            "field": field,
            "field_path_hash": str(item.get("field_path_hash", "")),
            "adapter_spec_root": str(item.get("adapter_spec_root", "")),
            "covered_provider_family_count": int(
                item.get("covered_provider_family_count", 0) or 0
            ),
            "covered_fixture_mode_count": int(
                item.get("covered_fixture_mode_count", 0) or 0
            ),
            "required_in_normalized_response": item.get(
                "required_in_normalized_response"
            )
            is True,
            "required_in_stream_final": item.get("required_in_stream_final") is True,
            "required_in_copy_export": item.get("required_in_copy_export") is True,
            "privacy_preserving": item.get("privacy_preserving") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["ready"] = (
            bool(row["field_path_hash"])
            and bool(row["adapter_spec_root"])
            and row["covered_provider_family_count"] >= required_family_count
            and row["covered_fixture_mode_count"] >= required_mode_count
            and row["required_in_normalized_response"]
            and row["required_in_stream_final"]
            and row["required_in_copy_export"]
            and row["privacy_preserving"]
            and row["fail_closed"]
        )
        row["normalized_field_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _negative_fixture_rows(
    harness_input: dict[str, Any], required_cases: list[str]
) -> list[dict[str, Any]]:
    row_map = _component_input_map(harness_input, "negative_fixture_rows")
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
            and row["verifier_command"] == "verify-universal-provider-adapter-harness"
            and row["expected_block"]
            and row["observed_block"]
        )
        row["negative_fixture_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _all_ready(rows: list[dict[str, Any]]) -> bool:
    return bool(rows) and all(row.get("ready") is True for row in rows)


def _count(rows: list[dict[str, Any]], key: str = "ready") -> int:
    return sum(1 for row in rows if row.get(key) is True)


def _artifact_summary(harness_input: dict[str, Any], name: str) -> dict[str, Any]:
    artifact = harness_input.get(name)
    return _summary(artifact if isinstance(artifact, dict) else None)


def make_universal_provider_adapter_harness(
    harness_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create the L157 universal provider adapter harness artifact."""

    policy = _policy(harness_input)
    required_artifacts = list(policy["required_core_artifacts"])
    artifact_bindings = _artifact_bindings(harness_input, required_artifacts)
    bindings = _binding_by_name(artifact_bindings)
    required_families = list(policy["required_provider_families"])
    required_modes = list(policy["required_fixture_modes"])
    provider_mode_rows = _provider_mode_rows(
        harness_input, required_families, required_modes
    )
    normalized_field_rows = _normalized_field_rows(
        harness_input,
        list(policy["required_normalized_response_fields"]),
        len(required_families),
        len(required_modes),
    )
    negative_fixture_rows = _negative_fixture_rows(
        harness_input, list(policy["required_negative_fixtures"])
    )

    certification_summary = _artifact_summary(harness_input, "certification_report")
    kernel_summary = _artifact_summary(
        harness_input, "universal_foundation_adoption_kernel"
    )
    wire_summary = _artifact_summary(harness_input, "universal_provider_wire_protocol")
    claim_summary = _artifact_summary(
        harness_input, "universal_claim_provenance_envelope"
    )

    provider_card = harness_input.get("provider_attribution_card", {})
    if not isinstance(provider_card, dict):
        provider_card = {}
    integration_profile = harness_input.get("integration_profile", {})
    if not isinstance(integration_profile, dict):
        integration_profile = {}
    discovery_manifest = harness_input.get("discovery_manifest", {})
    if not isinstance(discovery_manifest, dict):
        discovery_manifest = {}

    core_artifacts_ready = all(
        row.get("present") is True
        and row.get("hash_reproducible") is True
        and row.get("status")
        in {"", "ready", "released", "passed", "verified", "attested"}
        for row in bindings.values()
    )
    public_projection = {
        "adapter_harness_policy": policy,
        "artifact_bindings": artifact_bindings,
        "provider_mode_rows": provider_mode_rows,
        "normalized_field_rows": normalized_field_rows,
        "negative_fixture_rows": negative_fixture_rows,
    }
    private_findings = _contains_private_fields(public_projection)
    checks = {
        "all_core_artifacts_present_and_hash_reproducible": core_artifacts_ready,
        "certification_reaches_l156": (
            certification_summary.get("status") == "passed"
            and _level_at_least(
                certification_summary.get("highest_level"), MINIMUM_ADOPTION_LEVEL
            )
        ),
        "l156_adoption_kernel_ready": (
            kernel_summary.get("status") == "ready"
            and kernel_summary.get("target_certification_level")
            == MINIMUM_ADOPTION_LEVEL
        ),
        "provider_wire_protocol_ready": (
            wire_summary.get("status") == "ready"
            and _level_at_least(
                wire_summary.get("target_certification_level"), "RDLLM-L151"
            )
        ),
        "claim_provenance_envelope_ready": (
            claim_summary.get("status") == "ready"
            and _level_at_least(
                claim_summary.get("target_certification_level"), "RDLLM-L150"
            )
        ),
        "all_provider_modes_ready": _all_ready(provider_mode_rows),
        "all_normalized_fields_ready": _all_ready(normalized_field_rows),
        "all_negative_fixtures_ready": _all_ready(negative_fixture_rows),
        "provider_card_declares_adapter_harness": provider_card.get(
            "public_disclosure_surfaces", {}
        ).get("universal_provider_adapter_harness")
        is True,
        "integration_profile_declares_adapter_harness": (
            integration_profile.get("public_surfaces", {}).get(
                "universal_provider_adapter_harness"
            )
            is True
            and integration_profile.get("schemas", {}).get(
                "universal_provider_adapter_harness"
            )
            == UNIVERSAL_PROVIDER_ADAPTER_HARNESS_SCHEMA
        ),
        "discovery_manifest_exposes_adapter_harness": (
            discovery_manifest.get("discovery", {}).get(
                "universal_provider_adapter_harness_path"
            )
            == DEFAULT_WELL_KNOWN_PATH
            and discovery_manifest.get("schemas", {}).get(
                "universal_provider_adapter_harness"
            )
            == UNIVERSAL_PROVIDER_ADAPTER_HARNESS_SCHEMA
        ),
        "privacy_preserved": (
            not private_findings
            and _private_strings_absent(public_projection, harness_input)
        ),
    }
    failure_modes = []
    if not checks["all_core_artifacts_present_and_hash_reproducible"]:
        failure_modes.append("adapter_harness_core_artifact_gap")
    if not checks["certification_reaches_l156"] or not checks[
        "l156_adoption_kernel_ready"
    ]:
        failure_modes.append("adapter_harness_kernel_level_gap")
    if not checks["provider_wire_protocol_ready"]:
        failure_modes.append("adapter_harness_provider_wire_gap")
    if not checks["claim_provenance_envelope_ready"]:
        failure_modes.append("adapter_harness_claim_provenance_gap")
    if not checks["all_provider_modes_ready"]:
        failure_modes.append("adapter_harness_provider_mode_gap")
    if not checks["all_normalized_fields_ready"]:
        failure_modes.append("adapter_harness_normalized_field_gap")
    if not checks["all_negative_fixtures_ready"]:
        failure_modes.append("adapter_harness_negative_fixture_gap")
    if not (
        checks["provider_card_declares_adapter_harness"]
        and checks["integration_profile_declares_adapter_harness"]
        and checks["discovery_manifest_exposes_adapter_harness"]
    ):
        failure_modes.append("adapter_harness_public_surface_gap")
    if not checks["privacy_preserved"]:
        failure_modes.append("adapter_harness_private_string_leak")

    evidence_commitments = {
        "artifact_binding_root": artifact_bindings["artifact_binding_root"],
        "provider_mode_root": merkle_root(
            [row["provider_mode_row_hash"] for row in provider_mode_rows]
        ),
        "normalized_field_root": merkle_root(
            [row["normalized_field_row_hash"] for row in normalized_field_rows]
        ),
        "negative_fixture_root": merkle_root(
            [row["negative_fixture_row_hash"] for row in negative_fixture_rows]
        ),
    }
    harness_decision = {
        "universal_provider_adapter_harness_authorized": not failure_modes,
        "native_provider_output_without_normalization_allowed": False,
        "stream_final_without_footer_allowed": False,
        "tool_call_without_claim_binding_allowed": False,
        "copy_export_without_status_link_allowed": False,
        "direct_settlement_without_adapter_harness_allowed": False,
        "failure_modes": failure_modes,
    }
    privacy = {
        "private_field_paths": _contains_private_fields(public_projection),
        "private_strings_absent": True,
        "raw_prompts_outputs_sources_or_provider_payloads_embedded": False,
        "hash_only_native_fixture_commitments": True,
    }
    summary = {
        "status": "ready"
        if harness_decision["universal_provider_adapter_harness_authorized"]
        else "blocked",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_adoption_level": MINIMUM_ADOPTION_LEVEL,
        "core_artifact_count": artifact_bindings["artifact_count"],
        "provider_family_count": len(required_families),
        "fixture_mode_count": len(required_modes),
        "provider_mode_count": len(provider_mode_rows),
        "ready_provider_mode_count": _count(provider_mode_rows),
        "normalized_field_count": len(normalized_field_rows),
        "ready_normalized_field_count": _count(normalized_field_rows),
        "negative_fixture_count": len(negative_fixture_rows),
        "ready_negative_fixture_count": _count(negative_fixture_rows),
        "failure_mode_count": len(failure_modes),
        "offline_verification_supported": True,
        "native_fixture_replay_supported": True,
        "provider_neutral_normalization_supported": not failure_modes,
        "claim_level_text_attribution_required": True,
        "source_footer_grounding_required": True,
        "copy_export_status_link_required": True,
        "privacy_preserved": checks["privacy_preserved"],
    }
    harness = {
        "adapter_harness_version": UNIVERSAL_PROVIDER_ADAPTER_HARNESS_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "adapter_harness_policy": policy,
        "artifact_bindings": artifact_bindings,
        "provider_mode_rows": provider_mode_rows,
        "normalized_field_rows": normalized_field_rows,
        "negative_fixture_rows": negative_fixture_rows,
        "evidence_commitments": evidence_commitments,
        "checks": checks,
        "harness_decision": harness_decision,
        "verifier_commands": {
            "create": "universal-provider-adapter-harness",
            "verify": "verify-universal-provider-adapter-harness",
            "well_known_path": DEFAULT_WELL_KNOWN_PATH,
            "schema": UNIVERSAL_PROVIDER_ADAPTER_HARNESS_SCHEMA,
        },
        "research_controls": {
            "training_data_pinpoint_provenance": "https://arxiv.org/abs/2605.05687",
            "traceable_training_data_provenance": "https://arxiv.org/abs/2603.17884",
            "citation_hallucination_audit": "https://arxiv.org/abs/2605.07723",
            "evidence_grounded_rag_claim_evaluation": "https://arxiv.org/abs/2605.01664",
            "rag_source_attribution": "https://arxiv.org/abs/2507.04480",
            "opentelemetry_genai_semconv": "https://opentelemetry.io/docs/specs/semconv/gen-ai/",
            "model_context_protocol": "https://modelcontextprotocol.io/specification/2025-11-25/",
            "openai_responses": "https://platform.openai.com/docs/api-reference/responses",
            "anthropic_messages": "https://docs.anthropic.com/en/api/messages",
            "google_gemini_generate_content": "https://ai.google.dev/gemini-api/docs/text-generation",
            "amazon_bedrock_converse": "https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html",
            "openrouter_chat_completions": "https://openrouter.ai/docs/api-reference/chat-completion",
        },
        "privacy": privacy,
        "summary": summary,
    }
    harness["privacy"]["private_strings_absent"] = _private_strings_absent(
        harness, harness_input
    )
    if not harness["privacy"]["private_strings_absent"]:
        harness["harness_decision"]["failure_modes"].append(
            "adapter_harness_private_string_leak"
        )
        harness["summary"]["status"] = "blocked"
        harness["summary"]["failure_mode_count"] = len(
            harness["harness_decision"]["failure_modes"]
        )
        harness["summary"]["privacy_preserved"] = False
    harness["universal_provider_adapter_harness_hash"] = hash_payload(
        _hashable_harness(harness)
    )
    if signing_secret:
        harness["signature"] = sign_payload(
            harness["universal_provider_adapter_harness_hash"], signing_secret
        )
    return harness


def validate_universal_provider_adapter_harness_shape(
    harness: dict[str, Any],
) -> list[str]:
    """Validate the public L157 provider adapter harness shape."""

    errors: list[str] = []
    required = (
        "adapter_harness_version",
        "issuer",
        "created_at",
        "adapter_harness_policy",
        "artifact_bindings",
        "provider_mode_rows",
        "normalized_field_rows",
        "negative_fixture_rows",
        "evidence_commitments",
        "checks",
        "harness_decision",
        "verifier_commands",
        "research_controls",
        "privacy",
        "summary",
        "universal_provider_adapter_harness_hash",
    )
    for key in required:
        if key not in harness:
            errors.append(f"missing universal provider adapter harness field: {key}")
    if errors:
        return errors
    if (
        harness.get("adapter_harness_version")
        != UNIVERSAL_PROVIDER_ADAPTER_HARNESS_VERSION
    ):
        errors.append("universal provider adapter harness version is unsupported")
    if harness.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal provider adapter harness target level is not RDLLM-L157")
    if (
        harness.get("adapter_harness_policy", {}).get("well_known_path")
        != DEFAULT_WELL_KNOWN_PATH
    ):
        errors.append("universal provider adapter harness well-known path is invalid")
    decision = harness.get("harness_decision", {})
    if decision.get("native_provider_output_without_normalization_allowed") is not False:
        errors.append("universal provider adapter harness permits unnormalized output")
    if decision.get("stream_final_without_footer_allowed") is not False:
        errors.append("universal provider adapter harness permits streams without footer")
    if decision.get("tool_call_without_claim_binding_allowed") is not False:
        errors.append("universal provider adapter harness permits unbound tool calls")
    if decision.get("copy_export_without_status_link_allowed") is not False:
        errors.append("universal provider adapter harness permits copied output without status link")
    if decision.get("direct_settlement_without_adapter_harness_allowed") is not False:
        errors.append("universal provider adapter harness permits direct settlement without harness")
    return errors


def verify_universal_provider_adapter_harness(
    harness: dict[str, Any],
    *,
    harness_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L157 adapter harness artifact against private replay input."""

    errors = validate_universal_provider_adapter_harness_shape(harness)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_harness(harness))
    if expected_hash != harness.get("universal_provider_adapter_harness_hash"):
        errors.append("universal provider adapter harness hash is not reproducible")

    expected = make_universal_provider_adapter_harness(
        harness_input,
        issuer=harness.get("issuer", DEFAULT_ISSUER),
        created_at=harness.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "adapter_harness_policy",
        "artifact_bindings",
        "provider_mode_rows",
        "normalized_field_rows",
        "negative_fixture_rows",
        "evidence_commitments",
        "checks",
        "harness_decision",
        "verifier_commands",
        "research_controls",
        "privacy",
        "summary",
    ):
        if expected.get(key) != harness.get(key):
            errors.append(
                f"universal provider adapter harness {key} does not match replay input"
            )
    if (
        expected.get("universal_provider_adapter_harness_hash")
        != harness.get("universal_provider_adapter_harness_hash")
    ):
        errors.append("universal provider adapter harness hash does not match replay input")
    if signing_secret and expected.get("signature") != harness.get("signature"):
        errors.append("universal provider adapter harness signature is invalid")
    if harness.get("summary", {}).get("status") != "ready":
        errors.append("universal provider adapter harness status is not ready")
    for check, passed in harness.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal provider adapter harness check failed: {check}")
    if _contains_private_fields(harness):
        errors.append("universal provider adapter harness exposes a private field")
    return errors
