# Pre-clausification formula rewrites for the llm-based nlpsolver.
#
# Pure formula-tree transformations applied before clausification:
#   - Meta-predicate normalization (is_rel2("is",...) → isa, "located in" → "in")
#   - Degree presupposition injection ("not very X" → X and not very X)
#   - Misnested existential hoisting (fix scoping errors from LLMs)
#   - Spurious "can" removal from event queries
#   - Consequent negation for low-confidence rules
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

import re


# ======== meta-predicate normalization ========

# "located X" → "X" for spatial prepositions
_LOCATED_PREFIX_MAP = {}
for _p in ("in", "at", "on", "near", "above", "under"):
  _LOCATED_PREFIX_MAP["located " + _p] = _p


# Preposition canonicalisation — pure surface-form variants mapped to the
# canonical form used by the exclusion/subsumption axioms. Handled as
# rewriting (not axioms) because the variants are the SAME concept, just
# spelled differently. Near-synonyms with distinct meaning (over/above,
# under/below, on_top_of/above) are handled by subsumption axioms in
# axioms_std.js, NOT by this table.
_PREP_CANONICAL = {
  # spatial — spaced form → underscored form (LLM mostly underscores already)
  "in front of":       "in_front_of",
  "in front":          "in_front_of",   # missing trailing "of"
  "front of":          "in_front_of",   # missing leading "in"
  "in back of":        "behind",        # colloquial ≡ behind
  "back of":           "behind",
  "to the left of":    "left_of",
  "left of":           "left_of",
  "to the right of":   "right_of",
  "right of":          "right_of",
  "on top of":         "on_top_of",
  "inside of":         "inside",
  "outside of":        "outside",
  "out of":            "outside",
  "far away from":     "far_from",
  "far from":          "far_from",
  "far":               "far_from",       # has_degree_rel2 arg 1: LLM sometimes drops "from"
  "close to":          "near",           # canonical collapse (close_to ⊆ near)
  "close_to":          "near",
  "next to":           "next_to",
  # temporal
  "prior to":          "prior_to",
  "subsequent to":     "after",
}

def rewrite_meta_predicates(tree):
  """Normalize verbose/meta is_rel2 predicates throughout the formula tree.

  Copula/identity:
    ["is rel2", "is", A, B]          → ["isa", A, B]
    ["is rel2", "=",  A, B]          → ["=", A, B]

  Spatial meta-predicates:
    ["is rel2", "located in", A, B]  → ["is rel2", "in", A, B]
    ["is rel2", "located at", A, B]  → ["is rel2", "at", A, B]
    ["is rel2", "located on", A, B]  → ["is rel2", "on", A, B]
    etc. for near, above, under.

  Temporal meta-predicate:
    ["is rel2", "time of", E, X]     → ["has time", E, X, "in"]

  Handles negated forms as well.
  """
  if not isinstance(tree, list) or not tree:
    return tree
  op = tree[0] if isinstance(tree[0], str) else None
  # Movement verb synonyms: travel/journey/move → go
  # Normalizing in the pipeline avoids synonym axiom chains in the prover,
  # which cause combinatorial explosion with many world states.
  if op in ("has type", "-has type") and len(tree) >= 3:
    verb = tree[2]
    if isinstance(verb, str) and verb in ("travel", "journey", "move"):
      return [tree[0], tree[1], "go"] + tree[3:]
    # Transfer verb synonyms: hand/pass/send → give
    if isinstance(verb, str) and verb in ("hand", "pass", "send"):
      return [tree[0], tree[1], "give"] + tree[3:]
    # Placement verb synonyms: place/set/lay/position/deposit → put
    if isinstance(verb, str) and verb in ("place", "set", "lay", "position", "deposit"):
      return [tree[0], tree[1], "put"] + tree[3:]
  # has_destination 3-arg → 4-arg backward compat: insert "at" as default prep.
  # Stage 2 may emit ["has destination", E, Dest] (no prep); axioms now expect
  # ["has destination", E, Dest, Prep]. Insert "at" so existing encodings still work.
  if op in ("has destination", "-has destination") and len(tree) == 3:
    return [tree[0], tree[1], tree[2], "at"]
  if op in ("is rel2", "-is rel2") and len(tree) >= 4:
    pfx = "-" if op.startswith("-") else ""
    rel = tree[1]
    if isinstance(rel, str):
      # Copula/identity
      if rel == "is":
        return [pfx + "isa", tree[2], tree[3]]
      if rel == "=":
        return [pfx + "=", tree[2], tree[3]]
      # Temporal meta-predicate: "time of" → has_time with default prep
      if rel == "time of" and len(tree) >= 4:
        return [pfx + "has time", tree[2], tree[3], "in"]
      # Spatial meta-predicates: "located in" → "in", etc.
      canonical = _LOCATED_PREFIX_MAP.get(rel)
      if canonical:
        return [pfx + "is rel2", canonical] + tree[2:]
      # Preposition canonicalisation: "in front of" → "in_front_of" etc.
      canonical = _PREP_CANONICAL.get(rel)
      if canonical:
        return [pfx + "is rel2", canonical] + tree[2:]
  # Also canonicalise the preposition in has_degree_rel2 (near/far_from) and
  # in has_location / has_time / has_destination's preposition slot.
  if op in ("has degree rel2", "-has degree rel2") and len(tree) >= 2:
    rel = tree[1]
    if isinstance(rel, str):
      canonical = _PREP_CANONICAL.get(rel)
      if canonical:
        return [op, canonical] + list(tree[2:])
  if op in ("has location", "-has location",
            "has time", "-has time",
            "has destination", "-has destination") and len(tree) >= 4:
    prep = tree[3]
    if isinstance(prep, str):
      canonical = _PREP_CANONICAL.get(prep)
      if canonical:
        return list(tree[:3]) + [canonical] + list(tree[4:])
  return [rewrite_meta_predicates(child) if isinstance(child, list) else child
          for child in tree]


# ======== receive → give normalization ========

def normalize_receive_events(tree):
  """Rewrite 'receive' events to 'give' with swapped actor→recipient.

  In an ["and", ...] block containing ["has type", E, "receive"],
  changes the verb to "give" and swaps ["has actor", E, X] to
  ["has recipient", E, X].  This handles assertions where the input
  describes a receive event ("Mary received a book") so the prover
  can use the give-based transfer axioms.

  The give→receive axiom bridge in axioms_std.js handles the reverse
  direction (queries asking about "receive" when facts use "give").
  """
  if not isinstance(tree, list) or not tree:
    return tree
  op = tree[0] if isinstance(tree[0], str) else None
  # Look for ["and", ...] blocks containing a receive event.
  if op == "and" and len(tree) >= 2:
    # Find event variables bound to "receive".
    receive_evars = set()
    for item in tree[1:]:
      if (isinstance(item, list) and len(item) >= 3
          and isinstance(item[0], str) and item[0] in ("has type", "-has type")
          and item[2] == "receive"):
        receive_evars.add(item[1])
    if receive_evars:
      result = [tree[0]]
      for item in tree[1:]:
        item = normalize_receive_events(item)  # recurse first
        if isinstance(item, list) and len(item) >= 3 and isinstance(item[0], str):
          evar = item[1]
          if evar in receive_evars:
            if item[0] in ("has type", "-has type") and item[2] == "receive":
              # receive → give
              result.append([item[0], item[1], "give"] + item[3:])
              continue
            if item[0] in ("has actor", "-has actor"):
              # actor of receive → recipient of give
              neg = "-" if item[0].startswith("-") else ""
              result.append([neg + "has recipient"] + item[1:])
              continue
        result.append(item)
      return result
  # Recurse into sub-expressions.
  return [normalize_receive_events(child) if isinstance(child, list) else child
          for child in tree]


# ======== strip tense-valued has_time ========

_GRAMMATICAL_TENSES = frozenset({"past", "present", "future", "timeless"})

def strip_tense_has_time(tree):
  """Remove has_time atoms where the time value is a grammatical tense.

  LLMs sometimes produce ["has time", E, "past", "in"] in questions,
  treating grammatical tense as a time value.  These are always wrong —
  tense belongs in $ctxt, not in has_time.  Strips them from "and"
  conjunctions; replaces a standalone occurrence with True (no-op for
  clausification since the conjunction collapses).
  """
  if not isinstance(tree, list) or not tree:
    return tree
  op = tree[0] if isinstance(tree[0], str) else None
  # Check if this node IS a tense-valued has_time
  if op in ("has time", "-has time") and len(tree) >= 3:
    if isinstance(tree[2], str) and tree[2] in _GRAMMATICAL_TENSES:
      return None  # sentinel: remove this conjunct
  # Recurse into children; filter out None from "and" conjunctions
  if op == "and":
    children = []
    for child in tree[1:]:
      result = strip_tense_has_time(child)
      if result is not None:
        children.append(result)
    if not children:
      return None
    if len(children) == 1:
      return children[0]
    return ["and"] + children
  # Wrappers whose body may be stripped: propagate None upward.
  if op == "@time" and len(tree) == 3:
    body = strip_tense_has_time(tree[2])
    if body is None:
      return None
    return [tree[0], tree[1], body]
  return [strip_tense_has_time(child) if isinstance(child, list) else child
          for child in tree]


# ======== degree presupposition injection ========

def inject_degree_presuppositions(tree):
  """Expand negated high-degree properties to include a presupposed positive assertion.

  Recursively walks *tree* (the raw Stage-2 JSON) and replaces every occurrence of
    ["not", ["has degree property", P, E, "high", C]]
  with
    ["and", ["has degree property", P, E, "none", C],
            ["not", ["has degree property", P, E, "high", C]]]

  "John is not very big" presupposes that John IS big (at the unmarked/none degree).
  The LLM pipelines only emit the negation; this adds the implicit positive assertion.
  """
  if not isinstance(tree, list) or len(tree) == 0:
    return tree
  # Recurse into children first (bottom-up).
  tree = [inject_degree_presuppositions(child) for child in tree]
  # Check for the target pattern.
  if (len(tree) == 2
      and tree[0] == "not"
      and isinstance(tree[1], list)
      and len(tree[1]) >= 4
      and tree[1][0] == "has degree property"
      and tree[1][3] == "high"):
    inner = tree[1]          # ["has degree property", P, E, "high", C]
    positive = list(inner)
    positive[3] = "none"     # ["has degree property", P, E, "none", C]
    return ["and", positive, tree]
  return tree


# ======== hoist misnested existentials ========

_VAR_PAT = re.compile(r'^[A-Z][A-Z0-9]?$')  # X, Y, Z, E, E1, X1, etc.

def _is_stage2_var(s):
  """True if s looks like a Stage-2 variable name (short uppercase)."""
  return isinstance(s, str) and _VAR_PAT.match(s) is not None

def _collect_free_vars(node, bound):
  """Collect Stage-2 variable names used free (not in bound) in node."""
  free = set()
  if not isinstance(node, list) or not node:
    return free
  op = node[0]
  if op in ("exists", "forall") and len(node) == 3:
    return _collect_free_vars(node[2], bound | {node[1]})
  if isinstance(op, str) and not isinstance(op, list):
    # Atom: check arguments (skip predicate name at index 0)
    for arg in node[1:]:
      if _is_stage2_var(arg) and arg not in bound:
        free.add(arg)
      elif isinstance(arg, list):
        free |= _collect_free_vars(arg, bound)
  else:
    for child in node:
      if isinstance(child, list):
        free |= _collect_free_vars(child, bound)
  return free

def hoist_misnested_exists(formula, bound=None):
  """Hoist existential quantifiers that bind variables used free in sibling conjuncts.

  Only processes ["and",...] nodes. Recurses into sub-formulas first (bottom-up),
  then checks the current and-node for misnested exists.
  """
  if bound is None:
    bound = set()
  if not isinstance(formula, list) or not formula:
    return formula
  op = formula[0]
  if op in ("exists", "forall") and len(formula) == 3:
    formula[2] = hoist_misnested_exists(formula[2], bound | {formula[1]})
    return formula
  if op == "implies" and len(formula) == 3:
    formula[1] = hoist_misnested_exists(formula[1], bound)
    formula[2] = hoist_misnested_exists(formula[2], bound)
    return formula
  if op != "and":
    # Recurse into children
    for i in range(len(formula)):
      if isinstance(formula[i], list):
        formula[i] = hoist_misnested_exists(formula[i], bound)
    return formula

  # op == "and": recurse into children first (bottom-up)
  for i in range(1, len(formula)):
    if isinstance(formula[i], list):
      formula[i] = hoist_misnested_exists(formula[i], bound)

  # Now check for misnested exists in this and-node
  changed = True
  while changed:
    changed = False
    conjuncts = formula[1:]  # re-read after mutations
    # Find exists conjuncts and free vars in non-exists conjuncts
    for i, conj in enumerate(conjuncts):
      if not (isinstance(conj, list) and len(conj) == 3
              and conj[0] == "exists"):
        continue
      var = conj[1]
      body = conj[2]
      # Check if var appears free in any other conjunct
      used_free = False
      for j, other in enumerate(conjuncts):
        if j == i:
          continue
        if var in _collect_free_vars(other, bound):
          used_free = True
          break
      if not used_free:
        continue
      # Collision check: var must not be already bound by enclosing scope
      if var in bound:
        continue
      # Hoist: remove the exists conjunct, merge body into and, wrap in exists
      idx = i + 1  # offset for "and" at index 0
      formula.pop(idx)
      # Merge body conjuncts into the and list
      if isinstance(body, list) and body and body[0] == "and":
        for bc in body[1:]:
          formula.append(bc)
      else:
        formula.append(body)
      # Wrap in exists
      formula = ["exists", var, formula]
      # Update bound for next iteration
      bound = bound | {var}
      changed = True
      break  # restart scan after mutation
    if changed and isinstance(formula, list) and formula[0] == "exists":
      # The and-node is now formula[2]; continue hoisting inside it
      formula[2] = hoist_misnested_exists(formula[2], bound)
      break

  return formula


# ======== spurious "can" removal ========

_MODAL_WORDS = frozenset({
  "can", "could", "able", "capable", "possible", "allowed",
  "permitted", "may", "might", "ability",
})

def strip_spurious_can(formula, asu_text):
  """Remove ["can", X, E] from event queries when no modal language is present.

  Only fires when:
  - The ASU text contains no modal words
  - ["can", X, E] appears in an ["and",...] conjunction inside question/ask
  - The same conjunction contains ["isa","activity",E] and ["has actor",E,X]
  - Both X and E are existentially quantified
  """
  if not asu_text or not isinstance(formula, list) or len(formula) < 2:
    return formula
  # Check for modal language in ASU text
  text_lower = asu_text.lower()
  for mw in _MODAL_WORDS:
    if mw in text_lower:
      return formula
  # Walk and strip
  _strip_can_walk(formula, set())
  return formula

def _strip_can_walk(node, existential_vars):
  """Recursively walk formula, collecting existential vars, stripping can."""
  if not isinstance(node, list) or not node:
    return
  op = node[0]
  if op == "exists" and len(node) == 3:
    new_vars = existential_vars | {node[1]}
    _strip_can_walk(node[2], new_vars)
    return
  if op in ("question", "ask"):
    for child in node[1:]:
      _strip_can_walk(child, existential_vars)
    return
  if op == "and":
    _try_remove_can(node, existential_vars)
    for child in node[1:]:
      if isinstance(child, list):
        _strip_can_walk(child, existential_vars)
    return
  for child in node:
    if isinstance(child, list):
      _strip_can_walk(child, existential_vars)

def _try_remove_can(and_node, existential_vars):
  """If and_node contains a spurious ["can",X,E], remove it."""
  conjuncts = and_node[1:]
  can_idx = None
  can_x = None
  can_e = None
  for i, c in enumerate(conjuncts):
    if (isinstance(c, list) and len(c) >= 3
        and c[0] == "can" and isinstance(c[1], str) and isinstance(c[2], str)):
      can_idx = i + 1  # offset by 1 for "and" at index 0
      can_x = c[1]
      can_e = c[2]
      break
  if can_idx is None:
    return
  # Check X and E are existentially quantified
  if can_x not in existential_vars or can_e not in existential_vars:
    return
  # Check for isa("activity", E) and has_actor(E, X) in same conjunction
  has_isa_activity = False
  has_actor = False
  for c in conjuncts:
    if not isinstance(c, list):
      continue
    if (len(c) >= 3 and c[0] == "isa" and c[1] == "activity" and c[2] == can_e):
      has_isa_activity = True
    if (len(c) >= 3 and c[0] == "has actor" and c[1] == can_e and c[2] == can_x):
      has_actor = True
  if has_isa_activity and has_actor:
    and_node.pop(can_idx)


# ======== pre-clausification polarity flip ========

def flip_polarity_atom(frm):
  """Toggle the sign of a single literal (add/remove "-" prefix on predicate)."""
  if not isinstance(frm, list) or not frm:
    return frm
  pred = frm[0]
  if not isinstance(pred, str):
    return frm
  if pred.startswith("-"):
    return [pred[1:]] + frm[1:]
  return ["-" + pred] + frm[1:]


def negate_inner(frm):
  """Negate the innermost content of a formula (used for consequent negation).

  Strips outermost exists/and wrappers, then flips the atom or normally body.
  Returns the negated form for use inside a normally wrapper.
  """
  if not isinstance(frm, list) or not frm:
    return ["not", frm]
  op = frm[0]
  if op == "exists" and len(frm) >= 3:
    return ["forall", frm[1], ["not", frm[2]]]
  if op == "and":
    if len(frm) >= 3:
      return [op] + list(frm[1:-1]) + [negate_inner(frm[-1])]
    return frm
  if op == "normally":
    if len(frm) >= 2:
      return [op, ["not", frm[1]]]
    return frm
  if op == "forall" and len(frm) >= 3:
    return [op, frm[1], negate_inner(frm[2])]
  if op == "implies" and len(frm) >= 3:
    return [op, frm[1], negate_inner(frm[2])]
  if op == "not" and len(frm) >= 2:
    return frm[1]
  return flip_polarity_atom(frm)


# Non-atomic operators: these are connectives, wrappers, or other compound
# formulas that should be negated by wrapping in ["not", ...] rather than
# flipping a predicate prefix.  The clausifier handles the NNF distribution.
_NON_ATOMIC_OPS = frozenset({
  "and", "or", "not", "implies", "equivalent", "xor",
  "normally", "typically", "holds", "question", "ask",
})

def negate_consequent(formula):
  """Negate the consequent of a rule formula before clausification.

  Handles:
    ["implies", A, B]            → ["implies", A, negate_inner(B)]
    ["forall", X, F]             → ["forall", X, negate_consequent(F)]
    ["exists", X, F]             → ["forall", X, ["not", F]]
    non-atomic formula           → ["not", formula]  (clausifier handles via NNF)
    bare atom ["pred", ...]      → ["-pred", ...]
  """
  if not isinstance(formula, list) or not formula:
    return formula
  op = formula[0]
  if not isinstance(op, str):
    return ["not", formula]
  if op == "implies" and len(formula) >= 3:
    return [op, formula[1], negate_inner(formula[2])]
  if op == "forall" and len(formula) >= 3:
    return [op, formula[1], negate_consequent(formula[2])]
  if op == "exists" and len(formula) >= 3:
    return ["forall", formula[1], ["not", formula[2]]]
  if op in _NON_ATOMIC_OPS:
    # "not" here gives double-negation: ["not",["not",F]] → clausifier eliminates
    return ["not", formula]
  return flip_polarity_atom(formula)
