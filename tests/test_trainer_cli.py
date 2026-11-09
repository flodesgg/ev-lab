"""Quiz selection, the trainer commands end to end, and practice statistics."""

from __future__ import annotations

import csv
from datetime import date
from fractions import Fraction as F
from pathlib import Path

import numpy as np
import pytest
import yaml
from typer.testing import CliRunner

from ev_lab.cli import app
from ev_lab.prob.montecarlo import rng_for
from ev_lab.puzzles.log import Attempts
from ev_lab.puzzles.registry import all_puzzles
from ev_lab.runinfo import RunInfo
from ev_lab.trainer import market_game, math_log, stats
from ev_lab.trainer.adaptive import pick_category
from ev_lab.trainer.market import QUANTITIES, MarketGame
from ev_lab.trainer.mental_math import CATEGORIES, generate
from ev_lab.trainer.quiz import pick_puzzle, priority

REPO = Path(__file__).resolve().parents[1]
runner = CliRunner()
SEED = 77


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    raw = yaml.safe_load((REPO / "config.yaml").read_text())
    raw["monte_carlo"]["trials"] = 2000
    raw["trainer"]["math"]["presets"]["tiny"] = {"questions": 3, "minutes": 1}
    raw["trainer"]["daily"]["math_preset"] = "tiny"
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(raw))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COLUMNS", "200")
    return tmp_path


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


# ---- quiz selection --------------------------------------------------------------------


def test_quiz_priority_order() -> None:
    puzzles = all_puzzles()
    pending = [p for p in puzzles if p.practice_pending]
    rng = np.random.default_rng(0)
    # nothing tried: a practice problem comes first
    assert pick_puzzle(puzzles, {}, rng).practice_pending
    # practice problems tried and solved: now something never seen
    done = {p.id: Attempts(1, True) for p in pending}
    nxt = pick_puzzle(puzzles, done, rng)
    assert nxt.id not in done
    # everything seen, one unsolved: that one
    seen = {p.id: Attempts(1, True) for p in puzzles}
    seen["penney_game"] = Attempts(3, False)
    assert pick_puzzle(puzzles, seen, rng).id == "penney_game"
    # everything solved: revision still returns a puzzle
    assert pick_puzzle(puzzles, {p.id: Attempts(1, True) for p in puzzles}, rng) in puzzles
    assert [priority(pending[0], {}), priority(nxt, {}), priority(nxt, seen)] == [0, 1, 3]


# ---- commands --------------------------------------------------------------------------


def _math_answers(count: int, level: int = 2) -> list[str]:
    """The right answers of the session `ev math --seed SEED` will ask (no history)."""
    rng = rng_for(SEED, "math")
    weights = dict.fromkeys(CATEGORIES, 2.0)
    out = []
    for _ in range(count):
        q = generate(rng, pick_category(rng, weights), level)
        out.append(str(q.answer))
    return out


def test_math_command_logs_every_answer(workdir: Path) -> None:
    answers = _math_answers(3)
    lines = ["", answers[0], "0", answers[2]]
    result = runner.invoke(
        app, ["math", "--preset", "tiny", "--seed", str(SEED)], input="\n".join(lines) + "\n"
    )
    assert result.exit_code == 0, result.output
    assert "3 questions in 1 minutes" in result.output
    assert "Correct: 2/3" in result.output
    rows = _rows(workdir / "practice" / math_log.FILE_NAME)
    assert list(rows[0]) == list(math_log.HEADER)
    assert [r["correct"] for r in rows] == ["1", "0", "1"]
    assert len({r["session_id"] for r in rows}) == 1
    assert all(r["level"] == "2" for r in rows)


def test_math_command_rejects_unknown_preset(workdir: Path) -> None:
    assert runner.invoke(app, ["math", "--preset", "nope"]).exit_code == 2


def _market_inputs(quantity: str | None = None) -> list[str]:
    """Quotes centred on the exact fair value for the game `--seed SEED` will deal."""
    rng = rng_for(SEED, "market")
    if quantity is None:
        quantity = list(QUANTITIES)[int(rng.integers(0, len(QUANTITIES)))]
    widths = [F(1, 5), F(3, 25), F(2, 25)]
    game = MarketGame(QUANTITIES[quantity], rng, F(1, 2), widths, 1)
    lines = []
    while not game.finished:
        fair = game.quantity.fair_value(game.known())
        half = game.max_width() / 2
        lines += [str(fair - half), str(fair + half)]
        game.play_round(fair - half, fair + half)
    return lines


def test_market_command_plays_and_logs(workdir: Path) -> None:
    lines = _market_inputs("sum3")
    result = runner.invoke(
        app, ["market", "--quantity", "sum3", "--seed", str(SEED)], input="\n".join(lines) + "\n"
    )
    assert result.exit_code == 0, result.output
    assert "Total P&L" in result.output and "EV of my quote" in result.output
    rows = _rows(workdir / "practice" / market_game.FILE_NAME)
    assert list(rows[0]) == list(market_game.HEADER) and len(rows) == 3
    for r in rows:  # the quotes were centred on fair value
        assert float(r["bid"]) <= float(r["fair_value"]) <= float(r["ask"])
    # same seed, same game
    again = runner.invoke(
        app, ["market", "--quantity", "sum3", "--seed", str(SEED)], input="\n".join(lines) + "\n"
    )
    rows2 = _rows(workdir / "practice" / market_game.FILE_NAME)[3:]
    assert again.exit_code == 0
    assert [(r["x"], r["trader"], r["side"]) for r in rows2] == [
        (r["x"], r["trader"], r["side"]) for r in rows
    ]


def test_market_command_abandoned_game_logs_nothing(workdir: Path) -> None:
    result = runner.invoke(app, ["market", "--quantity", "max2", "--seed", "1"], input="4\n5\n")
    assert result.exit_code == 0 and "nothing logged" in result.output
    assert not (workdir / "practice" / market_game.FILE_NAME).exists()
    assert runner.invoke(app, ["market", "--quantity", "nope"]).exit_code == 2


def test_daily_runs_all_three_parts_and_stats_reports_them(workdir: Path) -> None:
    puzzle = pick_puzzle(all_puzzles(), {}, rng_for(SEED, "quiz"))
    puzzle_lines = ["1", "2"] if puzzle.kind == "market" else ["1/7"]
    lines = ["", *_math_answers(3), *puzzle_lines, *_market_inputs()]
    result = runner.invoke(app, ["daily", "--seed", str(SEED)], input="\n".join(lines) + "\n")
    assert result.exit_code == 0, result.output
    out = result.output
    assert out.index("1/3") < out.index("2/3") < out.index("3/3") < out.index("Done for today")
    practice = workdir / "practice"
    assert len(_rows(practice / "math_log.csv")) == 3
    assert [r["puzzle_id"] for r in _rows(practice / "puzzle_log.csv")] == [puzzle.id]
    assert len(_rows(practice / "market_log.csv")) >= 2

    shown = runner.invoke(app, ["stats"])
    assert shown.exit_code == 0, shown.output
    assert "Streak: 1 day(s)" in shown.output and "Math answers: 3" in shown.output
    report = workdir / "reports" / "practice"
    summary = (report / stats.SUMMARY_NAME).read_text()
    assert summary.index("## Limitations") < summary.index("## As of")
    for name in (stats.ACCURACY_PNG, stats.SPEED_PNG):
        data = (report / name).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) > 5000


def test_stats_with_no_practice(workdir: Path) -> None:
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0 and "No practice logged yet" in result.output
    assert not (workdir / "reports" / "practice").exists()


# ---- statistics ------------------------------------------------------------------------


def test_streak() -> None:
    d = date(2026, 11, 9)
    days = {date(2026, 11, 9), date(2026, 11, 8), date(2026, 11, 7), date(2026, 11, 5)}
    assert stats.streak(days, d) == 3
    assert stats.streak(days - {d}, d) == 2  # today still open: yesterday's streak holds
    assert stats.streak({date(2026, 11, 5)}, d) == 0
    assert stats.streak(set(), d) == 0


def _write_history(practice: Path) -> None:
    """Three days of hand-made math answers, one puzzle attempt, one market round."""
    practice.mkdir()
    math = [
        # day, session, category, correct, seconds
        ("2026-11-03", "s1", "squares", 1, 4.0),
        ("2026-11-03", "s1", "squares", 0, 6.0),
        ("2026-11-03", "s1", "division", 0, 12.0),
        ("2026-11-04", "s2", "squares", 1, 3.0),
        ("2026-11-04", "s2", "division", 0, 10.0),
        ("2026-11-04", "s2", "division", 1, 8.0),
        ("2026-11-05", "s3", "mul_2x2", 0, 20.0),
        ("2026-11-05", "s3", "mul_2x2", 0, 30.0),
        ("2026-11-05", "s3", "squares", 1, 2.0),
    ]
    with (practice / math_log.FILE_NAME).open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(math_log.HEADER)
        for day, session, category, correct, seconds in math:
            w.writerow(
                [f"{day}T18:00:00+00:00", session, category, 2, "q", "a", "c", correct, seconds]
            )
    with (practice / "puzzle_log.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp_utc", "run_id", "puzzle_id", "answer", "correct", "seconds"])
        w.writerow(["2026-11-05T18:10:00+00:00", "r", "monty_hall", "1/2", 0, "30.0"])
        w.writerow(["2026-11-06T18:10:00+00:00", "r", "monty_hall", "2/3", 1, "20.0"])
    with (practice / market_game.FILE_NAME).open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(market_game.HEADER)
        w.writerow(
            [
                "2026-11-06T18:20:00+00:00",
                "g1",
                "max2",
                1,
                "",
                1,
                4,
                5,
                "4.472222",
                "0.1",
                "noise",
                "buy",
                6,
                -1,
            ]
        )
        w.writerow(
            [
                "2026-11-06T18:20:00+00:00",
                "g1",
                "max2",
                2,
                "6",
                1,
                4,
                5,
                "6",
                "-0.5",
                "informed",
                "buy",
                6,
                -1,
            ]
        )


def test_summary_numbers_by_hand(tmp_path: Path) -> None:
    _write_history(tmp_path / "practice")
    s = stats.summarise(
        tmp_path / "practice", date(2026, 11, 6), window=200, min_answers=2, puzzles_total=29
    )
    assert (s.streak, s.practice_days) == (4, 4)
    assert (s.math_answers, s.math_sessions) == (9, 3)
    by = {c.category: c for c in s.categories}
    assert (by["squares"].answers, by["squares"].accuracy, by["squares"].median_seconds) == (
        4,
        0.75,
        3.5,
    )
    assert (by["division"].answers, by["division"].median_seconds) == (3, 10.0)
    assert by["division"].accuracy == pytest.approx(1 / 3)
    # weakest: mul_2x2 (0%), then division (33%), then squares (75%)
    assert [c.category for c in s.weakest] == ["mul_2x2", "division", "squares"]
    assert (s.puzzles_tried, s.puzzles_solved, s.puzzle_attempts) == (1, 1, 2)
    assert (s.market_games, s.market_rounds, s.market_total_pnl) == (1, 2, -2.0)
    assert s.market_quotes_containing_fair == 1  # 4.47 is inside 4 @ 5; 6 is not

    # a category with too few answers in the window is not ranked
    ranked = stats.weakest_categories(
        stats.load_math(tmp_path / "practice"), window=200, min_answers=3
    )
    assert [c.category for c in ranked] == ["division", "squares"]
    # only the last answers count
    recent = stats.weakest_categories(
        stats.load_math(tmp_path / "practice"), window=3, min_answers=1
    )
    assert [c.category for c in recent] == ["mul_2x2", "squares"]


def test_daily_table_by_hand(tmp_path: Path) -> None:
    _write_history(tmp_path / "practice")
    table = stats.daily_table(stats.load_math(tmp_path / "practice"))
    row = table[(table["day"] == date(2026, 11, 3)) & (table["category"] == "squares")].iloc[0]
    assert (row["answers"], row["accuracy"], row["median_seconds"]) == (2, 0.5, 5.0)
    assert len(table) == 6


def test_summary_report_regression(tmp_path: Path) -> None:
    """Fixed logs must render exactly the stored summary."""
    _write_history(tmp_path / "practice")
    s = stats.summarise(
        tmp_path / "practice", date(2026, 11, 6), window=200, min_answers=2, puzzles_total=29
    )
    info = RunInfo(
        "20260101T000000Z-abcdef",
        "2026-01-01T00:00:00+00:00",
        "0123456789ab",
        False,
        "feedfacecafe",
        7,
    )
    text = stats.render_summary(s, info)
    assert text == (REPO / "tests" / "expected" / "practice_summary.md").read_text()
    written = stats.write_report(tmp_path / "out", s, stats.load_math(tmp_path / "practice"), info)
    assert [p.name for p in written] == [stats.SUMMARY_NAME, stats.ACCURACY_PNG, stats.SPEED_PNG]
    assert all(p.stat().st_size > 0 for p in written)
