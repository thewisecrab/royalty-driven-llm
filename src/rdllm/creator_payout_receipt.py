"""Creator-facing payout receipts for RDLLM settlement proof chains."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload

CREATOR_PAYOUT_RECEIPT_REPORT_VERSION = "rdllm-creator-payout-receipt-report/v1"
CREATOR_PAYOUT_RECEIPT_REPORT_SCHEMA = (
    "docs/schemas/creator_payout_receipt_report.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L79"
MONEY_QUANT = Decimal("0.000001")

DECLARED_HASH_FIELDS = (
    "report_hash",
    "contract_hash",
    "attestation_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "bundle_hash",
    "graph_hash",
    "trust_registry_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "output",
    "answer_text",
    "source_text",
    "evidence_text",
    "matched_text",
    "quote",
    "copied_output",
    "payout_account",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
    "tax_id",
    "customer_id",
    "customer_email",
    "payment_method",
    "raw_processor_record",
    "raw_payment_account",
    "secret",
    "signing_secret",
    "private_key",
}


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
        if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
    }


def _hashable_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not key.endswith("_row_hash")}


def _declared_hash(artifact: dict[str, Any]) -> str:
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(_hashable_artifact(artifact))


def _artifact_hash_is_reproducible(artifact: dict[str, Any]) -> bool:
    if not any(artifact.get(field) for field in DECLARED_HASH_FIELDS):
        return True
    return hash_payload(_hashable_artifact(artifact)) == _declared_hash(artifact)


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


def _sum_money(rows: list[dict[str, Any]], field: str) -> Decimal:
    return sum((_decimal(row.get(field, "0")) for row in rows), Decimal("0")).quantize(
        MONEY_QUANT,
        rounding=ROUND_HALF_UP,
    )


def _index_by(rows: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    return {str(row.get(field, "")): row for row in rows if row.get(field)}


def _creator_totals(rows: list[dict[str, Any]], amount_field: str) -> list[dict[str, Any]]:
    totals: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    names: dict[str, str] = {}
    works: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        creator_id = str(row.get("recipient_creator_id", ""))
        currency = str(row.get("currency", ""))
        if not creator_id or not currency:
            continue
        totals[(creator_id, currency)] += _decimal(row.get(amount_field, "0"))
        names[creator_id] = str(row.get("recipient_creator_name", ""))
        if row.get("work_id"):
            works[creator_id].add(str(row.get("work_id", "")))
    result = []
    for (creator_id, currency), amount in sorted(totals.items()):
        row = {
            "recipient_creator_id": creator_id,
            "recipient_creator_name": names.get(creator_id, ""),
            "currency": currency,
            "amount": _money(amount),
            "work_count": len(works.get(creator_id, set())),
            "work_ids_root": hash_payload(sorted(works.get(creator_id, set()))),
        }
        row["creator_total_row_hash"] = hash_payload(_hashable_row(row))
        result.append(row)
    return result


def _rail_attestation_index(
    payment_rail_attestation: dict[str, Any],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    rows = payment_rail_attestation.get("processor_attestation_rows", [])
    return {
        (
            str(row.get("processor_id", "")),
            str(row.get("settlement_batch_hash", "")),
            str(row.get("record_type", "")),
        ): row
        for row in rows
    }


def _coverage_index(
    payment_rail_attestation: dict[str, Any],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    rows = payment_rail_attestation.get("batch_coverage_rows", [])
    return {
        (
            str(row.get("processor_id", "")),
            str(row.get("settlement_batch_hash", "")),
            str(row.get("record_type", "")),
        ): row
        for row in rows
    }


def _clearinghouse_payable_index(
    clearinghouse_report: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return _index_by(clearinghouse_report.get("payable_rows", []), "settlement_row_hash")


def _payout_rows(
    *,
    clearinghouse_report: dict[str, Any],
    remittance_report: dict[str, Any],
    payment_execution_report: dict[str, Any],
    payment_rail_attestation: dict[str, Any],
) -> list[dict[str, Any]]:
    payable_by_hash = _clearinghouse_payable_index(clearinghouse_report)
    execution_by_id = _index_by(
        payment_execution_report.get("payment_execution_rows", []),
        "payment_instruction_id",
    )
    rail_by_key = _rail_attestation_index(payment_rail_attestation)
    coverage_by_key = _coverage_index(payment_rail_attestation)
    rows: list[dict[str, Any]] = []
    for instruction in remittance_report.get("payment_instruction_rows", []):
        instruction_id = str(instruction.get("payment_instruction_id", ""))
        execution = execution_by_id.get(instruction_id, {})
        key = (
            str(execution.get("external_processor", "")),
            str(execution.get("settlement_batch_hash", "")),
            "payment_settlement",
        )
        rail_row = rail_by_key.get(key, {})
        coverage_row = coverage_by_key.get(key, {})
        payable = payable_by_hash.get(
            str(instruction.get("clearinghouse_settlement_row_hash", "")),
            {},
        )
        row = {
            "creator_receipt_id": hash_payload(
                {
                    "payment_instruction_id": instruction_id,
                    "execution_row_hash": execution.get("execution_row_hash", ""),
                    "rail_attestation_row_hash": rail_row.get(
                        "attestation_row_hash", ""
                    ),
                }
            ),
            "recipient_creator_id": str(instruction.get("recipient_creator_id", "")),
            "recipient_creator_name": str(instruction.get("recipient_creator_name", "")),
            "recipient_kind": str(instruction.get("recipient_kind", "")),
            "work_id": str(instruction.get("work_id", "")),
            "chunk_ids": sorted(str(item) for item in instruction.get("chunk_ids", [])),
            "origin_hashes": sorted(
                str(item) for item in instruction.get("origin_hashes", [])
            ),
            "clearinghouse_report_hash": _declared_hash(clearinghouse_report),
            "clearinghouse_settlement_row_hash": str(
                instruction.get("clearinghouse_settlement_row_hash", "")
            ),
            "clearinghouse_row_present": bool(payable),
            "remittance_report_hash": _declared_hash(remittance_report),
            "payment_instruction_id": instruction_id,
            "instruction_row_hash": str(instruction.get("instruction_row_hash", "")),
            "license_status": str(instruction.get("license_status", "")),
            "license_term_hash": str(instruction.get("license_term_hash", "")),
            "payout_account_hash": str(instruction.get("payout_account_hash", "")),
            "payout_account_disclosed": bool(
                instruction.get("payout_account_disclosed", False)
            ),
            "end_to_end_id": str(instruction.get("end_to_end_id", "")),
            "currency": str(instruction.get("currency", "")),
            "instructed_amount": _money(instruction.get("amount", "0")),
            "executed_amount": _money(execution.get("executed_amount", "0")),
            "execution_status": str(execution.get("execution_status", "")),
            "execution_row_hash": str(execution.get("execution_row_hash", "")),
            "processor_id": str(execution.get("external_processor", "")),
            "processor_record_hash": str(execution.get("processor_record_hash", "")),
            "processor_record_row_hash": str(
                execution.get("processor_record_row_hash", "")
            ),
            "settlement_batch_hash": str(execution.get("settlement_batch_hash", "")),
            "settled_at": str(execution.get("settled_at", "")),
            "rail_attestation_row_hash": str(rail_row.get("attestation_row_hash", "")),
            "rail_batch_coverage_row_hash": str(
                coverage_row.get("coverage_row_hash", "")
            ),
            "rail_signature_valid": bool(rail_row.get("signature_valid", False)),
            "rail_batch_signed": bool(
                coverage_row.get("signed_processor_attestation_present", False)
            ),
            "creator_visible_status": (
                "paid_verified"
                if execution.get("execution_status") == "settled_verified"
                and rail_row.get("signature_valid") is True
                and coverage_row.get("signed_processor_attestation_present") is True
                else "not_verified"
            ),
        }
        row["creator_receipt_row_hash"] = hash_payload(_hashable_row(row))
        rows.append(row)
    return sorted(
        rows,
        key=lambda row: (
            row["recipient_creator_id"],
            row["work_id"],
            row["payment_instruction_id"],
        ),
    )


def _escrow_rows(
    *,
    remittance_report: dict[str, Any],
    payment_execution_report: dict[str, Any],
    payment_rail_attestation: dict[str, Any],
) -> list[dict[str, Any]]:
    execution_by_id = _index_by(
        payment_execution_report.get("escrow_execution_rows", []),
        "escrow_instruction_id",
    )
    rail_by_key = _rail_attestation_index(payment_rail_attestation)
    coverage_by_key = _coverage_index(payment_rail_attestation)
    rows: list[dict[str, Any]] = []
    for instruction in remittance_report.get("escrow_instruction_rows", []):
        instruction_id = str(instruction.get("escrow_instruction_id", ""))
        execution = execution_by_id.get(instruction_id, {})
        key = (
            str(execution.get("external_processor", "")),
            str(execution.get("settlement_batch_hash", "")),
            "escrow_settlement",
        )
        rail_row = rail_by_key.get(key, {})
        coverage_row = coverage_by_key.get(key, {})
        row = {
            "creator_receipt_id": hash_payload(
                {
                    "escrow_instruction_id": instruction_id,
                    "execution_row_hash": execution.get("execution_row_hash", ""),
                    "rail_attestation_row_hash": rail_row.get(
                        "attestation_row_hash", ""
                    ),
                }
            ),
            "recipient_creator_id": str(instruction.get("recipient_creator_id", "")),
            "recipient_creator_name": str(instruction.get("recipient_creator_name", "")),
            "work_id": str(instruction.get("work_id", "")),
            "currency": str(instruction.get("currency", "")),
            "escrow_amount": _money(instruction.get("amount", "0")),
            "executed_amount": _money(execution.get("executed_amount", "0")),
            "escrow_instruction_id": instruction_id,
            "escrow_instruction_row_hash": str(
                instruction.get("escrow_instruction_row_hash", "")
            ),
            "execution_status": str(execution.get("execution_status", "")),
            "execution_row_hash": str(execution.get("execution_row_hash", "")),
            "escrow_account_hash": str(instruction.get("escrow_account_hash", "")),
            "processor_id": str(execution.get("external_processor", "")),
            "settlement_batch_hash": str(execution.get("settlement_batch_hash", "")),
            "rail_attestation_row_hash": str(rail_row.get("attestation_row_hash", "")),
            "rail_batch_coverage_row_hash": str(
                coverage_row.get("coverage_row_hash", "")
            ),
            "rail_signature_valid": bool(rail_row.get("signature_valid", False)),
            "rail_batch_signed": bool(
                coverage_row.get("signed_processor_attestation_present", False)
            ),
            "creator_visible_status": (
                "escrowed_verified"
                if execution.get("execution_status") == "escrowed_verified"
                and rail_row.get("signature_valid") is True
                and coverage_row.get("signed_processor_attestation_present") is True
                else "not_verified"
            ),
        }
        row["creator_escrow_receipt_row_hash"] = hash_payload(_hashable_row(row))
        rows.append(row)
    return sorted(rows, key=lambda row: row["escrow_instruction_id"])


def _hold_rows(
    *,
    remittance_report: dict[str, Any],
    payment_execution_report: dict[str, Any],
) -> list[dict[str, Any]]:
    execution_by_hash = _index_by(
        payment_execution_report.get("hold_carryforward_rows", []),
        "remittance_hold_row_hash",
    )
    rows: list[dict[str, Any]] = []
    for hold in remittance_report.get("remittance_hold_rows", []):
        execution = execution_by_hash.get(str(hold.get("hold_row_hash", "")), {})
        row = {
            "creator_receipt_id": hash_payload(
                {
                    "hold_row_hash": hold.get("hold_row_hash", ""),
                    "hold_carryforward_row_hash": execution.get(
                        "hold_carryforward_row_hash", ""
                    ),
                }
            ),
            "recipient_creator_id": str(hold.get("recipient_creator_id", "")),
            "work_id": str(hold.get("work_id", "")),
            "currency": str(hold.get("currency", "")),
            "held_amount": _money(hold.get("amount", "0")),
            "hold_reason": str(hold.get("hold_reason", "")),
            "hold_status": str(hold.get("hold_status", "")),
            "hold_row_hash": str(hold.get("hold_row_hash", "")),
            "hold_carryforward_row_hash": str(
                execution.get("hold_carryforward_row_hash", "")
            ),
            "creator_visible_status": "held_not_paid",
        }
        row["creator_hold_receipt_row_hash"] = hash_payload(_hashable_row(row))
        rows.append(row)
    return sorted(rows, key=lambda row: row["hold_row_hash"])


def make_creator_payout_receipt_report(
    *,
    clearinghouse_report: dict[str, Any],
    remittance_report: dict[str, Any],
    payment_execution_report: dict[str, Any],
    payment_rail_attestation: dict[str, Any],
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create creator-visible receipts for paid, escrowed, and held settlement rows."""

    private_paths = _contains_private_fields(
        {
            "clearinghouse_report": clearinghouse_report,
            "remittance_report": remittance_report,
            "payment_execution_report": payment_execution_report,
            "payment_rail_attestation": payment_rail_attestation,
        }
    )
    payout_rows = _payout_rows(
        clearinghouse_report=clearinghouse_report,
        remittance_report=remittance_report,
        payment_execution_report=payment_execution_report,
        payment_rail_attestation=payment_rail_attestation,
    )
    escrow_rows = _escrow_rows(
        remittance_report=remittance_report,
        payment_execution_report=payment_execution_report,
        payment_rail_attestation=payment_rail_attestation,
    )
    hold_rows = _hold_rows(
        remittance_report=remittance_report,
        payment_execution_report=payment_execution_report,
    )
    creator_total_rows = _creator_totals(payout_rows, "executed_amount")
    expected_payment_total = _decimal(
        payment_execution_report.get("summary", {}).get("executed_payment_total", "0")
    )
    expected_escrow_total = _decimal(
        payment_execution_report.get("summary", {}).get("executed_escrow_total", "0")
    )
    expected_hold_total = _decimal(
        payment_execution_report.get("summary", {}).get("hold_total", "0")
    )
    checks = {
        "clearinghouse_report_ready": clearinghouse_report.get("summary", {}).get(
            "status"
        )
        == "ready",
        "remittance_report_ready": remittance_report.get("summary", {}).get("status")
        == "ready"
        and remittance_report.get("summary", {}).get("instruction_only") is True,
        "payment_execution_report_ready": payment_execution_report.get(
            "summary", {}
        ).get("status")
        == "ready"
        and payment_execution_report.get("summary", {}).get(
            "target_certification_level"
        )
        == "RDLLM-L77",
        "payment_rail_attestation_ready": payment_rail_attestation.get(
            "summary", {}
        ).get("status")
        == "ready"
        and payment_rail_attestation.get("summary", {}).get(
            "target_certification_level"
        )
        == "RDLLM-L78",
        "input_hashes_reproducible": all(
            _artifact_hash_is_reproducible(artifact)
            for artifact in (
                clearinghouse_report,
                remittance_report,
                payment_execution_report,
                payment_rail_attestation,
            )
        ),
        "remittance_binds_clearinghouse": remittance_report.get("commitments", {}).get(
            "clearinghouse_report_hash"
        )
        == _declared_hash(clearinghouse_report),
        "payment_execution_binds_remittance": payment_execution_report.get(
            "commitments", {}
        ).get("remittance_report_hash")
        == _declared_hash(remittance_report),
        "payment_rail_binds_execution": payment_rail_attestation.get(
            "commitments", {}
        ).get("payment_execution_report_hash")
        == _declared_hash(payment_execution_report),
        "all_payment_instructions_have_creator_receipts": len(payout_rows)
        == len(remittance_report.get("payment_instruction_rows", [])),
        "all_payout_receipts_bind_clearinghouse_rows": all(
            row["clearinghouse_row_present"] for row in payout_rows
        ),
        "all_payout_receipts_bind_execution_rows": all(
            row["execution_status"] == "settled_verified"
            and row["executed_amount"] == row["instructed_amount"]
            and row["execution_row_hash"]
            for row in payout_rows
        ),
        "all_payout_receipts_bind_signed_rail_batches": all(
            row["rail_signature_valid"] and row["rail_batch_signed"] for row in payout_rows
        ),
        "creator_payout_totals_match_execution": _sum_money(
            payout_rows,
            "executed_amount",
        )
        == expected_payment_total,
        "creator_escrow_totals_match_execution": _sum_money(
            escrow_rows,
            "executed_amount",
        )
        == expected_escrow_total,
        "creator_hold_totals_match_execution": _sum_money(
            hold_rows,
            "held_amount",
        )
        == expected_hold_total,
        "payout_accounts_not_disclosed": all(
            row["payout_account_disclosed"] is False for row in payout_rows
        ),
        "private_creator_receipt_fields_absent": not private_paths,
    }
    report = {
        "report_version": CREATOR_PAYOUT_RECEIPT_REPORT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "receipt_policy": {
            "profile": "rdllm-creator-facing-payout-receipts/v1",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": "RDLLM-L78",
            "creator_visible_statuses": [
                "paid_verified",
                "escrowed_verified",
                "held_not_paid",
                "not_verified",
            ],
            "raw_payment_accounts_forbidden": True,
            "raw_prompt_output_source_text_forbidden": True,
            "per_creator_verification_supported": True,
        },
        "creator_payout_rows": payout_rows,
        "creator_escrow_rows": escrow_rows,
        "creator_hold_rows": hold_rows,
        "creator_total_rows": creator_total_rows,
        "checks": checks,
        "commitments": {
            "clearinghouse_report_hash": _declared_hash(clearinghouse_report),
            "remittance_report_hash": _declared_hash(remittance_report),
            "payment_execution_report_hash": _declared_hash(payment_execution_report),
            "payment_rail_attestation_hash": _declared_hash(payment_rail_attestation),
            "creator_payout_root": hash_payload(payout_rows),
            "creator_escrow_root": hash_payload(escrow_rows),
            "creator_hold_root": hash_payload(hold_rows),
            "creator_total_root": hash_payload(creator_total_rows),
        },
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "creator_count": len(
                {row["recipient_creator_id"] for row in payout_rows if row["recipient_creator_id"]}
            ),
            "creator_payout_receipt_count": len(payout_rows),
            "creator_escrow_receipt_count": len(escrow_rows),
            "creator_hold_receipt_count": len(hold_rows),
            "creator_payout_total": _money(_sum_money(payout_rows, "executed_amount")),
            "creator_escrow_total": _money(_sum_money(escrow_rows, "executed_amount")),
            "creator_hold_total": _money(_sum_money(hold_rows, "held_amount")),
            "creator_visible_payouts_verified": all(checks.values()),
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "raw_payment_accounts_disclosed": False,
            "raw_processor_records_disclosed": False,
            "customer_or_tax_records_disclosed": False,
            "uses_payout_account_hashes": True,
            "uses_source_and_settlement_hashes": True,
        },
        "schemas": {
            "creator_payout_receipt_report": CREATOR_PAYOUT_RECEIPT_REPORT_SCHEMA,
            "clearinghouse_report": "docs/schemas/clearinghouse_report.schema.json",
            "remittance_report": "docs/schemas/remittance_report.schema.json",
            "payment_execution_report": "docs/schemas/payment_execution_report.schema.json",
            "payment_rail_attestation": "docs/schemas/payment_rail_attestation.schema.json",
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


def validate_creator_payout_receipt_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "receipt_policy",
        "creator_payout_rows",
        "creator_escrow_rows",
        "creator_hold_rows",
        "creator_total_rows",
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
            errors.append(f"missing creator payout receipt report field: {key}")
    if errors:
        return errors
    if report.get("report_version") != CREATOR_PAYOUT_RECEIPT_REPORT_VERSION:
        errors.append("creator payout receipt report version is unsupported")
    if report.get("receipt_policy", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("creator payout receipt target certification level is unsupported")
    for key in (
        "clearinghouse_report_hash",
        "remittance_report_hash",
        "payment_execution_report_hash",
        "payment_rail_attestation_hash",
        "creator_payout_root",
        "creator_escrow_root",
        "creator_hold_root",
        "creator_total_root",
    ):
        if key not in report.get("commitments", {}):
            errors.append(f"missing creator payout receipt commitment: {key}")
    for key in (
        "status",
        "target_certification_level",
        "creator_count",
        "creator_payout_receipt_count",
        "creator_escrow_receipt_count",
        "creator_hold_receipt_count",
        "creator_payout_total",
        "creator_escrow_total",
        "creator_hold_total",
        "creator_visible_payouts_verified",
    ):
        if key not in report.get("summary", {}):
            errors.append(f"missing creator payout receipt summary field: {key}")
    if "creator_payout_receipt_report" not in report.get("schemas", {}):
        errors.append("missing creator payout receipt report schema")
    return errors


def verify_creator_payout_receipt_report(
    report: dict[str, Any],
    *,
    clearinghouse_report: dict[str, Any],
    remittance_report: dict[str, Any],
    payment_execution_report: dict[str, Any],
    payment_rail_attestation: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify creator-facing payout receipts against settlement proof artifacts."""

    errors = validate_creator_payout_receipt_report_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get("report_hash"):
        errors.append("creator payout receipt report hash is not reproducible")
    expected = make_creator_payout_receipt_report(
        clearinghouse_report=clearinghouse_report,
        remittance_report=remittance_report,
        payment_execution_report=payment_execution_report,
        payment_rail_attestation=payment_rail_attestation,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "receipt_policy",
        "creator_payout_rows",
        "creator_escrow_rows",
        "creator_hold_rows",
        "creator_total_rows",
        "checks",
        "commitments",
        "summary",
        "privacy",
        "schemas",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"creator payout receipt report {key} does not match inputs")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("creator payout receipt report hash does not match inputs")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("creator payout receipt report status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"creator payout receipt check failed: {check}")
    if _contains_private_fields(report):
        errors.append("creator payout receipt report exposes private fields")
    if signing_secret:
        signature = report.get("signature", {})
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("creator payout receipt report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("creator payout receipt report signature is invalid")
    return errors
