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

# Logical connectives that are NOT predicates.
_connectives = {"and", "or", "not", "implies", "equivalent", "xor", "forall", "exists"}

# Opaque wrappers: clausification does not recurse inside these.
# Variable renaming (outer varmap) is still applied to their contents.
_opaque_wrappers = {"normally", "-normally"}

# Counter for Skolem function/constant names (reset per top-level call).
_skolem_nr = 0

# Counter for $defq predicate names (reset per top-level call).
_defq_nr = 0


# ======== main entry point ========

def rawlogic_convert(logic):
  """Convert stage-2 LLM output to a GK-compatible clause list.

  Input:  stage-2 list ["and", ["@id","S1",PACKAGE], ...]
  Output: list of {"@name":..., "@logic":CLAUSE} / {"@name":..., "@question":F}
  Returns None on fatal error.
  """
  global _skolem_nr, _defq_nr
  _skolem_nr = 0          # reset once for the whole conversion
  _defq_nr   = 0
  if not logic or not isinstance(logic, list):
    return None

  if logic[0] == "@id":
    items = [logic]
  elif logic[0] == "and":
    items = logic[1:]
  else:
    return None

  result = []
  for item in items:
    objs = _convert_id_package(item)
    if objs:
      result.extend(objs)  
  return result


# ======== package extraction ========

def _convert_id_package(item):
  """Process ["@id", sid, PACKAGE] → list of GK clause dicts."""
  if not isinstance(item, list) or len(item) < 3 or item[0] != "@id":
    return []
  sid = item[1]
  package = item[2]
  name = "sent_" + str(sid)

  is_question, formula, confidence = _extract_package(package)
  if formula is None:
    return []

  if is_question:
    # Distinguish wh-questions (["ask", var, body]) from yes/no questions.
    if isinstance(formula, list) and len(formula) >= 3 and formula[0] == "ask":
      ask_var = str(formula[1])
      body    = formula[2]
      if _is_simple_question_formula(body):
        # Single atom with ≤1 variable: direct @question, no $defq wrapper.
        free_vars_in_body = sorted(_collect_body_free_vars(body))
        varmap = {ask_var: "?:" + ask_var}
        varmap.update({v: "?:" + v for v in free_vars_in_body})
        flat = _flatten_q_atoms(body, varmap)
        if not flat:
          return []
        q_formula = flat[0] if len(flat) == 1 else [["and"] + flat]
        return [{"@name": name, "@question": q_formula, "@askvars": 1}]
      else:
        # Complex case: wrap in $defq biconditional.
        return _build_defq_question(name, ask_var, body)
    else:
      # Yes/no question.
      if _is_simple_question_formula(formula):
        # Single atom with ≤1 variable: direct @question, no $defq wrapper.
        free_vars_in_formula = sorted(_collect_body_free_vars(formula))
        varmap = {v: "?:" + v for v in free_vars_in_formula}
        flat = _flatten_q_atoms(formula, varmap)
        if not flat:
          return []
        q_formula = flat[0] if len(flat) == 1 else [["and"] + flat]
        return [{"@name": name, "@question": q_formula}]
      else:
        # Complex case: wrap in $defq biconditional.
        return _build_defq_question(name, None, formula)

  # Clausify the formula.
  clauses = _clausify(formula)
  result = []
  for clause in clauses:
    obj = {"@name": name, "@logic": clause}
    if confidence is not None:
      obj["@confidence"] = confidence
    result.append(obj)
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


# ======== clausification ========

def _clausify(formula):
  """Convert a formula to a list of GK clauses (CNF).

  Returns a list of clauses, where each clause is either:
    - a single atom: ["pred", arg, ...]
    - a list of atoms (disjunction): [["pred1",...], ["pred2",...], ...]
  """
  f1 = _implies_to_or(formula)
  f2 = _push_neg(f1, True)
  f3 = _skolemize(f2, [], {})
  f4 = _distribute(f3)
  return _extract_clauses(f4)


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

  Variable names in stage-2 LLM output are uppercase-initial identifiers
  without spaces, e.g. X, Y, Z, S1, Var.  Strings starting with '?:' are
  already in GK format and also count as variables.
  Constants are either lowercase ('car', 'elephant'), numbered ('John 1',
  'car 2'), or URLs — none of which match the pattern.
  """
  if not isinstance(s, str) or ' ' in s:
    return False
  if s.startswith('?:'):
    return True
  return bool(re.match(r'^[A-Z][A-Za-z0-9]*$', s))


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


def _build_defq_question(name, ask_var, body):
  """Build $defq biconditional @logic clauses and a @question entry.

  For a wh-question (ask_var is not None, e.g. "X"):
    Constructs:  forall X. ($defq0(X) <=> exists Ys. body)
    Emits:       @logic clauses (with @sourcetype:"question") from the CNF
                 @question: [$defq0, ?:X]  with @askvars: 1

  For a yes/no question (ask_var is None):
    Constructs:  $defq0() <=> body
    Emits:       @logic clauses (with @sourcetype:"question") from the CNF
                 @question: [$defq0]

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
    defq_atom = [defq_name, ask_var]
    frm = ["forall", ask_var, ["equivalent", defq_atom, wrapped_body]]
    q_atom = [defq_name, "?:" + ask_var]
    askvars = 1
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
  result.append(q_obj)
  return result


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


# =========== the end ==========
