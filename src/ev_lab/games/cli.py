"""`ev games` and `ev indifference`."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import typer
from rich.console import Console

from ev_lab.context import ConfigOption, Context, start
from ev_lab.games import cfr, kuhn
from ev_lab.games.catalog import GAMES, REGRET_GAMES
from ev_lab.games.indifference import bluff_share, calling_frequency
from ev_lab.games.matrix import solve_zero_sum
from ev_lab.games.regret import regret_matching
from ev_lab.prob.montecarlo import rng_for
from ev_lab.puzzles.grading import parse_number
from ev_lab.reports import games_report

console = Console()
FAMILY_ALPHAS = tuple(Fraction(k, 12) for k in range(5))  # 0, 1/12, ..., 1/3


def build_report(ctx: Context) -> games_report.GamesReport:
    solutions = [(name, solve_zero_sum(a)) for name, a in GAMES.items()]
    by_name = dict(solutions)
    regret_rows = []
    for name in REGRET_GAMES:
        run = regret_matching(
            GAMES[name],
            ctx.cfg.games.regret_iterations,
            rng_for(ctx.cfg.random.seed, f"regret:{name}"),
        )
        lp = by_name[name]
        error = max(
            max(abs(float(a) - float(b)) for a, b in zip(run.row, lp.row, strict=True)),
            max(abs(float(a) - float(b)) for a, b in zip(run.col, lp.col, strict=True)),
        )
        regret_rows.append(
            games_report.RegretRow(name, run.iterations, list(run.row), list(run.col), error)
        )
    solver, checkpoints = cfr.run(ctx.cfg.games.cfr_iterations)
    family = [kuhn.equilibrium(a) for a in FAMILY_ALPHAS]
    return games_report.GamesReport(
        matrix=solutions,
        regret=regret_rows,
        checkpoints=checkpoints,
        strategy=solver.average_strategy(),
        family_alphas=FAMILY_ALPHAS,
        family_values=[kuhn.expected_value(s) for s in family],
        family_exploitabilities=[kuhn.exploitability(s) for s in family],
    )


def register(app: typer.Typer) -> None:
    @app.command("games")
    def games(config: Path = ConfigOption) -> None:
        """Matrix games (LP), regret matching and CFR on Kuhn poker -> reports/games/."""
        ctx = start(config)
        report = build_report(ctx)
        paths = games_report.write(ctx.cfg.paths.reports / "games", report, ctx.info)
        last = report.checkpoints[-1]
        console.print(
            f"Kuhn CFR after {last.iteration:,} iterations: value {last.value:+.6f} "
            f"(theory {float(kuhn.GAME_VALUE):+.6f}), exploitability {last.exploitability:.6f}."
        )
        console.print(
            f"{'All exact checks pass' if report.ok() else 'AN EXACT CHECK FAILED'}. "
            f"Written: {', '.join(str(p) for p in paths)}"
        )
        ctx.logger.info("games report ok=%s exploitability=%.6f", report.ok(), last.exploitability)
        if not report.ok():
            raise typer.Exit(code=1)

    @app.command("indifference")
    def indifference(
        pot: str = typer.Option(..., "--pot", help="Pot before the bet."),
        bet: str = typer.Option(..., "--bet", help="Size of the bet."),
        config: Path = ConfigOption,
    ) -> None:
        """Bluff share and calling frequency that make the opponent indifferent."""
        start(config)
        try:
            p, b = parse_number(pot), parse_number(bet)
            share, call = bluff_share(p, b), calling_frequency(p, b)
        except ValueError as e:
            console.print(f"[red]error:[/red] {e}")
            raise typer.Exit(code=2) from e
        console.print(
            f"Bluffs in the betting range: {share} = {float(share):.2%}  (B / (P + 2B)): "
            "the caller is then indifferent between calling and folding."
        )
        console.print(
            f"Calling frequency: {call} = {float(call):.2%}  (P / (P + B)): "
            "a pure bluff then breaks even."
        )
