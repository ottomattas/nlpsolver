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


# Proper-name bases that appear with more than one distinct number in the
# current proof (e.g. "John" when both "John 1" and "John 3" are present).
# Set once by _compute_ambiguity() before any rendering begins.
_ambiguous_bases = set()

# URL display names (last path segment) that map to two or more different URLs.
# When a name is in this set, the full URL is appended even in the answer line.
_ambiguous_url_names = set()

# Map from Skolem constant name (e.g. "sk0") to its type string (e.g. "animal"),
# derived by scanning proof steps for isa(TYPE, skN) atoms.
# Reset per proof by _compute_skolem_types().
_skolem_types = {}

# Maps from str(skolem_function_term) to verb/actor/target strings,
# derived by scanning proof steps for has_type/has_actor/has_target atoms
# whose subject is a Skolem function (a list starting with sk\d+).
# Reset per proof by _compute_skolem_types().
_skolem_fn_verbs   = {}   # str(term) -> verb string  (e.g. "eat")
_skolem_fn_actors  = {}   # str(term) -> actor string (e.g. "Greg 2")
_skolem_fn_targets = {}   # str(term) -> target string (e.g. "Mike 1")


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

  # For wh-questions: keep only answers in the best object-type tier
  # (concrete > Skolem > population), preserving the goodness order within tier.
  answers = _filter_by_best_tier(answers)

  # Build sent_SN -> raw sentence text map from stage-1 output
  sentence_map = _build_sentence_map(s1_json)

  # How many $ans arguments are actual answer variables (1 for a single-ask
  # wh-question; None means show all, e.g. yes/no or a pair question).
  askvars = _extract_askvars(logic)

  # Determine which proper-name bases are ambiguous (multiple entities share
  # the same base name, e.g. "John 1" and "John 3") so that rendering can
  # keep the distinguishing number instead of silently dropping it.
  # Scan the full logic input (all clauses sent to the prover) so that
  # entities present in the problem but absent from this specific proof path
  # are still counted.  Fall back to scanning just the answers if logic is None.
  _compute_ambiguity(logic if logic is not None else answers)

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

  Used for the answer line — URLs appear without the parenthetical URL
  unless the display name is ambiguous (maps to 2+ different URLs).
  """
  if not isinstance(atom, list) or len(atom) < 2:
    return str(atom)
  val = atom[1]
  if not isinstance(val, str):
    return str(val)
  # with_url=False: only append URL when the name is ambiguous
  return _entity_name(val, with_url=False)


def _fmt_conf(conf):
  """Format a confidence float as a two-decimal string."""
  return str(round(conf, 2))


def _fmt_pct(conf):
  """Format a confidence float as a percentage string, e.g. 0.81 -> '81%'."""
  return str(round(conf * 100)) + "%"


def _extract_step_conf(reason):
  """Return the trailing confidence value from a proof step reason, or 1.0."""
  if not isinstance(reason, list) or not reason:
    return 1.0
  last = reason[-1]
  if isinstance(last, float) or (isinstance(last, int) and not isinstance(last, bool)):
    return float(last)
  return 1.0


def _answer_goodness(ans):
  """Sorting key: high confidence, shorter proof is better."""
  conf     = ans.get("confidence", 0)
  length   = len(ans.get("positive proof", [])) + len(ans.get("negative proof", []))
  blockers = 5 * len(ans.get("blockers", []))
  return conf * 10_000_000 - length - blockers


def _ans_object_tier(val):
  """Return the object-type tier for an answer value.

  Tiers (lower is better / more preferred):
    0 -- CONCRETE: a specific named constant (e.g. "John 1", a URL)
    1 -- SKOLEM:   a Skolem constant ("sk0", "sk1", ...)
    2 -- POPULATION: a class-population constant ("$some_*", "$some_not_*")

  Boolean answers (True/False) always return 0 so they are never filtered out.
  When val is a list of $ans atoms, the tier of the *most concrete* atom wins.
  """
  if val is True or val is False or val is None:
    return 0
  if not isinstance(val, list):
    return 0
  best = 2
  for atom in val:
    if not isinstance(atom, list) or len(atom) < 2:
      continue
    s = atom[1]
    if not isinstance(s, str):
      best = 0   # non-string arg → treat as concrete
      break
    if s.startswith("$some_"):
      tier = 2
    elif re.match(r'^sk\d+$', s):
      tier = 1
    else:
      tier = 0
    if tier < best:
      best = tier
    if best == 0:
      break
  return best


def _filter_by_best_tier(answers):
  """Return answers filtered to the best (lowest) object-type tier.

  Boolean answers are never filtered out.  If all answers are boolean,
  or if no object answers exist, the list is returned unchanged.
  """
  tiers = [_ans_object_tier(a.get("answer")) for a in answers]
  obj_tiers = [t for a, t in zip(answers, tiers)
               if not isinstance(a.get("answer"), bool)]
  if not obj_tiers:
    return answers
  best = min(obj_tiers)
  if best == 2:
    # All object answers are population constants — keep them all as-is.
    return answers
  return [a for a, t in zip(answers, tiers)
          if isinstance(a.get("answer"), bool) or t == best]


def _compute_ambiguity(obj):
  """Scan obj and set _ambiguous_bases and _ambiguous_url_names.

  _ambiguous_bases: proper-name bases appearing with 2+ distinct numbers
    (e.g. "John" when both "John 1" and "John 3" are present).
  _ambiguous_url_names: URL display names that resolve to 2+ different URLs
    (e.g. "Paris" if two different Paris URLs appear).
  """
  global _ambiguous_bases, _ambiguous_url_names
  base_numbers = {}   # base -> set of ints
  url_names    = {}   # display_name -> set of URLs
  _scan_constants(obj, base_numbers, url_names)
  _ambiguous_bases     = {b for b, nums in base_numbers.items() if len(nums) > 1}
  _ambiguous_url_names = {n for n, urls in url_names.items()    if len(urls)  > 1}


def _scan_constants(obj, base_numbers, url_names):
  """Recursively scan obj for proper-name constants and URL constants."""
  if isinstance(obj, str):
    if obj.startswith("?:"):
      return
    if obj.startswith("http://") or obj.startswith("https://"):
      name = _extract_url_name(obj)
      url_names.setdefault(name, set()).add(obj)
      return
    m = re.match(r'^(.*\S)\s+(\d+)$', obj)
    if m:
      base = m.group(1)
      if base[:1].isupper():
        base_numbers.setdefault(base, set()).add(int(m.group(2)))
  elif isinstance(obj, list):
    for el in obj:
      _scan_constants(el, base_numbers, url_names)
  elif isinstance(obj, dict):
    for v in obj.values():
      _scan_constants(v, base_numbers, url_names)


def _is_skolem_fn(val):
  """Return True if val is a Skolem function term: a list whose first element
  matches sk\\d+ (e.g. ["sk0", "Greg 2", "Mike 1"])."""
  return (isinstance(val, list) and val and
          isinstance(val[0], str) and re.match(r'^sk\d+$', val[0]))


def _compute_skolem_types(proof):
  """Scan proof steps and populate Skolem lookup tables.

  _skolem_types      : skN (string constant) -> type string from isa(TYPE,skN)
  _skolem_fn_verbs   : str(fn_term) -> verb   from has_type(fn_term, VERB)
  _skolem_fn_actors  : str(fn_term) -> actor  from has_actor(fn_term, ACTOR)
  _skolem_fn_targets : str(fn_term) -> target from has_target(fn_term, TARGET)

  Called once per proof before rendering.  Only the first fact for each key
  is kept.
  """
  global _skolem_types, _skolem_fn_verbs, _skolem_fn_actors, _skolem_fn_targets
  _skolem_types     = {}
  _skolem_fn_verbs  = {}
  _skolem_fn_actors = {}
  _skolem_fn_targets = {}
  for step in proof:
    clause = step[2] if len(step) > 2 else []
    if not isinstance(clause, list):
      continue
    for atom in clause:
      if not isinstance(atom, list) or len(atom) < 3:
        continue
      pred = atom[0]
      # isa(TYPE, skN) — for simple Skolem constants
      if pred == "isa" and isinstance(atom[2], str) and re.match(r'^sk\d+$', atom[2]):
        _skolem_types.setdefault(atom[2], str(atom[1]))
      # has_type / has_actor / has_target where subject is a Skolem function
      elif pred == "has type" and _is_skolem_fn(atom[1]):
        key = str(atom[1])
        _skolem_fn_verbs.setdefault(key, str(atom[2]))
      elif pred == "has actor" and _is_skolem_fn(atom[1]):
        key = str(atom[1])
        _skolem_fn_actors.setdefault(key, str(atom[2]))
      elif pred == "has target" and _is_skolem_fn(atom[1]):
        key = str(atom[1])
        _skolem_fn_targets.setdefault(key, str(atom[2]))


def _extract_url_name(url):
  """Extract a human-readable display name from a URL.

  Takes the last non-empty path segment, strips URL encoding, converts
  underscores to spaces.  Falls back to the full URL if no segment found.

  Examples:
    https://en.wikipedia.org/wiki/Paris            -> "Paris"
    https://en.wikipedia.org/wiki/New_York_City    -> "New York City"
    https://dbpedia.org/resource/Eiffel_Tower      -> "Eiffel Tower"
  """
  try:
    # Drop query string and fragment
    path = url.split("?")[0].split("#")[0]
    segments = [s for s in path.split("/") if s]
    # segments[0] is the scheme-less domain; name is the last path component
    # (index >= 2 means there is at least one path element after the domain)
    if len(segments) >= 2:
      name = segments[-1]
    elif segments:
      name = segments[-1]
    else:
      return url
    # Basic URL decoding and underscore expansion
    name = name.replace("_", " ").replace("%20", " ").replace("%27", "'")
    return name if name else url
  except Exception:
    return url


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

    proof = ans.get("positive proof") or ans.get("negative proof")
    if not proof:
      continue

    # Which sent_* names appear in this proof?
    used_names   = _collect_sent_names(proof)
    sorted_names = sorted(used_names, key=_sent_name_sort_key)

    # Deduplicate by raw text: multiple ASUs from the same source sentence
    # share the same raw string and must share the same sentence number.
    sent_nr    = {}   # sent_SN -> display number
    seen_raws  = {}   # raw text -> display number (first assigned)
    sent_lines = ["Sentences used:"]
    for name in sorted_names:
      raw = sentence_map.get(name, name)
      if raw not in seen_raws:
        nr = len(seen_raws) + 1
        seen_raws[raw] = nr
        sent_lines.append("  (" + str(nr) + ") " + raw)
      sent_nr[name] = seen_raws[raw]

    # Proof step list — use "by contradiction" header when proof ends in Contradiction.
    _compute_skolem_types(proof)
    is_contradiction = any(len(s) > 2 and s[2] is False for s in proof)
    proof_header = "Proof steps (by contradiction):" if is_contradiction else "Proof steps:"
    step_lines = [proof_header]
    for step in proof:
      step_lines.append(_format_step(step, sent_nr, show_logic=show_logic))

    # Append exceptions section from answer-level blockers (grounded constants).
    blockers = ans.get("blockers", [])
    if blockers:
      blocker_strs = [_block_to_english(blk) for blk in blockers]
      blocker_strs = [s for s in blocker_strs if s]
      if blocker_strs:
        step_lines.append("Exceptions checked and not holding:")
        for bs in blocker_strs:
          step_lines.append("  " + bs)

    block = "\n".join(sent_lines) + "\n" + "\n".join(step_lines)

    conf = ans.get("confidence", 1)
    if conf < 0.9999:
      block = "Confidence " + _fmt_pct(conf) + ".\n" + block

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
  conf       = _extract_step_conf(reason)
  if conf < 0.9999:
    why_str = why_str + ", confidence " + _fmt_pct(conf)
  line = "  (" + str(nr) + ") " + clause_str + "  [" + why_str + "]"
  if show_logic:
    line += "\n        " + _format_clause_logic(clause)
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
      return "negated question"
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

def _block_to_english(block_atom):
  """Render a $block atom as an English exception string.

  Structure: ["$block", PRIORITY, ["$not", INNER_ATOM]]
  Returns the negated rendering of INNER_ATOM (e.g. "John cannot fly"),
  or "" if the atom is malformed.
  """
  if not isinstance(block_atom, list) or len(block_atom) < 3:
    return ""
  inner = block_atom[2]
  if (isinstance(inner, list) and inner and inner[0] == "$not"
      and len(inner) > 1 and isinstance(inner[1], list)):
    return _atom_to_english_negated(inner[1])
  if isinstance(inner, list):
    return _atom_to_english(inner)
  return str(inner)


def _format_clause_logic(clause):
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


def _clause_to_str(clause):
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

  conditions    = []   # positively-rendered negated atoms -> "if ..."
  neg_atoms     = []   # base atoms (pred without "-") for pure-negative rendering
  consequences  = []   # positively-rendered positive atoms -> "then ..."
  blocker_texts = []   # "except when ..." rendered from $block atoms

  for atom in clause:
    if not isinstance(atom, list) or not atom:
      continue
    pred = str(atom[0])
    if pred == "$block":
      bt = _block_to_english(atom)
      if bt:
        blocker_texts.append(bt)
    elif pred == "$ans":
      consequences.append(_ans_atom_name(atom) + " is an answer")
    elif pred.startswith("-"):
      base = [pred[1:]] + list(atom[1:])
      conditions.append(_atom_to_english(base))
      neg_atoms.append(base)
    else:
      consequences.append(_atom_to_english(atom))

  if conditions and consequences:
    result = "if " + " and ".join(conditions) + " then " + " or ".join(consequences)
  elif consequences:
    result = " or ".join(consequences)
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


# ---- entity name helper ----

# Safe letters for labelling noun-phrase constants.
# Skips letters that are common stage-2 variable names (E, K, N, S, V, X, Y, Z)
# so that "car B" can never be confused with a proof variable.
_SAFE_LETTERS = "ABCDFGHIJLMPQRTUW"   # 17 slots; enough for any realistic proof

# Prepositions used as relations in ["is rel2", RELATION, E1, E2].
# These render as "E1 is RELATION E2" (no "of").
# Anything else (relational nouns: parent, part, member, …) renders as
# "E1 is RELATION of E2".
_PREPOSITIONS = {
  "in", "at", "on", "near", "by", "beside", "under", "above", "below",
  "over", "inside", "outside", "between", "through", "around", "across",
  "before", "after", "within", "from", "to", "into", "onto", "upon",
  "behind", "beyond", "along", "among", "toward", "towards",
  "with", "without", "during", "since", "until", "till", "off", "up", "down",
  "next to", "close to", "far from",
}


def _conjugate_verb(v):
  """Third-person singular present tense of a bare verb (simple heuristic)."""
  if v.endswith(("s", "sh", "ch", "x", "z")):
    return v + "es"
  if v.endswith("y") and len(v) > 1 and v[-2] not in "aeiou":
    return v[:-1] + "ies"
  return v + "s"


def _to_gerund(verb):
  """Return the gerund (-ing) form of a bare verb (simple heuristic).

  eat->eating, bark->barking, run->running, bite->biting, study->studying.
  """
  if not verb:
    return verb + "ing"
  # lie/die -> lying/dying
  if verb.endswith("ie"):
    return verb[:-2] + "ying"
  # bake/bite/save -> baking/biting/saving  (drop silent e, but not ee/oe)
  if (verb.endswith("e") and len(verb) > 2
      and verb[-2] not in "aeiou" and not verb.endswith("ee")):
    return verb[:-1] + "ing"
  # run/sit/get -> running/sitting/getting  (CVC, double final consonant)
  vowels = "aeiou"
  if (len(verb) >= 3
      and verb[-1] not in vowels + "wxyhz"
      and verb[-2] in vowels
      and verb[-3] not in vowels):
    return verb + verb[-1] + "ing"
  return verb + "ing"


def _skolem_fn_to_name(term):
  """Render a Skolem function term ["sk0", arg1, arg2, ...] as English.

  Uses _skolem_fn_verbs / _skolem_fn_actors / _skolem_fn_targets (populated by
  _compute_skolem_types) to describe the reified event.

  Examples:
    ["sk0","Greg 2","Mike 1"]  -> "the eating by Greg of Mike"
    ["sk0","?:X","Mike 1"]     -> "the eating of Mike"
    ["sk0","?:X","?:Y"]        -> "the eating event"
    (no verb found)            -> "the event"
  """
  key  = str(term)
  verb = _skolem_fn_verbs.get(key)
  if not verb:
    return "the event"
  gerund = _to_gerund(verb)

  actor_raw  = _skolem_fn_actors.get(key, "")
  target_raw = _skolem_fn_targets.get(key, "")

  # Only use ground (non-variable) actor/target in the description
  actor  = actor_raw  if actor_raw  and not actor_raw.startswith("?:") else ""
  target = target_raw if target_raw and not target_raw.startswith("?:") else ""

  if actor and target:
    return "the " + gerund + " by " + _entity_name(actor) + " of " + _entity_name(target)
  if actor:
    return "the " + gerund + " by " + _entity_name(actor)
  if target:
    return "the " + gerund + " of " + _entity_name(target)
  return "the " + gerund + " event"


def _entity_name(val, with_url=False):
  """Display name for a logic constant or variable.

  - Skolem functions (lists)  -> "the eating by Greg of Mike" etc.
  - Variables (?:X)           -> strip prefix -> "X"
  - URL constants             -> extract last path segment ->
                                   "Paris" or "Paris (https://...)" depending
                                   on with_url and _ambiguous_url_names
  - Proper-name constants     -> strip trailing number -> "John 1" -> "John"
                                 (keeps number when base is in _ambiguous_bases)
  - Noun-phrase constants     -> replace number with safe letter ->
                                 "car 2" -> "car B",  "dog 1" -> "dog A"

  with_url=True  : append full URL in parentheses for URL constants
                   (used in proof steps for traceability)
  with_url=False : omit URL unless the display name is ambiguous
                   (used in answer line for readability)
  """
  if _is_skolem_fn(val):
    return _skolem_fn_to_name(val)
  if not isinstance(val, str):
    return str(val)
  if val.startswith("?:"):
    val = val[2:]
  # Population constants: $some_not_* -> "some non-*",  $some_* -> "some *"
  if val.startswith("$some_not_"):
    return "some non-" + val[len("$some_not_"):].replace("_", " ")
  if val.startswith("$some_"):
    return "some " + val[len("$some_"):].replace("_", " ")
  # Skolem constants: sk0, sk1, ... -> "some TYPE skN" using proof context
  if re.match(r'^sk\d+$', val):
    typ = _skolem_types.get(val)
    if typ:
      return "some " + typ + " " + val
    return val
  # URL constant
  if val.startswith("http://") or val.startswith("https://"):
    name = _extract_url_name(val)
    if with_url or name in _ambiguous_url_names:
      return name + " (" + val + ")"
    return name
  m = re.match(r'^(.*\S)\s+(\d+)$', val)
  if not m:
    return val
  base = m.group(1)
  n    = int(m.group(2))
  if base[:1].isupper():
    # Proper name — keep the number when multiple entities share the same base
    # (e.g. "John 1" vs "John 3"); drop it when there is only one "John".
    if base in _ambiguous_bases:
      return base + " " + str(n)
    return base
  # Noun-phrase constant — replace number with a safe letter
  if 1 <= n <= len(_SAFE_LETTERS):
    label = _SAFE_LETTERS[n - 1]        # 1->A, 2->B, 3->C, 4->D, 5->F, …
  else:
    label = str(n)                       # fallback for very large indices
  return base + " " + label


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
    """Display name of args[i] — always with URL appended for URL constants."""
    if i >= len(args):
      return "?"
    return _entity_name(args[i], with_url=True)

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
      rel = e(0)
      last = rel.split()[-1].lower() if rel else ""
      if rel.lower() in _PREPOSITIONS or last in _PREPOSITIONS or last == "of":
        return e(1) + " is " + rel + " " + e(2)
      return e(1) + " is " + rel + " of " + e(2)
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
      last = rel.split()[-1].lower() if rel else ""
      if last in _PREPOSITIONS or last == "of":
        return ent1 + " is " + adv + rel + " " + ent2
      if " " not in rel:
        return ent1 + " " + adv + _conjugate_verb(rel) + " " + ent2
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

  if pred == "typically":
    # ["typically", ENTITY, VERB]
    if len(args) >= 2:
      return e(0) + " typically " + _conjugate_verb(str(args[1]))
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

  # ---- $defq* question-definition atoms ----

  if pred.startswith("$defq"):
    if not args:
      return "answer holds"
    if len(args) == 1:
      return e(0) + " is an answer"
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
      parts.append(_entity_name(a, with_url=True))
    elif isinstance(a, list):
      parts.append(_atom_to_english(a))
    else:
      parts.append(str(a))
  return pred + "(" + ", ".join(parts) + ")" if parts else pred


def _atom_to_english_negated(atom):
  """Render a single atom in its natural negated English form.

  Used for pure-negative clauses (all atoms negated, no positive atoms) so
  that "X is not Y" / "X does not have Y" is produced instead of the
  awkward "not: X is Y".  Falls back to "not: " + positive form for any
  predicate not explicitly listed here.

  The atom argument is the BASE atom (predicate name WITHOUT the leading "-").
  """
  if not isinstance(atom, list) or not atom:
    return "not: " + str(atom)

  pred = str(atom[0])
  args = atom[1:]

  def e(i):
    if i >= len(args): return "?"
    return _entity_name(args[i], with_url=True)

  # ---- core predicates ----

  if pred == "isa":
    if len(args) >= 2:
      typ = e(0); ent = e(1)
      if typ == "activity": return ent + " is not an activity"
      if typ == "set":      return ent + " is not a set"
      return ent + " is not " + _indef_article(typ) + " " + typ
    return "not: " + _atom_fallback(atom)

  if pred == "has property":
    if len(args) >= 2:
      return e(1) + " is not " + e(0)
    return "not: " + _atom_fallback(atom)

  if pred == "have":
    if len(args) >= 2:
      return e(0) + " does not have " + e(1)
    return "not: " + _atom_fallback(atom)

  if pred == "has part":
    if len(args) >= 2:
      return e(0) + " does not have " + e(1) + " as a part"
    return "not: " + _atom_fallback(atom)

  if pred == "is rel2":
    if len(args) >= 3:
      rel = e(0)
      last = rel.split()[-1].lower() if rel else ""
      if rel.lower() in _PREPOSITIONS or last in _PREPOSITIONS or last == "of":
        return e(1) + " is not " + rel + " " + e(2)
      return e(1) + " is not " + rel + " of " + e(2)
    return "not: " + _atom_fallback(atom)

  if pred == "can":
    if len(args) >= 2:
      return e(0) + " cannot " + e(1)
    return "not: " + _atom_fallback(atom)

  # ---- gradable predicates ----

  if pred == "has degree property":
    if len(args) >= 4:
      prop = e(0); ent = e(1)
      adv, art_type = _degree_parts(e(2))
      relcls = e(3)
      art = "the" if art_type == "def" else _indef_article(adv if adv else prop)
      return ent + " is not " + art + " " + adv + prop + " " + relcls
    return "not: " + _atom_fallback(atom)

  if pred == "has degree rel2":
    if len(args) >= 4:
      adv, _ = _degree_parts(e(3))
      rel = e(0)
      last = rel.split()[-1].lower() if rel else ""
      if last in _PREPOSITIONS or last == "of":
        return e(1) + " is not " + adv + rel + " " + e(2)
      if " " not in rel:
        return e(1) + " does not " + adv + rel + " " + e(2)
      return e(1) + " is not " + adv + rel + " of " + e(2)
    return "not: " + _atom_fallback(atom)

  # ---- event reification predicates ----

  if pred == "has type":
    if len(args) >= 2:
      return e(0) + " is not a " + e(1) + " event"
    return "not: " + _atom_fallback(atom)

  if pred == "has actor":
    if len(args) >= 2:
      return e(1) + " does not perform " + e(0)
    return "not: " + _atom_fallback(atom)

  if pred == "has target":
    if len(args) >= 2:
      return e(0) + " does not target " + e(1)
    return "not: " + _atom_fallback(atom)

  if pred == "has location":
    if len(args) >= 2:
      return e(0) + " does not take place at " + e(1)
    return "not: " + _atom_fallback(atom)

  if pred == "has instrument":
    if len(args) >= 2:
      return e(0) + " does not use " + e(1)
    return "not: " + _atom_fallback(atom)

  if pred == "has manner":
    if len(args) >= 2:
      return e(0) + " does not happen in a " + e(1) + " manner"
    return "not: " + _atom_fallback(atom)

  if pred == "has direction":
    if len(args) >= 2:
      return e(0) + " does not go towards " + e(1)
    return "not: " + _atom_fallback(atom)

  if pred == "has time":
    if len(args) >= 2:
      return e(0) + " does not happen at " + e(1)
    return "not: " + _atom_fallback(atom)

  if pred == "typical":
    if len(args) >= 1:
      return e(0) + " is not typical"
    return "not typical"

  if pred == "typically":
    if len(args) >= 2:
      return e(0) + " does not typically " + str(args[1])
    return "not typically"

  # ---- state / world predicates ----

  if pred == "holds":
    if len(args) >= 2 and isinstance(args[1], list):
      return _atom_to_english_negated(args[1])
    return "not: " + _atom_fallback(atom)

  # ---- set predicates ----

  if pred == "is set of":
    if len(args) >= 2:
      return e(1) + " is not a set of " + e(0)
    return "not: " + _atom_fallback(atom)

  if pred == "member":
    if len(args) >= 2:
      return e(0) + " is not a member of " + e(1)
    return "not: " + _atom_fallback(atom)

  if pred == "member has property":
    if len(args) >= 2:
      return "members of " + e(1) + " are not " + e(0)
    return "not: " + _atom_fallback(atom)

  if pred == "is subset of":
    if len(args) >= 2:
      return e(0) + " is not a subset of " + e(1)
    return "not: " + _atom_fallback(atom)

  # ---- comparison predicates ----

  if pred == "=":
    if len(args) >= 2:
      return e(0) + " does not equal " + e(1)
    return "not: " + _atom_fallback(atom)

  if pred == "<":
    if len(args) >= 2:
      return e(0) + " is not less than " + e(1)
    return "not: " + _atom_fallback(atom)

  if pred == ">":
    if len(args) >= 2:
      return e(0) + " is not greater than " + e(1)
    return "not: " + _atom_fallback(atom)

  # ---- $defq* ----

  if pred.startswith("$defq"):
    if not args:      return "the answer does not hold"
    if len(args) == 1: return e(0) + " is not an answer"
    return "not: " + _atom_fallback(atom)

  # ---- fallback ----

  return "not: " + _atom_to_english(atom)


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
