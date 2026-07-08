"""Citation and grounding quality evaluation for RDLLM events."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from rdllm.models import ClaimSupport, RoyaltyShare, SourceReference, UsageEvent
from rdllm.text import jaccard_similarity, stable_hash, tokenize

QUALITY_VERSION = "rdllm-grounding-quality/v1"
SOURCE_LABEL_RE = re.compile(r"^\[(S\d+)\]\s+", re.MULTILINE)
SPAN_HASH_RE = re.compile(r"span=([a-f0-9]{12})")
SUPPORT_SCORE_FLOOR = 0.75


def _mean(values: list[float], *, default: float = 0.0) -> float:
    if not values:
        return default
    return sum(values) / len(values)


def _round(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 8)


def _source_labels_in_output(output: str) -> list[str]:
    return SOURCE_LABEL_RE.findall(output)


def _span_prefixes_in_output(output: str) -> set[str]:
    return set(SPAN_HASH_RE.findall(output))


def _source_accessibility_score(sources: list[SourceReference]) -> tuple[float, list[str]]:
    if not sources:
        return 0.0, []

    issues: list[str] = []
    scores: list[float] = []
    for source in sources:
        checks = {
            "source_uri": bool(source.source_uri),
            "content_hash": bool(source.content_hash),
            "quote": bool(source.quote),
            "license": bool(source.license),
        }
        score = sum(1 for passed in checks.values() if passed) / len(checks)
        scores.append(score)
        for check, passed in checks.items():
            if not passed:
                issues.append(f"{source.label} missing {check}")
    return _round(_mean(scores)), issues


def _claim_relevance_score(claims: list[ClaimSupport]) -> float:
    supported_claims = [claim for claim in claims if claim.supported]
    if not supported_claims:
        return 0.0
    scores: list[float] = []
    for claim in supported_claims:
        overlap = jaccard_similarity(tokenize(claim.claim), tokenize(claim.evidence_text))
        scores.append(max(claim.support_score, overlap))
    return _round(_mean(scores))


def _fact_support_score(claims: list[ClaimSupport], span_prefixes: set[str]) -> tuple[float, list[str]]:
    if not claims:
        return 0.0, ["no claims were extracted"]

    issues: list[str] = []
    scores: list[float] = []
    for index, claim in enumerate(claims, start=1):
        if not claim.supported:
            scores.append(0.0)
            issues.append(f"C{index} unsupported")
            continue
        checks = {
            "source_label": bool(claim.source_label),
            "chunk_id": bool(claim.chunk_id),
            "evidence_text": bool(claim.evidence_text),
            "span_hash": bool(claim.evidence_span_hash),
            "support_score_floor": claim.support_score >= SUPPORT_SCORE_FLOOR,
            "span_in_footer": claim.evidence_span_hash[:12] in span_prefixes,
            "span_hash_reproducible": (
                bool(claim.evidence_text)
                and stable_hash(claim.evidence_text) == claim.evidence_span_hash
            ),
            "char_offsets": claim.evidence_start_char >= 0
            and claim.evidence_end_char >= claim.evidence_start_char,
        }
        score = sum(1 for passed in checks.values() if passed) / len(checks)
        scores.append(score)
        for check, passed in checks.items():
            if not passed:
                issues.append(f"C{index} missing {check}")
    return _round(_mean(scores)), issues


def _citation_integrity_score(
    output: str,
    sources: list[SourceReference],
    claims: list[ClaimSupport],
) -> tuple[float, list[str]]:
    source_labels = [source.label for source in sources]
    source_label_set = set(source_labels)
    footer_labels = _source_labels_in_output(output)
    span_prefixes = _span_prefixes_in_output(output)
    issues: list[str] = []
    checks: list[bool] = [
        footer_labels == source_labels,
        all(
            not claim.supported or claim.source_label in source_label_set
            for claim in claims
        ),
        all(
            not claim.supported
            or not claim.evidence_span_hash
            or claim.evidence_span_hash[:12] in span_prefixes
            for claim in claims
        ),
        len(set(source_labels)) == len(source_labels),
    ]
    if footer_labels != source_labels:
        issues.append("footer source labels do not match source references")
    for index, claim in enumerate(claims, start=1):
        if claim.supported and claim.source_label not in source_label_set:
            issues.append(f"C{index} uses unknown source label {claim.source_label}")
        if (
            claim.supported
            and claim.evidence_span_hash
            and claim.evidence_span_hash[:12] not in span_prefixes
        ):
            issues.append(f"C{index} evidence span hash missing from footer")
    if len(set(source_labels)) != len(source_labels):
        issues.append("duplicate source labels")
    return _round(sum(1 for check in checks if check) / len(checks)), issues


def _policy_alignment_score(
    grounding_report: dict[str, Any],
    policy_decisions: list[dict[str, Any]],
) -> tuple[float, list[str]]:
    denied = [decision for decision in policy_decisions if not decision.get("allowed")]
    policy_status = grounding_report.get("policy_status")
    issues: list[str] = []
    if denied and policy_status != "blocked":
        issues.append("policy denials exist but report is not blocked")
    if not denied and policy_status == "blocked":
        issues.append("policy report is blocked without denied decisions")
    if issues:
        return 0.0, issues
    return 1.0, []


def _payout_alignment_score(
    sources: list[SourceReference],
    shares: list[RoyaltyShare],
    grounding_report: dict[str, Any],
) -> tuple[float, list[str]]:
    if not shares:
        return 1.0, []

    issues: list[str] = []
    source_chunks = {source.chunk_id for source in sources}
    non_escrow = [
        share for share in shares if not share.chunk_id.startswith("escrow:")
    ]
    escrow = [share for share in shares if share.chunk_id.startswith("escrow:")]
    if non_escrow:
        missing = [
            share.chunk_id for share in non_escrow if share.chunk_id not in source_chunks
        ]
        if missing:
            issues.append(f"paid chunks are not visible sources: {', '.join(missing)}")
    if escrow and sources:
        issues.append("escrow share appears with visible source references")
    if grounding_report.get("policy_status") == "blocked":
        if not escrow or escrow[0].creator_id != "rights_conflict_escrow":
            issues.append("blocked event is not assigned to rights-conflict escrow")
    if grounding_report.get("registry_status") == "disputed":
        if not escrow or escrow[0].creator_id != "registry_dispute_escrow":
            issues.append("registry-disputed event is not assigned to registry-dispute escrow")
    if (
        not sources
        and grounding_report.get("policy_status") != "blocked"
        and grounding_report.get("registry_status") != "disputed"
    ):
        if not escrow or escrow[0].creator_id != "unattributed_escrow":
            issues.append("unattributed event is not assigned to unattributed escrow")
    return (0.0 if issues else 1.0), issues


def evaluate_grounding_quality(
    *,
    output: str,
    sources: list[SourceReference],
    claims: list[ClaimSupport],
    grounding_report: dict[str, Any],
    policy_decisions: list[dict[str, Any]],
    royalty_shares: list[RoyaltyShare],
) -> dict[str, Any]:
    """Evaluate whether source labels actually support claims and payouts."""

    if grounding_report.get("policy_status") == "blocked":
        payout_score, payout_issues = _payout_alignment_score(
            sources, royalty_shares, grounding_report
        )
        policy_score, policy_issues = _policy_alignment_score(
            grounding_report, policy_decisions
        )
        issues = payout_issues + policy_issues
        return {
            "quality_version": QUALITY_VERSION,
            "verdict": "blocked_by_policy" if not issues else "failed",
            "overall_score": _round(0.5 * policy_score + 0.5 * payout_score),
            "scores": {
                "source_accessibility": None,
                "citation_integrity": None,
                "evidence_relevance": None,
                "fact_support": None,
                "policy_alignment": _round(policy_score),
                "payout_alignment": _round(payout_score),
            },
            "summary": {
                "source_count": len(sources),
                "claim_count": len(claims),
                "supported_claims": sum(1 for claim in claims if claim.supported),
                "footer_source_count": len(_source_labels_in_output(output)),
                "footer_span_hash_count": len(_span_prefixes_in_output(output)),
            },
            "issues": issues,
            "policy": {
                "support_score_floor": SUPPORT_SCORE_FLOOR,
            },
        }

    if grounding_report.get("registry_status") == "disputed":
        payout_score, payout_issues = _payout_alignment_score(
            sources, royalty_shares, grounding_report
        )
        policy_score, policy_issues = _policy_alignment_score(
            grounding_report, policy_decisions
        )
        issues = payout_issues + policy_issues
        return {
            "quality_version": QUALITY_VERSION,
            "verdict": "blocked_by_registry" if not issues else "failed",
            "overall_score": _round(0.5 * policy_score + 0.5 * payout_score),
            "scores": {
                "source_accessibility": None,
                "citation_integrity": None,
                "evidence_relevance": None,
                "fact_support": None,
                "policy_alignment": _round(policy_score),
                "payout_alignment": _round(payout_score),
            },
            "summary": {
                "source_count": len(sources),
                "claim_count": len(claims),
                "supported_claims": sum(1 for claim in claims if claim.supported),
                "footer_source_count": len(_source_labels_in_output(output)),
                "footer_span_hash_count": len(_span_prefixes_in_output(output)),
                "registry_conflicts": grounding_report.get("registry_conflicts", 0),
            },
            "issues": issues,
        }

    payout_score, payout_issues = _payout_alignment_score(
        sources, royalty_shares, grounding_report
    )
    policy_score, policy_issues = _policy_alignment_score(
        grounding_report, policy_decisions
    )

    if not sources and not claims:
        issues = payout_issues + policy_issues
        return {
            "quality_version": QUALITY_VERSION,
            "verdict": "unattributed" if not issues else "failed",
            "overall_score": _round(0.5 * payout_score + 0.5 * policy_score),
            "scores": {
                "source_accessibility": 0.0,
                "citation_integrity": 1.0,
                "evidence_relevance": 0.0,
                "fact_support": 0.0,
                "policy_alignment": _round(policy_score),
                "payout_alignment": _round(payout_score),
            },
            "summary": {
                "source_count": 0,
                "claim_count": 0,
                "supported_claims": 0,
                "footer_source_count": len(_source_labels_in_output(output)),
                "footer_span_hash_count": len(_span_prefixes_in_output(output)),
            },
            "issues": issues,
        }

    span_prefixes = _span_prefixes_in_output(output)
    accessibility_score, accessibility_issues = _source_accessibility_score(sources)
    citation_score, citation_issues = _citation_integrity_score(output, sources, claims)
    relevance_score = _claim_relevance_score(claims)
    fact_score, fact_issues = _fact_support_score(claims, span_prefixes)
    issues = (
        accessibility_issues
        + citation_issues
        + fact_issues
        + policy_issues
        + payout_issues
    )
    overall = _round(
        0.15 * accessibility_score
        + 0.20 * citation_score
        + 0.20 * relevance_score
        + 0.30 * fact_score
        + 0.10 * policy_score
        + 0.05 * payout_score
    )
    if issues or fact_score < 0.90 or citation_score < 0.90:
        verdict = "failed" if overall < 0.70 else "warning"
    else:
        verdict = "verified"
    return {
        "quality_version": QUALITY_VERSION,
        "verdict": verdict,
        "overall_score": overall,
        "scores": {
            "source_accessibility": _round(accessibility_score),
            "citation_integrity": _round(citation_score),
            "evidence_relevance": _round(relevance_score),
            "fact_support": _round(fact_score),
            "policy_alignment": _round(policy_score),
            "payout_alignment": _round(payout_score),
        },
        "summary": {
            "source_count": len(sources),
            "claim_count": len(claims),
            "supported_claims": sum(1 for claim in claims if claim.supported),
            "footer_source_count": len(_source_labels_in_output(output)),
            "footer_span_hash_count": len(span_prefixes),
        },
        "issues": issues,
    }


def evaluate_event_grounding_quality(event: UsageEvent) -> dict[str, Any]:
    return evaluate_grounding_quality(
        output=event.output,
        sources=event.source_references,
        claims=event.claim_support,
        grounding_report=event.grounding_report,
        policy_decisions=event.policy_decisions,
        royalty_shares=event.royalty_shares,
    )
