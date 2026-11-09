# Game theory: matrix games, regret matching, CFR on Kuhn poker

## Limitations (read first)

- Kuhn poker has 12 information sets. Nothing here says how these methods scale; real games need sampling and abstraction, which are not built.
- CFR results are approximations after a finite number of iterations. The exact statements are: the certified LP solutions, and the exact check of the equilibrium family (value and exploitability computed with Fractions).
- Regret matching uses sampled actions, so its averages are random; the seed is fixed.
- Exploitability here is the average of the two best-response gains (NashConv / 2).

## Result

- Overall: **all exact checks pass**.
- Kuhn poker, vanilla CFR, 100 iterations: value for player 1 -0.054000 (theory -1/18 = -0.055556), exploitability 0.020000.
- Learned strategy: alpha = P(bet | jack) = 0.2500; largest deviation from the equilibrium with that alpha: 0.0167.

## Zero-sum matrix games by linear programming (exact, certified)

| game | value | row strategy | column strategy | certified |
|---|---|---|---|---|
| hand-solved 2x2 | 1/7 | (3/7, 4/7) | (2/7, 5/7) | yes |

Certified = the row strategy guarantees the value against every column and the column strategy concedes no more against every row, checked in exact arithmetic.

## Regret matching in self-play (simulation)

| game | iterations | average row strategy | average column strategy | max error vs LP |
|---|---|---|---|---|
| rps | 1,000 | (0.3000, 0.3000, 0.4000) | (0.3300, 0.3300, 0.3400) | 0.0667 |

## Kuhn poker: the equilibrium family, checked exactly

| alpha | value for player 1 | exploitability |
|---|---|---|
| 0 | -1/18 | 0 |
| 1/3 | -1/18 | 0 |

## Kuhn poker: CFR convergence (approximation)

Figure: `kuhn_exploitability.png` (log-log).

| iterations | exploitability | value for player 1 |
|---|---|---|
| 1 | 0.333333 | -0.020000 |
| 100 | 0.020000 | -0.054000 |

## Kuhn poker: learned strategy vs equilibrium

P(bet or call) at each information set (card + history; p = pass, b = bet).

| information set | learned | equilibrium at learned alpha | difference |
|---|---|---|---|
| `J` | 0.2500 | 0.2500 | +0.0000 |
| `Jpb` | 0.0000 | 0.0000 | +0.0000 |
| `Q` | 0.0000 | 0.0000 | +0.0000 |
| `Qpb` | 0.5833 | 0.5833 | +0.0000 |
| `K` | 0.7500 | 0.7500 | +0.0000 |
| `Kpb` | 1.0000 | 1.0000 | +0.0000 |
| `Jp` | 0.3333 | 0.3333 | +0.0000 |
| `Jb` | 0.0000 | 0.0000 | +0.0000 |
| `Qp` | 0.0000 | 0.0000 | +0.0000 |
| `Qb` | 0.3500 | 0.3333 | +0.0167 |
| `Kp` | 1.0000 | 1.0000 | +0.0000 |
| `Kb` | 1.0000 | 1.0000 | +0.0000 |

---
_run 20260101T000000Z-abcdef · commit 0123456789ab · config feedfacecafe · seed 7_
