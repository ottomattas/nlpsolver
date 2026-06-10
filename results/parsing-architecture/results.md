# Results 01 — Parsing-architecture experiments: two-stage vs one-stage

Companion to `wip/plans/01-parsing-architecture-experiments.md`.
Status: **Gate-1 complete** (100-subset, all 4 models). Full 1600-set **not run** —
awaiting Tanel's go-ahead.
Run: `nlpsolver/llmpipe` on macOS (local `gk` ARM64), LLM cache on, thinking off
(baseline decoding). Date: 2026-06-09.

---

## 0. TL;DR (the answer to "kas kaks stage on parem kui üks, ja kui palju ja mis juhul")

- **Yes, two-stage is better** — for **every** model, on every cut. One-stage
  almost never rescues a case that two-stage misses.
- **By how much: model-dependent.** Big for the stronger models (gpt 100→86,
  claude 98→90), small for the cheap ones (gemini 99→97, deepseek 98→96).
  Aggregate over 400 cases: **A 98.8% vs best one-stage 91.5%** (~7 pts).
- **In which cases:** negation/polarity, comparatives, change-of-state/aspect,
  multi-answer conjunctions, defeasible (exception) reasoning, and modal hedging
  — the cases where decomposing into an explicit intermediate first pays off.
- **Key nuance:** the win comes from the **separate second call (A)**, *not* from
  the ASU representation per se. Asking one call to "think in ASUs" then emit
  logic (**B**) is **no better** than going straight to logic (**C**): 90.2% vs
  91.5%. The staged refinement is the lever, not the in-prompt structure.

## 1. What was run

The architecture ladder from the plan (§3), Stages 3–5 held identical:

| ID | Condition | LLM calls | Intermediate ASU |
|----|-----------|----------:|------------------|
| **A** | Two-stage (baseline) | 2 | explicit, separate call |
| **B** | One-call, structured | 1 | reasoned through in one response, then logic |
| **C** | One-call, direct | 1 | none (English → Stage-2 logic JSON directly) |

- Models: `gpt-5.1`, `claude-sonnet-4-6`, `gemini-2.5-flash`, `deepseek-v4-flash`.
- Dataset: `tests_core_100.py` (100 curated cases). **1200/1200 case-runs, 0 errors.**
- B and C were built **additively** (new `prompts/onestage_*_wrapper.txt`,
  `llmparse.parse_text_onestage`, `solve.py -onestage`, condition-tagged
  `runtests.py`). The baseline Stage-1/Stage-2 prompts and the Stage-2 contract
  are untouched, so Condition A is unchanged and reproducible.

## 2. RQ1 — Is two-stage better? Accuracy matrix

```
model      A two-stage   B one-struct   C one-direct
gpt           100.0%         84.0%          86.0%
claude         98.0%         87.0%          90.0%
gemini         99.0%         97.0%          94.0%
deepseek       98.0%         93.0%          96.0%
-----------------------------------------------------
ALL (n=400)    98.8%         90.2%          91.5%
```

Two-stage is highest for all four models. **Answer: yes.**

## 3. RQ2 — By how much? Magnitude + case-level win/loss

Gap (A − best one-stage variant), per model:

| model | A | best 1-stage | gap |
|-------|--:|--:|--:|
| gpt | 100 | 86 | **14** |
| claude | 98 | 90 | **8** |
| gemini | 99 | 97 | 2 |
| deepseek | 98 | 96 | 2 |

The gap is carried by the stronger models; the cheap models are nearly flat. The
win/loss ledger shows the advantage is **near-strict**, not an averaging artefact
(`A>1` = A correct & one-stage wrong; `1>A` = the reverse):

```
              A vs B (struct)            A vs C (direct)
model      A>1  1>A  both  neither    A>1  1>A  both  neither
gpt         16    0    84     0        14    0    86     0
claude      12    1    86     1        10    2    88     0
gemini       3    1    96     0         6    1    93     0
deepseek     7    2    91     0         4    2    94     0
```

One-stage rescues a two-stage failure in only **0–2 cases per model** — two-stage
essentially dominates.

## 4. RQ3 — In which cases does the second stage matter?

Cases where **A is correct but BOTH one-stage variants fail** (the "needs the
second stage" set), with how many models miss them:

| case | #models | expected | input (truncated) | phenomenon |
|------|:------:|----------|-------------------|------------|
| 612 | **4/4** | "a red car and a blue bicycle" | *John bought a red car and a blue bicycle. What did John buy?* | multi-answer conjunction |
| 1310 | 3 | garden | *...Mary went to... Where is Mary?* | multi-hop location tracking |
| 553 | 2 | False | *The mountain is higher than the hill. Is the hill higher...?* | comparative asymmetry |
| 605 | 2 | False | *...studied hard and passed the exam. Did the students fail?* | lexical/negation entailment |
| 1206 | 2 | False | *John stopped smoking. Does John smoke now?* | change-of-state / aspect |
| 1365 | 2 | "Mike or Mickey" | *If X is a father of Y... (grandfather rules)* | multi-premise rule chaining |
| 234, 893 | 1 | True/False | possessive / relative-clause presupposition | embedded structure |
| 1427, 1429 | 1 | True | *Penguins do not fly. Birds fly...* / baby birds | defeasible / exception reasoning |
| 1500 | 1 | "Likely false" | *Tallinn is hardly in Latvia...* | modal hedging |
| 1011, 1099, 1146, 248, 671 | 1 | mixed | negation, wh-questions | polarity / wh |

The recurring themes — **negation & polarity, comparatives, change-of-state,
multi-answer conjunctions, defeasible reasoning, modal hedging** — are exactly
where an explicit intermediate decomposition before logic encoding helps.

**Regressions (one-stage beats two-stage)** are rare and mostly model-specific:
case 1052 (claude, "destroyed → not intact"), 28 (gemini, "Probably true"
confidence), 1340/1335 (deepseek). ~4 distinct cases total — two-stage is not
strictly Pareto, but close.

## 5. The key architectural finding (A→B vs B→C)

- **A → B (the separate second call):** 98.8% → 90.2%. This is the real cost of
  collapsing to one call.
- **B → C (the ASU representation in-prompt):** 90.2% → 91.5% — a wash (C even
  slightly ahead overall). Telling a single call to "reason through ASUs" buys
  essentially nothing over going direct.

Interpretation: the benefit of the architecture is the **staged refinement / second
round-trip**, not the ASU intermediate format itself. A clean, defensible story.

## 6. Caveats / threats to validity

- **Scope:** 100-subset only. It is *curated to be easy* (A scores 98–100%), so
  this likely **understates** the gap. The full 1600-set is needed for
  paper-grade magnitudes and per-phenomenon breakdowns. **Not run yet (pending
  Tanel).**
- **Prompt fairness:** B/C reuse the full Stage-1+Stage-2 specs as reference, so
  one-stage has the *same knowledge* as two-stage; only the I/O contract differs.
  The one-stage prompts have had **no iteration budget** yet — a weak prompt
  understates one-stage, so these numbers are a lower bound for one-stage.
- **Mac vs Linux `gk`:** A re-run locally on Mac (98–100%) matches the published
  Linux baseline range; no parity concern observed.
- **Decoding:** thinking off for all (baseline). Reasoning-on is extension E3.

## 7. Reproduce

```bash
# from llmpipe/ — A/B/C for one model on the 100-subset
python3 runtests.py tests/tests_core_100.py -llms gemini                     # A
python3 runtests.py tests/tests_core_100.py -llms gemini -onestage struct    # B
python3 runtests.py tests/tests_core_100.py -llms gemini -onestage direct    # C

# overview + per-case win/loss (from repo root)
python3 tools/status.py          # add: core 1600  for the full set
python3 tools/winloss.py

# extensions (X2 needs new runs; the rest re-analyse the committed snapshot)
cd llmpipe
python3 runtests.py tests/tests_core_100.py -ids 612,1206,1310,234,553,605,1365,117,248,598 -onestage refine   # X2 (Condition D)
python3 runtests.py tests/tests_core_defeasible.py                 # X3 condition A
python3 runtests.py tests/tests_core_defeasible.py -onestage direct # X3 condition C
cd ../results/parsing-architecture/analysis
python3 x1_faithfulness.py   # X1   (free)
python3 x2_selfrefine.py     # X2   (reads committed snapshot)
python3 x3_defeasible.py     # X3   (reads committed snapshot)
python3 e8_complexity_scaling.py     # E8  (free)
python3 e2_failure_localisation.py   # E2  (free)
python3 e5_cost_frontier.py          # E5  (free)
```
Per-case outputs (this committed snapshot): `results/parsing-architecture/core_100/{twostage,onestage-struct,onestage-direct}/<llm>/case_NNNN.json` (+ `summary.json` per cell). The live working copy that `runtests.py` writes is the gitignored `llmpipe/testresults/`.

## 8. Extensions — six ready-to-run studies for the paper

These build on the Gate-1 result without duplicating Tanel's own plans. Each is
specified below in ~10 sentences: the **question**, the **prompt/method** it uses,
**how it is run** (a 10-case × 4-model pilot, or pure re-analysis of the committed
1,200-run dataset), the **pilot result**, and — explicitly — **what it contributes
to the paper**. The apparatus for all six is committed so Tanel can pick any one
and scale it to the full 1600-set by changing the test file or `-ids`. Analysis
code lives in `analysis/`; the X2/X3 pilot data is snapshotted alongside core_100.

### 8.0 Token cost (so the spend is legible)

A single one-stage call ≈ **56K input tokens**; two-stage splits this into a
~26K Stage-1 + ~30K Stage-2 call (≈ 56K total). Per-case output is small (logic
JSON, ~0.3–2K). Four of the six extensions cost **zero new tokens** — they
re-analyse data we already paid for.

| Ext | New generation? | Pilot run | New tokens (10×4) | Status |
|-----|-----------------|-----------|-------------------|--------|
| **X1** parse faithfulness | no — re-analysis + local `gk` | — | ~0 | **done** |
| **X2** decomposition vs self-refine | yes — 1 refine call/case (pass-1 cache-hits C) | `selfrefine` on 10 A>C cases | ~2.2M | **done** |
| **X3** defeasible focus | yes — A+C on fresh defeasible cases | `core_defeasible` A & C | ~5M (1427/1429 cache-hit) | **done** |
| **E8** complexity scaling | no — re-analysis | — | ~0 | **done** |
| **E2** failure localisation | no — re-analysis of traces | — | ~0 | **done** |
| **E5** accuracy-per-cost | no — proxy from prompt sizes | — | ~0 | **done** |

Total new spend for the full pilot set ≈ **~7M tokens (~$8–12)**, dominated by
claude+gpt; gemini/deepseek are pennies. The paper reports calls/tokens, not
dollars.

### 8.1 X1 — Parse faithfulness / logical-form agreement  *(`analysis/x1_faithfulness.py`)*

The Gate-1 numbers are end-to-end *answer* accuracy; X1 asks whether the two-stage
*logical form itself* is better, which is the claim a logic audience cares about.
**No new prompt** is needed: it re-reads the stored Stage-2 logic, clause lists and
answers for A/B/C and scores logic-level quality — sentence-package coverage,
whether the question is encoded, clause depth (logic richness), and the rate of
unprovable "Unknown" outputs. It then takes every case where A and C return
*different answers* and asks which condition's logic was right. **Result:** when A
and C disagree, two-stage wins overwhelmingly — gpt **14–0**, claude **10–2**,
gemini **6–1**, deepseek **4–2** — and A produces richer logic (~20 vs ~17 clauses)
with fewer "Unknown"s (gpt 24% vs 34%). So the divergence is not luck: the
two-stage *encoding* is more faithful, not just its final answer. **Paper
contribution:** it reframes the headline from "two-stage answers better" to
"two-stage parses better", grounding the architecture claim at the logical-form
level and giving the qualitative figure (e.g. case 553: A keeps the comparative as
`has degree rel2`, C flattens it to a bare `>` and cannot prove the answer).
Scaling = run on the 1600-set for per-phenomenon faithfulness deltas.

### 8.2 X2 — Decomposition vs. self-refinement  *(`analysis/x2_selfrefine.py`, prompt `prompts/onestage_refine_user.txt`)*

Gate-1 §5 showed the win comes from the separate second *call*, not the ASU format
— but "second call" still conflates two mechanisms, and X2 separates them. The new
**Condition D (`-onestage refine`)** does one-stage-direct, then a **second LLM call
that shows the model its own logic and asks it to critique and correct it** (the
prompt `onestage_refine_user.txt` explicitly forbids introducing ASUs, so it is the
*same* subtask twice = iteration, not decomposition). D therefore matches A's call
count (2) and C's no-ASU encoding, isolating *decomposition* (two different
subtasks, as in A) from *iteration* (a second pass over the same subtask). It is run
on the 10 cases where A beats C; pass-1 hits the cached Condition-C result, so only
the refine call is billed (~2.2M tokens). **Result (decisive):** A **97.5%**, C
**45.0%**, D **45.0%** — self-refinement rescued **0 of 22** failing cases across all
four models and changed *zero* answers; it recovers **0%** of the decomposition gap.
A model re-reading its own one-shot logic stays locked in the same under-specified
encoding. **Paper contribution:** this is the mechanistic core of the story — the
two-stage benefit is specifically the *decomposition into a separate parse subtask*,
not extra compute, not iteration, and not the ASU notation; that triangulation
(A>C, B≈C, D≈C) is a clean, novel result for a neuro-symbolic venue. Scaling = run D
on the full A>C set from the 1600 run.

### 8.3 X3 — Defeasible / nonmonotonic focus  *(`analysis/x3_defeasible.py`, set `tests/tests_core_defeasible.py`)*

X3 asks *where* the decomposition advantage lives, hypothesising it concentrates on
**defeasible reasoning** — generics overridden by exceptions ("birds fly" /
"penguins do not fly") — because that is exactly where `gk`'s nonmonotonic blocker
machinery is essential and where a single-pass first-order encoding has no sound
form. **No new prompt**: the instrument is a curated 10-case defeasible set drawn
verbatim from the suite's *DEFAULT & DEFEASIBLE* and *DEFAULTS WITH EXCEPTIONS*
sections (ids/expected identical, so results are comparable), run under A vs C. A
one-shot parse tends to emit a plain universal that the exception then
contradicts; the two-stage parse isolates the default/exception structure before
encoding it. The A−C gap on this set is contrasted with the ~7pt overall gap on
core_100 — a markedly larger gap = the advantage is defeasible-driven. **Result:**
A **100%** vs C **85%** — a **15pt** gap, ~2× the ~7.3pt overall gap — carried by
the strongest model: gpt collapses 100%→**40%** in one-stage on the penguin /
baby-bird cases (1408/1424/1426/1427/1429/1458), while claude/gemini/deepseek hold
100% on this small set (so the full defeasible phase is needed to size the effect
for the smaller-gap models). **Paper contribution:** it pins the architecture benefit
to the phenomenon class where the symbolic prover does work an LLM cannot soundly
do alone — the strongest possible framing for a neuro-symbolic paper, since it shows
the neural front-end and the symbolic back-end are *complementary*, not redundant.
Scaling = the full ~73-case defeasible/exception phase of the 1600-set.

### 8.4 E8 — Complexity scaling  *(`analysis/e8_complexity_scaling.py`)*

E8 asks whether one-stage fails *more* as inputs grow, which would explain why the
curated-easy 100-subset *understates* the gap. **No new prompt**: it derives cheap
complexity features per case (sentence count, words, and two-stage package count as
a structural-entity proxy), bins cases low/med/high, and reports A vs C accuracy and
their gap per bin, plus the point-biserial correlation between complexity and C
being wrong. **Result:** the A−C gap climbs from **2.3 pts (low)** to **11.3 (med)**
and **8.2 (high)**, with positive correlations (entities r=+0.14); the signal is
real but muted because the 100-subset is deliberately easy. **Paper contribution:**
it both motivates the full-1600 run (the gap is complexity-gated, so the easy subset
is a lower bound) and supplies a scaling curve — "decomposition matters more the
harder the sentence" — which is a quantitative, defensible claim rather than an
anecdote. Scaling = the 1600-set, where the high-complexity phases (relative
clauses, possession inference, measures) will sharpen the slope.

### 8.5 E2 — Failure-localisation taxonomy  *(`analysis/e2_failure_localisation.py`)*

E2 turns "one-stage is worse" into "one-stage breaks *here*", attributing each
incorrect run to the pipeline stage where it failed. **No new prompt**: it reads the
stored trace and buckets every wrong run as parse-fail (no logic), no-question (the
query wasn't encoded), convert-fail (no clauses), no-proof (clauses but the prover
returns "Unknown" — a fidelity gap), wrong-answer (a confident but mis-encoded
answer), or error. **Result:** one-stage failures localise almost entirely to
**no-proof (20/34 for C)** and **wrong-answer (13/34)**, with parse/convert failures
near zero; two-stage has only 5 failures total of any kind. **Paper contribution:**
it shows the cost of collapsing the parse is *semantic* — the single pass emits
logic that is too weak to prove or subtly wrong — not a formatting or plumbing
problem, which both rules out trivial explanations and tells a reader exactly what
the second stage fixes. It also pairs with X1 (the no-proof bucket *is* the
"Unknown" faithfulness failure). Scaling = the same taxonomy on the 1600-set yields
a per-phase failure-origin table.

### 8.6 E5 — Accuracy-per-cost frontier  *(`analysis/e5_cost_frontier.py`)*

E5 answers the practitioner's question — "is the second stage worth it?" — on two
cost axes the data supports: LLM requests per case and input-token budget. **No new
prompt**: it counts base calls plus logged retries and multiplies the measured
per-call prompt sizes. **Result (counter-intuitive):** two-stage uses ~**2.08
requests/case** but only **56,027 input tokens** — essentially the *same* token
budget as a single one-stage call (56,391), because A splits the prompt into two
smaller halves; on accuracy-per-100K-input-tokens A (**176**) actually beats C
(**162**). **Paper contribution:** it dismantles the natural objection that
two-stage "costs 2×" — the extra accuracy costs one extra *request* (and the
output tokens), not extra input tokens, so on a token-budget basis the second stage
is close to free; the only real axis on which one-stage wins is request count /
latency. This gives the paper an honest, quantified cost-benefit recommendation.
(Output tokens are not logged, so this is an input-token + request-count frontier; a
re-run with usage capture would close that gap.) Scaling = recompute on the 1600-set.

### 8.7 Left to Tanel (avoid duplication)

- **E1 — Stage-3 / "ilma reegliteta" axiom ablation** (Tanel said he'll do this).
- **RQ4 — nonce-word arm** (Tanel's classic question; offer support only).
- **E3 (reasoning on/off)** and **E7 (retry-loop contribution)** remain noted in the
  plan as cheap follow-ups if a reviewer asks.

## 9. Open decision

Scope to the **full 1600-set** (A/B/C × 4 models) for paper-grade numbers and the
per-phase/per-subsection RQ3 breakdown, and to scale whichever extension Tanel
prefers (X1–X3, E2/E5/E8 above). The apparatus is ready; **holding the big run
until Tanel confirms** scope and which extension to lead with.
