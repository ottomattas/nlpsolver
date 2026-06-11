#!/usr/bin/env python3
"""The failure cause map (plan 03 §2.3): bucket every failing run of a
dose x model cell by WHERE the chain broke, using the stage-1 coverage
and stage-2 fidelity analyzers plus a clause-level diff against the b0
baseline run of the same case+model.

Buckets (primary cause, one per failing run):

  gk-error            prover-side resource error (datarec allocator etc.);
  stage2-malformed    LLM emitted logic gk/convert rejects (null at formula
                      level, several questions, missing/duplicate units);
  stage1-omission     input sentence absent from the stage-1 output;
  stage1-capture      ballast/original entity merge in stage 1;
  stage1-id-break     one referent fractured into several entity ids;
  stage1-merge        two referents collapsed into one entity id (the
                      spurious-proof channel behind wrong answers);
  stage2-loss         stage-1 unit lost on the way into stage-2 logic;
  pipeline-world-shift
                      stage outputs equivalent to b0, but the question
                      clause's world binding moved (free variable pinned
                      to a constant, or re-pinned to a later world):
                      ballast event sentences advance the world chain and
                      lc_packages binds a stateless query to the LATEST
                      world -- a pipeline-level cause, not an LLM one;
  stage1-distortion   original sentence's stage-1 units differ from b0
                      (entity/action/adjective loss, type flip, unit drop)
                      and the difference propagates to the clauses;
  stage2-distortion   stage-1 equivalent to b0 but the stage-2 logic of an
                      original sentence changed, and so did its clauses;
  convert/pipeline    stage 1 and stage 2 both equivalent to b0, yet the
                      clause set differs -- logconvert/injector territory;
  unexplained         no detector fired; needs eyes.

The same flags are counted over the PASSING runs of the cell, so every
bucket comes with its false-positive (control) rate.

-intervene upgrades the world-shift attribution from heuristic to CAUSAL:
each failing run is replayed through logconvert+gk from its stored
stage-1/2 JSON (zero LLM calls, ~2-4s/case) with the question clauses'
pinned world constant freed to a variable; if that alone recovers the b0
answer, the run is bucketed pipeline-world-shift on intervention evidence,
overriding any co-occurring heuristic flag.

Without -intervene: no LLM calls and no prover runs, stored traces only.

Run:  python3 results/ballast-robustness/analysis/cause_map.py
        [-live] [-doses 8,16] [-models gpt,claude] [-intervene]
        [-verbose] [-json FILE]
"""
import re
import json
import argparse
import common as C
import stage1_coverage as S1
import stage2_fidelity as S2

BUCKETS = ["gk-error", "stage2-malformed", "stage1-omission",
           "stage1-capture", "stage1-id-break", "stage1-merge",
           "stage2-loss", "pipeline-world-shift", "stage1-distortion",
           "stage2-distortion", "convert/pipeline", "unexplained"]


# ======== clause-level evidence ========

def clause_logic(cl):
  return cl.get("@logic", cl.get("@question"))


_WORLD = re.compile(r"^W\d+$")


def norm_clause(o):
  """Clause-term normalisation for set comparison across runs: strip
  entity numbering ('#:John 6'->'#:John'), canonicalise ?:variables per
  clause, neutralise unit-id fragments in strings, blur world constants
  (the question-world check below handles worlds explicitly)."""
  def walk(t, varmap):
    if isinstance(t, list):
      return [walk(x, varmap) for x in t]
    if isinstance(t, str):
      if t.startswith("?:"):
        if t not in varmap:
          varmap[t] = f"?:v{len(varmap) + 1}"
        return varmap[t]
      if _WORLD.match(t):
        return "W*"
      return re.sub(r"\s+\d+$", "", t)
    return t
  return json.dumps(walk(o, {}), sort_keys=True)


def nl_tokens(s):
  """Token set of a clause's @nl / an input sentence, blind to the entity
  numbering and word order the pipeline adds ('Is John 6 a child of Mike
  7?' matches 'John is a child of Mike?')."""
  return frozenset(t for t in S1.norm_sent(s).split() if not t.isdigit())


def orig_clause_set(case, orig_token_sets):
  """Normalised STATEMENT clauses whose @nl maps to an original sentence
  of the case (ballast-derived, injected and question clauses excluded;
  question clauses are handled by question_world)."""
  out = {}
  for cl in case.get("clauses") or []:
    if not isinstance(cl, dict):
      continue
    if "question" in str(cl.get("@sourcetype", "")) or "@question" in cl:
      continue
    nl = cl.get("@nl")
    if not isinstance(nl, str) or nl_tokens(nl) not in orig_token_sets:
      continue
    key = norm_clause(clause_logic(cl))
    out[key] = out.get(key, 0) + 1
  return out


def query_unit_ids(case):
  return {u.get("unit_id") for p in (case.get("stage1") or [])
          if isinstance(p, dict) for u in p.get("units", [])
          if u.get("type") == "query"}


def question_world(case):
  """Signature of the world term(s) the question clauses proper
  (@sourcetype == "question") are bound to: 'var' (free -- unifies with
  any world), 'W<k>' (pinned constant), or 'none' (no $ctxt found)."""
  worlds = set()
  for cl in case.get("clauses") or []:
    if not isinstance(cl, dict) or cl.get("@sourcetype") != "question":
      continue
    stack = [clause_logic(cl)]
    while stack:
      t = stack.pop()
      if isinstance(t, list):
        if len(t) >= 3 and t[0] == "$ctxt":
          w = t[2]
          if isinstance(w, str):
            worlds.add("var" if w.startswith("?:") else w)
        stack.extend(x for x in t if isinstance(x, list))
  if not worlds:
    return "none"
  if any(w == "var" for w in worlds):
    return "var"
  return max(worlds, key=lambda w: int(w[1:]) if w[1:].isdigit() else -1)


def error_class(case):
  """Classify pipeline/prover error strings; None if no error surfaced."""
  ans = str(case.get("answer", ""))
  perr = ""
  if isinstance(case.get("proof"), dict):
    perr = str(case["proof"].get("error", ""))
  txt = (ans if ans.startswith("Error") else "") + " " + perr
  txt = txt.lower().strip()
  if not txt:
    return None
  if "datarec" in txt or "memory allocation" in txt:
    return "gk-error"
  if "prover returned empty result" in txt or "prover returned none" in txt:
    # the gk allocator bug (results.md §11.1, case 1011) surfaces exactly
    # like this in the answer field; gk's stderr is not in the trace
    return "gk-error"
  if "null can be used" in txt or "formula" in txt:
    return "stage2-malformed"
  if "several questions" in txt:
    return "stage2-malformed"
  if txt.startswith("error"):
    return "convert/pipeline"
  return None


# ======== per-run cause assignment ========

def freeworld_intervention(case, b0_case):
  """Replay logconvert+gk from the stored stage-1/2 JSON with the question
  world freed; returns (freed_answer, recovers_b0, world_was_pinned)."""
  from spot_verify import replay
  try:
    ans, _n, subs = replay(case, freeworld=True)
  except Exception as e:
    return (f"replay-error: {e}", False, False)
  ans = str(ans)
  recovers = (bool(subs) and b0_case is not None
              and ans == str(b0_case.get("answer"))
              and ans != str(case.get("answer")))
  return (ans, recovers, bool(subs))


def analyze_case(case, b0_case, man_entry, intervene=False):
  """(primary_bucket, evidence dict) for one run."""
  f1 = S1.analyze_run(case, b0_case, man_entry)
  f2 = S2.analyze_run(case, b0_case, man_entry)
  ev = {"stage1": S1.flag_summary(f1), "stage2": S2.flag_summary(f2)}

  orig_tok = {nl_tokens(t) for t, s in
              S1.input_sentences(case, man_entry)
              if s in ("orig", "question")}
  qw = question_world(case)
  qw0 = question_world(b0_case) if b0_case else "none"
  ev["question_world"] = f"{qw0} -> {qw}"

  lost = []
  if b0_case:
    now = orig_clause_set(case, orig_tok)
    was = orig_clause_set(b0_case, orig_tok)
    lost = [k for k in was if k not in now]
    ev["orig_clauses_lost_vs_b0"] = len(lost)
    ev["orig_clauses_b0/now"] = f"{sum(was.values())}/{sum(now.values())}"

  err = error_class(case)
  ev["error_class"] = err

  s1_diff = any((f1.get("b0") or {}).values())
  s2_diff = bool((f2.get("b0") or {}).get("logic_changed"))
  clause_diff = bool(lost)
  # question-world drift: free variable pinned to a constant, or re-pinned
  # to a different constant ('none' = no $ctxt comparison possible)
  world_shifted = (qw != qw0 and qw != "none" and qw0 != "none"
                   and qw != "var")

  # ---- causal intervention (fails only, when -intervene) ----
  if intervene and not C.is_correct(case):
    freed, recovers, pinned = freeworld_intervention(case, b0_case)
    ev["freeworld"] = {"answer": freed, "recovers_b0": recovers,
                       "world_was_pinned": pinned}
    if recovers:
      return "pipeline-world-shift", ev

  # ---- primary bucket, in causal-evidence order ----
  if err == "gk-error":
    return "gk-error", ev
  if err == "stage2-malformed" or f2["malformed"] or f2["n_questions"] != 1:
    return "stage2-malformed", ev
  if any(side in ("orig", "question") for side, _t in f1["omission"]) or \
     any(side in ("orig", "question") for side, _t in f1["empty_units"]):
    return "stage1-omission", ev
  if f1["capture"]:
    return "stage1-capture", ev
  if f2["loss_orig"]:
    return "stage2-loss", ev
  if f1["id_break"]:
    # gk distinguishes "#:book 1" from "#:book 2" even where the
    # normalised clause diff does not; a fractured referent is
    # proof-breaking on its own
    return "stage1-id-break", ev
  if f1["id_merge"]:
    return "stage1-merge", ev
  # heuristic world-shift attribution only when the causal test did NOT
  # run (if it ran and failed to rescue, the pin is not the cause)
  if world_shifted and not clause_diff and \
     not (intervene and not C.is_correct(case)):
    return "pipeline-world-shift", ev
  if clause_diff and s1_diff:
    return "stage1-distortion", ev
  if clause_diff and s2_diff:
    return "stage2-distortion", ev
  if clause_diff or world_shifted or err:
    return "convert/pipeline", ev
  return "unexplained", ev


# ======== CLI ========

def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("-live", action="store_true")
  ap.add_argument("-doses", default="8,16")
  ap.add_argument("-models", default="gpt,claude")
  ap.add_argument("-intervene", action="store_true",
                  help="causal world-shift test: replay each failing run "
                       "through logconvert+gk with the question world "
                       "freed (no LLM calls, ~2-4s per failing case)")
  ap.add_argument("-verbose", action="store_true")
  ap.add_argument("-json", default=None,
                  help="dump per-case records to this file")
  args = ap.parse_args()
  source = "live" if args.live else "snapshot"
  doses = [int(s) for s in args.doses.split(",") if s.strip()]
  models = [x for x in args.models.split(",") if x]

  records = []
  table = {}   # (model, dose) -> {bucket: count}
  controls = {}  # (model, dose) -> {bucket: count among passes}

  for d in doses:
    excl = C.exclusions(d)
    for m in models:
      cc = C.load(d, m, source)
      cc = {cid: c for cid, c in cc.items() if cid not in excl}
      if not cc:
        print(f"b{d} {m}: no data")
        continue
      man, rev = C.resolve_manifest(d, cc)
      b0 = C.load(0, m)
      print(f"\n=== b{d} {m} ({len(cc)} valid cases; manifest rev "
            f"{rev or 'worktree'}) ===")
      tab, ctl = {}, {}
      for cid, case in sorted(cc.items()):
        if cid not in man:
          continue
        ok = C.is_correct(case)
        bucket, ev = analyze_case(case, b0.get(cid), man[cid],
                                  intervene=args.intervene)
        rec = {"model": m, "dose": d, "case_id": cid, "correct": ok,
               "answer": str(case.get("answer", "")),
               "expected": case.get("expected_answer"),
               "bucket": bucket, "evidence": ev,
               "b0_correct": C.is_correct(b0[cid]) if cid in b0 else None}
        records.append(rec)
        if ok:
          ctl[bucket] = ctl.get(bucket, 0) + 1
        else:
          tab[bucket] = tab.get(bucket, 0) + 1
          print(f"  case {cid:4d} -> {bucket:20s} "
                f"answer={rec['answer'][:36]!r:40s} "
                f"qworld[{ev['question_world']}] "
                f"lost={ev.get('orig_clauses_lost_vs_b0', '?')}"
                + (f" b0_FAIL" if rec["b0_correct"] is False else ""))
          if args.verbose:
            print(f"        s1: {ev['stage1']}  s2: {ev['stage2']}  "
                  f"err: {ev['error_class']}")
      table[(m, d)] = tab
      controls[(m, d)] = ctl

  print("\n\nCAUSE MAP (failing valid runs; pass-side control counts in "
        "parentheses)\n")
  hdr = f"{'bucket':20s}" + "".join(f"{m} b{d:<6}" for d in doses
                                    for m in models)
  print(hdr)
  print("-" * len(hdr))
  for b in BUCKETS:
    row = f"{b:20s}"
    tot = 0
    for d in doses:
      for m in models:
        n = table.get((m, d), {}).get(b, 0)
        c = controls.get((m, d), {}).get(b, 0)
        tot += n
        row += f"{n:3d} ({c:2d})  "
    if tot or b == "unexplained":
      print(row)
  print("\n(control = passing runs the same detector chain assigns to the "
        "same bucket;\n 'unexplained' among passes simply means no flag "
        "fired, which is the healthy state)")

  if args.json:
    with open(args.json, "w") as f:
      json.dump(records, f, indent=1)
    print(f"\nwrote {len(records)} records to {args.json}")


if __name__ == "__main__":
  main()
