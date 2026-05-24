udppipe
========

udppipe is a Stanza/UD-based experimental pipeline for automated reasoning in natural language,
capable of performing both natural language inference (NLI) and question answering.

The pipeline converts English text to extended first-order logic (FOL), solves the
resulting problem with the `gk` reasoner, and optionally converts the proof back to English.
udppipe does not depend on large language models, although it has optional experimental
LLM support (sentence simplification, direct LLM solving, LLM-based parsing to logic).
See the `llmpipe` folder for the purely LLM-based natural language reasoning pipeline.

The pipeline is described in the paper
[An Experimental Pipeline for Automated Reasoning in Natural Language](https://link.springer.com/chapter/10.1007/978-3-031-38499-8_29).

The pipeline contains:
* A semantic parser from English to extended first-order logic.
* A first-order logic commonsense reasoner solving the problem expressed in extended logic.
* A subsystem for converting the proof given by the reasoner to English.

The commonsense reasoner is built on top of
a [high-performance FOL reasoner](https://link.springer.com/chapter/10.1007/978-3-030-29436-6_32),
extended to use [numeric confidences](https://link.springer.com/chapter/10.1007/978-3-030-79876-5_29)
and [defeasible rules](https://link.springer.com/chapter/10.1007/978-3-031-10769-6_18).

The logic produced by the pipeline is encoded in
[JSON-LD Logic](https://github.com/tammet/json-ld-logic)
([specification](https://logictools.org/json.html)), a JSON encoding of first-order
logic clauses.


Further documentation
---------------------

* [ENCODINGS.md](ENCODINGS.md) -- Detailed reference for the logic encoding: predicates
  (`isa`, `prop`, `rel2`, `act1/act2`, etc.), constants, variables, confidence, context
  terms, defeasible reasoning (`$block`), and question encoding.
* [DOCUMENTATION.md](DOCUMENTATION.md) -- Code documentation: file structure, module
  responsibilities, data flow through the pipeline, and configuration reference.
* `paper/` -- Draft paper on representing concepts for automated reasoning.
* `examples/` -- Debug output traces for selected test cases (run with `-debug -explain`).


Installation
------------

The system requires Linux on x86-64 (the bundled `gk` binary is a
statically-linked Linux x86-64 ELF) and Python 3.10+.
The external dependencies are:

* **Stanza** -- the Stanford NLP package https://stanfordnlp.github.io/stanza/
  converting English to a [UD](https://universaldependencies.org/) parse tree.
  Tested with Stanza versions 1.3 through 1.12.
* **transformers** -- required by Stanza 1.10+ for the dependency-parser model.
* **gk** -- the reasoner binary, included in the system.

Install into a venv (recommended — avoids polluting the system Python):

    python3 -m venv ../my-venv
    ../my-venv/bin/pip install -r requirements.txt
    ../my-venv/bin/python3 -c 'import stanza; stanza.download("en")'
    source ../my-venv/bin/activate

The first `import stanza; stanza.download("en")` downloads ~525 MB of model
files into `~/.cache/stanza/`. Once cached, the server starts in a few seconds.

The `gk` reasoner binary along with taxonomy data files is included in the ../gk folder. 
It is based on
[gkc](https://github.com/tammet/gkc)
([paper](https://link.springer.com/chapter/10.1007%2F978-3-030-29436-6_32)),
extended with probabilistic and defeasible reasoning
([confidences](https://link.springer.com/chapter/10.1007/978-3-030-79876-5_29),
[default logic](https://link.springer.com/chapter/10.1007/978-3-031-10769-6_18);
demo page: https://logictools.org/gk/).

Hardware notes:
* A GPU speeds up Stanza significantly.
* The gk reasoner requires at least 3 GB of shared memory.

The subfolders `gui` and `amr` contain experimental code not currently used by the pipeline.


Running nlpsolver
-----------------

### Step 1: Start the server

    source my-venv/bin/activate   # if using venv
    ./nlpserver.py

The server initializes Stanza, loads data files into shared memory, and starts
a local HTTP server (default port 8080). It prints `Server ready.` when ready.

### Step 2: Run queries

    ./nlpsolver.py "Elephants are big. John is an elephant. Who is big?"

Input can be a quoted text, a filename, or both. The text should contain one or more
assumption sentences followed by a question (ending with `?`).

### Command-line options

**Basic options:**

    -explain          give an English explanation/proof of the answer
    -logic            show the generated logic
    -debug            show the full pipeline trace (UD tree, logic steps, prover I/O)
    -cache            cache Stanza and gk results (SQLite database nlpcache.db;
                      delete the file to clear the cache)
    -nosolve          convert to logic and show prover input, but do not run the prover
    -help             show help text

**Simplified logic representation:**

    -simple           turn on all three simplification options below
    -nocontext        omit context information (time, situation) from logic
    -noexceptions     omit exception/blocker information from logic
    -simpleproperties omit property strength and type; implies -noexceptions

**Prover control:**

    -seconds N        proof search time limit in seconds (default: 2)
    -prover           show prover JSON input/output
    -rawresult        output only the raw JSON result from the prover
    -axioms F1 .. FN  use these axiom files instead of axioms_std.js
    -strategy F       use a JSON strategy file instead of the default search strategy
    -printlevel N     prover verbosity (default 10; try 12 for more detail)

**LLM options** (experimental; requires API keys in `../secrets/`):

    -llm <provider>   select LLM provider: gpt, claude, gemini, or deepseek (default: gpt)
    -llmsimplify      simplify complex sentences with an LLM before parsing
    -llmsolve         bypass the logic pipeline; solve directly with the LLM
    -llmparseall      parse input to logic with the LLM, then solve with gk
    -solveparsed      input is already JSON logic; solve directly with gk

The `-llm` option selects which LLM provider to use for any of the LLM modes.
API keys are read from plain-text files in the `../secrets/` directory:
`gpt_secrets.txt`, `claude_secrets.txt`, `gemini_secrets.txt`, `deepseek_secrets.txt`.
Each file should contain only the API key.

Default model versions (configured in `nlpllm.py`):
* GPT: `gpt-5.1`
* Claude: `claude-sonnet-4-6`
* Gemini: `gemini-2.5-flash-lite`
* DeepSeek: `deepseek-chat`

Example: simplify sentences with Claude before parsing:

    ./nlpsolver.py "The big elephant which was old walked slowly to the river. The elephant was thirsty?" -llmsimplify -llm claude

Example: solve directly with Gemini (no logic pipeline):

    ./nlpsolver.py "All cats are animals. Tom is a cat. Tom is an animal?" -llmsolve -llm gemini


Testing and capabilities
------------------------

Run regression tests:

    ./nlptest.py

The test files to run are configured at the top of `nlptest.py`.
Available test files in `tests/`:

* `tests_core.py` -- 1329 core capability tests
* `tests_hans.py` -- subset of the [HANS set](https://arxiv.org/abs/1902.01007)
* `tests_allen.py` -- tests from the [Allen ProofWriter demo](https://proofwriter.apps.allenai.org/)
* `tests_wikipedia.py` -- tests based on Wikipedia-style text

A few test failures are normal: they may depend on time resources, Stanza version
differences, or test harness interpretation of answers.


Knowledge bases
---------------

The default knowledge base is the small `axioms_std.js`.

Larger knowledge bases can be enabled by editing the `axiomfiles` line in `nlpserver.py`:

    axiomfiles=None # "wnet_10k.js cnet_50k.js quasi_50k.js"

These provide experimental knowledge from WordNet, ConceptNet, and Quasimodo
(see [the paper](https://www.scitepress.org/Link.aspx?doi=10.5220/0011532200003335)).


Configuration
-------------

* Pipeline options: `nlpglobals.py` (top of file)
* Server settings (port, data files): `nlpserver.py` (top of file)
* LLM provider/model configuration: `nlpllm.py` (top of file)


Performance
-----------

The system has low performance on most NLI/QA benchmarks oriented towards machine learning.
As an exception, it achieves ca 95% on the anti-ML benchmark
[HANS](https://arxiv.org/abs/1902.01007) (compared to ca 60% for pre-GPT3 LLMs;
random choice gives 50%). The 5% loss is due to incorrect UD parses from Stanza.

The system solves almost all [Allen ProofWriter demo](https://proofwriter.apps.allenai.org/)
examples and handles inference problems that current LLMs struggle with, such as:

* Replacing real-world concepts with nonsense words (e.g. "greezer", "drimm") —
  LLMs lose accuracy while nlpsolver handles them identically to real words.
* Numeric comparisons with large or unusual numbers —
  LLMs may fail while nlpsolver computes exact results.

Runtime for small examples is ca 0.5 seconds on a Linux laptop with GPU
(Stanza ~0.17s, UD-to-logic ~0.04s, prover ~0.3s). Complex examples may
require more prover time, controlled via `-seconds N`.


Examples
--------

Simple query:

    ./nlpsolver.py "Most elephants are big. Young elephants are not big.
          Mike is probably an elephant. John is a young elephant. Who is big?"

Output:

    Likely Mike.

With explanation:

    ./nlpsolver.py "Most elephants are big. Young elephants are not big.
          Mike is probably an elephant. John is a young elephant. Who is big?"
          -explain

Output:

    Answer:
    Likely Mike.

    Explained:

    Likely mike:
    Confidence 76%.
    Sentences used:
    (1) Most elephants are big.
    (2) Mike is probably an elephant.
    (3) Who is big?
    Statements inferred:
    (1) If X is an elephant, then X is big. Confidence 85%. Why: sentence 1.
    (2) Mike is an elephant. Confidence 90%. Why: sentence 2.
    (3) Mike is big. Confidence 76%. Why: statements 1, 2.
    (4) If X is a big Y, then X matches the query. Why: sentence 3.
    (5) Mike matches the query. Confidence 76%. Why: statements 3, 4.
    (6) If X matches the query, then X is an answer. Why: the question.
    (7) Mike is an answer. Confidence 76%. Why: statements 5, 6.

Use `-debug` for the full pipeline trace: UD parse trees, logic conversion steps,
prover input/output in [JSON-LD-LOGIC](https://github.com/tammet/json-ld-logic) format
([paper](https://ieeexplore.ieee.org/abstract/document/9364411)).
See `examples/` for pre-generated debug traces.
