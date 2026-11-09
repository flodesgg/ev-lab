from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.dist import Dist
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.simtools import as_float

COINS, HEADS = 100, 5


def solve() -> Fraction:
    coin = Dist.from_weights({"fair": COINS - 1, "two-headed": 1})

    def all_heads(kind: str) -> Dist[tuple[str, bool]]:
        p = Fraction(1) if kind == "two-headed" else Fraction(1, 2) ** HEADS
        return Dist({(kind, True): p, (kind, False): 1 - p})

    seen = coin.bind(all_heads).condition(lambda outcome: outcome[1])
    return seen.prob(lambda outcome: outcome[0] == "two-headed")


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    two_headed = rng.integers(0, COINS, n) == 0
    flips = rng.integers(0, 2, size=(n, HEADS)) == 1
    all_heads = two_headed | flips.all(axis=1)
    return as_float(two_headed[all_heads])


PUZZLE = Puzzle(
    id="two_headed_coin",
    title="Is it the two-headed coin?",
    statement=(
        f"A bag holds {COINS} coins: {COINS - 1} are fair and one has heads on both sides. "
        f"You draw a coin at random and toss it {HEADS} times: all {HEADS} are heads. What "
        "is the probability that you are holding the two-headed coin?"
    ),
    tags=("conditional probability",),
    difficulty=2,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Bayes with odds. Prior odds two-headed : fair are 1 : 99. The evidence is 2^5 = 32 "
        "times more likely under the two-headed coin (1 against 1/32).\n"
        "Posterior odds = prior odds x likelihood ratio = 32 : 99, so the probability is "
        "32 / (32 + 99). Strong evidence, but the prior was weak.\n"
        "Answer: {answer}."
    ),
)
