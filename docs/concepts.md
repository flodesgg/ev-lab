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
