"""The "make me a market" game: engine and exact fair values (no input/output here).

X is a hidden quantity built from independent components (dice, groups of coin tosses).
Each round I quote a bid and an ask for X, no wider than the round allows. Then one trader
arrives and may trade one contract:

  noise trader     buys at my ask or sells at my bid, 50/50, whatever the price
  informed trader  also sees the next hidden component; buys if X is worth more than my
                   ask given what they know, sells if it is worth less than my bid,
                   otherwise does nothing

After the round one more component becomes public and I requote. At the end X is revealed
and every trade is settled against it: a trader who bought at my ask costs me X - ask.

Losing to the informed trader while earning the spread from the noise trader is adverse
selection in its smallest form.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

import numpy as np

from ev_lab.prob.dist import Dist, fair_die, joint, sum_of

Trader = Literal["noise", "informed"]
Side = Literal["buy", "sell", "none"]  # from the trader's point of view


# Conditional distributions are pure functions of (quantity id, known components).
_GIVEN_CACHE: dict[tuple[str, tuple[int, ...]], Dist[int]] = {}


@dataclass(frozen=True)
class Quantity:
    id: str
    title: str
    components: tuple[Dist[int], ...]
    labels: tuple[str, ...]
    combine: Callable[[tuple[int, ...]], int]

    def given(self, known: Sequence[int]) -> Dist[int]:
        """Distribution of X when the first len(known) components are known."""
        key = (self.id, tuple(known))
        if key not in _GIVEN_CACHE:
            rest = joint(*self.components[len(known) :])
            _GIVEN_CACHE[key] = rest.map(lambda r: self.combine((*known, *r)))
        return _GIVEN_CACHE[key]

    def fair_value(self, known: Sequence[int]) -> Fraction:
        return self.given(known).expect()

    def value_range(self) -> int:
        support = self.given(()).support
        return max(support) - min(support)


def _heads(tosses: int) -> Dist[int]:
    return sum_of(Dist.uniform([0, 1]), tosses)


_DIE = fair_die()

QUANTITIES: dict[str, Quantity] = {
    q.id: q
    for q in (
        Quantity("sum3", "Sum of three dice", (_DIE,) * 3, ("die 1", "die 2", "die 3"), sum),
        Quantity("max2", "Larger of two dice", (_DIE,) * 2, ("die 1", "die 2"), max),
        Quantity(
            "product2",
            "Product of two dice",
            (_DIE,) * 2,
            ("die 1", "die 2"),
            lambda c: c[0] * c[1],
        ),
        Quantity(
            "heads10",
            "Number of heads in 10 coin tosses",
            (_heads(4), _heads(3), _heads(3)),
            ("heads in tosses 1-4", "heads in tosses 5-7", "heads in tosses 8-10"),
            sum,
        ),
        Quantity(
            "range3",
            "Largest minus smallest of three dice",
            (_DIE,) * 3,
            ("die 1", "die 2", "die 3"),
            lambda c: max(c) - min(c),
        ),
    )
}


def expected_pnl(
    quantity: Quantity,
    known: Sequence[int],
    bid: Fraction,
    ask: Fraction,
    informed_prob: Fraction,
) -> Fraction:
    """My exact expected profit from one round's quote, before the trader arrives."""
    # noise: sells to me at the bid or buys from me at the ask, each with probability 1/2
    noise = (ask - bid) / 2
    informed = Fraction(0)
    for component, p in quantity.components[len(known)].items():
        value = quantity.fair_value((*known, component))
        if value > ask:
            informed += p * (ask - value)  # they buy; I sold too cheap
        elif value < bid:
            informed += p * (value - bid)  # they sell; I paid too much
    return (1 - informed_prob) * noise + informed_prob * informed


@dataclass(frozen=True)
class RoundRecord:
    round: int  # 1-based
    known: tuple[int, ...]
    max_width: Fraction
    bid: Fraction
    ask: Fraction
    fair_value: Fraction  # exact, given the public information
    expected_pnl: Fraction  # exact, of this quote
    trader: Trader
    side: Side
    trader_value: Fraction | None  # the informed trader's fair value (None for noise)


def sample(dist: Dist[int], rng: np.random.Generator) -> int:
    outcomes = dist.support
    p = np.array([float(dist[o]) for o in outcomes])
    return outcomes[int(rng.choice(len(outcomes), p=p / p.sum()))]


class MarketGame:
    def __init__(
        self,
        quantity: Quantity,
        rng: np.random.Generator,
        informed_prob: Fraction,
        width_fracs: Sequence[Fraction],
        min_width: int,
    ) -> None:
        self.quantity = quantity
        self._rng = rng
        self.informed_prob = informed_prob
        self._width_fracs = list(width_fracs)
        self._min_width = min_width
        self.hidden: tuple[int, ...] = tuple(sample(c, rng) for c in quantity.components)
        self.x: int = quantity.combine(self.hidden)
        self.records: list[RoundRecord] = []

    @property
    def rounds(self) -> int:
        return len(self.quantity.components)

    @property
    def finished(self) -> bool:
        return len(self.records) == self.rounds

    def known(self) -> tuple[int, ...]:
        """Components that are public in the current round."""
        return self.hidden[: len(self.records)]

    def max_width(self) -> Fraction:
        """Widest quote allowed this round: a share of X's range that narrows each round."""
        r = len(self.records)
        frac = self._width_fracs[min(r, len(self._width_fracs) - 1)]
        return Fraction(max(self._min_width, round(self.quantity.value_range() * frac)))

    def quote_error(self, bid: Fraction, ask: Fraction) -> str | None:
        if bid >= ask:
            return "the bid must be below the ask"
        if ask - bid > self.max_width():
            return f"too wide: at most {self.max_width()} this round"
        return None

    def play_round(self, bid: Fraction, ask: Fraction) -> RoundRecord:
        if self.finished:
            raise RuntimeError("the game is over")
        error = self.quote_error(bid, ask)
        if error is not None:
            raise ValueError(error)
        known = self.known()
        # both numbers are always drawn, so the random stream does not depend on my quotes
        is_informed = self._rng.random() < float(self.informed_prob)
        noise_buys = self._rng.random() < 0.5
        trader_value: Fraction | None = None
        side: Side
        if is_informed:
            trader_value = self.quantity.fair_value(self.hidden[: len(known) + 1])
            side = "buy" if trader_value > ask else "sell" if trader_value < bid else "none"
        else:
            side = "buy" if noise_buys else "sell"
        record = RoundRecord(
            round=len(self.records) + 1,
            known=known,
            max_width=self.max_width(),
            bid=bid,
            ask=ask,
            fair_value=self.quantity.fair_value(known),
            expected_pnl=expected_pnl(self.quantity, known, bid, ask, self.informed_prob),
            trader="informed" if is_informed else "noise",
            side=side,
            trader_value=trader_value,
        )
        self.records.append(record)
        return record

    def pnl(self, record: RoundRecord) -> Fraction:
        """My profit on one round's trade, settled against the revealed X."""
        if record.side == "buy":
            return record.ask - self.x
        if record.side == "sell":
            return self.x - record.bid
        return Fraction(0)

    def total_pnl(self) -> Fraction:
        return sum((self.pnl(r) for r in self.records), Fraction(0))
