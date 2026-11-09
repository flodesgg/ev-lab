"""Cards: deck, evaluators (oracle vs fast), enumeration counts, ranges, equity, pot odds."""

from __future__ import annotations

import itertools
import math
from fractions import Fraction as F
from pathlib import Path

import numpy as np
import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st
from typer.testing import CliRunner

from ev_lab.cards.deck import card, card_str, cards_str, parse_cards
from ev_lab.cards.equity import equity_exact, equity_mc, exact_scenarios
from ev_lab.cards.evaluator import (
    CATEGORY_NAMES,
    FLUSH,
    FULL_HOUSE,
    HIGH_CARD,
    PAIR,
    QUADS,
    STRAIGHT,
    STRAIGHT_FLUSH,
    TRIPS,
    TWO_PAIR,
    category_of,
    rank5,
    rank7_oracle,
)
from ev_lab.cards.fast import category_counts, combinations_array, evaluate, evaluate_one
from ev_lab.cards.potodds import breakeven_equity, call_ev
from ev_lab.cards.ranges import Combo, parse_range, remove_dead
from ev_lab.cards.reference import (
    FIVE_CARD_COUNTS,
    FIVE_CARD_TOTAL,
    SEVEN_CARD_COUNTS,
    SEVEN_CARD_TOTAL,
)
from ev_lab.cli import app
from ev_lab.prob.montecarlo import McResult, assert_agrees
from ev_lab.reports import cards_check
from ev_lab.runinfo import RunInfo

REPO = Path(__file__).resolve().parents[1]
runner = CliRunner()


def H(text: str) -> list[int]:
    return parse_cards(text)


def hand(text: str) -> list[Combo]:
    return parse_range(text)


def random_hands(n: int, k: int, seed: int) -> np.ndarray:  # type: ignore[type-arg]
    rng = np.random.default_rng(seed)
    return rng.permuted(np.tile(np.arange(52), (n, 1)), axis=1)[:, :k]


# ---- deck ------------------------------------------------------------------------------


def test_card_round_trip() -> None:
    assert [card_str(c) for c in range(52)] == [r + s for r in "23456789TJQKA" for s in "cdhs"]
    assert all(card(card_str(c)) == c for c in range(52))
    assert card("ah") == card("Ah") == 50
    assert cards_str(H("Ah Kh, 2c")) == "AhKh2c"


@pytest.mark.parametrize("bad", ["A", "1h", "Ax", "AhK", "10h"])
def test_bad_cards_are_rejected(bad: str) -> None:
    with pytest.raises(ValueError, match="not a"):
        parse_cards(bad)


def test_duplicate_cards_are_rejected_with_a_clear_error() -> None:
    with pytest.raises(ValueError, match="duplicate card: Ah"):
        parse_cards("AhKhAh")


# ---- oracle: categories and ordering by hand -------------------------------------------

EXAMPLES = [
    ("AsKsQsJsTs", STRAIGHT_FLUSH),
    ("5h4h3h2hAh", STRAIGHT_FLUSH),  # steel wheel
    ("9c9d9h9sKd", QUADS),
    ("KcKdKh2s2d", FULL_HOUSE),
    ("Ah9h7h4h2h", FLUSH),
    ("Ts9d8h7c6s", STRAIGHT),
    ("5s4d3h2cAs", STRAIGHT),  # wheel
    ("QcQdQh7s2d", TRIPS),
    ("JcJd4h4s9d", TWO_PAIR),
    ("8c8dAhKs2d", PAIR),
    ("AcJd8h6s2d", HIGH_CARD),
]


@pytest.mark.parametrize(("text", "category"), EXAMPLES)
def test_five_card_categories(text: str, category: int) -> None:
    assert category_of(rank5(H(text))) == category
    assert category_of(evaluate_one(H(text))) == category
    assert len(CATEGORY_NAMES) == 9


def test_ordering_within_categories_by_hand() -> None:
    def better(a: str, b: str) -> bool:
        return rank5(H(a)) > rank5(H(b))

    assert better("6s5d4h3c2s", "5s4d3h2cAs")  # six-high straight beats the wheel
    assert better("6h5h4h3h2h", "5h4h3h2hAh")  # and the steel wheel is the lowest SF
    assert better("AsKsQsJsTs", "KsQsJsTs9s")
    assert better("2c2d2h2sAd", "AcAdAhKsKd")  # any quads beat any full house
    assert better("3c3d3h2s2d", "2c2d2hAsAd")  # full house: trips first
    assert better("AhKh7h4h3h", "AhQhJhTh9h")  # flush: card by card
    assert better("KcKd2h2s3d", "QcQdJhJsAd")  # two pair: top pair first
    assert better("KcKd3h3sAd", "KcKd3h3sQd")  # then the kicker
    assert better("8c8dAhKs3d", "8c8dAhKs2d")  # pair: third kicker decides
    assert rank5(H("AcKdQhJs9d")) == rank5(H("AdKhQsJc9h"))  # suits never break ties
    assert rank5(H("5s4d3h2cAs")) < rank5(H("6s5d4h3c2s")) < rank5(H("AsKdQhJcTs"))


def test_evaluators_reject_wrong_sizes() -> None:
    with pytest.raises(ValueError):
        rank5(H("AsKs"))
    with pytest.raises(ValueError):
        rank7_oracle(H("AsKsQsJs"))
    with pytest.raises(ValueError):
        evaluate(np.zeros((3, 4), dtype=np.int64))


# ---- fast evaluator vs oracle ----------------------------------------------------------

SEVEN_CARD_EDGE_CASES = [
    ("wheel", "As2d3h4c5s9dKh", STRAIGHT, "5s4c3h2dAs"),
    ("steel wheel", "Ah2h3h4h5hKsKd", STRAIGHT_FLUSH, "5h4h3h2hAh"),
    ("wheel loses to six-high in the same seven", "As2d3h4c5s6dKh", STRAIGHT, "6d5s4c3h2d"),
    ("flush and straight, not a straight flush", "9h8h7h6d5c2hKh", FLUSH, "Kh9h8h7h2h"),
    (
        "straight flush hidden below a higher flush card",
        "Kh9h8h7h6h5h2c",
        STRAIGHT_FLUSH,
        "9h8h7h6h5h",
    ),
    (
        "straight flush beats a higher plain straight",
        "9h8h7h6h5hTdJc",
        STRAIGHT_FLUSH,
        "9h8h7h6h5h",
    ),
    ("two sets of trips make a full house", "KcKdKh7s7d7hAc", FULL_HOUSE, "KcKdKh7s7d"),
    ("trips and two pairs: best pair fills", "KcKdKh7s7d9h9c", FULL_HOUSE, "KcKdKh9h9c"),
    ("three pairs: best two plus best kicker", "AcAdKhKs3d3h2c", TWO_PAIR, "AcAdKhKs3d"),
    ("three pairs where the third pair is the kicker", "AcAdKhKsQdQh2c", TWO_PAIR, "AcAdKhKsQd"),
    ("three pairs where the seventh card is the kicker", "9c9d5h5s3d3hAc", TWO_PAIR, "9c9d5h5sAc"),
    ("quads with a pair: best kicker", "8c8d8h8sKdKh2c", QUADS, "8c8d8h8sKd"),
    ("quads with trips", "8c8d8h8sKdKhKc", QUADS, "8c8d8h8sKd"),
    ("seven-card flush uses the top five", "AhQh9h7h5h3h2h", FLUSH, "AhQh9h7h5h"),
    ("broadway inside seven", "AsKdQhJcTs2d3h", STRAIGHT, "AsKdQhJcTs"),
    ("long straight uses the top end", "4c5d6h7s8d9hTc", STRAIGHT, "Tc9h8d7s6h"),
    ("ace does not wrap around", "QcKdAh2s3d7h9c", HIGH_CARD, "AhKdQc9c7h"),
    ("full house beats flush in the same seven", "KhKdKc7h7d2h3h", FULL_HOUSE, "KhKdKc7h7d"),
]


@pytest.mark.parametrize(("name", "seven", "category", "best_five"), SEVEN_CARD_EDGE_CASES)
def test_seven_card_edge_cases(name: str, seven: str, category: int, best_five: str) -> None:
    cards = H(seven)
    expected = rank5(H(best_five))  # the best five cards, written out by hand
    assert category_of(expected) == category, name
    assert rank7_oracle(cards) == expected, name
    assert evaluate_one(cards) == expected, name


def test_fast_agrees_with_oracle_on_random_seven_card_hands() -> None:
    hands = random_hands(20_000, 7, seed=1)
    oracle = np.array([rank7_oracle(h) for h in hands.tolist()])
    assert (evaluate(hands) == oracle).all()


def test_fast_agrees_with_oracle_on_six_card_hands() -> None:
    hands = random_hands(5_000, 6, seed=2)
    oracle = np.array([rank7_oracle(h) for h in hands.tolist()])
    assert (evaluate(hands) == oracle).all()


@pytest.mark.slow
def test_fast_agrees_with_oracle_on_a_million_random_hands() -> None:
    hands = random_hands(1_000_000, 7, seed=3)
    fast = evaluate(hands)
    for start in range(0, len(hands), 50_000):
        chunk = hands[start : start + 50_000].tolist()
        assert fast[start : start + 50_000].tolist() == [rank7_oracle(h) for h in chunk]


@pytest.mark.slow
def test_fast_agrees_with_oracle_on_every_five_card_hand() -> None:
    hands = combinations_array(52, 5)
    fast = evaluate(hands)
    for start in range(0, len(hands), 100_000):
        chunk = hands[start : start + 100_000].tolist()
        assert fast[start : start + 100_000].tolist() == [rank5(h) for h in chunk]


# ---- enumeration counts ----------------------------------------------------------------


def test_all_five_card_hands_category_counts() -> None:
    counts = category_counts(5)
    assert sum(counts) == FIVE_CARD_TOTAL == math.comb(52, 5)
    assert tuple(counts) == FIVE_CARD_COUNTS


@pytest.mark.slow
def test_all_five_card_hands_category_counts_with_the_oracle() -> None:
    counts = [0] * 9
    for five in itertools.combinations(range(52), 5):
        counts[category_of(rank5(five))] += 1
    assert tuple(counts) == FIVE_CARD_COUNTS


@pytest.mark.slow
def test_all_seven_card_hands_category_counts() -> None:
    counts = category_counts(7)
    assert sum(counts) == SEVEN_CARD_TOTAL == math.comb(52, 7)
    assert tuple(counts) == SEVEN_CARD_COUNTS


def test_combinations_array_is_complete_and_colex() -> None:
    for n, k in [(6, 3), (7, 0), (5, 5), (8, 2), (4, 5)]:
        rows = [tuple(r) for r in combinations_array(n, k).tolist()]
        assert sorted(rows) == sorted(itertools.combinations(range(n), k))
        assert rows == sorted(rows, key=lambda r: r[::-1])  # colex order
    # prefix property used by the enumerators
    assert (combinations_array(9, 3)[:20] == combinations_array(6, 3)).all()


# ---- evaluator properties --------------------------------------------------------------

seven_cards = st.lists(st.integers(0, 51), min_size=7, max_size=7, unique=True)


@given(seven_cards, st.permutations(range(7)), st.permutations(range(4)))
def test_value_ignores_card_order_and_suit_names(
    cards: list[int], order: list[int], suits: list[int]
) -> None:
    base = evaluate_one(cards)
    assert evaluate_one([cards[i] for i in order]) == base  # a hand never beats itself
    relabelled = [(c // 4) * 4 + suits[c % 4] for c in cards]
    assert evaluate_one(relabelled) == base


@given(seven_cards)
def test_seven_cards_are_at_least_as_good_as_any_five_of_them(cards: list[int]) -> None:
    value = evaluate_one(cards)
    fives = [rank5(five) for five in itertools.combinations(cards, 5)]
    assert value == max(fives)
    assert evaluate_one(cards[:6]) <= value


@given(seven_cards, seven_cards, seven_cards)
def test_comparison_is_transitive(a: list[int], b: list[int], c: list[int]) -> None:
    va, vb, vc = evaluate_one(a), evaluate_one(b), evaluate_one(c)
    if va >= vb and vb >= vc:
        assert va >= vc
    # the oracle and the fast evaluator order every pair the same way
    assert (va > vb) == (rank7_oracle(a) > rank7_oracle(b))


# ---- ranges ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "count"),
    [
        ("AA", 6),
        ("AKs", 4),
        ("AKo", 12),
        ("AK", 16),
        ("TT+", 30),
        ("AQs+", 8),
        ("KTs+", 12),
        ("A5s-A2s", 16),
        ("A2s-A5s", 16),
        ("99-66", 24),
        ("TT+,AQs+", 38),
        ("AhKh", 1),
        ("AA,AA,AKs", 10),
        ("ATo+", 48),
    ],
)
def test_range_sizes(text: str, count: int) -> None:
    combos = parse_range(text)
    assert len(combos) == count == len(set(combos))
    assert all(a > b for a, b in combos)


def test_range_contents() -> None:
    assert set(parse_range("AKs")) == {(card(f"A{s}"), card(f"K{s}")) for s in "cdhs"}
    assert all(a % 4 != b % 4 for a, b in parse_range("AKo"))
    lows = {b // 4 for _, b in parse_range("A5s-A2s")}
    assert lows == {0, 1, 2, 3}
    assert {a // 4 for a, _ in parse_range("TT+")} == {8, 9, 10, 11, 12}
    assert parse_range("KQo") == parse_range("QKo")


@pytest.mark.parametrize("bad", ["", "AKx", "AAs", "A5s-K2s", "A5s-A2o", "XY", "AhAh", "TT-AKs"])
def test_bad_ranges_are_rejected(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_range(bad)


def test_card_removal() -> None:
    aces = parse_range("AA")
    left = remove_dead(aces, [card("Ah")])
    assert len(left) == 3 and all(card("Ah") not in c for c in left)
    assert len(remove_dead(parse_range("AKs"), H("AhKd"))) == 2


# ---- equity ----------------------------------------------------------------------------


def _oracle_equity(holes: list[list[int]], board: list[int]) -> list[F]:
    """Independent, slow equity: itertools boards and the 21-subset oracle."""
    used = set(board) | {c for h in holes for c in h}
    deck = [c for c in range(52) if c not in used]
    shares = [F(0)] * len(holes)
    total = 0
    for rest in itertools.combinations(deck, 5 - len(board)):
        values = [rank7_oracle([*h, *board, *rest]) for h in holes]
        best = max(values)
        winners = [i for i, v in enumerate(values) if v == best]
        for i in winners:
            shares[i] += F(1, len(winners))
        total += 1
    return [s / total for s in shares]


@pytest.mark.parametrize(
    ("hands", "board"),
    [
        (["AhKh", "QsQd"], "2c7d9h"),
        (["AhKh", "QsQd"], "2c7d9hKs"),
        (["AhKh", "QsQd", "7c7s"], "2c7d9hKs"),
        (["AsKd", "AcKh"], "2c7d9h"),  # mostly ties
        (["9h8h", "AsAd", "KcQc"], "ThJh2c"),
    ],
)
def test_exact_equity_matches_independent_oracle(hands: list[str], board: str) -> None:
    result = equity_exact([hand(h) for h in hands], H(board))
    assert [p.equity for p in result.players] == _oracle_equity([H(h) for h in hands], H(board))
    for p in result.players:
        assert type(p.equity) is F and 0 <= p.equity <= 1
        assert p.win + p.tie + p.loss == 1
    assert sum(p.equity for p in result.players) == 1


def test_river_equity_by_hand() -> None:
    # Board 2c 7d 9h Ks: AhKh has kings, QsQd has queens. One card to come (44 left):
    # the queens win only with one of the two remaining queens.
    result = equity_exact([hand("AhKh"), hand("QsQd")], H("2c7d9hKs"))
    assert result.scenarios == 44
    assert result.players[1].equity == F(2, 44)
    assert result.players[0].win == F(42, 44) and result.players[0].tie == 0


def test_preflop_enumerates_all_boards_and_equities_sum_to_one() -> None:
    result = equity_exact([hand("AhKh"), hand("QsQd")])
    assert result.scenarios == 1_712_304
    a, b = result.players
    assert a.equity + b.equity == 1  # complement, with ties split
    assert a.win + a.tie + b.win == 1 and a.tie == b.tie


def test_suit_symmetry_is_exact() -> None:
    result = equity_exact([hand("AsKs"), hand("AdKd")], H("2c"))
    a, b = result.players
    assert a.equity == b.equity == F(1, 2)
    assert a.win == b.win and a.tie == b.tie
    # relabelling suits consistently changes nothing
    one = equity_exact([hand("AhKh"), hand("QsQd")], H("2c7d9h"))
    two = equity_exact([hand("AdKd"), hand("QcQh")], H("2s7h9d"))
    assert [p.equity for p in one.players] == [p.equity for p in two.players]


def test_complement_when_players_swap() -> None:
    ab = equity_exact([hand("JhTh"), hand("AcAd")], H("9h8c2d"))
    ba = equity_exact([hand("AcAd"), hand("JhTh")], H("9h8c2d"))
    assert ab.players[0].equity == ba.players[1].equity
    assert ab.players[0].equity + ba.players[0].equity == 1


def test_exact_matches_monte_carlo() -> None:
    ranges = [hand("AhKh"), hand("QsQd"), hand("7c7s")]
    exact = equity_exact(ranges, H("2c"))
    mc = equity_mc(ranges, H("2c"), 150_000, np.random.default_rng(5))
    for e, m in zip(exact.players, mc.players, strict=True):
        assert_agrees(e.equity, m.equity, label="equity")
        assert abs(m.win - float(e.win)) < 0.01 and abs(m.tie - float(e.tie)) < 0.01
    assert sum(p.equity.estimate for p in mc.players) == pytest.approx(1.0)


def test_hand_versus_range_exact_and_monte_carlo() -> None:
    villain = parse_range("TT+,AQs+")
    board = H("2c7d9hKs")
    exact = equity_exact([hand("AhKh"), villain], board)
    # card removal: of the 38 combos, those using Ah, Kh or Ks cannot be dealt
    dealable = remove_dead(villain, [*H("AhKh"), *board])
    # removed: AA with Ah (3), KK with Kh or Ks (5), AhKh and AsKs (2), AhQh (1)
    assert len(dealable) == 38 - 3 - 5 - 2 - 1
    assert exact.scenarios == len(dealable) * 44
    # equal weight per dealable combo: the average of the per-combo equities
    per_combo = [equity_exact([hand("AhKh"), [c]], board).players[0].equity for c in dealable]
    assert exact.players[0].equity == sum(per_combo, F(0)) / len(dealable)
    mc = equity_mc([hand("AhKh"), villain], board, 100_000, np.random.default_rng(6))
    assert_agrees(exact.players[0].equity, mc.players[0].equity, label="vs range")
    assert mc.trials < 100_000  # trials with a blocked combo were rejected


def test_duplicate_cards_between_hands_or_board_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate card"):
        equity_exact([hand("AhKh"), hand("AhQd")])
    with pytest.raises(ValueError, match="duplicate card"):
        equity_exact([hand("AhKh"), hand("QsQd")], H("Ah7d9h"))
    with pytest.raises(ValueError, match="duplicate card"):
        equity_mc([hand("AhKh"), hand("AhQd")], [], 1000, np.random.default_rng(0))
    with pytest.raises(ValueError, match="duplicate card"):
        equity_exact([hand("AhKh"), hand("QsQd")], H("2c2c9h"))
    with pytest.raises(ValueError, match="two players"):
        equity_exact([hand("AhKh")])


def test_scenario_count_for_the_default_mode() -> None:
    assert exact_scenarios([hand("AhKh"), hand("QsQd")], []) == 1_712_304
    assert exact_scenarios([hand("AhKh"), hand("QsQd")], H("2c7d9h")) == 990


holes_and_board = st.lists(st.integers(0, 51), min_size=10, max_size=10, unique=True)


@settings(max_examples=25, deadline=None)
@given(holes_and_board, st.integers(2, 3), st.integers(3, 5))
def test_equities_are_probabilities_that_sum_to_one(
    cards: list[int], players: int, board_size: int
) -> None:
    ranges = [
        [(max(cards[2 * i : 2 * i + 2]), min(cards[2 * i : 2 * i + 2]))] for i in range(players)
    ]
    result = equity_exact(ranges, cards[6 : 6 + board_size])
    assert all(0 <= p.equity <= 1 for p in result.players)
    assert sum(p.equity for p in result.players) == 1


# ---- pot odds --------------------------------------------------------------------------


def test_pot_odds_by_hand() -> None:
    # Pot was 100, villain bets 50: 150 in the middle, 50 to call. Need 50 / 200 = 25%.
    assert breakeven_equity(150, 50) == F(1, 4)
    assert call_ev(F(1, 4), 150, 50) == 0
    # With 1/3 equity: win 150 a third of the time, lose 50 two thirds: 50 - 100/3 = 50/3
    assert call_ev(F(1, 3), 150, 50) == F(50, 3)
    # Flush draw on the turn: 9 outs of 46 unseen cards, pot-sized bet (pot 200, call 100)
    assert breakeven_equity(200, 100) == F(1, 3)
    assert call_ev(F(9, 46), 200, 100) == F(9, 46) * 200 - F(37, 46) * 100 < 0
    with pytest.raises(ValueError):
        call_ev(F(3, 2), 100, 50)
    with pytest.raises(TypeError):
        call_ev(0.25, 100, 50)  # type: ignore[arg-type]


# ---- CLI -------------------------------------------------------------------------------


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    raw = yaml.safe_load((REPO / "config.yaml").read_text())
    raw["cards"] = {"exact_limit": 100_000, "mc_trials": 20_000}
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(raw))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COLUMNS", "200")
    return tmp_path


def test_equity_command_exact_on_a_flop(workdir: Path) -> None:
    result = runner.invoke(app, ["equity", "AhKh", "QsQd", "--board", "2c7d9hKs"])
    assert result.exit_code == 0, result.output
    assert "Exact: 44 scenarios" in result.output and "= 1/22" in result.output


def test_equity_command_falls_back_to_monte_carlo_and_is_reproducible(workdir: Path) -> None:
    first = runner.invoke(app, ["equity", "AhKh", "TT+,AQs+"])
    second = runner.invoke(app, ["equity", "AhKh", "TT+,AQs+"])
    assert first.exit_code == 0, first.output
    assert "Monte Carlo" in first.output and "(SE)" in first.output and "38 combos" in first.output
    assert first.output == second.output  # same seed, same numbers
    forced = runner.invoke(app, ["equity", "AhKh", "QsQd", "--board", "2c7d9h", "--mc", "5000"])
    assert "Monte Carlo" in forced.output


def test_equity_command_errors(workdir: Path) -> None:
    dup = runner.invoke(app, ["equity", "AhKh", "AhQd"])
    assert dup.exit_code == 2 and "duplicate card" in dup.output
    assert runner.invoke(app, ["equity", "AhKh", "QsQd", "--exact", "--mc", "5000"]).exit_code == 2
    assert runner.invoke(app, ["equity", "AhKh", "ZZ"]).exit_code == 2


def test_pot_odds_command(workdir: Path) -> None:
    result = runner.invoke(app, ["pot-odds", "--pot", "150", "--call", "50", "--equity", "1/3"])
    assert result.exit_code == 0, result.output
    assert "1/4" in result.output and "+16.6667" in result.output and "call" in result.output


def test_cards_check_command_writes_a_passing_report(workdir: Path) -> None:
    result = runner.invoke(app, ["cards-check"])
    assert result.exit_code == 0, result.output
    report = (workdir / "reports" / "cards" / "cards_check.md").read_text()
    assert report.index("## Limitations") < report.index("## Result")
    assert "all checks pass" in report and "**NO**" not in report
    assert "1,302,540" in report and "Skipped in this run" in report


def test_cards_check_report_regression() -> None:
    """Fixed inputs must render exactly the stored file (one wrong count, one bad equity)."""
    seven = list(SEVEN_CARD_COUNTS)
    seven[1] += 1
    check = cards_check.CardsCheck(
        five_counts=FIVE_CARD_COUNTS,
        seven_counts=seven,
        oracle_hands=1000,
        oracle_mismatches=0,
        equities=[
            cards_check.EquityRow("A vs B", 44, F(21, 22), McResult(0.9541, 0.0011, 40_000)),
            cards_check.EquityRow("C vs D", 990, F(1, 2), McResult(0.52, 0.002, 40_000)),
        ],
        tol_se=4.0,
    )
    info = RunInfo(
        "20260101T000000Z-abcdef",
        "2026-01-01T00:00:00+00:00",
        "0123456789ab",
        False,
        "feedfacecafe",
        7,
    )
    text = cards_check.render(check, info)
    assert not check.ok() and text.count("**NO**") == 2
    assert text == (REPO / "tests" / "expected" / "cards_check.md").read_text()
