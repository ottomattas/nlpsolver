#!/usr/bin/env python3
"""Per-case win/loss analysis for the parsing-architecture experiments.

Compares Condition A (two-stage) against B (one-stage struct) and C (one-stage
direct) at the case level, per model, and surfaces the cases where the second
stage actually matters (A right, one-stage wrong) — the RQ3 "which cases" view.

A case whose run errored is counted as wrong.

Usage:
    python3 tools/winloss.py            # core_100 subset
    python3 tools/winloss.py core       # full 1600-set
"""
import os
import sys
import glob
import json

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONDS = {"A": "twostage", "B": "onestage-struct", "C": "onestage-direct"}
MODELS = ["gpt", "claude", "gemini", "deepseek"]


def load(testname, cond, model):
  """case_id -> bool correctness (errored/missing answer => False)."""
  d = os.path.join(_ROOT, "llmpipe", "testresults", testname, CONDS[cond], model)
  out = {}
  for fp in glob.glob(os.path.join(d, "case_*.json")):
    try:
      dd = json.load(open(fp))
    except Exception:
      continue
    cid = dd.get("case_id")
    out[cid] = (("error" not in dd) and bool(dd.get("correctness")))
  return out


def load_text(testname, model):
  """case_id -> input_text (from the two-stage files; any condition would do)."""
  d = os.path.join(_ROOT, "llmpipe", "testresults", testname, CONDS["A"], model)
  out = {}
  for fp in glob.glob(os.path.join(d, "case_*.json")):
    try:
      dd = json.load(open(fp))
    except Exception:
      continue
    out[dd.get("case_id")] = dd.get("input_text", "")
  return out


def winloss(a, x):
  ids = sorted(set(a) & set(x))
  aw = [i for i in ids if a[i] and not x[i]]      # A right, one-stage wrong
  xw = [i for i in ids if x[i] and not a[i]]      # one-stage right, A wrong
  both = [i for i in ids if a[i] and x[i]]
  neither = [i for i in ids if not a[i] and not x[i]]
  return ids, aw, xw, both, neither


def main():
  testname = sys.argv[1] if len(sys.argv) > 1 else "core_100"
  print(f"\nwin/loss vs two-stage (A) — {testname}\n")

  print(f"{'model':9} {'comparison':14} {'n':>4} {'A>1stage':>9} {'1stage>A':>9} "
        f"{'both':>5} {'neither':>8}")
  print("-" * 64)
  twostage_only = {}     # model -> set of case_ids A solves but BOTH B and C miss
  for model in MODELS:
    a = load(testname, "A", model)
    b = load(testname, "B", model)
    c = load(testname, "C", model)
    for label, x in (("A vs B (struct)", b), ("A vs C (direct)", c)):
      ids, aw, xw, both, neither = winloss(a, x)
      print(f"{model:9} {label:14} {len(ids):4d} {len(aw):9d} {len(xw):9d} "
            f"{len(both):5d} {len(neither):8d}")
    common = set(a) & set(b) & set(c)
    twostage_only[model] = {i for i in common if a[i] and not b[i] and not c[i]}
    print()

  # Cases the second stage rescues, per model, and across ALL models.
  print("two-stage-only wins (A correct, BOTH one-stage variants wrong):")
  for model in MODELS:
    print(f"  {model:9} {len(twostage_only[model]):3d} cases  "
          f"{sorted(twostage_only[model])}")
  robust = set.intersection(*twostage_only.values()) if twostage_only else set()
  print(f"\ncases needing two-stage for EVERY model: {len(robust)} -> {sorted(robust)}")
  if robust:
    texts = load_text(testname, "gpt")
    print("\nthese 'genuinely-need-two-stage' cases:")
    for cid in sorted(robust):
      print(f"  [{cid:4d}] {texts.get(cid, '')[:90]}")
  print()


if __name__ == "__main__":
  main()
