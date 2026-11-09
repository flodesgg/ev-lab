"""Probability quiz: which puzzle to ask next.

Order of priority: my practice problems that I have not tried, then puzzles I have never
seen, then puzzles I tried but never got right, then solved ones (as revision). Within the
first non-empty group the choice is random.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

from ev_lab.puzzles.base import Puzzle
from ev_lab.puzzles.log import Attempts


def priority(puzzle: Puzzle, attempts: Mapping[str, Attempts]) -> int:
    a = attempts.get(puzzle.id)
    if a is None:
        return 0 if puzzle.practice_pending else 1
    return 3 if a.solved else 2


def pick_puzzle(
    puzzles: Sequence[Puzzle], attempts: Mapping[str, Attempts], rng: np.random.Generator
) -> Puzzle:
    best = min(priority(p, attempts) for p in puzzles)
    group = [p for p in puzzles if priority(p, attempts) == best]
    return group[int(rng.integers(0, len(group)))]
