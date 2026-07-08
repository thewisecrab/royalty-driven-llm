"""Audit the hosted RDLLM public proof surface for private payload leaks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = ROOT / "docs"
HOSTED_MANIFEST = DOCS_ROOT / ".well-known" / "rdllm.json"
HOSTED_ARTIFACT_DIR = DOCS_ROOT / ".well-known" / "rdllm"
HOSTED_SCHEMA_MIRROR = DOCS_ROOT / "docs" / "schemas"

MAX_REPORTED_FINDINGS = 50

FORBIDDEN_EXACT_KEYS = {
    "access_token",
    "account_number",
    "api_key",
    "bank_account",
    "bearer_token",
    "chain_of_thought",
    "completion_text",
    "content",
    "customer_data",
    "customer_prompt",
    "developer_prompt",
    "document_text",
    "evidence_text",
    "iban",
    "matched_text",
    "password",
    "payout_account",
    "payout_account_id",
    "private_key",
    "private_reasoning",
    "private_reasoning_text",
    "raw_prompt",
    "refresh_token",
    "response_text",
    "routing_number",
    "scratchpad",
    "secret",
    "session_token",
    "source_body",
    "source_text",
    "swift",
    "system_prompt",
    "tax_id",
    "tool_output_text",
    "user_prompt",
}

MUST_BE_FALSE_PRIVACY_FLAGS = {
    "additional_private_source_text_disclosed",
    "api_key_disclosed",
    "attestor_secret_disclosed",
    "candidate_evidence_text_disclosed",
    "chain_of_thought_disclosed",
    "claim_evidence_text_disclosed",
    "context_text_disclosed",
    "counterevidence_text_disclosed",
    "customer_or_payment_text_disclosed",
    "customer_or_tax_record_disclosed",
    "customer_or_tax_records_disclosed",
    "deployment_key_secret_disclosed",
    "evidence_text_disclosed",
    "feedback_text_disclosed",
    "full_private_receipt_disclosed",
    "full_snapshot_payload_disclosed",
    "hidden_state_disclosed",
    "invoice_text_disclosed",
    "matched_text_disclosed",
    "memory_text_disclosed",
    "notice_text_disclosed",
    "payment_account_disclosed",
    "payment_data_disclosed",
    "payment_identifier_disclosed",
    "payment_text_disclosed",
    "payout_account_disclosed",
    "payout_accounts_disclosed",
    "private_answer_text_disclosed",
    "private_economics_disclosed",
    "private_finance_payload_disclosed",
    "private_ledger_disclosed",
    "private_memory_text_disclosed",
    "private_payment_details_disclosed",
    "private_payout_accounts_disclosed",
    "private_prompt_disclosed",
    "private_prompt_payload_disclosed",
    "private_prompt_text_disclosed",
    "private_reasoning_disclosed",
    "private_response_disclosed",
    "private_salts_disclosed",
    "private_source_corpus_disclosed",
    "private_source_text_disclosed",
    "private_tool_payload_disclosed",
    "private_values_disclosed",
    "prompt_disclosed",
    "prompt_text_disclosed",
    "raw_account_disclosed",
    "raw_answer_text_disclosed",
    "raw_attestation_signatures_disclosed",
    "raw_billing_record_disclosed",
    "raw_billing_records_disclosed",
    "raw_bond_account_disclosed",
    "raw_cache_key_disclosed",
    "raw_claim_text_disclosed",
    "raw_context_text_disclosed",
    "raw_creator_identity_disclosed",
    "raw_customer_account_disclosed",
    "raw_customer_record_disclosed",
    "raw_customer_records_disclosed",
    "raw_customer_or_billing_logs_disclosed",
    "raw_customer_or_tax_records_disclosed",
    "raw_descriptor_disclosed",
    "raw_escrow_accounts_disclosed",
    "raw_evidence_text_disclosed",
    "raw_excerpt_text_redisclosed",
    "raw_finance_record_disclosed",
    "raw_finance_records_disclosed",
    "raw_full_source_text_disclosed",
    "raw_hidden_states_disclosed",
    "raw_http_body_disclosed",
    "raw_issuer_keys_disclosed",
    "raw_key_material_disclosed",
    "raw_license_token_disclosed",
    "raw_media_disclosed",
    "raw_memory_payload_disclosed",
    "raw_model_output_text_disclosed",
    "raw_model_weights_disclosed",
    "raw_native_response_disclosed",
    "raw_output_disclosed",
    "raw_output_text_disclosed",
    "raw_payment_account_disclosed",
    "raw_payment_accounts_disclosed",
    "raw_payment_details_disclosed",
    "raw_payout_accounts_disclosed",
    "raw_private_reasoning_disclosed",
    "raw_private_trace_disclosed",
    "raw_prompt_disclosed",
    "raw_prompt_text_disclosed",
    "raw_protocol_notice_disclosed",
    "raw_provider_response_disclosed",
    "raw_query_text_disclosed",
    "raw_region_text_disclosed",
    "raw_request_disclosed",
    "raw_request_or_response_disclosed",
    "raw_response_disclosed",
    "raw_reward_or_preference_text_disclosed",
    "raw_signal_text_disclosed",
    "raw_snapshot_body_disclosed",
    "raw_source_text_disclosed",
    "raw_tool_output_disclosed",
    "raw_tool_payload_disclosed",
    "raw_tool_result_disclosed",
    "raw_token_logits_disclosed",
    "raw_token_or_secret_disclosed",
    "raw_trace_disclosed",
    "raw_training_text_disclosed",
    "raw_validation_dataset_disclosed",
    "reward_explanation_disclosed",
    "signing_secrets_disclosed",
    "source_quote_text_disclosed",
    "source_secret_disclosed",
    "source_text_disclosed",
    "student_prompt_text_disclosed",
    "student_output_text_disclosed",
    "teacher_output_text_disclosed",
    "training_text_disclosed",
    "verifier_private_notes_disclosed",
    "watch_secret_disclosed",
    "work_text_disclosed",
}

RAW_SECRET_KEY_RE = re.compile(
    r"(^|_)(api_key|access_token|bearer_token|password|private_key|"
    r"refresh_token|secret|session_token)(_|$)"
)
SAFE_SENSITIVE_KEY_SUFFIXES = (
    "_commitment",
    "_disclosed",
    "_digest",
    "_fingerprint",
    "_hash",
    "_hashes",
    "_id",
    "_ids",
    "_key_id",
    "_not_disclosed",
    "_public_key",
    "_root",
)

SECRET_VALUE_PATTERNS = (
    ("openai_or_anthropic_key", re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}")),
    ("aws_access_key", re.compile(r"(?<![A-Z0-9])AKIA[0-9A-Z]{16}(?![A-Z0-9])")),
    ("gcp_api_key", re.compile(r"(?<![A-Za-z0-9])AIza[0-9A-Za-z_-]{35}(?![A-Za-z0-9_-])")),
    (
        "stripe_secret_key",
        re.compile(r"(?<![A-Za-z0-9])(?:sk|rk)_(?:live|test)_[0-9A-Za-z]{16,}"),
    ),
    ("github_token", re.compile(r"(?<![A-Za-z0-9])(?:ghp|gho|ghu|ghs|ghr)_[0-9A-Za-z]{30,}")),
    ("github_pat", re.compile(r"(?<![A-Za-z0-9])github_pat_[0-9A-Za-z_]{30,}")),
    ("slack_token", re.compile(r"(?<![A-Za-z0-9])xox[baprs]-[0-9A-Za-z-]{20,}")),
    ("private_key_pem", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("raw_payout_account", re.compile(r"(?<![A-Za-z0-9])acct_[0-9A-Za-z_]{5,}")),
)


def relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")


def _json_pointer_escape(part: str) -> str:
    return part.replace("~", "~0").replace("/", "~1")


def _iter_hosted_artifact_json() -> list[Path]:
    paths: list[Path] = []
    if HOSTED_MANIFEST.is_file():
        paths.append(HOSTED_MANIFEST)
    if HOSTED_ARTIFACT_DIR.is_dir():
        paths.extend(sorted(HOSTED_ARTIFACT_DIR.glob("*.json")))
    return paths


def _iter_public_files() -> list[Path]:
    roots = [
        DOCS_ROOT / ".well-known",
        HOSTED_SCHEMA_MIRROR,
    ]
    files: list[Path] = []
    for root in roots:
        if root.is_dir():
            files.extend(sorted(path for path in root.rglob("*") if path.is_file()))
    return files


def _safe_sensitive_key(key: str) -> bool:
    return key.endswith(SAFE_SENSITIVE_KEY_SUFFIXES)


def _is_check_name_scope(pointer: str) -> bool:
    return pointer == "/checks" or pointer.endswith("/checks")


def _scan_json_value(
    value: Any,
    *,
    path: Path,
    pointer: str,
    report: dict[str, Any],
) -> None:
    if isinstance(value, dict):
        for raw_key, item in value.items():
            key = str(raw_key)
            normalized_key = _normalize_key(key)
            child_pointer = f"{pointer}/{_json_pointer_escape(key)}"
            if normalized_key in FORBIDDEN_EXACT_KEYS:
                report["forbidden_key_findings"].append(
                    {
                        "path": relpath(path),
                        "pointer": child_pointer,
                        "key": key,
                        "reason": "raw private payload key is not allowed on the hosted public surface",
                    }
                )
            elif (
                RAW_SECRET_KEY_RE.search(normalized_key)
                and not _safe_sensitive_key(normalized_key)
                and not _is_check_name_scope(pointer)
                and not isinstance(item, bool)
            ):
                report["forbidden_key_findings"].append(
                    {
                        "path": relpath(path),
                        "pointer": child_pointer,
                        "key": key,
                        "reason": "secret-looking key is not hash-only or disclosure-only",
                    }
                )
            if normalized_key in MUST_BE_FALSE_PRIVACY_FLAGS and item is not False:
                report["disclosure_flag_findings"].append(
                    {
                        "path": relpath(path),
                        "pointer": child_pointer,
                        "key": key,
                        "value": item,
                        "reason": "public artifact declares private or raw data disclosure",
                    }
                )
            _scan_json_value(item, path=path, pointer=child_pointer, report=report)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_json_value(
                item,
                path=path,
                pointer=f"{pointer}/{index}",
                report=report,
            )
    elif isinstance(value, str):
        _scan_string(value, path=path, pointer=pointer, report=report)


def _scan_string(
    value: str,
    *,
    path: Path,
    pointer: str,
    report: dict[str, Any],
) -> None:
    for pattern_name, pattern in SECRET_VALUE_PATTERNS:
        match = pattern.search(value)
        if match:
            report["secret_value_findings"].append(
                {
                    "path": relpath(path),
                    "pointer": pointer,
                    "pattern": pattern_name,
                    "match_prefix": match.group(0)[:12],
                }
            )


def _scan_public_file(path: Path, report: dict[str, Any]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        report["binary_file_count"] += 1
        return
    for pattern_name, pattern in SECRET_VALUE_PATTERNS:
        match = pattern.search(text)
        if match:
            line_number = text.count("\n", 0, match.start()) + 1
            report["public_file_secret_findings"].append(
                {
                    "path": relpath(path),
                    "line": line_number,
                    "pattern": pattern_name,
                    "match_prefix": match.group(0)[:12],
                }
            )


def audit() -> dict[str, Any]:
    report: dict[str, Any] = {
        "status": "passed",
        "hosted_json_count": 0,
        "public_file_count": 0,
        "binary_file_count": 0,
        "forbidden_key_findings": [],
        "disclosure_flag_findings": [],
        "secret_value_findings": [],
        "public_file_secret_findings": [],
        "errors": [],
    }
    if not HOSTED_MANIFEST.is_file():
        report["errors"].append(f"missing hosted manifest: {relpath(HOSTED_MANIFEST)}")
    if not HOSTED_ARTIFACT_DIR.is_dir():
        report["errors"].append(
            f"missing hosted artifact directory: {relpath(HOSTED_ARTIFACT_DIR)}"
        )

    for path in _iter_hosted_artifact_json():
        report["hosted_json_count"] += 1
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            report["errors"].append(f"invalid JSON in {relpath(path)}: {exc}")
            continue
        _scan_json_value(data, path=path, pointer="", report=report)

    public_files = _iter_public_files()
    report["public_file_count"] = len(public_files)
    for path in public_files:
        _scan_public_file(path, report)

    for finding_type in (
        "forbidden_key_findings",
        "disclosure_flag_findings",
        "secret_value_findings",
        "public_file_secret_findings",
    ):
        for finding in report[finding_type]:
            location = finding["path"]
            if "pointer" in finding:
                location = f"{location}{finding['pointer']}"
            elif "line" in finding:
                location = f"{location}:{finding['line']}"
            report["errors"].append(f"{finding_type}: {location}: {finding['reason'] if 'reason' in finding else finding['pattern']}")

    if report["errors"]:
        report["status"] = "failed"
    return report


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"public_surface_privacy_audit status: {report['status']}",
        f"hosted_json_count: {report['hosted_json_count']}",
        f"public_file_count: {report['public_file_count']}",
        f"forbidden_key_count: {len(report['forbidden_key_findings'])}",
        f"disclosure_flag_count: {len(report['disclosure_flag_findings'])}",
        f"secret_value_count: {len(report['secret_value_findings'])}",
        f"public_file_secret_count: {len(report['public_file_secret_findings'])}",
    ]
    if report["errors"]:
        lines.append("errors:")
        for error in report["errors"][:MAX_REPORTED_FINDINGS]:
            lines.append(f"- {error}")
        remaining = len(report["errors"]) - MAX_REPORTED_FINDINGS
        if remaining > 0:
            lines.append(f"- ... {remaining} more")
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
