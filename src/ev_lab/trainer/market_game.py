"""The market game at the terminal: prompts, the review table, the log."""

from __future__ import annotations

from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path

from ev_lab.fmt import dec, signed
from ev_lab.practice_log import append_row
from ev_lab.puzzles.grading import parse_number
from ev_lab.trainer.io import IO
from ev_lab.trainer.market import MarketGame, RoundRecord

FILE_NAME = "market_log.csv"
HEADER = (
    "timestamp_utc",
    "session_id",
    "quantity",
    "round",
    "known",
    "max_width",
    "bid",
    "ask",
    "fair_value",
    "expected_pnl",
    "trader",
    "side",
    "x",
    "pnl",
)


def _known_text(game: MarketGame, known: tuple[int, ...]) -> str:
    if not known:
        return "nothing"
    return ", ".join(
        f"{label} = {v}" for label, v in zip(game.quantity.labels, known, strict=False)
    )


def _ask_quote(game: MarketGame, io: IO) -> tuple[Fraction, Fraction] | None:
    while True:
        values: list[Fraction] = []
        for name in ("bid", "ask"):
            while True:
                text = io.ask(f"  your {name}: ")
                if text is None:
                    return None
                try:
                    values.append(parse_number(text))
                    break
                except ValueError:
                    io.say("  not a number; try again")
        error = game.quote_error(values[0], values[1])
        if error is None:
            return values[0], values[1]
        io.say(f"  [yellow]{error}[/yellow]")


def _trade_text(record: RoundRecord) -> str:
    if record.side == "buy":
        return f"buys at {dec(record.ask)}"
    if record.side == "sell":
        return f"sells at {dec(record.bid)}"
    return "no trade"


def review_lines(game: MarketGame) -> list[str]:
    """After the game: what was fair, what I quoted, who traded against me."""
    out = [
        f"X = {game.x}. Total P&L: {signed(game.total_pnl())}.",
        "",
        "round | public information | fair value | my quote | trader (their value) | trade "
        "| P&L | EV of my quote",
    ]
    for r in game.records:
        inside = r.bid <= r.fair_value <= r.ask
        theirs = "noise" if r.trader_value is None else f"informed ({dec(r.trader_value, 2)})"
        out.append(
            f"{r.round} | {_known_text(game, r.known)} | {dec(r.fair_value, 3)} | "
            f"{dec(r.bid)} @ {dec(r.ask)}{'' if inside else ' (misses fair value)'} | "
            f"{theirs} | {_trade_text(r)} | {signed(game.pnl(r))} | {signed(r.expected_pnl, 3)}"
        )
    out += [
        "",
        "Fair value = E[X | public information], exact. EV of my quote = expected profit of "
        "that quote before the trader arrived: + half the spread from a noise trader, minus "
        "what an informed trader takes when their value is outside my quote.",
    ]
    return out


def review_rows(game: MarketGame) -> list[dict[str, str]]:
    """The review as one record per round (for the web page)."""
    return [
        {
            "round": str(r.round),
            "public": _known_text(game, r.known),
            "fair_value": dec(r.fair_value, 3),
            "quote": f"{dec(r.bid)} @ {dec(r.ask)}",
            "contains_fair": "yes" if r.bid <= r.fair_value <= r.ask else "no",
            "trader": "noise" if r.trader_value is None else f"informed ({dec(r.trader_value, 2)})",
            "trade": _trade_text(r),
            "pnl": signed(game.pnl(r)),
            "expected_pnl": signed(r.expected_pnl, 3),
        }
        for r in game.records
    ]


def known_text(game: MarketGame) -> str:
    """What is public in the current round."""
    return _known_text(game, game.known())


def trade_text(record: RoundRecord) -> str:
    return "No trade." if record.side == "none" else "A trader " + _trade_text(record) + "."


def log_game(practice_dir: Path, session_id: str, game: MarketGame) -> None:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    for r in game.records:
        append_row(
            practice_dir / FILE_NAME,
            HEADER,
            {
                "timestamp_utc": now,
                "session_id": session_id,
                "quantity": game.quantity.id,
                "round": r.round,
                "known": ";".join(str(v) for v in r.known),
                "max_width": dec(r.max_width),
                "bid": dec(r.bid),
                "ask": dec(r.ask),
                "fair_value": dec(r.fair_value, 6),
                "expected_pnl": dec(r.expected_pnl, 6),
                "trader": r.trader,
                "side": r.side,
                "x": game.x,
                "pnl": dec(game.pnl(r)),
            },
        )


def play(game: MarketGame, io: IO) -> bool:
    """Run one game. Returns False if the input ended before the game did."""
    q = game.quantity
    io.say(f"[bold]Make me a market[/bold]: X = {q.title.lower()}.")
    io.say(
        f"{game.rounds} rounds, one contract per trade. One trader arrives per round: a noise "
        "trader (trades either side at random) or an informed trader (already sees the next "
        "piece of X). You find out which only at the end."
    )
    while not game.finished:
        number = len(game.records) + 1
        io.say(
            f"\nRound {number}/{game.rounds}. Public: {_known_text(game, game.known())}. "
            f"Max width: {dec(game.max_width())}."
        )
        quote = _ask_quote(game, io)
        if quote is None:
            return False
        record = game.play_round(*quote)
        io.say(
            "  A trader " + _trade_text(record) + "." if record.side != "none" else "  No trade."
        )
    io.say("")
    for line in review_lines(game):
        io.say(line)
    return True
