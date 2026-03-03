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

from globals import options as _g_options

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


# ======== main entry point ========

def rawlogic_convert(logic):
  """Convert stage-2 LLM output to a GK-compatible clause list.

  Input:  stage-2 list ["and", ["@id","S1",PACKAGE], ...]
  Output: list of {"@name":..., "@logic":CLAUSE} / {"@name":..., "@question":F}
  Returns None on fatal error.
  """
  global _skolem_nr, _defq_nr, _fv_nr
  _skolem_nr = 0          # reset once for the whole conversion
  _defq_nr   = 0
  _fv_nr     = 0
  if not logic or not isinstance(logic, list):
    return None

  if logic[0] == "@id":
    items = [logic]
  elif logic[0] == "and":
    items = logic[1:]
  else:
    return None

  # Build population facts by scanning the raw stage-2 input first.
  pop_facts = _populate_clauses(items)

  result = []
  for item in items:
    objs = _convert_id_package(item)
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

  # Fix RELCLASS mismatches in question degree-predicate atoms.
  _coerce_relclass(result)

  # When -simpleproperties / -simple is active, replace degree predicates with
  # their non-gradable equivalents so the prover sees simpler atoms.
  if _g_options.get("noproptypes_flag", False):
    _strip_degree_predicates(result)

  return result


# ======== package extraction ========

def _convert_id_package(item):
  """Process ["@id", sid, PACKAGE] → list of GK clause dicts."""
  if not isinstance(item, list) or len(item) < 3 or item[0] != "@id":
    return []
  sid = item[1]
  package = item[2]
  name = "sent_" + str(sid)

  is_question, formula, confidence, world, location, knower, tense = _extract_package_ctx(package)
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
        result = [{"@name": name, "@question": q_formula, "@askvars": 1}]
      else:
        # Complex case: wrap in $defq biconditional.
        result = _build_defq_question(name, ask_var, body)
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
      # For questions: world from ["@world",W] if Stage 2 forwarded pre_state, else free var.
      # Tense from ["@tense",T] if Stage 2 forwarded ASU.time, else free var.
      situation  = world if world is not None else _fresh_fv()
      tense_term = tense if tense is not None else _fresh_fv()
    else:
      # Situational facts: world from ["holds",W,F]; tense from ["state time",W,T].
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
    knower   -- the HOLDER from a sibling ["kb", K, HOLDER, ...], or None
    tense    -- T from a sibling ["@tense", T] (query tense hint), or
                T from a sibling ["state time", W, T] (situational tense), or None.
               ["@tense"] takes priority if both appear in the same package.
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
    tense_hint = None   # from ["@tense", T] sibling (query tense forwarding)
    world_hint = None   # from ["@world", W] sibling (query pre_state forwarding)
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
      elif elop == "@tense" and len(el) >= 2:
        tense_hint = el[1]
      elif elop == "kb" and len(el) >= 3:
        knower = el[2]   # ["kb", K, HOLDER, ATTITUDE, W]
      elif elop == "@world" and len(el) >= 2:
        world_hint = el[1]
      elif main_pkg is None:
        main_pkg = el
    # ["@tense"] overrides ["state time"] if both somehow appear.
    final_tense = tense_hint if tense_hint is not None else tense
    if main_pkg is not None:
      is_q, formula, _, world, loc2, kn2, _ = _extract_package_ctx(main_pkg)
      if location is None:
        location = loc2
      if knower is None:
        knower = kn2
      # ["@world",W] overrides the world from the inner package (used for questions).
      if world_hint is not None:
        world = world_hint
      return is_q, formula, confidence, world, location, knower, final_tense
    return False, None, confidence, world_hint, location, knower, final_tense

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

def _clausify(formula):
  """Convert a formula to a list of GK clauses (CNF).

  Returns a list of clauses, where each clause is either:
    - a single atom: ["pred", arg, ...]
    - a list of atoms (disjunction): [["pred1",...], ["pred2",...], ...]
  """
  f1 = _implies_to_or(formula)
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
      obj["@question"] = _coerce_atom(obj["@question"], const_classes)
    if "@logic" in obj and obj.get("@sourcetype") == "question":
      obj["@logic"] = _coerce_clause(obj["@logic"], const_classes)


def _coerce_atom(atom, const_classes):
  """Recursively substitute RELCLASS in degree-predicate atoms.

  Handles both raw question formulas (with connectives and quantifiers)
  and flat GK clause atoms.
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
    return [pred] + [_coerce_atom(el, const_classes) for el in atom[1:]]
  if pred in ("forall", "exists") and len(atom) >= 3:
    return [pred, atom[1], _coerce_atom(atom[2], const_classes)]

  return atom


def _coerce_clause(clause, const_classes):
  """Apply _coerce_atom to a GK clause (single atom or disjunction)."""
  if not isinstance(clause, list) or not clause:
    return clause
  # Disjunction: first element is itself a list of atoms.
  if isinstance(clause[0], list):
    return [_coerce_atom(atom, const_classes) for atom in clause]
  # Single atom.
  return _coerce_atom(clause, const_classes)


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
