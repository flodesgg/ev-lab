"""Coin-pattern races as absorbing Markov chains (not a puzzle itself; shared helper)."""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

from ev_lab.prob.markov import AbsorbingChain


def pattern_chain(patterns: Sequence[str], alphabet: str = "HT") -> AbsorbingChain[str]:
    """Toss until one of `patterns` appears. A state is the longest suffix of the tosses so
    far that is still the beginning of some pattern; the start is the empty string."""
    prefixes = {p[:i] for p in patterns for i in range(len(p) + 1)}
    step = Fraction(1, len(alphabet))
    transitions: dict[str, dict[str, Fraction]] = {}
    for state in prefixes:
        if state in patterns:
            continue
        row: dict[str, Fraction] = {}
        for symbol in alphabet:
            nxt = state + symbol
            while nxt not in prefixes:
                nxt = nxt[1:]
            row[nxt] = row.get(nxt, Fraction(0)) + step
        transitions[state] = row
    return AbsorbingChain(transitions)
