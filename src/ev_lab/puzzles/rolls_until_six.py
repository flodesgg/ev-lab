from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.markov import AbsorbingChain
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle


def solve() -> Fraction:
    chain = AbsorbingChain({"rolling": {"rolling": Fraction(5, 6), "six": Fraction(1, 6)}})
    return chain.expected_steps("rolling")


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    return rng.geometric(1 / 6, n).astype(np.float64)


PUZZLE = Puzzle(
    id="rolls_until_six",
    title="Rolls until the first six",
    statement="A fair die is rolled repeatedly. What is the expected number of rolls until "
    "the first six (counting the roll that shows the six)?",
    tags=("expected value", "Markov chain"),
    difficulty=1,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Let E be the answer. One roll is always spent; with probability 5/6 you are back "
        "where you started: E = 1 + (5/6)E.\n"
        "In general, waiting for an event of probability p takes 1/p tries on average.\n"
        "Answer: {answer}."
    ),
)
