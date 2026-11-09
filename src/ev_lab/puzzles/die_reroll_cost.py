from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.dist import fair_die
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.simtools import run_until

COST = Fraction(1, 4)


def threshold_value(threshold: int, cost: Fraction, sides: int = 6) -> Fraction:
    """Value of the policy 'stop at the first roll >= threshold'. The number of rolls is
    geometric with success probability p, so the expected number of paid re-rolls is 1/p - 1."""
    die = fair_die(sides)
    p_stop = die.prob(lambda face: face >= threshold)
    return die.condition(lambda face: face >= threshold).expect() - cost * (1 / p_stop - 1)


def best_threshold(cost: Fraction, sides: int = 6) -> tuple[int, Fraction]:
    return max(
        ((t, threshold_value(t, cost, sides)) for t in range(1, sides + 1)),
        key=lambda tv: tv[1],
    )


def solve() -> Fraction:
    return best_threshold(COST)[1]


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    threshold, _ = best_threshold(COST)
    rerolls, final = run_until(
        rng,
        rng.integers(1, 7, n),
        lambda face, r: r.integers(1, 7, face.size),
        lambda face: face >= threshold,
    )
    return final - float(COST) * rerolls


PUZZLE = Puzzle(
    id="die_reroll_cost",
    title="Die game where each re-roll costs money",
    statement=(
        "You roll a fair die and are paid the number showing in dollars. Before collecting "
        "you may re-roll as many times as you like, but each re-roll costs $0.25. With "
        "optimal play, what is the fair value of this game?"
    ),
    tags=("optimal stopping", "expected value"),
    difficulty=3,
    solve=solve,
    simulate=simulate,
    explanation=(
        "The situation looks the same before every roll, so the best rule is a fixed "
        "threshold: stop at the first roll of at least t.\n"
        "For a threshold t: value = (average of the faces >= t) - cost x (expected "
        "re-rolls), and the expected number of rolls is 6 / (number of faces >= t).\n"
        "Compare t = 1..6 and take the best. Check: re-roll a face f only if the value of "
        "the game minus the cost exceeds f.\n"
        "Answer: {answer}."
    ),
)
