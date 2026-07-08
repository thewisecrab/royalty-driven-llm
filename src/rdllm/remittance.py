"""Verifiable remittance instructions for RDLLM clearinghouse settlement."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload

REMITTANCE_REPORT_VERSION = "rdllm-remittance-report/v1"
REMITTANCE_REPORT_SCHEMA = "docs/schemas/remittance_report.schema.json"
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
    "payout_account",
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "swift_bic",
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
        if key
        not in {
            "report_hash",
            "contract_hash",
            "signature",
        }
    }


def _declared_hash(artifact: dict[str, Any]) -> str:
    for field in ("report_hash", "contract_hash"):
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(artifact)


def _artifact_hash_is_reproducible(artifact: dict[str, Any]) -> bool:
    declared = _declared_hash(artifact)
    if artifact.get("report_hash") or artifact.get("contract_hash"):
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


def _license_lookup(contract: dict[str, Any]) -> dict[str, dict[str, dict[str, str]]]:
    by_creator: dict[str, dict[str, str]] = {}
    by_work: dict[str, dict[str, str]] = {}
    for commitment in contract.get("creator_commitments", []):
        creator_id = str(commitment.get("creator_id", ""))
        if not creator_id:
            continue
        by_creator[creator_id] = {
            "creator_id": creator_id,
            "creator_name": str(commitment.get("creator_name", "")),
            "payout_account_hash": str(commitment.get("payout_account_hash", "")),
            "license_status": "unknown",
            "term_hash": "",
        }
    for term in contract.get("terms", []):
        creator_id = str(term.get("creator_id", ""))
        work_id = str(term.get("work_id", ""))
        if not creator_id or not work_id:
            continue
        row = {
            "creator_id": creator_id,
            "creator_name": str(term.get("creator_name", "")),
            "payout_account_hash": str(term.get("payout_account_hash", "")),
            "license_status": str(term.get("consent_status", "unknown")),
            "term_hash": str(term.get("term_hash", "")),
        }
        by_work[f"{creator_id}:{work_id}"] = row
        by_creator[creator_id] = {**by_creator.get(creator_id, {}), **row}
    return {"by_creator": by_creator, "by_work": by_work}


def _license_payment_info(
    row: dict[str, Any],
    *,
    creator_license_contract: dict[str, Any],
) -> dict[str, str]:
    lookup = _license_lookup(creator_license_contract)
    creator_id = str(row.get("recipient_creator_id", ""))
    work_id = str(row.get("work_id", ""))
    return (
        lookup["by_work"].get(f"{creator_id}:{work_id}")
        or lookup["by_creator"].get(creator_id)
        or {
            "creator_id": creator_id,
            "creator_name": "",
            "payout_account_hash": "",
            "license_status": "missing",
            "term_hash": "",
        }
    )


def _end_to_end_id(seed: dict[str, Any]) -> str:
    return f"RDLLM-{hash_payload(seed)[:29]}"


def _payment_instruction_row(
    row: dict[str, Any],
    *,
    clearinghouse_report_hash: str,
    creator_license_contract_hash: str,
    creator_license_contract: dict[str, Any],
    payment_rail: str,
) -> dict[str, Any]:
    payment_info = _license_payment_info(
        row,
        creator_license_contract=creator_license_contract,
    )
    seed = {
        "clearinghouse_report_hash": clearinghouse_report_hash,
        "settlement_row_hash": row.get("settlement_row_hash", ""),
        "recipient_creator_id": row.get("recipient_creator_id", ""),
        "work_id": row.get("work_id", ""),
        "amount": row.get("total_payout", "0"),
        "currency": row.get("currency", ""),
    }
    instruction_id = hash_payload(seed)
    end_to_end_id = _end_to_end_id(seed)
    instruction = {
        "payment_instruction_id": instruction_id,
        "instruction_status": "ready_for_payment_file",
        "payment_rail": payment_rail,
        "recipient_creator_id": str(row.get("recipient_creator_id", "")),
        "recipient_creator_name": payment_info.get("creator_name", ""),
        "recipient_kind": str(row.get("recipient_kind", "creator")),
        "work_id": str(row.get("work_id", "")),
        "currency": str(row.get("currency", "")),
        "amount": _money(row.get("total_payout", "0")),
        "payout_account_hash": payment_info.get("payout_account_hash", ""),
        "payout_account_disclosed": False,
        "license_status": payment_info.get("license_status", "missing"),
        "license_term_hash": payment_info.get("term_hash", ""),
        "creator_license_contract_hash": creator_license_contract_hash,
        "clearinghouse_report_hash": clearinghouse_report_hash,
        "clearinghouse_settlement_row_hash": str(row.get("settlement_row_hash", "")),
        "origin_hashes": sorted(str(item) for item in row.get("origin_hashes", [])),
        "chunk_ids": sorted(str(item) for item in row.get("chunk_ids", [])),
        "obligation_count": int(row.get("obligation_count", 0) or 0),
        "end_to_end_id": end_to_end_id,
        "remittance_reference": f"RDLLM royalty {instruction_id[:16]}",
        "payment_rail_fields": {
            "message_family": "ISO 20022 Payments Initiation",
            "message_type": "pain.001-compatible-credit-transfer",
            "creditor_account_hash": payment_info.get("payout_account_hash", ""),
            "ultimate_creditor_id": str(row.get("recipient_creator_id", "")),
            "instructed_amount": _money(row.get("total_payout", "0")),
            "currency": str(row.get("currency", "")),
            "end_to_end_id": end_to_end_id,
            "remittance_information": {
                "structured_reference_type": "RDLLM",
                "structured_reference": instruction_id[:32],
                "clearinghouse_reference": clearinghouse_report_hash[:32],
                "settlement_row_reference": str(row.get("settlement_row_hash", ""))[:32],
            },
        },
    }
    instruction["instruction_row_hash"] = hash_payload(instruction)
    return instruction


def _escrow_instruction_row(
    row: dict[str, Any],
    *,
    clearinghouse_report_hash: str,
    escrow_account_id: str,
    payment_rail: str,
) -> dict[str, Any]:
    seed = {
        "clearinghouse_report_hash": clearinghouse_report_hash,
        "settlement_row_hash": row.get("settlement_row_hash", ""),
        "escrow_recipient": row.get("recipient_creator_id", ""),
        "amount": row.get("total_payout", "0"),
        "currency": row.get("currency", ""),
    }
    instruction_id = hash_payload(seed)
    instruction = {
        "escrow_instruction_id": instruction_id,
        "instruction_status": "ready_for_escrow_file",
        "payment_rail": payment_rail,
        "escrow_account_hash": hash_payload({"escrow_account_id": escrow_account_id}),
        "escrow_account_disclosed": False,
        "escrow_reason": "rights_or_registry_resolution_required",
        "recipient_creator_id": str(row.get("recipient_creator_id", "")),
        "work_id": str(row.get("work_id", "")),
        "currency": str(row.get("currency", "")),
        "amount": _money(row.get("total_payout", "0")),
        "clearinghouse_report_hash": clearinghouse_report_hash,
        "clearinghouse_settlement_row_hash": str(row.get("settlement_row_hash", "")),
        "origin_hashes": sorted(str(item) for item in row.get("origin_hashes", [])),
        "chunk_ids": sorted(str(item) for item in row.get("chunk_ids", [])),
        "end_to_end_id": _end_to_end_id(seed),
        "remittance_reference": f"RDLLM escrow {instruction_id[:16]}",
    }
    instruction["instruction_row_hash"] = hash_payload(instruction)
    return instruction


def _clearing_hold_row(row: dict[str, Any], *, clearinghouse_report_hash: str) -> dict[str, Any]:
    hold = {
        "hold_id": hash_payload(
            {
                "clearinghouse_report_hash": clearinghouse_report_hash,
                "normalized_obligation_hash": row.get("normalized_obligation_hash", ""),
            }
        ),
        "hold_status": str(row.get("settlement_status", "")),
        "hold_reason": str(row.get("hold_reason", "")),
        "recipient_creator_id": str(row.get("recipient_creator_id", "")),
        "work_id": str(row.get("work_id", "")),
        "chunk_id": str(row.get("chunk_id", "")),
        "currency": str(row.get("currency", "")),
        "amount": _money(row.get("payout", "0")),
        "clearinghouse_report_hash": clearinghouse_report_hash,
        "clearinghouse_obligation_hash": str(row.get("normalized_obligation_hash", "")),
        "origin_hash": str(row.get("origin_hash", "")),
        "origin_row_hash": str(row.get("origin_row_hash", "")),
    }
    hold["hold_row_hash"] = hash_payload(hold)
    return hold


def _missing_account_hold_row(
    row: dict[str, Any],
    *,
    clearinghouse_report_hash: str,
) -> dict[str, Any]:
    hold = {
        "hold_id": hash_payload(
            {
                "clearinghouse_report_hash": clearinghouse_report_hash,
                "settlement_row_hash": row.get("settlement_row_hash", ""),
                "hold_reason": "missing_payout_account_hash",
            }
        ),
        "hold_status": "held_missing_payout_account",
        "hold_reason": "missing_payout_account_hash",
        "recipient_creator_id": str(row.get("recipient_creator_id", "")),
        "work_id": str(row.get("work_id", "")),
        "chunk_id": "",
        "currency": str(row.get("currency", "")),
        "amount": _money(row.get("total_payout", "0")),
        "clearinghouse_report_hash": clearinghouse_report_hash,
        "clearinghouse_obligation_hash": "",
        "clearinghouse_settlement_row_hash": str(row.get("settlement_row_hash", "")),
        "origin_hashes": sorted(str(item) for item in row.get("origin_hashes", [])),
    }
    hold["hold_row_hash"] = hash_payload(hold)
    return hold


def make_remittance_report(
    *,
    clearinghouse_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    payment_rail: str = "iso20022-pain001-compatible",
    escrow_account_id: str = "rdllm-registry-escrow",
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create payment-file-ready remittance instructions from a clearinghouse report."""

    clearinghouse_hash = _declared_hash(clearinghouse_report)
    license_hash = _declared_hash(creator_license_contract)
    payment_rows: list[dict[str, Any]] = []
    missing_account_holds: list[dict[str, Any]] = []
    for row in clearinghouse_report.get("payable_rows", []):
        instruction = _payment_instruction_row(
            row,
            clearinghouse_report_hash=clearinghouse_hash,
            creator_license_contract_hash=license_hash,
            creator_license_contract=creator_license_contract,
            payment_rail=payment_rail,
        )
        if (
            instruction["payout_account_hash"]
            and instruction["license_status"] == "active"
        ):
            payment_rows.append(instruction)
        else:
            missing_account_holds.append(
                _missing_account_hold_row(
                    row,
                    clearinghouse_report_hash=clearinghouse_hash,
                )
            )
    escrow_rows = [
        _escrow_instruction_row(
            row,
            clearinghouse_report_hash=clearinghouse_hash,
            escrow_account_id=escrow_account_id,
            payment_rail=payment_rail,
        )
        for row in clearinghouse_report.get("escrow_rows", [])
    ]
    clearing_holds = [
        _clearing_hold_row(row, clearinghouse_report_hash=clearinghouse_hash)
        for row in clearinghouse_report.get("held_rows", [])
    ]
    payment_rows = _sort_rows(payment_rows, "recipient_creator_id", "work_id", "currency")
    escrow_rows = _sort_rows(escrow_rows, "recipient_creator_id", "work_id", "currency")
    remittance_hold_rows = _sort_rows(
        clearing_holds + missing_account_holds,
        "hold_status",
        "recipient_creator_id",
        "work_id",
        "amount",
    )
    payable_total = _decimal(clearinghouse_report.get("summary", {}).get("payable_total", "0"))
    escrow_total = _decimal(clearinghouse_report.get("summary", {}).get("escrow_total", "0"))
    clearing_held_total = _decimal(
        clearinghouse_report.get("summary", {}).get("held_total", "0")
    )
    payment_total = _sum_money(payment_rows, "amount")
    escrow_instruction_total = _sum_money(escrow_rows, "amount")
    clearing_hold_total = _sum_money(clearing_holds, "amount")
    missing_account_hold_total = _sum_money(missing_account_holds, "amount")
    accounted_total = (
        payment_total
        + escrow_instruction_total
        + clearing_hold_total
        + missing_account_hold_total
    ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    expected_clearing_total = (
        payable_total + escrow_total + clearing_held_total
    ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    checks = {
        "clearinghouse_hash_reproducible": _artifact_hash_is_reproducible(
            clearinghouse_report
        ),
        "creator_license_contract_hash_reproducible": _artifact_hash_is_reproducible(
            creator_license_contract
        ),
        "clearinghouse_report_ready": clearinghouse_report.get("summary", {}).get("status")
        == "ready",
        "payment_instructions_cover_all_payable_rows": len(payment_rows)
        == len(clearinghouse_report.get("payable_rows", [])),
        "payable_rows_have_payout_account_hashes": all(
            row.get("payout_account_hash") and row.get("payout_account_disclosed") is False
            for row in payment_rows
        ),
        "payable_rows_have_active_license_terms": all(
            row.get("license_status") == "active" and row.get("license_term_hash")
            for row in payment_rows
        ),
        "payment_instructions_conserve_payable_total": payment_total == payable_total,
        "escrow_instructions_conserve_escrow_total": escrow_instruction_total
        == escrow_total,
        "clearinghouse_held_rows_preserved": clearing_hold_total == clearing_held_total
        and len(clearing_holds) == len(clearinghouse_report.get("held_rows", [])),
        "missing_payment_account_holds_empty": not missing_account_holds,
        "all_cleared_value_accounted_for": accounted_total == expected_clearing_total,
        "instruction_only_no_bank_settlement_asserted": True,
        "no_private_payment_account_disclosed": True,
    }
    report = {
        "report_version": REMITTANCE_REPORT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "remittance_policy": {
            "profile": "rdllm-verifiable-remittance/v1",
            "payment_rail": payment_rail,
            "payment_execution_mode": "instruction_only",
            "clearinghouse_report_hash": clearinghouse_hash,
            "creator_license_contract_hash": license_hash,
            "target_certification_level": "RDLLM-L44",
            "minimum_input_level": "RDLLM-L43",
            "standards_alignment": {
                "payment_initiation": "ISO 20022 pain.001-compatible",
                "remittance_advice": "ISO 20022 remt.001-compatible",
                "verifiable_claims": "W3C Verifiable Credentials 2.0-shaped",
                "provenance": "W3C PROV-shaped",
            },
            "raw_payout_accounts_forbidden": True,
        },
        "payment_instruction_rows": payment_rows,
        "escrow_instruction_rows": escrow_rows,
        "remittance_hold_rows": remittance_hold_rows,
        "checks": checks,
        "commitments": {
            "clearinghouse_report_hash": clearinghouse_hash,
            "creator_license_contract_hash": license_hash,
            "payment_instruction_root": hash_payload(payment_rows),
            "escrow_instruction_root": hash_payload(escrow_rows),
            "remittance_hold_root": hash_payload(remittance_hold_rows),
            "payment_rail_policy_hash": hash_payload(
                {
                    "payment_rail": payment_rail,
                    "payment_execution_mode": "instruction_only",
                    "escrow_account_hash": hash_payload(
                        {"escrow_account_id": escrow_account_id}
                    ),
                }
            ),
        },
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": "RDLLM-L44",
            "payment_instruction_count": len(payment_rows),
            "escrow_instruction_count": len(escrow_rows),
            "remittance_hold_count": len(remittance_hold_rows),
            "payment_total": _money(payment_total),
            "escrow_instruction_total": _money(escrow_instruction_total),
            "clearinghouse_held_total": _money(clearing_hold_total),
            "missing_account_hold_total": _money(missing_account_hold_total),
            "accounted_total": _money(accounted_total),
            "expected_clearing_total": _money(expected_clearing_total),
            "payment_rail": payment_rail,
            "instruction_only": True,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "payout_account_disclosed": False,
            "escrow_account_disclosed": False,
            "uses_payout_account_hashes": True,
            "uses_payment_reconciliation_hashes": True,
        },
        "schemas": {
            "remittance_report": REMITTANCE_REPORT_SCHEMA,
            "clearinghouse_report": "docs/schemas/clearinghouse_report.schema.json",
            "creator_license_contract": "docs/schemas/creator_license_contract.schema.json",
        },
    }
    private_paths = _contains_private_fields(report)
    if private_paths:
        report["checks"]["no_private_payment_account_disclosed"] = False
        report["summary"]["status"] = "failed"
        report["summary"]["private_field_paths"] = private_paths
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


def validate_remittance_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "remittance_policy",
        "payment_instruction_rows",
        "escrow_instruction_rows",
        "remittance_hold_rows",
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
            errors.append(f"missing remittance report field: {key}")
    if errors:
        return errors
    if report.get("report_version") != REMITTANCE_REPORT_VERSION:
        errors.append("remittance report version is unsupported")
    for key in (
        "profile",
        "payment_rail",
        "payment_execution_mode",
        "clearinghouse_report_hash",
        "creator_license_contract_hash",
        "target_certification_level",
    ):
        if key not in report.get("remittance_policy", {}):
            errors.append(f"missing remittance policy field: {key}")
    for key in (
        "payment_instruction_root",
        "escrow_instruction_root",
        "remittance_hold_root",
        "payment_rail_policy_hash",
    ):
        if key not in report.get("commitments", {}):
            errors.append(f"missing remittance commitment: {key}")
    for row in report.get("payment_instruction_rows", []):
        for key in (
            "payment_instruction_id",
            "instruction_status",
            "recipient_creator_id",
            "work_id",
            "currency",
            "amount",
            "payout_account_hash",
            "clearinghouse_settlement_row_hash",
            "end_to_end_id",
            "instruction_row_hash",
        ):
            if key not in row:
                errors.append(f"missing payment instruction field: {key}")
    for key in (
        "status",
        "target_certification_level",
        "payment_instruction_count",
        "payment_total",
        "accounted_total",
        "expected_clearing_total",
        "instruction_only",
    ):
        if key not in report.get("summary", {}):
            errors.append(f"missing remittance summary field: {key}")
    if "remittance_report" not in report.get("schemas", {}):
        errors.append("missing remittance report schema")
    return errors


def verify_remittance_report(
    report: dict[str, Any],
    *,
    clearinghouse_report: dict[str, Any],
    creator_license_contract: dict[str, Any],
    escrow_account_id: str = "rdllm-registry-escrow",
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a remittance report against clearinghouse and license artifacts."""

    errors = validate_remittance_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("remittance report hash is not reproducible")

    expected = make_remittance_report(
        clearinghouse_report=clearinghouse_report,
        creator_license_contract=creator_license_contract,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        payment_rail=report.get("remittance_policy", {}).get(
            "payment_rail", "iso20022-pain001-compatible"
        ),
        escrow_account_id=escrow_account_id,
        signing_secret=signing_secret,
    )
    for key in (
        "remittance_policy",
        "payment_instruction_rows",
        "escrow_instruction_rows",
        "remittance_hold_rows",
        "checks",
        "commitments",
        "summary",
        "privacy",
        "schemas",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"remittance report {key} does not match source artifacts")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("remittance report hash does not match source artifacts")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("remittance report status is not ready")
    if report.get("summary", {}).get("instruction_only") is not True:
        errors.append("remittance report must be instruction-only")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"remittance check failed: {check}")
    if report.get("privacy", {}).get("payout_account_disclosed") is not False:
        errors.append("remittance report discloses payout accounts")
    if report.get("privacy", {}).get("uses_payout_account_hashes") is not True:
        errors.append("remittance report must use payout account hashes")
    private_paths = _contains_private_fields(report)
    if private_paths:
        errors.append(
            "remittance report exposes private fields: "
            + ", ".join(sorted(private_paths))
        )
    for term in creator_license_contract.get("terms", []):
        if term.get("payout_account_disclosed") is not False:
            errors.append("creator license contract term discloses payout account")
    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("remittance report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("remittance report signature is invalid")

    return errors
