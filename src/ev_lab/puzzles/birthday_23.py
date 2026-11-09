from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.simtools import as_float


def shared_birthday(people: int, days: int = 365) -> Fraction:
    all_different = Fraction(1)
    for i in range(people):
        all_different *= Fraction(days - i, days)
    return 1 - all_different


def solve() -> Fraction:
    return shared_birthday(23)


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    days = np.sort(rng.integers(0, 365, size=(n, 23)), axis=1)
    return as_float((np.diff(days, axis=1) == 0).any(axis=1))


PUZZLE = Puzzle(
    id="birthday_23",
    title="The birthday problem",
    statement="There are 23 people in a room. Assume 365 equally likely birthdays, "
    "independent between people. What is the probability that at least two share a birthday?",
    tags=("combinatorics",),
    difficulty=2,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Compute the complement: everyone different. Seat people one at a time: the i-th "
        "new person must avoid the i birthdays already taken, probability (365 - i)/365.\n"
        "Multiply these for i = 0..22 and subtract from 1. It is large because 23 people "
        "form 253 pairs.\n"
        "Answer: {answer}."
    ),
)
