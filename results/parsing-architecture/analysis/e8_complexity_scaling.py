#!/usr/bin/env python3
"""E8 - Complexity scaling.

Tests whether the one-stage collapse is concentrated on COMPLEX inputs: does the
two-stage (A) - one-stage-direct (C) accuracy gap widen as the input grows?

Complexity per case (cheap, text + two-stage-logic derived):
  sentences = terminal-punctuation count;
  entities  = Stage-2 sentence-packages in the two-stage parse (structural size);
  words     = whitespace tokens.
Cases are binned by a combined complexity score; for each bin we report A and C
accuracy and the gap.  Also prints the point-biserial correlation between each
complexity feature and C being WRONG (positive = harder inputs fail more often).

Run:  python3 results/parsing-architecture/analysis/e8_complexity_scaling.py
"""
import common as C


def corr(xs, ys):
  """Pearson r (point-biserial when ys is 0/1)."""
  n = len(xs)
  if n < 2:
    return 0.0
  mx = sum(xs) / n
  my = sum(ys) / n
  num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
  dx = sum((x - mx) ** 2 for x in xs) ** 0.5
  dy = sum((y - my) ** 2 for y in ys) ** 0.5
  return num / (dx * dy) if dx and dy else 0.0


def main():
  print("\nE8 - complexity scaling: does the A-vs-C gap widen with input size? "
        "(core_100)\n")
  # Pool all models for a stable signal on the easy 100-subset.
  rows = []  # (sentences, entities, words, A_correct, C_correct)
  feats = {"sentences": [], "entities": [], "words": []}
  c_wrong = []
  for model in C.MODELS:
    a = C.load("A", model)
    c = C.load("C", model)
    for i in set(a) & set(c):
      text = a[i].get("input_text", "")
      s = C.n_sentences(text)
      e = C.stage2_packages(a[i])
      w = len((text or "").split())
      rows.append((s, e, w, C.is_correct(a[i]), C.is_correct(c[i])))
      feats["sentences"].append(s)
      feats["entities"].append(e)
      feats["words"].append(w)
      c_wrong.append(0 if C.is_correct(c[i]) else 1)

  # Bin by a combined score (sentences + entities) into low/med/high terciles.
  scored = sorted(rows, key=lambda r: (r[0] + r[1], r[2]))
  k = max(1, len(scored) // 3)
  bins = [("low", scored[:k]), ("med", scored[k:2 * k]), ("high", scored[2 * k:])]
  print(f"{'bin':6} {'n':>4} {'sent~':>6} {'ent~':>5} {'A acc%':>7} {'C acc%':>7} {'gap':>6}")
  print("-" * 44)
  for name, grp in bins:
    n = len(grp) or 1
    sa = 100.0 * sum(r[3] for r in grp) / n
    sc = 100.0 * sum(r[4] for r in grp) / n
    sent = sum(r[0] for r in grp) / n
    ent = sum(r[1] for r in grp) / n
    print(f"{name:6} {len(grp):4d} {sent:6.1f} {ent:5.1f} {sa:7.1f} {sc:7.1f} {sa-sc:6.1f}")

  print("\ncorrelation of complexity with C being WRONG (point-biserial r):")
  for f in ("sentences", "entities", "words"):
    print(f"  {f:10} r = {corr(feats[f], c_wrong):+.3f}")
  print("\nReading: a positive gap that grows low->high, and positive r, support "
        "'one-stage fails more as inputs get complex'.  On the curated-easy 100-set "
        "the effect is muted; the full 1600-set is where it should show clearly.\n")


if __name__ == "__main__":
  main()
