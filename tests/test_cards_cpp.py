"""The C++ evaluator: same values as the Python oracle and numpy, same category counts."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from test_cards import SEVEN_CARD_EDGE_CASES, random_hands

from ev_lab.cards import cpp
from ev_lab.cards.deck import parse_cards
from ev_lab.cards.evaluator import rank5, rank7_oracle
from ev_lab.cards.fast import combinations_array, evaluate
from ev_lab.cards.reference import FIVE_CARD_COUNTS, SEVEN_CARD_COUNTS, SEVEN_CARD_TOTAL
from ev_lab.reports import cpp_check
from ev_lab.runinfo import RunInfo

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def _compiled() -> None:
    try:
        cpp.build()
    except cpp.CppUnavailableError as e:  # no compiler on this machine: say so, do not pass
        pytest.skip(f"C++ evaluator not built: {e}")


def test_binary_is_rebuilt_only_when_sources_change() -> None:
    first = cpp.build()
    stamp = first.stat().st_mtime
    assert cpp.build().stat().st_mtime == stamp  # up to date: no recompilation
    assert first == cpp.binary_path() and first.parent.name == "build"


@pytest.mark.parametrize(("name", "seven", "category", "best_five"), SEVEN_CARD_EDGE_CASES)
def test_edge_cases(name: str, seven: str, category: int, best_five: str) -> None:
    value = int(cpp.evaluate(np.array([parse_cards(seven)]))[0])
    assert value == rank5(parse_cards(best_five)), name
    assert value // 13**5 == category, name


def test_agrees_with_the_oracle_on_random_hands() -> None:
    hands = random_hands(20_000, 7, seed=11)
    assert cpp.evaluate(hands).tolist() == [rank7_oracle(h) for h in hands.tolist()]


def test_agrees_with_numpy_on_five_six_and_seven_cards() -> None:
    for k in (5, 6, 7):
        hands = random_hands(200_000, k, seed=12 + k)
        assert (cpp.evaluate(hands) == evaluate(hands)).all(), k


def test_agrees_with_numpy_on_every_five_card_hand() -> None:
    hands = combinations_array(52, 5)
    assert (cpp.evaluate(hands) == evaluate(hands)).all()


def test_category_counts_of_all_five_and_seven_card_hands() -> None:
    assert cpp.category_counts(5).counts == FIVE_CARD_COUNTS
    seven = cpp.category_counts(7)  # all 133,784,560 hands, a second or two in C++
    assert seven.counts == SEVEN_CARD_COUNTS and sum(seven.counts) == SEVEN_CARD_TOTAL
    assert seven.seconds > 0


def test_bad_input_is_rejected_with_a_clear_error() -> None:
    with pytest.raises(ValueError, match="duplicate card 1"):
        cpp.evaluate(np.array([[1, 1, 2, 3, 4]]))
    with pytest.raises(ValueError, match=r"not in 0\.\.51"):
        cpp.evaluate(np.array([[0, 1, 2, 3, 52]]))
    with pytest.raises(ValueError, match="k = 5, 6 or 7"):
        cpp.evaluate(np.array([[0, 1, 2, 3]]))
    assert len(cpp.evaluate(np.zeros((0, 7), dtype=np.int64))) == 0


def test_benchmark_reports_a_positive_speed() -> None:
    assert cpp.benchmark(200_000) > 1_000_000  # even a slow machine clears a million a second


def test_missing_sources_are_reported(tmp_path: Path) -> None:
    with pytest.raises(cpp.CppUnavailableError, match="sources not found"):
        cpp.build(root=tmp_path)


def _fixed(**changes: object) -> cpp_check.CppCheck:
    base: dict[str, object] = {
        "five_counts": FIVE_CARD_COUNTS,
        "seven_counts": SEVEN_CARD_COUNTS,
        "seven_seconds": 1.5,
        "oracle_hands": 1000,
        "oracle_mismatches": 0,
        "numpy_hands": 5000,
        "numpy_mismatches": 0,
        "cpp_hands_per_second": 80_000_000.0,
        "numpy_hands_per_second": 1_250_000.0,
    }
    return cpp_check.CppCheck(**(base | changes))  # type: ignore[arg-type]


def test_cpp_report_regression() -> None:
    """Fixed inputs must render exactly the stored file."""
    info = RunInfo(
        "20260101T000000Z-abcdef",
        "2026-01-01T00:00:00+00:00",
        "0123456789ab",
        False,
        "feedfacecafe",
        7,
    )
    text = cpp_check.render(_fixed(), info)
    assert _fixed().ok() and text.index("## Limitations") < text.index("## Result")
    assert text == (REPO / "tests" / "expected" / "cpp_check.md").read_text()
    assert not _fixed(numpy_mismatches=1).ok() and not _fixed(oracle_mismatches=2).ok()
    wrong = list(SEVEN_CARD_COUNTS)
    wrong[0] += 1
    assert not _fixed(seven_counts=wrong).ok()
    assert "**NO**" in cpp_check.render(_fixed(seven_counts=wrong), info)
