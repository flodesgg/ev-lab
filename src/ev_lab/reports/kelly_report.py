"""The `ev kelly` report: growth curve, simulated paths, approximations, estimated edge."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes

from ev_lab.kelly.core import expected_wealth_factor, growth_rate, hit_probability_approx
from ev_lab.kelly.simulate import FractionResult
from ev_lab.kelly.uncertainty import UncertaintyRow
from ev_lab.prob.montecarlo import McResult
from ev_lab.runinfo import RunInfo

REPORT_NAME = "kelly.md"
GROWTH_PNG = "growth_curve.png"
UNCERTAINTY_PNG = "estimated_edge.png"
_SURFACE, _INK, _INK_SOFT = "#fcfcfb", "#0b0b0b", "#52514e"
_BLUE, _ORANGE, _GREY = "#2a78d6", "#eb6834", "#8a897f"


@dataclass(frozen=True)
class KellyReport:
    p: float
    odds: float
    kelly: Fraction
    bets: int
    paths: int
    ruin_level: float
    drawdown_level: float
    max_fraction: float
    tol_se: float
    results: Sequence[FractionResult]
    uncertainty: Sequence[UncertaintyRow]

    def growth_checks_pass(self) -> bool:
        """Simulated mean log growth within tolerance of the exact g(f), for every size."""
        return all(abs(_z(r.growth_sim, r.growth_exact)) < self.tol_se for r in self.results)


def _z(mc: McResult, exact: float) -> float:
    return (mc.estimate - exact) / mc.se if mc.se > 0 else 0.0


def _pm(mc: McResult, digits: int = 4) -> str:
    return f"{mc.estimate:.{digits}f} ± {mc.se:.{digits}f}"


def render(r: KellyReport, info: RunInfo) -> str:
    f_star = float(r.kelly)
    by_multiple = {x.multiple: x for x in r.results}
    half_better = [u.n for u in r.uncertainty if u.half_on_estimate > u.full_on_estimate]
    full_better = [u.n for u in r.uncertainty if u.full_on_estimate > u.half_on_estimate]
    negative = [u.n for u in r.uncertainty if u.full_on_estimate < 0]
    lines = [
        "# Kelly criterion and bet sizing",
        "",
        "## Limitations (read first)",
        "",
        "- One repeated binary bet with known odds, independent outcomes, no costs, no limits, "
        "and wealth that can be divided without end. Real edges are none of these.",
        "- Three kinds of numbers appear and are labelled: **exact** (formulas and binomial "
        "sums), **simulation** (with a standard error) and **approximation** (continuous-time "
        "formulas that assume many small bets and an infinite horizon).",
        f"- The simulation has a finite horizon ({r.bets:,} bets). Events that take long to "
        "happen (hitting a drawdown level when betting large) are under-counted relative to "
        "the infinite-horizon approximation.",
        "- Mean terminal wealth is dominated by a few lucky paths; the sample mean is far "
        "below the exact expectation for the larger bet sizes. The median is the typical "
        "outcome.",
        f"- With an estimated edge the stake is capped at {r.max_fraction:.0%} of wealth. "
        "Without a cap, a sample of only wins makes naive Kelly stake everything, and the "
        "expected log growth is minus infinity.",
        "",
        "## Result",
        "",
        f"- Bet: win probability p = {r.p:g}, net odds b = {r.odds:g}. Kelly fraction "
        f"**f\\* = {r.kelly}** = {f_star:.4f} (exact). Growth at f\\*: "
        f"{growth_rate(f_star, r.p, r.odds):.6f} per bet; at 2 f\\*: "
        f"{growth_rate(2 * f_star, r.p, r.odds):+.6f} per bet (exact; about zero).",
        f"- Simulated mean log growth agrees with the exact g(f) within {r.tol_se:g} SE for "
        f"every bet size: **{'yes' if r.growth_checks_pass() else 'NO'}**.",
    ]
    if 1.0 in by_multiple and 0.5 in by_multiple:
        full, half = by_multiple[1.0], by_multiple[0.5]
        lines.append(
            f"- Half Kelly keeps {half.growth_exact / full.growth_exact:.0%} of the growth "
            f"rate (exact) while the simulated chance of ever falling to "
            f"{r.drawdown_level:.0%} of the start drops from "
            f"{full.p_hit_drawdown_level.estimate:.1%} to {half.p_hit_drawdown_level.estimate:.1%}."
        )
    if negative:
        lines.append(
            f"- Sizing full Kelly from an estimate of p has **negative** expected growth for "
            f"n = {', '.join(str(n) for n in negative)} past bets (exact)."
        )
    if half_better:
        lines.append(
            "- Half Kelly on the estimate has higher expected growth than full Kelly on the "
            f"estimate for n = {', '.join(f'{n:,}' for n in half_better)}"
            + (
                f"; full Kelly is better for n = {', '.join(f'{n:,}' for n in full_better)}."
                if full_better
                else "."
            )
        )
    lines += [
        "",
        "## Bet sizes on the same simulated paths",
        "",
        f"{r.paths:,} paths of {r.bets:,} bets, common random numbers across bet sizes. "
        "Start wealth = 1. (z is the same in every row: on shared paths the log growth of "
        "every bet size is a linear function of the same number of wins.)",
        "",
        "| x Kelly | stake f | g(f) exact | mean log growth, sim ± SE | z | median wealth "
        "| mean wealth, sim | mean wealth, exact |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for x in r.results:
        exact_mean = expected_wealth_factor(x.fraction, r.p, r.odds) ** r.bets
        lines.append(
            f"| {x.multiple:g} | {x.fraction:.4f} | {x.growth_exact:+.6f} | "
            f"{x.growth_sim.estimate:+.6f} ± {x.growth_sim.se:.6f} | "
            f"{_z(x.growth_sim, x.growth_exact):+.2f} | {x.median_wealth:,.3g} | "
            f"{x.mean_wealth:,.3g} | {exact_mean:,.3g} |"
        )
    lines += [
        "",
        "## Risk: simulation vs continuous-time approximation",
        "",
        f"Approximation: P(wealth ever falls to x of its start) = x^(2/c - 1) when staking c "
        f"x Kelly (1 for c >= 2); here x = {r.drawdown_level:g}.",
        "",
        f"| x Kelly | P(final < {r.ruin_level:g}), sim ± SE | P(ever <= {r.drawdown_level:g}), "
        "sim ± SE | approximation | sim - approx | max drawdown: median / 90% / 99% |",
        "|---|---|---|---|---|---|",
    ]
    for x in r.results:
        approx = hit_probability_approx(r.drawdown_level, x.multiple)
        q50, q90, q99 = x.max_drawdown_quantiles
        lines.append(
            f"| {x.multiple:g} | {_pm(x.p_below_ruin_level)} | {_pm(x.p_hit_drawdown_level)} | "
            f"{approx:.4f} | {x.p_hit_drawdown_level.estimate - approx:+.4f} | "
            f"{q50:.1%} / {q90:.1%} / {q99:.1%} |"
        )
    lines += [
        "",
        "Where they agree: small and moderate bet sizes, where the level is reached early or "
        "never. Where they do not: at 1.5 and 2 x Kelly the approximation counts paths that "
        f"would reach the level after bet {r.bets:,}, and it ignores that wealth moves in "
        "jumps, not continuously.",
        "",
        "## Sizing from an estimated edge (exact binomial sums)",
        "",
        "p is estimated from n past bets (p_hat = wins / n) and the stake is Kelly(p_hat) or "
        "half of it; the growth is evaluated at the true p.",
        "",
        "| n past bets | full Kelly on estimate | half Kelly on estimate | true Kelly "
        "| P(estimate shows no edge) | P(stake > 2 x true Kelly) |",
        "|---|---|---|---|---|---|",
    ]
    for u in r.uncertainty:
        lines.append(
            f"| {u.n:,} | {u.full_on_estimate:+.6f} | {u.half_on_estimate:+.6f} | "
            f"{u.true_kelly:+.6f} | {u.p_no_bet:.1%} | {u.p_overbet_2x:.1%} |"
        )
    lines += [
        "",
        "## What this means for paper-lab",
        "",
        "paper-lab reports a setup's expectancy with a bootstrap confidence interval. That "
        "interval is the same object as the uncertainty about p above. If the interval "
        "includes zero, the data cannot tell a positive edge from none: staking the Kelly "
        "fraction of the point estimate is exactly the 'full Kelly on estimate' column at "
        "small n, where expected growth is negative. The disciplined size is the Kelly "
        "fraction of an edge you can defend, the lower end of the interval, and when that "
        "is zero or below, **the Kelly bet is zero**. Until the forward test narrows the "
        "interval, the correct position size is none, and after that a fraction of Kelly.",
        "",
        f"Figures: `{GROWTH_PNG}`, `{UNCERTAINTY_PNG}`.",
        "",
        "---",
        info.markdown_footer(),
        "",
    ]
    return "\n".join(lines)


def _style(ax: Axes) -> None:
    ax.set_facecolor(_SURFACE)
    ax.grid(color="#e4e3df", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#c3c2b7")
    ax.tick_params(colors=_INK_SOFT, labelsize=8, length=0)


def plot_growth(r: KellyReport, path: Path) -> None:
    """g(f) against the staked fraction, with f* and 2 f* marked."""
    f_star = float(r.kelly)
    top = min(0.99, 2.4 * f_star)
    fs = np.linspace(0.0, top, 400)
    gs = [growth_rate(float(f), r.p, r.odds) for f in fs]
    fig, ax = plt.subplots(figsize=(7.2, 4.4), facecolor=_SURFACE)
    _style(ax)
    ax.axhline(0.0, color="#c3c2b7", linewidth=1.0)
    ax.plot(fs, gs, color=_BLUE, linewidth=2)
    for f, label, dy in ((f_star, "f* (Kelly)", 10), (2 * f_star, "2 f*: growth about 0", 10)):
        if f <= top:
            g = growth_rate(f, r.p, r.odds)
            ax.plot([f], [g], marker="o", markersize=8, color=_BLUE,
                    markeredgecolor=_SURFACE, markeredgewidth=2)  # fmt: skip
            ax.annotate(f"{label}\nf = {f:.3f}, g = {g:+.5f}", (f, g), textcoords="offset points",
                        xytext=(0, dy), ha="center", fontsize=9, color=_INK)  # fmt: skip
    ax.set_xlabel("fraction of wealth staked per bet, f", color=_INK_SOFT, fontsize=9)
    ax.set_ylabel("expected log growth per bet, g(f)", color=_INK_SOFT, fontsize=9)
    ax.set_title(
        f"Growth rate against bet size (p = {r.p:g}, odds = {r.odds:g}; exact)",
        fontsize=11, color=_INK, loc="left",
    )  # fmt: skip
    ax.set_ylim(min(gs) * 1.15, max(gs) * 1.9)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130, facecolor=_SURFACE)
    plt.close(fig)


def plot_uncertainty(r: KellyReport, path: Path) -> None:
    """Expected growth against the number of past bets used to estimate p."""
    ns = [u.n for u in r.uncertainty]
    fig, ax = plt.subplots(figsize=(7.2, 4.4), facecolor=_SURFACE)
    _style(ax)
    ax.axhline(0.0, color="#c3c2b7", linewidth=1.0)
    series = (
        ("true Kelly (p known)", [u.true_kelly for u in r.uncertainty], _GREY, "--", None),
        ("full Kelly on estimate", [u.full_on_estimate for u in r.uncertainty], _BLUE, "-", "o"),
        ("half Kelly on estimate", [u.half_on_estimate for u in r.uncertainty], _ORANGE, "-", "s"),
    )
    for label, ys, color, style, marker in series:
        ax.plot(ns, ys, color=color, linewidth=2 if marker else 1.4, linestyle=style,
                marker=marker, markersize=6, markeredgecolor=_SURFACE, markeredgewidth=1.2,
                label=label)  # fmt: skip
    ax.set_xscale("log")
    ax.set_xlabel("past bets used to estimate p (log scale)", color=_INK_SOFT, fontsize=9)
    ax.set_ylabel("expected log growth per bet", color=_INK_SOFT, fontsize=9)
    ax.set_title(
        "Sizing from an estimated edge: full vs half Kelly (exact)", fontsize=11, color=_INK,
        loc="left",
    )  # fmt: skip
    legend = ax.legend(loc="lower right", fontsize=9, frameon=False)
    for text in legend.get_texts():
        text.set_color(_INK)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130, facecolor=_SURFACE)
    plt.close(fig)


def write(report_dir: Path, report: KellyReport, info: RunInfo) -> list[Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    text_path = report_dir / REPORT_NAME
    text_path.write_text(render(report, info))
    plot_growth(report, report_dir / GROWTH_PNG)
    plot_uncertainty(report, report_dir / UNCERTAINTY_PNG)
    return [text_path, report_dir / GROWTH_PNG, report_dir / UNCERTAINTY_PNG]
