"""Media attribution reports for image, audio, video, and other non-text assets."""

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
from rdllm.text import jaccard_similarity, stable_hash, tokenize

MEDIA_ATTRIBUTION_VERSION = "rdllm-media-attribution/v1"
DEFAULT_ACCEPT_THRESHOLD = 0.65
DEFAULT_CREATOR_POOL_RATE = Decimal("0.55")
MONEY_QUANT = Decimal("0.000001")
SUPPORTED_MEDIA_TYPES = ("image", "audio", "video", "3d", "text")


def load_media_corpus(path: str | Path) -> dict[str, Any]:
    """Load a media attribution corpus with creators and registered assets."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_media_inputs(path: str | Path) -> list[dict[str, Any]]:
    """Load submitted media signatures for attribution."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return list(data.get("inputs", data.get("submitted_media", [])))
    return list(data)


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY_QUANT))


def _allocate_item_pools(creator_pool: Decimal, item_count: int) -> list[Decimal]:
    if item_count <= 0:
        return []
    base = (creator_pool / Decimal(item_count)).quantize(MONEY_QUANT)
    pools = [base for _ in range(item_count)]
    remainder = creator_pool - sum(pools, Decimal("0"))
    if remainder:
        pools[-1] = (pools[-1] + remainder).quantize(MONEY_QUANT)
    return pools


def _asset_hash(asset: dict[str, Any]) -> str:
    value = str(asset.get("content_hash") or "")
    if value:
        return value
    return stable_hash(
        canonical_json(
            {
                "asset_id": asset.get("asset_id", ""),
                "media_type": asset.get("media_type", ""),
                "descriptor": asset.get("descriptor", ""),
            }
        )
    )


def _input_hash(item: dict[str, Any]) -> str:
    value = str(item.get("content_hash") or item.get("input_hash") or "")
    if value:
        return value
    return stable_hash(
        canonical_json(
            {
                "input_id": item.get("input_id", ""),
                "media_type": item.get("media_type", ""),
                "descriptor": item.get("descriptor", ""),
            }
        )
    )


def _hamming_similarity(left: str, right: str) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    distance = sum(1 for left_char, right_char in zip(left, right) if left_char != right_char)
    return 1.0 - (distance / len(left))


def _descriptor_similarity(left: str, right: str) -> float:
    return jaccard_similarity(tokenize(left), tokenize(right))


def _score_candidate(input_item: dict[str, Any], asset: dict[str, Any]) -> dict[str, Any]:
    if str(input_item.get("media_type", "")) != str(asset.get("media_type", "")):
        return {
            "exact_hash_match": False,
            "perceptual_similarity": 0.0,
            "descriptor_similarity": 0.0,
            "decision_score": 0.0,
        }
    exact_hash_match = _input_hash(input_item) == _asset_hash(asset)
    perceptual_similarity = _hamming_similarity(
        str(input_item.get("perceptual_hash", "")),
        str(asset.get("perceptual_hash", "")),
    )
    descriptor_similarity = _descriptor_similarity(
        str(input_item.get("descriptor", "")),
        str(asset.get("descriptor", "")),
    )
    if exact_hash_match:
        decision_score = 1.0
    else:
        decision_score = (
            0.55 * perceptual_similarity
            + 0.35 * descriptor_similarity
            + 0.10 * float(exact_hash_match)
        )
    return {
        "exact_hash_match": exact_hash_match,
        "perceptual_similarity": round(perceptual_similarity, 8),
        "descriptor_similarity": round(descriptor_similarity, 8),
        "decision_score": round(decision_score, 8),
    }


def _creators_by_id(media_corpus: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(creator.get("creator_id", "")): creator
        for creator in media_corpus.get("creators", [])
    }


def _ranked_candidates(
    input_item: dict[str, Any],
    media_corpus: dict[str, Any],
) -> list[dict[str, Any]]:
    creators = _creators_by_id(media_corpus)
    rows: list[dict[str, Any]] = []
    for asset in media_corpus.get("assets", []):
        score = _score_candidate(input_item, asset)
        if score["decision_score"] <= 0:
            continue
        creator = creators.get(str(asset.get("creator_id", "")), {})
        rows.append(
            {
                "asset_id": asset.get("asset_id", ""),
                "creator_id": asset.get("creator_id", ""),
                "creator_name": creator.get("name", ""),
                "title": asset.get("title", ""),
                "media_type": asset.get("media_type", ""),
                "source_uri": asset.get("source_uri", ""),
                "content_hash": _asset_hash(asset),
                "exact_hash_match": score["exact_hash_match"],
                "perceptual_similarity": score["perceptual_similarity"],
                "descriptor_similarity": score["descriptor_similarity"],
                "decision_score": score["decision_score"],
                "rank": 0,
            }
        )
    rows.sort(key=lambda row: (-float(row["decision_score"]), row["asset_id"]))
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def _private_strings(
    media_corpus: dict[str, Any],
    submitted_media: list[dict[str, Any]],
) -> list[str]:
    values: list[str] = []
    for asset in media_corpus.get("assets", []):
        values.append(str(asset.get("descriptor", "")))
    for item in submitted_media:
        values.append(str(item.get("descriptor", "")))
    return [value for value in values if len(value.strip()) >= 16]


def make_media_attribution_report(
    media_corpus: dict[str, Any],
    submitted_media: list[dict[str, Any]],
    *,
    gross_revenue: Decimal | str | float = Decimal("1.00"),
    creator_pool_rate: Decimal | str | float = DEFAULT_CREATOR_POOL_RATE,
    accept_threshold: float = DEFAULT_ACCEPT_THRESHOLD,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a privacy-safe attribution and payout report for media inputs."""

    gross = Decimal(str(gross_revenue)).quantize(MONEY_QUANT)
    rate = Decimal(str(creator_pool_rate))
    creator_pool = (gross * rate).quantize(MONEY_QUANT)
    item_pools = _allocate_item_pools(creator_pool, len(submitted_media))
    item_pool = item_pools[0] if item_pools else Decimal("0")
    matches: list[dict[str, Any]] = []
    payout_totals: defaultdict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    payout_inputs: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    escrow_total = Decimal("0")
    for input_index, input_item in enumerate(submitted_media, start=1):
        current_item_pool = item_pools[input_index - 1] if item_pools else Decimal("0")
        ranked = _ranked_candidates(input_item, media_corpus)
        best = ranked[0] if ranked else None
        matched = bool(best and float(best["decision_score"]) >= accept_threshold)
        if matched and best:
            payout_key = (str(best["creator_id"]), str(best["asset_id"]))
            payout_totals[payout_key] += current_item_pool
            payout_inputs[payout_key].append(str(input_item.get("input_id", f"input:{input_index}")))
        else:
            escrow_total += current_item_pool
        match = {
            "input_id": input_item.get("input_id", f"input:{input_index}"),
            "media_type": input_item.get("media_type", ""),
            "input_hash": _input_hash(input_item),
            "perceptual_hash_commitment": stable_hash(str(input_item.get("perceptual_hash", ""))),
            "descriptor_hash": stable_hash(str(input_item.get("descriptor", ""))),
            "ranked_candidates": ranked[:5],
            "decision": {
                "status": "matched" if matched else "unattributed_escrow",
                "accept_threshold": round(float(accept_threshold), 8),
                "best_asset_id": best.get("asset_id", "") if best else "",
                "best_creator_id": best.get("creator_id", "") if best else "",
                "decision_score": best.get("decision_score", 0.0) if best else 0.0,
                "payout": _money(current_item_pool if matched else Decimal("0")),
                "escrow_payout": _money(Decimal("0") if matched else current_item_pool),
            },
        }
        match["match_hash"] = hash_payload(match)
        matches.append(match)

    shares = [
        {
            "creator_id": creator_id,
            "asset_id": asset_id,
            "input_ids": sorted(payout_inputs[(creator_id, asset_id)]),
            "payout": _money(payout),
            "contribution_weight": round(float(payout / creator_pool), 8)
            if creator_pool
            else 0.0,
        }
        for (creator_id, asset_id), payout in sorted(payout_totals.items())
    ]
    if escrow_total:
        shares.append(
            {
                "creator_id": "unattributed_media_escrow",
                "asset_id": "escrow:unattributed_media",
                "payout": _money(escrow_total),
                "contribution_weight": round(float(escrow_total / creator_pool), 8)
                if creator_pool
                else 0.0,
            }
        )

    matched_count = len([item for item in matches if item["decision"]["status"] == "matched"])
    media_type_counts: defaultdict[str, int] = defaultdict(int)
    for item in submitted_media:
        media_type_counts[str(item.get("media_type", ""))] += 1
    report = {
        "report_version": MEDIA_ATTRIBUTION_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": {
            "profile": "rdllm-media-attribution-policy/v1",
            "supported_media_types": list(SUPPORTED_MEDIA_TYPES),
            "accept_threshold": round(float(accept_threshold), 8),
            "creator_pool_rate": str(rate),
            "matching_signals": [
                "content_hash",
                "perceptual_hash",
                "descriptor_similarity",
            ],
        },
        "economics": {
            "gross_revenue": _money(gross),
            "creator_pool": _money(creator_pool),
            "item_pool": _money(item_pool),
            "payout_total": _money(sum((Decimal(share["payout"]) for share in shares), Decimal("0"))),
            "escrow_total": _money(escrow_total),
        },
        "matches": matches,
        "royalty_shares": shares,
        "commitments": {
            "media_corpus_root": hash_payload(
                [
                    {
                        "asset_id": asset.get("asset_id", ""),
                        "creator_id": asset.get("creator_id", ""),
                        "media_type": asset.get("media_type", ""),
                        "content_hash": _asset_hash(asset),
                        "perceptual_hash_commitment": stable_hash(
                            str(asset.get("perceptual_hash", ""))
                        ),
                        "descriptor_hash": stable_hash(str(asset.get("descriptor", ""))),
                    }
                    for asset in media_corpus.get("assets", [])
                ]
            ),
            "submitted_media_root": hash_payload(
                [
                    {
                        "input_id": item.get("input_id", ""),
                        "media_type": item.get("media_type", ""),
                        "input_hash": _input_hash(item),
                        "perceptual_hash_commitment": stable_hash(
                            str(item.get("perceptual_hash", ""))
                        ),
                        "descriptor_hash": stable_hash(str(item.get("descriptor", ""))),
                    }
                    for item in submitted_media
                ]
            ),
            "match_root": hash_payload([item["match_hash"] for item in matches]),
            "share_root": hash_payload(shares),
        },
        "summary": {
            "status": "ready",
            "input_count": len(submitted_media),
            "matched_count": matched_count,
            "escrow_count": len(submitted_media) - matched_count,
            "media_type_counts": dict(sorted(media_type_counts.items())),
            "creator_count": len({share["creator_id"] for share in shares if not share["creator_id"].endswith("_escrow")}),
            "asset_count": len({share["asset_id"] for share in shares if not str(share["asset_id"]).startswith("escrow:")}),
            "creator_pool_conserved": (
                sum((Decimal(share["payout"]) for share in shares), Decimal("0"))
                == creator_pool
            ),
            "multimodal_source_attribution": True,
        },
        "privacy": {
            "raw_media_disclosed": False,
            "raw_descriptor_disclosed": False,
            "perceptual_hash_disclosed": False,
            "report_uses_hashes_scores_and_asset_ids": True,
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


def validate_media_attribution_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "economics",
        "matches",
        "royalty_shares",
        "commitments",
        "summary",
        "privacy",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing media attribution field: {key}")
    if errors:
        return errors
    if report.get("report_version") != MEDIA_ATTRIBUTION_VERSION:
        errors.append("media attribution report version is unsupported")
    for match in report.get("matches", []):
        for key in ("input_id", "media_type", "input_hash", "ranked_candidates", "decision", "match_hash"):
            if key not in match:
                errors.append(f"missing media attribution match field: {key}")
    return errors


def verify_media_attribution_report(
    report: dict[str, Any],
    media_corpus: dict[str, Any],
    submitted_media: list[dict[str, Any]],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify a media attribution report."""

    errors = validate_media_attribution_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("media attribution report hash is not reproducible")

    expected = make_media_attribution_report(
        media_corpus,
        submitted_media,
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
        "policy",
        "economics",
        "matches",
        "royalty_shares",
        "commitments",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"media attribution {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("media attribution report hash does not match replay")

    if report.get("summary", {}).get("creator_pool_conserved") is not True:
        errors.append("media attribution creator pool is not conserved")
    rendered = canonical_json(report)
    for value in _private_strings(media_corpus, submitted_media):
        if value in rendered:
            errors.append("media attribution report leaks raw descriptor text")
            break

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("media attribution report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("media attribution report signature is invalid")
    return errors
