# Decisions

One line (or a short paragraph) per decision, newest at the bottom. Bugs found in earlier code
are recorded here too, with the test that now catches them.

## Stage 0 (2026-11-09)

- **D-001 Engineering conventions follow `paper-lab`.** Same ruff rule set, mypy strict on
  `src/`, pydantic config with `extra="forbid"` and `frozen=True`, 12-character SHA-256 config
  hash, `RunInfo` with run id and git commit. Written for this project, not copied: the
  trading-specific sections are gone and `RunInfo` carries the seed instead of a data hash.
- **D-002 `offline_only: true` is enforced by the config loader** (same idea as paper-lab's
  `paper_only`). It is a statement of scope that cannot be switched off by editing YAML.
- **D-003 Two hashes.** `config_hash` covers the whole file; `results_hash` covers only the
  sections that change computed numbers (`random`, `monte_carlo`), so moving the logs folder
  does not look like a different experiment. New result-changing sections must be added to
  `RESULT_SECTIONS` in `config.py`.
- **D-004 Logs go to the rotating file only, not to the terminal.** The terminal belongs to the
  trainer; a log line in the middle of a timed drill is noise and could leak an answer.
- **D-005 CLI library: typer** (Nick's choice: default). Less boilerplate than argparse and it
  shares `rich` with the trainer UI.
- **D-006 `make check` excludes `@pytest.mark.slow`** through `addopts = -m 'not slow'`;
  `make check-all` overrides the marker expression. The fast set must stay under a minute.
- **D-007 Choices fixed for later stages** (Nick: "all defaults", 2026-11-09):
  mental-math formats 80-in-8 and 40-in-8 both exist as config presets, with a short 4-minute
  block inside `ev daily`; in the market game the maximum quote width narrows each round;
  the trainer and puzzle statements are in English; the four `practice_pending` puzzles use
  their classic formulations, and the "market on a hidden integer" asks for a bid/ask quote.
- **D-008 Config sections are added in the stage that uses them.** No unused keys in
  `config.yaml`: an unused key is an untested key.

## Stage A (2026-11-09)

- **D-009 One gate for exactness (`prob/exact.py`).** Every probability and payoff entering
  `Dist`, the linear solver, the Markov solver or the stopping solver passes through
  `exact()`, which accepts only `int` and `Fraction`. Floats, numpy scalars and bools raise
  `TypeError`. A float cannot leak into an exact answer silently.
- **D-010 Simulators are vectorised** (`(rng, n) -> array of n samples`) so that 29 puzzles x
  200,000 trials run in about a second. Step-by-step processes use `simtools.run_until`.
- **D-011 Conditional probabilities are simulated by rejection:** the simulator returns values
  only for trials where the condition happened; the SE uses the accepted count.
- **D-012 One random stream per task, named.** `rng_for(seed, name)` seeds from
  `SeedSequence([root seed, crc32(name)])`. Adding or reordering puzzles does not change the
  numbers of the others. (`SeedSequence.spawn` gives order-dependent children, which is why
  the name is hashed in instead.)
- **D-013 Spoiler policy.** (a) `ev puzzle try` asks before it reveals; with no answer it
  aborts and logs nothing. (b) `ev puzzle check-all` prints the exact value and the estimate
  only for puzzles that have an attempt in `practice/puzzle_log.csv`; other rows show only the
  z-score. (c) `assert_agrees` reports only the z-score. (d) No test states the answer of a
  `practice_pending` puzzle. The source code of a solver necessarily contains the method.
- **D-014 Grading.** A numeric answer is correct within 0.5% of the exact value
  (`puzzles.rel_tolerance`), so `14.7` and `147/10` both pass but a rounded `0.5` for
  `0.5073` does not. A market answer is correct when the quote is two-sided, no wider than the
  puzzle allows, and contains the fair value.
- **D-015 Geometric puzzles are exact too:** the favourable region is clipped out of the unit
  square with Fraction coordinates and measured with the shoelace formula, instead of typing
  in a known area.
- **D-016 Puzzle parameters chosen by me** (Nick may change them): gambler's ruin p = 2/5 from
  3 to 6; ballot 6 against 4; hats for 8 people; re-roll cost 0.25 (chosen so that the best
  threshold is unique); St Petersburg capped at 2^10; ropes 10; max of 5 cards from 20.
- **D-017 Practice logs are append-only** (`practice_log.py`): rows are only appended and the
  header is verified on every read and write.
