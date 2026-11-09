"""The `ev puzzle check-all` report: exact answer vs Monte Carlo for every puzzle.

No spoilers: the exact answer and the estimate of a puzzle are printed only once that
puzzle has been attempted. Before that the row shows only the z-score, which says whether
the two methods agree without revealing either number.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from ev_lab.prob.montecarlo import McResult, agrees
from ev_lab.puzzles.base import Puzzle, format_answer
from ev_lab.runinfo import RunInfo

REPORT_NAME = "check_all.md"
HIDDEN = "hidden until attempted"


@dataclass(frozen=True)
class CheckRow:
    puzzle: Puzzle
    exact: Fraction
    mc: McResult
    attempted: bool

    def ok(self, tol_se: float) -> bool:
        return agrees(self.exact, self.mc, tol_se)


def render(rows: Sequence[CheckRow], info: RunInfo, trials: int, tol_se: float) -> str:
    passed = sum(r.ok(tol_se) for r in rows)
    p_false = math.erfc(tol_se / math.sqrt(2))  # two-sided normal tail
    worst = max((abs(r.mc.z(r.exact)) for r in rows), default=0.0)
    lines = [
        "# Puzzle library: exact answers vs Monte Carlo",
        "",
        "## Limitations (read first)",
        "",
        f"- A check passes when the exact answer is within {tol_se:g} standard errors (SE) of "
        "the simulated mean. An error smaller than the SE cannot be detected this way.",
        "- The solver and the simulator are written separately, but by the same author from "
        "the same reading of the statement. A misread statement passes this check.",
        "- For conditional probabilities the simulator keeps only the trials where the "
        "condition happened, so `n` is smaller than the number of trials run.",
        f"- False alarms: for a correct answer P(|z| >= {tol_se:g}) is about {p_false:.1e} "
        f"(normal approximation), so with {len(rows)} checks about 1 run in "
        f"{round(1 / (p_false * len(rows))):,} flags something that is fine. The seed is "
        "fixed, so a given commit and config always give the same table.",
        "",
        "## Result",
        "",
        f"- Puzzles checked: **{len(rows)}**; exact and Monte Carlo agree: "
        f"**{passed}**; disagree: **{len(rows) - passed}**.",
        f"- Trials per puzzle: {trials:,}. Largest |z|: {worst:.2f}.",
        "- Exact answers are `fractions.Fraction` (computed, never typed in). Estimates are "
        "simulation means with their standard error.",
        "",
        "## Table",
        "",
        "`z` = (Monte Carlo estimate - exact) / SE.",
        "",
        "| puzzle | difficulty | tags | n | z | agree | exact | Monte Carlo ± SE |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        p = r.puzzle
        if r.attempted:
            exact, estimate = format_answer(r.exact), f"{r.mc.estimate:.5f} ± {r.mc.se:.5f}"
        else:
            exact, estimate = HIDDEN, HIDDEN
        lines.append(
            f"| `{p.id}` | {p.difficulty} | {', '.join(p.tags)} | {r.mc.n:,} | "
            f"{r.mc.z(r.exact):+.2f} | {'yes' if r.ok(tol_se) else '**NO**'} | "
            f"{exact} | {estimate} |"
        )
    lines += ["", "---", info.markdown_footer(), ""]
    return "\n".join(lines)


def write(report_dir: Path, text: str) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / REPORT_NAME
    path.write_text(text)
    return path
