# Puzzle simulators: bias check over independent seeds

## Limitations (read first)

- This detects a systematic gap between solver and simulator. It cannot detect an error they share (a misread statement).
- A gap much smaller than SE / sqrt(200) of one run stays invisible.
- With 29 puzzles and a limit of 4, a false alarm is very unlikely; a real bias of a few percent of one standard error is flagged.

## Result

- 200 independent seeds x 200,000 trials per puzzle.
- Puzzles with |mean z| x sqrt(200) below 4: **29 of 29**.
- Largest: `die_reroll_cost` at +1.98.

## Table

| puzzle | mean z | sd of z | mean z x sqrt(200) | share with abs(z) > 2 | ok |
|---|---|---|---|---|---|
| `die_one_reroll` | +0.118 | 0.97 | +1.67 | 0.035 | yes |
| `market_hidden_integer` | +0.050 | 1.08 | +0.70 | 0.070 | yes |
| `two_dice_six` | +0.016 | 1.06 | +0.22 | 0.045 | yes |
| `tosses_until_hh` | -0.023 | 1.01 | -0.33 | 0.065 | yes |
| `expected_max_three_dice` | -0.058 | 1.03 | -0.81 | 0.040 | yes |
| `expected_max_two_dice` | -0.041 | 0.91 | -0.57 | 0.015 | yes |
| `monty_hall` | -0.029 | 0.95 | -0.41 | 0.035 | yes |
| `rolls_until_six` | -0.023 | 0.94 | -0.33 | 0.030 | yes |
| `three_cards_red_face` | +0.039 | 0.94 | +0.55 | 0.035 | yes |
| `three_dice_sum_ten` | +0.062 | 0.96 | +0.87 | 0.040 | yes |
| `birthday_23` | -0.008 | 0.94 | -0.11 | 0.050 | yes |
| `broken_stick_triangle` | +0.026 | 1.02 | +0.37 | 0.045 | yes |
| `coupon_collector_die` | +0.045 | 1.11 | +0.64 | 0.085 | yes |
| `expected_max_of_draws` | +0.032 | 0.92 | +0.46 | 0.040 | yes |
| `first_ace_position` | -0.097 | 0.99 | -1.37 | 0.050 | yes |
| `fixed_points_permutation` | -0.075 | 0.93 | -1.05 | 0.030 | yes |
| `four_cards_four_suits` | +0.030 | 0.96 | +0.43 | 0.040 | yes |
| `gamblers_ruin_biased` | +0.043 | 1.08 | +0.61 | 0.080 | yes |
| `meeting_window` | +0.003 | 1.03 | +0.05 | 0.040 | yes |
| `monty_hall_four_doors` | -0.115 | 1.05 | -1.62 | 0.070 | yes |
| `random_walk_duration` | +0.004 | 0.98 | +0.05 | 0.040 | yes |
| `rolls_until_two_sixes` | +0.026 | 0.98 | +0.36 | 0.055 | yes |
| `st_petersburg_capped` | +0.101 | 0.98 | +1.43 | 0.045 | yes |
| `two_headed_coin` | -0.114 | 1.02 | -1.62 | 0.055 | yes |
| `ballot_problem` | -0.038 | 1.02 | -0.53 | 0.060 | yes |
| `die_reroll_cost` | +0.140 | 1.01 | +1.98 | 0.045 | yes |
| `penney_game` | -0.072 | 1.01 | -1.01 | 0.070 | yes |
| `red_black_stopping` | -0.028 | 0.95 | -0.40 | 0.035 | yes |
| `rope_loops` | -0.089 | 0.96 | -1.26 | 0.055 | yes |

For unbiased code: mean z near 0, sd near 1, and about 4.6% of runs beyond 2.

---
_run 20261109T215910Z-f656c4 · commit ab81588b3155 (dirty) · config e5861062b213 · seed 20261109_
