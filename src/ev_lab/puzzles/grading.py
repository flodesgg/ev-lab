"""Reading and grading an answer typed at the prompt."""

from __future__ import annotations

from fractions import Fraction

from ev_lab.puzzles.base import Puzzle


def parse_number(text: str, percent_divides: bool = True) -> Fraction:
    """'7/2', '3.5', '35%', '1,000' or ' 0.25 ' as an exact Fraction. ValueError otherwise.
    A trailing % divides by 100 (35% -> 7/20) unless `percent_divides` is False, in which
    case the sign is just dropped (for questions whose answer is itself a percentage)."""
    cleaned = text.strip().replace(",", "").replace("$", "").replace(" ", "")
    percent = cleaned.endswith("%")
    if percent:
        cleaned = cleaned[:-1]
    try:
        value = Fraction(cleaned)
    except (ValueError, ZeroDivisionError) as e:
        raise ValueError(f"not a number: {text!r} (use a fraction like 7/2 or a decimal)") from e
    return value / 100 if percent and percent_divides else value


def number_is_correct(answer: Fraction, exact: Fraction, rel_tolerance: float) -> bool:
    """Within the relative tolerance of the exact value (absolute if the exact value is 0)."""
    tol = Fraction(rel_tolerance).limit_denominator(10**9)
    scale = abs(exact) if exact != 0 else Fraction(1)
    return abs(answer - exact) <= tol * scale


def market_is_correct(bid: Fraction, ask: Fraction, fair: Fraction, max_width: Fraction) -> bool:
    """A valid two-sided quote, no wider than allowed, that contains the fair value."""
    return bid < ask and ask - bid <= max_width and bid <= fair <= ask


def market_feedback(bid: Fraction, ask: Fraction, fair: Fraction, puzzle: Puzzle) -> str:
    assert puzzle.max_width is not None
    if bid >= ask:
        return "the bid must be below the ask"
    if ask - bid > puzzle.max_width:
        return f"the quote is wider than the allowed {puzzle.max_width}"
    if fair < bid:
        return "the fair value is below your bid: a seller hits your bid and you overpay"
    if fair > ask:
        return "the fair value is above your ask: a buyer lifts your offer and you sell cheap"
    return "the fair value is inside your quote"
