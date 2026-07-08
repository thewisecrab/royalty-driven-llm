"""Universal provider onboarding and migration covenants.

The L175 layer turns the L174 procurement/regulatory reliance contract into an
executable adoption covenant for foundation model providers. A provider cannot
claim production RDLLM adoption by publishing terms alone: native API surfaces,
SDKs, gateways, marketplace listings, customer migration artifacts, rollout
gates, rollback controls, and negative fixtures must all bind to the same L174
contract before enterprise migration or public provider support is allowed.
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

UNIVERSAL_PROVIDER_ONBOARDING_MIGRATION_COVENANT_VERSION = (
    "rdllm-universal-provider-onboarding-migration-covenant/v1"
)
UNIVERSAL_PROVIDER_ONBOARDING_MIGRATION_COVENANT_SCHEMA = (
    "docs/schemas/universal_provider_onboarding_migration_covenant.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L175"
MINIMUM_PROCUREMENT_RELIANCE_LEVEL = "RDLLM-L174"
MINIMUM_PROVIDER_BINDING_LEVEL = "RDLLM-L168"
MINIMUM_PROVIDER_CONFORMANCE_LEVEL = "RDLLM-L169"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-provider-onboarding-migration-covenant.json"
)

REQUIRED_PROVIDER_FAMILIES = (
    "openai",
    "anthropic",
    "google_gemini",
    "meta_llama",
    "mistral",
    "cohere",
    "xai",
    "amazon_bedrock",
    "microsoft_azure_ai",
    "alibaba_qwen",
    "deepseek",
    "ai21",
    "ibm_watsonx",
    "nvidia_nim",
    "huggingface_inference",
    "oracle_oci_generative_ai",
    "together_ai",
    "groq",
)

REQUIRED_NATIVE_API_SURFACES = (
    "text_generation",
    "chat_or_messages",
    "responses_api",
    "streaming_final_event",
    "batch_generation",
    "tool_calling",
    "agent_runtime",
    "retrieval_or_file_search",
    "embeddings",
    "fine_tuning_or_customization",
    "evaluations",
    "model_context_protocol",
    "image_generation",
    "audio_generation_or_transcription",
    "safety_and_policy_guardrails",
    "admin_audit_export",
    "billing_metering",
    "copy_export_or_share",
)

REQUIRED_MIGRATION_ARTIFACTS = (
    "provider_migration_guide",
    "api_mapping_matrix",
    "sdk_shim",
    "gateway_proxy",
    "conformance_ci_fixture",
    "sample_source_footer_response",
    "telemetry_mapping",
    "billing_settlement_mapping",
    "enterprise_terms_addendum",
    "marketplace_listing_pack",
    "regulator_export_template",
    "creator_challenge_runbook",
    "rollback_plan",
    "customer_support_runbook",
)

REQUIRED_ROLLOUT_GATES = (
    "executive_owner_assigned",
    "native_surface_mapping_complete",
    "sandbox_fixture_passed",
    "canary_rollout_green",
    "sdk_gateway_released",
    "enterprise_terms_updated",
    "marketplace_listing_verified",
    "regulator_export_enabled",
    "creator_challenge_desk_enabled",
    "settlement_meter_connected",
    "copy_export_preservation_enabled",
    "model_version_rollover_bound",
    "incident_rollback_exercised",
    "general_availability_approved",
)

REQUIRED_NEGATIVE_ONBOARDING_FAILURES = (
    "legacy_endpoint_without_footer",
    "sdk_strips_source_footer",
    "streaming_final_missing_receipt",
    "tool_output_unattributed",
    "batch_response_missing_manifest",
    "enterprise_terms_override_l174",
    "marketplace_claim_without_l174",
    "regulator_export_disabled",
    "model_version_alias_drift",
    "customer_proxy_bypass",
    "creator_challenge_sla_missing",
    "settlement_meter_disconnected",
    "private_payload_in_migration_log",
    "rollback_serves_unattributed_output",
)

DECLARED_HASH_FIELDS = (
    "universal_provider_onboarding_migration_covenant_hash",
    "universal_procurement_regulatory_reliance_contract_hash",
    "universal_foundation_provider_binding_matrix_hash",
    "universal_provider_conformance_runner_receipt_hash",
    "integration_profile_hash",
    "discovery_manifest_hash",
    "provider_family_hash",
    "native_api_contract_hash",
    "adapter_release_hash",
    "sdk_release_hash",
    "gateway_policy_hash",
    "migration_artifact_hash",
    "surface_mapping_hash",
    "rollout_gate_hash",
    "fixture_hash",
    "verifier_hash",
    "telemetry_hash",
    "settlement_hash",
    "rollback_hash",
    "support_hash",
    "contract_hash",
    "mapping_hash",
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
    "billing_record",
    "contract_terms_text",
    "migration_log_text",
    "support_ticket_text",
    "tool_payload",
    "api_key",
    "access_token",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_provider_onboarding_migration_covenant_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L175 onboarding covenant."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_covenant(covenant: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in covenant.items()
        if key
        not in {
            "universal_provider_onboarding_migration_covenant_hash",
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


def _level_number(level: Any) -> int | None:
    if not isinstance(level, str) or not level.startswith("RDLLM-L"):
        return None
    try:
        return int(level.removeprefix("RDLLM-L"))
    except ValueError:
        return None


def _level_at_least(level: Any, minimum: str) -> bool:
    current = _level_number(level)
    required = _level_number(minimum)
    return current is not None and required is not None and current >= required


def _procurement_contract_ready(contract: dict[str, Any] | None) -> bool:
    summary = _summary(contract)
    decision = contract.get("procurement_reliance_decision", {}) if contract else {}
    return bool(
        contract
        and summary.get("status") == "ready"
        and _level_at_least(
            summary.get("target_certification_level", ""),
            MINIMUM_PROCUREMENT_RELIANCE_LEVEL,
        )
        and decision.get("procurement_reliance_ready") is True
        and decision.get("enterprise_procurement_allowed") is True
    )


def _provider_binding_ready(matrix: dict[str, Any] | None) -> bool:
    summary = _summary(matrix)
    return bool(
        matrix
        and summary.get("status") == "ready"
        and _level_at_least(
            summary.get("target_certification_level", ""),
            MINIMUM_PROVIDER_BINDING_LEVEL,
        )
    )


def _provider_conformance_ready(receipt: dict[str, Any] | None) -> bool:
    summary = _summary(receipt)
    return bool(
        receipt
        and summary.get("status") == "ready"
        and _level_at_least(
            summary.get("target_certification_level", ""),
            MINIMUM_PROVIDER_CONFORMANCE_LEVEL,
        )
    )


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    fields: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if str(key) in PRIVATE_FIELD_NAMES:
                fields.append(child_path)
            fields.extend(_contains_private_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            fields.extend(_contains_private_fields(child, child_path))
    return sorted(set(fields))


def _private_strings_absent(public: dict[str, Any], covenant_input: dict[str, Any]) -> bool:
    public_json = canonical_json(public)
    private_strings = [
        str(item)
        for item in covenant_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _row_map(covenant_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    value = covenant_input.get(key, {})
    if not isinstance(value, dict):
        return {}
    return {str(name): row for name, row in value.items() if isinstance(row, dict)}


def _complete_rows(
    rows: dict[str, dict[str, Any]],
    required: tuple[str, ...],
    ready_fn,
) -> tuple[list[str], list[str]]:
    missing = [name for name in required if name not in rows]
    incomplete = [
        name for name in required if name in rows and not ready_fn(rows[name])
    ]
    return missing, incomplete


def _provider_family_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            bool(row.get("provider_family_hash")),
            bool(row.get("native_api_contract_hash")),
            bool(row.get("adapter_release_hash")),
            bool(row.get("sdk_release_hash")),
            bool(row.get("gateway_policy_hash")),
            bool(row.get("telemetry_hash")),
            bool(row.get("settlement_hash")),
            bool(row.get("rollback_hash")),
            row.get("l174_contract_accepted") is True,
            row.get("native_surface_mapped") is True,
            row.get("conformance_runner_green") is True,
            row.get("customer_migration_supported") is True,
            row.get("legacy_route_fail_closed") is True,
            row.get("no_private_payloads") is True,
        )
    )


def _native_surface_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            bool(row.get("surface_mapping_hash")),
            bool(row.get("test_fixture_hash")),
            bool(row.get("verifier_hash")),
            bool(row.get("footer_contract_hash")),
            bool(row.get("telemetry_mapping_hash")),
            row.get("mapped_for_all_required_provider_families") is True,
            row.get("source_footer_preserved") is True,
            row.get("machine_readable_sources_preserved") is True,
            row.get("settlement_meter_bound") is True,
            row.get("negative_fixture_covered") is True,
            row.get("no_private_payloads") is True,
        )
    )


def _migration_artifact_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            bool(row.get("migration_artifact_hash")),
            bool(row.get("version_hash")),
            bool(row.get("publication_hash")),
            bool(row.get("support_hash")),
            bool(row.get("rollback_hash")),
            row.get("published") is True,
            row.get("customer_executable") is True,
            row.get("binds_l174_contract") is True,
            row.get("covers_all_required_provider_families") is True,
            row.get("no_private_payloads") is True,
        )
    )


def _rollout_gate_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            bool(row.get("rollout_gate_hash")),
            bool(row.get("owner_hash")),
            bool(row.get("evidence_hash")),
            bool(row.get("verifier_hash")),
            bool(row.get("sla_hash")),
            row.get("gate_passed") is True,
            row.get("blocks_ga_on_failure") is True,
            row.get("rollback_on_failure") is True,
            row.get("audit_visible") is True,
            row.get("no_private_payloads") is True,
        )
    )


def _negative_row_ready(row: dict[str, Any]) -> bool:
    return all(
        (
            bool(row.get("fixture_hash")),
            bool(row.get("native_route_hash")),
            bool(row.get("verifier_hash")),
            row.get("expected_reject") is True,
            row.get("observed_reject") is True,
            row.get("migration_blocked") is True,
            row.get("provider_claim_blocked") is True,
            row.get("rollback_triggered") is True,
            row.get("settlement_held") is True,
            row.get("no_private_payloads") is True,
        )
    )


def make_universal_provider_onboarding_migration_covenant(
    covenant_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L175 universal provider onboarding covenant."""

    procurement_contract = covenant_input.get(
        "universal_procurement_regulatory_reliance_contract"
    )
    provider_binding_matrix = covenant_input.get(
        "universal_foundation_provider_binding_matrix"
    )
    provider_conformance_runner = covenant_input.get(
        "universal_provider_conformance_runner_receipt"
    )
    provider_rows = _row_map(covenant_input, "provider_family_rows")
    surface_rows = _row_map(covenant_input, "native_api_surface_rows")
    migration_rows = _row_map(covenant_input, "migration_artifact_rows")
    rollout_rows = _row_map(covenant_input, "rollout_gate_rows")
    negative_rows = _row_map(covenant_input, "negative_onboarding_rows")

    missing_providers, incomplete_providers = _complete_rows(
        provider_rows,
        REQUIRED_PROVIDER_FAMILIES,
        _provider_family_row_ready,
    )
    missing_surfaces, incomplete_surfaces = _complete_rows(
        surface_rows,
        REQUIRED_NATIVE_API_SURFACES,
        _native_surface_row_ready,
    )
    missing_migration, incomplete_migration = _complete_rows(
        migration_rows,
        REQUIRED_MIGRATION_ARTIFACTS,
        _migration_artifact_row_ready,
    )
    missing_rollout, incomplete_rollout = _complete_rows(
        rollout_rows,
        REQUIRED_ROLLOUT_GATES,
        _rollout_gate_row_ready,
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_rows,
        REQUIRED_NEGATIVE_ONBOARDING_FAILURES,
        _negative_row_ready,
    )

    checks = {
        "procurement_reliance_contract_bound": _artifact_hash_is_reproducible(
            procurement_contract
            if isinstance(procurement_contract, dict)
            else None
        ),
        "procurement_reliance_contract_l174_ready": _procurement_contract_ready(
            procurement_contract if isinstance(procurement_contract, dict) else None
        ),
        "provider_binding_matrix_bound": _artifact_hash_is_reproducible(
            provider_binding_matrix
            if isinstance(provider_binding_matrix, dict)
            else None
        ),
        "provider_binding_matrix_l168_ready": _provider_binding_ready(
            provider_binding_matrix
            if isinstance(provider_binding_matrix, dict)
            else None
        ),
        "provider_conformance_runner_bound": _artifact_hash_is_reproducible(
            provider_conformance_runner
            if isinstance(provider_conformance_runner, dict)
            else None
        ),
        "provider_conformance_runner_l169_ready": _provider_conformance_ready(
            provider_conformance_runner
            if isinstance(provider_conformance_runner, dict)
            else None
        ),
        "provider_family_rows_complete": not missing_providers
        and not incomplete_providers,
        "native_api_surface_rows_complete": not missing_surfaces
        and not incomplete_surfaces,
        "migration_artifact_rows_complete": not missing_migration
        and not incomplete_migration,
        "rollout_gate_rows_complete": not missing_rollout
        and not incomplete_rollout,
        "negative_onboarding_fixtures_reject": not missing_negative
        and not incomplete_negative,
        "onboarding_covenant_signed": signing_secret is not None,
    }
    failure_modes = [name for name, passed in checks.items() if not passed]
    ready = not failure_modes

    provider_root = merkle_root([
        hash_payload({"name": name, "row": provider_rows.get(name, {})})
        for name in REQUIRED_PROVIDER_FAMILIES
    ])
    surface_root = merkle_root([
        hash_payload({"name": name, "row": surface_rows.get(name, {})})
        for name in REQUIRED_NATIVE_API_SURFACES
    ])
    migration_root = merkle_root([
        hash_payload({"name": name, "row": migration_rows.get(name, {})})
        for name in REQUIRED_MIGRATION_ARTIFACTS
    ])
    rollout_root = merkle_root([
        hash_payload({"name": name, "row": rollout_rows.get(name, {})})
        for name in REQUIRED_ROLLOUT_GATES
    ])
    negative_root = merkle_root([
        hash_payload({"name": name, "row": negative_rows.get(name, {})})
        for name in REQUIRED_NEGATIVE_ONBOARDING_FAILURES
    ])

    public = {
        "universal_provider_onboarding_migration_covenant_version": (
            UNIVERSAL_PROVIDER_ONBOARDING_MIGRATION_COVENANT_VERSION
        ),
        "schema": UNIVERSAL_PROVIDER_ONBOARDING_MIGRATION_COVENANT_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": (
                "rdllm-universal-provider-onboarding-migration-policy/v1"
            ),
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_procurement_reliance_level": (
                MINIMUM_PROCUREMENT_RELIANCE_LEVEL
            ),
            "minimum_provider_binding_level": MINIMUM_PROVIDER_BINDING_LEVEL,
            "minimum_provider_conformance_level": (
                MINIMUM_PROVIDER_CONFORMANCE_LEVEL
            ),
            "provider_claim_requires_native_migration": True,
            "legacy_routes_fail_closed": True,
            "customer_migration_artifacts_required": True,
            "rollback_must_preserve_attribution": True,
            "private_payloads_forbidden_in_public_covenant": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_PROVIDER_ONBOARDING_MIGRATION_COVENANT_VERSION,
        },
        "procurement_contract_binding": {
            "present": isinstance(procurement_contract, dict),
            "artifact_hash": _declared_hash(
                procurement_contract
                if isinstance(procurement_contract, dict)
                else None
            ),
            "payload_hash": hash_payload(
                _hashable_artifact(
                    procurement_contract
                    if isinstance(procurement_contract, dict)
                    else None
                )
            ),
            "hash_reproducible": checks["procurement_reliance_contract_bound"],
            "status": _summary(
                procurement_contract
                if isinstance(procurement_contract, dict)
                else None
            ).get("status", ""),
            "level": _summary(
                procurement_contract
                if isinstance(procurement_contract, dict)
                else None
            ).get("target_certification_level", ""),
        },
        "provider_binding_matrix_binding": {
            "present": isinstance(provider_binding_matrix, dict),
            "artifact_hash": _declared_hash(
                provider_binding_matrix
                if isinstance(provider_binding_matrix, dict)
                else None
            ),
            "payload_hash": hash_payload(
                _hashable_artifact(
                    provider_binding_matrix
                    if isinstance(provider_binding_matrix, dict)
                    else None
                )
            ),
            "hash_reproducible": checks["provider_binding_matrix_bound"],
            "status": _summary(
                provider_binding_matrix
                if isinstance(provider_binding_matrix, dict)
                else None
            ).get("status", ""),
            "level": _summary(
                provider_binding_matrix
                if isinstance(provider_binding_matrix, dict)
                else None
            ).get("target_certification_level", ""),
        },
        "provider_conformance_runner_binding": {
            "present": isinstance(provider_conformance_runner, dict),
            "artifact_hash": _declared_hash(
                provider_conformance_runner
                if isinstance(provider_conformance_runner, dict)
                else None
            ),
            "payload_hash": hash_payload(
                _hashable_artifact(
                    provider_conformance_runner
                    if isinstance(provider_conformance_runner, dict)
                    else None
                )
            ),
            "hash_reproducible": checks["provider_conformance_runner_bound"],
            "status": _summary(
                provider_conformance_runner
                if isinstance(provider_conformance_runner, dict)
                else None
            ).get("status", ""),
            "level": _summary(
                provider_conformance_runner
                if isinstance(provider_conformance_runner, dict)
                else None
            ).get("target_certification_level", ""),
        },
        "provider_family_rows": provider_rows,
        "native_api_surface_rows": surface_rows,
        "migration_artifact_rows": migration_rows,
        "rollout_gate_rows": rollout_rows,
        "negative_onboarding_rows": negative_rows,
        "evidence_roots": {
            "provider_family_root": provider_root,
            "native_api_surface_root": surface_root,
            "migration_artifact_root": migration_root,
            "rollout_gate_root": rollout_root,
            "negative_onboarding_root": negative_root,
        },
        "checks": checks,
        "onboarding_decision": {
            "provider_onboarding_ready": ready,
            "native_provider_claims_allowed": ready,
            "customer_migration_allowed": ready,
            "marketplace_rollout_allowed": ready,
            "regulator_rollout_allowed": ready,
            "legacy_routes_blocked": ready,
            "settlement_release_allowed": ready,
            "failure_modes": failure_modes,
            "missing_provider_families": missing_providers,
            "incomplete_provider_families": incomplete_providers,
            "missing_native_api_surfaces": missing_surfaces,
            "incomplete_native_api_surfaces": incomplete_surfaces,
            "missing_migration_artifacts": missing_migration,
            "incomplete_migration_artifacts": incomplete_migration,
            "missing_rollout_gates": missing_rollout,
            "incomplete_rollout_gates": incomplete_rollout,
            "missing_negative_onboarding_failures": missing_negative,
            "incomplete_negative_onboarding_failures": incomplete_negative,
        },
        "coverage": {
            "required_provider_family_count": len(REQUIRED_PROVIDER_FAMILIES),
            "ready_provider_family_count": len(REQUIRED_PROVIDER_FAMILIES)
            - len(missing_providers)
            - len(incomplete_providers),
            "required_native_api_surface_count": len(REQUIRED_NATIVE_API_SURFACES),
            "ready_native_api_surface_count": len(REQUIRED_NATIVE_API_SURFACES)
            - len(missing_surfaces)
            - len(incomplete_surfaces),
            "required_migration_artifact_count": len(REQUIRED_MIGRATION_ARTIFACTS),
            "ready_migration_artifact_count": len(REQUIRED_MIGRATION_ARTIFACTS)
            - len(missing_migration)
            - len(incomplete_migration),
            "required_rollout_gate_count": len(REQUIRED_ROLLOUT_GATES),
            "ready_rollout_gate_count": len(REQUIRED_ROLLOUT_GATES)
            - len(missing_rollout)
            - len(incomplete_rollout),
            "required_negative_onboarding_failure_count": len(
                REQUIRED_NEGATIVE_ONBOARDING_FAILURES
            ),
            "ready_negative_onboarding_failure_count": len(
                REQUIRED_NEGATIVE_ONBOARDING_FAILURES
            )
            - len(missing_negative)
            - len(incomplete_negative),
        },
        "privacy": {
            "private_payload_fields": [],
            "private_strings_absent": True,
            "private_payloads_excluded": True,
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_procurement_reliance_level": (
                MINIMUM_PROCUREMENT_RELIANCE_LEVEL
            ),
            "minimum_provider_binding_level": MINIMUM_PROVIDER_BINDING_LEVEL,
            "minimum_provider_conformance_level": (
                MINIMUM_PROVIDER_CONFORMANCE_LEVEL
            ),
            "provider_family_count": len(REQUIRED_PROVIDER_FAMILIES),
            "ready_provider_family_count": len(REQUIRED_PROVIDER_FAMILIES)
            - len(missing_providers)
            - len(incomplete_providers),
            "native_api_surface_count": len(REQUIRED_NATIVE_API_SURFACES),
            "ready_native_api_surface_count": len(REQUIRED_NATIVE_API_SURFACES)
            - len(missing_surfaces)
            - len(incomplete_surfaces),
            "migration_artifact_count": len(REQUIRED_MIGRATION_ARTIFACTS),
            "ready_migration_artifact_count": len(REQUIRED_MIGRATION_ARTIFACTS)
            - len(missing_migration)
            - len(incomplete_migration),
            "rollout_gate_count": len(REQUIRED_ROLLOUT_GATES),
            "ready_rollout_gate_count": len(REQUIRED_ROLLOUT_GATES)
            - len(missing_rollout)
            - len(incomplete_rollout),
            "negative_onboarding_failure_count": len(
                REQUIRED_NEGATIVE_ONBOARDING_FAILURES
            ),
            "ready_negative_onboarding_failure_count": len(
                REQUIRED_NEGATIVE_ONBOARDING_FAILURES
            )
            - len(missing_negative)
            - len(incomplete_negative),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": True,
            "signed_provider_onboarding_covenant": signing_secret is not None,
        },
    }
    public["privacy"]["private_payload_fields"] = _contains_private_fields(public)
    public["privacy"]["private_strings_absent"] = _private_strings_absent(
        public,
        covenant_input,
    )
    public["privacy"]["private_payloads_excluded"] = (
        not public["privacy"]["private_payload_fields"]
        and public["privacy"]["private_strings_absent"]
    )
    if not public["privacy"]["private_payloads_excluded"]:
        public["checks"]["private_payloads_excluded"] = False
        for decision in (
            "provider_onboarding_ready",
            "native_provider_claims_allowed",
            "customer_migration_allowed",
            "marketplace_rollout_allowed",
            "regulator_rollout_allowed",
            "legacy_routes_blocked",
            "settlement_release_allowed",
        ):
            public["onboarding_decision"][decision] = False
        if "private_payloads_excluded" not in public["onboarding_decision"][
            "failure_modes"
        ]:
            public["onboarding_decision"]["failure_modes"].append(
                "private_payloads_excluded"
            )
        public["summary"]["status"] = "blocked"
        public["summary"]["failure_mode_count"] = len(
            public["onboarding_decision"]["failure_modes"]
        )
        public["summary"]["privacy_preserved"] = False

    public["universal_provider_onboarding_migration_covenant_hash"] = hash_payload(
        _hashable_covenant(public)
    )
    if signing_secret:
        public["signature"] = {
            "issuer": issuer,
            "algorithm": "HMAC-SHA256",
            "value": sign_payload(_hashable_covenant(public), signing_secret),
        }
    return public


def validate_universal_provider_onboarding_migration_covenant_shape(
    covenant: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for an L175 onboarding covenant."""

    errors: list[str] = []
    required = (
        "universal_provider_onboarding_migration_covenant_version",
        "schema",
        "created_at",
        "issuer",
        "policy",
        "well_known",
        "procurement_contract_binding",
        "provider_binding_matrix_binding",
        "provider_conformance_runner_binding",
        "provider_family_rows",
        "native_api_surface_rows",
        "migration_artifact_rows",
        "rollout_gate_rows",
        "negative_onboarding_rows",
        "evidence_roots",
        "checks",
        "onboarding_decision",
        "coverage",
        "privacy",
        "summary",
        "universal_provider_onboarding_migration_covenant_hash",
    )
    for key in required:
        if key not in covenant:
            errors.append(f"missing provider onboarding covenant field: {key}")
    if covenant.get("universal_provider_onboarding_migration_covenant_version") != (
        UNIVERSAL_PROVIDER_ONBOARDING_MIGRATION_COVENANT_VERSION
    ):
        errors.append(
            "unexpected universal_provider_onboarding_migration_covenant_version"
        )
    if covenant.get("schema") != UNIVERSAL_PROVIDER_ONBOARDING_MIGRATION_COVENANT_SCHEMA:
        errors.append("unexpected provider onboarding covenant schema")
    for name in REQUIRED_PROVIDER_FAMILIES:
        if name not in covenant.get("provider_family_rows", {}):
            errors.append(f"missing provider family row: {name}")
    for name in REQUIRED_NATIVE_API_SURFACES:
        if name not in covenant.get("native_api_surface_rows", {}):
            errors.append(f"missing native API surface row: {name}")
    for name in REQUIRED_MIGRATION_ARTIFACTS:
        if name not in covenant.get("migration_artifact_rows", {}):
            errors.append(f"missing migration artifact row: {name}")
    for name in REQUIRED_ROLLOUT_GATES:
        if name not in covenant.get("rollout_gate_rows", {}):
            errors.append(f"missing rollout gate row: {name}")
    for name in REQUIRED_NEGATIVE_ONBOARDING_FAILURES:
        if name not in covenant.get("negative_onboarding_rows", {}):
            errors.append(f"missing negative onboarding row: {name}")
    for check in (
        "procurement_reliance_contract_bound",
        "procurement_reliance_contract_l174_ready",
        "provider_binding_matrix_bound",
        "provider_binding_matrix_l168_ready",
        "provider_conformance_runner_bound",
        "provider_conformance_runner_l169_ready",
        "provider_family_rows_complete",
        "native_api_surface_rows_complete",
        "migration_artifact_rows_complete",
        "rollout_gate_rows_complete",
        "negative_onboarding_fixtures_reject",
        "onboarding_covenant_signed",
    ):
        if check not in covenant.get("checks", {}):
            errors.append(f"missing provider onboarding covenant check: {check}")
    return errors


def verify_universal_provider_onboarding_migration_covenant(
    covenant_input: dict[str, Any],
    covenant: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L175 onboarding covenant against replay input."""

    errors = validate_universal_provider_onboarding_migration_covenant_shape(
        covenant
    )
    expected_hash = hash_payload(_hashable_covenant(covenant))
    if (
        covenant.get("universal_provider_onboarding_migration_covenant_hash")
        != expected_hash
    ):
        errors.append("universal_provider_onboarding_migration_covenant_hash mismatch")
    private_fields = _contains_private_fields(covenant)
    if private_fields:
        errors.append(
            "provider onboarding covenant exposes private fields: "
            + ", ".join(private_fields)
        )
    if not _private_strings_absent(covenant, covenant_input):
        errors.append("provider onboarding covenant exposes private input strings")
    replayed = make_universal_provider_onboarding_migration_covenant(
        covenant_input,
        issuer=covenant.get("issuer", DEFAULT_ISSUER),
        created_at=covenant.get("created_at"),
        signing_secret=signing_secret,
    )
    if replayed.get(
        "universal_provider_onboarding_migration_covenant_hash"
    ) != covenant.get("universal_provider_onboarding_migration_covenant_hash"):
        errors.append("provider onboarding covenant does not match replay inputs")
    if covenant.get("summary", {}).get("status") != "ready":
        errors.append("provider onboarding covenant is not ready")
    if covenant.get("onboarding_decision", {}).get("provider_onboarding_ready") is not True:
        errors.append("provider onboarding covenant decision is not ready")
    if covenant.get("privacy", {}).get("private_payloads_excluded") is not True:
        errors.append("provider onboarding covenant privacy is not preserved")
    if signing_secret:
        signature = covenant.get("signature", {})
        expected_signature = sign_payload(_hashable_covenant(covenant), signing_secret)
        if not signature:
            errors.append("provider onboarding covenant is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("provider onboarding covenant signature is invalid")
    return errors
