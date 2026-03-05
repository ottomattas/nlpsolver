#!/usr/bin/env python3
"""
Post-pass merger for synonym clusters.

Goal:
- Take a CSV with rows like:
    CANON_ID,syn1,sim1,syn2,sim2,...
  where syn1 is typically the canonical lemma with sim1 == 1.00.
- Merge overlapping clusters so that if canonical lemma of cluster A appears in cluster B
  with score >= tau_merge (and same POS), they get unified into one canonical concept.
- Choose one canonical lemma per merged group (default: most frequent by wordfreq zipf).
- Output:
  1) merged_clusters.csv (same compact row format)
  2) id_mapping.csv mapping old canonical IDs -> new canonical IDs

Usage:
  python merge_clusters.py input.csv merged.csv mapping.csv --tau_merge 0.88 --min_score 0.50 --max_syn 10

Notes:
- Requires: pip install wordfreq
  If wordfreq isn't available, falls back to a deterministic heuristic.
  
  
How it solves your PRODUCE/GENERATE example

If produce appears in the GENERATE_V row with score 0.92 and tau_merge <= 0.92, then the two clusters are merged
into one component and you get one canonical (chosen by wordfreq frequency, typically produce), 
with generate included as a synonym.

Typical settings

--tau_merge 0.88 (merge fairly strong overlaps)

--min_score 0.50

--max_syn 10

If you want a stricter merge (fewer merges, less risk of polysemy collapse), use --tau_merge 0.92 or 0.95.  
  
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Iterable, Set

# Optional frequency ranking
try:
    from wordfreq import zipf_frequency
except Exception:
    zipf_frequency = None  # type: ignore


# ----------------------------
# Utilities
# ----------------------------

POS_RE = re.compile(r".*_([NAV])(\d+)?$")  # e.g., FAST_A, FAST_A01, CAR_N2, RUN_V03


def parse_pos(canon_id: str) -> Optional[str]:
    m = POS_RE.match(canon_id)
    if not m:
        return None
    return m.group(1)


def normalize_form(s: str) -> str:
    return s.strip().lower()


def safe_float(x: str) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def lemma_zipf(lemma: str) -> float:
    if zipf_frequency is None:
        # fallback: prefer shorter, then lexicographic; convert to a pseudo-score
        # (higher is better)
        return 10.0 - min(len(lemma), 10) + (hash(lemma) % 1000) / 1e6
    return float(zipf_frequency(lemma, "en"))


# ----------------------------
# Data structures
# ----------------------------

@dataclass
class ClusterRow:
    canon_id: str
    pos: str
    canon_lemma: str
    items: Dict[str, float]  # lemma -> score (includes canon_lemma with 1.00 usually)


class UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, a: int) -> int:
        while self.parent[a] != a:
            self.parent[a] = self.parent[self.parent[a]]
            a = self.parent[a]
        return a

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            self.parent[ra] = rb
        elif self.rank[ra] > self.rank[rb]:
            self.parent[rb] = ra
        else:
            self.parent[rb] = ra
            self.rank[ra] += 1


# ----------------------------
# Parsing
# ----------------------------

def read_clusters(path: str) -> List[ClusterRow]:
    rows: List[ClusterRow] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for line_no, parts in enumerate(reader, start=1):
            if not parts:
                continue
            canon_id = parts[0].strip()
            pos = parse_pos(canon_id)
            if pos is None:
                raise ValueError(f"Cannot parse POS from canonical id '{canon_id}' at line {line_no}")

            # Parse pairs (lemma, score)
            items: Dict[str, float] = {}
            pairs = parts[1:]
            # Accept both odd/even lengths; ignore trailing junk if any
            for i in range(0, len(pairs) - 1, 2):
                lemma = normalize_form(pairs[i])
                score = safe_float(pairs[i + 1])
                if not lemma:
                    continue
                if score != score:  # NaN check
                    continue
                # keep max score if duplicates
                items[lemma] = max(items.get(lemma, 0.0), float(score))

            # Canon lemma is usually the first lemma after canon_id; else pick best by score then freq
            canon_lemma = None
            if len(parts) >= 3:
                canon_lemma = normalize_form(parts[1])
            if not canon_lemma or canon_lemma not in items:
                # choose highest score, break ties by zipf
                if not items:
                    raise ValueError(f"No items found for '{canon_id}' at line {line_no}")
                canon_lemma = max(items.items(), key=lambda kv: (kv[1], lemma_zipf(kv[0])))[0]

            rows.append(ClusterRow(canon_id=canon_id, pos=pos, canon_lemma=canon_lemma, items=items))
    return rows


# ----------------------------
# Merge criterion
# ----------------------------

def build_merge_edges(clusters: List[ClusterRow], tau_merge: float) -> List[Tuple[int, int]]:
    """
    Merge A and B if:
      - same POS
      - canonical lemma of A appears in B with score >= tau_merge
        OR canonical lemma of B appears in A with score >= tau_merge
    """
    # Index lemma -> clusters containing it (and score)
    lemma_to_clusters: Dict[Tuple[str, str], List[Tuple[int, float]]] = {}
    # key: (pos, lemma)
    for idx, c in enumerate(clusters):
        for lemma, score in c.items.items():
            key = (c.pos, lemma)
            lemma_to_clusters.setdefault(key, []).append((idx, score))

    edges: Set[Tuple[int, int]] = set()

    for i, c in enumerate(clusters):
        key = (c.pos, c.canon_lemma)
        for j, score_in_j in lemma_to_clusters.get(key, []):
            if i == j:
                continue
            # canonical lemma of i appears in j with sufficient score -> merge
            if score_in_j >= tau_merge:
                a, b = (i, j) if i < j else (j, i)
                edges.add((a, b))

        # Also check the reverse direction (canon of others appearing in i) is already covered
        # by iterating all i; but we can keep it symmetric automatically.

    return sorted(edges)


# ----------------------------
# Group synthesis
# ----------------------------

def choose_group_canonical_lemma(group_indices: List[int], clusters: List[ClusterRow]) -> str:
    """
    Pick canonical lemma for merged group:
      - highest zipf frequency
      - tie-breaker: appears as canonical lemma in some cluster
      - then shortest
    """
    lemmas: Set[str] = set()
    canon_lemmas: Set[str] = set()
    for idx in group_indices:
        c = clusters[idx]
        lemmas |= set(c.items.keys())
        canon_lemmas.add(c.canon_lemma)

    def keyfn(lemma: str):
        return (
            lemma_zipf(lemma),
            1 if lemma in canon_lemmas else 0,
            -len(lemma),  # prefer shorter if all else equal
        )

    return max(lemmas, key=keyfn)


def synthesize_group_items(
    group_indices: List[int],
    clusters: List[ClusterRow],
    chosen_canon: str,
    min_score: float,
    max_syn: int,
) -> Dict[str, float]:
    """
    Combine lemma->score using max over all occurrences.
    Ensure chosen_canon has score 1.00.
    Drop items < min_score (except chosen_canon).
    Keep up to max_syn (excluding chosen_canon, which is always included).
    """
    combined: Dict[str, float] = {}
    for idx in group_indices:
        for lemma, score in clusters[idx].items.items():
            combined[lemma] = max(combined.get(lemma, 0.0), float(score))

    combined[chosen_canon] = 1.00

    # Filter
    kept = [(l, s) for (l, s) in combined.items() if (l == chosen_canon or s >= min_score)]
    # Sort: by score desc then zipf desc
    kept.sort(key=lambda kv: (kv[1], lemma_zipf(kv[0])), reverse=True)

    # Build limited list with chosen canon first
    out: Dict[str, float] = {chosen_canon: 1.00}
    for lemma, score in kept:
        if lemma == chosen_canon:
            continue
        if len(out) - 1 >= max_syn:  # max_syn synonyms besides canonical
            break
        out[lemma] = float(score)

    return out


def make_unique_canon_id(base_lemma: str, pos: str, used: Dict[str, int]) -> str:
    base = f"{base_lemma.upper()}_{pos}"
    if base not in used:
        used[base] = 1
        return base
    used[base] += 1
    # append 2-digit counter for collisions
    return f"{base}{used[base]:02d}"


# ----------------------------
# Main
# ----------------------------

def merge_clusters(
    clusters: List[ClusterRow],
    tau_merge: float,
    min_score: float,
    max_syn: int,
) -> Tuple[List[str], List[Tuple[str, str]]]:
    """
    Returns:
      - merged_lines: compact CSV lines (no header)
      - mapping: list of (old_id, new_id)
    """
    n = len(clusters)
    uf = UnionFind(n)

    for a, b in build_merge_edges(clusters, tau_merge=tau_merge):
        uf.union(a, b)

    # groups: root -> indices
    groups: Dict[int, List[int]] = {}
    for i in range(n):
        r = uf.find(i)
        groups.setdefault(r, []).append(i)

    # Produce merged rows; keep POS-separated canonical IDs and stable ordering
    used_ids: Dict[str, int] = {}
    merged_lines: List[str] = []
    mapping: List[Tuple[str, str]] = []

    # stable order: by POS then by best frequency of chosen canonical then by original position
    group_infos = []
    for root, idxs in groups.items():
        pos = clusters[idxs[0]].pos
        chosen_canon = choose_group_canonical_lemma(idxs, clusters)
        freq = lemma_zipf(chosen_canon)
        first_idx = min(idxs)
        group_infos.append((pos, -freq, first_idx, root, chosen_canon, idxs))

    group_infos.sort()

    for pos, _, _, root, chosen_canon, idxs in group_infos:
        new_id = make_unique_canon_id(chosen_canon, pos, used_ids)
        items = synthesize_group_items(
            group_indices=idxs,
            clusters=clusters,
            chosen_canon=chosen_canon,
            min_score=min_score,
            max_syn=max_syn,
        )

        # format line: CANON_ID,lemma,score,lemma,score...
        parts = [new_id]
        # canonical first then rest by score
        rest = [(l, s) for (l, s) in items.items() if l != chosen_canon]
        rest.sort(key=lambda kv: (kv[1], lemma_zipf(kv[0])), reverse=True)

        parts.append(chosen_canon)
        parts.append(f"{1.00:.2f}")
        for lemma, score in rest:
            parts.append(lemma)
            parts.append(f"{score:.2f}")

        merged_lines.append(",".join(parts))

        for idx in idxs:
            mapping.append((clusters[idx].canon_id, new_id))

    return merged_lines, mapping


def write_lines(path: str, lines: List[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        for line in lines:
            f.write(line + "\n")


def write_mapping(path: str, mapping: List[Tuple[str, str]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["old_id", "new_id"])
        for a, b in mapping:
            w.writerow([a, b])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_csv", help="Input clusters CSV (linewise compact format)")
    ap.add_argument("output_merged_csv", help="Output merged clusters CSV")
    ap.add_argument("output_mapping_csv", help="Output old->new canonical ID mapping CSV")
    ap.add_argument("--tau_merge", type=float, default=0.88,
                    help="Merge if a canonical lemma appears in another cluster with score >= tau_merge")
    ap.add_argument("--min_score", type=float, default=0.50,
                    help="Drop merged synonyms with score < min_score (canonical kept regardless)")
    ap.add_argument("--max_syn", type=int, default=10,
                    help="Max synonyms to keep per merged cluster (excluding canonical)")
    args = ap.parse_args()

    clusters = read_clusters(args.input_csv)
    merged_lines, mapping = merge_clusters(
        clusters=clusters,
        tau_merge=args.tau_merge,
        min_score=args.min_score,
        max_syn=args.max_syn,
    )

    write_lines(args.output_merged_csv, merged_lines)
    write_mapping(args.output_mapping_csv, mapping)

    print(f"Read {len(clusters)} clusters from {args.input_csv}")
    print(f"Wrote {len(merged_lines)} merged clusters to {args.output_merged_csv}")
    print(f"Wrote mapping for {len(mapping)} old IDs to {args.output_mapping_csv}")
    if zipf_frequency is None:
        print("Note: 'wordfreq' not available; used fallback heuristic for canonical selection.")
    else:
        print("Used wordfreq.zipf_frequency for canonical selection.")


if __name__ == "__main__":
    main()