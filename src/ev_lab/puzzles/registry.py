"""Finds every puzzle module in this package (each exposes a module-level `PUZZLE`)."""

from __future__ import annotations

import importlib
import pkgutil
from functools import cache

import ev_lab.puzzles as _package
from ev_lab.puzzles.base import Puzzle

_NOT_PUZZLES = {"base", "registry", "simtools", "patterns", "cli", "log", "grading"}


@cache
def all_puzzles() -> tuple[Puzzle, ...]:
    """All puzzles: practice problems first, then by difficulty, then by id."""
    found: dict[str, Puzzle] = {}
    for info in pkgutil.iter_modules(_package.__path__):
        if info.name in _NOT_PUZZLES or info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{_package.__name__}.{info.name}")
        puzzle = module.PUZZLE
        if not isinstance(puzzle, Puzzle):
            raise TypeError(f"{info.name}.PUZZLE is not a Puzzle")
        if puzzle.id != info.name:
            raise ValueError(f"puzzle id {puzzle.id!r} must equal its module name {info.name!r}")
        found[puzzle.id] = puzzle
    return tuple(sorted(found.values(), key=lambda p: (not p.practice_pending, p.difficulty, p.id)))


def get_puzzle(puzzle_id: str) -> Puzzle:
    for p in all_puzzles():
        if p.id == puzzle_id:
            return p
    raise KeyError(puzzle_id)
