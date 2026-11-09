from __future__ import annotations

from fractions import Fraction

import numpy as np

from ev_lab.prob.dist import Dist, joint
from ev_lab.prob.montecarlo import FloatArray
from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.simtools import as_float


def switch_win_probability(doors: int) -> Fraction:
    """One car. You pick a door; the host, who knows where the car is, opens one other door
    that hides a goat (uniformly among those he may open); you switch to a uniformly chosen
    door among the other closed ones."""
    all_doors = range(doors)

    def play(car_pick: tuple[int, ...]) -> Dist[bool]:
        car, pick = car_pick
        host = Dist.uniform(d for d in all_doors if d not in (car, pick))
        return host.bind(
            lambda opened: Dist.uniform(d for d in all_doors if d not in (pick, opened)).map(
                lambda final: final == car
            )
        )

    setup = joint(Dist.uniform(all_doors), Dist.uniform(all_doors))
    return setup.bind(play).prob(lambda win: win)


def simulate_switch(rng: np.random.Generator, n: int, doors: int) -> FloatArray:
    rows = np.arange(n)
    car = rng.integers(0, doors, n)
    pick = rng.integers(0, doors, n)
    # host: a uniformly random door among those that are neither the pick nor the car
    u = rng.random((n, doors))
    u[rows, car] = 2.0
    u[rows, pick] = 2.0
    opened = u.argmin(axis=1)
    # player: a uniformly random door among those that are neither the pick nor opened
    v = rng.random((n, doors))
    v[rows, pick] = 2.0
    v[rows, opened] = 2.0
    final = v.argmin(axis=1)
    return as_float(final == car)


def solve() -> Fraction:
    return switch_win_probability(3)


def simulate(rng: np.random.Generator, n: int) -> FloatArray:
    return simulate_switch(rng, n, 3)


PUZZLE = Puzzle(
    id="monty_hall",
    title="Monty Hall",
    statement=(
        "A car is behind one of three doors, goats behind the other two. You pick a door. "
        "The host, who knows where the car is, opens one of the other two doors to show a "
        "goat and offers you the remaining closed door. If you switch, what is the "
        "probability that you win the car?"
    ),
    tags=("conditional probability",),
    difficulty=1,
    solve=solve,
    simulate=simulate,
    explanation=(
        "Your first pick is right with probability 1/3, and the host's action cannot change "
        "that: he can always show a goat. Switching wins exactly when the first pick was "
        "wrong.\n"
        "The host's knowledge matters: if he opened a door at random and it happened to be "
        "a goat, the answer would be different.\n"
        "Answer: {answer}."
    ),
)
