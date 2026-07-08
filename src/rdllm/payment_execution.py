"""External payment execution attestations for RDLLM remittance reports."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload

PAYMENT_EXECUTION_REPORT_VERSION = "rdllm-payment-execution-report/v1"
PAYMENT_EXECUTION_REPORT_SCHEMA = "docs/schemas/payment_execution_report.schema.json"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L77"
MONEY_QUANT = Decimal("0.000001")

PRIVATE_FIELD_NAMES = {
    "prompt",
    "output",
    "answer_text",
    "quote",
    "evidence_text",
    "matched_text",
    "copied_output",
    "source_text",
    "customer_id",
    "customer_name",
    "customer_email",
    "billing_account",
    "payout_account",
    "processor_account",
    "payment_method",
    "card_number",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "raw_payment_record",
    "raw_processor_record",
    "raw_bank_record",
}


def _decimal(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value))


def _money(value: Decimal | str | int | float) -> str:
    return str(_decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


def _sum_money(rows: list[dict[str, Any]], field: str) -> Decimal:
    return sum((_decimal(row.get(field, "0")) for row in rows), Decimal("0")).quantize(
        MONEY_QUANT,
        rounding=ROUND_HALF_UP,
    )


def _sort_rows(rows: list[dict[str, Any]], *keys: str) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: tuple(str(row.get(key, "")) for key in keys))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in artifact.items()
        if key not in {"report_hash", "contract_hash", "attestation_hash", "signature"}
    }


def _declared_hash(artifact: dict[str, Any]) -> str:
    for field in ("report_hash", "contract_hash", "attestation_hash"):
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(artifact)


def _artifact_hash_is_reproducible(artifact: dict[str, Any]) -> bool:
    declared = _declared_hash(artifact)
    if artifact.get("report_hash") or artifact.get("contract_hash") or artifact.get(
        "attestation_hash"
    ):
        return hash_payload(_hashable_artifact(artifact)) == declared
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


def _hashable_processor_record_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key != "processor_record_row_hash"
    }


def _hashable_execution_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key
        not in {
            "execution_row_hash",
            "hold_carryforward_row_hash",
        }
    }


def _normalize_processor_records(
    processor_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, record in enumerate(processor_records, start=1):
        record_type = str(record.get("record_type") or record.get("type") or "")
        payment_instruction_id = str(
            record.get("payment_instruction_id")
            or (
                record.get("instruction_id")
                if record_type == "payment_settlement"
                else ""
            )
            or ""
        )
        escrow_instruction_id = str(
            record.get("escrow_instruction_id")
            or (
                record.get("instruction_id")
                if record_type == "escrow_settlement"
                else ""
            )
            or ""
        )
        account_hash = str(
            record.get("payout_account_hash")
            or record.get("escrow_account_hash")
            or record.get("account_hash")
            or ""
        )
        row = {
            "processor_record_id": str(
                record.get("processor_record_id")
                or record.get("record_id")
                or record.get("id")
                or f"processor-record:{index}"
            ),
            "external_processor": str(
                record.get("external_processor")
                or record.get("processor")
                or record.get("payment_processor")
                or "unknown"
            ),
            "record_type": record_type,
            "payment_instruction_id": payment_instruction_id,
            "escrow_instruction_id": escrow_instruction_id,
            "end_to_end_id": str(record.get("end_to_end_id", "")),
            "settlement_status": str(record.get("settlement_status", "")),
            "settled_amount": _money(record.get("settled_amount", record.get("amount", "0"))),
            "currency": str(record.get("currency", "")),
            "payout_account_hash": (
                account_hash if record_type == "payment_settlement" else ""
            ),
            "escrow_account_hash": (
                account_hash if record_type == "escrow_settlement" else ""
            ),
            "processor_record_hash": str(record.get("processor_record_hash", "")),
            "settlement_batch_hash": str(record.get("settlement_batch_hash", "")),
            "settled_at": str(record.get("settled_at", "")),
            "raw_processor_record_disclosed": False,
            "raw_payment_account_disclosed": False,
            "customer_or_tax_record_disclosed": False,
        }
        row["processor_record_row_hash"] = hash_payload(_hashable_processor_record_row(row))
        rows.append(row)
    return _sort_rows(
        rows,
        "record_type",
        "payment_instruction_id",
        "escrow_instruction_id",
        "processor_record_id",
    )


def _payment_record_key(row: dict[str, Any]) -> tuple[str, str]:
    if row.get("record_type") == "payment_settlement":
        return ("payment", str(row.get("payment_instruction_id", "")))
    if row.get("record_type") == "escrow_settlement":
        return ("escrow", str(row.get("escrow_instruction_id", "")))
    return ("invalid", str(row.get("processor_record_id", "")))


def _processor_record_maps(
    processor_record_rows: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], set[tuple[str, str]]]:
    counts = Counter(_payment_record_key(row) for row in processor_record_rows)
    duplicates = {key for key, count in counts.items() if key[1] and count > 1}
    payment_by_id: dict[str, dict[str, Any]] = {}
    escrow_by_id: dict[str, dict[str, Any]] = {}
    for row in processor_record_rows:
        if row.get("record_type") == "payment_settlement" and row.get(
            "payment_instruction_id"
        ):
            payment_by_id.setdefault(str(row["payment_instruction_id"]), row)
        elif row.get("record_type") == "escrow_settlement" and row.get(
            "escrow_instruction_id"
        ):
            escrow_by_id.setdefault(str(row["escrow_instruction_id"]), row)
    return payment_by_id, escrow_by_id, duplicates


def _unmatched_processor_rows(
    processor_record_rows: list[dict[str, Any]],
    *,
    payment_instruction_ids: set[str],
    escrow_instruction_ids: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in processor_record_rows:
        reason = ""
        record_type = row.get("record_type")
        if record_type == "payment_settlement":
            if row.get("payment_instruction_id") not in payment_instruction_ids:
                reason = "unknown_payment_instruction_id"
        elif record_type == "escrow_settlement":
            if row.get("escrow_instruction_id") not in escrow_instruction_ids:
                reason = "unknown_escrow_instruction_id"
        else:
            reason = "unsupported_processor_record_type"
        if reason:
            unmatched = {
                "processor_record_row_hash": row["processor_record_row_hash"],
                "processor_record_id": row["processor_record_id"],
                "record_type": str(record_type or ""),
                "instruction_id": str(
                    row.get("payment_instruction_id")
                    or row.get("escrow_instruction_id")
                    or ""
                ),
                "settlement_status": str(row.get("settlement_status", "")),
                "reason": reason,
            }
            unmatched["unmatched_row_hash"] = hash_payload(unmatched)
            rows.append(unmatched)
    return _sort_rows(rows, "reason", "processor_record_id", "instruction_id")


def _payment_execution_rows(
    payment_instruction_rows: list[dict[str, Any]],
    *,
    payment_by_id: dict[str, dict[str, Any]],
    remittance_report_hash: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for instruction in payment_instruction_rows:
        instruction_id = str(instruction.get("payment_instruction_id", ""))
        record = payment_by_id.get(instruction_id)
        amount_match = bool(
            record
            and _decimal(record.get("settled_amount", "0"))
            == _decimal(instruction.get("amount", "0"))
        )
        currency_match = bool(
            record
            and str(record.get("currency", "")) == str(instruction.get("currency", ""))
        )
        account_match = bool(
            record
            and str(record.get("payout_account_hash", ""))
            == str(instruction.get("payout_account_hash", ""))
        )
        reference_match = bool(
            record
            and str(record.get("end_to_end_id", ""))
            == str(instruction.get("end_to_end_id", ""))
        )
        settled = bool(record and record.get("settlement_status") == "settled")
        execution_status = (
            "settled_verified"
            if settled and amount_match and currency_match and account_match and reference_match
            else "missing_processor_record"
            if not record
            else "settlement_mismatch"
        )
        row = {
            "payment_instruction_id": instruction_id,
            "recipient_creator_id": str(instruction.get("recipient_creator_id", "")),
            "recipient_creator_name": str(instruction.get("recipient_creator_name", "")),
            "recipient_kind": str(instruction.get("recipient_kind", "")),
            "work_id": str(instruction.get("work_id", "")),
            "currency": str(instruction.get("currency", "")),
            "instructed_amount": _money(instruction.get("amount", "0")),
            "executed_amount": _money(record.get("settled_amount", "0") if record else "0"),
            "execution_status": execution_status,
            "processor_settlement_status": str(
                record.get("settlement_status", "") if record else ""
            ),
            "external_processor": str(record.get("external_processor", "") if record else ""),
            "processor_record_hash": str(
                record.get("processor_record_hash", "") if record else ""
            ),
            "settlement_batch_hash": str(
                record.get("settlement_batch_hash", "") if record else ""
            ),
            "settled_at": str(record.get("settled_at", "") if record else ""),
            "end_to_end_id": str(instruction.get("end_to_end_id", "")),
            "processor_end_to_end_id": str(
                record.get("end_to_end_id", "") if record else ""
            ),
            "payout_account_hash": str(instruction.get("payout_account_hash", "")),
            "payout_account_disclosed": False,
            "instruction_row_hash": str(instruction.get("instruction_row_hash", "")),
            "processor_record_row_hash": str(
                record.get("processor_record_row_hash", "") if record else ""
            ),
            "remittance_report_hash": remittance_report_hash,
            "amount_match": amount_match,
            "currency_match": currency_match,
            "payout_account_hash_match": account_match,
            "end_to_end_id_match": reference_match,
        }
        row["execution_row_hash"] = hash_payload(_hashable_execution_row(row))
        rows.append(row)
    return _sort_rows(rows, "recipient_creator_id", "work_id", "payment_instruction_id")


def _escrow_execution_rows(
    escrow_instruction_rows: list[dict[str, Any]],
    *,
    escrow_by_id: dict[str, dict[str, Any]],
    remittance_report_hash: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for instruction in escrow_instruction_rows:
        instruction_id = str(instruction.get("escrow_instruction_id", ""))
        record = escrow_by_id.get(instruction_id)
        amount_match = bool(
            record
            and _decimal(record.get("settled_amount", "0"))
            == _decimal(instruction.get("amount", "0"))
        )
        currency_match = bool(
            record
            and str(record.get("currency", "")) == str(instruction.get("currency", ""))
        )
        account_match = bool(
            record
            and str(record.get("escrow_account_hash", ""))
            == str(instruction.get("escrow_account_hash", ""))
        )
        reference_match = bool(
            record
            and str(record.get("end_to_end_id", ""))
            == str(instruction.get("end_to_end_id", ""))
        )
        escrowed = bool(record and record.get("settlement_status") == "escrowed")
        execution_status = (
            "escrowed_verified"
            if escrowed and amount_match and currency_match and account_match and reference_match
            else "missing_processor_record"
            if not record
            else "escrow_settlement_mismatch"
        )
        row = {
            "escrow_instruction_id": instruction_id,
            "recipient_creator_id": str(instruction.get("recipient_creator_id", "")),
            "work_id": str(instruction.get("work_id", "")),
            "currency": str(instruction.get("currency", "")),
            "instructed_amount": _money(instruction.get("amount", "0")),
            "executed_amount": _money(record.get("settled_amount", "0") if record else "0"),
            "execution_status": execution_status,
            "processor_settlement_status": str(
                record.get("settlement_status", "") if record else ""
            ),
            "external_processor": str(record.get("external_processor", "") if record else ""),
            "processor_record_hash": str(
                record.get("processor_record_hash", "") if record else ""
            ),
            "settlement_batch_hash": str(
                record.get("settlement_batch_hash", "") if record else ""
            ),
            "settled_at": str(record.get("settled_at", "") if record else ""),
            "end_to_end_id": str(instruction.get("end_to_end_id", "")),
            "processor_end_to_end_id": str(
                record.get("end_to_end_id", "") if record else ""
            ),
            "escrow_account_hash": str(instruction.get("escrow_account_hash", "")),
            "escrow_account_disclosed": False,
            "instruction_row_hash": str(instruction.get("instruction_row_hash", "")),
            "processor_record_row_hash": str(
                record.get("processor_record_row_hash", "") if record else ""
            ),
            "remittance_report_hash": remittance_report_hash,
            "amount_match": amount_match,
            "currency_match": currency_match,
            "escrow_account_hash_match": account_match,
            "end_to_end_id_match": reference_match,
        }
        row["execution_row_hash"] = hash_payload(_hashable_execution_row(row))
        rows.append(row)
    return _sort_rows(rows, "recipient_creator_id", "work_id", "escrow_instruction_id")


def _hold_carryforward_rows(
    remittance_hold_rows: list[dict[str, Any]],
    *,
    remittance_report_hash: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for hold in remittance_hold_rows:
        row = {
            "hold_id": str(hold.get("hold_id", "")),
            "hold_status": str(hold.get("hold_status", "")),
            "hold_reason": str(hold.get("hold_reason", "")),
            "recipient_creator_id": str(hold.get("recipient_creator_id", "")),
            "work_id": str(hold.get("work_id", "")),
            "chunk_id": str(hold.get("chunk_id", "")),
            "currency": str(hold.get("currency", "")),
            "amount": _money(hold.get("amount", "0")),
            "execution_status": "held_not_paid",
            "remittance_report_hash": remittance_report_hash,
            "remittance_hold_row_hash": str(hold.get("hold_row_hash", "")),
        }
        row["hold_carryforward_row_hash"] = hash_payload(_hashable_execution_row(row))
        rows.append(row)
    return _sort_rows(rows, "hold_status", "recipient_creator_id", "work_id", "amount")


def make_payment_execution_report(
    *,
    remittance_report: dict[str, Any],
    processor_records: list[dict[str, Any]],
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a replayable hash-only proof that remittance instructions settled."""

    remittance_hash = _declared_hash(remittance_report)
    private_input_paths = _contains_private_fields(processor_records)
    processor_record_rows = _normalize_processor_records(processor_records)
    payment_by_id, escrow_by_id, duplicate_keys = _processor_record_maps(
        processor_record_rows
    )
    payment_instruction_rows = list(remittance_report.get("payment_instruction_rows", []))
    escrow_instruction_rows = list(remittance_report.get("escrow_instruction_rows", []))
    remittance_hold_rows = list(remittance_report.get("remittance_hold_rows", []))
    payment_instruction_ids = {
        str(row.get("payment_instruction_id", ""))
        for row in payment_instruction_rows
        if row.get("payment_instruction_id")
    }
    escrow_instruction_ids = {
        str(row.get("escrow_instruction_id", ""))
        for row in escrow_instruction_rows
        if row.get("escrow_instruction_id")
    }
    unmatched_processor_rows = _unmatched_processor_rows(
        processor_record_rows,
        payment_instruction_ids=payment_instruction_ids,
        escrow_instruction_ids=escrow_instruction_ids,
    )
    payment_execution_rows = _payment_execution_rows(
        payment_instruction_rows,
        payment_by_id=payment_by_id,
        remittance_report_hash=remittance_hash,
    )
    escrow_execution_rows = _escrow_execution_rows(
        escrow_instruction_rows,
        escrow_by_id=escrow_by_id,
        remittance_report_hash=remittance_hash,
    )
    hold_carryforward_rows = _hold_carryforward_rows(
        remittance_hold_rows,
        remittance_report_hash=remittance_hash,
    )

    expected_payment_total = _sum_money(payment_instruction_rows, "amount")
    expected_escrow_total = _sum_money(escrow_instruction_rows, "amount")
    hold_total = _sum_money(hold_carryforward_rows, "amount")
    executed_payment_total = _sum_money(payment_execution_rows, "executed_amount")
    executed_escrow_total = _sum_money(escrow_execution_rows, "executed_amount")
    expected_remittance_total = (
        expected_payment_total + expected_escrow_total + hold_total
    ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    accounted_total = (
        executed_payment_total + executed_escrow_total + hold_total
    ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    expected_processor_record_count = len(payment_instruction_rows) + len(
        escrow_instruction_rows
    )
    processor_record_count_matches = len(processor_record_rows) == expected_processor_record_count
    checks = {
        "remittance_hash_reproducible": _artifact_hash_is_reproducible(remittance_report),
        "remittance_report_ready": remittance_report.get("summary", {}).get("status")
        == "ready",
        "remittance_input_is_instruction_only": remittance_report.get("summary", {}).get(
            "instruction_only"
        )
        is True,
        "processor_records_match_instruction_count": processor_record_count_matches,
        "processor_record_rows_hash_bound": all(
            hash_payload(_hashable_processor_record_row(row))
            == row.get("processor_record_row_hash")
            for row in processor_record_rows
        ),
        "processor_record_hashes_present": all(
            row.get("processor_record_hash") and row.get("settlement_batch_hash")
            for row in processor_record_rows
        ),
        "no_duplicate_processor_records": not duplicate_keys,
        "no_unmatched_processor_records": not unmatched_processor_rows,
        "all_payment_instructions_matched": all(
            row["execution_status"] == "settled_verified"
            for row in payment_execution_rows
        ),
        "payment_execution_amounts_match_instructions": all(
            row["amount_match"] for row in payment_execution_rows
        ),
        "payment_execution_accounts_match_instructions": all(
            row["payout_account_hash_match"] for row in payment_execution_rows
        ),
        "payment_execution_references_match_instructions": all(
            row["end_to_end_id_match"] for row in payment_execution_rows
        ),
        "all_escrow_instructions_matched": all(
            row["execution_status"] == "escrowed_verified"
            for row in escrow_execution_rows
        ),
        "escrow_execution_amounts_match_instructions": all(
            row["amount_match"] for row in escrow_execution_rows
        ),
        "escrow_execution_accounts_match_instructions": all(
            row["escrow_account_hash_match"] for row in escrow_execution_rows
        ),
        "escrow_execution_references_match_instructions": all(
            row["end_to_end_id_match"] for row in escrow_execution_rows
        ),
        "remittance_holds_preserved_not_paid": len(hold_carryforward_rows)
        == len(remittance_hold_rows)
        and hold_total == _sum_money(remittance_hold_rows, "amount"),
        "executed_payment_total_matches_remittance": executed_payment_total
        == expected_payment_total,
        "executed_escrow_total_matches_remittance": executed_escrow_total
        == expected_escrow_total,
        "all_remittance_value_accounted_for": accounted_total
        == expected_remittance_total,
        "private_payment_fields_absent_from_input": not private_input_paths,
        "payout_accounts_not_disclosed": True,
    }
    duplicate_processor_records = [
        {
            "record_class": key[0],
            "instruction_id": key[1],
            "reason": "duplicate_processor_record_for_instruction",
            "duplicate_key_hash": hash_payload({"record_class": key[0], "instruction_id": key[1]}),
        }
        for key in sorted(duplicate_keys)
    ]
    report = {
        "report_version": PAYMENT_EXECUTION_REPORT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "execution_policy": {
            "profile": "rdllm-external-payment-execution/v1",
            "payment_execution_mode": "external_processor_attested",
            "remittance_report_hash": remittance_hash,
            "payment_rail": str(
                remittance_report.get("remittance_policy", {}).get("payment_rail", "")
            ),
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": "RDLLM-L44",
            "standards_alignment": {
                "payment_initiation": "ISO 20022 pain.001-compatible",
                "payment_status": "ISO 20022 pain.002/camt-compatible hash evidence",
                "remittance_advice": "ISO 20022 remt.001-compatible",
                "verifiable_claims": "W3C Verifiable Credentials 2.0-shaped",
                "provenance": "W3C PROV-shaped",
            },
            "raw_payout_accounts_forbidden": True,
            "processor_records_required": True,
        },
        "processor_record_rows": processor_record_rows,
        "payment_execution_rows": payment_execution_rows,
        "escrow_execution_rows": escrow_execution_rows,
        "hold_carryforward_rows": hold_carryforward_rows,
        "unmatched_processor_records": unmatched_processor_rows,
        "duplicate_processor_records": duplicate_processor_records,
        "checks": checks,
        "commitments": {
            "remittance_report_hash": remittance_hash,
            "payment_instruction_root": remittance_report.get("commitments", {}).get(
                "payment_instruction_root", ""
            ),
            "escrow_instruction_root": remittance_report.get("commitments", {}).get(
                "escrow_instruction_root", ""
            ),
            "remittance_hold_root": remittance_report.get("commitments", {}).get(
                "remittance_hold_root", ""
            ),
            "processor_record_root": hash_payload(processor_record_rows),
            "payment_execution_root": hash_payload(payment_execution_rows),
            "escrow_execution_root": hash_payload(escrow_execution_rows),
            "hold_carryforward_root": hash_payload(hold_carryforward_rows),
            "unmatched_processor_record_root": hash_payload(unmatched_processor_rows),
            "duplicate_processor_record_root": hash_payload(duplicate_processor_records),
            "settlement_batch_root": hash_payload(
                sorted(
                    {
                        row.get("settlement_batch_hash", "")
                        for row in processor_record_rows
                        if row.get("settlement_batch_hash")
                    }
                )
            ),
        },
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "payment_execution_count": len(payment_execution_rows),
            "escrow_execution_count": len(escrow_execution_rows),
            "hold_carryforward_count": len(hold_carryforward_rows),
            "processor_record_count": len(processor_record_rows),
            "expected_processor_record_count": expected_processor_record_count,
            "unmatched_processor_record_count": len(unmatched_processor_rows),
            "duplicate_processor_record_count": len(duplicate_processor_records),
            "executed_payment_total": _money(executed_payment_total),
            "expected_payment_total": _money(expected_payment_total),
            "executed_escrow_total": _money(executed_escrow_total),
            "expected_escrow_total": _money(expected_escrow_total),
            "hold_total": _money(hold_total),
            "accounted_total": _money(accounted_total),
            "expected_remittance_total": _money(expected_remittance_total),
            "external_payment_execution_attested": all(checks.values()),
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "raw_processor_records_disclosed": False,
            "raw_payout_accounts_disclosed": False,
            "raw_escrow_accounts_disclosed": False,
            "customer_or_tax_records_disclosed": False,
            "uses_processor_hashes": True,
            "uses_payout_account_hashes": True,
            "uses_escrow_account_hashes": True,
        },
        "schemas": {
            "payment_execution_report": PAYMENT_EXECUTION_REPORT_SCHEMA,
            "remittance_report": "docs/schemas/remittance_report.schema.json",
        },
    }
    report_private_paths = _contains_private_fields(report)
    report["checks"]["private_payment_fields_absent_from_report"] = not report_private_paths
    if private_input_paths:
        report["summary"]["private_input_field_paths"] = private_input_paths
    if report_private_paths:
        report["summary"]["private_report_field_paths"] = report_private_paths
    report["summary"]["status"] = (
        "ready" if all(report["checks"].values()) else "failed"
    )
    report["summary"]["external_payment_execution_attested"] = all(
        report["checks"].values()
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


def validate_payment_execution_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "execution_policy",
        "processor_record_rows",
        "payment_execution_rows",
        "escrow_execution_rows",
        "hold_carryforward_rows",
        "unmatched_processor_records",
        "duplicate_processor_records",
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
            errors.append(f"missing payment execution report field: {key}")
    if errors:
        return errors
    if report.get("report_version") != PAYMENT_EXECUTION_REPORT_VERSION:
        errors.append("payment execution report version is unsupported")
    for key in (
        "profile",
        "payment_execution_mode",
        "remittance_report_hash",
        "payment_rail",
        "target_certification_level",
        "minimum_input_level",
    ):
        if key not in report.get("execution_policy", {}):
            errors.append(f"missing payment execution policy field: {key}")
    if report.get("execution_policy", {}).get(
        "target_certification_level"
    ) != TARGET_CERTIFICATION_LEVEL:
        errors.append("payment execution target certification level is unsupported")
    for row in report.get("processor_record_rows", []):
        for key in (
            "processor_record_id",
            "external_processor",
            "record_type",
            "end_to_end_id",
            "settlement_status",
            "settled_amount",
            "currency",
            "processor_record_hash",
            "settlement_batch_hash",
            "processor_record_row_hash",
        ):
            if key not in row:
                errors.append(f"missing processor record field: {key}")
    for row in report.get("payment_execution_rows", []):
        for key in (
            "payment_instruction_id",
            "currency",
            "instructed_amount",
            "executed_amount",
            "execution_status",
            "processor_record_hash",
            "settlement_batch_hash",
            "payout_account_hash",
            "payout_account_disclosed",
            "instruction_row_hash",
            "processor_record_row_hash",
            "execution_row_hash",
        ):
            if key not in row:
                errors.append(f"missing payment execution field: {key}")
    for row in report.get("escrow_execution_rows", []):
        for key in (
            "escrow_instruction_id",
            "currency",
            "instructed_amount",
            "executed_amount",
            "execution_status",
            "processor_record_hash",
            "settlement_batch_hash",
            "escrow_account_hash",
            "escrow_account_disclosed",
            "instruction_row_hash",
            "processor_record_row_hash",
            "execution_row_hash",
        ):
            if key not in row:
                errors.append(f"missing escrow execution field: {key}")
    for key in (
        "remittance_report_hash",
        "processor_record_root",
        "payment_execution_root",
        "escrow_execution_root",
        "hold_carryforward_root",
        "settlement_batch_root",
    ):
        if key not in report.get("commitments", {}):
            errors.append(f"missing payment execution commitment: {key}")
    for key in (
        "status",
        "target_certification_level",
        "payment_execution_count",
        "escrow_execution_count",
        "hold_carryforward_count",
        "processor_record_count",
        "executed_payment_total",
        "executed_escrow_total",
        "accounted_total",
        "expected_remittance_total",
        "external_payment_execution_attested",
    ):
        if key not in report.get("summary", {}):
            errors.append(f"missing payment execution summary field: {key}")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("payment execution summary target certification level is unsupported")
    if "payment_execution_report" not in report.get("schemas", {}):
        errors.append("missing payment execution report schema")
    return errors


def verify_payment_execution_report(
    report: dict[str, Any],
    *,
    remittance_report: dict[str, Any],
    processor_records: list[dict[str, Any]],
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify payment execution against remittance and processor records."""

    errors = validate_payment_execution_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("payment execution report hash is not reproducible")

    expected = make_payment_execution_report(
        remittance_report=remittance_report,
        processor_records=processor_records,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "execution_policy",
        "processor_record_rows",
        "payment_execution_rows",
        "escrow_execution_rows",
        "hold_carryforward_rows",
        "unmatched_processor_records",
        "duplicate_processor_records",
        "checks",
        "commitments",
        "summary",
        "privacy",
        "schemas",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"payment execution report {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("payment execution report hash does not match replay")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("payment execution report status is not ready")
    failed_checks = [
        key for key, passed in report.get("checks", {}).items() if passed is not True
    ]
    if failed_checks:
        errors.append(f"payment execution report failed checks: {', '.join(failed_checks)}")
    if report.get("summary", {}).get("external_payment_execution_attested") is not True:
        errors.append("payment execution report is not externally attested")
    if _contains_private_fields(report):
        errors.append("payment execution report leaks private payment fields")
    if signing_secret:
        signature = report.get("signature", {})
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("payment execution report is not HMAC signed")
        if signature.get("value") != expected_signature:
            errors.append("payment execution report signature is invalid")
    return errors
