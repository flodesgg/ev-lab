"""practice/puzzle_log.csv: one row per attempt at a puzzle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ev_lab.practice_log import append_row, read_rows

FILE_NAME = "puzzle_log.csv"
HEADER = ("timestamp_utc", "run_id", "puzzle_id", "answer", "correct", "seconds")


@dataclass(frozen=True)
class Attempts:
    count: int
    solved: bool  # at least one correct attempt


def log_attempt(
    practice_dir: Path, run_id: str, puzzle_id: str, answer: str, correct: bool, seconds: float
) -> None:
    append_row(
        practice_dir / FILE_NAME,
        HEADER,
        {
            "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "run_id": run_id,
            "puzzle_id": puzzle_id,
            "answer": answer,
            "correct": int(correct),
            "seconds": f"{seconds:.1f}",
        },
    )


def attempts_by_puzzle(practice_dir: Path) -> dict[str, Attempts]:
    out: dict[str, Attempts] = {}
    for row in read_rows(practice_dir / FILE_NAME, HEADER):
        prev = out.get(row["puzzle_id"], Attempts(0, False))
        out[row["puzzle_id"]] = Attempts(prev.count + 1, prev.solved or row["correct"] == "1")
    return out
