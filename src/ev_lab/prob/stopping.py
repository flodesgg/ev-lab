"""Optimal stopping.

Finite horizon, exact: backward induction. At the last moment you must stop, so the value
there is known. One step earlier, compare "stop now" with the expected value of continuing
(which uses the values just computed), and so on back to the start.

Infinite horizon, floats: value iteration. Used only as an independent check.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Sequence
from fractions import Fraction

from ev_lab.prob.dist import Dist
from ev_lab.prob.exact import exact


class StoppingSolution[S: Hashable]:
    """At time t = 0..horizon in state s you may stop and collect stop_value(t, s). While
    t < horizon you may instead continue: the next state is drawn from step(t, s). At
    t = horizon you must stop. Ties are resolved in favour of stopping."""

    def __init__(
        self,
        horizon: int,
        stop_value: Callable[[int, S], Fraction | int],
        step: Callable[[int, S], Dist[S]],
    ) -> None:
        if horizon < 0:
            raise ValueError("horizon must be non-negative")
        self.horizon = horizon
        self._stop_value = stop_value
        self._step = step
        self._value: dict[tuple[int, S], Fraction] = {}

    def stop_value(self, t: int, s: S) -> Fraction:
        return exact(self._stop_value(t, s))

    def continuation(self, t: int, s: S) -> Fraction:
        """Expected value of not stopping now and playing optimally afterwards."""
        if t >= self.horizon:
            raise ValueError("cannot continue at the horizon")
        return self._step(t, s).expect(lambda nxt: self.value(t + 1, nxt))

    def value(self, t: int, s: S) -> Fraction:
        """Value of the game from (t, s) under optimal play."""
        key = (t, s)
        if key not in self._value:
            stop = self.stop_value(t, s)
            self._value[key] = stop if t >= self.horizon else max(stop, self.continuation(t, s))
        return self._value[key]

    def should_stop(self, t: int, s: S) -> bool:
        return t >= self.horizon or self.stop_value(t, s) >= self.continuation(t, s)


def value_iteration[S: Hashable](
    states: Sequence[S],
    stop_value: Callable[[S], float],
    step: Callable[[S], Dist[S]],
    cost: float = 0.0,
    tol: float = 1e-13,
    max_iter: int = 100_000,
) -> dict[S, float]:
    """Infinite-horizon stopping in floats: V(s) = max(stop(s), -cost + E[V(next)]).
    Iterates from V = stop until the largest change is below `tol`."""
    value = {s: float(stop_value(s)) for s in states}
    moves = {s: [(nxt, float(p)) for nxt, p in step(s).items()] for s in states}
    for _ in range(max_iter):
        new = {
            s: max(float(stop_value(s)), -cost + sum(p * value[nxt] for nxt, p in moves[s]))
            for s in states
        }
        change = max(abs(new[s] - value[s]) for s in states)
        value = new
        if change < tol:
            return value
    raise RuntimeError("value iteration did not converge")
