"""Causal evidence-utility attribution for grounded responses.

This layer audits whether a credited source merely looks relevant or actually
matters to the answer under replay interventions. It uses shallow observable
retrieval-use traces plus REMOVE, REPLACE, DUPLICATE, and multi-source removal
trials to reject spurious citations, prior-context citation drift, and duplicate
over-crediting.
"""

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

EVIDENCE_UTILITY_ATTRIBUTION_VERSION = "rdllm-causal-evidence-utility/v1"
EVIDENCE_UTILITY_ATTRIBUTION_SCHEMA = (
    "docs/schemas/evidence_utility_attribution_report.schema.json"
)
EVIDENCE_UTILITY_ATTRIBUTION_POLICY_VERSION = (
    "rdllm-causal-evidence-utility-policy/v1"
)
TARGET_CERTIFICATION_LEVEL = "RDLLM-L88"
DEFAULT_CREATOR_POOL_RATE = Decimal("0.55")
DEFAULT_MIN_UTILITY = 0.35
DEFAULT_MAX_DUPLICATE_CREDIT_INFLATION = 0.02
DEFAULT_MAX_DUPLICATE_TRACE_DRIFT = 0.12
MONEY_QUANT = Decimal("0.000001")


def load_evidence_utility_input(path: str | Path) -> dict[str, Any]:
    """Load private inputs used to replay a causal evidence utility report."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY_QUANT))


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _event_input(utility_input: dict[str, Any]) -> dict[str, Any]:
    event = utility_input.get("event", {})
    prompt = str(event.get("prompt_text", ""))
    response = str(event.get("response_text", event.get("output_text", "")))
    return {
        "event_id": str(event.get("event_id", "")),
        "event_hash": str(event.get("event_hash") or stable_hash(response)),
        "prompt_hash": str(event.get("prompt_hash") or stable_hash(prompt)),
        "response_hash": str(event.get("response_hash") or stable_hash(response)),
        "model_id": str(event.get("model_id", "")),
        "model_version": str(event.get("model_version", "")),
    }


def _claim_id(claim: dict[str, Any], index: int) -> str:
    return str(claim.get("claim_id") or f"claim_{index}")


def _source_id(source: dict[str, Any], index: int) -> str:
    return str(
        source.get("source_id")
        or source.get("document_id")
        or source.get("chunk_id")
        or source.get("work_id")
        or f"source_{index}"
    )


def _source_content_hash(source: dict[str, Any]) -> str:
    return str(source.get("content_hash") or stable_hash(str(source.get("content", ""))))


def _claim_rows(utility_input: dict[str, Any]) -> list[dict[str, Any]]:
    claims = utility_input.get("claims", [])
    if not claims:
        response = str(
            utility_input.get("event", {}).get(
                "response_text",
                utility_input.get("event", {}).get("output_text", ""),
            )
        )
        claims = [{"claim_id": "claim_1", "claim_text": response}]
    rows: list[dict[str, Any]] = []
    for index, claim in enumerate(claims, start=1):
        claim_text = str(claim.get("claim_text", ""))
        rows.append(
            {
                "claim_id": _claim_id(claim, index),
                "claim_hash": str(claim.get("claim_hash") or stable_hash(claim_text)),
                "expected_source_ids": sorted(
                    str(item) for item in claim.get("expected_source_ids", [])
                ),
                "requires_current_turn_evidence": bool(
                    claim.get("requires_current_turn_evidence", True)
                ),
            }
        )
    return rows


def _source_rows(utility_input: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, source in enumerate(utility_input.get("candidate_sources", []), start=1):
        rows.append(
            {
                "source_id": _source_id(source, index),
                "work_id": str(source.get("work_id", "")),
                "chunk_id": str(source.get("chunk_id", "")),
                "creator_id": str(source.get("creator_id", "")),
                "creator_name": str(source.get("creator_name", "")),
                "title": str(source.get("title", "")),
                "source_uri": str(source.get("source_uri", "")),
                "content_hash": _source_content_hash(source),
                "modality": str(source.get("modality", "text") or "text").lower(),
                "source_role": str(source.get("source_role", "candidate") or "candidate"),
            }
        )
    return rows


def _outcome_key(claim_id: str) -> str:
    return str(claim_id)


def _outcomes_by_claim(container: dict[str, Any]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for outcome in container.get("claim_outcomes", []):
        claim_id = str(outcome.get("claim_id", ""))
        if claim_id:
            grouped[_outcome_key(claim_id)] = dict(outcome)
    return grouped


def _claim_score(outcome: dict[str, Any]) -> float:
    supported = 1.0 if bool(outcome.get("supported", False)) else 0.0
    confidence = _clamp(float(outcome.get("confidence", 0.0) or 0.0))
    groundedness = _clamp(float(outcome.get("groundedness", confidence) or 0.0))
    return _clamp((0.5 * supported) + (0.3 * confidence) + (0.2 * groundedness))


def _cited_source_ids(outcome: dict[str, Any]) -> set[str]:
    return {str(item) for item in outcome.get("cited_source_ids", [])}


def _trial_target_set(trial: dict[str, Any]) -> set[str]:
    return {str(item) for item in trial.get("target_source_ids", [])}


def _trial_operator(trial: dict[str, Any]) -> str:
    return str(trial.get("operator", "")).lower().strip()


def _trial_hash(trial: dict[str, Any]) -> str:
    redacted = {
        "trial_id": str(trial.get("trial_id", "")),
        "operator": _trial_operator(trial),
        "target_source_ids": sorted(_trial_target_set(trial)),
        "replacement_source_ids": sorted(
            str(item) for item in trial.get("replacement_source_ids", [])
        ),
        "trace_divergence": round(
            _clamp(float(trial.get("trace_divergence", 0.0) or 0.0)), 8
        ),
        "claim_outcome_hashes": [
            hash_payload(
                {
                    "claim_id": str(outcome.get("claim_id", "")),
                    "supported": bool(outcome.get("supported", False)),
                    "confidence": round(
                        _clamp(float(outcome.get("confidence", 0.0) or 0.0)), 8
                    ),
                    "groundedness": round(
                        _clamp(float(outcome.get("groundedness", 0.0) or 0.0)), 8
                    ),
                    "cited_source_ids": sorted(_cited_source_ids(outcome)),
                }
            )
            for outcome in trial.get("claim_outcomes", [])
        ],
        "duplicate_credit_total": round(
            float(trial.get("duplicate_credit_total", 0.0) or 0.0), 8
        ),
    }
    return hash_payload(redacted)


def _trace_commitment(utility_input: dict[str, Any]) -> dict[str, Any]:
    trace = utility_input.get("retrieval_trace", {})
    steps = trace.get("steps", [])
    step_hashes: list[str] = []
    current_sources = {str(item) for item in trace.get("current_turn_source_ids", [])}
    prior_sources = {str(item) for item in trace.get("prior_turn_source_ids", [])}
    carried_sources = {str(item) for item in trace.get("carried_forward_source_ids", [])}
    for index, step in enumerate(steps, start=1):
        step_sources = {str(item) for item in step.get("source_ids", [])}
        if step.get("source_id"):
            step_sources.add(str(step.get("source_id")))
        if str(step.get("turn_scope", "current")) == "current":
            current_sources.update(step_sources)
        elif str(step.get("turn_scope", "")) == "prior":
            prior_sources.update(step_sources)
        step_hashes.append(
            hash_payload(
                {
                    "step_id": str(step.get("step_id") or f"step_{index}"),
                    "tool": str(step.get("tool", "")),
                    "action": str(step.get("action", "")),
                    "source_ids": sorted(step_sources),
                    "query_hash": str(
                        step.get("query_hash") or stable_hash(str(step.get("query", "")))
                    ),
                    "observation_hash": str(
                        step.get("observation_hash")
                        or stable_hash(str(step.get("observation", "")))
                    ),
                    "turn_scope": str(step.get("turn_scope", "current")),
                }
            )
        )
    payload = {
        "turn_id": str(trace.get("turn_id", "")),
        "current_turn_source_ids": sorted(current_sources),
        "prior_turn_source_ids": sorted(prior_sources),
        "carried_forward_source_ids": sorted(carried_sources),
        "step_hashes": step_hashes,
    }
    return {
        "turn_id": payload["turn_id"],
        "trace_hash": hash_payload(payload),
        "current_turn_source_ids": payload["current_turn_source_ids"],
        "prior_turn_source_ids": payload["prior_turn_source_ids"],
        "carried_forward_source_ids": payload["carried_forward_source_ids"],
        "step_count": len(step_hashes),
        "step_hashes": step_hashes,
    }


def _baseline_commitment(utility_input: dict[str, Any]) -> dict[str, Any]:
    baseline = utility_input.get("baseline", {})
    outcomes = []
    for outcome in baseline.get("claim_outcomes", []):
        outcomes.append(
            {
                "claim_id": str(outcome.get("claim_id", "")),
                "supported": bool(outcome.get("supported", False)),
                "confidence": round(
                    _clamp(float(outcome.get("confidence", 0.0) or 0.0)), 8
                ),
                "groundedness": round(
                    _clamp(float(outcome.get("groundedness", 0.0) or 0.0)), 8
                ),
                "cited_source_ids": sorted(_cited_source_ids(outcome)),
            }
        )
    return {
        "baseline_hash": hash_payload(outcomes),
        "claim_outcome_count": len(outcomes),
        "claim_outcome_hashes": [hash_payload(outcome) for outcome in outcomes],
    }


def _find_trial(
    trials: list[dict[str, Any]],
    operator: str,
    source_id: str,
    *,
    claim_id: str,
) -> dict[str, Any] | None:
    for trial in trials:
        if _trial_operator(trial) != operator:
            continue
        if source_id not in _trial_target_set(trial):
            continue
        outcomes = _outcomes_by_claim(trial)
        if claim_id in outcomes:
            return trial
    return None


def _find_synergy(
    trials: list[dict[str, Any]],
    source_id: str,
    *,
    claim_id: str,
    baseline_score: float,
) -> tuple[float, str]:
    best_score = 0.0
    best_trial_id = ""
    for trial in trials:
        if _trial_operator(trial) not in {"pair_remove", "multi_remove"}:
            continue
        targets = _trial_target_set(trial)
        if source_id not in targets or len(targets) < 2:
            continue
        outcome = _outcomes_by_claim(trial).get(claim_id)
        if outcome is None:
            continue
        divergence = _clamp(float(trial.get("trace_divergence", 0.0) or 0.0))
        score = _clamp((baseline_score - _claim_score(outcome)) + (0.15 * divergence))
        if score > best_score:
            best_score = score
            best_trial_id = str(trial.get("trial_id", ""))
    return best_score, best_trial_id


def _intervention_score(
    baseline_outcome: dict[str, Any],
    trial: dict[str, Any] | None,
    *,
    claim_id: str,
) -> float:
    if trial is None:
        return 0.0
    outcome = _outcomes_by_claim(trial).get(claim_id)
    if outcome is None:
        return 0.0
    baseline_score = _claim_score(baseline_outcome)
    trial_score = _claim_score(outcome)
    divergence = _clamp(float(trial.get("trace_divergence", 0.0) or 0.0))
    return _clamp((baseline_score - trial_score) + (0.15 * divergence))


def _duplicate_neutral(
    trial: dict[str, Any] | None,
    *,
    max_credit_inflation: float,
    max_trace_drift: float,
) -> tuple[bool, float, float]:
    if trial is None:
        return False, 1.0, 1.0
    inflation = max(0.0, float(trial.get("duplicate_credit_total", 1.0) or 0.0) - 1.0)
    trace_drift = _clamp(float(trial.get("trace_divergence", 0.0) or 0.0))
    return (
        inflation <= max_credit_inflation and trace_drift <= max_trace_drift,
        round(inflation, 8),
        round(trace_drift, 8),
    )


def _raw_private_values(utility_input: dict[str, Any]) -> list[str]:
    values: list[str] = []
    event = utility_input.get("event", {})
    for key in ("prompt_text", "response_text", "output_text"):
        value = str(event.get(key, ""))
        if len(value) >= 12:
            values.append(value)
    for claim in utility_input.get("claims", []):
        value = str(claim.get("claim_text", ""))
        if len(value) >= 12:
            values.append(value)
    for source in utility_input.get("candidate_sources", []):
        value = str(source.get("content", ""))
        if len(value) >= 12:
            values.append(value)
    for step in utility_input.get("retrieval_trace", {}).get("steps", []):
        for key in ("query", "observation"):
            value = str(step.get(key, ""))
            if len(value) >= 12:
                values.append(value)
    return values


def _no_raw_private_text(report: dict[str, Any], utility_input: dict[str, Any]) -> bool:
    rendered = canonical_json(report)
    return all(value not in rendered for value in _raw_private_values(utility_input))


def _utility_rows(
    utility_input: dict[str, Any],
    *,
    min_utility: float,
    max_duplicate_credit_inflation: float,
    max_duplicate_trace_drift: float,
) -> list[dict[str, Any]]:
    claims = _claim_rows(utility_input)
    source_rows = _source_rows(utility_input)
    source_ids = {row["source_id"] for row in source_rows}
    source_lookup = {row["source_id"]: row for row in source_rows}
    current_sources = set(_trace_commitment(utility_input)["current_turn_source_ids"])
    baseline_outcomes = _outcomes_by_claim(utility_input.get("baseline", {}))
    trials = [dict(trial) for trial in utility_input.get("perturbation_trials", [])]
    rows: list[dict[str, Any]] = []
    for claim in claims:
        claim_id = claim["claim_id"]
        baseline_outcome = baseline_outcomes.get(claim_id, {})
        baseline_score = _claim_score(baseline_outcome)
        cited_sources = _cited_source_ids(baseline_outcome) & source_ids
        for source_id in sorted(cited_sources):
            remove_trial = _find_trial(trials, "remove", source_id, claim_id=claim_id)
            replace_trial = _find_trial(trials, "replace", source_id, claim_id=claim_id)
            duplicate_trial = _find_trial(
                trials, "duplicate", source_id, claim_id=claim_id
            )
            remove_utility = _intervention_score(
                baseline_outcome, remove_trial, claim_id=claim_id
            )
            replace_utility = _intervention_score(
                baseline_outcome, replace_trial, claim_id=claim_id
            )
            synergy_utility, synergy_trial_id = _find_synergy(
                trials,
                source_id,
                claim_id=claim_id,
                baseline_score=baseline_score,
            )
            duplicate_ok, duplicate_inflation, duplicate_trace_drift = _duplicate_neutral(
                duplicate_trial,
                max_credit_inflation=max_duplicate_credit_inflation,
                max_trace_drift=max_duplicate_trace_drift,
            )
            utility_score = max(remove_utility, replace_utility, synergy_utility)
            in_current_turn_trace = source_id in current_sources
            failure_reasons: list[str] = []
            if not bool(baseline_outcome.get("supported", False)):
                failure_reasons.append("baseline_claim_not_supported")
            if claim["requires_current_turn_evidence"] and not in_current_turn_trace:
                failure_reasons.append("source_not_in_current_turn_trace")
            if utility_score < min_utility:
                failure_reasons.append("insufficient_causal_utility")
            if not duplicate_ok:
                failure_reasons.append("duplicate_trial_not_neutral")
            accepted = not failure_reasons
            if accepted and remove_utility >= min_utility:
                role = "necessary"
            elif accepted and replace_utility >= min_utility:
                role = "replace_sensitive"
            elif accepted and synergy_utility >= min_utility:
                role = "synergistic"
            elif accepted:
                role = "causal"
            elif "source_not_in_current_turn_trace" in failure_reasons:
                role = "context_drift"
            elif "duplicate_trial_not_neutral" in failure_reasons:
                role = "duplicate_overcredited"
            else:
                role = "spurious"
            rows.append(
                {
                    "claim_id": claim_id,
                    "source_id": source_id,
                    "creator_id": source_lookup[source_id]["creator_id"],
                    "baseline_cited": True,
                    "baseline_claim_supported": bool(
                        baseline_outcome.get("supported", False)
                    ),
                    "in_current_turn_trace": in_current_turn_trace,
                    "remove_trial_id": str(remove_trial.get("trial_id", ""))
                    if remove_trial
                    else "",
                    "replace_trial_id": str(replace_trial.get("trial_id", ""))
                    if replace_trial
                    else "",
                    "duplicate_trial_id": str(duplicate_trial.get("trial_id", ""))
                    if duplicate_trial
                    else "",
                    "synergy_trial_id": synergy_trial_id,
                    "remove_utility": round(remove_utility, 8),
                    "replace_utility": round(replace_utility, 8),
                    "synergy_utility": round(synergy_utility, 8),
                    "utility_score": round(utility_score, 8),
                    "duplicate_credit_inflation": duplicate_inflation,
                    "duplicate_trace_drift": duplicate_trace_drift,
                    "duplicate_neutral": duplicate_ok,
                    "utility_role": role,
                    "accepted": accepted,
                    "failure_reasons": failure_reasons,
                }
            )
    return rows


def _claim_attribution_rows(
    claims: list[dict[str, Any]],
    utility_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_claim: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in utility_rows:
        by_claim[row["claim_id"]].append(row)
    rows: list[dict[str, Any]] = []
    for claim in claims:
        claim_id = claim["claim_id"]
        claim_rows = by_claim.get(claim_id, [])
        accepted = [row for row in claim_rows if row["accepted"]]
        total_utility = sum(float(row["utility_score"]) for row in accepted)
        accepted_source_ids = [row["source_id"] for row in accepted]
        rejected_source_ids = [
            row["source_id"] for row in claim_rows if not row["accepted"]
        ]
        rows.append(
            {
                "claim_id": claim_id,
                "claim_hash": claim["claim_hash"],
                "accepted_source_ids": accepted_source_ids,
                "rejected_source_ids": rejected_source_ids,
                "causal_source_count": len(accepted_source_ids),
                "status": "causally_grounded" if accepted_source_ids else "escrow",
                "total_utility": round(total_utility, 8),
            }
        )
    return rows


def _economics(
    source_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, Any]],
    utility_rows: list[dict[str, Any]],
    *,
    gross_revenue: Decimal,
    creator_pool_rate: Decimal,
) -> dict[str, Any]:
    creator_pool = (gross_revenue * creator_pool_rate).quantize(MONEY_QUANT)
    claim_count = max(1, len(claim_rows))
    per_claim_pool = (creator_pool / Decimal(claim_count)).quantize(MONEY_QUANT)
    source_lookup = {row["source_id"]: row for row in source_rows}
    utility_by_claim: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in utility_rows:
        if row["accepted"]:
            utility_by_claim[row["claim_id"]].append(row)
    source_payouts: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    escrow = Decimal("0")
    allocated_claim_pools = Decimal("0")
    for claim_index, claim in enumerate(claim_rows, start=1):
        if claim_index == claim_count:
            claim_pool = creator_pool - allocated_claim_pools
        else:
            claim_pool = per_claim_pool
            allocated_claim_pools += claim_pool
        accepted = utility_by_claim.get(claim["claim_id"], [])
        utility_total = sum(Decimal(str(row["utility_score"])) for row in accepted)
        if not accepted or utility_total <= 0:
            escrow += claim_pool
            continue
        allocated = Decimal("0")
        for index, row in enumerate(accepted, start=1):
            if index == len(accepted):
                amount = claim_pool - allocated
            else:
                amount = (claim_pool * Decimal(str(row["utility_score"])) / utility_total).quantize(
                    MONEY_QUANT
                )
                allocated += amount
            source = source_lookup[row["source_id"]]
            source_payouts[(row["source_id"], source["creator_id"])] += amount
    payout_rows = [
        {
            "source_id": source_id,
            "creator_id": creator_id,
            "amount": _money(amount),
        }
        for (source_id, creator_id), amount in sorted(source_payouts.items())
    ]
    creator_rows: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in payout_rows:
        creator_rows[row["creator_id"]] += Decimal(row["amount"])
    total_paid = sum((Decimal(row["amount"]) for row in payout_rows), Decimal("0"))
    return {
        "gross_revenue": _money(gross_revenue),
        "creator_pool_rate": str(creator_pool_rate),
        "creator_pool": _money(creator_pool),
        "per_claim_pool": _money(per_claim_pool),
        "source_payouts": payout_rows,
        "creator_payouts": [
            {"creator_id": creator_id, "amount": _money(amount)}
            for creator_id, amount in sorted(creator_rows.items())
        ],
        "escrow": _money(escrow),
        "total_paid": _money(total_paid),
        "pool_conserved": total_paid + escrow == creator_pool,
    }


def make_evidence_utility_attribution_report(
    utility_input: dict[str, Any],
    *,
    gross_revenue: Decimal = Decimal("1.00"),
    creator_pool_rate: Decimal = DEFAULT_CREATOR_POOL_RATE,
    min_utility: float = DEFAULT_MIN_UTILITY,
    max_duplicate_credit_inflation: float = DEFAULT_MAX_DUPLICATE_CREDIT_INFLATION,
    max_duplicate_trace_drift: float = DEFAULT_MAX_DUPLICATE_TRACE_DRIFT,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a replayable report that credits sources by causal utility."""

    issued_at = created_at or now_iso()
    claims = _claim_rows(utility_input)
    sources = _source_rows(utility_input)
    trace = _trace_commitment(utility_input)
    baseline = _baseline_commitment(utility_input)
    utility_rows = _utility_rows(
        utility_input,
        min_utility=min_utility,
        max_duplicate_credit_inflation=max_duplicate_credit_inflation,
        max_duplicate_trace_drift=max_duplicate_trace_drift,
    )
    claim_attribution = _claim_attribution_rows(claims, utility_rows)
    economics = _economics(
        sources,
        claim_attribution,
        utility_rows,
        gross_revenue=gross_revenue,
        creator_pool_rate=creator_pool_rate,
    )
    accepted_source_ids = sorted(
        {row["source_id"] for row in utility_rows if row["accepted"]}
    )
    footer_sources = [
        {
            "source_id": row["source_id"],
            "work_id": row["work_id"],
            "creator_id": row["creator_id"],
            "title": row["title"],
            "source_uri": row["source_uri"],
            "content_hash": row["content_hash"],
        }
        for row in sources
        if row["source_id"] in accepted_source_ids
    ]
    footer_claims = [
        {
            "claim_id": row["claim_id"],
            "source_ids": row["accepted_source_ids"],
            "status": row["status"],
        }
        for row in claim_attribution
    ]
    trial_hashes = [_trial_hash(dict(trial)) for trial in utility_input.get("perturbation_trials", [])]
    claim_source_report = utility_input.get("claim_source_attribution_report", {})
    checks = {
        "all_claims_have_causal_sources": all(
            row["status"] == "causally_grounded" for row in claim_attribution
        ),
        "intervention_trials_cover_cited_sources": all(
            row["remove_trial_id"] or row["replace_trial_id"] or row["synergy_trial_id"]
            for row in utility_rows
        ),
        "no_prior_context_citation_drift": all(
            row["in_current_turn_trace"] for row in utility_rows if row["baseline_cited"]
        ),
        "duplicate_trials_do_not_inflate_credit": all(
            row["duplicate_neutral"] for row in utility_rows
        ),
        "no_rejected_cited_sources": all(row["accepted"] for row in utility_rows),
        "creator_pool_conserved": bool(economics["pool_conserved"]),
        "claim_source_report_bound": not claim_source_report
        or bool(claim_source_report.get("report_hash")),
    }
    report: dict[str, Any] = {
        "report_version": EVIDENCE_UTILITY_ATTRIBUTION_VERSION,
        "created_at": issued_at,
        "issuer": issuer,
        "event": _event_input(utility_input),
        "policy": {
            "profile": EVIDENCE_UTILITY_ATTRIBUTION_POLICY_VERSION,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "min_utility": min_utility,
            "max_duplicate_credit_inflation": max_duplicate_credit_inflation,
            "max_duplicate_trace_drift": max_duplicate_trace_drift,
        },
        "retrieval_trace": trace,
        "baseline": baseline,
        "perturbation_commitments": {
            "trial_count": len(trial_hashes),
            "trial_hashes": trial_hashes,
        },
        "claim_source_report_binding": {
            "report_hash": str(claim_source_report.get("report_hash", "")),
            "status": str(claim_source_report.get("summary", {}).get("status", "")),
            "target_certification_level": str(
                claim_source_report.get("summary", {}).get(
                    "target_certification_level", ""
                )
            ),
        },
        "sources": sources,
        "claims": claims,
        "utility_attribution": utility_rows,
        "claim_attribution": claim_attribution,
        "footer": {
            "footer_hash": hash_payload(
                {"source_rows": footer_sources, "claim_rows": footer_claims}
            ),
            "source_rows": footer_sources,
            "claim_rows": footer_claims,
            "source_row_count": len(footer_sources),
        },
        "economics": economics,
        "checks": checks,
        "schemas": {
            "evidence_utility_attribution_report": EVIDENCE_UTILITY_ATTRIBUTION_SCHEMA,
        },
    }
    checks["no_raw_private_text"] = _no_raw_private_text(report, utility_input)
    status = "ready" if all(checks.values()) else "failed"
    report["summary"] = {
        "status": status,
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "claim_count": len(claims),
        "causally_grounded_claim_count": sum(
            1 for row in claim_attribution if row["status"] == "causally_grounded"
        ),
        "escrow_claim_count": sum(
            1 for row in claim_attribution if row["status"] == "escrow"
        ),
        "source_count": len(sources),
        "accepted_source_count": len(accepted_source_ids),
        "rejected_source_count": len(
            {row["source_id"] for row in utility_rows if not row["accepted"]}
        ),
        "context_drift_rejection_count": sum(
            1 for row in utility_rows if row["utility_role"] == "context_drift"
        ),
        "duplicate_overcredit_rejection_count": sum(
            1 for row in utility_rows if row["utility_role"] == "duplicate_overcredited"
        ),
        "spurious_source_rejection_count": sum(
            1 for row in utility_rows if row["utility_role"] == "spurious"
        ),
        "trial_count": len(trial_hashes),
        "footer_hash": report["footer"]["footer_hash"],
    }
    report["report_hash"] = hash_payload(_hashable_report(report))
    if signing_secret:
        report["signature"] = sign_payload(report["report_hash"], signing_secret)
    return report


def validate_evidence_utility_attribution_report_shape(
    report: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for a causal utility report."""

    errors: list[str] = []
    if report.get("report_version") != EVIDENCE_UTILITY_ATTRIBUTION_VERSION:
        errors.append("invalid_report_version")
    policy = report.get("policy", {})
    if policy.get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("invalid_target_certification_level")
    for key in (
        "event",
        "retrieval_trace",
        "baseline",
        "perturbation_commitments",
        "sources",
        "claims",
        "utility_attribution",
        "claim_attribution",
        "footer",
        "economics",
        "checks",
        "summary",
        "schemas",
    ):
        if key not in report:
            errors.append(f"missing_{key}")
    if "evidence_utility_attribution_report" not in report.get("schemas", {}):
        errors.append("missing_schema_reference")
    footer = report.get("footer", {})
    if footer.get("footer_hash") != hash_payload(
        {
            "source_rows": footer.get("source_rows", []),
            "claim_rows": footer.get("claim_rows", []),
        }
    ):
        errors.append("footer_hash_not_reproducible")
    if report.get("report_hash") != hash_payload(_hashable_report(report)):
        errors.append("report_hash_not_reproducible")
    checks = report.get("checks", {})
    if not checks.get("creator_pool_conserved"):
        errors.append("creator_pool_not_conserved")
    if not checks.get("duplicate_trials_do_not_inflate_credit"):
        errors.append("duplicate_credit_inflation")
    if not checks.get("no_rejected_cited_sources", True):
        errors.append("rejected_cited_sources")
    if not checks.get("no_prior_context_citation_drift"):
        errors.append("prior_context_citation_drift")
    if not checks.get("intervention_trials_cover_cited_sources"):
        errors.append("missing_intervention_trials")
    if not checks.get("no_raw_private_text", True):
        errors.append("raw_private_text_leaked")
    return errors


def verify_evidence_utility_attribution_report(
    report: dict[str, Any],
    utility_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify a causal evidence utility report."""

    errors = validate_evidence_utility_attribution_report_shape(report)
    policy = report.get("policy", {})
    economics = report.get("economics", {})
    expected = make_evidence_utility_attribution_report(
        utility_input,
        gross_revenue=Decimal(str(economics.get("gross_revenue", "1.00"))),
        creator_pool_rate=Decimal(str(economics.get("creator_pool_rate", "0.55"))),
        min_utility=float(policy.get("min_utility", DEFAULT_MIN_UTILITY)),
        max_duplicate_credit_inflation=float(
            policy.get(
                "max_duplicate_credit_inflation",
                DEFAULT_MAX_DUPLICATE_CREDIT_INFLATION,
            )
        ),
        max_duplicate_trace_drift=float(
            policy.get("max_duplicate_trace_drift", DEFAULT_MAX_DUPLICATE_TRACE_DRIFT)
        ),
        issuer=str(report.get("issuer", DEFAULT_ISSUER)),
        created_at=str(report.get("created_at", "")) or None,
        signing_secret=signing_secret,
    )
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("report_hash_drift")
    if expected.get("summary") != report.get("summary"):
        errors.append("summary_drift")
    if expected.get("footer") != report.get("footer"):
        errors.append("footer_drift")
    if expected.get("utility_attribution") != report.get("utility_attribution"):
        errors.append("utility_attribution_drift")
    if signing_secret and expected.get("signature") != report.get("signature"):
        errors.append("signature_invalid")
    if not _no_raw_private_text(report, utility_input):
        errors.append("raw_private_text_leaked")
    return sorted(set(errors))
