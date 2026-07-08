"""Pinpoint provenance reports for internal-memory and candidate-corpus attribution."""

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

PINPOINT_PROVENANCE_VERSION = "rdllm-pinpoint-provenance-report/v1"
PINPOINT_PROVENANCE_SCHEMA = "docs/schemas/pinpoint_provenance_report.schema.json"
PINPOINT_POLICY_VERSION = "rdllm-pinpoint-provenance-policy/v1"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L68"
DEFAULT_CREATOR_POOL_RATE = Decimal("0.55")
DEFAULT_ACCEPT_THRESHOLD = 0.34
DEFAULT_MIN_MARGIN = 0.04
DEFAULT_MIN_CRITICAL_RECALL = 0.80
MONEY_QUANT = Decimal("0.000001")

ANTI_DOCUMENT_ROLES = {
    "anti_document",
    "hard_anti_document",
    "forbidden_decoy",
    "topical_decoy",
}


def load_pinpoint_provenance_input(path: str | Path) -> dict[str, Any]:
    """Load private pinpoint-provenance inputs for report replay."""

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


def _event_input(provenance_input: dict[str, Any]) -> dict[str, Any]:
    event = provenance_input.get("event", {})
    prompt = str(event.get("prompt_text", ""))
    response = str(event.get("response_text", event.get("output_text", "")))
    return {
        "event_id": str(event.get("event_id", "")),
        "event_hash": str(event.get("event_hash", "")),
        "prompt_hash": str(event.get("prompt_hash") or stable_hash(prompt)),
        "response_hash": str(event.get("response_hash") or stable_hash(response)),
        "model_id": str(event.get("model_id", "")),
        "model_version": str(event.get("model_version", "")),
    }


def _document_hash(document: dict[str, Any]) -> str:
    return str(document.get("content_hash") or stable_hash(str(document.get("content", ""))))


def _document_id(document: dict[str, Any], index: int) -> str:
    return str(
        document.get("document_id")
        or document.get("chunk_id")
        or document.get("work_id")
        or f"candidate_document_{index}"
    )


def _document_role(document: dict[str, Any]) -> str:
    role = str(document.get("document_role", document.get("role", "candidate")))
    return role or "candidate"


def _claim_id(claim: dict[str, Any], index: int) -> str:
    return str(claim.get("claim_id") or f"claim_{index}")


def _claim_texts(provenance_input: dict[str, Any]) -> list[dict[str, Any]]:
    claims = provenance_input.get("claims", [])
    if claims:
        return [dict(claim) for claim in claims]
    response = str(
        provenance_input.get("event", {}).get(
            "response_text",
            provenance_input.get("event", {}).get("output_text", ""),
        )
    )
    return [
        {
            "claim_id": "claim_1",
            "claim_text": response,
            "required_evidence_phrases": [],
        }
    ]


def _phrase_hashes(phrases: list[str]) -> list[str]:
    return [stable_hash(phrase.lower().strip()) for phrase in phrases if phrase.strip()]


def _input_claim_row(claim: dict[str, Any], index: int) -> dict[str, Any]:
    claim_text = str(claim.get("claim_text", ""))
    phrases = [
        str(item)
        for item in claim.get("required_evidence_phrases", [])
        if str(item).strip()
    ]
    return {
        "claim_id": _claim_id(claim, index),
        "claim_hash": str(claim.get("claim_hash") or stable_hash(claim_text)),
        "required_evidence_phrase_hashes": _phrase_hashes(phrases),
        "expected_work_ids": sorted(str(item) for item in claim.get("expected_work_ids", [])),
        "forbidden_work_ids": sorted(str(item) for item in claim.get("forbidden_work_ids", [])),
    }


def _idf_weights(documents: list[dict[str, Any]], claims: list[dict[str, Any]]) -> dict[str, float]:
    counts: defaultdict[str, int] = defaultdict(int)
    for item in documents:
        counts.update({token: 1 for token in set(tokenize(str(item.get("content", ""))))})
    for claim in claims:
        counts.update({token: 1 for token in set(tokenize(str(claim.get("claim_text", ""))))})
    total = max(1, len(documents) + len(claims))
    return {token: 1.0 + total / (1 + count) for token, count in counts.items()}


def _weighted_recall(
    left_tokens: list[str],
    right_tokens: list[str],
    idf: dict[str, float],
) -> float:
    left = set(left_tokens)
    right = set(right_tokens)
    if not left:
        return 0.0
    numerator = sum(idf.get(token, 1.0) for token in left & right)
    denominator = sum(idf.get(token, 1.0) for token in left)
    if denominator <= 0:
        return 0.0
    return _clamp(numerator / denominator)


def _phrase_recall(phrases: list[str], document_text: str) -> float:
    if not phrases:
        return 1.0
    lowered = document_text.lower()
    found = sum(1 for phrase in phrases if phrase.lower().strip() in lowered)
    return round(found / len(phrases), 8)


def _critical_token_recall(claim_tokens: list[str], document_tokens: list[str]) -> float:
    critical = [token for token in claim_tokens if len(token) >= 5]
    if not critical:
        critical = claim_tokens
    if not critical:
        return 0.0
    document_set = set(document_tokens)
    return round(len([token for token in critical if token in document_set]) / len(critical), 8)


def _score_document_for_claim(
    *,
    claim: dict[str, Any],
    claim_row: dict[str, Any],
    document: dict[str, Any],
    document_index: int,
    response_tokens: list[str],
    idf: dict[str, float],
) -> dict[str, Any]:
    claim_text = str(claim.get("claim_text", ""))
    document_text = str(document.get("content", ""))
    claim_tokens = tokenize(claim_text)
    document_tokens = tokenize(document_text)
    phrases = [
        str(item)
        for item in claim.get("required_evidence_phrases", [])
        if str(item).strip()
    ]
    phrase_score = _phrase_recall(phrases, document_text)
    critical_score = _critical_token_recall(claim_tokens, document_tokens)
    claim_coverage = _weighted_recall(claim_tokens, document_tokens, idf)
    response_coverage = _weighted_recall(response_tokens, document_tokens, idf)
    topical_overlap = jaccard_similarity(claim_tokens + response_tokens, document_tokens)
    role = _document_role(document)
    work_id = str(document.get("work_id", ""))
    forbidden = work_id in set(claim_row["forbidden_work_ids"]) or role in ANTI_DOCUMENT_ROLES
    expected = work_id in set(claim_row["expected_work_ids"])
    anti_penalty = 0.25 if forbidden else 0.0
    decision_score = _clamp(
        0.34 * phrase_score
        + 0.22 * critical_score
        + 0.18 * claim_coverage
        + 0.14 * response_coverage
        + 0.12 * topical_overlap
        - anti_penalty
    )
    feature_payload = {
        "claim_id": claim_row["claim_id"],
        "claim_hash": claim_row["claim_hash"],
        "document_id": _document_id(document, document_index),
        "work_id": work_id,
        "content_hash": _document_hash(document),
        "required_evidence_phrase_hashes": claim_row["required_evidence_phrase_hashes"],
        "scores": {
            "required_phrase_recall": round(phrase_score, 8),
            "critical_token_recall": round(critical_score, 8),
            "claim_weighted_recall": round(claim_coverage, 8),
            "response_weighted_recall": round(response_coverage, 8),
            "topical_overlap": round(topical_overlap, 8),
            "anti_document_penalty": round(anti_penalty, 8),
            "decision_score": round(decision_score, 8),
        },
    }
    return {
        "claim_id": claim_row["claim_id"],
        "claim_hash": claim_row["claim_hash"],
        "document_id": _document_id(document, document_index),
        "work_id": work_id,
        "chunk_id": str(document.get("chunk_id", "")),
        "creator_id": str(document.get("creator_id", "")),
        "creator_name": str(document.get("creator_name", "")),
        "title": str(document.get("title", "")),
        "source_uri": str(document.get("source_uri", "")),
        "content_hash": _document_hash(document),
        "document_role": role,
        "candidate_relation": "forbidden_anti_document"
        if forbidden
        else ("expected_support" if expected else "unlabeled_candidate"),
        "scores": feature_payload["scores"],
        "feature_commitment": hash_payload(feature_payload),
        "rank": 0,
        "support_margin": 0.0,
        "decision": "candidate",
    }


def _rank_rows(
    provenance_input: dict[str, Any],
    *,
    accept_threshold: float,
    min_margin: float,
    min_critical_recall: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    documents = [dict(item) for item in provenance_input.get("candidate_documents", [])]
    claims = _claim_texts(provenance_input)
    claim_rows = [_input_claim_row(claim, index) for index, claim in enumerate(claims, start=1)]
    response = str(
        provenance_input.get("event", {}).get(
            "response_text",
            provenance_input.get("event", {}).get("output_text", ""),
        )
    )
    response_tokens = tokenize(response)
    idf = _idf_weights(documents, claims)
    all_rows: list[dict[str, Any]] = []
    verified_claims: list[dict[str, Any]] = []
    for claim_index, claim in enumerate(claims, start=1):
        claim_row = claim_rows[claim_index - 1]
        rows = [
            _score_document_for_claim(
                claim=claim,
                claim_row=claim_row,
                document=document,
                document_index=document_index,
                response_tokens=response_tokens,
                idf=idf,
            )
            for document_index, document in enumerate(documents, start=1)
        ]
        rows.sort(
            key=lambda row: (
                -float(row["scores"]["decision_score"]),
                row["candidate_relation"] == "forbidden_anti_document",
                str(row["work_id"]),
                str(row["document_id"]),
            )
        )
        top = rows[0] if rows else None
        second_score = float(rows[1]["scores"]["decision_score"]) if len(rows) > 1 else 0.0
        top_score = float(top["scores"]["decision_score"]) if top else 0.0
        support_margin = round(top_score - second_score, 8) if top else 0.0
        accepted = bool(
            top
            and top["candidate_relation"] != "forbidden_anti_document"
            and top_score >= accept_threshold
            and support_margin >= min_margin
            and float(top["scores"]["required_phrase_recall"]) >= min_critical_recall
        )
        for rank, row in enumerate(rows, start=1):
            row["rank"] = rank
            row["support_margin"] = support_margin if rank == 1 else 0.0
            if rank == 1 and accepted:
                row["decision"] = "accepted"
            elif row["candidate_relation"] == "forbidden_anti_document":
                row["decision"] = "rejected_anti_document"
            elif rank == 1:
                row["decision"] = "pinpoint_escrow"
            else:
                row["decision"] = "candidate"
            row["row_hash"] = hash_payload(row)
        all_rows.extend(rows)
        verified_claims.append(
            {
                "claim_id": claim_row["claim_id"],
                "claim_hash": claim_row["claim_hash"],
                "top_document_id": str(top.get("document_id", "")) if top else "",
                "top_work_id": str(top.get("work_id", "")) if top else "",
                "top_content_hash": str(top.get("content_hash", "")) if top else "",
                "top_decision_score": round(top_score, 8),
                "support_margin": support_margin,
                "required_evidence_phrase_hashes": claim_row[
                    "required_evidence_phrase_hashes"
                ],
                "expected_work_ids": claim_row["expected_work_ids"],
                "forbidden_work_ids": claim_row["forbidden_work_ids"],
                "decision": "accepted" if accepted else "pinpoint_escrow",
                "accepted_source_label": f"S{len([item for item in verified_claims if item.get('decision') == 'accepted']) + 1}"
                if accepted
                else "",
                "anti_document_rejected": (
                    not top
                    or top.get("candidate_relation") != "forbidden_anti_document"
                ),
            }
        )
    return claim_rows, all_rows, verified_claims


def _source_footers(
    candidate_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    accepted = [row for row in candidate_rows if row["decision"] == "accepted"]
    footers: list[dict[str, Any]] = []
    for index, row in enumerate(accepted, start=1):
        label = f"S{index}"
        footer_text = (
            f"Sources: [{label}] {row['title']} ({row['source_uri']}) "
            f"work={row['work_id']} hash={str(row['content_hash'])[:18]} "
            f"score={row['scores']['decision_score']}"
        )
        footers.append(
            {
                "claim_id": row["claim_id"],
                "claim_hash": row["claim_hash"],
                "label": label,
                "work_id": row["work_id"],
                "chunk_id": row["chunk_id"],
                "creator_id": row["creator_id"],
                "source_uri": row["source_uri"],
                "content_hash": row["content_hash"],
                "decision_score": row["scores"]["decision_score"],
                "support_margin": row["support_margin"],
                "footer_text_hash": stable_hash(footer_text),
                "footer_text_preview": footer_text,
            }
        )
    accepted_claims = {row["claim_id"] for row in accepted}
    for claim in claim_rows:
        if claim["claim_id"] in accepted_claims:
            continue
        footer_text = (
            "Sources: no registered candidate document passed pinpoint provenance; "
            "creator pool routed to pinpoint provenance escrow."
        )
        footers.append(
            {
                "claim_id": claim["claim_id"],
                "claim_hash": claim["claim_hash"],
                "label": "",
                "work_id": "escrow:pinpoint_provenance",
                "chunk_id": "escrow:pinpoint_provenance",
                "creator_id": "pinpoint_provenance_escrow",
                "source_uri": "",
                "content_hash": "",
                "decision_score": 0.0,
                "support_margin": 0.0,
                "footer_text_hash": stable_hash(footer_text),
                "footer_text_preview": footer_text,
            }
        )
    return footers


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
    shares_by_key: defaultdict[tuple[str, str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    share_claims: defaultdict[tuple[str, str, str], list[str]] = defaultdict(list)
    escrow_total = Decimal("0")
    accepted_by_claim = {
        str(row["claim_id"]): row
        for row in candidate_rows
        if row.get("decision") == "accepted"
    }
    for claim in claim_rows:
        row = accepted_by_claim.get(str(claim["claim_id"]))
        if row:
            key = (str(row["creator_id"]), str(row["work_id"]), str(row["chunk_id"]))
            shares_by_key[key] += per_claim
            share_claims[key].append(str(claim["claim_id"]))
        else:
            key = (
                "pinpoint_provenance_escrow",
                "escrow:pinpoint_provenance",
                "escrow:pinpoint_provenance",
            )
            shares_by_key[key] += per_claim
            share_claims[key].append(str(claim["claim_id"]))
            escrow_total += per_claim
    shares: list[dict[str, Any]] = []
    paid_so_far = Decimal("0")
    items = sorted(shares_by_key.items(), key=lambda item: item[0])
    for index, ((creator_id, work_id, chunk_id), payout) in enumerate(items):
        if index == len(items) - 1:
            payout = creator_pool - paid_so_far
        else:
            payout = payout.quantize(MONEY_QUANT)
        paid_so_far += payout
        shares.append(
            {
                "creator_id": creator_id,
                "work_id": work_id,
                "chunk_id": chunk_id,
                "claim_ids": sorted(share_claims[(creator_id, work_id, chunk_id)]),
                "decision": "pinpoint_escrow"
                if creator_id == "pinpoint_provenance_escrow"
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
    verified_claims: list[dict[str, Any]],
    source_footers: list[dict[str, Any]],
    royalty_shares: list[dict[str, Any]],
    creator_pool: Decimal,
    accept_threshold: float,
    min_margin: float,
    min_critical_recall: float,
) -> dict[str, bool]:
    accepted_rows = [row for row in candidate_rows if row.get("decision") == "accepted"]
    accepted_claims = {row["claim_id"] for row in accepted_rows}
    footer_claims = {
        footer["claim_id"]
        for footer in source_footers
        if footer.get("work_id") != "escrow:pinpoint_provenance"
    }
    forbidden_accepted = [
        row
        for row in accepted_rows
        if row.get("candidate_relation") == "forbidden_anti_document"
        or row.get("document_role") in ANTI_DOCUMENT_ROLES
    ]
    payout_total = sum(
        (Decimal(str(share["payout"])) for share in royalty_shares),
        Decimal("0"),
    )
    row_json = canonical_json(candidate_rows)
    return {
        "candidate_rows_rank_every_claim": all(
            any(row.get("claim_id") == claim["claim_id"] for row in candidate_rows)
            for claim in claim_rows
        ),
        "accepted_claims_have_visible_source_footer": accepted_claims.issubset(
            footer_claims
        ),
        "anti_documents_never_accepted": not forbidden_accepted,
        "accepted_sources_meet_threshold_and_margin": all(
            row.get("decision") != "accepted"
            or (
                float(row["scores"]["decision_score"]) >= accept_threshold
                and float(row["scores"]["required_phrase_recall"]) >= min_critical_recall
                and float(row["support_margin"]) >= min_margin
            )
            for row in candidate_rows
        ),
        "unattributed_claims_route_to_escrow": all(
            claim["decision"] == "accepted"
            or any(
                share["decision"] == "pinpoint_escrow"
                and claim["claim_id"] in share.get("claim_ids", [])
                for share in royalty_shares
            )
            for claim in verified_claims
        ),
        "creator_pool_conserved": payout_total == creator_pool,
        "public_rows_do_not_embed_private_text": (
            row_json.find('"content":') == -1
            and row_json.find('"claim_text":') == -1
            and row_json.find('"response_text":') == -1
            and row_json.find('"prompt_text":') == -1
        ),
    }


def make_pinpoint_provenance_report(
    provenance_input: dict[str, Any],
    *,
    gross_revenue: Decimal | str | float = Decimal("1.00"),
    creator_pool_rate: Decimal | str | float = DEFAULT_CREATOR_POOL_RATE,
    accept_threshold: float = DEFAULT_ACCEPT_THRESHOLD,
    min_margin: float = DEFAULT_MIN_MARGIN,
    min_critical_recall: float = DEFAULT_MIN_CRITICAL_RECALL,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed pinpoint provenance report for a generated response."""

    gross = Decimal(str(gross_revenue)).quantize(MONEY_QUANT)
    rate = Decimal(str(creator_pool_rate))
    creator_pool = (gross * rate).quantize(MONEY_QUANT)
    claim_rows, candidate_rows, verified_claims = _rank_rows(
        provenance_input,
        accept_threshold=accept_threshold,
        min_margin=min_margin,
        min_critical_recall=min_critical_recall,
    )
    footers = _source_footers(candidate_rows, claim_rows)
    shares, escrow_total = _allocate(
        claim_rows,
        candidate_rows,
        creator_pool=creator_pool,
    )
    checks = _checks(
        claim_rows=claim_rows,
        candidate_rows=candidate_rows,
        verified_claims=verified_claims,
        source_footers=footers,
        royalty_shares=shares,
        creator_pool=creator_pool,
        accept_threshold=accept_threshold,
        min_margin=min_margin,
        min_critical_recall=min_critical_recall,
    )
    accepted_rows = [row for row in candidate_rows if row["decision"] == "accepted"]
    report = {
        "report_version": PINPOINT_PROVENANCE_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "event": _event_input(provenance_input),
        "policy": {
            "profile": PINPOINT_POLICY_VERSION,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "creator_pool_rate": str(rate),
            "accept_threshold": round(float(accept_threshold), 8),
            "min_support_margin": round(float(min_margin), 8),
            "min_critical_fact_recall": round(float(min_critical_recall), 8),
            "accepted_decision": "accepted",
            "ambiguous_decision": "pinpoint_escrow",
            "anti_document_decision": "rejected_anti_document",
            "topical_similarity_alone_is_insufficient": True,
        },
        "economics": {
            "gross_revenue": _money(gross),
            "creator_pool": _money(creator_pool),
            "payout_total": _money(
                sum((Decimal(share["payout"]) for share in shares), Decimal("0"))
            ),
            "escrow_total": _money(escrow_total),
        },
        "claim_rows": verified_claims,
        "candidate_rows": candidate_rows,
        "source_footers": footers,
        "royalty_shares": shares,
        "commitments": {
            "pinpoint_input_root": hash_payload(
                {
                    "event": _event_input(provenance_input),
                    "claims": claim_rows,
                    "candidate_documents": [
                        {
                            "document_id": _document_id(document, index),
                            "work_id": str(document.get("work_id", "")),
                            "chunk_id": str(document.get("chunk_id", "")),
                            "creator_id": str(document.get("creator_id", "")),
                            "source_uri": str(document.get("source_uri", "")),
                            "content_hash": _document_hash(document),
                            "document_role": _document_role(document),
                        }
                        for index, document in enumerate(
                            provenance_input.get("candidate_documents", []),
                            start=1,
                        )
                    ],
                }
            ),
            "claim_root": hash_payload(verified_claims),
            "candidate_row_root": hash_payload([row["row_hash"] for row in candidate_rows]),
            "source_footer_root": hash_payload(footers),
            "share_root": hash_payload(shares),
        },
        "checks": checks,
        "schemas": {
            "pinpoint_provenance_report": PINPOINT_PROVENANCE_SCHEMA,
        },
        "summary": {
            "status": "ready" if all(checks.values()) else "failed",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "claim_count": len(claim_rows),
            "candidate_document_count": len(provenance_input.get("candidate_documents", [])),
            "candidate_row_count": len(candidate_rows),
            "accepted_claim_count": len({row["claim_id"] for row in accepted_rows}),
            "escrow_claim_count": len(claim_rows)
            - len({row["claim_id"] for row in accepted_rows}),
            "anti_document_rejected_count": len(
                [
                    row
                    for row in candidate_rows
                    if row["decision"] == "rejected_anti_document"
                ]
            ),
            "source_footer_count": len(footers),
            "creator_pool_conserved": checks["creator_pool_conserved"],
            "pinpoint_provenance": True,
            "offline_verification_supported": True,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "response_text_disclosed": False,
            "claim_text_disclosed": False,
            "source_text_disclosed": False,
            "critical_evidence_phrases_disclosed": False,
            "public_report_uses_hashes_scores_and_source_ids": True,
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


def validate_pinpoint_provenance_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "event",
        "policy",
        "economics",
        "claim_rows",
        "candidate_rows",
        "source_footers",
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
            errors.append(f"missing pinpoint provenance field: {key}")
    if errors:
        return errors
    if report.get("report_version") != PINPOINT_PROVENANCE_VERSION:
        errors.append("pinpoint provenance report version is unsupported")
    if report.get("policy", {}).get("profile") != PINPOINT_POLICY_VERSION:
        errors.append("pinpoint provenance policy profile is unsupported")
    if report.get("summary", {}).get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("pinpoint provenance target certification level is unsupported")
    if "pinpoint_provenance_report" not in report.get("schemas", {}):
        errors.append("missing pinpoint provenance schema")
    for row in report.get("candidate_rows", []):
        for key in (
            "claim_id",
            "claim_hash",
            "document_id",
            "work_id",
            "chunk_id",
            "creator_id",
            "content_hash",
            "document_role",
            "candidate_relation",
            "scores",
            "feature_commitment",
            "rank",
            "support_margin",
            "decision",
            "row_hash",
        ):
            if key not in row:
                errors.append(f"missing pinpoint candidate row field: {key}")
    for footer in report.get("source_footers", []):
        for key in (
            "claim_id",
            "claim_hash",
            "label",
            "work_id",
            "chunk_id",
            "creator_id",
            "content_hash",
            "footer_text_hash",
            "footer_text_preview",
        ):
            if key not in footer:
                errors.append(f"missing pinpoint source footer field: {key}")
    return errors


def _private_strings(provenance_input: dict[str, Any]) -> list[str]:
    values: list[str] = []
    event = provenance_input.get("event", {})
    values.append(str(event.get("prompt_text", "")))
    values.append(str(event.get("response_text", event.get("output_text", ""))))
    for claim in provenance_input.get("claims", []):
        values.append(str(claim.get("claim_text", "")))
        values.extend(str(item) for item in claim.get("required_evidence_phrases", []))
    for document in provenance_input.get("candidate_documents", []):
        values.append(str(document.get("content", "")))
    return [value for value in values if len(value.strip()) >= 16]


def verify_pinpoint_provenance_report(
    report: dict[str, Any],
    provenance_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify a pinpoint provenance report against private inputs."""

    errors = validate_pinpoint_provenance_report_shape(report)
    if errors:
        return errors
    if hash_payload(_hashable_report(report)) != report.get("report_hash"):
        errors.append("pinpoint provenance report hash is not reproducible")

    expected = make_pinpoint_provenance_report(
        provenance_input,
        gross_revenue=report.get("economics", {}).get("gross_revenue", "1.00"),
        creator_pool_rate=report.get("policy", {}).get(
            "creator_pool_rate",
            str(DEFAULT_CREATOR_POOL_RATE),
        ),
        accept_threshold=float(
            report.get("policy", {}).get("accept_threshold", DEFAULT_ACCEPT_THRESHOLD)
        ),
        min_margin=float(
            report.get("policy", {}).get("min_support_margin", DEFAULT_MIN_MARGIN)
        ),
        min_critical_recall=float(
            report.get("policy", {}).get(
                "min_critical_fact_recall",
                DEFAULT_MIN_CRITICAL_RECALL,
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
        "claim_rows",
        "candidate_rows",
        "source_footers",
        "royalty_shares",
        "commitments",
        "checks",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"pinpoint provenance {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("pinpoint provenance report hash does not match replay")
    if report.get("summary", {}).get("status") != "ready":
        errors.append("pinpoint provenance report status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"pinpoint provenance check failed: {check}")

    rendered = canonical_json(report)
    for value in _private_strings(provenance_input):
        if value and value in rendered:
            errors.append("pinpoint provenance report leaks private input text")
            break

    if signing_secret:
        signature = report.get("signature", {})
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("pinpoint provenance report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("pinpoint provenance report signature is invalid")
    return errors
