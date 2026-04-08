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
    # [pred, PROP, ENTITY, DEGREE, RELCLASS] -> [simple_pred, PROP, ENTITY]
    return [pfx + "has property", frm[1], frm[2]]

  if base == "has degree rel2" and len(frm) >= 4:
    # [pred, REL, E1, E2, DEGREE, RELCLASS] -> [simple_pred, REL, E1, E2]
    return [pfx + "is rel2", frm[1], frm[2], frm[3]]

  # Any other formula/atom: recurse into sub-elements to catch nested occurrences.
  return [frm[0]] + [_strip_deg_frm(a) if isinstance(a, list) else a
                     for a in frm[1:]]


