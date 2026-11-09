"""Small helpers for vectorised simulators (many trials advanced together with numpy)."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]


def run_until(
    rng: np.random.Generator,
    start: IntArray,
    step: Callable[[IntArray, np.random.Generator], IntArray],
    done: Callable[[IntArray], BoolArray],
    max_steps: int = 1_000_000,
) -> tuple[IntArray, IntArray]:
    """Advance every trial one step at a time until it is done.

    `start` holds one integer state per trial. `step` maps the states of the still-running
    trials to their next states. Returns (number of steps taken, final state) per trial."""
    state = start.astype(np.int64).copy()
    steps = np.zeros_like(state)
    active = ~done(state)
    for _ in range(max_steps):
        idx = np.flatnonzero(active)
        if idx.size == 0:
            return steps, state
        state[idx] = step(state[idx], rng)
        steps[idx] += 1
        active[idx] = ~done(state[idx])
    raise RuntimeError("simulation did not finish")


def shuffled_rows(rng: np.random.Generator, n: int, deck: NDArray[np.int64]) -> IntArray:
    """n independent uniform shuffles of `deck`, one per row."""
    return rng.permuted(np.tile(deck, (n, 1)), axis=1)


def as_float(values: NDArray[np.generic]) -> NDArray[np.float64]:
    """One float per trial (booleans become 0.0 / 1.0)."""
    return np.asarray(values, dtype=np.float64)
