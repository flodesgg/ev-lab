"""The timed mental-math session as a step-by-step object (for the web page).

Same rules as `math_session.run_math_session`, which drives the terminal: N questions in M
minutes, the clock is checked when an answer arrives, an answer after the deadline is
discarded, an empty answer skips the question (logged as wrong), unreadable input is asked
again while the clock runs.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from ev_lab.fmt import dec
from ev_lab.puzzles.grading import parse_number
from ev_lab.trainer.adaptive import pick_category
from ev_lab.trainer.math_session import AnswerLogger, MathSummary
from ev_lab.trainer.mental_math import Question, generate


@dataclass(frozen=True)
class Graded:
    status: str  # "graded", "invalid" (ask again) or "late" (deadline passed, not counted)
    correct: bool = False
    correct_answer: str = ""


class MathDrill:
    def __init__(
        self,
        *,
        questions: int,
        seconds_limit: float,
        level: int,
        rng: np.random.Generator,
        weights: dict[str, float],
        clock: Callable[[], float],
        log: AnswerLogger,
    ) -> None:
        self._level, self._rng, self._weights = level, rng, weights
        self._clock, self._log = clock, log
        self.summary = MathSummary(target=questions, seconds_limit=seconds_limit)
        self._start = clock()
        self._asked = self._start
        self.finished = False
        self.current: Question | None = None
        self._next_question()

    @property
    def number(self) -> int:
        """1-based number of the current question."""
        return self.summary.answered + 1

    def remaining(self) -> float:
        return max(0.0, self.summary.seconds_limit - (self._clock() - self._start))

    def _finish(self, reason: str) -> None:
        self.finished = True
        self.current = None
        self.summary.ended = reason
        self.summary.seconds_used = min(self._clock() - self._start, self.summary.seconds_limit)

    def _next_question(self) -> None:
        if self.summary.answered >= self.summary.target:
            self._finish("all questions answered")
            return
        self.current = generate(self._rng, pick_category(self._rng, self._weights), self._level)
        self._asked = self._clock()

    def submit(self, text: str) -> Graded:
        if self.finished or self.current is None:
            raise RuntimeError("the session is over")
        now = self._clock()
        if now - self._start > self.summary.seconds_limit:
            self._finish("time is up")
            return Graded("late")
        given = None
        if text.strip():
            try:
                given = parse_number(text, percent_divides=False)
            except ValueError:
                return Graded("invalid")
        q = self.current
        ok = given is not None and q.is_correct(given)
        seconds = now - self._asked
        self._log(q, text.strip(), ok, seconds)
        self.summary.results.append((q, ok, seconds))
        self._next_question()
        return Graded("graded", ok, dec(q.answer))

    def stop(self) -> None:
        if not self.finished:
            self._finish("stopped early")
