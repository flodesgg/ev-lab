from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.expected_max_two_dice import expected_max, simulate_max


def solve() -> Fraction:
    return expected_max(3)


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    return simulate_max(rng, n, 3)


PUZZLE = Puzzle(
    id="expected_max_three_dice",
    title="Expected maximum of three dice",
    statement="Three fair dice are rolled. What is the expected value of the largest of "
    "the three numbers?",
    tags=("order statistics", "expected value"),
    difficulty=1,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Same idea as for two dice: P(max <= k) = (k/6)^3.\n"
        "A quick route is the tail sum E[max] = sum over k = 0..5 of P(max > k) "
        "= sum of (1 - (k/6)^3).\n"
        "Answer: {answer}."
    ),
)
