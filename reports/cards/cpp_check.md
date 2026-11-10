# Cards: the C++ evaluator

## Limitations (read first)

- The C++ code is a port of the numpy evaluator, by the same author, with the same value encoding. It adds a second language and speed, not an independent design.
- Speeds are measured on this machine in one run and will differ elsewhere. The C++ figure times evaluation only; the numpy figure includes numpy's own overheads. Treat the ratio as an order of magnitude.
- Python talks to the C++ program through text on standard input, which is simple and slow; that cost is not part of the speed figure.

## Result

- Overall: **all checks pass**.
- C++ vs Python oracle (all 21 five-card subsets) on 100,000 random 7-card hands: 0 mismatches.
- C++ vs numpy evaluator on 1,000,000 random 7-card hands: 0 mismatches.
- All 133,784,560 seven-card hands enumerated in C++ in 1.4 s.
- Speed (7-card hands per second): C++ 83,797,712, numpy 3,672,413, ratio 23.

## Category counts from C++ (exact enumeration)

| category | 5 cards | reference | 7 cards | reference | match |
|---|---|---|---|---|---|
| straight flush | 40 | 40 | 41,584 | 41,584 | yes |
| four of a kind | 624 | 624 | 224,848 | 224,848 | yes |
| full house | 3,744 | 3,744 | 3,473,184 | 3,473,184 | yes |
| flush | 5,108 | 5,108 | 4,047,644 | 4,047,644 | yes |
| straight | 10,200 | 10,200 | 6,180,020 | 6,180,020 | yes |
| three of a kind | 54,912 | 54,912 | 6,461,620 | 6,461,620 | yes |
| two pair | 123,552 | 123,552 | 31,433,400 | 31,433,400 | yes |
| one pair | 1,098,240 | 1,098,240 | 58,627,800 | 58,627,800 | yes |
| high card | 1,302,540 | 1,302,540 | 23,294,460 | 23,294,460 | yes |

---
_run 20261110T063013Z-06e5c5 · commit 008b4ed9a883 (dirty) · config 0a1d37906cc8 · seed 20261109_
