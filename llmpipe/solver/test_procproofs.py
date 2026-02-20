#!/usr/bin/env python3
# Test for procproofs.py: processes outexample.txt and outexample2.txt through
# the proof formatter and prints results for manual inspection.
#
# Run from the solver/ directory:
#   python3 test_procproofs.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import procproofs

# ======== outexample.txt ========
# The proof has 4 clause names: sent_S1 .. sent_S4.
# Original text (reconstructed from clause content):
#   S1: "John is nice."
#   S2: "Nice persons are happy."   (rule used as axiom)
#   S3: "Mike is happy."
#   S4: "Who is happy?"             (question -> goal)

mock_s1_json_ex1 = [
  {"raw": "John is nice.",          "units": [{"unit_id": "S1"}]},
  {"raw": "Nice persons are happy.", "units": [{"unit_id": "S2"}]},
  {"raw": "Mike is happy.",          "units": [{"unit_id": "S3"}]},
  {"raw": "Who is happy?",           "units": [{"unit_id": "S4"}]},
]

# ======== outexample2.txt ========
# sent_S1 and sent_S4 are used.
# Original text:
#   S1: "John is nice."
#   S4: "Is John nice?"

mock_s1_json_ex2 = [
  {"raw": "John is nice.",  "units": [{"unit_id": "S1"}]},
  {"raw": "Is John nice?",  "units": [{"unit_id": "S4"}]},
]


def run(label, filename, s1_json, opts):
  path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
  with open(path) as f:
    raw = f.read()
  result = procproofs.process_proof(raw, s1_json=s1_json, options=opts)
  print("=" * 60)
  print(label)
  print("-" * 60)
  print(result)
  print()


run("outexample.txt  — basic answer",
    "outexample.txt", mock_s1_json_ex1, {})

run("outexample.txt  — with -explain",
    "outexample.txt", mock_s1_json_ex1, {"prover_explain_flag": True})

run("outexample.txt  — with -explain -logic (shows raw clause)",
    "outexample.txt", mock_s1_json_ex1,
    {"prover_explain_flag": True, "show_logic_flag": True})

run("outexample2.txt — basic answer",
    "outexample2.txt", mock_s1_json_ex2, {})

run("outexample2.txt — with -explain",
    "outexample2.txt", mock_s1_json_ex2, {"prover_explain_flag": True})
