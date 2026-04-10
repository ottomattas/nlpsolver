#!/usr/bin/env python3
"""
Build antonym and mutual-exclusion data files from WordNet.

Antonym extraction (all three POSes):
  ant_a.txt / ant_n.txt / ant_v.txt -- WordNet antonym pairs in Format A:
       CANONICAL_ID, antonym1, score1, antonym2, score2, ...
       Antonyms come from exhaustive WordNet lemma.antonyms() walks.

Exclusion groups (adjectives only — verbs and nouns rarely have clean
mutually-exclusive sibling sets):
  excl_a.txt -- Mutual-exclusion groups, one per line:
       GROUP_ID, source, score, needs_blocker, word1, word2, ..., wordN

       needs_blocker is 0 or 1: 1 means the cluster should be guarded by a
       blocker predicate at axiom-emission time (e.g. colors need a
       multicolored blocker; months, days and class levels do not).

       Sources:
         1. WN_ATTRIBUTE_KEEP allowlist — a tiny curated set of WordNet
            synset.attribute() groups known to be genuine mutual-exclusion
            groups. Most wn_attribute groups are 2-element antonym pairs
            or synonym/antonym mixtures so the default is "drop".
         2. Hyponyms of noun categories mapped to adjective lemmas
            (currently COLOR and LANGUAGE).
         3. Manually curated groups for categorical taxonomies that
            WordNet underrepresents (months, days, directions, phases of
            matter, basic colors/shapes/materials, etc.).

WordNet extractions are filtered by zipf_frequency (default 3.0) so only
common words are kept. Manual groups bypass the zipf filter.

Only groups with >= 3 members are kept — two-element groups are dropped
because they are almost always plain antonym pairs which belong in ant_a.txt.

Run:
    venv/bin/python build_exclusion_data.py              # all outputs
    venv/bin/python build_exclusion_data.py --no_excl    # antonyms only
    venv/bin/python build_exclusion_data.py --only_excl  # exclusions only
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from typing import Iterable

from nltk.corpus import wordnet as wn
from wordfreq import zipf_frequency


# ---------------------------------------------------------------------------
# Filtering helpers
# ---------------------------------------------------------------------------

_BAD_RX = re.compile(r"^[^a-z]")  # rule out anything not starting with a-z


def norm(w: str) -> str:
    return w.lower().replace("_", " ").strip()


def is_good_word(w: str, min_zipf: float, allow_phrase: bool = False) -> bool:
    if not w or _BAD_RX.match(w):
        return False
    if not allow_phrase and " " in w:
        return False
    if "-" in w and len(w) > 20:
        return False
    return zipf_frequency(w, "en") >= min_zipf


def adj_lemma_exists(w: str) -> bool:
    """True if w has a WordNet adjective synset (a or s)."""
    return bool(wn.synsets(w.replace(" ", "_"), pos="a") or
                wn.synsets(w.replace(" ", "_"), pos="s"))


# ---------------------------------------------------------------------------
# Antonym extraction
# ---------------------------------------------------------------------------

def _pos_synsets(pos: str):
    """Return iterable of all synsets for a POS. For adjectives we walk both
    a (head) and s (satellite) synsets — both can have antonyms."""
    if pos == "a":
        return list(wn.all_synsets(pos="a")) + list(wn.all_synsets(pos="s"))
    return list(wn.all_synsets(pos=pos))


def extract_antonym_pairs(pos: str, min_zipf: float) -> dict[str, list[tuple[str, float]]]:
    """Walk all synsets for a POS, collect WordNet antonym pairs.

    Returns dict: canonical_word -> list of (antonym_word, score), score 0.95.
    Each antonym pair appears once under the alphabetically smaller canonical.
    """
    raw_pairs: set[tuple[str, str]] = set()
    for s in _pos_synsets(pos):
        for l in s.lemmas():
            for ant in l.antonyms():
                a = norm(l.name())
                b = norm(ant.name())
                if a == b:
                    continue
                if not is_good_word(a, min_zipf) or not is_good_word(b, min_zipf):
                    continue
                # Canonicalize: alphabetical to avoid duplicates
                raw_pairs.add(tuple(sorted((a, b))))

    # Group antonyms by canonical (one row per word, listing its antonyms).
    # We list both directions so that "good" → bad and "bad" → good are both findable.
    by_canon: dict[str, set[str]] = defaultdict(set)
    for a, b in raw_pairs:
        by_canon[a].add(b)
        by_canon[b].add(a)

    # Sort antonyms by frequency (most common first).
    out: dict[str, list[tuple[str, float]]] = {}
    for canon, ants in by_canon.items():
        ranked = sorted(ants, key=lambda w: -zipf_frequency(w, "en"))
        out[canon] = [(w, 0.95) for w in ranked]
    return out


def write_antonym_file(by_canon: dict[str, list[tuple[str, float]]], path: str, pos: str):
    """Write Format A: CANONICAL_ID,word1,score1,word2,score2,..."""
    pos_letter = pos.upper()
    canons = sorted(by_canon.keys(), key=lambda w: -zipf_frequency(w, "en"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Antonym pairs extracted from WordNet lemma.antonyms() (POS={pos})\n")
        f.write("# Format: CANONICAL_ID,word1,score1,word2,score2,...\n")
        for c in canons:
            cid = re.sub(r"[^A-Z0-9_]", "_", c.upper()) + f"_{pos_letter}01"
            pairs = by_canon[c]
            row = cid + "," + ",".join(f"{w},{s:.2f}" for w, s in pairs)
            f.write(row + "\n")
    print(f"Wrote {len(canons)} antonym entries to {path}")


# ---------------------------------------------------------------------------
# Exclusion groups: WordNet attribute() relation
# ---------------------------------------------------------------------------

# synset.attributes() is fundamentally noisy — it collects adjectives that
# share an attribute noun, but those include antonym pairs (right/wrong),
# synonym-only groups (cyclic/cyclical), and 2+2 antonym+synonym mixtures
# (correct/incorrect/right/wrong). The only reliable way to use it is an
# explicit allowlist of synsets known to yield genuine mutual-exclusion
# groups. Each entry maps synset_name -> needs_blocker (0 or 1).
WN_ATTRIBUTE_KEEP: dict[str, int] = {
    "status.n.01":            0,   # social/class levels — hard exclusive
    "temperature.n.01":       1,   # scale position; parts/time can differ
    "orientation.n.03":       1,   # geometric alignment; parts can differ
    "temporal_relation.n.01": 0,   # ordering unique for a given pair
    "stature.n.02":           1,   # relative size
}


def extract_attribute_groups(min_zipf: float
                             ) -> list[tuple[str, str, list[str], int]]:
    """Walk all adjective synsets; group lemmas sharing an attribute noun.
    Only synsets in WN_ATTRIBUTE_KEEP are kept (strict allowlist).

    Returns list of (group_id, source_synset_name, [members], needs_blocker).
    Groups with fewer than 3 members are dropped.
    """
    groups: dict[str, set[str]] = defaultdict(set)
    for s in list(wn.all_synsets(pos="a")) + list(wn.all_synsets(pos="s")):
        for attr in s.attributes():
            if attr.name() not in WN_ATTRIBUTE_KEEP:
                continue
            for l in s.lemma_names():
                w = norm(l)
                if is_good_word(w, min_zipf):
                    groups[attr.name()].add(w)

    out: list[tuple[str, str, list[str], int]] = []
    for synset_name, members in groups.items():
        if len(members) < 3:
            continue
        stem = synset_name.split(".")[0].upper()
        blocker = WN_ATTRIBUTE_KEEP[synset_name]
        ranked = sorted(members, key=lambda w: -zipf_frequency(w, "en"))
        out.append((stem, synset_name, ranked, blocker))
    out.sort(key=lambda t: -len(t[2]))
    return out


# ---------------------------------------------------------------------------
# Exclusion groups: noun hyponyms mapped to adjective lemmas
# ---------------------------------------------------------------------------

# Top-level noun categories whose hyponyms typically have adjective forms
# of the same lemma (e.g. "red" the color noun and "red" the adjective).
#
# After testing, almost every useful category turned out to be either
# too noisy (material.n.01 pulls in unrelated adjective homonyms) or
# incomplete (natural_language.n.01 misses the major languages and
# pulls in family/region names). Manual lists are cleaner for all
# current needs. This stub is kept for future use if a tight noun
# synset is found whose hyponyms are all real adjectives.
NOUN_CATEGORY_ROOTS: list[tuple[str, list[str], int, float | None, int]] = [
    # (group_id, list of noun synset names, max_depth, min_zipf_override, needs_blocker)
]


def collect_hyponyms(root: wn.synset, max_depth: int) -> list[wn.synset]:
    out = []
    frontier = [(root, 0)]
    seen = set()
    while frontier:
        s, d = frontier.pop()
        if s.name() in seen:
            continue
        seen.add(s.name())
        out.append(s)
        if d < max_depth:
            for h in s.hyponyms():
                frontier.append((h, d + 1))
    return out


def extract_noun_category_groups(default_min_zipf: float
                                 ) -> list[tuple[str, str, list[str], int]]:
    """For each NOUN_CATEGORY_ROOTS entry, collect adjective lemmas matching
    the noun hyponym lemma names. Skip single-letter or 2-letter matches
    (those are chemical symbols and abbreviations, not real adjectives).

    Returns list of (group_id, source, members, needs_blocker)."""
    out = []
    for gid, root_names, depth, min_zipf_override, blocker in NOUN_CATEGORY_ROOTS:
        mz = default_min_zipf if min_zipf_override is None else min_zipf_override
        members: set[str] = set()
        sources: list[str] = []
        for rn in root_names:
            try:
                root = wn.synset(rn)
            except Exception:
                continue
            sources.append(rn)
            for h in collect_hyponyms(root, depth):
                for ln in h.lemma_names():
                    w = norm(ln)
                    if len(w) < 3:
                        continue
                    if not is_good_word(w, mz):
                        continue
                    if not adj_lemma_exists(w):
                        continue
                    members.add(w)
        if len(members) < 3:
            continue
        ranked = sorted(members, key=lambda w: -zipf_frequency(w, "en"))
        out.append((gid, "+".join(sources), ranked, blocker))
    return out


# ---------------------------------------------------------------------------
# Manually curated groups for cases WordNet misses or under-covers
# ---------------------------------------------------------------------------

# Manual groups. Each entry is (group_id, needs_blocker, [words]).
#
# needs_blocker=0 means the cluster's mutual exclusivity is near-absolute
# (one month per date, one day of the week, one cardinal direction pointed
# at, one social-class level per person). needs_blocker=1 means exclusivity
# holds normally but mixtures/partial states/multi-valued descriptions are
# common enough that a guard predicate is needed (multicolored objects,
# composite materials, multilingual documents, etc.).
#
# Groups that used to live here but were removed because they are not
# genuine mutual-exclusion sets: SIZE_BASIC (fuzzy scale), SPEED
# (mostly synonyms of "fast"), BRIGHTNESS, HARDNESS, QUALITY_BASIC,
# BEAUTY, HAPPINESS (subjective scales), AGE_BASIC (mixed antonym+
# synonym), LENGTH/HEIGHT/WIDTH/WEIGHT (antonym pairs), INTACTNESS,
# OPENNESS, CLEANNESS (scale positions, not exclusive states).
MANUAL_GROUPS: list[tuple[str, int, list[str]]] = [
    # --- Temporal categorical taxonomies (hard exclusive) ---
    ("MONTH", 0, ["january", "february", "march", "april", "may", "june",
                  "july", "august", "september", "october", "november",
                  "december"]),
    ("DAY_OF_WEEK", 0, ["monday", "tuesday", "wednesday", "thursday", "friday",
                        "saturday", "sunday"]),
    ("SEASON", 0, ["spring", "summer", "autumn", "fall", "winter"]),

    # --- Spatial/directional taxonomies (hard exclusive for a single vector) ---
    ("DIRECTION_CARDINAL", 0, ["north", "south", "east", "west"]),
    ("COMPASS_8", 0, ["north", "south", "east", "west",
                      "northeast", "northwest", "southeast", "southwest"]),
    ("HEMISPHERE", 0, ["northern", "southern", "eastern", "western"]),
    ("AXIS_ALIGNMENT", 0, ["horizontal", "vertical", "diagonal"]),
    ("DIMENSIONALITY", 0, ["one-dimensional", "two-dimensional",
                           "three-dimensional"]),

    # --- Physical state / classification (hard exclusive for a pure sample) ---
    ("PHASE_OF_MATTER", 0, ["solid", "liquid", "gaseous", "plasma"]),

    # --- Colors (need blocker: multicolored entities) ---
    ("COLOR_BASIC", 1, ["red", "blue", "green", "yellow", "orange", "purple",
                        "pink", "brown", "black", "white", "gray", "grey"]),
    ("COLOR_EXTRA", 1, ["beige", "tan", "navy", "maroon", "crimson", "scarlet",
                        "turquoise", "cyan", "magenta", "indigo", "violet",
                        "olive", "teal", "khaki", "amber", "ivory"]),

    # --- Languages (need blocker: multilingual text) ---
    ("LANGUAGE", 1, ["english", "french", "spanish", "german", "italian",
                     "portuguese", "russian", "chinese", "japanese", "korean",
                     "arabic", "hindi", "greek", "latin", "hebrew", "turkish",
                     "polish", "dutch", "swedish", "thai", "vietnamese",
                     "czech", "hungarian"]),

    # --- Nationalities / major cultural identities ---
    # (need blocker: dual/multi-national identity, diasporas)
    ("NATIONALITY_MAJOR", 1, ["american", "british", "french", "german",
                              "italian", "spanish", "russian", "chinese",
                              "japanese", "korean", "indian", "brazilian",
                              "mexican", "canadian", "australian", "dutch",
                              "polish", "turkish", "egyptian", "iranian"]),

    # --- Shapes (need blocker: composite/complex shapes) ---
    ("SHAPE_BASIC", 1, ["round", "square", "triangular", "oval", "rectangular",
                        "circular", "spherical", "cubic", "flat", "curved"]),

    # --- Materials (need blocker: composite materials) ---
    ("MATERIAL_BASIC", 1, ["wooden", "metal", "metallic", "plastic", "glass",
                           "stone", "paper", "leather", "ceramic", "rubber",
                           "concrete", "cloth"]),
    ("METAL_TYPE", 1, ["iron", "steel", "copper", "bronze", "golden",
                       "silver", "aluminum", "titanium", "brass"]),
    ("FABRIC_TYPE", 1, ["cotton", "woolen", "silk", "linen", "polyester",
                        "nylon", "denim", "suede", "velvet"]),
    ("WOOD_TYPE", 1, ["oak", "pine", "maple", "birch", "cherry", "mahogany",
                      "teak", "cedar", "bamboo"]),

    # --- Scale-position groups (need blocker: parts of a thing can differ) ---
    ("TEMPERATURE_BASIC", 1, ["hot", "cold", "warm", "cool", "freezing",
                              "boiling", "lukewarm", "tepid"]),
    ("WETNESS", 1, ["wet", "dry", "damp", "moist", "soaked", "arid"]),

    # --- Tastes (need blocker: mixed flavors) ---
    ("TASTE", 1, ["sweet", "sour", "salty", "bitter", "umami"]),

    # --- Religion (need blocker: interfaith/multi-religious identity) ---
    ("RELIGION", 1, ["christian", "muslim", "jewish", "hindu", "buddhist",
                     "atheist", "agnostic"]),

    # --- Weather conditions (need blocker: conditions often mix) ---
    ("WEATHER_CONDITION", 1, ["sunny", "cloudy", "rainy", "snowy", "windy",
                              "foggy", "stormy", "clear", "overcast",
                              "misty", "hazy"]),

    # --- Cooking methods applied to prepared food as adjectives ---
    # (need blocker: many dishes involve multiple methods — e.g. "braised
    # and grilled")
    ("COOKING_METHOD", 1, ["baked", "boiled", "fried", "grilled", "roasted",
                           "steamed", "raw", "sauteed", "poached", "braised",
                           "smoked"]),

    # --- Government / political system types (need blocker: hybrid regimes) ---
    ("GOVERNMENT_TYPE", 1, ["democratic", "authoritarian", "monarchic",
                            "republican", "socialist", "communist",
                            "capitalist", "fascist", "theocratic",
                            "totalitarian"]),

    # --- Rock types (hard geological classification) ---
    ("ROCK_TYPE", 0, ["igneous", "sedimentary", "metamorphic"]),

    # --- Animal biological class (hard taxonomic classification) ---
    ("ANIMAL_CLASS", 0, ["mammalian", "reptilian", "avian", "amphibian",
                         "piscine", "insectile"]),

    # --- Art movements (need blocker: works can blend styles) ---
    ("ART_MOVEMENT", 1, ["cubist", "impressionist", "expressionist",
                         "surrealist", "abstract", "realist", "baroque",
                         "renaissance", "romantic", "modernist", "gothic"]),

    # --- Architectural styles (need blocker: eclectic buildings) ---
    ("ARCHITECTURAL_STYLE", 1, ["gothic", "baroque", "renaissance",
                                "neoclassical", "modernist", "victorian",
                                "colonial", "brutalist", "romanesque"]),

    # --- Visual patterns (need blocker: composite / multi-pattern items) ---
    ("PATTERN", 1, ["striped", "checked", "plaid", "spotted", "floral",
                    "solid", "dotted", "speckled"]),

    # --- Educational levels (hard exclusive for a given program) ---
    ("EDUCATIONAL_LEVEL", 0, ["elementary", "secondary", "tertiary",
                              "undergraduate", "graduate", "postgraduate"]),

    # --- Musical tempos (one tempo per passage — Italian loanwords used
    # adjectivally in music contexts: "an allegro section") ---
    ("MUSICAL_TEMPO", 0, ["largo", "adagio", "andante", "moderato",
                          "allegretto", "allegro", "vivace", "presto"]),

    # --- Event/reporting frequency (one frequency per schedule) ---
    # Found via Kaikki coordinate_terms exploration.
    ("FREQUENCY", 0, ["hourly", "daily", "weekly", "monthly", "quarterly",
                      "yearly", "annual"]),

    # --- Christian denomination (finer-grained than RELIGION; blocker
    # because mixed-denomination families exist). Found via Kaikki. ---
    ("CHRISTIAN_DENOMINATION", 1, ["catholic", "orthodox", "protestant",
                                   "evangelical"]),

    # --- Mathematical growth/progression type (one per function).
    # Found via Kaikki. ---
    ("GROWTH_RATE", 0, ["arithmetic", "geometric", "exponential"]),
]


def manual_groups(min_zipf: float) -> list[tuple[str, str, list[str], int]]:
    """Manual groups bypass the zipf filter — they were chosen by hand.
    Returns (group_id, source, members, needs_blocker)."""
    out = []
    for gid, blocker, words in MANUAL_GROUPS:
        members = [w for w in words if w and not _BAD_RX.match(w)]
        if len(members) >= 3:
            out.append((gid, "manual", members, blocker))
    return out


# ---------------------------------------------------------------------------
# Combine and write exclusion groups
# ---------------------------------------------------------------------------

def write_exclusion_file(groups: list[tuple[str, str, list[str], int]], path: str,
                         score: float = 0.95):
    """Write CSV: GROUP_ID,source,score,needs_blocker,word1,word2,...

    needs_blocker is 0 or 1. Groups are deduplicated by member set
    (keep first source listed)."""
    seen: dict[frozenset, tuple[str, str, list[str], int]] = {}
    for gid, source, members, blocker in groups:
        key = frozenset(members)
        if key in seen:
            continue
        seen[key] = (gid, source, members, blocker)

    with open(path, "w", encoding="utf-8") as f:
        f.write("# Mutual-exclusion groups for adjectives.\n")
        f.write("# Format: GROUP_ID,source,score,needs_blocker,word1,word2,...\n")
        f.write("# needs_blocker is 0 or 1 (1 = cluster needs a guard predicate\n")
        f.write("# at axiom-emission time, e.g. 'multicolored' for COLOR).\n")
        f.write("# Source values: wn_attribute, wn_hyponyms, manual\n")
        ranked = sorted(seen.values(), key=lambda t: (-len(t[2]), t[0]))
        for gid, source, members, blocker in ranked:
            row = (f"{gid},{source},{score:.2f},{blocker},"
                   + ",".join(members))
            f.write(row + "\n")
    print(f"Wrote {len(seen)} exclusion groups to {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min_zipf", type=float, default=3.0,
                    help="Minimum word frequency (zipf) to include (default 3.0)")
    ap.add_argument("--no_excl", action="store_true",
                    help="Skip exclusion-group extraction (antonyms only)")
    ap.add_argument("--only_excl", action="store_true",
                    help="Skip antonym extraction (exclusions only). "
                         "Useful to rebuild excl_a.txt without clobbering "
                         "manually-merged ant_a.txt additions.")
    ap.add_argument("--out_excl", default="excl_a.txt")
    args = ap.parse_args()

    if not args.only_excl:
        for pos in ("a", "n", "v"):
            print(f"== Building antonyms POS={pos} (min_zipf={args.min_zipf}) ==")
            ants = extract_antonym_pairs(pos, args.min_zipf)
            write_antonym_file(ants, f"ant_{pos}.txt", pos)
            print()

    if args.no_excl:
        return

    print(f"== Building exclusion groups (min_zipf={args.min_zipf}) ==")

    attr_groups = extract_attribute_groups(args.min_zipf)
    print(f"  WordNet attribute groups:    {len(attr_groups)}")

    noun_groups = extract_noun_category_groups(args.min_zipf)
    print(f"  Noun-hyponym derived groups: {len(noun_groups)}")

    man_groups = manual_groups(args.min_zipf)
    print(f"  Manually curated groups:     {len(man_groups)}")

    # Tag with source for the file. Each entry is
    # (gid, source, members, needs_blocker).
    tagged = (
        [(gid, "wn_attribute:" + src, m, b) for gid, src, m, b in attr_groups] +
        [(gid, "wn_hyponyms:" + src, m, b) for gid, src, m, b in noun_groups] +
        [(gid, "manual", m, b)             for gid, src, m, b in man_groups]
    )

    write_exclusion_file(tagged, args.out_excl)


if __name__ == "__main__":
    main()
