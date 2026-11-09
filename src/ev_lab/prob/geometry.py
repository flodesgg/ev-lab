"""Exact areas of convex polygons cut out by straight lines.

Geometric probability with uniform points is "favourable area / total area". When the
favourable region is bounded by straight lines, it is a polygon, and its area is an exact
Fraction: clip the square by each inequality, then apply the shoelace formula.
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

from ev_lab.prob.exact import exact

Point = tuple[Fraction, Fraction]

UNIT_SQUARE: list[Point] = [
    (Fraction(0), Fraction(0)),
    (Fraction(1), Fraction(0)),
    (Fraction(1), Fraction(1)),
    (Fraction(0), Fraction(1)),
]


def clip(
    polygon: Sequence[Point], a: Fraction | int, b: Fraction | int, c: Fraction | int
) -> list[Point]:
    """Keep the part of a convex polygon where a*x + b*y <= c (Sutherland-Hodgman)."""
    fa, fb, fc = exact(a), exact(b), exact(c)
    out: list[Point] = []
    for i, p in enumerate(polygon):
        q = polygon[(i + 1) % len(polygon)]
        side_p = fa * p[0] + fb * p[1] - fc
        side_q = fa * q[0] + fb * q[1] - fc
        if side_p <= 0:
            out.append(p)
        if (side_p < 0 < side_q) or (side_q < 0 < side_p):
            t = side_p / (side_p - side_q)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def area(polygon: Sequence[Point]) -> Fraction:
    """Shoelace formula. Zero for a degenerate polygon (fewer than 3 points)."""
    if len(polygon) < 3:
        return Fraction(0)
    twice = Fraction(0)
    for i, (x1, y1) in enumerate(polygon):
        x2, y2 = polygon[(i + 1) % len(polygon)]
        twice += x1 * y2 - x2 * y1
    return abs(twice) / 2
