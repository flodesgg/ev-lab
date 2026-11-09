from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.dist import fair_die, sum_of
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.simtools import as_float


def solve() -> Fraction:
    return sum_of(fair_die(), 3)[10]


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    return as_float(rng.integers(1, 7, size=(n, 3)).sum(axis=1) == 10)


PUZZLE = Puzzle(
    id="three_dice_sum_ten",
    title="Three dice summing to ten",
    statement="Three fair dice are rolled. What is the probability that the numbers sum to "
    "exactly 10?",
    tags=("combinatorics",),
    difficulty=1,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Count ordered triples out of 216. List the unordered combinations that sum to 10 "
        "and count the orderings of each: three different numbers give 6 orders, a pair "
        "gives 3.\n"
        "Galileo's point: 9 and 10 have the same number of unordered combinations, but 10 "
        "has more ordered ones.\n"
        "Answer: {answer}."
    ),
)
