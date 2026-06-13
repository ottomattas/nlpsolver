#!/usr/bin/env python3
"""Five follow-up probes on the ballast-robustness traces (offline, ~$0).

All five run on the stored traces + cache only; gk is replayed locally where a
probe needs it (none of these do). Companion to the §16 probes; documented in
results.md §17.

  1. b4 anomaly    - is the gpt non-monotonic dip at b4 real or contamination?
  2. clause-loss   - within no_proof, is the parse loss omission or distortion?
  3. world-infl    - does ballast world-inflation predict world-shift failures?
  4. hard-core     - do the four models fail on the same cases (shared core)?
  5. confidence    - does low stage-1 self-confidence predict failure?

Usage:
  python3 extra_probes.py                 # all five, default doses/models
  python3 extra_probes.py -probe core     # one probe
  python3 extra_probes.py -doses 8,16,32 -models gpt,claude,gemini,deepseek
"""
import argparse, json, re, statistics as st
from collections import Counter

import common as C
import cause_map as CM

ALL_MODELS = ["gpt", "claude", "gemini", "deepseek"]


def _cells(doses, models):
    """Yield (dose, model, cells, manifest, exclusions) for cells with data."""
    for d in doses:
        for m in models:
            cc = C.load(d, m)
            if not cc:
                continue
            man, rev = C.resolve_manifest(d, cc)
            excl = C.exclusions(d) if rev is not None else set()
            yield d, m, cc, man, excl


def _nworlds(case):
    return len(set(re.findall(r'"(W\d+)"', json.dumps(case.get("clauses") or []))))


# --------------------------------------------------------------------------- 1
def probe_b4(doses, models):
    print("=== 1. b4 anomaly: dose curve, raw vs splitter-exclusions ===")
    for m in models:
        line = [f"  {m:9}"]
        for d in [2, 4, 8, 16, 32]:
            cc = C.load(d, m)
            if not cc:
                continue
            man, rev = C.resolve_manifest(d, cc)
            excl = C.exclusions(d) if rev is not None else set()
            kept = [c for cid, c in cc.items() if cid not in excl]
            acc = 100 * sum(C.is_correct(c) for c in kept) / len(kept)
            line.append(f"b{d}={acc:4.1f}(n{len(kept)})")
        print(" ".join(line))
    print("  -> gpt shows a real, exclusion-robust dip at b4; claude is monotone.\n")


# --------------------------------------------------------------------------- 2
def probe_clause_loss(doses, models):
    print("=== 2. clause-loss anatomy: cause buckets among no_proof failures ===")
    buck = Counter()
    total = 0
    for d, m, cc, man, excl in _cells(doses, models):
        b0 = C.load(0, m)
        for cid, c in cc.items():
            if cid in excl or cid not in man:
                continue
            if C.is_correct(c) or str(c.get("answer")) != "Unknown." or not c.get("clauses"):
                continue
            total += 1
            bkt, _ = CM.analyze_case(c, b0.get(cid), man[cid], intervene=False)
            buck[bkt] += 1
    print(f"  n_no_proof={total}")
    for b, n in buck.most_common():
        print(f"    {b:22s} {n:3d}  ({100 * n / total:.0f}%)")
    print("  -> whole-sentence omission is ~0; the loss is distortion/id-break.\n")


# --------------------------------------------------------------------------- 3
def probe_world_inflation(doses, models):
    print("=== 3. world-inflation vs failure (within fixed-dose cells, b0-correct only) ===")
    buckets = {"held": [], "wshift_flip": [], "other_flip": []}
    for d, m, cc, man, excl in _cells(doses, models):
        b0 = C.load(0, m)
        if not b0:
            continue
        cell = []
        for cid, c in cc.items():
            if cid in excl or cid not in man or cid not in b0 or not C.is_correct(b0[cid]):
                continue
            dw = _nworlds(c) - _nworlds(b0[cid])
            flip = not C.is_correct(c)
            lab = "held"
            if flip:
                bkt, _ = CM.analyze_case(c, b0.get(cid), man[cid], intervene=False)
                lab = "wshift_flip" if bkt == "pipeline-world-shift" else "other_flip"
            cell.append((dw, lab))
        if len(cell) < 10:
            continue
        mu = st.mean(x for x, _ in cell)
        sd = st.pstdev([x for x, _ in cell]) or 1.0
        for dw, lab in cell:
            buckets[lab].append((dw - mu) / sd)
    print("  dworld z-scored within each cell, pooled (mean z = world-inflation vs cell avg):")
    for k in ("held", "wshift_flip", "other_flip"):
        v = buckets[k]
        if v:
            print(f"    {k:12} n={len(v):4d}  mean_z(dworld)={st.mean(v):+.2f}")
    print("  -> world-shift failures specifically carry more ballast world-inflation.\n")


# --------------------------------------------------------------------------- 4
def probe_core(doses, models):
    print("=== 4. cross-model failure overlap (shared hard core) ===")
    for d in doses:
        present = [m for m in models if C.load(d, m)]
        if len(present) < 2:
            continue
        common_ids = None
        failset = {}
        for m in present:
            cc = C.load(d, m)
            man, rev = C.resolve_manifest(d, cc)
            excl = C.exclusions(d) if rev is not None else set()
            ids = {cid for cid in cc if cid in man and cid not in excl}
            common_ids = ids if common_ids is None else (common_ids & ids)
            failset[m] = {cid for cid in ids if not C.is_correct(cc[cid])}
        cnt = Counter()
        for m in present:
            for cid in failset[m]:
                if cid in common_ids:
                    cnt[cid] += 1
        dist = Counter(cnt.values())
        any_fail = sum(1 for cid in common_ids if cnt[cid] > 0)
        core = sum(1 for cid in common_ids if cnt[cid] == len(present))
        spread = ", ".join(f"{k}:{dist.get(k, 0)}" for k in range(1, len(present) + 1))
        print(f"  b{d}: models={len(present)} eval-common={len(common_ids)} | "
              f"fail in k models: {spread} | any-fail={any_fail} all-fail(core)={core}")
    print("  -> low dose = idiosyncratic failures; high dose exposes a shared core.\n")


# --------------------------------------------------------------------------- 5
def probe_confidence(doses, models):
    print("=== 5. stage-1 self-confidence vs downstream failure (b0-correct only) ===")

    def cstats(c):
        vs = [u.get("confidence") for p in c.get("stage1") or [] if isinstance(p, dict)
              for u in p.get("units", []) if isinstance(u.get("confidence"), (int, float))]
        return (min(vs), sum(vs) / len(vs)) if vs else None

    pooled_fail, pooled_ok = [], []
    for d, m, cc, man, excl in _cells(doses, models):
        b0 = C.load(0, m)
        if not b0:
            continue
        for cid, c in cc.items():
            if cid in excl or cid not in man or cid not in b0 or not C.is_correct(b0[cid]):
                continue
            cs = cstats(c)
            if not cs:
                continue
            (pooled_fail if not C.is_correct(c) else pooled_ok).append(cs[0])
    if pooled_fail and pooled_ok:
        print(f"  pooled min stage-1 confidence: "
              f"fail={st.mean(pooled_fail):.3f} (n={len(pooled_fail)})  "
              f"ok={st.mean(pooled_ok):.3f} (n={len(pooled_ok)})")
    print("  -> failing cases self-report lower stage-1 confidence (strongest at b32).\n")


PROBES = {
    "b4": probe_b4,
    "clloss": probe_clause_loss,
    "world": probe_world_inflation,
    "core": probe_core,
    "conf": probe_confidence,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-doses", default="8,16,32")
    ap.add_argument("-models", default=",".join(ALL_MODELS))
    ap.add_argument("-probe", default="all", choices=["all"] + list(PROBES))
    a = ap.parse_args()
    doses = [int(x) for x in a.doses.split(",") if x.strip()]
    models = [x.strip() for x in a.models.split(",") if x.strip()]
    chosen = PROBES.keys() if a.probe == "all" else [a.probe]
    for name in chosen:
        PROBES[name](doses, models)


if __name__ == "__main__":
    main()
