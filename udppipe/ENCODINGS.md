Encodings Reference
===================

This document describes the logic encoding scheme used by udppipe: how English sentences
are represented as extended first-order logic (FOL) formulas for the gk reasoner.
The encoding is described in the paper `paper/concepts.pdf`
("Representing Concepts for Automated Reasoning with Natural Language").

All logic is expressed in the
[JSON-LD-LOGIC](https://github.com/tammet/json-ld-logic) format, a JSON encoding
of first-order logic clauses extended with confidences and defeasible reasoning.
See also:
- [JSON-LD Logic specification and examples](https://logictools.org/json.html)
- Tammet, T. and Sutcliffe, G., 2021. Combining JSON-LD with First Order Logic.
  In *2021 IEEE 15th International Conference on Semantic Computing (ICSC)*
  (pp. 256-261). IEEE.

Overview
--------

The pipeline converts each English sentence into one or more FOL clauses using a small
set of **wrapper predicates**. These wrappers allow general axioms (e.g. transitivity
rules, persistence rules) to be written once and applied uniformly, rather than requiring
a separate predicate symbol per English word. The main wrapper predicates are:

| Predicate   | Arity | Meaning |
|-------------|-------|---------|
| `isa`       | 2-3   | Class membership: *X is a Y* |
| `prop`      | 6-7   | Property of an object: *X is ADJ* |
| `rel2`      | 5-6   | Binary relation between objects (preposition-based) |
| `rel2_of`   | 5     | "of"-relation: *the tail of X* |
| `rel2_than` | 5     | Comparative relation: *X is taller than Y* |
| `act1`      | 5-6   | Intransitive action (concrete): *X runs* |
| `act2`      | 6-7   | Transitive action (concrete): *X eats Y* |
| `do1`       | 5-6   | Typical/habitual intransitive action: *birds fly* |
| `do2`       | 6-7   | Typical/habitual transitive action: *bears eat fish* |
| `can1`      | 5-6   | Capability (intransitive): *birds can fly* |
| `can2`      | 6-7   | Capability (transitive): *bears can eat fish* |

Additionally, several **system predicates** (prefixed with `$`) are used:

| Predicate / Function | Purpose |
|----------------------|---------|
| `$conf`              | Confidence annotation: `[$conf, 0.9, False]` |
| `$ctxt`              | Context term: `[$ctxt, Pres, 1]` (tense + frame number) |
| `$block`             | Blocking literal for defeasible reasoning (exceptions) |
| `$def0`, `$def1`...  | Definition predicates introduced for questions |
| `$ans`               | Answer marker in prover output |
| `$not`               | Negation within blocking literals |
| `$measure1`          | Measure representation: `$measure1(length, obj, meter, ctxt)` |
| `$theof1`            | "The X of Y" representation: `$theof1(color, obj, ctxt)` |
| `$count`             | Count/cardinality function |
| `$setof`             | Set-building function |
| `$greater`, `$less`  | Arithmetic comparison |
| `$afteract`          | Frame after an action (for temporal reasoning) |
| `$dummysubject`      | Placeholder subject |
| `$free_variable`     | Marks a variable as fully free (in question encoding) |
| `$generic`           | "Not specified" / default value for property intensity or class |

Constants and Variables
-----------------------

### Constants (objects)

Constant names encode their origin:

| Pattern | Source | Example |
|---------|--------|---------|
| `c1_John`, `c2_Eve` | Proper nouns (PROPN). Counter prefix `c` + sentence-local counter + `_` + name. | "John" -> `c1_John` |
| `the_c3_car` | Determined common nouns (using "the", "a", "an"). Prefix `the_` + counter + `_` + noun lemma. | "a red car" -> `the_c3_car` |
| `cs1`, `cs2` | Skolem constants from existential quantification. Prefix `cs` + counter. | "Bears have a tail" -> tail is `cs1` |
| `some_elephant` | Generic/existential witness for a class. | "Elephants are big" introduces `some_elephant` |
| `some_young_elephant` | Generic witness with property. | "Young elephants are not big" introduces `some_young_elephant` |
| `Dummyname_1` | Placeholder introduced for "who"/"what" questions, replaced internally during processing. | "Who is big?" -> `Dummyname_1 is big?` |

### Variables

Variables are prefixed with `?:` in the JSON-LD-LOGIC format:

| Pattern | Use |
|---------|-----|
| `?:S1`, `?:S2` | Subject variables in quantified rules |
| `?:O1`, `?:O2` | Object variables |
| `?:X`, `?:Y`, `?:Z` | General variables (from axioms) |
| `?:Q1` | Question variable |
| `?:A1`, `?:A2` | Action/event identifier variables |
| `?:Fv1`, `?:Fv2` | Frame variables (for context generalization) |
| `?:Tense5` | Tense variables |
| `?:Ignore10` | Ignored positions during matching |

The `isa` Predicate (Class Membership)
---------------------------------------

Encodes "X is a Y" or "X belongs to class Y".

**Full form:** `[isa, class, object, [$conf, confidence, is_defeasible]]`

**Simplified (after clausification):** `[isa, class, object]`

Examples:

| English | Logic |
|---------|-------|
| "John is an elephant" | `[isa, elephant, c1_John, [$conf, 1, False]]` |
| "Elephants are animals" (rule) | `[forall, [?:S2], [[isa, elephant, ?:S2, [$conf, 1, False]], =>, [isa, animal, ?:S2, [$conf, 1, True]]]]` |
| "Mike is probably an elephant" | `[isa, elephant, c1_Mike, [$conf, 0.9, False]]` |

After clausification, the confidence annotation is moved to the clause metadata `@confidence`
field and removed from the literal itself. The `is_defeasible` boolean (second element of
`$conf`) indicates whether the consequent of a rule should get blocking literals.

Class membership is treated as **permanent and context-insensitive** -- unlike properties,
`isa` does not carry a context term `$ctxt`.

The `prop` Predicate (Properties)
----------------------------------

Encodes adjective-based properties of objects.

**Full form:** `[prop, property_name, object, intensity, relative_class, [$conf, confidence, is_defeasible], [$ctxt, tense, frame]]`

**Simplified form (after clausification):** `[prop, property_name, object, intensity, relative_class, [$ctxt, tense, frame]]`

Arguments:

| Position | Name | Values | Description |
|----------|------|--------|-------------|
| 1 | property_name | lemma string | The adjective lemma: `big`, `red`, `young` |
| 2 | object | constant or variable | The thing having the property |
| 3 | intensity | `1`, `3`, or `$generic` | `1` = low ("a bit big"), `$generic` = normal, `3` = high ("very big") |
| 4 | relative_class | class name or `$generic` | The class relative to which the property holds (e.g. "big for a mouse") |
| 5 | confidence | `[$conf, N, bool]` | Numeric confidence (removed after clausification) |
| 6 | context | `[$ctxt, tense, frame]` | Temporal context |

Examples:

| English | Logic |
|---------|-------|
| "John is big" | `[prop, big, c1_John, $generic, $generic, [$conf, 1, False], [$ctxt, Pres, 1]]` |
| "Albert was a very small mouse" | `isa(mouse, c1_Albert) & prop(small, c1_Albert, 3, mouse, $ctxt(Past, 1))` |
| "Albert was small" | `prop(small, c1_Albert, $generic, $generic, $ctxt(Past, 1))` |

Intensity axioms in `axioms_std.js`:
- `prop(W, X, 3, C, CT) => prop(W, X, $generic, C, CT)` -- high implies generic
- `prop(W, X, 1, C, CT) => prop(W, X, $generic, C, CT)` -- low implies generic
- `prop(W, X, 1, C, CT) => -prop(W, X, 3, C, CT)` -- low contradicts high

The `rel2` Family (Binary Relations)
--------------------------------------

Binary relations are categorized by the preposition or relation type:

| Predicate | Relation type | Example English |
|-----------|--------------|-----------------|
| `rel2` | General (preposition-based) | "John is in a house" -> `rel2(in, c1_John, the_c2_house, ...)` |
| `rel2_of` | "of"-relations, possession | "the tail of the bear" -> `rel2_of(part, tail, bear, ...)` |
| `rel2_than` | Comparative | "John is nicer than Eve" -> `rel2_than(nice, c1_John, c2_Eve, ...)` |

**Full form for `rel2`:** `[rel2, relation_word, subject, object, [$conf, N, bool], [$ctxt, tense, frame]]`

**Simplified:** `[rel2, relation_word, subject, object, [$ctxt, tense, frame]]`

The relation_word is determined by the preposition: `in`, `on`, `above`, `under`, `at`, `have`, etc.

Example:

| English | Logic |
|---------|-------|
| "John is above a box" | `[rel2, above, c1_John, the_c2_box, [$conf, 1, False], [$ctxt, Pres, 1]]` |
| "The red square has a nail" | `[rel2, have, the_c1_square, cs2, [$conf, 1, False], [$ctxt, Pres, 1]]` where `cs2` is a skolem constant for the nail |
| "Where is John?" | Asks for `[rel2, where, c1_John, ?:Q1, ...]` (the `where` wrapper unifies with `in`, `on`, `at`, etc. via axioms) |

The `where` meta-relation is axiomatized to match any locative relation:
```
rel2(where, X, Y, Z) :- rel2(in, X, Y, Z)
rel2(where, X, Y, Z) :- rel2(on, X, Y, Z)
rel2(where, X, Y, Z) :- rel2(at, X, Y, Z)
...
```

Action Predicates
-----------------

Verbs are encoded using a semi-Davidsonian approach: the verb, actor, optional target,
and context are collected into a single atom. An event identifier variable connects
additional properties (adverbs) in separate atoms.

### Concrete actions: `act1`, `act2`

| Predicate | Arguments | Example |
|-----------|-----------|---------|
| `act1` | `[act1, verb, subject, [$conf,...], event_id, [$ctxt,...]]` | "John ran" |
| `act2` | `[act2, verb, subject, object, [$conf,...], event_id, [$ctxt,...]]` | "John ate the apple" |

Example: "John quickly ate the apple" becomes:
```
act2(eat, c1_John, the_c2_apple, cs3, $ctxt(Past, 1))
  & prop(quickly, cs3, $generic, $generic, $ctxt(X, 1))
```
where `cs3` is the event identifier.

### Habitual/typical actions: `do1`, `do2`

Used for general statements about what things typically do:
- "Birds fly" -> `do1(fly, ?:X, ...)` (within a quantified rule over birds)
- "Bears eat fish" -> `do2(eat, ?:X, ?:Y, ...)` (within a quantified rule)

### Capabilities: `can1`, `can2`

Used for "can" statements:
- "Birds can fly" -> `can1(fly, ?:X, ...)`

Key axioms in `axioms_std.js` connect these:
- `act1(W,X,Z,CT) => can1(W,X,Z,CT)` -- doing implies ability
- `act2(W,X,Y,Z,CT) => can1(W,X,Z,CT)` -- doing (transitive) implies ability
- `do1(W,X,Z,CT) => can1(W,X,Z,CT)` -- typical behavior implies ability
- `can1(W,X,Z,CT) => do1(W,X,Z,CT)` with low confidence (0.15) -- ability weakly implies doing

Context Terms
-------------

The context term `[$ctxt, tense, frame]` encodes temporal/situational information:

| Component | Values | Description |
|-----------|--------|-------------|
| Tense | `Pres`, `Past` | Present or past tense |
| Frame | integer (1, 2, 3...) or variable | Situation counter, incremented for sequential events. Frame 1 is the default starting frame. |

Example: "John went to the park. He ate lunch."
- Going: `$ctxt(Past, 1)`
- Eating: `$ctxt(Past, 2)` (a later situation)

Persistence axioms in `axioms_std.js` propagate facts across frames (defeasibly):
- `prop(R, X, A, B, $ctxt(T, 1)) => prop(R, X, A, B, $ctxt(T, 2))` with blocking
- `rel2(R, X, Y, $ctxt(Past, 1)) => rel2(R, X, Y, $ctxt(Pres, 1))` with blocking

The `-simple` / `-nocontext` flags suppress context terms entirely, producing simpler logic.

Confidence
----------

Every clause may carry a numeric confidence in [0, 1]:

| Qualifier | Confidence |
|-----------|------------|
| (no qualifier -- certain rule) | 1.0 |
| "probably", "likely" | 0.9 |
| "most" (quantifier) | 0.85 |
| "some" (quantifier) | 0.5 |
| explicit percentage ("90%") | parsed value |

Confidences are encoded initially as `[$conf, value, is_defeasible]` within literals.
During clausification, they are extracted to the clause-level `@confidence` field.
The reasoner multiplies confidences during inference: if rule R has confidence 0.85 and
premise P has confidence 0.9, the derived conclusion has confidence 0.85 * 0.9 = 0.765.

Defeasible Reasoning and `$block`
----------------------------------

Default logic is implemented via **blocking literals** (`$block`). Normal rules --
i.e. rules that are not explicitly strengthened with "all" or "every" -- produce
defeasible clauses. The pattern for a typical rule like "Birds can fly" is:

```
Pre-clausification (forall form):
  [forall, [?:X], [[isa, bird, ?:X], =>, [can1, fly, ?:X, ..., [$conf, 1, True]]]]

GK clauses after clausification:
  ["-isa","bird","?:X"], ["can1","fly","?:X",...], ["$block",["$","bird",1],["$not",["can1","?:X","fly",...]]]
```

The `$block` literal means: *"this conclusion (`can X fly`) can be defeated by a rule
with priority higher than `["$","bird",1]` for the class `bird`"*. An exception rule
such as "Penguins cannot fly" carries a higher priority and the same head atom,
allowing GK to prefer the exception.

More concretely, given:
1. "Elephants are big" (defeasible, conf 0.85)
2. "Young elephants are not big" (stronger rule, conf 1.0)

John, a young elephant, triggers rule 2 which blocks the conclusion of rule 1 for John.
Mike, a plain elephant, is not blocked and gets "big" derived with confidence 0.85.

The `$block` tag `["$", class, rule_number]` identifies which rule produced the
defeasible conclusion. The inner `$not(...)` specifies the literal whose derivation
would defeat the clause. The reasoner uses recursively deepening iterations of search
with diminishing time limits to resolve the precedence between competing rules.

Defeasible expansion can be disabled with `-noexceptions` (or `-simple`).

Question Encoding
-----------------

Questions are encoded using **definition predicates** (`$def0`, `$def1`, ...):

**Yes/no questions** (e.g. "John is an animal?"):
```
{@question: [isa, animal, c1_John]}
```
The reasoner tries to prove or refute this directly.

**Wh-questions** (e.g. "Who is big?"):
1. The question word is replaced by a dummy name: "Dummyname_1 is big?"
2. The dummy sentence is parsed to logic normally.
3. A definition equivalence is created: `$def0(?Q1) <=> prop(big, ?Q1, $generic, $free_variable, $ctxt(Pres, ?Fv))`
4. The question clause `{@question: [$def0, ?Q1]}` asks the prover to find bindings for `?Q1`.
5. Answers arrive as `[$ans, constant]` in the prover output.

The `$free_variable` marker in position 4 of `prop` allows matching regardless of the
relative class value.

Clause Metadata
---------------

Each clause in the final JSON sent to the prover can have these metadata fields:

| Field | Type | Description |
|-------|------|-------------|
| `@logic` | list | The clause (disjunction of literals in clause normal form) |
| `@name` | string | Source sentence identifier, e.g. `"sent_1"` |
| `@confidence` | float | Numeric confidence in [0, 1] |
| `@question` | list | Marks a question clause |
| `@sourcetype` | string | E.g. `"question"` for clauses derived from the question |

Example clause:
```json
{"@logic": ["or",
    ["-isa","elephant","?:S2"],
    ["prop","big","?:S2","$generic","$generic",["$ctxt","Pres",1]],
    ["$block",["$","elephant",1],["$not",["prop","big","?:S2","$generic","$generic",["$ctxt","Pres",1]]]]],
 "@name": "sent_1",
 "@confidence": 0.85}
```

Intermediate Representations
-----------------------------

During parsing, the UD tree is converted through several intermediate tree stages.
These are visible in the `-debug` output:

1. **UD tree** -- the Stanza Universal Dependencies parse tree.
2. **subsentence_logic_tree** -- initial SVO extraction: `svo [ elephant be big ]`
3. **object_logic_tree** -- conjunctions/disjunctions expanded: `svo [ [and,elephant,fox] be big ]`
4. **property_logic_tree** -- adjective modifiers attached: `svo [ [props,young,elephant] be big ]`
5. **flat_logic_tree** -- conjunctions flattened into separate SVO triples.
6. **flat_props_tree** -- final tree before logic generation.

The intermediate tree uses these node types:
- `svo [ subject verb object ]` -- subject-verb-object triple
- `sv [ subject verb ]` -- subject-verb (intransitive)
- `[props, adj, noun]` -- noun with property modifier
- `[and, ...]`, `[or, ...]`, `[nor, ...]` -- boolean combinations
- `[seq, item1, item2]` -- sequence (e.g. multiple modifiers)

After the tree stages, proper FOL logic is generated, simplified, clausified, and
enriched with confidence/blocking annotations before being sent to the gk prover.

Axiom File (`axioms_std.js`)
-----------------------------

The default axiom file `axioms_std.js` provides a small world model for reasoning.
Key groups of axioms:

- **Type hierarchy**: `thing <=> object`
- **Property intensity**: high/low/generic implications and contradictions
- **Property-class inference**: `prop(X, Y, $generic, ...) & isa(U, Y) => prop(X, Y, U, ...)`
  with blocking (confidence 0.8)
- **Verb type connections**: `act1 => can1`, `do1 => can1`, `can1 => do1` (weak)
- **Persistence axioms**: properties and relations propagate across frames (defeasibly)
- **Tense bridging**: past-tense facts weakly persist to present
- **Spatial reasoning**: `where` unifies with `in`, `on`, `at`, `under`, `over`
- **Transitivity**: `in` is transitive, `rel2_than` is transitive
- **Movement axioms**: going to/from updates location (`act1(go, ...)`)
- **Possession axioms**: taking/discarding updates `rel2(have, ...)`
- **Counting axioms**: relating set counts through conjunction decomposition
- **Measure axioms**: unit types for `$measure1`

Simplified Mode
---------------

The flags `-simple`, `-nocontext`, `-noexceptions`, and `-simpleproperties` progressively
simplify the output:

- `-nocontext` removes `$ctxt` terms from all literals
- `-noexceptions` removes `$block` literals (no defeasible reasoning)
- `-simpleproperties` removes intensity and relative class from `prop`, also turns on `-noexceptions`
- `-simple` turns on all three

Simplified "John is big" becomes just `[prop, big, c1_John]` rather than
`[prop, big, c1_John, $generic, $generic, [$conf, 1, False], [$ctxt, Pres, 1]]`.
