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

## Stage B (2026-11-09)

- **D-018 Session randomness.** A practice session draws a fresh seed (written to
  `logs/ev_lab.log`) so that questions differ every day; `--seed N` replays a session
  exactly. Streams inside a session are named (`math`, `quiz`, `market`), see D-012.
- **D-019 Adaptive rule for mental math** (`trainer/adaptive.py`). Per category, over its
  last 50 answers (`trainer.math.adaptive_window`): accuracy = (correct + 1)/(answers + 2);
  slowness = clip(category median seconds / overall median seconds - 1, 0, 1);
  weight = 1 + 2 (1 - accuracy) + slowness, so between 1 and 4. A category is asked with
  probability weight / sum of weights. A never-seen category has weight 2. Every category
  keeps weight >= 1 so nothing drops out of practice.
- **D-020 Timing.** The clock is checked when an answer arrives (terminal input cannot be
  interrupted). An answer that arrives after the deadline is discarded and not logged.
  Enter skips a question (logged as wrong); unreadable input is asked again while the clock
  runs.
- **D-021 Tolerances** (`trainer/mental_math.py`): exact for products, squares, sums and
  percentage -> fraction; division within 0.01 (rounded or truncated to 2 decimals both
  pass); fraction -> percentage within 0.1 points; percentage change within 0.1 (level 1)
  or 0.5 (levels 2-3).
- **D-022 Market game rules** (`trainer/market.py`). One trader per round: informed with
  probability 0.5, otherwise noise. The informed trader sees the next component to be
  revealed and trades one contract only if their fair value is outside my quote. Maximum
  width per round = max(1, round(range of X x 0.20 / 0.12 / 0.08)). The trader's type is
  shown only in the review after the game. Both random numbers of a round are always drawn,
  so the deal and the trader types do not depend on what I quote.
- **D-023 The review shows the exact expected P&L of each quote** (`expected_pnl`), not only
  the realised P&L: the realised number is mostly luck, the expected one judges the quote.
- **D-024 "heads in 10 tosses" is revealed in three groups** (tosses 1-4, 5-7, 8-10) to keep
  every game at 2-3 rounds.
- **D-025 Statistics use UTC days** and are computed from the three append-only logs only.
  Weakest categories are ranked over the last 200 math answers, categories with fewer than 5
  answers in that window are not ranked.
- **D-026 Figures are small multiples** (one panel per category, shared axes, one line each)
  in two files, accuracy and speed, rather than eight lines in one chart or two y-axes.

## Stage C (2026-11-09)

- **D-027 Hand value = category x 13^5 + five base-13 tiebreaker digits.** One integer,
  higher is better, identical in the oracle and the fast evaluator so they can be compared
  with `==`.
- **D-028 Fast evaluator = rank bit masks + 8192-entry tables, vectorised with numpy**
  (`cards/fast.py`). No numba: about a million 7-card hands per second is enough, and the
  code stays readable. It handles 5, 6 and 7 cards with the same code path.
- **D-029 Enumerations use combinations in colex order** (`combinations_array`), where the
  subsets of the first m cards are a prefix. All 7-card hands are produced as "two largest
  cards + a prefix of the 5-subsets", so the 133,784,560 hands never exist in memory at once.
- **D-030 Equity result types.** Exact enumeration returns Fractions (win, tie, equity);
  Monte Carlo returns floats with a standard error. They are different types on purpose.
- **D-031 Ranges are weighted equally per dealable combination.** In exact mode every
  compatible assignment of hands is enumerated; in Monte Carlo hands are drawn uniformly
  from each range and trials where two hands share a card are rejected, which gives the same
  distribution.
- **D-032 `ev equity` picks the method by size:** exact up to `cards.exact_limit` scenarios
  (5,000,000; heads-up preflop is 1,712,304), otherwise Monte Carlo with the fixed seed,
  unless `--exact` or `--mc N` is given.
- **D-033 Pot odds convention:** `pot` includes the bet being faced; `call` is the amount to
  add. EV(call) = equity x pot - (1 - equity) x call, relative to folding = 0.
