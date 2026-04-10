#!/usr/bin/env python3
"""
Merge adjective antonym pairs from mkdata/adjectives.val into mkdata/ant_a.txt.

File format: TAB-separated, three columns per line
    word1 <TAB> word2 <TAB> label
where label==1 means antonym pair and label==0 means synonym pair. Only
label==1 rows are considered. Both words must have a WordNet adjective
synset (head or satellite) or the pair is dropped. Pairs already present in
ant_a.txt (either direction) are skipped. New entries get the canonical ID
suffix _AV01 so they're distinguishable from _A01 (WordNet), _AM01 (manual
lists), and _AC01 (CSV).

Run:
    venv/bin/python merge_antonyms_val.py --dry_run    # review first
    venv/bin/python merge_antonyms_val.py              # apply
"""
from __future__ import annotations

import argparse
import os
import sys

from merge_antonyms_manual import (
    load_existing_pairs,
    append_new_entries,
    norm,
    is_adjective,
)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ANT_A = os.path.join(SCRIPT_DIR, "ant_a.txt")
DEFAULT_VAL = os.path.join(SCRIPT_DIR, "adjectives.val")


# Curated allowlist of adjective antonym pairs from adjectives.val approved
# for merging. Every other label=1 row is ignored (many are mislabels or
# too domain-specific for general sentences). Stored as frozensets so either
# direction matches.
APPROVED_PAIRS: set[frozenset] = {
    # General opposites
    frozenset({"noble", "ignoble"}),
    frozenset({"good", "awful"}),
    frozenset({"simplistic", "complex"}),
    frozenset({"rectangular", "rounded"}),
    frozenset({"hot", "cool"}),
    frozenset({"warm", "cold"}),
    frozenset({"stupid", "clever"}),
    frozenset({"large", "minuscule"}),
    frozenset({"legitimate", "invalid"}),
    frozenset({"flawless", "flawed"}),
    frozenset({"comprehensible", "incomprehensible"}),
    frozenset({"mythical", "real"}),
    frozenset({"pleased", "displeased"}),
    frozenset({"transparent", "opaque"}),
    frozenset({"social", "antisocial"}),
    frozenset({"occasional", "regular"}),
    frozenset({"childish", "mature"}),
    frozenset({"logical", "invalid"}),
    frozenset({"radical", "moderate"}),
    frozenset({"opposite", "same"}),
    frozenset({"fake", "genuine"}),
    frozenset({"inauspicious", "auspicious"}),
    frozenset({"unimportant", "great"}),
    frozenset({"unoccupied", "occupied"}),
    frozenset({"anomalous", "normal"}),
    frozenset({"correct", "improper"}),
    frozenset({"awake", "unconscious"}),
    frozenset({"distant", "near"}),
    frozenset({"prostrate", "erect"}),
    frozenset({"intimate", "remote"}),
    frozenset({"firm", "soft"}),
    frozenset({"naked", "clothed"}),
    frozenset({"strict", "permissive"}),
    frozenset({"strict", "lenient"}),
    frozenset({"cheerful", "sad"}),
    frozenset({"desperate", "hopeful"}),
    frozenset({"plump", "thin"}),
    frozenset({"static", "dynamic"}),
    frozenset({"new", "ancient"}),
    frozenset({"intuitive", "logical"}),
    frozenset({"dull", "clear"}),
    frozenset({"talented", "untalented"}),
    frozenset({"tremendous", "small"}),
    frozenset({"risky", "safe"}),
    frozenset({"special", "ordinary"}),
    frozenset({"advantageous", "disadvantageous"}),
    # Domain-but-usable
    frozenset({"indirect", "immediate"}),
    frozenset({"academic", "applied"}),
    frozenset({"disparate", "same"}),
    frozenset({"separate", "integrated"}),
    frozenset({"intrinsic", "extrinsic"}),
    frozenset({"aged", "fresh"}),
    frozenset({"tangy", "sweet"}),
    frozenset({"plain", "decorative"}),
    frozenset({"leaded", "unleaded"}),
    frozenset({"plebeian", "patrician"}),
    frozenset({"makeshift", "permanent"}),
    frozenset({"human", "animal"}),
    frozenset({"marine", "terrestrial"}),
    frozenset({"unskillful", "skillful"}),
    frozenset({"sloping", "vertical"}),
    frozenset({"illusionary", "real"}),
    frozenset({"separate", "adjacent"}),
    frozenset({"rich", "plain"}),
    frozenset({"extraneous", "intrinsic"}),
    frozenset({"aged", "green"}),
    frozenset({"latent", "actual"}),
    frozenset({"underground", "open"}),
    frozenset({"bald", "haired"}),
    frozenset({"open", "private"}),
    frozenset({"weird", "familiar"}),
    frozenset({"sensual", "mental"}),
    frozenset({"unidirectional", "bidirectional"}),
    frozenset({"alien", "native"}),
    frozenset({"stillborn", "alive"}),
    frozenset({"romantic", "practical"}),
    frozenset({"agrarian", "urban"}),
    frozenset({"absurd", "logical"}),
    frozenset({"inhomogeneous", "homogeneous"}),
    frozenset({"northerly", "southerly"}),
    frozenset({"reusable", "expendable"}),
    frozenset({"incompressible", "compressible"}),
    frozenset({"coated", "uncoated"}),
}


def parse_val(path: str) -> list[tuple[str, str]]:
  """Return (w1, w2) pairs for rows where the label column is '1'."""
  out: list[tuple[str, str]] = []
  with open(path, encoding="utf-8") as f:
    for line in f:
      parts = line.rstrip("\n").split("\t")
      if len(parts) != 3:
        continue
      if parts[2].strip() != "1":
        continue
      w1, w2 = norm(parts[0]), norm(parts[1])
      if w1 and w2 and w1 != w2:
        out.append((w1, w2))
  return out


def merge_pairs(existing: set[frozenset],
                candidates: list[tuple[str, str]]) -> list[tuple[str, str]]:
  """Filter to novel, adjective-only, allowlisted pairs. Order preserved."""
  seen: set[frozenset] = set()
  new: list[tuple[str, str]] = []
  for w1, w2 in candidates:
    key = frozenset({w1, w2})
    if key not in APPROVED_PAIRS:
      continue
    if key in existing or key in seen:
      continue
    if not (is_adjective(w1) and is_adjective(w2)):
      continue
    seen.add(key)
    new.append((w1, w2))
  return new


def main() -> int:
  ap = argparse.ArgumentParser(description=__doc__,
                               formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("--val", default=DEFAULT_VAL,
                  help=f"path to adjectives.val (default: {DEFAULT_VAL})")
  ap.add_argument("--ant_a", default=DEFAULT_ANT_A,
                  help=f"path to ant_a.txt (default: {DEFAULT_ANT_A})")
  ap.add_argument("--dry_run", action="store_true",
                  help="report what would be added, but do not modify ant_a.txt")
  args = ap.parse_args()

  existing = load_existing_pairs(args.ant_a)
  print(f"existing pair count in {os.path.basename(args.ant_a)}: {len(existing)}")

  raw = parse_val(args.val)
  print(f"antonym rows (label=1) in {os.path.basename(args.val)}: {len(raw)}")

  new_pairs = merge_pairs(existing, raw)
  print(f"new adjective pairs to add: {len(new_pairs)}")

  for w1, w2 in new_pairs:
    print(f"  + {w1} / {w2}")

  if args.dry_run:
    print("(dry run — ant_a.txt not modified)")
    return 0

  append_new_entries(args.ant_a, new_pairs,
                     suffix="AV01",
                     header_note="Added from adjectives.val (label=1 antonym pairs)")
  if new_pairs:
    print(f"appended {len(new_pairs)} entries to {args.ant_a}")
  else:
    print("nothing to append")
  return 0


if __name__ == "__main__":
  sys.exit(main())
