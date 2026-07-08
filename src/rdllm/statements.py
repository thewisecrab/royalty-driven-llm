"""Periodic royalty statements for aggregated RDLLM usage events."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from rdllm.models import UsageEvent
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload

STATEMENT_VERSION = "rdllm-royalty-statement/v1"
MONEY_QUANT = Decimal("0.000001")
PRIVATE_FIELD_NAMES = {
    "prompt",
    "output",
    "answer_text",
    "quote",
    "evidence_text",
    "matched_text",
}


def _money(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANT)


def _money_str(value: Decimal | str | int | float) -> str:
    return str(_money(value))


def _sum_money(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal("0")).quantize(MONEY_QUANT)


def _creator_kind(creator_id: str) -> str:
    if creator_id.endswith("_escrow"):
        return "escrow"
    return "creator"


def _sort_rows(rows: list[dict[str, Any]], *keys: str) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: tuple(str(row.get(key, "")) for key in keys))


def _receipt_rollups(receipts: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for receipt in receipts or []:
        payload = receipt.get("payload", {})
        event = payload.get("event", {})
        rows.append(
            {
                "event_id": event.get("event_id", ""),
                "event_hash": event.get("event_hash", ""),
                "receipt_hash": receipt.get("receipt_hash", ""),
                "source_access_trace_hash": payload.get("telemetry", {}).get(
                    "source_access_trace_hash", ""
                ),
                "source_reference_trace_hash": payload.get("telemetry", {}).get(
                    "source_reference_trace_hash", ""
                ),
                "claim_support_trace_hash": payload.get("telemetry", {}).get(
                    "claim_support_trace_hash", ""
                ),
            }
        )
    return _sort_rows(rows, "event_id", "receipt_hash")


def _trace_rollups(traces: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for trace in traces or []:
        summary = trace.get("summary", {})
        rows.append(
            {
                "event_id": trace.get("event_id", ""),
                "event_hash": trace.get("event_hash", ""),
                "trace_hash": trace.get("trace_hash", ""),
                "source_access_trace_hash": summary.get("source_access_trace_hash", ""),
                "source_reference_trace_hash": summary.get(
                    "source_reference_trace_hash", ""
                ),
                "claim_support_trace_hash": summary.get("claim_support_trace_hash", ""),
                "source_access_count": summary.get("source_access_count", 0),
                "visible_source_count": summary.get("visible_source_count", 0),
                "claim_count": summary.get("claim_count", 0),
            }
        )
    return _sort_rows(rows, "event_id", "trace_hash")


def _statement_payload(
    ledger_data: dict[str, Any],
    *,
    issuer: str,
    issued_at: str,
    period_start: str = "",
    period_end: str = "",
    receipts: list[dict[str, Any]] | None = None,
    traces: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    events = [UsageEvent.from_dict(item) for item in ledger_data.get("events", [])]
    receipt_rows = _receipt_rollups(receipts)
    trace_rows = _trace_rollups(traces)
    receipt_by_event = {row["event_id"]: row for row in receipt_rows}
    trace_by_event = {row["event_id"]: row for row in trace_rows}

    event_rows: list[dict[str, Any]] = []
    share_rows: list[dict[str, Any]] = []
    source_access_rows: list[dict[str, Any]] = []
    source_reference_rows: list[dict[str, Any]] = []
    claim_rows: list[dict[str, Any]] = []

    creator_totals: dict[str, dict[str, Any]] = {}
    work_totals: dict[tuple[str, str], dict[str, Any]] = {}
    source_totals: dict[tuple[str, str, str], dict[str, Any]] = {}

    for event in events:
        event_receipt = receipt_by_event.get(event.event_id, {})
        event_trace = trace_by_event.get(event.event_id, {})
        event_rows.append(
            {
                "event_id": event.event_id,
                "event_hash": event.event_hash,
                "receipt_hash": event_receipt.get("receipt_hash", ""),
                "trace_hash": event_trace.get("trace_hash", ""),
                "gross_revenue": _money_str(event.gross_revenue),
                "creator_pool": _money_str(event.creator_pool),
                "source_access_count": len(event.source_accesses),
                "visible_source_count": len(event.source_references),
                "supported_claim_count": sum(
                    1 for support in event.claim_support if support.supported
                ),
                "attribution_gap_verdict": event.attribution_gap.get("verdict", ""),
                "grounding_status": event.grounding_report.get("status", ""),
            }
        )

        for access in event.source_accesses:
            source_access_rows.append(
                {
                    "event_id": event.event_id,
                    "event_hash": event.event_hash,
                    "access_id": access.access_id,
                    "access_type": access.access_type,
                    "use": access.use,
                    "creator_id": access.creator_id,
                    "work_id": access.work_id,
                    "chunk_id": access.chunk_id,
                    "content_hash": access.content_hash,
                    "decision_status": access.decision_status,
                    "policy_allowed": access.policy_allowed,
                    "registry_allowed": access.registry_allowed,
                }
            )

        for source in event.source_references:
            source_reference_rows.append(
                {
                    "event_id": event.event_id,
                    "event_hash": event.event_hash,
                    "label": source.label,
                    "creator_id": source.creator_id,
                    "work_id": source.work_id,
                    "chunk_id": source.chunk_id,
                    "content_hash": source.content_hash,
                    "contribution_weight": str(source.contribution_weight),
                    "payout": _money_str(source.payout),
                    "evidence_span_hashes": list(source.evidence_span_hashes),
                }
            )
            source_key = (source.creator_id, source.work_id, source.chunk_id)
            source_total = source_totals.setdefault(
                source_key,
                {
                    "creator_id": source.creator_id,
                    "work_id": source.work_id,
                    "chunk_id": source.chunk_id,
                    "content_hash": source.content_hash,
                    "visible_source_count": 0,
                    "supported_claim_count": 0,
                    "source_access_count": 0,
                    "payout": Decimal("0"),
                },
            )
            source_total["visible_source_count"] += 1
            source_total["payout"] += _money(source.payout)

        for support in event.claim_support:
            if not support.supported:
                continue
            claim_rows.append(
                {
                    "event_id": event.event_id,
                    "event_hash": event.event_hash,
                    "claim_hash": hash_payload(support.claim),
                    "source_label": support.source_label,
                    "work_id": support.work_id,
                    "chunk_id": support.chunk_id,
                    "evidence_span_hash": support.evidence_span_hash,
                    "supported": support.supported,
                }
            )
            for source_total in source_totals.values():
                if (
                    source_total["work_id"] == support.work_id
                    and source_total["chunk_id"] == support.chunk_id
                ):
                    source_total["supported_claim_count"] += 1

        for access in event.source_accesses:
            source_key = (access.creator_id, access.work_id, access.chunk_id)
            source_total = source_totals.setdefault(
                source_key,
                {
                    "creator_id": access.creator_id,
                    "work_id": access.work_id,
                    "chunk_id": access.chunk_id,
                    "content_hash": access.content_hash,
                    "visible_source_count": 0,
                    "supported_claim_count": 0,
                    "source_access_count": 0,
                    "payout": Decimal("0"),
                },
            )
            source_total["source_access_count"] += 1

        for share in event.royalty_shares:
            share_row = {
                "event_id": event.event_id,
                "event_hash": event.event_hash,
                "creator_id": share.creator_id,
                "work_id": share.work_id,
                "chunk_id": share.chunk_id,
                "content_hash": share.content_hash,
                "contribution_weight": str(share.contribution_weight),
                "payout": _money_str(share.payout),
                "kind": _creator_kind(share.creator_id),
            }
            share_rows.append(share_row)

            creator_total = creator_totals.setdefault(
                share.creator_id,
                {
                    "creator_id": share.creator_id,
                    "kind": _creator_kind(share.creator_id),
                    "total_payout": Decimal("0"),
                    "event_ids": set(),
                    "work_ids": set(),
                    "chunk_ids": set(),
                    "source_access_count": 0,
                    "visible_source_count": 0,
                    "supported_claim_count": 0,
                },
            )
            creator_total["total_payout"] += _money(share.payout)
            creator_total["event_ids"].add(event.event_id)
            creator_total["work_ids"].add(share.work_id)
            creator_total["chunk_ids"].add(share.chunk_id)

            work_key = (share.creator_id, share.work_id)
            work_total = work_totals.setdefault(
                work_key,
                {
                    "creator_id": share.creator_id,
                    "work_id": share.work_id,
                    "total_payout": Decimal("0"),
                    "event_ids": set(),
                    "chunk_ids": set(),
                    "source_access_count": 0,
                    "visible_source_count": 0,
                    "supported_claim_count": 0,
                },
            )
            work_total["total_payout"] += _money(share.payout)
            work_total["event_ids"].add(event.event_id)
            work_total["chunk_ids"].add(share.chunk_id)

    for source in source_totals.values():
        creator_total = creator_totals.get(source["creator_id"])
        if creator_total:
            creator_total["source_access_count"] += source["source_access_count"]
            creator_total["visible_source_count"] += source["visible_source_count"]
            creator_total["supported_claim_count"] += source["supported_claim_count"]
        work_total = work_totals.get((source["creator_id"], source["work_id"]))
        if work_total:
            work_total["source_access_count"] += source["source_access_count"]
            work_total["visible_source_count"] += source["visible_source_count"]
            work_total["supported_claim_count"] += source["supported_claim_count"]

    work_rows: list[dict[str, Any]] = []
    for work in work_totals.values():
        work_rows.append(
            {
                "creator_id": work["creator_id"],
                "work_id": work["work_id"],
                "total_payout": _money_str(work["total_payout"]),
                "event_count": len(work["event_ids"]),
                "chunk_count": len(work["chunk_ids"]),
                "source_access_count": work["source_access_count"],
                "visible_source_count": work["visible_source_count"],
                "supported_claim_count": work["supported_claim_count"],
            }
        )
    work_rows = _sort_rows(work_rows, "creator_id", "work_id")

    source_usage_rows = [
        {
            "creator_id": source["creator_id"],
            "work_id": source["work_id"],
            "chunk_id": source["chunk_id"],
            "content_hash": source["content_hash"],
            "total_payout": _money_str(source["payout"]),
            "source_access_count": source["source_access_count"],
            "visible_source_count": source["visible_source_count"],
            "supported_claim_count": source["supported_claim_count"],
        }
        for source in source_totals.values()
    ]
    source_usage_rows = _sort_rows(source_usage_rows, "creator_id", "work_id", "chunk_id")

    creator_rows: list[dict[str, Any]] = []
    escrow_rows: list[dict[str, Any]] = []
    for creator in creator_totals.values():
        row = {
            "creator_id": creator["creator_id"],
            "kind": creator["kind"],
            "total_payout": _money_str(creator["total_payout"]),
            "event_count": len(creator["event_ids"]),
            "work_count": len(creator["work_ids"]),
            "chunk_count": len(creator["chunk_ids"]),
            "source_access_count": creator["source_access_count"],
            "visible_source_count": creator["visible_source_count"],
            "supported_claim_count": creator["supported_claim_count"],
            "work_statement_hash": hash_payload(
                [
                    work
                    for work in work_rows
                    if work["creator_id"] == creator["creator_id"]
                ]
            ),
        }
        if creator["kind"] == "escrow":
            escrow_rows.append(row)
        else:
            creator_rows.append(row)

    creator_rows = _sort_rows(creator_rows, "creator_id")
    escrow_rows = _sort_rows(escrow_rows, "creator_id")
    event_rows = _sort_rows(event_rows, "event_id")
    share_rows = _sort_rows(share_rows, "event_id", "creator_id", "work_id", "chunk_id")
    source_access_rows = _sort_rows(source_access_rows, "event_id", "access_id")
    source_reference_rows = _sort_rows(source_reference_rows, "event_id", "label")
    claim_rows = _sort_rows(claim_rows, "event_id", "claim_hash")

    direct_total = _sum_money(
        [Decimal(row["total_payout"]) for row in creator_rows]
    )
    escrow_total = _sum_money([Decimal(row["total_payout"]) for row in escrow_rows])
    total_creator_pool = _sum_money([event.creator_pool for event in events])
    total_payout = _sum_money([Decimal(row["payout"]) for row in share_rows])
    total_gross = _sum_money([event.gross_revenue for event in events])

    return {
        "statement_version": STATEMENT_VERSION,
        "issuer": issuer,
        "issued_at": issued_at,
        "period": {
            "start": period_start,
            "end": period_end,
        },
        "summary": {
            "event_count": len(events),
            "receipt_count": len(receipt_rows),
            "trace_count": len(trace_rows),
            "creator_count": len(creator_rows),
            "escrow_account_count": len(escrow_rows),
            "source_access_count": len(source_access_rows),
            "visible_source_count": len(source_reference_rows),
            "supported_claim_count": len(claim_rows),
            "gross_revenue_total": _money_str(total_gross),
            "creator_pool_total": _money_str(total_creator_pool),
            "payout_total": _money_str(total_payout),
            "direct_creator_total": _money_str(direct_total),
            "escrow_total": _money_str(escrow_total),
            "attribution_gap_event_count": sum(
                1
                for row in event_rows
                if row["attribution_gap_verdict"] not in {"", "closed"}
            ),
        },
        "commitments": {
            "ledger_hash": hash_payload(ledger_data),
            "event_root": hash_payload(event_rows),
            "share_root": hash_payload(share_rows),
            "creator_statement_root": hash_payload(creator_rows),
            "escrow_statement_root": hash_payload(escrow_rows),
            "work_statement_root": hash_payload(work_rows),
            "source_usage_root": hash_payload(source_usage_rows),
            "source_access_root": hash_payload(source_access_rows),
            "source_reference_root": hash_payload(source_reference_rows),
            "claim_support_root": hash_payload(claim_rows),
            "receipt_root": hash_payload(receipt_rows),
            "trace_root": hash_payload(trace_rows),
        },
        "event_rollups": event_rows,
        "creator_statements": creator_rows,
        "escrow_statements": escrow_rows,
        "work_statements": work_rows,
        "source_usage": source_usage_rows,
        "receipt_rollups": receipt_rows,
        "trace_rollups": trace_rows,
        "privacy": {
            "prompt_disclosed": False,
            "answer_disclosed": False,
            "source_quotes_disclosed": False,
            "evidence_text_disclosed": False,
            "matched_text_disclosed": False,
            "public_fields": [
                "event hashes",
                "receipt hashes",
                "trace hashes",
                "creator totals",
                "work totals",
                "source usage counts",
                "claim counts",
                "payout totals",
            ],
        },
    }


def _hashable_statement(statement: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in statement.items()
        if key not in {"statement_hash", "signature"}
    }


def make_royalty_statement(
    ledger_data: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    issued_at: str | None = None,
    period_start: str = "",
    period_end: str = "",
    receipts: list[dict[str, Any]] | None = None,
    traces: list[dict[str, Any]] | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a privacy-preserving aggregate royalty statement for a ledger."""

    statement = _statement_payload(
        ledger_data,
        issuer=issuer,
        issued_at=issued_at or now_iso(),
        period_start=period_start,
        period_end=period_end,
        receipts=receipts,
        traces=traces,
    )
    statement["statement_hash"] = hash_payload(_hashable_statement(statement))
    statement["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_statement(statement), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return statement


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


def validate_statement_shape(statement: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in (
        "statement_version",
        "issuer",
        "issued_at",
        "period",
        "summary",
        "commitments",
        "event_rollups",
        "creator_statements",
        "escrow_statements",
        "work_statements",
        "source_usage",
        "receipt_rollups",
        "trace_rollups",
        "privacy",
        "statement_hash",
        "signature",
    ):
        if key not in statement:
            errors.append(f"missing statement field: {key}")
    if errors:
        return errors
    if statement.get("statement_version") != STATEMENT_VERSION:
        errors.append("statement version is unsupported")
    for key in (
        "event_count",
        "receipt_count",
        "trace_count",
        "creator_pool_total",
        "payout_total",
        "direct_creator_total",
        "escrow_total",
    ):
        if key not in statement.get("summary", {}):
            errors.append(f"missing statement summary field: {key}")
    for key in (
        "ledger_hash",
        "event_root",
        "share_root",
        "creator_statement_root",
        "escrow_statement_root",
        "work_statement_root",
        "source_usage_root",
        "source_access_root",
        "source_reference_root",
        "claim_support_root",
        "receipt_root",
        "trace_root",
    ):
        if key not in statement.get("commitments", {}):
            errors.append(f"missing statement commitment: {key}")
    return errors


def verify_royalty_statement(
    ledger_data: dict[str, Any],
    statement: dict[str, Any],
    *,
    receipts: list[dict[str, Any]] | None = None,
    traces: list[dict[str, Any]] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify that a royalty statement is reproducible from a ledger."""

    errors = validate_statement_shape(statement)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_statement(statement))
    if expected_hash != statement.get("statement_hash"):
        errors.append("statement hash is not reproducible")

    expected = make_royalty_statement(
        ledger_data,
        issuer=statement.get("issuer", DEFAULT_ISSUER),
        issued_at=statement.get("issued_at", ""),
        period_start=statement.get("period", {}).get("start", ""),
        period_end=statement.get("period", {}).get("end", ""),
        receipts=receipts,
        traces=traces,
        signing_secret=signing_secret,
    )
    for key in (
        "summary",
        "commitments",
        "event_rollups",
        "creator_statements",
        "escrow_statements",
        "work_statements",
        "source_usage",
        "receipt_rollups",
        "trace_rollups",
        "privacy",
    ):
        if expected.get(key) != statement.get(key):
            errors.append(f"statement {key} does not match recomputed ledger rollup")
    if expected.get("statement_hash") != statement.get("statement_hash"):
        errors.append("statement hash does not match ledger rollup")

    private_paths = _contains_private_fields(statement)
    if private_paths:
        errors.append(
            "statement exposes private fields: " + ", ".join(sorted(private_paths))
        )

    summary = statement.get("summary", {})
    if summary.get("creator_pool_total") != summary.get("payout_total"):
        errors.append("statement payout total does not equal creator pool total")
    direct = Decimal(str(summary.get("direct_creator_total", "0")))
    escrow = Decimal(str(summary.get("escrow_total", "0")))
    payout_total = Decimal(str(summary.get("payout_total", "0")))
    if _money(direct + escrow) != _money(payout_total):
        errors.append("direct creator total plus escrow total does not equal payout total")

    event_hashes = {
        row.get("event_id", ""): row.get("event_hash", "")
        for row in statement.get("event_rollups", [])
    }
    for row in statement.get("receipt_rollups", []):
        event_id = row.get("event_id", "")
        if event_id not in event_hashes:
            errors.append(f"receipt rollup event {event_id} is not in statement events")
        elif row.get("event_hash") != event_hashes[event_id]:
            errors.append(f"receipt rollup event hash mismatch for {event_id}")
    for row in statement.get("trace_rollups", []):
        event_id = row.get("event_id", "")
        if event_id not in event_hashes:
            errors.append(f"trace rollup event {event_id} is not in statement events")
        elif row.get("event_hash") != event_hashes[event_id]:
            errors.append(f"trace rollup event hash mismatch for {event_id}")

    if signing_secret:
        signature = statement.get("signature", {})
        expected_signature = sign_payload(_hashable_statement(statement), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("statement is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("statement signature is invalid")

    return errors


def statement_summary(statement: dict[str, Any]) -> dict[str, Any]:
    """Return the compact fields useful for CLI and certification output."""

    return {
        "statement_hash": statement.get("statement_hash", ""),
        "summary": statement.get("summary", {}),
        "commitments": statement.get("commitments", {}),
    }
