"""Parametric-memory attribution for foundation-model answers.

This layer covers the case that current-turn retrieval attribution cannot cover:
an answer claim appears to come from model weights or training memory. It binds
private source/probe evidence to a public hash-only report, rejects current
context contamination, rejects anti-documents, and allocates royalties only when
training-summary membership plus memory/influence evidence are replayable.
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
from rdllm.text import stable_hash, tokenize

PARAMETRIC_MEMORY_ATTRIBUTION_VERSION = "rdllm-parametric-memory-attribution/v1"
PARAMETRIC_MEMORY_ATTRIBUTION_SCHEMA = (
    "docs/schemas/parametric_memory_attribution_report.schema.json"
)
PARAMETRIC_MEMORY_POLICY_VERSION = "rdllm-parametric-memory-policy/v1"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L89"
DEFAULT_CREATOR_POOL_RATE = Decimal("0.55")
DEFAULT_MIN_SUPPORT = 0.34
DEFAULT_MIN_MEMORY = 0.45
DEFAULT_MIN_INFLUENCE = 0.25
DEFAULT_MIN_ANTI_MARGIN = 0.20
MONEY_QUANT = Decimal("0.000001")


def load_parametric_memory_input(path: str | Path) -> dict[str, Any]:
    """Load private inputs used to replay parametric-memory attribution."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY_QUANT))


def _clamp(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))


def _event_input(attribution_input: dict[str, Any]) -> dict[str, Any]:
    event = attribution_input.get("event", {})
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


def _source_content(source: dict[str, Any]) -> str:
    for key in ("content", "source_text", "body_text"):
        value = source.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _source_content_hash(source: dict[str, Any]) -> str:
    return str(source.get("content_hash") or stable_hash(_source_content(source)))


def _claim_rows(attribution_input: dict[str, Any]) -> list[dict[str, Any]]:
    claims = attribution_input.get("claims", [])
    if not claims:
        response = str(
            attribution_input.get("event", {}).get(
                "response_text",
                attribution_input.get("event", {}).get("output_text", ""),
            )
        )
        claims = [{"claim_id": "claim_1", "claim_text": response}]
    rows: list[dict[str, Any]] = []
    for index, claim in enumerate(claims, start=1):
        claim_text = str(claim.get("claim_text", ""))
        required_phrases = [str(item) for item in claim.get("required_evidence_phrases", [])]
        rows.append(
            {
                "claim_id": _claim_id(claim, index),
                "claim_hash": str(claim.get("claim_hash") or stable_hash(claim_text)),
                "expected_parametric_source_ids": sorted(
                    str(item)
                    for item in claim.get(
                        "expected_parametric_source_ids",
                        claim.get("expected_source_ids", []),
                    )
                ),
                "required_phrase_hashes": [
                    stable_hash(phrase) for phrase in required_phrases if phrase
                ],
                "requires_parametric_memory": bool(
                    claim.get("requires_parametric_memory", True)
                ),
            }
        )
    return rows


def _source_rows(attribution_input: dict[str, Any]) -> list[dict[str, Any]]:
    sources = attribution_input.get(
        "training_sources",
        attribution_input.get("candidate_sources", []),
    )
    rows: list[dict[str, Any]] = []
    for index, source in enumerate(sources, start=1):
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
                "source_role": str(
                    source.get("source_role", "training_candidate") or "training_candidate"
                ),
                "policy_allowed": bool(source.get("policy_allowed", True)),
            }
        )
    return rows


def _training_cohorts(training_summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(cohort.get("work_id", "")): dict(cohort)
        for cohort in training_summary.get("training_content", {}).get("cohorts", [])
        if cohort.get("work_id")
    }


def _training_summary_binding(training_summary: dict[str, Any]) -> dict[str, Any]:
    cohorts = training_summary.get("training_content", {}).get("cohorts", [])
    return {
        "summary_hash": str(training_summary.get("summary_hash", "")),
        "summary_version": str(training_summary.get("summary_version", "")),
        "provider_id": str(training_summary.get("provider", {}).get("id", "")),
        "model_id": str(training_summary.get("provider", {}).get("model_id", "")),
        "model_version": str(
            training_summary.get("provider", {}).get("model_version", "")
        ),
        "training_stage": str(
            training_summary.get("provider", {}).get("training_stage", "")
        ),
        "cohort_count": len(cohorts),
        "cohort_root": hash_payload(
            [
                {
                    "work_id": str(cohort.get("work_id", "")),
                    "content_hash": str(cohort.get("content_hash", "")),
                    "training_allowed": cohort.get("training_allowed") is True,
                    "training_value_root": str(cohort.get("training_value_root", "")),
                }
                for cohort in cohorts
            ]
        ),
    }


def _model_signal_binding(model_signal_report: dict[str, Any]) -> dict[str, Any]:
    summary = model_signal_report.get("summary", {})
    return {
        "report_hash": str(model_signal_report.get("report_hash", "")),
        "report_version": str(model_signal_report.get("report_version", "")),
        "status": str(summary.get("status", "")),
        "signal_count": int(summary.get("signal_count", 0) or 0),
        "accepted_signal_count": int(summary.get("accepted_signal_count", 0) or 0),
        "signal_row_root": str(
            model_signal_report.get("commitments", {}).get("signal_row_root", "")
        ),
    }


def _model_signal_scores(model_signal_report: dict[str, Any]) -> dict[str, float]:
    scores: dict[str, float] = defaultdict(float)
    for row in model_signal_report.get("signal_rows", []):
        if row.get("decision") != "accepted":
            continue
        work_id = str(row.get("work_id", ""))
        if not work_id:
            continue
        scores[work_id] = max(scores[work_id], _clamp(row.get("decision_score", 0.0)))
    return dict(scores)


def _source_training_rows(
    source_rows: list[dict[str, Any]],
    training_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    cohorts = _training_cohorts(training_summary)
    rows: list[dict[str, Any]] = []
    for source in source_rows:
        cohort = cohorts.get(source["work_id"], {})
        content_hash_matches = (
            bool(cohort)
            and str(cohort.get("content_hash", "")) == source["content_hash"]
        )
        rows.append(
            {
                "source_id": source["source_id"],
                "work_id": source["work_id"],
                "creator_id": source["creator_id"],
                "source_role": source["source_role"],
                "training_summary_member": bool(cohort),
                "training_allowed": cohort.get("training_allowed") is True,
                "content_hash_matches_training_summary": content_hash_matches,
                "policy_allowed": source["policy_allowed"],
                "training_value_root": str(cohort.get("training_value_root", "")),
            }
        )
    return rows


def _required_phrase_support(
    claim: dict[str, Any],
    source: dict[str, Any],
    attribution_input: dict[str, Any],
) -> float:
    raw_claim = next(
        (
            item
            for item in attribution_input.get("claims", [])
            if _claim_id(item, 0) == claim["claim_id"]
        ),
        {},
    )
    raw_source = next(
        (
            item
            for item in attribution_input.get(
                "training_sources",
                attribution_input.get("candidate_sources", []),
            )
            if _source_id(item, 0) == source["source_id"]
        ),
        {},
    )
    content = _source_content(raw_source).lower()
    required_phrases = [
        str(item).lower()
        for item in raw_claim.get("required_evidence_phrases", [])
        if str(item).strip()
    ]
    phrase_score = 0.0
    if required_phrases:
        phrase_hits = sum(1 for phrase in required_phrases if phrase in content)
        phrase_score = phrase_hits / len(required_phrases)
    claim_tokens = set(tokenize(str(raw_claim.get("claim_text", "")).lower()))
    source_tokens = set(tokenize(content))
    overlap_score = (
        len(claim_tokens & source_tokens) / len(claim_tokens)
        if claim_tokens
        else 0.0
    )
    return round(_clamp((0.65 * phrase_score) + (0.35 * overlap_score)), 8)


def _probe_operator(probe: dict[str, Any]) -> str:
    return str(probe.get("operator", probe.get("probe_type", ""))).lower().strip()


def _probe_target_sources(probe: dict[str, Any]) -> set[str]:
    targets = {str(item) for item in probe.get("target_source_ids", [])}
    if probe.get("target_source_id"):
        targets.add(str(probe.get("target_source_id")))
    return targets


def _probe_claim_ids(probe: dict[str, Any]) -> set[str]:
    claim_ids = {str(item) for item in probe.get("claim_ids", [])}
    if probe.get("claim_id"):
        claim_ids.add(str(probe.get("claim_id")))
    return claim_ids


def _probe_score_for_source(probe: dict[str, Any], source_id: str) -> float:
    scores = probe.get("attribution_scores", {})
    if isinstance(scores, dict) and source_id in scores:
        return _clamp(scores.get(source_id, 0.0))
    if source_id in _probe_target_sources(probe):
        for key in ("source_score", "target_score", "attribution_score"):
            if key in probe:
                return _clamp(probe.get(key, 0.0))
    return 0.0


def _memory_probe_score(
    probes: list[dict[str, Any]],
    *,
    claim_id: str,
    source_id: str,
) -> float:
    best = 0.0
    for probe in probes:
        if _probe_operator(probe) not in {
            "memory_recall",
            "parametric_recall",
            "paraphrase_recall",
            "probabilistic_token_attribution",
        }:
            continue
        if claim_id not in _probe_claim_ids(probe):
            continue
        if source_id not in _probe_target_sources(probe):
            continue
        supported = 1.0 if bool(probe.get("claim_supported", True)) else 0.0
        confidence = _clamp(probe.get("confidence", 0.0))
        attribution = _probe_score_for_source(probe, source_id)
        best = max(best, _clamp((0.35 * supported) + (0.35 * confidence) + (0.30 * attribution)))
    return round(best, 8)


def _influence_probe_score(
    probes: list[dict[str, Any]],
    *,
    claim_id: str,
    source_id: str,
) -> float:
    best = 0.0
    for probe in probes:
        if _probe_operator(probe) not in {
            "source_ablation",
            "influence_probe",
            "cohort_suppression",
            "counterfactual_suppression",
        }:
            continue
        if claim_id not in _probe_claim_ids(probe):
            continue
        if source_id not in _probe_target_sources(probe):
            continue
        delta = _clamp(
            probe.get(
                "influence_delta",
                probe.get("score_drop", probe.get("confidence_drop", 0.0)),
            )
        )
        attribution = _probe_score_for_source(probe, source_id)
        best = max(best, _clamp(max(delta, attribution)))
    return round(best, 8)


def _anti_source_margin(
    probes: list[dict[str, Any]],
    *,
    claim_id: str,
    source_id: str,
    anti_source_ids: set[str],
) -> float:
    if not anti_source_ids:
        return 1.0
    best_target = 0.0
    best_anti = 0.0
    for probe in probes:
        if _probe_operator(probe) not in {"anti_source", "anti_document", "hard_negative"}:
            continue
        if claim_id not in _probe_claim_ids(probe):
            continue
        best_target = max(best_target, _probe_score_for_source(probe, source_id))
        for anti_source_id in anti_source_ids:
            best_anti = max(best_anti, _probe_score_for_source(probe, anti_source_id))
    if best_target == 0.0 and best_anti == 0.0:
        return 0.0
    return round(best_target - best_anti, 8)


def _current_context_sources(attribution_input: dict[str, Any]) -> set[str]:
    event = attribution_input.get("event", {})
    trace = attribution_input.get("retrieval_trace", {})
    sources = {str(item) for item in event.get("current_turn_source_ids", [])}
    sources.update(str(item) for item in trace.get("current_turn_source_ids", []))
    for probe in attribution_input.get("memory_probes", attribution_input.get("probes", [])):
        if _probe_operator(probe) != "context_contamination":
            continue
        sources.update(str(item) for item in probe.get("current_context_source_ids", []))
        sources.update(_probe_target_sources(probe))
    return sources


def _probe_hash(probe: dict[str, Any]) -> str:
    score_items = probe.get("attribution_scores", {})
    if not isinstance(score_items, dict):
        score_items = {}
    redacted = {
        "probe_id": str(probe.get("probe_id", "")),
        "operator": _probe_operator(probe),
        "claim_ids": sorted(_probe_claim_ids(probe)),
        "target_source_ids": sorted(_probe_target_sources(probe)),
        "anti_source_ids": sorted(str(item) for item in probe.get("anti_source_ids", [])),
        "claim_supported": bool(probe.get("claim_supported", False)),
        "confidence": round(_clamp(probe.get("confidence", 0.0)), 8),
        "influence_delta": round(
            _clamp(
                probe.get(
                    "influence_delta",
                    probe.get("score_drop", probe.get("confidence_drop", 0.0)),
                )
            ),
            8,
        ),
        "attribution_scores": {
            str(key): round(_clamp(value), 8)
            for key, value in sorted(score_items.items())
        },
        "current_context_source_ids": sorted(
            str(item) for item in probe.get("current_context_source_ids", [])
        ),
    }
    return hash_payload(redacted)


def _probe_commitments(attribution_input: dict[str, Any]) -> dict[str, Any]:
    probes = attribution_input.get("memory_probes", attribution_input.get("probes", []))
    probe_hashes = [_probe_hash(dict(probe)) for probe in probes]
    return {
        "probe_count": len(probe_hashes),
        "probe_hashes": probe_hashes,
        "probe_root": hash_payload(probe_hashes),
    }


def _raw_private_values(attribution_input: dict[str, Any]) -> list[str]:
    values: list[str] = []
    event = attribution_input.get("event", {})
    for key in ("prompt_text", "response_text", "output_text"):
        value = str(event.get(key, ""))
        if len(value) >= 12:
            values.append(value)
    for claim in attribution_input.get("claims", []):
        value = str(claim.get("claim_text", ""))
        if len(value) >= 12:
            values.append(value)
    for source in attribution_input.get(
        "training_sources",
        attribution_input.get("candidate_sources", []),
    ):
        value = _source_content(source)
        if len(value) >= 12:
            values.append(value)
    for probe in attribution_input.get("memory_probes", attribution_input.get("probes", [])):
        for key in ("prompt_text", "output_text", "probe_text", "completion_text"):
            value = str(probe.get(key, ""))
            if len(value) >= 12:
                values.append(value)
    return values


def _no_raw_private_text(report: dict[str, Any], attribution_input: dict[str, Any]) -> bool:
    rendered = canonical_json(report)
    return all(value not in rendered for value in _raw_private_values(attribution_input))


def _parametric_rows(
    attribution_input: dict[str, Any],
    *,
    min_support: float,
    min_memory: float,
    min_influence: float,
    min_anti_margin: float,
) -> list[dict[str, Any]]:
    claims = _claim_rows(attribution_input)
    sources = _source_rows(attribution_input)
    probes = [
        dict(probe)
        for probe in attribution_input.get("memory_probes", attribution_input.get("probes", []))
    ]
    training_summary = attribution_input.get("training_content_summary", {})
    training_rows = {
        row["source_id"]: row for row in _source_training_rows(sources, training_summary)
    }
    model_signal_scores = _model_signal_scores(
        attribution_input.get("model_signal_report", {})
    )
    current_context = _current_context_sources(attribution_input)
    anti_source_ids = {
        row["source_id"]
        for row in sources
        if str(row.get("source_role", "")).lower()
        in {"anti_source", "anti_document", "hard_negative"}
    }
    rows: list[dict[str, Any]] = []
    for claim in claims:
        expected = set(claim["expected_parametric_source_ids"])
        for source in sources:
            source_id = source["source_id"]
            if expected and source_id not in expected and source_id not in anti_source_ids:
                continue
            support_score = _required_phrase_support(claim, source, attribution_input)
            memory_score = _memory_probe_score(
                probes,
                claim_id=claim["claim_id"],
                source_id=source_id,
            )
            influence_score = _influence_probe_score(
                probes,
                claim_id=claim["claim_id"],
                source_id=source_id,
            )
            model_signal_score = model_signal_scores.get(source["work_id"], 0.0)
            anti_margin = _anti_source_margin(
                probes,
                claim_id=claim["claim_id"],
                source_id=source_id,
                anti_source_ids=anti_source_ids - {source_id},
            )
            training = training_rows.get(source_id, {})
            context_contaminated = source_id in current_context
            failure_reasons: list[str] = []
            if not claim["requires_parametric_memory"]:
                failure_reasons.append("claim_does_not_require_parametric_memory")
            if source_id not in expected and source_id in anti_source_ids:
                failure_reasons.append("source_marked_as_anti_document")
            if context_contaminated:
                failure_reasons.append("current_context_should_use_evidence_utility")
            if not training.get("training_summary_member"):
                failure_reasons.append("source_missing_from_training_summary")
            if not training.get("content_hash_matches_training_summary"):
                failure_reasons.append("content_hash_not_in_training_summary")
            if not training.get("training_allowed"):
                failure_reasons.append("training_not_allowed")
            if not training.get("policy_allowed", True):
                failure_reasons.append("source_policy_blocked")
            if support_score < min_support:
                failure_reasons.append("insufficient_source_support")
            if memory_score < min_memory:
                failure_reasons.append("insufficient_memory_recall_evidence")
            if max(influence_score, model_signal_score) < min_influence:
                failure_reasons.append("insufficient_influence_evidence")
            if anti_margin < min_anti_margin:
                failure_reasons.append("anti_document_margin_too_small")
            accepted = not failure_reasons
            attribution_score = _clamp(
                (0.25 * support_score)
                + (0.30 * memory_score)
                + (0.25 * max(influence_score, model_signal_score))
                + (0.20 * max(0.0, anti_margin))
            )
            if accepted and influence_score >= min_influence:
                decision = "accepted_parametric_influence"
            elif accepted:
                decision = "accepted_model_signal"
            elif context_contaminated:
                decision = "current_context_escrow"
            elif source_id in anti_source_ids:
                decision = "anti_document_rejected"
            else:
                decision = "parametric_memory_escrow"
            rows.append(
                {
                    "claim_id": claim["claim_id"],
                    "source_id": source_id,
                    "work_id": source["work_id"],
                    "creator_id": source["creator_id"],
                    "source_role": source["source_role"],
                    "training_summary_member": bool(training.get("training_summary_member")),
                    "training_allowed": bool(training.get("training_allowed")),
                    "content_hash_matches_training_summary": bool(
                        training.get("content_hash_matches_training_summary")
                    ),
                    "support_score": round(support_score, 8),
                    "memory_recall_score": round(memory_score, 8),
                    "influence_probe_score": round(influence_score, 8),
                    "model_signal_score": round(model_signal_score, 8),
                    "anti_source_margin": round(anti_margin, 8),
                    "current_context_contaminated": context_contaminated,
                    "attribution_score": round(attribution_score, 8),
                    "decision": decision,
                    "accepted": accepted,
                    "failure_reasons": failure_reasons,
                }
            )
    return rows


def _claim_attribution_rows(
    claims: list[dict[str, Any]],
    attribution_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_claim: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in attribution_rows:
        by_claim[row["claim_id"]].append(row)
    rows: list[dict[str, Any]] = []
    for claim in claims:
        claim_rows = by_claim.get(claim["claim_id"], [])
        accepted = [row for row in claim_rows if row["accepted"]]
        rejected = [row for row in claim_rows if not row["accepted"]]
        rows.append(
            {
                "claim_id": claim["claim_id"],
                "claim_hash": claim["claim_hash"],
                "accepted_source_ids": [row["source_id"] for row in accepted],
                "rejected_source_ids": [row["source_id"] for row in rejected],
                "parametric_source_count": len(accepted),
                "status": "parametric_grounded" if accepted else "escrow",
                "total_attribution_score": round(
                    sum(float(row["attribution_score"]) for row in accepted),
                    8,
                ),
            }
        )
    return rows


def _economics(
    claim_rows: list[dict[str, Any]],
    attribution_rows: list[dict[str, Any]],
    *,
    gross_revenue: Decimal,
    creator_pool_rate: Decimal,
) -> dict[str, Any]:
    creator_pool = (gross_revenue * creator_pool_rate).quantize(MONEY_QUANT)
    claim_count = max(1, len(claim_rows))
    per_claim_pool = (creator_pool / Decimal(claim_count)).quantize(MONEY_QUANT)
    accepted_by_claim: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in attribution_rows:
        if row["accepted"]:
            accepted_by_claim[row["claim_id"]].append(row)
    source_payouts: dict[tuple[str, str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    escrow = Decimal("0")
    allocated_claim_pools = Decimal("0")
    for claim_index, claim in enumerate(claim_rows, start=1):
        if claim_index == claim_count:
            claim_pool = creator_pool - allocated_claim_pools
        else:
            claim_pool = per_claim_pool
            allocated_claim_pools += claim_pool
        accepted = accepted_by_claim.get(claim["claim_id"], [])
        score_total = sum(Decimal(str(row["attribution_score"])) for row in accepted)
        if not accepted or score_total <= Decimal("0"):
            escrow += claim_pool
            continue
        allocated = Decimal("0")
        for index, row in enumerate(accepted, start=1):
            if index == len(accepted):
                amount = claim_pool - allocated
            else:
                amount = (
                    claim_pool
                    * Decimal(str(row["attribution_score"]))
                    / score_total
                ).quantize(MONEY_QUANT)
                allocated += amount
            source_payouts[(row["source_id"], row["work_id"], row["creator_id"])] += amount
    payout_rows = [
        {
            "source_id": source_id,
            "work_id": work_id,
            "creator_id": creator_id,
            "amount": _money(amount),
        }
        for (source_id, work_id, creator_id), amount in sorted(source_payouts.items())
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


def make_parametric_memory_attribution_report(
    attribution_input: dict[str, Any],
    *,
    gross_revenue: Decimal = Decimal("1.00"),
    creator_pool_rate: Decimal = DEFAULT_CREATOR_POOL_RATE,
    min_support: float = DEFAULT_MIN_SUPPORT,
    min_memory: float = DEFAULT_MIN_MEMORY,
    min_influence: float = DEFAULT_MIN_INFLUENCE,
    min_anti_margin: float = DEFAULT_MIN_ANTI_MARGIN,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a replayable report for training-memory source attribution."""

    issued_at = created_at or now_iso()
    claims = _claim_rows(attribution_input)
    sources = _source_rows(attribution_input)
    training_summary = attribution_input.get("training_content_summary", {})
    model_signal_report = attribution_input.get("model_signal_report", {})
    training_rows = _source_training_rows(sources, training_summary)
    attribution_rows = _parametric_rows(
        attribution_input,
        min_support=min_support,
        min_memory=min_memory,
        min_influence=min_influence,
        min_anti_margin=min_anti_margin,
    )
    claim_attribution = _claim_attribution_rows(claims, attribution_rows)
    economics = _economics(
        claim_attribution,
        attribution_rows,
        gross_revenue=gross_revenue,
        creator_pool_rate=creator_pool_rate,
    )
    accepted_source_ids = sorted(
        {row["source_id"] for row in attribution_rows if row["accepted"]}
    )
    footer_sources = [
        {
            "source_id": row["source_id"],
            "work_id": row["work_id"],
            "creator_id": row["creator_id"],
            "title": row["title"],
            "source_uri": row["source_uri"],
            "content_hash": row["content_hash"],
            "attribution_channel": "parametric_memory",
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
    checks = {
        "all_parametric_claims_attributed": all(
            row["status"] == "parametric_grounded" for row in claim_attribution
        ),
        "training_summary_bound": bool(
            _training_summary_binding(training_summary)["summary_hash"]
        ),
        "model_signal_or_probe_influence_bound": all(
            max(row["influence_probe_score"], row["model_signal_score"]) >= min_influence
            for row in attribution_rows
            if row["accepted"]
        ),
        "accepted_sources_in_training_summary": all(
            row["training_summary_member"]
            and row["content_hash_matches_training_summary"]
            for row in attribution_rows
            if row["accepted"]
        ),
        "accepted_sources_training_allowed": all(
            row["training_allowed"] for row in attribution_rows if row["accepted"]
        ),
        "anti_documents_rejected": all(
            not row["accepted"]
            for row in attribution_rows
            if row["source_role"] in {"anti_source", "anti_document", "hard_negative"}
        ),
        "no_current_context_contamination": all(
            not row["current_context_contaminated"]
            for row in attribution_rows
            if row["accepted"]
        ),
        "creator_pool_conserved": bool(economics["pool_conserved"]),
    }
    report: dict[str, Any] = {
        "report_version": PARAMETRIC_MEMORY_ATTRIBUTION_VERSION,
        "created_at": issued_at,
        "issuer": issuer,
        "event": _event_input(attribution_input),
        "policy": {
            "profile": PARAMETRIC_MEMORY_POLICY_VERSION,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "min_support": min_support,
            "min_memory": min_memory,
            "min_influence": min_influence,
            "min_anti_margin": min_anti_margin,
        },
        "training_summary_binding": _training_summary_binding(training_summary),
        "model_signal_binding": _model_signal_binding(model_signal_report),
        "probe_commitments": _probe_commitments(attribution_input),
        "sources": sources,
        "claims": claims,
        "source_training": training_rows,
        "parametric_attribution": attribution_rows,
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
            "parametric_memory_attribution_report": PARAMETRIC_MEMORY_ATTRIBUTION_SCHEMA,
        },
    }
    checks["no_raw_private_text"] = _no_raw_private_text(report, attribution_input)
    status = "ready" if all(checks.values()) else "failed"
    report["summary"] = {
        "status": status,
        "target_certification_level": TARGET_CERTIFICATION_LEVEL,
        "claim_count": len(claims),
        "parametric_grounded_claim_count": sum(
            1 for row in claim_attribution if row["status"] == "parametric_grounded"
        ),
        "escrow_claim_count": sum(
            1 for row in claim_attribution if row["status"] == "escrow"
        ),
        "source_count": len(sources),
        "accepted_source_count": len(accepted_source_ids),
        "rejected_source_count": len(
            {row["source_id"] for row in attribution_rows if not row["accepted"]}
        ),
        "anti_document_rejection_count": sum(
            1 for row in attribution_rows if row["decision"] == "anti_document_rejected"
        ),
        "context_contamination_rejection_count": sum(
            1 for row in attribution_rows if row["decision"] == "current_context_escrow"
        ),
        "training_summary_miss_count": sum(
            1
            for row in attribution_rows
            if "source_missing_from_training_summary" in row["failure_reasons"]
            or "content_hash_not_in_training_summary" in row["failure_reasons"]
        ),
        "probe_count": report["probe_commitments"]["probe_count"],
        "footer_hash": report["footer"]["footer_hash"],
    }
    report["report_hash"] = hash_payload(_hashable_report(report))
    if signing_secret:
        report["signature"] = sign_payload(report["report_hash"], signing_secret)
    return report


def validate_parametric_memory_attribution_report_shape(
    report: dict[str, Any],
) -> list[str]:
    """Return structural validation errors for a parametric-memory report."""

    errors: list[str] = []
    if report.get("report_version") != PARAMETRIC_MEMORY_ATTRIBUTION_VERSION:
        errors.append("invalid_report_version")
    policy = report.get("policy", {})
    if policy.get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("invalid_target_certification_level")
    for key in (
        "event",
        "training_summary_binding",
        "model_signal_binding",
        "probe_commitments",
        "sources",
        "claims",
        "source_training",
        "parametric_attribution",
        "claim_attribution",
        "footer",
        "economics",
        "checks",
        "summary",
        "schemas",
    ):
        if key not in report:
            errors.append(f"missing_{key}")
    if "parametric_memory_attribution_report" not in report.get("schemas", {}):
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
    if not checks.get("accepted_sources_in_training_summary"):
        errors.append("accepted_source_missing_training_summary")
    if not checks.get("accepted_sources_training_allowed"):
        errors.append("accepted_source_training_not_allowed")
    if not checks.get("anti_documents_rejected"):
        errors.append("anti_document_accepted")
    if not checks.get("no_current_context_contamination"):
        errors.append("current_context_contamination")
    if not checks.get("model_signal_or_probe_influence_bound"):
        errors.append("influence_evidence_missing")
    if not checks.get("no_raw_private_text", True):
        errors.append("raw_private_text_leaked")
    return errors


def verify_parametric_memory_attribution_report(
    report: dict[str, Any],
    attribution_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify a parametric-memory attribution report."""

    errors = validate_parametric_memory_attribution_report_shape(report)
    policy = report.get("policy", {})
    economics = report.get("economics", {})
    expected = make_parametric_memory_attribution_report(
        attribution_input,
        gross_revenue=Decimal(str(economics.get("gross_revenue", "1.00"))),
        creator_pool_rate=Decimal(str(economics.get("creator_pool_rate", "0.55"))),
        min_support=float(policy.get("min_support", DEFAULT_MIN_SUPPORT)),
        min_memory=float(policy.get("min_memory", DEFAULT_MIN_MEMORY)),
        min_influence=float(policy.get("min_influence", DEFAULT_MIN_INFLUENCE)),
        min_anti_margin=float(policy.get("min_anti_margin", DEFAULT_MIN_ANTI_MARGIN)),
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
    if expected.get("parametric_attribution") != report.get("parametric_attribution"):
        errors.append("parametric_attribution_drift")
    if signing_secret and expected.get("signature") != report.get("signature"):
        errors.append("signature_invalid")
    if not _no_raw_private_text(report, attribution_input):
        errors.append("raw_private_text_leaked")
    return sorted(set(errors))
