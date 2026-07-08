"""Production-readiness checks for open-source RDLLM deployments."""

from __future__ import annotations

import argparse
import hashlib
from importlib import resources
import json
from pathlib import Path
import re
from typing import Any


DATA_PACKAGE = "rdllm.data"
PROFILE_SCHEMA = "rdllm-production-readiness-profile/v1"
REPORT_SCHEMA = "rdllm-production-readiness-report/v1"
REPOSITORY_REPORT_SCHEMA = "rdllm-production-readiness-repository-report/v1"
REPOSITORY_REPORT_SCHEMA_RESOURCE = (
    "schemas",
    "production_readiness_repository_report.schema.json",
)

OPERATOR_TYPES = {
    "individual",
    "company",
    "institution",
    "government",
    "model_provider",
    "public_sector",
    "nonprofit",
}

ENVIRONMENTS = {
    "production",
    "regulated_production",
    "public_sector_production",
    "sovereign_production",
}

TENANCY_MODELS = {
    "single_tenant",
    "multi_tenant",
    "federated",
    "offline_single_user",
}

REQUIRED_DEPLOYMENT_FIELDS = (
    "deployment_id",
    "operator_name",
    "operator_type",
    "environment",
    "tenancy_model",
    "deployment_region_policy",
)

REQUIRED_PUBLIC_SURFACE_FIELDS = (
    "discovery_manifest_url",
    "provider_attribution_card_url",
    "public_schema_base_url",
    "transparency_log_url",
    "security_contact",
    "license_url",
)

REQUIRED_BOOLEAN_CONTROLS: dict[str, tuple[str, ...]] = {
    "runtime_controls": (
        "auth_required",
        "rate_limits_enabled",
        "tenant_isolation_enabled",
        "abuse_monitoring_enabled",
        "fail_closed_on_unknown_provider_state",
        "source_footer_required",
        "response_envelope_required",
        "streaming_emission_gate_required",
        "provider_route_allowlist_required",
        "no_raw_prompt_publication",
    ),
    "security_controls": (
        "secrets_externalized",
        "dependency_update_policy",
        "ci_required",
        "supply_chain_provenance_required",
        "vulnerability_reporting_path",
        "audit_log_immutability",
        "backup_restore_tested",
        "incident_response_runbook",
        "privacy_redaction_public_surfaces",
        "admin_actions_audited",
    ),
    "evidence_controls": (
        "claim_source_verification_required",
        "source_rationale_required",
        "footer_copy_export_preservation",
        "proof_pack_publication_required",
        "public_discovery_manifest_required",
        "third_party_audit_supported",
        "negative_fixture_replay_required",
        "model_response_state_normalization_required",
    ),
    "governance_controls": (
        "creator_onboarding_policy",
        "rights_registry_required",
        "duplicate_claim_dispute_process",
        "dispute_escrow_required",
        "human_review_for_conflicts",
        "appeals_process",
        "consent_revocation_process",
        "terms_publication_required",
    ),
    "settlement_controls": (
        "escrow_for_unattributed_enabled",
        "raw_payment_accounts_never_public",
        "payout_reconciliation_required",
        "settlement_report_required",
        "processor_attestation_or_instruction_only",
        "tax_and_legal_operator_responsibility_accepted",
    ),
}

PUBLIC_SECTOR_BOOLEAN_CONTROLS = (
    "procurement_evidence_export_enabled",
    "records_retention_policy_defined",
    "accessibility_review_required",
    "data_residency_policy_defined",
    "public_interest_review_policy_defined",
)

MAX_SLO_CONTROLS = {
    "operations_slo.revocation_propagation_sla_hours": 24,
    "operations_slo.incident_triage_sla_hours": 24,
    "operations_slo.footer_verification_latency_budget_ms": 2000,
    "operations_slo.transparency_publication_sla_minutes": 60,
    "operations_slo.backup_restore_test_interval_days": 90,
}

MIN_SLO_CONTROLS = {
    "settlement_controls.minimum_creator_pool_rate": 0.0001,
}


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def load_repository_report_schema() -> dict[str, Any]:
    resource = resources.files(DATA_PACKAGE).joinpath(
        *REPOSITORY_REPORT_SCHEMA_RESOURCE
    )
    return json.loads(resource.read_text(encoding="utf-8"))


def repository_readiness_report_hash(report: dict[str, Any]) -> str:
    payload = {
        key: value
        for key, value in report.items()
        if key != "repository_report_hash"
    }
    return canonical_hash(payload)


def _get_path(payload: dict[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _control(
    control_id: str,
    category: str,
    passed: bool,
    requirement: str,
    evidence: Any,
) -> dict[str, Any]:
    return {
        "control_id": control_id,
        "category": category,
        "status": "ready" if passed else "blocked",
        "requirement": requirement,
        "evidence": evidence,
    }


def evaluate_production_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Evaluate an operator profile against the RDLLM production baseline."""

    controls: list[dict[str, Any]] = []

    controls.append(
        _control(
            "profile.schema",
            "profile",
            profile.get("schema") == PROFILE_SCHEMA,
            f"profile schema must be {PROFILE_SCHEMA}",
            profile.get("schema"),
        )
    )

    deployment = profile.get("deployment", {})
    for field in REQUIRED_DEPLOYMENT_FIELDS:
        value = deployment.get(field) if isinstance(deployment, dict) else None
        controls.append(
            _control(
                f"deployment.{field}",
                "deployment",
                isinstance(value, str) and bool(value.strip()),
                f"deployment.{field} must be set",
                value,
            )
        )

    controls.append(
        _control(
            "deployment.operator_type_allowed",
            "deployment",
            deployment.get("operator_type") in OPERATOR_TYPES,
            f"operator_type must be one of {sorted(OPERATOR_TYPES)}",
            deployment.get("operator_type"),
        )
    )
    controls.append(
        _control(
            "deployment.environment_production",
            "deployment",
            deployment.get("environment") in ENVIRONMENTS,
            f"environment must be one of {sorted(ENVIRONMENTS)}",
            deployment.get("environment"),
        )
    )
    controls.append(
        _control(
            "deployment.tenancy_model_allowed",
            "deployment",
            deployment.get("tenancy_model") in TENANCY_MODELS,
            f"tenancy_model must be one of {sorted(TENANCY_MODELS)}",
            deployment.get("tenancy_model"),
        )
    )

    public_surfaces = profile.get("public_surfaces", {})
    for field in REQUIRED_PUBLIC_SURFACE_FIELDS:
        value = (
            public_surfaces.get(field) if isinstance(public_surfaces, dict) else None
        )
        controls.append(
            _control(
                f"public_surfaces.{field}",
                "public_surfaces",
                isinstance(value, str) and bool(value.strip()),
                f"public_surfaces.{field} must be published",
                value,
            )
        )

    for category, names in REQUIRED_BOOLEAN_CONTROLS.items():
        values = profile.get(category, {})
        for name in names:
            value = values.get(name) if isinstance(values, dict) else None
            controls.append(
                _control(
                    f"{category}.{name}",
                    category,
                    value is True,
                    f"{category}.{name} must be true",
                    value,
                )
            )

    public_sector_applicable = deployment.get("operator_type") in {
        "government",
        "public_sector",
    }
    public_sector_values = profile.get("public_sector_controls", {})
    for name in PUBLIC_SECTOR_BOOLEAN_CONTROLS:
        value = (
            public_sector_values.get(name)
            if isinstance(public_sector_values, dict)
            else None
        )
        if public_sector_applicable:
            passed = value is True
            requirement = f"public_sector_controls.{name} must be true"
        else:
            passed = isinstance(value, bool)
            requirement = (
                f"public_sector_controls.{name} must be declared; true is required "
                "only for government or public-sector deployments"
            )
        controls.append(
            _control(
                f"public_sector_controls.{name}",
                "public_sector_controls",
                passed,
                requirement,
                value,
            )
        )

    for dotted_path, maximum in MAX_SLO_CONTROLS.items():
        value = _get_path(profile, dotted_path)
        controls.append(
            _control(
                dotted_path,
                dotted_path.split(".", 1)[0],
                isinstance(value, (int, float)) and value <= maximum,
                f"{dotted_path} must be <= {maximum}",
                value,
            )
        )

    for dotted_path, minimum in MIN_SLO_CONTROLS.items():
        value = _get_path(profile, dotted_path)
        controls.append(
            _control(
                dotted_path,
                dotted_path.split(".", 1)[0],
                isinstance(value, (int, float)) and value >= minimum,
                f"{dotted_path} must be >= {minimum}",
                value,
            )
        )

    settlement_mode = _get_path(profile, "settlement_controls.settlement_mode")
    controls.append(
        _control(
            "settlement_controls.settlement_mode",
            "settlement_controls",
            settlement_mode
            in {"processor_attested", "instruction_only", "escrow_only"},
            "settlement_mode must be processor_attested, instruction_only, or escrow_only",
            settlement_mode,
        )
    )

    direct_payout = _get_path(profile, "settlement_controls.direct_payout_enabled")
    processor_attestation = _get_path(
        profile, "settlement_controls.external_payment_processor_attestation_required"
    )
    controls.append(
        _control(
            "settlement_controls.direct_payout_enabled",
            "settlement_controls",
            isinstance(direct_payout, bool),
            "direct_payout_enabled must be a boolean",
            direct_payout,
        )
    )
    controls.append(
        _control(
            "settlement_controls.external_payment_processor_attestation_required",
            "settlement_controls",
            isinstance(processor_attestation, bool),
            "external_payment_processor_attestation_required must be a boolean",
            processor_attestation,
        )
    )
    controls.append(
        _control(
            "settlement_controls.direct_payout_attested",
            "settlement_controls",
            direct_payout is not True or processor_attestation is True,
            "direct payout requires external payment processor attestation",
            {
                "direct_payout_enabled": direct_payout,
                "external_payment_processor_attestation_required": processor_attestation,
            },
        )
    )
    controls.append(
        _control(
            "settlement_controls.mode_direct_payout_consistency",
            "settlement_controls",
            (
                settlement_mode == "processor_attested"
                and direct_payout is True
                and processor_attestation is True
            )
            or (settlement_mode in {"instruction_only", "escrow_only"} and direct_payout is False),
            "processor_attested enables direct payout; instruction_only and escrow_only must not",
            {
                "settlement_mode": settlement_mode,
                "direct_payout_enabled": direct_payout,
                "external_payment_processor_attestation_required": processor_attestation,
            },
        )
    )

    blocked = [row for row in controls if row["status"] != "ready"]
    ready = len(controls) - len(blocked)
    deployment_id = deployment.get("deployment_id") if isinstance(deployment, dict) else None
    operator_type = deployment.get("operator_type") if isinstance(deployment, dict) else None
    direct_creator_settlement_allowed = (
        not blocked
        and settlement_mode == "processor_attested"
        and direct_payout is True
        and processor_attestation is True
    )
    return {
        "schema": REPORT_SCHEMA,
        "profile_hash": canonical_hash(profile),
        "summary": {
            "status": "ready" if not blocked else "blocked",
            "deployment_id": deployment_id,
            "operator_type": operator_type,
            "settlement_mode": settlement_mode,
            "direct_payout_enabled": direct_payout,
            "payment_processor_attested": processor_attestation,
            "ready_control_count": ready,
            "blocked_control_count": len(blocked),
            "total_control_count": len(controls),
            "production_grade_claim_allowed": not blocked,
            "direct_creator_settlement_allowed": direct_creator_settlement_allowed,
            "public_sector_use_supported": not blocked and public_sector_applicable,
        },
        "control_rows": controls,
        "blocked_controls": [
            {
                "control_id": row["control_id"],
                "requirement": row["requirement"],
                "evidence": row["evidence"],
            }
            for row in blocked
        ],
    }


def verify_production_readiness_report(
    profile: dict[str, Any], report: dict[str, Any]
) -> dict[str, Any]:
    expected = evaluate_production_profile(profile)
    errors: list[str] = []
    for field in ("schema", "profile_hash"):
        if report.get(field) != expected.get(field):
            errors.append(f"{field} mismatch")
    expected_summary = expected.get("summary", {})
    actual_summary = report.get("summary", {})
    for field in (
        "status",
        "ready_control_count",
        "blocked_control_count",
        "total_control_count",
        "production_grade_claim_allowed",
        "direct_creator_settlement_allowed",
        "public_sector_use_supported",
        "settlement_mode",
        "direct_payout_enabled",
        "payment_processor_attested",
    ):
        if actual_summary.get(field) != expected_summary.get(field):
            errors.append(f"summary.{field} mismatch")
    if report.get("control_rows") != expected.get("control_rows"):
        errors.append("control_rows mismatch")
    return {
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "profile_hash": expected["profile_hash"],
    }


def _resolve_schema_ref(root_schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        return {}
    current: Any = root_schema
    for part in ref[2:].split("/"):
        if not isinstance(current, dict) or part not in current:
            return {}
        current = current[part]
    return current if isinstance(current, dict) else {}


def _schema_path_label(path: tuple[str, ...]) -> str:
    return ".".join(path) if path else "<root>"


def _schema_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _schema_type_is_valid(value: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        return any(_schema_type_matches(value, entry) for entry in expected)
    if isinstance(expected, str):
        return _schema_type_matches(value, expected)
    return True


def _schema_condition_matches(
    value: Any,
    schema_node: dict[str, Any],
    root_schema: dict[str, Any],
) -> bool:
    if "$ref" in schema_node:
        return _schema_condition_matches(
            value,
            _resolve_schema_ref(root_schema, schema_node["$ref"]),
            root_schema,
        )
    if "const" in schema_node and value != schema_node["const"]:
        return False
    if "enum" in schema_node and value not in schema_node["enum"]:
        return False
    expected_type = schema_node.get("type")
    if expected_type is not None and not _schema_type_is_valid(value, expected_type):
        return False
    if "required" in schema_node:
        if not isinstance(value, dict):
            return False
        if any(field not in value for field in schema_node["required"]):
            return False
    if "properties" in schema_node:
        if not isinstance(value, dict):
            return False
        for field, child_schema in schema_node["properties"].items():
            if field in value and not _schema_condition_matches(
                value[field],
                child_schema,
                root_schema,
            ):
                return False
    return True


def _schema_errors(
    value: Any,
    schema_node: dict[str, Any],
    root_schema: dict[str, Any],
    path: tuple[str, ...] = (),
) -> list[str]:
    if "$ref" in schema_node:
        return _schema_errors(
            value,
            _resolve_schema_ref(root_schema, schema_node["$ref"]),
            root_schema,
            path,
        )

    errors: list[str] = []
    label = _schema_path_label(path)
    if "const" in schema_node and value != schema_node["const"]:
        errors.append(f"{label}: expected constant {schema_node['const']!r}")
    if "enum" in schema_node and value not in schema_node["enum"]:
        errors.append(f"{label}: expected one of {schema_node['enum']!r}")

    expected_type = schema_node.get("type")
    if expected_type is not None and not _schema_type_is_valid(value, expected_type):
        errors.append(f"{label}: expected {expected_type!r}")
        return errors

    validates_object_shape = (
        expected_type == "object"
        or "properties" in schema_node
        or "required" in schema_node
        or schema_node.get("additionalProperties") is False
    )
    if validates_object_shape:
        if not isinstance(value, dict):
            errors.append(f"{label}: expected object")
            return errors
        properties = schema_node.get("properties", {})
        for field in schema_node.get("required", []):
            if field not in value:
                errors.append(f"{label}.{field}: missing required field")
        if schema_node.get("additionalProperties") is False:
            unknown = sorted(set(value) - set(properties))
            errors.extend(f"{label}.{field}: unknown field" for field in unknown)
        for field, child_schema in properties.items():
            if field in value:
                errors.extend(
                    _schema_errors(
                        value[field],
                        child_schema,
                        root_schema,
                        (*path, field),
                    )
                )

    if isinstance(value, list):
        if "minItems" in schema_node and len(value) < int(schema_node["minItems"]):
            errors.append(
                f"{label}: must contain at least {schema_node['minItems']} items"
            )
        if "maxItems" in schema_node and len(value) > int(schema_node["maxItems"]):
            errors.append(
                f"{label}: must contain at most {schema_node['maxItems']} items"
            )
        if schema_node.get("uniqueItems") is True:
            seen: set[str] = set()
            for item in value:
                marker = json.dumps(item, sort_keys=True, separators=(",", ":"))
                if marker in seen:
                    errors.append(f"{label}: items must be unique")
                    break
                seen.add(marker)
        item_schema = schema_node.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(
                    _schema_errors(
                        item,
                        item_schema,
                        root_schema,
                        (*path, str(index)),
                    )
                )

    if isinstance(value, str) and "pattern" in schema_node:
        if re.search(schema_node["pattern"], value) is None:
            errors.append(f"{label}: does not match pattern {schema_node['pattern']!r}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema_node and value < schema_node["minimum"]:
            errors.append(f"{label}: value must be >= {schema_node['minimum']}")
        if "maximum" in schema_node and value > schema_node["maximum"]:
            errors.append(f"{label}: value must be <= {schema_node['maximum']}")

    for entry in schema_node.get("allOf", []):
        if "if" in entry and "then" in entry:
            if _schema_condition_matches(value, entry["if"], root_schema):
                errors.extend(_schema_errors(value, entry["then"], root_schema, path))
        else:
            errors.extend(_schema_errors(value, entry, root_schema, path))
    return errors


def verify_repository_readiness_report(report: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    schema = load_repository_report_schema()
    errors.extend(
        f"schema:{error}"
        for error in _schema_errors(report, schema, schema)
    )

    if report.get("schema") != REPOSITORY_REPORT_SCHEMA:
        errors.append("schema mismatch")
    status = report.get("status")
    if status not in {"ready", "blocked"}:
        errors.append("status must be ready or blocked")
    report_errors = report.get("errors")
    if not isinstance(report_errors, list) or not all(
        isinstance(error, str) for error in report_errors
    ):
        errors.append("errors must be a list of strings")
        report_errors = []
    if status == "ready" and report_errors:
        errors.append("ready repository report must not contain errors")
    if status == "blocked" and not report_errors:
        errors.append("blocked repository report must contain errors")
    expected_hash = repository_readiness_report_hash(report)
    if report.get("repository_report_hash") != expected_hash:
        errors.append("repository_report_hash mismatch")

    summary = report.get("summary", {})
    if not isinstance(summary, dict):
        errors.append("summary must be an object")
        summary = {}
    profile_report = report.get("profile_report", {})
    if not isinstance(profile_report, dict):
        errors.append("profile_report must be an object")
        profile_report = {}
    profile_summary = profile_report.get("summary", {})
    if not isinstance(profile_summary, dict):
        errors.append("profile_report.summary must be an object")
        profile_summary = {}
    profile_matrix = report.get("profile_matrix", {})
    if not isinstance(profile_matrix, dict):
        errors.append("profile_matrix must be an object")
        profile_matrix = {}
    profile_matrix_summary = profile_matrix.get("summary", {})
    if not isinstance(profile_matrix_summary, dict):
        errors.append("profile_matrix.summary must be an object")
        profile_matrix_summary = {}
    acceptance_matrix = report.get("acceptance_matrix", {})
    if not isinstance(acceptance_matrix, dict):
        errors.append("acceptance_matrix must be an object")
        acceptance_matrix = {}
    acceptance_summary = acceptance_matrix.get("summary", {})
    if not isinstance(acceptance_summary, dict):
        errors.append("acceptance_matrix.summary must be an object")
        acceptance_summary = {}

    if profile_report.get("schema") != REPORT_SCHEMA:
        errors.append("profile_report.schema mismatch")
    if summary.get("profile_status") != profile_summary.get("status"):
        errors.append("summary.profile_status mismatch")
    if summary.get("profile_matrix_status") != profile_matrix.get("status"):
        errors.append("summary.profile_matrix_status mismatch")
    if summary.get("profile_matrix_profile_count") != profile_matrix_summary.get(
        "profile_count"
    ):
        errors.append("summary.profile_matrix_profile_count mismatch")
    if summary.get("acceptance_matrix_status") != acceptance_matrix.get("status"):
        errors.append("summary.acceptance_matrix_status mismatch")
    if summary.get("acceptance_matrix_operator_template_count") != (
        acceptance_summary.get("operator_template_count")
    ):
        errors.append("summary.acceptance_matrix_operator_template_count mismatch")
    if summary.get("acceptance_matrix_passed_count") != acceptance_summary.get(
        "passed_count"
    ):
        errors.append("summary.acceptance_matrix_passed_count mismatch")
    if summary.get(
        "acceptance_matrix_production_acceptance_allowed_count"
    ) != acceptance_summary.get("production_acceptance_allowed_count"):
        errors.append(
            "summary.acceptance_matrix_production_acceptance_allowed_count mismatch"
        )

    if status == "ready":
        required_summary = {
            "profile_status": "ready",
            "profile_matrix_status": "passed",
            "profile_matrix_profile_count": 5,
            "acceptance_matrix_status": "passed",
            "acceptance_matrix_operator_template_count": 5,
            "acceptance_matrix_passed_count": 5,
            "acceptance_matrix_production_acceptance_allowed_count": 5,
        }
        for field, expected in required_summary.items():
            if summary.get(field) != expected:
                errors.append(f"summary.{field} expected {expected!r}")
        if summary.get("production_grade_claim_allowed") is not True:
            errors.append("summary.production_grade_claim_allowed must be true")
        expected_templates = {
            "company",
            "government",
            "individual",
            "institution",
            "public_sector",
        }
        rows = acceptance_matrix.get("rows", [])
        if not isinstance(rows, list):
            errors.append("acceptance_matrix.rows must be a list")
            rows = []
        templates = {
            row.get("operator_template")
            for row in rows
            if isinstance(row, dict)
        }
        if templates != expected_templates:
            errors.append("acceptance_matrix.rows do not cover every operator template")
        for row in rows:
            if not isinstance(row, dict):
                errors.append("acceptance_matrix row must be an object")
                continue
            template = row.get("operator_template", "")
            for field, expected in {
                "status": "passed",
                "acceptance_status": "ready",
                "acceptance_verification_status": "passed",
                "production_acceptance_decision": "allow",
                "source_grounding_acceptance_status": "passed",
                "audit_response_binding_status": "passed",
                "recovery_verification_status": "passed",
            }.items():
                if row.get(field) != expected:
                    errors.append(
                        f"acceptance_matrix.rows[{template}].{field} expected {expected!r}"
                    )

    return {
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "repository_report_hash": expected_hash,
    }


def render_repository_verification_text(verification: dict[str, Any]) -> str:
    lines = [
        f"production_readiness_repository_verification status: {verification['status']}",
        f"repository_report_hash: {verification.get('repository_report_hash', '')}",
    ]
    if verification.get("errors"):
        lines.append("errors:")
        lines.extend(f"- {error}" for error in verification["errors"])
    return "\n".join(lines)


def required_profile_control_count() -> int:
    empty = evaluate_production_profile({})
    return int(empty["summary"]["total_control_count"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a saved RDLLM repository production-readiness report."
    )
    parser.add_argument(
        "--report",
        required=True,
        help="Saved repository-mode production-readiness report to verify.",
    )
    parser.add_argument(
        "--write-report",
        help="Optional path to write the JSON verification result.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args(argv)

    report = load_json(Path(args.report))
    verification = verify_repository_readiness_report(report)
    if args.write_report:
        destination = Path(args.write_report)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(verification, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.json:
        print(json.dumps(verification, indent=2, sort_keys=True))
    else:
        print(render_repository_verification_text(verification))
    return 0 if verification["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
