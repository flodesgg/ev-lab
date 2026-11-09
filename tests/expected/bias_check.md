# Puzzle simulators: bias check over independent seeds

## Limitations (read first)

- This detects a systematic gap between solver and simulator. It cannot detect an error they share (a misread statement).
- A gap much smaller than SE / sqrt(4) of one run stays invisible.
- With 2 puzzles and a limit of 4, a false alarm is very unlikely; a real bias of a few percent of one standard error is flagged.

## Result

- 4 independent seeds x 1,000 trials per puzzle.
- Puzzles with |mean z| x sqrt(4) below 4: **1 of 2**.
- Largest: `penney_game` at +5.00.

## Table

| puzzle | mean z | sd of z | mean z x sqrt(4) | share with abs(z) > 2 | ok |
|---|---|---|---|---|---|
| `monty_hall` | +0.000 | 0.79 | +0.00 | 0.000 | yes |
| `penney_game` | +2.500 | 0.35 | +5.00 | 0.750 | **NO** |

For unbiased code: mean z near 0, sd near 1, and about 4.6% of runs beyond 2.

---
_run 20260101T000000Z-abcdef · commit 0123456789ab · config feedfacecafe · seed 7_
