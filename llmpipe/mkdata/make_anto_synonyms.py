#!/usr/bin/env python3
"""
Build synonym and antonym clusters for frequent English lemmas.

Outputs:
  - synonyms: CANONICAL_ID,syn1,sim1,syn2,sim2,...
  - antonyms: CANONICAL_ID,ant1,score1,ant2,score2,...

Dependencies:
  pip install wordfreq fasttext nltk numpy
  python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"

Requires:
  A fastText .bin model, e.g. cc.en.300.bin

----------

  python build_syn_ant_clusters.py \
  --ft_model cc.en.300.bin \
  --pos a \
  --concepts 1000 \
  --out_syn clusters_adjs_syn.csv \
  --out_ant clusters_adjs_ant.csv
  
  python build_syn_ant_clusters.py --ft_model cc.en.300.bin --pos n --concepts 1000 --out_syn clusters_n_syn.csv --out_ant clusters_n_ant.csv
python build_syn_ant_clusters.py --ft_model cc.en.300.bin --pos v --concepts 1000 --out_syn clusters_v_syn.csv --out_ant clusters_v_ant.csv

---------

The file you want is:

cc.en.300.bin

It is ~4.2GB.

? Step 1 -- Go to fastText pretrained vectors page

Official location:
https://fasttext.cc/docs/en/crawl-vectors.html

Look for:

English - Common Crawl (600B tokens) - 300 dimensions

Download:

cc.en.300.bin.gz
? Step 2 -- Download from command line (Linux/macOS)
wget https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.en.300.bin.gz

wget https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.en.300.bin.gz

gunzip cc.en.300.bin.gz

import fasttext

model = fasttext.load_model("cc.en.300.bin")
print(model.get_dimension())

---

Option 2 (Smaller model, faster loading)

If 4GB is too heavy, you can use:

wiki-news-300d-1M-subword.bin

Download:

wget https://dl.fbaipublicfiles.com/fasttext/vectors-english/wiki-news-300d-1M-subword.bin.gz
gunzip wiki-news-300d-1M-subword.bin.gz

Size:

~1GB uncompressed

Quality:

Slightly lower coverage than Common Crawl

Still excellent for synonym work
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
import fasttext
from wordfreq import iter_wordlist, zipf_frequency
from nltk.corpus import wordnet as wn


REL_ADJ_SUFFIX = re.compile(r".*(al|ic|ical|ary|ory|ive|ian|ese)$")
ALPHA_OR_UNDERSCORE = re.compile(r"^[a-z_]+$")


def cosine(u: np.ndarray, v: np.ndarray) -> float:
    nu = float(np.linalg.norm(u))
    nv = float(np.linalg.norm(v))
    if nu == 0.0 or nv == 0.0:
        return 0.0
    return float(np.dot(u, v) / (nu * nv))


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def norm_form(s: str) -> str:
    s = s.lower().strip()
    s = s.replace("-", "_")
    return s


def is_good_surface_form(s: str) -> bool:
    s = norm_form(s)
    if not s or len(s) == 1:
        return False
    if not ALPHA_OR_UNDERSCORE.match(s):
        return False
    return True


def wn_pos(letter: str) -> str:
    letter = letter.lower()
    if letter == "n":
        return wn.NOUN
    if letter == "v":
        return wn.VERB
    if letter == "a":
        return wn.ADJ
    raise ValueError(f"Unsupported POS: {letter} (use n|v|a)")


def canonical_id(base_lemma: str, pos_letter: str, sense_index: int) -> str:
    return f"{base_lemma.upper()}_{pos_letter.upper()}{sense_index:02d}"


def fasttext_vec(ft, token: str) -> np.ndarray:
    return np.asarray(ft.get_word_vector(token), dtype=np.float32)


def membership_score(sim_embed01: float) -> float:
    # True synset co-membership gets a high baseline.
    return 0.70 + 0.30 * clamp01(sim_embed01)


def related_score(sim_embed01: float, sim_wn01: float) -> float:
    return 0.50 * clamp01(sim_embed01) + 0.50 * clamp01(sim_wn01)


def wup_similarity(S1, S2) -> float:
    if S1 is None or S2 is None:
        return 0.0
    sim = S1.wup_similarity(S2)
    return float(sim) if sim is not None else 0.0


def choose_seed_lemmas(
    pos_letter: str, n_seeds: int, min_zipf: float, extra_seeds: Optional[Sequence[str]] = None
) -> List[str]:
    pos = wn_pos(pos_letter)
    seen: Set[str] = set()
    seeds: List[str] = []

    # Prepend extra seeds (e.g. from childwords list) regardless of zipf threshold
    for w in (extra_seeds or []):
        w = norm_form(w)
        if not is_good_surface_form(w) or w in seen:
            continue
        wn_query = w.replace("_", " ")
        if wn.synsets(wn_query, pos=pos):
            seeds.append(w)
            seen.add(w)

    for w in iter_wordlist("en", wordlist="best"):
        w = norm_form(w)
        if not is_good_surface_form(w) or w in seen:
            continue
        if zipf_frequency(w, "en") < min_zipf:
            break
        wn_query = w.replace("_", " ")
        if wn.synsets(wn_query, pos=pos):
            seeds.append(w)
            seen.add(w)
            if len(seeds) >= n_seeds:
                break
    return seeds


def pick_canonical_synset_for_lemma(lemma: str, pos_letter: str):
    pos = wn_pos(pos_letter)
    wn_query = lemma.replace("_", " ")
    syns = wn.synsets(wn_query, pos=pos)
    return syns[0] if syns else None


def synset_canonical_lemma(S, pos_letter: str) -> str:
    names = [norm_form(x) for x in S.lemma_names()]
    names = [x for x in names if is_good_surface_form(x)]
    if not names:
        return ""
    names.sort(key=lambda w: zipf_frequency(w, "en"), reverse=True)
    return names[0]


def antonyms_from_synset(S) -> Set[str]:
    """
    Collect antonyms for ANY lemma in the synset (higher recall, still precise).
    """
    out: Set[str] = set()
    for l in S.lemmas():
        for ant in l.antonyms():
            out.add(norm_form(ant.name()))
    return {w for w in out if is_good_surface_form(w)}


def build_synonyms(
    ft,
    S,
    pos_letter: str,
    min_score: float,
    max_syn: int,
    require_min: int,
    filter_rel_adj: bool,
) -> Tuple[str, List[Tuple[str, float]]]:
    canon = synset_canonical_lemma(S, pos_letter)
    if not canon:
        return "", []

    antset = antonyms_from_synset(S)  # to avoid leaking antonyms into synonyms
    v0 = fasttext_vec(ft, canon)

    best: Dict[str, float] = {}

    # 1) in-synset synonyms (high precision)
    for w in S.lemma_names():
        w = norm_form(w)
        if w == canon or w in antset:
            continue
        if not is_good_surface_form(w):
            continue
        if pos_letter == "a" and filter_rel_adj and REL_ADJ_SUFFIX.match(w):
            continue

        vw = fasttext_vec(ft, w)
        sim01 = (cosine(v0, vw) + 1.0) / 2.0
        score = membership_score(sim01)
        best[w] = max(best.get(w, 0.0), score)

    # 2) expansions if needed
    if len(best) < require_min:
        extra: Set[str] = set()
        if pos_letter == "a":
            for r in (S.similar_tos() + S.also_sees()):
                extra |= {norm_form(x) for x in r.lemma_names()}
        else:
            for r in (S.hypernyms() + S.hyponyms()):
                extra |= {norm_form(x) for x in r.lemma_names()}

        for w in extra:
            if w == canon or w in best or w in antset:
                continue
            if not is_good_surface_form(w):
                continue
            if pos_letter == "a" and filter_rel_adj and REL_ADJ_SUFFIX.match(w):
                continue

            vw = fasttext_vec(ft, w)
            sim_e01 = (cosine(v0, vw) + 1.0) / 2.0

            if pos_letter in ("n", "v"):
                S2 = pick_canonical_synset_for_lemma(w, pos_letter)
                sim_w01 = wup_similarity(S, S2)
                score = related_score(sim_e01, sim_w01)
            else:
                score = 0.55 * sim_e01  # conservative

            if score >= min_score:
                best[w] = max(best.get(w, 0.0), score)

    ranked = sorted(best.items(), key=lambda x: x[1], reverse=True)
    ranked = [(w, sc) for (w, sc) in ranked if sc >= min_score][:max_syn]
    return canon, ranked


def antonym_score(ft, canon: str, ant: str) -> float:
    """
    Antonym confidence score in [0,1]:
      - WordNet antonym edge gives a high base
      - Embedding opposition gives some shaping but is not fully trusted
    """
    v0 = fasttext_vec(ft, canon)
    va = fasttext_vec(ft, ant)
    sim = cosine(v0, va)                  # [-1,1]
    sim01 = (sim + 1.0) / 2.0            # [0,1]
    opposition = 1.0 - sim01             # higher means more "opposite" in embedding space

    # Base for a WordNet antonym edge + modest shaping:
    return clamp01(0.75 + 0.25 * opposition)


def build_antonyms(
    ft,
    S,
    pos_letter: str,
    min_score: float,
    max_ant: int,
    filter_rel_adj: bool,
) -> Tuple[str, List[Tuple[str, float]]]:
    canon = synset_canonical_lemma(S, pos_letter)
    if not canon:
        return "", []

    ants = antonyms_from_synset(S)
    # Don't include canon itself; and apply same surface/relational filters
    cleaned: List[str] = []
    for a in ants:
        if a == canon:
            continue
        if pos_letter == "a" and filter_rel_adj and REL_ADJ_SUFFIX.match(a):
            continue
        cleaned.append(a)

    scored: Dict[str, float] = {}
    for a in cleaned:
        sc = antonym_score(ft, canon, a)
        if sc >= min_score:
            scored[a] = max(scored.get(a, 0.0), sc)

    ranked = sorted(scored.items(), key=lambda x: x[1], reverse=True)[:max_ant]
    return canon, ranked


def build_clusters_for_pos(
    ft,
    pos_letter: str,
    n_concepts: int,
    n_seed_lemmas: int,
    min_zipf: float,
    syn_min_score: float,
    ant_min_score: float,
    max_syn: int,
    max_ant: int,
    require_min_syn: int,
    filter_rel_adj: bool,
    extra_seeds: Optional[Sequence[str]] = None,
) -> Tuple[List[str], List[str]]:
    seeds = choose_seed_lemmas(pos_letter, n_seed_lemmas, min_zipf=min_zipf, extra_seeds=extra_seeds)

    synset_order: List = []
    seen: Set = set()
    for w in seeds:
        S = pick_canonical_synset_for_lemma(w, pos_letter)
        if S is None:
            continue
        if S not in seen:
            seen.add(S)
            synset_order.append(S)
        if len(synset_order) >= n_concepts * 3:
            break

    syn_lines: List[str] = []
    ant_lines: List[str] = []
    canon_name_counts: Dict[str, int] = defaultdict(int)

    for S in synset_order:
        canon, syns = build_synonyms(
            ft, S, pos_letter,
            min_score=syn_min_score,
            max_syn=max_syn,
            require_min=require_min_syn,
            filter_rel_adj=filter_rel_adj,
        )
        if not canon or len(syns) < min(3, require_min_syn):
            continue

        canon_name_counts[canon] += 1
        cid = canonical_id(canon, pos_letter, canon_name_counts[canon])

        # synonym line
        parts = [cid]
        for w, sc in syns:
            parts.append(w); parts.append(f"{sc:.2f}")
        syn_lines.append(",".join(parts))

        # antonym line (may be empty; that's fine)
        _, ants = build_antonyms(
            ft, S, pos_letter,
            min_score=ant_min_score,
            max_ant=max_ant,
            filter_rel_adj=filter_rel_adj,
        )
        ant_parts = [cid]
        for w, sc in ants:
            ant_parts.append(w); ant_parts.append(f"{sc:.2f}")
        ant_lines.append(",".join(ant_parts))

        if len(syn_lines) >= n_concepts:
            break

    return syn_lines, ant_lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ft_model", required=True, help="Path to fastText .bin model (e.g., cc.en.300.bin)")
    ap.add_argument("--pos", required=True, choices=["n", "a", "v"], help="POS: n (nouns), a (adjs), v (verbs)")
    ap.add_argument("--concepts", type=int, default=1000)
    ap.add_argument("--seed_lemmas", type=int, default=15000)
    ap.add_argument("--min_zipf", type=float, default=3.5)

    ap.add_argument("--syn_min_score", type=float, default=0.50)
    ap.add_argument("--ant_min_score", type=float, default=0.50)

    ap.add_argument("--max_syn", type=int, default=10)
    ap.add_argument("--max_ant", type=int, default=10)
    ap.add_argument("--require_min_syn", type=int, default=3)

    ap.add_argument("--no_filter_rel_adj", action="store_true")
    ap.add_argument("--out_syn", required=True, help="Output CSV for synonyms")
    ap.add_argument("--out_ant", required=True, help="Output CSV for antonyms")
    ap.add_argument("--extra_seeds", default=None,
                    help="File with extra seed words to prepend (one per line, * suffix stripped)")

    args = ap.parse_args()
    ft = fasttext.load_model(args.ft_model)

    extra_seeds: Optional[List[str]] = None
    if args.extra_seeds:
        with open(args.extra_seeds, encoding="utf-8") as fh:
            extra_seeds = [
                line.strip().rstrip("*").strip()
                for line in fh
                if line.strip() and not line.startswith("\t")
            ]

    syn_lines, ant_lines = build_clusters_for_pos(
        ft=ft,
        pos_letter=args.pos,
        n_concepts=args.concepts,
        n_seed_lemmas=args.seed_lemmas,
        min_zipf=args.min_zipf,
        syn_min_score=args.syn_min_score,
        ant_min_score=args.ant_min_score,
        max_syn=args.max_syn,
        max_ant=args.max_ant,
        require_min_syn=args.require_min_syn,
        filter_rel_adj=(not args.no_filter_rel_adj),
        extra_seeds=extra_seeds,
    )

    with open(args.out_syn, "w", encoding="utf-8") as f:
        for line in syn_lines:
            f.write(line + "\n")

    with open(args.out_ant, "w", encoding="utf-8") as f:
        for line in ant_lines:
            f.write(line + "\n")

    print(f"Wrote {len(syn_lines)} synonym clusters to {args.out_syn}")
    print(f"Wrote {len(ant_lines)} antonym clusters to {args.out_ant} (same canonical IDs)")


if __name__ == "__main__":
    main()