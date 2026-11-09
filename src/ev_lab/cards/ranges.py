"""Hold'em starting-hand ranges in the usual shorthand.

    AhKh        one specific combination
    TT          a pair (6 combinations)        TT+     that pair and all higher pairs
    AKs / AKo   suited (4) / offsuit (12)      AK      both (16)
    AQs+        AQs and AKs: raise the lower card up to just below the higher one
    A5s-A2s     a span with the same high card; 99-66 a span of pairs
    TT+,AQs+    a comma-separated list

A combination is a pair of card integers (higher card first). Card removal: combinations
that use a card already dealt elsewhere are dropped with `remove_dead`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from ev_lab.cards.deck import RANKS, card, make_card

Combo = tuple[int, int]


def _combo(a: int, b: int) -> Combo:
    return (a, b) if a > b else (b, a)


def _pair(rank: int) -> list[Combo]:
    return [_combo(make_card(rank, s), make_card(rank, t)) for s in range(4) for t in range(s)]


def _unpaired(high: int, low: int, kind: str) -> list[Combo]:
    out = []
    for s in range(4):
        for t in range(4):
            if (kind == "s" and s == t) or (kind == "o" and s != t) or kind == "":
                out.append(_combo(make_card(high, s), make_card(low, t)))
    return out


def _parse_hand_class(token: str) -> tuple[int, int, str]:
    """'AKs' -> (12, 11, 's'); 'TT' -> (8, 8, ''); the higher rank first."""
    if len(token) not in (2, 3):
        raise ValueError(f"not a hand: {token!r}")
    a, b = RANKS.find(token[0].upper()), RANKS.find(token[1].upper())
    kind = token[2:].lower()
    if a < 0 or b < 0 or kind not in ("", "s", "o"):
        raise ValueError(f"not a hand: {token!r}")
    if a == b and kind:
        raise ValueError(f"a pair cannot be suited or offsuit: {token!r}")
    return max(a, b), min(a, b), kind


def _class_combos(high: int, low: int, kind: str) -> list[Combo]:
    return _pair(high) if high == low else _unpaired(high, low, kind)


def _parse_token(token: str) -> list[Combo]:
    if len(token) == 4 and token[1].lower() in "cdhs" and token[3].lower() in "cdhs":
        a, b = card(token[:2]), card(token[2:])
        if a == b:
            raise ValueError(f"duplicate card in {token!r}")
        return [_combo(a, b)]
    if "-" in token:
        left, right = token.split("-", 1)
        h1, l1, k1 = _parse_hand_class(left)
        h2, l2, k2 = _parse_hand_class(right)
        if k1 != k2:
            raise ValueError(f"a span must not mix suited and offsuit: {token!r}")
        if h1 == l1 and h2 == l2:  # pairs: 99-66
            lo, hi = sorted((h1, h2))
            return [c for r in range(lo, hi + 1) for c in _pair(r)]
        if h1 != h2 or h1 == l1 or h2 == l2:
            raise ValueError(f"a span needs the same high card on both sides: {token!r}")
        lo, hi = sorted((l1, l2))
        return [c for low in range(lo, hi + 1) for c in _unpaired(h1, low, k1)]
    if token.endswith("+"):
        high, low, kind = _parse_hand_class(token[:-1])
        if high == low:
            return [c for r in range(high, 13) for c in _pair(r)]
        return [c for lw in range(low, high) for c in _unpaired(high, lw, kind)]
    return _class_combos(*_parse_hand_class(token))


def parse_range(text: str) -> list[Combo]:
    """All combinations of a range, without repeats, in a stable order."""
    tokens = [t.strip() for t in text.split(",") if t.strip()]
    if not tokens:
        raise ValueError("empty range")
    seen: dict[Combo, None] = {}
    for token in tokens:
        for combo in _parse_token(token):
            seen.setdefault(combo, None)
    return list(seen)


def remove_dead(combos: Iterable[Combo], dead: Sequence[int]) -> list[Combo]:
    """Card removal: drop every combination that uses a card in `dead`."""
    blocked = set(dead)
    return [c for c in combos if c[0] not in blocked and c[1] not in blocked]
