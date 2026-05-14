# Modal-classifier rework — session memo (2026-05-14)

Cumulative memo covering the modal-classifier overhaul executed over
two sessions (paused 2026-05-10, resumed and finished 2026-05-14).
Original plan in `MEMO_2026_05_09_modals_plan.md`.

## Big picture

The old design encoded modality via two parallel atomic predicates:

- `["can", X, V_or_E, Ctxt]` — Track-1 atomic capability (also accepted
  Track-2 event arg)
- `["typically", X, V, Ctxt]` — Track-1 atomic habitual
- `["typical", E, Ctxt]` — Track-2 marker on an event

This was paired with a "reconstruction zoo" in `axioms_std.js` §5 that
materialised a Davidsonian event from `typically(X, V)` and four
bridge axioms in §8 connecting Track-1 and Track-2.

The new design unifies on a **single Davidsonian track with arity-1
modal classifiers** attached to event variables:

| Mode | Classifier conjunct (last in event's "and") |
|------|----------------------------------------------|
| event | (none) |
| habitual | `["typical","E"]` |
| capability | `["capability","E"]` |
| necessity | `["necessity","E"]` |
| obligation | `["obligation","E"]` |
| volition | `["volition","E"]`  (two-event reification, see below) |
| intention | `["intention","E"]` |
| expectation | `["expectation","E"]` |
| speech_act | `["speech_act","E"]` |

The classifier is the LAST conjunct of the event's outer `and` block.

Two-event reification handles experiencer / speech-act content: the
outer event E1 carries the classifier; the inner event E2 (linked by
`["has content","E1","E2"]`) is the action being wanted / intended /
expected / spoken about.  See Stage-2 §6.3 in
`prompts/stage2_instructions_full.txt`.

## Phase status

| Phase | Status | What landed |
|-------|--------|-------------|
| Phase 1 — pipeline (renderer + smoke) | DONE | 8 new `_PRED_TABLE` entries in `proof_english.py` for the new classifiers |
| Phase 2 — Stage-1 prompts | DONE | mode enum 3→9, §5.2.1 verb-mode table, §5.2.2 two-event structure, §5.3 rule generalised, §12 retitled "EPISTEMIC ONLY", 7 new Stage-1 examples; §8.4 modal-negation example added |
| Phase 3 — Stage-2 prompts | DONE | §6 ACTION COMPILATION rewrite, Track-1 deleted, classifier table (Step C), Two-Event compilation (§6.3), 5 new EX2 worked examples |
| Plan A — has_time canonicalisation | DONE | `["has time", E, "past"|"present"|"future", "in"]` is canonical for Davidsonian events; `lc_rewrites.strip_tense_has_time` narrowed to spare event vars |
| Phase 4 — axiom changes | DONE | deleted §5 typical/typically zoo + §8 bridges + §6 can frame + §10 can normalisation; added A1 defeasible event→capability bridge with two `$block` guards |
| Phase 5 — iterate axioms | not started | deferred until new failing cases arise |
| Phase 6 — final cleanup | not started | docs / dead code removal |

## Files touched (uncommitted)

- `solver/proof_english.py` — 8 new _PRED_TABLE entries (Phase 1)
- `solver/lc_rewrites.py` — `strip_tense_has_time` narrowed via new
  `_collect_event_vars` helper (Plan A)
- `solver/stage_sanity.py` — comment rationale updated (Plan A)
- `prompts/stage1_instructions.txt`, `prompts/stage1_instructions_full.txt`
  — Phase 2 edits + §8.4 modal-negation example
- `prompts/stage1_examples.txt` — 7 new Stage-1 examples
- `prompts/stage2_instructions.txt`, `prompts/stage2_instructions_full.txt`
  — Phase 3 edits + Plan A §8.1 and §2.9 edits
- `prompts/stage2_examples.txt` — 6 conversions + 5 new EX2 examples
- `axioms_std.js` — Phase 4 deletions and A1 addition
- `debug/modal_smoke.py`, `modal_smoke2.py`, `phase4_smoke.py`,
  `plan_a_smoke.py` — smoke test runners (small Python scripts)
- `MEMO_2026_05_09_modals_plan.md` — running status

## Plan A — has_time canonicalisation

**Decision:** for Davidsonian events with a grammatical tense different
from the ambient ASU tense, encode tense on the event via
`["has time", E, "past"|"present"|"future", "in"]`.  The preposition is
literally `"in"` for grammatical tenses.

**Why:** the example file used this shape 9 times while the instructions
forbade it.  `lc_rewrites.strip_tense_has_time` silently stripped it,
making the runtime behaviour inconsistent with both layers.  All four
LLMs naturally emit this shape; aligning the instructions with reality
keeps it.

**Boundary:** for non-Davidsonian atoms (`have`, `is rel2`, `has part`,
`has property`, …) tense flows through the `$ctxt` mechanism (injected
from the Stage-1 unit `time` field) or via `["@time", TENSE, ATOM]`
wrappers.  `@time` is now explicitly scoped to non-Davidsonian atoms
(§2.9 in Stage-2 prompts).

**Pipeline change:** `strip_tense_has_time` now scans the tree once for
event variables (anything introduced by `isa(activity, E)`), then keeps
`has_time(E, "past", "in")` on those and strips it on non-event vars
plus the (always-misplaced) `state_time(W, "past")`.

**Out of scope (Plan B, deferred):** the deeper redesign of
`$ctxt.Time` / `$ctxt.World` / `pre_state` / `next_state` / dynamic
question-tense bridges.  Most invasive — wait until a failing case
forces it.

## Phase 4 — A1 capability bridge

Final clause shape:

```
[¬isa(activity, ?:E),
 ¬has_type(?:E, ?:V, ?:Ctxt),
 ¬has_actor(?:E, ?:X, ?:Ctxt),
 capability(?:E),
 $block(["bridge_capability", ?:E], $not(capability(?:E))),
 $block(["bridge_capability_content", ?:E], has_content(?:Eo, ?:E))]
```

**Semantics.** Any Davidsonian event defeasibly entails a capability
reading on the same event variable.  Two `$block` guards limit when
the conclusion is dropped:

1. **`bridge_capability`** fires on positive evidence of
   `¬capability(E)` — i.e., a strict negation (e.g., "Penguins cannot
   fly").  Standard defeasibility.
2. **`bridge_capability_content`** fires on positive evidence of
   `has_content(?:Eo, E)` — i.e., E is the inner content of a
   two-event reification.  Prevents "John told Mary to leave" from
   over-deriving "Mary can leave".

**Design notes.**

- `isa(activity, E)` and `has_content(E1, E2)` are world-invariant
  (arity 2, no Ctxt).  `has_type`, `has_actor`, `has_target`, etc.
  carry Ctxt.
- The bridge derives `capability(E)` on the SAME event variable, not
  a paired Skolem.  Preserves all role atoms (has_target,
  has_recipient, has_location, has_time, …) for the capability reading
  without copy clauses.
- `$block` challenges use POSITIVE patterns (no CWA needed) — the
  prover only fires the block when it can positively prove the
  challenger.  Without a strict ¬capability and without a has_content
  backlink, the bridge fires at full confidence.

**What the bridge does NOT cover** (deferred until needed):

- Cross-world frame for capability ("Yesterday X was able to V; can X
  V now?") — would need an explicit frame axiom over event time slots.
- Epistemic gating ("John thinks Mary can fly" leaking to speaker's
  world) — handled structurally today via existential scope inside
  `kb holds`; revisit if a leak is observed.
- Other modal classifiers (necessity / obligation / volition / …) —
  no bridges added; rely on Stage-2 emitting matching shapes for
  assertion and query so the prover unifies directly.

## Stage-2 prompt corrections within Phase 3

Two corrections to the §6.2 / §6 Step C/D documentation, applied on
resume:

- **Correction A** — Step C "extra wrapping" column dropped.
  Wrapping in `["normally", ...]` is governed by ASU type
  (`normal_rule`), not by mode.  Habitual+situation does NOT wrap;
  capability inside normal_rule DOES wrap.
- **Correction B** — Step D strict-negation rule rewritten.
  `["not", ["exists","E",["and",...]]]` preserves the SAME shape the
  assertion would emit, INCLUDING the modal classifier.  This gives
  the intended WEAK reading: "lack of capability" rather than "no
  event of this shape ever exists".  Concrete example: "Penguins
  cannot fly" must keep `["capability","E"]` inside the strict
  negation block.

## Stage-1 §8.4 modal-negation example

Added one positive example to the Negation Preservation section in
both CORE and FULL Stage-1 prompts:

```
"John cannot fly?" -> "Can John 1 not fly?" (NOT "Can John 1 fly?")
```

Closes a 1/9 deepseek misfire observed in the regression sweep where
the negation polarity got dropped from a modal-negation query.  After
the example landed, 36/36 cases pass across all 4 LLMs.

## Verification summary

| Sweep | Cases × LLMs | Result |
|-------|--------------|--------|
| Initial 9-case modal regression (n1–n9) | 9 × 4 = 36 | 36/36 ✓ |
| Plan A verification (pa1–pa5) | 5 × 4 = 20 | 19/20 — pa4 gemini "yesterday" literalisation, unrelated to Plan A |
| Phase 4 capability bridge (p4a–p4f) | 6 × 4 = 24 | 24/24 ✓ — including the inner-content negative case p4f |

The pre-existing `time: "yesterday"` Stage-1 issue (gemini parses
"yesterday" as an explicit time literal instead of normalising to
`time: "past"`) remains.  It belongs to Plan B territory.  No
regression introduced.

## Conventions established

- Modal classifiers are **arity 1** (`capability(E)`, `typical(E)`,
  …).  They mark events intrinsically; world/tense info lives on the
  event's role atoms (`has_time`, `has_actor`, `has_target`, …) which
  do carry `$ctxt`.
- The `$ctxt(Time, World, Loc, KB)` mechanism is unchanged.  KB-based
  epistemic restriction works structurally via `["kb holds", K, F]`
  scope rather than per-predicate KB slots.
- Two-event reification for volition / intention / expectation /
  speech_act uses **inline nesting** (option b): the `roles.content`
  value is a nested action object, compiled to a fresh inner E2
  linked by `has_content`.
- "Has content" is the structural marker that identifies inner content
  events.  A1's `bridge_capability_content` $block consumes this.

## What stays for later

- Plan B (deeper world/time/tense redesign) — not motivated by any
  failing case.
- Phase 5 (axiom iteration) — wait for new failing cases.
- Phase 6 (cleanup) — remove disabled `// can` block from §6a comment
  in axioms_std.js; update CLAUDE.md / DOCUMENTATION.md / ENCODINGS.md
  (this memo + the §1.5 / §2.4 / §3.12 edits land in this commit);
  remove or archive the four smoke-test scripts in `debug/` after
  cases are migrated to `testfixlog`.
- The 9 EX2 / regression test scenarios (n1–n9, p4a–p4f, pa1–pa5) are
  not yet entered as numbered cases in `testfixlog_april.txt`.  Likely
  belong to `testfixlog_may.txt` when added.

## Open issue tracker

- `pa4` gemini — "Mary smoked yesterday. Did Mary smoke?" — literalises
  "yesterday" into `time: "yesterday"` instead of `time: "past"`,
  causing tense mismatch with the query.  Stage-1 prompt issue.  Not
  load-bearing for any current test case but worth fixing if
  yesterday/today literals become important.  Plan B redesign would
  resolve it.
- (Open from earlier) `case 198 — §12 is_rel2 block` — deferred.  Not
  modal-related but tracked separately.
