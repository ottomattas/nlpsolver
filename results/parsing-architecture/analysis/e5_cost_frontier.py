#!/usr/bin/env python3
"""E5 - Accuracy-per-cost frontier.

Plots (as a table) accuracy against the cost of each parser architecture, using
two cost axes that the stored data supports without new runs:

  calls/case      : LLM parse requests per case = base calls (+ logged retries);
  input-tok/case  : system-prompt input tokens per case (chars/4, measured).

The non-obvious result: two-stage (A) splits its prompt into a smaller Stage-1
and Stage-2 call, so its TOTAL input-token cost (~56K) is about the SAME as a
single one-stage call (~56K) - the extra accuracy costs an extra REQUEST and the
extra output tokens, not extra input tokens.  Output tokens are not logged, so
this is an input-token + request-count frontier (a lower bound on one-stage's
relative efficiency, since one-stage also emits the whole logic in one go).

Run:  python3 results/parsing-architecture/analysis/e5_cost_frontier.py
"""
import common as C


def main():
  print("\nE5 - accuracy per cost (core_100 snapshot)\n")
  print(f"{'model':9} {'cond':10} {'acc%':>6} {'calls/case':>11} "
        f"{'in-tok/case':>12} {'acc/call':>9} {'acc/100Ktok':>12}")
  print("-" * 74)
  agg = {k: {"acc": 0, "calls": 0, "n": 0} for k in ("A", "B", "C")}
  for model in C.MODELS:
    for k in ("A", "B", "C"):
      cc = C.load(k, model)
      n = len(cc) or 1
      acc = 100.0 * sum(C.is_correct(c) for c in cc.values()) / n
      calls = sum(C.llm_calls(k, c) for c in cc.values()) / n
      intok = C.COND_INPUT_TOK[k]            # fixed per condition (sysprompt)
      agg[k]["acc"] += sum(C.is_correct(c) for c in cc.values())
      agg[k]["calls"] += sum(C.llm_calls(k, c) for c in cc.values())
      agg[k]["n"] += len(cc)
      print(f"{model:9} {C.COND_LABEL[k]:10} {acc:6.1f} {calls:11.2f} "
            f"{intok:12d} {acc/max(calls,1e-9):9.2f} "
            f"{acc/(intok/1e5):12.2f}")
    print()
  print("aggregate over 400 case-runs:")
  for k in ("A", "B", "C"):
    n = agg[k]["n"] or 1
    acc = 100.0 * agg[k]["acc"] / n
    calls = agg[k]["calls"] / n
    intok = C.COND_INPUT_TOK[k]
    print(f"{'ALL':9} {C.COND_LABEL[k]:10} {acc:6.1f} {calls:11.2f} "
          f"{intok:12d} {acc/max(calls,1e-9):9.2f} {acc/(intok/1e5):12.2f}")
  print("\nReading: A buys its accuracy with ~2 requests/case at roughly the same "
        "input-token\nbudget as a single one-stage call - cheap on tokens, "
        "costlier only in request count.\n")


if __name__ == "__main__":
  main()
