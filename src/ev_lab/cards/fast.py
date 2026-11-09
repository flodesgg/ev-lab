"""Fast hand evaluation for many hands at once (numpy), 5 to 7 cards each.

Same integer values as the oracle in `evaluator.py`. Idea: describe a hand by 13-bit masks
(bit r set = rank r present) and look everything up in tables with 8192 entries.

    m1, m2, m3, m4   ranks that appear at least once / twice / three times / four times
    fm               ranks of the flush suit, if five or more cards share a suit

Why seven cards need care (each is a test case):
  * the best hand is not "the best pattern you can see": with two sets of trips the lower
    trips act as the pair of a full house; with three pairs the third pair's rank competes
    for the kicker with the seventh card;
  * a straight and a flush in the same seven cards are a straight flush only if five
    *suited* cards are consecutive, so the straight test must run on the flush mask;
  * with six or seven suited cards the flush uses the top five of that suit;
  * the ace is low in A-2-3-4-5, where the straight's high card is the five.
"""

from __future__ import annotations

from math import comb

import numpy as np
from numpy.typing import NDArray

from ev_lab.cards.evaluator import (
    BASE,
    FLUSH,
    FULL_HOUSE,
    PAIR,
    QUADS,
    STRAIGHT,
    STRAIGHT_FLUSH,
    TRIPS,
    TWO_PAIR,
)

IntArray = NDArray[np.int64]

_N = 1 << 13
_W = [13**4, 13**3, 13**2, 13, 1]  # weight of tiebreaker digit 0..4


def _bits_desc(mask: int) -> list[int]:
    return [r for r in range(12, -1, -1) if mask >> r & 1]


def _straight_high(mask: int) -> int:
    for high in range(12, 3, -1):
        if all(mask >> r & 1 for r in range(high - 4, high + 1)):
            return high
    wheel = (1 << 12) | 0b1111
    return 3 if mask & wheel == wheel else -1


def _digits(mask: int, count: int, first_digit: int) -> int:
    """The top `count` ranks of `mask`, written from tiebreaker position `first_digit`."""
    return sum(r * _W[first_digit + i] for i, r in enumerate(_bits_desc(mask)[:count]))


HIGH = np.array([max(m.bit_length() - 1, 0) for m in range(_N)], dtype=np.int64)
POPCOUNT = np.array([m.bit_count() for m in range(_N)], dtype=np.int64)
STRAIGHT_HIGH = np.array([_straight_high(m) for m in range(_N)], dtype=np.int64)
TOP5 = np.array([_digits(m, 5, 0) for m in range(_N)], dtype=np.int64)
KICK3 = np.array([_digits(m, 3, 1) for m in range(_N)], dtype=np.int64)  # after a pair
KICK2 = np.array([_digits(m, 2, 1) for m in range(_N)], dtype=np.int64)  # after trips


def evaluate(cards: NDArray[np.integer]) -> IntArray:
    """Values of n hands given as an (n, k) array of card integers, k = 5, 6 or 7."""
    hands = np.asarray(cards, dtype=np.int64)
    if hands.ndim != 2 or not 5 <= hands.shape[1] <= 7:
        raise ValueError("expected an (n, k) array with k = 5, 6 or 7")
    n, k = hands.shape
    bit = np.left_shift(1, hands >> 2)
    suit = hands & 3

    m1 = np.zeros(n, dtype=np.int64)
    m2, m3, m4 = m1.copy(), m1.copy(), m1.copy()
    suit_masks = [m1.copy() for _ in range(4)]
    for j in range(k):
        b = bit[:, j]
        m4 |= m3 & b  # order matters: promote from the highest count down
        m3 |= m2 & b
        m2 |= m1 & b
        m1 |= b
        for s in range(4):
            suit_masks[s] |= np.where(suit[:, j] == s, b, 0)

    fm = np.zeros(n, dtype=np.int64)
    for s in range(4):
        fm = np.where(POPCOUNT[suit_masks[s]] >= 5, suit_masks[s], fm)

    sf_high = STRAIGHT_HIGH[fm]
    straight_high = STRAIGHT_HIGH[m1]

    quad = HIGH[m4]
    quads_value = quad * _W[0] + HIGH[m1 & ~(1 << quad)] * _W[1]

    trip = HIGH[m3]
    pairs_besides_trip = m2 & ~(1 << trip)  # includes a second, lower set of trips
    full_value = trip * _W[0] + HIGH[pairs_besides_trip] * _W[1]
    trips_value = trip * _W[0] + KICK2[m1 & ~(1 << trip)]

    pair1 = HIGH[m2]
    lower_pairs = m2 & ~(1 << pair1)
    pair2 = HIGH[lower_pairs]
    kicker = HIGH[m1 & ~(1 << pair1) & ~(1 << pair2)]  # may be a third pair's rank
    two_pair_value = pair1 * _W[0] + pair2 * _W[1] + kicker * _W[2]
    pair_value = pair1 * _W[0] + KICK3[m1 & ~(1 << pair1)]

    values = np.select(
        [
            sf_high >= 0,
            m4 != 0,
            (m3 != 0) & (pairs_besides_trip != 0),
            fm != 0,
            straight_high >= 0,
            m3 != 0,
            lower_pairs != 0,
            m2 != 0,
        ],
        [
            STRAIGHT_FLUSH * BASE + sf_high * _W[0],
            QUADS * BASE + quads_value,
            FULL_HOUSE * BASE + full_value,
            FLUSH * BASE + TOP5[fm],
            STRAIGHT * BASE + straight_high * _W[0],
            TRIPS * BASE + trips_value,
            TWO_PAIR * BASE + two_pair_value,
            PAIR * BASE + pair_value,
        ],
        default=TOP5[m1],
    )
    return np.asarray(values, dtype=np.int64)


def evaluate_one(cards: list[int] | tuple[int, ...]) -> int:
    return int(evaluate(np.array([cards], dtype=np.int64))[0])


def combinations_array(n: int, k: int) -> IntArray:
    """All k-subsets of range(n) as a (C(n, k), k) array, in *colex* order (sorted by the
    largest element, then the next largest, ...). In that order the subsets of range(m)
    are exactly the first C(m, k) rows, for every m <= n."""
    if k == 0:
        return np.zeros((1, 0), dtype=np.int64)
    if k > n:
        return np.zeros((0, k), dtype=np.int64)
    # Build colex order directly: the subsets whose largest element is `top` are the
    # (k-1)-subsets of range(top), each extended by `top`.
    smaller = combinations_array(n - 1, k - 1)
    counts = _binomials(n, k - 1)
    blocks = [
        np.column_stack([smaller[: counts[top]], np.full(counts[top], top, dtype=np.int64)])
        for top in range(k - 1, n)
    ]
    return np.concatenate(blocks)


def _binomials(n: int, k: int) -> list[int]:
    """[C(0, k), C(1, k), ..., C(n - 1, k)]."""
    return [comb(m, k) for m in range(n)]


def category_counts(cards_per_hand: int) -> list[int]:
    """Number of hands in each category (index 0 = high card .. 8 = straight flush) over
    every `cards_per_hand`-card subset of the deck. Seven cards: 133,784,560 hands, slow."""
    if cards_per_hand not in (5, 6, 7):
        raise ValueError("cards_per_hand must be 5, 6 or 7")
    counts = np.zeros(9, dtype=np.int64)
    extra = cards_per_hand - 5
    lower = combinations_array(52 - extra, 5)  # the five smallest cards of each hand
    # choose the `extra` largest cards explicitly; the rest are a colex prefix below them
    for top in combinations_array(52, extra):
        smallest_top = int(top[0]) if extra else 52
        rows = lower[: comb(smallest_top, 5)]
        if len(rows) == 0:
            continue
        hands = np.column_stack([rows, np.tile(top, (len(rows), 1))]) if extra else rows
        counts += np.bincount(evaluate(hands) // BASE, minlength=9)
    return [int(c) for c in counts]
