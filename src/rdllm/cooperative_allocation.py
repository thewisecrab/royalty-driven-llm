"""Shapley and Banzhaf payout weights for a small set of context sources.

The engine default remains the fixed-coefficient utility in ``engine._allocate``.
This module is the opt-in alternative. It allocates an explicit value function
``v(coalition)``. Exact values are used for small player sets. Monte Carlo
estimates are available for larger sets and can be rescaled so the reported
weights sum to ``v(N) - v(empty)``.

These are classical cooperative values, not an implementation of the polynomial
MaxShapley algorithm or of Cluster Shapley clustering.

Cited methods:
- MaxShapley: Patel, Zhou, and Fanti, arXiv:2512.05958.
- Data Banzhaf: Wang and Jia, arXiv:2205.15466.
- Cluster Shapley: Ye and Yoganarasimhan, arXiv:2505.23842
  (paper title: Fair Document Valuation in LLM Summaries via Shapley Values).
- Data Shapley: Ghorbani and Zou, arXiv:1904.02868.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Iterable, Mapping
from decimal import Decimal, ROUND_HALF_UP
from itertools import combinations

Player = str
ValueFn = Callable[[frozenset[Player]], float]

ALLOCATION_METHOD_IDS = {
    "fixed_coefficients": "rdllm-fixed-coefficient-allocation/v1",
    "shapley": "rdllm-shapley-context-allocation/v1",
    "banzhaf": "rdllm-normalized-banzhaf-context-allocation/v1",
}
MONEY_QUANT = Decimal("0.000001")
EXACT_PLAYER_LIMIT = 10


def output_token_coverage_value(
    coalition: Iterable[Player],
    token_sets: Mapping[Player, set[str]],
    output_tokens: set[str],
) -> float:
    """Share of distinct output tokens covered by the coalition.

    Coverage is monotone. A source whose tokens miss the output is a null player.
    Two sources with the same token set are symmetric.
    """

    if not output_tokens:
        return 0.0
    covered: set[str] = set()
    for player in coalition:
        covered |= token_sets.get(player, set())
    return len(covered & output_tokens) / len(output_tokens)


def _scale_to_target(values: dict[Player, float], target: float) -> dict[Player, float]:
    total = sum(values.values())
    if abs(target) <= 1e-12:
        return {player: 0.0 for player in values}
    if abs(total) <= 1e-12:
        return {player: 0.0 for player in values}
    factor = target / total
    return {player: weight * factor for player, weight in values.items()}


def shapley_values(players: list[Player], value_fn: ValueFn) -> dict[Player, float]:
    """Exact Shapley values. ``sum(values) == v(N) - v(empty)`` for finite games."""

    if not players:
        return {}
    n = len(players)
    factorial = math.factorial
    weights: dict[Player, float] = {}
    for player in players:
        others = [candidate for candidate in players if candidate != player]
        total = 0.0
        for size in range(len(others) + 1):
            # |S|!(n-|S|-1)! / n!
            coalition_weight = factorial(size) * factorial(n - size - 1) / factorial(n)
            for coalition in combinations(others, size):
                base = frozenset(coalition)
                marginal = float(value_fn(base | {player})) - float(value_fn(base))
                total += coalition_weight * marginal
        weights[player] = total
    return weights


def banzhaf_values(
    players: list[Player],
    value_fn: ValueFn,
    *,
    normalized: bool = True,
) -> dict[Player, float]:
    """Average marginal contribution over coalitions (Banzhaf).

    ``normalized=True`` rescales the averages so they sum to ``v(N) - v(empty)``.
    The raw averages keep symmetry and the null-player property and are not
    claimed to be efficient.
    """

    if not players:
        return {}
    weights: dict[Player, float] = {}
    for player in players:
        others = [candidate for candidate in players if candidate != player]
        total = 0.0
        count = 0
        for size in range(len(others) + 1):
            for coalition in combinations(others, size):
                base = frozenset(coalition)
                total += float(value_fn(base | {player})) - float(value_fn(base))
                count += 1
        weights[player] = total / count if count else 0.0
    if normalized:
        target = float(value_fn(frozenset(players))) - float(value_fn(frozenset()))
        return _scale_to_target(weights, target)
    return weights


def monte_carlo_shapley_values(
    players: list[Player],
    value_fn: ValueFn,
    *,
    samples: int = 256,
    seed: int = 0,
    normalized: bool = True,
) -> dict[Player, float]:
    """Permutation-sampled Shapley estimate. Seeded, so a given game replays."""

    if not players:
        return {}
    if samples < 1:
        raise ValueError("samples must be positive")
    rng = random.Random(seed)
    totals = {player: 0.0 for player in players}
    empty_value = float(value_fn(frozenset()))
    for _ in range(samples):
        order = list(players)
        rng.shuffle(order)
        coalition: set[Player] = set()
        previous = empty_value
        for player in order:
            coalition.add(player)
            current = float(value_fn(frozenset(coalition)))
            totals[player] += current - previous
            previous = current
    values = {player: total / samples for player, total in totals.items()}
    if normalized:
        target = float(value_fn(frozenset(players))) - empty_value
        return _scale_to_target(values, target)
    return values


def monte_carlo_banzhaf_values(
    players: list[Player],
    value_fn: ValueFn,
    *,
    samples: int = 256,
    seed: int = 0,
    normalized: bool = True,
) -> dict[Player, float]:
    """Sample coalitions uniformly for each player. Seeded."""

    if not players:
        return {}
    if samples < 1:
        raise ValueError("samples must be positive")
    rng = random.Random(seed)
    totals = {player: 0.0 for player in players}
    others = {player: [candidate for candidate in players if candidate != player] for player in players}
    for _ in range(samples):
        for player in players:
            coalition = frozenset(
                candidate for candidate in others[player] if rng.random() < 0.5
            )
            totals[player] += float(value_fn(coalition | {player})) - float(value_fn(coalition))
    values = {player: total / samples for player, total in totals.items()}
    if normalized:
        target = float(value_fn(frozenset(players))) - float(value_fn(frozenset()))
        return _scale_to_target(values, target)
    return values


def cooperative_values(
    players: list[Player],
    value_fn: ValueFn,
    *,
    method: str,
    samples: int = 256,
    seed: int = 0,
) -> dict[Player, float]:
    """Dispatch exact or Monte Carlo Shapley / normalized Banzhaf values."""

    if method not in {"shapley", "banzhaf"}:
        raise ValueError(f"unsupported cooperative method: {method}")
    exact = len(players) <= EXACT_PLAYER_LIMIT
    if method == "shapley":
        if exact:
            return shapley_values(players, value_fn)
        return monte_carlo_shapley_values(
            players, value_fn, samples=samples, seed=seed, normalized=True
        )
    if exact:
        return banzhaf_values(players, value_fn, normalized=True)
    return monte_carlo_banzhaf_values(
        players, value_fn, samples=samples, seed=seed, normalized=True
    )


def allocate_creator_pool(
    values: Mapping[Player, float],
    creator_pool: Decimal | str | int | float,
) -> dict[Player, Decimal]:
    """Turn nonnegative cooperative weights into pool amounts that sum to the pool.

    Nonpositive weights are omitted. The last remaining player, in sorted id
    order, receives the rounding remainder.
    """

    pool = Decimal(str(creator_pool)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    positive = [
        (player, Decimal(str(weight)))
        for player, weight in sorted(values.items())
        if Decimal(str(weight)) > 0
    ]
    if pool == 0 or not positive:
        return {}
    denominator = sum((weight for _, weight in positive), Decimal("0"))
    if denominator <= 0:
        return {}
    payouts: dict[Player, Decimal] = {}
    remaining = pool
    for index, (player, weight) in enumerate(positive):
        if index == len(positive) - 1:
            payout = remaining
        else:
            payout = (pool * weight / denominator).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            remaining -= payout
        payouts[player] = payout
    return payouts
