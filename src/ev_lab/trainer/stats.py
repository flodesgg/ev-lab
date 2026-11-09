"""Practice statistics: accuracy and speed per category over time, streak, weak spots.

Days are UTC days (the logs store UTC timestamps). Numbers are reported as they are.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # files only, never a window
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from ev_lab.practice_log import read_rows
from ev_lab.puzzles import log as puzzle_log
from ev_lab.runinfo import RunInfo
from ev_lab.trainer import market_game, math_log
from ev_lab.trainer.mental_math import TITLES

SUMMARY_NAME = "summary.md"
ACCURACY_PNG = "math_accuracy.png"
SPEED_PNG = "math_speed.png"

_SURFACE, _INK, _INK_SOFT, _SERIES = "#fcfcfb", "#0b0b0b", "#52514e", "#2a78d6"


@dataclass(frozen=True)
class CategoryStat:
    category: str
    answers: int
    accuracy: float
    median_seconds: float


@dataclass(frozen=True)
class Summary:
    today: date
    streak: int
    practice_days: int
    math_answers: int
    math_sessions: int
    categories: list[CategoryStat]  # all time
    weakest: list[CategoryStat]  # over the recent window
    weakest_window: int
    puzzles_total: int
    puzzles_tried: int
    puzzles_solved: int
    puzzle_attempts: int
    market_games: int
    market_rounds: int
    market_total_pnl: float
    market_quotes_containing_fair: int


def _frame(path: Path, header: tuple[str, ...]) -> pd.DataFrame:
    df = pd.DataFrame(read_rows(path, header), columns=list(header))
    df["day"] = pd.to_datetime(df["timestamp_utc"], utc=True).dt.date
    return df


def load_math(practice_dir: Path) -> pd.DataFrame:
    df = _frame(practice_dir / math_log.FILE_NAME, math_log.HEADER)
    df["correct"] = df["correct"].astype(int)
    df["seconds"] = df["seconds"].astype(float)
    return df


def load_puzzles(practice_dir: Path) -> pd.DataFrame:
    df = _frame(practice_dir / puzzle_log.FILE_NAME, puzzle_log.HEADER)
    df["correct"] = df["correct"].astype(int)
    return df


def load_market(practice_dir: Path) -> pd.DataFrame:
    df = _frame(practice_dir / market_game.FILE_NAME, market_game.HEADER)
    for column in ("bid", "ask", "fair_value", "pnl"):
        df[column] = df[column].astype(float)
    return df


def category_stats(math: pd.DataFrame) -> list[CategoryStat]:
    out = []
    for category in TITLES:
        rows = math[math["category"] == category]
        if len(rows):
            out.append(
                CategoryStat(
                    category,
                    len(rows),
                    float(rows["correct"].mean()),
                    float(rows["seconds"].median()),
                )
            )
    return out


def weakest_categories(
    math: pd.DataFrame, window: int, min_answers: int, count: int = 3
) -> list[CategoryStat]:
    """Lowest accuracy first (slower first on ties), over the last `window` answers.
    Categories with fewer than `min_answers` answers in the window are not ranked."""
    stats = [s for s in category_stats(math.tail(window)) if s.answers >= min_answers]
    return sorted(stats, key=lambda s: (s.accuracy, -s.median_seconds))[:count]


def daily_table(math: pd.DataFrame) -> pd.DataFrame:
    """One row per (day, category): answers, accuracy, median seconds."""
    grouped = math.groupby(["day", "category"], sort=True)
    return grouped.agg(
        answers=("correct", "size"),
        accuracy=("correct", "mean"),
        median_seconds=("seconds", "median"),
    ).reset_index()


def streak(days: set[date], today: date) -> int:
    """Consecutive practice days ending today, or ending yesterday if today is still open."""
    current = today if today in days else today - timedelta(days=1)
    length = 0
    while current in days:
        length += 1
        current -= timedelta(days=1)
    return length


def summarise(
    practice_dir: Path, today: date, window: int, min_answers: int, puzzles_total: int
) -> Summary:
    math, puzzles, market = (
        load_math(practice_dir),
        load_puzzles(practice_dir),
        load_market(practice_dir),
    )
    days = set(math["day"]) | set(puzzles["day"]) | set(market["day"])
    solved = puzzles[puzzles["correct"] == 1]["puzzle_id"].nunique()
    inside = (
        (market["bid"] <= market["fair_value"]) & (market["fair_value"] <= market["ask"])
    ).sum()
    return Summary(
        today=today,
        streak=streak(days, today),
        practice_days=len(days),
        math_answers=len(math),
        math_sessions=int(math["session_id"].nunique()),
        categories=category_stats(math),
        weakest=weakest_categories(math, window, min_answers),
        weakest_window=window,
        puzzles_total=puzzles_total,
        puzzles_tried=int(puzzles["puzzle_id"].nunique()),
        puzzles_solved=int(solved),
        puzzle_attempts=len(puzzles),
        market_games=int(market["session_id"].nunique()) if len(market) else 0,
        market_rounds=len(market),
        market_total_pnl=float(market["pnl"].sum()),
        market_quotes_containing_fair=int(inside),
    )


def _stat_row(s: CategoryStat) -> str:
    return f"| {TITLES[s.category]} | {s.answers} | {s.accuracy:.0%} | {s.median_seconds:.1f} |"


def render_summary(s: Summary, info: RunInfo) -> str:
    lines = [
        "# Practice summary",
        "",
        "## Limitations (read first)",
        "",
        "- Self-timed at a keyboard: typing speed is part of every time, and nobody is watching.",
        "- The math trainer asks weak categories more often (adaptive weights), so the overall "
        "accuracy is pulled down relative to an even mix. Compare within a category.",
        "- An answer that arrives after a session's deadline is discarded and not logged.",
        "- Days are UTC days. A category with few answers has a noisy accuracy.",
        "- Market-game P&L is dominated by luck over a few games; the share of quotes that "
        "contain the fair value is the steadier number.",
        "",
        f"## As of {s.today.isoformat()} (UTC)",
        "",
        f"- Streak: **{s.streak}** day(s) in a row; {s.practice_days} practice day(s) in total.",
        f"- Mental math: {s.math_answers} answers in {s.math_sessions} session(s).",
        f"- Puzzles: {s.puzzles_solved} solved, {s.puzzles_tried} tried, of {s.puzzles_total} "
        f"({s.puzzle_attempts} attempts).",
    ]
    if s.market_rounds:
        lines.append(
            f"- Market game: {s.market_games} game(s), total P&L {s.market_total_pnl:+.2f}; "
            f"{s.market_quotes_containing_fair} of {s.market_rounds} quotes contained the "
            "fair value."
        )
    else:
        lines.append("- Market game: no games yet.")
    lines += ["", f"## Weakest categories (last {s.weakest_window} math answers)", ""]
    if s.weakest:
        lines += ["| category | answers | accuracy | median s |", "|---|---|---|---|"]
        lines += [_stat_row(c) for c in s.weakest]
    else:
        lines.append("Not enough answers yet to rank categories.")
    lines += ["", "## Mental math by category (all time)", ""]
    if s.categories:
        lines += ["| category | answers | accuracy | median s |", "|---|---|---|---|"]
        lines += [_stat_row(c) for c in s.categories]
        lines += [
            "",
            f"Figures: `{ACCURACY_PNG}` (accuracy per day), `{SPEED_PNG}` (median seconds).",
        ]
    else:
        lines.append("No math answers yet.")
    lines += ["", "---", info.markdown_footer(), ""]
    return "\n".join(lines)


def plot_by_category(
    daily: pd.DataFrame, column: str, title: str, path: Path, percent: bool
) -> None:
    """Small multiples: one panel per category, one line each, a shared y-axis."""
    fig, axes = plt.subplots(2, 4, figsize=(13, 5.6), sharex=True, sharey=True, facecolor=_SURFACE)
    top = 1.0 if percent else max(1.0, float(daily[column].max())) * 1.1
    for ax, (category, name) in zip(axes.flat, TITLES.items(), strict=True):
        rows = daily[daily["category"] == category]
        ax.set_facecolor(_SURFACE)
        ax.set_title(name, fontsize=10, color=_INK, loc="left")
        ax.set_ylim(-0.04 * top, top * 1.04)
        ax.grid(axis="y", color="#e4e3df", linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color("#c3c2b7")
        ax.tick_params(colors=_INK_SOFT, labelsize=8, length=0)
        if percent:
            ax.yaxis.set_major_formatter(lambda v, _pos: f"{v:.0%}")
        if len(rows) == 0:
            ax.text(
                0.5,
                0.5,
                "no answers yet",
                transform=ax.transAxes,
                ha="center",
                color=_INK_SOFT,
                fontsize=9,
            )
            continue
        days = pd.to_datetime(rows["day"])
        ax.plot(
            days,
            rows[column],
            color=_SERIES,
            linewidth=2,
            marker="o",
            markersize=6,
            markeredgecolor=_SURFACE,
            markeredgewidth=1.5,
        )
        last = rows.iloc[-1]
        label = f"{last[column]:.0%}" if percent else f"{last[column]:.1f} s"
        ax.annotate(
            label,
            (days.iloc[-1], last[column]),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=9,
            color=_INK,
        )
    all_days = pd.to_datetime(daily["day"])
    pad = pd.Timedelta(hours=12) if all_days.nunique() > 1 else pd.Timedelta(days=1)
    for ax in axes.flat:  # the x-axis is shared: every panel shows the same dates
        ax.set_xlim(all_days.min() - pad, all_days.max() + pad)
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=1, maxticks=4))  # type: ignore[no-untyped-call]
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))  # type: ignore[no-untyped-call]
    fig.suptitle(title, fontsize=13, color=_INK, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130, facecolor=_SURFACE)
    plt.close(fig)


def write_report(
    report_dir: Path, summary: Summary, math: pd.DataFrame, info: RunInfo
) -> list[Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    written = [report_dir / SUMMARY_NAME]
    written[0].write_text(render_summary(summary, info))
    if len(math):
        daily = daily_table(math)
        plot_by_category(
            daily,
            "accuracy",
            "Mental math: accuracy per day, by category",
            report_dir / ACCURACY_PNG,
            percent=True,
        )
        plot_by_category(
            daily,
            "median_seconds",
            "Mental math: median seconds per answer per day, by category",
            report_dir / SPEED_PNG,
            percent=False,
        )
        written += [report_dir / ACCURACY_PNG, report_dir / SPEED_PNG]
    return written
