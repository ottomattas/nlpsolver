#!/usr/bin/env python3
"""Position effect: does ballast at the start vs right before the question
hurt differently?  (Plan 02 §6.)

Uses the generator manifest (insertion slot per ballast sentence: 0 = very
start, n = immediately before the question) and the per-case results.
Reports accuracy conditioned on ballast placement and the placements of the
cases each model lost vs b0.  At low dose this is descriptive only -- few
failures, no significance claims.

Run:  python3 results/ballast-robustness/analysis/position_effect.py [-live]
      [-doses 2] [-models gpt,claude]
"""
import argparse
import common as C


def placements(entry):
  """Set of placement categories for one case's ballast: start/middle/preq."""
  n = entry["n_statements"]
  cats = set()
  for b in entry["ballast"]:
    if b["slot"] == 0:
      cats.add("start")
    elif b["slot"] == n:
      cats.add("preq")
    else:
      cats.add("middle")
  return cats


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("-live", action="store_true")
  ap.add_argument("-doses", default="2")
  ap.add_argument("-models", default="gpt,claude")
  args = ap.parse_args()
  source = "live" if args.live else "snapshot"
  doses = [int(s) for s in args.doses.split(",") if s.strip()]
  models = [m for m in args.models.split(",") if m]

  for d in doses:
    man = C.manifest(d)
    base = {m: C.load(0, m) for m in models}
    print(f"\n=== dose b{d} ===")
    for m in models:
      cc = C.load(d, m, source)
      if not cc:
        print(f"{m}: no data")
        continue
      print(f"\n{m} (n={len(cc)}):")
      for cat in ("start", "middle", "preq"):
        with_cat = [cid for cid in cc if cat in placements(man[cid])]
        without = [cid for cid in cc if cat not in placements(man[cid])]
        def acc(ids):
          return (100.0 * sum(C.is_correct(cc[i]) for i in ids) / len(ids)
                  if ids else float("nan"))
        print(f"  has {cat:6}: n={len(with_cat):3d} acc={acc(with_cat):5.1f}   "
              f"without: n={len(without):3d} acc={acc(without):5.1f}")
      lost = sorted(cid for cid in cc if cid in base[m]
                    and C.is_correct(base[m][cid]) and not C.is_correct(cc[cid]))
      if lost:
        print(f"  lost cases vs b0: ")
        for cid in lost:
          e = man[cid]
          spots = [(b["slot"], e["n_statements"]) for b in e["ballast"]]
          print(f"    case {cid}: slots {spots} -> {sorted(placements(e))}")
  print()


if __name__ == "__main__":
  main()
