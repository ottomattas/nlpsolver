# Logic-to-English rendering for proof explanations.
#
# Converts CNF proof clauses and atoms into readable English sentences.
# Also maintains module-level state (ambiguity sets, Skolem type tables)
# that is populated once per proof and read during rendering.
#
# Public API used by proof_explain.py and procproofs.py:
#   compute_ambiguity(obj)       -- scan logic for name ambiguities
#   compute_skolem_types(proof)  -- populate Skolem lookup tables
#   entity_name(val, with_url)   -- display name for a constant/variable
#   ans_atom_name(atom)          -- display name from a $ans atom
#   clause_to_str(clause)        -- clause -> if-then English string
#   format_clause_logic(clause)  -- clause -> compact JSON string
#   block_to_english(block_atom) -- $block atom -> English string
#   _atom_to_english(atom)        -- positive atom -> English
#   _atom_to_english_negated(atom)-- negated atom -> English
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

from linguistics import (
  indef_article  as _indef_article,
  conjugate_verb as _conjugate_verb,
  make_comparative as _make_comparative,
  to_gerund      as _to_gerund,
  looks_like_verb as _looks_like_verb,
  PREPOSITIONS   as _PREPOSITIONS,
)


# ======== $ans context-arg filtering ========

# Time tokens and world-state pattern that are pipeline residuals, not answer content.
_ANS_TIME_TOKENS = frozenset({"present", "past", "future"})
_ANS_WORLD_RE    = re.compile(r'^W\d+$')

def _ans_display_args(ans_args):
  """Strip context residuals from a $ans arg list, keeping only meaningful args.

  Filtered out: world-state tokens (W0, W1, ...), time tokens (present/past/future),
  and free-variable references (?:X, ?:X3, ...).
  Kept: entity constants, prepositions (for where-queries), numeric values, etc.
  """
  kept = []
  for a in ans_args:
    if not isinstance(a, str):
      kept.append(a)
      continue
    if a.startswith("?"):               # free variable: ?:X, ?:X3, ?:Y3, ...
      continue
    if _ANS_WORLD_RE.match(a):          # world state: W0, W1, ...
      continue
    if a in _ANS_TIME_TOKENS:           # time token
      continue
    kept.append(a)
  return kept


# ======== render context (all per-proof state) ========

class RenderContext:
  """Bundles all per-proof mutable state into one object.

  Avoids fragile module-level globals that can leak between proofs if a
  caller forgets to call one of the reset functions.
  """
  __slots__ = (
    "entity_map",          # entity id -> display name (from stage-1 JSON)
    "ambiguous_bases",     # set of proper-name bases with 2+ distinct numbers
    "ambiguous_url_names", # set of URL display names mapping to 2+ URLs
    "skolem_types",        # skN -> type string from isa(TYPE,skN)
    "skolem_fn_verbs",     # str(fn_term) -> verb string
    "skolem_fn_actors",    # str(fn_term) -> actor string
    "skolem_fn_targets",   # str(fn_term) -> target string
    "skolem_fn_types",     # sk_name -> object type from isa(TYPE,[sk_name,...])
    "skolem_introduced",   # set of skN names already shown with "some TYPE" prefix
    "skolem_display",      # skN -> short display name like "act1"
    "var_display",         # raw var "?:2006" -> short display name "E1"
  )
  def __init__(self):
    self.entity_map          = {}
    self.ambiguous_bases     = set()
    self.ambiguous_url_names = set()
    self.skolem_types        = {}
    self.skolem_fn_verbs     = {}
    self.skolem_fn_actors    = {}
    self.skolem_fn_targets   = {}
    self.skolem_fn_types     = {}
    self.skolem_introduced   = set()
    self.skolem_display      = {}
    self.var_display          = {}


# Module-level context instance, reset per proof.
_ctx = RenderContext()


# ======== public API (backward-compatible thin wrappers) ========

def set_entity_map(emap):
  """Install a new entity display-name map for the current proof."""
  _ctx.entity_map = emap if isinstance(emap, dict) else {}

def get_entity_display(val):
  """Return the entity_map display name for val, or None if not mapped."""
  return _ctx.entity_map.get(val)

def compute_ambiguity(obj):
  """Scan obj and populate ambiguous-name sets in the current context."""
  base_numbers = {}
  url_names    = {}
  _scan_constants(obj, base_numbers, url_names)
  _ctx.ambiguous_bases     = {b.lower() for b, nums in base_numbers.items() if len(nums) > 1}
  _ctx.ambiguous_url_names = {n for n, urls in url_names.items()    if len(urls)  > 1}

def compute_skolem_types(proof):
  """Scan proof steps and populate Skolem lookup tables in the current context.

  Also builds display-name maps for Skolem constants (sk0 → act1) and
  long/numeric prover variables (?:2006 → E1).
  """
  _ctx.skolem_types      = {}
  _ctx.skolem_fn_verbs   = {}
  _ctx.skolem_fn_actors  = {}
  _ctx.skolem_fn_targets = {}
  _ctx.skolem_fn_types   = {}
  _ctx.skolem_introduced = set()
  _ctx.skolem_display    = {}
  _ctx.var_display       = {}
  for step in proof:
    clause = step[2] if len(step) > 2 else []
    if not isinstance(clause, list):
      continue
    for atom in clause:
      if not isinstance(atom, list) or len(atom) < 3:
        continue
      pred = atom[0]
      if pred == "isa" and isinstance(atom[2], str) and re.match(r'^sk\d+$', atom[2]):
        _ctx.skolem_types.setdefault(atom[2], str(atom[1]))
      elif pred == "isa" and _is_skolem_fn(atom[2]):
        _ctx.skolem_fn_types.setdefault(atom[2][0], str(atom[1]))
      elif pred == "has type" and _is_skolem_fn(atom[1]):
        _ctx.skolem_fn_verbs.setdefault(str(atom[1]), str(atom[2]))
      elif pred == "has actor" and _is_skolem_fn(atom[1]):
        _ctx.skolem_fn_actors.setdefault(str(atom[1]), str(atom[2]))
      elif pred == "has target" and _is_skolem_fn(atom[1]):
        _ctx.skolem_fn_targets.setdefault(str(atom[1]), str(atom[2]))

  # Build Skolem display names: sk0 → act1 (for activity), evt1 (for event), etc.
  _TYPE_ABBREV = {"activity": "act", "event": "event", "set": "set"}
  type_counters = {}
  for sk in sorted(_ctx.skolem_types.keys(), key=lambda s: int(s[2:])):
    typ = _ctx.skolem_types[sk]
    abbrev = _TYPE_ABBREV.get(typ.lower(), typ.lower()[:3])
    n = type_counters.get(abbrev, 0) + 1
    type_counters[abbrev] = n
    _ctx.skolem_display[sk] = abbrev + str(n)

  # Build variable display names for long/numeric prover variables.
  # Collect all variables across the proof, rename ugly ones.
  all_vars = set()
  for step in proof:
    clause = step[2] if len(step) > 2 else []
    if isinstance(clause, list):
      _collect_vars(clause, all_vars)
  # Only rename variables that are long (>2 chars after ?:) or purely numeric.
  _SHORT_VARS = {"X", "Y", "Z", "W", "U", "V", "E", "N", "S", "K"}
  var_counter = {}
  for v in sorted(all_vars):
    bare = v[2:]  # strip "?:"
    if bare in _SHORT_VARS or (len(bare) <= 2 and bare[0].isalpha()):
      continue  # already short enough
    # Pick a letter based on variable role heuristics.
    if bare.isdigit():
      letter = "E"  # numeric vars are typically event-related
    elif bare[0].isalpha():
      letter = bare[0].upper()  # keep the first letter
    else:
      letter = "V"
    n = var_counter.get(letter, 0) + 1
    var_counter[letter] = n
    display = letter + str(n) if n > 1 or letter in var_counter else letter + str(n)
    _ctx.var_display[v] = display


def _collect_vars(obj, result):
  """Recursively collect all ?:-prefixed variable strings from a clause."""
  if isinstance(obj, str):
    if obj.startswith("?:"):
      result.add(obj)
  elif isinstance(obj, list):
    for el in obj:
      _collect_vars(el, result)


# ======== ambiguity scanning ========

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
      # Track both proper-name and common-noun bases for ambiguity detection.
      base_numbers.setdefault(base, set()).add(int(m.group(2)))
  elif isinstance(obj, list):
    for el in obj:
      _scan_constants(el, base_numbers, url_names)
  elif isinstance(obj, dict):
    for v in obj.values():
      _scan_constants(v, base_numbers, url_names)


# ======== Skolem helpers ========

def _is_skolem_fn(val):
  """Return True if val is a Skolem function term: a list whose first element
  matches sk\\d+ (e.g. ["sk0", "Greg 2", "Mike 1"])."""
  return (isinstance(val, list) and val and
          isinstance(val[0], str) and re.match(r'^sk\d+$', val[0]))


# ======== URL helpers ========

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
    if segments:
      name = segments[-1]
    else:
      return url
    # Basic URL decoding and underscore expansion
    name = name.replace("_", " ").replace("%20", " ").replace("%27", "'")
    return name if name else url
  except Exception:
    return url


# ======== constants ========

# Safe letters for labelling noun-phrase constants.
# Skips letters that are common stage-2 variable names (E, K, N, S, V, X, Y, Z)
# so that "car B" can never be confused with a proof variable.
_SAFE_LETTERS = "ABCDFGHIJLMPQRTUW"   # 17 slots; enough for any realistic proof

# Prepositions used as relations in ["is rel2", RELATION, E1, E2].
# These render as "E1 is RELATION E2" (no "of").
# Anything else (relational nouns: parent, part, member, …) renders as
# "E1 is RELATION of E2".
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


def _is_var_display(s):
  """Return True if s looks like a prover variable display name (e.g. 'X', 'V2006', 'R')."""
  return bool(re.match(r'^(V\d+|[A-Z]\d*)$', s))


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


# ======== entity naming ========

def _skolem_fn_to_name(term):
  """Render a Skolem function term ["sk0", arg1, arg2, ...] as English.

  Uses _ctx.skolem_fn_verbs / _ctx.skolem_fn_actors / _ctx.skolem_fn_targets
  (populated by compute_skolem_types) to describe the reified event.  Falls
  back to _ctx.skolem_fn_types (keyed by function name) for non-event objects.

  Examples (event Skolem):
    ["sk0","Greg 2","Mike 1"]  -> "the eating by Greg of Mike"
    ["sk0","?:X","Mike 1"]     -> "the eating of Mike"
    ["sk0","?:X","?:Y"]        -> "the eating event"
  Examples (object Skolem, type="roof"):
    ["sk0","$some_car"]        -> "the roof of some car"
    ["sk0","?:X"]              -> "a roof"
    (no type found)            -> "the event"
  """
  key  = str(term)
  verb = _ctx.skolem_fn_verbs.get(key)
  if not verb:
    # Not a reified event — try object-type lookup keyed by function name.
    fn_name = term[0] if isinstance(term, list) and term else ""
    obj_type = _ctx.skolem_fn_types.get(fn_name)
    if obj_type:
      arg = term[1] if len(term) > 1 else None
      if arg is None or (isinstance(arg, str) and arg.startswith("?:")):
        return _indef_article(obj_type) + " " + obj_type
      return "the " + obj_type + " of " + entity_name(arg)
    return "the event"
  gerund = _to_gerund(verb)

  actor_raw  = _ctx.skolem_fn_actors.get(key, "")
  target_raw = _ctx.skolem_fn_targets.get(key, "")

  # Only use ground (non-variable) actor/target in the description
  actor  = actor_raw  if actor_raw  and not actor_raw.startswith("?:") else ""
  target = target_raw if target_raw and not target_raw.startswith("?:") else ""

  if actor and target:
    return "the " + gerund + " by " + entity_name(actor) + " of " + entity_name(target)
  if actor:
    return "the " + gerund + " by " + entity_name(actor)
  if target:
    return "the " + gerund + " of " + entity_name(target)
  return "the " + gerund + " event"


def entity_name(val, with_url=False, proof_mode=False):
  """Display name for a logic constant or variable.

  - Skolem functions (lists)  -> "the eating by Greg of Mike" etc.
  - Variables (?:X)           -> strip prefix -> "X"
  - URL constants             -> extract last path segment ->
                                   "Paris" or "Paris (https://...)" depending
                                   on with_url and _ctx.ambiguous_url_names
  - Proper-name constants     -> strip trailing number -> "John 1" -> "John"
                                 (keeps number when base is in _ctx.ambiguous_bases)
  - Noun-phrase constants     -> replace number with safe letter ->
                                 "car 2" -> "car B",  "dog 1" -> "dog A"

  with_url=True   : append full URL in parentheses for URL constants
                    (used in proof steps for traceability)
  with_url=False  : omit URL unless the display name is ambiguous
                    (used in answer line for readability)
  proof_mode=True : skip entity_map for single common-noun entities to avoid
                    qualifier-predicate redundancy in proof steps (e.g.
                    "the very big mouse is very big" instead of
                    "the very big mouse is a very big mouse")
  """
  # Raw mode (json_flag): use raw logic IDs so English matches JSON output.
  # Variables strip ?:, everything else shown as-is.
  import globals as _g
  if _g.options.get("json_flag") and proof_mode:
    if _is_skolem_fn(val):
      return str(val)
    if not isinstance(val, str):
      return str(val)
    if val.startswith("?:"):
      bare = val[2:]
      return ("V" + bare) if bare.isdigit() else bare
    return val

  if _is_skolem_fn(val):
    return _skolem_fn_to_name(val)
  if not isinstance(val, str):
    return str(val)
  # Check entity map: prefer the user's original phrasing for answer display.
  # In proof_mode, skip entity_map for single (non-ambiguous) common-noun
  # entities — their qualifier adjectives often duplicate predicate content.
  if val in _ctx.entity_map:
    if proof_mode:
      m = re.match(r'^(.*\S)\s+(\d+)$', val)
      if m and m.group(1)[:1].islower() and m.group(1).lower() not in _ctx.ambiguous_bases:
        pass  # fall through to default "the NOUN" rendering below
      else:
        return _ctx.entity_map[val]
    else:
      name = _ctx.entity_map[val]
      if with_url and (val.startswith("http://") or val.startswith("https://")):
        return name + " (" + val + ")"
      return name
  if val.startswith("?:"):
    # Use the short display name if one was computed for this variable.
    orig = val
    if orig in _ctx.var_display:
      return _ctx.var_display[orig]
    val = val[2:]
    # Purely numeric names are prover-generated fresh variables — prefix with "V"
    if val.isdigit():
      val = "V" + val
  # Population constants: $some_not_* -> "a non-*",  $some_* -> "a/an *"
  if val.startswith("$some_not_"):
    noun = val[len("$some_not_"):].replace("_", " ")
    return _indef_article(noun) + " non-" + noun
  if val.startswith("$some_"):
    noun = val[len("$some_"):].replace("_", " ")
    return _indef_article(noun) + " " + noun
  # Skolem constants: sk0, sk1, ... -> "some TYPE act1" on first mention,
  # then just "act1" on subsequent mentions within the same proof.
  if re.match(r'^sk\d+$', val):
    display = _ctx.skolem_display.get(val, val)
    typ = _ctx.skolem_types.get(val)
    if typ:
      if val in _ctx.skolem_introduced:
        return display
      _ctx.skolem_introduced.add(val)
      return "some " + typ + " " + display
    return display
  # URL constant
  if val.startswith("http://") or val.startswith("https://"):
    name = _extract_url_name(val)
    if with_url or name in _ctx.ambiguous_url_names:
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
    if base.lower() in _ctx.ambiguous_bases:
      return base + " " + str(n)
    return base
  # Noun-phrase constant — replace number with a safe letter
  if 1 <= n <= len(_SAFE_LETTERS):
    label = _SAFE_LETTERS[n - 1]        # 1->A, 2->B, 3->C, 4->D, 5->F, …
  else:
    label = str(n)                       # fallback for very large indices
  return base + " " + label


def ans_atom_name(atom):
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
  return entity_name(val, with_url=False)


# ======== clause / atom rendering ========
# Converts CNF proof clauses to readable English.
# A clause is a list of atoms (disjunction); atoms with a "-" prefix are negated.
# Negated atoms are rendered as "if" conditions; positive atoms as "then" consequences.
# _atom_to_english handles every predicate in the stage-2 whitelist.

def _forall_or_to_english(frm):
  """Render ["forall", VAR, ["or", ["-isa", TYPE, VAR], CONCL]] as English.

  This is the GK encoding of ∀VAR.(TYPE(VAR) → CONCL), i.e. "all TYPEs are ...".
  Returns a string, or None if the pattern does not match.
  """
  if not (isinstance(frm, list) and len(frm) == 3 and frm[0] == "forall"):
    return None
  var  = frm[1]
  body = frm[2]
  if not (isinstance(body, list) and body and body[0] == "or"):
    return None
  # Find the -isa(TYPE, VAR) guard and the positive conclusion atom(s)
  neg_isa = None
  concls  = []
  for el in body[1:]:
    if (isinstance(el, list) and el and el[0] == "-isa"
        and len(el) >= 3 and el[2] == var):
      neg_isa = el
    else:
      concls.append(el)
  if neg_isa is None or not concls:
    return None
  typ = str(neg_isa[1])

  def _concl_pred(c):
    """Render a conclusion atom without its subject (the universal variable)."""
    if not isinstance(c, list) or not c:
      return str(c)
    p = str(c[0])
    neg = p.startswith("-")
    base = p[1:] if neg else p
    # has degree property: [pred, PROP, ENTITY(=VAR), DEGREE, RELCLASS]
    if base == "has degree property" and len(c) >= 3 and c[2] == var:
      adv, _ = _degree_parts(entity_name(c[3]) if len(c) > 3 else "")
      prop = str(c[1])
      prefix = "not " if neg else ""
      return prefix + adv + prop
    # has property: [pred, PROP, ENTITY(=VAR)]
    if base == "has property" and len(c) >= 3 and c[2] == var:
      prop = str(c[1])
      return ("not " if neg else "") + prop
    # fallback to full atom rendering
    base_atom = [base] + list(c[1:])
    return _atom_to_english_negated(base_atom) if neg else _atom_to_english(c)

  concl_text = " and ".join(_concl_pred(c) for c in concls)
  return "all " + typ + "s are " + concl_text


def block_to_english(block_atom):
  """Render a $block atom as an English exception string.

  Structure: ["$block", PRIORITY, ["$not", INNER]]
  Returns the negated rendering of INNER, or "" if malformed.
  """
  if not isinstance(block_atom, list) or len(block_atom) < 3:
    return ""
  inner = block_atom[2]
  if not (isinstance(inner, list) and inner and inner[0] == "$not"
          and len(inner) > 1 and isinstance(inner[1], list)):
    if isinstance(inner, list):
      return _atom_to_english(inner)
    return str(inner)
  body = inner[1]
  # Special case: forall-or pattern encodes a universal rule head.
  foe = _forall_or_to_english(body)
  if foe is not None:
    return "not: " + foe
  return _atom_to_english_negated(body)


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
  if re.match(r'^sk\d+$', val):
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


def _defq_ans_bridge(clause):
  """Detect the $defq/$ans bridge pattern in a 2-atom clause.

  Returns 'unwrap' for [-$defq*(args...), $ans(args...)]  -- defq drives ans
  Returns 'wrap'   for [$defq*(args...), -$ans(args...)]  -- ans drives defq
  Returns None otherwise (including wrong atom count or mismatched args).

  Both orderings (a,b) and (b,a) are checked.
  """
  if not isinstance(clause, list) or len(clause) != 2:
    return None
  a, b = clause[0], clause[1]
  if not isinstance(a, list) or not isinstance(b, list) or not a or not b:
    return None
  for first, second in [(a, b), (b, a)]:
    pa = str(first[0]);  args_a = first[1:]
    pb = str(second[0]); args_b = second[1:]
    if args_a != args_b:
      continue
    if pa.startswith("-$defq") and pb == "$ans":
      return "unwrap"
    if pa.startswith("$defq") and pb == "-$ans":
      return "wrap"
  return None


def clause_to_str(clause):
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

  # Detect the $defq/$ans bridge step that connects the internal answer
  # marker to the output answer atom (or vice versa).
  bridge = _defq_ans_bridge(clause)
  if bridge == "unwrap":
    return "technical answer unwrap step"
  if bridge == "wrap":
    return "technical answer wrap step"

  conditions    = []   # positively-rendered negated atoms -> "if ..."
  neg_atoms     = []   # base atoms (pred without "-") for pure-negative rendering
  consequences  = []   # (english_str, is_normally) pairs for positive atoms
  raw_pos_atoms = []   # raw positive atoms (for $block matching)
  block_atoms   = []   # raw $block atoms
  blocker_texts = []   # "except when ..." rendered from unmatched $block atoms

  for atom in clause:
    if not isinstance(atom, list) or not atom:
      continue
    pred = str(atom[0])
    if pred == "$block":
      block_atoms.append(atom)
    elif pred == "$ans":
      meaningful = _ans_display_args(atom[1:])
      if len(meaningful) >= 2:
        bracket = "[" + ", ".join(entity_name(a, with_url=True) for a in meaningful) + "]"
        consequences.append((bracket + " is an answer", False))
      elif meaningful:
        consequences.append((entity_name(meaningful[0]) + " is an answer", False))
      else:
        consequences.append((ans_atom_name(atom) + " is an answer", False))
      raw_pos_atoms.append(atom)
    elif pred.startswith("-"):
      base = [pred[1:]] + list(atom[1:])
      conditions.append(_atom_to_english(base))
      neg_atoms.append(base)
    else:
      consequences.append((_atom_to_english(atom), False))
      raw_pos_atoms.append(atom)

  # Detect standard defeasible pattern: $block body matches a positive conclusion.
  # When matched, render the conclusion with "normally" instead of appending
  # "except when ..." (which redundantly restates the conclusion's negation).
  matched_blocks = set()
  for bi, block in enumerate(block_atoms):
    if (isinstance(block, list) and len(block) >= 3
        and isinstance(block[2], list) and block[2] and block[2][0] == "$not"
        and len(block[2]) > 1):
      body = block[2][1]
      for ci, raw_atom in enumerate(raw_pos_atoms):
        if raw_atom == body:
          # Mark this consequence as defeasible and this $block as matched.
          text, _ = consequences[ci]
          consequences[ci] = (text, True)
          matched_blocks.add(bi)
          break

  # Unmatched $blocks get rendered as "except when ..." (post-resolution cases).
  for bi, block in enumerate(block_atoms):
    if bi not in matched_blocks:
      bt = block_to_english(block)
      if bt:
        blocker_texts.append(bt)

  # Deduplicate identical condition strings (e.g. isa(man,X) and
  # has_degree_property(strong,X,none,man) may both render as "X is a man").
  conditions = list(dict.fromkeys(conditions))

  # Build consequence text, prepending "normally" to defeasible conclusions.
  cons_parts = []
  for text, is_normally in consequences:
    cons_parts.append("normally " + text if is_normally else text)

  if conditions and cons_parts:
    result = "if " + " and ".join(conditions) + " then " + " or ".join(cons_parts)
  elif cons_parts:
    result = " or ".join(cons_parts)
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


# ======== atom-to-English converters ========
#
# Table-driven dispatch: each predicate has a (min_args, pos_fn, neg_fn) entry.
# pos_fn(e, args) returns the positive English string.
# neg_fn(e, args) returns the negated English string.
# Complex predicates use dedicated helpers; simple ones use inline lambdas.

def _isa_pos(e, args):
  # Use raw type string to avoid entity_map turning "man" into "the strong man".
  typ = str(args[0]) if args else e(0)
  ent = e(1)
  if typ == "activity": return ent + " is an activity"
  if typ == "set":      return ent + " is a set"
  return ent + " is " + _indef_article(typ) + " " + typ

def _isa_neg(e, args):
  typ = str(args[0]) if args else e(0)
  ent = e(1)
  if typ == "activity": return ent + " is not an activity"
  if typ == "set":      return ent + " is not a set"
  return ent + " is not " + _indef_article(typ) + " " + typ

def _is_rel2_pos(e, args):
  rel = e(0)
  last = rel.split()[-1].lower() if rel else ""
  if rel.lower() in _PREPOSITIONS or last in _PREPOSITIONS or last == "of":
    return e(1) + " is " + rel + " " + e(2)
  if _looks_like_verb(rel):
    return e(1) + " " + _conjugate_verb(rel) + " " + e(2)
  return e(1) + " is " + rel + " of " + e(2)

def _is_rel2_neg(e, args):
  rel = e(0)
  last = rel.split()[-1].lower() if rel else ""
  if rel.lower() in _PREPOSITIONS or last in _PREPOSITIONS or last == "of":
    return e(1) + " is not " + rel + " " + e(2)
  if _looks_like_verb(rel):
    return e(1) + " does not " + rel + " " + e(2)
  return e(1) + " is not " + rel + " of " + e(2)

def _has_degree_property_render(e, args, neg=False):
  prop = e(0); ent = e(1)
  adv, art_type = _degree_parts(e(2))
  relcls_raw = args[3] if len(args) > 3 else ""
  cop = " is not " if neg else " is "
  # Omit relclass when it's a variable, "none", or "entity" — these carry no
  # useful comparison-class info and produce ugly English like "a big none".
  if isinstance(relcls_raw, str) and (relcls_raw.startswith("?:")
      or relcls_raw in ("none", "entity")):
    return ent + cop + adv + prop
  # Omit relclass when it matches the entity's base noun — avoids redundancy
  # like "the mouse is a very big mouse" → "the mouse is very big".
  ent_raw = args[1] if len(args) > 1 else ""
  if isinstance(ent_raw, str) and isinstance(relcls_raw, str):
    ent_base = re.match(r'^(.*\S)\s+\d+$', ent_raw)
    if ent_base and ent_base.group(1).lower() == relcls_raw.lower():
      return ent + cop + adv + prop
  # Use the raw relclass string (not entity_name) to avoid entity_map lookup
  # turning class names like "man" into "the strong man".
  relcls = str(relcls_raw)
  art = "the" if art_type == "def" else _indef_article(adv if adv else prop)
  return ent + cop + art + " " + adv + prop + " " + relcls

def _has_degree_rel2_render(e, args, neg=False):
  rel = e(0); ent1 = e(1); ent2 = e(2)
  degree_raw = str(args[3]).lower() if len(args) > 3 else "none"
  last = rel.split()[-1].lower() if rel else ""
  cop = " is not " if neg else " is "
  if last in _PREPOSITIONS or last == "of":
    return ent1 + cop + rel + " " + ent2
  if _is_var_display(rel):
    if neg: return ent1 + " does not have a " + rel + "-relation with " + ent2
    return ent1 + " has a " + rel + "-relation with " + ent2
  if degree_raw in ("high", "more"):
    return ent1 + cop + _make_comparative(rel) + " than " + ent2
  if degree_raw == "most":
    return ent1 + cop.rstrip() + " the most " + rel + " of all compared to " + ent2
  if degree_raw in ("low", "less"):
    return ent1 + cop + "less " + rel + " than " + ent2
  if degree_raw == "least":
    return ent1 + cop.rstrip() + " the least " + rel + " of all compared to " + ent2
  return ent1 + cop + rel + " of " + ent2

def _is_var_raw(args, i):
  """True if args[i] is a raw variable string (starts with '?:')."""
  return (len(args) > i and isinstance(args[i], str) and args[i].startswith("?:"))

# Predicate dispatch table: pred -> (min_args, pos_fn, neg_fn)
# pos_fn / neg_fn signature: (e, args) -> str
_PRED_TABLE = {
  # core predicates
  "has property":       (2, lambda e,a: e(1)+" is "+e(0),
                            lambda e,a: e(1)+" is not "+e(0)),
  "have":               (2, lambda e,a: e(0)+" has "+e(1),
                            lambda e,a: e(0)+" does not have "+e(1)),
  "has part":           (2, lambda e,a: e(0)+" has "+e(1)+" as a part",
                            lambda e,a: e(0)+" does not have "+e(1)+" as a part"),
  "can":                (2, lambda e,a: e(0)+" can "+e(1),
                            lambda e,a: e(0)+" cannot "+e(1)),
  # predicates with complex logic
  "isa":                (2, _isa_pos, _isa_neg),
  "is rel2":            (3, _is_rel2_pos, _is_rel2_neg),
  "has degree property":(4, lambda e,a: _has_degree_property_render(e, a, neg=False),
                            lambda e,a: _has_degree_property_render(e, a, neg=True)),
  "has degree rel2":    (4, lambda e,a: _has_degree_rel2_render(e, a, neg=False),
                            lambda e,a: _has_degree_rel2_render(e, a, neg=True)),
  # event reification predicates
  "has type":           (2, lambda e,a: e(0)+" is a "+e(1)+" event",
                            lambda e,a: e(0)+" is not a "+e(1)+" event"),
  "has actor":          (2, lambda e,a: e(1)+" performs "+e(0),
                            lambda e,a: e(1)+" does not perform "+e(0)),
  "has target":         (2, lambda e,a: e(0)+" targets "+e(1),
                            lambda e,a: e(0)+" does not target "+e(1)),
  "has location":       (2, lambda e,a: e(0)+" takes place at "+e(1),
                            lambda e,a: e(0)+" does not take place at "+e(1)),
  "has instrument":     (2, lambda e,a: e(0)+" uses "+e(1),
                            lambda e,a: e(0)+" does not use "+e(1)),
  "has manner":         (2, lambda e,a: e(0)+" happens in a "+e(1)+" manner",
                            lambda e,a: e(0)+" does not happen in a "+e(1)+" manner"),
  "has direction":      (2, lambda e,a: e(0)+" goes towards "+e(1),
                            lambda e,a: e(0)+" does not go towards "+e(1)),
  "has time":           (2, lambda e,a: e(0)+" happens at "+("time " if _is_var_raw(a,1) else "")+e(1),
                            lambda e,a: e(0)+" does not happen at "+("time " if _is_var_raw(a,1) else "")+e(1)),
  # state / world predicates
  "state time":         (2, lambda e,a: "at time "+e(1),         None),
  "state location":     (2, lambda e,a: "at location "+e(1),     None),
  # set predicates
  "is set of":          (2, lambda e,a: e(1)+" is a set of "+e(0),
                            lambda e,a: e(1)+" is not a set of "+e(0)),
  "member":             (2, lambda e,a: e(0)+" is a member of "+e(1),
                            lambda e,a: e(0)+" is not a member of "+e(1)),
  "member has property":(2, lambda e,a: "members of "+e(1)+" are "+e(0),
                            lambda e,a: "members of "+e(1)+" are not "+e(0)),
  "is subset of":       (2, lambda e,a: e(0)+" is a subset of "+e(1),
                            lambda e,a: e(0)+" is not a subset of "+e(1)),
  "set union":          (3, lambda e,a: e(2)+" is the union of "+e(0)+" and "+e(1),
                            None),
  "$count":             (1, lambda e,a: "count of "+e(0),        None),
  # comparison predicates
  "=":                  (2, lambda e,a: e(0)+" equals "+e(1),
                            lambda e,a: e(0)+" does not equal "+e(1)),
  "<":                  (2, lambda e,a: e(0)+" is less than "+e(1),
                            lambda e,a: e(0)+" is not less than "+e(1)),
  ">":                  (2, lambda e,a: e(0)+" is greater than "+e(1),
                            lambda e,a: e(0)+" is not greater than "+e(1)),
  # mental predicates
  "kb":                 (3, lambda e,a: e(1)+" "+e(2)+" that ...", None),
  "kb force":           (0, None,                                  None),
}


def _render_atom(atom, negated=False):
  """Unified atom-to-English renderer.  Dispatches via _PRED_TABLE for most
  predicates; handles special cases (holds, normally, $defq*, etc.) inline.

  negated=False: positive form ("X is Y")
  negated=True:  natural negated form ("X is not Y")
  """
  if not isinstance(atom, list) or not atom:
    return ("not: " + str(atom)) if negated else str(atom)

  pred = str(atom[0])
  args = atom[1:]

  def e(i):
    """Display name of args[i] — proof_mode for simpler common-noun names."""
    if i >= len(args): return "?"
    return entity_name(args[i], with_url=True, proof_mode=True)

  # ---- table-driven dispatch ----
  entry = _PRED_TABLE.get(pred)
  if entry is not None:
    min_args, pos_fn, neg_fn = entry
    if len(args) < min_args:
      return ("not: " if negated else "") + _atom_fallback(atom)
    if negated:
      if neg_fn is not None:
        return neg_fn(e, args)
      return "not: " + (pos_fn(e, args) if pos_fn else _atom_fallback(atom))
    if pos_fn is not None:
      return pos_fn(e, args)
    return _atom_fallback(atom)

  # ---- special predicates requiring recursive dispatch or custom logic ----

  if pred == "typical":
    if len(args) >= 1:
      return (e(0) + " is not typical") if negated else (e(0) + " is typical")
    return "not typical" if negated else "typically"

  if pred == "typically":
    if len(args) >= 2:
      if negated:
        return e(0) + " does not typically " + str(args[1])
      return e(0) + " typically " + _conjugate_verb(str(args[1]))
    return "not typically" if negated else "typically"

  if pred == "holds":
    if len(args) >= 2 and isinstance(args[1], list):
      return _render_atom(args[1], negated=negated)
    return ("not: " if negated else "") + _atom_fallback(atom)

  if pred == "normally":
    if len(args) >= 1 and isinstance(args[0], list):
      return "normally, " + _render_atom(args[0], negated=negated)
    return "normally"

  if pred == "kb holds":
    if len(args) >= 2 and isinstance(args[1], list):
      return _render_atom(args[1], negated=negated)
    return ("not: " if negated else "") + _atom_fallback(atom)

  if pred == "kb says":
    if len(args) >= 3 and isinstance(args[2], list):
      if negated:
        return "not: " + e(1) + " says that " + _render_atom(args[2])
      return e(1) + " says that " + _render_atom(args[2])
    return ("not: " if negated else "") + _atom_fallback(atom)

  if pred == "next":
    return ""

  # ---- $defq* question-definition atoms ----
  if pred.startswith("$defq"):
    if not args:
      return "the answer does not hold" if negated else "answer holds"
    if len(args) == 1:
      return (e(0) + " is not the answer") if negated else (e(0) + " is the answer")
    bracket = "[" + ", ".join(entity_name(a, with_url=True) for a in args) + "]"
    return (bracket + " is not the answer") if negated else (bracket + " is the answer")

  # ---- traceability (skip in English) ----
  if pred in ("@id", "@p", "@definite"):
    if pred == "@id" and len(args) >= 2 and isinstance(args[1], list):
      return _render_atom(args[1], negated=negated)
    return ""

  # ---- fallback ----
  if negated:
    return "not: " + _render_atom(atom)
  return _atom_fallback(atom)


def _atom_fallback(atom):
  """Fallback renderer: pred(arg1, arg2) with underscores as spaces."""
  if not isinstance(atom, list) or not atom:
    return str(atom)
  pred = str(atom[0]).replace("_", " ")
  parts = []
  for a in atom[1:]:
    if isinstance(a, str):
      parts.append(entity_name(a, with_url=True))
    elif isinstance(a, list):
      parts.append(_render_atom(a))
    else:
      parts.append(str(a))
  return pred + "(" + ", ".join(parts) + ")" if parts else pred


def _atom_to_english(atom):
  """Convert a single logic atom to readable English."""
  return _render_atom(atom, negated=False)


def _atom_to_english_negated(atom):
  """Render a single atom in its natural negated English form.

  The atom argument is the BASE atom (predicate name WITHOUT the leading "-").
  """
  return _render_atom(atom, negated=True)


# =========== the end ==========
