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
python3 wip/status.py            # add: core 1600  for the full set
python3 wip/winloss.py
```
Per-case outputs (this committed snapshot): `results/parsing-architecture/core_100/{twostage,onestage-struct,onestage-direct}/<llm>/case_NNNN.json` (+ `summary.json` per cell). The live working copy that `runtests.py` writes is the gitignored `llmpipe/testresults/`.

## 8. Proposed extensions — for Tanel to pick

These build on the Gate-1 result without me duplicating Tanel's own plans. Two
tiers by cost:

**Free (re-analysis of the existing A/B/C outputs — no new API calls):**
- **E2 — Failure-localisation taxonomy.** Attribute each one-stage failure to
  Stage-2 vs logconvert vs prover vs rendering, using the stored traces. Turns
  §4 into a *where it breaks* table.
- **E5 — Accuracy-per-cost frontier.** Plot accuracy vs LLM-call/token cost
  (two calls ≈ 2×). Practical "is the second stage worth it" curve.
- **E7 — Retry-loop contribution.** How much the sanity-check corrective retry
  adds, per condition (the stats are already logged).

**Needs new runs (extra spend/time):**
- **E3 — Reasoning on/off.** Does enabling model "thinking" let one call recover
  the two-stage gap? Small subset, gpt/claude/gemini toggles. (Directly tests the
  §5 "is it just externalised reasoning?" question.)
- **E4 — Model-strength interaction.** Does the gap shrink as models get stronger?
  The Gate-1 data already hints the opposite (gpt has the *largest* gap) — worth a
  clean extra model point per provider.
- **E6 — Paraphrase robustness.** Stability per condition under light syntactic
  perturbation.

**Left to Tanel (flagged in plan §9, avoid duplication):**
- **E1 — Stage-3 / "ilma reegliteta" axiom ablation** (Tanel said he'll do this).
- **RQ4 — nonce-word arm** (Tanel's classic question; offer support only).

## 9. Open decision

Scope to the **full 1600-set** (A/B/C × 4 models) for paper-grade numbers and the
per-phase/per-subsection RQ3 breakdown? It is a large run — **holding until Tanel
confirms** he wants it and which extensions (E2–E7) he'd like from me.
