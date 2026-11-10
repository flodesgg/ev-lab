"""Bridge to the C++ hand evaluator (`cpp/`), built on demand with the system compiler.

The C++ code is a port of the fast evaluator and is tested the same way: against the Python
oracle, on the hand-written edge cases, and by counting every 5-card and 7-card hand.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

SOURCES = ("evaluator.hpp", "main.cpp")
FLAGS = ("-O2", "-std=c++17", "-Wall", "-Wextra", "-Wpedantic", "-Werror")


class CppUnavailableError(RuntimeError):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def binary_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / "build" / "ev_eval"


def build(root: Path | None = None, force: bool = False) -> Path:
    """Compile the evaluator if the binary is missing or older than its sources."""
    root = root or repo_root()
    sources = [root / "cpp" / name for name in SOURCES]
    binary = binary_path(root)
    if not all(s.exists() for s in sources):
        raise CppUnavailableError(f"C++ sources not found under {root / 'cpp'}")
    newest = max(s.stat().st_mtime for s in sources)
    if not force and binary.exists() and binary.stat().st_mtime >= newest:
        return binary
    compiler = shutil.which("c++")
    if compiler is None:
        raise CppUnavailableError("no C++ compiler (c++) on PATH")
    binary.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [compiler, *FLAGS, "-o", str(binary), str(root / "cpp" / "main.cpp")],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise CppUnavailableError(f"compilation failed:\n{result.stderr}")
    return binary


def _run(args: list[str], stdin: str | None = None) -> str:
    result = subprocess.run(
        [str(build()), *args], input=stdin, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or f"ev_eval exited with {result.returncode}")
    return result.stdout


def evaluate(hands: NDArray[np.integer]) -> NDArray[np.int64]:
    """Values of n hands given as an (n, k) array of card integers, k = 5, 6 or 7."""
    array = np.asarray(hands, dtype=np.int64)
    if array.ndim != 2 or not 5 <= array.shape[1] <= 7:
        raise ValueError("expected an (n, k) array with k = 5, 6 or 7")
    if len(array) == 0:
        return np.zeros(0, dtype=np.int64)
    text = "\n".join(" ".join(map(str, row)) for row in array.tolist())
    out = _run(["eval", str(array.shape[1])], stdin=text + "\n")
    return np.array(out.split(), dtype=np.int64)


@dataclass(frozen=True)
class Counts:
    counts: tuple[int, ...]  # index 0 = high card .. 8 = straight flush
    seconds: float


def category_counts(cards_per_hand: int) -> Counts:
    """Category counts over every hand of this size, enumerated in C++."""
    lines = _run(["counts", str(cards_per_hand)]).split("\n")
    return Counts(tuple(int(v) for v in lines[:9]), float(lines[9].split()[1]))


def benchmark(hands: int) -> float:
    """7-card hands evaluated per second (evaluation only, hands generated beforehand)."""
    fields = dict(line.split() for line in _run(["bench", str(hands)]).strip().split("\n"))
    return int(fields["hands"]) / float(fields["seconds"])
