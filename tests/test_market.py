"""Market game: exact fair values, trader behaviour, expected P&L, a stored playthrough."""

from __future__ import annotations

import itertools
import json
from fractions import Fraction as F
from pathlib import Path

import numpy as np
import pytest

from ev_lab.practice_log import read_rows
from ev_lab.prob.montecarlo import FloatArray, assert_agrees, rng_for, run_mc
from ev_lab.trainer import market_game
from ev_lab.trainer.io import ScriptedIO
from ev_lab.trainer.market import QUANTITIES, MarketGame, Quantity, expected_pnl

REPO = Path(__file__).resolve().parents[1]
HALF = F(1, 2)
WIDTHS = [F(1, 5), F(3, 25), F(2, 25)]


def _game(quantity: str, seed: int, informed: F = HALF) -> MarketGame:
    return MarketGame(QUANTITIES[quantity], np.random.default_rng(seed), informed, WIDTHS, 1)


def _brute_force_value(q: Quantity, known: tuple[int, ...]) -> F:
    """E[X | known] by listing every completion with its probability."""
    total = F(0)
    rest = q.components[len(known) :]
    for combo in itertools.product(*[list(c.items()) for c in rest]):
        p = F(1)
        for _, pc in combo:
            p *= pc
        total += p * q.combine((*known, *[v for v, _ in combo]))
    return total


@pytest.mark.parametrize("quantity", sorted(QUANTITIES))
def test_fair_values_are_exact_at_every_stage(quantity: str) -> None:
    q = QUANTITIES[quantity]
    for revealed in range(len(q.components) + 1):
        for known in itertools.product(*[c.support for c in q.components[:revealed]]):
            value = q.fair_value(known)
            assert type(value) is F
            assert value == _brute_force_value(q, known)


def test_fair_values_by_hand() -> None:
    assert QUANTITIES["sum3"].fair_value(()) == F(21, 2)
    assert QUANTITIES["sum3"].fair_value((6,)) == 13
    assert QUANTITIES["sum3"].fair_value((6, 1)) == F(21, 2)
    assert QUANTITIES["product2"].fair_value(()) == F(49, 4)  # (7/2)^2, independence
    assert QUANTITIES["product2"].fair_value((2,)) == 7
    assert QUANTITIES["heads10"].fair_value(()) == 5
    assert QUANTITIES["heads10"].fair_value((4,)) == 7  # 4 seen + 3 expected of 6 left
    assert QUANTITIES["max2"].fair_value((6,)) == 6
    # max(4, d): 4, 4, 4, 4, 5, 6 -> 27/6
    assert QUANTITIES["max2"].fair_value((4,)) == F(27, 6)


def test_fair_value_is_a_martingale() -> None:
    """Averaging the next round's fair value over the next component gives today's."""
    for q in QUANTITIES.values():
        for known in itertools.product(*[c.support for c in q.components[:1]]):
            nxt = q.components[1].expect(lambda c, k=known, q=q: q.fair_value((*k, c)))
            assert nxt == q.fair_value(known)


def test_max_width_narrows_each_round() -> None:
    game = _game("sum3", 1)
    widths = []
    for _ in range(3):
        widths.append(game.max_width())
        mid = round(game.quantity.fair_value(game.known()))
        game.play_round(F(mid) - HALF, F(mid) + HALF)
    assert widths == [3, 2, 1]  # range 15 x (0.2, 0.12, 0.08), rounded, at least 1
    assert _game("product2", 1).max_width() == 7


def test_quote_validation() -> None:
    game = _game("sum3", 1)
    assert game.quote_error(F(10), F(10)) == "the bid must be below the ask"
    assert "too wide" in (game.quote_error(F(8), F(12)) or "")
    assert game.quote_error(F(9), F(12)) is None
    with pytest.raises(ValueError, match="too wide"):
        game.play_round(F(1), F(18))
    assert game.records == []


def test_informed_trader_trades_only_when_the_quote_is_wrong() -> None:
    for seed in range(200):
        game = _game("sum3", seed, informed=F(1))
        for _ in range(game.rounds):
            fair = game.quantity.fair_value(game.known())
            half = game.max_width() / 2
            r = game.play_round(fair - half, fair + half)
            assert r.trader == "informed" and r.trader_value is not None
            assert r.trader_value == game.quantity.fair_value(game.hidden[: len(r.known) + 1])
            expected = (
                "buy" if r.trader_value > r.ask else "sell" if r.trader_value < r.bid else "none"
            )
            assert r.side == expected
        # in the last round the informed trader knows X exactly: I never win that trade
        assert game.pnl(game.records[-1]) <= 0


def test_noise_trader_always_trades_and_is_fair_on_average() -> None:
    sides = []
    for seed in range(400):
        game = _game("max2", seed, informed=F(0))
        r = game.play_round(F(4), F(5))
        assert r.trader == "noise" and r.trader_value is None and r.side in ("buy", "sell")
        sides.append(r.side)
    assert 0.4 < sides.count("buy") / len(sides) < 0.6


def test_settlement() -> None:
    game = _game("max2", 3, informed=F(0))
    r = game.play_round(F(4), F(5))
    expected = F(5) - game.x if r.side == "buy" else game.x - F(4)
    assert game.pnl(r) == expected
    game.play_round(F(4), F(5))
    assert game.finished and game.total_pnl() == sum(game.pnl(x) for x in game.records)
    with pytest.raises(RuntimeError, match="over"):
        game.play_round(F(4), F(5))


def test_random_stream_does_not_depend_on_my_quotes() -> None:
    a, b = _game("sum3", 9), _game("sum3", 9)
    assert a.hidden == b.hidden
    for _ in range(3):
        ra, rb = a.play_round(F(10), F(11)), b.play_round(F(3), F(4))
        assert ra.trader == rb.trader


def test_expected_pnl_by_hand() -> None:
    # sum3, dice 3 and 4 public: X = 7 + d, fair 10.5. Quote 10 @ 11.
    # Informed sees d: buys at 11 when X is 12 or 13 (I lose 1, 2), sells at 10 when X is 8
    # or 9 (I lose 2, 1): expected -6/6 = -1. Noise: half the spread = +1/2.
    q = QUANTITIES["sum3"]
    assert expected_pnl(q, (3, 4), F(10), F(11), F(1)) == -1
    assert expected_pnl(q, (3, 4), F(10), F(11), F(0)) == HALF
    assert expected_pnl(q, (3, 4), F(10), F(11), HALF) == F(-1, 4)
    # a quote centred on fair value with the informed trader's whole range inside is safe
    assert expected_pnl(q, (3, 4), F(8), F(13), F(1)) == 0


def test_expected_pnl_matches_simulation_of_the_engine() -> None:
    q = QUANTITIES["product2"]
    bid, ask = F(9), F(16)

    def simulate(rng: np.random.Generator, n: int) -> FloatArray:
        out = np.zeros(n)
        for i in range(n):
            game = MarketGame(q, rng, HALF, WIDTHS, 1)
            first = game.play_round(bid, ask)
            # one round only, settled against the X that this game dealt
            out[i] = float(game.pnl(first))
        return out

    exact = expected_pnl(q, (), bid, ask, HALF)
    assert_agrees(exact, run_mc(simulate, 20_000, rng_for(4, "market-ev")), label="round-1 EV")


def test_scripted_playthrough_matches_stored_outcome(tmp_path: Path) -> None:
    """Fixed seed and fixed quotes must reproduce the stored game exactly."""
    game = _game("sum3", 20261109)
    io = ScriptedIO(["9", "12", "abc", "10", "13", "10", "12", "11", "12"])
    assert market_game.play(game, io)
    outcome = {
        "hidden": list(game.hidden),
        "x": game.x,
        "total_pnl": str(game.total_pnl()),
        "rounds": [
            {
                "known": list(r.known),
                "max_width": str(r.max_width),
                "quote": f"{r.bid} @ {r.ask}",
                "fair_value": str(r.fair_value),
                "expected_pnl": str(r.expected_pnl),
                "trader": r.trader,
                "side": r.side,
                "trader_value": None if r.trader_value is None else str(r.trader_value),
                "pnl": str(game.pnl(r)),
            }
            for r in game.records
        ],
    }
    stored = json.loads((REPO / "tests" / "expected" / "market_playthrough.json").read_text())
    assert outcome == stored
    text = "\n".join(io.transcript)
    assert "too wide" in text and "not a number" in text  # the two rejected inputs
    assert text.index("Round 3/3") < text.index("Total P&L")  # nothing revealed early
    assert "fair value" not in text[: text.index("Total P&L")].lower()

    market_game.log_game(tmp_path, "s1", game)
    rows = read_rows(tmp_path / market_game.FILE_NAME, market_game.HEADER)
    assert [r["round"] for r in rows] == ["1", "2", "3"]
    assert rows[0]["known"] == "" and rows[2]["known"].count(";") == 1
    assert {r["x"] for r in rows} == {str(game.x)}
    assert sum(F(r["pnl"]) for r in rows) == game.total_pnl()


def test_abandoned_game_returns_false() -> None:
    game = _game("sum3", 1)
    assert market_game.play(game, ScriptedIO(["9", "12"])) is False
    assert not game.finished
