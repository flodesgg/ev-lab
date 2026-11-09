from __future__ import annotations

from fractions import Fraction
from math import comb

import numpy as np

from ev_lab.prob.dist import Dist
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.simtools import shuffled_rows

CARDS, DRAWN = 20, 5


def max_distribution(cards: int, drawn: int) -> Dist[int]:
    """The maximum is k when card k is drawn and the other drawn cards are all below k."""
    return Dist.from_weights({k: comb(k - 1, drawn - 1) for k in range(drawn, cards + 1)})


def solve() -> Fraction:
    return max_distribution(CARDS, DRAWN).expect()


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    hands = shuffled_rows(rng, n, np.arange(1, CARDS + 1))[:, :DRAWN]
    return hands.max(axis=1).astype(np.float64)


PUZZLE = Puzzle(
    id="expected_max_of_draws",
    title="Largest of five numbered cards",
    statement=f"Cards numbered 1 to {CARDS} are shuffled and {DRAWN} are drawn without "
    "replacement. What is the expected value of the largest number drawn?",
    tags=("order statistics", "combinatorics"),
    difficulty=2,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Symmetry of gaps: the 5 drawn cards split the 15 others into 6 gaps of equal "
        "expected size 15/6. The largest drawn card sits just below the last gap: "
        "20 - 15/6.\n"
        "General rule: the maximum of m draws from 1..N averages m (N + 1)/(m + 1).\n"
        "Answer: {answer}."
    ),
)
