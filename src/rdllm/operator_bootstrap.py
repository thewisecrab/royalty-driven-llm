"""Bootstrap an RDLLM operator deployment directory."""

from __future__ import annotations

import argparse
from importlib import resources
import json
from pathlib import Path
from typing import Any

from rdllm.operator_profile import (
    TEMPLATE_RESOURCES as PROFILE_TEMPLATES,
    create_profile,
    profile_result,
    write_json as write_profile_json,
)
from rdllm.service_config import (
    TEMPLATE_RESOURCES as SERVICE_TEMPLATES,
    create_service_config,
    service_config_result,
    write_json as write_service_json,
)
from rdllm.production_readiness import load_json


BOOTSTRAP_SCHEMA = "rdllm-operator-bootstrap/v1"
BOOTSTRAP_VERIFICATION_SCHEMA = "rdllm-operator-bootstrap-verification/v1"
DATA_PACKAGE = "rdllm.data"
BOOTSTRAP_SCHEMA_RESOURCE = ("schemas", "operator_bootstrap_manifest.schema.json")
BOOTSTRAP_VERIFICATION_SCHEMA_RESOURCE = (
    "schemas",
    "operator_bootstrap_verification.schema.json",
)
SAMPLE_CORPUS_RESOURCE = ("sample_corpus.json",)
REFERENCE_ARTIFACT_RESOURCES = {
    "certification_report": (
        "reference_artifacts",
        "certification_report.json",
    ),
    "discovery_manifest": (
        "reference_artifacts",
        "discovery_manifest.json",
    ),
    "provider_attribution_card": (
        "reference_artifacts",
        "provider_attribution_card.json",
    ),
    "production_readiness_report": (
        "reference_artifacts",
        "production_readiness_report.json",
    ),
    "universal_production_invocation_admission": (
        "reference_artifacts",
        "universal_production_invocation_admission.json",
    ),
    "universal_runtime_conformance_receipt": (
        "reference_artifacts",
        "universal_runtime_conformance_receipt.json",
    ),
    "universal_source_grounded_response_receipt": (
        "reference_artifacts",
        "universal_source_grounded_response_receipt.json",
    ),
}

SUMMARY_FIELDS = {
    "operator_name",
    "operator_template",
    "service_template",
    "profile_status",
    "service_config_status",
    "settlement_mode",
    "production_grade_claim_allowed",
    "direct_creator_settlement_allowed",
    "public_sector_use_supported",
    "sample_corpus_included",
    "reference_artifacts_included",
}
SUMMARY_STRING_FIELDS = {
    "operator_name",
    "operator_template",
    "service_template",
    "settlement_mode",
}
SUMMARY_STATUS_FIELDS = {"profile_status", "service_config_status"}
SUMMARY_BOOLEAN_FIELDS = {
    "production_grade_claim_allowed",
    "direct_creator_settlement_allowed",
    "public_sector_use_supported",
    "sample_corpus_included",
    "reference_artifacts_included",
}
PATH_FIELDS = {
    "output_dir",
    "operator_profile",
    "readiness_report",
    "service_config",
    "artifact_dir",
    "corpus",
    "runtime_dir",
    "manifest",
    "readme",
}
COMMAND_FIELDS = {"validate_profile", "validate_service_config", "start_service"}


def _path(path: Path) -> str:
    return path.as_posix()


def _resource_json(parts: tuple[str, ...]) -> dict[str, Any]:
    resource = resources.files(DATA_PACKAGE).joinpath(*parts)
    return json.loads(resource.read_text(encoding="utf-8"))


def load_bootstrap_schema() -> dict[str, Any]:
    return _resource_json(BOOTSTRAP_SCHEMA_RESOURCE)


def load_bootstrap_verification_schema() -> dict[str, Any]:
    return _resource_json(BOOTSTRAP_VERIFICATION_SCHEMA_RESOURCE)


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _field_errors(
    payload: dict[str, Any],
    *,
    allowed: set[str],
    required: set[str],
    path: str,
) -> list[str]:
    errors = [
        f"{path}.{field}: missing required field"
        for field in sorted(required - set(payload))
    ]
    errors.extend(
        f"{path}.{field}: unknown field"
        for field in sorted(set(payload) - allowed)
    )
    return errors


def _string_array_errors(value: Any, path: str) -> list[str]:
    if not isinstance(value, list):
        return [f"{path}: expected array"]
    return [
        f"{path}[{index}]: expected non-empty string"
        for index, item in enumerate(value)
        if not _is_nonempty_string(item)
    ]


def bootstrap_manifest_errors(manifest: Any) -> list[str]:
    if not isinstance(manifest, dict):
        return ["<root>: expected object"]
    errors: list[str] = []
    top_level_fields = {
        "schema",
        "status",
        "summary",
        "paths",
        "commands",
        "errors",
        "included_reference_artifacts",
    }
    errors.extend(
        _field_errors(
            manifest,
            allowed=top_level_fields,
            required=top_level_fields,
            path="<root>",
        )
    )
    if manifest.get("schema") != BOOTSTRAP_SCHEMA:
        errors.append(f"<root>.schema: expected {BOOTSTRAP_SCHEMA!r}")
    if manifest.get("status") not in {"ready", "blocked"}:
        errors.append("<root>.status: expected one of ['ready', 'blocked']")

    summary = manifest.get("summary")
    if not isinstance(summary, dict):
        errors.append("<root>.summary: expected object")
    else:
        errors.extend(
            _field_errors(
                summary,
                allowed=SUMMARY_FIELDS,
                required=SUMMARY_FIELDS,
                path="summary",
            )
        )
        for field in sorted(SUMMARY_STRING_FIELDS):
            if not _is_nonempty_string(summary.get(field)):
                errors.append(f"summary.{field}: expected non-empty string")
        for field in sorted(SUMMARY_STATUS_FIELDS):
            if summary.get(field) not in {"ready", "blocked"}:
                errors.append(f"summary.{field}: expected one of ['ready', 'blocked']")
        for field in sorted(SUMMARY_BOOLEAN_FIELDS):
            if not isinstance(summary.get(field), bool):
                errors.append(f"summary.{field}: expected boolean")

    paths = manifest.get("paths")
    if not isinstance(paths, dict):
        errors.append("<root>.paths: expected object")
    else:
        errors.extend(
            _field_errors(
                paths,
                allowed=PATH_FIELDS,
                required=PATH_FIELDS,
                path="paths",
            )
        )
        for field in sorted(PATH_FIELDS):
            if not _is_nonempty_string(paths.get(field)):
                errors.append(f"paths.{field}: expected non-empty string")

    commands = manifest.get("commands")
    if not isinstance(commands, dict):
        errors.append("<root>.commands: expected object")
    else:
        errors.extend(
            _field_errors(
                commands,
                allowed=COMMAND_FIELDS,
                required=COMMAND_FIELDS,
                path="commands",
            )
        )
        for field in sorted(COMMAND_FIELDS):
            if not _is_nonempty_string(commands.get(field)):
                errors.append(f"commands.{field}: expected non-empty string")

    errors.extend(_string_array_errors(manifest.get("errors"), "<root>.errors"))
    errors.extend(
        _string_array_errors(
            manifest.get("included_reference_artifacts"),
            "<root>.included_reference_artifacts",
        )
    )
    return errors


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _copy_data_resource(parts: tuple[str, ...], destination: Path) -> None:
    resource = resources.files(DATA_PACKAGE).joinpath(*parts)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(resource.read_bytes())


def _copy_reference_artifacts(destination_dir: Path) -> list[str]:
    copied: list[str] = []
    for parts in REFERENCE_ARTIFACT_RESOURCES.values():
        destination = destination_dir / parts[-1]
        _copy_data_resource(parts, destination)
        copied.append(_path(destination))
    return copied


def _resolve_manifest_path(
    paths: dict[str, Any],
    field: str,
    output_dir: Path,
) -> Path | None:
    raw = paths.get(field)
    if not _is_nonempty_string(raw):
        return None
    path = Path(raw)
    if path.is_absolute() and path.exists():
        return path
    declared_output = paths.get("output_dir")
    if _is_nonempty_string(declared_output) and path.is_absolute():
        try:
            return output_dir / path.relative_to(Path(declared_output))
        except ValueError:
            pass
    if not path.is_absolute():
        return output_dir / path
    return path


def _resolve_manifest_value(
    raw: str,
    paths: dict[str, Any],
    output_dir: Path,
) -> Path:
    path = Path(raw)
    if path.is_absolute() and path.exists():
        return path
    declared_output = paths.get("output_dir")
    if _is_nonempty_string(declared_output) and path.is_absolute():
        try:
            return output_dir / path.relative_to(Path(declared_output))
        except ValueError:
            pass
    return output_dir / path if not path.is_absolute() else path


def _path_check_errors(
    manifest: dict[str, Any],
    output_dir: Path,
    *,
    check_runtime: bool,
) -> tuple[list[str], dict[str, str]]:
    errors: list[str] = []
    resolved: dict[str, str] = {"output_dir": _path(output_dir)}
    paths = manifest.get("paths", {})
    if not isinstance(paths, dict):
        return errors, resolved

    file_fields = {
        "operator_profile",
        "readiness_report",
        "service_config",
        "manifest",
        "readme",
    }
    dir_fields = {"artifact_dir", "runtime_dir"}
    for field in sorted(file_fields | dir_fields):
        path = _resolve_manifest_path(paths, field, output_dir)
        if path is None:
            continue
        resolved[field] = _path(path)
        if field in file_fields and not path.is_file():
            errors.append(f"paths.{field}: file does not exist: {path}")
        if field in dir_fields and not path.is_dir():
            errors.append(f"paths.{field}: directory does not exist: {path}")

    corpus_path = _resolve_manifest_path(paths, "corpus", output_dir)
    if corpus_path is not None:
        resolved["corpus"] = _path(corpus_path)
        summary = manifest.get("summary", {})
        sample_included = isinstance(summary, dict) and summary.get(
            "sample_corpus_included"
        )
        if sample_included and not corpus_path.is_file():
            errors.append(
                f"paths.corpus: sample corpus file does not exist: {corpus_path}"
            )

    included = manifest.get("included_reference_artifacts", [])
    if isinstance(included, list):
        for index, raw in enumerate(included):
            if not _is_nonempty_string(raw):
                continue
            artifact_path = _resolve_manifest_value(raw, paths, output_dir)
            if not artifact_path.is_file():
                errors.append(
                    "included_reference_artifacts"
                    f"[{index}]: file does not exist: {artifact_path}"
                )

    summary = manifest.get("summary", {})
    if isinstance(summary, dict) and summary.get("reference_artifacts_included"):
        expected_names = {
            parts[-1] for parts in REFERENCE_ARTIFACT_RESOURCES.values()
        }
        actual_names = {
            Path(raw).name
            for raw in included
            if isinstance(raw, str) and raw.strip()
        }
        if actual_names != expected_names:
            errors.append(
                "included_reference_artifacts: expected packaged reference "
                f"artifact filenames {sorted(expected_names)!r}"
            )
    if check_runtime and corpus_path is not None and not corpus_path.is_file():
        errors.append(
            f"paths.corpus: runtime corpus file does not exist: {corpus_path}"
        )
    return errors, resolved


def _load_verification_json(
    path: Path,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    try:
        return load_json(path)
    except Exception as exc:
        errors.append(f"{label}: failed to read JSON: {exc}")
        return None


def verify_bootstrap_dir(
    output_dir: Path,
    *,
    check_runtime: bool = False,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    manifest_path = output_dir / "operator_bootstrap_manifest.json"
    errors: list[str] = []
    manifest = _load_verification_json(manifest_path, "manifest", errors)
    if manifest is None:
        return {
            "schema": BOOTSTRAP_VERIFICATION_SCHEMA,
            "status": "failed",
            "errors": errors,
            "verified_dir": _path(output_dir),
            "manifest_path": _path(manifest_path),
            "manifest_status": "missing",
            "manifest_schema_status": "failed",
            "profile_status": "skipped",
            "service_config_status": "skipped",
            "runtime_status": "skipped",
            "resolved_paths": {},
        }

    manifest_errors = bootstrap_manifest_errors(manifest)
    errors.extend(f"manifest schema: {error}" for error in manifest_errors)
    path_errors, resolved_paths = _path_check_errors(
        manifest,
        output_dir,
        check_runtime=check_runtime,
    )
    errors.extend(path_errors)
    paths = (
        manifest.get("paths", {})
        if isinstance(manifest.get("paths"), dict)
        else {}
    )
    summary = (
        manifest.get("summary", {})
        if isinstance(manifest.get("summary"), dict)
        else {}
    )

    profile_check: dict[str, Any] | None = None
    service_check: dict[str, Any] | None = None

    profile_path = _resolve_manifest_path(paths, "operator_profile", output_dir)
    report_path = _resolve_manifest_path(paths, "readiness_report", output_dir)
    if profile_path and profile_path.is_file():
        profile = _load_verification_json(profile_path, "operator_profile", errors)
        if profile is not None:
            profile_check = profile_result(profile)
            errors.extend(f"profile: {error}" for error in profile_check["errors"])
            if report_path and report_path.is_file():
                report = _load_verification_json(report_path, "readiness_report", errors)
                if report is not None and report != profile_check["readiness_report"]:
                    errors.append(
                        "readiness_report: file does not match recomputed profile report"
                    )
            if summary.get("operator_name") != profile.get("deployment", {}).get(
                "operator_name"
            ):
                errors.append(
                    "summary.operator_name: does not match operator profile deployment"
                )

    service_config_path = _resolve_manifest_path(paths, "service_config", output_dir)
    if service_config_path and service_config_path.is_file():
        service_config = _load_verification_json(
            service_config_path,
            "service_config",
            errors,
        )
        if service_config is not None:
            service_check = service_config_result(
                service_config,
                root=output_dir,
                check_runtime=check_runtime,
            )
            errors.extend(
                f"service_config: {error}" for error in service_check["errors"]
            )
            if paths.get("corpus") != service_config.get("corpus"):
                errors.append("paths.corpus: does not match service config corpus")

    if profile_check is not None:
        if summary.get("profile_status") != profile_check["status"]:
            errors.append(
                "summary.profile_status: does not match recomputed profile status"
            )
    if service_check is not None:
        if summary.get("service_config_status") != service_check["status"]:
            errors.append(
                "summary.service_config_status: does not match recomputed service status"
            )

    computed_status = (
        "ready"
        if profile_check is not None
        and service_check is not None
        and profile_check["status"] == "ready"
        and service_check["status"] == "ready"
        else "blocked"
    )
    if manifest.get("status") != computed_status:
        errors.append("status: does not match recomputed bootstrap status")

    return {
        "schema": BOOTSTRAP_VERIFICATION_SCHEMA,
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "verified_dir": _path(output_dir),
        "manifest_path": _path(manifest_path),
        "manifest_status": manifest.get("status", "unknown"),
        "manifest_schema_status": "passed" if not manifest_errors else "failed",
        "profile_status": (
            profile_check["status"] if profile_check is not None else "skipped"
        ),
        "service_config_status": (
            service_check["status"] if service_check is not None else "skipped"
        ),
        "runtime_status": (
            service_check["runtime_status"] if service_check is not None else "skipped"
        ),
        "resolved_paths": resolved_paths,
    }


def _render_readme(manifest: dict[str, Any]) -> str:
    paths = manifest["paths"]
    commands = manifest["commands"]
    summary = manifest["summary"]
    lines = [
        "# RDLLM Operator Bootstrap",
        "",
        "Generated files:",
        f"- operator profile: `{paths['operator_profile']}`",
        f"- readiness report: `{paths['readiness_report']}`",
        f"- service config: `{paths['service_config']}`",
        f"- bootstrap manifest: `{paths['manifest']}`",
        "",
        "Generated directories:",
        f"- proof artifacts: `{paths['artifact_dir']}`",
        f"- runtime state: `{paths['runtime_dir']}`",
        "",
        "Status:",
        f"- profile status: `{summary['profile_status']}`",
        f"- service config status: `{summary['service_config_status']}`",
        f"- settlement mode: `{summary['settlement_mode']}`",
        "- direct creator settlement allowed: "
        f"`{json.dumps(summary['direct_creator_settlement_allowed'])}`",
        "- sample corpus included: "
        f"`{json.dumps(summary['sample_corpus_included'])}`",
        "- reference artifacts included: "
        f"`{json.dumps(summary['reference_artifacts_included'])}`",
        "",
        "Next commands:",
        f"```bash\nrdllm-operator-bootstrap --verify-dir {paths['output_dir']}\n```",
        f"```bash\n{commands['validate_profile']}\n```",
        f"```bash\n{commands['validate_service_config']}\n```",
        f"```bash\n{commands['start_service']}\n```",
        "",
        "Before routing production traffic, replace sample or reference artifacts "
        "with operator-controlled production artifacts when applicable, set the "
        "bearer token hash environment variable, and require `/readyz` to report "
        "ready.",
        "",
    ]
    return "\n".join(lines)


def bootstrap_operator(
    *,
    output_dir: Path,
    operator_template: str,
    operator_name: str,
    security_contact: str,
    corpus: str | None = None,
    service_template: str = "default",
    deployment_id: str | None = None,
    deployment_region_policy: str | None = None,
    artifact_dir: str | None = None,
    audit_log_path: str | None = None,
    token_sha256_env: str = "RDLLM_SERVICE_TOKEN_SHA256",
    provider_id: str | None = None,
    provider_base_url: str | None = None,
    provider_model: str | None = None,
    provider_api_key_env: str | None = None,
    include_sample_corpus: bool = False,
    include_reference_artifacts: bool = False,
    check_runtime: bool = False,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    runtime_dir = output_dir / "runtime"
    proof_artifact_dir = (
        Path(artifact_dir).resolve()
        if artifact_dir
        else output_dir / "artifacts"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    proof_artifact_dir.mkdir(parents=True, exist_ok=True)
    corpus_dir = output_dir / "corpus"

    profile_path = output_dir / "production_readiness_profile.json"
    report_path = output_dir / "production_readiness_report.json"
    service_config_path = output_dir / "service_config.json"
    manifest_path = output_dir / "operator_bootstrap_manifest.json"
    readme_path = output_dir / "README.md"
    copied_reference_artifacts: list[str] = []
    copied_sample_corpus = ""

    if include_sample_corpus:
        sample_corpus_path = corpus_dir / "sample_corpus.json"
        _copy_data_resource(SAMPLE_CORPUS_RESOURCE, sample_corpus_path)
        copied_sample_corpus = _path(sample_corpus_path)
        corpus = copied_sample_corpus
    if not corpus:
        raise ValueError("--corpus is required unless --include-sample-corpus is set")
    if include_reference_artifacts:
        copied_reference_artifacts = _copy_reference_artifacts(proof_artifact_dir)

    profile = create_profile(
        template=operator_template,
        operator_name=operator_name,
        security_contact=security_contact,
        deployment_id=deployment_id,
        deployment_region_policy=deployment_region_policy,
    )
    profile_check = profile_result(profile)
    write_profile_json(profile_path, profile)
    write_profile_json(report_path, profile_check["readiness_report"])

    service_config = create_service_config(
        template=service_template,
        corpus=corpus,
        audit_log_path=audit_log_path
        or _path(runtime_dir / "rdllm_service_audit.jsonl"),
        token_sha256_env=token_sha256_env,
        artifact_dir=_path(proof_artifact_dir),
        provider_id=provider_id,
        provider_base_url=provider_base_url,
        provider_model=provider_model,
        provider_api_key_env=provider_api_key_env,
    )
    service_check = service_config_result(
        service_config,
        root=output_dir,
        check_runtime=check_runtime,
    )
    write_service_json(service_config_path, service_config)

    profile_summary = profile_check["readiness_report"]["summary"]
    status = (
        "ready"
        if profile_check["status"] == "ready"
        and service_check["status"] == "ready"
        else "blocked"
    )
    manifest: dict[str, Any] = {
        "schema": BOOTSTRAP_SCHEMA,
        "status": status,
        "summary": {
            "operator_name": operator_name,
            "operator_template": operator_template,
            "service_template": service_template,
            "profile_status": profile_check["status"],
            "service_config_status": service_check["status"],
            "settlement_mode": profile_summary["settlement_mode"],
            "production_grade_claim_allowed": profile_summary[
                "production_grade_claim_allowed"
            ],
            "direct_creator_settlement_allowed": profile_summary[
                "direct_creator_settlement_allowed"
            ],
            "public_sector_use_supported": profile_summary[
                "public_sector_use_supported"
            ],
            "sample_corpus_included": bool(copied_sample_corpus),
            "reference_artifacts_included": bool(copied_reference_artifacts),
        },
        "paths": {
            "output_dir": _path(output_dir),
            "operator_profile": _path(profile_path),
            "readiness_report": _path(report_path),
            "service_config": _path(service_config_path),
            "artifact_dir": _path(proof_artifact_dir),
            "corpus": corpus,
            "runtime_dir": _path(runtime_dir),
            "manifest": _path(manifest_path),
            "readme": _path(readme_path),
        },
        "commands": {
            "validate_profile": (
                "rdllm-operator-profile validate "
                f"--profile {profile_path} --write-report {report_path}"
            ),
            "validate_service_config": (
                f"rdllm-service-config validate --config {service_config_path}"
            ),
            "start_service": f"rdllm-service --config {service_config_path}",
        },
        "errors": [
            *(f"profile: {error}" for error in profile_check["errors"]),
            *(f"service_config: {error}" for error in service_check["errors"]),
        ],
        "included_reference_artifacts": copied_reference_artifacts,
    }
    write_service_json(manifest_path, manifest)
    _write_text(readme_path, _render_readme(manifest))
    return manifest


def render_text(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    paths = manifest["paths"]
    lines = [
        f"operator_bootstrap status: {manifest['status']}",
        f"operator_name: {summary['operator_name']}",
        f"operator_template: {summary['operator_template']}",
        f"service_template: {summary['service_template']}",
        f"profile_status: {summary['profile_status']}",
        f"service_config_status: {summary['service_config_status']}",
        f"settlement_mode: {summary['settlement_mode']}",
        "direct_creator_settlement_allowed: "
        f"{json.dumps(summary['direct_creator_settlement_allowed'])}",
        "sample_corpus_included: "
        f"{json.dumps(summary['sample_corpus_included'])}",
        "reference_artifacts_included: "
        f"{json.dumps(summary['reference_artifacts_included'])}",
        f"output_dir: {paths['output_dir']}",
        f"manifest: {paths['manifest']}",
    ]
    if manifest.get("errors"):
        lines.append("errors:")
        lines.extend(f"- {error}" for error in manifest["errors"])
    return "\n".join(lines)


def render_verification_text(report: dict[str, Any]) -> str:
    lines = [
        f"operator_bootstrap_verification status: {report['status']}",
        f"manifest_status: {report['manifest_status']}",
        f"manifest_schema_status: {report['manifest_schema_status']}",
        f"profile_status: {report['profile_status']}",
        f"service_config_status: {report['service_config_status']}",
        f"runtime_status: {report['runtime_status']}",
        f"verified_dir: {report['verified_dir']}",
        f"manifest_path: {report['manifest_path']}",
    ]
    if report.get("errors"):
        lines.append("errors:")
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--verify-dir",
        type=Path,
        help="Verify a generated operator bootstrap directory.",
    )
    parser.add_argument(
        "--operator-template",
        choices=sorted(PROFILE_TEMPLATES),
    )
    parser.add_argument("--operator-name")
    parser.add_argument("--security-contact")
    parser.add_argument("--corpus")
    parser.add_argument(
        "--service-template",
        choices=sorted(SERVICE_TEMPLATES),
        default="default",
    )
    parser.add_argument("--deployment-id")
    parser.add_argument("--deployment-region-policy")
    parser.add_argument("--artifact-dir")
    parser.add_argument("--audit-log-path")
    parser.add_argument("--token-sha256-env", default="RDLLM_SERVICE_TOKEN_SHA256")
    parser.add_argument("--provider-id")
    parser.add_argument("--provider-base-url")
    parser.add_argument("--provider-model")
    parser.add_argument("--provider-api-key-env")
    parser.add_argument("--include-sample-corpus", action="store_true")
    parser.add_argument("--include-reference-artifacts", action="store_true")
    parser.add_argument("--check-runtime", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.verify_dir is not None:
        report = verify_bootstrap_dir(
            args.verify_dir,
            check_runtime=args.check_runtime,
        )
        print(
            json.dumps(report, indent=2, sort_keys=True)
            if args.json
            else render_verification_text(report)
        )
        return 0 if report["status"] == "passed" else 1

    if args.output_dir is None:
        parser.error("--output-dir is required unless --verify-dir is set")
    if args.operator_template is None:
        parser.error("--operator-template is required unless --verify-dir is set")
    if args.operator_name is None:
        parser.error("--operator-name is required unless --verify-dir is set")
    if args.security_contact is None:
        parser.error("--security-contact is required unless --verify-dir is set")

    try:
        manifest = bootstrap_operator(
            output_dir=args.output_dir,
            operator_template=args.operator_template,
            operator_name=args.operator_name,
            security_contact=args.security_contact,
            corpus=args.corpus,
            service_template=args.service_template,
            deployment_id=args.deployment_id,
            deployment_region_policy=args.deployment_region_policy,
            artifact_dir=args.artifact_dir,
            audit_log_path=args.audit_log_path,
            token_sha256_env=args.token_sha256_env,
            provider_id=args.provider_id,
            provider_base_url=args.provider_base_url,
            provider_model=args.provider_model,
            provider_api_key_env=args.provider_api_key_env,
            include_sample_corpus=args.include_sample_corpus,
            include_reference_artifacts=args.include_reference_artifacts,
            check_runtime=args.check_runtime,
        )
    except ValueError as exc:
        parser.error(str(exc))
        return 2
    print(
        json.dumps(manifest, indent=2, sort_keys=True)
        if args.json
        else render_text(manifest)
    )
    return 0 if manifest["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
