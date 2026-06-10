# Results 02 — Ballast robustness: distractor sentences at increasing dose

Companion to `wip/plans/02-ballast-robustness-experiments.md` (Tanel's ask,
2026-06-10: insert pure-ballast sentences into the test cases at increasing
dose and measure when accuracy degrades).
Status: **Phases 0–2 run (b2/b4/b8/b16 × gpt+claude on the 100-subset).**
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

Pool: 738 unique statement sentences from the 1600 set (4,179 raw − 1,600
questions − 246 wh − 167 pronoun − 22 short − 1,406 duplicates).

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
| 3 | 100-subset @ N_light/N_heavy, gemini+deepseek | pending |
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
- **`gk-bug-case1011-minimal.gkin`** — minimal reproducer (17 clauses +
  question, delta-debugged from case 1011's 141-clause prover input) for
  the gk datarec allocator error of §11.1. Run:
  `gk/gk-macos-arm64 llmpipe/axioms_std.js -strategytext
  '{"strategy": ["unit"], "query_preference": 0}' -seconds 2
  results/ballast-robustness/gk-bug-case1011-minimal.gkin -defaults
  -confidence 0.1 -keepconfidence 0.1 --datafolder gk` → fails in ~0.3s
  with "cannot extend datarec area"; `-mbsize` 1000–16000 does not help;
  removing the question makes it pass. Observed on macOS ARM64; ~1% of
  b16 cases — relevant for Phase 5.

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
The local sqlite cache (`llmpipe/cache.db`, gitignored, preserved) makes
replays of unchanged prompts free — that is what enables Tanel's
gk-strategy reruns at zero API cost.
