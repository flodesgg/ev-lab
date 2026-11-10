"""Numbers quoted in README and docs must appear in the report file they cite.

Hard rule of the project: every number in the documentation comes from a file produced by
this repository's code. This test keeps the quoted figures and the committed reports in
step: regenerate a report with different results and the documentation fails here until it
is updated.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

PUZZLES = "reports/puzzles/check_all.md"
BIAS = "reports/puzzles/bias_check.md"
CARDS = "reports/cards/cards_check.md"
GAMES = "reports/games/games.md"
KELLY = "reports/kelly/kelly.md"
LEDUC = "reports/games/leduc.md"
CPP = "reports/cards/cpp_check.md"

# (text as quoted in the docs, report that must contain `evidence`, evidence)
CLAIMS: list[tuple[str, str, str]] = [
    ("29 of 29 agree", PUZZLES, "Puzzles checked: **29**; exact and Monte Carlo agree: **29**"),
    ("largest |z| 3.86", PUZZLES, "Largest |z|: 3.86"),
    ("200,000 trials", PUZZLES, "Trials per puzzle: 200,000"),
    ("bias_check.md", BIAS, "below 4: **29 of 29**"),
    ("2,598,960", CARDS, "| total | 2,598,960 | 2,598,960 |"),
    ("133,784,560", CARDS, "| total | 133,784,560 | 133,784,560 |"),
    ("100,000 random 7-card hands", CARDS, "on 100,000 random 7-card hands: 0 mismatches"),
    ("197833/428076", CARDS, "| AhKh vs QsQd, preflop | 1,712,304 | 197833/428076 |"),
    ("1,712,304", CARDS, "1,712,304"),
    ("0.000633", GAMES, "exploitability 0.000633"),
    ("-0.055554", GAMES, "value for player 1 -0.055554"),
    ("0.0030", GAMES, "largest deviation from the equilibrium with that alpha: 0.0030"),
    ("-1/18", GAMES, "| 1/3 | -1/18 | 0 |"),
    ("0.000041", LEDUC, "exploitability **0.000041**"),
    ("0.005333", LEDUC, "Vanilla CFR after 3,000 iterations: exploitability 0.005333"),
    ("-5/64", LEDUC, "| both players uniformly random | -0.078125000000 | -5/64"),
    ("288 information sets", LEDUC, "Size: 288 information sets by rank (936 when suits"),
    ("C++17 port", CPP, "C++ vs numpy evaluator on 1,000,000 random 7-card hands: 0 mismatches"),
    ("1/10", KELLY, "**f\\* = 1/10**"),
    ("75%", KELLY, "Half Kelly keeps 75% of the growth rate"),
    ("47.1% to 12.3%", KELLY, "drops from 47.1% to 12.3%"),
    ("n = 10, 20, 50", KELLY, "expected growth for n = 10, 20, 50 past bets"),
]

DOCS = ["README.md", "docs/writeup.md"]


@pytest.mark.parametrize(("quoted", "report", "evidence"), CLAIMS)
def test_quoted_number_is_backed_by_its_report(quoted: str, report: str, evidence: str) -> None:
    assert evidence in (REPO / report).read_text(), f"{report} no longer says: {evidence}"
    used = [d for d in DOCS if quoted in (REPO / d).read_text()]
    assert used, f"claim {quoted!r} is listed here but quoted in no document"


def test_writeup_only_claims_extra_numbers_that_reports_contain() -> None:
    """Figures that appear only in the write-up, each tied to its report line."""
    writeup = (REPO / "docs" / "writeup.md").read_text()
    extra = [
        ("mean +0.004 and standard deviation\n0.98", BIAS),
        ("0.46335 ± 0.00111", CARDS),
        ("0.0050", GAMES),
        ("0.0027", GAMES),
        ("alpha = 0.2200", GAMES),
        ("0.005008", KELLY),
        ("-0.000138", KELLY),
        ("n = 10, 20, 50, 100, 200", KELLY),
    ]
    for quoted, report in extra:
        assert quoted in writeup, quoted
        needle = quoted.replace("alpha = ", "alpha = P(bet | jack) = ")
        if report == BIAS:
            needle = "| `random_walk_duration` | +0.004 | 0.98 |"
        assert needle in (REPO / report).read_text(), f"{quoted} not found in {report}"


def test_every_report_puts_limitations_before_results() -> None:
    for report in (PUZZLES, BIAS, CARDS, GAMES, KELLY, LEDUC, CPP):
        text = (REPO / report).read_text()
        assert text.index("## Limitations") < text.index("## Result"), report


def test_reports_were_generated_from_committed_code() -> None:
    for report in (PUZZLES, BIAS, CARDS, GAMES, KELLY, LEDUC, CPP):
        footer = (REPO / report).read_text().rstrip().splitlines()[-1]
        assert footer.startswith("_run ") and "seed " in footer, report
        assert "(dirty)" not in footer, f"{report} was generated from uncommitted code"
        assert "no-git" not in footer, report


def test_no_report_or_document_spoils_a_practice_puzzle() -> None:
    """Rows of puzzles I have not attempted must stay hidden in the committed report."""
    import csv

    from ev_lab.puzzles.registry import all_puzzles

    log = REPO / "practice" / "puzzle_log.csv"
    attempted = set()
    if log.exists():
        with log.open(newline="") as f:
            attempted = {row["puzzle_id"] for row in csv.DictReader(f)}
    rows = {
        line.split("`")[1]: line
        for line in (REPO / PUZZLES).read_text().splitlines()
        if line.startswith("| `")
    }
    for p in all_puzzles():
        if p.id not in attempted:
            assert "hidden until attempted" in rows[p.id], p.id
