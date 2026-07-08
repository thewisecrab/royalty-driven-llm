"""Run production acceptance across every supported RDLLM operator role."""

from __future__ import annotations

import argparse
from importlib import resources
import json
import os
from pathlib import Path
from typing import Any

from rdllm.operator_acceptance import run_acceptance_report, verify_acceptance_report
from rdllm.operator_bootstrap import bootstrap_operator
from rdllm.operator_recovery import create_recovery_manifest
from rdllm.service import (
    ServiceConfig,
    ServiceState,
    _append_audit_log,
    _attribute,
    canonical_hash,
    load_json,
    token_hash,
)


MATRIX_SCHEMA = "rdllm-operator-acceptance-matrix/v1"
MATRIX_SCHEMA_RESOURCE = ("schemas", "operator_acceptance_matrix.schema.json")
DATA_PACKAGE = "rdllm.data"
MATRIX_TOKEN = "rdllm-operator-acceptance-matrix-token"
MATRIX_TOKEN_ENV = "RDLLM_OPERATOR_ACCEPTANCE_MATRIX_TOKEN_SHA256"
RESPONSE_PROMPT = "What should royalty-bearing AI answers expose?"
RESPONSE_OUTPUT = (
    "Every royalty bearing AI answer should have a provenance record. "
    "The record should include source identifiers, content hashes, retrieval "
    "scores, output citations, payout weights, and an event hash that allows "
    "auditors to replay the attribution."
)
ROLE_EXPECTATIONS: dict[str, dict[str, Any]] = {
    "individual": {
        "settlement_mode": "escrow_only",
        "direct_creator_settlement_allowed": False,
        "public_sector_use_supported": False,
    },
    "company": {
        "settlement_mode": "instruction_only",
        "direct_creator_settlement_allowed": False,
        "public_sector_use_supported": False,
    },
    "institution": {
        "settlement_mode": "instruction_only",
        "direct_creator_settlement_allowed": False,
        "public_sector_use_supported": False,
    },
    "government": {
        "settlement_mode": "escrow_only",
        "direct_creator_settlement_allowed": False,
        "public_sector_use_supported": True,
    },
    "public_sector": {
        "settlement_mode": "processor_attested",
        "direct_creator_settlement_allowed": True,
        "public_sector_use_supported": True,
    },
}
REQUIRED_OPERATOR_TEMPLATES = tuple(ROLE_EXPECTATIONS)
REQUIRED_SETTLEMENT_MODES = {
    "escrow_only",
    "instruction_only",
    "processor_attested",
}


def load_acceptance_matrix_schema() -> dict[str, Any]:
    resource = resources.files(DATA_PACKAGE).joinpath(*MATRIX_SCHEMA_RESOURCE)
    return json.loads(resource.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _path(path: Path) -> str:
    return path.resolve().as_posix()


def _empty_role_row(
    *,
    operator_template: str,
    output_dir: Path,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "operator_template": operator_template,
        "status": "failed",
        "errors": errors,
        "output_dir": _path(output_dir),
        "acceptance_report_path": "",
        "response_path": "",
        "display_text_path": "",
        "audit_log_path": "",
        "recovery_manifest_path": "",
        "acceptance_status": "unknown",
        "acceptance_verification_status": "unknown",
        "production_acceptance_decision": "unknown",
        "traffic_decision": "unknown",
        "operator_type": "",
        "settlement_mode": "",
        "production_grade_claim_allowed": False,
        "direct_creator_settlement_allowed": False,
        "public_sector_use_supported": False,
        "response_production_display_ready": False,
        "response_display_text_status": "unknown",
        "response_display_text_hash": "",
        "source_grounding_acceptance_status": "unknown",
        "audit_response_binding_status": "unknown",
        "recovery_verification_status": "unknown",
        "acceptance_report_hash": "",
    }


def _write_ready_response(root: Path, operator_template: str) -> tuple[Path, Path, Path]:
    config = load_json(root / "service_config.json")
    state = ServiceState.from_config(ServiceConfig(raw=config, root=root))
    status_code, response = _attribute(
        state,
        {
            "prompt": RESPONSE_PROMPT,
            "output": RESPONSE_OUTPUT,
            "gross_revenue": "1.00",
        },
    )
    if status_code != 200 or response.get("status") != "ready":
        raise RuntimeError(
            "service attribution did not produce a ready response: "
            f"http={status_code}, status={response.get('status', 'unknown')}"
        )
    runtime_dir = root / "runtime"
    response_path = runtime_dir / "service_response.json"
    display_text_path = runtime_dir / "copied_display_text.txt"
    _write_json(response_path, response)
    display_text_path.write_text(
        str(response.get("display", {}).get("rendered_text", "")),
        encoding="utf-8",
    )
    _append_audit_log(
        state,
        request_id=f"operator-acceptance-matrix-{operator_template}",
        status=str(response["status"]),
        event_payload=response["event"],
        audit_errors=list(response.get("audit_errors", [])),
        source_footer_hash=str(
            response.get("summary", {}).get("source_footer_hash", "")
        ),
        display_hash=str(response.get("summary", {}).get("display_hash", "")),
    )
    audit_log_path = state.config.audit_log_path
    if audit_log_path is None:
        raise RuntimeError("service config did not define an audit log path")
    return response_path, display_text_path, audit_log_path


def _role_expectation_errors(row: dict[str, Any]) -> list[str]:
    template = str(row.get("operator_template", ""))
    expected = ROLE_EXPECTATIONS.get(template, {})
    errors: list[str] = []
    if row.get("acceptance_status") != "ready":
        errors.append("acceptance report was not ready")
    if row.get("acceptance_verification_status") != "passed":
        errors.append("acceptance verification did not pass")
    if row.get("production_acceptance_decision") != "allow":
        errors.append("production acceptance decision did not allow")
    if row.get("traffic_decision") != "allow":
        errors.append("traffic decision did not allow")
    if row.get("operator_type") != template:
        errors.append(
            f"operator_type {row.get('operator_type')!r} did not match template"
        )
    for field, expected_value in expected.items():
        if row.get(field) != expected_value:
            errors.append(
                f"{field}: expected {expected_value!r}, got {row.get(field)!r}"
            )
    if row.get("production_grade_claim_allowed") is not True:
        errors.append("production grade claim was not allowed")
    if row.get("response_production_display_ready") is not True:
        errors.append("response was not production display ready")
    if row.get("response_display_text_status") != "passed":
        errors.append("copied display text verification did not pass")
    if row.get("source_grounding_acceptance_status") != "passed":
        errors.append("source grounding acceptance did not pass")
    if row.get("audit_response_binding_status") != "passed":
        errors.append("audit response binding did not pass")
    if row.get("recovery_verification_status") != "passed":
        errors.append("recovery verification did not pass")
    return errors


def _run_role_acceptance(
    *,
    output_root: Path,
    operator_template: str,
    check_runtime: bool,
) -> dict[str, Any]:
    role_dir = output_root / operator_template
    try:
        manifest = bootstrap_operator(
            output_dir=role_dir,
            operator_template=operator_template,
            operator_name=f"RDLLM {operator_template.title()} Operator",
            security_contact="security@example.com",
            token_sha256_env=MATRIX_TOKEN_ENV,
            include_sample_corpus=True,
            include_reference_artifacts=True,
            check_runtime=check_runtime,
        )
        if manifest.get("status") != "ready":
            return _empty_role_row(
                operator_template=operator_template,
                output_dir=role_dir,
                errors=[
                    "bootstrap did not produce a ready operator root",
                    *list(manifest.get("errors", [])),
                ],
            )
        response_path, display_text_path, audit_log_path = _write_ready_response(
            role_dir,
            operator_template,
        )
        recovery_manifest = create_recovery_manifest(root=role_dir)
        recovery_manifest_path = role_dir / "runtime" / "recovery_manifest.json"
        _write_json(recovery_manifest_path, recovery_manifest)
        acceptance_report_path = role_dir / "runtime" / "acceptance_report.json"
        acceptance = run_acceptance_report(
            profile=role_dir / "production_readiness_profile.json",
            service_config=role_dir / "service_config.json",
            response=response_path,
            display_text=display_text_path,
            audit_log=audit_log_path,
            expected_audit_count=1,
            recovery_manifest=recovery_manifest_path,
            service_root=role_dir,
            bootstrap_dir=role_dir,
            recovery_root=role_dir,
            check_runtime=check_runtime,
        )
        _write_json(acceptance_report_path, acceptance)
        verification = verify_acceptance_report(acceptance)
    except Exception as exc:
        return _empty_role_row(
            operator_template=operator_template,
            output_dir=role_dir,
            errors=[f"{type(exc).__name__}: {exc}"],
        )

    summary = acceptance.get("summary", {})
    response_verification = (
        acceptance.get("launch_gate", {}).get("response_verification", {})
    )
    source_acceptance = response_verification.get(
        "source_grounding_acceptance",
        {},
    )
    row = {
        "operator_template": operator_template,
        "status": "passed",
        "errors": [],
        "output_dir": _path(role_dir),
        "acceptance_report_path": _path(acceptance_report_path),
        "response_path": _path(response_path),
        "display_text_path": _path(display_text_path),
        "audit_log_path": _path(audit_log_path),
        "recovery_manifest_path": _path(recovery_manifest_path),
        "acceptance_status": str(acceptance.get("status", "unknown")),
        "acceptance_verification_status": str(verification.get("status", "unknown")),
        "production_acceptance_decision": str(
            summary.get("production_acceptance_decision", "unknown")
        ),
        "traffic_decision": str(summary.get("traffic_decision", "unknown")),
        "operator_type": str(summary.get("operator_type", "")),
        "settlement_mode": str(summary.get("settlement_mode", "")),
        "production_grade_claim_allowed": bool(
            summary.get("production_grade_claim_allowed", False)
        ),
        "direct_creator_settlement_allowed": bool(
            summary.get("direct_creator_settlement_allowed", False)
        ),
        "public_sector_use_supported": bool(
            summary.get("public_sector_use_supported", False)
        ),
        "response_production_display_ready": bool(
            response_verification.get("production_display_ready", False)
        ),
        "response_display_text_status": str(
            response_verification.get("display_text_status", "unknown")
        ),
        "response_display_text_hash": str(
            response_verification.get("display_text_hash", "")
        ),
        "source_grounding_acceptance_status": str(
            source_acceptance.get("status", "unknown")
        ),
        "audit_response_binding_status": str(
            summary.get("audit_response_binding_status", "unknown")
        ),
        "recovery_verification_status": str(
            summary.get("recovery_verification_status", "unknown")
        ),
        "acceptance_report_hash": str(
            acceptance.get("acceptance_report_hash", "")
        ),
    }
    row["errors"] = [
        *list(acceptance.get("errors", [])),
        *[f"verification: {error}" for error in verification.get("errors", [])],
        *_role_expectation_errors(row),
    ]
    row["status"] = "passed" if not row["errors"] else "failed"
    return row


def run_acceptance_matrix(
    *,
    output_dir: Path,
    operator_templates: list[str] | None = None,
    check_runtime: bool = True,
) -> dict[str, Any]:
    output_root = output_dir.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    requested_templates = operator_templates or list(REQUIRED_OPERATOR_TEMPLATES)
    old_token_hash = os.environ.get(MATRIX_TOKEN_ENV)
    os.environ[MATRIX_TOKEN_ENV] = token_hash(MATRIX_TOKEN)
    try:
        rows = [
            _run_role_acceptance(
                output_root=output_root,
                operator_template=template,
                check_runtime=check_runtime,
            )
            for template in requested_templates
        ]
    finally:
        if old_token_hash is None:
            os.environ.pop(MATRIX_TOKEN_ENV, None)
        else:
            os.environ[MATRIX_TOKEN_ENV] = old_token_hash

    templates = {str(row.get("operator_template", "")) for row in rows}
    settlement_modes = {
        str(row.get("settlement_mode", ""))
        for row in rows
        if row.get("settlement_mode")
    }
    errors: list[str] = []
    for template in sorted(set(REQUIRED_OPERATOR_TEMPLATES) - templates):
        errors.append(f"missing operator template: {template}")
    for mode in sorted(REQUIRED_SETTLEMENT_MODES - settlement_modes):
        errors.append(f"missing settlement mode: {mode}")
    for row in rows:
        errors.extend(
            f"{row['operator_template']}: {error}"
            for error in row.get("errors", [])
        )

    summary = {
        "operator_template_count": len(rows),
        "passed_count": sum(1 for row in rows if row.get("status") == "passed"),
        "failed_count": sum(1 for row in rows if row.get("status") != "passed"),
        "operator_templates": sorted(templates),
        "settlement_modes": sorted(settlement_modes),
        "direct_settlement_template_count": sum(
            1 for row in rows if row.get("direct_creator_settlement_allowed") is True
        ),
        "no_direct_settlement_template_count": sum(
            1 for row in rows if row.get("direct_creator_settlement_allowed") is False
        ),
        "public_sector_template_count": sum(
            1 for row in rows if row.get("public_sector_use_supported") is True
        ),
        "production_acceptance_allowed_count": sum(
            1
            for row in rows
            if row.get("production_acceptance_decision") == "allow"
        ),
        "copied_display_verified_count": sum(
            1 for row in rows if row.get("response_display_text_status") == "passed"
        ),
        "runtime_checked": check_runtime,
        "output_dir": _path(output_root),
    }
    report = {
        "schema": MATRIX_SCHEMA,
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "summary": summary,
        "rows": rows,
    }
    report["matrix_report_hash"] = canonical_hash(report)
    return report


def render_text(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        f"operator_acceptance_matrix status: {report['status']}",
        f"operator_template_count: {summary['operator_template_count']}",
        f"passed_count: {summary['passed_count']}",
        f"failed_count: {summary['failed_count']}",
        "operator_templates: "
        f"{json.dumps(summary['operator_templates'], sort_keys=True)}",
        "settlement_modes: "
        f"{json.dumps(summary['settlement_modes'], sort_keys=True)}",
        f"direct_settlement_template_count: {summary['direct_settlement_template_count']}",
        f"public_sector_template_count: {summary['public_sector_template_count']}",
        f"copied_display_verified_count: {summary['copied_display_verified_count']}",
        f"output_dir: {summary['output_dir']}",
        f"matrix_report_hash: {report['matrix_report_hash']}",
    ]
    for row in report["rows"]:
        lines.append(
            "row: "
            f"{row['operator_template']} status={row['status']} "
            f"acceptance={row['acceptance_status']} "
            f"display_text={row['response_display_text_status']} "
            f"settlement={row['settlement_mode']} "
            f"direct_settlement="
            f"{json.dumps(row['direct_creator_settlement_allowed'])} "
            f"public_sector={json.dumps(row['public_sector_use_supported'])}"
        )
    if report["errors"]:
        lines.append("errors:")
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--operator-template",
        choices=sorted(REQUIRED_OPERATOR_TEMPLATES),
        action="append",
        dest="operator_templates",
    )
    parser.add_argument("--no-runtime-check", action="store_true")
    parser.add_argument("--write-report", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = run_acceptance_matrix(
        output_dir=args.output_dir,
        operator_templates=args.operator_templates,
        check_runtime=not args.no_runtime_check,
    )
    if args.write_report is not None:
        _write_json(args.write_report, report)
    print(
        json.dumps(report, indent=2, sort_keys=True)
        if args.json
        else render_text(report)
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
