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
from pydantic import BaseModel, ConfigDict, Field, field_validator

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


# Sections that change computed numbers (not paths or logging).
RESULT_SECTIONS = ("random", "monte_carlo")


class Config(_Strict):
    project: ProjectConfig
    paths: PathsConfig
    logging: LoggingConfig
    random: RandomConfig
    monte_carlo: MonteCarloConfig

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
