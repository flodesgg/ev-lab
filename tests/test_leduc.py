"""Leduc hold'em: rules by hand, the slow evaluator, the fast solver, CFR+ convergence."""

from __future__ import annotations

from fractions import Fraction as F
from pathlib import Path

import numpy as np
import pytest
import yaml
from typer.testing import CliRunner

from ev_lab.cli import app
from ev_lab.games import leduc, leduc_cfr
from ev_lab.games.cfr import checkpoint_schedule
from ev_lab.games.cli import build_leduc_report
from ev_lab.reports import leduc_report
from ev_lab.runinfo import RunInfo

REPO = Path(__file__).resolve().parents[1]
runner = CliRunner()
J, Q, K = 0, 1, 2

# ---- rules -----------------------------------------------------------------------------


def test_betting_sequences_of_one_round() -> None:
    seqs = leduc.round_sequences()
    assert len(seqs) == 15 == len(set(seqs))
    ended = sorted(s for s in seqs if leduc.round_over(s))
    assert ended == sorted(["cc", "rc", "rf", "crc", "crf", "rrc", "rrf", "crrc", "crrf"])
    assert leduc.legal_actions("") == "cr" == leduc.legal_actions("c")
    assert leduc.legal_actions("r") == "fcr" == leduc.legal_actions("cr")
    assert leduc.legal_actions("rr") == "fc" == leduc.legal_actions("crr")  # two-bet cap
    assert leduc.legal_actions("rc") == ""
    assert [leduc.player_to_act(s) for s in ("", "c", "cr", "rr")] == [0, 1, 0, 0]


@pytest.mark.parametrize(
    ("seq", "bet", "expected"),
    [
        ("cc", 2, (0, 0)),
        ("rc", 2, (2, 2)),
        ("rf", 2, (2, 0)),
        ("crc", 2, (2, 2)),
        ("rrc", 2, (4, 4)),  # bet 2, raise to 4, call
        ("rrf", 2, (2, 4)),
        ("crrc", 4, (8, 8)),
        ("crrf", 4, (8, 4)),
    ],
)
def test_chips_committed_in_a_round(seq: str, bet: int, expected: tuple[int, int]) -> None:
    assert leduc.commitments(seq, bet) == expected


@pytest.mark.parametrize(
    ("r0", "r1", "public", "seq1", "seq2", "expected"),
    [
        (K, Q, None, "rf", None, 1),  # player 2 folds to the first bet: player 1 wins the ante
        (J, K, None, "crf", None, -1),  # player 1 checks and folds: loses the ante
        (J, K, None, "rrf", None, -3),  # player 1 bets 2, folds to the raise: ante + 2
        (K, Q, J, "cc", "cc", 1),  # no bets: higher card wins the ante
        (Q, K, J, "cc", "cc", -1),
        (J, K, J, "rc", "cc", 3),  # the jack pairs the board and beats the king
        (K, K, J, "rc", "rc", 0),  # same rank: split
        (Q, J, J, "rrc", "crrc", -13),  # 1 + 4 + 8 lost to a pair of jacks
        (K, Q, J, "rc", "rf", 3),  # player 2 folds in round 2: loses ante + round-1 call
        (K, Q, J, "cc", "crf", -1),  # player 1 checks and folds to a bet: only the ante
        (K, Q, J, "cc", "crrf", 5),  # check, bet 4, raise to 8, player 2 folds: ante + 4
    ],
)
def test_payoffs_by_hand(
    r0: int, r1: int, public: int | None, seq1: str, seq2: str | None, expected: int
) -> None:
    assert leduc.payoff(r0, r1, public, seq1, seq2) == expected


def test_information_sets() -> None:
    keys = leduc.all_infosets()
    assert len(keys) == len(set(keys)) == 288  # 3 ranks x 6 + 3 x 5 x 3 x 6
    assert leduc.card_level_infoset_count() == 936  # the count in the checked source
    assert leduc.infoset_key(K, "cr") == "K:cr"
    assert leduc.infoset_key(K, "rc", J, "c") == "K:rc/J:c"
    assert leduc.strength(J, J) > leduc.strength(K, J) > leduc.strength(Q, J)


# ---- slow evaluator --------------------------------------------------------------------


def _always(prefer: str) -> dict[str, dict[str, F]]:
    """Every information set plays the first legal action found in `prefer`."""
    out = {}
    for key in leduc.all_infosets():
        actions = leduc.legal_actions(key.rsplit(":", 1)[1])
        pick = next(a for a in prefer if a in actions)
        out[key] = {a: F(int(a == pick)) for a in actions}
    return out


def test_expected_values_of_simple_strategies_by_hand() -> None:
    # nobody ever bets: a showdown for the antes; the deal is symmetric
    assert leduc.expected_value(_always("cf")) == 0
    # everybody always raises and calls: still symmetric
    assert leduc.expected_value(_always("rc")) == 0
    # player 1 always bets, player 2 always folds: player 1 collects the ante every hand
    one_sided = _always("rc") | {
        k: v for k, v in _always("fc").items() if k.split(":")[1] in ("r", "c", "crr")
    }
    assert leduc.expected_value(one_sided) == 1
    value = leduc.expected_value(leduc.uniform_strategy())
    assert isinstance(value, F)  # exact when the strategy is exact


def test_chance_weights_match_card_counting() -> None:
    m1, w = leduc_cfr.chance_weights()
    assert m1.sum() == pytest.approx(1.0) and w.sum() == pytest.approx(1.0)
    # by hand: both jacks dealt, 2 of 30 ordered deals; then the public card cannot be a jack
    assert m1[J, J] == pytest.approx(2 / 30) and w[J, J, J] == 0
    # J and Q dealt (4 of 30), public K: 2 of the 4 remaining cards
    assert w[K, J, Q] == pytest.approx(4 / 30 * 2 / 4)
    assert w[J, J, Q] == pytest.approx(4 / 30 * 1 / 4)
    assert w.sum(axis=0) == pytest.approx(m1)  # summing out the public card


# ---- fast evaluator against the slow one -----------------------------------------------


def test_fast_and_slow_evaluators_agree_on_random_strategies() -> None:
    rng = np.random.default_rng(0)
    for _ in range(5):
        solver = leduc_cfr.LeducSolver()
        for node in solver.nodes:  # arbitrary positive weights -> an arbitrary strategy
            node.strategy_sum = rng.random(node.strategy_sum.shape) + 0.01
        slow = leduc.expected_value(solver.strategy_table())
        assert solver.value() == pytest.approx(float(slow), abs=1e-12)
    fresh = leduc_cfr.LeducSolver()
    assert fresh.value() == pytest.approx(
        float(leduc.expected_value(leduc.uniform_strategy())), abs=1e-12
    )


def test_tree_shape() -> None:
    solver = leduc_cfr.LeducSolver()
    assert len(solver.nodes) == 6 + 5 * 3 * 6  # public decision nodes
    assert len(solver.strategy_table()) == 288
    for node in solver.nodes:
        assert node.current_strategy().sum(axis=1) == pytest.approx(np.ones(3))


# ---- CFR+ ------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def report() -> leduc_report.LeducReport:
    return build_leduc_report(400)


def test_cross_checks_pass(report: leduc_report.LeducReport) -> None:
    assert report.ok()
    assert report.uniform_value_exact == leduc.expected_value(leduc.uniform_strategy())
    # each best-response policy, run through the slow evaluator, earns what was claimed
    for claimed, achieved in zip(report.br_claimed, report.br_achieved, strict=True):
        assert claimed == pytest.approx(achieved, abs=1e-10)


def test_best_response_bounds_the_value(report: leduc_report.LeducReport) -> None:
    # player 1 can do at least as well as the average strategy; so can player 2 (sign flipped)
    assert report.br_claimed[0] >= report.value_fast - 1e-12
    assert report.br_claimed[1] >= -report.value_fast - 1e-12
    assert all(c.exploitability >= 0 for c in (*report.plus, *report.vanilla))


def test_cfr_plus_converges_and_beats_vanilla(report: leduc_report.LeducReport) -> None:
    plus, vanilla = report.plus, report.vanilla
    assert plus[-1].iteration == vanilla[-1].iteration == 400
    assert plus[-1].exploitability < 0.003
    assert plus[-1].exploitability < plus[0].exploitability / 500
    assert vanilla[-1].exploitability > 5 * plus[-1].exploitability
    # the value has settled: the last two checkpoints agree closely, and the first player loses
    assert plus[-1].value == pytest.approx(plus[-2].value, abs=0.002)
    assert -0.1 < plus[-1].value < -0.07


def test_solver_is_deterministic() -> None:
    a, _ = leduc_cfr.run(30, True, checkpoint_schedule(30))
    b = leduc_cfr.LeducSolver()
    b.iterate(30)
    assert a.strategy_table() == b.strategy_table()


def test_regrets_stay_non_negative_only_with_plus() -> None:
    plus, vanilla = leduc_cfr.LeducSolver(plus=True), leduc_cfr.LeducSolver(plus=False)
    plus.iterate(20)
    vanilla.iterate(20)
    assert all((node.regret >= 0).all() for node in plus.nodes)
    assert any((node.regret < 0).any() for node in vanilla.nodes)


# ---- report and CLI --------------------------------------------------------------------


def test_leduc_report_regression() -> None:
    """Fixed inputs must render exactly the stored file."""
    cp = leduc_cfr.Checkpoint
    fixed = leduc_report.LeducReport(
        infosets=288,
        card_level_infosets=936,
        public_nodes=96,
        uniform_value_exact=F(-5, 64),
        uniform_value_fast=-0.078125,
        plus=[cp(1, 2.4, -0.08), cp(100, 0.01, -0.085)],
        vanilla=[cp(1, 2.4, -0.08), cp(100, 0.1, -0.09)],
        value_fast=-0.085,
        value_slow=-0.085,
        br_achieved=(-0.08, 0.1),
        br_claimed=(-0.08, 0.1),
    )
    info = RunInfo(
        "20260101T000000Z-abcdef",
        "2026-01-01T00:00:00+00:00",
        "0123456789ab",
        False,
        "feedfacecafe",
        7,
    )
    text = leduc_report.render(fixed, info)
    assert fixed.ok() and text.index("## Limitations") < text.index("## Result")
    assert text == (REPO / "tests" / "expected" / "leduc.md").read_text()
    broken = leduc_report.LeducReport(**{**fixed.__dict__, "value_slow": -0.08})
    assert not broken.ok()


def test_leduc_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw = yaml.safe_load((REPO / "config.yaml").read_text())
    raw["games"]["leduc_iterations"] = 60
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(raw))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COLUMNS", "200")
    result = runner.invoke(app, ["leduc"])
    assert result.exit_code == 0, result.output
    assert "Cross-checks agree" in result.output
    report_text = (tmp_path / "reports" / "games" / "leduc.md").read_text()
    assert "-5/64" in report_text and "936" in report_text
    png = (tmp_path / "reports" / "games" / "leduc_exploitability.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 5000
