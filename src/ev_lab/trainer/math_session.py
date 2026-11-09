"""A timed mental-math session: "N questions in M minutes".

The clock is checked when an answer arrives (input cannot be interrupted): an answer that
comes in after the deadline is discarded and the session ends.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from statistics import median

import numpy as np

from ev_lab.fmt import dec
from ev_lab.puzzles.grading import parse_number
from ev_lab.trainer.adaptive import pick_category
from ev_lab.trainer.io import IO
from ev_lab.trainer.mental_math import TITLES, Question, generate

AnswerLogger = Callable[[Question, str, bool, float], None]


@dataclass
class MathSummary:
    target: int
    seconds_limit: float
    seconds_used: float = 0.0
    results: list[tuple[Question, bool, float]] = field(default_factory=list)
    ended: str = "all questions answered"

    @property
    def answered(self) -> int:
        return len(self.results)

    @property
    def correct(self) -> int:
        return sum(ok for _, ok, _ in self.results)

    def lines(self) -> list[str]:
        out = [
            f"Session over ({self.ended}). Answered {self.answered} of {self.target} in "
            f"{self.seconds_used:.0f} s (limit {self.seconds_limit:.0f} s).",
        ]
        if not self.results:
            return out
        out.append(
            f"Correct: {self.correct}/{self.answered} ({self.correct / self.answered:.0%}). "
            f"Median time per answer: {median(s for _, _, s in self.results):.1f} s."
        )
        for category, title in TITLES.items():
            rows = [(ok, s) for q, ok, s in self.results if q.category == category]
            if rows:
                out.append(
                    f"  {title:28s} {sum(ok for ok, _ in rows)}/{len(rows)} correct, "
                    f"median {median(s for _, s in rows):.1f} s"
                )
        return out


def run_math_session(
    *,
    questions: int,
    seconds_limit: float,
    level: int,
    rng: np.random.Generator,
    weights: dict[str, float],
    io: IO,
    clock: Callable[[], float],
    log: AnswerLogger,
) -> MathSummary:
    summary = MathSummary(target=questions, seconds_limit=seconds_limit)
    start = clock()
    for number in range(1, questions + 1):
        if clock() - start >= seconds_limit:
            summary.ended = "time is up"
            break
        q = generate(rng, pick_category(rng, weights), level)
        asked = clock()
        given = None
        while given is None:
            left = max(0.0, seconds_limit - (clock() - start))
            text = io.ask(f"[{number}/{questions} | {left:3.0f} s left]  {q.text} = ")
            if text is None:
                summary.ended = "stopped early"
                break
            if text.strip() == "":
                break  # skipped: counts as wrong
            try:
                given = parse_number(text, percent_divides=False)
            except ValueError:
                io.say("  not a number; try again (Enter skips)")
        if summary.ended == "stopped early":
            break
        now = clock()
        if now - start > seconds_limit:
            summary.ended = "time is up"
            io.say("  time is up: the last answer came after the deadline and is not counted")
            break
        ok = given is not None and q.is_correct(given)
        seconds = now - asked
        log(q, "" if given is None else (text or "").strip(), ok, seconds)
        summary.results.append((q, ok, seconds))
        io.say("  [green]right[/green]" if ok else f"  [red]wrong[/red]: {dec(q.answer)}")
    summary.seconds_used = min(clock() - start, seconds_limit)
    return summary
