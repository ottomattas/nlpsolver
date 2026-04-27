#!/usr/bin/env python3
"""
Generate solver/data_*.py files from mkdata/*.txt source files.

Reads:
  mkdata/syn_{a,n,v}_rewrite.txt     → solver/data_canonicals.py
  mkdata/ant_{a,n,v}.txt             → solver/data_antonyms.py
  mkdata/syn_{a,n,v}_soft_axioms.txt → solver/data_synonyms.py
  mkdata/excl_a.txt                  → solver/data_exclusions.py

Run from the mkdata/ directory:
    python build_solver_data.py
"""
import os
import sys
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOLVER_DIR = os.path.join(SCRIPT_DIR, "..", "solver")

# ======== manual entries to preserve ========

# These are hand-curated and must not be overwritten by generated data.
MANUAL_CANONICALS = {
    "inside": "in",
    "within": "in",
    "auto": "car",
    "automobile": "car",
    "awake": "wake",
}

# Manual adjective-antonym PAIRS. These are NOT used for semnormalize
# polarity-flipping rewriting any more; instead each pair is injected as a
# 2-member `needs_blocker=False` mutual-exclusion group into
# data_exclusions.py, so the prover sees a has_property-template exclusion
# axiom [-has_property(w1,X,C), -has_property(w2,X,C)].
#
# Format: {word_a: word_b} — one entry per pair (direction doesn't matter).
#
# Spatial pairs (outside/inside, below/above etc.) are NOT listed here —
# they belong in excl_a.txt SPATIAL_* groups with the is_rel2 template.
MANUAL_ANTONYMS = {
    "broken":     "intact",
    "unfinished": "finished",
    "incomplete": "complete",
    "undone":     "done",
}

# Words that should never appear as antonym keys, even if WordNet lists them.
# "abstract" clashes with isa(abstract, X) category annotations from stage 1.
# "past"/"present"/"future" clash with tense markers inside $ctxt terms.
BLOCKED_ANTONYM_WORDS = frozenset({
    "abstract", "past", "present", "future",
    # Kinship / gender — complementary categories, not true antonyms.
    # Flipping "X is a sister" to "X is not a brother" loses positive
    # type info and destroys $theof1 resolution. Handled instead as
    # mutual-exclusion pair groups in excl_a.txt (KIN_* / GENDER_*).
    "sister", "brother", "mother", "father", "aunt", "uncle",
    "daughter", "son", "nephew", "niece", "husband", "wife",
    "man", "woman", "boy", "girl", "male", "female",
    "king", "queen",
    # Spatial / directional — complementary positions, not antonyms.
    "top", "bottom", "front", "back", "left", "right",
    "rear", "head", "tail", "here", "there",
    "north", "south", "east", "west",
    # Temporal sequence — mutually exclusive at a time, not antonyms.
    "day", "night", "sunrise", "sunset",
    "waning", "waxing", "waking", "sleeping",
    # Colours — handled by COLOR_BASIC exclusion group.
    "black", "white",
    # Ambiguous homographs (animal vs market term).
    "bull", "bear",
})


# ======== helpers ========

def read_rewrite_file(path):
    """Read member,canonical pairs from a rewrite file."""
    pairs = {}
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found, skipping")
        return pairs
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) != 2:
                continue
            member, canonical = parts[0].strip(), parts[1].strip()
            pairs[member] = canonical
    return pairs


def read_antonym_file(path):
    """Read antonym file → list of (canonical, [(word, score), ...])."""
    entries = []
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found, skipping")
        return entries
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) < 2:
                continue
            cid = parts[0].strip()
            # Extract canonical from CID: GOOD_A01 → good, NEW_A01 → new
            m = re.match(r"^(.+)_[ANV]\d+$", cid)
            if not m:
                continue
            canonical = m.group(1).lower()
            words = []
            i = 1
            while i + 1 < len(parts):
                word = parts[i].strip()
                score = parts[i + 1].strip()
                if word:
                    words.append((word, float(score)))
                i += 2
            entries.append((canonical, words))
    return entries


def read_soft_axioms_file(path, pos):
    """Read word_a,word_b,score triples from a soft axioms file."""
    pairs = []
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found, skipping")
        return pairs
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) != 3:
                continue
            a, b, score = parts[0].strip(), parts[1].strip(), float(parts[2].strip())
            pairs.append((a, b, score, pos))
    return pairs


def read_exclusion_file(path):
    """Read exclusion groups from excl_a.txt."""
    groups = {}
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found, skipping")
        return groups
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) < 6:
                continue
            gid = parts[0].strip()
            source = parts[1].strip()
            score = float(parts[2].strip())
            needs_blocker = int(parts[3].strip())
            words = [p.strip() for p in parts[4:] if p.strip()]
            groups[gid] = {
                "source": source,
                "score": score,
                "needs_blocker": bool(needs_blocker),
                "words": words,
            }
    return groups


def write_py_file(path, content, header_comment):
    """Write a generated Python file with header."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {header_comment}\n")
        f.write("# AUTO-GENERATED by mkdata/build_solver_data.py — do not edit by hand.\n")
        f.write("#\n")
        f.write(content)
    print(f"  wrote {path}")


# ======== generators ========

def build_canonicals():
    """Generate data_canonicals.py from manual entries + syn_*_rewrite.txt files."""
    print("Building data_canonicals.py ...")
    merged = dict(MANUAL_CANONICALS)
    conflicts = []
    for pos, fname in [("a", "syn_a_rewrite.txt"), ("n", "syn_n_rewrite.txt"), ("v", "syn_v_rewrite.txt")]:
        pairs = read_rewrite_file(os.path.join(SCRIPT_DIR, fname))
        for member, canonical in pairs.items():
            if member in merged and merged[member] != canonical:
                conflicts.append((member, merged[member], canonical, pos))
            else:
                merged[member] = canonical
    if conflicts:
        print(f"  WARNING: {len(conflicts)} conflicts (first entry wins):")
        for m, old, new, pos in conflicts[:10]:
            print(f"    {m}: {old} vs {new} (from {pos})")

    lines = []
    lines.append("# Canonical word forms for semantic normalisation.\n")
    lines.append("#\n")
    lines.append("# Format: {variant: canonical}\n")
    lines.append("# Applied unconditionally (after antonym resolution) to all eligible atom arguments.\n")
    lines.append("#\n")
    lines.append("# Manual entries (hand-curated, preserved across regeneration):\n")
    for k in sorted(MANUAL_CANONICALS):
        lines.append(f'#   "{k}": "{MANUAL_CANONICALS[k]}"\n')
    lines.append("#\n")
    lines.append(f"CANONICALS={{\n")
    for k in sorted(merged):
        lines.append(f'"{k}":"{merged[k]}",\n')
    lines.append("}\n")
    write_py_file(
        os.path.join(SOLVER_DIR, "data_canonicals.py"),
        "".join(lines),
        "Canonical word forms for semantic normalisation.",
    )
    print(f"  {len(merged)} entries ({len(MANUAL_CANONICALS)} manual + {len(merged) - len(MANUAL_CANONICALS)} generated)")
    return merged


def build_antonyms(canonicals):
    """Generate data_antonyms.py from ant_*.txt files.

    Note: MANUAL_ANTONYMS is NOT merged here any more — its pairs are
    injected as exclusion groups by build_exclusions().

    Returns chain_rejected: [(word, canonical), ...] — pairs whose canonical
    target is itself a CANONICALS key (would chain-substitute in semnormalize
    Pass 2 to an unrelated sense, e.g. open→close→near). These are not written
    to ANTONYMS; build_exclusions() emits them as has_property-template
    mutual-exclusion axioms instead.
    """
    print("Building data_antonyms.py ...")
    merged = {}
    chain_rejected = []
    skipped_circular = 0
    skipped_self = 0
    # Verb antonym rewrites are intentionally excluded.
    # Most verb antonym pairs from WordNet (give/take, buy/sell, come/go, ...)
    # are perspective inversions or process complementarities, not logical
    # opposites. Polarity-flip is wrong for them, and key verbs collide with
    # axiom-vocab predicates (e.g. give/take broke the give->have bridge in
    # axioms_std.js:329-336, surfacing as case 171). The few verb pairs where
    # polarity-flip is defensible (like/dislike, love/hate, etc.) will be
    # re-introduced via a separate defeasible attitude-mutex injector
    # (Phase 2) gated on both sides being present.
    for pos, fname in [("a", "ant_a.txt"), ("n", "ant_n.txt")]:
        entries = read_antonym_file(os.path.join(SCRIPT_DIR, fname))
        for canonical, words in entries:
            for word, score in words:
                if word == canonical:
                    skipped_self += 1
                    continue
                if word in BLOCKED_ANTONYM_WORDS:
                    continue
                # Skip if this would create a circular mapping
                if canonical in merged and merged[canonical] == word:
                    skipped_circular += 1
                    continue
                # Don't map a word that is itself a canonical target in CANONICALS
                # (the canonical pass would then try to re-substitute)
                if word in canonicals:
                    continue
                # Don't rewrite to a target that is itself canonicalized — the
                # canonical pass would chain-substitute to an unrelated sense.
                # Defer to exclusion-axiom emission instead.
                if canonical in canonicals:
                    chain_rejected.append((word, canonical))
                    continue
                merged[word] = canonical

    lines = []
    lines.append("# Directional antonym pairs for semantic normalisation.\n")
    lines.append("#\n")
    lines.append("# Format: {word: antonym}\n")
    lines.append("# Meaning: flip the polarity of the enclosing atom AND replace word with antonym.\n")
    lines.append("#\n")
    lines.append(f"ANTONYMS={{\n")
    for k in sorted(merged):
        lines.append(f'"{k}":"{merged[k]}",\n')
    lines.append("}\n")
    write_py_file(
        os.path.join(SOLVER_DIR, "data_antonyms.py"),
        "".join(lines),
        "Directional antonym pairs for semantic normalisation.",
    )
    print(f"  {len(merged)} entries (all generated; MANUAL_ANTONYMS now feeds data_exclusions.py)")
    if skipped_circular:
        print(f"  skipped {skipped_circular} circular mappings")
    if skipped_self:
        print(f"  skipped {skipped_self} self-mappings")
    if chain_rejected:
        print(f"  deferred {len(chain_rejected)} pairs to exclusion axioms (target is a CANONICALS key)")
    return chain_rejected


def build_synonyms():
    """Generate data_synonyms.py from syn_*_soft_axioms.txt files."""
    print("Building data_synonyms.py ...")
    all_pairs = []
    for pos, fname in [("a", "syn_a_soft_axioms.txt"), ("n", "syn_n_soft_axioms.txt"), ("v", "syn_v_soft_axioms.txt")]:
        pairs = read_soft_axioms_file(os.path.join(SCRIPT_DIR, fname), pos)
        all_pairs.extend(pairs)
        print(f"  {fname}: {len(pairs)} pairs")

    # Build bidirectional index
    index = {}
    for a, b, score, pos in all_pairs:
        if a not in index:
            index[a] = []
        index[a].append((b, score, pos))
        if b not in index:
            index[b] = []
        index[b].append((a, score, pos))

    lines = []
    lines.append("# Soft synonym pairs for dynamic axiom injection.\n")
    lines.append("#\n")
    lines.append("# Format: {word: [(other_word, score, pos), ...]}\n")
    lines.append("# Bidirectional: if (A,B) is a pair, both A→B and B→A are stored.\n")
    lines.append("# pos: 'a' (adjective), 'n' (noun), 'v' (verb)\n")
    lines.append("#\n")
    lines.append(f"SOFT_SYNONYMS={{\n")
    for k in sorted(index):
        entries = index[k]
        entry_strs = [f'("{e[0]}",{e[1]:.2f},"{e[2]}")' for e in entries]
        lines.append(f'"{k}":[{",".join(entry_strs)}],\n')
    lines.append("}\n")
    write_py_file(
        os.path.join(SOLVER_DIR, "data_synonyms.py"),
        "".join(lines),
        "Soft synonym pairs for dynamic axiom injection.",
    )
    print(f"  {len(index)} unique words, {len(all_pairs)} pairs")


def build_exclusions(chain_rejected=None):
    """Generate data_exclusions.py from excl_a.txt plus MANUAL_ANTONYMS pairs
    plus chain_rejected antonym pairs deferred from build_antonyms().
    """
    print("Building data_exclusions.py ...")
    groups = read_exclusion_file(os.path.join(SCRIPT_DIR, "excl_a.txt"))

    # Inject MANUAL_ANTONYMS pairs as 2-member has_property exclusion groups.
    # Deduped by pair (frozenset) so a dict carrying both directions still emits
    # a single group.
    manual_seen = set()
    for w1, w2 in MANUAL_ANTONYMS.items():
        pair = frozenset([w1, w2])
        if pair in manual_seen:
            continue
        manual_seen.add(pair)
        a, b = sorted([w1, w2])
        gid = f"MANUAL_ADJ_{a.upper()}_{b.upper()}"
        groups[gid] = {
            "source": "manual",
            "score": 0.95,
            "needs_blocker": False,
            "words": [a, b],
        }

    # Inject chain-rejected antonym pairs (from build_antonyms) as 2-member
    # has_property exclusion groups — same treatment as MANUAL_ANTONYMS.
    # needs_blocker=True (defeasible) because many of these are gradable
    # adjectives (abundant/scarce) where a middle ground exists.
    for w1, w2 in (chain_rejected or []):
        pair = frozenset([w1, w2])
        if pair in manual_seen:
            continue
        manual_seen.add(pair)
        a, b = sorted([w1, w2])
        gid = f"ANT_{a.upper()}_{b.upper()}"
        if gid in groups:
            continue
        groups[gid] = {
            "source": "manual",
            "score": 0.95,
            "needs_blocker": True,
            "words": [a, b],
        }

    if not groups:
        print("  no exclusion data found")
        return

    # Build inverted index
    inv_index = {}
    for gid, info in groups.items():
        for word in info["words"]:
            if word not in inv_index:
                inv_index[word] = []
            inv_index[word].append(gid)

    lines = []
    lines.append("# Mutual-exclusion groups for dynamic axiom injection.\n")
    lines.append("#\n")
    lines.append("# EXCLUSION_GROUPS: group definitions\n")
    lines.append("# EXCLUSION_INDEX: {word: [group_ids]} for O(1) lookup\n")
    lines.append("#\n")
    lines.append(f"EXCLUSION_GROUPS={{\n")
    for gid in sorted(groups):
        g = groups[gid]
        words_str = "[" + ",".join(f'"{w}"' for w in g["words"]) + "]"
        lines.append(f'"{gid}":{{"score":{g["score"]:.2f},"needs_blocker":{g["needs_blocker"]},"words":{words_str}}},\n')
    lines.append("}\n\n")
    lines.append(f"EXCLUSION_INDEX={{\n")
    for k in sorted(inv_index):
        gids_str = "[" + ",".join(f'"{g}"' for g in inv_index[k]) + "]"
        lines.append(f'"{k}":{gids_str},\n')
    lines.append("}\n")
    write_py_file(
        os.path.join(SOLVER_DIR, "data_exclusions.py"),
        "".join(lines),
        "Mutual-exclusion groups for dynamic axiom injection.",
    )
    print(f"  {len(groups)} groups, {len(inv_index)} indexed words")


# ======== main ========

def main():
    print(f"Source: {SCRIPT_DIR}")
    print(f"Target: {SOLVER_DIR}")
    print()
    canonicals = build_canonicals()
    print()
    chain_rejected = build_antonyms(canonicals)
    print()
    build_synonyms()
    print()
    build_exclusions(chain_rejected)
    print()
    print("Done.")


if __name__ == "__main__":
    main()
