# Leduc hold'em: CFR+ against vanilla CFR

## Limitations (read first)

- Leduc hold'em is still a toy: 6 cards and two betting rounds. It is about 24 times larger than Kuhn poker in information sets, not a step towards real poker sizes.
- The strategy is an approximation after a finite number of iterations. No exact equilibrium and no reference game value from a source is used; the evidence is the exploitability, computed by an exact best response.
- The best-response routine and the solver share one tree. The cross-checks below run strategies through a second, slow evaluator that deals actual cards; they confirm values, and that each best response is achievable, not that it is the largest possible.
- Exploitability here is the average of the two best-response gains (NashConv / 2), in chips per hand, with antes of 1.

## Result

- Cross-checks between the fast and the slow evaluator: **all agree** (tolerance 1e-09).
- CFR+ after 3,000 iterations: exploitability **0.000041**, value for the first player -0.085605.
- Vanilla CFR after 3,000 iterations: exploitability 0.005333, that is 129 times the CFR+ figure.
- Size: 288 information sets by rank (936 when suits are kept apart), 96 decision nodes in the public tree.

## Cross-checks (fast vector evaluator vs slow card-by-card evaluator)

| quantity | fast | slow | difference |
|---|---|---|---|
| both players uniformly random | -0.078125000000 | -5/64 = -0.078125000000 (exact) | -1.1e-16 |
| CFR+ average strategy | -0.085605119804 | -0.085605119804 | +1.8e-16 |
| best response of player 1 | -0.085575298274 | -0.085575298274 | -6.9e-17 |
| best response of player 2 | +0.085658092683 | +0.085658092683 | +2.8e-17 |

## Convergence

Figure: `leduc_exploitability.png` (log-log).

| iterations | CFR+ exploitability | vanilla CFR exploitability | CFR+ value |
|---|---|---|---|
| 1 | 2.373611 | 2.373611 | -0.078125 |
| 2 | 2.057917 | 2.061319 | -0.192064 |
| 3 | 1.793544 | 1.798807 | +0.122996 |
| 6 | 1.195113 | 1.304663 | -0.560761 |
| 10 | 0.610439 | 0.888579 | -0.355274 |
| 18 | 0.215815 | 0.526512 | -0.151700 |
| 32 | 0.071594 | 0.292555 | -0.093859 |
| 56 | 0.027235 | 0.163048 | -0.086225 |
| 100 | 0.013416 | 0.095716 | -0.084633 |
| 178 | 0.005379 | 0.061500 | -0.085332 |
| 316 | 0.002072 | 0.032959 | -0.085508 |
| 562 | 0.000734 | 0.019029 | -0.085571 |
| 1,000 | 0.000259 | 0.011818 | -0.085594 |
| 1,778 | 0.000098 | 0.007752 | -0.085602 |
| 3,000 | 0.000041 | 0.005333 | -0.085605 |

---
_run 20261110T060000Z-709c0b · commit f94a174f03b2 (dirty) · config 0a1d37906cc8 · seed 20261109_
