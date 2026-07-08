"""Parse and resolve citation-shaped markers in displayed answers."""

from __future__ import annotations

from collections.abc import Iterable
import re


ANSWER_CITATION_MARKER_RE = re.compile(
    r"\[(?P<body>S\d+|C\d+|Source:\s*\d+|\d{1,3}(?:\s*(?:,|-|–|—)\s*\d{1,3})*)\]",
    re.IGNORECASE,
)
ANSWER_LINK_URI_RE = re.compile(
    r"(?P<uri>[A-Za-z][A-Za-z0-9+.-]*://[^\s<>)\]]+)"
)
URI_TRAILING_PUNCTUATION = ".,;:!?"
MODEL_RELIANCE_CLAIM_RE = re.compile(
    r"\b(?:(?:i|we|the model|this model|the llm|this llm|the ai|this ai|"
    r"the system|this system)\s+(?:used|relied on|consulted|read|looked at|"
    r"drew on|was influenced by|verified against|checked against)|"
    r"(?:my|our|the model's|this model's|the llm's|the ai's|the system's)\s+"
    r"(?:reasoning|chain of thought|internal computation|hidden state|"
    r"internal trace|scratchpad)|"
    r"(?:source|sources|citation|citations|document|documents|page|pages)\s+"
    r"(?:shaped|influenced|drove|determined)\s+(?:the|this|my|our)\s+"
    r"(?:answer|response|output))\b",
    re.IGNORECASE,
)


def answer_citation_markers(answer_text: str) -> list[str]:
    markers: list[str] = []
    for match in ANSWER_CITATION_MARKER_RE.finditer(answer_text):
        marker = re.sub(r"\s+", " ", match.group(0).strip())
        if marker not in markers:
            markers.append(marker)
    return markers


def answer_citation_marker_keys(marker: str) -> set[str]:
    match = ANSWER_CITATION_MARKER_RE.fullmatch(marker)
    if not match:
        return {marker.upper()}
    body = str(match.group("body")).strip()
    if re.fullmatch(r"S\d+", body, flags=re.IGNORECASE):
        return {f"[{body.upper()}]"}
    if re.fullmatch(r"C\d+", body, flags=re.IGNORECASE):
        return {f"[{body.upper()}]"}
    source_match = re.fullmatch(r"Source:\s*(\d+)", body, flags=re.IGNORECASE)
    if source_match:
        return {f"[S{source_match.group(1)}]"}

    keys: set[str] = set()
    for part in re.split(r"\s*,\s*", body):
        range_match = re.fullmatch(r"(\d{1,3})\s*[-–—]\s*(\d{1,3})", part)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            step = 1 if end >= start else -1
            for value in range(start, end + step, step):
                keys.add(f"[S{value}]")
        elif re.fullmatch(r"\d{1,3}", part):
            keys.add(f"[S{part}]")
    return keys or {marker.upper()}


def source_citation_keys(source_labels: Iterable[str]) -> set[str]:
    return {f"[{label}]".upper() for label in source_labels if label}


def claim_citation_keys(claim_indexes: Iterable[object]) -> set[str]:
    return {f"[C{index}]".upper() for index in claim_indexes if index is not None}


def resolved_answer_citation_markers(
    answer_text: str,
    allowed_keys: set[str],
) -> list[str]:
    return [
        marker
        for marker in answer_citation_markers(answer_text)
        if answer_citation_marker_keys(marker) <= allowed_keys
    ]


def unresolved_answer_citation_markers(
    answer_text: str,
    allowed_keys: set[str],
) -> list[str]:
    return [
        marker
        for marker in answer_citation_markers(answer_text)
        if not answer_citation_marker_keys(marker) <= allowed_keys
    ]


def normalize_answer_link_uri(uri: object) -> str:
    return str(uri).strip().strip("<>").rstrip(URI_TRAILING_PUNCTUATION)


def answer_link_uris(answer_text: str) -> list[str]:
    uris: list[str] = []
    for match in ANSWER_LINK_URI_RE.finditer(answer_text):
        uri = normalize_answer_link_uri(match.group("uri"))
        if uri and uri not in uris:
            uris.append(uri)
    return uris


def resolved_answer_link_uris(
    answer_text: str,
    allowed_uris: set[str],
) -> list[str]:
    normalized_allowed = {
        normalize_answer_link_uri(uri) for uri in allowed_uris if str(uri).strip()
    }
    return [
        uri
        for uri in answer_link_uris(answer_text)
        if normalize_answer_link_uri(uri) in normalized_allowed
    ]


def unresolved_answer_link_uris(
    answer_text: str,
    allowed_uris: set[str],
) -> list[str]:
    normalized_allowed = {
        normalize_answer_link_uri(uri) for uri in allowed_uris if str(uri).strip()
    }
    return [
        uri
        for uri in answer_link_uris(answer_text)
        if normalize_answer_link_uri(uri) not in normalized_allowed
    ]


def model_reliance_claim_markers(answer_text: str) -> list[str]:
    markers: list[str] = []
    for match in MODEL_RELIANCE_CLAIM_RE.finditer(answer_text):
        marker = re.sub(r"\s+", " ", match.group(0).strip()).lower()
        if marker not in markers:
            markers.append(marker)
    return markers
