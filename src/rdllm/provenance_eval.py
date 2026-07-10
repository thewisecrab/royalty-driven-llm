"""Portable provenance evaluation reports for source-attribution quality."""

from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from rdllm.models import UsageEvent, Work
from rdllm.receipts import (
    DEFAULT_ISSUER,
    canonical_json,
    hash_payload,
    now_iso,
    sign_payload,
)

PROVENANCE_EVALUATION_VERSION = "rdllm-provenance-evaluation/v1"
DEFAULT_PROVIDER = "provider:unspecified"
DEFAULT_MODEL_ID = "model:unspecified"
DEFAULT_MODEL_VERSION = "unknown"


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _work_map(works: dict[str, Work] | list[Work]) -> dict[str, Work]:
    if isinstance(works, dict):
        return works
    return {work.work_id: work for work in works}


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _private_strings(engine: Any, benchmark_cases: list[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    works = _work_map(engine.works)
    values.extend(work.content for work in works.values())
    for case in benchmark_cases:
        values.append(str(case.get("prompt", "")))
        values.append(str(case.get("output", "")))
    return [value for value in values if len(value.strip()) >= 16]


def _case_input(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": str(case.get("case_id", "")),
        "scenario": str(case.get("scenario", "unspecified")),
        "prompt_hash": hash_payload(str(case.get("prompt", ""))),
        "output_hash": hash_payload(str(case.get("output", ""))),
        "expected_work_ids": sorted(str(item) for item in case.get("expected_work_ids", [])),
        "forbidden_work_ids": sorted(str(item) for item in case.get("forbidden_work_ids", [])),
        "expected_upstream_work_ids": sorted(
            str(item) for item in case.get("expected_upstream_work_ids", [])
        ),
        "expect_escrow": bool(case.get("expect_escrow", False)),
        "require_grounding": bool(
            case.get("require_grounding", bool(case.get("expected_work_ids", [])))
        ),
    }


def load_provenance_benchmark(path: str | Path) -> list[dict[str, Any]]:
    """Load benchmark cases from JSON.

    The file may either be a list of cases or an object with a `cases` list. Cases
    intentionally keep prompt/output text outside the public report; the report
    commits only to hashes.
    """

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [dict(item) for item in data]
    return [dict(item) for item in data.get("cases", [])]


def _empty_source_row(work_id: str) -> dict[str, Any]:
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


def _ranked_sources(event: UsageEvent) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}

    def row(work_id: str) -> dict[str, Any]:
        if work_id not in rows:
            rows[work_id] = _empty_source_row(work_id)
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
        item["payout"] = _decimal(item["payout"]) + share.payout
        item["royalty_share_count"] = int(item["royalty_share_count"]) + 1

    ranked = []
    for item in rows.values():
        decision_score = (
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
                "decision_score": round(decision_score, 8),
                "signals": {
                    "retrieval_score": round(float(item["retrieval_score"]), 8),
                    "text_match_score": round(float(item["text_match_score"]), 8),
                    "output_support": round(float(item["output_support"]), 8),
                    "claim_support_score": round(float(item["claim_support_score"]), 8),
                    "contribution_weight": round(float(item["contribution_weight"]), 8),
                    "payout": str(_decimal(item["payout"]).quantize(Decimal("0.000001"))),
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


def _rank_map(ranked_sources: list[dict[str, Any]]) -> dict[str, int]:
    return {str(item["work_id"]): int(item["rank"]) for item in ranked_sources}


def _case_report(engine: Any, case: dict[str, Any]) -> dict[str, Any]:
    case_input = _case_input(case)
    event = engine.attribute_text(
        str(case.get("prompt", "")),
        str(case.get("output", "")),
        gross_revenue=case.get("gross_revenue", "1.00"),
    )
    audit_errors = engine.audit_event(event)
    ranked = _ranked_sources(event)
    ranks = _rank_map(ranked)
    expected = set(case_input["expected_work_ids"])
    forbidden = set(case_input["forbidden_work_ids"])
    upstream = set(case_input["expected_upstream_work_ids"])
    visible_or_paid = {
        str(item["work_id"])
        for item in ranked
        if item["signals"]["source_reference_count"] > 0
        or item["signals"]["royalty_share_count"] > 0
    }
    paid = {
        str(item["work_id"])
        for item in ranked
        if _decimal(item["signals"]["payout"]) > Decimal("0")
    }
    top1 = ranked[0]["work_id"] if ranked else ""
    expected_best_rank = min((ranks[item] for item in expected if item in ranks), default=0)
    forbidden_best_rank = min((ranks[item] for item in forbidden if item in ranks), default=0)
    escrow_payout = sum(
        (
            share.payout
            for share in event.royalty_shares
            if share.chunk_id.startswith("escrow:")
            or share.creator_id.endswith("_escrow")
        ),
        Decimal("0"),
    )
    claim_count = len(event.claim_support)
    supported_claim_count = len([claim for claim in event.claim_support if claim.supported])
    grounding_verified = (
        event.grounding_quality.get("verdict") == "verified"
        or (claim_count > 0 and claim_count == supported_claim_count)
    )
    attribution_gap_closed = event.attribution_gap.get("verdict") in {"closed", ""}
    if case_input["expect_escrow"] and escrow_payout >= event.creator_pool:
        attribution_gap_closed = True
    expected_recall = (
        round(len(expected & visible_or_paid) / len(expected), 8) if expected else 1.0
    )
    precision = (
        round(len(paid & expected) / len(paid), 8)
        if paid and expected
        else (1.0 if not paid or case_input["expect_escrow"] else 0.0)
    )
    decoy_margin = 0
    if expected_best_rank and forbidden_best_rank:
        decoy_margin = forbidden_best_rank - expected_best_rank

    checks = {
        "audit_clean": not audit_errors,
        "top1_expected": (not expected and not ranked) or top1 in expected,
        "expected_visible_or_paid": expected.issubset(visible_or_paid),
        "expected_paid": case_input["expect_escrow"] or expected.issubset(paid),
        "forbidden_not_top1": top1 not in forbidden,
        "forbidden_ranked_below_expected": (
            not forbidden
            or not forbidden_best_rank
            or (bool(expected_best_rank) and forbidden_best_rank > expected_best_rank)
        ),
        "expected_upstream_visible_or_paid": upstream.issubset(visible_or_paid),
        "grounding_verified": grounding_verified or not case_input["require_grounding"],
        "attribution_gap_closed": attribution_gap_closed,
        "escrow_expected_pool": (
            escrow_payout >= event.creator_pool if case_input["expect_escrow"] else True
        ),
    }
    errors = [name for name, passed in checks.items() if not passed]
    status = "passed" if not errors else "failed"
    return {
        "case_id": case_input["case_id"],
        "scenario": case_input["scenario"],
        "case_input": case_input,
        "event": {
            "event_id": event.event_id,
            "event_hash": event.event_hash,
            "creator_pool": str(event.creator_pool.quantize(Decimal("0.000001"))),
            "source_count": len(event.source_references),
            "claim_count": claim_count,
            "supported_claim_count": supported_claim_count,
            "escrow_payout": str(escrow_payout.quantize(Decimal("0.000001"))),
        },
        "ranked_sources": ranked,
        "checks": checks,
        "metrics": {
            "expected_recall": expected_recall,
            "paid_source_precision": precision,
            "expected_best_rank": expected_best_rank,
            "forbidden_best_rank": forbidden_best_rank,
            "decoy_rank_margin": decoy_margin,
            "grounding_quality_score": event.grounding_quality.get("overall_score"),
        },
        "audit_errors": audit_errors,
        "errors": errors,
        "status": status,
    }


def _summary(case_reports: list[dict[str, Any]]) -> dict[str, Any]:
    case_count = len(case_reports)
    passed = len([case for case in case_reports if case["status"] == "passed"])
    failed = case_count - passed
    expected_recalls = [
        float(case["metrics"]["expected_recall"]) for case in case_reports
    ]
    precisions = [
        float(case["metrics"]["paid_source_precision"]) for case in case_reports
    ]
    top1_cases = [
        case
        for case in case_reports
        if case["case_input"]["expected_work_ids"]
        and not case["case_input"]["expect_escrow"]
    ]
    decoy_cases = [
        case for case in case_reports if case["case_input"]["forbidden_work_ids"]
    ]
    escrow_cases = [case for case in case_reports if case["case_input"]["expect_escrow"]]
    grounding_cases = [
        case for case in case_reports if case["case_input"]["require_grounding"]
    ]
    top1_accuracy = (
        len([case for case in top1_cases if case["checks"]["top1_expected"]])
        / len(top1_cases)
        if top1_cases
        else 1.0
    )
    decoy_resistance = (
        len(
            [
                case
                for case in decoy_cases
                if case["checks"]["forbidden_ranked_below_expected"]
                and case["checks"]["forbidden_not_top1"]
            ]
        )
        / len(decoy_cases)
        if decoy_cases
        else 1.0
    )
    escrow_accuracy = (
        len([case for case in escrow_cases if case["checks"]["escrow_expected_pool"]])
        / len(escrow_cases)
        if escrow_cases
        else 1.0
    )
    grounding_rate = (
        len([case for case in grounding_cases if case["checks"]["grounding_verified"]])
        / len(grounding_cases)
        if grounding_cases
        else 1.0
    )
    score = round(passed / case_count, 8) if case_count else 0.0
    return {
        "status": "passed" if case_count and failed == 0 else "failed",
        "case_count": case_count,
        "passed": passed,
        "failed": failed,
        "score": score,
        "mean_expected_recall": round(sum(expected_recalls) / case_count, 8)
        if case_count
        else 0.0,
        "mean_paid_source_precision": round(sum(precisions) / case_count, 8)
        if case_count
        else 0.0,
        "top1_accuracy": round(top1_accuracy, 8),
        "decoy_resistance_rate": round(decoy_resistance, 8),
        "escrow_accuracy": round(escrow_accuracy, 8),
        "grounding_verified_rate": round(grounding_rate, 8),
    }


def make_provenance_evaluation_report(
    engine: Any,
    benchmark_cases: list[dict[str, Any]],
    *,
    issuer: str = DEFAULT_ISSUER,
    provider: str = DEFAULT_PROVIDER,
    model_id: str = DEFAULT_MODEL_ID,
    model_version: str = DEFAULT_MODEL_VERSION,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Evaluate source-attribution quality against portable benchmark cases."""

    case_reports = [_case_report(engine, case) for case in benchmark_cases]
    case_inputs = [_case_input(case) for case in benchmark_cases]
    report = {
        "evaluation_version": PROVENANCE_EVALUATION_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "provider": {
            "id": provider,
            "model_id": model_id,
            "model_version": model_version,
        },
        "benchmark": {
            "profile": "rdllm-provenance-benchmark/v1",
            "case_count": len(case_inputs),
            "case_root": hash_payload(case_inputs),
            "coverage": {
                "clean_source": any(
                    case["scenario"] == "clean_source" for case in case_inputs
                ),
                "paraphrase": any(
                    case["scenario"] == "paraphrase" for case in case_inputs
                ),
                "hard_decoy": any(
                    case["scenario"] == "hard_decoy" for case in case_inputs
                ),
                "unattributed_escrow": any(
                    case["scenario"] == "unattributed_escrow" for case in case_inputs
                ),
                "derivative_lineage": any(
                    case["scenario"] == "derivative_lineage" for case in case_inputs
                ),
            },
        },
        "summary": _summary(case_reports),
        "cases": case_reports,
        "evidence_roots": {
            "event_hash_root": hash_payload(
                [case["event"]["event_hash"] for case in case_reports]
            ),
            "ranked_source_root": hash_payload(
                [case["ranked_sources"] for case in case_reports]
            ),
            "case_result_root": hash_payload(
                [
                    {
                        "case_id": case["case_id"],
                        "status": case["status"],
                        "checks": case["checks"],
                        "metrics": case["metrics"],
                    }
                    for case in case_reports
                ]
            ),
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "answer_text_disclosed": False,
            "source_text_disclosed": False,
            "claim_evidence_text_disclosed": False,
            "benchmark_inputs_disclosed_as_hashes": True,
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


def validate_provenance_evaluation_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "evaluation_version",
        "issuer",
        "created_at",
        "provider",
        "benchmark",
        "summary",
        "cases",
        "evidence_roots",
        "privacy",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing provenance evaluation field: {key}")
    if errors:
        return errors
    if report.get("evaluation_version") != PROVENANCE_EVALUATION_VERSION:
        errors.append("provenance evaluation version is unsupported")
    for case in report.get("cases", []):
        for key in ("case_id", "scenario", "case_input", "event", "ranked_sources", "checks", "metrics", "status"):
            if key not in case:
                errors.append(f"missing provenance evaluation case field: {key}")
    return errors


def verify_provenance_evaluation_report(
    engine: Any,
    report: dict[str, Any],
    benchmark_cases: list[dict[str, Any]],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify an evaluation report by replaying the benchmark cases."""

    errors = validate_provenance_evaluation_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("provenance evaluation hash is not reproducible")

    expected = make_provenance_evaluation_report(
        engine,
        benchmark_cases,
        issuer=report.get("issuer", DEFAULT_ISSUER),
        provider=report.get("provider", {}).get("id", DEFAULT_PROVIDER),
        model_id=report.get("provider", {}).get("model_id", DEFAULT_MODEL_ID),
        model_version=report.get("provider", {}).get(
            "model_version", DEFAULT_MODEL_VERSION
        ),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in ("provider", "benchmark", "summary", "cases", "evidence_roots", "privacy"):
        if expected.get(key) != report.get(key):
            errors.append(f"provenance evaluation {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("provenance evaluation report hash does not match replay")

    if report.get("privacy", {}).get("benchmark_inputs_disclosed_as_hashes") is not True:
        errors.append("provenance evaluation must disclose benchmark inputs as hashes")

    rendered = canonical_json(report)
    for value in _private_strings(engine, benchmark_cases):
        if value in rendered:
            errors.append("provenance evaluation leaks private benchmark or source text")
            break

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("provenance evaluation is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("provenance evaluation signature is invalid")

    return errors
