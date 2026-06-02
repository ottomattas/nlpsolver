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

---

## Stative tense-persistence bridges — coverage gap (OPEN, 2026-06-01)

### Problem
Stative predicates (`have`, `has part`, `has property`, `has degree
property`, `can`, `is rel2`, `has degree rel2`) persist across time: a fact
true in the past is normally still true in the present.  This is encoded by
**per-need bridge axioms** generated by `build_question_tense_bridges`
(`lc_ctxt.py`): for each stative literal that must be *proved* at a ground
tense, it emits a defeasible, `$block`-guarded bridge from the opposite
tense, e.g.

```
[-have(?A,?B,past),  have(?A,?B,present),  $block(0, $not(have(?A,?B,present)))]   @0.97
```

These bridges **replace** the old global frame axioms (`axioms_std.js §6a`,
now disabled) which were removed because a fully-general `have(past) ⇒
have(present)` axiom migrates every stative fact across worlds and blows up
the prover search (see `prover.py:94` note on duplicated frame resolvents).
The per-need approach keeps the blast radius to literals that actually occur.

### What is landed (2026-06-01)
The bridge builder is invoked only under the `is_question` gate
(`lc_packages.py` ~692) and originally scanned only the question's `@logic`
clauses for **negative** stative literals (the body→`$defq` direction).  Two
extensions landed:
- **Ownership canonicalisation** (`lc_rewrites.rewrite_meta_predicates`):
  `is rel2 "belonged to"/"owned by"/"owns"/...` → `have(owner,thing)`, so a
  possessive assertion and a "who owns / whose" query use the same predicate.
- **Direct-`@question` goals** (`lc_ctxt._collect_question_goal_signatures`):
  the builder now also scans the *positive* stative literal in a direct
  `["@question", FORMULA]` goal (an unguarded question that did not become a
  `$defq` biconditional).  Closed case **152** ("The boy lost his backpack.
  Who does the backpack belong to?") on gpt/deepseek — they had
  `have(boy,backpack,past)` but, lacking the `$defq` wrapper, never got the
  forward bridge that gemini/claude received.

### The remaining gap (NOT landed)
Bridges are still generated **only for question goals**.  The same cross-
tense need also arises, with no bridge, in:
1. **Rule premises.**  A rule whose antecedent is a stative literal, e.g.
   `have(X,Y,present) → ...`, appears in clause form as a *negative* premise
   literal `[-have(X,Y,present), <consequent>]`.  If that premise carries a
   **ground** tense different from the matching fact's tense, the rule will
   not fire and nothing bridges the gap.
2. **Blockers.**  A defeasible rule's `["$block", 0, ["$not", STATIVE]]`
   guard references a stative literal at a ground tense; evaluating the
   block against a differently-tensed fact needs the same bridge.
   `_collect_stative_signatures` currently **skips** `$block` bodies.

### Example (why it usually doesn't bite — and when it would)
"If a person has a car, the person is rich. John had a car. Is John rich?"
→ **Probably true** on gpt and gemini *today*, because the generic rule
premise is **tenseless**: Stage-2 emits the antecedent with no `@time`
wrapper, so `$ctxt` injection gives it a **free-variable tense slot**, which
unifies with the past fact directly — no bridge needed.  The gap surfaces
only when a rule premise (or blocker) carries a **ground** tense (a rule
lifted from a tensed statement, or an `@time`-wrapped rule) that differs
from the fact's tense.  No current test case isolates this, which is why it
is recorded rather than fixed.

### Proposed generalisation (with caveat)
Generalise the signature collection to scan **all** packages' `@logic`
clauses for negative stative premise literals (not just question clauses),
and **also** descend into `$block` bodies to collect the relevant stative
literal there; then emit the same per-need bridges (deduped).  Because rule-
premise args are variables, the emitted bridge collapses to a general frame
axiom for that predicate — but it is still **demand-gated** (emitted only
when a rule/blocker actually references the stative predicate), unlike the
fully-global §6a axioms.

**Caveat:** variable-args bridges from rule premises re-approach the cost
that got §6a disabled.  Any implementation must be followed by a prover-
**timing** regression sweep over the rule-heavy / defeasible cases, not just
a correctness check.

### Status
OPEN.  The question-side work (ownership canonicalisation, possessive-without-
ownership Stage-2 check + retry, direct-`@question` bridge) is landed and
logged under cases 152/154.  The rule-premise + blocker generalisation is
**not** landed — implement as its own change with a timing sweep when a
concrete failing case appears.  Entry point: `build_question_tense_bridges`
and the `is_question` gate at `lc_packages.py` ~692.


## Case 464 — comparative-measure question "which is cheaper?"  (REMOVE, 2026-06-02)

### Problem
Case 464 (REMOVED from the test set): "The red car has the price three
dollars. The blue car costs two dollars. Which car is cheaper?"  Expected:
*The blue car*.  Both prices are stated as
`$measure_of("price", car, W0) = $measure(N, "dollar")`; "cheaper" should pick
the car with the smaller price.

### How the four LLMs encode it (debug/e464_*)
- **gemini** ✓ — pairwise disjunction of `<` over `$measure_of price`:
  `(X=car1 ∧ price(car1)<price(car2)) ∨ (X=car2 ∧ price(car2)<price(car1))`.
  The `<` is rewritten to `less_measure`; prover computes 2<3 → blue.
- **claude / deepseek** ✗ — bare gradable degree atom in the question,
  `has_degree_property("cheap", X, "high", "car")`, with **no link** to the
  stated prices → goal unsatisfiable → Unknown.
- **gpt** ✗ — mis-encodes the comparison as price **equality**:
  `price(X)=price(car1) ∨ price(X)=price(car3)` → every car matches → returns
  both cars.

### What was tried (not landed)
1. **Axiom bridge** cheap/expensive ↔ price (`less_measure(price(X),price(Y))
   → has_degree_property("cheap",X,high)`): deterministic but over-generates
   for n≥3 (the middle-priced entity also satisfies it), needs a curated
   adjective↔measure table, and cannot rescue gpt's equality mis-parse.
2. **Soft Stage-2 sanity-retry** (a `comparative_not_measure` check in
   `stage_sanity.py`): detect a measurable comparative ("cheaper/longer/…")
   + a bare-degree question + `$measure_of` facts present, and *suggest*
   (softly) re-encoding as a `<` comparison of the measures.  Result:
   - deepseek complied with the robust existential shape
     `∃Y (isa(car,Y) ∧ price(X)<price(Y))` → blue ✓.
   - **claude** complied with the encoding *type* but chose a single, wrong
     reference: `price(X) < price(car3)` (car3 = blue) → nothing is cheaper
     than blue → Unknown ✗.  The "cheaper among candidates = the *minimal*
     one" semantics did not transfer.
   - gpt was not triggered (its body already contains `$measure_of`, so the
     "already measure-based" gate excludes it).
   Net 1/4 → 2/4; the check was **reverted**.

### Why removed
The correct encoding is "the candidate whose `$measure_of` value is minimal
(cheaper/shorter/lighter) / maximal (longer/heavier/taller) among all
candidates."  The LLMs do not produce this consistently, and the divergence
(bare degree atom vs. equality vs. single-reference `<`) is too wide to
normalise in the pipeline without prompt changes (out of campaign scope).
A reliable fix belongs in the Stage-2 prompt (teach the min/max-over-
candidates comparison shape directly), not in post-hoc axioms or retries.

### Status
REMOVE.  Logged in testfixlog_june.txt (Action: REMOVE FROM TEST SET).  No
code landed.  Revisit only as part of a Stage-2 prompt revision covering
comparative/superlative measure questions.  Case 465 below is the same class.


## Case 465 — comparative-measure question "which is longer?"  (REMOVE, 2026-06-02)

### Problem
Case 465 (REMOVED from the test set): "The length of the red car is 3 meters.
The length of the black car is 5 meters. Which car is longer?"  Expected *The
black car* (5 > 3).  Same class as Case 464 above — see it for the full
analysis of the comparative-measure encoding problem.

### How the four LLMs encode it (debug/e465_*)
- **gemini / claude / deepseek** ✗ — bare gradable degree atom
  `has_degree_property("long", X, "high", "car")`, divorced from the stated
  `$measure_of length` facts → goal unsatisfiable → Unknown.
- **gpt** ✓ (fragile) — single-reference comparison
  `length(X) > length(car 2)` where `car 2` is the RED car (3 m), so black
  (5 > 3) answers → correct, but only by a lucky reference choice; referencing
  the black car instead would give Unknown (cf. claude in 464).

### Why removed
Identical to Case 464: the LLMs do not consistently produce the correct
"maximal `$measure_of` value among candidates" encoding, and the divergence is
too wide to normalise in the pipeline without prompt changes (out of campaign
scope).

### Status
REMOVE.  Logged in testfixlog_june.txt (Action: REMOVE FROM TEST SET).  No
code landed.  Same prompt-side fix as Case 464.


## Case 557 — relational-comparative question "which is lower?"  (REMOVE, 2026-06-02)

### Problem
Case 557 (REMOVED from the test set): "The mountain is higher than the hill.
Which is lower, the mountain or the hill?"  Expected *The hill.*  Unlike
464/465 there are **no explicit measures** — "higher than" is a bare
relational comparative, and the question asks the converse ("lower").  The
question itself is unambiguous (mountain higher ⟹ hill is the lower one), so
unlike 547/548 a surface reformulation does not help.

### How the four LLMs encode it (debug/e557_*)
- **gemini** ✓ — invents an abstract `$measure_of("height", …)` and compares:
  assertion `> (height(mtn), height(hill))`, question a disjunctive `<` on
  `$measure_of height`.  Rewrites to `less_measure`; prover answers hill.
- **deepseek** ✗ — clean relational both sides: assertion
  `has_degree_rel2("high", mtn, hill)`, question (xor) `has_degree_rel2("low",
  hill, mtn)` / `…("low", mtn, hill)`.  Correct shape, but nothing connects
  `high(A,B)` to `low(B,A)`.
- **claude / gpt** ✗ — assert the relational `has_degree_rel2("high", mtn,
  hill)` but ask the **absolute** `has_degree_property("low", X)` — a
  predicate mismatch with no bridge.

### Two missing pieces (neither landed)
1. **Converse-comparative axiom**: `has_degree_rel2(W1, A, B) →
   has_degree_rel2(W2, B, A)` for gradable antonym pairs (high/low, tall/
   short, …).  `low`/`high` are in `data_antonyms.py`, but antonym *folding*
   only flips polarity + word (`low(A,B)` → `¬high(A,B)`), which is NOT the
   arg-swapped converse a comparative needs.  This alone fixes deepseek (2/4).
2. **`has_degree_rel2` → `has_degree_property` bridge**: e.g.
   `has_degree_rel2("low", A, B) → has_degree_property("low", A)`, to let
   claude/gpt's absolute-degree question consume the relational assertion.
   Semantically loose — "A is lower than B" does not imply "A is low" in
   general (only for the "which is the X-er one" reading) — so it carries the
   same regression risk that got 464/465 removed.

### Why removed
Same family as 464/465: the comparative encoding scatters across LLMs (measure
vs relational-both vs relational/absolute-mismatch), and the bridging axioms
needed to unify them are either out of scope (the converse axiom is principled
but only partial) or too risky (the rel2→property bridge).  A reliable fix
belongs in the Stage-2 prompt (a single canonical comparative encoding), not
in post-hoc axioms.

### Status
REMOVE.  Logged in testfixlog_june.txt (Action: REMOVE FROM TEST SET).  No
code landed.  If revisited, the converse-comparative axiom (piece 1) is the
clean, principled part worth landing on its own; the rel2→property bridge
(piece 2) needs a Stage-2 prompt decision instead.


## Case 1014 — PP-attachment ambiguity "in his pyjamas"  (REMOVE, 2026-06-02)

### Problem
Case 1014 (REMOVED from the test set): "John shot an elephant in his pyjamas.
The elephant was in his pyjamas?"  Expected *None* (Unknown).  The canonical
Groucho-Marx prepositional-phrase attachment ambiguity: "in his pyjamas" can
attach to **John** (the shooter was in his pyjamas) or to the **elephant**;
"his" is independently ambiguous (John's vs the elephant's pyjamas).  The
question is unanswerable without disambiguation.

### How the four LLMs resolve it (debug/e1014_*)
- **gpt** ✓ (Unknown, accidentally) — DROPS the PP entirely: the assertion
  encodes only the shooting event, never attaching "in his pyjamas" to anyone.
  The question `is_rel2("in", elephant, pyjamas)` finds no info → Unknown.
  Correct answer, but by losing the modifier rather than recognising ambiguity.
- **gemini / deepseek** ✗ (True) — commit to the ELEPHANT reading and ASSERT
  `is_rel2("in", elephant 2, pyjamas 3)` (gemini also `have(elephant,
  pyjamas)`).  The question then matches the assertion in one step (proof:
  sent_S2 → sent_S4) → True.
- **claude** ✗ (Probably true) — same elephant attachment, defeasibly.

### Why removed
PP-attachment is decided during PARSING (Stage-1/Stage-2); there is no sound
post-parse pipeline or axiom fix — a clause set that has already attached the
PP to the elephant simply proves True.  The only lever is the prompt (teach the
parser to flag/avoid committing on ambiguous attachment), which is out of
campaign scope.  The expected `None` is correct and the sentence is the
textbook example of irreducible syntactic ambiguity.

### Status
REMOVE.  Logged in testfixlog_june.txt (Action: REMOVE FROM TEST SET).  No
code landed.  Same class as the other ambiguity removals (14, 578).


## Case 1612 — kb epistemic-modal factive inference "found out where → knows location"  (REMOVE, 2026-06-02)

### Problem
Case 1612 (REMOVED from the test set): "Tom found out where the key was. Does
Tom know the location of the key?"  Expected *True* — finding out where the key
is = knowing its location.  A factive/epistemic inference: `found out` ⟹ `know`,
and `where X is` ⟹ `the location of X`.

### How the four LLMs encode it (debug/e1612_*)
- **deepseek** ✓ — simple RELATIONAL encoding: it pre-computes the inference in
  Stage 2, asserting `is_rel2("knows", Tom, location2)` in W1 (and a `find_out`
  event in W0).  The question `is_rel2("knows", Tom, location2)` matches the
  asserted conclusion directly → True.  (Effectively asserts the conclusion.)
- **gemini / claude / gpt** ✗ — the `kb` epistemic-modal encoding:
  `kb(K, Tom, knowledge, W)`, `kb force factive`, `kb holds CONTENT`.
  - Assertion: `kb holds (ask X: at(key, X))` — "Tom knows WHERE the key is."
  - Question:  `kb holds (at(key, location2))` — "Tom knows the key is AT
    location2."

### Why removed
The `kb` modal **survives to the gk clause list but is inert**: the only
pipeline handling is knower-extraction (`lc_packages`, the `["kb",K,HOLDER,…]`
read) and English rendering (`proof_english`).  There are **no reasoning
axioms** for `kb` — nothing implements the three things this inference needs:
1. a factive axiom (`kb force factive ∧ kb holds P ⟹ P` holds in reality),
2. a wh-resolution bridge (`knows (ask X: at(key,X))` ⟹ `knows at(key, L)` for
   the actual location L), and
3. a fact fixing where the key actually is.
So gemini/claude/gpt's `kb` atoms carry no inferential weight → Unknown.
(gemini additionally mis-parses the question content as `isa("important", key)`,
a second blocker.)  Supporting this properly is a substantial epistemic-modal
reasoning framework — disproportionate for one case — and the only lighter
alternative is a Stage-2 prompt redirect to deepseek's relational form (out of
campaign scope).

### Status
REMOVE.  Logged in testfixlog_june.txt (Action: REMOVE FROM TEST SET).  No code
landed.  If the `kb` epistemic-modal framework is ever built out, this case (and
the broad class of "knows where / knows that / found out" factives) becomes the
natural target — note it would need prompt + axiom co-design, since 3 of 4 LLMs
already emit the `kb` shape but nothing consumes it.


## Case 1614 — put-result location + name->man  (REMOVE, 2026-06-02)

### Problem
Case 1614 (REMOVED from the test set): "If a man has a coin, he puts it in the
box. John has a coin. Where is the coin?"  Expected *In the box.*  The intended
chain: man(John) ∧ have(John,coin) -> put(John,coin,in box) -> the coin is in
the box -> "In the box."

### How the four LLMs handle it (debug/e1614_*)
- **gpt** ✓ (by a Stage-1 artifact) — its STAGE-1 over-generates an extra unit
  "John 1 puts the coin 2 in a box 3." (it applied the rule to John during
  parsing), so the conclusion is asserted outright; a put-destination ->
  location step then answers "In the box."  Not real rule reasoning.
- **gemini / claude / deepseek** ✗ — encode the rule faithfully
  (forall X: man(X) -> forall Y: coin(Y) -> normally(have(X,Y) ∧ put-event
  X,Y,dest box "in")) and the fact have(John,coin), and rely on the prover to
  chain.  It does not, for TWO reasons.

### Two missing inferences (verified)
1. **name -> man**: John is typed only `person`; the rule's antecedent needs
   `isa(man, X)`.  A man IS a person but not vice-versa, and there is no
   proper-male-name -> man (gender) inference, so the rule never fires on John.
2. **put -> location result bridge**: even after manually adding
   `isa(man, John)` the proof still returns "no answers found" -- `put(X, Y,
   destination box "in")` does not yield `is_rel2(in, Y, box)`, so "Where is
   the coin?" has nothing to match.  There is no placement-verb result-location
   axiom (cf. the verb-result-STATE bridges destroy->destroyed, which are about
   properties, not locations).

### Why removed
The case needs BOTH a name->gender->man inference (risky, generally
unsupported) AND a put-X-in-Y -> X-is-in-Y placement-result bridge.  The only
LLM that "passes" does so via a Stage-1 parsing over-generation, not reasoning.
Too complicated for the campaign.

### Status
REMOVE.  Logged in testfixlog_june.txt (Action: REMOVE FROM TEST SET).  No code
landed.  If revisited: the put->location result bridge is the cleaner, more
general half (a placement-verb analogue of inject_verb_result_state_axioms,
emitting is_rel2(<prep>, target, destination) in the next world); the name->man
half is the genuinely hard part and would likely stay a prompt/ontology issue.


## Case 367 — conflicting-modifier coreference ("the small wheelbarrow")  (REMOVE, 2026-06-02)

### Problem
Case 367 (REMOVED from the test set): "A blue hand of a man moved a wheel of a
LARGE wheelbarrow. The SMALL wheelbarrow had a wheel?"  Expected *None*
(Unknown -- no small wheelbarrow was ever mentioned).

### How the four LLMs handle it (testresults/core/*/case_0367.json)
- **gpt / deepseek** ✓ (Unknown) -- they do NOT corefer the definite "the small
  wheelbarrow" with "a large wheelbarrow" (the modifiers conflict), so "the
  small wheelbarrow" is a distinct, unmentioned entity -> nothing known ->
  Unknown.
- **claude / gemini** ✗ (False) -- Stage-1 binds "the SMALL wheelbarrow" to the
  only wheelbarrow in scope, the "LARGE wheelbarrow" (single entity
  `wheelbarrow 4`).  That entity then carries BOTH `has_degree_property(small,
  wheelbarrow 4)` AND `has_degree_property(large, wheelbarrow 4)`.  The gradable
  large/small antonym mutex fires (`large => not small`), the "small
  wheelbarrow" premise becomes contradictory, and the query resolves to False.

### Root cause
A definite description with a CONFLICTING gradable modifier ("the **small** …")
should not coreference an antecedent bearing the OPPOSITE modifier ("a
**large** …").  claude/gemini bind it anyway, and the antonym mutex flips the
answer to False.  This is a Stage-1 entity-resolution decision (prompt
territory).

### On "is False defensible?"
False is defensible ONLY under a Russellian theory of descriptions ("the F is
G" = there EXISTS a unique F that is G) PLUS a closed-world assumption
("unmentioned => nonexistent"): then "no small wheelbarrow exists" makes the
existential claim false.  The solver is OPEN-world (unmentioned => Unknown, not
False) and uses presupposition-style definites, so Unknown is the consistent
answer.  Crucially, the claude/gemini False does NOT arise from that Russellian
reasoning -- it is a coreference + antonym-mutex artifact that merely coincides
with the same letter.

### Why removed
Two tangled problems: (1) a conflicting-modifier coreference bug (Stage-1,
prompt-level), and (2) genuine definite-description ambiguity (Strawsonian
Unknown vs Russellian+CWA False).  A pipeline guard -- suppress coreference, or
suppress the antonym mutex, when an entity acquires conflicting antonym
modifiers via coreference -- is possible but risky and does not resolve the
underlying ambiguity.

### Status
REMOVE.  Logged in testfixlog_june.txt (Action: REMOVE FROM TEST SET).  No code
landed.  If revisited: the cleanest lever is a Stage-1 rule "do not coref a
definite to an antecedent with a conflicting gradable modifier"; the
ambiguity half stays a test-design question.

---

## Case 1074 — Factive stative content ("explain that the road was closed")

**Input:** "The guide explained that the road was closed. The road was closed?"
**Expected:** True.  **Status: REMOVE (too hard).**

### What happens
Factive "explain that P" entails P, so "the road was closed?" should be True.
Result: claude/gemini True; gpt/deepseek Unknown (2/4).

The question is the STATE `has_degree_property("closed", road2)`.  The four LLMs
encode the factive content "the road was closed" at different depths:
- **claude / gemini** emit the closed STATE — `has_degree_property("closed",
  road2)` — as a ground fact inside `holds W0` (claude also adds a direct S2
  assertion + `kb holds`).  A ground stative fact matches the stative question
  → True.
- **deepseek** emits a `close` EVENT (`has_type close`, `has_target road2`) with
  the `speech_act` classifier, but NO closed-state property.
- **gpt** emits a `be_closed` EVENT (the copula+participle mashed into one verb)
  AND drops the `speech_act` classifier entirely.

### Why it's hard (three tangled causes)
1. **Eventive-vs-stative divergence** (the core issue): "was closed" is a passive
   STATIVE; claude/gemini read it as the closed state, gpt/deepseek as a close
   EVENT.  The stative question can't match an event.  This is a Stage-2
   (prompt-level) reading choice.
2. **Factive-verb gap:** the §5.2 factive-content bridge is gated to
   say/claim/report/state/announce and OMITS "explain".  So even the content
   event's `actuality` is not derived for "explain that".
3. **No close-event → closed-property bridge:** even with "explain" added and
   `actuality(close-event)` derived, deepseek's actual `close` event does not
   yield `has_degree_property("closed", road)` — `close`/`closed` is not in
   `_VERB_RESULT_STATES`, and adding it is risky (open/close polysemy, "open" is
   also an adjective).  gpt additionally lacks `speech_act` and uses `be_closed`.

The sister case **1075** ("…Was the road open?") is Unknown on **all four** —
the open/closed mutex needs the closed STATE, which is not reliably derived —
confirming the factive-content-state reasoning is generally weak for "explain".

### Worth landing independently (does NOT fix 1074)
Adding **"explain" to the §5.2 factive verb list** is a genuine, low-risk
correctness fix — "explain that P" is factive like report/state — and would help
factive-explain cases whose content is EVENTIVE and queried eventively (e.g.
"…explained that Mary left. Mary left?").  It does not flip 1074 because of the
event/state gap and gpt's missing classifier.

### Status
REMOVE.  Logged in testfixlog_june.txt (Action: REMOVE FROM TEST SET).  No code
landed.  If revisited: (a) add "explain" to §5.2; (b) a Stage-2 nudge to read a
passive "was <participle>" as a stative `has_degree_property` when it is factive
content; (c) optionally a guarded close→closed result-state bridge.

---

## Case 1190 — "What was X doing?" (do-proverb question)

**Input:** "Mary was reading a book when the phone rang. What was Mary doing?"
**Expected:** ['Reading a book.', 'Read.']  **Status: REMOVE (too hard).**

### What happens
claude/gpt → "Read." (correct); gemini/deepseek → Unknown (2/4).

The pro-verb "doing" is encoded two ways in the question (S3):
- **claude / gpt**: `ask X: exists E (isa(activity,E) ∧ has_type(E, X) ∧
  has_actor(E, Mary) ∧ has_time(E, past))` — X is the activity TYPE → binds the
  premise's `read` event → "Read."
- **gemini / deepseek**: `ask X: exists E (isa(activity,E) ∧ has_type(E, "do") ∧
  has_actor(E, Mary) ∧ has_target(E, X) ∧ …)` — "do/doing" taken LITERALLY as a
  verb whose target is the answer.  Mary's event is `read`, not `do`, so nothing
  matches → Unknown.

### Why it's hard
The fix is a do-proverb question rewrite: `has_type(E,"do") + has_target(E,X)` →
`has_type(E, X)` (drop the target).  But it cannot fire unconditionally — a
LITERAL `do` event ("Mary did her homework.  What did Mary do?" → "Homework")
has the SAME question shape, and the rewrite would wrongly turn it into a
type-ask (binding "do").  Disambiguation requires gating on whether a
`has_type(_, "do")` event actually appears on the ASSERTION side (literal) or
not (pro-verb) — a parse-quality heuristic that is correct for the common case
but fragile.  Part of the broader "What was X doing?" class (task #103,
gerund-enriched answers — the expected even prefers "Reading a book.").

### Status
REMOVE.  Logged in testfixlog_june.txt (Action: REMOVE FROM TEST SET).  No code
landed.  If revisited: implement the gated do-proverb rewrite (only when no
`do`-typed event exists on the assertion side), and fold into task #103 for the
gerund-enriched answer form ("Reading a book.").

---

## Case 1361 — Dropped wh-class noun (empty class)

**Input:** "Squirrels can fly. Foxes cannot fly. Squirrels and foxes are
animals. Which table can fly?"  **Expected:** None (Unknown).
**Status: REMOVE (too hard).**

### What happens
claude/gemini → Unknown (correct); gpt/deepseek → "A squirrel." (2/4).

"Which table can fly?" asks about an EMPTY, incompatible class — no table is
mentioned and tables can't fly. The wh-question (Stage-1 captures the
wh_placeholder `{"id":"table","type":"generic","category":"artifact",
"wh_placeholder":true}`) should constrain the answer to tables:
- **claude / gemini**: `ask X (isa("table", X) ∧ … fly … capability)` → no table
  exists → Unknown.
- **gpt / deepseek**: `ask X (… fly … capability)` — they DROP `isa("table",X)`
  entirely → the answer var is unconstrained → any flier → "A squirrel."

### Why it's hard
A "dropped wh-class" Stage-2 sanity check was prototyped: a `wh_placeholder` that
is `type="generic"` denotes a class (common noun, not a concrete object like
"John"), and the check fires when that class noun is absent from the ask query.
But it ABANDONED for over-firing:
- Across the test set, ~31 case-files "drop" the wh-class — and **only 1361
  actually fails**. The rest PASS, because dropping the class is HARMLESS when
  the class has instances (e.g. "Who is a nice man?" — dropping `isa(man,X)`
  still yields the nice men) or another constraint (a property, a count)
  disambiguates.
- 1361 fails ONLY because "table" is an **empty + incompatible** class. Isolating
  that needs ~4 stacked heuristics (concrete category, single-word, no `isa`
  instances of the class anywhere, not a how-many/value question), and even then
  it would trigger retries on ~30 passing cases (waste + regression risk) to fix
  one.

So the principled reading: gpt/deepseek give a defensible (if pragmatically odd)
answer to a degenerate query; the cost of a precise check far exceeds the value.

### Status
REMOVE.  Logged in testfixlog_june.txt (Action: REMOVE FROM TEST SET).  No code
landed (the prototype check was reverted).  If revisited: the only sound signal
is "the queried wh-class has zero instances in the problem" → the answer must be
Unknown; but that is really a closed-world emptiness check, not a parse fix.

---

## Case 1551 — Nested negation scope ("It is not true that some…are…")

**Input:** "It is not true that some big yellow cats are strong. All big yellow
cats are not strong?"  **Expected:** True.  **Status: REMOVE (too hard).**

### What happens
gemini/deepseek → True (correct); claude/gpt → Unknown (2/4).

The premise is logically equivalent to the question:
`¬∃x(cat x ∧ strong x)` ≡ `∀x(cat x → ¬strong x)` = "All big yellow cats are not
strong". So it should be True.

| LLM | premise encoding | meaning |
|-----|------------------|---------|
| gemini / deepseek | `∀X (big-yellow-cat X → ¬strong X)` | no cat strong ✓ |
| claude | `∃X (big-yellow-cat X ∧ ¬strong X)` | SOME cat not strong (∃¬) ✗ |
| gpt | `¬∃X (big-yellow-cat X ∧ ¬strong X)` | = ∀(cat → strong): all cats ARE strong ✗ |

gemini/deepseek apply the ¬∃→∀¬ equivalence themselves and emit the universal
form, which matches the question. claude/gpt mis-scope the nested negation:
- **claude**: collapses "not true that SOME are strong" into "SOME are not
  strong" (`∃¬` instead of `¬∃`) — a weaker, inequivalent statement.
- **gpt**: keeps the outer ¬ but ALSO negates "strong" inside
  (`¬∃(cat ∧ ¬strong)`), double-negating into "all cats ARE strong" — the
  opposite.

### Why it's hard
Both failures are Stage-2 **negation-scope / quantifier** parse errors on the
"It is not true that some … are …" construction — a logically tricky
double-negation-vs-quantifier interaction. The premise the LLM produces is
simply WRONG (not a missing inference), so no pipeline/axiom pass can recover
it; the prover would derive the ¬∃→∀¬ equivalence on its own IF the premise were
encoded correctly. The fix is the LLM scoping the negation correctly — a
prompt-level matter, out of campaign scope. Not ambiguous (one logical reading);
just hard to parse.

### Status
REMOVE.  Logged in testfixlog_june.txt (Action: REMOVE FROM TEST SET).  No code
landed.  If revisited: a Stage-2 prompt example for "It is not true that
some/all …" → ¬∃ / ¬∀ canonical forms; possibly a Stage-2 sanity check that a
"it is not true that" matrix wraps the WHOLE proposition in a single outer
negation (no inner property negation), but detecting the intended scope from the
parse is itself the hard part.

---

## Case 1613 — Donkey sentence (donkey anaphora + conditional question)

**Input:** "Every farmer who owns a donkey beats it. If John is a farmer and
owns a donkey, does he beat it?"  **Expected:** True.
**Status: REMOVE (too hard).**

### What happens
claude/gpt → True (correct); gemini/deepseek → Unknown (2/4).

The donkey sentence's correct form is `∀X (farmer X → ∀Y (donkey Y ∧ own(X,Y) →
beat(X,Y)))` — the "it" is the universally-bound donkey in the antecedent. The
question "If John is a farmer and owns a donkey, does he beat it?" is a
CONDITIONAL: assume John is a farmer owning donkey Y, derive he beats Y → True by
modus ponens.

| LLM | encoding | result |
|-----|----------|--------|
| claude / gpt | rule ∀∀(...→beat); question conditional (assume → beat) | True ✓ |
| gemini | rule correct, but QUESTION = `farmer(John) ∧ ∃Y(donkey Y ∧ own(John,Y) ∧ beat)` — existential to PROVE, not a conditional to assume | Unknown ✗ |
| deepseek | question correct, but RULE = `∀X ∃Y((farmer∧donkey∧own)→beat)` — ∃Y over the implication, vacuously satisfiable | Unknown ✗ |

### Why it's hard
Two DISTINCT Stage-2 quantifier-scoping errors on the canonical donkey-anaphora
construction plus a conditional question:
- **gemini** drops the conditional ("if … does he") and makes it an existential
  ASSERTION question — it tries to prove John actually owns and beats a donkey
  (never asserted) instead of assuming the hypothesis.
- **deepseek** mis-scopes the rule's donkey as `∃Y` over the conditional rather
  than universally in the antecedent.

Both produce the WRONG logical form (not a missing inference), so no
pipeline/axiom pass can recover it — the prover proves it fine when the form is
correct (claude/gpt). The fix is correct Stage-2 quantifier scoping of donkey
anaphora + conditional questions — a prompt-level matter and a classic hard
problem in formal semantics. Not ambiguous; the expected True is right.

### Status
REMOVE.  Logged in testfixlog_june.txt (Action: REMOVE FROM TEST SET).  No code
landed.  If revisited: a Stage-2 prompt example for donkey anaphora ("Every N
who Rs a M Vs it" → ∀∀(N∧M∧R→V)) and for "If <hyp>, does he <q>?" as a
conditional question (assume the hyp, query the consequent).

---

## Case 1618 — Exhaustive cleft ("It was the red car that won")

**Input:** "It was the red car that won. Did the blue car win?"
**Expected:** False.  **Status: REMOVE (too hard).**

### What happens
claude/gpt → False (correct); gemini/deepseek → Unknown (2/4).

An exhaustive cleft "It was X that V'd" means "the V-er IS X" — exhaustivity:
`∀Z (Z won → Z = the_red_car)`. With the blue car a distinct entity, "Did the
blue car win?" → False.

All four emit a uniqueness clause `∀X (… win … → X = car1)`, differing only in
the antecedent:

| LLM | uniqueness antecedent | effect |
|-----|-----------------------|--------|
| claude / gpt | `car X ∧ win-event by X → X = car1` | any winner = the red car → blue car2 ≠ car1 (UNA) → False ✓ |
| gemini / deepseek | `car X ∧ RED X ∧ win by X → X = car1` | uniqueness restricted to RED winners → a BLUE winner is not excluded → Unknown ✗ |

### Why it's hard
A Stage-2 cleft-exhaustivity SCOPING error: gemini/deepseek copy the focus's
descriptive property `red(X)` INTO the uniqueness quantifier's antecedent. That
weakens it to "red winners are the red car" — saying nothing about a blue
winner. The "red" belongs to the IDENTIFIED entity (car1), not as a restriction
on the quantified winner X. claude/gpt leave the antecedent general, so the
exhaustivity excludes any non-car1 winner.

The failing parse is simply the wrong (too weak) logical form, not a missing
inference — the prover gets False when the exhaustivity is general (claude/gpt).
The fix is correct Stage-2 scoping of cleft exhaustivity (do not restrict the
quantified variable by the focus's own properties) — a prompt-level matter.
Expected False is right under the standard exhaustive-cleft reading.

### Status
REMOVE.  Logged in testfixlog_june.txt (Action: REMOVE FROM TEST SET).  No code
landed.  If revisited: a Stage-2 prompt example for clefts — "It was the <ADJ N>
that V'd" → `V(the_ADJ_N) ∧ ∀Z(Z V'd → Z = the_ADJ_N)`, with the exhaustivity
antecedent quantifying over ALL V-ers (only the isa class, not the focus's
adjectives). A pipeline strip of a focus-property literal from a `→ X = K`
uniqueness antecedent is possible but a narrow, risky heuristic for one case.
