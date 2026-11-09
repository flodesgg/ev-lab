from __future__ import annotations

from fractions import Fraction
from math import comb

import numpy as np

from ev_lab.prob.dist import Dist
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.simtools import as_float, shuffled_rows

PEOPLE = 8


def fixed_point_distribution(n: int) -> Dist[int]:
    """Number of fixed points of a uniform random permutation of n items: choose which k
    items stay in place, then derange the rest. Derangements: D(m) = (m-1)(D(m-1) + D(m-2))."""
    derangements = [1, 0]
    for m in range(2, n + 1):
        derangements.append((m - 1) * (derangements[m - 1] + derangements[m - 2]))
    return Dist.from_weights({k: comb(n, k) * derangements[n - k] for k in range(n + 1)})


def solve() -> Fraction:
    return fixed_point_distribution(PEOPLE).expect()


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    hats = shuffled_rows(rng, n, np.arange(PEOPLE))
    return as_float((hats == np.arange(PEOPLE)).sum(axis=1))


PUZZLE = Puzzle(
    id="fixed_points_permutation",
    title="Hats returned at random",
    statement=f"{PEOPLE} people leave their hats at the door. The hats are handed back in a "
    "uniformly random order. What is the expected number of people who get their own hat?",
    tags=("combinatorics", "expected value"),
    difficulty=2,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Linearity of expectation: person i gets their own hat with probability 1/n, so "
        "the expected count is n x (1/n). The events are dependent, but linearity does "
        "not need independence.\n"
        "The answer does not depend on n. Answer: {answer}."
    ),
)
