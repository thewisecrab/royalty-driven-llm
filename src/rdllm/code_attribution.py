"""License-aware attribution reports for generated code snippets."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
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
)

CODE_ATTRIBUTION_VERSION = "rdllm-code-attribution-report/v1"
CODE_ATTRIBUTION_SCHEMA = "docs/schemas/code_attribution_report.schema.json"
CODE_ATTRIBUTION_POLICY_VERSION = "rdllm-code-attribution-policy/v1"
DEFAULT_CREATOR_POOL_RATE = Decimal("0.55")
DEFAULT_ACCEPT_THRESHOLD = 0.34
DEFAULT_STRONG_COPY_THRESHOLD = 0.67
MONEY_QUANT = Decimal("0.000001")

IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
TOKEN_RE = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+|==|!=|<=|>=|[-+*/%]=?|[{}()[\].,:;]"
)

CODE_KEYWORDS = {
    "and",
    "as",
    "async",
    "await",
    "break",
    "case",
    "catch",
    "class",
    "const",
    "continue",
    "def",
    "default",
    "do",
    "elif",
    "else",
    "except",
    "false",
    "finally",
    "for",
    "from",
    "function",
    "if",
    "import",
    "in",
    "let",
    "match",
    "new",
    "none",
    "not",
    "null",
    "or",
    "return",
    "static",
    "switch",
    "true",
    "try",
    "var",
    "while",
    "with",
}

PERMISSIVE_LICENSES = {
    "apache-2.0",
    "bsd-2-clause",
    "bsd-3-clause",
    "cc0-1.0",
    "isc",
    "mit",
    "mpl-2.0",
    "royalty-bearing",
    "unlicense",
    "zlib",
}
COPYLEFT_LICENSES = {"gpl-2.0", "gpl-3.0", "lgpl-2.1", "lgpl-3.0"}
NETWORK_COPYLEFT_LICENSES = {"agpl-3.0"}
RESTRICTED_LICENSES = {"all-rights-reserved", "no-ai", "proprietary", "restricted"}


def load_code_attribution_inputs(path: str | Path) -> list[dict[str, Any]]:
    """Load submitted generated-code outputs for attribution."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [dict(item) for item in data]
    return [dict(item) for item in data.get("outputs", data.get("code_outputs", []))]


def _hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"report_hash", "signature"}
    }


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY_QUANT))


def _normalise_code(code: str) -> str:
    lines = [line.rstrip() for line in code.replace("\r\n", "\n").split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def _code_lines(code: str) -> list[str]:
    return [line.strip() for line in _normalise_code(code).split("\n") if line.strip()]


def _code_tokens(code: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(_normalise_code(code))]


def _identifiers(code: str) -> list[str]:
    return [
        token.lower()
        for token in IDENTIFIER_RE.findall(_normalise_code(code))
        if token.lower() not in CODE_KEYWORDS and len(token) > 1
    ]


def _line_hash_root(lines: list[str]) -> str:
    return hash_payload([stable_hash(line) for line in lines])


def _normalise_license(value: str) -> str:
    text = value.strip().lower().replace("_", "-").replace(" ", "-")
    text = text.replace("-license", "")
    if text in {"apache", "apache2", "apache-2"}:
        return "apache-2.0"
    if text in {"bsd", "bsd-3"}:
        return "bsd-3-clause"
    if text in {"gpl3", "gplv3", "gpl-3.0-only", "gpl-3.0-or-later"}:
        return "gpl-3.0"
    if text in {"gpl2", "gplv2", "gpl-2.0-only", "gpl-2.0-or-later"}:
        return "gpl-2.0"
    if text in {"agpl3", "agplv3", "agpl-3.0-only", "agpl-3.0-or-later"}:
        return "agpl-3.0"
    if text in {"lgpl3", "lgplv3", "lgpl-3.0-only", "lgpl-3.0-or-later"}:
        return "lgpl-3.0"
    if text in {"lgpl2.1", "lgpl-2.1-only", "lgpl-2.1-or-later"}:
        return "lgpl-2.1"
    if text in {"closed", "commercial", "private"}:
        return "proprietary"
    return text


def _license_compatibility(
    source_license: str,
    intended_license: str,
    distribution: str,
) -> dict[str, Any]:
    source = _normalise_license(source_license)
    intended = _normalise_license(intended_license)
    distribution_mode = distribution.strip().lower() or "distributed"
    if source in RESTRICTED_LICENSES:
        return {
            "status": "conflict",
            "compatible": False,
            "notice_required": False,
            "source_disclosure_required": False,
            "share_alike_required": False,
            "reason": "source license is restricted for generated-code reuse",
        }
    if source in NETWORK_COPYLEFT_LICENSES and intended != source:
        return {
            "status": "conflict",
            "compatible": False,
            "notice_required": True,
            "source_disclosure_required": True,
            "share_alike_required": True,
            "reason": "network copyleft source requires AGPL-compatible output terms",
        }
    if source in COPYLEFT_LICENSES and intended not in COPYLEFT_LICENSES:
        if distribution_mode in {"internal", "private-evaluation", "non-distributed"}:
            return {
                "status": "review",
                "compatible": True,
                "notice_required": True,
                "source_disclosure_required": False,
                "share_alike_required": True,
                "reason": "copyleft match is internal-only and must be reviewed before distribution",
            }
        return {
            "status": "conflict",
            "compatible": False,
            "notice_required": True,
            "source_disclosure_required": True,
            "share_alike_required": True,
            "reason": "copyleft source is incompatible with intended output license",
        }
    if source in PERMISSIVE_LICENSES:
        return {
            "status": "compatible",
            "compatible": True,
            "notice_required": source not in {"cc0-1.0", "unlicense"},
            "source_disclosure_required": False,
            "share_alike_required": False,
            "reason": "permissive or royalty-bearing source can be reused with attribution and payout",
        }
    return {
        "status": "review",
        "compatible": True,
        "notice_required": True,
        "source_disclosure_required": False,
        "share_alike_required": False,
        "reason": "unknown license requires human review before high-confidence reuse",
    }


def _input_row(
    item: dict[str, Any],
    index: int,
    default_gross_revenue: Decimal,
) -> dict[str, Any]:
    output_id = str(item.get("output_id") or item.get("input_id") or f"code_output_{index}")
    code = str(item.get("code", item.get("output", "")))
    normalised = _normalise_code(code)
    lines = _code_lines(normalised)
    gross = Decimal(str(item.get("gross_revenue", default_gross_revenue))).quantize(
        MONEY_QUANT
    )
    return {
        "output_id": output_id,
        "language": str(item.get("language", "unknown")),
        "generated_code_hash": stable_hash(normalised),
        "generated_line_count": len(lines),
        "generated_line_hash_root": _line_hash_root(lines),
        "generated_token_fingerprint": hash_payload(sorted(set(_code_tokens(normalised)))),
        "generated_identifier_fingerprint": hash_payload(
            sorted(set(_identifiers(normalised)))
        ),
        "intended_license": _normalise_license(str(item.get("intended_license", "proprietary"))),
        "distribution": str(item.get("distribution", "distributed")),
        "policy_use": str(item.get("policy_use", "generation")),
        "gross_revenue": _money(gross),
    }


def _score_chunk(
    *,
    output_id: str,
    generated_code: str,
    generated_hash: str,
    chunk: Any,
) -> dict[str, Any]:
    source_code = _normalise_code(chunk.text)
    generated = _normalise_code(generated_code)
    source_lines = _code_lines(source_code)
    generated_lines = _code_lines(generated)
    source_line_hashes = {stable_hash(line) for line in source_lines}
    generated_line_hashes = {stable_hash(line) for line in generated_lines}
    exact_line_overlap = (
        len(source_line_hashes & generated_line_hashes) / len(source_line_hashes)
        if source_line_hashes
        else 0.0
    )
    generated_line_coverage = (
        len(source_line_hashes & generated_line_hashes) / len(generated_line_hashes)
        if generated_line_hashes
        else 0.0
    )
    source_tokens = _code_tokens(source_code)
    generated_tokens = _code_tokens(generated)
    longest_length, longest_tokens = longest_common_token_sequence(
        source_tokens,
        generated_tokens,
    )
    ngram_score = ngram_containment(
        source_tokens,
        generated_tokens,
        size=min(5, max(1, len(source_tokens))),
    )
    identifier_overlap = jaccard_similarity(
        set(_identifiers(source_code)),
        set(_identifiers(generated)),
    )
    token_overlap = jaccard_similarity(set(source_tokens), set(generated_tokens))
    exact_snippet_match = bool(source_code and source_code in generated)
    lcs_score = min(1.0, longest_length / 40)
    decision_score = min(
        1.0,
        (
            0.34 * exact_line_overlap
            + 0.16 * generated_line_coverage
            + 0.16 * ngram_score
            + 0.14 * lcs_score
            + 0.10 * identifier_overlap
            + 0.06 * token_overlap
            + 0.04 * float(exact_snippet_match)
        ),
    )
    scores = {
        "exact_line_overlap": round(exact_line_overlap, 8),
        "generated_line_coverage": round(generated_line_coverage, 8),
        "ngram_containment": round(ngram_score, 8),
        "longest_sequence": round(lcs_score, 8),
        "identifier_overlap": round(identifier_overlap, 8),
        "token_overlap": round(token_overlap, 8),
        "exact_snippet_match": exact_snippet_match,
        "decision_score": round(decision_score, 8),
    }
    matched_line_hashes = sorted(source_line_hashes & generated_line_hashes)
    feature_payload = {
        "output_id": output_id,
        "chunk_id": chunk.chunk_id,
        "work_id": chunk.work_id,
        "generated_code_hash": generated_hash,
        "source_content_hash": chunk.content_hash,
        "matched_line_hashes": matched_line_hashes,
        "matched_sequence_hash": stable_hash(" ".join(longest_tokens)) if longest_tokens else "",
        "scores": scores,
    }
    return {
        "output_id": output_id,
        "work_id": chunk.work_id,
        "chunk_id": chunk.chunk_id,
        "creator_id": chunk.creator_id,
        "title": chunk.title,
        "source_uri": chunk.source_uri,
        "content_hash": chunk.content_hash,
        "source_license": _normalise_license(chunk.license),
        "matched_line_count": len(matched_line_hashes),
        "matched_line_hash_root": hash_payload(matched_line_hashes),
        "matched_sequence_hash": feature_payload["matched_sequence_hash"],
        "scores": scores,
        "feature_commitment": hash_payload(feature_payload),
        "rank": 0,
    }


def _allocate(
    pool: Decimal,
    rows: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], Decimal]]:
    if not rows:
        return []
    total = sum(Decimal(str(row["scores"]["decision_score"])) for row in rows)
    if total <= 0:
        total = Decimal(len(rows))
    allocations: list[tuple[dict[str, Any], Decimal]] = []
    remainder = pool
    for row in rows[:-1]:
        share = Decimal(str(row["scores"]["decision_score"])) / total
        payout = (pool * share).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        allocations.append((row, payout))
        remainder -= payout
    allocations.append((rows[-1], remainder.quantize(MONEY_QUANT)))
    return allocations


def _analyse_outputs(
    engine: RoyaltyDrivenLLM,
    inputs: list[dict[str, Any]],
    *,
    default_gross_revenue: Decimal,
    creator_pool_rate: Decimal,
    accept_threshold: float,
    strong_copy_threshold: float,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    Decimal,
]:
    input_rows: list[dict[str, Any]] = []
    match_rows: list[dict[str, Any]] = []
    shares: list[dict[str, Any]] = []
    obligations: list[dict[str, Any]] = []
    escrow_total = Decimal("0")
    payout_totals: defaultdict[tuple[str, str, str], Decimal] = defaultdict(
        lambda: Decimal("0")
    )
    payout_outputs: defaultdict[tuple[str, str, str], list[str]] = defaultdict(list)

    for index, item in enumerate(inputs, start=1):
        input_row = _input_row(item, index, default_gross_revenue)
        input_rows.append(input_row)
        generated_code = str(item.get("code", item.get("output", "")))
        gross = Decimal(input_row["gross_revenue"])
        pool = (gross * creator_pool_rate).quantize(MONEY_QUANT)
        candidates = [
            _score_chunk(
                output_id=input_row["output_id"],
                generated_code=generated_code,
                generated_hash=input_row["generated_code_hash"],
                chunk=chunk,
            )
            for chunk in engine.chunks
        ]
        candidates = [
            row for row in candidates if float(row["scores"]["decision_score"]) > 0
        ]
        candidates.sort(
            key=lambda row: (
                -float(row["scores"]["decision_score"]),
                str(row["work_id"]),
                str(row["chunk_id"]),
            )
        )
        accepted: list[dict[str, Any]] = []
        conflicts: list[dict[str, Any]] = []
        for rank, row in enumerate(candidates, start=1):
            chunk = engine.chunk_by_id[row["chunk_id"]]
            policy_decision = engine.policy_engine.evaluate_chunk(
                chunk,
                input_row["policy_use"],
                jurisdiction=engine.jurisdiction,
                creator_pool_rate=creator_pool_rate,
            )
            license_check = _license_compatibility(
                row["source_license"],
                input_row["intended_license"],
                input_row["distribution"],
            )
            score = float(row["scores"]["decision_score"])
            row = dict(row)
            row["rank"] = rank
            row["policy_allowed"] = policy_decision.allowed
            row["policy_reasons"] = list(policy_decision.reasons)
            row["license_check"] = license_check
            if score >= accept_threshold:
                if policy_decision.allowed and license_check["compatible"]:
                    row["decision"] = (
                        "code_attributed_review"
                        if license_check["status"] == "review"
                        else "code_attributed"
                    )
                    accepted.append(row)
                else:
                    row["decision"] = "license_conflict_review"
                    conflicts.append(row)
            else:
                row["decision"] = "below_threshold"
            match_rows.append(row)
        strong_conflict = any(
            float(row["scores"]["decision_score"]) >= strong_copy_threshold
            for row in conflicts
        )
        if strong_conflict:
            escrow_total += pool
            shares.append(
                {
                    "output_id": input_row["output_id"],
                    "creator_id": "code_license_conflict_escrow",
                    "work_id": "escrow:code_license_conflict",
                    "chunk_id": "escrow:code_license_conflict",
                    "decision": "license_conflict_review",
                    "payout": _money(pool),
                    "contribution_weight": 1.0,
                    "decision_score": max(
                        [row["scores"]["decision_score"] for row in conflicts] or [0.0]
                    ),
                }
            )
            obligations.append(
                {
                    "output_id": input_row["output_id"],
                    "status": "hold_for_license_review",
                    "release_recommendation": "hold",
                    "reason": "strong copied-code signal from incompatible or denied source",
                    "creator_pool": _money(pool),
                    "conflict_count": len(conflicts),
                    "accepted_source_count": len(accepted),
                    "obligation_hash": "",
                }
            )
            continue
        if not accepted:
            escrow_total += pool
            shares.append(
                {
                    "output_id": input_row["output_id"],
                    "creator_id": "code_attribution_escrow",
                    "work_id": "escrow:code_attribution",
                    "chunk_id": "escrow:code_attribution",
                    "decision": "unattributed_code_escrow",
                    "payout": _money(pool),
                    "contribution_weight": 1.0,
                    "decision_score": candidates[0]["scores"]["decision_score"] if candidates else 0.0,
                }
            )
            obligations.append(
                {
                    "output_id": input_row["output_id"],
                    "status": "unattributed_escrow",
                    "release_recommendation": "hold_or_rewrite",
                    "reason": "no registered code source passed attribution threshold",
                    "creator_pool": _money(pool),
                    "conflict_count": len(conflicts),
                    "accepted_source_count": 0,
                    "obligation_hash": "",
                }
            )
            continue
        allocations = _allocate(pool, accepted)
        for row, payout in allocations:
            key = (str(row["creator_id"]), str(row["work_id"]), str(row["chunk_id"]))
            payout_totals[key] += payout
            payout_outputs[key].append(input_row["output_id"])
            shares.append(
                {
                    "output_id": input_row["output_id"],
                    "creator_id": row["creator_id"],
                    "work_id": row["work_id"],
                    "chunk_id": row["chunk_id"],
                    "decision": row["decision"],
                    "payout": _money(payout),
                    "contribution_weight": round(float(payout / pool), 8) if pool else 0.0,
                    "decision_score": row["scores"]["decision_score"],
                }
            )
        obligations.append(
            {
                "output_id": input_row["output_id"],
                "status": "allow_with_attribution",
                "release_recommendation": "allow",
                "reason": "all accepted copied-code matches are policy and license compatible",
                "creator_pool": _money(pool),
                "conflict_count": len(conflicts),
                "accepted_source_count": len(accepted),
                "obligation_hash": "",
            }
        )

    for obligation in obligations:
        obligation["obligation_hash"] = hash_payload(
            {key: value for key, value in obligation.items() if key != "obligation_hash"}
        )
    payout_rows = [
        {
            "creator_id": creator_id,
            "work_id": work_id,
            "chunk_id": chunk_id,
            "output_ids": sorted(payout_outputs[(creator_id, work_id, chunk_id)]),
            "payout": _money(payout),
            "payout_hash": hash_payload(
                {
                    "creator_id": creator_id,
                    "work_id": work_id,
                    "chunk_id": chunk_id,
                    "output_ids": sorted(payout_outputs[(creator_id, work_id, chunk_id)]),
                    "payout": _money(payout),
                }
            ),
        }
        for (creator_id, work_id, chunk_id), payout in sorted(payout_totals.items())
    ]
    return input_rows, match_rows, shares, payout_rows, obligations, escrow_total


def _private_strings(engine: RoyaltyDrivenLLM, inputs: list[dict[str, Any]]) -> list[str]:
    values = [work.content for work in engine.works.values()]
    for item in inputs:
        values.append(str(item.get("code", item.get("output", ""))))
    return [value for value in values if len(value.strip()) >= 16]


def make_code_attribution_report(
    engine: RoyaltyDrivenLLM,
    inputs: list[dict[str, Any]],
    *,
    gross_revenue: Decimal | str | float = Decimal("1.00"),
    creator_pool_rate: Decimal | str | float = DEFAULT_CREATOR_POOL_RATE,
    accept_threshold: float = DEFAULT_ACCEPT_THRESHOLD,
    strong_copy_threshold: float = DEFAULT_STRONG_COPY_THRESHOLD,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a privacy-safe generated-code attribution and license report."""

    default_gross = Decimal(str(gross_revenue)).quantize(MONEY_QUANT)
    rate = Decimal(str(creator_pool_rate))
    input_rows, match_rows, shares, payout_rows, obligations, escrow_total = _analyse_outputs(
        engine,
        inputs,
        default_gross_revenue=default_gross,
        creator_pool_rate=rate,
        accept_threshold=accept_threshold,
        strong_copy_threshold=strong_copy_threshold,
    )
    creator_pool_total = sum(
        Decimal(row["gross_revenue"]) * rate for row in input_rows
    ).quantize(MONEY_QUANT)
    payout_total = sum(
        Decimal(str(share["payout"]))
        for share in shares
        if not str(share["creator_id"]).startswith("code_")
    ).quantize(MONEY_QUANT)
    share_total = sum(Decimal(str(share["payout"])) for share in shares).quantize(
        MONEY_QUANT
    )
    conflict_count = len(
        [share for share in shares if share["decision"] == "license_conflict_review"]
    )
    accepted_count = len(
        [
            share
            for share in shares
            if share["decision"] in {"code_attributed", "code_attributed_review"}
        ]
    )
    report = {
        "report_version": CODE_ATTRIBUTION_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "policy": {
            "profile": CODE_ATTRIBUTION_POLICY_VERSION,
            "accept_threshold": round(float(accept_threshold), 8),
            "strong_copy_threshold": round(float(strong_copy_threshold), 8),
            "creator_pool_rate": str(rate),
            "default_gross_revenue_per_output": _money(default_gross),
            "license_compatibility_profile": "rdllm-spdx-code-compatibility/v1",
            "release_policy": {
                "compatible_matches_may_release_with_attribution": True,
                "strong_incompatible_copy_blocks_release": True,
                "unknown_or_unattributed_code_routes_to_escrow": True,
                "license_review_required_for_unknown_or_copyleft_matches": True,
            },
        },
        "submitted_outputs": input_rows,
        "match_rows": match_rows,
        "royalty_shares": shares,
        "payout_rows": payout_rows,
        "obligations": obligations,
        "commitments": {
            "submitted_output_root": hash_payload(input_rows),
            "match_root": hash_payload(match_rows),
            "royalty_share_root": hash_payload(shares),
            "payout_root": hash_payload(payout_rows),
            "obligation_root": hash_payload(obligations),
            "policy_root": hash_payload(
                [
                    {
                        "chunk_id": chunk.chunk_id,
                        "work_id": chunk.work_id,
                        "content_hash": chunk.content_hash,
                        "license": _normalise_license(chunk.license),
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
            "target_certification_level": "RDLLM-L53",
            "output_count": len(input_rows),
            "candidate_row_count": len(match_rows),
            "accepted_share_count": accepted_count,
            "license_conflict_count": conflict_count,
            "escrow_output_count": len(
                [
                    share
                    for share in shares
                    if str(share["creator_id"]).startswith("code_")
                ]
            ),
            "creator_pool_total": _money(creator_pool_total),
            "payable_total": _money(payout_total),
            "escrow_total": _money(escrow_total),
            "creator_pool_conserved": share_total == creator_pool_total,
            "copied_code_attribution_supported": True,
            "spdx_license_compatibility_checked": True,
        },
        "privacy": {
            "generated_code_disclosed": False,
            "source_code_disclosed": False,
            "matched_code_disclosed": False,
            "line_hashes_disclosed_as_roots": True,
            "identifier_sets_disclosed_as_hashes": True,
            "report_uses_hashes_scores_source_ids_and_license_status": True,
        },
        "schemas": {
            "code_attribution_report": CODE_ATTRIBUTION_SCHEMA,
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


def validate_code_attribution_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "policy",
        "submitted_outputs",
        "match_rows",
        "royalty_shares",
        "payout_rows",
        "obligations",
        "commitments",
        "summary",
        "privacy",
        "schemas",
        "report_hash",
        "signature",
    )
    for key in required:
        if key not in report:
            errors.append(f"missing code attribution field: {key}")
    if errors:
        return errors
    if report.get("report_version") != CODE_ATTRIBUTION_VERSION:
        errors.append("code attribution report version is unsupported")
    if report.get("policy", {}).get("profile") != CODE_ATTRIBUTION_POLICY_VERSION:
        errors.append("code attribution policy profile is unsupported")
    for row in report.get("submitted_outputs", []):
        for key in (
            "output_id",
            "language",
            "generated_code_hash",
            "generated_line_hash_root",
            "intended_license",
            "distribution",
            "gross_revenue",
        ):
            if key not in row:
                errors.append(f"missing code output row field: {key}")
    for row in report.get("match_rows", []):
        for key in (
            "output_id",
            "work_id",
            "chunk_id",
            "creator_id",
            "content_hash",
            "source_license",
            "scores",
            "feature_commitment",
            "license_check",
            "policy_allowed",
            "decision",
        ):
            if key not in row:
                errors.append(f"missing code match row field: {key}")
    return errors


def verify_code_attribution_report(
    report: dict[str, Any],
    engine: RoyaltyDrivenLLM,
    inputs: list[dict[str, Any]],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify a generated-code attribution report."""

    errors = validate_code_attribution_report_shape(report)
    if errors:
        return errors
    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("code attribution report hash is not reproducible")
    expected = make_code_attribution_report(
        engine,
        inputs,
        gross_revenue=report.get("policy", {}).get(
            "default_gross_revenue_per_output", "1.00"
        ),
        creator_pool_rate=report.get("policy", {}).get(
            "creator_pool_rate", str(DEFAULT_CREATOR_POOL_RATE)
        ),
        accept_threshold=float(
            report.get("policy", {}).get("accept_threshold", DEFAULT_ACCEPT_THRESHOLD)
        ),
        strong_copy_threshold=float(
            report.get("policy", {}).get(
                "strong_copy_threshold", DEFAULT_STRONG_COPY_THRESHOLD
            )
        ),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "policy",
        "submitted_outputs",
        "match_rows",
        "royalty_shares",
        "payout_rows",
        "obligations",
        "commitments",
        "summary",
        "privacy",
        "schemas",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"code attribution {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("code attribution report hash does not match replay")
    if report.get("summary", {}).get("creator_pool_conserved") is not True:
        errors.append("code attribution creator pool is not conserved")
    rendered = canonical_json(report)
    for value in _private_strings(engine, inputs):
        if value in rendered:
            errors.append("code attribution report leaks private code text")
            break
    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("code attribution report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("code attribution report signature is invalid")
    return errors
