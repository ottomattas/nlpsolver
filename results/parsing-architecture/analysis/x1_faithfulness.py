#!/usr/bin/env python3
"""X1 - Parse faithfulness / logical-form agreement.

Measures logical-form QUALITY directly, not just end-to-end answer accuracy.
For each condition (A/B/C) and model it reports, over the committed core_100
snapshot:
  - coverage : mean Stage-2 sentence-packages vs. mean input sentences, and the
               share of cases that drop a sentence relative to two-stage (A);
  - question : share of parses that actually encode the question;
  - depth    : mean #clauses produced (logic richness proxy);
  - unknown  : share of runs that yield no proof / "Unknown" (a faithfulness
               failure distinct from a confidently-wrong answer).
It then contrasts A vs C at the logic level: answer-agreement rate, and on the
disagreements, how often A is right vs C is right.

Run:  python3 results/parsing-architecture/analysis/x1_faithfulness.py
"""
import common as C


def coverage_drop(a, x):
  """Share of shared cases where x has FEWER stage-2 packages than A (dropped a
  sentence/clause relative to two-stage)."""
  ids = set(a) & set(x)
  drop = [i for i in ids if C.stage2_packages(x[i]) < C.stage2_packages(a[i])]
  return len(drop), len(ids)


def main():
  print("\nX1 - parse faithfulness / logical-form quality (core_100 snapshot)\n")
  print(f"{'model':9} {'cond':10} {'cover(pkg/sent)':>16} {'has_Q%':>7} "
        f"{'clauses':>8} {'unknown%':>9} {'acc%':>6}")
  print("-" * 70)
  for model in C.MODELS:
    cases = {k: C.load(k, model) for k in ("A", "B", "C")}
    for k in ("A", "B", "C"):
      cc = cases[k]
      n = len(cc) or 1
      pkg = sum(C.stage2_packages(c) for c in cc.values()) / n
      sent = sum(C.n_sentences(c.get("input_text", "")) for c in cc.values()) / n
      hasq = 100.0 * sum(C.has_question(c) for c in cc.values()) / n
      clauses = sum(len(c.get("clauses", [])) for c in cc.values()) / n
      unknown = 100.0 * sum(1 for c in cc.values()
                            if str(c.get("answer", "")).strip().lower().startswith("unknown")) / n
      acc = 100.0 * sum(C.is_correct(c) for c in cc.values()) / n
      print(f"{model:9} {C.COND_LABEL[k]:10} {pkg:6.2f}/{sent:<6.2f}{'':3} "
            f"{hasq:6.1f} {clauses:8.2f} {unknown:8.1f} {acc:6.1f}")
    print()

  # A-vs-C logical-form divergence: where the two logics yield different answers.
  print("A vs C - logical-form divergence (answers from each condition's logic):")
  print(f"{'model':9} {'n':>4} {'agree%':>7} {'disagree':>9} "
        f"{'A-right':>8} {'C-right':>8} {'both-wrong':>11}")
  print("-" * 62)
  for model in C.MODELS:
    a = C.load("A", model)
    c = C.load("C", model)
    ids = sorted(set(a) & set(c))
    agree = dis = aR = cR = bothW = 0
    for i in ids:
      sa = str(a[i].get("answer", "")).strip().lower()
      sc = str(c[i].get("answer", "")).strip().lower()
      if sa == sc:
        agree += 1
        continue
      dis += 1
      ac, cc_ = C.is_correct(a[i]), C.is_correct(c[i])
      if ac and not cc_: aR += 1
      elif cc_ and not ac: cR += 1
      elif not ac and not cc_: bothW += 1
    n = len(ids) or 1
    print(f"{model:9} {len(ids):4d} {100.0*agree/n:7.1f} {dis:9d} "
          f"{aR:8d} {cR:8d} {bothW:11d}")
  print("\nReading: high coverage + has_Q + clause depth and low unknown% = a more "
        "faithful logical form.\nWhere A and C disagree, 'A-right' >> 'C-right' "
        "means the two-stage logic, not just its answer, is the better one.\n")


if __name__ == "__main__":
  main()
