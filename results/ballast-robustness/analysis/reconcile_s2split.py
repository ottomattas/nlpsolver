#!/usr/bin/env python3
"""Proposal 3 (plan 04 follow-up): would a symbolic CROSS-CHUNK
RECONCILIATION pass turn -s2split into a net robustness win?

s2split breaks fresh cases at chunk joins because the per-sentence stage-2
calls share no global registry (results.md §15.2-§15.4, §12.4): a referent
fractures into several ids, and each chunk re-emits its own world-context
and `$theof` definitions.  §12.4 predicted a "global entity registry" would
be needed.  This tests the cheapest symbolic version of that idea -- applied
AFTER the LLM, on the stored clauses, zero LLM cost:

  reconcile(clauses) =
    canonicalise entity ids   ("#:lamp 3" -> "#:lamp": one id per base name)
    merge worlds              (every "W<k>" -> "W0": one world)
    dedupe identical facts     (collapse the per-chunk re-emitted duplicates)

then gk is replayed UNCHANGED on the reconciled set (same path as
spot_verify.gk_replay) and the answer is graded with the pipeline's own
matcher (test._result_matches).  The §15.2 rescued/broken table is recomputed
under reconciliation so the net effect (and any over-merge cost -- collapsing
two genuinely distinct same-name referents into a spurious proof) is visible.

Only cases the transform actually changes are replayed; the rest keep their
stored s2split answer.

Run:  python3 reconcile_s2split.py [-doses 8,16]
        [-models gpt,claude,gemini,deepseek] [-tag s2split_slightcoarse]
        [-no-world-merge] [-verbose] [-live]
"""
import os
import re
import sys
import copy
import json
import argparse
import common as C

sys.path.insert(0, os.path.join(C.REPO, "llmpipe"))
sys.path.insert(0, os.path.join(C.REPO, "llmpipe", "solver"))

_ENT = re.compile(r"^(#:.*?)\s+\d+$")
_WORLD = re.compile(r"^W\d+$")


def _matcher():
  import test as _t
  return _t._result_matches


def reconcile(clauses, world_merge=True, dedupe=True):
  """Canonicalise entity numbering, merge worlds, dedupe identical facts.
  Question clauses are never deduped (there must stay exactly one)."""
  def walk(t):
    if isinstance(t, list):
      return [walk(x) for x in t]
    if isinstance(t, dict):
      return {k: (v if k == "@nl" else walk(v)) for k, v in t.items()}
    if isinstance(t, str):
      m = _ENT.match(t)
      if m:
        return m.group(1)
      if world_merge and _WORLD.match(t):
        return "W0"
    return t

  out, seen = [], set()
  for cl in copy.deepcopy(clauses):
    c2 = walk(cl)
    if dedupe and isinstance(c2, dict) and "@question" not in c2 \
       and "question" not in str(c2.get("@sourcetype", "")):
      key = json.dumps(c2.get("@logic"), sort_keys=True)
      if key in seen:
        continue
      seen.add(key)
    out.append(c2)
  return out


def gk_replay_clauses(case, clauses):
  import prover
  from procproofs import process_proof
  logic = [{k: v for k, v in cl.items() if k != "@nl"}
           if isinstance(cl, dict) else cl
           for cl in copy.deepcopy(clauses)]
  if not logic:
    return None
  pr = prover.call_prover(logic, s1_json=case.get("stage1"))
  return str(process_proof(pr, text=case["input_text"],
                           s1_json=case.get("stage1"),
                           s2_json=case.get("stage2"), logic=logic,
                           options=None))


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("-doses", default="8,16")
  ap.add_argument("-models", default="gpt,claude,gemini,deepseek")
  ap.add_argument("-tag", default="s2split_slightcoarse")
  ap.add_argument("-no-world-merge", action="store_true", dest="no_world")
  ap.add_argument("-live", action="store_true")
  ap.add_argument("-verbose", action="store_true")
  args = ap.parse_args()
  source = "live" if args.live else "snapshot"
  doses = [int(s) for s in args.doses.split(",") if s.strip()]
  models = [x for x in args.models.split(",") if x]
  match = _matcher()

  def correct(expected, answer, text):
    if answer is None:
      return False
    try:
      return bool(match(expected, answer, text, single_stage=False))
    except Exception:
      return False

  rows = []
  for d in doses:
    for m in models:
      split = C.load(d, m, source, tag=args.tag)
      base = C.load(d, m, source)
      if not split or not base:
        continue
      man, rev = C.resolve_manifest(d, split)
      excl = C.exclusions(d) if rev is not None else set()
      ids = sorted(c for c in split
                   if c in base and c in man and c not in excl)
      acc = {"base": 0, "split": 0, "recon": 0}
      flips = {"split_resc": [], "split_brk": [],
               "recon_resc": [], "recon_brk": [],
               "recon_fixed": [], "recon_newbrk": [], "overmerge": []}
      n_replayed = 0
      for cid in ids:
        sc = split[cid]
        exp = sc.get("expected_answer")
        text = sc.get("input_text")
        bcor = C.is_correct(base[cid])
        scor = C.is_correct(sc)
        cl = sc.get("clauses") or []
        rc = reconcile(cl, world_merge=not args.no_world)
        if not cl or json.dumps(rc) == json.dumps(cl):
          rcor, rans = scor, str(sc.get("answer"))
        else:
          n_replayed += 1
          rans = gk_replay_clauses(sc, rc)
          rcor = correct(exp, rans, text)
        acc["base"] += bcor
        acc["split"] += scor
        acc["recon"] += rcor
        if scor and not bcor:
          flips["split_resc"].append(cid)
        if bcor and not scor:
          flips["split_brk"].append(cid)
        if rcor and not bcor:
          flips["recon_resc"].append(cid)
        if bcor and not rcor:
          flips["recon_brk"].append(cid)
        if rcor and not scor:
          flips["recon_fixed"].append(cid)
        if scor and not rcor:
          flips["recon_newbrk"].append(cid)
          flags = (str(sc.get("answer")) == "Unknown.")  # was no_proof
          if not flags:
            flips["overmerge"].append(cid)
      rows.append((m, d, rev, acc, flips, n_replayed, len(ids)))

  wm = "off" if args.no_world else "on"
  print(f"\n==== Proposal 3: s2split + symbolic reconciliation "
        f"(world-merge {wm}) ====")
  print("accuracy (of valid graded cases); flips vs the PLAIN baseline\n")
  hdr = (f"{'cell':14s} {'base':>4s} {'split':>5s} {'recon':>5s}  "
         f"{'split r/b':>9s}  {'recon r/b':>9s}  {'recon vs split fix/new':>22s}")
  print(hdr)
  print("-" * len(hdr))
  tot = {"base": 0, "split": 0, "recon": 0}
  for m, d, rev, acc, fl, nrep, n in rows:
    for k in tot:
      tot[k] += acc[k]
    print(f"{m+' b'+str(d):14s} {acc['base']:>4d} {acc['split']:>5d} "
          f"{acc['recon']:>5d}  "
          f"{len(fl['split_resc']):>4d}/{len(fl['split_brk']):<4d} "
          f"{len(fl['recon_resc']):>4d}/{len(fl['recon_brk']):<4d} "
          f"{len(fl['recon_fixed']):>10d}/{len(fl['recon_newbrk']):<4d}"
          f"  (replayed {nrep}/{n})")
    if args.verbose:
      if fl["recon_fixed"]:
        print(f"      reconciliation FIXED (split-wrong -> ok): {fl['recon_fixed']}")
      if fl["recon_newbrk"]:
        print(f"      reconciliation NEW-BROKE (split-ok -> wrong): "
              f"{fl['recon_newbrk']}  of which over-merge: {fl['overmerge']}")
  print("-" * len(hdr))
  print(f"{'TOTAL':14s} {tot['base']:>4d} {tot['split']:>5d} {tot['recon']:>5d}")
  net_split = tot["split"] - tot["base"]
  net_recon = tot["recon"] - tot["base"]
  print(f"\nnet vs baseline: s2split {net_split:+d},  "
        f"s2split+reconcile {net_recon:+d}  (positive = robustness win)")
  print("Read: reconciliation is a net win only if 'recon vs split fix' "
        "clearly exceeds 'new',\nand 'recon r/b' beats 'split r/b'. Over-merge "
        "= a previously-correct case turned wrong\nby collapsing distinct "
        "same-name referents (the §12.4 spurious-proof risk).")


if __name__ == "__main__":
  main()
