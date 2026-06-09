#!/usr/bin/env python3
"""X2 - Decomposition vs. self-refinement.

The Gate-1 result showed two-stage's advantage comes from the separate second
CALL, not the ASU format.  But "second call" conflates two mechanisms:
  decomposition - the two calls do DIFFERENT subtasks (parse -> encode), as in A;
  iteration     - a second pass over the SAME subtask (encode -> revise).
Condition D (selfrefine) is the control: one-stage-direct (C) plus a self-revision
pass, NO decomposition.  Same call count as A (2), same no-ASU as C.

This script runs over the X2 pilot ids (the cases where A beats C) and reports,
per model: accuracy of A, C, D, and how many C-failures the refine pass RESCUED.
If D ~ A -> the lever is iteration; if D ~ C -> the lever is decomposition.

Reads A/C/D from the snapshot by default (snapshot selfrefine first), or pass
'live' to read the gitignored testresults tree.

Run:  python3 results/parsing-architecture/analysis/x2_selfrefine.py [live]
"""
import sys
import common as C

PILOT_IDS = [612, 1206, 1310, 234, 553, 605, 1365, 117, 248, 598]


def main():
  source = sys.argv[1] if len(sys.argv) > 1 else "snapshot"
  ids = set(PILOT_IDS)
  print(f"\nX2 - decomposition vs self-refinement ({source}; X2 pilot = {len(PILOT_IDS)} "
        f"cases where A>C)\n")
  print(f"{'model':9} {'A acc%':>7} {'C acc%':>7} {'D acc%':>7} "
        f"{'C->D rescued':>13} {'D->C broke':>11}")
  print("-" * 60)
  tot = {"A": 0, "C": 0, "D": 0, "resc": 0, "broke": 0, "n": 0}
  for model in C.MODELS:
    a = {i: v for i, v in C.load("A", model).items() if i in ids}
    c = {i: v for i, v in C.load("C", model).items() if i in ids}
    d = {i: v for i, v in C.load("D", model, source=source).items() if i in ids}
    common = sorted(set(a) & set(c) & set(d))
    if not common:
      print(f"{model:9} (no D data yet)")
      continue
    aA = sum(C.is_correct(a[i]) for i in common)
    cC = sum(C.is_correct(c[i]) for i in common)
    dD = sum(C.is_correct(d[i]) for i in common)
    resc = sum(1 for i in common if not C.is_correct(c[i]) and C.is_correct(d[i]))
    broke = sum(1 for i in common if C.is_correct(c[i]) and not C.is_correct(d[i]))
    n = len(common)
    tot["A"] += aA; tot["C"] += cC; tot["D"] += dD
    tot["resc"] += resc; tot["broke"] += broke; tot["n"] += n
    print(f"{model:9} {100.0*aA/n:7.1f} {100.0*cC/n:7.1f} {100.0*dD/n:7.1f} "
          f"{resc:13d} {broke:11d}")
  n = tot["n"] or 1
  print("-" * 60)
  print(f"{'ALL':9} {100.0*tot['A']/n:7.1f} {100.0*tot['C']/n:7.1f} "
        f"{100.0*tot['D']/n:7.1f} {tot['resc']:13d} {tot['broke']:11d}")
  gapAC = 100.0 * (tot["A"] - tot["C"]) / n
  gapDC = 100.0 * (tot["D"] - tot["C"]) / n
  recovered = (100.0 * gapDC / gapAC) if gapAC else 0.0
  print(f"\nA-C gap on these cases: {gapAC:.1f} pts;  D-C (self-refine) gain: "
        f"{gapDC:.1f} pts;\nself-refinement recovers {recovered:.0f}% of the "
        f"decomposition gap.")
  print("Low recovery => the two-stage advantage is DECOMPOSITION, not mere "
        "iteration.\n")


if __name__ == "__main__":
  main()
