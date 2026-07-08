"""Cross-provider clearinghouse reports for RDLLM royalty settlement."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload

CLEARINGHOUSE_REPORT_VERSION = "rdllm-clearinghouse-report/v1"
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
}


def _decimal(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value))


def _money(value: Decimal | str | int | float) -> str:
    return str(_decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


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
            "statement_hash",
            "report_hash",
            "signature",
        }
    }


def _declared_hash(artifact: dict[str, Any]) -> str:
    for field in ("statement_hash", "report_hash"):
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(artifact)


def _artifact_hash_is_reproducible(artifact: dict[str, Any]) -> bool:
    declared = _declared_hash(artifact)
    if artifact.get("statement_hash") or artifact.get("report_hash"):
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


def _recipient_kind(creator_id: str, chunk_id: str = "") -> str:
    if creator_id.endswith("_escrow") or chunk_id.startswith("escrow:"):
        return "escrow"
    return "creator"


def _statement_provider_id(statement: dict[str, Any], index: int) -> str:
    return str(statement.get("provider", {}).get("id") or statement.get("issuer") or f"statement:{index}")


def _transitive_provider_id(report: dict[str, Any], index: int) -> str:
    return str(
        report.get("downstream", {}).get("provider_id")
        or report.get("issuer")
        or f"transitive:{index}"
    )


def _statement_artifact_row(statement: dict[str, Any], index: int) -> dict[str, Any]:
    event_hashes = [
        str(row.get("event_hash", ""))
        for row in statement.get("event_rollups", [])
        if row.get("event_hash")
    ]
    event_ids = [
        str(row.get("event_id", ""))
        for row in statement.get("event_rollups", [])
        if row.get("event_id")
    ]
    row = {
        "artifact_index": index,
        "artifact_ref": f"statement:{index}",
        "artifact_type": "royalty_statement",
        "provider_id": _statement_provider_id(statement, index),
        "issuer": str(statement.get("issuer", "")),
        "declared_hash": _declared_hash(statement),
        "artifact_hash_reproducible": _artifact_hash_is_reproducible(statement),
        "period_start": str(statement.get("period", {}).get("start", "")),
        "period_end": str(statement.get("period", {}).get("end", "")),
        "event_count": len(event_hashes),
        "event_root": hash_payload(event_hashes),
        "event_ids_root": hash_payload(event_ids),
        "payout_total": _money(statement.get("summary", {}).get("payout_total", "0")),
    }
    row["artifact_row_hash"] = hash_payload(row)
    return row


def _transitive_artifact_row(report: dict[str, Any], index: int) -> dict[str, Any]:
    row = {
        "artifact_index": index,
        "artifact_ref": f"transitive:{index}",
        "artifact_type": "transitive_attribution_report",
        "provider_id": _transitive_provider_id(report, index),
        "issuer": str(report.get("issuer", "")),
        "declared_hash": _declared_hash(report),
        "artifact_hash_reproducible": _artifact_hash_is_reproducible(report),
        "upstream_capsule_hash": str(report.get("upstream", {}).get("capsule_hash", "")),
        "downstream_event_hash": str(report.get("downstream", {}).get("event_hash", "")),
        "status": str(report.get("summary", {}).get("status", "")),
        "obligation_count": len(report.get("settlement_obligations", [])),
        "transitive_pool": _money(report.get("summary", {}).get("transitive_pool", "0")),
    }
    row["artifact_row_hash"] = hash_payload(row)
    return row


def _statement_obligations(
    statement: dict[str, Any],
    *,
    artifact_row: dict[str, Any],
    duplicate_artifact_refs: set[str],
    overlap_artifact_refs: set[str],
    settlement_currency: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    origin_hash = artifact_row["declared_hash"]
    event_hashes = [
        str(row.get("event_hash", ""))
        for row in statement.get("event_rollups", [])
        if row.get("event_hash")
    ]
    event_ids = [
        str(row.get("event_id", ""))
        for row in statement.get("event_rollups", [])
        if row.get("event_id")
    ]
    for index, source in enumerate(statement.get("source_usage", []), start=1):
        creator_id = str(source.get("creator_id", ""))
        chunk_id = str(source.get("chunk_id", ""))
        kind = _recipient_kind(creator_id, chunk_id)
        payout = _money(source.get("total_payout", "0"))
        row = {
            "origin_type": "royalty_statement",
            "origin_artifact_ref": artifact_row["artifact_ref"],
            "origin_hash": origin_hash,
            "origin_provider_id": artifact_row["provider_id"],
            "origin_row_index": index,
            "origin_row_hash": hash_payload(source),
            "event_hash_root": hash_payload(event_hashes),
            "event_ids_root": hash_payload(event_ids),
            "recipient_creator_id": creator_id,
            "recipient_creator_name": "",
            "recipient_kind": kind,
            "work_id": str(source.get("work_id", "")),
            "chunk_id": chunk_id,
            "content_hash": str(source.get("content_hash", "")),
            "basis": "provider_aggregate_royalty_statement",
            "currency": settlement_currency,
            "payout": payout,
            "source_access_count": int(source.get("source_access_count", 0) or 0),
            "visible_source_count": int(source.get("visible_source_count", 0) or 0),
            "supported_claim_count": int(source.get("supported_claim_count", 0) or 0),
            "settlement_status": "payable" if kind == "creator" else "escrow",
            "duplicate_of": "",
            "hold_reason": "",
        }
        if artifact_row["artifact_ref"] in duplicate_artifact_refs:
            row["settlement_status"] = "held_duplicate"
            row["hold_reason"] = "duplicate_statement_submission"
        elif artifact_row["artifact_ref"] in overlap_artifact_refs:
            row["settlement_status"] = "held_overlap_review"
            row["hold_reason"] = "statement_event_hash_overlap"
        row["obligation_key"] = hash_payload(
            {
                "origin_type": row["origin_type"],
                "origin_hash": origin_hash,
                "origin_row_hash": row["origin_row_hash"],
                "recipient_creator_id": creator_id,
                "work_id": row["work_id"],
                "chunk_id": chunk_id,
                "payout": payout,
            }
        )
        row["normalized_obligation_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _transitive_obligations(
    report: dict[str, Any],
    *,
    artifact_row: dict[str, Any],
    duplicate_artifact_refs: set[str],
    duplicate_obligation_refs: set[str],
    settlement_currency: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    origin_hash = artifact_row["declared_hash"]
    for index, obligation in enumerate(report.get("settlement_obligations", []), start=1):
        creator_id = str(obligation.get("recipient_creator_id", ""))
        chunk_id = str(obligation.get("chunk_id", ""))
        kind = _recipient_kind(creator_id, chunk_id)
        payout = _money(obligation.get("payout", "0"))
        transitive_key = hash_payload(
            {
                "downstream_event_hash": obligation.get("downstream_event_hash", ""),
                "upstream_capsule_hash": obligation.get("upstream_capsule_hash", ""),
                "obligation_hash": obligation.get("obligation_hash", ""),
                "recipient_creator_id": creator_id,
                "work_id": obligation.get("work_id", ""),
                "chunk_id": chunk_id,
            }
        )
        row = {
            "origin_type": "transitive_attribution_report",
            "origin_artifact_ref": artifact_row["artifact_ref"],
            "origin_hash": origin_hash,
            "origin_provider_id": artifact_row["provider_id"],
            "origin_row_index": index,
            "origin_row_hash": str(obligation.get("obligation_hash", hash_payload(obligation))),
            "downstream_event_hash": str(obligation.get("downstream_event_hash", "")),
            "upstream_capsule_hash": str(obligation.get("upstream_capsule_hash", "")),
            "recipient_creator_id": creator_id,
            "recipient_creator_name": str(obligation.get("recipient_creator_name", "")),
            "recipient_kind": kind,
            "work_id": str(obligation.get("work_id", "")),
            "chunk_id": chunk_id,
            "content_hash": "",
            "basis": str(obligation.get("basis", "copied_output_transitive_obligation")),
            "currency": settlement_currency,
            "payout": payout,
            "share_of_transitive_pool": str(obligation.get("share_of_transitive_pool", "")),
            "settlement_status": "payable" if kind == "creator" else "escrow",
            "duplicate_of": "",
            "hold_reason": "",
        }
        row_ref = f"{artifact_row['artifact_ref']}:{index}"
        if artifact_row["artifact_ref"] in duplicate_artifact_refs:
            row["settlement_status"] = "held_duplicate"
            row["hold_reason"] = "duplicate_transitive_report_submission"
        elif row_ref in duplicate_obligation_refs:
            row["settlement_status"] = "held_duplicate"
            row["hold_reason"] = "duplicate_transitive_obligation"
        row["obligation_key"] = hash_payload(
            {
                "origin_type": row["origin_type"],
                "origin_hash": origin_hash,
                "origin_row_hash": row["origin_row_hash"],
                "transitive_key": transitive_key,
                "recipient_creator_id": creator_id,
                "work_id": row["work_id"],
                "chunk_id": chunk_id,
                "payout": payout,
            }
        )
        row["normalized_obligation_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _duplicate_and_overlap_sets(
    statements: list[dict[str, Any]],
    transitive_reports: list[dict[str, Any]],
) -> tuple[set[str], set[str], set[str], list[dict[str, Any]]]:
    duplicate_artifact_refs: set[str] = set()
    overlap_artifact_refs: set[str] = set()
    duplicate_obligation_refs: set[str] = set()
    duplicate_rows: list[dict[str, Any]] = []

    seen_origin_hashes: dict[tuple[str, str], str] = {}
    seen_statement_events: dict[str, str] = {}
    for index, statement in enumerate(statements, start=1):
        artifact_ref = f"statement:{index}"
        origin_hash = _declared_hash(statement)
        origin_key = ("royalty_statement", origin_hash)
        if origin_key in seen_origin_hashes:
            duplicate_artifact_refs.add(artifact_ref)
            duplicate_rows.append(
                {
                    "duplicate_type": "duplicate_statement_submission",
                    "origin_hash": origin_hash,
                    "duplicate_of": seen_origin_hashes[origin_key],
                    "artifact_index": index,
                }
            )
        else:
            seen_origin_hashes[origin_key] = artifact_ref
        for event in statement.get("event_rollups", []):
            event_hash = str(event.get("event_hash", ""))
            if not event_hash:
                continue
            if event_hash in seen_statement_events and seen_statement_events[event_hash] != origin_hash:
                overlap_artifact_refs.add(artifact_ref)
                duplicate_rows.append(
                    {
                        "duplicate_type": "statement_event_hash_overlap",
                        "origin_hash": origin_hash,
                        "duplicate_of": seen_statement_events[event_hash],
                        "event_hash": event_hash,
                        "artifact_index": index,
                    }
                )
            else:
                seen_statement_events[event_hash] = origin_hash

    seen_transitive_keys: dict[str, str] = {}
    for index, report in enumerate(transitive_reports, start=1):
        artifact_ref = f"transitive:{index}"
        origin_hash = _declared_hash(report)
        origin_key = ("transitive_attribution_report", origin_hash)
        if origin_key in seen_origin_hashes:
            duplicate_artifact_refs.add(artifact_ref)
            duplicate_rows.append(
                {
                    "duplicate_type": "duplicate_transitive_report_submission",
                    "origin_hash": origin_hash,
                    "duplicate_of": seen_origin_hashes[origin_key],
                    "artifact_index": index,
                }
            )
        else:
            seen_origin_hashes[origin_key] = artifact_ref
        for obligation_index, obligation in enumerate(report.get("settlement_obligations", []), start=1):
            key = hash_payload(
                {
                    "downstream_event_hash": obligation.get("downstream_event_hash", ""),
                    "upstream_capsule_hash": obligation.get("upstream_capsule_hash", ""),
                    "obligation_hash": obligation.get("obligation_hash", ""),
                    "recipient_creator_id": obligation.get("recipient_creator_id", ""),
                    "work_id": obligation.get("work_id", ""),
                    "chunk_id": obligation.get("chunk_id", ""),
                }
            )
            if key in seen_transitive_keys:
                duplicate_obligation_refs.add(f"{artifact_ref}:{obligation_index}")
                duplicate_rows.append(
                    {
                        "duplicate_type": "duplicate_transitive_obligation",
                        "origin_hash": origin_hash,
                        "duplicate_of": seen_transitive_keys[key],
                        "obligation_key": key,
                        "artifact_index": index,
                    }
                )
            else:
                seen_transitive_keys[key] = origin_hash

    return (
        duplicate_artifact_refs,
        overlap_artifact_refs,
        duplicate_obligation_refs,
        _sort_rows(duplicate_rows, "duplicate_type", "origin_hash", "artifact_index"),
    )


def _aggregate_settlement_rows(rows: list[dict[str, Any]], *, status: str) -> list[dict[str, Any]]:
    totals: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        if row.get("settlement_status") != status:
            continue
        key = (
            str(row.get("recipient_creator_id", "")),
            str(row.get("recipient_kind", "")),
            str(row.get("work_id", "")),
            str(row.get("currency", "USD")),
        )
        total = totals.setdefault(
            key,
            {
                "recipient_creator_id": key[0],
                "recipient_kind": key[1],
                "work_id": key[2],
                "currency": key[3],
                "total_payout": Decimal("0"),
                "obligation_count": 0,
                "origin_hashes": set(),
                "chunk_ids": set(),
            },
        )
        total["total_payout"] += _decimal(row.get("payout", "0"))
        total["obligation_count"] += 1
        total["origin_hashes"].add(row.get("origin_hash", ""))
        if row.get("chunk_id"):
            total["chunk_ids"].add(row["chunk_id"])
    aggregate_rows: list[dict[str, Any]] = []
    for total in totals.values():
        aggregate = {
            "recipient_creator_id": total["recipient_creator_id"],
            "recipient_kind": total["recipient_kind"],
            "work_id": total["work_id"],
            "currency": total["currency"],
            "total_payout": _money(total["total_payout"]),
            "obligation_count": total["obligation_count"],
            "origin_hashes": sorted(total["origin_hashes"]),
            "chunk_ids": sorted(total["chunk_ids"]),
        }
        aggregate["settlement_row_hash"] = hash_payload(aggregate)
        aggregate_rows.append(aggregate)
    return _sort_rows(aggregate_rows, "recipient_creator_id", "work_id", "currency")


def _sum_status(rows: list[dict[str, Any]], status: str) -> Decimal:
    return sum(
        (_decimal(row.get("payout", "0")) for row in rows if row.get("settlement_status") == status),
        Decimal("0"),
    ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def make_clearinghouse_report(
    *,
    royalty_statements: list[dict[str, Any]] | None = None,
    transitive_reports: list[dict[str, Any]] | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    settlement_currency: str = "USD",
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a neutral clearing report across provider statements and transitive reports."""

    statements = royalty_statements or []
    transitives = transitive_reports or []
    statement_rows = [
        _statement_artifact_row(statement, index)
        for index, statement in enumerate(statements, start=1)
    ]
    transitive_rows = [
        _transitive_artifact_row(report, index)
        for index, report in enumerate(transitives, start=1)
    ]
    (
        duplicate_artifact_refs,
        overlap_artifact_refs,
        duplicate_obligation_refs,
        duplicate_rows,
    ) = _duplicate_and_overlap_sets(statements, transitives)
    obligations: list[dict[str, Any]] = []
    for statement, artifact_row in zip(statements, statement_rows):
        obligations.extend(
            _statement_obligations(
                statement,
                artifact_row=artifact_row,
                duplicate_artifact_refs=duplicate_artifact_refs,
                overlap_artifact_refs=overlap_artifact_refs,
                settlement_currency=settlement_currency,
            )
        )
    for report, artifact_row in zip(transitives, transitive_rows):
        obligations.extend(
            _transitive_obligations(
                report,
                artifact_row=artifact_row,
                duplicate_artifact_refs=duplicate_artifact_refs,
                duplicate_obligation_refs=duplicate_obligation_refs,
                settlement_currency=settlement_currency,
            )
        )
    obligations = _sort_rows(
        obligations,
        "settlement_status",
        "recipient_creator_id",
        "work_id",
        "chunk_id",
        "origin_hash",
        "origin_row_index",
    )
    payable_rows = _aggregate_settlement_rows(obligations, status="payable")
    escrow_rows = _aggregate_settlement_rows(obligations, status="escrow")
    held_rows = [
        row
        for row in obligations
        if str(row.get("settlement_status", "")).startswith("held_")
    ]
    status_counts: defaultdict[str, int] = defaultdict(int)
    for row in obligations:
        status_counts[str(row.get("settlement_status", ""))] += 1

    report_without_checks = {
        "input_artifact_rows": statement_rows + transitive_rows,
        "normalized_obligations": obligations,
        "payable_rows": payable_rows,
        "escrow_rows": escrow_rows,
        "held_rows": held_rows,
        "duplicate_rows": duplicate_rows,
    }
    payable_total = _sum_status(obligations, "payable")
    escrow_total = _sum_status(obligations, "escrow")
    held_total = sum(
        (
            _decimal(row.get("payout", "0"))
            for row in obligations
            if str(row.get("settlement_status", "")).startswith("held_")
        ),
        Decimal("0"),
    ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    gross_obligation_total = sum(
        (_decimal(row.get("payout", "0")) for row in obligations),
        Decimal("0"),
    ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    settled_total = (payable_total + escrow_total + held_total).quantize(
        MONEY_QUANT,
        rounding=ROUND_HALF_UP,
    )
    payable_row_total = sum(
        (_decimal(row.get("total_payout", "0")) for row in payable_rows),
        Decimal("0"),
    ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    escrow_row_total = sum(
        (_decimal(row.get("total_payout", "0")) for row in escrow_rows),
        Decimal("0"),
    ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    checks = {
        "input_artifact_hashes_reproducible": all(
            row["artifact_hash_reproducible"]
            for row in statement_rows + transitive_rows
        ),
        "transitive_reports_ready": all(
            row.get("status") == "ready" for row in transitive_rows
        ),
        "duplicates_are_held_not_paid": all(
            row.get("settlement_status", "").startswith("held_")
            for row in held_rows
        ),
        "no_duplicate_obligations_paid_twice": not any(
            row.get("settlement_status") == "payable"
            and (
                row.get("origin_artifact_ref") in duplicate_artifact_refs
                or row.get("origin_artifact_ref") in overlap_artifact_refs
            )
            for row in obligations
        ),
        "payable_rows_conserve_payable_obligations": payable_total == payable_row_total,
        "escrow_rows_conserve_escrow_obligations": escrow_total == escrow_row_total,
        "all_obligations_accounted_for": gross_obligation_total == settled_total,
        "no_private_text_disclosed": True,
    }
    report = {
        "report_version": CLEARINGHOUSE_REPORT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "settlement_policy": {
            "profile": "rdllm-cross-provider-clearing/v1",
            "settlement_currency": settlement_currency,
            "input_artifacts": [
                "rdllm-royalty-statement/v1",
                "rdllm-transitive-attribution-report/v1",
            ],
            "duplicate_policy": "pay_first_unique_origin_hold_repeated_or_overlapping_submissions",
            "escrow_policy": "route_unresolved_or_escrow_recipients_to_registry_escrow",
            "minimum_provider_certification_level": "RDLLM-L42",
            "clearinghouse_target_level": "RDLLM-L43",
        },
        **report_without_checks,
        "checks": checks,
        "commitments": {
            "input_artifact_root": hash_payload(statement_rows + transitive_rows),
            "normalized_obligation_root": hash_payload(obligations),
            "payable_root": hash_payload(payable_rows),
            "escrow_root": hash_payload(escrow_rows),
            "held_root": hash_payload(held_rows),
            "duplicate_root": hash_payload(duplicate_rows),
            "policy_hash": hash_payload(
                {
                    "profile": "rdllm-cross-provider-clearing/v1",
                    "duplicate_policy": "pay_first_unique_origin_hold_repeated_or_overlapping_submissions",
                    "escrow_policy": "route_unresolved_or_escrow_recipients_to_registry_escrow",
                    "minimum_provider_certification_level": "RDLLM-L42",
                    "clearinghouse_target_level": "RDLLM-L43",
                }
            ),
        },
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": "RDLLM-L43",
            "statement_count": len(statement_rows),
            "transitive_report_count": len(transitive_rows),
            "input_artifact_count": len(statement_rows) + len(transitive_rows),
            "normalized_obligation_count": len(obligations),
            "payable_obligation_count": status_counts.get("payable", 0),
            "escrow_obligation_count": status_counts.get("escrow", 0),
            "held_obligation_count": len(held_rows),
            "duplicate_count": len(duplicate_rows),
            "payable_creator_count": len({row["recipient_creator_id"] for row in payable_rows}),
            "escrow_account_count": len({row["recipient_creator_id"] for row in escrow_rows}),
            "gross_obligation_total": _money(gross_obligation_total),
            "payable_total": _money(payable_total),
            "escrow_total": _money(escrow_total),
            "held_total": _money(held_total),
            "accounted_total": _money(settled_total),
            "settlement_currency": settlement_currency,
            "double_payment_prevented": checks["no_duplicate_obligations_paid_twice"],
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "copied_output_text_disclosed": False,
            "clearing_uses_hashes_totals_and_source_ids": True,
        },
    }
    private_paths = _contains_private_fields(report)
    if private_paths:
        report["checks"]["no_private_text_disclosed"] = False
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


def validate_clearinghouse_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "settlement_policy",
        "input_artifact_rows",
        "normalized_obligations",
        "payable_rows",
        "escrow_rows",
        "held_rows",
        "duplicate_rows",
        "checks",
        "commitments",
        "summary",
        "privacy",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing clearinghouse report field: {key}")
    if errors:
        return errors
    if report.get("report_version") != CLEARINGHOUSE_REPORT_VERSION:
        errors.append("clearinghouse report version is unsupported")
    for key in (
        "profile",
        "settlement_currency",
        "duplicate_policy",
        "minimum_provider_certification_level",
        "clearinghouse_target_level",
    ):
        if key not in report.get("settlement_policy", {}):
            errors.append(f"missing clearinghouse policy field: {key}")
    for key in (
        "input_artifact_root",
        "normalized_obligation_root",
        "payable_root",
        "escrow_root",
        "held_root",
        "duplicate_root",
        "policy_hash",
    ):
        if key not in report.get("commitments", {}):
            errors.append(f"missing clearinghouse commitment: {key}")
    for key in (
        "status",
        "target_certification_level",
        "normalized_obligation_count",
        "payable_total",
        "escrow_total",
        "held_total",
        "double_payment_prevented",
    ):
        if key not in report.get("summary", {}):
            errors.append(f"missing clearinghouse summary field: {key}")
    return errors


def verify_clearinghouse_report(
    report: dict[str, Any],
    *,
    royalty_statements: list[dict[str, Any]] | None = None,
    transitive_reports: list[dict[str, Any]] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a clearinghouse report against submitted public settlement artifacts."""

    errors = validate_clearinghouse_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("clearinghouse report hash is not reproducible")

    expected = make_clearinghouse_report(
        royalty_statements=royalty_statements,
        transitive_reports=transitive_reports,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        settlement_currency=report.get("settlement_policy", {}).get(
            "settlement_currency", "USD"
        ),
        signing_secret=signing_secret,
    )
    for key in (
        "settlement_policy",
        "input_artifact_rows",
        "normalized_obligations",
        "payable_rows",
        "escrow_rows",
        "held_rows",
        "duplicate_rows",
        "checks",
        "commitments",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"clearinghouse report {key} does not match submitted artifacts")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("clearinghouse report hash does not match submitted artifacts")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("clearinghouse report status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"clearinghouse check failed: {check}")
    if report.get("summary", {}).get("double_payment_prevented") is not True:
        errors.append("clearinghouse report does not prevent double payment")
    if report.get("privacy", {}).get("clearing_uses_hashes_totals_and_source_ids") is not True:
        errors.append("clearinghouse report must use hashes, totals, and source ids")
    private_paths = _contains_private_fields(report)
    if private_paths:
        errors.append(
            "clearinghouse report exposes private fields: "
            + ", ".join(sorted(private_paths))
        )

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("clearinghouse report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("clearinghouse report signature is invalid")

    return errors
