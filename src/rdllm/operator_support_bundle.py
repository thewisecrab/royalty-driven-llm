"""Create a redacted RDLLM operator diagnostic support bundle."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from importlib import resources
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import platform
import re
import sys
from typing import Any

from rdllm.operator_bootstrap import verify_bootstrap_dir
from rdllm.operator_doctor import run_doctor
from rdllm.service_config import service_config_result
from rdllm.service_response_verifier import load_json, verify_service_response


SUPPORT_BUNDLE_SCHEMA = "rdllm-operator-support-bundle/v1"
SUPPORT_BUNDLE_SCHEMA_RESOURCE = ("schemas", "operator_support_bundle.schema.json")
DATA_PACKAGE = "rdllm.data"
PACKAGE_NAME = "royalty-driven-llm"
PATH_REDACTION = "[redacted:path]"
EMAIL_REDACTION = "[redacted:email]"


def load_support_bundle_schema() -> dict[str, Any]:
    resource = resources.files(DATA_PACKAGE).joinpath(*SUPPORT_BUNDLE_SCHEMA_RESOURCE)
    return json.loads(resource.read_text(encoding="utf-8"))


def _package_version() -> str:
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return "unknown"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _redact_string(value: str) -> str:
    value = re.sub(
        r"(?<![:/])\/(?:[^\s,;:)]+\/)+[^\s,;:)]+",
        PATH_REDACTION,
        value,
    )
    return re.sub(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        EMAIL_REDACTION,
        value,
    )


def _redacted_errors(errors: Any) -> list[str]:
    if not isinstance(errors, list):
        return []
    return [_redact_string(str(error)) for error in errors]


def _status_ok(status: str) -> bool:
    return status in {"passed", "ready", "skipped"}


def _section_status(section: dict[str, Any]) -> str:
    status = section.get("status", "unknown")
    return status if isinstance(status, str) else "unknown"


def _service_config_public_summary(config: dict[str, Any]) -> dict[str, Any]:
    auth = config.get("auth", {})
    artifacts = config.get("artifacts", {})
    limits = config.get("limits", {})
    providers = config.get("providers", [])
    return {
        "schema": str(config.get("schema", "")),
        "auth_mode": str(auth.get("mode", "")) if isinstance(auth, dict) else "",
        "auth_token_configured": (
            isinstance(auth, dict)
            and bool(auth.get("token_sha256_env") or auth.get("token_sha256"))
        ),
        "provider_count": len(providers) if isinstance(providers, list) else 0,
        "artifact_count": len(artifacts) if isinstance(artifacts, dict) else 0,
        "corpus_configured": bool(config.get("corpus")),
        "audit_log_configured": bool(config.get("audit_log_path")),
        "runtime_limits_configured": isinstance(limits, dict) and bool(limits),
    }


def _doctor_summary(report: dict[str, Any]) -> dict[str, Any]:
    bootstrap = report.get("bootstrap", {})
    response = report.get("response", {})
    package_resources = report.get("package_resources", {})
    profile_templates = report.get("profile_templates", {})
    return {
        "schema": str(report.get("schema", "")),
        "status": _section_status(report),
        "errors": _redacted_errors(report.get("errors", [])),
        "package_resources": {
            "status": _section_status(package_resources),
            "checks": package_resources.get("checks", {})
            if isinstance(package_resources.get("checks"), dict)
            else {},
            "errors": _redacted_errors(package_resources.get("errors", [])),
        },
        "profile_templates": {
            "status": _section_status(profile_templates),
            "profile_statuses": profile_templates.get("profile_statuses", {})
            if isinstance(profile_templates.get("profile_statuses"), dict)
            else {},
            "errors": _redacted_errors(profile_templates.get("errors", [])),
        },
        "bootstrap": {
            "status": _section_status(bootstrap),
            "manifest_status": str(bootstrap.get("manifest_status", "")),
            "verification_status": str(bootstrap.get("verification_status", "")),
            "runtime_status": str(bootstrap.get("runtime_status", "")),
            "errors": _redacted_errors(bootstrap.get("errors", [])),
        },
        "response": {
            "status": _section_status(response),
            "response_status": str(response.get("response_status", "")),
            "verification_status": str(response.get("verification_status", "")),
            "event_hash": str(response.get("event_hash", "")),
            "footer_hash": str(response.get("footer_hash", "")),
            "display_hash": str(response.get("display_hash", "")),
            "errors": _redacted_errors(response.get("errors", [])),
        },
    }


def _bootstrap_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": str(report.get("schema", "")),
        "status": _section_status(report),
        "errors": _redacted_errors(report.get("errors", [])),
        "manifest_status": str(report.get("manifest_status", "")),
        "manifest_schema_status": str(report.get("manifest_schema_status", "")),
        "profile_status": str(report.get("profile_status", "")),
        "service_config_status": str(report.get("service_config_status", "")),
        "runtime_status": str(report.get("runtime_status", "")),
    }


def _service_config_summary(
    config_path: Path,
    *,
    root: Path | None,
    check_runtime: bool,
) -> dict[str, Any]:
    try:
        config = load_json(config_path)
    except Exception as exc:
        return {
            "status": "failed",
            "errors": [
                f"service_config: failed to read JSON: {_redact_string(str(exc))}"
            ],
            "schema_status": "failed",
            "runtime_status": "skipped",
            "public_summary": {},
        }
    result = service_config_result(
        config,
        root=(root or config_path.parent),
        check_runtime=check_runtime,
    )
    return {
        "status": result["status"],
        "errors": _redacted_errors(result.get("errors", [])),
        "schema_status": str(result.get("schema_status", "")),
        "runtime_status": str(result.get("runtime_status", "")),
        "public_summary": _service_config_public_summary(config),
    }


def _response_summary(response_path: Path) -> dict[str, Any]:
    try:
        response = load_json(response_path)
    except Exception as exc:
        return {
            "schema": "rdllm-service-response-verification/v1",
            "status": "failed",
            "errors": [f"response: failed to read JSON: {_redact_string(str(exc))}"],
            "event_id": "",
            "event_hash": "",
            "footer_hash": "",
            "display_hash": "",
            "source_count": 0,
            "claim_count": 0,
            "grounding_verdict": "",
            "attribution_gap_verdict": "",
        }
    report = verify_service_response(response)
    report["errors"] = _redacted_errors(report.get("errors", []))
    return report


def _acceptance_summary(report_path: Path) -> dict[str, Any]:
    from rdllm.operator_acceptance import verify_acceptance_report

    try:
        report = load_json(report_path)
    except Exception as exc:
        return {
            "schema": "rdllm-operator-acceptance-verification/v1",
            "status": "failed",
            "errors": [
                f"acceptance_report: failed to read JSON: {_redact_string(str(exc))}"
            ],
            "acceptance_status": "unknown",
            "production_acceptance_decision": "unknown",
            "traffic_decision": "unknown",
            "recorded_acceptance_report_hash": "",
            "computed_acceptance_report_hash": "",
        }
    verification = verify_acceptance_report(report)
    verification["errors"] = _redacted_errors(verification.get("errors", []))
    return verification


def _redaction_policy() -> dict[str, Any]:
    return {
        "raw_prompts_included": False,
        "raw_outputs_included": False,
        "raw_source_text_included": False,
        "evidence_previews_included": False,
        "rendered_footers_included": False,
        "tokens_or_api_keys_included": False,
        "payment_account_details_included": False,
        "local_paths_included": False,
        "retained_fields": [
            "status",
            "schema_status",
            "runtime_status",
            "event_hash",
            "footer_hash",
            "display_hash",
            "acceptance_report_hash",
            "source_count",
            "claim_count",
            "error_messages_with_paths_and_emails_redacted",
        ],
    }


def _environment() -> dict[str, Any]:
    return {
        "package": {
            "name": PACKAGE_NAME,
            "version": _package_version(),
        },
        "python": {
            "version": sys.version.split()[0],
            "implementation": platform.python_implementation(),
        },
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
        },
    }


def run_support_bundle(
    *,
    bootstrap_dir: Path | None = None,
    service_config: Path | None = None,
    service_root: Path | None = None,
    response: Path | None = None,
    acceptance_report: Path | None = None,
    check_runtime: bool = False,
    run_installed_doctor: bool = True,
) -> dict[str, Any]:
    sections: dict[str, dict[str, Any]] = {}
    checks_run: list[str] = []

    if run_installed_doctor:
        try:
            sections["doctor"] = _doctor_summary(run_doctor())
        except Exception as exc:
            sections["doctor"] = {
                "status": "failed",
                "errors": [f"doctor: failed to run: {_redact_string(str(exc))}"],
            }
        checks_run.append("doctor")
    else:
        sections["doctor"] = {"status": "skipped", "errors": []}

    if bootstrap_dir is not None:
        sections["bootstrap_verification"] = _bootstrap_summary(
            verify_bootstrap_dir(bootstrap_dir, check_runtime=check_runtime)
        )
        checks_run.append("bootstrap_verification")

    if service_config is not None:
        sections["service_config_validation"] = _service_config_summary(
            service_config,
            root=service_root,
            check_runtime=check_runtime,
        )
        checks_run.append("service_config_validation")

    if response is not None:
        sections["response_verification"] = _response_summary(response)
        checks_run.append("response_verification")

    if acceptance_report is not None:
        sections["acceptance_verification"] = _acceptance_summary(acceptance_report)
        checks_run.append("acceptance_verification")

    errors: list[str] = []
    for name in checks_run:
        section = sections[name]
        if not _status_ok(_section_status(section)):
            section_errors = section.get("errors", [])
            if section_errors:
                errors.extend(f"{name}: {error}" for error in section_errors)
            else:
                errors.append(f"{name}: status {_section_status(section)}")

    return {
        "schema": SUPPORT_BUNDLE_SCHEMA,
        "status": "passed" if checks_run and not errors else "failed",
        "generated_at": _utc_now(),
        "errors": errors,
        "checks_run": checks_run,
        "environment": _environment(),
        "redaction": _redaction_policy(),
        **sections,
    }


def render_text(report: dict[str, Any], *, output_path: Path | None = None) -> str:
    lines = [
        f"operator_support_bundle status: {report['status']}",
        "checks_run: " + ", ".join(report.get("checks_run", [])),
        f"doctor_status: {report.get('doctor', {}).get('status', 'skipped')}",
    ]
    if "bootstrap_verification" in report:
        lines.append(
            "bootstrap_verification_status: "
            f"{report['bootstrap_verification']['status']}"
        )
    if "service_config_validation" in report:
        lines.append(
            "service_config_status: "
            f"{report['service_config_validation']['status']}"
        )
    if "response_verification" in report:
        lines.append(
            "response_verification_status: "
            f"{report['response_verification']['status']}"
        )
    if "acceptance_verification" in report:
        lines.append(
            "acceptance_verification_status: "
            f"{report['acceptance_verification']['status']}"
        )
    if output_path is not None:
        lines.append(f"bundle_written: {output_path}")
    lines.append(
        "redaction: raw prompts, outputs, source text, tokens, API keys, "
        "payment account details, and local paths excluded"
    )
    if report.get("errors"):
        lines.append("errors:")
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap-dir", type=Path)
    parser.add_argument("--service-config", type=Path)
    parser.add_argument("--service-root", type=Path)
    parser.add_argument("--response", type=Path)
    parser.add_argument("--acceptance-report", type=Path)
    parser.add_argument("--check-runtime", action="store_true")
    parser.add_argument(
        "--skip-doctor",
        action="store_true",
        help="Do not run the packaged operator doctor self-test.",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = run_support_bundle(
        bootstrap_dir=args.bootstrap_dir,
        service_config=args.service_config,
        service_root=args.service_root,
        response=args.response,
        acceptance_report=args.acceptance_report,
        check_runtime=args.check_runtime,
        run_installed_doctor=not args.skip_doctor,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(report, indent=2, sort_keys=True)
        if args.json
        else render_text(report, output_path=args.output)
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
