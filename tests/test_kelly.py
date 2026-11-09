"""Kelly: exact formulas, simulation against theory, estimated edge, report."""

from __future__ import annotations

import math
from fractions import Fraction as F
from pathlib import Path

import numpy as np
import pytest
import yaml
from hypothesis import given
from hypothesis import strategies as st
from typer.testing import CliRunner

from ev_lab.cli import app
from ev_lab.kelly.core import (
    expected_wealth_factor,
    growth_rate,
    hit_probability_approx,
    kelly_bet,
    kelly_fraction,
)
from ev_lab.kelly.simulate import FractionResult, evaluate_fraction, simulate, win_counts
from ev_lab.kelly.uncertainty import (
    UncertaintyRow,
    estimated_fraction,
    expected_growth,
    uncertainty_table,
)
from ev_lab.prob.montecarlo import McResult
from ev_lab.reports import kelly_report
from ev_lab.runinfo import RunInfo

REPO = Path(__file__).resolve().parents[1]
runner = CliRunner()
P, ODDS, KELLY = 0.55, 1.0, 0.1
MULTIPLES = [0.25, 0.5, 1.0, 1.5, 2.0]

# ---- exact formulas --------------------------------------------------------------------


def test_kelly_fraction_by_hand() -> None:
    assert kelly_fraction(F(55, 100), 1) == F(1, 10)  # even money: 2p - 1
    assert kelly_fraction(F(1, 2), 2) == F(1, 4)  # 0.5 - 0.5/2
    assert kelly_fraction(F(1, 4), 5) == F(1, 10)  # long shot: 0.25 - 0.75/5
    assert isinstance(kelly_fraction(F(55, 100), 1), F)
    with pytest.raises(TypeError):
        kelly_fraction(0.55, 1)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        kelly_fraction(F(3, 2), 1)


def test_zero_edge_means_zero_bet() -> None:
    assert kelly_fraction(F(1, 2), 1) == 0  # fair coin at even money
    assert kelly_fraction(F(1, 3), 2) == 0  # fair at 2-to-1
    assert kelly_fraction(F(1, 11), 10) == 0
    assert kelly_fraction(F(2, 5), 1) == F(-1, 5)  # negative edge: the formula goes negative
    assert kelly_bet(F(2, 5), 1) == 0  # and the bet is nothing


def test_growth_at_zero_and_at_one() -> None:
    assert growth_rate(0.0, P, ODDS) == 0.0
    assert growth_rate(1.0, P, ODDS) == -math.inf
    with pytest.raises(ValueError):
        growth_rate(1.5, P, ODDS)


@pytest.mark.parametrize(
    ("p", "odds"),
    [(F(55, 100), F(1)), (F(3, 5), F(1)), (F(2, 5), F(2)), (F(1, 4), F(5)), (F(9, 10), F(1, 2))],
)
def test_kelly_fraction_is_the_argmax_of_growth_on_a_fine_grid(p: F, odds: F) -> None:
    grid = np.arange(0.0, 0.9995, 0.0005)
    growth = [growth_rate(float(f), float(p), float(odds)) for f in grid]
    best = float(grid[int(np.argmax(growth))])
    assert best == pytest.approx(float(kelly_fraction(p, odds)), abs=0.00051)
    assert max(growth) > 0


@given(
    st.fractions(min_value=F(1, 100), max_value=F(99, 100)),
    st.fractions(min_value=F(1, 10), max_value=10),
)
def test_growth_is_lower_on_both_sides_of_kelly(p: F, odds: F) -> None:
    f = float(kelly_bet(p, odds))
    if not 0.01 < f < 0.98:
        return
    here = growth_rate(f, float(p), float(odds))
    assert here >= growth_rate(f - 0.01, float(p), float(odds))
    assert here >= growth_rate(f + 0.01, float(p), float(odds))


def test_twice_kelly_has_about_zero_growth() -> None:
    # exact for the continuous approximation, slightly negative for a discrete bet
    g1, g2 = growth_rate(KELLY, P, ODDS), growth_rate(2 * KELLY, P, ODDS)
    assert g2 < 0 and abs(g2) < 0.05 * g1


def test_half_kelly_keeps_three_quarters_of_the_growth() -> None:
    # continuous approximation: g(c f*) / g(f*) = 2c - c^2 = 0.75 at c = 1/2
    ratio = growth_rate(KELLY / 2, P, ODDS) / growth_rate(KELLY, P, ODDS)
    assert ratio == pytest.approx(0.75, abs=0.01)


def test_expected_wealth_grows_with_the_stake_even_when_typical_wealth_shrinks() -> None:
    assert expected_wealth_factor(0.2, P, ODDS) == pytest.approx(1.02)
    assert expected_wealth_factor(0.2, P, ODDS) > expected_wealth_factor(0.1, P, ODDS) > 1
    assert growth_rate(0.2, P, ODDS) < 0


def test_hit_probability_approximation() -> None:
    assert hit_probability_approx(0.5, 1.0) == pytest.approx(0.5)
    assert hit_probability_approx(0.5, 0.5) == pytest.approx(0.125)
    assert hit_probability_approx(0.1, 1.0) == pytest.approx(0.1)
    assert hit_probability_approx(0.5, 2.0) == 1.0 == hit_probability_approx(0.5, 3.0)
    with pytest.raises(ValueError):
        hit_probability_approx(1.5, 1.0)


# ---- simulation ------------------------------------------------------------------------


@pytest.fixture(scope="module")
def results() -> list[FractionResult]:
    return simulate(P, ODDS, KELLY, MULTIPLES, 500, 4000, 0.1, 0.5, np.random.default_rng(11))


def test_simulated_log_growth_matches_the_exact_rate(results: list[FractionResult]) -> None:
    for r in results:
        assert r.growth_exact == pytest.approx(growth_rate(r.fraction, P, ODDS))
        assert abs(r.growth_sim.estimate - r.growth_exact) < 4 * r.growth_sim.se, r.multiple
        assert r.growth_sim.n == 4000


def test_same_seed_same_paths_and_common_random_numbers() -> None:
    a = win_counts(P, 50, 20, np.random.default_rng(3))
    b = win_counts(P, 50, 20, np.random.default_rng(3))
    c = win_counts(P, 50, 20, np.random.default_rng(4))
    assert (a == b).all() and not (a == c).all()
    assert a.shape == (20, 51) and (a[:, 0] == 0).all()
    steps = np.diff(a, axis=1)
    assert set(np.unique(steps)) <= {0, 1}
    one = simulate(P, ODDS, KELLY, MULTIPLES, 50, 200, 0.1, 0.5, np.random.default_rng(3))
    two = simulate(P, ODDS, KELLY, MULTIPLES, 50, 200, 0.1, 0.5, np.random.default_rng(3))
    assert one == two


def test_path_metrics_by_hand() -> None:
    # win, loss, loss, win at f = 1/2, even money: wealth 1.5, 0.75, 0.375, 0.5625
    counts = np.array([[0, 1, 1, 1, 2], [0, 1, 1, 1, 2]], dtype=np.int32)
    r = evaluate_fraction(counts, 0.5, 5.0, P, ODDS, ruin_level=0.1, drawdown_level=0.5)
    assert r.median_wealth == pytest.approx(0.5625) == pytest.approx(r.mean_wealth)
    assert r.max_drawdown_quantiles == pytest.approx((0.75, 0.75, 0.75))  # 1.5 -> 0.375
    assert r.p_hit_drawdown_level.estimate == 1.0  # 0.375 <= 0.5
    assert r.p_below_ruin_level.estimate == 0.0
    assert r.growth_sim.estimate == pytest.approx(math.log(0.5625) / 4)


def test_risk_rises_with_bet_size(results: list[FractionResult]) -> None:
    hits = [r.p_hit_drawdown_level.estimate for r in results]
    medians = [r.max_drawdown_quantiles[0] for r in results]
    assert hits == sorted(hits) and medians == sorted(medians)
    assert all(0 <= q <= 1 for r in results for q in r.max_drawdown_quantiles)
    # typical wealth is highest at full Kelly; at twice Kelly it goes nowhere
    typical = {r.multiple: r.median_wealth for r in results}
    assert typical[1.0] == max(typical.values()) and typical[2.0] < typical[0.25]


def test_continuous_approximation_is_close_for_small_bets_and_too_high_for_large(
    results: list[FractionResult],
) -> None:
    by = {r.multiple: r for r in results}
    for multiple, tolerance in ((0.25, 0.01), (0.5, 0.03)):
        approx = hit_probability_approx(0.5, multiple)
        assert abs(by[multiple].p_hit_drawdown_level.estimate - approx) < tolerance
    # finite horizon: at twice Kelly not every path has halved yet, the approximation says 1
    assert by[2.0].p_hit_drawdown_level.estimate < 1.0


def test_sample_mean_wealth_matches_the_exact_mean_for_a_small_stake(
    results: list[FractionResult],
) -> None:
    quarter = results[0]
    exact = expected_wealth_factor(quarter.fraction, P, ODDS) ** 500
    assert quarter.mean_wealth == pytest.approx(exact, rel=0.05)


# ---- estimated edge --------------------------------------------------------------------


def test_estimated_fraction_is_clipped_and_capped() -> None:
    assert estimated_fraction(5, 10, 1.0, 0.9) == 0.0  # p_hat = 0.5: no edge
    assert estimated_fraction(3, 10, 1.0, 0.9) == 0.0  # negative edge: no bet
    assert estimated_fraction(6, 10, 1.0, 0.9) == pytest.approx(0.2)
    assert estimated_fraction(10, 10, 1.0, 0.9) == 0.9  # all wins: capped, not "bet it all"


def test_expected_growth_by_hand_for_two_past_bets() -> None:
    # n = 2: p_hat is 0, 1/2 or 1. Only two wins (probability p^2) lead to a bet, of the cap.
    cap = 0.9
    expected = P**2 * growth_rate(cap, P, ODDS)
    assert expected_growth(2, P, ODDS, 1.0, cap) == pytest.approx(expected)
    assert expected_growth(2, P, ODDS, 0.5, cap) == pytest.approx(
        P**2 * growth_rate(cap / 2, P, ODDS)
    )


def test_expected_growth_matches_sampling_the_estimate() -> None:
    n, cap = 50, 0.9
    rng = np.random.default_rng(21)
    wins = rng.binomial(n, P, size=200_000)
    growth = np.array(
        [growth_rate(estimated_fraction(k, n, ODDS, cap), P, ODDS) for k in range(n + 1)]
    )
    sample = growth[wins]
    se = sample.std(ddof=1) / math.sqrt(len(sample))
    assert abs(sample.mean() - expected_growth(n, P, ODDS, 1.0, cap)) < 4 * se


def test_uncertainty_table_shape() -> None:
    rows = uncertainty_table([10, 100, 5000], P, ODDS, 0.9)
    best = growth_rate(KELLY, P, ODDS)
    for r in rows:
        assert r.true_kelly == pytest.approx(best)
        assert r.full_on_estimate < best and r.half_on_estimate < best
    small, _, large = rows
    assert small.full_on_estimate < 0 < large.full_on_estimate  # small samples lose money
    assert small.half_on_estimate > small.full_on_estimate  # half Kelly protects
    assert large.full_on_estimate > large.half_on_estimate  # with a good estimate, full wins
    assert large.full_on_estimate == pytest.approx(best, rel=0.03)
    # P(no bet) at n = 10 is P(at most 5 wins), by direct binomial sum
    by_hand = sum(math.comb(10, k) * P**k * (1 - P) ** (10 - k) for k in range(6))
    assert small.p_no_bet == pytest.approx(by_hand)
    assert [r.p_no_bet for r in rows] == sorted((r.p_no_bet for r in rows), reverse=True)


# ---- report and CLI --------------------------------------------------------------------


def _fixed_report() -> kelly_report.KellyReport:
    def row(multiple: float, growth: float, sim: float, hit: float) -> FractionResult:
        return FractionResult(
            multiple=multiple,
            fraction=multiple * KELLY,
            growth_exact=growth,
            growth_sim=McResult(sim, 0.0001, 1000),
            median_wealth=12.5,
            mean_wealth=20.0,
            p_below_ruin_level=McResult(0.01, 0.003, 1000),
            p_hit_drawdown_level=McResult(hit, 0.01, 1000),
            max_drawdown_quantiles=(0.5, 0.7, 0.9),
        )

    return kelly_report.KellyReport(
        p=P,
        odds=ODDS,
        kelly=F(1, 10),
        bets=100,
        paths=1000,
        ruin_level=0.1,
        drawdown_level=0.5,
        max_fraction=0.9,
        tol_se=4.0,
        results=[row(0.5, 0.003753, 0.0038, 0.12), row(1.0, 0.005008, 0.0049, 0.47)],
        uncertainty=[
            UncertaintyRow(10, -0.03, -0.001, 0.005, 0.5, 0.27),
            UncertaintyRow(1000, 0.0045, 0.0036, 0.005, 0.001, 0.001),
        ],
    )


def test_kelly_report_regression() -> None:
    """Fixed inputs must render exactly the stored file."""
    info = RunInfo(
        "20260101T000000Z-abcdef",
        "2026-01-01T00:00:00+00:00",
        "0123456789ab",
        False,
        "feedfacecafe",
        7,
    )
    text = kelly_report.render(_fixed_report(), info)
    assert text.index("## Limitations") < text.index("## Result")
    assert text == (REPO / "tests" / "expected" / "kelly.md").read_text()


def test_report_flags_a_growth_mismatch() -> None:
    report = _fixed_report()
    assert report.growth_checks_pass()
    bad = FractionResult(
        **{**report.results[0].__dict__, "growth_sim": McResult(0.01, 0.0001, 1000)}
    )
    broken = kelly_report.KellyReport(**{**report.__dict__, "results": [bad]})
    assert not broken.growth_checks_pass()


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    raw = yaml.safe_load((REPO / "config.yaml").read_text())
    raw["kelly"] |= {"bets": 200, "paths": 500, "sample_sizes": [10, 100]}
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(raw))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COLUMNS", "200")
    return tmp_path


def test_kelly_command_writes_report_and_figures(workdir: Path) -> None:
    first = runner.invoke(app, ["kelly"])
    assert first.exit_code == 0, first.output
    assert "Kelly fraction 1/10" in first.output
    folder = workdir / "reports" / "kelly"
    report = (folder / "kelly.md").read_text()
    assert "**f\\* = 1/10**" in report and "paper-lab" in report
    for name in ("growth_curve.png", "estimated_edge.png"):
        data = (folder / name).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) > 5000
    runner.invoke(app, ["kelly"])
    again = (folder / "kelly.md").read_text()
    assert report.split("\n---\n")[0] == again.split("\n---\n")[0]  # same seed, same numbers


def test_kelly_bet_command(workdir: Path) -> None:
    result = runner.invoke(app, ["kelly-bet", "--p", "0.55", "--odds", "1"])
    assert result.exit_code == 0 and "1/10" in result.output and "half Kelly" in result.output
    none = runner.invoke(app, ["kelly-bet", "--p", "0.5", "--odds", "1"])
    assert "the Kelly bet is 0" in none.output
    assert runner.invoke(app, ["kelly-bet", "--p", "1.5"]).exit_code == 2


def test_config_rejects_a_bet_without_edge_or_a_ruinous_multiple() -> None:
    from pydantic import ValidationError

    from ev_lab.config import Config

    raw = yaml.safe_load((REPO / "config.yaml").read_text())
    for change in ({"p": 0.5}, {"multiples": [1.0, 10.0]}):
        bad = {**raw, "kelly": {**raw["kelly"], **change}}
        with pytest.raises(ValidationError, match="kelly"):
            Config.model_validate(bad)
