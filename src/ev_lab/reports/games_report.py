"""The `ev games` report: matrix games by LP, regret matching, CFR on Kuhn poker."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ev_lab.games import kuhn
from ev_lab.games.cfr import Checkpoint
from ev_lab.games.indifference import bluff_share, calling_frequency
from ev_lab.games.matrix import MatrixSolution
from ev_lab.runinfo import RunInfo

REPORT_NAME = "games.md"
FIGURE_NAME = "kuhn_exploitability.png"
_SURFACE, _INK, _INK_SOFT, _SERIES = "#fcfcfb", "#0b0b0b", "#52514e", "#2a78d6"


@dataclass(frozen=True)
class RegretRow:
    game: str
    iterations: int
    row: Sequence[float]
    col: Sequence[float]
    max_error: float  # largest |average strategy - LP strategy| over both players


@dataclass(frozen=True)
class GamesReport:
    matrix: Sequence[tuple[str, MatrixSolution]]
    regret: Sequence[RegretRow]
    checkpoints: Sequence[Checkpoint]
    strategy: dict[str, float]  # CFR average strategy, infoset -> P(bet)
    family_alphas: Sequence[Fraction]  # equilibria verified exactly
    family_values: Sequence[Fraction]
    family_exploitabilities: Sequence[Fraction]

    def ok(self) -> bool:
        return (
            all(s.certified for _, s in self.matrix)
            and all(v == kuhn.GAME_VALUE for v in self.family_values)
            and all(e == 0 for e in self.family_exploitabilities)
        )


def _probs(p: Sequence[Fraction]) -> str:
    return "(" + ", ".join(str(v) for v in p) + ")"


def _indifference_row(alpha: Fraction) -> str:
    """The equilibrium's own frequencies, to compare with the indifference formulas."""
    s = kuhn.equilibrium(alpha)
    bluffs = s["J"] / (s["J"] + s["K"])  # jacks among player 1's bets (kings bet for value)
    calls = (s["Qb"] + s["Kb"]) / 2  # player 2 holds Q or K equally often against a jack
    return f"| {alpha} | {bluffs} | {calls} |"


def _floats(p: Sequence[float]) -> str:
    return "(" + ", ".join(f"{v:.4f}" for v in p) + ")"


def render(r: GamesReport, info: RunInfo) -> str:
    last = r.checkpoints[-1]
    alpha, deviation = kuhn.family_distance(r.strategy)
    target = kuhn.equilibrium(Fraction(alpha))
    lines = [
        "# Game theory: matrix games, regret matching, CFR on Kuhn poker",
        "",
        "## Limitations (read first)",
        "",
        "- Kuhn poker has 12 information sets. Nothing here says how these methods scale; "
        "real games need sampling and abstraction, which are not built.",
        "- CFR results are approximations after a finite number of iterations. The exact "
        "statements are: the certified LP solutions, and the exact check of the equilibrium "
        "family (value and exploitability computed with Fractions).",
        "- Regret matching uses sampled actions, so its averages are random; the seed is fixed.",
        "- Exploitability here is the average of the two best-response gains (NashConv / 2).",
        "",
        "## Result",
        "",
        f"- Overall: **{'all exact checks pass' if r.ok() else 'AN EXACT CHECK FAILED'}**.",
        f"- Kuhn poker, vanilla CFR, {last.iteration:,} iterations: value for player 1 "
        f"{last.value:+.6f} (theory -1/18 = {float(kuhn.GAME_VALUE):+.6f}), exploitability "
        f"{last.exploitability:.6f}.",
        f"- Learned strategy: alpha = P(bet | jack) = {alpha:.4f}; largest deviation from the "
        f"equilibrium with that alpha: {deviation:.4f}.",
        "",
        "## Zero-sum matrix games by linear programming (exact, certified)",
        "",
        "| game | value | row strategy | column strategy | certified |",
        "|---|---|---|---|---|",
    ]
    for name, s in r.matrix:
        lines.append(
            f"| {name} | {s.value} | {_probs(s.row)} | {_probs(s.col)} | "
            f"{'yes' if s.certified else '**NO**'} |"
        )
    lines += [
        "",
        "Certified = the row strategy guarantees the value against every column and the "
        "column strategy concedes no more against every row, checked in exact arithmetic.",
        "",
        "## Regret matching in self-play (simulation)",
        "",
        "| game | iterations | average row strategy | average column strategy | max error vs LP |",
        "|---|---|---|---|---|",
    ]
    for row in r.regret:
        lines.append(
            f"| {row.game} | {row.iterations:,} | {_floats(row.row)} | {_floats(row.col)} | "
            f"{row.max_error:.4f} |"
        )
    lines += [
        "",
        "## Kuhn poker: the equilibrium family, checked exactly",
        "",
        "| alpha | value for player 1 | exploitability |",
        "|---|---|---|",
    ]
    for a, v, e in zip(r.family_alphas, r.family_values, r.family_exploitabilities, strict=True):
        lines.append(f"| {a} | {v} | {e} |")
    lines += [
        "",
        "## Indifference frequencies in Kuhn poker (exact)",
        "",
        f"Pot 2 (two antes), bet 1. Bluff share that makes a caller indifferent, B / (P + 2B): "
        f"**{bluff_share(2, 1)}**. Calling frequency that makes a bluff break even, "
        f"P / (P + B): **{calling_frequency(2, 1)}**.",
        "",
        "| alpha | bluffs in player 1's betting range | player 2 calls a jack's bluff |",
        "|---|---|---|",
        *[_indifference_row(a) for a in r.family_alphas if a > 0],
        "",
        "## Kuhn poker: CFR convergence (approximation)",
        "",
        f"Figure: `{FIGURE_NAME}` (log-log).",
        "",
        "| iterations | exploitability | value for player 1 |",
        "|---|---|---|",
    ]
    for c in r.checkpoints:
        lines.append(f"| {c.iteration:,} | {c.exploitability:.6f} | {c.value:+.6f} |")
    lines += [
        "",
        "## Kuhn poker: learned strategy vs equilibrium",
        "",
        "P(bet or call) at each information set (card + history; p = pass, b = bet).",
        "",
        "| information set | learned | equilibrium at learned alpha | difference |",
        "|---|---|---|---|",
    ]
    for name in (*kuhn.INFOSETS[0], *kuhn.INFOSETS[1]):
        eq = float(target[name])
        lines.append(
            f"| `{name}` | {r.strategy[name]:.4f} | {eq:.4f} | {r.strategy[name] - eq:+.4f} |"
        )
    lines += ["", "---", info.markdown_footer(), ""]
    return "\n".join(lines)


def plot_exploitability(checkpoints: Sequence[Checkpoint], path: Path) -> None:
    """Exploitability against iterations on log-log axes, with a 1/sqrt(T) guide line."""
    xs = [c.iteration for c in checkpoints if c.exploitability > 0]
    ys = [c.exploitability for c in checkpoints if c.exploitability > 0]
    fig, ax = plt.subplots(figsize=(7.2, 4.4), facecolor=_SURFACE)
    ax.set_facecolor(_SURFACE)
    guide = [ys[0] * (xs[0] / x) ** 0.5 for x in xs]
    ax.plot(xs, guide, color="#a8a79f", linewidth=1.2, linestyle="--")
    mid = len(xs) // 3
    ax.annotate(
        "guide: slope of 1/sqrt(T)", (xs[mid], guide[mid]), textcoords="offset points",
        xytext=(10, 10), ha="left", fontsize=9, color=_INK_SOFT,
    )  # fmt: skip
    ax.plot(xs, ys, color=_SERIES, linewidth=2, marker="o", markersize=5,
            markeredgecolor=_SURFACE, markeredgewidth=1.2)  # fmt: skip
    ax.annotate(
        f"{ys[-1]:.5f} after {xs[-1]:,}", (xs[-1], ys[-1]), textcoords="offset points",
        xytext=(-6, -14), ha="right", fontsize=9, color=_INK,
    )  # fmt: skip
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylim(min(ys) * 0.35, max(max(ys), max(guide)) * 1.6)
    ax.set_xlabel("CFR iterations", color=_INK_SOFT, fontsize=9)
    ax.set_ylabel("exploitability (chips per hand)", color=_INK_SOFT, fontsize=9)
    ax.set_title(
        "Kuhn poker: exploitability of the CFR average strategy", fontsize=11, color=_INK,
        loc="left",
    )  # fmt: skip
    ax.grid(which="major", color="#e4e3df", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#c3c2b7")
    ax.tick_params(colors=_INK_SOFT, labelsize=8, which="both", length=0)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130, facecolor=_SURFACE)
    plt.close(fig)


def write(report_dir: Path, report: GamesReport, info: RunInfo) -> list[Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    text_path = report_dir / REPORT_NAME
    text_path.write_text(render(report, info))
    plot_exploitability(report.checkpoints, report_dir / FIGURE_NAME)
    return [text_path, report_dir / FIGURE_NAME]
