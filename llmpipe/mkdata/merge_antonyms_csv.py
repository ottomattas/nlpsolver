#!/usr/bin/env python3
"""
Merge adjective antonym pairs from mkdata/antonyms.csv into mkdata/ant_a.txt.

The CSV is large (~11k rows across all POSes) so we filter aggressively:
  * only rows where part_of_speech == 'adjective'
  * the antonyms field is split on '|' and deduplicated
  * both the lemma and each antonym must pass a commonness filter
    (wordfreq.zipf_frequency >= --min_zipf, default 3.0)
  * both words must have at least one WordNet adjective synset (a or s)
  * single-word entries only (phrases with spaces are dropped)

Pairs already present in ant_a.txt (either direction) are skipped.
New pairs are appended under a comment header with canonical ID suffix _AC01
to distinguish them from _A01 (WordNet) and _AM01 (manual list) entries.

Run:
    venv/bin/python merge_antonyms_csv.py
    venv/bin/python merge_antonyms_csv.py --dry_run
    venv/bin/python merge_antonyms_csv.py --min_zipf 3.5
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

from nltk.corpus import wordnet as wn
from wordfreq import zipf_frequency

from merge_antonyms_manual import (
    load_existing_pairs,
    append_new_entries,
    norm,
    is_adjective,
)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ANT_A = os.path.join(SCRIPT_DIR, "ant_a.txt")
DEFAULT_CSV = os.path.join(SCRIPT_DIR, "antonyms.csv")


# Pairs suppressed from the CSV merge because WordNet's antonym link only
# holds under a specialized reading (grammar, music, phonetics, niche
# domains, ...) that never fires on generic sentences in this pipeline.
# Stored as frozensets so either direction of lookup matches.
CSV_BLACKLIST: set[frozenset] = {
    frozenset({"essential", "adjective"}),
    frozenset({"main", "dependent"}),
    frozenset({"single", "common"}),
    frozenset({"pass", "running"}),
    frozenset({"end-stopped", "run-on"}),
    frozenset({"loud", "piano"}),
    frozenset({"soft", "forte"}),
    frozenset({"flatter", "natural"}),
    frozenset({"sharper", "flat"}),
    frozenset({"hard", "voiced"}),
    frozenset({"incident", "basic"}),
    frozenset({"diffuse", "hard"}),
    frozenset({"self-generated", "induced"}),
    frozenset({"paranormal", "sensory"}),
    frozenset({"stiff", "impotent"}),
    frozenset({"strong", "impotent"}),
    frozenset({"rough", "cut"}),
    frozenset({"shed", "persistent"}),
    frozenset({"direct", "collateral"}),
    frozenset({"walk-on", "speaking"}),
    frozenset({"outer", "safe"}),
    frozenset({"operative", "medical"}),
    frozenset({"cancelled", "on"}),
    frozenset({"confirming", "negative"}),
    frozenset({"kept", "broken"}),
    frozenset({"uncertain", "sealed"}),
}


def parse_csv_adjective_pairs(path: str) -> list[tuple[str, str]]:
  """Return (lemma, antonym) pairs for adjective rows, split on '|'."""
  out: list[tuple[str, str]] = []
  with open(path, encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
      if row.get("part_of_speech", "").strip() != "adjective":
        continue
      lemma = norm(row.get("lemma", ""))
      if not lemma:
        continue
      raw = row.get("antonyms", "") or ""
      seen_on_row: set[str] = set()
      for ant in raw.split("|"):
        ant = norm(ant)
        if not ant or ant == lemma or ant in seen_on_row:
          continue
        seen_on_row.add(ant)
        out.append((lemma, ant))
  return out


def is_common(w: str, min_zipf: float) -> bool:
  if not w or " " in w:
    return False
  if not w[0].isalpha():
    return False
  return zipf_frequency(w, "en") >= min_zipf


def merge_pairs(existing: set[frozenset],
                candidates: list[tuple[str, str]],
                min_zipf: float) -> list[tuple[str, str]]:
  """Filter to novel, common, adjective-only, non-blacklisted pairs."""
  seen: set[frozenset] = set()
  new: list[tuple[str, str]] = []
  for w1, w2 in candidates:
    key = frozenset({w1, w2})
    if key in existing or key in seen or key in CSV_BLACKLIST:
      continue
    if not (is_common(w1, min_zipf) and is_common(w2, min_zipf)):
      continue
    if not (is_adjective(w1) and is_adjective(w2)):
      continue
    seen.add(key)
    new.append((w1, w2))
  return new


def strip_blacklisted_from_db(ant_a_path: str) -> int:
  """Remove any existing ant_a.txt rows whose (canonical_lemma, antonym) pair
  is in CSV_BLACKLIST. Returns the number of rows removed.

  Each data row has the form 'LEMMA_A##,word1,score1,word2,score2,...'. A row
  may contain several antonyms; we drop only the blacklisted word(s) from that
  row, and drop the whole row if no antonyms remain.
  """
  if not os.path.exists(ant_a_path):
    return 0
  out_lines: list[str] = []
  removed = 0
  with open(ant_a_path, encoding="utf-8") as f:
    for line in f:
      raw = line.rstrip("\n")
      stripped = raw.strip()
      if not stripped or stripped.startswith("#"):
        out_lines.append(raw)
        continue
      parts = [p.strip() for p in stripped.split(",")]
      if len(parts) < 3 or "_" not in parts[0]:
        out_lines.append(raw)
        continue
      canonical = norm(parts[0].rsplit("_", 1)[0])
      kept: list[str] = [parts[0]]
      i = 1
      row_removed = 0
      while i + 1 < len(parts):
        word = norm(parts[i])
        score = parts[i + 1]
        if frozenset({canonical, word}) in CSV_BLACKLIST:
          row_removed += 1
        else:
          kept.append(word)
          kept.append(score)
        i += 2
      if row_removed == 0:
        out_lines.append(raw)
      elif len(kept) >= 3:
        out_lines.append(",".join(kept))
        removed += row_removed
      else:
        removed += row_removed  # whole row dropped
  with open(ant_a_path, "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines) + "\n")
  return removed


def main() -> int:
  ap = argparse.ArgumentParser(description=__doc__,
                               formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("--csv", default=DEFAULT_CSV,
                  help=f"path to antonyms.csv (default: {DEFAULT_CSV})")
  ap.add_argument("--ant_a", default=DEFAULT_ANT_A,
                  help=f"path to ant_a.txt (default: {DEFAULT_ANT_A})")
  ap.add_argument("--min_zipf", type=float, default=3.0,
                  help="minimum wordfreq zipf score for both words (default 3.0)")
  ap.add_argument("--dry_run", action="store_true",
                  help="report what would be added, but do not modify ant_a.txt")
  ap.add_argument("--show", type=int, default=40,
                  help="sample size to print (default 40; 0 = print all)")
  args = ap.parse_args()

  if not args.dry_run:
    stripped = strip_blacklisted_from_db(args.ant_a)
    if stripped:
      print(f"stripped {stripped} blacklisted pair(s) from {os.path.basename(args.ant_a)}")

  existing = load_existing_pairs(args.ant_a)
  print(f"existing pair count in {os.path.basename(args.ant_a)}: {len(existing)}")

  raw = parse_csv_adjective_pairs(args.csv)
  print(f"adjective rows parsed from {os.path.basename(args.csv)}: {len(raw)}")

  new_pairs = merge_pairs(existing, raw, args.min_zipf)
  print(f"new adjective pairs to add (min_zipf={args.min_zipf}): {len(new_pairs)}")

  limit = len(new_pairs) if args.show == 0 else min(args.show, len(new_pairs))
  for w1, w2 in new_pairs[:limit]:
    print(f"  + {w1} / {w2}")
  if limit < len(new_pairs):
    print(f"  ... ({len(new_pairs) - limit} more; use --show 0 to list all)")

  if args.dry_run:
    print("(dry run — ant_a.txt not modified)")
    return 0

  append_new_entries(args.ant_a, new_pairs,
                     suffix="AC01",
                     header_note=f"Added from antonyms.csv (min_zipf={args.min_zipf})")
  if new_pairs:
    print(f"appended {len(new_pairs)} entries to {args.ant_a}")
  else:
    print("nothing to append")
  return 0


if __name__ == "__main__":
  sys.exit(main())
