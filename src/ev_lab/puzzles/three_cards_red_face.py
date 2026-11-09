from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.dist import Dist
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.simtools import as_float

CARDS = ("RR", "RB", "BB")


def solve() -> Fraction:
    # outcome = (face up, face down): each card and each side equally likely
    faces = Dist.uniform((card[side], card[1 - side]) for card in CARDS for side in (0, 1))
    return faces.condition(lambda f: f[0] == "R").prob(lambda f: f[1] == "R")


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    red = np.array([[True, True], [True, False], [False, False]])  # is each side red?
    card = rng.integers(0, 3, n)
    side = rng.integers(0, 2, n)
    up, down = red[card, side], red[card, 1 - side]
    return as_float(down[up])


PUZZLE = Puzzle(
    id="three_cards_red_face",
    title="Three cards, one red face showing",
    statement=(
        "There are three cards: one is red on both sides, one is black on both sides, and "
        "one is red on one side and black on the other. A card is drawn at random and "
        "placed on the table with a random side up. The side you see is red. What is the "
        "probability that the other side is also red?"
    ),
    tags=("conditional probability",),
    difficulty=1,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Count faces, not cards. There are three red faces, each equally likely to be the "
        "one you see. Two of them belong to the red-red card.\n"
        "The intuitive '1/2' forgets that the red-red card shows red twice as often as the "
        "mixed card.\n"
        "Answer: {answer}."
    ),
)
