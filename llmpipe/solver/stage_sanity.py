# Sanity checks for Stage-1 and Stage-2 LLM output.
#
# Each check is a small, independent function that walks the parsed JSON and
# returns a list of Issue instances for any structural problems.  Issues
# carry enough context to (a) describe the problem to the LLM in a retry
# prompt and (b) fingerprint-compare across retries for persistence
# detection.
#
# Currently implemented:
#   * Stage 2: free-variable check (variable names bound somewhere in the
#     formula but referenced outside their binding scope).
#
# The framework is designed for easy extension — add a new _check_* function
# and register it in the dispatch list at the bottom of the corresponding
# check_stage<n>() function.
#
#-----------------------------------------------------------------
# Copyright 2026 Tanel Tammet (tanel.tammet@gmail.com)
# Licensed under the Apache License, Version 2.0.
#-----------------------------------------------------------------

from dataclasses import dataclass
import json
import re


@dataclass(frozen=True)
class Issue:
  """A single structural problem detected in LLM output.

  Equality / hashing is by all fields; fingerprinting for persistence
  detection across retries uses only (kind, location) — see
  issue_fingerprints().
  """
  kind: str          # e.g. "free_variable"
  location: str      # path into the formula, e.g. "@id:S1/forall:X/implies/..."
  description: str   # human-readable one-liner
  evidence: str      # JSON snippet of the offending atom/subtree


def issue_fingerprints(issues):
  """Return a frozenset of (kind, location) tuples for persistence detection."""
  return frozenset((i.kind, i.location) for i in issues)


# ======== Stage-2 structural operators ========

# Quantifier-like binders whose second element is the bound variable name.
_BINDERS = frozenset({"forall", "exists", "ask"})

# Operators whose body/children are sub-formulas (walk structurally, no
# new binding).  The walker recurses into all list children; entries here
# are used for path labeling and keep the predicate-detection logic clean.
_STRUCTURAL_OPS = frozenset({
  "and", "or", "not", "implies", "iff", "xor",
  "holds", "question", "normally",
  "@id", "@time", "@p",
})


# ======== Stage-2 free-variable check ========

def _collect_binder_names(node, lexicon):
  """Walk the tree; add every string used as the binder of
  forall/exists/ask to the lexicon set.  First pass: defines which names
  are treated as variables in the free-variable scan."""
  if not isinstance(node, list) or not node:
    return
  if isinstance(node[0], str):
    op = node[0]
    if op in _BINDERS and len(node) >= 3 and isinstance(node[1], str):
      lexicon.add(node[1])
  for child in node[1:]:
    if isinstance(child, list):
      _collect_binder_names(child, lexicon)


def _scan_free_vars(node, lexicon, scope, issues, path):
  """Second pass: emit free-variable Issues for lexicon strings that
  appear as atom arguments outside their binding scope.

  scope: frozenset of currently-bound variable names (per enclosing
  forall/exists/ask).
  path: dotted path used as the Issue.location — helps the LLM locate
  the offending atom in its own output.
  """
  if not isinstance(node, list) or not node:
    return
  if not isinstance(node[0], str):
    return
  op = node[0]

  # Binder: extend scope and recurse into the body (node[2]).
  if op in _BINDERS and len(node) >= 3 and isinstance(node[1], str):
    new_scope = scope | {node[1]}
    body = node[2]
    new_path = path + "/" + op + ":" + node[1]
    if isinstance(body, list):
      _scan_free_vars(body, lexicon, new_scope, issues, new_path)
    return

  # Structural recursion: walk every list child; preserve current scope.
  if op in _STRUCTURAL_OPS:
    for i, child in enumerate(node[1:], start=1):
      if isinstance(child, list):
        _scan_free_vars(child, lexicon, scope, issues, path + "/" + op)
    return

  # Otherwise treat as an atom.  Predicate is at position 0 (skipped).
  # Each argument string in the lexicon but not in scope is a free reference.
  for i, arg in enumerate(node[1:], start=1):
    if isinstance(arg, str):
      if arg in lexicon and arg not in scope:
        try:
          ev = json.dumps(node)
        except Exception:
          ev = str(node)
        issues.append(Issue(
          kind="free_variable",
          location=path + "/" + op + "[arg" + str(i) + "]",
          description=("Variable '" + arg + "' is referenced here but is "
                       "not bound by any enclosing forall/exists/ask. "
                       "Stage-2 instructions forbid free variables — the "
                       "binder must enclose every use."),
          evidence=ev,
        ))
    elif isinstance(arg, list):
      _scan_free_vars(arg, lexicon, scope, issues, path + "/" + op)


def _check_stage2_free_variables(logic):
  """Detect variable references outside their binding scope.  A 'variable
  reference' is any string argument that also appears somewhere in the
  formula as a binder name — string constants that never serve as binders
  are treated as entity ids/labels and ignored."""
  if not isinstance(logic, list):
    return []
  lexicon = set()
  _collect_binder_names(logic, lexicon)
  if not lexicon:
    return []
  issues = []
  _scan_free_vars(logic, lexicon, frozenset(), issues, "")
  return issues


# ======== Stage-2 misplaced meta-predicate check ========

# Tense words that, when found as the value slot of state_time/has_time,
# signal the atom is carrying grammatical tense — which should live in
# $ctxt (added during clausification), not as a predicate argument.
_TENSE_WORDS = frozenset({"past", "present", "future", "timeless"})

# Operators whose argument is a formula body.  When the walker descends into
# these, meta-predicates with tense values should no longer be legal at
# that depth — they belong as siblings at the package level.
_BODY_OPS = frozenset({"holds", "question", "ask", "normally"})


def _walk_body_depth(node, inside_body, issues, path):
  """Recurse the tree.  `inside_body` becomes True once we enter the body
  argument of a holds/question/ask/normally wrapper; from that point on,
  any tense-valued state_time/has_time atom is flagged.  Also recurses
  through quantifiers and connectives while preserving inside_body state.
  """
  if not isinstance(node, list) or not node or not isinstance(node[0], str):
    return
  op = node[0]

  if inside_body and op in ("state time", "-state time") and len(node) >= 3:
    tval = node[2]
    if isinstance(tval, str) and tval in _TENSE_WORDS:
      issues.append(Issue(
        kind="state_time_in_body",
        location=path + "/" + op,
        description=("Meta-predicate 'state time' with a grammatical tense "
                     "value ('" + tval + "') appears inside a formula body, "
                     "but tense metadata belongs at the package level "
                     "(sibling to 'holds'/'question'/'ask'), not inside "
                     "the quantified formula. Remove this atom from the "
                     "body and place the tense information at the package "
                     "sibling level if needed."),
        evidence=_safe_json(node),
      ))
      return

  # NOTE: intentionally do NOT flag `has time E TENSE PREP` here. Per
  # Stage-2 §8.1, this is the canonical shape for grammatical tense on
  # Davidsonian event variables and must survive into clausification.
  # strip_tense_has_time keeps it on event vars and strips it elsewhere.

  # Body-introducing operators: recurse into the last child with inside_body=True.
  if op in _BODY_OPS:
    # holds has signature [holds, W, BODY]; question/ask/normally have a
    # body as their single argument after op.  Recurse structurally but
    # flag inside_body for the body argument(s).
    for i, child in enumerate(node[1:], start=1):
      if isinstance(child, list):
        # For "holds", only the second arg (index 2 in node, i==2) is the body.
        # For "ask", the first arg (i==1) is the var, second (i==2) is body.
        # For "question"/"normally", the first (i==1) is the body.
        if op == "holds" and i == 2:
          _walk_body_depth(child, True, issues, path + "/" + op)
        elif op in ("question", "normally") and i == 1:
          _walk_body_depth(child, True, issues, path + "/" + op)
        elif op == "ask" and i == 2:
          _walk_body_depth(child, True, issues, path + "/" + op)
        else:
          _walk_body_depth(child, inside_body, issues, path + "/" + op)
    return

  # Quantifiers and connectives: recurse preserving inside_body.
  for child in node[1:]:
    if isinstance(child, list):
      _walk_body_depth(child, inside_body, issues, path + "/" + op)


def _check_stage2_misplaced_meta_tense(logic):
  """Detect misplaced tense-valued state_time/has_time atoms inside formula
  bodies.  See cases 37 and 142 for examples."""
  if not isinstance(logic, list):
    return []
  issues = []
  _walk_body_depth(logic, False, issues, "")
  return issues


# ======== Stage-2 dropped-specific-noun check ========

_WH_PLACEHOLDERS = frozenset({
  "who", "what", "which", "whom", "whose",
  "where", "when", "why", "how",
})


def _build_s1_generic_cat_to_id(s1_json):
  """Build {category: unique_specific_id} from Stage-1 generic entities
  that pass the guards.  Only categories where a single qualifying generic
  entity exists are retained — mirrors _build_query_cat_to_id in
  lc_rewrites.py."""
  if not isinstance(s1_json, list):
    return {}
  cat_to_ids = {}
  for pkg in s1_json:
    if not isinstance(pkg, dict):
      continue
    for asu in pkg.get("units", []) or []:
      if not isinstance(asu, dict):
        continue
      for ent in asu.get("entities", []) or []:
        if not isinstance(ent, dict):
          continue
        if ent.get("type") != "generic":
          continue
        eid = ent.get("id")
        cat = ent.get("category")
        if not (isinstance(eid, str) and isinstance(cat, str)):
          continue
        if not eid or not cat:
          continue
        if eid.lower() == cat.lower():
          continue
        if eid.lower() in _WH_PLACEHOLDERS:
          continue
        if " " in eid:
          continue
        if eid[:1].isupper():
          continue
        cat_to_ids.setdefault(cat, []).append(eid)
  return {cat: ids[0] for cat, ids in cat_to_ids.items() if len(ids) == 1}


def _scan_dropped_noun(node, cat_to_id, issues, path):
  """Walk the tree; for every 'exists VAR, BODY' where BODY is an 'and'
  with exactly one isa(CAT, VAR) literal and CAT has a known specific-id
  mapping distinct from CAT, emit an Issue (the Stage-2 query used the
  generic category where the Stage-1 specific noun should appear).
  """
  if not isinstance(node, list) or not node or not isinstance(node[0], str):
    return
  op = node[0]

  if op == "exists" and len(node) == 3 and isinstance(node[1], str):
    var = node[1]
    body = node[2]
    _check_exists_body_for_dropped_noun(body, var, cat_to_id, issues,
                                        path + "/exists:" + var)
    if isinstance(body, list):
      _scan_dropped_noun(body, cat_to_id, issues, path + "/exists:" + var)
    return

  for child in node[1:]:
    if isinstance(child, list):
      _scan_dropped_noun(child, cat_to_id, issues, path + "/" + op)


def _check_exists_body_for_dropped_noun(body, var, cat_to_id, issues, path):
  if not isinstance(body, list) or len(body) < 2 or body[0] != "and":
    return
  args = body[1:]
  isa_cats_for_var = []
  for arg in args:
    if (isinstance(arg, list) and len(arg) >= 3 and arg[0] == "isa"
        and arg[2] == var and isinstance(arg[1], str)):
      isa_cats_for_var.append(arg[1])
  if len(isa_cats_for_var) != 1:
    return
  cat = isa_cats_for_var[0]
  if cat not in cat_to_id:
    return
  specific = cat_to_id[cat]
  if specific == cat or specific in isa_cats_for_var:
    return
  issues.append(Issue(
    kind="dropped_specific_noun",
    location=path,
    description=("Query existential '" + var + "' is constrained only by "
                 "isa('" + cat + "', " + var + "), but the Stage-1 ASU "
                 "declared this entity with id='" + specific + "' and "
                 "category='" + cat + "'. Queries must preserve the "
                 "user's specific noun — add isa('" + specific + "', " +
                 var + ") so the query asks about '" + specific + "', "
                 "not any entity of category '" + cat + "'."),
    evidence=_safe_json(body),
  ))


def _check_stage2_dropped_specific_noun(logic, s1_json):
  """Detect query existentials constrained only by the category isa where
  Stage-1 unambiguously specified a different specific noun id.  See
  case 136."""
  if not isinstance(logic, list) or not isinstance(s1_json, list):
    return []
  cat_to_id = _build_s1_generic_cat_to_id(s1_json)
  if not cat_to_id:
    return []
  issues = []
  _scan_dropped_noun(logic, cat_to_id, issues, "")
  return issues


# ======== Stage-2 predicate-arity check ========

# Exact arities for Stage-2 predicates whose shape is unambiguously declared
# in stage2_instructions_full.txt §2.2, §2.3, §2.6.  We only enforce
# predicates where the arity is non-negotiable; skip any predicate whose
# correct arity depends on optional fields.
_ARITY_TABLE = {
  "isa": 2,
  "has property": 2,
  "have": 2,
  "has part": 2,
  "is rel2": 3,
  "can": 2,
  "has degree property": 4,
  "has degree rel2": 5,
  "has type": 2,
  "has actor": 2,
  "has target": 2,
  "has recipient": 2,
  "has source": 2,
  "has instrument": 2,
  "has manner": 2,
  "has direction": 2,
  "has beneficiary": 2,
  "has accompaniment": 2,
  "has path": 2,
  "has result": 2,
  "has topic": 2,
  "has cause": 2,
  "has destination": 3,
  "has location": 3,
  "has time": 3,
  "typical": 1,
  "typically": 2,
}


def _scan_arities(node, issues, path):
  if not isinstance(node, list) or not node or not isinstance(node[0], str):
    return
  op = node[0]
  base = op[1:] if op.startswith("-") else op

  # Structural nodes we only recurse into (they're not atoms).
  _STRUCTURAL = _BINDERS | _STRUCTURAL_OPS | _BODY_OPS
  if base in _STRUCTURAL:
    for child in node[1:]:
      if isinstance(child, list):
        _scan_arities(child, issues, path + "/" + op)
    return

  # Atom: check arity against table if known.
  if base in _ARITY_TABLE:
    expected = _ARITY_TABLE[base]
    actual = len(node) - 1  # minus the predicate name
    if actual != expected:
      issues.append(Issue(
        kind="wrong_arity",
        location=path + "/" + op,
        description=("Predicate '" + base + "' expects arity " +
                     str(expected) + " (" + str(expected) + " arguments "
                     "after the predicate name) but was emitted with "
                     "arity " + str(actual) + ". Check the Stage-2 "
                     "predicate signatures in the instructions and adjust "
                     "the arguments."),
        evidence=_safe_json(node),
      ))
      return  # don't also recurse into a malformed atom's children

  # Recurse into any list children (e.g., @time wrappers, nested subterms).
  for child in node[1:]:
    if isinstance(child, list):
      _scan_arities(child, issues, path + "/" + op)


def _check_stage2_arities(logic):
  """Detect atoms whose arity disagrees with the declared Stage-2 signature."""
  if not isinstance(logic, list):
    return []
  issues = []
  _scan_arities(logic, issues, "")
  return issues


# ======== Stage-2 missing-question check ========
#
# Detects the case where a Stage-1 unit was identified as a query (either
# its parent package's raw text contains a "?" or the unit's `type` field
# is "query"), but the corresponding Stage-2 @id package contains no
# `question` / `ask` wrapper.  This catches LLM truncations where the
# query unit was silently dropped, as well as cases where the LLM emitted
# a `holds` package for what should have been a question.

def _contains_question_or_ask(node):
  """Return True if any node in the tree has op `question` or `ask`."""
  if not isinstance(node, list) or not node:
    return False
  if isinstance(node[0], str) and node[0] in ("question", "ask"):
    return True
  for child in node[1:]:
    if isinstance(child, list) and _contains_question_or_ask(child):
      return True
  return False


def _collect_question_ids_from_logic(node, found):
  """Walk the Stage-2 tree.  For every `@id` encountered, record its s_id
  in `found` if the body sub-tree contains a `question` or `ask` wrapper.
  @ids are siblings under the top-level `and`, never nested, so we don't
  recurse past them once visited."""
  if not isinstance(node, list) or not node:
    return
  if isinstance(node[0], str):
    op = node[0]
    if op == "@id" and len(node) >= 3 and isinstance(node[1], str):
      sid = node[1]
      body = node[2]
      if isinstance(body, list) and _contains_question_or_ask(body):
        found.add(sid)
      return
  for child in node[1:]:
    if isinstance(child, list):
      _collect_question_ids_from_logic(child, found)


def _check_stage2_multiple_questions(logic):
  """Detect when Stage-2 emits more than one @id package whose body
  contains a `question` or `ask` wrapper.  The gk prover accepts only
  one @question per call; multiple questions cause "several questions
  given" errors and the pipeline cannot dispatch them.

  Triggered when a single conditional yes/no like "If A and B, does C?"
  is broken into separate sub-questions instead of a single conditional
  question with antecedent (A & B) and consequent C.
  """
  if not isinstance(logic, list):
    return []
  found = set()
  _collect_question_ids_from_logic(logic, found)
  if len(found) < 2:
    return []
  sids = sorted(found)
  return [Issue(
    kind="multiple_questions",
    location=", ".join("@id:" + s for s in sids),
    description=("Stage-2 emitted " + str(len(sids)) + " separate "
                 "question/ask packages (@ids " + ", ".join(sids) + "). "
                 "The downstream prover accepts at most ONE query per "
                 "input, so multiple question packages cannot be answered "
                 "together.  If the source sentence is a single "
                 "conditional yes/no (e.g. \"If A and B, does C?\") or a "
                 "single factive (e.g. \"Does X know that Y?\"), encode "
                 "the whole question as ONE package whose body wraps the "
                 "complete formula — e.g. [\"question\", [\"implies\", "
                 "[\"and\", A, B], C]] for the conditional, or "
                 "[\"question\", [\"and\", knows-A, fact-Y]] for the "
                 "factive embedding.  Assertions extracted from question "
                 "presuppositions belong in their own assertion packages "
                 "(no question/ask wrapper), not as separate queries."),
    evidence="question @ids: " + ", ".join(sids),
  )]


def _check_stage2_missing_question(logic, s1_json):
  """Detect Stage-1 query units that have no corresponding question/ask
  package in Stage-2.  Triggered when either unit.type == "query" or the
  parent package's raw text contains "?"."""
  if not isinstance(logic, list) or not isinstance(s1_json, list):
    return []
  expected = []      # list of (unit_id, raw)
  for pkg in s1_json:
    if not isinstance(pkg, dict):
      continue
    raw = pkg.get("raw", "") if isinstance(pkg.get("raw", ""), str) else ""
    raw_has_q = "?" in raw
    units = pkg.get("units", []) or []
    # If any unit in the package is already query-typed, trust Stage-1's
    # split: only flag query-typed units.  Otherwise (no explicit query
    # type) fall back to the raw-has-"?" hail-mary so a totally missing
    # query type doesn't go unnoticed.
    has_query_unit = any(
      isinstance(u, dict) and u.get("type") == "query" for u in units)
    for unit in units:
      if not isinstance(unit, dict):
        continue
      uid = unit.get("unit_id")
      if not isinstance(uid, str):
        continue
      utype = unit.get("type")
      if utype == "query":
        expected.append((uid, raw))
      elif raw_has_q and not has_query_unit:
        expected.append((uid, raw))
  if not expected:
    return []

  found = set()
  _collect_question_ids_from_logic(logic, found)

  issues = []
  for uid, raw in expected:
    if uid in found:
      continue
    issues.append(Issue(
      kind="missing_question",
      location="@id:" + uid,
      description=("Source sentence \"" + raw + "\" is a question (Stage-1 "
                   "marked unit " + uid + " as a query and/or the raw text "
                   "contains '?'), but the Stage-2 output has no "
                   "['question', FORMULA] or ['ask', VAR, FORMULA] wrapper "
                   "for unit " + uid + ".  Every query unit must be wrapped "
                   "as a 'question' (yes/no questions) or 'ask' (WH "
                   "questions) package — the @id for unit " + uid + " is "
                   "missing or wraps the wrong package shape.  Please add "
                   "the appropriate query package."),
      evidence=raw,
    ))
  return issues


# ======== Stage-2 event-shape check ========

# Event-role predicates (other than has_type).  If any of these mentions
# event variable E, the event is considered to have at least one role.
_EVENT_ROLE_PREDS = frozenset({
  "has actor", "has target", "has recipient", "has source",
  "has destination", "has location", "has instrument",
  "has manner", "has direction", "has time", "has beneficiary",
  "has accompaniment", "has path", "has result", "has topic",
  "has cause", "typical",
})


def _collect_atoms_for_var_in_and(body, var):
  """Return all atoms within an 'and' conjunction body that mention var
  (as any argument).  If body isn't an 'and', treat it as a single atom."""
  if not isinstance(body, list) or not body:
    return []
  atoms = []
  if body[0] == "and":
    candidates = body[1:]
  else:
    candidates = [body]
  for c in candidates:
    if isinstance(c, list) and var in c:
      atoms.append(c)
  return atoms


def _scan_event_shapes(node, issues, path):
  if not isinstance(node, list) or not node or not isinstance(node[0], str):
    return
  op = node[0]

  if op == "exists" and len(node) == 3 and isinstance(node[1], str):
    var = node[1]
    body = node[2]
    atoms = _collect_atoms_for_var_in_and(body, var)
    # Does the event carry a `has type` for this var?
    has_type_seen = any(
      isinstance(a, list) and len(a) >= 3 and a[0] == "has type" and a[1] == var
      for a in atoms)
    if has_type_seen:
      has_activity_isa = any(
        isinstance(a, list) and len(a) >= 3 and a[0] == "isa"
        and a[1] == "activity" and a[2] == var
        for a in atoms)
      has_some_role = any(
        isinstance(a, list) and len(a) >= 2 and a[0] in _EVENT_ROLE_PREDS
        and a[1] == var
        for a in atoms)
      if not has_activity_isa:
        issues.append(Issue(
          kind="event_missing_activity_isa",
          location=path + "/exists:" + var,
          description=("Event variable '" + var + "' has a 'has type' "
                       "atom but no 'isa(activity, " + var + ")' "
                       "conjunct. Stage-2 events must be typed with "
                       "isa(activity, E) in the same 'and' conjunction."),
          evidence=_safe_json(body),
        ))
      if not has_some_role:
        issues.append(Issue(
          kind="event_missing_role",
          location=path + "/exists:" + var,
          description=("Event variable '" + var + "' has 'has type' and "
                       "(possibly) isa(activity,…) but no thematic-role "
                       "atom (has_actor / has_target / has_recipient / "
                       "has_location / has_time / typical / etc.). Every "
                       "event needs at least one role linking it to an "
                       "entity or property."),
          evidence=_safe_json(body),
        ))
    # Recurse into body in case there are nested existentials.
    if isinstance(body, list):
      _scan_event_shapes(body, issues, path + "/exists:" + var)
    return

  for child in node[1:]:
    if isinstance(child, list):
      _scan_event_shapes(child, issues, path + "/" + op)


def _check_stage2_event_shapes(logic):
  """Detect events (existentials with has_type) missing isa(activity,E) or
  any thematic-role atom."""
  if not isinstance(logic, list):
    return []
  issues = []
  _scan_event_shapes(logic, issues, "")
  return issues


# ======== Stage-2 inner-content-event missing has_time check ========
#
# In a two-event reification (speech_act / volition / intention /
# expectation), the OUTER event E1 carries the modal classifier and a
# has_time atom, while the INNER content event E2 (linked via
# ["has content", E1, E2]) carries its own Davidsonian roles -- including
# its own has_time, since the embedded clause has independent tense.
#
# Gemini intermittently omits has_time on the inner content event of
# speech_act reifications (e.g., "John said that Mary left." -> the inner
# leave-event lacks has_time(E2, "past", "in")).  The axioms_std.js §5.2
# factive bridge then derives actuality(E2) but the question's tensed
# event ["has time", E_q, "past", "in"] fails to unify with E2.
#
# The check fires only when ALL of the following hold (5-gate criterion):
#   1. V appears as the 2nd argument of ["has content", E1, V] (V is an
#      inner content event).
#   2. V has a ["has type", V, ...] atom in its exists-scope (V is a
#      Davidsonian event, not a stative or propositional content).
#   3. V has NO ["has time", V, ...] atom in its exists-scope.
#   4. V has NO modal classifier in its exists-scope -- capability,
#      typical, necessity, obligation, volition, intention, expectation,
#      or speech_act (events that carry a classifier are intentionally
#      tenseless and shouldn't require has_time).
#   5. The Stage-1 unit containing this @id has its "time" field set
#      (past / present / future) -- evidence that the input is
#      tense-anchored at the matrix level.  Skips generic / tenseless
#      inputs where missing has_time on the inner event is fine.

_INNER_EVENT_MODAL_CLASSIFIERS = frozenset({
  "capability", "typical", "necessity", "obligation",
  "volition", "intention", "expectation", "speech_act",
})


def _collect_inner_content_vars(node, found):
  """Collect every string V that appears as the 2nd argument of an atom
  whose head is 'has content' anywhere in the tree."""
  if not isinstance(node, list) or not node:
    return
  head = node[0] if isinstance(node[0], str) else None
  if head == "has content" and len(node) >= 3 and isinstance(node[2], str):
    found.add(node[2])
  for c in node:
    if isinstance(c, list):
      _collect_inner_content_vars(c, found)


def _has_modal_classifier_for_var(body, var):
  """True if `body` (typically an `and` block) contains any classifier
  atom of arity 1 referencing var, e.g. ["capability", var]."""
  if not isinstance(body, list) or not body:
    return False
  if body[0] == "and":
    children = body[1:]
  else:
    children = [body]
  for c in children:
    if (isinstance(c, list) and len(c) == 2
        and isinstance(c[0], str)
        and c[0] in _INNER_EVENT_MODAL_CLASSIFIERS
        and c[1] == var):
      return True
  return False


def _unit_id_has_tense(s1_json, unit_id):
  """True if Stage-1 contains a unit with the given unit_id whose `time`
  field is set to past/present/future."""
  if not isinstance(s1_json, list):
    return False
  for item in s1_json:
    if not isinstance(item, dict):
      continue
    for u in item.get("units", []) or []:
      if not isinstance(u, dict):
        continue
      if u.get("unit_id") != unit_id:
        continue
      t = u.get("time")
      if isinstance(t, str) and t.lower() in ("past", "present", "future"):
        return True
      return False
  return False


def _scan_inner_event_time(node, inner_vars, s1_json, current_id,
                           issues, path):
  if not isinstance(node, list) or not node or not isinstance(node[0], str):
    return
  op = node[0]

  # Track which @id we're inside (gate 5 needs this for Stage-1 lookup).
  if op == "@id" and len(node) >= 3 and isinstance(node[1], str):
    new_id = node[1]
    for child in node[2:]:
      if isinstance(child, list):
        _scan_inner_event_time(child, inner_vars, s1_json, new_id,
                               issues, path + "/@id:" + new_id)
    return

  if op == "exists" and len(node) == 3 and isinstance(node[1], str):
    var = node[1]
    body = node[2]
    if var in inner_vars:
      atoms = _collect_atoms_for_var_in_and(body, var)
      has_type_seen = any(
        isinstance(a, list) and len(a) >= 3
        and a[0] == "has type" and a[1] == var
        for a in atoms)
      has_time_seen = any(
        isinstance(a, list) and len(a) >= 3
        and a[0] == "has time" and a[1] == var
        for a in atoms)
      has_classifier = _has_modal_classifier_for_var(body, var)
      unit_is_tensed = (current_id is not None
                       and _unit_id_has_tense(s1_json, current_id))
      if (has_type_seen and not has_time_seen and not has_classifier
          and unit_is_tensed):
        issues.append(Issue(
          kind="inner_content_event_missing_time",
          location=path + "/exists:" + var,
          description=(
            "Inner content event '" + var + "' (linked by has_content) "
            "has a 'has type' atom and no modal classifier, but no "
            "'has time' atom -- yet the Stage-1 unit '"
            + str(current_id) + "' is tense-anchored. Embedded clauses "
            "carry their own tense, so the inner event needs a "
            "has_time atom (e.g., "
            "[\"has time\", \"" + var + "\", \"past\", \"in\"]) matching "
            "the embedded clause's tense, so modal-bridge axioms can "
            "unify it with a tensed query event."),
          evidence=_safe_json(body),
        ))
    if isinstance(body, list):
      _scan_inner_event_time(body, inner_vars, s1_json, current_id,
                             issues, path + "/exists:" + var)
    return

  for child in node[1:]:
    if isinstance(child, list):
      _scan_inner_event_time(child, inner_vars, s1_json, current_id,
                             issues, path + "/" + op)


def _check_stage2_inner_content_event_time(logic, s1_json=None):
  """Flag inner content events (referenced by has_content) that have a
  has_type atom but no has_time atom in their exists-scope, AND no modal
  classifier, AND the surrounding Stage-1 unit is tense-anchored.
  See the section comment above for the 5-gate criterion."""
  if not isinstance(logic, list):
    return []
  inner_vars = set()
  _collect_inner_content_vars(logic, inner_vars)
  if not inner_vars:
    return []
  issues = []
  _scan_inner_event_time(logic, inner_vars, s1_json, None, issues, "")
  return issues


# ======== Stage-2 entity-ID prefix-typo check ========
#
# Detects entity IDs like "fr fridge 3" that are an existing entity ID
# ("fridge 3") prefixed by a stray initial fragment of the same noun. Seen
# on case 152 with gemini, where the question's isa guard contained
# "fr fridge 3" while the assertion (and the question's is_rel2 atom)
# used "fridge 3" — the mismatch made the goal unreachable. The check
# triggers a corrective Stage-2 retry via the standard sanity-retry loop.

# Entity IDs follow the convention "<lowercase-noun-or-phrase> <integer>"
# or "<Capitalized-name> <integer>". Match anything that ends with a single
# space + digits.
_ENTITY_ID_RE = re.compile(r'^(\S.*?) (\d+)$')

# Stop the prefix check from flagging legitimate adjective-modified IDs.
_MAX_TYPO_PREFIX_LEN = 4


def _collect_entity_ids_with_paths(node, found, path):
  """Walk node (dicts, lists, strings), recording the first path at which
  each id-shaped string is seen. id-shape := "<text> <integer>".

  found: dict id -> path (first occurrence wins).
  """
  if isinstance(node, str):
    if _ENTITY_ID_RE.match(node) and node not in found:
      found[node] = path
    return
  if isinstance(node, dict):
    # Walk dict values; key into path so we can locate by key when useful.
    for key, val in node.items():
      _collect_entity_ids_with_paths(val, found, path + "/" + str(key))
    return
  if not isinstance(node, list) or not node:
    return
  head = node[0] if isinstance(node[0], str) else None
  for i, child in enumerate(node):
    child_path = (path + "/" + head) if head and i == 0 else (path + "[" + str(i) + "]")
    _collect_entity_ids_with_paths(child, found, child_path)


def _is_prefix_typo(candidate_base, target_base):
  """Return the stray prefix `extra` if candidate_base = extra + ' ' + target_base
  AND extra is a prefix of target_base's first word (case-insensitive),
  with len(extra) <= _MAX_TYPO_PREFIX_LEN. Otherwise None.
  """
  needle = " " + target_base
  if not candidate_base.endswith(needle):
    return None
  extra = candidate_base[: -len(needle)]
  if not extra or " " in extra:
    return None
  if len(extra) > _MAX_TYPO_PREFIX_LEN:
    return None
  first_word = target_base.split(" ", 1)[0]
  if not first_word:
    return None
  if first_word.lower().startswith(extra.lower()):
    return extra
  return None


def _check_stage2_entity_id_typos(logic):
  """Flag entity IDs that look like prefix-typos of another entity in the
  same Stage-2 output. See module docstring for case 152 (gemini) example.
  """
  if not isinstance(logic, list):
    return []
  found = {}
  _collect_entity_ids_with_paths(logic, found, "")
  if len(found) < 2:
    return []

  # Bucket by numeric suffix to limit the pairwise scan.
  by_suffix = {}
  for ident, path in found.items():
    m = _ENTITY_ID_RE.match(ident)
    if not m:
      continue
    by_suffix.setdefault(m.group(2), []).append((ident, m.group(1), path))

  issues = []
  reported = set()
  for suffix, items in by_suffix.items():
    if len(items) < 2:
      continue
    # Compare every distinct pair; flag the longer one if the shorter
    # is a typo-target of it.
    for i in range(len(items)):
      for j in range(len(items)):
        if i == j:
          continue
        cand_id, cand_base, cand_path = items[i]
        tgt_id,  tgt_base,  _         = items[j]
        if cand_id in reported:
          continue
        if len(cand_base) <= len(tgt_base):
          continue
        extra = _is_prefix_typo(cand_base, tgt_base)
        if extra is None:
          continue
        reported.add(cand_id)
        issues.append(Issue(
          kind="entity_id_typo",
          location=cand_path,
          description=('Entity id ' + json.dumps(cand_id)
                       + ' looks like a typo of '
                       + json.dumps(tgt_id)
                       + ' (stray prefix ' + json.dumps(extra) + ').'
                       + ' Replace ' + json.dumps(cand_id)
                       + ' with ' + json.dumps(tgt_id)
                       + ' wherever it appears.'),
          evidence=_safe_json([cand_id, "->", tgt_id]),
        ))
        break
  return issues


# ======== small helpers ========

def _safe_json(obj):
  try:
    return json.dumps(obj)
  except Exception:
    return str(obj)


# ======== Stage-1 missing-wh-placeholder check ========
#
# Detects WH-question units whose Stage-1 entities list is missing a
# wh_placeholder entity.  The Stage-1 instructions require WH queries to
# include {id: "entity", type: "generic", wh_placeholder: true} and to
# transform the unit's text per the question-word rules (What → "Which
# entity", etc.).  Some LLMs (notably gpt) skip the entity injection and
# leave the text unchanged, which then makes Stage-2 fall back to a yes/no
# encoding (case 48 with gpt: "What is the length of the red car?" became
# a yes/no with a hallucinated 80).

# Wh-words that mark the start of a wh-question.  Detection is
# case-insensitive and applied to the leading word of the raw / text
# field.  "How" + "many" is treated specially: "How many ..." should keep
# numeric wording per the Stage-1 instructions, but still needs a
# placeholder to give Stage-2 a binding slot.
_WH_LEAD_WORDS = frozenset({
  "what", "which", "who", "whom", "whose",
  "where", "when", "why", "how",
})


def _starts_with_wh(text):
  """Return True if the leading word of `text` is a wh-question word."""
  if not isinstance(text, str):
    return False
  s = text.strip()
  if not s:
    return False
  # Take the first word, strip punctuation/quotes.
  for sep in (" ", "\t", "\n"):
    idx = s.find(sep)
    if idx > 0:
      s = s[:idx]
      break
  s = s.strip(".,!?;:'\"()[]{}")
  return s.lower() in _WH_LEAD_WORDS


def _has_wh_placeholder(unit):
  """Return True if any entity in the unit has wh_placeholder=True."""
  if not isinstance(unit, dict):
    return False
  for ent in unit.get("entities", []) or []:
    if isinstance(ent, dict) and ent.get("wh_placeholder"):
      return True
  return False


def _check_stage1_missing_wh_placeholder(s1_json):
  """Detect Stage-1 query units with a wh-leading text but no
  wh_placeholder entity.  Triggers a corrective retry asking the LLM to
  add the placeholder and apply the question-word transformation to the
  unit's `text` field."""
  if not isinstance(s1_json, list):
    return []
  issues = []
  for pkg in s1_json:
    if not isinstance(pkg, dict):
      continue
    raw = pkg.get("raw", "")
    raw_text = raw if isinstance(raw, str) else ""
    for unit in pkg.get("units", []) or []:
      if not isinstance(unit, dict):
        continue
      if unit.get("type") != "query":
        continue
      if _has_wh_placeholder(unit):
        continue
      utext = unit.get("text", "") if isinstance(unit.get("text", ""), str) else ""
      # A unit is wh if either its own text or the parent raw begins with
      # a wh-word.  Most reliable signal is the unit's text after Stage-1
      # rewrites; raw is the user's original wording.
      if not (_starts_with_wh(utext) or _starts_with_wh(raw_text)):
        continue
      uid = unit.get("unit_id", "?")
      issues.append(Issue(
        kind="missing_wh_placeholder",
        location="@id:" + str(uid),
        description=("Unit " + str(uid) + " has type='query' and a "
                     "wh-question text (\"" + (utext or raw_text) +
                     "\"), but its entities list contains no "
                     "wh_placeholder entry. Wh-questions MUST include a "
                     "placeholder entity such as "
                     "{\"id\":\"entity\",\"type\":\"generic\","
                     "\"wh_placeholder\":true} (or "
                     "{\"id\":<noun>,\"type\":\"generic\","
                     "\"wh_placeholder\":true} when the question names a "
                     "category, e.g. \"Which person\" → id \"person\"). "
                     "Also transform the unit's `text` field per the "
                     "Question Word Transformation rules: What/Where → "
                     "\"Which entity ...\", Who/Whom → \"Which entity "
                     "...\", When → keep \"When\", How many → keep "
                     "numeric wording."),
        evidence=_safe_json(unit),
      ))
  return issues


# ======== Stage-1 entity-used-as-location check ========

def _collect_concrete_entity_ids(unit):
  """Return the set of concrete-entity IDs declared in a unit's
  entities list. Generic / wh-placeholder entities are skipped."""
  out = set()
  if not isinstance(unit, dict):
    return out
  for ent in unit.get("entities", []) or []:
    if not isinstance(ent, dict):
      continue
    if ent.get("type") != "concrete":
      continue
    eid = ent.get("id")
    if isinstance(eid, str) and eid:
      out.add(eid)
  return out


def _check_stage1_entity_used_as_location(s1_json):
  """Detect Stage-1 units where the `location` field is a concrete-entity
  ID declared in the same unit's `entities` list.

  Stage-1's `location` field is the *scene* where the unit's situation
  occurs (e.g. "the kitchen", "the park", "outside"). It must NOT be a
  concrete object that participates in a spatial relation as a secondary
  argument — that belongs in the actions/relations, not in the
  scene-location.

  Symptom: lc_ctxt injects `location` into the `$ctxt` location slot, so
  ASU pairs that should share a context end up with distinct entity
  constants there. Mutex / X2 axioms cannot then unify the two contexts.
  See gemini's case 148 trace (assertion ctxt has "table 3", question
  ctxt has "floor 4" — contexts don't unify, X2 cannot fire).
  """
  if not isinstance(s1_json, list):
    return []
  issues = []
  for pkg in s1_json:
    if not isinstance(pkg, dict):
      continue
    for unit in pkg.get("units", []) or []:
      if not isinstance(unit, dict):
        continue
      loc = unit.get("location")
      if not isinstance(loc, str) or not loc:
        continue
      concrete_ids = _collect_concrete_entity_ids(unit)
      if loc not in concrete_ids:
        continue
      uid = unit.get("unit_id", "?")
      issues.append(Issue(
        kind="entity_used_as_location",
        location="@id:" + str(uid),
        description=("Unit " + str(uid) + " has location=\"" + loc +
                     "\" which is a concrete entity declared in the "
                     "same unit's entities list. The `location` field "
                     "is for the SCENE / place where the situation "
                     "occurs (e.g. \"the kitchen\", \"the park\", "
                     "\"outside\"). It must NOT be a concrete object "
                     "that participates in a spatial relation as the "
                     "secondary argument. If the only spatial info is "
                     "\"X is on Y\" (or under/in/etc.), put that "
                     "preposition + entity in the relevant action's "
                     "roles (e.g. roles.location with location_prep) "
                     "and OMIT the unit-level `location` field. If "
                     "there is a separate scene location, replace "
                     "\"" + loc + "\" with that scene name. Do not "
                     "use the concrete entity " + loc + " as the "
                     "scene location."),
        evidence=_safe_json(unit),
      ))
  return issues


# ======== public API ========

def check_stage1(s1_json):
  """Run all registered Stage-1 sanity checks and return the combined
  issue list."""
  issues = []
  issues.extend(_check_stage1_missing_wh_placeholder(s1_json))
  issues.extend(_check_stage1_entity_used_as_location(s1_json))
  return issues


def check_stage2(logic, s1_json=None):
  """Run all registered Stage-2 sanity checks and return the combined
  issue list.  s1_json provides ASU context for checks that need it
  (currently: the dropped-specific-noun check).
  """
  issues = []
  issues.extend(_check_stage2_free_variables(logic))
  issues.extend(_check_stage2_misplaced_meta_tense(logic))
  issues.extend(_check_stage2_dropped_specific_noun(logic, s1_json))
  issues.extend(_check_stage2_arities(logic))
  issues.extend(_check_stage2_event_shapes(logic))
  issues.extend(_check_stage2_inner_content_event_time(logic, s1_json))
  issues.extend(_check_stage2_missing_question(logic, s1_json))
  issues.extend(_check_stage2_multiple_questions(logic))
  issues.extend(_check_stage2_entity_id_typos(logic))
  return issues


# ======== retry-prompt suffix ========

def format_retry_suffix(issues, flawed_parsed):
  """Build the text appended to the original stage input when re-calling
  the LLM after a sanity-check failure.

  Structure:
    * Shows the LLM's previous (flawed) answer.
    * Lists each issue with kind, location, and description.
    * Asks for a corrected JSON.
  """
  try:
    flawed_str = json.dumps(flawed_parsed, indent=2)
  except Exception:
    flawed_str = str(flawed_parsed)

  lines = []
  lines.append("")
  lines.append("Your previous answer was:")
  lines.append(flawed_str)
  lines.append("")
  lines.append("This answer has the following issues:")
  for i, iss in enumerate(issues, start=1):
    lines.append(str(i) + ". [" + iss.kind + "] " + iss.description)
    if iss.location:
      lines.append("   location: " + iss.location)
    if iss.evidence:
      lines.append("   offending subtree: " + iss.evidence)
  lines.append("")
  lines.append("Please produce a corrected answer that does not have these "
               "issues. Return only the corrected JSON, with no additional "
               "commentary.")
  lines.append("")
  return "\n".join(lines)
