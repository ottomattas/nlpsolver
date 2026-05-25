# Debugging Guide

This document describes how to diagnose and fix failures in the `llmpipe` pipeline.
It covers the debugging workflow, diagnostic tools, common failure patterns, the
time/world state system, and the testfixlog conventions.

---

## Table of Contents

1. [Debugging Workflow](#1-debugging-workflow)
2. [Diagnostic Tools](#2-diagnostic-tools)
3. [Failure Taxonomy](#3-failure-taxonomy)
4. [Time and World State Semantics](#4-time-and-world-state-semantics)
5. [testfixlog Format](#5-testfixlog-format)
6. [Case Studies](#6-case-studies)

---

## 1. Debugging Workflow

### 1.1 The Debug/Register Cycle

1. **Run `python3 examine.py N`** — looks up Case N in `testfixlog.txt`, runs all
   five solvers (gemini, claude, gpt, deepseek, udp) in parallel with `-debug -json`,
   writes logs to `eN_gemini.txt`, `eN_claude.txt`, etc.

2. **Read the testfixlog entry** — note the Input, Expected, and Received values.

3. **Compare all five logs** — look at answers, Stage-1 parses, Stage-2 logic, and
   GK clause lists across all LLMs and the UDP pipeline.

4. **Classify the error** — determine where in the pipeline the failure occurs
   (see §3 Failure Taxonomy).

5. **Isolate** — if the root cause is unclear, construct a simpler input that
   isolates the suspected issue. Run `python3 solver/solve.py -logic -json "..."`.

6. **Fix** — apply the appropriate fix (prompt change, code change, axiom change).

7. **Verify** — rerun with all four LLMs. Use `-nollmcache` if prompts changed.

8. **Register** — add Conclusion, Cause, and Fixes fields to the testfixlog entry.

### 1.2 Key Principle

Always check ALL LLMs, not just the default one. Different LLMs produce different
Stage-1/Stage-2 outputs and expose different failure modes.

---

## 2. Diagnostic Tools

### 2.1 Output Levels

The CLI flags form a hierarchy — each level includes all previous:

```
-explain     English proof steps
-logic       + simplified ASU text, sentences-to-clauses, logic under proof steps
-details     + stage-1/2 JSON, prover input/output JSON
-debug       + raw LLM responses, prover params, full trace (implies -json)
```

### 2.2 Key Flags

| Flag | What it shows | When to use |
|------|--------------|-------------|
| `-logic -json` | Sentences-to-clauses + JSON logic in proofs | First look at pipeline output |
| `-details` | Stage-1/2 JSON + prover I/O | Checking LLM parse quality |
| `-debug` | Everything | Deep investigation |
| `-gkin FILE` | Save GK input to file with the GK command | Running GK standalone |
| `-seconds N` | Increase prover time limit | Testing if failure is a timeout |
| `-nollmcache` | Bypass LLM cache | After prompt changes |
| `-llm NAME` | Select a specific LLM | Comparing LLM behavior |

### 2.3 The Sentences-to-Clauses Block

The `=== sentences mapped to clauses ===` block (shown with `-logic`) is the most
useful single view for debugging. It groups GK clauses by source ASU:

```
A man 1 had a car 2.
  isa(person,man_A)
  isa(car,car_B)
  have(man_A,car_B,$ctxt(past,w0))
The car 2 was red.
  has_property(red,car_B,$ctxt(past,w1))
Did the man 1 have the red car 2?
  $defq0 => have(man_A,car_B,$ctxt(past))
  ...
```

Check for:
- Correct predicate choice (`have` vs event reification, `has property` vs `has degree property`)
- $ctxt values — do assertion and query world/tense components allow unification?
- Missing or extra `isa` facts
- Correct entity constants

### 2.4 The GK Input File

Use `-gkin FILE` to save the actual JSON sent to GK. The first line is a comment
with the exact GK command:

```bash
# Copy-paste the command from the first line:
../gk/gk axioms_std.js -seconds 2 myfile.js -defaults ...
```

This helps distinguish "prover can't find the proof" from "the clauses are wrong".

---

## 3. Failure Taxonomy

### 3.1 Stage-1 Parse Errors

**Symptoms:** Correct LLM answer differs from incorrect LLM answer; the Stage-1
JSON shows different entity IDs, types, or metadata.

| Error | Example | Where to look |
|-------|---------|---------------|
| Wrong entity resolution | "The car" resolved to car 1 instead of car 2 | Stage-1 entities, coreference |
| Wrong ASU type | `situation` instead of `normal_rule` | Stage-1 `type` field |
| Missing tense | No `time: "past"` on a past-tense sentence | Stage-1 `time` field |
| Missing/wrong actions | Stative verb encoded as action, or vice versa | Stage-1 `actions` field |
| Wrong adjective metadata | Missing entry or wrong relclass in `adjectives` | Stage-1 `adjectives` |
| Wrong world assignment | Descriptive info creating unnecessary new world state | Stage-1 `pre_state`/`next_state` |
| Conjunctive query split | "Is X red and big?" split into separate queries | Should be one query ASU |

**Fix:** Edit `prompts/stage1_instructions_full.txt` or `prompts/stage1_examples.txt`.
After changing prompts, run with `-nollmcache`.

### 3.2 Stage-2 Logic Errors

**Symptoms:** Stage-1 looks correct but Stage-2 logic is wrong.

| Error | Example | Where to look |
|-------|---------|---------------|
| Wrong predicate | `has property` when `adjectives` says use `has degree property` | Stage-2 predicates vs adjectives |
| Event reification of stative | `has_type(E,have)` instead of `have(X,Y)` | Stage-2 event encoding |
| Wrong quantifier structure | `exists` where `forall` needed, missing `normally` | Stage-2 formula structure |
| Variable collision | Two `exists E` blocks sharing the same `E` | Stage-2 variable names |
| Wrong entity type | `isa(person,X)` instead of `isa(man,X)` | Stage-2 isa predicates |

**Fix:** Edit `prompts/stage2_instructions_full.txt` or `prompts/stage2_examples.txt`.
The pipeline has a safety-net stative rewriter (`semnormalize.rewrite_stative_events`)
for event-reified statives.

### 3.3 Logconvert / $ctxt Errors

**Symptoms:** Stage-1 and Stage-2 look correct, but GK clauses have wrong $ctxt.

| Error | Example | Where to look |
|-------|---------|---------------|
| World mismatch | Assertion at W0, query at W1 | $ctxt world slot — see §4 |
| Tense mismatch | Assertion "present", query "past" | $ctxt tense slot |
| Shared world variable | All descriptive atoms forced into same world | $ctxt injection |
| Wrong relclass | Query uses "person" but rule uses "bear" | `_coerce_relclass` |
| Missing entity isa | No `isa(man, man 1)` alongside `isa(person, man 1)` | Entity base-word injection |

**Fix:** Code changes in `logconvert.py`. Check `_inject_ctxt_question` and
post-processing passes.

**Quick test:** When you suspect $ctxt world/tense mismatch is blocking a proof,
try the same input with `-nocontext` (or `-simple`). This removes all $ctxt
injection. If the proof succeeds with `-nocontext` but fails without, the issue
is definitely a $ctxt mismatch — not a logic or axiom problem.

### 3.4 Prover / Axiom Errors

**Symptoms:** GK clauses look correct but prover returns "no information".

| Error | Example | Where to look |
|-------|---------|---------------|
| Missing persistence axiom | Fact at W0 can't reach W1 | `axioms_std.js` persistence section |
| Missing tense bridge | Present at W0 doesn't match past at W1 | `axioms_std.js` tense bridging |
| Missing bridge axiom | Event relation can't match direct predicate | `axioms_std.js` event bridges |
| Timeout | Complex biconditional | Try `-seconds 10` |
| Tautological population answer | Population constant proves its own existence | `procproofs.py` filters |

**Fix:** Add axioms to `axioms_std.js` or increase prover time.

### 3.5 Answer Formatting Errors

**Symptoms:** Prover finds right answer but it displays wrong.

| Error | Example | Where to look |
|-------|---------|---------------|
| Wrong entity display name | "the drove bought car" instead of "the car" | `entity_map.py` |
| Multiple answers | Population + concrete answer | `_filter_by_best_tier` |
| Wrong confidence | Shows 90% when should be 100% | Confidence propagation |

---

## 4. Time and World State Semantics

### 4.1 World States

World states (W0, W1, W2, ...) represent successive states of the world as the
story or situation evolves. A state change occurs when an event modifies the
situation:

```
"John had an apple."               → state W0
"John gave the apple to Mike."     → state change W0 → W1
"Mike ate the apple."              → state change W1 → W2
```

So W0 = before the apple is given, W1 = after the apple is given, W2 = after
the apple is eaten. World states represent different versions of the world,
not merely timestamps.

State changes are triggered by:
- Possession changes (give, buy, sell)
- Location changes (go, arrive, leave, move)
- Physical changes (break, eat, open, close)
- Narrative events that must occur in sequence

Descriptive information (adjectives, relative clauses) does NOT create new states.

### 4.2 Relative Tense

Each predicate is evaluated relative to a world state using the `$ctxt` term:

```
["$ctxt", TENSE, WORLD, LOCATION, HOLDER]
```

Only the first two components are relevant for time:

| TENSE | Meaning |
|-------|---------|
| `present` | The predicate holds **at** WORLD |
| `past` | The predicate held at some **earlier** world state (before WORLD) |
| `future` | The predicate holds at some **later** world state (after WORLD) |
| `timeless` | The predicate does not depend on world progression |

**Examples:**

```json
["have","John","apple",["$ctxt","present","W0",...]]
```
John has the apple **at** world state W0.

```json
["have","John","apple",["$ctxt","past","W2",...]]
```
John had the apple at some world state **before** W2.

```json
["have","Mark","apple",["$ctxt","future","W0",...]]
```
Mark will have the apple at some world state **after** W0.

### 4.3 Narrative Defaults

For ordinary statements in a story:
- The clause is interpreted as `present` at its own world state
- State changes are represented with `next_state`
- Rules use free variables for both tense and world (match any context)

### 4.4 How $ctxt Is Injected

The pipeline injects `$ctxt` after clausification. The world and tense values
come from different sources depending on the clause type:

| Clause type | Tense source | World source |
|-------------|-------------|--------------|
| Rules (forall/implies) | free variable | free variable |
| Assertions (holds W F) | Stage-1 `time` or `"present"` | `pre_state` or W from holds |
| Questions — descriptive atoms | Stage-1 `time` or free var | free var (independent per atom) |
| Questions — stative matrix | Stage-1 `time` or free var | free var |
| Questions — dynamic matrix | Stage-1 `time` or free var | `pre_state` or free var |

### 4.5 The Three-Way Question Split

In `$defq` yes/no questions, atoms are classified into three categories for
world assignment:

**Descriptive** (always free-var world, independent per atom):
`isa`, event predicates (`has type`, `has actor`, `has target`, `has time`,
`has location`, etc.), `typical`, `typically`. Also `has_property` /
`has_degree_property` when a main relation is present (property used as
restrictive noun modifier, e.g., "the **red** car" in "Did the man have the
red car?").

**Stative matrix** (free-var world):
`have`, `can`, `has part`. These describe persistent states — the question
asks whether the state holds in any world, not specifically in W1.

**Dynamic matrix** (query's world):
`is_rel2`, `has_degree_rel2`, and property predicates when they ARE the main
query (no main relation present, e.g., "Is the car red?").

Each descriptive/stative atom gets its OWN fresh world variable so they can
independently match assertions in different world states.

### 4.6 Why World Mismatches Occur

A typical failure scenario:

1. Sentence 1: "A man had a car." → `have(man,car,$ctxt(past,W0))`
2. Sentence 2: "A woman bought the car." → creates state change W0→W1
3. Sentence 3: "The car was red." → `has_property(red,car,$ctxt(past,W1))`
4. Query: "The man had a red car?" → query `pre_state` = W1

If the query's `have` atom gets concrete W1, it can't unify with the assertion's
W0. The persistence axiom `have(X,Y,$ctxt(T,W0,...)) => have(X,Y,$ctxt(T,W1,...))`
exists but requires the prover to chain through defeasible reasoning inside a
complex biconditional.

The fix: stative matrix predicates (`have`) get free-var world in questions,
allowing direct unification with any world.

### 4.7 Persistence and Tense Bridging Axioms

`axioms_std.js` contains axioms for reasoning across world states:

**World ordering:**
- `next(W0,W1)` — W1 is the immediate successor of W0 (generated by Stage 2)
- `before(W0,W1)` — W0 is an earlier world state than W1 (derived from `next` + transitivity)

**Tense bridging:** If a predicate holds at world W (present tense), it also
held in the past relative to any later world:
```
pred(X,$ctxt(present,W,...)) & before(W,W2) => pred(X,$ctxt(past,W2,...))
```

**Persistence:** Facts persist forward across world states (defeasible):
```
have(X,Y,$ctxt(T,W0,...)) => have(X,Y,$ctxt(T,W1,...))  [defeasible]
have(X,Y,$ctxt(T,W1,...)) => have(X,Y,$ctxt(T,W2,...))  [defeasible]
```

Coverage: `have`, `has property`, `has degree property`, `can`, `has part`,
`is rel2`, `has degree rel2` — each across W0→W1→W2→W3.

These are defeasible (carry `$block`): a state change can defeat persistence.
"John had an apple. John gave the apple to Mike." — the persistence of
`have(John,apple)` from W0 to W1 is blocked by the give event.

---

## 5. testfixlog Format

### 5.1 Entry Structure

```
  Case: NNN
  Input:    The natural language input text
  Expected: The correct answer (e.g., True., False., 'John.', Unknown.)
  Received: What the pipeline actually produced
  [Conclusion: Fixed. / Semi-fixed. / Unsolved.]
  [Cause: Brief description of the root cause]
  [Fixes: What was changed to fix it]
  [Comment: Additional notes]
  [Outstanding: Action items for future work]
```

### 5.2 Status Values

| Status | Meaning |
|--------|---------|
| (no Conclusion) | Unprocessed — not yet investigated |
| `Fixed` | All four LLMs return the correct answer |
| `Semi-fixed` | Some LLMs fixed, others still fail |
| `Unsolved` | Investigated but no fix applied |

### 5.3 Conventions

- Keep all text short — one or two lines per field
- Reference related cases: "Same as case NNN"
- Do not rewrite or remove existing fields — only add
- The `Cause` field should name WHERE the failure occurs (Stage-1, Stage-2, logconvert, prover)
- The `Fixes` field should name WHAT was changed (prompt section, code function, axiom)

### 5.4 Current Statistics (2026-03-15)

- Total cases: 349
- Fixed: 86
- Semi-fixed: 9
- Unsolved: 1
- Unprocessed: 253

---

## 6. Case Studies

### 6.1 Case 103: Stative Event Reification

**Input:** "A man had a car which a woman bought. The car was red. The man had a red car?"

**Problem:** GPT nondeterministically event-reified "had" as `has_type(E,have)`
instead of `have(man,car)`. The query used direct `have` — predicates didn't match.

**Diagnosis:** Compared GPT (Unknown) with Claude (True). Stage-2 logic differed:
GPT used Davidsonian event encoding for "had", Claude used direct `have`.

**Fixes:** Stage-2 prompt updated to use direct predicates for statives.
Added `semnormalize.rewrite_stative_events` as safety net.

### 6.2 Case 105: World Mismatch in Relative Clauses

**Input:** "A man had a car which a woman bought. The car was red. The man had
the red car which a woman bought?"

**Problem:** Query's "bought" event atoms had concrete world W1, assertion's were
at W0. Also, all descriptive atoms shared one free-var world, forcing unification.

**Diagnosis:** Checked $ctxt values in sentences-to-clauses block. Assertion buy
at `$ctxt(past,W0)`, query buy at `$ctxt(past,W1)`.

**Fixes:** Descriptive atoms in questions get free-var world. Each descriptive
atom gets its OWN independent free variable (not shared).

### 6.3 Case 1147: Multiple Layers of Failure

**Input:** "A man who ate breakfast had a car which a woman bought. The car was red.
A man who ate breakfast had a red car which a woman bought?"

**Problem:** Multiple independent issues layered on top of each other.

**Diagnosis path:**
1. World mismatch → fixed with descriptive/matrix split
2. Property `has_property(red)` shared world with events → fixed with independent free vars
3. `isa(person, man 1)` but query needed `isa(man, X)` → added entity base-word isa injection
4. Claude/GPT reused variable `E` for both events → Stage-2 prompt fix
5. Matrix `have` had concrete W1 vs assertion W0 → stative matrix predicates get free-var world

**Key insight:** Each fix peeled away one layer. Comparing working LLMs (Gemini)
with failing ones (Claude, GPT) identified exactly which encoding difference
caused each failure.
