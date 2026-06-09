#!/usr/bin/env python3
"""X3 - Defeasible / nonmonotonic focus.

Hypothesis: the two-stage advantage CONCENTRATES on defeasible reasoning -
generics with exceptions ("birds fly", "penguins do not fly") - because that is
where gk's nonmonotonic blocker machinery is essential and where a one-shot
first-order encoding has no sound form.  An LLM that writes logic in a single
pass tends to emit a plain universal that the exception then contradicts; the
two-stage parse isolates the default/exception structure first.

Compares Condition A (two-stage) vs C (one-stage direct) on the 10-case
defeasible set (tests_core_defeasible.py), per model, and prints the A-C gap.
Contrast this gap with the ~7pt overall A-C gap on core_100: a markedly larger
gap here = the advantage is defeasible-driven.

Reads from the core_defeasible snapshot by default; pass 'live' for testresults.

Run:  python3 results/parsing-architecture/analysis/x3_defeasible.py [live]
"""
import sys
import common as C


def main():
  source = sys.argv[1] if len(sys.argv) > 1 else "snapshot"
  print(f"\nX3 - defeasible reasoning: two-stage (A) vs one-stage-direct (C) "
        f"({source})\n")
  print(f"{'model':9} {'n':>3} {'A acc%':>7} {'C acc%':>7} {'gap':>6} "
        f"{'A>C ids (C wrong, A right)':>30}")
  print("-" * 72)
  tA = tC = tn = 0
  for model in C.MODELS:
    a = C.load("A", model, testname="core_defeasible", source=source)
    c = C.load("C", model, testname="core_defeasible", source=source)
    ids = sorted(set(a) & set(c))
    if not ids:
      print(f"{model:9} (no data yet)")
      continue
    aA = sum(C.is_correct(a[i]) for i in ids)
    cC = sum(C.is_correct(c[i]) for i in ids)
    awins = [i for i in ids if C.is_correct(a[i]) and not C.is_correct(c[i])]
    n = len(ids)
    tA += aA; tC += cC; tn += n
    print(f"{model:9} {n:3d} {100.0*aA/n:7.1f} {100.0*cC/n:7.1f} "
          f"{100.0*(aA-cC)/n:6.1f}  {awins}")
  n = tn or 1
  print("-" * 72)
  gap = 100.0 * (tA - tC) / n
  print(f"{'ALL':9} {n:3d} {100.0*tA/n:7.1f} {100.0*tC/n:7.1f} {gap:6.1f}")
  print(f"\nDefeasible A-C gap: {gap:.1f} pts vs ~7.3 pts overall on core_100.")
  print("A markedly larger gap here => the two-stage advantage is defeasible-driven, "
        "the part\nof reasoning where the symbolic prover (gk) is doing work an LLM "
        "alone cannot soundly encode.\n")


if __name__ == "__main__":
  main()
