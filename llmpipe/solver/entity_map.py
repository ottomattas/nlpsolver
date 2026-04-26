# Entity display-name map built from stage-1 JSON.
#
# Entry point: build_entity_map(s1_json)
#
# Returns a flat dict {entity_id: display_name, url: display_name} that maps
# every entity identifier (local id string or Wikipedia URL) to the best
# human-readable display name for that entity.
#
# Rules (applied in priority order):
#
#  Single entity with a given base name
#    → display = base as written by the user (first occurrence).
#      Proper noun (uppercase): no article.
#      Common noun (lowercase): "the " prefix stored in the map.
#
#  Multiple entities sharing the same base name, all with distinct URLs
#    → fall back to Wikipedia page titles to disambiguate.
#
#  Multiple entities sharing the same base name, generic (no URL or same URL)
#    → qualifier extraction: look at the word(s) immediately before the entity
#      id in the first-seen unit text (skip articles / demonstratives), try
#      increasing lengths starting from 1 word until all names are unique.
#    → "the red car" preferred over "the very red car"; "car 1"/"car 2" used
#      as last resort when no qualifier makes the names unique.
#
# Words stripped when scanning for qualifiers (not kept in display name):
#   a  an  the  this  that  these  those
#
# First occurrence of each entity id wins; later occurrences of the same id
# are ignored (even if they appear in a richer textual context).
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

from collections import defaultdict
from linguistics import IRREGULAR_PAST_VERBS


# Words that are skipped when scanning backwards for qualifier words.
_SKIP_WORDS = frozenset({
  "a", "an", "the", "this", "that", "these", "those",
})

# Words that stop qualifier collection (can't be adjective modifiers).
_STOP_WORDS = frozenset({
  "if", "when", "while", "unless", "because", "since", "although", "though",
  "and", "or", "but", "nor", "so", "yet",
  "is", "are", "was", "were", "be", "been", "being",
  "has", "have", "had", "does", "do", "did",
  "can", "could", "will", "would", "shall", "should", "may", "might", "must",
  "in", "on", "at", "to", "from", "by", "with", "for", "of", "about",
  "into", "onto", "upon", "over", "under", "between", "through",
  "near", "above", "below", "beside", "behind", "before", "after",
  "during", "around", "along", "across", "against", "among", "within",
  "then", "than", "as", "not", "no",
  # Relative pronouns / wh-words (prevent "whom Eve" or "which car" as qualifiers)
  "who", "whom", "whose", "which", "where", "what",
}) | IRREGULAR_PAST_VERBS


# ======== id parsing ========

def _base_and_suffix(eid):
  """Split a stage-1 entity id into (base, suffix).

  "car 1"    -> ("car", "1")
  "John B"   -> ("John", "B")
  "elephants"-> ("elephants", None)   # generic, no suffix
  """
  parts = eid.rsplit(" ", 1)
  if len(parts) == 2:
    s = parts[1]
    if s.isdigit() or (len(s) == 1 and s.isalpha()):
      return parts[0], s
  return eid, None


# ======== qualifier extraction ========

def _qualifier_words(text, base, suffix, extra_stops=None):
  """Return the list of qualifier words immediately before 'base [suffix]' in text.

  Strips trailing punctuation from each token before matching.
  Scans backwards from the entity position, skipping _SKIP_WORDS, then
  collecting non-skip words until another skip word or start of string.
  extra_stops: set of lowercase words to treat as stop words (entity base names).
  """
  words   = text.split()
  cleaned = [w.rstrip(".,;:!?\"'") for w in words]
  base_lo = base.lower()

  # Try to find: cleaned[i] == base, cleaned[i+1] == suffix
  if suffix is not None:
    for i in range(len(cleaned) - 1):
      if cleaned[i].lower() == base_lo and cleaned[i + 1] == suffix:
        return _gather_backwards(cleaned, i, words, extra_stops=extra_stops)

  # Fallback: match base alone (suffix may have been elided in the text)
  for i in range(len(cleaned)):
    if cleaned[i].lower() == base_lo:
      return _gather_backwards(cleaned, i, words, extra_stops=extra_stops)

  return []


def _is_qualifier_stop(w, extra_stops=None):
  """True if w cannot be a pre-nominal adjective qualifier.

  Stops on: _STOP_WORDS, caller-supplied extra_stops (entity bases / verbs),
  bare digits (entity ID suffixes), past-tense -ed verbs (with a small
  participial-adjective allowlist), and possessive 's tokens.
  """
  wl = w.lower()
  if wl in _STOP_WORDS:
    return True
  if extra_stops and wl in extra_stops:
    return True
  if w.isdigit():
    return True
  if wl.endswith("ed") and len(wl) > 3 and wl not in ("red", "named", "called"):
    return True
  if wl == "'s" or wl.endswith("'s"):
    return True
  return False


def _gather_backwards(words, pos, raw_words=None, extra_stops=None):
  """Collect qualifier words to the left of words[pos].

  Pre-nominal adjectives sit between an article/determiner and the noun;
  the article itself bounds the noun phrase.  Walk backwards from pos-1
  collecting non-stop words; stop at the first SKIP_WORD (article/
  demonstrative), stop word, or clause boundary (comma/semicolon).
  Crucially we do NOT skip past a leading article — doing so would cross
  out of the noun phrase and pick up the preceding verb (e.g. "owns a
  house" → "owns" wrongly captured as a qualifier of "house").
  """
  def _at_boundary(idx):
    if raw_words and idx < len(raw_words):
      return raw_words[idx][-1:] in (",", ";")
    return False

  quals = []
  j = pos - 1
  while j >= 0 and words[j].lower() not in _SKIP_WORDS:
    if _at_boundary(j) or _is_qualifier_stop(words[j], extra_stops):
      break
    quals.insert(0, words[j])
    j -= 1
  return quals


# ======== display name builders ========

def _display_name(base, qual_words):
  """Build a display name from a base and qualifier words.

  Proper nouns (uppercase first letter): no article added.
  Common nouns (lowercase first letter): 'the ' prefix.
  Strips leading determiners from base to avoid "the the bear".
  """
  # Strip leading determiner from base (LLMs may include "the" in concrete IDs).
  b = base
  first = b.split()[0].lower() if b else ""
  if first in _SKIP_WORDS and " " in b:
    b = b.split(" ", 1)[1]
  if qual_words:
    # Drop qualifier words already present as a prefix of the base
    # (e.g., base "blue straw" with qualifier ["blue"] → skip "blue").
    b_words = b.lower().split()
    filtered = [q for q in qual_words if q.lower() not in b_words]
    if filtered:
      return "the " + " ".join(filtered) + " " + b
    # All qualifiers already in base — fall through to default
  if b[:1].islower():
    return "the " + b
  return b


def _url_title(url):
  """Extract a human-readable title from a Wikipedia (or similar) URL."""
  try:
    path = url.split("?")[0].split("#")[0]
    segs = [s for s in path.split("/") if s]
    if len(segs) >= 2:
      return segs[-1].replace("_", " ").replace("%20", " ").replace("%27", "'")
    return url
  except Exception:
    return url


# ======== adjective collection from stage-2 logic ========

_MAX_QUALIFIERS = 2   # max adjectives in display name unless needed for disambiguation


def _collect_adjectives_from_logic(s2_json):
  """Walk the stage-2 logic tree and collect adjectives for concrete entities.

  Finds ["has degree property", WORD, ENTITY, ...] and ["has property", WORD, ENTITY, ...]
  atoms where ENTITY is a concrete constant (not a variable).
  Returns {entity_id: [adjective_words]} with duplicates removed, order preserved.
  """
  result = defaultdict(list)
  seen   = defaultdict(set)     # entity -> set of lowercase adj words already added

  def _walk(node):
    if not isinstance(node, list) or not node:
      return
    op = node[0]
    if op in ("has degree property", "has property") and len(node) >= 3:
      word   = node[1]
      entity = node[2]
      if isinstance(word, str) and isinstance(entity, str) and not entity.startswith("?:"):
        w_lo = word.lower()
        if w_lo not in seen[entity]:
          seen[entity].add(w_lo)
          result[entity].append(word)
    for el in node:
      if isinstance(el, list):
        _walk(el)

  if isinstance(s2_json, list):
    _walk(s2_json)
  return dict(result)


def _collect_action_verbs(s1_json, s2_json=None):
  """Collect action root verbs from stage-1 JSON and relation names from stage-2.

  Returns a set of lowercase verb strings that should not be used as qualifiers.
  """
  verbs = set()
  for para in s1_json:
    if not isinstance(para, dict):
      continue
    for unit in para.get("units", []):
      if not isinstance(unit, dict):
        continue
      for action in unit.get("actions", []):
        if isinstance(action, dict):
          root = action.get("root", "")
          if root:
            verbs.add(root.lower())
  # Also collect relation names from stage-2 "is rel2" atoms — these are
  # verbs/relations (e.g. "like", "fear") that should never be qualifiers.
  if s2_json:
    _collect_rel2_verbs(s2_json, verbs)
  return verbs


def _collect_rel2_verbs(node, verbs):
  """Recursively scan stage-2 JSON for ["is rel2", REL, ...] and collect REL."""
  if not isinstance(node, list) or not node:
    return
  if (node[0] in ("is rel2", "-is rel2", "has degree rel2", "-has degree rel2")
      and len(node) >= 2 and isinstance(node[1], str) and not node[1].startswith("?:")):
    verbs.add(node[1].lower())
  for el in node:
    if isinstance(el, list):
      _collect_rel2_verbs(el, verbs)


def _collect_text_qualifiers(s1_json, action_verbs=None):
  """Collect pre-nominal qualifier words for each entity across ALL ASU texts.

  Scans both ASU ``text`` fields and paragraph ``raw`` fields so that
  pre-nominal adjectives survive even when the LLM drops them from the
  simplified ASU text (e.g. Gemini turning "The big bear is strong" into
  "The bear 1 is strong").

  action_verbs: set of lowercase verb roots from stage-1 actions, treated as
  extra stop words to prevent "drove" or "buy" from being picked up as qualifiers.

  Returns {entity_id: [qualifier_words]} — union of qualifiers from every
  text that mentions the entity.
  """
  eid_texts = defaultdict(list)
  eid_info  = {}
  for para in s1_json:
    if not isinstance(para, dict):
      continue
    raw = para.get("raw", "")
    for unit in para.get("units", []):
      if not isinstance(unit, dict):
        continue
      text = unit.get("text", "")
      if not text:
        continue
      for ent in unit.get("entities", []):
        if not isinstance(ent, dict):
          continue
        eid = ent.get("id", "")
        if not eid:
          continue
        if eid not in eid_info:
          eid_info[eid] = _base_and_suffix(eid)
        eid_texts[eid].append(text)
        if raw:
          eid_texts[eid].append(raw)

  # Build extra stop words: entity base names + action verbs + conjugations.
  # Prevents "John" in "John 1 drove a car 2" from becoming a qualifier for
  # "car 2", and "likes"/"gave" from becoming qualifiers.
  entity_bases = {info[0].lower() for info in eid_info.values()}
  if action_verbs:
    entity_bases = entity_bases | action_verbs
    for v in action_verbs:
      entity_bases.add(v + "s")
      entity_bases.add(v + "es")
      entity_bases.add(v + "d")
      entity_bases.add(v + "ed")
      entity_bases.add(v + "ing")

  result = {}
  for eid, texts in eid_texts.items():
    base, suffix = eid_info[eid]
    seen_quals = []
    seen_set   = set()
    for text in texts:
      quals = _qualifier_words(text, base, suffix, extra_stops=entity_bases)
      for q in quals:
        q_lo = q.lower()
        if q_lo not in seen_set:
          seen_set.add(q_lo)
          seen_quals.append(q)
    result[eid] = seen_quals
  return result


def _entity_quals(eid, text_quals, logic_adjs, base, suffix, need_disambig=False):
  """Determine the qualifier words to use for an entity's display name.

  text_quals  : qualifiers from pre-nominal position in ASU texts (across all ASUs)
  logic_adjs  : adjectives from stage-2 logic (["has degree property",...] atoms)
  need_disambig: True if multiple entities share the same base and we need to tell them apart

  Returns a list of qualifier words.
  Rules:
    - Pre-nominal qualifiers (from text) are always preferred.
    - Logic adjectives supplement when text has none (e.g., relative clause adjectives).
    - Limit to _MAX_QUALIFIERS unless disambiguation requires more.
  """
  tq = text_quals.get(eid, [])
  la = logic_adjs.get(eid, [])

  if tq:
    quals = list(tq)
    if not need_disambig:
      return quals[:_MAX_QUALIFIERS]
    return quals
  else:
    # No pre-nominal qualifiers — use logic adjectives as qualifying adjectives.
    # For proper nouns (uppercase base) that are unique, skip logic adjectives
    # entirely: "John" is better than "the strong John" when there's only one John.
    if not need_disambig:
      if base[:1].isupper():
        return []
      return la[:1]
    return la[:_MAX_QUALIFIERS] if len(la) <= _MAX_QUALIFIERS else la


# ======== disambiguation for multi-entity groups ========

def _disambiguate_with_qualifiers(group, base, text_quals, logic_adjs):
  """Assign unique display names to a group of entities via qualifier words.

  group      : list of (eid, url, text, suffix)
  base       : original-case base string (e.g. "car")
  text_quals : {eid: [pre-nominal qualifier words]} from all ASU texts
  logic_adjs : {eid: [adjective words]} from stage-2 logic

  Returns {eid: display_name}.  Falls back to raw id strings when no
  qualifier combination can make all names unique.
  """
  # Collect qualifier word-lists for each entity, combining text and logic sources
  qual_map = {}
  for eid, url, text, suffix in group:
    quals = _entity_quals(eid, text_quals, logic_adjs, base, suffix, need_disambig=True)
    qual_map[eid] = quals

  eids    = [g[0] for g in group]
  max_len = max((len(qual_map[e]) for e in eids), default=0)

  for n in range(1, max_len + 1):
    # Take the n rightmost qualifier words (closest to the base noun)
    keys = {}
    for eid in eids:
      q = qual_map[eid]
      taken = q[-n:] if len(q) >= n else q
      keys[eid] = " ".join(taken).lower()

    if len(set(keys.values())) == len(eids):
      # All unique at this qualifier length — build display names
      result = {}
      for eid in eids:
        q = qual_map[eid]
        taken = q[-n:] if len(q) >= n else q
        result[eid] = _display_name(base, taken)
      return result

  # No unique combination found — fall back to entity id strings
  return {eid: eid for eid in eids}


# ======== main entry point ========

def build_entity_map(s1_json, s2_json=None):
  """Build {entity_id: display_name, url: display_name} from stage-1 JSON.

  Keys include both local id strings (e.g. "America 1") and URL strings
  (e.g. "https://en.wikipedia.org/wiki/United_States").  The display name
  uses the user's original phrasing (first occurrence) wherever possible.

  If s2_json is provided, adjectives from the stage-2 logic are used to
  supplement text-based qualifiers (handles relative-clause adjectives like
  "the bear who is big").
  """
  if not s1_json or not isinstance(s1_json, list):
    return {}

  # --- collect qualifiers from all ASU texts and from stage-2 logic ---
  action_verbs = _collect_action_verbs(s1_json, s2_json=s2_json)
  text_quals = _collect_text_qualifiers(s1_json, action_verbs=action_verbs)
  logic_adjs = _collect_adjectives_from_logic(s2_json) if s2_json else {}

  # --- collect entities; first occurrence wins ---
  seen_ids = set()
  # list of (eid, url_or_None, first_text, base, suffix)
  entities = []

  for para in s1_json:
    if not isinstance(para, dict):
      continue
    for unit in para.get("units", []):
      if not isinstance(unit, dict):
        continue
      text = unit.get("text", "")
      for ent in unit.get("entities", []):
        if not isinstance(ent, dict):
          continue
        eid = ent.get("id", "")
        if not eid or eid in seen_ids:
          continue
        seen_ids.add(eid)
        url  = ent.get("url")
        base, suffix = _base_and_suffix(eid)
        entities.append((eid, url, text, base, suffix))

  if not entities:
    return {}

  # --- group by lowercase base name ---
  by_base = defaultdict(list)
  for eid, url, text, base, suffix in entities:
    by_base[base.lower()].append((eid, url, text, base, suffix))

  result = {}  # will hold id->name and url->name

  for base_lower, group in by_base.items():
    base_written = group[0][3]   # original-case base from first occurrence

    if len(group) == 1:
      # --- single entity ---
      eid, url, text, base, suffix = group[0]
      quals = _entity_quals(eid, text_quals, logic_adjs, base, suffix)
      display = _display_name(base_written, quals)
      result[eid] = display
      if url:
        result.setdefault(url, display)

    else:
      # --- multiple entities share the same base ---
      # Separate bare class names (no suffix) from concrete instances (with suffix).
      # Bare class names like "fox" don't conflict with concrete "fox 2".
      concrete = [g for g in group if g[4] is not None]
      bare     = [g for g in group if g[4] is None]

      # Process bare class entities as individual entries
      for eid, url, text, base, suffix in bare:
        quals = _entity_quals(eid, text_quals, logic_adjs, base, suffix)
        display = _display_name(base_written, quals)
        result[eid] = display
        if url:
          result.setdefault(url, display)

      # Process concrete entities as a group (may need disambiguation)
      disambig = concrete if concrete else []
      if len(disambig) <= 1:
        for eid, url, text, base, suffix in disambig:
          quals = _entity_quals(eid, text_quals, logic_adjs, base, suffix)
          display = _display_name(base_written, quals)
          result[eid] = display
          if url:
            result.setdefault(url, display)
      else:
        urls = [g[1] for g in disambig]
        all_have_url    = all(u is not None for u in urls)
        distinct_urls   = len(set(u for u in urls if u)) == len(disambig)

        if all_have_url and distinct_urls:
          for eid, url, text, base, suffix in disambig:
            title = _url_title(url)
            result[eid] = title
            result.setdefault(url, title)
        else:
          sub = [(eid, url, text, suffix) for eid, url, text, base, suffix in disambig]
          names = _disambiguate_with_qualifiers(sub, base_written, text_quals, logic_adjs)
          for eid, url, text, base, suffix in disambig:
            display = names.get(eid, eid)
            result[eid] = display
            if url:
              result.setdefault(url, display)

  _apply_genitive_overrides(result, s2_json, eid_to_base={e: b for e, _, _, b, _ in entities})
  return result


def _apply_genitive_overrides(result, s2_json, eid_to_base):
  """Override generic "the X" displays with "OWNER's X" derived from
  ["is rel2","X of",ENT,OWNER] atoms in stage-2 logic.

  Only applies when the relation head ("X" in "X of") matches the entity's
  Stage-1 base name — this is the safety filter that distinguishes kinship
  / role relations ("sister of", "owner of") from spatial ones ("north of",
  "in front of") where ENT.base is a place noun, not the role word.
  """
  if not s2_json:
    return
  for ent, role, owner in _collect_genitive_relations(s2_json):
    if ent not in result or owner not in result:
      continue
    role_head = role[:-len(" of")].strip()
    if not role_head:
      continue
    base = eid_to_base.get(ent, "")
    if base.lower() != role_head.lower():
      continue
    owner_disp = result[owner]
    if not owner_disp:
      continue
    suffix = "'" if owner_disp.endswith("s") else "'s"
    result[ent] = owner_disp + suffix + " " + role_head


def _collect_genitive_relations(s2_json):
  """Yield (entity_id, relation_name, owner_id) from ["is rel2","X of",ENT,OWNER]."""
  results = []
  def _walk(node):
    if not isinstance(node, list) or not node:
      return
    if (node[0] == "is rel2" and len(node) >= 4
        and isinstance(node[1], str) and node[1].lower().endswith(" of")
        and isinstance(node[2], str) and not node[2].startswith("?:")
        and isinstance(node[3], str) and not node[3].startswith("?:")):
      results.append((node[2], node[1], node[3]))
    for el in node:
      if isinstance(el, list):
        _walk(el)
  _walk(s2_json)
  return results


# =========== the end ===========
