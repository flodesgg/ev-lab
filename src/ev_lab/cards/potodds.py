"""Pot odds: is a call profitable given my equity?

`pot` is everything already in the middle when I decide, including the bet I am facing.
`call` is what I must add. If I call and win I gain `pot`; if I lose I lose `call`.
"""

from __future__ import annotations

from fractions import Fraction

from ev_lab.prob.exact import exact


def call_ev(equity: Fraction, pot: Fraction | int, call: Fraction | int) -> Fraction:
    """Expected value of calling, relative to folding (which is worth 0)."""
    e, p, c = exact(equity), exact(pot), exact(call)
    if not 0 <= e <= 1 or p < 0 or c < 0:
        raise ValueError("need 0 <= equity <= 1 and non-negative amounts")
    return e * p - (1 - e) * c


def breakeven_equity(pot: Fraction | int, call: Fraction | int) -> Fraction:
    """The equity at which calling is worth exactly 0: call / (pot + call)."""
    p, c = exact(pot), exact(call)
    if p < 0 or c <= 0:
        raise ValueError("need a non-negative pot and a positive call")
    return c / (p + c)
