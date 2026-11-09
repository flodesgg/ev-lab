"""The `ev puzzle bias-check` report: is any simulator biased?

One exact-vs-simulation comparison at a fixed seed can pass or fail by luck. Repeating it on
many independent seeds gives, per puzzle, a set of z-scores that should look like standard
normal draws: mean near 0, standard deviation near 1. A simulator (or solver) with a small
systematic error shows a mean z that grows with the square root of the number of trials.

Only z-scores are printed, never answers.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean, pstdev

from ev_lab.runinfo import RunInfo

REPORT_NAME = "bias_check.md"
MEAN_Z_LIMIT = 4.0  # the mean of N z-scores has standard error 1/sqrt(N)


@dataclass(frozen=True)
class BiasRow:
    puzzle_id: str
    z_scores: Sequence[float]

    @property
    def mean_z(self) -> float:
        return fmean(self.z_scores)

    @property
    def sd_z(self) -> float:
        return pstdev(self.z_scores)

    @property
    def standardised_mean(self) -> float:
        """mean z in units of its own standard error, 1/sqrt(N)."""
        return self.mean_z * math.sqrt(len(self.z_scores))

    def ok(self) -> bool:
        return abs(self.standardised_mean) < MEAN_Z_LIMIT


def render(rows: Sequence[BiasRow], info: RunInfo, seeds: int, trials: int) -> str:
    worst = max(rows, key=lambda r: abs(r.standardised_mean))
    lines = [
        "# Puzzle simulators: bias check over independent seeds",
        "",
        "## Limitations (read first)",
        "",
        "- This detects a systematic gap between solver and simulator. It cannot detect an "
        "error they share (a misread statement).",
        f"- A gap much smaller than SE / sqrt({seeds}) of one run stays invisible.",
        f"- With {len(rows)} puzzles and a limit of {MEAN_Z_LIMIT:g}, a false alarm is very "
        "unlikely; a real bias of a few percent of one standard error is flagged.",
        "",
        "## Result",
        "",
        f"- {seeds} independent seeds x {trials:,} trials per puzzle.",
        f"- Puzzles with |mean z| x sqrt({seeds}) below {MEAN_Z_LIMIT:g}: "
        f"**{sum(r.ok() for r in rows)} of {len(rows)}**.",
        f"- Largest: `{worst.puzzle_id}` at {worst.standardised_mean:+.2f}.",
        "",
        "## Table",
        "",
        f"| puzzle | mean z | sd of z | mean z x sqrt({seeds}) | share with abs(z) > 2 | ok |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        beyond = sum(abs(z) > 2 for z in r.z_scores) / len(r.z_scores)
        lines.append(
            f"| `{r.puzzle_id}` | {r.mean_z:+.3f} | {r.sd_z:.2f} | {r.standardised_mean:+.2f} | "
            f"{beyond:.3f} | {'yes' if r.ok() else '**NO**'} |"
        )
    lines += [
        "",
        "For unbiased code: mean z near 0, sd near 1, and about 4.6% of runs beyond 2.",
        "",
        "---",
        info.markdown_footer(),
        "",
    ]
    return "\n".join(lines)


def write(report_dir: Path, text: str) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / REPORT_NAME
    path.write_text(text)
    return path
