"""`ev puzzle` commands, the practice log, grading, and the check-all report."""

from __future__ import annotations

import csv
from fractions import Fraction as F
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from ev_lab.cli import app
from ev_lab.practice_log import LogHeaderError, append_row, read_rows
from ev_lab.prob.montecarlo import McResult
from ev_lab.puzzles.grading import market_is_correct, number_is_correct, parse_number
from ev_lab.puzzles.log import HEADER, attempts_by_puzzle
from ev_lab.puzzles.registry import all_puzzles, get_puzzle
from ev_lab.reports import puzzle_bias, puzzle_check
from ev_lab.runinfo import RunInfo

REPO = Path(__file__).resolve().parents[1]
runner = CliRunner()


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A scratch project folder with the real config, but fewer Monte Carlo trials."""
    raw = yaml.safe_load((REPO / "config.yaml").read_text())
    raw["monte_carlo"]["trials"] = 4000
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(raw))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COLUMNS", "200")
    return tmp_path


def _log_rows(workdir: Path) -> list[dict[str, str]]:
    with (workdir / "practice" / "puzzle_log.csv").open(newline="") as f:
        return list(csv.DictReader(f))


# ---- grading ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("7/2", F(7, 2)),
        (" 3.5 ", F(7, 2)),
        ("35%", F(35, 100)),
        ("1,000", F(1000)),
        ("$4.25", F(17, 4)),
        ("-1/3", F(-1, 3)),
        ("6", F(6)),
    ],
)
def test_parse_number(text: str, value: F) -> None:
    parsed = parse_number(text)
    assert parsed == value and isinstance(parsed, F)


@pytest.mark.parametrize("text", ["", "abc", "1/0", "1/2/3", "half"])
def test_parse_number_rejects_garbage(text: str) -> None:
    with pytest.raises(ValueError, match="not a number"):
        parse_number(text)


def test_number_tolerance_is_relative() -> None:
    exact = F(200)
    assert number_is_correct(F(200), exact, 0.005)
    assert number_is_correct(F(201), exact, 0.005)  # exactly 0.5% away
    assert not number_is_correct(F(2011, 10), exact, 0.005)
    assert number_is_correct(F(1, 1000), F(0), 0.005)  # absolute when the answer is 0
    assert not number_is_correct(F(1, 100), F(0), 0.005)


def test_market_grading() -> None:
    fair, width = F(21, 2), F(2)
    assert market_is_correct(F(10), F(11), fair, width)
    assert market_is_correct(F(21, 2), F(12), fair, width)  # fair value on the edge counts
    assert not market_is_correct(F(11), F(12), fair, width)  # fair below the bid
    assert not market_is_correct(F(8), F(10), fair, width)  # fair above the ask
    assert not market_is_correct(F(9), F(12), fair, width)  # too wide
    assert not market_is_correct(F(11), F(10), fair, width)  # crossed
    assert not market_is_correct(F(10), F(10), fair, width)  # not two-sided


# ---- append-only log -------------------------------------------------------------------


def test_log_is_append_only_with_a_checked_header(tmp_path: Path) -> None:
    path = tmp_path / "log.csv"
    append_row(path, ("a", "b"), {"a": 1, "b": "x"})
    before = path.read_text()
    append_row(path, ("a", "b"), {"a": 2, "b": "y"})
    after = path.read_text()
    assert after.startswith(before)  # earlier rows untouched
    assert after.splitlines() == ["a,b", "1,x", "2,y"]
    assert read_rows(path, ("a", "b")) == [{"a": "1", "b": "x"}, {"a": "2", "b": "y"}]
    with pytest.raises(LogHeaderError):
        append_row(path, ("a", "c"), {"a": 3, "c": "z"})
    with pytest.raises(LogHeaderError):
        read_rows(path, ("a", "c"))
    with pytest.raises(ValueError, match="do not match header"):
        append_row(path, ("a", "b"), {"a": 3})
    assert path.read_text() == after  # failed writes changed nothing


def test_missing_log_reads_as_empty(tmp_path: Path) -> None:
    assert read_rows(tmp_path / "none.csv", ("a",)) == []
    assert attempts_by_puzzle(tmp_path) == {}


# ---- ev puzzle try ---------------------------------------------------------------------


def test_try_asks_first_then_reveals_and_logs(workdir: Path) -> None:
    result = runner.invoke(app, ["puzzle", "try", "rolls_until_six"], input="1/7\n")
    assert result.exit_code == 0, result.output
    out = result.output
    assert out.index("expected number of rolls") < out.index("Your answer")
    assert out.index("Your answer") < out.index("Not correct") < out.index("Explanation")
    assert "Monte Carlo" in out and "Exact:" in out
    rows = _log_rows(workdir)
    assert list(rows[0]) == list(HEADER)
    assert rows[0]["puzzle_id"] == "rolls_until_six"
    assert rows[0]["answer"] == "1/7" and rows[0]["correct"] == "0"


def test_try_accepts_decimal_within_tolerance_and_reprompts_on_garbage(workdir: Path) -> None:
    result = runner.invoke(app, ["puzzle", "try", "coupon_collector_die"], input="abc\n14.7\n")
    assert result.exit_code == 0, result.output
    assert "not a number" in result.output
    assert "Correct" in result.output and "Not correct" not in result.output
    assert [r["correct"] for r in _log_rows(workdir)] == ["1"]
    assert attempts_by_puzzle(workdir / "practice")["coupon_collector_die"].solved


def test_try_never_shows_the_solution_without_an_answer(workdir: Path) -> None:
    result = runner.invoke(app, ["puzzle", "try", "monty_hall"], input="")
    assert result.exit_code != 0  # no answer given: aborted
    assert "Explanation" not in result.output and "Exact" not in result.output
    assert not (workdir / "practice" / "puzzle_log.csv").exists()


def test_try_market_puzzle(workdir: Path) -> None:
    puzzle = get_puzzle("market_hidden_integer")
    fair = puzzle.solve()
    good = f"{float(fair - 1)}\n{float(fair + 1)}\n"
    assert "Correct" in runner.invoke(app, ["puzzle", "try", puzzle.id], input=good).output
    wide = runner.invoke(app, ["puzzle", "try", puzzle.id], input="1\n100\n").output
    assert "Not correct" in wide and "wider than" in wide
    off = runner.invoke(app, ["puzzle", "try", puzzle.id], input="1\n2\n").output
    assert "Not correct" in off and "above your ask" in off
    rows = _log_rows(workdir)
    assert [r["correct"] for r in rows] == ["1", "0", "0"]
    assert rows[1]["answer"] == "1 @ 100"


def test_try_unknown_puzzle(workdir: Path) -> None:
    result = runner.invoke(app, ["puzzle", "try", "nope"])
    assert result.exit_code == 2 and "unknown puzzle" in result.output


# ---- ev puzzle list --------------------------------------------------------------------


def test_list_filters_and_status(workdir: Path) -> None:
    everything = runner.invoke(app, ["puzzle", "list"])
    assert everything.exit_code == 0
    assert f"{len(all_puzzles())} of {len(all_puzzles())} puzzles" in everything.output
    assert "practice: to do" in everything.output

    markov = runner.invoke(app, ["puzzle", "list", "--tag", "markov", "--difficulty", "2"])
    assert "tosses_until_hh" in markov.output and "monty_hall" not in markov.output

    runner.invoke(app, ["puzzle", "try", "rolls_until_six"], input="6\n")
    assert "solved (1 tries)" in runner.invoke(app, ["puzzle", "list"]).output

    bad = runner.invoke(app, ["puzzle", "list", "--tag", "astrology"])
    assert bad.exit_code == 2


# ---- ev puzzle check-all and its report ------------------------------------------------


def test_check_all_writes_a_report_without_spoilers(workdir: Path) -> None:
    runner.invoke(app, ["puzzle", "try", "rolls_until_six"], input="6\n")
    result = runner.invoke(app, ["puzzle", "check-all"])
    assert result.exit_code == 0, result.output
    assert f"{len(all_puzzles())} puzzles" in result.output
    report = (workdir / "reports" / "puzzles" / "check_all.md").read_text()
    assert report.index("## Limitations") < report.index("## Result")
    rows = [line for line in report.splitlines() if line.startswith("| `")]
    assert len(rows) == len(all_puzzles())
    for line in rows:
        attempted = line.startswith("| `rolls_until_six`")
        assert (puzzle_check.HIDDEN in line) != attempted
    assert "seed 20261109" in report and "config " in report and "commit " in report


def _fake_info() -> RunInfo:
    return RunInfo(
        run_id="20260101T000000Z-abcdef",
        started_utc="2026-01-01T00:00:00+00:00",
        git_commit="0123456789ab",
        git_dirty=False,
        config_hash="feedfacecafe",
        seed=7,
    )


def test_report_regression_against_stored_output() -> None:
    """Fixed inputs must render exactly the stored file. To accept an intended change,
    regenerate tests/expected/check_all.md and review the diff."""
    rows = [
        puzzle_check.CheckRow(
            get_puzzle("rolls_until_six"), F(6), McResult(6.01, 0.0122, 200_000), attempted=True
        ),
        puzzle_check.CheckRow(
            get_puzzle("monty_hall"), F(2, 3), McResult(0.6661, 0.00105, 200_000), attempted=False
        ),
        puzzle_check.CheckRow(
            get_puzzle("birthday_23"), F(1, 2), McResult(0.5073, 0.0011, 200_000), attempted=True
        ),
    ]
    text = puzzle_check.render(rows, _fake_info(), trials=200_000, tol_se=4.0)
    assert text == (REPO / "tests" / "expected" / "check_all.md").read_text()
    assert "**NO**" in text  # the deliberately wrong third row is flagged
    assert "2/3" not in text  # the unattempted row stays hidden


# ---- ev puzzle bias-check --------------------------------------------------------------


def test_bias_rows_flag_a_shifted_simulator_but_not_noise() -> None:
    import numpy as np

    rng = np.random.default_rng(0)
    fair = puzzle_bias.BiasRow("fair", rng.normal(0.0, 1.0, 200).tolist())
    shifted = puzzle_bias.BiasRow("shifted", rng.normal(0.6, 1.0, 200).tolist())
    assert fair.ok() and abs(fair.mean_z) < 0.25 and 0.8 < fair.sd_z < 1.2
    assert not shifted.ok()  # a bias of 0.6 SE per run is obvious over 200 seeds
    assert shifted.standardised_mean == pytest.approx(shifted.mean_z * 200**0.5)


def test_bias_check_command(workdir: Path) -> None:
    result = runner.invoke(app, ["puzzle", "bias-check", "--seeds", "5"])
    assert result.exit_code == 0, result.output
    assert "0 flagged" in result.output
    report = (workdir / "reports" / "puzzles" / "bias_check.md").read_text()
    assert report.index("## Limitations") < report.index("## Result")
    assert len([line for line in report.splitlines() if line.startswith("| `")]) == len(
        all_puzzles()
    )


def test_bias_report_regression() -> None:
    rows = [
        puzzle_bias.BiasRow("monty_hall", [0.5, -0.5, 1.0, -1.0]),
        puzzle_bias.BiasRow("penney_game", [2.5, 3.0, 2.0, 2.5]),
    ]
    text = puzzle_bias.render(rows, _fake_info(), seeds=4, trials=1000)
    assert "**NO**" in text and "Largest: `penney_game` at +5.00" in text
    assert text == (REPO / "tests" / "expected" / "bias_check.md").read_text()
