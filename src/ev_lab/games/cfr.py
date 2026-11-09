"""Vanilla counterfactual regret minimisation (Zinkevich, Johanson, Bowling & Piccione,
2007) for Kuhn poker.

CFR is regret matching applied at every information set at once. For each information set
and action it accumulates the *counterfactual regret*: how much better the action would
have done than the current strategy, weighted by the probability that the opponent (and
chance) let the game reach this point. The current strategy is proportional to positive
regret; the *average* strategy over all iterations converges to a Nash equilibrium, with
exploitability shrinking roughly like 1 / sqrt(iterations).

"Vanilla" = every iteration walks the whole tree for all six deals (no sampling), and both
players are updated in the same pass.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ev_lab.games import kuhn


@dataclass
class Node:
    regret: list[float] = field(default_factory=lambda: [0.0, 0.0])  # for p, b
    strategy_sum: list[float] = field(default_factory=lambda: [0.0, 0.0])

    def strategy(self) -> list[float]:
        pos = [max(r, 0.0) for r in self.regret]
        total = pos[0] + pos[1]
        return [pos[0] / total, pos[1] / total] if total > 0 else [0.5, 0.5]


@dataclass(frozen=True)
class Checkpoint:
    iteration: int
    exploitability: float
    value: float  # player 1's expected payoff under the average strategies


class KuhnCFR:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {name: Node() for side in kuhn.INFOSETS for name in side}
        self.iterations = 0

    def _walk(self, deal: tuple[int, int], history: str, reach0: float, reach1: float) -> float:
        """Returns the expected payoff for the player to act at `history`."""
        player = kuhn.player_to_act(history)
        if history in kuhn.TERMINAL:
            to_p1 = kuhn.payoff(deal, history)
            return float(to_p1 if player == 0 else -to_p1)
        node = self.nodes[kuhn.infoset(deal, history)]
        strategy = node.strategy()
        utils = [0.0, 0.0]
        for a, action in enumerate(kuhn.ACTIONS):
            if player == 0:
                utils[a] = -self._walk(deal, history + action, reach0 * strategy[a], reach1)
            else:
                utils[a] = -self._walk(deal, history + action, reach0, reach1 * strategy[a])
        node_util = strategy[0] * utils[0] + strategy[1] * utils[1]
        own, other = (reach0, reach1) if player == 0 else (reach1, reach0)
        for a in range(2):
            node.regret[a] += other * (utils[a] - node_util)  # counterfactual: opponent reach
            node.strategy_sum[a] += own * strategy[a]  # average strategy: own reach
        return node_util

    def iterate(self, count: int = 1) -> None:
        for _ in range(count):
            for deal in kuhn.DEALS:
                self._walk(deal, "", 1.0, 1.0)
            self.iterations += 1

    def average_strategy(self) -> dict[str, float]:
        """Infoset -> P(bet), averaged over all iterations (weighted by own reach)."""
        out = {}
        for name, node in self.nodes.items():
            total = node.strategy_sum[0] + node.strategy_sum[1]
            out[name] = node.strategy_sum[1] / total if total > 0 else 0.5
        return out

    def checkpoint(self) -> Checkpoint:
        strategy = kuhn.to_exact(self.average_strategy())
        return Checkpoint(
            self.iterations,
            float(kuhn.exploitability(strategy)),
            float(kuhn.expected_value(strategy)),
        )


def checkpoint_schedule(iterations: int, per_decade: int = 4) -> list[int]:
    """Iteration counts spaced evenly on a log scale, ending exactly at `iterations`."""
    points = {iterations}
    k = 0
    while True:
        value = round(10 ** (k / per_decade))
        if value >= iterations:
            break
        points.add(value)
        k += 1
    return sorted(points)


def run(iterations: int) -> tuple[KuhnCFR, list[Checkpoint]]:
    solver = KuhnCFR()
    checkpoints = []
    for target in checkpoint_schedule(iterations):
        solver.iterate(target - solver.iterations)
        checkpoints.append(solver.checkpoint())
    return solver, checkpoints
