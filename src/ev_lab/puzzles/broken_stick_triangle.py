from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.geometry import UNIT_SQUARE, area, clip
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle

HALF = Fraction(1, 2)


def solve() -> Fraction:
    """Break points (x, y) are uniform in the unit square. A triangle needs every piece to
    be shorter than half the stick. Two convex regions: x < y and y < x."""
    # x < y: pieces are x, y - x, 1 - y
    lower = clip(UNIT_SQUARE, 1, -1, 0)  # x <= y
    lower = clip(lower, 1, 0, HALF)  # x <= 1/2
    lower = clip(lower, -1, 1, HALF)  # y - x <= 1/2
    lower = clip(lower, 0, -1, -HALF)  # 1 - y <= 1/2
    # y < x: pieces are y, x - y, 1 - x
    upper = clip(UNIT_SQUARE, -1, 1, 0)
    upper = clip(upper, 0, 1, HALF)
    upper = clip(upper, 1, -1, HALF)
    upper = clip(upper, -1, 0, -HALF)
    return area(lower) + area(upper)


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    cuts = np.sort(rng.random((n, 2)), axis=1)
    pieces = np.column_stack([cuts[:, 0], cuts[:, 1] - cuts[:, 0], 1 - cuts[:, 1]])
    return (pieces.max(axis=1) < 0.5).astype(np.float64)


PUZZLE = Puzzle(
    id="broken_stick_triangle",
    title="Broken stick forming a triangle",
    statement="A stick is broken at two points chosen independently and uniformly along "
    "its length. What is the probability that the three pieces can form a triangle?",
    tags=("geometric probability",),
    difficulty=2,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Three lengths form a triangle exactly when the longest is shorter than the sum of "
        "the other two, i.e. every piece is shorter than half the stick.\n"
        "Draw the two break points as a point (x, y) in the unit square. The three "
        "conditions cut out two small triangles; probability = their total area.\n"
        "Answer: {answer}."
    ),
)
