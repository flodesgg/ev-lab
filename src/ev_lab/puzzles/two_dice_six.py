from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.dist import fair_die, joint
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.simtools import as_float


def solve() -> Fraction:
    rolls = joint(fair_die(), fair_die())
    given = rolls.condition(lambda r: 6 in r)
    return given.prob(lambda r: r == (6, 6))


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    rolls = rng.integers(1, 7, size=(n, 2))
    told = (rolls == 6).any(axis=1)  # keep only the trials where the condition holds
    return as_float((rolls[told] == 6).all(axis=1))


PUZZLE = Puzzle(
    id="two_dice_six",
    title="Two dice, at least one six",
    statement=(
        "Two fair dice are rolled. You are told that at least one of them shows a six. "
        "What is the probability that both show a six?"
    ),
    tags=("conditional probability",),
    difficulty=1,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Condition by counting. Of the 36 equally likely ordered rolls, list those with at "
        "least one six; that list is the new sample space. Only one of them is (6, 6).\n"
        "The trap is to treat it as 'the other die': nobody said which die shows the six, "
        "so the conditioning event is larger than 'the first die is a six'.\n"
        "Answer: {answer}."
    ),
    practice_pending=True,
)
