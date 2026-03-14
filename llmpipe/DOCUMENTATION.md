# llmpipe — Developer Documentation

`llmpipe` is a pipeline that converts natural-language text into first-order predicate logic using
LLMs, then hands the logic to the `gk` theorem prover to answer questions.  This document explains
the pipeline end-to-end, describes every source file, and gives a thorough overview of the logic
representation so that a developer or LLM can quickly start extending or modifying the system.

---

## Table of Contents

1. [Quick start](#1-quick-start)
2. [Pipeline overview](#2-pipeline-overview)
3. [Repository layout](#3-repository-layout)
4. [Representation overview](#4-representation-overview)
   - 4.1 [Stage-1 ASU JSON](#41-stage-1-asu-json)
   - 4.2 [Stage-2 logic JSON](#42-stage-2-logic-json)
   - 4.3 [GK clause list](#43-gk-clause-list)
   - 4.4 [The adjectives field](#44-the-adjectives-field)
   - 4.5 [The $ctxt context term](#45-the-ctxt-context-term)
   - 4.6 [Defeasible reasoning and $block](#46-defeasible-reasoning-and-block)
5. [Source files](#5-source-files)
   - 5.1 [solve.py](#51-solvepy)
   - 5.2 [llmparse.py](#52-llmparsepy)
   - 5.3 [llmcall.py](#53-llmcallpy)
   - 5.4 [logconvert.py](#54-logconvertpy)
   - 5.5 [lc_clausify.py](#55-lc_clausifypy)
   - 5.6 [lc_questions.py](#56-lc_questionspy)
   - 5.7 [procproofs.py](#57-procproofspy)
   - 5.8 [proof_render.py](#58-proof_renderpy)
   - 5.9 [proof_explain.py](#59-proof_explainpy)
   - 5.10 [prover.py](#510-proverpy)
   - 5.11 [pretty.py](#511-prettypy)
   - 5.12 [cache.py](#512-cachepy)
   - 5.13 [globals.py](#513-globalspy)
   - 5.14 [utils.py](#514-utilspy)
   - 5.15 [linguistics.py](#515-linguisticspy)
6. [Prompt files](#6-prompt-files)
7. [Key algorithms in logconvert.py and lc_clausify.py](#7-key-algorithms-in-logconvertpy-and-lc_clausifypy)
   - 7.1 [Package extraction](#71-package-extraction)
   - 7.2 [FOL to CNF clausification](#72-fol-to-cnf-clausification)
   - 7.3 [Defeasible expansion](#73-defeasible-expansion)
   - 7.4 [Context injection ($ctxt)](#74-context-injection-ctxt)
   - 7.5 [Gradable property normalisation](#75-gradable-property-normalisation)
   - 7.6 [Population facts](#76-population-facts)
   - 7.7 [Stage-2 rewrites and modifications](#77-stage-2-rewrites-and-modifications)
8. [Configuration and options](#8-configuration-and-options)
9. [The mkdata toolkit](#9-the-mkdata-toolkit)
10. [Extending and modifying the pipeline](#10-extending-and-modifying-the-pipeline)

---

## 1. Quick start

All scripts are run from the `llmpipe/` directory.

```bash
# Answer a question
python3 solver/solve.py "Elephants are animals. John is an elephant. Is John an animal?"

# Show every intermediate representation
python3 solver/solve.py -debug -logic -prover -explain "..."

# Use a specific LLM
python3 solver/solve.py -llm claude -version claude-sonnet-4-6 "..."

# Parse to logic only, do not call the prover
python3 solver/solve.py -nosolve "..."

# Call an LLM directly (no pipeline)
python3 ask.py "What is the capital of France?"
python3 ask.py -llm claude -p prompt.txt -f input.txt

# Run the test suite
python3 test.py
python3 test.py tests/tests_core.py -llm claude
```

---

## 2. Pipeline overview

```
English text
    │
    ▼
llmparse.parse_text()              [solver/llmparse.py]
    │   Stage 1: English → ASU JSON
    │   Stage 2: ASU JSON → logic JSON
    │   (LLM responses cached in cache.db)
    │
    ▼
logconvert.rawlogic_convert()      [solver/logconvert.py + lc_clausify.py + lc_questions.py]
    │   Logic JSON → GK clause list
    │   FOL → CNF, Skolemisation, defeasible expansion,
    │   context injection, gradable normalisation
    │
    ▼
prover.call_prover()               [solver/prover.py]
    │   Writes clause list to a temp file
    │   Runs the gk binary as a subprocess
    │   Returns raw JSON result string
    │
    ▼
procproofs.process_proof()         [solver/procproofs.py + proof_render.py + proof_explain.py]
    │   Parses prover JSON
    │   Selects best proof, formats answer
    │   Optionally renders step-by-step explanation
    │
    ▼
Answer string
```

The top-level entry point for library use is `english_to_answer(text, options)` in `solve.py`.
The command-line entry point is `main()` in the same file.

---

## 3. Repository layout

```
llmpipe/
├── solver/              Core pipeline modules
│   ├── solve.py         CLI entry point; english_to_answer() library function
│   ├── llmparse.py      Two-stage LLM parser
│   ├── llmcall.py       LLM API wrapper (GPT / Claude / Gemini / DeepSeek, no SDK)
│   ├── logconvert.py    Stage-2 JSON → GK clause list (main driver)
│   ├── lc_clausify.py   FOL → CNF clausification
│   ├── lc_questions.py  Wh-question encoding and population facts
│   ├── procproofs.py    Prover output → answer string
│   ├── proof_render.py  Atom/clause rendering (table-driven)
│   ├── proof_explain.py Step-by-step proof explanation formatter
│   ├── linguistics.py   Pure English heuristics (articles, conjugation, gerunds)
│   ├── prover.py        gk binary interface
│   ├── pretty.py        JSON pretty-printer (Style B)
│   ├── cache.py         SQLite cache for LLM responses and prover results
│   ├── globals.py       Options dict and file paths
│   ├── utils.py         debug_print, clause_list_to_json
│   └── gradables.txt    Whitelist of gradable adjectives (~400 entries)
│
├── prompts/             LLM system prompts
│   ├── stage1_instructions.txt
│   ├── stage1_examples.txt
│   ├── stage2_instructions.txt
│   └── stage2_examples.txt
│
├── tests/               Test cases
│   ├── tests_core.py    Core test suite ([text, expected_answer] pairs)
│   ├── tests_medium_core.py
│   └── tests_small.py
│
├── mkdata/              Synonym/antonym data builder (standalone, own venv)
│   └── README.md        Full documentation for mkdata
│
├── axioms_std.js        Default background-knowledge axioms for gk (persistence,
│                        event-to-relation bridges, transitivity, degree entailments)
├── cache.db             SQLite cache (auto-created; not committed)
│
├── ask.py               Direct LLM call tool (uses solver/llmcall.py)
├── test.py              Test runner
├── checkprompt.py       Validate JSON in prompt example files
└── DOCUMENTATION.md     Full developer documentation
```

---

## 4. Representation overview

The pipeline uses three successive JSON representations.  Understanding all three is essential for
any work on the system.

### 4.1 Stage-1 ASU JSON

**Produced by:** Stage-1 LLM call
**Consumed by:** Stage-2 LLM call and `logconvert.py`

Stage 1 converts English into a list of *sentence packages*, each containing one or more *Atomic
Semantic Units* (ASUs).  Each ASU is one minimal proposition that can be true or false.

```json
[
  {
    "raw": "Birds can fly, but penguins cannot.",
    "units": [
      {
        "unit_id": "S1",
        "text": "Birds can fly.",
        "type": "normal_rule",
        "entities": [{"id":"birds","type":"generic"}],
        "confidence": 0.95
      },
      {
        "unit_id": "S2",
        "text": "Penguins cannot fly.",
        "type": "strict_rule",
        "entities": [{"id":"penguins","type":"generic"}]
      }
    ]
  }
]
```

**ASU `type` values:**

| type | Meaning |
|------|---------|
| `real` | Timeless encyclopedic fact about a specific named entity |
| `situation` | Concrete event or state in a narrative (has tense) |
| `strict_rule` | Definition or law that holds without exception (`forall`/`implies`) |
| `normal_rule` | Defeasible default behaviour (`normally`, `typically`) |
| `query` | A question to be answered |

**Entity object fields:**

| field | meaning |
|-------|---------|
| `id` | Primary symbol — used as-is in Stage 2 (never normalise) |
| `type` | `"concrete"` (specific instance) or `"generic"` (class/kind) |
| `url` | Wikipedia URL for named entities; Stage 2 uses this instead of `id` |
| `scope` | For generics: `"dependent"` (per-subject existential), `"global"` (shared existential), `"kind"` (substance constant — treated as a constant, not a variable) |
| `text` | Present only for relational-role nouns and attribute entities (e.g. `"weight"`, `"sister"`); used to identify the kind of role, not for naming |
| `wh_placeholder` | `true` for the fresh variable introduced for `who/what/where/when` questions |

**Key optional ASU fields:**

| field | meaning |
|-------|---------|
| `adjectives` | List of `[word, intensity, relclass]` for every adjective in the ASU; `intensity` is `"none"`, `"low"` (slightly), or `"high"` (very/extremely); `relclass` is the comparison class (`"person"`, `"car"`, `"entity"` if generic, `"none"` if non-gradable) |
| `pre_state` / `next_state` | World constants for state tracking (`"W0"`, `"W1"`, …) |
| `time` | `"past"`, `"present"`, `"future"`, a year string, or a structured list `["relative", offset, anchor]` |
| `location` | Entity id of the location |
| `confidence` | Float 0–1 (omit for 1.0); affects `@p` metadata in Stage 2 |
| `mental_holder` / `mental_attitude` / `epistemic_force` / `attitude_target` | For propositional attitudes (`knows that`, `believes that`) |
| `definites` | List of `[REL, VALUE_ID, ARG_ID]` for definite descriptions (`"the handle of the fork"`) |

### 4.2 Stage-2 logic JSON

**Produced by:** Stage-2 LLM call
**Consumed by:** `logconvert.rawlogic_convert()`

Stage 2 translates each ASU into first-order predicate logic encoded as nested JSON lists.  The
top-level structure is always:

```json
["and", ["@id","S1", PACKAGE], ["@id","S2", PACKAGE], ...]
```

Each `PACKAGE` is one of:

```
["holds", WORLD, FORMULA]          -- assertion anchored to a world constant
["question", FORMULA]              -- yes/no question
["ask", VAR, FORMULA]              -- wh-question; VAR is the answer variable
["and", PACKAGE, ["@p","Sx",P]]    -- package with confidence P (0–1 float)
```

`FORMULA` is a standard first-order formula in JSON:

```json
["forall","X", ["implies", ["isa","bird","X"], ["normally", ["can","X","fly"]]]]
```

**Predicate inventory** (closed whitelist — no invented predicates):

| Category | Predicates |
|----------|-----------|
| Logical | `and`, `or`, `xor`, `not`, `implies`, `forall`, `exists`, `=`, `<`, `>` |
| Core | `isa TYPE ENTITY`, `has property PROP ENTITY`, `have OWNER OWNED`, `has part WHOLE PART`, `is rel2 REL E1 E2`, `can ENTITY ACTION` |
| Gradable | `has degree property PROP ENTITY DEGREE RELCLASS`, `has degree rel2 REL E1 E2 DEGREE RELCLASS` |
| Events | `isa "activity" E`, `has type E VERB`, `has actor E ENTITY`, `has target E ENTITY`, `has location E ENTITY`, `has instrument E ENTITY`, `has manner E MANNER`, `has direction E DIR`, `has time E TIME`, `typical E`, `typically ENTITY VERB` |
| World | `holds W F`, `next W1 W2`, `state time W T`, `state location W L` |
| Defeasible | `normally FORMULA` |
| Mental | `kb K HOLDER ATTITUDE W`, `kb force K FORCE`, `kb holds K FORMULA`, `kb says K1 K2 FORMULA` |
| Sets | `isa "set" S`, `is set of TYPE S`, `member has property PROP S`, `member ENTITY S`, `is subset of S1 S2`, `set union S1 S2 S3`, `$count S` |
| Traceability | `@id "Sx" FORMULA`, `@p "Sx" P`, `@definite "Sx" W REL ARG VALUE` |
| Questions | `question F`, `ask VAR F` |

**Predicate selection rule for adjectives** (mandatory):

- If a word appears in `ASU.adjectives` → use `has degree property` (or `has degree rel2` for
  binary relations).  Take DEGREE and RELCLASS from the matching adjectives entry.  Do NOT also
  emit `has property` / `is rel2`.
- If a word does NOT appear in `ASU.adjectives` → use `has property` / `is rel2`.  Never both.

**Variable naming conventions:**

| Role | Names |
|------|-------|
| Entity | `X`, `Y`, `Z`, `X1`, `Y1`, … |
| Event | `E`, `E1`, `E2`, … |
| Set | `S`, `S1`, `S2`, … |
| Knowledge base | `K_Sx` |
| Count | `N` |
| Scalar value | `V` |

### 4.3 GK clause list

**Produced by:** `logconvert.rawlogic_convert()`
**Consumed by:** `prover.call_prover()`

The GK prover expects a JSON array of clause dicts:

```json
[
  {"@name": "sent_S1", "@logic": ["isa","bird","tweety 1"]},
  {"@name": "sent_S2", "@logic": [
    ["-isa","bird","?:X"], ["can","?:X","fly"]
  ]},
  {"@name": "sent_S3", "@question": ["can","tweety 1","fly"]}
]
```

Each dict has exactly one content key: `@logic` for assertions, `@question` for the query.

**Clause formats:**

- Single atom: `["pred", arg1, arg2, ...]`
- Disjunction: `[["pred1",...], ["pred2",...], ...]` — represents `pred1 OR pred2 OR ...`
- Negated atom: `["-pred", arg1, ...]` — the `-` prefix negates the predicate

**Variables:** any string beginning with `?:` (e.g. `"?:X"`, `"?:Fv3"`).  In GK, all free
variables in a clause are implicitly universally quantified.  Existential quantifiers are
eliminated by Skolemisation during `rawlogic_convert`.

**Defeasible atoms:** `["$block", PRIORITY, ["$not", HEAD]]`
These appear alongside the rest of the clause literals.  The prover uses the priority to decide
which default conclusions can be blocked by more specific rules.  Priority has the form
`["$", CLASS, N]` where CLASS is the subject class (e.g. `"bird"`) and N is an integer.

**Context atom:** `["$ctxt", TENSE, WORLD, LOCATION, KNOWER]`
Appended to eligible predicate atoms (see §4.5).  All four components are either concrete
constants or fresh free variables.

**Confidence:** Some clause dicts also carry `"@confidence": 0.8` (from `@p` metadata).

### 4.4 The adjectives field

All adjectives/properties in Stage-1 output carry an `"adjectives"` field:

```json
"adjectives": [["tall","none","person"], ["fast","none","car"], ["red","none","none"]]
```

Each entry is `[word, intensity, relclass]`:

- **word** — the adjective or relational phrase (e.g. `"close to"`)
- **intensity** — `"none"` (plain), `"low"` (slightly/a bit), `"high"` (very/extremely)
- **relclass** — the comparison class; use `"none"` for non-gradable adjectives (colours,
  categorical) and `"entity"` when no specific class is known; the system replaces both
  `"entity"` and `"none"` with a fresh free variable during `logconvert` (since neither
  carries a useful comparison-class constraint)

Stage 2 then uses this field to decide which predicate to emit (`has degree property` vs
`has property`; `has degree rel2` vs `is rel2`).  `logconvert` additionally normalises based on
the whitelist in `solver/gradables.txt`: words not in the whitelist are downgraded from
`has degree property` to `has property` regardless of what Stage 2 produced.

### 4.5 The $ctxt context term

Every eligible predicate atom in the GK clause list is augmented with a trailing `$ctxt` term:

```
["has property","tall","John 1",  ["$ctxt","past","W0","?:Fv1","?:Fv2"]]
                                    ▲        ▲      ▲    ▲       ▲
                                    pred     tense  world loc     knower
```

The four `$ctxt` arguments are:

| Position | Source |
|----------|--------|
| tense | `ASU.time` from Stage 1, or a fresh free variable for rules |
| world | `ASU.pre_state` from Stage 1 (or `W` constant from `["holds",W,F]`) |
| location | `ASU.location` from Stage 1, or a fresh free variable |
| knower | holder of a mental attitude, or a fresh free variable |

Eligible predicates (`_CTXT_ELIGIBLE` in `logconvert.py`): `has property`, `have`, `has part`,
`can`, `is rel2`, `has degree property`, `has degree rel2`, plus all event predicates (`has type`,
`has actor`, `has target`, …), `typical`, `typically`.  Structural predicates (`isa`, `holds`,
`state *`, `next`, `kb *`, `@*`, `$*`, `=`, `<`, `>`) are NOT augmented.

Context injection can be disabled with `-nocontext` (or `-simple`).

### 4.6 Defeasible reasoning and $block

Normal rules (type `normal_rule` in Stage 1) produce defeasible clauses.  The pattern for a
typical bird-fly rule is:

```
Stage 2 (holds world / forall):
  ["forall","X",["implies",["isa","bird","X"],["normally",["can","X","fly"]]]]

GK clauses produced by logconvert:
  ["-isa","bird","?:X"],  ["can","?:X","fly"],  ["$block",["$","bird",1],["$not",["can","?:X","fly"]]]
```

The `$block` literal means: *"this conclusion (`can X fly`) can be defeated by a rule with
priority higher than `["$","bird",1]` for the class `bird`"*.  The penguin exception would carry
a higher priority and the same head atom, allowing GK to prefer the exception.

Defeasible expansion can be disabled with `-noexceptions` (or `-simple`).

---

## 5. Source files

All Python source lives in `solver/`.  All scripts are run from `llmpipe/`.

### 5.1 solve.py

**Role:** CLI entry point and library facade.

**Key function:** `english_to_answer(text, options=None) -> str`
Orchestrates the complete pipeline.  Calls `llmparse.parse_text`, then `rawlogic_convert`,
then `prover.call_prover`, then `process_proof`.  Returns the answer string; on any error
returns a string starting with `"Error:"` rather than raising.

`main()` parses `sys.argv`, builds an options dict, and calls `english_to_answer`.

**CLI flags** (all optional):

Output level (hierarchy — each level includes all previous levels):

```
-explain           Show English proof explanation
-logic             + simplified ASU text, sentences-to-clauses, logic in proof steps
-details           + stage-1/2 JSON, prover input/output JSON
-debug             + raw LLM responses, prover params, full pipeline trace
```

Output format and other flags:

```
-json              Show logic as raw JSON instead of traditional pred(arg,...) syntax
-jsonlogic         Shortcut for -logic -json
-gkin FILE         Save GK prover input to FILE (with the GK command as a comment)
-llm NAME          LLM provider: gpt, claude, gemini, deepseek
-version VER       Model version string
-nosolve           Parse only; do not call the prover
-nollmcache        Disable LLM response caching for this run
-clearcache        Clear all caches and exit
-seconds N         Prover time limit (default 2)
-simple            No context, no exceptions, simple properties
```

### 5.2 llmparse.py

**Role:** Two-stage LLM parser.

**Key function:** `parse_text(text, llm=None, version=None, tokens=None) -> (s1_json, s2_json, stats)`

The function:
1. Loads prompts from `prompts/` on first call (lazy, cached in module-level globals).
2. Calls `_run_stage(1, text, ...)` to produce Stage-1 ASU JSON.
3. Serialises Stage-1 output as JSON string; passes it as input to `_run_stage(2, ...)`.
4. Returns both parsed objects plus a stats dict.

**`_run_stage`** handles robustness:
- Calls `llmcall.call_llm`.
- Tries `json.loads` on the raw response.
- If that fails, applies `fix_json` (heuristic repairs: strip markdown fences, remove Python
  literals, balance brackets, strip trailing junk, etc.).
- If still invalid, makes one LLM retry with error feedback in the prompt.
- Tracks all events in the stats dict (`s1_calls`, `s1_json_errors`, `s1_json_fixes`,
  `s1_retry_calls`, etc.).

**`fix_json(s)`** applies up to 10 repair strategies in sequence, returning the first one that
produces valid JSON.  Repairs include: stripping ` ```json ``` ` fences, replacing Python
`True`/`False`/`None` with JSON equivalents, stripping non-JSON wrapper text, adding missing
commas, balancing brackets.

**Prompt composition:** `_compose_prompt(instructions_file, examples_file)` concatenates
instructions + `"\n\nExamples:\n\n"` + examples into a single system prompt string.

### 5.3 llmcall.py

**Role:** Low-level LLM API wrapper.

**Key function:** `call_llm(sysprompt, input_text, llm=None, version=None, max_tokens=None, think=False) -> str | None`

Dispatches to `call_gemini`, `call_claude`, `call_gpt`, or `call_deepseek` based on the
`use_llm` setting.  Two shared helpers keep the provider functions concise:
- `_read_api_key(filepath, provider)` — reads a plain-text API key file
- `_post_with_retry(host, url, body, headers, provider)` — HTTPS POST with retry loop,
  error handling, and JSON response parsing

**Caching:** Before calling the LLM, `call_llm` checks the SQLite cache in `cache.db`.  The
cache key encodes: provider, version, temperature, seed, max_tokens, think, sysprompt, input_text.
If a match is found, the cached response is returned immediately.  The result of every new LLM
call is stored in the cache before returning.  Caching is controlled by
`globals.options["use_llm_cache_flag"]` (default `True`).

**Debug output:** Uses `utils.debug_print` with module-level `debug` and `calldebug` flags:
- `debug = True` logs each provider's raw response
- `calldebug = True` logs the full request body sent to the API

**Configuration** (edit at the top of `llmcall.py`):

```python
use_llm          = "gemini"            # "gpt" | "claude" | "gemini" | "deepseek"
claudeversion    = "claude-sonnet-4-6"
gptversion       = "gpt-5.1"
geminiversion    = "gemini-2.0-flash"
deepseekversion  = "deepseek-chat"     # V3.2; "deepseek-reasoner" for thinking
temperature      = 0
default_max_tokens = 8000
max_retries      = 3
```

API keys are read from plain-text files in `../secrets/` (relative to `llmpipe/`):
`gpt_secrets.txt`, `claude_secrets.txt`, `gemini_secrets.txt`, `deepseek_secrets.txt`.
The directory path is set once via `_secrets_dir` in `llmcall.py`.

### 5.4 logconvert.py

**Role:** Main driver for logic conversion — orchestrates the full Stage-2 JSON → GK clause
list pipeline.  The heavy computation is split across three files: `logconvert.py` handles
package extraction, context injection, and post-processing passes; `lc_clausify.py` does FOL→CNF
compilation; `lc_questions.py` handles question encoding and population facts.

**Key function:** `rawlogic_convert(logic, s1_json=None) -> list | None`

Converts the Stage-2 nested JSON formula into a flat GK clause list:

```
["and", ["@id","S1",PACKAGE], ...] (Stage-2 input)
    │
    ├─ _build_asu_index(s1_json)          build unit_id→ASU lookup from Stage 1
    ├─ _populate_clauses(items)            collect "populate" background facts
    │
    ├─ for each @id item:
    │    _convert_id_package(item, asu_index)
    │        _extract_package_ctx()        unpack PACKAGE: formula, world, tense, etc.
    │        override with Stage-1 ASU data (tense, world, location)
    │        _process_question()           wh-/yes-no question dispatch  [→ lc_questions.py]
    │        _process_assertion()          clausify + confidence  [→ lc_clausify.py]
    │        inject $ctxt into result
    │
    ├─ insert population facts before first @question
    ├─ inject $ctxt into population facts
    ├─ _normalize_gradable_predicates()   whitelist-based has property ↔ has degree property
    ├─ _strip_isa_entity()                remove trivially-true/false isa entity literals
    ├─ _coerce_relclass()                 fix RELCLASS mismatches in question atoms
    ├─ _strip_degree_predicates()         (only if -simpleproperties flag)
    └─ strip @sourcetype                  remove internal annotation before prover
```

**Module-level constants:**

- `_GRADABLE_PROPS` — frozenset loaded from `solver/gradables.txt`; ~400 lowercase property names
- `_CTXT_ELIGIBLE` — frozenset of predicates that receive a `$ctxt` argument

**Counter globals** (reset at the start of each `rawlogic_convert` call):

- `lc_clausify._skolem_nr`, `lc_clausify._gobj_nr` — Skolem and generic-object counters
- `lc_questions._defq_nr` — `$defq` predicate name counter (for complex questions)
- `_fv_nr` (in `logconvert`) — fresh free-variable counter (`?:Fv1`, `?:Fv2`, …)

See §7 for detailed discussion of the key algorithms.

### 5.5 lc_clausify.py

**Role:** FOL → CNF clausification compiler.

**Public API used by `logconvert.py`:**

- `clausify(formula) -> list` — converts a first-order formula to a list of CNF clauses
- `looks_like_var(s) -> bool` — true if `s` starts with `?:` (GK variable convention)
- `apply_varmap(formula, varmap) -> formula` — substitute variables by name
- `connectives` — frozenset of logical connective names (not predicates)

**Clausification pipeline** (inside `clausify`):

```
_normalize_type_case
_strip_typical_from_antecedent
_expand_generic_objects
_normalize_quantifiers
_implies_to_or                 eliminate implies / equivalent / xor
_push_neg                      push negations in to reach NNF
_expand_normally (pass 1)      push normally inside exists/and
_skolemize                     eliminate existentials → Skolem terms
_distribute                    distribute or over and → CNF
_expand_normally (pass 2)      normally(atom) → $block clause
_extract_clauses               collect flat clause list
```

**Internal helpers** (extracted from `_expand_normally` and `_distribute`):

- `_flatten_or_elements(elements)` — flatten nested `or` wrappers in a list of formula elements
- `_classify_literals(lits)` — split literals into `(neg_lits, pos_lits)` by predicate polarity
- `_extract_isa_priority(neg_lits, blocker_class_tag, extra_neg)` — compute `$block` priority
  from negative literals and optional class tag

**Module-level counters** (reset externally by `rawlogic_convert`):

- `_skolem_nr` — next Skolem constant/function index
- `_gobj_nr` — generic-object counter for `_expand_generic_objects`

### 5.6 lc_questions.py

**Role:** Wh-question encoding and population-fact collection.

**Public API used by `logconvert.py`:**

- `build_defq_question(name, ask_var, body, where_prep=None) -> list` — encode a wh- or yes/no
  question as `$defq` biconditional GK clauses
- `find_where_atom(body, ask_var) -> atom | None` — find the location atom in a where-question body
- `build_where_question(name, entity, ask_var, specific_prep=None) -> list` — encode a where-question
- `flatten_q_atoms(frm, varmap) -> list` — flatten an `ask` formula into a list of atoms
- `scan_item_formula(frm, name, polarity, classes, has_props, deg_props)` — scan a formula for
  isa / has-property / has-degree-property atoms, recording polarity in the provided dicts
- `build_population_facts(classes, has_props, deg_props) -> list` — build positive/negative
  synthetic population clauses from collected scan data
- `is_ground_term(t) -> bool` — true if `t` contains no variables
- `is_simple_question_formula(f) -> bool` — true if `f` is a single atom (not compound)
- `collect_body_free_vars(frm, bound=None) -> set` — free variables in a formula
- `find_haslocation_prep(body, ask_var) -> str | None` — return `"in"` if body contains
  `has_location` with the ask variable
- `simplify_contradictory_and(frm) -> formula` — simplify `["and", ["not", A], A]` to `["not", A]`
- `S2_VAR_RE` — regex matching Stage-2 variable names (uppercase-initial identifiers)
- `WHERE_SPATIAL_PREPS` — set of spatial prepositions handled as where-questions

### 5.7 procproofs.py

**Role:** Post-processing of raw prover output into a human-readable answer.

**Key function:** `process_proof(proof_result, text=None, s1_json=None, logic=None, options=None) -> str`

1. Parses the raw prover JSON string.
2. Checks for `"result": "answer found"`.  Returns `"Unknown."` if not found.
3. Sorts answers by `_answer_goodness` (confidence desc, proof length asc).
4. Filters to the best object-type tier: concrete entities > Skolem constants > population facts.
5. Formats the answer string via `_format_answers`:
   - Boolean `True`/`False` → `"True"` / `"False"`
   - Named entities → display name (strips numbering when unambiguous, strips URL when
     display name is unambiguous)
   - Confidence < 0.99 → appends `"(confidence X%)"`
6. Optionally renders a step-by-step proof explanation (via `proof_explain.format_explanation`)
   when `-explain` is used.

**Internal helpers:**

- `_join_and_finish(parts)` — join a list of answer strings with "and", capitalise, add period;
  shared by `_format_where_answers` and `_format_answers`

**Ambiguity handling:** Before formatting, `compute_ambiguity` (from `proof_render.py`) scans
the full logic list to find entity names that appear with more than one number (e.g. `"John 1"`
and `"John 3"`).  Such names keep their distinguishing number in output.

**Imports from proof_render.py:** `compute_ambiguity`, `entity_name`, `ans_atom_name`
**Imports from proof_explain.py:** `format_explanation`, `build_sentence_map`, `ans_display_key`

### 5.8 proof_render.py

**Role:** Low-level rendering of proof atoms and clauses as English strings.

**Architecture:** Atom-to-English rendering is table-driven via `_PRED_TABLE`, a dict mapping
predicate names to `(arity, pos_renderer, neg_renderer)` tuples.  The unified `_render_atom(atom,
negated=False)` function dispatches through the table, with fallback handlers for special cases
(`holds`, `normally`, `$defq*`, etc.).

Per-proof mutable state (entity map, ambiguous names, Skolem type annotations) is bundled in a
`RenderContext` class (`_ctx` module-level instance), replacing former module-level globals.

**Imports from linguistics.py:** `indef_article`, `conjugate_verb`, `make_comparative`,
`to_gerund` — pure English heuristic helpers with no dependency on proof state.

**Public API:**

- `compute_ambiguity(logic) -> (set, set)` — returns `(ambiguous_names, ambiguous_urls)` by
  scanning the full clause list for multiply-numbered entities
- `compute_skolem_types(proof)` — annotate each Skolem constant in a proof with the type inferred
  from `isa` literals in the proof steps (mutates step dicts in-place)
- `set_entity_map(entity_map)` — set the entity display map in the render context
- `get_entity_display(key)` — look up an entity's display name
- `entity_name(atom_arg, ambiguous, ambig_urls) -> str` — format one entity argument for display
- `ans_atom_name(atom) -> str` — format the answer atom of a proof step
- `clause_to_str(clause) -> str` — convert a raw clause list to a readable string
- `format_clause_logic(clause) -> str` — format clause as FOL-style logic notation
- `block_to_english(blocker) -> str` — convert a `$block` literal to a readable exception string

### 5.9 proof_explain.py

**Role:** Builds the full step-by-step proof explanation presented to the user.

**Public API:**

- `build_sentence_map(s1_json) -> dict` — builds `{"sent_S1": "raw text", ...}` from Stage-1
  output; maps each clause name back to the original English sentence it came from
- `format_explanation(answers, sentence_map, show_logic=False) -> str` — main entry point;
  produces the `"Explained:\n\n..."` block for all (non-duplicate) answers; groups proof steps
  under "Sentences used:", "Knowledge used:", and "Proof steps:"
- `ans_display_key(val, askvars=None) -> hashable` — canonical dedup key for an answer value;
  ignores auxiliary world-state arguments

### 5.10 prover.py

**Role:** Interface to the `gk` binary theorem prover.

**Key function:** `call_prover(logic) -> str`

1. Serialises the GK clause list to a JSON string using `clause_list_to_json` (from `utils.py`).
2. Writes the string to a temporary file.
3. Launches the `gk` binary via `subprocess.Popen` with the temp file plus flags built from
   `globals.options` (axiom files, strategy, time limit, print level, KB flags).
4. Reads stdout, decodes as ASCII, optionally caches the result, removes the temp file.
5. Returns the raw prover output string (JSON).

Key paths (from `globals.py`):

```
../gk/gk                      binary
llmpipe/axioms_std.js          default axiom file
../gk/gk_name_number.txt       name→number data
../gk/gk_taxonomy_packed.txt   taxonomy data
```

### 5.11 pretty.py

**Role:** Human-readable pretty-printing of JSON structures.

**Key functions:**
- `pp_logic(obj, file=None)` — print a GK clause list
- `pp_stage1(obj, file=None)` — print Stage-1 ASU JSON
- `pp_stage2(obj, file=None)` — print Stage-2 logic JSON
- `pp_str(obj) -> str` — return the formatted string (used by the three above)

**Layout (Style B):** Lists are kept on one line when they fit within 100 columns.  When
expanded, the first element follows the opening `[` immediately; subsequent elements are indented
to align with the first.  Consecutive closing-bracket-only lines are merged onto one line.

**`noquotes` mode** (`pretty.noquotes = True`): suppresses quotation marks and replaces spaces
in strings with underscores — more readable for debugging.

### 5.12 cache.py

**Role:** SQLite-backed cache for LLM responses and prover results.

Three separate tables in `cache.db`:
- `llm_cache` — keyed on `(provider, version, temperature, seed, max_tokens, sysprompt, input)`
- `proof_cache` — keyed on the prover parameter string
- `parse_cache` — for parsed results (future use)

Key functions: `get_llm_from_cache`, `add_llm_to_cache`, `get_proof_from_cache`,
`add_proof_to_cache`, `clear_all_caches`.  LLM caching is controlled by
`globals.options["use_llm_cache_flag"]`.  Proof caching is off by default and enabled with
`-cache`.

### 5.13 globals.py

**Role:** Global configuration, file paths, and the `options` dict.

Contains only what is actually used by the active pipeline:

**`options` dict** — runtime behaviour flags:

| Key | Default | Effect |
|-----|---------|--------|
| `use_llm_cache_flag` | `True` | Use SQLite LLM cache |
| `use_cache_flag` | `False` | Use prover result cache |
| `debug_print_flag` | `False` | Print debug info |
| `prover_print_flag` | `False` | Print prover I/O |
| `show_logic_flag` | `False` | Print parsed logic |
| `prover_explain_flag` | `False` | Print proof explanation |
| `prover_nosolve_flag` | `False` | Parse only, skip prover |
| `prover_seconds` | `2` | Prover time limit |
| `nocontext_flag` | `False` | Disable $ctxt injection |
| `noexceptions_flag` | `False` | Disable defeasible $block |
| `noproptypes_flag` | `False` | Strip degree predicates |
| `nokb_flag` | `True` | Skip shared-memory KB |

**File paths** (computed relative to `llmpipe/`):

```python
cache_db_name     = "cache.db"
prover_fname      = "../gk/gk"
prover_axiomfile  = "axioms_std.js"
prover_datafolder = "../gk"
memkb_name        = "1000"
prover_infile     = "gk_infile.js"
prover_params     = ["-defaults", "-confidence", "0.1", "-keepconfidence", "0.1"]
usekb_prover_params = ["-usekb", "-confidence", "0.1", "-keepconfidence", "0.1"]
```

**`set_global_options(newoptions)`** — merge a dict into `options`; called by `solve.py` with
the parsed CLI flags.

### 5.14 utils.py

**Role:** Shared utility functions used across the pipeline.

- `debug_print(label, data=None, flag=None)` — prints a labelled debug message when `flag` is
  truthy.  If `flag` is `None` (default), falls back to `globals.options["debug_print_flag"]`.
  Pass an explicit boolean to use a different flag (e.g. `llmcall.py` passes its module-level
  `debug` and `calldebug` variables).  Formats `data` intelligently: lists are printed one
  element per line (nested lists indented), dicts show key/value pairs.

- `clause_list_to_json(logic) -> str` — converts the Python GK clause list to a JSON string
  suitable for passing to the `gk` binary.  Uses `json.dumps` with compact separators.

### 5.15 linguistics.py

**Role:** Pure English linguistic heuristics used by `proof_render.py` for human-readable output.
No dependency on proof state or any other pipeline module.

- `indef_article(word) -> str` — returns `"an"` before vowel sounds, `"a"` otherwise
- `conjugate_verb(v) -> str` — third-person singular present tense (`fly` → `flies`)
- `make_comparative(adj) -> str` — comparative form (`nice` → `nicer`, `beautiful` → `more beautiful`)
- `to_gerund(verb) -> str` — gerund form (`run` → `running`, `bite` → `biting`)

---

## 6. Prompt files

All four prompt files live in `prompts/`.  They are concatenated into system prompts by
`llmparse._compose_prompt`:

```
<instructions>

Examples:

<examples>
```

| File | Purpose |
|------|---------|
| `stage1_instructions.txt` | Full specification of Stage-1 output format; entity rules, type classification, splitting rules, adjective format, scope hints, state tracking, etc. |
| `stage1_examples.txt` | ~30 worked input→output examples for Stage 1; one per `---` separator |
| `stage2_instructions.txt` | Full specification of Stage-2 output format; entity handling (concrete/generic/kind/wh), quantification rules by ASU type, predicate inventory, property/relation selection rule |
| `stage2_examples.txt` | ~40 worked input→output examples for Stage 2; one per `----` separator |

**Editing the prompts** is the primary way to improve Stage-1 and Stage-2 accuracy.  Both
instruction files have version-pinned sections (`== 1. ... ==`, `== 2. ... ==`, etc.) that can be
updated independently.  The examples in both files follow the same section separator (`---` or
`----`) and can be added, removed or corrected freely.

An important constraint: **examples must be consistent with instructions**.  In particular:
- Every adjective/property that appears in an ASU text must appear in `"adjectives"` in Stage-1
  examples (including queries and rules).
- Stage-2 examples must use `has degree property` (not `has property`) when the word is in
  `adjectives`, and vice versa; never both.

---

## 7. Key algorithms in logconvert.py and lc_clausify.py

### 7.1 Package extraction

`_extract_package_ctx(package)` (in `logconvert.py`) unwraps a Stage-2 PACKAGE and returns
`(is_question, formula, confidence, world, location, knower, tense)`.

The PACKAGE shapes it handles:
- `["holds", W, F]` → `is_question=False`, `formula=F`, `world=W`
- `["question", F]` → `is_question=True`, `formula=F`
- `["ask", VAR, F]` → `is_question=True`, `formula=["ask",VAR,F]` (kept whole for wh-handling)
- `["and", PKG, ["@p","Sx",P], ["state time",W,T], ...]` → recurse into the main sub-package;
  collect confidence, tense, location, knower from siblings

After extraction, `_convert_id_package` overrides `tense`, `world`, and `location` with data
from the matching Stage-1 ASU (when `asu_index` is available).  Stage-1 data is authoritative
because it is produced closer to the English source.  The actual question/assertion logic is
delegated to `_process_question` (wh-/yes-no dispatch) and `_process_assertion` (confidence
handling + clausification).

### 7.2 FOL to CNF clausification

`clausify(formula)` (in `lc_clausify.py`) converts a first-order formula into conjunctive normal
form through five passes:

1. **`_implies_to_or`** — eliminate `implies`, `equivalent`, `xor`:
   - `implies(A,B)` → `or(not(A), B)`
   - `equivalent(A,B)` → `and(implies(A,B), implies(B,A))`, then recurse
   - `xor(A,B)` → `and(or(A,B), or(not(A),not(B)))`
   - Does not recurse inside `_opaque_wrappers` (i.e. `normally`)

2. **`_push_neg`** — push negations inward to reach Negation Normal Form (NNF):
   - De Morgan: `not(and(...))` → `or(not(...),...)`, etc.
   - Quantifier duality: `not(forall X, P)` → `exists X, not(P)`
   - Atom negation: toggle the `"-"` prefix on the predicate name
   - `normally` treated as opaque: `not(normally(F))` → `"-normally"(F)`

3. **`_expand_normally` pass 1** — push `normally` inside complex bodies before Skolemisation:
   - `normally(exists X, B)` → `exists X, _push_normally_inside(B)`
   - `normally(and(A1,...,An))` → `and(A1,...,An-1, normally(An))`
   - Simple `normally(atom)` is left for pass 2

4. **`_skolemize(frm, universal_vars, varmap)`** — eliminate existential quantifiers:
   - `forall X, F` → recurse with `X` added to `universal_vars`
   - `exists X, F` → replace `X` with a Skolem term:
     - No universal vars in scope → Skolem constant `"sk0"`, `"sk1"`, …
     - Universal vars in scope → Skolem function `["sk0","?:X",...]` applied to those vars
   - `forall` is stripped (variables become free, i.e. implicitly universally quantified in GK)

5. **`_distribute`** — distribute `or` over `and` to reach CNF:
   - `or(and(A,B), C)` → `and(or(A,C), or(B,C))`
   - Recursive until no `or` wraps an `and`

6. **`_expand_normally` pass 2** — expand remaining `normally(atom)` into `$block` clauses:
   - See §7.3 below

7. **`_extract_clauses`** — collect all flat clauses from the resulting `and` tree

### 7.3 Defeasible expansion

After Skolemisation and CNF distribution, every `normally(atom)` appears inside an `or` clause
alongside conditions (negative literals `-isa bird ?:X`) and other conclusions.

`_expand_normally` pass 2 processes such an `or` clause:
1. Separate negative literals (conditions, start with `"-"`) from positive literals (conclusions).
2. Use the **last positive literal** as the head to be blocked.
3. Compute priority `["$", CLASS, N]`:
   - CLASS = class from the last `-isa` condition (e.g. `"bird"`), or `"$generic"` if no `-isa`
   - N = number of non-`isa` negative conditions + 1 (more specific rules get higher N)
4. Append `["$block", priority, ["$not", head]]` to the clause.

Result for `normally(["can","?:X","fly"])` inside `["-isa","bird","?:X"]`:
```
["-isa","bird","?:X"], ["can","?:X","fly"], ["$block",["$","bird",1],["$not",["can","?:X","fly"]]]
```

The penguin exception would generate priority `["$","bird",2]` (higher specificity), which GK
uses to defeat the bird default.

With `-noexceptions`, the `$block` is suppressed and `normally` becomes equivalent to a strict
implication.

### 7.4 Context injection ($ctxt)

After clausification, `_inject_ctxt_into_objs` (in `logconvert.py`) appends a
`["$ctxt",T,W,L,K]` term to every eligible predicate atom in every `@logic` clause.

The four `$ctxt` components per ASU:

| Component | Rules | Situational facts | Questions |
|-----------|-------|-------------------|-----------|
| tense T | fresh free var | Stage-1 `time` or `"present"` | Stage-1 `time` or fresh var |
| world W | fresh free var | Stage-1 `pre_state` or W from `holds` | Stage-1 `pre_state` or fresh var |
| location L | fresh free var | Stage-1 `location` or fresh var | Stage-1 `location` or fresh var |
| knower K | fresh free var | mental holder or fresh var | mental holder or fresh var |

Rules use fresh free variables for all four components so they match facts from any time/world.
Situational facts use concrete world/tense values so they match only facts in the same context.

Context injection can be disabled globally with `nocontext_flag`.

### 7.5 Gradable property normalisation

`_normalize_gradable_predicates(result)` (in `logconvert.py`) iterates over all clauses and
applies `_norm_grad_frm` to every predicate atom:

- `has degree property PROP ...` where PROP is **not** in `_GRADABLE_PROPS`
  → convert to `has property PROP ENTITY` (drop degree/relclass)
- `has property PROP ...` where PROP **is** in `_GRADABLE_PROPS`
  → convert to `has degree property PROP ENTITY "none" RELCLASS` (add degree/relclass;
  RELCLASS = fresh free variable)
- `has degree property ... RELCLASS` where RELCLASS is `"entity"` or `"none"`
  → replace with a fresh free variable (neither carries a useful comparison-class constraint,
  and leaving them as constants would block unification against meaningful relclasses like
  `"person"`)

The same logic applies to `has degree rel2` vs `is rel2`.

After this normalisation, `_strip_isa_entity` removes any remaining `["isa","entity",X]` or
`["-isa","entity",X]` literals, since "entity" is universal:
- Positive `isa entity X` makes a clause a tautology → remove the entire clause
- Negative `-isa entity X` is always false → remove just the literal

### 7.6 Population facts

`_populate_clauses(items)` (in `logconvert.py`, using helpers from `lc_questions.py`) makes one
pass over all Stage-2 items before clausification and collects *population facts*: `isa TYPE
ENTITY` atoms for every concrete entity that appears as an argument of a `forall`-quantified
rule.  For example, if a rule says "all birds can fly" and a concrete entity `tweety 1` appears
as an `isa bird tweety 1` fact, that fact must be inserted before the question so the prover can
use it.

Population facts are tagged with `"@sourcetype": "populate"` internally (stripped before the
prover sees them) so that `_coerce_relclass` can treat them differently from question clauses.

### 7.7 Stage-2 rewrites and modifications

The pipeline applies several transformations to the raw Stage-2 LLM output before and after
clausification.  These compensate for LLM inconsistencies, enforce pipeline conventions, and
bridge representation gaps.

**Pre-clausification rewrites** (on the raw Stage-2 JSON formula, before `clausify`):

| Rewrite | Where | Example | What it does |
|---------|-------|---------|-------------|
| Degree presupposition injection | `logconvert._inject_degree_presuppositions` | "John is not very big" → adds "John is big" (unmarked degree) alongside the negated "very big" | `["not",["has degree property",P,E,"high",C]]` → `["and",["has degree property",P,E,"none",C],["not",...]]` |
| Stative event rewriting | `semnormalize.rewrite_stative_events` | "John had a car" encoded as an event → rewritten to direct `have(john,car)` | Replaces Davidsonian event encoding of stative verbs (have, own, like, love, etc.) with direct predicates.  Safety: only rewrites when the event variable has no extra properties (has_location, etc.) |
| `@time` stripping | `logconvert._strip_time_wrappers` | "John was tall" — the past-tense `@time` wrapper becomes a `$tense` sentinel controlling the tense slot in `$ctxt` | Converts `["@time","past",ATOM]` wrappers into `$tense` sentinels on the atom |
| Entity category injection | `logconvert._build_entity_category_clauses` | "John is an elephant" — Stage-1 says John's category is "person", so `isa(person, John 1)` is added even though Stage-2 only emits `isa(elephant, John 1)` | Adds `isa(CATEGORY, ENTITY)` facts from Stage-1 entity annotations when not already present in Stage-2 |
| Entity base-word isa | `logconvert._build_entity_category_clauses` | "A man had a car" — entity `man 1` has category "person", but the base word "man" is also a type; adds `isa(man, man 1)` alongside `isa(person, man 1)` | For concrete entities with a lowercase base word different from the category, injects `isa(BASE, ENTITY)` so queries using the descriptive type word can match |
| Compound subsumption | `logconvert._build_compound_subsumption` | "Baby birds do not fly" — adds a rule that baby birds are birds, so general bird rules can apply to them | Adds `isa(BASE, X) :- isa(COMPOUND, X)` rules for compound types |

**Post-clausification modifications** (on the GK clause list):

| Modification | Where | Example | What it does |
|-------------|-------|---------|-------------|
| `$ctxt` injection | `logconvert._inject_ctxt_into_objs` / `_inject_ctxt_question` | "John was tall" → atom gets `$ctxt(past,W0,?,?)` anchoring it to the past in world W0 | Appends `["$ctxt",T,W,L,K]` to eligible predicate atoms.  Rules: all-free-var.  Assertions: concrete world/tense.  Questions: see next row (§7.4) |
| Descriptive/stative/dynamic split | `logconvert._inject_ctxt_question` | "Did the man have the red car which a woman bought?" — `bought` events and `red` property each get independent free-var worlds; stative `have` also gets free-var world; only dynamic event predicates (if matrix) keep the query's world | Three-way $ctxt world dispatch in `$defq` questions: (1) **descriptive** atoms (isa, event atoms, properties when a main relation is present) each get an independent free-var world; (2) **stative matrix** predicates (have, can, has part) get free-var world — persistent states don't need concrete world anchoring; (3) **dynamic matrix** predicates (is_rel2, properties when no main relation) keep the query's world.  `_question_has_main_relation` detects whether properties are restrictive modifiers.  Each descriptive/stative atom gets its OWN fresh world variable to avoid forced co-unification across different world states |
| Gradable normalisation | `logconvert._normalize_gradable_predicates` | "John is big" — LLM used `has property(big,...)` but "big" is in the gradable whitelist → upgraded to `has degree property` | Whitelist-based `has property` ↔ `has degree property` conversion; replaces `"entity"` and `"none"` relclass with free variables (§7.5) |
| `isa entity` stripping | `logconvert._strip_isa_entity` | "Every entity that is big is strong" — `isa(entity,X)` is always true, so the clause is a tautology → removed | Removes tautological `isa(entity,X)` literals (§7.5) |
| RELCLASS coercion | `logconvert._coerce_relclass` | "Is John big?" — query uses relclass "person" (John's category) but the rule uses "bear" → relclass replaced with free variable so they unify | Fixes relclass mismatches in question degree-predicate atoms |
| Possessive `have` inference | `logconvert._add_possessive_have` | "The handle of the fork" — `is_rel2(handle of, fork, handle)` + `isa(handle, handle)` → `have(fork, handle)` | Infers `have(Y,E)` from possessive `is_rel2` patterns |
| Degree stripping | `logconvert._strip_degree_predicates` | With `-simpleproperties`: `has_degree_property(big,X,none,animal)` → `has_property(big,X)` | (Only with `-simpleproperties`) Replaces degree predicates with simple property predicates |
| Semantic normalisation | `semnormalize.sem_normalize_clauses` | "The ball is outside the box" → `outside` is antonym of `inside` → flips polarity and substitutes: `-is_rel2(inside,ball,box)` | Antonym resolution (flip polarity + swap word) and canonical substitution (synonym → canonical form) |
| `@sourcetype` stripping | Serialisation (`clause_list_to_json`) | Population facts carry `@sourcetype:"populate"` internally for processing — stripped before the prover sees them | Internal `@sourcetype` tags are excluded from prover input |

---

## 8. Configuration and options

**To change the default LLM provider or model**, edit `solver/llmcall.py`:
```python
use_llm          = "gemini"            # "gpt" | "claude" | "gemini" | "deepseek"
geminiversion    = "gemini-2.0-flash"
claudeversion    = "claude-sonnet-4-6"
deepseekversion  = "deepseek-chat"
```

**To change the gradable property whitelist**, edit `solver/gradables.txt`.  One lowercase
property name per line.

**To change prover defaults** (time limit, axioms, strategy), edit `globals.py` or pass flags
to `english_to_answer` via the `options` dict:
```python
english_to_answer(text, {"prover_seconds": 5, "nocontext_flag": True})
```

**To disable LLM caching for a single call:**
```python
english_to_answer(text, {"use_llm_cache_flag": False})
```

---

## 9. The mkdata toolkit

`mkdata/` is a standalone toolkit (separate venv, no dependency on `solver/`) for building the
synonym/antonym data files consumed by the reasoning pipeline.

**What it produces:**

- `syn_rewrite_<pos>.txt` — hard rewrite table (word → canonical, similarity ≥ 0.90); used
  by `logconvert.py` to normalise predicate names before clausification
- `syn_axioms_<pos>.js` — soft GK axiom file (0.70 ≤ similarity < 0.90); passed to the `gk`
  prover alongside `axioms_std.js` for near-synonym bridging during proof search

One pair of files per part of speech: N (nouns), A (adjectives), V (verbs/relations).

**Key scripts:**

| Script | Purpose |
|--------|---------|
| `build_syn_data.py` | Main pipeline: Format-A cluster file → rewrite table + GK axioms |
| `make_anto_synonyms.py` | Build cluster files from scratch using fastText + WordNet |
| `make_gradables.py` | Library module: extract gradable adjectives from a text corpus |
| `merge.py` | Cluster merger library used by `build_syn_data.py` |

**Quick regeneration** (when `syn_*_10.txt` cluster files are updated):
```bash
cd mkdata/
venv/bin/python build_syn_data.py syn_n_10.txt N
venv/bin/python build_syn_data.py syn_a_10.txt A
venv/bin/python build_syn_data.py syn_v_10.txt V
```

See `mkdata/README.md` for full documentation including environment setup, cluster file format,
and instructions for rebuilding cluster files from scratch (~30–90 min, requires `cc.en.300.bin`).

> **Integration status:** The output files are not yet wired into the `solver/` pipeline.  When
> integration is done, `syn_rewrite_*.txt` will be loaded by `logconvert.py` and `syn_axioms_*.js`
> will be passed to `prover.py` alongside `axioms_std.js`.

---

## 10. Extending and modifying the pipeline

### Adding new predicates

1. Add the predicate to the whitelist table in `prompts/stage2_instructions.txt` (section
   `== 5. PREDICATE INVENTORY ==`).
2. Add examples to `prompts/stage2_examples.txt` showing the new predicate in context.
3. If the predicate should receive `$ctxt`, add it to `_CTXT_ELIGIBLE` in `logconvert.py`.
4. If `procproofs.py` needs to render the predicate in an explanation, add an entry to
   `_PRED_TABLE` in `proof_render.py` (or a special-case handler in `_render_atom`).

### Modifying Stage-1 parsing behaviour

Edit `prompts/stage1_instructions.txt` and add/update examples in `prompts/stage1_examples.txt`.
The most impactful sections are:
- `== 4. TYPE CLASSIFICATION ==` — when to use `real`/`situation`/`strict_rule`/`normal_rule`
- `== 12. ADJECTIVES ==` — the adjectives field format
- `== 8. SCOPE HINTS ==` — dependent/global/kind scope for generics

### Modifying Stage-2 compilation behaviour

Edit `prompts/stage2_instructions.txt` and `prompts/stage2_examples.txt`.  The most impactful
sections are:
- `== 4. QUANTIFICATION RULES ==` — how each ASU type is compiled to FOL
- The Property and Relation Predicate Selection Rule — `has degree property` vs `has property`

### Adding a new LLM provider

In `llmcall.py`, add a `call_newprovider(sysprompt, input_text, version, max_tokens)` function
following the pattern of `call_claude`, `call_gpt`, or `call_deepseek`, then dispatch from
`call_llm` when `llm == "newprovider"`.

### Improving proof post-processing

`procproofs.py` is where answer extraction and explanation rendering live.  Key extension points:
- `proof_explain.format_explanation` — generates the step-by-step English proof
- `_answer_goodness` in `procproofs.py` — the sorting key for ranking multiple candidate answers
- `_filter_by_best_tier` in `procproofs.py` — selects among concrete, Skolem, and population answers

### Running tests

```bash
python3 test.py                         # run all tests with the default LLM
python3 test.py tests/tests_core.py -llm claude
```

Each test is a `[text, expected_answer]` pair.  Add new tests to `tests/tests_core.py`.

To regenerate the logconvert pretty-print check file after changes to `logconvert.py`:
```bash
python3 run_pretty_check.py > logconvert_check.txt
```
