"""Trainer commands: `ev math`, `ev quiz`, `ev market`, `ev daily`, `ev stats`."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path

import numpy as np
import typer

from ev_lab.context import ConfigOption, Context, start
from ev_lab.prob.montecarlo import rng_for
from ev_lab.puzzles.cli import attempt
from ev_lab.puzzles.registry import all_puzzles
from ev_lab.trainer import market_game, math_log, srs, stats
from ev_lab.trainer.adaptive import category_weights
from ev_lab.trainer.io import ConsoleIO
from ev_lab.trainer.market import QUANTITIES, MarketGame
from ev_lab.trainer.math_session import MathSummary, run_math_session
from ev_lab.trainer.mental_math import CATEGORIES, TITLES, TOLERANCE_NOTE
from ev_lab.trainer.quiz import pick_puzzle

SeedOption = typer.Option(None, "--seed", help="Repeat a session exactly (default: random).")


def _seed(ctx: Context, seed: int | None) -> int:
    """A fresh seed per session unless one is given; logged, so any session can be replayed."""
    chosen = seed if seed is not None else int(np.random.SeedSequence().generate_state(1)[0])
    ctx.logger.info("session seed=%d", chosen)
    return chosen


def _math(ctx: Context, io: ConsoleIO, seed: int, preset: str, level: int | None) -> MathSummary:
    cfg = ctx.cfg.trainer.math
    if preset not in cfg.presets:
        io.say(f"unknown preset {preset!r}; presets: {', '.join(cfg.presets)}")
        raise typer.Exit(code=2)
    p = cfg.presets[preset]
    use_level = level if level is not None else cfg.level
    practice = ctx.cfg.paths.practice
    weights = category_weights(math_log.history(practice), list(CATEGORIES), cfg.adaptive_window)
    focus = sorted(weights, key=lambda c: -weights[c])[:2]
    io.say(
        f"[bold]Mental math[/bold]: {p.questions} questions in {p.minutes:g} minutes, level "
        f"{use_level}. Enter skips a question. {TOLERANCE_NOTE}"
    )
    if max(weights.values()) > min(weights.values()):  # no history: all weights are equal
        io.say(f"Asked more often today: {', '.join(TITLES[c] for c in focus)}.")
    if io.ask("Press Enter to start the clock ") is None:
        raise typer.Exit(code=1)
    summary = run_math_session(
        questions=p.questions,
        seconds_limit=p.minutes * 60,
        level=use_level,
        rng=rng_for(seed, "math"),
        weights=weights,
        io=io,
        clock=time.monotonic,
        log=lambda q, answer, ok, seconds: math_log.log_answer(
            practice, ctx.info.run_id, q, answer, ok, seconds
        ),
    )
    io.say("")
    for line in summary.lines():
        io.say(line)
    ctx.logger.info("math: %d answered, %d correct", summary.answered, summary.correct)
    return summary


def _schedule(ctx: Context) -> dict[str, srs.Card]:
    cfg = ctx.cfg.trainer.srs
    return srs.load_schedule(ctx.cfg.paths.practice, cfg.fast_seconds, cfg.slow_seconds)


def _quiz(ctx: Context, io: ConsoleIO, seed: int) -> None:
    today = datetime.now(UTC).date()
    puzzle, reason = pick_puzzle(all_puzzles(), _schedule(ctx), today, rng_for(seed, "quiz"))
    io.say(f"[dim]Chosen: {reason}.[/dim]")
    attempt(puzzle, ctx)
    card = _schedule(ctx)[puzzle.id]
    io.say(f"Next review of this puzzle: {card.due.isoformat()} (in {card.interval_days} d).")


def _market(ctx: Context, io: ConsoleIO, seed: int, quantity: str | None) -> None:
    cfg = ctx.cfg.trainer.market
    rng = rng_for(seed, "market")
    if quantity is None:
        quantity = list(QUANTITIES)[int(rng.integers(0, len(QUANTITIES)))]
    if quantity not in QUANTITIES:
        io.say(f"unknown quantity {quantity!r}; choose from: {', '.join(QUANTITIES)}")
        raise typer.Exit(code=2)
    game = MarketGame(
        QUANTITIES[quantity],
        rng,
        Fraction(cfg.informed_prob).limit_denominator(1000),
        [Fraction(f).limit_denominator(1000) for f in cfg.width_fracs],
        cfg.min_width,
    )
    if market_game.play(game, io):
        market_game.log_game(ctx.cfg.paths.practice, ctx.info.run_id, game)
        ctx.logger.info("market %s: pnl=%s", quantity, game.total_pnl())
    else:
        io.say("Game abandoned; nothing logged.")


def register(app: typer.Typer) -> None:
    @app.command("math")
    def math(
        preset: str | None = typer.Option(None, "--preset", help="A preset from config.yaml."),
        level: int | None = typer.Option(None, "--level", min=1, max=3),
        seed: int | None = SeedOption,
        config: Path = ConfigOption,
    ) -> None:
        """Timed mental math: N questions in M minutes."""
        ctx = start(config)
        chosen = preset or ctx.cfg.trainer.math.default_preset
        _math(ctx, ConsoleIO(), _seed(ctx, seed), chosen, level)

    @app.command("quiz")
    def quiz(seed: int | None = SeedOption, config: Path = ConfigOption) -> None:
        """One probability puzzle: unseen or previously wrong first."""
        ctx = start(config)
        _quiz(ctx, ConsoleIO(), _seed(ctx, seed))

    @app.command("market")
    def market(
        quantity: str | None = typer.Option(None, "--quantity", help=", ".join(QUANTITIES)),
        seed: int | None = SeedOption,
        config: Path = ConfigOption,
    ) -> None:
        """Make-me-a-market game on a hidden dice or coin quantity."""
        ctx = start(config)
        _market(ctx, ConsoleIO(), _seed(ctx, seed), quantity)

    @app.command("daily")
    def daily(seed: int | None = SeedOption, config: Path = ConfigOption) -> None:
        """The daily 10 minutes: mental math, one puzzle, one market game."""
        ctx = start(config)
        io = ConsoleIO()
        chosen = _seed(ctx, seed)
        io.say("[bold]Daily session[/bold] 1/3")
        _math(ctx, io, chosen, ctx.cfg.trainer.daily.math_preset, None)
        io.say("\n[bold]Daily session[/bold] 2/3: one puzzle")
        _quiz(ctx, io, chosen)
        io.say("\n[bold]Daily session[/bold] 3/3")
        _market(ctx, io, chosen, None)
        io.say("\nDone for today. Progress: ev stats")

    @app.command("stats")
    def stats_(config: Path = ConfigOption) -> None:
        """Accuracy and speed per category over time, streak, weakest categories."""
        ctx = start(config)
        io = ConsoleIO()
        cfg = ctx.cfg.trainer.stats
        practice = ctx.cfg.paths.practice
        today = datetime.now(UTC).date()
        due = sum(c.days_overdue(today) >= 0 for c in _schedule(ctx).values())
        summary = stats.summarise(
            practice, today, cfg.weakest_window, cfg.weakest_min_answers, len(all_puzzles()), due
        )
        if summary.practice_days == 0:
            io.say("No practice logged yet. Start with: ev daily")
            return
        written = stats.write_report(
            ctx.cfg.paths.reports / "practice", summary, stats.load_math(practice), ctx.info
        )
        io.say(
            f"Streak: {summary.streak} day(s). Math answers: {summary.math_answers}. Puzzles "
            f"solved: {summary.puzzles_solved}/{summary.puzzles_total} "
            f"({summary.reviews_due} review(s) due). Market games: {summary.market_games}."
        )
        if summary.weakest:
            io.say("Weakest categories:")
            for c in summary.weakest:
                io.say(
                    f"  {TITLES[c.category]:28s} {c.accuracy:.0%} correct, "
                    f"median {c.median_seconds:.1f} s ({c.answers} answers)"
                )
        io.say("Written: " + ", ".join(str(p) for p in written))
