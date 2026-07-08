"""Universal reference implementation distribution.

The L164 layer turns the L163 industry root into an installable, signed, and
reproducible reference distribution. It is the adoption bridge between "the
industry root verifies" and "a provider, gateway, SDK, MCP tool, or settlement
processor can deploy the same fail-closed mechanism without inventing a custom
integration."
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_REFERENCE_IMPLEMENTATION_DISTRIBUTION_VERSION = (
    "rdllm-universal-reference-implementation-distribution/v1"
)
UNIVERSAL_REFERENCE_IMPLEMENTATION_DISTRIBUTION_SCHEMA = (
    "docs/schemas/universal_reference_implementation_distribution.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L164"
MINIMUM_INDUSTRY_ROOT_LEVEL = "RDLLM-L163"
MINIMUM_ADOPTION_PACK_LEVEL = "RDLLM-L162"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-reference-implementation-distribution.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "certification_report",
    "certification_attestation",
    "provider_attribution_card",
    "integration_profile",
    "discovery_manifest",
    "assurance_bundle",
    "proof_dependency_graph",
    "trust_registry",
    "universal_industry_adoption_root",
    "universal_foundation_provider_adoption_pack",
    "response_envelope",
    "source_footer_delivery",
    "revenue_allocation_report",
    "finance_ledger_attestation",
)

REQUIRED_DISTRIBUTION_COMPONENTS = (
    "reference_cli_package",
    "python_sdk_package",
    "typescript_sdk_package",
    "http_gateway_middleware",
    "openapi_contract_bundle",
    "mcp_tool_server_adapter",
    "otel_collector_mapping",
    "c2pa_assertion_template",
    "w3c_vc_trust_mark_template",
    "scitt_statement_template",
    "settlement_rail_adapter",
    "conformance_ci_workflow",
    "offline_verifier_container",
    "schema_bundle",
    "sample_application",
    "procurement_policy_pack",
    "sbom_and_slsa_provenance_bundle",
)

REQUIRED_INSTALL_TARGETS = (
    "openai_responses_api",
    "anthropic_messages_api",
    "google_gemini_generate_content",
    "azure_openai_responses",
    "aws_bedrock_converse",
    "openrouter_chat_completions",
    "local_openai_compatible_runtime",
    "open_weight_llama_runtime",
    "mistral_chat_api",
    "cohere_chat_api",
    "xai_grok_api",
    "enterprise_gateway_proxy",
    "rag_retrieval_pipeline",
    "mcp_agent_runtime",
)

REQUIRED_NEGATIVE_DISTRIBUTION_FAILURES = (
    "missing_l163_industry_root",
    "unsigned_sdk_package",
    "missing_sbom",
    "missing_slsa_provenance",
    "non_reproducible_build",
    "sdk_strips_source_footer",
    "gateway_permits_unverified_response",
    "mcp_adapter_missing_source_locator",
    "otel_mapping_missing_span_attributes",
    "c2pa_template_not_bound_to_root",
    "vc_status_unavailable",
    "scitt_statement_not_logged",
    "settlement_adapter_bypasses_hold",
    "install_target_without_negative_fixture",
    "private_payload_leak",
)

DECLARED_HASH_FIELDS = (
    "universal_reference_implementation_distribution_hash",
    "universal_industry_adoption_root_hash",
    "universal_foundation_provider_adoption_pack_hash",
    "trust_registry_hash",
    "attestation_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "report_hash",
    "bundle_hash",
    "graph_hash",
    "summary_hash",
    "envelope_hash",
    "receipt_hash",
    "event_hash",
    "package_hash",
    "distribution_hash",
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


def load_universal_reference_implementation_distribution_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L164 reference distribution."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_distribution(distribution: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in distribution.items()
        if key
        not in {"universal_reference_implementation_distribution_hash", "signature"}
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
    public_payload: dict[str, Any], distribution_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(public_payload)
    private_strings = [
        str(item)
        for item in distribution_input.get("private_strings", [])
        if isinstance(item, str) and len(item) >= 8
    ]
    return all(item not in public_json for item in private_strings)


def _summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact, dict):
        return {}
    summary = artifact.get("summary")
    return summary if isinstance(summary, dict) else {}


def _level_number(level: str) -> int | None:
    if not level.startswith("RDLLM-L"):
        return None
    try:
        return int(level.removeprefix("RDLLM-L"))
    except ValueError:
        return None


def _level_at_least(level: str, minimum: str) -> bool:
    current = _level_number(level)
    required = _level_number(minimum)
    return current is not None and required is not None and current >= required


def _artifact_level(artifact: dict[str, Any] | None) -> str:
    summary = _summary(artifact)
    for key in (
        "target_certification_level",
        "highest_level",
        "minimum_certification_level",
    ):
        value = summary.get(key)
        if isinstance(value, str) and value:
            return value
    certification = artifact.get("certification") if isinstance(artifact, dict) else None
    if isinstance(certification, dict):
        value = certification.get("highest_level")
        if isinstance(value, str):
            return value
    return ""


def _artifact_binding(name: str, artifact: dict[str, Any] | None) -> dict[str, Any]:
    declared = _declared_hash(artifact)
    return {
        "artifact_hash": declared,
        "payload_hash": hash_payload(_hashable_artifact(artifact)),
        "hash_reproducible": _artifact_hash_is_reproducible(artifact),
        "status": str(_summary(artifact).get("status", "")),
        "level": _artifact_level(artifact),
        "present": isinstance(artifact, dict) and bool(artifact),
        "artifact": name,
    }


def _artifact_bindings(
    distribution_input: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        name: _artifact_binding(
            name,
            distribution_input.get(name)
            if isinstance(distribution_input.get(name), dict)
            else None,
        )
        for name in REQUIRED_CORE_ARTIFACTS
    }


def _row_map(distribution_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    rows = distribution_input.get(key, {})
    return rows if isinstance(rows, dict) else {}


def _distribution_component_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "component_hash",
        "package_hash",
        "version_hash",
        "sbom_hash",
        "slsa_provenance_hash",
        "build_recipe_hash",
        "signature_hash",
        "transparency_log_entry_hash",
        "verifier_command_hash",
        "public_path_hash",
    )
    required_flags = (
        "reproducible_build",
        "signed",
        "sbom_available",
        "slsa_provenance_available",
        "transparency_logged",
        "verifier_available",
        "fail_closed_default",
        "private_payloads_excluded",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _install_target_ready(row: dict[str, Any]) -> bool:
    required_hashes = (
        "target_hash",
        "adapter_hash",
        "fixture_hash",
        "ci_result_hash",
        "verifier_command_hash",
        "negative_fixture_hash",
        "root_binding_hash",
    )
    required_flags = (
        "adapter_available",
        "fixture_available",
        "ci_passed",
        "offline_verifier_available",
        "fail_closed_default",
        "source_footer_preserved",
        "telemetry_mapping_bound",
        "settlement_meter_bound",
        "root_requirement_enforced",
    )
    return all(str(row.get(field, "")) for field in required_hashes) and all(
        row.get(flag) is True for flag in required_flags
    )


def _negative_failure_ready(row: dict[str, Any]) -> bool:
    return all(
        row.get(flag) is True
        for flag in (
            "expected_reject",
            "observed_reject",
            "installation_blocked",
            "root_reliance_blocked",
            "settlement_held",
            "public_status_marked_failed",
        )
    ) and bool(row.get("fixture_hash"))


def _complete_rows(
    rows: dict[str, dict[str, Any]],
    required: tuple[str, ...],
    predicate: Any,
) -> tuple[list[str], list[str]]:
    missing = [name for name in required if name not in rows]
    incomplete = [
        name
        for name in required
        if name in rows and not predicate(rows.get(name, {}))
    ]
    return missing, incomplete


def _is_ready_artifact(artifact: dict[str, Any] | None) -> bool:
    if not isinstance(artifact, dict):
        return False
    status = _summary(artifact).get("status")
    return status in {
        "ready",
        "passed",
        "verified",
        "attested",
        "published",
        "released",
    } or bool(artifact)


def _root_binds_adoption_pack(
    industry_root: dict[str, Any] | None,
    adoption_pack: dict[str, Any] | None,
) -> bool:
    if not isinstance(industry_root, dict) or not isinstance(adoption_pack, dict):
        return False
    binding = industry_root.get("artifact_bindings", {}).get(
        "universal_foundation_provider_adoption_pack", {}
    )
    return binding.get("artifact_hash") == _declared_hash(adoption_pack)


def make_universal_reference_implementation_distribution(
    distribution_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L164 universal reference implementation distribution."""

    industry_root = distribution_input.get("universal_industry_adoption_root")
    adoption_pack = distribution_input.get("universal_foundation_provider_adoption_pack")
    artifact_bindings = _artifact_bindings(distribution_input)
    component_rows = _row_map(distribution_input, "distribution_component_rows")
    install_target_rows = _row_map(distribution_input, "install_target_rows")
    negative_distribution_rows = _row_map(
        distribution_input, "negative_distribution_rows"
    )

    missing_components, incomplete_components = _complete_rows(
        component_rows,
        REQUIRED_DISTRIBUTION_COMPONENTS,
        _distribution_component_ready,
    )
    missing_targets, incomplete_targets = _complete_rows(
        install_target_rows,
        REQUIRED_INSTALL_TARGETS,
        _install_target_ready,
    )
    missing_negative, incomplete_negative = _complete_rows(
        negative_distribution_rows,
        REQUIRED_NEGATIVE_DISTRIBUTION_FAILURES,
        _negative_failure_ready,
    )

    core_artifacts_bound = all(
        binding["present"] and binding["hash_reproducible"]
        for binding in artifact_bindings.values()
    )
    core_artifacts_ready = all(
        _is_ready_artifact(distribution_input.get(name))
        for name in REQUIRED_CORE_ARTIFACTS
        if name
        not in {
            "response_envelope",
            "source_footer_delivery",
            "revenue_allocation_report",
            "finance_ledger_attestation",
        }
    )
    industry_root_l163_ready = bool(
        isinstance(industry_root, dict)
        and _summary(industry_root).get("status") == "ready"
        and _summary(industry_root).get("target_certification_level")
        == MINIMUM_INDUSTRY_ROOT_LEVEL
        and industry_root.get("adoption_decision", {}).get(
            "industry_adoption_root_ready"
        )
        is True
    )
    adoption_pack_l162_ready = bool(
        isinstance(adoption_pack, dict)
        and _summary(adoption_pack).get("status") == "ready"
        and _summary(adoption_pack).get("target_certification_level")
        == MINIMUM_ADOPTION_PACK_LEVEL
    )
    root_binds_adoption_pack = _root_binds_adoption_pack(
        industry_root if isinstance(industry_root, dict) else None,
        adoption_pack if isinstance(adoption_pack, dict) else None,
    )
    root_well_known_valid = bool(
        isinstance(industry_root, dict)
        and industry_root.get("well_known", {}).get("path")
        == "/.well-known/rdllm/universal-industry-adoption-root.json"
    )
    all_distribution_components_installable = (
        not missing_components and not incomplete_components
    )
    all_install_targets_fail_closed = not missing_targets and not incomplete_targets
    negative_distribution_fixtures_reject = (
        not missing_negative and not incomplete_negative
    )
    sbom_and_slsa_provenance_available = all(
        row.get("sbom_available") is True
        and row.get("slsa_provenance_available") is True
        for row in component_rows.values()
    ) and bool(component_rows)
    transparency_entries_available = all(
        row.get("transparency_logged") is True
        and bool(row.get("transparency_log_entry_hash"))
        for row in component_rows.values()
    ) and bool(component_rows)

    checks = {
        "core_artifacts_bound": core_artifacts_bound,
        "core_artifacts_ready": core_artifacts_ready,
        "industry_root_l163_ready": industry_root_l163_ready,
        "adoption_pack_l162_ready": adoption_pack_l162_ready,
        "industry_root_binds_l162_adoption_pack": root_binds_adoption_pack,
        "industry_root_well_known_valid": root_well_known_valid,
        "all_distribution_components_installable": (
            all_distribution_components_installable
        ),
        "all_install_targets_fail_closed": all_install_targets_fail_closed,
        "sbom_and_slsa_provenance_available": sbom_and_slsa_provenance_available,
        "transparency_log_entries_available": transparency_entries_available,
        "negative_distribution_fixtures_reject": (
            negative_distribution_fixtures_reject
        ),
        "reference_distribution_signed": bool(signing_secret),
    }
    failure_modes = [name for name, passed in checks.items() if not passed]

    component_root = merkle_root([
        hash_payload({"name": name, "row": component_rows.get(name, {})})
        for name in REQUIRED_DISTRIBUTION_COMPONENTS
    ])
    install_target_root = merkle_root([
        hash_payload({"name": name, "row": install_target_rows.get(name, {})})
        for name in REQUIRED_INSTALL_TARGETS
    ])
    negative_root = merkle_root([
        hash_payload({"name": name, "row": negative_distribution_rows.get(name, {})})
        for name in REQUIRED_NEGATIVE_DISTRIBUTION_FAILURES
    ])

    distribution: dict[str, Any] = {
        "universal_reference_implementation_distribution_version": (
            UNIVERSAL_REFERENCE_IMPLEMENTATION_DISTRIBUTION_VERSION
        ),
        "schema": UNIVERSAL_REFERENCE_IMPLEMENTATION_DISTRIBUTION_SCHEMA,
        "created_at": created_at or now_iso(),
        "issuer": issuer,
        "policy": {
            "policy_version": (
                "rdllm-universal-reference-implementation-distribution-policy/v1"
            ),
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_industry_root_level": MINIMUM_INDUSTRY_ROOT_LEVEL,
            "minimum_adoption_pack_level": MINIMUM_ADOPTION_PACK_LEVEL,
            "signed_installable_distribution_required": True,
            "self_assertion_sufficient": False,
            "reproducible_build_required": True,
            "sbom_required": True,
            "slsa_provenance_required": True,
            "transparency_log_required": True,
            "fail_closed_default_required": True,
            "source_footer_reliance_requires_distribution": True,
            "creator_settlement_release_requires_distribution": True,
        },
        "well_known": {
            "path": DEFAULT_WELL_KNOWN_PATH,
            "returns": UNIVERSAL_REFERENCE_IMPLEMENTATION_DISTRIBUTION_VERSION,
        },
        "artifact_bindings": artifact_bindings,
        "distribution_component_rows": {
            name: component_rows.get(name, {})
            for name in REQUIRED_DISTRIBUTION_COMPONENTS
        },
        "install_target_rows": {
            name: install_target_rows.get(name, {})
            for name in REQUIRED_INSTALL_TARGETS
        },
        "negative_distribution_rows": {
            name: negative_distribution_rows.get(name, {})
            for name in REQUIRED_NEGATIVE_DISTRIBUTION_FAILURES
        },
        "distribution_model": {
            "type": "signed_reproducible_installable_reference_distribution",
            "industry_root_hash": _declared_hash(
                industry_root if isinstance(industry_root, dict) else None
            ),
            "adoption_pack_hash": _declared_hash(
                adoption_pack if isinstance(adoption_pack, dict) else None
            ),
            "root_binds_adoption_pack": root_binds_adoption_pack,
            "distribution_binds_industry_root": True,
            "distribution_binds_components": True,
            "distribution_binds_install_targets": True,
        },
        "evidence_roots": {
            "artifact_binding_root": merkle_root([
                hash_payload({"name": name, "binding": binding})
                for name, binding in artifact_bindings.items()
            ]),
            "distribution_component_root": component_root,
            "install_target_root": install_target_root,
            "negative_distribution_root": negative_root,
        },
        "distribution_decision": {
            "reference_distribution_ready": not failure_modes,
            "provider_self_assertion_sufficient": False,
            "source_footer_reliance_allowed": not failure_modes,
            "creator_settlement_release_allowed": not failure_modes,
            "provider_installation_allowed": not failure_modes,
            "failure_modes": failure_modes,
            "missing_distribution_components": missing_components,
            "incomplete_distribution_components": incomplete_components,
            "missing_install_targets": missing_targets,
            "incomplete_install_targets": incomplete_targets,
            "missing_negative_distribution_failures": missing_negative,
            "incomplete_negative_distribution_failures": incomplete_negative,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "native_provider_payloads_disclosed": False,
            "tool_payloads_disclosed": False,
            "customer_records_disclosed": False,
            "payment_account_details_disclosed": False,
            "public_distribution_uses_hashes_status_rows_and_verifier_commands": True,
        },
    }
    checks["private_fields_absent"] = not _contains_private_fields(distribution)
    checks["private_strings_absent"] = _private_strings_absent(
        distribution, distribution_input
    )
    distribution["checks"] = checks
    if not checks["private_fields_absent"] or not checks["private_strings_absent"]:
        distribution["distribution_decision"]["reference_distribution_ready"] = False
        for check in ("private_fields_absent", "private_strings_absent"):
            if (
                not checks[check]
                and check not in distribution["distribution_decision"]["failure_modes"]
            ):
                distribution["distribution_decision"]["failure_modes"].append(check)

    distribution["summary"] = {
        "status": "ready"
        if distribution["distribution_decision"]["reference_distribution_ready"]
        else "blocked",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_industry_root_level": MINIMUM_INDUSTRY_ROOT_LEVEL,
        "minimum_adoption_pack_level": MINIMUM_ADOPTION_PACK_LEVEL,
        "core_artifact_count": len(REQUIRED_CORE_ARTIFACTS),
        "bound_core_artifact_count": sum(
            1
            for binding in artifact_bindings.values()
            if binding["present"] and binding["hash_reproducible"]
        ),
        "distribution_component_count": len(REQUIRED_DISTRIBUTION_COMPONENTS),
        "ready_distribution_component_count": len(REQUIRED_DISTRIBUTION_COMPONENTS)
        - len(missing_components)
        - len(incomplete_components),
        "install_target_count": len(REQUIRED_INSTALL_TARGETS),
        "ready_install_target_count": len(REQUIRED_INSTALL_TARGETS)
        - len(missing_targets)
        - len(incomplete_targets),
        "negative_distribution_failure_count": len(
            REQUIRED_NEGATIVE_DISTRIBUTION_FAILURES
        ),
        "ready_negative_distribution_failure_count": len(
            REQUIRED_NEGATIVE_DISTRIBUTION_FAILURES
        )
        - len(missing_negative)
        - len(incomplete_negative),
        "failure_mode_count": len(
            distribution["distribution_decision"]["failure_modes"]
        ),
        "signed_installable_distribution": bool(signing_secret),
        "reproducible_builds_required": True,
        "sbom_and_slsa_provenance_available": (
            sbom_and_slsa_provenance_available
        ),
        "transparency_log_entries_available": transparency_entries_available,
        "source_footer_reliance_allowed": distribution["distribution_decision"][
            "source_footer_reliance_allowed"
        ],
        "creator_settlement_release_allowed": distribution["distribution_decision"][
            "creator_settlement_release_allowed"
        ],
        "provider_installation_allowed": distribution["distribution_decision"][
            "provider_installation_allowed"
        ],
        "privacy_preserved": checks["private_fields_absent"]
        and checks["private_strings_absent"],
    }
    distribution["universal_reference_implementation_distribution_hash"] = (
        hash_payload(_hashable_distribution(distribution))
    )
    distribution["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(
                distribution["universal_reference_implementation_distribution_hash"],
                signing_secret,
            )
            if signing_secret
            else ""
        ),
    }
    return distribution


def validate_universal_reference_implementation_distribution_shape(
    distribution: dict[str, Any],
) -> list[str]:
    """Validate the public shape of an L164 reference distribution."""

    errors: list[str] = []
    if (
        distribution.get("universal_reference_implementation_distribution_version")
        != UNIVERSAL_REFERENCE_IMPLEMENTATION_DISTRIBUTION_VERSION
    ):
        errors.append(
            "universal reference implementation distribution version is unsupported"
        )
    if distribution.get("schema") != UNIVERSAL_REFERENCE_IMPLEMENTATION_DISTRIBUTION_SCHEMA:
        errors.append(
            "universal reference implementation distribution schema is unsupported"
        )
    if (
        distribution.get("summary", {}).get("target_certification_level")
        != TARGET_CERTIFICATION_LEVEL
    ):
        errors.append(
            "universal reference implementation distribution target level is not RDLLM-L164"
        )
    if distribution.get("well_known", {}).get("path") != DEFAULT_WELL_KNOWN_PATH:
        errors.append(
            "universal reference implementation distribution well-known path is invalid"
        )
    for section in (
        "artifact_bindings",
        "distribution_component_rows",
        "install_target_rows",
        "negative_distribution_rows",
        "distribution_model",
        "evidence_roots",
        "distribution_decision",
        "privacy",
        "checks",
        "summary",
    ):
        if not isinstance(distribution.get(section), dict):
            errors.append(
                f"universal reference implementation distribution missing {section}"
            )
    for component in REQUIRED_DISTRIBUTION_COMPONENTS:
        if component not in distribution.get("distribution_component_rows", {}):
            errors.append(
                "universal reference implementation distribution missing component "
                f"{component}"
            )
    for target in REQUIRED_INSTALL_TARGETS:
        if target not in distribution.get("install_target_rows", {}):
            errors.append(
                "universal reference implementation distribution missing install "
                f"target {target}"
            )
    for failure in REQUIRED_NEGATIVE_DISTRIBUTION_FAILURES:
        if failure not in distribution.get("negative_distribution_rows", {}):
            errors.append(
                "universal reference implementation distribution missing negative "
                f"failure {failure}"
            )
    if distribution.get("distribution_decision", {}).get(
        "provider_self_assertion_sufficient"
    ):
        errors.append(
            "universal reference implementation distribution permits self assertion"
        )
    if _contains_private_fields(distribution):
        errors.append(
            "universal reference implementation distribution exposes a private field"
        )
    return errors


def verify_universal_reference_implementation_distribution(
    distribution: dict[str, Any],
    *,
    distribution_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify an L164 reference implementation distribution."""

    errors = validate_universal_reference_implementation_distribution_shape(
        distribution
    )
    expected_hash = hash_payload(_hashable_distribution(distribution))
    if expected_hash != distribution.get(
        "universal_reference_implementation_distribution_hash"
    ):
        errors.append(
            "universal reference implementation distribution hash is not reproducible"
        )

    expected = make_universal_reference_implementation_distribution(
        distribution_input,
        issuer=str(distribution.get("issuer", DEFAULT_ISSUER)),
        created_at=str(distribution.get("created_at", "")) or None,
        signing_secret=signing_secret,
    )
    for key in (
        "artifact_bindings",
        "distribution_component_rows",
        "install_target_rows",
        "negative_distribution_rows",
        "distribution_model",
        "evidence_roots",
        "distribution_decision",
        "privacy",
        "checks",
        "summary",
    ):
        if distribution.get(key) != expected.get(key):
            errors.append(
                "universal reference implementation distribution "
                f"{key} does not match replay input"
            )
    if distribution.get(
        "universal_reference_implementation_distribution_hash"
    ) != expected.get("universal_reference_implementation_distribution_hash"):
        errors.append(
            "universal reference implementation distribution hash does not match replay input"
        )
    if distribution.get("signature") != expected.get("signature"):
        errors.append(
            "universal reference implementation distribution signature is invalid"
        )
    if distribution.get("summary", {}).get("status") != "ready":
        errors.append("universal reference implementation distribution status is not ready")
    for check, passed in distribution.get("checks", {}).items():
        if not passed:
            errors.append(
                "universal reference implementation distribution check failed: "
                f"{check}"
            )
    if _contains_private_fields(distribution):
        errors.append(
            "universal reference implementation distribution exposes a private field"
        )
    if not _private_strings_absent(distribution, distribution_input):
        errors.append(
            "universal reference implementation distribution exposes private input text"
        )
    return errors
