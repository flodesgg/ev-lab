"""Command-line entry point: `ev <command>`.

Commands
  check-config    validate config.yaml and print run metadata
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from pydantic import ValidationError

from ev_lab import __version__
from ev_lab.config import DEFAULT_CONFIG_PATH, load_config
from ev_lab.logging_setup import setup_logging
from ev_lab.runinfo import new_run_info

app = typer.Typer(
    help="EV Lab: exact probability, game theory and bet sizing (offline study only).",
    no_args_is_help=True,
    add_completion=False,
)


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
    """Root options (keeps `ev <command>` form even while there is a single command)."""


@app.command("check-config")
def check_config(
    config: Path = typer.Option(DEFAULT_CONFIG_PATH, "--config", help="Path to config.yaml."),
) -> None:
    """Validate config.yaml and print run metadata as JSON."""
    try:
        cfg, cfg_hash = load_config(config)
    except (OSError, ValueError, ValidationError) as e:
        typer.echo(f"config error: {e}", err=True)
        raise typer.Exit(code=1) from e
    info = new_run_info(cfg_hash, cfg.random.seed)
    logger = setup_logging(cfg.logging, cfg.paths.logs, info.run_id)
    logger.info("config ok: hash=%s results_hash=%s", cfg_hash, cfg.results_hash())
    typer.echo(json.dumps({**info.as_dict(), "results_hash": cfg.results_hash()}, indent=2))


def main() -> None:
    app()
