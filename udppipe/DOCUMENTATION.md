Code Documentation
===================

This document describes the source code organization, module responsibilities,
and data flow in the udppipe natural language reasoning pipeline.

Architecture Overview
---------------------

The pipeline has four main stages:

```
English text
    |
    v
[nlpserver.py] -- Stanza NLP parser (UD parse tree)
    |
    v
[nlptologic.py + modules] -- Semantic parser (UD -> FOL)
    |
    v
[nlpprover.py] -- gk reasoner invocation
    |
    v
[nlpanswer.py] -- Answer extraction & proof verbalization
```

The system runs as two processes:
1. **nlpserver.py** -- a persistent HTTP server that wraps Stanza and manages shared memory
   for gk data files. Must be started first.
2. **nlpsolver.py** -- the command-line driver that sends text to the server, converts the
   UD parse to logic, calls the gk reasoner, and produces the answer.

File Structure
--------------

### Entry Points

| File | Purpose |
|------|---------|
| `nlpsolver.py` | Main CLI entry point. Parses command-line arguments, orchestrates the full pipeline: text preprocessing -> Stanza parse -> UD-to-logic -> prover -> answer. Contains `answer_question()`, the top-level function. |
| `nlpserver.py` | HTTP server wrapping Stanza. Initializes Stanza pipeline, loads gk data files into shared memory, serves UD parses via HTTP on port 8080. |
| `nlptest.py` | Regression test runner. Imports `answer_question` and runs test files configured at the top of the script. |

### Core Pipeline Modules

| File | Purpose | Key Functions |
|------|---------|---------------|
| `nlptologic.py` | Top-level UD-to-logic converter. Iterates over sentences, manages object database, handles question detection. | `parse_ud(doc, entities)` |
| `nlpproperlogic.py` | Core logic builder. Converts UD parse trees into intermediate logic trees (SVO, property trees) and then into FOL formulas. | `build_sentence_proper_logic()` |
| `nlpobjlogic.py` | Object/entity logic. Handles constant creation, object database management, coreference heuristics. | (object management functions) |
| `nlpquestion.py` | Question handling. Detects question sentences, performs "dummification" (replacing "who"/"what" with placeholder names), creates definition predicates. | `is_question_sentence()` |
| `nlpprover.py` | Prover interface. Serializes logic to JSON, writes temp file, calls the gk binary via subprocess, parses JSON output. | `call_prover(logic)` |
| `nlpanswer.py` | Answer construction. Interprets prover JSON output, selects best answers, builds English explanations from proof traces. | `make_nlp_result()` |

### Supporting Modules

| File | Purpose |
|------|---------|
| `nlpglobals.py` | Global configuration: all command-line option flags, constant/variable prefixes, string replacement tables, predicate names. |
| `nlputils.py` | Utility functions: debug printing, list manipulation, logic formatting, JSON serialization. |
| `nlpuncertain.py` | Confidence/uncertainty encoding. Extracts `$conf` annotations from logic, generates `$block` literals for defeasible rules, manages confidence propagation. |
| `nlpsimplify.py` | Logic simplification. Removes redundant clauses, performs subsumption checks on the clause list. |
| `nlprewrite.py` | Text-level rewriting. Applies pattern-matching rules from `replacements.txt` to transform input text before parsing. |
| `nlppronoun.py` | Pronoun resolution. Heuristic-based coreference for pronouns (he, she, it, they) by matching against the object database. |
| `nlppostprocess.py` | Optional post-processing of generated logic (e.g. RDF-style transformations). Activated by `-postprocess` flag. |
| `nlpllm.py` | Optional LLM integration. Experimental support for using LLMs to simplify sentences or assist parsing. |
| `nlpcache.py` | Caching layer. SQLite-based cache (`nlpcache.db`) for Stanza parse results and gk prover outputs. Activated by `-cache` flag. |
| `nlpmakequestions.py` | Utility for generating question variants from input text. |

### Data Files

| File / Directory | Purpose |
|------------------|---------|
| `axioms_std.js` | Default axiom file: small world model with rules for type hierarchy, persistence, spatial reasoning, verb connections, etc. Loaded by gk alongside the problem clauses. |
| `gk_axiomfile.js` | Same as `axioms_std.js` (alternative name used in some configurations). |
| `replacements.txt` | Text rewriting rules applied before parsing. Format: `pattern ==> replacement`. |
| `gk` | The gk reasoner binary (Linux ELF). Based on gkc, extended with confidence and defeasible reasoning. |
| `data/` | Large data files (downloaded separately). WordNet taxonomy, similarity scores, etc. Used by gk via shared memory. |

### Test Files

| File / Directory | Purpose |
|------------------|---------|
| `tests/` | Directory containing test definition files. |
| `tests_core.py` | Core capability tests (within `tests/` or root). |
| `tests_hans.py` | Tests from the HANS dataset (anti-ML inference set). |
| `tests_allen.py` | Tests from the Allen ProofWriter demo. |

### Other Directories

| Directory | Purpose |
|-----------|---------|
| `examples/` | Debug output examples from core tests (run with `-debug -explain`). |
| `paper/` | Draft paper on knowledge representation in the pipeline. |
| `results/` | Test result logs. |

Data Flow in Detail
-------------------

### 1. Text Preprocessing (`nlpsolver.py`, `nlpglobals.py`)

Input text undergoes string replacements defined in `nlpglobals.py`:
- Contractions expanded: "isn't" -> "is not", "can't" -> "can not"
- Pronouns replaced: "somebody" -> "a person", "something" -> "an object"
- Capability phrases normalized: "is able to" -> "can", "is incapable of" -> "can not"

### 2. Stanza Parsing (`nlpserver.py`)

The preprocessed text is sent to the Stanza server, which returns:
- **UD parse tree**: each word annotated with lemma, UPOS tag, dependency relation, features
- **Named entities**: detected persons, locations, etc.

### 3. Sentence Rewriting (`nlprewrite.py`)

Pattern-matching rules from `replacements.txt` are applied to the word list.
The rewritten text is re-parsed by Stanza if changes were made.

### 4. UD-to-Logic Conversion (`nlptologic.py` -> `nlpproperlogic.py`)

For each sentence:

a. **Question detection** (`nlpquestion.py`): if the sentence ends with "?", it is
   identified as a question. Wh-words are replaced with dummy names for uniform parsing.

b. **SVO extraction** (`nlpproperlogic.py`): the UD tree is traversed to extract
   subject-verb-object structure. The root word's UPOS tag and dependency relations
   determine the sentence pattern.

c. **Intermediate tree building**: through stages (subsentence -> object -> property ->
   flat -> flat_props), conjunctions are expanded, adjective modifiers attached, and
   the tree is flattened.

d. **FOL generation**: the flat tree is converted to proper FOL using wrapper predicates
   (`isa`, `prop`, `rel2`, `act1/act2`, `do1/do2`, `can1/can2`). Constants are created
   for named entities and determined nouns. Variables and quantifiers are assigned
   heuristically.

e. **Object database**: detected objects (proper nouns, determined nouns) are recorded with
   their properties for coreference resolution in later sentences.

### 5. Logic Post-processing

a. **Simplification** (`nlpsimplify.py`): removes redundant clauses, merges name atoms.

b. **Uncertainty encoding** (`nlpuncertain.py`): extracts `$conf` annotations, generates
   `$block` literals for defeasible rules, assigns clause-level `@confidence`.
   Defeasible rules (those not strengthened with "all"/"every") get a `$block` guard
   literal that allows stronger exception rules to defeat them -- see ENCODINGS.md
   for the full `$block` mechanism.

c. **Clausification**: formulas are converted to clause normal form (disjunctions of
   literals). Quantifiers are removed (universal variables become free, existential
   variables are Skolemized).

### 6. Prover Invocation (`nlpprover.py`)

The clause list is serialized to JSON and written to a temp file. The GK input format
is based on [JSON-LD Logic](https://github.com/tammet/json-ld-logic), a JSON encoding
of first-order logic clauses. See also:
- [JSON-LD Logic specification and examples](https://logictools.org/json.html)
- Tammet, T. and Sutcliffe, G., 2021. Combining JSON-LD with First Order Logic.
  In *2021 IEEE 15th International Conference on Semantic Computing (ICSC)*
  (pp. 256-261). IEEE.

The gk binary is called with:
```
./gk axioms_std.js -seconds N <tempfile> -defaults -confidence 0.1 -keepconfidence 0.1
```

The prover returns JSON with:
- `result`: "answer found", "no answer", etc.
- `answers[]`: each answer with confidence, proof trace, and blocking literals

### 7. Answer Construction (`nlpanswer.py`)

The prover output is interpreted:
- For yes/no questions: `true`/`false` answers are extracted
- For wh-questions: `$ans(constant)` bindings are collected, generic/skolem answers
  are filtered out when concrete answers exist
- Confidences are compared; the best answers are selected
- If `-explain` is set, proof traces are converted to English step-by-step explanations

Key Configuration (`nlpglobals.py`)
------------------------------------

Important configuration variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `server_port` | 8080 | Port for the Stanza server |
| `prover_fname` | `"../gk/gk"` | Path to the gk binary |
| `prover_axiomfile` | `"axioms_std.js"` | Default axiom file |
| `constant_prefix` | `"c"` | Prefix for generated constants |
| `det_constant_prefix` | `"the_"` | Prefix for determined-noun constants |
| `skolem_constant_prefix` | `"cs"` | Prefix for Skolem constants |
| `definition_prefix` | `"$def"` | Prefix for question definitions |
| `generic_value` | `"$generic"` | Default value for unspecified property parameters |
| `min_prop_intensity` | 1 | Low intensity value |
| `max_prop_intensity` | 3 | High intensity value |

Command-line flags are stored in the `options` dictionary. See `nlpsolver.py -help` or
the README for the full list.

Extending the System
--------------------

### Adding axioms

Add rules to `axioms_std.js` or create a new axiom file and pass it with
`-axioms myfile.js`. Axioms are in JSON-LD-LOGIC clause form.

### Adding text rewrite rules

Add patterns to `replacements.txt` using the format:
```
input pattern ==> output pattern
```

### Adding test cases

Create a Python file with test tuples and add it to the `test_files` list in `nlptest.py`.
Test format: `(input_text, expected_answer)` tuples.
