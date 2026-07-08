"""Hash-bound finance ledger attestations for RDLLM revenue pools."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload
from rdllm.revenue_allocation import validate_revenue_allocation_report_shape

FINANCE_LEDGER_ATTESTATION_VERSION = "rdllm-finance-ledger-attestation/v1"
FINANCE_LEDGER_ATTESTATION_SCHEMA = (
    "docs/schemas/finance_ledger_attestation.schema.json"
)
MONEY_QUANT = Decimal("0.000001")

PRIVATE_FIELD_NAMES = {
    "prompt",
    "output",
    "answer_text",
    "quote",
    "evidence_text",
    "matched_text",
    "source_text",
    "account_id",
    "customer_id",
    "customer_name",
    "customer_email",
    "billing_account",
    "billing_email",
    "invoice_number",
    "invoice_text",
    "invoice_pdf",
    "raw_invoice",
    "raw_receipt",
    "raw_finance_record",
    "raw_billing_record",
    "raw_meter_event",
    "payment_method",
    "payment_intent",
    "card_number",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
}

FINANCE_HASH_FIELDS = (
    "record_hash",
    "ledger_entry_hash",
    "billing_record_hash",
    "invoice_hash",
    "receipt_hash",
    "customer_id_hash",
    "account_id_hash",
    "payment_intent_hash",
    "transaction_hash",
    "meter_event_hash",
    "meter_event_root",
    "ad_impression_root",
    "export_batch_hash",
    "batch_hash",
    "contract_hash",
    "marketplace_order_hash",
)


def _money(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _money_str(value: Decimal | str | int | float) -> str:
    return str(_money(value))


def _sum_money(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal("0")).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _sort_rows(rows: list[dict[str, Any]], *keys: str) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: tuple(str(row.get(key, "")) for key in keys))


def _hashable_attestation(attestation: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in attestation.items()
        if key not in {"attestation_hash", "signature"}
    }


def _hashable_finance_record(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "finance_record_row_hash"}


def _hashable_rollup(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "rollup_row_hash"}


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


def _revenue_allocation_hash_reproducible(report: dict[str, Any]) -> bool:
    declared = report.get("report_hash")
    if not isinstance(declared, str) or not declared:
        return False
    hashable = {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }
    return hash_payload(hashable) == declared


def _allocation_source_rows(
    revenue_allocation_report: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = revenue_allocation_report.get("revenue_sources", [])
    if not isinstance(rows, list):
        return []
    return [
        row
        for row in rows
        if isinstance(row, dict)
    ]


def _normalize_finance_records(
    finance_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, record in enumerate(finance_records, start=1):
        record_id = str(
            record.get("finance_record_id")
            or record.get("record_id")
            or record.get("id")
            or f"finance-record:{index}"
        )
        source_id = str(
            record.get("revenue_source_id")
            or record.get("source_id")
            or ""
        )
        record_hashes = {
            field: str(record[field])
            for field in FINANCE_HASH_FIELDS
            if record.get(field)
        }
        external_record_hash_supplied = bool(record_hashes)
        row = {
            "finance_record_id": record_id,
            "revenue_source_id": source_id,
            "external_system": str(
                record.get("external_system")
                or record.get("system")
                or "unknown"
            ),
            "record_type": str(
                record.get("record_type")
                or record.get("type")
                or "usage_revenue_record"
            ),
            "period_start": str(record.get("period_start", "")),
            "period_end": str(record.get("period_end", "")),
            "currency": str(record.get("currency", "USD")),
            "gross_revenue": _money_str(record.get("gross_revenue", "0")),
            "adjustment_type": str(record.get("adjustment_type", "gross")),
            "record_hashes": dict(sorted(record_hashes.items())),
            "external_record_hash_supplied": external_record_hash_supplied,
            "raw_customer_record_disclosed": False,
            "invoice_text_disclosed": False,
            "raw_finance_record_disclosed": False,
            "payment_identifier_disclosed": False,
        }
        if not row["record_hashes"]:
            row["record_hashes"] = {
                "safe_record_hash": hash_payload(
                    {
                        "finance_record_id": record_id,
                        "revenue_source_id": source_id,
                        "external_system": row["external_system"],
                        "record_type": row["record_type"],
                        "period_start": row["period_start"],
                        "period_end": row["period_end"],
                        "currency": row["currency"],
                        "gross_revenue": row["gross_revenue"],
                        "adjustment_type": row["adjustment_type"],
                    }
                )
            }
        row["finance_record_row_hash"] = hash_payload(_hashable_finance_record(row))
        rows.append(row)
    return _sort_rows(rows, "revenue_source_id", "finance_record_id")


def _rollup_rows(
    finance_record_rows: list[dict[str, Any]],
    allocation_source_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    allocation_by_source = {
        str(row.get("source_id", "")): row
        for row in allocation_source_rows
    }
    source_ids = sorted(
        {
            *allocation_by_source.keys(),
            *[
                str(row.get("revenue_source_id", ""))
                for row in finance_record_rows
                if row.get("revenue_source_id")
            ],
        }
    )
    rows: list[dict[str, Any]] = []
    for source_id in source_ids:
        records = [
            row
            for row in finance_record_rows
            if row.get("revenue_source_id") == source_id
        ]
        allocation_source = allocation_by_source.get(source_id, {})
        finance_total = _sum_money(
            [_money(row.get("gross_revenue", "0")) for row in records]
        )
        allocation_total = _money(allocation_source.get("gross_revenue", "0"))
        currencies = {
            str(row.get("currency", ""))
            for row in records
            if row.get("currency")
        }
        if allocation_source.get("currency"):
            currencies.add(str(allocation_source.get("currency")))
        row = {
            "revenue_source_id": source_id,
            "source_type": str(allocation_source.get("source_type", "")),
            "source_row_hash": str(allocation_source.get("source_row_hash", "")),
            "record_count": len(records),
            "external_systems": sorted(
                {
                    str(row.get("external_system", ""))
                    for row in records
                    if row.get("external_system")
                }
            ),
            "currency": (
                sorted(currencies)[0]
                if len(currencies) == 1
                else "MIXED" if currencies else ""
            ),
            "finance_gross_revenue": _money_str(finance_total),
            "revenue_allocation_gross_revenue": _money_str(allocation_total),
            "gross_revenue_matches_revenue_allocation": (
                finance_total == allocation_total
            ),
            "finance_record_root": hash_payload(records),
            "allocation_source_present": bool(allocation_source),
            "finance_records_present": bool(records),
        }
        row["rollup_row_hash"] = hash_payload(_hashable_rollup(row))
        rows.append(row)
    return _sort_rows(rows, "revenue_source_id")


def make_finance_ledger_attestation(
    finance_records: list[dict[str, Any]],
    *,
    revenue_allocation_report: dict[str, Any],
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed attestation from private finance exports to RDLLM revenue."""

    allocation_source_rows = _allocation_source_rows(revenue_allocation_report)
    finance_record_rows = _normalize_finance_records(finance_records)
    rollups = _rollup_rows(finance_record_rows, allocation_source_rows)
    finance_total = _sum_money(
        [_money(row.get("gross_revenue", "0")) for row in finance_record_rows]
    )
    allocation_total = _sum_money(
        [_money(row.get("gross_revenue", "0")) for row in allocation_source_rows]
    )
    finance_record_ids = [
        row["finance_record_id"]
        for row in finance_record_rows
    ]
    allocation_source_ids = {
        str(row.get("source_id", ""))
        for row in allocation_source_rows
        if row.get("source_id")
    }
    finance_source_ids = {
        str(row.get("revenue_source_id", ""))
        for row in finance_record_rows
        if row.get("revenue_source_id")
    }
    currencies = {
        str(row.get("currency", ""))
        for row in [*finance_record_rows, *allocation_source_rows]
        if row.get("currency")
    }
    private_input_paths = _contains_private_fields(finance_records)
    private_report_paths = _contains_private_fields(
        {
            "finance_record_rows": finance_record_rows,
            "revenue_source_rollups": rollups,
        }
    )
    allocation_shape_errors = validate_revenue_allocation_report_shape(
        revenue_allocation_report
    )
    checks = {
        "revenue_allocation_report_ready": (
            not allocation_shape_errors
            and revenue_allocation_report.get("summary", {}).get("status") == "ready"
            and _revenue_allocation_hash_reproducible(revenue_allocation_report)
        ),
        "finance_records_present": bool(finance_record_rows),
        "finance_record_rows_hash_bound": all(
            row.get("finance_record_row_hash")
            == hash_payload(_hashable_finance_record(row))
            for row in finance_record_rows
        ),
        "finance_record_hashes_present": all(
            row.get("external_record_hash_supplied") is True
            for row in finance_record_rows
        ),
        "rollup_rows_hash_bound": all(
            row.get("rollup_row_hash") == hash_payload(_hashable_rollup(row))
            for row in rollups
        ),
        "all_finance_records_map_to_allocation_sources": (
            bool(finance_source_ids)
            and finance_source_ids.issubset(allocation_source_ids)
        ),
        "all_allocation_sources_have_finance_records": (
            bool(allocation_source_ids)
            and allocation_source_ids.issubset(finance_source_ids)
        ),
        "source_totals_match_revenue_allocation": all(
            row.get("gross_revenue_matches_revenue_allocation") is True
            for row in rollups
        ),
        "total_gross_matches_revenue_allocation": finance_total == allocation_total,
        "single_currency_report": len(currencies) <= 1,
        "no_duplicate_finance_record_rows": (
            len(finance_record_ids) == len(set(finance_record_ids))
        ),
        "private_finance_fields_absent_from_input": not private_input_paths,
        "private_finance_fields_absent_from_report": not private_report_paths,
    }
    attestation = {
        "attestation_version": FINANCE_LEDGER_ATTESTATION_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "finance_record_rows": finance_record_rows,
        "revenue_source_rollups": rollups,
        "checks": checks,
        "commitments": {
            "revenue_allocation_report_hash": str(
                revenue_allocation_report.get("report_hash", "")
            ),
            "revenue_allocation_source_root": hash_payload(allocation_source_rows),
            "finance_record_root": hash_payload(finance_record_rows),
            "revenue_source_rollup_root": hash_payload(rollups),
            "finance_gross_revenue_total": _money_str(finance_total),
            "revenue_allocation_gross_revenue_total": _money_str(allocation_total),
            "external_system_root": hash_payload(
                sorted(
                    {
                        str(row.get("external_system", ""))
                        for row in finance_record_rows
                        if row.get("external_system")
                    }
                )
            ),
        },
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": "RDLLM-L47",
            "finance_record_count": len(finance_record_rows),
            "revenue_source_count": len(allocation_source_rows),
            "external_system_count": len(
                {
                    row.get("external_system", "")
                    for row in finance_record_rows
                    if row.get("external_system")
                }
            ),
            "currency": sorted(currencies)[0] if len(currencies) == 1 else "MIXED",
            "finance_gross_revenue_total": _money_str(finance_total),
            "revenue_allocation_gross_revenue_total": _money_str(allocation_total),
            "unmatched_finance_source_count": len(
                finance_source_ids - allocation_source_ids
            ),
            "unbacked_allocation_source_count": len(
                allocation_source_ids - finance_source_ids
            ),
            "private_input_field_paths": private_input_paths,
            "private_report_field_paths": private_report_paths,
            "revenue_allocation_shape_errors": allocation_shape_errors,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "raw_customer_account_disclosed": False,
            "invoice_text_disclosed": False,
            "raw_finance_records_disclosed": False,
            "payment_identifier_disclosed": False,
            "finance_rows_use_hashes_amounts_and_source_ids": True,
        },
        "schemas": {
            "finance_ledger_attestation": FINANCE_LEDGER_ATTESTATION_SCHEMA,
            "revenue_allocation_report": (
                "docs/schemas/revenue_allocation_report.schema.json"
            ),
        },
    }
    attestation["attestation_hash"] = hash_payload(
        _hashable_attestation(attestation)
    )
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


def validate_finance_ledger_attestation_shape(
    attestation: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = (
        "attestation_version",
        "issuer",
        "created_at",
        "finance_record_rows",
        "revenue_source_rollups",
        "checks",
        "commitments",
        "summary",
        "privacy",
        "schemas",
        "attestation_hash",
        "signature",
    )
    for key in required:
        if key not in attestation:
            errors.append(f"missing finance ledger attestation field: {key}")
    if errors:
        return errors
    if attestation.get("attestation_version") != FINANCE_LEDGER_ATTESTATION_VERSION:
        errors.append("finance ledger attestation version is unsupported")
    for key in (
        "revenue_allocation_report_ready",
        "finance_record_hashes_present",
        "source_totals_match_revenue_allocation",
        "total_gross_matches_revenue_allocation",
        "private_finance_fields_absent_from_report",
    ):
        if key not in attestation.get("checks", {}):
            errors.append(f"missing finance ledger check: {key}")
    for key in (
        "revenue_allocation_report_hash",
        "revenue_allocation_source_root",
        "finance_record_root",
        "revenue_source_rollup_root",
        "finance_gross_revenue_total",
        "revenue_allocation_gross_revenue_total",
    ):
        if key not in attestation.get("commitments", {}):
            errors.append(f"missing finance ledger commitment: {key}")
    return errors


def verify_finance_ledger_attestation(
    attestation: dict[str, Any],
    *,
    finance_records: list[dict[str, Any]],
    revenue_allocation_report: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a finance attestation against source records and allocation report."""

    errors = validate_finance_ledger_attestation_shape(attestation)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_attestation(attestation))
    if expected_hash != attestation.get("attestation_hash"):
        errors.append("finance ledger attestation hash is not reproducible")

    expected = make_finance_ledger_attestation(
        finance_records,
        revenue_allocation_report=revenue_allocation_report,
        issuer=attestation.get("issuer", DEFAULT_ISSUER),
        created_at=attestation.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "finance_record_rows",
        "revenue_source_rollups",
        "checks",
        "commitments",
        "summary",
        "privacy",
        "schemas",
    ):
        if expected.get(key) != attestation.get(key):
            errors.append(
                f"finance ledger attestation {key} does not match recomputed inputs"
            )
    if expected.get("attestation_hash") != attestation.get("attestation_hash"):
        errors.append("finance ledger attestation hash does not match recomputed inputs")

    if attestation.get("summary", {}).get("status") != "ready":
        errors.append("finance ledger attestation status is not ready")
    for check, passed in attestation.get("checks", {}).items():
        if passed is not True:
            errors.append(f"finance ledger attestation check failed: {check}")

    private_paths = _contains_private_fields(attestation)
    if private_paths:
        errors.append(
            "finance ledger attestation exposes private fields: "
            + ", ".join(sorted(private_paths))
        )

    signature = attestation.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(
            _hashable_attestation(attestation),
            signing_secret,
        )
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("finance ledger attestation is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("finance ledger attestation signature is invalid")

    return errors
