#!/usr/bin/env python3
"""E2 - Failure-localisation taxonomy.

Attributes each INCORRECT run to the pipeline stage where it broke, using the
stored trace (stage2 / clauses / proof / answer).  Buckets, in pipeline order:

  parse_fail    : no Stage-2 logic produced at all (the LLM parse failed);
  no_question   : logic produced but the question was not encoded as a question;
  convert_fail  : logic produced but logconvert emitted no clauses;
  no_proof      : clauses produced but the prover found nothing -> "Unknown"
                  (a logical-fidelity gap: the encoding was too weak to prove);
  wrong_answer  : a confident answer was produced but it is wrong (a semantic
                  encoding error, not a gap);
  error         : the run raised an exception.

This turns "one-stage is worse" into "one-stage breaks HERE", per condition.

Run:  python3 results/parsing-architecture/analysis/e2_failure_localisation.py
"""
import common as C

BUCKETS = ["parse_fail", "no_question", "convert_fail", "no_proof", "wrong_answer", "error"]


def bucket(case):
  if "error" in case:
    return "error"
  s2 = case.get("stage2")
  if not s2:
    return "parse_fail"
  if not C.has_question(case):
    return "no_question"
  if not case.get("clauses"):
    return "convert_fail"
  ans = str(case.get("answer", "")).strip().lower()
  if ans.startswith("unknown") or ans == "" or not case.get("proof"):
    return "no_proof"
  return "wrong_answer"


def main():
  print("\nE2 - failure localisation (core_100 snapshot; only INCORRECT runs)\n")
  hdr = f"{'model':9} {'cond':10} {'fails':>5} " + " ".join(f"{b:>12}" for b in BUCKETS)
  print(hdr)
  print("-" * len(hdr))
  totals = {k: {b: 0 for b in BUCKETS} for k in ("A", "B", "C")}
  for model in C.MODELS:
    for k in ("A", "B", "C"):
      cc = C.load(k, model)
      counts = {b: 0 for b in BUCKETS}
      for c in cc.values():
        if not C.is_correct(c):
          counts[bucket(c)] += 1
      fails = sum(counts.values())
      for b in BUCKETS:
        totals[k][b] += counts[b]
      print(f"{model:9} {C.COND_LABEL[k]:10} {fails:5d} "
            + " ".join(f"{counts[b]:>12}" for b in BUCKETS))
    print()
  print("condition totals over all 4 models:")
  for k in ("A", "B", "C"):
    fails = sum(totals[k].values())
    print(f"{'ALL':9} {C.COND_LABEL[k]:10} {fails:5d} "
          + " ".join(f"{totals[k][b]:>12}" for b in BUCKETS))
  print("\nReading: where the one-stage bars (B/C) grow vs A localises the cost of "
        "collapsing the parse.\n")


if __name__ == "__main__":
  main()
