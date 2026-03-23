llmpipe
=======

`llmpipe` is a natural-language question-answering pipeline built on LLMs and a first-order
theorem prover.  It converts English text into predicate logic using a two-stage LLM parser,
then passes the logic to the [`gk`](../gk/) binary prover to produce answers.

Quick start
-----------

```bash
# Run from the llmpipe/ directory
python3 solver/solve.py "Elephants are animals. John is an elephant. Is John an animal?"
# → True.

python3 solver/solve.py "Mary is taller than John. Who is tall?" -explain
# → Mary. (with step-by-step proof)
```

How it works
------------

```
English text
  → Stage-1 LLM parse   (English → Atomic Semantic Units)
  → Stage-2 LLM parse   (ASUs → first-order logic JSON)
  → logconvert          (FOL JSON → GK clause list, CNF, Skolemisation)
  → gk prover           (theorem prover binary)
  → procproofs          (answer extraction + proof explanation)
  → Answer string
```

The pipeline supports GPT, Claude, Gemini, and DeepSeek as the parsing LLM.  LLM responses are
cached in `cache.db` (SQLite) so repeated queries are free.

Repository layout
-----------------

```
llmpipe/
├── solver/       Core pipeline modules (solve.py, logconvert.py, llmparse.py, …)
├── prompts/      LLM system prompts for Stage 1 and Stage 2
├── tests/        Test cases ([text, expected_answer] pairs)
├── mkdata/       Synonym/antonym data builder (standalone, own venv)
├── ask.py        Direct LLM call tool (uses solver/llmcall.py)
└── test.py       Test runner
```

Running
-------

```bash
# Basic usage
python3 solver/solve.py "TEXT"

# Call an LLM directly (no pipeline)
python3 ask.py "What is the capital of France?"
python3 ask.py -llm claude -p prompt.txt "input text"

# Output level (hierarchy: each includes previous levels)
-explain                          Show English proof
-logic                            + simplified text, clauses, logic in proofs
-details                          + stage-1/2 JSON, prover input/output
-debug                            + raw LLM responses, full trace

# Useful flags
-llm claude|gpt|gemini|deepseek   LLM provider (default set in llmcall.py)
-version MODEL                    Model version string
-json                             Show logic as raw JSON instead of traditional syntax
-gkin FILE                        Save GK prover input to FILE
-nosolve                          Parse to logic only, skip prover
-nollmcache                       Disable LLM cache for this run
-seconds N                        Prover time limit (default 2)

# Run tests
python3 test.py
python3 test.py tests/tests_core.py -llm claude
```

Configuration
-------------

**LLM provider and model:** edit `solver/llmcall.py`:
```python
use_llm       = "gemini"            # "gpt" | "claude" | "gemini" | "deepseek"
claudeversion = "claude-sonnet-4-6"
geminiversion = "gemini-2.0-flash"
```

**API keys:** plain-text files in `../secrets/` (`gpt_secrets.txt`, `claude_secrets.txt`, `gemini_secrets.txt`,
`deepseek_secrets.txt`).


Documentation
-------------

See `ENCODINGS.md` for the three data representations (Stage-1, Stage-2, GK input) with examples.

See `DOCUMENTATION.md` for a full developer guide covering:
- Every source file with its public API
- Key algorithms: FOL→CNF clausification, defeasible reasoning, context injection,
  gradable property normalisation, wh-question encoding
- How to extend the pipeline (new predicates, new LLM providers, improved prompts)

See `PROOF_RENDERING.md` for how proofs are rendered as English explanations.

See `DEBUGGING.md` for the debugging workflow, failure taxonomy, and world/tense system.
