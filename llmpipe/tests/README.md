# tests/

Test files for the llmpipe pipeline.  Each file is a Python literal — a
list of `[id, input, expected]` triples.  The leading `id` is an integer
case number (required, and stable across runs) used by `test.py`,
`runtests.py`, `examine.py`, and `testfixlog_may.txt`.  `input` is the
English text and `expected` is the expected answer.  Run with
`python3 test.py <file>` (single LLM) or `python3 runtests.py <file>`
(all LLMs in parallel) from the parent directory.

## Files

- **`tests_core.py`** — the current main test suite (~1600 cases).
  This is what `python3 test.py` runs by default.

- **`tests_core_100.py`** — a 100-case representative subset of
  `tests_core.py`, for fast smoke runs across all LLMs.

- **`tests_extra.py`** — extended linguistic regression suite
  (~400 cases): argument structure, passive, coordination, ellipsis,
  relative clauses, modification, comparatives, anaphora, tense,
  appositives, participials, possessives, ditransitives, control verbs.
  Curated from Gemini/GPT suggestions in `suggested_examples.txt`.

- **`tests_medium_core.py`** — a mid-sized subset of `tests_core.py`
  suitable for medium-length regression runs.

- **`tests_small.py`** — three tests; intended for quick
  experimentation and smoke testing of pipeline changes.

## Running

```bash
# default — tests_core.py
python3 test.py

# explicit file + LLM
python3 test.py tests/tests_core.py -llm claude

# subset
python3 test.py tests/tests_extra.py -limit 20
python3 test.py tests/tests_core.py -filter "penguin"
```

`test.py` auto-resumes from `test_output.txt` — re-running re-uses
previous results unless `-restart` is passed.  See `python3 test.py
-help` for all flags.

To run every case across multiple LLMs in parallel (one JSON file per
case+LLM under `testresults/<name>/<llm>/`, with a live `summary.json`),
use `runtests.py` instead — see DOCUMENTATION.md §10 "Running tests".
