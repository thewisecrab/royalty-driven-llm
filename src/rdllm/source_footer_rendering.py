"""Shared rendering for public RDLLM source footers."""

from __future__ import annotations

from typing import Any


def _list(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return "none"
    return ",".join(str(item) for item in value)


def _score(value: Any) -> str:
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "0.000"


def render_source_footer_text(
    *,
    source_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, Any]],
    grounding_report: dict[str, Any],
) -> str:
    lines = ["Sources"]
    if source_rows:
        for row in source_rows:
            lines.append(
                f"{row.get('display_label', '')} {row.get('title', '')} - "
                f"{row.get('creator_name', '')}; "
                f"uri={row.get('source_uri', '')}; "
                f"claims={row.get('supported_claim_count', 0)}; "
                f"confidence={row.get('confidence', '')}; "
                f"support={_score(row.get('output_support', 0))}; "
                f"text_match={_score(row.get('text_match_score', 0))}; "
                f"weight={row.get('contribution_weight', '')}; "
                f"payout={row.get('payout', '')}; "
                f"metrics={row.get('usage_metric_profile', '')}; "
                f"scope={row.get('usage_metric_scope', '')}; "
                "methods="
                f"support:{row.get('support_metric_method', '')},"
                f"text_match:{row.get('text_match_metric_method', '')},"
                f"weight:{row.get('weight_metric_method', '')},"
                f"payout:{row.get('payout_metric_method', '')}; "
                f"why={row.get('why', '')}; "
                f"settlement={row.get('settlement_status', '')}; "
                f"verify={row.get('verification_handle', '')}; "
                f"hash={row.get('content_hash_prefix', '')}."
            )
            if row.get("evidence_preview"):
                lines.append(f"    Evidence: {row['evidence_preview']}")
    else:
        lines.append(
            "[U1] No registered source matched this output; creator pool assigned "
            "to unattributed escrow."
        )

    supported_claim_rows = [row for row in claim_rows if row.get("supported")]
    if supported_claim_rows:
        lines.append("Claim Evidence")
        for row in supported_claim_rows:
            lines.append(
                f"[C{row.get('claim_index')}] {row.get('source_label', '')}; "
                f"claim_hash={row.get('claim_hash_prefix', '')}; "
                f"support={_score(row.get('support_score', 0))}; "
                f"span={row.get('evidence_span_hash_prefix', '')}; "
                f"chars={row.get('evidence_start_char')}-"
                f"{row.get('evidence_end_char')}. "
                f"warrant={row.get('warrant_strength_status', '')}; "
                f"force={_list(row.get('claim_force_flags', []))}; "
                f"missing={_list(row.get('warrant_mismatch_flags', []))}; "
                f"disagreement={row.get('source_disagreement_status', '')}; "
                f"agreements={_list(row.get('agreement_source_labels', []))}; "
                f"conflicts={_list(row.get('disagreement_source_labels', []))}; "
                f"disagreement_profile={row.get('source_disagreement_profile', '')}. "
                f"profile={row.get('claim_warrant_profile', '')}. "
                f"Claim: {row.get('claim_preview', '')} "
                f"Evidence: {row.get('evidence_preview', '')}"
            )

    unsupported_claim_rows = [row for row in claim_rows if not row.get("supported")]
    if unsupported_claim_rows:
        lines.append("Unsupported Claims")
        for row in unsupported_claim_rows:
            lines.append(
                f"[C{row.get('claim_index')}] "
                f"claim_hash={row.get('claim_hash_prefix', '')}; "
                f"support={_score(row.get('support_score', 0))}; "
                "reason=no_registered_evidence."
            )

    lines.append(
        "Grounding: "
        f"{grounding_report.get('supported_claims', 0)}/"
        f"{grounding_report.get('total_claims', 0)} claims supported; "
        f"status={grounding_report.get('status', 'partial')}."
    )
    return "\n".join(lines)
