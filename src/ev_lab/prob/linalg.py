"""Exact linear algebra on Fractions (Gauss-Jordan elimination). Small matrices only."""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

from ev_lab.prob.exact import exact

Matrix = list[list[Fraction]]


class SingularMatrixError(ValueError):
    pass


def identity(n: int) -> Matrix:
    return [[Fraction(int(i == j)) for j in range(n)] for i in range(n)]


def solve(a: Sequence[Sequence[Fraction | int]], b: Sequence[Sequence[Fraction | int]]) -> Matrix:
    """Solve A X = B exactly. A is n x n, B is n x m; returns X (n x m)."""
    n = len(a)
    if any(len(row) != n for row in a) or len(b) != n:
        raise ValueError("A must be square and B must have as many rows as A")
    aug = [[exact(v) for v in a[i]] + [exact(v) for v in b[i]] for i in range(n)]
    for col in range(n):
        pivot = next((r for r in range(col, n) if aug[r][col] != 0), None)
        if pivot is None:
            raise SingularMatrixError("matrix is singular")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        aug[col] = [v / scale for v in aug[col]]
        for r in range(n):
            factor = aug[r][col]
            if r != col and factor != 0:
                aug[r] = [v - factor * w for v, w in zip(aug[r], aug[col], strict=True)]
    return [row[n:] for row in aug]


def inverse(a: Sequence[Sequence[Fraction | int]]) -> Matrix:
    return solve(a, identity(len(a)))


def matmul(a: Sequence[Sequence[Fraction]], b: Sequence[Sequence[Fraction]]) -> Matrix:
    cols = len(b[0]) if b else 0
    return [
        [sum((row[k] * b[k][j] for k in range(len(b))), Fraction(0)) for j in range(cols)]
        for row in a
    ]
