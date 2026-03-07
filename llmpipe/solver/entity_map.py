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


# Words that are skipped when scanning backwards for qualifier words.
_SKIP_WORDS = frozenset({
  "a", "an", "the", "this", "that", "these", "those",
})


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

def _qualifier_words(text, base, suffix):
  """Return the list of qualifier words immediately before 'base [suffix]' in text.

  Strips trailing punctuation from each token before matching.
  Scans backwards from the entity position, skipping _SKIP_WORDS, then
  collecting non-skip words until another skip word or start of string.
  """
  words   = text.split()
  cleaned = [w.rstrip(".,;:!?\"'") for w in words]
  base_lo = base.lower()

  # Try to find: cleaned[i] == base, cleaned[i+1] == suffix
  if suffix is not None:
    for i in range(len(cleaned) - 1):
      if cleaned[i].lower() == base_lo and cleaned[i + 1] == suffix:
        return _gather_backwards(cleaned, i)

  # Fallback: match base alone (suffix may have been elided in the text)
  for i in range(len(cleaned)):
    if cleaned[i].lower() == base_lo:
      return _gather_backwards(cleaned, i)

  return []


def _gather_backwards(words, pos):
  """Collect qualifier words to the left of words[pos].

  Skips over leading _SKIP_WORDS, then collects non-skip words.
  Returns them in left-to-right order (closest to base is last).
  """
  j = pos - 1
  while j >= 0 and words[j].lower() in _SKIP_WORDS:
    j -= 1
  quals = []
  while j >= 0 and words[j].lower() not in _SKIP_WORDS:
    quals.insert(0, words[j])
    j -= 1
  return quals


# ======== display name builders ========

def _display_name(base, qual_words):
  """Build a display name from a base and qualifier words.

  Proper nouns (uppercase first letter): no article added.
  Common nouns (lowercase first letter): 'the ' prefix.
  """
  if qual_words:
    return "the " + " ".join(qual_words) + " " + base
  if base[:1].islower():
    return "the " + base
  return base


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


# ======== disambiguation for multi-entity groups ========

def _disambiguate_with_qualifiers(group, base):
  """Assign unique display names to a group of entities via qualifier words.

  group  : list of (eid, url, text, suffix)
  base   : original-case base string (e.g. "car")

  Returns {eid: display_name}.  Falls back to raw id strings when no
  qualifier combination can make all names unique.
  """
  # Collect qualifier word-lists for each entity
  qual_map = {}
  for eid, url, text, suffix in group:
    qual_map[eid] = _qualifier_words(text, base, suffix)

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

def build_entity_map(s1_json):
  """Build {entity_id: display_name, url: display_name} from stage-1 JSON.

  Keys include both local id strings (e.g. "America 1") and URL strings
  (e.g. "https://en.wikipedia.org/wiki/United_States").  The display name
  uses the user's original phrasing (first occurrence) wherever possible.
  """
  if not s1_json or not isinstance(s1_json, list):
    return {}

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
      display = _display_name(base_written, [])
      result[eid] = display
      if url:
        result.setdefault(url, display)

    else:
      # --- multiple entities share the same base ---
      urls = [g[1] for g in group]
      all_have_url    = all(u is not None for u in urls)
      distinct_urls   = len(set(u for u in urls if u)) == len(group)

      if all_have_url and distinct_urls:
        # All entities have distinct URLs → use Wikipedia titles
        for eid, url, text, base, suffix in group:
          title = _url_title(url)
          result[eid] = title
          result.setdefault(url, title)
      else:
        # Use qualifier extraction
        sub = [(eid, url, text, suffix) for eid, url, text, base, suffix in group]
        names = _disambiguate_with_qualifiers(sub, base_written)
        for eid, url, text, base, suffix in group:
          display = names.get(eid, eid)
          result[eid] = display
          if url:
            result.setdefault(url, display)

  return result


# =========== the end ===========
