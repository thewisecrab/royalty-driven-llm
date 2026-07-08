"""Residual training-corpus royalty reports for diffuse model value."""

from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash

RESIDUAL_CORPUS_ROYALTY_VERSION = "rdllm-residual-corpus-royalty-report/v1"
RESIDUAL_CORPUS_ROYALTY_SCHEMA = "docs/schemas/residual_corpus_royalty_report.schema.json"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L95"
MONEY_QUANT = Decimal("0.000001")
SHARE_QUANT = Decimal("0.00000001")
DEFAULT_CREATOR_POOL_RATE = Decimal("0.55")
DEFAULT_RESIDUAL_POOL_RATE = Decimal("0.10")
DEFAULT_MIN_CONFIDENCE = Decimal("0.50")
DEFAULT_MIN_VALUATION_SCORE = Decimal("0.000001")
DEFAULT_MAX_SINGLE_CREATOR_SHARE = Decimal("0.50")

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
}

DECLARED_HASH_FIELDS = (
    "report_hash",
    "summary_hash",
    "contract_hash",
    "attestation_hash",
    "manifest_hash",
    "profile_hash",
    "card_hash",
    "bundle_hash",
    "graph_hash",
    "trust_registry_hash",
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


def _share(value: Any) -> str:
    return str(_decimal(value).quantize(SHARE_QUANT, rounding=ROUND_HALF_UP))


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


def _declared_hash(artifact: dict[str, Any]) -> str:
    for field in DECLARED_HASH_FIELDS:
        value = artifact.get(field)
        if isinstance(value, str) and value:
            return value
    return hash_payload(_hashable_artifact(artifact)) if artifact else ""


def _artifact_hash_is_reproducible(artifact: dict[str, Any]) -> bool:
    declared = _declared_hash(artifact)
    return bool(declared) and declared == hash_payload(_hashable_artifact(artifact))


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


def _artifact_row(name: str, artifact: dict[str, Any]) -> dict[str, Any]:
    row = {
        "name": name,
        "artifact_type": str(
            artifact.get("summary_version")
            or artifact.get("contract_version")
            or artifact.get("version")
            or artifact.get("report_version")
            or ""
        ),
        "artifact_hash": _declared_hash(artifact),
        "payload_hash": hash_payload(_hashable_artifact(artifact)) if artifact else "",
        "hash_reproducible": _artifact_hash_is_reproducible(artifact),
        "status": str(artifact.get("summary", {}).get("status", "")),
        "highest_level": str(
            artifact.get("summary", {}).get("target_certification_level")
            or artifact.get("summary", {}).get("highest_level", "")
        ),
    }
    row["artifact_row_hash"] = hash_payload(row)
    return row


def _cohort_rows(training_summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, entry in enumerate(
        training_summary.get("training_content", {}).get("cohorts", []),
        start=1,
    ):
        row = {
            "cohort_id": str(entry.get("work_id") or f"cohort:{index}"),
            "work_id": str(entry.get("work_id", "")),
            "creator_id": str(entry.get("creator_id", "")),
            "content_modality": str(entry.get("content_modality", "")),
            "content_category": str(entry.get("content_category", "")),
            "license": str(entry.get("license", "")),
            "source_uri_hash": stable_hash(str(entry.get("source_uri", "")))
            if entry.get("source_uri")
            else "",
            "content_hash": str(entry.get("content_hash", "")),
            "chunk_count": int(entry.get("chunk_count", 0) or 0),
            "chunk_hash_root": str(entry.get("chunk_hash_root", "")),
            "training_allowed": bool(entry.get("training_allowed", False)),
            "requires_royalty": bool(entry.get("requires_royalty", False)),
            "requires_attribution": bool(entry.get("requires_attribution", False)),
            "revoked": bool(entry.get("revoked", False)),
            "training_value_root": str(entry.get("training_value_root", "")),
        }
        row["cohort_row_hash"] = hash_payload(row)
        rows.append(row)
    return rows


def _license_terms(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(term.get("work_id", "")): term for term in contract.get("terms", [])}


def _revenue_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    public = {
        "revenue_id": str(row.get("revenue_id", row.get("source_id", f"revenue:{index}"))),
        "source_type": str(row.get("source_type", row.get("type", "model_usage_revenue"))),
        "period_start": str(row.get("period_start", "")),
        "period_end": str(row.get("period_end", "")),
        "currency": str(row.get("currency", "USD")),
        "amount": _money(row.get("amount", "0")),
        "revenue_source_hash": str(
            row.get("revenue_source_hash")
            or row.get("source_hash")
            or row.get("billing_record_hash")
            or ""
        ),
    }
    public["revenue_row_hash"] = str(row.get("revenue_row_hash") or hash_payload(public))
    return public


def _valuation_row(
    row: dict[str, Any],
    index: int,
    *,
    cohort_by_work: dict[str, dict[str, Any]],
    terms_by_work: dict[str, dict[str, Any]],
    min_confidence: Decimal,
    min_score: Decimal,
) -> dict[str, Any]:
    work_id = str(row.get("work_id", ""))
    cohort = cohort_by_work.get(work_id, {})
    term = terms_by_work.get(work_id, {})
    score = max(_decimal(row.get("valuation_score", row.get("training_value_score", "0"))), Decimal("0"))
    confidence = max(min(_decimal(row.get("confidence_score", "1")), Decimal("1")), Decimal("0"))
    allowed_uses = set(str(item) for item in term.get("allowed_uses", []))
    reasons: list[str] = []
    if not cohort:
        reasons.append("missing_training_summary_cohort")
    if not term:
        reasons.append("missing_license_term")
    if not cohort.get("training_allowed", False):
        reasons.append("training_not_allowed_by_summary")
    if term.get("consent_status") != "active":
        reasons.append("license_not_active")
    if "training" not in allowed_uses:
        reasons.append("training_use_not_licensed")
    if cohort.get("revoked") or term.get("revoked"):
        reasons.append("revoked_work")
    if confidence < min_confidence:
        reasons.append("valuation_confidence_below_threshold")
    if score < min_score:
        reasons.append("valuation_score_below_threshold")
    if not row.get("valuation_evidence_hash"):
        reasons.append("missing_valuation_evidence_hash")
    public = {
        "valuation_id": str(row.get("valuation_id", f"valuation:{index}")),
        "work_id": work_id,
        "creator_id": str(row.get("creator_id") or cohort.get("creator_id", "")),
        "valuation_method": str(row.get("valuation_method", "dynamic_local_shapley")),
        "valuation_score": _share(score),
        "confidence_score": _share(confidence),
        "valuation_evidence_hash": str(row.get("valuation_evidence_hash", "")),
        "valuation_matrix_cell_hash": str(
            row.get("valuation_matrix_cell_hash")
            or stable_hash(f"{work_id}:{score}:{confidence}")
        ),
        "training_value_root": str(
            row.get("training_value_root") or cohort.get("training_value_root", "")
        ),
        "cohort_row_hash": str(cohort.get("cohort_row_hash", "")),
        "license_term_hash": str(term.get("term_hash", "")),
        "payout_account_hash": str(term.get("payout_account_hash", "")),
        "eligible_for_residual_royalty": not reasons,
        "ineligibility_reasons": reasons,
    }
    public["valuation_row_hash"] = str(row.get("valuation_row_hash") or hash_payload(public))
    return public


def _bounded_shares(
    score_by_key: dict[str, Decimal],
    *,
    target_share: Decimal,
    cap: Decimal,
) -> dict[str, Decimal]:
    if not score_by_key or target_share <= 0:
        return {key: Decimal("0") for key in score_by_key}
    remaining = set(score_by_key)
    shares = {key: Decimal("0") for key in score_by_key}
    remaining_share = target_share
    while remaining and remaining_share > 0:
        total = sum(score_by_key[key] for key in remaining)
        if total <= 0:
            equal = remaining_share / Decimal(len(remaining))
            for key in remaining:
                shares[key] += min(equal, cap)
            break
        capped_this_round: set[str] = set()
        for key in sorted(remaining):
            proposed = remaining_share * score_by_key[key] / total
            if shares[key] + proposed > cap:
                delta = cap - shares[key]
                shares[key] = cap
                remaining_share -= max(delta, Decimal("0"))
                capped_this_round.add(key)
        if not capped_this_round:
            for key in remaining:
                shares[key] += remaining_share * score_by_key[key] / total
            break
        remaining -= capped_this_round
    return shares


def _creator_bounded_work_shares(
    rows: list[dict[str, Any]],
    raw_share_by_hash: dict[str, Decimal],
    *,
    max_share: Decimal,
) -> tuple[dict[str, Decimal], Decimal, list[dict[str, Any]]]:
    score_by_creator: dict[str, Decimal] = {}
    score_by_row: dict[str, Decimal] = {}
    row_hash_by_creator: dict[str, list[str]] = {}
    for row in rows:
        row_hash = row["valuation_row_hash"]
        creator_id = row["creator_id"]
        score = _decimal(row["valuation_score"])
        score_by_row[row_hash] = score
        score_by_creator[creator_id] = score_by_creator.get(creator_id, Decimal("0")) + score
        row_hash_by_creator.setdefault(creator_id, []).append(row_hash)

    target_share = sum(raw_share_by_hash[row["valuation_row_hash"]] for row in rows)
    creator_share_by_id = _bounded_shares(
        score_by_creator,
        target_share=target_share,
        cap=max_share,
    )
    row_share_by_hash: dict[str, Decimal] = {}
    creator_rows: list[dict[str, Any]] = []
    for creator_id in sorted(row_hash_by_creator):
        creator_share = creator_share_by_id.get(creator_id, Decimal("0"))
        creator_score = score_by_creator.get(creator_id, Decimal("0"))
        allocated = Decimal("0")
        row_hashes = sorted(row_hash_by_creator[creator_id])
        for index, row_hash in enumerate(row_hashes, start=1):
            if creator_score <= 0:
                row_share = (
                    creator_share / Decimal(len(row_hashes)) if row_hashes else Decimal("0")
                )
            elif index == len(row_hashes):
                row_share = creator_share - allocated
            else:
                row_share = creator_share * score_by_row[row_hash] / creator_score
                allocated += row_share
            row_share_by_hash[row_hash] = max(row_share, Decimal("0"))
        creator_row = {
            "creator_id": creator_id,
            "eligible_work_count": len(row_hashes),
            "valuation_score_total": _share(creator_score),
            "raw_share_total": _share(
                sum(raw_share_by_hash[row_hash] for row_hash in row_hashes)
            ),
            "bounded_share_total": _share(creator_share),
            "max_single_creator_share": _share(max_share),
            "creator_share_capped": creator_share
            < sum(raw_share_by_hash[row_hash] for row_hash in row_hashes),
        }
        creator_row["creator_residual_share_hash"] = hash_payload(creator_row)
        creator_rows.append(creator_row)
    return row_share_by_hash, sum(creator_share_by_id.values()), creator_rows


def _receipt_row(row: dict[str, Any], row_hash: str, amount: Decimal, index: int) -> dict[str, Any]:
    receipt = {
        "receipt_id": f"residual-corpus-royalty-receipt:{index}",
        "recipient_creator_id": row["creator_id"],
        "work_id": row["work_id"],
        "currency": row["currency"],
        "amount": _money(amount),
        "basis": "diffuse_training_corpus_residual_royalty",
        "valuation_row_hash": row["valuation_row_hash"],
        "settlement_row_hash": row_hash,
    }
    receipt["receipt_hash"] = hash_payload(receipt)
    return receipt


def load_residual_corpus_royalty_input(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def make_residual_corpus_royalty_report(
    residual_input: dict[str, Any],
    *,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed residual royalty report for licensed training-corpus value."""

    training_summary = dict(residual_input.get("training_content_summary", {}))
    license_contract = dict(residual_input.get("creator_license_contract", {}))
    revenue_allocation_report = dict(residual_input.get("revenue_allocation_report", {}))
    finance_ledger_attestation = dict(residual_input.get("finance_ledger_attestation", {}))
    policy = dict(residual_input.get("policy", {}))
    creator_pool_rate = _decimal(policy.get("creator_pool_rate", DEFAULT_CREATOR_POOL_RATE))
    residual_pool_rate = _decimal(policy.get("residual_pool_rate", DEFAULT_RESIDUAL_POOL_RATE))
    min_confidence = _decimal(policy.get("minimum_confidence_score", DEFAULT_MIN_CONFIDENCE))
    min_score = _decimal(policy.get("minimum_valuation_score", DEFAULT_MIN_VALUATION_SCORE))
    max_share = _decimal(policy.get("max_single_creator_share", DEFAULT_MAX_SINGLE_CREATOR_SHARE))

    evidence_artifacts = [
        _artifact_row("training_content_summary", training_summary),
        _artifact_row("creator_license_contract", license_contract),
    ]
    if revenue_allocation_report:
        evidence_artifacts.append(
            _artifact_row("revenue_allocation_report", revenue_allocation_report)
        )
    if finance_ledger_attestation:
        evidence_artifacts.append(
            _artifact_row("finance_ledger_attestation", finance_ledger_attestation)
        )

    corpus_rows = _cohort_rows(training_summary)
    cohort_by_work = {row["work_id"]: row for row in corpus_rows}
    terms_by_work = _license_terms(license_contract)
    revenue_rows = [
        _revenue_row(row, index)
        for index, row in enumerate(residual_input.get("model_usage_revenue_rows", []), start=1)
    ]
    valuation_rows = [
        _valuation_row(
            row,
            index,
            cohort_by_work=cohort_by_work,
            terms_by_work=terms_by_work,
            min_confidence=min_confidence,
            min_score=min_score,
        )
        for index, row in enumerate(residual_input.get("valuation_rows", []), start=1)
    ]
    revenue_total = sum(_decimal(row["amount"]) for row in revenue_rows)
    residual_pool = (revenue_total * creator_pool_rate * residual_pool_rate).quantize(
        MONEY_QUANT,
        rounding=ROUND_HALF_UP,
    )
    total_score = sum(_decimal(row["valuation_score"]) for row in valuation_rows)
    eligible_rows = [row for row in valuation_rows if row["eligible_for_residual_royalty"]]
    escrow_candidate_rows = [
        row for row in valuation_rows if not row["eligible_for_residual_royalty"]
    ]
    raw_share_by_hash = {
        row["valuation_row_hash"]: (
            _decimal(row["valuation_score"]) / total_score if total_score > 0 else Decimal("0")
        )
        for row in valuation_rows
    }
    escrow_rows: list[dict[str, Any]] = []
    escrow_total = Decimal("0")
    escrowed_valuation_hashes: set[str] = set()
    for index, row in enumerate(escrow_candidate_rows, start=1):
        amount = (residual_pool * raw_share_by_hash[row["valuation_row_hash"]]).quantize(
            MONEY_QUANT,
            rounding=ROUND_HALF_UP,
        )
        escrow = {
            "escrow_id": f"escrow:residual-corpus:{index}",
            "recipient_creator_id": row["creator_id"],
            "work_id": row["work_id"],
            "currency": str(policy.get("currency", "USD")),
            "amount": _money(amount),
            "reason": "residual_corpus_valuation_not_payable",
            "ineligibility_reasons": row["ineligibility_reasons"],
            "valuation_row_hash": row["valuation_row_hash"],
        }
        escrow["escrow_row_hash"] = hash_payload(escrow)
        escrow_rows.append(escrow)
        escrow_total += amount
        escrowed_valuation_hashes.add(row["valuation_row_hash"])

    bounded_share_by_hash, bounded_share_total, creator_share_rows = (
        _creator_bounded_work_shares(
            eligible_rows,
            raw_share_by_hash,
            max_share=max_share,
        )
    )
    bounded_payable_pool = (residual_pool * bounded_share_total).quantize(
        MONEY_QUANT,
        rounding=ROUND_HALF_UP,
    )
    payable_rows: list[dict[str, Any]] = []
    receipt_rows: list[dict[str, Any]] = []
    paid_so_far = Decimal("0")
    for index, row in enumerate(sorted(eligible_rows, key=lambda item: item["valuation_row_hash"]), start=1):
        if index == len(eligible_rows):
            amount = bounded_payable_pool - paid_so_far
        else:
            amount = (residual_pool * bounded_share_by_hash[row["valuation_row_hash"]]).quantize(
                MONEY_QUANT,
                rounding=ROUND_HALF_UP,
            )
            paid_so_far += amount
        payable = {
            "payable_id": f"payable:residual-corpus:{index}",
            "recipient_creator_id": row["creator_id"],
            "work_id": row["work_id"],
            "currency": str(policy.get("currency", "USD")),
            "amount": _money(amount),
            "raw_share": _share(raw_share_by_hash[row["valuation_row_hash"]]),
            "bounded_share": _share(bounded_share_by_hash[row["valuation_row_hash"]]),
            "valuation_method": row["valuation_method"],
            "valuation_row_hash": row["valuation_row_hash"],
            "cohort_row_hash": row["cohort_row_hash"],
            "license_term_hash": row["license_term_hash"],
            "payout_account_hash": row["payout_account_hash"],
            "basis": "licensed_training_corpus_residual_value",
        }
        payable["payable_row_hash"] = hash_payload(payable)
        payable_rows.append(payable)
        receipt_rows.append(_receipt_row({**row, "currency": payable["currency"]}, payable["payable_row_hash"], amount, index))

    payable_total = sum(_decimal(row["amount"]) for row in payable_rows)
    cap_or_rounding_overflow = residual_pool - payable_total - escrow_total
    if cap_or_rounding_overflow > Decimal("0"):
        overflow = {
            "escrow_id": "escrow:residual-corpus:creator-cap-overflow",
            "recipient_creator_id": "residual_corpus_pool_escrow",
            "work_id": "",
            "currency": str(policy.get("currency", "USD")),
            "amount": _money(cap_or_rounding_overflow),
            "reason": "residual_corpus_creator_cap_or_rounding_overflow",
            "ineligibility_reasons": [
                "creator_share_cap_or_rounding_remainder_requires_future_allocation"
            ],
            "valuation_row_hash": hash_payload(creator_share_rows),
        }
        overflow["escrow_row_hash"] = hash_payload(overflow)
        escrow_rows.append(overflow)
        escrow_total += cap_or_rounding_overflow
    direct_rows = [
        {
            "source_report_hash": str(row.get("source_report_hash", "")),
            "settlement_row_hash": str(row.get("settlement_row_hash", "")),
            "amount": _money(row.get("amount", "0")),
            "excluded_from_residual_pool": True,
        }
        for row in residual_input.get("direct_attribution_settlement_rows", [])
    ]
    for row in direct_rows:
        row["direct_row_hash"] = hash_payload(row)

    checks = {
        "training_summary_hash_reproducible": evidence_artifacts[0]["hash_reproducible"],
        "creator_license_contract_hash_reproducible": evidence_artifacts[1]["hash_reproducible"],
        "revenue_rows_hash_bound": all(row["revenue_source_hash"] for row in revenue_rows)
        and bool(revenue_rows),
        "valuation_rows_cover_training_summary": {
            row["work_id"] for row in valuation_rows
        }.issubset(set(cohort_by_work))
        and bool(valuation_rows),
        "valuation_evidence_hashes_present": all(
            row["valuation_evidence_hash"] for row in valuation_rows
        ),
        "rights_policy_enforced": all(
            row["eligible_for_residual_royalty"]
            or row["ineligibility_reasons"]
            for row in valuation_rows
        ),
        "unlicensed_or_weak_value_escrowed": all(
            row["valuation_row_hash"] in escrowed_valuation_hashes
            for row in escrow_candidate_rows
        ),
        "max_single_creator_share_enforced": all(
            _decimal(row["bounded_share_total"]) <= max_share
            for row in creator_share_rows
        ),
        "residual_pool_conserved": residual_pool == payable_total + escrow_total,
        "direct_attribution_not_double_counted": all(
            row["excluded_from_residual_pool"] and row["settlement_row_hash"]
            for row in direct_rows
        )
        if direct_rows
        else True,
        "creator_receipts_created": len(receipt_rows) == len(payable_rows),
        "private_text_not_disclosed": True,
    }
    status = "ready" if all(checks.values()) else "needs_review"

    report = {
        "version": RESIDUAL_CORPUS_ROYALTY_VERSION,
        "issued_at": created_at or now_iso(),
        "issuer": issuer,
        "case": {
            "case_id": str(residual_input.get("case_id", "residual-corpus-royalty")),
            "status": status,
            "period_start": str(residual_input.get("period_start", "")),
            "period_end": str(residual_input.get("period_end", "")),
        },
        "policy": {
            "currency": str(policy.get("currency", "USD")),
            "creator_pool_rate": str(creator_pool_rate),
            "residual_pool_rate": str(residual_pool_rate),
            "minimum_confidence_score": str(min_confidence),
            "minimum_valuation_score": str(min_score),
            "max_single_creator_share": str(max_share),
            "valuation_method_family": str(
                policy.get("valuation_method_family", "dynamic_local_shapley")
            ),
            "residual_pool_separate_from_direct_attribution": True,
        },
        "scope": {
            "visible_answer_attribution_surface": (
                "source-confidence, citation-footer, rendered-attribution-audit, "
                "claim-source-attribution, semantic-text-attribution"
            ),
            "residual_training_value_surface": "residual-corpus-royalty",
            "does_not_replace_user_visible_citations": True,
            "does_not_double_count_direct_answer_attribution": True,
            "only_settles_diffuse_licensed_training_corpus_value": True,
        },
        "evidence_artifacts": evidence_artifacts,
        "model_usage_revenue_rows": revenue_rows,
        "training_corpus_rows": corpus_rows,
        "valuation_rows": valuation_rows,
        "creator_residual_share_rows": creator_share_rows,
        "direct_attribution_settlement_rows": direct_rows,
        "payable_rows": payable_rows,
        "escrow_rows": escrow_rows,
        "creator_residual_receipts": receipt_rows,
        "accounting": {
            "model_usage_revenue_total": _money(revenue_total),
            "creator_pool_rate": str(creator_pool_rate),
            "residual_pool_rate": str(residual_pool_rate),
            "residual_corpus_pool": _money(residual_pool),
            "payable_total": _money(payable_total),
            "escrow_total": _money(escrow_total),
            "direct_attribution_total_excluded": _money(
                sum(_decimal(row["amount"]) for row in direct_rows)
            ),
        },
        "checks": checks,
        "privacy": {
            "raw_training_text_disclosed": False,
            "raw_prompt_disclosed": False,
            "raw_output_disclosed": False,
            "raw_customer_records_disclosed": False,
            "raw_payment_details_disclosed": False,
            "public_report_uses_hash_commitments": True,
        },
        "schemas": {
            "residual_corpus_royalty_report": RESIDUAL_CORPUS_ROYALTY_SCHEMA,
        },
        "summary": {
            "status": status,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "valuation_row_count": len(valuation_rows),
            "eligible_valuation_row_count": len(eligible_rows),
            "escrow_valuation_row_count": len(escrow_rows),
            "payable_count": len(payable_rows),
            "creator_residual_receipt_count": len(receipt_rows),
            "creator_count": len(creator_share_rows),
            "creator_pool_conserved": checks["residual_pool_conserved"],
            "direct_attribution_separated": checks[
                "direct_attribution_not_double_counted"
            ],
            "model_usage_revenue_total": _money(revenue_total),
            "residual_corpus_pool": _money(residual_pool),
            "payable_total": _money(payable_total),
            "escrow_total": _money(escrow_total),
            "residual_pool_conserved": checks["residual_pool_conserved"],
        },
    }
    if _contains_private_fields(report):
        report["checks"]["private_text_not_disclosed"] = False
        report["case"]["status"] = "needs_review"
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


def validate_residual_corpus_royalty_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "version",
        "case",
        "policy",
        "scope",
        "evidence_artifacts",
        "model_usage_revenue_rows",
        "training_corpus_rows",
        "valuation_rows",
        "creator_residual_share_rows",
        "direct_attribution_settlement_rows",
        "payable_rows",
        "escrow_rows",
        "creator_residual_receipts",
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
            errors.append(f"missing residual corpus royalty report field: {key}")
    if report.get("version") != RESIDUAL_CORPUS_ROYALTY_VERSION:
        errors.append("residual corpus royalty report version is unsupported")
    if "residual_corpus_royalty_report" not in report.get("schemas", {}):
        errors.append("missing residual corpus royalty report schema")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("residual corpus royalty target level is incorrect")
    return errors


def verify_residual_corpus_royalty_report(
    report: dict[str, Any],
    residual_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a residual corpus royalty report against private valuation evidence."""

    errors = validate_residual_corpus_royalty_report_shape(report)
    if hash_payload(_hashable_report(report)) != report.get("report_hash", ""):
        errors.append("residual corpus royalty report hash is not reproducible")
    expected = make_residual_corpus_royalty_report(
        residual_input,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("issued_at"),
        signing_secret=signing_secret,
    )
    comparable_keys = (
        "case",
        "policy",
        "scope",
        "evidence_artifacts",
        "model_usage_revenue_rows",
        "training_corpus_rows",
        "valuation_rows",
        "creator_residual_share_rows",
        "direct_attribution_settlement_rows",
        "payable_rows",
        "escrow_rows",
        "creator_residual_receipts",
        "accounting",
        "checks",
        "privacy",
        "schemas",
        "summary",
    )
    for key in comparable_keys:
        if report.get(key) != expected.get(key):
            errors.append(f"residual corpus royalty report {key} does not match evidence")
    if report.get("report_hash") != expected.get("report_hash"):
        errors.append("residual corpus royalty report hash does not match evidence")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("residual corpus royalty report status is not ready")
    for check, passed in report.get("checks", {}).items():
        if not passed:
            errors.append(f"residual corpus royalty check failed: {check}")
    if _contains_private_fields(report) or any(
        private and private in canonical_json(report)
        for private in residual_input.get("private_strings", [])
    ):
        errors.append("residual corpus royalty report discloses private text")
    if signing_secret:
        signature = report.get("signature", {})
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("residual corpus royalty report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("residual corpus royalty report signature is invalid")
    return errors
