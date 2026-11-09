# Game theory: matrix games, regret matching, CFR on Kuhn poker

## Limitations (read first)

- Kuhn poker has 12 information sets. Nothing here says how these methods scale; real games need sampling and abstraction, which are not built.
- CFR results are approximations after a finite number of iterations. The exact statements are: the certified LP solutions, and the exact check of the equilibrium family (value and exploitability computed with Fractions).
- Regret matching uses sampled actions, so its averages are random; the seed is fixed.
- Exploitability here is the average of the two best-response gains (NashConv / 2).

## Result

- Overall: **all exact checks pass**.
- Kuhn poker, vanilla CFR, 100,000 iterations: value for player 1 -0.055554 (theory -1/18 = -0.055556), exploitability 0.000633.
- Learned strategy: alpha = P(bet | jack) = 0.2200; largest deviation from the equilibrium with that alpha: 0.0030.

## Zero-sum matrix games by linear programming (exact, certified)

| game | value | row strategy | column strategy | certified |
|---|---|---|---|---|
| rock-paper-scissors | 0 | (1/3, 1/3, 1/3) | (1/3, 1/3, 1/3) | yes |
| biased rock-paper-scissors | 0 | (1/4, 1/2, 1/4) | (1/4, 1/2, 1/4) | yes |
| matching pennies | 0 | (1/2, 1/2) | (1/2, 1/2) | yes |
| hand-solved 2x2 | 1/7 | (3/7, 4/7) | (2/7, 5/7) | yes |
| dominated third row | 1/7 | (3/7, 4/7, 0) | (2/7, 5/7) | yes |

Certified = the row strategy guarantees the value against every column and the column strategy concedes no more against every row, checked in exact arithmetic.

## Regret matching in self-play (simulation)

| game | iterations | average row strategy | average column strategy | max error vs LP |
|---|---|---|---|---|
| rock-paper-scissors | 100,000 | (0.3324, 0.3340, 0.3336) | (0.3361, 0.3283, 0.3356) | 0.0050 |
| biased rock-paper-scissors | 100,000 | (0.2509, 0.4973, 0.2517) | (0.2505, 0.4997, 0.2498) | 0.0027 |

## Kuhn poker: the equilibrium family, checked exactly

| alpha | value for player 1 | exploitability |
|---|---|---|
| 0 | -1/18 | 0 |
| 1/12 | -1/18 | 0 |
| 1/6 | -1/18 | 0 |
| 1/4 | -1/18 | 0 |
| 1/3 | -1/18 | 0 |

## Kuhn poker: CFR convergence (approximation)

Figure: `kuhn_exploitability.png` (log-log).

| iterations | exploitability | value for player 1 |
|---|---|---|
| 1 | 0.333333 | -0.020833 |
| 2 | 0.348958 | -0.071615 |
| 3 | 0.276620 | -0.040887 |
| 6 | 0.126223 | -0.044869 |
| 10 | 0.091144 | -0.035974 |
| 18 | 0.052787 | -0.041932 |
| 32 | 0.052257 | -0.051733 |
| 56 | 0.026254 | -0.050932 |
| 100 | 0.023301 | -0.054715 |
| 178 | 0.017124 | -0.054833 |
| 316 | 0.009699 | -0.054970 |
| 562 | 0.007191 | -0.055045 |
| 1,000 | 0.006505 | -0.055178 |
| 1,778 | 0.006335 | -0.055463 |
| 3,162 | 0.003836 | -0.055531 |
| 5,623 | 0.003579 | -0.055516 |
| 10,000 | 0.001486 | -0.055531 |
| 17,783 | 0.001393 | -0.055541 |
| 31,623 | 0.001198 | -0.055554 |
| 56,234 | 0.000897 | -0.055554 |
| 100,000 | 0.000633 | -0.055554 |

## Kuhn poker: learned strategy vs equilibrium

P(bet or call) at each information set (card + history; p = pass, b = bet).

| information set | learned | equilibrium at learned alpha | difference |
|---|---|---|---|
| `J` | 0.2200 | 0.2200 | +0.0000 |
| `Jpb` | 0.0000 | 0.0000 | +0.0000 |
| `Q` | 0.0000 | 0.0000 | +0.0000 |
| `Qpb` | 0.5553 | 0.5533 | +0.0019 |
| `K` | 0.6630 | 0.6600 | +0.0030 |
| `Kpb` | 1.0000 | 1.0000 | -0.0000 |
| `Jp` | 0.3318 | 0.3333 | -0.0016 |
| `Jb` | 0.0000 | 0.0000 | +0.0000 |
| `Qp` | 0.0000 | 0.0000 | +0.0000 |
| `Qb` | 0.3359 | 0.3333 | +0.0025 |
| `Kp` | 1.0000 | 1.0000 | -0.0000 |
| `Kb` | 1.0000 | 1.0000 | -0.0000 |

---
_run 20261109T214439Z-2f7787 · commit 5bce8fdb5c0b (dirty) · config 370370b721d7 · seed 20261109_
