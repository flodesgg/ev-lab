from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.markov import AbsorbingChain
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.simtools import run_until


def expected_rolls(sides: int) -> Fraction:
    """State = number of distinct faces seen so far."""
    chain = AbsorbingChain(
        {k: {k: Fraction(k, sides), k + 1: Fraction(sides - k, sides)} for k in range(sides)}
    )
    return chain.expected_steps(0)


def solve() -> Fraction:
    return expected_rolls(6)


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    # state = bitmask of the faces seen; done when all six bits are set
    steps, _ = run_until(
        rng,
        np.zeros(n, dtype=np.int64),
        lambda seen, r: seen | (1 << r.integers(0, 6, seen.size)),
        lambda seen: seen == 0b111111,
    )
    return steps.astype(np.float64)


PUZZLE = Puzzle(
    id="coupon_collector_die",
    title="Rolls until every face has appeared",
    statement="A fair die is rolled repeatedly. What is the expected number of rolls until "
    "every one of the six faces has appeared at least once?",
    tags=("expected value", "Markov chain"),
    difficulty=2,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Split the wait into stages. With k faces already seen, a roll shows a new face "
        "with probability (6 - k)/6, so that stage takes 6/(6 - k) rolls on average.\n"
        "By linearity of expectation add the stages: 6/6 + 6/5 + 6/4 + 6/3 + 6/2 + 6/1.\n"
        "Answer: {answer}."
    ),
)
