"""Spaced repetition (SM-2): the update rule by hand, replaying a log, the schedule."""

from __future__ import annotations

import csv
from datetime import date, timedelta
from fractions import Fraction as F
from pathlib import Path

import pytest
import yaml
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError
from typer.testing import CliRunner

from ev_lab.cli import app
from ev_lab.config import Config
from ev_lab.puzzles import log as puzzle_log
from ev_lab.trainer.srs import (
    INITIAL_EF,
    MIN_EF,
    Card,
    due_text,
    load_schedule,
    quality,
    review,
    schedule_from_rows,
)

REPO = Path(__file__).resolve().parents[1]
runner = CliRunner()
D0 = date(2026, 11, 1)


def test_quality_from_an_attempt() -> None:
    assert quality(False, 5.0, 60, 180) == 1  # wrong, however fast
    assert quality(True, 60.0, 60, 180) == 5
    assert quality(True, 61.0, 60, 180) == 4
    assert quality(True, 180.0, 60, 180) == 4
    assert quality(True, 500.0, 60, 180) == 3


def test_perfect_answers_by_hand() -> None:
    # q = 5 adds exactly 0.1 to EF each time: 2.6, 2.7, 2.8
    a = review(None, 5, D0)
    assert (a.repetitions, a.ease, a.interval_days, a.due) == (1, F(26, 10), 1, D0 + timedelta(1))
    b = review(a, 5, a.due)
    assert (b.repetitions, b.ease, b.interval_days) == (2, F(27, 10), 6)
    c = review(b, 5, b.due)
    assert (c.repetitions, c.ease, c.interval_days) == (3, F(28, 10), 17)  # ceil(6 x 2.8 = 16.8)
    d = review(c, 5, c.due)
    assert d.interval_days == 50  # ceil(17 x 2.9 = 49.3)
    assert d.reviews == 4


def test_ease_change_per_grade_by_hand() -> None:
    # EF' - EF = 0.1 - (5 - q)(0.08 + (5 - q) 0.02): +0.10, 0.00, -0.14 for q = 5, 4, 3
    assert review(None, 5, D0).ease - INITIAL_EF == F(1, 10)
    assert review(None, 4, D0).ease - INITIAL_EF == 0
    assert review(None, 3, D0).ease - INITIAL_EF == F(-14, 100)


def test_a_failed_review_restarts_the_intervals_and_keeps_the_ease() -> None:
    card = review(review(review(None, 5, D0), 5, D0), 5, D0)
    failed = review(card, 1, D0 + timedelta(30))
    assert (failed.repetitions, failed.interval_days, failed.ease) == (0, 1, card.ease)
    assert failed.due == D0 + timedelta(31) and failed.reviews == 4
    again = review(failed, 5, failed.due)
    assert (again.repetitions, again.interval_days) == (1, 1)  # the sequence starts over
    assert review(again, 5, again.due).interval_days == 6


def test_ease_never_falls_below_the_minimum() -> None:
    card = None
    for _ in range(40):
        card = review(card, 3, D0)
    assert card is not None and card.ease == MIN_EF == F(13, 10)


def test_quality_range_is_checked() -> None:
    with pytest.raises(ValueError):
        review(None, 6, D0)


@given(st.lists(st.integers(0, 5), min_size=1, max_size=30))
def test_invariants_for_any_review_history(grades: list[int]) -> None:
    card = None
    for q in grades:
        previous = card
        card = review(card, q, D0)
        assert card.ease >= MIN_EF and card.interval_days >= 1
        assert isinstance(card.ease, F)
        if q < 3:
            assert card.repetitions == 0 and card.interval_days == 1
        elif previous is not None and previous.repetitions >= 2:
            assert card.interval_days >= previous.interval_days  # EF >= 1.3 > 1
    assert card is not None and card.reviews == len(grades)


def _row(day: str, puzzle: str, correct: int, seconds: float) -> dict[str, str]:
    return {
        "timestamp_utc": f"{day}T18:00:00+00:00",
        "run_id": "r",
        "puzzle_id": puzzle,
        "answer": "x",
        "correct": str(correct),
        "seconds": str(seconds),
    }


def test_schedule_is_a_replay_of_the_log() -> None:
    rows = [
        _row("2026-11-01", "monty_hall", 0, 30),  # wrong: due 2 Nov
        _row("2026-11-02", "monty_hall", 1, 30),  # right, fast: due 3 Nov
        _row("2026-11-02", "penney_game", 1, 400),  # right, slow (grade 3): due 3 Nov
        _row("2026-11-03", "monty_hall", 1, 100),  # right, medium (grade 4): due 9 Nov
    ]
    schedule = schedule_from_rows(rows, 60, 180)
    monty, penney = schedule["monty_hall"], schedule["penney_game"]
    assert (monty.repetitions, monty.interval_days, monty.due) == (2, 6, date(2026, 11, 9))
    assert monty.ease == F(26, 10) and monty.reviews == 3  # +0.1 for the 5, +0 for the 4
    assert (penney.interval_days, penney.ease) == (1, F(236, 100))
    assert due_text(monty, date(2026, 11, 9)) == "due today"
    assert due_text(monty, date(2026, 11, 12)) == "due 3 d ago"
    assert due_text(monty, date(2026, 11, 5)) == "due in 4 d"
    assert monty.days_overdue(date(2026, 11, 12)) == 3
    # a prefix of the log gives the earlier state: the schedule is a pure function of the log
    assert schedule_from_rows(rows[:1], 60, 180)["monty_hall"] == Card(0, INITIAL_EF, 1, D0, 1)


def test_no_log_means_an_empty_schedule(tmp_path: Path) -> None:
    assert load_schedule(tmp_path, 60, 180) == {}


def test_config_rejects_fast_not_below_slow() -> None:
    raw = yaml.safe_load((REPO / "config.yaml").read_text())
    raw["trainer"]["srs"] = {"fast_seconds": 200, "slow_seconds": 100}
    with pytest.raises(ValidationError, match="fast_seconds"):
        Config.model_validate(raw)


def test_quiz_and_list_follow_the_schedule(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every puzzle seen; one review overdue: `ev quiz` must pick it and reschedule it."""
    from ev_lab.puzzles.registry import all_puzzles

    raw = yaml.safe_load((REPO / "config.yaml").read_text())
    raw["monte_carlo"]["trials"] = 2000
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(raw))
    (tmp_path / "practice").mkdir()
    today = date.today()
    with (tmp_path / "practice" / puzzle_log.FILE_NAME).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(puzzle_log.HEADER))
        w.writeheader()
        for p in all_puzzles():
            day = today - timedelta(days=5 if p.id == "rolls_until_six" else 0)
            w.writerow(_row(day.isoformat(), p.id, 1, 30))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COLUMNS", "200")

    listed = runner.invoke(app, ["puzzle", "list", "--tag", "expected value", "--difficulty", "1"])
    assert "due 4 d ago" in listed.output  # first success: interval 1 day, 5 days ago

    result = runner.invoke(app, ["quiz"], input="6\n")
    assert result.exit_code == 0, result.output
    assert "Chosen: review, due 4 d ago" in result.output
    assert "expected number of rolls" in result.output and "Correct" in result.output
    assert "(in 6 d)" in result.output  # second success in a row: six days
    stats_out = runner.invoke(app, ["stats"]).output
    assert "0 review(s) due" in stats_out
