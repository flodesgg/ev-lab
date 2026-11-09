from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.dist import fair_die
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.prob.stopping import StoppingSolution
from ev_lab.puzzles.base import Puzzle


def game(rolls: int, sides: int = 6) -> StoppingSolution[int]:
    """State = the face showing. Stop: collect the face. Continue: roll again."""
    die = fair_die(sides)
    return StoppingSolution(rolls - 1, lambda _t, face: face, lambda _t, _face: die)


def value(rolls: int, sides: int = 6) -> Fraction:
    g = game(rolls, sides)
    return fair_die(sides).expect(lambda face: g.value(0, face))


def solve() -> Fraction:
    return value(rolls=2)


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    g = game(2)
    keep = np.array([False] + [g.should_stop(0, face) for face in range(1, 7)])
    first = rng.integers(1, 7, n)
    second = rng.integers(1, 7, n)
    return np.where(keep[first], first, second).astype(np.float64)


PUZZLE = Puzzle(
    id="die_one_reroll",
    title="Die game with one optional re-roll",
    statement=(
        "You roll a fair six-sided die. You may keep the result, or re-roll once and keep "
        "the second result. You are paid the kept number in dollars. With optimal play, "
        "what is the fair value of this game?"
    ),
    tags=("optimal stopping", "expected value"),
    difficulty=1,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Work backwards. A re-roll is worth the mean of one die. So keep the first roll "
        "exactly when it beats that mean, otherwise re-roll.\n"
        "Value = sum over kept faces of face/6, plus P(re-roll) times the mean of a die.\n"
        "Answer: {answer}."
    ),
    practice_pending=True,
)
