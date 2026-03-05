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

import re
import os as _os

from globals import options as _g_options


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

# Logical connectives that are NOT predicates.
_connectives = {"and", "or", "not", "implies", "equivalent", "xor", "forall", "exists"}

# Opaque wrappers: clausification does not recurse inside these.
# Variable renaming (outer varmap) is still applied to their contents.
_opaque_wrappers = {"normally", "-normally"}

# Counter for Skolem function/constant names (reset per top-level call).
_skolem_nr = 0

# Counter for $defq predicate names (reset per top-level call).
_defq_nr = 0

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

# Spatial prepositions handled by "Where is X?" queries.
_SPATIAL_PREPS = ["in", "on", "at", "near", "above", "under"]

# Stage-2 meta-predicates that indicate a "Where is X?" location query.
_WHERE_META_PREDS = frozenset({"located in", "located at", "located on",
                               "located near", "location", "located"})


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


def rawlogic_convert(logic, s1_json=None):
  """Convert stage-2 LLM output to a GK-compatible clause list.

  Input:  stage-2 list ["and", ["@id","S1",PACKAGE], ...]
          s1_json -- Stage-1 JSON from llmparse.parse_text(), used for
                     programmatic $ctxt injection (tense, world, location).
  Output: list of {"@name":..., "@logic":CLAUSE} / {"@name":..., "@question":F}
  Returns None on fatal error.
  """
  global _skolem_nr, _defq_nr, _fv_nr, _gobj_nr
  _skolem_nr = 0          # reset once for the whole conversion
  _defq_nr   = 0
  _fv_nr     = 0
  _gobj_nr   = 0
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

  # Build population facts by scanning the raw stage-2 input first.
  pop_facts = _populate_clauses(items)

  result = []
  for item in items:
    objs = _convert_id_package(item, asu_index)
    if objs:
      result.extend(objs)

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


# ======== package extraction ========

def _convert_id_package(item, asu_index=None):
  """Process ["@id", sid, PACKAGE] → list of GK clause dicts."""
  if not isinstance(item, list) or len(item) < 3 or item[0] != "@id":
    return []
  sid = item[1]
  package = item[2]
  name = "sent_" + str(sid)

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
      where_atom = _find_where_atom(body, ask_var)
      if where_atom is not None:
        entity = where_atom[2]
        atom_pred = where_atom[1]
        # Use specific prep when query uses a concrete spatial preposition;
        # use all preps for meta-predicates like "located in".
        specific_prep = atom_pred if atom_pred in _WHERE_SPATIAL_PREPS else None
        # When the entity is a stage-2 variable (e.g. "E" from an event),
        # _build_where_question would generate an over-broad biconditional
        # matching ANY event's location.  Instead, use _build_defq_question
        # which preserves all constraints from the original body.
        entity_is_s2var = isinstance(entity, str) and bool(_S2_VAR_RE.match(entity))
        if specific_prep and entity_is_s2var:
          result = _build_defq_question(name, ask_var, body, where_prep=specific_prep)
        else:
          result = _build_where_question(name, entity, ask_var, specific_prep=specific_prep)
        is_where_question = True
      elif _is_simple_question_formula(body):
        # Single atom with ≤1 variable: direct @question, no $defq wrapper.
        free_vars_in_body = sorted(_collect_body_free_vars(body))
        varmap = {ask_var: "?:" + ask_var}
        varmap.update({v: "?:" + v for v in free_vars_in_body})
        flat = _flatten_q_atoms(body, varmap)
        if not flat:
          return []
        q_formula = flat[0] if len(flat) == 1 else [["and"] + flat]
        result = [{"@name": name, "@question": q_formula, "@askvars": 1}]
      else:
        # Complex case: wrap in $defq biconditional.
        # Detect has_location(E, ask_var) → encode "in" as the preposition.
        where_prep = _find_haslocation_prep(body, ask_var)
        result = _build_defq_question(name, ask_var, body, where_prep=where_prep)
        if where_prep:
          is_where_question = True
    else:
      # Yes/no question.
      # When $ctxt is active, always use $defq so the @question atom is the
      # machinery literal ["$defq0"] (no free variables → GK returns plain
      # `true` rather than `$ans(W0,…)` which confuses answer extraction).
      if _is_simple_question_formula(formula) and _g_options.get("nocontext_flag", False):
        # Direct @question only when $ctxt is disabled.
        free_vars_in_formula = sorted(_collect_body_free_vars(formula))
        varmap = {v: "?:" + v for v in free_vars_in_formula}
        flat = _flatten_q_atoms(formula, varmap)
        if not flat:
          return []
        q_formula = flat[0] if len(flat) == 1 else [["and"] + flat]
        result = [{"@name": name, "@question": q_formula}]
      else:
        # Complex formula, or: simple but $ctxt active → $defq biconditional.
        # Fix contradictory ["and", ["not", A], A] that LLM generates for
        # "No X is Y?" questions — simplify to just ["not", A].
        formula = _simplify_contradictory_and(formula)
        result = _build_defq_question(name, None, formula)
  else:
    # Clausify the formula.
    clauses = _clausify(formula)
    result = []
    for clause in clauses:
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
    return atom

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


# ======== clausification ========

# Predicates whose second positional argument (index 2) is an "object" entity
# that the LLM may express as a bare plural type name like "berries" or "carrots".
# These need expansion to a fresh variable + isa constraint so that the prover
# can match them against specific instances.
_GENERIC_OBJ_PREDS = frozenset({
  "has target", "has location", "has direction", "has instrument",
})

# Bare type name: all lowercase letters (no digits, no uppercase, no suffix number).
_BARE_TYPE_RE = re.compile(r'^[a-z][a-z]*$')

# Counter for fresh variables introduced by _expand_generic_objects (module-level).
_gobj_nr = 0

def _singularize(word):
  """Very basic English singularization (plural → singular type name)."""
  if word.endswith("ies") and len(word) > 3:
    return word[:-3] + "y"          # berries→berry, activities→activity
  if word.endswith("ses") and len(word) > 3:
    return word[:-2]                # buses→bus
  if word.endswith("xes") and len(word) > 3:
    return word[:-2]                # foxes→fox
  if word.endswith("ches") and len(word) > 4:
    return word[:-2]                # matches→match
  if word.endswith("shes") and len(word) > 4:
    return word[:-2]                # wishes→wish
  if word.endswith("s") and not word.endswith("ss") and len(word) > 2:
    return word[:-1]                # carrots→carrot, bears→bear
  return word

def _expand_generic_objects(frm):
  """Replace bare plural type names in object positions with fresh vars + isa.

  Transforms ["has target", event, "berries"] into:
    ["exists", "Gobj1", ["and", ["isa", "berry", "Gobj1"],
                                ["has target", event, "Gobj1"]]]

  This allows the prover to unify the generic type name with specific instances
  (e.g. sk0 where isa(berry, sk0)) via the isa constraint.  Recurses into all
  sub-formulas.
  """
  global _gobj_nr
  if not isinstance(frm, list) or not frm:
    return frm
  op = frm[0]
  if op in _GENERIC_OBJ_PREDS and len(frm) >= 3:
    obj = frm[2]
    if isinstance(obj, str) and _BARE_TYPE_RE.match(obj):
      sing = _singularize(obj)
      var  = "Gobj" + str(_gobj_nr)
      _gobj_nr += 1
      rest = [frm[0], frm[1], var] + list(frm[3:])
      return ["exists", var, ["and", ["isa", sing, var], rest]]
  # Recurse into sub-formulas (connectives, quantifiers, wrappers)
  if isinstance(op, str) and op in (_connectives | _opaque_wrappers):
    return [op] + [_expand_generic_objects(el) for el in frm[1:]]
  return frm


def _strip_typical_from_antecedent(frm):
  """Remove ["typical", ...] atoms from conjunctions in implies-antecedents.

  The LLM adds typical(E) to activity descriptions in conditional antecedents
  (e.g. "if X eats berries" → exists E. isa(activity,E) ∧ typical(E) ∧ ...).
  Specific events never carry typical, so the conditional never fires.
  Strip typical from the antecedent only — it's a valid guard in consequents.
  """
  if not isinstance(frm, list) or not frm:
    return frm
  op = frm[0]
  if op == "implies" and len(frm) == 3:
    ant = _drop_typical_conjuncts(frm[1])
    con = _strip_typical_from_antecedent(frm[2])
    return [op, ant, con]
  if op in _connectives or op in _opaque_wrappers:
    return [op] + [_strip_typical_from_antecedent(el) for el in frm[1:]]
  return frm

def _drop_typical_conjuncts(frm):
  """Recursively remove ["typical", ...] atoms from "and" conjunctions.

  Only drops typical when it is one conjunct among others.  A standalone
  ["typical", ...] that is the entire antecedent is left unchanged.
  """
  if not isinstance(frm, list) or not frm:
    return frm
  op = frm[0]
  if op == "and":
    kept = []
    for el in frm[1:]:
      if isinstance(el, list) and el and el[0] == "typical":
        continue      # drop typical conjunct
      kept.append(_drop_typical_conjuncts(el))
    if len(kept) == 1:
      return kept[0]
    if not kept:
      return frm    # nothing left — leave original to avoid empty formula
    return ["and"] + kept
  if op in ("exists", "forall") and len(frm) == 3:
    return [op, frm[1], _drop_typical_conjuncts(frm[2])]
  return frm


def _normalize_type_case(frm):
  """Lowercase the type-name argument in 'isa' atoms throughout a formula.

  The LLM sometimes capitalises type names in certain sentences (e.g. "Baby bird"
  from "Baby birds do not fly") while lowercasing them in others ("baby bird"
  from "John is a baby bird").  Normalising to lowercase ensures consistent
  unification inside the prover.
  Only the CLASS argument (frm[1]) of an 'isa' or '-isa' atom is lowercased;
  entity constants (frm[2]) keep their original casing.
  """
  if not isinstance(frm, list) or not frm:
    return frm
  op = frm[0]
  if op in ("isa", "-isa") and len(frm) >= 2 and isinstance(frm[1], str):
    return [op, frm[1].lower()] + [_normalize_type_case(a) for a in frm[2:]]
  if isinstance(op, str):
    return [op] + [_normalize_type_case(el) for el in frm[1:]]
  return frm


def _normalize_quantifiers(frm):
  """Normalize multi-body quantifiers into standard 3-element form.

  LLMs sometimes generate ["exists","X",f1,f2,...] without an explicit "and"
  wrapper.  Convert these to ["exists","X",["and",f1,f2,...]] so the rest of
  the pipeline can assume the standard 3-element ["exists", var, body] form.
  """
  if not isinstance(frm, list) or not frm:
    return frm
  op = frm[0]
  if op in ("exists", "forall"):
    if len(frm) > 3:
      body = ["and"] + [_normalize_quantifiers(f) for f in frm[2:]]
      return [op, frm[1], body]
    if len(frm) == 3:
      return [op, frm[1], _normalize_quantifiers(frm[2])]
    return frm
  if op in _connectives:
    return [op] + [_normalize_quantifiers(el) for el in frm[1:]]
  return frm


def _clausify(formula):
  """Convert a formula to a list of GK clauses (CNF).

  Returns a list of clauses, where each clause is either:
    - a single atom: ["pred", arg, ...]
    - a list of atoms (disjunction): [["pred1",...], ["pred2",...], ...]
  """
  # Normalise type-name casing in isa/−isa atoms (LLM may capitalise inconsistently).
  fn = _normalize_type_case(formula)
  # Strip typical() from implies-antecedents (LLM adds it even in conditionals
  # where it shouldn't be required, causing rules to miss specific events).
  fa = _strip_typical_from_antecedent(fn)
  # Expand bare plural type names in object positions to fresh vars + isa.
  fe = _expand_generic_objects(fa)
  f0 = _normalize_quantifiers(fe)
  f1 = _implies_to_or(f0)
  f2 = _push_neg(f1, True)
  # Pass 1: push normally(...) inside exists/and until it wraps a single atom.
  f3 = _expand_normally(f2)
  f4 = _skolemize(f3, [], {})
  f5 = _distribute(f4)
  # Pass 2: expand normally(atom) -> $block now that clauses are flat and
  # Skolem terms have replaced existential variables.
  f6 = _expand_normally(f5)
  return _extract_clauses(f6)


def _implies_to_or(frm):
  """Eliminate non-primitive connectives, recursively.

  Transformations applied (does not recurse inside opaque wrappers):
    implies(A,B)    -> or(not(A), B)
    equivalent(A,B) -> and(implies(A,B), implies(B,A))  then recurse
    xor(A,B)        -> and(or(A,B), or(not(A),not(B)))
  """
  if not isinstance(frm, list) or not frm:
    return frm
  op = frm[0]

  if op in _opaque_wrappers:
    return frm  # opaque: keep as-is

  if op == "implies":
    if len(frm) == 3:
      a = _implies_to_or(frm[1])
      b = _implies_to_or(frm[2])
      return ["or", ["not", a], b]
    return frm

  if op == "equivalent":
    # equivalent(A,B) = (A=>B) and (B=>A); expand then recurse so implies gets eliminated too
    if len(frm) == 3:
      a = frm[1]
      b = frm[2]
      return _implies_to_or(["and", ["implies", a, b], ["implies", b, a]])
    return frm

  if op == "xor":
    # xor(A,B) = (A or B) and (not(A) or not(B))
    if len(frm) == 3:
      a = _implies_to_or(frm[1])
      b = _implies_to_or(frm[2])
      return ["and", ["or", a, b], ["or", ["not", a], ["not", b]]]
    return frm

  if op in ("and", "or", "not"):
    return [op] + [_implies_to_or(el) for el in frm[1:]]

  if op in ("forall", "exists"):
    # frm[1] is the variable name (string), frm[2] is the body
    return [op, frm[1], _implies_to_or(frm[2])]

  # Atomic formula — no subformulas
  return frm


def _push_neg(frm, pos):
  """Push negation inside to reach NNF.
  pos=True means the current context is positive (no enclosing negation).
  'normally' and similar wrappers are treated as opaque atoms.
  """
  if not isinstance(frm, list) or not frm:
    return frm
  op = frm[0]

  if op in _opaque_wrappers:
    # Negate the wrapper name if needed, but don't recurse inside.
    if not pos:
      neg_op = op[1:] if op.startswith("-") else "-" + op
      return [neg_op] + frm[1:]
    return frm

  if op in ("forall", "exists"):
    new_op = op
    if not pos:
      new_op = "exists" if op == "forall" else "forall"
    return [new_op, frm[1], _push_neg(frm[2], pos)]

  if op in ("and", "or"):
    new_op = op
    if not pos:
      new_op = "or" if op == "and" else "and"
    return [new_op] + [_push_neg(el, pos) for el in frm[1:]]

  if op == "not":
    return _push_neg(frm[1], not pos)

  # Atomic formula
  if pos:
    return frm
  # Negate by toggling "-" prefix on predicate name
  pred = op
  if isinstance(pred, str):
    if pred.startswith("-"):
      return [pred[1:]] + frm[1:]
    else:
      return ["-" + pred] + frm[1:]
  return frm


def _push_normally_inside(frm):
  """Push normally inward through exists/and until it wraps a single atom.

  Called from _expand_normally (pass 1) when normally wraps a complex body.

    normally(exists var, body) -> exists var, _push_normally_inside(body)
    normally(and(A1,...,An))   -> and(A1,...,An-1, normally(An))
    normally(atom)             -> normally(atom)  [base case]

  The result is passed to _skolemize, which eliminates the exists and
  substitutes Skolem terms.  The remaining normally(atom) wrappers are
  then expanded into $block clauses by _expand_normally pass 2.
  """
  if not isinstance(frm, list) or not frm:
    return ["normally", frm]
  op = frm[0]
  if op == "exists":
    return ["exists", frm[1], _push_normally_inside(frm[2])]
  if op == "and":
    if len(frm) > 2:
      # and(A1,...,An) -> and(A1,...,An-1, normally(An))
      return ["and"] + list(frm[1:-1]) + [["normally", frm[-1]]]
    if len(frm) == 2:
      # and(A1) -> normally(A1)
      return ["normally", frm[1]]
  # Atom or other: wrap with normally
  return ["normally", frm]


def _expand_normally(frm):
  """Expand normally(...) wrappers into defeasible clauses with $block atoms.

  Called twice in _clausify:
    Pass 1 (before _skolemize): pushes normally inside complex bodies
      (exists / and) so that after Skolemization each normally wraps a
      single concrete atom.
    Pass 2 (after _distribute): expands normally(atom) into $block clauses.

  The body inside normally is still in raw stage-2 form (not NNF) when
  encountered in pass 1, so _implies_to_or and _push_neg are applied first.

  If options["noexceptions_flag"] is True, strips normally without blockers.

  For each clause (or-disjunction) that contains normally(atom):
    - Classifies literals: negative conditions (start with "-") vs positive heads.
    - Uses the last positive literal as the head (the conclusion to be blocked).
    - Builds priority ["$", CLASS, N] where CLASS is the class from the last
      -isa condition (or "$generic"), and N = len(non-isa conditions) + 1.
    - Returns the clause with ["$block", priority, ["$not", head]] appended.

  A lone normally(body) not inside an or is normalised to a 1-element
  disjunction before processing.
  """
  if not isinstance(frm, list) or not frm:
    return frm
  op = frm[0]

  if op == "and":
    return ["and"] + [_expand_normally(el) for el in frm[1:]]

  if op in ("forall", "exists"):
    return [op, frm[1], _expand_normally(frm[2])]

  if op in _opaque_wrappers or op == "or":
    # Normalise: a lone normally(...) is treated as a one-element disjunction.
    elements = [frm] if op in _opaque_wrappers else frm[1:]

    # Separate normally-wrappers from regular literals.
    regular_lits = []
    pushed_lits  = []  # from _push_normally_inside; must NOT be re-expanded here
    body_lits    = []  # literals extracted from normally-body formulas

    for el in elements:
      if isinstance(el, list) and el and el[0] in _opaque_wrappers:
        body = el[1] if len(el) >= 2 else None
        if body is None:
          continue
        is_pos = not el[0].startswith("-")
        # Process body: implies elimination then NNF push.
        processed = _push_neg(_implies_to_or(body), is_pos)
        # Flatten processed body into a flat list of literals.
        # _push_neg may produce nested ors (e.g. from de Morgan on conjunctive
        # conditions), so flatten one level before collecting.
        if isinstance(processed, list) and processed and processed[0] == "or":
          for lit in processed[1:]:
            if isinstance(lit, list) and lit and lit[0] == "or":
              body_lits.extend(lit[1:])   # one-level flatten of nested or
            else:
              body_lits.append(lit)
        elif isinstance(processed, list) and processed and processed[0] in ("and", "exists"):
          # Complex body (conjunction or existential): push normally inward so
          # that after Skolemization it wraps a single atom (pass 2 handles it).
          # Use pushed_lits (not regular_lits) to prevent pass-1 re-expansion of
          # the normally(atom) we just placed deep inside — it has no outer -isa
          # context yet and would generate a $block with wrong priority.
          if is_pos:
            pushed_lits.append(_push_normally_inside(processed))
          else:
            # -normally with complex body: expand as certain (negated).
            regular_lits.append(_expand_normally(processed))
        elif isinstance(processed, list) and processed:
          body_lits.append(processed)
        # else: empty body — skip
      else:
        regular_lits.append(el)

    # Recurse into regular literals (may contain nested normally, and/or, …).
    # pushed_lits are intentionally excluded from this recursion.
    regular_lits = [_expand_normally(el) for el in regular_lits]

    all_lits = regular_lits + pushed_lits + body_lits
    if not all_lits:
      return frm

    # If no normally bodies were extracted (all were complex conjunctions or
    # pushed inside exists/and for pass 2), return as a plain or-clause.
    if not body_lits:
      if len(all_lits) == 1:
        return all_lits[0]
      return ["or"] + all_lits

    # Check noexceptions flag: treat normally as certain, no $block.
    if _g_options.get("noexceptions_flag", False):
      if len(all_lits) == 1:
        return all_lits[0]
      return ["or"] + all_lits

    # Classify literals: negative conditions vs positive heads.
    neg_lits = [l for l in all_lits
                if isinstance(l, list) and l and
                isinstance(l[0], str) and l[0].startswith("-")]
    pos_lits = [l for l in all_lits
                if not (isinstance(l, list) and l and
                        isinstance(l[0], str) and l[0].startswith("-"))]

    if not pos_lits:
      # No positive head found: cannot create a blocker; treat as certain.
      if len(all_lits) == 1:
        return all_lits[0]
      return ["or"] + all_lits

    # Use the last positive literal as the head (the conclusion to be blocked).
    head     = pos_lits[-1]
    other_pos = pos_lits[:-1]

    # Compute priority: [$, CLASS, N]
    #   CLASS = class from the last -isa condition, or "$generic" if none.
    #   N     = (number of non-isa negative conditions) + 1.
    isa_conds   = [l for l in neg_lits if l[0] == "-isa"]
    non_isa_neg = [l for l in neg_lits if l[0] != "-isa"]
    priornr = len(non_isa_neg) + 1
    if isa_conds and len(isa_conds[-1]) >= 2:
      cls = str(isa_conds[-1][1])
    else:
      cls = "$generic"
    priority = ["$", cls, priornr]
    blocker  = ["$block", priority, ["$not", head]]

    result_lits = neg_lits + other_pos + [head, blocker]
    if len(result_lits) == 1:
      return result_lits[0]
    return ["or"] + result_lits

  # Atomic formula — no expansion needed.
  return frm


def _skolemize(frm, freevars, varmap):
  """Skolemize existential quantifiers; rename forall vars to ?:VAR.

  freevars: list of current free (universally quantified) ?:X variable names
  varmap:   dict mapping stage-2 var names (e.g. "X") to GK forms ("?:X")

  After skolemization, forall quantifiers are eliminated (var renamed to ?:X,
  quantifier wrapper dropped). Exists quantifiers are eliminated by
  substituting the variable with a Skolem constant or function.
  """
  if not isinstance(frm, list) or not frm:
    return frm
  op = frm[0]

  if op in _opaque_wrappers:
    # Keep opaque wrapper but apply outer varmap to rename outer vars inside.
    return _apply_varmap(frm, varmap)

  if op == "forall":
    var = frm[1]
    body = frm[2]
    gk_var = "?:" + var
    new_varmap = dict(varmap)
    new_varmap[var] = gk_var
    new_freevars = freevars + [gk_var]
    # Drop the quantifier — the renamed free var is implicitly universally quantified in GK
    return _skolemize(body, new_freevars, new_varmap)

  if op == "exists":
    var = frm[1]
    body = frm[2]
    skolem = _make_skolem(freevars)
    new_varmap = dict(varmap)
    new_varmap[var] = skolem
    return _skolemize(body, freevars, new_varmap)

  if op in ("and", "or", "not"):
    return [op] + [_skolemize(el, freevars, varmap) for el in frm[1:]]

  # Atomic formula: apply varmap to rename any stage-2 vars in arguments
  return _apply_varmap(frm, varmap)


def _make_skolem(freevars):
  """Create a Skolem constant (no free vars) or function (with free vars)."""
  global _skolem_nr
  name = "sk" + str(_skolem_nr)
  _skolem_nr += 1
  if freevars:
    return [name] + freevars
  return name


def _apply_varmap(frm, varmap):
  """Recursively substitute stage-2 variable names in frm using varmap."""
  if isinstance(frm, str):
    return varmap.get(frm, frm)
  if not isinstance(frm, list):
    return frm
  return [_apply_varmap(el, varmap) for el in frm]


def _distribute(frm):
  """Distribute OR over AND (CNF transformation).
  Input must be in NNF with no quantifiers (after _skolemize).
  Opaque wrappers are treated as atoms.
  """
  if not isinstance(frm, list) or not frm:
    return frm
  op = frm[0]

  if op in _opaque_wrappers:
    return frm  # opaque atom

  if op == "and":
    # Distribute each child and flatten any nested ANDs that result.
    result = []
    for el in frm[1:]:
      d = _distribute(el)
      if isinstance(d, list) and d and d[0] == "and":
        result.extend(d[1:])
      else:
        result.append(d)
    return ["and"] + result

  if op == "or":
    # Recursively distribute each sub-formula first
    parts = [_distribute(el) for el in frm[1:]]

    # Flatten nested "or"s into a single disjunction
    flat = []
    for p in parts:
      if isinstance(p, list) and p and p[0] == "or":
        flat.extend(p[1:])
      else:
        flat.append(p)

    # Check if any element is an "and" (requires distribution)
    has_and = any(isinstance(p, list) and p and p[0] == "and" for p in flat)
    if not has_and:
      if len(flat) == 1:
        return flat[0]
      return ["or"] + flat

    # Build groups: each "and" element contributes its children; others wrap in [...]
    groups = []
    for p in flat:
      if isinstance(p, list) and p and p[0] == "and":
        groups.append(p[1:])
      else:
        groups.append([p])

    # Cartesian product of groups (each combo is one clause)
    combos = _cartesian(groups)
    if len(combos) == 1:
      combo = combos[0]
      return combo[0] if len(combo) == 1 else ["or"] + combo

    clauses = []
    for combo in combos:
      clauses.append(combo[0] if len(combo) == 1 else ["or"] + combo)
    return ["and"] + clauses

  # Atomic
  return frm


def _cartesian(groups):
  """Compute cartesian product of groups (list of lists)."""
  result = [[]]
  for group in groups:
    new_result = []
    for existing in result:
      for item in group:
        new_result.append(existing + [item])
    result = new_result
  return result


def _extract_clauses(frm):
  """Extract a flat list of GK clauses from a CNF formula.

  A GK clause is:
    - single atom:  ["pred", arg, ...]           (a plain list)
    - disjunction:  [["pred1",...], ["pred2",...]] (list of lists)

  The input is in CNF (output of _distribute), so:
    - top-level "and": each child is a separate clause
    - top-level "or":  its children are atoms, forming one multi-literal clause
    - anything else:   one single-literal clause
  """
  if not isinstance(frm, list) or not frm:
    return []
  op = frm[0]

  if op == "and":
    clauses = []
    for el in frm[1:]:
      clauses.extend(_extract_clauses(el))
    return clauses

  if op == "or":
    # Each child should be an atom at this point
    atoms = frm[1:]
    return [atoms]  # one clause = list of atom-lists

  # Single atom (predicate or opaque wrapper)
  return [frm]


# ======== $defq question wrapping ========

def _simplify_contradictory_and(frm):
  """Simplify ["and", ["not", A], A] to ["not", A].

  The LLM sometimes generates such a contradictory conjunction for yes/no
  questions that ask about a universally-negative statement (e.g. "No elephant
  is an animal?" → ["and", ["not", exists-elephant-animal], exists-elephant-animal]).
  In that case the correct question formula is just the negative part ["not", A].

  Only the pattern NOT-first is simplified.  The pattern A-first (["and", A, ["not", A]])
  is left unchanged because in that case the original self-contradictory formula
  happens to let the prover return the correct answer (e.g. False for
  "John is not defeated?" when John IS defeated).
  """
  if not (isinstance(frm, list) and len(frm) == 3 and frm[0] == "and"):
    return frm
  a, b = frm[1], frm[2]
  # Pattern: ["not", X] and X  (negation comes first)
  if isinstance(a, list) and a and a[0] == "not" and len(a) == 2 and a[1] == b:
    return a
  return frm


def _is_simple_question_formula(frm):
  """Return True if frm is a single positive atom with at most 1 distinct variable.

  Simple questions are handled with a direct @question entry (no $defq wrapper).
  Complex questions (multiple atoms, 2+ variables, or nested connectives) need
  the $defq biconditional approach so the prover has richer resolution paths.

  Examples:
    ["isa", "animal", "John 1"]  -> True  (0 variables)
    ["isa", "animal", "X"]       -> True  (1 variable)
    ["have", "X", "Y"]           -> False (2 variables)
    ["and", ...]                 -> False (connective, not a single atom)
    ["forall", "X", ...]         -> False (quantifier, not a single atom)
  """
  if not isinstance(frm, list) or not frm:
    return False
  pred = frm[0]
  if not isinstance(pred, str) or pred in _connectives or pred.startswith("-"):
    return False
  for arg in frm[1:]:
    if isinstance(arg, list):
      return False              # nested structure -> not a flat atom
  vars_seen = set()
  for arg in frm[1:]:
    if isinstance(arg, str) and _looks_like_var(arg):
      vars_seen.add(arg)
  return len(vars_seen) <= 1


def _looks_like_var(s):
  """Return True if s looks like a stage-2 variable name (e.g. X, Y, S1).

  Variables in stage-2 LLM output are a single uppercase letter optionally
  followed by digits: X, Y, Z, E, S, W, S1, S2, X1, W0.  Strings starting
  with '?:' are already in GK format and also count as variables.

  Multi-letter capitalized words (English, French, German, Buddhist …) are
  proper-noun constants, not variables, and must NOT match.
  """
  if not isinstance(s, str) or ' ' in s:
    return False
  if s.startswith('?:'):
    return True
  return bool(re.match(r'^[A-Z][0-9]*$', s))


def _collect_body_free_vars(frm, bound=None):
  """Collect free variable names appearing in a stage-2 formula.

  Returns a set of plain variable names (e.g. {"Y", "Z"}) that:
    - appear as atom arguments
    - look like variable names (see _looks_like_var)
    - are NOT bound by any forall/exists quantifier in frm
    - are NOT in the initial 'bound' set

  Used to find the non-ask free variables that must be wrapped in 'exists'
  before constructing the $defq biconditional.
  """
  if bound is None:
    bound = frozenset()
  if not isinstance(frm, list) or not frm:
    return set()
  op = frm[0]
  if op in ("forall", "exists"):
    var = str(frm[1])
    return _collect_body_free_vars(frm[2], bound | {var})
  if op in _connectives:
    result = set()
    for el in frm[1:]:
      result |= _collect_body_free_vars(el, bound)
    return result
  # Atom: frm[0] is the predicate, frm[1:] are arguments.
  result = set()
  for arg in frm[1:]:
    if isinstance(arg, str) and _looks_like_var(arg) and arg not in bound:
      result.add(arg)
    elif isinstance(arg, list):
      result |= _collect_body_free_vars(arg, bound)
  return result


def _find_haslocation_prep(body, ask_var):
  """Return "in" if body contains ["has location", event_var, ask_var], else None.

  Searches recursively through "and"/"exists"/"forall" wrappers.
  Used to detect activity-location queries like "Where did John eat candy?"
  where stage-2 encodes the location as has_location(E, X) with X as the
  ask variable.  The implied preposition is always "in".
  """
  if not isinstance(body, list) or not body:
    return None
  if body[0] == "has location" and len(body) == 3 and body[2] == ask_var:
    return "in"
  if body[0] == "and":
    for item in body[1:]:
      found = _find_haslocation_prep(item, ask_var)
      if found is not None:
        return found
  if body[0] in ("exists", "forall") and len(body) >= 3:
    return _find_haslocation_prep(body[2], ask_var)
  return None


def _build_defq_question(name, ask_var, body, where_prep=None):
  """Build $defq biconditional @logic clauses and a @question entry.

  For a wh-question (ask_var is not None, e.g. "X"):
    Constructs:  forall X. ($defq0(X) <=> exists Ys. body)
    Emits:       @logic clauses (with @sourcetype:"question") from the CNF
                 @question: [$defq0, ?:X]  with @askvars: 1

  For a yes/no question (ask_var is None):
    Constructs:  $defq0() <=> body
    Emits:       @logic clauses (with @sourcetype:"question") from the CNF
                 @question: [$defq0]

  where_prep: if set (e.g. "in"), the $defq atom becomes 2-arg [$defqN, prep, X]
    so that the answer includes the preposition.  Sets @askvars:2 and
    @where_query:True.  Used for has_location activity-location queries.

  Non-ask free variables in body are automatically wrapped in 'exists' so
  the clausification handles them correctly (Skolem functions of ask_var).
  """
  global _defq_nr
  defq_name = "$defq" + str(_defq_nr)
  _defq_nr += 1

  # Wrap body in 'exists' for every free variable that is not the ask variable.
  initial_bound = {ask_var} if ask_var else set()
  free_vars = sorted(_collect_body_free_vars(body, bound=initial_bound))
  wrapped_body = body
  for fv in free_vars:
    wrapped_body = ["exists", fv, wrapped_body]

  # Build the biconditional formula.
  if ask_var:
    if where_prep:
      # 2-arg $defq: [$defqN, "in", X] — encodes the preposition in the answer.
      defq_atom = [defq_name, where_prep, ask_var]
      q_atom    = [defq_name, "?:Rel", "?:" + ask_var]
      askvars   = 2
    else:
      defq_atom = [defq_name, ask_var]
      q_atom    = [defq_name, "?:" + ask_var]
      askvars   = 1
    frm = ["forall", ask_var, ["equivalent", defq_atom, wrapped_body]]
  else:
    defq_atom = [defq_name]
    frm = ["equivalent", defq_atom, wrapped_body]
    q_atom = [defq_name]
    askvars = None

  # Clausify using the existing CNF machinery (handles forall/exists/equivalent).
  clauses = _clausify(frm)

  # Each clause gets @sourcetype:"question" to mark it as question-derived.
  result = []
  for clause in clauses:
    result.append({"@name": name, "@sourcetype": "question", "@logic": clause})

  # The @question entry itself does not carry @sourcetype.
  q_obj = {"@name": name, "@question": q_atom}
  if askvars is not None:
    q_obj["@askvars"] = askvars
  if where_prep:
    q_obj["@where_query"] = True
  result.append(q_obj)
  return result


_WHERE_SPATIAL_PREPS = frozenset(_SPATIAL_PREPS)


def _find_where_atom(body, ask_var):
  """Find and return a where-query atom within body, or None.

  Matches atoms of the form  ["is rel2", pred, entity, ask_var]  where:
    - pred is a meta-predicate (e.g. "located in") in _WHERE_META_PREDS, OR
    - pred is a concrete spatial preposition (e.g. "near") in _WHERE_SPATIAL_PREPS
  In either case the ask_var must appear as the LAST positional argument
  (position 3), making it the location being queried.

  Handles forms:
    Simple:      ["is rel2", pred, entity, ask_var]
    Compound:    ["and", ..., <matching atom>, ...]
    Existential: ["exists", var, <body>]
  Returns the matching atom list if found, else None.
  """
  if not isinstance(body, list) or not body:
    return None
  if (body[0] == "is rel2" and len(body) == 4 and body[3] == ask_var
      and body[1] in (_WHERE_META_PREDS | _WHERE_SPATIAL_PREPS)):
    return body
  if body[0] == "and":
    for item in body[1:]:
      found = _find_where_atom(item, ask_var)
      if found is not None:
        return found
  if body[0] in ("exists", "forall") and len(body) >= 3:
    return _find_where_atom(body[2], ask_var)
  return None


def _is_where_body(body, ask_var):
  """Return True if body contains a 'Where is X?' pattern."""
  return _find_where_atom(body, ask_var) is not None


_S2_VAR_RE = re.compile(r'^[A-Z][A-Za-z0-9]*$')


def _s2var_to_gk(name_str):
  """Convert a stage-2 variable name like 'Y' to a GK variable '?:Y'.

  Stage-2 variables are uppercase-initial identifiers (X, Y, Entity, ...).
  Constants (John 1, box 1, etc.) contain spaces or start lowercase.
  If already a GK variable (starts with "?:"), returned unchanged.
  """
  if isinstance(name_str, str):
    if name_str.startswith("?:"):
      return name_str
    if _S2_VAR_RE.match(name_str):
      return "?:" + name_str
  return name_str


def _build_where_question(name, entity, ask_var, specific_prep=None):
  """Build biconditional @logic clauses and @question entry for 'Where is X?'.

  For each preposition p in the applicable set, generates two CNF clauses:
    Forward:  ["-is rel2", p, entity_gk, "?:Q1"], [$defqN, p, "?:Q1"]
    Backward: ["-" + defqN, p, "?:Q1"],            ["is rel2", p, entity_gk, "?:Q1"]

  entity may be a stage-2 variable name (e.g. "Y") — it is converted to a GK
  variable ("?:Y") so the biconditional matches any entity's location.

  If specific_prep is given (e.g. "near"), only that preposition is used;
  otherwise all _SPATIAL_PREPS are used (for meta-predicate queries like "located in").

  The @question is [$defqN, ?:Rel, ?:Q1] with @askvars=2 and @where_query=True.
  $ctxt is injected into "is rel2" atoms automatically by _inject_ctxt_into_objs.
  """
  global _defq_nr
  defq_name = "$defq" + str(_defq_nr)
  _defq_nr += 1

  entity_gk = _s2var_to_gk(entity)
  preps = [specific_prep] if specific_prep else _SPATIAL_PREPS

  result = []
  for prep in preps:
    # Forward: is_rel2(prep, entity_gk, Q1) => defqN(prep, Q1)
    fwd = [["-is rel2", prep, entity_gk, "?:Q1"], [defq_name, prep, "?:Q1"]]
    result.append({"@name": name, "@sourcetype": "question", "@logic": fwd})
    # Backward: defqN(prep, Q1) => is_rel2(prep, entity_gk, Q1)
    bwd = [["-" + defq_name, prep, "?:Q1"], ["is rel2", prep, entity_gk, "?:Q1"]]
    result.append({"@name": name, "@sourcetype": "question", "@logic": bwd})

  q_atom = [defq_name, "?:Rel", "?:Q1"]
  q_obj = {"@name": name, "@question": q_atom, "@askvars": 2, "@where_query": True}
  result.append(q_obj)
  return result


# ======== population fact injection ========

def _norm_for_const(s):
  """Normalise a class/property name for use in a $some_* constant name.
  Spaces become underscores; other characters kept as-is.
  """
  return str(s).replace(" ", "_")


def _is_ground_term(term):
  """Return True if term is a ground constant (not a variable or term with vars).

  Strings that look like variables (uppercase-initial no-space identifiers, or
  ?:-prefixed GK variables) are not ground.  Lists (Skolem function terms) are
  not ground.  All other strings are treated as ground constants.
  """
  return isinstance(term, str) and not _looks_like_var(term)


def _scan_item_formula(frm, name, polarity, classes, has_props, deg_props):
  """Recursively scan a formula for isa / has-property / has-degree-property atoms.

  Works on both raw stage-2 formulas (connectives and/or/not/forall/exists/
  implies/equivalent/xor/ask) and clausified GK clause lists (disjunctions
  represented as a list whose first element is itself a list).

  Arguments:
    frm       -- formula or clause to scan
    name      -- sent_SN name to record on first occurrence
    polarity  -- True = positive context, False = negative context
    classes   -- dict: CLASS -> {"name", "has_pos", "has_neg"}
    has_props -- dict: PROPERTY -> {"name", "has_pos", "has_neg"}
    deg_props -- dict: (PROPERTY, RELCLASS) -> {"name", "has_pos", "has_neg"}
  """
  if not isinstance(frm, list) or not frm:
    return
  first = frm[0]

  # Clausified disjunction: first element is itself a list (atom).
  if isinstance(first, list):
    for atom in frm:
      _scan_item_formula(atom, name, polarity, classes, has_props, deg_props)
    return

  pred = first

  # Structural connectives — recurse, tracking polarity.
  if pred in ("and", "or", "implies", "equivalent", "xor"):
    for el in frm[1:]:
      _scan_item_formula(el, name, polarity, classes, has_props, deg_props)
    return
  if pred == "not":
    if len(frm) >= 2:
      _scan_item_formula(frm[1], name, not polarity, classes, has_props, deg_props)
    return
  if pred in ("forall", "exists"):
    if len(frm) >= 3:
      _scan_item_formula(frm[2], name, polarity, classes, has_props, deg_props)
    return
  # ["ask", var, body] — scan the body.
  if pred == "ask":
    if len(frm) >= 3:
      _scan_item_formula(frm[2], name, polarity, classes, has_props, deg_props)
    return
  # Transparent wrappers — recurse into the formula argument.
  if pred == "normally" or pred == "question":
    if len(frm) >= 2:
      _scan_item_formula(frm[1], name, polarity, classes, has_props, deg_props)
    return
  if pred == "holds":
    if len(frm) >= 3:
      _scan_item_formula(frm[2], name, polarity, classes, has_props, deg_props)
    return

  # Atom (may carry a "-" negation prefix on the predicate name).
  if isinstance(pred, str) and pred.startswith("-"):
    actual_pred = pred[1:]
    atom_pol    = not polarity
  else:
    actual_pred = pred
    atom_pol    = polarity

  args = frm[1:]

  if actual_pred == "isa" and len(args) >= 2:
    cls    = str(args[0])
    entity = args[1]
    if cls not in classes:
      classes[cls] = {"name": name, "has_pos": False, "has_neg": False}
    if _is_ground_term(entity):
      if atom_pol:
        classes[cls]["has_pos"] = True
      else:
        classes[cls]["has_neg"] = True

  elif actual_pred == "has property" and len(args) >= 2:
    prop   = str(args[0])
    entity = args[1]
    if prop not in has_props:
      has_props[prop] = {"name": name, "has_pos": False, "has_neg": False}
    if _is_ground_term(entity):
      if atom_pol:
        has_props[prop]["has_pos"] = True
      else:
        has_props[prop]["has_neg"] = True

  elif actual_pred == "has degree property" and len(args) >= 4:
    prop     = str(args[0])
    entity   = args[1]
    relclass = args[3]
    # Only include when RELCLASS is a constant (not a variable).
    if isinstance(relclass, str) and not _looks_like_var(relclass):
      key = (prop, relclass)
      if key not in deg_props:
        deg_props[key] = {"name": name, "has_pos": False, "has_neg": False}
      if _is_ground_term(entity):
        if atom_pol:
          deg_props[key]["has_pos"] = True
        else:
          deg_props[key]["has_neg"] = True


def _build_population_facts(classes, has_props, deg_props):
  """Build the list of @logic population entries from collected scan data.

  For each key, emits a positive and/or negative synthetic clause, skipping
  whichever polarity is already covered by an existing ground constant.
  Every entry carries @sourcetype:"populate".
  """
  result = []

  for cls, info in classes.items():
    name = info["name"]
    cn   = _norm_for_const(cls)
    if not info["has_pos"]:
      result.append({"@name": name, "@sourcetype": "populate",
                     "@logic": ["isa", cls, "$some_" + cn]})
    if not info["has_neg"]:
      result.append({"@name": name, "@sourcetype": "populate",
                     "@logic": ["-isa", cls, "$some_not_" + cn]})

  for prop, info in has_props.items():
    name = info["name"]
    cn   = _norm_for_const(prop)
    if not info["has_pos"]:
      result.append({"@name": name, "@sourcetype": "populate",
                     "@logic": ["has property", prop, "$some_" + cn]})
    if not info["has_neg"]:
      result.append({"@name": name, "@sourcetype": "populate",
                     "@logic": ["-has property", prop, "$some_not_" + cn]})

  for (prop, relclass), info in deg_props.items():
    name = info["name"]
    cn   = _norm_for_const(prop) + "_" + _norm_for_const(relclass)
    if not info["has_pos"]:
      result.append({"@name": name, "@sourcetype": "populate",
                     "@logic": ["has degree property", prop, "$some_" + cn,
                                "none", relclass]})
    if not info["has_neg"]:
      result.append({"@name": name, "@sourcetype": "populate",
                     "@logic": ["-has degree property", prop, "$some_not_" + cn,
                                "none", relclass]})

  return result


def _populate_clauses(items):
  """Scan all @id items in the raw stage-2 input and return population entries.

  This is the main entry point called from rawlogic_convert.  The underlying
  scanner (_scan_item_formula) handles both raw stage-2 and clausified forms,
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
      _scan_item_formula(formula, name, True, classes, has_props, deg_props)

  return _build_population_facts(classes, has_props, deg_props)


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

  Scans assertional @logic clauses (not question-derived, not populate) for
  ground isa(CLASS, CONST) facts to build a CONST -> {CLASS, ...} map.

  Then, for every degree-predicate atom in @question or @sourcetype:question
  @logic entries: if
    - the ENTITY argument is a known ground constant, AND
    - RELCLASS is not among that constant's established isa classes, AND
    - the constant has exactly one established isa class
  then RELCLASS is replaced with that single known class.

  Modifies result in place.
  """
  # --- 1. build const_classes from assertional @logic entries ---
  const_classes = {}   # CONST -> set of CLASS strings

  for obj in result:
    if not isinstance(obj, dict):
      continue
    src = obj.get("@sourcetype")
    if src in ("question", "populate"):
      continue
    if "@logic" not in obj:
      continue
    clause = obj["@logic"]
    # Single atom: ["isa", CLASS, CONST]
    if (isinstance(clause, list) and len(clause) >= 3 and
        isinstance(clause[0], str) and clause[0] == "isa" and
        _is_ground_term(clause[2])):
      const_classes.setdefault(clause[2], set()).add(str(clause[1]))
    # Disjunctive clause: list of atom-lists (ground isa rarely here, but scan anyway)
    elif isinstance(clause, list) and clause and isinstance(clause[0], list):
      for atom in clause:
        if (isinstance(atom, list) and len(atom) >= 3 and
            isinstance(atom[0], str) and atom[0] == "isa" and
            _is_ground_term(atom[2])):
          const_classes.setdefault(atom[2], set()).add(str(atom[1]))

  if not const_classes:
    return

  # --- 2. apply coercion to question entries ---
  for obj in result:
    if not isinstance(obj, dict):
      continue
    if "@question" in obj:
      obj["@question"] = _coerce_atom(obj["@question"], const_classes, is_question=True)
    if "@logic" in obj and obj.get("@sourcetype") == "question":
      obj["@logic"] = _coerce_clause(obj["@logic"], const_classes, is_question=True)


def _coerce_atom(atom, const_classes, is_question=False):
  """Recursively substitute RELCLASS in degree-predicate atoms.

  Handles both raw question formulas (with connectives and quantifiers)
  and flat GK clause atoms.

  is_question: when True (processing @question or @sourcetype:question entries),
    the RELCLASS in "has degree rel2" atoms is always replaced with a fresh free
    variable so the question unifies with any rule regardless of its RELCLASS.
    (E.g. "cat" from Emily's type vs "animal" from the generic rule both unify
    with a free variable.)  For "has degree property" the original mismatch-based
    coercion is preserved.
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
      # For "has degree rel2" in questions: always use a free variable for
      # RELCLASS so the question matches any rule regardless of its RELCLASS.
      if is_question and base == "has degree rel2" and isinstance(relclass, str):
        new_atom = list(atom)
        new_atom[relclass_idx] = _fresh_fv()
        return new_atom
      if (entity and _is_ground_term(entity) and
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
    return [pred] + [_coerce_atom(el, const_classes, is_question) for el in atom[1:]]
  if pred in ("forall", "exists") and len(atom) >= 3:
    return [pred, atom[1], _coerce_atom(atom[2], const_classes, is_question)]

  return atom


def _coerce_clause(clause, const_classes, is_question=False):
  """Apply _coerce_atom to a GK clause (single atom or disjunction)."""
  if not isinstance(clause, list) or not clause:
    return clause
  # Disjunction: first element is itself a list of atoms.
  if isinstance(clause[0], list):
    return [_coerce_atom(atom, const_classes, is_question) for atom in clause]
  # Single atom.
  return _coerce_atom(clause, const_classes, is_question)


# ======== question formula flattening ========

def _flatten_q_atoms(frm, varmap):
  """Strip all quantifiers and flatten AND conjunctions in a question formula.

  Every bound variable (forall or exists) is renamed to ?:VAR and the
  quantifier wrapper is dropped.  Nested ["and", ...] conjunctions are
  recursively flattened.  All other formulas (atoms, or, etc.) have the
  varmap applied and are returned as a single-element list.

  Returns a flat list of atoms ready for the @question value.
  """
  if not isinstance(frm, list) or not frm:
    return []
  op = frm[0]

  if op in ("exists", "forall"):
    var    = str(frm[1])
    gk_var = "?:" + var
    new_vm = dict(varmap)
    new_vm[var] = gk_var
    return _flatten_q_atoms(frm[2], new_vm)

  if op == "and":
    atoms = []
    for el in frm[1:]:
      atoms.extend(_flatten_q_atoms(el, varmap))
    return atoms

  # Atom or other formula (or, not, …) — apply varmap, return as one item.
  return [_apply_varmap(frm, varmap)]


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
