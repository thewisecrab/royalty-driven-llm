"""Attribution-gap accounting for accessed, cited, paid, and escrowed sources."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from rdllm.models import RoyaltyShare, SourceAccess, SourceReference, UsageEvent
from rdllm.receipts import canonical_json
from rdllm.text import stable_hash

ATTRIBUTION_GAP_VERSION = "rdllm-attribution-gap/v1"


def evaluate_attribution_gap(
    *,
    source_accesses: list[SourceAccess],
    source_references: list[SourceReference],
    royalty_shares: list[RoyaltyShare],
    grounding_report: dict[str, Any],
) -> dict[str, Any]:
    """Measure whether consumed sources were cited, paid, or explicitly escrowed."""

    access_by_chunk: dict[str, list[SourceAccess]] = {}
    for access in source_accesses:
        access_by_chunk.setdefault(access.chunk_id, []).append(access)

    accessed_chunks = set(access_by_chunk)
    visible_chunks = {reference.chunk_id for reference in source_references}
    paid_chunks = {
        share.chunk_id
        for share in royalty_shares
        if share.payout > Decimal("0") and not share.chunk_id.startswith("escrow:")
    }
    escrow_accounts = {
        share.creator_id
        for share in royalty_shares
        if share.chunk_id.startswith("escrow:") and share.payout > Decimal("0")
    }
    policy_blocked_chunks = {
        access.chunk_id for access in source_accesses if not access.policy_allowed
    }
    registry_blocked_chunks = {
        access.chunk_id for access in source_accesses if not access.registry_allowed
    }
    allowed_accessed_chunks = {
        chunk_id
        for chunk_id, accesses in access_by_chunk.items()
        if all(access.policy_allowed and access.registry_allowed for access in accesses)
    }

    consumed_without_credit = sorted(
        chunk_id
        for chunk_id in allowed_accessed_chunks
        if chunk_id not in visible_chunks and chunk_id not in paid_chunks
    )
    cited_without_access = sorted(visible_chunks - accessed_chunks)
    paid_hidden = sorted(paid_chunks - visible_chunks)
    policy_withheld = sorted(policy_blocked_chunks - visible_chunks)
    registry_withheld = sorted(registry_blocked_chunks - visible_chunks)
    credited_chunks = (
        visible_chunks
        | paid_chunks
        | (policy_blocked_chunks if "rights_conflict_escrow" in escrow_accounts else set())
        | (registry_blocked_chunks if "registry_dispute_escrow" in escrow_accounts else set())
    )

    issues: list[str] = []
    for chunk_id in consumed_without_credit:
        issues.append(f"accessed source is neither cited, paid, nor escrowed: {chunk_id}")
    for chunk_id in cited_without_access:
        issues.append(f"visible source was not present in access trace: {chunk_id}")
    for chunk_id in paid_hidden:
        issues.append(f"paid source is hidden from user-visible attribution: {chunk_id}")
    if policy_withheld and "rights_conflict_escrow" not in escrow_accounts:
        issues.append("policy-withheld sources are not assigned to rights-conflict escrow")
    if registry_withheld and "registry_dispute_escrow" not in escrow_accounts:
        issues.append("registry-withheld sources are not assigned to registry-dispute escrow")

    if issues:
        verdict = "open_gap"
    elif not accessed_chunks and "unattributed_escrow" in escrow_accounts:
        verdict = "unattributed"
    elif policy_withheld or registry_withheld:
        verdict = "escrowed"
    else:
        verdict = "closed"

    accessed_count = len(accessed_chunks)
    allowed_accessed_count = len(allowed_accessed_chunks)
    visible_count = len(visible_chunks)
    credited_count = len(credited_chunks)
    paid_count = len(paid_chunks)
    report: dict[str, Any] = {
        "gap_version": ATTRIBUTION_GAP_VERSION,
        "verdict": verdict,
        "summary": {
            "access_record_count": len(source_accesses),
            "accessed_source_count": accessed_count,
            "allowed_accessed_source_count": allowed_accessed_count,
            "visible_source_count": visible_count,
            "paid_source_count": paid_count,
            "credited_source_count": len(credited_chunks),
            "consumed_without_credit_count": len(consumed_without_credit),
            "cited_without_access_count": len(cited_without_access),
            "paid_hidden_count": len(paid_hidden),
            "policy_withheld_count": len(policy_withheld),
            "registry_withheld_count": len(registry_withheld),
            "escrow_accounts": sorted(escrow_accounts),
        },
        "scores": {
            "citation_efficiency": _ratio(visible_count, accessed_count),
            "credit_efficiency": _ratio(credited_count, accessed_count),
            "allowed_credit_coverage": _ratio(
                allowed_accessed_count - len(consumed_without_credit),
                allowed_accessed_count,
            ),
            "payout_visibility": _ratio(paid_count - len(paid_hidden), paid_count),
            "attribution_gap_rate": _ratio(
                len(consumed_without_credit) + len(cited_without_access) + len(paid_hidden),
                max(accessed_count, visible_count, paid_count),
            ),
        },
        "accessed_sources": [_access_summary(access) for access in source_accesses],
        "classifications": {
            "consumed_without_credit": consumed_without_credit,
            "cited_without_access": cited_without_access,
            "paid_hidden": paid_hidden,
            "policy_withheld": policy_withheld,
            "registry_withheld": registry_withheld,
        },
        "grounding_status": grounding_report.get("status", ""),
        "policy_status": grounding_report.get("policy_status", "allowed"),
        "registry_status": grounding_report.get("registry_status", "clear"),
        "issues": issues,
    }
    report["report_hash"] = stable_hash(canonical_json(_hashable_report(report)))
    return report


def evaluate_event_attribution_gap(event: UsageEvent) -> dict[str, Any]:
    return evaluate_attribution_gap(
        source_accesses=event.source_accesses,
        source_references=event.source_references,
        royalty_shares=event.royalty_shares,
        grounding_report=event.grounding_report,
    )


def verify_attribution_gap_report(event: UsageEvent) -> list[str]:
    errors: list[str] = []
    if not event.attribution_gap:
        errors.append("event attribution gap report is missing")
        return errors
    expected = evaluate_event_attribution_gap(event)
    if event.attribution_gap.get("report_hash") != expected.get("report_hash"):
        errors.append("attribution gap report hash does not match event state")
    for key in ("summary", "scores", "classifications", "verdict", "issues"):
        if event.attribution_gap.get(key) != expected.get(key):
            errors.append(f"attribution gap {key} does not match recomputed report")
    return errors


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(max(0.0, min(1.0, numerator / denominator)), 8)


def _access_summary(access: SourceAccess) -> dict[str, Any]:
    return {
        "access_id": access.access_id,
        "access_type": access.access_type,
        "use": access.use,
        "chunk_id": access.chunk_id,
        "work_id": access.work_id,
        "creator_id": access.creator_id,
        "content_hash": access.content_hash,
        "score": round(access.score, 8),
        "rank": access.rank,
        "policy_allowed": access.policy_allowed,
        "registry_allowed": access.registry_allowed,
        "decision_status": access.decision_status,
    }


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in report.items() if key != "report_hash"}
