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

Stages 0, A and B are done; see [STATUS.md](STATUS.md) for the roadmap.

- **Exact toolkit** (`src/ev_lab/prob/`): finite distributions, absorbing Markov chains,
  optimal stopping by backward induction, exact polygon areas, a Monte Carlo checker.
- **Puzzle library** (`src/ev_lab/puzzles/`): classic interview puzzles, each with an exact
  solver, an independent simulator and an explanation. The count and the exact-vs-simulation
  table are in [reports/puzzles/check_all.md](reports/puzzles/check_all.md).
- **Trainer** (`src/ev_lab/trainer/`): timed mental math with adaptive category selection,
  a probability quiz drawn from the puzzle library, and a "make me a market" game against a
  noise trader and an informed trader. Every answer is logged in `practice/`; my progress is
  in `reports/practice/` once I have practised.

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

uv run ev daily                       # the daily 10 minutes: math, one puzzle, one market game
uv run ev stats                       # streak, weakest categories -> reports/practice/
uv run ev math --preset sprint        # 80 questions in 8 minutes
uv run ev market --quantity sum3      # one market game

uv run ev puzzle list                 # what is there, and my status (no answers)
uv run ev puzzle list --tag markov --difficulty 2
uv run ev puzzle try rolls_until_six  # statement -> my answer -> solution
uv run ev puzzle check-all            # exact vs Monte Carlo -> reports/puzzles/check_all.md
```

`ev puzzle try` always asks for an answer first. The check-all report hides the answer of
every puzzle that has not been attempted yet.

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
