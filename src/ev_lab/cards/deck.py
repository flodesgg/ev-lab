"""Card representation: an integer 0..51.

rank = card // 4 (0 is a deuce, 12 is an ace); suit = card % 4 (clubs, diamonds, hearts,
spades). Text form is rank then suit: 'Ah', 'Td', '2c'.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

RANKS = "23456789TJQKA"
SUITS = "cdhs"
DECK_SIZE = 52


def make_card(rank: int, suit: int) -> int:
    return rank * 4 + suit


def rank_of(card: int) -> int:
    return card // 4


def suit_of(card: int) -> int:
    return card % 4


def card(text: str) -> int:
    """'Ah' -> integer. The rank letter may be lower case; '10' is written 'T'."""
    if len(text) != 2:
        raise ValueError(f"not a card: {text!r} (write rank then suit, like Ah or Td)")
    rank, suit = RANKS.find(text[0].upper()), SUITS.find(text[1].lower())
    if rank < 0 or suit < 0:
        raise ValueError(f"not a card: {text!r} (ranks {RANKS}, suits {SUITS})")
    return make_card(rank, suit)


def card_str(c: int) -> str:
    return RANKS[rank_of(c)] + SUITS[suit_of(c)]


def cards_str(cards: Iterable[int]) -> str:
    return "".join(card_str(c) for c in cards)


def parse_cards(text: str) -> list[int]:
    """'AhKh', 'Ah Kh' or 'Ah,Kh' -> list of cards. Duplicates are rejected."""
    compact = text.replace(" ", "").replace(",", "")
    if len(compact) % 2:
        raise ValueError(f"not a list of cards: {text!r}")
    cards = [card(compact[i : i + 2]) for i in range(0, len(compact), 2)]
    require_distinct(cards)
    return cards


def require_distinct(cards: Sequence[int]) -> None:
    seen: set[int] = set()
    for c in cards:
        if c in seen:
            raise ValueError(f"duplicate card: {card_str(c)} appears more than once")
        seen.add(c)
