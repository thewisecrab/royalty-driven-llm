"""Run a fail-closed RDLLM operator launch gate."""

from __future__ import annotations

import argparse
import json
from importlib import resources
from pathlib import Path
from typing import Any

from rdllm.operator_bootstrap import verify_bootstrap_dir
from rdllm.operator_support_bundle import run_support_bundle
from rdllm.production_readiness import (
    evaluate_production_profile,
    load_json,
    verify_production_readiness_report,
)
from rdllm.service_config import service_config_result
from rdllm.service_response_verifier import verify_service_response


LAUNCH_GATE_SCHEMA = "rdllm-operator-launch-gate/v1"
LAUNCH_GATE_SCHEMA_RESOURCE = ("schemas", "operator_launch_gate.schema.json")
DATA_PACKAGE = "rdllm.data"


def load_launch_gate_schema() -> dict[str, Any]:
    resource = resources.files(DATA_PACKAGE).joinpath(*LAUNCH_GATE_SCHEMA_RESOURCE)
    return json.loads(resource.read_text(encoding="utf-8"))


def _status_ok(status: str) -> bool:
    return status in {"ready", "passed", "skipped"}


def _section_status(section: dict[str, Any]) -> str:
    status = section.get("status", "unknown")
    return status if isinstance(status, str) else "unknown"


def _public_service_summary(config: dict[str, Any]) -> dict[str, Any]:
    auth = config.get("auth", {})
    limits = config.get("limits", {})
    artifacts = config.get("artifacts", {})
    providers = config.get("providers", [])
    return {
        "schema": str(config.get("schema", "")),
        "auth_mode": str(auth.get("mode", "")) if isinstance(auth, dict) else "",
        "auth_configured": (
            isinstance(auth, dict)
            and bool(auth.get("token_sha256_env") or auth.get("token_sha256"))
        ),
        "rate_limit_configured": (
            isinstance(limits, dict)
            and int(limits.get("rate_limit_requests_per_window", 0) or 0) > 0
            and int(limits.get("rate_limit_window_seconds", 0) or 0) > 0
        ),
        "artifact_count": len(artifacts) if isinstance(artifacts, dict) else 0,
        "provider_count": len(providers) if isinstance(providers, list) else 0,
        "corpus_configured": bool(config.get("corpus")),
        "audit_log_configured": bool(config.get("audit_log_path")),
    }


def _profile_section(
    profile_path: Path,
    trust_store_path: Path | None = None,
) -> dict[str, Any]:
    try:
        profile = load_json(profile_path)
    except Exception as exc:
        return {
            "status": "blocked",
            "errors": [f"profile: failed to read JSON: {exc}"],
            "summary": {},
            "blocked_controls": [],
            "profile_hash": "",
        }
    try:
        trust_store = load_json(trust_store_path) if trust_store_path else None
    except Exception as exc:
        return {
            "status": "blocked",
            "errors": [f"trust_store: failed to read JSON: {exc}"],
            "summary": {},
            "blocked_controls": [],
            "profile_hash": "",
        }
    report = evaluate_production_profile(profile, trust_store=trust_store)
    verification = verify_production_readiness_report(
        profile,
        report,
        trust_store=trust_store,
    )
    errors = list(verification["errors"])
    summary = report["summary"]
    if summary["status"] != "ready":
        errors.extend(
            f"{row['control_id']}: {row['requirement']}"
            for row in report["blocked_controls"]
        )
    return {
        "status": "ready" if not errors else "blocked",
        "errors": errors,
        "summary": {
            "profile_status": summary["status"],
            "operator_type": summary.get("operator_type"),
            "settlement_mode": summary.get("settlement_mode"),
            "external_evidence_status": summary.get("external_evidence_status"),
            "production_grade_claim_allowed": summary[
                "production_grade_claim_allowed"
            ],
            "direct_creator_settlement_allowed": summary[
                "direct_creator_settlement_allowed"
            ],
            "public_sector_use_supported": summary["public_sector_use_supported"],
            "ready_control_count": summary["ready_control_count"],
            "blocked_control_count": summary["blocked_control_count"],
        },
        "blocked_controls": report["blocked_controls"],
        "profile_hash": report["profile_hash"],
    }


def _service_config_section(
    service_config_path: Path,
    *,
    service_root: Path | None,
    check_runtime: bool,
) -> dict[str, Any]:
    try:
        config = load_json(service_config_path)
    except Exception as exc:
        return {
            "status": "blocked",
            "errors": [f"service_config: failed to read JSON: {exc}"],
            "schema_status": "failed",
            "runtime_status": "skipped",
            "public_summary": {},
        }
    result = service_config_result(
        config,
        root=service_root or service_config_path.parent,
        check_runtime=check_runtime,
    )
    return {
        "status": result["status"],
        "errors": result["errors"],
        "schema_status": result["schema_status"],
        "runtime_status": result["runtime_status"],
        "public_summary": _public_service_summary(config),
    }


def _empty_response_report(
    *,
    status: str,
    errors: list[str],
    display_text: Path | None,
    display_text_status: str = "not_checked",
) -> dict[str, Any]:
    return {
        "schema": "rdllm-service-response-verification/v1",
        "status": status,
        "errors": errors,
        "event_id": "",
        "event_hash": "",
        "footer_hash": "",
        "display_hash": "",
        "display_text_status": display_text_status,
        "display_text_hash": "",
        "display_text_path": str(display_text) if display_text is not None else "",
        "source_count": 0,
        "claim_count": 0,
        "response_status": "unknown",
        "production_display_ready": False,
        "grounding_verdict": "",
        "attribution_gap_verdict": "",
    }


def _fail_response_report(
    report: dict[str, Any],
    error: str,
    *,
    display_text_status: str | None = None,
    display_text_hash: str | None = None,
    display_text_path: str | None = None,
) -> dict[str, Any]:
    failed = dict(report)
    errors = list(failed.get("errors", []))
    errors.append(error)
    failed["errors"] = errors
    failed["status"] = "failed"
    failed["production_display_ready"] = False
    if display_text_status is not None:
        failed["display_text_status"] = display_text_status
    if display_text_hash is not None:
        failed["display_text_hash"] = display_text_hash
    if display_text_path is not None:
        failed["display_text_path"] = display_text_path
    return failed


def _response_section(
    response_path: Path | None,
    *,
    display_text: Path | None,
    skip_response: bool,
) -> dict[str, Any]:
    if response_path is None:
        return _empty_response_report(
            status="skipped" if skip_response else "failed",
            errors=[] if skip_response else ["response: saved response is required"],
            display_text=display_text,
        )
    try:
        response = load_json(response_path)
    except Exception as exc:
        return _empty_response_report(
            status="failed",
            errors=[f"response: failed to read JSON: {exc}"],
            display_text=display_text,
        )

    if display_text is None:
        report = verify_service_response(response)
        report = _fail_response_report(
            report,
            "display_text: copied/exported display text is required for production launch",
            display_text_status="failed",
            display_text_hash="",
            display_text_path="",
        )
    else:
        display_text_path = str(display_text)
        try:
            copied_text = display_text.read_text(encoding="utf-8")
        except Exception as exc:
            report = verify_service_response(response)
            report = _fail_response_report(
                report,
                f"display_text: failed to read text: {exc}",
                display_text_status="failed",
                display_text_hash="",
                display_text_path=display_text_path,
            )
        else:
            report = verify_service_response(
                response,
                display_text=copied_text,
                display_text_path=display_text_path,
            )

    if response.get("status") != "ready":
        report = _fail_response_report(
            report,
            "response.status: expected ready for production display, "
            f"got {response.get('status', '<missing>')}",
        )
    return report


def _bootstrap_section(
    bootstrap_dir: Path | None,
    *,
    check_runtime: bool,
) -> dict[str, Any]:
    if bootstrap_dir is None:
        return {"status": "skipped", "errors": []}
    return verify_bootstrap_dir(bootstrap_dir, check_runtime=check_runtime)


def run_launch_gate(
    *,
    profile: Path,
    service_config: Path,
    service_root: Path | None = None,
    bootstrap_dir: Path | None = None,
    response: Path | None = None,
    display_text: Path | None = None,
    check_runtime: bool = True,
    skip_response: bool = False,
    support_bundle_output: Path | None = None,
    trust_store: Path | None = None,
) -> dict[str, Any]:
    profile_report = _profile_section(profile, trust_store)
    service_report = _service_config_section(
        service_config,
        service_root=service_root,
        check_runtime=check_runtime,
    )
    bootstrap_report = _bootstrap_section(
        bootstrap_dir,
        check_runtime=check_runtime,
    )
    response_report = _response_section(
        response,
        display_text=display_text,
        skip_response=skip_response,
    )

    support_report: dict[str, Any] = {"status": "skipped", "errors": []}
    if support_bundle_output is not None:
        support_report = run_support_bundle(
            bootstrap_dir=bootstrap_dir,
            service_config=service_config,
            service_root=service_root,
            response=response,
            check_runtime=check_runtime,
            run_installed_doctor=True,
        )
        support_bundle_output.parent.mkdir(parents=True, exist_ok=True)
        support_bundle_output.write_text(
            json.dumps(support_report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    sections = {
        "profile": profile_report,
        "service_config": service_report,
        "bootstrap_verification": bootstrap_report,
        "response_verification": response_report,
        "support_bundle": {
            "status": support_report.get("status", "unknown"),
            "errors": support_report.get("errors", []),
            "written": support_bundle_output is not None,
        },
    }
    errors: list[str] = []
    for name, section in sections.items():
        if not _status_ok(_section_status(section)):
            section_errors = section.get("errors", [])
            if section_errors:
                errors.extend(f"{name}: {error}" for error in section_errors)
            else:
                errors.append(f"{name}: status {_section_status(section)}")

    summary = {
        "profile_status": profile_report["status"],
        "service_config_status": service_report["status"],
        "service_runtime_status": service_report["runtime_status"],
        "bootstrap_verification_status": bootstrap_report["status"],
        "response_verification_status": response_report["status"],
        "display_text_status": response_report.get("display_text_status", "not_checked"),
        "support_bundle_status": sections["support_bundle"]["status"],
        "production_grade_claim_allowed": (
            not errors
            and profile_report["summary"].get("production_grade_claim_allowed")
            is True
        ),
        "direct_creator_settlement_allowed": (
            not errors
            and profile_report["summary"].get("direct_creator_settlement_allowed")
            is True
        ),
        "public_sector_use_supported": (
            not errors
            and profile_report["summary"].get("public_sector_use_supported") is True
        ),
        "traffic_decision": "allow" if not errors else "block",
        "response_required": not skip_response,
        "display_text_required": not skip_response,
        "runtime_checked": check_runtime,
    }
    return {
        "schema": LAUNCH_GATE_SCHEMA,
        "status": "ready" if not errors else "blocked",
        "errors": errors,
        "summary": summary,
        **sections,
    }


def render_text(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        f"operator_launch_gate status: {report['status']}",
        f"traffic_decision: {summary['traffic_decision']}",
        f"profile_status: {summary['profile_status']}",
        f"service_config_status: {summary['service_config_status']}",
        f"service_runtime_status: {summary['service_runtime_status']}",
        f"bootstrap_verification_status: {summary['bootstrap_verification_status']}",
        f"response_verification_status: {summary['response_verification_status']}",
        f"display_text_status: {summary['display_text_status']}",
        f"support_bundle_status: {summary['support_bundle_status']}",
        "production_grade_claim_allowed: "
        f"{json.dumps(summary['production_grade_claim_allowed'])}",
        "direct_creator_settlement_allowed: "
        f"{json.dumps(summary['direct_creator_settlement_allowed'])}",
        "public_sector_use_supported: "
        f"{json.dumps(summary['public_sector_use_supported'])}",
    ]
    if report["errors"]:
        lines.append("errors:")
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--service-config", type=Path, required=True)
    parser.add_argument(
        "--trust-store",
        type=Path,
        help="Externally managed trust store used to verify deployment attestations.",
    )
    parser.add_argument("--service-root", type=Path)
    parser.add_argument("--bootstrap-dir", type=Path)
    parser.add_argument("--response", type=Path)
    parser.add_argument(
        "--display-text",
        type=Path,
        help=(
            "Copied or exported public answer text. Required whenever a saved "
            "response is used for a production launch gate."
        ),
    )
    parser.add_argument(
        "--skip-runtime",
        action="store_true",
        help="Validate schemas without checking corpus, token, and artifact readiness.",
    )
    parser.add_argument(
        "--skip-response",
        action="store_true",
        help="Allow config/profile preflight without a saved attribution response.",
    )
    parser.add_argument("--write-support-bundle", type=Path)
    parser.add_argument("--write-report", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = run_launch_gate(
        profile=args.profile,
        service_config=args.service_config,
        service_root=args.service_root,
        bootstrap_dir=args.bootstrap_dir,
        response=args.response,
        display_text=args.display_text,
        check_runtime=not args.skip_runtime,
        skip_response=args.skip_response,
        support_bundle_output=args.write_support_bundle,
        trust_store=args.trust_store,
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
    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
