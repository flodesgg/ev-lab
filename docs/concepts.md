# Concepts

Two to four plain sentences the first time a concept appears in the code. The goal: I can
explain each one in an interview without notes.

## Stage 0

### Reproducibility (seed, config hash, git commit)
A result is reproducible when someone else can run the same code with the same settings and
get the same numbers. Three things pin a run down: the code version (git commit), the settings
(config hash) and the random numbers (seed). Every report this lab generates prints all three,
so a number can always be traced back to what produced it.

### Seeded random number generator
A computer's "random" numbers come from a deterministic formula started from a number called
the seed. The same seed gives the same sequence, which makes a simulation repeatable and a
failing statistical test debuggable. When several independent simulations are needed, each gets
its own stream derived from the root seed (`SeedSequence.spawn`) instead of reusing one.

### Exact arithmetic vs floating point
A float stores a number in binary with limited precision, so `0.1 + 0.2` is not exactly `0.3`.
A `Fraction` stores a numerator and a denominator as integers and never rounds. Probabilities
of finite experiments are ratios of counts, so they can and should be computed exactly; floats
are used only for simulation estimates.

## Stage A

### Conditional probability
P(A given B) is the probability of A once you know B happened: throw away every outcome where
B is false and ask how much of what remains is A. Formula: P(A | B) = P(A and B) / P(B). Most
interview traps are about choosing B correctly ("at least one die is a six" is a bigger event
than "the first die is a six"). In code: `Dist.condition`.

### Bayes' rule in odds form
Posterior odds = prior odds x likelihood ratio. Start with how likely each hypothesis was,
multiply by how much better one hypothesis explains the evidence than the other. It is the
fastest way to do Bayes in your head (see the two-headed coin puzzle).

### Expected value and linearity of expectation
The expected value is the probability-weighted average outcome: what you would earn per game
on average over many games. Linearity: E[X + Y] = E[X] + E[Y] always, even when X and Y depend
on each other. This turns hard counting problems into sums of simple probabilities (hats
returned at random, coupon collector, rope loops).

### Conditional expectation and first-step analysis
E[X | situation] is the expected value given what you know now. First-step analysis writes
the unknown expectation in terms of itself: spend one step, then you are in a new situation
whose expectation is another unknown. That gives a few linear equations (rolls until a six:
E = 1 + (5/6)E).

### Absorbing Markov chain and the fundamental matrix
A Markov chain moves between states with probabilities that depend only on the current state.
A state is absorbing if you never leave it (the game is over). With Q the transition matrix
among the non-absorbing states, N = (I - Q)^(-1) counts the expected number of visits to each
state; the row sums of N are the expected number of steps until the game ends. This is
first-step analysis done once for all states. In code: `prob/markov.py`.

### Optimal stopping and backward induction
An optimal stopping problem asks when to take what you have instead of continuing. Backward
induction solves it from the end: at the last moment there is no choice, so the value is
known; one step earlier you compare "stop now" with the expected value of continuing; repeat
back to the start. The value of continuing is called the continuation value. In code:
`prob/stopping.py`.

### Option value
Being allowed, but not forced, to stop is worth something. In the red/black card game playing
to the end always gives exactly zero, yet the game has a positive value because you can stop
while ahead.

### Monte Carlo and standard error
Monte Carlo estimates a number by simulating the experiment many times and averaging. The
standard error (SE = sample standard deviation / sqrt(n)) is the typical distance between
that average and the truth; four times more trials halve it. This lab accepts an exact answer
when it is within 4 SE of the simulation.

### Martingale
A martingale is a fair game: given everything so far, the expected next value equals the
current value. If you stop a fair game at a (bounded) stopping time, the expected value at
stopping still equals the starting value. That one fact gives gambler's-ruin probabilities
and expected durations without solving equations.

### Order statistics
Sort a sample: the k-th smallest value is the k-th order statistic (the maximum is the last
one). Two tools cover most questions: P(max <= k) = P(every value <= k), and the symmetry
argument that m drawn items split the remaining ones into m + 1 gaps of equal expected size.

### Geometric probability
When points are chosen uniformly from a region, probability = favourable area / total area.
Draw the two random numbers as a point in the unit square and shade where the condition
holds. In code the shaded polygon's area is computed exactly (`prob/geometry.py`).

### Adverse selection (first look)
When you quote a price, the people who trade with you are not random: someone who knows more
trades only when your price is wrong in their favour. A wider quote is the protection. The
market game in Stage B makes this concrete.

## Stage B

### Bid, ask, spread, making a market
A market maker quotes two prices: the bid (where they buy) and the ask (where they sell). The
difference is the spread. If buyers and sellers arrive at random, the market maker earns half
the spread per trade on average. "Make me a market on X" in an interview means: give a bid and
an ask around your estimate of X's fair value, and be ready to trade on either side.

### Fair value as a conditional expectation
The fair value of a contract that pays X is E[X | what is publicly known]. When a new piece of
information arrives the fair value jumps, but before it arrives the expected jump is zero:
fair values over time form a martingale. In the game, compare `fair value` across rounds.

### Adverse selection
A noise trader trades for reasons unrelated to the price; an informed trader trades only when
your quote is wrong given what they know. So conditional on being traded with, your price was
more likely wrong: buyers tend to appear when your ask is too low. The spread must cover this
loss. In the game the "EV of my quote" column is exactly: half-spread earned from noise minus
the loss to the informed trader.

### Why the quote narrows as information arrives
Early on the informed trader's knowledge is worth a lot (one die out of three is hidden from
you but not from them), so a wide quote is needed. As components are revealed publicly, less
can be known that you do not know, and competition forces tighter quotes.

### Speed/accuracy trade-off and adaptive practice
Timed numerical tests reward fast, correct answers and often penalise wrong ones. Practising
what you are already good at feels productive but changes little; the trainer therefore asks
weak and slow categories more often and reports accuracy per category, not only overall.

## Stage C

### Hand evaluator
A function that turns a set of cards into one number such that a better poker hand always has
a larger number. Here the number is "category, then tiebreakers": a pair of kings with an ace
kicker is (pair, K, A, ...). With five cards this is a short case analysis; that simple
version is the *oracle* against which the fast version is tested.

### Why a 7-card evaluator needs care
You must find the best five of seven cards, and the best five is not always the most obvious
pattern. Two sets of trips make a full house (the lower trips act as the pair). Three pairs
make two pair, and the kicker may come from the third pair. A straight and a flush in the same
seven cards are a straight flush only if five suited cards are consecutive. The ace can be
low (A-2-3-4-5), and then the five is the high card. Each of these is an explicit test.

### Oracle testing
When a fast, clever implementation is hard to trust, write a slow one that is obviously right
and demand that both agree on a huge number of inputs. Here: all 21 five-card subsets versus
bit masks and lookup tables, compared on a million random hands and on every 5-card hand.

### Enumeration as a test
There are exactly 2,598,960 five-card hands and 133,784,560 seven-card hands. Classify every
one and compare the number in each category with the known combinatorial counts. If an edge
case were mishandled, some count would be off.

### Equity
Your equity is the share of the pot you win on average if all remaining cards are dealt with
no more betting: P(win) + P(tie) x (your share in a tie). Exactly: enumerate every possible
remaining board. Approximately: sample boards (Monte Carlo) and report a standard error.

### Range and card removal
A range is the set of hands an opponent might hold, e.g. `TT+,AQs+` = pairs tens or better
plus ace-queen and ace-king suited. Card removal (blockers): cards you can see cannot be in
the opponent's hand, so holding an ace makes the opponent's AA combinations drop from 6 to 3.

### Pot odds
The price of a call compared with what you can win. If the pot (including the bet) is P and
the call is C, calling breaks even when your equity is C / (P + C). EV of a call =
equity x P - (1 - equity) x C. It is the same sum as "is this bet worth taking at these odds"
in any trading question.

## Stage D

### Zero-sum game, mixed strategy, value
In a zero-sum game one player's gain is the other's loss. A pure strategy is a single action;
a mixed strategy is a probability distribution over actions (in rock-paper-scissors any pure
strategy loses to its counter, so you must randomise). The minimax theorem says there is a
number, the value of the game, that the row player can guarantee on average and that the
column player can hold them to. It is found by linear programming (`games/matrix.py`).

### Nash equilibrium
A pair of strategies where neither player can gain by changing their own strategy alone. In a
zero-sum game an equilibrium strategy is a "safe" strategy: it guarantees the value whatever
the opponent does. It does not maximise profit against a bad opponent; it cannot be beaten.

### The indifference principle
If I mix between two actions at equilibrium, both must be worth the same to me, otherwise I
would always take the better one. So the *opponent's* frequencies are set to make me
indifferent. Betting P into a pot, with bet B:

- the caller risks B to win P + B. If a fraction f of bets are bluffs, calling earns
  f (P + B) - (1 - f) B. This is zero when **f = B / (P + 2B)**: the bluff share that makes
  the caller indifferent;
- a pure bluff risks B to win P. If the caller calls with probability c, the bluff earns
  (1 - c) P - c B. This is zero when **c = P / (P + B)**: the calling frequency that makes
  bluffing break even.

Kuhn poker (P = 2, B = 1) uses exactly f = 1/4 and c = 2/3; a test checks it.

### Why bluffing at the right frequency is optimal
If I never bluff, the opponent folds whenever I bet and my strong hands earn nothing extra.
If I bluff too often, the opponent calls everything and my bluffs lose. At the indifference
frequency the opponent's best reply gains nothing, and my strong hands get paid. Bluffing is
a way to get value for good hands.

### Information set
In a game with hidden cards a player cannot tell apart situations that differ only in what
they cannot see. All such situations form one information set, and a strategy must do the
same thing in all of them. Kuhn poker has 12: (my card) x (betting so far).

### Regret and regret matching
Regret of an action: how much more I would have earned so far had I always played it. Regret
matching plays each action in proportion to its positive regret. When both players do this
in a zero-sum game, their average strategies approach a Nash equilibrium.

### Counterfactual regret minimisation (CFR)
Regret matching at every information set simultaneously, where each regret is weighted by the
probability that the *opponent and chance* bring the game to that point ("counterfactual":
as if I had tried to get there). The average strategy converges to an equilibrium; the error
shrinks roughly like 1 / sqrt(iterations).

### Best response and exploitability
A best response is the most profitable strategy against a fixed opponent strategy.
Exploitability measures how far a strategy pair is from equilibrium: how much a
best-responding opponent would win above the game value (here averaged over both seats). It is
zero exactly at a Nash equilibrium, so it is the honest progress measure for a solver.
