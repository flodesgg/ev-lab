"""Config loading: the committed file is valid, bad files are rejected."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from ev_lab.config import Config, config_hash, load_config

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def raw() -> dict[str, Any]:
    with (REPO / "config.yaml").open() as f:
        loaded = yaml.safe_load(f)
    assert isinstance(loaded, dict)
    return loaded


def _write(tmp_path: Path, raw: dict[str, Any]) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump(raw))
    return p


def test_committed_config_is_valid() -> None:
    cfg, cfg_hash = load_config(REPO / "config.yaml")
    assert cfg.project.name == "ev-lab"
    assert cfg.project.offline_only is True
    assert len(cfg_hash) == 12


def test_unknown_key_is_rejected(raw: dict[str, Any], tmp_path: Path) -> None:
    raw["monte_carlo"]["trails"] = 10_000  # typo of "trials"
    with pytest.raises(ValidationError, match="trails"):
        load_config(_write(tmp_path, raw))


def test_offline_only_cannot_be_disabled(raw: dict[str, Any], tmp_path: Path) -> None:
    raw["project"]["offline_only"] = False
    with pytest.raises(ValidationError, match="offline_only must be true"):
        load_config(_write(tmp_path, raw))


def test_config_is_frozen(raw: dict[str, Any]) -> None:
    cfg = Config.model_validate(raw)
    with pytest.raises(ValidationError):
        cfg.random.seed = 1  # type: ignore[misc]


def test_top_level_must_be_mapping(tmp_path: Path) -> None:
    p = tmp_path / "config.yaml"
    p.write_text("- just\n- a list\n")
    with pytest.raises(ValueError, match="top level must be a mapping"):
        load_config(p)


def test_hash_ignores_key_order_and_sees_changes(raw: dict[str, Any]) -> None:
    reordered = dict(reversed(list(raw.items())))
    assert config_hash(raw) == config_hash(reordered)
    changed = copy.deepcopy(raw)
    changed["random"]["seed"] += 1
    assert config_hash(raw) != config_hash(changed)


def test_results_hash_ignores_paths_and_logging(raw: dict[str, Any]) -> None:
    base = Config.model_validate(raw)
    moved = copy.deepcopy(raw)
    moved["paths"]["logs"] = "elsewhere"
    moved["logging"]["level"] = "DEBUG"
    assert Config.model_validate(moved).results_hash() == base.results_hash()
    reseeded = copy.deepcopy(raw)
    reseeded["random"]["seed"] += 1
    assert Config.model_validate(reseeded).results_hash() != base.results_hash()


def test_yaml_bare_off_is_a_boolean_not_a_string() -> None:
    # the pitfall noted in config.yaml: this is why string values are quoted
    assert yaml.safe_load("mode: off") == {"mode": False}
    assert yaml.safe_load('mode: "off"') == {"mode": "off"}
