# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`llmpipe` is an experimental pipeline for semantic parsing of natural language into first-order predicate logic using LLMs (OpenAI GPT, Anthropic Claude, Google Gemini). It is part of the larger `nlpsolver` repository. Parsed logic is passed to the `gk` binary theorem prover which returns answers.

## Running the Pipeline

All scripts are run from the `llmpipe/` directory.

```bash
# Run the full pipeline on a natural language query
python3 solver/solve.py "Elephants are animals. John is an elephant. Is John an animal?"

# Run the test suite (default: tests/tests_core.py)
python3 test.py
python3 test.py tests/tests_core.py -llm claude

# Regenerate the logconvert pretty-print check file
python3 run_pretty_check.py > logconvert_check.txt
```

### solve.py flags

```
-llm NAME        LLM provider: gpt, claude, or gemini
-version VER     Model version string, e.g. claude-sonnet-4-6
-debug           Show full pipeline details
-logic           Show parsed logic clauses
-explain         Show English proof explanation
-prover          Show raw prover input/output
-nollmcache      Disable LLM response caching for this run
-cache           Enable GK prover result caching (off by default)
-nosolve         Parse to logic only, do not run the prover
-seconds N       Give the prover N seconds (default 2)
```

## Architecture

### Pipeline (`solver/solve.py` → `english_to_answer()`)

```
English text
  -> llmparse.parse_text()      [Stage 1: English -> ASUs; Stage 2: ASUs -> logic JSON]
  -> logconvert.rawlogic_convert()  [logic JSON -> GK clause list (FOL to CNF)]
  -> prover.call_prover()       [calls gk binary]
  -> procproofs.process_proof() [post-process prover output; currently pass-through]
  -> answer string
```

### Solver Modules (`solver/`)

- `solve.py` — CLI entry point and `english_to_answer(text, options)` function
- `llmparse.py` — two-stage LLM parser; `parse_text(text)` → `(s1_json, s2_json, stats)`
- `llmcall.py` — LLM API wrapper (GPT/Claude/Gemini) with retries and SQLite caching; `call_llm(sysprompt, input_text)`
- `logconvert.py` — converts stage-2 JSON to GK clause list; `rawlogic_convert(logic)` implements full FOL-to-CNF: implies/xor/equivalent elimination, NNF push, Skolemization, distribution, clause extraction
- `procproofs.py` — post-processes prover output (currently a pass-through stub)
- `prover.py` — invokes the `gk` binary subprocess; `call_prover(logic)`
- `cache.py` — SQLite-backed cache for LLM responses and prover results
- `globals.py` — global `options` dict and file paths (uses `os.path` for absolute paths)
- `pretty.py` — JSON pretty-printer; `pp_str/pp_logic/pp_stage1/pp_stage2`; Style B layout with `noquotes` mode
- `utils.py` — two utility functions used by the pipeline: `debug_print`, `clause_list_to_json`

### Logic Representation

Stage-2 LLM output format:
```
["and", ["@id","S1", PACKAGE], ["@id","S2", PACKAGE], ...]
```
where PACKAGE is `["holds",world,F]`, `["question",F]`, `["ask",var,F]`, or `["and",PKG,["@p","Sx",p]]`.

GK clause list format (output of `logconvert`):
```
[{"@name":"sent_S1", "@logic": CLAUSE}, ...]   -- assertion
{"@name":"sent_S1", "@question": FORMULA}       -- query
```
Variables: `"?:X"` prefix. Negation: `"-"` prefix on predicate name.

### Prompt Files (`prompts/`)

```
prompts/stage1_instructions.txt   -- Stage 1 system prompt instructions
prompts/stage1_examples.txt       -- Stage 1 few-shot examples
prompts/stage2_instructions.txt   -- Stage 2 system prompt instructions
prompts/stage2_examples.txt       -- Stage 2 few-shot examples
```

`prompts/tmparchive/` holds historical prompt versions.

### LLM Configuration (`solver/llmcall.py`)

```python
use_llm       = "claude"              # "gpt" | "claude" | "gemini"
claudeversion = "claude-sonnet-4-6"
gptversion    = "gpt-5.1"
geminiversion = "gemini-2.0-flash"
temperature   = 0
default_max_tokens = 4000
```

API keys are read from JSON files at:
- `../gpt/gpt_secrets.js`
- `../gpt/claude_secrets.js`
- `../gpt/gemini_secrets.js`

LLM responses are cached by default in `cache.db` (SQLite), keyed on provider, version, temperature, max_tokens, sysprompt and input. Use `-nollmcache` to disable.

### Dependencies

The `gk` binary and its data files must be present:
```
llmpipe/axioms_std.js
../gk/gk                    (binary)
../gk/gk_name_number.txt
../gk/gk_taxonomy_packed.txt
```
Full solver data: http://logictools.org/data/nlpsolver_data.tar.gz

### Test Data

- `tests/tests_core.py` — list of `[text, expected_answer]` pairs for the core pipeline

### Other Top-Level Scripts

- `nlpsimplecollect.py` — collect LLM parsing results for a test file
- `nlpsimpleconv.py` — parse and clean raw collected results
- `collectmultillmconv.py` — orchestrate multiple LLM providers in one collection run
- `comparellmconv.py` — compare Stage-1 outputs from multiple LLM runs
- `checkprompt.py` — validate JSON in prompt files
- `run_pretty_check.py` — run `rawlogic_convert` on 10 examples and pretty-print results
