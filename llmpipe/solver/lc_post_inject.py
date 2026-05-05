# Dynamic axiom injection passes for the post-clausification clause list.
#
# Each injector scans the clause list for trigger words / patterns and
# returns a list of new axiom clauses.  Injectors never mutate the input
# clause list — the caller appends the returned axioms.
#
# Sections:
#   - shared helpers      _collect_eligible_words, _eligible_word
#   - inject_soft_synonyms          (Tier B synonym biconditionals)
#   - inject_exclusion_axioms       (excl_a.txt mutual-exclusion groups)
#   - inject_verb_mutex_axioms      (cross-event verb mutex, e.g. pass↔fail)
#   - inject_kinship_mutex_axioms   (gender-paired role mutex)
#   - inject_containment_bridge_axioms (filled-with/contain → "is rel2 in")
#   - inject_world_geometry         (minimal next chain over present worlds)
#
#-----------------------------------------------------------------
# Copyright 2026 Tanel Tammet (tanel.tammet@gmail.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#-----------------------------------------------------------------

from lc_ctxt import fresh_fv as _fresh_fv
from lc_clausify import is_world_constant as _is_world_constant

# ======== soft synonym and exclusion axiom injection ========

from data_synonyms import SOFT_SYNONYMS
from data_exclusions import EXCLUSION_GROUPS, EXCLUSION_INDEX

# When True, only emit a soft synonym or exclusion axiom if BOTH sides of the
# pair appear in the problem (input clauses or axiom files). When False, emit
# whenever at least one side appears (original behavior — more axioms, slower).
REQUIRE_BOTH_SIDES = True


def _collect_eligible_words(result):
  """Scan all clauses and collect eligible string arguments (skip pred names,
  URLs, variables, internal markers). Returns a dict mapping lowercase word
  to the original-case form (for use in generated axioms)."""
  words = {}  # lowercase → original case

  def _walk(frm):
    if not isinstance(frm, list) or not frm:
      return
    first = frm[0]
    # GK disjunctive clause: first element is a list → recurse each atom.
    if isinstance(first, list):
      for atom in frm:
        _walk(atom)
      return
    # Regular atom: skip position 0 (predicate name), scan positions 1+.
    for i in range(1, len(frm)):
      arg = frm[i]
      if isinstance(arg, list):
        # Skip $ctxt terms — context markers, not semantic content.
        if arg and isinstance(arg[0], str) and arg[0].startswith("$ctxt"):
          pass
        else:
          _walk(arg)
      elif isinstance(arg, str) and _eligible_word(arg):
        words[arg.lower()] = arg  # keep original case

  for obj in result:
    if not isinstance(obj, dict):
      continue
    if "@logic" in obj:
      _walk(obj["@logic"])
    if "@question" in obj:
      _walk(obj["@question"])
  return words


def _eligible_word(s):
  """True if s is a candidate for synonym/exclusion matching."""
  if not s:
    return False
  if s.startswith("http"):
    return False
  if s.startswith("?:"):
    return False
  if s.startswith("$"):
    return False
  if s.startswith("@"):
    return False
  return True


# Axiom templates by POS.
# Adjectives use "has property" — normalize_gradable_predicates() promotes
# to "has degree property" afterwards if the word is in GRADABLE_PROPS.
# A single free context variable "?:Ctxt" is used (not the expanded
# ["$ctxt",T,W,L,K] form) — it unifies with any context term.
_SOFT_SYN_TEMPLATES = {
    "a": lambda w, o, ct: [
        ["-has property", w, "?:X", ct],
        ["has property", o, "?:X", ct]
    ],
    "n": lambda w, o, ct: [
        ["-isa", w, "?:X"],
        ["isa", o, "?:X"]
    ],
    "v": lambda w, o, ct: [
        ["-has type", "?:E", w, ct],
        ["has type", "?:E", o, ct]
    ],
}


def inject_soft_synonyms(result, axiom_vocab=frozenset()):
  """Scan clause list for words with soft synonym pairs; emit biconditional
  axiom clauses for each relevant pair. Returns list of new clause dicts.

  When REQUIRE_BOTH_SIDES is True, only emits if the other side of the pair
  also appears in the input clauses or axiom_vocab.
  """
  words = _collect_eligible_words(result)  # {lowercase: original_case}
  if not words:
    return []

  all_known = set(words) | axiom_vocab if REQUIRE_BOTH_SIDES else None

  axioms = []
  emitted = set()  # frozenset pairs to avoid duplicates

  for lc_word, orig_word in words.items():
    if lc_word not in SOFT_SYNONYMS:
      continue
    for other, score, pos in SOFT_SYNONYMS[lc_word]:
      if all_known is not None and other not in all_known:
        continue
      pair_key = frozenset((lc_word, other))
      if pair_key in emitted:
        continue
      emitted.add(pair_key)
      template = _SOFT_SYN_TEMPLATES.get(pos)
      if not template:
        continue
      ct = _fresh_fv()
      clause1 = template(orig_word, other, ct)
      axioms.append({"@name": "frm_syn",
                      "@logic": clause1,
                      "@confidence": score})
      ct2 = _fresh_fv()
      clause2 = template(other, orig_word, ct2)
      axioms.append({"@name": "frm_syn",
                      "@logic": clause2,
                      "@confidence": score})
  return axioms


# Groups whose members appear as is_rel2 target arguments (temporal/location)
# rather than has_property adjective atoms.
_IS_REL2_EXCL_GROUPS = frozenset({
    "MONTH", "DAY_OF_WEEK", "SEASON",
})

# Groups whose members appear as the RELATION at is_rel2 argument 1
# (spatial / temporal-order prepositions like behind, above, before).
# Emitted axiom shape:
#   [-is_rel2(w1,?:X,?:Y,ct), -is_rel2(w2,?:X,?:Y,ct)]
_IS_REL2_PREP_GROUPS = frozenset({
    "SPATIAL_SAGITTAL",
    "SPATIAL_VERTICAL",
    "SPATIAL_VERTICAL_OVER_UNDER",
    "SPATIAL_CONTAINMENT",
    "SPATIAL_LATERAL",
    "TEMPORAL_ORDER",
})

# Groups whose members appear as the RELATION at has_degree_rel2 argument 1
# (degree-based binary relations like near, far_from).
# Emitted per pair: two asymmetric axioms — positive side any-degree,
# antonym side "none" intensity, shared RELCLASS:
#   [-has_degree_rel2(W1, ?:X, ?:Y, ?:D, ?:RC, ct),
#    -has_degree_rel2(W2, ?:X, ?:Y, "none", ?:RC, ct)]
#   [-has_degree_rel2(W2, ?:X, ?:Y, ?:D, ?:RC, ct),
#    -has_degree_rel2(W1, ?:X, ?:Y, "none", ?:RC, ct)]
# The existing high→none / low→none intensity bridges in axioms_std.js §9
# then propagate the "none" negation to all intensities via contrapositive.
_HAS_DEGREE_REL2_PREP_GROUPS = frozenset({
    "PROXIMITY",
})

# Groups whose mutual-exclusion axioms are emitted statically in
# axioms_std.js §7e. These first-class preposition predicates appear in the
# standard ontology (subsumption rules in §7c/7d), so the exclusions hold
# universally — dynamic injection would emit equivalent clauses on every
# problem (both sides are in axiom_vocab), but placing them statically
# pairs them with the related subsumption rules. Skipped here to avoid
# duplication.
_STATIC_PREP_EXCL_GROUPS = frozenset({
    "SPATIAL_VERTICAL",
    "SPATIAL_VERTICAL_OVER_UNDER",
    "SPATIAL_SAGITTAL",
    "SPATIAL_CONTAINMENT",
    "SPATIAL_LATERAL",
    "TEMPORAL_ORDER",
    "PROXIMITY",
})


def inject_exclusion_axioms(result, axiom_vocab=frozenset()):
  """Scan clause list for words in exclusion groups; emit pairwise mutual-
  exclusion clauses for groups with 2+ members present. Returns list of
  new clause dicts.

  When REQUIRE_BOTH_SIDES is True, a group member counts as "present" if it
  appears in either the input clauses or axiom_vocab.
  """
  words = _collect_eligible_words(result)
  if not words:
    return []

  all_known = set(words) | axiom_vocab if REQUIRE_BOTH_SIDES else set(words)

  # Find which groups have 2+ members present in all_known.
  group_members = {}  # gid → set of original-case words
  for lc_word in all_known:
    if lc_word not in EXCLUSION_INDEX:
      continue
    for gid in EXCLUSION_INDEX[lc_word]:
      if gid in _STATIC_PREP_EXCL_GROUPS:
        continue
      if gid not in group_members:
        group_members[gid] = set()
      # Use original case from input if available, else lowercase.
      group_members[gid].add(words.get(lc_word, lc_word))

  axioms = []
  for gid, present in group_members.items():
    if len(present) < 2:
      continue
    ginfo = EXCLUSION_GROUPS.get(gid)
    if not ginfo:
      continue
    score = ginfo["score"]
    is_rel2_group = gid in _IS_REL2_EXCL_GROUPS
    is_rel2_prep_group = gid in _IS_REL2_PREP_GROUPS
    has_degree_rel2_prep_group = gid in _HAS_DEGREE_REL2_PREP_GROUPS
    present_list = sorted(present)
    for i in range(len(present_list)):
      for j in range(i + 1, len(present_list)):
        w1, w2 = present_list[i], present_list[j]
        if has_degree_rel2_prep_group:
          # Preposition at has_degree_rel2 arg 1. Two asymmetric axioms per
          # pair: positive side any-degree (?:D), antonym side "none"
          # intensity, shared ?:RC. Intensity bridges (high→none, low→none)
          # in axioms_std.js §9 propagate the "none" negation to all
          # intensities via contrapositive.
          for (left, right) in ((w1, w2), (w2, w1)):
            d = _fresh_fv()
            rc = _fresh_fv()
            ct = _fresh_fv()
            clause = [
                ["-has degree rel2", left,  "?:X", "?:Y", d,      rc, ct],
                ["-has degree rel2", right, "?:X", "?:Y", "none", rc, ct],
            ]
            axioms.append({"@name": "frm_excl",
                            "@logic": clause,
                            "@confidence": score})
        elif is_rel2_prep_group:
          # Preposition at is_rel2 arg 1; two free entity variables.
          ct = _fresh_fv()
          clause = [
              ["-is rel2", w1, "?:X", "?:Y", ct],
              ["-is rel2", w2, "?:X", "?:Y", ct],
          ]
          axioms.append({"@name": "frm_excl",
                          "@logic": clause,
                          "@confidence": score})
        elif is_rel2_group:
          ct = _fresh_fv()
          clause = [
              ["-is rel2", "?:R", "?:X", w1, ct],
              ["-is rel2", "?:R", "?:X", w2, ct],
          ]
          axioms.append({"@name": "frm_excl",
                          "@logic": clause,
                          "@confidence": score})
        elif ginfo["needs_blocker"]:
          # Two defeasible axioms per pair, each blockable by the other side.
          # ¬w1(X,CT) ∨ ¬w2(X,CT) ∨ $block(0, w2(X,CT))
          ct1 = _fresh_fv()
          axioms.append({"@name": "frm_excl",
                          "@logic": [
                              ["-has property", w1, "?:X", ct1],
                              ["-has property", w2, "?:X", ct1],
                              ["$block", 0, ["has property", w2, "?:X", ct1]],
                          ],
                          "@confidence": score})
          # ¬w1(X,CT) ∨ ¬w2(X,CT) ∨ $block(0, w1(X,CT))
          ct2 = _fresh_fv()
          axioms.append({"@name": "frm_excl",
                          "@logic": [
                              ["-has property", w1, "?:X", ct2],
                              ["-has property", w2, "?:X", ct2],
                              ["$block", 0, ["has property", w1, "?:X", ct2]],
                          ],
                          "@confidence": score})
        else:
          # Hard exclusion: ¬w1(X,CT) ∨ ¬w2(X,CT)
          ct = _fresh_fv()
          clause = [
              ["-has property", w1, "?:X", ct],
              ["-has property", w2, "?:X", ct],
          ]
          axioms.append({"@name": "frm_excl",
                          "@logic": clause,
                          "@confidence": score})
  return axioms


# Verb-event defeasible mutex pairs. For each (v1, v2) pair, when both
# verbs appear in the input (or axiom vocabulary), inject a defeasible
# cross-event mutex saying that two events sharing actor + target cannot
# defeasibly have these mutually-incompatible types in the same context.
# Verb antonyms cannot be folded into ANTONYMS (verb antonyms are mostly
# perspective inversions, not logical opposites — see mkdata/CLAUDE.md).
# The mutex injector handles the small set where polarity-style mutex IS
# semantically appropriate (pass/fail, succeed/fail, ...).
_VERB_MUTEX_PAIRS = [
    ("pass", "fail"),
]


def inject_verb_mutex_axioms(result, axiom_vocab=frozenset()):
  """Scan clause list for verbs in _VERB_MUTEX_PAIRS; for each pair where
  BOTH verbs appear, emit two symmetric defeasible cross-event mutex
  axioms.

  Shape (one direction):
    [-has type   E1 v1 Ct,
     -has actor  E1 X  Ct,
     -has target E1 Y  Ct,
     -has type   E2 v2 Ct,
     -has actor  E2 X  Ct,
     -has target E2 Y  Ct,
     $block(0, has type E2 v2 Ct)]

  Two events sharing actor + target + context cannot have these
  mutually-incompatible types unless the right-side type is independently
  supported (defeated by $block).
  """
  words = _collect_eligible_words(result)
  if not words:
    return []
  all_known = set(words) | axiom_vocab if REQUIRE_BOTH_SIDES else set(words)
  axioms = []
  for v1, v2 in _VERB_MUTEX_PAIRS:
    if v1 not in all_known or v2 not in all_known:
      continue
    for (left, right) in ((v1, v2), (v2, v1)):
      ct = _fresh_fv()
      clause = [
          ["-has type",   "?:E1", left,  ct],
          ["-has actor",  "?:E1", "?:Ag", ct],
          ["-has target", "?:E1", "?:Tg", ct],
          ["-has type",   "?:E2", right, ct],
          ["-has actor",  "?:E2", "?:Ag", ct],
          ["-has target", "?:E2", "?:Tg", ct],
          ["$block", 0, ["has type", "?:E2", right, ct]],
      ]
      axioms.append({"@name": "frm_verb_excl",
                      "@logic": clause,
                      "@confidence": 0.85})
  return axioms


# Gender-paired role mutex pairs (kinship + royalty). For each pair (a, b),
# when both terms appear in the input or axiom_vocab, emit hard
# mutual-exclusion clauses both at the noun-category level
# (-isa a X ∨ -isa b X) and the relation level (-is rel2 "a of" X Y ∨
# -is rel2 "b of" X Y). These terms are in BLOCKED_ANTONYM_WORDS
# (mkdata/build_solver_data.py) — gendered role pairs aren't true antonyms
# (flipping "Sara is a sister" to "Sara is not a brother" loses the positive
# type info), so the polarity-flip path is blocked and we use this
# symmetric mutex instead. Pairs not used in the current test corpus are
# included as low-cost future-proofing — the dynamic injector only emits a
# pair when BOTH sides appear, so unused pairs cost nothing at runtime.
_KINSHIP_MUTEX_PAIRS = (
    # Core kinship
    ("sister",        "brother"),
    ("daughter",      "son"),
    ("mother",        "father"),
    ("wife",          "husband"),
    ("aunt",          "uncle"),
    ("niece",         "nephew"),
    ("grandmother",   "grandfather"),
    ("granddaughter", "grandson"),
    # Step / god relations
    ("stepmother",    "stepfather"),
    ("stepdaughter",  "stepson"),
    ("stepsister",    "stepbrother"),
    ("godmother",     "godfather"),
    # Status
    ("widow",         "widower"),
    ("bride",         "groom"),
    # Royalty (analogous gender-paired mutex)
    ("queen",         "king"),
    ("princess",      "prince"),
)


def inject_kinship_mutex_axioms(result, axiom_vocab=frozenset()):
  """For each gender-paired role pair where both terms appear in the input
  or axiom_vocab, emit hard mutex clauses for both the noun category and
  the "X of" relation.

  Closes case 79 ("Sara, the sister of Mike, left. Sara is the brother of
  Mike?" — expected False).
  """
  words = _collect_eligible_words(result)
  all_known = set(words) | axiom_vocab
  axioms = []
  for a, b in _KINSHIP_MUTEX_PAIRS:
    if a not in all_known or b not in all_known:
      continue
    # Category-level mutex: isa atoms are 3-arg, no $ctxt.
    axioms.append({"@name": "frm_kin_excl",
                   "@logic": [["-isa", a, "?:X"], ["-isa", b, "?:X"]]})
    # Relation-level mutex: is rel2 "<a> of" / "<b> of" with shared $ctxt.
    ct = _fresh_fv()
    axioms.append({"@name": "frm_kin_excl",
                   "@logic": [
                       ["-is rel2", a + " of", "?:X", "?:Y", ct],
                       ["-is rel2", b + " of", "?:X", "?:Y", ct],
                   ]})
  return axioms


# Containment relations that bridge to canonical "in" with arguments swapped.
# "X is filled with Y" / "X contains Y" → "Y is in X".
# "in" is treated as universally available (it appears as a first-class
# preposition throughout axioms_std.js §7c/§7e), so the bridge is gated only
# on the source relation appearing in the input or in axiom_vocab.
# "holding" is NOT in this list — semantically "X is holding Y" = "X has Y",
# not "Y is in X" (e.g. "the woman holding a lamp" doesn't mean lamp-in-woman).
_CONTAINMENT_BRIDGES = (
    "filled with",
    "contain",
    "containing",
    "contains",
)


def inject_containment_bridge_axioms(result, axiom_vocab=frozenset()):
  """For each containment relation in _CONTAINMENT_BRIDGES that appears in
  the input clauses or axiom_vocab, emit a static bridge axiom mapping it
  to "is rel2 in" with arguments swapped.

  Shape:
    [-is rel2 SRC X Y Ct, is rel2 in Y X Ct]

  Closes case 84 ("The cup filled with water fell. The cup contained
  water?") on deepseek and claude — the assertion uses "filled with" while
  the question uses "contain"/"in"; both resolve through "in" via these
  bridges.
  """
  words = _collect_eligible_words(result)
  all_known = set(words) | axiom_vocab
  axioms = []
  for rel in _CONTAINMENT_BRIDGES:
    if rel not in all_known:
      continue
    ct = _fresh_fv()
    clause = [
        ["-is rel2", rel, "?:X", "?:Y", ct],
        ["is rel2", "in", "?:Y", "?:X", ct],
    ]
    axioms.append({"@name": "frm_contain", "@logic": clause})
  return axioms


# ======== carrier vocabulary lift ========

# Carrier nouns: small movable surfaces that "pass through" the on-support
# relation. The carrier-transparency axiom (axioms_std.js §7g) consumes
# `isa(carrier, X, Ctxt)` to derive on(X, S) from on(X, C) + on(C, S).
# Each lift here is emitted only when its noun appears in the input clauses
# or axiom_vocab (mirrors REQUIRE_BOTH_SIDES from soft synonyms).
_CARRIER_NOUNS = frozenset({
    "plate", "tray", "saucer", "dish",
    "newspaper", "napkin", "tablecloth",
    "mat", "rug", "carpet",
})


def inject_carrier_lifts(result, axiom_vocab=frozenset()):
  """Scan clause list for carrier nouns; emit one isa-to-carrier
  lifting clause per noun present in input or axiom_vocab.

  Shape (per noun N):
    [-isa N ?:X ?:Ctxt, isa "carrier" ?:X ?:Ctxt]
  """
  words = _collect_eligible_words(result)
  all_known = set(words) | axiom_vocab
  axioms = []
  for noun in _CARRIER_NOUNS:
    if noun not in all_known:
      continue
    ct = _fresh_fv()
    clause = [
        ["-isa", noun, "?:X", ct],
        ["isa", "carrier", "?:X", ct],
    ]
    axioms.append({"@name": "frm_carrier_lift", "@logic": clause})
  return axioms


# ======== world-graph geometry ========

def inject_world_geometry(result):
  """Emit a minimal `next` chain spanning the concrete worlds (W0, W1, ...)
  actually present in the clause list.

  Replaces the static W0..W12 chain that used to live in axioms_std.js §11.
  When 0 or 1 distinct worlds are present, emits nothing (transitivity has
  nothing to chain). Otherwise fills any gaps in [min_idx, max_idx] so the
  `before` transitivity closure still derives `before(Wi,Wj)` for all
  observed i<j.
  """
  worlds = set()
  def _scan(tree):
    if isinstance(tree, str):
      if _is_world_constant(tree):
        worlds.add(tree)
      return
    if isinstance(tree, list):
      for el in tree:
        _scan(el)
  for obj in result:
    if not isinstance(obj, dict):
      continue
    for key in ("@logic", "@question"):
      v = obj.get(key)
      if v is not None:
        _scan(v)

  if len(worlds) <= 1:
    return []

  indices = sorted(int(w[1:]) for w in worlds)
  lo, hi = indices[0], indices[-1]
  axioms = []
  for i in range(lo, hi):
    axioms.append({"@name": "frm_world_geom",
                   "@sourcetype": "world_geometry",
                   "@logic": ["next", "W" + str(i), "W" + str(i + 1)]})
  return axioms
