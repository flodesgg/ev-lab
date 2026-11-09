# Cards: evaluator and equity checks

## Limitations (read first)

- The fast evaluator is compared with the oracle on a random sample of 7-card hands, not on all of them. The category counts over all hands are a second, complete check, but two errors inside one category that cancel in the count would pass it.
- The oracle and the fast evaluator share the value encoding (category, then tiebreakers). A wrong idea about poker hand ranking would be in both.
- Equity assumes every remaining board is equally likely and all hands go to showdown. It says nothing about betting.
- Offline study only. Nothing here connects to, or assists play on, any site.

## Result

- Overall: **all checks pass**.
- Fast evaluator vs oracle on 100,000 random 7-card hands: 0 mismatches.

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
| one pair | 58,627,800 | 58,627,800 | yes |
| high card | 23,294,460 | 23,294,460 | yes |
| total | 133,784,560 | 133,784,560 | |

## Equity: exact enumeration vs Monte Carlo

Equity of the first hand. `z` = (Monte Carlo - exact) / SE.

| matchup | scenarios | exact | exact (decimal) | Monte Carlo ± SE | z | agree |
|---|---|---|---|---|---|---|
| AhKh vs QsQd, preflop | 1,712,304 | 197833/428076 | 0.462145 | 0.46335 ± 0.00111 | +1.08 | yes |
| AhKh vs QsQd on 2c7d9h | 990 | 28/99 | 0.282828 | 0.28248 ± 0.00101 | -0.35 | yes |
| 9h8h vs AsAd vs KcQc on ThJh2c | 903 | 152/301 | 0.504983 | 0.50472 ± 0.00112 | -0.23 | yes |
| AhKh vs TT+,AQs+ on 2c7d9h | 29,700 | 19301/59400 | 0.324933 | 0.32686 ± 0.00112 | +1.72 | yes |

---
_run 20261109T215402Z-c873b1 · commit 4505a18a9fa7 · config e5861062b213 · seed 20261109_
