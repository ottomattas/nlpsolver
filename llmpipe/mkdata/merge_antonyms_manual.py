#!/usr/bin/env python3
"""
Merge hand-curated adjective antonym pairs from antonyms1.txt and
antonyms2.txt into mkdata/ant_a.txt.

Both source files live in mkdata/ alongside this script.

  antonyms2.txt -- one pair per line, "word1 - word2" (plus free-text headers)
  antonyms1.txt -- one pair per line,
                   "w1 w2 not wX [relation ...] frequency"
                   Headers/blank lines are skipped.

Both w1 and w2 must have a WordNet adjective synset (pos 'a' or 's') or the
pair is dropped. Pairs already present in ant_a.txt (either direction) are
skipped. New pairs are appended under a comment header with canonical ID
suffix _AM01 to distinguish them from the original WordNet rows (_A01).

Run:
    venv/bin/python merge_antonyms_manual.py
    venv/bin/python merge_antonyms_manual.py --dry_run
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable

from nltk.corpus import wordnet as wn


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ANT_A = os.path.join(SCRIPT_DIR, "ant_a.txt")
DEFAULT_SRC1 = os.path.join(SCRIPT_DIR, "antonyms1.txt")
DEFAULT_SRC2 = os.path.join(SCRIPT_DIR, "antonyms2.txt")


def norm(w: str) -> str:
  return w.lower().strip().replace("_", " ")


def is_adjective(w: str) -> bool:
  """True if w has at least one WordNet adjective synset (head or satellite)."""
  key = w.replace(" ", "_")
  return bool(wn.synsets(key, pos="a") or wn.synsets(key, pos="s"))


# ---------- existing DB ----------

def load_existing_pairs(ant_a_path: str) -> set[frozenset]:
  """Return a set of frozenset({canonical, antonym}) pairs from ant_a.txt."""
  pairs: set[frozenset] = set()
  if not os.path.exists(ant_a_path):
    return pairs
  with open(ant_a_path, encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if not line or line.startswith("#"):
        continue
      parts = [p.strip() for p in line.split(",")]
      if len(parts) < 3:
        continue
      cid = parts[0]
      # Strip trailing _A## (or _AM##, _AC##) POS suffix.
      if "_" not in cid:
        continue
      canonical = norm(cid.rsplit("_", 1)[0])
      i = 1
      while i + 1 < len(parts):
        word = norm(parts[i])
        # parts[i+1] is the score; we ignore it here
        if canonical and word:
          pairs.add(frozenset({canonical, word}))
        i += 2
  return pairs


# ---------- source file parsing ----------

def parse_antonyms2(path: str) -> list[tuple[str, str]]:
  """Parse 'word1 - word2' pairs; skip lines without that structure."""
  out: list[tuple[str, str]] = []
  if not os.path.exists(path):
    print(f"warning: {path} not found, skipping", file=sys.stderr)
    return out
  with open(path, encoding="utf-8") as f:
    for line in f:
      parts = line.strip().split()
      if len(parts) == 3 and parts[1] == "-":
        out.append((norm(parts[0]), norm(parts[2])))
  return out


def parse_antonyms1(path: str) -> list[tuple[str, str]]:
  """Parse 'w1 w2 not wX ... freq' entries; skip headers and blanks.

  We accept any line that has at least four whitespace-separated tokens where
  token[2] == 'not'. First two tokens are the antonym pair.
  """
  out: list[tuple[str, str]] = []
  if not os.path.exists(path):
    print(f"warning: {path} not found, skipping", file=sys.stderr)
    return out
  with open(path, encoding="utf-8") as f:
    for line in f:
      parts = line.strip().split()
      if len(parts) < 4:
        continue
      if parts[2] != "not":
        continue
      w1, w2 = norm(parts[0]), norm(parts[1])
      if w1 and w2 and w1 != w2:
        out.append((w1, w2))
  return out


# ---------- merge ----------

def merge_pairs(existing: set[frozenset],
                candidates: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
  """Return deduplicated list of (w1, w2) pairs that are NOT in existing and
  where both words are WordNet adjectives."""
  seen: set[frozenset] = set()
  new: list[tuple[str, str]] = []
  for w1, w2 in candidates:
    key = frozenset({w1, w2})
    if key in existing or key in seen:
      continue
    if not (is_adjective(w1) and is_adjective(w2)):
      continue
    seen.add(key)
    new.append((w1, w2))
  return new


def append_new_entries(ant_a_path: str,
                       new_pairs: list[tuple[str, str]],
                       suffix: str,
                       header_note: str) -> None:
  if not new_pairs:
    return
  with open(ant_a_path, "a", encoding="utf-8") as f:
    f.write("\n# " + header_note + "\n")
    for w1, w2 in new_pairs:
      cid = w1.upper().replace(" ", "_") + "_" + suffix
      f.write(f"{cid},{w2},0.95\n")


# ---------- main ----------

def main() -> int:
  ap = argparse.ArgumentParser(description=__doc__,
                               formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("--antonyms1", default=DEFAULT_SRC1,
                  help=f"path to antonyms1.txt (default: {DEFAULT_SRC1})")
  ap.add_argument("--antonyms2", default=DEFAULT_SRC2,
                  help=f"path to antonyms2.txt (default: {DEFAULT_SRC2})")
  ap.add_argument("--ant_a", default=DEFAULT_ANT_A,
                  help=f"path to ant_a.txt (default: {DEFAULT_ANT_A})")
  ap.add_argument("--dry_run", action="store_true",
                  help="report what would be added, but do not modify ant_a.txt")
  args = ap.parse_args()

  existing = load_existing_pairs(args.ant_a)
  print(f"existing pair count in {os.path.basename(args.ant_a)}: {len(existing)}")

  raw2 = parse_antonyms2(args.antonyms2)
  raw1 = parse_antonyms1(args.antonyms1)
  print(f"parsed antonyms2.txt pairs: {len(raw2)}")
  print(f"parsed antonyms1.txt pairs: {len(raw1)}")

  # Merge sources; order preserved so antonyms2 takes priority on display.
  new_pairs = merge_pairs(existing, raw2 + raw1)
  print(f"new adjective pairs to add: {len(new_pairs)}")

  for w1, w2 in new_pairs:
    print(f"  + {w1} / {w2}")

  if args.dry_run:
    print("(dry run — ant_a.txt not modified)")
    return 0

  append_new_entries(args.ant_a, new_pairs,
                     suffix="AM01",
                     header_note="Added from antonyms1.txt + antonyms2.txt (manual lists)")
  if new_pairs:
    print(f"appended {len(new_pairs)} entries to {args.ant_a}")
  else:
    print("nothing to append")
  return 0


if __name__ == "__main__":
  sys.exit(main())
