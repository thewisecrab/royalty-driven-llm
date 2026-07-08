"""Counterfactual source-influence reports for credited RDLLM events."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from rdllm.engine import RoyaltyDrivenLLM
from rdllm.models import UsageEvent, Work
from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)
from rdllm.text import stable_hash

COUNTERFACTUAL_REPORT_VERSION = "rdllm-counterfactual-influence/v1"
DEFAULT_MIN_IMPACT_MARGIN = 0.05
MONEY_QUANT = Decimal("0.000001")


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY_QUANT))


def _work_hash(work: Work) -> str:
    return stable_hash(work.content)


def _empty_row(work_id: str) -> dict[str, Any]:
    return {
        "work_id": work_id,
        "creator_id": "",
        "chunk_id": "",
        "content_hash": "",
        "retrieval_score": 0.0,
        "text_match_score": 0.0,
        "output_support": 0.0,
        "claim_support_score": 0.0,
        "contribution_weight": 0.0,
        "payout": Decimal("0"),
        "source_reference_count": 0,
        "royalty_share_count": 0,
        "access_count": 0,
    }


def _source_rows(event: UsageEvent) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}

    def row(work_id: str) -> dict[str, Any]:
        if work_id not in rows:
            rows[work_id] = _empty_row(work_id)
        return rows[work_id]

    for hit in event.retrieval_hits:
        item = row(hit.chunk.work_id)
        item["creator_id"] = hit.chunk.creator_id
        item["chunk_id"] = hit.chunk.chunk_id
        item["content_hash"] = hit.chunk.content_hash
        item["retrieval_score"] = max(float(item["retrieval_score"]), float(hit.score))

    for match in event.text_matches:
        item = row(match.chunk.work_id)
        item["creator_id"] = match.chunk.creator_id
        item["chunk_id"] = match.chunk.chunk_id
        item["content_hash"] = match.chunk.content_hash
        item["text_match_score"] = max(float(item["text_match_score"]), float(match.score))

    for access in event.source_accesses:
        item = row(access.work_id)
        item["creator_id"] = access.creator_id
        item["chunk_id"] = access.chunk_id
        item["content_hash"] = access.content_hash
        item["access_count"] = int(item["access_count"]) + 1

    for reference in event.source_references:
        item = row(reference.work_id)
        item["creator_id"] = reference.creator_id
        item["chunk_id"] = reference.chunk_id
        item["content_hash"] = reference.content_hash
        item["retrieval_score"] = max(
            float(item["retrieval_score"]), float(reference.retrieval_score)
        )
        item["text_match_score"] = max(
            float(item["text_match_score"]), float(reference.text_match_score)
        )
        item["output_support"] = max(
            float(item["output_support"]), float(reference.output_support)
        )
        item["source_reference_count"] = int(item["source_reference_count"]) + 1

    for support in event.claim_support:
        if not support.work_id:
            continue
        item = row(support.work_id)
        item["chunk_id"] = support.chunk_id or item["chunk_id"]
        item["claim_support_score"] = max(
            float(item["claim_support_score"]), float(support.support_score)
        )

    for share in event.royalty_shares:
        if share.work_id.startswith("escrow:") or share.chunk_id.startswith("escrow:"):
            continue
        item = row(share.work_id)
        item["creator_id"] = share.creator_id
        item["chunk_id"] = share.chunk_id
        item["content_hash"] = share.content_hash
        item["contribution_weight"] = max(
            float(item["contribution_weight"]), float(share.contribution_weight)
        )
        item["payout"] = item["payout"] + share.payout
        item["royalty_share_count"] = int(item["royalty_share_count"]) + 1

    ranked: list[dict[str, Any]] = []
    for item in rows.values():
        score = (
            0.30 * float(item["text_match_score"])
            + 0.25 * float(item["output_support"])
            + 0.20 * float(item["retrieval_score"])
            + 0.15 * float(item["claim_support_score"])
            + 0.10 * float(item["contribution_weight"])
        )
        ranked.append(
            {
                "work_id": item["work_id"],
                "creator_id": item["creator_id"],
                "chunk_id": item["chunk_id"],
                "content_hash": item["content_hash"],
                "rank": 0,
                "decision_score": round(score, 8),
                "signals": {
                    "retrieval_score": round(float(item["retrieval_score"]), 8),
                    "text_match_score": round(float(item["text_match_score"]), 8),
                    "output_support": round(float(item["output_support"]), 8),
                    "claim_support_score": round(float(item["claim_support_score"]), 8),
                    "contribution_weight": round(float(item["contribution_weight"]), 8),
                    "payout": _money(item["payout"]),
                    "source_reference_count": int(item["source_reference_count"]),
                    "royalty_share_count": int(item["royalty_share_count"]),
                    "access_count": int(item["access_count"]),
                },
            }
        )

    ranked.sort(key=lambda item: (-float(item["decision_score"]), item["work_id"]))
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return ranked


def _row_by_work(event: UsageEvent) -> dict[str, dict[str, Any]]:
    return {row["work_id"]: row for row in _source_rows(event)}


def _subject_work_ids(event: UsageEvent) -> list[str]:
    work_ids = {
        share.work_id
        for share in event.royalty_shares
        if share.payout > Decimal("0")
        and not share.work_id.startswith("escrow:")
        and not share.chunk_id.startswith("escrow:")
        and not share.creator_id.endswith("_escrow")
    }
    work_ids.update(source.work_id for source in event.source_references)
    return sorted(work_ids)


def _engine_without_work(engine: RoyaltyDrivenLLM, work_id: str) -> RoyaltyDrivenLLM:
    return RoyaltyDrivenLLM(
        creators=list(engine.creators.values()),
        works=[work for work in engine.works.values() if work.work_id != work_id],
        creator_pool_rate=engine.creator_pool_rate,
        top_k=engine.top_k,
        jurisdiction=engine.jurisdiction,
        attestations=engine.attestations,
        registry_report=engine.registry_report,
        enforce_registry=engine.enforce_registry,
    )


def _private_strings(event: UsageEvent, engine: RoyaltyDrivenLLM) -> list[str]:
    values = [event.prompt, event.output, event.answer_text]
    values.extend(source.quote for source in event.source_references)
    values.extend(claim.evidence_text for claim in event.claim_support)
    values.extend(work.content for work in engine.works.values())
    return [value for value in values if len(value.strip()) >= 16]


def _best_substitute(ablated_event: UsageEvent) -> dict[str, Any]:
    rows = _source_rows(ablated_event)
    if not rows:
        return {
            "work_id": "",
            "creator_id": "",
            "rank": 0,
            "decision_score": 0.0,
            "content_hash": "",
        }
    row = rows[0]
    return {
        "work_id": row["work_id"],
        "creator_id": row["creator_id"],
        "rank": row["rank"],
        "decision_score": row["decision_score"],
        "content_hash": row["content_hash"],
    }


def make_counterfactual_report(
    event: UsageEvent,
    engine: RoyaltyDrivenLLM,
    *,
    min_impact_margin: float = DEFAULT_MIN_IMPACT_MARGIN,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create an intervention report by removing each credited source work."""

    original_rows = _row_by_work(event)
    interventions: list[dict[str, Any]] = []
    audit_errors: list[dict[str, Any]] = []
    for work_id in _subject_work_ids(event):
        work = engine.works.get(work_id)
        original = original_rows.get(work_id, _empty_row(work_id))
        reduced_engine = _engine_without_work(engine, work_id)
        ablated_event = reduced_engine.attribute_text(
            event.prompt,
            event.answer_text,
            gross_revenue=event.gross_revenue,
        )
        errors = reduced_engine.audit_event(ablated_event)
        if errors:
            audit_errors.append({"work_id": work_id, "errors": errors})
        ablated_rows = _row_by_work(ablated_event)
        substitute = _best_substitute(ablated_event)
        original_score = float(original.get("decision_score", 0.0))
        substitute_score = float(substitute.get("decision_score", 0.0))
        impact_margin = round(original_score - substitute_score, 8)
        role = (
            "decisive"
            if impact_margin >= min_impact_margin
            else "replaceable_or_redundant"
            if original_score > 0
            else "weak_or_uncredited"
        )
        source_absent = work_id not in ablated_rows
        payout_reallocated = (
            sum((share.payout for share in ablated_event.royalty_shares), Decimal("0"))
            == ablated_event.creator_pool
        )
        intervention = {
            "work_id": work_id,
            "creator_id": work.creator_id if work else "",
            "content_hash": _work_hash(work) if work else "",
            "baseline": {
                "rank": original.get("rank", 0),
                "decision_score": round(original_score, 8),
                "payout": original.get("signals", {}).get("payout", "0.000000")
                if "signals" in original
                else _money(original.get("payout", Decimal("0"))),
                "contribution_weight": original.get("signals", {}).get(
                    "contribution_weight",
                    round(float(original.get("contribution_weight", 0.0)), 8),
                )
                if "signals" in original
                else round(float(original.get("contribution_weight", 0.0)), 8),
            },
            "intervention": {
                "type": "remove_work",
                "removed_work_id": work_id,
                "ablation_event_id": ablated_event.event_id,
                "ablation_event_hash": ablated_event.event_hash,
                "source_absent_after_ablation": source_absent,
                "payout_reallocated_or_escrowed": payout_reallocated,
                "audit_errors": errors,
            },
            "best_substitute": substitute,
            "impact": {
                "impact_margin": impact_margin,
                "min_required_margin": round(float(min_impact_margin), 8),
                "role": role,
                "passes_margin": impact_margin >= min_impact_margin,
                "replacement_pressure": round(substitute_score, 8),
            },
        }
        intervention["intervention_hash"] = hash_payload(intervention)
        interventions.append(intervention)

    decisive_count = len(
        [item for item in interventions if item["impact"]["role"] == "decisive"]
    )
    weak_count = len(
        [item for item in interventions if item["impact"]["role"] != "decisive"]
    )
    average_margin = (
        sum(float(item["impact"]["impact_margin"]) for item in interventions)
        / len(interventions)
        if interventions
        else 0.0
    )
    all_absent = all(
        item["intervention"]["source_absent_after_ablation"] for item in interventions
    )
    report = {
        "report_version": COUNTERFACTUAL_REPORT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "event": {
            "event_id": event.event_id,
            "event_hash": event.event_hash,
            "creator_pool": _money(event.creator_pool),
            "subject_work_count": len(interventions),
        },
        "policy": {
            "profile": "rdllm-counterfactual-source-influence/v1",
            "intervention": "remove_credited_work",
            "min_impact_margin": round(float(min_impact_margin), 8),
            "same_prompt_and_answer_replayed": True,
            "event_text_committed_not_disclosed": True,
        },
        "baseline_sources": _source_rows(event),
        "interventions": interventions,
        "commitments": {
            "event_hash": event.event_hash,
            "baseline_source_root": hash_payload(_source_rows(event)),
            "intervention_root": hash_payload(interventions),
            "ablation_event_root": hash_payload(
                [
                    item["intervention"]["ablation_event_hash"]
                    for item in interventions
                ]
            ),
        },
        "summary": {
            "status": "ready" if not audit_errors and all_absent else "failed",
            "subject_work_count": len(interventions),
            "decisive_source_count": decisive_count,
            "replaceable_or_weak_source_count": weak_count,
            "average_impact_margin": round(average_margin, 8),
            "all_sources_counterfactually_removed": all_absent,
            "audit_error_count": len(audit_errors),
            "min_impact_margin": round(float(min_impact_margin), 8),
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "claim_evidence_text_disclosed": False,
            "report_uses_hashes_scores_and_work_ids": True,
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


def validate_counterfactual_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "event",
        "policy",
        "baseline_sources",
        "interventions",
        "commitments",
        "summary",
        "privacy",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing counterfactual report field: {key}")
    if errors:
        return errors
    if report.get("report_version") != COUNTERFACTUAL_REPORT_VERSION:
        errors.append("counterfactual report version is unsupported")
    for intervention in report.get("interventions", []):
        for key in ("work_id", "baseline", "intervention", "best_substitute", "impact", "intervention_hash"):
            if key not in intervention:
                errors.append(f"missing counterfactual intervention field: {key}")
    return errors


def verify_counterfactual_report(
    report: dict[str, Any],
    event: UsageEvent,
    engine: RoyaltyDrivenLLM,
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify a counterfactual source-influence report."""

    errors = validate_counterfactual_report_shape(report)
    if errors:
        return errors

    if report.get("event", {}).get("event_hash") != event.event_hash:
        errors.append("counterfactual report event hash does not match event")

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("counterfactual report hash is not reproducible")

    expected = make_counterfactual_report(
        event,
        engine,
        min_impact_margin=float(
            report.get("policy", {}).get(
                "min_impact_margin", DEFAULT_MIN_IMPACT_MARGIN
            )
        ),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "event",
        "policy",
        "baseline_sources",
        "interventions",
        "commitments",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"counterfactual report {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("counterfactual report hash does not match replay")

    rendered = canonical_json(report)
    for value in _private_strings(event, engine):
        if value in rendered:
            errors.append("counterfactual report leaks private prompt, answer, or source text")
            break

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("counterfactual report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("counterfactual report signature is invalid")

    return errors
