"""Run metadata: shape of the run id, behaviour inside and outside a git repo."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ev_lab.runinfo import new_run_info


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def test_outside_git_reports_no_git(tmp_path: Path) -> None:
    info = new_run_info("abc123abc123", seed=7, repo=tmp_path)
    assert info.git_commit == "no-git"
    assert info.git_dirty is False
    assert info.seed == 7
    assert re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{6}", info.run_id)


def test_inside_git_reports_commit_and_dirty_flag(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    (tmp_path / "a.txt").write_text("a")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "a")

    clean = new_run_info("h", seed=1, repo=tmp_path)
    assert re.fullmatch(r"[0-9a-f]{12}", clean.git_commit)
    assert clean.git_dirty is False

    (tmp_path / "b.txt").write_text("b")
    assert new_run_info("h", seed=1, repo=tmp_path).git_dirty is True


def test_run_ids_are_unique() -> None:
    ids = {new_run_info("h", seed=1).run_id for _ in range(20)}
    assert len(ids) == 20


def test_footer_carries_everything_needed_to_reproduce(tmp_path: Path) -> None:
    info = new_run_info("cfghash", seed=42, repo=tmp_path)
    footer = info.markdown_footer()
    for part in (info.run_id, info.git_commit, "cfghash", "seed 42"):
        assert part in footer
