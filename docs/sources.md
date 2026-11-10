# Sources

Every reference value used in a test is either computed inside the test by an independent
method, or listed here with a source that was actually opened and checked. A value recalled
from memory does not count.

Format: value · where it is used · source · date checked · what exactly was checked.

## Checked sources

All opened and read on 2026-11-09. Each value is also computed by this repo's code
(`tests/test_puzzles.py::test_reference_values_from_the_specification`); the source is a
second, external confirmation.

| value | used in | source | what was checked |
|---|---|---|---|
| Expected rolls of a die until a given face = 6 | `puzzles/rolls_until_six.py` | Wikipedia, "Geometric distribution", https://en.wikipedia.org/wiki/Geometric_distribution | Mean of the number of trials up to the first success is 1/p; the page's own example is a die rolled until a "1", p = 1/6. |
| Coupon collector, E[T] = n H_n; die: 6 (1 + 1/2 + ... + 1/6) = 14.7 | `puzzles/coupon_collector_die.py` | Wikipedia, "Coupon collector's problem", https://en.wikipedia.org/wiki/Coupon_collector%27s_problem | Formula E(T) = n H_n, and the page's worked example E(50) = 224.9603, which the code reproduces (`test_coupon_collector_matches_the_source_example_for_50`). |
| Birthday problem, 23 people: 0.507297 | `puzzles/birthday_23.py` | Wikipedia, "Birthday problem", https://en.wikipedia.org/wiki/Birthday_problem | "P(B) = 1 - 0.492703 = 0.507297", under 365 equally likely, independent birthdays. |
| Monty Hall, switching wins with 2/3 | `puzzles/monty_hall.py` | Wikipedia, "Monty Hall problem", https://en.wikipedia.org/wiki/Monty_Hall_problem | "Under these standard assumptions, the probability of winning the car after switching is 2/3." |
| Expected fixed points of a random permutation = 1; D(n+2) = (n+1)(D(n+1) + D(n)); D(n,k) = C(n,k) D(n-k) | `puzzles/fixed_points_permutation.py` | Wikipedia, "Rencontres numbers", https://en.wikipedia.org/wiki/Rencontres_numbers | Expected value 1 for n >= 1; the derangement recurrence and the formula for k fixed points. The recurrence is also checked by brute force for n <= 6. |

| Category counts of all 2,598,960 five-card hands and all 133,784,560 seven-card hands | `cards/reference.py`, `tests/test_cards.py` | Wikipedia, "Poker probability", https://en.wikipedia.org/wiki/Poker_probability | Both frequency tables, every row. The page lists royal flushes separately (4 and 4,324); added to the other straight flushes (36 and 37,260) they give 40 and 41,584. The totals match C(52,5) and C(52,7). |

| Kuhn poker: rules, value -1/18 for the first player, the one-parameter equilibrium family | `games/kuhn.py` | Wikipedia, "Kuhn poker", https://en.wikipedia.org/wiki/Kuhn_poker (original: H. W. Kuhn, "Simplified Two-Person Poker", 1950, not opened) | Rules and payouts; player 1: bet the jack with alpha in [0, 1/3], the king with 3 alpha, always check the queen and call with it alpha + 1/3, fold the jack, call the king; player 2: king always bets/calls, queen checks and calls 1/3, jack never calls and bets 1/3; "lose at a rate of -1/18 per hand". The code then proves it: exact value -1/18 and exact exploitability 0 (`tests/test_games.py`). |

| Kelly fraction f* = p - q/b and log growth p ln(1 + b f) + q ln(1 - f) | `kelly/core.py` | Wikipedia, "Kelly criterion", https://en.wikipedia.org/wiki/Kelly_criterion (original: J. L. Kelly, 1956, not opened) | The page gives f* = p/l - q/g and u = p log(1 + f g) + q log(1 - f l) with gain g and loss l; with l = 1 and g = b this is the formula used. Even money: "bets 2p - 1 times their initial wealth". The code checks that f* is the argmax of g on a fine grid. The page does **not** state the "twice Kelly gives zero growth" rule; that is computed here (exact g(2 f*) in the report). |

| Algorithm SM-2: EF starts at 2.5; I(1) = 1, I(2) = 6, I(n) = I(n-1) x EF rounded up; EF' = EF + (0.1 - (5 - q)(0.08 + (5 - q) 0.02)), minimum 1.3; q < 3 restarts the intervals and leaves EF unchanged | `trainer/srs.py` | P. A. Wozniak, "Application of a computer to improve the results obtained in working with the SuperMemo method" (1990), algorithm page https://super-memory.com/english/ol/sm2.htm, checked 2026-11-10 | Every item of the numbered algorithm description: initial E-Factor, the three interval rules and the rounding, the update formula, the floor of 1.3, the meaning of grades 0 to 5, the reset rule for grades below 3. |

| Leduc hold'em rules: 6 cards (two suits of J, Q, K), antes of 1, two rounds, raise amounts 2 and 4, two-bet maximum, one public card; 936 information states | `games/leduc.py` | OpenSpiel, `open_spiel/games/leduc_poker/leduc_poker.h` (header comment and `kNumInfoStates`), https://github.com/google-deepmind/open_spiel, checked 2026-11-10 | Deck, antes, rounds, raise amounts, the two-bet maximum and the constant 936, which `card_level_infoset_count()` reproduces. The header does not state the showdown rule. |
| Leduc hold'em showdown: the player whose card matches the public card wins, otherwise the higher rank | `games/leduc.py` | RLCard documentation, "Games in RLCard", https://rlcard.org/games.html, checked 2026-11-10 (original: Southey et al., "Bayes' Bluff", 2005; the PDF was downloaded but could not be read here) | The showdown rule, and again the deck, the two-bet maximum and raise amounts 2 and 4. |

Not taken from a source: the closed forms quoted in puzzle explanations (ballot theorem,
gambler's ruin, a*b duration of a fair walk, gap symmetry), each tested against an
independent computation in `tests/test_puzzles.py`; and the continuous-time drawdown formula
x^(2/c - 1), which is derived in `kelly/core.py` (geometric Brownian motion) and reported as
an approximation next to the simulation, never as a reference value.

## Cited for the method only (no number is taken from them)

- Zinkevich, Johanson, Bowling & Piccione (2007), "Regret Minimization in Games with
  Incomplete Information": the CFR algorithm. Not opened; the implementation is validated by
  its results (value, exploitability, equilibrium family), not by the paper.
- Hart & Mas-Colell (2000): regret matching. Same remark.
- Tammelin (2014), "Solving Large Imperfect Information Games Using CFR+": the three
  changes that make up CFR+. Not opened; validated by exploitability on Leduc hold'em.
