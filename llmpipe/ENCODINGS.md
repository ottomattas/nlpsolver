# llmpipe — Encoding Reference

This document describes the three main data representations used in the `llmpipe`
pipeline: Stage-1 ASU JSON, Stage-2 logic JSON, and GK prover input.  Each section
explains the encoding, its purpose, and the key features with small examples.

For implementation details see `DOCUMENTATION.md`.

---

## Table of Contents

1. [Stage-1: Atomic Semantic Units (ASU JSON)](#1-stage-1-atomic-semantic-units)
2. [Stage-2: First-Order Logic JSON](#2-stage-2-first-order-logic-json)
3. [GK Prover Input: Clause List](#3-gk-prover-input-clause-list)
4. [End-to-End Example](#4-end-to-end-example)

---

## 1. Stage-1: Atomic Semantic Units

**Produced by:** Stage-1 LLM call (llmparse.py)
**Consumed by:** Stage-2 LLM call and logconvert.py

Stage 1 converts English text into a list of *sentence packages*.  Each sentence
produces one package containing one or more *Atomic Semantic Units* (ASUs) — minimal
propositions that can be independently true or false.

### 1.1 Top-Level Structure

```json
[
  {
    "raw": "Birds can fly, but penguins cannot.",
    "units": [
      { "unit_id": "S1", "text": "Birds can fly.", ... },
      { "unit_id": "S2", "text": "Penguins cannot fly.", ... }
    ]
  }
]
```

Each `"raw"` field contains one original sentence.  The `"units"` array contains
the ASUs derived from it.  Unit IDs are globally unique (`S1`, `S2`, `S3`, ...).

### 1.2 ASU Types

Every ASU has a `"type"` field:

| Type | Meaning | Example |
|------|---------|---------|
| `real` | Timeless fact about a named entity | "Tallinn is a city." |
| `situation` | Concrete event or state in a narrative | "John drove a car." |
| `strict_rule` | Universal definition/law (forall/implies) | "Elephants are animals." |
| `normal_rule` | Defeasible default (normally/typically) | "Birds can fly." |
| `query` | A question | "Is John an animal?" |

### 1.3 Entities

Each ASU lists its entities with type and optional metadata:

```json
"entities": [
  {"id": "John 1", "type": "concrete", "category": "person"},
  {"id": "car 2", "type": "concrete", "category": "artifact"},
  {"id": "animals", "type": "generic"}
]
```

**Concrete** entities are specific instances (numbered: `"John 1"`, `"car 2"`).
**Generic** entities represent classes or kinds (`"animals"`, `"forest"`).

**Entity IDs** follow these rules:
- Famous names: `"John 1"` + optional `"url"` field for Wikipedia disambiguation
- Concrete common nouns: numbered (`"car 2"`, `"dog 1"`)
- Generic: surface phrase without determiners (`"animals"`, `"forest"`)
- Consistency: the same entity keeps the same ID across all ASUs

**Category** (optional): ontological type — `person`, `animal`, `plant`, `place`,
`organization`, `artifact`, `substance`, `event`, `abstract`.

### 1.4 Scope (Generic Entities)

Generic entities may carry a `"scope"` hint:

| Scope | Meaning | Example |
|-------|---------|---------|
| `dependent` | Per-subject existential (default) | "a tail" in "Dogs have a tail" |
| `global` | One shared instance | "a park" in "All children play in a park" |
| `kind` | Uncountable mass substance (constant) | "water", "gold", "air" |

### 1.5 Actions

Physical acts and capabilities are annotated with the `"actions"` field:

```json
"actions": [{"root": "eat", "mode": "habitual", "roles": {"target": "berries"}}]
```

- **root**: base verb in infinitive form (`"eat"` not `"ate"`)
- **mode**: `habitual` (regular tendency), `capability` (ability), `event` (one-time)
- **roles** (optional): `target`, `location`, `instrument`, `direction`, `manner`, `recipient`

Stative verbs (have, own, like, love, fear, know, believe) are NOT encoded as actions.

### 1.6 Adjectives

All property words are listed in the `"adjectives"` field:

```json
"adjectives": [["tall", "none", "person"], ["red", "none", "none"]]
```

Each entry is `[word, intensity, relclass]`:
- **word**: the adjective (`"tall"`, `"red"`, `"close to"`)
- **intensity**: `"none"` (plain), `"low"` (slightly), `"high"` (very/extremely)
- **relclass**: comparison class (`"person"`, `"car"`) or `"entity"` (generic) or `"none"` (non-gradable like colours)

This field is critical: Stage 2 uses it to decide between `has degree property` and
`has property`.

### 1.7 World States and Time

#### World states

World states (W0, W1, W2, ...) represent successive states of the world as the
story or situation evolves.  A state change occurs when an event modifies the
situation:

```json
{"unit_id": "S1", "text": "John 1 had an apple 2.",
 "pre_state": "W0", "next_state": "W1"}
{"unit_id": "S2", "text": "John 1 gave the apple 2 to Mike 3.",
 "pre_state": "W1", "next_state": "W2"}
{"unit_id": "S3", "text": "Mike 3 ate the apple 2.",
 "pre_state": "W2", "next_state": "W3"}
```

W0 = before the apple is given, W1 = after the apple is given, W2 = after
the apple is eaten.  World states represent different **versions of the world**,
not merely timestamps.

State changes are triggered by:
- Possession changes (give, buy, sell)
- Location changes (go, arrive, leave, move)
- Physical changes (break, eat, open, close)
- Narrative events that must occur in sequence

Descriptive information (adjectives, relative clauses) does NOT create new states
— "The car is red and expensive" stays in the same world.

#### Relative tense

The `"time"` field on an ASU marks tense **relative to the ASU's world state**:

| Value | Meaning |
|-------|---------|
| `"past"` | The predicate held at some **earlier** world state |
| `"present"` | The predicate holds **at** the current world state |
| `"future"` | The predicate will hold at some **later** world state |
| Omitted | Unmarked present (default for plain present-tense statements and rules) |

For example, if an ASU has `"pre_state": "W2"` and `"time": "past"`, its
predicates describe something that was true before W2 — possibly at W0 or W1.

This relative interpretation is carried through to the `$ctxt` context term in
the GK clause list (see §3.4).

#### Explicit time values (dated world states)

When the `"time"` field contains an explicit time value like `"1800"` or `"Monday"`
(rather than a grammatical tense), the pipeline treats it as a **dated world state**:

1. Stage 1 produces `"time": "1800"`, `"time_prep": "during"`, `"state_tense": "past"`.
2. `logconvert.py` recognizes the non-grammatical value and:
   - Keeps `$ctxt` tense as `"present"` (facts are current at that time)
   - Generates a world-time equality: `["=", ["$theof1","time","W0","?:C"], ["$datetime", 1800]]`
   - Preserves the event-level `has_time(E, 1800, "during", ...)` from Stage 2
   - Generates `is_past_world(W0)` from `"state_tense": "past"`
3. For numeric values, bridge axioms in `axioms_std.js` also derive `is_past_world(W0)`
   via `$less(1800, 2026)` (redundant backup).  For non-numeric values like `"Monday"`,
   `state_tense` is the only source.
4. Tense normalization axioms promote `$ctxt(present, W0, ...)` to `$ctxt(past, W0, ...)`
   for all predicates, allowing past-tense questions to match.

The `"state_tense"` field carries the grammatical tense (past/present/future) that
`"time"` cannot hold when it contains an explicit value.  It is only set when `"time"`
is a value, never when `"time"` is already a grammatical tense.

### 1.9 Confidence

Float 0–1 representing logical strength.  Omitted when 1.0.

| Source | Confidence |
|--------|-----------|
| Explicit probability ("30%") | 0.3 |
| Usually/normally | 0.98 |
| Often/probably | 0.8 |
| Sometimes | 0.5 |
| Rarely | 0.2 |
| Some/a/an (existential) | 0.99 |

### 1.10 Other Fields

- **`location`**: entity ID of the location — "John ran in the park" → `"location": "park 2"`
- **`mental_holder` / `mental_attitude`**: for propositional attitudes —
  "John knows that Mary is tall" → `"mental_holder": "John 1"`, `"mental_attitude": "knows"`
- **`epistemic_force`**: `"factive"` (knows), `"non_factive"` (believes), `"counterfactual"` (imagines)
- **`definites`**: for definite possessives — "John's sister" →
  `"definites": [["sister of", "sister 2", "John 1"]]`.
  This triggers the `$theof1` rewrite in lc_postprocess: the flat entity ID (`"sister 2"`)
  is replaced by a canonical function term `["$theof1", "sister", "John 1", CTXT]`
  so that all references to "John's sister" unify as the same object (see §3.7).
- **`wh_placeholder`**: `true` on the entity introduced for who/what/where questions —
  `{"id": "entity", "type": "generic", "wh_placeholder": true}`

### 1.11 Complete Stage-1 Example

**Input:** "Bears eat red berries in a forest. John is a bear. Who eats berries?"

```json
[
  {"raw": "Bears eat red berries in a forest.",
   "units": [
     {"unit_id": "S1",
      "text": "Bears eat red berries in a forest.",
      "type": "normal_rule",
      "entities": [
        {"id": "bears", "type": "generic", "category": "animal"},
        {"id": "berries", "type": "generic", "scope": "dependent"},
        {"id": "forest", "type": "generic", "scope": "dependent", "category": "place"}
      ],
      "actions": [{"root": "eat", "mode": "habitual",
                   "roles": {"target": "berries", "location": "forest"}}],
      "adjectives": [["red", "none", "berry"]],
      "confidence": 0.95}
   ]},
  {"raw": "John is a bear.",
   "units": [
     {"unit_id": "S2",
      "text": "John 1 is a bear.",
      "type": "situation",
      "entities": [{"id": "John 1", "type": "concrete", "category": "person"}]}
   ]},
  {"raw": "Who eats berries?",
   "units": [
     {"unit_id": "S3",
      "text": "Which entity eats berries?",
      "type": "query",
      "entities": [
        {"id": "entity", "type": "generic", "wh_placeholder": true},
        {"id": "berries", "type": "generic"}
      ],
      "actions": [{"root": "eat", "mode": "habitual",
                   "roles": {"target": "berries"}}]}
   ]}
]
```

---

## 2. Stage-2: First-Order Logic JSON

**Produced by:** Stage-2 LLM call (llmparse.py)
**Consumed by:** logconvert.rawlogic_convert()

Stage 2 converts each ASU into first-order predicate logic encoded as nested JSON
lists.

### 2.1 Top-Level Structure

```json
["and",
  ["@id", "S1", PACKAGE],
  ["@id", "S2", PACKAGE],
  ...
]
```

Each ASU produces one `["@id", "Sx", PACKAGE]`.

### 2.2 Package Shapes

```
["holds", W, FORMULA]          — assertion anchored to a world constant
["question", FORMULA]           — yes/no question
["ask", VAR, FORMULA]           — wh-question; VAR is the answer variable
["and", PACKAGE, ["@p","Sx",P]] — package with confidence P (0–1)
```

### 2.3 Logical Connectives

```
["and", A, B, ...]     ["or", A, B, ...]      ["xor", A, B]
["not", A]              ["implies", A, B]       ["=", A, B]
["<", A, B]             [">", A, B]
["forall", "X", A]      ["exists", "X", A]
["question", A]         ["ask", "X", A]
```

### 2.4 Predicates

The predicate inventory is a closed whitelist — no invented predicates.

#### Core Predicates

| Predicate | Arguments | Example |
|-----------|-----------|---------|
| `isa` | TYPE, ENTITY | `["isa", "bird", "John 1"]` |
| `has property` | PROP, ENTITY | `["has property", "red", "car 2"]` |
| `have` | OWNER, OWNED | `["have", "John 1", "car 2"]` |
| `has part` | WHOLE, PART | `["has part", "bird 1", "tail 2"]` |
| `is rel2` | REL, E1, E2 | `["is rel2", "near", "A", "B"]` |
| `can` | ENTITY, ACTION | `["can", "X", "fly"]` |

#### Gradable Predicates

Used when the word appears in the ASU's `adjectives` field:

| Predicate | Arguments | Example |
|-----------|-----------|---------|
| `has degree property` | PROP, ENTITY, DEGREE, RELCLASS | `["has degree property", "tall", "John 1", "none", "person"]` |
| `has degree rel2` | REL, E1, E2, DEGREE, RELCLASS | `["has degree rel2", "close to", "A", "B", "high", "city"]` |

DEGREE values: `"none"`, `"high"` (very), `"low"` (slightly), `"more"`, `"most"`, `"less"`, `"least"`.

#### Event Reification Predicates

Dynamic verbs are encoded as Davidsonian events:

```json
["exists", "E", ["and",
  ["isa", "activity", "E"],
  ["has type", "E", "eat"],
  ["has actor", "E", "John 1"],
  ["has target", "E", "berries"],
  ["has time", "E", "past", "in"]
]]
```

| Predicate | Meaning |
|-----------|---------|
| `isa "activity" E` | E is an event |
| `has type E VERB` | Event type (verb root) |
| `has actor E ENTITY` | Who performs the event |
| `has target E ENTITY` | What the event acts on |
| `has location E ENTITY PREP` | Where the event occurs; PREP is the spatial preposition (`"in"`, `"at"`, `"near"`, etc.) |
| `has instrument E ENTITY` | What tool is used |
| `has manner E MANNER` | How the event is done |
| `has direction E DIR` | Direction of movement |
| `has time E TIME PREP` | When the event occurs; PREP is the temporal preposition (`"in"`, `"on"`, `"during"`, etc.) |
| `typical E` | Marks the event as defeasible (for $block) |
| `typically ENTITY VERB` | Atomic habitual predicate (Track 1) |

#### Structural Predicates

```
["holds", W, F]                — anchor formula F to world state W
["next", W1, W2]               — W2 is the immediate successor of W1
["before", W1, W2]             — W1 is an earlier world state than W2
["=", ["$theof1","time",W,C], ["$datetime",N]]  — world W anchored to time N (numeric)
["state location", W, L]       — location in world state
["normally", F]                — defeasible wrapper
["@time", TIME, ATOM]          — per-predicate time override
["@id", "Sx", F]               — ASU traceability
["@p", "Sx", P]                — confidence annotation
```

Note: `next` is generated by Stage 2 from `next_state` annotations.  `before` is
NOT generated by Stage 2 — it is derived by background axioms in `axioms_std.js`
(e.g., `next(W0,W1) => before(W0,W1)` and transitivity of `before`).

#### Set and Counting Predicates

Stage-2 uses `$setof` to define sets and `$count` for cardinality:

**Stage-2 lambda forms** (what the LLM produces):

```
// Anchored (set owned by a subject — no set id needed):
["$setof", "?:X", ["and", ["isa","car","?:X"], ["prop","red","?:X"], ["have","John 1","?:X"]]]

// Conditions-only (no subject — set id from Stage-1):
["$setof", "?:X", "set 1", ["and", ["isa","elephant","?:X"], ["prop","red","?:X"]]]
```

**Count assertion**: `["=", 3, ["$count", SETOF_TERM]]`

**Distributive actions** over set members:
```
["forall", "?:M",
  ["implies", ["member", "?:M", SETOF_TERM],
    ["exists", "E", [...event body using ?:M...]]]]
```

**Canonical forms** (after programmatic conversion by `lc_sets.py`):

```
// Anchored: anchor predicate extracted, conditions $-prefixed, $arg1 replaces VAR
["$setof", "have", "John 1", ["$and", ["$isa","car","$arg1"], ["$prop","red","$arg1"]]]

// Conditions-only: "id" marker, set_id preserved, no $ prefix
["$setof", "id", "set 1", ["$and", ["isa","elephant","$arg1"], ["prop","red","$arg1"]]]
```

The `$and` arguments are always sorted: `$isa`/`isa` entries first, then
remaining sorted alphabetically.

The conversion also generates:
- **Membership axioms**: `member(M, $setof(...)) <=> conditions(M)` (one per unique pattern)
- **Element instantiation**: concrete individuals `$setK_elI` with all
  set properties, membership, and pairwise distinctness (up to configurable limit)

### 2.5 Quantification Patterns

**Strict rules** use `forall` + `implies`:

```json
["forall", "X", ["implies", ["isa", "elephant", "X"], ["isa", "animal", "X"]]]
```

"Elephants are animals."

**Normal rules** wrap the consequent in `normally`:

```json
["forall", "X", ["implies", ["isa", "bird", "X"],
  ["normally", ["can", "X", "fly"]]]]
```

"Birds can fly."

**Situations** use concrete constants:

```json
["holds", "W0", ["isa", "person", "John 1"]]
```

"John is a person."

**Yes/no questions** use `question`:

```json
["question", ["isa", "animal", "John 1"]]
```

"Is John an animal?"

**Wh-questions** use `ask`:

```json
["ask", "X", ["and", ["isa", "animal", "X"], ["has property", "big", "X"]]]
```

"Who is a big animal?"

### 2.6 Variable Conventions

| Role | Names |
|------|-------|
| Entity | X, Y, Z, X1, Y1 |
| Event | E, E1, E2 |
| Set | S, S1, S2 |
| Count | N |
| Scalar | V |

Variables must always be introduced by a quantifier (`forall` or `exists`) and
used within its scope.

### 2.7 Complete Stage-2 Examples

**"Birds can fly."** (normal_rule, capability, Track 1):

```json
["and",
  ["@id","S1",
    ["holds","W0",
      ["forall","X",
        ["implies", ["isa","bird","X"],
          ["normally", ["can","X","fly"]]]]]]]
```

**"John smiled."** (situation, event, Track 2):

```json
["and",
  ["@id","S1",
    ["and",
      ["holds","W0",
        ["exists","E", ["and",
          ["isa","activity","E"],
          ["has type","E","smile"],
          ["has actor","E","John 1"],
          ["has time","E","past"]]]],
      ["next","W0","W1"]]]]
```

**"Bears eat red berries in a forest."** (normal_rule, habitual, Track 2 with roles):

```json
["and",
  ["@id","S1",
    ["and",
      ["holds","W0",
        ["forall","X",
          ["implies", ["isa","bear","X"],
            ["normally",
              ["exists","E", ["and",
                ["isa","activity","E"],
                ["has type","E","eat"],
                ["has actor","E","X"],
                ["exists","Y", ["and",
                  ["isa","berry","Y"],
                  ["has degree property","red","Y","none","berry"],
                  ["has target","E","Y"]]],
                ["exists","Z", ["and",
                  ["isa","forest","Z"],
                  ["has location","E","Z","in"]]],
                ["typical","E"]]]]]]],
      ["@p","S1",0.95]]]]
```

**"Who is tall?"** (query, wh-question):

```json
["and",
  ["@id","S1",
    ["ask","X",
      ["has degree property","tall","X","none","entity"]]]]
```

**"The man had the car. The car was red."** (two situations with state):

```json
["and",
  ["@id","S1",
    ["holds","W0",
      ["and",
        ["isa","man","man 1"],
        ["isa","car","car 2"],
        ["have","man 1","car 2"]]]],
  ["@id","S2",
    ["holds","W0",
      ["and",
        ["isa","car","car 2"],
        ["has property","red","car 2"]]]]]
```

---

## 3. GK Prover Input: Clause List

**Produced by:** logconvert.rawlogic_convert() + lc_postprocess passes
**Consumed by:** prover.call_prover() → gk binary

The Stage-2 logic JSON is compiled into a flat list of clause dictionaries in
conjunctive normal form (CNF) suitable for the GK theorem prover.

### 3.1 Structure

```json
[
  {"@name": "sent_S1", "@logic": ["isa", "bird", "tweety 1"]},
  {"@name": "sent_S2", "@logic": [
    ["-isa", "bird", "?:X"], ["can", "?:X", "fly"]
  ]},
  {"@name": "sent_S3", "@question": ["can", "tweety 1", "fly"]}
]
```

Each dict has exactly one content key:
- `"@logic"` for assertions (facts and rules)
- `"@question"` for the query

### 3.2 Clause Formats

- **Single atom**: `["pred", arg1, arg2, ...]`
- **Disjunction**: `[["pred1",...], ["pred2",...]]` — represents `pred1 OR pred2`
- **Negated atom**: `["-pred", arg1, ...]` — the `-` prefix negates

A disjunctive clause with negative atoms encodes an implication:
`["-isa","bird","?:X"], ["can","?:X","fly"]` means `isa(bird,X) => can(X,fly)`.

### 3.3 Variables

Any string starting with `?:` is a variable (`"?:X"`, `"?:Fv3"`).  All free
variables in a clause are implicitly universally quantified.  Existential
quantifiers from Stage 2 are eliminated by Skolemization:

- No universal vars in scope → Skolem constant: `"sk0_house"`, `"sk1_car"`, ...
  (type suffix from `isa` in the existential body; plain `"sk0"` if no type found)
- Universal vars in scope → Skolem function: `["sk0", "?:X"]` (plain name, no type suffix)

### 3.4 The $ctxt Context Term

Eligible predicate atoms are augmented with a trailing context term:

```json
["has property", "tall", "John 1", ["$ctxt", "past", "W0", "?:Fv1", "?:Fv2"]]
```

The four `$ctxt` components:

| Position | Meaning | Source |
|----------|---------|--------|
| 1 (tense) | `"past"`, `"present"`, `"future"`, `"timeless"` | ASU `time` field |
| 2 (world) | `"W0"`, `"W1"`, or free var | ASU `pre_state` |
| 3 (location) | Entity ID or free var | ASU `location` |
| 4 (knower) | Entity ID or free var | Mental holder |

#### Tense is relative to the world state

The tense component is interpreted **relative to** the world state, not as an
absolute timestamp:

| $ctxt | Interpretation |
|-------|---------------|
| `$ctxt(present, W0, ...)` | The predicate holds **at** W0 |
| `$ctxt(past, W2, ...)` | The predicate held at some world state **before** W2 |
| `$ctxt(future, W0, ...)` | The predicate will hold at some world state **after** W0 |

Examples:

```json
["have","John 1","apple 2",["$ctxt","present","W0",...]]
```
John has the apple **at** world state W0.

```json
["have","John 1","apple 2",["$ctxt","past","W2",...]]
```
John had the apple at some world state **before** W2.

```json
["have","Mark 3","apple 2",["$ctxt","future","W0",...]]
```
Mark will have the apple at some world state **after** W0.

#### World assignment by clause type

**Rules**: all four components are free variables (match any context).

**Assertions**: concrete world/tense from Stage 1.  A clause in a narrative
defaults to `present` at its own world state.

**Questions**: three-way dispatch:
- Descriptive atoms (isa, event predicates) → each gets its own independent free-var world
- Stative matrix predicates (have, can, has part) → free-var world
- Dynamic matrix predicates (is_rel2, properties as main query) → query's world

#### Eligible predicates

Receive `$ctxt`: `has property`, `have`, `has part`, `can`, `is rel2`,
`has degree property`, `has degree rel2`, event predicates, `typical`, `typically`.

Do NOT receive `$ctxt`: `isa`, `holds`, `next`, `state *`, `kb *`, `@*`, `$*`, `=`, `<`, `>`.

### 3.5 Defeasible Reasoning ($block)

Normal rules produce defeasible clauses with a `$block` literal:

```json
["-isa","bird","?:X"], ["can","?:X","fly"],
  ["$block", ["$","bird",1], ["$not", ["can","?:X","fly"]]]
```

This means: "birds can fly, but this conclusion can be defeated by a more specific
rule."

**Priority mechanism:** The priority `["$","bird",1]` has the form `["$", CLASS, N]`
where CLASS is the subject class and N is a specificity count.  A rule with more
conditions gets a higher N.  For example:

- "Birds can fly" → priority `["$","bird",1]` (1 isa condition)
- "Penguins cannot fly" → priority `["$","bird",2]` (isa penguin + isa bird = more specific)

When the prover finds conflicting conclusions for the same head atom, the rule
with higher N wins — penguins override the general bird rule.  This implements
the specificity preference in defeasible reasoning.

GK extends the [GKC theorem prover](https://logictools.org/gk/) with
[numeric confidences](https://link.springer.com/chapter/10.1007/978-3-030-79876-5_29)
and [defeasible rules](https://link.springer.com/chapter/10.1007/978-3-031-10769-6_18).
See also:
- [Confidence and defeasible reasoning examples](http://logictools.org/confer/)
- [GK tutorial](https://logictools.org/gk/tutorial.html)

### 3.6 Confidence

Some clause dicts carry `"@confidence": 0.8` (from `@p` metadata).  The prover
uses this to rank answers by certainty.

### 3.7 Transformations Applied

The pipeline applies several transformations between Stage-2 output and GK input:

**Pre-clausification** (on the raw formula):
- Degree presupposition injection: "not very big" → adds "big" (unmarked)
- Stative event rewriting: event-encoded have/like/own → direct predicates
- `@time` stripping: time wrappers → `$tense` sentinels
- Entity category/base-word isa injection from Stage-1 metadata
- Meta-predicate normalization (lc_rewrites.py): `is_rel2("is",A,B)` → `isa(A,B)`;
  `is_rel2("=",A,B)` → `=(A,B)`;
  `is_rel2("located in/at/on/near/above/under",A,B)` → `is_rel2("in/at/on/near/above/under",A,B)`
- Misnested existential hoisting (lc_rewrites.py, assertion formulas only)
- Spurious `can` removal (lc_rewrites.py, event queries without modal language)

**During clausification** (lc_clausify.py):
- Connective elimination (implies → or, equivalent → and)
- Negation Normal Form (push negations inward)
- Defeasible expansion (normally → $block)
- Skolemization (exists → typed Skolem constants `sk0_house`, plain functions `["sk0","?:X"]`)
- CNF distribution (or over and)

**Post-clausification** (lc_ctxt.py + lc_postprocess.py, on the clause list):
- $ctxt injection with world dispatch (lc_ctxt.py)
- `$theof1` definite function terms (lc_postprocess.py): when an ASU has a `definites` entry
  (e.g., `["father of", "the father 2", "John 1"]`), the flat entity ID is replaced
  by `["$theof1", "father", "John 1", CTXT]` throughout all clauses.  Bridge axioms
  (`isa`, `have`, `is rel2`) are generated per relation.  This makes "the father of
  John", "John's father", and wh-queries all refer to the same canonical term.
- Gradable property normalization (lc_postprocess.py, whitelist-based has property ↔ has degree property)
- isa(entity,X) stripping (lc_postprocess.py, tautological)
- RELCLASS coercion for question atoms (lc_postprocess.py)
- Population fact generation (lc_postprocess.py, synthetic witnesses for rule variables)
- Set existence fact generation (lc_sets.py, assertion-context `forall/member` patterns)
- Semantic normalization (semnormalize.py, antonym resolution, canonical substitution)

**Post-prover** (procproofs.py):
- Answer tier filtering (concrete > Skolem > population)
- Tautological population answer filtering
- Proof deduplication (eliminate shadow proofs with same answer + same content sources)

### 3.8 Entity ISA Injection

The pipeline injects `isa` facts from Stage-1 metadata that Stage-2 may not
have emitted:

**Category isa:** For each concrete entity with a `"category"` field,
`isa(CATEGORY, ENTITY)` is added unless Stage-2 already has a
**positive-polarity** `isa` for that entity (polarity tracked through
connectives, negation, implications, and low-confidence packages).
Entities in negated or low-confidence contexts are not skipped — they
need the injection.  Exact duplicates with content-derived clauses are
removed.  Example: `"John 1"` with `category: "person"` →
`["isa", "person", "John 1"]`.

**Base-word isa:** When a concrete entity's ID has a lowercase base word
different from the category, an additional `isa(BASE, ENTITY)` is injected.
Example: `"man 1"` with `category: "person"` → both
`["isa", "person", "man 1"]` and `["isa", "man", "man 1"]`.
This ensures queries using the descriptive type word ("Who is a man?") can
match even when Stage-2 only emitted `isa(person, ...)`.

**Compound subsumption:** For compound entity types like "baby bird",
a subsumption rule `isa(bird, X) :- isa(baby bird, X)` is generated
so that general bird rules can apply to baby birds.

### 3.9 Population Facts

For each class mentioned in a forall-quantified rule, synthetic "population"
facts are generated so the prover has witnesses to instantiate:

```json
{"@name": "sent_S1", "@logic": ["isa", "bird", "$some_bird"]}
{"@name": "sent_S1", "@logic": ["-isa", "bird", "$some_not_bird"]}
```

`$some_bird` witnesses that at least one bird exists.
`$some_not_bird` witnesses that at least one non-bird exists.

Population facts are also generated for property predicates:
`["has property", "red", "$some_red_berry"]` witnesses that at least one
red berry exists.

### 3.10 Question Encoding ($defq)

Complex questions are encoded as biconditional formulas using `$defq` predicates:

```json
{"@name": "sent_S3", "@logic": [
  ["-isa","animal","John 1"],
  ["-has property","red","John 1", ...],
  ["$defq0"]
]}
{"@name": "sent_S3", "@question": ["$defq0"]}
```

The prover derives `$defq0` when all conditions are met, then matches it against
the `@question` entry to produce the answer.

For wh-questions, `$defq` carries the answer variable:
```json
{"@name": "sent_S3", "@question": ["$defq0", "?:X"], "@askvars": 1}
```

**Where/When queries** use 2-arg `$defq` atoms to encode the preposition in the answer:
```json
{"@logic": [["-is rel2","in","John 1","?:Q1",CTXT], ["$defq0","in","?:Q1"]]}
{"@logic": [["-$defq0","in","?:Q1"], ["is rel2","in","John 1","?:Q1",CTXT]]}
...biconditionals for each preposition (in, on, at, near, above, under)...
{"@question": ["$defq0","?:Rel","?:Q1"], "@askvars": 2, "@where_query": true}
```
The prover returns `["$ans", "in", "Paris 1"]` → formatted as "In Paris."
`@when_query` works identically with temporal prepositions.

**Who/What queries** use isa + equality biconditionals sharing one `$defq`:
```json
{"@logic": [["-isa","?:X","John 1"], ["$defq0","?:X"]]}
{"@logic": [["-$defq0","?:X"], ["isa","?:X","John 1"]]}
{"@logic": [["-=","?:X","John 1"], ["$defq0","?:X"]]}
{"@logic": [["-$defq0","?:X"], ["=","?:X","John 1"]]}
{"@question": ["$defq0","?:X"], "@askvars": 1, "@who_query": true,
 "@who_entity": "John 1", "@who_kind": "who"}
```
The prover returns types (`$ans("car")`) and equalities (`$ans("king 2")`).

### 3.11 GK Input File Format

The clause list is serialized as JSON with `//` comment lines between ASU groups:

```
// Elephants are animals.
{"@logic": [["-isa","elephant","?:X"], ["isa","animal","?:X"]],
 "@name": "sent_S1"},
// John 1 is an elephant.
{"@logic": ["isa","elephant","John 1"],
 "@name": "sent_S2"},
// Is John 1 an animal?
{"@logic": [["-$defq0"], ["isa","animal","John 1"]],
 "@name": "sent_S3"},
...
// [population facts]
{"@logic": ["-isa","elephant","$some_not_elephant"],
 "@name": "sent_S1"},
```

The GK input format is based on
[JSON-LD Logic](https://github.com/tammet/json-ld-logic), a JSON encoding
of first-order logic clauses.  See also:
- [JSON-LD Logic specification and examples](https://logictools.org/json.html)
- Tammet, T. and Sutcliffe, G., 2021. Combining JSON-LD with First Order Logic.
  In *2021 IEEE 15th International Conference on Semantic Computing (ICSC)*
  (pp. 256–261). IEEE.

### 3.12 Background Axioms (axioms_std.js)

The prover also loads `axioms_std.js` containing background knowledge:

- **Taxonomy**: subtype transitivity
- **Part-whole & possession**: has part → have inference
- **Definite function terms**: `$theof1` bridges — generic `have(?:S, $theof1(?:R, ?:S, ?:C), ?:C)`
  plus per-relation `isa` and `is rel2` bridges (generated by lc_postprocess)
- **Degree intensity**: high → none entailment, high/low contradiction
- **Gradable transitivity**: comparative relation chaining
- **Event bridges**: activity + has type + has actor → is rel2 / have
- **Spatial transitivity**: in/inside/located-in chaining
- **Persistence (frame problem)**: facts persist across world states unless blocked
  (defeasible for have, has property, has degree property, can, has part, is rel2;
  W0→W1→W2→W3)

---

## 4. End-to-End Example

**Input:** "Elephants are animals. John is an elephant. Is John an animal?"

### Stage 1 Output

```json
[
  {"raw": "Elephants are animals.",
   "units": [{"unit_id": "S1", "text": "Elephants are animals.",
              "type": "strict_rule",
              "entities": [{"id":"elephants","type":"generic","category":"animal"},
                           {"id":"animals","type":"generic","category":"animal"}]}]},
  {"raw": "John is an elephant.",
   "units": [{"unit_id": "S2", "text": "John 1 is an elephant.",
              "type": "situation",
              "entities": [{"id":"John 1","type":"concrete","category":"person"}]}]},
  {"raw": "Is John an animal?",
   "units": [{"unit_id": "S3", "text": "Is John 1 an animal?",
              "type": "query",
              "entities": [{"id":"John 1","type":"concrete","category":"person"}]}]}
]
```

### Stage 2 Output

```json
["and",
  ["@id","S1", ["holds","W0",
    ["forall","X", ["implies", ["isa","elephant","X"], ["isa","animal","X"]]]]],
  ["@id","S2", ["holds","W0", ["isa","elephant","John 1"]]],
  ["@id","S3", ["question", ["isa","animal","John 1"]]]
]
```

### GK Input (after logconvert)

```json
[
// Elephants are animals.
{"@logic": [["-isa","elephant","?:X"], ["isa","animal","?:X"]],
 "@name": "sent_S1"},
// John 1 is an elephant.
{"@logic": ["isa","elephant","John 1"],
 "@name": "sent_S2"},
// Is John 1 an animal?
{"@logic": [["-$defq0"], ["isa","animal","John 1"]],
 "@name": "sent_S3"},
{"@logic": [["-isa","animal","John 1"], ["$defq0"]],
 "@name": "sent_S3"},
// [population facts]
{"@logic": ["-isa","elephant","$some_not_elephant"],
 "@name": "sent_S1"},
{"@logic": ["isa","animal","$some_animal"],
 "@name": "sent_S1"},
{"@logic": ["-isa","animal","$some_not_animal"],
 "@name": "sent_S1"},
// Is John 1 an animal?
{"@question": ["$defq0"],
 "@name": "sent_S3"}
]
```

### Answer

```
True.
```

The prover derives `isa(animal, John 1)` from the rule
(`isa(elephant,X) => isa(animal,X)`) and the fact (`isa(elephant, John 1)`),
which satisfies the `$defq0` biconditional, confirming the answer.
