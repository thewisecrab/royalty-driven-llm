"""Small text utilities used by the royalty prototype."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from typing import Iterable

TOKEN_RE = re.compile(r"[a-z0-9]+")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

STOPWORDS = {
    "a",
    "about",
    "all",
    "also",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "by",
    "can",
    "for",
    "from",
    "has",
    "have",
    "how",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "use",
    "used",
    "uses",
    "when",
    "where",
    "with",
}


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in TOKEN_RE.findall(text.lower())
        if len(token) > 1 and token not in STOPWORDS
    ]


def term_counts(tokens: Iterable[str]) -> Counter[str]:
    return Counter(tokens)


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    common = set(left) & set(right)
    numerator = sum(left[key] * right[key] for key in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def jaccard_similarity(left_tokens: Iterable[str], right_tokens: Iterable[str]) -> float:
    left = set(left_tokens)
    right = set(right_tokens)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def ngrams(tokens: list[str], size: int) -> set[tuple[str, ...]]:
    if size <= 0 or len(tokens) < size:
        return set()
    return {tuple(tokens[index : index + size]) for index in range(len(tokens) - size + 1)}


def ngram_containment(source_tokens: list[str], output_tokens: list[str], size: int = 5) -> float:
    source = ngrams(source_tokens, size)
    output = ngrams(output_tokens, size)
    if not source or not output:
        return 0.0
    return len(source & output) / len(source)


def longest_common_token_sequence(
    left_tokens: list[str], right_tokens: list[str]
) -> tuple[int, list[str]]:
    if not left_tokens or not right_tokens:
        return 0, []

    previous = [0] * (len(right_tokens) + 1)
    best_length = 0
    best_end = 0

    for left_index, left_token in enumerate(left_tokens, start=1):
        current = [0] * (len(right_tokens) + 1)
        for right_index, right_token in enumerate(right_tokens, start=1):
            if left_token == right_token:
                current[right_index] = previous[right_index - 1] + 1
                if current[right_index] > best_length:
                    best_length = current[right_index]
                    best_end = left_index
        previous = current

    return best_length, left_tokens[best_end - best_length : best_end]


def split_sentences(text: str) -> list[str]:
    sentences = [part.strip() for part in SENTENCE_RE.split(text.strip()) if part.strip()]
    return sentences or [text.strip()]


def chunk_text(text: str, max_tokens: int = 90) -> list[str]:
    sentences = split_sentences(text)
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0

    for sentence in sentences:
        size = len(tokenize(sentence))
        if current and current_size + size > max_tokens:
            chunks.append(" ".join(current))
            current = [sentence]
            current_size = size
        else:
            current.append(sentence)
            current_size += size

    if current:
        chunks.append(" ".join(current))
    return chunks
