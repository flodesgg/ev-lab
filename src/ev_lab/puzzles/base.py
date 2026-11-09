"""The shape of a puzzle.

Every puzzle has an exact solver that *computes* its answer as a Fraction (no hard-coded
numbers) and a simulator that plays the experiment and is used as an independent check.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
from typing import Literal, get_args

from ev_lab.prob.montecarlo import Simulator

Tag = Literal[
    "conditional probability",
    "expected value",
    "Markov chain",
    "optimal stopping",
    "combinatorics",
    "geometric probability",
    "order statistics",
    "martingales",
]
TAGS: tuple[str, ...] = get_args(Tag)

Kind = Literal["number", "market"]


@dataclass(frozen=True)
class Puzzle:
    id: str
    title: str
    statement: str
    tags: tuple[Tag, ...]
    difficulty: Literal[1, 2, 3]
    solve: Callable[[], Fraction]
    simulate: Simulator
    # May contain "{answer}", filled in from solve() when shown. Shown only after an attempt.
    explanation: str
    # One of Nick's current practice problems: listed first, solution hidden until attempted.
    practice_pending: bool = False
    # "number": one numeric answer. "market": a bid and an ask around the fair value.
    kind: Kind = "number"
    max_width: Fraction | None = None

    def __post_init__(self) -> None:
        if not self.tags:
            raise ValueError(f"{self.id}: a puzzle needs at least one tag")
        if (self.kind == "market") != (self.max_width is not None):
            raise ValueError(f"{self.id}: max_width is required for, and only for, a market")


def format_answer(x: Fraction) -> str:
    """'7/2 (= 3.5)' style: the exact fraction first, then a decimal."""
    if x.denominator == 1:
        return str(x.numerator)
    return f"{x} (~ {float(x):.6g})"
