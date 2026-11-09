from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.dist import fair_die, joint
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle


def expected_max(dice: int) -> Fraction:
    return joint(*[fair_die()] * dice).map(max).expect()


def simulate_max(rng: np.random.Generator, n: int, dice: int) -> FloatArray:
    return rng.integers(1, 7, size=(n, dice)).max(axis=1).astype(np.float64)


def solve() -> Fraction:
    return expected_max(2)


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    return simulate_max(rng, n, 2)


PUZZLE = Puzzle(
    id="expected_max_two_dice",
    title="Expected maximum of two dice",
    statement="Two fair dice are rolled. What is the expected value of the larger of the "
    "two numbers?",
    tags=("order statistics", "expected value"),
    difficulty=1,
    solve=solve,
    simulate=simulate,
    explanation=(
        "P(max <= k) = (k/6)^2, because both dice must be at most k. So "
        "P(max = k) = (k^2 - (k-1)^2)/36 = (2k - 1)/36.\n"
        "Then E[max] = sum of k (2k - 1)/36 for k = 1..6.\n"
        "Answer: {answer}."
    ),
)
