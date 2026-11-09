"""Mental-arithmetic question generators.

Every question carries its exact answer as a Fraction and an absolute tolerance. Exact
categories (products, squares, sums) have tolerance 0; categories whose answer is a rounded
decimal accept a small error, listed in `TOLERANCE_NOTE`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from fractions import Fraction
from math import gcd

import numpy as np

from ev_lab.fmt import dec, is_terminating

LEVELS = (1, 2, 3)


@dataclass(frozen=True)
class Question:
    category: str
    level: int
    text: str
    answer: Fraction
    tolerance: Fraction  # absolute; 0 means the answer must be exact

    def is_correct(self, given: Fraction) -> bool:
        return abs(given - self.answer) <= self.tolerance


Generator = Callable[[np.random.Generator, int], Question]


def _int(rng: np.random.Generator, low: int, high: int) -> int:
    """Uniform integer in [low, high], both ends included."""
    return int(rng.integers(low, high + 1))


def _pick[T](rng: np.random.Generator, options: tuple[T, ...]) -> T:
    return options[_int(rng, 0, len(options) - 1)]


def mul_2x2(rng: np.random.Generator, level: int) -> Question:
    low, high = {1: (11, 30), 2: (12, 99), 3: (31, 99)}[level]
    a, b = _int(rng, low, high), _int(rng, low, high)
    return Question("mul_2x2", level, f"{a} x {b}", Fraction(a * b), Fraction(0))


def mul_3x1(rng: np.random.Generator, level: int) -> Question:
    (alo, ahi), (blo, bhi) = {
        1: ((101, 300), (2, 5)),
        2: ((101, 999), (3, 9)),
        3: ((501, 999), (6, 9)),
    }[level]
    a, b = _int(rng, alo, ahi), _int(rng, blo, bhi)
    return Question("mul_3x1", level, f"{a} x {b}", Fraction(a * b), Fraction(0))


def decimal_mul(rng: np.random.Generator, level: int) -> Question:
    a = Fraction(_int(rng, 11, 99), 10)
    if level == 1:
        b = Fraction(_int(rng, 2, 9))
    elif level == 2:
        b = Fraction(_int(rng, 2, 9), 10)
    else:
        b = Fraction(_int(rng, 11, 99), 10)
    return Question("decimal_mul", level, f"{dec(a)} x {dec(b)}", a * b, Fraction(0))


def division(rng: np.random.Generator, level: int) -> Question:
    (alo, ahi), (blo, bhi) = {
        1: ((10, 99), (2, 9)),
        2: ((100, 999), (3, 19)),
        3: ((100, 999), (13, 99)),
    }[level]
    a, b = _int(rng, alo, ahi), _int(rng, blo, bhi)
    return Question(
        "division", level, f"{a} / {b} (to 2 decimals)", Fraction(a, b), Fraction(1, 100)
    )


_DENOMINATORS: Mapping[int, tuple[int, ...]] = {
    1: (2, 4, 5, 10),
    2: (3, 6, 8, 20, 25),
    3: (7, 9, 11, 12, 16, 40),
}


def frac_pct(rng: np.random.Generator, level: int) -> Question:
    d = _pick(rng, _DENOMINATORS[level])
    n = _int(rng, 1, d - 1)
    while gcd(n, d) != 1:
        n = _int(rng, 1, d - 1)
    value = Fraction(n, d)
    # the reverse direction only makes sense when the percentage is a finite decimal
    if is_terminating(value) and rng.random() < 0.5:
        return Question("frac_pct", level, f"{dec(100 * value)}% as a fraction", value, Fraction(0))
    return Question("frac_pct", level, f"{n}/{d} as a percentage", 100 * value, Fraction(1, 10))


def squares(rng: np.random.Generator, level: int) -> Question:
    low, high = {1: (11, 30), 2: (31, 70), 3: (71, 100)}[level]
    n = _int(rng, low, high)
    return Question("squares", level, f"{n}^2", Fraction(n * n), Fraction(0))


def pct_change(rng: np.random.Generator, level: int) -> Question:
    if level == 1:
        a = 20 * _int(rng, 1, 10)
        b = a + a * _pick(rng, (-50, -25, -20, -10, 10, 20, 25, 50)) // 100
        tolerance = Fraction(1, 10)
    else:
        a = 5 * _int(rng, 4, 40) if level == 2 else _int(rng, 30, 300)
        delta = 0
        while delta == 0:
            delta = _int(rng, -(a // 2), a // 2)
        b = a + delta
        tolerance = Fraction(1, 2)
    return Question(
        "pct_change", level, f"{a} -> {b}: percentage change", Fraction(100 * (b - a), a), tolerance
    )


def seq_sum(rng: np.random.Generator, level: int) -> Question:
    if level == 1:
        n = _int(rng, 10, 30)
        return Question(
            "seq_sum", level, f"1 + 2 + 3 + ... + {n}", Fraction(n * (n + 1) // 2), Fraction(0)
        )
    if level == 3 and rng.random() < 0.5:
        k = _int(rng, 5, 10)
        return Question(
            "seq_sum", level, f"1 + 2 + 4 + ... + {2**k}", Fraction(2 ** (k + 1) - 1), Fraction(0)
        )
    first, step = _int(rng, 1, 9), _int(rng, 2, 9)
    terms = _int(rng, 5, 12) if level == 2 else _int(rng, 10, 25)
    last = first + step * (terms - 1)
    text = f"{first} + {first + step} + {first + 2 * step} + ... + {last} ({terms} terms)"
    return Question("seq_sum", level, text, Fraction(terms * (first + last), 2), Fraction(0))


CATEGORIES: dict[str, Generator] = {
    "mul_2x2": mul_2x2,
    "mul_3x1": mul_3x1,
    "decimal_mul": decimal_mul,
    "division": division,
    "frac_pct": frac_pct,
    "squares": squares,
    "pct_change": pct_change,
    "seq_sum": seq_sum,
}

TITLES: dict[str, str] = {
    "mul_2x2": "2-digit x 2-digit",
    "mul_3x1": "3-digit x 1-digit",
    "decimal_mul": "decimal multiplication",
    "division": "division to 2 decimals",
    "frac_pct": "fractions <-> percentages",
    "squares": "squares up to 100^2",
    "pct_change": "percentage change",
    "seq_sum": "sums of sequences",
}

TOLERANCE_NOTE = (
    "Exact answers are required except: division (within 0.01), fraction -> percentage "
    "(within 0.1 percentage points), percentage change (within 0.1 at level 1, 0.5 at "
    "levels 2-3)."
)


def generate(rng: np.random.Generator, category: str, level: int) -> Question:
    if level not in LEVELS:
        raise ValueError(f"level must be one of {LEVELS}")
    return CATEGORIES[category](rng, level)
