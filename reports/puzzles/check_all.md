# Puzzle library: exact answers vs Monte Carlo

## Limitations (read first)

- A check passes when the exact answer is within 4 standard errors (SE) of the simulated mean. An error smaller than the SE cannot be detected this way.
- The solver and the simulator are written separately, but by the same author from the same reading of the statement. A misread statement passes this check.
- For conditional probabilities the simulator keeps only the trials where the condition happened, so `n` is smaller than the number of trials run.
- False alarms: for a correct answer P(|z| >= 4) is about 6.3e-05 (normal approximation), so with 29 checks about 1 run in 544 flags something that is fine. The seed is fixed, so a given commit and config always give the same table.

## Result

- Puzzles checked: **29**; exact and Monte Carlo agree: **29**; disagree: **0**.
- Trials per puzzle: 200,000. Largest |z|: 3.86.
- Exact answers are `fractions.Fraction` (computed, never typed in). Estimates are simulation means with their standard error.

## Table

`z` = (Monte Carlo estimate - exact) / SE.

| puzzle | difficulty | tags | n | z | agree | exact | Monte Carlo ± SE |
|---|---|---|---|---|---|---|---|
| `die_one_reroll` | 1 | optimal stopping, expected value | 200,000 | +0.58 | yes | hidden until attempted | hidden until attempted |
| `market_hidden_integer` | 1 | expected value | 200,000 | +1.55 | yes | hidden until attempted | hidden until attempted |
| `two_dice_six` | 1 | conditional probability | 61,104 | -0.17 | yes | hidden until attempted | hidden until attempted |
| `tosses_until_hh` | 2 | Markov chain, expected value | 200,000 | +0.63 | yes | hidden until attempted | hidden until attempted |
| `expected_max_three_dice` | 1 | order statistics, expected value | 200,000 | -2.06 | yes | hidden until attempted | hidden until attempted |
| `expected_max_two_dice` | 1 | order statistics, expected value | 200,000 | -0.39 | yes | hidden until attempted | hidden until attempted |
| `monty_hall` | 1 | conditional probability | 200,000 | -2.03 | yes | hidden until attempted | hidden until attempted |
| `rolls_until_six` | 1 | expected value, Markov chain | 200,000 | +0.88 | yes | hidden until attempted | hidden until attempted |
| `three_cards_red_face` | 1 | conditional probability | 100,233 | +1.32 | yes | hidden until attempted | hidden until attempted |
| `three_dice_sum_ten` | 1 | combinatorics | 200,000 | -1.02 | yes | hidden until attempted | hidden until attempted |
| `birthday_23` | 2 | combinatorics | 200,000 | +1.72 | yes | hidden until attempted | hidden until attempted |
| `broken_stick_triangle` | 2 | geometric probability | 200,000 | -1.05 | yes | hidden until attempted | hidden until attempted |
| `coupon_collector_die` | 2 | expected value, Markov chain | 200,000 | -0.98 | yes | hidden until attempted | hidden until attempted |
| `expected_max_of_draws` | 2 | order statistics, combinatorics | 200,000 | -0.27 | yes | hidden until attempted | hidden until attempted |
| `first_ace_position` | 2 | order statistics, combinatorics | 200,000 | -0.63 | yes | hidden until attempted | hidden until attempted |
| `fixed_points_permutation` | 2 | combinatorics, expected value | 200,000 | -0.24 | yes | hidden until attempted | hidden until attempted |
| `four_cards_four_suits` | 2 | combinatorics | 200,000 | +0.37 | yes | hidden until attempted | hidden until attempted |
| `gamblers_ruin_biased` | 2 | Markov chain, martingales | 200,000 | +1.37 | yes | hidden until attempted | hidden until attempted |
| `meeting_window` | 2 | geometric probability | 200,000 | +1.34 | yes | hidden until attempted | hidden until attempted |
| `monty_hall_four_doors` | 2 | conditional probability | 200,000 | -1.32 | yes | hidden until attempted | hidden until attempted |
| `random_walk_duration` | 2 | martingales, Markov chain | 200,000 | +3.86 | yes | hidden until attempted | hidden until attempted |
| `rolls_until_two_sixes` | 2 | Markov chain, expected value | 200,000 | -1.29 | yes | hidden until attempted | hidden until attempted |
| `st_petersburg_capped` | 2 | expected value | 200,000 | -0.85 | yes | hidden until attempted | hidden until attempted |
| `two_headed_coin` | 2 | conditional probability | 8,219 | +0.34 | yes | hidden until attempted | hidden until attempted |
| `ballot_problem` | 3 | combinatorics, martingales | 200,000 | +1.62 | yes | hidden until attempted | hidden until attempted |
| `die_reroll_cost` | 3 | optimal stopping, expected value | 200,000 | -0.55 | yes | hidden until attempted | hidden until attempted |
| `penney_game` | 3 | Markov chain, conditional probability | 200,000 | +1.64 | yes | hidden until attempted | hidden until attempted |
| `red_black_stopping` | 3 | optimal stopping | 200,000 | -0.88 | yes | hidden until attempted | hidden until attempted |
| `rope_loops` | 3 | expected value, combinatorics | 200,000 | +1.23 | yes | hidden until attempted | hidden until attempted |

---
_run 20261109T210751Z-f41f73 · commit 5ac8dfdcfc47 · config 397bd215b8b2 · seed 20261109_
