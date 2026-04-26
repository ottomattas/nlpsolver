#!/usr/bin/env python3

# Test runner for the LLM-based nlpsolver pipeline.
#
# Loads one or more test files (Python list literals of [input, expected] pairs),
# runs each input through english_to_answer(), compares the result to the
# expected value, and reports a summary.
#
# Default test file: tests/tests_core.py
# Run with -help to see all options.
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

import re
import sys
import time

sys.path.insert(0, './solver')
from solve import english_to_answer
import solve as _solve_mod


def _print(*args, **kwargs):
  """Print to stdout and, if a log file is open, also write there (flushed)."""
  print(*args, **kwargs)
  _log_write(*args, **kwargs)

def _log_write(*args, **kwargs):
  """Write to the log file only (no console output). Flushed after every call."""
  if _log_fh is not None:
    end = kwargs.get("end", "\n")
    sep = kwargs.get("sep", " ")
    line = sep.join(str(a) for a in args) + end
    _log_fh.write(line)
    _log_fh.flush()

# ======== defaults ========

# Default test file used when no files are given on the command line.
default_test_file = "tests/tests_core.py"

# ======== configuration (overridable via command line) ========

# Output verbosity: exactly one of these will be True after _parse_cmd_line().
#   verbose : print Input / Expected / Received for every test  (default)
#   compact : print a single "." (pass) or "F" (fail) character per test
#   quiet   : no per-test output at all; only the final summary
show_verbose = True
show_compact = False
show_quiet   = False

# When True, print only the tests that failed (skip the passing ones).
show_failures_only = False

# When True, stop the run immediately after the first failure.
stop_on_fail = False

# Run at most this many tests per file (0 = unlimited).
limit = 0

# Skip this many tests at the start of each file (0 = no skip).
skip = 0

# When set, only run tests whose input text contains this substring.
filter_pattern = None

# When True, do not accept answers that contain confidence qualifiers "(…)".
strict_confidences = False

# When True, spatial prepositions must match exactly between expected and received.
# When False (default), a leading preposition on one side but not the other is OK
# (e.g. "Estonia" and "in Estonia" are treated as equivalent).
# Comparison is always case-insensitive.
strict_prepositions = False

# Log file: all output is also written here (flushed after every line).
# Set to None to disable.  Override with -logfile PATH on the command line.
# On restart, the log file is parsed to determine which tests were already
# completed, so the run can resume automatically.  Use -restart to start fresh.
log_file_path = "test_output.txt"
_log_fh = None   # opened in main()

# When True, delete the log file and start fresh (set by -restart flag).
restart = False


# ======== helptext ========

helptext = """test.py — run nlpsolver tests from a test file.

Usage:
  python test.py [options] [testfile ...]

Test files are Python files containing a single list literal of
[input, expected] pairs, e.g.:
  [
    ["Elephants are animals. John is an elephant. John is an animal?", True],
    ["Elephants are animals. Who is an animal?", "An elephant."],
    ["John has a car?", None],   # None means "Unknown" is the expected answer
    ["John gave a book to Mary. What did Mary receive?", ["A book.", "The book."]],
  ]
When expected is a list, the test passes if the received answer matches
ANY element of the list.

If no test file is given, tests/tests_core.py is used.

output control:
 -v  / -verbose        print Input / Expected / Received for every test (default)
 -c  / -compact        print one character per test: . (pass) or F (fail)
 -q  / -quiet          no per-test output; only the final summary
 -f  / -failonly       only print tests that failed

flow control:
 -stopfail             stop the run after the first failure
 -limit N              run at most N tests per file
 -skip N               skip the first N tests in each file
 -filter PATTERN       only run tests whose input contains PATTERN (case-sensitive)
 -restart              start fresh (ignore any previous progress in the log file);
                       without this flag, the run auto-resumes from where it left off

solver options:
 -llm NAME             LLM provider: gpt, claude, gemini, or deepseek
 -version VER          model version string, e.g. gemini-2.0-flash
 -logfile PATH         write log to PATH instead of test_output.txt

cache / matching options:
 -nollmcache           disable LLM response caching for this run
                       (LLM cache is ON by default; results are keyed on
                       provider, version, all call parameters and input text)
 -cache                enable GK prover result caching (off by default)
 -strict               strict confidence comparison: "Probably true." and "Likely true."
                       match each other but not plain "True." (default: qualifiers are
                       stripped so all certainty levels are treated as equivalent)
 -strictprep           strict preposition matching: "in Estonia" and "Estonia" are
                       treated as different answers (default: permissive — a leading
                       spatial preposition on one side but not the other is ignored)

 -help                 show this help text
"""


# ======== auto-resume from log file ========

def _load_progress(log_path):
  """Parse a test_output.txt log file to recover completed test results.

  Returns (completed_count, passed, failed, errors) where errors is a list
  of (test_stub, received) pairs suitable for the summary printer.
  """
  completed = 0
  passed = 0
  failed = 0
  errors = []
  try:
    with open(log_path, "r") as f:
      lines = f.readlines()
  except OSError:
    return (0, 0, 0, [])

  i = 0
  cur_input = None
  cur_expected = None
  while i < len(lines):
    line = lines[i].rstrip("\n")
    if line.startswith("Input:    "):
      cur_input = line[len("Input:    "):]
    elif line.startswith("Expected: "):
      cur_expected = line[len("Expected: "):]
    elif line.startswith("Result:   "):
      result = line[len("Result:   "):].strip()
      completed += 1
      if result == "OK":
        passed += 1
      else:
        failed += 1
        # Scan back for the Received: line
        received = ""
        for j in range(max(0, i - 3), i):
          rline = lines[j].rstrip("\n")
          if rline.startswith("Received: "):
            received = rline[len("Received: "):]
            break
        errors.append(([cur_input, cur_expected], received))
      cur_input = None
      cur_expected = None
    i += 1

  return (completed, passed, failed, errors)


# ======== main ========

def main():
  global _log_fh
  test_files, solver_opts = _parse_cmd_line()

  if log_file_path:
    if restart:
      # Start fresh: truncate the log file
      try:
        _log_fh = open(log_file_path, "w", buffering=1)
      except OSError as e:
        print("Warning: cannot open log file", log_file_path, ":", e)
    else:
      # Resume mode: append to existing log file
      try:
        _log_fh = open(log_file_path, "a", buffering=1)
      except OSError as e:
        print("Warning: cannot open log file", log_file_path, ":", e)

  all_passed = 0
  all_failed = 0
  all_ran    = 0
  all_errors = []   # list of (file, test, received) triples

  total_start = time.time()

  for tf in test_files:
    passed, failed, ran, errors = run_file(tf, solver_opts)
    all_passed += passed
    all_failed += failed
    all_ran    += ran
    all_errors += errors

  elapsed = round(time.time() - total_start, 2)

  if _log_fh:
    _log_fh.close()

  if len(test_files) > 1:
    _print()
    _print("=" * 50)
    _print("Overall summary")
    _print("=" * 50)
    _print_summary(all_ran, all_passed, all_failed, elapsed, all_errors)
  elif not all_errors and not show_verbose:
    # Single file, no failures — print_summary was already called inside run_file
    pass


# ======== per-file runner ========

def run_file(path, solver_opts):
  """Load a test file, run every test through the solver, return stats."""
  tests = _load_test_file(path)
  if tests is None:
    return (0, 0, 0, [])

  # --- auto-resume from log file ---
  resume_count = 0
  resumed_passed = 0
  resumed_failed = 0
  resumed_errors = []
  if not restart and log_file_path:
    resume_count, resumed_passed, resumed_failed, resumed_errors = _load_progress(log_file_path)

  _print()
  _print("=" * 50)
  _print("Test file:", path)
  _print("=" * 50)
  if resume_count > 0:
    _print(f"Resuming: skipping {resume_count} already completed tests "
           f"({resumed_passed} passed, {resumed_failed} failed)")
  if show_verbose:
    _print()

  passed  = resumed_passed
  failed  = resumed_failed
  ran     = resume_count
  errors  = resumed_errors  # (test, received) pairs
  skipped = 0

  start = time.time()

  for i, test in enumerate(tests):
    # --- skip already-resumed tests ---
    if i < resume_count:
      continue
    # --- skip / limit / filter ---
    if skipped < skip:
      skipped += 1
      continue
    if limit and (ran - resume_count) >= limit:
      break
    if filter_pattern and filter_pattern not in test[0]:
      continue

    ran += 1
    inp      = test[0]
    expected = test[1]

    # --- run solver ---
    try:
      received = english_to_answer(inp, dict(solver_opts))
    except KeyboardInterrupt:
      _print("\nInterrupted.")
      break
    except Exception as e:
      received = "Software error: " + str(e)

    # --- compare ---
    ok = _result_matches(expected, received, inp)

    # --- output ---
    if show_compact:
      _print("." if ok else "F", end="", flush=True)
      # Always write structured lines to log for resume support
      _log_write("Input:   ", inp)
      _log_write("Expected:", _display(expected))
      _log_write("Received:", received)
      _log_write("Result:  ", "OK" if ok else "FAIL")
      _log_write()
    elif show_quiet:
      # No console output, but write structured lines to log
      _log_write("Input:   ", inp)
      _log_write("Expected:", _display(expected))
      _log_write("Received:", received)
      _log_write("Result:  ", "OK" if ok else "FAIL")
      _log_write()
    elif show_verbose:
      if ok and show_failures_only:
        pass  # suppress passing tests on console
      else:
        _print("Input:   ", inp)
        _print("Expected:", _display(expected))
        _print("Received:", received)
        _print("Result:  ", "OK" if ok else "FAIL")
        _print()
      # If suppressed on console, still write to log for resume
      if ok and show_failures_only:
        _log_write("Input:   ", inp)
        _log_write("Expected:", _display(expected))
        _log_write("Received:", received)
        _log_write("Result:  ", "OK" if ok else "FAIL")
        _log_write()

    if ok:
      passed += 1
    else:
      failed += 1
      errors.append((test, received))
      if stop_on_fail:
        if show_compact:
          _print()
        _print("Stopping after first failure (-stopfail).")
        break

  if show_compact:
    _print()   # newline after the dot row

  elapsed = round(time.time() - start, 2)
  _print_summary(ran, passed, failed, elapsed, errors)

  return (passed, failed, ran, errors)


# ======== result comparison ========

def _result_matches(expected, received, input_text=""):
  """Return True if received is an acceptable answer for expected.

  When expected is a list, the test passes if received matches ANY element.
  """
  # Multiple acceptable answers: pass if any alternative matches.
  if isinstance(expected, list):
    return any(_result_matches_single(alt, received, input_text) for alt in expected)
  return _result_matches_single(expected, received, input_text)


def _result_matches_single(expected, received, input_text=""):
  """Return True if received matches a single expected value."""
  # Normalise Python booleans to canonical answer strings
  if received is True:  received  = "True."
  if received is False: received  = "False."
  if expected is True:  expected  = "True."
  if expected is False: expected  = "False."

  if not received:
    return False

  # Strip confidence qualifiers like "(0.95)" from the received string
  cleaned = received
  if type(cleaned) == str and "(" in cleaned and ")" in cleaned:
    if strict_confidences:
      return False
    tmp = []
    depth = 0
    for ch in cleaned:
      if ch == "(":
        depth += 1
      elif ch == ")":
        depth -= 1
      elif depth == 0:
        tmp.append(ch)
    cleaned = "".join(tmp).replace(" .", ".").strip()

  # Take only the first line of the answer
  if type(cleaned) == str:
    cleaned = cleaned.split("\n")[0].strip()

  # None expected means any "Unknown…" answer is acceptable
  if expected is None:
    return type(cleaned) == str and cleaned.startswith("Unknown")

  if type(expected) == str:
    expected = expected.strip()

  if expected == cleaned:
    return True

  # Phrase-level comparison: order-independent, preposition-permissive
  if type(expected) == str and type(cleaned) == str:
    if _phrases_match(expected, cleaned):
      return True

  # Standardised comparison: ignore punctuation, sort words
  if _standardize(expected) == _standardize(cleaned):
    return True

  # Confidence-qualifier comparison.
  # Default (non-strict): strip leading certainty adverbs from both sides and
  #   compare core content — "Probably true." == "True." == "Likely true."
  # Strict: normalise all qualifier words to a single canonical form ("Probably")
  #   so qualifiers at the same certainty class match each other but not the
  #   plain unqualified form — "Probably true." == "Likely true." != "True."
  norm_cleaned  = _norm_conf_qualifier(cleaned)
  norm_expected = _norm_conf_qualifier(expected)
  if norm_cleaned != cleaned or norm_expected != expected:
    if norm_cleaned == norm_expected:
      return True
    if _standardize(norm_expected) == _standardize(norm_cleaned):
      return True

  # Adjective-prepend: "The nice mother" matches "The mother" if "nice" is in the input text
  if type(expected) == str and type(cleaned) == str and input_text:
    if _adjective_prepend_match(expected, cleaned, input_text):
      return True

  return False


# Spatial prepositions that may prefix location phrases in answers.
# These are stripped for comparison only when one side has a prep and the other does not.
_SPATIAL_PREPS = frozenset({
  "in", "on", "at", "near", "above", "under", "below", "over",
  "inside", "outside", "behind", "beside", "between", "by",
  "within", "upon", "onto", "into",
})

# Articles stripped when normalising phrase content.
_ARTICLES = frozenset({"a", "an", "the"})

# Certainty adverbs that may prefix an answer (case-insensitive match on first word).
_CONF_QUALIFIERS = frozenset({"probably", "likely", "perhaps", "certainly", "possibly"})


def _split_and_phrases(txt):
  """Split a string on ' and ', ', and ', or ', ' into individual phrases."""
  parts = re.split(r',\s+and\s+|,\s+|\s+and\s+', txt)
  return [p.strip() for p in parts if p.strip()]


def _parse_phrase(phrase):
  """Return (prep, content) for a phrase (all lowercase, stripped of articles).

  prep is the leading spatial preposition (lowercase) or "".
  content is the remaining words, lowercased, articles removed, joined by space.
  In non-strict confidence mode, leading confidence qualifiers (e.g. "likely")
  are also stripped from individual phrases.
  """
  words = phrase.lower().replace(".", "").replace(",", "").split()
  prep = ""
  if words and words[0] in _SPATIAL_PREPS:
    prep = words[0]
    words = words[1:]
  if not strict_confidences and words and words[0] in _CONF_QUALIFIERS:
    words = words[1:]
  words = [w for w in words if w not in _ARTICLES]
  return prep, " ".join(words)


def _adjective_prepend_match(expected, received, input_text):
  """Return True if received equals expected with adjectives prepended before nouns,
  and every extra adjective appears in input_text.

  E.g. expected="The mother", received="The nice mother", input has "nice" → True.
  Works for multi-word answers like "The mother and the fox" vs "The nice mother and the nice fox".
  """
  input_lower = input_text.lower()
  exp_phrases = _split_and_phrases(expected)
  rec_phrases = _split_and_phrases(received)
  if len(exp_phrases) != len(rec_phrases):
    return False
  # Sort both sides by content for order-independent comparison
  exp_sorted = sorted(exp_phrases, key=str.lower)
  rec_sorted = sorted(rec_phrases, key=str.lower)
  for ep, rp in zip(exp_sorted, rec_sorted):
    ew = ep.lower().replace(".", "").split()
    rw = rp.lower().replace(".", "").split()
    # received must contain all words of expected in order, with extra words (adjectives)
    ei = 0
    extras = []
    for w in rw:
      if ei < len(ew) and w == ew[ei]:
        ei += 1
      else:
        extras.append(w)
    if ei != len(ew):
      return False
    # Every extra word must appear in the input text
    if not extras:
      continue
    for adj in extras:
      if adj not in input_lower:
        return False
  return True


def _phrases_match(expected_str, received_str):
  """Return True if expected_str and received_str represent the same set of phrases.

  Order is always ignored.  Preposition handling depends on strict_prepositions:
    permissive (default): "Estonia" == "in Estonia" (prep on one side only → OK)
    strict: prepositions must match exactly on both sides.
  Comparison is case-insensitive and strips articles.

  Single-phrase comparisons are handled by the same prep-permissive logic
  so e.g. "Estonia." matches "In Estonia." for case 187.
  """
  exp_phrases = _split_and_phrases(expected_str)
  rec_phrases = _split_and_phrases(received_str)
  if len(exp_phrases) != len(rec_phrases):
    return False
  if not exp_phrases:
    return False

  exp_parsed = sorted([_parse_phrase(p) for p in exp_phrases], key=lambda x: x[1])
  rec_parsed = sorted([_parse_phrase(p) for p in rec_phrases], key=lambda x: x[1])

  for (ep, ec), (rp, rc) in zip(exp_parsed, rec_parsed):
    if ec != rc:
      return False
    if strict_prepositions:
      if ep != rp:
        return False
    else:
      # permissive: both have preps → must match; one absent → OK
      if ep and rp and ep != rp:
        return False
  return True

def _norm_conf_qualifier(txt):
  """Normalise a leading confidence-qualifier word in txt.

  Non-strict mode (default): drop the qualifier entirely.
  Strict mode: replace all qualifier words with the canonical "Probably".
  Returns txt unchanged if no qualifier is found.
  """
  if type(txt) != str:
    return txt
  parts = txt.split(" ", 1)
  if len(parts) == 2 and parts[0].rstrip(".").lower() in _CONF_QUALIFIERS:
    return parts[1] if not strict_confidences else "Probably " + parts[1]
  return txt


def _standardize(txt):
  """Remove punctuation, lower-case, sort words — for fuzzy comparison.

  Also strips articles (a/an/the) and single-letter Skolem-suffix words
  (e.g. 'Mother A' -> 'mother', 'The mother' -> 'mother') so that entity
  naming style differences don't cause spurious failures.
  """
  if type(txt) != str:
    return txt
  txt = txt.replace(".", "").replace(",", " ").lower()
  words = txt.split()
  # Remove articles and single-letter words (Skolem suffixes like 'a', 'b', 'c')
  _skip = {"a", "an", "the"}
  words = [w for w in words if w not in _skip and len(w) > 1]
  words.sort()
  return words


def _display(expected):
  """Pretty-print an expected value for output."""
  if isinstance(expected, list):
    return " | ".join(_display(alt) for alt in expected)
  if expected is True:  return "True."
  if expected is False: return "False."
  if expected is None:  return "Unknown (None)"
  return repr(expected)


# ======== summary printer ========

def _print_summary(ran, passed, failed, elapsed, errors):
  _print()
  _print(f"Tests run: {ran}  |  Passed: {passed}  |  Failed: {failed}  |  Time: {elapsed}s")
  if errors:
    _print()
    _print("Failed tests:")
    for test, received in errors:
      _print("  Input:   ", test[0])
      _print("  Expected:", _display(test[1]))
      _print("  Received:", received)
      _print()


# ======== test file loader ========

def _load_test_file(path):
  """Read and eval a test file; return the list of tests or None on error."""
  try:
    with open(path, "r") as f:
      src = f.read()
  except OSError:
    print(f"Error: could not read test file: {path}")
    return None
  try:
    tests = eval(src)
  except Exception as e:
    print(f"Error: could not parse test file {path}: {e}")
    return None
  if not isinstance(tests, list):
    print(f"Error: test file {path} does not contain a list.")
    return None
  return tests


# ======== command-line parser ========

def _parse_cmd_line():
  """Return (list_of_test_files, solver_options_dict)."""
  global show_verbose, show_compact, show_quiet, show_failures_only
  global stop_on_fail, limit, skip, filter_pattern, strict_confidences, strict_prepositions
  global restart, log_file_path

  solver_opts = {}
  test_files  = []
  params = sys.argv[1:]
  elpos  = -1
  skippos = 0

  for el in params:
    elpos += 1
    if skippos > 0:
      skippos -= 1
      continue

    if el in ["-v", "--v", "-verbose", "--verbose"]:
      show_verbose = True
      show_compact = False
      show_quiet   = False
    elif el in ["-c", "--c", "-compact", "--compact"]:
      show_compact = True
      show_verbose = False
      show_quiet   = False
    elif el in ["-q", "--q", "-quiet", "--quiet"]:
      show_quiet   = True
      show_verbose = False
      show_compact = False
    elif el in ["-f", "--f", "-failonly", "--failonly"]:
      show_failures_only = True
    elif el in ["-stopfail", "--stopfail"]:
      stop_on_fail = True
    elif el in ["-strict", "--strict"]:
      strict_confidences = True
    elif el in ["-strictprep", "--strictprep"]:
      strict_prepositions = True
    elif el in ["-restart", "--restart"]:
      restart = True
    elif el in ["-nollmcache", "--nollmcache"]:
      solver_opts["use_llm_cache_flag"] = False
    elif el in ["-cache", "--cache"]:
      solver_opts["use_cache_flag"] = True
    elif el in ["-limit", "--limit"]:
      if elpos + 1 >= len(params):
        print("-limit requires an integer argument"); sys.exit(0)
      try:
        limit = int(params[elpos + 1])
      except ValueError:
        print("-limit requires an integer argument"); sys.exit(0)
      skippos = 1
    elif el in ["-skip", "--skip"]:
      if elpos + 1 >= len(params):
        print("-skip requires an integer argument"); sys.exit(0)
      try:
        skip = int(params[elpos + 1])
      except ValueError:
        print("-skip requires an integer argument"); sys.exit(0)
      skippos = 1
    elif el in ["-filter", "--filter"]:
      if elpos + 1 >= len(params):
        print("-filter requires a pattern argument"); sys.exit(0)
      filter_pattern = params[elpos + 1]
      skippos = 1
    elif el in ["-llm", "--llm"]:
      if elpos + 1 >= len(params):
        print("-llm requires a provider name"); sys.exit(0)
      _solve_mod.llm = params[elpos + 1]
      skippos = 1
    elif el in ["-version", "--version"]:
      if elpos + 1 >= len(params):
        print("-version requires a version string"); sys.exit(0)
      _solve_mod.llm_version = params[elpos + 1]
      skippos = 1
    elif el in ["-think", "--think"]:
      # -think alone → True; -think N → integer budget
      if elpos + 1 < len(params):
        try:
          solver_opts["think_flag"] = int(params[elpos + 1])
          skippos = 1
        except ValueError:
          solver_opts["think_flag"] = True
      else:
        solver_opts["think_flag"] = True
    elif el in ["-logfile", "--logfile"]:
      if elpos + 1 >= len(params):
        print("-logfile requires a file path"); sys.exit(0)
      log_file_path = params[elpos + 1]
      skippos = 1
    elif el in ["help", "-help", "--help"]:
      print(helptext); sys.exit(0)
    elif el and el.startswith("-"):
      print(f"Unknown option: {el}"); print(helptext); sys.exit(0)
    else:
      test_files.append(el)

  if not test_files:
    test_files = [default_test_file]

  # In quiet mode, failures_only is implied for per-test output (there is none),
  # but we still show the failures block in the summary.
  if show_quiet:
    show_verbose = False
    show_compact = False

  return test_files, solver_opts


# ======== entry point ========

if __name__ == "__main__":
  main()


# =========== the end ==========
