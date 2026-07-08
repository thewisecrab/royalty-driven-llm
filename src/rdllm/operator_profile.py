"""Create and validate RDLLM production-readiness operator profiles."""

from __future__ import annotations

import argparse
import copy
from importlib import resources
import json
import re
from pathlib import Path
from typing import Any

from rdllm.production_readiness import (
    evaluate_production_profile,
    load_json,
    verify_production_readiness_report,
)


DATA_PACKAGE = "rdllm.data"
PROFILE_SCHEMA_RESOURCE = ("schemas", "production_readiness_profile.schema.json")
PROFILE_VERIFICATION_SCHEMA = "rdllm-operator-profile-verification/v1"
PROFILE_VERIFICATION_SCHEMA_RESOURCE = (
    "schemas",
    "operator_profile_verification.schema.json",
)
TEMPLATE_RESOURCES = {
    "individual": ("production_profiles", "individual_escrow_only.json"),
    "company": ("production_profiles", "company_instruction_only.json"),
    "institution": ("production_profiles", "institution_instruction_only.json"),
    "government": ("production_profiles", "government_escrow_only.json"),
    "public_sector": ("production_profiles", "public_sector_processor_attested.json"),
}


def _resource_json(parts: tuple[str, ...]) -> dict[str, Any]:
    resource = resources.files(DATA_PACKAGE).joinpath(*parts)
    return json.loads(resource.read_text(encoding="utf-8"))


def load_profile_schema() -> dict[str, Any]:
    return _resource_json(PROFILE_SCHEMA_RESOURCE)


def load_profile_verification_schema() -> dict[str, Any]:
    return _resource_json(PROFILE_VERIFICATION_SCHEMA_RESOURCE)


def load_template(template: str) -> dict[str, Any]:
    if template not in TEMPLATE_RESOURCES:
        choices = ", ".join(sorted(TEMPLATE_RESOURCES))
        raise ValueError(f"unknown template {template!r}; choose one of: {choices}")
    return _resource_json(TEMPLATE_RESOURCES[template])


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "operator"


def _is_json_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _path_label(path: tuple[str, ...]) -> str:
    return ".".join(path) if path else "<root>"


def _resolve_ref(root_schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        return {}
    current: Any = root_schema
    for part in ref[2:].split("/"):
        if not isinstance(current, dict) or part not in current:
            return {}
        current = current[part]
    return current if isinstance(current, dict) else {}


def _condition_matches(
    value: Any,
    condition: dict[str, Any],
    root_schema: dict[str, Any],
) -> bool:
    if "$ref" in condition:
        return _condition_matches(
            value,
            _resolve_ref(root_schema, condition["$ref"]),
            root_schema,
        )
    if "const" in condition and value != condition["const"]:
        return False
    if "enum" in condition and value not in condition["enum"]:
        return False
    expected_type = condition.get("type")
    if expected_type == "object" and not isinstance(value, dict):
        return False
    if expected_type == "string" and not isinstance(value, str):
        return False
    if expected_type == "boolean" and not isinstance(value, bool):
        return False
    if expected_type == "number" and not _is_json_number(value):
        return False
    if "properties" in condition:
        if not isinstance(value, dict):
            return False
        for key, child_condition in condition["properties"].items():
            if key not in value:
                return False
            if not _condition_matches(value[key], child_condition, root_schema):
                return False
    return True


def _validate_node(
    value: Any,
    schema_node: dict[str, Any],
    root_schema: dict[str, Any],
    path: tuple[str, ...],
) -> list[str]:
    if "$ref" in schema_node:
        return _validate_node(
            value,
            _resolve_ref(root_schema, schema_node["$ref"]),
            root_schema,
            path,
        )

    errors: list[str] = []
    label = _path_label(path)
    if "const" in schema_node and value != schema_node["const"]:
        errors.append(f"{label}: expected constant {schema_node['const']!r}")
    if "enum" in schema_node and value not in schema_node["enum"]:
        errors.append(f"{label}: expected one of {schema_node['enum']!r}")

    expected_type = schema_node.get("type")
    type_ok = True
    if expected_type == "object":
        type_ok = isinstance(value, dict)
    elif expected_type == "string":
        type_ok = isinstance(value, str)
    elif expected_type == "boolean":
        type_ok = isinstance(value, bool)
    elif expected_type == "number":
        type_ok = _is_json_number(value)
    if not type_ok:
        errors.append(f"{label}: expected {expected_type}")
        return errors

    if isinstance(value, str) and "minLength" in schema_node:
        if len(value) < int(schema_node["minLength"]):
            errors.append(f"{label}: length must be at least {schema_node['minLength']}")

    if _is_json_number(value):
        if "minimum" in schema_node and value < schema_node["minimum"]:
            errors.append(f"{label}: value must be >= {schema_node['minimum']}")
        if "maximum" in schema_node and value > schema_node["maximum"]:
            errors.append(f"{label}: value must be <= {schema_node['maximum']}")

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
        required = schema_node.get("required", [])
        for field in required:
            if field not in value:
                errors.append(f"{label}.{field}: missing required field")
        if schema_node.get("additionalProperties") is False:
            unknown = sorted(set(value) - set(properties))
            errors.extend(f"{label}.{field}: unknown field" for field in unknown)
        for field, child_schema in properties.items():
            if field in value:
                errors.extend(
                    _validate_node(
                        value[field],
                        child_schema,
                        root_schema,
                        (*path, field),
                    )
                )

    for entry in schema_node.get("allOf", []):
        if "if" in entry and "then" in entry:
            if _condition_matches(value, entry["if"], root_schema):
                errors.extend(_validate_node(value, entry["then"], root_schema, path))
        else:
            errors.extend(_validate_node(value, entry, root_schema, path))
    return errors


def profile_schema_errors(profile: dict[str, Any]) -> list[str]:
    schema = load_profile_schema()
    return _validate_node(profile, schema, schema, ())


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def profile_result(profile: dict[str, Any]) -> dict[str, Any]:
    schema_errors = profile_schema_errors(profile)
    readiness_report = evaluate_production_profile(profile)
    verification = verify_production_readiness_report(profile, readiness_report)
    errors = [
        *(f"profile schema: {error}" for error in schema_errors),
        *(f"report verification: {error}" for error in verification["errors"]),
        *(
            f"{row['control_id']}: {row['requirement']}"
            for row in readiness_report["blocked_controls"]
        ),
    ]
    return {
        "schema": PROFILE_VERIFICATION_SCHEMA,
        "status": "ready" if not errors else "blocked",
        "errors": errors,
        "schema_status": "passed" if not schema_errors else "failed",
        "verification_status": verification["status"],
        "profile": profile,
        "readiness_report": readiness_report,
    }


def create_profile(
    *,
    template: str,
    operator_name: str,
    security_contact: str,
    deployment_id: str | None = None,
    deployment_region_policy: str | None = None,
    discovery_manifest_url: str | None = None,
    provider_attribution_card_url: str | None = None,
    public_schema_base_url: str | None = None,
    transparency_log_url: str | None = None,
    license_url: str | None = None,
) -> dict[str, Any]:
    profile = copy.deepcopy(load_template(template))
    deployment = profile.setdefault("deployment", {})
    public_surfaces = profile.setdefault("public_surfaces", {})

    template_slug = template.replace("_", "-")
    deployment["operator_name"] = operator_name
    deployment["deployment_id"] = (
        deployment_id or f"rdllm-{_slug(operator_name)}-{template_slug}"
    )
    if deployment_region_policy:
        deployment["deployment_region_policy"] = deployment_region_policy

    public_surfaces["security_contact"] = security_contact
    for field, value in {
        "discovery_manifest_url": discovery_manifest_url,
        "provider_attribution_card_url": provider_attribution_card_url,
        "public_schema_base_url": public_schema_base_url,
        "transparency_log_url": transparency_log_url,
        "license_url": license_url,
    }.items():
        if value:
            public_surfaces[field] = value
    return profile


def _attach_paths(
    result: dict[str, Any],
    *,
    profile_path: Path | None = None,
    report_path: Path | None = None,
    template: str | None = None,
) -> dict[str, Any]:
    if profile_path is not None:
        result["profile_path"] = profile_path.as_posix()
    if report_path is not None:
        result["report_path"] = report_path.as_posix()
    if template is not None:
        result["template_resource"] = "/".join(
            (DATA_PACKAGE, *TEMPLATE_RESOURCES[template])
        )
    return result


def render_text(result: dict[str, Any]) -> str:
    report = result["readiness_report"]
    summary = report["summary"]
    lines = [
        f"operator_profile status: {result['status']}",
        f"schema_status: {result['schema_status']}",
        f"verification_status: {result['verification_status']}",
        f"deployment_id: {summary.get('deployment_id')}",
        f"operator_type: {summary.get('operator_type')}",
        f"settlement_mode: {summary.get('settlement_mode')}",
        "production_grade_claim_allowed: "
        f"{json.dumps(summary.get('production_grade_claim_allowed'))}",
        "direct_creator_settlement_allowed: "
        f"{json.dumps(summary.get('direct_creator_settlement_allowed'))}",
        "public_sector_use_supported: "
        f"{json.dumps(summary.get('public_sector_use_supported'))}",
        f"profile_hash: {report['profile_hash']}",
    ]
    if result.get("template_resource"):
        lines.append(f"template_resource: {result['template_resource']}")
    if result.get("profile_path"):
        lines.append(f"profile_path: {result['profile_path']}")
    if result.get("report_path"):
        lines.append(f"report_path: {result['report_path']}")
    if result.get("errors"):
        lines.append("errors:")
        lines.extend(f"- {error}" for error in result["errors"])
    return "\n".join(lines)


def _print_result(result: dict[str, Any], as_json: bool) -> None:
    print(
        json.dumps(result, indent=2, sort_keys=True)
        if as_json
        else render_text(result)
    )


def create(args: argparse.Namespace) -> int:
    profile = create_profile(
        template=args.template,
        operator_name=args.operator_name,
        security_contact=args.security_contact,
        deployment_id=args.deployment_id,
        deployment_region_policy=args.deployment_region_policy,
        discovery_manifest_url=args.discovery_manifest_url,
        provider_attribution_card_url=args.provider_attribution_card_url,
        public_schema_base_url=args.public_schema_base_url,
        transparency_log_url=args.transparency_log_url,
        license_url=args.license_url,
    )
    result = profile_result(profile)
    if args.output:
        write_json(args.output, profile)
    if args.write_report:
        write_json(args.write_report, result["readiness_report"])
    _attach_paths(
        result,
        profile_path=args.output,
        report_path=args.write_report,
        template=args.template,
    )
    _print_result(result, args.json)
    return 0 if result["status"] == "ready" else 1


def validate(args: argparse.Namespace) -> int:
    profile = load_json(args.profile)
    result = profile_result(profile)
    if args.write_report:
        write_json(args.write_report, result["readiness_report"])
    _attach_paths(result, profile_path=args.profile, report_path=args.write_report)
    _print_result(result, args.json)
    return 0 if result["status"] == "ready" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser(
        "create",
        help="Create an operator-specific readiness profile from a packaged template.",
    )
    create_parser.add_argument(
        "--template",
        choices=sorted(TEMPLATE_RESOURCES),
        required=True,
    )
    create_parser.add_argument("--operator-name", required=True)
    create_parser.add_argument("--security-contact", required=True)
    create_parser.add_argument("--deployment-id")
    create_parser.add_argument("--deployment-region-policy")
    create_parser.add_argument("--discovery-manifest-url")
    create_parser.add_argument("--provider-attribution-card-url")
    create_parser.add_argument("--public-schema-base-url")
    create_parser.add_argument("--transparency-log-url")
    create_parser.add_argument("--license-url")
    create_parser.add_argument("--output", type=Path)
    create_parser.add_argument("--write-report", type=Path)
    create_parser.add_argument("--json", action="store_true")
    create_parser.set_defaults(func=create)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate an existing operator readiness profile and optional report output.",
    )
    validate_parser.add_argument("--profile", type=Path, required=True)
    validate_parser.add_argument("--write-report", type=Path)
    validate_parser.add_argument("--json", action="store_true")
    validate_parser.set_defaults(func=validate)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
