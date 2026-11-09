"""Indifference: the bluffing and calling frequencies that leave the opponent no good choice.

Pot P before the bet, bet size B.

Bluff share. The caller risks B to win P + B. If a fraction f of the betting range is
bluffs, calling earns f (P + B) - (1 - f) B. Setting this to 0 gives
    f = B / (P + 2B).

Calling frequency. A pure bluff risks B to win P. If the opponent calls with probability c,
the bluff earns (1 - c) P - c B. Setting this to 0 gives
    c = P / (P + B).
"""

from __future__ import annotations

from fractions import Fraction

from ev_lab.prob.exact import exact


def _check(pot: Fraction, bet: Fraction) -> None:
    if pot <= 0 or bet <= 0:
        raise ValueError("pot and bet must be positive")


def bluff_share(pot: Fraction | int, bet: Fraction | int) -> Fraction:
    """Share of bluffs in a betting range that makes a caller indifferent."""
    p, b = exact(pot), exact(bet)
    _check(p, b)
    return b / (p + 2 * b)


def calling_frequency(pot: Fraction | int, bet: Fraction | int) -> Fraction:
    """Calling frequency that makes a pure bluff break even."""
    p, b = exact(pot), exact(bet)
    _check(p, b)
    return p / (p + b)


def caller_ev(pot: Fraction, bet: Fraction, bluffs: Fraction) -> Fraction:
    """EV of calling a bet when a fraction `bluffs` of the bettor's range is bluffs."""
    return bluffs * (pot + bet) - (1 - bluffs) * bet


def bluff_ev(pot: Fraction, bet: Fraction, call_prob: Fraction) -> Fraction:
    """EV of a pure bluff when the opponent calls with probability `call_prob`."""
    return (1 - call_prob) * pot - call_prob * bet
