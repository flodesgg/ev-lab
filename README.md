# ev-lab

An offline lab for the mathematics that trading interviews test: probability and expected
value, market-making games, game theory and bet sizing.

It has three jobs:

1. **Compute exactly.** Probabilities are `fractions.Fraction`, obtained by enumeration,
   dynamic programming or linear algebra. Every exact answer is checked by an independent
   Monte Carlo simulation with a standard error.
2. **Train daily.** A timed trainer logs every answer, so progress is measured, not felt.
3. **Be explainable.** Every number in this repository comes from a file produced by its code.

## Status

Stage 0 (skeleton) is done. Nothing mathematical is built yet; see [STATUS.md](STATUS.md)
for the current step and the roadmap.

## What this is not

Offline study only. The lab does not connect to poker rooms, casinos, sportsbooks or betting
exchanges, has no bots or real-time assistance, scrapes nothing and needs no credentials.
Poker appears only as a mathematical object (hand evaluation, equity, toy games solved to
equilibrium). `config.yaml` carries `offline_only: true` and the loader refuses any other
value.

## Use

```bash
uv sync               # create the environment from the committed lockfile
make check            # ruff, mypy --strict, pytest (fast set)
make check-all        # the same plus slow exhaustive tests
uv run ev check-config
```

## Layout

```
src/ev_lab/
  config.py  runinfo.py  logging_setup.py  cli.py
  prob/  puzzles/  trainer/  cards/  games/  kelly/  reports/    # filled stage by stage
tests/      one test module per source module
practice/   my practice logs (CSV)
reports/    generated reports and figures
docs/       concepts.md, decisions.md, sources.md
```

## Conventions

- Config is validated by pydantic (`extra="forbid"`, frozen); every generated report carries a
  run id, the git commit, the config hash and the seed.
- Randomness only through `numpy.random.Generator` with explicit seeds.
- Sister project: `paper-lab` (paper-only trading research lab), same engineering conventions.
