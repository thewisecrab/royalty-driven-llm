"""Claim-source attribution reports for grounded response footers.

This layer is an independent audit over the final answer surface: each factual
claim is replayed against candidate sources, topical anti-documents, optional
Q&A nuggets, and optional visual evidence regions before any source is credited.
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
from rdllm.text import (
    jaccard_similarity,
    longest_common_token_sequence,
    stable_hash,
    tokenize,
)

CLAIM_SOURCE_ATTRIBUTION_VERSION = "rdllm-claim-source-attribution/v1"
CLAIM_SOURCE_ATTRIBUTION_SCHEMA = (
    "docs/schemas/claim_source_attribution_report.schema.json"
)
CLAIM_SOURCE_ATTRIBUTION_POLICY_VERSION = "rdllm-claim-source-attribution-policy/v1"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L87"
DEFAULT_CREATOR_POOL_RATE = Decimal("0.55")
DEFAULT_ACCEPT_THRESHOLD = 0.48
DEFAULT_MIN_MARGIN = 0.04
DEFAULT_MIN_ANTI_MARGIN = 0.08
MONEY_QUANT = Decimal("0.000001")

ANTI_DOCUMENT_ROLES = {
    "anti_document",
    "hard_anti_document",
    "forbidden_decoy",
    "topical_decoy",
}

VISUAL_MODALITIES = {
    "image",
    "pdf",
    "slide",
    "screenshot",
    "webpage_screenshot",
    "video",
}


def load_claim_source_attribution_input(path: str | Path) -> dict[str, Any]:
    """Load private inputs used to replay a claim-source attribution report."""

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


def _source_role(source: dict[str, Any]) -> str:
    role = str(source.get("source_role", source.get("document_role", "candidate")))
    return role or "candidate"


def _source_modality(source: dict[str, Any]) -> str:
    return str(source.get("modality", "text") or "text").lower()


def _source_content_hash(source: dict[str, Any]) -> str:
    return str(source.get("content_hash") or stable_hash(str(source.get("content", ""))))


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
        phrases = [
            str(item)
            for item in claim.get("required_evidence_phrases", [])
            if str(item).strip()
        ]
        rows.append(
            {
                "claim_id": _claim_id(claim, index),
                "claim_hash": str(claim.get("claim_hash") or stable_hash(claim_text)),
                "required_evidence_phrase_hashes": [
                    stable_hash(phrase.lower().strip()) for phrase in phrases
                ],
                "expected_source_ids": sorted(
                    str(item) for item in claim.get("expected_source_ids", [])
                ),
                "forbidden_source_ids": sorted(
                    str(item) for item in claim.get("forbidden_source_ids", [])
                ),
                "expected_refusal": bool(claim.get("expected_refusal", False)),
            }
        )
    return rows


def _source_public_rows(attribution_input: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, source in enumerate(attribution_input.get("candidate_sources", []), start=1):
        source_id = _source_id(source, index)
        visual_regions = _visual_region_rows(source_id, source)
        rows.append(
            {
                "source_id": source_id,
                "work_id": str(source.get("work_id", "")),
                "chunk_id": str(source.get("chunk_id", "")),
                "creator_id": str(source.get("creator_id", "")),
                "creator_name": str(source.get("creator_name", "")),
                "title": str(source.get("title", "")),
                "source_uri": str(source.get("source_uri", "")),
                "content_hash": _source_content_hash(source),
                "source_role": _source_role(source),
                "modality": _source_modality(source),
                "visual_region_hashes": [
                    row["region_hash"] for row in visual_regions
                ],
                "visual_region_count": len(visual_regions),
            }
        )
    return rows


def _visual_region_rows(source_id: str, source: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, region in enumerate(source.get("visual_regions", []), start=1):
        payload = {
            "source_id": source_id,
            "region_id": str(region.get("region_id") or f"region_{index}"),
            "page": int(region.get("page", 0) or 0),
            "x": round(float(region.get("x", 0.0) or 0.0), 6),
            "y": round(float(region.get("y", 0.0) or 0.0), 6),
            "width": round(float(region.get("width", 0.0) or 0.0), 6),
            "height": round(float(region.get("height", 0.0) or 0.0), 6),
            "region_text_hash": stable_hash(str(region.get("region_text", ""))),
            "label_hash": stable_hash(str(region.get("label", ""))),
        }
        payload["region_hash"] = hash_payload(payload)
        rows.append(payload)
    return rows


def _source_search_text(source: dict[str, Any]) -> str:
    parts = [str(source.get("content", ""))]
    for region in source.get("visual_regions", []):
        parts.append(str(region.get("region_text", "")))
        parts.append(str(region.get("label", "")))
    return "\n".join(part for part in parts if part)


def _nuggets_by_source(attribution_input: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for nugget in attribution_input.get("qna_nuggets", []):
        source_id = str(nugget.get("source_id", ""))
        if source_id:
            grouped[source_id].append(dict(nugget))
    return grouped


def _phrase_recall(phrase_hashes: list[str], phrases: list[str], source_text: str) -> float:
    if not phrase_hashes and not phrases:
        return 1.0
    lowered = source_text.lower()
    found = sum(1 for phrase in phrases if phrase.lower().strip() in lowered)
    denominator = max(1, len(phrases), len(phrase_hashes))
    return round(found / denominator, 8)


def _critical_recall(claim_tokens: list[str], source_tokens: list[str]) -> float:
    critical = [token for token in claim_tokens if len(token) >= 5]
    if not critical:
        critical = claim_tokens
    if not critical:
        return 0.0
    source_set = set(source_tokens)
    return round(len([token for token in critical if token in source_set]) / len(critical), 8)


def _nugget_alignment(claim_text: str, nuggets: list[dict[str, Any]]) -> tuple[float, list[str]]:
    claim_tokens = tokenize(claim_text)
    best = 0.0
    hashes: list[str] = []
    for nugget in nuggets:
        text = f"{nugget.get('question', '')} {nugget.get('answer', '')}"
        score = jaccard_similarity(claim_tokens, tokenize(text))
        best = max(best, score)
        hashes.append(
            hash_payload(
                {
                    "nugget_id": str(nugget.get("nugget_id", "")),
                    "source_id": str(nugget.get("source_id", "")),
                    "question_hash": stable_hash(str(nugget.get("question", ""))),
                    "answer_hash": stable_hash(str(nugget.get("answer", ""))),
                }
            )
        )
    return round(best, 8), sorted(hashes)


def _score_source_for_claim(
    *,
    claim: dict[str, Any],
    claim_row: dict[str, Any],
    source: dict[str, Any],
    source_index: int,
    nuggets_by_source: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    source_id = _source_id(source, source_index)
    claim_text = str(claim.get("claim_text", ""))
    source_text = _source_search_text(source)
    claim_tokens = tokenize(claim_text)
    source_tokens = tokenize(source_text)
    longest_length, longest_tokens = longest_common_token_sequence(
        claim_tokens,
        source_tokens,
    )
    token_overlap = jaccard_similarity(claim_tokens, source_tokens)
    critical_recall = _critical_recall(claim_tokens, source_tokens)
    phrases = [
        str(item)
        for item in claim.get("required_evidence_phrases", [])
        if str(item).strip()
    ]
    phrase_recall = _phrase_recall(
        claim_row["required_evidence_phrase_hashes"],
        phrases,
        source_text,
    )
    sequence_score = round(
        min(1.0, longest_length / max(4, len(claim_tokens))),
        8,
    )
    nugget_score, nugget_hashes = _nugget_alignment(
        claim_text,
        nuggets_by_source.get(source_id, []),
    )
    modality = _source_modality(source)
    visual_regions = _visual_region_rows(source_id, source)
    visual_required = modality in VISUAL_MODALITIES
    visual_anchor_score = 1.0
    if visual_required:
        visual_anchor_score = 1.0 if visual_regions else 0.0
    role = _source_role(source)
    forbidden = (
        source_id in set(claim_row["forbidden_source_ids"])
        or role in ANTI_DOCUMENT_ROLES
    )
    expected = source_id in set(claim_row["expected_source_ids"])
    anti_penalty = 0.28 if forbidden else 0.0
    decision_score = _clamp(
        0.27 * phrase_recall
        + 0.23 * critical_recall
        + 0.17 * token_overlap
        + 0.13 * sequence_score
        + 0.10 * nugget_score
        + 0.10 * visual_anchor_score
        - anti_penalty
    )
    matched_sequence_hash = (
        stable_hash(" ".join(longest_tokens)) if longest_tokens else ""
    )
    feature_payload = {
        "claim_id": claim_row["claim_id"],
        "claim_hash": claim_row["claim_hash"],
        "source_id": source_id,
        "content_hash": _source_content_hash(source),
        "required_evidence_phrase_hashes": claim_row[
            "required_evidence_phrase_hashes"
        ],
        "nugget_hashes": nugget_hashes,
        "visual_region_hashes": [row["region_hash"] for row in visual_regions],
        "matched_sequence_hash": matched_sequence_hash,
        "scores": {
            "required_phrase_recall": round(phrase_recall, 8),
            "critical_token_recall": round(critical_recall, 8),
            "token_overlap": round(token_overlap, 8),
            "sequence_score": round(sequence_score, 8),
            "qna_nugget_alignment": round(nugget_score, 8),
            "visual_anchor_score": round(visual_anchor_score, 8),
            "anti_document_penalty": round(anti_penalty, 8),
            "decision_score": round(decision_score, 8),
        },
    }
    return {
        "claim_id": claim_row["claim_id"],
        "claim_hash": claim_row["claim_hash"],
        "source_id": source_id,
        "work_id": str(source.get("work_id", "")),
        "chunk_id": str(source.get("chunk_id", "")),
        "creator_id": str(source.get("creator_id", "")),
        "creator_name": str(source.get("creator_name", "")),
        "title": str(source.get("title", "")),
        "source_uri": str(source.get("source_uri", "")),
        "content_hash": _source_content_hash(source),
        "modality": modality,
        "source_role": role,
        "candidate_relation": "forbidden_anti_document"
        if forbidden
        else ("expected_support" if expected else "unlabeled_candidate"),
        "scores": feature_payload["scores"],
        "feature_commitment": hash_payload(feature_payload),
        "matched_sequence_hash": matched_sequence_hash,
        "qna_nugget_hashes": nugget_hashes,
        "visual_region_hashes": [row["region_hash"] for row in visual_regions],
        "visual_region_count": len(visual_regions),
        "rank": 0,
        "loo_utility_drop": 0.0,
        "anti_document_margin": 0.0,
        "attribution_credit": 0.0,
        "decision": "candidate",
    }


def _rank_claim_sources(
    attribution_input: dict[str, Any],
    *,
    accept_threshold: float,
    min_margin: float,
    min_anti_margin: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    claims = attribution_input.get("claims", [])
    if not claims:
        claims = [
            {
                "claim_id": "claim_1",
                "claim_text": str(
                    attribution_input.get("event", {}).get(
                        "response_text",
                        attribution_input.get("event", {}).get("output_text", ""),
                    )
                ),
            }
        ]
    claim_rows = _claim_rows({**attribution_input, "claims": claims})
    sources = [dict(item) for item in attribution_input.get("candidate_sources", [])]
    public_sources = _source_public_rows(attribution_input)
    nuggets_by_source = _nuggets_by_source(attribution_input)
    all_candidate_rows: list[dict[str, Any]] = []
    audited_claims: list[dict[str, Any]] = []

    for claim_index, claim in enumerate(claims, start=1):
        claim_row = claim_rows[claim_index - 1]
        rows = [
            _score_source_for_claim(
                claim=claim,
                claim_row=claim_row,
                source=source,
                source_index=source_index,
                nuggets_by_source=nuggets_by_source,
            )
            for source_index, source in enumerate(sources, start=1)
        ]
        rows.sort(
            key=lambda row: (
                -float(row["scores"]["decision_score"]),
                row["candidate_relation"] == "forbidden_anti_document",
                str(row["source_id"]),
            )
        )
        top = rows[0] if rows else None
        top_score = float(top["scores"]["decision_score"]) if top else 0.0
        second_score = float(rows[1]["scores"]["decision_score"]) if len(rows) > 1 else 0.0
        top_non_anti = max(
            [
                float(row["scores"]["decision_score"])
                for row in rows
                if row["candidate_relation"] != "forbidden_anti_document"
            ]
            or [0.0]
        )
        top_anti = max(
            [
                float(row["scores"]["decision_score"])
                for row in rows
                if row["candidate_relation"] == "forbidden_anti_document"
            ]
            or [0.0]
        )
        support_margin = round(max(0.0, top_score - second_score), 8)
        anti_margin = round(top_non_anti - top_anti, 8)
        accepted = bool(
            top
            and not claim_row["expected_refusal"]
            and top["candidate_relation"] != "forbidden_anti_document"
            and top_score >= accept_threshold
            and support_margin >= min_margin
            and anti_margin >= min_anti_margin
        )
        accepted_source_ids = {str(top["source_id"])} if accepted and top else set()
        raw_credit_by_source: dict[str, float] = {}
        for row in rows:
            source_id = str(row["source_id"])
            score = float(row["scores"]["decision_score"])
            if source_id in accepted_source_ids:
                loo_drop = max(0.0, score - second_score)
                raw_credit_by_source[source_id] = max(
                    0.0,
                    score + loo_drop + max(0.0, anti_margin),
                )
        raw_total = sum(raw_credit_by_source.values())
        for rank, row in enumerate(rows, start=1):
            source_id = str(row["source_id"])
            row["rank"] = rank
            row["loo_utility_drop"] = (
                round(max(0.0, top_score - second_score), 8)
                if source_id in accepted_source_ids
                else 0.0
            )
            row["anti_document_margin"] = anti_margin
            if source_id in accepted_source_ids and raw_total > 0:
                row["attribution_credit"] = round(
                    raw_credit_by_source[source_id] / raw_total,
                    8,
                )
                row["decision"] = "accepted"
            elif row["candidate_relation"] == "forbidden_anti_document":
                row["decision"] = "rejected_anti_document"
            elif rank == 1:
                row["decision"] = (
                    "expected_refusal"
                    if claim_row["expected_refusal"]
                    else "attribution_escrow"
                )
            else:
                row["decision"] = "candidate"
            row["row_hash"] = hash_payload(row)
        all_candidate_rows.extend(rows)
        audited_claims.append(
            {
                "claim_id": claim_row["claim_id"],
                "claim_hash": claim_row["claim_hash"],
                "top_source_id": str(top.get("source_id", "")) if top else "",
                "top_content_hash": str(top.get("content_hash", "")) if top else "",
                "top_decision_score": round(top_score, 8),
                "support_margin": support_margin,
                "anti_document_margin": anti_margin,
                "expected_refusal": claim_row["expected_refusal"],
                "decision": "grounded"
                if accepted
                else (
                    "expected_refusal"
                    if claim_row["expected_refusal"]
                    else "attribution_escrow"
                ),
                "accepted_source_ids": sorted(accepted_source_ids),
                "required_evidence_phrase_hashes": claim_row[
                    "required_evidence_phrase_hashes"
                ],
                "expected_source_ids": claim_row["expected_source_ids"],
                "forbidden_source_ids": claim_row["forbidden_source_ids"],
            }
        )
    return claim_rows, public_sources, all_candidate_rows, audited_claims


def _footer_rows(
    candidate_rows: list[dict[str, Any]],
    audited_claims: list[dict[str, Any]],
) -> dict[str, Any]:
    accepted = [row for row in candidate_rows if row.get("decision") == "accepted"]
    source_labels: dict[str, str] = {}
    source_rows: list[dict[str, Any]] = []
    for row in accepted:
        source_id = str(row["source_id"])
        if source_id in source_labels:
            continue
        label = f"S{len(source_labels) + 1}"
        source_labels[source_id] = label
        display_text = (
            f"[{label}] {row['title']} - {row['creator_name']}; "
            f"work={row['work_id']}; chunk={row['chunk_id']}; "
            f"hash={str(row['content_hash'])[:18]}; "
            f"score={row['scores']['decision_score']}; uri={row['source_uri']}"
        )
        footer_row = {
            "label": label,
            "source_id": source_id,
            "work_id": row["work_id"],
            "chunk_id": row["chunk_id"],
            "creator_id": row["creator_id"],
            "creator_name": row["creator_name"],
            "title": row["title"],
            "source_uri": row["source_uri"],
            "content_hash_prefix": str(row["content_hash"])[:18],
            "decision_score": row["scores"]["decision_score"],
            "attribution_credit": row["attribution_credit"],
            "display_text": display_text,
        }
        footer_row["footer_row_hash"] = hash_payload(footer_row)
        source_rows.append(footer_row)

    claim_rows: list[dict[str, Any]] = []
    for claim in audited_claims:
        accepted_ids = list(claim.get("accepted_source_ids", []))
        if accepted_ids:
            label = source_labels.get(accepted_ids[0], "")
            display_text = (
                f"claim={claim['claim_id']} -> [{label}] "
                f"support={claim['top_decision_score']}; "
                f"margin={claim['support_margin']}; anti_margin={claim['anti_document_margin']}"
            )
        else:
            label = ""
            display_text = (
                f"claim={claim['claim_id']} -> no verified source; "
                f"decision={claim['decision']}"
            )
        claim_row = {
            "claim_id": claim["claim_id"],
            "claim_hash": claim["claim_hash"],
            "label": label,
            "decision": claim["decision"],
            "top_source_id": claim["top_source_id"],
            "top_decision_score": claim["top_decision_score"],
            "support_margin": claim["support_margin"],
            "anti_document_margin": claim["anti_document_margin"],
            "display_text": display_text,
        }
        claim_row["claim_footer_hash"] = hash_payload(claim_row)
        claim_rows.append(claim_row)
    footer_text = "\n".join(
        [row["display_text"] for row in source_rows]
        + [row["display_text"] for row in claim_rows]
    )
    footer = {
        "profile": "rdllm-claim-source-footer/v1",
        "source_rows": source_rows,
        "claim_rows": claim_rows,
        "footer_text": footer_text,
        "source_row_count": len(source_rows),
        "claim_row_count": len(claim_rows),
    }
    footer["footer_hash"] = hash_payload(footer)
    return footer


def _allocate(
    claim_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    *,
    creator_pool: Decimal,
) -> tuple[list[dict[str, Any]], Decimal]:
    per_claim = (
        (creator_pool / Decimal(str(max(1, len(claim_rows))))).quantize(MONEY_QUANT)
        if claim_rows
        else Decimal("0")
    )
    accepted_by_claim: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidate_rows:
        if row.get("decision") == "accepted":
            accepted_by_claim[str(row["claim_id"])].append(row)

    shares_by_key: defaultdict[tuple[str, str, str], Decimal] = defaultdict(
        lambda: Decimal("0")
    )
    share_claims: defaultdict[tuple[str, str, str], list[str]] = defaultdict(list)
    escrow_total = Decimal("0")
    for claim in claim_rows:
        rows = accepted_by_claim.get(str(claim["claim_id"]), [])
        if rows:
            paid_for_claim = Decimal("0")
            for index, row in enumerate(rows):
                key = (str(row["creator_id"]), str(row["work_id"]), str(row["chunk_id"]))
                if index == len(rows) - 1:
                    payout = per_claim - paid_for_claim
                else:
                    payout = (
                        per_claim * Decimal(str(row.get("attribution_credit", 0.0)))
                    ).quantize(MONEY_QUANT)
                paid_for_claim += payout
                shares_by_key[key] += payout
                share_claims[key].append(str(claim["claim_id"]))
        else:
            key = (
                "claim_source_attribution_escrow",
                "escrow:claim_source_attribution",
                "escrow:claim_source_attribution",
            )
            shares_by_key[key] += per_claim
            share_claims[key].append(str(claim["claim_id"]))
            escrow_total += per_claim

    shares: list[dict[str, Any]] = []
    paid_so_far = Decimal("0")
    items = sorted(shares_by_key.items(), key=lambda item: item[0])
    for index, ((creator_id, work_id, chunk_id), payout) in enumerate(items):
        payout = payout.quantize(MONEY_QUANT)
        if index == len(items) - 1:
            payout = creator_pool - paid_so_far
        paid_so_far += payout
        shares.append(
            {
                "creator_id": creator_id,
                "work_id": work_id,
                "chunk_id": chunk_id,
                "claim_ids": sorted(set(share_claims[(creator_id, work_id, chunk_id)])),
                "decision": "attribution_escrow"
                if creator_id == "claim_source_attribution_escrow"
                else "accepted",
                "payout": _money(payout),
                "contribution_weight": round(float(payout / creator_pool), 8)
                if creator_pool
                else 0.0,
            }
        )
    return shares, escrow_total


def _checks(
    *,
    claim_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    audited_claims: list[dict[str, Any]],
    footer: dict[str, Any],
    royalty_shares: list[dict[str, Any]],
    creator_pool: Decimal,
    accept_threshold: float,
    min_margin: float,
    min_anti_margin: float,
) -> dict[str, bool]:
    accepted = [row for row in candidate_rows if row.get("decision") == "accepted"]
    accepted_claims = {str(row["claim_id"]) for row in accepted}
    grounded_claims = {
        str(claim["claim_id"])
        for claim in audited_claims
        if claim.get("decision") == "grounded"
    }
    footer_claims = {
        str(row["claim_id"])
        for row in footer.get("claim_rows", [])
        if row.get("label")
    }
    accepted_visual = [
        row
        for row in accepted
        if str(row.get("modality", "")).lower() in VISUAL_MODALITIES
    ]
    payout_total = sum(
        (Decimal(str(share["payout"])) for share in royalty_shares),
        Decimal("0"),
    )
    row_json = canonical_json(
        {
            "candidate_rows": candidate_rows,
            "footer": footer,
            "royalty_shares": royalty_shares,
        }
    )
    credit_by_claim: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in accepted:
        credit_by_claim[str(row["claim_id"])] += Decimal(
            str(row.get("attribution_credit", 0.0))
        )
    return {
        "every_claim_has_grounded_source_or_escrow": all(
            claim["decision"] in {"grounded", "attribution_escrow", "expected_refusal"}
            for claim in audited_claims
        ),
        "grounded_claims_have_visible_footer_rows": grounded_claims.issubset(
            footer_claims
        ),
        "accepted_sources_are_not_anti_documents": all(
            row.get("candidate_relation") != "forbidden_anti_document"
            and row.get("source_role") not in ANTI_DOCUMENT_ROLES
            for row in accepted
        ),
        "accepted_sources_meet_threshold_margin_and_anti_margin": all(
            float(row["scores"]["decision_score"]) >= accept_threshold
            and float(row["loo_utility_drop"]) >= min_margin
            and float(row["anti_document_margin"]) >= min_anti_margin
            for row in accepted
        ),
        "visual_sources_have_region_commitments": all(
            int(row.get("visual_region_count", 0) or 0) > 0
            and bool(row.get("visual_region_hashes"))
            for row in accepted_visual
        ),
        "attribution_credit_conserved_per_grounded_claim": all(
            abs(float(credit_by_claim[claim_id]) - 1.0) < 0.000001
            for claim_id in accepted_claims
        ),
        "unattributed_claims_route_to_escrow": all(
            claim["decision"] == "grounded"
            or any(
                share["decision"] == "attribution_escrow"
                and claim["claim_id"] in share.get("claim_ids", [])
                for share in royalty_shares
            )
            or claim["decision"] == "expected_refusal"
            for claim in audited_claims
        ),
        "footer_hash_reproducible": (
            hash_payload({key: value for key, value in footer.items() if key != "footer_hash"})
            == footer.get("footer_hash")
        ),
        "candidate_row_hashes_reproducible": all(
            hash_payload({key: value for key, value in row.items() if key != "row_hash"})
            == row.get("row_hash")
            for row in candidate_rows
        ),
        "creator_pool_conserved": payout_total == creator_pool,
        "public_report_does_not_embed_private_text": (
            row_json.find('"claim_text"') == -1
            and row_json.find('"content"') == -1
            and row_json.find('"response_text"') == -1
            and row_json.find('"prompt_text"') == -1
            and row_json.find('"region_text"') == -1
        ),
    }


def make_claim_source_attribution_report(
    attribution_input: dict[str, Any],
    *,
    gross_revenue: Decimal | str | float = Decimal("1.00"),
    creator_pool_rate: Decimal | str | float = DEFAULT_CREATOR_POOL_RATE,
    accept_threshold: float = DEFAULT_ACCEPT_THRESHOLD,
    min_margin: float = DEFAULT_MIN_MARGIN,
    min_anti_margin: float = DEFAULT_MIN_ANTI_MARGIN,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed claim-source attribution report."""

    gross = Decimal(str(gross_revenue)).quantize(MONEY_QUANT)
    rate = Decimal(str(creator_pool_rate))
    creator_pool = (gross * rate).quantize(MONEY_QUANT)
    claim_rows, public_sources, candidate_rows, audited_claims = _rank_claim_sources(
        attribution_input,
        accept_threshold=accept_threshold,
        min_margin=min_margin,
        min_anti_margin=min_anti_margin,
    )
    footer = _footer_rows(candidate_rows, audited_claims)
    shares, escrow_total = _allocate(
        claim_rows,
        candidate_rows,
        creator_pool=creator_pool,
    )
    checks = _checks(
        claim_rows=claim_rows,
        candidate_rows=candidate_rows,
        audited_claims=audited_claims,
        footer=footer,
        royalty_shares=shares,
        creator_pool=creator_pool,
        accept_threshold=accept_threshold,
        min_margin=min_margin,
        min_anti_margin=min_anti_margin,
    )
    accepted = [row for row in candidate_rows if row.get("decision") == "accepted"]
    report = {
        "report_version": CLAIM_SOURCE_ATTRIBUTION_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "event": _event_input(attribution_input),
        "policy": {
            "profile": CLAIM_SOURCE_ATTRIBUTION_POLICY_VERSION,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "creator_pool_rate": str(rate),
            "accept_threshold": round(float(accept_threshold), 8),
            "min_loo_margin": round(float(min_margin), 8),
            "min_anti_document_margin": round(float(min_anti_margin), 8),
            "topical_similarity_alone_is_insufficient": True,
            "claim_level_footer_required": True,
            "visual_region_commitments_required_when_visual_source_is_credited": True,
            "loo_source_importance_enabled": True,
        },
        "economics": {
            "gross_revenue": _money(gross),
            "creator_pool": _money(creator_pool),
            "payout_total": _money(
                sum((Decimal(share["payout"]) for share in shares), Decimal("0"))
            ),
            "escrow_total": _money(escrow_total),
        },
        "claims": audited_claims,
        "sources": public_sources,
        "candidate_rows": candidate_rows,
        "footer": footer,
        "royalty_shares": shares,
        "commitments": {
            "claim_root": hash_payload(claim_rows),
            "source_root": hash_payload(public_sources),
            "candidate_row_root": hash_payload(
                [row["row_hash"] for row in candidate_rows]
            ),
            "footer_hash": footer["footer_hash"],
            "share_root": hash_payload(shares),
            "private_input_root": hash_payload(
                {
                    "event": _event_input(attribution_input),
                    "claims": claim_rows,
                    "sources": public_sources,
                    "qna_nugget_commitments": sorted(
                        nugget_hash
                        for nuggets in _nuggets_by_source(attribution_input).values()
                        for nugget_hash in _nugget_alignment("", nuggets)[1]
                    ),
                }
            ),
        },
        "checks": checks,
        "schemas": {
            "claim_source_attribution_report": CLAIM_SOURCE_ATTRIBUTION_SCHEMA,
        },
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "claim_count": len(claim_rows),
            "source_count": len(public_sources),
            "candidate_row_count": len(candidate_rows),
            "grounded_claim_count": len(
                [claim for claim in audited_claims if claim["decision"] == "grounded"]
            ),
            "escrow_claim_count": len(
                [
                    claim
                    for claim in audited_claims
                    if claim["decision"] == "attribution_escrow"
                ]
            ),
            "accepted_source_count": len({row["source_id"] for row in accepted}),
            "anti_document_rejected_count": len(
                [
                    row
                    for row in candidate_rows
                    if row["decision"] == "rejected_anti_document"
                ]
            ),
            "visual_region_commitment_count": sum(
                len(row.get("visual_region_hashes", [])) for row in accepted
            ),
            "footer_hash": footer["footer_hash"],
            "creator_pool_conserved": checks["creator_pool_conserved"],
            "offline_verification_supported": True,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "response_text_disclosed": False,
            "claim_text_disclosed": False,
            "source_text_disclosed": False,
            "visual_region_text_disclosed": False,
            "public_report_uses_hashes_scores_source_ids_and_footer_rows": True,
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


def validate_claim_source_attribution_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "event",
        "policy",
        "economics",
        "claims",
        "sources",
        "candidate_rows",
        "footer",
        "royalty_shares",
        "commitments",
        "checks",
        "schemas",
        "summary",
        "privacy",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing claim-source attribution field: {key}")
    if errors:
        return errors
    if report.get("report_version") != CLAIM_SOURCE_ATTRIBUTION_VERSION:
        errors.append("claim-source attribution report version is unsupported")
    if report.get("policy", {}).get("profile") != CLAIM_SOURCE_ATTRIBUTION_POLICY_VERSION:
        errors.append("claim-source attribution policy profile is unsupported")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("claim-source attribution target certification level is unsupported")
    if "claim_source_attribution_report" not in report.get("schemas", {}):
        errors.append("missing claim-source attribution schema")
    for row in report.get("candidate_rows", []):
        for key in (
            "claim_id",
            "claim_hash",
            "source_id",
            "work_id",
            "chunk_id",
            "creator_id",
            "content_hash",
            "modality",
            "source_role",
            "candidate_relation",
            "scores",
            "feature_commitment",
            "rank",
            "loo_utility_drop",
            "anti_document_margin",
            "attribution_credit",
            "decision",
            "row_hash",
        ):
            if key not in row:
                errors.append(f"missing claim-source candidate row field: {key}")
    footer = report.get("footer", {})
    for key in ("profile", "source_rows", "claim_rows", "footer_text", "footer_hash"):
        if key not in footer:
            errors.append(f"missing claim-source footer field: {key}")
    return errors


def _private_strings(attribution_input: dict[str, Any]) -> list[str]:
    values: list[str] = []
    event = attribution_input.get("event", {})
    values.append(str(event.get("prompt_text", "")))
    values.append(str(event.get("response_text", event.get("output_text", ""))))
    for claim in attribution_input.get("claims", []):
        values.append(str(claim.get("claim_text", "")))
        values.extend(str(item) for item in claim.get("required_evidence_phrases", []))
    for source in attribution_input.get("candidate_sources", []):
        values.append(str(source.get("content", "")))
        for region in source.get("visual_regions", []):
            values.append(str(region.get("region_text", "")))
            values.append(str(region.get("label", "")))
    for nugget in attribution_input.get("qna_nuggets", []):
        values.append(str(nugget.get("question", "")))
        values.append(str(nugget.get("answer", "")))
    return [value for value in values if len(value.strip()) >= 16]


def verify_claim_source_attribution_report(
    report: dict[str, Any],
    attribution_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify a claim-source attribution report."""

    errors = validate_claim_source_attribution_report_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get("report_hash"):
        errors.append("claim-source attribution report hash is not reproducible")

    expected = make_claim_source_attribution_report(
        attribution_input,
        gross_revenue=report.get("economics", {}).get("gross_revenue", "1.00"),
        creator_pool_rate=report.get("policy", {}).get(
            "creator_pool_rate",
            str(DEFAULT_CREATOR_POOL_RATE),
        ),
        accept_threshold=float(
            report.get("policy", {}).get(
                "accept_threshold",
                DEFAULT_ACCEPT_THRESHOLD,
            )
        ),
        min_margin=float(
            report.get("policy", {}).get("min_loo_margin", DEFAULT_MIN_MARGIN)
        ),
        min_anti_margin=float(
            report.get("policy", {}).get(
                "min_anti_document_margin",
                DEFAULT_MIN_ANTI_MARGIN,
            )
        ),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "event",
        "policy",
        "economics",
        "claims",
        "sources",
        "candidate_rows",
        "footer",
        "royalty_shares",
        "commitments",
        "checks",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"claim-source attribution {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("claim-source attribution report hash does not match replay")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("claim-source attribution report status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"claim-source attribution check failed: {check}")

    rendered = canonical_json(report)
    for value in _private_strings(attribution_input):
        if value and value in rendered:
            errors.append("claim-source attribution report leaks private input text")
            break

    if signing_secret:
        signature = report.get("signature", {})
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("claim-source attribution report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("claim-source attribution report signature is invalid")
    return errors
