#!/usr/bin/env python3
"""Stage-2 fidelity: did the ASU -> logic stage keep every stage-1 unit,
keep the question, and keep each unit's logic equivalent to the b0
baseline?  (Plan 03 §2.2 -- Tanel's second question, asked only of runs
whose stage 1 is mostly OK.)

Stage 2 output is ["and", ["@id", "S<k>", <logic>], ...] keyed by the
stage-1 unit ids, so coverage is exact.  Flags:

  malformed     stage2 missing/non-list, nulls in the tree, duplicate or
                shapeless @id entries (claude's b8-1315 / b16-193 class);
  s2-loss       stage-1 unit id with no @id entry (split by input side);
  s2-extra      @id entry with no stage-1 unit (hallucinated unit);
  no-question / multi-question
                count of ["question", ...] formulas != 1 (gk rejects >1);
  vs-b0         per original input sentence: the normalised logic of its
                units differs from the b0 run (entity numbering, unit-id
                references and bound-variable names are normalised away
                first, so only structural/semantic drift remains).

No LLM calls; reads stored traces only.

Run:  python3 results/ballast-robustness/analysis/stage2_fidelity.py
        [-live] [-doses 8,16] [-models gpt,claude] [-fails-only] [-verbose]
"""
import re
import json
import argparse
import common as C
from stage1_coverage import (input_sentences, align, norm_sent)


# ======== stage-2 indexing and normalisation ========

def s2_index(stage2):
  """({unit_id: logic}, issues).  Tolerates the observed shapes; anything
  unexpected lands in issues as 'malformed: ...'."""
  issues = []
  if not isinstance(stage2, list) or not stage2:
    return {}, ["malformed: stage2 missing or not a list"]
  if tree_has_none(stage2):
    issues.append("malformed: null inside stage2 tree")
  id2logic = {}
  entries = stage2[1:] if stage2 and stage2[0] == "and" else stage2
  for e in entries:
    if (isinstance(e, list) and len(e) == 3 and e[0] == "@id"
        and isinstance(e[1], str)):
      if e[1] in id2logic:
        issues.append(f"malformed: duplicate @id {e[1]}")
      id2logic[e[1]] = e[2]
    else:
      issues.append(f"malformed: non-@id entry {json.dumps(e)[:60]}")
  return id2logic, issues


def tree_has_none(o):
  if o is None:
    return True
  if isinstance(o, list):
    return any(tree_has_none(x) for x in o)
  return False


def count_questions(id2logic):
  """yes/no questions are ["question", ...], wh-questions ["ask", var, ...]."""
  n = 0
  for logic in id2logic.values():
    stack = [logic]
    while stack:
      t = stack.pop()
      if isinstance(t, list):
        if t and t[0] in ("question", "ask"):
          n += 1
        stack.extend(x for x in t if isinstance(x, list))
  return n


_ENT_NUM = re.compile(r"\s+\d+$")
_UNIT_ID = re.compile(r"^S\d+$")
_VAR = re.compile(r"^[A-Z][0-9]*$")


def norm_logic(o, varmap=None):
  """Normalise one unit's logic for cross-run comparison: strip entity
  numeric suffixes ('John 6'->'John'), neutralise unit-id references
  ('S5'->'S*'), rename bound variables AND world constants in
  first-occurrence order.  Worlds must be renamed here because ballast
  event sentences legitimately renumber the world chain around the
  original sentences; absolute world drift is a *pipeline*-level concern
  handled by cause_map's question-world check, not an LLM stage-2 one."""
  if varmap is None:
    varmap = {}
  if isinstance(o, list):
    return [norm_logic(x, varmap) for x in o]
  if isinstance(o, str):
    if _UNIT_ID.match(o):
      return "S*"
    if re.match(r"^W\d+$", o) or _VAR.match(o):
      if o not in varmap:
        varmap[o] = f"v{len(varmap) + 1}"
      return varmap[o]
    return _ENT_NUM.sub("", o)
  return o


def norm_key(logic):
  return json.dumps(norm_logic(logic), sort_keys=True)


# ======== per-run analysis ========

def unit_side_map(case, man_entry):
  """{unit_id: side} via the stage-1 sentence alignment."""
  expected = input_sentences(case, man_entry)
  pkgs = [p for p in (case.get("stage1") or []) if isinstance(p, dict)]
  cover, _owner = align([t for t, _s in expected], [p.get("raw", "")
                                                    for p in pkgs])
  side_of = {}
  for i, (_text, side) in enumerate(expected):
    for j in cover[i]:
      for u in pkgs[j].get("units", []):
        uid = u.get("unit_id")
        if uid:
          side_of[uid] = "orig" if side == "question" else side
  return side_of


def sentence_unit_ids(case, man_entry, sides=("orig", "question")):
  """{normalised sentence: [unit ids]} for the given input sides."""
  expected = input_sentences(case, man_entry)
  pkgs = [p for p in (case.get("stage1") or []) if isinstance(p, dict)]
  cover, owner = align([t for t, _s in expected], [p.get("raw", "")
                                                   for p in pkgs])
  out = {}
  for i, (text, side) in enumerate(expected):
    if side not in sides:
      continue
    if any(len(owner[j]) > 1 for j in cover[i]):
      continue  # merged with another sentence; not attributable
    out[norm_sent(text)] = [u.get("unit_id") for j in cover[i]
                            for u in pkgs[j].get("units", [])
                            if u.get("unit_id")]
  return out


def analyze_run(case, b0_case, man_entry):
  """All stage-2 flags for one run.  b0_case may be None."""
  id2logic, issues = s2_index(case.get("stage2"))
  side_of = unit_side_map(case, man_entry)
  s1_ids = set(side_of)

  flags = {"malformed": issues, "loss_orig": [], "loss_ballast": [],
           "extra": sorted(set(id2logic) - s1_ids),
           "n_questions": count_questions(id2logic), "b0": {}}
  for uid in sorted(s1_ids - set(id2logic)):
    key = "loss_orig" if side_of[uid] == "orig" else "loss_ballast"
    flags[key].append(uid)

  if b0_case:
    b0_id2logic, _ = s2_index(b0_case.get("stage2"))
    # original sentences only; b0 input == base text, so use a manifest
    # entry with no ballast for the baseline side
    b0_man = {"ballast": []}
    sent_ids = sentence_unit_ids(case, man_entry)
    b0_sent_ids = sentence_unit_ids(b0_case, b0_man)
    changed = []
    for key, uids in sent_ids.items():
      if key not in b0_sent_ids:
        continue
      now = sorted(norm_key(id2logic[u]) for u in uids if u in id2logic)
      was = sorted(norm_key(b0_id2logic[u]) for u in b0_sent_ids[key]
                   if u in b0_id2logic)
      if now != was:
        changed.append((key, len(was), len(now)))
    flags["b0"]["logic_changed"] = changed
  return flags


def flag_summary(flags):
  tags = []
  if flags["malformed"]:
    tags.append(f"malformed x{len(flags['malformed'])}")
  if flags["loss_orig"]:
    tags.append(f"s2-loss-orig x{len(flags['loss_orig'])}")
  if flags["loss_ballast"]:
    tags.append(f"s2-loss-ballast x{len(flags['loss_ballast'])}")
  if flags["extra"]:
    tags.append(f"s2-extra x{len(flags['extra'])}")
  if flags["n_questions"] != 1:
    tags.append(f"questions={flags['n_questions']}")
  ch = flags["b0"].get("logic_changed") if flags.get("b0") else None
  if ch:
    tags.append(f"b0:logic-changed x{len(ch)}")
  return tags


# ======== CLI ========

def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("-live", action="store_true")
  ap.add_argument("-doses", default="8,16")
  ap.add_argument("-models", default="gpt,claude")
  ap.add_argument("-fails-only", action="store_true", dest="fails_only")
  ap.add_argument("-verbose", action="store_true")
  args = ap.parse_args()
  source = "live" if args.live else "snapshot"

  for d in [int(s) for s in args.doses.split(",") if s.strip()]:
    excl = C.exclusions(d)
    for m in [x for x in args.models.split(",") if x]:
      cc = C.load(d, m, source)
      cc = {cid: c for cid, c in cc.items() if cid not in excl}
      if not cc:
        print(f"b{d} {m}: no data")
        continue
      man, rev = C.resolve_manifest(d, cc)
      b0 = C.load(0, m)
      print(f"\n=== b{d} {m} ({len(cc)} valid cases; manifest rev "
            f"{rev or 'worktree'}) ===")
      agg = {"fail": {}, "pass": {}, "n_fail": 0, "n_pass": 0}
      for cid, case in sorted(cc.items()):
        if cid not in man:
          continue
        ok = C.is_correct(case)
        if args.fails_only and ok:
          continue
        flags = analyze_run(case, b0.get(cid), man[cid])
        tags = flag_summary(flags)
        grp = "pass" if ok else "fail"
        agg["n_" + grp] += 1
        for t in tags:
          agg[grp][t.split(" x")[0]] = agg[grp].get(t.split(" x")[0], 0) + 1
        if not ok or args.verbose:
          print(f"  case {cid:4d} {'PASS' if ok else 'FAIL'} "
                f"[{', '.join(tags) if tags else 'clean stage2'}]")
          if args.verbose:
            for k in ("malformed", "loss_orig", "loss_ballast", "extra"):
              for item in flags.get(k) or []:
                print(f"        {k}: {item}")
            for item in flags["b0"].get("logic_changed", []):
              print(f"        b0:logic-changed: {item}")
      print(f"  -- flag prevalence: fails (n={agg['n_fail']}) "
            f"{dict(sorted(agg['fail'].items()))}")
      if not args.fails_only:
        print(f"                      passes (n={agg['n_pass']}) "
              f"{dict(sorted(agg['pass'].items()))}")


if __name__ == "__main__":
  main()
