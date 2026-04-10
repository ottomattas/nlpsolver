#!/usr/bin/env python3
"""
Policy C canonical selection for adjective synonym clusters in syn_a_10.txt.

For each cluster:
  - winner is FIXED to the current CID canonical (never replaced)
  - compute POS-weighted zipf: adj_zipf(w) = zipf(w) * (adj_synsets/total_synsets)
  - winner-level gate: adj_zipf(winner) >= MIN_ADJ_ZIPF, else UNSAFE_LOW
  - winner-level sense check: winner's effective-primary adj synset group
    (rank 0 with lonely-head skip + similar_tos expansion) must contain at
    least one other cluster word, else UNSAFE_WEIRD
  - per-member (SAFE clusters only): each listed member must pass the same
    primary-sense alignment rule against the other cluster words; members
    that fail get marked DROP. Protected exception: any member that is
    itself the canonical of some cluster stays SAFE (rule 5).
  - the canonical itself is never dropped (rule 4).

Default: writes syn_a_canonicals_review.txt.
With --apply: also rewrites syn_a_10.txt with dropped members removed from
SAFE clusters (UNSAFE clusters left untouched). Backup is written to
syn_a_10.txt.bak_drops before modification.

Run:
    mkdata/venv/bin/python pick_canonicals_a.py                # review only
    mkdata/venv/bin/python pick_canonicals_a.py --apply        # apply drops
    mkdata/venv/bin/python pick_canonicals_a.py --apply --dry_run
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict

from nltk.corpus import wordnet as wn
from wordfreq import zipf_frequency


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SYN_A = os.path.join(SCRIPT_DIR, "syn_a_10.txt")
DEFAULT_REVIEW = os.path.join(SCRIPT_DIR, "syn_a_canonicals_review.txt")
DEFAULT_REWRITE = os.path.join(SCRIPT_DIR, "syn_a_rewrite.txt")
DEFAULT_SOFT_AXIOMS = os.path.join(SCRIPT_DIR, "syn_a_soft_axioms.txt")
DEFAULT_SOFT_PAIRS_IN = os.path.join(SCRIPT_DIR, "syn_a_soft_pairs.txt")
MIN_ADJ_ZIPF = 3.0


# ----- WordNet helpers -------------------------------------------------------

def adj_synsets(w):
  return [s for s in wn.synsets(w) if s.pos() in ("a", "s")]


def adj_zipf(w):
  """POS-weighted zipf: zipf(w) * (adj_synsets / all_synsets)."""
  all_syns = wn.synsets(w)
  if not all_syns:
    return 0.0
  n_adj = sum(1 for s in all_syns if s.pos() in ("a", "s"))
  return zipf_frequency(w, "en") * (n_adj / len(all_syns))


def is_lonely_head(syn):
  """Head adj synset with <=1 lemma and no similar_tos — structural placeholder."""
  if syn.pos() != "a":
    return False
  if len(syn.lemmas()) > 1:
    return False
  return not syn.similar_tos()


def effective_primary_group(word):
  """Set of lemma names in word's effective-primary adj synset group.

  Rank 0 normally, falling through to rank 1 if rank 0 is a lonely head.
  The group is always {head + all satellites} of the head cluster that
  primary belongs to. If primary is a satellite (pos='s'), we resolve to
  the head first, then collect every satellite hanging off that head."""
  syns = adj_synsets(word)
  if not syns:
    return set()
  primary = syns[0]
  if is_lonely_head(primary) and len(syns) > 1:
    primary = syns[1]

  if primary.pos() == "s":
    heads = primary.similar_tos()  # satellite -> head(s)
    if heads:
      group_syns = set()
      for h in heads:
        group_syns.add(h)
        group_syns.update(h.similar_tos())  # head -> sister satellites
    else:
      group_syns = {primary}
  else:
    group_syns = {primary, *primary.similar_tos()}

  lemmas = set()
  for s in group_syns:
    for lem in s.lemmas():
      lemmas.add(lem.name().lower())
  return lemmas


def primary_matches_cluster(word, other_words):
  """True if word's effective-primary adj group contains any of other_words."""
  if not other_words:
    return False
  return bool(effective_primary_group(word) & set(other_words))


# ----- cluster file I/O ------------------------------------------------------

def load_clusters(path):
  """Return list of (cid, canonical, listed_members, line_index, raw_line)."""
  out = []
  with open(path, encoding="utf-8") as f:
    for idx, raw in enumerate(f):
      line = raw.rstrip("\n")
      stripped = line.strip()
      if not stripped or stripped.startswith("#"):
        continue
      parts = stripped.split(",")
      cid = parts[0]
      canon = cid.rsplit("_", 1)[0].lower()
      listed = []
      i = 1
      while i + 1 < len(parts):
        word = parts[i].strip()
        score = parts[i + 1].strip()
        if word:
          listed.append((word, score))
        i += 2
      out.append((cid, canon, listed, idx, line))
  return out


def canonical_set_from(clusters):
  return {canon for (_cid, canon, _m, _i, _r) in clusters}


# ----- classification --------------------------------------------------------

def classify(cid, canonical, listed_members, canonical_set):
  """Return dict with keys: status, winner_zipf, safe, dropped.
  'safe' and 'dropped' are lists of listed member words (not the canonical)."""
  winner = canonical
  wz = adj_zipf(winner)

  # Winner gate: adj_zipf threshold
  if wz < MIN_ADJ_ZIPF:
    return {"status": "UNSAFE_LOW", "winner_zipf": wz, "safe": [], "dropped": []}

  # All cluster words = canonical + listed members
  all_words = [canonical] + [w for (w, _s) in listed_members]

  # Winner-level sense alignment
  winner_others = [w for w in all_words if w != winner]
  if not primary_matches_cluster(winner, winner_others):
    return {"status": "UNSAFE_WEIRD", "winner_zipf": wz, "safe": [], "dropped": []}

  # Per-member check
  safe, dropped = [], []
  for word, _score in listed_members:
    if word in canonical_set:
      safe.append(word)     # rule 5: canonical-set protection
      continue
    others = [w for w in all_words if w != word]
    if primary_matches_cluster(word, others):
      safe.append(word)
    else:
      dropped.append(word)

  # Safety fallback: if ALL listed members would be dropped, Policy C has
  # no signal for this cluster — treat as UNSAFE and leave it untouched
  # instead of deleting the cluster entirely.
  if listed_members and not safe:
    return {"status": "UNSAFE_NODROP", "winner_zipf": wz, "safe": [], "dropped": []}

  return {"status": "SAFE", "winner_zipf": wz, "safe": safe, "dropped": dropped}


# ----- review file writer ----------------------------------------------------

def write_review(path, clusters, classifications):
  counts = defaultdict(int)
  for c in classifications:
    counts[c["status"]] += 1

  with open(path, "w", encoding="utf-8") as f:
    f.write("Tier A adjective canonicals — review file\n")
    f.write("=" * 70 + "\n\n")
    f.write("Policy C (POS-weighted zipf + primary-sense + per-member safety)\n")
    f.write(f"Base: syn_a_10.txt with {len(clusters)} clusters\n")
    f.write(f"Winner gate: adj_zipf >= {MIN_ADJ_ZIPF} (winner fixed to CID canonical)\n\n")
    f.write(f"Totals:\n")
    f.write(f"  SAFE          : {counts['SAFE']}\n")
    f.write(f"  UNSAFE_WEIRD  : {counts['UNSAFE_WEIRD']}\n")
    f.write(f"  UNSAFE_LOW    : {counts['UNSAFE_LOW']}\n")
    f.write(f"  UNSAFE_NODROP : {counts['UNSAFE_NODROP']}  "
            f"(all members would drop — cluster left untouched)\n\n")

    n_drops = sum(len(c["dropped"]) for c in classifications)
    f.write(f"Total listed members to drop across SAFE clusters: {n_drops}\n\n")

    f.write("=" * 70 + "\n")
    f.write("SAFE — Tier A clusters (drops will be applied with --apply)\n")
    f.write("=" * 70 + "\n\n")
    for (cid, canon, listed, _idx, _raw), cls in zip(clusters, classifications):
      if cls["status"] != "SAFE":
        continue
      f.write(f"  {cid:22s} {canon:13s} -> {canon:13s} "
              f"adj_zipf={cls['winner_zipf']:.2f}\n")
      if cls["safe"]:
        f.write(f"    SAFE:    {', '.join(cls['safe'])}\n")
      if cls["dropped"]:
        f.write(f"    DROP:    {', '.join(cls['dropped'])}\n")
      members_str = ", ".join(f"{w}({s})" for (w, s) in listed)
      f.write(f"    MEMBERS: {members_str}\n\n")

    f.write("\n" + "=" * 70 + "\n")
    f.write("UNSAFE_WEIRD — winner's primary sense not in cluster (no drops)\n")
    f.write("=" * 70 + "\n\n")
    for (cid, canon, listed, _idx, _raw), cls in zip(clusters, classifications):
      if cls["status"] != "UNSAFE_WEIRD":
        continue
      f.write(f"  {cid:22s} {canon:13s}  adj_zipf={cls['winner_zipf']:.2f}\n")
      f.write(f"    members: {', '.join(w for (w, _s) in listed)}\n")

    f.write("\n" + "=" * 70 + "\n")
    f.write(f"UNSAFE_LOW — winner adj_zipf < {MIN_ADJ_ZIPF} (no drops)\n")
    f.write("=" * 70 + "\n\n")
    for (cid, canon, listed, _idx, _raw), cls in zip(clusters, classifications):
      if cls["status"] != "UNSAFE_LOW":
        continue
      f.write(f"  {cid:22s} {canon:13s}  adj_zipf={cls['winner_zipf']:.2f}\n")


# ----- apply drops to syn_a_10.txt ------------------------------------------

def apply_drops(syn_a_path, clusters, classifications, dry_run):
  """Rewrite cluster lines with SAFE-cluster DROP members removed.
  UNSAFE clusters are left untouched. Returns (lines_modified, members_dropped,
  clusters_emptied)."""
  with open(syn_a_path, encoding="utf-8") as f:
    raw_lines = f.readlines()

  # Build a map from line index -> updated line (only for SAFE clusters with drops)
  updates = {}
  lines_modified = 0
  members_dropped = 0
  emptied = []

  for (cid, canon, listed, idx, raw_line), cls in zip(clusters, classifications):
    if cls["status"] != "SAFE":
      continue
    drop_set = set(cls["dropped"])
    if not drop_set:
      continue
    kept = [(w, s) for (w, s) in listed if w not in drop_set]
    members_dropped += len(listed) - len(kept)
    lines_modified += 1
    if not kept:
      emptied.append(cid)
      # Skip the cluster entirely (cannot be represented with empty members)
      updates[idx] = None
    else:
      rebuilt = cid + "," + ",".join(f"{w},{s}" for (w, s) in kept) + "\n"
      updates[idx] = rebuilt

  out_lines = []
  for i, line in enumerate(raw_lines):
    if i in updates:
      repl = updates[i]
      if repl is not None:
        out_lines.append(repl)
      # else: drop the entire line
    else:
      out_lines.append(line)

  if not dry_run:
    import shutil
    backup = syn_a_path + ".bak_drops"
    shutil.copy2(syn_a_path, backup)
    with open(syn_a_path, "w", encoding="utf-8") as f:
      f.writelines(out_lines)

  return lines_modified, members_dropped, emptied


# ----- emit Tier A / Tier B files --------------------------------------------

def emit_tier_a(clusters, classifications, canonical_set, out_path):
  """Write syn_a_rewrite.txt: member -> canonical for SAFE members of SAFE
  clusters. Members that are themselves canonicals (of any cluster) are
  skipped so canonicals never get rewritten. On ambiguity (member appears
  as SAFE in multiple SAFE clusters with different canonicals), pick the
  mapping with the highest member score. Returns (n_entries, n_ambiguous)."""
  entries = defaultdict(list)   # member -> list of (canonical, score, cid)
  for (cid, canon, listed, _i, _r), cls in zip(clusters, classifications):
    if cls["status"] != "SAFE":
      continue
    safe_set = set(cls["safe"])
    for m, s_str in listed:
      if m not in safe_set:
        continue
      if m in canonical_set:
        continue
      try:
        score = float(s_str)
      except ValueError:
        score = 0.0
      entries[m].append((canon, score, cid))

  resolved = {}
  n_ambiguous = 0
  for m, cands in entries.items():
    unique_canons = {c for (c, _s, _cid) in cands}
    if len(unique_canons) > 1:
      n_ambiguous += 1
    cands.sort(key=lambda x: -x[1])
    resolved[m] = cands[0]  # (canonical, score, cid)

  with open(out_path, "w", encoding="utf-8") as f:
    f.write("# syn_a_rewrite.txt — Tier A hard-rewrite lookup\n")
    f.write("# Source: pick_canonicals_a.py --emit (Policy C on syn_a_10.txt)\n")
    f.write("# Members that are themselves canonicals of any cluster are not\n")
    f.write("# emitted. On ambiguity across SAFE clusters, highest member score wins.\n")
    f.write("# Format: member,canonical\n")
    f.write("#\n")
    for m in sorted(resolved):
      canon, _sc, _cid = resolved[m]
      f.write(f"{m},{canon}\n")
  return len(resolved), n_ambiguous


def emit_tier_b(clusters, classifications, soft_pairs_in, out_path):
  """Write syn_a_soft_axioms.txt: pair list for Tier B biconditionals.
  Sources:
    - all UNSAFE cluster canonical↔member pairs (with score from syn_a_10.txt)
    - all pairs from syn_a_soft_pairs.txt (harvested sub-canonical stash)
  Dedupe by unordered pair; on dup, higher score wins.
  Returns (from_unsafe, from_harvest_new, total)."""
  pairs = {}  # frozenset -> (w_a, w_b, score)

  for (cid, canon, listed, _i, _r), cls in zip(clusters, classifications):
    if cls["status"] == "SAFE":
      continue
    for m, s_str in listed:
      try:
        score = float(s_str)
      except ValueError:
        score = 0.0
      key = frozenset({canon, m})
      if key in pairs:
        if pairs[key][2] < score:
          pairs[key] = (canon, m, score)
      else:
        pairs[key] = (canon, m, score)
  from_unsafe = len(pairs)

  from_harvest_new = 0
  if os.path.exists(soft_pairs_in):
    for line in open(soft_pairs_in, encoding="utf-8"):
      s = line.strip()
      if not s or s.startswith("#"):
        continue
      parts = s.split(",")
      if len(parts) != 3:
        continue
      a, b, sc_str = parts[0].strip(), parts[1].strip(), parts[2].strip()
      try:
        score = float(sc_str)
      except ValueError:
        continue
      key = frozenset({a, b})
      if key in pairs:
        if pairs[key][2] < score:
          pairs[key] = (a, b, score)
      else:
        pairs[key] = (a, b, score)
        from_harvest_new += 1

  with open(out_path, "w", encoding="utf-8") as f:
    f.write("# syn_a_soft_axioms.txt — Tier B soft biconditional axiom candidates\n")
    f.write("# Generated by pick_canonicals_a.py --emit\n")
    f.write("# Sources: UNSAFE cluster (canonical,member) pairs from syn_a_10.txt\n")
    f.write("#          + syn_a_soft_pairs.txt (harvested sub-canonical pairs)\n")
    f.write("# Format: word_a,word_b,score\n")
    f.write("#\n")
    rows = sorted(pairs.values(), key=lambda x: (-x[2], x[0], x[1]))
    for a, b, s in rows:
      f.write(f"{a},{b},{s:.2f}\n")
  return from_unsafe, from_harvest_new, len(pairs)


# ----- main flow -------------------------------------------------------------

def main():
  ap = argparse.ArgumentParser(description=__doc__,
                               formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("--syn_a", default=DEFAULT_SYN_A)
  ap.add_argument("--review_out", default=DEFAULT_REVIEW)
  ap.add_argument("--apply", action="store_true",
                  help="rewrite syn_a_10.txt with SAFE-cluster drops applied")
  ap.add_argument("--dry_run", action="store_true",
                  help="with --apply: print counts only, do not write")
  ap.add_argument("--emit", action="store_true",
                  help="emit syn_a_rewrite.txt (Tier A) and "
                       "syn_a_soft_axioms.txt (Tier B)")
  ap.add_argument("--rewrite_out", default=DEFAULT_REWRITE)
  ap.add_argument("--soft_axioms_out", default=DEFAULT_SOFT_AXIOMS)
  ap.add_argument("--soft_pairs_in", default=DEFAULT_SOFT_PAIRS_IN)
  args = ap.parse_args()

  clusters = load_clusters(args.syn_a)
  print(f"loaded {len(clusters)} clusters from {os.path.basename(args.syn_a)}",
        file=sys.stderr)

  canonical_set = canonical_set_from(clusters)
  print(f"canonical set size: {len(canonical_set)}", file=sys.stderr)

  classifications = []
  for (cid, canon, listed, _idx, _raw) in clusters:
    classifications.append(classify(cid, canon, listed, canonical_set))

  counts = defaultdict(int)
  for c in classifications:
    counts[c["status"]] += 1
  total_drops = sum(len(c["dropped"]) for c in classifications)
  print(f"  SAFE={counts['SAFE']}, UNSAFE_WEIRD={counts['UNSAFE_WEIRD']}, "
        f"UNSAFE_LOW={counts['UNSAFE_LOW']}, "
        f"UNSAFE_NODROP={counts['UNSAFE_NODROP']}", file=sys.stderr)
  print(f"  total DROP members across SAFE: {total_drops}", file=sys.stderr)

  write_review(args.review_out, clusters, classifications)
  print(f"review written to {args.review_out}", file=sys.stderr)

  if args.apply:
    lines_mod, members_dropped, emptied = apply_drops(
        args.syn_a, clusters, classifications, args.dry_run)
    print(f"\n--- apply {'(DRY RUN)' if args.dry_run else ''} ---", file=sys.stderr)
    print(f"cluster lines modified: {lines_mod}", file=sys.stderr)
    print(f"listed members removed: {members_dropped}", file=sys.stderr)
    if emptied:
      print(f"clusters whose listed members were ALL dropped "
            f"(entire line removed): {len(emptied)}", file=sys.stderr)
      for cid in emptied:
        print(f"    {cid}", file=sys.stderr)
    if not args.dry_run:
      print(f"backup: {os.path.basename(args.syn_a)}.bak_drops", file=sys.stderr)

  if args.emit:
    n_a, n_ambig = emit_tier_a(clusters, classifications, canonical_set,
                               args.rewrite_out)
    from_unsafe, from_harvest, total_b = emit_tier_b(
        clusters, classifications, args.soft_pairs_in, args.soft_axioms_out)
    print(f"\n--- emit ---", file=sys.stderr)
    print(f"Tier A ({os.path.basename(args.rewrite_out)}): "
          f"{n_a} member→canonical mappings", file=sys.stderr)
    if n_ambig:
      print(f"  ({n_ambig} members had multiple SAFE canonicals; "
            f"highest-score mapping used)", file=sys.stderr)
    print(f"Tier B ({os.path.basename(args.soft_axioms_out)}): "
          f"{total_b} pairs total", file=sys.stderr)
    print(f"  from UNSAFE clusters (canon↔member): {from_unsafe}", file=sys.stderr)
    print(f"  from harvest stash (new pairs): {from_harvest}", file=sys.stderr)
  return 0


if __name__ == "__main__":
  sys.exit(main())
