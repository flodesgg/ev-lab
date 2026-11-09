from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.geometry import UNIT_SQUARE, area, clip
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle

WAIT = Fraction(15, 60)  # as a fraction of the hour


def solve() -> Fraction:
    region = clip(UNIT_SQUARE, 1, -1, WAIT)  # x - y <= wait
    region = clip(region, -1, 1, WAIT)  # y - x <= wait
    return area(region)


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    arrivals = rng.random((n, 2))
    return (np.abs(arrivals[:, 0] - arrivals[:, 1]) < float(WAIT)).astype(np.float64)


PUZZLE = Puzzle(
    id="meeting_window",
    title="Two friends meeting",
    statement=(
        "Two friends agree to meet between 12:00 and 13:00. Each arrives at an independent, "
        "uniformly random time in that hour, waits 15 minutes and then leaves. What is the "
        "probability that they meet?"
    ),
    tags=("geometric probability",),
    difficulty=2,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Plot the two arrival times as a point in the unit square. They meet when the "
        "point is within 1/4 of the diagonal: |x - y| < 1/4.\n"
        "The complement is two corner triangles with legs 3/4; together they form a square "
        "of side 3/4. So the probability is 1 - (3/4)^2.\n"
        "Answer: {answer}."
    ),
)
