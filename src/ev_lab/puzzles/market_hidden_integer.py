from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.dist import Dist
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle

LOW, HIGH = 1, 100


def solve() -> Fraction:
    return Dist.uniform(range(LOW, HIGH + 1)).expect()


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    return rng.integers(LOW, HIGH + 1, n).astype(np.float64)


PUZZLE = Puzzle(
    id="market_hidden_integer",
    title="Make a market on a hidden integer",
    statement=(
        f"I have picked an integer uniformly at random from {LOW} to {HIGH} and the contract "
        "pays that many dollars. Make me a market: quote a bid and an ask at most 5 apart. "
        "Your quote is accepted if the fair value lies between your bid and your ask."
    ),
    tags=("expected value",),
    difficulty=1,
    solve=solve,
    simulate=simulate,
    explanation=(
        "With no information the fair value is the mean of the number: (low + high) / 2.\n"
        "Centre the quote there. The width is your protection: a counterparty who knows "
        "more than you trades only when your price is wrong (adverse selection), so a "
        "tighter quote earns less per trade and loses more to informed flow.\n"
        "Fair value: {answer}."
    ),
    practice_pending=True,
    kind="market",
    max_width=Fraction(5),
)
