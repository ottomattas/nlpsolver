# Atom-to-English rendering for proof explanations.
#
# Converts CNF proof atoms and clauses into readable English sentences.
# Table-driven predicate dispatch via _PRED_TABLE.
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

import json
import re

from lc_clausify import is_skolem_const, is_skolem_fn

from linguistics import (
  indef_article  as _indef_article,
  conjugate_verb as _conjugate_verb,
  make_comparative as _make_comparative,
  to_gerund      as _to_gerund,
  looks_like_verb as _looks_like_verb,
  PREPOSITIONS   as _PREPOSITIONS,
)

from proof_utils import (
  entity_name, _ctx, _degree_parts, _is_var_display,
  _ans_display_args, _SAFE_LETTERS,
)

import globals as _g


def ans_atom_name(atom):
  """Return the display name from a $ans atom like ["$ans", "John 1"].

  Used for the answer line — URLs appear without the parenthetical URL
  unless the display name is ambiguous (maps to 2+ different URLs).
  """
  if not isinstance(atom, list) or len(atom) < 2:
    return str(atom)
  val = atom[1]
  if isinstance(val, list) and val:
    return render_term_english(val)
  if not isinstance(val, str):
    return str(val)
  # with_url=False: only append URL when the name is ambiguous
  return entity_name(val, with_url=False)


# ======== clause / atom rendering ========
# Converts CNF proof clauses to readable English.
# A clause is a list of atoms (disjunction); atoms with a "-" prefix are negated.
# Negated atoms are rendered as "if" conditions; positive atoms as "then" consequences.
# _atom_to_english handles every predicate in the stage-2 whitelist.

def _forall_or_to_english(frm):
  """Render ["forall", VAR, ["or", ["-isa", TYPE, VAR], CONCL]] as English.

  This is the GK encoding of ∀VAR.(TYPE(VAR) → CONCL), i.e. "all TYPEs are ...".
  Returns a string, or None if the pattern does not match.
  """
  if not (isinstance(frm, list) and len(frm) == 3 and frm[0] == "forall"):
    return None
  var  = frm[1]
  body = frm[2]
  if not (isinstance(body, list) and body and body[0] == "or"):
    return None
  # Find the -isa(TYPE, VAR) guard and the positive conclusion atom(s)
  neg_isa = None
  concls  = []
  for el in body[1:]:
    if (isinstance(el, list) and el and el[0] == "-isa"
        and len(el) >= 3 and el[2] == var):
      neg_isa = el
    else:
      concls.append(el)
  if neg_isa is None or not concls:
    return None
  typ = str(neg_isa[1])

  def _concl_pred(c):
    """Render a conclusion atom without its subject (the universal variable)."""
    if not isinstance(c, list) or not c:
      return str(c)
    p = str(c[0])
    neg = p.startswith("-")
    base = p[1:] if neg else p
    # has degree property: [pred, PROP, ENTITY(=VAR), DEGREE, RELCLASS]
    if base == "has degree property" and len(c) >= 3 and c[2] == var:
      adv, _ = _degree_parts(entity_name(c[3]) if len(c) > 3 else "")
      prop = str(c[1])
      prefix = "not " if neg else ""
      return prefix + adv + prop
    # has property: [pred, PROP, ENTITY(=VAR)]
    if base == "has property" and len(c) >= 3 and c[2] == var:
      prop = str(c[1])
      return ("not " if neg else "") + prop
    # fallback to full atom rendering
    base_atom = [base] + list(c[1:])
    return _atom_to_english_negated(base_atom) if neg else _atom_to_english(c)

  concl_text = " and ".join(_concl_pred(c) for c in concls)
  return "all " + typ + "s are " + concl_text


def block_to_english(block_atom):
  """Render a $block atom as an English exception string.

  Structure: ["$block", PRIORITY, ["$not", INNER]]
  Returns the negated rendering of INNER, or "" if malformed.
  """
  if not isinstance(block_atom, list) or len(block_atom) < 3:
    return ""
  inner = block_atom[2]
  if not (isinstance(inner, list) and inner and inner[0] == "$not"
          and len(inner) > 1 and isinstance(inner[1], list)):
    if isinstance(inner, list):
      return _atom_to_english(inner)
    return str(inner)
  body = inner[1]
  # Special case: forall-or pattern encodes a universal rule head.
  foe = _forall_or_to_english(body)
  if foe is not None:
    return "not: " + foe
  return _atom_to_english_negated(body)



# Traditional/JSON logic rendering (in proof_logic.py).
from proof_logic import (
  format_clause_logic, format_clause_traditional, formula_to_logic,
)


def _defq_ans_bridge(clause):
  """Detect the $defq/$ans bridge pattern in a 2-atom clause.

  Returns 'unwrap' for [-$defq*(args...), $ans(args...)]  -- defq drives ans
  Returns 'wrap'   for [$defq*(args...), -$ans(args...)]  -- ans drives defq
  Returns None otherwise (including wrong atom count or mismatched args).

  Both orderings (a,b) and (b,a) are checked.
  """
  if not isinstance(clause, list) or len(clause) != 2:
    return None
  a, b = clause[0], clause[1]
  if not isinstance(a, list) or not isinstance(b, list) or not a or not b:
    return None
  for first, second in [(a, b), (b, a)]:
    pa = str(first[0]);  args_a = first[1:]
    pb = str(second[0]); args_b = second[1:]
    if args_a != args_b:
      continue
    if pa.startswith("-$defq") and pb == "$ans":
      return "unwrap"
    if pa.startswith("$defq") and pb == "-$ans":
      return "wrap"
  return None


def clause_to_str(clause):
  """Convert a proof clause to a human-readable if-then English string."""
  if clause is False or clause is None:
    return "Contradiction"
  if not isinstance(clause, list):
    return str(clause)

  # Detect the contradiction-assumption step: a single negated $defq* atom,
  # which represents the refutation assumption "suppose the answer is no".
  if (len(clause) == 1 and isinstance(clause[0], list) and clause[0] and
      isinstance(clause[0][0], str) and clause[0][0].startswith("-$defq")):
    if len(clause[0]) <= 1:
      return "assume for contradiction: the answer is no"
    else:
      return "assume for contradiction: no such answer exists"

  # Detect the $defq/$ans bridge step that connects the internal answer
  # marker to the output answer atom (or vice versa).
  bridge = _defq_ans_bridge(clause)
  if bridge == "unwrap":
    return "technical answer unwrap step"
  if bridge == "wrap":
    return "technical answer wrap step"

  conditions    = []   # positively-rendered negated atoms -> "if ..."
  neg_atoms     = []   # base atoms (pred without "-") for pure-negative rendering
  consequences  = []   # (english_str, is_normally) pairs for positive atoms
  raw_pos_atoms = []   # raw positive atoms (for $block matching)
  block_atoms   = []   # raw $block atoms
  blocker_texts = []   # "except when ..." rendered from unmatched $block atoms

  for atom in clause:
    if not isinstance(atom, list) or not atom:
      continue
    pred = str(atom[0])
    if pred == "$block":
      block_atoms.append(atom)
    elif pred == "$ans":
      meaningful = _ans_display_args(atom[1:])
      if len(meaningful) >= 2:
        bracket = "[" + ", ".join(entity_name(a, with_url=True) for a in meaningful) + "]"
        consequences.append((bracket + " is an answer", False))
      elif meaningful:
        consequences.append((entity_name(meaningful[0]) + " is an answer", False))
      else:
        consequences.append((ans_atom_name(atom) + " is an answer", False))
      raw_pos_atoms.append(atom)
    elif pred.startswith("-"):
      base = [pred[1:]] + list(atom[1:])
      conditions.append(_atom_to_english(base))
      neg_atoms.append(base)
    else:
      consequences.append((_atom_to_english(atom), False))
      raw_pos_atoms.append(atom)

  # Detect standard defeasible pattern: $block body matches a positive conclusion.
  # When matched, render the conclusion with "normally" instead of appending
  # "except when ..." (which redundantly restates the conclusion's negation).
  matched_blocks = set()
  for bi, block in enumerate(block_atoms):
    if (isinstance(block, list) and len(block) >= 3
        and isinstance(block[2], list) and block[2] and block[2][0] == "$not"
        and len(block[2]) > 1):
      body = block[2][1]
      for ci, raw_atom in enumerate(raw_pos_atoms):
        if raw_atom == body:
          # Mark this consequence as defeasible and this $block as matched.
          text, _ = consequences[ci]
          consequences[ci] = (text, True)
          matched_blocks.add(bi)
          break

  # Unmatched $blocks get rendered as "except when ..." (post-resolution cases).
  for bi, block in enumerate(block_atoms):
    if bi not in matched_blocks:
      bt = block_to_english(block)
      if bt:
        blocker_texts.append(bt)

  # Deduplicate identical condition strings (e.g. isa(man,X) and
  # has_degree_property(strong,X,none,man) may both render as "X is a man").
  conditions = list(dict.fromkeys(conditions))

  # Build consequence text, prepending "normally" to defeasible conclusions.
  cons_parts = []
  for text, is_normally in consequences:
    cons_parts.append("normally " + text if is_normally else text)

  if conditions and cons_parts:
    result = "if " + " and ".join(conditions) + " then " + " or ".join(cons_parts)
  elif cons_parts:
    result = " or ".join(cons_parts)
  elif conditions:
    if len(conditions) == 1:
      # Single negated atom: render in natural negated form.
      result = _atom_to_english_negated(neg_atoms[0])
    else:
      # Multi-atom pure-negative clause ¬A₁ ∨ … ∨ ¬Aₙ is logically equivalent
      # to A₁ ∧ … ∧ Aₙ₋₁ → ¬Aₙ.  Render as "if A₁ and … then not-Aₙ".
      result = ("if " + " and ".join(conditions[:-1]) +
                " then " + _atom_to_english_negated(neg_atoms[-1]))
  elif blocker_texts:
    # Clause is purely $block atoms — outstanding exception(s) still to be ruled out.
    return "outstanding exception: " + " and ".join(blocker_texts)
  else:
    result = "(empty)"

  if blocker_texts:
    result += ", except when " + " and ".join(blocker_texts)

  return result


# ======== atom-to-English converters ========
#
# Table-driven dispatch: each predicate has a (min_args, pos_fn, neg_fn) entry.
# pos_fn(e, args) returns the positive English string.
# neg_fn(e, args) returns the negated English string.
# Complex predicates use dedicated helpers; simple ones use inline lambdas.

def _isa_pos(e, args):
  # Use raw type string to avoid entity_map turning "man" into "the strong man".
  typ = str(args[0]) if args else e(0)
  ent = e(1)
  if typ == "activity": return ent + " is an activity"
  if typ == "set":      return ent + " is a set"
  return ent + " is " + _indef_article(typ) + " " + typ

def _isa_neg(e, args):
  typ = str(args[0]) if args else e(0)
  ent = e(1)
  if typ == "activity": return ent + " is not an activity"
  if typ == "set":      return ent + " is not a set"
  return ent + " is not " + _indef_article(typ) + " " + typ

def _is_rel2_pos(e, args):
  rel = e(0)
  last = rel.split()[-1].lower() if rel else ""
  if rel.lower() in _PREPOSITIONS or last in _PREPOSITIONS or last == "of":
    return e(1) + " is " + rel + " " + e(2)
  if _looks_like_verb(rel):
    return e(1) + " " + _conjugate_verb(rel) + " " + e(2)
  return e(1) + " is " + rel + " of " + e(2)

def _is_rel2_neg(e, args):
  rel = e(0)
  last = rel.split()[-1].lower() if rel else ""
  if rel.lower() in _PREPOSITIONS or last in _PREPOSITIONS or last == "of":
    return e(1) + " is not " + rel + " " + e(2)
  if _looks_like_verb(rel):
    return e(1) + " does not " + rel + " " + e(2)
  return e(1) + " is not " + rel + " of " + e(2)

def _has_degree_property_render(e, args, neg=False):
  prop = e(0); ent = e(1)
  adv, art_type = _degree_parts(e(2))
  relcls_raw = args[3] if len(args) > 3 else ""
  cop = " is not " if neg else " is "
  # Omit relclass when it's a variable, "none", or "entity" — these carry no
  # useful comparison-class info and produce ugly English like "a big none".
  if isinstance(relcls_raw, str) and (relcls_raw.startswith("?:")
      or relcls_raw in ("none", "entity")):
    return ent + cop + adv + prop
  # Omit relclass when it matches the entity's base noun — avoids redundancy
  # like "the mouse is a very big mouse" → "the mouse is very big".
  ent_raw = args[1] if len(args) > 1 else ""
  if isinstance(ent_raw, str) and isinstance(relcls_raw, str):
    ent_base = re.match(r'^(.*\S)\s+\d+$', ent_raw)
    if ent_base and ent_base.group(1).lower() == relcls_raw.lower():
      return ent + cop + adv + prop
  # Use the raw relclass string (not entity_name) to avoid entity_map lookup
  # turning class names like "man" into "the strong man".
  relcls = str(relcls_raw)
  art = "the" if art_type == "def" else _indef_article(adv if adv else prop)
  return ent + cop + art + " " + adv + prop + " " + relcls

def _has_degree_rel2_render(e, args, neg=False):
  rel = e(0); ent1 = e(1); ent2 = e(2)
  degree_raw = str(args[3]).lower() if len(args) > 3 else "none"
  last = rel.split()[-1].lower() if rel else ""
  cop = " is not " if neg else " is "
  if last in _PREPOSITIONS or last == "of":
    return ent1 + cop + rel + " " + ent2
  if _is_var_display(rel):
    if neg: return ent1 + " does not have a " + rel + "-relation with " + ent2
    return ent1 + " has a " + rel + "-relation with " + ent2
  if degree_raw in ("high", "more"):
    return ent1 + cop + _make_comparative(rel) + " than " + ent2
  if degree_raw == "most":
    return ent1 + cop.rstrip() + " the most " + rel + " of all compared to " + ent2
  if degree_raw in ("low", "less"):
    return ent1 + cop + "less " + rel + " than " + ent2
  if degree_raw == "least":
    return ent1 + cop.rstrip() + " the least " + rel + " of all compared to " + ent2
  return ent1 + cop + rel + " of " + ent2

def _is_var_raw(args, i):
  """True if args[i] is a raw variable string (starts with '?:')."""
  return (len(args) > i and isinstance(args[i], str) and args[i].startswith("?:"))

def render_term_english(term):
  """Render a complex list term (nested function/predicate) as English.

  Handles $count, $setof, TPTP arithmetic ($sum, $difference, $product,
  $quotient), and infix arithmetic (+, -, *, /).
  Falls back to str() for unrecognized terms.
  """
  if not isinstance(term, list) or not term:
    return str(term)

  op = term[0]

  # $datetime -> just the value
  if op == "$datetime" and len(term) >= 2:
    return str(term[1])

  # $theof1 -> "the TYPE of SUBJECT"
  if op == "$theof1" and len(term) >= 3:
    type_name = term[1] if isinstance(term[1], str) else str(term[1])
    subj = entity_name(term[2], proof_mode=True)
    return "the " + type_name + " of " + subj

  # $measure_of -> "the TYPE of SUBJECT"
  if op == "$measure_of" and len(term) >= 3:
    type_name = term[1] if isinstance(term[1], str) else str(term[1])
    subj = entity_name(term[2], proof_mode=True)
    return "the " + type_name + " of " + subj

  # $measure -> "80 kilometers" (original form, before canonicalization)
  if op == "$measure" and len(term) == 3:
    return str(term[1]) + " " + str(term[2]) + "s"

  # $list with number + #:unit -> "80000 meters"
  if op == "$list" and len(term) == 3:
    val = term[1]
    unit = term[2]
    if isinstance(unit, str) and unit.startswith("#:"):
      unit_name = unit[2:]  # strip #: prefix
      return str(val) + " " + unit_name + "s"
    return str(val) + " " + str(unit)

  # $count -> "the number of ..."
  if op == "$count" and len(term) >= 2:
    inner = _render_setof_english(term[1])
    return "the number of " + inner

  # $setof -> delegate
  if op == "$setof":
    return _render_setof_english(term)

  # TPTP prefix arithmetic functions
  _ARITH_PREFIX = {
    "$sum": "+", "$difference": "-", "$product": "*", "$quotient": "/",
    "$quotient_e": "/", "$remainder_e": "mod", "$remainder_t": "mod",
    "$remainder_f": "mod", "$uminus": "-",
    "$floor": "floor", "$ceiling": "ceiling",
    "$truncate": "truncate", "$round": "round",
    "$to_int": "int", "$to_real": "real",
  }
  if op in _ARITH_PREFIX and len(term) >= 2:
    if op == "$uminus":
      return "-" + entity_name(term[1], proof_mode=True)
    if len(term) == 2:
      # Unary: $floor(X) etc
      return _ARITH_PREFIX[op] + "(" + entity_name(term[1], proof_mode=True) + ")"
    a = entity_name(term[1], proof_mode=True)
    b = entity_name(term[2], proof_mode=True)
    return a + " " + _ARITH_PREFIX[op] + " " + b

  # Infix arithmetic: [A, "+", B] etc
  if len(term) == 3 and isinstance(term[1], str) and term[1] in ("+", "-", "*", "/"):
    a = entity_name(term[0], proof_mode=True)
    b = entity_name(term[2], proof_mode=True)
    return a + " " + term[1] + " " + b

  return str(term)


def _render_setof_english(term):
  """Render a $setof term as English.

  Fully concrete (anchor + subject + $isa in conditions):
    $setof(have, John 1, [$and, $isa(car,$arg1)]) -> "cars John has"
    $setof(have, John 1, [$and, $isa(car,$arg1), $has_degree_property(nice,...)]) -> "nice cars John has"

  Partially concrete (anchor + subject concrete, some variable conditions):
    $setof(have, John 1, [$and, $isa(car,$arg1), ?:Y]) -> "cars John has that satisfy Y"

  All variables (generic axiom):
    $setof(?:Y, ?:Z, [$and, ?:U, ?:V]) -> "a set of things satisfying conditions U and V"
  """
  if not isinstance(term, list) or not term or term[0] != "$setof" or len(term) < 3:
    return str(term)

  # Parse canonical $setof form
  if term[1] == "id":
    # Conditions-only: ["$setof", "id", SET_ID, ["$and", ...]]
    set_id = term[2]
    conds = term[3] if len(term) > 3 else []
    type_name = _extract_type_from_conds(conds)
    return type_name + " in " + str(set_id)

  # Anchored: ["$setof", PRED, SUBJ, ["$and", ...]]
  pred = term[1]
  subj = term[2] if len(term) > 2 else "?"
  conds = term[3] if len(term) > 3 else term[2]

  pred_is_var = isinstance(pred, str) and pred.startswith("?:")
  subj_is_var = isinstance(subj, str) and subj.startswith("?:")

  # All variables -> generic description
  if pred_is_var and subj_is_var:
    cond_str = _render_and_conditions(conds)
    return "a set of things satisfying " + cond_str

  # Concrete anchor/subject -> try to produce natural English
  type_name, props, extra_vars = _extract_type_and_props(conds)
  subj_name = entity_name(subj, proof_mode=True)

  # Build the base: "nice cars John has"
  if props:
    desc = " ".join(props) + " " + type_name
  else:
    desc = type_name

  if pred == "have":
    base = desc + " " + subj_name + " has"
  elif pred == "can":
    base = desc + " that can " + str(conds)
  else:
    base = desc + " " + pred + " " + subj_name

  # Append unresolved variable conditions
  if extra_vars:
    var_str = " and ".join(entity_name(v, proof_mode=True) for v in extra_vars)
    base += " that satisfy " + var_str

  return base


def _extract_type_and_props(conds):
  """Extract type name, property adjectives, and unresolved variable conditions.

  Returns (type_name, props_list, extra_vars_list).
  """
  if not isinstance(conds, list) or not conds:
    return "things", [], []
  items = conds[1:] if conds[0] in ("$and", "and") else [conds]

  type_name = "things"
  props = []
  extra_vars = []

  for item in items:
    if isinstance(item, str) and item.startswith("?:"):
      extra_vars.append(item)
      continue
    if not isinstance(item, list) or len(item) < 2:
      continue
    pred = item[0]
    if pred in ("$isa", "isa") and isinstance(item[1], str):
      type_name = item[1] + "s"
    elif pred in ("$has_degree_property", "has degree property") and len(item) >= 3:
      # Extract the adjective name
      adj = item[1] if isinstance(item[1], str) and not item[1].startswith("?:") else None
      if adj:
        props.append(adj)
      else:
        extra_vars.append(item)
    else:
      # Skip $arg1-only predicates (like $have which duplicates the anchor)
      pass

  return type_name, props, extra_vars


def _render_and_conditions(conds):
  """Render $and conditions as a readable string.

  Variable conditions: "conditions U and V"
  Mixed: "conditions $isa(car, ...) and V"
  """
  if not isinstance(conds, list) or not conds:
    return "conditions " + str(conds)
  items = conds[1:] if conds[0] in ("$and", "and") else [conds]

  parts = []
  for item in items:
    if isinstance(item, str) and item.startswith("?:"):
      parts.append(entity_name(item, proof_mode=True))
    elif isinstance(item, str):
      parts.append(item)
    else:
      parts.append(str(item))

  if len(parts) == 1:
    return "condition " + parts[0]
  return "conditions " + " and ".join(parts)


def _extract_type_from_conds(conds):
  """Extract the type name from a $and conditions list."""
  type_name, _, _ = _extract_type_and_props(conds)
  return type_name


def _render_member(e, args, negated):
  """Render member atom, with special handling for $setof set terms."""
  if len(args) >= 2 and isinstance(args[1], list) and args[1] and args[1][0] == "$setof":
    set_desc = _render_setof_english(args[1])
    ent = e(0)
    if negated:
      return ent + " is not among " + set_desc
    return ent + " is among " + set_desc
  if negated:
    return e(0) + " is not a member of " + e(1)
  return e(0) + " is a member of " + e(1)


def _render_equals(e, args, negated):
  """Render an = atom, with special handling for $count terms."""
  # Check if either argument is a $count term
  for i in (0, 1):
    val = args[i]
    other = args[1 - i]
    if isinstance(val, list) and val and val[0] == "$count":
      set_desc = render_term_english(val)
      other_name = entity_name(other, proof_mode=True)
      if negated:
        return set_desc + " is not " + other_name
      return set_desc + " is " + other_name
  # Default: plain equals
  if negated:
    return e(0) + " does not equal " + e(1)
  return e(0) + " equals " + e(1)


# Predicate dispatch table: pred -> (min_args, pos_fn, neg_fn)
# pos_fn / neg_fn signature: (e, args) -> str
_PRED_TABLE = {
  # core predicates
  "has property":       (2, lambda e,a: e(1)+" is "+e(0),
                            lambda e,a: e(1)+" is not "+e(0)),
  "have":               (2, lambda e,a: e(0)+" has "+e(1),
                            lambda e,a: e(0)+" does not have "+e(1)),
  "has part":           (2, lambda e,a: e(0)+" has "+e(1)+" as a part",
                            lambda e,a: e(0)+" does not have "+e(1)+" as a part"),
  "can":                (2, lambda e,a: e(0)+" can "+e(1),
                            lambda e,a: e(0)+" cannot "+e(1)),
  # predicates with complex logic
  "isa":                (2, _isa_pos, _isa_neg),
  "is rel2":            (3, _is_rel2_pos, _is_rel2_neg),
  "has degree property":(4, lambda e,a: _has_degree_property_render(e, a, neg=False),
                            lambda e,a: _has_degree_property_render(e, a, neg=True)),
  "has degree rel2":    (4, lambda e,a: _has_degree_rel2_render(e, a, neg=False),
                            lambda e,a: _has_degree_rel2_render(e, a, neg=True)),
  # event reification predicates
  "has type":           (2, lambda e,a: e(0)+" is a "+e(1)+" event",
                            lambda e,a: e(0)+" is not a "+e(1)+" event"),
  "has actor":          (2, lambda e,a: e(1)+" performs "+e(0),
                            lambda e,a: e(1)+" does not perform "+e(0)),
  "has target":         (2, lambda e,a: e(0)+" targets "+e(1),
                            lambda e,a: e(0)+" does not target "+e(1)),
  "has location":       (3, lambda e,a: e(0)+" takes place "+e(2)+" "+e(1),
                            lambda e,a: e(0)+" does not take place "+e(2)+" "+e(1)),
  "has instrument":     (2, lambda e,a: e(0)+" uses "+e(1),
                            lambda e,a: e(0)+" does not use "+e(1)),
  "has manner":         (2, lambda e,a: e(0)+" happens in a "+e(1)+" manner",
                            lambda e,a: e(0)+" does not happen in a "+e(1)+" manner"),
  "has direction":      (2, lambda e,a: e(0)+" goes towards "+e(1),
                            lambda e,a: e(0)+" does not go towards "+e(1)),
  "has destination":    (2, lambda e,a: e(0)+" goes to "+e(1),
                            lambda e,a: e(0)+" does not go to "+e(1)),
  "has recipient":      (2, lambda e,a: e(0)+" is given to "+e(1),
                            lambda e,a: e(0)+" is not given to "+e(1)),
  "has source":         (2, lambda e,a: e(0)+" comes from "+e(1),
                            lambda e,a: e(0)+" does not come from "+e(1)),
  "has beneficiary":    (2, lambda e,a: e(0)+" is for "+e(1),
                            lambda e,a: e(0)+" is not for "+e(1)),
  "has accompaniment":  (2, lambda e,a: e(0)+" is with "+e(1),
                            lambda e,a: e(0)+" is not with "+e(1)),
  "has path":           (2, lambda e,a: e(0)+" goes through "+e(1),
                            lambda e,a: e(0)+" does not go through "+e(1)),
  "has result":         (2, lambda e,a: e(0)+" results in "+e(1),
                            lambda e,a: e(0)+" does not result in "+e(1)),
  "has topic":          (2, lambda e,a: e(0)+" is about "+e(1),
                            lambda e,a: e(0)+" is not about "+e(1)),
  "has cause":          (2, lambda e,a: e(0)+" is caused by "+e(1),
                            lambda e,a: e(0)+" is not caused by "+e(1)),
  "has time":           (3, lambda e,a: e(0)+" happens "+e(2)+" "+("time " if _is_var_raw(a,1) else "")+e(1),
                            lambda e,a: e(0)+" does not happen "+e(2)+" "+("time " if _is_var_raw(a,1) else "")+e(1)),
  # state / world predicates
  "next":               (2, lambda e,a: e(0)+" is followed by "+e(1),
                            lambda e,a: e(0)+" is not followed by "+e(1)),
  "before":             (2, lambda e,a: e(0)+" is before "+e(1),
                            lambda e,a: e(0)+" is not before "+e(1)),
  "state time":         (2, lambda e,a: "at time "+e(1),         None),
  "state location":     (2, lambda e,a: "at location "+e(1),     None),
  # set predicates
  "is set of":          (2, lambda e,a: e(1)+" is a set of "+e(0),
                            lambda e,a: e(1)+" is not a set of "+e(0)),
  "member":             (2, lambda e,a: _render_member(e, a, False),
                            lambda e,a: _render_member(e, a, True)),
  "member has property":(2, lambda e,a: "members of "+e(1)+" are "+e(0),
                            lambda e,a: "members of "+e(1)+" are not "+e(0)),
  "is subset of":       (2, lambda e,a: e(0)+" is a subset of "+e(1),
                            lambda e,a: e(0)+" is not a subset of "+e(1)),
  "set union":          (3, lambda e,a: e(2)+" is the union of "+e(0)+" and "+e(1),
                            None),
  "$count":             (1, lambda e,a: "count of "+e(0),        None),
  # comparison predicates
  "=":                  (2, lambda e,a: _render_equals(e, a, False),
                            lambda e,a: _render_equals(e, a, True)),
  "<":                  (2, lambda e,a: e(0)+" is less than "+e(1),
                            lambda e,a: e(0)+" is not less than "+e(1)),
  ">":                  (2, lambda e,a: e(0)+" is greater than "+e(1),
                            lambda e,a: e(0)+" is not greater than "+e(1)),
  "$less":              (2, lambda e,a: e(0)+" is less than "+e(1),
                            lambda e,a: e(0)+" is not less than "+e(1)),
  "$lesseq":            (2, lambda e,a: e(0)+" is at most "+e(1),
                            lambda e,a: e(0)+" is not at most "+e(1)),
  "$greater":           (2, lambda e,a: e(0)+" is greater than "+e(1),
                            lambda e,a: e(0)+" is not greater than "+e(1)),
  "$greatereq":         (2, lambda e,a: e(0)+" is at least "+e(1),
                            lambda e,a: e(0)+" is not at least "+e(1)),
  "less_measure":       (2, lambda e,a: e(0)+" is less than "+e(1),
                            lambda e,a: e(0)+" is not less than "+e(1)),
  # mental predicates
  "kb":                 (3, lambda e,a: e(1)+" "+e(2)+" that ...", None),
  "kb force":           (0, None,                                  None),
}


def _render_atom(atom, negated=False):
  """Unified atom-to-English renderer.  Dispatches via _PRED_TABLE for most
  predicates; handles special cases (holds, normally, $defq*, etc.) inline.

  negated=False: positive form ("X is Y")
  negated=True:  natural negated form ("X is not Y")
  """
  if not isinstance(atom, list) or not atom:
    return ("not: " + str(atom)) if negated else str(atom)

  pred = str(atom[0])
  args = atom[1:]

  def e(i):
    """Display name of args[i] — proof_mode for simpler common-noun names."""
    if i >= len(args): return "?"
    return entity_name(args[i], with_url=True, proof_mode=True)

  # ---- table-driven dispatch ----
  entry = _PRED_TABLE.get(pred)
  if entry is not None:
    min_args, pos_fn, neg_fn = entry
    if len(args) < min_args:
      return ("not: " if negated else "") + _atom_fallback(atom)
    if negated:
      if neg_fn is not None:
        return neg_fn(e, args)
      return "not: " + (pos_fn(e, args) if pos_fn else _atom_fallback(atom))
    if pos_fn is not None:
      return pos_fn(e, args)
    return _atom_fallback(atom)

  # ---- special predicates requiring recursive dispatch or custom logic ----

  if pred == "typical":
    if len(args) >= 1:
      return (e(0) + " is not typical") if negated else (e(0) + " is typical")
    return "not typical" if negated else "typically"

  if pred == "typically":
    if len(args) >= 2:
      if negated:
        return e(0) + " does not typically " + str(args[1])
      return e(0) + " typically " + _conjugate_verb(str(args[1]))
    return "not typically" if negated else "typically"

  if pred == "holds":
    if len(args) >= 2 and isinstance(args[1], list):
      return _render_atom(args[1], negated=negated)
    return ("not: " if negated else "") + _atom_fallback(atom)

  if pred == "normally":
    if len(args) >= 1 and isinstance(args[0], list):
      return "normally, " + _render_atom(args[0], negated=negated)
    return "normally"

  if pred == "kb holds":
    if len(args) >= 2 and isinstance(args[1], list):
      return _render_atom(args[1], negated=negated)
    return ("not: " if negated else "") + _atom_fallback(atom)

  if pred == "kb says":
    if len(args) >= 3 and isinstance(args[2], list):
      if negated:
        return "not: " + e(1) + " says that " + _render_atom(args[2])
      return e(1) + " says that " + _render_atom(args[2])
    return ("not: " if negated else "") + _atom_fallback(atom)

  if pred == "next":
    return ""

  # ---- $defq* question-definition atoms ----
  if pred.startswith("$defq"):
    if not args:
      return "the answer does not hold" if negated else "answer holds"
    if len(args) == 1:
      return (e(0) + " is not the answer") if negated else (e(0) + " is the answer")
    bracket = "[" + ", ".join(entity_name(a, with_url=True) for a in args) + "]"
    return (bracket + " is not the answer") if negated else (bracket + " is the answer")

  # ---- traceability (skip in English) ----
  if pred in ("@id", "@p", "@definite"):
    if pred == "@id" and len(args) >= 2 and isinstance(args[1], list):
      return _render_atom(args[1], negated=negated)
    return ""

  # ---- fallback ----
  if negated:
    return "not: " + _render_atom(atom)
  return _atom_fallback(atom)


def _atom_fallback(atom):
  """Fallback renderer: pred(arg1, arg2) with underscores as spaces."""
  if not isinstance(atom, list) or not atom:
    return str(atom)
  pred = str(atom[0]).replace("_", " ")
  parts = []
  for a in atom[1:]:
    if isinstance(a, str):
      parts.append(entity_name(a, with_url=True))
    elif isinstance(a, list):
      parts.append(_render_atom(a))
    else:
      parts.append(str(a))
  return pred + "(" + ", ".join(parts) + ")" if parts else pred


def _atom_to_english(atom):
  """Convert a single logic atom to readable English."""
  return _render_atom(atom, negated=False)


def _atom_to_english_negated(atom):
  """Render a single atom in its natural negated English form.

  The atom argument is the BASE atom (predicate name WITHOUT the leading "-").
  """
  return _render_atom(atom, negated=True)


