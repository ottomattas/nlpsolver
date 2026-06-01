# Hard Cases Memo

A running collection of test cases that are conceptually hard — where the
right answer is clear but the *encoding path* to get there is non-obvious or
unresolved. Each entry preserves the problem, what we tried, the proposed
solution, and the open arguments, so we can pick the thread back up later.

No code is committed for any "OPEN" entry below unless noted; these are
design notes, not landed fixes.

---

## Case 76 — "the manager, Anna" / unique definite role  (OPEN, 2026-05-29)

### Problem
Input:  `The manager, Anna, called Eve. Eve is the manager?`
Expected: `False.`

Why False: the definite article "the" appears in **both** the statement
("The manager, Anna") and the question ("Eve is **the** manager?"). In this
concrete, closed situation the manager role is filled by exactly one entity,
and that entity is Anna. Since Eve != Anna, Eve is not the manager.

Verbal form of the key constraint:
> *In this situation, if somebody has the manager role/property, then that
> entity is Anna.*

### How the four LLMs handle it today (from elogs/failing_2026_05_26/e76_*)
- **gpt**  → `True` (WRONG). Stage-1 is fine (apposition captured), but Stage-2
  drops the identity and emits two trivial `isa person` atoms for both the
  assertion and the query → both trivially true.
- **claude** → `False` (correct) via equality `=(Anna, manager 3)`,
  `=(Eve, manager 3)` + UNA. But uses a **third entity** `manager 3`.
- **gemini** → `False` but by accident: drops the apposition, asks
  `=(Eve, Anna)` → UNA → False. Right answer, wrong question.
- **deepseek** → `Unknown`. Two entities (manager generic), `isa(manager,Anna)`,
  query `isa(manager,Eve)`; no uniqueness, so nothing refutes Eve → Unknown.
  Structurally the closest to what we want, just missing uniqueness.

### User's stance on the desired parse
- Stage-1 should produce **two entities only** (Anna, Eve). "manager" is a
  **role/property**, NOT a separate entity. (So gpt/claude's three-entity parse
  is rejected; gemini/deepseek's two-entity parse is the right shape.)
- The reason to answer False is the **uniqueness of the manager-roled entity**,
  licensed by the definite "the" in both statement and question.

### Proposed Stage-2 encoding (the experiment)
Build on the two-entity parse; encode "manager" as a **property** (`has property`,
which carries a `$ctxt` slot) rather than `isa` (context-free). Add a uniqueness
rule equating any manager-holder to Anna.

```json
["and",
  ["@id","S1",
    ["holds","W0",
      ["and",
        ["isa","person","Anna 1"],
        ["isa","person","Eve 2"],
        ["exists","E",
          ["and",
            ["isa","activity","E"],
            ["has type","E","call"],
            ["has actor","E","Anna 1"],
            ["has recipient","E","Eve 2"],
            ["has time","E","past","in"]]]]]],

  ["@id","S2",
    ["holds","W0",
      ["and",
        ["has property","manager","Anna 1"],
        ["forall","X",
          ["implies",
            ["has property","manager","X"],
            ["=","X","Anna 1"]]]]]],

  ["@id","S3",
    ["question",
      ["has property","manager","Eve 2"]]]]
```

### Experiment result
Tested by bypassing the LLM (monkeypatch `llmparse.parse_text` to return
hand-written s1/s2 JSON, then run the real `english_to_answer` pipeline —
harness reproduced in the appendix).

Result: **`False.`**, confidence 1. Clean 5-step proof:
1. uniqueness rule:  `-hasprop(manager,X,present) | X = Anna 1`
2. query branch:     `-$defq0 | hasprop(manager,Eve 2,present)`
3. negated goal:     `$defq0`
4. MP(2,3):          `hasprop(manager,Eve 2,present)`  (assume Eve is the manager)
5. MP(1,4):          `=(Eve 2, Anna 1)` killed by UNA (`#:Eve 2 != #:Anna 1`) → contradiction.

So the **design works** and needs no axiom changes. The `isa -> has property`
switch is what makes the rule fire (context-free `isa` could not be scoped).

### The unresolved problem: W0-scoping
We wanted the uniqueness rule scoped to the current situation W0. It is **not**.
The injected world slots come out as:

```
S1 event:  ["$ctxt","past","W0", …]      ← concrete W0
S2 fact:   ["$ctxt","present","?:Fv5", …] ← FREE VAR, not W0
S2 rule:   ["$ctxt","present","?:Fv5", …] ← same free var
S3 query:  ["$ctxt","present","?:Fv9", …] ← free var
```

The proof still closes (free vars unify, both `present`), but the rule is
effectively **global across all worlds**, not W0-local. A second situation
with a different manager would be wrongly collapsed onto Anna.

#### Root cause (verified)
The world slot is assigned **per package**, by formula type, in
`lc_packages.py:648-685`:
- **Rule package** (formula contains `forall`/`normally`): `situation = _fresh_fv()`,
  `tense_term = _fresh_fv()` — comment "rules are tense-independent". A law
  must hold in every world/time, so its literals get free-var world+tense.
- **Question package**: matrix predicate keeps the query's world; descriptive/
  identifying predicates get a fresh free-var world (match any state).
- **Plain situational fact** (`else`): `situation = world` straight from
  `holds W,F` (concrete W0), else fresh.

`is_rule_formula` (lc_ctxt.py:84-90) returns true if `forall` appears
*anywhere* in the package. Because the experiment bundled the fact and the
`forall` rule under one `@id`, the **whole package** was typed as a rule →
free-var world even on the plain Anna fact. Splitting them into separate
packages restored `W0` on the fact (rule still free-var). So the free var is
about **rule-vs-fact package typing**, not about `has property` per se.

### Candidate solutions for pinning the rule's world to W0 (none chosen)

**Option 1 — blunt one-liner (global reinterpretation).** In the rule branch,
`situation = world if world is not None else _fresh_fv()`. Pins any
`holds W`-wrapped rule to W. Risk: reinterprets *every* holds-wrapped rule as
world-local; general laws some LLM wraps in `holds W0` would stop crossing into
W1. Needs a real regression sweep.

**Option 2 — explicit marker (safe, opt-in).** New Stage-2 construct, e.g.
`["holds_local","W0",["forall",…]]` (or a sentinel conjunct), routed through a
world-pinned injection. General laws untouched, zero regression risk; cost is
new plumbing + a Stage-2 convention.

**Option 3 — injector idempotency (surgical, against the grain).** Make
`inject_ctxt_atom` (lc_ctxt.py:339) skip atoms whose last arg is already a
`$ctxt`, then write `["has property","manager","X",["$ctxt","?:T","W0",…]]`
directly. Pins chosen atoms without reclassifying the package, but pushes
world-awareness into Stage-2, which is otherwise world-naive.

**Option 4 — pattern-detect property-uniqueness rules (most idiomatic).**
Detect the shape `forall X. has_property(P,X) -> X = CONST` in `convert_id_package`
and, only for those, use the asserted `world` instead of a free var. Keeps every
other rule world-general (no global change), no new Stage-2 keyword.

Matcher + branch sketch:
```python
def _is_property_uniqueness_rule(formula):
    if not isinstance(formula, list) or not formula:
        return False
    if formula[0] == "and":
        return any(_is_property_uniqueness_rule(c) for c in formula[1:])
    if formula[0] == "forall" and len(formula) >= 3:
        body = formula[2]
        if isinstance(body, list) and body[:1] == ["implies"] and len(body) >= 3:
            var, ant, cons = formula[1], body[1], body[2]
            ant_ok  = (isinstance(ant, list) and len(ant) >= 3
                       and ant[0] == "has property" and ant[2] == var)
            cons_ok = (isinstance(cons, list) and len(cons) == 3
                       and cons[0] == "=" and var in (cons[1], cons[2]))
            return ant_ok and cons_ok
    return False

# in lc_packages.py rule branch (~648):
if _is_rule_formula(formula):
    if world is not None and _is_property_uniqueness_rule(formula):
        situation = world          # pin definite-role uniqueness to asserted world
    else:
        situation = _fresh_fv()
    tense_term = _fresh_fv()        # keep tense free
```
Pin world, leave tense free — the proof still closes (query's descriptive
free-var world unifies with the pinned W0). 

Arguments around Option 4:
- Pro: idiomatic (codebase is full of detect-a-shape passes); no global change;
  no new keyword; surgical blast radius.
- Con: it is *option 2 made implicit* — still couples to a canonical Stage-2
  shape (LLM must emit exactly `forall X. has_property(P,X) -> X=c`, under a
  `holds W`). Different role encoding (`isa`, flipped equality, missing `holds`)
  → detection misses.
- Con: would also catch legitimate world-general functional laws of the same
  shape (e.g. "the capital of Estonia is Tallinn"); pinning those to the
  asserted world may be wrong. Mitigation: additionally require the filler to be
  a Stage-1 numbered / `#:`-eligible concrete entity, scoping it to closed-scene
  cases.
- Con: implicit behavior → needs a DOCUMENTATION/CLAUDE note.

### Decision
None yet (2026-05-29). User: "I do not have a good solution in mind right now."
Revisit. The full answer also depends on whether the matching **Stage-1** rule
(two-entity parse, role as property) is worth adding, and whether
"unique definite role in a closed scene" recurs enough to justify the machinery.

### Status of related work
- Earlier-drafted prompt rules for this case (Stage-1 apposition + Stage-2
  concrete-identity, the three-entity equality route) were **reverted** at user
  request — the two-entity / property route above supersedes them.
- No pipeline code changed for this case.

### Appendix — test harness (no LLM call)
`/tmp/test_case76.py` (temporary; reproduce if gone):
```python
import sys
sys.path.insert(0, "/opt/nlpsolver/llmpipe/solver")
import llmparse, solve

TEXT = "The manager, Anna, called Eve. Eve is the manager?"
s1_json = [
  {"raw":"The manager, Anna, called Eve.","units":[
    {"unit_id":"S1","text":"Anna 1 called Eve 2.","type":"situation",
     "entities":[{"id":"Anna 1","type":"concrete","category":"person"},
                 {"id":"Eve 2","type":"concrete","category":"person"}],
     "actions":[{"root":"call","mode":"event",
                 "roles":{"actor":"Anna 1","recipient":"Eve 2"}}],
     "time":"past"},
    {"unit_id":"S2","text":"Anna 1 is the manager.","type":"situation",
     "entities":[{"id":"Anna 1","type":"concrete","category":"person"},
                 {"id":"manager","type":"generic","category":"person"}],
     "time":"present"}]},
  {"raw":"Eve is the manager?","units":[
    {"unit_id":"S3","text":"Is Eve 2 the manager?","type":"query",
     "entities":[{"id":"Eve 2","type":"concrete","category":"person"},
                 {"id":"manager","type":"generic","category":"person"}],
     "time":"present"}]},
]
s2_json = ["and",
  ["@id","S1",["holds","W0",["and",
    ["isa","person","Anna 1"],["isa","person","Eve 2"],
    ["exists","E",["and",["isa","activity","E"],["has type","E","call"],
      ["has actor","E","Anna 1"],["has recipient","E","Eve 2"],
      ["has time","E","past","in"]]]]]],
  ["@id","S2",["holds","W0",["and",
    ["has property","manager","Anna 1"],
    ["forall","X",["implies",["has property","manager","X"],
      ["=","X","Anna 1"]]]]]],
  ["@id","S3",["question",["has property","manager","Eve 2"]]]]

llmparse.parse_text = lambda *a, **k: (s1_json, s2_json, {})
opts = {"show_details_flag":True,"show_logic_flag":True,"show_prover_flag":True,
        "prover_explain_flag":True,"json_flag":True,"prover_seconds":2}
print(solve.english_to_answer(TEXT, opts))
```

---

## Case 263 — collective "together" vs "alone"  (WONTFIX / REMOVE, 2026-05-29)

### Problem
Input:  `John and Mary lifted the piano together. Did John lift the piano alone?`
Expected: `False.`

The collective "together" entails John did NOT lift it alone (Mary co-lifted).
The hard part is proving a NEGATIVE: the query posits a lifting event by John
with manner "alone", and proving "no such event exists" normally needs
event-uniqueness / closed-world — the same wall as Case 76.

### How the solvers handle it (debug/e263_*)
- **claude / deepseek** → `True` (WRONG): Stage-2 DROPS "alone" from the query,
  so it collapses to "did John lift the piano?", trivially entailed by the
  joint event.
- **gpt / gemini** → `Unknown`: keep "alone" (`has manner E alone`) but there is
  no axiom linking "alone" to the co-actor/accompaniment, so it sits inert.
- **udp** → `Unknown`: "together" and "alone" as separate prop markers on
  different constants, no mutex relating them.

### Validated idea (NOT landed): Stage-1 decomposition
Mirror the phasal §9.1 approach. "X and Y VERBed Z together" lexically entails
"X did not VERB Z alone" (and same for Y), so have Stage-1 assert that negative
explicitly:

  S1: joint lift event (actor John, accompaniment Mary, target piano)
  S2: "John did not lift the piano alone."   (explicit negative entailment)
  (S2b: "Mary did not lift the piano alone.")

The query "Did John lift the piano alone?" then directly contradicts S2 →
False.  Verified in a /tmp harness: **False, confidence 1** — no new axioms,
reuses the existing negation/contradiction handling.  Requires "alone" to be
encoded identically (`has manner E "alone"`, same world/tense) in S2 and the
query — guaranteed since both come from the same Stage-1 phrasing.

### Why this, not a mutex axiom
The tempting alternative — encode alone/together as mutually-exclusive manners
plus `has_accompaniment(E,_) ⇒ ¬alone(E)` — does NOT reach False: the query's
event is a fresh existential, so the axiom only shows the *asserted* joint event
is not alone, not that *no* solo lift exists.  You would still be at Unknown
unless you also add event-uniqueness ("the lifting of the piano by John is
unique") — the heavy Case-76-style machinery.  The Stage-1 decomposition
sidesteps that by asserting the entailment directly.

### Decision: WONTFIX / REMOVE (2026-05-29)
Not landed.  The decomposition works and is faithful, but it bakes in the
pragmatic single-event reading (as 162/180 did for habituals): "Did John lift
it alone?" is only False if the described joint lift is THE relevant lifting —
a pragmatic, not strictly logical, closure.  Judged too complicated to justify
a dedicated Stage-1 rule for one case.  Logged for removal from the test set
(testfixlog Status 2026-05-29).

### Appendix — test harness (/tmp/test_263.py)
```python
import sys
sys.path.insert(0, "/opt/nlpsolver/llmpipe/solver")
import llmparse, solve

TEXT = "John and Mary lifted the piano together. Did John lift the piano alone?"
s1 = [
  {"raw":"John and Mary lifted the piano together.","units":[
    {"unit_id":"S1","text":"John 1 and Mary 2 lifted the piano 3 together.","type":"situation",
     "entities":[{"id":"John 1","type":"concrete","category":"person"},
                 {"id":"Mary 2","type":"concrete","category":"person"},
                 {"id":"piano 3","type":"concrete","category":"artifact"}],"time":"past"},
    {"unit_id":"S2","text":"John 1 did not lift the piano 3 alone.","type":"situation",
     "entities":[{"id":"John 1","type":"concrete","category":"person"},
                 {"id":"piano 3","type":"concrete","category":"artifact"}],"time":"past"}]},
  {"raw":"Did John lift the piano alone?","units":[
    {"unit_id":"S3","text":"Did John 1 lift the piano 3 alone?","type":"query",
     "entities":[{"id":"John 1","type":"concrete","category":"person"},
                 {"id":"piano 3","type":"concrete","category":"artifact"}],"time":"past"}]},
]
s2 = ["and",
  ["@id","S1",["holds","W0",["and",
    ["isa","person","John 1"],["isa","person","Mary 2"],["isa","piano","piano 3"],
    ["exists","E",["and",["isa","activity","E"],["has type","E","lift"],
      ["has actor","E","John 1"],["has accompaniment","E","Mary 2"],
      ["has target","E","piano 3"],["has time","E","past","in"]]]]]],
  ["@id","S2",["holds","W0",["not",["exists","E",["and",["isa","activity","E"],
    ["has type","E","lift"],["has actor","E","John 1"],["has target","E","piano 3"],
    ["has manner","E","alone"],["has time","E","past","in"]]]]]],
  ["@id","S3",["question",["exists","E",["and",["isa","activity","E"],
    ["has type","E","lift"],["has actor","E","John 1"],["has target","E","piano 3"],
    ["has manner","E","alone"],["has time","E","past","in"]]]]]]

llmparse.parse_text = lambda *a, **k: (s1, s2, {})
opts = {"prover_seconds":2,"show_prover_flag":True,"prover_explain_flag":True,
        "show_logic_flag":True,"json_flag":True}
print(solve.english_to_answer(TEXT, opts))
```

---

## C / D / E / H residual cases — WONTFIX / REMOVE (2026-05-29)

These five remained after Clusters A/B/F were fixed (and 262 closed, 263 parked).
Each needs a distinct, fairly heavy semantic mechanism — not worth a dedicated
rule for one case each. All logged for removal from the test set (testfixlog
Status 2026-05-29). Root-cause notes for if we revisit.

### Case 255 — exceptive "everyone except X"
`Everyone except John arrived. Did Mary arrive?`  Expected: True.
- claude gets it right: strict universal `forall Y: isa(person,Y) & Y!=John -> arrived(Y)`
  plus the bystander fact `isa(person, Mary)`; Mary!=John (UNA) -> Mary arrived -> True.
- gpt drops `isa(person, Mary)` and over-defeasibilizes (normal_rule + `normally`);
  deepseek drops the `isa(person,Y)` restrictor from the universal; gemini died on a
  Stage-1 MAX_TOKENS over-thinking + connection failure.
- Missing piece: a reliable Stage-1/2 convention forcing the strict, isa-restricted
  universal AND keeping the bystander entity fact. Doable but LLM-consistency-fragile.

### Case 249 — deontic "must" vs "allowed"
`John must leave the room. Is John allowed to stay?`  Expected: False.
- Needs deontic duality (obligation to leave => not permitted to stay) plus leave/stay
  opposition. The modal-classifier system marks `obligation` but has no
  obligation<->permission inference and no leave/stay antonym bridge.

### Case 261 — implicative "too ADJ to V"
`The box is too heavy for Mary to lift. Did Mary lift the box?`  Expected: False.
- "too heavy for Mary to lift" implies Mary did NOT lift it (negative implicative).
  The pipeline has no "too ADJ for X to V => not V(X)" construction; the embedded
  infinitival is not turned into a negated event.

### Case 158 — passive role reversal
`The mouse was chased by the cat. Did the mouse chase the cat?`  Expected: False.
- Passive "mouse was chased by cat" = chase(actor=cat, target=mouse). Query "did the
  mouse chase the cat?" = chase(actor=mouse, target=cat) -- reversed roles. Answering
  False needs event/role uniqueness (the only chase has cat as actor) -- the same
  negative-proof / closed-world wall as Case 76 / 263. (Bundle with task #74: 155
  passive->have.)

### Case 145 — "what happened to X" event query
`The old wooden bridge collapsed yesterday. What happened to the bridge?`  Expected: 'It collapsed.'
- Two faults: (1) role mismatch -- "happen TO the bridge" is encoded with
  `has_target`/`has_recipient`(bridge), but intransitive "collapsed" stores the bridge
  as `has_actor`, so claude/gpt/gemini -> Unknown (only deepseek used has_actor and
  matched). (2) soft-synonym noise -- a `collapse<->give` (conf 0.86) soft-synonym
  bridged the open answer var, giving deepseek "Collapse, give and receive".
- PARTIAL fix landed 2026-05-29: removed `give,collapse` from
  mkdata/syn_v_soft_axioms.txt + rebuilt data_synonyms.py, so deepseek now answers just
  "Collapse." The role mismatch (Unknown on the other 3) is unfixed -- "what happened to
  X" must match the event on ANY thematic role of X, which is the remaining hard part.

---

## Case 639 — "Anna, the manager" / who-is-the-manager apposition  (OPEN, 2026-05-30)

### Problem
Input:  `Anna, the manager, called Eve. Who is the manager?`
Expected: `Anna.`

Sibling of case 76 (same apposition shape, opposite question polarity).
Case 76 asks `Eve is the manager?` and wants `False`; case 639 asks
`Who is the manager?` and wants `Anna.`  Both rely on the same parse of
the apposition `Anna, the manager`.

### How the four LLMs handle it
- **gpt** -> `Anna.` (correct).  Encodes the apposition as
  `is rel2("manager of", manager 2, Anna 1)` (a role-RELATION).  Query
  `is rel2("manager of", manager 2, X)` binds X = Anna directly.
- **claude / gemini / deepseek** -> `Unknown.` (all three).  Create a
  separate `manager 3` entity plus an equality `=(Anna 1, manager 3)`,
  and encode the query as `isa(manager, manager 3) AND =(X, manager 3)`.
  The prover binds X = `manager 3`, which equals `@who_entity`, so
  `_format_who_answers` filters it out as self-referential
  (procproofs.py:553-567).  The Anna binding via equality paramodulation
  is never surfaced.

### Why it's hard
Two routes are possible, neither lands cleanly today:
1. **Stage-2 prompt rule** -- "X, the ROLE" appositive should encode as
   `isa(role, X)` directly on the referenced entity (Anna), not as a
   separate role-entity + `=`.  Same encoding gpt already produces.
   Risk: this also affects case 76 (where the third-entity encoding is
   how claude currently produces the correct False answer via UNA), so
   the prompt change would have to be coordinated with case 76's plan.
2. **Renderer fix** in `_format_who_answers` -- when the surviving
   answer equals `@who_entity`, also chase equality `=` chains and
   surface the non-who-entity side as the answer.  More general,
   helps any future appositive variant, but adds renderer complexity
   and a paramodulation pass at answer-extraction time.

Recommend doing (1) and re-running case 76 to confirm the new
encoding still produces False there (the uniqueness rule from the
case-76 design note would do the work; see Case 76 entry above).

### Status
Removed from `tests/tests_core.py` and `tests/tests_core_100.py`
on 2026-05-30.  TODO: re-add once either (1) or (2) lands.

---

## Case 1610 — "knows who broke" ⊢ "knows it is broken"  (REMOVE, 2026-06-01)

### Problem
"John knows who broke the vase. Does John know that the vase is broken?"
Expected **True**.  All four LLMs answer **Unknown**.

The inference is epistemic **knowledge closure** combined with a
result-state bridge:
  knows[ ∃X. break(X, vase) ]   +   break(_, vase) ⊢ broken(vase)
  ⟹  knows[ broken(vase) ].

### How the four LLMs encode it (case_1610.json)
All four use the knowledge-base machinery: `["kb", K, John, "knowledge", W]`,
`["kb force", K, "factive"]`, `["kb holds", K, CONTENT]`.

- **claude**: asserts the breaking in W0; `kb holds(K_S2,
  [∃X∃E break(X,vase) ∧ actuality])` in W1.  Query: `kb holds(K_S3,
  [isa(artifact,vase) ∧ broken(vase)])` in W1.
- **gemini**: knowledge in W1 throughout; content `∃X isa(person,X) ∧
  break(X,vase)`; query content `broken(vase)`.
- **gpt**: nests an `["ask", X, …]` *inside* `kb holds` (a wh-knowledge
  term), world W0.
- **deepseek**: assertion knowledge in W0, query knowledge in W1 — world
  mismatch.

### Why it's hard (root cause, verified from the clause list)
The `kb holds` **content is an opaque nested term** — the whole formula
sits as the third argument of `kb holds` and is never clausified into
provable atoms:
```
kb holds(K_S2, [∃X∃E: break(X,vase) ∧ actuality(E)])      ← known
kb holds(K_S3, [isa(artifact,vase) ∧ broken(vase)])        ← queried
```
So:
1. The `break → broken` result-state bridge (`frm_verb_result`, §verb-
   result-state) operates on ordinary `has_property` atoms.  It **cannot
   reach inside** the opaque `kb holds` term, so `knows[break]` never
   becomes `knows[broken]`.
2. There is no **knowledge-closure** mechanism: nothing rewrites
   `kb holds(K, [break(X,Y)])` into `kb holds(K, [broken(Y)])`.  Doing so
   needs structural pattern-matching + transformation of a deeply-nested
   term, which gk does not do.
3. Even with closure, the four encodings would not line up — different
   worlds (W0 vs W1), gpt's nested `ask`, deepseek's world mismatch.

### Why REMOVE (not postpone)
A real fix is a bespoke epistemic knowledge-closure feature over opaque
`kb holds` terms (apply selected world axioms — here break→broken — inside
the knowledge scope), plus Stage-2 encoding normalisation so the known
content and queried content share worlds/shape.  That is a substantial
reasoning subsystem, well beyond a targeted axiom or pipeline pass, and is
not justified by a single test case.

### Status
Logged REMOVE in `testfixlog_june.txt` (2026-06-01).  TODO: delete from
`tests/tests_core.py` when the test set is next edited from the fixlog
action tags.  Re-add only if a knowledge-closure mechanism is built.
