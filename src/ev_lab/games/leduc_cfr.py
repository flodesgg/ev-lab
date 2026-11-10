"""CFR+ (Tammelin, 2014) and exact best response for Leduc hold'em.

Instead of walking the tree once per deal, the solver walks the *public* tree (betting and
the public card) once and carries a vector with one entry per private rank. A terminal
node then needs one small matrix product. This is the standard way to make CFR fast.

CFR+ differs from vanilla CFR in three ways:
  * regrets are never allowed to go below zero (regret matching+);
  * the two players are updated in turn, not together;
  * the average strategy weights iteration t by t, so early, poor strategies fade.
Vanilla CFR is kept as an option to show the difference on the same game.

Chance is folded into weights: M1[i][j] = P(private ranks i, j) and
W[k][i][j] = P(private ranks i, j and public rank k).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from ev_lab.games import leduc

FloatArray = NDArray[np.float64]


def chance_weights() -> tuple[FloatArray, FloatArray]:
    """(M1, W): probabilities of the private ranks, and jointly with the public rank."""
    m1 = np.array([[(2 if i == j else 4) / 30 for j in range(3)] for i in range(3)])
    w = np.zeros((3, 3, 3))
    for k in range(3):
        for i in range(3):
            for j in range(3):
                left = 2 - (i == k) - (j == k)  # cards of rank k still in the deck
                w[k, i, j] = m1[i, j] * left / 4
    return m1, w


@dataclass
class Node:
    r1: str
    public: int | None = None
    r2: str | None = None
    kind: str = "decision"  # "decision", "chance" or "terminal"
    player: int = 0
    actions: str = ""
    children: list[Node] = field(default_factory=list)
    # terminal: chance weight x payoff to player 1, indexed [rank of player 1, rank of 2]
    weighted_payoff: FloatArray = field(default_factory=lambda: np.zeros((3, 3)))
    # decision: one row per private rank of the acting player, one column per action
    regret: FloatArray = field(default_factory=lambda: np.zeros((3, 0)))
    strategy_sum: FloatArray = field(default_factory=lambda: np.zeros((3, 0)))

    def current_strategy(self) -> FloatArray:
        positive = np.maximum(self.regret, 0.0)
        total = positive.sum(axis=1, keepdims=True)
        uniform = np.full_like(positive, 1.0 / positive.shape[1])
        return np.where(total > 0, positive / np.where(total > 0, total, 1.0), uniform)

    def average_strategy(self) -> FloatArray:
        total = self.strategy_sum.sum(axis=1, keepdims=True)
        uniform = np.full_like(self.strategy_sum, 1.0 / self.strategy_sum.shape[1])
        return np.where(total > 0, self.strategy_sum / np.where(total > 0, total, 1.0), uniform)


def _terminal(r1: str, public: int | None, r2: str | None, weight: FloatArray) -> Node:
    pay = np.array(
        [[leduc.payoff(i, j, public, r1, r2) for j in range(3)] for i in range(3)], dtype=float
    )
    return Node(r1, public, r2, kind="terminal", weighted_payoff=weight * pay)


def build_tree() -> Node:
    m1, w = chance_weights()

    def round2(r1: str, public: int, seq: str) -> Node:
        if leduc.round_over(seq):
            return _terminal(r1, public, seq, w[public])
        actions = leduc.legal_actions(seq)
        node = Node(r1, public, seq, player=leduc.player_to_act(seq), actions=actions)
        node.regret = np.zeros((3, len(actions)))
        node.strategy_sum = np.zeros((3, len(actions)))
        node.children = [round2(r1, public, seq + a) for a in actions]
        return node

    def round1(seq: str) -> Node:
        if leduc.round_over(seq):
            if seq.endswith("f"):
                return _terminal(seq, None, None, m1)
            return Node(seq, kind="chance", children=[round2(seq, k, "") for k in range(3)])
        actions = leduc.legal_actions(seq)
        node = Node(seq, player=leduc.player_to_act(seq), actions=actions)
        node.regret = np.zeros((3, len(actions)))
        node.strategy_sum = np.zeros((3, len(actions)))
        node.children = [round1(seq + a) for a in actions]
        return node

    return round1("")


def decision_nodes(root: Node) -> list[Node]:
    out, stack = [], [root]
    while stack:
        node = stack.pop()
        if node.kind == "decision":
            out.append(node)
        stack.extend(node.children)
    return out


Policy = Callable[[Node], FloatArray]


def _terminal_values(node: Node, player: int, reach_opp: FloatArray) -> FloatArray:
    """Counterfactual value of each private rank of `player` at a terminal node."""
    if player == 0:
        return node.weighted_payoff @ reach_opp
    return -(node.weighted_payoff.T @ reach_opp)


def values(
    node: Node, player: int, reach_opp: FloatArray, policy: Policy, best: bool
) -> FloatArray:
    """Counterfactual values for `player` per private rank. The opponent follows `policy`;
    `player` follows it too, or (best=True) picks the best action at every information set."""
    if node.kind == "terminal":
        return _terminal_values(node, player, reach_opp)
    if node.kind == "chance":
        return sum(
            (values(child, player, reach_opp, policy, best) for child in node.children),
            np.zeros(3),
        )
    sigma = policy(node)
    if node.player != player:
        return sum(
            (
                values(child, player, reach_opp * sigma[:, a], policy, best)
                for a, child in enumerate(node.children)
            ),
            np.zeros(3),
        )
    per_action = np.stack(
        [values(child, player, reach_opp, policy, best) for child in node.children], axis=1
    )
    if best:
        return np.asarray(per_action.max(axis=1), dtype=np.float64)
    return np.asarray((sigma * per_action).sum(axis=1), dtype=np.float64)


def best_response_policy(root: Node, player: int, policy: Policy) -> dict[int, FloatArray]:
    """A pure best response of `player` against `policy`, as node id -> one-hot rows."""
    chosen: dict[int, FloatArray] = {}

    def walk(node: Node, reach_opp: FloatArray) -> FloatArray:
        if node.kind == "terminal":
            return _terminal_values(node, player, reach_opp)
        if node.kind == "chance":
            return np.sum([walk(child, reach_opp) for child in node.children], axis=0)
        if node.player != player:
            sigma = policy(node)
            return np.sum(
                [walk(child, reach_opp * sigma[:, a]) for a, child in enumerate(node.children)],
                axis=0,
            )
        per_action = np.stack([walk(child, reach_opp) for child in node.children], axis=1)
        pick = per_action.argmax(axis=1)
        chosen[id(node)] = np.eye(len(node.children))[pick]
        return np.asarray(per_action.max(axis=1), dtype=np.float64)

    walk(root, np.ones(3))
    return chosen


@dataclass(frozen=True)
class Checkpoint:
    iteration: int
    exploitability: float
    value: float  # player 1's expected winnings under the average strategies


class LeducSolver:
    def __init__(self, plus: bool = True) -> None:
        self.plus = plus
        self.root = build_tree()
        self.nodes = decision_nodes(self.root)
        self.iterations = 0

    def _update(
        self, node: Node, player: int, reach_own: FloatArray, reach_opp: FloatArray, weight: float
    ) -> FloatArray:
        if node.kind == "terminal":
            return _terminal_values(node, player, reach_opp)
        if node.kind == "chance":
            return np.sum(
                [self._update(c, player, reach_own, reach_opp, weight) for c in node.children],
                axis=0,
            )
        sigma = node.current_strategy()
        if node.player != player:
            return np.sum(
                [
                    self._update(c, player, reach_own, reach_opp * sigma[:, a], weight)
                    for a, c in enumerate(node.children)
                ],
                axis=0,
            )
        per_action = np.stack(
            [
                self._update(c, player, reach_own * sigma[:, a], reach_opp, weight)
                for a, c in enumerate(node.children)
            ],
            axis=1,
        )
        node_value = (sigma * per_action).sum(axis=1)
        node.regret += per_action - node_value[:, None]
        if self.plus:
            np.maximum(node.regret, 0.0, out=node.regret)
        node.strategy_sum += weight * reach_own[:, None] * sigma
        return np.asarray(node_value, dtype=np.float64)

    def iterate(self, count: int = 1) -> None:
        ones = np.ones(3)
        for _ in range(count):
            self.iterations += 1
            weight = float(self.iterations) if self.plus else 1.0
            for player in (0, 1):
                self._update(self.root, player, ones, ones, weight)

    @staticmethod
    def average(node: Node) -> FloatArray:
        return node.average_strategy()

    def value(self) -> float:
        return float(values(self.root, 0, np.ones(3), self.average, best=False).sum())

    def best_response_value(self, player: int) -> float:
        return float(values(self.root, player, np.ones(3), self.average, best=True).sum())

    def exploitability(self) -> float:
        """(best response of player 1 + best response of player 2) / 2: 0 at equilibrium."""
        return (self.best_response_value(0) + self.best_response_value(1)) / 2

    def checkpoint(self) -> Checkpoint:
        return Checkpoint(self.iterations, self.exploitability(), self.value())

    def strategy_table(self, policy: Policy | None = None) -> dict[str, dict[str, float]]:
        """Infoset -> action -> probability, in the format of `leduc.expected_value`."""
        get = policy or self.average
        out: dict[str, dict[str, float]] = {}
        for node in self.nodes:
            sigma = get(node)
            for rank in range(3):
                key = leduc.infoset_key(rank, node.r1, node.public, node.r2)
                out[key] = {a: float(sigma[rank, i]) for i, a in enumerate(node.actions)}
        return out


def run(iterations: int, plus: bool, schedule: list[int]) -> tuple[LeducSolver, list[Checkpoint]]:
    solver = LeducSolver(plus=plus)
    checkpoints = []
    for target in schedule:
        if target > iterations:
            break
        solver.iterate(target - solver.iterations)
        checkpoints.append(solver.checkpoint())
    return solver, checkpoints
