"""Run an installed RDLLM operator self-test."""

from __future__ import annotations

import argparse
import hashlib
from importlib import resources
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from rdllm.operator_bootstrap import (
    bootstrap_operator,
    load_bootstrap_schema,
    load_bootstrap_verification_schema,
    verify_bootstrap_dir,
)
from rdllm.operator_profile import (
    TEMPLATE_RESOURCES as PROFILE_TEMPLATES,
    create_profile,
    load_profile_schema,
    load_profile_verification_schema,
    profile_result,
)
from rdllm.production_readiness import load_repository_report_schema
from rdllm.service import ServiceConfig, ServiceState, _attribute, load_json
from rdllm.service_config import (
    TEMPLATE_RESOURCES as SERVICE_TEMPLATES,
    load_service_config_verification_schema,
    load_service_schema,
    load_service_template,
)
from rdllm.service_response_verifier import (
    load_response_schema,
    verify_service_response,
)


DOCTOR_SCHEMA = "rdllm-operator-doctor/v1"
DOCTOR_SCHEMA_RESOURCE = ("schemas", "operator_doctor.schema.json")
DATA_PACKAGE = "rdllm.data"
DOCTOR_TOKEN = "rdllm-operator-doctor-token"
DOCTOR_TOKEN_ENV = "RDLLM_OPERATOR_DOCTOR_TOKEN_SHA256"
DOCTOR_RESPONSE_OUTPUT = (
    "Every royalty bearing AI answer should have a provenance record. "
    "The record should include source identifiers, content hashes, retrieval "
    "scores, output citations, payout weights, and an event hash that allows "
    "auditors to replay the attribution."
)


def load_doctor_schema() -> dict[str, Any]:
    resource = resources.files(DATA_PACKAGE).joinpath(*DOCTOR_SCHEMA_RESOURCE)
    return json.loads(resource.read_text(encoding="utf-8"))


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _status_from_errors(errors: list[str]) -> str:
    return "passed" if not errors else "failed"


def _check_package_resources() -> dict[str, Any]:
    errors: list[str] = []
    checks: dict[str, str] = {}

    def load_acceptance_matrix_schema_resource() -> dict[str, Any]:
        from rdllm.operator_acceptance_matrix import load_acceptance_matrix_schema

        return load_acceptance_matrix_schema()

    resource_loaders = {
        "bootstrap_schema": load_bootstrap_schema,
        "bootstrap_verification_schema": load_bootstrap_verification_schema,
        "acceptance_matrix_schema": load_acceptance_matrix_schema_resource,
        "doctor_schema": load_doctor_schema,
        "profile_schema": load_profile_schema,
        "profile_verification_schema": load_profile_verification_schema,
        "repository_readiness_schema": load_repository_report_schema,
        "service_schema": load_service_schema,
        "service_config_verification_schema": load_service_config_verification_schema,
        "response_schema": load_response_schema,
    }
    for name, loader in resource_loaders.items():
        try:
            loader()
        except Exception as exc:
            checks[name] = "failed"
            errors.append(f"{name}: failed to load: {exc}")
        else:
            checks[name] = "passed"

    for template in sorted(SERVICE_TEMPLATES):
        name = f"service_template:{template}"
        try:
            load_service_template(template)
        except Exception as exc:
            checks[name] = "failed"
            errors.append(f"{name}: failed to load: {exc}")
        else:
            checks[name] = "passed"

    return {
        "status": _status_from_errors(errors),
        "errors": errors,
        "checks": checks,
    }


def _check_profile_templates() -> dict[str, Any]:
    errors: list[str] = []
    statuses: dict[str, str] = {}
    for template in sorted(PROFILE_TEMPLATES):
        try:
            profile = create_profile(
                template=template,
                operator_name=f"RDLLM Doctor {template}",
                security_contact="security@example.com",
            )
            result = profile_result(profile)
        except Exception as exc:
            statuses[template] = "failed"
            errors.append(f"{template}: failed to evaluate: {exc}")
            continue
        statuses[template] = result["status"]
        errors.extend(f"{template}: {error}" for error in result["errors"])
    return {
        "status": "passed"
        if not errors and all(status == "ready" for status in statuses.values())
        else "failed",
        "errors": errors,
        "profile_statuses": statuses,
    }


def _run_bootstrap_check(output_dir: Path, operator_template: str) -> dict[str, Any]:
    old_token_hash = os.environ.get(DOCTOR_TOKEN_ENV)
    os.environ[DOCTOR_TOKEN_ENV] = _token_hash(DOCTOR_TOKEN)
    try:
        manifest = bootstrap_operator(
            output_dir=output_dir,
            operator_template=operator_template,
            operator_name="RDLLM Operator Doctor",
            security_contact="security@example.com",
            token_sha256_env=DOCTOR_TOKEN_ENV,
            include_sample_corpus=True,
            include_reference_artifacts=True,
            check_runtime=True,
        )
        verification = verify_bootstrap_dir(output_dir, check_runtime=True)
    finally:
        if old_token_hash is None:
            os.environ.pop(DOCTOR_TOKEN_ENV, None)
        else:
            os.environ[DOCTOR_TOKEN_ENV] = old_token_hash
    return {
        "status": "passed"
        if manifest["status"] == "ready" and verification["status"] == "passed"
        else "failed",
        "manifest_status": manifest["status"],
        "verification_status": verification["status"],
        "runtime_status": verification["runtime_status"],
        "errors": [*manifest["errors"], *verification["errors"]],
        "manifest_path": manifest["paths"]["manifest"],
    }


def _run_response_check(output_dir: Path) -> dict[str, Any]:
    old_token_hash = os.environ.get(DOCTOR_TOKEN_ENV)
    os.environ[DOCTOR_TOKEN_ENV] = _token_hash(DOCTOR_TOKEN)
    try:
        config = load_json(output_dir / "service_config.json")
        state = ServiceState.from_config(
            ServiceConfig(raw=config, root=output_dir.resolve())
        )
        status_code, response = _attribute(
            state,
            {
                "prompt": "What should royalty-bearing AI answers expose?",
                "output": DOCTOR_RESPONSE_OUTPUT,
                "gross_revenue": "1.00",
            },
        )
        response_path = output_dir / "service_response.json"
        response_path.write_text(
            json.dumps(response, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        verification = verify_service_response(response)
    finally:
        if old_token_hash is None:
            os.environ.pop(DOCTOR_TOKEN_ENV, None)
        else:
            os.environ[DOCTOR_TOKEN_ENV] = old_token_hash
    errors = []
    if status_code != 200:
        errors.append(f"service response returned HTTP {status_code}")
    errors.extend(verification["errors"])
    acceptance = verification.get("source_grounding_acceptance", {})
    if not isinstance(acceptance, dict):
        acceptance = {}
    return {
        "status": "passed"
        if not errors and verification["status"] == "passed"
        else "failed",
        "response_status": response.get("status", "unknown"),
        "verification_status": verification["status"],
        "production_display_ready": verification.get(
            "production_display_ready",
            False,
        ),
        "source_grounding_acceptance_status": acceptance.get("status", "unknown"),
        "event_hash": verification["event_hash"],
        "footer_hash": verification["footer_hash"],
        "display_hash": verification["display_hash"],
        "response_path": response_path.as_posix(),
        "errors": errors,
    }


def run_doctor(
    *,
    work_dir: Path | None = None,
    operator_template: str = "individual",
) -> dict[str, Any]:
    errors: list[str] = []
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    if work_dir is None:
        temp_dir = tempfile.TemporaryDirectory(prefix="rdllm-operator-doctor-")
        output_dir = Path(temp_dir.name) / "operator"
    else:
        output_dir = work_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

    try:
        resources = _check_package_resources()
        profiles = _check_profile_templates()
        try:
            bootstrap = _run_bootstrap_check(output_dir, operator_template)
        except Exception as exc:
            bootstrap = {
                "status": "failed",
                "manifest_status": "unknown",
                "verification_status": "failed",
                "runtime_status": "unknown",
                "errors": [f"bootstrap failed: {exc}"],
                "manifest_path": "",
            }
        try:
            response = _run_response_check(output_dir)
        except Exception as exc:
            response = {
                "status": "failed",
                "response_status": "unknown",
                "verification_status": "failed",
                "event_hash": "",
                "footer_hash": "",
                "display_hash": "",
                "response_path": "",
                "errors": [f"response verification failed: {exc}"],
            }
        for section_name, section in (
            ("package_resources", resources),
            ("profile_templates", profiles),
            ("bootstrap", bootstrap),
            ("response", response),
        ):
            errors.extend(
                f"{section_name}: {error}" for error in section.get("errors", [])
            )
        return {
            "schema": DOCTOR_SCHEMA,
            "status": _status_from_errors(errors),
            "errors": errors,
            "work_dir": output_dir.as_posix() if work_dir is not None else "",
            "package_resources": resources,
            "profile_templates": profiles,
            "bootstrap": bootstrap,
            "response": response,
        }
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"operator_doctor status: {report['status']}",
        f"package_resources_status: {report['package_resources']['status']}",
        f"profile_templates_status: {report['profile_templates']['status']}",
        f"bootstrap_status: {report['bootstrap']['status']}",
        f"bootstrap_runtime_status: {report['bootstrap']['runtime_status']}",
        f"response_status: {report['response']['status']}",
        "response_verification_status: "
        f"{report['response']['verification_status']}",
        "response_production_display_ready: "
        f"{json.dumps(bool(report['response'].get('production_display_ready', False)))}",
        "response_source_grounding_acceptance_status: "
        f"{report['response'].get('source_grounding_acceptance_status', 'unknown')}",
    ]
    if report.get("work_dir"):
        lines.append(f"work_dir: {report['work_dir']}")
    if report["errors"]:
        lines.append("errors:")
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument(
        "--operator-template",
        choices=sorted(PROFILE_TEMPLATES),
        default="individual",
    )
    parser.add_argument("--write-report", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = run_doctor(
        work_dir=args.work_dir,
        operator_template=args.operator_template,
    )
    if args.write_report:
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(report, indent=2, sort_keys=True)
        if args.json
        else render_text(report)
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
