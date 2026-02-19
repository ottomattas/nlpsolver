# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`llmpipe` is an experimental pipeline for semantic parsing of natural language into first-order predicate logic using LLMs (OpenAI GPT, Claude, Gemini). It is part of the larger `nlpsolver` repository. The parsed logic is evaluated by the `solver/` components and the `gk` binary reasoner.

## Running Scripts

All configuration is hardcoded at the top of each Python script — there are no external config files or CLI flags for model/prompt selection.

```bash
# Collect LLM parsing results for texts in a test file
python3 nlpsimplecollect.py

# Convert raw LLM output into a processed/cleaned format
python3 nlpsimpleconv.py

# Run the full test pipeline on pre-parsed logic triples
python3 nlptest.py --solveparsed

# Validate JSON syntax in a prompt file and show statistics
python3 checkprompt.py

# Compare Stage-1 outputs from three different LLM runs (ignoring whitespace)
python3 comparellmconv.py file1.txt file2.txt file3.txt

# Run nlpsolver directly on a natural language query
python3 solver/nlpsolver.py "Elephants are animals. John is an elephant. Is John an animal?"

# Solver flags: -explain, -debug, -logic, -solveparsed <json_file>
```

## Dependencies

The `gk` binary (logic reasoner) and its data files (`gk_name_number.txt`, `gk_taxonomy_packed.txt`, `axioms_std.js`) must be present in the `llmpipe/` root. Full solver data is available at http://logictools.org/data/nlpsolver_data.tar.gz.

## Architecture

### Two-Stage LLM Pipeline

The primary workflow converts natural language to logic in two stages via LLM calls:

1. **Stage 1** (`prompts/stage1_*.txt`): NL text → Atomic Semantic Units (ASUs) as JSON
2. **Stage 2** (`prompts/stage2_*.txt`): ASUs → first-order predicate logic JSON

`nlpsimplecollect.py` drives this pipeline, iterating over a test data file, calling the configured LLM, and writing results in a custom pipe-separated format:
```
|!!|<INPUT TEXT>|$$|<LLM OUTPUT TEXT>
```

`nlpsimpleconv.py` then parses and cleans those raw results.

`collectmultillmconv.py` is the most recent script (actively modified) and supports orchestrating multiple LLM providers in one run.

### Solver Module (`solver/`)

The `solver/` directory contains a symbolic NLP pipeline invoked by `nlptest.py` and directly via `nlpsolver.py`:

- `nlpsolver.py` — CLI entry point; orchestrates the full pipeline
- `llmcall.py` — LLM API wrapper (Claude/GPT/Gemini) with retries; primary entry point is `call_llm(sysprompt, input_text)`
- `nlptologic.py` — Converts Universal Dependencies (UD) parse trees to logic
- `nlpproperlogic.py` — Builds first-order logic predicates
- `nlpllm.py` — Higher-level LLM solving/parsing logic (uses `llmcall.py` for API calls)
- `nlpprover.py` — Invokes the `gk` binary and handles its output
- `nlpanswer.py` — Extracts and formats the final answer
- `nlpglobals.py` — Global configuration and constants shared across modules

### Test Data

- `tests/llm_core_test.py` — Core logic reasoning test cases
- `tests/tests_hans.py` — Hans benchmark (entailment: subject/object swap, passives, relative clauses)

Both are Python files containing lists of `[text, expected_answer]` pairs. `nlptest.py` reads these and evaluates solver output against expected labels.

### Prompt Files (`prompts/`)

Active prompts follow the naming pattern `logifyprompt<N>_stage<1|2>.txt` or `logifyprompt<N>.txt`. The `prompts/tmparchive/` subdirectory holds historical versions. The currently configured prompt is set by the `syspromptfile` variable at the top of each collection script.

### LLM Provider Configuration

Inside each script, switch providers by changing:
```python
use_llm = "gemini"   # "claude", "gpt", or "gemini"
claudeversion = "claude-sonnet-4-5"
gptversion = "gpt-5.1"
geminiversion = "gemini-3-flash-preview"
temperature = 0
default_max_tokens = 4000
```

API keys are read from environment variables or a local config — check `solver/nlpllm.py` for the exact key names used.
