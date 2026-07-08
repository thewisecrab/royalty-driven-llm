"""Validate public RDLLM discovery artifacts against declared schemas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

PUBLIC_ARTIFACT_FILE_ALIASES = {
    "counterfactual_influence_report": "counterfactual_report",
    "model_signal_attribution_report": "model_signal_report",
    "response_release_gate": "release_gate",
    "foundation_api_profile": "foundation_attribution_profile",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact_path(name: str) -> Path:
    direct = ROOT / "artifacts" / f"{name}.json"
    if direct.is_file():
        return direct
    alias = PUBLIC_ARTIFACT_FILE_ALIASES.get(name)
    if alias:
        aliased = ROOT / "artifacts" / f"{alias}.json"
        if aliased.is_file():
            return aliased
    return direct


def _schema_path(name: str, schemas: dict[str, Any]) -> Path:
    declared = schemas.get(name)
    if isinstance(declared, str) and declared:
        return ROOT / declared
    return ROOT / "docs" / "schemas" / f"{name}.schema.json"


def _format_validation_error(error: Any) -> str:
    location = ".".join(str(part) for part in error.path) or "<root>"
    return f"{location}: {error.message}"


def audit() -> dict[str, Any]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        return {
            "status": "failed",
            "errors": [f"jsonschema is required for artifact schema audit: {exc}"],
            "validated_artifact_count": 0,
            "catalog_artifact_count": 0,
            "schema_count": 0,
        }

    manifest_path = ROOT / "artifacts" / "discovery_manifest.json"
    manifest = _load_json(manifest_path)
    schemas = manifest.get("schemas", {})
    if not isinstance(schemas, dict):
        schemas = {}
    catalog = manifest.get("artifact_catalog", [])
    if not isinstance(catalog, list):
        catalog = []

    errors: list[str] = []
    schema_path_errors: list[str] = []
    validation_failures: list[dict[str, Any]] = []
    validated_rows: list[dict[str, Any]] = []
    missing_artifacts: list[str] = []
    missing_schemas: list[str] = []

    for schema_name, schema_location in sorted(schemas.items()):
        if not isinstance(schema_location, str):
            schema_path_errors.append(f"{schema_name}: schema path is not a string")
            continue
        if not (ROOT / schema_location).is_file():
            schema_path_errors.append(f"{schema_name}: missing schema {schema_location}")

    for row in catalog:
        if not isinstance(row, dict):
            errors.append("artifact_catalog contains a non-object row")
            continue
        name = str(row.get("name", ""))
        if not name:
            errors.append("artifact_catalog row is missing name")
            continue

        artifact_path = _artifact_path(name)
        schema_path = _schema_path(name, schemas)
        if not artifact_path.is_file():
            missing_artifacts.append(f"{name}: {artifact_path.relative_to(ROOT)}")
            continue
        if not schema_path.is_file():
            missing_schemas.append(f"{name}: {schema_path.relative_to(ROOT)}")
            continue

        artifact = _load_json(artifact_path)
        schema = _load_json(schema_path)
        validator = Draft202012Validator(schema)
        row_errors = sorted(
            validator.iter_errors(artifact),
            key=lambda item: [str(part) for part in item.path],
        )
        if row_errors:
            validation_failures.append(
                {
                    "artifact": name,
                    "artifact_path": artifact_path.relative_to(ROOT).as_posix(),
                    "schema_path": schema_path.relative_to(ROOT).as_posix(),
                    "error_count": len(row_errors),
                    "first_error": _format_validation_error(row_errors[0]),
                }
            )
            continue

        validated_rows.append(
            {
                "artifact": name,
                "artifact_path": artifact_path.relative_to(ROOT).as_posix(),
                "schema_path": schema_path.relative_to(ROOT).as_posix(),
                "required": bool(row.get("required", False)),
            }
        )

    for item in schema_path_errors:
        errors.append(f"manifest schema path error: {item}")
    for item in missing_artifacts:
        errors.append(f"missing public artifact: {item}")
    for item in missing_schemas:
        errors.append(f"missing public artifact schema: {item}")
    for failure in validation_failures:
        errors.append(
            "schema validation failed for "
            f"{failure['artifact']} ({failure['artifact_path']}): "
            f"{failure['first_error']}"
        )

    required_catalog_count = sum(
        1 for row in catalog if isinstance(row, dict) and row.get("required") is True
    )
    required_validated_count = sum(1 for row in validated_rows if row["required"])
    return {
        "status": "failed" if errors else "passed",
        "catalog_artifact_count": len(catalog),
        "required_catalog_artifact_count": required_catalog_count,
        "schema_count": len(schemas),
        "validated_artifact_count": len(validated_rows),
        "required_validated_artifact_count": required_validated_count,
        "validation_failure_count": len(validation_failures),
        "missing_artifact_count": len(missing_artifacts),
        "missing_schema_count": len(missing_schemas),
        "schema_path_error_count": len(schema_path_errors),
        "validated_artifacts": validated_rows,
        "validation_failures": validation_failures,
        "missing_artifacts": missing_artifacts,
        "missing_schemas": missing_schemas,
        "schema_path_errors": schema_path_errors,
        "errors": errors,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"artifact_schema_audit status: {report['status']}",
        f"catalog_artifact_count: {report['catalog_artifact_count']}",
        f"validated_artifact_count: {report['validated_artifact_count']}",
        f"schema_count: {report['schema_count']}",
        f"validation_failure_count: {report['validation_failure_count']}",
        f"missing_artifact_count: {report['missing_artifact_count']}",
        f"missing_schema_count: {report['missing_schema_count']}",
    ]
    if report["errors"]:
        lines.append("errors:")
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = audit()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
