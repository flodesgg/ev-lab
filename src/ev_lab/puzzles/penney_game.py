from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.patterns import pattern_chain
from ev_lab.puzzles.simtools import IntArray, as_float, run_until

YOURS, THEIRS = "THH", "HHT"


def solve() -> Fraction:
    return pattern_chain([YOURS, THEIRS]).absorption_probs("")[YOURS]


def _code(pattern: str) -> int:
    """Last three tosses as bits (H = 1), with a marker bit meaning 'three tosses seen'."""
    return 0b1000 | int(pattern.replace("H", "1").replace("T", "0"), 2)


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    yours, theirs = _code(YOURS), _code(THEIRS)

    def toss(state: IntArray, r: np.random.Generator) -> IntArray:
        nxt = (state << 1) | r.integers(0, 2, state.size)
        return np.where(nxt >= 0b10000, (nxt & 0b111) | 0b1000, nxt)

    _, final = run_until(
        rng, np.ones(n, dtype=np.int64), toss, lambda s: (s == yours) | (s == theirs)
    )
    return as_float(final == yours)


PUZZLE = Puzzle(
    id="penney_game",
    title="Penney's game: THH against HHT",
    statement=(
        "A fair coin is tossed repeatedly. You win if the pattern THH appears before the "
        "pattern HHT; your opponent wins if HHT appears first. What is the probability "
        "that you win?"
    ),
    tags=("Markov chain", "conditional probability"),
    difficulty=3,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Both patterns are equally likely in any three given tosses, yet the race is not "
        "fair. HHT can only win if the game starts HH: after HH, the first tail completes "
        "HHT. Once any tail has appeared before HH, every later HH is preceded by a T, "
        "so THH is completed first.\n"
        "So the opponent wins exactly when the first two tosses are both heads.\n"
        "Answer: {answer}."
    ),
)
