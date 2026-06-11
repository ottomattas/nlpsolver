# Results 02 — Ballast robustness: distractor sentences at increasing dose

Companion to `wip/plans/02-ballast-robustness-experiments.md` (Tanel's ask,
2026-06-10: insert pure-ballast sentences into the test cases at increasing
dose and measure when accuracy degrades).
Status: **Phases 0–3 run** (b2/b4/b8/b16 × gpt+claude, plus b8/b16 ×
gemini+deepseek on the 100-subset — §13).
Post-run auditing caught a sentence-splitter bug that contaminated part of
the collected suites (excluded analytically, generator fixed — §11.2) and
an Anthropic credit outage inside claude's b16 (patched same evening —
§11.4). **Decision: no clean rerun of the 100-subset ladder** — the
contaminated minority is excluded, the curve is unambiguous, and because
ballast picks are seeded per (case_id, dose), the fixed-generator 1600
suites at the chosen doses contain the clean 100-subset cells as a strict
subset, so Phases 4–5 deliver the definitive numbers automatically.
The full 1600 runs (Phases 4–5) are gated on explicit sign-off.
Run: `nlpsolver/llmpipe` on macOS (local `gk` ARM64), two-stage pipeline,
LLM cache on, thinking off, prover at the default 2s. Date: 2026-06-10.
**2026-06-11: §12 adds the failure cause map** (where the chain breaks as
sentence count grows — Tanel's follow-up ask before he builds chunking)
**and §13 adds Phase 3** (gemini+deepseek at b8/b16 on the regenerated
clean suites). §12.6 extends the map to the Phase 3 cells; §13.2 and the
§12.2 table carry a same-day correction — every "prover returned empty
result" run in the study is a deterministic gk datarec hit, not a
timeout, and the bug is sensitive to the gk input serialisation.

---

## 0. TL;DR (the answer so far to "kas/kuidas ballast mõjub")

- **At b2 (2 inert sentences per case), the effect is just barely visible:**
  gpt 100→98, claude 98→96 on the 100-subset. A −2pt drop per model is at
  the edge of noise for n=100, but the per-case evidence below says it is
  real and mechanistically interpretable.
- **Every single failure is an LLM-parse effect, not a prover effect.** All
  6 incorrect runs are `no_proof` (logic too weak → "Unknown"); none are
  wrong answers, none are errors, and re-running the lost cases with a 10s
  prover budget (5× default) changes nothing — so the symbolic half is, as
  predicted, immune to truly inert ballast, and the degradation enters
  through the neural parse.
- **The observed failure mechanisms:** (a) fragile case classes that plan-01
  already flagged (comparatives, possessive presupposition, hedged
  confidence) silently lose needed clauses when ballast is present; (b) one
  explicit **coreference capture**: claude resolved the ballast sentence
  "This was deep." onto the original "John is glad." and broke case 22.
- **Both models parsed every ballast sentence** (0 of 200 runs dropped the
  ballast) — the distraction cost is paid in the *original* sentences'
  encoding quality, not in skipping ballast.
- **Cost: Phase 1 was $7.71 list-price total** (not the ~$15 estimate),
  because provider prompt caching served ~97.6% of input tokens.

## 1. What was run

### 1.1 The generator (`llmpipe/tests/ballast/make_ballast.py`)

Ballast = statement sentences drawn from `tests_core.py` itself (never
questions; no wh-words; no pronouns). A pool sentence is accepted for a case
only if it is **inert** for it:

1. no shared content words — checked over raw words, naive morphological
   variants (plural/past/-ing/comparative, plus an irregular-form map:
   mice/mouse, bought/buy, has/have, ...) and `CANONICALS` canonical forms;
2. no `ANTONYMS` link in either direction (antonym folding must not bridge);
3. no `SOFT_SYNONYMS` link **at any score** ("ka pehmelt");
4. no shared `data_exclusions` group (mutual-exclusion injection);
5. no pair in two *different* noun-mutex groups (`_ISA_EXCL_GROUPS`) —
   `inject_isa_cross_group_axioms` would otherwise emit a cross-group mutex
   axiom bridging the vocabularies (found by the spot checks, §1.2);
6. ballast sentences are mutually inert within a case.

Function words (the/a/is/in/...) are an explicit visible stopword list;
have/has/had and number words count as content. Insertion slots (start /
between statements / right before the question) come from a seeded RNG
(`random.Random(case_id*1000 + dose)`); the question always stays last; the
output regenerates byte-identically. Self-checks re-verify every condition
from the written files. On the 100-subset @ b2 all 100 cases generated at
the **strict** level (no relaxation; min 196 eligible pool sentences/case).

Pool: ~730 unique statement sentences from the 1600 set (b2-era generator:
738 = 4,179 raw − 1,600 questions − 246 wh − 167 pronoun − 22 short −
1,406 duplicates; 733 at rev `88ca7b0`, the suites the collected
gpt+claude b4–b16 cells ran on; 732 with the current post-splitter-fix
generator, which the regenerated suites incl. Phase 3 use — committed as
`llmpipe/tests/ballast/ballast_pool.txt`; each manifest records its own
`pool_stats`).

### 1.2 Validation before spending (plan §4)

`spot_check.py` runs original vs ballasted inputs through the full pipeline
and verifies **on the clause sets** that (a) no clause mixes ballast and
original vocabulary (argument positions; predicate heads like `have`/`has
property` are scaffolding), (b) no injected axiom bridges the two sides,
(c) the answer still matches. Six probe cases (taxonomy, wh, conditional,
defeasible-confidence, measure, pronoun-bearing) — all PASS after the
isa-cross-group fix. The one violation the first round found (ballast
"house" × original "animal" bridged by `frm_excl_isa_xg` on wh-case 6)
became generator condition 5 above.

### 1.3 Phase 1

`runtests.py tests/ballast/tests_core_100_b2.py -llms gpt,claude` —
100 cases × 2 models, 200/200 runs, 0 errors. Models: `gpt-5.1`,
`claude-sonnet-4-6`. b0 reference: the plan-01 Gate-1 two-stage snapshot
(`results/parsing-architecture/core_100/twostage/`), same 100 cases, same
pipeline, no ballast.

## 2. Dose-response (the headline table, to be extended per dose)

```
accuracy %        b0       b2
gpt            100.0     98.0
claude          98.0     96.0
```

Per-case flips vs b0 (not just the aggregate):

```
gpt    b2: lost 553, 893            | gained none
claude b2: lost 22, 1500, 1521      | gained 248
```

The gained case (claude 248, a b0 failure that now passes) is a reminder
that ±1 case is decoding noise; the **lost** set is where the mechanism is.

## 3. Failure decomposition (E2 pattern)

All incorrect b2 runs land in **no_proof** — logic produced, question
encoded, clauses converted, but the prover finds nothing and answers
"Unknown":

```
model   dose  fails  parse_fail  no_question  convert_fail  no_proof  wrong_answer  error
gpt       b2      2           0            0             0         2             0      0
claude    b2      4           0            0             0         4             0      0
```

**Prover-time check (plan §4.3):** re-running all 5 lost cases with
`-seconds 10` (5× the default budget; LLM calls cache-served) leaves every
answer at "Unknown." — so these are **not prover timeouts**. The ballast
made the *parse* weaker: the encoding loses exactly the clause(s) the proof
needed. The lost cases are 553 (comparative equality), 893 (possessive /
relative-clause presupposition), 22 (conditional + coreference capture,
§5), 1500 ("Likely false" hedging), 1521 ("Probably false" confidence) —
overlapping strongly with the fragile classes plan-01's RQ3 identified.

## 4. Position effect (descriptive at this dose)

From the manifest slots (0 = very start, n = immediately before the
question): both gpt losses had all ballast at the **start**; claude's three
losses all involve a **before-question** insertion. Conditioned accuracies
(has-placement vs not) move 3–7pts in opposite directions for the two
models — at 2–6 failures per model this is anecdote, not signal. Phase 2's
higher doses will give the position analysis actual power.

## 5. Ballast handling audit (every run, not just spot checks)

`ballast_audit.py` applies the spot-check clause classifier to all 200
stored runs:

- **Ballast is always parsed:** 0 cases (of 200) where the LLM emitted no
  clauses for the ballast sentences. The distraction cost is in the
  *original* content's encoding, not in dropping ballast.
- **Coreference/merge leaks (MIXED clauses):** gpt 5 cases, claude 3.
  Eyeballed, they split into:
  - **Real captures:** claude case 22 — ballast "This was deep." was
    resolved onto the original ("John 1 being glad was deep") and the case
    was **lost**; gpt case 134 — original pronoun "She" re-bound to the
    ballast's "the mouse" (answer survived, since both pronoun uses moved
    together); both models case 136 — "She" → ballast "Mary"; gpt case
    1408 — the entity "Dr. Penguins" (answer survived). **Correction
    (post-Phase-2):** case 1408 was NOT an LLM merge — the suite text
    itself read "A surgeon, Dr. Penguins are birds." due to the splitter
    bug of §11.2; the model parsed corrupted input faithfully.
  - **Benign enrichment:** the LLM typing ballast people as `isa person` /
    John as `animal` where that word happens to be on the other side
    (cases 70, 1365) — scaffolding, not a bridge.
- **Generator note:** "This was deep." passed the inertness filter because
  bare demonstratives (this/that) are function words. Pool filtering should
  also drop **demonstrative-subject sentences** before the Phase 2 doses
  are generated (pronouns are already dropped). The leak class is itself a
  finding — Tanel predicted it ("coreference leakage") — and at b2 it cost
  exactly one case.

## 6. Cost (from the §1.5 usage ledger — real API calls only, list prices)

```
model    calls      in_tok    of which cached    out_tok     USD
gpt        211   6,600,120   6,451,968 (97.8%)   136,223    2.35
claude     213   7,652,875   7,486,856 (97.8%)   170,664    5.36
TOTAL Phase 1                                               7.71
```

- Provider prompt caching (gpt cached input $0.125/M vs $1.25/M; claude
  cache reads $0.30/M vs $3.00/M, writes 1.25×) absorbed nearly all input
  spend: the run cost **$7.71 vs the ~$15 list-price estimate**. Claude
  costs more per case because each worker process re-writes the prompt
  cache and its cache writes are billed at a premium.
- Phase 0 (key smoke test on 4 providers + two spot-check rounds on
  gemini): ≈ 0.8M input tokens ≈ **$0.7**. Session total ≈ **$8.4**.
- Prices checked 2026-06-10: gpt-5.1 $1.25/$0.125/$10 per M (in/cached/out);
  claude-sonnet-4-6 $3/$3.75/$0.30/$15 (in/cache-write/cache-read/out);
  gemini-2.5-flash $0.30/$0.03/$2.50; deepseek-v4-flash $0.14/$0.0028/$0.28.
- Mechanics: `llmcall.py` captures each real API response's `usage` field
  into the per-case JSON (`llm_usage`); local-LLM-cache hits add no record,
  so sums are the true marginal spend. `analysis/token_ledger.py` prices
  them.

## 7. Caveats / threats to validity

- **n=100 and −2pts:** each model's drop is ~1.4 SE; the dose-response
  *curve* across Phase 2 doses, not the single b2 point, is the result.
  The per-case mechanism evidence (5 losses all no_proof, one traced to a
  coreference capture) supports a real-but-small effect at b2.
- **The 100-subset is curated easy** (b0 = 98–100%), so ceiling effects
  compress the measurable drop; the full 1600 (Phases 4–5) will not have
  this compression.
- **One leak class is generator-fixable** (demonstrative subjects). Fixing
  it before Phase 2 changes the b2 suite if regenerated; the committed b2
  suite + this snapshot stay as-collected for reproducibility.
- **Prover budget:** default 2s everywhere; the §4.3 recheck used 10s only
  diagnostically. At higher doses clause counts grow — watch `no_proof`
  for timeout masquerade per dose (the recheck is one command).
- **Tense/aspect of ballast vs original:** ballast keeps its source tense;
  no constraint links it to the case's tense. Inertness conditions make
  cross-tense interference impossible at clause level, but it may still
  distract the parse — that is part of the measured phenomenon.

## 8. Reproduce

```bash
# from llmpipe/ — generator (deterministic; self-checks built in)
python3 tests/ballast/make_ballast.py -dose 2

# clause-set spot checks (LLM cache makes reruns ~free)
python3 tests/ballast/spot_check.py -dose 2 -ids 2,6,22,28,470,134 -llm gemini

# Phase 1
python3 runtests.py tests/ballast/tests_core_100_b2.py -llms gpt,claude

# analyses (read the committed snapshot; -live reads llmpipe/testresults/)
cd ../results/ballast-robustness/analysis
python3 dose_response.py          # accuracy + failure decomposition + flips
python3 token_ledger.py           # tokens + $ from llm_usage
python3 position_effect.py        # insertion-slot effects
python3 ballast_audit.py [-verbose]  # ballast parsed? coref leaks?
```

Per-case outputs (committed snapshot):
`results/ballast-robustness/core_100_b2/twostage/<llm>/case_NNNN.json`
(+ `summary.json` per cell). The live tree `llmpipe/testresults/` is
gitignored. Suite + manifest: `llmpipe/tests/ballast/tests_core_100_b2.py`,
`.../tests_core_100_b2.manifest.json`.

## 9. What each dataset contributes to the paper

- **b2 (this snapshot):** the *light-dose* anchor of the dose-response
  curve, plus the cleanest version of the headline mechanistic claim — in a
  neuro-symbolic pipeline, inert-context degradation enters **only through
  the neural parse** (all failures no_proof at unchanged prover budget; the
  symbolic half provably indifferent, per the clause-level audit). It also
  contributes the coreference-capture failure mode (LLM re-binds anaphors
  onto distractor NPs), which pure-prover robustness arguments cannot see.
- **Phase 2 doses (b4/b8/b16, pending):** the curve itself — N_light /
  N_heavy selection with evidence, position-effect power, and the
  parse-vs-prover decomposition per dose.
- **Phases 4–5 (1600×4, pending sign-off):** paper-grade magnitudes,
  per-phenomenon breakdowns, and the two final datasets Tanel asked for
  (light = slightly hurting, heavy = clearly hurting).

## 10. Phase status

| Phase | What | Status |
|-------|------|--------|
| 0 | Generator + self-checks + clause spot-checks (6 cases, gemini) | **done** — all PASS after isa-cross-group fix |
| 1 | 100-subset @ b2, gpt+claude | **done** — 200/200, 0 errors, $7.71 |
| 2 | 100-subset @ b4/b8/b16, gpt+claude | **run, provisional** (§11) — clean rerun pending sign-off |
| 3 | 100-subset @ b8/b16, gemini+deepseek | **done** (§13) — 400/400, $14.51 |
| 4 | Full 1600 @ N_light, 4 models | **gated: explicit sign-off (large spend)** |
| 5 | Full 1600 @ N_heavy, 4 models | **gated: explicit sign-off (large spend)** |

## 11. Phase 2 (b4/b8/b16, gpt+claude) — provisional results and incidents

All 600 runs executed (b4/b8/b16 × 2 models × 100 cases), at a constant
non-binding 32K output budget (`runtests.py -maxtokens`, see §11.3).
Snapshots: `core_100_b4/`, `core_100_b8/`, `core_100_b16/`. Per-dose
exclusion lists: `phase2_exclusions.json`.

### 11.1 The curve (provisional)

As collected (all 100 cases per cell) and on valid cases only (excluding
the contaminated cases of §11.2 and claude-b16's credit-outage cases of
§11.4):

```
accuracy %, as collected        valid cases only (excluded/cell)
        b0    b2    b4    b8   b16     b2     b4     b8     b16
gpt   100.0  98.0  84.0  93.0  78.0   98.0   85.1   94.6   79.4   (-2/-6/-7/-32)
claude 98.0  96.0  94.0  89.0  83.0   95.9   94.7   90.3   85.3   (-2/-6/-7/-32)
```

(claude-b16 includes the 22 credit-outage cases re-run 2026-06-10 evening
on the *old* suite — texts verified byte-identical to the collected data —
so the cell is complete; only the contamination exclusions remain. One
patched case, 1011, failed with gk's "db memory allocation error: cannot
extend datarec area" → "prover returned empty result": at b16 the clause
sets are big enough to hit prover-side resource limits — an operational
finding in line with §11.3, relevant to Tanel's later gk-strategy replays.)

- The dose effect is now unambiguous: both models degrade with dose, and
  b16 is the "clearly hurting" regime (N_heavy candidate). b4–b8 looks
  like N_light territory.
- Failure decomposition stays parse-side: `no_proof` dominates everywhere;
  a **wrong_answer** bucket appears from b4 on (3–4/dose/model) — at higher
  doses the parse doesn't just lose clauses, it produces misleading ones —
  and claude emitted *malformed* stage-2 logic once at b8 (case 1315,
  "null at formula level") and again at b16 (case 193).
- **gpt's b4 (85.1) < b8 (94.6) is non-monotonic on complete cells** and
  survives the contamination exclusions. Each dose has an independently
  drawn ballast set, so an unlucky/interactive b4 draw or run-level decode
  variance are the candidates; the clean rerun will say which.

### 11.2 Incident: splitter bug contaminated part of the suites

The pool builder split "A surgeon, **Dr.** Smith, entered the room." at
the abbreviation dot. Three corruption channels into the collected runs:
fragment ballast "A surgeon, Dr." (and partials "Smith, entered the
room.", "Smith, a surgeon, entered the room."); ballast inserted *inside*
the severed original of case 1085; and b2-1408's "Dr. Penguins" (§5
correction). Contaminated cases — b2: 2, b4: 6, b8: 7, b16: 32 (ids in
`phase2_exclusions.json`). Fixed in commit `9a69fc8` (abbreviation-masking
in `split_sentences`); all four suites regenerated cleanly at strict
inertness. The regenerated suites reshuffle all picks (pool size changed),
so the collected runs correspond to the old suites in git history.

### 11.3 Incident: 8K output cap truncates heavy-dose parses

At b16 the default 8000-token output budget truncates stage outputs
(gemini probes: every call returned exactly ~8K and two probe cases died
with "stage 2 produced no output"; a 10s/32K rerun PASSed them). gpt's
reasoning tokens count against the same budget. Phase 2 therefore ran at
32K (non-binding; b2 calls peak at 1.8K, b16 at ~6K mean output). The cap
collision is itself an operational finding for anyone running this
pipeline on long inputs.

### 11.4 Incident: Anthropic credit outage inside claude-b16 (RESOLVED)

22 consecutive claude cases (588–1094) got "credit balance is too low",
recorded no API response, and were initially bucketed as failures. After a
credit top-up they were re-run the same evening against the **old** suite
(extracted from git history; texts verified identical to the collected
runs) so the dataset and the sqlite LLM cache are hole-free for replays.
18/22 passed; the cell numbers above include them. Cost of the patch:
≈ $3.1.

### 11.4b Replay artifacts (per Tanel's email: keep everything, incl. the cache)

- **`cache-snapshot-phases0-2.db.gz`** (1.4 MB; SHA256
  `d9895a7a56f3bb903ecef574c49eac9fc3d42ec7f32dde4af4b2ba46b0707f48`) — a
  consistent `VACUUM INTO` snapshot of the local LLM cache covering every
  call of Phases 0–2 incl. the outage patch, taken at code state `28f774e`.
  To replay: gunzip → place as `llmpipe/cache.db`. **b4/b8/b16 must be
  re-run with `-maxtokens 32000`** (the output budget is part of the cache
  key; b2 used the default 8000) — otherwise every call misses the cache
  and makes real API calls. Cache hits answer in <1s.
- **`cache-snapshot-phases0-3.db.gz`** (2.3 MB; SHA256
  `48c6789b5abeda7dec30ba8fa6a12d8b0ead005bd74002252615dbc500549146`) —
  same procedure, taken after Phase 3 completed (2026-06-11); supersedes
  the phases0-2 snapshot (strict superset: adds every gemini+deepseek
  b8/b16 call). The phases0-2 file stays committed because sent emails
  link to it. The same `-maxtokens 32000` rule applies.
- **`gk-bug-case1011-minimal.gkin`** — minimal reproducer (17 clauses +
  question, delta-debugged from case 1011's 141-clause prover input) for
  the gk datarec allocator error of §11.1. Run:
  `gk/gk-macos-arm64 llmpipe/axioms_std.js -strategytext
  '{"strategy": ["unit"], "query_preference": 0}' -seconds 2
  results/ballast-robustness/gk-bug-case1011-minimal.gkin -defaults
  -confidence 0.1 -keepconfidence 0.1 --datafolder gk` → fails in ~0.3s
  with "cannot extend datarec area"; `-mbsize` 1000–16000 does not help;
  removing the question makes it pass. Observed on macOS ARM64; 6
  deterministic instances across the study (3 at b8, 3 at b16, clause
  sets 83–179 — see §13.2, incl. the input-serialisation sensitivity) —
  relevant for Phases 4–5.

### 11.5 Phase-2 cost (usage ledger, list prices)

```
dose       gpt     claude   note
b4        3.28       7.09
b8        4.99       9.92
b16       8.33      16.31   incl. the $3.1 credit-outage patch (§11.4)
Phase 2  16.60      33.32   = $49.92
```

Study total (Phase 0 ≈ $0.7 + Phase 1 $7.71 + Phase 2 $49.92): **≈ $58**.
Caching context (Tanel's email): 95.7% of the study's 61.4M input tokens
were provider-cache-served (~10× cheaper on the input side), but output
tokens are not cacheable and account for **66% of the actual bill** — so
the total lands ~3× under list ($54.7 actual vs $169.6 uncached for the
same tokens), not 10×. Projections at measured per-case rates for the
1600 runs: Phase 4 @ b8 ≈ **$270** (gpt $80 + claude $159 + gemini ~$25 +
deepseek ~$3), Phase 5 @ b16 ≈ **$390** (gpt $133 + claude $214 + gemini
~$35 + deepseek ~$4) — both together comfortably under the €900 quote.
**Superseded for gemini+deepseek by the measured Phase 3 rates — see
§13.4** (revised total ≈ $817, still under the quote).
The local sqlite cache (`llmpipe/cache.db`, gitignored, preserved) makes
replays of unchanged prompts free — that is what enables Tanel's
gk-strategy reruns at zero API cost.

## 12. Failure cause map: where the chain breaks as sentence count grows

Added 2026-06-11 (Tanel's follow-up ask: before building stage-2 chunking,
find out *which phase of the pipeline breaks, and how*, when there are
many sentences). Everything in this section is computed from the **stored
traces** of the Phase 1–2 runs — zero new LLM spend — by four new scripts
in `analysis/`: `stage1_coverage.py`, `stage2_fidelity.py`, `cause_map.py`,
`spot_verify.py`.

### 12.1 Method

For every **valid** failing run of the complete gpt+claude b8/b16 cells
(contaminated cases of §11.2 excluded; 38 failing runs in total), and for
all passing runs as controls:

1. **Stage-1 coverage** — align the input sentences (original + ballast,
   classified through the manifest the cell actually ran on) to the
   stage-1 `raw` packages, tolerating LLM-side merges/splits. Flags:
   sentence omitted; empty unit list; entity base-name on both the
   ballast and the original side (capture); one referent under more
   numeric ids than in the b0 run of the same case (**id-break**) or
   fewer (**id-merge**); per-sentence unit/entity/action/type/confidence
   diffs vs b0.
2. **Stage-2 fidelity** — stage-2 output is keyed by stage-1 unit ids
   (`["@id","S7",…]`), so coverage is exact: units lost between stages,
   hallucinated ids, missing/multiple question formulas, malformed trees;
   plus a normalised per-sentence logic diff vs b0 (entity numbering,
   variable names and world numbering normalised away).
3. **Clause-level diff vs b0** — normalised clause sets restricted to
   original-sentence clauses, and the world term the question clauses are
   bound to.
4. **Causal intervention** (`cause_map.py -intervene`) — each failing run
   is replayed through logconvert+semnormalize+gk **from its stored
   stage-1/2 JSON** (no LLM involved), with one surgical change: the
   question clauses' pinned world constant is replaced by a fresh
   variable. If that alone returns the exact b0 answer, the world binding
   *is* the cause for that run.

Every failing run gets one primary bucket; the same detectors run over
the passing runs of the cell give each bucket's control rate.

### 12.2 The map (valid failing runs; pass-side control counts in parentheses)

```
bucket                gpt b8    claude b8   gpt b16   claude b16   total
------------------------------------------------------------------------
pipeline-world-shift  2 ( 6)     4 (14)     4 ( 3)     5 ( 9)       15
stage1-id-break       1 ( 2)     1 ( 0)     3 ( 2)     0 ( 0)        5
stage2-distortion     1 (17)     0 (15)     1 (11)     2 (10)        4
stage2-malformed      0 ( 0)     1 ( 0)     0 ( 0)     2 ( 1)        3
gk-error              0 ( 0)     0 ( 0)     2 ( 0)     1 ( 0)        3
stage1-merge          0 ( 0)     0 ( 0)     2 ( 1)     0 ( 0)        2
convert/pipeline      1 ( 9)     0 ( 3)     1 ( 5)     0 ( 4)        2
stage1-distortion     0 (14)     1 ( 8)     0 ( 8)     0 ( 6)        1
unexplained           0          2          1          0             3
fails analysed        5          9         14         10            38
```

*(Correction 2026-06-11, post-Phase-3: gpt-b16 cases 1052 and 1375 were
initially bucketed `pipeline-world-shift` because the freeworld
intervention rescued them. Their stored answer is a prover-side error,
and for those the intervention is invalid evidence: freeing the question
world changes the prover input and merely sidesteps the crash. An
unchanged stored-clause gk replay reproduces both deterministically —
they are datarec allocator hits (§12.6, §13.2) and now count as
`gk-error`. The map above and all derived numbers reflect this.)*

Headline readings:

- **No input sentence was ever dropped.** Across all 322 valid runs
  (passes + fails, both models, both doses), stage 1 emitted ASUs for
  every original and every ballast sentence — `stage1-omission` is empty.
  Tanel's first suspicion ("kas lauseid on puudu?") is ruled out: the
  semantic stage scales to b16-length inputs without losing content.
- **The single largest cause is not the LLM at all.** 15/38 (39%) of the
  failures are `pipeline-world-shift`, *causally verified* by the
  intervention: re-running gk on the stored parse with only the question's
  world binding freed returns the exact b0 answer (and an unchanged
  replay still reproduces the failure). Mechanism: ballast
  event sentences ("Eve introduced Mary.") legitimately advance the world
  chain (`next W0 W1 …`); for a query with no `pre_state`,
  `lc_packages.py` binds the question to the **latest** world; a stateless
  original fact ("John is a child of Mike", confidence 0.2) stays asserted
  in `W0`; nothing carries it forward, so the prover finds nothing. More
  inert event sentences ⇒ more world transitions ⇒ more queries pinned
  away from their facts — degradation that grows with input length but
  lives in the **convert layer**, not the neural parse.
- **Object tracking does break — in both directions** (Tanel's second
  suspicion, confirmed but small): 5 id-breaks (one referent fractured
  into two ids) and 2 id-merges (two referents collapsed into one).
  Breaks kill proofs via entity UNA (`#:lamp 1` ≠ `#:lamp 2`); merges
  *manufacture* proofs — both gpt-b16 wrong answers are merges.
- **Stage-2 causes are real but the minority:** 4 distortions (changed
  logic for an original sentence with clean stage 1), 3 malformed outputs
  (claude only: "null at formula level" b8-1315, "several questions"
  b16-193, empty stage-2 b16-562).
- The high pass-side control rates for `pipeline-world-shift` (3–14 per
  cell) and the distortion buckets show these signatures are *necessary
  but not sufficient* — world pinning only kills cases whose queried fact
  is stateless-in-W0, and most logic drift is harmless variation. That is
  exactly why the bucket assignment leans on the causal intervention and
  a b0-diff, not on flags alone.

### 12.3 One worked example per bucket

- **pipeline-world-shift — case 1521 @ b8/gpt** ("It is not probable that
  John is a child of Mike. John is a child of Mike?", expected *Probably
  false*). Stage 1 and stage 2 are byte-equivalent to b0 for the original
  sentences. But b0 encodes the question world as a free variable, while
  at b8 four ballast event sentences advance the chain to `W1` and the
  question clause becomes
  `["is rel2","child of","#:John","#:Mike",["$ctxt","present","W1",…]]`
  with the fact pinned at `W0` → "Unknown." Replaying gk with `W1` freed
  (`spot_verify.py -dose 8 -model gpt -case 1521 -freeworld`) returns
  **"Probably false."** — the b0 answer — with no other change.
- **stage1-id-break — case 671 @ b8/gpt** ("The woman holding a heavy
  lamp sang. The lamp was light?", expected *False*). At b0 both mentions
  are `lamp 1`; with 8 ballast sentences between them, the definite
  anaphor "The lamp" gets a fresh `lamp 2`. UNA makes them distinct
  constants, the heavy/light contradiction can no longer attach → Unknown.
  Same pattern: 134/234/524 @ b16 ("She was in a room. / She was in the
  room?" → `room 2` vs `room 3`).
- **stage1-merge — case 542 @ b16/gpt** ("The red square has a nail. A
  blue square has a hole. A red square has a hole?", expected *Unknown*).
  b0 correctly makes `square 1` (red) and `square 2` (blue); at b16 gpt
  reuses **`square 1` for both**, the entity is red+blue with nail+hole,
  and the prover proves "True." — a spurious proof manufactured by entity
  collapse. Case 550 (its "False." twin) is the same mechanism.
- **stage2-distortion — case 1475 @ b8/gpt** ("If a bear eats red
  berries, it is big. John eats berries. … John is big?", expected
  *Unknown*). Stage 1 is clean; stage 2's encodings of all four original
  sentences drift vs b0 and the drift loses the *red*-berries guard →
  "Probably true."
- **stage2-malformed — case 1315 @ b8/claude**: stage-2 logic with a
  null at formula level, rejected by gk ("error in formula nr 3
  sent_S1"); case 193 @ b16 emitted two `question` formulas ("several
  questions given"). Pure LLM output-discipline failures at high dose.
- **gk-error — cases 1052 & 1375 @ b16/gpt, 1375 @ b16/claude**: "prover
  returned empty result" on structurally sound clause sets (144–179
  clauses). All three reproduce deterministically in <1s when gk is
  replayed unchanged from the stored clauses in the live input
  serialisation — the §11.1 datarec allocator bug, not timeouts (§13.2
  has the full six-instance picture incl. Phase 3).
- **unexplained (3):** claude-b8 470 & 605, gpt-b16 747 — stage 1, stage
  2 and clauses all look b0-equivalent and the question world is free;
  these need a manual gk-side look (suspect: search-space growth from the
  ballast clauses interacting with the 2s budget).

### 12.4 What this implies for the chunking hypothesis

The proposed fix (stage 1 over the whole text, stage 2 chunk-wise over
stage-1 output, reassemble) targets the *neural* stages. The map says:

1. **Stage 1 whole-text is viable** — nothing is omitted even at b16, so
   the premise of the hypothesis holds. Its real enemy is entity
   tracking over distance (id-breaks/merges, 7/38): any chunking design
   should keep a global entity registry across chunks, or it will *add*
   id-breaks at chunk boundaries rather than remove them.
2. **Chunked stage 2 would address the genuinely stage-2 causes (7/38:
   distortions + malformed)** — shorter per-call outputs should restore
   the output discipline that claude loses at b8/b16 and reduce drift.
3. **But the largest single cause (39%) is below both stages** and no
   chunking will touch it: the question-world binding in the convert
   layer. The cheap, surgical alternative the intervention points to:
   bind stateless questions to a world *variable* (or carry stateless
   facts across `next` transitions). That one change would have rescued
   15 of the 38 failures outright — before any LLM-side work.

### 12.5 Reproduce

```bash
cd results/ballast-robustness/analysis

# the full map (static heuristics only, <2s)
python3 cause_map.py -doses 8,16 -models gpt,claude

# with the causal world-shift intervention (replays gk per failing run
# from the stored stage-1/2 JSON; no LLM calls; ~5 min)
python3 cause_map.py -doses 8,16 -models gpt,claude -intervene

# all four models incl. the Phase 3 cells (§12.6; ~10 min with -intervene)
python3 cause_map.py -doses 8,16 -models gpt,claude,gemini,deepseek -intervene

# per-stage detail
python3 stage1_coverage.py -doses 8,16 -models gpt,claude [-verbose]
python3 stage2_fidelity.py -doses 8,16 -models gpt,claude [-verbose]

# single-case causal check (the §12.3 world-shift exemplar)
python3 spot_verify.py -dose 8 -model gpt -case 1521 -freeworld
```

Caveats: n=38 failing runs, gpt+claude only, on the as-collected (old)
suites with contaminated cases excluded; §12.6 extends the map with the
gemini+deepseek Phase 3 cells (n=53, clean regenerated suites). Bucket
assignment is heuristic except where a replay provides causal evidence
(`pipeline-world-shift` via the freeworld intervention, `gk-error` via
the unchanged stored-clause replay); the per-bucket exemplars above were
verified by hand. The world-shift *signature* also occurs in passing
runs — it is fatal only in combination with a stateless queried fact,
which is why control rates are reported alongside.

### 12.6 Extension to gemini+deepseek (Phase 3 cells)

Same scripts, same `-intervene` causal checks, run over the §13 snapshot
(clean regenerated suites, no exclusions; 53 failing runs):

```
bucket               gemini b8  deepseek b8  gemini b16  deepseek b16  total
-----------------------------------------------------------------------------
pipeline-world-shift  2 (14)     3 (11)      7 (13)      3 (11)        15
stage2-distortion     1 (21)     1 (14)      5 (17)      2 (12)         9
stage1-capture        1 ( 1)     2 ( 1)      1 ( 1)      1 ( 3)         5
stage1-id-break       1 ( 2)     1 ( 0)      1 ( 3)      1 ( 1)         4
gk-error              2 ( 0)     1 ( 0)      0 ( 0)      0 ( 0)         3
stage2-malformed      0 ( 1)     0 ( 4)      1 ( 4)      2 ( 5)         3
stage1-distortion     1 (11)     2 (18)      0 (10)      0 (17)         3
convert/pipeline      1 ( 3)     0 ( 2)      1 ( 5)      1 ( 3)         3
unexplained           1          3           2           2              8
fails analysed       10         13          18          12             53
```

Readings, against the gpt+claude map of §12.2:

- **The cause structure replicates on an independent model pair and
  independent ballast draws.** `pipeline-world-shift` is again the
  largest bucket (15/53, 28%; study-wide 30/91, 33%), again causally
  verified per run: unchanged replay reproduces the failure, freeing the
  question world returns the exact b0 answer. Cases 1239 and 1521 land
  in this bucket for **every model at every dose** — the mechanism is
  case-determined, not model-determined, as expected for a convert-layer
  cause.
- **Stage-1 omission stays at zero** across all 400 Phase 3 runs — the
  no-sentence-dropped result now holds for all four models.
- **`stage1-capture` becomes visible** (5 runs vs ~0 for gpt+claude):
  case 107 ("Who is nice? The nice man / the quiet man") picks up a
  ballast adjective on an original entity in *every* Phase 3 cell — the
  wrong-answer channel for this model pair, where gpt's was id-merge.
- **gemini's b16 signature is stage-2 distortion** (5 of its 18 fails):
  stage 1 clean, logic of original sentences drifts vs b0. Consistent
  with gemini paying the largest accuracy cost at b16 (−17pt, §13.1).
- **All three b8 "prover returned empty result" runs are gk datarec
  hits** (gemini 250/1317, deepseek 1011) — deterministic, <1s, see the
  §13.2 correction below. With gpt+claude's three b16 instances, the
  allocator bug accounts for 6/91 failing runs study-wide.
- The 8 unexplained include deepseek-b8 1335 (whose b0 run also fails —
  not a ballast effect) and two odd-answer runs (409, 888) where the
  model answered with the wrong surface form; the rest look like the
  same search-budget suspects as §12.3's.

The chunking implications of §12.4 carry over unchanged — the dominant
cause is still below both LLM stages, entity tracking still breaks both
ways (id-break/capture/merge: 9/53), and genuinely stage-2 causes
(distortion+malformed, 12/53) remain the minority chunking could help.

## 13. Phase 3 (b8/b16, gemini+deepseek) — the second model pair confirms the curve

400 runs (2 doses × 2 models × 100 cases), completed 2026-06-11.
Models: `gemini-2.5-flash`, `deepseek-v4-flash`. Same pipeline settings
as Phase 2 (32K output budget,
prover at 2s), plus `-timeout 300` (§13.3). Snapshots:
`core_100_b8/twostage/{gemini,deepseek}/`, `core_100_b16/twostage/…`.

**These cells ran on the regenerated post-splitter-fix suites** (current
working tree; `resolve_manifest` confirms provenance), so they need **no
contamination exclusions** — but they are also not draw-identical to the
gpt+claude Phase 2 cells, which ran on the old suites. Same doses,
different ballast draws; compare shapes, not individual cases.

### 13.1 The curve

```
accuracy %       b0     b8    b16
gemini         99.0   90.0   82.0
deepseek       98.0   87.0   88.0
```

- Both models reproduce the Phase 2 finding: **clear degradation by b8**,
  and for gemini b16 is again the clearly-hurting regime (−17pt vs b0).
- deepseek is flat b8→b16 (87→88) — the same non-monotonicity gpt showed
  at b4<b8, and the same explanation is available: each dose is an
  independent ballast draw, so per-dose draw luck is ±a few points.
  Phases 4–5 (n=1600/dose) settle this.
- Failure decomposition is again entirely parse-side in signature:
  **zero** `parse_fail`/`no_question`/`convert_fail` anywhere; `no_proof`
  dominates (gemini 8 of 10 at b8, 12 of 18 at b16; deepseek 11/13 and
  10/12), `wrong_answer` grows with dose for gemini (2→6).
- Per-case flips vs b0: gemini b8 lost 10, b16 lost 18; deepseek lost 12
  at both. **Cases 70, 107, 671, 1239 are lost by both models at both
  doses** — the fragile-case classes of §3 (possessive presupposition,
  wh-answer phrasing, comparatives) recur on an independent model pair
  and independent ballast draws.

### 13.2 Prover-side incidents: 3 "prover returned empty result" at b8

All three b8 runs whose answer is "Error: prover returned empty result"
were replayed from the stored clause JSON. **Corrected finding
(2026-06-11, superseding the first pass): all three are deterministic
datarec allocator hits, not timeouts.**

- The first replay pass stripped `@nl` and re-fed the clause list to gk
  as **plain JSON** with the stored strategy. Under that protocol 1317
  and 1011 answer the expected `false` in <1s and only 250 fails — which
  was initially read as "250 = the §11.1 bug, 1317/1011 = load-sensitive
  timeouts".
- Replaying instead through the pipeline's own `prover.call_prover`
  serialisation — identical clauses, but with the `//` ASU comment lines
  the live runs actually feed gk (`spot_verify.gk_replay`) — **all three
  fail deterministically in 0.15–0.6s on an idle machine** with
  `db memory allocation error: cannot extend datarec area`. Not
  timeouts: the 2s budget is never reached.
- So the datarec bug is **sensitive to the input serialisation**: the
  same clause set can pass as plain JSON and crash with comment lines
  (or vice versa). Useful fact for the reproducer family; it also means
  replay-based triage of prover errors must use the live serialisation
  (`gk_replay` does; the §12.6 map is built on it).
- Instances: gemini b8 250 (108 clauses), gemini b8 1317 (83), deepseek
  b8 1011 (90); plus gpt b16 1052 (179), gpt b16 1375 (146), claude b16
  1375 (144) from the Phase 2 cells — 6 study-wide, clause sets ≥83.
  (deepseek-b8 1011 shares its base case with claude-b16's §11.1 hit —
  different suite, different clause set; no longer looking like
  coincidence now that the family has 6 members.)

### 13.3 Operational incidents (all resolved, all instructive)

- **deepseek read-timeouts:** heavy-dose generations routinely exceed
  `llmcall.py`'s 60s default HTTP timeout; the first overnight attempt
  produced silently empty case files (timeout → `None` → no error
  recorded). Fix: `runtests.py -timeout` (commit `78efa1f`); Phase 3 ran
  at 300s. Operationally: a read-timeout aborts the case *after* the
  provider has generated (and bills) the output, so the provider
  dashboard can show slightly more than the §13.4 ledger.
- **gemini 503 "high demand" storms:** hundreds of occurrences across the
  runs, concentrated in peak hours; the built-in retries absorbed most,
  the refill passes picked up the rest.
- **gemini prepay credit depletion** mid-b16 (2026-06-11) — same failure
  class as §11.4 (Anthropic), caught after 7-retry exhaustion on 3 cases;
  topped up and refilled the same day. Provider-credit exhaustion has now
  hit 2 of 4 providers mid-run: worth a pre-run balance check before
  Phases 4–5.

### 13.4 Phase-3 cost (usage ledger, list prices)

```
dose     gemini  deepseek
b8         5.84      0.44
b16        7.58      0.65
Phase 3   13.42      1.09   = $14.51
```

deepseek's ~96% provider-cache hit rate and ~20× cheaper tokens make it
nearly free; gemini pays mostly for output (3.6M output tokens, ~68% of
its bill) and its cache hit rate was only ~20%. Study total (Phases
0–3): **≈ $73**.

**This corrects the §11.5 gemini estimates.** At measured Phase 3
per-case rates, the 1600-run projections become: Phase 4 @ b8 ≈ **$339**
(gpt $80 + claude $159 + gemini $93 + deepseek $7), Phase 5 @ b16 ≈
**$478** (gpt $133 + claude $214 + gemini $121 + deepseek $10) — together
≈ **$817**: still under the €900 quote, but with far less margin than
the §11.5 figures (which had guessed gemini at ~$25/$35). Part of
gemini's measured rate is 503/timeout retry churn (real billed calls),
so these are conservative-high; still, gemini is the second-largest cost
in any full run.

### 13.5 Reproduce

```bash
# from llmpipe/ — fills only missing case files, so a replay against the
# committed cache snapshot (§11.4b, phases0-3) makes no API calls
python3 runtests.py tests/ballast/tests_core_100_b8.py  -llms gemini,deepseek -maxtokens 32000 -timeout 300
python3 runtests.py tests/ballast/tests_core_100_b16.py -llms gemini,deepseek -maxtokens 32000 -timeout 300

# the §13.1 table and ledger
cd results/ballast-robustness/analysis
python3 dose_response.py -doses 8,16 -models gemini,deepseek
python3 token_ledger.py  -doses 8,16 -models gemini,deepseek
```
