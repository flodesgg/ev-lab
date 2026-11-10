# ev-lab: exact answers, checked twice

Nick, November 2026. Every number below is copied from a file produced by this repository's
code; the file is named next to it. Regenerate the files with the commands in the README.

## 1. Purpose

Trading interviews keep testing the same skills: probability and expected-value puzzles,
mental arithmetic under time pressure, quoting a two-sided market, game-theory reasoning and
bet sizing. I wanted three things from one project: a tool that computes such answers
exactly, a trainer that logs every answer I give, and a repository I can explain line by
line. The design rule is that an exact answer is not trusted until a second, independent
method agrees with it.

## 2. What was built

1. **Exact probability toolkit** (`src/ev_lab/prob/`). A finite distribution type with
   `Fraction` probabilities (map, convolution, conditioning, expectation, variance); an
   absorbing Markov chain solver through the fundamental matrix N = (I - Q)^(-1) with exact
   Gauss-Jordan elimination; optimal stopping by backward induction; exact areas of polygons
   for geometric probability; a Monte Carlo checker that returns an estimate with its
   standard error. One function (`prob/exact.py`) refuses floats, so a rounded number cannot
   enter an exact computation.
2. **Puzzle library** (`src/ev_lab/puzzles/`). 29 classic puzzles, each with a statement, an
   exact solver that computes the answer, an independent simulator and an explanation.
3. **Trainer** (`src/ev_lab/trainer/`). Timed mental math in eight categories with adaptive
   selection, a probability quiz, and a market-making game in which a hidden quantity is
   revealed piece by piece while a noise trader and an informed trader hit my quotes.
4. **Cards** (`src/ev_lab/cards/`). A slow, obviously correct hand evaluator (best five of
   seven by trying all 21 subsets), a fast one (bit masks and lookup tables, vectorised),
   Hold'em equity by exact enumeration and by Monte Carlo, a range parser with card removal,
   pot odds.
5. **Game theory** (`src/ev_lab/games/`). Zero-sum matrix games by linear programming,
   regret matching, Kuhn poker with vanilla counterfactual regret minimisation (CFR), best
   response and exploitability, an indifference calculator.
6. **Bet sizing** (`src/ev_lab/kelly/`). Kelly fraction and growth rate, simulation of
   fractional and over-sized Kelly on shared random paths, and the exact expected growth
   when the win probability is only an estimate.

## 3. Limitations

These come before the results on purpose.

- **Same author on both sides of every check.** The solver and the simulator of a puzzle
  are separate code, but both come from my reading of the statement. A misread statement
  passes. Reference values from checked sources ([sources.md](sources.md)) reduce this for
  some results, not for all.
- **A check at 4 standard errors cannot see an error smaller than the standard error.**
- **Toy games.** Kuhn poker has 12 information sets and Leduc hold'em 288. Nothing here
  shows that the methods scale; real games need sampling and abstraction that are not built.
- **Equity is not strategy.** Equity assumes all cards are dealt with no further betting.
- **The Kelly results are for one stylised bet**: known odds, independent outcomes, no
  costs, infinitely divisible wealth. The continuous-time drawdown formula is an
  approximation and is labelled as one. Sizing from an estimate uses a cap of 90% of wealth,
  a modelling choice (decision D-043).
- **No practice data yet.** The trainer is tested with scripted input. At the time of
  writing I have not logged a real session, so this document contains no claim about my own
  speed or accuracy.
- **Offline study only.** Poker is used as a mathematical object. The project has no
  connection to any gambling site and no tool that could assist live play.

## 4. How each part was checked

**Puzzles: exact against Monte Carlo.** For each puzzle the simulator runs 200,000 trials
from its own named random stream; the exact answer must lie within 4 standard errors of the
simulated mean. Result: 29 puzzles checked, 29 agree, largest |z| 3.86
([reports/puzzles/check_all.md](../reports/puzzles/check_all.md)). A z of 3.86 in 29 checks
is unusual, so I did not leave it at "it passed": re-running every simulator on 200
independent seeds gave, for that puzzle, z-scores with mean +0.004 and standard deviation
0.98, which is what an unbiased simulator produces, and flagged none of the 29
([reports/puzzles/bias_check.md](../reports/puzzles/bias_check.md)). The seed was kept
(decision D-046). Beyond simulation, many
answers have a second exact method in the tests: brute force over all permutations for the
hat problem, over all counting orders for the ballot problem, value iteration for the
re-roll game, closed forms for gambler's ruin and the fair-walk duration. Five reference
values were confirmed against a source ([sources.md](sources.md)).

**Trainer.** Each generated arithmetic question is recomputed from its text by a different
route (for example a square as a sum of odd numbers) in a property-based test. The market
game's fair values are compared with brute-force enumeration at every stage, the exact
expected profit of a quote is compared with a simulation of the game engine, and a scripted
game with a fixed seed must reproduce a stored outcome
(`tests/expected/market_playthrough.json`).

**Hand evaluator: oracle and enumeration.** The fast evaluator and the oracle agree on
100,000 random 7-card hands with 0 mismatches
([reports/cards/cards_check.md](../reports/cards/cards_check.md)), and in the slow test set
on a much larger sample and on every 5-card hand. Independently, classifying all
2,598,960 five-card hands and all 133,784,560 seven-card hands gives exactly the known count
in each of the nine categories (same file; source in [sources.md](sources.md)). Hand-written
7-card edge cases cover the wheel, the steel wheel, a straight and a flush that
do not make a straight flush, two sets of trips, and three pairs.

**Equity.** Exact enumeration is compared with an independent slow implementation (plain
`itertools` and the oracle evaluator) on several boards, with hand-counted cases, with
symmetry (two suited ace-kings have exactly equal equity; equities sum to exactly 1), and
with Monte Carlo. Example: AhKh against QsQd before the flop is 197833/428076 = 0.462145
over 1,712,304 boards, and the simulation gives 0.46335 ± 0.00111
([reports/cards/cards_check.md](../reports/cards/cards_check.md)).

**Matrix games.** The linear program runs in floating point; its solution is converted to
fractions and certified in exact arithmetic: the row strategy's guaranteed payoff must equal
the column strategy's. All five test games are certified, including a 2x2 game solved by
hand with value 1/7 ([reports/games/games.md](../reports/games/games.md)).

**Kuhn poker and CFR.** The one-parameter family of equilibria was taken from a checked
source and then proven by the code: for every tested alpha the exact value is -1/18 and the
exact exploitability is 0. CFR after 100,000 iterations has value -0.055554 for the first
player and exploitability 0.000633; the learned strategy has alpha = 0.2200 and is within
0.0030 of the family member with that alpha
([reports/games/games.md](../reports/games/games.md)). Regret matching on two matrix games
ends within 0.0050 and 0.0027 of the linear-programming solution (same file).

**Leduc hold'em and CFR+.** A second, larger game is solved with CFR+ on the public tree.
The fast solver is checked against a slow evaluator that deals the actual cards: both give
-5/64 for two uniformly random players, and they agree on the solver's strategy and on what
each best-response policy earns. After 3,000 iterations CFR+ has exploitability 0.000041;
vanilla CFR on the same game has 0.005333
([reports/games/leduc.md](../reports/games/leduc.md)). No reference game value is asserted
(decision D-058).

**Kelly.** The Kelly fraction is tested as the argmax of the growth rate on a fine grid. For
p = 0.55 at even money it is 1/10, with growth 0.005008 per bet, and -0.000138 per bet at
twice Kelly ([reports/kelly/kelly.md](../reports/kelly/kelly.md)). The simulated mean log
growth agrees with the exact rate within 4 standard errors for every bet size (same file).
The expected growth under an estimated edge is an exact binomial sum and is tested against
sampling.

## 5. Findings

1. **Exactness is cheap and worth it.** All 29 puzzle answers are fractions, and every
   disagreement I met while building was a bug of mine, not noise.
2. **A 7-card evaluator fails in the corners, not in the middle.** Random testing alone
   would rarely hit a steel wheel; the complete category counts and the named edge cases
   are what make the result trustworthy.
3. **Bluffing frequency is an indifference condition.** With pot P and bet B, a caller is
   indifferent when the share of bluffs is B / (P + 2B), and a bluff breaks even when the
   caller calls P / (P + B) of the time. Kuhn poker's equilibrium uses exactly these numbers
   (1/4 and 2/3), which a test verifies in exact arithmetic.
4. **CFR converges roughly like one over the square root of the iterations**, visible as a
   straight line on log-log axes (`reports/games/kuhn_exploitability.png`).
5. **Bet size matters more than edge.** Half Kelly keeps 75% of the growth rate while the
   simulated chance of ever falling to 50% of the starting wealth drops from 47.1% to 12.3%
   ([reports/kelly/kelly.md](../reports/kelly/kelly.md)). The continuous-time formula agrees
   with the simulation for small stakes and overstates the risk for large ones over a finite
   horizon (same file, table "Risk").
6. **An estimated edge is not an edge.** If p = 0.55 is estimated from n past bets and full
   Kelly is staked on the estimate, expected growth is negative for n = 10, 20, 50; half
   Kelly on the estimate is better than full Kelly for n = 10, 20, 50, 100, 200
   ([reports/kelly/kelly.md](../reports/kelly/kelly.md)). This is the same statement as
   paper-lab's: an expectancy whose bootstrap confidence interval includes zero supports a
   position size of zero.

## 6. What I would do next

Log real practice sessions and report my own numbers honestly. Leduc hold'em (with CFR+) and
a C++ port of the evaluator, both listed here earlier, are now built; see the README. Next
would be a sampling variant of CFR (Monte Carlo CFR) on a game too large to traverse fully.

## 7. One line for a CV

> Built an offline probability and game-theory lab in Python (29 interview puzzles solved
> exactly and verified by simulation, a 7-card hand evaluator verified on all 133,784,560
> hands, a CFR solver reaching exploitability 0.000633 on Kuhn poker, Kelly sizing under
> parameter uncertainty), with typed code, property-based tests and reproducible reports.

Numbers and their files: 29 puzzles: `reports/puzzles/check_all.md`. 133,784,560 hands:
`reports/cards/cards_check.md`. Exploitability 0.000633: `reports/games/games.md`.
