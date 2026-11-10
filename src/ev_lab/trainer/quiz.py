"""Probability quiz: which puzzle to ask next.

Order of priority:
  1. my practice problems that I have never tried;
  2. reviews that are due (spaced repetition, `trainer/srs.py`), the most overdue first;
  3. puzzles I have never seen;
  4. if nothing is due and nothing is new: the review that falls due soonest.
Ties are broken at random.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date

import numpy as np

from ev_lab.puzzles.base import Puzzle
from ev_lab.trainer.srs import Card, due_text


def _random(group: Sequence[Puzzle], rng: np.random.Generator) -> Puzzle:
    return group[int(rng.integers(0, len(group)))]


def pick_puzzle(
    puzzles: Sequence[Puzzle],
    schedule: Mapping[str, Card],
    today: date,
    rng: np.random.Generator,
) -> tuple[Puzzle, str]:
    """The next puzzle and a short reason for choosing it."""
    pending = [p for p in puzzles if p.practice_pending and p.id not in schedule]
    if pending:
        return _random(pending, rng), "practice problem, not tried yet"
    due = [p for p in puzzles if p.id in schedule and schedule[p.id].days_overdue(today) >= 0]
    if due:
        most = max(schedule[p.id].days_overdue(today) for p in due)
        chosen = _random([p for p in due if schedule[p.id].days_overdue(today) == most], rng)
        return chosen, f"review, {due_text(schedule[chosen.id], today)}"
    unseen = [p for p in puzzles if p.id not in schedule]
    if unseen:
        return _random(unseen, rng), "new puzzle"
    soonest = min(schedule[p.id].due for p in puzzles)
    chosen = _random([p for p in puzzles if schedule[p.id].due == soonest], rng)
    return chosen, f"nothing is due; earliest review, {due_text(schedule[chosen.id], today)}"
