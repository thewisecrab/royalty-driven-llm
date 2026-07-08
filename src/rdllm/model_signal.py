"""Model-internal signal attribution reports for provider-private telemetry."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

import json

from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)
from rdllm.text import stable_hash

MODEL_SIGNAL_VERSION = "rdllm-model-signal-attribution/v1"
ATTRIBUTION_CONTRACT_VERSION = "rdllm-attribution-contract/v1"
DEFAULT_ACCEPT_THRESHOLD = 0.50
DEFAULT_CREATOR_POOL_RATE = Decimal("0.55")
MONEY_QUANT = Decimal("0.000001")

SIGNAL_WEIGHTS = {
    "logprob_delta": 0.30,
    "activation_similarity": 0.25,
    "gradient_influence": 0.20,
    "attention_mass": 0.15,
    "memorization_score": 0.10,
}

PRIVATE_SIGNAL_FIELDS = (
    "private_trace",
    "hidden_state",
    "hidden_states",
    "activation_vector",
    "activation_vectors",
    "token_logits",
    "raw_signal_payload",
    "prompt_text",
    "output_text",
)


def load_model_signal_input(path: str | Path) -> dict[str, Any]:
    """Load provider-private model attribution telemetry."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY_QUANT))


def _clamp_signal(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))


def _signal_scores(row: dict[str, Any]) -> dict[str, float]:
    signals = row.get("signals", row)
    return {
        channel: round(_clamp_signal(signals.get(channel, 0.0)), 8)
        for channel in SIGNAL_WEIGHTS
    }


def _decision_score(row: dict[str, Any]) -> float:
    scores = _signal_scores(row)
    return round(
        sum(scores[channel] * weight for channel, weight in SIGNAL_WEIGHTS.items()),
        8,
    )


def _content_hash(row: dict[str, Any]) -> str:
    value = str(row.get("content_hash") or "")
    if value:
        return value
    return stable_hash(
        canonical_json(
            {
                "work_id": row.get("work_id", ""),
                "title": row.get("title", ""),
                "source_uri": row.get("source_uri", ""),
            }
        )
    )


def _private_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row.get(key)
        for key in PRIVATE_SIGNAL_FIELDS
        if key in row and row.get(key) not in (None, "")
    }


def _signal_commitment(row: dict[str, Any]) -> str:
    return hash_payload(
        {
            "signal_id": row.get("signal_id", ""),
            "work_id": row.get("work_id", ""),
            "signals": _signal_scores(row),
            "private_payload": _private_payload(row),
        }
    )


def _private_strings(signal_input: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for field in ("prompt_text", "output_text"):
        values.append(str(signal_input.get("event", {}).get(field, "")))
    for row in signal_input.get("signals", []):
        for value in _private_payload(row).values():
            if isinstance(value, str):
                values.append(value)
            elif isinstance(value, list):
                values.extend(str(item) for item in value if isinstance(item, str))
            elif isinstance(value, dict):
                values.extend(str(item) for item in value.values() if isinstance(item, str))
    return [value for value in values if len(value.strip()) >= 16]


def _creators_by_id(signal_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(creator.get("creator_id", "")): creator
        for creator in signal_input.get("creators", [])
    }


def _ranked_rows(
    signal_input: dict[str, Any],
    *,
    accept_threshold: float,
) -> list[dict[str, Any]]:
    creators = _creators_by_id(signal_input)
    rows: list[dict[str, Any]] = []
    for signal in signal_input.get("signals", []):
        creator = creators.get(str(signal.get("creator_id", "")), {})
        decision_score = _decision_score(signal)
        policy_allowed = bool(signal.get("policy_allowed", True))
        accepted = policy_allowed and decision_score >= accept_threshold
        rows.append(
            {
                "signal_id": signal.get("signal_id", ""),
                "work_id": signal.get("work_id", ""),
                "creator_id": signal.get("creator_id", ""),
                "creator_name": creator.get("name", ""),
                "title": signal.get("title", ""),
                "source_uri": signal.get("source_uri", ""),
                "content_hash": _content_hash(signal),
                "signal_scores": _signal_scores(signal),
                "decision_score": decision_score,
                "policy_allowed": policy_allowed,
                "decision": "accepted" if accepted else "model_signal_escrow",
                "signal_commitment": _signal_commitment(signal),
                "rank": 0,
            }
        )
    rows.sort(
        key=lambda row: (
            row["decision"] != "accepted",
            -float(row["decision_score"]),
            str(row["work_id"]),
            str(row["signal_id"]),
        )
    )
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def _allocate_pool(
    rows: list[dict[str, Any]],
    *,
    creator_pool: Decimal,
) -> tuple[list[dict[str, Any]], Decimal]:
    weights: list[tuple[str, str, str, Decimal]] = []
    escrow_weight = Decimal("0")
    for row in rows:
        weight = Decimal(str(row["decision_score"]))
        if weight <= Decimal("0"):
            continue
        if row["decision"] == "accepted":
            weights.append(
                (
                    str(row["creator_id"]),
                    str(row["work_id"]),
                    str(row["signal_id"]),
                    weight,
                )
            )
        else:
            escrow_weight += weight

    total_weight = sum((item[3] for item in weights), Decimal("0")) + escrow_weight
    if total_weight <= Decimal("0"):
        return [
            {
                "creator_id": "model_signal_escrow",
                "work_id": "escrow:model_signal",
                "signal_ids": [row["signal_id"] for row in rows],
                "payout": _money(creator_pool),
                "contribution_weight": 1.0 if creator_pool else 0.0,
            }
        ], creator_pool

    shares: list[dict[str, Any]] = []
    paid_so_far = Decimal("0")
    payout_totals: defaultdict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    signal_ids: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    for index, (creator_id, work_id, signal_id, weight) in enumerate(weights):
        if index == len(weights) - 1 and escrow_weight == Decimal("0"):
            payout = creator_pool - paid_so_far
        else:
            payout = (creator_pool * weight / total_weight).quantize(MONEY_QUANT)
        paid_so_far += payout
        payout_totals[(creator_id, work_id)] += payout
        signal_ids[(creator_id, work_id)].append(signal_id)

    if escrow_weight:
        escrow_total = creator_pool - paid_so_far
    else:
        escrow_total = Decimal("0")

    for (creator_id, work_id), payout in sorted(payout_totals.items()):
        shares.append(
            {
                "creator_id": creator_id,
                "work_id": work_id,
                "signal_ids": sorted(signal_ids[(creator_id, work_id)]),
                "payout": _money(payout),
                "contribution_weight": round(float(payout / creator_pool), 8)
                if creator_pool
                else 0.0,
            }
        )
    if escrow_total:
        shares.append(
            {
                "creator_id": "model_signal_escrow",
                "work_id": "escrow:model_signal",
                "signal_ids": [
                    row["signal_id"]
                    for row in rows
                    if row["decision"] != "accepted"
                    and float(row["decision_score"]) > 0
                ],
                "payout": _money(escrow_total),
                "contribution_weight": round(float(escrow_total / creator_pool), 8)
                if creator_pool
                else 0.0,
            }
        )
    return shares, escrow_total


def make_model_signal_report(
    signal_input: dict[str, Any],
    *,
    gross_revenue: Decimal | str | float = Decimal("1.00"),
    creator_pool_rate: Decimal | str | float = DEFAULT_CREATOR_POOL_RATE,
    accept_threshold: float = DEFAULT_ACCEPT_THRESHOLD,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a privacy-preserving attribution report from model-internal signals."""

    gross = Decimal(str(gross_revenue)).quantize(MONEY_QUANT)
    rate = Decimal(str(creator_pool_rate))
    creator_pool = (gross * rate).quantize(MONEY_QUANT)
    rows = _ranked_rows(signal_input, accept_threshold=accept_threshold)
    shares, escrow_total = _allocate_pool(rows, creator_pool=creator_pool)
    accepted_rows = [row for row in rows if row["decision"] == "accepted"]
    event = signal_input.get("event", {})
    report = {
        "report_version": MODEL_SIGNAL_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "event": {
            "event_id": event.get("event_id", ""),
            "event_hash": event.get("event_hash", ""),
            "prompt_hash": event.get("prompt_hash", stable_hash(str(event.get("prompt_text", "")))),
            "output_hash": event.get("output_hash", stable_hash(str(event.get("output_text", "")))),
            "model_id": event.get("model_id", ""),
            "model_version": event.get("model_version", ""),
        },
        "attribution_contract": {
            "contract_version": ATTRIBUTION_CONTRACT_VERSION,
            "claim": "registered_work_influence_on_generated_output",
            "explained_output": "event.output_hash",
            "eligible_features": [
                "registered_work_signal_rows",
                "provider_retrieval_or_memory_signals",
                "training_or_finetuning_influence_signals",
            ],
            "feature_granularity": "registered_work",
            "generative_process": "autoregressive_or_equivalent_generation_trace",
            "attributed_score": "weighted_model_signal_decision_score",
            "held_fixed": [
                "model_id",
                "model_version",
                "prompt_hash",
                "output_hash",
                "signal_input_root",
                "rights_policy_profile",
            ],
            "excluded_features": [
                "raw_hidden_states",
                "raw_token_logits",
                "private_prompt_text",
                "private_output_text",
                "chain_of_thought",
            ],
            "public_claim_limit": "scores_and_commitments_prove_replayable_attribution_without_disclosing_private_telemetry",
        },
        "policy": {
            "profile": "rdllm-model-signal-policy/v1",
            "accept_threshold": round(float(accept_threshold), 8),
            "creator_pool_rate": str(rate),
            "signal_weights": SIGNAL_WEIGHTS,
            "accepted_decision": "accepted",
            "rejected_decision": "model_signal_escrow",
        },
        "economics": {
            "gross_revenue": _money(gross),
            "creator_pool": _money(creator_pool),
            "payout_total": _money(
                sum((Decimal(share["payout"]) for share in shares), Decimal("0"))
            ),
            "escrow_total": _money(escrow_total),
        },
        "signal_rows": rows,
        "royalty_shares": shares,
        "commitments": {
            "model_signal_input_root": hash_payload(
                [
                    {
                        "signal_id": row.get("signal_id", ""),
                        "work_id": row.get("work_id", ""),
                        "creator_id": row.get("creator_id", ""),
                        "content_hash": _content_hash(row),
                        "signal_scores": _signal_scores(row),
                        "private_signal_commitment": _signal_commitment(row),
                    }
                    for row in signal_input.get("signals", [])
                ]
            ),
            "signal_row_root": hash_payload(
                [
                    {
                        "signal_id": row["signal_id"],
                        "work_id": row["work_id"],
                        "decision_score": row["decision_score"],
                        "decision": row["decision"],
                        "signal_commitment": row["signal_commitment"],
                    }
                    for row in rows
                ]
            ),
            "share_root": hash_payload(shares),
        },
        "summary": {
            "status": "ready",
            "signal_count": len(rows),
            "accepted_signal_count": len(accepted_rows),
            "escrow_signal_count": len(rows) - len(accepted_rows),
            "creator_count": len({share["creator_id"] for share in shares if not share["creator_id"].endswith("_escrow")}),
            "work_count": len({share["work_id"] for share in shares if not str(share["work_id"]).startswith("escrow:")}),
            "creator_pool_conserved": (
                sum((Decimal(share["payout"]) for share in shares), Decimal("0"))
                == creator_pool
            ),
            "model_internal_signal_attribution": True,
        },
        "privacy": {
            "raw_hidden_states_disclosed": False,
            "raw_token_logits_disclosed": False,
            "raw_private_trace_disclosed": False,
            "prompt_text_disclosed": False,
            "output_text_disclosed": False,
            "report_uses_commitments_scores_and_source_ids": True,
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


def validate_model_signal_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "event",
        "attribution_contract",
        "policy",
        "economics",
        "signal_rows",
        "royalty_shares",
        "commitments",
        "summary",
        "privacy",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing model signal field: {key}")
    if errors:
        return errors
    if report.get("report_version") != MODEL_SIGNAL_VERSION:
        errors.append("model signal report version is unsupported")
    contract = report.get("attribution_contract", {})
    if contract.get("contract_version") != ATTRIBUTION_CONTRACT_VERSION:
        errors.append("model signal attribution contract is unsupported")
    for key in (
        "claim",
        "explained_output",
        "eligible_features",
        "feature_granularity",
        "generative_process",
        "attributed_score",
        "held_fixed",
        "excluded_features",
    ):
        if key not in contract:
            errors.append(f"missing model signal attribution contract field: {key}")
    for row in report.get("signal_rows", []):
        for key in (
            "signal_id",
            "work_id",
            "creator_id",
            "content_hash",
            "signal_scores",
            "decision_score",
            "decision",
            "signal_commitment",
            "rank",
        ):
            if key not in row:
                errors.append(f"missing model signal row field: {key}")
    return errors


def verify_model_signal_report(
    report: dict[str, Any],
    signal_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify a provider model-signal attribution report."""

    errors = validate_model_signal_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("model signal report hash is not reproducible")

    expected = make_model_signal_report(
        signal_input,
        gross_revenue=report.get("economics", {}).get("gross_revenue", "1.00"),
        creator_pool_rate=report.get("policy", {}).get(
            "creator_pool_rate", str(DEFAULT_CREATOR_POOL_RATE)
        ),
        accept_threshold=float(
            report.get("policy", {}).get("accept_threshold", DEFAULT_ACCEPT_THRESHOLD)
        ),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "event",
        "attribution_contract",
        "policy",
        "economics",
        "signal_rows",
        "royalty_shares",
        "commitments",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"model signal {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("model signal report hash does not match replay")

    if report.get("summary", {}).get("creator_pool_conserved") is not True:
        errors.append("model signal creator pool is not conserved")

    rendered = canonical_json(report)
    for value in _private_strings(signal_input):
        if value in rendered:
            errors.append("model signal report leaks raw private telemetry")
            break

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("model signal report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("model signal report signature is invalid")
    return errors
