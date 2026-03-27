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
  find_hastime_prep,
  build_defq_question,
  find_where_atom,
  find_when_atom,
  build_where_question,
  build_when_question,
  build_who_question,
  flatten_q_atoms,
  scan_item_formula,
  build_population_facts,
  is_ground_term,
  S2_VAR_RE,
  WHERE_SPATIAL_PREPS,
  WHEN_TEMPORAL_PREPS,
)


# Post-clausification passes (in lc_postprocess.py).
from lc_postprocess import (
  GRADABLE_PROPS as _GRADABLE_PROPS,
  populate_clauses as _populate_clauses,
  build_compound_subsumption as _build_compound_subsumption,
  coerce_relclass as _coerce_relclass,
  normalize_gradable_predicates as _normalize_gradable_predicates,
  strip_isa_entity as _strip_isa_entity,
  rewrite_definites as _rewrite_definites,
  add_possessive_have as _add_possessive_have,
  strip_degree_predicates as _strip_degree_predicates,
)

# $ctxt injection and time handling (in lc_ctxt.py).
import lc_ctxt
from lc_ctxt import (
  fresh_fv as _fresh_fv,
  is_rule_formula as _is_rule_formula,
  strip_time_wrappers as _strip_time_wrappers,
  inject_ctxt_atom as _inject_ctxt_atom,
  inject_ctxt_into_objs as _inject_ctxt_into_objs,
  inject_ctxt_question as _inject_ctxt_question,
  MAIN_RELATION_PREDS as _MAIN_RELATION_PREDS,
)


# Pre-clausification formula rewrites (in lc_rewrites.py).
from lc_rewrites import (
  rewrite_meta_predicates as _rewrite_meta_predicates,
  inject_degree_presuppositions as _inject_degree_presuppositions,
  hoist_misnested_exists as _hoist_misnested_exists,
  strip_spurious_can as _strip_spurious_can,
  negate_consequent as _negate_consequent,
)


# Stative event rewriting is in semnormalize.py; import the entry point.
from semnormalize import rewrite_stative_events as _rewrite_stative_events


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
    raw = pkg.get("raw", "")
    for asu in pkg.get("units", []):
      if isinstance(asu, dict):
        uid = asu.get("unit_id")
        if uid:
          asu["_raw"] = raw  # store parent raw text for who/what detection
          index[uid] = asu
  return index


def _collect_isa_entities(tree):
  """Return the set of entity IDs that appear in ["isa", class, entity_id] in *tree*.

  Recursively walks the raw Stage-2 JSON to find all positive isa atoms.
  Used to avoid emitting redundant entity category clauses when the Stage-2
  logic already contains an isa for the same entity.
  """
  found = set()
  if not isinstance(tree, list) or len(tree) == 0:
    return found
  if (len(tree) == 3
      and tree[0] == "isa"
      and isinstance(tree[2], str)):
    found.add(tree[2])
  for child in tree:
    if isinstance(child, list):
      found |= _collect_isa_entities(child)
  return found


def _build_entity_category_clauses(s1_json, skip_entities=frozenset()):
  """Build isa clauses for concrete entities that carry a category annotation.

  For each unique concrete entity with a "category" field in any ASU, emits:
    {"@name": "entity_S<N>", "@logic": ["isa", category, entity_id]}
  where S<N> is the unit_id of the first ASU in which the entity appears.

  Additionally, when the entity id has a lowercase base word that differs from
  the category, also emits isa(base, entity_id).  For example, "man 1" with
  category "person" produces both isa(person, man 1) and isa(man, man 1).
  This ensures the descriptive type word is available for query matching.

  Deduplicates by entity_id so each entity produces at most one set of clauses.
  Entities in *skip_entities* are skipped (they already have an isa in
  the Stage-2 logic).
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
        name = "entity_" + uid
        # Category isa (e.g. isa(person, man 1)) — skip if Stage-2 already has it.
        if eid not in skip_entities:
          clauses.append({"@name": name, "@logic": ["isa", category, eid]})
        # Base-word isa (e.g. isa(man, man 1)) — always add when the base
        # is a lowercase type word different from the category, even if
        # skip_entities contains the entity (Stage-2 may have isa(person,...)
        # but not isa(man,...)).
        parts = eid.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].isdigit():
          base = parts[0]
          if base[:1].islower() and base.lower() != category.lower():
            clauses.append({"@name": name, "@logic": ["isa", base, eid]})
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
  lc_ctxt._fv_nr = 0             # reset once for the whole conversion
  lc_clausify._skolem_nr = 0
  lc_clausify._gobj_nr   = 0
  lc_questions._defq_nr  = 0

  if not logic or not isinstance(logic, list):
    return None

  # Inject degree presuppositions before any other processing:
  # "not very X" presupposes "X", so expand ["not",["has degree property",P,E,"high",C]]
  # into ["and", ["has degree property",P,E,"none",C], ["not",["has degree property",P,E,"high",C]]]
  logic = _inject_degree_presuppositions(logic)

  # Rewrite event-reified stative verbs (have, like, own, ...) to direct
  # predicates.  LLMs sometimes use Davidsonian event encoding for statives;
  # the prover needs the direct predicate form.
  logic = _rewrite_stative_events(logic)

  # Rewrite is_rel2("is", A, B) → isa(A, B).  The copula "is" is not a real
  # relation; LLMs (especially Gemini) sometimes produce it for identity/type
  # questions.  Safe because is_rel2("is",...) has no valid semantic meaning.
  logic = _rewrite_meta_predicates(logic)

  # Rewrite $setof terms to canonical form (replaces ?:X with $arg1,
  # extracts anchors, $-prefixes internal predicates, generates membership
  # axioms and element instantiation clauses).
  import lc_sets as _lc_sets
  _lc_sets._set_counter = 0
  logic, set_axioms, set_element_clauses = _lc_sets.process_sets(logic)

  if logic[0] == "@id":
    items = [logic]
  elif logic[0] == "and":
    items = logic[1:]
  else:
    return None

  # Group set element clauses by source SID so each ASU can inject its own
  # $ctxt (world, tense) into its element facts.  @name format is
  # "sent_S1_el1", "sent_S1_dist", etc. — extract SID as the part between
  # "sent_" and the last "_el" or "_dist" suffix.
  set_el_by_sid = {}
  for cl in set_element_clauses:
    nm = cl.get("@name", "")
    if nm.startswith("sent_"):
      core = nm[5:]  # strip "sent_"
      # Find the SID: everything before "_el" or "_dist"
      for sep in ("_el", "_dist", "_exist"):
        idx = core.find(sep)
        if idx >= 0:
          sid = core[:idx]
          set_el_by_sid.setdefault(sid, []).append(cl)
          break

  # Build unit_id -> ASU index for programmatic $ctxt injection from Stage-1 data.
  asu_index = _build_asu_index(s1_json)

  # Build entity category isa facts from Stage-1 entity annotations.
  # Skip entities that already have an isa in the Stage-2 logic to avoid
  # redundant or potentially conflicting category assertions.
  s2_isa_entities = _collect_isa_entities(logic)
  entity_cat_clauses = _build_entity_category_clauses(s1_json, skip_entities=s2_isa_entities)

  # Build population facts by scanning the raw stage-2 input first.
  pop_facts = _populate_clauses(items)

  # Build compound type subsumption rules (e.g. "baby bird" -> "bird").
  compound_subs = _build_compound_subsumption(items)

  # Track how many times each unit_id has been seen so we can generate
  # globally unique clause names (sent_S1, sent_S1_2, sent_S1_3, ...).
  uid_count = {}
  theof_relations = set()  # collect (REL, TYPE) pairs for bridge axiom generation
  result = []
  for item in items:
    if isinstance(item, list) and len(item) >= 2 and item[0] == "@id":
      sid = str(item[1])
      uid_count[sid] = uid_count.get(sid, 0) + 1
      objs = _convert_id_package(item, asu_index, uid_suffix=uid_count[sid],
                                 set_el_by_sid=set_el_by_sid,
                                 theof_relations=theof_relations)
    else:
      objs = _convert_id_package(item, asu_index, set_el_by_sid=set_el_by_sid,
                                 theof_relations=theof_relations)
    if objs:
      result.extend(objs)

  # Emit any orphan element clauses (SIDs not matched) with free-variable $ctxt.
  for sid, el_clauses in set_el_by_sid.items():
    if not _g_options.get("nocontext_flag", False):
      ctxt_template = ["$ctxt", None, _fresh_fv(), _fresh_fv(), _fresh_fv()]
      _inject_ctxt_into_objs(el_clauses, ctxt_template, _fresh_fv())
    result.extend(el_clauses)

  # Add set membership axioms (pre-clausified by lc_sets).
  for ax_clause in set_axioms:
    result.append({"@name": "frm_set", "@logic": ax_clause})

  # Add per-relation $theof1 bridge axioms.
  for rel_name, type_base in theof_relations:
    # is_rel2("father of", $theof1("father", ?:S, ?:C), ?:S, ?:C)
    bridge_rel = ["is rel2", rel_name,
                  ["$theof1", type_base, "?:S", "?:C"], "?:S", "?:C"]
    result.append({"@name": "frm_theof", "@logic": bridge_rel})
    # isa("father", $theof1("father", ?:S, ?:C))
    bridge_isa = ["isa", type_base,
                  ["$theof1", type_base, "?:S", "?:C"]]
    result.append({"@name": "frm_theof", "@logic": bridge_isa})

  # Prepend entity category clauses at the start of the clause list so they
  # are available as given facts throughout the proof.
  result = entity_cat_clauses + result

  # Insert population facts and compound subsumption rules immediately before
  # the first @question entry so they are available as background knowledge.
  background = pop_facts + compound_subs
  first_q = next((i for i, o in enumerate(result) if "@question" in o), len(result))
  result[first_q:first_q] = background

  # Inject $ctxt into population and subsumption facts (free-variable rules).
  if not _g_options.get("nocontext_flag", False):
    for fact in background:
      ctxt_template = ["$ctxt", None, _fresh_fv(), _fresh_fv(), _fresh_fv()]
      _inject_ctxt_into_objs([fact], ctxt_template, _fresh_fv())

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

  # @sourcetype is kept in the clause list so that downstream display code
  # (format_sentences_to_clauses) can distinguish population facts from
  # ASU-derived clauses.  It is stripped in clause_list_to_json_commented
  # before serialization for the prover.

  return result


# ======== package extraction ========


def _question_has_main_relation(formula):
  """Return True if the question formula contains a main relational predicate.

  Scans top-level conjuncts (not inside exists) for have, can, is_rel2, etc.
  When True, property predicates (has_property, has_degree_property) in the
  question are restrictive modifiers (descriptive), not the matrix predication.
  """
  # Unwrap question/ask wrappers to get the body.
  body = formula
  if isinstance(body, list) and body:
    if body[0] == "question" and len(body) >= 2:
      body = body[1]
    elif body[0] == "ask" and len(body) >= 3:
      body = body[2]
  if not isinstance(body, list) or not body:
    return False
  # Collect top-level conjuncts.
  if body[0] == "and":
    conjuncts = body[1:]
  else:
    conjuncts = [body]
  for c in conjuncts:
    if not isinstance(c, list) or not c or not isinstance(c[0], str):
      continue
    pred = c[0]
    base = pred[1:] if pred.startswith("-") else pred
    # Direct main relation predicate (have, can, is_rel2, etc.)
    if base in _MAIN_RELATION_PREDS:
      return True
    # Event-based predication: an exists block indicates a reified event
    # (e.g. "bought", "ate") which is a main predication, not just a modifier.
    if base == "exists" and len(c) >= 3:
      return True
  return False


def _fix_missing_ask(formula, asu_index, sid):
  """Wrap formula as ["ask", VAR, BODY] when Stage-1 has wh_placeholder.

  Some LLMs produce ["question", BODY] instead of ["ask", VAR, BODY] for
  wh-questions.  After _extract_package_ctx, ["question", BODY] becomes just
  BODY (unwrapped), while ["ask", VAR, BODY] stays as-is.  So we detect the
  missing "ask" by checking: is_question is True, formula doesn't start with
  "ask", and Stage-1 has wh_placeholder.  Then find the free variable and wrap.
  """
  if not isinstance(formula, list) or not formula:
    return formula
  # Already correct: ["ask", VAR, BODY] survived extraction.
  if formula[0] == "ask":
    return formula
  # Check Stage-1 for wh_placeholder.
  if not asu_index:
    return formula
  asu = asu_index.get(sid)
  if asu is None:
    return formula
  has_wh = False
  for ent in asu.get("entities", []):
    if isinstance(ent, dict) and ent.get("wh_placeholder"):
      has_wh = True
      break
  if not has_wh:
    return formula
  # Find free variables in the question body.
  free_vars = sorted(collect_body_free_vars(formula))
  if len(free_vars) == 1:
    return ["ask", free_vars[0], formula]
  return formula


def _detect_who_query(body, ask_var):
  """Detect 'Who is X?' / 'What is X?' pattern and return the entity constant.

  Matches:
    ["=", ask_var, ENTITY] or ["=", ENTITY, ask_var]
    ["isa", ask_var, ENTITY] or ["isa", ENTITY, ask_var]
    ["is rel2", "is", ENTITY, ask_var]
  where ENTITY is a ground constant (not a stage-2 variable).
  Returns the entity string, or None if not matched.
  """
  if not isinstance(body, list) or len(body) < 3:
    return None
  op = body[0]
  if op == "=" and len(body) == 3:
    a, b = body[1], body[2]
    if a == ask_var and isinstance(b, str) and not S2_VAR_RE.match(b):
      return b
    if b == ask_var and isinstance(a, str) and not S2_VAR_RE.match(a):
      return a
  # ["isa", ask_var, ENTITY] — ask_var in type position: "What type is ENTITY?"
  # Do NOT match ["isa", TYPE, ask_var] — that's "Which X is a TYPE?" (standard wh)
  if op == "isa" and len(body) == 3:
    if body[1] == ask_var and isinstance(body[2], str) and not S2_VAR_RE.match(body[2]):
      return body[2]
  # ["is rel2", "is", ENTITY, ask_var] or ["is rel2", "is", ask_var, ENTITY]
  if op == "is rel2" and len(body) >= 4 and body[1] == "is":
    a, b = body[2], body[3]
    if b == ask_var and isinstance(a, str) and not S2_VAR_RE.match(a):
      return a
    if a == ask_var and isinstance(b, str) and not S2_VAR_RE.match(b):
      return b
  return None


def _process_question(formula, name, raw_text=None):
  """Handle question formulas (ask / yes-no) → (result_list, question_kind).

  question_kind is None, "where", or "when".
  Returns (None, None) when the formula produces no output (caller should return []).
  """
  question_kind = None
  # Distinguish wh-questions (["ask", var, body]) from yes/no questions.
  if isinstance(formula, list) and len(formula) >= 3 and formula[0] == "ask":
    ask_var = str(formula[1])
    body    = formula[2]
    # "Where is X?" pattern: body contains ["is rel2", <meta-pred>, entity, ask_var]
    result = None
    where_atom = find_where_atom(body, ask_var)
    if where_atom is not None:
      entity = where_atom[2]
      atom_pred = where_atom[1]
      # Use specific prep when query uses a non-default spatial preposition
      # (near, above, under); use all preps for "in"/"on"/"at" and meta-predicates
      # since these are generic location queries.
      _GENERIC_SPATIAL = frozenset({"in", "on", "at"})
      specific_prep = atom_pred if (atom_pred in WHERE_SPATIAL_PREPS
                                    and atom_pred not in _GENERIC_SPATIAL) else None
      # When the entity is a stage-2 variable (e.g. "Y" for "a car"),
      # build_where_question would generate an over-broad biconditional
      # matching ANY entity's location.  Instead, use build_defq_question
      # which preserves all constraints from the original body (e.g. isa(car,Y)).
      # For meta-predicates with variable entity, fall through to the general
      # defq path below (meta-preds like "located in" don't exist in facts).
      entity_is_s2var = isinstance(entity, str) and bool(S2_VAR_RE.match(entity))
      if entity_is_s2var:
        # Variable entity + meta-predicate: fall through to general path.
        # Variable entity + concrete prep: use defq with that prep.
        if specific_prep:
          result = build_defq_question(name, ask_var, body,
                                       wh_prep=specific_prep, wh_marker="@where_query")
          question_kind = "where"
      else:
        result = build_where_question(name, entity, ask_var, specific_prep=specific_prep)
        question_kind = "where"
    if result is None:
      # "When is X?" pattern: body contains ["is rel2", <temporal-pred>, entity, ask_var]
      when_atom = find_when_atom(body, ask_var)
      if when_atom is not None:
        entity = when_atom[2]
        atom_pred = when_atom[1]
        specific_prep = atom_pred if atom_pred in WHEN_TEMPORAL_PREPS else None
        entity_is_s2var = isinstance(entity, str) and bool(S2_VAR_RE.match(entity))
        if entity_is_s2var:
          wp = specific_prep if specific_prep else "in"
          result = build_defq_question(name, ask_var, body,
                                       wh_prep=wp, wh_marker="@when_query")
        else:
          result = build_when_question(name, entity, ask_var, specific_prep=specific_prep)
        question_kind = "when"
      else:
        # "Who is X?" / "What is X?" pattern: body is [=, var, entity] or [isa, ...]
        who_entity = _detect_who_query(body, ask_var)
        if who_entity is not None:
          # Determine who vs what from raw question text
          who_kind = "what" if raw_text and raw_text.lower().startswith("what") else "who"
          result = build_who_question(name, who_entity, ask_var, who_kind=who_kind)
          question_kind = "who"
        elif is_simple_question_formula(body):
          # Single atom with ≤1 variable: direct @question, no $defq wrapper.
          free_vars_in_body = sorted(collect_body_free_vars(body))
          varmap = {ask_var: "?:" + ask_var}
          varmap.update({v: "?:" + v for v in free_vars_in_body})
          flat = flatten_q_atoms(body, varmap)
          if not flat:
            return None, None
          q_formula = flat[0] if len(flat) == 1 else [["and"] + flat]
          result = [{"@name": name, "@question": q_formula, "@askvars": 1}]
        else:
          # Complex case: wrap in $defq biconditional.
          # Detect has_location(E, ask_var) → encode "in" as the preposition.
          where_prep = find_haslocation_prep(body, ask_var)
          if where_prep:
            result = build_defq_question(name, ask_var, body, where_prep=where_prep)
            question_kind = "where"
          else:
            # Detect has_time(E, ask_var) → encode "in" as the temporal preposition.
            when_prep = find_hastime_prep(body, ask_var)
            if when_prep:
              result = build_defq_question(name, ask_var, body,
                                           wh_prep=when_prep, wh_marker="@when_query")
              question_kind = "when"
            else:
              result = build_defq_question(name, ask_var, body)
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
        return None, None
      q_formula = flat[0] if len(flat) == 1 else [["and"] + flat]
      result = [{"@name": name, "@question": q_formula}]
    else:
      # Complex formula, or: simple but $ctxt active → $defq biconditional.
      # Fix contradictory ["and", ["not", A], A] that LLM generates for
      # "No X is Y?" questions — simplify to just ["not", A].
      formula = simplify_contradictory_and(formula)
      result = build_defq_question(name, None, formula)
  return result, question_kind


def _process_assertion(formula, name, confidence):
  """Handle assertion formulas → list of GK clause dicts."""
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
  return result


def _convert_id_package(item, asu_index=None, uid_suffix=None, set_el_by_sid=None,
                        theof_relations=None):
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

  # Strip @time wrappers and annotate leaf atoms with $tense sentinels.
  # Pass the ASU-level tense as the default; atoms inside @time wrappers
  # will get their specific tense instead.
  if not _g_options.get("nocontext_flag", False):
    formula = _strip_time_wrappers(formula, tense)

  question_kind = None
  if is_question:
    # Remove spurious "can" from event queries with no modal language.
    asu_text = ""
    if asu_index:
      asu = asu_index.get(sid)
      if asu:
        asu_text = asu.get("text", "")
    formula = _strip_spurious_can(formula, asu_text)
    # Safety net: if Stage-1 has wh_placeholder but Stage-2 used ["question",...]
    # instead of ["ask",VAR,...], detect the free variable and convert.
    formula = _fix_missing_ask(formula, asu_index, sid)
    # Get raw question text for who/what detection
    raw_q_text = ""
    if asu_index:
      asu_q = asu_index.get(sid)
      if asu_q:
        raw_q_text = asu_q.get("_raw", asu_q.get("text", ""))
    result, question_kind = _process_question(formula, name, raw_text=raw_q_text)
    if result is None:
      return []
  else:
    formula = _hoist_misnested_exists(formula)
    result = _process_assertion(formula, name, confidence)

  # Inject $ctxt into @logic entries (not @question entries).
  ctxt_template = None
  tense_term = None
  if not _g_options.get("nocontext_flag", False):
    loc_term = location if location is not None else _fresh_fv()
    kn_term  = knower  if knower  is not None else _fresh_fv()
    if _is_rule_formula(formula):
      situation  = _fresh_fv()
      tense_term = _fresh_fv()   # rules are tense-independent
      ctxt_template = ["$ctxt", None, situation, loc_term, kn_term]
      _inject_ctxt_into_objs(result, ctxt_template, tense_term)
    elif is_question:
      if question_kind in ("where", "when"):
        # Where/when-query biconditionals must be world-agnostic: location/time
        # facts may come from any world state (e.g. W0 travel facts vs W2 query).
        situation  = _fresh_fv()
        tense_term = _fresh_fv()
        ctxt_template = ["$ctxt", None, situation, loc_term, kn_term]
        _inject_ctxt_into_objs(result, ctxt_template, tense_term)
      else:
        # Non-where questions: matrix predicates use the query's world;
        # descriptive predicates (isa, event atoms from relative clauses)
        # use free-var world so they can match assertions in any world state.
        # When a main relation (have, can, is_rel2) is present, property
        # predicates are also descriptive (restrictive noun modifiers).
        matrix_world = world if world is not None else _fresh_fv()
        desc_world   = _fresh_fv()
        tense_term   = tense if tense is not None else _fresh_fv()
        ctxt_matrix = ["$ctxt", None, matrix_world, loc_term, kn_term]
        ctxt_desc   = ["$ctxt", None, desc_world,   loc_term, kn_term]
        props_desc = _question_has_main_relation(formula)
        _inject_ctxt_question(result, ctxt_matrix, ctxt_desc, tense_term,
                              props_are_desc=props_desc)
    else:
      # Situational facts: world from ["holds",W,F]; tense from Stage-1 time field.
      situation  = world if world is not None else _fresh_fv()
      tense_term = tense if tense is not None else "present"
      ctxt_template = ["$ctxt", None, situation, loc_term, kn_term]
      _inject_ctxt_into_objs(result, ctxt_template, tense_term)

  # Rewrite definite functional descriptions to $theof1 terms.
  if theof_relations is not None:
    _rewrite_definites(result, asu_index, str(sid), theof_relations)

  # Inject $ctxt into set element instantiation clauses for this ASU.
  # Element clauses inherit the same world/tense as the ASU's own clauses.
  sid_key = str(sid)
  if set_el_by_sid and sid_key in set_el_by_sid:
    el_clauses = set_el_by_sid.pop(sid_key)
    if ctxt_template is not None and not is_question:
      _inject_ctxt_into_objs(el_clauses, ctxt_template, tense_term)
    result.extend(el_clauses)

  return result


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



# =========== the end ==========
