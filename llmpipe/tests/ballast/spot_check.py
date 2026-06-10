#!/usr/bin/env python3

# Clause-set spot checks for the ballast suites (plan 02 §4.2: Tanel's
# "pistelisi kontrolle genereeritud disjunktihulkade peal").
#
# For each requested case, runs the full pipeline on the ORIGINAL and the
# BALLASTED input (LLM cache stays ON — rerunning is free) and verifies on
# the produced clause sets that the ballast stayed inert end-to-end:
#
#   (a) no clause mixes ballast vocabulary with original vocabulary --
#       every clause must classify as ballast-side, original-side or
#       neutral machinery.  A MIXED clause means either a generator bug or
#       an LLM coreference/merge leak;
#   (b) no generated/injected axiom (soft-synonym, exclusion, bridge, ...)
#       connects ballast vocabulary to original vocabulary -- generated
#       clauses are subject to the same MIXED test;
#   (c) the answer of the ballasted run still matches the expected answer
#       (and the original run's answer is reported alongside).
#
# Vocabulary sides come from the same machinery the generator used
# (make_ballast.analyze: raw words + morphological variants + canonicals),
# so the two sides are disjoint by construction.  Clause words that appear
# on neither side (pipeline scaffolding like isa/has property, skolems,
# worlds, LLM paraphrases) are 'neutral' and reported but not fatal.
#
# Usage (from the llmpipe/ directory):
#   python3 tests/ballast/spot_check.py -dose 2 -ids 2,6,22,28,470,134 -llm gemini

import os
import sys
import re
import json
import time
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
LLMPIPE = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, LLMPIPE)
sys.path.insert(0, os.path.join(LLMPIPE, "solver"))

from make_ballast import STOPWORDS, content_words, norm_ws, analyze
from runtests import load_tests, _import_matcher

import solve as solve_mod
from solve import english_to_answer


def _word_tokens(s, out):
  if s.startswith("#:"):
    s = s[2:]
  if s.startswith("?:") or s.startswith("$") or s.startswith("@"):
    return
  s = s.lstrip("-")             # negated predicate names
  for t in re.findall(r"[a-z']+", s.lower()):
    t = t.strip("'")
    if t.endswith("'s"):
      t = t[:-2]
    if t:
      out.add(t)


def clause_words(node, args, preds):
  """Collect lowercase word tokens from a clause tree, separating
  PREDICATE-position words (heads of atoms/connectives — pipeline
  scaffolding like isa / has property / have) from ARGUMENT-position words
  (entity, class and property constants — the actual case vocabulary).
  Variables (?:), entity-UNA prefixes (#:) and $/@ machinery are skipped."""
  if not isinstance(node, list) or not node:
    return
  head, rest = node[0], node[1:]
  if isinstance(head, str):
    _word_tokens(head, preds)
  else:
    clause_words(head, args, preds)
  for x in rest:
    if isinstance(x, str):
      _word_tokens(x, args)
    else:
      clause_words(x, args, preds)


def vocab_side(words_set):
  """Expanded comparison set (variants + canonicals) for a bag of words."""
  return analyze(words_set)["exp"]


def run_case(text):
  collect = {}
  t0 = time.time()
  ans = english_to_answer(text, options={}, collect=collect)
  return ans, collect, time.time() - t0


def check_case(cid, orig_text, ball_text, expected, ballast_texts, matcher):
  orig_ans, oc, ot = run_case(orig_text)
  ball_ans, bc, bt = run_case(ball_text)

  orig_vocab = vocab_side(content_words(norm_ws(orig_text)))
  ball_vocab = set()
  for b in ballast_texts:
    ball_vocab |= vocab_side(content_words(b))

  sides = {"original": 0, "ballast": 0, "neutral": 0}
  mixed = []
  scaffold_by_side = {"original": set(), "ballast": set()}
  for c in bc.get("clauses", []):
    if not isinstance(c, dict):
      continue
    body = c.get("@logic", c.get("@question"))
    args, preds = set(), set()
    clause_words(body, args, preds)
    args -= STOPWORDS
    hits_b = args & ball_vocab
    hits_o = args & orig_vocab
    if hits_b and hits_o:
      mixed.append((c.get("@name"), c.get("@nl"), sorted(hits_b), sorted(hits_o)))
    elif hits_b:
      sides["ballast"] += 1
      scaffold_by_side["ballast"] |= preds | (args - ball_vocab)
    elif hits_o:
      sides["original"] += 1
      scaffold_by_side["original"] |= preds | (args - orig_vocab)
    else:
      sides["neutral"] += 1

  shared_scaffold = scaffold_by_side["original"] & scaffold_by_side["ballast"]

  def verdict(ans):
    try:
      return bool(matcher(expected, ans, orig_text))
    except Exception:
      return None

  ok_orig, ok_ball = verdict(orig_ans), verdict(ball_ans)
  usage = bc.get("llm_usage", [])
  tok_in = sum(u["input_tokens"] for u in usage)
  tok_out = sum(u["output_tokens"] for u in usage)

  print(f"\n=== case {cid} ===")
  print(f"  original : answer={str(orig_ans).splitlines()[0]!r:40s} "
        f"match={ok_orig} ({ot:.1f}s)")
  print(f"  ballasted: answer={str(ball_ans).splitlines()[0]!r:40s} "
        f"match={ok_ball} ({bt:.1f}s)")
  print(f"  expected : {expected!r}")
  print(f"  clauses  : original={sides['original']} ballast={sides['ballast']} "
        f"neutral={sides['neutral']} MIXED={len(mixed)}")
  if shared_scaffold:
    print(f"  shared scaffold words (both sides, non-fatal): {sorted(shared_scaffold)}")
  print(f"  ballasted-run tokens: in={tok_in} out={tok_out} "
        f"(api calls={len(usage)}; 0 = served from local LLM cache)")
  for (name, nl, hb, ho) in mixed:
    print(f"  MIXED clause {name}: {nl!r}")
    print(f"        ballast-side words {hb}  original-side words {ho}")

  passed = (not mixed) and ok_ball is True
  print(f"  -> {'PASS' if passed else 'FAIL'}")
  return passed, tok_in, tok_out


def main():
  ap = argparse.ArgumentParser(description="Ballast clause-set spot checks.")
  ap.add_argument("-dose", type=int, required=True)
  ap.add_argument("-ids", required=True, help="Comma-separated case ids")
  ap.add_argument("-llm", default="gemini")
  ap.add_argument("-base", default="tests/tests_core_100.py")
  ap.add_argument("-maxtokens", type=int, default=0,
                  help="Per-call LLM output budget (0 = llmcall default of "
                       "8000; heavy doses need more, see runtests -maxtokens)")
  args = ap.parse_args()

  solve_mod.llm = args.llm
  if args.maxtokens:
    solve_mod.max_tokens = args.maxtokens
  matcher = _import_matcher()

  base_path = os.path.join(LLMPIPE, args.base)
  stem = os.path.splitext(os.path.basename(base_path))[0]
  ball_path = os.path.join(HERE, f"{stem}_b{args.dose}.py")
  manifest_path = os.path.join(HERE, f"{stem}_b{args.dose}.manifest.json")

  base = {t[0]: t for t in load_tests(base_path)}
  ball = {t[0]: t for t in load_tests(ball_path)}
  with open(manifest_path) as f:
    manifest = {e["case_id"]: e for e in json.load(f)["cases"]}

  ids = [int(s) for s in args.ids.split(",") if s.strip()]
  results = []
  tot_in = tot_out = 0
  for cid in ids:
    _, orig_text, expected = base[cid]
    _, ball_text, _ = ball[cid]
    ballast_texts = [b["text"] for b in manifest[cid]["ballast"]]
    ok, ti, to = check_case(cid, norm_ws(orig_text), ball_text, expected,
                            ballast_texts, matcher)
    results.append((cid, ok))
    tot_in += ti
    tot_out += to

  print("\n=== summary ===")
  for cid, ok in results:
    print(f"  case {cid}: {'PASS' if ok else 'FAIL'}")
  print(f"  total new tokens this check: in={tot_in} out={tot_out}")
  if not all(ok for _, ok in results):
    sys.exit(1)
  print("ALL SPOT CHECKS PASSED")


if __name__ == "__main__":
  main()


# =========== the end ==========
