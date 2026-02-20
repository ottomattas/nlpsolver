#!/usr/bin/env python3
# solvetest.py — run the solve pipeline on a test file and report results.
#
# Usage:
#   python3 solvetest.py [testfile.py] [options]
#
# Default test file: tests/tests_core.py
#
# Options:
#   -llm NAME      : LLM provider (gpt, claude, gemini)
#   -version VER   : model version string (e.g. claude-sonnet-4-6)
#   -seconds N     : prover timeout in seconds (default: 2)
#   -axioms f ...  : axiom files to pass to the prover
#   -usekb         : use background knowledge base
#   -nokb          : disable knowledge base
#   -cache         : enable GK prover result cache (off by default)
#   -nollmcache    : disable LLM response cache (LLM cache is on by default)
#   -log FILE      : log file path (default: solvetest.log)
#   -stop N        : stop after N cumulative failures (0 = run all, default 0)
#   -v             : verbose — print each test result as it runs
#   -help          : show this help text
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
import re
import time

# Add solver/ to the import path so we can import solve, globals, etc.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "solver"))

import solve


# ======== defaults ========

DEFAULT_TEST_FILE = "tests/tests_core.py"
DEFAULT_LOG_FILE  = "solvetest.log"


# ======== entry point ========

def main():
  test_file, solve_opts, run_opts = _parse_args()

  tests = _load_tests(test_file)
  if tests is None:
    sys.exit(1)

  print("Running {:d} tests from {}".format(len(tests), test_file))
  print("Log:     {}".format(run_opts["log_file"]))
  print()

  results = _run_tests(tests, test_file, solve_opts, run_opts)
  _print_summary(results)


# ======== test loading ========

def _load_tests(test_file):
  """Load and eval a test file; return the list of tests, or None on error."""
  try:
    with open(test_file, "r") as f:
      src = f.read()
  except OSError as e:
    print("Error: could not read test file {}: {}".format(test_file, e))
    return None
  try:
    tests = eval(src)
  except Exception as e:
    print("Error: could not parse test file {}:".format(test_file))
    print(" ", e)
    return None
  if not isinstance(tests, list):
    print("Error: test file {} did not evaluate to a list.".format(test_file))
    return None
  return tests


# ======== test runner ========

def _run_tests(tests, test_file, solve_opts, run_opts):
  """Run all tests; write each result to the log immediately; return a results dict."""
  verbose    = run_opts.get("verbose", False)
  log_file   = run_opts.get("log_file", DEFAULT_LOG_FILE)
  stop_after = run_opts.get("stop_after", 0)

  entries  = []
  n_passed = 0
  n_failed = 0
  start    = time.time()

  # Open the log file once and write the header; each entry is flushed
  # immediately so the log is intact even if testing is interrupted.
  try:
    logf = open(log_file, "w")
  except OSError as e:
    print("Warning: could not open log file {}: {}".format(log_file, e))
    logf = None

  ts = time.strftime("%Y-%m-%d %H:%M:%S")
  _log(logf, "solvetest log — {}".format(ts))
  _log(logf, "Test file : {}".format(test_file))
  _log(logf, "Tests     : {:d}".format(len(tests)))
  _log(logf, "")

  for i, test in enumerate(tests):
    if not isinstance(test, list) or len(test) < 2:
      continue
    text     = test[0]
    expected = test[1]
    # test[2:] is optional extra info — not used for evaluation

    nr = i + 1

    if verbose:
      _print_test_header(nr, len(tests), text)

    # Call the solver
    try:
      got = solve.english_to_answer(text, dict(solve_opts))
    except KeyboardInterrupt:
      print("\nInterrupted.")
      _log(logf, "--- interrupted ---")
      break
    except Exception as e:
      got = "Error: " + str(e)

    ok = _answers_match(got, expected)

    entry = {
      "nr":       nr,
      "text":     text,
      "expected": expected,
      "got":      got,
      "ok":       ok,
    }
    entries.append(entry)

    # Write this entry to the log and flush immediately so it survives cancellation
    status = "PASS" if ok else "FAIL"
    _log(logf, "[{:d}] {}  {}  expected={}".format(nr, status, text[:100], _fmt(expected)))
    if not ok:
      _log(logf, "     got      : {}".format(
        got[:200] if isinstance(got, str) else str(got)))
    if logf:
      logf.flush()

    if ok:
      n_passed += 1
      if verbose:
        print("  PASS  expected={}  got={}".format(_fmt(expected), _fmt(got)))
      else:
        print(".", end="", flush=True)
    else:
      n_failed += 1
      if verbose:
        print("  FAIL  expected={}  got={}".format(_fmt(expected), _fmt(got)))
      else:
        print("F", end="", flush=True)
    sys.stdout.flush()

    if stop_after and n_failed >= stop_after:
      print("\nStopping after {:d} failure(s).".format(stop_after))
      break

  elapsed = time.time() - start

  if not verbose:
    print()   # newline after the dot/F progress line

  # Write summary footer to the log
  _log(logf, "")
  _log(logf, "Tests run : {:d}".format(len(entries)))
  _log(logf, "Passed    : {:d}".format(n_passed))
  _log(logf, "Failed    : {:d}".format(n_failed))
  _log(logf, "Time      : {:.1f}s".format(elapsed))
  _log(logf, "--- end ---")

  if logf:
    logf.close()

  return {
    "total":   len(entries),
    "passed":  n_passed,
    "failed":  n_failed,
    "elapsed": elapsed,
    "entries": entries,
  }


# ======== answer comparison ========

def _answers_match(got, expected):
  """Return True if the solver output matches the expected answer.

  Rules:
    expected is None   -> got must start with "Unknown"
    expected is True   -> got must start with "True"
    expected is False  -> got must start with "False"
    expected is str    -> direct match, or normalized token-set match

  Normalization (for string comparison):
    - strip confidence annotations like "(confidence 0.85)"
    - take only the first line
    - strip trailing . ! ?
    - lowercase
    - split on whitespace and commas, sort tokens
    This lets "John and Mary." match "Mary and John." etc.
  """
  # Coerce booleans to canonical strings
  if got is True:   got  = "True."
  if got is False:  got  = "False."

  # Extract the first meaningful line from got; strip confidence annotations.
  got_clean = _clean_answer(got)

  if expected is None:
    return got_clean.lower().startswith("unknown")

  if expected is True or expected == "True" or expected == "True.":
    return got_clean.lower().startswith("true")

  if expected is False or expected == "False" or expected == "False.":
    return got_clean.lower().startswith("false")

  if isinstance(expected, str):
    exp_clean = _clean_answer(expected)
    if got_clean == exp_clean:
      return True
    # Normalized token-set comparison
    return _normalize(got_clean) == _normalize(exp_clean)

  return False


def _clean_answer(txt):
  """Strip confidence annotations, take first line, strip whitespace."""
  if not isinstance(txt, str):
    return str(txt)
  # Remove "(confidence X.XX)" style annotations
  txt = re.sub(r'\s*\(confidence[^)]*\)', '', txt)
  # Take first non-empty line
  for line in txt.splitlines():
    line = line.strip()
    if line:
      return line
  return txt.strip()


def _normalize(txt):
  """Lowercase, strip punctuation, split, sort — for fuzzy matching."""
  txt = txt.lower()
  txt = re.sub(r'[.,!?;:]+', '', txt)
  tokens = re.split(r'[\s,]+', txt)
  tokens = [t for t in tokens if t]
  tokens.sort()
  return tokens


# ======== output helpers ========

def _fmt(val):
  """Short display of an expected or got value."""
  if val is None:  return "None"
  if val is True:  return "True"
  if val is False: return "False"
  s = str(val)
  return s[:60] + "…" if len(s) > 60 else s


def _print_test_header(nr, total, text):
  print("[{}/{}] {}".format(nr, total, text[:100] + ("…" if len(text) > 100 else "")))


def _print_summary(results):
  """Print final summary to stdout."""
  total   = results["total"]
  passed  = results["passed"]
  failed  = results["failed"]
  elapsed = results["elapsed"]

  print()
  print("=" * 50)
  print("Tests run : {:d}".format(total))
  print("Passed    : {:d}".format(passed))
  print("Failed    : {:d}".format(failed))
  print("Time      : {:.1f}s".format(elapsed))
  print("=" * 50)

  if failed:
    print()
    print("Failed tests:")
    for e in results["entries"]:
      if not e["ok"]:
        print()
        print("  [{:d}] {}".format(e["nr"], e["text"][:120]))
        print("       expected : {}".format(_fmt(e["expected"])))
        print("       got      : {}".format(_fmt(e["got"])))


# ======== log file ========

def _log(logf, line):
  """Write one line to the open log file handle (no-op if logf is None)."""
  if logf:
    logf.write(line + "\n")


# ======== argument parsing ========

def _parse_args():
  """Parse sys.argv; return (test_file, solve_opts, run_opts)."""
  params    = sys.argv[1:]
  test_file = DEFAULT_TEST_FILE
  log_file  = DEFAULT_LOG_FILE
  verbose   = False
  stop_after = 0
  solve_opts = {}   # passed through to solve.english_to_answer()

  i = 0
  while i < len(params):
    el = params[i]

    if el in ("-help", "--help"):
      _print_help()
      sys.exit(0)

    elif el in ("-v", "--v", "-verbose", "--verbose"):
      verbose = True

    elif el in ("-cache", "--cache"):
      solve_opts["use_cache_flag"] = True

    elif el in ("-nollmcache", "--nollmcache"):
      solve_opts["use_llm_cache_flag"] = False

    elif el in ("-usekb", "--usekb"):
      solve_opts["usekb_flag"] = True

    elif el in ("-nokb", "--nokb"):
      solve_opts["nokb_flag"] = True

    elif el in ("-llm", "--llm"):
      i += 1
      if i >= len(params):
        print("-llm requires a provider name: gpt, claude, or gemini")
        sys.exit(1)
      solve.llm = params[i]

    elif el in ("-version", "--version"):
      i += 1
      if i >= len(params):
        print("-version requires a model version string")
        sys.exit(1)
      solve.llm_version = params[i]

    elif el in ("-seconds", "--seconds"):
      i += 1
      if i >= len(params):
        print("-seconds requires an integer argument")
        sys.exit(1)
      try:
        solve_opts["prover_seconds"] = int(params[i])
      except ValueError:
        print("-seconds requires an integer argument")
        sys.exit(1)

    elif el in ("-axioms", "--axioms"):
      axiom_files = []
      i += 1
      while i < len(params) and params[i] and not params[i].startswith("-"):
        axiom_files.append(params[i])
        i += 1
      solve_opts["prover_axiomfiles"] = axiom_files
      continue   # i already advanced past the axiom filenames

    elif el in ("-log", "--log"):
      i += 1
      if i >= len(params):
        print("-log requires a file path argument")
        sys.exit(1)
      log_file = params[i]

    elif el in ("-stop", "--stop"):
      i += 1
      if i >= len(params):
        print("-stop requires an integer argument")
        sys.exit(1)
      try:
        stop_after = int(params[i])
      except ValueError:
        print("-stop requires an integer argument")
        sys.exit(1)

    elif el and el.startswith("-"):
      print("Unknown option: " + el)
      _print_help()
      sys.exit(1)

    else:
      # Positional argument: test file path
      test_file = el

    i += 1

  run_opts = {
    "verbose":    verbose,
    "log_file":   log_file,
    "stop_after": stop_after,
  }
  return test_file, solve_opts, run_opts


def _print_help():
  print("""Usage: python3 solvetest.py [testfile.py] [options]

Default test file: tests/tests_core.py

Options:
  -llm NAME      LLM provider: gpt, claude, or gemini
  -version VER   Model version string (e.g. claude-sonnet-4-6, gpt-4o)
  -seconds N     Prover timeout in seconds (default: 2)
  -axioms f ...  Axiom files to pass to the prover
  -usekb         Use background knowledge base
  -nokb          Disable knowledge base
  -cache         Enable GK prover result caching (off by default)
  -nollmcache    Disable LLM response caching (LLM cache is on by default)
  -log FILE      Log file path (default: solvetest.log)
  -stop N        Stop after N cumulative failures (0 = run all, default 0)
  -v             Verbose: print each test result as it runs
  -help          Show this help text

Test file format (Python list literal):
  [
    ["Text with a question.", True],          # expected: True
    ["Text with a question.", False],         # expected: False
    ["Text with a question.", None],          # expected: Unknown
    ["Text with a question.", "John."],       # expected: string answer
    ["Text ...", "John.", ["extra", "info"]], # extra field is ignored
  ]

Answer matching:
  None expected   -> solver output starts with "Unknown"
  True expected   -> solver output starts with "True"
  False expected  -> solver output starts with "False"
  String expected -> direct match, or normalized token-set match
                     (strips punctuation, lowercases, sorts words)
""")


# ======== run ========

if __name__ == "__main__":
  main()


# =========== the end ==========
