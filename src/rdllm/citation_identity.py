"""Citation identity reports for detecting fabricated or swapped citations."""

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

CITATION_IDENTITY_VERSION = "rdllm-citation-identity-report/v1"
CITATION_IDENTITY_SCHEMA = "docs/schemas/citation_identity_report.schema.json"
CITATION_IDENTITY_POLICY_VERSION = "rdllm-citation-identity-policy/v1"
TARGET_CERTIFICATION_LEVEL = "RDLLM-L69"
DEFAULT_CREATOR_POOL_RATE = Decimal("0.55")
DEFAULT_ACCEPT_THRESHOLD = 0.72
DEFAULT_MIN_TITLE_SIMILARITY = 0.72
DEFAULT_MIN_AUTHOR_OVERLAP = 0.50
DEFAULT_MIN_CLAIM_SUPPORT = 0.55
MONEY_QUANT = Decimal("0.000001")

IDENTIFIER_FIELDS = ("doi", "arxiv_id", "isbn", "pmid", "url", "source_uri")
ACCEPTED_STATUSES = {"verified", "minor_metadata_drift"}


def load_citation_identity_input(path: str | Path) -> dict[str, Any]:
    """Load private citation-identity inputs for report replay."""

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


def _normalize_identifier(kind: str, value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    if kind == "doi":
        lowered = lowered.removeprefix("https://doi.org/")
        lowered = lowered.removeprefix("http://doi.org/")
        lowered = lowered.removeprefix("doi:")
        return lowered.strip()
    if kind == "arxiv_id":
        lowered = lowered.removeprefix("arxiv:")
        lowered = lowered.removeprefix("https://arxiv.org/abs/")
        lowered = lowered.removeprefix("http://arxiv.org/abs/")
        return lowered.split("v", 1)[0].strip()
    if kind in {"url", "source_uri"}:
        return lowered.rstrip("/")
    return lowered


def _identifier_pairs(item: dict[str, Any]) -> list[tuple[str, str]]:
    identifiers = item.get("identifiers", {})
    pairs: list[tuple[str, str]] = []
    for kind in IDENTIFIER_FIELDS:
        value = item.get(kind) or identifiers.get(kind)
        normalized = _normalize_identifier(kind, value)
        if normalized:
            pairs.append((kind, normalized))
    return pairs


def _primary_identifier(item: dict[str, Any]) -> tuple[str, str]:
    pairs = _identifier_pairs(item)
    if not pairs:
        return "", ""
    priority = {kind: index for index, kind in enumerate(IDENTIFIER_FIELDS)}
    pairs.sort(key=lambda pair: priority.get(pair[0], len(priority)))
    return pairs[0]


def _title(item: dict[str, Any]) -> str:
    return str(
        item.get("title")
        or item.get("declared_title")
        or item.get("canonical_title")
        or ""
    )


def _authors(item: dict[str, Any]) -> list[str]:
    value = item.get("authors") or item.get("declared_authors") or item.get(
        "canonical_authors"
    )
    if isinstance(value, list):
        return [str(author).strip() for author in value if str(author).strip()]
    if isinstance(value, str) and value.strip():
        return [part.strip() for part in value.split(";") if part.strip()]
    return []


def _year(item: dict[str, Any]) -> str:
    return str(item.get("year") or item.get("published_year") or "").strip()


def _authority_id(authority: dict[str, Any], index: int) -> str:
    return str(authority.get("authority_id") or authority.get("record_id") or f"authority_{index}")


def _authority_by_identifier(
    authority_records: list[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for authority in authority_records:
        for kind, value in _identifier_pairs(authority):
            lookup[(kind, value)] = authority
    return lookup


def _best_authority(
    citation: dict[str, Any],
    authority_records: list[dict[str, Any]],
    lookup: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any] | None:
    for key in _identifier_pairs(citation):
        if key in lookup:
            return lookup[key]
    citation_tokens = tokenize(_title(citation))
    if not citation_tokens:
        return None
    candidates = [
        (
            jaccard_similarity(citation_tokens, tokenize(_title(authority))),
            authority,
        )
        for authority in authority_records
    ]
    candidates.sort(key=lambda item: item[0], reverse=True)
    if not candidates or candidates[0][0] < 0.45:
        return None
    return candidates[0][1]


def _author_tokens(authors: list[str]) -> set[str]:
    tokens: set[str] = set()
    for author in authors:
        parts = tokenize(author)
        if parts:
            tokens.add(parts[-1])
    return tokens


def _author_overlap(citation: dict[str, Any], authority: dict[str, Any]) -> float:
    declared = _author_tokens(_authors(citation))
    canonical = _author_tokens(_authors(authority))
    if not declared or not canonical:
        return 0.0
    return len(declared & canonical) / len(declared | canonical)


def _identifier_match_score(citation: dict[str, Any], authority: dict[str, Any]) -> float:
    citation_pairs = set(_identifier_pairs(citation))
    authority_pairs = set(_identifier_pairs(authority))
    if not citation_pairs:
        return 0.0
    return 1.0 if citation_pairs & authority_pairs else 0.0


def _phrase_recall(phrases: list[str], text: str) -> float:
    if not phrases:
        return 1.0
    lowered = text.lower()
    found = sum(1 for phrase in phrases if phrase.lower().strip() in lowered)
    return found / len(phrases)


def _claim_support_score(claim: dict[str, Any], authority: dict[str, Any]) -> float:
    claim_text = str(claim.get("claim_text", ""))
    phrases = [
        str(item)
        for item in claim.get("required_evidence_phrases", [])
        if str(item).strip()
    ]
    support_text = " ".join(
        str(authority.get(field, ""))
        for field in (
            "abstract",
            "summary",
            "source_excerpt",
            "verified_excerpt",
            "content",
        )
    )
    phrase_score = _phrase_recall(phrases, support_text)
    claim_tokens = tokenize(claim_text)
    support_tokens = tokenize(support_text)
    token_score = jaccard_similarity(claim_tokens, support_tokens)
    if phrases:
        return round(max(phrase_score, token_score), 8)
    return round(token_score, 8)


def _claim_id(claim: dict[str, Any], index: int) -> str:
    return str(claim.get("claim_id") or f"claim_{index}")


def _claim_hash(claim: dict[str, Any]) -> str:
    return str(claim.get("claim_hash") or stable_hash(str(claim.get("claim_text", ""))))


def _claims(citation_input: dict[str, Any]) -> list[dict[str, Any]]:
    claims = citation_input.get("claims") or citation_input.get("claim_bindings") or []
    return [dict(claim) for claim in claims]


def _citations_for_claim(
    claim: dict[str, Any],
    citations_by_id: dict[str, dict[str, Any]],
    all_citations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    citation_ids = [
        str(item)
        for item in claim.get("citation_ids", claim.get("citations", []))
        if str(item).strip()
    ]
    if not citation_ids:
        return all_citations
    return [
        citations_by_id[citation_id]
        for citation_id in citation_ids
        if citation_id in citations_by_id
    ]


def _event(citation_input: dict[str, Any]) -> dict[str, Any]:
    event = citation_input.get("event", {})
    response_text = str(event.get("response_text", event.get("output_text", "")))
    prompt_text = str(event.get("prompt_text", ""))
    return {
        "event_id": str(event.get("event_id", "")),
        "event_hash": str(event.get("event_hash", "")),
        "prompt_hash": str(event.get("prompt_hash") or stable_hash(prompt_text)),
        "response_hash": str(event.get("response_hash") or stable_hash(response_text)),
        "model_id": str(event.get("model_id", "")),
        "model_version": str(event.get("model_version", "")),
    }


def _status(
    *,
    authority: dict[str, Any] | None,
    identifier_score: float,
    title_score: float,
    author_score: float,
    year_score: float,
    claim_support_score: float,
    min_title_similarity: float,
    min_author_overlap: float,
    min_claim_support: float,
) -> str:
    if authority is None:
        return "fabricated_citation"
    if identifier_score < 1.0 and title_score < min_title_similarity:
        return "unresolved_metadata"
    if identifier_score >= 1.0 and (
        title_score < 0.45 or author_score < 0.20 or year_score < 1.0
    ):
        return "identifier_metadata_mismatch"
    if claim_support_score < min_claim_support:
        return "claim_not_supported_by_citation"
    if (
        identifier_score >= 1.0
        and title_score >= min_title_similarity
        and author_score >= min_author_overlap
        and year_score >= 1.0
    ):
        return "verified"
    if (
        identifier_score >= 1.0
        and title_score >= 0.60
        and author_score >= 0.35
        and claim_support_score >= min_claim_support
    ):
        return "minor_metadata_drift"
    return "metadata_ambiguous"


def _canonical_identifier(authority: dict[str, Any] | None) -> tuple[str, str]:
    if authority is None:
        return "", ""
    return _primary_identifier(authority)


def _score_claim_citation(
    *,
    claim: dict[str, Any],
    claim_index: int,
    citation: dict[str, Any],
    authority: dict[str, Any] | None,
    authority_index: int,
    accept_threshold: float,
    min_title_similarity: float,
    min_author_overlap: float,
    min_claim_support: float,
) -> dict[str, Any]:
    title_score = (
        jaccard_similarity(tokenize(_title(citation)), tokenize(_title(authority)))
        if authority is not None
        else 0.0
    )
    author_score = _author_overlap(citation, authority or {})
    year_score = 1.0 if authority is not None and _year(citation) == _year(authority) else 0.0
    identifier_score = _identifier_match_score(citation, authority or {})
    support_score = _claim_support_score(claim, authority or {})
    decision_score = round(
        _clamp(
            0.30 * identifier_score
            + 0.22 * title_score
            + 0.18 * author_score
            + 0.10 * year_score
            + 0.20 * support_score
        ),
        8,
    )
    identity_status = _status(
        authority=authority,
        identifier_score=identifier_score,
        title_score=title_score,
        author_score=author_score,
        year_score=year_score,
        claim_support_score=support_score,
        min_title_similarity=min_title_similarity,
        min_author_overlap=min_author_overlap,
        min_claim_support=min_claim_support,
    )
    accepted = identity_status in ACCEPTED_STATUSES and decision_score >= accept_threshold
    declared_kind, declared_identifier = _primary_identifier(citation)
    canonical_kind, canonical_identifier = _canonical_identifier(authority)
    authority_id = _authority_id(authority, authority_index) if authority else ""
    row = {
        "claim_id": _claim_id(claim, claim_index),
        "claim_hash": _claim_hash(claim),
        "citation_id": str(citation.get("citation_id") or citation.get("id") or ""),
        "work_id": str(citation.get("work_id", "")),
        "chunk_id": str(citation.get("chunk_id", "")),
        "creator_id": str(citation.get("creator_id", "")),
        "declared_identifier_type": declared_kind,
        "declared_identifier_hash": stable_hash(f"{declared_kind}:{declared_identifier}")
        if declared_identifier
        else "",
        "resolved_authority_id_hash": stable_hash(authority_id) if authority_id else "",
        "canonical_identifier_type": canonical_kind,
        "canonical_identifier_hash": stable_hash(f"{canonical_kind}:{canonical_identifier}")
        if canonical_identifier
        else "",
        "metadata_scores": {
            "identifier_match": round(identifier_score, 8),
            "title_similarity": round(title_score, 8),
            "author_overlap": round(author_score, 8),
            "year_match": round(year_score, 8),
            "claim_support": round(support_score, 8),
            "decision_score": decision_score,
        },
        "identity_status": identity_status,
        "decision": "accepted" if accepted else "citation_identity_escrow",
        "canonical_footer": _canonical_footer_payload(
            citation=citation,
            authority=authority,
            identity_status=identity_status,
            claim_ids=[_claim_id(claim, claim_index)],
        )
        if accepted
        else {},
    }
    row["row_hash"] = hash_payload(_hashable_row(row, "row_hash"))
    return row


def _canonical_footer_payload(
    *,
    citation: dict[str, Any],
    authority: dict[str, Any] | None,
    identity_status: str,
    claim_ids: list[str],
) -> dict[str, Any]:
    if authority is None:
        return {}
    identifier_kind, identifier = _canonical_identifier(authority)
    title = _title(authority)
    year = _year(authority)
    uri = str(authority.get("source_uri") or authority.get("url") or citation.get("source_uri", ""))
    display_identifier = (
        f"arXiv:{identifier}"
        if identifier_kind == "arxiv_id"
        else f"doi:{identifier}"
        if identifier_kind == "doi"
        else identifier
    )
    display_text = (
        f"{title} ({display_identifier}, {year}); "
        f"identity={identity_status}; claims={len(claim_ids)}; uri={uri}"
    )
    return {
        "title": title,
        "year": year,
        "canonical_identifier_type": identifier_kind,
        "canonical_identifier": identifier,
        "source_uri": uri,
        "display_text": display_text,
    }


def _canonical_footers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    claim_ids: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    for row in rows:
        if row["decision"] != "accepted":
            continue
        key = (row["work_id"], row["canonical_identifier_hash"])
        grouped[key] = row
        claim_ids[key].add(row["claim_id"])

    footers: list[dict[str, Any]] = []
    for index, (key, row) in enumerate(sorted(grouped.items()), start=1):
        payload = dict(row.get("canonical_footer", {}))
        claims = sorted(claim_ids[key])
        payload["display_text"] = payload.get("display_text", "").replace(
            f"claims=1;", f"claims={len(claims)};"
        )
        footer = {
            "label": f"S{index}",
            "work_id": row["work_id"],
            "chunk_id": row["chunk_id"],
            "creator_id": row["creator_id"],
            "citation_id": row["citation_id"],
            "claim_ids": claims,
            "canonical_identifier_type": payload.get("canonical_identifier_type", ""),
            "canonical_identifier_hash": row["canonical_identifier_hash"],
            "canonical_title_hash": stable_hash(payload.get("title", "")),
            "source_uri": payload.get("source_uri", ""),
            "identity_status": row["identity_status"],
            "footer_text": payload.get("display_text", ""),
        }
        footer["footer_row_hash"] = hash_payload(
            _hashable_row(footer, "footer_row_hash")
        )
        footers.append(footer)
    return footers


def _allocate_pool(
    rows: list[dict[str, Any]],
    *,
    creator_pool: Decimal,
) -> tuple[list[dict[str, Any]], Decimal]:
    accepted: list[tuple[str, str, str, Decimal]] = []
    escrow_weight = Decimal("0")
    for row in rows:
        score = Decimal(str(row["metadata_scores"]["decision_score"]))
        if score <= Decimal("0"):
            continue
        if row["decision"] == "accepted":
            accepted.append((row["creator_id"], row["work_id"], row["citation_id"], score))
        else:
            escrow_weight += score

    total_weight = sum((item[3] for item in accepted), Decimal("0")) + escrow_weight
    if total_weight <= Decimal("0"):
        return [
            {
                "creator_id": "citation_identity_escrow",
                "work_id": "escrow:citation_identity",
                "citation_ids": sorted({row["citation_id"] for row in rows}),
                "claim_ids": sorted({row["claim_id"] for row in rows}),
                "decision": "citation_identity_escrow",
                "payout": _money(creator_pool),
                "contribution_weight": 1.0 if creator_pool else 0.0,
            }
        ], creator_pool

    totals: defaultdict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    citation_ids: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    claim_ids: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    paid_so_far = Decimal("0")
    for index, (creator_id, work_id, citation_id, weight) in enumerate(accepted):
        if index == len(accepted) - 1 and escrow_weight == Decimal("0"):
            payout = creator_pool - paid_so_far
        else:
            payout = (creator_pool * weight / total_weight).quantize(MONEY_QUANT)
        paid_so_far += payout
        key = (creator_id, work_id)
        totals[key] += payout
        citation_ids[key].add(citation_id)
        claim_ids[key].update(
            row["claim_id"]
            for row in rows
            if row["creator_id"] == creator_id
            and row["work_id"] == work_id
            and row["citation_id"] == citation_id
            and row["decision"] == "accepted"
        )

    escrow_total = creator_pool - paid_so_far if escrow_weight else Decimal("0")
    shares: list[dict[str, Any]] = []
    for (creator_id, work_id), payout in sorted(totals.items()):
        shares.append(
            {
                "creator_id": creator_id,
                "work_id": work_id,
                "citation_ids": sorted(citation_ids[(creator_id, work_id)]),
                "claim_ids": sorted(claim_ids[(creator_id, work_id)]),
                "decision": "accepted",
                "payout": _money(payout),
                "contribution_weight": round(float(payout / creator_pool), 8)
                if creator_pool
                else 0.0,
            }
        )
    if escrow_total:
        shares.append(
            {
                "creator_id": "citation_identity_escrow",
                "work_id": "escrow:citation_identity",
                "citation_ids": sorted(
                    {
                        row["citation_id"]
                        for row in rows
                        if row["decision"] != "accepted"
                    }
                ),
                "claim_ids": sorted(
                    {
                        row["claim_id"]
                        for row in rows
                        if row["decision"] != "accepted"
                    }
                ),
                "decision": "citation_identity_escrow",
                "payout": _money(escrow_total),
                "contribution_weight": round(float(escrow_total / creator_pool), 8)
                if creator_pool
                else 0.0,
            }
        )
    return shares, escrow_total


def _private_strings(citation_input: dict[str, Any]) -> list[str]:
    values: list[str] = []
    event = citation_input.get("event", {})
    values.extend([str(event.get("prompt_text", "")), str(event.get("response_text", ""))])
    for claim in _claims(citation_input):
        values.append(str(claim.get("claim_text", "")))
    for citation in citation_input.get("citations", []):
        values.extend(
            str(citation.get(field, ""))
            for field in ("quoted_text", "source_excerpt", "content")
        )
    for authority in citation_input.get("authority_records", []):
        values.extend(
            str(authority.get(field, ""))
            for field in ("abstract", "summary", "source_excerpt", "verified_excerpt", "content")
        )
    return [value for value in values if len(value.strip()) >= 16]


def _checks(
    *,
    rows: list[dict[str, Any]],
    footers: list[dict[str, Any]],
    shares: list[dict[str, Any]],
    creator_pool: Decimal,
    rendered_report: str,
    private_strings: list[str],
    min_claim_support: float,
) -> dict[str, bool]:
    accepted_rows = [row for row in rows if row["decision"] == "accepted"]
    rejected_rows = [row for row in rows if row["decision"] != "accepted"]
    footer_keys = {(footer["work_id"], footer["canonical_identifier_hash"]) for footer in footers}
    return {
        "every_citation_row_resolved_or_escrowed": all(
            row["identity_status"] != "fabricated_citation"
            or row["decision"] == "citation_identity_escrow"
            for row in rows
        ),
        "fabricated_citations_blocked": all(
            row["decision"] == "citation_identity_escrow"
            for row in rows
            if row["identity_status"] == "fabricated_citation"
        ),
        "identifier_metadata_mismatches_blocked": all(
            row["decision"] == "citation_identity_escrow"
            for row in rows
            if row["identity_status"] == "identifier_metadata_mismatch"
        ),
        "claim_support_required_for_footer": all(
            float(row["metadata_scores"]["claim_support"]) >= min_claim_support
            for row in accepted_rows
        ),
        "verified_citations_have_canonical_footer": all(
            (row["work_id"], row["canonical_identifier_hash"]) in footer_keys
            for row in accepted_rows
        ),
        "rejected_citations_route_to_escrow": (
            not rejected_rows
            or any(share["decision"] == "citation_identity_escrow" for share in shares)
        ),
        "creator_pool_conserved": (
            sum((Decimal(share["payout"]) for share in shares), Decimal("0"))
            == creator_pool
        ),
        "public_rows_do_not_embed_private_text": not any(
            value in rendered_report for value in private_strings
        ),
    }


def make_citation_identity_report(
    citation_input: dict[str, Any],
    *,
    gross_revenue: Decimal | str | float = Decimal("1.00"),
    creator_pool_rate: Decimal | str | float = DEFAULT_CREATOR_POOL_RATE,
    accept_threshold: float = DEFAULT_ACCEPT_THRESHOLD,
    min_title_similarity: float = DEFAULT_MIN_TITLE_SIMILARITY,
    min_author_overlap: float = DEFAULT_MIN_AUTHOR_OVERLAP,
    min_claim_support: float = DEFAULT_MIN_CLAIM_SUPPORT,
    issuer: str = DEFAULT_ISSUER,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a report that verifies public citation identity before footer use."""

    gross = Decimal(str(gross_revenue)).quantize(MONEY_QUANT)
    rate = Decimal(str(creator_pool_rate))
    creator_pool = (gross * rate).quantize(MONEY_QUANT)
    citations = [dict(item) for item in citation_input.get("citations", [])]
    authority_records = [
        dict(item) for item in citation_input.get("authority_records", [])
    ]
    authority_lookup = _authority_by_identifier(authority_records)
    authority_indices = {
        id(authority): index
        for index, authority in enumerate(authority_records, start=1)
    }
    citations_by_id = {
        str(citation.get("citation_id") or citation.get("id") or ""): citation
        for citation in citations
    }
    rows: list[dict[str, Any]] = []
    for claim_index, claim in enumerate(_claims(citation_input), start=1):
        for citation in _citations_for_claim(claim, citations_by_id, citations):
            authority = _best_authority(citation, authority_records, authority_lookup)
            rows.append(
                _score_claim_citation(
                    claim=claim,
                    claim_index=claim_index,
                    citation=citation,
                    authority=authority,
                    authority_index=authority_indices.get(id(authority), 0)
                    if authority
                    else 0,
                    accept_threshold=accept_threshold,
                    min_title_similarity=min_title_similarity,
                    min_author_overlap=min_author_overlap,
                    min_claim_support=min_claim_support,
                )
            )
    rows.sort(
        key=lambda row: (
            row["decision"] != "accepted",
            str(row["claim_id"]),
            -float(row["metadata_scores"]["decision_score"]),
            str(row["citation_id"]),
        )
    )
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
        row["row_hash"] = hash_payload(_hashable_row(row, "row_hash"))

    footers = _canonical_footers(rows)
    shares, escrow_total = _allocate_pool(rows, creator_pool=creator_pool)
    accepted_rows = [row for row in rows if row["decision"] == "accepted"]
    report = {
        "report_version": CITATION_IDENTITY_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "event": _event(citation_input),
        "policy": {
            "profile": CITATION_IDENTITY_POLICY_VERSION,
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "creator_pool_rate": str(rate),
            "accept_threshold": round(float(accept_threshold), 8),
            "min_title_similarity": round(float(min_title_similarity), 8),
            "min_author_overlap": round(float(min_author_overlap), 8),
            "min_claim_support": round(float(min_claim_support), 8),
            "accepted_statuses": sorted(ACCEPTED_STATUSES),
            "rejected_decision": "citation_identity_escrow",
            "fabricated_or_swapped_citations_cannot_enter_footer": True,
        },
        "economics": {
            "gross_revenue": _money(gross),
            "creator_pool": _money(creator_pool),
            "payout_total": _money(
                sum((Decimal(share["payout"]) for share in shares), Decimal("0"))
            ),
            "escrow_total": _money(escrow_total),
        },
        "citation_rows": rows,
        "canonical_footers": footers,
        "royalty_shares": shares,
        "commitments": {
            "citation_identity_input_root": hash_payload(citation_input),
            "authority_record_root": hash_payload(
                [
                    {
                        "authority_id": _authority_id(authority, index),
                        "identifier_pairs": _identifier_pairs(authority),
                        "title_hash": stable_hash(_title(authority)),
                        "author_root": hash_payload(_authors(authority)),
                    }
                    for index, authority in enumerate(authority_records, start=1)
                ]
            ),
            "citation_row_root": hash_payload(rows),
            "canonical_footer_root": hash_payload(footers),
            "share_root": hash_payload(shares),
        },
        "checks": {},
        "schemas": {
            "citation_identity_report": CITATION_IDENTITY_SCHEMA,
        },
        "summary": {
            "status": "ready",
            "target_certification_level": TARGET_CERTIFICATION_LEVEL,
            "citation_count": len(citations),
            "authority_record_count": len(authority_records),
            "citation_row_count": len(rows),
            "verified_citation_row_count": len(accepted_rows),
            "escrow_citation_row_count": len(rows) - len(accepted_rows),
            "canonical_footer_count": len(footers),
            "fabricated_citation_count": len(
                [row for row in rows if row["identity_status"] == "fabricated_citation"]
            ),
            "metadata_mismatch_count": len(
                [
                    row
                    for row in rows
                    if row["identity_status"] == "identifier_metadata_mismatch"
                ]
            ),
            "claim_support_failure_count": len(
                [
                    row
                    for row in rows
                    if row["identity_status"] == "claim_not_supported_by_citation"
                ]
            ),
            "creator_pool_conserved": (
                sum((Decimal(share["payout"]) for share in shares), Decimal("0"))
                == creator_pool
            ),
            "offline_verification_supported": True,
        },
        "privacy": {
            "prompt_text_disclosed": False,
            "response_text_disclosed": False,
            "claim_text_disclosed": False,
            "source_excerpt_disclosed": False,
            "authority_content_disclosed": False,
            "report_uses_hashes_scores_and_canonical_public_metadata": True,
        },
    }
    rendered = canonical_json(report)
    report["checks"] = _checks(
        rows=rows,
        footers=footers,
        shares=shares,
        creator_pool=creator_pool,
        rendered_report=rendered,
        private_strings=_private_strings(citation_input),
        min_claim_support=min_claim_support,
    )
    if not all(report["checks"].values()):
        report["summary"]["status"] = "failed"
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


def validate_citation_identity_report_shape(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "report_version",
        "issuer",
        "created_at",
        "event",
        "policy",
        "economics",
        "citation_rows",
        "canonical_footers",
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
            errors.append(f"missing citation identity field: {key}")
    if errors:
        return errors
    if report.get("report_version") != CITATION_IDENTITY_VERSION:
        errors.append("citation identity report version is unsupported")
    policy = report.get("policy", {})
    if policy.get("profile") != CITATION_IDENTITY_POLICY_VERSION:
        errors.append("citation identity policy is unsupported")
    if policy.get("target_certification_level") != TARGET_CERTIFICATION_LEVEL:
        errors.append("citation identity target certification level is unsupported")
    for row in report.get("citation_rows", []):
        for key in (
            "claim_id",
            "claim_hash",
            "citation_id",
            "work_id",
            "creator_id",
            "declared_identifier_type",
            "declared_identifier_hash",
            "resolved_authority_id_hash",
            "canonical_identifier_type",
            "canonical_identifier_hash",
            "metadata_scores",
            "identity_status",
            "decision",
            "rank",
            "row_hash",
        ):
            if key not in row:
                errors.append(f"missing citation identity row field: {key}")
    for footer in report.get("canonical_footers", []):
        for key in (
            "label",
            "work_id",
            "creator_id",
            "citation_id",
            "claim_ids",
            "canonical_identifier_type",
            "canonical_identifier_hash",
            "canonical_title_hash",
            "source_uri",
            "identity_status",
            "footer_text",
            "footer_row_hash",
        ):
            if key not in footer:
                errors.append(f"missing canonical citation footer field: {key}")
    return errors


def verify_citation_identity_report(
    report: dict[str, Any],
    citation_input: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Replay and verify a citation identity report against authority records."""

    errors = validate_citation_identity_report_shape(report)
    if errors:
        return errors

    expected_hash = hash_payload(_hashable_report(report))
    if expected_hash != report.get("report_hash"):
        errors.append("citation identity report hash is not reproducible")

    policy = report.get("policy", {})
    expected = make_citation_identity_report(
        citation_input,
        gross_revenue=report.get("economics", {}).get("gross_revenue", "1.00"),
        creator_pool_rate=policy.get(
            "creator_pool_rate", str(DEFAULT_CREATOR_POOL_RATE)
        ),
        accept_threshold=float(
            policy.get("accept_threshold", DEFAULT_ACCEPT_THRESHOLD)
        ),
        min_title_similarity=float(
            policy.get("min_title_similarity", DEFAULT_MIN_TITLE_SIMILARITY)
        ),
        min_author_overlap=float(
            policy.get("min_author_overlap", DEFAULT_MIN_AUTHOR_OVERLAP)
        ),
        min_claim_support=float(
            policy.get("min_claim_support", DEFAULT_MIN_CLAIM_SUPPORT)
        ),
        issuer=report.get("issuer", DEFAULT_ISSUER),
        created_at=report.get("created_at", ""),
        signing_secret=signing_secret,
    )
    for key in (
        "event",
        "policy",
        "economics",
        "citation_rows",
        "canonical_footers",
        "royalty_shares",
        "commitments",
        "checks",
        "schemas",
        "summary",
        "privacy",
    ):
        if expected.get(key) != report.get(key):
            errors.append(f"citation identity {key} does not match replay")
    if expected.get("report_hash") != report.get("report_hash"):
        errors.append("citation identity report hash does not match replay")

    if report.get("summary", {}).get("status") != "ready":
        errors.append("citation identity report status is not ready")
    for check, passed in report.get("checks", {}).items():
        if passed is not True:
            errors.append(f"citation identity check failed: {check}")

    rendered = canonical_json(report)
    for value in _private_strings(citation_input):
        if value in rendered:
            errors.append("citation identity report leaks private input text")
            break

    signature = report.get("signature", {})
    if signing_secret:
        expected_signature = sign_payload(_hashable_report(report), signing_secret)
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("citation identity report is not HMAC signed")
        elif signature.get("value") != expected_signature:
            errors.append("citation identity report signature is invalid")

    return errors
