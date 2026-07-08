"""Training-data valuation utilities for royalty priors."""

from __future__ import annotations

from itertools import combinations

from rdllm.models import Chunk


def exact_shapley_values(
    chunks: list[Chunk],
    benchmark_prompts: list[str],
    score_fn,
) -> dict[str, float]:
    """Compute exact Shapley values for small corpora.

    `score_fn(prompt, subset)` must return the utility of a subset of chunks for
    a benchmark prompt. This is intentionally simple and deterministic so audits
    can replay the valuation on small registered corpora.
    """

    if not chunks:
        return {}
    if len(chunks) > 8:
        return leave_one_out_values(chunks, benchmark_prompts, score_fn)

    values = {chunk.chunk_id: 0.0 for chunk in chunks}
    chunk_ids = [chunk.chunk_id for chunk in chunks]
    chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    n = len(chunks)

    for prompt in benchmark_prompts:
        for chunk in chunks:
            others = [chunk_id for chunk_id in chunk_ids if chunk_id != chunk.chunk_id]
            marginal_total = 0.0
            coalition_count = 0
            for coalition_size in range(len(others) + 1):
                for coalition_ids in combinations(others, coalition_size):
                    coalition = [chunk_by_id[chunk_id] for chunk_id in coalition_ids]
                    with_chunk = coalition + [chunk]
                    marginal_total += score_fn(prompt, with_chunk) - score_fn(
                        prompt, coalition
                    )
                    coalition_count += 1
            values[chunk.chunk_id] += marginal_total / coalition_count

    prompt_count = max(1, len(benchmark_prompts))
    return normalize_centered(
        {chunk_id: max(0.0, value / prompt_count) for chunk_id, value in values.items()}
    )


def leave_one_out_values(
    chunks: list[Chunk],
    benchmark_prompts: list[str],
    score_fn,
) -> dict[str, float]:
    values = {chunk.chunk_id: 0.0 for chunk in chunks}
    for prompt in benchmark_prompts:
        full_score = score_fn(prompt, chunks)
        for chunk in chunks:
            without = [candidate for candidate in chunks if candidate.chunk_id != chunk.chunk_id]
            values[chunk.chunk_id] += max(0.0, full_score - score_fn(prompt, without))
    prompt_count = max(1, len(benchmark_prompts))
    return normalize_centered(
        {chunk_id: value / prompt_count for chunk_id, value in values.items()}
    )


def normalize_centered(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    average = sum(values.values()) / len(values)
    if average <= 0:
        return {key: 1.0 for key in values}
    return {key: max(0.05, value / average) for key, value in values.items()}
