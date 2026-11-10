"""The `ev leduc` report: CFR+ against vanilla CFR on Leduc hold'em."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ev_lab.games import kuhn
from ev_lab.games.leduc_cfr import Checkpoint
from ev_lab.runinfo import RunInfo

REPORT_NAME = "leduc.md"
FIGURE_NAME = "leduc_exploitability.png"
_SURFACE, _INK, _INK_SOFT = "#fcfcfb", "#0b0b0b", "#52514e"
_BLUE, _ORANGE = "#2a78d6", "#eb6834"
EV_TOLERANCE = 1e-9


@dataclass(frozen=True)
class LeducReport:
    infosets: int  # by rank, as solved here
    card_level_infosets: int  # with suits kept apart, as other implementations count
    public_nodes: int  # decision nodes of the public tree
    uniform_value_exact: Fraction  # both players uniformly random, slow evaluator
    uniform_value_fast: float  # the same from the fast evaluator
    plus: Sequence[Checkpoint]
    vanilla: Sequence[Checkpoint]
    value_fast: float  # CFR+ average strategy, fast evaluator
    value_slow: float  # the same strategy through the slow card-by-card evaluator
    br_achieved: tuple[float, float]  # slow evaluation of each best-response policy
    br_claimed: tuple[float, float]  # the fast best-response values

    def ok(self) -> bool:
        return (
            abs(self.uniform_value_fast - float(self.uniform_value_exact)) < EV_TOLERANCE
            and abs(self.value_fast - self.value_slow) < EV_TOLERANCE
            and all(
                abs(a - c) < EV_TOLERANCE
                for a, c in zip(self.br_achieved, self.br_claimed, strict=True)
            )
        )


def render(r: LeducReport, info: RunInfo) -> str:
    plus, vanilla = r.plus[-1], r.vanilla[-1]
    kuhn_infosets = sum(len(side) for side in kuhn.INFOSETS)
    lines = [
        "# Leduc hold'em: CFR+ against vanilla CFR",
        "",
        "## Limitations (read first)",
        "",
        "- Leduc hold'em is still a toy: 6 cards and two betting rounds. It has "
        f"{r.infosets // kuhn_infosets} times the information sets of Kuhn poker "
        f"({r.infosets} against {kuhn_infosets}), which is not a step towards real poker sizes.",
        "- The strategy is an approximation after a finite number of iterations. No exact "
        "equilibrium and no reference game value from a source is used; the evidence is the "
        "exploitability, computed by an exact best response.",
        "- The best-response routine and the solver share one tree. The cross-checks below "
        "run strategies through a second, slow evaluator that deals actual cards; they "
        "confirm values, and that each best response is achievable, not that it is the "
        "largest possible.",
        "- Exploitability here is the average of the two best-response gains (NashConv / 2), "
        "in chips per hand, with antes of 1.",
        "",
        "## Result",
        "",
        f"- Cross-checks between the fast and the slow evaluator: "
        f"**{'all agree' if r.ok() else 'DISAGREE'}** (tolerance {EV_TOLERANCE:g}).",
        f"- CFR+ after {plus.iteration:,} iterations: exploitability "
        f"**{plus.exploitability:.6f}**, value for the first player {plus.value:+.6f}.",
        f"- Vanilla CFR after {vanilla.iteration:,} iterations: exploitability "
        f"{vanilla.exploitability:.6f}, that is "
        f"{vanilla.exploitability / plus.exploitability:,.0f} times the CFR+ figure.",
        f"- Size: {r.infosets} information sets by rank ({r.card_level_infosets} when suits "
        f"are kept apart), {r.public_nodes} decision nodes in the public tree.",
        "",
        "## Cross-checks (fast vector evaluator vs slow card-by-card evaluator)",
        "",
        "| quantity | fast | slow | difference |",
        "|---|---|---|---|",
        f"| both players uniformly random | {r.uniform_value_fast:+.12f} | "
        f"{r.uniform_value_exact} = {float(r.uniform_value_exact):+.12f} (exact) | "
        f"{r.uniform_value_fast - float(r.uniform_value_exact):+.1e} |",
        f"| CFR+ average strategy | {r.value_fast:+.12f} | {r.value_slow:+.12f} | "
        f"{r.value_fast - r.value_slow:+.1e} |",
    ]
    for seat in (0, 1):
        lines.append(
            f"| best response of player {seat + 1} | {r.br_claimed[seat]:+.12f} | "
            f"{r.br_achieved[seat]:+.12f} | {r.br_claimed[seat] - r.br_achieved[seat]:+.1e} |"
        )
    lines += [
        "",
        "## Convergence",
        "",
        f"Figure: `{FIGURE_NAME}` (log-log).",
        "",
        "| iterations | CFR+ exploitability | vanilla CFR exploitability | CFR+ value |",
        "|---|---|---|---|",
    ]
    vanilla_at = {c.iteration: c for c in r.vanilla}
    for c in r.plus:
        other = vanilla_at.get(c.iteration)
        other_text = f"{other.exploitability:.6f}" if other else ""
        lines.append(
            f"| {c.iteration:,} | {c.exploitability:.6f} | {other_text} | {c.value:+.6f} |"
        )
    lines += ["", "---", info.markdown_footer(), ""]
    return "\n".join(lines)


def plot(r: LeducReport, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.4), facecolor=_SURFACE)
    ax.set_facecolor(_SURFACE)
    lowest = 1.0
    for label, points, color, marker in (
        ("vanilla CFR", r.vanilla, _ORANGE, "s"),
        ("CFR+", r.plus, _BLUE, "o"),
    ):
        xs = [c.iteration for c in points if c.exploitability > 0]
        ys = [c.exploitability for c in points if c.exploitability > 0]
        ax.plot(xs, ys, color=color, linewidth=2, marker=marker, markersize=5,
                markeredgecolor=_SURFACE, markeredgewidth=1.2, label=label)  # fmt: skip
        ax.annotate(f"{label}: {ys[-1]:.6f}", (xs[-1], ys[-1]), textcoords="offset points",
                    xytext=(-10, -16), ha="right", fontsize=9, color=_INK)  # fmt: skip
        lowest = min(lowest, min(ys))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylim(bottom=lowest * 0.25)
    ax.set_xlabel("iterations", color=_INK_SOFT, fontsize=9)
    ax.set_ylabel("exploitability (chips per hand)", color=_INK_SOFT, fontsize=9)
    ax.set_title("Leduc hold'em: exploitability of the average strategy", fontsize=11,
                 color=_INK, loc="left")  # fmt: skip
    ax.grid(which="major", color="#e4e3df", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#c3c2b7")
    ax.tick_params(colors=_INK_SOFT, labelsize=8, which="both", length=0)
    legend = ax.legend(loc="upper right", fontsize=9, frameon=False)
    for text in legend.get_texts():
        text.set_color(_INK)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130, facecolor=_SURFACE)
    plt.close(fig)


def write(report_dir: Path, report: LeducReport, info: RunInfo) -> list[Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    text_path = report_dir / REPORT_NAME
    text_path.write_text(render(report, info))
    plot(report, report_dir / FIGURE_NAME)
    return [text_path, report_dir / FIGURE_NAME]
