from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle

ROPES = 10


def expected_loops(ropes: int) -> Fraction:
    """With k strands left there are 2k free ends. Take one end; of the 2k - 1 other ends
    exactly one belongs to the same strand and closes a loop. Either way k drops by one."""
    total = Fraction(0)
    for k in range(ropes, 0, -1):
        total += Fraction(1, 2 * k - 1)
    return total


def solve() -> Fraction:
    return expected_loops(ROPES)


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    loops = np.zeros(n)
    for k in range(ROPES, 0, -1):
        # the second end is uniform among the 2k - 1 others; index 0 = same strand
        loops += rng.integers(0, 2 * k - 1, n) == 0
    return loops


PUZZLE = Puzzle(
    id="rope_loops",
    title="Tying ropes into loops",
    statement=(
        f"A bowl holds {ROPES} ropes, so {2 * ROPES} loose ends. You repeatedly pick two "
        "loose ends at random and tie them together, until no loose ends remain. What is "
        "the expected number of closed loops?"
    ),
    tags=("expected value", "combinatorics"),
    difficulty=3,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Each tie reduces the number of strands by one, so there are exactly 10 ties. "
        "With k strands left, the tie closes a loop with probability 1/(2k - 1): the "
        "second end must be the other end of the same strand.\n"
        "By linearity, E[loops] = 1/19 + 1/17 + ... + 1/3 + 1/1.\n"
        "Answer: {answer}."
    ),
)
