"""Universal citation verification contract for grounded response footers.

The L141 layer closes the gap between source-attributed runtime context and the
citations a user actually sees. A provider may not claim that a footer grounds an
answer unless every displayed source label is independently checked for source
identity, locator health, metadata fidelity, claim support, evidence-force
calibration, context provenance, rendered-footer delivery, and royalty state.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_CITATION_VERIFICATION_CONTRACT_VERSION = (
    "rdllm-universal-citation-verification-contract/v1"
)
UNIVERSAL_CITATION_VERIFICATION_CONTRACT_SCHEMA = (
    "docs/schemas/universal_citation_verification_contract.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L141"
MINIMUM_INPUT_LEVEL = "RDLLM-L140"
DEFAULT_WELL_KNOWN_PATH = (
    "/.well-known/rdllm/universal-citation-verification-contract.json"
)

REQUIRED_CORE_ARTIFACTS = (
    "universal_context_provenance_bridge",
    "source_footer_delivery",
    "response_envelope",
    "source_verification_report",
    "citation_url_health",
    "evidence_locator_manifest",
    "answer_claim_coverage_report",
    "evidence_force_calibration",
    "source_confidence_report",
    "warranted_source_footer",
    "rendered_attribution_audit",
    "trust_registry",
)

REQUIRED_VERIFICATION_DIMENSIONS = (
    "source_identity",
    "locator_resolvability",
    "metadata_fidelity",
    "claim_support",
    "evidence_force_calibration",
    "footer_rendering",
    "context_provenance",
    "royalty_status",
    "source_authenticity",
    "private_leakage",
)

REQUIRED_FAILURE_CASES = (
    "nonexistent_source",
    "metadata_drift",
    "inaccessible_locator",
    "unsupported_claim",
    "overclaimed_evidence_force",
    "footer_context_mismatch",
    "hallucinated_label",
    "missing_royalty_state",
    "stale_snapshot",
    "private_text_leak",
)

REQUIRED_VERIFIER_COMMANDS = (
    "verify-universal-context-provenance-bridge",
    "verify-source-verification",
    "verify-citation-url-health",
    "verify-evidence-locator-manifest",
    "verify-answer-claim-coverage-report",
    "verify-evidence-force-calibration",
    "verify-source-confidence-report",
    "verify-warranted-source-footer",
    "verify-rendered-attribution-audit",
    "verify-universal-citation-verification-contract",
)

DECLARED_HASH_FIELDS = (
    "universal_citation_verification_contract_hash",
    "universal_context_provenance_bridge_hash",
    "source_footer_delivery_hash",
    "citation_url_health_hash",
    "evidence_locator_manifest_hash",
    "evidence_force_calibration_hash",
    "source_confidence_hash",
    "warranted_source_footer_hash",
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
    "raw_context",
    "raw_context_text",
    "context_text",
    "tool_result",
    "raw_tool_result",
    "raw_model_output",
    "raw_native_response",
    "native_response_body",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "raw_answer_text",
    "rendered_output",
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
    "license_server_secret",
    "raw_license_token",
    "access_token",
    "refresh_token",
    "secret",
    "signing_secret",
    "private_key",
}

ALLOWED_LOCATOR_STATES = {"live", "archived", "content_addressed", "snapshot"}
ALLOWED_ROYALTY_STATES = {"direct", "licensed", "active", "escrow"}


def load_universal_citation_verification_contract_input(
    path: str | Path,
) -> dict[str, Any]:
    """Load private replay input for an L141 citation verification contract."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_citation_verification_contract_hash", "signature"}
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
    report: dict[str, Any], contract_input: dict[str, Any]
) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in contract_input.get("private_strings", [])
        if str(item).strip()
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


def _source_labels_from_footer(delivery: dict[str, Any]) -> set[str]:
    labels: set[str] = set()
    for row in delivery.get("source_delivery_rows", []):
        if not isinstance(row, dict):
            continue
        label = row.get("source_label") or row.get("label")
        if label:
            labels.add(str(label))
    for row in delivery.get("claim_delivery_rows", []):
        if not isinstance(row, dict):
            continue
        for label in row.get("source_labels", []):
            labels.add(str(label))
    return labels


def _source_labels_from_response(envelope: dict[str, Any]) -> set[str]:
    labels: set[str] = set()
    response = envelope.get("response", {})
    for label in response.get("source_labels", []):
        labels.add(str(label))
    return labels


def _source_labels_from_l140(bridge: dict[str, Any]) -> set[str]:
    labels: set[str] = set()
    for row in bridge.get("context_access_rows", []):
        if isinstance(row, dict) and row.get("source_label"):
            labels.add(str(row["source_label"]))
    return labels


def _component_input_map(contract_input: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    value = contract_input.get(key, {})
    if isinstance(value, dict):
        return {
            str(name): row
            for name, row in value.items()
            if isinstance(row, dict)
        }
    if isinstance(value, list):
        return {
            str(
                row.get("dimension")
                or row.get("case_id")
                or row.get("command")
                or row.get("source_label")
                or row.get("label")
            ): row
            for row in value
            if isinstance(row, dict)
        }
    return {}


def _policy(contract_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(contract_input.get("citation_policy", {}))
    return {
        "profile": "rdllm-universal-citation-verification-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "required_core_artifacts": list(
            policy.get("required_core_artifacts", REQUIRED_CORE_ARTIFACTS)
        ),
        "required_verification_dimensions": list(
            policy.get(
                "required_verification_dimensions", REQUIRED_VERIFICATION_DIMENSIONS
            )
        ),
        "required_failure_cases": list(
            policy.get("required_failure_cases", REQUIRED_FAILURE_CASES)
        ),
        "required_verifier_commands": list(
            policy.get("required_verifier_commands", REQUIRED_VERIFIER_COMMANDS)
        ),
        "minimum_evidence_force_score": str(
            policy.get("minimum_evidence_force_score", "0.75")
        ),
        "on_unverified_citation": "block_verified_footer_claim",
        "on_unsupported_claim": "remove_claim_or_label_unsupported",
        "on_hallucinated_source": "block_response_release_and_route_to_audit",
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


def _verification_dimension_rows(
    contract_input: dict[str, Any], required_dimensions: list[str]
) -> list[dict[str, Any]]:
    dimension_map = _component_input_map(contract_input, "verification_dimension_rows")
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
        row["verification_dimension_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _citation_rows(
    contract_input: dict[str, Any], minimum_force_score: Decimal
) -> list[dict[str, Any]]:
    rows = []
    for item in sorted(
        contract_input.get("citation_verification_rows", []),
        key=lambda row: (
            int(row.get("display_order", 0) or 0),
            str(row.get("source_label", "")),
        ),
    ):
        if not isinstance(item, dict):
            continue
        force_score = str(item.get("evidence_force_score", "0"))
        row = {
            "source_label": str(item.get("source_label", "")),
            "display_label": str(item.get("display_label", "")),
            "display_order": int(item.get("display_order", 0) or 0),
            "work_id": str(item.get("work_id", "")),
            "creator_id": str(item.get("creator_id", "")),
            "title_hash": str(item.get("title_hash", "")),
            "source_uri_hash": str(item.get("source_uri_hash", "")),
            "locator_hash": str(item.get("locator_hash", "")),
            "metadata_hash": str(item.get("metadata_hash", "")),
            "claim_hashes": sorted(
                {str(value) for value in item.get("claim_hashes", []) if value}
            ),
            "context_access_hashes": sorted(
                {
                    str(value)
                    for value in item.get("context_access_hashes", [])
                    if value
                }
            ),
            "footer_row_hash": str(item.get("footer_row_hash", "")),
            "source_verification_row_hash": str(
                item.get("source_verification_row_hash", "")
            ),
            "url_health_row_hash": str(item.get("url_health_row_hash", "")),
            "locator_row_hash": str(item.get("locator_row_hash", "")),
            "confidence_row_hash": str(item.get("confidence_row_hash", "")),
            "evidence_force_row_hash": str(item.get("evidence_force_row_hash", "")),
            "rendered_audit_row_hash": str(item.get("rendered_audit_row_hash", "")),
            "royalty_event_hash": str(item.get("royalty_event_hash", "")),
            "locator_state": str(item.get("locator_state", "")),
            "freshness_state": str(item.get("freshness_state", "")),
            "royalty_state": str(item.get("royalty_state", "")),
            "confidence_level": str(item.get("confidence_level", "")),
            "evidence_force_score": force_score,
            "source_exists": item.get("source_exists") is True,
            "metadata_verified": item.get("metadata_verified") is True,
            "claim_supported": item.get("claim_supported") is True,
            "footer_visible": item.get("footer_visible") is True,
            "context_bound": item.get("context_bound") is True,
            "royalty_linked": item.get("royalty_linked") is True,
            "authenticity_verified": item.get("authenticity_verified") is True,
        }
        row["ready"] = (
            bool(row["source_label"])
            and bool(row["display_label"])
            and bool(row["work_id"])
            and bool(row["creator_id"])
            and bool(row["title_hash"])
            and bool(row["source_uri_hash"])
            and bool(row["locator_hash"])
            and bool(row["metadata_hash"])
            and bool(row["claim_hashes"])
            and bool(row["context_access_hashes"])
            and bool(row["footer_row_hash"])
            and bool(row["source_verification_row_hash"])
            and bool(row["url_health_row_hash"])
            and bool(row["locator_row_hash"])
            and bool(row["confidence_row_hash"])
            and bool(row["evidence_force_row_hash"])
            and bool(row["rendered_audit_row_hash"])
            and bool(row["royalty_event_hash"])
            and row["locator_state"] in ALLOWED_LOCATOR_STATES
            and row["freshness_state"] == "fresh"
            and row["royalty_state"] in ALLOWED_ROYALTY_STATES
            and row["confidence_level"] in {"verified", "high"}
            and _as_decimal(force_score) >= minimum_force_score
            and row["source_exists"]
            and row["metadata_verified"]
            and row["claim_supported"]
            and row["footer_visible"]
            and row["context_bound"]
            and row["royalty_linked"]
            and row["authenticity_verified"]
        )
        row["citation_verification_row_hash"] = hash_payload(row)
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
            and bool(row["verifier_command"])
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
        row = {
            "command": command,
            "declared": command in declared,
            "required": True,
        }
        row["verifier_command_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def make_universal_citation_verification_contract(
    contract_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed L141 universal citation verification contract."""

    created_at = created_at or now_iso()
    policy = _policy(contract_input)
    minimum_force_score = _as_decimal(policy["minimum_evidence_force_score"])
    required_artifacts = [str(name) for name in policy["required_core_artifacts"]]
    required_dimensions = [
        str(name) for name in policy["required_verification_dimensions"]
    ]
    required_cases = [str(name) for name in policy["required_failure_cases"]]
    required_commands = [str(name) for name in policy["required_verifier_commands"]]

    bridge = contract_input.get("universal_context_provenance_bridge", {})
    source_footer_delivery = contract_input.get("source_footer_delivery", {})
    response_envelope = contract_input.get("response_envelope", {})
    discovery = contract_input.get("discovery_manifest", {})

    artifact_bindings = _artifact_bindings(contract_input, required_artifacts)
    verification_dimension_rows = _verification_dimension_rows(
        contract_input, required_dimensions
    )
    citation_verification_rows = _citation_rows(contract_input, minimum_force_score)
    failure_case_rows = _failure_case_rows(contract_input, required_cases)
    verifier_command_rows = _verifier_command_rows(contract_input, required_commands)

    footer_labels = _source_labels_from_footer(source_footer_delivery)
    response_labels = _source_labels_from_response(response_envelope)
    bridge_labels = _source_labels_from_l140(bridge)
    citation_labels = {row["source_label"] for row in citation_verification_rows}

    public_projection = {
        "artifact_bindings": artifact_bindings,
        "verification_dimension_rows": verification_dimension_rows,
        "citation_verification_rows": citation_verification_rows,
        "failure_case_rows": failure_case_rows,
        "verifier_command_rows": verifier_command_rows,
    }
    private_findings = _contains_private_fields(public_projection)
    discovery_path = discovery.get("discovery", {}).get(
        "universal_citation_verification_contract_path"
    )

    checks = {
        "required_core_artifacts_present": all(
            row["present"] for row in artifact_bindings["bindings"]
        ),
        "artifact_hashes_reproducible": all(
            row["hash_reproducible"] for row in artifact_bindings["bindings"]
        ),
        "context_bridge_ready_l140": (
            _artifact_status(bridge) == "ready"
            and _artifact_target_level(bridge) == MINIMUM_INPUT_LEVEL
            and _summary(bridge).get("privacy_preserved") is True
        ),
        "verification_dimensions_complete": all(
            row["ready"] for row in verification_dimension_rows
        ),
        "citation_rows_present": bool(citation_verification_rows),
        "citation_rows_ready": bool(citation_verification_rows)
        and all(row["ready"] for row in citation_verification_rows),
        "displayed_footer_labels_covered": bool(footer_labels)
        and footer_labels <= citation_labels,
        "response_source_labels_covered": bool(response_labels)
        and response_labels <= citation_labels,
        "context_source_labels_covered": bool(bridge_labels)
        and bridge_labels <= citation_labels,
        "citation_labels_not_hallucinated": bool(citation_labels)
        and citation_labels <= (footer_labels | response_labels | bridge_labels),
        "all_claims_supported_by_verified_citations": all(
            row["claim_supported"] for row in citation_verification_rows
        ),
        "all_citations_have_royalty_projection": all(
            row["royalty_linked"] and row["royalty_state"] in ALLOWED_ROYALTY_STATES
            for row in citation_verification_rows
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
        "required_core_artifacts_present": "citation_contract_artifact_missing",
        "artifact_hashes_reproducible": "citation_contract_artifact_hash_not_reproducible",
        "context_bridge_ready_l140": "context_bridge_not_ready_l140",
        "verification_dimensions_complete": "citation_verification_dimension_gap",
        "citation_rows_present": "citation_rows_missing",
        "citation_rows_ready": "citation_row_failed_verification",
        "displayed_footer_labels_covered": "displayed_footer_label_unverified",
        "response_source_labels_covered": "response_source_label_unverified",
        "context_source_labels_covered": "context_source_label_unverified",
        "citation_labels_not_hallucinated": "hallucinated_citation_label",
        "all_claims_supported_by_verified_citations": "unsupported_cited_claim",
        "all_citations_have_royalty_projection": "citation_missing_royalty_projection",
        "failure_cases_fail_closed": "citation_negative_case_not_blocked",
        "public_verifier_commands_declared": "citation_verifier_command_missing",
        "discovery_manifest_exposes_contract_path": "citation_contract_discovery_path_missing",
        "public_report_has_no_private_field_names": "private_field_name_leak",
        "private_strings_absent": "private_string_leak",
    }
    failure_modes = [failure_modes_by_check[name] for name in failed_checks]
    ready = not failed_checks

    commitments = {
        "artifact_binding_root": artifact_bindings["artifact_binding_root"],
        "verification_dimension_root": merkle_root(
            [row["verification_dimension_row_hash"] for row in verification_dimension_rows]
        ),
        "citation_verification_root": merkle_root(
            [row["citation_verification_row_hash"] for row in citation_verification_rows]
        ),
        "failure_case_root": merkle_root(
            [row["failure_case_row_hash"] for row in failure_case_rows]
        ),
        "verifier_command_root": merkle_root(
            [row["verifier_command_row_hash"] for row in verifier_command_rows]
        ),
        "universal_context_provenance_bridge_hash": _declared_hash(bridge),
        "source_footer_delivery_hash": _declared_hash(source_footer_delivery),
        "response_envelope_hash": _declared_hash(response_envelope),
    }
    commitments["citation_contract_commitment_hash"] = hash_payload(commitments)

    report: dict[str, Any] = {
        "citation_contract_version": UNIVERSAL_CITATION_VERIFICATION_CONTRACT_VERSION,
        "issuer": issuer,
        "created_at": created_at,
        "citation_policy": policy,
        "artifact_bindings": artifact_bindings,
        "verification_dimension_rows": verification_dimension_rows,
        "citation_verification_rows": citation_verification_rows,
        "failure_case_rows": failure_case_rows,
        "verifier_command_rows": verifier_command_rows,
        "commitments": commitments,
        "checks": checks,
        "citation_decision": {
            "decision": "publish_universal_citation_verification_contract"
            if ready
            else "block_universal_citation_verification_contract",
            "publication_authorized": ready,
            "verified_footer_release_approved": ready,
            "citation_reliance_approved": ready,
            "failed_checks": failed_checks,
            "failure_modes": failure_modes,
            "safe_output_policy": "render_only_l141_verified_citations"
            if ready
            else "block_verified_citation_claim",
        },
        "schemas": {
            "universal_citation_verification_contract": (
                UNIVERSAL_CITATION_VERIFICATION_CONTRACT_SCHEMA
            ),
            "universal_context_provenance_bridge": (
                "docs/schemas/universal_context_provenance_bridge.schema.json"
            ),
            "source_footer_delivery": "docs/schemas/source_footer_delivery.schema.json",
            "response_envelope": "docs/schemas/response_envelope.schema.json",
            "evidence_locator_manifest": (
                "docs/schemas/evidence_locator_manifest.schema.json"
            ),
        },
        "privacy": {
            "raw_answer_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_context_text_disclosed": False,
            "raw_prompt_text_disclosed": False,
            "hash_only_citation_bindings": True,
            "private_field_findings": private_findings,
            "private_strings_absent": checks["private_strings_absent"],
        },
        "summary": {
            "status": "ready" if ready else "blocked",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "verification_dimension_count": len(verification_dimension_rows),
            "citation_verification_count": len(citation_verification_rows),
            "displayed_footer_label_count": len(footer_labels),
            "context_source_label_count": len(bridge_labels),
            "failure_case_count": len(failure_case_rows),
            "verifier_command_count": len(verifier_command_rows),
            "failed_check_count": len(failed_checks),
            "failure_mode_count": len(failure_modes),
            "privacy_preserved": not private_findings
            and checks["private_strings_absent"] is True,
            "universal_context_provenance_bridge_hash": _declared_hash(bridge),
            "citation_contract_commitment_hash": commitments[
                "citation_contract_commitment_hash"
            ],
        },
    }
    report["universal_citation_verification_contract_hash"] = hash_payload(
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


def validate_universal_citation_verification_contract_shape(
    report: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = (
        "citation_contract_version",
        "issuer",
        "created_at",
        "citation_policy",
        "artifact_bindings",
        "verification_dimension_rows",
        "citation_verification_rows",
        "failure_case_rows",
        "verifier_command_rows",
        "commitments",
        "checks",
        "citation_decision",
        "schemas",
        "privacy",
        "summary",
        "universal_citation_verification_contract_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing universal citation verification field: {key}")
    if errors:
        return errors
    if (
        report.get("citation_contract_version")
        != UNIVERSAL_CITATION_VERIFICATION_CONTRACT_VERSION
    ):
        errors.append("universal citation verification contract version is unsupported")
    if (
        report.get("schemas", {}).get("universal_citation_verification_contract")
        != UNIVERSAL_CITATION_VERIFICATION_CONTRACT_SCHEMA
    ):
        errors.append("universal citation verification contract schema path is not declared")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("universal citation verification contract target level is not RDLLM-L141")
    for finding in _contains_private_fields(report):
        errors.append(
            f"universal citation verification contract contains private field: {finding}"
        )
    return errors


def verify_universal_citation_verification_contract(
    report: dict[str, Any],
    *,
    contract_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L141 universal citation verification contract by replaying inputs."""

    errors = validate_universal_citation_verification_contract_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("universal_citation_verification_contract_hash"):
        errors.append("universal citation verification contract hash is not reproducible")

    expected = make_universal_citation_verification_contract(
        contract_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "citation_policy",
        "artifact_bindings",
        "verification_dimension_rows",
        "citation_verification_rows",
        "failure_case_rows",
        "verifier_command_rows",
        "commitments",
        "checks",
        "citation_decision",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"universal citation verification contract {key} does not match replay")
    if expected.get("universal_citation_verification_contract_hash") != report.get(
        "universal_citation_verification_contract_hash"
    ):
        errors.append("universal citation verification contract hash does not match replay")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("universal citation verification contract status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"universal citation verification contract check failed: {check}")

    if not _private_strings_absent(report, contract_input):
        errors.append("universal citation verification contract leaks a private input string")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("universal citation verification contract is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("universal citation verification contract signature is invalid")

    return errors
