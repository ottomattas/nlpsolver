# Proof Rendering in English

This document describes how `llmpipe` renders theorem prover proofs as
human-readable English explanations.  It covers entity naming, atom-to-English
translation, clause rendering, proof step formatting, and the dual-mode
logic display (traditional and JSON).

For the underlying data representations see `ENCODINGS.md`.
For implementation details see `DOCUMENTATION.md`.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Entity Naming](#2-entity-naming)
3. [Atom-to-English Translation](#3-atom-to-english-translation)
4. [Clause Rendering](#4-clause-rendering)
5. [Proof Explanation Structure](#5-proof-explanation-structure)
6. [Logic Display Modes](#6-logic-display-modes)
7. [Examples](#7-examples)

---

## 1. Overview

When the `-explain` flag is used, the pipeline renders a step-by-step proof
explanation after the answer.  The explanation has three sections:

1. **Sentences used** — which input sentences contributed to the proof
2. **Knowledge used** — background axioms used (if any)
3. **Proof steps** — the logical derivation in English, optionally with
   formal logic notation underneath each step

The rendering pipeline is split across three modules:

| Module | Responsibility |
|--------|---------------|
| `proof_render.py` | Atom/clause → English; entity naming; table-driven predicate dispatch |
| `proof_explain.py` | Proof structure: step numbering, sentence map, explanation assembly |
| `entity_map.py` | Display names for entities from Stage-1 metadata |
| `procproofs.py` | Answer extraction, formatting, confidence display |

---

## 2. Entity Naming

Entity display names are computed by `entity_name()` in `proof_render.py`,
with display maps built by `entity_map.py`.

### 2.1 Naming Rules

| Entity type | Example ID | Display name | Rule |
|-------------|-----------|-------------|------|
| Proper noun (unique) | `"John 1"` | `John` | Strip trailing number when only one John exists |
| Proper noun (ambiguous) | `"John 1"` / `"John 3"` | `John 1` / `John 3` | Keep number to disambiguate |
| Common noun (unique) | `"car 2"` | `the car` or `car B` | `the NOUN` from entity_map, or safe-letter fallback in proofs |
| Common noun (ambiguous) | `"car 1"` / `"car 2"` | `the red car` / `the black car` | Qualifier adjectives from ASU text to disambiguate |
| Skolem constant | `"sk0"` | `some activity act1` (first), `act1` (after) | Type from `isa(TYPE,skN)` in proof; informative rename; "some TYPE" on first mention only |
| Skolem function | `["sk0","?:X"]` | `the eating by X` | Verb + actor/target from event context |
| Variable | `"?:X"` | `X` | Strip `?:` prefix; numeric vars like `?:2006` → `E1` (short rename) |
| Population constant | `"$some_car"` | `a car` | Strip `$some_` prefix, add article |
| Population negative | `"$some_not_car"` | `a non-car` | Strip `$some_not_`, add "non-" |

### 2.2 Proof Mode

In proof rendering, `entity_name()` operates in `proof_mode=True`:
- Single common-noun entities skip the entity_map (avoids qualifier-predicate
  redundancy like "the very big mouse is a very big mouse")
- Multiple same-base entities still use entity_map for disambiguation
- Proper nouns always use entity_map

### 2.3 JSON Mode

When `-json` is set, `entity_name()` returns raw logic IDs
(`"car 2"`, `"sk0"`, `"John 1"`) so English directly mirrors the JSON output.

---

## 3. Atom-to-English Translation

Atoms are rendered by `_render_atom()` using the table-driven `_PRED_TABLE`.
Each predicate maps to `(min_args, pos_renderer, neg_renderer)`.

### 3.1 Predicate Table

| Predicate | Positive | Negative |
|-----------|----------|----------|
| `isa` | `John is a man` | `John is not a man` |
| `has property` | `car B is red` | `car B is not red` |
| `have` | `John has car B` | `John does not have car B` |
| `has part` | `bird A has tail B as a part` | `...does not have...` |
| `can` | `John can fly` | `John cannot fly` |
| `is rel2` (preposition) | `John is near Mary` | `John is not near Mary` |
| `is rel2` (verb) | `Eve likes John` | `Eve does not like John` |
| `is rel2` (noun) | `John is sister of Mary` | `John is not sister of Mary` |
| `has degree property` | `John is a tall person` | `John is not a tall person` |
| `has type` | `act1 is a drive event` | `act1 is not a drive event` |
| `has actor` | `John performs act1` | `John does not perform act1` |
| `has target` | `act1 targets car B` | `act1 does not target car B` |
| `has location` | `act1 takes place at park A` | `...does not take place...` |
| `has time` | `act1 happens at past` / `act1 happens at time Z` | `...does not happen...` |
| `next` | `W0 is followed by W1` | `W0 is not followed by W1` |
| `before` | `W0 is before W1` | `W0 is not before W1` |

For `has time`, the word "time" is prepended when the argument is a variable
(`"happens at time Z"`) but omitted for constants (`"happens at past"`).

### 3.2 Verb Detection for is_rel2

Relations that look like verbs (e.g., `"like"`, `"love"`, `"fear"`) are
rendered as conjugated verbs (`"Eve likes John"`) rather than the default
`"is REL of"` pattern.  Detection uses a built-in verb set and suffix
heuristics (`-ed`, `-ing`) from `linguistics.py`.

### 3.3 Degree Properties

`has degree property` rendering adapts to context:

- With variable relclass: `"John is tall"` (relclass omitted)
- With `"none"` or `"entity"` relclass: `"John is big"` (omitted — uninformative)
- With matching entity base: `"the mouse is very big"` (relclass = base → omitted)
- With different relclass: `"John is a tall person"` (relclass shown with article)
- Degree adverbs: `"very"` (high), `"slightly"` (low), none (plain)

### 3.4 isa Rendering

The TYPE argument in `isa` uses the raw type string (not entity_map) to avoid
qualifier leaks: `"John is a man"`, not `"John is a strong man"`.

### 3.5 Special Atoms

| Pattern | Rendering |
|---------|-----------|
| `["$defq0"]` | `answer holds` |
| `["-$defq0"]` (single atom) | `assume for contradiction: the answer is no` |
| `["$defq0","?:X"]` / `["-$defq0","?:X"]` | `...no such answer exists` |
| `["$ans", val]` | `John is an answer` / `the car is an answer` |
| `["$block",...]` | See §4.2 |
| `false` | `Contradiction` |

---

## 4. Clause Rendering

`clause_to_str()` converts a GK proof clause (disjunction of atoms) into
an English if-then sentence.

### 4.1 Clause Structure

A clause like `[[-isa,bird,X], [can,X,fly]]` is rendered as:

> if X is a bird then X can fly

- **Negative atoms** (with `-` prefix) → "if" conditions (rendered positively)
- **Positive atoms** → "then" consequences
- **Pure positive** → disjunction: `"A or B"`
- **All negative** → last negated as conclusion: `"if A then not B"`

Duplicate conditions are removed (e.g., `isa(man,X)` and
`has_degree_property(strong,X,none,man)` both rendering as "X is a man").

### 4.2 Defeasible Clauses ($block)

When a clause contains a `$block` atom whose body matches a positive
conclusion in the same clause, the clause is rendered with "normally"
instead of "except when":

> if X is a bird then normally X can fly

When the `$block` doesn't match (after resolution), it falls back to:

> John is not an animal, except when John is not a small animal

Purely `$block` clauses (no other atoms) render as:

> outstanding exception: John cannot fly

### 4.3 Bridge Steps

Technical `$defq`/`$ans` bridge clauses are rendered as:

> technical answer unwrap step

---

## 5. Proof Explanation Structure

`format_explanation()` in `proof_explain.py` assembles the full explanation.

### 5.1 Sections

```
Explained:

[Confidence 90%.]                          — only if < 100%

Sentences used:
  (1) Birds can fly.                       — input sentences cited in proof
  (2) Tweety is a bird.

[Knowledge used:                           — only if background axioms used
  if ... then ... Why: assumed basic knowledge.]

Proof steps [by contradiction]:            — "by contradiction" if proof ends in false
  (1) if X is a bird then normally X can fly  [sentence 1, confidence 90%]
        isa(bird,X) => can(X,fly)  [block(-can(X,fly))]  @0.9
  ...
  (N) Contradiction  [from steps 5, 6]
        false

[Exceptions checked and not holding:       — only for defeasible proofs
  Tweety cannot fly]
```

### 5.2 Step Attribution

Each step shows its origin in square brackets:

| Origin | Rendering |
|--------|-----------|
| Input sentence | `[sentence 1]` or `[sentence 1, confidence 90%]` |
| Background axiom | `[background knowledge]` |
| Contradiction assumption | `[from question]` or `[assumption]` |
| Derived step | `[from steps 1, 2]` |

### 5.3 Logic Display

When `-logic` is active, each proof step shows the formal clause underneath
the English, indented by 8 spaces:

```
  (1) if X is a bird then normally X can fly  [sentence 1, confidence 90%]
        isa(bird,X) => can(X,fly)  [block(-can(X,fly))]  @0.9
```

The logic format is traditional (`pred(arg,arg)`) by default, or raw JSON
with `-json` (see §6).

---

## 6. Logic Display Modes

### 6.1 Traditional Syntax (default)

Constants are lowercase (`john`, `car_B`), variables are uppercase (`X`, `E1`).
Clauses with negative atoms are rendered as implications:

```
isa(bird,X) => can(X,fly)
```

Negation uses `-`:

```
-can(tweety,fly)
```

`$ctxt` terms are compressed — free-variable components stripped:

```
has_property(red,car_B,$ctxt(past,w0))    — concrete tense and world kept
has_property(tall,X)                       — all-free $ctxt removed entirely
```

Long lines are broken at `=>` and `&` boundaries:

```
isa(man,man_A) & isa(car,car_B) & has_property(red,car_B) =>
    $defq0
```

Confidence shown as `@0.9` suffix. `$block` shown as `[block(-pred(...))]`.

### 6.2 Naming Consistency

Traditional logic names are derived from `entity_name()` to ensure
English and logic refer to the same entity the same way:

| English | Traditional logic |
|---------|------------------|
| `John` | `john` |
| `Eve` | `eve` |
| `car B` | `car_B` |
| `the red car` | `red_car` |
| `act1` | `act1` |

### 6.3 JSON Mode (`-json`)

With `-json`, logic is shown as raw JSON arrays:

```json
[["-isa","bird","?:X"], ["can","?:X","fly"]]
```

English uses raw IDs (`"John 1"`, `"sk0"`, `"car 2"`) to match.

### 6.4 Quantified Formulas

The `formula_to_logic()` function renders Stage-2 formulas with quantifiers
as functions:

```
forall(X,(isa(bird,X) => normally(can(X,fly))))
exists(E,(isa(activity,E) & has_type(E,eat) & has_actor(E,john)))
```

---

## 7. Examples

These examples show the output with `-logic -json` (English + JSON logic).

### 7.1 Simple Proof by Contradiction

**Input:** "Elephants are animals. John is an elephant. Is John an animal?"

```
Proof steps (by contradiction):
  (1) if X is an elephant then X is an animal  [sentence 1]
        [["-isa","elephant","?:X"], ["isa","animal","?:X"]]
  (2) John 1 is an elephant  [sentence 2]
        ["isa","elephant","John 1"]
  (3) John 1 is an animal  [from steps 1, 2]
        ["isa","animal","John 1"]
  (4) if John 1 is an animal then answer holds  [sentence 3]
        [["-isa","animal","John 1"], ["$defq0"]]
  (5) assume for contradiction: the answer is no  [from question]
        ["-$defq0"]
  (6) Contradiction  [from steps 3, 4, 5]
        false
```

### 7.2 Defeasible Proof with Exception Check

**Input:** "Birds can fly. Tweety is a bird. Can Tweety fly?"

```
Confidence 90%.
Proof steps:
  (1) if X is a bird then normally X can fly  [sentence 1, confidence 90%]
        [["$block",["$","bird",1],["$not",["can","?:X","fly",...]]],
         ["can","?:X","fly",...], ["-isa","bird","?:X"]]
  (2) Tweety 1 is a bird  [sentence 2]
        ["isa","bird","Tweety 1"]
  (3) normally Tweety 1 can fly  [from steps 1, 2, confidence 90%]
        [["$block",...], ["can","Tweety 1","fly",...]]
  (4) if Tweety 1 can fly then answer holds  [sentence 3]
        [["$defq0"], ["-can","Tweety 1","fly",...]]
  (5) assume for contradiction: the answer is no  [from question]
        ["-$defq0"]
  (6) outstanding exception: Tweety 1 cannot fly  [from steps 3, 4, 5, confidence 90%]
        ["$block",["$","bird",1],["$not",["can","Tweety 1","fly",...]]]
Exceptions checked and not holding:
  Tweety 1 cannot fly
```

### 7.3 Wh-Question with Background Knowledge

**Input:** "Mary is taller than John. Who is tall?"

```
Knowledge used:
  if Y has a X-relation with Z then Y is X. Why: assumed basic knowledge.
    [["-has degree rel2","?:X","?:Y","?:Z","?:U","?:V","?:W"],
     ["has degree property","?:X","?:Y","none","?:V","?:W"]]
Proof steps:
  (1) Mary 1 is taller than John 2  [sentence 1]
        ["has degree rel2","tall","Mary 1","John 2","high","person",
         ["$ctxt","present","W0","?:X","?:Y"]]
  (2) if Y has a X-relation with Z then Y is X  [background knowledge]
        [["-has degree rel2","?:X","?:Y","?:Z","?:U","?:V","?:W"],
         ["has degree property","?:X","?:Y","none","?:V","?:W"]]
  (3) Mary 1 is a tall person  [from steps 1, 2]
        ["has degree property","tall","Mary 1","none","person",
         ["$ctxt","present","W0","?:X","?:Y"]]
  (4) if X is tall then X is an answer  [from question]
        [["-has degree property","tall","?:X","none","?:Y",
          ["$ctxt","?:Z","?:U","?:V","?:W"]],
         ["$ans","?:X","?:Y","?:Z","?:U","?:V","?:W"]]
  (5) [Mary, person] is an answer  [from steps 3, 4]
        ["$ans","Mary 1","person","present","W0","?:X3","?:Y3"]
```

### 7.4 Event Proof with Relative Clause

**Input:** "A man had a car which a woman bought. The car was red. Who had a red car?"

```
Proof steps:
  (1) if X is red and W has X and X is a car then W is the answer  [sentence 3]
        [["-has property","red","?:X",["$ctxt","?:Y","?:Z","?:U","?:V"]],
         ["-have","?:W","?:X",["$ctxt","?:Y","?:2006","?:U","?:V"]],
         ["-isa","car","?:X"], ["$defq0","?:W"]]
  (2) car 2 is red  [sentence 2]
        ["has property","red","car 2",["$ctxt","past","W2","?:X","?:Y"]]
  (3) if car 2 is a car and X3 has car 2 then X3 is the answer  [from steps 1, 2]
        [["-isa","car","car 2"],
         ["-have","?:X3","car 2",["$ctxt","past","?:Y3","?:Z3","?:U3"]],
         ["$defq0","?:X3"]]
  (4) car 2 is a car  [sentence 1]
        ["isa","car","car 2"]
  (5) if X has car 2 then X is the answer  [from steps 3, 4]
        [["-have","?:X","car 2",["$ctxt","past","?:Y","?:Z","?:U"]],
         ["$defq0","?:X"]]
  (6) man 1 has car 2  [sentence 1]
        ["have","man 1","car 2",["$ctxt","past","W0","?:X","?:Y"]]
  (7) man 1 is the answer  [from steps 5, 6]
        ["$defq0","man 1"]
  (8) technical answer unwrap step  [from question]
        [["-$defq0","?:X"], ["$ans","?:X"]]
  (9) the man is an answer  [from steps 7, 8]
        ["$ans","man 1"]
```

### 7.5 Strict Negation Override

**Input:** "Birds can fly. Penguins cannot fly. Tweety is a penguin. Can Tweety fly?"

```
Proof steps (by contradiction):
  (1) if X can fly then X is not a penguin  [sentence 1]
        [["-can","?:X","fly",["$ctxt","?:Y","?:Z","?:U","?:V"]],
         ["-isa","penguin","?:X"]]
  (2) if answer holds then Tweety 1 can fly  [sentence 3]
        [["-$defq0"], ["can","Tweety 1","fly",["$ctxt","?:X","?:Y","?:Z","?:U"]]]
  (3) answer holds  [assumption]
        ["$defq0"]
  (4) Tweety 1 can fly  [from steps 2, 3]
        ["can","Tweety 1","fly",["$ctxt","?:X","?:Y","?:Z","?:U"]]
  (5) Tweety 1 is not a penguin  [from steps 1, 4]
        ["-isa","penguin","Tweety 1"]
  (6) Tweety 1 is a penguin  [sentence 2]
        ["isa","penguin","Tweety 1"]
  (7) Contradiction  [from steps 5, 6]
        false
```
