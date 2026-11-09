# Puzzle library: exact answers vs Monte Carlo

## Limitations (read first)

- A check passes when the exact answer is within 4 standard errors (SE) of the simulated mean. An error smaller than the SE cannot be detected this way.
- The solver and the simulator are written separately, but by the same author from the same reading of the statement. A misread statement passes this check.
- For conditional probabilities the simulator keeps only the trials where the condition happened, so `n` is smaller than the number of trials run.
- False alarms: for a correct answer P(|z| >= 4) is about 6.3e-05 (normal approximation), so with 3 checks about 1 run in 5,262 flags something that is fine. The seed is fixed, so a given commit and config always give the same table.

## Result

- Puzzles checked: **3**; exact and Monte Carlo agree: **2**; disagree: **1**.
- Trials per puzzle: 200,000. Largest |z|: 6.64.
- Exact answers are `fractions.Fraction` (computed, never typed in). Estimates are simulation means with their standard error.

## Table

`z` = (Monte Carlo estimate - exact) / SE.

| puzzle | difficulty | tags | n | z | agree | exact | Monte Carlo ± SE |
|---|---|---|---|---|---|---|---|
| `rolls_until_six` | 1 | expected value, Markov chain | 200,000 | +0.82 | yes | 6 | 6.01000 ± 0.01220 |
| `monty_hall` | 1 | conditional probability | 200,000 | -0.54 | yes | hidden until attempted | hidden until attempted |
| `birthday_23` | 2 | combinatorics | 200,000 | +6.64 | **NO** | 1/2 (~ 0.5) | 0.50730 ± 0.00110 |

---
_run 20260101T000000Z-abcdef · commit 0123456789ab · config feedfacecafe · seed 7_
