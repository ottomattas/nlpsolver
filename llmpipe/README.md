# llmpipe

`llmpipe` is a natural-language question-answering pipeline built on LLMs and a first-order
theorem prover.  It converts English text into predicate logic using a two-stage LLM parser,
then passes the logic to the [`gk`](../gk/) binary prover to produce answers.

## Quick start

```bash
# Run from the llmpipe/ directory
python3 solver/solve.py "Elephants are animals. John is an elephant. Is John an animal?"
# → True.

python3 solver/solve.py "Mary is taller than John. Who is tall?" -explain
# → Mary. (with step-by-step proof)
```

## How it works

```
English text
  → Stage-1 LLM parse   (English → Atomic Semantic Units)
  → Stage-2 LLM parse   (ASUs → first-order logic JSON)
  → logconvert          (FOL JSON → GK clause list, CNF, Skolemisation)
  → gk prover           (theorem prover binary)
  → procproofs          (answer extraction + proof explanation)
  → Answer string
```

The pipeline supports GPT, Claude, and Gemini as the parsing LLM.  LLM responses are cached in
`cache.db` (SQLite) so repeated queries are free.

## Repository layout

```
llmpipe/
├── solver/       Core pipeline modules (solve.py, logconvert.py, llmparse.py, …)
├── prompts/      LLM system prompts for Stage 1 and Stage 2
├── tests/        Test cases ([text, expected_answer] pairs)
└── mkdata/       Synonym/antonym data builder (standalone, own venv)
```

## Running

```bash
# Basic usage
python3 solver/solve.py "TEXT"

# Useful flags
-llm claude|gpt|gemini    LLM provider (default set in llmcall.py)
-version MODEL            Model version string
-debug                    Show full pipeline detail
-logic                    Show parsed logic (prover input)
-explain                  Show step-by-step proof
-nosolve                  Parse to logic only, skip prover
-nollmcache               Disable LLM cache for this run
-seconds N                Prover time limit (default 2)

# Run tests
python3 test.py
python3 test.py tests/tests_core.py -llm claude
```

## Configuration

**LLM provider and model:** edit `solver/llmcall.py`:
```python
use_llm       = "claude"            # "gpt" | "claude" | "gemini"
claudeversion = "claude-sonnet-4-6"
```

**API keys:** JSON files in `../gpt/` (`gpt_secrets.js`, `claude_secrets.js`, `gemini_secrets.js`).

**Required external data** (not in this repo):
```
../gk/gk                    gk prover binary
../gk/gk_name_number.txt    gk data file
../gk/gk_taxonomy_packed.txt
```
Full solver data: http://logictools.org/data/nlpsolver_data.tar.gz

## Documentation

See `DOCUMENTATION.md` for a full developer guide covering:
- All three JSON representations (Stage-1 ASU, Stage-2 logic, GK clause list)
- Every source file with its public API
- Key algorithms: FOL→CNF clausification, defeasible reasoning, context injection,
  gradable property normalisation, wh-question encoding
- How to extend the pipeline (new predicates, new LLM providers, improved prompts)
