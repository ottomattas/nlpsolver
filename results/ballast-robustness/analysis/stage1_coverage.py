#!/usr/bin/env python3
"""Stage-1 coverage: did the semantic stage (ASU output) keep all input
sentences, and did it keep entity identity straight?  (Plan 03 §2.1 —
Tanel's first question: "kas seal on lauseid puudu, kas ei suudeta
trackida objekte".)

Per run, the input sentences (original + ballast, classified through the
generator manifest of the suite the cell ACTUALLY ran on) are aligned to
the stage-1 `raw` entries, tolerating LLM-side merges and splits.  Flags:

  omission     input sentence with no stage-1 package at all (or an empty
               `units` list) -- the sentence vanished from the parse;
  capture      an entity base-name appears in units on BOTH the original
               and the ballast side (coreference/merge leak: inertness
               guarantees the two vocabularies are disjoint);
  id-break     the same concrete base-name carries MORE distinct numeric
               ids than in the b0 baseline run of the same case (one
               referent fractured into several entities);
  vs-b0        per original sentence: unit-count drop, unit-type flips,
               entity/action/adjective losses, confidence changes against
               the b0 (no-ballast) run of the same case+model.

No LLM calls; reads stored traces only.

Run:  python3 results/ballast-robustness/analysis/stage1_coverage.py
        [-live] [-doses 8,16] [-models gpt,claude] [-fails-only] [-verbose]
"""
import os
import re
import sys
import argparse
import common as C

sys.path.insert(0, C.BALLAST_DIR)
from make_ballast import split_sentences, norm_ws


# ======== sentence alignment ========

def norm_sent(s):
  """Normalisation for sentence identity: case/punct/whitespace-blind."""
  s = s.lower()
  s = re.sub(r"[^a-z0-9]+", " ", s)
  return re.sub(r"\s+", " ", s).strip()


def input_sentences(case, man_entry):
  """[(text, side)] in input order; side in {orig, ballast, question}.
  Classified by membership of the manifest's ballast texts in the stored
  input_text -- authoritative regardless of slot semantics."""
  sents = split_sentences(norm_ws(case["input_text"]))
  ballast = {norm_sent(b["text"]) for b in man_entry["ballast"]}
  out = []
  for i, s in enumerate(sents):
    if i == len(sents) - 1:
      side = "question"
    elif norm_sent(s) in ballast:
      side = "ballast"
    else:
      side = "orig"
    out.append((s, side))
  return out


def align(expected, raws):
  """Align expected input sentences to stage-1 raw strings.

  Returns (cover, owner): cover[i] = raw indices covering expected[i];
  owner[j] = expected indices covered by raw j.  Handles 1:1 matches,
  raw-side merges (one raw = several consecutive expected) and splits
  (several consecutive raws = one expected), then a token-overlap
  fallback for paraphrased raws.
  """
  ne, nr = len(expected), len(raws)
  en = [norm_sent(s) for s in expected]
  rn = [norm_sent(s) for s in raws]
  cover = [[] for _ in range(ne)]
  owner = [[] for _ in range(nr)]

  def free_e(i):
    return not cover[i]

  def free_r(j):
    return not owner[j]

  def link(i, j):
    cover[i].append(j)
    owner[j].append(i)

  # 1:1 exact, in order (duplicates pair up positionally)
  used = set()
  for j in range(nr):
    for i in range(ne):
      if i not in used and free_e(i) and en[i] == rn[j]:
        link(i, j)
        used.add(i)
        break

  # merges: one raw covers >= 2 consecutive expected
  for j in range(nr):
    if not free_r(j):
      continue
    for w in (2, 3, 4):
      for i in range(ne - w + 1):
        if all(free_e(k) for k in range(i, i + w)) and \
           " ".join(en[i:i + w]) == rn[j]:
          for k in range(i, i + w):
            link(k, j)
          break
      if not free_r(j):
        break

  # splits: >= 2 consecutive raws cover one expected
  for i in range(ne):
    if not free_e(i):
      continue
    for w in (2, 3, 4):
      for j in range(nr - w + 1):
        if all(free_r(k) for k in range(j, j + w)) and \
           " ".join(rn[j:j + w]) == en[i]:
          for k in range(j, j + w):
            link(i, k)
          break
      if not free_e(i):
        break

  # fuzzy fallback: best token-Jaccard >= 0.5 between leftovers
  for j in range(nr):
    if not free_r(j):
      continue
    rt = set(rn[j].split())
    best, best_i = 0.0, None
    for i in range(ne):
      if not free_e(i):
        continue
      et = set(en[i].split())
      if not rt or not et:
        continue
      jac = len(rt & et) / len(rt | et)
      if jac > best:
        best, best_i = jac, i
    if best_i is not None and best >= 0.5:
      link(best_i, j)

  return cover, owner


# ======== entity utilities ========

# Bound variables / placeholders in stage-1 entity lists ("X1", "Y", "E2");
# real entities are either "name N" (concrete) or a plain noun (generic).
_VAR_RE = re.compile(r"^[A-Z][0-9]*$")
_PLACEHOLDERS = {"someone", "something", "somebody"}


def base_name(eid):
  """'John 6' -> 'john'; 'mouse 3' -> 'mouse'; 'animals' -> 'animals'."""
  return re.sub(r"\s+\d+$", "", eid).strip().lower()


def real_entities(unit):
  """Non-variable, non-placeholder entity ids of one unit."""
  out = []
  for e in unit.get("entities", []):
    eid = e.get("id")
    if not isinstance(eid, str) or _VAR_RE.match(eid):
      continue
    if base_name(eid) in _PLACEHOLDERS:
      continue
    out.append((eid, e.get("type")))
  return out


def sentence_features(units):
  """Comparable feature summary of one input sentence's units."""
  return {
    "n_units": len(units),
    "types": sorted(u.get("type", "?") for u in units),
    "entities": sorted({base_name(eid) for u in units
                        for eid, _t in real_entities(u)}),
    "actions": sorted({a.get("root", "?") for u in units
                       for a in u.get("actions", [])}),
    "adjectives": sorted({adj[0] for u in units
                          for adj in u.get("adjectives", [])
                          if isinstance(adj, list) and adj}),
    "confidences": sorted(u["confidence"] for u in units
                          if isinstance(u.get("confidence"), (int, float))),
  }


# ======== per-run analysis ========

def analyze_run(case, b0_case, man_entry):
  """All stage-1 flags for one run.  b0_case may be None (no baseline)."""
  expected = input_sentences(case, man_entry)
  s1 = case.get("stage1") or []
  raws = [p.get("raw", "") for p in s1 if isinstance(p, dict)]
  pkgs = [p for p in s1 if isinstance(p, dict)]
  cover, owner = align([t for t, _s in expected], raws)

  flags = {"omission": [], "empty_units": [], "seg_drift": [],
           "merged": [], "capture": [], "id_break": [], "b0": {}}

  # sentence -> units (merged sentences share the raw's units)
  sent_units = []
  for i, (text, side) in enumerate(expected):
    units = [u for j in cover[i] for u in pkgs[j].get("units", [])]
    merged = any(len(owner[j]) > 1 for j in cover[i])
    sent_units.append((text, side, units, merged))
    if not cover[i]:
      flags["omission"].append((side, text))
    elif not units:
      flags["empty_units"].append((side, text))
    if merged:
      flags["merged"].append((side, text))
  for j in range(len(raws)):
    if not owner[j]:
      flags["seg_drift"].append(raws[j])

  # capture: entity base-name present on both sides
  side_names = {"orig": set(), "ballast": set()}
  for text, side, units, _m in sent_units:
    key = "orig" if side == "question" else side
    for u in units:
      for eid, _t in real_entities(u):
        side_names[key].add(base_name(eid))
  flags["capture"] = sorted(side_names["orig"] & side_names["ballast"])

  # id-break: concrete base-name (on the ORIGINAL side -- ballast keeps
  # its own referents) with more distinct ids than at b0
  def census_units(units_list):
    seen = {}
    for u in units_list:
      for eid, etype in real_entities(u):
        if etype == "concrete":
          seen.setdefault(base_name(eid), set()).add(eid)
    return seen

  census = census_units([u for _t, side, units, _m in sent_units
                         if side != "ballast" for u in units])
  base_census = census_units([u for p in (b0_case.get("stage1") or [])
                              if isinstance(p, dict)
                              for u in p.get("units", [])]) if b0_case else {}
  for name, ids in sorted(census.items()):
    n0 = len(base_census.get(name, [1])) if b0_case else 1
    if len(ids) > max(n0, 1):
      flags["id_break"].append((name, sorted(ids)))

  # vs b0, per original sentence (skip merged -- counts not attributable)
  if b0_case:
    b0_raws = [p.get("raw", "") for p in (b0_case.get("stage1") or [])
               if isinstance(p, dict)]
    b0_pkgs = [p for p in (b0_case.get("stage1") or []) if isinstance(p, dict)]
    orig_texts = [t for t, s in expected if s in ("orig", "question")]
    b0_cover, b0_owner = align(orig_texts, b0_raws)
    b0_units = {}
    for i, t in enumerate(orig_texts):
      if any(len(b0_owner[j]) > 1 for j in b0_cover[i]):
        continue
      b0_units[norm_sent(t)] = [u for j in b0_cover[i]
                                for u in b0_pkgs[j].get("units", [])]
    diffs = {"unit_drop": [], "type_flip": [], "entity_loss": [],
             "action_loss": [], "adjective_loss": [], "confidence_change": []}
    for text, side, units, merged in sent_units:
      if side == "ballast" or merged:
        continue
      key = norm_sent(text)
      if key not in b0_units:
        continue
      f, f0 = sentence_features(units), sentence_features(b0_units[key])
      if f["n_units"] < f0["n_units"]:
        diffs["unit_drop"].append((text, f0["n_units"], f["n_units"]))
      if f["types"] != f0["types"]:
        diffs["type_flip"].append((text, f0["types"], f["types"]))
      for fld, flag in [("entities", "entity_loss"), ("actions", "action_loss"),
                        ("adjectives", "adjective_loss")]:
        lost = sorted(set(f0[fld]) - set(f[fld]))
        if lost:
          diffs[flag].append((text, lost))
      if f["confidences"] != f0["confidences"]:
        diffs["confidence_change"].append((text, f0["confidences"],
                                           f["confidences"]))
    flags["b0"] = diffs
  return flags


def flag_summary(flags):
  """Short one-line tag list for a run's flags."""
  tags = []
  for k in ("omission", "empty_units", "capture", "id_break", "seg_drift"):
    if flags.get(k):
      tags.append(f"{k}x{len(flags[k])}")
  for k, v in (flags.get("b0") or {}).items():
    if v:
      tags.append(f"b0:{k}x{len(v)}")
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
          agg[grp][t.split("x")[0]] = agg[grp].get(t.split("x")[0], 0) + 1
        if not ok or args.verbose:
          print(f"  case {cid:4d} {'PASS' if ok else 'FAIL'} "
                f"[{', '.join(tags) if tags else 'clean stage1'}]")
          if args.verbose:
            for k in ("omission", "empty_units", "capture", "id_break"):
              for item in flags.get(k) or []:
                print(f"        {k}: {item}")
            for k, v in (flags.get("b0") or {}).items():
              for item in v:
                print(f"        b0:{k}: {item}")
      print(f"  -- flag prevalence: fails (n={agg['n_fail']}) "
            f"{dict(sorted(agg['fail'].items()))}")
      if not args.fails_only:
        print(f"                      passes (n={agg['n_pass']}) "
              f"{dict(sorted(agg['pass'].items()))}")


if __name__ == "__main__":
  main()
