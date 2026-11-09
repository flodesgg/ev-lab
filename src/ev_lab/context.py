"""What every command needs: the validated config, run metadata and the logger."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import typer
from pydantic import ValidationError

from ev_lab.config import DEFAULT_CONFIG_PATH, Config, load_config
from ev_lab.logging_setup import setup_logging
from ev_lab.runinfo import RunInfo, new_run_info

ConfigOption = typer.Option(DEFAULT_CONFIG_PATH, "--config", help="Path to config.yaml.")


@dataclass(frozen=True)
class Context:
    cfg: Config
    info: RunInfo
    logger: logging.Logger


def start(config_path: Path) -> Context:
    """Load the config or exit with code 1 and a readable message."""
    try:
        cfg, cfg_hash = load_config(config_path)
    except (OSError, ValueError, ValidationError) as e:
        typer.echo(f"config error: {e}", err=True)
        raise typer.Exit(code=1) from e
    info = new_run_info(cfg_hash, cfg.random.seed)
    logger = setup_logging(cfg.logging, cfg.paths.logs, info.run_id)
    return Context(cfg=cfg, info=info, logger=logger)
