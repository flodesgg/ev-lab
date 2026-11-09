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
