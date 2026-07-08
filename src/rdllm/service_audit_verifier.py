"""Verify RDLLM service hash-chained audit logs."""

from __future__ import annotations

import argparse
from datetime import datetime
from importlib import resources
import json
from pathlib import Path
from typing import Any

from rdllm.service import canonical_hash


DATA_PACKAGE = "rdllm.data"
AUDIT_ENTRY_SCHEMA = "rdllm-service-audit-entry/v1"
AUDIT_VERIFICATION_SCHEMA = "rdllm-service-audit-verification/v1"
AUDIT_ENTRY_SCHEMA_RESOURCE = (
    "schemas",
    "service_audit_entry.schema.json",
)
AUDIT_VERIFICATION_SCHEMA_RESOURCE = (
    "schemas",
    "service_audit_verification.schema.json",
)


def load_audit_entry_schema() -> dict[str, Any]:
    resource = resources.files(DATA_PACKAGE)
    for part in AUDIT_ENTRY_SCHEMA_RESOURCE:
        resource = resource.joinpath(part)
    return json.loads(resource.read_text(encoding="utf-8"))


def load_audit_verification_schema() -> dict[str, Any]:
    resource = resources.files(DATA_PACKAGE)
    for part in AUDIT_VERIFICATION_SCHEMA_RESOURCE:
        resource = resource.joinpath(part)
    return json.loads(resource.read_text(encoding="utf-8"))


def _read_rows(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        return [], [f"audit_log: failed to read: {exc}"]
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_number}: invalid JSON: {exc}")
            continue
        if not isinstance(row, dict):
            errors.append(f"line {line_number}: expected object")
            continue
        rows.append(row)
    return rows, errors


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _timestamp_valid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return True


def _entry_hash(row: dict[str, Any]) -> str:
    return canonical_hash(
        {key: value for key, value in row.items() if key != "entry_hash"}
    )


def _validate_row(
    row: dict[str, Any],
    *,
    index: int,
    previous_hash: str,
) -> list[str]:
    errors: list[str] = []
    prefix = f"line {index}"
    required = {
        "schema",
        "request_id",
        "timestamp",
        "status",
        "event_id",
        "event_hash",
        "source_footer_hash",
        "display_hash",
        "source_count",
        "audit_error_count",
        "previous_entry_hash",
        "entry_hash",
    }
    for field in sorted(required - set(row)):
        errors.append(f"{prefix}.{field}: missing required field")
    if row.get("schema") != AUDIT_ENTRY_SCHEMA:
        errors.append(f"{prefix}.schema: expected {AUDIT_ENTRY_SCHEMA!r}")
    if not _is_nonempty_string(row.get("request_id")):
        errors.append(f"{prefix}.request_id: expected non-empty string")
    if not _timestamp_valid(row.get("timestamp")):
        errors.append(f"{prefix}.timestamp: expected UTC timestamp")
    if row.get("status") not in {"ready", "blocked"}:
        errors.append(f"{prefix}.status: expected ready or blocked")
    for field in (
        "event_id",
        "event_hash",
        "source_footer_hash",
        "display_hash",
        "previous_entry_hash",
        "entry_hash",
    ):
        if not isinstance(row.get(field), str):
            errors.append(f"{prefix}.{field}: expected string")
    for field in ("source_count", "audit_error_count"):
        if not _is_nonnegative_int(row.get(field)):
            errors.append(f"{prefix}.{field}: expected non-negative integer")
    audit_error_count = row.get("audit_error_count")
    if _is_nonnegative_int(audit_error_count):
        if row.get("status") == "ready" and audit_error_count != 0:
            errors.append(
                f"{prefix}.audit_error_count: ready entry must have zero audit errors"
            )
        if row.get("status") == "blocked" and audit_error_count == 0:
            errors.append(
                f"{prefix}.audit_error_count: blocked entry must have audit errors"
            )
    if row.get("previous_entry_hash") != previous_hash:
        errors.append(f"{prefix}.previous_entry_hash: chain mismatch")
    if (
        isinstance(row.get("entry_hash"), str)
        and row.get("entry_hash") != _entry_hash(row)
    ):
        errors.append(f"{prefix}.entry_hash: mismatch")
    event_hash = row.get("event_hash")
    event_id = row.get("event_id")
    if row.get("status") == "ready" and not event_hash:
        errors.append(f"{prefix}.event_hash: ready entry must bind an event")
    if row.get("status") == "ready" and not row.get("source_footer_hash"):
        errors.append(
            f"{prefix}.source_footer_hash: ready entry must bind a source footer"
        )
    if row.get("status") == "ready" and not row.get("display_hash"):
        errors.append(f"{prefix}.display_hash: ready entry must bind a display")
    if event_hash:
        expected_event_id = f"evt_{event_hash[:16]}"
        if event_id != expected_event_id:
            errors.append(f"{prefix}.event_id: does not match event hash")
    return errors


def verify_service_audit_log(
    audit_log: Path,
    *,
    expected_count: int | None = None,
    allow_empty: bool = False,
) -> dict[str, Any]:
    rows, errors = _read_rows(audit_log)
    if expected_count is not None and len(rows) != expected_count:
        errors.append(f"entry_count: expected {expected_count}, got {len(rows)}")
    if not rows and not allow_empty and not errors:
        errors.append("audit_log: no audit entries found")

    previous_hash = ""
    ready_count = 0
    blocked_count = 0
    audit_error_total = 0
    source_count_total = 0
    first_entry_hash = ""
    last_entry_hash = ""
    first_event_hash = ""
    last_event_hash = ""
    first_source_footer_hash = ""
    last_source_footer_hash = ""
    first_display_hash = ""
    last_display_hash = ""
    for index, row in enumerate(rows, start=1):
        errors.extend(_validate_row(row, index=index, previous_hash=previous_hash))
        if index == 1:
            first_entry_hash = str(row.get("entry_hash", ""))
            first_event_hash = str(row.get("event_hash", ""))
            first_source_footer_hash = str(row.get("source_footer_hash", ""))
            first_display_hash = str(row.get("display_hash", ""))
        if row.get("status") == "ready":
            ready_count += 1
        if row.get("status") == "blocked":
            blocked_count += 1
        if isinstance(row.get("audit_error_count"), int):
            audit_error_total += int(row["audit_error_count"])
        if isinstance(row.get("source_count"), int):
            source_count_total += int(row["source_count"])
        previous_hash = str(row.get("entry_hash", ""))
        last_entry_hash = previous_hash
        last_event_hash = str(row.get("event_hash", ""))
        last_source_footer_hash = str(row.get("source_footer_hash", ""))
        last_display_hash = str(row.get("display_hash", ""))

    return {
        "schema": AUDIT_VERIFICATION_SCHEMA,
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "entry_count": len(rows),
        "ready_entry_count": ready_count,
        "blocked_entry_count": blocked_count,
        "audit_error_total": audit_error_total,
        "source_count_total": source_count_total,
        "first_entry_hash": first_entry_hash,
        "last_entry_hash": last_entry_hash,
        "first_event_hash": first_event_hash,
        "last_event_hash": last_event_hash,
        "first_source_footer_hash": first_source_footer_hash,
        "last_source_footer_hash": last_source_footer_hash,
        "first_display_hash": first_display_hash,
        "last_display_hash": last_display_hash,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"service_audit_verification status: {report['status']}",
        f"entry_count: {report['entry_count']}",
        f"ready_entry_count: {report['ready_entry_count']}",
        f"blocked_entry_count: {report['blocked_entry_count']}",
        f"audit_error_total: {report['audit_error_total']}",
        f"source_count_total: {report['source_count_total']}",
        f"first_entry_hash: {report['first_entry_hash']}",
        f"last_entry_hash: {report['last_entry_hash']}",
        f"first_event_hash: {report['first_event_hash']}",
        f"last_event_hash: {report['last_event_hash']}",
        f"first_source_footer_hash: {report['first_source_footer_hash']}",
        f"last_source_footer_hash: {report['last_source_footer_hash']}",
        f"first_display_hash: {report['first_display_hash']}",
        f"last_display_hash: {report['last_display_hash']}",
    ]
    if report["errors"]:
        lines.append("errors:")
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-log", type=Path, required=True)
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--allow-empty", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = verify_service_audit_log(
        args.audit_log,
        expected_count=args.expected_count,
        allow_empty=args.allow_empty,
    )
    print(
        json.dumps(report, indent=2, sort_keys=True)
        if args.json
        else render_text(report)
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
