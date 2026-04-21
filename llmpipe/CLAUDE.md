# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`llmpipe` is an experimental pipeline for semantic parsing of natural language into first-order predicate logic using LLMs (OpenAI GPT, Anthropic Claude, Google Gemini, DeepSeek). It is part of the larger `nlpsolver` repository. Parsed logic is passed to the `gk` binary theorem prover which returns answers.

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
Output level (hierarchy — each includes previous levels):
-explain         Show English proof explanation
-logic           + simplified text, sentences-to-clauses, logic in proof steps
-details         + stage-1/2 JSON, prover input/output JSON
-debug           + raw LLM responses, prover params, full trace

Output format:
-json            Show logic as raw JSON instead of traditional syntax
-jsonlogic       Shortcut for -logic -json
-gkin FILE       Save GK prover input to FILE (with GK command as comment)

Simplification (see ENCODINGS.md §5 for details):
-nocontext       Context → constant "$c" (no worlds/tense)
-noexceptions    Strip $block from defeasible rules
-simpleproperties  Degree predicates → simple (+ -noexceptions)
-simple          All three combined

Other:
-llm NAME        LLM provider: gpt, claude, gemini, or deepseek
-version VER     Model version string, e.g. claude-sonnet-4-6
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
- `llmparse.py` — two-stage LLM parser; `parse_text(text)` → `(s1_json, s2_json, stats)`; includes entity ID case normalization between stages
- `llmcall.py` — LLM API wrapper (GPT/Claude/Gemini/DeepSeek) with retries and SQLite caching; `call_llm(sysprompt, input_text)`
- `logconvert.py` — main driver for stage-2 JSON → GK clause list; `rawlogic_convert(logic)`; orchestrates package extraction, question/assertion processing, and post-processing passes
- `lc_rewrites.py` — pre-clausification formula rewrites: meta-predicate normalization (incl. `is_rel2("time of")`→`has_time`), tense-valued `has_time` stripping, degree presuppositions, existential hoisting, spurious `can` removal, polarity flip
- `lc_ctxt.py` — `$ctxt` context injection, time-wrapper stripping, fresh variable generation, predicate classification constants
- `lc_postprocess.py` — post-clausification clause-list passes: gradable normalization, RELCLASS coercion, isa-entity stripping, `$theof1` definite rewrites (global pass), `$measure`→`$list` canonical unit conversion for `$measure_of` terms, `less_measure` rewriting for comparison operators on measures, `$theof1` unwrap inside `$measure_of`, possessive `have` inference, population facts, degree stripping, soft synonym axiom injection, exclusion axiom injection
- `lc_clausify.py` — FOL-to-CNF compiler: implies/xor/equivalent elimination, NNF push, normally expansion, Skolemization, distribution, clause extraction.  Also provides Skolem identification helpers (`is_skolem_const`, `is_skolem_fn`, `skolem_type_from_name`), typed Skolem constant naming (`sk0_house`), `is_world_constant` (W0/W1 excluded from variable detection)
- `lc_questions.py` — question wrapping (`ask`/`question` → `@question`/`@askvars`), population fact injection, and WH-question builders: `build_where_question`/`build_when_question` (preposition expansion), `build_who_question` (isa + equality biconditionals), `build_defq_question` (general $defq)
- `lc_sets.py` — set/counting: `$setof` rewriting to canonical form, membership axiom generation, element instantiation, set existence fact generation
- `procproofs.py` — post-processes prover output; formats answers (bool, who/what, where/when), confidence labels, proof deduplication, Skolem resolution, proof explanation dispatch; `@what_query` class-preference (population over concrete, Skolem-to-class resolution)
- `proof_explain.py` — generates English proof explanations from prover proof steps
- `proof_render.py` — facade module re-exporting from `proof_utils`, `proof_english`, `proof_logic`
- `proof_utils.py` — entity naming, Skolem type resolution, render context state, ambiguity detection
- `proof_english.py` — atom/clause → English rendering; table-driven predicate dispatch via `_PRED_TABLE`
- `proof_logic.py` — traditional `pred(arg,...)` and JSON logic syntax rendering
- `linguistics.py` — pure English heuristics (articles, verb conjugation, comparatives, gerunds); used by proof_english.py
- `prover.py` — invokes the `gk` binary subprocess; `call_prover(logic)`; auto-selects unit strategy when equalities with function terms detected
- `cache.py` — SQLite-backed cache for LLM responses and prover results
- `globals.py` — global `options` dict and file paths (uses `os.path` for absolute paths)
- `pretty.py` — JSON pretty-printer; `pp_str/pp_logic/pp_stage1/pp_stage2`; Style B layout with `noquotes` mode
- `utils.py` — utility functions: `debug_print`, `clause_list_to_json`
- `semnormalize.py` — post-clausification semantic normalization: antonym folding (flip polarity + replace word) and canonical word substitution; skips `$ctxt` terms; handles disjunctive clauses
- `data_canonicals.py` — (generated) `CANONICALS` dict: ~752 Tier A `{variant: canonical}` entries from `mkdata/syn_{a,n,v}_rewrite.txt`
- `data_antonyms.py` — (generated) `ANTONYMS` dict: ~935 `{word: antonym}` entries from `mkdata/ant_{a,n,v}.txt`
- `data_synonyms.py` — (generated) `SOFT_SYNONYMS` dict: ~12K words, bidirectional `{word: [(other, score, pos), ...]}` index from `mkdata/syn_{a,n,v}_soft_axioms.txt`
- `data_exclusions.py` — (generated) `EXCLUSION_GROUPS` + `EXCLUSION_INDEX` from `mkdata/excl_a.txt`
- `axiom_vocab.py` — extracts and caches content words from axiom files (e.g. `axioms_std.js`); used to restrict synonym/exclusion injection to pairs where both sides appear in the problem or axioms

### Semantic Normalization Pipeline

Applied after clausification, before the prover. Controlled by `-nosemnormal` flag.

```
rawlogic_convert() produces clause list
  |
  v
semnormalize.sem_normalize_clauses(clauses)     [solve.py:184]
  Pass 1: Antonym folding — if word in ANTONYMS, flip atom polarity + replace
  Pass 2: Canonical substitution — if word in CANONICALS, replace unconditionally
  (Both skip $ctxt terms, handle disjunctive clauses)
```

Soft synonym and exclusion axioms are injected earlier, inside `rawlogic_convert()`:

```
rawlogic_convert():
  ... clausification, population facts ...
  result.extend(background)            # population + compound subsumption
  result.extend(sem_axioms)            # soft synonyms + exclusions [appended after all sent_* clauses]
  ... gradable normalization (promotes has_property -> has_degree_property) ...
```

**Soft synonym axioms** (`inject_soft_synonyms` in `lc_postprocess.py`):
- Scans clause list for words in `SOFT_SYNONYMS`
- Emits biconditional clauses: `[-has_property, W, X, Ct], [has_property, OTHER, X, Ct]`
- Templates: `has property` for adjectives (gradable normalizer promotes later), `isa` for nouns, `has type` for verbs
- Uses a single free variable `?:Ct` for context (unifies with any `$ctxt` term)
- Two-side restriction (`REQUIRE_BOTH_SIDES = True`): only emits if other side also appears in input clauses or axiom file vocabulary

**Exclusion axioms** (`inject_exclusion_axioms` in `lc_postprocess.py`):
- Scans clause list for words in `EXCLUSION_INDEX`
- For groups with 2+ members present, emits pairwise exclusion clauses
- `needs_blocker=False` groups: hard exclusion `[-has_property, W1, X, Ct], [-has_property, W2, X, Ct]`
- `needs_blocker=True` groups: two defeasible axioms per pair with `$block` on each side
- Temporal groups (MONTH, DAY_OF_WEEK, SEASON): use `is rel2` template instead of `has property`

**Axiom vocabulary cache** (`axiom_vocab.py`):
- Extracts content words from axiom files, caches in `.vocab` sibling file
- Auto-rebuilt when axiom file is newer than vocab cache
- Used by both injection functions for the two-side restriction

**Regenerating data files** after changing `mkdata/*.txt` sources:
```bash
cd mkdata && python3 build_solver_data.py
```

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
use_llm          = "gemini"              # "gpt" | "claude" | "gemini" | "deepseek"
claudeversion    = "claude-sonnet-4-6"
gptversion       = "gpt-5.1"
geminiversion    = "gemini-2.5-flash-lite"
deepseekversion  = "deepseek-chat"       # V3.2; "deepseek-reasoner" for thinking
temperature      = 0
default_max_tokens = 8000
```

API keys are read from JSON files at:
- `../secrets/gpt_secrets.txt`
- `../secrets/claude_secrets.txt`
- `../secrets/gemini_secrets.txt`
- `../secrets/deepseek_secrets.txt`

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

## Debug Case Workflow

When the user says **"Debug case N"** (where N is a case number in `testfixlog.txt`):

1. **Run `python3 examine.py N`** — this looks up Case N in `testfixlog.txt`, runs all five
   solvers (gemini, claude, gpt, deepseek, udp) in parallel with `-debug -json`, and writes
   logs to `eN_gemini.txt`, `eN_claude.txt`, `eN_gpt.txt`, `eN_deepseek.txt`, `eN_udp.txt`.
   The `-json` flag ensures logic is shown in raw JSON for cross-referencing with prover I/O.

2. **Read `testfixlog.txt` entry for Case N** — note the `Input:` text and `Expected:` value.

3. **Explore all five log files** — read them fully, comparing the answers and logic/proof
   output across all LLM providers and the UDP pipeline.

4. **Examine Stage 1 and Stage 2 outputs** — a correct final answer is not sufficient.
   Compare the Stage 1 and Stage 2 raw outputs across all LLMs. Minor stylistic differences
   between LLMs are OK, but report any major conceptual differences (e.g., wrong entity
   types, missing isa guards, flat vs nested quantifier structure, dropped conditions).
   Both stages must be correct, not just the final answer.

5. **Assess the Expected value** — form an independent opinion on whether the `Expected:`
   value in testfixlog.txt is the correct answer under a normal interpretation of the input,
   or whether it should be changed, or whether there are good alternatives.
   Assume the UDP pipeline answer is correct in most (but not all) cases.

6. **Analyze errors** — if any LLM pipeline log files give an incorrect or suboptimal answer,
   analyze the root cause (stage-1 parse, stage-2 logic, logconvert, prover input, proof
   post-processing, etc.).

7. **Test with -nocontext if $ctxt suspected** — if the failure looks like a world/tense
   mismatch in $ctxt, run `python3 solver/solve.py -nocontext "..."` on the same input.
   If it succeeds without context but fails with, the issue is $ctxt injection, not logic.

8. **Simplify if uncertain** — if the root cause is unclear, construct a simpler version of
   the input text that isolates the suspected issue, run `python3 solver/solve.py ...` on it,
   and examine the result. Repeat as needed.

9. **Write analysis and fix plan** — summarize the root cause(s) of any errors and propose a
   concrete plan for fixing. Do **not** write any code or modify any files at this stage.

## Register Fix Workflow

When the user says **"Register fix for case N"** — assuming the debug analysis was done,
a fix was implemented, and it has been verified to work:

1. **Read the Case N entry in `testfixlog.txt`** to see its current state.
2. **Add brief `Conclusion:`, `Cause:`, and `Fixes:` fields** to the case entry, following
   the style and brevity of existing entries in the file. Keep all text short — one or two
   lines per field. If a comment would be long, shorten it to the essential point.
3. **Do not rewrite or remove existing fields** — only add what is missing.

## Work Process Rules

- **NEVER pass `-nollmcache` or `--nollmcache` to any command.** This flag bypasses the LLM
  cache and wastes API credits. There are NO exceptions — even if the user asks you to
  "recheck" or "rerun", always use the cache. If the user has changed prompts, they will
  run the solver themselves or explicitly tell you to disable the cache.
- **Always trust the LLM cache.** The user may run the solver independently, so cache
  entries may be newer than what you last saw. Always use cache and trust its results.
- **Never run `test.py` with more than 5 examples** without explicit instruction from the user.
  Use `-limit 5` or `-filter PATTERN` to restrict the run. For quick sanity checks, run
  `python3 solver/solve.py ...` on individual examples instead of the full test suite.
- **Run `python3 solver/solve.py ...`** directly without asking for consent.
- **Grep and read-only bash commands** (grep, sed without -i, cat, head, tail, echo) inside the
  llmpipe folder may be run without asking for consent, as long as no files are written,
  modified, or deleted.
- **Prefer the built-in Grep/Read/Glob tools** to grep etc bash tools
- **Compound read-only commands** using | with grep, head, tail, cat are allowed.
- **Avoid using $() syntax** when other alternatives possible



### Other Top-Level Scripts

- `nlpsimplecollect.py` — collect LLM parsing results for a test file
- `nlpsimpleconv.py` — parse and clean raw collected results
- `collectmultillmconv.py` — orchestrate multiple LLM providers in one collection run
- `comparellmconv.py` — compare Stage-1 outputs from multiple LLM runs
- `checkprompt.py` — validate JSON in prompt files
- `run_pretty_check.py` — run `rawlogic_convert` on 10 examples and pretty-print results
