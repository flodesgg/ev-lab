from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.monty_hall import simulate_switch, switch_win_probability


def solve() -> Fraction:
    return switch_win_probability(4)


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    return simulate_switch(rng, n, 4)


PUZZLE = Puzzle(
    id="monty_hall_four_doors",
    title="Monty Hall with four doors",
    statement=(
        "A car is behind one of four doors, goats behind the other three. You pick a door. "
        "The host, who knows where the car is, opens one of the other three doors to show a "
        "goat. You then switch to one of the two other closed doors, chosen at random. "
        "What is the probability that you win the car?"
    ),
    tags=("conditional probability",),
    difficulty=2,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Your first pick keeps its 1/4. The remaining 3/4 is now spread over the two other "
        "closed doors, equally by symmetry.\n"
        "So switching wins with (3/4) x (1/2), which beats staying (1/4).\n"
        "Answer: {answer}."
    ),
)
