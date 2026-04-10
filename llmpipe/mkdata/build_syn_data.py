#!/usr/bin/env python3
"""
Build synonym rewrite table and GK axiom file from a Format-A synonym cluster file.

Usage:
    venv/bin/python build_syn_data.py syn_n_10.txt N \\
        --tau_merge 0.90 --hard_thresh 0.90 --soft_min 0.70 --max_syn 12

    venv/bin/python build_syn_data.py syn_a_10.txt A

    venv/bin/python build_syn_data.py syn_v_10.txt V

Outputs default to the current directory (syn_rewrite_<pos>.txt, syn_axioms_<pos>.js).
Override with --out_rewrite and --out_axioms.

Format A (input):  FAST_A01,quick,0.95,rapid,0.92,...
Format B (internal): FAST_A01,fast,1.00,quick,0.95,rapid,0.92,...

Outputs:
  syn_rewrite_?.txt  -- hard rewrite table: word,POS,canonical  (score >= hard_thresh)
  syn_axioms_?.js    -- GK soft axioms: JSON objects with @logic and @confidence
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import os

# merge.py must be in the same directory
sys.path.insert(0, os.path.dirname(__file__))
from merge import read_clusters, merge_clusters


# ---------------------------------------------------------------------------
# Step 1: Format A -> Format B (in-memory)
# ---------------------------------------------------------------------------

def to_format_b(lines: list[str], pos: str) -> list[str]:
    """Convert Format-A lines to Format-B strings (canonical prepended at 1.00)."""
    result = []
    pos_upper = pos.upper()
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = [p.strip() for p in line.split(',')]
        cid = parts[0]
        # Extract canonical word from CID: FAST_A01 -> "fast", CAR_N01 -> "car"
        canon = re.sub(rf'_{pos_upper}\d*$', '', cid, flags=re.IGNORECASE).lower()
        # Parse existing synonym pairs from Format A
        pairs = []
        for i in range(1, len(parts) - 1, 2):
            w = parts[i].strip().lower()
            s = parts[i + 1].strip()
            if w:
                pairs.append((w, s))
        # Promote or prepend canonical with score 1.00
        existing = {w for w, _ in pairs}
        if canon in existing:
            pairs = [(canon, '1.00')] + [(w, s) for w, s in pairs if w != canon]
        else:
            pairs = [(canon, '1.00')] + pairs
        result.append(cid + ',' + ','.join(f'{w},{s}' for w, s in pairs))
    return result


# ---------------------------------------------------------------------------
# Step 3: Build rewrite table and axiom file from merged clusters
# ---------------------------------------------------------------------------

def make_axiom_clauses(synonym: str, canonical: str, pos: str) -> list[list]:
    """Return list of [neg_lit, pos_lit] clause pairs for this synonym -> canonical mapping."""
    s = synonym
    c = canonical
    clauses = []
    if pos == 'N':
        clauses.append([["-isa", s, "?:X"], ["isa", c, "?:X"]])
    elif pos == 'A':
        clauses.append([["-has degree property", s, "?:X", "?:D", "?:R", "?:CT"],
                        ["has degree property", c, "?:X", "?:D", "?:R", "?:CT"]])
        clauses.append([["-has property", s, "?:X", "?:CT"],
                        ["has property", c, "?:X", "?:CT"]])
    elif pos == 'V':
        clauses.append([["-has type", "?:E", s, "?:CT"], ["has type", "?:E", c, "?:CT"]])
        clauses.append([["-is rel2", s, "?:X", "?:Y", "?:CT"],
                        ["is rel2", c, "?:X", "?:Y", "?:CT"]])
        clauses.append([["-has degree rel2", s, "?:X", "?:Y", "?:D", "?:R", "?:CT"],
                        ["has degree rel2", c, "?:X", "?:Y", "?:D", "?:R", "?:CT"]])
    return clauses


def build_rewrite_and_axioms(
    merged_lines: list[str],
    pos: str,
    hard_thresh: float,
    soft_min: float,
) -> tuple[list[str], list[dict]]:
    """
    Returns:
      rewrite_rows: list of "word,POS,canonical" strings
      axiom_objects: list of {"@logic": [...], "@confidence": score} dicts
    """
    # Collect all canonical words (polysemy guard)
    all_canonicals: set[str] = set()
    parsed: list[tuple[str, list[tuple[str, float]]]] = []

    for line in merged_lines:
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 3:
            continue
        canonical = parts[1].lower()
        all_canonicals.add(canonical)
        pairs = []
        for i in range(1, len(parts) - 1, 2):
            w = parts[i].strip().lower()
            try:
                sc = float(parts[i + 1].strip())
            except ValueError:
                continue
            if w:
                pairs.append((w, sc))
        parsed.append((canonical, pairs))

    # For hard rewrite: track best (score, canonical) per word
    best_hard: dict[str, tuple[float, str]] = {}
    # Collect soft axiom entries
    soft_entries: list[tuple[str, str, float]] = []  # (synonym, canonical, score)

    for canonical, pairs in parsed:
        for word, score in pairs:
            if word == canonical:
                continue  # skip self
            if score >= hard_thresh:
                # Only rewrite if word is not itself a canonical
                if word not in all_canonicals:
                    prev = best_hard.get(word)
                    if prev is None or score > prev[0]:
                        best_hard[word] = (score, canonical)
            elif score >= soft_min:
                soft_entries.append((word, canonical, score))

    # Build rewrite table rows
    rewrite_rows = []
    for word, (score, canonical) in sorted(best_hard.items()):
        rewrite_rows.append(f"{word},{pos},{canonical}")

    # Build axiom objects
    axiom_objects = []
    for synonym, canonical, score in soft_entries:
        for clause in make_axiom_clauses(synonym, canonical, pos):
            axiom_objects.append({"@logic": clause, "@confidence": round(score, 2)})

    return rewrite_rows, axiom_objects


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Build synonym rewrite table and GK axioms from Format-A cluster file.")
    ap.add_argument("input_file", help="Format-A synonym cluster file (e.g., syn_n_fixed.txt)")
    ap.add_argument("pos", choices=["N", "A", "V"], help="Part of speech: N, A, or V")
    ap.add_argument("--tau_merge", type=float, default=0.90,
                    help="Merge threshold: merge clusters whose canonicals overlap at this score (default 0.90)")
    ap.add_argument("--hard_thresh", type=float, default=0.90,
                    help="Hard rewrite threshold: score >= this goes to rewrite table (default 0.90)")
    ap.add_argument("--soft_min", type=float, default=0.70,
                    help="Soft axiom minimum score: soft_min <= score < hard_thresh (default 0.70)")
    ap.add_argument("--max_syn", type=int, default=12,
                    help="Max synonyms per merged cluster (default 12)")
    ap.add_argument("--out_rewrite", default=None,
                    help="Output rewrite table path (default: ./syn_rewrite_<pos>.txt)")
    ap.add_argument("--out_axioms", default=None,
                    help="Output axiom file path (default: ./syn_axioms_<pos>.js)")
    args = ap.parse_args()

    pos = args.pos.upper()
    pos_lower = pos.lower()

    out_rewrite = args.out_rewrite or f"syn_rewrite_{pos_lower}.txt"
    out_axioms = args.out_axioms or f"syn_axioms_{pos_lower}.js"

    # Read Format-A source
    with open(args.input_file, 'r', encoding='utf-8') as f:
        lines_a = f.readlines()

    # Step 1: Convert to Format B
    lines_b = to_format_b(lines_a, pos)
    print(f"Format A: {len(lines_a)} input lines -> Format B: {len(lines_b)} rows")

    # Spot-check first row
    if lines_b:
        print(f"  Format B sample: {lines_b[0][:80]}")

    # Step 2: Write temp file and run merge
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False,
                                     encoding='utf-8') as tf:
        tf_path = tf.name
        for line in lines_b:
            tf.write(line + '\n')

    try:
        clusters = read_clusters(tf_path)
        merged_lines, mapping = merge_clusters(
            clusters=clusters,
            tau_merge=args.tau_merge,
            min_score=args.soft_min,
            max_syn=args.max_syn,
        )
    finally:
        os.unlink(tf_path)

    print(f"Merge: {len(clusters)} clusters -> {len(merged_lines)} merged clusters "
          f"({len(mapping)} old->new mappings)")

    # Step 3: Build rewrite table and axioms
    rewrite_rows, axiom_objects = build_rewrite_and_axioms(
        merged_lines, pos,
        hard_thresh=args.hard_thresh,
        soft_min=args.soft_min,
    )

    # Write rewrite table
    with open(out_rewrite, 'w', encoding='utf-8') as f:
        for row in rewrite_rows:
            f.write(row + '\n')
    print(f"Rewrite table: {len(rewrite_rows)} entries -> {out_rewrite}")

    # Write axiom file
    header = (
        f"// Auto-generated synonym axioms for POS={pos}. Do not edit manually.\n"
        f"// Source: {os.path.basename(args.input_file)}  "
        f"Generated by: mkdata/build_syn_data.py\n"
        f"// tau_merge={args.tau_merge}  hard_thresh={args.hard_thresh}  "
        f"soft_min={args.soft_min}\n"
    )
    with open(out_axioms, 'w', encoding='utf-8') as f:
        f.write(header)
        f.write('[\n')
        for i, obj in enumerate(axiom_objects):
            comma = ',' if i < len(axiom_objects) - 1 else ''
            f.write(json.dumps(obj) + comma + '\n')
        f.write(']\n')
    print(f"Axiom file: {len(axiom_objects)} axiom entries -> {out_axioms}")

    # Verify axiom file is valid JSON (after stripping comment lines)
    with open(out_axioms, 'r', encoding='utf-8') as f:
        content = f.read()
    json_content = '\n'.join(l for l in content.splitlines() if not l.startswith('//'))
    try:
        parsed = json.loads(json_content)
        print(f"Axiom file JSON valid: {len(parsed)} objects parsed OK")
    except json.JSONDecodeError as e:
        print(f"WARNING: Axiom file JSON validation failed: {e}", file=sys.stderr)


if __name__ == '__main__':
    main()
