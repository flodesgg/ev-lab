# Kelly criterion and bet sizing

## Limitations (read first)

- One repeated binary bet with known odds, independent outcomes, no costs, no limits, and wealth that can be divided without end. Real edges are none of these.
- Three kinds of numbers appear and are labelled: **exact** (formulas and binomial sums), **simulation** (with a standard error) and **approximation** (continuous-time formulas that assume many small bets and an infinite horizon).
- The simulation has a finite horizon (100 bets). Events that take long to happen (hitting a drawdown level when betting large) are under-counted relative to the infinite-horizon approximation.
- Mean terminal wealth is dominated by a few lucky paths; the sample mean is far below the exact expectation for the larger bet sizes. The median is the typical outcome.
- With an estimated edge the stake is capped at 90% of wealth. Without a cap, a sample of only wins makes naive Kelly stake everything, and the expected log growth is minus infinity.

## Result

- Bet: win probability p = 0.55, net odds b = 1. Kelly fraction **f\* = 1/10** = 0.1000 (exact). Growth at f\*: 0.005008 per bet; at 2 f\*: -0.000138 per bet (exact; about zero).
- Simulated mean log growth agrees with the exact g(f) within 4 SE for every bet size: **yes**.
- Half Kelly keeps 75% of the growth rate (exact) while the simulated chance of ever falling to 50% of the start drops from 47.0% to 12.0%.
- Sizing full Kelly from an estimate of p has **negative** expected growth for n = 10 past bets (exact).
- Half Kelly on the estimate has higher expected growth than full Kelly on the estimate for n = 10; full Kelly is better for n = 1,000.

## Bet sizes on the same simulated paths

1,000 paths of 100 bets, common random numbers across bet sizes. Start wealth = 1. (z is the same in every row: on shared paths the log growth of every bet size is a linear function of the same number of wins.)

| x Kelly | stake f | g(f) exact | mean log growth, sim ± SE | z | median wealth | mean wealth, sim | mean wealth, exact |
|---|---|---|---|---|---|---|---|
| 0.5 | 0.0500 | +0.003753 | +0.003800 ± 0.000100 | +0.47 | 12.5 | 20 | 1.65 |
| 1 | 0.1000 | +0.005008 | +0.004900 ± 0.000100 | -1.08 | 12.5 | 20 | 2.7 |

## Risk: simulation vs continuous-time approximation

Approximation: P(wealth ever falls to x of its start) = x^(2/c - 1) when staking c x Kelly (1 for c >= 2); here x = 0.5.

| x Kelly | P(final < 0.1), sim ± SE | P(ever <= 0.5), sim ± SE | approximation | sim - approx | max drawdown: median / 90% / 99% |
|---|---|---|---|---|---|
| 0.5 | 0.0100 ± 0.0030 | 0.1200 ± 0.0100 | 0.1250 | -0.0050 | 50.0% / 70.0% / 90.0% |
| 1 | 0.0100 ± 0.0030 | 0.4700 ± 0.0100 | 0.5000 | -0.0300 | 50.0% / 70.0% / 90.0% |

Where they agree: small and moderate bet sizes, where the level is reached early or never. Where they do not: at 1.5 and 2 x Kelly the approximation counts paths that would reach the level after bet 100, and it ignores that wealth moves in jumps, not continuously.

## Sizing from an estimated edge (exact binomial sums)

p is estimated from n past bets (p_hat = wins / n) and the stake is Kelly(p_hat) or half of it; the growth is evaluated at the true p.

| n past bets | full Kelly on estimate | half Kelly on estimate | true Kelly | P(estimate shows no edge) | P(stake > 2 x true Kelly) |
|---|---|---|---|---|---|
| 10 | -0.030000 | -0.001000 | +0.005000 | 50.0% | 27.0% |
| 1,000 | +0.004500 | +0.003600 | +0.005000 | 0.1% | 0.1% |

## What this means for paper-lab

paper-lab reports a setup's expectancy with a bootstrap confidence interval. That interval is the same object as the uncertainty about p above. If the interval includes zero, the data cannot tell a positive edge from none: staking the Kelly fraction of the point estimate is exactly the 'full Kelly on estimate' column at small n, where expected growth is negative. The disciplined size is the Kelly fraction of an edge you can defend, the lower end of the interval, and when that is zero or below, **the Kelly bet is zero**. Until the forward test narrows the interval, the correct position size is none, and after that a fraction of Kelly.

Figures: `growth_curve.png`, `estimated_edge.png`.

---
_run 20260101T000000Z-abcdef · commit 0123456789ab · config feedfacecafe · seed 7_
