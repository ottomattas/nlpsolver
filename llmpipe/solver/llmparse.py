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
from stage_sanity import (
  check_stage1 as _check_stage1,
  check_stage2 as _check_stage2,
  format_retry_suffix as _format_retry_suffix,
  issue_fingerprints as _issue_fingerprints,
)

# ======== prompt file configuration ========

# Absolute path to llmpipe/ (parent of this file's directory), so that
# prompt files are found regardless of the working directory at runtime.
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

stage1_instructions_file = os.path.join(_root, "prompts", "stage1_instructions_full.txt")
stage1_examples_file     = os.path.join(_root, "prompts", "stage1_examples.txt")
stage1_checklist_file    = os.path.join(_root, "prompts", "stage1_checklist_full.txt")
stage2_instructions_file = os.path.join(_root, "prompts", "stage2_instructions_full.txt")
stage2_examples_file     = os.path.join(_root, "prompts", "stage2_examples.txt")
stage2_checklist_file    = os.path.join(_root, "prompts", "stage2_checklist_full.txt")

# One-stage experiment prompts (Conditions B/C): small wrappers that reframe the
# task as a single English -> logic-JSON step, prepended to the existing Stage-1
# and Stage-2 specs (reused verbatim as reference knowledge).
onestage_direct_wrapper_file = os.path.join(_root, "prompts", "onestage_direct_wrapper.txt")
onestage_struct_wrapper_file = os.path.join(_root, "prompts", "onestage_struct_wrapper.txt")

# Separator inserted between instructions and examples when building a prompt
examples_separator = "\n\nExamples:\n\n"

# ======== LLM configuration ========

# These are passed through to llmcall.call_llm; None means use llmcall defaults
use_llm   = None   # "gpt" | "claude" | "gemini" | "deepseek" | None
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
_onestage_sysprompt = {}   # {"direct": str, "struct": str}


def load_prompts():
  """Load and compose stage prompts from files. Called automatically on first use."""
  global _stage1_sysprompt, _stage2_sysprompt
  _stage1_sysprompt = _compose_prompt(stage1_instructions_file, stage1_examples_file, "stage1",
                                      checklist_file=stage1_checklist_file)
  _stage2_sysprompt = _compose_prompt(stage2_instructions_file, stage2_examples_file, "stage2",
                                      checklist_file=stage2_checklist_file)


def _read_prompt_file(path, label):
  try:
    with open(path, "r") as f:
      return f.read().strip()
  except Exception as e:
    _print_error("Could not read " + label + " file '" + path + "': " + str(e))
    return ""


def load_onestage_prompt(mode):
  """Compose and cache the one-stage system prompt for mode 'direct' or 'struct'.

  Reuses the existing Stage-1 and Stage-2 specifications and examples verbatim as
  reference knowledge, prefixed by a wrapper (onestage_*_wrapper.txt) that
  redefines the task as a single English -> logic-JSON step.  The baseline
  two-stage prompts are left untouched so Condition A is unaffected.
  """
  wrapper_file = onestage_direct_wrapper_file if mode == "direct" else onestage_struct_wrapper_file
  wrapper  = _read_prompt_file(wrapper_file, "onestage " + mode + " wrapper")
  s1_instr = _read_prompt_file(stage1_instructions_file, "stage1 instructions")
  s2_instr = _read_prompt_file(stage2_instructions_file, "stage2 instructions")
  s1_ex    = _read_prompt_file(stage1_examples_file, "stage1 examples")
  s2_ex    = _read_prompt_file(stage2_examples_file, "stage2 examples")
  s2_check = _read_prompt_file(stage2_checklist_file, "stage2 checklist")
  parts = [
    wrapper,
    "============================================================\n"
    "REFERENCE SPEC 1 - English to Atomic Semantic Units (ASUs)\n"
    "============================================================\n\n" + s1_instr,
    "============================================================\n"
    "REFERENCE SPEC 2 - ASUs to logic JSON (your OUTPUT format)\n"
    "============================================================\n\n" + s2_instr,
    "Reference examples - English to ASUs (the first sub-step):\n\n" + s1_ex,
    "Reference examples - ASUs to logic JSON (the output format):\n\n" + s2_ex,
  ]
  if s2_check:
    parts.append(s2_check)
  _onestage_sysprompt[mode] = "\n\n".join(p for p in parts if p)
  return _onestage_sysprompt[mode]


def _compose_prompt(instructions_file, examples_file, label, checklist_file=None):
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
  checklist = ""
  if checklist_file:
    try:
      with open(checklist_file, "r") as f:
        checklist = f.read().strip()
    except Exception as e:
      _print_error("Could not read " + label + " checklist file '" + checklist_file + "': " + str(e))
  if instructions and examples:
    prompt = instructions + examples_separator + examples
    if checklist:
      prompt = prompt + "\n\n" + checklist
    return prompt
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

  # Input text is already shown by solve.py; no need to repeat here.

  # --- stage 1 ---
  s1_json, s1_raw, s1_err = _run_stage(1, text, _stage1_sysprompt,
                                        eff_llm, eff_version, eff_tokens, eff_think, stats,
                                        check_fn=lambda parsed: _check_stage1(parsed))
  if s1_err:
    _debug_write("STAGE 1 ERROR: " + s1_err)
  else:
    _debug_write("STAGE 1 OK")

  if s1_json is None:
    return (None, None, stats)

  # Normalize entity IDs that differ only by sentence-start capitalization.
  _normalize_entity_id_case(s1_json, stats)

  # --- stage 2 ---
  s2_input = json.dumps(s1_json)
  s2_json, s2_raw, s2_err = _run_stage(2, s2_input, _stage2_sysprompt,
                                        eff_llm, eff_version, eff_tokens, eff_think, stats,
                                        check_fn=lambda parsed: _check_stage2(parsed, s1_json))
  if s2_err:
    _debug_write("STAGE 2 ERROR: " + s2_err)
  else:
    _debug_write("STAGE 2 OK")

  return (s1_json, s2_json, stats)


def parse_text_onestage(text, mode="direct", llm=None, version=None, tokens=None, think=None):
  """One-stage parse: a single LLM call converts English directly to Stage-2
  logic JSON (the experiment ladder's Condition C 'direct' or B 'struct').

  Returns (None, stage2_json, stats).  s1_json is None by design: the
  downstream pipeline (logconvert, prover, procproofs) tolerates s1_json=None,
  losing only cosmetic source-sentence annotations, not answer correctness.

  Stats are recorded under the same s2_* keys as two-stage Stage 2, so the
  single call gets the identical JSON-fix and sanity-retry machinery as the
  baseline (no Stage-1 cross-checks, since there is no Stage-1 output).
  """
  if mode not in ("direct", "struct"):
    _print_error("unknown onestage mode '" + str(mode) + "' (expected 'direct' or 'struct')")
    return (None, None, _make_stats())

  if mode not in _onestage_sysprompt:
    load_onestage_prompt(mode)
  sysprompt = _onestage_sysprompt[mode]

  eff_llm     = llm     or use_llm
  eff_version = version or llm_version
  eff_tokens  = tokens  or max_tokens
  eff_think   = think if think is not None else use_think

  stats = _make_stats()

  s2_json, s2_raw, s2_err = _run_stage(2, text, sysprompt,
                                       eff_llm, eff_version, eff_tokens, eff_think, stats,
                                       check_fn=lambda parsed: _check_stage2(parsed, None))
  if s2_err:
    _debug_write("ONESTAGE (" + mode + ") ERROR: " + s2_err)
  else:
    _debug_write("ONESTAGE (" + mode + ") OK")

  return (None, s2_json, stats)


# ======== stage runner ========

def _run_stage(stage_nr, input_text, sysprompt, llm, version, tokens, think, stats,
               check_fn=None):
  """Run one LLM stage with JSON checking, fixing, and one retry on bad JSON.

  If check_fn is provided, it is called on the successfully-parsed output
  (check_fn(parsed) -> list[Issue]).  When it reports issues a separate
  sanity-retry loop kicks in: the LLM is re-called with the original input
  plus a suffix describing the flawed output and the issues.  At most two
  sanity retries per stage; retry stops early if an issue persists across
  attempts (see _run_sanity_retry).

  Returns (parsed_json, raw_text, error_or_None).
  """
  key = "s" + str(stage_nr)
  stats[key + "_calls"] += 1

  import llmcall as _llmcall
  actual_llm = llm or use_llm or _llmcall.use_llm
  _debug_write("\n=== stage " + str(stage_nr) + " LLM call (" + actual_llm + ") ===\n")
  _debug_write_json("INPUT:", input_text)

  raw = call_llm(sysprompt, input_text, llm=llm, version=version, max_tokens=tokens, think=think)

  if raw is None:
    stats[key + "_llm_errors"] += 1
    return (None, None, "stage " + str(stage_nr) + " LLM call returned None")

  _debug_write_json("RAW OUTPUT:", raw)

  # --- first parse attempt ---
  parsed, err = _try_parse(raw)
  if parsed is not None:
    return _maybe_sanity_retry(stage_nr, input_text, parsed, raw, check_fn,
                               sysprompt, llm, version, tokens, think, stats)

  stats[key + "_json_errors"] += 1
  _debug_write("JSON parse failed: " + err)

  # --- try fixes ---
  fixed, fixes = fix_json(raw)
  if fixes:
    _debug_write("Fixes applied: " + ", ".join(fixes))
    stats[key + "_json_fixes"] += len(fixes)
    _record_fixes(stats, key, fixes)
    parsed, err = _try_parse(fixed)
    if parsed is not None:
      _debug_write("Fixed JSON parsed OK")
      return _maybe_sanity_retry(stage_nr, input_text, parsed, fixed, check_fn,
                                 sysprompt, llm, version, tokens, think, stats)
    _debug_write("Fixed JSON still invalid: " + err)

  # --- LLM retry ---
  stats[key + "_retry_calls"] += 1
  stats[key + "_retries"].append("json-fail retry: " + (err or "parse error")[:60])
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
    return _maybe_sanity_retry(stage_nr, input_text, parsed, raw2, check_fn,
                               sysprompt, llm, version, tokens, think, stats)

  # --- fixes on retry output ---
  fixed2, fixes2 = fix_json(raw2)
  if fixes2:
    _debug_write("Retry fixes applied: " + ", ".join(fixes2))
    stats[key + "_json_fixes"] += len(fixes2)
    _record_fixes(stats, key, fixes2)
    parsed, err = _try_parse(fixed2)
    if parsed is not None:
      stats[key + "_retry_ok"] += 1
      _debug_write("Retry fixed JSON parsed OK")
      return _maybe_sanity_retry(stage_nr, input_text, parsed, fixed2, check_fn,
                                 sysprompt, llm, version, tokens, think, stats)

  stats[key + "_retry_fail"] += 1
  _debug_write("Stage " + str(stage_nr) + " failed after retry: " + err)
  return (None, raw2, "stage " + str(stage_nr) + " JSON invalid after fix and retry: " + err)


# ======== sanity-check retry ========

# Hard cap on total LLM calls per stage for sanity retry (not counting the
# initial call).  Attempt 1 is the first corrective retry; attempt 2 is the
# last.  Beyond that the current best-effort output is returned even if
# issues linger, so the pipeline can proceed.
_SANITY_MAX_RETRIES = 2


def _maybe_sanity_retry(stage_nr, input_text, parsed, raw, check_fn,
                        sysprompt, llm, version, tokens, think, stats):
  """Run the per-stage sanity checker and, if it reports issues, re-call
  the LLM with a corrective prompt.  Returns (parsed, raw, None) — the
  best-effort output regardless of whether the issues were fully fixed
  (the pipeline continues with imperfect output rather than aborting).
  """
  if check_fn is None:
    return (parsed, raw, None)

  key = "s" + str(stage_nr)
  try:
    issues = check_fn(parsed)
  except Exception as e:
    _debug_write("Sanity checker raised exception: " + str(e))
    return (parsed, raw, None)

  if not issues:
    return (parsed, raw, None)

  # Track issue fingerprints across attempts to detect persistence.
  prev_fingerprints = _issue_fingerprints(issues)
  current_parsed, current_raw = parsed, raw
  current_issues = issues

  for attempt in range(1, _SANITY_MAX_RETRIES + 1):
    stats[key + "_sanity_retries"] += 1
    _debug_write("Stage " + str(stage_nr) + " sanity retry #" + str(attempt)
                 + " with " + str(len(current_issues)) + " issue(s)")
    # Record a short message summarising why the retry fired: the issue KINDS
    # only (descriptions are long and live in the corrective prompt / debug log).
    kinds = [(getattr(it, "kind", "") or "issue") for it in current_issues]
    stats[key + "_retries"].append("sanity #" + str(attempt) + ": " + ", ".join(kinds))
    suffix = _format_retry_suffix(current_issues, current_parsed)
    retry_input = input_text + suffix

    raw_new = call_llm(sysprompt, retry_input,
                       llm=llm, version=version, max_tokens=tokens, think=think)
    if raw_new is None:
      stats[key + "_sanity_fail"] += 1
      _debug_write("Stage " + str(stage_nr) + " sanity retry #" + str(attempt)
                   + " LLM returned None; stopping")
      break
    _debug_write_json("SANITY RETRY #" + str(attempt) + " OUTPUT:", raw_new)

    # Parse + JSON-fix fallback (mirrors the _run_stage primary path).
    parsed_new, perr = _try_parse(raw_new)
    raw_final = raw_new
    if parsed_new is None:
      fixed_new, fixes_new = fix_json(raw_new)
      if fixes_new:
        stats[key + "_json_fixes"] += len(fixes_new)
        _record_fixes(stats, key, fixes_new)
        parsed_new, perr = _try_parse(fixed_new)
        if parsed_new is not None:
          raw_final = fixed_new

    if parsed_new is None:
      stats[key + "_sanity_fail"] += 1
      _debug_write("Stage " + str(stage_nr) + " sanity retry #" + str(attempt)
                   + " JSON invalid: " + perr + "; stopping")
      break

    current_parsed, current_raw = parsed_new, raw_final

    try:
      new_issues = check_fn(parsed_new)
    except Exception as e:
      _debug_write("Sanity checker raised exception on retry: " + str(e))
      break

    if not new_issues:
      stats[key + "_sanity_ok"] += 1
      _debug_write("Stage " + str(stage_nr) + " sanity retry #" + str(attempt)
                   + " produced clean output")
      return (current_parsed, current_raw, None)

    new_fingerprints = _issue_fingerprints(new_issues)
    # Persistence: any issue from the previous attempt still present → stop.
    if new_fingerprints & prev_fingerprints:
      stats[key + "_sanity_fail"] += 1
      _debug_write("Stage " + str(stage_nr) + " sanity retry #" + str(attempt)
                   + " — issue(s) persist across attempts; stopping")
      break

    # All-new issues: try once more (if cap not reached).
    prev_fingerprints = new_fingerprints
    current_issues = new_issues

  # Out of retries or stopped on persistence.  Return the best-effort output;
  # downstream passes handle residual imperfections (or the query fails in
  # ways we already recognise).
  return (current_parsed, current_raw, None)


# ======== JSON fixing ========

def fix_json(s):
  """Attempt to repair common JSON errors in LLM output.

  Returns (fixed_string, list_of_fix_names) where list_of_fix_names is
  non-empty if any fix was applied and the result is valid JSON, or
  (best_attempt, None) if all fixes failed.
  """
  s = s.strip()
  applied = []

  # 0. Strip preamble text before JSON (e.g. LLM planning/reasoning output)
  if not s.startswith(("```", "[", "{")):
    fence = re.search(r'^```(?:json)?\s*$', s, re.MULTILINE)
    if fence:
      s = s[fence.start():]
      applied.append("stripped preamble before fence")
    else:
      m = re.search(r'^[\[{]', s, re.MULTILINE)
      if m:
        s = s[m.start():]
        applied.append("stripped preamble before JSON")
  if _ok(s): return (s, applied or None)

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

  # 7a. Quote bare Stage-2-style variable identifiers in JSON array context.
  # Some LLMs (notably gpt) emit ["ask","X",[..., ["=", ..., X]]] where the
  # interior X is left as a bare identifier instead of "X".  The bare token
  # only appears in array element positions (between [/, on the left and
  # ,/] on the right), and is a single uppercase letter optionally followed
  # by digits (Stage-2 variable convention: X, Y, E, S1, ...).  Quoting it
  # leaves quoted strings unchanged because the lookbehind requires [ or ,.
  s2 = re.sub(r'(?<=[\[,])(\s*)([A-Z][0-9]*)(\s*)(?=[,\]])', r'\1"\2"\3', s)
  if s2 != s:
    s = s2
    applied.append("quoted bare variable identifiers")
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


# ======== entity ID case normalization ========

import re as _re

_ID_WITH_NUMBER_RE = _re.compile(r'^(.+)\s+(\d+)$')

def _normalize_entity_id_case(s1_json, stats=None):
  """Normalize entity IDs that differ only by sentence-start capitalization.

  When the same entity appears as "Car 1" (sentence start) and "car 1"
  (mid-sentence), replace the capitalized form with the lowercase form.

  Only fires when ALL conditions hold:
    (a) Two IDs differ only in the first character's case, rest identical
    (b) The ID contains a number suffix (e.g., "Car 1", not bare "Car")
    (c) The capitalized form appears as the first word of a raw sentence

  Modifies s1_json in place.
  """
  if not isinstance(s1_json, list):
    return

  # Collect all entity IDs and raw sentence texts.
  all_ids = set()
  raw_sentences = []
  for pkg in s1_json:
    if not isinstance(pkg, dict):
      continue
    raw = pkg.get("raw", "")
    if raw:
      raw_sentences.append(raw)
    for unit in pkg.get("units", []):
      for ent in unit.get("entities", []):
        eid = ent.get("id")
        if isinstance(eid, str):
          all_ids.add(eid)

  # Find pairs differing only by first-char case.
  replacements = {}  # capitalized_id → lowercase_id
  for eid in all_ids:
    if not eid or not eid[0].isupper():
      continue
    m = _ID_WITH_NUMBER_RE.match(eid)
    if not m:
      continue  # condition (b): must have number
    lower_form = eid[0].lower() + eid[1:]
    if lower_form not in all_ids:
      continue  # condition (a): lowercase form must exist
    # condition (c): capitalized form must be first word of a raw sentence
    first_word = eid.split()[0]  # e.g., "Car"
    is_sentence_start = any(r.startswith(first_word + " ") or r.startswith(first_word + "'")
                            for r in raw_sentences)
    if is_sentence_start:
      replacements[eid] = lower_form

  if not replacements:
    return

  # Apply replacements throughout all entities, definites, actions, etc.
  _replace_ids_in_s1(s1_json, replacements)
  if stats is not None:
    stats["s1_fixes"].append("entity-id case normalized")


def _replace_ids_in_s1(obj, replacements):
  """Recursively replace entity ID strings in Stage 1 JSON."""
  if isinstance(obj, dict):
    for key in obj:
      val = obj[key]
      if isinstance(val, str) and val in replacements:
        obj[key] = replacements[val]
      elif isinstance(val, (dict, list)):
        _replace_ids_in_s1(val, replacements)
  elif isinstance(obj, list):
    for i, val in enumerate(obj):
      if isinstance(val, str) and val in replacements:
        obj[i] = replacements[val]
      elif isinstance(val, (dict, list)):
        _replace_ids_in_s1(val, replacements)


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
    "s1_sanity_retries", "s1_sanity_ok", "s1_sanity_fail",
    "s2_calls", "s2_llm_errors", "s2_json_errors", "s2_json_fixes",
    "s2_retry_calls", "s2_retry_ok", "s2_retry_fail",
    "s2_sanity_retries", "s2_sanity_ok", "s2_sanity_fail",
  ]
  d = {k: 0 for k in keys}
  # Detail lists for runtests: fix names actually applied and retry messages.
  # "stripped markdown fence" is excluded from fix lists per spec.
  d["s1_fixes"] = []
  d["s2_fixes"] = []
  d["s1_retries"] = []
  d["s2_retries"] = []
  return d


# Cosmetic wrapper-stripping fixes that are NOT registered (LLM-output noise,
# not a structural repair): the markdown fence and the preamble before the JSON
# header.  Everything else from fix_json IS registered (prefixed "json: ").
_SKIP_FIX_NAMES = {
    "stripped markdown fence",
    "stripped preamble before fence",
    "stripped preamble before JSON",
}


def _record_fixes(stats, key, fixes):
  """Append non-skipped JSON fix names (prefixed "json: ") to the stage's
  fix list.  All fixes here originate from fix_json (JSON-syntax repairs)."""
  if not fixes:
    return
  for f in fixes:
    if f not in _SKIP_FIX_NAMES:
      stats[key + "_fixes"].append("json: " + f)


def print_stats(stats):
  """Print a human-readable summary of parse stats."""
  print("Parse stats:")
  print("  Stage 1: calls={s1_calls}  llm_errors={s1_llm_errors}"
        "  json_errors={s1_json_errors}  fixes={s1_json_fixes}"
        "  retries={s1_retry_calls}  retry_ok={s1_retry_ok}  retry_fail={s1_retry_fail}"
        "  sanity_retries={s1_sanity_retries}  sanity_ok={s1_sanity_ok}  sanity_fail={s1_sanity_fail}".format(**stats))
  print("  Stage 2: calls={s2_calls}  llm_errors={s2_llm_errors}"
        "  json_errors={s2_json_errors}  fixes={s2_json_fixes}"
        "  retries={s2_retry_calls}  retry_ok={s2_retry_ok}  retry_fail={s2_retry_fail}"
        "  sanity_retries={s2_sanity_retries}  sanity_ok={s2_sanity_ok}  sanity_fail={s2_sanity_fail}".format(**stats))


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
