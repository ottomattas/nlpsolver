#!/usr/bin/env python3
"""Proposal 2 (plan 04 follow-up): does entity id-break depend on the
DISTANCE between mentions (a finite tracking horizon), rather than on the
total ballast dose?

stage1_coverage flags an id-break when one concrete referent fractures into
several entity ids vs its b0 run (results.md §15.1, §12.4 -- the dominant
chunk-boundary failure mode and the one s2split makes worse).  If breaks are
a horizon effect, a referent should fracture once its two mentions drift far
enough apart -- and the breaking distance should be roughly dose-independent,
which would name a concrete chunk-size budget the pipeline can hold.

For every concrete referent that is mentioned more than once (an original
sentence plus, typically, the question), this measures the gap between its
first and last mention:

  span_sents      input sentences from first to last mention (inclusive of
                  the intervening ballast);
  ballast_gap     ballast sentences sitting between the two mentions -- the
                  actual neural "carry" the model had to sustain.

Referents are split into BROKEN (id-break vs b0) and HELD (kept one id), and
the ballast_gap distributions are compared per model.  A clean horizon shows
up as broken referents living above a gap threshold that holds across doses.

No LLM calls, no prover: stored stage-1 traces + the generator manifest only.

Run:  python3 tracking_horizon.py [-doses 8,16,32]
        [-models gpt,claude,gemini,deepseek] [-verbose] [-live]
"""
import sys
import argparse
import statistics as st
import common as C
import stage1_coverage as S1


def per_sentence_basenames(case, man_entry):
  """[(side, {concrete base-name})] aligned to input sentence order."""
  expected = S1.input_sentences(case, man_entry)
  s1 = case.get("stage1") or []
  raws = [p.get("raw", "") for p in s1 if isinstance(p, dict)]
  pkgs = [p for p in s1 if isinstance(p, dict)]
  cover, _owner = S1.align([t for t, _s in expected], raws)
  rows = []
  for i, (_t, side) in enumerate(expected):
    names = set()
    for j in cover[i]:
      for u in pkgs[j].get("units", []):
        for eid, etype in S1.real_entities(u):
          if etype == "concrete":
            names.add(S1.base_name(eid))
    rows.append((side, names))
  return rows


def broken_basenames(case, b0_case):
  """{base-name: (n_ids_now, n_ids_b0)} for concrete referents on the
  original side, split into broken (more ids than b0) and held."""
  def census(stage1, exclude_ballast_sides=None):
    seen = {}
    for p in (stage1 or []):
      if not isinstance(p, dict):
        continue
      for u in p.get("units", []):
        for eid, etype in S1.real_entities(u):
          if etype == "concrete":
            seen.setdefault(S1.base_name(eid), set()).add(eid)
    return seen
  now = census(case.get("stage1"))
  was = census(b0_case.get("stage1")) if b0_case else {}
  out = {}
  for name, ids in now.items():
    n0 = len(was.get(name, [1])) if b0_case else 1
    out[name] = (len(ids), max(n0, 1))
  return out


def referent_gaps(case, b0_case, man_entry):
  """[(base, broken, n_ids, span_sents, ballast_gap)] for multiply-mentioned
  concrete referents (>=2 input sentences mention them)."""
  rows = per_sentence_basenames(case, man_entry)
  census = broken_basenames(case, b0_case)
  out = []
  for name, (n_now, n0) in census.items():
    # mention sentences on the tracked (orig+question) side
    idxs = [i for i, (side, names) in enumerate(rows)
            if side in ("orig", "question") and name in names]
    if len(idxs) < 2:
      continue
    first, last = idxs[0], idxs[-1]
    ballast_gap = sum(1 for i in range(first + 1, last)
                      if rows[i][0] == "ballast")
    out.append((name, n_now > n0, n_now, last - first, ballast_gap))
  return out


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("-doses", default="8,16,32")
  ap.add_argument("-models", default="gpt,claude,gemini,deepseek")
  ap.add_argument("-live", action="store_true")
  ap.add_argument("-verbose", action="store_true")
  args = ap.parse_args()
  source = "live" if args.live else "snapshot"
  doses = [int(s) for s in args.doses.split(",") if s.strip()]
  models = [x for x in args.models.split(",") if x]

  # per model: lists of ballast_gap for broken vs held referents
  agg = {m: {"broken": [], "held": [], "by_dose": {}} for m in models}
  pairs = []  # pooled (ballast_gap, broken_bool) for the hazard curve

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
      dose_broken = []
      for cid, case in sorted(cc.items()):
        if cid not in man:
          continue
        for name, broken, n_ids, span, bgap in \
                referent_gaps(case, b0.get(cid), man[cid]):
          bucket = "broken" if broken else "held"
          agg[m][bucket].append(bgap)
          pairs.append((bgap, broken))
          if broken:
            dose_broken.append(bgap)
            if args.verbose:
              print(f"  b{d} {m} case {cid:4d}: {name!r} broke into "
                    f"{n_ids} ids; span={span} sents, ballast_gap={bgap}")
      agg[m]["by_dose"][d] = dose_broken

  def summ(xs):
    if not xs:
      return "n=0"
    return (f"n={len(xs)} min={min(xs)} med={int(st.median(xs))} "
            f"mean={st.mean(xs):.1f} max={max(xs)}")

  print("\n==== Proposal 2 summary: tracking horizon (ballast sentences "
        "between mentions) ====\n")
  print(f"{'model':9s} {'broken referents':38s} {'held referents'}")
  for m in models:
    print(f"{m:9s} {summ(agg[m]['broken']):38s} {summ(agg[m]['held'])}")

  print("\n-- breaking distance by dose (ballast_gap of broken referents) --")
  for m in models:
    parts = []
    for d in doses:
      xs = agg[m]["by_dose"].get(d, [])
      parts.append(f"b{d}:{summ(xs)}")
    print(f"  {m:9s} " + " | ".join(parts))

  print("\n-- break hazard by mention gap (all models pooled) --")
  edges = [(0, 1), (2, 3), (4, 6), (7, 10), (11, 15), (16, 999)]
  print(f"  {'ballast_gap':12s} {'referents':>10s} {'broken':>7s} {'rate':>7s}")
  for lo, hi in edges:
    sub = [b for g, b in pairs if lo <= g <= hi]
    nb = sum(sub)
    rate = (nb / len(sub) * 100) if sub else 0.0
    label = f"{lo}-{hi if hi < 999 else '+'}"
    print(f"  {label:12s} {len(sub):>10d} {nb:>7d} {rate:>6.1f}%")

  print("\nRead: if 'broken' gaps sit well above 'held' gaps and the broken "
        "min/median is similar across doses,\nthe break is a mention-distance "
        "(horizon) effect, not a raw-dose effect -- naming a chunk budget.")


if __name__ == "__main__":
  main()
