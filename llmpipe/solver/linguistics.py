# Pure linguistic utility functions for English rendering.
#
# These are simple heuristic helpers with no dependency on proof state
# or any other module in the pipeline.
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


def indef_article(word):
  """'an' before vowel sounds, 'a' otherwise."""
  return "an" if word[:1].lower() in "aeiou" else "a"


def conjugate_verb(v):
  """Third-person singular present tense of a bare verb (simple heuristic)."""
  if v.endswith(("s", "sh", "ch", "x", "z")):
    return v + "es"
  if v.endswith("y") and len(v) > 1 and v[-2] not in "aeiou":
    return v[:-1] + "ies"
  return v + "s"


def make_comparative(adj):
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


def to_gerund(verb):
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


# =========== the end ==========
