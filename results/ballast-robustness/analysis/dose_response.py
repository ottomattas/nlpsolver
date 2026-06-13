#!/usr/bin/env python3
"""Dose-response: accuracy vs ballast dose per model (the headline table),
with E2-style failure decomposition and per-case flips vs the b0 baseline.

Failure buckets (pipeline order, mirrors plan-01 e2_failure_localisation):
  parse_fail   : no Stage-2 logic at all
  no_question  : logic produced but no question encoded
  convert_fail : logic produced but no clauses
  no_proof     : clauses produced but prover found nothing -> "Unknown"
                 (weak logic OR prover timeout -- disambiguate via -seconds)
  wrong_answer : confident but wrong answer
  error        : run raised an exception

Run:  python3 results/ballast-robustness/analysis/dose_response.py [-live]
      [-doses 2,4] [-models gpt,claude]
"""
import sys
import argparse
import common as C

BUCKETS = ["parse_fail", "no_question", "convert_fail", "no_proof",
           "wrong_answer", "error"]


def has_question(case):
  import json
  s2 = case.get("stage2")
  txt = json.dumps(s2) if s2 is not None else ""
  return ('"question"' in txt) or ('"ask"' in txt) or ('"@question"' in txt)


def bucket(case):
  if "error" in case:
    return "error"
  if not case.get("stage2"):
    return "parse_fail"
  if not has_question(case):
    return "no_question"
  if not case.get("clauses"):
    return "convert_fail"
  ans = str(case.get("answer", "")).strip().lower()
  if ans.startswith("unknown") or ans == "" or not case.get("proof"):
    return "no_proof"
  return "wrong_answer"


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("-live", action="store_true",
                  help="read llmpipe/testresults/ instead of the snapshot")
  ap.add_argument("-doses", default="2", help="ballast doses, e.g. 2,4,8")
  ap.add_argument("-models", default="gpt,claude")
  ap.add_argument("-tag", default=None,
                  help="condition-variant cell suffix to read for doses>0 "
                       "(e.g. slightcoarse, s2split_slightcoarse); b0 stays "
                       "the plain baseline. Omit for the two-stage baseline.")
  args = ap.parse_args()
  source = "live" if args.live else "snapshot"
  doses = [0] + [int(s) for s in args.doses.split(",") if s.strip()]
  models = [m for m in args.models.split(",") if m]

  cond = f"; condition={args.tag}" if args.tag else ""
  print("\nDose-response: accuracy (%) per model x ballast dose "
        f"({source} data; b0 = plan-01 Gate-1 twostage{cond})\n")
  hdr = f"{'model':9}" + "".join(f"{'b' + str(d):>9}" for d in doses)
  print(hdr)
  print("-" * len(hdr))
  data = {}
  for m in models:
    row = f"{m:9}"
    for d in doses:
      cc = C.load(d, m, source if d else "snapshot", tag=args.tag if d else None)
      data[(m, d)] = cc
      n = len(cc)
      if n == 0:
        row += f"{'--':>9}"
        continue
      acc = 100.0 * sum(C.is_correct(c) for c in cc.values()) / n
      row += f"{acc:8.1f}{'*' if n < 100 else ' '}"
    print(row)
  print("  (* = partial cell, run still in progress)\n")

  print("Failure decomposition (incorrect runs only):\n")
  hdr2 = (f"{'model':9} {'dose':>5} {'n':>4} {'fails':>6} "
          + " ".join(f"{b:>12}" for b in BUCKETS))
  print(hdr2)
  print("-" * len(hdr2))
  for m in models:
    for d in doses:
      cc = data[(m, d)]
      if not cc:
        continue
      counts = {b: 0 for b in BUCKETS}
      for c in cc.values():
        if not C.is_correct(c):
          counts[bucket(c)] += 1
      print(f"{m:9} {'b' + str(d):>5} {len(cc):4d} {sum(counts.values()):6d} "
            + " ".join(f"{counts[b]:>12}" for b in BUCKETS))
    print()

  print("Per-case flips vs b0 (same case, same model):\n")
  for m in models:
    base = data.get((m, 0), {})
    for d in doses[1:]:
      cc = data[(m, d)]
      both = [cid for cid in cc if cid in base]
      lost = sorted(cid for cid in both
                    if C.is_correct(base[cid]) and not C.is_correct(cc[cid]))
      gained = sorted(cid for cid in both
                      if not C.is_correct(base[cid]) and C.is_correct(cc[cid]))
      print(f"{m} b{d}: lost {len(lost)} {lost}  | gained {len(gained)} {gained}")
  print()


if __name__ == "__main__":
  main()
