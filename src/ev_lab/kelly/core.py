"""The Kelly criterion for a repeated binary bet (Kelly, 1956).

A bet wins with probability p and then pays b per unit staked (net odds); otherwise the
stake is lost. Staking a fraction f of current wealth every time multiplies wealth by
(1 + b f) on a win and by (1 - f) on a loss. After many bets wealth grows like
exp(g(f) x number of bets), where

    g(f) = p ln(1 + b f) + (1 - p) ln(1 - f)        expected log growth per bet

Kelly's fraction maximises g:   f* = p - (1 - p) / b   (edge / odds).
Staking more than f* lowers the growth rate *and* raises the risk; at about 2 f* the
growth rate is back to roughly zero.
"""

from __future__ import annotations

import math
from fractions import Fraction

from ev_lab.prob.exact import exact


def kelly_fraction(p: Fraction, odds: Fraction | int) -> Fraction:
    """f* = p - (1 - p) / b, exactly. Negative when the bet has a negative edge."""
    pp, b = exact(p), exact(odds)
    if not 0 <= pp <= 1 or b <= 0:
        raise ValueError("need 0 <= p <= 1 and positive odds")
    return pp - (1 - pp) / b


def kelly_bet(p: Fraction, odds: Fraction | int) -> Fraction:
    """What to actually stake: f*, or nothing when the edge is zero or negative."""
    return max(Fraction(0), kelly_fraction(p, odds))


def growth_rate(f: float, p: float, odds: float) -> float:
    """g(f): expected log growth per bet. -inf when f = 1 (a loss wipes out everything)."""
    if not 0 <= f <= 1:
        raise ValueError("the staked fraction must be between 0 and 1")
    if f == 1.0:
        return -math.inf if p < 1 else math.log1p(odds)
    return p * math.log1p(odds * f) + (1 - p) * math.log1p(-f)


def expected_wealth_factor(f: float, p: float, odds: float) -> float:
    """Expected wealth multiple per bet: 1 + f x (edge per unit staked). The *mean* keeps
    growing with f even where the *typical* (median) outcome shrinks."""
    return 1 + f * (p * odds - (1 - p))


def hit_probability_approx(level: float, multiple: float) -> float:
    """Continuous-time approximation of P(wealth ever falls to `level` x start) when
    staking `multiple` x Kelly: level^(2/multiple - 1), and 1 for multiple >= 2.

    Assumes wealth follows a geometric Brownian motion (many small bets) and an infinite
    horizon. Log-wealth then has drift (c - c^2/2) s^2 and variance c^2 s^2 per unit time
    (c = multiple, s = edge/volatility of one bet), and a Brownian motion with drift m > 0
    and variance v ever falls by d with probability exp(-2 m d / v)."""
    if not 0 < level < 1 or multiple <= 0:
        raise ValueError("need 0 < level < 1 and a positive multiple")
    if multiple >= 2:
        return 1.0
    return float(level ** (2 / multiple - 1))
