from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle

CAP_TOSS = 10  # the bank can pay at most 2**10


def solve() -> Fraction:
    total = Fraction(0)
    p_reached = Fraction(0)
    for k in range(1, CAP_TOSS + 1):  # first head on toss k
        p = Fraction(1, 1 << k)
        total += p * (1 << k)
        p_reached += p
    return total + (1 - p_reached) * (1 << CAP_TOSS)  # later than the cap: the capped payout


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    first_head = rng.geometric(0.5, n)
    return 2.0 ** np.minimum(first_head, CAP_TOSS)


PUZZLE = Puzzle(
    id="st_petersburg_capped",
    title="St Petersburg game with a limited bank",
    statement=(
        "A fair coin is tossed until the first head. If the first head is on toss k you are "
        f"paid 2^k dollars, but the bank can pay at most 2^{CAP_TOSS} = {2**CAP_TOSS} dollars, "
        "so any larger payout is replaced by that amount. What is the fair value of this "
        "game?"
    ),
    tags=("expected value",),
    difficulty=2,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Each outcome k below the cap contributes (1/2^k) x 2^k = 1 dollar. There are 10 "
        "such terms. All later outcomes together have probability 1/2^10 and pay 2^10: "
        "one more dollar.\n"
        "Without the cap the sum never ends (infinite expectation): the 'paradox' rests on "
        "a bank with unlimited money.\n"
        "Answer: {answer}."
    ),
)
