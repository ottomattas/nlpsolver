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
-geminicache     Enable Gemini server-side context caching (off by default)
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
- `llmparse.py` — two-stage LLM parser; `parse_text(text)` → `(s1_json, s2_json, stats)`; includes entity ID case normalization between stages; runs `stage_sanity.check_stage{1,2}` after each parse and re-calls the LLM with a corrective prompt (max 2 retries per stage) if issues are found
- `llmcall.py` — LLM API wrapper (GPT/Claude/Gemini/DeepSeek) with retries and SQLite caching; `call_llm(sysprompt, input_text)`
- `logconvert.py` — top-level orchestrator for stage-2 JSON → GK clause list; `rawlogic_convert(logic)`; runs structural repair, what-question population, Stage-1 entity bookkeeping, phantom-isa-guard stripping (`_strip_phantom_query_guards` — drops an orphan `isa(C,E)` guard from a query body when E is a Stage-1 entity that is never asserted and is used nowhere else in the query, e.g. a leaked definite-description referent that would make the whole query unprovable), and dispatches per-package processing to `lc_packages`
- `lc_packages.py` — per-`@id` package processing: `extract_package_ctx`, `convert_id_package`, `_process_question`/`_process_assertion`, raw wh-word probes, confidence distribution
- `lc_rewrites.py` — pre-clausification formula rewrites: meta-predicate normalization (incl. `is_rel2("time of")`→`has_time`), tense-valued `has_time` filtering (narrowed 2026-05-14: KEEPS the canonical Davidsonian shape `["has time", E, "past"|"present"|"future", "in"]` when E is an event var introduced by `isa(activity, E)`, STRIPS the same shape on non-event vars and always strips in-body `state_time`), `inject_actuality` (2026-05-15: appends `["actuality", E]` to every Davidsonian event lacking a Stage-2 modal classifier and not appearing as `has_content` inner arg), degree presuppositions, existential hoisting, polarity flip. The legacy `strip_spurious_can` remains but no longer fires under the new arity-1 capability classifier.
- `lc_ctxt.py` — `$ctxt` context injection, time-wrapper stripping, fresh variable generation, predicate classification constants
- `lc_post_normalize.py` — post-clausification normalising / repair passes: gradable predicate normalization, RELCLASS coercion, isa-entity stripping, possessive `have` inference, `have`→`has_part` fact bridge for typed body-part nouns (`add_haspart_for_typed_have`), `have`→`has_part` axiom bridge (`inject_have_to_haspart_axioms`, defeasible 0.9, type-gated by rule premise scan — complements axioms_std.js §2 by supplying the contrapositive `¬has_part ⊢ ¬have` needed when a query uses `have` and the asserting rule uses `has_part`), degree stripping, population fact extraction, compound subsumption rules
- `lc_post_reify.py` — post-clausification reification of definite descriptions and measurements: `$theof1` definite rewrites (global pass, with chain-rewrite guard), `$measure`→`$list` canonical unit conversion for `$measure_of` terms, `less_measure` rewriting for comparison operators on measures, `$theof1` unwrap inside `$measure_of`
- `lc_post_inject.py` — post-clausification dynamic axiom injection: soft synonym axioms, mutual-exclusion axioms (incl. noun-mutex via `_ISA_EXCL_GROUPS` and gradable adjective antonyms via `MANUAL_ADJ_GRAD_*`), cross-group isa-mutex (`inject_isa_cross_group_axioms`), verb mutex (pass↔fail), kinship mutex (16 gender-paired roles), carrier vocabulary lift (`inject_carrier_lifts` — plate/tray/etc. → `isa(carrier,X)`), verb-result-state bridges (`inject_verb_result_state_axioms` — destroy/break/etc. → has property "destroyed"/"broken"/etc. with two bridges A and B for event-based and stative encodings; runs BEFORE inject_exclusion_axioms so result-state words become eligible for the exclusion injector), measure_of→"<noun> of" relational bridges (`inject_measure_relation_bridges` — per measure noun N, emitted only when both a `$measure_of(N,...)` fact and an `is_rel2 "N of"` atom appear; lets a relationally-phrased measure query "what is the length of X?" reach the `$list` value. Paired with the `$list` value-preference in `proof_answer_select._prefer_measure_value_answers`), negative-implicative bridges (`inject_negative_implicative_bridges` — refuse/decline; "Tom refused to eat the soup" → no actual eat(Tom,soup) → "Tom ate the soup?" is False; emitted only when refuse/decline appears), world-graph geometry (next-chain over present worlds).  Gate policy: `inject_soft_synonyms` fires on any pair where both sides are in input ∪ axiom_vocab; all other injectors require AT LEAST ONE side of the pair (or the single trigger word) to appear in the actual input — axiom-vocab-only triggers would either duplicate static axioms or sit idle.
- `lc_post_una.py` — post-clausification entity UNA wrapping: prefix every Stage-1 numbered entity with `#:` so the gk prover treats distinct entity constants as definitely unequal. Three-step criterion: surface-form regex + Stage-1 entity-set membership + not-Skolem-shaped. Required by axioms_std.js §7g (X2 direct-support uniqueness). Render-time strip in `proof_utils.entity_name`, `proof_logic._logic_name`, `procproofs.process_proof`
- `lc_clausify.py` — FOL-to-CNF compiler: implies/xor/equivalent elimination, NNF push, normally expansion, Skolemization, distribution, clause extraction.  Also provides Skolem identification helpers (`is_skolem_const`, `is_skolem_fn`, `skolem_type_from_name`), typed Skolem constant naming (`sk0_house`), `is_world_constant` (W0/W1 excluded from variable detection)
- `lc_questions.py` — question wrapping (`ask`/`question` → `@question`/`@askvars`), population fact injection, and WH-question builders: `build_where_question`/`build_when_question` (preposition expansion), `build_who_question` (isa + equality biconditionals), `build_defq_question` (general $defq).  Also `hoist_generic_yn_subject` — bare-plural-generic yes/no rewrite: detects `forall X, isa(C,X) → normally(BODY)` (Stage-2 §7.4(a)), hoists `isa(C, skq_S<qid>_<C>)` as a fact, and rewrites the question body to `BODY[X ← skq…]` so the defeasible rule fires on a fresh skolem (UDP-shaped). Avoids both the strict-collapse bug of pure `forall` and the John-shortcut bug of pure `exists` for queries like "Cars have trunks?"
- `lc_sets.py` — set/counting: `$setof` rewriting to canonical form, membership axiom generation, element instantiation, set existence fact generation
- `procproofs.py` — orchestrator for prover-output post-processing; `process_proof` parses the prover JSON, strips the `#:` UNA prefix, then drives answer selection (`proof_answer_select`) and formatting (`proof_answer_format`), and dispatches proof explanation (`proof_explain`). The two heavy halves live in sibling modules:
- `proof_answer_select.py` — decides WHICH answer bindings survive: tier ranking (`_ans_object_tier`/`_filter_by_best_tier`: concrete > Skolem > population), `$list` measure-value preference (`_prefer_measure_value_answers`), unbound-var drop, class-name-leak and tautological-population filters, and proof deduplication (`_deduplicate_proofs`). `@what_query` preference is split by query shape (`_what_query_is_relational`): a RELATIONAL what-query (answer var is a relatum of `is_rel2`/`has_degree_rel2`, e.g. "What is X afraid of?") prefers the class over a concrete instance (`population_beats_concrete` in `_filter_by_best_tier`) → "A cat." not "Emily."; a CLASSIFICATION what-query (answer var is the entity of `isa`, "What is an Estonian city?") keeps the concrete (`Tallinn`).
- `proof_answer_format.py` — renders the surviving bindings into English: bool (`_format_bool_answer`), who/what (`_format_who_answers`), where/when (`_format_prep_answers`), generic value join (`_format_answers`), confidence labels, Skolem-to-class resolution (`_resolve_what_skolem_answers`), plus the query-shape probes (`_is_who_query`/`_is_what_query`/`_is_prep_query`/`_extract_askvars`) that `process_proof` dispatches on
- `proof_explain.py` — generates English proof explanations from prover proof steps
- `proof_render.py` — facade module re-exporting from `proof_utils`, `proof_english`, `proof_logic`
- `proof_utils.py` — entity naming, Skolem type resolution, render context state, ambiguity detection
- `proof_english.py` — atom/clause → English rendering; table-driven predicate dispatch via `_PRED_TABLE` plus a per-clause `_ClauseRenderCtx` driving variable phrasing (`_intro`: `"some X"` / `"an event E"` / `"a situation V"` / `"the situation W0"` / `"the flying event sk0 of Mike 1"`).  Two-pass render (classify → conditions before consequents) with R1 (drop tautological isa), R3 (situation prefix on world args), R7 (helper-predicate templates: moved/transferred), modal-classifier reorder in pure-negative clauses, isa-bundling (`"some penguin X"`) gated on pure-negative, and a Skolem-fn seen-tracker that flips first → short form (`"the flying event sk0 of Mike 1"` → `"sk0 of Mike 1"`).  See DOCUMENTATION.md §5.9 for the full extension guide.
- `proof_logic.py` — traditional `pred(arg,...)` and JSON logic syntax rendering
- `linguistics.py` — pure English heuristics (articles, verb conjugation, comparatives, gerunds); used by proof_english.py
- `prover.py` — invokes the `gk` binary subprocess; `call_prover(logic)`; auto-selects unit strategy when equalities with function terms detected
- `cache.py` — SQLite-backed cache for LLM responses and prover results
- `globals.py` — global `options` dict and file paths (uses `os.path` for absolute paths)
- `pretty.py` — JSON pretty-printer; `pp_str/pp_logic/pp_stage1/pp_stage2`; Style B layout with `noquotes` mode
- `utils.py` — utility functions: `debug_print`, `clause_list_to_json`
- `semnormalize.py` — post-clausification semantic normalization: antonym folding (flip polarity + replace word) and canonical word substitution; skips `$ctxt` terms; handles disjunctive clauses
- `data_canonicals.py` — (generated) `CANONICALS` dict: ~752 Tier A `{variant: canonical}` entries from `mkdata/syn_{a,n,v}_rewrite.txt`
- `data_antonyms.py` — (generated) `ANTONYMS` dict: ~850 `{word: antonym}` entries from `mkdata/ant_{a,n,v}.txt` (kinship/gender/spatial/temporal/colour pairs blocked via `BLOCKED_ANTONYM_WORDS`; pairs whose target is itself a `CANONICALS` key are deferred to exclusion-axiom emission instead of rewriting, to prevent semnormalize Pass 2 from chain-substituting to an unrelated sense)
- `data_synonyms.py` — (generated) `SOFT_SYNONYMS` dict: ~12K words, bidirectional `{word: [(other, score, pos), ...]}` index from `mkdata/syn_{a,n,v}_soft_axioms.txt`
- `data_exclusions.py` — (generated) `EXCLUSION_GROUPS` + `EXCLUSION_INDEX` from `mkdata/excl_a.txt` and `mkdata/excl_n.txt` (the noun-mutex groups)
- `axiom_vocab.py` — extracts and caches content words from axiom files (e.g. `axioms_std.js`); used to restrict synonym/exclusion injection to pairs where both sides appear in the problem or axioms
- `stage_sanity.py` — structural sanity checks for Stage-1/Stage-2 LLM output. Stage-2 checks: free-variable references outside binder scope (case 259); misplaced `state_time` inside formula body (case 37); query `isa(CAT, VAR)` dropping Stage-1's specific noun (case 136); predicate-arity violations; events missing `isa(activity, E)` or any thematic role; missing `@question` / `ask` wrapper; entity-id prefix typos. Stage-1 checks: missing `wh_placeholder` for wh-questions; entity used as unit-level location (case 148 — gemini/gpt put concrete entity in `location` field, polluting `$ctxt`). Framework supports a corrective retry loop in `llmparse.py`: see DOCUMENTATION.md §7.8

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

**Soft synonym axioms** (`inject_soft_synonyms` in `lc_post_inject.py`):
- Scans clause list for words in `SOFT_SYNONYMS`
- Emits biconditional clauses: `[-has_property, W, X, Ct], [has_property, OTHER, X, Ct]`
- Templates: `has property` for adjectives (gradable normalizer promotes later), `isa` for nouns, `has type` for verbs
- Uses a single free variable `?:Ct` for context (unifies with any `$ctxt` term)
- Two-side restriction (`REQUIRE_BOTH_SIDES = True`): only emits if other side also appears in input clauses or axiom file vocabulary

**Exclusion axioms** (`inject_exclusion_axioms` in `lc_post_inject.py`):
- Scans clause list for words in `EXCLUSION_INDEX`
- For groups with 2+ members present, emits pairwise exclusion clauses
- `needs_blocker=False` groups: hard exclusion `[-has_property, W1, X, Ct], [-has_property, W2, X, Ct]`
- `needs_blocker=True` groups: two defeasible axioms per pair with `$block` on each side
- Five atom shapes by group id: default `has_property` (adjectives); `_IS_REL2_EXCL_GROUPS` (MONTH/DAY_OF_WEEK/SEASON) use `is rel2` with target at arg 3; `_IS_REL2_PREP_GROUPS` (SPATIAL_*, TEMPORAL_ORDER) use `is rel2` with preposition at arg 1 plus two free entity variables; `_HAS_DEGREE_REL2_PREP_GROUPS` (PROXIMITY) emit two asymmetric axioms per pair — positive side any-degree, antonym side `"none"` intensity, shared `?:RC`; `_ISA_EXCL_GROUPS` (NOUN_* — see `mkdata/excl_n.txt`) emit BOTH same-entity shortcut `[¬isa(w1, X), ¬isa(w2, X)]` AND cross-entity inequality `[¬isa(w1, X), ¬isa(w2, Y), ¬=(X, Y)]`. The cross-entity form covers distinctness reasoning when the prover has two different entities; the shortcut allows direct refutation without paramodulation through equality.
- `MANUAL_ANTONYMS` (in `mkdata/build_solver_data.py`) contributes synthetic `MANUAL_ADJ_*` 2-member exclusion groups (adjective pairs like `broken/intact`); it no longer feeds ANTONYMS rewriting
- Chain-rejected antonym pairs (where the ANTONYMS target is also a CANONICALS key) are deferred from `build_antonyms` to `build_exclusions` and emitted as synthetic `ANT_<W1>_<W2>` defeasible adjective exclusion groups (~65 pairs). Same runtime template as `MANUAL_ADJ_*`
- Spatial/temporal preposition subsumption (under → below, prior_to → before, etc.) lives as static axioms in `axioms_std.js` §7c/7d. Preposition surface-form canonicalisation ("in front of" → "in_front_of") happens pre-clausification in `lc_rewrites._PREP_CANONICAL`. See DOCUMENTATION.md §9.5.
- `(on, under)` and `(on, below)` strict mutex pairs live statically in `axioms_std.js` §7e (next to the existing `(above, below)` etc.). They don't fit the dynamic-mutex group template — there's no `excl_n.txt` group containing both `on` and `under`/`below`.

**Cross-group noun mutex** (`inject_isa_cross_group_axioms` in `lc_post_inject.py`):
- Layer 2 of the noun-mutex story (Layer 1 is the within-group `_ISA_EXCL_GROUPS` branch above).
- For pairs `(w1, w2)` from DIFFERENT `_ISA_EXCL_GROUPS` groups (e.g. `car` in NOUN_VEHICLE, `animal` in NOUN_TOP_LEVEL), emits the same two shapes as Layer 1 (same-entity shortcut + cross-entity inequality).
- Same REQUIRE_BOTH_SIDES gating.

**Carrier vocabulary lift** (`inject_carrier_lifts` in `lc_post_inject.py`):
- Static list `_CARRIER_NOUNS = {plate, tray, saucer, dish, newspaper, napkin, tablecloth, mat, rug, carpet}`.
- For each present noun, emits one lifting clause `[-isa <noun> ?:X ?:Ctxt, isa "carrier" ?:X ?:Ctxt]`.
- Consumed by the static carrier-transparency axiom in `axioms_std.js` §7f. Handles "pizza on plate, plate on table → pizza on table".

**Verb-result-state bridges** (`inject_verb_result_state_axioms` in `lc_post_inject.py`):
- Pair list `_VERB_RESULT_STATES = {(destroy, destroyed), (break, broken), (damage, damaged), (complete, completed), (kill, killed), (repair, repaired)}` — `(finish, finished)` is covered by a static axiom in `axioms_std.js` and not duplicated here.
- For each pair whose verb appears in input or axiom_vocab, emits TWO defeasible (0.9) bridges to handle both Stage-2 encodings:
  - **Bridge A** (event-based, gemini/deepseek): `has type E V Ct + has target E X Ct + next W W2 → has property <pp> X [present W2 ...]`.
  - **Bridge B** (stative property-name, claude): `has property V X [_ W _ _ _] + next W W2 → has property <pp> X [present W2 ...]`.
- Both target `present @ next-world` so mutex axioms fire on the question's present-tense reading.
- Wired into `rawlogic_convert` BEFORE `inject_exclusion_axioms` so result-state words become eligible for the exclusion injector's REQUIRE_BOTH_SIDES check (e.g. enables `destroyed/intact` mutex when "destroy" appears).
- Closes cases 156 (True) and 157 (False) on all three LLMs.

**MANUAL_GRADABLE_ANTONYMS** (`mkdata/build_solver_data.py`):
- Hand-curated dict of gradable adjective antonym pairs that should NOT polarity-flip via ANTONYMS (the flip negates the assertion, defeating cross-world frame propagation in §6).
- Initial pairs: `expensive/cheap`, `destroyed/intact`. Emits defeasible `MANUAL_ADJ_GRAD_<W1>_<W2>` exclusion groups (`needs_blocker=True`) via `build_exclusions`.
- `build_antonyms` filters these pairs out of ANTONYMS so they flow exclusively through the exclusion path.
- Closes case 55 (claude/deepseek "bicycle was expensive / was cheap?" → False) and contributes to case 157.

**X2 direct-support uniqueness** (axioms_std.js §7g, static):
- Strict — `on(X,Y1) ∧ on(X,Y2) → Y1 = Y2` with four `$block` escapes for stacked / part-of configurations.
- Combined with entity UNA via `#:` (`lc_post_una.apply_una`), forces contradiction when two distinct Stage-1 entities are claimed as `on`-targets of the same X.
- Closes case 148 ("pizza on table, ask pizza on floor?" → False).
- For LLMs that introduce a Skolem for "the floor" (definite description), UNA does NOT directly contradict — but the Layer-1 noun-mutex axioms for NOUN_FURNITURE_FIXTURE provide an alternate path via paramodulation.

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

### Modal Classifiers (2026-05-14 rework)

Modality is encoded by **arity-1 classifier predicates on Davidsonian
event variables**, attached as the LAST conjunct of the event's outer
`and` block:

```
["isa","activity","E"], ["has type","E","fly"], ["has actor","E","X"],
["capability","E"]
```

Eight Stage-2 classifiers map 1:1 with the Stage-1 `mode` enum:
`typical` (habitual), `capability`, `necessity`, `obligation`,
`volition`, `intention`, `expectation`, `speech_act`.  The four
mental/speech modes (volition / intention / expectation / speech_act)
use **two-event reification**: an outer event E1 with the classifier
and a nested inner event E2 linked by `["has content","E1","E2"]`.

A ninth classifier — `actuality(E)` — marks real events and is
**injected by the pipeline** in `lc_rewrites.inject_actuality` after
Stage-2 parses but before clausification.  Stage 2 deliberately does
not emit it.  Injection rule: every `and`-block introducing
`isa(activity, E)` gets `["actuality", E]` appended unless (a) one of
the eight Stage-2 classifiers already applies to E or (b) E appears as
the second argument of `has_content` anywhere (i.e., E is an inner
content event of a two-event reification).  `actuality` is hidden from
English rendering (`proof_english._render_atom`) since it is pipeline
metadata.

Phase-4 axiom support is one defeasible bridge in `axioms_std.js` §5.1
that derives `capability(E)` from `actuality(E)`, gated by a single
`$block` for strict `¬capability(E)` overrides (penguin negations).
Modal events and inner content events carry no `actuality` marker, so
the bridge does not fire on them by construction.

Grammatical tense on Davidsonian events lives on the event itself via
`["has time", E, "past"|"present"|"future", "in"]` (Plan A
canonicalisation).  Non-Davidsonian atoms still receive tense via
`$ctxt.Time` or `@time` wrappers.

### Prompt Files (`prompts/`)

```
prompts/stage1_instructions_full.txt   -- Stage 1 system prompt instructions
prompts/stage1_checklist_full.txt      -- Stage 1 procedural checklist
prompts/stage1_examples.txt            -- Stage 1 few-shot examples
prompts/stage2_instructions_full.txt   -- Stage 2 system prompt instructions
prompts/stage2_checklist_full.txt      -- Stage 2 procedural checklist
prompts/stage2_examples.txt            -- Stage 2 few-shot examples
```

`prompts/tmparchive/` holds historical prompt versions.

### LLM Configuration (`solver/llmcall.py`)

```python
use_llm          = "gemini"              # "gpt" | "claude" | "gemini" | "deepseek"
claudeversion    = "claude-sonnet-4-6"
gptversion       = "gpt-5.1"
geminiversion    = "gemini-2.5-flash"
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

- `tests/tests_core.py` — list of `[id, input, expected]` triples for the core pipeline
- `testresults/core/<llm>/case_NNNN.json` — latest batch results per LLM (input, expected,
  answer, correctness, stage1/stage2/clauses/gk_command/proof); the primary debug input
- `testresults/core/all4_failed.txt`, `failed_cases.txt` — triage lists of failing cases

## Debug Case Workflow

When the user says **"Debug case N"** (where N is a case id in `testfixlog_june.txt` or in the
`testresults/core/all4_failed.txt` / `failed_cases.txt` lists):

1. **Read the four batch result files** for Case N — one per LLM:
   `testresults/core/{claude,gpt,gemini,deepseek}/case_NNNN.json` (zero-padded to 4 digits,
   e.g. `case_0033.json`). Each JSON already contains `input_text`, `expected_answer`,
   `answer`, `correctness`, and the full pipeline artifacts: `stage1`, `stage2`, `clauses`,
   `gk_command`, `proof`. This is the primary input — no need to re-run the solver to inspect
   the parse and proof. (These come straight from the SQLite LLM cache, so they match what a
   fresh `solve.py` run would produce.)

   For fuller `-debug -explain -logic` logs (raw trace, prover params), run
   `python3 examine.py N`: it looks up case N in `tests/tests_core.py`, runs all four LLMs
   **sequentially** (cache-served, so fast; no UDP), and writes
   `debug/eN_{gemini,claude,gpt,deepseek}.txt`. These logs live under `debug/`, outside
   `testresults/core/`, so they never disturb the batch results.

2. **Note the `Input:` text and `Expected:` value** — from the JSON (`input_text`,
   `expected_answer`) and/or the `testfixlog_june.txt` entry if one exists.

3. **Compare across all four LLMs** — read the JSONs (or the `debug/eN_*.txt` logs) fully,
   comparing answers and the logic/proof output. If you need the raw LLM responses or prover
   params, the `examine.py` logs have them, or run `python3 solver/solve.py -debug -json -llm
   NAME "..."`. For a UDP-pipeline reference answer (not collected in the batch and not run by
   `examine.py`), run the udppipe solver manually — include it per the standing "always
   include UDP" guidance when it is informative.

4. **Examine Stage 1 and Stage 2 outputs** — a correct final answer is not sufficient.
   Compare the `stage1` and `stage2` JSON across all LLMs. Minor stylistic differences
   between LLMs are OK, but report any major conceptual differences (e.g., wrong entity
   types, missing isa guards, flat vs nested quantifier structure, dropped conditions).
   Both stages must be correct, not just the final answer.

5. **Assess the Expected value** — form an independent opinion on whether the `Expected:`
   value is the correct answer under a normal interpretation of the input, or whether it
   should be changed, or whether there are good alternatives. (We may remove or fix the test
   case itself.) A UDP-pipeline answer, when obtained, is correct in most but not all cases.

6. **Analyze errors** — if any LLM pipeline gives an incorrect or suboptimal answer,
   analyze the root cause (stage-1 parse, stage-2 logic, logconvert, prover input, proof
   post-processing, etc.).

7. **Test with -nocontext if $ctxt suspected** — if the failure looks like a world/tense
   mismatch in $ctxt, run `python3 solver/solve.py -nocontext "..."` on the same input.
   If it succeeds without context but fails with, the issue is $ctxt injection, not logic.

8. **Simplify if uncertain** — if the root cause is unclear, construct a simpler version of
   the input text that isolates the suspected issue, run `python3 solver/solve.py ...` on it,
   and examine the result. Repeat as needed.

9. **Prover-timeout suspected?** — if the failure looks like the prover may simply be
   running out of time on a complex query (not a logic bug), try in this order:
   (a) run without `axioms_std.js` (smaller search space — pass an empty axiom file or
       use the `-axiomfiles` flag if available) to see if the axiom file is the bottleneck;
   (b) swap the strategy: `{"strategy": ["unit"], "query_preference": 1}` or
       `{"strategy": ["query_focus"], "query_preference": 1}` — these often close proofs
       that `negative_pref/posunitpara` (the current default) doesn't;
   (c) only as a last resort, increase `-seconds` to confirm the proof exists.
   If one of the alternate strategies works much faster, the default may need to change.

10. **Write analysis and fix plan** — summarize the root cause(s) of any errors and propose a
   concrete plan for fixing. Do **not** write any code or modify any files at this stage.

**Fix scope (current campaign):** fixes go into **pipeline code, axioms, or test criteria**
(including removing or correcting a bad test case). **Leave the prompt files unchanged.** If a
case cannot be fixed without modifying `prompts/`, postpone it — record the diagnosis in
`testfixlog_june.txt` and move on rather than touching a prompt.

## Register Fix Workflow

When the user says **"Register fix for case N"** — assuming the debug analysis was done,
a fix was implemented, and it has been verified to work:

1. **Read the Case N entry in `testfixlog_june.txt`** to see its current state. If the case has
   no entry yet, create one (Case / Input / Expected / Received, matching the file's style).
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

- `runtests.py` — batch runner: every `[id,input,expected]` case × N LLMs in parallel, one
  JSON per (case, llm) under `testresults/<name>/<llm>/case_NNNN.json`, with a live
  `summary.json`. Resumes by skipping existing files; `-redo`/`-redo-errors` override. See
  DOCUMENTATION.md §10.
- `nlpsimplecollect.py` — collect LLM parsing results for a test file
- `nlpsimpleconv.py` — parse and clean raw collected results
- `collectmultillmconv.py` — orchestrate multiple LLM providers in one collection run
- `comparellmconv.py` — compare Stage-1 outputs from multiple LLM runs
- `checkprompt.py` — validate JSON in prompt files
- `run_pretty_check.py` — run `rawlogic_convert` on 10 examples and pretty-print results
