"""Load and validate config.yaml.

All parameters live in config.yaml; code reads them only through `load_config`.
Unknown keys are rejected so a typo cannot silently fall back to a default.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DEFAULT_CONFIG_PATH = Path("config.yaml")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProjectConfig(_Strict):
    name: str
    offline_only: bool

    @field_validator("offline_only")
    @classmethod
    def _must_be_offline(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "offline_only must be true: this lab never connects to gambling sites "
                "or supports real-money play"
            )
        return v


class PathsConfig(_Strict):
    practice: Path
    reports: Path
    logs: Path
    data: Path


class LoggingConfig(_Strict):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    file: str = "ev_lab.log"
    max_bytes: int = Field(gt=0)
    backup_count: int = Field(ge=0)


class RandomConfig(_Strict):
    seed: int = Field(ge=0)


class MonteCarloConfig(_Strict):
    trials: int = Field(ge=1000)
    tolerance_se: float = Field(gt=0, le=6)


class PuzzlesConfig(_Strict):
    rel_tolerance: float = Field(gt=0, le=0.05)


class MathPreset(_Strict):
    questions: int = Field(ge=1, le=500)
    minutes: float = Field(gt=0, le=60)


class MathConfig(_Strict):
    default_preset: str
    level: Literal[1, 2, 3]
    adaptive_window: int = Field(ge=5)
    presets: dict[str, MathPreset] = Field(min_length=1)

    @model_validator(mode="after")
    def _default_exists(self) -> MathConfig:
        if self.default_preset not in self.presets:
            raise ValueError(f"default_preset {self.default_preset!r} is not in presets")
        return self


class MarketConfig(_Strict):
    informed_prob: float = Field(ge=0, le=1)
    width_fracs: list[float] = Field(min_length=1)
    min_width: int = Field(ge=1)

    @field_validator("width_fracs")
    @classmethod
    def _fractions_of_range(cls, v: list[float]) -> list[float]:
        if any(not 0 < f <= 1 for f in v):
            raise ValueError("width_fracs must lie in (0, 1]")
        return v


class DailyConfig(_Strict):
    math_preset: str


class StatsConfig(_Strict):
    weakest_window: int = Field(ge=10)
    weakest_min_answers: int = Field(ge=1)


class TrainerConfig(_Strict):
    math: MathConfig
    market: MarketConfig
    daily: DailyConfig
    stats: StatsConfig

    @model_validator(mode="after")
    def _daily_preset_exists(self) -> TrainerConfig:
        if self.daily.math_preset not in self.math.presets:
            raise ValueError(f"daily.math_preset {self.daily.math_preset!r} is not in presets")
        return self


class CardsConfig(_Strict):
    exact_limit: int = Field(ge=1)
    mc_trials: int = Field(ge=1000)


class GamesConfig(_Strict):
    regret_iterations: int = Field(ge=100)
    cfr_iterations: int = Field(ge=10)


# Sections that change computed numbers (not paths or logging).
RESULT_SECTIONS = ("random", "monte_carlo", "cards", "games")


class Config(_Strict):
    project: ProjectConfig
    paths: PathsConfig
    logging: LoggingConfig
    random: RandomConfig
    monte_carlo: MonteCarloConfig
    puzzles: PuzzlesConfig
    trainer: TrainerConfig
    cards: CardsConfig
    games: GamesConfig

    def results_hash(self) -> str:
        """Hash of everything that changes generated numbers. Two reports with the same
        results hash and git commit must be identical."""
        dumped = self.model_dump(mode="json")
        return config_hash({k: dumped[k] for k in RESULT_SECTIONS})


def config_hash(raw: dict[str, object]) -> str:
    """Stable short hash of the config content (key order independent)."""
    canonical = json.dumps(raw, sort_keys=True, default=str).encode()
    return hashlib.sha256(canonical).hexdigest()[:12]


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> tuple[Config, str]:
    """Read, validate and hash the config. Raises on any invalid value."""
    p = Path(path)
    with p.open() as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ValueError(f"{p}: top level must be a mapping")
    return Config.model_validate(raw), config_hash(raw)
