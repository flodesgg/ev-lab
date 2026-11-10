"""Game theory: LP for matrix games, regret matching, Kuhn poker, CFR, indifference."""

from __future__ import annotations

from fractions import Fraction as F
from pathlib import Path

import numpy as np
import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st
from typer.testing import CliRunner

from ev_lab.cli import app
from ev_lab.games import cfr, kuhn
from ev_lab.games.catalog import (
    BIASED_RPS,
    DOMINATED_ROW,
    GAMES,
    HAND_2X2,
    MATCHING_PENNIES,
    ROCK_PAPER_SCISSORS,
)
from ev_lab.games.indifference import bluff_ev, bluff_share, caller_ev, calling_frequency
from ev_lab.games.matrix import (
    MatrixSolution,
    col_guarantee,
    exploitability,
    row_guarantee,
    solve_zero_sum,
)
from ev_lab.games.regret import regret_matching, strategy_from_regrets
from ev_lab.reports import games_report
from ev_lab.runinfo import RunInfo

REPO = Path(__file__).resolve().parents[1]
runner = CliRunner()
THIRD = F(1, 3)

# ---- matrix games ----------------------------------------------------------------------


def test_rock_paper_scissors() -> None:
    s = solve_zero_sum(ROCK_PAPER_SCISSORS)
    assert s == MatrixSolution(F(0), (THIRD,) * 3, (THIRD,) * 3, certified=True)


def test_matching_pennies() -> None:
    s = solve_zero_sum(MATCHING_PENNIES)
    assert s.certified and s.value == 0
    assert s.row == (F(1, 2), F(1, 2)) and s.col == (F(1, 2), F(1, 2))


def test_two_by_two_solved_by_hand() -> None:
    # Row mixes p on row 1 so that both columns pay the same:
    #   3p - 2(1-p) = -p + (1-p)  ->  p = 3/7, value = 3(3/7) - 2(4/7) = 1/7.
    # Column mixes q on column 1: 3q - (1-q) = -2q + (1-q)  ->  q = 2/7.
    s = solve_zero_sum(HAND_2X2)
    assert s.certified
    assert (s.value, s.row, s.col) == (F(1, 7), (F(3, 7), F(4, 7)), (F(2, 7), F(5, 7)))


def test_dominated_strategy_gets_zero_weight() -> None:
    s = solve_zero_sum(DOMINATED_ROW)
    assert s.certified and s.row[2] == 0
    assert (s.value, s.row[:2], s.col) == (F(1, 7), (F(3, 7), F(4, 7)), (F(2, 7), F(5, 7)))


def test_biased_rps_is_certified_and_indifferent() -> None:
    s = solve_zero_sum(BIASED_RPS)
    assert s.certified and s.value == 0  # the game is still symmetric: A = -A^T
    # every pure reply earns exactly the value against the opponent's mix (indifference)
    for i in range(3):
        assert sum(BIASED_RPS[i][j] * s.col[j] for j in range(3)) == s.value


def test_pure_saddle_point() -> None:
    s = solve_zero_sum(((4, 2, 5), (3, 1, 0)))  # row 1, column 2: value 2
    assert s.certified and s.value == 2
    assert s.row == (1, 0) and s.col == (0, 1, 0)


def test_guarantees_and_exploitability() -> None:
    uniform = (THIRD,) * 3
    always_rock = (F(1), F(0), F(0))
    assert row_guarantee(ROCK_PAPER_SCISSORS, always_rock) == -1  # paper beats it
    assert col_guarantee(ROCK_PAPER_SCISSORS, uniform) == 0
    assert exploitability(ROCK_PAPER_SCISSORS, always_rock, uniform) == 1
    assert exploitability(ROCK_PAPER_SCISSORS, uniform, uniform) == 0


def test_bad_matrices_are_rejected() -> None:
    with pytest.raises(ValueError, match="rectangular"):
        solve_zero_sum(((1, 2), (3,)))
    with pytest.raises(ValueError, match="rectangular"):
        solve_zero_sum(())
    with pytest.raises(TypeError):
        solve_zero_sum(((0.5, 1), (1, 0)))  # type: ignore[arg-type]


small_matrix = st.integers(2, 4).flatmap(
    lambda n: st.lists(st.lists(st.integers(-5, 5), min_size=n, max_size=n), min_size=2, max_size=4)
)


@settings(max_examples=60, deadline=None)
@given(small_matrix)
def test_random_games_are_certified_and_bounded_by_pure_strategies(a: list[list[int]]) -> None:
    s = solve_zero_sum(a)
    assert s.certified
    assert sum(s.row) == 1 and sum(s.col) == 1 and min(*s.row, *s.col) >= 0
    maximin = max(min(row) for row in a)  # best pure guarantee for the row player
    minimax = min(max(row[j] for row in a) for j in range(len(a[0])))
    assert maximin <= s.value <= minimax
    # swapping the players' roles negates the value
    negated_transpose = [[-a[i][j] for i in range(len(a))] for j in range(len(a[0]))]
    assert solve_zero_sum(negated_transpose).value == -s.value


# ---- regret matching -------------------------------------------------------------------


def test_strategy_from_regrets() -> None:
    assert strategy_from_regrets(np.array([2.0, -1.0, 6.0])).tolist() == [0.25, 0.0, 0.75]
    assert strategy_from_regrets(np.array([-1.0, -2.0])).tolist() == [0.5, 0.5]


@pytest.mark.parametrize("name", ["rock-paper-scissors", "biased rock-paper-scissors"])
def test_regret_matching_average_converges_to_the_lp_solution(name: str) -> None:
    lp = solve_zero_sum(GAMES[name])
    run = regret_matching(GAMES[name], 40_000, np.random.default_rng(3))
    assert run.row == pytest.approx([float(p) for p in lp.row], abs=0.03)
    assert run.col == pytest.approx([float(p) for p in lp.col], abs=0.03)
    assert run.row.sum() == pytest.approx(1.0)
    # and it is much closer than after a short run
    short = regret_matching(GAMES[name], 200, np.random.default_rng(3))
    target = np.array([float(p) for p in lp.row])
    assert np.abs(run.row - target).max() < np.abs(short.row - target).max()


def test_regret_matching_is_reproducible() -> None:
    a = regret_matching(BIASED_RPS, 2000, np.random.default_rng(8))
    b = regret_matching(BIASED_RPS, 2000, np.random.default_rng(8))
    assert a.row.tolist() == b.row.tolist() and a.col.tolist() == b.col.tolist()


# ---- Kuhn poker: the game --------------------------------------------------------------

J, Q, K = 0, 1, 2


def test_game_structure() -> None:
    assert len(kuhn.DEALS) == 6
    assert kuhn.INFOSETS[0] == ("J", "Jpb", "Q", "Qpb", "K", "Kpb")
    assert kuhn.INFOSETS[1] == ("Jp", "Jb", "Qp", "Qb", "Kp", "Kb")
    assert [kuhn.player_to_act(h) for h in ("", "p", "b", "pb")] == [0, 1, 1, 0]
    assert kuhn.infoset((K, J), "pb") == "Kpb" and kuhn.infoset((K, J), "p") == "Jp"


@pytest.mark.parametrize(
    ("deal", "history", "expected"),
    [
        ((K, Q), "pp", 1),
        ((J, Q), "pp", -1),
        ((J, K), "bp", 1),  # a bluff that works
        ((K, Q), "bb", 2),
        ((J, Q), "bb", -2),
        ((K, J), "pbp", -1),  # folding the best hand still loses the ante
        ((Q, J), "pbb", 2),
        ((Q, K), "pbb", -2),
    ],
)
def test_payoffs(deal: tuple[int, int], history: str, expected: int) -> None:
    assert kuhn.payoff(deal, history) == expected


def test_payoff_rejects_unfinished_histories() -> None:
    with pytest.raises(ValueError):
        kuhn.payoff((K, Q), "pb")


def _constant(p: F) -> dict[str, F]:
    return {name: p for side in kuhn.INFOSETS for name in side}


def test_values_of_simple_strategies_by_hand() -> None:
    # nobody ever bets: always a showdown for 1, and the deal is symmetric
    assert kuhn.expected_value(_constant(F(0))) == 0
    # everybody always bets and calls: always a showdown for 2, still symmetric
    assert kuhn.expected_value(_constant(F(1))) == 0
    # player 1 always bets, player 2 always folds: player 1 wins the ante every time
    s = _constant(F(0)) | {"J": F(1), "Q": F(1), "K": F(1)}
    assert kuhn.expected_value(s) == 1


def test_best_response_by_hand() -> None:
    # Against a player 2 who never bets and never calls, player 1 bets everything: +1.
    assert kuhn.best_response_value(0, _constant(F(0))) == 1
    # Against a player 1 who never bets and never calls, player 2 bets every time
    # after the check and wins the ante: +1 for player 2.
    assert kuhn.best_response_value(1, _constant(F(0))) == 1
    assert kuhn.exploitability(_constant(F(0))) == 1


def test_best_response_is_at_least_any_other_strategy() -> None:
    rng = np.random.default_rng(0)
    for _ in range(20):
        base = {n: F(int(rng.integers(0, 11)), 10) for side in kuhn.INFOSETS for n in side}
        other = {n: F(int(rng.integers(0, 11)), 10) for side in kuhn.INFOSETS for n in side}
        mixed0 = base | {n: other[n] for n in kuhn.INFOSETS[0]}
        mixed1 = base | {n: other[n] for n in kuhn.INFOSETS[1]}
        assert kuhn.best_response_value(0, base) >= kuhn.expected_value(mixed0)
        assert kuhn.best_response_value(1, base) >= -kuhn.expected_value(mixed1)
        assert kuhn.exploitability(base) >= 0


# ---- Kuhn poker: the equilibrium family, exactly ---------------------------------------


@pytest.mark.parametrize("alpha", [F(k, 24) for k in range(9)])
def test_equilibrium_family_has_value_minus_one_eighteenth_and_zero_exploitability(
    alpha: F,
) -> None:
    s = kuhn.equilibrium(alpha)
    assert kuhn.expected_value(s) == F(-1, 18) == kuhn.GAME_VALUE
    assert kuhn.best_response_value(0, s) == F(-1, 18)
    assert kuhn.best_response_value(1, s) == F(1, 18)
    assert kuhn.exploitability(s) == 0


def test_leaving_the_family_is_exploitable() -> None:
    with pytest.raises(ValueError):
        kuhn.equilibrium(F(1, 2))
    base = kuhn.equilibrium(F(1, 6))
    for name, value in [("J", F(2, 3)), ("Qb", F(1)), ("Jp", F(0)), ("K", F(0)), ("Qpb", F(0))]:
        assert kuhn.exploitability(base | {name: value}) > 0, name
    # never bluffing with the jack as player 2 lets player 1 fold queens to every bet
    no_bluff = base | {"Jp": F(0)}
    assert kuhn.best_response_value(0, no_bluff) > F(-1, 18)


def test_family_distance() -> None:
    alpha, gap = kuhn.family_distance(kuhn.equilibrium(F(1, 4)))
    assert alpha == 0.25 and gap < 1e-12
    alpha, gap = kuhn.family_distance(kuhn.equilibrium(F(1, 4)) | {"Qb": F(1)})
    assert gap == pytest.approx(2 / 3)


# ---- CFR -------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def cfr_run() -> tuple[cfr.KuhnCFR, list[cfr.Checkpoint]]:
    return cfr.run(6000)


def test_cfr_value_converges_to_minus_one_eighteenth(
    cfr_run: tuple[cfr.KuhnCFR, list[cfr.Checkpoint]],
) -> None:
    _, checkpoints = cfr_run
    assert checkpoints[-1].iteration == 6000
    assert checkpoints[-1].value == pytest.approx(-1 / 18, abs=0.002)


def test_cfr_exploitability_falls_toward_zero(
    cfr_run: tuple[cfr.KuhnCFR, list[cfr.Checkpoint]],
) -> None:
    _, checkpoints = cfr_run
    exploit = [c.exploitability for c in checkpoints]
    assert all(e >= 0 for e in exploit)
    assert exploit[-1] < 0.006 and exploit[-1] < exploit[0] / 50
    # roughly a 1/sqrt(T) decline: 100 times more iterations, well over 5 times lower
    at = {c.iteration: c.exploitability for c in checkpoints}
    assert at[10] / at[1000] > 5


def test_cfr_strategy_lies_in_the_equilibrium_family(
    cfr_run: tuple[cfr.KuhnCFR, list[cfr.Checkpoint]],
) -> None:
    solver, _ = cfr_run
    strategy = solver.average_strategy()
    alpha, gap = kuhn.family_distance(strategy)
    assert 0 <= alpha <= 1 / 3 and gap < 0.03
    assert strategy["K"] == pytest.approx(3 * alpha, abs=0.03)
    assert strategy["Qpb"] == pytest.approx(alpha + 1 / 3, abs=0.03)
    assert strategy["Jp"] == pytest.approx(1 / 3, abs=0.03)
    assert strategy["Qb"] == pytest.approx(1 / 3, abs=0.03)
    for never in ("Q", "Jpb", "Qp", "Jb"):
        assert strategy[never] < 0.01
    for always in ("Kpb", "Kp", "Kb"):
        assert strategy[always] > 0.99


def test_cfr_is_deterministic_and_checkpoints_do_not_change_the_result() -> None:
    a, _ = cfr.run(300)
    b = cfr.KuhnCFR()
    b.iterate(300)
    assert a.average_strategy() == b.average_strategy()


def test_checkpoint_schedule() -> None:
    schedule = cfr.checkpoint_schedule(1000)
    assert schedule[0] == 1 and schedule[-1] == 1000
    assert schedule == sorted(set(schedule)) and {10, 100} <= set(schedule)
    assert cfr.checkpoint_schedule(1) == [1]


# ---- indifference ----------------------------------------------------------------------


def test_indifference_by_hand() -> None:
    # pot-sized bet: a third of the range may be bluffs, and the caller defends half
    assert bluff_share(100, 100) == THIRD
    assert calling_frequency(100, 100) == F(1, 2)
    # half-pot bet: 1/4 bluffs, call 2/3
    assert bluff_share(100, 50) == F(1, 4)
    assert calling_frequency(100, 50) == F(2, 3)
    with pytest.raises(ValueError):
        bluff_share(0, 10)


@given(
    st.fractions(min_value=F(1, 10), max_value=100), st.fractions(min_value=F(1, 10), max_value=100)
)
def test_indifference_formulas_make_the_direct_ev_zero(pot: F, bet: F) -> None:
    f, c = bluff_share(pot, bet), calling_frequency(pot, bet)
    assert caller_ev(pot, bet, f) == 0
    assert bluff_ev(pot, bet, c) == 0
    # more bluffs than that: calling profits; fewer: calling loses
    assert caller_ev(pot, bet, (f + 1) / 2) > 0 > caller_ev(pot, bet, f / 2)
    assert bluff_ev(pot, bet, c / 2) > 0 > bluff_ev(pot, bet, (c + 1) / 2)


@pytest.mark.parametrize("alpha", [F(1, 12), F(1, 5), THIRD])
def test_kuhn_equilibrium_uses_exactly_the_indifference_frequencies(alpha: F) -> None:
    """In Kuhn poker the pot is 2 (two antes) and the bet is 1."""
    s = kuhn.equilibrium(alpha)
    # player 1's betting range: kings (3 alpha) for value, jacks (alpha) as bluffs
    assert s["J"] / (s["J"] + s["K"]) == bluff_share(2, 1) == F(1, 4)
    # player 2's betting range after a check: king always, jack 1/3
    assert s["Jp"] / (s["Jp"] + s["Kp"]) == bluff_share(2, 1)
    # player 2 facing player 1's jack bluff holds Q or K equally often
    assert (s["Qb"] + s["Kb"]) / 2 == calling_frequency(2, 1) == F(2, 3)
    # player 1 facing player 2's jack bluff: checked queens (always) and kings (1 - 3 alpha)
    checked_q, checked_k = 1 - s["Q"], 1 - s["K"]
    call = (checked_q * s["Qpb"] + checked_k * s["Kpb"]) / (checked_q + checked_k)
    assert call == calling_frequency(2, 1)


# ---- report and CLI --------------------------------------------------------------------


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    raw = yaml.safe_load((REPO / "config.yaml").read_text())
    raw["games"] |= {"regret_iterations": 3000, "cfr_iterations": 500}
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(raw))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COLUMNS", "200")
    return tmp_path


def test_games_command_writes_report_and_figure(workdir: Path) -> None:
    result = runner.invoke(app, ["games"])
    assert result.exit_code == 0, result.output
    assert "All exact checks pass" in result.output
    report = (workdir / "reports" / "games" / "games.md").read_text()
    assert report.index("## Limitations") < report.index("## Result")
    assert "| 1/3 | -1/18 | 0 |" in report and "| hand-solved 2x2 | 1/7 |" in report
    png = (workdir / "reports" / "games" / "kuhn_exploitability.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 5000


def test_indifference_command(workdir: Path) -> None:
    result = runner.invoke(app, ["indifference", "--pot", "2", "--bet", "1"])
    assert result.exit_code == 0, result.output
    assert "1/4" in result.output and "2/3" in result.output
    assert runner.invoke(app, ["indifference", "--pot", "0", "--bet", "1"]).exit_code == 2


def test_games_report_regression() -> None:
    """Fixed inputs must render exactly the stored file."""
    family = [F(0), THIRD]
    strategy = {k: float(v) for k, v in kuhn.equilibrium(F(1, 4)).items()} | {"Qb": 0.35}
    report = games_report.GamesReport(
        matrix=[("hand-solved 2x2", solve_zero_sum(HAND_2X2))],
        regret=[games_report.RegretRow("rps", 1000, [0.3, 0.3, 0.4], [0.33, 0.33, 0.34], 0.0667)],
        checkpoints=[cfr.Checkpoint(1, 0.333333, -0.02), cfr.Checkpoint(100, 0.02, -0.054)],
        strategy=strategy,
        family_alphas=family,
        family_values=[kuhn.expected_value(kuhn.equilibrium(a)) for a in family],
        family_exploitabilities=[kuhn.exploitability(kuhn.equilibrium(a)) for a in family],
    )
    info = RunInfo(
        "20260101T000000Z-abcdef",
        "2026-01-01T00:00:00+00:00",
        "0123456789ab",
        False,
        "feedfacecafe",
        7,
    )
    assert report.ok()
    assert (
        games_report.render(report, info) == (REPO / "tests" / "expected" / "games.md").read_text()
    )
