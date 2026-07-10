"""Create a final RDLLM operator production-acceptance report."""

from __future__ import annotations

import argparse
import json
import sys
from importlib import resources
from pathlib import Path
from typing import Any

from rdllm.operator_launch_gate import run_launch_gate
from rdllm.operator_recovery import verify_recovery_manifest
from rdllm.service import canonical_hash
from rdllm.service_audit_verifier import verify_service_audit_log


ACCEPTANCE_SCHEMA = "rdllm-operator-acceptance-report/v1"
ACCEPTANCE_VERIFICATION_SCHEMA = "rdllm-operator-acceptance-verification/v1"
DATA_PACKAGE = "rdllm.data"
ACCEPTANCE_SCHEMA_RESOURCE = ("schemas", "operator_acceptance_report.schema.json")
ACCEPTANCE_VERIFICATION_SCHEMA_RESOURCE = (
    "schemas",
    "operator_acceptance_verification.schema.json",
)


def load_acceptance_schema() -> dict[str, Any]:
    resource = resources.files(DATA_PACKAGE).joinpath(*ACCEPTANCE_SCHEMA_RESOURCE)
    return json.loads(resource.read_text(encoding="utf-8"))


def load_acceptance_verification_schema() -> dict[str, Any]:
    resource = resources.files(DATA_PACKAGE).joinpath(
        *ACCEPTANCE_VERIFICATION_SCHEMA_RESOURCE
    )
    return json.loads(resource.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _status_ok(status: Any) -> bool:
    return status in {"ready", "passed"}


def _section_errors(name: str, section: dict[str, Any]) -> list[str]:
    status = section.get("status", "unknown")
    if _status_ok(status):
        return []
    errors = section.get("errors", [])
    if isinstance(errors, list) and errors:
        return [f"{name}: {error}" for error in errors]
    return [f"{name}: status {status}"]


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _is_hash(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _shape_errors(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["<root>: expected object"]
    errors: list[str] = []
    required = {
        "schema",
        "status",
        "errors",
        "summary",
        "evidence",
        "launch_gate",
        "audit_verification",
        "audit_response_binding",
        "recovery_verification",
        "acceptance_report_hash",
    }
    for field in sorted(required - set(report)):
        errors.append(f"<root>.{field}: missing required field")
    if report.get("schema") != ACCEPTANCE_SCHEMA:
        errors.append(f"<root>.schema: expected {ACCEPTANCE_SCHEMA!r}")
    if report.get("status") not in {"ready", "blocked"}:
        errors.append("<root>.status: expected ready or blocked")
    if not isinstance(report.get("errors"), list):
        errors.append("<root>.errors: expected array")
    elif not all(isinstance(error, str) for error in report["errors"]):
        errors.append("<root>.errors: expected string items")
    if not isinstance(report.get("summary"), dict):
        errors.append("<root>.summary: expected object")
    if not isinstance(report.get("evidence"), dict):
        errors.append("<root>.evidence: expected object")
    if not _is_hash(report.get("acceptance_report_hash")):
        errors.append("<root>.acceptance_report_hash: expected SHA-256 hex string")

    for name in (
        "launch_gate",
        "audit_verification",
        "audit_response_binding",
        "recovery_verification",
    ):
        section = report.get(name)
        if not isinstance(section, dict):
            errors.append(f"<root>.{name}: expected object")
            continue
        if "status" not in section:
            errors.append(f"{name}.status: missing required field")
        if not isinstance(section.get("errors", []), list):
            errors.append(f"{name}.errors: expected array")

    summary = _as_dict(report.get("summary"))
    summary_required = {
        "production_acceptance_decision",
        "traffic_decision",
        "launch_gate_status",
        "response_verification_status",
        "response_display_text_status",
        "audit_verification_status",
        "audit_response_binding_status",
        "recovery_verification_status",
        "runtime_checked",
        "support_bundle_written",
        "operator_type",
        "settlement_mode",
        "production_grade_claim_allowed",
        "direct_creator_settlement_allowed",
        "public_sector_use_supported",
    }
    for field in sorted(summary_required - set(summary)):
        errors.append(f"summary.{field}: missing required field")
    if summary.get("production_acceptance_decision") not in {"allow", "block"}:
        errors.append("summary.production_acceptance_decision: expected allow or block")
    if summary.get("traffic_decision") not in {"allow", "block"}:
        errors.append("summary.traffic_decision: expected allow or block")
    for field in (
        "launch_gate_status",
        "response_verification_status",
        "response_display_text_status",
        "audit_verification_status",
        "audit_response_binding_status",
        "recovery_verification_status",
    ):
        if not isinstance(summary.get(field), str):
            errors.append(f"summary.{field}: expected string")
    for field in (
        "runtime_checked",
        "support_bundle_written",
        "production_grade_claim_allowed",
        "direct_creator_settlement_allowed",
        "public_sector_use_supported",
    ):
        if not isinstance(summary.get(field), bool):
            errors.append(f"summary.{field}: expected boolean")

    evidence = _as_dict(report.get("evidence"))
    evidence_required = {
        "profile_hash",
        "response_event_hash",
        "response_footer_hash",
        "response_display_hash",
        "response_display_text_hash",
        "audit_first_entry_hash",
        "audit_last_entry_hash",
        "audit_entry_count",
        "recovery_manifest_file_count",
        "recovery_checked_count",
    }
    for field in sorted(evidence_required - set(evidence)):
        errors.append(f"evidence.{field}: missing required field")
    for field in (
        "profile_hash",
        "response_event_hash",
        "response_footer_hash",
        "response_display_hash",
        "response_display_text_hash",
        "audit_first_entry_hash",
        "audit_last_entry_hash",
    ):
        value = evidence.get(field, "")
        if not isinstance(value, str):
            errors.append(f"evidence.{field}: expected string")
    for field in (
        "audit_entry_count",
        "recovery_manifest_file_count",
        "recovery_checked_count",
    ):
        value = evidence.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"evidence.{field}: expected non-negative integer")
    return errors


def _expected_acceptance_errors(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for name in (
        "launch_gate",
        "audit_verification",
        "audit_response_binding",
        "recovery_verification",
    ):
        section = report.get(name, {})
        section = section if isinstance(section, dict) else {}
        errors.extend(_section_errors(name, section))
    return errors


def verify_acceptance_report(report: dict[str, Any]) -> dict[str, Any]:
    errors = _shape_errors(report)
    if not isinstance(report, dict):
        return {
            "schema": ACCEPTANCE_VERIFICATION_SCHEMA,
            "status": "failed",
            "errors": errors,
            "acceptance_status": "unknown",
            "production_acceptance_decision": "unknown",
            "traffic_decision": "unknown",
            "recorded_acceptance_report_hash": "",
            "computed_acceptance_report_hash": "",
        }

    without_hash = {
        key: value for key, value in report.items() if key != "acceptance_report_hash"
    }
    computed_hash = canonical_hash(without_hash)
    recorded_hash = str(report.get("acceptance_report_hash", ""))
    if recorded_hash and recorded_hash != computed_hash:
        errors.append("acceptance_report_hash: mismatch")

    summary = _as_dict(report.get("summary"))
    evidence = _as_dict(report.get("evidence"))
    launch_gate = _as_dict(report.get("launch_gate"))
    launch_summary = _as_dict(launch_gate.get("summary"))
    response_verification = _as_dict(launch_gate.get("response_verification"))
    audit_verification = _as_dict(report.get("audit_verification"))
    audit_binding = _as_dict(report.get("audit_response_binding"))
    recovery_verification = _as_dict(report.get("recovery_verification"))

    expected_errors = _expected_acceptance_errors(report)
    reported_errors = _as_list(report.get("errors"))
    if reported_errors != expected_errors:
        errors.append("errors: does not match section failures")
    expected_status = "ready" if not expected_errors else "blocked"
    if report.get("status") != expected_status:
        errors.append(f"status: expected {expected_status}")
    expected_decision = (
        "allow"
        if expected_status == "ready"
        and launch_summary.get("production_grade_claim_allowed") is True
        else "block"
    )
    if summary.get("production_acceptance_decision") != expected_decision:
        errors.append(
            "summary.production_acceptance_decision: does not match section failures"
        )
    expected_claim_flag = expected_status == "ready"
    claim_flag_bindings = (
        (
            "summary.production_grade_claim_allowed",
            summary.get("production_grade_claim_allowed"),
            expected_claim_flag
            and launch_summary.get("production_grade_claim_allowed") is True,
        ),
        (
            "summary.direct_creator_settlement_allowed",
            summary.get("direct_creator_settlement_allowed"),
            expected_claim_flag
            and launch_summary.get("direct_creator_settlement_allowed") is True,
        ),
        (
            "summary.public_sector_use_supported",
            summary.get("public_sector_use_supported"),
            expected_claim_flag
            and launch_summary.get("public_sector_use_supported") is True,
        ),
    )
    bindings = (
        (
            "summary.launch_gate_status",
            summary.get("launch_gate_status"),
            launch_gate.get("status"),
        ),
        (
            "summary.traffic_decision",
            summary.get("traffic_decision"),
            launch_summary.get("traffic_decision"),
        ),
        (
            "summary.response_verification_status",
            summary.get("response_verification_status"),
            response_verification.get("status"),
        ),
        (
            "summary.response_display_text_status",
            summary.get("response_display_text_status"),
            response_verification.get("display_text_status", "not_checked"),
        ),
        (
            "summary.audit_verification_status",
            summary.get("audit_verification_status"),
            audit_verification.get("status"),
        ),
        (
            "summary.audit_response_binding_status",
            summary.get("audit_response_binding_status"),
            audit_binding.get("status"),
        ),
        (
            "summary.recovery_verification_status",
            summary.get("recovery_verification_status"),
            recovery_verification.get("status"),
        ),
        (
            "evidence.profile_hash",
            evidence.get("profile_hash"),
            _as_dict(launch_gate.get("profile")).get("profile_hash", ""),
        ),
        (
            "evidence.response_event_hash",
            evidence.get("response_event_hash"),
            response_verification.get("event_hash", ""),
        ),
        (
            "evidence.response_footer_hash",
            evidence.get("response_footer_hash"),
            response_verification.get("footer_hash", ""),
        ),
        (
            "evidence.response_display_hash",
            evidence.get("response_display_hash"),
            response_verification.get("display_hash", ""),
        ),
        (
            "evidence.response_display_text_hash",
            evidence.get("response_display_text_hash"),
            response_verification.get("display_text_hash", ""),
        ),
        (
            "evidence.audit_first_entry_hash",
            evidence.get("audit_first_entry_hash"),
            audit_verification.get("first_entry_hash", ""),
        ),
        (
            "evidence.audit_last_entry_hash",
            evidence.get("audit_last_entry_hash"),
            audit_verification.get("last_entry_hash", ""),
        ),
        (
            "evidence.audit_entry_count",
            evidence.get("audit_entry_count"),
            audit_verification.get("entry_count", 0),
        ),
        (
            "evidence.recovery_manifest_file_count",
            evidence.get("recovery_manifest_file_count"),
            recovery_verification.get("manifest_file_count", 0),
        ),
        (
            "evidence.recovery_checked_count",
            evidence.get("recovery_checked_count"),
            recovery_verification.get("checked_count", 0),
        ),
        (
            "audit_response_binding.response_event_hash",
            audit_binding.get("response_event_hash"),
            evidence.get("response_event_hash"),
        ),
        (
            "audit_response_binding.response_footer_hash",
            audit_binding.get("response_footer_hash"),
            evidence.get("response_footer_hash"),
        ),
        (
            "audit_response_binding.response_display_hash",
            audit_binding.get("response_display_hash"),
            evidence.get("response_display_hash"),
        ),
        (
            "audit_response_binding.latest_event_hash",
            audit_binding.get("latest_event_hash"),
            audit_verification.get("last_event_hash", ""),
        ),
        (
            "audit_response_binding.latest_source_footer_hash",
            audit_binding.get("latest_source_footer_hash"),
            audit_verification.get("last_source_footer_hash", ""),
        ),
        (
            "audit_response_binding.latest_display_hash",
            audit_binding.get("latest_display_hash"),
            audit_verification.get("last_display_hash", ""),
        ),
        (
            "audit_response_binding.audit_event_count",
            audit_binding.get("audit_event_count"),
            evidence.get("audit_entry_count"),
        ),
    ) + claim_flag_bindings
    for label, actual, expected in bindings:
        if actual != expected:
            errors.append(f"{label}: binding mismatch")

    if (
        report.get("status") == "ready"
        and audit_binding.get("allow_nonlatest_response_event") is not True
        and audit_binding.get("latest_event_matches_response") is not True
    ):
        errors.append(
            "audit_response_binding.latest_event_matches_response: required for ready report"
        )
    if (
        report.get("status") == "ready"
        and audit_binding.get("event_present") is not True
    ):
        errors.append("audit_response_binding.event_present: required for ready report")
    if report.get("status") == "ready":
        if audit_binding.get("latest_entry_status") != "ready":
            errors.append(
                "audit_response_binding.latest_entry_status: required ready for ready report"
            )
        if audit_binding.get("latest_audit_error_count") != 0:
            errors.append(
                "audit_response_binding.latest_audit_error_count: required zero for ready report"
            )
        if audit_binding.get("latest_entry_ready") is not True:
            errors.append(
                "audit_response_binding.latest_entry_ready: required for ready report"
            )
        if audit_binding.get("latest_entry_clean") is not True:
            errors.append(
                "audit_response_binding.latest_entry_clean: required for ready report"
            )
        if audit_binding.get("source_footer_hash_matches_response") is not True:
            errors.append(
                "audit_response_binding.source_footer_hash_matches_response: "
                "required for ready report"
            )
        if audit_binding.get("display_hash_matches_response") is not True:
            errors.append(
                "audit_response_binding.display_hash_matches_response: "
                "required for ready report"
            )
    if report.get("status") == "ready":
        for label, value in (
            ("evidence.profile_hash", evidence.get("profile_hash")),
            ("evidence.response_event_hash", evidence.get("response_event_hash")),
            ("evidence.response_footer_hash", evidence.get("response_footer_hash")),
            ("evidence.response_display_hash", evidence.get("response_display_hash")),
            (
                "evidence.response_display_text_hash",
                evidence.get("response_display_text_hash"),
            ),
            ("evidence.audit_first_entry_hash", evidence.get("audit_first_entry_hash")),
            ("evidence.audit_last_entry_hash", evidence.get("audit_last_entry_hash")),
        ):
            if not _is_hash(value):
                errors.append(f"{label}: expected SHA-256 hex string for ready report")
        if summary.get("response_display_text_status") != "passed":
            errors.append(
                "summary.response_display_text_status: required passed for ready report"
            )

    return {
        "schema": ACCEPTANCE_VERIFICATION_SCHEMA,
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "acceptance_status": str(report.get("status", "unknown")),
        "production_acceptance_decision": str(
            summary.get("production_acceptance_decision", "unknown")
        ),
        "traffic_decision": str(summary.get("traffic_decision", "unknown")),
        "recorded_acceptance_report_hash": recorded_hash,
        "computed_acceptance_report_hash": computed_hash,
    }


def _audit_rows(audit_log: Path) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    rows: list[dict[str, Any]] = []
    try:
        lines = audit_log.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        return [], [f"audit_log: failed to read rows: {exc}"]
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(
                f"line {line_number}: invalid JSON while binding event: {exc}"
            )
            continue
        if not isinstance(row, dict):
            errors.append(f"line {line_number}: expected audit object")
            continue
        rows.append(row)
    return rows, errors


def _audit_response_binding(
    *,
    audit_log: Path,
    response_event_hash: str,
    response_footer_hash: str,
    response_display_hash: str,
    allow_nonlatest_response_event: bool,
) -> dict[str, Any]:
    rows, errors = _audit_rows(audit_log)
    event_hashes = [
        row.get("event_hash")
        for row in rows
        if isinstance(row.get("event_hash"), str) and row.get("event_hash")
    ]
    latest_event_hash = event_hashes[-1] if event_hashes else ""
    latest_row = rows[-1] if rows else {}
    matching_rows = [
        row
        for row in rows
        if response_event_hash
        and isinstance(row.get("event_hash"), str)
        and row.get("event_hash") == response_event_hash
    ]
    matching_row = matching_rows[-1] if matching_rows else {}
    latest_entry_status = str(latest_row.get("status", "")) if latest_row else ""
    latest_audit_error_count = latest_row.get("audit_error_count", 0)
    event_present = bool(response_event_hash and response_event_hash in event_hashes)
    latest_event_matches_response = bool(
        response_event_hash and latest_event_hash == response_event_hash
    )
    matched_source_footer_hash = str(matching_row.get("source_footer_hash", ""))
    matched_display_hash = str(matching_row.get("display_hash", ""))
    latest_source_footer_hash = str(latest_row.get("source_footer_hash", ""))
    latest_display_hash = str(latest_row.get("display_hash", ""))
    source_footer_hash_matches_response = bool(
        response_footer_hash
        and matched_source_footer_hash
        and matched_source_footer_hash == response_footer_hash
    )
    display_hash_matches_response = bool(
        response_display_hash
        and matched_display_hash
        and matched_display_hash == response_display_hash
    )
    latest_entry_ready = latest_entry_status == "ready"
    latest_entry_clean = latest_audit_error_count == 0
    if not response_event_hash:
        errors.append("response_event_hash: missing from response verification")
    if not response_footer_hash:
        errors.append("response_footer_hash: missing from response verification")
    if not response_display_hash:
        errors.append("response_display_hash: missing from response verification")
    if response_event_hash and not event_present:
        errors.append("audit_log: response event hash was not found")
    if (
        response_event_hash
        and event_present
        and not latest_event_matches_response
        and not allow_nonlatest_response_event
    ):
        errors.append("audit_log: latest event does not match saved response")
    if response_event_hash and latest_event_matches_response and not latest_entry_ready:
        errors.append("audit_log: latest entry status is not ready")
    if response_event_hash and latest_event_matches_response and not latest_entry_clean:
        errors.append("audit_log: latest entry has audit errors")
    if response_event_hash and event_present and not source_footer_hash_matches_response:
        errors.append("audit_log: source footer hash does not match saved response")
    if response_event_hash and event_present and not display_hash_matches_response:
        errors.append("audit_log: display hash does not match saved response")
    return {
        "schema": "rdllm-operator-audit-response-binding/v1",
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "response_event_hash": response_event_hash,
        "response_footer_hash": response_footer_hash,
        "response_display_hash": response_display_hash,
        "latest_event_hash": latest_event_hash,
        "matched_source_footer_hash": matched_source_footer_hash,
        "matched_display_hash": matched_display_hash,
        "latest_source_footer_hash": latest_source_footer_hash,
        "latest_display_hash": latest_display_hash,
        "latest_entry_status": latest_entry_status,
        "latest_audit_error_count": latest_audit_error_count
        if isinstance(latest_audit_error_count, int)
        else 0,
        "event_present": event_present,
        "latest_event_matches_response": latest_event_matches_response,
        "source_footer_hash_matches_response": source_footer_hash_matches_response,
        "display_hash_matches_response": display_hash_matches_response,
        "latest_entry_ready": latest_entry_ready,
        "latest_entry_clean": latest_entry_clean,
        "allow_nonlatest_response_event": allow_nonlatest_response_event,
        "audit_event_count": len(event_hashes),
    }


def _recovery_section(
    recovery_manifest: Path,
    *,
    recovery_root: Path | None,
) -> dict[str, Any]:
    try:
        manifest = _load_json(recovery_manifest)
    except Exception as exc:
        return {
            "schema": "rdllm-operator-recovery-verification/v1",
            "status": "failed",
            "errors": [f"recovery_manifest: failed to read JSON: {exc}"],
            "checked_count": 0,
            "missing_count": 0,
            "mismatch_count": 0,
            "manifest_file_count": 0,
            "restored_total_bytes": 0,
        }
    return verify_recovery_manifest(manifest, root=recovery_root)


def run_acceptance_report(
    *,
    profile: Path,
    service_config: Path,
    response: Path,
    audit_log: Path,
    recovery_manifest: Path,
    display_text: Path | None = None,
    service_root: Path | None = None,
    bootstrap_dir: Path | None = None,
    recovery_root: Path | None = None,
    check_runtime: bool = True,
    expected_audit_count: int | None = None,
    allow_nonlatest_response_event: bool = False,
    support_bundle_output: Path | None = None,
    trust_store: Path | None = None,
) -> dict[str, Any]:
    launch_gate = run_launch_gate(
        profile=profile,
        service_config=service_config,
        service_root=service_root,
        bootstrap_dir=bootstrap_dir,
        response=response,
        display_text=display_text,
        check_runtime=check_runtime,
        skip_response=False,
        support_bundle_output=support_bundle_output,
        trust_store=trust_store,
    )
    audit_verification = verify_service_audit_log(
        audit_log,
        expected_count=expected_audit_count,
    )
    response_verification = launch_gate.get("response_verification", {})
    response_event_hash = str(response_verification.get("event_hash", ""))
    response_footer_hash = str(response_verification.get("footer_hash", ""))
    response_display_hash = str(response_verification.get("display_hash", ""))
    audit_binding = _audit_response_binding(
        audit_log=audit_log,
        response_event_hash=response_event_hash,
        response_footer_hash=response_footer_hash,
        response_display_hash=response_display_hash,
        allow_nonlatest_response_event=allow_nonlatest_response_event,
    )
    recovery_verification = _recovery_section(
        recovery_manifest,
        recovery_root=recovery_root,
    )

    sections = {
        "launch_gate": launch_gate,
        "audit_verification": audit_verification,
        "audit_response_binding": audit_binding,
        "recovery_verification": recovery_verification,
    }
    errors: list[str] = []
    for name, section in sections.items():
        errors.extend(_section_errors(name, section))

    launch_summary = launch_gate.get("summary", {})
    profile_section = launch_gate.get("profile", {})
    profile_summary = (
        profile_section.get("summary", {}) if isinstance(profile_section, dict) else {}
    )
    production_claim_allowed = (
        not errors and launch_summary.get("production_grade_claim_allowed") is True
    )
    summary = {
        "production_acceptance_decision": (
            "allow" if production_claim_allowed else "block"
        ),
        "traffic_decision": launch_summary.get("traffic_decision", "block"),
        "launch_gate_status": launch_gate.get("status", "unknown"),
        "response_verification_status": response_verification.get("status", "unknown"),
        "response_display_text_status": response_verification.get(
            "display_text_status",
            "not_checked",
        ),
        "audit_verification_status": audit_verification.get("status", "unknown"),
        "audit_response_binding_status": audit_binding.get("status", "unknown"),
        "recovery_verification_status": recovery_verification.get("status", "unknown"),
        "runtime_checked": check_runtime,
        "support_bundle_written": support_bundle_output is not None,
        "operator_type": profile_summary.get("operator_type", ""),
        "settlement_mode": profile_summary.get("settlement_mode", ""),
        "production_grade_claim_allowed": production_claim_allowed,
        "direct_creator_settlement_allowed": (
            not errors
            and launch_summary.get("direct_creator_settlement_allowed") is True
        ),
        "public_sector_use_supported": (
            not errors and launch_summary.get("public_sector_use_supported") is True
        ),
    }
    evidence = {
        "profile_hash": profile_section.get("profile_hash", ""),
        "response_event_hash": response_event_hash,
        "response_footer_hash": response_footer_hash,
        "response_display_hash": response_display_hash,
        "response_display_text_hash": response_verification.get(
            "display_text_hash",
            "",
        ),
        "audit_first_entry_hash": audit_verification.get("first_entry_hash", ""),
        "audit_last_entry_hash": audit_verification.get("last_entry_hash", ""),
        "audit_entry_count": audit_verification.get("entry_count", 0),
        "recovery_manifest_file_count": recovery_verification.get(
            "manifest_file_count",
            0,
        ),
        "recovery_checked_count": recovery_verification.get("checked_count", 0),
    }
    report = {
        "schema": ACCEPTANCE_SCHEMA,
        "status": "ready" if not errors else "blocked",
        "errors": errors,
        "summary": summary,
        "evidence": evidence,
        **sections,
    }
    report["acceptance_report_hash"] = canonical_hash(report)
    return report


def render_text(report: dict[str, Any]) -> str:
    summary = report["summary"]
    evidence = report["evidence"]
    lines = [
        f"operator_acceptance status: {report['status']}",
        f"production_acceptance_decision: {summary['production_acceptance_decision']}",
        f"traffic_decision: {summary['traffic_decision']}",
        f"launch_gate_status: {summary['launch_gate_status']}",
        f"response_verification_status: {summary['response_verification_status']}",
        f"response_display_text_status: {summary['response_display_text_status']}",
        f"audit_verification_status: {summary['audit_verification_status']}",
        f"audit_response_binding_status: {summary['audit_response_binding_status']}",
        f"recovery_verification_status: {summary['recovery_verification_status']}",
        f"response_event_hash: {evidence['response_event_hash']}",
        f"response_display_hash: {evidence['response_display_hash']}",
        f"response_display_text_hash: {evidence['response_display_text_hash']}",
        f"audit_entry_count: {evidence['audit_entry_count']}",
        "audit_latest_entry_status: "
        f"{report['audit_response_binding'].get('latest_entry_status', '')}",
        "audit_latest_error_count: "
        f"{report['audit_response_binding'].get('latest_audit_error_count', 0)}",
        f"recovery_checked_count: {evidence['recovery_checked_count']}",
        f"acceptance_report_hash: {report['acceptance_report_hash']}",
    ]
    if report["errors"]:
        lines.append("errors:")
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines)


def render_verification_text(report: dict[str, Any]) -> str:
    lines = [
        f"operator_acceptance_verification status: {report['status']}",
        f"acceptance_status: {report['acceptance_status']}",
        "production_acceptance_decision: "
        f"{report['production_acceptance_decision']}",
        f"traffic_decision: {report['traffic_decision']}",
        "recorded_acceptance_report_hash: "
        f"{report['recorded_acceptance_report_hash']}",
        "computed_acceptance_report_hash: "
        f"{report['computed_acceptance_report_hash']}",
    ]
    if report["errors"]:
        lines.append("errors:")
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines)


def create_main(argv: list[str] | None = None) -> int:
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
    parser.add_argument("--response", type=Path, required=True)
    parser.add_argument("--display-text", type=Path, required=True)
    parser.add_argument("--audit-log", type=Path, required=True)
    parser.add_argument("--expected-audit-count", type=int)
    parser.add_argument("--recovery-manifest", type=Path, required=True)
    parser.add_argument("--recovery-root", type=Path)
    parser.add_argument("--no-runtime-check", action="store_true")
    parser.add_argument("--allow-nonlatest-response-event", action="store_true")
    parser.add_argument("--write-support-bundle", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = run_acceptance_report(
        profile=args.profile,
        service_config=args.service_config,
        service_root=args.service_root,
        bootstrap_dir=args.bootstrap_dir,
        response=args.response,
        display_text=args.display_text,
        audit_log=args.audit_log,
        expected_audit_count=args.expected_audit_count,
        recovery_manifest=args.recovery_manifest,
        recovery_root=args.recovery_root,
        check_runtime=not args.no_runtime_check,
        allow_nonlatest_response_event=args.allow_nonlatest_response_event,
        support_bundle_output=args.write_support_bundle,
        trust_store=args.trust_store,
    )
    _write_json(args.output, report)
    print(
        json.dumps(report, indent=2, sort_keys=True)
        if args.json
        else render_text(report)
    )
    return 0 if report["status"] == "ready" else 1


def verify_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a saved RDLLM operator acceptance report."
    )
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        report = _load_json(args.report)
    except Exception as exc:
        verification = {
            "schema": ACCEPTANCE_VERIFICATION_SCHEMA,
            "status": "failed",
            "errors": [f"report: failed to read JSON: {exc}"],
            "acceptance_status": "unknown",
            "production_acceptance_decision": "unknown",
            "traffic_decision": "unknown",
            "recorded_acceptance_report_hash": "",
            "computed_acceptance_report_hash": "",
        }
    else:
        verification = verify_acceptance_report(report)
    print(
        json.dumps(verification, indent=2, sort_keys=True)
        if args.json
        else render_verification_text(verification)
    )
    return 0 if verification["status"] == "passed" else 1


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    if args and args[0] == "verify":
        return verify_main(args[1:])
    return create_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
