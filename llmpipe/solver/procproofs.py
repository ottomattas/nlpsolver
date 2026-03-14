# Proof result processing for the llm-based nlpsolver.
#
# Entry point: process_proof(proof_result, text=None, s1_json=None, logic=None, options=None)
# Called by solve.py after the theorem prover returns its raw result.
#
# This module handles answer selection, filtering, and formatting.
# Rendering is delegated to proof_render.py; explanation formatting to proof_explain.py.
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

from proof_render import (
  compute_ambiguity, entity_name, ans_atom_name,
  set_entity_map, get_entity_display,
)
from proof_explain import format_explanation, build_sentence_map, ans_display_key
from entity_map import build_entity_map


# ======== main entry point ========

def process_proof(proof_result, text=None, s1_json=None, s2_json=None, logic=None, options=None):
  """Post-process the raw prover result into a final answer string.

  Arguments:
    proof_result -- raw JSON string returned by prover.call_prover()
    text         -- the original English input (for context / fallback)
    s1_json      -- stage-1 ASU list; used to map clause names to raw sentences
    s2_json      -- stage-2 logic JSON; used for adjective extraction in entity names
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
  answers = _filter_tautological_population_answers(answers, logic)
  if not answers:
    return "Unknown."

  # Build entity display-name map from stage-1 output (user's original phrasing)
  # and install it in proof_render so that entity_name() uses it globally.
  set_entity_map(build_entity_map(s1_json, s2_json))

  # Build sent_SN -> raw sentence text map from stage-1 output
  sentence_map = build_sentence_map(s1_json)

  # How many $ans arguments are actual answer variables (1 for a single-ask
  # wh-question; None means show all, e.g. yes/no or a pair question).
  askvars = _extract_askvars(logic)

  # Determine which proper-name bases are ambiguous (multiple entities share
  # the same base name, e.g. "John 1" and "John 3") so that rendering can
  # keep the distinguishing number instead of silently dropping it.
  # Scan the full logic input (all clauses sent to the prover) so that
  # entities present in the problem but absent from this specific proof path
  # are still counted.  Fall back to scanning just the answers if logic is None.
  compute_ambiguity(logic if logic is not None else answers)

  # Format the answer value(s)
  if _is_where_query(logic):
    answer_str = _format_where_answers(answers, logic=logic)
  else:
    answer_str = _format_answers(answers, askvars=askvars)

  # Optionally append a step-by-step proof explanation
  explain     = options.get("prover_explain_flag", False)
  show_logic  = options.get("show_logic_flag", False)
  if explain:
    explanation = format_explanation(answers, sentence_map, show_logic=show_logic)
    if explanation:
      answer_str = answer_str + "\n\n" + explanation

  return answer_str


# ======== formatting helpers ========

def _join_and_finish(parts):
  """Join parts with commas/and, capitalize first letter, ensure trailing period."""
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


def _is_where_query(logic):
  """Return True if logic contains a @where_query marker (set by logconvert)."""
  if not logic or not isinstance(logic, list):
    return False
  for obj in logic:
    if isinstance(obj, dict) and obj.get("@where_query"):
      return True
  return False


def _location_entity_name(val, entity_props=None):
  """Format a location entity constant for display in a 'where' answer.

  Checks the entity_map first (user's original phrasing, with qualifier and
  article already incorporated).  Falls back to URL-name extraction and
  common-noun article logic.

  "house 2"             -> "the house"
  "house 3" (red)       -> "the red house"  (entity_map or entity_props lookup)
  "London 1"            -> "London"          (proper noun: no article)
  "https://.../Estonia" -> "Estonia"
  """
  if not isinstance(val, str):
    return str(val)
  # Entity map overrides everything — already has correct article and qualifier
  em = get_entity_display(val)
  if em is not None:
    return em
  # URL constants: use entity_name which extracts the last path segment
  if val.startswith("http://") or val.startswith("https://"):
    return entity_name(val, with_url=False)
  # Strip trailing digit suffix
  m = re.match(r'^(.*\S)\s+\d+$', val)
  base = m.group(1) if m else val
  if base[:1].isupper():
    return base       # proper noun — no article
  # Strip leading "the " or "The " (entity names sometimes include the article)
  if base.lower().startswith("the "):
    base = base[4:]
  # Look up adjectives for this entity (e.g. "red" for "house 3")
  adjs = entity_props.get(val, []) if entity_props else []
  adj_prefix = " ".join(adjs) + " " if adjs else ""
  return "the " + adj_prefix + base


def _where_conf_prefix(conf):
  """Return a confidence qualifier prefix for a where answer, or None if below threshold.

  conf >= 0.95: no prefix (plain answer)
  conf >= 0.85: "Likely"
  conf >= 0.60: "Probably"
  conf <  0.60: return empty string to signal Unknown
  """
  if conf >= 0.95:
    return ""
  if conf >= 0.85:
    return "Likely"
  if conf >= 0.60:
    return "Probably"
  return None   # below threshold -> Unknown


def _build_entity_props(logic):
  """Build a dict mapping entity constant -> list of its property adjectives.

  Scans assertional @logic clauses for ["has property", adj, entity, ...] atoms.
  Returns {entity: [adj, ...]} where adj strings are in order of occurrence.
  """
  props = {}
  if not logic:
    return props
  for obj in logic:
    if not isinstance(obj, dict) or "@logic" not in obj:
      continue
    if obj.get("@sourcetype") == "question":
      continue
    clause = obj["@logic"]
    # Accept single atom or list of atoms (disjunctive clause)
    atoms = clause if isinstance(clause[0], list) else [clause]
    for atom in atoms:
      if (isinstance(atom, list) and len(atom) >= 3
          and atom[0] == "has property"
          and isinstance(atom[1], str) and isinstance(atom[2], str)):
        adj    = atom[1]
        entity = atom[2]
        if not entity.startswith("$"):
          props.setdefault(entity, [])
          if adj not in props[entity]:
            props[entity].append(adj)
  return props


def _format_where_answers(answers, logic=None):
  """Format where-query answers as location strings.

  Each answer has val = [["$ans", prep, entity], ...].
  Returns e.g. "In the house." or "In the house and in the city."
  Applies confidence prefix ("Probably", "Likely") when confidence < 0.95.
  Returns "Unknown." when all answers are below the 0.60 confidence threshold.
  If logic is provided, adjectives for location entities are reconstructed.
  """
  entity_props = _build_entity_props(logic)

  parts = []
  seen  = set()
  best_conf = 0.0
  for ans in answers:
    val  = ans.get("answer")
    conf = ans.get("confidence", 1.0)
    if not isinstance(val, list) or not val:
      continue
    atom = val[0]   # first (should be only) $ans atom
    if not isinstance(atom, list) or len(atom) < 3:
      continue
    prep       = atom[1]
    entity_raw = atom[2]
    if not isinstance(prep, str) or not isinstance(entity_raw, str):
      continue
    key = (prep, entity_raw)
    if key in seen:
      continue
    seen.add(key)
    if conf > best_conf:
      best_conf = conf
    parts.append(prep + " " + _location_entity_name(entity_raw, entity_props))

  if not parts:
    return "Unknown."

  prefix = _where_conf_prefix(best_conf)
  if prefix is None:
    return "Unknown."

  if prefix:
    parts[0] = prefix + " " + parts[0]
  return _join_and_finish(parts)


def _format_bool_answer(val, conf, has_conflict=False):
  """Format a True/False answer with verbal confidence qualifier.

  has_conflict: True when the prover returned both a positive and a negative
  proof; confidence then represents the net surplus of positive over negative
  evidence rather than pure positive-chain strength.

  Threshold scheme:
    True,  conf >= 0.95              -> "True"
    True,  conf >= 0.70              -> "Probably true"
    True,  conf >= 0.40, no conflict -> "Likely true"
    True,  conf >= 0.10              -> "Possibly true (confidence X)"
    True,  conf <  0.10              -> "Unknown."
    False, conf >= 0.95              -> "False"
    False, conf >= 0.85              -> "Likely false (confidence X)"
    False, conf >= 0.60              -> "Probably false (confidence X)"
    False, conf <  0.60              -> "Probably false"

  The asymmetry is intentional: True uses finer graduation because positive
  proofs carry varying chain strength, and very low confidence (<0.10) is
  indistinguishable from noise (→ "Unknown.").  False is proved by
  contradiction, so even weak negative evidence is informative — low-confidence
  False still reports "Probably false" rather than falling back to "Unknown.".
  """
  if conf >= 0.95:
    return "True" if val else "False"
  if val is True:
    if conf >= 0.70:
      return "Probably true"
    if conf >= 0.40 and not has_conflict:
      return "Likely true"
    if conf >= 0.10:
      return "Possibly true (confidence " + _fmt_conf(conf) + ")"
    return "Unknown."
  else:  # val is False
    if conf >= 0.85:
      return "Likely false (confidence " + _fmt_conf(conf) + ")"
    if conf >= 0.60:
      return "Probably false (confidence " + _fmt_conf(conf) + ")"
    return "Probably false"


def _format_answers(answers, askvars=None):
  """Collect answer values from all (non-duplicate) answer entries and join.

  askvars: if set, only the first askvars $ans atoms in each answer are
  shown in the output (the rest are auxiliary existential variables).
  The detailed proof explanation is unaffected.
  """
  parts     = []
  seen_keys = set()
  for ans in answers:
    val  = ans.get("answer")
    conf = ans.get("confidence", 1)

    key = ans_display_key(val)
    if key in seen_keys:
      continue
    seen_keys.add(key)

    if val is True or val is False:
      has_conflict = ("negative proof" in ans) and ("positive proof" in ans)
      s = _format_bool_answer(val, conf, has_conflict=has_conflict)
    elif isinstance(val, list) and val:
      # Each element is an $ans atom like ["$ans", "John 1"].
      # When len(val) > askvars, the prover produced a disjunctive residual:
      # multiple possible values for the same ask variable(s).  Group atoms
      # into chunks of size askvars; each chunk is one alternative.
      # Example: askvars=1, val=[[$ans,Mike],[$ans,Mary]] → "Mike or Mary"
      if askvars and len(val) > askvars:
        groups = [val[i:i+askvars] for i in range(0, len(val), askvars)]
        alt_strs = []
        for grp in groups:
          names = [ans_atom_name(a) for a in grp]
          alt_strs.append(" and ".join(names) if len(names) > 1 else names[0])
        s = " or ".join(alt_strs)
      else:
        display = val[:askvars] if askvars is not None else val
        names = [ans_atom_name(a) for a in display]
        s = names[0] if len(names) == 1 else "(" + " and ".join(names) + ")"
      if conf < 0.99:
        s += " (confidence " + _fmt_conf(conf) + ")"
    else:
      s = str(val)
      if conf < 0.99:
        s += " (confidence " + _fmt_conf(conf) + ")"
    parts.append(s)

  if not parts:
    return "Could not find an answer."
  return _join_and_finish(parts)


def _fmt_conf(conf):
  """Format a confidence float as a two-decimal string."""
  return str(round(conf, 2))


# ======== answer selection and filtering ========

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


def _extract_question_pop_keys(logic):
  """Extract a list of (pred, prop_or_class) tuples identifying predicates queried.

  Used by _is_tautological_population_answer to detect circular population proofs.
  Returns a list of tuples (may be empty).

  For direct questions like ["isa", CLASS, ?:var]:
    -> [("isa", CLASS)]

  For $defq-wrapped questions like ["$defq0", ?:X]:
    Scans the biconditional @logic clauses for negative conditions and extracts
    the population-relevant predicates from them.  E.g. the clause
      [["-isa","car","?:X"], ["-has degree property","nice","?:X",...], ["$defq0","?:X"]]
    yields [("isa", "car"), ("has degree property", "nice")].
  """
  _POP_PREDS = {"isa", "has degree property", "has property"}
  if not logic or not isinstance(logic, list):
    return []
  keys = []
  for obj in logic:
    if not isinstance(obj, dict) or "@question" not in obj:
      continue
    q = obj["@question"]
    if not isinstance(q, list) or len(q) < 2:
      continue
    pred = q[0]
    if pred in _POP_PREDS:
      keys.append((pred, str(q[1])))
      return keys
    # $defq question: scan the biconditional clauses for query predicates.
    if pred.startswith("$defq"):
      for obj2 in logic:
        if not isinstance(obj2, dict) or "@logic" not in obj2:
          continue
        clause = obj2["@logic"]
        if not isinstance(clause, list) or not clause:
          continue
        # Look for multi-atom clause containing ["$defqN", ...] as positive literal.
        if not isinstance(clause[0], list):
          continue  # single atom, not the biconditional clause
        has_defq = any(isinstance(a, list) and a and isinstance(a[0], str)
                       and a[0].startswith("$defq") for a in clause)
        if not has_defq:
          continue
        # Extract (pred, arg1) from negative literals in this clause.
        # Skip "isa" — isa population facts are legitimate type witnesses,
        # not circular.  Only property predicates indicate circularity.
        for atom in clause:
          if (isinstance(atom, list) and atom and isinstance(atom[0], str)
              and atom[0].startswith("-") and len(atom) >= 3):
            base_pred = atom[0][1:]
            if base_pred in _POP_PREDS and base_pred != "isa":
              key = (base_pred, str(atom[1]))
              if key not in keys:
                keys.append(key)
      return keys
  return keys


def _is_tautological_population_answer(ans, question_pop_keys):
  """Return True if ans is a $some_* constant proved directly via the
  population clause that asserts the very property/class being queried.

  Two checks:
    1. question_pop_keys non-empty: $some_* constant proved via a single-atom
       population clause [PRED, PROP, answer_const, ...] where PRED/PROP
       match any of the question's population keys.
    2. $some_not_* constant proved via its own negative population clause
       ["-PRED", ..., answer_const, ...] — always circular regardless of
       what the question predicate is.
  """
  val = ans.get("answer")
  if not isinstance(val, list) or not val:
    return False
  if not isinstance(val[0], list) or len(val[0]) < 2:
    return False
  answer_const = val[0][1]
  if not isinstance(answer_const, str) or not answer_const.startswith("$some_"):
    return False

  proof = ans.get("positive proof", [])
  for step in proof:
    if len(step) < 3:
      continue
    justification = step[1]
    clause = step[2]
    if not isinstance(justification, list) or not justification:
      continue
    if justification[0] != "in":
      continue
    # Unwrap single-element list wrapper if present: [[atom]] -> [atom]
    inner_clause = clause
    if (isinstance(clause, list) and len(clause) == 1
        and isinstance(clause[0], list)):
      inner_clause = clause[0]
    if not (isinstance(inner_clause, list) and len(inner_clause) >= 3):
      continue
    # Check 1: matches any question predicate/property.
    if question_pop_keys:
      for qkey in question_pop_keys:
        if (inner_clause[0] == qkey[0]
            and str(inner_clause[1]) == qkey[1]
            and inner_clause[2] == answer_const):
          return True
    # Check 2: $some_not_* proved from its own negative population clause.
    if (answer_const.startswith("$some_not_")
        and isinstance(inner_clause[0], str)
        and inner_clause[0].startswith("-")
        and inner_clause[2] == answer_const):
      return True
  return False


def _filter_tautological_population_answers(answers, logic):
  """Remove tautological population answers.

  A tautological answer is a $some_* constant proved solely via the
  population clause that asserts the very property/class being queried —
  i.e. the proof is circular: 'some big elephant is big because some big
  elephant is big (by population)'. Such answers are always filtered out,
  even when no non-tautological alternatives exist (producing "Unknown").
  """
  question_pop_keys = _extract_question_pop_keys(logic)
  tautological = [a for a in answers
                  if _is_tautological_population_answer(a, question_pop_keys)]
  if not tautological:
    return answers
  return [a for a in answers if a not in tautological]


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
