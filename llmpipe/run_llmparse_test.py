#!/usr/bin/env python3

# Quick test for the two-stage LLM parser (llmparse.py).
# Run from the llmpipe/ directory:
#   python3 run_llmparse_test.py

import sys
import json

sys.path.insert(0, "solver")

import llmparse
import llmcall

# ======== test inputs ========

test_inputs = [
  "Red cars do not have crenkils. Blue cars have crenkils. Some cars have crenkils?",
  "The red square is nice. A blue square is cool. A square is cool?",
]

# ======== runner ========

def run_tests(provider, version, debug_file):
  print()
  print("=" * 70)
  print("Provider:", provider, " Version:", version)
  print("Debug file:", debug_file)
  print("=" * 70)

  # Reset llmparse state for this run
  llmparse.debug = True
  llmparse.debug_file = debug_file
  llmparse._stage1_sysprompt = None   # force prompt reload
  llmparse._stage2_sysprompt = None

  # Clear / create the debug file for this run
  try:
    open(debug_file, "w").close()
  except Exception as e:
    print("Warning: could not create debug file:", e)

  total_stats = llmparse._make_stats()

  for i, text in enumerate(test_inputs):
    print()
    print("--- Test", i + 1, "---")
    print("Input:", text)

    s1, s2, stats = llmparse.parse_text(text, llm=provider, version=version)

    print()
    print("Stage 1 result:")
    print(json.dumps(s1, indent=2) if s1 is not None else "FAILED")
    print()
    print("Stage 2 result:")
    print(json.dumps(s2, indent=2) if s2 is not None else "FAILED")

    llmparse.add_stats(total_stats, stats)

  print()
  print("Stats for", provider + ":")
  llmparse.print_stats(total_stats)


# ======== run ========

run_tests("claude",  llmcall.claudeversion,  "debug_claude.log")
run_tests("gemini",  llmcall.geminiversion,  "debug_gemini.log")
run_tests("gpt",     llmcall.gptversion,     "debug_gpt.log")

print()
print("Done. Debug logs: debug_claude.log  debug_gemini.log  debug_gpt.log")
