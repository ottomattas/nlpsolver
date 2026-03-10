# Two-stage LLM parser: English -> Stage-1 ASUs -> Stage-2 logic.
#
# Primary entry point: parse_text(text)
# Returns (stage1_json, stage2_json, stats).
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

import sys
import os
import json
import re

# llmcall.py must be importable (run from the llmpipe/ working directory)
from llmcall import call_llm
import pretty

# ======== prompt file configuration ========

# Absolute path to llmpipe/ (parent of this file's directory), so that
# prompt files are found regardless of the working directory at runtime.
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

stage1_instructions_file = os.path.join(_root, "prompts", "stage1_instructions.txt")
stage1_examples_file     = os.path.join(_root, "prompts", "stage1_examples.txt")
stage2_instructions_file = os.path.join(_root, "prompts", "stage2_instructions.txt")
stage2_examples_file     = os.path.join(_root, "prompts", "stage2_examples.txt")

# Separator inserted between instructions and examples when building a prompt
examples_separator = "\n\nExamples:\n\n"

# ======== LLM configuration ========

# These are passed through to llmcall.call_llm; None means use llmcall defaults
use_llm   = None   # "gpt" | "claude" | "gemini" | None
llm_version = None # model version string, or None for llmcall default
max_tokens  = None # int, or None for llmcall default
use_think   = False # True to enable medium reasoning/thinking mode

# ======== debug / logging configuration ========

debug = False          # print stage inputs, outputs and fix details to stdout
debug_file = None      # path to append debug log to, or None to disable
                       # e.g. debug_file = "llmparse_debug.log"

# ======== module-level prompt cache ========

_stage1_sysprompt = None
_stage2_sysprompt = None


def load_prompts():
  """Load and compose stage prompts from files. Called automatically on first use."""
  global _stage1_sysprompt, _stage2_sysprompt
  _stage1_sysprompt = _compose_prompt(stage1_instructions_file, stage1_examples_file, "stage1")
  _stage2_sysprompt = _compose_prompt(stage2_instructions_file, stage2_examples_file, "stage2")


def _compose_prompt(instructions_file, examples_file, label):
  try:
    with open(instructions_file, "r") as f:
      instructions = f.read().strip()
  except Exception as e:
    _print_error("Could not read " + label + " instructions file '" + instructions_file + "': " + str(e))
    instructions = ""
  try:
    with open(examples_file, "r") as f:
      examples = f.read().strip()
  except Exception as e:
    _print_error("Could not read " + label + " examples file '" + examples_file + "': " + str(e))
    examples = ""
  if instructions and examples:
    return instructions + examples_separator + examples
  return instructions or examples


# ======== main entry point ========

def parse_text(text, llm=None, version=None, tokens=None, think=None):
  """Parse English text through stage 1 (ASUs) then stage 2 (logic).

  Optional llm/version/tokens/think override the module-level defaults.

  Returns (stage1_json, stage2_json, stats) where:
    - stage1_json is the parsed Stage-1 JSON object, or None on failure.
    - stage2_json is the parsed Stage-2 JSON object, or None on failure.
    - stats is a dict of error/retry counts (printable via print_stats).
  """
  global _stage1_sysprompt, _stage2_sysprompt
  if _stage1_sysprompt is None:
    load_prompts()

  eff_llm     = llm     or use_llm
  eff_version = version or llm_version
  eff_tokens  = tokens  or max_tokens
  eff_think   = think if think is not None else use_think

  stats = _make_stats()

  _debug_write("\n"+"="*30 + " llmparse " + "="*30+"\n")
  _debug_write("INPUT: " + text)

  # --- stage 1 ---
  s1_json, s1_raw, s1_err = _run_stage(1, text, _stage1_sysprompt,
                                        eff_llm, eff_version, eff_tokens, eff_think, stats)
  if s1_err:
    _debug_write("STAGE 1 ERROR: " + s1_err)
  else:
    _debug_write("STAGE 1 OK")

  if s1_json is None:
    return (None, None, stats)

  # --- stage 2 ---
  s2_input = json.dumps(s1_json)
  s2_json, s2_raw, s2_err = _run_stage(2, s2_input, _stage2_sysprompt,
                                        eff_llm, eff_version, eff_tokens, eff_think, stats)
  if s2_err:
    _debug_write("STAGE 2 ERROR: " + s2_err)
  else:
    _debug_write("STAGE 2 OK")

  return (s1_json, s2_json, stats)


# ======== stage runner ========

def _run_stage(stage_nr, input_text, sysprompt, llm, version, tokens, think, stats):
  """Run one LLM stage with JSON checking, fixing, and one retry on bad JSON.

  Returns (parsed_json, raw_text, error_or_None).
  """
  key = "s" + str(stage_nr)
  stats[key + "_calls"] += 1

  _debug_write("\n--- Stage " + str(stage_nr) + " call ---")
  _debug_write_json("INPUT:", input_text)

  raw = call_llm(sysprompt, input_text, llm=llm, version=version, max_tokens=tokens, think=think)

  if raw is None:
    stats[key + "_llm_errors"] += 1
    return (None, None, "stage " + str(stage_nr) + " LLM call returned None")

  _debug_write_json("RAW OUTPUT:", raw)

  # --- first parse attempt ---
  parsed, err = _try_parse(raw)
  if parsed is not None:
    return (parsed, raw, None)

  stats[key + "_json_errors"] += 1
  _debug_write("JSON parse failed: " + err)

  # --- try fixes ---
  fixed, fixes = fix_json(raw)
  if fixes:
    _debug_write("Fixes applied: " + ", ".join(fixes))
    stats[key + "_json_fixes"] += len(fixes)
    parsed, err = _try_parse(fixed)
    if parsed is not None:
      _debug_write("Fixed JSON parsed OK")
      return (parsed, fixed, None)
    _debug_write("Fixed JSON still invalid: " + err)

  # --- LLM retry ---
  stats[key + "_retry_calls"] += 1
  retry_input = _build_retry_prompt(input_text, raw)
  _debug_write("Retrying stage " + str(stage_nr) + " with error feedback...")

  raw2 = call_llm(sysprompt, retry_input, llm=llm, version=version, max_tokens=tokens, think=think)

  if raw2 is None:
    stats[key + "_llm_errors"] += 1
    stats[key + "_retry_fail"] += 1
    return (None, raw, "stage " + str(stage_nr) + " retry LLM call returned None")

  _debug_write_json("RETRY OUTPUT:", raw2)

  parsed, err = _try_parse(raw2)
  if parsed is not None:
    stats[key + "_retry_ok"] += 1
    return (parsed, raw2, None)

  # --- fixes on retry output ---
  fixed2, fixes2 = fix_json(raw2)
  if fixes2:
    _debug_write("Retry fixes applied: " + ", ".join(fixes2))
    stats[key + "_json_fixes"] += len(fixes2)
    parsed, err = _try_parse(fixed2)
    if parsed is not None:
      stats[key + "_retry_ok"] += 1
      _debug_write("Retry fixed JSON parsed OK")
      return (parsed, fixed2, None)

  stats[key + "_retry_fail"] += 1
  _debug_write("Stage " + str(stage_nr) + " failed after retry: " + err)
  return (None, raw2, "stage " + str(stage_nr) + " JSON invalid after fix and retry: " + err)


# ======== JSON fixing ========

def fix_json(s):
  """Attempt to repair common JSON errors in LLM output.

  Returns (fixed_string, list_of_fix_names) where list_of_fix_names is
  non-empty if any fix was applied and the result is valid JSON, or
  (best_attempt, None) if all fixes failed.
  """
  s = s.strip()
  applied = []

  # 1. Strip markdown code fences (```json...``` or ```...```)
  if s.startswith("```"):
    lines = s.splitlines()
    if lines[0].startswith("```"):
      lines = lines[1:]
    if lines and lines[-1].strip() == "```":
      lines = lines[:-1]
    s = "\n".join(lines).strip()
    applied.append("stripped markdown fence")
  if _ok(s): return (s, applied or None)

  # 2. Remove null / None values appearing as bare array elements
  s2 = s
  for pattern, repl in [
    (r",\s*null\s*(?=[\],])", ""),
    (r"(?<=[\[,])\s*null\s*,", ""),
    (r",\s*None\s*(?=[\],])", ""),
    (r"(?<=[\[,])\s*None\s*,", ""),
  ]:
    s2 = re.sub(pattern, repl, s2)
  if s2 != s:
    s = s2
    applied.append("removed null/None elements")
  if _ok(s): return (s, applied or None)

  # 3. Replace Python literals: True/False/None -> true/false/null
  s2 = re.sub(r'\bTrue\b', 'true', re.sub(r'\bFalse\b', 'false',
              re.sub(r'\bNone\b', 'null', s)))
  if s2 != s:
    s = s2
    applied.append("replaced Python literals")
  if _ok(s): return (s, applied or None)

  # 4. Strip any leading/trailing non-JSON text (keep from first [ or { to last ] or })
  m = re.search(r'[\[{]', s)
  if m:
    start = m.start()
    # find matching end from the right
    end = max(s.rfind("]"), s.rfind("}"))
    if end > start:
      s2 = s[start:end + 1]
      if s2 != s:
        s = s2
        applied.append("stripped non-JSON wrapper text")
  if _ok(s): return (s, applied or None)

  # 5. Add missing commas between adjacent array/object elements (] [ and } {)
  s2 = re.sub(r'\]\s*\[', '], [', s)
  s2 = re.sub(r'\}\s*\{', '}, {', s2)
  if s2 != s:
    s = s2
    applied.append("added missing commas between adjacent elements")
  if _ok(s): return (s, applied or None)

  # 6. Remove trailing commas before ] or }
  s2 = re.sub(r',\s*([\]}])', r'\1', s)
  if s2 != s:
    s = s2
    applied.append("removed trailing commas")
  if _ok(s): return (s, applied or None)

  # 7. Fix ]"] -> ]] (a specific bracket-quote-bracket glitch)
  if ']"]' in s:
    s2 = s.replace(']"]', ']]')
    if s2 != s:
      s = s2
      applied.append('fixed ]\"][ glitch')
  if _ok(s): return (s, applied or None)

  # 8. Remove junk after the top-level closing bracket (fix_internal)
  s2 = _fix_internal(s)
  if s2 != s:
    s = s2
    applied.append("removed content after top-level close bracket")
  if _ok(s): return (s, applied or None)

  # 9. Balance square brackets
  opens  = s.count("[")
  closes = s.count("]")
  if opens > closes:
    s = s + "]" * (opens - closes)
    applied.append("added " + str(opens - closes) + " closing bracket(s)")
  elif closes > opens:
    excess = closes - opens
    # trim from the right
    tmp = s
    while excess > 0 and tmp.endswith("]"):
      tmp = tmp[:-1]
      excess -= 1
    if tmp != s:
      s = tmp
      applied.append("removed " + str(closes - opens) + " excess closing bracket(s)")
  if _ok(s): return (s, applied or None)

  # 10. Re-apply fix_internal after bracket balance (may expose new top-level junk)
  s2 = _fix_internal(s)
  if s2 != s:
    s = s2
    applied.append("fix_internal pass 2")
    opens  = s.count("[")
    closes = s.count("]")
    if opens > closes:
      s = s + "]" * (opens - closes)
      applied.append("re-balanced brackets after fix_internal pass 2")
  if _ok(s): return (s, applied or None)

  return (s, None)


def _fix_internal(s):
  """Recursively remove content that appears after the top-level closing bracket.

  Handles cases like  [...][...] or [...] "trailing text"  produced by LLMs.
  """
  in_quotes = False
  depth = 0
  for i, c in enumerate(s):
    if c == '"' and not in_quotes:
      in_quotes = True
      continue
    if c == '"' and in_quotes:
      in_quotes = False
      continue
    if in_quotes:
      continue
    if c == "[":
      depth += 1
    elif c == "]":
      depth -= 1
      if depth == 0 and i < len(s) - 1 and s[i + 1:].strip():
        # There is non-whitespace after the closing bracket: remove it and recurse
        return _fix_internal(s[:i] + s[i + 1:])
  return s


def _ok(s):
  """Return True if s is valid JSON."""
  try:
    json.loads(s)
    return True
  except:
    return False


def _try_parse(s):
  """Try json.loads; return (obj, None) on success or (None, error_str) on failure."""
  try:
    return (json.loads(s), None)
  except Exception as e:
    return (None, str(e))


# ======== retry prompt ========

def _build_retry_prompt(original_input, bad_output):
  return (
    "The output you produced is not valid JSON. "
    "Please try again and output ONLY valid JSON, with no additional text.\n\n"
    "Original input:\n" + original_input + "\n\n"
    "Your invalid output:\n" + bad_output
  )


# ======== stats ========

def _make_stats():
  keys = [
    "s1_calls", "s1_llm_errors", "s1_json_errors", "s1_json_fixes",
    "s1_retry_calls", "s1_retry_ok", "s1_retry_fail",
    "s2_calls", "s2_llm_errors", "s2_json_errors", "s2_json_fixes",
    "s2_retry_calls", "s2_retry_ok", "s2_retry_fail",
  ]
  return {k: 0 for k in keys}


def print_stats(stats):
  """Print a human-readable summary of parse stats."""
  print("Parse stats:")
  print("  Stage 1: calls={s1_calls}  llm_errors={s1_llm_errors}"
        "  json_errors={s1_json_errors}  fixes={s1_json_fixes}"
        "  retries={s1_retry_calls}  retry_ok={s1_retry_ok}  retry_fail={s1_retry_fail}".format(**stats))
  print("  Stage 2: calls={s2_calls}  llm_errors={s2_llm_errors}"
        "  json_errors={s2_json_errors}  fixes={s2_json_fixes}"
        "  retries={s2_retry_calls}  retry_ok={s2_retry_ok}  retry_fail={s2_retry_fail}".format(**stats))


def add_stats(total, delta):
  """Accumulate delta into total stats dict (for multi-text runs)."""
  for k in total:
    total[k] += delta.get(k, 0)
  return total


# ======== debug helpers ========

def _debug_write(msg):
  if debug:
    print(msg)
  if debug_file:
    try:
      with open(debug_file, "a") as f:
        f.write(msg + "\n")
    except Exception as e:
      print("Could not write to debug file:", e)


def _debug_write_json(label, text):
  """Write label + text to the debug output.  If text is valid JSON, pretty-print it."""
  try:
    obj = json.loads(text)
    msg = label + "\n" + pretty.pp_str(obj)
  except Exception:
    msg = label + "\n" + text
  _debug_write(msg)


def _print_error(msg):
  print("llmparse error:", msg)


# =========== the end ==========
