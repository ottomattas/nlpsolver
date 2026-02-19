#!/usr/bin/env python3
"""
Compare Stage-1 outputs from 3 different LLM runs.

Input file format (repeated blocks):
  |!!|<INPUT TEXT>|$$|<OUTPUT TEXT (may include ```json fences, comments, etc.)>

For each input:
- extract the JSON from each output text (ignore trailing explanations/comments)
- compare the 3 JSON values disregarding whitespace AND order (treat lists as multisets)
- if they differ, print the input and the three pretty-printed JSONs for easy comparison

Usage:
  python compare_stage1_outputs.py fileA.txt fileB.txt fileC.txt
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------
# Parsing the custom file format
# -----------------------------

SPLIT_MARK = "|!!|"
SEP_MARK = "|$$|"


@dataclass
class ParsedBlock:
    inp: str
    out_raw: str
    out_json: Optional[Any]
    parse_error: Optional[str]


def parse_blocks_file(path: str) -> List[ParsedBlock]:
    text = open(path, "r", encoding="utf-8").read()

    # Split on |!!| markers; ignore anything before the first marker
    chunks = text.split(SPLIT_MARK)
    blocks: List[ParsedBlock] = []

    for chunk in chunks[1:]:
        if SEP_MARK not in chunk:
            # malformed chunk
            inp = chunk.strip()
            blocks.append(ParsedBlock(inp=inp, out_raw="", out_json=None,
                                     parse_error=f"Missing separator {SEP_MARK!r}"))
            continue

        inp_part, out_part = chunk.split(SEP_MARK, 1)
        inp = inp_part.strip()
        out_raw = out_part.strip()

        out_json, err = extract_first_json(out_raw)
        blocks.append(ParsedBlock(inp=inp, out_raw=out_raw, out_json=out_json, parse_error=err))

    return blocks


# -----------------------------
# JSON extraction from messy text
# -----------------------------

FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def extract_first_json(text: str) -> Tuple[Optional[Any], Optional[str]]:
    """
    Try to extract a parseable JSON value from arbitrary text.
    Preference order:
      1) content inside ```json ... ``` fences (first match)
      2) first balanced JSON object/array found in the text
    Returns: (parsed_obj or None, error_msg or None)
    """
    # 1) Prefer fenced JSON
    m = FENCE_RE.search(text)
    if m:
        candidate = m.group(1).strip()
        obj, err = try_load_json(candidate)
        if err is None:
            return obj, None
        # If fenced content fails, fall through to balanced scan.

    # 2) Balanced scan for first JSON array/object
    # Find earliest '{' or '['
    starts = [i for i, ch in enumerate(text) if ch in "{["]
    for start in starts[:50]:  # avoid pathological scans
        substr = balanced_json_substring(text, start)
        if not substr:
            continue
        obj, err = try_load_json(substr)
        if err is None:
            return obj, None

    return None, "Could not extract parseable JSON from output text."


def try_load_json(s: str) -> Tuple[Optional[Any], Optional[str]]:
    try:
        return json.loads(s), None
    except Exception as e:
        return None, f"json.loads failed: {e}"


def balanced_json_substring(text: str, start: int) -> Optional[str]:
    """
    Return the shortest prefix from text[start:] that forms a balanced JSON object/array.
    Handles strings and escapes so braces inside strings don't count.
    """
    if start >= len(text) or text[start] not in "{[":
        return None

    stack = []
    in_str = False
    esc = False

    opening = text[start]
    stack.append(opening)

    for i in range(start + 1, len(text)):
        ch = text[i]

        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue

        # not in string
        if ch == '"':
            in_str = True
            continue

        if ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if not stack:
                return None
            top = stack[-1]
            if (top == "{" and ch == "}") or (top == "[" and ch == "]"):
                stack.pop()
                if not stack:
                    return text[start:i + 1]
            else:
                # mismatched
                return None

    return None


# -----------------------------
# Canonicalization for "ignore order"
# -----------------------------

def canonicalize(x: Any) -> Any:
    """
    Convert JSON-like structures into a canonical form where:
      - dict key order doesn't matter (sorted)
      - list order doesn't matter (treated as multiset; sorted by canonical string)
    """
    if isinstance(x, dict):
        # canonicalize values, then sort keys
        return {k: canonicalize(x[k]) for k in sorted(x.keys())}
    if isinstance(x, list):
        canon_elems = [canonicalize(e) for e in x]
        # sort elements by a stable representation
        canon_elems.sort(key=lambda v: stable_repr(v))
        return canon_elems
    return x


def stable_repr(x: Any) -> str:
    """
    Stable string for sorting canonicalized items.
    """
    try:
        return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return repr(x)


def pretty(x: Any) -> str:
    return json.dumps(x, indent=2, sort_keys=True, ensure_ascii=False)


# -----------------------------
# Main comparison logic
# -----------------------------

def build_map(blocks: List[ParsedBlock], path: str) -> Dict[str, ParsedBlock]:
    mp: Dict[str, ParsedBlock] = {}
    for b in blocks:
        if b.inp in mp:
            # Keep first, but warn
            print(f"[WARN] Duplicate input in {path}: {b.inp!r}", file=sys.stderr)
            continue
        mp[b.inp] = b
    return mp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file1")
    ap.add_argument("file2")
    ap.add_argument("file3")
    args = ap.parse_args()

    files = [args.file1, args.file2, args.file3]
    parsed = [parse_blocks_file(p) for p in files]
    maps = [build_map(parsed[i], files[i]) for i in range(3)]

    all_inputs = sorted(set().union(*[set(m.keys()) for m in maps]))

    diffs = 0
    for inp in all_inputs:
        blocks = [m.get(inp) for m in maps]

        # If any missing, treat as difference
        missing = [i for i, b in enumerate(blocks) if b is None]
        if missing:
            diffs += 1
            print("=" * 80)
            print(f"INPUT: {inp}")
            print(f"[DIFF] Missing in files: {', '.join(str(i+1) for i in missing)}")
            for i, b in enumerate(blocks):
                print("-" * 80)
                print(f"FILE {i+1}: {files[i]}")
                if b is None:
                    print("(missing)")
                else:
                    if b.out_json is not None:
                        print(pretty(b.out_json))
                    else:
                        print(f"(json parse failed) {b.parse_error}")
                        print("RAW OUTPUT (truncated to 2000 chars):")
                        print(b.out_raw[:2000])
            continue

        # Compare canonicalized JSONs (or parse errors)
        canons = []
        for b in blocks:
            if b.out_json is None:
                canons.append(("__PARSE_ERROR__", b.parse_error or "unknown"))
            else:
                canons.append(("__JSON__", canonicalize(b.out_json)))

        # If any parse error -> diff
        if any(tag == "__PARSE_ERROR__" for tag, _ in canons):
            diffs += 1
            print("=" * 80)
            print(f"INPUT: {inp}")
            for i, b in enumerate(blocks):
                print("-" * 80)
                print(f"FILE {i+1}: {files[i]}")
                if b.out_json is not None:
                    print(pretty(b.out_json))
                else:
                    print(f"(json parse failed) {b.parse_error}")
                    print("RAW OUTPUT (truncated to 2000 chars):")
                    print(b.out_raw[:2000])
            continue

        # All are JSON
        canon_vals = [v for tag, v in canons]  # type: ignore
        same = (canon_vals[0] == canon_vals[1] == canon_vals[2])
        if not same:
            diffs += 1
            print("=" * 80)
            print(f"INPUT: {inp}")
            for i, b in enumerate(blocks):
                print("-" * 80)
                print(f"FILE {i+1}: {files[i]}")
                print(pretty(b.out_json))

    print("=" * 80)
    print(f"Done. Differences found: {diffs}")
    return 0 if diffs == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
