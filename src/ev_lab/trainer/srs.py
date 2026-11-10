"""Spaced repetition for puzzles: Algorithm SM-2 (Wozniak, 1990).

A puzzle I solved comes back after a growing interval; one I got wrong comes back the next
day. Each puzzle carries an easiness factor EF (starts at 2.5). After a review graded
q = 0..5:

    q < 3   start again: next interval 1 day, EF unchanged
    q >= 3  EF' = EF + (0.1 - (5 - q) (0.08 + (5 - q) 0.02)), never below 1.3
            interval: 1 day after the first success, 6 days after the second,
            then previous interval x EF, rounded up

Source checked: docs/sources.md. The schedule is not stored anywhere: it is recomputed from
the append-only puzzle log every time, so it can never disagree with the history.

The grade comes from the attempt itself, not from self-assessment: wrong = 1; right = 5 if
fast, 4 if medium, 3 if slow (thresholds in config.yaml).
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from fractions import Fraction
from pathlib import Path

from ev_lab.practice_log import read_rows
from ev_lab.puzzles import log as puzzle_log

INITIAL_EF = Fraction(5, 2)
MIN_EF = Fraction(13, 10)


@dataclass(frozen=True)
class Card:
    """The review state of one puzzle."""

    repetitions: int  # successful reviews in a row
    ease: Fraction
    interval_days: int
    last_review: date
    reviews: int  # all reviews, including failed ones

    @property
    def due(self) -> date:
        return self.last_review + timedelta(days=self.interval_days)

    def days_overdue(self, today: date) -> int:
        """Positive when the review is late, 0 on the due day, negative before it."""
        return (today - self.due).days


def quality(correct: bool, seconds: float, fast_seconds: float, slow_seconds: float) -> int:
    if not correct:
        return 1
    if seconds <= fast_seconds:
        return 5
    return 4 if seconds <= slow_seconds else 3


def review(card: Card | None, q: int, day: date) -> Card:
    """The state after one review of grade q on `day` (card is None for a first attempt)."""
    if not 0 <= q <= 5:
        raise ValueError("quality must be between 0 and 5")
    repetitions = card.repetitions if card else 0
    ease = card.ease if card else INITIAL_EF
    reviews = (card.reviews if card else 0) + 1
    if q < 3:
        return Card(0, ease, 1, day, reviews)
    ease = max(
        MIN_EF, ease + Fraction(1, 10) - (5 - q) * (Fraction(2, 25) + (5 - q) * Fraction(1, 50))
    )
    if repetitions == 0:
        interval = 1
    elif repetitions == 1:
        interval = 6
    else:
        assert card is not None
        interval = math.ceil(card.interval_days * ease)
    return Card(repetitions + 1, ease, interval, day, reviews)


def schedule_from_rows(
    rows: Iterable[dict[str, str]], fast_seconds: float, slow_seconds: float
) -> dict[str, Card]:
    """Replay the puzzle log in order and return the current card of every puzzle seen."""
    cards: dict[str, Card] = {}
    for row in rows:
        day = datetime.fromisoformat(row["timestamp_utc"]).date()
        q = quality(row["correct"] == "1", float(row["seconds"]), fast_seconds, slow_seconds)
        cards[row["puzzle_id"]] = review(cards.get(row["puzzle_id"]), q, day)
    return cards


def load_schedule(practice_dir: Path, fast_seconds: float, slow_seconds: float) -> dict[str, Card]:
    rows = read_rows(practice_dir / puzzle_log.FILE_NAME, puzzle_log.HEADER)
    return schedule_from_rows(rows, fast_seconds, slow_seconds)


def due_text(card: Card, today: date) -> str:
    late = card.days_overdue(today)
    if late > 0:
        return f"due {late} d ago"
    return "due today" if late == 0 else f"due in {-late} d"
