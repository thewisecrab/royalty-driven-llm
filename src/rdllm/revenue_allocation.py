"""Revenue-source allocation reports for RDLLM usage events."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from rdllm.models import UsageEvent
from rdllm.receipts import DEFAULT_ISSUER, hash_payload, now_iso, sign_payload

REVENUE_ALLOCATION_REPORT_VERSION = "rdllm-revenue-allocation-report/v1"
REVENUE_ALLOCATION_REPORT_SCHEMA = "docs/schemas/revenue_allocation_report.schema.json"
MONEY_QUANT = Decimal("0.000001")
WEIGHT_QUANT = Decimal("0.00000001")

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
    "billing_account",
    "billing_email",
    "invoice_number",
    "invoice_text",
    "invoice_pdf",
    "payment_method",
    "card_number",
    "bank_account",
    "routing_number",
    "iban",
    "swift_bic",
}

SUPPORTED_ALLOCATION_MODES = {
    "ledger_gross_revenue",
    "equal_event_split",
    "event_count",
    "request_count",
    "source_access_count",
    "visible_source_count",
    "supported_claim_count",
    "output_token_count",
    "total_token_count",
    "output_character_count",
    "subscription_usage",
    "ad_impression",
    "api_metered_tokens",
    "weighted_engagement",
}

BASIS_ALIASES = {
    "event_count": "equal_event_split",
    "request_count": "equal_event_split",
    "subscription_usage": "output_token_count",
    "ad_impression": "equal_event_split",
    "api_metered_tokens": "total_token_count",
    "weighted_engagement": "source_access_count",
}

SOURCE_HASH_FIELDS = (
    "account_id_hash",
    "customer_id_hash",
    "billing_account_hash",
    "invoice_hash",
    "billing_record_hash",
    "meter_event_root",
    "ad_campaign_hash",
    "subscription_pool_hash",
    "contract_hash",
    "marketplace_order_hash",
)


def _decimal(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value))


def _money(value: Decimal | str | int | float) -> Decimal:
    return _decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _money_str(value: Decimal | str | int | float) -> str:
    return str(_money(value))


def _weight_str(value: Decimal | str | int | float) -> str:
    return str(_decimal(value).quantize(WEIGHT_QUANT, rounding=ROUND_HALF_UP))


def _sum_money(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal("0")).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _sort_rows(rows: list[dict[str, Any]], *keys: str) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: tuple(str(row.get(key, "")) for key in keys))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _hashable_source(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "source_row_hash"}


def _hashable_event_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "allocation_row_hash"}


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


def _events_from_ledger(ledger_data: dict[str, Any]) -> list[UsageEvent]:
    return [
        UsageEvent.from_dict(item)
        for item in ledger_data.get("events", [])
    ]


def _receipt_rows(receipts: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for receipt in receipts or []:
        event = (
            receipt.get("payload", {}).get("event", {})
            if isinstance(receipt.get("payload"), dict)
            else {}
        )
        if not event and isinstance(receipt.get("event"), dict):
            event = receipt.get("event", {})
        row = {
            "event_id": str(event.get("event_id", "")),
            "event_hash": str(event.get("event_hash", "")),
            "receipt_hash": str(receipt.get("receipt_hash", "")),
        }
        rows.append(row)
    return _sort_rows(rows, "event_id", "receipt_hash")


def _event_metrics(event: UsageEvent) -> dict[str, int]:
    answer = event.answer_text or event.output
    prompt_tokens = len(event.prompt.split())
    output_tokens = len(answer.split())
    return {
        "request_count": 1,
        "event_count": 1,
        "source_access_count": len(event.source_accesses),
        "visible_source_count": len(event.source_references),
        "supported_claim_count": sum(
            1 for support in event.claim_support if support.supported
        ),
        "prompt_token_count": prompt_tokens,
        "output_token_count": output_tokens,
        "total_token_count": prompt_tokens + output_tokens,
        "output_character_count": len(answer),
    }


def _canonical_mode(mode: str) -> str:
    return BASIS_ALIASES.get(mode, mode)


def _event_weight(event: UsageEvent, mode: str) -> Decimal:
    canonical = _canonical_mode(mode)
    if canonical == "ledger_gross_revenue":
        return max(_money(event.gross_revenue), Decimal("0"))
    if canonical == "equal_event_split":
        return Decimal("1")
    metrics = _event_metrics(event)
    return Decimal(str(max(metrics.get(canonical, 0), 0)))


def _normalized_policy(
    allocation_policy: dict[str, Any] | None,
    *,
    currency: str,
) -> dict[str, Any]:
    policy = dict(allocation_policy or {})
    mode = str(
        policy.get("allocation_mode")
        or policy.get("allocation_basis")
        or "ledger_gross_revenue"
    )
    policy.setdefault("policy_id", f"revenue-allocation:{mode}")
    policy["allocation_mode"] = mode
    policy["canonical_basis"] = _canonical_mode(mode)
    policy.setdefault("currency", currency)
    policy.setdefault("rounding", str(MONEY_QUANT))
    policy.setdefault("event_order", "event_id_ascending")
    policy.setdefault("raw_customer_records_forbidden", True)
    policy.setdefault("requires_source_revenue_conservation", True)
    policy.setdefault("requires_ledger_event_gross_match", True)
    policy.setdefault("target_certification_level", "RDLLM-L46")
    return policy


def _normalize_revenue_sources(
    revenue_sources: list[dict[str, Any]],
    *,
    default_currency: str,
    default_basis: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, source in enumerate(revenue_sources, start=1):
        source_id = str(source.get("source_id") or source.get("id") or f"revenue:{index}")
        basis = str(
            source.get("allocation_basis")
            or source.get("basis")
            or default_basis
        )
        hashes = {
            field: str(source[field])
            for field in SOURCE_HASH_FIELDS
            if source.get(field)
        }
        row = {
            "source_id": source_id,
            "source_type": str(source.get("source_type") or source.get("type") or "usage_revenue_pool"),
            "period_start": str(source.get("period_start", "")),
            "period_end": str(source.get("period_end", "")),
            "currency": str(source.get("currency") or default_currency),
            "gross_revenue": _money_str(source.get("gross_revenue", "0")),
            "allocation_basis": basis,
            "source_hashes": dict(sorted(hashes.items())),
            "raw_account_disclosed": False,
            "invoice_text_disclosed": False,
            "raw_billing_record_disclosed": False,
        }
        if not row["source_hashes"]:
            row["source_hashes"] = {
                "source_record_hash": hash_payload(
                    {
                        "source_id": source_id,
                        "source_type": row["source_type"],
                        "period_start": row["period_start"],
                        "period_end": row["period_end"],
                        "currency": row["currency"],
                        "gross_revenue": row["gross_revenue"],
                        "allocation_basis": basis,
                    }
                )
            }
        row["source_row_hash"] = hash_payload(_hashable_source(row))
        rows.append(row)
    return _sort_rows(rows, "source_id", "source_type")


def _allocate_amount(
    amount: Decimal,
    weights: list[Decimal],
) -> list[Decimal]:
    if not weights:
        return []
    denominator = sum(weights, Decimal("0"))
    if denominator <= Decimal("0"):
        weights = [Decimal("1") for _weight in weights]
        denominator = Decimal(len(weights))
    allocations: list[Decimal] = []
    remaining = _money(amount)
    for index, weight in enumerate(weights):
        if index == len(weights) - 1:
            allocation = remaining
        else:
            allocation = _money(amount * weight / denominator)
            remaining = _money(remaining - allocation)
        allocations.append(allocation)
    return allocations


def _source_allocations(
    revenue_sources: list[dict[str, Any]],
    weights: list[Decimal],
) -> list[list[dict[str, Any]]]:
    allocations_by_event: list[list[dict[str, Any]]] = [
        [] for _weight in weights
    ]
    for source in revenue_sources:
        source_amount = _money(source["gross_revenue"])
        allocated = _allocate_amount(source_amount, weights)
        for index, amount in enumerate(allocated):
            allocations_by_event[index].append(
                {
                    "source_id": source["source_id"],
                    "source_type": source["source_type"],
                    "allocation_basis": source["allocation_basis"],
                    "currency": source["currency"],
                    "gross_revenue": _money_str(amount),
                    "source_row_hash": source["source_row_hash"],
                }
            )
    return allocations_by_event


def _event_allocation_rows(
    events: list[UsageEvent],
    *,
    revenue_sources: list[dict[str, Any]],
    allocation_policy: dict[str, Any],
    receipts: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    ordered = sorted(events, key=lambda event: event.event_id)
    mode = str(allocation_policy.get("allocation_mode", "ledger_gross_revenue"))
    weights = [_event_weight(event, mode) for event in ordered]
    receipt_by_event = {row["event_id"]: row for row in _receipt_rows(receipts)}
    allocations_by_event = _source_allocations(revenue_sources, weights)
    rows: list[dict[str, Any]] = []
    for event, weight, source_allocations in zip(ordered, weights, allocations_by_event):
        allocated_gross = _sum_money(
            [_money(row["gross_revenue"]) for row in source_allocations]
        )
        ledger_gross = _money(event.gross_revenue)
        creator_pool = _money(event.creator_pool)
        expected_creator_pool = _money(allocated_gross * event.creator_pool_rate)
        receipt = receipt_by_event.get(event.event_id, {})
        metrics = _event_metrics(event)
        row = {
            "event_id": event.event_id,
            "event_hash": event.event_hash,
            "receipt_hash": receipt.get("receipt_hash", ""),
            "receipt_event_hash": receipt.get("event_hash", ""),
            "allocation_basis": mode,
            "canonical_basis": allocation_policy.get("canonical_basis", _canonical_mode(mode)),
            "basis_weight": _weight_str(weight),
            "usage_metrics": metrics,
            "revenue_source_count": len(source_allocations),
            "revenue_source_ids": sorted(row["source_id"] for row in source_allocations),
            "source_allocations": _sort_rows(source_allocations, "source_id"),
            "allocated_gross_revenue": _money_str(allocated_gross),
            "ledger_gross_revenue": _money_str(ledger_gross),
            "gross_revenue_matches_ledger": allocated_gross == ledger_gross,
            "creator_pool_rate": str(event.creator_pool_rate),
            "expected_creator_pool": _money_str(expected_creator_pool),
            "ledger_creator_pool": _money_str(creator_pool),
            "creator_pool_matches_allocation": expected_creator_pool == creator_pool,
            "royalty_share_root": hash_payload(
                [share.to_dict() for share in event.royalty_shares]
            ),
        }
        row["allocation_row_hash"] = hash_payload(_hashable_event_row(row))
        rows.append(row)
    return _sort_rows(rows, "event_id")


def make_revenue_allocation_report(
    ledger_data: dict[str, Any],
    *,
    revenue_sources: list[dict[str, Any]],
    receipts: list[dict[str, Any]] | None = None,
    allocation_policy: dict[str, Any] | None = None,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed report that allocates monetized revenue into RDLLM events."""

    currency = str((revenue_sources[0] or {}).get("currency", "USD")) if revenue_sources else "USD"
    policy = _normalized_policy(allocation_policy, currency=currency)
    events = _events_from_ledger(ledger_data)
    source_rows = _normalize_revenue_sources(
        revenue_sources,
        default_currency=str(policy.get("currency", "USD")),
        default_basis=str(policy.get("allocation_mode", "ledger_gross_revenue")),
    )
    event_rows = _event_allocation_rows(
        events,
        revenue_sources=source_rows,
        allocation_policy=policy,
        receipts=receipts,
    )
    receipt_rows = _receipt_rows(receipts)
    source_total = _sum_money([_money(row["gross_revenue"]) for row in source_rows])
    allocated_total = _sum_money(
        [_money(row["allocated_gross_revenue"]) for row in event_rows]
    )
    ledger_total = _sum_money([_money(event.gross_revenue) for event in events])
    creator_pool_total = _sum_money([_money(event.creator_pool) for event in events])
    expected_creator_pool_total = _sum_money(
        [_money(row["expected_creator_pool"]) for row in event_rows]
    )
    event_ids = [row["event_id"] for row in event_rows]
    receipt_event_ids = {row["event_id"] for row in receipt_rows if row["event_id"]}
    event_hashes = {event.event_id: event.event_hash for event in events}
    unsupported_mode = str(policy.get("allocation_mode", "")) not in SUPPORTED_ALLOCATION_MODES
    private_input_paths = _contains_private_fields(revenue_sources)
    private_report_paths = _contains_private_fields(
        {
            "revenue_sources": source_rows,
            "event_allocation_rows": event_rows,
        }
    )
    checks = {
        "allocation_mode_supported": not unsupported_mode,
        "revenue_sources_present": bool(source_rows),
        "ledger_events_present": bool(event_rows),
        "single_currency_report": len({row["currency"] for row in source_rows}) <= 1,
        "revenue_source_rows_hash_bound": all(
            row.get("source_row_hash") == hash_payload(_hashable_source(row))
            for row in source_rows
        ),
        "source_revenue_conserved_to_event_allocations": source_total == allocated_total,
        "ledger_gross_revenue_matches_allocations": ledger_total == allocated_total
        and all(row["gross_revenue_matches_ledger"] for row in event_rows),
        "creator_pool_conserved_from_allocated_revenue": (
            creator_pool_total == expected_creator_pool_total
            and all(row["creator_pool_matches_allocation"] for row in event_rows)
        ),
        "no_duplicate_event_rows": len(event_ids) == len(set(event_ids)),
        "receipt_hashes_bind_events": not receipts
        or (
            set(event_ids).issubset(receipt_event_ids)
            and all(
                row.get("receipt_event_hash") == event_hashes.get(row["event_id"])
                for row in event_rows
            )
        ),
        "private_billing_fields_absent_from_input": not private_input_paths,
        "private_billing_fields_absent_from_report": not private_report_paths,
    }
    report = {
        "report_version": REVENUE_ALLOCATION_REPORT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "allocation_policy": policy,
        "revenue_sources": source_rows,
        "event_allocation_rows": event_rows,
        "receipt_rollups": receipt_rows,
        "checks": checks,
        "commitments": {
            "ledger_hash": hash_payload(ledger_data),
            "allocation_policy_hash": hash_payload(policy),
            "revenue_source_root": hash_payload(source_rows),
            "event_allocation_root": hash_payload(event_rows),
            "receipt_root": hash_payload(receipt_rows),
            "gross_revenue_total": _money_str(source_total),
            "allocated_gross_revenue_total": _money_str(allocated_total),
            "ledger_gross_revenue_total": _money_str(ledger_total),
            "creator_pool_total": _money_str(creator_pool_total),
        },
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": "RDLLM-L46",
            "revenue_source_count": len(source_rows),
            "event_count": len(event_rows),
            "receipt_count": len(receipt_rows),
            "allocation_mode": policy.get("allocation_mode", ""),
            "currency": policy.get("currency", "USD"),
            "gross_revenue_total": _money_str(source_total),
            "allocated_gross_revenue_total": _money_str(allocated_total),
            "ledger_gross_revenue_total": _money_str(ledger_total),
            "creator_pool_total": _money_str(creator_pool_total),
            "expected_creator_pool_total": _money_str(expected_creator_pool_total),
            "unallocated_revenue_total": _money_str(source_total - allocated_total),
            "private_input_field_paths": private_input_paths,
            "private_report_field_paths": private_report_paths,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "raw_customer_account_disclosed": False,
            "invoice_text_disclosed": False,
            "raw_billing_records_disclosed": False,
            "uses_account_invoice_and_meter_hashes": True,
            "event_rows_use_hashes_and_aggregate_metrics": True,
        },
        "schemas": {
            "revenue_allocation_report": REVENUE_ALLOCATION_REPORT_SCHEMA,
            "attribution_receipt": "docs/schemas/attribution_receipt.schema.json",
            "royalty_statement": "docs/schemas/royalty_statement.schema.json",
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


def validate_revenue_allocation_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "allocation_policy",
        "revenue_sources",
        "event_allocation_rows",
        "receipt_rollups",
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
            errors.append(f"missing revenue allocation report field: {key}")
    if errors:
        return errors
    if report.get("report_version") != REVENUE_ALLOCATION_REPORT_VERSION:
        errors.append("revenue allocation report version is unsupported")
    for key in (
        "source_revenue_conserved_to_event_allocations",
        "ledger_gross_revenue_matches_allocations",
        "creator_pool_conserved_from_allocated_revenue",
        "receipt_hashes_bind_events",
    ):
        if key not in report.get("checks", {}):
            errors.append(f"missing revenue allocation check: {key}")
    for key in (
        "ledger_hash",
        "allocation_policy_hash",
        "revenue_source_root",
        "event_allocation_root",
        "gross_revenue_total",
        "creator_pool_total",
    ):
        if key not in report.get("commitments", {}):
            errors.append(f"missing revenue allocation commitment: {key}")
    return errors


def verify_revenue_allocation_report(
    report: dict[str, Any],
    ledger_data: dict[str, Any],
    *,
    revenue_sources: list[dict[str, Any]],
    receipts: list[dict[str, Any]] | None = None,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a revenue allocation report against ledger, source pools, and receipts."""

    errors = validate_revenue_allocation_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("revenue allocation report hash is not reproducible")

    expected = make_revenue_allocation_report(
        ledger_data,
        revenue_sources=revenue_sources,
        receipts=receipts,
        allocation_policy=report.get("allocation_policy", {}),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "allocation_policy",
        "revenue_sources",
        "event_allocation_rows",
        "receipt_rollups",
        "checks",
        "commitments",
        "summary",
        "privacy",
        "schemas",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"revenue allocation {key} does not match recomputed inputs")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("revenue allocation report hash does not match recomputed inputs")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("revenue allocation report status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"revenue allocation check failed: {check}")

    private_paths = _contains_private_fields(report)
    if private_paths:
        errors.append(
            "revenue allocation report exposes private fields: "
            + ", ".join(sorted(private_paths))
        )

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("revenue allocation report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("revenue allocation report signature is invalid")

    return errors
