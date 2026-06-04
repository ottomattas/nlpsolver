# tests/

Test files for the llmpipe pipeline.  Each file is a Python literal — a
list of `[id, input, expected]` triples.  The leading `id` is an integer
case number (required, and stable across runs) used by `test.py`,
`runtests.py`, `examine.py`, and `testfixlog_may.txt`.  `input` is the
English text and `expected` is the expected answer.  Run with
`python3 test.py <file>` (single LLM) or `python3 runtests.py <file>`
(all LLMs in parallel) from the parent directory.

These test sets and their recorded multi-LLM results are also published, with
analysis, in the [nlformtasks](https://github.com/tammet/nlformtasks) repository.

## Files

- **`tests_core.py`** — the current main test suite (~1600 cases).
  This is what `python3 test.py` runs by default.

- **`tests_core_100.py`** — a 100-case representative subset of
  `tests_core.py`, for fast smoke runs across all LLMs.

## Running

Two runners drive these files, both from the parent (`llmpipe/`) directory.

### `test.py` — quick single-LLM runs

Best for iterating on one LLM and eyeballing failures.

```bash
# default — tests_core.py
python3 test.py

# explicit file + LLM
python3 test.py tests/tests_core.py -llm claude

# subset
python3 test.py tests/tests_core_100.py -limit 20
python3 test.py tests/tests_core.py -filter "penguin"
```

`test.py` auto-resumes from `test_output.txt` — re-running re-uses previous
results unless `-restart` is passed.  See `python3 test.py -help` for all flags.

### `runtests.py` — full multi-LLM batch runs (recommended)

The batch runner: every case × the requested LLMs, writing one JSON file per
case+LLM under `testresults/<name>/<llm>/case_NNNN.json` (with stage-1/2 JSON,
clauses, prover command and proof) plus a live `summary.json`.  This is how the
recorded results published in [nlformtasks](https://github.com/tammet/nlformtasks)
are produced, and the right tool for a complete pass across all four LLMs.

```bash
# all four LLMs (claude, gpt, gemini, deepseek), full suite
python3 runtests.py tests/tests_core.py

# the 100-case subset, run sequentially (good for cache-served reruns)
python3 runtests.py tests/tests_core_100.py -sequential

# pick LLMs / re-run failures
python3 runtests.py tests/tests_core.py -llms claude,gpt -redo-errors
```

It resumes by skipping cases whose JSON already exists (`-redo` / `-redo-errors`
override).  See DOCUMENTATION.md §10 "Running tests" for the full flag list.
