# mkdata — Synonym/Antonym Data Builder

This directory builds the synonym and antonym data files consumed by the
`nlpsolver` reasoning pipeline. It is self-contained and does not depend on
any other `llmpipe` module.

---

## What is built here

The pipeline produces two kinds of solver data from raw synonym cluster files:

**Hard rewrite table** (`syn_rewrite_<pos>.txt`)
Maps a synonym word to its canonical form when similarity ≥ 0.90.
Used by `logconvert.py` to normalize predicate names before clausification,
so the prover sees one consistent name for a concept.

**Soft axiom file** (`syn_axioms_<pos>.js`)
GK inference rules for weaker synonyms (0.70 ≤ similarity < 0.90).
Passed to the GK prover alongside `axioms_std.js` so it can bridge
near-synonyms during proof search.

One rewrite table and one axiom file are produced per part of speech:
nouns (N), adjectives (A), verbs/relations (V).

---

## Directory layout

```
mkdata/
├── README.md                    # this file
├── CLAUDE.md                    # LLM coding instructions
│
│── Input cluster files (Format A, committed)
├── syn_n_10.txt                 # ~1046 noun synonym clusters
├── syn_a_10.txt                 # ~572  adjective synonym clusters
├── syn_v_10.txt                 # ~999  verb/relation synonym clusters
│
│── Generated output files (committed)
├── syn_rewrite_n.txt            # noun hard rewrite table
├── syn_rewrite_a.txt            # adjective hard rewrite table
├── syn_rewrite_v.txt            # verb hard rewrite table
├── syn_axioms_n.js              # noun soft GK axioms
├── syn_axioms_a.js              # adjective soft GK axioms
├── syn_axioms_v.js              # verb soft GK axioms
│
│── Core scripts (committed)
├── build_syn_data.py            # Format-A -> rewrite table + GK axioms
├── merge.py                     # cluster merger library (used by build_syn_data.py)
├── make_anto_synonyms.py        # build syn/ant cluster files from fastText + WordNet
├── make_gradables.py            # gradable adjective extractor (library module)
│
│── Seed vocabulary lists (committed)
├── childwords.txt               # child vocabulary seed list (used by make_anto_synonyms.py)
│
│── Notes (committed)
├── bridging_notes.txt           # design notes
│
│── Large model files (NOT committed — too large for git)
├── cc.en.300.bin                # fastText Common Crawl model, ~6.7 GB
└── cc.en.300.bin.gz             # compressed original, ~4.5 GB
```

---

## Cluster file format (Format A)

The `syn_*.txt` input files (and antonym files produced by `make_anto_synonyms.py`) use **Format A**:

```
CANONICAL_ID, word1, score1, word2, score2, ...
```

- `CANONICAL_ID` encodes the concept and POS: `FAST_A01`, `CAR_N01`, `THINK_V01`
  - The word before `_<POS><digits>` is the canonical lemma for that cluster.
  - Polysemous words get multiple clusters: `WAY_N01` (manner), `WAY_N02` (means), etc.
- Words are sorted by descending similarity score.
- Scores are cosine similarity of fastText embeddings, blended with WordNet
  Wu-Palmer similarity; range 0.50–1.00 in these files.
- The canonical word itself is **not** listed as a pair — it is implicit in the ID.

Example:
```
FAST_A01,quick,0.95,rapid,0.92,speedy,0.91,swift,0.88,fleet,0.82
```

---

## Scripts

### `build_syn_data.py` — main pipeline (Format A → solver data)

Takes a Format-A cluster file and produces a rewrite table and a GK axiom file.

**Pipeline inside the script:**
1. Convert Format A to Format B (prepend canonical word with score 1.00)
2. Merge overlapping clusters via `merge.py` (clusters whose canonicals
   appear in each other above `tau_merge` are unified)
3. Split merged synonyms into:
   - Hard rewrites (score ≥ `hard_thresh`): written to `syn_rewrite_<pos>.txt`
   - Soft axioms (`soft_min` ≤ score < `hard_thresh`): written to `syn_axioms_<pos>.js`

**Polysemy guard:** a word is only added to the rewrite table if it is not
itself a canonical in any cluster. Canonicals are never rewritten.

**Running (standard):**
```bash
venv/bin/python build_syn_data.py syn_n_10.txt N \
    --tau_merge 0.90 --hard_thresh 0.90 --soft_min 0.70 --max_syn 12

venv/bin/python build_syn_data.py syn_a_10.txt A

venv/bin/python build_syn_data.py syn_v_10.txt V
```

Outputs default to the current directory. Override with `--out_rewrite` and
`--out_axioms`.

**All flags:**
```
input_file       Format-A cluster file
pos              N | A | V
--tau_merge F    Merge threshold (default 0.90)
--hard_thresh F  Hard rewrite threshold (default 0.90)
--soft_min F     Soft axiom lower bound (default 0.70)
--max_syn N      Max synonyms per merged cluster (default 12)
--out_rewrite P  Output rewrite table path
--out_axioms P   Output axiom file path
```

---

### `make_anto_synonyms.py` — build cluster files from scratch

Generates Format-A synonym and antonym cluster files using:
- **fastText** embeddings (`cc.en.300.bin`) for similarity scoring
- **WordNet** (via NLTK) for synset structure and antonym relations
- **wordfreq** for selecting frequent seed lemmas

**Running:**
```bash
# Nouns
venv/bin/python make_anto_synonyms.py \
    --ft_model cc.en.300.bin --pos n --concepts 1000 \
    --out_syn syn_n_10.txt --out_ant ant_n.txt

# Adjectives
venv/bin/python make_anto_synonyms.py \
    --ft_model cc.en.300.bin --pos a --concepts 1000 \
    --out_syn syn_a_10.txt --out_ant ant_a.txt

# Verbs
venv/bin/python make_anto_synonyms.py \
    --ft_model cc.en.300.bin --pos v --concepts 1000 \
    --out_syn syn_v_10.txt --out_ant ant_v.txt
```

Add `--extra_seeds childwords.txt` to prioritise child-vocabulary words
as seed concepts (recommended for nouns and adjectives).

**Key flags:**
```
--ft_model PATH      fastText .bin model (required)
--pos n|a|v          Part of speech (required)
--concepts N         Number of output clusters (default 1000)
--seed_lemmas N      Candidate seed pool size (default 15000)
--min_zipf F         Minimum word frequency (zipf scale, default 3.5)
--syn_min_score F    Minimum synonym similarity to include (default 0.50)
--ant_min_score F    Minimum antonym similarity to include (default 0.50)
--max_syn N          Max synonyms per cluster (default 10)
--max_ant N          Max antonyms per cluster (default 10)
--require_min_syn N  Skip clusters with fewer than N synonyms (default 3)
--no_filter_rel_adj  Include relational adjectives (national, historic, ...)
--extra_seeds FILE   Prepend seed words from file (one per line)
--out_syn FILE       Output synonym CSV (required)
--out_ant FILE       Output antonym CSV (required)
```

**Runtime:** ~10–30 minutes per POS depending on hardware (fastText model is
loaded once into RAM, ~8 GB peak usage).

---

### `make_gradables.py` — gradable adjective extractor (library)

Not a standalone script. Import and call from Python:

```python
from make_gradables import extract_gradable_adjs
rows = extract_gradable_adjs(docs, nlp, min_count=5)
# rows: list of (lemma, count, deg_rate, comp_rate, scale, score)
# scale: "open" (very tall) or "closed" (completely full)
```

`docs` is an iterable of raw text strings. `nlp` is a loaded spaCy model
(any model with POS tagging).

---

## Output file formats

### Rewrite table (`syn_rewrite_<pos>.txt`)

One entry per line: `word,POS,canonical`

```
automobile,N,car
quick,A,fast
speedy,A,fast
acquire,V,get
```

Rules:
- Only non-canonical words appear (canonicals are never rewritten).
- When a word maps to multiple clusters above threshold, the highest-scoring
  cluster wins.

### GK axiom file (`syn_axioms_<pos>.js`)

JSON array (with `//` comment header lines). Each entry:

```json
{"@logic": [NEGATIVE_LITERAL, POSITIVE_LITERAL], "@confidence": 0.85}
```

The clause pattern per POS:

| POS | Negative literal | Positive literal |
|-----|-----------------|-----------------|
| N | `["-isa", synonym, "?:X"]` | `["isa", canonical, "?:X"]` |
| A | `["-has degree property", s, "?:X", "?:D", "?:R", "?:CT"]` | `["has degree property", c, ...]` |
| A | `["-has property", s, "?:X", "?:CT"]` | `["has property", c, "?:X", "?:CT"]` |
| V | `["-has type", "?:E", s, "?:CT"]` | `["has type", "?:E", c, "?:CT"]` |
| V | `["-is rel2", s, "?:X", "?:Y", "?:CT"]` | `["is rel2", c, "?:X", "?:Y", "?:CT"]` |
| V | `["-has degree rel2", s, "?:X", "?:Y", "?:D", "?:R", "?:CT"]` | `["has degree rel2", c, ...]` |

`?:CT` is the context tuple `[$ctxt, tense, world, loc, knower]` appended by
`logconvert.py`. Axioms must include it to match clausified predicates.

---

## Environment setup

All scripts run inside a local `venv/`. The venv is not committed to git.

**Create and populate the venv (first time):**
```bash
cd mkdata/
python3 -m venv venv
venv/bin/pip install wordfreq fasttext nltk numpy
venv/bin/python -c "
import nltk
nltk.download('wordnet')
nltk.download('omw-1.4')
"
```

`make_gradables.py` additionally requires spaCy and more NLTK corpora if you
use it directly:
```bash
venv/bin/pip install spacy
venv/bin/python -m spacy download en_core_web_sm
venv/bin/python -c "
import nltk
for pkg in ['brown','reuters','gutenberg','webtext','inaugural','movie_reviews','abc','punkt_tab']:
    nltk.download(pkg)
"
```

**Always prefix commands with `venv/bin/python`** (or activate the venv with
`source venv/bin/activate`).

---

## Large files not in git

| File | Size | How to obtain |
|------|------|--------------|
| `cc.en.300.bin` | ~6.7 GB | `gunzip cc.en.300.bin.gz` |
| `cc.en.300.bin.gz` | ~4.5 GB | `wget https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.en.300.bin.gz` |

A lighter alternative fastText model (lower coverage, ~1 GB uncompressed):
```bash
wget https://dl.fbaipublicfiles.com/fasttext/vectors-english/wiki-news-300d-1M-subword.bin.gz
gunzip wiki-news-300d-1M-subword.bin.gz
```

---

## Typical workflow

### Regenerate solver data from existing cluster files

Run whenever `syn_*_10.txt` files are updated:

```bash
venv/bin/python build_syn_data.py syn_n_10.txt N
venv/bin/python build_syn_data.py syn_a_10.txt A
venv/bin/python build_syn_data.py syn_v_10.txt V
```

### Rebuild cluster files from scratch

Takes 30–90 minutes total. Requires `cc.en.300.bin`.

```bash
venv/bin/python make_anto_synonyms.py \
    --ft_model cc.en.300.bin --pos n --concepts 1000 \
    --extra_seeds childwords.txt \
    --out_syn syn_n_10.txt --out_ant ant_n.txt

venv/bin/python make_anto_synonyms.py \
    --ft_model cc.en.300.bin --pos a --concepts 1000 \
    --extra_seeds childwords.txt \
    --out_syn syn_a_10.txt --out_ant ant_a.txt

venv/bin/python make_anto_synonyms.py \
    --ft_model cc.en.300.bin --pos v --concepts 1000 \
    --out_syn syn_v_10.txt --out_ant ant_v.txt

# Then regenerate solver data
venv/bin/python build_syn_data.py syn_n_10.txt N
venv/bin/python build_syn_data.py syn_a_10.txt A
venv/bin/python build_syn_data.py syn_v_10.txt V
```

---

## Integration with the solver

The output files are consumed by the `llmpipe/solver/` pipeline (integration
deferred — wiring not yet done at time of writing):

- `syn_rewrite_*.txt` → `logconvert.py`: normalize predicate names before
  clausification (hard synonymy)
- `syn_axioms_*.js` → `prover.py`: passed to GK alongside `axioms_std.js`
  for soft synonymy inference during proof search
