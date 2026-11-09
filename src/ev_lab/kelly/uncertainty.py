"""Kelly sizing when the win probability is only an estimate.

The true p is unknown. I observe n past bets with k wins, estimate p_hat = k / n and stake
the Kelly fraction of p_hat (never less than 0, never more than a cap). The growth I then
actually get is g(that fraction) evaluated at the *true* p. Averaging over the binomial
distribution of k gives the expected growth exactly: no simulation is needed.

Overestimating the edge costs more than underestimating it (g falls faster to the right of
f* than to the left), which is why practitioners stake a fraction of Kelly.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from scipy.stats import binom

from ev_lab.kelly.core import growth_rate


@dataclass(frozen=True)
class UncertaintyRow:
    n: int
    full_on_estimate: float  # expected growth per bet, staking Kelly(p_hat)
    half_on_estimate: float  # staking half of Kelly(p_hat)
    true_kelly: float  # g(f*) with the true p: the unreachable benchmark
    p_no_bet: float  # probability that the estimate shows no edge, so nothing is staked
    p_overbet_2x: float  # probability that Kelly(p_hat) is more than twice the true Kelly


def estimated_fraction(wins: int, n: int, odds: float, max_fraction: float) -> float:
    p_hat = wins / n
    return min(max_fraction, max(0.0, p_hat - (1 - p_hat) / odds))


def expected_growth(n: int, p: float, odds: float, scale: float, max_fraction: float) -> float:
    """E[g(scale x Kelly(p_hat))] over p_hat = Binomial(n, p) / n, with the true p in g."""
    total = 0.0
    for k in range(n + 1):
        weight = float(binom.pmf(k, n, p))
        if weight > 0.0:
            f = scale * estimated_fraction(k, n, odds, max_fraction)
            total += weight * growth_rate(f, p, odds)
    return total


def uncertainty_table(
    sample_sizes: Sequence[int], p: float, odds: float, max_fraction: float
) -> list[UncertaintyRow]:
    kelly = p - (1 - p) / odds
    best = growth_rate(kelly, p, odds)
    rows = []
    for n in sample_sizes:
        fractions = [estimated_fraction(k, n, odds, max_fraction) for k in range(n + 1)]
        pmf = [float(binom.pmf(k, n, p)) for k in range(n + 1)]
        rows.append(
            UncertaintyRow(
                n=n,
                full_on_estimate=expected_growth(n, p, odds, 1.0, max_fraction),
                half_on_estimate=expected_growth(n, p, odds, 0.5, max_fraction),
                true_kelly=best,
                p_no_bet=sum(w for w, f in zip(pmf, fractions, strict=True) if f == 0.0),
                p_overbet_2x=sum(w for w, f in zip(pmf, fractions, strict=True) if f > 2 * kelly),
            )
        )
    return rows
