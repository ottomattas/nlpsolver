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


# ======== module-level state (reset per proof) ========

# Entity display-name map built from stage-1 JSON.
# Maps entity id strings and URL strings to human-readable display names
# derived from the user's original phrasing (e.g. "America 1" -> "America",
# "https://.../United_States" -> "America", "car 1" -> "the red car").
# Set once per proof by set_entity_map(); consulted first in entity_name().
_entity_map = {}

def set_entity_map(emap):
  """Install a new entity display-name map for the current proof."""
  global _entity_map
  _entity_map = emap if isinstance(emap, dict) else {}

def get_entity_display(val):
  """Return the entity_map display name for val, or None if not mapped."""
  return _entity_map.get(val)

# Proper-name bases that appear with more than one distinct number in the
# current proof (e.g. "John" when both "John 1" and "John 3" are present).
# Set once by compute_ambiguity() before any rendering begins.
_ambiguous_bases = set()

# URL display names (last path segment) that map to two or more different URLs.
# When a name is in this set, the full URL is appended even in the answer line.
_ambiguous_url_names = set()

# Map from Skolem constant name (e.g. "sk0") to its type string (e.g. "animal"),
# derived by scanning proof steps for isa(TYPE, skN) atoms.
# Reset per proof by compute_skolem_types().
_skolem_types = {}

# Maps from str(skolem_function_term) to verb/actor/target strings,
# derived by scanning proof steps for has_type/has_actor/has_target atoms
# whose subject is a Skolem function (a list starting with sk\d+).
# Reset per proof by compute_skolem_types().
_skolem_fn_verbs   = {}   # str(term) -> verb string  (e.g. "eat")
_skolem_fn_actors  = {}   # str(term) -> actor string (e.g. "Greg 2")
_skolem_fn_targets = {}   # str(term) -> target string (e.g. "Mike 1")
_skolem_fn_types   = {}   # sk_name -> object type from isa(TYPE,[sk_name,...]) (e.g. "roof")


# ======== ambiguity detection ========

def compute_ambiguity(obj):
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


# ======== Skolem type tables ========

def _is_skolem_fn(val):
  """Return True if val is a Skolem function term: a list whose first element
  matches sk\\d+ (e.g. ["sk0", "Greg 2", "Mike 1"])."""
  return (isinstance(val, list) and val and
          isinstance(val[0], str) and re.match(r'^sk\d+$', val[0]))


def compute_skolem_types(proof):
  """Scan proof steps and populate Skolem lookup tables.

  _skolem_types      : skN (string constant) -> type string from isa(TYPE,skN)
  _skolem_fn_verbs   : str(fn_term) -> verb   from has_type(fn_term, VERB)
  _skolem_fn_actors  : str(fn_term) -> actor  from has_actor(fn_term, ACTOR)
  _skolem_fn_targets : str(fn_term) -> target from has_target(fn_term, TARGET)

  Called once per proof before rendering.  Only the first fact for each key
  is kept.
  """
  global _skolem_types, _skolem_fn_verbs, _skolem_fn_actors, _skolem_fn_targets
  global _skolem_fn_types
  _skolem_types      = {}
  _skolem_fn_verbs   = {}
  _skolem_fn_actors  = {}
  _skolem_fn_targets = {}
  _skolem_fn_types   = {}   # sk_name (e.g. "sk0") -> object type from isa(TYPE, [sk_name,...])
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
      # isa(TYPE, [skN, ...]) — Skolem function used as an object (e.g. a roof witness)
      elif pred == "isa" and _is_skolem_fn(atom[2]):
        fn_name = atom[2][0]
        _skolem_fn_types.setdefault(fn_name, str(atom[1]))
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


# ======== constants ========

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


# ======== linguistic helpers ========

def _indef_article(word):
  """'an' before vowel sounds, 'a' otherwise."""
  return "an" if word[:1].lower() in "aeiou" else "a"


def _conjugate_verb(v):
  """Third-person singular present tense of a bare verb (simple heuristic)."""
  if v.endswith(("s", "sh", "ch", "x", "z")):
    return v + "es"
  if v.endswith("y") and len(v) > 1 and v[-2] not in "aeiou":
    return v[:-1] + "ies"
  return v + "s"


def _make_comparative(adj):
  """Return the comparative form of an adjective (e.g. 'nice' -> 'nicer').

  Uses '-er' for short adjectives, 'more ADJ' for longer ones.
  """
  if not adj or " " in adj:
    return "more " + adj
  v = "aeiou"
  # ends in silent e: nice -> nicer, large -> larger
  if adj.endswith("e") and len(adj) > 2 and adj[-2] not in v:
    return adj + "r"
  # CVC doubling: big -> bigger, sad -> sadder
  if (len(adj) >= 3 and adj[-1] not in v + "wxhy"
      and adj[-2] in v and adj[-3] not in v):
    return adj + adj[-1] + "er"
  # ends in consonant-y: happy -> happier
  if adj.endswith("y") and len(adj) > 2 and adj[-2] not in v:
    return adj[:-1] + "ier"
  # short adjective (≤ 6 chars): append -er
  if len(adj) <= 6:
    return adj + "er"
  return "more " + adj


def _is_var_display(s):
  """Return True if s looks like a prover variable display name (e.g. 'X', 'V2006', 'R')."""
  return bool(re.match(r'^(V\d+|[A-Z]\d*)$', s))


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

  Uses _skolem_fn_verbs / _skolem_fn_actors / _skolem_fn_targets (populated by
  compute_skolem_types) to describe the reified event.  Falls back to
  _skolem_fn_types (keyed by function name) for non-event Skolem objects.

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
  verb = _skolem_fn_verbs.get(key)
  if not verb:
    # Not a reified event — try object-type lookup keyed by function name.
    fn_name = term[0] if isinstance(term, list) and term else ""
    obj_type = _skolem_fn_types.get(fn_name)
    if obj_type:
      arg = term[1] if len(term) > 1 else None
      if arg is None or (isinstance(arg, str) and arg.startswith("?:")):
        return _indef_article(obj_type) + " " + obj_type
      return "the " + obj_type + " of " + entity_name(arg)
    return "the event"
  gerund = _to_gerund(verb)

  actor_raw  = _skolem_fn_actors.get(key, "")
  target_raw = _skolem_fn_targets.get(key, "")

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


def entity_name(val, with_url=False):
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
  # Check entity map first: prefer the user's original phrasing over the
  # default URL-basename or id-suffix logic below.
  if val in _entity_map:
    name = _entity_map[val]
    if with_url and (val.startswith("http://") or val.startswith("https://")):
      return name + " (" + val + ")"
    return name
  if val.startswith("?:"):
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
  consequences  = []   # positively-rendered positive atoms -> "then ..."
  blocker_texts = []   # "except when ..." rendered from $block atoms

  for atom in clause:
    if not isinstance(atom, list) or not atom:
      continue
    pred = str(atom[0])
    if pred == "$block":
      bt = block_to_english(atom)
      if bt:
        blocker_texts.append(bt)
    elif pred == "$ans":
      meaningful = _ans_display_args(atom[1:])
      if len(meaningful) >= 2:
        bracket = "[" + ", ".join(entity_name(a, with_url=True) for a in meaningful) + "]"
        consequences.append(bracket + " is an answer")
      elif meaningful:
        consequences.append(entity_name(meaningful[0]) + " is an answer")
      else:
        consequences.append(ans_atom_name(atom) + " is an answer")
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


# ======== atom-to-English converters ========

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
    return entity_name(args[i], with_url=True)

  # ---- core predicates ----

  if pred == "isa":
    # ["isa", TYPE, ENTITY]
    if len(args) >= 2:
      typ = e(0)
      # TYPE is a class name, not a specific instance — strip any "the " prefix
      # that entity_map may have added for common-noun entity ids (e.g. "the city").
      if typ.startswith("the "):
        typ = typ[4:]
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
      relcls_raw = args[3] if len(args) > 3 else ""
      if isinstance(relcls_raw, str) and relcls_raw.startswith("?:"):
        # Unbound variable — omit class noun and article
        return ent + " is " + adv + prop
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
      rel        = e(0)
      ent1       = e(1)
      ent2       = e(2)
      degree_raw = str(args[3]).lower() if len(args) > 3 else "none"
      last = rel.split()[-1].lower() if rel else ""
      # Preposition relations: "ahead of X", "next to Y"
      if last in _PREPOSITIONS or last == "of":
        return ent1 + " is " + rel + " " + ent2
      # Generic variable as relation (from axiom clauses): use readable template
      if _is_var_display(rel):
        return ent1 + " has a " + rel + "-relation with " + ent2
      # True comparative degrees: render as "X is ADJer than Y"
      if degree_raw in ("high", "more"):
        return ent1 + " is " + _make_comparative(rel) + " than " + ent2
      if degree_raw == "most":
        return ent1 + " is the most " + rel + " of all compared to " + ent2
      if degree_raw in ("low", "less"):
        return ent1 + " is less " + rel + " than " + ent2
      if degree_raw == "least":
        return ent1 + " is the least " + rel + " of all compared to " + ent2
      # degree="none" or other: binary relation — "X is REL of Y"
      return ent1 + " is " + rel + " of " + ent2
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
      return e(0) + " is the answer"
    bracket = "[" + ", ".join(entity_name(a, with_url=True) for a in args) + "]"
    return bracket + " is the answer"

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
      parts.append(entity_name(a, with_url=True))
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
    return entity_name(args[i], with_url=True)

  # ---- core predicates ----

  if pred == "isa":
    if len(args) >= 2:
      typ = e(0); ent = e(1)
      if typ.startswith("the "):
        typ = typ[4:]
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
      relcls_raw = args[3] if len(args) > 3 else ""
      if isinstance(relcls_raw, str) and relcls_raw.startswith("?:"):
        # Unbound variable — omit class noun and article
        return ent + " is not " + adv + prop
      relcls = e(3)
      art = "the" if art_type == "def" else _indef_article(adv if adv else prop)
      return ent + " is not " + art + " " + adv + prop + " " + relcls
    return "not: " + _atom_fallback(atom)

  if pred == "has degree rel2":
    if len(args) >= 4:
      rel        = e(0)
      ent1       = e(1)
      ent2       = e(2)
      degree_raw = str(args[3]).lower() if len(args) > 3 else "none"
      last = rel.split()[-1].lower() if rel else ""
      if last in _PREPOSITIONS or last == "of":
        return ent1 + " is not " + rel + " " + ent2
      if _is_var_display(rel):
        return ent1 + " does not have a " + rel + "-relation with " + ent2
      if degree_raw in ("high", "more"):
        return ent1 + " is not " + _make_comparative(rel) + " than " + ent2
      if degree_raw in ("low", "less"):
        return ent1 + " is not less " + rel + " than " + ent2
      return ent1 + " is not " + rel + " of " + ent2
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
    if not args:       return "the answer does not hold"
    if len(args) == 1: return e(0) + " is not the answer"
    bracket = "[" + ", ".join(entity_name(a, with_url=True) for a in args) + "]"
    return bracket + " is not the answer"

  # ---- fallback ----

  return "not: " + _atom_to_english(atom)


# =========== the end ==========
