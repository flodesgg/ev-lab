"""Append-only CSV logs of my practice answers.

A log is never rewritten: rows are only added at the end. The header is checked on every
write, so a changed column layout fails loudly instead of silently corrupting the history.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path


class LogHeaderError(ValueError):
    pass


def _existing_header(path: Path) -> list[str] | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    with path.open(newline="") as f:
        return next(csv.reader(f), None)


def append_row(path: Path, header: Sequence[str], row: Mapping[str, object]) -> None:
    """Append one row. Creates the file with `header` if needed; refuses a different header
    or a row whose keys are not exactly the header."""
    if set(row) != set(header):
        raise ValueError(f"row keys {sorted(row)} do not match header {list(header)}")
    existing = _existing_header(path)
    if existing is not None and existing != list(header):
        raise LogHeaderError(f"{path}: header is {existing}, expected {list(header)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(header))
        if existing is None:
            writer.writeheader()
        writer.writerow(row)


def read_rows(path: Path, header: Sequence[str]) -> list[dict[str, str]]:
    """All rows (empty if the file does not exist). The header must match."""
    existing = _existing_header(path)
    if existing is None:
        return []
    if existing != list(header):
        raise LogHeaderError(f"{path}: header is {existing}, expected {list(header)}")
    with path.open(newline="") as f:
        return list(csv.DictReader(f))
