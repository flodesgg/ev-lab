"""Kuhn poker (Kuhn, 1950): the smallest poker game with bluffing.

Three cards (J < Q < K), two players, each antes 1 and gets one card. One betting round
with a single bet of 1: player 1 passes (p) or bets (b); facing a bet a player folds (p) or
calls (b); after a pass player 2 may bet, and then player 1 must fold or call.

    history  meaning                      payoff to player 1
    pp       check, check: showdown       +1 / -1
    bp       bet, fold                    +1
    bb       bet, call: showdown          +2 / -2
    pbp      check, bet, fold             -1
    pbb      check, bet, call: showdown   +2 / -2

A player cannot see the opponent's card, so decisions are made per *information set*:
own card + history, e.g. "Kpb" = I hold the king, I checked, the opponent bet.
A strategy maps each information set to P(bet or call).
"""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from itertools import permutations, product

CARDS = "JQK"
ACTIONS = "pb"  # p = pass (check or fold), b = bet (or call)
TERMINAL = ("pp", "bp", "bb", "pbp", "pbb")
DEALS: tuple[tuple[int, int], ...] = tuple(permutations(range(3), 2))  # 6 equally likely

# information sets: card + history at which that player acts
P1_HISTORIES = ("", "pb")
P2_HISTORIES = ("p", "b")
INFOSETS: tuple[tuple[str, ...], tuple[str, ...]] = (
    tuple(c + h for c in CARDS for h in P1_HISTORIES),
    tuple(c + h for c in CARDS for h in P2_HISTORIES),
)

Strategy = Mapping[str, Fraction]  # infoset -> probability of action "b"


def player_to_act(history: str) -> int:
    return len(history) % 2


def payoff(deal: tuple[int, int], history: str) -> int:
    """Payoff to player 1 at a terminal history."""
    higher = 1 if deal[0] > deal[1] else -1
    if history == "pp":
        return higher
    if history == "bp":
        return 1
    if history == "pbp":
        return -1
    if history in ("bb", "pbb"):
        return 2 * higher
    raise ValueError(f"not a terminal history: {history!r}")


def infoset(deal: tuple[int, int], history: str) -> str:
    return CARDS[deal[player_to_act(history)]] + history


def to_exact(strategy: Mapping[str, float | Fraction]) -> dict[str, Fraction]:
    """Floats are converted exactly (a float is a binary fraction), not rounded."""
    return {k: Fraction(v) for k, v in strategy.items()}


def _value(deal: tuple[int, int], history: str, strategy: Strategy) -> Fraction:
    if history in TERMINAL:
        return Fraction(payoff(deal, history))
    bet = strategy[infoset(deal, history)]
    return (1 - bet) * _value(deal, history + "p", strategy) + bet * _value(
        deal, history + "b", strategy
    )


def expected_value(strategy: Strategy) -> Fraction:
    """Player 1's exact expected payoff when both players follow `strategy`."""
    return sum((_value(deal, "", strategy) for deal in DEALS), Fraction(0)) / len(DEALS)


def best_response_value(player: int, strategy: Strategy) -> Fraction:
    """The most `player` can earn (in their own payoff) against the other player's part of
    `strategy`. Brute force over the player's 2^6 = 64 pure strategies: obviously correct,
    and cheap in a game this small."""
    sign = 1 if player == 0 else -1
    best: Fraction | None = None
    for choice in product((Fraction(0), Fraction(1)), repeat=len(INFOSETS[player])):
        candidate = dict(strategy)
        candidate.update(zip(INFOSETS[player], choice, strict=True))
        value = sign * expected_value(candidate)
        if best is None or value > best:
            best = value
    assert best is not None
    return best


def exploitability(strategy: Strategy) -> Fraction:
    """Average gain available to a best-responding opponent: 0 exactly at a Nash
    equilibrium, positive otherwise. (best response of 1 vs 2) + (best response of 2 vs 1),
    divided by 2; the game is zero-sum so the game value cancels."""
    return (best_response_value(0, strategy) + best_response_value(1, strategy)) / 2


def equilibrium(alpha: Fraction) -> dict[str, Fraction]:
    """The one-parameter family of Nash equilibria (Kuhn, 1950), 0 <= alpha <= 1/3.
    Source checked: docs/sources.md. Verified in tests by exact computation: value -1/18
    and exploitability exactly 0 for every alpha tried."""
    if not 0 <= alpha <= Fraction(1, 3):
        raise ValueError("alpha must be between 0 and 1/3")
    third = Fraction(1, 3)
    return {
        # player 1, first action: bluff the jack with alpha, value-bet the king with 3 alpha
        "J": alpha,
        "Q": Fraction(0),
        "K": 3 * alpha,
        # player 1 after check-bet: fold the jack, call the queen sometimes, call the king
        "Jpb": Fraction(0),
        "Qpb": alpha + third,
        "Kpb": Fraction(1),
        # player 2 after a check: bluff the jack 1/3, check the queen, bet the king
        "Jp": third,
        "Qp": Fraction(0),
        "Kp": Fraction(1),
        # player 2 facing a bet: fold the jack, call the queen 1/3, call the king
        "Jb": Fraction(0),
        "Qb": third,
        "Kb": Fraction(1),
    }


GAME_VALUE = Fraction(-1, 18)  # for player 1; re-derived exactly in tests


def family_distance(strategy: Mapping[str, float | Fraction]) -> tuple[float, float]:
    """(alpha, largest deviation from the equilibrium with that alpha), where alpha is read
    off as P(bet | jack) and clipped to [0, 1/3]."""
    alpha = min(max(float(strategy["J"]), 0.0), 1 / 3)
    target = equilibrium(Fraction(alpha))
    return alpha, max(abs(float(strategy[k]) - float(target[k])) for k in target)
