"""Settlement clearing for universal multi-provider composition receipts.

L130 proves that a public answer was assembled from attested provider segments.
This L131 layer proves that the same segment weights deterministically clear into
payable, escrow, or held creator obligations without changing the source footer.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.transparency import merkle_root

UNIVERSAL_COMPOSITION_SETTLEMENT_VERSION = (
    "rdllm-universal-composition-settlement/v1"
)
UNIVERSAL_COMPOSITION_SETTLEMENT_SCHEMA = (
    "docs/schemas/universal_composition_settlement.schema.json"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L131"
MINIMUM_INPUT_LEVEL = "RDLLM-L130"
MONEY_QUANT = Decimal("0.000001")
WEIGHT_QUANT = Decimal("0.000001")

DECLARED_HASH_FIELDS = (
    "universal_composition_settlement_hash",
    "universal_composition_receipt_hash",
    "source_footer_delivery_hash",
    "envelope_hash",
    "report_hash",
    "card_hash",
    "manifest_hash",
    "profile_hash",
    "bundle_hash",
    "statement_hash",
    "receipt_hash",
)

PRIVATE_FIELD_NAMES = {
    "prompt",
    "prompt_text",
    "raw_prompt",
    "raw_model_output",
    "raw_native_response",
    "raw_composition_payload",
    "native_response_body",
    "output",
    "output_text",
    "raw_output",
    "answer_text",
    "source_text",
    "training_text",
    "document_text",
    "evidence_text",
    "matched_text",
    "quote",
    "reasoning",
    "chain_of_thought",
    "invoice_text",
    "billing_email",
    "customer_id",
    "customer_email",
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
}

RIGHTS_PAYABLE = {"active", "allowed", "licensed", "verified", "payable"}
RIGHTS_ESCROW = {"pending", "unknown", "unresolved", "escrow"}
RIGHTS_HELD = {"blocked", "disputed", "held", "revoked"}
SETTLEMENT_STATUSES = {"payable", "escrow", "held"}


def load_universal_composition_settlement_input(path: str | Path) -> dict[str, Any]:
    """Load private replay inputs for an L131 composition settlement receipt."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"universal_composition_settlement_hash", "signature"}
    }


def _hashable_artifact(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    return {
        key: value
        for key, value in artifact.items()
        if key not in set(DECLARED_HASH_FIELDS) | {"signature"}
    }


def _declared_hash(artifact: dict[str, Any] | None) -> str:
    if not artifact:
        return ""
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(_hashable_artifact(artifact))


def _artifact_hash_is_reproducible(artifact: dict[str, Any] | None) -> bool:
    if not artifact:
        return False
    declared = _declared_hash(artifact)
    return bool(declared) and declared == hash_payload(_hashable_artifact(artifact))


def _contains_private_fields(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key) in PRIVATE_FIELD_NAMES or _contains_private_fields(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_private_fields(child) for child in value)
    return False


def _private_strings_absent(
    report: dict[str, Any],
    settlement_input: dict[str, Any],
) -> bool:
    public_json = canonical_json(report)
    private_strings = [
        str(item)
        for item in settlement_input.get("private_strings", [])
        if str(item).strip()
    ]
    return all(item not in public_json for item in private_strings)


def _decimal(value: Any, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _money(value: Any) -> Decimal:
    return _decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _money_str(value: Any) -> str:
    return str(_money(value))


def _weight(value: Any) -> Decimal:
    return _decimal(value).quantize(WEIGHT_QUANT, rounding=ROUND_HALF_UP)


def _weight_str(value: Any) -> str:
    return str(_weight(value))


def _sum_money(rows: list[dict[str, Any]], field: str) -> Decimal:
    return sum((_money(row.get(field, "0")) for row in rows), Decimal("0")).quantize(
        MONEY_QUANT,
        rounding=ROUND_HALF_UP,
    )


def _allocate_amount(total: Decimal, weights: list[Decimal]) -> list[Decimal]:
    if not weights:
        return []
    amounts: list[Decimal] = []
    allocated = Decimal("0")
    for index, weight in enumerate(weights):
        if index == len(weights) - 1:
            amount = (total - allocated).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        else:
            amount = (total * weight).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            allocated += amount
        amounts.append(amount)
    return amounts


def _sort_rows(rows: list[dict[str, Any]], *keys: str) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: tuple(str(row.get(key, "")) for key in keys))


def _policy(settlement_input: dict[str, Any]) -> dict[str, Any]:
    policy = dict(settlement_input.get("settlement_policy", {}))
    currency = str(
        policy.get("currency")
        or policy.get("settlement_currency")
        or settlement_input.get("revenue_allocation_report", {})
        .get("summary", {})
        .get("currency", "USD")
    )
    return {
        "profile": "rdllm-universal-composition-settlement-policy/v1",
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "minimum_input_level": MINIMUM_INPUT_LEVEL,
        "currency": currency,
        "rounding": str(MONEY_QUANT),
        "creator_pool_rate": str(policy.get("creator_pool_rate", "")),
        "gross_revenue": str(policy.get("gross_revenue", "")),
        "creator_pool": str(policy.get("creator_pool", "")),
        "segment_weight_source": "l130_provider_weight",
        "source_entitlement_weight_source": "l131_source_entitlement_weight",
        "requires_l130_release": bool(policy.get("requires_l130_release", True)),
        "requires_revenue_conservation": bool(
            policy.get("requires_revenue_conservation", True)
        ),
        "requires_explicit_source_entitlements": bool(
            policy.get("requires_explicit_source_entitlements", True)
        ),
        "requires_source_footer_binding": bool(
            policy.get("requires_source_footer_binding", True)
        ),
        "on_missing_source_entitlement": "block_settlement",
        "on_unresolved_rights": "escrow",
        "on_disputed_rights": "hold",
        "on_pool_mismatch": "block_settlement",
        "raw_billing_records_disclosure_allowed": False,
        "raw_answer_text_disclosure_allowed": False,
    }


def _artifact_bindings(
    settlement_input: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    artifacts = {
        "universal_composition_receipt": settlement_input.get(
            "universal_composition_receipt"
        ),
        "revenue_allocation_report": settlement_input.get("revenue_allocation_report"),
        "clearinghouse_report": settlement_input.get("clearinghouse_report"),
    }
    bindings: dict[str, dict[str, Any]] = {}
    for name, artifact in artifacts.items():
        artifact_type = (
            (artifact or {}).get("composition_receipt_version")
            or (artifact or {}).get("report_version")
            or (artifact or {}).get("settlement_version")
            or ""
        )
        bindings[name] = {
            "present": bool(artifact),
            "declared_hash": _declared_hash(artifact),
            "hash_reproducible": _artifact_hash_is_reproducible(artifact),
            "artifact_type": str(artifact_type),
            "status": str((artifact or {}).get("summary", {}).get("status", "")),
            "target_certification_level": str(
                (artifact or {}).get("summary", {}).get("target_certification_level", "")
            ),
        }
    return bindings


def _revenue_binding(
    settlement_input: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    revenue_report = settlement_input.get("revenue_allocation_report", {})
    report_summary = revenue_report.get("summary", {})
    currency = str(report_summary.get("currency") or policy["currency"])
    gross = (
        policy["gross_revenue"]
        or report_summary.get("gross_revenue_total")
        or report_summary.get("allocated_gross_revenue_total")
        or "0"
    )
    creator_pool = (
        policy["creator_pool"] or report_summary.get("creator_pool_total") or "0"
    )
    creator_pool_rate = policy["creator_pool_rate"]
    if not creator_pool_rate:
        gross_decimal = _money(gross)
        creator_pool_decimal = _money(creator_pool)
        creator_pool_rate = (
            str((creator_pool_decimal / gross_decimal).quantize(WEIGHT_QUANT))
            if gross_decimal > Decimal("0")
            else "0"
        )
    expected_creator_pool = _money(_money(gross) * _decimal(creator_pool_rate))
    binding = {
        "currency": currency,
        "gross_revenue": _money_str(gross),
        "creator_pool_rate": str(creator_pool_rate),
        "creator_pool": _money_str(creator_pool),
        "expected_creator_pool": _money_str(expected_creator_pool),
        "revenue_allocation_report_hash": _declared_hash(revenue_report),
        "revenue_allocation_status": str(report_summary.get("status", "")),
        "revenue_allocation_target_level": str(
            report_summary.get("target_certification_level", "")
        ),
        "revenue_event_count": int(report_summary.get("event_count", 0) or 0),
        "revenue_source_count": int(report_summary.get("revenue_source_count", 0) or 0),
        "revenue_source_root": str(
            revenue_report.get("commitments", {}).get("revenue_source_root", "")
        ),
        "event_allocation_root": str(
            revenue_report.get("commitments", {}).get("event_allocation_root", "")
        ),
    }
    binding["revenue_binding_hash"] = hash_payload(binding)
    return binding


def _composition_binding(universal_receipt: dict[str, Any]) -> dict[str, Any]:
    composition_plan = universal_receipt.get("composition_plan", {})
    commitments = universal_receipt.get("commitments", {})
    segments = universal_receipt.get("provider_segments", [])
    binding = {
        "universal_composition_receipt_hash": str(
            universal_receipt.get("universal_composition_receipt_hash", "")
        ),
        "composition_id": str(composition_plan.get("composition_id", "")),
        "composition_status": str(universal_receipt.get("summary", {}).get("status", "")),
        "composition_target_level": str(
            universal_receipt.get("summary", {}).get("target_certification_level", "")
        ),
        "final_response_envelope_hash": str(
            commitments.get(
                "final_response_envelope_hash",
                composition_plan.get("final_response_envelope_hash", ""),
            )
        ),
        "source_footer_delivery_hash": str(
            commitments.get(
                "source_footer_delivery_hash",
                composition_plan.get("source_footer_delivery_hash", ""),
            )
        ),
        "provider_segment_root": str(
            commitments.get(
                "provider_segment_root",
                composition_plan.get("computed_segment_root", ""),
            )
        ),
        "deployment_attestation_root": str(
            commitments.get("deployment_attestation_root", "")
        ),
        "telemetry_span_root": str(commitments.get("telemetry_span_root", "")),
        "provider_segment_count": len(segments),
        "provider_families": sorted({str(row.get("provider_family", "")) for row in segments}),
        "segment_ids": [str(row.get("segment_id", "")) for row in segments],
    }
    binding["composition_binding_hash"] = hash_payload(binding)
    return binding


def _segment_rows(universal_receipt: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in universal_receipt.get("provider_segments", [])
    ]


def _provider_weights_conserve_unit(segment_rows: list[dict[str, Any]]) -> bool:
    try:
        weights = [_weight(row.get("provider_weight", "0")) for row in segment_rows]
    except (InvalidOperation, TypeError, ValueError):
        return False
    return bool(weights) and sum(weights, Decimal("0")) == Decimal("1.000000") and all(
        weight >= Decimal("0") for weight in weights
    )


def _provider_segment_settlement_rows(
    *,
    universal_receipt: dict[str, Any],
    revenue_binding: dict[str, Any],
) -> list[dict[str, Any]]:
    segments = _segment_rows(universal_receipt)
    creator_pool = _money(revenue_binding.get("creator_pool", "0"))
    weights = [_weight(segment.get("provider_weight", "0")) for segment in segments]
    amounts = _allocate_amount(creator_pool, weights)
    rows: list[dict[str, Any]] = []
    for index, (segment, amount) in enumerate(zip(segments, amounts), start=1):
        row = {
            "display_order": index,
            "settlement_row_type": "provider_segment_pool",
            "segment_id": str(segment.get("segment_id", "")),
            "segment_hash": str(segment.get("segment_hash", "")),
            "provider_id": str(segment.get("provider_id", "")),
            "provider_family": str(segment.get("provider_family", "")),
            "native_model": str(segment.get("native_model", "")),
            "deployment_id": str(segment.get("deployment_id", "")),
            "deployment_attestation_hash": str(
                segment.get("deployment_attestation_hash", "")
            ),
            "native_response_id": str(segment.get("native_response_id", "")),
            "response_envelope_hash": str(segment.get("response_envelope_hash", "")),
            "source_footer_delivery_hash": str(
                segment.get("source_footer_delivery_hash", "")
            ),
            "claim_ids": [str(item) for item in segment.get("claim_ids", [])],
            "source_labels": [str(item) for item in segment.get("source_labels", [])],
            "provider_weight": _weight_str(segment.get("provider_weight", "0")),
            "currency": str(revenue_binding.get("currency", "USD")),
            "creator_pool": _money_str(creator_pool),
            "segment_pool": _money_str(amount),
            "basis": "l130_provider_weight",
        }
        row["segment_settlement_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _derive_status(entitlement: dict[str, Any]) -> tuple[str, str, str]:
    rights_status = str(entitlement.get("rights_status", "licensed")).lower()
    recipient_kind = str(entitlement.get("recipient_kind", "")).lower()
    recipient_creator_id = str(entitlement.get("recipient_creator_id", ""))
    if not recipient_kind:
        recipient_kind = (
            "escrow"
            if recipient_creator_id.endswith("_escrow")
            or rights_status in RIGHTS_ESCROW
            else "creator"
        )
    declared = str(entitlement.get("settlement_status", "")).lower()
    if declared in SETTLEMENT_STATUSES:
        status = declared
    elif rights_status in RIGHTS_HELD:
        status = "held"
    elif rights_status in RIGHTS_ESCROW or recipient_kind == "escrow":
        status = "escrow"
    else:
        status = "payable"
    hold_reason = str(entitlement.get("hold_reason", ""))
    if status == "escrow" and not hold_reason:
        hold_reason = "unresolved_source_rights"
    if status == "held" and not hold_reason:
        hold_reason = "disputed_or_blocked_source_rights"
    return recipient_kind, rights_status, status if status else "escrow", hold_reason


def _source_entitlement_rows(
    settlement_input: dict[str, Any],
    segment_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    segments_by_id = {str(row.get("segment_id", "")): row for row in segment_rows}
    rows: list[dict[str, Any]] = []
    for index, entitlement in enumerate(
        settlement_input.get("source_entitlements", []),
        start=1,
    ):
        segment_id = str(entitlement.get("segment_id", ""))
        segment = segments_by_id.get(segment_id, {})
        recipient_kind, rights_status, status, hold_reason = _derive_status(entitlement)
        row = {
            "display_order": index,
            "segment_id": segment_id,
            "provider_id": str(
                entitlement.get("provider_id") or segment.get("provider_id", "")
            ),
            "provider_family": str(
                entitlement.get("provider_family") or segment.get("provider_family", "")
            ),
            "deployment_attestation_hash": str(
                entitlement.get("deployment_attestation_hash")
                or segment.get("deployment_attestation_hash", "")
            ),
            "source_label": str(entitlement.get("source_label", "")),
            "claim_id": str(entitlement.get("claim_id", "")),
            "recipient_creator_id": str(entitlement.get("recipient_creator_id", "")),
            "recipient_kind": recipient_kind,
            "work_id": str(entitlement.get("work_id", "")),
            "chunk_id": str(entitlement.get("chunk_id", "")),
            "content_hash": str(entitlement.get("content_hash", "")),
            "allocation_weight": _weight_str(entitlement.get("allocation_weight", "0")),
            "rights_status": rights_status,
            "settlement_status": status,
            "hold_reason": hold_reason,
            "basis": str(entitlement.get("basis", "segment_source_entitlement")),
        }
        row["source_entitlement_hash"] = hash_payload(row)
        rows.append(row)
    return _sort_rows(rows, "segment_id", "source_label", "claim_id", "recipient_creator_id")


def _creator_obligation_rows(
    *,
    composition_binding: dict[str, Any],
    revenue_binding: dict[str, Any],
    provider_segment_rows: list[dict[str, Any]],
    source_entitlement_rows: list[dict[str, Any]],
    clearinghouse_hash: str,
) -> list[dict[str, Any]]:
    entitlements_by_segment: dict[str, list[dict[str, Any]]] = {}
    for row in source_entitlement_rows:
        entitlements_by_segment.setdefault(str(row.get("segment_id", "")), []).append(row)
    obligations: list[dict[str, Any]] = []
    for segment_row in provider_segment_rows:
        entitlements = entitlements_by_segment.get(str(segment_row["segment_id"]), [])
        weights = [_weight(row.get("allocation_weight", "0")) for row in entitlements]
        payouts = _allocate_amount(_money(segment_row["segment_pool"]), weights)
        for index, (entitlement, payout) in enumerate(zip(entitlements, payouts), start=1):
            row = {
                "display_order": len(obligations) + 1,
                "settlement_row_type": "creator_obligation",
                "composition_id": composition_binding["composition_id"],
                "universal_composition_receipt_hash": composition_binding[
                    "universal_composition_receipt_hash"
                ],
                "revenue_allocation_report_hash": revenue_binding[
                    "revenue_allocation_report_hash"
                ],
                "clearinghouse_report_hash": clearinghouse_hash,
                "segment_settlement_row_hash": segment_row[
                    "segment_settlement_row_hash"
                ],
                "source_entitlement_hash": entitlement["source_entitlement_hash"],
                "segment_id": segment_row["segment_id"],
                "segment_hash": segment_row["segment_hash"],
                "provider_id": segment_row["provider_id"],
                "provider_family": segment_row["provider_family"],
                "deployment_attestation_hash": segment_row[
                    "deployment_attestation_hash"
                ],
                "source_label": entitlement["source_label"],
                "claim_id": entitlement["claim_id"],
                "recipient_creator_id": entitlement["recipient_creator_id"],
                "recipient_kind": entitlement["recipient_kind"],
                "work_id": entitlement["work_id"],
                "chunk_id": entitlement["chunk_id"],
                "content_hash": entitlement["content_hash"],
                "currency": revenue_binding["currency"],
                "segment_pool": segment_row["segment_pool"],
                "allocation_weight": entitlement["allocation_weight"],
                "payout": _money_str(payout),
                "settlement_status": entitlement["settlement_status"],
                "rights_status": entitlement["rights_status"],
                "hold_reason": entitlement["hold_reason"],
                "basis": "l131_composition_segment_source_settlement",
                "obligation_index_within_segment": index,
            }
            row["obligation_key"] = hash_payload(
                {
                    "composition": row["universal_composition_receipt_hash"],
                    "segment": row["segment_id"],
                    "source_label": row["source_label"],
                    "claim_id": row["claim_id"],
                    "recipient_creator_id": row["recipient_creator_id"],
                    "work_id": row["work_id"],
                    "chunk_id": row["chunk_id"],
                    "payout": row["payout"],
                }
            )
            row["creator_obligation_hash"] = hash_payload(row)
            obligations.append(row)
    return _sort_rows(
        obligations,
        "segment_id",
        "source_label",
        "claim_id",
        "recipient_creator_id",
        "work_id",
        "chunk_id",
    )


def _aggregate_recipient_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aggregates: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (
            str(row.get("settlement_status", "")),
            str(row.get("recipient_creator_id", "")),
            str(row.get("recipient_kind", "")),
            str(row.get("work_id", "")),
            str(row.get("currency", "USD")),
        )
        aggregate = aggregates.setdefault(
            key,
            {
                "settlement_status": key[0],
                "recipient_creator_id": key[1],
                "recipient_kind": key[2],
                "work_id": key[3],
                "currency": key[4],
                "total_payout": Decimal("0"),
                "obligation_count": 0,
                "segment_ids": set(),
                "source_labels": set(),
                "claim_ids": set(),
                "chunk_ids": set(),
            },
        )
        aggregate["total_payout"] += _money(row.get("payout", "0"))
        aggregate["obligation_count"] += 1
        for field, target in (
            ("segment_id", "segment_ids"),
            ("source_label", "source_labels"),
            ("claim_id", "claim_ids"),
            ("chunk_id", "chunk_ids"),
        ):
            if row.get(field):
                aggregate[target].add(row[field])
    output: list[dict[str, Any]] = []
    for aggregate in aggregates.values():
        row = {
            "settlement_status": aggregate["settlement_status"],
            "recipient_creator_id": aggregate["recipient_creator_id"],
            "recipient_kind": aggregate["recipient_kind"],
            "work_id": aggregate["work_id"],
            "currency": aggregate["currency"],
            "total_payout": _money_str(aggregate["total_payout"]),
            "obligation_count": aggregate["obligation_count"],
            "segment_ids": sorted(aggregate["segment_ids"]),
            "source_labels": sorted(aggregate["source_labels"]),
            "claim_ids": sorted(aggregate["claim_ids"]),
            "chunk_ids": sorted(aggregate["chunk_ids"]),
        }
        row["aggregate_recipient_row_hash"] = hash_payload(row)
        output.append(row)
    return _sort_rows(
        output,
        "settlement_status",
        "recipient_creator_id",
        "work_id",
        "currency",
    )


def _duplicate_obligation_keys(rows: list[dict[str, Any]]) -> list[str]:
    keys = [str(row.get("obligation_key", "")) for row in rows]
    return sorted({key for key in keys if key and keys.count(key) > 1})


def _entitlement_weight_sums(
    source_entitlement_rows: list[dict[str, Any]],
) -> dict[str, Decimal]:
    sums: dict[str, Decimal] = {}
    for row in source_entitlement_rows:
        segment_id = str(row.get("segment_id", ""))
        sums[segment_id] = sums.get(segment_id, Decimal("0")) + _weight(
            row.get("allocation_weight", "0")
        )
    return {
        segment_id: total.quantize(WEIGHT_QUANT, rounding=ROUND_HALF_UP)
        for segment_id, total in sums.items()
    }


def _source_scope_failures(
    segment_rows: list[dict[str, Any]],
    source_entitlement_rows: list[dict[str, Any]],
) -> tuple[list[str], list[str], list[str]]:
    segments_by_id = {str(row.get("segment_id", "")): row for row in segment_rows}
    missing_segment_ids: list[str] = []
    unknown_source_refs: list[str] = []
    unknown_claim_refs: list[str] = []
    entitlement_segment_ids = {
        str(row.get("segment_id", "")) for row in source_entitlement_rows
    }
    for segment in segment_rows:
        segment_id = str(segment.get("segment_id", ""))
        if segment_id not in entitlement_segment_ids:
            missing_segment_ids.append(segment_id)
    for row in source_entitlement_rows:
        segment = segments_by_id.get(str(row.get("segment_id", "")), {})
        if not segment:
            missing_segment_ids.append(str(row.get("segment_id", "")))
            continue
        source_labels = {str(item) for item in segment.get("source_labels", [])}
        claim_ids = {str(item) for item in segment.get("claim_ids", [])}
        if row.get("source_label") and row["source_label"] not in source_labels:
            unknown_source_refs.append(
                f"{row.get('segment_id')}:{row.get('source_label')}"
            )
        if row.get("claim_id") and row["claim_id"] not in claim_ids:
            unknown_claim_refs.append(f"{row.get('segment_id')}:{row.get('claim_id')}")
    return (
        sorted(set(missing_segment_ids)),
        sorted(set(unknown_source_refs)),
        sorted(set(unknown_claim_refs)),
    )


def _checks(
    *,
    settlement_input: dict[str, Any],
    policy: dict[str, Any],
    artifact_bindings: dict[str, dict[str, Any]],
    composition_binding: dict[str, Any],
    revenue_binding: dict[str, Any],
    segment_rows: list[dict[str, Any]],
    provider_segment_rows: list[dict[str, Any]],
    source_entitlement_rows: list[dict[str, Any]],
    creator_obligation_rows: list[dict[str, Any]],
    aggregate_recipient_rows: list[dict[str, Any]],
    missing_segment_ids: list[str],
    unknown_source_refs: list[str],
    unknown_claim_refs: list[str],
    duplicate_keys: list[str],
) -> dict[str, bool]:
    clearinghouse = settlement_input.get("clearinghouse_report", {})
    clearinghouse_present = bool(clearinghouse)
    clearinghouse_summary = clearinghouse.get("summary", {})
    segment_ids = [str(row.get("segment_id", "")) for row in segment_rows]
    provider_segment_ids = [str(row.get("segment_id", "")) for row in provider_segment_rows]
    segment_pools_total = _sum_money(provider_segment_rows, "segment_pool")
    creator_obligation_total = _sum_money(creator_obligation_rows, "payout")
    aggregate_total = _sum_money(aggregate_recipient_rows, "total_payout")
    entitlement_sums = _entitlement_weight_sums(source_entitlement_rows)
    status_values = {str(row.get("settlement_status", "")) for row in creator_obligation_rows}
    source_footer_hash = composition_binding.get("source_footer_delivery_hash", "")
    public_report = {
        "composition_binding": composition_binding,
        "revenue_binding": revenue_binding,
        "provider_segment_settlement_rows": provider_segment_rows,
        "source_entitlement_rows": source_entitlement_rows,
        "creator_obligation_rows": creator_obligation_rows,
        "aggregate_recipient_rows": aggregate_recipient_rows,
    }
    return {
        "l130_composition_receipt_hash_reproducible": (
            artifact_bindings["universal_composition_receipt"]["present"]
            and artifact_bindings["universal_composition_receipt"]["hash_reproducible"]
        ),
        "l130_composition_receipt_released": (
            not policy["requires_l130_release"]
            or (
                composition_binding["composition_status"] == "released"
                and composition_binding["composition_target_level"] == MINIMUM_INPUT_LEVEL
            )
        ),
        "revenue_basis_present": _money(revenue_binding["creator_pool"]) > Decimal("0"),
        "revenue_allocation_ready_if_present": (
            not artifact_bindings["revenue_allocation_report"]["present"]
            or (
                artifact_bindings["revenue_allocation_report"]["hash_reproducible"]
                and artifact_bindings["revenue_allocation_report"]["status"] == "ready"
            )
        ),
        "creator_pool_matches_revenue_basis": (
            not policy["requires_revenue_conservation"]
            or _money(revenue_binding["creator_pool"])
            == _money(revenue_binding["expected_creator_pool"])
        ),
        "settlement_currency_matches_revenue": (
            str(policy["currency"]) == str(revenue_binding["currency"])
        ),
        "provider_segment_rows_cover_l130_segments": (
            bool(provider_segment_rows)
            and sorted(provider_segment_ids) == sorted(segment_ids)
        ),
        "provider_weights_conserve_unit": _provider_weights_conserve_unit(segment_rows),
        "segment_pools_conserve_creator_pool": (
            segment_pools_total == _money(revenue_binding["creator_pool"])
        ),
        "source_entitlement_rows_cover_segments": (
            not policy["requires_explicit_source_entitlements"]
            or (not missing_segment_ids and bool(source_entitlement_rows))
        ),
        "source_entitlements_reference_l130_claims_and_sources": (
            not unknown_source_refs and not unknown_claim_refs
        ),
        "source_entitlement_weights_conserve_each_segment": all(
            entitlement_sums.get(segment_id, Decimal("0")) == Decimal("1.000000")
            for segment_id in segment_ids
        )
        and bool(segment_ids),
        "creator_obligations_conserve_segment_pools": (
            creator_obligation_total == segment_pools_total
        ),
        "aggregate_rows_conserve_creator_obligations": (
            aggregate_total == creator_obligation_total
        ),
        "settlement_statuses_explicit": (
            bool(creator_obligation_rows)
            and status_values.issubset(SETTLEMENT_STATUSES)
            and all(row.get("settlement_status") for row in creator_obligation_rows)
        ),
        "unresolved_or_disputed_sources_not_paid": all(
            not (
                row.get("rights_status") in RIGHTS_ESCROW | RIGHTS_HELD
                and row.get("settlement_status") == "payable"
            )
            for row in creator_obligation_rows
        ),
        "source_footer_binding_preserved": (
            not policy["requires_source_footer_binding"]
            or all(
                row.get("source_footer_delivery_hash") == source_footer_hash
                for row in provider_segment_rows
            )
        ),
        "no_duplicate_creator_obligations": not duplicate_keys,
        "clearinghouse_ready_if_present": (
            not clearinghouse_present
            or (
                artifact_bindings["clearinghouse_report"]["hash_reproducible"]
                and clearinghouse_summary.get("status") == "ready"
                and _money(clearinghouse_summary.get("accounted_total", "0"))
                == _money(revenue_binding["creator_pool"])
            )
        ),
        "private_text_not_disclosed": (
            not _contains_private_fields(public_report)
            and _private_strings_absent(public_report, settlement_input)
        ),
    }


def _failure_modes(checks: dict[str, bool]) -> list[str]:
    mapping = {
        "l130_composition_receipt_hash_reproducible": "l130_receipt_hash_drift",
        "l130_composition_receipt_released": "l130_receipt_not_released",
        "revenue_basis_present": "missing_revenue_basis",
        "revenue_allocation_ready_if_present": "revenue_allocation_not_ready",
        "creator_pool_matches_revenue_basis": "creator_pool_revenue_mismatch",
        "settlement_currency_matches_revenue": "settlement_currency_mismatch",
        "provider_segment_rows_cover_l130_segments": "provider_segment_settlement_gap",
        "provider_weights_conserve_unit": "provider_weight_conservation_failure",
        "segment_pools_conserve_creator_pool": "segment_pool_conservation_failure",
        "source_entitlement_rows_cover_segments": "missing_source_entitlement",
        "source_entitlements_reference_l130_claims_and_sources": "source_entitlement_scope_mismatch",
        "source_entitlement_weights_conserve_each_segment": "source_entitlement_weight_mismatch",
        "creator_obligations_conserve_segment_pools": "creator_obligation_conservation_failure",
        "aggregate_rows_conserve_creator_obligations": "aggregate_recipient_conservation_failure",
        "settlement_statuses_explicit": "settlement_status_missing",
        "unresolved_or_disputed_sources_not_paid": "unresolved_source_paid",
        "source_footer_binding_preserved": "source_footer_binding_lost",
        "no_duplicate_creator_obligations": "duplicate_creator_obligation",
        "clearinghouse_ready_if_present": "clearinghouse_binding_mismatch",
        "private_text_not_disclosed": "private_text_leak",
    }
    return sorted(
        {mode for check, mode in mapping.items() if checks.get(check) is not True}
    )


def make_universal_composition_settlement(
    settlement_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an L131 settlement receipt for an L130 universal composition."""

    universal_receipt = settlement_input.get("universal_composition_receipt", {})
    policy = _policy(settlement_input)
    artifact_bindings = _artifact_bindings(settlement_input)
    revenue_binding = _revenue_binding(settlement_input, policy)
    composition_binding = _composition_binding(universal_receipt)
    segment_rows = _segment_rows(universal_receipt)
    provider_segment_rows = _provider_segment_settlement_rows(
        universal_receipt=universal_receipt,
        revenue_binding=revenue_binding,
    )
    source_entitlement_rows = _source_entitlement_rows(settlement_input, segment_rows)
    clearinghouse_hash = artifact_bindings["clearinghouse_report"]["declared_hash"]
    creator_obligation_rows = _creator_obligation_rows(
        composition_binding=composition_binding,
        revenue_binding=revenue_binding,
        provider_segment_rows=provider_segment_rows,
        source_entitlement_rows=source_entitlement_rows,
        clearinghouse_hash=clearinghouse_hash,
    )
    aggregate_rows = _aggregate_recipient_rows(creator_obligation_rows)
    (
        missing_segment_ids,
        unknown_source_refs,
        unknown_claim_refs,
    ) = _source_scope_failures(segment_rows, source_entitlement_rows)
    duplicate_keys = _duplicate_obligation_keys(creator_obligation_rows)
    checks = _checks(
        settlement_input=settlement_input,
        policy=policy,
        artifact_bindings=artifact_bindings,
        composition_binding=composition_binding,
        revenue_binding=revenue_binding,
        segment_rows=segment_rows,
        provider_segment_rows=provider_segment_rows,
        source_entitlement_rows=source_entitlement_rows,
        creator_obligation_rows=creator_obligation_rows,
        aggregate_recipient_rows=aggregate_rows,
        missing_segment_ids=missing_segment_ids,
        unknown_source_refs=unknown_source_refs,
        unknown_claim_refs=unknown_claim_refs,
        duplicate_keys=duplicate_keys,
    )
    failed = [key for key, value in checks.items() if value is not True]
    blocked = bool(failed)
    failure_modes = _failure_modes(checks)
    payable_rows = [
        row for row in creator_obligation_rows if row.get("settlement_status") == "payable"
    ]
    escrow_rows = [
        row for row in creator_obligation_rows if row.get("settlement_status") == "escrow"
    ]
    held_rows = [
        row for row in creator_obligation_rows if row.get("settlement_status") == "held"
    ]
    report: dict[str, Any] = {
        "settlement_version": UNIVERSAL_COMPOSITION_SETTLEMENT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "settlement_policy": policy,
        "artifact_bindings": artifact_bindings,
        "composition_binding": composition_binding,
        "revenue_binding": revenue_binding,
        "provider_segment_settlement_rows": provider_segment_rows,
        "source_entitlement_rows": source_entitlement_rows,
        "creator_obligation_rows": creator_obligation_rows,
        "aggregate_recipient_rows": aggregate_rows,
        "settlement_decision": {
            "decision": "block_settlement" if blocked else "release_settlement",
            "settlement_authorized": not blocked,
            "failed_checks": failed,
            "failure_modes": failure_modes,
            "safe_output_policy": (
                "suppress_unverified_composition_settlement"
                if blocked
                else "publish_composition_settlement_rows"
            ),
        },
        "checks": checks,
        "coverage_gaps": {
            "failed_checks": failed,
            "failure_modes": failure_modes,
            "missing_segment_entitlements": missing_segment_ids,
            "unknown_source_references": unknown_source_refs,
            "unknown_claim_references": unknown_claim_refs,
            "duplicate_obligation_keys": duplicate_keys,
            "entitlement_weight_sums_by_segment": {
                segment_id: _weight_str(total)
                for segment_id, total in _entitlement_weight_sums(
                    source_entitlement_rows
                ).items()
            },
        },
        "commitments": {
            "universal_composition_receipt_hash": composition_binding[
                "universal_composition_receipt_hash"
            ],
            "revenue_allocation_report_hash": revenue_binding[
                "revenue_allocation_report_hash"
            ],
            "clearinghouse_report_hash": clearinghouse_hash,
            "composition_binding_hash": composition_binding["composition_binding_hash"],
            "revenue_binding_hash": revenue_binding["revenue_binding_hash"],
            "provider_segment_root": composition_binding["provider_segment_root"],
            "segment_settlement_root": merkle_root(
                [row["segment_settlement_row_hash"] for row in provider_segment_rows]
            ),
            "source_entitlement_root": merkle_root(
                [row["source_entitlement_hash"] for row in source_entitlement_rows]
            ),
            "creator_obligation_root": merkle_root(
                [row["creator_obligation_hash"] for row in creator_obligation_rows]
            ),
            "aggregate_recipient_root": merkle_root(
                [row["aggregate_recipient_row_hash"] for row in aggregate_rows]
            ),
            "payable_root": merkle_root(
                [row["creator_obligation_hash"] for row in payable_rows]
            ),
            "escrow_root": merkle_root(
                [row["creator_obligation_hash"] for row in escrow_rows]
            ),
            "held_root": merkle_root(
                [row["creator_obligation_hash"] for row in held_rows]
            ),
            "schema": UNIVERSAL_COMPOSITION_SETTLEMENT_SCHEMA,
        },
        "schemas": {
            "universal_composition_settlement": UNIVERSAL_COMPOSITION_SETTLEMENT_SCHEMA,
            "universal_composition_receipt": "docs/schemas/universal_composition_receipt.schema.json",
            "revenue_allocation_report": "docs/schemas/revenue_allocation_report.schema.json",
            "clearinghouse_report": "docs/schemas/clearinghouse_report.schema.json",
        },
        "privacy": {
            "raw_prompt_text_disclosed": False,
            "raw_answer_text_disclosed": False,
            "raw_source_text_disclosed": False,
            "raw_billing_records_disclosed": False,
            "raw_provider_response_disclosed": False,
            "settlement_uses_hashes_ids_and_totals": True,
        },
        "summary": {
            "status": "blocked" if blocked else "ready",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "minimum_input_level": MINIMUM_INPUT_LEVEL,
            "composition_id": composition_binding["composition_id"],
            "currency": revenue_binding["currency"],
            "gross_revenue": revenue_binding["gross_revenue"],
            "creator_pool": revenue_binding["creator_pool"],
            "provider_segment_count": len(provider_segment_rows),
            "source_entitlement_count": len(source_entitlement_rows),
            "creator_obligation_count": len(creator_obligation_rows),
            "aggregate_recipient_count": len(aggregate_rows),
            "payable_total": _money_str(_sum_money(payable_rows, "payout")),
            "escrow_total": _money_str(_sum_money(escrow_rows, "payout")),
            "held_total": _money_str(_sum_money(held_rows, "payout")),
            "settled_total": _money_str(_sum_money(creator_obligation_rows, "payout")),
            "failed_check_count": len(failed),
            "failure_mode_count": len(failure_modes),
            "composition_settlement_authorized": not blocked,
            "double_payment_prevented": checks["no_duplicate_creator_obligations"],
            "unresolved_sources_escrowed_or_held": checks[
                "unresolved_or_disputed_sources_not_paid"
            ],
            "source_footer_binding_preserved": checks["source_footer_binding_preserved"],
            "privacy_preserved": checks["private_text_not_disclosed"],
        },
    }
    report["universal_composition_settlement_hash"] = hash_payload(
        _hashable_report(report)
    )
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


def validate_universal_composition_settlement_shape(
    report: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = (
        "settlement_version",
        "issuer",
        "created_at",
        "settlement_policy",
        "artifact_bindings",
        "composition_binding",
        "revenue_binding",
        "provider_segment_settlement_rows",
        "source_entitlement_rows",
        "creator_obligation_rows",
        "aggregate_recipient_rows",
        "settlement_decision",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
        "universal_composition_settlement_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing universal composition settlement field: {key}")
    if errors:
        return errors
    if report.get("settlement_version") != UNIVERSAL_COMPOSITION_SETTLEMENT_VERSION:
        errors.append("universal composition settlement version is unsupported")
    if (
        report.get("schemas", {}).get("universal_composition_settlement")
        != UNIVERSAL_COMPOSITION_SETTLEMENT_SCHEMA
    ):
        errors.append("universal composition settlement schema is not declared")
    if not isinstance(report.get("creator_obligation_rows"), list):
        errors.append("universal composition settlement obligations are not a list")
    if (
        report.get("summary", {}).get("target_certification_level")
        != TARGET_CERTIFICATION_LEVEL
    ):
        errors.append("universal composition settlement target level is not RDLLM-L131")
    return errors


def verify_universal_composition_settlement(
    report: dict[str, Any],
    *,
    settlement_input: dict[str, Any],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an L131 universal composition settlement against replay inputs."""

    errors = validate_universal_composition_settlement_shape(report)
    if errors:
        return errors

    if hash_payload(_hashable_report(report)) != report.get(
        "universal_composition_settlement_hash"
    ):
        errors.append("universal composition settlement hash is not reproducible")

    expected = make_universal_composition_settlement(
        settlement_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "settlement_policy",
        "artifact_bindings",
        "composition_binding",
        "revenue_binding",
        "provider_segment_settlement_rows",
        "source_entitlement_rows",
        "creator_obligation_rows",
        "aggregate_recipient_rows",
        "settlement_decision",
        "checks",
        "coverage_gaps",
        "commitments",
        "schemas",
        "privacy",
        "summary",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"universal composition settlement {key} does not match inputs")
    if expected.get("universal_composition_settlement_hash") != report.get(
        "universal_composition_settlement_hash"
    ):
        errors.append("universal composition settlement hash does not match inputs")

    decision = report.get("settlement_decision", {})
    if report.get("summary", {}).get("status") == "blocked":
        if decision.get("decision") != "block_settlement" or decision.get(
            "settlement_authorized"
        ):
            errors.append("universal composition blocked settlement is not fail-closed")
    elif report.get("summary", {}).get("status") == "ready":
        if decision.get("decision") != "release_settlement" or not decision.get(
            "settlement_authorized"
        ):
            errors.append("universal composition settlement is not releasable")
    else:
        errors.append("universal composition settlement status is unsupported")

    if _contains_private_fields(report):
        errors.append("universal composition settlement exposes private field names")
    if not _private_strings_absent(report, settlement_input):
        errors.append("universal composition settlement exposes private replay text")

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("universal composition settlement is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("universal composition settlement signature is invalid")

    return errors
