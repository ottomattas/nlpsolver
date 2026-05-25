# tests/

Test files for the llmpipe pipeline.  Each file is a Python literal — a
list of `[text, expected_answer]` pairs (with an optional third element
that the runner ignores).  Run with `python3 test.py <file>` from the
parent directory.

## Files

- **`tests_core.py`** — the current main test suite (~1600 cases).
  This is what `python3 test.py` runs by default.

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
