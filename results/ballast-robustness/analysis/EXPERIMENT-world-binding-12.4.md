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

_(filled when the full run completes; see `/tmp/world_binding.log`.)_

Partial (b8, raw — rescues not yet discounted for gk-crash contamination):
gpt 88→89 (+2 resc / −1 regr), claude 82→84 (+3/−2), gemini 89→91 (+4/−2, 2 of
the rescues are gk-crash sidesteps), deepseek 86→90 (+4/−0, 1 gk-crash sidestep).
Net at b8 is small and partly contaminated; the verdict waits on b16/b32.
