#!/usr/bin/env python3
"""Proposal 1 (plan 04 follow-up): is the high-dose `no_proof` mass a prover
SEARCH/TIME limit, or genuine PARSE loss?

The study's headline claim is that ballast degradation enters only through
the neural parse, with the symbolic half indifferent at a fixed prover
budget (results.md §0, §3).  That budget check was only ever done at b2
(§3, a 10s recheck).  By b16/b32 the clause sets reach 270-300+ and the gk
datarec bug shows the prover is stressed at scale (§13.2, §14.2).  This
script tests, at zero LLM cost, whether MORE prover time recovers any
failing answer.

For every `no_proof` failure (stored answer "Unknown.", expected something
else, clauses present) it first triages the case so the budget sweep is
spent only on the cases the hypothesis is actually about:

  clause-loss   original-sentence clauses are missing vs the b0 run -- the
                parse dropped what the proof needed; more time cannot help.
  world-shift   freeing the question world (spot_verify) recovers the b0
                answer -- a convert-layer binding cause, not a time limit.
  candidate     clauses look sufficient (no loss, world not the cause): the
                genuine "did the prover just run out of search?" case.

Only `candidate` cases get the budget sweep (gk replayed UNCHANGED from the
stored clauses, same serialisation the live run used -- spot_verify.gk_replay
-- at each -budgets value).  A flip to the expected answer at a larger
budget is search-limit evidence; no flips means the failure is genuinely in
the parse/clauses, and the headline claim survives at scale.

Run:  python3 prover_budget.py [-doses 16,32] [-models gpt,claude,gemini,deepseek]
        [-budgets 15,30] [-verbose] [-live]
No LLM calls.  gk runs locally; a non-solving case consumes its full budget,
so keep the candidate set (printed first) in mind when picking -budgets.
"""
import sys
import argparse
import os
import common as C
import cause_map as CM
import stage1_coverage as S1
import spot_verify as SV

sys.path.insert(0, os.path.join(C.REPO, "llmpipe"))
sys.path.insert(0, os.path.join(C.REPO, "llmpipe", "solver"))
import globals as G  # noqa: E402


def _matcher():
  """The pipeline's own answer comparator (lenient on polarity strength,
  list-valued expecteds, etc.) so a flip is judged exactly as a live run."""
  import test as _t
  return _t._result_matches


def graded_correct(match, expected, answer, text):
  if answer is None or answer == "Unknown.":
    return False
  try:
    return bool(match(expected, answer, text, single_stage=False))
  except Exception:
    return False


def set_budget(seconds, cli):
  """cli=True -> exactly `seconds`; cli=False -> live auto-estimation with
  `seconds` as the floor (reproduces what the collected run's prover saw)."""
  G.options["prover_seconds"] = seconds
  G.options["prover_seconds_cli"] = cli


def is_no_proof_fail(case):
  ans = str(case.get("answer", ""))
  return (not C.is_correct(case) and ans == "Unknown."
          and str(case.get("expected_answer", "")) not in ("", "Unknown.")
          and bool(case.get("clauses")))


def triage(case, b0_case, man_entry):
  """('clause-loss'|'world-shift'|'candidate', detail)."""
  orig_tok = {CM.nl_tokens(t) for t, s in S1.input_sentences(case, man_entry)
              if s in ("orig", "question")}
  if b0_case:
    now = CM.orig_clause_set(case, orig_tok)
    was = CM.orig_clause_set(b0_case, orig_tok)
    lost = [k for k in was if k not in now]
    if lost:
      return "clause-loss", f"{len(lost)} orig clause(s) missing vs b0"
  # world-shift: free the question world at the live budget
  set_budget(2, False)
  _plain, freed, transient, recovers, _pinned = \
      CM.freeworld_intervention(case, b0_case)
  if transient:
    return "non-reproducing", "stored fail not reproduced at 2s"
  if recovers:
    return "world-shift", f"freed world -> {freed!r}"
  return "candidate", "clauses sufficient, world not the cause"


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("-doses", default="16,32")
  ap.add_argument("-models", default="gpt,claude,gemini,deepseek")
  ap.add_argument("-budgets", default="15,30",
                  help="extra prover-second budgets to try on candidates")
  ap.add_argument("-live", action="store_true")
  ap.add_argument("-verbose", action="store_true")
  args = ap.parse_args()
  source = "live" if args.live else "snapshot"
  doses = [int(s) for s in args.doses.split(",") if s.strip()]
  models = [x for x in args.models.split(",") if x]
  budgets = [int(s) for s in args.budgets.split(",") if s.strip()]
  match = _matcher()

  totals = {"no_proof": 0, "clause-loss": 0, "world-shift": 0,
            "non-reproducing": 0, "candidate": 0, "flipped": 0}
  flips = []

  for d in doses:
    for m in models:
      cc = C.load(d, m, source)
      if not cc:
        continue
      man, rev = C.resolve_manifest(d, cc)
      if rev is not None:
        excl = C.exclusions(d)
        cc = {cid: c for cid, c in cc.items() if cid not in excl}
      b0 = C.load(0, m)
      nps = {cid: c for cid, c in cc.items()
             if cid in man and is_no_proof_fail(c)}
      print(f"\n=== b{d} {m}: {len(nps)} no_proof failures "
            f"(suite {rev or 'worktree'}) ===")
      for cid, case in sorted(nps.items()):
        totals["no_proof"] += 1
        kind, detail = triage(case, b0.get(cid), man[cid])
        totals[kind] = totals.get(kind, 0) + 1
        line = f"  {cid:4d}  {kind:15s} {detail}"
        if kind == "candidate":
          exp = case.get("expected_answer")
          text = case.get("input_text")
          sweep = []
          flipped_to = None
          for b in budgets:
            set_budget(b, True)
            ans = str(SV.gk_replay(case))
            sweep.append(f"{b}s={ans!r}")
            if graded_correct(match, exp, ans, text):
              flipped_to = (b, ans)
              break
          line += "  ->  " + " ".join(sweep)
          if flipped_to:
            totals["flipped"] += 1
            flips.append((m, d, cid, flipped_to[0], flipped_to[1]))
            line += f"  *** FLIP @ {flipped_to[0]}s -> {flipped_to[1]!r} (exp {exp!r})"
        if args.verbose or kind == "candidate":
          print(line)

  print("\n\n==== Proposal 1 summary: search-limit vs parse-loss ====")
  print(f"  no_proof failures analysed : {totals['no_proof']}")
  print(f"    clause-loss (parse)      : {totals['clause-loss']}")
  print(f"    world-shift (convert)    : {totals['world-shift']}")
  print(f"    non-reproducing          : {totals['non-reproducing']}")
  print(f"    candidates (sufficient)  : {totals['candidate']}")
  print(f"    of which FLIP w/ time    : {totals['flipped']}  "
        f"budgets={budgets}s")
  if flips:
    print("  flips:")
    for m, d, cid, b, ans in flips:
      print(f"    b{d} {m} case {cid}: solved at {b}s -> {ans!r}")
  else:
    print("  -> no candidate flipped: the high-dose no_proof mass is NOT a "
          "prover time limit; it is in the clauses (parse/convert).")


if __name__ == "__main__":
  main()
