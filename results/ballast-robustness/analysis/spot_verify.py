#!/usr/bin/env python3
"""Spot-verify a cause-map exemplar from its stored trace (plan 03 §2.4).

Replays the post-LLM pipeline (logconvert -> semnormalize -> gk) directly
from the stage-1/stage-2 JSON stored in the per-case snapshot -- zero LLM
calls, so it is free and exactly reproduces what the run's prover saw.

  -freeworld   causal test for the pipeline-world-shift bucket: after the
               replay, replace the question clauses' pinned world CONSTANT
               (lc_packages binds a stateless query to the latest world,
               which ballast event sentences keep advancing) with a fresh
               variable, run gk again, and report both answers.  If the
               freed run recovers the b0 answer, the world pinning IS the
               failure cause for this case.

Run:  python3 results/ballast-robustness/analysis/spot_verify.py
        -dose 8 -model gpt -case 1521 [-live] [-freeworld]
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


_WORLD = re.compile(r"^W\d+$")


def free_question_world(logic):
  """Replace pinned world constants in the question clauses ('@question'
  entries and the $defq carrier clauses) with a fresh variable, in place.
  Returns the list of substitutions made."""
  subs = []

  def is_question_clause(cl):
    if "@question" in cl:
      return True
    txt = json.dumps(cl.get("@logic", ""))
    return "$defq" in txt

  def walk(t, where):
    if isinstance(t, list):
      if len(t) >= 3 and t[0] == "$ctxt" and isinstance(t[2], str) \
         and _WORLD.match(t[2]):
        subs.append((where, t[2]))
        t[2] = "?:WQFREE"
      for x in t:
        walk(x, where)

  for cl in logic:
    if isinstance(cl, dict) and is_question_clause(cl):
      for key in ("@logic", "@question"):
        if key in cl:
          walk(cl[key], cl.get("@name", "?"))
  return subs


def replay(case, freeworld=False):
  """(answer, n_clauses, world_subs) from the stored stage-1/2 JSON."""
  from logconvert import rawlogic_convert
  import semnormalize
  import prover
  from procproofs import process_proof

  if not case.get("stage1") or not case.get("stage2"):
    return ("Error: stored trace has no stage-1/2 output (parse failed).",
            0, [])
  s1 = copy.deepcopy(case["stage1"])
  s2 = copy.deepcopy(case["stage2"])
  logic = rawlogic_convert(copy.deepcopy(s2), s1, fixes=[])
  if logic is None:
    return ("Error: rawlogic_convert returned None.", 0, [])
  logic = semnormalize.sem_normalize_clauses(logic)
  subs = free_question_world(logic) if freeworld else []
  proof_result = prover.call_prover(logic, s1_json=s1)
  answer = process_proof(proof_result, text=case["input_text"],
                         s1_json=s1, s2_json=s2, logic=logic, options=None)
  return (answer, len(logic), subs)


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("-dose", type=int, required=True)
  ap.add_argument("-model", required=True)
  ap.add_argument("-case", type=int, required=True)
  ap.add_argument("-live", action="store_true")
  ap.add_argument("-freeworld", action="store_true")
  args = ap.parse_args()

  source = "live" if args.live else "snapshot"
  cc = C.load(args.dose, args.model, source)
  case = cc.get(args.case)
  if case is None:
    sys.exit(f"case {args.case} not in b{args.dose}/{args.model} ({source})")
  b0 = C.load(0, args.model).get(args.case)

  print(f"case {args.case}  b{args.dose}/{args.model}   expected="
        f"{case.get('expected_answer')}")
  print(f"  stored answer : {case.get('answer')!r}  "
        f"(correct={case.get('correctness')})")
  if b0:
    print(f"  b0 answer     : {b0.get('answer')!r}  "
          f"(correct={b0.get('correctness')})")

  ans, n, _ = replay(case)
  print(f"  replayed      : {ans!r}   ({n} clauses, no LLM calls)")

  if args.freeworld:
    ans2, _n2, subs = replay(case, freeworld=True)
    print(f"  world-freed   : {ans2!r}   "
          f"(replaced {[w for _c, w in subs]} -> ?:WQFREE in "
          f"{sorted({c for c, _w in subs})})")


if __name__ == "__main__":
  main()
