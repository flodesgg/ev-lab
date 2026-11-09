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
