"""`ev kelly` (report) and `ev kelly-bet` (calculator)."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import typer
from rich.console import Console

from ev_lab.context import ConfigOption, Context, start
from ev_lab.kelly.core import growth_rate, kelly_bet, kelly_fraction
from ev_lab.kelly.simulate import simulate
from ev_lab.kelly.uncertainty import uncertainty_table
from ev_lab.prob.montecarlo import rng_for
from ev_lab.puzzles.grading import parse_number
from ev_lab.reports import kelly_report

console = Console()


def build_report(ctx: Context) -> kelly_report.KellyReport:
    cfg = ctx.cfg.kelly
    p = Fraction(cfg.p).limit_denominator(10_000)
    odds = Fraction(cfg.odds).limit_denominator(10_000)
    kelly = kelly_fraction(p, odds)
    results = simulate(
        cfg.p,
        cfg.odds,
        float(kelly),
        cfg.multiples,
        cfg.bets,
        cfg.paths,
        cfg.ruin_level,
        cfg.drawdown_level,
        rng_for(ctx.cfg.random.seed, "kelly:paths"),
    )
    return kelly_report.KellyReport(
        p=cfg.p,
        odds=cfg.odds,
        kelly=kelly,
        bets=cfg.bets,
        paths=cfg.paths,
        ruin_level=cfg.ruin_level,
        drawdown_level=cfg.drawdown_level,
        max_fraction=cfg.max_fraction,
        tol_se=ctx.cfg.monte_carlo.tolerance_se,
        results=results,
        uncertainty=uncertainty_table(cfg.sample_sizes, cfg.p, cfg.odds, cfg.max_fraction),
    )


def register(app: typer.Typer) -> None:
    @app.command("kelly")
    def kelly(config: Path = ConfigOption) -> None:
        """Kelly growth curve, simulated bet sizes, estimated edge -> reports/kelly/."""
        ctx = start(config)
        report = build_report(ctx)
        paths = kelly_report.write(ctx.cfg.paths.reports / "kelly", report, ctx.info)
        ok = report.growth_checks_pass()
        console.print(
            f"Kelly fraction {report.kelly} = {float(report.kelly):.4f}. Simulated growth "
            f"matches g(f): {'yes' if ok else 'NO'}. Written: {', '.join(str(p) for p in paths)}"
        )
        ctx.logger.info("kelly report growth_checks=%s", ok)
        if not ok:
            raise typer.Exit(code=1)

    @app.command("kelly-bet")
    def kelly_bet_(
        p: str = typer.Option(..., "--p", help="Win probability, e.g. 0.55 or 11/20."),
        odds: str = typer.Option("1", "--odds", help="Net odds b: profit per 1 staked."),
        config: Path = ConfigOption,
    ) -> None:
        """Kelly fraction and growth rate for one binary bet."""
        start(config)
        try:
            pp, b = parse_number(p, percent_divides=True), parse_number(odds)
            raw, stake = kelly_fraction(pp, b), kelly_bet(pp, b)
        except ValueError as e:
            console.print(f"[red]error:[/red] {e}")
            raise typer.Exit(code=2) from e
        console.print(f"f* = p - (1 - p)/b = {raw} = {float(raw):.4f}")
        if stake == 0:
            console.print("No positive edge: the Kelly bet is 0.")
            return
        for label, f in (("full Kelly", stake), ("half Kelly", stake / 2)):
            if f < 1:
                g = growth_rate(float(f), float(pp), float(b))
                console.print(f"{label}: stake {float(f):.2%} of wealth, growth {g:+.6f} per bet")
            else:
                console.print(f"{label}: stake {float(f):.2%} of wealth (a sure win)")
