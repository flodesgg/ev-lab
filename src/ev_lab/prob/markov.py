"""Absorbing Markov chains, solved exactly.

Order the states as transient first, absorbing last. The transition matrix is then
    P = [[Q, R],
         [0, I]]
and the fundamental matrix N = (I - Q)^(-1) has a direct meaning: N[i][j] is the expected
number of visits to transient state j when starting from transient state i. From it:
    expected steps until absorption from i  = sum of row i of N
    probability of ending in absorbing k    = (N R)[i][k]
"""

from __future__ import annotations

from collections.abc import Hashable, Mapping
from fractions import Fraction

from ev_lab.prob.exact import exact
from ev_lab.prob.linalg import Matrix, SingularMatrixError, identity, inverse, matmul


class AbsorbingChain[S: Hashable]:
    """`transitions[s]` maps each next state to its probability. A state with no entry, or
    whose only move is to itself, is absorbing."""

    def __init__(self, transitions: Mapping[S, Mapping[S, Fraction | int]]) -> None:
        rows: dict[S, dict[S, Fraction]] = {
            s: {t: exact(p) for t, p in row.items() if exact(p) != 0}
            for s, row in transitions.items()
        }
        states: list[S] = list(rows)
        for row in rows.values():
            for t in row:
                if t not in rows and t not in states:
                    states.append(t)

        def is_absorbing(s: S) -> bool:
            return s not in rows or rows[s] == {s: Fraction(1)}

        self.transient: list[S] = [s for s in states if not is_absorbing(s)]
        self.absorbing: list[S] = [s for s in states if is_absorbing(s)]
        for s in self.transient:
            if any(p < 0 for p in rows[s].values()):
                raise ValueError(f"negative probability out of state {s!r}")
            total = sum(rows[s].values(), Fraction(0))
            if total != 1:
                raise ValueError(f"probabilities out of state {s!r} sum to {total}, not 1")

        self._ti = {s: i for i, s in enumerate(self.transient)}
        zero = Fraction(0)
        self.q: Matrix = [[rows[s].get(t, zero) for t in self.transient] for s in self.transient]
        self.r: Matrix = [[rows[s].get(t, zero) for t in self.absorbing] for s in self.transient]
        n = len(self.transient)
        i_minus_q = [[identity(n)[i][j] - self.q[i][j] for j in range(n)] for i in range(n)]
        try:
            self.fundamental: Matrix = inverse(i_minus_q)
        except SingularMatrixError as e:
            raise ValueError(
                "some transient state can never reach an absorbing state "
                "(the expected time to absorption would be infinite)"
            ) from e
        self._absorb: Matrix = matmul(self.fundamental, self.r) if n else []

    def expected_steps(self, start: S) -> Fraction:
        """Expected number of steps until absorption, starting from `start`."""
        if start in self._ti:
            return sum(self.fundamental[self._ti[start]], Fraction(0))
        self._require_known(start)
        return Fraction(0)

    def expected_visits(self, start: S, state: S) -> Fraction:
        """Expected number of visits to transient `state` (the start counts as a visit)."""
        return self.fundamental[self._ti[start]][self._ti[state]]

    def absorption_probs(self, start: S) -> dict[S, Fraction]:
        """Probability of ending in each absorbing state, starting from `start`."""
        if start in self._ti:
            return dict(zip(self.absorbing, self._absorb[self._ti[start]], strict=True))
        self._require_known(start)
        return {s: Fraction(int(s == start)) for s in self.absorbing}

    def _require_known(self, s: S) -> None:
        if s not in self.absorbing:
            raise KeyError(f"unknown state {s!r}")
