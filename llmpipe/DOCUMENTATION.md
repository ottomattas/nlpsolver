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
   - 5.7 [lc_sets.py](#57-lc_setspy)
   - 5.8 [procproofs.py](#58-procproofspy)
   - 5.9 [proof_render.py](#59-proof_renderpy)
   - 5.10 [proof_explain.py](#510-proof_explainpy)
   - 5.9 [proof_explain.py](#59-proof_explainpy)
   - 5.10 [prover.py](#510-proverpy)
   - 5.11 [pretty.py](#511-prettypy)
   - 5.12 [cache.py](#512-cachepy)
   - 5.13 [globals.py](#513-globalspy)
   - 5.14 [utils.py](#514-utilspy)
   - 5.15 [linguistics.py](#515-linguisticspy)
   - 5.16 [stage_sanity.py](#516-stage_sanitypy)
6. [Prompt files](#6-prompt-files)
7. [Key algorithms in logconvert.py and lc_clausify.py](#7-key-algorithms-in-logconvertpy-and-lc_clausifypy)
   - 7.1 [Package extraction](#71-package-extraction)
   - 7.2 [FOL to CNF clausification](#72-fol-to-cnf-clausification)
   - 7.3 [Defeasible expansion](#73-defeasible-expansion)
   - 7.4 [Context injection ($ctxt)](#74-context-injection-ctxt)
   - 7.5 [Gradable property normalisation](#75-gradable-property-normalisation)
   - 7.6 [Population facts](#76-population-facts)
   - 7.7 [Stage-2 rewrites and modifications](#77-stage-2-rewrites-and-modifications)
   - 7.8 [Stage sanity checks and corrective retry loop](#78-stage-sanity-checks-and-corrective-retry-loop)
   - 7.9 [Confidence and uncertainty handling](#79-confidence-and-uncertainty-handling)
8. [Configuration and options](#8-configuration-and-options)
9. [The mkdata toolkit and solver integration](#9-the-mkdata-toolkit-and-solver-integration)
   - 9.1 [What mkdata produces](#91-what-mkdata-produces)
   - 9.2 [Solver runtime files](#92-solver-runtime-files)
   - 9.3 [Solver integration](#93-solver-integration)
   - 9.4 [Full build pipeline](#94-full-build-pipeline)
   - 9.5 [Spatial and temporal preposition handling](#95-spatial-and-temporal-preposition-handling)
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
│   ├── logconvert.py    Stage-2 JSON → GK clause list (orchestration)
│   ├── lc_rewrites.py   Pre-clausification formula rewrites
│   ├── lc_ctxt.py       $ctxt injection, time handling, fresh variables
│   ├── lc_postprocess.py Post-clausification clause-list passes
│   ├── lc_clausify.py   FOL → CNF clausification
│   ├── lc_questions.py  Wh-question encoding and population facts
│   ├── lc_sets.py       Set/counting: $setof rewriting, membership axioms, element instantiation
│   ├── procproofs.py    Prover output → answer string
│   ├── proof_render.py  Proof rendering facade (re-exports from proof_utils/english/logic)
│   ├── proof_utils.py   Entity naming, Skolem resolution, render context
│   ├── proof_english.py Atom/clause → English rendering (table-driven)
│   ├── proof_logic.py   Traditional/JSON logic syntax rendering
│   ├── proof_explain.py Step-by-step proof explanation formatter
│   ├── linguistics.py   Pure English heuristics (articles, conjugation, gerunds)
│   ├── prover.py        gk binary interface
│   ├── pretty.py        JSON pretty-printer (Style B)
│   ├── cache.py         SQLite cache for LLM responses and prover results
│   ├── semnormalize.py  Semantic normalization (antonym folding + canonical substitution)
│   ├── axiom_vocab.py   Axiom file vocabulary extraction and caching
│   ├── data_canonicals.py  (generated) Tier A rewrite dict (~752 entries)
│   ├── data_antonyms.py    (generated) Antonym pairs dict (~710 entries; adjective + noun only, verbs excluded)
│   ├── data_synonyms.py    (generated) Soft synonym index (~12K words)
│   ├── data_exclusions.py  (generated) Exclusion groups + index
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
│                        event-to-relation bridges, movement/transfer results,
│                        give/receive perspective bridges, transitivity, degree entailments)
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
any work on the system.  See `ENCODINGS.md` for a detailed encoding reference with examples.

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
| `time_prep` | Temporal preposition when `time` is an explicit value: `"during"`, `"on"`, `"before"`, etc. |
| `state_tense` | `"past"`, `"present"`, `"future"` — grammatical tense when `time` holds an explicit value instead of a tense.  Generates `is_past_world(W)` for `"past"`. |
| `location` | Entity id of the location |
| `confidence` | Float 0–1 (omit for 1.0); affects `@p` metadata in Stage 2 |
| `mental_holder` / `mental_attitude` / `epistemic_force` / `attitude_target` | For propositional attitudes (`knows that`, `believes that`) |
| `definites` | List of `[REL, VALUE_ID, ARG_ID]` for definite descriptions (`"the handle of the fork"`).  Triggers `$theof1` function term rewrite in logconvert (see §7 post-clausification table). |

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
| Events | `isa "activity" E`, `has type E VERB`, `has actor E ENTITY`, `has target E ENTITY`, `has location E ENTITY PREP`, `has instrument E ENTITY`, `has manner E MANNER`, `has direction E DIR`, `has time E TIME PREP`, `typical E`, `typically ENTITY VERB` |
| World | `holds W F`, `next W1 W2`, `before W1 W2` (axiom-derived), `state time W T`, `state location W L` |
| Defeasible | `normally FORMULA` |
| Mental | `kb K HOLDER ATTITUDE W`, `kb force K FORCE`, `kb holds K FORMULA`, `kb says K1 K2 FORMULA` |
| Sets | `$setof VAR [and CONDITIONS]`, `$setof VAR SET_ID [and CONDITIONS]`, `$count SETOF_TERM`, `member ENTITY SETOF_TERM`, `isa "set" S`, `is set of TYPE S` |
| Definite functions | `$theof1 TYPE SUBJECT CTXT` — canonical function term for "the TYPE of SUBJECT" (generated by logconvert from `definites`).  For measurements, Stage 2 outputs `$measure_of ATTR OBJ WORLD` (ground) with `$measure NUMBER UNIT`; pipeline converts to `$list NUM "#:UNIT"` in canonical units. |
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

**Confidence:** Some clause dicts also carry `"@confidence": 0.8` (from `@p` metadata or
Stage-1 `confidence`).  The value is an **evidence** score in [−1, 1] (probability `p`
mapped via `2p − 1`) and is distributed across the ASU's clauses using the three-tier
anchor scheme documented in §7.9.

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

Eligible predicates (`CTXT_ELIGIBLE` in `lc_ctxt.py`): `has property`, `have`, `has part`,
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

When a defeasible rule also carries a Stage-1 `confidence` (e.g.
`"Elephants normally have trunks, probability 0.8"`), the `$block`-bearing clauses
are the preferred anchors for the uncertainty; see §7.9 for the full distribution
scheme.

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
3. Normalises entity IDs via `_normalize_entity_id_case`: merges IDs that differ only
   by first-character capitalisation (e.g., `"Car 1"` at sentence start vs `"car 1"`
   mid-sentence) when the ID has a number suffix and the capitalised form appears at
   sentence start.
4. Serialises Stage-1 output as JSON string; passes it as input to `_run_stage(2, ...)`.
5. Returns both parsed objects plus a stats dict.

**`_run_stage`** handles robustness:
- Calls `llmcall.call_llm`.
- Tries `json.loads` on the raw response.
- If that fails, applies `fix_json` (heuristic repairs: strip markdown fences, remove Python
  literals, balance brackets, strip trailing junk, etc.).
- If still invalid, makes one LLM retry with error feedback in the prompt.
- After a successful parse, invokes a per-stage **sanity checker** (`check_stage1` /
  `check_stage2` from `stage_sanity.py`) and, if it reports issues, enters a separate
  corrective-retry loop via `_maybe_sanity_retry` (see §7.8 and §5.16 for details).
- Tracks all events in the stats dict (`s1_calls`, `s1_json_errors`, `s1_json_fixes`,
  `s1_retry_calls`, `s1_sanity_retries`, `s1_sanity_ok`, `s1_sanity_fail`, etc.).

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
geminiversion    = "gemini-2.5-flash"
deepseekversion  = "deepseek-chat"     # V3.2; "deepseek-reasoner" for thinking
temperature      = 0
default_max_tokens = 8000
max_retries      = 3
```

API keys are read from plain-text files in `../secrets/` (relative to `llmpipe/`):
`gpt_secrets.txt`, `claude_secrets.txt`, `gemini_secrets.txt`, `deepseek_secrets.txt`.
The directory path is set once via `_secrets_dir` in `llmcall.py`.

### 5.4 logconvert.py and supporting modules

**Role:** Main driver for logic conversion — orchestrates the full Stage-2 JSON → GK clause
list pipeline.  The computation is split across several files:

| Module | Responsibility |
|--------|---------------|
| `logconvert.py` | Orchestration: package extraction, question/assertion dispatch |
| `lc_rewrites.py` | Pre-clausification formula rewrites (meta-predicate normalization incl. `"time of"`→`has_time`, tense-valued `has_time` stripping, verb normalization: travel/journey/move→go, hand/pass/send→give, receive→give with actor↔recipient swap, existential hoisting, spurious `can` removal, polarity flip) |
| `lc_ctxt.py` | `$ctxt` injection, time-wrapper stripping, fresh variable generation |
| `lc_postprocess.py` | Post-clausification clause-list passes (gradable normalization, RELCLASS coercion, `$theof1`, possessive `have`, population facts, degree stripping) |
| `lc_clausify.py` | FOL→CNF compilation |
| `lc_questions.py` | Question encoding and population fact builders |
| `lc_sets.py` | Set/counting: `$setof` rewriting, membership axioms, element instantiation |

**Key function:** `rawlogic_convert(logic, s1_json=None) -> list | None`

Converts the Stage-2 nested JSON formula into a flat GK clause list:

```
["and", ["@id","S1",PACKAGE], ...] (Stage-2 input)
    │
    ├─ _hoist_nested_ids(logic)           extract @id blocks nested by LLM bracket errors
    ├─ _build_asu_index(s1_json)          build unit_id→ASU lookup from Stage 1
    ├─ rewrite_meta_predicates(logic)     [lc_rewrites] "located in"→"in", "is"→isa, "time of"→has_time, travel/journey/move→go, hand/pass/send→give
    ├─ normalize_receive_events(logic)   [lc_rewrites] receive→give with actor→recipient swap
    ├─ strip_tense_has_time(logic)       [lc_rewrites] remove has_time(E,"past",...) bogus atoms
    ├─ inject_degree_presuppositions()    [lc_rewrites] "not very X" → X and not very X
    ├─ populate_clauses(items)            [lc_postprocess] collect background facts
    │
    ├─ for each @id item:
    │    _convert_id_package(item, asu_index)
    │        _extract_package_ctx()        unpack PACKAGE: formula, world, tense, etc.
    │        override with Stage-1 ASU data (tense, world, location)
    │        compute latest world numerically for queries without pre_state
    │        default question tense to "present" when Stage 1 omits "time"
    │        generate $theof1/$datetime fact for explicit time values
    │        inject event has_time from Stage 1 if missing (repair for LLM omission)
    │        generate is_past_world(W) from state_tense="past"
    │        strip_spurious_can()          [lc_rewrites] remove non-modal "can"
    │        hoist_misnested_exists()      [lc_rewrites] fix variable scoping
    │        _process_question()           wh-/yes-no question dispatch [→ lc_questions]
    │        _process_assertion()          clausify + three-tier confidence distribution (§7.9) [→ lc_clausify]
    │        inject $ctxt into result      [lc_ctxt]
    │
    ├─ rewrite_definites() (global)        [lc_postprocess] $theof1 for all ASU definites
    ├─ rewrite_measure_terms()            [lc_postprocess] $measure→$list, less_measure rewrite, $theof1 unwrap in $measure_of
    ├─ insert population facts before first @question
    ├─ generate "what" population facts     for @what_query: isa(CLASS,$some_CLASS) from witnesses
    ├─ inject $ctxt into population facts  [lc_ctxt]
    ├─ normalize_gradable_predicates()    [lc_postprocess]
    ├─ strip_isa_entity()                 [lc_postprocess]
    ├─ coerce_relclass()                  [lc_postprocess]
    ├─ strip_degree_predicates()          [lc_postprocess] (only if -simpleproperties)
    └─ strip @sourcetype                  remove internal annotation before prover
```

**Counter globals** (reset at the start of each `rawlogic_convert` call):

- `lc_clausify._skolem_nr`, `lc_clausify._gobj_nr` — Skolem and generic-object counters
- `lc_questions._defq_nr` — `$defq` predicate name counter
- `lc_ctxt._fv_nr` — fresh free-variable counter (`?:Fv1`, `?:Fv2`, …)

See §7 for detailed discussion of the key algorithms.

### 5.5 lc_clausify.py

**Role:** FOL → CNF clausification compiler.

**Public API used by `logconvert.py`:**

- `clausify(formula) -> list` — converts a first-order formula to a list of CNF clauses
- `looks_like_var(s) -> bool` — true if `s` matches Stage-2 variable pattern (`?:`-prefixed or single uppercase letter + digits) but NOT world constants
- `is_world_constant(s) -> bool` — true if `s` matches `W0`, `W1`, etc. (excluded from variable detection)
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

### 5.7 lc_sets.py

**Role:** Programmatic conversion of Stage-2 `$setof` terms into canonical form,
generation of membership axioms, and element instantiation.

**Entry point:** `process_sets(formula)` — called before clausification.  Returns
`(rewritten_formula, axioms, element_clauses)`.

**Two $setof forms:**

| LLM output | Canonical form | When |
|------------|---------------|------|
| `["$setof","?:X",["and",...conds with have...]]` | `["$setof","have","John 1",["$and",...$-prefixed...]]` | Stative anchor found (have, is_rel2, can) |
| `["$setof","?:X","set 1",["and",...conds...]]` | `["$setof","id","set 1",["$and",...conds...]]` | No anchor, set_id from Stage-1 |

**Conversion steps** (inside-out for nested $setof):
1. Detect anchor predicate in conditions; extract it
2. Replace bound variable with `$arg1` (`$arg2` for nested)
3. `$`-prefix predicates in anchored form; no prefix for conditions-only
4. Sort `$and` entries: `$isa`/`isa` first, rest alphabetically
5. Mutate the $setof node in place

**Membership axiom generation:** For each unique $setof pattern, a
`forall/biconditional` axiom is generated:
```
member(?:M, $setof(have, ?:S, [$and, $isa(?:C,$arg1), $prop(?:P,$arg1)]))
  <=> isa(?:C, ?:M) & prop(?:P, ?:M) & have(?:S, ?:M)
```
Concrete values in conditions are generalized to forall variables.

**Element instantiation:** For each positive `["=", N, ["$count", $setof_term]]`
in an assertion context (inside `holds`, not in queries), creates
`min(N, set_element_limit)` concrete element constants (`$setK_elI`) with:
- All set properties (un-prefixed predicates)
- Anchor predicate (if anchored)
- `member` assertions
- Pairwise distinctness (`["-=", el1, el2]`)

Configurable via `globals.options["set_element_limit"]` (default 3).

**Key functions:**
- `_classify_setof(conditions, var)` — detect anchor predicate
- `_rewrite_setof(node, depth)` — rewrite one $setof to canonical form
- `_build_membership_axiom(info)` — generate the forall/biconditional
- `_instantiate_elements(info, source_name, count)` — create element clauses
- `_instantiate_distributive_events(formula, setof_term, elements, source_name)` —
  create per-element event instances from forall/implies/member blocks

### 5.8 procproofs.py

**Role:** Post-processing of raw prover output into a human-readable answer.

**Key function:** `process_proof(proof_result, text=None, s1_json=None, logic=None, options=None) -> str`

1. Parses the raw prover JSON string.
2. Checks for `"result": "answer found"`.  Returns `"Unknown."` if not found.
3. Sorts answers by `_answer_goodness` (confidence desc, proof length asc).
4. Filters to the best object-type tier: concrete entities > Skolem constants > population facts.
   For `@what_query`: prefers population (class) over concrete (instance).
   Resolves Skolem function answers to class names via `get_skolem_fn_type`.
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

### 5.9 Proof rendering modules

Proof rendering is split across four files, with `proof_render.py` as a thin facade:

| Module | Role |
|--------|------|
| `proof_render.py` | Facade — re-exports public API from the three implementation modules |
| `proof_utils.py` | Entity naming, Skolem type resolution, render context state, ambiguity detection |
| `proof_english.py` | Atom/clause → English rendering; table-driven via `_PRED_TABLE` |
| `proof_logic.py` | Traditional `pred(arg,...)` and JSON logic syntax rendering |

Per-proof mutable state (entity map, ambiguous names, Skolem type annotations) is bundled in a
`RenderContext` class (`_ctx` module-level instance) in `proof_utils.py`.

Atom-to-English rendering in `proof_english.py` is table-driven via `_PRED_TABLE`, a dict mapping
predicate names to `(arity, pos_renderer, neg_renderer)` tuples.

See `PROOF_RENDERING.md` for a detailed description of the rendering principles,
entity naming rules, clause rendering, and proof explanation structure with examples.

**Public API** (all importable from `proof_render.py`):

- `compute_ambiguity(logic)` — scan clause list for ambiguous entity names [`proof_utils`]
- `compute_skolem_types(proof, logic=None)` — populate Skolem type tables from logic + proof [`proof_utils`]
- `set_entity_map(entity_map)` — set entity display map [`proof_utils`]
- `get_entity_display(key)` — look up display name [`proof_utils`]
- `entity_name(val, with_url, proof_mode)` — format entity for display [`proof_utils`]
- `ans_atom_name(atom)` — format answer atom [`proof_english`]
- `clause_to_str(clause)` — clause → English string [`proof_english`]
- `block_to_english(blocker)` — `$block` → English exception string [`proof_english`]
- `format_clause_logic(clause)` — clause → compact JSON [`proof_logic`]
- `format_clause_traditional(clause)` — clause → traditional logic syntax [`proof_logic`]
- `formula_to_logic(formula)` — FOL formula → traditional syntax [`proof_logic`]

### 5.10 proof_explain.py

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

**Auto strategy selection** (`_auto_strategy`): when no `-strategy` flag is given,
analyses the clause list for equalities with function terms (`$measure_of`, `$theof1`,
`$list`, `$datetime`) or `less_measure` atoms.  When found, selects the `unit` strategy
(`-strategytext`) which handles equational reasoning better than the default
`negative_pref/posunitpara` strategy (empirically better than
`negative_pref/knuthbendix_pref` on complex multi-existential queries).
Printed with `-debug`.  Alternate strategies worth trying on timeout-suspected cases:
`{"strategy": ["unit"], "query_preference": 1}` and
`{"strategy": ["query_focus"], "query_preference": 1}`.

**Prover seconds auto-estimation** (`_estimate_seconds`): when no CLI `-seconds` is
given, counts distinct world constants (W0, W1, ...) in the clause list and scales
the time limit from an empirical table (2x safety multiplier).  Examples: ≤6 worlds →
2s (default), 7 → 4s, 8 → 10s, 9 → 20s, 10 → 60s, 11 → 300s.  CLI `-seconds N`
always overrides the estimate.

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

**Role:** Pure English linguistic heuristics used by `proof_english.py` for human-readable output.
No dependency on proof state or any other pipeline module.

- `indef_article(word) -> str` — returns `"an"` before vowel sounds, `"a"` otherwise
- `conjugate_verb(v) -> str` — third-person singular present tense (`fly` → `flies`)
- `make_comparative(adj) -> str` — comparative form (`nice` → `nicer`, `beautiful` → `more beautiful`)
- `to_gerund(verb) -> str` — gerund form (`run` → `running`, `bite` → `biting`)

### 5.16 stage_sanity.py

**Role:** Structural sanity checks for Stage-1 ASU JSON and Stage-2 logic JSON, used by
`llmparse._maybe_sanity_retry` to detect LLM output errors that the Stage prompts explicitly
forbid (or that the downstream pipeline cannot handle) and trigger a corrective re-call of
the same LLM.  See §7.8 for the retry-loop semantics and motivation.

**Public API:**

- `Issue(kind, location, description, evidence)` — frozen dataclass representing a single
  detected problem.  `kind` is the category (e.g. `free_variable`); `(kind, location)` is the
  fingerprint used to detect persistence across retries; `description` and `evidence` are
  shown to the LLM in the corrective prompt.
- `check_stage1(s1_json) -> list[Issue]` — runs all registered Stage-1 checks (currently
  empty; framework in place).
- `check_stage2(logic, s1_json=None) -> list[Issue]` — runs all registered Stage-2 checks
  (see table below).
- `format_retry_suffix(issues, flawed_parsed) -> str` — builds the text appended to the
  original stage input when re-calling the LLM.  Structure: shows the LLM's flawed output,
  lists the issues (kind + location + description), then asks for a corrected JSON.
- `issue_fingerprints(issues) -> frozenset[tuple[str,str]]` — persistence-comparison helper.

**Registered Stage-2 checks:**

| Check | Kind | Triggers on | Example case |
|---|---|---|---|
| `_check_stage2_free_variables` | `free_variable` | Any atom-argument string that matches a binder name (`forall`/`exists`/`ask`) elsewhere in the formula but is outside the binder's scope. | Case 259 — donkey anaphora |
| `_check_stage2_misplaced_meta_tense` | `state_time_in_body` | `["state time", W, TENSE]` atom inside a `holds`/`question`/`ask` body.  Tense metadata belongs at package level, not as a body literal. | Case 37 |
| `_check_stage2_dropped_specific_noun` | `dropped_specific_noun` | Query `exists VAR, (and ... isa(CAT, VAR) ...)` where Stage-1 has a unique generic entity with `category=CAT` and `id != CAT` — the query lost the specific noun. | Case 136 |
| `_check_stage2_arities` | `wrong_arity` | Atom whose arity disagrees with the declared Stage-2 signature (whitelist of 27 predicates: `isa/2`, `has property/2`, `has type/2`, `has actor/2`, `has part/2`, `is rel2/3`, `has degree property/4`, `has degree rel2/5`, `typical/1`, etc.). | Scattered |
| `_check_stage2_event_shapes` | `event_missing_activity_isa` / `event_missing_role` | Event variable E used as first arg of `has_type(E, VERB)` must have `isa("activity", E)` AND at least one thematic-role atom (any of `has_actor`, `has_target`, `has_recipient`, `has_source`, `has_destination`, `has_location`, `has_instrument`, `has_manner`, `has_direction`, `has_time`, `has_beneficiary`, `has_accompaniment`, `has_path`, `has_result`, `has_topic`, `has_cause`, `typical`) in the same `and` conjunction.  Either missing item is its own issue. | — |
| `_check_stage2_missing_question` | `missing_question` | A Stage-1 unit is a query (either `unit.type == "query"` or its parent package's `raw` text contains `?`) but the matching `@id` in Stage-2 has no `question`/`ask` wrapper anywhere in its body — covers both whole-package truncations and `holds`-where-`question`-was-expected. | LLM truncation on multi-sentence inputs |

**Conventions:**

- Checks are pure functions over the parsed JSON; they do not mutate or consult other
  pipeline state.
- When a check also has a downstream post-processing rescue (e.g., `strip_tense_has_time` for
  misplaced meta-tense, `inject_query_specific_noun_isas` for dropped specific nouns), the
  sanity check takes priority: a successful retry produces cleaner Stage-2 output, and the
  post-processor silently no-ops on the corrected formula.
- Checks that overlap with benign LLM-prompt examples are deliberately omitted.  For
  instance, `["has time", E, "past", "in"]` is labelled WRONG in the Stage-2 instructions
  but appears in the examples file; LLMs emit it consistently, so no check fires —
  `strip_tense_has_time` handles it cheaply.

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

Context injection can be disabled globally with `nocontext_flag`.  In that mode the
constant `"$c"` is injected as the last argument of every eligible atom (instead of
a `$ctxt` term), so axioms with `?:Ctxt` still unify while axioms with explicit
`$ctxt(...)` patterns become inert.

#### Question-specific past↔present tense bridges

For each question package, after `$ctxt` injection, `lc_ctxt.build_question_tense_bridges`
walks the question's body→defq clauses, finds present-tense or past-tense stative
literals, and emits one specialized bridge axiom per unique (predicate, args) signature:

```
[-pred(args, $ctxt(opposite_tense, ?:W, ...)),
  pred(args, $ctxt(question_tense, ?:W, ...)),
  $block(0, $not(pred(args, $ctxt(question_tense, ?:W, ...))))]
```

Entity arguments are pinned to the constants from the question; free variables in the
question literal become fresh variables in the bridge.  Confidence per predicate:
0.97 for `have`, 0.95 for `is rel2` and `has degree rel2`, 0.99 for the others
(`has property`, `has degree property`, `has part`, `can`).

This replaces the disabled global Section 6a same-world tense bridges in
`axioms_std.js`.  Pinning entities keeps the search space small (the bridge can only
fire on facts about those specific entities), avoiding the prover slowdown caused by
the global axioms while bridging the same set of tense mismatches between
past-tense assertions and present-tense questions (and vice versa).

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

**Compound witnesses.** When a rule's antecedent is a conjunction binding the same variable
to multiple atoms, `_scan_compound_antecedent` records a *compound witness* and the population
emits an intersection entity satisfying ALL the conjuncts simultaneously. Two flavors today:

- **Spatial**: `[isa, TYPE, X] ∧ [is_rel2/has_degree_rel2, prep, X, ground_target]` →
  `$some_<type>_<prep>_<location>` with both atoms.
- **Adjective**: `[isa, TYPE, X] ∧ [has_property, ATTR, X]` (or `has_degree_property` with
  intensity/relclass) → `$some_<attr>_<type>` with both atoms. Without this, defeasible
  rules of the form "ADJ TYPEs are not P" have no concrete witness for the prover to apply
  them to (case 74: "Red cars are not nice" was being closed via the more general
  "Cars are nice" rule alone, returning "Probably true" instead of the expected False).

### 7.7 Stage-2 rewrites and modifications

The pipeline applies several transformations to the raw Stage-2 LLM output before and after
clausification.  These compensate for LLM inconsistencies, enforce pipeline conventions, and
bridge representation gaps.

**Pre-clausification rewrites** (on the raw Stage-2 JSON formula, before `clausify`):

| Rewrite | Where | Example | What it does |
|---------|-------|---------|-------------|
| Degree presupposition injection | `lc_rewrites.inject_degree_presuppositions` | "John is not very big" → adds "John is big" (unmarked degree) alongside the negated "very big" | `["not",["has degree property",P,E,"high",C]]` → `["and",["has degree property",P,E,"none",C],["not",...]]` |
| Stative event rewriting | `semnormalize.rewrite_stative_events` | "John had a car" encoded as an event → rewritten to direct `have(john,car)` | Replaces Davidsonian event encoding of stative verbs (have, own, like, love, etc.) with direct predicates.  Safety: only rewrites when the event variable has no extra properties (has_location, etc.) |
| `@time` stripping | `lc_ctxt.strip_time_wrappers` | "John was tall" — the past-tense `@time` wrapper becomes a `$tense` sentinel controlling the tense slot in `$ctxt` | Converts `["@time","past",ATOM]` wrappers into `$tense` sentinels on the atom |
| Entity category injection | `logconvert._build_entity_category_clauses` | "John is an elephant" — Stage-1 says John's category is "person", so `isa(person, John 1)` is added even though Stage-2 only emits `isa(elephant, John 1)` | Adds `isa(CATEGORY, ENTITY)` facts from Stage-1 entity annotations.  Skipped when the entity already has a **positive-polarity** isa in Stage-2 (`_collect_positive_isa_entities` tracks polarity through connectives, negation, implications, and low-confidence packages).  Entities in negated or low-confidence contexts are NOT skipped — they need the injection.  Exact duplicates with `sent_S*` clauses are removed by `_dedup_entity_clauses`. |
| Entity base-word isa | `logconvert._build_entity_category_clauses` | "A man had a car" — entity `man 1` has category "person", but the base word "man" is also a type; adds `isa(man, man 1)` alongside `isa(person, man 1)` | For concrete entities with a lowercase base word different from the category, injects `isa(BASE, ENTITY)` so queries using the descriptive type word can match |
| Compound subsumption | `lc_postprocess.build_compound_subsumption` | "Baby birds do not fly" — adds a rule that baby birds are birds, so general bird rules can apply to them | Adds `isa(BASE, X) :- isa(COMPOUND, X)` rules for compound types |

**Post-clausification modifications** (on the GK clause list):

| Modification | Where | Example | What it does |
|-------------|-------|---------|-------------|
| `$ctxt` injection | `lc_ctxt.inject_ctxt_into_objs` / `inject_ctxt_question` | "John was tall" → atom gets `$ctxt(past,W0,?,?)` anchoring it to the past in world W0 | Appends `["$ctxt",T,W,L,K]` to eligible predicate atoms.  Rules: all-free-var.  Assertions: concrete world/tense.  Questions: see next row (§7.4) |
| Descriptive/stative/dynamic split | `lc_ctxt.inject_ctxt_question` | "Did the man have the red car which a woman bought?" — `bought` events and `red` property each get independent free-var worlds; stative `have` also gets free-var world; only dynamic event predicates (if matrix) keep the query's world | Three-way $ctxt world dispatch in `$defq` questions: (1) **descriptive** atoms (isa, event atoms, properties when a main relation is present) each get an independent free-var world; (2) **stative matrix** predicates (have, can, has part) get free-var world — persistent states don't need concrete world anchoring; (3) **dynamic matrix** predicates (is_rel2, properties when no main relation) keep the query's world.  `_question_has_main_relation` detects whether properties are restrictive modifiers.  Each descriptive/stative atom gets its OWN fresh world variable to avoid forced co-unification across different world states |
| Gradable normalisation | `lc_postprocess.normalize_gradable_predicates` | "John is big" — LLM used `has property(big,...)` but "big" is in the gradable whitelist → upgraded to `has degree property` | Whitelist-based `has property` ↔ `has degree property` conversion; replaces `"entity"` and `"none"` relclass with free variables (§7.5) |
| `isa entity` stripping | `lc_postprocess.strip_isa_entity` | "Every entity that is big is strong" — `isa(entity,X)` is always true, so the clause is a tautology → removed | Removes tautological `isa(entity,X)` literals (§7.5) |
| RELCLASS coercion | `lc_postprocess.coerce_relclass` | (question) "Is John big?" — query uses relclass "person" (John's category) but the rule uses "bear" → relclass replaced with free variable; (assertion) "John is a nice big bear. John is nice." — stage-1 split loses the "bear" context and tags "nice" with relclass "animal" while the rule expects "bear" → assertion's "animal" replaced with a free variable | Fixes relclass mismatches. Question-side: `has degree rel2` always coerces to free var; `has degree property` coerces when the relclass is one of the entity's isa classes and no matching rule exists. Assertion-side (new): coerces when the fact's relclass is either (a) one of the entity's multiple isa classes while another class of the entity also appears as a rule-side relclass for the same property, or (b) not in the entity's isa classes while some isa class of the entity appears as a rule-side relclass — both symptoms of stage-1 generic-category leakage. `prop_relclasses` is built from both positive and negated literals so rule bodies contribute. |
| `$theof1` definite rewrite | `lc_postprocess.rewrite_definites` | "The father of John is nice" — `"the father 2"` → `["$theof1","father","John 1",CTXT]` throughout all clauses; `is_rel2` clause removed; per-relation `isa`/`is_rel2` bridge axioms generated as `frm_theof`; grounded `have(arg,$theof1,ctxt)` fact emitted for the concrete owner | Replaces flat entity IDs for definite functional descriptions with canonical function terms so that "the father of John", "John's father", and wh-queries all refer to the same term.  Triggered by Stage-1 `definites` field.  Primary: matches `is_rel2` clause.  Fallback: matches `have` + `isa` pair.  The formerly-universal `have` bridge in `axioms_std.js` (`[have, ?:S, $theof1(?:R,?:S,?:C), ?:C]`) has been removed because its free `?:S` let the prover satisfy any wh-possession query with a free-variable witness; `rewrite_definites` now emits the needed grounded possession fact directly. |
| Possessive `have` inference | `lc_postprocess.add_possessive_have` | "The handle of the fork" — `is_rel2(handle of, fork, handle)` + `isa(handle, handle)` → `have(fork, handle)` | Infers `have(Y,E,CT)` from possessive `is_rel2` patterns.  Handles ground entities, Skolem functions, and `$theof1` terms.  For rule clauses with guard literals (e.g., `[-isa,elephant,?:X]`), generates conditional `have` with the same guard.  Skips `@name=frm_theof` clauses (the universally-quantified per-relation schema axioms) because processing them would regenerate the universal have bridge that was removed for free-variable-witness reasons (see `$theof1` definite rewrite row above). |
| `have` → `has_part` bridge for typed body-part nouns | `lc_postprocess.add_haspart_for_typed_have` | Rule "If an animal has a trunk, it is an elephant" Stage-2-encoded with `-has_part(?:X,?:Y,Ctxt)` and `-isa(trunk,?:Y)`; fact "John has a long trunk" Stage-2-encoded as `have(John 1, trunk 1, Ctxt)` + `isa(trunk, trunk 1)` → emit `has_part(John 1, trunk 1, Ctxt)` so the rule fires (case 207). | **Conservative, problem-local bridge.**  Stage-2 LLM is inconsistent: generic universal claims ("Elephants have trunks") use `has_part`, but specific instance claims with adjectives ("John has a long trunk") often use `have` for some LLMs (gemini, gpt) — which then fail to unify with has_part-using rules.  Pass 1 walks rule clauses and collects the set of types T paired with `-has_part(?:X,?:Y)` AND `-isa(T,?:Y)` for the same `?:Y`; if empty, the bridge does nothing.  Pass 2 collects explicit `isa(T, E)` facts for ground/Skolem entities.  Pass 3 walks single-atom positive `have(X, Y, Ctxt)` clauses; for each, looks up Y's type (explicit isa first; else `_parse_entity_name_type` fallback peels off Stage-2's naming convention "trunk 1" → "trunk", "sk0_trunk" → "trunk") and emits `has_part(X, Y, Ctxt)` only when the type intersects the rule-collected set.  Safe under the subtype rule in `axioms_std.js` because that rule requires `isa(Y1, Y2)` where Y1 is a class with subtypes; specific entities are not classes so the inheritance never propagates back to a class. |
| Misnested existential hoisting | `lc_rewrites.hoist_misnested_exists` | `[exists E, [and, has_actor(E,X), [exists X, isa(bear,X)]]]` → `[exists E, [exists X, [and, has_actor(E,X), isa(bear,X)]]]` | Pre-clausification fix for assertion formulas.  Detects existential variables used free in sibling conjuncts before their `exists` binding, hoists the binding to wrap the entire conjunction.  Only applies in assertion contexts (from `holds`), with collision checks against enclosing bindings. |
| Spurious `can` removal | `lc_rewrites.strip_spurious_can` | "Did bears eat berries?" — removes `["can",X,E]` from event query when no modal language in ASU text | Pre-clausification pass on question formulas.  Fires when `can(X,E)` appears alongside `isa(activity,E)` and `has_actor(E,X)` in the same conjunction, both X and E are existentially quantified, and the ASU text contains no modal words (can, could, able, may, might, etc.). |
| Meta-predicate normalization | `lc_rewrites.rewrite_meta_predicates` | `["is rel2","is",A,B]` → `["isa",A,B]`; `["is rel2","=",A,B]` → `["=",A,B]`; `["is rel2","located in",A,B]` → `["is rel2","in",A,B]` | Pre-clausification rewrite applied to all formulas.  Normalizes copula (`is` → `isa`), identity (`=`), spatial meta-predicates (`located in/at/on/near/above/under` → bare preposition), movement verbs (travel/journey/move → go), placement verbs (place/set/lay/position/deposit → put), and transfer verb synonyms (hand/pass/send → give).  Also normalizes 3-arg `has_destination(E,Dest)` to 4-arg `has_destination(E,Dest,"at")` for backward compat with stale Stage-2 cache entries. |
| Perspective verb → dative head normalization | `lc_rewrites.normalize_receive_events` | `["has type",E,"receive"]` + `["has actor",E,X]` → `["has type",E,"give"]` + `["has recipient",E,X]`.  Same pattern for hear→tell, see→show, get→give. | Formula-level rewrite: in `and`-blocks containing a perspective-verb event (receive, get, hear, see), the verb is changed to its dative head (give, tell, show) and the actor role is swapped to recipient.  Single mapping table `_PERSPECTIVE_TO_DATIVE`; function name retained for back-compat.  Asymmetry preserved — the rewrite never adds an actor for events lacking an explicit dative agent, so "Did John receive a book?" still fails when John was the giver.  Allows the give-based transfer axioms in `axioms_std.js` to derive `have(Recipient, Object)` in the next world state, and lets queries about hear/see/get match facts about tell/show/give. |
| Set existence fact | `lc_sets._walk_for_count` | "Bears ate berries" with `forall/implies/member/$setof` in assertion context → `member("$some_bear", $setof(...))` | Generates a ground set membership fact for assertion-context `forall/member` patterns so the prover can bootstrap resolution through member-guarded clauses.  Skipped when the set already has element instantiation from a count assertion. |
| Degree stripping | `lc_postprocess.strip_degree_predicates` | With `-simpleproperties`: `has_degree_property(big,X,none,animal)` → `has_property(big,X)` | (Only with `-simpleproperties`) Replaces degree predicates with simple property predicates |
| Semantic normalisation | `semnormalize.sem_normalize_clauses` | "The ball is outside the box" → `outside` is antonym of `inside` → flips polarity and substitutes: `-is_rel2(inside,ball,box)` | Antonym resolution (~710 pairs, adjective + noun only: flip polarity + swap word) and canonical substitution (~752 pairs: synonym → canonical form).  Skips `$ctxt` terms.  Polarity-flipping is applied ONLY at the top-level literal — inside nested function terms (`$theof1`, `$measure_of`, Skolem), only canonical substitution runs (flipping `$theof1` to `-$theof1` would produce invalid terms).  Data loaded from generated `data_antonyms.py` and `data_canonicals.py`.  Verb antonyms (`ant_v.txt`) are intentionally excluded from rewriting — most are perspective inversions (give/take, buy/sell), process complementarities (start/stop, come/go), or weak pairs where polarity-flip is wrong, and key verbs collide with axiom-vocab predicates (case 171).  Useful verb subsets (attitude pairs like like/dislike) are scheduled for re-introduction via a defeasible attitude-mutex injector.  `build_antonyms` also skips any pair whose canonical target is itself a CANONICALS key — such chain-through pairs are deferred to `build_exclusions` and emitted as synthetic `ANT_<W1>_<W2>` exclusion groups instead (prevents Pass 2 from chain-substituting the fold target to an unrelated sense, e.g. `open→close→near`). |
| Soft synonym injection | `lc_postprocess.inject_soft_synonyms` | "The car is red" + axioms mention "crimson" → emits `red(X,Ct) <=> crimson(X,Ct)` biconditional | Dynamic injection of Tier B synonym axioms for words present in both input and axiom vocabulary.  Templates: `has property` (adj), `isa` (noun), `has type` (verb). |
| Exclusion injection | `lc_postprocess.inject_exclusion_axioms` | "The car is blue. Was it red?" → emits `NOT blue(X,Ct) OR NOT red(X,Ct)` with `$block` | Dynamic injection of mutual-exclusion axioms from `excl_a.txt` groups.  `needs_blocker=True` groups use defeasible `$block`; `False` groups are hard exclusions. Four atom shapes: default `has_property` (adjective); `_IS_REL2_EXCL_GROUPS` (MONTH/DAY_OF_WEEK/SEASON) — `is_rel2` target at arg 3; `_IS_REL2_PREP_GROUPS` (SPATIAL_*, TEMPORAL_ORDER) — `is_rel2` preposition at arg 1 with two free entity variables; `_HAS_DEGREE_REL2_PREP_GROUPS` (PROXIMITY) — `has_degree_rel2` preposition at arg 1 with two asymmetric axioms per pair. Also injects `MANUAL_ANTONYMS` adjective pairs as synthetic `MANUAL_ADJ_<W1>_<W2>` groups, and chain-rejected antonym pairs (from `build_antonyms`) as synthetic `ANT_<W1>_<W2>` defeasible adjective groups. See §9.5 for preposition handling. **Note**: the seven preposition groups in `_STATIC_PREP_EXCL_GROUPS` (SPATIAL_VERTICAL/_OVER_UNDER/_SAGITTAL/_CONTAINMENT/_LATERAL, TEMPORAL_ORDER, PROXIMITY) are skipped here — their mutual-exclusion axioms live statically in `axioms_std.js` §7e because both sides are first-class predicates in the standard ontology. |
| World-graph geometry | `lc_postprocess.inject_world_geometry` | "Mary slept. Mary is awake. Was Mary awake?" → emits `next(W0,W1)` | Dynamic injection of the minimal `next(Wi,Wi+1)` chain spanning the concrete world constants actually present in the clause list. Replaces the static `W0..W12` chain that used to live in `axioms_std.js` §11. Skips emission entirely when ≤1 world is present (most single-tense problems); otherwise fills any gaps in `[min_idx, max_idx]` so `before` transitivity still closes. Keeps the `before` derivation graph small. |
| `@sourcetype` stripping | Serialisation (`clause_list_to_json`) | Population facts carry `@sourcetype:"populate"` internally for processing — stripped before the prover sees them | Internal `@sourcetype` tags are excluded from prover input |

---

### 7.8 Stage sanity checks and corrective retry loop

LLMs occasionally produce Stage-2 output that violates constraints the prompt explicitly
forbids — for example, free variables (case 259, "Every farmer who owns a donkey beats it"
where gemini leaves `Y` unbound in the consequent).  Rather than add a post-processing
rewrite for each such quirk, `llmparse.py` runs a **sanity checker** on every Stage-1 and
Stage-2 parse and, when issues are detected, re-calls the same LLM with the original prompt
plus the flawed output and a description of what went wrong.

**Mechanism** (in `llmparse._maybe_sanity_retry`):

1. After a Stage-N parse succeeds, call `check_stage<N>(parsed)`.  If the issue list is
   empty, return immediately.
2. Otherwise, fingerprint the issues by `(kind, location)` and enter the retry loop.
3. **Attempt 1 (corrective retry).**  Build a prompt = original input + `format_retry_suffix`
   (shows the flawed output and lists the issues).  Call the LLM.  Parse (with `fix_json`
   fallback) and re-check.  If clean, return.
4. **Attempt 2 (final retry).**  Only if attempt 1 produced issues that are **all new**
   (no fingerprint overlap with attempt 0).  Persistent issues → stop (retry not
   productive).  If cap reached, return best-effort output; downstream passes handle
   residual imperfections.
5. **Hard cap:** 2 corrective retries per stage.  The initial call plus 2 retries = 3 LLM
   calls max per stage.

**Cache interaction:** each retry input is a longer string (original + suffix describing the
flaw), so it hashes to a distinct cache key via `cache.make_llm_cache_key`.  Retries benefit
from the normal cache: a repeated run with the same input and flawed first response will
reuse the cached retry instead of re-calling the LLM.

**Stats tracked** (per stage, added to the `parse_text` stats dict):

- `sN_sanity_retries` — number of corrective LLM calls made.
- `sN_sanity_ok` — number of attempts that produced clean output (at most one per input).
- `sN_sanity_fail` — number of attempts that failed (returned None, JSON-invalid even after
  `fix_json`, or persisted with the same issues).

Visible in the `-debug` flag's Parse-stats block.

**Relationship to post-processing rescues:** some sanity-check kinds have overlapping
post-processing passes (e.g. `state_time_in_body` ↔ `lc_rewrites.strip_tense_has_time`;
`dropped_specific_noun` ↔ `lc_rewrites.inject_query_specific_noun_isas`).  The retry is
preferred when the LLM can plausibly fix the issue itself — the resulting Stage-2 is cleaner
and less reliant on rescue heuristics.  Post-processing remains as a belt-and-braces for
LLMs/inputs where the retry doesn't land.

**Design boundary — what is NOT checked:**

- Purely semantic calibration (confidence values, word choice between synonyms, tense
  accuracy on past/future verbs) is not flagged.
- Structural patterns that appear in the Stage-2 examples file are not flagged even if
  technically "wrong" per instructions (e.g. `has time E TENSE PREP`), because LLMs follow
  examples.  Post-processing handles these.
- Verb-frame decomposition (e.g. `has property "filled with water"`) is not flagged — the
  LLM cannot plausibly rewrite its own output that much on a retry.

The list of checks lives in `stage_sanity.py` (§5.16).  Adding a new check = one new
`_check_stage<N>_*` function plus a call inside `check_stage<N>`; no change to `llmparse.py`
is needed.

---

### 7.9 Confidence and uncertainty handling

Natural-language probabilistic hedging (`"John smokes tobacco with probability 0.8"`,
`"Elephants are rarely animals"`, `"It is false that X"`) is carried through the pipeline
as a numeric confidence value on Stage-1 ASUs and propagated into per-clause
`@confidence` annotations that the prover multiplies along resolution chains.  This
section describes every transform applied between Stage-1 and the prover.

#### Stage-1 captures probability as `confidence`

Stage-1 extracts probabilistic hedges from the input text and attaches them as a
`confidence` field on the ASU:

| Input phrase | Stage-1 `confidence` |
|---|---|
| (unmodified) | 1.0 (default) |
| `"with probability 0.8"` | 0.8 |
| `"probably"`, `"with probability 90%"` | 0.90 |
| `"likely"`, `"expected"` | ~0.80 |
| `"maybe"` | ~0.60 |
| `"unlikely"`, `"hardly"`, `"rarely"` | ~0.20 |
| `"probably not"`, `"not probable"` | ~0.20 |
| `"with probability 0%"` | 0.0 |
| `"it is false that X"`, `"it is not true that X"` | (omitted) — encoded as negation in `text` |

The field semantics: **probability** that the ASU's claim holds, in [0, 1].

**Explicit negation markers are NOT probability.**  Phrases like
`"it is false that X"`, `"it is not true that X"`, `"it is not the case that X"`
are full-confidence negated assertions.  Stage-1 PART 4 of the confidence
rules (`prompts/stage1_instructions_full.txt`) instructs the LLM to encode
the negation in the `text` field (`"X is not ..."`) and **omit** the
`confidence` field entirely.  When combined with a probability modifier
(`"it is probably false that X"`, `"with 0.8 probability it is false that X"`),
the probability goes in `confidence` and the negation stays in `text`:
`"it is likely false that John is nice"` → `text: "John 1 is not nice."`,
`confidence: 0.8`.  Without this rule, LLMs double-encode the negation
(`["not", F]` in the formula **plus** `confidence: 0.0`), which collapses to
a positive assertion after `_negate_consequent` fires.  See the "double-
encoding safety net" subsection below.

#### Stage-2 optionally reports confidence via `@p`

Stage-2 can carry the confidence forward as a package-level `@p` annotation:

```
["and", PACKAGE, ["@p", "S1", 0.8]]
```

`_process_assertion` uses the `@p` value as the input `confidence` to the clausification
step (`logconvert.py:916`).

#### Probability → evidence scale

The prover uses a symmetric evidence scale in `[-1, 1]`: **−1 = certainly false,
0 = no information, +1 = certainly true**.  `_process_assertion` maps probability `p` to
evidence `e`:

| Input `p` | Evidence `e` | Polarity flip? |
|---|---|---|
| `[0, 0.5)` | `1 − 2p` | **Yes** — consequent negated before clausification |
| `0.5` | `0` | — (all clauses dropped; prover returns "no information") |
| `(0.5, 1)` | `2p − 1` | No |
| `1` | `1.0` | No (unannotated = full confidence) |

Worked examples:

- `p = 0.8` → `e = 0.6`, no flip
- `p = 0.9` → `e = 0.8`, no flip
- `p = 0.1` → `e = 0.8`, **flip**: the assertion is negated, then asserted at `e = 0.8`
- `p = 0.0` → `e = 1.0`, **flip**: full-confidence negated assertion
- `p = 1.0` → no annotation (full confidence)

Polarity flip: `_negate_consequent(formula)` (see `lc_rewrites.py`) negates the
consequent of a rule body (or the whole formula for a bare assertion) so that low-p inputs
become high-evidence negated assertions.  This is done pre-clausification so the CNF is
structurally correct.

#### Double-encoding safety net (case 234)

When an LLM ignores PART 4 and double-encodes a negation (emits both
`["not", F]` in the formula **and** `confidence: 0.0` / `@p: 0.0`), the
`negate_consequent` step above would apply a second negation, collapsing
the claim back to positive (e.g. "It is false that X" would be asserted
as "X at full confidence" — case 234).

`_process_assertion` catches this in `logconvert.py`: if `@p == 0.0` **and**
the formula has an explicit `not` at a top-level position (root, direct
`and` conjunct, `implies` consequent, or `forall/exists` body root —
checked by `_has_explicit_negation_at_top`), the `@p` is dropped (treated
as absent/full-confidence).  The formula's own `not` then carries the
negation through clausification, producing the intended fully-confident
negated assertion.

Narrow to exactly `@p == 0.0`: a formula with `not F` paired with
`@p < 0.5` but > 0 can legitimately mean "I'm unsure about the negation"
(`"probably not X"` style), which the existing `negate_consequent` branch
handles correctly.  Broadening would regress that case.

#### Per-clause distribution of evidence

Clausification of a single ASU typically produces several clauses (event-role atoms, isa
facts, `typical/$block` defeasibility markers, etc.).  Naively stamping `@confidence = e`
on **every** clause causes the prover's chain multiplication to report `e^N` for an
N-step derivation — quickly dropping below the `0.1` keep-confidence threshold and
causing legitimate answers to be filtered out.

`_distribute_clause_confidence` (`logconvert.py`) distributes `e` across an **anchor
set** using a three-case priority:

1. **Clauses with a `$block` atom.**  These are defeasibility anchors — every derivation
   passing through the rule touches one of them.  If any $block-carrying clause exists,
   each gets `e^(1/k)` where `k` is the count of such clauses.  Non-$block clauses stay
   at confidence 1.0 (no annotation).

2. **Clauses referencing a Skolem constant or function.**  If no $block clauses exist
   but the ASU contains Skolems (e.g. `sk0_activity` from an `exists E, …` in the
   Stage-2 formula), these event-spine clauses receive `e^(1/k)`.  Non-Skolem clauses
   (plain ground isa facts like `isa(person, "John 1")`) stay at 1.0 — they are entity
   annotations unconnected to the probabilistic claim.

3. **Every clause.**  For pure class/relation assertions without events
   (e.g. `"John is an elephant with probability 0.8"` → single `isa` clause), all
   clauses receive `e^(1/k)` equally.

In every case, the **chain product over the anchor set equals `e` exactly**, so any
derivation that covers the full anchor set reports the intended confidence.

Edge cases:

- `e = 0`: all clauses dropped (line `if e == 0.0: return []`).  Input `p = 0.5` falls
  through this branch, producing no assertions at all — the prover returns
  "no information".
- `e = 1.0` (also `p = 1.0`): all clauses emitted without `@confidence` annotation.
  Prover treats as full confidence — no chain decay.
- `k = 0`: only possible for an empty clause list, which can happen when the formula
  is vacuous; the function returns `[]`.

#### Prover threshold

`globals.py:81` pins the prover to `-confidence 0.1 -keepconfidence 0.1`: any answer
whose derived confidence is below 0.1 is filtered out as noise.  Before the three-tier
distribution was introduced this threshold hid legitimate probabilistic answers (e.g.
case 235's 6-clause chain at `0.6^6 ≈ 0.047`); now the chain product equals `e`, well
above 0.1 for typical probability inputs (`p ≥ 0.6` maps to `e ≥ 0.2`).

#### Answer rendering with confidence

The reported answer string carries a verbal qualifier derived from the proved confidence
(`_format_bool_answer` in `procproofs.py:588`):

| Boolean | `conf ≥` | Rendered |
|---|---|---|
| True | 0.95 | `True.` |
| True | 0.70 | `Probably true.` |
| True | 0.40 | `Likely true.` |
| True | 0.10 | `Possibly true (confidence X).` |
| True | <0.10 | `Unknown.` |
| False | 0.95 | `False.` |
| False | 0.85 | `Likely false (confidence X).` |
| False | 0.60 | `Probably false (confidence X).` |
| False | <0.60 | `Probably false.` |

The asymmetry is intentional: True is graduated finely because positive proof chains
vary in strength, while False is proved by contradiction and even weak negative evidence
is informative.

Generic wh-answers (what-queries, and who-queries that fall into the
`_format_answers` path) append `(confidence X)` to the answer entity name
when `conf < 0.99`.  The test-harness matcher strips the parenthetical by
default (non-strict mode), so `"The man (confidence 0.94)"` passes tests
expecting `"The man"`.

**Who-queries use a qualitative prefix instead of numeric suffix**
(`_format_who_answers`).  The prefix is derived from the **minimum
confidence** across the surviving answer set (the weakest link in the
claim):

| Min confidence | Prefix |
|---|---|
| `> 0.8` | (none) |
| `(0.4, 0.8]` | `"Probably "` |
| `[0.05, 0.4]` | `"Maybe "` |
| `< 0.05` | answer dropped |

Examples (cases 241, 242):
- `"Elephants probably do not have wings. John is an elephant. Who does
  not have wings?"` → John has confidence 0.6 → `"Probably John."`
- `"Elephants probably do not have wings. John is maybe an elephant.
  Who does not have wings?"` → John has confidence 0.12 (chained
  0.6 × 0.2) → `"Maybe John."`

The threshold values mirror the Stage-1 adverb mapping (`probably` → 0.8,
`maybe` → 0.6).  The prefix is capitalized; the following word retains
its original case, so `"Probably John."` keeps the proper-noun capital
and `"Probably a tobacco."` keeps the article lowercase.

#### Skolem-typed answer rendering for "what" queries

Questions starting or containing "what" / "which" get an `@what_query` marker set by
`_process_question` (via `_raw_has_what_word` which matches the wh-word as a whole
word anywhere in the query text, not only at the start — case 243's "John smokes
what?" is correctly detected).  For such queries, `_resolve_what_skolem_answers`
(`procproofs.py`) replaces Skolem-typed answer values with population constants of the
corresponding class:

- Skolem **constant** like `"sk1_tobacco"` with an `isa(tobacco, sk1_tobacco)` fact
  → `$some_tobacco` → renders as `"a tobacco"`.
- Skolem **function** term like `["sk3", "Emily 1"]` typed as `wolf` → `$some_wolf`
  → renders as `"a wolf"`.

Without this remapping, the answer would leak the raw Skolem display name
(`"Tob1"`, `"Wol1"`) instead of the user's original noun.

#### Who-query formatting with Skolem-typed answers

`_format_who_answers` classifies each answer value into *types*, *properties*, or
*equalities*.  Before the fix, Skolem constants fell to the *equalities* bucket because
they contain digits (the skolem index).  Now if the Skolem has a known type from
`get_skolem_type` — derived from `isa(T, sk…)` facts during `compute_skolem_types` — the
**type** is promoted to the types list instead, so the who-answer renders as
`"a <type>"` consistently with what-queries.

#### Summary — files involved

| File | Role |
|---|---|
| `solver/logconvert.py` | `_process_assertion`, `_distribute_clause_confidence`, `_clause_has_block`, `_clause_has_skolem`, `_has_explicit_negation_at_top` (double-encoding safety net), `_raw_has_what_word`, `_raw_has_who_word`, `_has_what_query` |
| `solver/lc_rewrites.py` | `negate_consequent` (used by polarity flip) |
| `solver/lc_clausify.py` | `is_skolem_const`, `is_skolem_fn` (reused by the distribution) |
| `solver/procproofs.py` | `_format_bool_answer`, `_format_answers`, `_format_who_answers` (qualitative prefix), `_resolve_what_skolem_answers`, `_extract_class_names`, `_filter_class_name_leaks` |
| `solver/globals.py` | prover confidence thresholds (`-confidence 0.1`, `-keepconfidence 0.1`) |
| `prompts/stage1_instructions_full.txt` | PART 4 of `--- confidence ---`: explicit-negation-marker rule |

---

## 7.5. WH-question handling

The pipeline handles four types of WH-questions through specialized detection and encoding in `logconvert._process_question` (routing) and `lc_questions` (clause generation), with answer formatting in `procproofs`.

### Where questions ("Where is X?")

Detection: `find_where_atom(body, ask_var)` matches `["is rel2", spatial_pred, entity, ask_var]` where `spatial_pred` is a spatial preposition after meta-predicate normalization (e.g., `"located in"` is rewritten to `"in"` by `_rewrite_meta_predicates` before detection).  Also detected via `find_haslocation_prep` matching `["has location", event_var, ask_var, prep]` in activity-location queries (extracts the preposition for the answer).

Encoding depends on the entity and preposition:
- **Concrete entity** (e.g., `"John 1"`): `build_where_question` generates biconditional clauses for each spatial preposition — forward and backward — sharing a single `$defq` with 2-arg atoms `[$defq, prep, ?:Q1]`.  Generic prepositions (`in, on, at`) trigger expansion over ALL spatial preps; specific prepositions (`near, above, under`) restrict to just that preposition.
- **Variable entity** (e.g., `"Y"` for "a car"): uses `build_defq_question` which preserves all body constraints (e.g., `isa(car, Y)`) to avoid over-broad matching.

Sets `@where_query: True` and `@askvars: 2`.

Answer format: `_format_prep_answers` renders `["$ans", prep, entity]` as "In Paris.", "Near the house.", etc. with confidence prefixes.  Skolem entities (constants like `"sk0_house"` or functions like `["sk0", "box 2"]`) are resolved to their type via `_resolve_skolem_entity` (e.g., "the house").

### When questions ("When is X?")

Identical infrastructure to Where, parameterized via shared internal functions (`_find_prep_query_atom`, `_find_has_event_role`, `_build_prep_question`).

Detection: `find_when_atom` matches `_WHEN_META_PREDS` (`scheduled for, happens in, occurs at, ...`) or `WHEN_TEMPORAL_PREPS` (`in, at, on, during, before, after`). Also via `find_hastime_prep` matching `["has time", event_var, ask_var, prep]`.

Encoding: `build_when_question` generates biconditionals over temporal prepositions. Sets `@when_query: True`.

Answer format: Same `_format_prep_answers` — renders as "On Monday.", "During the summer.", etc.

### Who/What questions ("Who is X?" / "What is X?")

Detection: `_detect_who_query(body, ask_var)` matches:
- `["=", ask_var, ENTITY]` or `["=", ENTITY, ask_var]` — identity
- `["isa", ask_var, ENTITY]` — type query (ask_var in type position)
- `["is rel2", "is", ENTITY, ask_var]` or `["is rel2", "is", ask_var, ENTITY]` — copula (rewritten to `isa` by `_rewrite_is_rel2_is` but also detected directly)

Returns the concrete entity constant. The raw question text determines `who_kind` ("who" or "what") for answer ranking.

Encoding: `build_who_question` generates two biconditional sets sharing one `$defq`:
1. **isa types**: `isa(?:X, ENTITY) <=> $defq(?:X)` — what types does ENTITY belong to?
2. **equality**: `=(?:X, ENTITY) <=> $defq(?:X)` — what equals ENTITY?

Sets `@who_query: True`, `@who_entity: ENTITY`, `@who_kind: "who"|"what"`, `@askvars: 1`.

Answer formatting: `_format_who_answers` collects `$ans` values from the prover (isa types and equalities) and **injects properties directly** from a clause-list scan (`_classify_who_answers` finds `has_degree_property(PROP, ENTITY, ...)` and `has_property(PROP, ENTITY, ...)` ground facts).  Properties bypass the prover because property biconditionals with variable PROP cause search-space explosion.

Filtering: self-referential answers (answer = queried entity) are kept only as fallback when no other answers exist.  `$`-prefixed constants (population/metadata) are always filtered.  When direct properties exist, the self-referential fallback is suppressed.

Classification and ranking differs by kind:
- Who: equality > isa types > properties
- What: isa types > properties > equality

Noun phrase composition: when both types and properties exist, they are merged into a composed noun phrase — e.g., types=["car"], properties=["bad","red"] → "a bad red car".  The primary type gets all properties as adjectives; additional types are listed separately with articles.  Properties without a type are listed bare ("nice").  Equalities rendered via `entity_name()`.

Returns both the answer string and the set of surviving values (used to filter proof explanations to only show relevant proofs).

### Other WH-questions ("Who is an animal?", "What did John eat?")

WH-questions that don't match the who/what identity pattern or the where/when preposition pattern fall through to the general `build_defq_question` path, which wraps the full ask body in a `$defq` biconditional. These handle "Who is an animal?" (find entities of type animal), "What did John eat?" (find event targets), etc.

The defq path also injects wh-kind markers so answer formatting can route
through the right formatter:

- `_raw_has_what_word(raw_text)` detects `what`/`which` as whole words
  anywhere in the query text → sets `@what_query: True` on the question
  object.
- `_raw_has_who_word(raw_text)` detects `who`/`whom` → sets
  `@who_query: True`.  Without this, complex who-questions like
  `"Who does not have wings?"` (whose body doesn't match the simple
  identity patterns of `_detect_who_query`) would fall through to the
  generic `_format_answers` path and render with a numeric
  `(confidence X)` suffix instead of the qualitative `"Probably X."` /
  `"Maybe X."` prefix from `_format_who_answers` (cases 241, 242).

### Class-name leak filtering in who-queries

The background part-inheritance axiom
`has_part(X, Y, Z) ∧ isa(X, U) → has_part(U, Y, Z)` (an elephant's part
is a part of all elephants) can unify the answer variable with a **class
name string** (e.g. `"elephant"`) via a population fact like
`isa(elephant, $some_elephant)`.  The resulting `$ans("elephant")` is not
an entity answer — it's a leak from the meta-variable in the axiom.

`_filter_class_name_leaks` in `procproofs.py` drops answers whose every
`$ans` atom binds to a class name (computed by `_extract_class_names`:
the set of first-arg strings from all `isa(CLASS, *)` atoms in the
problem's clause list).  The filter fires only for generic
wh-placeholder queries — when `@who_entity` is **unset**.  For queries
with an explicit `@who_entity` (like `"Who is John?"`), class names are
legitimate type descriptions of the queried entity and are kept.

### $ctxt injection for WH-questions

All question types use the query's concrete world from Stage 1 `pre_state` for matrix
predicates (is_rel2, have, etc.), and free-var worlds for descriptive atoms (isa, event
predicates).  Tense defaults to `"present"` when Stage 1 does not provide a `"time"`
field — matching the convention that bare present-tense is the unmarked default.
Stage 1 provides `"time": "past"` for explicitly past-tense questions ("Did he run?",
"Was the car red?"), which the pipeline uses directly.

This present-tense default prevents the tense bridge axioms (`present@W_old` →
`past@W_new` via `before(W_old,W_new)`) from leaking stale historical facts into
present-tense queries like "Where is John?" — the query's `$ctxt(present, W, ...)`
only matches present-tense results at the query world, not past-tense bridged facts.

---

## 7.6. Proof deduplication

The prover often returns multiple proofs for the same answer that differ only in temporal/world-navigation paths (e.g., 10 proofs for "in the house" using different world-state axiom routes W0→W1, W0→W1→W2, etc.).

`_deduplicate_proofs(answers)` in `procproofs.py` eliminates redundant shadow proofs:

1. **Group** answers by conclusion value (deep-equal) AND content fingerprint (frozenset of `sent_*` sources used in the proof).
2. **Within each group** (same answer + same content sentences), proof A dominates proof B if ALL of:
   - `len(A.blockers) <= len(B.blockers)`
   - `A.confidence >= B.confidence - 0.15` (configurable threshold)
   - `len(A.steps) <= len(B.steps)`
3. **Remove dominated proofs**, keeping the simplest non-dominated proof per group.

Runs after `_filter_by_best_tier` and `_filter_tautological_population_answers`, before answer formatting.

---

## 7.7. Typed Skolem constants

Skolem constants generated during clausification embed their type in the name when the type is known from the existential body:

- `["exists", "Y", ["and", ["isa","house","Y"], ...]]` → constant `"sk0_house"` (instead of `"sk0"`)
- Unknown type: plain `"sk0"` (backward compatible)
- Skolem functions (from rules with free variables) keep plain names: `["sk0", "?:X"]`

Helper functions in `lc_clausify.py`:
- `is_skolem_const(val)` — matches both `sk0` and `sk0_house` patterns
- `is_skolem_fn(val)` — matches list Skolem functions
- `skolem_type_from_name(name)` — extracts type: `"sk0_house"` → `"house"`, `"sk0"` → `None`

Skolem type resolution for rendering (`procproofs._resolve_skolem_entity`):
1. **Fast path**: extract type from name via `skolem_type_from_name`
2. **Fallback**: look up type from `compute_skolem_types` clause-list scan (handles old-format names and Skolem functions)

`compute_skolem_types(proof, logic=None)` in `proof_render.py` scans both the logic clause list (for types not used in the proof) and proof steps, populating `skolem_types` and `skolem_fn_types` tables.

---

## 8. Configuration and options

**To change the default LLM provider or model**, edit `solver/llmcall.py`:
```python
use_llm          = "gemini"            # "gpt" | "claude" | "gemini" | "deepseek"
geminiversion    = "gemini-2.5-flash"
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

## 9. The mkdata toolkit and solver integration

`mkdata/` is a standalone toolkit (separate venv, no dependency on `solver/`) for building
synonym, antonym, and mutual-exclusion data files. The final step (`build_solver_data.py`)
generates Python dict files in `solver/` that are loaded at runtime.

### 9.1 What mkdata produces

| Output | Count | Purpose |
|--------|-------|---------|
| `syn_{a,n,v}_rewrite.txt` | 416 / 218 / 124 entries | Tier A hard rewrites (`member,canonical`) |
| `syn_{a,n,v}_soft_axioms.txt` | 2496 / 6218 / 4103 pairs | Tier B soft synonym pairs (`word_a,word_b,score`) |
| `ant_{a,n,v}.txt` | 1483 / 375 / 295 entries | Antonym pairs (directional, polarity-flip) |
| `excl_a.txt` | ~60 groups (+ 4 synthetic from `MANUAL_ANTONYMS`, + ~60 synthetic `ANT_*` groups from chain-rejected antonym pairs) | Mutual-exclusion groups (colors, months, nationalities, kinship/gender pairs, spatial/temporal opposites) |

### 9.2 Solver runtime files

Generated by `cd mkdata && python3 build_solver_data.py` (fast, ~1 sec):

| Generated file | Contents | Used by |
|----------------|----------|---------|
| `solver/data_canonicals.py` | `CANONICALS` dict (~752 entries, all POS merged) | `semnormalize.py` |
| `solver/data_antonyms.py` | `ANTONYMS` dict (~850 directional pairs) | `semnormalize.py` |
| `solver/data_synonyms.py` | `SOFT_SYNONYMS` dict (~12K words, bidirectional) | `lc_postprocess.py` |
| `solver/data_exclusions.py` | `EXCLUSION_GROUPS` + `EXCLUSION_INDEX` (~123 groups, 4 atom shapes) | `lc_postprocess.py` |

Must be regenerated whenever any mkdata `.txt` source changes.

### 9.3 Solver integration

The data files are integrated at two points in the pipeline:

**Post-clausification semantic normalization** (`semnormalize.py`, called from `solve.py`):
1. Antonym folding: if a word is in `ANTONYMS`, flip atom polarity and substitute the antonym
2. Canonical substitution: if a word is in `CANONICALS`, replace unconditionally

Both passes walk all atom arguments (positions 1+), skip predicate names (position 0),
skip `$ctxt` terms, and handle disjunctive clauses (list-of-lists). Controlled by
`-nosemnormal` flag.

**Dynamic axiom injection** (`lc_postprocess.py`, called from `logconvert.rawlogic_convert`):

*Soft synonym axioms* (`inject_soft_synonyms`):
- Scans the clause list for words appearing in `SOFT_SYNONYMS`
- Emits biconditional clauses: `NOT pred(W,X,Ct) OR pred(OTHER,X,Ct)` (both directions)
- Templates: `has property` for adjectives (gradable normalizer promotes later), `isa` for
  nouns, `has type` for verbs
- Uses a single free variable for context (unifies with any `$ctxt` term)
- Two-side restriction (`REQUIRE_BOTH_SIDES = True` in `lc_postprocess.py`): only emits if
  the other side also appears in the input clauses or axiom file vocabulary

*Exclusion axioms* (`inject_exclusion_axioms`):
- Scans the clause list for words appearing in `EXCLUSION_INDEX`
- For groups with 2+ members present, emits pairwise exclusion clauses
- `needs_blocker=False` (months, days, kinship, spatial opposites): hard exclusion
  `NOT w1(X,Ct) OR NOT w2(X,Ct)`
- `needs_blocker=True` (colors, nationalities): defeasible exclusion with `$block` on each
  side (two axioms per pair), allowing override when both are explicitly asserted
- Four atom shapes selected per group:
  - **Default** (`has_property`): adjective groups — `[-has property, w, ?:X, ct]`
  - **`_IS_REL2_EXCL_GROUPS`** (MONTH, DAY_OF_WEEK, SEASON): preposition-target at
    is_rel2 position 3 — `[-is rel2, ?:R, ?:X, w, ct]`
  - **`_IS_REL2_PREP_GROUPS`** (SPATIAL_*, TEMPORAL_ORDER): preposition itself at
    is_rel2 position 1, with two free entity variables —
    `[-is rel2, w, ?:X, ?:Y, ct]`
  - **`_HAS_DEGREE_REL2_PREP_GROUPS`** (PROXIMITY): preposition at has_degree_rel2
    position 1. Emitted as TWO asymmetric axioms per pair — positive side
    any-degree, antonym side `"none"` intensity, shared `?:RC`:
    `[-has degree rel2, W1, ?:X, ?:Y, ?:D, ?:RC, ct], [-has degree rel2, W2, ?:X, ?:Y, "none", ?:RC, ct]`
    (and the symmetric axiom with W1/W2 swapped). The existing high→none /
    low→none intensity bridges in axioms_std.js §9 propagate the "none"
    negation to all intensities via contrapositive.

*MANUAL_ANTONYMS → synthetic adjective exclusion groups*:
`MANUAL_ANTONYMS` in `build_solver_data.py` is a small hand-curated dict of adjective
antonym pairs (currently `broken/intact`, `unfinished/finished`, `incomplete/complete`,
`undone/done`). **It no longer feeds `ANTONYMS` for polarity-flip rewriting.** Instead,
`build_exclusions()` converts each pair into a 2-member `needs_blocker=False` exclusion
group named `MANUAL_ADJ_<W1>_<W2>`, emitted with the default has_property template.
Semantically this is cleaner: "X is broken" and "X is intact" are mutually exclusive, not
strictly complementary — the axiom form expresses that precisely without losing positive
atoms.

*Chain-rejected antonyms → synthetic `ANT_*` exclusion groups*:
`build_antonyms` applies two symmetric guards against chain-contamination with the
canonical-substitution pass:
1. `word in CANONICALS` — skip; Pass 2 would shadow the fold source.
2. `canonical in CANONICALS` — skip rewriting; Pass 2 would chain-substitute the target
   to an unrelated sense. Example: WordNet has `open ↔ close` (verb sense) and
   `CANONICALS["close"] = "near"` (adjective sense from syn_a rewrites). Without the
   guard, semnormalize would turn `has_property(open, door)` into
   `-has_property(near, door)` — a nonsense atom (door is not near).

Pairs rejected by guard (2) — about 65 pairs — are deferred to `build_exclusions` and
emitted as synthetic 2-member `needs_blocker=True` (defeasible) exclusion groups named
`ANT_<W1>_<W2>`. Same has_property template as `MANUAL_ADJ_*`, same two-side
restriction, same injection code path. This preserves the semantic link between
antonym pairs (so the prover can still derive contradictions) without the destructive
rewriting that caused the chain bug. `needs_blocker=True` is used because many of these
pairs are gradable (abundant/scarce, hot/cold) where a middle ground exists and a hard
exclusion would overshoot.

*Axiom vocabulary cache* (`axiom_vocab.py`):
- Extracts content words from axiom files (e.g. `axioms_std.js`), caches in `.vocab` sibling file
- Auto-rebuilt when axiom file is newer than cache
- Used by both injection functions for the two-side restriction

### 9.4 Full build pipeline

```
Step 1: make_anto_synonyms.py --pos {a,n,v}  ->  syn_*_10.txt, ant_*.txt
Step 2: harvest_syn_{a,n,v}.py               ->  expands syn_*_10.txt
Step 3: pick_canonicals_{a,n,v}.py --apply --emit  ->  syn_*_rewrite.txt, syn_*_soft_axioms.txt
Step 4: build_exclusion_data.py              ->  excl_a.txt
Step 5: build_solver_data.py                 ->  solver/data_*.py
```

Steps 1-4 are heavy (fastText model, NLTK). Step 5 is fast and should be re-run after any
source .txt changes. See `mkdata/README.md` for full documentation.

### 9.5 Spatial and temporal preposition handling

Handled via three cooperating mechanisms. Each is used where it fits best — pure surface
variants get rewritten, mutual exclusions get dynamic axioms, near-synonyms with distinct
meaning get static subsumption axioms.

**(a) Canonical rewriting — form variants (pre-clausification)**

`_PREP_CANONICAL` in `solver/lc_rewrites.py` maps spaced / colloquial preposition forms to
their underscored canonical forms. Applied inside `rewrite_meta_predicates` to:
- `is_rel2` argument 1,
- `has_degree_rel2` argument 1 (for near/far_from/close_to),
- `has_location` / `has_time` / `has_destination` preposition slot (argument 3).

Examples:
```
"in front of"      → "in_front_of"
"to the left of"   → "left_of"
"in back of"       → "behind"        # colloquial collapse
"inside of"        → "inside"        # "of" drop
"out of"           → "outside"
"far away from"    → "far_from"
"far"              → "far_from"      # has_degree_rel2: LLM sometimes drops "from"
"close to"         → "near"          # collapse into near (no subsumption axiom needed)
"prior to"         → "prior_to"
"subsequent to"    → "after"
```

Used only when the source form is a pure surface variant of the target (same concept,
different spelling). True lexical synonyms with distinct connotations (under ≠ below
exactly) are not collapsed here.

**(b) Mutual-exclusion axioms — spatial/temporal opposites (dynamic injection)**

Groups in `mkdata/excl_a.txt` whose ids belong to `_IS_REL2_PREP_GROUPS` (in
`solver/lc_postprocess.py`) are emitted with the preposition-at-pos-1 template:
```
[-is_rel2(w1, ?:X, ?:Y, ct), -is_rel2(w2, ?:X, ?:Y, ct)]
```
Current groups (all `needs_blocker=False`, i.e. hard exclusion):
```
SPATIAL_SAGITTAL                 behind, in_front_of
SPATIAL_VERTICAL                 above, below
SPATIAL_VERTICAL_OVER_UNDER      over, under
SPATIAL_CONTAINMENT              inside, outside
SPATIAL_LATERAL                  left_of, right_of
TEMPORAL_ORDER                   before, after
```

A fourth shape, `_HAS_DEGREE_REL2_PREP_GROUPS`, handles binary relations that
use `has_degree_rel2` instead of `is_rel2` (6-arg predicate with DEGREE and
RELCLASS slots). Currently one group:
```
PROXIMITY                        near, far_from
```
Each such group emits **two asymmetric axioms per pair** — positive side at
any degree (`?:D`), antonym side at `"none"` intensity, shared `?:RC`:
```
[-has_degree_rel2(near,     ?:X, ?:Y, ?:D,   ?:RC, ct),
 -has_degree_rel2(far_from, ?:X, ?:Y, "none", ?:RC, ct)]
[-has_degree_rel2(far_from, ?:X, ?:Y, ?:D,   ?:RC, ct),
 -has_degree_rel2(near,     ?:X, ?:Y, "none", ?:RC, ct)]
```
The intensity bridges (high→none, low→none) in axioms_std.js §9 then
propagate the `"none"` negation to all intensities via contrapositive, so
"very near" correctly rules out "far_from" at every degree.
Axioms emitted only when ≥2 members of a group appear in the problem or axiom vocabulary
(two-side restriction via `REQUIRE_BOTH_SIDES`).

**(c) Subsumption axioms — near-synonyms (static, in axioms_std.js)**

A small set of universally-useful one-way implications, placed as static axioms in
`axioms_std.js` §7c (spatial) and §7d (temporal). Direction is always
specific → general (the more specific predicate implies the more general one):
```
underneath, beneath, under   →  below          [§7c]
over, on_top_of              →  above          [§7c]
prior_to, preceding          →  before         [§7d]
following                    →  after          [§7d]
```
These are static (always loaded) rather than dynamically injected because the set is
small (~8 axioms), universally relevant, and should chain cleanly with other static
axioms in the KB.

**Canonical rewriting adjustments for has_degree_rel2 forms:**
- `"far"` → `"far_from"` (LLM sometimes drops "from" in query form)
- `"close to"` / `"close_to"` → `"near"` (close_to collapsed into near; subsumption not needed)

**Out of scope for now:**
- `earlier_than` / `later_than` (also `has_degree_rel2`): no active exclusion partner in
  tests (temporal order is captured in `is_rel2(before/after)`). A subsumption like
  `earlier_than → before` would require crossing `has_degree_rel2 → is_rel2` — a
  different axiom shape.

**Interaction example.** For "The car parked behind the house was blue. Was the car in
front of the house?":

1. Stage 2 emits `is_rel2("behind", car, house, C)` and query
   `is_rel2("in_front_of", car, house, C)`.
2. `rewrite_meta_predicates` is a no-op here (both already canonical).
3. `inject_exclusion_axioms` sees both `behind` and `in_front_of` in `SPATIAL_SAGITTAL`
   and emits `[-is_rel2("behind",?:X,?:Y,ct), -is_rel2("in_front_of",?:X,?:Y,ct)]`.
4. Assertion + exclusion axiom derives `-is_rel2("in_front_of", car, house, C)`,
   contradicting the query → answer **False**.

---

## 10. Extending and modifying the pipeline

### Adding new predicates

1. Add the predicate to the whitelist table in `prompts/stage2_instructions.txt` (section
   `== 5. PREDICATE INVENTORY ==`).
2. Add examples to `prompts/stage2_examples.txt` showing the new predicate in context.
3. If the predicate should receive `$ctxt`, add it to `CTXT_ELIGIBLE` in `lc_ctxt.py`.
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
