# Cards: evaluator and equity checks

## Limitations (read first)

- The fast evaluator is compared with the oracle on a random sample of 7-card hands, not on all of them. The category counts over all hands are a second, complete check, but two errors inside one category that cancel in the count would pass it.
- The oracle and the fast evaluator share the value encoding (category, then tiebreakers). A wrong idea about poker hand ranking would be in both.
- Equity assumes every remaining board is equally likely and all hands go to showdown. It says nothing about betting.
- Offline study only. Nothing here connects to, or assists play on, any site.

## Result

- Overall: **A CHECK FAILED**.
- Fast evaluator vs oracle on 1,000 random 7-card hands: 0 mismatches.

## All 5-card hands by category (exact enumeration)

| category | computed | reference | match |
|---|---|---|---|
| straight flush | 40 | 40 | yes |
| four of a kind | 624 | 624 | yes |
| full house | 3,744 | 3,744 | yes |
| flush | 5,108 | 5,108 | yes |
| straight | 10,200 | 10,200 | yes |
| three of a kind | 54,912 | 54,912 | yes |
| two pair | 123,552 | 123,552 | yes |
| one pair | 1,098,240 | 1,098,240 | yes |
| high card | 1,302,540 | 1,302,540 | yes |
| total | 2,598,960 | 2,598,960 | |

## All 7-card hands by category, best five of seven (exact enumeration)

| category | computed | reference | match |
|---|---|---|---|
| straight flush | 41,584 | 41,584 | yes |
| four of a kind | 224,848 | 224,848 | yes |
| full house | 3,473,184 | 3,473,184 | yes |
| flush | 4,047,644 | 4,047,644 | yes |
| straight | 6,180,020 | 6,180,020 | yes |
| three of a kind | 6,461,620 | 6,461,620 | yes |
| two pair | 31,433,400 | 31,433,400 | yes |
| one pair | 58,627,801 | 58,627,800 | **NO** |
| high card | 23,294,460 | 23,294,460 | yes |
| total | 133,784,561 | 133,784,560 | |

## Equity: exact enumeration vs Monte Carlo

Equity of the first hand. `z` = (Monte Carlo - exact) / SE.

| matchup | scenarios | exact | exact (decimal) | Monte Carlo ± SE | z | agree |
|---|---|---|---|---|---|---|
| A vs B | 44 | 21/22 | 0.954545 | 0.95410 ± 0.00110 | -0.40 | yes |
| C vs D | 990 | 1/2 | 0.500000 | 0.52000 ± 0.00200 | +10.00 | **NO** |

---
_run 20260101T000000Z-abcdef · commit 0123456789ab · config feedfacecafe · seed 7_
