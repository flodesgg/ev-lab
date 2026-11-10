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

## Stage D (2026-11-09)

- **D-034 LP solutions are certified in exact arithmetic.** scipy's `linprog` returns floats;
  they are rationalised (`limit_denominator(10000)`) and then checked with Fractions: the row
  strategy's guarantee must equal the column strategy's guarantee. Equality is a proof of
  optimality (weak duality), so the reported value is exact. `certified=False` would mean the
  rationalisation missed (a game whose solution needs larger denominators).
- **D-035 Regret matching uses sampled actions** with a seeded generator. With expected
  updates from a uniform start, rock-paper-scissors would never move and "converge" trivially.
- **D-036 Kuhn best response by brute force** over the 64 pure strategies of a player:
  obviously correct, and the game is tiny. All evaluation is in Fractions; CFR's float
  strategies are converted exactly (a float is a binary fraction) before evaluation.
- **D-037 Exploitability = (best-response gain of player 1 + of player 2) / 2**, i.e.
  NashConv / 2, in chips per hand.
- **D-038 The equilibrium family is encoded from a checked source and then proven by the
  code:** for nine values of alpha the exact value is -1/18 and the exact exploitability is 0.
  The CFR test then measures the distance of the learned strategy to the family member with
  the learned alpha.
- **D-039 Vanilla CFR with simultaneous updates,** full traversal of the six deals per
  iteration, average strategy weighted by the player's own reach probability.

## Stage E (2026-11-09)

- **D-040 Example bet: p = 0.55 at even money,** so f* = 1/10 exactly and 2 f* = 0.2 stays
  far from staking the whole bankroll. The config refuses a bet without edge and a multiple
  that would stake 100%.
- **D-041 All bet sizes use the same simulated win/loss sequences** (common random numbers).
  Log wealth is computed from cumulative win counts, so one integer array serves every size.
  Consequence: the z-score of "simulated growth vs g(f)" is identical for all sizes.
- **D-042 Three kinds of numbers are labelled in the report:** exact (formulas, binomial
  sums), simulation (with SE), approximation (x^(2/c - 1), derived for geometric Brownian
  motion with an infinite horizon). The mean terminal wealth is shown next to its exact
  expectation to make visible that the sample mean is unreliable for large stakes.
- **D-043 Estimated edge: stake = min(cap, max(0, Kelly(p_hat))) with cap = 0.9.** Without a
  cap, a sample with only wins gives p_hat = 1 and a stake of 100%, whose log growth is minus
  infinity, so the expected growth of naive Kelly on an estimate is minus infinity for every
  n. The cap is a modelling choice; the report says so. The expected growth is an exact
  binomial sum, checked against sampling in a test.
- **D-044 `hit_probability_approx` returns 1 for multiples >= 2** (non-positive drift: the
  level is reached eventually).

## Stage F (2026-11-09)

- **D-045 `git_dirty` ignores `reports/` and `practice/`.** A report used to be stamped
  "(dirty)" merely because an earlier report or a practice log had been written in the same
  working tree. Dirty now means: code, config, tests or docs differ from the commit.
  Test: `tests/test_runinfo.py::test_inside_git_reports_commit_and_dirty_flag`.
- **D-046 A z of 3.86 was investigated, not re-seeded.** `ev puzzle check-all` passes at the
  fixed seed with a largest |z| of 3.86 (`random_walk_duration`), unusually close to the
  limit of 4. Changing the seed until the table looks calm would be adjusting the evidence.
  Instead `ev puzzle bias-check` repeats the comparison on many independent seeds for every
  puzzle: an unbiased simulator gives z-scores with mean 0 and standard deviation 1. Result
  in `reports/puzzles/bias_check.md`: no puzzle is flagged. The seed stays as it is.
- **D-047 Documentation numbers are tested** (`tests/test_docs_numbers.py`): each figure
  quoted in README, the write-up and the interview notes must occur in the report it cites,
  reports must have been generated from committed code, and limitations must precede
  results.
- **D-048 No practice figure in the README yet.** The project specification asks for a figure of my
  practice progress. No real session has been logged, and a figure from synthetic data
  would be a fabricated result, so the README says where the figure will appear instead.

## Stage G (2026-11-10): spaced repetition, chosen by Nick

- **D-049 Stage G = spaced repetition (SM-2) for puzzles** (Nick's choice out of the four
  options in the project specification).
- **D-050 The schedule is recomputed from `practice/puzzle_log.csv` on every use.** There is
  no schedule file, so the schedule cannot drift from the history and the log stays the only
  state. Review days are UTC days.
- **D-051 The grade comes from the attempt, not from self-assessment:** wrong = 1; right
  within 60 s = 5, within 180 s = 4, slower = 3 (`trainer.srs`). SM-2's grades 0 and 2 are
  not used.
- **D-052 Reading of SM-2 where the source leaves room:** the easiness factor is updated
  first and the new value sets the next interval; fractional intervals are rounded up; a
  failed review resets the interval sequence and leaves the easiness factor unchanged (all
  three as in the source text). SM-2's last step (repeat failed items the same day until
  graded 4 or better) is not enforced: a failed puzzle is simply due the next day.
- **D-053 Quiz order:** untried practice problems, then due reviews (most overdue first),
  then new puzzles, then the earliest future review. Before Stage G it was "unseen or
  previously wrong first"; a wrong answer now returns after one day instead of immediately.

## Stage G, second option (2026-11-10): Leduc hold'em with CFR+, chosen by Nick

- **D-054 Rules from two checked sources** (`docs/sources.md`): antes of 1, bets of 2 then 4,
  at most two bets per round, a pair with the public card wins, otherwise the higher card.
- **D-055 Information sets are keyed by rank, not by card** (288 instead of 936). Suits
  never affect a payoff, so merging them loses nothing; the card-level count is computed
  and tested because it is the number the source reports.
- **D-056 Two implementations.** `games/leduc.py` deals the six actual cards and walks the
  tree per deal: slow, plain, exact with Fractions. `games/leduc_cfr.py` walks the public
  tree once with one vector entry per private rank and chance folded into weight matrices.
  The fast one is tested against the slow one: random strategies, the uniform strategy
  (exactly -5/64), the solver's average strategy, and each best-response policy.
- **D-057 CFR+ = regret matching+ (regrets floored at zero), alternating updates, average
  weighted by the iteration number.** Vanilla CFR here also alternates, with a uniform
  average, so the figure isolates the other two changes.
- **D-058 No reference game value is asserted.** I recall a value for Leduc but have not
  found it in a source I could open, so tests check exploitability, agreement between the
  two evaluators and the sign of the value, not a number from memory.
- **D-059 The best response is validated as achievable, not as maximal:** its policy is run
  through the slow evaluator and must earn exactly the claimed value. That it is the largest
  possible rests on the routine being a per-information-set maximum on a tree with perfect
  recall; the report states this limit.

## Stage G, third option (2026-11-10): the evaluator in C++, chosen by Nick

- **D-060 C++ and not Rust:** Apple clang is installed, Rust is not, and installing a
  toolchain is Nick's call. C++17, one header (`cpp/evaluator.hpp`) and a small command-line
  tool (`cpp/main.cpp`), compiled with `-O2 -Wall -Wextra -Wpedantic -Werror`.
- **D-061 Same value encoding as Python,** so C++, numpy and the oracle are compared with
  `==`. The C++ code is a port of the numpy evaluator's logic, not a new design.
- **D-062 Python talks to the binary through text on stdin/stdout** (`cards/cpp.py`). No
  extension module, no build system: the binary is rebuilt on demand when a source file is
  newer. Slow for the bridge, irrelevant for the checks, and it keeps `uv sync` free of a
  compiler requirement.
- **D-063 The tests are skipped, with a stated reason, on a machine without a compiler.**
  They are not silently passed. On this machine they run in the fast set, including the
  enumeration of all 7-card hands (about a second and a half in C++).
- **D-064 Speeds in the report are one measurement on one machine** and are labelled so. The
  C++ number times evaluation only.

## Stage G, fourth option (2026-11-10): a local web page for the trainer, chosen by Nick

- **D-065 Standard library only.** `http.server` plus one self-contained HTML file with
  inline CSS and JavaScript: no web framework, no build step, no file fetched from the
  internet. The server binds to 127.0.0.1, so the page cannot be reached from another
  machine. Start: `uv run ev web`.
- **D-066 The page is a second front end, not a second trainer.** It calls
  `web/app.py::TrainerApp`, which uses the same question generators, adaptive weights,
  puzzle scheduling, market engine, grading functions and append-only logs as the terminal
  commands. A session on the page and one in the terminal land in the same history.
- **D-067 The server's clock is the judge.** The countdown in the browser is a display that
  is re-synchronised on every answer; whether an answer was in time is decided on the
  server, with the same rule as in the terminal (an answer after the deadline is discarded).
- **D-068 No spoilers over the wire.** A correct answer, an explanation or the hidden value
  of a market game is only ever part of the reply to a submitted answer; tests check the
  keys of the earlier replies.
- **D-069 Tested without sockets.** `web/server.py::respond` maps a request to a response as
  a pure function; tests call it and `TrainerApp.handle` directly. The real server and page
  were exercised by hand in a browser against a scratch copy of the logs.
- **D-070 The timed session exists twice:** `math_session.run_math_session` (terminal loop)
  and `math_drill.MathDrill` (step by step, for the page). Same rules, separately tested.
  Merging them would change how the terminal tests count clock reads; left as is.
- **D-071 Bug found while checking the page:** bid and ask fields were shown for ordinary
  puzzles, because a CSS rule (`label { display: grid }`) overrode the `hidden` attribute.
  Fixed with a global `[hidden] { display: none !important; }`. No automated test covers
  rendering (there is no browser in the test suite); recorded here as a known gap.
- **D-072 History rewritten before publication.** Every commit was rewritten so that
  author, committer and the `authors` field of `pyproject.toml` use the GitHub noreply
  address, and working notes that are not part of the project were removed from the
  history. Code is unchanged, but commit ids changed. Reports generated earlier still carry
  the old ids; each maps to a commit with identical code and reports (file by file
  comparison of the trees, `pyproject.toml` and the removed notes excluded):
  e63e0609f008 -> a8e5460, 655617a991f8 -> 60a33ea, 5321ef890a59 -> bb1d591,
  4505a18a9fa7 -> 99c59a1.
