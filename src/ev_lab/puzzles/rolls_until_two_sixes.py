from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.markov import AbsorbingChain
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.simtools import run_until


def solve() -> Fraction:
    six, other = Fraction(1, 6), Fraction(5, 6)
    chain = AbsorbingChain({0: {0: other, 1: six}, 1: {0: other, 2: six}})
    return chain.expected_steps(0)


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    steps, _ = run_until(
        rng,
        np.zeros(n, dtype=np.int64),
        lambda run, r: np.where(r.integers(1, 7, run.size) == 6, run + 1, 0),
        lambda run: run >= 2,
    )
    return steps.astype(np.float64)


PUZZLE = Puzzle(
    id="rolls_until_two_sixes",
    title="Rolls until two sixes in a row",
    statement="A fair die is rolled repeatedly. What is the expected number of rolls until "
    "two sixes in a row appear for the first time?",
    tags=("Markov chain", "expected value"),
    difficulty=2,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Two states: no progress (E0) and 'last roll was a six' (E1).\n"
        "E0 = 1 + (5/6) E0 + (1/6) E1,   E1 = 1 + (5/6) E0.\n"
        "General pattern for a run of two successes of probability p: 1/p + 1/p^2.\n"
        "Answer: {answer}."
    ),
)
