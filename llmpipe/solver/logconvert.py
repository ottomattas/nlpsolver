# Logic conversion for the llm-based nlpsolver.
#
# Entry point: rawlogic_convert(logic)
# Takes stage-2 LLM output and produces GK-compatible clause list.
#
# Stage-2 input format:
#   ["and", ["@id","S1", PACKAGE], ["@id","S2", PACKAGE], ...]
#
# PACKAGE is one of:
#   ["holds", world, F]           - assertion: extract F
#   ["question", F]               - query: use F with @question key
#   ["ask", var, F]               - query with binding var -> ["exists",var,F]
#   ["and", PKG, ["@p","Sx",p]]   - with confidence metadata
#
# Output format (GK input):
#   [{"@name":"sent_S1", "@logic": CLAUSE}, ...]
#   {"@name":"sent_S3", "@question": FORMULA}
#
# GK clauses:
#   Single atom:         ["pred", arg, ...]
#   Multi-literal (or):  [["pred1",...], ["pred2",...], ...]
# Variables:  "?:X" (free vars = implicitly universally quantified in GK)
# Negation:   "-" prefix on predicate name, e.g. "-isa"
#
# Module structure:
#   lc_clausify.py   -- FOL-to-CNF compiler (clausify and helpers)
#   lc_questions.py  -- question wrapping and population fact injection
#   logconvert.py    -- main driver, package extraction, context injection,
#                       post-processing passes (this file)
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
#-------------------------------------------------------------------

import os as _os

from globals import options as _g_options

import lc_clausify
import lc_questions

from lc_clausify import clausify

from lc_questions import (
  simplify_contradictory_and,
  is_simple_question_formula,
  collect_body_free_vars,
  find_haslocation_prep,
  build_defq_question,
  find_where_atom,
  build_where_question,
  flatten_q_atoms,
  scan_item_formula,
  build_population_facts,
  is_ground_term,
  S2_VAR_RE,
  WHERE_SPATIAL_PREPS,
)


# ======== gradable property whitelist ========

def _load_gradable_props():
  """Load solver/gradables.txt into a frozenset of lowercase property names."""
  try:
    path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "gradables.txt")
    with open(path) as f:
      return frozenset(line.strip().lower() for line in f if line.strip())
  except Exception:
    return frozenset()

_GRADABLE_PROPS = _load_gradable_props()

# Counter for fresh free-variable names in $ctxt injection (reset per top-level call).
_fv_nr = 0

# Predicates that receive a $ctxt term as their last argument during context injection.
# Structural predicates (isa, holds, state*, next, kb*, @*, $*, =, <, >) are excluded.
_CTXT_ELIGIBLE = frozenset({
  "has property", "have", "has part", "can", "is rel2",
  "has degree property", "has degree rel2",
  "has type", "has actor", "has target", "has location",
  "has instrument", "has manner", "has direction", "has time",
  "typical", "typically",
})


# ======== main entry point ========

def _build_asu_index(s1_json):
  """Build a {unit_id: ASU} dict from Stage-1 JSON for programmatic $ctxt injection.

  s1_json is the list of sentence packages returned by llmparse.parse_text().
  Returns an empty dict when s1_json is None or malformed.
  """
  if not s1_json or not isinstance(s1_json, list):
    return {}
  index = {}
  for pkg in s1_json:
    if not isinstance(pkg, dict):
      continue
    for asu in pkg.get("units", []):
      if isinstance(asu, dict):
        uid = asu.get("unit_id")
        if uid:
          index[uid] = asu
  return index


def _build_entity_category_clauses(s1_json):
  """Build isa clauses for concrete entities that carry a category annotation.

  For each unique concrete entity with a "category" field in any ASU, emits:
    {"@name": "entity_S<N>", "@logic": ["isa", category, entity_id]}
  where S<N> is the unit_id of the first ASU in which the entity appears.
  Deduplicates by entity_id so each entity produces at most one clause.
  """
  if not s1_json or not isinstance(s1_json, list):
    return []
  seen = set()
  clauses = []
  for pkg in s1_json:
    if not isinstance(pkg, dict):
      continue
    for asu in pkg.get("units", []):
      if not isinstance(asu, dict):
        continue
      uid = asu.get("unit_id", "")
      for ent in asu.get("entities", []):
        if not isinstance(ent, dict):
          continue
        eid      = ent.get("id")
        category = ent.get("category")
        if not eid or not category:
          continue
        if ent.get("type") != "concrete":
          continue
        if eid in seen:
          continue
        seen.add(eid)
        clauses.append({"@name": "entity_" + uid,
                        "@logic": ["isa", category, eid]})
  return clauses


def rawlogic_convert(logic, s1_json=None):
  """Convert stage-2 LLM output to a GK-compatible clause list.

  Input:  stage-2 list ["and", ["@id","S1",PACKAGE], ...]
          s1_json -- Stage-1 JSON from llmparse.parse_text(), used for
                     programmatic $ctxt injection (tense, world, location)
                     and entity category isa injection.
  Output: list of {"@name":..., "@logic":CLAUSE} / {"@name":..., "@question":F}
  Returns None on fatal error.
  """
  global _fv_nr
  _fv_nr = 0                    # reset once for the whole conversion
  lc_clausify._skolem_nr = 0
  lc_clausify._gobj_nr   = 0
  lc_questions._defq_nr  = 0

  if not logic or not isinstance(logic, list):
    return None

  if logic[0] == "@id":
    items = [logic]
  elif logic[0] == "and":
    items = logic[1:]
  else:
    return None

  # Build unit_id -> ASU index for programmatic $ctxt injection from Stage-1 data.
  asu_index = _build_asu_index(s1_json)

  # Build entity category isa facts from Stage-1 entity annotations.
  # These are prepended to the clause list so the prover sees them as given facts.
  entity_cat_clauses = _build_entity_category_clauses(s1_json)

  # Build population facts by scanning the raw stage-2 input first.
  pop_facts = _populate_clauses(items)

  # Track how many times each unit_id has been seen so we can generate
  # globally unique clause names (sent_S1, sent_S1_2, sent_S1_3, ...).
  uid_count = {}
  result = []
  for item in items:
    if isinstance(item, list) and len(item) >= 2 and item[0] == "@id":
      sid = str(item[1])
      uid_count[sid] = uid_count.get(sid, 0) + 1
      objs = _convert_id_package(item, asu_index, uid_suffix=uid_count[sid])
    else:
      objs = _convert_id_package(item, asu_index)
    if objs:
      result.extend(objs)

  # Prepend entity category clauses at the start of the clause list so they
  # are available as given facts throughout the proof.
  result = entity_cat_clauses + result

  # Insert population facts immediately before the first @question entry
  # so they are available as background knowledge during proof search.
  first_q = next((i for i, o in enumerate(result) if "@question" in o), len(result))
  for i, fact in enumerate(pop_facts):
    result.insert(first_q + i, fact)

  # Inject $ctxt into population facts (all-free variables; they are background rules).
  if not _g_options.get("nocontext_flag", False):
    for fact in pop_facts:
      ctxt = ["$ctxt", _fresh_fv(), _fresh_fv(), _fresh_fv(), _fresh_fv()]
      _inject_ctxt_into_objs([fact], ctxt)

  # Infer have(Y,E,CT) from possessive is_rel2(T+" of",E,Y,CT) + isa(T,E) pairs.
  _add_possessive_have(result)

  # Normalize has property / has degree property based on the gradable whitelist.
  # Must run before _coerce_relclass so relclass coercion sees the correct predicate.
  _normalize_gradable_predicates(result)

  # Remove isa/entity literals: positive ones make a clause a tautology (remove
  # the whole clause); negative ones are always false (remove just the literal).
  _strip_isa_entity(result)

  # Fix RELCLASS mismatches in question degree-predicate atoms.
  _coerce_relclass(result)

  # When -simpleproperties / -simple is active, replace degree predicates with
  # their non-gradable equivalents so the prover sees simpler atoms.
  if _g_options.get("noproptypes_flag", False):
    _strip_degree_predicates(result)

  # Strip @sourcetype before handing the clause list to the prover;
  # it is an internal annotation only needed during logconvert processing.
  for obj in result:
    if isinstance(obj, dict):
      obj.pop("@sourcetype", None)

  return result


# ======== pre-clausification polarity flip ========

def _flip_polarity_atom(frm):
  """Toggle the sign of a single literal (add/remove "-" prefix on predicate)."""
  if not isinstance(frm, list) or not frm:
    return frm
  pred = frm[0]
  if not isinstance(pred, str):
    return frm
  if pred.startswith("-"):
    return [pred[1:]] + frm[1:]
  return ["-" + pred] + frm[1:]


def _negate_inner(frm):
  """Negate the innermost content of a formula (used for consequent negation).

  Strips outermost exists/and wrappers, then flips the atom or normally body.
  Returns the negated form for use inside a normally wrapper.
  """
  if not isinstance(frm, list) or not frm:
    return ["not", frm]
  op = frm[0]
  if op == "exists" and len(frm) >= 3:
    # ¬∃Y.P  =  ∀Y.¬P  (De Morgan)
    return ["forall", frm[1], ["not", frm[2]]]
  if op == "and":
    # and(A,B) → negate the last child (the action/conclusion)
    if len(frm) >= 3:
      return [op] + list(frm[1:-1]) + [_negate_inner(frm[-1])]
    return frm
  if op == "normally":
    # normally(B) → normally(not(B)); clausify's _expand_normally will call
    # _push_neg on "not(B)" to produce the negated body literals.
    if len(frm) >= 2:
      return [op, ["not", frm[1]]]
    return frm
  if op == "forall" and len(frm) >= 3:
    # forall X. P → forall X. _negate_inner(P)
    return [op, frm[1], _negate_inner(frm[2])]
  if op == "implies" and len(frm) >= 3:
    # implies(A, B) → implies(A, _negate_inner(B))
    return [op, frm[1], _negate_inner(frm[2])]
  if op == "not" and len(frm) >= 2:
    # not(P) → P  (double negation elimination)
    return frm[1]
  # Plain atom — negate directly.
  return _flip_polarity_atom(frm)


def _negate_consequent(formula):
  """Negate the consequent of a rule formula before clausification.

  Handles:
    ["implies", A, B]            → ["implies", A, _negate_inner(B)]
    ["forall", X, F]             → ["forall", X, _negate_consequent(F)]
    ["exists", X, F]             → ["forall", X, ["not", F]]   (De Morgan: ¬∃X.F = ∀X.¬F)
    ["normally", B]              → ["normally", ["not", B]]
    ["not", F]                   → F  (double negation elimination)
    bare atom ["pred", ...]      → ["-pred", ...]
  """
  if not isinstance(formula, list) or not formula:
    return formula
  op = formula[0]
  if op == "implies" and len(formula) >= 3:
    return [op, formula[1], _negate_inner(formula[2])]
  if op == "forall" and len(formula) >= 3:
    return [op, formula[1], _negate_consequent(formula[2])]
  if op == "exists" and len(formula) >= 3:
    # ¬∃X.F  =  ∀X.¬F  (De Morgan) — clausify handles forall+not correctly
    return ["forall", formula[1], ["not", formula[2]]]
  if op == "normally" and len(formula) >= 2:
    return [op, ["not", formula[1]]]
  if op == "not" and len(formula) >= 2:
    return formula[1]  # double negation elimination
  # Bare atom.
  return _flip_polarity_atom(formula)


# ======== package extraction ========

def _convert_id_package(item, asu_index=None, uid_suffix=None):
  """Process ["@id", sid, PACKAGE] → list of GK clause dicts."""
  if not isinstance(item, list) or len(item) < 3 or item[0] != "@id":
    return []
  sid = item[1]
  package = item[2]
  name = "sent_" + str(sid)
  if uid_suffix is not None and uid_suffix > 1:
    name = name + "_" + str(uid_suffix)

  is_question, formula, confidence, world, location, knower, tense = _extract_package_ctx(package)
  if formula is None:
    return []

  # Override $ctxt parameters with Stage-1 ASU data when available.
  # Stage-1 "time", "pre_state", "location" are more reliable than scanning
  # Stage-2 siblings; this is the programmatic $ctxt injection (option B).
  if asu_index:
    asu = asu_index.get(sid)
    if asu is not None:
      s1_tense = asu.get("time")
      if s1_tense is not None:
        tense = s1_tense
      if is_question:
        s1_world = asu.get("pre_state")
        if s1_world is not None:
          world = s1_world
      s1_loc = asu.get("location")
      if s1_loc is not None:
        location = s1_loc

  is_where_question = False
  if is_question:
    # Distinguish wh-questions (["ask", var, body]) from yes/no questions.
    if isinstance(formula, list) and len(formula) >= 3 and formula[0] == "ask":
      ask_var = str(formula[1])
      body    = formula[2]
      # "Where is X?" pattern: body contains ["is rel2", <meta-pred>, entity, ask_var]
      where_atom = find_where_atom(body, ask_var)
      if where_atom is not None:
        entity = where_atom[2]
        atom_pred = where_atom[1]
        # Use specific prep when query uses a concrete spatial preposition;
        # use all preps for meta-predicates like "located in".
        specific_prep = atom_pred if atom_pred in WHERE_SPATIAL_PREPS else None
        # When the entity is a stage-2 variable (e.g. "E" from an event),
        # build_where_question would generate an over-broad biconditional
        # matching ANY event's location.  Instead, use build_defq_question
        # which preserves all constraints from the original body.
        entity_is_s2var = isinstance(entity, str) and bool(S2_VAR_RE.match(entity))
        if specific_prep and entity_is_s2var:
          result = build_defq_question(name, ask_var, body, where_prep=specific_prep)
        else:
          result = build_where_question(name, entity, ask_var, specific_prep=specific_prep)
        is_where_question = True
      elif is_simple_question_formula(body):
        # Single atom with ≤1 variable: direct @question, no $defq wrapper.
        free_vars_in_body = sorted(collect_body_free_vars(body))
        varmap = {ask_var: "?:" + ask_var}
        varmap.update({v: "?:" + v for v in free_vars_in_body})
        flat = flatten_q_atoms(body, varmap)
        if not flat:
          return []
        q_formula = flat[0] if len(flat) == 1 else [["and"] + flat]
        result = [{"@name": name, "@question": q_formula, "@askvars": 1}]
      else:
        # Complex case: wrap in $defq biconditional.
        # Detect has_location(E, ask_var) → encode "in" as the preposition.
        where_prep = find_haslocation_prep(body, ask_var)
        result = build_defq_question(name, ask_var, body, where_prep=where_prep)
        if where_prep:
          is_where_question = True
    else:
      # Yes/no question.
      # When $ctxt is active, always use $defq so the @question atom is the
      # machinery literal ["$defq0"] (no free variables → GK returns plain
      # `true` rather than `$ans(W0,…)` which confuses answer extraction).
      if is_simple_question_formula(formula) and _g_options.get("nocontext_flag", False):
        # Direct @question only when $ctxt is disabled.
        free_vars_in_formula = sorted(collect_body_free_vars(formula))
        varmap = {v: "?:" + v for v in free_vars_in_formula}
        flat = flatten_q_atoms(formula, varmap)
        if not flat:
          return []
        q_formula = flat[0] if len(flat) == 1 else [["and"] + flat]
        result = [{"@name": name, "@question": q_formula}]
      else:
        # Complex formula, or: simple but $ctxt active → $defq biconditional.
        # Fix contradictory ["and", ["not", A], A] that LLM generates for
        # "No X is Y?" questions — simplify to just ["not", A].
        formula = simplify_contradictory_and(formula)
        result = build_defq_question(name, None, formula)
  else:
    # Pre-clausification polarity flip for low-confidence negative-leaning rules.
    # Stage-1 probability p ∈ (0, 0.5) → negate the consequent BEFORE clausify
    # so the negation is encoded in the formula structure (avoids Skolem companion
    # clause split that the post-clausification approach suffered from).
    if confidence is not None and 0 < confidence < 0.5:
      formula = _negate_consequent(formula)
      confidence = round(1.0 - 2.0 * confidence, 4)
    elif confidence is not None and 0.5 < confidence < 1.0:
      confidence = round(2.0 * confidence - 1.0, 4)
    elif confidence == 0.5:
      confidence = 0   # exactly 0.5 → abs(2*0.5-1)=0; prover filters it out → "no information"
    # Clausify the formula.
    clauses = clausify(formula)
    result = []
    for clause in clauses:
      # Confidence 0.0 means 50% probability: abs(2*0.5-1)=0, no evidence either
      # way.  GK rejects @confidence values of exactly 0, so skip the clause
      # entirely — the prover will return "no information".
      if confidence == 0.0:
        continue
      obj = {"@name": name, "@logic": clause}
      if confidence is not None:
        obj["@confidence"] = confidence
      result.append(obj)

  # Inject $ctxt into @logic entries (not @question entries).
  if not _g_options.get("nocontext_flag", False):
    if _is_rule_formula(formula):
      situation  = _fresh_fv()
      tense_term = _fresh_fv()   # rules are tense-independent
    elif is_question:
      if is_where_question:
        # Where-query biconditionals must be world-agnostic: location facts
        # may come from any world state (e.g. W0 travel facts vs W2 query).
        situation  = _fresh_fv()
        tense_term = _fresh_fv()
      else:
        # For questions: world from Stage-1 pre_state (or free var); tense from Stage-1 time.
        situation  = world if world is not None else _fresh_fv()
        tense_term = tense if tense is not None else _fresh_fv()
    else:
      # Situational facts: world from ["holds",W,F]; tense from Stage-1 time field.
      situation  = world if world is not None else _fresh_fv()
      tense_term = tense if tense is not None else "present"
    loc_term = location if location is not None else _fresh_fv()
    kn_term  = knower  if knower  is not None else _fresh_fv()
    ctxt = ["$ctxt", tense_term, situation, loc_term, kn_term]
    _inject_ctxt_into_objs(result, ctxt)

  return result


def _extract_package(package):
  """Extract (is_question, formula, confidence) from a PACKAGE list."""
  if not isinstance(package, list) or not package:
    return False, None, None

  op = package[0]

  if op == "holds":
    # ["holds", world, F]
    if len(package) >= 3:
      return False, package[2], None
    return False, None, None

  elif op == "question":
    # ["question", F]
    if len(package) >= 2:
      return True, package[1], None
    return True, None, None

  elif op == "ask":
    # ["ask", var, F]  — wh-question; return as-is so _convert_id_package can
    # identify the answer variable before flattening.
    if len(package) >= 3:
      return True, package, None
    return True, None, None

  elif op == "and":
    # ["and", PKG, ["@p","Sx",p], ...]  — compound package with metadata
    main_pkg = None
    confidence = None
    for el in package[1:]:
      if isinstance(el, list) and len(el) == 3 and el[0] == "@p":
        confidence = el[2]
      elif main_pkg is None:
        main_pkg = el
    if main_pkg is not None:
      is_q, formula, _ = _extract_package(main_pkg)
      return is_q, formula, confidence
    return False, None, confidence

  else:
    # Unknown package type — treat as raw formula assertion.
    return False, package, None


def _extract_package_ctx(package):
  """Like _extract_package but also returns (world, location, knower, tense).

  Returns: (is_question, formula, confidence, world, location, knower, tense)
    world    -- the W constant from ["holds", W, F], or None
    location -- the LOC from a sibling ["state location", W, LOC], or None
                (fallback only; Stage-1 ASU "location" takes priority via _convert_id_package)
    knower   -- the HOLDER from a sibling ["kb", K, HOLDER, ...], or None
    tense    -- T from a sibling ["state time", W, T], or None
                (fallback only; Stage-1 ASU "time" takes priority via _convert_id_package)
  """
  if not isinstance(package, list) or not package:
    return False, None, None, None, None, None, None

  op = package[0]

  if op == "holds":
    if len(package) >= 3:
      return False, package[2], None, package[1], None, None, None
    return False, None, None, None, None, None, None

  elif op == "question":
    if len(package) >= 2:
      return True, package[1], None, None, None, None, None
    return True, None, None, None, None, None, None

  elif op == "ask":
    if len(package) >= 3:
      return True, package, None, None, None, None, None
    return True, None, None, None, None, None, None

  elif op == "and":
    main_pkg   = None
    confidence = None
    location   = None
    knower     = None
    tense      = None
    for el in package[1:]:
      if not isinstance(el, list) or not el:
        continue
      elop = el[0]
      if elop == "@p" and len(el) == 3:
        confidence = el[2]
      elif elop == "state location" and len(el) >= 3:
        location = el[2]
      elif elop == "state time" and len(el) >= 3:
        tense = el[2]
      elif elop == "kb" and len(el) >= 3:
        knower = el[2]   # ["kb", K, HOLDER, ATTITUDE, W]
      elif main_pkg is None:
        main_pkg = el
    if main_pkg is not None:
      is_q, formula, _, world, loc2, kn2, _ = _extract_package_ctx(main_pkg)
      if location is None:
        location = loc2
      if knower is None:
        knower = kn2
      return is_q, formula, confidence, world, location, knower, tense
    return False, None, confidence, None, location, knower, tense

  else:
    return False, package, None, None, None, None, None


# ======== population fact scanning ========

def _populate_clauses(items):
  """Scan all @id items in the raw stage-2 input and return population entries.

  This is the main entry point called from rawlogic_convert.  The underlying
  scanner (scan_item_formula) handles both raw stage-2 and clausified forms,
  so this function can also be applied to a clausified clause list.
  """
  classes   = {}   # CLASS -> {"name", "has_pos", "has_neg"}
  has_props = {}   # PROPERTY -> {"name", "has_pos", "has_neg"}
  deg_props = {}   # (PROPERTY, RELCLASS) -> {"name", "has_pos", "has_neg"}

  for item in items:
    if not isinstance(item, list) or len(item) < 3 or item[0] != "@id":
      continue
    name    = "sent_" + str(item[1])
    package = item[2]
    _is_q, formula, _conf = _extract_package(package)
    if _is_q:
      continue   # never populate from the question sentence — circular by construction
    if formula is not None:
      scan_item_formula(formula, name, True, classes, has_props, deg_props)

  return build_population_facts(classes, has_props, deg_props)


# ======== context injection ========

def _fresh_fv():
  """Return a fresh GK free-variable name, e.g. '?:Fv1', '?:Fv2', …"""
  global _fv_nr
  _fv_nr += 1
  return "?:Fv" + str(_fv_nr)


def _is_rule_formula(frm):
  """Return True if frm contains 'forall' or 'normally' at any nesting level."""
  if not isinstance(frm, list) or not frm:
    return False
  if frm[0] in ("forall", "normally"):
    return True
  return any(_is_rule_formula(el) for el in frm[1:])


def _inject_ctxt_atom(atom, ctxt):
  """Append ctxt as the last argument of an eligible GK atom.

  Handles:
    - ["$block", priority, ["$not", INNER]] — recurses into INNER
    - Eligible atoms (base pred in _CTXT_ELIGIBLE) — appends ctxt
    - Everything else — returns unchanged
  """
  if not isinstance(atom, list) or not atom:
    return atom
  pred = atom[0]
  if not isinstance(pred, str):
    return atom
  base = pred[1:] if pred.startswith("-") else pred

  if base == "or":
    return ["or"] + [_inject_ctxt_atom(sub, ctxt) for sub in atom[1:]]

  if base == "$block" and len(atom) >= 3:
    body = atom[2]
    if isinstance(body, list) and len(body) >= 2 and body[0] == "$not":
      inner = _inject_ctxt_atom(body[1], ctxt)
      return [atom[0], atom[1], ["$not", inner]]
    # Negative-head block: body is the positive exception target (no $not wrapper).
    inner = _inject_ctxt_atom(body, ctxt)
    return [atom[0], atom[1], inner]

  if base in _CTXT_ELIGIBLE:
    return list(atom) + [ctxt]

  return atom


def _inject_ctxt_clause(clause, ctxt):
  """Inject ctxt into a GK clause (single atom or disjunction of atoms)."""
  if not isinstance(clause, list) or not clause:
    return clause
  if isinstance(clause[0], list):
    # Disjunctive clause: list of atom-lists
    return [_inject_ctxt_atom(atom, ctxt) for atom in clause]
  # Single atom
  return _inject_ctxt_atom(clause, ctxt)


def _inject_ctxt_into_objs(objs, ctxt):
  """Inject ctxt into @logic and @question entries of clause dicts (in place).

  For @logic: handles single atoms and disjunctive clauses.
  For @question: injects into the question atom if eligible (simple questions).
    $defq machinery atoms (e.g. ["$defq0"]) are not in _CTXT_ELIGIBLE and are
    left unchanged, so complex $defq questions are unaffected.
  """
  for obj in objs:
    if not isinstance(obj, dict):
      continue
    if "@logic" in obj:
      obj["@logic"] = _inject_ctxt_clause(obj["@logic"], ctxt)
    if "@question" in obj:
      obj["@question"] = _inject_ctxt_atom(obj["@question"], ctxt)


# ======== RELCLASS coercion ========

# Maps predicate name -> (entity_arg_index, relclass_arg_index).
# Used to identify which argument is the entity (for class lookup) and which
# is the RELCLASS (to be replaced when it doesn't match the entity's known class).
_degree_preds_relclass = {
  "has degree property": (2, 4),   # [pred, PROP, ENTITY, DEGREE, RELCLASS]
  "has degree rel2":     (2, 5),   # [pred, REL, E1, E2, DEGREE, RELCLASS] — RELCLASS describes E1
}


def _coerce_relclass(result):
  """Fix RELCLASS mismatches in question degree-predicate atoms.

  Builds two maps from assertional @logic clauses:
    const_classes:   CONST -> {CLASS, ...}  (from isa(CLASS,CONST) facts)
    prop_relclasses: PROP  -> {RELCLASS, ...} (from has degree property assertions)

  For every has degree property atom in @question or @sourcetype:question entries:
    If relclass ∈ entity's known isa classes (spurious entity-category assignment)
    AND relclass does NOT appear as a relclass in any assertional clause for the
    same property (no matching rule exists) → replace with a fresh free variable
    so the question can unify with whichever rule actually applies.

  This fixes the case where stage-1 uses the entity's ontological category
  (e.g. "person") as relclass in a query, while the only relevant rule uses a
  different relclass (e.g. "bear").  Intentional relclasses from explicit nouns
  in the question ("Is John a big mouse?" → "mouse") are preserved because they
  don't match any of John's isa classes.

  Also retains the existing assertional mismatch-coercion (non-question path)
  and the has degree rel2 free-variable substitution in questions.

  Modifies result in place.
  """
  # --- 1. build lookup maps from assertional @logic entries ---
  const_classes   = {}   # CONST -> set of CLASS strings  (from isa facts)
  prop_relclasses = {}   # PROP  -> set of RELCLASS strings (from has degree property)

  for obj in result:
    if not isinstance(obj, dict):
      continue
    src = obj.get("@sourcetype")
    if src in ("question", "populate"):
      continue
    if "@logic" not in obj:
      continue
    clause = obj["@logic"]
    # Normalise to a list of atoms (handle both single-atom and disjunctive clauses).
    atoms = clause if (isinstance(clause, list) and clause and
                       isinstance(clause[0], list)) else [clause]
    for atom in atoms:
      if not isinstance(atom, list) or not atom or not isinstance(atom[0], str):
        continue
      pred = atom[0]
      # isa(CLASS, CONST) — build const_classes
      if pred == "isa" and len(atom) >= 3 and is_ground_term(atom[2]):
        const_classes.setdefault(atom[2], set()).add(str(atom[1]))
      # has degree property [pred, PROP, ENTITY, DEGREE, RELCLASS, ...]
      # Collect concrete (non-variable) relclass strings only.
      elif pred == "has degree property" and len(atom) >= 5:
        rc = atom[4]
        if isinstance(rc, str) and not rc.startswith("?"):
          prop_relclasses.setdefault(str(atom[1]), set()).add(rc)

  if not const_classes:
    return

  # --- 2. apply coercion to question entries ---
  for obj in result:
    if not isinstance(obj, dict):
      continue
    if "@question" in obj:
      obj["@question"] = _coerce_atom(obj["@question"], const_classes,
                                      prop_relclasses=prop_relclasses,
                                      is_question=True)
    if "@logic" in obj and obj.get("@sourcetype") == "question":
      obj["@logic"] = _coerce_clause(obj["@logic"], const_classes,
                                     prop_relclasses=prop_relclasses,
                                     is_question=True)


def _coerce_atom(atom, const_classes, prop_relclasses=None, is_question=False):
  """Recursively substitute RELCLASS in degree-predicate atoms.

  Handles both raw question formulas (with connectives and quantifiers)
  and flat GK clause atoms.

  For "has degree rel2" in questions: always use a fresh free variable.

  For "has degree property" in questions: use a fresh free variable when
    - relclass is one of the entity's known isa classes (stage-1 spuriously
      used the entity's ontological category), AND
    - that relclass does not appear as a relclass in any assertional clause
      for the same property (no matching rule exists to unify against).
  This preserves intentional relclasses from explicit comparison nouns
  ("Is John a big mouse?" keeps "mouse" when no mouse-bigness rule exists but
  "mouse" is not one of John's isa classes).

  For non-question assertional atoms: replace relclass when it mismatches the
  entity's single known isa class (original coercion behaviour).
  """
  if not isinstance(atom, list) or not atom:
    return atom
  pred = atom[0]
  if not isinstance(pred, str):
    return atom

  # Degree predicate (possibly with a leading "-" negation prefix).
  base = pred[1:] if pred.startswith("-") else pred
  if base in _degree_preds_relclass:
    entity_idx, relclass_idx = _degree_preds_relclass[base]
    if len(atom) > relclass_idx:
      entity   = atom[entity_idx]   if len(atom) > entity_idx   else None
      relclass = atom[relclass_idx]
      if is_question:
        # "has degree rel2": always free variable.
        if base == "has degree rel2" and isinstance(relclass, str):
          new_atom = list(atom)
          new_atom[relclass_idx] = _fresh_fv()
          return new_atom
        # "has degree property": free variable only when relclass was spuriously
        # derived from the entity's category AND no matching rule exists.
        if (base == "has degree property" and
            isinstance(relclass, str) and not relclass.startswith("?") and
            entity and is_ground_term(entity) and
            entity in const_classes and
            relclass in const_classes[entity] and
            relclass not in (prop_relclasses or {}).get(
                atom[1] if len(atom) > 1 else "", set())):
          new_atom = list(atom)
          new_atom[relclass_idx] = _fresh_fv()
          return new_atom
      else:
        # Assertional (non-question): replace relclass when it mismatches the
        # entity's single known isa class.
        if (entity and is_ground_term(entity) and
            entity in const_classes and
            isinstance(relclass, str) and
            relclass not in const_classes[entity]):
          known = const_classes[entity]
          if len(known) == 1:
            new_atom = list(atom)
            new_atom[relclass_idx] = next(iter(known))
            return new_atom
    return atom

  # Logical connectives / quantifiers: recurse.
  if pred in ("and", "or", "not"):
    return [pred] + [_coerce_atom(el, const_classes, prop_relclasses, is_question)
                     for el in atom[1:]]
  if pred in ("forall", "exists") and len(atom) >= 3:
    return [pred, atom[1], _coerce_atom(atom[2], const_classes, prop_relclasses, is_question)]

  return atom


def _coerce_clause(clause, const_classes, prop_relclasses=None, is_question=False):
  """Apply _coerce_atom to a GK clause (single atom or disjunction)."""
  if not isinstance(clause, list) or not clause:
    return clause
  # Disjunction: first element is itself a list of atoms.
  if isinstance(clause[0], list):
    return [_coerce_atom(atom, const_classes, prop_relclasses, is_question)
            for atom in clause]
  # Single atom.
  return _coerce_atom(clause, const_classes, prop_relclasses, is_question)


# ======== gradable predicate normalization ========

def _normalize_gradable_predicates(result):
  """Normalize has property / has degree property atoms based on _GRADABLE_PROPS.

  For every atom in @logic and @question entries:
    - "has degree property" where PROP not in whitelist
        → "has property" (DEGREE and RELCLASS dropped; $ctxt preserved)
    - "has property" where PROP is in whitelist
        → "has degree property" with DEGREE="none", RELCLASS=fresh_var ($ctxt preserved)
    - "has degree property" where PROP is in whitelist and RELCLASS == "entity"
        → RELCLASS replaced with a fresh free variable ("entity" is universal
          and blocks unification against specific-class annotations like "person")

  This ensures consistent predicate names across rules, facts, and queries
  regardless of whether Stage 1/Stage 2 emitted adjectives annotations.
  Modifies result in place.
  """
  if not _GRADABLE_PROPS:
    return result
  for obj in result:
    if not isinstance(obj, dict):
      continue
    if "@logic" in obj:
      obj["@logic"] = _norm_grad_frm(obj["@logic"])
    if "@question" in obj:
      obj["@question"] = _norm_grad_frm(obj["@question"])
  return result


def _norm_grad_frm(frm):
  """Recursively normalize one formula or GK clause for gradable predicates."""
  if not isinstance(frm, list) or not frm:
    return frm

  first = frm[0]

  # GK disjunctive clause: first element is itself a list — recurse into each atom.
  if isinstance(first, list):
    return [_norm_grad_frm(a) for a in frm]

  if not isinstance(first, str):
    return frm

  pred = first
  neg  = pred.startswith("-")
  base = pred[1:] if neg else pred
  pfx  = "-" if neg else ""

  if base == "has degree property" and len(frm) >= 5:
    # ["has degree property", PROP, ENTITY, DEGREE, RELCLASS, optional_$ctxt]
    prop = frm[1]
    if isinstance(prop, str) and prop.lower() not in _GRADABLE_PROPS:
      # Strip to has property; preserve $ctxt at position 5 if present.
      new_atom = [pfx + "has property", frm[1], frm[2]]
      if len(frm) >= 6:
        new_atom.append(frm[5])
      return new_atom
    # Keep as degree property; replace "entity" relclass with a free variable
    # since "entity" is universally true and carries no useful constraint.
    relclass = frm[4]
    if relclass == "entity":
      new_atom = [frm[0], frm[1], frm[2], frm[3], _fresh_fv()]
      if len(frm) >= 6:
        new_atom.append(frm[5])
      return new_atom

  elif base == "has property" and len(frm) >= 3:
    # ["has property", PROP, ENTITY, optional_$ctxt]
    prop = frm[1]
    if isinstance(prop, str) and prop.lower() in _GRADABLE_PROPS:
      # Upgrade to has degree property; use a free variable for relclass
      # (avoids spurious "entity" constant that can block unification).
      new_atom = [pfx + "has degree property", frm[1], frm[2], "none", _fresh_fv()]
      if len(frm) >= 4:
        new_atom.append(frm[3])
      return new_atom

  # Logical connectives / quantifiers: recurse into sub-formulas.
  return [frm[0]] + [_norm_grad_frm(a) if isinstance(a, list) else a
                     for a in frm[1:]]


# ======== isa-entity stripping ========

def _strip_isa_entity(result):
  """Remove all isa/entity literals from the clause list.

  Since "entity" is the universal base type (everything is an entity), the
  literal ["isa","entity",X] is always true and ["-isa","entity",X] is always
  false.  Keeping them causes spurious unification failures when a rule that
  uses a generic variable (annotated as entity) tries to match a concrete fact.

  Rules:
    - Any clause containing a POSITIVE ["isa","entity",X] literal is a
      tautology → remove the entire clause dict.
    - Any ["-isa","entity",X] literal is always false → remove just the
      literal from its clause.  If the clause becomes empty after removal,
      remove the entire clause dict.

  Only @logic dicts are touched; @question dicts are left unchanged.
  Modifies result in place and returns it.
  """
  def _is_pos_isa_entity(lit):
    return (isinstance(lit, list) and len(lit) >= 3
            and lit[0] == "isa" and lit[1] == "entity")

  def _is_neg_isa_entity(lit):
    return (isinstance(lit, list) and len(lit) >= 3
            and lit[0] == "-isa" and lit[1] == "entity")

  keep = []
  for obj in result:
    if not isinstance(obj, dict) or "@logic" not in obj:
      keep.append(obj)
      continue
    clause = obj["@logic"]
    # Unit atom (single literal, not a list-of-lists).
    if clause and not isinstance(clause[0], list):
      if _is_pos_isa_entity(clause) or _is_neg_isa_entity(clause):
        continue          # drop entire clause dict
      keep.append(obj)
      continue
    # Disjunctive clause (list of literal lists).
    if any(_is_pos_isa_entity(lit) for lit in clause):
      continue            # tautology → drop entire clause dict
    filtered = [lit for lit in clause if not _is_neg_isa_entity(lit)]
    if not filtered:
      continue            # empty clause after removal → drop
    obj["@logic"] = filtered
    keep.append(obj)
  result[:] = keep
  return result


# ======== possessive have inference ========

_ACTIVITY_ROLE_PREDS = frozenset({
  "has target", "has actor", "has instrument", "has direction", "has location",
})

def _add_possessive_have(result):
  """Infer have(Y,E,CT) from paired isa(T,E) + is_rel2(T+" of",E,Y,CT) facts.

  "The car of Mary" produces:
    isa("car", car2)
    is_rel2("car of", car2, Mary, CT)
  but "Mary has a car?" checks have(Mary, sk, CT).  This function bridges the
  gap by emitting have(Mary, car2, CT) whenever the isa type T matches the
  relation prefix (T+" of").

  Context (tense, world, location, knower) for the generated have fact:
  - If the possessed entity E appears as the argument of an activity-role fact
    (has_target, has_actor, has_instrument, etc.) we use that fact's CT.
    This handles "John saw a twig of an elephant" correctly: twig2 is the
    has_target of a past see-event, so have(elephant, twig2, CT_past) is
    emitted rather than a spurious present-tense fact.
  - Otherwise fall back to the CT from the is_rel2 fact itself (correct for
    direct possessives like "The bike of John is blue" with no containing event).

  The isa-type check prevents spurious have for non-possessive relations such
  as is_rel2("afraid of", wolf, mice) — there is no isa("afraid", wolf).

  Only ground (non-variable, non-compound-term) entity arguments are processed.
  New facts are inserted before the first @question entry.
  """
  def _is_ground_str(v):
    return isinstance(v, str) and not v.startswith("?:")

  # Pass 1a: collect isa(T, E) facts for ground T and E.
  isa_types = {}          # entity_str -> set of type_str
  for obj in result:
    if not isinstance(obj, dict) or "@logic" not in obj:
      continue
    clause = obj["@logic"]
    if not (isinstance(clause, list) and clause
            and isinstance(clause[0], str) and clause[0] == "isa"
            and len(clause) >= 3):
      continue
    typ, ent = clause[1], clause[2]
    if _is_ground_str(typ) and _is_ground_str(ent):
      isa_types.setdefault(ent, set()).add(typ)

  # Pass 1b: collect CT of the first activity-role fact mentioning each entity.
  # has_target(act, E, CT) / has_actor(act, E, CT) / has_instrument(act, E, CT) …
  # E is always at argument position 2 (index 2) for these predicates.
  entity_event_ct = {}    # entity_str -> CT from containing activity
  for obj in result:
    if not isinstance(obj, dict) or "@logic" not in obj:
      continue
    clause = obj["@logic"]
    if not (isinstance(clause, list) and clause
            and isinstance(clause[0], str)
            and clause[0] in _ACTIVITY_ROLE_PREDS
            and len(clause) >= 4):
      continue
    ent = clause[2]
    ct  = clause[3] if len(clause) > 3 else None
    if _is_ground_str(ent) and ent not in entity_event_ct and ct is not None:
      entity_event_ct[ent] = ct

  # Pass 2: find is_rel2(R, E, Y, CT_possessive) where R ends in " of" and
  # isa(T, E) exists with T+" of" == R.  Emit have(Y, E, CT_chosen).
  new_facts = []
  seen = set()
  for obj in result:
    if not isinstance(obj, dict) or "@logic" not in obj:
      continue
    clause = obj["@logic"]
    if not (isinstance(clause, list) and clause
            and isinstance(clause[0], str) and clause[0] == "is rel2"
            and len(clause) >= 4):
      continue
    rel, ent, owner = clause[1], clause[2], clause[3]
    ct_possessive = clause[4] if len(clause) > 4 else None
    if not (isinstance(rel, str) and rel.endswith(" of")):
      continue
    if not (_is_ground_str(ent) and _is_ground_str(owner)):
      continue
    expected_type = rel[:-3]    # strip trailing " of"
    if ent not in isa_types or expected_type not in isa_types[ent]:
      continue
    # Prefer the activity-event CT (correct tense) over the possessive CT.
    ct = entity_event_ct.get(ent, ct_possessive)
    have_clause = ["have", owner, ent]
    if ct is not None:
      have_clause.append(list(ct) if isinstance(ct, list) else ct)
    key = (owner, ent)
    if key in seen:
      continue
    seen.add(key)
    new_facts.append({"@name": obj.get("@name", "sent_?"), "@logic": have_clause})

  if not new_facts:
    return
  first_q = next((i for i, o in enumerate(result) if "@question" in o), len(result))
  for i, fact in enumerate(new_facts):
    result.insert(first_q + i, fact)


# ======== degree-predicate stripping (noproptypes_flag) ========

def _strip_degree_predicates(result):
  """Replace degree predicates with their non-gradable equivalents throughout
  the result clause list.  Called from rawlogic_convert when noproptypes_flag
  is True.  Modifies each clause dict in place and returns the same list.

    has degree property(PROP, ENTITY, DEGREE, RELCLASS) -> has property(PROP, ENTITY)
    has degree rel2(REL, E1, E2, DEGREE, RELCLASS)      -> is rel2(REL, E1, E2)

  Handles negated forms ("-has degree property", "-has degree rel2") as well,
  and recurses into nested sub-formulas (e.g. inside $block / $not).
  """
  for obj in result:
    if not isinstance(obj, dict):
      continue
    if "@logic" in obj:
      obj["@logic"] = _strip_deg_frm(obj["@logic"])
    if "@question" in obj:
      obj["@question"] = _strip_deg_frm(obj["@question"])
  return result


def _strip_deg_frm(frm):
  """Recursively strip degree info from one formula or GK clause."""
  if not isinstance(frm, list) or not frm:
    return frm

  first = frm[0]

  # GK clause: first element is itself a list (atom) — recurse into each atom.
  if isinstance(first, list):
    return [_strip_deg_frm(a) for a in frm]

  if not isinstance(first, str):
    return frm

  # Atom whose predicate may carry a "-" negation prefix.
  pred = first
  neg  = pred.startswith("-")
  base = pred[1:] if neg else pred
  pfx  = "-" if neg else ""

  if base == "has degree property" and len(frm) >= 3:
    # [pred, PROP, ENTITY, DEGREE, RELCLASS] -> [simple_pred, PROP, ENTITY]
    return [pfx + "has property", frm[1], frm[2]]

  if base == "has degree rel2" and len(frm) >= 4:
    # [pred, REL, E1, E2, DEGREE, RELCLASS] -> [simple_pred, REL, E1, E2]
    return [pfx + "is rel2", frm[1], frm[2], frm[3]]

  # Any other formula/atom: recurse into sub-elements to catch nested occurrences.
  return [frm[0]] + [_strip_deg_frm(a) if isinstance(a, list) else a
                     for a in frm[1:]]


# =========== the end ==========
