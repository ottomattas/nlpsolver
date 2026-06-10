#!/usr/bin/env python3
"""Live status overview for llmpipe experiment runs.

Scans llmpipe/testresults/<testname>/<condition>/<llm>/case_*.json and prints
a model x condition matrix: cases done, accuracy, and pass/fail/err counts.

Usage (from anywhere):
    python3 tools/status.py              # defaults to the core_100 subset
    python3 tools/status.py core         # the full 1600-set
    python3 tools/status.py core_100_b8  # a ballast suite
"""
import os
import sys
import glob
import json
import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# condition dir -> short label; order = the A/B/C ladder (most -> least structured)
CONDITIONS = [("twostage", "A two-stage"),
              ("onestage-struct", "B one-struct"),
              ("onestage-direct", "C one-direct")]
MODELS = ["gpt", "claude", "gemini", "deepseek"]
TOTAL_EXPECTED = 100  # only used to flag "in progress"; accuracy uses actual done


def tally(testname, cond, model):
  d = os.path.join(_ROOT, "llmpipe", "testresults", testname, cond, model)
  if not os.path.isdir(d):
    return (0, 0, 0, 0)
  done = passed = failed = errored = 0
  for fp in glob.glob(os.path.join(d, "case_*.json")):
    try:
      data = json.load(open(fp))
    except Exception:
      continue
    done += 1
    if "error" in data:
      errored += 1
    elif data.get("correctness") is True:
      passed += 1
    else:
      failed += 1
  return (done, passed, failed, errored)


def fmt_cell(done, p, f, e, expected, w):
  """Render one cell with fixed-width fields so columns never drift.

  Layout:  <done><flag> <acc>% (<pass>/<fail>/<err>)
  where the numeric fields are right-justified to width `w` (derived from the
  run's expected case count), the flag is a single char ('*' = in progress).
  """
  if done == 0:
    return "-"
  acc = 100.0 * p / done
  flag = " " if done >= expected else "*"
  return f"{done:>{w}}{flag} {acc:5.1f}% ({p:>{w}}/{f:>{w}}/{e:>2})"


def main():
  testname = sys.argv[1] if len(sys.argv) > 1 else "core_100"
  expected = int(sys.argv[2]) if len(sys.argv) > 2 else TOTAL_EXPECTED
  now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  # Field width = digits needed for the largest possible count (>=3 for looks).
  w = max(3, len(str(expected)))
  # Cell width is fixed by the layout above; size a column to fit it + labels.
  cw = max(len(fmt_cell(expected, expected, 0, 0, expected, w)),
           max(len(lbl) for _, lbl in CONDITIONS))
  mw = max(len("model"), max(len(m) for m in MODELS), len("ALL"))

  print(f"\nnlpsolver run status — {testname}   ({now})\n")
  header = f"{'model':<{mw}}  " + "  ".join(f"{lbl:>{cw}}" for _, lbl in CONDITIONS)
  print(header)
  print("-" * len(header))

  totals = {c: [0, 0, 0, 0] for c, _ in CONDITIONS}
  for model in MODELS:
    cells = []
    for cond, _ in CONDITIONS:
      d, p, f, e = tally(testname, cond, model)
      cells.append(f"{fmt_cell(d, p, f, e, expected, w):>{cw}}")
      for i, v in enumerate((d, p, f, e)):
        totals[cond][i] += v
    print(f"{model:<{mw}}  " + "  ".join(cells))

  print("-" * len(header))
  # Per-condition column totals (accuracy over all cases done so far).
  tcells = []
  for cond, _ in CONDITIONS:
    d, p, f, e = totals[cond]
    tcells.append(f"{fmt_cell(d, p, f, e, expected * len(MODELS), w):>{cw}}")
  print(f"{'ALL':<{mw}}  " + "  ".join(tcells))
  grand = sum(totals[c][0] for c, _ in CONDITIONS)
  print(f"\ncells: <done><flag> <acc>% (pass/fail/err).  * = in progress (<{expected}).")
  print(f"overall case-runs done: {grand} / {expected * len(CONDITIONS) * len(MODELS)}\n")


if __name__ == "__main__":
  main()
