from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.patterns import pattern_chain
from ev_lab.puzzles.simtools import run_until


def solve() -> Fraction:
    return pattern_chain(["HH"]).expected_steps("")


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    # state = current run of heads (0, 1 or 2)
    steps, _ = run_until(
        rng,
        np.zeros(n, dtype=np.int64),
        lambda run, r: np.where(r.random(run.size) < 0.5, run + 1, 0),
        lambda run: run >= 2,
    )
    return steps.astype(np.float64)


PUZZLE = Puzzle(
    id="tosses_until_hh",
    title="Tosses until two heads in a row",
    statement=(
        "A fair coin is tossed repeatedly. What is the expected number of tosses until two "
        "heads in a row appear for the first time?"
    ),
    tags=("Markov chain", "expected value"),
    difficulty=2,
    solve=solve,
    simulate=simulate,
    explanation=(
        "First-step analysis with two states: 'no progress' (E0) and 'one head' (E1).\n"
        "E0 = 1 + E0/2 + E1/2   (a tail wastes the toss, a head moves on)\n"
        "E1 = 1 + E0/2          (a tail sends you back, a head finishes)\n"
        "Solve the two equations. Answer: {answer}."
    ),
    practice_pending=True,
)
