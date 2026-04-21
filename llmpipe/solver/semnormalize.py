# Semantic normalisation of GK clause lists.
#
# Entry point: sem_normalize_clauses(clauses)
#
# Two normalisation passes applied to every eligible atom argument
# (all positions except position 0 / predicate name; skips URLs,
# ?:-variables, lists, and internal $/@-markers):
#
#   1. Antonym resolution (data_antonyms.ANTONYMS):
#      Flip atom polarity AND replace word with its antonym.
#      Applied regardless of current polarity, so:
#        positive "outside" → negative "inside"
#        negative "outside" → positive "inside"
#      This may introduce negations as well as remove them.
#
#   2. Canonical substitution (data_canonicals.CANONICALS):
#      Replace a variant word with its canonical form unconditionally.
#      e.g. "inside" → "in", "auto" → "car", "awake" → "wake"
#
# When globals.options["debug_print_flag"] is True and at least one
# substitution was made, the clause list is pretty-printed before and
# after normalisation.
#
# Normalisation is suppressed when globals.options["nosemnormal_flag"] is True.
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

import globals
import pretty
from data_antonyms import ANTONYMS
from data_canonicals import CANONICALS


# ======== eligibility check ========

def _eligible(s):
  """Return True if string s is a candidate for normalisation.

  Skips: URLs, ?:-variables, internal $-markers, @-keys.
  """
  if not isinstance(s, str):
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


# ======== atom-level normalisation ========

def _normalize_atom(atom):
  """Normalise a single atom (list) in place; return change count.

  Recurses into list-valued arguments.
  Position 0 (predicate name) is never modified.
  For GK disjunctive clauses (first element is a list), recurses into
  every element — there is no predicate name to skip.
  """
  if not isinstance(atom, list) or len(atom) == 0:
    return 0
  # GK disjunctive clause: first element is a list → recurse all elements.
  if isinstance(atom[0], list):
    changes = 0
    for sub in atom:
      changes += _normalize_atom(sub)
    return changes
  changes = 0
  pred = atom[0]
  negated = isinstance(pred, str) and pred.startswith("-")
  for i in range(1, len(atom)):
    arg = atom[i]
    if isinstance(arg, list):
      # Skip $ctxt terms — these are context markers, not semantic content.
      if arg and isinstance(arg[0], str) and arg[0].startswith("$ctxt"):
        pass
      else:
        # recurse but do not flip polarity into nested sub-structures
        changes += _normalize_atom(arg)
    elif _eligible(arg):
      word = arg
      # Pass 1: antonym resolution — flip polarity and swap to antonym
      if word in ANTONYMS:
        antonym = ANTONYMS[word]
        # flip predicate polarity
        if negated:
          atom[0] = pred[1:]   # strip leading "-"
          negated = False
        else:
          atom[0] = "-" + pred
          negated = True
        pred = atom[0]
        atom[i] = antonym
        word = antonym
        changes += 1
      # Pass 2: canonical substitution
      if word in CANONICALS:
        atom[i] = CANONICALS[word]
        changes += 1
  return changes


# ======== clause-level normalisation ========

def _normalize_clause(clause):
  """Normalise one clause dict; return change count."""
  if not isinstance(clause, dict):
    return 0
  changes = 0
  for key in ("@logic", "@question"):
    if key in clause:
      changes += _normalize_atom(clause[key])
  return changes


# ======== top-level entry point ========

def sem_normalize_clauses(clauses):
  """Normalise a GK clause list in place; return the (modified) list.

  Prints before/after pretty-printed clause lists when debug is on
  and at least one substitution was made.
  """
  if not isinstance(clauses, list):
    return clauses

  debug = globals.options.get("debug_print_flag", False)

  if debug:
    before_str = pretty.pp_str(clauses)

  total = 0
  for clause in clauses:
    total += _normalize_clause(clause)

  if total > 0 and debug:
    print("\n=== semantic normalization: {:d} substitution(s) ===\n".format(total))
    print("before:")
    print(before_str)
    print("\nafter:")
    print(pretty.pp_str(clauses))

  return clauses


# ======== stative event rewriting (pre-clausification) ========

from linguistics import STATIVE_TO_PRED


def rewrite_stative_events(tree):
  """Rewrite event-reified stative verbs to direct predicates.

  Operates on raw stage-2 JSON (pre-clausification).
  Finds ["exists", VAR, ["and", ...]] where the conjuncts encode a stative
  verb event (isa activity, has type VERB, has actor, has target, optional
  has time), and replaces with the direct predicate form.

  Only rewrites when the event variable does not appear in any conjuncts
  beyond the recognized core event atoms (safety check: no information lost).

  Recurses bottom-up through the whole formula tree.
  """
  if not isinstance(tree, list) or not tree:
    return tree
  # Recurse into children first (bottom-up).
  tree = [rewrite_stative_events(child) for child in tree]
  # Check for the target pattern: ["exists", VAR, BODY]
  if len(tree) == 3 and tree[0] == "exists" and isinstance(tree[1], str):
    result = _try_rewrite_stative(tree[1], tree[2])
    if result is not None:
      return result
  return tree


def _try_rewrite_stative(var, body):
  """Try to rewrite a stative event. Returns the replacement formula, or None."""
  if not isinstance(body, list) or not body:
    return None
  conjuncts = body[1:] if body[0] == "and" else [body]

  # Extract recognized event atoms.
  isa_activity = False
  verb = None
  actor = None
  target = None
  time_val = None
  core_indices = set()

  for i, c in enumerate(conjuncts):
    if not isinstance(c, list) or len(c) < 3:
      continue
    pred = c[0]
    if pred == "isa" and c[1] == "activity" and c[2] == var:
      isa_activity = True
      core_indices.add(i)
    elif pred == "has type" and c[1] == var and isinstance(c[2], str):
      verb = c[2]
      core_indices.add(i)
    elif pred == "has actor" and c[1] == var:
      actor = c[2]
      core_indices.add(i)
    elif pred == "has target" and c[1] == var:
      target = c[2]
      core_indices.add(i)
    elif pred == "has time" and c[1] == var:
      time_val = c[2]
      core_indices.add(i)

  if not isa_activity or verb is None or verb not in STATIVE_TO_PRED:
    return None
  if actor is None:
    return None

  # Safety: var must not appear in any non-core conjuncts.
  for i, c in enumerate(conjuncts):
    if i in core_indices:
      continue
    if _formula_contains(c, var):
      return None

  # Build the direct predicate.
  pred_name, rel_name = STATIVE_TO_PRED[verb]
  if rel_name is not None:
    new_pred = [pred_name, rel_name, actor]
    if target is not None:
      new_pred.append(target)
  else:
    new_pred = [pred_name, actor]
    if target is not None:
      new_pred.append(target)

  if time_val is not None:
    new_pred = ["@time", time_val, new_pred]

  remaining = [conjuncts[i] for i in range(len(conjuncts)) if i not in core_indices]
  if remaining:
    return ["and"] + remaining + [new_pred]
  return new_pred


def _formula_contains(formula, var):
  """Return True if var (string) appears anywhere in formula."""
  if formula == var:
    return True
  if isinstance(formula, list):
    return any(_formula_contains(el, var) for el in formula)
  return False


# =========== the end ===========
