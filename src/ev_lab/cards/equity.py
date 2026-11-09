"""Texas Hold'em equity: the share of the pot a hand wins on average at showdown.

Each player holds two cards (or a range of possible two-card hands); five board cards are
shared. Equity = P(win) + P(tie) x (share of the pot in a tie): ties split the pot.

Exact: enumerate every way to complete the board (heads-up before the flop that is
C(48, 5) = 1,712,304 boards) for every compatible assignment of hands; results are
Fractions. Monte Carlo: sample hands and boards; results come with a standard error.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from math import comb

import numpy as np

from ev_lab.cards.deck import DECK_SIZE, require_distinct
from ev_lab.cards.fast import IntArray, combinations_array, evaluate
from ev_lab.cards.ranges import Combo, remove_dead
from ev_lab.prob.montecarlo import McResult

Range = Sequence[Combo]


@dataclass(frozen=True)
class ExactPlayer:
    win: Fraction  # wins the whole pot
    tie: Fraction  # shares the pot
    equity: Fraction

    @property
    def loss(self) -> Fraction:
        return 1 - self.win - self.tie


@dataclass(frozen=True)
class ExactEquity:
    players: tuple[ExactPlayer, ...]
    scenarios: int  # (hand assignment, board) pairs enumerated


@dataclass(frozen=True)
class McPlayer:
    win: float
    tie: float
    equity: McResult

    @property
    def loss(self) -> float:
        return 1.0 - self.win - self.tie


@dataclass(frozen=True)
class McEquity:
    players: tuple[McPlayer, ...]
    trials: int  # accepted trials (hands that did not collide)


def _prepare(ranges: Sequence[Range], board: Sequence[int]) -> list[list[Combo]]:
    if len(ranges) < 2:
        raise ValueError("equity needs at least two players")
    if len(board) > 5:
        raise ValueError("a board has at most 5 cards")
    require_distinct(list(board))
    for r in ranges:
        for combo in r:
            if combo[0] == combo[1]:
                raise ValueError("duplicate card: a hand holds the same card twice")
    live = [remove_dead(r, board) for r in ranges]  # card removal against the board
    if any(not r for r in live):
        raise ValueError("duplicate card: a hand uses a card that is already on the board")
    return live


def _assignments(ranges: Sequence[Range]) -> list[tuple[Combo, ...]]:
    """Every way to give each player a hand from their range with no card used twice."""
    out = []
    for hands in product(*ranges):
        cards = [c for hand in hands for c in hand]
        if len(set(cards)) == len(cards):
            out.append(hands)
    return out


def exact_scenarios(ranges: Sequence[Range], board: Sequence[int]) -> int:
    """How many (assignment, board) pairs exact enumeration would visit."""
    live = _prepare(ranges, board)
    remaining = DECK_SIZE - len(board) - 2 * len(live)
    return len(_assignments(live)) * comb(remaining, 5 - len(board))


def _winner_counts(holes: Sequence[IntArray], boards: IntArray) -> IntArray:
    """counts[p, k] = number of rows where player p has the best hand and exactly k + 1
    players share it. `holes[p]` is (n, 2) or (1, 2); `boards` is (n, 5)."""
    n = len(boards)
    values = np.stack(
        [evaluate(np.concatenate([np.broadcast_to(h, (n, 2)), boards], axis=1)) for h in holes]
    )
    best = values == values.max(axis=0)
    sharing = best.sum(axis=0)
    players = len(holes)
    counts = np.zeros((players, players), dtype=np.int64)
    for p in range(players):
        counts[p] = np.bincount(sharing[best[p]] - 1, minlength=players)
    return counts


def equity_exact(ranges: Sequence[Range], board: Sequence[int] = ()) -> ExactEquity:
    live = _prepare(ranges, board)
    assignments = _assignments(live)
    if not assignments:
        raise ValueError("duplicate card: the hands cannot be dealt together")
    players = len(live)
    need = 5 - len(board)
    fixed = np.array(board, dtype=np.int64)
    counts = np.zeros((players, players), dtype=np.int64)
    scenarios = 0
    for hands in assignments:
        used = set(board) | {c for hand in hands for c in hand}
        deck = np.array([c for c in range(DECK_SIZE) if c not in used], dtype=np.int64)
        runouts = deck[combinations_array(len(deck), need)]
        boards = np.concatenate([np.broadcast_to(fixed, (len(runouts), len(fixed))), runouts], 1)
        holes = [np.array([hand], dtype=np.int64) for hand in hands]
        counts += _winner_counts(holes, boards)
        scenarios += len(boards)
    result = []
    for p in range(players):
        win = Fraction(int(counts[p, 0]), scenarios)
        tie = Fraction(int(counts[p, 1:].sum()), scenarios)
        equity = sum(
            (Fraction(int(counts[p, k]), scenarios * (k + 1)) for k in range(players)),
            Fraction(0),
        )
        result.append(ExactPlayer(win, tie, equity))
    return ExactEquity(tuple(result), scenarios)


def equity_mc(
    ranges: Sequence[Range], board: Sequence[int], trials: int, rng: np.random.Generator
) -> McEquity:
    """Sample a hand for each player (uniformly from their range, rejecting trials where
    two hands share a card), then the rest of the board from the unused cards."""
    live = _prepare(ranges, board)
    players = len(live)
    holes = np.stack(
        [np.array(r, dtype=np.int64)[rng.integers(0, len(r), trials)] for r in live], axis=1
    )  # (trials, players, 2)
    flat = np.sort(holes.reshape(trials, 2 * players), axis=1)
    ok = (np.diff(flat, axis=1) != 0).all(axis=1)
    holes = holes[ok]
    n = len(holes)
    if n < 2:
        raise ValueError("duplicate card: the hands cannot be dealt together")
    need = 5 - len(board)
    keys = rng.random((n, DECK_SIZE))
    rows = np.arange(n)
    for c in board:
        keys[:, c] = 2.0
    for p in range(players):
        for j in range(2):
            keys[rows, holes[:, p, j]] = 2.0
    runouts = np.argsort(keys, axis=1)[:, :need]  # the `need` smallest keys: a uniform draw
    fixed = np.broadcast_to(np.array(board, dtype=np.int64), (n, len(board)))
    boards = np.concatenate([fixed, runouts], axis=1)

    values = np.stack(
        [evaluate(np.concatenate([holes[:, p, :], boards], axis=1)) for p in range(players)]
    )
    best = values == values.max(axis=0)
    sharing = best.sum(axis=0)
    result = []
    for p in range(players):
        share = np.where(best[p], 1.0 / sharing, 0.0)
        se = float(share.std(ddof=1)) / float(np.sqrt(n))
        result.append(
            McPlayer(
                win=float((best[p] & (sharing == 1)).mean()),
                tie=float((best[p] & (sharing > 1)).mean()),
                equity=McResult(float(share.mean()), se, n),
            )
        )
    return McEquity(tuple(result), n)
