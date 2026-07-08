"""Universal RDLLM interoperability test kit.

The L139 layer moves the L138 adoption standard from a publishable contract to a
portable implementation kit. It proves that provider adapters, SDK bindings,
CI/offline runners, golden fixtures, and negative mutation cases are present and
replayable before an implementation claims universal RDLLM compatibility.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.composite_foundation_adapter import DEFAULT_PROVIDER_FAMILIES
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_INTEROP_TEST_KIT_VERSION = "rdllm-universal-interop-test-kit/v1"
UNIVERSAL_INTEROP_TEST_KIT_SCHEMA = (
    "docs/schemas/universal_interop_test_kit.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L139"
MINIMUM_INPUT_LEVEL = "RDLLM-L138"
DEFAULT_WELL_KNOWN_PATH = "/.well-known/rdllm/universal-interop-test-kit.json"

REQUIRED_CORE_ARTIFACTS = (
    "universal_adoption_standard",
    "universal_rdllm_passport",
    "conformance_vector_pack",
    "integration_profile",
    "discovery_manifest",
    "provider_attribution_card",
    "certification_report",
    "foundation_provider_conformance",
    "composite_foundation_adapter",
    "foundation_runtime_adapter",
    "universal_invocation_guard",
    "universal_invocation_coverage",
    "source_footer_delivery",
    "response_envelope",
    "trust_registry",
)

REQUIRED_KIT_COMPONENTS = (
    "golden_provider_fixtures",
    "negative_mutation_fixtures",
    "openapi_contract_bundle",
    "offline_verifier_bundle",
    "sdk_reference_bindings",
    "ci_replay_workflow",
    "procurement_checklist",
)

REQUIRED_SDK_BINDINGS = (
    "openapi",
    "http_curl",
    "python",
    "typescript",
)

REQUIRED_EXECUTION_TARGETS = (
    "local_cli",
    "ci_runner",
    "offline_auditor",
    "gateway_middleware",
)

REQUIRED_FAILURE_CASES = (
    "missing_source_footer",
    "missing_public_proof_object",
    "invalid_signature",
    "stale_provider_route",
    "rights_denied_source",
    "hallucinated_citation",
    "unguarded_native_call",
    "private_text_leak",
)

REQUIRED_VERIFIER_COMMANDS = (
    "verify-universal-adoption-standard",
    "verify-universal-rdllm-passport",
    "verify-conformance-vector-pack",
    "verify-foundation-provider-conformance",
    "verify-foundation-runtime-adapter",
    "verify-universal-invocation-guard",
    "verify-source-footer-delivery",
    "verify-response-envelope",
    "verify-universal-interop-test-kit",
)

DECLARED_HASH_FIELDS = (
    "universal_interop_test_kit_hash",
    "universal_adoption_standard_hash",
    "universal_rdllm_passport_hash",
    "universal_invocation_coverage_hash",
    "universal_invocation_guard_hash",
    "foundation_runtime_adapter_hash",
    "foundation_provider_conformance_hash",
    "composite_foundation_adapter_hash",
    "source_footer_delivery_hash",
    "trust_registry_hash",
    "vector_pack_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "report_hash",
    "envelope_hash",
    "bundle_hash",
    "summary_hash",
    "statement_hash",
    "receipt_hash",
    "event_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "raw_model_output",
    "raw_native_response",
    "native_response_body",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "raw_answer_text",
    "rendered_output",
    "copied_output",
    "source_text",
    "training_text",
    "document_text",
    "full_source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
    "customer_id",
    "customer_email",
    "invoice_text",
    "payment_method",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "license_server_secret",
    "raw_license_token",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_interop_test_kit_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L139 universal interop test kit."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_interop_test_kit_hash", "signature"}
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


def _private_strings_absent(report: dict[str, Any], kit_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item) for item in kit_input.get("private_strings", []) if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _level_number(level: Any) -> int:
    if not isinstance(level, str):
        return -1
    try:
        return int(level.removeprefix("RDLLM-L"))
    except ValueError:
        return -1


def _level_at_least(level: Any, minimum: str) -> bool:
    return _level_number(level) >= _level_number(minimum)


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


def _policy(kit_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(kit_input.get("interop_policy", {}))
    return {
        "profile": "rdllm-universal-interop-test-kit-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_provider_families": list(
            policy.get("required_provider_families", DEFAULT_PROVIDER_FAMILIES)
        ),
        "required_kit_components": list(
            policy.get("required_kit_components", REQUIRED_KIT_COMPONENTS)
        ),
        "required_sdk_bindings": list(
            policy.get("required_sdk_bindings", REQUIRED_SDK_BINDINGS)
        ),
        "required_execution_targets": list(
            policy.get("required_execution_targets", REQUIRED_EXECUTION_TARGETS)
        ),
        "required_failure_cases": list(
            policy.get("required_failure_cases", REQUIRED_FAILURE_CASES)
        ),
        "required_verifier_commands": list(
            policy.get("required_verifier_commands", REQUIRED_VERIFIER_COMMANDS)
        ),
        "on_missing_l138_standard": "reject_universal_interop_claim",
        "on_missing_provider_fixture": "block_compatibility_publication",
        "on_failed_negative_case": "block_sdk_release",
        "on_missing_sdk_binding": "block_procurement_approval",
        "on_private_text_leak": "block_publication",
    }


def _artifact_bindings(kit_input: dict[str, Any], names: list[str]) -> dict[str, Any]:
    rows = []
    for name in names:
        artifact = kit_input.get(name)
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


def _component_input_map(kit_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    value = kit_input.get(key, {})
    if isinstance(value, dict):
        return {
            str(name): row
            for name, row in value.items()
            if isinstance(row, dict)
        }
    if isinstance(value, list):
        return {
            str(row.get("name") or row.get("component") or row.get("binding") or row.get("target") or row.get("case_id")): row
            for row in value
            if isinstance(row, dict)
        }
    return {}


def _kit_component_rows(
    kit_input: dict[str, Any], required_components: list[str]
) -> list[dict[str, Any]]:
    component_map = _component_input_map(kit_input, "kit_components")
    rows = []
    for component in sorted(required_components):
        item = component_map.get(component, {})
        row = {
            "component": component,
            "present": item.get("present") is True,
            "artifact_hash": str(item.get("artifact_hash", "")),
            "runnable": item.get("runnable") is True,
            "offline_capable": item.get("offline_capable") is True,
            "docs_path": str(item.get("docs_path", "")),
            "verifier_command": str(item.get("verifier_command", "")),
            "required": True,
        }
        row["ready"] = (
            row["present"]
            and bool(row["artifact_hash"])
            and row["runnable"]
            and row["offline_capable"]
            and bool(row["docs_path"])
            and bool(row["verifier_command"])
        )
        row["kit_component_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _sdk_binding_rows(
    kit_input: dict[str, Any], required_bindings: list[str]
) -> list[dict[str, Any]]:
    binding_map = _component_input_map(kit_input, "sdk_binding_rows")
    rows = []
    for binding in sorted(required_bindings):
        item = binding_map.get(binding, {})
        row = {
            "binding": binding,
            "package_name": str(item.get("package_name", "")),
            "version": str(item.get("version", "")),
            "contract_hash": str(item.get("contract_hash", "")),
            "golden_fixture_hash": str(item.get("golden_fixture_hash", "")),
            "verifier_command": str(item.get("verifier_command", "")),
            "install_or_usage_path": str(item.get("install_or_usage_path", "")),
            "supports_fail_closed": item.get("supports_fail_closed") is True,
            "supports_footer_rendering": item.get("supports_footer_rendering") is True,
            "supports_content_credentials": item.get("supports_content_credentials")
            is True,
            "supports_gateway_middleware": item.get("supports_gateway_middleware")
            is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["package_name"])
            and bool(row["version"])
            and bool(row["contract_hash"])
            and bool(row["golden_fixture_hash"])
            and bool(row["verifier_command"])
            and bool(row["install_or_usage_path"])
            and row["supports_fail_closed"]
            and row["supports_footer_rendering"]
            and row["supports_content_credentials"]
            and row["supports_gateway_middleware"]
        )
        row["sdk_binding_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _execution_target_rows(
    kit_input: dict[str, Any], required_targets: list[str]
) -> list[dict[str, Any]]:
    target_map = _component_input_map(kit_input, "execution_target_rows")
    rows = []
    for target in sorted(required_targets):
        item = target_map.get(target, {})
        row = {
            "target": target,
            "runner_environment": str(item.get("runner_environment", "")),
            "command": str(item.get("command", "")),
            "artifact_hash": str(item.get("artifact_hash", "")),
            "replay_passed": item.get("replay_passed") is True,
            "negative_mutations_rejected": item.get("negative_mutations_rejected")
            is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["runner_environment"])
            and bool(row["command"])
            and bool(row["artifact_hash"])
            and row["replay_passed"]
            and row["negative_mutations_rejected"]
        )
        row["execution_target_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _provider_fixture_rows(
    kit_input: dict[str, Any], required_families: list[str]
) -> list[dict[str, Any]]:
    fixture_map = {
        str(row.get("provider_family", "")): row
        for row in kit_input.get("provider_fixture_rows", [])
        if isinstance(row, dict)
    }
    standard_rows = {
        str(row.get("provider_family", "")): row
        for row in kit_input.get("universal_adoption_standard", {}).get(
            "provider_family_rows", []
        )
        if isinstance(row, dict)
    }
    rows = []
    for family in sorted(required_families):
        item = fixture_map.get(family, {})
        standard_row = standard_rows.get(family, {})
        row = {
            "provider_family": family,
            "standard_provider_family_row_hash": str(
                standard_row.get("standard_provider_family_row_hash", "")
            ),
            "adapter_fixture_hash": str(item.get("adapter_fixture_hash", "")),
            "runtime_fixture_hash": str(item.get("runtime_fixture_hash", "")),
            "conformance_vector_hash": str(item.get("conformance_vector_hash", "")),
            "sample_request_hash": str(item.get("sample_request_hash", "")),
            "sample_response_hash": str(item.get("sample_response_hash", "")),
            "response_envelope_hash": str(item.get("response_envelope_hash", "")),
            "source_footer_delivery_hash": str(
                item.get("source_footer_delivery_hash", "")
            ),
            "invocation_guard_hash": str(item.get("invocation_guard_hash", "")),
            "negative_mutation_count": int(item.get("negative_mutation_count", 0) or 0),
            "streaming_fixture_present": item.get("streaming_fixture_present") is True,
            "tool_call_fixture_present": item.get("tool_call_fixture_present") is True,
            "citation_fixture_present": item.get("citation_fixture_present") is True,
            "status": str(item.get("status", "")),
            "required": True,
        }
        row["ready"] = (
            bool(row["standard_provider_family_row_hash"])
            and bool(row["adapter_fixture_hash"])
            and bool(row["runtime_fixture_hash"])
            and bool(row["conformance_vector_hash"])
            and bool(row["sample_request_hash"])
            and bool(row["sample_response_hash"])
            and bool(row["response_envelope_hash"])
            and bool(row["source_footer_delivery_hash"])
            and bool(row["invocation_guard_hash"])
            and row["negative_mutation_count"] > 0
            and row["streaming_fixture_present"]
            and row["tool_call_fixture_present"]
            and row["citation_fixture_present"]
            and row["status"] == "passed"
        )
        row["provider_fixture_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _failure_case_rows(
    kit_input: dict[str, Any], required_cases: list[str]
) -> list[dict[str, Any]]:
    case_map = _component_input_map(kit_input, "failure_case_rows")
    rows = []
    for case_id in sorted(required_cases):
        item = case_map.get(case_id, {})
        row = {
            "case_id": case_id,
            "fixture_hash": str(item.get("fixture_hash", "")),
            "verifier_command": str(item.get("verifier_command", "")),
            "expected_block": item.get("expected_block") is True,
            "observed_block": item.get("observed_block") is True,
            "required": True,
        }
        row["passed"] = (
            bool(row["fixture_hash"])
            and bool(row["verifier_command"])
            and row["expected_block"]
            and row["observed_block"]
        )
        row["failure_case_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _verifier_command_rows(
    kit_input: dict[str, Any], required_commands: list[str]
) -> list[dict[str, Any]]:
    integration = kit_input.get("integration_profile", {})
    declared = set(
        integration.get("verifier_contract", {}).get("reference_cli_commands", [])
    ) | {str(command) for command in kit_input.get("verifier_commands", [])}
    rows = []
    for command in sorted(required_commands):
        row = {
            "command": command,
            "declared": command in declared,
            "required": True,
        }
        row["verifier_command_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def make_universal_interop_test_kit(
    kit_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L139 universal RDLLM interoperability test kit."""

    created_at = created_at or now_iso()
    policy = _policy(kit_input)
    required_artifacts = [str(name) for name in policy["required_core_artifacts"]]
    required_families = [str(name) for name in policy["required_provider_families"]]
    required_components = [str(name) for name in policy["required_kit_components"]]
    required_bindings = [str(name) for name in policy["required_sdk_bindings"]]
    required_targets = [str(name) for name in policy["required_execution_targets"]]
    required_cases = [str(name) for name in policy["required_failure_cases"]]
    required_commands = [str(name) for name in policy["required_verifier_commands"]]

    adoption_standard = kit_input.get("universal_adoption_standard", {})
    certification = kit_input.get("certification_report", {})
    discovery = kit_input.get("discovery_manifest", {})
    integration = kit_input.get("integration_profile", {})

    artifact_bindings = _artifact_bindings(kit_input, required_artifacts)
    component_rows = _kit_component_rows(kit_input, required_components)
    sdk_rows = _sdk_binding_rows(kit_input, required_bindings)
    target_rows = _execution_target_rows(kit_input, required_targets)
    provider_rows = _provider_fixture_rows(kit_input, required_families)
    failure_rows = _failure_case_rows(kit_input, required_cases)
    command_rows = _verifier_command_rows(kit_input, required_commands)

    private_findings = _contains_private_fields(
        {
            "artifact_bindings": artifact_bindings,
            "kit_component_rows": component_rows,
            "sdk_binding_rows": sdk_rows,
            "execution_target_rows": target_rows,
            "provider_fixture_rows": provider_rows,
            "failure_case_rows": failure_rows,
            "verifier_command_rows": command_rows,
        }
    )
    discovery_path = discovery.get("discovery", {}).get(
        "universal_interop_test_kit_path"
    )

    checks = {
        "required_core_artifacts_present": all(
            row["present"] for row in artifact_bindings["bindings"]
        ),
        "artifact_hashes_reproducible": all(
            row["hash_reproducible"] for row in artifact_bindings["bindings"]
        ),
        "certification_level_at_least_l138": (
            _summary(certification).get("status") == "passed"
            and _level_at_least(_summary(certification).get("highest_level", ""), "RDLLM-L138")
        ),
        "adoption_standard_ready_l138": (
            _artifact_status(adoption_standard) == "ready"
            and _artifact_target_level(adoption_standard) == "RDLLM-L138"
            and _summary(adoption_standard).get("offline_verification_supported") is True
            and _summary(adoption_standard).get("privacy_preserved") is True
        ),
        "kit_components_complete": all(row["ready"] for row in component_rows),
        "sdk_bindings_complete": all(row["ready"] for row in sdk_rows),
        "execution_targets_complete": all(row["ready"] for row in target_rows),
        "provider_fixture_coverage_complete": all(row["ready"] for row in provider_rows),
        "negative_failure_cases_complete": all(row["passed"] for row in failure_rows),
        "public_verifier_commands_declared": all(
            row["declared"] for row in command_rows
        ),
        "discovery_manifest_exposes_kit_path": discovery_path == DEFAULT_WELL_KNOWN_PATH,
        "offline_verification_supported": (
            integration.get("verifier_contract", {}).get(
                "offline_verification_supported"
            )
            is True
            and _summary(adoption_standard).get("offline_verification_supported")
            is True
        ),
        "public_report_has_no_private_field_names": not private_findings,
    }
    checks["private_strings_absent"] = _private_strings_absent(
        {
            "artifact_bindings": artifact_bindings,
            "kit_component_rows": component_rows,
            "sdk_binding_rows": sdk_rows,
            "execution_target_rows": target_rows,
            "provider_fixture_rows": provider_rows,
            "failure_case_rows": failure_rows,
            "verifier_command_rows": command_rows,
        },
        kit_input,
    )

    failed_checks = [name for name, passed in checks.items() if passed is not True]
    failure_modes_by_check = {
        "required_core_artifacts_present": "required_interop_artifact_missing",
        "artifact_hashes_reproducible": "interop_artifact_hash_not_reproducible",
        "certification_level_at_least_l138": "certification_level_too_low",
        "adoption_standard_ready_l138": "adoption_standard_missing_or_blocked",
        "kit_components_complete": "interop_component_missing",
        "sdk_bindings_complete": "sdk_binding_missing_or_incomplete",
        "execution_targets_complete": "execution_target_not_replayable",
        "provider_fixture_coverage_complete": "provider_fixture_coverage_gap",
        "negative_failure_cases_complete": "negative_failure_case_not_blocked",
        "public_verifier_commands_declared": "interop_verifier_command_missing",
        "discovery_manifest_exposes_kit_path": "discovery_interop_path_missing",
        "offline_verification_supported": "offline_interop_verification_not_supported",
        "public_report_has_no_private_field_names": "private_field_name_leak",
        "private_strings_absent": "private_string_leak",
    }
    failure_modes = [failure_modes_by_check[name] for name in failed_checks]
    ready = not failed_checks

    commitments = {
        "artifact_binding_root": artifact_bindings["artifact_binding_root"],
        "kit_component_root": merkle_root(
            [row["kit_component_row_hash"] for row in component_rows]
        ),
        "sdk_binding_root": merkle_root(
            [row["sdk_binding_row_hash"] for row in sdk_rows]
        ),
        "execution_target_root": merkle_root(
            [row["execution_target_row_hash"] for row in target_rows]
        ),
        "provider_fixture_root": merkle_root(
            [row["provider_fixture_row_hash"] for row in provider_rows]
        ),
        "failure_case_root": merkle_root(
            [row["failure_case_row_hash"] for row in failure_rows]
        ),
        "verifier_command_root": merkle_root(
            [row["verifier_command_row_hash"] for row in command_rows]
        ),
        "universal_adoption_standard_hash": _declared_hash(adoption_standard),
        "certification_report_hash": _declared_hash(certification),
        "discovery_manifest_hash": _declared_hash(discovery),
    }
    commitments["interop_kit_commitment_hash"] = hash_payload(commitments)

    report: dict[str, Any] = {
        "interop_kit_version": UNIVERSAL_INTEROP_TEST_KIT_VERSION,
        "issuer": issuer,
        "created_at": created_at,
        "interop_policy": policy,
        "artifact_bindings": artifact_bindings,
        "kit_component_rows": component_rows,
        "sdk_binding_rows": sdk_rows,
        "execution_target_rows": target_rows,
        "provider_fixture_rows": provider_rows,
        "failure_case_rows": failure_rows,
        "verifier_command_rows": command_rows,
        "commitments": commitments,
        "checks": checks,
        "interop_decision": {
            "decision": "publish_universal_interop_test_kit"
            if ready
            else "block_universal_interop_test_kit",
            "publication_authorized": ready,
            "sdk_release_approved": ready,
            "procurement_approved": ready,
            "failed_checks": failed_checks,
            "failure_modes": failure_modes,
            "safe_output_policy": "publish_l139_test_kit_and_l138_standard"
            if ready
            else "block_interop_kit_publication",
        },
        "schemas": {
            "universal_interop_test_kit": UNIVERSAL_INTEROP_TEST_KIT_SCHEMA,
            "universal_adoption_standard": "docs/schemas/universal_adoption_standard.schema.json",
            "universal_rdllm_passport": "docs/schemas/universal_rdllm_passport.schema.json",
            "conformance_vector_pack": "docs/schemas/conformance_vector_pack.schema.json",
            "integration_profile": "docs/schemas/integration_profile.schema.json",
            "discovery_manifest": "docs/schemas/discovery_manifest.schema.json",
        },
        "privacy": {
            "raw_prompt_text_disclosed": False,
            "raw_output_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "private_payment_details_disclosed": False,
            "hash_only_interop_bindings": True,
            "private_field_findings": private_findings,
            "private_strings_absent": checks["private_strings_absent"],
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "provider_family_count": len(provider_rows),
            "kit_component_count": len(component_rows),
            "sdk_binding_count": len(sdk_rows),
            "execution_target_count": len(target_rows),
            "failure_case_count": len(failure_rows),
            "verifier_command_count": len(command_rows),
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
            "offline_verification_supported": checks[
                "offline_verification_supported"
            ],
            "privacy_preserved": not private_findings
            and checks["private_strings_absent"] is True,
            "universal_adoption_standard_hash": _declared_hash(adoption_standard),
            "interop_kit_commitment_hash": commitments[
                "interop_kit_commitment_hash"
            ],
        },
    }
    report["universal_interop_test_kit_hash"] = hash_payload(_hashable_report(report))
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "unsigned",
        "issuer": issuer,
        "value": sign_payload(_hashable_report(report), signing_secret)
        if signing_secret
        else "",
    }
    return report


def validate_universal_interop_test_kit_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "interop_kit_version",
        "issuer",
        "created_at",
        "interop_policy",
        "artifact_bindings",
        "kit_component_rows",
        "sdk_binding_rows",
        "execution_target_rows",
        "provider_fixture_rows",
        "failure_case_rows",
        "verifier_command_rows",
        "commitments",
        "checks",
        "interop_decision",
        "schemas",
        "privacy",
        "summary",
        "universal_interop_test_kit_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing universal interop test kit field: {key}")
    if errors:
        return errors
    if report.get("interop_kit_version") != UNIVERSAL_INTEROP_TEST_KIT_VERSION:
        errors.append("universal interop test kit version is unsupported")
    if (
        report.get("schemas", {}).get("universal_interop_test_kit")
        != UNIVERSAL_INTEROP_TEST_KIT_SCHEMA
    ):
        errors.append("universal interop test kit schema path is not declared")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal interop test kit target level is not RDLLM-L139")
    for finding in _contains_private_fields(report):
        errors.append(f"universal interop test kit contains private field: {finding}")
    return errors


def verify_universal_interop_test_kit(
    report: dict[str, Any],
    *,
    kit_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L139 universal interop test kit by replaying its inputs."""

    errors = validate_universal_interop_test_kit_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("universal_interop_test_kit_hash"):
        errors.append("universal interop test kit hash is not reproducible")

    expected = make_universal_interop_test_kit(
        kit_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "interop_policy",
        "artifact_bindings",
        "kit_component_rows",
        "sdk_binding_rows",
        "execution_target_rows",
        "provider_fixture_rows",
        "failure_case_rows",
        "verifier_command_rows",
        "commitments",
        "checks",
        "interop_decision",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"universal interop test kit {key} does not match replay")
    if expected.get("universal_interop_test_kit_hash") != report.get(
        "universal_interop_test_kit_hash"
    ):
        errors.append("universal interop test kit hash does not match replay")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("universal interop test kit status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal interop test kit check failed: {check}")

    if not _private_strings_absent(report, kit_input):
        errors.append("universal interop test kit leaks a private input string")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("universal interop test kit is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("universal interop test kit signature is invalid")

    return errors
