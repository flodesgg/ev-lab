"""Simulating repeated Kelly-type bets on many paths.

All bet sizes are run on the *same* sequences of wins and losses (common random numbers),
so differences between fractions are not blurred by different luck.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from ev_lab.kelly.core import growth_rate
from ev_lab.prob.montecarlo import McResult


@dataclass(frozen=True)
class FractionResult:
    multiple: float  # of the Kelly fraction
    fraction: float  # of wealth staked per bet
    growth_exact: float  # g(f)
    growth_sim: McResult  # mean log growth per bet across paths
    median_wealth: float  # terminal, start = 1
    mean_wealth: float
    p_below_ruin_level: McResult  # terminal wealth below the ruin level
    p_hit_drawdown_level: McResult  # wealth ever at or below the drawdown level
    max_drawdown_quantiles: tuple[float, float, float]  # median, 90%, 99%


def win_counts(p: float, bets: int, paths: int, rng: np.random.Generator) -> NDArray[np.int32]:
    """Cumulative number of wins after 0..bets bets, one row per path."""
    wins = rng.random((paths, bets)) < p
    counts = np.zeros((paths, bets + 1), dtype=np.int32)
    np.cumsum(wins, axis=1, out=counts[:, 1:])
    return counts


def _proportion(hits: NDArray[np.bool_]) -> McResult:
    n = int(hits.size)
    share = float(hits.mean())
    return McResult(share, math.sqrt(share * (1 - share) / n), n)


def evaluate_fraction(
    counts: NDArray[np.int32],
    fraction: float,
    multiple: float,
    p: float,
    odds: float,
    ruin_level: float,
    drawdown_level: float,
) -> FractionResult:
    paths, columns = counts.shape
    bets = columns - 1
    up, down = math.log1p(odds * fraction), math.log1p(-fraction)
    steps = np.arange(columns)
    log_wealth = counts * up + (steps - counts) * down  # (paths, bets + 1), starts at 0
    final = log_wealth[:, -1]
    per_bet = final / bets
    running_max = np.maximum.accumulate(log_wealth, axis=1)
    max_drawdown = 1.0 - np.exp((log_wealth - running_max).min(axis=1))
    q50, q90, q99 = (float(q) for q in np.quantile(max_drawdown, [0.5, 0.9, 0.99]))
    return FractionResult(
        multiple=multiple,
        fraction=fraction,
        growth_exact=growth_rate(fraction, p, odds),
        growth_sim=McResult(
            float(per_bet.mean()), float(per_bet.std(ddof=1)) / math.sqrt(paths), paths
        ),
        median_wealth=float(np.exp(np.median(final))),
        mean_wealth=float(np.exp(final).mean()),
        p_below_ruin_level=_proportion(final < math.log(ruin_level)),
        p_hit_drawdown_level=_proportion(log_wealth.min(axis=1) <= math.log(drawdown_level)),
        max_drawdown_quantiles=(q50, q90, q99),
    )


def simulate(
    p: float,
    odds: float,
    kelly: float,
    multiples: Sequence[float],
    bets: int,
    paths: int,
    ruin_level: float,
    drawdown_level: float,
    rng: np.random.Generator,
) -> list[FractionResult]:
    counts = win_counts(p, bets, paths, rng)
    return [
        evaluate_fraction(counts, m * kelly, m, p, odds, ruin_level, drawdown_level)
        for m in multiples
    ]
