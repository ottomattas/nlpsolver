#!/usr/bin/env python3

# Ballast generator for the distractor-robustness experiments.
#
# Takes a base test suite (default tests/tests_core_100.py) and a sentence
# pool (default tests/tests_core.py), and produces a new suite in which every
# case has N "ballast" sentences inserted before the final question, at
# deterministically random positions (start / between statements / right
# before the question).  Ids and expected answers are unchanged.
#
# The ballast must be PURE (Tanel, 2026-06-10): apart from function words it
# may share no content words with the original case, and it must not connect
# to the original vocabulary through the pipeline's dynamic-axiom machinery.
# A pool sentence S is accepted as ballast for case T only if ALL hold:
#
#   1. content(S) ∩ content(T) = ∅  on raw words AND naive morphological
#      variants (plural/past/progressive/comparative stripping), so
#      "elephants" vs "elephant" is caught;
#   2. canonical forms (data_canonicals.CANONICALS) of (1) are disjoint too —
#      two different surface words may not collide on one canonical;
#   3. no word pair (s,t) is linked in data_antonyms.ANTONYMS (either
#      direction): antonym folding must never bridge ballast and original;
#   4. no word pair (s,t) is linked in data_synonyms.SOFT_SYNONYMS at ANY
#      score ("ka pehmelt"); if the pool empties, per-case relaxation to
#      score >= 0.5 only, recorded in the manifest;
#   5. no shared proper names — subsumed by (1), all checks are lowercase;
#   6. no word pair in the same data_exclusions group: lc_post_inject's
#      mutual-exclusion axioms must not bridge ballast and original either;
#   7. no word pair in two DIFFERENT noun-mutex groups (_ISA_EXCL_GROUPS):
#      lc_post_inject.inject_isa_cross_group_axioms emits cross-group
#      cross-entity mutex axioms (e.g. house x animal), which would also
#      bridge the vocabularies.  Subsumption-exempt pairs (animal subsumes
#      the animal-kind group, etc.) are allowed, mirroring the injector.
#
# Ballast sentences are also MUTUALLY inert within one case (the ballast may
# not form its own reasoning chain); at high dose this can be relaxed to
# intra-ballast overlap, which is recorded per case in the manifest.
#
# Pool restrictions: statement sentences only (never questions), no wh-words,
# no pronouns (coreference-leak risk), >= 3 tokens, >= 1 content word.
#
# Deterministic: seeded RNG random.Random(case_id * 1000 + dose), no
# timestamps — same inputs always produce byte-identical outputs.
#
# Usage (from the llmpipe/ directory):
#   python3 tests/ballast/make_ballast.py -dose 2
#   python3 tests/ballast/make_ballast.py -dose 8 -base tests/tests_core.py
#
# Writes tests_<basestem>_b<N>.py and tests_<basestem>_b<N>.manifest.json
# into this directory, then re-reads both and re-verifies every condition
# (self-check).  Exits non-zero if any check fails.

import os
import sys
import re
import json
import random
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))          # llmpipe/tests/ballast
LLMPIPE = os.path.dirname(os.path.dirname(HERE))           # llmpipe/
sys.path.insert(0, LLMPIPE)                                # runtests.load_tests
sys.path.insert(0, os.path.join(LLMPIPE, "solver"))        # data_* modules

from runtests import load_tests
from data_synonyms import SOFT_SYNONYMS
from data_antonyms import ANTONYMS
from data_canonicals import CANONICALS
from data_exclusions import EXCLUSION_INDEX, EXCLUSION_GROUPS
from lc_post_inject import _ISA_EXCL_GROUPS, _TOP_LEVEL_SUBSUMES

# word -> set of noun-mutex group ids (condition 7).  The pipeline's injector
# resolves multi-group words first-wins over a frozenset (order undefined),
# so we conservatively keep ALL groups a word belongs to.
_ISA_WORD_GROUPS = {}
for _gid in sorted(_ISA_EXCL_GROUPS):
  for _w in EXCLUSION_GROUPS.get(_gid, {}).get("words", ()):
    _ISA_WORD_GROUPS.setdefault(_w, set()).add(_gid)

# ======== function words ========

# Small explicit stopword list (visible by design — see plan §3).  Everything
# NOT in this list counts as a content word.  Deliberate choices:
#   - have/has/had are CONTENT words: they map to the possession predicate
#     `have` and to have->has_part dynamic bridges, so ballast must not share
#     them with a possession case.
#   - number words (one, two, three, ...) and digits are CONTENT words:
#     counting cases depend on them.
#   - wh-words (who/what/...) are NOT stopwords; pool sentences containing
#     them are dropped entirely, and on the case side they simply become
#     content words that never match.
#   - prepositions ARE stopwords (per plan §3): they map to relation NAMES
#     (is_rel2("on",...)) whose axioms act per-entity, and entity vocabulary
#     is guaranteed disjoint by the content-word checks.
STOPWORDS = frozenset("""
a an the this that these those some any all every each both either neither
no none such other another more most many much few several enough less than
is are was were be been being am
do does did doing done
can could may might must shall should will would ought
not never only even just too also
very somewhat quite rather really extremely slightly almost
i you he she it we they me him her us them
my your his its our their mine yours hers ours theirs
myself yourself himself herself itself ourselves themselves
of in on at to from with without by for about into onto over under above
below between behind before after near beside through during against around
across off out up down inside outside within upon toward towards along
and or but if then else because so as while although though whether since
until unless
there
isn't aren't wasn't weren't don't doesn't didn't can't cannot couldn't
won't wouldn't shouldn't mustn't needn't hasn't haven't hadn't ain't
""".split())

# Pool-only filters.
WH_WORDS = frozenset(["who", "whom", "whose", "what", "which", "where",
                      "when", "why", "how"])
PRONOUNS = frozenset(["i", "you", "he", "she", "it", "we", "they",
                      "me", "him", "her", "us", "them",
                      "his", "hers", "its", "their", "theirs", "my", "our",
                      "your", "mine", "yours", "ours",
                      "himself", "herself", "itself", "themselves",
                      "myself", "yourself", "ourselves"])

# Bare demonstratives ("This was deep.") act like pronouns: with no content
# NP of their own they invite the parser to resolve them onto neighbouring
# (original) content.  Phase 1 caught exactly one such capture (case 22,
# claude resolved ballast "This was deep." onto "John is glad." and lost the
# case), so from dose b4 on the pool drops any sentence where a demonstrative
# is NOT followed by a content word (i.e. is a bare pronoun-like NP rather
# than a determiner as in "this car").  "That" as complementizer before a
# noun ("believes that Mary...") survives; bare relativizer "that is red"
# is dropped too — conservative, and the pool is large.
DEMONSTRATIVES = frozenset(["this", "that", "these", "those"])

def _has_bare_demonstrative(toks):
  for i, t in enumerate(toks):
    if t in DEMONSTRATIVES:
      nxt = toks[i + 1] if i + 1 < len(toks) else None
      if nxt is None or nxt in STOPWORDS:
        return True
  return False

# ======== text utilities ========

def norm_ws(text):
  return re.sub(r"\s+", " ", text).strip()


# Title abbreviations that end in '.' but never end a sentence here.  The
# corpus contains "Dr. Smith"; splitting after "Dr." dismembered that
# sentence into pool fragments ("A surgeon, Dr.") AND let ballast be
# inserted inside the original sentence (caught post-hoc in Phase 2:
# "A surgeon, Dr. Penguins are birds.").
_ABBREVS = ("Dr.", "Mr.", "Mrs.", "Ms.", "Prof.", "St.", "Jr.", "Sr.")

def split_sentences(text):
  """Split normalized text on terminal punctuation followed by whitespace.
  Title abbreviations (Dr. etc) are protected from splitting."""
  t = norm_ws(text)
  for a in _ABBREVS:
    t = t.replace(a + " ", a + "\x00")
  parts = re.split(r"(?<=[.?!])\s+", t)
  return [p.replace("\x00", " ") for p in parts if p]


def tokenize(sentence):
  """Lowercase word tokens; possessive 's stripped."""
  toks = re.findall(r"[a-z0-9']+", sentence.lower())
  out = []
  for t in toks:
    t = t.strip("'")
    if t.endswith("'s"):
      t = t[:-2]
    if t:
      out.append(t)
  return out


def content_words(sentence):
  return [t for t in tokenize(sentence) if t not in STOPWORDS]


# Irregular inflections the suffix rules below cannot reach.  Both the
# inflected form and its lemma land in the comparison set, so "mice" vs
# "mouse" or "bought" vs "buy" counts as word overlap.  Only forms that
# plausibly occur in the test suites are listed; over-listing is safe.
IRREGULAR = {
  "has": "have", "had": "have", "having": "have",
  "men": "man", "women": "woman", "children": "child", "child's": "child",
  "mice": "mouse", "feet": "foot", "geese": "goose", "teeth": "tooth",
  "people": "person", "oxen": "ox", "wolves": "wolf", "leaves": "leaf",
  "knives": "knife", "lives": "life", "shelves": "shelf", "wives": "wife",
  "ate": "eat", "eaten": "eat", "saw": "see", "seen": "see",
  "went": "go", "gone": "go", "goes": "go",
  "bought": "buy", "brought": "bring", "caught": "catch", "taught": "teach",
  "drove": "drive", "driven": "drive", "wrote": "write", "written": "write",
  "broke": "break", "broken": "break", "took": "take", "taken": "take",
  "gave": "give", "given": "give", "made": "make", "ran": "run",
  "came": "come", "sat": "sit", "stood": "stand", "fell": "fall",
  "fallen": "fall", "held": "hold", "kept": "keep", "slept": "sleep",
  "left": "leave", "lost": "lose", "found": "find", "told": "tell",
  "said": "say", "got": "get", "gotten": "get", "flew": "fly",
  "flown": "fly", "grew": "grow", "grown": "grow", "knew": "know",
  "known": "know", "threw": "throw", "thrown": "throw", "wore": "wear",
  "worn": "wear", "sold": "sell", "sent": "send", "spent": "spend",
  "built": "build", "bent": "bend", "met": "meet", "swam": "swim",
  "swum": "swim", "sang": "sing", "sung": "sing", "drank": "drink",
  "drunk": "drink", "rode": "ride", "ridden": "ride", "chose": "choose",
  "chosen": "choose", "spoke": "speak", "spoken": "speak",
  "stole": "steal", "stolen": "steal", "woke": "wake", "woken": "wake",
  "heard": "hear", "felt": "feel", "meant": "mean", "paid": "pay",
  "laid": "lay", "lay": "lie", "lain": "lie", "hid": "hide",
  "hidden": "hide", "bit": "bite", "bitten": "bite", "shot": "shoot",
  "won": "win", "fed": "feed", "fled": "flee", "led": "lead",
  "better": "good", "best": "good", "worse": "bad", "worst": "bad",
  "bigger": "big", "biggest": "big",
}


def variants(w):
  """Naive morphological variants for overlap checking.  Over-generation is
  safe: false matches only shrink the candidate pool."""
  out = {w}
  if w in IRREGULAR:
    out.add(IRREGULAR[w])
  n = len(w)
  if w.endswith("ies") and n > 4: out.add(w[:-3] + "y")     # flies -> fly
  if w.endswith("es") and n > 3:  out.add(w[:-2])           # boxes -> box
  if w.endswith("s") and not w.endswith("ss") and n > 3:
    out.add(w[:-1])                                          # cars -> car
  if w.endswith("ied") and n > 4: out.add(w[:-3] + "y")     # carried -> carry
  if w.endswith("ed") and n > 3:
    out.add(w[:-2]); out.add(w[:-1])                         # barked, baked
    if n > 4 and w[-3] == w[-4]: out.add(w[:-3])             # stopped -> stop
  if w.endswith("ing") and n > 4:
    out.add(w[:-3]); out.add(w[:-3] + "e")                   # walking, baking
    if n > 5 and w[-4] == w[-5]: out.add(w[:-4])             # running -> run
  if w.endswith("er") and n > 3:
    out.add(w[:-2]); out.add(w[:-1])                         # taller -> tall
    if n > 4 and w[-3] == w[-4]: out.add(w[:-3])             # bigger -> big
  if w.endswith("est") and n > 4:
    out.add(w[:-3]); out.add(w[:-2])                         # tallest -> tall
    if n > 5 and w[-4] == w[-5]: out.add(w[:-4])             # biggest -> big
  return out


# Reverse antonym index (ANTONYMS is directional; we need both directions).
_REV_ANT = {}
for _k, _v in ANTONYMS.items():
  _REV_ANT.setdefault(_v, set()).add(_k)


def analyze(words):
  """Precompute the comparison sets for a bag of content words:
     exp        - words + morphological variants + canonical forms
     ant        - all antonym partners of exp (both directions)
     syn_all    - all soft-synonym partners of exp, any score
     syn_strong - soft-synonym partners with score >= 0.5
     excl       - all exclusion-group ids touched by exp"""
  exp = set()
  for w in words:
    for v in variants(w):
      exp.add(v)
      c = CANONICALS.get(v)
      if c:
        exp.add(c)
  ant, syn_all, syn_strong, excl = set(), set(), set(), set()
  isa_groups = {}
  for w in exp:
    a = ANTONYMS.get(w)
    if a:
      ant.add(a)
    ant |= _REV_ANT.get(w, set())
    for (p, score, _pos) in SOFT_SYNONYMS.get(w, ()):
      syn_all.add(p)
      if score >= 0.5:
        syn_strong.add(p)
    excl.update(EXCLUSION_INDEX.get(w, ()))
    if w in _ISA_WORD_GROUPS:
      isa_groups[w] = _ISA_WORD_GROUPS[w]
  return {"exp": exp, "ant": ant, "syn_all": syn_all,
          "syn_strong": syn_strong, "excl": excl, "isa_groups": isa_groups}


# ======== compatibility predicate ========

# Relaxation levels (per case, recorded in the manifest):
#   0 "strict"          : soft synonyms rejected at any score
#   1 "soft05"          : soft synonyms rejected only at score >= 0.5
#   2 "soft05+intra"    : like 1, but ballast sentences may overlap each other
LEVEL_NAMES = {0: "strict", 1: "soft05", 2: "soft05+intra-overlap"}

REASONS = ["word-overlap", "antonym", "soft-synonym", "exclusion-group",
           "isa-cross-group"]


def _isa_cross_group(b, c):
  """True if some word pair would trigger inject_isa_cross_group_axioms:
  members of two different noun-mutex groups, not subsumption-exempt."""
  for w1, gs1 in b["isa_groups"].items():
    for w2, gs2 in c["isa_groups"].items():
      for g1 in gs1:
        for g2 in gs2:
          if g1 == g2:
            continue                       # same group: condition 6 covers it
          if g2 in _TOP_LEVEL_SUBSUMES.get(w1, ()):
            continue
          if g1 in _TOP_LEVEL_SUBSUMES.get(w2, ()):
            continue
          return True
  return False


def compat(b, c, syn_level):
  """Return None if entries b and c are mutually inert, else the (first)
  reason for rejection.  syn_level 0 = any-score synonyms reject; 1 = only
  score >= 0.5 rejects.  Raw word overlap is never relaxed."""
  if b["exp"] & c["exp"]:
    return "word-overlap"
  if (b["ant"] & c["exp"]) or (c["ant"] & b["exp"]):
    return "antonym"
  syn_key = "syn_all" if syn_level == 0 else "syn_strong"
  if (b[syn_key] & c["exp"]) or (c[syn_key] & b["exp"]):
    return "soft-synonym"
  if b["excl"] & c["excl"]:
    return "exclusion-group"
  if b["isa_groups"] and c["isa_groups"] and _isa_cross_group(b, c):
    return "isa-cross-group"
  return None


# ======== pool construction ========

def build_pool(pool_tests):
  """Statement sentences of the pool suite, deduplicated, each with its
  comparison sets and source case ids.  Returns (pool list, stats dict)."""
  stats = {"raw_sentences": 0, "questions": 0, "dropped_wh": 0,
           "dropped_pronoun": 0, "dropped_demonstrative": 0,
           "dropped_short": 0, "dropped_nocontent": 0,
           "kept_before_dedup": 0}
  by_text = {}
  order = []
  for cid, text, _expected in pool_tests:
    sents = split_sentences(text)
    for s in sents:
      stats["raw_sentences"] += 1
      if not s.endswith("."):          # questions (and any fragment) excluded
        stats["questions"] += 1
        continue
      toks = tokenize(s)
      tokset = set(toks)
      if tokset & WH_WORDS:
        stats["dropped_wh"] += 1
        continue
      if tokset & PRONOUNS:
        stats["dropped_pronoun"] += 1
        continue
      if _has_bare_demonstrative(toks):
        stats["dropped_demonstrative"] += 1
        continue
      if len(toks) < 3:
        stats["dropped_short"] += 1
        continue
      cw = content_words(s)
      if not cw:
        stats["dropped_nocontent"] += 1
        continue
      stats["kept_before_dedup"] += 1
      if s in by_text:
        by_text[s]["source_cases"].add(cid)
      else:
        entry = analyze(cw)
        entry["text"] = s
        entry["source_cases"] = {cid}
        by_text[s] = entry
        order.append(s)
  pool = [by_text[t] for t in order]
  for e in pool:
    e["source_cases"] = sorted(e["source_cases"])
  stats["pool_size"] = len(pool)
  return pool, stats


# ======== per-case generation ========

def make_case(cid, text, dose, pool, reject_counts):
  """Pick `dose` ballast sentences for one case and insert them.
  Returns (new_text, manifest_entry)."""
  sents = split_sentences(text)
  assert sents and sents[-1].endswith("?"), f"case {cid}: no final question"
  statements, question = sents[:-1], sents[-1]
  for s in statements:
    assert s.endswith("."), f"case {cid}: non-statement before question: {s!r}"

  case_entry = analyze(content_words(norm_ws(text)))

  rng = random.Random(cid * 1000 + dose)
  order = rng.sample(range(len(pool)), len(pool))

  picked = []            # pool indices, in pick order
  picked_set = set()
  final_level = 0
  intra_overlaps = []    # [reason, text_a, text_b] when level 2 was needed
  for level in (0, 1, 2):
    syn_level = min(level, 1)
    for idx in order:
      if len(picked) >= dose:
        break
      if idx in picked_set:
        continue
      b = pool[idx]
      r = compat(b, case_entry, syn_level)
      if r:
        reject_counts[r] += 1
        continue
      mutual = [(compat(b, pool[j], syn_level), j) for j in picked]
      bad = [(r2, j) for (r2, j) in mutual if r2]
      if bad and level < 2:
        reject_counts["intra-ballast"] += 1
        continue
      for (r2, j) in bad:   # level 2 only: record the allowed overlap
        intra_overlaps.append([r2, b["text"], pool[j]["text"]])
      picked.append(idx)
      picked_set.add(idx)
    final_level = level
    if len(picked) >= dose:
      break
  if len(picked) < dose:
    raise RuntimeError(f"case {cid}: pool exhausted, only {len(picked)}/{dose} "
                       "ballast sentences found even with all relaxations")

  # Insertion slots: 0 = very start, k = before statement k, n = right
  # before the question.  Several ballast sentences may share a slot.
  n = len(statements)
  slots = [rng.randint(0, n) for _ in picked]

  parts = []
  for i in range(n + 1):
    for b_idx, slot in zip(picked, slots):
      if slot == i:
        parts.append(pool[b_idx]["text"])
    if i < n:
      parts.append(statements[i])
  parts.append(question)
  new_text = " ".join(parts)

  entry = {
    "case_id": cid,
    "n_statements": n,
    "relax_level": LEVEL_NAMES[final_level],
    "ballast": [
      {"text": pool[b_idx]["text"],
       "source_cases": pool[b_idx]["source_cases"],
       "slot": slot}
      for b_idx, slot in zip(picked, slots)
    ],
  }
  if intra_overlaps:
    entry["intra_ballast_overlaps"] = intra_overlaps
  return new_text, entry


# ======== output rendering ========

def render_testfile(base_rel, pool_rel, dose, cases):
  lines = [
    "# Ballast-augmented test suite — AUTO-GENERATED by tests/ballast/make_ballast.py, do not edit.",
    f"# base: {base_rel} | pool: statement sentences of {pool_rel} | dose: {dose} ballast sentences per case.",
    "# Ids and expected answers are identical to the base suite; ballast sentences, their source",
    "# cases and insertion slots are listed in the .manifest.json next to this file.",
    f"# Regenerate (from llmpipe/): python3 tests/ballast/make_ballast.py -dose {dose} -base {base_rel} -pool {pool_rel}",
    "[",
  ]
  for cid, text, expected in cases:
    lines.append(f"  [{cid!r}, {text!r}, {expected!r}],")
  lines.append("]")
  return "\n".join(lines) + "\n"


def render_manifest(base_rel, pool_rel, dose, pool_stats, reject_counts,
                    eligibility, level_hist, case_entries):
  obj = {
    "generator": "tests/ballast/make_ballast.py",
    "base": base_rel,
    "pool": pool_rel,
    "dose": dose,
    "n_cases": len(case_entries),
    "pool_stats": pool_stats,
    "rejection_counts": reject_counts,
    "strict_eligible_per_case": eligibility,
    "relax_level_histogram": level_hist,
    "cases": case_entries,
  }
  return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


# ======== self-checks ========

def verify(base_tests, gen_path, manifest_path, dose, pool):
  """Re-read the generated suite + manifest from disk and re-verify every
  guarantee.  Raises AssertionError on any violation."""
  gen_tests = load_tests(gen_path)
  with open(manifest_path) as f:
    manifest = json.load(f)
  mcases = {e["case_id"]: e for e in manifest["cases"]}
  pool_by_text = {e["text"]: e for e in pool}

  assert len(gen_tests) == len(base_tests), "case count mismatch"
  level_rank = {v: k for k, v in LEVEL_NAMES.items()}

  for (bid, btext, bexp), (gid, gtext, gexp) in zip(base_tests, gen_tests):
    assert bid == gid, f"id order mismatch: {bid} vs {gid}"
    assert bexp == gexp, f"case {bid}: expected answer changed"
    m = mcases[bid]
    bsents = split_sentences(btext)
    gsents = split_sentences(gtext)
    # question unchanged and still last; no new questions appeared
    assert gsents[-1] == bsents[-1], f"case {bid}: question changed"
    assert sum(1 for s in gsents if s.endswith("?")) == \
           sum(1 for s in bsents if s.endswith("?")), f"case {bid}: '?' count changed"
    # original sentences unmodified and in order once ballast is removed
    ballast_texts = [b["text"] for b in m["ballast"]]
    assert len(ballast_texts) == dose, f"case {bid}: dose mismatch"
    remaining = list(gsents)
    for bt in ballast_texts:
      assert bt in remaining, f"case {bid}: ballast sentence missing: {bt!r}"
      remaining.remove(bt)
    assert remaining == bsents, f"case {bid}: original sentences modified or reordered"
    # slots are consistent with the actual insertion positions
    n = len(bsents) - 1
    for b in m["ballast"]:
      assert 0 <= b["slot"] <= n, f"case {bid}: slot out of range"
    # re-verify the inertness conditions at the recorded relaxation level
    syn_level = min(level_rank[m["relax_level"]], 1)
    case_entry = analyze(content_words(norm_ws(btext)))
    entries = []
    for bt in ballast_texts:
      be = pool_by_text.get(bt) or dict(analyze(content_words(bt)), text=bt)
      r = compat(be, case_entry, syn_level)
      assert r is None, f"case {bid}: ballast not inert ({r}): {bt!r}"
      entries.append(be)
    if level_rank[m["relax_level"]] < 2:
      for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
          r = compat(entries[i], entries[j], syn_level)
          assert r is None, (f"case {bid}: ballast pair not mutually inert "
                             f"({r}): {entries[i]['text']!r} / {entries[j]['text']!r}")


# ======== main ========

def main():
  ap = argparse.ArgumentParser(description="Generate a ballast-augmented test suite.")
  ap.add_argument("-dose", type=int, required=True,
                  help="Number of ballast sentences to insert per case")
  ap.add_argument("-base", default="tests/tests_core_100.py",
                  help="Base suite (default: tests/tests_core_100.py)")
  ap.add_argument("-pool", default="tests/tests_core.py",
                  help="Sentence pool suite (default: tests/tests_core.py)")
  ap.add_argument("-outdir", default=HERE,
                  help="Output directory (default: this script's directory)")
  args = ap.parse_args()

  base_path = os.path.join(LLMPIPE, args.base) if not os.path.isabs(args.base) else args.base
  pool_path = os.path.join(LLMPIPE, args.pool) if not os.path.isabs(args.pool) else args.pool

  base_tests = load_tests(base_path)
  pool_tests = load_tests(pool_path)
  pool, pool_stats = build_pool(pool_tests)
  print(f"Pool: {pool_stats['pool_size']} unique statement sentences "
        f"(from {pool_stats['raw_sentences']} raw; "
        f"-{pool_stats['questions']} questions, -{pool_stats['dropped_wh']} wh, "
        f"-{pool_stats['dropped_pronoun']} pronoun, "
        f"-{pool_stats['dropped_demonstrative']} demonstrative, "
        f"-{pool_stats['dropped_short']} short, "
        f"-{pool_stats['dropped_nocontent']} no-content, "
        f"-{pool_stats['kept_before_dedup'] - pool_stats['pool_size']} duplicates)")

  # Pool-health report: strictly eligible candidates per case.
  elig = []
  for cid, text, _exp in base_tests:
    ce = analyze(content_words(norm_ws(text)))
    elig.append(sum(1 for b in pool if compat(b, ce, 0) is None))
  elig_sorted = sorted(elig)
  eligibility = {"min": elig_sorted[0],
                 "median": elig_sorted[len(elig) // 2],
                 "max": elig_sorted[-1]}
  print(f"Strictly eligible ballast per case: min={eligibility['min']} "
        f"median={eligibility['median']} max={eligibility['max']}")

  reject_counts = {r: 0 for r in REASONS + ["intra-ballast"]}
  out_cases = []
  case_entries = []
  level_hist = {}
  for cid, text, expected in base_tests:
    new_text, entry = make_case(cid, text, args.dose, pool, reject_counts)
    out_cases.append((cid, new_text, expected))
    case_entries.append(entry)
    level_hist[entry["relax_level"]] = level_hist.get(entry["relax_level"], 0) + 1

  stem = os.path.splitext(os.path.basename(base_path))[0]    # tests_core_100
  out_py = os.path.join(args.outdir, f"{stem}_b{args.dose}.py")
  out_manifest = os.path.join(args.outdir, f"{stem}_b{args.dose}.manifest.json")

  testfile_text = render_testfile(args.base, args.pool, args.dose, out_cases)
  manifest_text = render_manifest(args.base, args.pool, args.dose, pool_stats,
                                  reject_counts, eligibility, level_hist,
                                  case_entries)
  with open(out_py, "w") as f:
    f.write(testfile_text)
  with open(out_manifest, "w") as f:
    f.write(manifest_text)
  print(f"Wrote {out_py}")
  print(f"Wrote {out_manifest}")
  print(f"Rejections during selection: {reject_counts}")
  print(f"Relaxation levels: {level_hist}")

  # --- self-checks ---
  verify(base_tests, out_py, out_manifest, args.dose, pool)
  # determinism: regenerating in memory must reproduce the files byte-for-byte
  reject2 = {r: 0 for r in REASONS + ["intra-ballast"]}
  out2 = []
  entries2 = []
  hist2 = {}
  for cid, text, expected in base_tests:
    t2, e2 = make_case(cid, text, args.dose, pool, reject2)
    out2.append((cid, t2, expected))
    entries2.append(e2)
    hist2[e2["relax_level"]] = hist2.get(e2["relax_level"], 0) + 1
  assert render_testfile(args.base, args.pool, args.dose, out2) == testfile_text, \
      "determinism check failed (test file)"
  assert render_manifest(args.base, args.pool, args.dose, pool_stats, reject2,
                         eligibility, hist2, entries2) == manifest_text, \
      "determinism check failed (manifest)"
  print("SELF-CHECK PASSED: ids/expected unchanged, question last, originals "
        "intact, all ballast re-verified inert, deterministic.")


if __name__ == "__main__":
  main()


# =========== the end ==========
