# Modal classifier rework — implementation plan

Date started: 2026-05-09
Status: Phase 0 in progress
Strategy: strict cutover; iterative axiom evolution (Phase 5)

## Final scheme (locked by user)

**Top-level arity-1 modal classifier predicates** attached to a Davidsonian
event variable, parallel to existing `typical(E)`:

| Stage-1 mode  | Stage-2 conjunct          | Surface markers (illustrative) |
|---------------|---------------------------|--------------------------------|
| `event`       | (none)                    | past tense, `will V` (future)  |
| `habitual`    | `["typical","E"]`         | normally/typically/usually     |
| `capability`  | `["capability","E"]`      | can / able / capable / could   |
| `volition`    | `["volition","E"]`        | want / wish / desire           |
| `intention`   | `["intention","E"]`       | plan / intend / aim / mean to  |
| `expectation` | `["expectation","E"]`     | hope / expect / anticipate     |
| `necessity`   | `["necessity","E"]`       | must / need / have to          |
| `obligation`  | `["obligation","E"]`      | should / ought / supposed      |
| `speech_act`  | `["speech_act","E"]` + `has force/speaker/addressee/content` | tell / say / ask / order / promise |

**Two-event reification (volition / intention / expectation / speech_act)** —
revised 2026-05-10 after wanter-vs-actor question. These four classifiers
ALWAYS use a two-event structure to keep experiencer separate from content
actor:

```
"John wants Mike to sell a car"
E1: isa(activity,E1), has_type(E1,want), has_actor(E1,John),
    volition(E1), has_content(E1,E2)
E2: isa(activity,E2), has_type(E2,sell), has_actor(E2,Mike),
    has_target(E2,car)
```

Subject control ("John wants to sell") just makes `has_actor(E2,John)` —
same scheme.

**Capability / necessity / obligation** stay as arity-1 classifiers on a
**single** Davidsonian event ("John can fly", "John must leave" have no
experiencer):

```
"John can fly"
E:  isa(activity,E), has_type(E,fly), has_actor(E,John), capability(E)
```

**Speech-act content** — the value of `has content(E1, E2)` is a nested event
variable `E2` with its own modal classifier per Stage-1 content sub-action:

- `tell/order/ask X to V` → content mode `obligation`, content actor = addressee
- `promise/vow to V` → content mode `obligation`, content actor = speaker
- `told/said that <state>` → content mode `event` (no classifier)

**Confirmed design choices:**

- `will V` (future tense) → mode `event`. Use `expectation` only for explicit
  `hope/expect/anticipate`.
- Bi-modal markers: dominant marker wins; capability beats habitual.
  ("John can typically fly" → capability.)
- Renumber Stage-2 §6 sections after deleting Track-1; verify all internal
  cross-references and example-file references before commit.
- No `actual(E)` predicate initially. Mode synchronization (Stage-1 §6.3
  rule 2) handles asserted-vs-modal distinction. Add `actual(E)` only if
  Phase 5 testing demands it.
- No speech-act force→content bridge axioms initially. Stage-2 emits content
  classifier directly. Add bridges in Phase 5 if needed.

## Acceptance criteria

| #  | Criterion |
|----|-----------|
| A1 | Stage-2 emits no `["can",...]` or `["typically",...]` literals after Phase 3. |
| A2 | Stage-2 emits exactly one arity-1 classifier per non-event action. |
| A3 | Speech acts emit reified outer event + nested content event. |
| A4 | Spurious-can default removed; closes claude B1 cluster (86, 90, 94, 97, 122, 146). |
| A5 | Existing capability-passing cases continue to pass. |
| A6 | Full 264-case sweep ≥ baseline 04-30 net. |

## Phases

### Phase 0 — Discovery & baseline (in progress)

1. Grep test files for modal-verb stems. Build case list.
2. Run modal-verb cases on all 4 LLMs (cached). Save results.
3. Categorize cases by mode.
4. Report case counts, expected wins, regression-watch list.

**Output files**: `elogs/baseline_2026_05_09_modals/{cases.txt, gemini.json,
claude.json, deepseek.json, gpt.json, summary.md}`.

WAIT for user feedback before starting Phase 1.

### Phase 1 — Pipeline (additive + defensive) — TRIMMED 2026-05-10

Originally four sub-tasks; trimmed to two after revisiting which were
actually load-bearing.

1. **DONE** `proof_english.py`: render dispatch for new classifiers
   (capability/volition/intention/expectation/necessity/obligation/
   speech_act + has_content). Atom-level adjective forms ("E is possible"
   etc.); clause-level "X can V" rendering deferred to Phase 6.
2. **DROPPED** `lc_post_normalize.py` cache bridge. Strict-cutover
   decision means affected cases re-warm naturally; old [can,X,V] still
   renders+clausifies until Phase 4 retires axioms; no defensive code
   needed today.
3. **DROPPED** stage_sanity skeleton. Phase 6 will add the legacy-shape
   check when its spec is concrete; disabled skeleton today = dead code.
4. **TODO** Smoke test: 3 known-passing modal cases on all 4 LLMs —
   confirm Phase 1.1 changes are inert for cached responses.

### Phase 2 — Stage-1 prompt rewrite (DONE FIRST — producer)

Rationale (revised 2026-05-10): Stage-1 is the producer of the `mode` field
that Stage-2 consumes. Doing Stage-1 first means the OLD Stage-2 still
understands the modes (treats `capability` as atomic-can shape) so we can
sanity-check Stage-1 in isolation before changing Stage-2's output shape.

1. Extend mode enum (§6.2).
2. Add illustrative verb-mode table (§6.2.1) — short, NOT exhaustive.
3. Add speech-act complement structure (§6.2.2).
4. **Delete** §6.3 rule 4 (spurious-capability default).
5. Add 3–5 examples in `stage1_examples.txt`.
6. Per-LLM Stage-1 mode-assignment check.

### Phase 3 — Stage-2 prompt rewrite (DONE SECOND — consumer)

1. Delete §6.2 Track 1 entirely.
2. Rewrite §6.1 single-track header.
3. Rewrite §6.3 Step C (modal classifier table); delete spurious-yn-default
   lines 842–843, 875.
4. Add §6.5 (Speech-act content nesting).
5. Update query subsection.
6. Edit existing examples in `prompts/stage2_examples.txt` (~20–40 edits).
7. Add 5 new examples covering new modes and speech_act.
8. Verify renumbering and cross-references.
9. Per-LLM compliance check.

### Phase 4 — Initial axiom changes (minimal)

1. Delete §5 Track-1 reconstruction zoo (lines 196–212).
2. Delete §8 ACTION MODAL BRIDGES (lines 217–247).
3. Add: strict event→capability bridge.
4. Add: defeasible typical→capability bridge.
5. Refactor §6 cross-world frame for `can` → `capability`.
6. Validate with two canonical capability cases + new-modal sanity.

### Phase 5 — Iterate axioms with testing (interactive)

Per cycle: targeted sweep → diagnose regressions → add axiom or fix prompt
→ re-sweep.

Likely additions (not pre-planned):
- Frame axioms for obligation/volition/intention/expectation/necessity.
- Force→content bridges if Stage-2 underspecifies.
- `actual(E)` if mode-synchronization proves insufficient.
- Per-classifier tense bridges if dynamic mechanism doesn't catch them.

After 2–3 cycles: full 264-case sweep.

### Phase 6 — Cleanup

1. Enable strict sanity check.
2. Remove `coerce_legacy_modal_to_classifier`.
3. Remove `strip_spurious_can`.
4. Remove dead `can`/`typically` entries from `proof_english`.
5. Update `CLAUDE.md`, `DOCUMENTATION.md`, `ENCODINGS.md`.
6. Log fixed cases in `testfixlog_may.txt`.

## Risks (top 3)

1. **Cache miss on first sweep**: budget ~300–400 fresh API calls per LLM.
2. **LLM non-compliance**: claude/gpt may keep emitting old `can` shape;
   sanity-retry plus targeted Stage-2 examples mitigate.
3. **Mode-sync gap**: capability-rule + plain-event-query unifying wrongly.
   Testable in Phase 4; fall back to `actual(E)` in Phase 5 if observed.

## Status tracker

- [x] Plan written (this file)
- [x] Phase 0: discovery + baseline (2026-05-09; 64 cases × 4 LLMs;
      see `elogs/baseline_2026_05_09_modals/phase0_report.md`)
- [x] Phase 1: pipeline (additive) — TRIMMED. Only renderer entries
      landed; smoke test confirms zero regression on cap/speech/volition
      sample cases (results match Phase 0 baseline exactly).
- [x] Phase 2: Stage-1 prompts (2026-05-10) — Edits A,B,C,D,E,G + 7 new
      examples landed in CORE + FULL. Edit F (extending §4.1 incompatible
      modes) intentionally dropped after user pushback — original narrow
      rule is correct.  Per-LLM Stage-1 compliance check PENDING (will
      cost fresh LLM calls since sysprompt-keyed cache will miss).
- [x] Phase 3: Stage-2 prompts — COMPLETE 2026-05-14.
      Batch 1 (instructions): §6 ACTION COMPILATION rewrite, Track 1 deleted,
      classifier table, Two-Event subsection, predicate inventory, validation
      checklist; Correction A (drop "extra wrapping" column) and Correction B
      (preserve modal classifier inside strict negation) applied in both
      CORE+FULL.
      Batch 2 (examples): Conv 1-6 all done (Conv 2 stone restored with
      `normally`; Conv 6 penguins encyclopaedic capability-in-negation
      applied); EX2 5 new examples added (necessity / obligation /
      volition / speech_act-obj-control / speech_act-subj-control).
      Compliance check: 20/20 across {gemini, claude, gpt, deepseek} × 5
      modal cases — all Stage-1 modes and Stage-2 classifiers correct;
      zero sanity retries; logs at debug/m{1..5}_*.txt.
- [x] Plan A — has_time canonicalisation (2026-05-14, executed
      mid-Phase-4 once the contradiction between Stage-2 §8.1 and the
      example file surfaced). Stage-2 §8.1 rewritten to permit
      `["has time", E, "past"|"present"|"future", "in"]` on Davidsonian
      events; §2.9 `@time` scoped to non-Davidsonian atoms.
      `lc_rewrites.strip_tense_has_time` narrowed via new
      `_collect_event_vars` helper to spare event vars. Verification:
      19/20 on pa1-pa5 (one pre-existing yesterday/today literalisation
      issue on gemini, unrelated). See MEMO_2026_05_14_modal_rework.md.
- [x] Phase 4: initial axioms (2026-05-14). DELETED old §5 typical/
      typically zoo (lines 175-212), §8 ACTION MODAL BRIDGES (lines
      214-247), §6 `can` cross-world frame (lines 491-500), §10 `can`
      past-world normalisation (lines 1108-1112). ADDED single
      defeasible event→capability bridge A1 in new §5.1 with two
      `$block` guards: `$not(capability(E))` for strict overrides and
      `has_content(?:Eo, E)` to prevent inner content events from
      auto-deriving capability. Final shape: same-event capability
      derivation (preserves all role atoms). Verification: 24/24 on
      p4a-p4f including inner-content negative case; 36/36 regression
      on n1-n9.
- [x] Phase 6: documentation (partial, 2026-05-14). MEMO_2026_05_14_
      modal_rework.md written; ENCODINGS.md §1.5/§1.7/§2.4/§3.12
      updated; DOCUMENTATION.md §4.2/§7.7 updated; CLAUDE.md updated
      with module pointer + Modal Classifiers section.
- [ ] Phase 5: iterate axioms with testing (deferred — no failing
      case currently motivates the next round; will be revisited as
      new modal cases hit the test suite).
- [ ] Phase 6: remaining cleanup — remove disabled `// can` block from
      §6a comment in axioms_std.js (it is inside a /* */ historical
      block so doesn't affect runtime), archive the debug smoke
      scripts (`debug/modal_smoke*.py`, `phase4_smoke.py`,
      `plan_a_smoke.py`) once their cases are entered as numbered
      cases in testfixlog (likely testfixlog_may.txt), retire
      `lc_rewrites.strip_spurious_can` after a cache-warmup window.

## Open questions deferred to Phase 5

1. Strict event→capability over content events (benign noise vs. gating).
2. Speech-act that-clause encoding shape (event-as-state vs. proposition wrapper).
3. `typically X can V` bi-modal handling (dominant: capability; needs
   testcase to confirm).
