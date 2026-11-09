# Sources

Every reference value used in a test is either computed inside the test by an independent
method, or listed here with a source that was actually opened and checked. A value recalled
from memory does not count.

Format: value · where it is used · source · date checked · what exactly was checked.

## Checked sources

All opened and read on 2026-11-09. Each value is also computed by this repo's code
(`tests/test_puzzles.py::test_reference_values_from_the_build_prompt`); the source is a
second, external confirmation.

| value | used in | source | what was checked |
|---|---|---|---|
| Expected rolls of a die until a given face = 6 | `puzzles/rolls_until_six.py` | Wikipedia, "Geometric distribution", https://en.wikipedia.org/wiki/Geometric_distribution | Mean of the number of trials up to the first success is 1/p; the page's own example is a die rolled until a "1", p = 1/6. |
| Coupon collector, E[T] = n H_n; die: 6 (1 + 1/2 + ... + 1/6) = 14.7 | `puzzles/coupon_collector_die.py` | Wikipedia, "Coupon collector's problem", https://en.wikipedia.org/wiki/Coupon_collector%27s_problem | Formula E(T) = n H_n, and the page's worked example E(50) = 224.9603, which the code reproduces (`test_coupon_collector_matches_the_source_example_for_50`). |
| Birthday problem, 23 people: 0.507297 | `puzzles/birthday_23.py` | Wikipedia, "Birthday problem", https://en.wikipedia.org/wiki/Birthday_problem | "P(B) = 1 - 0.492703 = 0.507297", under 365 equally likely, independent birthdays. |
| Monty Hall, switching wins with 2/3 | `puzzles/monty_hall.py` | Wikipedia, "Monty Hall problem", https://en.wikipedia.org/wiki/Monty_Hall_problem | "Under these standard assumptions, the probability of winning the car after switching is 2/3." |
| Expected fixed points of a random permutation = 1; D(n+2) = (n+1)(D(n+1) + D(n)); D(n,k) = C(n,k) D(n-k) | `puzzles/fixed_points_permutation.py` | Wikipedia, "Rencontres numbers", https://en.wikipedia.org/wiki/Rencontres_numbers | Expected value 1 for n >= 1; the derangement recurrence and the formula for k fixed points. The recurrence is also checked by brute force for n <= 6. |

Not taken from a source: the closed forms quoted in puzzle explanations (ballot theorem,
gambler's ruin, a*b duration of a fair walk, gap symmetry). Each is tested against an
independent computation in `tests/test_puzzles.py`.

## To be checked when first used

- Stage C: category counts for all 5-card and all 7-card poker hands.
- Stage D: the value of Kuhn poker and its one-parameter family of equilibria (Kuhn, 1950);
  CFR (Zinkevich, Johanson, Bowling & Piccione, 2007).
- Stage E: Kelly criterion (Kelly, 1956) and the continuous-time drawdown approximations.
