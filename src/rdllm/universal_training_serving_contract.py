"""Universal training-to-serving attribution contracts for foundation models.

The L143 layer closes a gap that remains after response-level citations and
grounded reuse are verified: foundation-model obligations can still be lost
between pretraining, fine-tuning, post-training, distillation, adapters, release
snapshots, provider routing, cache reuse, and final serving. This contract binds
those stages into one provider-neutral proof so training-time source rights,
attribution, and royalty obligations survive into every served answer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_TRAINING_SERVING_CONTRACT_VERSION = (
    "rdllm-universal-training-serving-contract/v1"
)
UNIVERSAL_TRAINING_SERVING_CONTRACT_SCHEMA = (
    "docs/schemas/universal_training_serving_contract.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L143"
MINIMUM_INPUT_LEVEL = "RDLLM-L142"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-training-serving-contract.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "universal_grounded_reuse_contract",
    "universal_citation_verification_contract",
    "training_content_summary",
    "training_memory_provenance",
    "post_training_signal_provenance",
    "model_lineage_attribution_report",
    "residual_corpus_royalty_report",
    "valuation_method_audit_report",
    "consent_revocation_propagation",
    "source_freshness_audit",
    "foundation_model_deployment_attestation",
    "foundation_runtime_router",
    "foundation_runtime_adapter",
    "foundation_provider_conformance",
    "composite_foundation_adapter",
    "foundation_api_profile",
    "provider_attribution_card",
    "integration_profile",
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
    "local_open_weights",
    "enterprise_gateway",
)

REQUIRED_TRAINING_STAGES = (
    "pretraining",
    "fine_tuning",
    "adapter_or_lora",
    "rlhf_rlaif_rlvr",
    "distillation",
    "synthetic_data_ingestion",
    "model_release",
    "runtime_serving",
    "grounded_reuse",
)

REQUIRED_CONTINUITY_DIMENSIONS = (
    "training_data_provenance",
    "post_training_signal_lineage",
    "distillation_and_synthetic_lineage",
    "adapter_delta_attribution",
    "model_release_binding",
    "runtime_provider_binding",
    "citation_and_reuse_continuity",
    "consent_revocation_continuity",
    "residual_royalty_conservation",
    "valuation_method_continuity",
    "provider_portability",
    "private_leakage",
)

REQUIRED_FAILURE_CASES = (
    "unbound_pretraining_corpus",
    "missing_post_training_signal_lineage",
    "synthetic_data_laundering",
    "distillation_lineage_gap",
    "adapter_delta_without_attribution",
    "deployment_model_hash_mismatch",
    "runtime_route_unbound_to_training_contract",
    "grounded_reuse_not_metered",
    "revoked_consent_not_propagated",
    "residual_royalty_not_conserved",
    "provider_family_missing",
    "private_training_text_leak",
)

REQUIRED_VERIFIER_COMMANDS = (
    "verify-universal-grounded-reuse-contract",
    "verify-universal-citation-verification-contract",
    "verify-training-memory-provenance",
    "verify-post-training-signal-provenance",
    "verify-model-lineage-attribution-report",
    "verify-residual-corpus-royalty-report",
    "verify-valuation-method-audit-report",
    "verify-consent-revocation-propagation",
    "verify-source-freshness-audit",
    "verify-foundation-model-deployment-attestation",
    "verify-foundation-runtime-router",
    "verify-foundation-runtime-adapter",
    "verify-foundation-provider-conformance",
    "verify-universal-training-serving-contract",
)

DECLARED_HASH_FIELDS = (
    "universal_training_serving_contract_hash",
    "universal_grounded_reuse_contract_hash",
    "universal_citation_verification_contract_hash",
    "training_memory_provenance_hash",
    "post_training_signal_provenance_hash",
    "model_lineage_attribution_report_hash",
    "residual_corpus_royalty_report_hash",
    "valuation_method_audit_hash",
    "consent_revocation_propagation_hash",
    "source_freshness_audit_hash",
    "foundation_model_deployment_attestation_hash",
    "foundation_runtime_router_hash",
    "foundation_runtime_adapter_hash",
    "foundation_provider_conformance_hash",
    "composite_foundation_adapter_hash",
    "universal_context_provenance_bridge_hash",
    "universal_interop_test_kit_hash",
    "universal_adoption_standard_hash",
    "universal_rdllm_passport_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "bundle_hash",
    "graph_hash",
    "trust_registry_hash",
    "report_hash",
    "summary_hash",
    "attestation_hash",
    "contract_hash",
    "package_hash",
    "envelope_hash",
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
    "raw_model_output",
    "raw_training_record",
    "training_text",
    "dataset_sample",
    "source_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "fine_tune_example",
    "reward_text",
    "preference_text",
    "critique_text",
    "distillation_output",
    "synthetic_record",
    "adapter_delta_raw",
    "cache_key",
    "customer_id",
    "customer_email",
    "access_token",
    "refresh_token",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_training_serving_contract_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L143 training-to-serving contract."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_training_serving_contract_hash", "signature"}
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


def _private_strings_absent(report: dict[str, Any], contract_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item) for item in contract_input.get("private_strings", []) if str(item).strip()
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


def _component_input_map(contract_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    value = contract_input.get(key, {})
    if isinstance(value, dict):
        return {str(name): row for name, row in value.items() if isinstance(row, dict)}
    if isinstance(value, list):
        result: dict[str, dict[str, Any]] = {}
        for row in value:
            if not isinstance(row, dict):
                continue
            name = (
                row.get("dimension")
                or row.get("provider_family")
                or row.get("training_stage")
                or row.get("stage")
                or row.get("case_id")
                or row.get("command")
            )
            if name:
                result[str(name)] = row
        return result
    return {}


def _obligation_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get("provider_family", "")), str(row.get("training_stage", "")))


def _policy(contract_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(contract_input.get("training_serving_policy", {}))
    return {
        "profile": "rdllm-universal-training-serving-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_provider_families": list(
            policy.get("required_provider_families", REQUIRED_PROVIDER_FAMILIES)
        ),
        "required_training_stages": list(
            policy.get("required_training_stages", REQUIRED_TRAINING_STAGES)
        ),
        "required_continuity_dimensions": list(
            policy.get(
                "required_continuity_dimensions", REQUIRED_CONTINUITY_DIMENSIONS
            )
        ),
        "required_failure_cases": list(
            policy.get("required_failure_cases", REQUIRED_FAILURE_CASES)
        ),
        "required_verifier_commands": list(
            policy.get("required_verifier_commands", REQUIRED_VERIFIER_COMMANDS)
        ),
        "on_unbound_training_stage": "block_release_and_route_to_training_replay",
        "on_unmetered_serving_use": "block_serving_and_settlement",
        "on_provider_family_gap": "block_provider_route",
        "on_revoked_consent_gap": "block_future_use_and_recompute_obligations",
        "on_private_text_leak": "block_publication",
    }


def _artifact_bindings(contract_input: dict[str, Any], names: list[str]) -> dict[str, Any]:
    rows = []
    for name in names:
        artifact = contract_input.get(name)
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


def _provider_family_rows(
    contract_input: dict[str, Any], required_families: list[str]
) -> list[dict[str, Any]]:
    family_map = _component_input_map(contract_input, "provider_family_rows")
    rows = []
    for family in sorted(required_families):
        item = family_map.get(family, {})
        row = {
            "provider_family": family,
            "training_adapter_hash": str(item.get("training_adapter_hash", "")),
            "serving_adapter_hash": str(item.get("serving_adapter_hash", "")),
            "runtime_route_schema_hash": str(item.get("runtime_route_schema_hash", "")),
            "obligation_schema_hash": str(item.get("obligation_schema_hash", "")),
            "public_verifier_command": str(item.get("public_verifier_command", "")),
            "supports_training_serving_attribution": (
                item.get("supports_training_serving_attribution") is True
            ),
            "supports_grounded_response_footer": (
                item.get("supports_grounded_response_footer") is True
            ),
            "supports_royalty_metering": item.get("supports_royalty_metering") is True,
            "fail_closed": item.get("fail_closed") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["training_adapter_hash"])
            and bool(row["serving_adapter_hash"])
            and bool(row["runtime_route_schema_hash"])
            and bool(row["obligation_schema_hash"])
            and row["public_verifier_command"]
            == "verify-universal-training-serving-contract"
            and row["supports_training_serving_attribution"]
            and row["supports_grounded_response_footer"]
            and row["supports_royalty_metering"]
            and row["fail_closed"]
        )
        row["provider_family_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _training_stage_rows(
    contract_input: dict[str, Any], required_stages: list[str]
) -> list[dict[str, Any]]:
    stage_map = _component_input_map(contract_input, "training_stage_rows")
    rows = []
    for stage in sorted(required_stages):
        item = stage_map.get(stage, {})
        row = {
            "training_stage": stage,
            "stage_manifest_hash": str(item.get("stage_manifest_hash", "")),
            "source_obligation_root": str(item.get("source_obligation_root", "")),
            "rights_state_root": str(item.get("rights_state_root", "")),
            "royalty_method_hash": str(item.get("royalty_method_hash", "")),
            "privacy_boundary_hash": str(item.get("privacy_boundary_hash", "")),
            "lineage_input_hash": str(item.get("lineage_input_hash", "")),
            "covered": item.get("covered") is True,
            "fail_closed": item.get("fail_closed") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["stage_manifest_hash"])
            and bool(row["source_obligation_root"])
            and bool(row["rights_state_root"])
            and bool(row["royalty_method_hash"])
            and bool(row["privacy_boundary_hash"])
            and bool(row["lineage_input_hash"])
            and row["covered"]
            and row["fail_closed"]
        )
        row["training_stage_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _continuity_dimension_rows(
    contract_input: dict[str, Any], required_dimensions: list[str]
) -> list[dict[str, Any]]:
    dimension_map = _component_input_map(contract_input, "continuity_dimension_rows")
    rows = []
    for dimension in sorted(required_dimensions):
        item = dimension_map.get(dimension, {})
        row = {
            "dimension": dimension,
            "evaluator_hash": str(item.get("evaluator_hash", "")),
            "proof_schema_hash": str(item.get("proof_schema_hash", "")),
            "calibration_hash": str(item.get("calibration_hash", "")),
            "fail_closed": item.get("fail_closed") is True,
            "covered": item.get("covered") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["evaluator_hash"])
            and bool(row["proof_schema_hash"])
            and bool(row["calibration_hash"])
            and row["fail_closed"]
            and row["covered"]
        )
        row["continuity_dimension_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _training_serving_obligation_rows(
    contract_input: dict[str, Any],
    required_families: list[str],
    required_stages: list[str],
) -> list[dict[str, Any]]:
    rows = []
    for item in sorted(
        contract_input.get("training_serving_obligation_rows", []),
        key=lambda row: (
            str(row.get("provider_family", "")),
            str(row.get("training_stage", "")),
        ),
    ):
        if not isinstance(item, dict):
            continue
        row = {
            "provider_family": str(item.get("provider_family", "")),
            "training_stage": str(item.get("training_stage", "")),
            "training_binding_hash": str(item.get("training_binding_hash", "")),
            "model_release_hash": str(item.get("model_release_hash", "")),
            "runtime_route_hash": str(item.get("runtime_route_hash", "")),
            "source_obligation_root": str(item.get("source_obligation_root", "")),
            "royalty_obligation_root": str(item.get("royalty_obligation_root", "")),
            "consent_state_root": str(item.get("consent_state_root", "")),
            "valuation_method_hash": str(item.get("valuation_method_hash", "")),
            "citation_contract_hash": str(item.get("citation_contract_hash", "")),
            "grounded_reuse_contract_hash": str(
                item.get("grounded_reuse_contract_hash", "")
            ),
            "serving_meter_hash": str(item.get("serving_meter_hash", "")),
            "footer_policy_hash": str(item.get("footer_policy_hash", "")),
            "training_source_bound": item.get("training_source_bound") is True,
            "runtime_route_bound": item.get("runtime_route_bound") is True,
            "serving_usage_metered": item.get("serving_usage_metered") is True,
            "citations_required_when_grounded": (
                item.get("citations_required_when_grounded") is True
            ),
            "footer_sources_required": item.get("footer_sources_required") is True,
            "royalty_carry_forward": item.get("royalty_carry_forward") is True,
            "revocation_propagates": item.get("revocation_propagates") is True,
            "residual_royalty_conserved": (
                item.get("residual_royalty_conserved") is True
            ),
            "synthetic_and_distillation_disclosed": (
                item.get("synthetic_and_distillation_disclosed") is True
            ),
            "adapter_delta_bound": item.get("adapter_delta_bound") is True,
            "fail_closed": item.get("fail_closed") is True,
        }
        row["required"] = (
            row["provider_family"] in required_families
            and row["training_stage"] in required_stages
        )
        row["ready"] = (
            row["required"]
            and bool(row["training_binding_hash"])
            and bool(row["model_release_hash"])
            and bool(row["runtime_route_hash"])
            and bool(row["source_obligation_root"])
            and bool(row["royalty_obligation_root"])
            and bool(row["consent_state_root"])
            and bool(row["valuation_method_hash"])
            and bool(row["citation_contract_hash"])
            and bool(row["grounded_reuse_contract_hash"])
            and bool(row["serving_meter_hash"])
            and bool(row["footer_policy_hash"])
            and row["training_source_bound"]
            and row["runtime_route_bound"]
            and row["serving_usage_metered"]
            and row["citations_required_when_grounded"]
            and row["footer_sources_required"]
            and row["royalty_carry_forward"]
            and row["revocation_propagates"]
            and row["residual_royalty_conserved"]
            and row["synthetic_and_distillation_disclosed"]
            and row["adapter_delta_bound"]
            and row["fail_closed"]
        )
        row["training_serving_obligation_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _failure_case_rows(
    contract_input: dict[str, Any], required_cases: list[str]
) -> list[dict[str, Any]]:
    case_map = _component_input_map(contract_input, "failure_case_rows")
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
            and row["verifier_command"]
            == "verify-universal-training-serving-contract"
            and row["expected_block"]
            and row["observed_block"]
        )
        row["failure_case_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _verifier_command_rows(
    contract_input: dict[str, Any], required_commands: list[str]
) -> list[dict[str, Any]]:
    declared = {str(command) for command in contract_input.get("verifier_commands", [])}
    integration = contract_input.get("integration_profile", {})
    declared |= set(
        integration.get("verifier_contract", {}).get("reference_cli_commands", [])
    )
    rows = []
    for command in sorted(required_commands):
        row = {"command": command, "declared": command in declared, "required": True}
        row["verifier_command_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def make_universal_training_serving_contract(
    contract_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L143 universal training-to-serving attribution contract."""

    created_at = created_at or now_iso()
    policy = _policy(contract_input)
    required_artifacts = [str(name) for name in policy["required_core_artifacts"]]
    required_families = [str(name) for name in policy["required_provider_families"]]
    required_stages = [str(name) for name in policy["required_training_stages"]]
    required_dimensions = [
        str(name) for name in policy["required_continuity_dimensions"]
    ]
    required_cases = [str(name) for name in policy["required_failure_cases"]]
    required_commands = [str(name) for name in policy["required_verifier_commands"]]

    grounded_reuse_contract = contract_input.get("universal_grounded_reuse_contract", {})
    citation_contract = contract_input.get("universal_citation_verification_contract", {})
    residual_report = contract_input.get("residual_corpus_royalty_report", {})
    valuation_report = contract_input.get("valuation_method_audit_report", {})
    discovery = contract_input.get("discovery_manifest", {})

    artifact_bindings = _artifact_bindings(contract_input, required_artifacts)
    provider_family_rows = _provider_family_rows(contract_input, required_families)
    training_stage_rows = _training_stage_rows(contract_input, required_stages)
    continuity_dimension_rows = _continuity_dimension_rows(
        contract_input, required_dimensions
    )
    obligation_rows = _training_serving_obligation_rows(
        contract_input, required_families, required_stages
    )
    failure_case_rows = _failure_case_rows(contract_input, required_cases)
    verifier_command_rows = _verifier_command_rows(contract_input, required_commands)

    required_matrix = {
        (provider_family, training_stage)
        for provider_family in required_families
        for training_stage in required_stages
    }
    observed_matrix = {_obligation_key(row) for row in obligation_rows}
    grounded_reuse_hash = _declared_hash(grounded_reuse_contract)
    citation_contract_hash = _declared_hash(citation_contract)
    residual_hash = _declared_hash(residual_report)
    valuation_hash = _declared_hash(valuation_report)
    discovery_path = discovery.get("discovery", {}).get(
        "universal_training_serving_contract_path"
    )

    public_projection = {
        "artifact_bindings": artifact_bindings,
        "provider_family_rows": provider_family_rows,
        "training_stage_rows": training_stage_rows,
        "continuity_dimension_rows": continuity_dimension_rows,
        "training_serving_obligation_rows": obligation_rows,
        "failure_case_rows": failure_case_rows,
        "verifier_command_rows": verifier_command_rows,
    }
    private_findings = _contains_private_fields(public_projection)

    checks = {
        "required_core_artifacts_present": all(
            row["present"] for row in artifact_bindings["bindings"]
        ),
        "artifact_hashes_reproducible": all(
            row["hash_reproducible"] for row in artifact_bindings["bindings"]
        ),
        "grounded_reuse_contract_ready_l142": (
            _artifact_status(grounded_reuse_contract) == "ready"
            and _artifact_target_level(grounded_reuse_contract) == MINIMUM_INPUT_LEVEL
            and _summary(grounded_reuse_contract).get("privacy_preserved") is True
        ),
        "provider_family_coverage_complete": all(
            row["ready"] for row in provider_family_rows
        ),
        "training_stage_coverage_complete": all(
            row["ready"] for row in training_stage_rows
        ),
        "continuity_dimensions_complete": all(
            row["ready"] for row in continuity_dimension_rows
        ),
        "training_serving_obligations_present": bool(obligation_rows),
        "training_serving_obligation_matrix_complete": (
            bool(required_matrix) and required_matrix <= observed_matrix
        ),
        "training_serving_obligations_ready": bool(obligation_rows)
        and all(row["ready"] for row in obligation_rows),
        "runtime_serving_events_metered": bool(obligation_rows)
        and all(
            row["serving_usage_metered"] and bool(row["serving_meter_hash"])
            for row in obligation_rows
        ),
        "citation_and_grounded_reuse_contracts_bound": bool(
            citation_contract_hash and grounded_reuse_hash
        )
        and all(
            row["citation_contract_hash"] == citation_contract_hash
            and row["grounded_reuse_contract_hash"] == grounded_reuse_hash
            for row in obligation_rows
        ),
        "training_serving_rights_continuity": all(
            row["revocation_propagates"] and bool(row["consent_state_root"])
            for row in obligation_rows
        ),
        "residual_royalty_and_valuation_bound": bool(residual_hash and valuation_hash)
        and all(
            row["residual_royalty_conserved"]
            and row["valuation_method_hash"] == valuation_hash
            for row in obligation_rows
        ),
        "failure_cases_fail_closed": all(row["passed"] for row in failure_case_rows),
        "public_verifier_commands_declared": all(
            row["declared"] for row in verifier_command_rows
        ),
        "discovery_manifest_exposes_contract_path": discovery_path
        in {"", None, DEFAULT_WELL_KNOWN_PATH},
        "public_report_has_no_private_field_names": not private_findings,
    }
    checks["private_strings_absent"] = _private_strings_absent(
        public_projection, contract_input
    )

    failed_checks = [name for name, passed in checks.items() if passed is not True]
    failure_modes_by_check = {
        "required_core_artifacts_present": "training_serving_artifact_missing",
        "artifact_hashes_reproducible": "training_serving_artifact_hash_not_reproducible",
        "grounded_reuse_contract_ready_l142": "grounded_reuse_contract_not_ready_l142",
        "provider_family_coverage_complete": "provider_family_training_serving_gap",
        "training_stage_coverage_complete": "training_stage_binding_gap",
        "continuity_dimensions_complete": "training_serving_continuity_dimension_gap",
        "training_serving_obligations_present": "serving_obligation_missing",
        "training_serving_obligation_matrix_complete": "training_serving_obligation_matrix_gap",
        "training_serving_obligations_ready": "training_serving_obligation_gate_failed",
        "runtime_serving_events_metered": "serving_obligation_metering_gap",
        "citation_and_grounded_reuse_contracts_bound": "citation_grounding_contract_continuity_gap",
        "training_serving_rights_continuity": "training_serving_rights_continuity_gap",
        "residual_royalty_and_valuation_bound": "residual_royalty_valuation_gap",
        "failure_cases_fail_closed": "training_serving_negative_case_not_blocked",
        "public_verifier_commands_declared": "training_serving_verifier_command_missing",
        "discovery_manifest_exposes_contract_path": "training_serving_contract_discovery_path_missing",
        "public_report_has_no_private_field_names": "private_field_name_leak",
        "private_strings_absent": "private_string_leak",
    }
    failure_modes = [failure_modes_by_check[name] for name in failed_checks]
    ready = not failed_checks

    commitments = {
        "artifact_binding_root": artifact_bindings["artifact_binding_root"],
        "provider_family_root": merkle_root(
            [row["provider_family_row_hash"] for row in provider_family_rows]
        ),
        "training_stage_root": merkle_root(
            [row["training_stage_row_hash"] for row in training_stage_rows]
        ),
        "continuity_dimension_root": merkle_root(
            [
                row["continuity_dimension_row_hash"]
                for row in continuity_dimension_rows
            ]
        ),
        "training_serving_obligation_root": merkle_root(
            [row["training_serving_obligation_row_hash"] for row in obligation_rows]
        ),
        "failure_case_root": merkle_root(
            [row["failure_case_row_hash"] for row in failure_case_rows]
        ),
        "verifier_command_root": merkle_root(
            [row["verifier_command_row_hash"] for row in verifier_command_rows]
        ),
        "universal_grounded_reuse_contract_hash": grounded_reuse_hash,
        "universal_citation_verification_contract_hash": citation_contract_hash,
        "residual_corpus_royalty_report_hash": residual_hash,
        "valuation_method_audit_hash": valuation_hash,
    }
    commitments["training_serving_commitment_hash"] = hash_payload(commitments)

    report: dict[str, Any] = {
        "training_serving_contract_version": (
            UNIVERSAL_TRAINING_SERVING_CONTRACT_VERSION
        ),
        "issuer": issuer,
        "created_at": created_at,
        "training_serving_policy": policy,
        "artifact_bindings": artifact_bindings,
        "provider_family_rows": provider_family_rows,
        "training_stage_rows": training_stage_rows,
        "continuity_dimension_rows": continuity_dimension_rows,
        "training_serving_obligation_rows": obligation_rows,
        "failure_case_rows": failure_case_rows,
        "verifier_command_rows": verifier_command_rows,
        "commitments": commitments,
        "checks": checks,
        "contract_decision": {
            "decision": "publish_universal_training_serving_contract"
            if ready
            else "block_universal_training_serving_contract",
            "publication_authorized": ready,
            "serving_attribution_approved": ready,
            "training_royalty_carry_forward_approved": ready,
            "failed_checks": failed_checks,
            "failure_modes": failure_modes,
            "safe_output_policy": "serve_only_when_training_stage_rights_citation_grounding_reuse_and_royalty_obligations_are_bound"
            if ready
            else "block_training_serving_attribution_claim",
        },
        "schemas": {
            "universal_training_serving_contract": (
                UNIVERSAL_TRAINING_SERVING_CONTRACT_SCHEMA
            ),
            "universal_grounded_reuse_contract": (
                "docs/schemas/universal_grounded_reuse_contract.schema.json"
            ),
            "universal_citation_verification_contract": (
                "docs/schemas/universal_citation_verification_contract.schema.json"
            ),
            "training_content_summary": (
                "docs/schemas/training_content_summary.schema.json"
            ),
            "post_training_signal_provenance": (
                "docs/schemas/post_training_signal_provenance.schema.json"
            ),
            "model_lineage_attribution_report": (
                "docs/schemas/model_lineage_attribution_report.schema.json"
            ),
        },
        "privacy": {
            "raw_training_text_disclosed": False,
            "raw_prompt_text_disclosed": False,
            "raw_answer_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_reward_or_preference_text_disclosed": False,
            "hash_only_training_serving_bindings": True,
            "private_field_findings": private_findings,
            "private_strings_absent": checks["private_strings_absent"],
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "provider_family_count": len(provider_family_rows),
            "training_stage_count": len(training_stage_rows),
            "continuity_dimension_count": len(continuity_dimension_rows),
            "training_serving_obligation_count": len(obligation_rows),
            "required_obligation_count": len(required_matrix),
            "failure_case_count": len(failure_case_rows),
            "verifier_command_count": len(verifier_command_rows),
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": not private_findings
            and checks["private_strings_absent"] is True,
            "universal_grounded_reuse_contract_hash": grounded_reuse_hash,
            "universal_citation_verification_contract_hash": citation_contract_hash,
            "training_serving_commitment_hash": commitments[
                "training_serving_commitment_hash"
            ],
        },
    }
    report["universal_training_serving_contract_hash"] = hash_payload(
        _hashable_report(report)
    )
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "unsigned",
        "issuer": issuer,
        "value": sign_payload(_hashable_report(report), signing_secret)
        if signing_secret
        else "",
    }
    return report


def validate_universal_training_serving_contract_shape(
    report: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = (
        "training_serving_contract_version",
        "issuer",
        "created_at",
        "training_serving_policy",
        "artifact_bindings",
        "provider_family_rows",
        "training_stage_rows",
        "continuity_dimension_rows",
        "training_serving_obligation_rows",
        "failure_case_rows",
        "verifier_command_rows",
        "commitments",
        "checks",
        "contract_decision",
        "schemas",
        "privacy",
        "summary",
        "universal_training_serving_contract_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing universal training-serving field: {key}")
    if errors:
        return errors
    if (
        report.get("training_serving_contract_version")
        != UNIVERSAL_TRAINING_SERVING_CONTRACT_VERSION
    ):
        errors.append("universal training-serving contract version is unsupported")
    if (
        report.get("schemas", {}).get("universal_training_serving_contract")
        != UNIVERSAL_TRAINING_SERVING_CONTRACT_SCHEMA
    ):
        errors.append("universal training-serving contract schema path is not declared")
    if (
        report.get("summary", {}).get("target_certification_level")
        != TARGET_CERTIFICATION_LEVEL
    ):
        errors.append("universal training-serving contract target level is not RDLLM-L143")
    for finding in _contains_private_fields(report):
        errors.append(f"universal training-serving contract contains private field: {finding}")
    return errors


def verify_universal_training_serving_contract(
    report: dict[str, Any],
    *,
    contract_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L143 universal training-to-serving contract by replaying inputs."""

    errors = validate_universal_training_serving_contract_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("universal_training_serving_contract_hash"):
        errors.append("universal training-serving contract hash is not reproducible")

    expected = make_universal_training_serving_contract(
        contract_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "training_serving_policy",
        "artifact_bindings",
        "provider_family_rows",
        "training_stage_rows",
        "continuity_dimension_rows",
        "training_serving_obligation_rows",
        "failure_case_rows",
        "verifier_command_rows",
        "commitments",
        "checks",
        "contract_decision",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"universal training-serving contract {key} does not match replay")
    if expected.get("universal_training_serving_contract_hash") != report.get(
        "universal_training_serving_contract_hash"
    ):
        errors.append("universal training-serving contract hash does not match replay")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("universal training-serving contract status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal training-serving contract check failed: {check}")

    if not _private_strings_absent(report, contract_input):
        errors.append("universal training-serving contract leaks a private input string")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("universal training-serving contract is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("universal training-serving contract signature is invalid")

    return errors
