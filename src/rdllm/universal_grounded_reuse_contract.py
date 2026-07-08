"""Universal grounded reuse contracts for cached or replayed model answers.

The L142 layer closes a provider-scale deployment gap: once an answer has been
generated and verified, serving stacks may reuse it through semantic caches,
gateway caches, agentic-report reuse, or native provider cache paths. Reuse is a
new usage event, not a free bypass. It must re-check query equivalence, evidence
overlap, source freshness, consent/license state, citation continuity, and
royalty metering before a cached answer may be displayed as grounded.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_GROUNDED_REUSE_CONTRACT_VERSION = (
    "rdllm-universal-grounded-reuse-contract/v1"
)
UNIVERSAL_GROUNDED_REUSE_CONTRACT_SCHEMA = (
    "docs/schemas/universal_grounded_reuse_contract.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L142"
MINIMUM_INPUT_LEVEL = "RDLLM-L141"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-grounded-reuse-contract.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "universal_citation_verification_contract",
    "response_envelope",
    "source_footer_delivery",
    "answer_claim_coverage_report",
    "source_freshness_audit",
    "consent_revocation_propagation",
    "citation_url_health",
    "evidence_locator_manifest",
    "source_access_lease_report",
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

REQUIRED_REUSE_DIMENSIONS = (
    "query_equivalence",
    "evidence_overlap",
    "source_version_validity",
    "claim_support_replay",
    "citation_contract_continuity",
    "license_and_consent_continuity",
    "royalty_metering",
    "cache_collision_resistance",
    "provider_portability",
    "private_leakage",
)

REQUIRED_FAILURE_CASES = (
    "query_collision",
    "stale_source_version",
    "evidence_mismatch",
    "revoked_consent",
    "unsupported_cached_claim",
    "missing_reuse_royalty_event",
    "citation_contract_drift",
    "cache_poisoning",
    "private_cache_key_leak",
    "undeclared_provider_cache",
)

REQUIRED_VERIFIER_COMMANDS = (
    "verify-universal-citation-verification-contract",
    "verify-source-freshness-audit",
    "verify-consent-revocation-propagation",
    "verify-source-access-lease-report",
    "verify-answer-claim-coverage-report",
    "verify-citation-url-health",
    "verify-evidence-locator-manifest",
    "verify-universal-grounded-reuse-contract",
)

DECLARED_HASH_FIELDS = (
    "universal_grounded_reuse_contract_hash",
    "universal_citation_verification_contract_hash",
    "source_footer_delivery_hash",
    "source_freshness_audit_hash",
    "consent_revocation_propagation_hash",
    "citation_url_health_hash",
    "evidence_locator_manifest_hash",
    "source_access_lease_report_hash",
    "lease_report_hash",
    "profile_hash",
    "manifest_hash",
    "card_hash",
    "report_hash",
    "envelope_hash",
    "trust_registry_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "raw_query",
    "query_text",
    "cache_key",
    "raw_cache_key",
    "cache_value",
    "raw_context",
    "raw_context_text",
    "tool_result",
    "raw_tool_result",
    "raw_model_output",
    "output",
    "output_text",
    "answer_text",
    "rendered_output",
    "source_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "customer_id",
    "customer_email",
    "access_token",
    "refresh_token",
    "secret",
    "signing_secret",
    "private_key",
}

ALLOWED_REUSE_SURFACES = {
    "semantic_answer_cache",
    "gateway_response_cache",
    "provider_prompt_cache",
    "kv_cache",
    "agentic_report_reuse",
    "enterprise_rag_cache",
}
ALLOWED_ROYALTY_STATES = {"direct", "licensed", "active", "escrow"}


def load_universal_grounded_reuse_contract_input(path: str | Path) -> dict[str, Any]:
    """Load private replay input for an L142 grounded reuse contract."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_grounded_reuse_contract_hash", "signature"}
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


def _private_strings_absent(report: dict[str, Any], reuse_input: dict[str, Any]) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item) for item in reuse_input.get("private_strings", []) if str(item).strip()
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


def _as_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _component_input_map(reuse_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    value = reuse_input.get(key, {})
    if isinstance(value, dict):
        return {str(name): row for name, row in value.items() if isinstance(row, dict)}
    if isinstance(value, list):
        return {
            str(
                row.get("dimension")
                or row.get("provider_family")
                or row.get("case_id")
                or row.get("command")
                or row.get("reuse_id")
            ): row
            for row in value
            if isinstance(row, dict)
        }
    return {}


def _source_labels_from_l141(contract: dict[str, Any]) -> set[str]:
    labels: set[str] = set()
    for row in contract.get("citation_verification_rows", []):
        if isinstance(row, dict) and row.get("source_label"):
            labels.add(str(row["source_label"]))
    return labels


def _policy(reuse_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(reuse_input.get("reuse_policy", {}))
    return {
        "profile": "rdllm-universal-grounded-reuse-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_provider_families": list(
            policy.get("required_provider_families", REQUIRED_PROVIDER_FAMILIES)
        ),
        "required_reuse_dimensions": list(
            policy.get("required_reuse_dimensions", REQUIRED_REUSE_DIMENSIONS)
        ),
        "required_failure_cases": list(
            policy.get("required_failure_cases", REQUIRED_FAILURE_CASES)
        ),
        "required_verifier_commands": list(
            policy.get("required_verifier_commands", REQUIRED_VERIFIER_COMMANDS)
        ),
        "minimum_query_similarity": str(policy.get("minimum_query_similarity", "0.85")),
        "minimum_evidence_overlap": str(policy.get("minimum_evidence_overlap", "0.80")),
        "on_stale_source": "block_reuse_and_refresh_generation",
        "on_revoked_consent": "block_reuse_and_route_to_revocation_replay",
        "on_missing_royalty_event": "block_reuse_settlement",
        "on_cache_collision": "block_reuse_and_open_abuse_audit",
        "on_private_text_leak": "block_publication",
    }


def _artifact_bindings(reuse_input: dict[str, Any], names: list[str]) -> dict[str, Any]:
    rows = []
    for name in names:
        artifact = reuse_input.get(name)
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
    reuse_input: dict[str, Any], required_families: list[str]
) -> list[dict[str, Any]]:
    family_map = _component_input_map(reuse_input, "provider_family_rows")
    rows = []
    for family in sorted(required_families):
        item = family_map.get(family, {})
        row = {
            "provider_family": family,
            "adapter_hash": str(item.get("adapter_hash", "")),
            "cache_surface_hash": str(item.get("cache_surface_hash", "")),
            "reuse_event_schema_hash": str(item.get("reuse_event_schema_hash", "")),
            "public_verifier_command": str(item.get("public_verifier_command", "")),
            "supports_grounded_reuse": item.get("supports_grounded_reuse") is True,
            "fail_closed": item.get("fail_closed") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["adapter_hash"])
            and bool(row["cache_surface_hash"])
            and bool(row["reuse_event_schema_hash"])
            and row["public_verifier_command"]
            == "verify-universal-grounded-reuse-contract"
            and row["supports_grounded_reuse"]
            and row["fail_closed"]
        )
        row["provider_family_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _reuse_dimension_rows(
    reuse_input: dict[str, Any], required_dimensions: list[str]
) -> list[dict[str, Any]]:
    dimension_map = _component_input_map(reuse_input, "reuse_dimension_rows")
    rows = []
    for dimension in sorted(required_dimensions):
        item = dimension_map.get(dimension, {})
        row = {
            "dimension": dimension,
            "evaluator_hash": str(item.get("evaluator_hash", "")),
            "evidence_schema_hash": str(item.get("evidence_schema_hash", "")),
            "calibration_hash": str(item.get("calibration_hash", "")),
            "fail_closed": item.get("fail_closed") is True,
            "covered": item.get("covered") is True,
            "required": True,
        }
        row["ready"] = (
            bool(row["evaluator_hash"])
            and bool(row["evidence_schema_hash"])
            and bool(row["calibration_hash"])
            and row["fail_closed"]
            and row["covered"]
        )
        row["reuse_dimension_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _reuse_decision_rows(
    reuse_input: dict[str, Any],
    minimum_query_similarity: Decimal,
    minimum_evidence_overlap: Decimal,
) -> list[dict[str, Any]]:
    rows = []
    for item in sorted(
        reuse_input.get("reuse_decision_rows", []),
        key=lambda row: (str(row.get("provider_family", "")), str(row.get("reuse_id", ""))),
    ):
        if not isinstance(item, dict):
            continue
        query_similarity = str(item.get("query_similarity", "0"))
        evidence_overlap = str(item.get("evidence_overlap", "0"))
        source_labels = sorted({str(value) for value in item.get("source_labels", []) if value})
        row = {
            "reuse_id": str(item.get("reuse_id", "")),
            "provider_family": str(item.get("provider_family", "")),
            "reuse_surface": str(item.get("reuse_surface", "")),
            "cache_entry_hash": str(item.get("cache_entry_hash", "")),
            "prior_query_hash": str(item.get("prior_query_hash", "")),
            "new_query_hash": str(item.get("new_query_hash", "")),
            "query_similarity": query_similarity,
            "evidence_overlap": evidence_overlap,
            "source_labels": source_labels,
            "source_version_root": str(item.get("source_version_root", "")),
            "fresh_evidence_root": str(item.get("fresh_evidence_root", "")),
            "prior_response_envelope_hash": str(item.get("prior_response_envelope_hash", "")),
            "reused_response_envelope_hash": str(item.get("reused_response_envelope_hash", "")),
            "citation_contract_hash": str(item.get("citation_contract_hash", "")),
            "freshness_audit_hash": str(item.get("freshness_audit_hash", "")),
            "consent_revocation_hash": str(item.get("consent_revocation_hash", "")),
            "source_access_lease_hash": str(item.get("source_access_lease_hash", "")),
            "attribution_receipt_hash": str(item.get("attribution_receipt_hash", "")),
            "reuse_royalty_event_hash": str(item.get("reuse_royalty_event_hash", "")),
            "settlement_row_hash": str(item.get("settlement_row_hash", "")),
            "source_version_state": str(item.get("source_version_state", "")),
            "consent_state": str(item.get("consent_state", "")),
            "license_state": str(item.get("license_state", "")),
            "claim_support_state": str(item.get("claim_support_state", "")),
            "royalty_state": str(item.get("royalty_state", "")),
            "citation_footer_preserved": item.get("citation_footer_preserved") is True,
            "cache_collision_checked": item.get("cache_collision_checked") is True,
            "adversarial_collision_blocked": item.get("adversarial_collision_blocked") is True,
            "reuse_metered_as_new_usage": item.get("reuse_metered_as_new_usage") is True,
            "reuse_allowed": item.get("reuse_allowed") is True,
        }
        row["ready"] = (
            bool(row["reuse_id"])
            and row["provider_family"] in REQUIRED_PROVIDER_FAMILIES
            and row["reuse_surface"] in ALLOWED_REUSE_SURFACES
            and bool(row["cache_entry_hash"])
            and bool(row["prior_query_hash"])
            and bool(row["new_query_hash"])
            and _as_decimal(query_similarity) >= minimum_query_similarity
            and _as_decimal(evidence_overlap) >= minimum_evidence_overlap
            and bool(row["source_labels"])
            and bool(row["source_version_root"])
            and bool(row["fresh_evidence_root"])
            and bool(row["prior_response_envelope_hash"])
            and bool(row["reused_response_envelope_hash"])
            and row["prior_response_envelope_hash"] == row["reused_response_envelope_hash"]
            and bool(row["citation_contract_hash"])
            and bool(row["freshness_audit_hash"])
            and bool(row["consent_revocation_hash"])
            and bool(row["source_access_lease_hash"])
            and bool(row["attribution_receipt_hash"])
            and bool(row["reuse_royalty_event_hash"])
            and bool(row["settlement_row_hash"])
            and row["source_version_state"] == "current"
            and row["consent_state"] == "active"
            and row["license_state"] == "allowed"
            and row["claim_support_state"] == "supported"
            and row["royalty_state"] in ALLOWED_ROYALTY_STATES
            and row["citation_footer_preserved"]
            and row["cache_collision_checked"]
            and row["adversarial_collision_blocked"]
            and row["reuse_metered_as_new_usage"]
            and row["reuse_allowed"]
        )
        row["reuse_decision_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _failure_case_rows(
    reuse_input: dict[str, Any], required_cases: list[str]
) -> list[dict[str, Any]]:
    case_map = _component_input_map(reuse_input, "failure_case_rows")
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
    reuse_input: dict[str, Any], required_commands: list[str]
) -> list[dict[str, Any]]:
    declared = {str(command) for command in reuse_input.get("verifier_commands", [])}
    integration = reuse_input.get("integration_profile", {})
    declared |= set(
        integration.get("verifier_contract", {}).get("reference_cli_commands", [])
    )
    rows = []
    for command in sorted(required_commands):
        row = {"command": command, "declared": command in declared, "required": True}
        row["verifier_command_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def make_universal_grounded_reuse_contract(
    reuse_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L142 universal grounded reuse contract."""

    created_at = created_at or now_iso()
    policy = _policy(reuse_input)
    required_artifacts = [str(name) for name in policy["required_core_artifacts"]]
    required_families = [str(name) for name in policy["required_provider_families"]]
    required_dimensions = [str(name) for name in policy["required_reuse_dimensions"]]
    required_cases = [str(name) for name in policy["required_failure_cases"]]
    required_commands = [str(name) for name in policy["required_verifier_commands"]]
    minimum_query_similarity = _as_decimal(policy["minimum_query_similarity"])
    minimum_evidence_overlap = _as_decimal(policy["minimum_evidence_overlap"])

    citation_contract = reuse_input.get("universal_citation_verification_contract", {})
    discovery = reuse_input.get("discovery_manifest", {})

    artifact_bindings = _artifact_bindings(reuse_input, required_artifacts)
    provider_family_rows = _provider_family_rows(reuse_input, required_families)
    reuse_dimension_rows = _reuse_dimension_rows(reuse_input, required_dimensions)
    reuse_decision_rows = _reuse_decision_rows(
        reuse_input, minimum_query_similarity, minimum_evidence_overlap
    )
    failure_case_rows = _failure_case_rows(reuse_input, required_cases)
    verifier_command_rows = _verifier_command_rows(reuse_input, required_commands)

    l141_labels = _source_labels_from_l141(citation_contract)
    reuse_labels = {
        label for row in reuse_decision_rows for label in row.get("source_labels", [])
    }
    public_projection = {
        "artifact_bindings": artifact_bindings,
        "provider_family_rows": provider_family_rows,
        "reuse_dimension_rows": reuse_dimension_rows,
        "reuse_decision_rows": reuse_decision_rows,
        "failure_case_rows": failure_case_rows,
        "verifier_command_rows": verifier_command_rows,
    }
    private_findings = _contains_private_fields(public_projection)
    discovery_path = discovery.get("discovery", {}).get(
        "universal_grounded_reuse_contract_path"
    )

    checks = {
        "required_core_artifacts_present": all(
            row["present"] for row in artifact_bindings["bindings"]
        ),
        "artifact_hashes_reproducible": all(
            row["hash_reproducible"] for row in artifact_bindings["bindings"]
        ),
        "citation_contract_ready_l141": (
            _artifact_status(citation_contract) == "ready"
            and _artifact_target_level(citation_contract) == MINIMUM_INPUT_LEVEL
            and _summary(citation_contract).get("privacy_preserved") is True
        ),
        "provider_family_coverage_complete": all(
            row["ready"] for row in provider_family_rows
        ),
        "reuse_dimensions_complete": all(row["ready"] for row in reuse_dimension_rows),
        "reuse_decisions_present": bool(reuse_decision_rows),
        "reuse_decisions_ready": bool(reuse_decision_rows)
        and all(row["ready"] for row in reuse_decision_rows),
        "reuse_source_labels_covered_by_l141": bool(l141_labels)
        and bool(reuse_labels)
        and reuse_labels <= l141_labels,
        "reuse_metered_as_new_usage": all(
            row["reuse_metered_as_new_usage"]
            and bool(row["reuse_royalty_event_hash"])
            and bool(row["settlement_row_hash"])
            for row in reuse_decision_rows
        ),
        "freshness_consent_and_license_preserved": all(
            row["source_version_state"] == "current"
            and row["consent_state"] == "active"
            and row["license_state"] == "allowed"
            for row in reuse_decision_rows
        ),
        "cache_collision_resistance_enforced": all(
            row["cache_collision_checked"] and row["adversarial_collision_blocked"]
            for row in reuse_decision_rows
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
        public_projection, reuse_input
    )

    failed_checks = [name for name, passed in checks.items() if passed is not True]
    failure_modes_by_check = {
        "required_core_artifacts_present": "reuse_contract_artifact_missing",
        "artifact_hashes_reproducible": "reuse_contract_artifact_hash_not_reproducible",
        "citation_contract_ready_l141": "citation_contract_not_ready_l141",
        "provider_family_coverage_complete": "provider_family_reuse_gap",
        "reuse_dimensions_complete": "reuse_dimension_gap",
        "reuse_decisions_present": "reuse_decision_missing",
        "reuse_decisions_ready": "reuse_decision_failed_gate",
        "reuse_source_labels_covered_by_l141": "reuse_source_label_not_l141_verified",
        "reuse_metered_as_new_usage": "reuse_royalty_metering_missing",
        "freshness_consent_and_license_preserved": "reuse_rights_or_freshness_invalid",
        "cache_collision_resistance_enforced": "reuse_cache_collision_risk",
        "failure_cases_fail_closed": "reuse_negative_case_not_blocked",
        "public_verifier_commands_declared": "reuse_verifier_command_missing",
        "discovery_manifest_exposes_contract_path": "reuse_contract_discovery_path_missing",
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
        "reuse_dimension_root": merkle_root(
            [row["reuse_dimension_row_hash"] for row in reuse_dimension_rows]
        ),
        "reuse_decision_root": merkle_root(
            [row["reuse_decision_row_hash"] for row in reuse_decision_rows]
        ),
        "failure_case_root": merkle_root(
            [row["failure_case_row_hash"] for row in failure_case_rows]
        ),
        "verifier_command_root": merkle_root(
            [row["verifier_command_row_hash"] for row in verifier_command_rows]
        ),
        "universal_citation_verification_contract_hash": _declared_hash(
            citation_contract
        ),
    }
    commitments["grounded_reuse_commitment_hash"] = hash_payload(commitments)

    report: dict[str, Any] = {
        "grounded_reuse_contract_version": UNIVERSAL_GROUNDED_REUSE_CONTRACT_VERSION,
        "issuer": issuer,
        "created_at": created_at,
        "reuse_policy": policy,
        "artifact_bindings": artifact_bindings,
        "provider_family_rows": provider_family_rows,
        "reuse_dimension_rows": reuse_dimension_rows,
        "reuse_decision_rows": reuse_decision_rows,
        "failure_case_rows": failure_case_rows,
        "verifier_command_rows": verifier_command_rows,
        "commitments": commitments,
        "checks": checks,
        "reuse_decision": {
            "decision": "publish_universal_grounded_reuse_contract"
            if ready
            else "block_universal_grounded_reuse_contract",
            "publication_authorized": ready,
            "grounded_reuse_approved": ready,
            "reuse_settlement_approved": ready,
            "failed_checks": failed_checks,
            "failure_modes": failure_modes,
            "safe_output_policy": "reuse_only_after_l142_freshness_consent_evidence_and_royalty_replay"
            if ready
            else "block_cached_answer_reuse",
        },
        "schemas": {
            "universal_grounded_reuse_contract": (
                UNIVERSAL_GROUNDED_REUSE_CONTRACT_SCHEMA
            ),
            "universal_citation_verification_contract": (
                "docs/schemas/universal_citation_verification_contract.schema.json"
            ),
            "source_footer_delivery": "docs/schemas/source_footer_delivery.schema.json",
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "source_freshness_audit": "docs/schemas/source_freshness_audit.schema.json",
            "consent_revocation_propagation": (
                "docs/schemas/consent_revocation_propagation.schema.json"
            ),
        },
        "privacy": {
            "raw_query_text_disclosed": False,
            "raw_answer_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_cache_key_disclosed": False,
            "hash_only_reuse_bindings": True,
            "private_field_findings": private_findings,
            "private_strings_absent": checks["private_strings_absent"],
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "provider_family_count": len(provider_family_rows),
            "reuse_dimension_count": len(reuse_dimension_rows),
            "reuse_decision_count": len(reuse_decision_rows),
            "l141_source_label_count": len(l141_labels),
            "reuse_source_label_count": len(reuse_labels),
            "failure_case_count": len(failure_case_rows),
            "verifier_command_count": len(verifier_command_rows),
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": not private_findings
            and checks["private_strings_absent"] is True,
            "universal_citation_verification_contract_hash": _declared_hash(
                citation_contract
            ),
            "grounded_reuse_commitment_hash": commitments[
                "grounded_reuse_commitment_hash"
            ],
        },
    }
    report["universal_grounded_reuse_contract_hash"] = hash_payload(
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


def validate_universal_grounded_reuse_contract_shape(
    report: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = (
        "grounded_reuse_contract_version",
        "issuer",
        "created_at",
        "reuse_policy",
        "artifact_bindings",
        "provider_family_rows",
        "reuse_dimension_rows",
        "reuse_decision_rows",
        "failure_case_rows",
        "verifier_command_rows",
        "commitments",
        "checks",
        "reuse_decision",
        "schemas",
        "privacy",
        "summary",
        "universal_grounded_reuse_contract_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing universal grounded reuse field: {key}")
    if errors:
        return errors
    if report.get("grounded_reuse_contract_version") != UNIVERSAL_GROUNDED_REUSE_CONTRACT_VERSION:
        errors.append("universal grounded reuse contract version is unsupported")
    if (
        report.get("schemas", {}).get("universal_grounded_reuse_contract")
        != UNIVERSAL_GROUNDED_REUSE_CONTRACT_SCHEMA
    ):
        errors.append("universal grounded reuse contract schema path is not declared")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal grounded reuse contract target level is not RDLLM-L142")
    for finding in _contains_private_fields(report):
        errors.append(f"universal grounded reuse contract contains private field: {finding}")
    return errors


def verify_universal_grounded_reuse_contract(
    report: dict[str, Any],
    *,
    reuse_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L142 universal grounded reuse contract by replaying inputs."""

    errors = validate_universal_grounded_reuse_contract_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("universal_grounded_reuse_contract_hash"):
        errors.append("universal grounded reuse contract hash is not reproducible")

    expected = make_universal_grounded_reuse_contract(
        reuse_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "reuse_policy",
        "artifact_bindings",
        "provider_family_rows",
        "reuse_dimension_rows",
        "reuse_decision_rows",
        "failure_case_rows",
        "verifier_command_rows",
        "commitments",
        "checks",
        "reuse_decision",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"universal grounded reuse contract {key} does not match replay")
    if expected.get("universal_grounded_reuse_contract_hash") != report.get(
        "universal_grounded_reuse_contract_hash"
    ):
        errors.append("universal grounded reuse contract hash does not match replay")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("universal grounded reuse contract status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal grounded reuse contract check failed: {check}")

    if not _private_strings_absent(report, reuse_input):
        errors.append("universal grounded reuse contract leaks a private input string")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("universal grounded reuse contract is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("universal grounded reuse contract signature is invalid")

    return errors
