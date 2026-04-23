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

  # NOTE: intentionally do NOT flag `has time E TENSE PREP` here. The
  # Stage-2 examples file illustrates this shape and most LLMs emit it
  # consistently.  The pipeline's strip_tense_has_time post-processor
  # handles it cheaply; triggering an LLM retry on every past-tense verb
  # would waste calls for a problem already solved.

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


# ======== small helpers ========

def _safe_json(obj):
  try:
    return json.dumps(obj)
  except Exception:
    return str(obj)


# ======== public API ========

def check_stage1(s1_json):
  """Run all Stage-1 sanity checks.  Currently empty: no Stage-1 issue
  patterns have been identified yet.  Returns [] always."""
  # Placeholder — the framework is in place so Stage-1 checks can be
  # added later without touching llmparse.py.
  return []


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
