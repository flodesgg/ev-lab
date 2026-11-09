from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.markov import AbsorbingChain
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.simtools import run_until

UP, DOWN = 3, 5


def solve() -> Fraction:
    half = Fraction(1, 2)
    chain = AbsorbingChain({k: {k + 1: half, k - 1: half} for k in range(-DOWN + 1, UP)})
    return chain.expected_steps(0)


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    steps, _ = run_until(
        rng,
        np.zeros(n, dtype=np.int64),
        lambda x, r: x + 2 * r.integers(0, 2, x.size) - 1,
        lambda x: (x == UP) | (x == -DOWN),
    )
    return steps.astype(np.float64)


PUZZLE = Puzzle(
    id="random_walk_duration",
    title="How long does a fair game last?",
    statement=(
        "You play a fair game, winning or losing $1 per round with probability 1/2 each. "
        f"You stop as soon as you are up ${UP} or down ${DOWN}. What is the expected number "
        "of rounds played?"
    ),
    tags=("martingales", "Markov chain"),
    difficulty=2,
    solve=solve,
    simulate=simulate,
    explanation=(
        "For a fair walk S, the process S^2 - (number of rounds) is a martingale, so "
        "E[rounds] = E[S^2 at the end].\n"
        "S itself is a martingale too, which gives P(end at +a) = b/(a + b). Then "
        "E[S^2] = a^2 b/(a+b) + b^2 a/(a+b) = a b.\n"
        "Answer: {answer}."
    ),
)
