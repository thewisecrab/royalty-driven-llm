"""Semantic text attribution reports for paraphrased and transformed outputs."""

from __future__ import annotations

import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

from rdllm.engine import RoyaltyDrivenLLM
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
    ngram_containment,
    stable_hash,
    tokenize,
)

SEMANTIC_TEXT_ATTRIBUTION_VERSION = "rdllm-semantic-text-attribution/v1"
SEMANTIC_TEXT_POLICY_VERSION = "rdllm-semantic-text-attribution-policy/v1"
DEFAULT_CREATOR_POOL_RATE = Decimal("0.55")
DEFAULT_ACCEPT_THRESHOLD = 0.24
DEFAULT_MIN_MARGIN = 0.03
MONEY_QUANT = Decimal("0.000001")

SYNONYM_GROUPS = {
    "appeal": {"appeal", "review", "redress"},
    "approve": {"approve", "approval", "authorize", "authorized", "permission", "permit", "permitted", "consent"},
    "attribution": {"attribution", "attribute", "credit", "credited", "citation", "cite", "source"},
    "audit": {"audit", "auditable", "replay", "replayable", "verify", "verified", "verification"},
    "challenge": {"challenge", "challenged", "contest", "dispute", "disputed", "object"},
    "claim": {"claim", "claims", "ownership", "owner", "duplicate"},
    "creator": {"creator", "creators", "author", "authors", "artist", "artists", "rightsholder", "rightsholders"},
    "hash": {"hash", "hashes", "fingerprint", "digest", "identifier", "identifiers"},
    "ledger": {"ledger", "record", "records", "log", "logs"},
    "license": {"license", "licenses", "licensing", "terms", "condition", "conditions"},
    "market": {"market", "marketplace", "exchange", "platform"},
    "payout": {"payout", "payouts", "payment", "payments", "royalty", "royalties", "remuneration"},
    "policy": {"policy", "policies", "rights", "rule", "rules", "restriction", "restrictions"},
    "provenance": {"provenance", "origin", "lineage", "trail"},
}

SYNONYM_LOOKUP = {
    token: concept
    for concept, tokens in SYNONYM_GROUPS.items()
    for token in tokens
}


def load_semantic_text_inputs(path: str | Path) -> list[dict[str, Any]]:
    """Load submitted text outputs for semantic attribution."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [dict(item) for item in data]
    return [dict(item) for item in data.get("outputs", [])]


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY_QUANT))


def _stem(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    for suffix in ("ing", "ation", "ions", "ion", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) > len(suffix) + 3:
            return token[: -len(suffix)]
    return token


def _semantic_tokens(text: str) -> list[str]:
    tokens = []
    for token in tokenize(text):
        stem = _stem(token)
        tokens.append(SYNONYM_LOOKUP.get(token, SYNONYM_LOOKUP.get(stem, stem)))
    return tokens


def _semantic_counter(text: str) -> Counter[str]:
    return Counter(_semantic_tokens(text))


def _weighted_overlap(
    left: Counter[str],
    right: Counter[str],
    idf: dict[str, float],
) -> float:
    if not left or not right:
        return 0.0
    overlap = set(left) & set(right)
    numerator = sum(min(left[token], right[token]) * idf.get(token, 1.0) for token in overlap)
    denominator = sum(left[token] * idf.get(token, 1.0) for token in left)
    if denominator <= 0:
        return 0.0
    return min(1.0, numerator / denominator)


def _semantic_idf(engine: RoyaltyDrivenLLM) -> dict[str, float]:
    document_counts: Counter[str] = Counter()
    for chunk in engine.chunks:
        document_counts.update(set(_semantic_tokens(chunk.text)))
    total = max(1, len(engine.chunks))
    return {
        token: 1.0 + (total / (1 + count))
        for token, count in document_counts.items()
    }


def _input_row(item: dict[str, Any], index: int, default_gross_revenue: Decimal) -> dict[str, Any]:
    input_id = str(item.get("input_id") or f"semantic_input_{index}")
    prompt = str(item.get("prompt", ""))
    output = str(item.get("output", ""))
    gross = Decimal(str(item.get("gross_revenue", default_gross_revenue))).quantize(
        MONEY_QUANT
    )
    return {
        "input_id": input_id,
        "prompt_hash": stable_hash(prompt),
        "output_hash": stable_hash(output),
        "output_semantic_fingerprint": hash_payload(sorted(_semantic_counter(output).items())),
        "policy_use": str(item.get("policy_use", "external_attribution")),
        "gross_revenue": _money(gross),
    }


def _score_chunk(
    *,
    input_id: str,
    output: str,
    prompt_hash: str,
    output_hash: str,
    chunk: Any,
    idf: dict[str, float],
) -> dict[str, Any]:
    source_tokens = tokenize(chunk.text)
    output_tokens = tokenize(output)
    longest_length, longest_tokens = longest_common_token_sequence(source_tokens, output_tokens)
    exact_score = longest_length / len(source_tokens) if source_tokens else 0.0
    ngram_score = ngram_containment(
        source_tokens,
        output_tokens,
        size=min(5, max(1, len(source_tokens))),
    )
    sequence_score = min(1.0, longest_length / 30)
    token_overlap = jaccard_similarity(source_tokens, output_tokens)
    source_semantic = _semantic_counter(chunk.text)
    output_semantic = _semantic_counter(output)
    concept_overlap = jaccard_similarity(source_semantic.keys(), output_semantic.keys())
    distinctiveness = _weighted_overlap(source_semantic, output_semantic, idf)
    semantic_density = min(1.0, len(set(source_semantic) & set(output_semantic)) / 8)
    decision_score = min(
        1.0,
        (
            0.18 * exact_score
            + 0.12 * ngram_score
            + 0.12 * sequence_score
            + 0.18 * token_overlap
            + 0.25 * concept_overlap
            + 0.10 * distinctiveness
            + 0.05 * semantic_density
        ),
    )
    scores = {
        "exact_sequence": round(exact_score, 8),
        "ngram_containment": round(ngram_score, 8),
        "longest_sequence": round(sequence_score, 8),
        "token_overlap": round(token_overlap, 8),
        "concept_overlap": round(concept_overlap, 8),
        "source_distinctiveness": round(distinctiveness, 8),
        "semantic_density": round(semantic_density, 8),
        "decision_score": round(decision_score, 8),
    }
    feature_payload = {
        "input_id": input_id,
        "chunk_id": chunk.chunk_id,
        "prompt_hash": prompt_hash,
        "output_hash": output_hash,
        "source_content_hash": chunk.content_hash,
        "source_semantic_fingerprint": hash_payload(sorted(source_semantic.items())),
        "output_semantic_fingerprint": hash_payload(sorted(output_semantic.items())),
        "matched_sequence_hash": stable_hash(" ".join(longest_tokens)) if longest_tokens else "",
        "scores": scores,
    }
    return {
        "input_id": input_id,
        "work_id": chunk.work_id,
        "chunk_id": chunk.chunk_id,
        "creator_id": chunk.creator_id,
        "title": chunk.title,
        "source_uri": chunk.source_uri,
        "content_hash": chunk.content_hash,
        "scores": scores,
        "feature_commitment": hash_payload(feature_payload),
        "rank": 0,
    }


def _ranked_rows(
    engine: RoyaltyDrivenLLM,
    inputs: list[dict[str, Any]],
    *,
    default_gross_revenue: Decimal,
    accept_threshold: float,
    min_margin: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    idf = _semantic_idf(engine)
    input_rows: list[dict[str, Any]] = []
    match_rows: list[dict[str, Any]] = []
    for index, item in enumerate(inputs, start=1):
        row = _input_row(item, index, default_gross_revenue)
        input_rows.append(row)
        output = str(item.get("output", ""))
        candidates = [
            _score_chunk(
                input_id=row["input_id"],
                output=output,
                prompt_hash=row["prompt_hash"],
                output_hash=row["output_hash"],
                chunk=chunk,
                idf=idf,
            )
            for chunk in engine.chunks
        ]
        candidates.sort(
            key=lambda candidate: (
                -float(candidate["scores"]["decision_score"]),
                str(candidate["work_id"]),
                str(candidate["chunk_id"]),
            )
        )
        top_score = float(candidates[0]["scores"]["decision_score"]) if candidates else 0.0
        second_score = (
            float(candidates[1]["scores"]["decision_score"]) if len(candidates) > 1 else 0.0
        )
        margin = round(top_score - second_score, 8)
        for rank, candidate in enumerate(candidates, start=1):
            chunk = engine.chunk_by_id[candidate["chunk_id"]]
            decision = engine.policy_engine.evaluate_chunk(
                chunk,
                row["policy_use"],
                jurisdiction=engine.jurisdiction,
                creator_pool_rate=engine.creator_pool_rate,
            )
            score = float(candidate["scores"]["decision_score"])
            is_top = rank == 1
            accepted = (
                is_top
                and score >= accept_threshold
                and (margin >= min_margin or score >= 0.50)
            )
            if accepted and not decision.allowed:
                status = "rights_conflict_escrow"
            elif accepted:
                status = "accepted"
            elif is_top and score >= accept_threshold:
                status = "ambiguous_semantic_escrow"
            else:
                status = "below_threshold"
            candidate.update(
                {
                    "rank": rank,
                    "decoy_margin": margin if is_top else 0.0,
                    "policy_allowed": decision.allowed,
                    "policy_reasons": list(decision.reasons),
                    "decision": status,
                }
            )
            match_rows.append(candidate)
    return input_rows, match_rows


def _allocate(
    input_rows: list[dict[str, Any]],
    match_rows: list[dict[str, Any]],
    *,
    creator_pool_rate: Decimal,
) -> tuple[list[dict[str, Any]], Decimal]:
    shares: list[dict[str, Any]] = []
    escrow_total = Decimal("0")
    rows_by_input: dict[str, list[dict[str, Any]]] = {}
    for row in match_rows:
        rows_by_input.setdefault(str(row["input_id"]), []).append(row)
    for input_row in input_rows:
        creator_pool_per_input = (
            Decimal(str(input_row.get("gross_revenue", "0"))) * creator_pool_rate
        ).quantize(MONEY_QUANT)
        rows = rows_by_input.get(str(input_row["input_id"]), [])
        accepted = [row for row in rows if row["decision"] == "accepted"]
        blocked = [row for row in rows if row["decision"] == "rights_conflict_escrow"]
        ambiguous = [row for row in rows if row["decision"] == "ambiguous_semantic_escrow"]
        if blocked:
            escrow_total += creator_pool_per_input
            shares.append(
                {
                    "input_id": input_row["input_id"],
                    "creator_id": "rights_conflict_escrow",
                    "work_id": "escrow:rights_conflict",
                    "chunk_id": "escrow:rights_conflict",
                    "decision": "rights_conflict_escrow",
                    "payout": _money(creator_pool_per_input),
                    "contribution_weight": 1.0,
                    "decision_score": blocked[0]["scores"]["decision_score"],
                }
            )
            continue
        if accepted:
            winner = accepted[0]
            shares.append(
                {
                    "input_id": input_row["input_id"],
                    "creator_id": winner["creator_id"],
                    "work_id": winner["work_id"],
                    "chunk_id": winner["chunk_id"],
                    "decision": "accepted",
                    "payout": _money(creator_pool_per_input),
                    "contribution_weight": 1.0,
                    "decision_score": winner["scores"]["decision_score"],
                }
            )
            continue
        escrow_total += creator_pool_per_input
        reason = "ambiguous_semantic_escrow" if ambiguous else "semantic_text_escrow"
        shares.append(
            {
                "input_id": input_row["input_id"],
                "creator_id": "semantic_text_escrow",
                "work_id": "escrow:semantic_text",
                "chunk_id": "escrow:semantic_text",
                "decision": reason,
                "payout": _money(creator_pool_per_input),
                "contribution_weight": 1.0,
                "decision_score": rows[0]["scores"]["decision_score"] if rows else 0.0,
            }
        )
    return shares, escrow_total


def _source_footers(
    input_rows: list[dict[str, Any]],
    match_rows: list[dict[str, Any]],
    shares: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Render public source-footer rows without prompt, answer, or source text."""

    rows_by_input: dict[str, list[dict[str, Any]]] = {}
    for row in match_rows:
        rows_by_input.setdefault(str(row["input_id"]), []).append(row)
    shares_by_input = {str(share["input_id"]): share for share in shares}
    footers: list[dict[str, Any]] = []
    for input_row in input_rows:
        input_id = str(input_row["input_id"])
        share = shares_by_input[input_id]
        accepted_rows = [
            row
            for row in rows_by_input.get(input_id, [])
            if row["chunk_id"] == share["chunk_id"] and row["decision"] == "accepted"
        ]
        if accepted_rows:
            row = accepted_rows[0]
            source = {
                "label": "S1",
                "title": row["title"],
                "work_id": row["work_id"],
                "chunk_id": row["chunk_id"],
                "creator_id": row["creator_id"],
                "source_uri": row["source_uri"],
                "content_hash": row["content_hash"],
                "decision_score": row["scores"]["decision_score"],
                "decoy_margin": row["decoy_margin"],
            }
            footer_text = (
                "Sources: [S1] "
                f"{source['title']} ({source['source_uri']}) "
                f"hash={str(source['content_hash'])[:18]} score={source['decision_score']}"
            )
            footers.append(
                {
                    "input_id": input_id,
                    "footer_status": "attributed",
                    "sources": [source],
                    "escrow": None,
                    "footer_text_hash": stable_hash(footer_text),
                    "footer_text_preview": footer_text,
                }
            )
            continue

        footer_text = (
            "Sources: no registered source passed semantic attribution; "
            f"creator pool routed to {share['decision']}."
        )
        footers.append(
            {
                "input_id": input_id,
                "footer_status": str(share["decision"]),
                "sources": [],
                "escrow": {
                    "creator_id": share["creator_id"],
                    "work_id": share["work_id"],
                    "chunk_id": share["chunk_id"],
                    "decision": share["decision"],
                    "payout": share["payout"],
                },
                "footer_text_hash": stable_hash(footer_text),
                "footer_text_preview": footer_text,
            }
        )
    return footers


def _private_strings(engine: RoyaltyDrivenLLM, inputs: list[dict[str, Any]]) -> list[str]:
    values = [work.content for work in engine.works.values()]
    for item in inputs:
        values.append(str(item.get("prompt", "")))
        values.append(str(item.get("output", "")))
    return [value for value in values if len(value.strip()) >= 16]


def make_semantic_text_attribution_report(
    engine: RoyaltyDrivenLLM,
    inputs: list[dict[str, Any]],
    *,
    gross_revenue: Decimal | str | float = Decimal("1.00"),
    creator_pool_rate: Decimal | str | float = DEFAULT_CREATOR_POOL_RATE,
    accept_threshold: float = DEFAULT_ACCEPT_THRESHOLD,
    min_margin: float = DEFAULT_MIN_MARGIN,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed attribution report for paraphrased or transformed text."""

    gross = Decimal(str(gross_revenue)).quantize(MONEY_QUANT)
    rate = Decimal(str(creator_pool_rate))
    input_rows, match_rows = _ranked_rows(
        engine,
        inputs,
        default_gross_revenue=gross,
        accept_threshold=accept_threshold,
        min_margin=min_margin,
    )
    shares, escrow_total = _allocate(
        input_rows,
        match_rows,
        creator_pool_rate=rate,
    )
    footers = _source_footers(input_rows, match_rows, shares)
    gross_total = sum(
        (Decimal(str(row["gross_revenue"])) for row in input_rows), Decimal("0")
    ).quantize(MONEY_QUANT)
    creator_pool_total = (gross_total * rate).quantize(MONEY_QUANT)
    payout_total = sum((Decimal(str(share["payout"])) for share in shares), Decimal("0"))
    accepted_count = len([share for share in shares if share["decision"] == "accepted"])
    report = {
        "report_version": SEMANTIC_TEXT_ATTRIBUTION_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": {
            "profile": SEMANTIC_TEXT_POLICY_VERSION,
            "creator_pool_rate": str(rate),
            "accept_threshold": round(float(accept_threshold), 8),
            "min_decoy_margin": round(float(min_margin), 8),
            "accepted_decision": "accepted",
            "ambiguous_decision": "ambiguous_semantic_escrow",
            "unmatched_decision": "semantic_text_escrow",
            "policy_block_decision": "rights_conflict_escrow",
        },
        "economics": {
            "default_gross_revenue_per_input": _money(gross),
            "gross_revenue_total": _money(gross_total),
            "creator_pool_total": _money(creator_pool_total),
            "payout_total": _money(payout_total),
            "escrow_total": _money(escrow_total),
        },
        "submitted_outputs": input_rows,
        "match_rows": match_rows,
        "royalty_shares": shares,
        "source_footers": footers,
        "commitments": {
            "input_root": hash_payload(input_rows),
            "match_row_root": hash_payload(match_rows),
            "share_root": hash_payload(shares),
            "footer_root": hash_payload(footers),
            "policy_root": hash_payload(
                [
                    {
                        "chunk_id": chunk.chunk_id,
                        "work_id": chunk.work_id,
                        "content_hash": chunk.content_hash,
                        "policy_id": chunk.policy_id,
                        "allowed_uses": sorted(chunk.allowed_uses),
                        "prohibited_uses": sorted(chunk.prohibited_uses),
                        "revoked": chunk.revoked,
                    }
                    for chunk in engine.chunks
                ]
            ),
        },
        "summary": {
            "status": "ready",
            "input_count": len(input_rows),
            "candidate_row_count": len(match_rows),
            "accepted_input_count": accepted_count,
            "escrow_input_count": len(input_rows) - accepted_count,
            "source_footer_count": len(footers),
            "rights_conflict_count": len(
                [share for share in shares if share["decision"] == "rights_conflict_escrow"]
            ),
            "creator_pool_conserved": payout_total == creator_pool_total,
            "semantic_text_attribution": True,
        },
        "privacy": {
            "source_text_disclosed": False,
            "prompt_text_disclosed": False,
            "output_text_disclosed": False,
            "matched_text_disclosed": False,
            "footer_discloses_source_ids_not_text": True,
            "semantic_fingerprints_disclosed_as_hashes": True,
            "report_uses_scores_hashes_and_source_ids": True,
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


def validate_semantic_text_attribution_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "economics",
        "submitted_outputs",
        "match_rows",
        "royalty_shares",
        "source_footers",
        "commitments",
        "summary",
        "privacy",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing semantic text attribution field: {key}")
    if errors:
        return errors
    if report.get("report_version") != SEMANTIC_TEXT_ATTRIBUTION_VERSION:
        errors.append("semantic text attribution report version is unsupported")
    if report.get("policy", {}).get("profile") != SEMANTIC_TEXT_POLICY_VERSION:
        errors.append("semantic text attribution policy profile is unsupported")
    for row in report.get("match_rows", []):
        for key in (
            "input_id",
            "work_id",
            "chunk_id",
            "creator_id",
            "content_hash",
            "scores",
            "feature_commitment",
            "rank",
            "decoy_margin",
            "policy_allowed",
            "decision",
        ):
            if key not in row:
                errors.append(f"missing semantic match row field: {key}")
    for footer in report.get("source_footers", []):
        for key in (
            "input_id",
            "footer_status",
            "sources",
            "escrow",
            "footer_text_hash",
            "footer_text_preview",
        ):
            if key not in footer:
                errors.append(f"missing semantic source footer field: {key}")
    return errors


def verify_semantic_text_attribution_report(
    report: dict[str, Any],
    engine: RoyaltyDrivenLLM,
    inputs: list[dict[str, Any]],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify a semantic text attribution report."""

    errors = validate_semantic_text_attribution_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("semantic text attribution report hash is not reproducible")

    expected = make_semantic_text_attribution_report(
        engine,
        inputs,
        gross_revenue=report.get("economics", {}).get(
            "default_gross_revenue_per_input", "1.00"
        ),
        creator_pool_rate=report.get("policy", {}).get(
            "creator_pool_rate", str(DEFAULT_CREATOR_POOL_RATE)
        ),
        accept_threshold=float(
            report.get("policy", {}).get("accept_threshold", DEFAULT_ACCEPT_THRESHOLD)
        ),
        min_margin=float(report.get("policy", {}).get("min_decoy_margin", DEFAULT_MIN_MARGIN)),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "economics",
        "submitted_outputs",
        "match_rows",
        "royalty_shares",
        "source_footers",
        "commitments",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"semantic text attribution {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("semantic text attribution report hash does not match replay")

    if report.get("summary", {}).get("creator_pool_conserved") is not True:
        errors.append("semantic text attribution creator pool is not conserved")

    rendered = canonical_json(report)
    for value in _private_strings(engine, inputs):
        if value in rendered:
            errors.append("semantic text attribution report leaks private text")
            break

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("semantic text attribution report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("semantic text attribution report signature is invalid")
    return errors
