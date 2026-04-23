# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`mkdata/` is a data-generation toolkit that produces synonym/antonym/exclusion
cluster files and gradable-adjective lists used by the broader `nlpsolver`
pipeline. It is standalone and does not depend on other `llmpipe` modules.

The final step of the pipeline (`build_solver_data.py`) generates Python dict
files in `solver/` that are loaded at runtime by the main solver.

## Data Files

### Synonym clusters (`syn_{a,n,v}_10.txt`)

Raw synonym clusters produced by `make_anto_synonyms.py` and expanded by
`harvest_syn_{a,n,v}.py`. Format: `CANONICAL_ID,word1,score1,word2,score2,...`
where `CANONICAL_ID` is `LEMMA_POS##` (e.g. `HAPPY_A01`, `CAR_N01`, `USE_V01`).
Scores are fastText cosine similarities.

- `syn_a_10.txt` -- 587 adjective clusters
- `syn_n_10.txt` -- 1968 noun clusters
- `syn_v_10.txt` -- 1093 verb clusters

### Tier A rewrite tables (`syn_{a,n,v}_rewrite.txt`)

Unconditional `member -> canonical` word substitutions applied post-clausification
by `semnormalize.py`. Only high-confidence, low-ambiguity pairs survive the
filters in `pick_canonicals_{a,n,v}.py`. Format: `member,canonical`.

- `syn_a_rewrite.txt` -- 416 adjective rewrites (e.g. `abrasive,rough`)
- `syn_n_rewrite.txt` -- 218 noun rewrites (e.g. `automobile,car`)
- `syn_v_rewrite.txt` -- 124 verb rewrites (e.g. `utilize,use`)

### Tier B soft axiom pairs (`syn_{a,n,v}_soft_axioms.txt`)

Weaker synonym pairs emitted as biconditional axioms at runtime, only when
relevant to the current problem. Includes pairs from UNSAFE clusters and
dropped members of SAFE clusters. Format: `word_a,word_b,score`.

- `syn_a_soft_axioms.txt` -- 2496 adjective pairs
- `syn_n_soft_axioms.txt` -- 6218 noun pairs
- `syn_v_soft_axioms.txt` -- 4103 verb pairs

### Antonym pairs (`ant_{a,n,v}.txt`)

Directional antonym pairs from WordNet `lemma.antonyms()`. At runtime,
encountering an antonym word flips atom polarity and substitutes the canonical.
Format: `CANONICAL_ID,word1,score1,word2,score2,...`

- `ant_a.txt` -- 1483 adjective antonym entries
- `ant_n.txt` -- 375 noun antonym entries
- `ant_v.txt` -- 295 verb antonym entries

`build_antonyms` in `build_solver_data.py` applies two symmetric guards to
avoid chain-contamination with `CANONICALS`:
1. `word in CANONICALS` — skip; Pass 2 canonical sub would shadow the
   antonym fold.
2. `canonical in CANONICALS` — don't rewrite; Pass 2 would chain-substitute
   the target to an unrelated sense (e.g. `open → close → near`). These
   rejected pairs are deferred to `build_exclusions` and emitted as
   defeasible adjective mutual-exclusion groups `ANT_<W1>_<W2>` (same
   runtime treatment as `MANUAL_ADJ_*` / `MANUAL_ANTONYMS`).

### Exclusion groups (`excl_a.txt`)

Mutual-exclusion groups where at most one member can be true of an entity at a
time (colors, months, nationalities, etc.). Injected as pairwise exclusion
clauses at runtime when 2+ members appear in the problem.
Format: `GROUP_ID,source,score,needs_blocker,word1,word2,...`

- `needs_blocker=0`: hard exclusion (months, days, compass directions)
- `needs_blocker=1`: defeasible exclusion with `$block` (colors, nationalities --
  a thing can occasionally be multi-colored)

~60 groups in `excl_a.txt`. After `build_solver_data.py` the runtime dict
`data_exclusions.py` has ~123 groups, 441 indexed words (includes
synthetic `MANUAL_ADJ_*` and `ANT_*` groups).

## Build Pipeline

```
Step 1: Cluster generation (heavy -- requires fastText model + NLTK WordNet)
  make_anto_synonyms.py --pos {a,n,v}
    -> syn_{a,n,v}_10.txt   (synonym clusters)
    -> ant_{a,n,v}.txt       (antonym pairs)

Step 2: Cluster expansion (adds new members via fastText + WordNet synset check)
  harvest_syn_{a,n,v}.py
    -> modifies syn_{a,n,v}_10.txt in place

Step 3: Canonical selection + Tier A/B emission
  pick_canonicals_{a,n,v}.py --apply --emit
    -> syn_{a,n,v}_rewrite.txt       (Tier A hard rewrites)
    -> syn_{a,n,v}_soft_axioms.txt   (Tier B soft axiom pairs)
    -> modifies syn_{a,n,v}_10.txt   (drops unsafe members)

Step 4: Exclusion group construction
  build_exclusion_data.py
    -> excl_a.txt

Step 5: Generate solver runtime files (fast -- reads .txt, writes .py dicts)
  build_solver_data.py
    -> solver/data_canonicals.py   (~752 Tier A entries, all POS merged)
    -> solver/data_antonyms.py     (~850 directional antonym pairs)
    -> solver/data_synonyms.py     (~12K words, ~12.8K soft synonym pairs)
    -> solver/data_exclusions.py   (~123 groups, ~441 indexed words)
```

Steps 1-4 are heavy and run rarely (when rebuilding clusters from scratch).
Step 5 is fast and should be re-run whenever any source .txt file changes:

```bash
cd mkdata && python3 build_solver_data.py
```

## Tier A Filter Parameters

### Adjectives (`pick_canonicals_a.py`)
- `MIN_ADJ_ZIPF = 3.0` -- winner frequency gate

### Nouns (`pick_canonicals_n.py`)
- `MIN_ZIPF = 4.0`, `MIN_NOUN_FRACTION = 0.25`, `MIN_DOMINANCE_MARGIN = 0.5`
- `MIN_MEMBER_ZIPF = 3.3`, `MAX_WINNER_SENSE_RANK = 0`
- `MAX_MEMBER_NOUN_SYNSETS = 3`, `MIN_MEMBER_SIMILARITY = 0.88`
- `BLOCKED_PAIRS` -- 18 manual blocklist entries (proper nouns, religious terms, etc.)

### Verbs (`pick_canonicals_v.py`)
- Same structure as nouns with: `MIN_MEMBER_ZIPF = 3.0`
- `MAX_MEMBER_VERB_SYNSETS = 5` (higher than nouns -- verbs are more polysemous)

## Other Scripts

### `make_anto_synonyms.py` -- synonym/antonym cluster builder

Requires heavy dependencies (fastText binary model ~4GB, NLTK WordNet, wordfreq).

```bash
pip install wordfreq fasttext nltk numpy
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"

wget https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.en.300.bin.gz
gunzip cc.en.300.bin.gz

python make_anto_synonyms.py --ft_model cc.en.300.bin --pos a --concepts 1000 \
  --out_syn clusters_adjs_syn.csv --out_ant clusters_adjs_ant.csv
```

### `make_gradables.py` -- gradable adjective extractor (library module)

Not a standalone script; import `extract_gradable_adjs(docs, nlp)` from it.

## Input word lists

- `important_words.txt` -- graded sight-word list (Dolch-style, ordered by reading level)
- `childwords.txt` -- supplementary child vocabulary list

These lists are used as seed/filter inputs for deciding which lemmas to include in generated data files.
