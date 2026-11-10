"""Leduc hold'em (Southey et al., 2005): a poker game one size up from Kuhn poker.

Six cards: two suits of J < Q < K. Two players, each antes 1 and gets one private card.
Round 1: betting with bets of 2. Then one public card is revealed. Round 2: betting with
bets of 4. At most two bets (a bet and one raise) per round. At showdown a private card
that pairs the public card wins; otherwise the higher card wins; equal ranks split.
Rules checked against two sources: docs/sources.md.

Actions inside a round are written as a string: c = check or call, r = bet or raise,
f = fold. Player 1 acts first in both rounds.

This module holds the rules and a plain, slow evaluator that deals actual cards. It is the
reference against which the fast solver in `leduc_cfr.py` is tested.
"""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from itertools import permutations

RANKS = "JQK"
DECK = (0, 0, 1, 1, 2, 2)  # the rank of each of the six cards
ANTE = 1
BET_SIZES = (2, 4)  # round 1, round 2
MAX_RAISES = 2

Strategy = Mapping[str, Mapping[str, float | Fraction]]  # infoset -> action -> probability


def round_over(seq: str) -> bool:
    return seq == "cc" or seq.endswith("f") or (seq.endswith("c") and "r" in seq)


def legal_actions(seq: str) -> str:
    if round_over(seq):
        return ""
    if "r" not in seq:
        return "cr"  # nothing to call: check or bet
    return "fcr" if seq.count("r") < MAX_RAISES else "fc"


def player_to_act(seq: str) -> int:
    return len(seq) % 2


def round_sequences() -> list[str]:
    """Every betting sequence that can occur within one round, shortest first."""
    out, frontier = [""], [""]
    while frontier:
        nxt = [seq + a for seq in frontier for a in legal_actions(seq)]
        out += nxt
        frontier = nxt
    return out


def commitments(seq: str, bet: int) -> tuple[int, int]:
    """Chips each player has put in during one round (beyond earlier rounds and the ante)."""
    put = [0, 0]
    for i, action in enumerate(seq):
        player = i % 2
        if action == "r":
            put[player] = max(put) + bet
        elif action == "c":
            put[player] = max(put)
    return put[0], put[1]


def strength(rank: int, public: int) -> int:
    """Showdown strength: a pair with the public card beats any unpaired card."""
    return rank + (3 if rank == public else 0)


def payoff(rank0: int, rank1: int, public: int | None, r1: str, r2: str | None) -> int:
    """Chips won by player 1 (the first to act) at a terminal history."""
    a0, a1 = commitments(r1, BET_SIZES[0])
    b0, b1 = commitments(r2, BET_SIZES[1]) if r2 is not None else (0, 0)
    in0, in1 = ANTE + a0 + b0, ANTE + a1 + b1
    last = r2 if r2 is not None else r1
    if last.endswith("f"):
        folder = (len(last) - 1) % 2
        return in1 if folder == 1 else -in0
    if public is None:
        raise ValueError("a showdown needs a public card")
    s0, s1 = strength(rank0, public), strength(rank1, public)
    return in1 if s0 > s1 else -in0 if s1 > s0 else 0


def infoset_key(rank: int, r1: str, public: int | None = None, r2: str | None = None) -> str:
    """What a player knows: own rank, round-1 betting, and (in round 2) the public rank and
    the betting so far. Suits never matter, so ranks are enough."""
    if public is None:
        return f"{RANKS[rank]}:{r1}"
    return f"{RANKS[rank]}:{r1}/{RANKS[public]}:{r2}"


def all_infosets() -> list[str]:
    keys = []
    decision = [s for s in round_sequences() if legal_actions(s)]
    to_round2 = [s for s in round_sequences() if round_over(s) and not s.endswith("f")]
    for rank in range(3):
        keys += [infoset_key(rank, s) for s in decision]
        keys += [
            infoset_key(rank, r1, public, s)
            for r1 in to_round2
            for public in range(3)
            for s in decision
        ]
    return keys


def card_level_infoset_count() -> int:
    """Information sets when suits are kept apart (6 private cards, 5 possible public
    cards): the count other implementations report."""
    decision = sum(1 for s in round_sequences() if legal_actions(s))
    to_round2 = sum(1 for s in round_sequences() if round_over(s) and not s.endswith("f"))
    return 6 * decision + 6 * 5 * to_round2 * decision


def uniform_strategy() -> dict[str, dict[str, Fraction]]:
    out: dict[str, dict[str, Fraction]] = {}
    for key in all_infosets():
        seq = key.rsplit(":", 1)[1]
        actions = legal_actions(seq)
        out[key] = {a: Fraction(1, len(actions)) for a in actions}
    return out


def _play(
    ranks: tuple[int, int], public: int | None, r1: str, r2: str | None, strategy: Strategy
) -> float | Fraction:
    seq = r2 if r2 is not None else r1
    if round_over(seq):
        raise AssertionError("handled by the caller")
    player = player_to_act(seq)
    probs = strategy[infoset_key(ranks[player], r1, public, r2)]
    total: float | Fraction = Fraction(0)
    for action in legal_actions(seq):
        p = probs[action]
        if p == 0:
            continue
        nxt = seq + action
        if r2 is None:
            total += p * _after_round1(ranks, nxt, strategy)
        elif round_over(nxt):
            total += p * payoff(ranks[0], ranks[1], public, r1, nxt)
        else:
            total += p * _play(ranks, public, r1, nxt, strategy)
    return total


# set by expected_value for the duration of one deal: the four cards left in the deck
_REMAINING: list[int] = []


def _after_round1(ranks: tuple[int, int], r1: str, strategy: Strategy) -> float | Fraction:
    if not round_over(r1):
        return _play(ranks, None, r1, None, strategy)
    if r1.endswith("f"):
        return payoff(ranks[0], ranks[1], None, r1, None)
    total: float | Fraction = Fraction(0)
    for card in _REMAINING:  # the public card: each remaining card equally likely
        total += _play(ranks, DECK[card], r1, "", strategy)
    return total / len(_REMAINING)


def expected_value(strategy: Strategy) -> float | Fraction:
    """Player 1's expected winnings per hand when both follow `strategy`. Deals the six
    actual cards in every order: 30 private deals x 4 public cards. Exact when the
    probabilities are Fractions."""
    total: float | Fraction = Fraction(0)
    deals = list(permutations(range(6), 2))
    for c0, c1 in deals:
        _REMAINING[:] = [c for c in range(6) if c not in (c0, c1)]
        total += _after_round1((DECK[c0], DECK[c1]), "", strategy)
    return total / len(deals)
