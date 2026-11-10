"""`ev equity` and `ev pot-odds`."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import typer
from rich.console import Console
from rich.table import Table

from ev_lab.cards import cpp
from ev_lab.cards.deck import cards_str, parse_cards
from ev_lab.cards.equity import equity_exact, equity_mc, exact_scenarios
from ev_lab.cards.evaluator import rank7_oracle
from ev_lab.cards.fast import category_counts, evaluate
from ev_lab.cards.potodds import breakeven_equity, call_ev
from ev_lab.cards.ranges import Combo, parse_range
from ev_lab.context import ConfigOption, Context, start
from ev_lab.prob.montecarlo import rng_for
from ev_lab.puzzles.grading import parse_number
from ev_lab.reports import cards_check, cpp_check

console = Console()


def parse_player(text: str) -> list[Combo]:
    """A specific hand ('AhKh') or a range ('TT+,AQs+')."""
    return parse_range(text)


def _describe(text: str, combos: list[Combo]) -> str:
    return cards_str(combos[0]) if len(combos) == 1 else f"{text} ({len(combos)} combos)"


# Matchups for the exact-vs-Monte-Carlo section of the report: (label, hands, board).
CHECK_MATCHUPS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("AhKh vs QsQd, preflop", ("AhKh", "QsQd"), ""),
    ("AhKh vs QsQd on 2c7d9h", ("AhKh", "QsQd"), "2c7d9h"),
    ("9h8h vs AsAd vs KcQc on ThJh2c", ("9h8h", "AsAd", "KcQc"), "ThJh2c"),
    ("AhKh vs TT+,AQs+ on 2c7d9h", ("AhKh", "TT+,AQs+"), "2c7d9h"),
)
ORACLE_SAMPLE = 100_000


def build_check(ctx: Context, full: bool) -> cards_check.CardsCheck:
    seed = ctx.cfg.random.seed
    hands = rng_for(seed, "cards-check:oracle").permuted(
        np.tile(np.arange(52), (ORACLE_SAMPLE, 1)), axis=1
    )[:, :7]
    fast = evaluate(hands).tolist()
    mismatches = sum(f != rank7_oracle(h) for f, h in zip(fast, hands.tolist(), strict=True))
    rows = []
    for label, players, board in CHECK_MATCHUPS:
        ranges = [parse_player(p) for p in players]
        exact = equity_exact(ranges, parse_cards(board))
        sim = equity_mc(
            ranges,
            parse_cards(board),
            ctx.cfg.cards.mc_trials,
            rng_for(seed, f"cards-check:{label}"),
        )
        rows.append(
            cards_check.EquityRow(
                label, exact.scenarios, exact.players[0].equity, sim.players[0].equity
            )
        )
    return cards_check.CardsCheck(
        five_counts=category_counts(5),
        seven_counts=category_counts(7) if full else None,
        oracle_hands=ORACLE_SAMPLE,
        oracle_mismatches=mismatches,
        equities=rows,
        tol_se=ctx.cfg.monte_carlo.tolerance_se,
    )


CPP_NUMPY_SAMPLE = 1_000_000
CPP_BENCH_HANDS = 20_000_000


def build_cpp_check(ctx: Context) -> cpp_check.CppCheck:
    rng = rng_for(ctx.cfg.random.seed, "cards-cpp")
    hands = rng.permuted(np.tile(np.arange(52), (CPP_NUMPY_SAMPLE, 1)), axis=1)[:, :7]
    started = time.perf_counter()
    numpy_values = evaluate(hands)
    numpy_seconds = time.perf_counter() - started
    cpp_values = cpp.evaluate(hands)
    sample = hands[:ORACLE_SAMPLE].tolist()
    oracle = [rank7_oracle(h) for h in sample]
    seven = cpp.category_counts(7)
    return cpp_check.CppCheck(
        five_counts=cpp.category_counts(5).counts,
        seven_counts=seven.counts,
        seven_seconds=seven.seconds,
        oracle_hands=ORACLE_SAMPLE,
        oracle_mismatches=sum(a != b for a, b in zip(cpp_values.tolist(), oracle, strict=False)),
        numpy_hands=CPP_NUMPY_SAMPLE,
        numpy_mismatches=int((cpp_values != numpy_values).sum()),
        cpp_hands_per_second=cpp.benchmark(CPP_BENCH_HANDS),
        numpy_hands_per_second=CPP_NUMPY_SAMPLE / numpy_seconds,
    )


def register(app: typer.Typer) -> None:
    @app.command("cards-cpp")
    def cards_cpp(config: Path = ConfigOption) -> None:
        """Build the C++ evaluator and check it -> reports/cards/cpp_check.md."""
        ctx = start(config)
        try:
            check = build_cpp_check(ctx)
        except cpp.CppUnavailableError as e:
            console.print(f"[red]error:[/red] {e}")
            raise typer.Exit(code=2) from e
        path = cpp_check.write(ctx.cfg.paths.reports / "cards", cpp_check.render(check, ctx.info))
        console.print(
            f"{'All checks pass' if check.ok() else 'A CHECK FAILED'}. C++ "
            f"{check.cpp_hands_per_second:,.0f} hands/s. Report: {path}"
        )
        ctx.logger.info("cards-cpp ok=%s", check.ok())
        if not check.ok():
            raise typer.Exit(code=1)

    @app.command("cards-check")
    def cards_check_(
        full: bool = typer.Option(False, "--full", help="Also enumerate all 7-card hands (slow)."),
        config: Path = ConfigOption,
    ) -> None:
        """Evaluator and equity checks, written to reports/cards/cards_check.md."""
        ctx = start(config)
        check = build_check(ctx, full)
        path = cards_check.write(
            ctx.cfg.paths.reports / "cards", cards_check.render(check, ctx.info)
        )
        console.print(f"{'All checks pass' if check.ok() else 'A CHECK FAILED'}. Report: {path}")
        ctx.logger.info("cards-check full=%s ok=%s", full, check.ok())
        if not check.ok():
            raise typer.Exit(code=1)

    @app.command("equity")
    def equity(
        players: list[str] = typer.Argument(..., help="Hands or ranges: AhKh QsQd 'TT+,AQs+'"),
        board: str = typer.Option("", "--board", help="0 to 5 board cards, e.g. 2c7d9h"),
        exact: bool = typer.Option(False, "--exact", help="Force exact enumeration."),
        mc: int | None = typer.Option(None, "--mc", min=1000, help="Monte Carlo with N trials."),
        config: Path = ConfigOption,
    ) -> None:
        """Texas Hold'em equity (ties split) for two or more hands or ranges."""
        ctx = start(config)
        if exact and mc is not None:
            console.print("choose either --exact or --mc N, not both")
            raise typer.Exit(code=2)
        try:
            board_cards = parse_cards(board)
            ranges = [parse_player(p) for p in players]
            scenarios = exact_scenarios(ranges, board_cards)
            use_exact = exact or (mc is None and scenarios <= ctx.cfg.cards.exact_limit)
            table = Table(title=f"Equity  (board: {cards_str(board_cards) or 'none'})")
            for column in ("player", "win", "tie", "loss", "equity"):
                table.add_column(column)
            if use_exact:
                result = equity_exact(ranges, board_cards)
                for text, combos, p in zip(players, ranges, result.players, strict=True):
                    table.add_row(
                        _describe(text, combos),
                        f"{float(p.win):.4%}",
                        f"{float(p.tie):.4%}",
                        f"{float(p.loss):.4%}",
                        f"{float(p.equity):.4%}  = {p.equity}",
                    )
                note = f"Exact: {result.scenarios:,} scenarios enumerated."
            else:
                trials = mc if mc is not None else ctx.cfg.cards.mc_trials
                rng = rng_for(ctx.cfg.random.seed, "equity:" + "|".join([*players, board]))
                sim = equity_mc(ranges, board_cards, trials, rng)
                for text, combos, q in zip(players, ranges, sim.players, strict=True):
                    table.add_row(
                        _describe(text, combos),
                        f"{q.win:.2%}",
                        f"{q.tie:.2%}",
                        f"{q.loss:.2%}",
                        f"{q.equity.estimate:.2%} ± {q.equity.se:.2%} (SE)",
                    )
                note = (
                    f"Monte Carlo: {sim.trials:,} accepted trials of {trials:,} "
                    f"(seed {ctx.cfg.random.seed}). Exact would need {scenarios:,} scenarios; "
                    "force it with --exact."
                )
        except ValueError as e:
            console.print(f"[red]error:[/red] {e}")
            raise typer.Exit(code=2) from e
        console.print(table)
        console.print(note)
        ctx.logger.info("equity %s board=%s exact=%s", players, board, use_exact)

    @app.command("pot-odds")
    def pot_odds(
        pot: str = typer.Option(..., "--pot", help="In the middle now, including the bet."),
        call: str = typer.Option(..., "--call", help="What I must put in to call."),
        equity_text: str | None = typer.Option(None, "--equity", help="My equity, e.g. 0.35."),
        config: Path = ConfigOption,
    ) -> None:
        """Break-even equity for a call, and the call's EV if my equity is given."""
        start(config)
        try:
            p, c = parse_number(pot), parse_number(call)
            need = breakeven_equity(p, c)
            console.print(f"Break-even equity: {need} = {float(need):.2%}  (call / (pot + call))")
            if equity_text is not None:
                e = parse_number(equity_text)
                ev = call_ev(e, p, c)
                verdict = "call" if ev > 0 else "fold" if ev < 0 else "indifferent"
                console.print(
                    f"EV of calling with {float(e):.2%} equity: {float(ev):+.4f}  ({verdict})"
                )
        except ValueError as e:
            console.print(f"[red]error:[/red] {e}")
            raise typer.Exit(code=2) from e
