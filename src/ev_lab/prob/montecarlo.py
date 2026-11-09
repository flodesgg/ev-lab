"""Monte Carlo as an independent check of exact answers.

A simulator plays the experiment many times and returns one number per trial. The mean of
those numbers estimates the exact answer; the standard error (sample standard deviation
divided by sqrt(n)) says how far off the mean typically is. An exact answer "agrees" when it
lies within `tol_se` standard errors of the estimate (4 by default: a correct answer fails
by chance about 6 times in 100,000).

For a conditional probability the simulator returns values only for the trials where the
condition happened (rejection sampling), so `n` is the number of accepted trials.
"""

from __future__ import annotations

import math
import zlib
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
Simulator = Callable[[np.random.Generator, int], FloatArray]


@dataclass(frozen=True)
class McResult:
    estimate: float
    se: float
    n: int

    def z(self, exact_value: Fraction) -> float:
        """(estimate - exact) in units of the standard error."""
        diff = self.estimate - float(_require_fraction(exact_value))
        if self.se == 0.0:
            return 0.0 if diff == 0.0 else math.copysign(math.inf, diff)
        return diff / self.se


def _require_fraction(x: object) -> Fraction:
    if not isinstance(x, Fraction):
        raise TypeError(f"the exact value must be a Fraction, got {type(x).__name__}")
    return x


def rng_for(seed: int, name: str) -> np.random.Generator:
    """An independent, reproducible stream for a named task. The stream depends only on the
    root seed and the name, not on how many other tasks exist or in which order they run."""
    return np.random.default_rng(np.random.SeedSequence([seed, zlib.crc32(name.encode())]))


def run_mc(simulate: Simulator, n: int, rng: np.random.Generator) -> McResult:
    samples = np.asarray(simulate(rng, n), dtype=np.float64)
    if samples.ndim != 1 or samples.size < 2:
        raise ValueError("a simulator must return a 1-D array with at least 2 samples")
    se = float(samples.std(ddof=1)) / math.sqrt(samples.size)
    return McResult(estimate=float(samples.mean()), se=se, n=int(samples.size))


def agrees(exact_value: Fraction, mc: McResult, tol_se: float = 4.0) -> bool:
    return abs(mc.z(exact_value)) < tol_se


def assert_agrees(
    exact_value: Fraction, mc: McResult, tol_se: float = 4.0, label: str = ""
) -> None:
    """Raise AssertionError when exact and Monte Carlo disagree. The message carries only
    the z-score, never the values, so a failing test cannot spoil a puzzle."""
    if not agrees(exact_value, mc, tol_se):
        raise AssertionError(
            f"{label or 'value'}: exact and Monte Carlo differ by {mc.z(exact_value):+.2f} SE "
            f"(n={mc.n}, tolerance {tol_se} SE)"
        )
