"""`ev puzzle ...` commands. The answer is always asked for before anything is revealed."""

from __future__ import annotations

import time
from fractions import Fraction
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ev_lab.context import ConfigOption, Context, start
from ev_lab.prob.montecarlo import McResult, rng_for, run_mc
from ev_lab.puzzles.base import TAGS, Puzzle, format_answer
from ev_lab.puzzles.grading import (
    market_feedback,
    market_is_correct,
    number_is_correct,
    parse_number,
)
from ev_lab.puzzles.log import attempts_by_puzzle, log_attempt
from ev_lab.puzzles.registry import all_puzzles, get_puzzle
from ev_lab.reports import puzzle_check

puzzle_app = typer.Typer(help="Probability and expected-value puzzles.", no_args_is_help=True)
console = Console()


def simulate_puzzle(puzzle: Puzzle, ctx: Context) -> McResult:
    """The puzzle's own reproducible stream: depends only on the root seed and the id."""
    rng = rng_for(ctx.cfg.random.seed, f"puzzle:{puzzle.id}")
    return run_mc(puzzle.simulate, ctx.cfg.monte_carlo.trials, rng)


@puzzle_app.command("list")
def list_(
    tag: str | None = typer.Option(None, "--tag", help="Part of a tag name, e.g. 'markov'."),
    difficulty: int | None = typer.Option(None, "--difficulty", min=1, max=3),
    config: Path = ConfigOption,
) -> None:
    """List puzzles and my status on each. Never shows answers."""
    ctx = start(config)
    if tag is not None and not any(tag.lower() in t.lower() for t in TAGS):
        console.print(f"unknown tag {tag!r}; tags: {', '.join(TAGS)}")
        raise typer.Exit(code=2)
    attempts = attempts_by_puzzle(ctx.cfg.paths.practice)
    table = Table(title="Puzzles")
    for column in ("id", "title", "diff", "tags", "status"):
        table.add_column(column)
    shown = 0
    for p in all_puzzles():
        if difficulty is not None and p.difficulty != difficulty:
            continue
        if tag is not None and not any(tag.lower() in t.lower() for t in p.tags):
            continue
        a = attempts.get(p.id)
        if a is None:
            status = "practice: to do" if p.practice_pending else "new"
        else:
            status = f"solved ({a.count} tries)" if a.solved else f"not yet ({a.count} tries)"
        table.add_row(p.id, p.title, str(p.difficulty), ", ".join(p.tags), status)
        shown += 1
    console.print(table)
    console.print(f"{shown} of {len(all_puzzles())} puzzles. Try one: ev puzzle try <id>")


def _ask(prompt: str) -> tuple[Fraction, str]:
    while True:
        text = str(typer.prompt(prompt))
        try:
            return parse_number(text), text.strip()
        except ValueError as e:
            console.print(f"[yellow]{e}[/yellow]")


@puzzle_app.command("try")
def try_(puzzle_id: str, config: Path = ConfigOption) -> None:
    """Attempt a puzzle: statement, my answer, and only then the solution."""
    ctx = start(config)
    try:
        puzzle = get_puzzle(puzzle_id)
    except KeyError:
        console.print(f"unknown puzzle {puzzle_id!r}; see: ev puzzle list")
        raise typer.Exit(code=2) from None

    console.print(
        Panel(puzzle.statement, title=f"{puzzle.title}  (difficulty {puzzle.difficulty})")
    )
    started = time.monotonic()
    if puzzle.kind == "market":
        assert puzzle.max_width is not None
        bid, bid_text = _ask("Your bid")
        ask, ask_text = _ask("Your ask")
        answer_text = f"{bid_text} @ {ask_text}"
    else:
        answer, answer_text = _ask("Your answer (fraction or decimal)")
    seconds = time.monotonic() - started

    exact = puzzle.solve()
    if puzzle.kind == "market":
        assert puzzle.max_width is not None
        correct = market_is_correct(bid, ask, exact, puzzle.max_width)
        detail = market_feedback(bid, ask, exact, puzzle)
    else:
        correct = number_is_correct(answer, exact, ctx.cfg.puzzles.rel_tolerance)
        detail = f"tolerance {ctx.cfg.puzzles.rel_tolerance:.1%} of the exact value"
    log_attempt(ctx.cfg.paths.practice, ctx.info.run_id, puzzle.id, answer_text, correct, seconds)
    ctx.logger.info("puzzle %s attempted: correct=%s seconds=%.1f", puzzle.id, correct, seconds)

    verdict = "[green]Correct[/green]" if correct else "[red]Not correct[/red]"
    console.print(f"\n{verdict} ({detail}). Time: {seconds:.0f} s.\n")
    console.print(
        Panel(puzzle.explanation.format(answer=format_answer(exact)), title="Explanation")
    )
    mc = simulate_puzzle(puzzle, ctx)
    console.print(f"Exact:        {format_answer(exact)}")
    console.print(
        f"Monte Carlo:  {mc.estimate:.5f} ± {mc.se:.5f} (SE), n = {mc.n:,}, z = {mc.z(exact):+.2f}"
    )


@puzzle_app.command("check-all")
def check_all(config: Path = ConfigOption) -> None:
    """Exact vs Monte Carlo for every puzzle, written to reports/puzzles/check_all.md."""
    ctx = start(config)
    attempts = attempts_by_puzzle(ctx.cfg.paths.practice)
    rows = [
        puzzle_check.CheckRow(p, p.solve(), simulate_puzzle(p, ctx), attempted=p.id in attempts)
        for p in all_puzzles()
    ]
    tol = ctx.cfg.monte_carlo.tolerance_se
    text = puzzle_check.render(rows, ctx.info, ctx.cfg.monte_carlo.trials, tol)
    path = puzzle_check.write(ctx.cfg.paths.reports / "puzzles", text)
    failed = [r.puzzle.id for r in rows if not r.ok(tol)]
    ctx.logger.info("check-all: %d puzzles, %d disagree", len(rows), len(failed))
    console.print(
        f"{len(rows)} puzzles: exact and Monte Carlo agree on {len(rows) - len(failed)}, "
        f"disagree on {len(failed)}. Report: {path}"
    )
    if failed:
        console.print(f"[red]disagree:[/red] {', '.join(failed)}")
        raise typer.Exit(code=1)
