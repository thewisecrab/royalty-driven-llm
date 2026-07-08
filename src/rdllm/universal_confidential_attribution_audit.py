"""Confidential attribution audit contracts for universal RDLLM deployments.

The L144 layer makes L143 independently trustworthy without forcing providers to
publish private corpora, reward data, model internals, prompts, or customer logs.
It binds confidential evidence rooms, ZK/TEE/selective-disclosure proof handles,
auditor quorum, creator challenge routes, regulator export policies, and
fail-closed negative fixtures to the public training-to-serving attribution
contract.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_CONFIDENTIAL_ATTRIBUTION_AUDIT_VERSION = (
    "rdllm-universal-confidential-attribution-audit/v1"
)
UNIVERSAL_CONFIDENTIAL_ATTRIBUTION_AUDIT_SCHEMA = (
    "docs/schemas/universal_confidential_attribution_audit.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L144"
MINIMUM_INPUT_LEVEL = "RDLLM-L143"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-confidential-attribution-audit.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "universal_training_serving_contract",
    "universal_grounded_reuse_contract",
    "universal_citation_verification_contract",
    "certification_report",
    "certification_attestation",
    "provider_attribution_card",
    "integration_profile",
    "training_content_summary",
    "training_memory_provenance",
    "post_training_signal_provenance",
    "residual_corpus_royalty_report",
    "valuation_method_audit_report",
    "foundation_model_deployment_attestation",
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

REQUIRED_AUDIT_DOMAINS = (
    "training_corpus_membership",
    "license_and_consent_state",
    "post_training_signal_lineage",
    "distillation_and_synthetic_lineage",
    "model_release_integrity",
    "runtime_serving_metering",
    "citation_grounding_replay",
    "residual_royalty_valuation",
    "revocation_and_unlearning_propagation",
    "creator_query_response",
)

REQUIRED_PROOF_MECHANISMS = (
    "zero_knowledge_dataset_membership",
    "tee_remote_attestation",
    "selective_disclosure_commitment",
    "encrypted_evidence_escrow",
    "auditor_quorum_challenge",
    "differential_privacy_budget",
    "secure_aggregate_settlement",
)

REQUIRED_STAKEHOLDER_ROLES = (
    "provider",
    "foundation_model_provider",
    "independent_auditor",
    "creator",
    "collective_rights_organization",
    "regulator",
    "enterprise_customer",
    "model_gateway",
)

REQUIRED_FAILURE_CASES = (
    "invalid_zk_proof",
    "stale_tee_quote",
    "auditor_quorum_missing",
    "private_field_leak",
    "missing_creator_challenge_route",
    "unbound_training_dataset_commitment",
    "revoked_source_still_included",
    "unmetered_serving_log",
    "valuation_input_unopened",
    "proof_room_split_view",
    "unsupported_provider_family",
    "denied_regulator_export",
)

REQUIRED_VERIFIER_COMMANDS = (
    "verify-universal-training-serving-contract",
    "verify-certification-attestation",
    "verify-trust-registry",
    "verify-provider-card",
    "verify-integration-profile",
    "verify-training-memory-provenance",
    "verify-post-training-signal-provenance",
    "verify-residual-corpus-royalty-report",
    "verify-valuation-method-audit-report",
    "verify-foundation-model-deployment-attestation",
    "verify-universal-confidential-attribution-audit",
)

DECLARED_HASH_FIELDS = (
    "universal_confidential_attribution_audit_hash",
    "universal_training_serving_contract_hash",
    "universal_grounded_reuse_contract_hash",
    "universal_citation_verification_contract_hash",
    "certification_report_hash",
    "report_hash",
    "attestation_hash",
    "card_hash",
    "profile_hash",
    "training_memory_provenance_hash",
    "post_training_signal_provenance_hash",
    "residual_corpus_royalty_report_hash",
    "valuation_method_audit_hash",
    "foundation_model_deployment_attestation_hash",
    "trust_registry_hash",
    "summary_hash",
    "contract_hash",
    "envelope_hash",
    "bundle_hash",
    "graph_hash",
    "manifest_hash",
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
    "reward_text",
    "preference_text",
    "critique_text",
    "distillation_output",
    "synthetic_record",
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
    "access_token",
    "refresh_token",
    "secret",
    "signing_secret",
    "private_key",
}


def load_universal_confidential_attribution_audit_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L144 confidential attribution audit."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_confidential_attribution_audit_hash", "signature"}
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


def _private_strings_absent(report: dict[str, Any], audit_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item) for item in audit_input.get("private_strings", []) if str(item).strip()
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


def _component_input_map(audit_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    value = audit_input.get(key, {})
    if isinstance(value, dict):
        return {str(name): row for name, row in value.items() if isinstance(row, dict)}
    if isinstance(value, list):
        result: dict[str, dict[str, Any]] = {}
        for row in value:
            if not isinstance(row, dict):
                continue
            name = (
                row.get("audit_domain")
                or row.get("domain")
                or row.get("provider_family")
                or row.get("proof_mechanism")
                or row.get("mechanism")
                or row.get("role")
                or row.get("case_id")
                or row.get("command")
            )
            if name:
                result[str(name)] = row
        return result
    return {}


def _obligation_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get("provider_family", "")), str(row.get("audit_domain", "")))


def _policy(audit_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(audit_input.get("confidential_audit_policy", {}))
    return {
        "profile": "rdllm-universal-confidential-attribution-audit-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_provider_families": list(
            policy.get("required_provider_families", REQUIRED_PROVIDER_FAMILIES)
        ),
        "required_audit_domains": list(
            policy.get("required_audit_domains", REQUIRED_AUDIT_DOMAINS)
        ),
        "required_proof_mechanisms": list(
            policy.get("required_proof_mechanisms", REQUIRED_PROOF_MECHANISMS)
        ),
        "required_stakeholder_roles": list(
            policy.get("required_stakeholder_roles", REQUIRED_STAKEHOLDER_ROLES)
        ),
        "required_failure_cases": list(
            policy.get("required_failure_cases", REQUIRED_FAILURE_CASES)
        ),
        "required_verifier_commands": list(
            policy.get("required_verifier_commands", REQUIRED_VERIFIER_COMMANDS)
        ),
        "on_invalid_private_proof": "block_attribution_claim_and_open_audit_challenge",
        "on_missing_auditor_quorum": "preserve_escrow_and_block_public_assurance",
        "on_creator_challenge_gap": "block_direct_settlement",
        "on_regulator_export_gap": "block_foundation_model_conformance_claim",
        "on_private_text_leak": "block_publication",
    }


def _artifact_bindings(audit_input: dict[str, Any], names: list[str]) -> dict[str, Any]:
    rows = []
    for name in names:
        artifact = audit_input.get(name)
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
    audit_input: dict[str, Any], required_families: list[str]
) -> list[dict[str, Any]]:
    family_map = _component_input_map(audit_input, "provider_family_rows")
    rows = []
    for family in sorted(required_families):
        item = family_map.get(family, {})
        row = {
            "provider_family": family,
            "proof_room_endpoint_hash": str(item.get("proof_room_endpoint_hash", "")),
            "verifier_policy_hash": str(item.get("verifier_policy_hash", "")),
            "attestation_root": str(item.get("attestation_root", "")),
            "challenge_api_hash": str(item.get("challenge_api_hash", "")),
            "public_verifier_command": str(item.get("public_verifier_command", "")),
            "supports_confidential_audit": item.get("supports_confidential_audit") is True,
            "supports_creator_challenges": item.get("supports_creator_challenges") is True,
            "supports_regulator_export": item.get("supports_regulator_export") is True,
            "fail_closed": item.get("fail_closed") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["proof_room_endpoint_hash"])
            and bool(row["verifier_policy_hash"])
            and bool(row["attestation_root"])
            and bool(row["challenge_api_hash"])
            and row["public_verifier_command"]
            == "verify-universal-confidential-attribution-audit"
            and row["supports_confidential_audit"]
            and row["supports_creator_challenges"]
            and row["supports_regulator_export"]
            and row["fail_closed"]
        )
        row["provider_family_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _audit_domain_rows(
    audit_input: dict[str, Any], required_domains: list[str]
) -> list[dict[str, Any]]:
    domain_map = _component_input_map(audit_input, "audit_domain_rows")
    rows = []
    for domain in sorted(required_domains):
        item = domain_map.get(domain, {})
        row = {
            "audit_domain": domain,
            "private_evidence_commitment": str(item.get("private_evidence_commitment", "")),
            "public_claim_hash": str(item.get("public_claim_hash", "")),
            "opening_policy_hash": str(item.get("opening_policy_hash", "")),
            "verifier_hash": str(item.get("verifier_hash", "")),
            "proof_mechanism_root": str(item.get("proof_mechanism_root", "")),
            "retention_policy_hash": str(item.get("retention_policy_hash", "")),
            "covered": item.get("covered") is True,
            "fail_closed": item.get("fail_closed") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["private_evidence_commitment"])
            and bool(row["public_claim_hash"])
            and bool(row["opening_policy_hash"])
            and bool(row["verifier_hash"])
            and bool(row["proof_mechanism_root"])
            and bool(row["retention_policy_hash"])
            and row["covered"]
            and row["fail_closed"]
        )
        row["audit_domain_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _proof_mechanism_rows(
    audit_input: dict[str, Any], required_mechanisms: list[str]
) -> list[dict[str, Any]]:
    mechanism_map = _component_input_map(audit_input, "proof_mechanism_rows")
    rows = []
    for mechanism in sorted(required_mechanisms):
        item = mechanism_map.get(mechanism, {})
        row = {
            "proof_mechanism": mechanism,
            "verifier_hash": str(item.get("verifier_hash", "")),
            "public_parameters_hash": str(item.get("public_parameters_hash", "")),
            "soundness_profile_hash": str(item.get("soundness_profile_hash", "")),
            "privacy_profile_hash": str(item.get("privacy_profile_hash", "")),
            "replay_fixture_hash": str(item.get("replay_fixture_hash", "")),
            "covered": item.get("covered") is True,
            "fail_closed": item.get("fail_closed") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["verifier_hash"])
            and bool(row["public_parameters_hash"])
            and bool(row["soundness_profile_hash"])
            and bool(row["privacy_profile_hash"])
            and bool(row["replay_fixture_hash"])
            and row["covered"]
            and row["fail_closed"]
        )
        row["proof_mechanism_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _stakeholder_access_rows(
    audit_input: dict[str, Any], required_roles: list[str]
) -> list[dict[str, Any]]:
    role_map = _component_input_map(audit_input, "stakeholder_access_rows")
    rows = []
    for role in sorted(required_roles):
        item = role_map.get(role, {})
        row = {
            "role": role,
            "access_policy_hash": str(item.get("access_policy_hash", "")),
            "disclosure_profile_hash": str(item.get("disclosure_profile_hash", "")),
            "challenge_endpoint_hash": str(item.get("challenge_endpoint_hash", "")),
            "audit_log_commitment": str(item.get("audit_log_commitment", "")),
            "revocation_channel_hash": str(item.get("revocation_channel_hash", "")),
            "authorized": item.get("authorized") is True,
            "fail_closed": item.get("fail_closed") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["access_policy_hash"])
            and bool(row["disclosure_profile_hash"])
            and bool(row["challenge_endpoint_hash"])
            and bool(row["audit_log_commitment"])
            and bool(row["revocation_channel_hash"])
            and row["authorized"]
            and row["fail_closed"]
        )
        row["stakeholder_access_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _confidential_audit_obligation_rows(
    audit_input: dict[str, Any],
    required_families: list[str],
    required_domains: list[str],
) -> list[dict[str, Any]]:
    rows = []
    for item in sorted(
        audit_input.get("confidential_audit_obligation_rows", []),
        key=lambda row: (
            str(row.get("provider_family", "")),
            str(row.get("audit_domain", "")),
        ),
    ):
        if not isinstance(item, dict):
            continue
        row = {
            "provider_family": str(item.get("provider_family", "")),
            "audit_domain": str(item.get("audit_domain", "")),
            "evidence_room_hash": str(item.get("evidence_room_hash", "")),
            "commitment_root": str(item.get("commitment_root", "")),
            "proof_artifact_hash": str(item.get("proof_artifact_hash", "")),
            "auditor_quorum_hash": str(item.get("auditor_quorum_hash", "")),
            "challenge_window_hash": str(item.get("challenge_window_hash", "")),
            "decision_log_hash": str(item.get("decision_log_hash", "")),
            "private_data_boundary_hash": str(item.get("private_data_boundary_hash", "")),
            "disclosure_policy_hash": str(item.get("disclosure_policy_hash", "")),
            "no_raw_data_disclosed": item.get("no_raw_data_disclosed") is True,
            "proof_verified": item.get("proof_verified") is True,
            "auditor_quorum_satisfied": item.get("auditor_quorum_satisfied") is True,
            "creator_challenge_supported": item.get("creator_challenge_supported") is True,
            "regulator_export_supported": item.get("regulator_export_supported") is True,
            "differential_privacy_budget_bound": (
                item.get("differential_privacy_budget_bound") is True
            ),
            "fail_closed": item.get("fail_closed") is True,
        }
        row["required"] = (
            row["provider_family"] in required_families
            and row["audit_domain"] in required_domains
        )
        row["ready"] = (
            row["required"]
            and bool(row["evidence_room_hash"])
            and bool(row["commitment_root"])
            and bool(row["proof_artifact_hash"])
            and bool(row["auditor_quorum_hash"])
            and bool(row["challenge_window_hash"])
            and bool(row["decision_log_hash"])
            and bool(row["private_data_boundary_hash"])
            and bool(row["disclosure_policy_hash"])
            and row["no_raw_data_disclosed"]
            and row["proof_verified"]
            and row["auditor_quorum_satisfied"]
            and row["creator_challenge_supported"]
            and row["regulator_export_supported"]
            and row["differential_privacy_budget_bound"]
            and row["fail_closed"]
        )
        row["confidential_audit_obligation_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _failure_case_rows(
    audit_input: dict[str, Any], required_cases: list[str]
) -> list[dict[str, Any]]:
    case_map = _component_input_map(audit_input, "failure_case_rows")
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
            == "verify-universal-confidential-attribution-audit"
            and row["expected_block"]
            and row["observed_block"]
        )
        row["failure_case_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _verifier_command_rows(
    audit_input: dict[str, Any], required_commands: list[str]
) -> list[dict[str, Any]]:
    declared = {str(command) for command in audit_input.get("verifier_commands", [])}
    integration = audit_input.get("integration_profile", {})
    declared |= set(
        integration.get("verifier_contract", {}).get("reference_cli_commands", [])
    )
    rows = []
    for command in sorted(required_commands):
        row = {"command": command, "declared": command in declared, "required": True}
        row["verifier_command_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def make_universal_confidential_attribution_audit(
    audit_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L144 universal confidential attribution audit contract."""

    created_at = created_at or now_iso()
    policy = _policy(audit_input)
    required_artifacts = [str(name) for name in policy["required_core_artifacts"]]
    required_families = [str(name) for name in policy["required_provider_families"]]
    required_domains = [str(name) for name in policy["required_audit_domains"]]
    required_mechanisms = [str(name) for name in policy["required_proof_mechanisms"]]
    required_roles = [str(name) for name in policy["required_stakeholder_roles"]]
    required_cases = [str(name) for name in policy["required_failure_cases"]]
    required_commands = [str(name) for name in policy["required_verifier_commands"]]

    training_serving_contract = audit_input.get("universal_training_serving_contract", {})
    discovery = audit_input.get("discovery_manifest", {})

    artifact_bindings = _artifact_bindings(audit_input, required_artifacts)
    provider_family_rows = _provider_family_rows(audit_input, required_families)
    audit_domain_rows = _audit_domain_rows(audit_input, required_domains)
    proof_mechanism_rows = _proof_mechanism_rows(audit_input, required_mechanisms)
    stakeholder_access_rows = _stakeholder_access_rows(audit_input, required_roles)
    obligation_rows = _confidential_audit_obligation_rows(
        audit_input, required_families, required_domains
    )
    failure_case_rows = _failure_case_rows(audit_input, required_cases)
    verifier_command_rows = _verifier_command_rows(audit_input, required_commands)

    required_matrix = {
        (provider_family, domain)
        for provider_family in required_families
        for domain in required_domains
    }
    observed_matrix = {_obligation_key(row) for row in obligation_rows}
    discovery_path = discovery.get("discovery", {}).get(
        "universal_confidential_attribution_audit_path"
    )

    public_projection = {
        "artifact_bindings": artifact_bindings,
        "provider_family_rows": provider_family_rows,
        "audit_domain_rows": audit_domain_rows,
        "proof_mechanism_rows": proof_mechanism_rows,
        "stakeholder_access_rows": stakeholder_access_rows,
        "confidential_audit_obligation_rows": obligation_rows,
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
        "training_serving_contract_ready_l143": (
            _artifact_status(training_serving_contract) == "ready"
            and _artifact_target_level(training_serving_contract) == MINIMUM_INPUT_LEVEL
            and _summary(training_serving_contract).get("privacy_preserved") is True
        ),
        "provider_family_coverage_complete": all(
            row["ready"] for row in provider_family_rows
        ),
        "audit_domain_coverage_complete": all(row["ready"] for row in audit_domain_rows),
        "proof_mechanisms_complete": all(row["ready"] for row in proof_mechanism_rows),
        "stakeholder_access_complete": all(
            row["ready"] for row in stakeholder_access_rows
        ),
        "confidential_audit_obligations_present": bool(obligation_rows),
        "confidential_audit_obligation_matrix_complete": (
            bool(required_matrix) and required_matrix <= observed_matrix
        ),
        "confidential_audit_obligations_ready": bool(obligation_rows)
        and all(row["ready"] for row in obligation_rows),
        "private_evidence_not_publicly_disclosed": bool(obligation_rows)
        and all(row["no_raw_data_disclosed"] for row in obligation_rows),
        "auditor_quorum_and_challenge_paths_bound": bool(obligation_rows)
        and all(
            row["auditor_quorum_satisfied"]
            and row["creator_challenge_supported"]
            and row["regulator_export_supported"]
            for row in obligation_rows
        ),
        "differential_privacy_budget_bound": bool(obligation_rows)
        and all(row["differential_privacy_budget_bound"] for row in obligation_rows),
        "failure_cases_fail_closed": all(row["passed"] for row in failure_case_rows),
        "public_verifier_commands_declared": all(
            row["declared"] for row in verifier_command_rows
        ),
        "discovery_manifest_exposes_contract_path": discovery_path
        in {"", None, DEFAULT_WELL_KNOWN_PATH},
        "public_report_has_no_private_field_names": not private_findings,
    }
    checks["private_strings_absent"] = _private_strings_absent(
        public_projection, audit_input
    )

    failed_checks = [name for name, passed in checks.items() if passed is not True]
    failure_modes_by_check = {
        "required_core_artifacts_present": "confidential_audit_artifact_missing",
        "artifact_hashes_reproducible": "confidential_audit_artifact_hash_not_reproducible",
        "training_serving_contract_ready_l143": "training_serving_contract_not_ready_l143",
        "provider_family_coverage_complete": "confidential_audit_provider_family_gap",
        "audit_domain_coverage_complete": "confidential_audit_domain_gap",
        "proof_mechanisms_complete": "confidential_audit_proof_mechanism_gap",
        "stakeholder_access_complete": "confidential_audit_stakeholder_access_gap",
        "confidential_audit_obligations_present": "confidential_audit_obligation_missing",
        "confidential_audit_obligation_matrix_complete": "confidential_audit_obligation_matrix_gap",
        "confidential_audit_obligations_ready": "confidential_audit_obligation_gate_failed",
        "private_evidence_not_publicly_disclosed": "confidential_audit_private_evidence_leak",
        "auditor_quorum_and_challenge_paths_bound": "confidential_audit_quorum_or_challenge_gap",
        "differential_privacy_budget_bound": "confidential_audit_privacy_budget_gap",
        "failure_cases_fail_closed": "confidential_audit_negative_case_not_blocked",
        "public_verifier_commands_declared": "confidential_audit_verifier_command_missing",
        "discovery_manifest_exposes_contract_path": "confidential_audit_discovery_path_missing",
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
        "audit_domain_root": merkle_root(
            [row["audit_domain_row_hash"] for row in audit_domain_rows]
        ),
        "proof_mechanism_root": merkle_root(
            [row["proof_mechanism_row_hash"] for row in proof_mechanism_rows]
        ),
        "stakeholder_access_root": merkle_root(
            [row["stakeholder_access_row_hash"] for row in stakeholder_access_rows]
        ),
        "confidential_audit_obligation_root": merkle_root(
            [
                row["confidential_audit_obligation_row_hash"]
                for row in obligation_rows
            ]
        ),
        "failure_case_root": merkle_root(
            [row["failure_case_row_hash"] for row in failure_case_rows]
        ),
        "verifier_command_root": merkle_root(
            [row["verifier_command_row_hash"] for row in verifier_command_rows]
        ),
        "universal_training_serving_contract_hash": _declared_hash(
            training_serving_contract
        ),
    }
    commitments["confidential_audit_commitment_hash"] = hash_payload(commitments)

    report: dict[str, Any] = {
        "confidential_audit_version": UNIVERSAL_CONFIDENTIAL_ATTRIBUTION_AUDIT_VERSION,
        "issuer": issuer,
        "created_at": created_at,
        "confidential_audit_policy": policy,
        "artifact_bindings": artifact_bindings,
        "provider_family_rows": provider_family_rows,
        "audit_domain_rows": audit_domain_rows,
        "proof_mechanism_rows": proof_mechanism_rows,
        "stakeholder_access_rows": stakeholder_access_rows,
        "confidential_audit_obligation_rows": obligation_rows,
        "failure_case_rows": failure_case_rows,
        "verifier_command_rows": verifier_command_rows,
        "commitments": commitments,
        "checks": checks,
        "audit_decision": {
            "decision": "publish_universal_confidential_attribution_audit"
            if ready
            else "block_universal_confidential_attribution_audit",
            "publication_authorized": ready,
            "confidential_audit_approved": ready,
            "direct_settlement_confidentially_auditable": ready,
            "failed_checks": failed_checks,
            "failure_modes": failure_modes,
            "safe_output_policy": "serve_attributed_answers_only_when_l143_claims_have_confidential_private_evidence_proofs_quorum_and_challenge_paths"
            if ready
            else "block_confidential_attribution_assurance",
        },
        "schemas": {
            "universal_confidential_attribution_audit": (
                UNIVERSAL_CONFIDENTIAL_ATTRIBUTION_AUDIT_SCHEMA
            ),
            "universal_training_serving_contract": (
                "docs/schemas/universal_training_serving_contract.schema.json"
            ),
            "certification_attestation": (
                "docs/schemas/certification_attestation.schema.json"
            ),
            "trust_registry": "docs/schemas/trust_registry.schema.json",
        },
        "privacy": {
            "raw_training_text_disclosed": False,
            "raw_prompt_text_disclosed": False,
            "raw_answer_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_reward_or_preference_text_disclosed": False,
            "model_weights_or_hidden_states_disclosed": False,
            "customer_or_billing_logs_disclosed": False,
            "hash_only_confidential_audit_bindings": True,
            "private_field_findings": private_findings,
            "private_strings_absent": checks["private_strings_absent"],
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "provider_family_count": len(provider_family_rows),
            "audit_domain_count": len(audit_domain_rows),
            "proof_mechanism_count": len(proof_mechanism_rows),
            "stakeholder_role_count": len(stakeholder_access_rows),
            "confidential_audit_obligation_count": len(obligation_rows),
            "required_obligation_count": len(required_matrix),
            "failure_case_count": len(failure_case_rows),
            "verifier_command_count": len(verifier_command_rows),
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": not private_findings
            and checks["private_strings_absent"] is True,
            "universal_training_serving_contract_hash": _declared_hash(
                training_serving_contract
            ),
            "confidential_audit_commitment_hash": commitments[
                "confidential_audit_commitment_hash"
            ],
        },
    }
    report["universal_confidential_attribution_audit_hash"] = hash_payload(
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


def validate_universal_confidential_attribution_audit_shape(
    report: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = (
        "confidential_audit_version",
        "issuer",
        "created_at",
        "confidential_audit_policy",
        "artifact_bindings",
        "provider_family_rows",
        "audit_domain_rows",
        "proof_mechanism_rows",
        "stakeholder_access_rows",
        "confidential_audit_obligation_rows",
        "failure_case_rows",
        "verifier_command_rows",
        "commitments",
        "checks",
        "audit_decision",
        "schemas",
        "privacy",
        "summary",
        "universal_confidential_attribution_audit_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing universal confidential audit field: {key}")
    if errors:
        return errors
    if (
        report.get("confidential_audit_version")
        != UNIVERSAL_CONFIDENTIAL_ATTRIBUTION_AUDIT_VERSION
    ):
        errors.append("universal confidential audit version is unsupported")
    if (
        report.get("schemas", {}).get("universal_confidential_attribution_audit")
        != UNIVERSAL_CONFIDENTIAL_ATTRIBUTION_AUDIT_SCHEMA
    ):
        errors.append("universal confidential audit schema path is not declared")
    if (
        report.get("summary", {}).get("target_certification_level")
        != TARGET_CERTIFICATION_LEVEL
    ):
        errors.append("universal confidential audit target level is not RDLLM-L144")
    for finding in _contains_private_fields(report):
        errors.append(f"universal confidential audit contains private field: {finding}")
    return errors


def verify_universal_confidential_attribution_audit(
    report: dict[str, Any],
    *,
    audit_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L144 confidential attribution audit by replaying inputs."""

    errors = validate_universal_confidential_attribution_audit_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("universal_confidential_attribution_audit_hash"):
        errors.append("universal confidential audit hash is not reproducible")

    expected = make_universal_confidential_attribution_audit(
        audit_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "confidential_audit_policy",
        "artifact_bindings",
        "provider_family_rows",
        "audit_domain_rows",
        "proof_mechanism_rows",
        "stakeholder_access_rows",
        "confidential_audit_obligation_rows",
        "failure_case_rows",
        "verifier_command_rows",
        "commitments",
        "checks",
        "audit_decision",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"universal confidential audit {key} does not match replay")
    if expected.get("universal_confidential_attribution_audit_hash") != report.get(
        "universal_confidential_attribution_audit_hash"
    ):
        errors.append("universal confidential audit hash does not match replay")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("universal confidential audit status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal confidential audit check failed: {check}")

    if not _private_strings_absent(report, audit_input):
        errors.append("universal confidential audit leaks a private input string")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("universal confidential audit is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("universal confidential audit signature is invalid")

    return errors
