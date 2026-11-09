"""Regret matching in self-play on a zero-sum matrix game (Hart & Mas-Colell, 2000).

Regret of an action = how much better I would have done, in total so far, had I always
played that action instead of what I actually played. Regret matching plays each action
with probability proportional to its positive regret. If both players do this, their
*average* strategies converge to a Nash equilibrium of a zero-sum game (the current
strategies need not converge: in rock-paper-scissors they keep cycling).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class RegretRun:
    row: FloatArray  # average strategies
    col: FloatArray
    iterations: int


def strategy_from_regrets(regrets: FloatArray) -> FloatArray:
    positive = np.maximum(regrets, 0.0)
    total = positive.sum()
    return positive / total if total > 0 else np.full(len(regrets), 1.0 / len(regrets))


def regret_matching(
    a: Sequence[Sequence[Fraction | int]], iterations: int, rng: np.random.Generator
) -> RegretRun:
    payoff = np.array([[float(v) for v in row] for row in a])
    m, n = payoff.shape
    regret_row, regret_col = np.zeros(m), np.zeros(n)
    sum_row, sum_col = np.zeros(m), np.zeros(n)
    for _ in range(iterations):
        s_row, s_col = strategy_from_regrets(regret_row), strategy_from_regrets(regret_col)
        sum_row += s_row
        sum_col += s_col
        i = int(rng.choice(m, p=s_row))
        j = int(rng.choice(n, p=s_col))
        # what each action would have earned against the opponent's actual move
        regret_row += payoff[:, j] - payoff[i, j]
        regret_col += -payoff[i, :] + payoff[i, j]
    return RegretRun(sum_row / iterations, sum_col / iterations, iterations)
