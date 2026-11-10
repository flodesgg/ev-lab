"""`ev games` and `ev indifference`."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import typer
from rich.console import Console

from ev_lab.context import ConfigOption, Context, start
from ev_lab.games import cfr, kuhn, leduc, leduc_cfr
from ev_lab.games.catalog import GAMES, REGRET_GAMES
from ev_lab.games.indifference import bluff_share, calling_frequency
from ev_lab.games.matrix import solve_zero_sum
from ev_lab.games.regret import regret_matching
from ev_lab.prob.montecarlo import rng_for
from ev_lab.puzzles.grading import parse_number
from ev_lab.reports import games_report, leduc_report

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


def _seat_plays(pure: dict[int, leduc_cfr.FloatArray], seat: int) -> leduc_cfr.Policy:
    """`seat` follows the given pure policy; the other player the average strategy."""

    def policy(node: leduc_cfr.Node) -> leduc_cfr.FloatArray:
        return pure[id(node)] if node.player == seat else node.average_strategy()

    return policy


def build_leduc_report(iterations: int) -> leduc_report.LeducReport:
    schedule = cfr.checkpoint_schedule(iterations)
    solver, plus = leduc_cfr.run(iterations, True, schedule)
    _, vanilla = leduc_cfr.run(iterations, False, schedule)
    fresh = leduc_cfr.LeducSolver()  # no iterations yet: both players uniformly random
    table = solver.strategy_table()
    achieved = []
    for seat in (0, 1):
        # a pure best response of this seat, played against the average strategy of the other
        pure = leduc_cfr.best_response_policy(solver.root, seat, solver.average)
        mixed = solver.strategy_table(_seat_plays(pure, seat))
        to_p1 = float(leduc.expected_value(mixed))
        achieved.append(to_p1 if seat == 0 else -to_p1)
    return leduc_report.LeducReport(
        infosets=len(leduc.all_infosets()),
        card_level_infosets=leduc.card_level_infoset_count(),
        public_nodes=len(solver.nodes),
        uniform_value_exact=Fraction(leduc.expected_value(leduc.uniform_strategy())),
        uniform_value_fast=fresh.value(),
        plus=plus,
        vanilla=vanilla,
        value_fast=solver.value(),
        value_slow=float(leduc.expected_value(table)),
        br_achieved=(achieved[0], achieved[1]),
        br_claimed=(solver.best_response_value(0), solver.best_response_value(1)),
    )


def register(app: typer.Typer) -> None:
    @app.command("leduc")
    def leduc_(config: Path = ConfigOption) -> None:
        """CFR+ against vanilla CFR on Leduc hold'em -> reports/games/leduc.md."""
        ctx = start(config)
        report = build_leduc_report(ctx.cfg.games.leduc_iterations)
        paths = leduc_report.write(ctx.cfg.paths.reports / "games", report, ctx.info)
        last = report.plus[-1]
        console.print(
            f"Leduc CFR+ after {last.iteration:,} iterations: exploitability "
            f"{last.exploitability:.6f}, value {last.value:+.6f}. Cross-checks "
            f"{'agree' if report.ok() else 'DISAGREE'}. Written: {', '.join(str(p) for p in paths)}"
        )
        ctx.logger.info("leduc report ok=%s exploitability=%.6f", report.ok(), last.exploitability)
        if not report.ok():
            raise typer.Exit(code=1)

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
