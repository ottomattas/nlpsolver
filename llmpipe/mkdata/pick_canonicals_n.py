#!/usr/bin/env python3
"""
Policy C canonical selection for NOUN synonym clusters in syn_n_10.txt.

Parallel to pick_canonicals_a.py but specialised for nouns:
  * POS-weighted zipf: noun_zipf(w) = zipf(w) * (noun_synsets / all_synsets)
  * primary-sense group = lemmas of w's first noun synset (no similar_to /
    satellite expansion — those don't exist for nouns)
  * WordNet hypernym/hyponym chains are intentionally NOT used: we want
    strict synonymy, not taxonomy.

For each cluster:
  - winner is FIXED to the current CID canonical (never replaced)
  - winner-level gate: noun_zipf(winner) >= MIN_ZIPF, else UNSAFE_LOW
  - winner-level sense check: winner's primary noun synset must contain at
    least one other cluster word, else UNSAFE_WEIRD
  - per-member (SAFE clusters only): each listed member must share a primary
    noun synset with at least one of the other cluster words; members that
    fail get marked DROP. Protected exception: any member that is itself the
    canonical of some cluster stays SAFE (rule 5).
  - the canonical itself is never dropped (rule 4).

Default: writes syn_n_canonicals_review.txt.
With --apply: also rewrites syn_n_10.txt with dropped members removed from
SAFE clusters (UNSAFE clusters left untouched). Backup: syn_n_10.txt.bak_drops.
With --emit: also writes syn_n_rewrite.txt and syn_n_soft_axioms.txt.

Run:
    mkdata/venv/bin/python pick_canonicals_n.py                # review only
    mkdata/venv/bin/python pick_canonicals_n.py --apply        # apply drops
    mkdata/venv/bin/python pick_canonicals_n.py --apply --emit # + Tier A/B
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict

from nltk.corpus import wordnet as wn
from wordfreq import zipf_frequency


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SYN = os.path.join(SCRIPT_DIR, "syn_n_10.txt")
DEFAULT_REVIEW = os.path.join(SCRIPT_DIR, "syn_n_canonicals_review.txt")
DEFAULT_REWRITE = os.path.join(SCRIPT_DIR, "syn_n_rewrite.txt")
DEFAULT_SOFT_AXIOMS = os.path.join(SCRIPT_DIR, "syn_n_soft_axioms.txt")
DEFAULT_SOFT_PAIRS_IN = os.path.join(SCRIPT_DIR, "syn_n_soft_pairs.txt")
# Winner absolute gate: raw zipf of the canonical must be at least this.
MIN_ZIPF = 4.0
# Canonical must be a noun at least this fraction of the time across WordNet
# synsets. Kills canonicals like 'one' (2/9 noun), 'funny' (1/5), 'separate'
# (2/19), 'helping' (1/9) whose raw frequency comes overwhelmingly from
# non-noun uses. Note: structure-based, NOT usage-based — noun-verb pairs
# like 'murder' (1/3) and 'building' (4/14) still pass at 0.25.
MIN_NOUN_FRACTION = 0.25
# Raw-zipf dominance margin: the canonical must be at least this much more
# frequent than the member in raw zipf. Prevents rewrites where the member
# and canonical have similar textual standing (e.g. 'america→usa',
# 'autopsy→pm', 'free_energy→energy').
MIN_DOMINANCE_MARGIN = 0.5
# Per-member absolute zipf floor. Filters out archaic or specialised member
# words whose rewrite rule would be clutter (e.g. 'acquirement', 'privation',
# 'yesteryear', 'offprint', 'nipper'). Members below this threshold are
# dropped to Tier B soft axioms.
MIN_MEMBER_ZIPF = 3.3
# Winner's cluster-matching synset max rank. 0 = strict (only primary sense
# of the winner word matches the cluster). Strict mode avoids polysemy traps
# like HOUSE_N02 (rank 1 'firm' sense) that would produce bad Tier A
# rewrites such as 'firm → house'.
MAX_WINNER_SENSE_RANK = 0
# Per-member max noun synsets. Polysemous members (many noun senses) are
# dangerous to hard-rewrite because the rewrite will be wrong for most of
# the member's senses. E.g. 'spot' (14 noun synsets) → 'place' catches only
# one sense. Low-synset members like 'automobile' (1) or 'tale' (2) are safe.
MAX_MEMBER_NOUN_SYNSETS = 3
# Per-member minimum fastText cosine similarity to the canonical. Ensures
# the member is semantically close enough for an unconditional rewrite.
MIN_MEMBER_SIMILARITY = 0.88
# Explicit blocklist for (member, canonical) pairs that pass all automatic
# gates but are still bad rewrites. Proper nouns, religious terms, person
# names, political entities, semantic mismatches.
BLOCKED_PAIRS = {
    ("fl", "florida"),
    ("nj", "jersey"),
    ("savior", "jesus"),
    ("saviour", "jesus"),
    ("slew", "lot"),
    ("null", "nothing"),
    ("nil", "nothing"),
    ("madonna", "mary"),
    ("simon_peter", "peter"),
    ("hank_williams", "williams"),
    ("john_roy_major", "john_major"),
    ("soviet_union", "russia"),
    ("ussr", "russia"),
    ("almighty", "lord"),
    ("creator", "lord"),
    ("divine", "lord"),
    ("second_coming_of_christ", "second_coming"),
    ("shield_of_david", "star_of_david"),
}


# ----- WordNet helpers -------------------------------------------------------

def noun_synsets(w):
  return wn.synsets(w, pos="n")


def noun_zipf(w):
  """Raw zipf frequency. Used for the absolute winner gate and for the
  canonical-vs-member dominance margin."""
  return zipf_frequency(w.replace("_", " "), "en")


def noun_fraction(w):
  """Fraction of w's WordNet synsets that are nouns. Structure-based
  signal for 'is this word mostly a noun' — independent of corpus
  frequency. A canonical with low noun_fraction (e.g. 'one' at 2/9,
  'funny' at 1/5, 'separate' at 2/19) produces bad rewrites because its
  real-world usage is mostly as something else (pronoun/adj/verb)."""
  all_s = wn.synsets(w)
  if not all_s:
    return 0.0
  n_noun = sum(1 for s in all_s if s.pos() == "n")
  return n_noun / len(all_s)


def primary_synset_lemmas(word):
  """Lemma names of word's primary (rank-0) noun synset, or empty set."""
  syns = noun_synsets(word)
  if not syns:
    return set()
  return {lem.name().lower() for lem in syns[0].lemmas()}


def primary_matches_cluster(word, other_words):
  """True if word's PRIMARY noun synset contains any of other_words.
  Used for the strict per-member drop check (Tier A safety)."""
  if not other_words:
    return False
  return bool(primary_synset_lemmas(word) & set(other_words))


def winner_match(word, other_words):
  """Return (rank, synset) for the lowest-ranked noun synset of word that
  contains any of other_words. (None, None) if no match. The returned
  synset is the 'cluster-matching synset' — the WordNet synset that best
  represents the cluster's intended sense for the winner."""
  if not other_words:
    return None, None
  other_set = set(other_words)
  for rank, s in enumerate(noun_synsets(word)):
    lemmas = {lem.name().lower() for lem in s.lemmas()}
    if lemmas & other_set:
      return rank, s
  return None, None


def member_primary_in_synset(member, synset):
  """True if member's PRIMARY noun synset equals `synset`. This is the
  strict Tier A safety check: a member is only rewritten to the canonical
  if the member's dominant WordNet sense is exactly the cluster sense."""
  syns = noun_synsets(member)
  if not syns:
    return False
  return syns[0] == synset


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
  winner = canonical
  wz = noun_zipf(winner)

  if wz < MIN_ZIPF:
    return {"status": "UNSAFE_LOW", "winner_zipf": wz, "safe": [], "dropped": []}

  # Canonical must be structurally mostly a noun. Kills 'one, funny,
  # separate, helping'-style canonicals whose non-noun senses dominate.
  if noun_fraction(winner) < MIN_NOUN_FRACTION:
    return {"status": "UNSAFE_POS", "winner_zipf": wz, "safe": [], "dropped": []}

  all_words = [canonical] + [w for (w, _s) in listed_members]

  winner_others = [w for w in all_words if w != winner]
  wrank, winner_synset = winner_match(winner, winner_others)
  if wrank is None or wrank > MAX_WINNER_SENSE_RANK:
    return {"status": "UNSAFE_WEIRD", "winner_zipf": wz,
            "winner_rank": wrank, "safe": [], "dropped": []}

  # Strict member check. A member is SAFE only if ALL of:
  #   (a) it is itself the canonical of another cluster (rule 5 protection),
  #       OR
  #   (b1) its primary noun synset equals the winner's cluster-matching
  #        synset (strict WordNet sense equality — guards polysemy), AND
  #   (b2) its raw zipf is above MIN_MEMBER_ZIPF (archaic member filter), AND
  #   (b3) the canonical's raw zipf is higher than the member's by at least
  #        MIN_DOMINANCE_MARGIN (the rewrite must be toward a notably more
  #        common word — catches 'america→usa', 'free_energy→energy',
  #        'autopsy→pm', 'calling→career').
  safe, dropped = [], []
  for word, score_str in listed_members:
    if word in canonical_set:
      safe.append(word)
      continue
    if (word, canonical) in BLOCKED_PAIRS:
      dropped.append(word)
      continue
    if not member_primary_in_synset(word, winner_synset):
      dropped.append(word)
      continue
    mz = noun_zipf(word)
    if mz < MIN_MEMBER_ZIPF:
      dropped.append(word)
      continue
    if wz - mz < MIN_DOMINANCE_MARGIN:
      dropped.append(word)
      continue
    if len(noun_synsets(word)) > MAX_MEMBER_NOUN_SYNSETS:
      dropped.append(word)
      continue
    try:
      sim = float(score_str)
    except ValueError:
      sim = 0.0
    if sim < MIN_MEMBER_SIMILARITY:
      dropped.append(word)
      continue
    safe.append(word)

  if listed_members and not safe:
    return {"status": "UNSAFE_NODROP", "winner_zipf": wz, "safe": [], "dropped": []}

  return {"status": "SAFE", "winner_zipf": wz, "safe": safe, "dropped": dropped}


# ----- review file writer ----------------------------------------------------

def write_review(path, clusters, classifications):
  counts = defaultdict(int)
  for c in classifications:
    counts[c["status"]] += 1

  with open(path, "w", encoding="utf-8") as f:
    f.write("Tier A noun canonicals — review file\n")
    f.write("=" * 70 + "\n\n")
    f.write("Policy C for nouns (POS-weighted zipf + primary noun synset match)\n")
    f.write(f"Base: syn_n_10.txt with {len(clusters)} clusters\n")
    f.write(f"Winner gate: noun_zipf >= {MIN_ZIPF} (winner fixed to CID canonical)\n\n")
    f.write(f"Totals:\n")
    f.write(f"  SAFE          : {counts['SAFE']}\n")
    f.write(f"  UNSAFE_WEIRD  : {counts['UNSAFE_WEIRD']}\n")
    f.write(f"  UNSAFE_LOW    : {counts['UNSAFE_LOW']}\n")
    f.write(f"  UNSAFE_POS    : {counts['UNSAFE_POS']}\n")
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
      f.write(f"  {cid:26s} {canon:18s} -> {canon:18s} "
              f"noun_zipf={cls['winner_zipf']:.2f}\n")
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
      f.write(f"  {cid:26s} {canon:18s}  noun_zipf={cls['winner_zipf']:.2f}\n")
      f.write(f"    members: {', '.join(w for (w, _s) in listed)}\n")

    f.write("\n" + "=" * 70 + "\n")
    f.write(f"UNSAFE_LOW — winner noun_zipf < {MIN_ZIPF} (no drops)\n")
    f.write("=" * 70 + "\n\n")
    for (cid, canon, listed, _idx, _raw), cls in zip(clusters, classifications):
      if cls["status"] != "UNSAFE_LOW":
        continue
      f.write(f"  {cid:26s} {canon:18s}  noun_zipf={cls['winner_zipf']:.2f}\n")

    f.write("\n" + "=" * 70 + "\n")
    f.write(f"UNSAFE_POS — canonical noun_fraction < {MIN_NOUN_FRACTION} (no drops)\n")
    f.write("=" * 70 + "\n\n")
    for (cid, canon, listed, _idx, _raw), cls in zip(clusters, classifications):
      if cls["status"] != "UNSAFE_POS":
        continue
      nf = noun_fraction(canon)
      f.write(f"  {cid:26s} {canon:18s}  noun_fraction={nf:.2f}\n")

    f.write("\n" + "=" * 70 + "\n")
    f.write("UNSAFE_NODROP — all listed members would fail the sense check\n")
    f.write("=" * 70 + "\n\n")
    for (cid, canon, listed, _idx, _raw), cls in zip(clusters, classifications):
      if cls["status"] != "UNSAFE_NODROP":
        continue
      f.write(f"  {cid:26s} {canon:18s}  noun_zipf={cls['winner_zipf']:.2f}\n")
      f.write(f"    members: {', '.join(w for (w, _s) in listed)}\n")


# ----- apply drops to syn_n_10.txt -------------------------------------------

def apply_drops(syn_path, clusters, classifications, dry_run):
  with open(syn_path, encoding="utf-8") as f:
    raw_lines = f.readlines()

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
    else:
      out_lines.append(line)

  if not dry_run:
    import shutil
    backup = syn_path + ".bak_drops"
    shutil.copy2(syn_path, backup)
    with open(syn_path, "w", encoding="utf-8") as f:
      f.writelines(out_lines)

  return lines_modified, members_dropped, emptied


# ----- emit Tier A / Tier B files --------------------------------------------

def emit_tier_a(clusters, classifications, canonical_set, out_path):
  entries = defaultdict(list)
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
    resolved[m] = cands[0]

  with open(out_path, "w", encoding="utf-8") as f:
    f.write("# syn_n_rewrite.txt — Tier A hard-rewrite lookup\n")
    f.write("# Source: pick_canonicals_n.py --emit (Policy C on syn_n_10.txt)\n")
    f.write("# Members that are themselves canonicals of any cluster are not\n")
    f.write("# emitted. On ambiguity across SAFE clusters, highest member score wins.\n")
    f.write("# Format: member,canonical\n")
    f.write("#\n")
    for m in sorted(resolved):
      canon, _sc, _cid = resolved[m]
      f.write(f"{m},{canon}\n")
  return len(resolved), n_ambiguous


def emit_tier_b(clusters, classifications, soft_pairs_in, out_path):
  pairs = {}

  # UNSAFE clusters: emit all canonical↔member pairs as soft axioms.
  # SAFE clusters: emit canonical↔dropped-member pairs (these failed strict
  # Tier A safety but still carry a weaker synonymy signal).
  for (cid, canon, listed, _i, _r), cls in zip(clusters, classifications):
    if cls["status"] == "SAFE":
      drop_set = set(cls["dropped"])
      emit_members = [(m, s) for (m, s) in listed if m in drop_set]
    else:
      emit_members = listed
    for m, s_str in emit_members:
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
    f.write("# syn_n_soft_axioms.txt — Tier B soft biconditional axiom candidates\n")
    f.write("# Generated by pick_canonicals_n.py --emit\n")
    f.write("# Sources: UNSAFE cluster (canonical,member) pairs from syn_n_10.txt\n")
    f.write("#          + syn_n_soft_pairs.txt (harvested sub-canonical pairs)\n")
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
  ap.add_argument("--syn", default=DEFAULT_SYN, dest="syn_path")
  ap.add_argument("--review_out", default=DEFAULT_REVIEW)
  ap.add_argument("--apply", action="store_true")
  ap.add_argument("--dry_run", action="store_true")
  ap.add_argument("--emit", action="store_true")
  ap.add_argument("--rewrite_out", default=DEFAULT_REWRITE)
  ap.add_argument("--soft_axioms_out", default=DEFAULT_SOFT_AXIOMS)
  ap.add_argument("--soft_pairs_in", default=DEFAULT_SOFT_PAIRS_IN)
  args = ap.parse_args()

  clusters = load_clusters(args.syn_path)
  print(f"loaded {len(clusters)} clusters from {os.path.basename(args.syn_path)}",
        file=sys.stderr)

  canonical_set = canonical_set_from(clusters)
  print(f"canonical set size: {len(canonical_set)}", file=sys.stderr)

  classifications = [classify(cid, canon, listed, canonical_set)
                     for (cid, canon, listed, _idx, _raw) in clusters]

  counts = defaultdict(int)
  for c in classifications:
    counts[c["status"]] += 1
  total_drops = sum(len(c["dropped"]) for c in classifications)
  print(f"  SAFE={counts['SAFE']}, UNSAFE_WEIRD={counts['UNSAFE_WEIRD']}, "
        f"UNSAFE_LOW={counts['UNSAFE_LOW']}, UNSAFE_POS={counts['UNSAFE_POS']}, "
        f"UNSAFE_NODROP={counts['UNSAFE_NODROP']}", file=sys.stderr)
  print(f"  total DROP members across SAFE: {total_drops}", file=sys.stderr)

  write_review(args.review_out, clusters, classifications)
  print(f"review written to {args.review_out}", file=sys.stderr)

  if args.apply:
    lines_mod, members_dropped, emptied = apply_drops(
        args.syn_path, clusters, classifications, args.dry_run)
    print(f"\n--- apply {'(DRY RUN)' if args.dry_run else ''} ---", file=sys.stderr)
    print(f"cluster lines modified: {lines_mod}", file=sys.stderr)
    print(f"listed members removed: {members_dropped}", file=sys.stderr)
    if emptied:
      print(f"clusters entirely removed: {len(emptied)}", file=sys.stderr)
      for cid in emptied[:10]:
        print(f"    {cid}", file=sys.stderr)
    if not args.dry_run:
      print(f"backup: {os.path.basename(args.syn_path)}.bak_drops", file=sys.stderr)

  if args.emit:
    n_a, n_ambig = emit_tier_a(clusters, classifications, canonical_set,
                               args.rewrite_out)
    from_unsafe, from_harvest, total_b = emit_tier_b(
        clusters, classifications, args.soft_pairs_in, args.soft_axioms_out)
    print(f"\n--- emit ---", file=sys.stderr)
    print(f"Tier A ({os.path.basename(args.rewrite_out)}): "
          f"{n_a} member->canonical mappings", file=sys.stderr)
    if n_ambig:
      print(f"  ({n_ambig} members had multiple SAFE canonicals; "
            f"highest-score mapping used)", file=sys.stderr)
    print(f"Tier B ({os.path.basename(args.soft_axioms_out)}): "
          f"{total_b} pairs total", file=sys.stderr)
    print(f"  from UNSAFE clusters: {from_unsafe}", file=sys.stderr)
    print(f"  from harvest stash: {from_harvest}", file=sys.stderr)
  return 0


if __name__ == "__main__":
  sys.exit(main())
