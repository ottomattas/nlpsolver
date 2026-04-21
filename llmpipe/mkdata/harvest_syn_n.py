#!/usr/bin/env python3
"""
Harvest new NOUN synonym pair candidates from the zaibacu WordNet-derived
thesaurus (roget.json) and produce a review file listing:

  ADD  — candidate word to join an existing cluster in syn_n_10.txt
  NEW  — candidate pair seeding a brand-new cluster
  SKIP — pair landing between two different clusters (merge, not handled)

Parallel to harvest_syn_a.py but specialised for nouns:
  * pos filter: zaibacu pos='noun', WordNet pos='n'
  * WordNet-strong = pair must share a NOUN SYNSET (no hypernym/hyponym)
  * effective primary group = lemmas of the word's first noun synset; no
    similar_to or satellite expansion (those don't exist for nouns)

Filters applied:
  - both words single-token, alpha, zipf_frequency >= --min_zipf (default 4.0)
  - both words have a WordNet noun synset
  - pair must be linked via shared noun synset
  - ADD bucket: absent's primary noun synset must contain at least one OTHER
    cluster member besides the trigger word
  - NEW seeds: a and b must share a noun synset (symmetric)

Apply-mode policy matches harvest_syn_a.py:
  - ADD score >= --min_score_member (0.70)
  - NEW score >= --min_score_canonical (0.828) -> new cluster with "_NH##" CID
  - NEW min_score_member <= score < min_score_canonical -> stash in
    syn_n_soft_pairs.txt
  - below min_score_member: drop

Run:
    mkdata/venv/bin/python harvest_syn_n.py                      # review only
    mkdata/venv/bin/python harvest_syn_n.py --apply              # also apply
    mkdata/venv/bin/python harvest_syn_n.py --apply --dry_run    # print diff
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np
from nltk.corpus import wordnet as wn
from wordfreq import zipf_frequency


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SYN = os.path.join(SCRIPT_DIR, "syn_n_10.txt")
DEFAULT_THESAURUS = os.path.join(SCRIPT_DIR, "roget.json")
DEFAULT_FT_MODEL = os.path.join(SCRIPT_DIR, "cc.en.300.bin")
DEFAULT_REVIEW = os.path.join(SCRIPT_DIR, "syn_n_additions_review.txt")
DEFAULT_SOFT_PAIRS = os.path.join(SCRIPT_DIR, "syn_n_soft_pairs.txt")
DEFAULT_MIN_SCORE_MEMBER = 0.70
DEFAULT_MIN_SCORE_CANONICAL = 0.828


# ----- syn_n_10.txt loading --------------------------------------------------

def load_clusters(path):
  """Return (cid_to_words, word_to_cids, existing_pairs)."""
  cid_to_words = {}
  word_to_cids = defaultdict(set)
  existing_pairs = set()
  for line in open(path, encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#"):
      continue
    parts = line.split(",")
    cid = parts[0]
    canon = cid.rsplit("_", 1)[0].lower()
    words = {canon}
    i = 1
    while i + 1 < len(parts):
      words.add(parts[i].strip().lower())
      i += 2
    cid_to_words[cid] = words
    for w in words:
      word_to_cids[w].add(cid)
    wl = sorted(words)
    for a in range(len(wl)):
      for b in range(a + 1, len(wl)):
        existing_pairs.add(frozenset({wl[a], wl[b]}))
  return cid_to_words, word_to_cids, existing_pairs


# ----- candidate filtering ---------------------------------------------------

def is_common_noun(w, min_zipf):
  if not w or not w.replace("_", "").isalpha():
    return False
  if zipf_frequency(w.replace("_", " "), "en") < min_zipf:
    return False
  return bool(wn.synsets(w, pos="n"))


def wn_relation(a, b):
  """Return 'same_synset' if a and b share any noun synset, else None.
  Hypernym/hyponym links are intentionally NOT used for nouns."""
  sa = set(wn.synsets(a, pos="n"))
  sb = set(wn.synsets(b, pos="n"))
  if sa & sb:
    return "same_synset"
  return None


def primary_noun_synset(word):
  syns = wn.synsets(word, pos="n")
  return syns[0] if syns else None


def effective_primary_group(word):
  """Return set of lemma names in word's primary noun synset.
  For nouns there is no similar_to expansion; the group is just the synset's
  own lemma list."""
  s = primary_noun_synset(word)
  if s is None:
    return set()
  return {lem.name().lower() for lem in s.lemmas()}


# ----- zaibacu loading -------------------------------------------------------

def load_thesaurus_pairs(path):
  pairs = set()
  with open(path, encoding="utf-8") as f:
    for line in f:
      try:
        d = json.loads(line)
      except Exception:
        continue
      if d.get("pos") != "noun":
        continue
      w = d.get("word", "").strip().lower()
      syns = [s.strip().lower() for s in d.get("synonyms", []) if s.strip()]
      if not w or not syns:
        continue
      cluster = {w, *syns}
      wl = sorted(cluster)
      for a in range(len(wl)):
        for b in range(a + 1, len(wl)):
          pairs.add(frozenset({wl[a], wl[b]}))
  return pairs


# ----- fastText scoring ------------------------------------------------------

def load_fasttext(path):
  import fasttext
  print(f"loading fastText model from {path} ... (takes ~30s)", file=sys.stderr)
  return fasttext.load_model(path)


def ft_cosine(ft, a, b):
  # fastText treats multi-word tokens as single tokens (subword averaged);
  # leave underscores as-is so multi-word lemmas get a reasonable vector.
  va = np.asarray(ft.get_word_vector(a), dtype=np.float32)
  vb = np.asarray(ft.get_word_vector(b), dtype=np.float32)
  na = float(np.linalg.norm(va))
  nb = float(np.linalg.norm(vb))
  if na == 0.0 or nb == 0.0:
    return 0.0
  return float(np.dot(va, vb) / (na * nb))


def score_for_pair(ft, a, b):
  cos = ft_cosine(ft, a, b)
  return round(max(0.0, min(1.0, (cos + 1.0) / 2.0)), 3)


# ----- apply mode ------------------------------------------------------------

def pick_canonical(a, b):
  """Higher raw zipf wins; tie → alphabetical first."""
  za = zipf_frequency(a.replace("_", " "), "en")
  zb = zipf_frequency(b.replace("_", " "), "en")
  if za > zb:
    return a, b
  if zb > za:
    return b, a
  return (a, b) if a < b else (b, a)


def apply_to_syn(syn_path, add_accepted, new_clusters, dry_run):
  """Append ADD members to matching cluster lines and new-cluster lines at end."""
  with open(syn_path, encoding="utf-8") as f:
    lines = f.readlines()

  adds_by_cid = defaultdict(list)
  for score, present, absent, cid in add_accepted:
    adds_by_cid[cid].append((absent, score))

  out_lines = []
  applied_cids = set()
  add_count = 0
  for line in lines:
    raw = line.rstrip("\n")
    stripped = raw.strip()
    if not stripped or stripped.startswith("#"):
      out_lines.append(line)
      continue
    parts = stripped.split(",")
    cid = parts[0]
    if cid not in adds_by_cid:
      out_lines.append(line)
      continue
    members = []
    i = 1
    while i + 1 < len(parts):
      members.append((parts[i].strip(), float(parts[i + 1])))
      i += 2
    existing_names = {m[0] for m in members}
    for absent, score in adds_by_cid[cid]:
      if absent in existing_names:
        continue
      members.append((absent, score))
      existing_names.add(absent)
      add_count += 1
    members.sort(key=lambda x: -x[1])
    rebuilt = cid + "," + ",".join(f"{w},{s:.2f}" for w, s in members) + "\n"
    out_lines.append(rebuilt)
    applied_cids.add(cid)

  warnings = []
  missing = set(adds_by_cid) - applied_cids
  if missing:
    warnings.append(f"{len(missing)} target CIDs not found in file: {sorted(missing)}")

  if out_lines and not out_lines[-1].endswith("\n"):
    out_lines[-1] += "\n"

  cid_counter = defaultdict(int)
  new_cluster_lines = []
  for score, canonical, other in new_clusters:
    cid_counter[canonical] += 1
    new_cid = f"{canonical.upper()}_NH{cid_counter[canonical]:02d}"
    new_cluster_lines.append(f"{new_cid},{other},{score:.2f}\n")
  out_lines.extend(new_cluster_lines)

  if not dry_run:
    import shutil
    backup = syn_path + ".bak_harvest"
    shutil.copy2(syn_path, backup)
    with open(syn_path, "w", encoding="utf-8") as f:
      f.writelines(out_lines)

  return add_count, len(new_cluster_lines), warnings


def write_soft_pairs(path, soft_pairs, dry_run):
  if dry_run:
    return
  existing = []
  if os.path.exists(path):
    for line in open(path, encoding="utf-8"):
      s = line.strip()
      if s and not s.startswith("#"):
        existing.append(s)
  seen = set()
  for row in existing:
    parts = row.split(",")
    if len(parts) >= 2:
      seen.add(frozenset({parts[0].strip(), parts[1].strip()}))

  new_rows = []
  for score, a, b in soft_pairs:
    key = frozenset({a, b})
    if key in seen:
      continue
    seen.add(key)
    new_rows.append(f"{a},{b},{score:.3f}")

  with open(path, "w", encoding="utf-8") as f:
    f.write("# Tier B soft-axiom noun synonym pairs\n")
    f.write("# Format: word_a,word_b,score  (fastText cosine, [0,1])\n")
    f.write("# Generated by harvest_syn_n.py --apply\n")
    f.write("#\n")
    for row in existing:
      f.write(row + "\n")
    for row in new_rows:
      f.write(row + "\n")


# ----- main flow -------------------------------------------------------------

def main():
  ap = argparse.ArgumentParser(description=__doc__,
                               formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("--syn", default=DEFAULT_SYN, dest="syn_path")
  ap.add_argument("--thesaurus", default=DEFAULT_THESAURUS)
  ap.add_argument("--ft_model", default=DEFAULT_FT_MODEL)
  ap.add_argument("--review_out", default=DEFAULT_REVIEW)
  ap.add_argument("--min_zipf", type=float, default=4.0)
  ap.add_argument("--no_fasttext", action="store_true")
  ap.add_argument("--apply", action="store_true")
  ap.add_argument("--dry_run", action="store_true")
  ap.add_argument("--soft_pairs_out", default=DEFAULT_SOFT_PAIRS)
  ap.add_argument("--min_score_member", type=float,
                  default=DEFAULT_MIN_SCORE_MEMBER)
  ap.add_argument("--min_score_canonical", type=float,
                  default=DEFAULT_MIN_SCORE_CANONICAL)
  args = ap.parse_args()

  cid_to_words, word_to_cids, existing_pairs = load_clusters(args.syn_path)
  print(f"loaded {len(cid_to_words)} clusters from {os.path.basename(args.syn_path)}",
        file=sys.stderr)

  raw_pairs = load_thesaurus_pairs(args.thesaurus)
  new_pairs = raw_pairs - existing_pairs
  print(f"raw pairs in thesaurus: {len(raw_pairs)}; novel vs base: {len(new_pairs)}",
        file=sys.stderr)

  filtered = []
  for p in new_pairs:
    a, b = sorted(p)
    if not (is_common_noun(a, args.min_zipf) and is_common_noun(b, args.min_zipf)):
      continue
    rel = wn_relation(a, b)
    if rel is None:
      continue
    filtered.append((a, b, rel))
  print(f"WordNet-strong candidates at zipf>={args.min_zipf}: {len(filtered)}",
        file=sys.stderr)

  add_candidates = []
  new_seeds = []
  skip_merge = 0
  for a, b, rel in filtered:
    ca, cb = word_to_cids.get(a, set()), word_to_cids.get(b, set())
    if not ca and not cb:
      new_seeds.append((a, b, rel))
    elif ca and cb:
      skip_merge += 1
    else:
      if ca:
        present, absent = a, b
        cids = ca
      else:
        present, absent = b, a
        cids = cb
      for cid in cids:
        add_candidates.append((present, absent, cid, rel))
  print(f"ADD raw: {len(add_candidates)}, NEW seeds: {len(new_seeds)}, "
        f"MERGE (skipped): {skip_merge}", file=sys.stderr)

  # Sense-alignment on ADD: absent's primary noun synset must contain at
  # least one OTHER cluster member besides `present`.
  add_kept = []
  add_rejected = []
  for present, absent, cid, rel in add_candidates:
    members = cid_to_words[cid]
    group = effective_primary_group(absent)
    others = {m for m in members if m != present}
    shared = group & others
    if shared:
      add_kept.append((present, absent, cid, rel, shared))
    else:
      add_rejected.append((present, absent, cid, rel))
  print(f"ADD after sense-alignment: kept {len(add_kept)}, rejected {len(add_rejected)}",
        file=sys.stderr)

  # NEW seeds: require primary-group overlap symmetrically.
  new_kept = []
  for a, b, rel in new_seeds:
    ga = effective_primary_group(a)
    gb = effective_primary_group(b)
    if b in ga or a in gb:
      new_kept.append((a, b, rel))
  print(f"NEW after sense-alignment: kept {len(new_kept)} / {len(new_seeds)}",
        file=sys.stderr)

  ft = None if args.no_fasttext else load_fasttext(args.ft_model)

  def score(a, b):
    if ft is None:
      return None
    return score_for_pair(ft, a, b)

  add_scored = []
  for present, absent, cid, rel, shared in add_kept:
    s = score(present, absent)
    add_scored.append((s if s is not None else 0.0, present, absent, cid, rel, shared))
  add_scored.sort(reverse=True)

  new_scored = []
  for a, b, rel in new_kept:
    s = score(a, b)
    new_scored.append((s if s is not None else 0.0, a, b, rel))
  new_scored.sort(reverse=True)

  with open(args.review_out, "w", encoding="utf-8") as out:
    out.write("Noun synonym harvest — review file\n")
    out.write("=" * 70 + "\n\n")
    out.write(f"Source: {os.path.basename(args.thesaurus)}\n")
    out.write(f"Base cluster file: {os.path.basename(args.syn_path)} "
              f"({len(cid_to_words)} clusters)\n")
    out.write(f"Filter: min_zipf={args.min_zipf}, noun WordNet synset, "
              f"shared noun synset, primary-sense alignment\n")
    out.write(f"Scoring: fastText cc.en.300.bin cosine, rescaled to [0,1]\n\n")
    out.write(f"ADD candidates (kept): {len(add_scored)}\n")
    out.write(f"NEW seeds (kept): {len(new_scored)}\n")
    out.write(f"MERGE (skipped): {skip_merge}\n")
    out.write(f"ADD rejected by sense-alignment: {len(add_rejected)}\n\n")

    out.write("=" * 70 + "\n")
    out.write("ADD — extend an existing cluster with a new word\n")
    out.write("=" * 70 + "\n")
    out.write("format: score  new_word -> existing_word  (cid)  [rel]  shared={...}\n\n")
    for s, present, absent, cid, rel, shared in add_scored:
      shared_str = ",".join(sorted(shared))
      out.write(f"  {s:.3f}  {absent:20s} -> {present:15s} "
                f"({cid})  [{rel}]  shared={{{shared_str}}}\n")

    out.write("\n" + "=" * 70 + "\n")
    out.write("NEW — seed a brand-new cluster (pairwise only)\n")
    out.write("=" * 70 + "\n")
    out.write("format: score  word_a / word_b  [rel]\n\n")
    for s, a, b, rel in new_scored:
      out.write(f"  {s:.3f}  {a} / {b}  [{rel}]\n")

    out.write("\n" + "=" * 70 + "\n")
    out.write("ADD candidates REJECTED by sense-alignment (for reference)\n")
    out.write("=" * 70 + "\n\n")
    for present, absent, cid, rel in sorted(add_rejected):
      members = sorted(cid_to_words[cid])[:6]
      out.write(f"  {absent:20s} -> {present:15s} "
                f"({cid})  [{rel}]  cluster={members}\n")

  print(f"\nreview written to {args.review_out}", file=sys.stderr)

  if args.apply:
    add_accepted = [
      (s, present, absent, cid)
      for (s, present, absent, cid, rel, shared) in add_scored
      if s >= args.min_score_member
    ]
    new_canonical = []
    new_stash = []
    for s, a, b, rel in new_scored:
      if s >= args.min_score_canonical:
        canonical, other = pick_canonical(a, b)
        new_canonical.append((s, canonical, other))
      elif s >= args.min_score_member:
        new_stash.append((s, a, b))

    print(f"\n--- apply plan (min_member={args.min_score_member}, "
          f"min_canonical={args.min_score_canonical}) ---", file=sys.stderr)
    print(f"ADD members to accept: {len(add_accepted)}", file=sys.stderr)
    print(f"NEW clusters to create: {len(new_canonical)}", file=sys.stderr)
    print(f"NEW pairs to stash (soft): {len(new_stash)}", file=sys.stderr)

    add_count, new_count, warnings = apply_to_syn(
        args.syn_path, add_accepted, new_canonical, args.dry_run)
    for w in warnings:
      print(f"  WARNING: {w}", file=sys.stderr)
    write_soft_pairs(args.soft_pairs_out, new_stash, args.dry_run)

    if args.dry_run:
      print(f"DRY RUN — no files modified", file=sys.stderr)
    else:
      print(f"applied: {add_count} new members to existing clusters, "
            f"{new_count} new clusters appended to {os.path.basename(args.syn_path)}",
            file=sys.stderr)
      print(f"soft pairs written to {os.path.basename(args.soft_pairs_out)}",
            file=sys.stderr)
      print(f"backup: {os.path.basename(args.syn_path)}.bak_harvest", file=sys.stderr)

  return 0


if __name__ == "__main__":
  sys.exit(main())
