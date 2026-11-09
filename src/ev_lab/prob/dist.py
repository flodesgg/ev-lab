"""A finite probability distribution with exact (Fraction) probabilities.

A `Dist` maps outcomes to probabilities that sum to exactly 1. Outcomes can be any hashable
value: an int, a tuple of dice, a string. Everything is computed by plain enumeration.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable, Iterator, Mapping
from fractions import Fraction

from ev_lab.prob.exact import exact


class Dist[T: Hashable]:
    __slots__ = ("_p",)

    def __init__(self, probs: Mapping[T, Fraction | int]) -> None:
        p: dict[T, Fraction] = {}
        for outcome, weight in probs.items():
            w = exact(weight)
            if w < 0:
                raise ValueError(f"negative probability for {outcome!r}: {w}")
            if w > 0:
                p[outcome] = w
        total = sum(p.values(), Fraction(0))
        if total != 1:
            raise ValueError(f"probabilities sum to {total}, not 1")
        self._p = p

    # ---- constructors -------------------------------------------------------------------

    @classmethod
    def from_weights(cls, weights: Mapping[T, Fraction | int]) -> Dist[T]:
        """Normalise non-negative weights (for example counts) into probabilities."""
        total = sum((exact(w) for w in weights.values()), Fraction(0))
        if total <= 0:
            raise ValueError("weights must have a positive sum")
        return cls({k: exact(w) / total for k, w in weights.items()})

    @classmethod
    def uniform(cls, outcomes: Iterable[T]) -> Dist[T]:
        """Every listed outcome equally likely. A repeated outcome counts once per repeat."""
        counts: dict[T, int] = {}
        for o in outcomes:
            counts[o] = counts.get(o, 0) + 1
        if not counts:
            raise ValueError("uniform() needs at least one outcome")
        return cls.from_weights(counts)

    @classmethod
    def point(cls, outcome: T) -> Dist[T]:
        return cls({outcome: 1})

    # ---- access -------------------------------------------------------------------------

    def items(self) -> Iterator[tuple[T, Fraction]]:
        return iter(self._p.items())

    @property
    def support(self) -> list[T]:
        return list(self._p)

    def __getitem__(self, outcome: T) -> Fraction:
        return self._p.get(outcome, Fraction(0))

    def __len__(self) -> int:
        return len(self._p)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Dist) and self._p == other._p

    def __hash__(self) -> int:
        return hash(frozenset(self._p.items()))

    def __repr__(self) -> str:
        body = ", ".join(f"{k!r}: {v}" for k, v in self._p.items())
        return f"Dist({{{body}}})"

    # ---- transformations ----------------------------------------------------------------

    def map[U: Hashable](self, f: Callable[[T], U]) -> Dist[U]:
        """Distribution of f(X). Outcomes with the same image are merged."""
        out: dict[U, Fraction] = {}
        for x, p in self._p.items():
            y = f(x)
            out[y] = out.get(y, Fraction(0)) + p
        return Dist(out)

    def bind[U: Hashable](self, f: Callable[[T], Dist[U]]) -> Dist[U]:
        """Two-stage experiment: draw X, then draw from f(X). Law of total probability."""
        out: dict[U, Fraction] = {}
        for x, p in self._p.items():
            for y, q in f(x).items():
                out[y] = out.get(y, Fraction(0)) + p * q
        return Dist(out)

    def combine[U: Hashable, V: Hashable](self, other: Dist[U], f: Callable[[T, U], V]) -> Dist[V]:
        """Distribution of f(X, Y) for independent X and Y."""
        out: dict[V, Fraction] = {}
        for x, p in self._p.items():
            for y, q in other._p.items():
                z = f(x, y)
                out[z] = out.get(z, Fraction(0)) + p * q
        return Dist(out)

    def condition(self, event: Callable[[T], bool]) -> Dist[T]:
        """Distribution of X given that the event happened: keep, then renormalise."""
        kept = {x: p for x, p in self._p.items() if event(x)}
        if not kept:
            raise ValueError("cannot condition on an event of probability 0")
        return Dist.from_weights(kept)

    # ---- numbers ------------------------------------------------------------------------

    def prob(self, event: Callable[[T], bool]) -> Fraction:
        return sum((p for x, p in self._p.items() if event(x)), Fraction(0))

    def expect(self, f: Callable[[T], Fraction | int] | None = None) -> Fraction:
        """E[f(X)], or E[X] when the outcomes themselves are exact numbers."""
        total = Fraction(0)
        for x, p in self._p.items():
            total += exact(x if f is None else f(x)) * p
        return total

    def variance(self, f: Callable[[T], Fraction | int] | None = None) -> Fraction:
        mean = self.expect(f)
        return sum(
            ((exact(x if f is None else f(x)) - mean) ** 2 * p for x, p in self._p.items()),
            Fraction(0),
        )


def fair_die(sides: int = 6) -> Dist[int]:
    return Dist.uniform(range(1, sides + 1))


def joint[T: Hashable](*dists: Dist[T]) -> Dist[tuple[T, ...]]:
    """Joint distribution of independent variables, as tuples."""
    out: Dist[tuple[T, ...]] = Dist.point(())
    for d in dists:
        out = out.combine(d, lambda acc, x: (*acc, x))
    return out


def convolve(a: Dist[int], b: Dist[int]) -> Dist[int]:
    """Distribution of the sum of two independent integer variables."""
    return a.combine(b, lambda x, y: x + y)


def sum_of(d: Dist[int], n: int) -> Dist[int]:
    """Distribution of the sum of n independent copies (n-fold convolution)."""
    if n < 0:
        raise ValueError("n must be non-negative")
    out: Dist[int] = Dist.point(0)
    for _ in range(n):
        out = convolve(out, d)
    return out
