from __future__ import annotations

from fractions import Fraction
from functools import cache
from math import comb

import numpy as np

from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.simtools import shuffled_rows

A_VOTES, B_VOTES = 6, 4


@cache
def _ways(a: int, b: int) -> int:
    """Number of counting orders that reach a votes for A and b for B with A strictly ahead
    after every vote counted so far."""
    if (a, b) == (0, 0):
        return 1
    if a <= b or b < 0:
        return 0
    return _ways(a - 1, b) + _ways(a, b - 1)


def always_ahead(a: int, b: int) -> Fraction:
    return Fraction(_ways(a, b), comb(a + b, b))


def solve() -> Fraction:
    return always_ahead(A_VOTES, B_VOTES)


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    votes = np.array([1] * A_VOTES + [-1] * B_VOTES)
    lead = shuffled_rows(rng, n, votes).cumsum(axis=1)
    return (lead > 0).all(axis=1).astype(np.float64)


PUZZLE = Puzzle(
    id="ballot_problem",
    title="The ballot problem",
    statement=(
        f"In an election candidate A gets {A_VOTES} votes and candidate B gets {B_VOTES}. "
        "The votes are counted one at a time in a uniformly random order. What is the "
        "probability that A is strictly ahead of B throughout the whole count?"
    ),
    tags=("combinatorics", "martingales"),
    difficulty=3,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Count paths: of all orders of the votes, how many keep A strictly ahead after "
        "every vote? A grid recursion (ways to reach (a, b) = ways from (a-1, b) plus ways "
        "from (a, b-1), zero whenever a <= b) gives the count.\n"
        "The classical result (reflection principle) is (a - b)/(a + b).\n"
        "Answer: {answer}."
    ),
)
