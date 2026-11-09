"""Logging goes to a rotating file only; the CLI validates the config."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ev_lab.cli import app
from ev_lab.config import LoggingConfig
from ev_lab.logging_setup import setup_logging

REPO = Path(__file__).resolve().parents[1]
runner = CliRunner()


def test_log_line_has_run_id_and_goes_to_file_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = LoggingConfig(max_bytes=10_000, backup_count=1)
    logger = setup_logging(cfg, tmp_path, "run-xyz")
    logger.info("hello")
    text = (tmp_path / cfg.file).read_text()
    assert "[run=run-xyz] hello" in text
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_setup_is_idempotent(tmp_path: Path) -> None:
    cfg = LoggingConfig(max_bytes=10_000, backup_count=1)
    setup_logging(cfg, tmp_path, "a")
    logger = setup_logging(cfg, tmp_path, "b")
    assert len(logger.handlers) == 1
    logger.info("once")
    assert (tmp_path / cfg.file).read_text().count("once") == 1


def test_log_rotates(tmp_path: Path) -> None:
    cfg = LoggingConfig(max_bytes=300, backup_count=2)
    logger = setup_logging(cfg, tmp_path, "r")
    for i in range(50):
        logger.info("line %d", i)
    assert (tmp_path / f"{cfg.file}.1").exists()
    assert not (tmp_path / f"{cfg.file}.3").exists()


def test_check_config_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    shutil.copy(REPO / "config.yaml", tmp_path / "config.yaml")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["check-config"])
    assert result.exit_code == 0, result.output
    out = json.loads(result.stdout)
    assert out["git_commit"] == "no-git"
    assert len(out["config_hash"]) == 12 and len(out["results_hash"]) == 12
    assert (tmp_path / "logs" / "ev_lab.log").exists()


def test_check_config_fails_on_bad_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "config.yaml").write_text("project: {name: x, offline_only: false}\n")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["check-config"])
    assert result.exit_code == 1


def test_check_config_fails_on_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["check-config"]).exit_code == 1


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.startswith("ev-lab ")
