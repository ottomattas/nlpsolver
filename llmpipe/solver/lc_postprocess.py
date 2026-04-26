# Post-clausification passes for the llm-based nlpsolver.
#
# Operates on the clause list (list of dicts with @logic/@question).
# Includes: gradable property normalization, RELCLASS coercion,
# isa-entity stripping, $theof1 definite rewrites, possessive have
# inference, population fact generation, compound type subsumption,
# and degree-predicate stripping.
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

import os as _os

from lc_ctxt import fresh_fv as _fresh_fv
from lc_questions import scan_item_formula, build_population_facts, is_ground_term
import globals as _g
_g_options = _g.options

# Lazy import to avoid circular dependency (logconvert imports lc_postprocess).
def _get_extract_package_ctx():
  from logconvert import _extract_package_ctx
  return _extract_package_ctx

# ======== gradable property whitelist ========

def load_gradable_props():
  """Load solver/gradables.txt into a frozenset of lowercase property names."""
  try:
    path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "gradables.txt")
    with open(path) as f:
      return frozenset(line.strip().lower() for line in f if line.strip())
  except Exception:
    return frozenset()

GRADABLE_PROPS = load_gradable_props()
# ======== population fact scanning ========

def populate_clauses(items):
  """Scan all @id items in the raw stage-2 input and return population entries.

  This is the main entry point called from rawlogic_convert.  The underlying
  scanner (scan_item_formula) handles both raw stage-2 and clausified forms,
  so this function can also be applied to a clausified clause list.
  """
  classes   = {}   # CLASS -> {"name", "has_pos", "has_neg"}
  has_props = {}   # PROPERTY -> {"name", "has_pos", "has_neg"}
  deg_props = {}   # (PROPERTY, RELCLASS) -> {"name", "has_pos", "has_neg"}
  compound_witnesses = {}  # (type, pred, prep, target) -> info dict

  for item in items:
    if not isinstance(item, list) or len(item) < 3 or item[0] != "@id":
      continue
    name    = "sent_" + str(item[1])
    package = item[2]
    _is_q, formula, _conf, _, _, _, _ = _get_extract_package_ctx()(package)
    if _is_q:
      continue   # never populate from the question sentence — circular by construction
    if formula is not None:
      scan_item_formula(formula, name, True, classes, has_props, deg_props,
                        compound_witnesses=compound_witnesses)

  return build_population_facts(classes, has_props, deg_props,
                                compound_witnesses=compound_witnesses)


# ======== compound type rules ========

def scan_compound_types(items):
  """Scan all @id items for isa / -isa atoms with space-containing type names.

  Returns a set of compound type strings (e.g. {"baby bird"}).
  """
  compounds = set()

  def _walk(frm):
    if not isinstance(frm, list) or not frm:
      return
    op = frm[0]
    if isinstance(op, str) and op in ("isa", "-isa") and len(frm) >= 3:
      typename = frm[1]
      if isinstance(typename, str) and " " in typename:
        compounds.add(typename)
    for el in frm[1:]:
      if isinstance(el, list):
        _walk(el)

  for item in items:
    if not isinstance(item, list) or len(item) < 3 or item[0] != "@id":
      continue
    _walk(item[2])

  return compounds


def build_compound_subsumption(items):
  """Build subsumption and composition rules for compound type names.

  For each compound type like "baby bird", emits:
    Rule 1 (subsumption, strict):
      [-isa, "baby bird", "?:X"], ["isa", "bird", "?:X"]
    Rule 2 (composition, confidence 0.95, no blocker):
      [-isa, "baby", "?:X"], [-isa, "bird", "?:X"], ["isa", "baby bird", "?:X"]
  """
  compounds = scan_compound_types(items)
  result = []
  for ctype in sorted(compounds):
    parts = ctype.split()
    head = parts[-1]
    modifier = " ".join(parts[:-1])
    # Rule 1: subsumption (strict) — baby bird -> bird
    result.append({
      "@name": "compound_sub",
      "@logic": [["-isa", ctype, "?:X"], ["isa", head, "?:X"]]
    })
    # Rule 2: composition (semi-strict) — baby + bird -> baby bird
    result.append({
      "@name": "compound_comp",
      "@logic": [
        ["-isa", modifier, "?:X"],
        ["-isa", head, "?:X"],
        ["isa", ctype, "?:X"]
      ],
      "@confidence": 0.95
    })
  return result


# ======== RELCLASS coercion ========

# Maps predicate name -> (entity_arg_index, relclass_arg_index).
# Used to identify which argument is the entity (for class lookup) and which
# is the RELCLASS (to be replaced when it doesn't match the entity's known class).
_degree_preds_relclass = {
  "has degree property": (2, 4),   # [pred, PROP, ENTITY, DEGREE, RELCLASS]
  "has degree rel2":     (2, 5),   # [pred, REL, E1, E2, DEGREE, RELCLASS] — RELCLASS describes E1
}


def coerce_relclass(result):
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
      # Strip leading "-" so rule-body negated literals also contribute.
      base_pred = pred[1:] if pred.startswith("-") else pred
      # isa(CLASS, CONST) — build const_classes (positive only)
      if pred == "isa" and len(atom) >= 3 and is_ground_term(atom[2]):
        const_classes.setdefault(atom[2], set()).add(str(atom[1]))
      # has degree property [pred, PROP, ENTITY, DEGREE, RELCLASS, ...]
      # Collect concrete (non-variable) relclass strings from both positive
      # (ground fact) and negative (rule body) occurrences.
      elif base_pred == "has degree property" and len(atom) >= 5:
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

  # --- 3. apply assertion-side coercion for multi-class entities ---
  # When a ground entity has isa classes that differ from an assertion's
  # RELCLASS slot (e.g. John is isa "bear" but the fact says "nice for an
  # animal"), Stage-1 has leaked a generic category into the relclass.
  # Coerce such assertion-side relclasses to a free variable so rules using
  # the entity's actual class (or another cross-used relclass) can unify.
  for obj in result:
    if not isinstance(obj, dict):
      continue
    if "@logic" not in obj:
      continue
    if obj.get("@sourcetype") in ("question", "populate"):
      continue
    obj["@logic"] = _coerce_clause(obj["@logic"], const_classes,
                                   prop_relclasses=prop_relclasses,
                                   is_question=False,
                                   assertion_multi_class=True)


def _coerce_atom(atom, const_classes, prop_relclasses=None, is_question=False,
                 assertion_multi_class=False):
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

  For non-question assertional atoms (default): replace relclass when it
  mismatches the entity's single known isa class (original behaviour).

  For non-question assertional atoms with assertion_multi_class=True:
  replace relclass with a free variable when the entity has multiple
  known classes, the current relclass is one of them, and another of the
  entity's classes appears as a relclass for the same property elsewhere
  (evidence of a rule/fact relclass split, e.g. "John is big (for an
  animal)" vs rule "for a bear").
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
      elif assertion_multi_class:
        # Assertion-side RELCLASS coercion. Fires in two situations:
        # (a) Entity has multiple isa classes and the relclass is one of them,
        #     while another of the entity's classes is used as a relclass
        #     elsewhere (evidence of a split between generic vs specific class).
        # (b) The relclass is NOT one of the entity's isa classes but a rule
        #     elsewhere uses a relclass that IS one of the entity's classes
        #     (the stage-1 generic category leaked into the relclass slot
        #     even though no matching isa fact was emitted).
        # In either case, replace with a fresh free variable so the rule's
        # relclass can unify.
        if (base == "has degree property" and
            entity and is_ground_term(entity) and
            entity in const_classes and
            isinstance(relclass, str) and not relclass.startswith("?")):
          prop = atom[1] if len(atom) > 1 else ""
          existing = (prop_relclasses or {}).get(str(prop), set())
          entity_classes = const_classes[entity]
          case_a = (relclass in entity_classes and len(entity_classes) > 1 and
                    any(c in existing for c in entity_classes - {relclass}))
          case_b = (relclass not in entity_classes and
                    any(c in existing for c in entity_classes))
          if case_a or case_b:
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
    return [pred] + [_coerce_atom(el, const_classes, prop_relclasses,
                                  is_question, assertion_multi_class)
                     for el in atom[1:]]
  if pred in ("forall", "exists") and len(atom) >= 3:
    return [pred, atom[1], _coerce_atom(atom[2], const_classes, prop_relclasses,
                                        is_question, assertion_multi_class)]

  return atom


def _coerce_clause(clause, const_classes, prop_relclasses=None, is_question=False,
                   assertion_multi_class=False):
  """Apply _coerce_atom to a GK clause (single atom or disjunction)."""
  if not isinstance(clause, list) or not clause:
    return clause
  # Disjunction: first element is itself a list of atoms.
  if isinstance(clause[0], list):
    return [_coerce_atom(atom, const_classes, prop_relclasses, is_question,
                         assertion_multi_class)
            for atom in clause]
  # Single atom.
  return _coerce_atom(clause, const_classes, prop_relclasses, is_question,
                      assertion_multi_class)


# ======== gradable predicate normalization ========

def normalize_gradable_predicates(result):
  """Normalize has property / has degree property atoms based on GRADABLE_PROPS.

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
  if not GRADABLE_PROPS:
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
    if isinstance(prop, str) and prop.lower() not in GRADABLE_PROPS:
      # Strip to has property; preserve $ctxt at position 5 if present.
      new_atom = [pfx + "has property", frm[1], frm[2]]
      if len(frm) >= 6:
        new_atom.append(frm[5])
      return new_atom
    # Keep as degree property; replace "entity"/"none" relclass with a free variable
    # since both mean "no specific comparison class" and carry no useful constraint.
    relclass = frm[4]
    if relclass in ("entity", "none"):
      new_atom = [frm[0], frm[1], frm[2], frm[3], _fresh_fv()]
      if len(frm) >= 6:
        new_atom.append(frm[5])
      return new_atom

  elif base == "has property" and len(frm) >= 3:
    # ["has property", PROP, ENTITY, optional_$ctxt]
    prop = frm[1]
    if isinstance(prop, str) and prop.lower() in GRADABLE_PROPS:
      # Upgrade to has degree property; use a free variable for relclass
      # (avoids spurious "entity" constant that can block unification).
      new_atom = [pfx + "has degree property", frm[1], frm[2], "none", _fresh_fv()]
      if len(frm) >= 4:
        new_atom.append(frm[3])
      return new_atom

  elif base == "has degree rel2" and len(frm) >= 6:
    # ["has degree rel2", REL, E1, E2, DEGREE, RELCLASS, optional_$ctxt]
    rel = frm[1]
    if isinstance(rel, str) and rel.lower() not in GRADABLE_PROPS:
      # Non-gradable relation: strip to is rel2; preserve $ctxt if present.
      new_atom = [pfx + "is rel2", frm[1], frm[2], frm[3]]
      if len(frm) >= 7:
        new_atom.append(frm[6])
      return new_atom
    # Gradable: replace "entity"/"none" relclass with a free variable.
    relclass = frm[5]
    if relclass in ("entity", "none"):
      new_atom = [frm[0], frm[1], frm[2], frm[3], frm[4], _fresh_fv()]
      if len(frm) >= 7:
        new_atom.append(frm[6])
      return new_atom

  elif base == "is rel2" and len(frm) >= 4:
    # ["is rel2", REL, E1, E2, optional_$ctxt]
    rel = frm[1]
    if isinstance(rel, str) and rel.lower() in GRADABLE_PROPS:
      # Gradable relation: upgrade to has degree rel2 with free relclass.
      new_atom = [pfx + "has degree rel2", frm[1], frm[2], frm[3], "none", _fresh_fv()]
      if len(frm) >= 5:
        new_atom.append(frm[4])
      return new_atom

  # Logical connectives / quantifiers: recurse into sub-formulas.
  return [frm[0]] + [_norm_grad_frm(a) if isinstance(a, list) else a
                     for a in frm[1:]]


# ======== isa-entity stripping ========

def strip_isa_entity(result):
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


# ======== $theof1 definite function terms ========

def _deep_replace(obj, old_val, new_val):
  """Recursively replace old_val with new_val throughout a nested list structure.

  old_val can be a string or a list (Skolem function).  Comparison is by
  equality (== operator, which does deep structural comparison for lists).
  """
  if obj == old_val:
    return new_val
  if isinstance(obj, list):
    return [_deep_replace(el, old_val, new_val) for el in obj]
  return obj


def _find_is_rel2_match(result, rel_name):
  """Find an is_rel2 atom in the clause list matching the given relation name.

  Scans all @logic entries for an atom of the form:
    ["is rel2", rel_name, VALUE_TERM, ARG_TERM, CTXT]
  or inside a disjunction (multi-literal clause):
    [... ["is rel2", rel_name, VALUE_TERM, ARG_TERM, CTXT] ...]

  Returns (clause_index, VALUE_TERM, ARG_TERM, CTXT) or None.
  """
  for i, obj in enumerate(result):
    if not isinstance(obj, dict) or "@logic" not in obj:
      continue
    clause = obj["@logic"]
    atoms = _clause_atoms(clause)
    for atom in atoms:
      if (isinstance(atom, list) and len(atom) >= 4
          and atom[0] == "is rel2" and atom[1] == rel_name):
        value_term = atom[2]
        arg_term = atom[3]
        ctxt = atom[4] if len(atom) > 4 else None
        return (i, value_term, arg_term, ctxt)
  return None


def _find_have_isa_match(result, type_base):
  """Fallback: find have/has_part + isa pair matching a definite type.

  Looks for clauses containing:
    ["isa", type_base, VALUE_TERM]
  and:
    ["have", ARG_TERM, VALUE_TERM, CTXT]
    or ["has part", ARG_TERM, VALUE_TERM, CTXT]
  where VALUE_TERM is the same in both.

  Returns (VALUE_TERM, ARG_TERM, CTXT) or None.
  """
  # Collect all (VALUE_TERM -> True) from isa atoms matching type_base
  isa_values = set()
  for obj in result:
    if not isinstance(obj, dict) or "@logic" not in obj:
      continue
    for atom in _clause_atoms(obj["@logic"]):
      if (isinstance(atom, list) and len(atom) >= 3
          and atom[0] == "isa" and atom[1] == type_base):
        val = atom[2]
        # Hashable key: use str() for lists (Skolem functions)
        isa_values.add(str(val) if isinstance(val, list) else val)

  # Find have or has_part atom whose VALUE_TERM is in isa_values
  for obj in result:
    if not isinstance(obj, dict) or "@logic" not in obj:
      continue
    for atom in _clause_atoms(obj["@logic"]):
      if (isinstance(atom, list) and len(atom) >= 3
          and atom[0] in ("have", "has part")):
        arg_term = atom[1]
        value_term = atom[2]
        ctxt = atom[3] if len(atom) > 3 else None
        key = str(value_term) if isinstance(value_term, list) else value_term
        if key in isa_values:
          return (value_term, arg_term, ctxt)
  return None


def _clause_atoms(clause):
  """Extract individual atoms from a clause (which may be a single atom or
  a multi-literal disjunction [lit1, lit2, ...] where each lit is a list)."""
  if not isinstance(clause, list) or not clause:
    return []
  # Multi-literal clause: list of lists (each element is an atom/literal)
  if isinstance(clause[0], list):
    return clause
  # Single-literal clause: the clause itself is the atom
  if isinstance(clause[0], str):
    return [clause]
  return []


def rewrite_definites(result, asu_index, sid, theof_relations):
  """Rewrite definite functional descriptions to $theof1 terms.

  For each definite in the ASU's Stage-1 data, find the corresponding
  is_rel2 (or have+isa fallback) in the clausified result, construct a
  $theof1 function term, and replace the entity throughout all clauses.

  theof_relations: set to collect (REL, TYPE) pairs for bridge axiom generation.
  """
  if not asu_index:
    return
  asu = asu_index.get(sid)
  if not asu:
    return
  definites = asu.get("definites")
  if not definites or not isinstance(definites, list):
    return

  for defn in definites:
    if not isinstance(defn, list) or len(defn) < 3:
      continue
    rel_name = defn[0]    # e.g., "father of", "head of"
    value_id = defn[1]    # e.g., "the father 2", "the head 1"
    # arg_id = defn[2]    # e.g., "John 1", "elephant 2" — may not appear in clauses

    # Compute base type: strip trailing " of" from relation name
    if rel_name.endswith(" of"):
      type_base = rel_name[:-3]
    else:
      type_base = rel_name

    # Primary: find is_rel2 match
    match = _find_is_rel2_match(result, rel_name)
    remove_clause_idx = None
    if match:
      clause_idx, value_term, arg_term, ctxt = match
      remove_clause_idx = clause_idx
    else:
      # Fallback: find have + isa match
      have_match = _find_have_isa_match(result, type_base)
      if have_match:
        value_term, arg_term, ctxt = have_match
      else:
        continue  # No matching pattern found — skip this definite

    # Construct $theof1 function term
    if ctxt is not None:
      fn_term = ["$theof1", type_base, arg_term, ctxt]
    else:
      fn_term = ["$theof1", type_base, arg_term]

    # Deep-replace value_term with fn_term throughout all clauses
    for obj in result:
      if "@logic" in obj:
        obj["@logic"] = _deep_replace(obj["@logic"], value_term, fn_term)
      if "@question" in obj:
        obj["@question"] = _deep_replace(obj["@question"], value_term, fn_term)

    # Remove the is_rel2 clause (now derivable from bridge axioms)
    if remove_clause_idx is not None:
      # Re-find it since indices may have shifted — match by content
      for i, obj in enumerate(result):
        if not isinstance(obj, dict) or "@logic" not in obj:
          continue
        clause = obj["@logic"]
        atoms = _clause_atoms(clause)
        has_is_rel2 = any(
          isinstance(a, list) and len(a) >= 4
          and a[0] == "is rel2" and a[1] == rel_name
          for a in atoms
        )
        if has_is_rel2:
          result.pop(i)
          break

    # Emit the grounded possession fact have(arg, fn_term, ctxt). The
    # matching is_rel2 fact was just consumed/removed, and the universal
    # have bridge formerly in axioms_std.js (removed because it generated
    # free-variable wh-answers) no longer fills the gap — so we explicitly
    # assert this grounded fact. Needed whenever arg_term is concrete
    # (e.g. "Mary 3") so "Mary had a brother?" resolves via a concrete have.
    if arg_term is not None:
      have_atom = ["have", arg_term, fn_term]
      if ctxt is not None:
        have_atom.append(list(ctxt) if isinstance(ctxt, list) else ctxt)
      result.append({"@name": "frm_theof", "@logic": have_atom})

    # Record for bridge axiom generation
    theof_relations.add((rel_name, type_base))


# ======== $measure_of / $measure canonical rewriting ========

# Unit → (canonical_unit, multiplier)
_UNIT_CONVERSIONS = {
  # Length → meter
  "kilometer":  ("meter", 1000),
  "km":         ("meter", 1000),
  "centimeter": ("meter", 0.01),
  "cm":         ("meter", 0.01),
  "millimeter": ("meter", 0.001),
  "mm":         ("meter", 0.001),
  "meter":      ("meter", 1),
  "m":          ("meter", 1),
  "mile":       ("meter", 1609),
  "foot":       ("meter", 0.3048),
  "feet":       ("meter", 0.3048),
  "inch":       ("meter", 0.0254),
  "yard":       ("meter", 0.9144),
  # Mass → kilogram
  "kilogram":   ("kilogram", 1),
  "kg":         ("kilogram", 1),
  "gram":       ("kilogram", 0.001),
  "g":          ("kilogram", 0.001),
  "milligram":  ("kilogram", 0.000001),
  "mg":         ("kilogram", 0.000001),
  "ton":        ("kilogram", 1000),
  "tonne":      ("kilogram", 1000),
  "pound":      ("kilogram", 0.4536),
  "ounce":      ("kilogram", 0.02835),
  # Time → second
  "second":     ("second", 1),
  "minute":     ("second", 60),
  "hour":       ("second", 3600),
  "day":        ("second", 86400),
  # Volume → liter
  "liter":      ("liter", 1),
  "litre":      ("liter", 1),
  "milliliter": ("liter", 0.001),
  "ml":         ("liter", 0.001),
  "gallon":     ("liter", 3.785),
}


def _convert_to_canonical(number, unit):
  """Convert (80, 'kilometer') → (80000, 'meter') or None."""
  conv = _UNIT_CONVERSIONS.get(unit.lower() if isinstance(unit, str) else unit)
  if conv is None:
    return None
  canonical_unit, multiplier = conv
  return (round(number * multiplier), canonical_unit)


def _canonicalize_measure(term):
  """Convert ["$measure", NUM, UNIT] → ["$list", CANON_NUM, "#:CANON_UNIT"].

  If the unit is unknown, returns ["$list", NUM, "#:UNIT"] (preserves number
  as integer, prefixes unit with #: for UNA).
  """
  if (not isinstance(term, list) or len(term) != 3
      or term[0] != "$measure"):
    return term
  number = term[1]
  unit = term[2]
  if not isinstance(number, (int, float)):
    return term
  converted = _convert_to_canonical(number, unit)
  if converted:
    canon_num, canon_unit = converted
    return ["$list", canon_num, "#:" + canon_unit]
  # Unknown unit: keep number, prefix unit with #:
  unit_str = unit if isinstance(unit, str) else str(unit)
  if not unit_str.startswith("#:"):
    unit_str = "#:" + unit_str
  return ["$list", round(number), unit_str]


def rewrite_measure_terms(result):
  """Convert $measure terms to canonical $list form throughout all clauses.

  Finds ["$measure", NUMBER, UNIT] anywhere in the clause list and replaces
  with ["$list", CANON_NUMBER, "#:CANON_UNIT"].

  Also collects $measure_of attributes for bridge axiom generation.
  Returns set of attribute names found in $measure_of terms.
  """
  measure_attrs = set()

  for obj in result:
    for key in ("@logic", "@question"):
      if key not in obj:
        continue
      obj[key] = _rewrite_measures_in_tree(obj[key], measure_attrs)

  return measure_attrs


def _is_measure_term(term):
  """Return True if term is a measurement: $measure_of, $measure, or $list with #: unit."""
  if not isinstance(term, list) or len(term) < 2:
    return False
  op = term[0]
  if op in ("$measure_of", "$measure"):
    return True
  if op == "$list" and len(term) == 3:
    unit = term[2]
    return isinstance(unit, str) and unit.startswith("#:")
  return False


# Comparison operators that should be rewritten to less_measure when
# both operands are measurement terms.
_MEASURE_LESS_OPS = frozenset({"<", "$less", "->=", "-$greatereq"})
_MEASURE_GREATER_OPS = frozenset({">", "$greater", "-<=", "-$lesseq"})
_MEASURE_LEQ_OPS = frozenset({"<=", "$lesseq", "->" , "-$greater"})
_MEASURE_GEQ_OPS = frozenset({">=", "$greatereq", "-<", "-$less"})


def _rewrite_measures_in_tree(tree, measure_attrs):
  """Recursively rewrite $measure terms, collect $measure_of attrs,
  and convert comparison operators on measures to less_measure."""
  if not isinstance(tree, list) or not tree:
    return tree
  op = tree[0] if isinstance(tree[0], str) else None

  # Convert $measure to canonical $list
  if op == "$measure" and len(tree) == 3:
    return _canonicalize_measure(tree)

  # Collect $measure_of attributes; unwrap nested $theof1 in entity arg.
  # rewrite_definites may have replaced an entity ID inside $measure_of with
  # $theof1, e.g. $measure_of(price, $theof1(price, car_A, ...), w0).
  # Unwrap to $measure_of(price, car_A, w0).
  if op == "$measure_of" and len(tree) >= 3:
    attr = tree[1]
    if isinstance(attr, str):
      measure_attrs.add(attr)
    entity = tree[2]
    if (isinstance(entity, list) and len(entity) >= 3
        and entity[0] == "$theof1"):
      tree = list(tree)
      tree[2] = entity[2]

  # Rewrite comparison operators on measure terms to less_measure.
  # Must recurse into operands first so $measure is canonicalized.
  if op is not None and len(tree) == 3:
    if op in _MEASURE_LESS_OPS or op in _MEASURE_GREATER_OPS or \
       op in _MEASURE_LEQ_OPS or op in _MEASURE_GEQ_OPS:
      lhs = _rewrite_measures_in_tree(tree[1], measure_attrs)
      rhs = _rewrite_measures_in_tree(tree[2], measure_attrs)
      if _is_measure_term(lhs) or _is_measure_term(rhs):
        if op in _MEASURE_LESS_OPS:
          # A < B  →  less_measure(A, B)
          return ["less_measure", lhs, rhs]
        if op in _MEASURE_GREATER_OPS:
          # A > B  →  less_measure(B, A)
          return ["less_measure", rhs, lhs]
        if op in _MEASURE_LEQ_OPS:
          # A <= B  →  not(less_measure(B, A))
          return ["not", ["less_measure", rhs, lhs]]
        if op in _MEASURE_GEQ_OPS:
          # A >= B  →  not(less_measure(A, B))
          return ["not", ["less_measure", lhs, rhs]]

  # Recurse
  return [_rewrite_measures_in_tree(el, measure_attrs)
          if isinstance(el, list) else el
          for el in tree]


# ======== possessive have inference ========

_ACTIVITY_ROLE_PREDS = frozenset({
  "has target", "has actor", "has instrument", "has direction", "has location",
  "has destination", "has recipient", "has source",
  "has beneficiary", "has accompaniment", "has path", "has result",
  "has topic", "has cause",
})

def add_possessive_have(result):
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

  def _is_entity_term(v):
    """True if v is a valid entity: ground string, Skolem function, or $theof1 term."""
    if _is_ground_str(v):
      return True
    if isinstance(v, list) and len(v) >= 2 and isinstance(v[0], str):
      return v[0].startswith("sk") or v[0] == "$theof1"
    return False

  def _entity_key(v):
    """Hashable key for an entity (string or list term)."""
    return str(v) if isinstance(v, list) else v

  def _extract_atoms(clause):
    """Return list of atoms from a clause (single-atom or multi-literal)."""
    if not isinstance(clause, list) or not clause:
      return []
    if isinstance(clause[0], list):
      return clause  # multi-literal: each element is an atom
    if isinstance(clause[0], str):
      return [clause]  # single atom
    return []

  def _extract_guard(clause):
    """Return the guard literals (negative atoms) from a multi-literal clause.
    For single-atom clauses, returns []."""
    if not isinstance(clause, list) or not clause or not isinstance(clause[0], list):
      return []
    return [atom for atom in clause
            if isinstance(atom, list) and atom
            and isinstance(atom[0], str) and atom[0].startswith("-")]

  # Pass 1a: collect isa(T, E) facts for ground and function-term entities.
  # key: _entity_key(E) -> set of type strings
  isa_types = {}
  for obj in result:
    if not isinstance(obj, dict) or "@logic" not in obj:
      continue
    for atom in _extract_atoms(obj["@logic"]):
      if (isinstance(atom, list) and len(atom) >= 3
          and isinstance(atom[0], str) and atom[0] == "isa"
          and isinstance(atom[1], str) and _is_entity_term(atom[2])):
        typ, ent = atom[1], atom[2]
        isa_types.setdefault(_entity_key(ent), set()).add(typ)

  # Pass 1b: collect CT of the first activity-role fact mentioning each entity.
  # has_target(act, E, CT) / has_actor(act, E, CT) / has_instrument(act, E, CT) …
  # E is always at argument position 2 (index 2) for these predicates.
  entity_event_ct = {}    # entity_key -> CT from containing activity
  for obj in result:
    if not isinstance(obj, dict) or "@logic" not in obj:
      continue
    for atom in _extract_atoms(obj["@logic"]):
      if (isinstance(atom, list) and len(atom) >= 4
          and isinstance(atom[0], str)
          and atom[0] in _ACTIVITY_ROLE_PREDS
          and _is_entity_term(atom[2])):
        ent = atom[2]
        # CT is the last argument if it's a $ctxt list
        ct = None
        if len(atom) > 3:
          last = atom[-1]
          if isinstance(last, list) and last and last[0] == "$ctxt":
            ct = last
        ekey = _entity_key(ent)
        if ekey not in entity_event_ct and ct is not None:
          entity_event_ct[ekey] = ct

  # Pass 2: find is_rel2(R, E, Y, CT_possessive) where R ends in " of" and
  # isa(T, E) exists with T+" of" == R.  Emit have(Y, E, CT_chosen).
  # For rule clauses with guard literals, emit a conditional have with the same guard.
  new_facts = []
  seen = set()
  for obj in result:
    if not isinstance(obj, dict) or "@logic" not in obj:
      continue
    # Skip the universal frm_theof schema axioms: their is_rel2 form has a
    # free ?:S owner and would yield a universally-quantified have axiom
    # ("every entity has its own X"), which lets the prover satisfy any
    # wh-query with a free-variable answer (e.g. "X3 and Tom").
    if obj.get("@name") == "frm_theof":
      continue
    clause = obj["@logic"]
    for atom in _extract_atoms(clause):
      if not (isinstance(atom, list) and len(atom) >= 4
              and isinstance(atom[0], str) and atom[0] == "is rel2"):
        continue
      rel, ent, owner = atom[1], atom[2], atom[3]
      ct_possessive = atom[4] if len(atom) > 4 else None
      if not (isinstance(rel, str) and rel.endswith(" of")):
        continue
      if not (_is_entity_term(ent) and (_is_ground_str(owner) or
              (isinstance(owner, str) and owner.startswith("?:")))):
        continue
      expected_type = rel[:-3]    # strip trailing " of"
      ekey = _entity_key(ent)
      if ekey not in isa_types or expected_type not in isa_types[ekey]:
        continue
      # Prefer the activity-event CT (correct tense) over the possessive CT.
      ct = entity_event_ct.get(ekey, ct_possessive)
      have_atom = ["have", owner, ent]
      if ct is not None:
        have_atom.append(list(ct) if isinstance(ct, list) else ct)
      # For rule clauses with guard literals, emit conditional have
      guard = _extract_guard(clause)
      if guard:
        have_clause = guard + [have_atom]
      else:
        have_clause = have_atom
      key = (str(owner), ekey)
      if key in seen:
        continue
      seen.add(key)
      new_facts.append({"@name": obj.get("@name", "sent_?"), "@logic": have_clause})

  if not new_facts:
    return
  first_q = next((i for i, o in enumerate(result) if "@question" in o), len(result))
  for i, fact in enumerate(new_facts):
    result.insert(first_q + i, fact)


# ======== have → has_part bridge for typed body-part nouns ========

def _parse_entity_name_type(entity):
  """Extract a candidate type string from an entity name using Stage-2 naming
  conventions.  Returns None for non-strings or names without a recognisable
  noun stem.

    "trunk 1"      -> "trunk"      (concrete + numeric suffix)
    "sk0_trunk"    -> "trunk"      (Skolem const with type tag)
    "$some_trunk"  -> "trunk"      (population existential)
    "John 1"       -> "John"       (proper name + suffix)

  Used by add_haspart_for_typed_have as a fallback when the explicit
  isa(T, E) atom is missing from Stage-2 output.
  """
  if not isinstance(entity, str):
    return None
  if entity.startswith("$some_"):
    rest = entity[len("$some_"):]
    if rest.startswith("not_"):
      rest = rest[4:]
    return rest.split("_", 1)[0] if rest else None
  if entity.startswith("sk") and "_" in entity:
    return entity.split("_", 1)[1] or None
  parts = entity.split()
  return parts[0] if parts else None


def add_haspart_for_typed_have(result):
  """Bridge specific have-facts to has_part when a rule uses has_part on the
  same noun type.  Conservative: fires only when the problem contains a
  has_part-using rule whose typed premise matches the have-fact's possessee.

  Motivating example (case 207):
    Rule:  "If an animal has a trunk, it is an elephant."
           Stage-2 clause uses has_part:
             [-isa(animal,?:X), -isa(trunk,?:Y), -has_part(?:X,?:Y,Ctxt),
              isa(elephant,?:X), $block, ...]
    Fact:  "John has a long trunk."
           Stage-2 (gemini/gpt) uses have, not has_part:
             have(John 1, trunk 1, Ctxt), isa(trunk, trunk 1)
    Query: "John is an elephant?" → Unknown (rule never fires because
           has_part(John 1, trunk 1, …) is not asserted).

  This bridge scans the rule clauses and finds the type "trunk" is paired
  with has_part.  It then sees have(John 1, trunk 1, …) where trunk 1 has
  isa(trunk, …), matching the rule's expected type, and emits the missing
  has_part(John 1, trunk 1, Ctxt).  The rule then fires → True.

  Conservatism:
  - RULE_HASPART_TYPES is local to the current problem — only types
    explicitly used in a has_part-typed rule premise here qualify.
  - For "John has a book" with no has_part rule about books, nothing fires.
  - For a hypothetical rule about "has_part friend", "John has a friend"
    would correctly fire.

  Name-parsing fallback (_parse_entity_name_type):
  - When the explicit isa(T, Y_const) atom is missing from Stage-2 output,
    parse the entity name (e.g. "trunk 1" → "trunk", "sk0_trunk" → "trunk")
    as a fallback type.  Removes the dependency on LLM reliably emitting
    isa, while remaining safe (still gated by RULE_HASPART_TYPES).
  """
  def _is_var(s):
    return isinstance(s, str) and s.startswith("?:")

  def _is_ground_str(v):
    return isinstance(v, str) and not v.startswith("?:")

  def _is_entity_term(v):
    if _is_ground_str(v):
      return True
    if isinstance(v, list) and len(v) >= 2 and isinstance(v[0], str):
      return v[0].startswith("sk") or v[0] == "$theof1"
    return False

  def _entity_key(v):
    return str(v) if isinstance(v, list) else v

  def _extract_atoms(clause):
    if not isinstance(clause, list) or not clause:
      return []
    if isinstance(clause[0], list):
      return clause
    if isinstance(clause[0], str):
      return [clause]
    return []

  # Pass 1: scan rule clauses for has_part-typed premises.
  # A "has_part-typed rule" is a multi-literal clause containing both
  # ["-has part", ?:X, ?:Y, …] and ["-isa", T, ?:Y] for the same ?:Y.
  rule_haspart_types = set()
  for obj in result:
    if not isinstance(obj, dict) or "@logic" not in obj:
      continue
    clause = obj["@logic"]
    if not (isinstance(clause, list) and clause and isinstance(clause[0], list)):
      continue   # not a multi-literal rule
    # collect ?:Y vars that appear as second arg of -has part
    haspart_vars = set()
    for atom in clause:
      if (isinstance(atom, list) and len(atom) >= 3
          and atom[0] == "-has part" and _is_var(atom[2])):
        haspart_vars.add(atom[2])
    if not haspart_vars:
      continue
    # for each such ?:Y, find -isa(T, ?:Y) in the same clause
    for atom in clause:
      if (isinstance(atom, list) and len(atom) >= 3
          and atom[0] == "-isa"
          and isinstance(atom[1], str)
          and atom[2] in haspart_vars):
        rule_haspart_types.add(atom[1])

  if not rule_haspart_types:
    return   # no has_part-typed rule in this problem; bridge would fire on nothing

  # Pass 2: collect explicit isa(T, E) for ground/function-term entities.
  isa_types = {}
  for obj in result:
    if not isinstance(obj, dict) or "@logic" not in obj:
      continue
    for atom in _extract_atoms(obj["@logic"]):
      if (isinstance(atom, list) and len(atom) >= 3
          and atom[0] == "isa"
          and isinstance(atom[1], str) and _is_entity_term(atom[2])):
        isa_types.setdefault(_entity_key(atom[2]), set()).add(atom[1])

  # Pass 3: walk single-atom positive have facts and emit has_part where
  # the possessee's type matches a rule's has_part-typed premise.
  new_facts = []
  seen = set()
  for obj in result:
    if not isinstance(obj, dict) or "@logic" not in obj:
      continue
    clause = obj["@logic"]
    if not (isinstance(clause, list) and clause and isinstance(clause[0], str)
            and clause[0] == "have" and len(clause) >= 3):
      continue   # not a single-atom positive have fact
    x_const, y_const = clause[1], clause[2]
    if not _is_entity_term(y_const):
      continue
    ekey = _entity_key(y_const)
    types = set(isa_types.get(ekey, ()))
    if not types:
      parsed = _parse_entity_name_type(y_const)
      if parsed:
        types = {parsed}
    if not (types & rule_haspart_types):
      continue
    # Build has_part atom with the same Ctxt (4th arg) if present.
    haspart = ["has part", x_const, y_const]
    if len(clause) > 3:
      haspart.append(clause[3])
    key = (str(x_const), ekey)
    if key in seen:
      continue
    seen.add(key)
    new_facts.append({"@name": obj.get("@name", "sent_?"), "@logic": haspart})

  if not new_facts:
    return
  first_q = next((i for i, o in enumerate(result) if "@question" in o), len(result))
  for i, fact in enumerate(new_facts):
    result.insert(first_q + i, fact)


# ======== degree-predicate stripping (noproptypes_flag) ========

def strip_degree_predicates(result):
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
    # [pred, PROP, ENTITY, DEGREE, RELCLASS, ctx?] -> [simple_pred, PROP, ENTITY, ctx?]
    result = [pfx + "has property", frm[1], frm[2]]
    # Preserve context argument (last element) if present beyond RELCLASS.
    # Full form: [pred, PROP, ENTITY, DEGREE, RELCLASS, CTXT] — 6 elements.
    if len(frm) >= 6:
      result.append(frm[5])
    return result

  if base == "has degree rel2" and len(frm) >= 4:
    # [pred, REL, E1, E2, DEGREE, RELCLASS, ctx?] -> [simple_pred, REL, E1, E2, ctx?]
    result = [pfx + "is rel2", frm[1], frm[2], frm[3]]
    # Full form: [pred, REL, E1, E2, DEGREE, RELCLASS, CTXT] — 7 elements.
    if len(frm) >= 7:
      result.append(frm[6])
    return result

  # Any other formula/atom: recurse into sub-elements to catch nested occurrences.
  return [frm[0]] + [_strip_deg_frm(a) if isinstance(a, list) else a
                     for a in frm[1:]]


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


