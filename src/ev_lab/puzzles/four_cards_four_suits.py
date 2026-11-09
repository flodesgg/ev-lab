from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.simtools import as_float, shuffled_rows


def solve() -> Fraction:
    """Deal one card at a time: card i + 1 must avoid the i suits already seen."""
    p = Fraction(1)
    for seen in range(4):
        p *= Fraction(52 - 13 * seen, 52 - seen)
    return p


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    suits = np.sort(shuffled_rows(rng, n, np.arange(52) % 4)[:, :4], axis=1)
    return as_float((np.diff(suits, axis=1) != 0).all(axis=1))


PUZZLE = Puzzle(
    id="four_cards_four_suits",
    title="Four cards, four suits",
    statement="Four cards are dealt from a shuffled standard 52-card deck. What is the "
    "probability that they are of four different suits?",
    tags=("combinatorics",),
    difficulty=2,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Deal one card at a time. The first is free. The second must avoid the first "
        "card's suit: 39 of the 51 remaining. Then 26 of 50, then 13 of 49.\n"
        "Same answer by counting hands: 13^4 choices (one card per suit) out of C(52, 4).\n"
        "Answer: {answer}."
    ),
)
