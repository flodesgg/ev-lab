"""The `ev cards-check` report: enumeration counts, fast vs oracle, exact vs Monte Carlo."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from ev_lab.cards.evaluator import CATEGORY_NAMES
from ev_lab.cards.reference import FIVE_CARD_COUNTS, SEVEN_CARD_COUNTS
from ev_lab.prob.montecarlo import McResult, agrees
from ev_lab.runinfo import RunInfo

REPORT_NAME = "cards_check.md"


@dataclass(frozen=True)
class EquityRow:
    label: str
    scenarios: int
    exact: Fraction
    mc: McResult


@dataclass(frozen=True)
class CardsCheck:
    five_counts: Sequence[int]
    seven_counts: Sequence[int] | None  # None when the slow enumeration was skipped
    oracle_hands: int
    oracle_mismatches: int
    equities: Sequence[EquityRow]
    tol_se: float

    def ok(self) -> bool:
        return (
            tuple(self.five_counts) == FIVE_CARD_COUNTS
            and (self.seven_counts is None or tuple(self.seven_counts) == SEVEN_CARD_COUNTS)
            and self.oracle_mismatches == 0
            and all(agrees(r.exact, r.mc, self.tol_se) for r in self.equities)
        )


def _count_table(computed: Sequence[int], reference: Sequence[int]) -> list[str]:
    lines = ["| category | computed | reference | match |", "|---|---|---|---|"]
    for i in range(8, -1, -1):
        same = "yes" if computed[i] == reference[i] else "**NO**"
        lines.append(f"| {CATEGORY_NAMES[i]} | {computed[i]:,} | {reference[i]:,} | {same} |")
    lines.append(f"| total | {sum(computed):,} | {sum(reference):,} | |")
    return lines


def render(check: CardsCheck, info: RunInfo) -> str:
    lines = [
        "# Cards: evaluator and equity checks",
        "",
        "## Limitations (read first)",
        "",
        "- The fast evaluator is compared with the oracle on a random sample of 7-card hands, "
        "not on all of them. The category counts over all hands are a second, complete check, "
        "but two errors inside one category that cancel in the count would pass it.",
        "- The oracle and the fast evaluator share the value encoding (category, then "
        "tiebreakers). A wrong idea about poker hand ranking would be in both.",
        "- Equity assumes every remaining board is equally likely and all hands go to "
        "showdown. It says nothing about betting.",
        "- Offline study only. Nothing here connects to, or assists play on, any site.",
        "",
        "## Result",
        "",
        f"- Overall: **{'all checks pass' if check.ok() else 'A CHECK FAILED'}**.",
        f"- Fast evaluator vs oracle on {check.oracle_hands:,} random 7-card hands: "
        f"{check.oracle_mismatches} mismatches.",
        "",
        "## All 5-card hands by category (exact enumeration)",
        "",
        *_count_table(check.five_counts, FIVE_CARD_COUNTS),
        "",
        "## All 7-card hands by category, best five of seven (exact enumeration)",
        "",
    ]
    if check.seven_counts is None:
        lines.append("Skipped in this run (slow). Run `ev cards-check --full`.")
    else:
        lines += _count_table(check.seven_counts, SEVEN_CARD_COUNTS)
    lines += [
        "",
        "## Equity: exact enumeration vs Monte Carlo",
        "",
        "Equity of the first hand. `z` = (Monte Carlo - exact) / SE.",
        "",
        "| matchup | scenarios | exact | exact (decimal) | Monte Carlo ± SE | z | agree |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in check.equities:
        ok = "yes" if agrees(r.exact, r.mc, check.tol_se) else "**NO**"
        lines.append(
            f"| {r.label} | {r.scenarios:,} | {r.exact} | {float(r.exact):.6f} | "
            f"{r.mc.estimate:.5f} ± {r.mc.se:.5f} | {r.mc.z(r.exact):+.2f} | {ok} |"
        )
    lines += ["", "---", info.markdown_footer(), ""]
    return "\n".join(lines)


def write(report_dir: Path, text: str) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / REPORT_NAME
    path.write_text(text)
    return path
