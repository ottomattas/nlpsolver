#!/usr/bin/env python3
"""
verify_tests.py  --  audit an nlpsolver test file using GPT, Gemini and Claude
as logic judges, then produce an annotated copy.

For each test [text, expected] the three LLMs are asked (with thinking enabled)
whether the expected answer is correct and what alternatives exist.  The result
is a goodness score (0-100) and an annotated output file.

Usage:
  python3 verify_tests.py tests/tests_core.py [options]

Options:
  --out FILE          write annotated output to FILE
                      (default: <input_stem>_verified.py in the same directory)
  --limit N           process only the first N tests  (default: all)
  --skip N            skip the first N tests           (default: 0)
  --think LEVEL       reasoning level: none | low | medium  (default: medium)
  --dry-run           print results but do not write output file

Goodness score:
  100  all three LLMs agree the expected answer is correct
   67  two LLMs agree
   33  one LLM agrees
    0  none agree
  Values in between arise when LLM alternatives soft-match the expected answer.

Output format: each test entry becomes [text, expected, metadata_dict] where
metadata_dict contains "goodness", "alternatives" and "comment" fields.
If an entry already has a third element (dict), it is updated in place.
test.py only reads entry[0] and entry[1], so the third element is ignored there.
"""

import sys
import os
import json
import re
import threading
import random

# Allow importing from solver/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "solver"))

import llmcall
import globals as _globals
import cache as _cache_mod

# ── LLM versions used for verification ────────────────────────────────────────
VERIFY_GPT_VERSION    = "gpt-5.1"
VERIFY_CLAUDE_VERSION = "claude-sonnet-4-6"
VERIFY_GEMINI_VERSION = "gemini-2.5-flash"

# ── matching helpers (mirror of test.py) ──────────────────────────────────────

_SPATIAL_PREPS = frozenset({
  "in", "on", "at", "near", "above", "under", "below", "over",
  "inside", "outside", "behind", "beside", "between", "by",
  "within", "upon", "onto", "into",
})
_ARTICLES       = frozenset({"a", "an", "the"})
_CONF_QUALIFIERS = frozenset({"probably", "likely", "perhaps", "certainly", "possibly"})


def _split_and_phrases(txt):
  parts = re.split(r',\s+and\s+|,\s+|\s+and\s+', txt)
  return [p.strip() for p in parts if p.strip()]


def _parse_phrase(phrase):
  words = phrase.lower().replace(".", "").replace(",", "").split()
  prep = ""
  if words and words[0] in _SPATIAL_PREPS:
    prep = words[0]
    words = words[1:]
  words = [w for w in words if w not in _ARTICLES]
  return prep, " ".join(words)


def _phrases_match(expected_str, received_str):
  exp = _split_and_phrases(expected_str)
  rec = _split_and_phrases(received_str)
  if len(exp) != len(rec) or len(exp) <= 1:
    return False
  exp_p = sorted([_parse_phrase(p) for p in exp], key=lambda x: x[1])
  rec_p = sorted([_parse_phrase(p) for p in rec], key=lambda x: x[1])
  for (ep, ec), (rp, rc) in zip(exp_p, rec_p):
    if ec != rc:
      return False
    if ep and rp and ep != rp:
      return False
  return True


def _norm_conf(txt):
  if not isinstance(txt, str):
    return txt
  parts = txt.split(" ", 1)
  if len(parts) == 2 and parts[0].rstrip(".").lower() in _CONF_QUALIFIERS:
    return parts[1]
  return txt


def _standardize(txt):
  if not isinstance(txt, str):
    return txt
  txt = txt.replace(".", "").replace(",", " ").lower()
  words = [w for w in txt.split() if w not in {"a", "an", "the"} and len(w) > 1]
  words.sort()
  return words


def result_matches(expected, received):
  """Return True if received is an acceptable answer for expected."""
  if received is True:  received = "True."
  if received is False: received = "False."
  if expected is True:  expected = "True."
  if expected is False: expected = "False."
  if not received:
    return False
  cleaned = received
  if isinstance(cleaned, str) and "(" in cleaned and ")" in cleaned:
    tmp = []; depth = 0
    for ch in cleaned:
      if ch == "(":   depth += 1
      elif ch == ")": depth -= 1
      elif depth == 0: tmp.append(ch)
    cleaned = "".join(tmp).replace(" .", ".").strip()
  if isinstance(cleaned, str):
    cleaned = cleaned.split("\n")[0].strip()
  if expected is None:
    return isinstance(cleaned, str) and cleaned.startswith("Unknown")
  if isinstance(expected, str):
    expected = expected.strip()
  if expected == cleaned:
    return True
  if isinstance(expected, str) and isinstance(cleaned, str):
    if _phrases_match(expected, cleaned):
      return True
  if _standardize(expected) == _standardize(cleaned):
    return True
  nc = _norm_conf(cleaned)
  ne = _norm_conf(expected)
  if nc != cleaned or ne != expected:
    if nc == ne:
      return True
    if _standardize(ne) == _standardize(nc):
      return True
  return False


# ── verification prompt ────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are an expert in logical reasoning and natural language understanding.
You will be given a short logical reasoning problem (a few sentences followed
by a question) and a proposed expected answer.  Your job is to judge whether
that answer is correct for the most natural, standard interpretation.

Rules:
- Answer types: boolean questions → "True.", "False.", or "Unknown."
  (Unknown = cannot be determined from the given information alone).
  Confidence-qualified variants like "Probably true." are also valid.
- Who/what questions → one or more entity names ending in ".", e.g. "John."
  or "John and Mary."
- None / null expected means the correct answer is "Unknown."
- Do NOT solve the problem yourself first and then judge — reason about the
  problem and the expected answer together.

Respond ONLY with a single JSON object, no markdown fences, no extra text:
{
  "correct": true or false,
  "alternatives": [],
  "comment": "one short sentence"
}

"alternatives": list up to 3 alternative answers that are also correct,
  but only if they genuinely differ from the proposed expected answer.
  Leave the list empty when the expected answer is correct and no alternatives exist.
"comment": one sentence summarising your reasoning.
"""


def _expected_display(expected):
  if expected is None:  return "Unknown."
  if expected is True:  return "True."
  if expected is False: return "False."
  return str(expected)


def _make_user_prompt(text, expected):
  return (
    "Problem:\n" + text.strip() +
    "\n\nProposed expected answer: " + _expected_display(expected)
  )


# ── LLM calls ─────────────────────────────────────────────────────────────────

def _call_llm_for_verification(llm, version, text, expected, think):
  """Call one LLM and return the raw string result."""
  user = _make_user_prompt(text, expected)
  return llmcall.call_llm(
    _SYSTEM_PROMPT, user,
    llm=llm, version=version,
    think=think,
    max_tokens=(think + 800) if think else 800,
  )


def _parse_response(raw):
  """Parse JSON from an LLM response string.  Returns dict or None."""
  if not raw:
    return None
  txt = raw.strip()
  # Strip markdown code fences if present
  if txt.startswith("```"):
    txt = re.sub(r"^```[a-z]*\n?", "", txt)
    txt = re.sub(r"\n?```\s*$", "", txt.strip())
  txt = txt.strip()
  try:
    return json.loads(txt)
  except Exception:
    m = re.search(r'\{.*\}', txt, re.DOTALL)
    if m:
      try:
        return json.loads(m.group())
      except Exception:
        pass
  return None


def _call_all_llms(text, expected, think):
  """Call GPT, Gemini, Claude in parallel.  Returns list of 3 dicts (or None)."""
  results = [None, None, None]
  specs = [
    ("gpt",    VERIFY_GPT_VERSION,    0),
    ("gemini", VERIFY_GEMINI_VERSION, 1),
    ("claude", VERIFY_CLAUDE_VERSION, 2),
  ]

  def _worker(llm, version, idx):
    raw = _call_llm_for_verification(llm, version, text, expected, think)
    results[idx] = _parse_response(raw)

  threads = [threading.Thread(target=_worker, args=spec) for spec in specs]
  for t in threads: t.start()
  for t in threads: t.join()
  return results


# ── goodness & annotation ─────────────────────────────────────────────────────

def _compute_annotation(expected, responses):
  """
  Compute goodness score, collect alternatives, build comment.

  Returns dict with keys: goodness (int 0-100), alternatives (list),
  comment (str), new_expected (same type as expected, possibly changed).
  """
  llm_names = ["gpt", "gemini", "claude"]
  agrees = 0
  llm_verdicts = []
  all_alternatives = []

  for name, resp in zip(llm_names, responses):
    if resp is None:
      llm_verdicts.append(name + ": error")
      continue
    correct = resp.get("correct", False)
    alts    = [a for a in (resp.get("alternatives") or []) if a][:3]
    cmt     = (resp.get("comment") or "").strip()

    # An LLM "agrees" if it says correct=True, or if one of its alternatives
    # matches the expected answer via result_matches.
    llm_agrees = correct
    if not llm_agrees:
      for a in alts:
        if result_matches(expected, a):
          llm_agrees = True
          break

    if llm_agrees:
      agrees += 1
      llm_verdicts.append(name + ": correct")
    else:
      if alts:
        alts_short = ", ".join('"' + a + '"' for a in alts)
        llm_verdicts.append(name + ": wrong, suggests " + alts_short)
      else:
        llm_verdicts.append(name + ": wrong")

    for a in alts:
      if a and a not in all_alternatives:
        all_alternatives.append(a)

  goodness = round(agrees / 3 * 100)

  # If nobody agrees, look for a consensus alternative (≥2 LLMs propose it).
  new_expected = expected
  if goodness == 0 and all_alternatives:
    votes = {}
    for resp in responses:
      if not resp:
        continue
      for a in (resp.get("alternatives") or [])[:3]:
        key = tuple(_standardize(a))
        votes[key] = votes.get(key, 0) + 1
    best_key = max(votes, key=votes.__getitem__) if votes else None
    if best_key and votes[best_key] >= 2:
      # Find the canonical string for this key
      for resp in responses:
        if not resp:
          continue
        for a in (resp.get("alternatives") or [])[:3]:
          if tuple(_standardize(a)) == best_key:
            new_expected = a
            break
        if new_expected != expected:
          break

  comment = "; ".join(llm_verdicts)
  return {
    "goodness":     goodness,
    "alternatives": all_alternatives[:3],
    "comment":      comment,
    "new_expected": new_expected,
  }


# ── test file I/O ──────────────────────────────────────────────────────────────

def _load_tests(path):
  """Load test file via eval() — same approach as test.py."""
  with open(path) as f:
    src = f.read()
  tests = eval(src)
  if not isinstance(tests, list):
    raise ValueError("Test file does not contain a list.")
  return tests


def _repr_expected(v):
  if v is True:  return "True"
  if v is False: return "False"
  if v is None:  return "None"
  return repr(v)


def _write_annotated(path, tests, annotations):
  """Write annotated test list to path as a valid Python eval-able file."""
  lines = ["# verified test file — generated by verify_tests.py\n", "\n", "[\n\n"]

  for i, (entry, ann) in enumerate(zip(tests, annotations)):
    text     = entry[0]
    expected = ann.get("new_expected", entry[1])
    goodness = ann.get("goodness", 100)
    alts     = ann.get("alternatives", [])
    comment  = ann.get("comment", "")
    comma    = "," if i < len(tests) - 1 else ""

    # Preserve existing extra fields beyond index 1 if present
    extra = entry[2] if len(entry) > 2 and isinstance(entry[2], dict) else {}

    meta = dict(extra)
    meta["goodness"] = goodness
    if alts:
      meta["alternatives"] = alts
    if comment:
      meta["comment"] = comment

    text_repr = '"""' + text.replace('\\', '\\\\') + '"""' if "\n" in text else repr(text)
    exp_repr  = _repr_expected(expected)

    lines.append("  [" + text_repr + ", " + exp_repr + ", " + json.dumps(meta) + "]" + comma + "\n\n")

  lines.append("]\n")
  with open(path, "w") as f:
    f.writelines(lines)


# ── command-line parsing ───────────────────────────────────────────────────────

def _parse_args():
  args      = sys.argv[1:]
  test_file = None
  out_file  = None
  limit     = 0
  skip      = 0
  think_str = "medium"
  dry_run   = False

  i = 0
  while i < len(args):
    a = args[i]
    if   a == "--limit"    and i + 1 < len(args): limit     = int(args[i+1]); i += 2
    elif a == "--skip"     and i + 1 < len(args): skip      = int(args[i+1]); i += 2
    elif a == "--out"      and i + 1 < len(args): out_file  = args[i+1];      i += 2
    elif a == "--think"    and i + 1 < len(args): think_str = args[i+1];      i += 2
    elif a == "--dry-run":  dry_run  = True;  i += 1
    elif not a.startswith("--"):
      test_file = a; i += 1
    else:
      print(f"Unknown option: {a}"); i += 1

  if not test_file:
    test_file = "tests/tests_core.py"

  if think_str not in ("none", "low", "medium"):
    print(f"Warning: unknown think level '{think_str}', using 'medium'")
    think_str = "medium"

  if out_file is None:
    base, ext = os.path.splitext(test_file)
    out_file = base + "_verified" + ext

  return test_file, out_file, limit, skip, think_str, dry_run


# ── main ───────────────────────────────────────────────────────────────────────

def main():
  test_file, out_file, limit, skip, think_str, dry_run = _parse_args()

  # none=False, low=500 token budget, medium=8000 token budget
  # none=False, low=1024 token budget, medium=8000 token budget
  think = {"none": False, "low": 1024, "medium": 8000}[think_str]

  print(f"Loading tests from: {test_file}")
  tests = _load_tests(test_file)
  print(f"Loaded {len(tests)} tests.")

  start = skip
  end   = (start + limit) if limit else len(tests)
  end   = min(end, len(tests))
  print(f"Processing tests {start+1}–{end}  (think={think_str})")
  print()

  # Annotations list parallel to tests; entries not in [start,end) keep defaults.
  annotations = []
  for i, entry in enumerate(tests):
    if i < start or i >= end:
      # Keep as-is
      ann = {"new_expected": entry[1]}
      if len(entry) > 2 and isinstance(entry[2], dict):
        ann.update(entry[2])
        ann["new_expected"] = entry[1]
      annotations.append(ann)
      continue

    text     = entry[0]
    expected = entry[1]
    exp_disp = _expected_display(expected)

    print(f"[{i+1}/{len(tests)}] {text[:70].strip()}...")
    print(f"  Expected: {exp_disp}")

    responses = _call_all_llms(text, expected, think)
    ann       = _compute_annotation(expected, responses)

    print(f"  Goodness: {ann['goodness']}%  |  {ann['comment']}")
    if ann["alternatives"]:
      print(f"  Alternatives: {ann['alternatives']}")
    if ann["new_expected"] != expected:
      print(f"  >>> Suggested new expected: {_expected_display(ann['new_expected'])}")

    annotations.append(ann)

    if not dry_run:
      _write_annotated(out_file, tests, annotations)

  if dry_run:
    print("\n[dry-run] Output not written.")
  else:
    print(f"\nAnnotated file written to: {out_file}")


if __name__ == "__main__":
  main()
