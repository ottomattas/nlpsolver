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

from lc_clausify import is_skolem_const, is_skolem_fn, skolem_type_from_name
from proof_render import (
  compute_ambiguity, compute_skolem_types, entity_name, ans_atom_name,
  set_entity_map, get_entity_display,
  get_skolem_type, get_skolem_fn_type,
)
from proof_explain import format_explanation, build_sentence_map, ans_display_key
from entity_map import build_entity_map


def _strip_una_prefix(node):
  """Recursively strip the leading `#:` UNA marker from every string."""
  if isinstance(node, str):
    return node[2:] if node.startswith("#:") else node
  if isinstance(node, list):
    return [_strip_una_prefix(x) for x in node]
  if isinstance(node, dict):
    return {k: _strip_una_prefix(v) for k, v in node.items()}
  return node


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

  # Strip the UNA `#:` prefix from every string in the prover output before
  # the rest of the post-processing runs. The prefix is only meaningful to
  # gk's UNA mechanism inside the prover; all downstream entity-id parsing
  # (Skolem detection, type extraction, ambiguity scanning) expects the
  # bare ids it emitted in the original logic.
  data = _strip_una_prefix(data)

  # Top-level error / no answer
  if "error" in data:
    return "Error: " + str(data["error"])
  if data.get("result") != "answer found":
    return "Unknown."

  answers = data.get("answers", [])
  if not answers:
    return "Unknown."

  # Simplify $get_world($ctxt(_, W, _, _)) → W in $ans atoms before any
  # filtering. The $get_world destructor axiom (axioms_std.js §13.A) is
  # bidirectional: paramodulation can wrap any term as $get_world of a
  # synthesized $ctxt, producing redundant alternative shapes of the same
  # answer. Reducing eagerly collapses those shapes so dedup and tier
  # filtering treat them as one.
  for ans in answers:
    val = ans.get("answer")
    if isinstance(val, list):
      ans["answer"] = [_simplify_get_world(atom) for atom in val]

  # Sort: highest confidence first, shorter proofs preferred
  answers = sorted(answers, key=_answer_goodness, reverse=True)

  # For wh-questions: keep only answers in the best object-type tier
  # (concrete > Skolem > population), preserving the goodness order within tier.
  # For "what" questions: prefer population (class) answers over concrete instances.
  # Class-name leaks (the part-inheritance bg axiom `has_part(X,Y,Z) &
  # isa(X,U) -> has_part(U,Y,Z)` can unify the answer variable with a class
  # name string via a population fact) are demoted to the population tier:
  # concrete entities beat class labels, but class labels survive as a
  # fallback when no concrete entity exists (cases 236, 241, 242).  Class
  # labels that are tautological wrt the queried predicate are dropped by
  # _filter_tautological_population_answers.
  is_what = _is_what_query(logic)
  is_who  = _is_who_query(logic)
  class_names = _extract_class_names(logic)
  if is_what:
    answers = _filter_by_best_tier(answers, prefer_population=True,
                                   class_names=class_names)
  else:
    answers = _filter_by_best_tier(answers, class_names=class_names)
  answers = _filter_tautological_population_answers(answers, logic,
                                                   class_names=class_names)
  answers = _deduplicate_proofs(answers)
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

  # Populate Skolem type tables from logic + proofs so that answer formatting
  # can resolve Skolem constants/functions to human-readable names.
  all_proofs = []
  for ans in answers:
    for key in ("positive proof", "negative proof"):
      p = ans.get(key)
      if isinstance(p, list):
        all_proofs.extend(p)
  compute_skolem_types(all_proofs, logic=logic)

  # For "what" queries: resolve Skolem function answers to their class.
  # E.g., $ans(["sk3","Emily 1"]) where sk3 is typed as "wolf" → $ans("$some_wolf").
  if is_what:
    _resolve_what_skolem_answers(answers)

  # Format the answer value(s)
  who_surviving = None
  if _is_prep_query(logic):
    answer_str = _format_prep_answers(answers, logic=logic)
  elif _is_who_query(logic):
    answer_str, who_surviving = _format_who_answers(answers, logic=logic)
  else:
    answer_str = _format_answers(answers, askvars=askvars)

  # For what-queries, strip property words named in the question from the
  # rendered answer. "What was deep? / the deep dent" → "the dent".
  if is_what:
    qprops = _extract_question_property_words(logic)
    if qprops:
      answer_str = _strip_question_props(answer_str, qprops)

  # Optionally append a step-by-step proof explanation
  explain     = options.get("prover_explain_flag", False)
  show_logic  = options.get("show_logic_flag", False)
  if explain:
    # For who/what queries, only explain answers that survived filtering
    explain_answers = answers
    if who_surviving is not None:
      def _atom_in_surviving(atom):
        if not (isinstance(atom, list) and len(atom) >= 2 and atom[0] == "$ans"):
          return False
        v = atom[1]
        if isinstance(v, list):
          v = entity_name(v)   # match the rendering done in _format_who_answers
        return isinstance(v, str) and v in who_surviving
      explain_answers = [a for a in answers
                         if isinstance(a.get("answer"), list)
                         and any(_atom_in_surviving(atom) for atom in a["answer"])]
    explanation = format_explanation(explain_answers, sentence_map, show_logic=show_logic, logic=logic)
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


def _is_prep_query(logic):
  """Return True if logic contains a @where_query or @when_query marker."""
  if not logic or not isinstance(logic, list):
    return False
  for obj in logic:
    if isinstance(obj, dict) and (obj.get("@where_query") or obj.get("@when_query")):
      return True
  return False


def _is_who_query(logic):
  """Return True if logic contains a @who_query marker."""
  if not logic or not isinstance(logic, list):
    return False
  for obj in logic:
    if isinstance(obj, dict) and obj.get("@who_query"):
      return True
  return False


def _get_who_entity(logic):
  """Return the @who_entity value from logic, or None."""
  if not logic or not isinstance(logic, list):
    return None
  for obj in logic:
    if isinstance(obj, dict) and "@who_entity" in obj:
      return obj["@who_entity"]
  return None


def _get_who_kind(logic):
  """Return the @who_kind value from logic ("who" or "what"), default "who"."""
  if not logic or not isinstance(logic, list):
    return "who"
  for obj in logic:
    if isinstance(obj, dict) and "@who_kind" in obj:
      return obj["@who_kind"]
  return "who"


def _is_what_query(logic):
  """Return True if logic contains a @what_query marker."""
  if not logic or not isinstance(logic, list):
    return False
  for obj in logic:
    if isinstance(obj, dict) and obj.get("@what_query"):
      return True
  return False


def _extract_question_property_words(logic):
  """Return the set of property words that the question's predicate body
  asks about — has_property / has_degree_property atoms with a literal
  string at the property slot. Used to strip those words from what-answer
  rendering ("What was deep?" / dent 2 → "the dent", not "the deep dent").
  """
  if not logic or not isinstance(logic, list):
    return frozenset()
  out = set()

  def _walk(node):
    if not isinstance(node, list) or not node:
      return
    head = node[0]
    if isinstance(head, str):
      bare = head[1:] if head.startswith("-") else head
      if bare == "has property" and len(node) >= 3 and isinstance(node[1], str):
        if not node[1].startswith("?:"):
          out.add(node[1])
      elif bare == "has degree property" and len(node) >= 3 and isinstance(node[1], str):
        if not node[1].startswith("?:"):
          out.add(node[1])
    for child in node:
      _walk(child)

  for clause in logic:
    if not isinstance(clause, dict):
      continue
    if clause.get("@sourcetype") == "question" or clause.get("@what_query"):
      _walk(clause.get("@logic"))
      _walk(clause.get("@question"))
  return frozenset(out)


def _strip_question_props(answer_str, prop_words):
  """Remove each prop word (whole word, case-insensitive) from answer_str
  and tidy up resulting whitespace and articles."""
  if not answer_str or not prop_words:
    return answer_str
  s = answer_str
  for w in prop_words:
    if not w:
      continue
    s = re.sub(r'\b' + re.escape(w) + r'\b', '', s, flags=re.IGNORECASE)
  # Collapse runs of whitespace and tidy stray space before punctuation.
  s = re.sub(r'\s+', ' ', s).strip()
  s = re.sub(r'\s+([.,;:])', r'\1', s)
  return s


def _resolve_what_skolem_answers(answers):
  """For 'what' queries, replace Skolem-typed answer values with population
  constants of the corresponding class.

  Two patterns handled:
    1. Skolem function terms:  $ans(["sk3","Emily 1"]) where sk3 is typed
       "wolf" → $ans("$some_wolf").  Uses get_skolem_fn_type.
    2. Skolem constants:       $ans("sk1_tobacco") where sk1_tobacco is typed
       "tobacco" (from isa(tobacco, sk1_tobacco) facts) → $ans("$some_tobacco").
       Uses get_skolem_type.

  The population constant renders as "a tobacco" / "a wolf" via entity_name,
  matching user expectations for "what is X?" queries that should return a
  class rather than a raw Skolem name.
  """
  for ans in answers:
    val = ans.get("answer")
    if not isinstance(val, list):
      continue
    new_val = []
    changed = False
    for atom in val:
      if not (isinstance(atom, list) and len(atom) >= 2 and atom[0] == "$ans"):
        new_val.append(atom)
        continue
      arg = atom[1]
      # Case 1: Skolem function term like ["sk3", "Emily 1"]
      if isinstance(arg, list) and arg and isinstance(arg[0], str):
        fn_type = get_skolem_fn_type(arg[0])
        if fn_type:
          pop_name = "$some_" + fn_type.replace(" ", "_")
          new_val.append(["$ans", pop_name] + atom[2:])
          changed = True
          continue
      # Case 2: Skolem constant like "sk1_tobacco"
      elif isinstance(arg, str) and is_skolem_const(arg):
        typ = get_skolem_type(arg)
        if typ:
          pop_name = "$some_" + typ.replace(" ", "_")
          new_val.append(["$ans", pop_name] + atom[2:])
          changed = True
          continue
      new_val.append(atom)
    if changed:
      ans["answer"] = new_val


def _classify_who_answers(logic, who_entity):
  """Scan assertion clauses to build sets of known types and properties for who_entity.

  Only full-confidence isa facts (clauses without @confidence or
  @confidence == 1.0) qualify as type descriptions — partial-confidence
  isa entries (from probabilistic clauses) are excluded, since they
  would over-broaden the answer (case 236: isa(person, John) at 0.77
  is an artifact of the "John is probably not bad" formula structure,
  not a genuine uncertain type claim).  Property detection has no
  confidence filter: a partial-confidence property is still a valid
  qualitative descriptor.

  Returns (isa_types, property_names) where both are sets of strings.
  """
  isa_types = set()
  prop_names = set()
  if not logic or not isinstance(logic, list):
    return isa_types, prop_names
  for obj in logic:
    if not isinstance(obj, dict) or "@logic" not in obj:
      continue
    nm = obj.get("@name", "")
    # Skip question-derived and population clauses
    if obj.get("@sourcetype") == "question":
      continue
    clause = obj["@logic"]
    if not isinstance(clause, list) or not clause:
      continue
    # Single-atom clauses only (not rules)
    if isinstance(clause[0], list):
      continue
    pred = clause[0]
    conf = obj.get("@confidence")
    full_conf = (conf is None or conf >= 1.0)
    if not full_conf:
      continue          # skip partial-confidence facts in both lists
    if pred == "isa" and len(clause) >= 3 and clause[2] == who_entity:
      isa_types.add(clause[1])
    if pred in ("has degree property", "has property") and len(clause) >= 3 and clause[2] == who_entity:
      prop_names.add(clause[1])
  return isa_types, prop_names


def _classify_use_vals(use_vals, isa_types, prop_names, who_entity,
                       non_self, self_only, seen):
  """Bucket each answer value into (types, properties, equalities), then
  inject prop_names (always) and isa_types (only when non_self is empty).

  Mutates `seen` to dedup injected names against answer values.
  Returns (types, properties, equalities, surviving_values).
  """
  surviving_values = set(v for v, _, _ in use_vals)
  equalities, types, properties = [], [], []

  for v, _, _ in use_vals:
    if v in isa_types:
      types.append(v)
    elif v in prop_names:
      properties.append(v)
    elif is_skolem_const(v):
      # Skolem with a known type — promote ("sk1_tobacco" → "tobacco")
      # so the answer renders "a tobacco" not the raw Skolem name.
      typ = get_skolem_type(v)
      if typ:
        types.append(typ)
      else:
        equalities.append(v)
    else:
      base = v.split()[0] if " " in v else v
      is_lower_noun = (base and base[0].islower()
                       and not any(c.isdigit() for c in v))
      if who_entity and isa_types and is_lower_noun:
        # Authoritative isa_types is full-confidence; lowercase value
        # NOT in that set is a partial-conf type leak — drop it.
        surviving_values.discard(v)
        continue
      if is_lower_noun:
        types.append(v)
      else:
        equalities.append(v)

  for p in prop_names:
    if p not in seen:
      seen.add(p)
      properties.append(p)
      surviving_values.add(p)

  # Case 236: prover only had self-ref answers but fact base has known
  # types — inject those and drop the tautological self-reference.
  if not non_self and isa_types:
    for v, _, _ in self_only:
      surviving_values.discard(v)
    equalities = []
    for t in sorted(isa_types):
      if t not in seen:
        seen.add(t)
        types.append(t)
        surviving_values.add(t)

  return types, properties, equalities, surviving_values


def _format_who_answers(answers, logic=None):
  """Format who/what-query answers as type, property, or identity descriptions.

  Each answer has val = [["$ans", TYPE_OR_ENTITY_OR_PROP], ...].
  Filters out $-prefixed constants (population/metadata).
  Self-referential answers (entity = queried entity) are kept only if no
  other answers exist.
  Ranking:
    Who:  equality > isa types > properties
    What: isa types > properties > equality
  Returns (answer_string, surviving_values_set).
  """
  who_entity = _get_who_entity(logic)
  who_kind = _get_who_kind(logic)
  isa_types, prop_names = _classify_who_answers(logic, who_entity)
  class_names = _extract_class_names(logic)

  # Collect all valid answer values with their per-answer confidences.
  # Lower bound 0.05 (was 0.60): keep partial-confidence answers so that
  # cases 241/242 emit "Probably John." / "Maybe John." with a qualitative
  # prefix instead of "Unknown."  Very low confidence (< 0.05) is still
  # dropped — such answers are dominated by noise from the prover chain.
  # Per-atom tier filtering: a single proof's val may carry multiple $ans
  # atoms of different tiers (e.g. [$ans("John 1"), $ans("wing")] from a
  # part-inheritance chain).  Within each val we keep only atoms at the
  # best tier present, so concrete entities suppress class-label / Skolem
  # leaks within the same proof.
  all_vals = []  # (value, is_self_ref, confidence)
  seen = set()

  for ans in answers:
    val = ans.get("answer")
    if not isinstance(val, list):
      continue
    conf = ans.get("confidence", 1)
    if conf < 0.05:
      continue
    best_atom_tier = _ans_object_tier(val, class_names)
    for atom in val:
      if not isinstance(atom, list) or len(atom) < 2 or atom[0] != "$ans":
        continue
      atom_tier = _ans_object_tier([atom], class_names)
      if atom_tier > best_atom_tier:
        continue
      v = atom[1]
      if isinstance(v, list):
        # Complex term (e.g., ["$theof1","sister","Mary 1",...]) — render
        # via entity_name → render_term_english to get an English string
        # like "Mary's sister".  Without this, $theof1 answers fall through
        # and the user sees "Unknown."
        rendered = entity_name(v)
        if not isinstance(rendered, str) or not rendered:
          continue
        v = rendered
      elif not isinstance(v, str):
        continue
      # Filter $-prefixed constants (population, metadata)
      if v.startswith("$"):
        continue
      if v in seen:
        continue
      seen.add(v)
      is_self = (who_entity and v == who_entity)
      all_vals.append((v, is_self, conf))

  # Separate self-referential from non-self
  non_self = [(v, s, c) for v, s, c in all_vals if not s]
  self_only = [(v, s, c) for v, s, c in all_vals if s]

  # Decide which answer set to render.  Three mutually-exclusive cases:
  #   - non_self non-empty: prover found real answers; render those.
  #   - non_self empty + prop_names exist: render only the injected
  #     properties below; self_only would be tautological.
  #   - both empty: keep self_only as a fallback (the isa_types injection
  #     below may replace it for case 236-style queries).
  if non_self:
    use_vals = non_self
  elif prop_names:
    use_vals = []
  else:
    use_vals = self_only

  types, properties, equalities, surviving_values = _classify_use_vals(
    use_vals, isa_types, prop_names, who_entity, non_self, self_only, seen,
  )

  if not types and not properties and not equalities:
    return "Unknown.", set()

  # Build formatted parts.
  # When types and properties coexist, compose noun phrases: "a bad red car".
  # When only properties, list bare: "nice" or "nice and big".
  # Equalities rendered separately.
  parts = []

  # Compose type noun phrases with properties as adjectives
  if types:
    primary_type = types[0]
    adj_str = " ".join(properties) if properties else ""
    noun = adj_str + " " + primary_type if adj_str else primary_type
    if noun.startswith(("the ", "a ", "an ")):
      parts.append(noun)
    else:
      article = "an" if noun[0] in "aeiou" else "a"
      parts.append(article + " " + noun)
    # Additional types without adjectives
    for t in types[1:]:
      if t.startswith(("the ", "a ", "an ")):
        parts.append(t)
      else:
        article = "an" if t[0] in "aeiou" else "a"
        parts.append(article + " " + t)
  elif properties:
    # No types — list properties bare
    parts.extend(properties)

  # Equality answers
  for v in equalities:
    parts.append(entity_name(v, with_url=False))

  # Rank: for "what", types+props already first; for "who", equalities first
  if who_kind == "who" and equalities and (types or properties):
    # Move equality parts to front
    eq_parts = parts[len(types) + (1 if types else len(properties)):]
    type_parts = parts[:len(types) + (1 if types else len(properties))]
    parts = eq_parts + type_parts

  result = parts[0]
  if len(parts) > 1:
    result = ", ".join(parts[:-1]) + " and " + parts[-1]

  # Qualitative confidence prefix based on the MINIMUM confidence across
  # the surviving answer set (the weakest link in the claim):
  #   > 0.8  -> no prefix
  #   > 0.4  -> "Probably "
  #   else   -> "Maybe "
  # Thresholds mirror the Stage-1 confidence table (0.8 = probably/likely,
  # 0.6 = maybe/possibly).  Applied to who-queries only; "what"-queries
  # have their own rendering pathway (set via who_kind).
  prefix = ""
  confs_in_use = [c for v, _, c in use_vals if v in surviving_values]
  if confs_in_use:
    min_conf = min(confs_in_use)
    if min_conf <= 0.4:
      prefix = "Maybe "
    elif min_conf <= 0.8:
      prefix = "Probably "

  if prefix:
    # Keep the first word's original case — "John" stays capitalized,
    # "a tobacco" stays lowercase after the capitalized prefix.
    result = prefix + result + "."
  else:
    result = result[0].upper() + result[1:] + "."

  return result, surviving_values


def _resolve_skolem_entity(val):
  """Resolve a Skolem constant or function to a human-readable name.

  For string Skolems like "sk0": looks up skolem_types → "the house".
  For list Skolems like ["sk0","box 2"]: looks up skolem_fn_types → "the house".
  Returns the resolved name string, or None if not a Skolem or no type found.
  """
  if is_skolem_const(val):
    # Fast path: extract type from name (sk0_house → house)
    typ = skolem_type_from_name(val)
    # Fallback: clause-list scan
    if not typ:
      typ = get_skolem_type(val)
    if typ:
      return "the " + typ if typ[0].islower() else typ
  if is_skolem_fn(val):
    typ = get_skolem_fn_type(val[0])
    if typ:
      return "the " + typ if typ[0].islower() else typ
  return None


def _location_entity_name(val, entity_props=None):
  """Format a location entity constant for display in a 'where' answer.

  Checks the entity_map first (user's original phrasing, with qualifier and
  article already incorporated).  Falls back to Skolem resolution, URL-name
  extraction and common-noun article logic.

  "house 2"             -> "the house"
  "house 3" (red)       -> "the red house"  (entity_map or entity_props lookup)
  "London 1"            -> "London"          (proper noun: no article)
  "https://.../Estonia" -> "Estonia"
  "sk0"                 -> "the house"       (Skolem type lookup)
  """
  if not isinstance(val, str):
    # List Skolem function like ["sk0", "box 2"]
    resolved = _resolve_skolem_entity(val)
    if resolved:
      return resolved
    return str(val)
  # Entity map overrides everything — already has correct article and qualifier
  em = get_entity_display(val)
  if em is not None:
    return em
  # String Skolem constants like "sk0"
  resolved = _resolve_skolem_entity(val)
  if resolved:
    return resolved
  # URL constants: use entity_name which extracts the last path segment
  if val.startswith("http://") or val.startswith("https://"):
    return entity_name(val, with_url=False)
  # Strip trailing digit suffix
  m = re.match(r'^(.*\S)\s+\d+$', val)
  base = m.group(1) if m else val
  if base[:1].isupper():
    return base       # proper noun — no article
  # Numeric / temporal values: no article (years, times, counts)
  if base[:1].isdigit():
    return base
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


def _format_prep_answers(answers, logic=None):
  """Format where/when-query answers as preposition + entity strings.

  Each answer has val = [["$ans", prep, entity], ...].
  Returns e.g. "In the house.", "On Monday.", "In the house and in the city."
  Applies confidence prefix ("Probably", "Likely") when confidence < 0.95.
  Returns "Unknown." when all answers are below the 0.60 confidence threshold.
  If logic is provided, adjectives for location entities are reconstructed.
  """
  entity_props = _build_entity_props(logic)

  # Collect all (prep, entity_key) pairs first, then filter.
  _SPECIFIC_PREPS = frozenset({"on", "in", "above", "under", "near"})
  entries = []   # list of (prep, entity_key, display_str, conf)
  seen    = set()
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
    if not isinstance(prep, str):
      continue
    if not isinstance(entity_raw, (str, list)):
      continue
    # Drop answers whose entity slot is an unresolved variable (the prover
    # returned a free `?:Xn` rather than a concrete location); they would
    # render as garbage like "in ?:X3".
    if isinstance(entity_raw, str) and entity_raw.startswith("?:"):
      continue
    # If the preposition slot is an unresolved variable, drop the prep
    # prefix and keep just the entity. Common when the prover unifies via
    # persistence with a variable-prep axiom and never narrows the prep.
    prep_for_display = "" if prep.startswith("?:") else prep
    entity_key = str(entity_raw)
    key = (prep, entity_key)
    if key in seen:
      continue
    seen.add(key)
    entity_display = _location_entity_name(entity_raw, entity_props)
    display = (prep_for_display + " " + entity_display) if prep_for_display else entity_display
    entries.append((prep, entity_key, display, conf))

  # Drop "at" answers when a more specific preposition ("on", "in", etc.)
  # exists for the same entity.  "at" is derived from on→at / in→at axioms;
  # showing both "on X" and "at X" is redundant.
  specific_entities = {ek for p, ek, _, _ in entries if p in _SPECIFIC_PREPS}
  parts = []
  best_conf = 0.0
  for prep, ek, display, conf in entries:
    if prep == "at" and ek in specific_entities:
      continue
    parts.append(display)
    if conf > best_conf:
      best_conf = conf

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
    False, conf >= 0.85              -> "Likely false"
    False, conf >= 0.60              -> "Probably false"
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
      return "Likely false"
    if conf >= 0.60:
      return "Probably false"
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
    else:
      s = str(val)
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


def _simplify_get_world(atom):
  """Rewrite ["$ans", ["$get_world", ["$ctxt", _, W, _, _]]] -> ["$ans", W].

  Applies the $get_world destructor axiom (axioms_std.js §13.A) eagerly so
  paramodulation-produced wrapping doesn't survive into tier filtering or
  rendering. Atoms whose argument is not a $get_world wrapper, or whose
  $get_world wraps something other than a $ctxt term of length >= 3, are
  returned unchanged.
  """
  if not isinstance(atom, list) or len(atom) < 2 or atom[0] != "$ans":
    return atom
  arg = atom[1]
  if (isinstance(arg, list) and len(arg) >= 2 and arg[0] == "$get_world"):
    ctxt = arg[1]
    if (isinstance(ctxt, list) and len(ctxt) >= 3 and ctxt[0] == "$ctxt"):
      return [atom[0], ctxt[2]]
  return atom


def _ans_object_tier(val, class_names=frozenset()):
  """Return the object-type tier for an answer value.

  Tiers (lower is better / more preferred):
    0 -- CONCRETE: a specific named constant (e.g. "John 1", a URL)
    1 -- SKOLEM:   a Skolem constant ("sk0", "sk1", ...) or Skolem function
                   term (["sk0", X])
    2 -- POPULATION: a class-population constant ("$some_*") or a bare
                   class-name string (e.g. "elephant" appearing as the first
                   argument of some isa(...) literal — demoted so concrete
                   entities beat class labels but class labels survive as a
                   fallback when no concrete entity exists).

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
    if isinstance(s, list):
      if is_skolem_fn(s):
        tier = 1
      elif s and s[0] == "$get_world":
        # Residual $get_world wrapper (unsimplified — typically a free-var
        # world slot). Demote so a cleaner sibling answer wins.
        tier = 1
      elif s and s[0] == "$measure_of":
        # Abstract reference ("the price of X") — semantically equivalent
        # to its measurement value but not the value itself. Demote so a
        # concrete $list/$datetime/number sibling wins.
        tier = 1
      else:
        # $list (canonical measurement), $datetime, $theof1, and other
        # complex terms remain at the concrete tier. $list and $datetime
        # carry the actual value; $theof1 is the only meaningful binding
        # in cases like "Mary's sister" where no concrete entity exists.
        tier = 0
    elif isinstance(s, str):
      if s.startswith("$some_"):
        tier = 2
      elif is_skolem_const(s):
        tier = 1
      elif s in class_names:
        tier = 2
      else:
        tier = 0
    else:
      tier = 0
    if tier < best:
      best = tier
    if best == 0:
      break
  return best


def _has_real_concrete_atom(val, class_names=frozenset()):
  """True if val (a list of $ans atoms) contains an atom whose argument is
  a real concrete entity name — a string that is neither a Skolem constant,
  a population ($some_*) constant, nor a bare class label.  Used to
  distinguish "Tallinn" (a real concrete answer that should beat population)
  from ["sk3","Emily 1"] (a Skolem function) and from "elephant" (a class
  label demoted to the population tier)."""
  if not isinstance(val, list):
    return False
  for atom in val:
    if not isinstance(atom, list) or len(atom) < 2:
      continue
    s = atom[1]
    if (isinstance(s, str)
        and not s.startswith("$some_")
        and not is_skolem_const(s)
        and s not in class_names):
      return True
  return False


def _filter_by_best_tier(answers, prefer_population=False, class_names=frozenset()):
  """Return answers filtered to the best object-type tier.

  Boolean answers are never filtered out.  If all answers are boolean,
  or if no object answers exist, the list is returned unchanged.

  prefer_population: when True ("what" questions), prefer population tier (2)
  over Skolem-function answers — yielding class-level renderings like
  "A wolf" instead of opaque Skolem function output.  Real concrete entity
  names (proper names, URLs) are never overridden by population — Tallinn
  must beat $some_city_in_Estonia for "What is an Estonian city?" (cases
  189, 190).
  """
  tiers = [_ans_object_tier(a.get("answer"), class_names) for a in answers]
  obj_tiers = [t for a, t in zip(answers, tiers)
               if not isinstance(a.get("answer"), bool)]
  if not obj_tiers:
    return answers
  if prefer_population and 2 in obj_tiers and min(obj_tiers) < 2:
    has_real_concrete = any(
      not isinstance(a.get("answer"), bool)
      and _has_real_concrete_atom(a.get("answer"), class_names)
      for a in answers
    )
    if not has_real_concrete:
      return [a for a, t in zip(answers, tiers)
              if isinstance(a.get("answer"), bool) or t == 2]
  best = min(obj_tiers)
  if best == 2:
    # All object answers are population constants — keep them all as-is.
    return answers
  return [a for a, t in zip(answers, tiers)
          if isinstance(a.get("answer"), bool) or t == best]


def _extract_class_names(logic):
  """Return the set of strings that appear as the CLASS (first arg) of any
  isa(CLASS, ENTITY) atom in the clause list.  Used to detect class-name
  leaks in wh-answers (cases 241, 242)."""
  class_names = set()
  if not isinstance(logic, list):
    return class_names
  for obj in logic:
    if not isinstance(obj, dict):
      continue
    clause = obj.get("@logic")
    if not isinstance(clause, list) or not clause:
      continue
    # Clause may be a single atom [pred, ...] or a disjunction of atoms.
    atoms = [clause] if isinstance(clause[0], str) else clause
    for atom in atoms:
      if not isinstance(atom, list) or len(atom) < 3:
        continue
      pred = atom[0]
      if isinstance(pred, str) and pred.lstrip("-") == "isa":
        cls = atom[1]
        if isinstance(cls, str) and cls:
          class_names.add(cls)
  return class_names


def _filter_class_name_leaks(answers, logic):
  """Drop answers whose every $ans atom binds to a CLASS name string
  (a name appearing as the first arg of some isa(CLASS, *) in the logic).
  These answers arise when part-inheritance-style bg axioms unify the
  answer variable with a class name via a population fact; they are not
  legitimate entity answers.  Answers mixing entity + class values are
  preserved; pure class-leak answers are removed."""
  class_names = _extract_class_names(logic)
  if not class_names:
    return answers
  result = []
  for ans in answers:
    val = ans.get("answer")
    if not isinstance(val, list):
      result.append(ans)
      continue
    has_any_ans = False
    all_class = True
    for atom in val:
      if not isinstance(atom, list) or len(atom) < 2 or atom[0] != "$ans":
        continue
      has_any_ans = True
      v = atom[1]
      if not isinstance(v, str) or v not in class_names:
        all_class = False
        break
    if has_any_ans and all_class:
      continue                     # drop: every $ans value is a class name
    result.append(ans)
  return result


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


def _is_tautological_population_answer(ans, question_pop_keys, class_names=frozenset()):
  """Return True if ans is a $some_* constant proved directly via the
  population clause that asserts the very property/class being queried,
  or a bare class-label string that matches the queried class/property.

  Three checks:
    1. question_pop_keys non-empty: $some_* constant proved via a single-atom
       population clause [PRED, PROP, answer_const, ...] where PRED/PROP
       match any of the question's population keys.
    2. $some_not_* constant proved via its own negative population clause
       ["-PRED", ..., answer_const, ...] — always circular regardless of
       what the question predicate is.
    3. Bare class-label string answer (e.g. "elephant") that matches the
       second element of any question_pop_keys entry — e.g. "Who is an
       elephant? -> elephant" restates the queried class, so it's a
       tautological wh-leak via part-inheritance / population chains.
  """
  val = ans.get("answer")
  if not isinstance(val, list) or not val:
    return False
  if not isinstance(val[0], list) or len(val[0]) < 2:
    return False
  answer_const = val[0][1]
  # Class-label tautology: bare class string matching the queried class.
  if (isinstance(answer_const, str)
      and answer_const in class_names
      and any(answer_const == qkey[1] for qkey in question_pop_keys)):
    return True
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


def _filter_tautological_population_answers(answers, logic, class_names=frozenset()):
  """Remove tautological population / class-label answers.

  A tautological answer is one of:
    - A $some_* constant proved solely via the population clause that
      asserts the very property/class being queried ('some big elephant is
      big because some big elephant is big').
    - A bare class-label string that matches the class being queried
      ('Who is an elephant? -> elephant').
  Such answers are always filtered out, even when no non-tautological
  alternatives exist (producing "Unknown").
  """
  question_pop_keys = _extract_question_pop_keys(logic)
  tautological = [a for a in answers
                  if _is_tautological_population_answer(a, question_pop_keys,
                                                       class_names)]
  if not tautological:
    return answers
  return [a for a in answers if a not in tautological]


# ======== proof deduplication ========

def _proof_content_sources(ans):
  """Return frozenset of sent_* clause names used as axiom sources in the proof."""
  sources = set()
  for key in ("positive proof", "negative proof"):
    proof = ans.get(key)
    if not isinstance(proof, list):
      continue
    for step in proof:
      reason = step[1] if len(step) > 1 else []
      if (isinstance(reason, list) and len(reason) > 1
          and reason[0] == "in" and isinstance(reason[1], str)
          and reason[1].startswith("sent_")):
        sources.add(reason[1])
  return frozenset(sources)


def _answer_key(ans):
  """Hashable key for grouping answers by conclusion value."""
  val = ans.get("answer")
  return json.dumps(val, sort_keys=True)


def _proof_step_count(ans):
  """Total number of proof steps (positive + negative)."""
  return (len(ans.get("positive proof", []))
        + len(ans.get("negative proof", [])))


def _deduplicate_proofs(answers, threshold=0.15):
  """Remove redundant shadow proofs that differ only in navigation paths.

  Two proofs are in the same group if they have the same answer value
  and the same set of content (sent_*) sources.  Within each group,
  shorter proofs with fewer blockers dominate longer ones when confidence
  is within threshold.
  """
  groups = {}
  for ans in answers:
    key = (_answer_key(ans), _proof_content_sources(ans))
    groups.setdefault(key, []).append(ans)

  result = []
  for key, group in groups.items():
    if len(group) == 1:
      result.append(group[0])
      continue
    # Sort: fewer blockers, fewer steps, higher confidence
    group.sort(key=lambda a: (
      len(a.get("blockers", [])),
      _proof_step_count(a),
      -a.get("confidence", 0)
    ))
    # Keep first (best); discard any dominated by it
    kept = group[0]
    result.append(kept)
    kb = len(kept.get("blockers", []))
    kc = kept.get("confidence", 0)
    ks = _proof_step_count(kept)
    for other in group[1:]:
      ob = len(other.get("blockers", []))
      oc = other.get("confidence", 0)
      os = _proof_step_count(other)
      dominated = (kb <= ob and kc >= oc - threshold and ks <= os)
      if not dominated:
        result.append(other)
  return result


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
