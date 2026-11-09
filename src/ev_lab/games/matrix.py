"""Two-player zero-sum matrix games solved by linear programming.

A[i][j] is what the column player pays the row player when row plays i and column plays j.
The row player picks a mixed strategy x to maximise the worst case over columns:

    maximise v   subject to   sum_i x_i A[i][j] >= v for every column j,  x a probability vector

The column player's problem is the mirror image, and by the minimax theorem both have the
same optimal value: the value of the game.

scipy's solver works in floats. The solution is then turned back into Fractions and
*certified exactly*: if the row strategy guarantees at least v against every column and the
column strategy concedes at most v against every row, the pair is a Nash equilibrium and v
is the value. No trust in floating point is needed for a certified result.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import linprog

from ev_lab.prob.exact import exact

Matrix = Sequence[Sequence[Fraction | int]]
FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class MatrixSolution:
    value: Fraction
    row: tuple[Fraction, ...]
    col: tuple[Fraction, ...]
    certified: bool  # True when the exact check below proves optimality


def row_guarantee(a: Matrix, x: Sequence[Fraction]) -> Fraction:
    """What the row strategy x earns against the column's best reply."""
    return min(
        sum((x[i] * exact(a[i][j]) for i in range(len(a))), Fraction(0)) for j in range(len(a[0]))
    )


def col_guarantee(a: Matrix, y: Sequence[Fraction]) -> Fraction:
    """What the column strategy y concedes against the row's best reply."""
    return max(
        sum((exact(a[i][j]) * y[j] for j in range(len(a[0]))), Fraction(0)) for i in range(len(a))
    )


def exploitability(a: Matrix, x: Sequence[Fraction], y: Sequence[Fraction]) -> Fraction:
    """How much the two players together could gain by best-responding: 0 at equilibrium."""
    return col_guarantee(a, y) - row_guarantee(a, x)


def _lp_max_min(payoff: FloatArray) -> FloatArray:
    """Mixed strategy over rows maximising the minimum expected payoff over columns."""
    m, n = payoff.shape
    # variables: x_0..x_{m-1}, v.  minimise -v  s.t.  v - sum_i x_i A[i][j] <= 0,  sum x = 1
    c = np.zeros(m + 1)
    c[-1] = -1.0
    a_ub = np.hstack([-payoff.T, np.ones((n, 1))])
    a_eq = np.hstack([np.ones((1, m)), np.zeros((1, 1))])
    result = linprog(
        c,
        A_ub=a_ub,
        b_ub=np.zeros(n),
        A_eq=a_eq,
        b_eq=np.ones(1),
        bounds=[(0, None)] * m + [(None, None)],
        method="highs",
    )
    if not result.success or result.x is None:
        raise RuntimeError(f"linear program failed: {result.message}")
    return np.asarray(result.x[:m], dtype=np.float64)


def _rationalise(p: FloatArray, max_denominator: int) -> tuple[Fraction, ...]:
    fractions = [Fraction(float(max(v, 0.0))).limit_denominator(max_denominator) for v in p]
    total = sum(fractions, Fraction(0))
    return tuple(f / total for f in fractions)


def solve_zero_sum(a: Matrix, max_denominator: int = 10_000) -> MatrixSolution:
    """Value and optimal mixed strategies of the zero-sum game with row payoffs `a`."""
    if not a or not a[0] or any(len(row) != len(a[0]) for row in a):
        raise ValueError("the payoff matrix must be rectangular and non-empty")
    payoff = np.array([[float(exact(v)) for v in row] for row in a])
    x = _rationalise(_lp_max_min(payoff), max_denominator)
    y = _rationalise(_lp_max_min(-payoff.T), max_denominator)
    low, high = row_guarantee(a, x), col_guarantee(a, y)
    # low <= value <= high always; equality proves both strategies optimal
    return MatrixSolution(value=low, row=x, col=y, certified=low == high)
