"""Reproducibility metadata attached to every generated report."""

from __future__ import annotations

import subprocess
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

OUTPUT_DIRS = ("reports", "practice")


@dataclass(frozen=True)
class RunInfo:
    run_id: str
    started_utc: str
    git_commit: str
    git_dirty: bool
    config_hash: str
    seed: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def markdown_footer(self) -> str:
        """One line for the bottom of a generated report."""
        dirty = " (dirty)" if self.git_dirty else ""
        return (
            f"_run {self.run_id} · commit {self.git_commit}{dirty} · "
            f"config {self.config_hash} · seed {self.seed}_"
        )


def _git(args: list[str], cwd: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, check=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip()


def new_run_info(config_hash: str, seed: int, repo: Path = Path(".")) -> RunInfo:
    now = datetime.now(UTC)
    commit = _git(["rev-parse", "--short=12", "HEAD"], repo) or "no-git"
    # "dirty" is about code and config. Generated outputs (reports, practice logs) change
    # with every run and must not mark the code that produced them as modified.
    status = _git(
        ["status", "--porcelain", "--", ".", *(f":(exclude){d}" for d in OUTPUT_DIRS)], repo
    )
    return RunInfo(
        run_id=f"{now:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6]}",
        started_utc=now.isoformat(timespec="seconds"),
        git_commit=commit,
        git_dirty=bool(status),
        config_hash=config_hash,
        seed=seed,
    )
