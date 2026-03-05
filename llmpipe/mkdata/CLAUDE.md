# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`mkdata/` is a data-generation toolkit that produces synonym/antonym cluster files and gradable-adjective lists used by the broader `nlpsolver` pipeline. It is standalone and does not depend on other `llmpipe` modules.

## Scripts

### `make_anto_synonyms.py` — synonym/antonym cluster builder

Requires heavy dependencies (fastText binary model ~4GB, NLTK WordNet, wordfreq). Run from this directory:

```bash
# Install dependencies
pip install wordfreq fasttext nltk numpy
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"

# Download fastText model (~4.2GB)
wget https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.en.300.bin.gz
gunzip cc.en.300.bin.gz

# Build adjective synonym/antonym clusters (1000 concepts)
python make_anto_synonyms.py --ft_model cc.en.300.bin --pos a --concepts 1000 \
  --out_syn clusters_adjs_syn.csv --out_ant clusters_adjs_ant.csv

# Nouns and verbs follow the same pattern (--pos n, --pos v)
```

**Output format** (CSV):
- Synonyms: `CANONICAL_ID,word1,score1,word2,score2,...`
- Antonyms: same format; `CANONICAL_ID` is shared between synonym and antonym files
- `CANONICAL_ID` format: `LEMMA_POS##` (e.g., `HAPPY_A01`)

**Key parameters:**
- `--concepts N` — number of output clusters (default 1000)
- `--min_zipf F` — minimum word frequency threshold (default 3.5)
- `--syn_min_score` / `--ant_min_score` — confidence thresholds (default 0.50)
- `--require_min_syn N` — skip clusters with fewer than N synonyms (default 3)
- `--no_filter_rel_adj` — include relational adjectives (e.g., *national*, *historic*)

### `make_gradables.py` — gradable adjective extractor (library module)

Not a standalone script; import `extract_gradable_adjs(docs, nlp)` from it. `docs` is an iterable of raw text strings; `nlp` is a loaded spaCy model. Returns a ranked list of `(lemma, count, deg_rate, comp_rate, scale, score)` tuples. The `scale` field is `"open"` or `"closed"` depending on whether the adjective co-occurs more with degree modifiers (*very*, *extremely*) vs. closed-scale modifiers (*completely*, *perfectly*).

## Input word lists

- `important_words.txt` — graded sight-word list (Dolch-style, ordered by reading level)
- `childwords.txt` — supplementary child vocabulary list

These lists are used as seed/filter inputs for deciding which lemmas to include in generated data files.
