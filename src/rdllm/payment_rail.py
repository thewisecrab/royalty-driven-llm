"""Payment-rail authenticity attestations for RDLLM payment execution."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload

PAYMENT_RAIL_ATTESTATION_VERSION = "rdllm-payment-rail-attestation/v1"
PAYMENT_RAIL_ATTESTATION_SCHEMA = "docs/schemas/payment_rail_attestation.schema.json"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L78"
MONEY_QUANT = Decimal("0.000001")

DECLARED_HASH_FIELDS = (
    "trust_registry_hash",
    "attestation_hash",
    "report_hash",
    "contract_hash",
    "bundle_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "envelope_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "output",
    "answer_text",
    "source_text",
    "evidence_text",
    "matched_text",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "customer_id",
    "customer_email",
    "raw_processor_record",
    "raw_payment_account",
    "payment_method",
    "secret",
    "signing_secret",
    "private_key",
}

TRUSTED_PROCESSOR_ROLES = {
    "payment_processor",
    "escrow_processor",
    "regulated_payment_processor",
    "regulated_escrow_processor",
}


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _hashable_processor_attestation(attestation: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in attestation.items()
        if key not in {"attestation_hash", "signature"}
    }


def _hashable_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not key.endswith("_row_hash")}


def _declared_hash(artifact: dict[str, Any]) -> str:
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(artifact)


def _artifact_hash_is_reproducible(artifact: dict[str, Any]) -> bool:
    declared = _declared_hash(artifact)
    if any(artifact.get(field) for field in DECLARED_HASH_FIELDS):
        return hash_payload(
            {
                key: value
                for key, value in artifact.items()
                if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
            }
        ) == declared
    return True


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


def _decimal(value: str | int | float | Decimal) -> Decimal:
    return Decimal(str(value or "0")).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _money(value: str | int | float | Decimal) -> str:
    return format(_decimal(value), "f")


def _processor_role(record_type: str) -> str:
    if record_type == "escrow_settlement":
        return "escrow_processor"
    return "payment_processor"


def _processor_groups(
    payment_execution_report: dict[str, Any],
) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in payment_execution_report.get("processor_record_rows", []):
        key = (
            str(row.get("external_processor", "")),
            str(row.get("settlement_batch_hash", "")),
            str(row.get("record_type", "")),
        )
        groups[key].append(row)
    return dict(groups)


def _active_processor_principals(
    trust_registry: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    principals: dict[str, dict[str, Any]] = {}
    for entry in trust_registry.get("principals", []):
        principal_id = str(entry.get("principal_id", ""))
        role = str(entry.get("role", ""))
        if (
            principal_id
            and role in TRUSTED_PROCESSOR_ROLES
            and entry.get("status") == "active"
        ):
            principals[principal_id] = entry
    return principals


def _group_summary(
    *,
    payment_execution_report_hash: str,
    processor_id: str,
    settlement_batch_hash: str,
    record_type: str,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    currencies = sorted({str(row.get("currency", "")) for row in records})
    record_hashes = sorted(str(row.get("processor_record_hash", "")) for row in records)
    row_hashes = sorted(str(row.get("processor_record_row_hash", "")) for row in records)
    total = sum((_decimal(row.get("settled_amount", "0")) for row in records), Decimal("0"))
    status_values = sorted({str(row.get("settlement_status", "")) for row in records})
    return {
        "payment_execution_report_hash": payment_execution_report_hash,
        "processor_id": processor_id,
        "processor_role": _processor_role(record_type),
        "record_type": record_type,
        "settlement_batch_hash": settlement_batch_hash,
        "processor_record_hashes": record_hashes,
        "processor_record_row_hashes": row_hashes,
        "record_count": len(records),
        "currency": currencies[0] if len(currencies) == 1 else "MULTI",
        "settled_total": _money(total),
        "settlement_status": status_values[0] if len(status_values) == 1 else "mixed",
    }


def make_processor_batch_attestations(
    *,
    payment_execution_report: dict[str, Any],
    processor_secrets: dict[str, str],
    created_at: str | None = None,
) -> list[dict[str, Any]]:
    """Create reference signed processor-batch attestations from execution rows."""

    payment_execution_hash = _declared_hash(payment_execution_report)
    attestations: list[dict[str, Any]] = []
    for index, ((processor_id, batch_hash, record_type), records) in enumerate(
        sorted(_processor_groups(payment_execution_report).items()),
        start=1,
    ):
        attestation = {
            "attestation_version": "rdllm-processor-batch-attestation/v1",
            "attestation_id": f"processor-batch:{index}",
            "created_at": created_at or now_iso(),
            **_group_summary(
                payment_execution_report_hash=payment_execution_hash,
                processor_id=processor_id,
                settlement_batch_hash=batch_hash,
                record_type=record_type,
                records=records,
            ),
            "raw_processor_records_disclosed": False,
        }
        attestation["attestation_hash"] = hash_payload(
            _hashable_processor_attestation(attestation)
        )
        secret = processor_secrets.get(processor_id, "")
        attestation["signature"] = {
            "algorithm": "HMAC-SHA256" if secret else "UNSIGNED",
            "issuer": processor_id,
            "value": (
                sign_payload(_hashable_processor_attestation(attestation), secret)
                if secret
                else ""
            ),
        }
        attestations.append(attestation)
    return attestations


def _attestation_index(
    processor_attestations: list[dict[str, Any]],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for attestation in processor_attestations:
        key = (
            str(attestation.get("processor_id", "")),
            str(attestation.get("settlement_batch_hash", "")),
            str(attestation.get("record_type", "")),
        )
        index.setdefault(key, attestation)
    return index


def _attestation_rows(
    *,
    payment_execution_report_hash: str,
    payment_execution_report: dict[str, Any],
    trust_registry: dict[str, Any],
    processor_attestations: list[dict[str, Any]],
    processor_secrets: dict[str, str],
) -> list[dict[str, Any]]:
    groups = _processor_groups(payment_execution_report)
    active_processors = _active_processor_principals(trust_registry)
    rows: list[dict[str, Any]] = []
    for attestation in processor_attestations:
        key = (
            str(attestation.get("processor_id", "")),
            str(attestation.get("settlement_batch_hash", "")),
            str(attestation.get("record_type", "")),
        )
        expected_records = groups.get(key, [])
        expected = (
            _group_summary(
                payment_execution_report_hash=payment_execution_report_hash,
                processor_id=key[0],
                settlement_batch_hash=key[1],
                record_type=key[2],
                records=expected_records,
            )
            if expected_records
            else {}
        )
        processor = active_processors.get(key[0])
        secret = processor_secrets.get(key[0], "")
        signature = attestation.get("signature", {})
        expected_signature = (
            sign_payload(_hashable_processor_attestation(attestation), secret)
            if secret
            else ""
        )
        record_hashes_match = bool(expected) and sorted(
            attestation.get("processor_record_hashes", [])
        ) == expected.get("processor_record_hashes", [])
        row_hashes_match = bool(expected) and sorted(
            attestation.get("processor_record_row_hashes", [])
        ) == expected.get("processor_record_row_hashes", [])
        totals_match = bool(expected) and _decimal(attestation.get("settled_total", "0")) == _decimal(
            expected.get("settled_total", "0")
        )
        row = {
            "attestation_id": str(attestation.get("attestation_id", "")),
            "processor_id": key[0],
            "processor_role": str(attestation.get("processor_role", "")),
            "record_type": key[2],
            "settlement_batch_hash": key[1],
            "payment_execution_report_hash": str(
                attestation.get("payment_execution_report_hash", "")
            ),
            "registered_processor": processor is not None,
            "processor_key_active": processor is not None
            and processor.get("status") == "active",
            "processor_role_allowed": str(attestation.get("processor_role", ""))
            in TRUSTED_PROCESSOR_ROLES,
            "signature_algorithm": str(signature.get("algorithm", "")),
            "signature_issuer": str(signature.get("issuer", "")),
            "signature_present": bool(signature.get("value", "")),
            "signature_valid": bool(
                secret
                and signature.get("algorithm") == "HMAC-SHA256"
                and signature.get("issuer") == key[0]
                and signature.get("value") == expected_signature
            ),
            "attestation_hash_reproducible": hash_payload(
                _hashable_processor_attestation(attestation)
            )
            == attestation.get("attestation_hash"),
            "payment_execution_report_hash_match": str(
                attestation.get("payment_execution_report_hash", "")
            )
            == payment_execution_report_hash,
            "expected_batch_present": bool(expected_records),
            "record_hashes_match": record_hashes_match,
            "record_row_hashes_match": row_hashes_match,
            "record_count_match": bool(expected)
            and int(attestation.get("record_count", 0) or 0)
            == int(expected.get("record_count", 0) or 0),
            "currency_match": bool(expected)
            and str(attestation.get("currency", "")) == str(expected.get("currency", "")),
            "settled_total_match": totals_match,
            "settlement_status_match": bool(expected)
            and str(attestation.get("settlement_status", ""))
            == str(expected.get("settlement_status", "")),
            "raw_processor_records_disclosed": bool(
                attestation.get("raw_processor_records_disclosed", False)
            ),
        }
        row["attestation_row_hash"] = hash_payload(_hashable_row(row))
        rows.append(row)
    return sorted(
        rows,
        key=lambda row: (
            row["processor_id"],
            row["settlement_batch_hash"],
            row["record_type"],
            row["attestation_id"],
        ),
    )


def _coverage_rows(
    payment_execution_report: dict[str, Any],
    attestation_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    signed_keys = {
        (
            row["processor_id"],
            row["settlement_batch_hash"],
            row["record_type"],
        )
        for row in attestation_rows
        if row["signature_valid"]
        and row["record_hashes_match"]
        and row["record_row_hashes_match"]
        and row["settled_total_match"]
    }
    rows: list[dict[str, Any]] = []
    for key, records in sorted(_processor_groups(payment_execution_report).items()):
        row = {
            "processor_id": key[0],
            "settlement_batch_hash": key[1],
            "record_type": key[2],
            "processor_record_count": len(records),
            "processor_record_root": hash_payload(
                sorted(str(record.get("processor_record_hash", "")) for record in records)
            ),
            "signed_processor_attestation_present": key in signed_keys,
        }
        row["coverage_row_hash"] = hash_payload(_hashable_row(row))
        rows.append(row)
    return rows


def make_payment_rail_attestation(
    *,
    payment_execution_report: dict[str, Any],
    trust_registry: dict[str, Any],
    processor_attestations: list[dict[str, Any]],
    processor_secrets: dict[str, str],
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a report proving payment execution evidence came from trusted rails."""

    payment_execution_hash = _declared_hash(payment_execution_report)
    private_paths = _contains_private_fields(
        {
            "payment_execution_report": payment_execution_report,
            "trust_registry": trust_registry,
            "processor_attestations": processor_attestations,
        }
    )
    attestation_rows = _attestation_rows(
        payment_execution_report_hash=payment_execution_hash,
        payment_execution_report=payment_execution_report,
        trust_registry=trust_registry,
        processor_attestations=processor_attestations,
        processor_secrets=processor_secrets,
    )
    coverage_rows = _coverage_rows(payment_execution_report, attestation_rows)
    required_processor_ids = sorted(
        {
            str(row.get("external_processor", ""))
            for row in payment_execution_report.get("processor_record_rows", [])
            if row.get("external_processor")
        }
    )
    active_processors = _active_processor_principals(trust_registry)
    checks = {
        "payment_execution_report_ready": payment_execution_report.get("summary", {}).get(
            "status"
        )
        == "ready"
        and payment_execution_report.get("summary", {}).get("target_certification_level")
        == "RDLLM-L77",
        "payment_execution_report_hash_reproducible": _artifact_hash_is_reproducible(
            payment_execution_report
        ),
        "trust_registry_ready": trust_registry.get("summary", {}).get("status") == "ready",
        "trust_registry_hash_reproducible": _artifact_hash_is_reproducible(trust_registry),
        "all_required_processors_registered": all(
            processor_id in active_processors for processor_id in required_processor_ids
        ),
        "all_processor_attestations_registered": all(
            row["registered_processor"] and row["processor_key_active"]
            for row in attestation_rows
        ),
        "all_processor_roles_allowed": all(
            row["processor_role_allowed"] for row in attestation_rows
        ),
        "all_processor_attestation_hashes_reproducible": all(
            row["attestation_hash_reproducible"] for row in attestation_rows
        ),
        "all_processor_signatures_valid": bool(attestation_rows)
        and all(row["signature_valid"] for row in attestation_rows),
        "all_processor_attestations_bind_payment_execution_report": all(
            row["payment_execution_report_hash_match"] for row in attestation_rows
        ),
        "all_processor_record_hashes_match_execution_report": all(
            row["record_hashes_match"] and row["record_row_hashes_match"]
            for row in attestation_rows
        ),
        "all_processor_totals_match_execution_report": all(
            row["record_count_match"]
            and row["currency_match"]
            and row["settled_total_match"]
            and row["settlement_status_match"]
            for row in attestation_rows
        ),
        "all_execution_batches_have_signed_processor_attestations": bool(coverage_rows)
        and all(row["signed_processor_attestation_present"] for row in coverage_rows),
        "no_duplicate_or_unmatched_execution_records": int(
            payment_execution_report.get("summary", {}).get(
                "duplicate_processor_record_count", 0
            )
            or 0
        )
        == 0
        and int(
            payment_execution_report.get("summary", {}).get(
                "unmatched_processor_record_count", 0
            )
            or 0
        )
        == 0,
        "private_payment_rail_fields_absent": not private_paths
        and not any(row["raw_processor_records_disclosed"] for row in attestation_rows),
    }
    report = {
        "report_version": PAYMENT_RAIL_ATTESTATION_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "rail_policy": {
            "profile": "rdllm-trusted-payment-rail-attestation/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": "RDLLM-L77",
            "processor_roles_allowed": sorted(TRUSTED_PROCESSOR_ROLES),
            "external_processor_signature_required": True,
            "trust_registry_required": True,
            "raw_payment_records_forbidden": True,
        },
        "required_processor_rows": [
            {
                "processor_id": processor_id,
                "registered": processor_id in active_processors,
                "entry_hash": active_processors.get(processor_id, {}).get("entry_hash", ""),
                "required_processor_row_hash": hash_payload(
                    {
                        "processor_id": processor_id,
                        "registered": processor_id in active_processors,
                        "entry_hash": active_processors.get(processor_id, {}).get(
                            "entry_hash", ""
                        ),
                    }
                ),
            }
            for processor_id in required_processor_ids
        ],
        "processor_attestation_rows": attestation_rows,
        "batch_coverage_rows": coverage_rows,
        "checks": checks,
        "commitments": {
            "payment_execution_report_hash": payment_execution_hash,
            "trust_registry_hash": _declared_hash(trust_registry),
            "required_processor_root": hash_payload(required_processor_ids),
            "processor_attestation_root": hash_payload(attestation_rows),
            "batch_coverage_root": hash_payload(coverage_rows),
            "processor_attestation_input_root": hash_payload(processor_attestations),
        },
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "required_processor_count": len(required_processor_ids),
            "processor_attestation_count": len(attestation_rows),
            "covered_batch_count": sum(
                1 for row in coverage_rows if row["signed_processor_attestation_present"]
            ),
            "required_batch_count": len(coverage_rows),
            "signed_external_payment_rail_attested": all(checks.values()),
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "raw_processor_records_disclosed": False,
            "raw_payout_accounts_disclosed": False,
            "raw_customer_or_tax_records_disclosed": False,
            "uses_processor_record_hashes": True,
            "uses_payment_rail_signatures": True,
        },
        "schemas": {
            "payment_rail_attestation": PAYMENT_RAIL_ATTESTATION_SCHEMA,
            "payment_execution_report": "docs/schemas/payment_execution_report.schema.json",
            "trust_registry": "docs/schemas/trust_registry.schema.json",
        },
    }
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


def validate_payment_rail_attestation_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "rail_policy",
        "required_processor_rows",
        "processor_attestation_rows",
        "batch_coverage_rows",
        "checks",
        "commitments",
        "summary",
        "privacy",
        "schemas",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing payment rail attestation field: {key}")
    if errors:
        return errors
    if report.get("report_version") != PAYMENT_RAIL_ATTESTATION_VERSION:
        errors.append("payment rail attestation version is unsupported")
    if report.get("rail_policy", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("payment rail target certification level is unsupported")
    for key in (
        "payment_execution_report_hash",
        "trust_registry_hash",
        "required_processor_root",
        "processor_attestation_root",
        "batch_coverage_root",
    ):
        if key not in report.get("commitments", {}):
            errors.append(f"missing payment rail commitment: {key}")
    for key in (
        "status",
        "target_certification_level",
        "required_processor_count",
        "processor_attestation_count",
        "covered_batch_count",
        "required_batch_count",
        "signed_external_payment_rail_attested",
    ):
        if key not in report.get("summary", {}):
            errors.append(f"missing payment rail summary field: {key}")
    if "payment_rail_attestation" not in report.get("schemas", {}):
        errors.append("missing payment rail attestation schema")
    return errors


def verify_payment_rail_attestation(
    report: dict[str, Any],
    *,
    payment_execution_report: dict[str, Any],
    trust_registry: dict[str, Any],
    processor_attestations: list[dict[str, Any]],
    processor_secrets: dict[str, str],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify payment-rail authenticity against execution and trust artifacts."""

    errors = validate_payment_rail_attestation_shape(report)
    if errors:
        return errors
    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("payment rail attestation hash is not reproducible")

    expected = make_payment_rail_attestation(
        payment_execution_report=payment_execution_report,
        trust_registry=trust_registry,
        processor_attestations=processor_attestations,
        processor_secrets=processor_secrets,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "rail_policy",
        "required_processor_rows",
        "processor_attestation_rows",
        "batch_coverage_rows",
        "checks",
        "commitments",
        "summary",
        "privacy",
        "schemas",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"payment rail attestation {key} does not match inputs")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("payment rail attestation hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("payment rail attestation status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"payment rail check failed: {check}")
    if _contains_private_fields(report):
        errors.append("payment rail attestation exposes private payment fields")
    if signing_secret:
        signature = report.get("signature", {})
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("payment rail attestation is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("payment rail attestation signature is invalid")
    return errors
