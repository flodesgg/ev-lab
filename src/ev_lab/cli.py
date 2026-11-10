"""Command-line entry point: `ev <command>`.

Commands
  check-config        validate config.yaml and print run metadata
  puzzle list         list puzzles (never shows answers)
  puzzle try ID       attempt a puzzle: your answer first, then the solution
  puzzle check-all    exact vs Monte Carlo for every puzzle -> reports/puzzles/
  puzzle bias-check   the same on many seeds: is any simulator biased?
  daily               the daily 10 minutes: mental math, one puzzle, one market game
  math                timed mental math (N questions in M minutes)
  quiz                one probability puzzle, unseen or previously wrong first
  market              make-me-a-market game with a noise and an informed trader
  stats               practice statistics -> reports/practice/
  web                 the trainer as a local web page (127.0.0.1 only)
  equity H1 H2 ...    Hold'em equity of hands or ranges (exact or Monte Carlo)
  pot-odds            EV of a call from equity, pot and bet size
  games               matrix games, regret matching, Kuhn CFR -> reports/games/
  leduc               CFR+ vs vanilla CFR on Leduc hold'em -> reports/games/
  indifference        bluff share and calling frequency for a pot and a bet
  kelly               Kelly growth, simulated bet sizes, estimated edge -> reports/kelly/
  kelly-bet           Kelly fraction for one bet
  cards-cpp           build and check the C++ evaluator -> reports/cards/
  cards-check         evaluator and equity checks -> reports/cards/ (--full: all 7-card hands)
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from ev_lab import __version__
from ev_lab.cards.cli import register as register_cards
from ev_lab.context import ConfigOption, start
from ev_lab.games.cli import register as register_games
from ev_lab.kelly.cli import register as register_kelly
from ev_lab.puzzles.cli import puzzle_app
from ev_lab.trainer.cli import register as register_trainer
from ev_lab.web.cli import register as register_web

app = typer.Typer(
    help="EV Lab: exact probability, game theory and bet sizing (offline study only).",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(puzzle_app, name="puzzle")
register_trainer(app)
register_web(app)
register_cards(app)
register_games(app)
register_kelly(app)


def _version(value: bool) -> None:
    if value:
        typer.echo(f"ev-lab {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False, "--version", callback=_version, is_eager=True, help="Show the version and exit."
    ),
) -> None:
    """Root options."""


@app.command("check-config")
def check_config(config: Path = ConfigOption) -> None:
    """Validate config.yaml and print run metadata as JSON."""
    ctx = start(config)
    results_hash = ctx.cfg.results_hash()
    ctx.logger.info("config ok: hash=%s results_hash=%s", ctx.info.config_hash, results_hash)
    typer.echo(json.dumps({**ctx.info.as_dict(), "results_hash": results_hash}, indent=2))


def main() -> None:
    app()
