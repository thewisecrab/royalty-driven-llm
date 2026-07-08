"""Forward-only settlement adjustments after attribution adjudication."""

from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash

POST_ADJUDICATION_SETTLEMENT_ADJUSTMENT_VERSION = (
    "rdllm-post-adjudication-settlement-adjustment-report/v1"
)
POST_ADJUDICATION_SETTLEMENT_ADJUSTMENT_SCHEMA = (
    "docs/schemas/post_adjudication_settlement_adjustment_report.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L94"
MONEY_QUANT = Decimal("0.000001")
DEFAULT_RECOUPMENT_CAP_RATE = Decimal("0.50")
DEFAULT_MINIMUM_ADJUSTMENT = Decimal("0.000001")

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "response_text",
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "private_note",
    "private_notes",
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

DECLARED_HASH_FIELDS = (
    "report_hash",
    "card_hash",
    "manifest_hash",
    "bundle_hash",
    "graph_hash",
    "attestation_hash",
    "receipt_hash",
    "event_hash",
    "artifact_hash",
    "row_hash",
    "payment_execution_hash",
)


def _decimal(value: Any, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _money(value: Any) -> str:
    return str(_decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


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


def _declared_artifact_hash(artifact: dict[str, Any]) -> str:
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return ""


def _contains_private_fields(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in PRIVATE_FIELD_NAMES:
                return True
            if _contains_private_fields(child):
                return True
    elif isinstance(value, list):
        return any(_contains_private_fields(child) for child in value)
    return False


def _public_hash(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) or isinstance(value, list):
        return hash_payload(value)
    return stable_hash(str(value))


def _recipient(row: dict[str, Any]) -> str:
    return str(
        row.get("recipient_creator_id")
        or row.get("creator_id")
        or row.get("recipient_id")
        or ""
    )


def _appeal_state(adjustment_input: dict[str, Any]) -> str:
    policy = dict(adjustment_input.get("policy", {}))
    appeal = dict(
        adjustment_input.get(
            "appeal_window",
            policy.get("appeal_window", adjustment_input.get("adjustment_window", {})),
        )
    )
    if appeal.get("appeal_filed") or policy.get("appeal_filed"):
        return "appeal_pending"
    state = str(
        policy.get(
            "appeal_state",
            appeal.get("state", appeal.get("status", policy.get("status", "closed"))),
        )
    ).lower()
    if state in {"open", "pending", "appeal_pending", "under_review"}:
        return "appeal_pending"
    return "closed"


def _basis_row(adjustment_input: dict[str, Any]) -> dict[str, Any]:
    basis = dict(
        adjustment_input.get(
            "basis_adjudication_report",
            adjustment_input.get("basis_artifact", {}),
        )
    )
    declared_hash = str(
        adjustment_input.get("basis_adjudication_hash")
        or basis.get("report_hash")
        or basis.get("artifact_hash")
        or ""
    )
    canonical_hash = hash_payload(basis) if basis else ""
    replay_hash = hash_payload(_hashable_artifact(basis)) if basis else ""
    basis_hash = declared_hash or replay_hash or canonical_hash
    hash_candidates = {value for value in (declared_hash, canonical_hash, replay_hash) if value}
    return {
        "artifact_type": str(
            adjustment_input.get(
                "basis_artifact_type",
                basis.get("version", "rdllm-attribution-dispute-adjudication-report/v1"),
            )
        ),
        "artifact_hash": basis_hash,
        "payload_hash": replay_hash or canonical_hash,
        "hash_reproducible": bool(basis_hash) and basis_hash in hash_candidates,
        "basis_status": str(basis.get("summary", {}).get("status", "")),
        "basis_target_certification_level": str(
            basis.get("summary", {}).get("target_certification_level", "")
        ),
        "basis_case_id": str(
            basis.get("summary", {}).get("case_id")
            or basis.get("case", {}).get("case_id")
            or adjustment_input.get("basis_case_id", "")
        ),
        "released_total": _money(
            basis.get("summary", {}).get("released_total")
            or basis.get("escrow", {}).get("released_total")
            or "0"
        ),
    }


def _paid_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    public = {
        "payment_id": str(row.get("payment_id", row.get("release_id", f"payment:{index}"))),
        "recipient_creator_id": _recipient(row),
        "work_id": str(row.get("work_id", "")),
        "chunk_id": str(row.get("chunk_id", "")),
        "source_row_hash": str(row.get("source_row_hash", "")),
        "currency": str(row.get("currency", "USD")),
        "amount": _money(row.get("amount", "0")),
        "payment_execution_hash": str(
            row.get("payment_execution_hash")
            or row.get("execution_hash")
            or row.get("processor_batch_hash", "")
        ),
        "creator_payout_receipt_hash": str(
            row.get("creator_payout_receipt_hash")
            or row.get("payout_receipt_hash")
            or row.get("receipt_hash", "")
        ),
        "original_settlement_hash": str(
            row.get("original_settlement_hash")
            or row.get("settlement_release_hash")
            or row.get("release_row_hash", "")
        ),
    }
    public["historical_payment_hash"] = str(
        row.get("historical_payment_hash") or row.get("payment_row_hash") or hash_payload(public)
    )
    return public


def _entitlement_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    public = {
        "entitlement_id": str(row.get("entitlement_id", f"entitlement:{index}")),
        "recipient_creator_id": _recipient(row),
        "work_id": str(row.get("work_id", "")),
        "chunk_id": str(row.get("chunk_id", "")),
        "source_row_hash": str(row.get("source_row_hash", "")),
        "currency": str(row.get("currency", "USD")),
        "corrected_amount": _money(
            row.get("corrected_amount", row.get("amount", row.get("entitlement_amount", "0")))
        ),
        "decision_hash": str(
            row.get("decision_hash")
            or row.get("adjudication_decision_hash")
            or row.get("claim_hash", "")
        ),
        "basis": str(row.get("basis", "corrected_post_adjudication_entitlement")),
    }
    public["corrected_entitlement_hash"] = str(
        row.get("corrected_entitlement_hash") or hash_payload(public)
    )
    return public


def _escrow_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    public = {
        "escrow_id": str(row.get("escrow_id", f"escrow:{index}")),
        "escrow_account_hash": str(row.get("escrow_account_hash", "")),
        "currency": str(row.get("currency", "USD")),
        "amount": _money(row.get("amount", "0")),
        "source": str(row.get("source", "post_adjudication_adjustment_pool")),
    }
    public["escrow_row_hash"] = str(row.get("escrow_row_hash") or hash_payload(public))
    return public


def _future_payable_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    public = {
        "payable_id": str(row.get("payable_id", f"future-payable:{index}")),
        "recipient_creator_id": _recipient(row),
        "currency": str(row.get("currency", "USD")),
        "amount": _money(row.get("amount", "0")),
        "payable_period": str(row.get("payable_period", "")),
        "payable_hash": str(row.get("payable_hash") or row.get("row_hash", "")),
    }
    if not public["payable_hash"]:
        public["payable_hash"] = hash_payload(public)
    return public


def _totals_by_creator(rows: list[dict[str, Any]], amount_field: str) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for row in rows:
        creator_id = row.get("recipient_creator_id", "")
        totals[creator_id] = totals.get(creator_id, Decimal("0")) + _decimal(
            row.get(amount_field, "0")
        )
    return totals


def _make_adjustment_rows(
    *,
    deltas: dict[str, Decimal],
    paid_rows: list[dict[str, Any]],
    entitlement_rows: list[dict[str, Any]],
    escrow_rows: list[dict[str, Any]],
    future_payable_rows: list[dict[str, Any]],
    basis_hash: str,
    status: str,
    recoupment_cap_rate: Decimal,
    minimum_adjustment: Decimal,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    top_up_rows: list[dict[str, Any]] = []
    recoupment_rows: list[dict[str, Any]] = []
    future_netting_rows: list[dict[str, Any]] = []
    freeze_rows: list[dict[str, Any]] = []
    receipt_rows: list[dict[str, Any]] = []
    paid_by_creator = {row["recipient_creator_id"]: row for row in paid_rows}
    entitlement_by_creator = {row["recipient_creator_id"]: row for row in entitlement_rows}
    future_by_creator: dict[str, list[dict[str, Any]]] = {}
    for row in future_payable_rows:
        future_by_creator.setdefault(row["recipient_creator_id"], []).append(row)
    escrow_account_hash = escrow_rows[0]["escrow_account_hash"] if escrow_rows else ""
    currency = (
        entitlement_rows[0]["currency"]
        if entitlement_rows
        else paid_rows[0]["currency"]
        if paid_rows
        else "USD"
    )
    for index, creator_id in enumerate(sorted(deltas), start=1):
        delta = deltas[creator_id]
        if abs(delta) < minimum_adjustment:
            continue
        paid = paid_by_creator.get(creator_id, {})
        entitlement = entitlement_by_creator.get(creator_id, {})
        if status != "ready":
            freeze = {
                "freeze_id": f"freeze:post-adjudication-adjustment:{index}",
                "recipient_creator_id": creator_id,
                "currency": str(entitlement.get("currency") or paid.get("currency") or currency),
                "amount": _money(abs(delta)),
                "delta_amount": _money(delta),
                "reason": "appeal_or_unresolved_post_adjudication_adjustment",
                "basis_adjudication_hash": basis_hash,
                "historical_payment_hash": str(paid.get("historical_payment_hash", "")),
                "corrected_entitlement_hash": str(
                    entitlement.get("corrected_entitlement_hash", "")
                ),
            }
            freeze["freeze_row_hash"] = hash_payload(freeze)
            freeze_rows.append(freeze)
            receipt = _adjustment_receipt(
                creator_id=creator_id,
                adjustment_type="freeze",
                amount=abs(delta),
                basis_hash=basis_hash,
                paid=paid,
                entitlement=entitlement,
                row_hash=freeze["freeze_row_hash"],
                index=index,
            )
            receipt_rows.append(receipt)
            continue
        if delta > 0:
            top_up = {
                "top_up_id": f"top-up:post-adjudication:{index}",
                "recipient_creator_id": creator_id,
                "work_id": str(entitlement.get("work_id", "")),
                "chunk_id": str(entitlement.get("chunk_id", "")),
                "source_row_hash": str(entitlement.get("source_row_hash", "")),
                "currency": str(entitlement.get("currency") or currency),
                "amount": _money(delta),
                "basis": "post_adjudication_underpayment_top_up",
                "basis_adjudication_hash": basis_hash,
                "escrow_account_hash": escrow_account_hash,
                "historical_payment_hash": str(paid.get("historical_payment_hash", "")),
                "corrected_entitlement_hash": str(
                    entitlement.get("corrected_entitlement_hash", "")
                ),
            }
            top_up["top_up_row_hash"] = hash_payload(top_up)
            top_up_rows.append(top_up)
            receipt_rows.append(
                _adjustment_receipt(
                    creator_id=creator_id,
                    adjustment_type="top_up",
                    amount=delta,
                    basis_hash=basis_hash,
                    paid=paid,
                    entitlement=entitlement,
                    row_hash=top_up["top_up_row_hash"],
                    index=index,
                )
            )
        elif delta < 0:
            overpaid = abs(delta)
            payable_total = sum(
                _decimal(row["amount"]) for row in future_by_creator.get(creator_id, [])
            )
            cap_amount = (payable_total * recoupment_cap_rate).quantize(
                MONEY_QUANT, rounding=ROUND_HALF_UP
            )
            recoupment_amount = min(overpaid, cap_amount)
            if recoupment_amount <= 0:
                freeze = {
                    "freeze_id": f"freeze:post-adjudication-recoupment:{index}",
                    "recipient_creator_id": creator_id,
                    "currency": str(paid.get("currency") or currency),
                    "amount": _money(overpaid),
                    "delta_amount": _money(delta),
                    "reason": "no_future_payable_available_for_capped_recoupment",
                    "basis_adjudication_hash": basis_hash,
                    "historical_payment_hash": str(paid.get("historical_payment_hash", "")),
                    "corrected_entitlement_hash": str(
                        entitlement.get("corrected_entitlement_hash", "")
                    ),
                }
                freeze["freeze_row_hash"] = hash_payload(freeze)
                freeze_rows.append(freeze)
                continue
            recoupment = {
                "recoupment_id": f"recoupment:post-adjudication:{index}",
                "recipient_creator_id": creator_id,
                "currency": str(paid.get("currency") or currency),
                "amount": _money(recoupment_amount),
                "overpaid_amount": _money(overpaid),
                "recoupment_cap_rate": str(recoupment_cap_rate),
                "future_payable_total": _money(payable_total),
                "basis": "post_adjudication_overpayment_forward_netting",
                "basis_adjudication_hash": basis_hash,
                "historical_payment_hash": str(paid.get("historical_payment_hash", "")),
                "corrected_entitlement_hash": str(
                    entitlement.get("corrected_entitlement_hash", "")
                ),
            }
            recoupment["recoupment_row_hash"] = hash_payload(recoupment)
            recoupment_rows.append(recoupment)
            remaining = recoupment_amount
            for payable in future_by_creator.get(creator_id, []):
                if remaining <= 0:
                    break
                amount = min(remaining, _decimal(payable["amount"]))
                netting = {
                    "netting_id": (
                        f"netting:post-adjudication:{index}:{len(future_netting_rows) + 1}"
                    ),
                    "recoupment_id": recoupment["recoupment_id"],
                    "recipient_creator_id": creator_id,
                    "future_payable_id": payable["payable_id"],
                    "future_payable_hash": payable["payable_hash"],
                    "currency": payable["currency"],
                    "amount": _money(amount),
                    "basis": "forward_only_future_payable_netting",
                }
                netting["netting_row_hash"] = hash_payload(netting)
                future_netting_rows.append(netting)
                remaining -= amount
            receipt_rows.append(
                _adjustment_receipt(
                    creator_id=creator_id,
                    adjustment_type="recoupment",
                    amount=recoupment_amount,
                    basis_hash=basis_hash,
                    paid=paid,
                    entitlement=entitlement,
                    row_hash=recoupment["recoupment_row_hash"],
                    index=index,
                )
            )
    return top_up_rows, recoupment_rows, future_netting_rows, freeze_rows, receipt_rows


def _adjustment_receipt(
    *,
    creator_id: str,
    adjustment_type: str,
    amount: Decimal,
    basis_hash: str,
    paid: dict[str, Any],
    entitlement: dict[str, Any],
    row_hash: str,
    index: int,
) -> dict[str, Any]:
    receipt = {
        "receipt_id": f"creator-adjustment-receipt:{index}:{adjustment_type}",
        "recipient_creator_id": creator_id,
        "adjustment_type": adjustment_type,
        "currency": str(entitlement.get("currency") or paid.get("currency") or "USD"),
        "amount": _money(amount),
        "basis": "creator_visible_post_adjudication_adjustment",
        "basis_adjudication_hash": basis_hash,
        "historical_payment_hash": str(paid.get("historical_payment_hash", "")),
        "corrected_entitlement_hash": str(
            entitlement.get("corrected_entitlement_hash", "")
        ),
        "adjustment_row_hash": row_hash,
    }
    receipt["receipt_hash"] = hash_payload(receipt)
    return receipt


def load_post_adjudication_settlement_adjustment_input(
    path: str | Path,
) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def make_post_adjudication_settlement_adjustment_report(
    adjustment_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed forward-only adjustment report after an adjudication result."""

    policy = dict(adjustment_input.get("policy", {}))
    recoupment_cap_rate = _decimal(
        policy.get("recoupment_cap_rate", DEFAULT_RECOUPMENT_CAP_RATE)
    )
    minimum_adjustment = _decimal(
        policy.get("minimum_adjustment", DEFAULT_MINIMUM_ADJUSTMENT)
    )
    basis = _basis_row(adjustment_input)
    appeal_state = _appeal_state(adjustment_input)
    paid_rows = [
        _paid_row(row, index)
        for index, row in enumerate(adjustment_input.get("previously_paid_rows", []), start=1)
    ]
    entitlement_rows = [
        _entitlement_row(row, index)
        for index, row in enumerate(
            adjustment_input.get("corrected_entitlement_rows", []), start=1
        )
    ]
    escrow_rows = [
        _escrow_row(row, index)
        for index, row in enumerate(adjustment_input.get("escrow_rows", []), start=1)
    ]
    future_payable_rows = [
        _future_payable_row(row, index)
        for index, row in enumerate(adjustment_input.get("future_payable_rows", []), start=1)
    ]
    paid_totals = _totals_by_creator(paid_rows, "amount")
    corrected_totals = _totals_by_creator(entitlement_rows, "corrected_amount")
    creators = sorted(set(paid_totals) | set(corrected_totals))
    deltas = {
        creator_id: corrected_totals.get(creator_id, Decimal("0"))
        - paid_totals.get(creator_id, Decimal("0"))
        for creator_id in creators
    }
    ready_basis = (
        basis["hash_reproducible"]
        and basis["basis_status"] == "ready"
        and basis["basis_target_certification_level"] == "RDLLM-L93"
    )
    if ready_basis and appeal_state == "closed":
        status = "ready"
    elif ready_basis and appeal_state == "appeal_pending":
        status = "appeal_pending"
    else:
        status = "needs_review"

    (
        top_up_rows,
        recoupment_rows,
        future_netting_rows,
        freeze_rows,
        creator_adjustment_receipts,
    ) = _make_adjustment_rows(
        deltas=deltas,
        paid_rows=paid_rows,
        entitlement_rows=entitlement_rows,
        escrow_rows=escrow_rows,
        future_payable_rows=future_payable_rows,
        basis_hash=basis["artifact_hash"],
        status=status,
        recoupment_cap_rate=recoupment_cap_rate,
        minimum_adjustment=minimum_adjustment,
    )

    paid_total = sum(_decimal(row["amount"]) for row in paid_rows)
    corrected_total = sum(_decimal(row["corrected_amount"]) for row in entitlement_rows)
    top_up_total = sum(_decimal(row["amount"]) for row in top_up_rows)
    recoupment_total = sum(_decimal(row["amount"]) for row in recoupment_rows)
    frozen_total = sum(_decimal(row["amount"]) for row in freeze_rows)
    escrow_total = sum(_decimal(row["amount"]) for row in escrow_rows)
    netting_total = sum(_decimal(row["amount"]) for row in future_netting_rows)
    net_delta = corrected_total - paid_total
    net_adjustment = top_up_total - recoupment_total
    recoupment_by_creator = _totals_by_creator(recoupment_rows, "amount")
    future_by_creator = _totals_by_creator(future_payable_rows, "amount")
    underpayment_total = sum(delta for delta in deltas.values() if delta > 0)
    overpayment_total = sum(abs(delta) for delta in deltas.values() if delta < 0)
    checks = {
        "basis_adjudication_ready": ready_basis,
        "historical_events_not_rewritten": all(
            row["historical_payment_hash"] for row in paid_rows
        )
        and bool(paid_rows),
        "payment_execution_or_receipt_hashes_present": all(
            row["payment_execution_hash"] or row["creator_payout_receipt_hash"]
            for row in paid_rows
        )
        and bool(paid_rows),
        "corrected_entitlements_hash_bound": all(
            row["corrected_entitlement_hash"] and row["decision_hash"]
            for row in entitlement_rows
        )
        and bool(entitlement_rows),
        "appeal_window_enforced": (
            appeal_state == "closed"
            or (
                appeal_state == "appeal_pending"
                and not top_up_rows
                and not recoupment_rows
                and not future_netting_rows
                and frozen_total == sum(abs(delta) for delta in deltas.values())
            )
        ),
        "recoupment_cap_enforced": all(
            amount
            <= (
                future_by_creator.get(creator_id, Decimal("0")) * recoupment_cap_rate
            ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            for creator_id, amount in recoupment_by_creator.items()
        ),
        "future_netting_matches_recoupment": netting_total == recoupment_total,
        "adjustment_totals_conserved": (
            (status == "ready" and net_delta == net_adjustment)
            or (status != "ready" and not top_up_rows and not recoupment_rows)
        ),
        "escrow_covers_top_ups": top_up_total <= escrow_total,
        "creator_visible_adjustment_receipts_created": len(creator_adjustment_receipts)
        == len(top_up_rows) + len(recoupment_rows) + len(freeze_rows),
        "private_text_not_disclosed": True,
    }
    if not all(checks.values()) and status == "ready":
        status = "needs_review"

    report = {
        "version": POST_ADJUDICATION_SETTLEMENT_ADJUSTMENT_VERSION,
        "issued_at": created_at or now_iso(),
        "issuer": issuer,
        "case": {
            "adjustment_case_id": str(
                adjustment_input.get("adjustment_case_id", adjustment_input.get("case_id", ""))
            ),
            "case_type": str(
                adjustment_input.get(
                    "case_type", "post_adjudication_settlement_adjustment"
                )
            ),
            "status": status,
            "opened_at": str(adjustment_input.get("opened_at", "")),
            "basis_adjudication": basis,
        },
        "policy": {
            "recoupment_cap_rate": str(recoupment_cap_rate),
            "minimum_adjustment": _money(minimum_adjustment),
            "appeal_state": appeal_state,
            "historical_payment_policy": str(
                policy.get(
                    "historical_payment_policy",
                    "append_only_forward_adjustment_no_rewrite",
                )
            ),
        },
        "previously_paid_rows": paid_rows,
        "corrected_entitlement_rows": entitlement_rows,
        "creator_delta_rows": [
            {
                "recipient_creator_id": creator_id,
                "previously_paid_total": _money(paid_totals.get(creator_id, "0")),
                "corrected_entitlement_total": _money(
                    corrected_totals.get(creator_id, "0")
                ),
                "delta_amount": _money(deltas[creator_id]),
            }
            for creator_id in creators
        ],
        "escrow_rows": escrow_rows,
        "future_payable_rows": future_payable_rows,
        "top_up_rows": top_up_rows,
        "recoupment_rows": recoupment_rows,
        "future_netting_rows": future_netting_rows,
        "adjustment_freeze_rows": freeze_rows,
        "creator_adjustment_receipts": creator_adjustment_receipts,
        "accounting": {
            "previously_paid_total": _money(paid_total),
            "corrected_entitlement_total": _money(corrected_total),
            "underpayment_total": _money(underpayment_total),
            "overpayment_total": _money(overpayment_total),
            "top_up_total": _money(top_up_total),
            "recoupment_total": _money(recoupment_total),
            "future_netting_total": _money(netting_total),
            "frozen_total": _money(frozen_total),
            "escrow_available_total": _money(escrow_total),
            "net_corrected_delta": _money(net_delta),
            "net_forward_adjustment": _money(net_adjustment),
        },
        "checks": checks,
        "privacy": {
            "raw_prompt_disclosed": False,
            "raw_output_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_payment_details_disclosed": False,
            "public_report_uses_hash_commitments": True,
        },
        "schemas": {
            "post_adjudication_settlement_adjustment_report": (
                POST_ADJUDICATION_SETTLEMENT_ADJUSTMENT_SCHEMA
            )
        },
        "summary": {
            "status": status,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "adjustment_case_id": str(
                adjustment_input.get("adjustment_case_id", adjustment_input.get("case_id", ""))
            ),
            "basis_case_id": basis["basis_case_id"],
            "adjusted_creator_count": sum(
                1 for delta in deltas.values() if abs(delta) >= minimum_adjustment
            ),
            "top_up_count": len(top_up_rows),
            "recoupment_count": len(recoupment_rows),
            "future_netting_count": len(future_netting_rows),
            "freeze_count": len(freeze_rows),
            "creator_adjustment_receipt_count": len(creator_adjustment_receipts),
            "appeal_state": appeal_state,
            "previously_paid_total": _money(paid_total),
            "corrected_entitlement_total": _money(corrected_total),
            "underpayment_total": _money(underpayment_total),
            "overpayment_total": _money(overpayment_total),
            "top_up_total": _money(top_up_total),
            "recoupment_total": _money(recoupment_total),
            "frozen_total": _money(frozen_total),
            "creator_adjustment_conserved": checks["adjustment_totals_conserved"],
        },
    }
    if _contains_private_fields(report):
        report["checks"]["private_text_not_disclosed"] = False
        report["summary"]["status"] = "needs_review"
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


def validate_post_adjudication_settlement_adjustment_report_shape(
    report: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = (
        "version",
        "case",
        "policy",
        "previously_paid_rows",
        "corrected_entitlement_rows",
        "creator_delta_rows",
        "escrow_rows",
        "future_payable_rows",
        "top_up_rows",
        "recoupment_rows",
        "future_netting_rows",
        "adjustment_freeze_rows",
        "creator_adjustment_receipts",
        "accounting",
        "checks",
        "privacy",
        "schemas",
        "summary",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing post-adjudication adjustment report field: {key}")
    if report.get("version") != POST_ADJUDICATION_SETTLEMENT_ADJUSTMENT_VERSION:
        errors.append("post-adjudication adjustment report version is unsupported")
    if "post_adjudication_settlement_adjustment_report" not in report.get("schemas", {}):
        errors.append("missing post-adjudication settlement adjustment report schema")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("post-adjudication adjustment target level is incorrect")
    return errors


def verify_post_adjudication_settlement_adjustment_report(
    report: dict[str, Any],
    adjustment_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a settlement adjustment report against private correction evidence."""

    errors = validate_post_adjudication_settlement_adjustment_report_shape(report)
    if hash_payload(_hashable_report(report)) != report.get("report_hash", ""):
        errors.append("post-adjudication adjustment report hash is not reproducible")
    expected = make_post_adjudication_settlement_adjustment_report(
        adjustment_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("issued_at"),
        signing_secret=signing_secret,
    )
    comparable_keys = (
        "case",
        "policy",
        "previously_paid_rows",
        "corrected_entitlement_rows",
        "creator_delta_rows",
        "escrow_rows",
        "future_payable_rows",
        "top_up_rows",
        "recoupment_rows",
        "future_netting_rows",
        "adjustment_freeze_rows",
        "creator_adjustment_receipts",
        "accounting",
        "checks",
        "privacy",
        "schemas",
        "summary",
    )
    for key in comparable_keys:
        if report.get(key) != expected.get(key):
            errors.append(f"post-adjudication adjustment report {key} does not match evidence")
    if report.get("report_hash") != expected.get("report_hash"):
        errors.append("post-adjudication adjustment report hash does not match evidence")
    if report.get("summary", {}).get("status") not in {"ready", "appeal_pending"}:
        errors.append("post-adjudication adjustment report status is not correction-safe")
    for check, passed in report.get("checks", {}).items():
        if not passed:
            errors.append(f"post-adjudication adjustment check failed: {check}")
    if _contains_private_fields(report) or any(
        private and private in canonical_json(report)
        for private in adjustment_input.get("private_strings", [])
    ):
        errors.append("post-adjudication adjustment report discloses private text")
    if signing_secret:
        signature = report.get("signature", {})
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("post-adjudication adjustment report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("post-adjudication adjustment report signature is invalid")
    return errors
