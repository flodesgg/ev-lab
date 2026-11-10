"""The trainer as a JSON application: the web page talks to `TrainerApp.handle`.

No HTTP here, so everything can be tested without a socket. The app holds at most one math
session, one puzzle and one market game at a time (there is one user: me). It writes to the
same practice logs as the terminal commands, through the same functions.

No spoilers: an answer or an explanation is only ever part of the reply to a submitted
answer.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np

from ev_lab.context import Context
from ev_lab.prob.montecarlo import rng_for, run_mc
from ev_lab.puzzles.base import Puzzle, format_answer
from ev_lab.puzzles.grading import (
    market_feedback,
    market_is_correct,
    number_is_correct,
    parse_number,
)
from ev_lab.puzzles.log import log_attempt
from ev_lab.puzzles.registry import all_puzzles
from ev_lab.trainer import market_game, math_log, srs, stats
from ev_lab.trainer.adaptive import category_weights
from ev_lab.trainer.market import QUANTITIES, MarketGame
from ev_lab.trainer.math_drill import MathDrill
from ev_lab.trainer.mental_math import CATEGORIES, TITLES, TOLERANCE_NOTE
from ev_lab.trainer.quiz import pick_puzzle

Json = dict[str, Any]
FIGURES = (stats.ACCURACY_PNG, stats.SPEED_PNG)


class ApiError(Exception):
    """A request the app refuses; becomes HTTP 400 with a readable message."""


class TrainerApp:
    def __init__(
        self, ctx: Context, seed: int, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.ctx, self.seed, self.clock = ctx, seed, clock
        self._counter = 0
        self._drill: MathDrill | None = None
        self._puzzle: Puzzle | None = None
        self._puzzle_started = 0.0
        self._game: MarketGame | None = None

    # ---- helpers -----------------------------------------------------------------------

    def _rng(self, name: str) -> np.random.Generator:
        self._counter += 1
        return rng_for(self.seed, f"web:{name}:{self._counter}")

    @property
    def _practice(self) -> Path:
        return self.ctx.cfg.paths.practice

    def _today(self) -> Any:
        return datetime.now(UTC).date()

    def _schedule(self) -> dict[str, srs.Card]:
        cfg = self.ctx.cfg.trainer.srs
        return srs.load_schedule(self._practice, cfg.fast_seconds, cfg.slow_seconds)

    @staticmethod
    def _number(body: Mapping[str, Any], key: str) -> Fraction:
        try:
            return parse_number(str(body.get(key, "")))
        except ValueError as e:
            raise ApiError(f"{key}: {e}") from e

    # ---- routing -----------------------------------------------------------------------

    def handle(self, method: str, path: str, body: Mapping[str, Any] | None = None) -> Json:
        """Dispatch one API call. Raises ApiError for a bad request, KeyError for no route."""
        routes: dict[tuple[str, str], Callable[[Mapping[str, Any]], Json]] = {
            ("GET", "/api/overview"): self.overview,
            ("POST", "/api/math/start"): self.math_start,
            ("POST", "/api/math/answer"): self.math_answer,
            ("POST", "/api/math/stop"): self.math_stop,
            ("POST", "/api/quiz/next"): self.quiz_next,
            ("POST", "/api/quiz/answer"): self.quiz_answer,
            ("POST", "/api/market/start"): self.market_start,
            ("POST", "/api/market/quote"): self.market_quote,
            ("POST", "/api/stats"): self.stats,
        }
        return routes[(method, path)](body or {})

    # ---- overview and statistics -------------------------------------------------------

    def _summary(self) -> stats.Summary:
        cfg = self.ctx.cfg.trainer.stats
        today = self._today()
        due = sum(c.days_overdue(today) >= 0 for c in self._schedule().values())
        return stats.summarise(
            self._practice,
            today,
            cfg.weakest_window,
            cfg.weakest_min_answers,
            len(all_puzzles()),
            due,
        )

    @staticmethod
    def _summary_json(s: stats.Summary) -> Json:
        def rows(items: list[stats.CategoryStat]) -> list[Json]:
            return [
                {
                    "category": TITLES[c.category],
                    "answers": c.answers,
                    "accuracy": round(c.accuracy, 4),
                    "median_seconds": round(c.median_seconds, 1),
                }
                for c in items
            ]

        return {
            "streak": s.streak,
            "practice_days": s.practice_days,
            "math_answers": s.math_answers,
            "math_sessions": s.math_sessions,
            "puzzles_solved": s.puzzles_solved,
            "puzzles_tried": s.puzzles_tried,
            "puzzles_total": s.puzzles_total,
            "reviews_due": s.reviews_due,
            "market_games": s.market_games,
            "market_total_pnl": round(s.market_total_pnl, 2),
            "market_rounds": s.market_rounds,
            "market_quotes_containing_fair": s.market_quotes_containing_fair,
            "weakest": rows(s.weakest),
            "categories": rows(s.categories),
        }

    def overview(self, _body: Mapping[str, Any]) -> Json:
        cfg = self.ctx.cfg.trainer.math
        return {
            "presets": {
                name: {"questions": p.questions, "minutes": p.minutes}
                for name, p in cfg.presets.items()
            },
            "default_preset": self.ctx.cfg.trainer.daily.math_preset,
            "level": cfg.level,
            "quantities": {q.id: q.title for q in QUANTITIES.values()},
            "tolerance_note": TOLERANCE_NOTE,
            "stats": self._summary_json(self._summary()),
        }

    def stats(self, _body: Mapping[str, Any]) -> Json:
        """Recompute the statistics and rewrite the report and figures."""
        summary = self._summary()
        figures: list[str] = []
        if summary.practice_days:
            written = stats.write_report(
                self.ctx.cfg.paths.reports / "practice",
                summary,
                stats.load_math(self._practice),
                self.ctx.info,
            )
            figures = [p.name for p in written if p.name in FIGURES]
        return {"stats": self._summary_json(summary), "figures": figures}

    def figure_path(self, name: str) -> Path | None:
        """Only the two known figure files can be served."""
        path = self.ctx.cfg.paths.reports / "practice" / name
        return path if name in FIGURES and path.exists() else None

    # ---- mental math -------------------------------------------------------------------

    def _math_state(self, drill: MathDrill) -> Json:
        return {
            "done": drill.finished,
            "number": drill.number,
            "total": drill.summary.target,
            "remaining": round(drill.remaining(), 1),
            "question": drill.current.text if drill.current else None,
            "summary": drill.summary.lines() if drill.finished else [],
        }

    def math_start(self, body: Mapping[str, Any]) -> Json:
        cfg = self.ctx.cfg.trainer.math
        preset = str(body.get("preset") or self.ctx.cfg.trainer.daily.math_preset)
        if preset not in cfg.presets:
            raise ApiError(f"unknown preset {preset!r}")
        level = int(body.get("level") or cfg.level)
        if level not in (1, 2, 3):
            raise ApiError("level must be 1, 2 or 3")
        weights = category_weights(
            math_log.history(self._practice), list(CATEGORIES), cfg.adaptive_window
        )
        p = cfg.presets[preset]
        run_id = f"{self.ctx.info.run_id}-m{self._counter + 1}"
        self._drill = MathDrill(
            questions=p.questions,
            seconds_limit=p.minutes * 60,
            level=level,
            rng=self._rng("math"),
            weights=weights,
            clock=self.clock,
            log=lambda q, answer, ok, seconds: math_log.log_answer(
                self._practice, run_id, q, answer, ok, seconds
            ),
        )
        focus: list[str] = []
        if max(weights.values()) > min(weights.values()):
            focus = [TITLES[c] for c in sorted(weights, key=lambda c: -weights[c])[:2]]
        return {**self._math_state(self._drill), "focus": focus}

    def _active_drill(self) -> MathDrill:
        if self._drill is None or self._drill.finished:
            raise ApiError("no math session is running")
        return self._drill

    def math_answer(self, body: Mapping[str, Any]) -> Json:
        drill = self._active_drill()
        graded = drill.submit(str(body.get("answer", "")))
        return {
            "status": graded.status,
            "correct": graded.correct,
            "correct_answer": graded.correct_answer,
            **self._math_state(drill),
        }

    def math_stop(self, _body: Mapping[str, Any]) -> Json:
        drill = self._active_drill()
        drill.stop()
        return self._math_state(drill)

    # ---- probability quiz --------------------------------------------------------------

    def quiz_next(self, _body: Mapping[str, Any]) -> Json:
        puzzle, reason = pick_puzzle(
            all_puzzles(), self._schedule(), self._today(), self._rng("quiz")
        )
        self._puzzle, self._puzzle_started = puzzle, self.clock()
        return {
            "id": puzzle.id,
            "title": puzzle.title,
            "statement": puzzle.statement,
            "difficulty": puzzle.difficulty,
            "tags": list(puzzle.tags),
            "kind": puzzle.kind,
            "max_width": None if puzzle.max_width is None else str(puzzle.max_width),
            "reason": reason,
        }

    def quiz_answer(self, body: Mapping[str, Any]) -> Json:
        puzzle = self._puzzle
        if puzzle is None:
            raise ApiError("no puzzle is open")
        exact = puzzle.solve()
        if puzzle.kind == "market":
            assert puzzle.max_width is not None
            bid, ask = self._number(body, "bid"), self._number(body, "ask")
            correct = market_is_correct(bid, ask, exact, puzzle.max_width)
            detail = market_feedback(bid, ask, exact, puzzle)
            answer_text = f"{str(body['bid']).strip()} @ {str(body['ask']).strip()}"
        else:
            answer = self._number(body, "answer")
            tolerance = self.ctx.cfg.puzzles.rel_tolerance
            correct = number_is_correct(answer, exact, tolerance)
            detail = f"tolerance {tolerance:.1%} of the exact value"
            answer_text = str(body["answer"]).strip()
        seconds = self.clock() - self._puzzle_started
        log_attempt(self._practice, self.ctx.info.run_id, puzzle.id, answer_text, correct, seconds)
        self.ctx.logger.info("web puzzle %s: correct=%s", puzzle.id, correct)
        self._puzzle = None  # one attempt per showing; the solution is now revealed
        mc = run_mc(
            puzzle.simulate,
            self.ctx.cfg.monte_carlo.trials,
            rng_for(self.ctx.cfg.random.seed, f"puzzle:{puzzle.id}"),
        )
        card = self._schedule()[puzzle.id]
        return {
            "correct": correct,
            "detail": detail,
            "seconds": round(seconds, 1),
            "explanation": puzzle.explanation.format(answer=format_answer(exact)),
            "exact": format_answer(exact),
            "monte_carlo": f"{mc.estimate:.5f} ± {mc.se:.5f} (SE), n = {mc.n:,}, "
            f"z = {mc.z(exact):+.2f}",
            "next_review": f"{card.due.isoformat()} (in {card.interval_days} d)",
        }

    # ---- market game -------------------------------------------------------------------

    def _market_state(self, game: MarketGame) -> Json:
        state: Json = {"done": game.finished, "rounds": game.rounds}
        if game.finished:
            state |= {
                "x": game.x,
                "total_pnl": f"{float(game.total_pnl()):+.2f}",
                "review": market_game.review_rows(game),
            }
        else:
            state |= {
                "round": len(game.records) + 1,
                "public": market_game.known_text(game),
                "max_width": str(game.max_width()),
            }
        return state

    def market_start(self, body: Mapping[str, Any]) -> Json:
        cfg = self.ctx.cfg.trainer.market
        rng = self._rng("market")
        quantity = body.get("quantity") or list(QUANTITIES)[int(rng.integers(0, len(QUANTITIES)))]
        if quantity not in QUANTITIES:
            raise ApiError(f"unknown quantity {quantity!r}")
        self._game = MarketGame(
            QUANTITIES[str(quantity)],
            rng,
            Fraction(cfg.informed_prob).limit_denominator(1000),
            [Fraction(f).limit_denominator(1000) for f in cfg.width_fracs],
            cfg.min_width,
        )
        return {"title": self._game.quantity.title, **self._market_state(self._game)}

    def market_quote(self, body: Mapping[str, Any]) -> Json:
        game = self._game
        if game is None or game.finished:
            raise ApiError("no market game is running")
        bid, ask = self._number(body, "bid"), self._number(body, "ask")
        error = game.quote_error(bid, ask)
        if error is not None:
            return {"status": "invalid", "error": error, **self._market_state(game)}
        record = game.play_round(bid, ask)
        if game.finished:
            market_game.log_game(self._practice, f"{self.ctx.info.run_id}-g{self._counter}", game)
            self.ctx.logger.info("web market %s: pnl=%s", game.quantity.id, game.total_pnl())
        return {
            "status": "ok",
            "trade": market_game.trade_text(record),
            **self._market_state(game),
        }
