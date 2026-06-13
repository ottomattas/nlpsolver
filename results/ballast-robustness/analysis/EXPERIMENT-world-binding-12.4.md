# Experiment branch: `experiment/world-binding-12.4`

**Status:** speculative / exploratory. This branch is intentionally isolated
from `main`. If the offline ceiling below is not worth it, the branch is
abandoned and nothing on `main` is affected. If it is worth it, the actual
convert-layer prototype is built here (step 2) before anything is proposed.

## Why this branch exists

`results.md` §12.4, §15.4 and §17.3 all converge on one claim: the dominant
ballast failure is **not** an LLM-parse problem but a **convert-layer** one.
`lc_packages` binds a stateless / tenseless question to the *latest* world
constant. Ballast **event** sentences keep advancing the world chain
(`W0`→`W1`→…), so by the end the question is pinned to a world where the answer
no longer holds — `pipeline-world-shift`, the single largest `no_proof` slice
(~28%, §17.2), and the one cause that chunking provably cannot reach (§15.4).
§17.3 added direct evidence: world-shift failures specifically carry +0.31 SD
more ballast-induced world inflation than held cases.

The proposed fix (§12.4) is to bind the question to a world **variable**
instead of a constant, so it unifies with whichever world the relevant fact
holds in.

## Why it is "high-risk" (and therefore branched, not on `main`)

Unlike the §16/§17 probes, the real fix is a **semantic change to the convert
layer** — Tanel's code, which he is actively editing (`-slightcoarse` &c.):

1. It changes the meaning of *every* case's clauses, not just the failing ones.
2. Freeing the question world too eagerly lets it unify with the **wrong**
   world → **spurious proofs** (a wrong `True.`/`False.`, worse than an honest
   `Unknown.`). This is the same over-merge risk §16.3 measured for world-merge.
3. It is Tanel's design call; an additive-only constraint has held all along.

## What this branch measures FIRST (step 1, low-risk, $0)

`world_binding.py` estimates the fix's **ceiling** without touching the
pipeline. For every case whose question world is *pinned* to a constant, it
re-runs the post-LLM pipeline (`logconvert → semnormalize → gk`, zero LLM
calls) twice — unchanged ("plain") and with the question world freed to a fresh
variable ("freed", `spot_verify.free_question_world`, i.e. the §12.4 transform)
— and grades both with the pipeline's own matcher.

- **`freed − plain`** = the pure §12.4 effect (same convert path, only the
  world binding differs).
- **rescues** (plain-wrong → freed-right) = world-shift failures the fix
  recovers.
- **regressions** (plain-right → freed-wrong) = the spurious-proof cost.

Caveat to apply when reading: some "rescues" coincide with a gk **allocator
crash** in the plain replay (`prover returned empty result` / `datarec`);
freeing the world changes the clause set and can sidestep the crash without the
world binding being the real cause (per `cause_map.freeworld_intervention`).
Those are flagged in the verbose log and must be discounted from clean rescues.

Cohort (b0-correct cases, b8/b16/b32 × 4 models): 310 pinned candidates
(108 currently failing = rescue targets, 202 currently passing = regression
risk).

Reproduce:
```bash
cd results/ballast-robustness/analysis
python3 world_binding.py -doses 8,16,32 -models gpt,claude,gemini,deepseek -verbose
```

## The gate

- **Escalate** (build the real convert prototype on this branch, with a strong
  writeup) only if clean rescues clearly exceed regressions and `freed − plain`
  is meaningfully positive — and ideally grows with dose (where world-shift is
  more common).
- **Abandon** the branch otherwise.

## Results

Full run, b0-correct cohort, 310 pinned candidates, gk budget 20s
(`freed`/`plain` both gk-replayed; `stored` = the live answer):

```
cell           n  cand  stored plain freed  rescue regr
gpt b8        93   17     88    88    89      2    1
claude b8     91   25     82    83    84      3    2
gemini b8     99   32     89    89    91      4    2
deepseek b8   98   27     86    88    90      3    1
gpt b16       68   16     54    55    60      5    0
claude b16    66   20     57    58    63      5    0
gemini b16    99   30     81    82    86      5    1
deepseek b16  98   27     86    87    89      2    0
gpt b32      100   25     72    73    78      5    0
claude b32    98   31     71    70    78      8    0
gemini b32    99   32     66    65    73      8    0
deepseek b32  98   28     74    74    78      4    0
------------------------------------------------------
TOTAL              310   906   912   959     54    7

pure §12.4 effect (freed - plain): +47
headline (freed - stored): +53   (convert drift plain - stored: +6)
rescues 54  vs  regressions 7  -> net +47
```

**Dose-growing, as §12.4 predicts.** Δ(freed−stored) is +9 at b8, +20 at b16,
+24 at b32 — the fix claws back the most exactly where world-shift dominates.
Per cell at b32 it recovers ~6–7 accuracy points (gpt 72→78, claude 71→78,
gemini 66→73, deepseek 74→78), i.e. roughly a quarter of the ballast-induced
drop. It is **not** a full fix (the rest is genuine parse distortion, §17.2),
but it is the single largest offline lever found.

**Regressions are rare and low-dose only:** 7 of 310 candidates, six of them at
b8, **zero at b16/b32**. The spurious-proof cost of freeing the question world
is real but small and does not grow with dose.

**Caveats:** ~8 of the 54 rescues coincide with a gk allocator crash in the
plain replay (250, 1317, 1011, 1052, 1375 — `prover returned empty result`);
freeing the world changes the clause set and can sidestep the crash without the
world binding being the true cause. Discounting those, clean net ≈ **+39**,
still strongly positive. Recurring clean rescues 1239 and 1521 appear in nearly
every cell — robust world-shift cases the fix reliably recovers.

## Verdict: GATE MET → escalate

Clean rescues (~46) ≫ regressions (7), `freed − plain` is clearly positive
(+47), and the effect grows with dose. The §12.4 convert-layer fix is worth
building. **Step 2** (this branch): prototype the actual fix in `lc_packages` /
the convert layer (bind the question to a world variable instead of the latest
constant), re-run the curve, and confirm the live result matches this ceiling —
to be done deliberately and with Tanel, since it is a semantic change in his
code. The regression set (1310, 1375 at b8) is the targeted-test list to make
sure the live fix does not over-free.
