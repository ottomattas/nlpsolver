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
  """
  if not isinstance(atom, list) or len(atom) == 0:
    return 0
  changes = 0
  pred = atom[0]
  negated = isinstance(pred, str) and pred.startswith("-")
  for i in range(1, len(atom)):
    arg = atom[i]
    if isinstance(arg, list):
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


# =========== the end ===========
