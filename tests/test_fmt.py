"""Printing exact numbers."""

from __future__ import annotations

from fractions import Fraction as F

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ev_lab.fmt import dec, is_terminating, signed
from ev_lab.puzzles.base import format_answer


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (F(7), "7"),
        (F(1692, 100), "16.92"),
        (F(1, 8), "0.125"),
        (F(-3, 4), "-0.75"),
        (F(100, 7), "14.2857"),
        (F(1, 3), "0.3333"),
        (F(1000), "1000"),
    ],
)
def test_dec(value: F, text: str) -> None:
    assert dec(value) == text


def test_dec_places_and_signed() -> None:
    assert dec(F(2, 3), 2) == "0.67"
    assert signed(F(5, 2)) == "+2.50" and signed(F(-1, 3), 3) == "-0.333"


def test_is_terminating() -> None:
    assert is_terminating(F(3, 40)) and is_terminating(F(5)) and is_terminating(F(1, 1024))
    assert not is_terminating(F(1, 3)) and not is_terminating(F(5, 14))


@given(st.integers(-(10**6), 10**6), st.integers(0, 6), st.integers(0, 6))
def test_terminating_decimals_round_trip_exactly(n: int, twos: int, fives: int) -> None:
    value = F(n, 2**twos * 5**fives)
    assert F(dec(value)) == value


def test_format_answer() -> None:
    assert format_answer(F(6)) == "6"
    assert format_answer(F(7, 2)) == "7/2 (~ 3.5)"
