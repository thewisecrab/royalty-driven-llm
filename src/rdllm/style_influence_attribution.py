"""Style and voice influence attribution for non-verbatim generated outputs.

This layer handles the gap between copied text/source attribution and broad
creative imitation. It credits a registered creator style only when the output
matches a licensed style profile, does not merely copy protected source text,
and remains separated from anti-style decoys.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
from math import sqrt
from pathlib import Path
from typing import Any

import json
import re

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

STYLE_INFLUENCE_ATTRIBUTION_VERSION = "rdllm-style-influence-attribution/v1"
STYLE_INFLUENCE_ATTRIBUTION_SCHEMA = (
    "docs/schemas/style_influence_attribution_report.schema.json"
)
STYLE_INFLUENCE_POLICY_VERSION = "rdllm-style-influence-attribution-policy/v1"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L90"

DEFAULT_CREATOR_POOL_RATE = Decimal("0.55")
DEFAULT_ACCEPT_THRESHOLD = 0.42
DEFAULT_MIN_STYLE_MARGIN = 0.04
DEFAULT_MIN_ANTI_MARGIN = 0.08
DEFAULT_MAX_CONTENT_OVERLAP = 0.35
DEFAULT_BLEND_WINDOW = 0.08
MONEY_QUANT = Decimal("0.000001")

STYLE_ROLES = {"candidate", "style_candidate", "reference_style"}
ANTI_STYLE_ROLES = {"anti_style", "style_decoy", "forbidden_style", "negative_style"}
STYLE_ALLOWED_USES = {
    "style_generation",
    "style_imitation",
    "voice_generation",
    "voice_imitation",
    "style_influence",
    "external_attribution",
}
SUPPORTED_MODALITIES = {"text", "image", "audio", "video", "3d", "music"}

FUNCTION_WORDS = (
    "a",
    "about",
    "after",
    "again",
    "all",
    "also",
    "although",
    "and",
    "as",
    "because",
    "but",
    "can",
    "cannot",
    "could",
    "for",
    "from",
    "however",
    "if",
    "in",
    "into",
    "is",
    "it",
    "just",
    "more",
    "must",
    "not",
    "of",
    "on",
    "or",
    "perhaps",
    "really",
    "should",
    "so",
    "than",
    "that",
    "the",
    "therefore",
    "through",
    "to",
    "very",
    "we",
    "while",
    "with",
    "without",
    "would",
    "you",
)


def load_style_influence_input(path: str | Path) -> dict[str, Any]:
    """Load private style-influence attribution inputs."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _hashable_row(row: dict[str, Any], hash_field: str) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != hash_field}


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY_QUANT))


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _event(style_input: dict[str, Any]) -> dict[str, Any]:
    event = style_input.get("event", {})
    prompt = str(event.get("prompt_text", ""))
    output = str(event.get("output_text", event.get("response_text", "")))
    return {
        "event_id": str(event.get("event_id", "")),
        "event_hash": str(event.get("event_hash") or stable_hash(output)),
        "prompt_hash": str(event.get("prompt_hash") or stable_hash(prompt)),
        "output_hash": str(event.get("output_hash") or stable_hash(output)),
        "model_id": str(event.get("model_id", "")),
        "model_version": str(event.get("model_version", "")),
        "declared_style_profile_ids": sorted(
            str(item) for item in event.get("declared_style_profile_ids", [])
        ),
        "declared_style_creator_ids": sorted(
            str(item) for item in event.get("declared_style_creator_ids", [])
        ),
    }


def _style_outputs(style_input: dict[str, Any]) -> list[dict[str, Any]]:
    outputs = style_input.get("style_outputs") or style_input.get("outputs")
    if not outputs:
        event = style_input.get("event", {})
        outputs = [
            {
                "output_id": event.get("event_id", "output_1"),
                "modality": event.get("modality", "text"),
                "output_text": event.get("output_text", event.get("response_text", "")),
                "descriptor": event.get("descriptor", ""),
                "perceptual_hash": event.get("perceptual_hash", ""),
                "declared_style_profile_ids": event.get(
                    "declared_style_profile_ids", []
                ),
                "declared_style_creator_ids": event.get(
                    "declared_style_creator_ids", []
                ),
            }
        ]
    return [dict(item) for item in outputs]


def _profile_id(profile: dict[str, Any], index: int) -> str:
    return str(
        profile.get("profile_id")
        or profile.get("style_id")
        or profile.get("asset_id")
        or f"style_profile_{index}"
    )


def _profile_role(profile: dict[str, Any]) -> str:
    return str(profile.get("source_role", profile.get("profile_role", "candidate")))


def _modality(item: dict[str, Any]) -> str:
    modality = str(item.get("modality", item.get("media_type", "text"))).lower()
    return modality if modality in SUPPORTED_MODALITIES else "text"


def _license_allowed(profile: dict[str, Any], use: str) -> bool:
    status = str(profile.get("license_status", "inactive")).lower()
    if status not in {"active", "licensed", "permitted"}:
        return False
    allowed = {
        str(item).lower()
        for item in profile.get("allowed_uses", profile.get("license_uses", []))
    }
    if not allowed:
        return bool(profile.get("style_royalty_allowed", False))
    return use.lower() in allowed or bool(allowed & STYLE_ALLOWED_USES)


def _feature_commitment(features: dict[str, float]) -> str:
    return hash_payload(
        sorted((key, round(float(value), 8)) for key, value in features.items())
    )


def _char_ngrams(text: str, size: int = 3) -> Counter[str]:
    cleaned = re.sub(r"\s+", " ", text.lower()).strip()
    counts: Counter[str] = Counter()
    for index in range(max(0, len(cleaned) - size + 1)):
        gram = cleaned[index : index + size]
        if len(gram.strip()) >= 2:
            counts[f"char3:{stable_hash(gram)[:12]}"] += 1
    return counts


def _text_style_features(texts: list[str]) -> dict[str, float]:
    text = "\n".join(part for part in texts if str(part).strip())
    tokens = tokenize(text)
    token_count = max(1, len(tokens))
    sentences = [
        part.strip()
        for part in re.split(r"[.!?]+", text)
        if part.strip()
    ]
    sentence_count = max(1, len(sentences))
    features: dict[str, float] = {
        "token_count_log": min(1.0, token_count / 400.0),
        "avg_sentence_length": min(1.0, token_count / sentence_count / 40.0),
        "avg_word_length": min(1.0, (sum(len(token) for token in tokens) / token_count) / 12.0),
        "type_token_ratio": len(set(tokens)) / token_count,
        "comma_per_sentence": min(1.0, text.count(",") / sentence_count / 3.0),
        "semicolon_per_sentence": min(1.0, text.count(";") / sentence_count),
        "colon_per_sentence": min(1.0, text.count(":") / sentence_count),
        "question_per_sentence": min(1.0, text.count("?") / sentence_count),
        "exclamation_per_sentence": min(1.0, text.count("!") / sentence_count),
        "quote_per_token": min(1.0, (text.count('"') + text.count("'")) / token_count),
        "paren_per_token": min(1.0, (text.count("(") + text.count(")")) / token_count),
    }
    token_counter = Counter(tokens)
    for word in FUNCTION_WORDS:
        features[f"fw:{word}"] = token_counter.get(word, 0) / token_count
    ngrams = _char_ngrams(text)
    total_ngrams = max(1, sum(ngrams.values()))
    for key, count in ngrams.most_common(64):
        features[key] = count / total_ngrams
    return features


def _descriptor_features(text: str) -> dict[str, float]:
    tokens = tokenize(text)
    token_count = max(1, len(tokens))
    counter = Counter(tokens)
    return {f"desc:{stable_hash(token)[:12]}": count / token_count for token, count in counter.items()}


def _features_for_profile(profile: dict[str, Any]) -> dict[str, float]:
    if isinstance(profile.get("feature_vector"), dict):
        return {
            str(key): float(value)
            for key, value in profile["feature_vector"].items()
            if isinstance(value, (int, float))
        }
    if _modality(profile) == "text":
        examples = [
            str(item)
            for item in profile.get("style_examples", profile.get("examples", []))
            if str(item).strip()
        ]
        if not examples and profile.get("descriptor"):
            examples = [str(profile.get("descriptor", ""))]
        return _text_style_features(examples)
    return _descriptor_features(str(profile.get("descriptor", "")))


def _features_for_output(output: dict[str, Any]) -> dict[str, float]:
    if isinstance(output.get("feature_vector"), dict):
        return {
            str(key): float(value)
            for key, value in output["feature_vector"].items()
            if isinstance(value, (int, float))
        }
    if _modality(output) == "text":
        return _text_style_features(
            [str(output.get("output_text", output.get("text", "")))]
        )
    return _descriptor_features(str(output.get("descriptor", "")))


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    shared = set(left) & set(right)
    numerator = sum(left[key] * right[key] for key in shared)
    left_norm = sqrt(sum(value * value for value in left.values()))
    right_norm = sqrt(sum(value * value for value in right.values()))
    if left_norm <= 0 or right_norm <= 0:
        return 0.0
    return _clamp(numerator / (left_norm * right_norm))


def _hamming_similarity(left: str, right: str) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    distance = sum(1 for a, b in zip(left, right) if a != b)
    return 1.0 - distance / len(left)


def _profile_texts(profile: dict[str, Any]) -> list[str]:
    texts = [
        str(item)
        for item in profile.get("style_examples", profile.get("examples", []))
        if str(item).strip()
    ]
    if profile.get("descriptor"):
        texts.append(str(profile.get("descriptor", "")))
    return texts


def _content_overlap(output: dict[str, Any], profile: dict[str, Any]) -> float:
    output_text = str(output.get("output_text", output.get("text", "")))
    if not output_text:
        return 0.0
    output_tokens = tokenize(output_text)
    best = 0.0
    for source_text in _profile_texts(profile):
        source_tokens = tokenize(source_text)
        if not source_tokens:
            continue
        longest, _ = longest_common_token_sequence(source_tokens, output_tokens)
        sequence_ratio = longest / max(1, min(len(source_tokens), len(output_tokens)))
        token_overlap = jaccard_similarity(source_tokens, output_tokens)
        best = max(best, sequence_ratio, token_overlap)
    return round(_clamp(best), 8)


def _declared_intent_score(output: dict[str, Any], profile: dict[str, Any], event: dict[str, Any]) -> float:
    profile_id = str(profile.get("profile_id", ""))
    creator_id = str(profile.get("creator_id", ""))
    declared_profiles = {
        str(item)
        for item in output.get("declared_style_profile_ids", [])
    } | set(event.get("declared_style_profile_ids", []))
    declared_creators = {
        str(item)
        for item in output.get("declared_style_creator_ids", [])
    } | set(event.get("declared_style_creator_ids", []))
    return 1.0 if profile_id in declared_profiles or creator_id in declared_creators else 0.0


def _output_public_row(output: dict[str, Any], index: int, default_gross_revenue: Decimal) -> dict[str, Any]:
    output_text = str(output.get("output_text", output.get("text", "")))
    gross = Decimal(str(output.get("gross_revenue", default_gross_revenue))).quantize(
        MONEY_QUANT
    )
    features = _features_for_output(output)
    row = {
        "output_id": str(output.get("output_id") or f"style_output_{index}"),
        "modality": _modality(output),
        "output_hash": str(output.get("output_hash") or stable_hash(output_text or canonical_json(output))),
        "style_feature_commitment": _feature_commitment(features),
        "declared_style_profile_ids": sorted(
            str(item) for item in output.get("declared_style_profile_ids", [])
        ),
        "declared_style_creator_ids": sorted(
            str(item) for item in output.get("declared_style_creator_ids", [])
        ),
        "policy_use": str(output.get("policy_use", "style_generation")),
        "gross_revenue": _money(gross),
    }
    row["output_row_hash"] = hash_payload(row)
    return row


def _profile_public_row(profile: dict[str, Any], index: int) -> dict[str, Any]:
    profile_id = _profile_id(profile, index)
    features = _features_for_profile(profile)
    row = {
        "profile_id": profile_id,
        "work_id": str(profile.get("work_id", "")),
        "creator_id": str(profile.get("creator_id", "")),
        "title": str(profile.get("title", "")),
        "source_uri": str(profile.get("source_uri", "")),
        "modality": _modality(profile),
        "profile_role": _profile_role(profile),
        "license_status": str(profile.get("license_status", "inactive")),
        "license_term_hash": str(
            profile.get("license_term_hash")
            or stable_hash(canonical_json(profile.get("license_terms", {})))
        ),
        "style_feature_commitment": _feature_commitment(features),
        "example_count": len(profile.get("style_examples", profile.get("examples", []))),
    }
    row["profile_row_hash"] = hash_payload(row)
    return row


def _score_candidate(
    *,
    output: dict[str, Any],
    output_row: dict[str, Any],
    output_features: dict[str, float],
    profile: dict[str, Any],
    profile_row: dict[str, Any],
    event: dict[str, Any],
    max_content_overlap: float,
) -> dict[str, Any]:
    profile_features = _features_for_profile(profile)
    same_modality = output_row["modality"] == profile_row["modality"]
    style_similarity = _cosine(output_features, profile_features) if same_modality else 0.0
    perceptual_similarity = 0.0
    if output_row["modality"] != "text":
        perceptual_similarity = _hamming_similarity(
            str(output.get("perceptual_hash", "")),
            str(profile.get("perceptual_hash", "")),
        )
    content_overlap = _content_overlap(output, profile) if output_row["modality"] == "text" else 0.0
    declared_intent = _declared_intent_score(output, profile_row, event)
    role = profile_row["profile_role"]
    license_allowed = _license_allowed(profile, output_row["policy_use"])
    decision_score = _clamp(
        0.68 * style_similarity
        + 0.12 * perceptual_similarity
        + 0.20 * declared_intent
    )
    if content_overlap > max_content_overlap:
        decision_score = min(decision_score, 0.40)
    row = {
        "output_id": output_row["output_id"],
        "profile_id": profile_row["profile_id"],
        "work_id": profile_row["work_id"],
        "creator_id": profile_row["creator_id"],
        "title": profile_row["title"],
        "source_uri": profile_row["source_uri"],
        "modality": output_row["modality"],
        "profile_role": role,
        "style_similarity": round(style_similarity, 8),
        "perceptual_similarity": round(perceptual_similarity, 8),
        "declared_intent_score": round(declared_intent, 8),
        "content_overlap_score": round(content_overlap, 8),
        "license_allowed": license_allowed,
        "decision_score": round(decision_score, 8),
        "copy_overlap_guard_passed": content_overlap <= max_content_overlap,
        "rank": 0,
        "failure_reasons": [],
        "decision": "unranked",
    }
    row["feature_commitment"] = hash_payload(
        {
            "output_feature_commitment": output_row["style_feature_commitment"],
            "profile_feature_commitment": profile_row["style_feature_commitment"],
            "scores": {
                key: row[key]
                for key in (
                    "style_similarity",
                    "perceptual_similarity",
                    "declared_intent_score",
                    "content_overlap_score",
                    "decision_score",
                )
            },
        }
    )
    return row


def _private_strings(style_input: dict[str, Any]) -> list[str]:
    values: list[str] = []
    event = style_input.get("event", {})
    values.extend(
        [
            str(event.get("prompt_text", "")),
            str(event.get("output_text", event.get("response_text", ""))),
        ]
    )
    for output in _style_outputs(style_input):
        values.append(str(output.get("output_text", output.get("text", ""))))
        values.append(str(output.get("descriptor", "")))
    for profile in style_input.get("style_profiles", []):
        values.append(str(profile.get("descriptor", "")))
        values.extend(str(item) for item in profile.get("style_examples", profile.get("examples", [])))
    return [value for value in values if len(value.strip()) >= 16]


def _assign_decisions(
    rows_by_output: dict[str, list[dict[str, Any]]],
    *,
    accept_threshold: float,
    min_style_margin: float,
    min_anti_margin: float,
    max_content_overlap: float,
    blend_window: float,
) -> list[dict[str, Any]]:
    assigned: list[dict[str, Any]] = []
    for output_id, rows in rows_by_output.items():
        rows.sort(
            key=lambda row: (-float(row["decision_score"]), str(row["profile_id"]))
        )
        top_score = float(rows[0]["decision_score"]) if rows else 0.0
        best_anti = max(
            (
                float(row["decision_score"])
                for row in rows
                if row["profile_role"] in ANTI_STYLE_ROLES
            ),
            default=0.0,
        )
        candidate_scores = [
            float(row["decision_score"])
            for row in rows
            if row["profile_role"] not in ANTI_STYLE_ROLES
        ]
        best_candidate = max(candidate_scores, default=0.0)
        second_candidate = sorted(candidate_scores, reverse=True)[1] if len(candidate_scores) > 1 else 0.0
        accepted_for_output = 0
        for rank, row in enumerate(rows, start=1):
            row["rank"] = rank
            row["style_margin"] = round(
                best_candidate - second_candidate if row["decision_score"] == best_candidate else 0.0,
                8,
            )
            row["anti_style_margin"] = round(float(row["decision_score"]) - best_anti, 8)
            row["failure_reasons"] = []
            role = row["profile_role"]
            if role in ANTI_STYLE_ROLES:
                row["decision"] = "anti_style_rejected"
                row["failure_reasons"].append("profile_marked_as_anti_style")
            elif float(row["content_overlap_score"]) > max_content_overlap:
                row["decision"] = "copy_overlap_requires_semantic_attribution"
                row["failure_reasons"].append("content_overlap_exceeds_style_limit")
            elif float(row["decision_score"]) < accept_threshold:
                row["decision"] = "style_unattributed_escrow"
                row["failure_reasons"].append("style_score_below_threshold")
            elif top_score - float(row["decision_score"]) > blend_window:
                row["decision"] = "style_unattributed_escrow"
                row["failure_reasons"].append("outside_style_blend_window")
            elif best_candidate - second_candidate < min_style_margin and len(candidate_scores) > 1:
                row["decision"] = "style_unattributed_escrow"
                row["failure_reasons"].append("insufficient_style_margin")
            elif float(row["decision_score"]) - best_anti < min_anti_margin:
                row["decision"] = "style_unattributed_escrow"
                row["failure_reasons"].append("insufficient_anti_style_margin")
            elif not row["license_allowed"]:
                row["decision"] = "style_rights_escrow"
                row["failure_reasons"].append("style_license_not_active_for_use")
            else:
                row["decision"] = "accepted_style_influence"
                accepted_for_output += 1
            row["style_row_hash"] = hash_payload(_hashable_row(row, "style_row_hash"))
        if accepted_for_output == 0:
            for row in rows:
                if row["decision"] == "style_unattributed_escrow":
                    row["output_unattributed"] = True
                    row["style_row_hash"] = hash_payload(_hashable_row(row, "style_row_hash"))
        assigned.extend(rows)
    return assigned


def _allocate_shares(
    output_rows: list[dict[str, Any]],
    style_rows: list[dict[str, Any]],
    creator_pool: Decimal,
) -> tuple[list[dict[str, Any]], Decimal, Decimal]:
    pools: dict[str, Decimal] = {}
    total_gross = sum(Decimal(row["gross_revenue"]) for row in output_rows)
    if total_gross <= 0:
        for row in output_rows:
            pools[row["output_id"]] = Decimal("0")
    else:
        allocated = Decimal("0")
        for index, row in enumerate(output_rows, start=1):
            if index == len(output_rows):
                pool = creator_pool - allocated
            else:
                pool = (creator_pool * Decimal(row["gross_revenue"]) / total_gross).quantize(MONEY_QUANT)
                allocated += pool
            pools[row["output_id"]] = pool.quantize(MONEY_QUANT)

    rows_by_output: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in style_rows:
        rows_by_output[row["output_id"]].append(row)

    shares: list[dict[str, Any]] = []
    payout_total = Decimal("0")
    escrow_total = Decimal("0")
    for output in output_rows:
        output_id = output["output_id"]
        pool = pools[output_id]
        accepted = [
            row
            for row in rows_by_output.get(output_id, [])
            if row["decision"] == "accepted_style_influence"
        ]
        if not accepted:
            escrow_total += pool
            shares.append(
                {
                    "output_id": output_id,
                    "creator_id": "style_attribution_escrow",
                    "work_id": "escrow:style_influence",
                    "profile_id": "escrow:style_influence",
                    "decision": "style_escrow",
                    "payout": _money(Decimal("0")),
                    "escrow_payout": _money(pool),
                    "contribution_weight": 0.0,
                }
            )
            continue
        score_total = sum(Decimal(str(row["decision_score"])) for row in accepted)
        allocated = Decimal("0")
        for index, row in enumerate(accepted, start=1):
            if index == len(accepted):
                payout = pool - allocated
            else:
                payout = (pool * Decimal(str(row["decision_score"])) / score_total).quantize(MONEY_QUANT)
                allocated += payout
            payout = payout.quantize(MONEY_QUANT)
            payout_total += payout
            shares.append(
                {
                    "output_id": output_id,
                    "creator_id": row["creator_id"],
                    "work_id": row["work_id"],
                    "profile_id": row["profile_id"],
                    "decision": "accepted_style_influence",
                    "payout": _money(payout),
                    "escrow_payout": _money(Decimal("0")),
                    "contribution_weight": round(float(payout / creator_pool), 8)
                    if creator_pool
                    else 0.0,
                }
            )
    for share in shares:
        share["share_hash"] = hash_payload(share)
    return shares, payout_total, escrow_total


def make_style_influence_attribution_report(
    style_input: dict[str, Any],
    *,
    gross_revenue: Decimal | str | float = Decimal("1.00"),
    creator_pool_rate: Decimal | str | float = DEFAULT_CREATOR_POOL_RATE,
    accept_threshold: float = DEFAULT_ACCEPT_THRESHOLD,
    min_style_margin: float = DEFAULT_MIN_STYLE_MARGIN,
    min_anti_margin: float = DEFAULT_MIN_ANTI_MARGIN,
    max_content_overlap: float = DEFAULT_MAX_CONTENT_OVERLAP,
    blend_window: float = DEFAULT_BLEND_WINDOW,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a hash-only style influence report for generated outputs."""

    gross = Decimal(str(gross_revenue)).quantize(MONEY_QUANT)
    rate = Decimal(str(creator_pool_rate))
    creator_pool = (gross * rate).quantize(MONEY_QUANT)
    event = _event(style_input)
    outputs = _style_outputs(style_input)
    profiles = [dict(profile) for profile in style_input.get("style_profiles", [])]
    output_rows = [
        _output_public_row(output, index, gross / max(1, len(outputs)))
        for index, output in enumerate(outputs, start=1)
    ]
    profile_rows = [
        _profile_public_row(profile, index)
        for index, profile in enumerate(profiles, start=1)
    ]
    rows_by_output: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for output, output_row in zip(outputs, output_rows, strict=False):
        output_features = _features_for_output(output)
        for profile, profile_row in zip(profiles, profile_rows, strict=False):
            rows_by_output[output_row["output_id"]].append(
                _score_candidate(
                    output=output,
                    output_row=output_row,
                    output_features=output_features,
                    profile=profile,
                    profile_row=profile_row,
                    event=event,
                    max_content_overlap=max_content_overlap,
                )
            )
    style_rows = _assign_decisions(
        rows_by_output,
        accept_threshold=accept_threshold,
        min_style_margin=min_style_margin,
        min_anti_margin=min_anti_margin,
        max_content_overlap=max_content_overlap,
        blend_window=blend_window,
    )
    shares, payout_total, escrow_total = _allocate_shares(
        output_rows, style_rows, creator_pool
    )
    accepted_rows = [
        row for row in style_rows if row["decision"] == "accepted_style_influence"
    ]
    footer_rows = [
        {
            "output_id": row["output_id"],
            "profile_id": row["profile_id"],
            "work_id": row["work_id"],
            "creator_id": row["creator_id"],
            "title": row["title"],
            "source_uri": row["source_uri"],
            "attribution_channel": "style_influence",
            "modality": row["modality"],
            "style_similarity": row["style_similarity"],
            "style_feature_commitment": next(
                profile["style_feature_commitment"]
                for profile in profile_rows
                if profile["profile_id"] == row["profile_id"]
            ),
        }
        for row in accepted_rows
    ]
    for row in footer_rows:
        row["footer_row_hash"] = hash_payload(row)

    private_report_text = canonical_json(
        {
            "style_rows": style_rows,
            "footer_rows": footer_rows,
            "shares": shares,
            "output_rows": output_rows,
            "profile_rows": profile_rows,
        }
    )
    no_private_text = not any(
        value and value in private_report_text for value in _private_strings(style_input)
    )
    checks = {
        "style_credit_requires_license": all(
            row["license_allowed"]
            for row in accepted_rows
        ),
        "style_credit_requires_threshold": all(
            float(row["decision_score"]) >= accept_threshold for row in accepted_rows
        ),
        "style_credit_requires_margin": all(
            float(row["style_margin"]) >= min_style_margin for row in accepted_rows
        ),
        "style_credit_separated_from_anti_style": all(
            float(row["anti_style_margin"]) >= min_anti_margin for row in accepted_rows
        ),
        "copy_overlap_routes_away_from_style_payout": all(
            row["decision"] != "accepted_style_influence"
            or float(row["content_overlap_score"]) <= max_content_overlap
            for row in style_rows
        ),
        "anti_style_profiles_rejected": all(
            row["decision"] == "anti_style_rejected"
            for row in style_rows
            if row["profile_role"] in ANTI_STYLE_ROLES
        ),
        "accepted_styles_have_footer_rows": len(footer_rows) == len(accepted_rows),
        "creator_pool_conserved": payout_total + escrow_total == creator_pool,
        "public_report_does_not_embed_private_style_text": no_private_text,
    }
    status = "ready" if all(checks.values()) and bool(output_rows) and bool(profile_rows) else "failed"
    report = {
        "report_version": STYLE_INFLUENCE_ATTRIBUTION_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "event": event,
        "policy": {
            "profile": STYLE_INFLUENCE_POLICY_VERSION,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "supported_modalities": sorted(SUPPORTED_MODALITIES),
            "creator_pool_rate": str(rate),
            "accept_threshold": round(float(accept_threshold), 8),
            "min_style_margin": round(float(min_style_margin), 8),
            "min_anti_margin": round(float(min_anti_margin), 8),
            "max_content_overlap": round(float(max_content_overlap), 8),
            "blend_window": round(float(blend_window), 8),
            "accepted_decision": "accepted_style_influence",
            "copy_overlap_decision": "copy_overlap_requires_semantic_attribution",
            "license_block_decision": "style_rights_escrow",
            "unattributed_decision": "style_unattributed_escrow",
        },
        "economics": {
            "gross_revenue": _money(gross),
            "creator_pool": _money(creator_pool),
            "payout_total": _money(payout_total),
            "escrow_total": _money(escrow_total),
        },
        "style_outputs": output_rows,
        "style_profiles": profile_rows,
        "style_attribution": style_rows,
        "footer": {
            "style_footer_rows": footer_rows,
            "style_footer_count": len(footer_rows),
            "footer_hash": hash_payload(footer_rows),
        },
        "royalty_shares": shares,
        "commitments": {
            "style_input_root": hash_payload(style_input),
            "output_root": hash_payload(output_rows),
            "profile_root": hash_payload(profile_rows),
            "style_attribution_root": hash_payload(style_rows),
            "footer_root": hash_payload(footer_rows),
            "share_root": hash_payload(shares),
            "policy_root": hash_payload(
                {
                    "accept_threshold": round(float(accept_threshold), 8),
                    "min_style_margin": round(float(min_style_margin), 8),
                    "min_anti_margin": round(float(min_anti_margin), 8),
                    "max_content_overlap": round(float(max_content_overlap), 8),
                    "blend_window": round(float(blend_window), 8),
                }
            ),
        },
        "checks": checks,
        "schemas": {
            "style_influence_attribution_report": STYLE_INFLUENCE_ATTRIBUTION_SCHEMA
        },
        "summary": {
            "status": status,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "output_count": len(output_rows),
            "style_profile_count": len(profile_rows),
            "style_row_count": len(style_rows),
            "accepted_style_count": len(accepted_rows),
            "style_footer_count": len(footer_rows),
            "anti_style_rejection_count": len(
                [row for row in style_rows if row["decision"] == "anti_style_rejected"]
            ),
            "copy_overlap_rejection_count": len(
                [
                    row
                    for row in style_rows
                    if row["decision"] == "copy_overlap_requires_semantic_attribution"
                ]
            ),
            "license_block_count": len(
                [row for row in style_rows if row["decision"] == "style_rights_escrow"]
            ),
            "creator_pool_conserved": checks["creator_pool_conserved"],
            "footer_hash": hash_payload(footer_rows),
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "output_text_disclosed": False,
            "style_example_text_disclosed": False,
            "raw_style_descriptor_disclosed": False,
            "feature_vectors_disclosed": False,
            "report_uses_hashes_scores_and_public_profile_metadata": True,
        },
    }
    report["report_hash"] = hash_payload(_hashable_report(report))
    report["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": sign_payload(_hashable_report(report), signing_secret)
        if signing_secret
        else "",
    }
    return report


def validate_style_influence_attribution_report_shape(report: dict[str, Any]) -> list[str]:
    """Validate required public fields for a style-influence report."""

    required = [
        "report_version",
        "issuer",
        "created_at",
        "event",
        "policy",
        "economics",
        "style_outputs",
        "style_profiles",
        "style_attribution",
        "footer",
        "royalty_shares",
        "commitments",
        "checks",
        "schemas",
        "summary",
        "privacy",
        "report_hash",
        "signature",
    ]
    errors: list[str] = []
    for key in required:
        if key not in report:
            errors.append(f"missing style influence field: {key}")
    if errors:
        return errors
    if report.get("report_version") != STYLE_INFLUENCE_ATTRIBUTION_VERSION:
        errors.append("style influence report version is unsupported")
    policy = report.get("policy", {})
    if policy.get("profile") != STYLE_INFLUENCE_POLICY_VERSION:
        errors.append("style influence policy version is unsupported")
    if policy.get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("style influence target certification level is unsupported")
    if "style_influence_attribution_report" not in report.get("schemas", {}):
        errors.append("style influence schema binding is missing")
    for index, row in enumerate(report.get("style_attribution", []), start=1):
        for key in (
            "output_id",
            "profile_id",
            "work_id",
            "creator_id",
            "decision_score",
            "content_overlap_score",
            "license_allowed",
            "decision",
            "style_row_hash",
        ):
            if key not in row:
                errors.append(f"missing style attribution row {index} field: {key}")
        if row.get("style_row_hash") and hash_payload(_hashable_row(row, "style_row_hash")) != row.get("style_row_hash"):
            errors.append(f"style attribution row {index} hash is not reproducible")
    for index, share in enumerate(report.get("royalty_shares", []), start=1):
        if share.get("share_hash") and hash_payload(_hashable_row(share, "share_hash")) != share.get("share_hash"):
            errors.append(f"style royalty share {index} hash is not reproducible")
    return errors


def verify_style_influence_attribution_report(
    report: dict[str, Any],
    style_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify a style-influence attribution report."""

    errors = validate_style_influence_attribution_report_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get("report_hash", ""):
        errors.append("style influence report hash is not reproducible")
    policy = report.get("policy", {})
    economics = report.get("economics", {})
    try:
        expected = make_style_influence_attribution_report(
            style_input,
            gross_revenue=Decimal(str(economics.get("gross_revenue", "0"))),
            creator_pool_rate=Decimal(str(policy.get("creator_pool_rate", "0.55"))),
            accept_threshold=float(policy.get("accept_threshold", DEFAULT_ACCEPT_THRESHOLD)),
            min_style_margin=float(policy.get("min_style_margin", DEFAULT_MIN_STYLE_MARGIN)),
            min_anti_margin=float(policy.get("min_anti_margin", DEFAULT_MIN_ANTI_MARGIN)),
            max_content_overlap=float(policy.get("max_content_overlap", DEFAULT_MAX_CONTENT_OVERLAP)),
            blend_window=float(policy.get("blend_window", DEFAULT_BLEND_WINDOW)),
            issuer=str(report.get("issuer", DEFAULT_ISSUER)),
            created_at=str(report.get("created_at", "")),
            signing_secret=signing_secret,
        )
    except Exception as exc:  # pragma: no cover - defensive replay error reporting
        return errors + [f"style influence replay failed: {exc}"]
    for key in (
        "event",
        "policy",
        "economics",
        "style_outputs",
        "style_profiles",
        "style_attribution",
        "footer",
        "royalty_shares",
        "commitments",
        "checks",
        "summary",
        "privacy",
    ):
        if report.get(key) != expected.get(key):
            errors.append(f"style influence {key} does not match replay")
    if report.get("report_hash") != expected.get("report_hash"):
        errors.append("style influence report hash does not match replay")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("style influence report status is not ready")
    for check, passed in report.get("checks", {}).items():
        if not passed:
            errors.append(f"style influence check failed: {check}")
    report_text = canonical_json(report)
    for private in _private_strings(style_input):
        if private and private in report_text:
            errors.append("style influence report leaks private input text")
            break
    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("style influence report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("style influence report signature is invalid")
    return errors
