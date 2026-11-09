from __future__ import annotations

from fractions import Fraction
from functools import cache

import numpy as np

from ev_lab.prob.dist import Dist
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.prob.stopping import StoppingSolution
from ev_lab.puzzles.base import Puzzle

REDS = BLACKS = 26


@cache
def game(reds: int, blacks: int) -> StoppingSolution[tuple[int, int]]:
    """State = (reds left, blacks left). Stopping collects the winnings so far."""

    def winnings(_t: int, left: tuple[int, int]) -> int:
        return (reds - left[0]) - (blacks - left[1])

    def draw(_t: int, left: tuple[int, int]) -> Dist[tuple[int, int]]:
        r, b = left
        return Dist.from_weights({(r - 1, b): r, (r, b - 1): b})

    return StoppingSolution(reds + blacks, winnings, draw)


def value(reds: int, blacks: int) -> Fraction:
    return game(reds, blacks).value(0, (reds, blacks))


def solve() -> Fraction:
    return value(REDS, BLACKS)


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    g = game(REDS, BLACKS)
    stop = np.array(
        [
            [g.should_stop(REDS + BLACKS - r - b, (r, b)) for b in range(BLACKS + 1)]
            for r in range(REDS + 1)
        ]
    )
    r = np.full(n, REDS, dtype=np.int64)
    b = np.full(n, BLACKS, dtype=np.int64)
    active = ~stop[r, b]
    while active.any():
        idx = np.flatnonzero(active)
        red = rng.random(idx.size) * (r[idx] + b[idx]) < r[idx]
        r[idx] -= red
        b[idx] -= ~red
        active[idx] = ~stop[r[idx], b[idx]]
    return ((REDS - r) - (BLACKS - b)).astype(np.float64)


PUZZLE = Puzzle(
    id="red_black_stopping",
    title="Red and black cards: when to stop",
    statement=(
        "A shuffled deck has 26 red and 26 black cards. Cards are turned over one at a "
        "time: you win $1 for each red card and lose $1 for each black card. You may stop "
        "at any time. With optimal play, what is the fair value of this game?"
    ),
    tags=("optimal stopping",),
    difficulty=3,
    solve=solve,
    simulate=simulate,
    explanation=(
        "The value is positive because you hold an option: playing to the end gives "
        "exactly 0, so you can never do worse than 0 from any point.\n"
        "Let V(r, b) be the expected future gain with r reds and b blacks left: "
        "V = max(0, [r (1 + V(r-1, b)) + b (-1 + V(r, b-1))] / (r + b)), V(0, b) = 0, "
        "V(r, 0) = r.\n"
        "Fill the table from small decks upwards (backward induction). Answer: {answer}."
    ),
)
