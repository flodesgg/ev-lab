"""practice/math_log.csv: one row per mental-math answer."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ev_lab.fmt import dec
from ev_lab.practice_log import append_row, read_rows
from ev_lab.trainer.adaptive import PastAnswer
from ev_lab.trainer.mental_math import Question

FILE_NAME = "math_log.csv"
HEADER = (
    "timestamp_utc",
    "session_id",
    "category",
    "level",
    "question",
    "answer",
    "correct_answer",
    "correct",
    "seconds",
)


def log_answer(
    practice_dir: Path, session_id: str, q: Question, answer: str, correct: bool, seconds: float
) -> None:
    append_row(
        practice_dir / FILE_NAME,
        HEADER,
        {
            "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "session_id": session_id,
            "category": q.category,
            "level": q.level,
            "question": q.text,
            "answer": answer,
            "correct_answer": dec(q.answer),
            "correct": int(correct),
            "seconds": f"{seconds:.1f}",
        },
    )


def history(practice_dir: Path) -> list[PastAnswer]:
    return [
        PastAnswer(r["category"], r["correct"] == "1", float(r["seconds"]))
        for r in read_rows(practice_dir / FILE_NAME, HEADER)
    ]
