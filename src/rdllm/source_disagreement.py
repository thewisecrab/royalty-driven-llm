"""Conservative source-disagreement checks for claim evidence rows."""

from __future__ import annotations

import re
from typing import Any

from rdllm.text import jaccard_similarity, tokenize


SOURCE_DISAGREEMENT_PROFILE = "rdllm-visible-source-disagreement/v1"
NEGATION_TERMS = {
    "no",
    "not",
    "never",
    "none",
    "cannot",
    "cant",
    "without",
}
NEGATION_PHRASES = (
    "do not",
    "does not",
    "did not",
    "must not",
    "should not",
    "is not",
    "are not",
    "was not",
    "were not",
)
BRACKET_MARKER_PATTERN = re.compile(
    r"\[(?:\s*(?:source\s*:\s*)?[A-Z]?\d+(?:\s*(?:,|-)\s*[A-Z]?\d+)*\s*)\]",
    re.IGNORECASE,
)
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "or",
    "should",
    "that",
    "the",
    "this",
    "to",
    "with",
}


def _strip_bracket_markers(text: str) -> str:
    return BRACKET_MARKER_PATTERN.sub("", text)


def _content_tokens(text: str) -> list[str]:
    return [
        token
        for token in tokenize(_strip_bracket_markers(text))
        if token not in STOPWORDS and token not in NEGATION_TERMS
    ]


def _has_negation(text: str) -> bool:
    clean_text = _strip_bracket_markers(text).lower()
    tokens = set(tokenize(clean_text))
    return bool(tokens & NEGATION_TERMS) or any(
        phrase in clean_text for phrase in NEGATION_PHRASES
    )


def _candidate_overlap(claim_tokens: list[str], evidence_tokens: list[str]) -> bool:
    overlap_count = len(set(claim_tokens) & set(evidence_tokens))
    return overlap_count >= 3 and jaccard_similarity(claim_tokens, evidence_tokens) >= 0.2


def claim_source_disagreement_report(
    *,
    claim: str,
    source_label: str,
    source_rows: list[dict[str, Any]],
    supported: bool = True,
) -> dict[str, Any]:
    if not supported:
        return {
            "source_disagreement_profile": SOURCE_DISAGREEMENT_PROFILE,
            "agreement_source_labels": [],
            "disagreement_source_labels": [],
            "source_disagreement_status": "not_checked",
        }

    claim_tokens = _content_tokens(claim)
    claim_negative = _has_negation(claim)
    agreement_labels: list[str] = []
    disagreement_labels: list[str] = []

    for row in source_rows:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label", ""))
        evidence = str(row.get("evidence_preview", ""))
        if not label or not evidence:
            continue
        evidence_tokens = _content_tokens(evidence)
        if not _candidate_overlap(claim_tokens, evidence_tokens):
            continue
        if _has_negation(evidence) != claim_negative:
            disagreement_labels.append(label)
        else:
            agreement_labels.append(label)

    if source_label and source_label not in agreement_labels and not disagreement_labels:
        agreement_labels.append(source_label)

    return {
        "source_disagreement_profile": SOURCE_DISAGREEMENT_PROFILE,
        "agreement_source_labels": sorted(set(agreement_labels)),
        "disagreement_source_labels": sorted(set(disagreement_labels)),
        "source_disagreement_status": (
            "failed" if disagreement_labels else "passed"
        ),
    }
