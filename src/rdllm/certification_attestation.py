"""Signed certification attestations for RDLLM conformance reports."""

from __future__ import annotations

from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload

CERTIFICATION_ATTESTATION_VERSION = "rdllm-certification-attestation/v1"
CERTIFICATION_ATTESTATION_SCHEMA = "docs/schemas/certification_attestation.schema.json"
MINIMUM_ATTESTABLE_LEVEL = "RDLLM-L51"

PRIVATE_FIELD_NAMES = {
    "prompt",
    "output",
    "answer_text",
    "source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "customer_id",
    "customer_email",
    "invoice_text",
    "payment_method",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "secret",
    "signing_secret",
    "private_key",
    "private_key_material",
}


def _hashable_attestation(attestation: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in attestation.items()
        if key not in {"attestation_hash", "signature"}
    }


def _hashable_certification_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _report_hash(report: dict[str, Any]) -> str:
    declared = report.get("report_hash")
    if isinstance(declared, str) and declared:
        return declared
    return hash_payload(_hashable_certification_report(report))


def _report_hash_reproducible(report: dict[str, Any]) -> bool:
    declared = report.get("report_hash")
    return (
        isinstance(declared, str)
        and bool(declared)
        and hash_payload(_hashable_certification_report(report)) == declared
    )


def _level_number(level: str) -> int:
    try:
        return int(level.rsplit("L", 1)[1])
    except (IndexError, ValueError):
        return -1


def _case_status_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in report.get("cases", []):
        row = {
            "id": str(case.get("id", "")),
            "status": str(case.get("status", "")),
            "check_root": hash_payload(case.get("checks", {})),
            "artifact_root": hash_payload(case.get("artifacts", {})),
            "error_root": hash_payload(case.get("errors", [])),
        }
        row["case_status_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _contains_private_fields(value: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}" if path else f"/{key}"
            if key in PRIVATE_FIELD_NAMES:
                findings.append(child_path)
            findings.extend(_contains_private_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_contains_private_fields(child, f"{path}/{index}"))
    return findings


def _summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary", {})
    return {
        "status": str(summary.get("status", "")),
        "highest_level": str(summary.get("highest_level", "")),
        "case_count": int(summary.get("case_count", 0) or 0),
        "passed": int(summary.get("passed", 0) or 0),
        "failed": int(summary.get("failed", 0) or 0),
        "score": float(summary.get("score", 0.0) or 0.0),
    }


def make_certification_attestation(
    certification_report: dict[str, Any],
    *,
    certifier_id: str = "certifier:rdllm-reference",
    target_provider: str = "provider:unspecified",
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    valid_until: str = "",
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public, signed attestation over a certification report hash."""

    summary = _summary(certification_report)
    case_rows = _case_status_rows(certification_report)
    report_hash_reproducible = _report_hash_reproducible(certification_report)
    all_cases_passed = (
        summary["case_count"] == len(case_rows)
        and summary["passed"] == len(case_rows)
        and summary["failed"] == 0
        and all(row["status"] == "passed" for row in case_rows)
    )
    private_paths = _contains_private_fields(
        {
            "subject": {
                "certification_version": certification_report.get(
                    "certification_version",
                    "",
                ),
                "suite": certification_report.get("suite", ""),
                "issued_at": certification_report.get("issued_at", ""),
                "implementation_hash": hash_payload(
                    certification_report.get("implementation", {})
                ),
                "levels_root": hash_payload(certification_report.get("levels", {})),
                "case_status_root": hash_payload(case_rows),
                "certification_report_hash": _report_hash(certification_report),
            },
            "certification_summary": summary,
        }
    )
    checks = {
        "certification_report_hash_reproducible": report_hash_reproducible,
        "certification_report_passed": summary["status"] == "passed",
        "highest_level_at_least_l51": _level_number(summary["highest_level"])
        >= _level_number(MINIMUM_ATTESTABLE_LEVEL),
        "case_count_matches_case_status_rows": summary["case_count"] == len(case_rows),
        "all_cases_passed": all_cases_passed,
        "failed_case_root_empty": hash_payload(
            [row for row in case_rows if row["status"] != "passed"]
        )
        == hash_payload([]),
        "case_status_root_bound": bool(case_rows),
        "private_report_payload_not_embedded": True,
        "private_field_names_absent": not private_paths,
        "schema_declared": bool(CERTIFICATION_ATTESTATION_SCHEMA),
    }
    attestation = {
        "attestation_version": CERTIFICATION_ATTESTATION_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "valid_until": valid_until,
        "certifier": {
            "id": certifier_id,
            "role": "certification_authority",
            "policy": "rdllm-public-conformance-attestation/v1",
        },
        "subject": {
            "target_provider": target_provider,
            "certification_version": certification_report.get(
                "certification_version",
                "",
            ),
            "suite": certification_report.get("suite", ""),
            "issued_at": certification_report.get("issued_at", ""),
            "certification_report_hash": _report_hash(certification_report),
            "implementation_hash": hash_payload(
                certification_report.get("implementation", {})
            ),
            "levels_root": hash_payload(certification_report.get("levels", {})),
            "case_status_root": hash_payload(case_rows),
            "case_status_row_count": len(case_rows),
        },
        "certification_summary": summary,
        "checks": checks,
        "commitments": {
            "schema": CERTIFICATION_ATTESTATION_SCHEMA,
            "minimum_attestable_level": MINIMUM_ATTESTABLE_LEVEL,
            "certification_report_hash": _report_hash(certification_report),
            "summary_hash": hash_payload(summary),
            "implementation_hash": hash_payload(
                certification_report.get("implementation", {})
            ),
            "levels_root": hash_payload(certification_report.get("levels", {})),
            "case_status_root": hash_payload(case_rows),
            "failed_case_root": hash_payload(
                [row for row in case_rows if row["status"] != "passed"]
            ),
        },
        "summary": {
            "status": "attested" if all(checks.values()) else "failed",
            "target_certification_level": "RDLLM-L52",
            "attested_highest_level": summary["highest_level"],
            "attested_case_count": summary["case_count"],
            "failed_check_count": sum(1 for value in checks.values() if value is not True),
            "private_input_field_count": len(private_paths),
        },
        "privacy": {
            "certification_report_payload_embedded": False,
            "case_artifacts_embedded": False,
            "private_prompt_or_source_text_disclosed": False,
            "customer_or_payment_text_disclosed": False,
            "attestation_uses_hashes_and_case_status_roots": True,
        },
    }
    attestation["attestation_hash"] = hash_payload(_hashable_attestation(attestation))
    attestation["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_attestation(attestation), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return attestation


def validate_certification_attestation_shape(attestation: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "attestation_version",
        "issuer",
        "created_at",
        "valid_until",
        "certifier",
        "subject",
        "certification_summary",
        "checks",
        "commitments",
        "summary",
        "privacy",
        "attestation_hash",
        "signature",
    )
    for key in required:
        if key not in attestation:
            errors.append(f"missing certification attestation field: {key}")
    if errors:
        return errors
    if attestation.get("attestation_version") != CERTIFICATION_ATTESTATION_VERSION:
        errors.append("certification attestation version is unsupported")
    for key in ("id", "role", "policy"):
        if key not in attestation.get("certifier", {}):
            errors.append(f"missing certification certifier field: {key}")
    for key in (
        "target_provider",
        "certification_version",
        "suite",
        "certification_report_hash",
        "implementation_hash",
        "levels_root",
        "case_status_root",
        "case_status_row_count",
    ):
        if key not in attestation.get("subject", {}):
            errors.append(f"missing certification attestation subject field: {key}")
    for key in (
        "certification_report_hash_reproducible",
        "certification_report_passed",
        "highest_level_at_least_l51",
        "case_count_matches_case_status_rows",
        "all_cases_passed",
        "failed_case_root_empty",
        "case_status_root_bound",
        "private_report_payload_not_embedded",
        "private_field_names_absent",
        "schema_declared",
    ):
        if key not in attestation.get("checks", {}):
            errors.append(f"missing certification attestation check: {key}")
    return errors


def verify_certification_attestation(
    attestation: dict[str, Any],
    certification_report: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a signed certification attestation against its certification report."""

    errors = validate_certification_attestation_shape(attestation)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_attestation(attestation))
    if expected_hash != attestation.get("attestation_hash"):
        errors.append("certification attestation hash is not reproducible")

    expected = make_certification_attestation(
        certification_report,
        certifier_id=attestation.get("certifier", {}).get(
            "id",
            "certifier:rdllm-reference",
        ),
        target_provider=attestation.get("subject", {}).get(
            "target_provider",
            "provider:unspecified",
        ),
        issuer=attestation.get("issuer", DEFAULT_ISSUER),
        created_at=attestation.get("created_at", ""),
        valid_until=attestation.get("valid_until", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "certifier",
        "subject",
        "certification_summary",
        "checks",
        "commitments",
        "summary",
        "privacy",
    ):
        if expected.get(key) != attestation.get(key):
            errors.append(f"certification attestation {key} does not match report")
    if expected.get("attestation_hash") != attestation.get("attestation_hash"):
        errors.append("certification attestation hash does not match report")

    for check, passed in attestation.get("checks", {}).items():
        if passed is not True:
            errors.append(f"certification attestation check failed: {check}")
    if attestation.get("summary", {}).get("status") != "attested":
        errors.append("certification attestation status is not attested")

    signature = attestation.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_attestation(attestation), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("certification attestation is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("certification attestation signature is invalid")

    return errors
