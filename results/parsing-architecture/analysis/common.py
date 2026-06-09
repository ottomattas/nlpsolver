#!/usr/bin/env python3
"""Shared loaders for the parsing-architecture extension analyses (X1, E2, E5, E8).

All four extensions are pure re-analysis of the committed Gate-1 snapshot under
results/parsing-architecture/core_100/<condition>/<model>/case_*.json — no new
LLM calls.  Pass source="live" to read the gitignored llmpipe/testresults/ tree
instead (e.g. for the X2 selfrefine and X3 defeasible pilots before snapshotting).
"""
import os
import glob
import json

# results/parsing-architecture/  (holds core_100/ snapshot + this analysis/ dir)
PA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# repo root
REPO = os.path.dirname(os.path.dirname(PA_ROOT))
LIVE_ROOT = os.path.join(REPO, "llmpipe", "testresults")

COND_DIR = {"A": "twostage", "B": "onestage-struct",
            "C": "onestage-direct", "D": "selfrefine"}
COND_LABEL = {"A": "two-stage", "B": "one-struct",
              "C": "one-direct", "D": "self-refine"}
# Base LLM parse calls per condition (excluding JSON/sanity retries).
COND_CALLS = {"A": 2, "B": 1, "C": 1, "D": 2}
MODELS = ["gpt", "claude", "gemini", "deepseek"]

# Per-call system-prompt sizes (tokens, ~chars/4) measured from prompts/.
TOK_STAGE1 = 25834
TOK_STAGE2 = 30193
TOK_ONESTAGE = 56391
# Total input-prompt tokens per condition (sysprompt only; case text is tiny).
COND_INPUT_TOK = {"A": TOK_STAGE1 + TOK_STAGE2,   # two smaller calls
                  "B": TOK_ONESTAGE,
                  "C": TOK_ONESTAGE,
                  "D": 2 * TOK_ONESTAGE}            # direct + refine


def _dir(cond, model, testname, source):
  if source == "live":
    return os.path.join(LIVE_ROOT, testname, COND_DIR[cond], model)
  return os.path.join(PA_ROOT, testname, COND_DIR[cond], model)


def load(cond, model, testname="core_100", source="snapshot"):
  """Return {case_id: case_dict} for one condition/model."""
  out = {}
  for fp in glob.glob(os.path.join(_dir(cond, model, testname, source), "case_*.json")):
    try:
      d = json.load(open(fp))
    except Exception:
      continue
    out[d.get("case_id")] = d
  return out


def is_correct(case):
  """A run is correct only if it produced an answer and matched (errors => wrong)."""
  return ("error" not in case) and bool(case.get("correctness"))


def stage2_packages(case):
  """Number of @id sentence packages in the Stage-2 logic (coverage proxy).

  Stage-2 is ['and', ['@id','S1',...], ...]; package count = len - 1.
  Returns 0 when stage2 is missing."""
  s2 = case.get("stage2")
  if not isinstance(s2, list) or not s2:
    return 0
  if s2[0] == "and":
    return len([x for x in s2[1:] if isinstance(x, list)])
  return 1  # single bare package


def has_question(case):
  """True if the Stage-2 logic encodes a question (a 'question'/'ask' head)."""
  s2 = case.get("stage2")
  txt = json.dumps(s2) if s2 is not None else ""
  return ('"question"' in txt) or ('"ask"' in txt) or ('"@question"' in txt)


def n_sentences(text):
  """Crude sentence count: terminal . ? ! groups."""
  import re
  parts = [p for p in re.split(r'[.?!]+', (text or "")) if p.strip()]
  return max(1, len(parts))


def retries(case):
  """Total recorded sanity/JSON retries across stages (0 if none logged)."""
  return len(case.get("stage_1_retries", [])) + len(case.get("stage_2_retries", []))


def llm_calls(cond, case):
  """LLM parse calls for this case = base calls for the condition + retries."""
  return COND_CALLS[cond] + retries(case)
