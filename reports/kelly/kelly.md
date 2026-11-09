# Kelly criterion and bet sizing

## Limitations (read first)

- One repeated binary bet with known odds, independent outcomes, no costs, no limits, and wealth that can be divided without end. Real edges are none of these.
- Three kinds of numbers appear and are labelled: **exact** (formulas and binomial sums), **simulation** (with a standard error) and **approximation** (continuous-time formulas that assume many small bets and an infinite horizon).
- The simulation has a finite horizon (1,000 bets). Events that take long to happen (hitting a drawdown level when betting large) are under-counted relative to the infinite-horizon approximation.
- Mean terminal wealth is dominated by a few lucky paths; the sample mean is far below the exact expectation for the larger bet sizes. The median is the typical outcome.
- With an estimated edge the stake is capped at 90% of wealth. Without a cap, a sample of only wins makes naive Kelly stake everything, and the expected log growth is minus infinity.

## Result

- Bet: win probability p = 0.55, net odds b = 1. Kelly fraction **f\* = 1/10** = 0.1000 (exact). Growth at f\*: 0.005008 per bet; at 2 f\*: -0.000138 per bet (exact; about zero).
- Simulated mean log growth agrees with the exact g(f) within 4 SE for every bet size: **yes**.
- Half Kelly keeps 75% of the growth rate (exact) while the simulated chance of ever falling to 50% of the start drops from 47.1% to 12.3%.
- Sizing full Kelly from an estimate of p has **negative** expected growth for n = 10, 20, 50 past bets (exact).
- Half Kelly on the estimate has higher expected growth than full Kelly on the estimate for n = 10, 20, 50, 100, 200; full Kelly is better for n = 500, 1,000, 2,000, 5,000.

## Bet sizes on the same simulated paths

10,000 paths of 1,000 bets, common random numbers across bet sizes. Start wealth = 1. (z is the same in every row: on shared paths the log growth of every bet size is a linear function of the same number of wins.)

| x Kelly | stake f | g(f) exact | mean log growth, sim ± SE | z | median wealth | mean wealth, sim | mean wealth, exact |
|---|---|---|---|---|---|---|---|
| 0.25 | 0.0250 | +0.002188 | +0.002186 ± 0.000008 | -0.29 | 8.92 | 12.1 | 12.1 |
| 0.5 | 0.0500 | +0.003753 | +0.003748 ± 0.000016 | -0.29 | 42.6 | 142 | 147 |
| 1 | 0.1000 | +0.005008 | +0.004999 ± 0.000032 | -0.29 | 150 | 1.98e+04 | 2.1e+04 |
| 1.5 | 0.1500 | +0.003736 | +0.003722 ± 0.000048 | -0.29 | 41.9 | 2.17e+06 | 2.92e+06 |
| 2 | 0.2000 | -0.000138 | -0.000156 ± 0.000064 | -0.29 | 0.871 | 3.72e+07 | 3.98e+08 |

## Risk: simulation vs continuous-time approximation

Approximation: P(wealth ever falls to x of its start) = x^(2/c - 1) when staking c x Kelly (1 for c >= 2); here x = 0.5.

| x Kelly | P(final < 0.1), sim ± SE | P(ever <= 0.5), sim ± SE | approximation | sim - approx | max drawdown: median / 90% / 99% |
|---|---|---|---|---|---|
| 0.25 | 0.0000 ± 0.0000 | 0.0071 ± 0.0008 | 0.0078 | -0.0007 | 35.8% / 49.1% / 62.7% |
| 0.5 | 0.0000 ± 0.0000 | 0.1234 ± 0.0033 | 0.1250 | -0.0016 | 61.5% / 77.4% / 88.9% |
| 1 | 0.0120 ± 0.0011 | 0.4708 ± 0.0050 | 0.5000 | -0.0292 | 89.4% / 97.4% / 99.6% |
| 1.5 | 0.1112 ± 0.0031 | 0.7481 ± 0.0043 | 0.7937 | -0.0456 | 98.4% / 99.9% / 100.0% |
| 2 | 0.3603 ± 0.0048 | 0.9024 ± 0.0030 | 1.0000 | -0.0976 | 99.9% / 100.0% / 100.0% |

Where they agree: small and moderate bet sizes, where the level is reached early or never. Where they do not: at 1.5 and 2 x Kelly the approximation counts paths that would reach the level after bet 1,000, and it ignores that wealth moves in jumps, not continuously.

## Sizing from an estimated edge (exact binomial sums)

p is estimated from n past bets (p_hat = wins / n) and the stake is Kelly(p_hat) or half of it; the growth is evaluated at the true p.

| n past bets | full Kelly on estimate | half Kelly on estimate | true Kelly | P(estimate shows no edge) | P(stake > 2 x true Kelly) |
|---|---|---|---|---|---|
| 10 | -0.029271 | -0.001158 | +0.005008 | 49.6% | 26.6% |
| 20 | -0.011247 | +0.001293 | +0.005008 | 40.9% | 25.2% |
| 50 | -0.001908 | +0.002601 | +0.005008 | 28.4% | 19.7% |
| 100 | +0.001132 | +0.003018 | +0.005008 | 18.3% | 13.4% |
| 200 | +0.002807 | +0.003276 | +0.005008 | 8.9% | 6.7% |
| 500 | +0.004027 | +0.003516 | +0.005008 | 1.4% | 1.1% |
| 1,000 | +0.004508 | +0.003629 | +0.005008 | 0.1% | 0.1% |
| 2,000 | +0.004758 | +0.003691 | +0.005008 | 0.0% | 0.0% |
| 5,000 | +0.004908 | +0.003728 | +0.005008 | 0.0% | 0.0% |

## What this means for paper-lab

paper-lab reports a setup's expectancy with a bootstrap confidence interval. That interval is the same object as the uncertainty about p above. If the interval includes zero, the data cannot tell a positive edge from none: staking the Kelly fraction of the point estimate is exactly the 'full Kelly on estimate' column at small n, where expected growth is negative. The disciplined size is the Kelly fraction of an edge you can defend, the lower end of the interval, and when that is zero or below, **the Kelly bet is zero**. Until the forward test narrows the interval, the correct position size is none, and after that a fraction of Kelly.

Figures: `growth_curve.png`, `estimated_edge.png`.

---
_run 20261109T215301Z-9c8502 · commit b57f9e7667df · config e5861062b213 · seed 20261109_
