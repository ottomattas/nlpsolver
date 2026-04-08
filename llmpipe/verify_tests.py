#!/usr/bin/env python3
"""
verify_tests.py  --  collect LLM answers for an nlpsolver test file.

For each test [text, expected] the configured LLMs are asked (with thinking
enabled) what the correct answer is.  The result is appended as a dict
{"llm_name": answer, ...} to each test entry and flushed immediately.

Usage:
  python3 verify_tests.py [tests/tests_core.py] [options]

Options:
  --out FILE          write annotated output to FILE
                      (default: <input_stem>_verified.py in the same directory)
  --limit N           process only the first N tests  (default: all)
  --skip N            skip the first N tests           (default: 0)
  --llms LIST         comma-separated LLM names to use (default: gpt,claude,gemini)
  --think LEVEL       reasoning level: none | low | medium  (default: medium)
  --dry-run           print results but do not write output file

Output format: each test entry becomes [text, expected, llm_answers_dict] where
llm_answers_dict maps LLM names to their proposed answers.
If an entry already has a third element (dict with LLM keys), existing answers
are preserved and only missing LLMs are queried.
test.py only reads entry[0] and entry[1], so the third element is ignored there.
"""

import sys
import os
import json
import re
import threading

# Allow importing from solver/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "solver"))

import llmcall
import globals as _globals
import cache as _cache_mod

# ── LLM versions used for verification ────────────────────────────────────────
LLM_VERSIONS = {
  "gpt":      "gpt-5.1",
  "claude":   "claude-sonnet-4-6",
  "gemini":   "gemini-2.5-flash-lite",
  "deepseek": "deepseek-chat",
}

# ── prompt ────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are an expert in logical reasoning and natural language understanding.
You will be given a short logical reasoning problem: a few sentences followed
by a question.  Your job is to determine the correct answer based ONLY on the
information given.

Rules:
- For yes/no questions: answer "True.", "False.", or "Unknown."
  (Unknown = cannot be determined from the given information alone.)
  Use confidence-qualified variants like "Probably true." or "Likely false."
  when the premises use words like "most", "probably", "normally" etc.
- For who/what/where/when/which questions: answer with the entity name(s)
  ending in ".", e.g. "John.", "John and Mary.", "In the house.", "On Monday."
  Answer "Unknown." if the answer cannot be determined.
- Use ONLY the information explicitly stated. Do not add world knowledge.
  If a fact is not stated or derivable, the answer is "Unknown."
- Treat each problem independently.

Respond ONLY with a single JSON object, no markdown fences, no extra text:
{
  "answer": "your answer here",
  "alternatives": []
}

"answer": your answer to the question (a string like "True.", "False.",
  "Unknown.", "John.", "In the house.", etc.)
"alternatives": list of up to 3 alternative answers that could also be
  correct under different reasonable interpretations. Empty list if none.
"""


def _expected_display(expected):
  if expected is None:  return "Unknown."
  if expected is True:  return "True."
  if expected is False: return "False."
  if isinstance(expected, list):
    return " or ".join(str(e) for e in expected)
  return str(expected)


def _make_user_prompt(text):
  return "Problem:\n" + text.strip()


# ── LLM calls ─────────────────────────────────────────────────────────────────

def _call_llm_for_answer(llm, version, text, think):
  """Call one LLM and return the raw string result."""
  user = _make_user_prompt(text)
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


def _extract_answer(resp):
  """Extract the answer from a parsed LLM response dict.
  Returns a string if no alternatives, or a list [answer, alt1, alt2, ...]
  if alternatives are present.  Handles missing fields gracefully."""
  if resp is None:
    return "Error"
  answer = resp.get("answer")
  alts = [str(a) for a in (resp.get("alternatives") or []) if a]
  if answer is not None:
    answer = str(answer)
    # Deduplicate: drop alts that repeat the primary answer
    alts = [a for a in alts if a != answer]
    if alts:
      return [answer] + alts
    return answer
  # No "answer" key — use alternatives if available
  if alts:
    if len(alts) == 1:
      return alts[0]
    return alts
  return "Error"


def _call_llms(text, think, llm_names):
  """Call specified LLMs in parallel.  Returns dict {name: answer_string_or_list}."""
  results = {}
  lock = threading.Lock()

  def _worker(name):
    try:
      version = LLM_VERSIONS.get(name, name)
      raw = _call_llm_for_answer(name, version, text, think)
      resp = _parse_response(raw)
      answer = _extract_answer(resp)
    except Exception as e:
      answer = "Error"
      print(f"  {name}: error — {e}")
    with lock:
      results[name] = answer

  threads = [threading.Thread(target=_worker, args=(name,)) for name in llm_names]
  for t in threads: t.start()
  for t in threads: t.join()
  return results


# ── test file I/O ──────────────────────────────────────────────────────────────

def _load_tests(path):
  """Load test file via eval() — same approach as test.py."""
  with open(path) as f:
    src = f.read()
  tests = eval(src)
  if not isinstance(tests, list):
    raise ValueError("Test file does not contain a list.")
  return tests


def _repr_value(v):
  if v is True:  return "True"
  if v is False: return "False"
  if v is None:  return "None"
  return repr(v)


def _write_output(path, tests):
  """Write test list to path as a valid Python eval-able file.
  Flushes after each call so partial results survive interruption."""
  lines = ["# verified test file — generated by verify_tests.py\n", "\n", "[\n\n"]

  for i, entry in enumerate(tests):
    text     = entry[0]
    expected = entry[1]
    comma    = "," if i < len(tests) - 1 else ""

    text_repr = '"""' + text.replace('\\', '\\\\') + '"""' if "\n" in text else repr(text)
    exp_repr  = _repr_value(expected)

    if len(entry) > 2:
      extra = entry[2]
      if isinstance(extra, dict):
        extra_repr = json.dumps(extra, ensure_ascii=False)
      elif isinstance(extra, list):
        # Preserve existing list flags like ["default"], ["nochange"]
        extra_repr = repr(extra)
      else:
        extra_repr = repr(extra)
      lines.append("  [" + text_repr + ", " + exp_repr + ", " + extra_repr + "]" + comma + "\n\n")
    else:
      lines.append("  [" + text_repr + ", " + exp_repr + "]" + comma + "\n\n")

  lines.append("]\n")
  with open(path, "w") as f:
    f.writelines(lines)
    f.flush()
    os.fsync(f.fileno())


# ── command-line parsing ───────────────────────────────────────────────────────

def _parse_args():
  args      = sys.argv[1:]
  test_file = None
  out_file  = None
  limit     = 0
  skip      = 0
  think_str = "medium"
  llms_str  = "gpt,claude,gemini,deepseek"
  dry_run   = False

  i = 0
  while i < len(args):
    a = args[i]
    if   a == "--limit"    and i + 1 < len(args): limit     = int(args[i+1]); i += 2
    elif a == "--skip"     and i + 1 < len(args): skip      = int(args[i+1]); i += 2
    elif a == "--out"      and i + 1 < len(args): out_file  = args[i+1];      i += 2
    elif a == "--think"    and i + 1 < len(args): think_str = args[i+1];      i += 2
    elif a == "--think-medium": think_str = "medium"; i += 1
    elif a == "--llms"     and i + 1 < len(args): llms_str  = args[i+1];      i += 2
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

  llm_names = [s.strip() for s in llms_str.split(",") if s.strip()]

  return test_file, out_file, limit, skip, think_str, llm_names, dry_run


# ── main ───────────────────────────────────────────────────────────────────────

def main():
  test_file, out_file, limit, skip, think_str, llm_names, dry_run = _parse_args()

  # none=False, low=1024 token budget, medium=8000 token budget
  think = {"none": False, "low": 1024, "medium": 8000}[think_str]

  print(f"Loading tests from: {test_file}")
  tests = _load_tests(test_file)
  print(f"Loaded {len(tests)} tests.")
  print(f"LLMs: {', '.join(llm_names)}")

  # Merge existing annotations from output file if it exists
  if not dry_run and os.path.exists(out_file):
    try:
      prev = _load_tests(out_file)
      if len(prev) == len(tests):
        merged = 0
        for j, pentry in enumerate(prev):
          if len(pentry) > 2 and isinstance(pentry[2], dict):
            # Carry over LLM answers into the working list
            if len(tests[j]) > 2 and isinstance(tests[j][2], dict):
              tests[j][2].update(pentry[2])
            else:
              tests[j] = [tests[j][0], tests[j][1], dict(pentry[2])]
            merged += 1
        if merged:
          print(f"Merged {merged} existing annotations from: {out_file}")
    except Exception:
      pass  # output file corrupt or incompatible — start fresh

  start = skip
  end   = (start + limit) if limit else len(tests)
  end   = min(end, len(tests))
  print(f"Processing tests {start+1}–{end}  (think={think_str})")
  print()

  for i in range(start, end):
    try:
      entry    = tests[i]
      text     = entry[0]
      expected = entry[1]

      # Get or create the LLM answers dict (third element)
      if len(entry) > 2 and isinstance(entry[2], dict):
        llm_answers = entry[2]
      else:
        llm_answers = {}

      # Determine which LLMs still need to be queried
      missing = [name for name in llm_names if name not in llm_answers]

      if not missing:
        print(f"[{i+1}/{len(tests)}] Already complete, skipping.")
        continue

      exp_disp = _expected_display(expected)
      print(f"[{i+1}/{len(tests)}] {text[:70].strip()}...")
      print(f"  Expected: {exp_disp}")

      new_answers = _call_llms(text, think, missing)
      llm_answers.update(new_answers)

      # Print collected answers
      for name in llm_names:
        ans = llm_answers.get(name, "?")
        if isinstance(ans, list):
          primary = ans[0]
          alts = ans[1:]
          marker = " ✓" if primary == exp_disp else ""
          print(f"  {name}: {primary}{marker}  (also: {', '.join(alts)})")
        else:
          marker = " ✓" if ans == exp_disp else ""
          print(f"  {name}: {ans}{marker}")

      # Update the test entry in place
      if len(entry) > 2 and isinstance(entry[2], dict):
        entry[2] = llm_answers
      elif len(entry) > 2:
        tests[i] = [text, expected, llm_answers]
      else:
        tests[i] = [text, expected, llm_answers]

      # Flush immediately
      if not dry_run:
        _write_output(out_file, tests)

      print()

    except Exception as e:
      print(f"[{i+1}/{len(tests)}] ERROR: {e}")
      print()

  if dry_run:
    print("\n[dry-run] Output not written.")
  else:
    print(f"\nAnnotated file written to: {out_file}")


if __name__ == "__main__":
  main()
