"""Optional claim-versus-evidence entailment score.

The lexical channel remains a text-overlap metric. This module adds a separate
fact-check style score in the MiniCheck / AlignScore setup: the evidence is the
premise and the claim is the hypothesis.

No neural checkpoint is required. ``backend="auto"`` uses a deterministic stub.
``backend="minicheck"`` or ``backend="alignscore"`` lazy-imports that package and,
if it is missing or no local scorer is supplied, falls back to the same stub.
The result records the model name, version, threshold, and backend actually used.

References for the task, not for the stub's accuracy:
MiniCheck (Tang, Laban, Durrett), arXiv:2404.10774.
AlignScore (Zha, Yang, Li, Hu), arXiv:2305.16739.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from rdllm.source_usage_metrics import NLI_SUPPORT_METRIC_ID
from rdllm.text import jaccard_similarity, tokenize

STUB_MODEL_NAME = "rdllm-deterministic-entailment-stub"
STUB_MODEL_VERSION = "1"
DEFAULT_ENTAILMENT_THRESHOLD = 0.75
OPTIONAL_BACKENDS = ("minicheck", "alignscore")

_NEGATION_RE = re.compile(
    r"\b(?:not|no|never|none|neither|without|cannot)\b|n't\b",
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
_NEGATION_TOKENS = {
    "not",
    "no",
    "never",
    "none",
    "neither",
    "without",
    "cannot",
    "cant",
    "dont",
    "doesnt",
    "didnt",
    "isnt",
    "arent",
    "wasnt",
    "werent",
    "wont",
    "wouldnt",
    "shouldnt",
    "couldnt",
}


def text_overlap_score(claim: str, evidence: str) -> float:
    """Symmetric token Jaccard overlap. This is not an entailment judgment."""

    claim_tokens = tokenize(claim)
    evidence_tokens = tokenize(evidence)
    if not claim_tokens or not evidence_tokens:
        return 0.0
    return jaccard_similarity(claim_tokens, evidence_tokens)


def _polarity(text: str) -> int:
    return len(_NEGATION_RE.findall(text)) % 2


def _content_tokens(text: str) -> set[str]:
    return {token for token in tokenize(text) if token not in _NEGATION_TOKENS}


def _numbers(text: str) -> set[str]:
    return set(_NUMBER_RE.findall(text))


def deterministic_entailment_score(claim: str, evidence: str) -> float:
    """Directional coverage of the claim by the evidence, with contradiction caps.

    Negation disagreement and claim numbers missing from the evidence lower the
    score even when most words overlap. The score is deterministic and is not a
    trained NLI model.
    """

    claim_tokens = _content_tokens(claim)
    evidence_tokens = _content_tokens(evidence)
    if not claim_tokens or not evidence_tokens:
        return 0.0
    coverage = len(claim_tokens & evidence_tokens) / len(claim_tokens)
    if _polarity(claim) != _polarity(evidence) and coverage >= 0.5:
        return round(min(coverage, 0.2), 8)
    claim_numbers = _numbers(claim)
    if claim_numbers and not claim_numbers <= _numbers(evidence):
        return round(min(coverage, 0.35), 8)
    return round(min(1.0, coverage), 8)


def _load_backend(name: str) -> Any:
    if name == "minicheck":
        import minicheck as module
    elif name == "alignscore":
        import alignscore as module
    else:
        raise ValueError(f"unknown entailment backend: {name}")
    return module


def score_entailment(
    claim: str,
    evidence: str,
    *,
    backend: str = "auto",
    threshold: float = DEFAULT_ENTAILMENT_THRESHOLD,
    scorer: Callable[[str, str], float] | None = None,
) -> dict[str, Any]:
    """Score whether ``evidence`` entails ``claim``.

    ``scorer``, when provided, is called as ``scorer(claim, evidence)`` and its
    float result is used directly. Otherwise optional neural backends are only
    imported when named, and any import or missing-scorer condition falls back
    to :func:`deterministic_entailment_score`.
    """

    requested = str(backend or "auto")
    fallback_reason = ""
    model_name = STUB_MODEL_NAME
    model_version = STUB_MODEL_VERSION
    used_backend = "deterministic_stub"
    score: float | None = None

    if scorer is not None:
        score = float(scorer(claim, evidence))
        used_backend = "injected" if requested == "auto" else requested
        model_name = str(getattr(scorer, "model_name", "injected-scorer"))
        model_version = str(getattr(scorer, "model_version", "injected"))
    elif requested in OPTIONAL_BACKENDS:
        try:
            module = _load_backend(requested)
        except ImportError as exc:
            fallback_reason = f"{requested} is not installed ({type(exc).__name__})"
        else:
            module_name = str(getattr(module, "__name__", requested))
            fallback_reason = (
                f"{requested} imported ({module_name}) but no local scorer was "
                "provided; deterministic stub used"
            )

    if score is None:
        score = deterministic_entailment_score(claim, evidence)
        used_backend = "deterministic_stub"
        model_name = STUB_MODEL_NAME
        model_version = STUB_MODEL_VERSION

    score = round(max(0.0, min(1.0, score)), 8)
    label = "entailed" if score >= threshold else "not_entailed"
    return {
        "metric_id": NLI_SUPPORT_METRIC_ID,
        "label": label,
        "score": score,
        "threshold": threshold,
        "model_name": model_name,
        "model_version": model_version,
        "backend": used_backend,
        "requested_backend": requested,
        "fallback_reason": fallback_reason,
        "text_overlap_score": round(text_overlap_score(claim, evidence), 8),
    }
