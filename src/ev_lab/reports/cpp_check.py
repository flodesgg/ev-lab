"""The `ev cards-cpp` report: the C++ evaluator against the Python evaluators."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from ev_lab.cards.evaluator import CATEGORY_NAMES
from ev_lab.cards.reference import FIVE_CARD_COUNTS, SEVEN_CARD_COUNTS
from ev_lab.runinfo import RunInfo

REPORT_NAME = "cpp_check.md"


@dataclass(frozen=True)
class CppCheck:
    five_counts: Sequence[int]
    seven_counts: Sequence[int]
    seven_seconds: float  # C++ time to enumerate all 7-card hands
    oracle_hands: int
    oracle_mismatches: int  # C++ vs the 21-subset Python oracle
    numpy_hands: int
    numpy_mismatches: int  # C++ vs the numpy evaluator
    cpp_hands_per_second: float
    numpy_hands_per_second: float

    def ok(self) -> bool:
        return (
            tuple(self.five_counts) == FIVE_CARD_COUNTS
            and tuple(self.seven_counts) == SEVEN_CARD_COUNTS
            and self.oracle_mismatches == 0
            and self.numpy_mismatches == 0
        )


def render(c: CppCheck, info: RunInfo) -> str:
    lines = [
        "# Cards: the C++ evaluator",
        "",
        "## Limitations (read first)",
        "",
        "- The C++ code is a port of the numpy evaluator, by the same author, with the same "
        "value encoding. It adds a second language and speed, not an independent design.",
        "- Speeds are measured on this machine in one run and will differ elsewhere. The C++ "
        "figure times evaluation only; the numpy figure includes numpy's own overheads. "
        "Treat the ratio as an order of magnitude.",
        "- Python talks to the C++ program through text on standard input, which is simple "
        "and slow; that cost is not part of the speed figure.",
        "",
        "## Result",
        "",
        f"- Overall: **{'all checks pass' if c.ok() else 'A CHECK FAILED'}**.",
        f"- C++ vs Python oracle (all 21 five-card subsets) on {c.oracle_hands:,} random "
        f"7-card hands: {c.oracle_mismatches} mismatches.",
        f"- C++ vs numpy evaluator on {c.numpy_hands:,} random 7-card hands: "
        f"{c.numpy_mismatches} mismatches.",
        f"- All {sum(c.seven_counts):,} seven-card hands enumerated in C++ in "
        f"{c.seven_seconds:.1f} s.",
        f"- Speed (7-card hands per second): C++ {c.cpp_hands_per_second:,.0f}, numpy "
        f"{c.numpy_hands_per_second:,.0f}, ratio "
        f"{c.cpp_hands_per_second / c.numpy_hands_per_second:,.0f}.",
        "",
        "## Category counts from C++ (exact enumeration)",
        "",
        "| category | 5 cards | reference | 7 cards | reference | match |",
        "|---|---|---|---|---|---|",
    ]
    for i in range(8, -1, -1):
        same = c.five_counts[i] == FIVE_CARD_COUNTS[i] and c.seven_counts[i] == SEVEN_CARD_COUNTS[i]
        lines.append(
            f"| {CATEGORY_NAMES[i]} | {c.five_counts[i]:,} | {FIVE_CARD_COUNTS[i]:,} | "
            f"{c.seven_counts[i]:,} | {SEVEN_CARD_COUNTS[i]:,} | {'yes' if same else '**NO**'} |"
        )
    lines += ["", "---", info.markdown_footer(), ""]
    return "\n".join(lines)


def write(report_dir: Path, text: str) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / REPORT_NAME
    path.write_text(text)
    return path
