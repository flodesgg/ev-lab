from __future__ import annotations

from fractions import Fraction
from math import comb

import numpy as np

from ev_lab.prob.dist import Dist
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.simtools import shuffled_rows

CARDS, ACES = 52, 4


def first_ace_distribution(cards: int, aces: int) -> Dist[int]:
    """The first ace is at position k when the other aces all lie in the cards after k."""
    return Dist.from_weights({k: comb(cards - k, aces - 1) for k in range(1, cards - aces + 2)})


def solve() -> Fraction:
    return first_ace_distribution(CARDS, ACES).expect()


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    deck = np.array([1] * ACES + [0] * (CARDS - ACES))
    return (shuffled_rows(rng, n, deck).argmax(axis=1) + 1).astype(np.float64)


PUZZLE = Puzzle(
    id="first_ace_position",
    title="Position of the first ace",
    statement="A standard 52-card deck is shuffled and cards are turned over one at a "
    "time. On average, at which position does the first ace appear (the top card is "
    "position 1)?",
    tags=("order statistics", "combinatorics"),
    difficulty=2,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Symmetry: the 4 aces cut the 48 other cards into 5 gaps (before the first ace, "
        "between aces, after the last). By symmetry each gap has 48/5 cards on average.\n"
        "The first ace comes right after the first gap: 48/5 + 1.\n"
        "Answer: {answer}."
    ),
)
