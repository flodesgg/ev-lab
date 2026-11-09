"""Hand evaluation: the simple, obviously correct version (the oracle).

A hand's strength is one integer, so that a higher number always means a better hand:

    value = category * 13^5 + tiebreakers written as up to five base-13 digits

Categories 0..8: high card, pair, two pair, three of a kind, straight, flush, full house,
four of a kind, straight flush. Tiebreakers are ranks (0 = deuce .. 12 = ace) in order of
importance, e.g. for two pair: higher pair, lower pair, kicker.

The 7-card value is the best of the 21 five-card subsets. This is slow and is used to
check the fast evaluator (`cards/fast.py`).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from itertools import combinations

BASE = 13**5
HIGH_CARD, PAIR, TWO_PAIR, TRIPS, STRAIGHT, FLUSH, FULL_HOUSE, QUADS, STRAIGHT_FLUSH = range(9)
CATEGORY_NAMES = (
    "high card",
    "one pair",
    "two pair",
    "three of a kind",
    "straight",
    "flush",
    "full house",
    "four of a kind",
    "straight flush",
)
WHEEL = [12, 3, 2, 1, 0]  # A-5-4-3-2: the ace plays low, the five is the high card


def encode(category: int, tiebreakers: Sequence[int]) -> int:
    value = 0
    for i in range(5):
        value = value * 13 + (tiebreakers[i] if i < len(tiebreakers) else 0)
    return category * BASE + value


def category_of(value: int) -> int:
    return value // BASE


def rank5(cards: Sequence[int]) -> int:
    """Value of exactly five cards."""
    if len(cards) != 5:
        raise ValueError("rank5 needs exactly 5 cards")
    ranks = sorted((c // 4 for c in cards), reverse=True)
    flush = len({c % 4 for c in cards}) == 1
    # ranks grouped by how often they appear: most frequent first, then higher rank first
    groups = sorted(Counter(ranks).items(), key=lambda rc: (rc[1], rc[0]), reverse=True)
    shape = [count for _, count in groups]
    by_importance = [rank for rank, _ in groups]

    straight_high = None
    if shape == [1, 1, 1, 1, 1]:
        if ranks[0] - ranks[4] == 4:
            straight_high = ranks[0]
        elif ranks == WHEEL:
            straight_high = 3

    if straight_high is not None:
        return encode(STRAIGHT_FLUSH if flush else STRAIGHT, [straight_high])
    if shape == [4, 1]:
        return encode(QUADS, by_importance)
    if shape == [3, 2]:
        return encode(FULL_HOUSE, by_importance)
    if flush:
        return encode(FLUSH, ranks)
    if shape == [3, 1, 1]:
        return encode(TRIPS, by_importance)
    if shape == [2, 2, 1]:
        return encode(TWO_PAIR, by_importance)
    if shape == [2, 1, 1, 1]:
        return encode(PAIR, by_importance)
    return encode(HIGH_CARD, ranks)


def rank7_oracle(cards: Sequence[int]) -> int:
    """Best five-card value among 5, 6 or 7 cards, by trying every five-card subset."""
    if not 5 <= len(cards) <= 7:
        raise ValueError("need 5, 6 or 7 cards")
    return max(rank5(five) for five in combinations(cards, 5))
