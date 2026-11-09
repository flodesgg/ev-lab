"""Printing exact numbers for people."""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction


def is_terminating(x: Fraction) -> bool:
    """True when x has a finite decimal expansion (denominator has only factors 2 and 5)."""
    d = x.denominator
    for prime in (2, 5):
        while d % prime == 0:
            d //= prime
    return d == 1


def dec(x: Fraction, places: int = 4) -> str:
    """Exact decimal when one exists ('16.92', '7'), otherwise rounded to `places`."""
    if is_terminating(x):
        text = format(Decimal(x.numerator) / Decimal(x.denominator), "f")
        return text.rstrip("0").rstrip(".") if "." in text else text
    return f"{float(x):.{places}f}"


def signed(x: Fraction, places: int = 2) -> str:
    return f"{float(x):+.{places}f}"
