# Leduc hold'em: CFR+ against vanilla CFR

## Limitations (read first)

- Leduc hold'em is still a toy: 6 cards and two betting rounds. It has 24 times the information sets of Kuhn poker (288 against 12), which is not a step towards real poker sizes.
- The strategy is an approximation after a finite number of iterations. No exact equilibrium and no reference game value from a source is used; the evidence is the exploitability, computed by an exact best response.
- The best-response routine and the solver share one tree. The cross-checks below run strategies through a second, slow evaluator that deals actual cards; they confirm values, and that each best response is achievable, not that it is the largest possible.
- Exploitability here is the average of the two best-response gains (NashConv / 2), in chips per hand, with antes of 1.

## Result

- Cross-checks between the fast and the slow evaluator: **all agree** (tolerance 1e-09).
- CFR+ after 100 iterations: exploitability **0.010000**, value for the first player -0.085000.
- Vanilla CFR after 100 iterations: exploitability 0.100000, that is 10 times the CFR+ figure.
- Size: 288 information sets by rank (936 when suits are kept apart), 96 decision nodes in the public tree.

## Cross-checks (fast vector evaluator vs slow card-by-card evaluator)

| quantity | fast | slow | difference |
|---|---|---|---|
| both players uniformly random | -0.078125000000 | -5/64 = -0.078125000000 (exact) | +0.0e+00 |
| CFR+ average strategy | -0.085000000000 | -0.085000000000 | +0.0e+00 |
| best response of player 1 | -0.080000000000 | -0.080000000000 | +0.0e+00 |
| best response of player 2 | +0.100000000000 | +0.100000000000 | +0.0e+00 |

## Convergence

Figure: `leduc_exploitability.png` (log-log).

| iterations | CFR+ exploitability | vanilla CFR exploitability | CFR+ value |
|---|---|---|---|
| 1 | 2.400000 | 2.400000 | -0.080000 |
| 100 | 0.010000 | 0.100000 | -0.085000 |

---
_run 20260101T000000Z-abcdef · commit 0123456789ab · config feedfacecafe · seed 7_
