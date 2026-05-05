# Traditional and JSON logic syntax rendering for proof display.
#
# Converts CNF clauses and FOL formulas to human-readable logic notation.
# Two modes: traditional pred(arg,...) syntax and compact JSON format.
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

from lc_clausify import is_skolem_const, is_skolem_fn
from proof_utils import entity_name, _ctx
import globals as _g


def format_clause_logic(clause):
  """Format a proof clause for logic display: compact JSON, no spaces inside
  atoms, one space between atoms.  A single-atom clause is unwrapped."""
  if clause is False or clause is None:
    return "false"
  if not isinstance(clause, list):
    return json.dumps(clause, ensure_ascii=False)
  if len(clause) == 1:
    return json.dumps(clause[0], separators=(',', ':'), ensure_ascii=False)
  return "[" + ", ".join(
    json.dumps(a, separators=(',', ':'), ensure_ascii=False) for a in clause
  ) + "]"


# ======== traditional logic syntax renderer ========
#
# Renders formulas and clauses in pred(arg1,arg2) notation.
# Constants are lowercased, variables are uppercase, spaces become underscores.
# Clauses with negative atoms are rendered as implications.

def _logic_name(val):
  """Convert a raw value to traditional logic notation.

  Variables (?:X) -> uppercase: X
  Constants (John 1, car 2) -> lowercase with underscores: john_1, car_2
  Skolem functions ([sk0,?:X]) -> sk0(X)
  Lists (non-Skolem) -> recursive
  """
  if isinstance(val, list):
    if not val:
      return "[]"
    # $ctxt term: render as $ctxt(args)
    if val[0] == "$ctxt":
      args = ",".join(_logic_name(a) for a in val[1:])
      return "$ctxt(" + args + ")"
    # Skolem function or other function term
    if isinstance(val[0], str):
      fname = val[0].replace(" ", "_")
      if not fname.startswith(("?:", "$")):
        fname = _lc_first(fname)
      elif fname.startswith("?:"):
        fname = fname[2:]
      args = ",".join(_logic_name(a) for a in val[1:])
      return fname + "(" + args + ")" if args else fname + "()"
    # List of atoms (clause): shouldn't reach here normally
    return "[" + ",".join(_logic_name(a) for a in val) + "]"
  if isinstance(val, bool):
    return "true" if val else "false"
  if not isinstance(val, str):
    return str(val)
  # UNA prefix: strip `#:` so all later branches see the bare entity id.
  if val.startswith("#:"):
    val = val[2:]
  # Variable
  if val.startswith("?:"):
    bare = val[2:]
    # Use var_display map if available
    if val in _ctx.var_display:
      return _ctx.var_display[val]
    if bare.isdigit():
      return "V" + bare
    return bare
  # Skolem constants: use display name (act1 for sk0, etc.)
  if is_skolem_const(val):
    return _ctx.skolem_display.get(val, val)
  # $-prefixed special constants: keep as-is
  if val.startswith("$"):
    return val.replace(" ", "_")
  # Regular constants: delegate to entity_name for the display name, then
  # adapt to logic notation (lowercase, underscores, strip articles).
  # This ensures logic and English use the same naming decisions.
  display = entity_name(val, proof_mode=True)
  # Strip leading "the " (English article, not needed in logic)
  if display.startswith("the "):
    display = display[4:]
  return _lc_first(display.replace(" ", "_"))


def _lc_first(s):
  """Lowercase the first character of a string."""
  if not s:
    return s
  return s[0].lower() + s[1:]


def _atom_to_logic(atom, negated=False):
  """Render one atom in traditional logic notation: pred(arg1,arg2,...).

  negated=True prepends ~.
  $ctxt arguments are included (use _compress_ctxt_clause to strip first).
  """
  if not isinstance(atom, list) or not atom:
    return ("-" + str(atom)) if negated else str(atom)
  pred = str(atom[0])
  # Handle negation prefix in the predicate name
  if pred.startswith("-"):
    return _atom_to_logic([pred[1:]] + list(atom[1:]), negated=not negated)
  prefix = "-" if negated else ""
  pred_name = _lc_first(pred.replace(" ", "_"))
  args = atom[1:]
  if not args:
    return prefix + pred_name
  args_str = ",".join(_logic_name(a) for a in args)
  return prefix + pred_name + "(" + args_str + ")"


def _compress_ctxt_clause(clause):
  """Strip free-variable-only $ctxt arguments from a clause.

  A variable is 'free in context' if it appears ONLY inside $ctxt terms
  and nowhere else in the clause. Such variables are uninformative and
  can be omitted for readability.

  Returns a new clause with $ctxt terms compressed or removed.
  """
  if not isinstance(clause, list):
    return clause

  # Detect single-atom clause (flat list, first element is a string predicate)
  # vs multi-atom clause (list of lists).
  is_single = clause and not isinstance(clause[0], list)

  if is_single:
    # Wrap in a list to use the same compression logic, then unwrap.
    outside_vars = set()
    _collect_outside_ctxt_vars(clause, outside_vars)
    return _compress_atom_ctxt(clause, outside_vars)

  # Multi-atom clause: collect vars outside $ctxt across all atoms.
  outside_vars = set()
  for atom in clause:
    if isinstance(atom, list) and atom:
      _collect_outside_ctxt_vars(atom, outside_vars)

  # Compress $ctxt in each atom.
  result = []
  for atom in clause:
    if isinstance(atom, list) and atom:
      result.append(_compress_atom_ctxt(atom, outside_vars))
    else:
      result.append(atom)
  return result


def _collect_outside_ctxt_vars(atom, result):
  """Collect variables from atom, skipping $ctxt sub-terms."""
  if isinstance(atom, str):
    if atom.startswith("?:"):
      result.add(atom)
    return
  if not isinstance(atom, list):
    return
  if atom and atom[0] == "$ctxt":
    return  # skip entire $ctxt
  for el in atom:
    _collect_outside_ctxt_vars(el, result)


def _compress_atom_ctxt(atom, outside_vars):
  """Replace $ctxt in an atom with a compressed version. Recurses into
  $block/$not wrappers to reach nested $ctxt terms."""
  if not isinstance(atom, list) or len(atom) < 2:
    return atom
  pred = atom[0] if isinstance(atom[0], str) else None
  # Recurse into $block and $not to compress nested $ctxt
  if pred == "$block" and len(atom) >= 3:
    return [atom[0], atom[1], _compress_atom_ctxt(atom[2], outside_vars)]
  if pred == "$not" and len(atom) >= 2:
    return [atom[0], _compress_atom_ctxt(atom[1], outside_vars)]
  # Find the $ctxt argument (always last positional argument).
  last = atom[-1]
  if not (isinstance(last, list) and last and last[0] == "$ctxt"):
    # No $ctxt — recurse into sub-atoms (for multi-atom clauses).
    if isinstance(atom[0], list):
      return [_compress_atom_ctxt(a, outside_vars) for a in atom]
    return atom
  # Compress the $ctxt: keep only non-free prefix components.
  ctxt_args = last[1:]  # [tense, world, location, knower]
  kept = []
  for component in ctxt_args:
    if isinstance(component, str) and component.startswith("?:"):
      if component not in outside_vars:
        break  # free in context — stop here, strip this and rest
    kept.append(component)
  if not kept:
    return atom[:-1]  # remove $ctxt entirely
  new_ctxt = ["$ctxt"] + kept
  return atom[:-1] + [new_ctxt]


def format_clause_traditional(clause, max_len=100, confidence=None):
  """Format a proof clause in traditional logic notation.

  Clauses with negative atoms are rendered as implications:
    ~isa(bird,X) | can(X,fly)  =>  isa(bird,X) => can(X,fly)

  $block atoms are rendered as annotation suffixes.
  $ctxt terms are compressed (free-variable components stripped).
  """
  if clause is False or clause is None:
    return "false"
  if not isinstance(clause, list):
    return str(clause)

  # Compress $ctxt terms
  clause = _compress_ctxt_clause(clause)

  # Single atom (not wrapped in a list-of-lists)
  if clause and not isinstance(clause[0], list):
    s = _atom_to_logic(clause)
    if confidence is not None and confidence < 0.9999:
      s += "  @" + str(round(confidence, 2))
    return s

  # Multi-atom clause: separate into conditions, conclusions, blockers
  neg_atoms = []
  pos_atoms = []
  block_texts = []
  for atom in clause:
    if not isinstance(atom, list) or not atom:
      continue
    pred = str(atom[0])
    if pred == "$block":
      block_texts.append(_block_to_logic(atom))
    elif pred.startswith("-"):
      neg_atoms.append(atom)
    else:
      pos_atoms.append(atom)

  # Build implication or disjunction
  if neg_atoms and pos_atoms:
    # Implication: conditions => conclusions
    conds = " & ".join(_atom_to_logic([a[0][1:]] + list(a[1:]))
                       for a in neg_atoms)
    concls = " | ".join(_atom_to_logic(a) for a in pos_atoms)
    s = conds + " => " + concls
  elif neg_atoms:
    # All negative — implication to negated last
    if len(neg_atoms) == 1:
      s = _atom_to_logic(neg_atoms[0])
    else:
      conds = " & ".join(_atom_to_logic([a[0][1:]] + list(a[1:]))
                         for a in neg_atoms[:-1])
      last = neg_atoms[-1]
      s = conds + " => " + _atom_to_logic([last[0][1:]] + list(last[1:]),
                                           negated=True)
  elif pos_atoms:
    s = " | ".join(_atom_to_logic(a) for a in pos_atoms)
  elif block_texts:
    # Purely $block clause — show the blocks directly
    s = ", ".join(block_texts)
    block_texts = []  # already rendered
  else:
    s = "(empty)"

  if block_texts:
    s += "  [" + ", ".join(block_texts) + "]"
  if confidence is not None and confidence < 0.9999:
    s += "  @" + str(round(confidence, 2))

  # Pretty-print if too long
  if len(s) > max_len:
    s = _break_logic_line(s, max_len)

  return s


def _block_to_logic(block_atom):
  """Render a $block atom in logic notation."""
  if not isinstance(block_atom, list) or len(block_atom) < 3:
    return ""
  inner = block_atom[2]
  if isinstance(inner, list) and inner and inner[0] == "$not" and len(inner) > 1:
    return "block(-" + _atom_to_logic(inner[1]) + ")"
  return "block(" + _logic_name(inner) + ")"


def _break_logic_line(s, max_len):
  """Break a long logic line at => or & boundaries."""
  # Try breaking at " => " — put conclusion on next line indented
  if " => " in s and len(s) > max_len:
    idx = s.index(" => ")
    lhs = s[:idx]
    rhs = s[idx + 4:]
    # Also break the lhs at & if needed
    if len(lhs) > max_len:
      lhs = _break_at_and(lhs, max_len)
    return lhs + " =>\n    " + rhs
  # Break at " & " boundaries
  if " & " in s and len(s) > max_len:
    return _break_at_and(s, max_len)
  return s


def _break_at_and(s, max_len):
  """Break a string at ' & ' boundaries when it exceeds max_len."""
  pieces = s.split(" & ")
  lines = []
  current = pieces[0]
  for p in pieces[1:]:
    if len(current) + len(p) + 3 > max_len:
      lines.append(current + " &")
      current = "    " + p
    else:
      current += " & " + p
  lines.append(current)
  return "\n".join(lines)


def formula_to_logic(formula, max_len=100):
  """Render a stage-2 FOL formula in traditional logic notation.

  Handles quantifiers, connectives, and nested structures:
    forall(X,implies(isa(bird,X),normally(can(X,fly))))
  """
  if formula is None:
    return "null"
  if isinstance(formula, bool):
    return "true" if formula else "false"
  if isinstance(formula, (int, float)):
    return str(formula)
  if isinstance(formula, str):
    return _logic_name(formula)
  if not isinstance(formula, list) or not formula:
    return str(formula)

  op = formula[0]
  if not isinstance(op, str):
    # List of atoms (clause-level) — shouldn't normally reach here
    return "[" + ", ".join(formula_to_logic(el) for el in formula) + "]"

  # Connectives rendered as infix operators
  _INFIX = {"and": " & ", "or": " | ", "implies": " => ",
            "equivalent": " <=> ", "xor": " xor "}
  if op in _INFIX and len(formula) >= 3:
    sep = _INFIX[op]
    parts = [formula_to_logic(a) for a in formula[1:]]
    inner = sep.join(parts)
    s = "(" + inner + ")"
    if len(s) > max_len:
      s = "(" + ("\n  " + sep.strip() + " ").join(parts) + ")"
    return s

  # Quantifiers: forall(X,body), exists(X,body)
  if op in ("forall", "exists") and len(formula) >= 3:
    var = _logic_name(formula[1])
    body = formula_to_logic(formula[2], max_len=max_len)
    return op + "(" + var + "," + body + ")"

  # Negation
  if op == "not" and len(formula) >= 2:
    return "-" + formula_to_logic(formula[1], max_len=max_len)

  # Structural wrappers: @id, holds, question, ask, normally, etc.
  if op == "@id" and len(formula) >= 3:
    sid = str(formula[1])
    body = formula_to_logic(formula[2], max_len=max_len)
    return "@id(" + sid + "," + body + ")"
  if op == "holds" and len(formula) >= 3:
    w = _logic_name(formula[1])
    body = formula_to_logic(formula[2], max_len=max_len)
    return "holds(" + w + "," + body + ")"
  if op == "question" and len(formula) >= 2:
    return "question(" + formula_to_logic(formula[1], max_len=max_len) + ")"
  if op == "ask" and len(formula) >= 3:
    var = _logic_name(formula[1])
    body = formula_to_logic(formula[2], max_len=max_len)
    return "ask(" + var + "," + body + ")"
  if op == "normally" and len(formula) >= 2:
    return "normally(" + formula_to_logic(formula[1], max_len=max_len) + ")"

  # Default: predicate/function application
  return _atom_to_logic(formula)
