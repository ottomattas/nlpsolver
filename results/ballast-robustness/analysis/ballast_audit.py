#!/usr/bin/env python3
"""Ballast handling audit (plan 02 §6): across ALL ballasted runs, did the
LLM actually emit logic for the ballast sentences (it should -- they are
real statements), and did any parse MERGE ballast entities with original
ones (a clause whose argument vocabulary mixes both sides => coreference
leak / generator bug worth reporting)?

This is the spot_check clause classifier applied to the whole stored run
instead of 5 probe cases; no LLM calls are made.

Run:  python3 results/ballast-robustness/analysis/ballast_audit.py [-live]
      [-doses 2] [-models gpt,claude]
"""
import os
import sys
import argparse
import common as C

sys.path.insert(0, C.BALLAST_DIR)
sys.path.insert(0, os.path.join(C.REPO, "llmpipe"))
sys.path.insert(0, os.path.join(C.REPO, "llmpipe", "solver"))

from make_ballast import STOPWORDS, content_words, norm_ws, analyze
from spot_check import clause_words


def vocab(text_or_texts):
  if isinstance(text_or_texts, str):
    text_or_texts = [text_or_texts]
  out = set()
  for t in text_or_texts:
    out |= analyze(content_words(norm_ws(t)))["exp"]
  return out


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("-live", action="store_true")
  ap.add_argument("-doses", default="2")
  ap.add_argument("-models", default="gpt,claude")
  ap.add_argument("-verbose", action="store_true",
                  help="print every mixed clause")
  args = ap.parse_args()
  source = "live" if args.live else "snapshot"
  doses = [int(s) for s in args.doses.split(",") if s.strip()]
  models = [m for m in args.models.split(",") if m]

  # Need the ORIGINAL case texts for the original-side vocabulary.
  from runtests import load_tests
  base_texts = {t[0]: t[1] for t in
                load_tests(os.path.join(C.REPO, "llmpipe", "tests",
                                        "tests_core_100.py"))}

  for d in doses:
    man = C.manifest(d)
    print(f"\n=== dose b{d} ===")
    for m in models:
      cc = C.load(d, m, source)
      if not cc:
        print(f"{m}: no data")
        continue
      n_cases = 0
      no_ballast_clauses = []   # ballast present in input but no clauses for it
      mixed_cases = {}
      for cid, case in sorted(cc.items()):
        if cid not in man or "error" in case:
          continue
        n_cases += 1
        ov = vocab(base_texts[cid])
        bv = vocab([b["text"] for b in man[cid]["ballast"]])
        n_ball = n_mixed = 0
        for cl in case.get("clauses", []):
          if not isinstance(cl, dict):
            continue
          arg_w, pred_w = set(), set()
          clause_words(cl.get("@logic", cl.get("@question")), arg_w, pred_w)
          arg_w -= STOPWORDS
          hb, ho = arg_w & bv, arg_w & ov
          if hb and ho:
            n_mixed += 1
            if args.verbose:
              print(f"  MIXED {m} b{d} case {cid} {cl.get('@name')}: "
                    f"{sorted(hb)} x {sorted(ho)}  nl={cl.get('@nl')!r}")
          elif hb:
            n_ball += 1
        if n_ball == 0:
          no_ballast_clauses.append(cid)
        if n_mixed:
          mixed_cases[cid] = n_mixed
      print(f"{m}: {n_cases} cases | ballast unparsed (0 ballast-side "
            f"clauses): {len(no_ballast_clauses)} {no_ballast_clauses[:10]} | "
            f"cases with MIXED clauses: {len(mixed_cases)} "
            f"{dict(sorted(mixed_cases.items())[:10])}")
  print("\nMIXED = a clause whose argument vocabulary touches both ballast"
        "\nand original content words (coreference/merge leak candidate)."
        "\nRe-run with -verbose to list them; eyeball before judging.\n")


if __name__ == "__main__":
  main()
