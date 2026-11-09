"""The one gate every probability passes through: integers and Fractions only."""

from __future__ import annotations

from fractions import Fraction


def exact(x: object) -> Fraction:
    """Return `x` as a Fraction. Floats (and numpy scalars, and bools) are refused, so a
    rounded number can never silently enter an exact computation."""
    if isinstance(x, bool) or not isinstance(x, (int, Fraction)):
        raise TypeError(f"exact arithmetic only: got {type(x).__name__} ({x!r})")
    return Fraction(x)
