from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.markov import AbsorbingChain
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.simtools import as_float, run_until

P_WIN = Fraction(2, 5)
START, TARGET = 3, 6


def ruin_chain(p: Fraction, target: int) -> AbsorbingChain[int]:
    return AbsorbingChain({k: {k + 1: p, k - 1: 1 - p} for k in range(1, target)})


def solve() -> Fraction:
    return ruin_chain(P_WIN, TARGET).absorption_probs(START)[TARGET]


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    _, final = run_until(
        rng,
        np.full(n, START, dtype=np.int64),
        lambda w, r: w + np.where(r.random(w.size) < float(P_WIN), 1, -1),
        lambda w: (w == 0) | (w == TARGET),
    )
    return as_float(final == TARGET)


PUZZLE = Puzzle(
    id="gamblers_ruin_biased",
    title="Gambler's ruin with an unfair coin",
    statement=(
        f"You start with ${START}. Each round you win $1 with probability {P_WIN} and lose "
        f"$1 otherwise. You stop when you reach ${TARGET} or $0. What is the probability "
        f"that you reach ${TARGET}?"
    ),
    tags=("Markov chain", "martingales"),
    difficulty=2,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Let h(k) be the chance of reaching the target from $k: h(k) = p h(k+1) + q h(k-1), "
        "h(0) = 0, h(target) = 1.\n"
        "Shortcut: with r = q/p, the process r^(wealth) is a martingale, which gives "
        "h(k) = (1 - r^k) / (1 - r^target).\n"
        "A small disadvantage per bet compounds into a large one. Answer: {answer}."
    ),
)
