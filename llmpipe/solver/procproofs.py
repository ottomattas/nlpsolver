# Proof result processing for the llm-based nlpsolver.
#
# Entry point: process_proof(proof_result, text=None, s1_json=None, logic=None, options=None)
# Called by solve.py after the theorem prover returns its raw result.
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

import json
import re


# ======== main entry point ========

def process_proof(proof_result, text=None, s1_json=None, logic=None, options=None):
  """Post-process the raw prover result into a final answer string.

  Arguments:
    proof_result -- raw JSON string returned by prover.call_prover()
    text         -- the original English input (for context / fallback)
    s1_json      -- stage-1 ASU list; used to map clause names to raw sentences
    logic        -- the logic list sent to the prover (unused for now)
    options      -- dict of option flags, e.g. {"prover_explain_flag": True,
                    "show_logic_flag": True}

  Returns the final answer string.
  """
  if options is None:
    options = {}

  # Parse prover JSON
  data = _parse_result(proof_result)
  if isinstance(data, str):       # _parse_result returned an error string
    return data

  # Top-level error / no answer
  if "error" in data:
    return "Error: " + str(data["error"])
  if data.get("result") != "answer found":
    return "Unknown."

  answers = data.get("answers", [])
  if not answers:
    return "Unknown."

  # Sort: highest confidence first, shorter proofs preferred
  answers = sorted(answers, key=_answer_goodness, reverse=True)

  # Build sent_SN -> raw sentence text map from stage-1 output
  sentence_map = _build_sentence_map(s1_json)

  # How many $ans arguments are actual answer variables (1 for a single-ask
  # wh-question; None means show all, e.g. yes/no or a pair question).
  askvars = _extract_askvars(logic)

  # Format the answer value(s)
  answer_str = _format_answers(answers, askvars=askvars)

  # Optionally append a step-by-step proof explanation
  explain     = options.get("prover_explain_flag", False)
  show_logic  = options.get("show_logic_flag", False)
  if explain:
    explanation = _format_explanation(answers, sentence_map, show_logic=show_logic)
    if explanation:
      answer_str = answer_str + "\n\n" + explanation

  return answer_str


# ======== answer formatting ========

def _extract_askvars(logic):
  """Return the @askvars count from the @question clause in logic, or None."""
  if not logic or not isinstance(logic, list):
    return None
  for obj in logic:
    if isinstance(obj, dict) and "@question" in obj and "@askvars" in obj:
      try:
        return int(obj["@askvars"])
      except (TypeError, ValueError):
        return None
  return None


def _format_answers(answers, askvars=None):
  """Collect answer values from all (non-duplicate) answer entries and join.

  askvars: if set, only the first askvars $ans atoms in each answer are
  shown in the output (the rest are auxiliary existential variables).
  The detailed proof explanation is unaffected.
  """
  parts = []
  seen  = []
  for ans in answers:
    val  = ans.get("answer")
    conf = ans.get("confidence", 1)
    if val in seen:
      continue
    seen.append(val)

    if val is True:
      s = "True"
    elif val is False:
      s = "False"
    elif isinstance(val, list) and val:
      # Each element is an $ans atom like ["$ans", "John 1"].
      # If askvars is set, only show the first askvars atoms (the
      # rest are auxiliary variables not being asked for).
      display = val[:askvars] if askvars is not None else val
      names = [_ans_atom_name(a) for a in display]
      s = "(" + " or ".join(names) + ")" if len(names) > 1 else names[0] if names else str(val)
    else:
      s = str(val)

    if conf < 0.99:
      s += " (confidence " + _fmt_conf(conf) + ")"
    parts.append(s)

  if not parts:
    return "Could not find an answer."

  if len(parts) == 1:
    res = parts[0]
  elif len(parts) == 2:
    res = parts[0] + " and " + parts[1]
  else:
    res = ", ".join(parts[:-1]) + " and " + parts[-1]

  if res and res[0].islower():
    res = res[0].upper() + res[1:]
  if not res.endswith("."):
    res += "."
  return res


def _ans_atom_name(atom):
  """Return the display name from a $ans atom like ["$ans", "John 1"].

  Strips the trailing disambiguation number (e.g. "John 1" -> "John",
  "Mike 2" -> "Mike").  Leaves the value unchanged if it has no suffix.
  """
  if not isinstance(atom, list) or len(atom) < 2:
    return str(atom)
  val = atom[1]
  if not isinstance(val, str):
    return str(val)
  if val.startswith("?:"):       # strip variable prefix ("?:X" -> "X")
    val = val[2:]
  m = re.match(r'^(.*)\s+\d+$', val)
  return m.group(1) if m else val


def _fmt_conf(conf):
  """Format a confidence float as a two-decimal string."""
  return str(round(conf, 2))


def _answer_goodness(ans):
  """Sorting key: high confidence, shorter proof is better."""
  conf     = ans.get("confidence", 0)
  length   = len(ans.get("positive proof", [])) + len(ans.get("negative proof", []))
  blockers = 5 * len(ans.get("blockers", []))
  return conf * 10_000_000 - length - blockers


# ======== sentence map ========

def _build_sentence_map(s1_json):
  """Build {"sent_S1": "John is nice.", "sent_S2": ..., ...} from stage-1 output.

  s1_json is a list of sentence objects:
    [{"raw": "John is nice.", "units": [{"unit_id": "S1", ...}, ...]}, ...]

  Each unit's unit_id maps to the raw sentence it came from.
  Returns an empty dict if s1_json is None or malformed.
  """
  result = {}
  if not s1_json or not isinstance(s1_json, list):
    return result
  for sent_obj in s1_json:
    if not isinstance(sent_obj, dict):
      continue
    raw = sent_obj.get("raw", "")
    for unit in sent_obj.get("units", []):
      if not isinstance(unit, dict):
        continue
      uid = unit.get("unit_id", "")
      if uid:
        result["sent_" + uid] = raw
  return result


# ======== explanation formatting ========

def _format_explanation(answers, sentence_map, show_logic=False):
  """Build a step-by-step proof explanation for all (non-duplicate) answers."""
  blocks    = []
  seen_vals = []
  multi     = _count_distinct_answers(answers) > 1

  for ans in answers:
    val   = ans.get("answer")
    if val in seen_vals:
      continue
    seen_vals.append(val)

    proof = ans.get("positive proof")
    if not proof:
      continue

    # Which sent_* names appear in this proof?
    used_names  = _collect_sent_names(proof)
    sorted_names = sorted(used_names, key=_sent_name_sort_key)
    sent_nr     = {name: i + 1 for i, name in enumerate(sorted_names)}

    # Numbered sentence list
    sent_lines = ["Sentences used:"]
    for name in sorted_names:
      raw = sentence_map.get(name, name)
      sent_lines.append("  (" + str(sent_nr[name]) + ") " + raw)

    # Proof step list
    step_lines = ["Proof steps:"]
    for step in proof:
      step_lines.append(_format_step(step, sent_nr, show_logic=show_logic))

    block = "\n".join(sent_lines) + "\n" + "\n".join(step_lines)

    if multi:
      label = _answer_label(val)
      block = label + ":\n" + block

    blocks.append(block)

  if not blocks:
    return ""
  return "Explained:\n\n" + "\n\n".join(blocks)


def _count_distinct_answers(answers):
  seen = []
  for ans in answers:
    v = ans.get("answer")
    if v not in seen:
      seen.append(v)
  return len(seen)


def _collect_sent_names(proof):
  """Return the set of sent_* clause names referenced in a proof."""
  names = set()
  for step in proof:
    reason = step[1] if len(step) > 1 else []
    if isinstance(reason, list) and reason and reason[0] == "in":
      name = reason[1] if len(reason) > 1 else ""
      if isinstance(name, str) and name.startswith("sent_"):
        names.add(name)
  return names


def _sent_name_sort_key(name):
  """Numeric sort key for sent_SN names (sent_S4 -> 4)."""
  m = re.search(r'\d+$', name)
  return int(m.group()) if m else 0


def _format_step(step, sent_nr, show_logic=False):
  """Render one proof step as a readable line."""
  nr     = step[0] if len(step) > 0 else "?"
  reason = step[1] if len(step) > 1 else []
  clause = step[2] if len(step) > 2 else []

  clause_str = _clause_to_str(clause)
  why_str    = _format_why(reason, sent_nr)
  line       = "  (" + str(nr) + ") " + clause_str + "  [" + why_str + "]"
  if show_logic:
    line += "\n        " + str(clause)
  return line


def _format_why(reason, sent_nr):
  """Format the 'why' part of a proof step reason."""
  if not isinstance(reason, list) or not reason:
    return "unknown"
  kind = reason[0]
  if kind == "in":
    source   = reason[1] if len(reason) > 1 else ""
    polarity = reason[2] if len(reason) > 2 else ""
    if polarity == "goal":
      return "from the question"
    if source in sent_nr:
      return "sentence " + str(sent_nr[source])
    return source
  else:
    # Collect integer step references; stop at the first string label
    # ("fromaxiom" / "fromgoal") which precedes the trailing confidence int.
    step_refs = []
    for el in reason[1:]:
      if isinstance(el, str):
        break
      if isinstance(el, int):
        step_refs.append(str(el))
      elif isinstance(el, list) and el and isinstance(el[0], int):
        step_refs.append(str(el[0]))
    if step_refs:
      return kind + " from steps " + ", ".join(step_refs)
    return kind


def _answer_label(val):
  """Short label for use in 'For X:' headings."""
  if val is True:  return "True"
  if val is False: return "False"
  if isinstance(val, list) and val:
    return _ans_atom_name(val[0])
  return str(val)


# ======== clause / atom rendering ========
# Converts CNF proof clauses to readable English.
# A clause is a list of atoms (disjunction); atoms with a "-" prefix are negated.
# Negated atoms are rendered as "if" conditions; positive atoms as "then" consequences.
# _atom_to_english handles every predicate in the stage-2 whitelist.

def _clause_to_str(clause):
  """Convert a proof clause to a human-readable if-then English string."""
  if clause is False or clause is None:
    return "Contradiction"
  if not isinstance(clause, list):
    return str(clause)

  conditions   = []   # negated atoms  -> "if ..."
  consequences = []   # positive atoms -> "then ..."

  for atom in clause:
    if not isinstance(atom, list) or not atom:
      continue
    pred = str(atom[0])
    if pred == "$ans":
      consequences.append(_ans_atom_name(atom) + " is an answer")
    elif pred.startswith("-"):
      conditions.append(_atom_to_english([pred[1:]] + list(atom[1:])))
    else:
      consequences.append(_atom_to_english(atom))

  if conditions and consequences:
    return "if " + " and ".join(conditions) + " then " + " or ".join(consequences)
  if consequences:
    return " or ".join(consequences)
  if conditions:
    return "not: " + " and ".join(conditions)
  return "(empty)"


# ---- entity name helper ----

def _entity_name(val):
  """Display name for a logic constant or variable.

  Strips the ?:-variable prefix and trailing disambiguation numbers
  (e.g. 'John 1' -> 'John', '?:X' -> 'X', 'W0' -> 'W0').
  World constants (W0, W1, ...) are returned unchanged.
  """
  if not isinstance(val, str):
    return str(val)
  if val.startswith("?:"):
    val = val[2:]
  m = re.match(r'^(.*\S)\s+\d+$', val)
  if m:
    val = m.group(1)
  return val


# ---- degree / gradable helpers ----

_DEGREE_TABLE = {
  "none":    ("",           "indef"),   # "a nice person"
  "":        ("",           "indef"),
  "regular": ("",           "indef"),
  "high":    ("very ",      "indef"),   # "a very nice person"
  "low":     ("slightly ",  "indef"),   # "a slightly nice person"
  "more":    ("more ",      "indef"),   # "a more nice person"
  "most":    ("most ",      "def"),     # "the most nice person"
  "less":    ("less ",      "indef"),
  "least":   ("least ",     "def"),     # "the least nice person"
}

def _degree_parts(degree):
  """Return (adverb_str, article_type) for a degree value."""
  key = str(degree).lower()
  if key in _DEGREE_TABLE:
    return _DEGREE_TABLE[key]
  # Numeric degree (0..1 or 0..100): map to rough adverbs
  try:
    n = float(key)
    if n > 0.75:
      return ("very ",     "indef")
    if n < 0.25:
      return ("slightly ", "indef")
    return ("",            "indef")
  except ValueError:
    return (key + " ",     "indef")

def _indef_article(word):
  """'an' before vowel sounds, 'a' otherwise."""
  return "an" if word[:1].lower() in "aeiou" else "a"


# ---- main atom-to-English converter ----

def _atom_to_english(atom):
  """Convert a single logic atom to readable English.

  Handles every predicate in the stage-2 whitelist.  Falls back to
  pred(arg1, arg2, ...) notation for anything unrecognised.
  """
  if not isinstance(atom, list) or not atom:
    return str(atom)

  pred = str(atom[0])
  args = atom[1:]

  def e(i):
    """Display name of args[i]."""
    if i >= len(args):
      return "?"
    v = args[i]
    return _entity_name(v) if isinstance(v, str) else str(v)

  # ---- core predicates ----

  if pred == "isa":
    # ["isa", TYPE, ENTITY]
    if len(args) >= 2:
      typ = e(0)
      ent = e(1)
      if typ == "activity":
        return ent + " is an activity"
      if typ == "set":
        return ent + " is a set"
      art = _indef_article(typ)
      return ent + " is " + art + " " + typ
    return _atom_fallback(atom)

  if pred == "has property":
    # ["has property", PROPERTY, ENTITY]
    if len(args) >= 2:
      return e(1) + " is " + e(0)
    return _atom_fallback(atom)

  if pred == "have":
    # ["have", OWNER, OWNED]
    if len(args) >= 2:
      return e(0) + " has " + e(1)
    return _atom_fallback(atom)

  if pred == "has part":
    # ["has part", WHOLE, PART]
    if len(args) >= 2:
      return e(0) + " has " + e(1) + " as a part"
    return _atom_fallback(atom)

  if pred == "is rel2":
    # ["is rel2", RELATION, ENTITY1, ENTITY2]
    if len(args) >= 3:
      return e(1) + " is " + e(0) + " of " + e(2)
    return _atom_fallback(atom)

  if pred == "can":
    # ["can", ENTITY, ACTION]
    if len(args) >= 2:
      return e(0) + " can " + e(1)
    return _atom_fallback(atom)

  # ---- gradable predicates ----

  if pred == "has degree property":
    # ["has degree property", PROPERTY, ENTITY, DEGREE, RELCLASS]
    if len(args) >= 4:
      prop    = e(0)
      ent     = e(1)
      adv, art_type = _degree_parts(e(2))
      relcls  = e(3)
      if art_type == "def":
        art = "the"
      else:
        art = _indef_article(adv if adv else prop)
      return ent + " is " + art + " " + adv + prop + " " + relcls
    return _atom_fallback(atom)

  if pred == "has degree rel2":
    # ["has degree rel2", RELATION, ENTITY1, ENTITY2, DEGREE, RELCLASS]
    if len(args) >= 4:
      rel   = e(0)
      ent1  = e(1)
      ent2  = e(2)
      adv, _ = _degree_parts(e(3))
      return ent1 + " is " + adv + rel + " of " + ent2
    return _atom_fallback(atom)

  # ---- event reification predicates ----

  if pred == "has type":
    # ["has type", EVENT, VERB]
    if len(args) >= 2:
      return e(0) + " is a " + e(1) + " event"
    return _atom_fallback(atom)

  if pred == "has actor":
    # ["has actor", EVENT, ENTITY]
    if len(args) >= 2:
      return e(1) + " performs " + e(0)
    return _atom_fallback(atom)

  if pred == "has target":
    # ["has target", EVENT, ENTITY]
    if len(args) >= 2:
      return e(0) + " targets " + e(1)
    return _atom_fallback(atom)

  if pred == "has location":
    # ["has location", EVENT, LOCATION]
    if len(args) >= 2:
      return e(0) + " takes place at " + e(1)
    return _atom_fallback(atom)

  if pred == "has instrument":
    # ["has instrument", EVENT, INSTRUMENT]
    if len(args) >= 2:
      return e(0) + " uses " + e(1)
    return _atom_fallback(atom)

  if pred == "has manner":
    # ["has manner", EVENT, MANNER]
    if len(args) >= 2:
      return e(0) + " happens in a " + e(1) + " manner"
    return _atom_fallback(atom)

  if pred == "has direction":
    # ["has direction", EVENT, DIRECTION]
    if len(args) >= 2:
      return e(0) + " goes towards " + e(1)
    return _atom_fallback(atom)

  if pred == "has time":
    # ["has time", EVENT, TIME]
    if len(args) >= 2:
      return e(0) + " happens at " + e(1)
    return _atom_fallback(atom)

  if pred == "typical":
    # ["typical", EVENT]
    if len(args) >= 1:
      return e(0) + " is typical"
    return "typically"

  # ---- state / world predicates ----

  if pred == "holds":
    # ["holds", W, FORMULA] — skip the world, render the inner formula
    if len(args) >= 2 and isinstance(args[1], list):
      return _atom_to_english(args[1])
    return _atom_fallback(atom)

  if pred == "state time":
    # ["state time", W, TIME]
    if len(args) >= 2:
      return "at time " + e(1)
    return _atom_fallback(atom)

  if pred == "state location":
    # ["state location", W, LOCATION]
    if len(args) >= 2:
      return "at location " + e(1)
    return _atom_fallback(atom)

  if pred == "next":
    # state transition — not meaningful to display
    return ""

  # ---- defeasible wrapper ----

  if pred == "normally":
    # ["normally", FORMULA]
    if len(args) >= 1 and isinstance(args[0], list):
      return "normally, " + _atom_to_english(args[0])
    return "normally"

  # ---- set predicates ----

  if pred == "is set of":
    # ["is set of", TYPE, SET]
    if len(args) >= 2:
      return e(1) + " is a set of " + e(0)
    return _atom_fallback(atom)

  if pred == "member":
    # ["member", ENTITY, SET]
    if len(args) >= 2:
      return e(0) + " is a member of " + e(1)
    return _atom_fallback(atom)

  if pred == "member has property":
    # ["member has property", PROPERTY, SET]
    if len(args) >= 2:
      return "members of " + e(1) + " are " + e(0)
    return _atom_fallback(atom)

  if pred == "is subset of":
    # ["is subset of", SET1, SET2]
    if len(args) >= 2:
      return e(0) + " is a subset of " + e(1)
    return _atom_fallback(atom)

  if pred == "set union":
    # ["set union", SET1, SET2, RESULT]
    if len(args) >= 3:
      return e(2) + " is the union of " + e(0) + " and " + e(1)
    return _atom_fallback(atom)

  if pred == "$count":
    # ["$count", SET]
    if len(args) >= 1:
      return "count of " + e(0)
    return "$count"

  # ---- comparison predicates ----

  if pred == "=":
    if len(args) >= 2:
      return e(0) + " equals " + e(1)
    return _atom_fallback(atom)

  if pred == "<":
    if len(args) >= 2:
      return e(0) + " is less than " + e(1)
    return _atom_fallback(atom)

  if pred == ">":
    if len(args) >= 2:
      return e(0) + " is greater than " + e(1)
    return _atom_fallback(atom)

  # ---- mental predicates ----

  if pred == "kb":
    # ["kb", K, HOLDER, ATTITUDE, W]
    if len(args) >= 3:
      return e(1) + " " + e(2) + " that ..."
    return _atom_fallback(atom)

  if pred == "kb holds":
    # ["kb holds", K, FORMULA]
    if len(args) >= 2 and isinstance(args[1], list):
      return _atom_to_english(args[1])
    return _atom_fallback(atom)

  if pred == "kb says":
    # ["kb says", K1, K2, FORMULA]
    if len(args) >= 3 and isinstance(args[2], list):
      return e(1) + " says that " + _atom_to_english(args[2])
    return _atom_fallback(atom)

  if pred == "kb force":
    return _atom_fallback(atom)

  # ---- traceability (skip in English) ----

  if pred in ("@id", "@p", "@definite"):
    if pred == "@id" and len(args) >= 2 and isinstance(args[1], list):
      return _atom_to_english(args[1])
    return ""

  # ---- fallback: pred(arg1, arg2, ...) ----

  return _atom_fallback(atom)


def _atom_fallback(atom):
  """Fallback renderer: pred(arg1, arg2) with underscores as spaces."""
  if not isinstance(atom, list) or not atom:
    return str(atom)
  pred = str(atom[0]).replace("_", " ")
  parts = []
  for a in atom[1:]:
    if isinstance(a, str):
      parts.append(_entity_name(a))
    elif isinstance(a, list):
      parts.append(_atom_to_english(a))
    else:
      parts.append(str(a))
  return pred + "(" + ", ".join(parts) + ")" if parts else pred


# ======== JSON parsing ========

def _parse_result(proof_result):
  """Parse the raw prover JSON string. Returns a dict or an error string."""
  if not proof_result:
    return "Error: prover returned empty result."
  if isinstance(proof_result, dict):
    return proof_result
  try:
    return json.loads(proof_result)
  except Exception as e:
    return "Error: could not parse prover result as JSON: " + str(e)


# =========== the end ==========
