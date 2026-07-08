"""Nonce-bound private audit challenges for selective-disclosure receipts."""

from __future__ import annotations

from typing import Any, Iterable

from rdllm.disclosure import verify_selective_disclosure_package
from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    payload_disclosure_leaves,
    sign_payload,
)

PRIVATE_AUDIT_VERSION = "rdllm-private-audit-challenge/v1"
PRIVATE_AUDIT_SCHEMA = "docs/schemas/private_audit_challenge.schema.json"


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _hashable_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "audit_row_hash"}


def _dedupe_paths(paths: Iterable[str]) -> list[str]:
    return sorted({str(path) for path in paths if str(path)})


def _package_leaves_by_path(
    package: dict[str, Any],
) -> dict[str, tuple[str, dict[str, Any]]]:
    leaves: dict[str, tuple[str, dict[str, Any]]] = {}
    for leaf in package.get("disclosed", []):
        path = str(leaf.get("path", ""))
        if path:
            leaves[path] = ("disclosed", leaf)
    for leaf in package.get("redacted", []):
        path = str(leaf.get("path", ""))
        if path:
            leaves[path] = ("redacted", leaf)
    return leaves


def _private_leaves_by_path(receipt: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(leaf.get("path", "")): leaf
        for leaf in payload_disclosure_leaves(receipt.get("payload", {}))
        if leaf.get("path")
    }


def _path_category(path: str) -> str:
    if path.startswith("/grounding/source_accesses/"):
        return "source_access_telemetry"
    if path.startswith("/grounding/sources/") and path.endswith("/quote"):
        return "source_quote_text"
    if path.startswith("/grounding/sources/"):
        return "source_metadata"
    if path.startswith("/grounding/claims/") and path.endswith(
        ("/claim", "/evidence_text")
    ):
        return "claim_private_text"
    if path.startswith("/grounding/claims/"):
        return "claim_support_metadata"
    if path.startswith("/economics/"):
        return "royalty_economics"
    if path.startswith("/rights/decisions/"):
        return "rights_decision"
    if path.startswith("/registry/decisions/"):
        return "registry_decision"
    if path.startswith("/event/"):
        return "event_integrity"
    if path.startswith("/privacy/"):
        return "privacy_commitment"
    return "receipt_payload"


def _is_private_path(path: str) -> bool:
    return (
        path.startswith("/grounding/source_accesses/")
        or path.startswith("/economics/")
        or path.startswith("/rights/decisions/")
        or path.startswith("/registry/decisions/")
        or path.endswith("/quote")
        or path.endswith("/evidence_text")
        or path.endswith("/payout_account")
    )


def _is_sensitive_value_path(path: str) -> bool:
    return (
        path.endswith("/quote")
        or path.endswith("/evidence_text")
        or path.endswith("/access_id")
        or path.endswith("/payout_account")
        or path.endswith("/matched_text")
    )


def _opening_commitment(
    *,
    path: str,
    leaf_hash: str,
    value_hash: str,
    salt_hash: str,
    package_hash: str,
    receipt_hash: str,
    challenge_nonce: str,
) -> str:
    return hash_payload(
        {
            "challenge_nonce": challenge_nonce,
            "leaf_hash": leaf_hash,
            "package_hash": package_hash,
            "path": path,
            "receipt_hash": receipt_hash,
            "salt_hash": salt_hash,
            "value_hash": value_hash,
            "version": PRIVATE_AUDIT_VERSION,
        }
    )


def _challenge_row(
    *,
    path: str,
    package_leaf: tuple[str, dict[str, Any]] | None,
    private_leaf: dict[str, Any] | None,
    package_hash: str,
    receipt_hash: str,
    challenge_nonce: str,
) -> dict[str, Any]:
    disclosure_status = package_leaf[0] if package_leaf else "missing"
    package_leaf_hash = ""
    if package_leaf:
        package_leaf_hash = str(package_leaf[1].get("leaf_hash", ""))
    private_leaf_hash = str(private_leaf.get("leaf_hash", "")) if private_leaf else ""
    leaf_hash = package_leaf_hash or private_leaf_hash
    value_hash = hash_payload(private_leaf.get("value")) if private_leaf else ""
    salt_hash = hash_payload(private_leaf.get("salt", "")) if private_leaf else ""
    row = {
        "path": path,
        "category": _path_category(path),
        "disclosure_status": disclosure_status,
        "private_path": _is_private_path(path),
        "leaf_hash": leaf_hash,
        "value_hash": value_hash,
        "salt_hash": salt_hash,
        "opening_commitment": _opening_commitment(
            path=path,
            leaf_hash=leaf_hash,
            value_hash=value_hash,
            salt_hash=salt_hash,
            package_hash=package_hash,
            receipt_hash=receipt_hash,
            challenge_nonce=challenge_nonce,
        ),
        "checks": {
            "path_present_in_package": package_leaf is not None,
            "path_present_in_private_receipt": private_leaf is not None,
            "package_leaf_matches_private_leaf": (
                package_leaf is not None
                and private_leaf is not None
                and package_leaf_hash == private_leaf_hash
            ),
            "commitment_nonce_bound": bool(challenge_nonce),
            "private_value_disclosed_in_report": False,
        },
    }
    row["audit_row_hash"] = hash_payload(_hashable_row(row))
    return row


def _private_values_absent(report: dict[str, Any], receipt: dict[str, Any]) -> bool:
    rendered = canonical_json(report)
    for leaf in payload_disclosure_leaves(receipt.get("payload", {})):
        path = str(leaf.get("path", ""))
        if not _is_sensitive_value_path(path):
            continue
        value = leaf.get("value")
        if not isinstance(value, str):
            continue
        if len(value) < 4:
            continue
        if value in rendered:
            return False
    return True


def make_private_audit_challenge_report(
    *,
    package: dict[str, Any],
    receipt: dict[str, Any],
    requested_paths: Iterable[str],
    auditor_id: str,
    challenge_nonce: str,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a public, nonce-bound challenge certificate over private receipt paths."""

    paths = _dedupe_paths(requested_paths)
    package_hash = str(package.get("package_hash", ""))
    receipt_hash = str(receipt.get("receipt_hash", ""))
    package_leaves = _package_leaves_by_path(package)
    private_leaves = _private_leaves_by_path(receipt)
    rows = [
        _challenge_row(
            path=path,
            package_leaf=package_leaves.get(path),
            private_leaf=private_leaves.get(path),
            package_hash=package_hash,
            receipt_hash=receipt_hash,
            challenge_nonce=challenge_nonce,
        )
        for path in paths
    ]
    standalone_errors = verify_selective_disclosure_package(package)
    private_errors = verify_selective_disclosure_package(
        package,
        receipt,
        signing_secret=signing_secret,
    )
    verification = {
        "selective_disclosure_package_verified": not standalone_errors,
        "private_receipt_opened_by_authorized_verifier": not private_errors,
        "all_requested_paths_committed": bool(paths)
        and all(row["checks"]["path_present_in_package"] for row in rows),
        "all_requested_paths_opened_from_private_receipt": bool(paths)
        and all(row["checks"]["path_present_in_private_receipt"] for row in rows),
        "all_package_leaves_match_private_receipt": bool(paths)
        and all(row["checks"]["package_leaf_matches_private_leaf"] for row in rows),
        "all_opening_commitments_nonce_bound": bool(challenge_nonce)
        and all(row["checks"]["commitment_nonce_bound"] for row in rows),
        "challenge_rows_hash_reproducible": all(
            hash_payload(_hashable_row(row)) == row.get("audit_row_hash")
            for row in rows
        ),
        "no_private_values_disclosed": True,
    }
    row_hashes = [row["audit_row_hash"] for row in rows]
    report = {
        "audit_version": PRIVATE_AUDIT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "audit_challenge": {
            "auditor_id": auditor_id,
            "challenge_nonce": challenge_nonce,
            "requested_paths": paths,
            "requested_path_root": hash_payload(paths),
            "challenge_binding_hash": hash_payload(
                {
                    "auditor_id": auditor_id,
                    "challenge_nonce": challenge_nonce,
                    "package_hash": package_hash,
                    "receipt_hash": receipt_hash,
                    "requested_path_root": hash_payload(paths),
                    "version": PRIVATE_AUDIT_VERSION,
                }
            ),
        },
        "subject": {
            "receipt_hash": receipt_hash,
            "payload_hash": package.get("payload_hash", ""),
            "payload_disclosure_root": package.get("payload_disclosure_root", ""),
            "selective_disclosure_package_hash": package_hash,
            "public_receipt_hash": hash_payload(package.get("public_receipt", {})),
        },
        "challenge_rows": rows,
        "verification": verification,
        "commitments": {
            "challenge_row_root": hash_payload(row_hashes),
            "requested_path_root": hash_payload(paths),
            "package_hash": package_hash,
            "receipt_hash": receipt_hash,
            "payload_disclosure_root": package.get("payload_disclosure_root", ""),
        },
        "summary": {
            "status": "pending",
            "requested_path_count": len(paths),
            "redacted_path_count": sum(
                1 for row in rows if row["disclosure_status"] == "redacted"
            ),
            "disclosed_path_count": sum(
                1 for row in rows if row["disclosure_status"] == "disclosed"
            ),
            "missing_path_count": sum(
                1 for row in rows if row["disclosure_status"] == "missing"
            ),
            "private_audit_supported": True,
            "public_report_discloses_only_hashes_categories_and_status": True,
        },
        "schemas": {
            "private_audit_challenge": PRIVATE_AUDIT_SCHEMA,
            "selective_disclosure_package": "docs/schemas/selective_disclosure_package.schema.json",
            "attribution_receipt": "docs/schemas/attribution_receipt.schema.json",
        },
        "privacy": {
            "private_prompt_text_disclosed": False,
            "private_answer_text_disclosed": False,
            "private_source_text_disclosed": False,
            "private_economics_disclosed": False,
            "private_payout_accounts_disclosed": False,
            "private_salts_disclosed": False,
            "private_values_disclosed": False,
            "paths_named_but_values_hidden": True,
            "auditor_nonce_required": True,
        },
    }
    report["verification"]["no_private_values_disclosed"] = _private_values_absent(
        report,
        receipt,
    )
    report["summary"]["status"] = (
        "verified" if all(report["verification"].values()) else "failed"
    )
    report["report_hash"] = hash_payload(_hashable_report(report))
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_report(report), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return report


def validate_private_audit_challenge_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "audit_version",
        "issuer",
        "created_at",
        "audit_challenge",
        "subject",
        "challenge_rows",
        "verification",
        "commitments",
        "summary",
        "schemas",
        "privacy",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing private audit challenge field: {key}")
    if errors:
        return errors
    if report.get("audit_version") != PRIVATE_AUDIT_VERSION:
        errors.append("private audit challenge version is unsupported")
    for key in (
        "auditor_id",
        "challenge_nonce",
        "requested_paths",
        "requested_path_root",
        "challenge_binding_hash",
    ):
        if key not in report.get("audit_challenge", {}):
            errors.append(f"missing private audit challenge request field: {key}")
    for key in (
        "receipt_hash",
        "payload_hash",
        "payload_disclosure_root",
        "selective_disclosure_package_hash",
        "public_receipt_hash",
    ):
        if key not in report.get("subject", {}):
            errors.append(f"missing private audit subject field: {key}")
    for row in report.get("challenge_rows", []):
        for key in (
            "path",
            "category",
            "disclosure_status",
            "private_path",
            "leaf_hash",
            "value_hash",
            "salt_hash",
            "opening_commitment",
            "checks",
            "audit_row_hash",
        ):
            if key not in row:
                errors.append(f"missing private audit row field: {key}")
    for key in (
        "challenge_row_root",
        "requested_path_root",
        "package_hash",
        "receipt_hash",
        "payload_disclosure_root",
    ):
        if key not in report.get("commitments", {}):
            errors.append(f"missing private audit commitment field: {key}")
    if "private_audit_challenge" not in report.get("schemas", {}):
        errors.append("missing private audit schema")
    return errors


def verify_private_audit_challenge_report(
    report: dict[str, Any],
    *,
    package: dict[str, Any],
    receipt: dict[str, Any] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a private audit challenge report against package and optional receipt."""

    errors = validate_private_audit_challenge_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("private audit challenge hash is not reproducible")

    if package.get("package_hash") != report.get("commitments", {}).get("package_hash"):
        errors.append("private audit challenge package hash does not match package")
    if package.get("package_hash") != report.get("subject", {}).get(
        "selective_disclosure_package_hash"
    ):
        errors.append("private audit challenge subject package hash does not match package")
    if package.get("payload_disclosure_root") != report.get("commitments", {}).get(
        "payload_disclosure_root"
    ):
        errors.append("private audit disclosure root does not match package")

    package_errors = verify_selective_disclosure_package(
        package,
        receipt,
        signing_secret=signing_secret,
    )
    errors.extend(f"selective disclosure: {error}" for error in package_errors)

    requested_paths = _dedupe_paths(
        report.get("audit_challenge", {}).get("requested_paths", [])
    )
    if hash_payload(requested_paths) != report.get("audit_challenge", {}).get(
        "requested_path_root"
    ):
        errors.append("private audit requested path root is not reproducible")
    if hash_payload(requested_paths) != report.get("commitments", {}).get(
        "requested_path_root"
    ):
        errors.append("private audit commitment path root is not reproducible")
    expected_binding_hash = hash_payload(
        {
            "auditor_id": report.get("audit_challenge", {}).get("auditor_id", ""),
            "challenge_nonce": report.get("audit_challenge", {}).get(
                "challenge_nonce", ""
            ),
            "package_hash": package.get("package_hash", ""),
            "receipt_hash": report.get("commitments", {}).get("receipt_hash", ""),
            "requested_path_root": hash_payload(requested_paths),
            "version": PRIVATE_AUDIT_VERSION,
        }
    )
    if expected_binding_hash != report.get("audit_challenge", {}).get(
        "challenge_binding_hash"
    ):
        errors.append("private audit challenge binding hash is not reproducible")

    row_hashes: list[str] = []
    package_leaves = _package_leaves_by_path(package)
    row_paths = [str(row.get("path", "")) for row in report.get("challenge_rows", [])]
    if row_paths != requested_paths:
        errors.append("private audit challenge rows do not match requested paths")
    for row in report.get("challenge_rows", []):
        path = str(row.get("path", ""))
        expected_row_hash = hash_payload(_hashable_row(row))
        if expected_row_hash != row.get("audit_row_hash"):
            errors.append(f"private audit row hash is not reproducible: {path}")
        row_hashes.append(str(row.get("audit_row_hash", "")))
        package_leaf = package_leaves.get(path)
        if package_leaf is None:
            errors.append(f"private audit row path is missing from package: {path}")
            continue
        if row.get("disclosure_status") != package_leaf[0]:
            errors.append(f"private audit row disclosure status mismatch: {path}")
        if row.get("leaf_hash") != package_leaf[1].get("leaf_hash"):
            errors.append(f"private audit row leaf hash mismatch: {path}")
        expected_opening_commitment = _opening_commitment(
            path=path,
            leaf_hash=str(row.get("leaf_hash", "")),
            value_hash=str(row.get("value_hash", "")),
            salt_hash=str(row.get("salt_hash", "")),
            package_hash=str(package.get("package_hash", "")),
            receipt_hash=str(report.get("commitments", {}).get("receipt_hash", "")),
            challenge_nonce=str(
                report.get("audit_challenge", {}).get("challenge_nonce", "")
            ),
        )
        if expected_opening_commitment != row.get("opening_commitment"):
            errors.append(f"private audit row opening commitment mismatch: {path}")
        if row.get("category") != _path_category(path):
            errors.append(f"private audit row category mismatch: {path}")
        if row.get("private_path") != _is_private_path(path):
            errors.append(f"private audit row privacy classification mismatch: {path}")
        if "value" in row or "salt" in row:
            errors.append(f"private audit row leaks raw opening material: {path}")
    if hash_payload(row_hashes) != report.get("commitments", {}).get(
        "challenge_row_root"
    ):
        errors.append("private audit challenge row root is not reproducible")

    if receipt is not None:
        expected = make_private_audit_challenge_report(
            package=package,
            receipt=receipt,
            requested_paths=requested_paths,
            auditor_id=report.get("audit_challenge", {}).get("auditor_id", ""),
            challenge_nonce=report.get("audit_challenge", {}).get(
                "challenge_nonce", ""
            ),
            issuer=report.get("issuer", DEFAULT_ISSUER),
            created_at=report.get("created_at", ""),
            signing_secret=signing_secret,
        )
        for key in (
            "audit_challenge",
            "subject",
            "challenge_rows",
            "verification",
            "commitments",
            "summary",
            "schemas",
            "privacy",
        ):
            if expected.get(key) != report.get(key):
                errors.append(f"private audit challenge {key} does not match private receipt")
        if expected.get("report_hash") != report.get("report_hash"):
            errors.append("private audit challenge hash does not match private receipt")
        if report.get("summary", {}).get("status") != "verified":
            errors.append("private audit challenge status is not verified")
        if not all(bool(value) for value in report.get("verification", {}).values()):
            errors.append("private audit challenge verification checks are not all true")

    if report.get("privacy", {}).get("private_values_disclosed") is not False:
        errors.append("private audit challenge must not disclose private values")
    if report.get("privacy", {}).get("private_salts_disclosed") is not False:
        errors.append("private audit challenge must not disclose private salts")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("private audit challenge is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("private audit challenge signature is invalid")
    return errors
