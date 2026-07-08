"""Evidence-force checks for claim evidence rows."""

from __future__ import annotations

import re
from typing import Any

from rdllm.text import tokenize


CLAIM_WARRANT_PROFILE = "rdllm-evidence-force-calibration/v1"
CLAIM_WARRANT_DIMENSIONS = [
    "relation",
    "modality",
    "scope",
    "temporal_validity",
    "numeric_specificity",
]

RELATION_TERMS = {
    "because",
    "cause",
    "causes",
    "caused",
    "causal",
    "drive",
    "drives",
    "driven",
    "increase",
    "increases",
    "decrease",
    "decreases",
    "improve",
    "improves",
    "reduce",
    "reduces",
    "prevent",
    "prevents",
    "lead",
    "leads",
    "requires",
    "depends",
    "compared",
    "than",
}
MODAL_STRENGTH = {
    "may": 1,
    "might": 1,
    "could": 1,
    "can": 1,
    "should": 2,
    "need": 2,
    "needs": 2,
    "must": 3,
    "required": 3,
    "requires": 3,
    "require": 3,
    "mandatory": 3,
}
SCOPE_TERMS = {
    "all",
    "always",
    "any",
    "each",
    "entire",
    "every",
    "everyone",
    "everything",
    "never",
    "none",
    "only",
}
TEMPORAL_TERMS = {
    "current",
    "currently",
    "latest",
    "now",
    "recent",
    "recently",
    "today",
    "tonight",
}
NUMBER_PATTERN = re.compile(r"\b\d+(?:[.,]\d+)*(?:%| percent)?\b", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
BRACKET_MARKER_PATTERN = re.compile(
    r"\[(?:\s*(?:source\s*:\s*)?[A-Z]?\d+(?:\s*(?:,|-)\s*[A-Z]?\d+)*\s*)\]",
    re.IGNORECASE,
)


def _strip_bracket_markers(text: str) -> str:
    return BRACKET_MARKER_PATTERN.sub("", text)


def _token_set(text: str) -> set[str]:
    return set(tokenize(text))


def _number_tokens(text: str) -> set[str]:
    return {
        match.group(0).lower().replace(",", "")
        for match in NUMBER_PATTERN.finditer(text)
    }


def _year_tokens(text: str) -> set[str]:
    return {match.group(0) for match in YEAR_PATTERN.finditer(text)}


def _force_details(text: str) -> dict[str, list[str]]:
    tokens = _token_set(text)
    numbers = _number_tokens(text)
    years = _year_tokens(text)
    temporal_terms = tokens & TEMPORAL_TERMS
    if "as of" in text.lower():
        temporal_terms.add("as_of")
    temporal = sorted(temporal_terms | years)
    return {
        "relation": sorted(tokens & RELATION_TERMS),
        "modality": sorted(tokens & set(MODAL_STRENGTH)),
        "scope": sorted(tokens & SCOPE_TERMS),
        "temporal_validity": temporal,
        "numeric_specificity": sorted(numbers),
    }


def _max_modality_strength(tokens: list[str]) -> int:
    return max((MODAL_STRENGTH.get(token, 0) for token in tokens), default=0)


def claim_warrant_report(
    *,
    claim: str,
    evidence: str,
    supported: bool = True,
) -> dict[str, Any]:
    if not supported:
        return {
            "claim_warrant_profile": CLAIM_WARRANT_PROFILE,
            "claim_force_flags": [],
            "evidence_force_flags": [],
            "warrant_mismatch_flags": [],
            "warrant_strength_status": "not_checked",
        }

    claim_details = _force_details(_strip_bracket_markers(claim))
    evidence_details = _force_details(evidence)
    claim_flags = [
        dimension
        for dimension in CLAIM_WARRANT_DIMENSIONS
        if claim_details[dimension]
    ]
    evidence_flags = [
        dimension
        for dimension in CLAIM_WARRANT_DIMENSIONS
        if evidence_details[dimension]
    ]

    mismatches: list[str] = []
    if claim_details["relation"] and not evidence_details["relation"]:
        mismatches.append("relation")
    if _max_modality_strength(claim_details["modality"]) > _max_modality_strength(
        evidence_details["modality"]
    ):
        mismatches.append("modality")
    if not set(claim_details["scope"]).issubset(set(evidence_details["scope"])):
        mismatches.append("scope")
    claim_temporal = set(claim_details["temporal_validity"])
    if claim_temporal and not claim_temporal.issubset(
        set(evidence_details["temporal_validity"])
    ):
        mismatches.append("temporal_validity")
    claim_numbers = set(claim_details["numeric_specificity"])
    if claim_numbers and not claim_numbers.issubset(
        set(evidence_details["numeric_specificity"])
    ):
        mismatches.append("numeric_specificity")

    return {
        "claim_warrant_profile": CLAIM_WARRANT_PROFILE,
        "claim_force_flags": claim_flags,
        "evidence_force_flags": evidence_flags,
        "warrant_mismatch_flags": sorted(set(mismatches)),
        "warrant_strength_status": "failed" if mismatches else "passed",
    }
