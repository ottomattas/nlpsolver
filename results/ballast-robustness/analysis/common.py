#!/usr/bin/env python3
"""Shared loaders for the ballast-robustness analyses (plan 02).

Dose b0 is the plan-01 Gate-1 two-stage snapshot
(results/parsing-architecture/core_100/twostage/<model>/), which ran the
identical 100 cases without ballast.  Doses b2, b4, ... live under
results/ballast-robustness/core_100_b<N>/twostage/<model>/ once snapshotted;
pass source="live" to read the gitignored llmpipe/testresults/ tree while a
phase is still running.
"""
import os
import glob
import json

BR_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(BR_ROOT))
PA_ROOT = os.path.join(REPO, "results", "parsing-architecture")
LIVE_ROOT = os.path.join(REPO, "llmpipe", "testresults")
BALLAST_DIR = os.path.join(REPO, "llmpipe", "tests", "ballast")

MODELS = ["gpt", "claude", "gemini", "deepseek"]

# List prices, USD per 1M tokens (checked 2026-06-10; sources in results.md).
# claude: cache_write is the 5-minute ephemeral write premium (1.25x input).
PRICES = {
  "gpt":      {"input": 1.25, "cached": 0.125, "output": 10.00},
  "claude":   {"input": 3.00, "cache_write": 3.75, "cached": 0.30, "output": 15.00},
  "gemini":   {"input": 0.30, "cached": 0.03, "output": 2.50},
  "deepseek": {"input": 0.14, "cached": 0.0028, "output": 0.28},
}


def dose_dir(dose, model, source="snapshot"):
  """Directory of per-case JSONs for (dose, model)."""
  if dose == 0:
    return os.path.join(PA_ROOT, "core_100", "twostage", model)
  testname = f"core_100_b{dose}"
  root = LIVE_ROOT if source == "live" else BR_ROOT
  return os.path.join(root, testname, "twostage", model)


def load(dose, model, source="snapshot"):
  """{case_id: case_dict} for one (dose, model)."""
  out = {}
  for fp in glob.glob(os.path.join(dose_dir(dose, model, source), "case_*.json")):
    try:
      d = json.load(open(fp))
    except Exception:
      continue
    out[d.get("case_id")] = d
  return out


def manifest(dose):
  """The generator manifest for a dose: {case_id: manifest_entry}."""
  fp = os.path.join(BALLAST_DIR, f"tests_core_100_b{dose}.manifest.json")
  with open(fp) as f:
    return {e["case_id"]: e for e in json.load(f)["cases"]}


def is_correct(case):
  """Correct only if it produced an answer and matched (errors => wrong)."""
  return ("error" not in case) and bool(case.get("correctness"))


def call_cost_usd(rec):
  """USD cost of one llm_usage record, from the raw provider fields."""
  llm = rec.get("llm")
  raw = rec.get("raw", {})
  p = PRICES.get(llm)
  if not p:
    return 0.0
  M = 1e6
  if llm == "claude":
    base = raw.get("input_tokens", 0)
    write = raw.get("cache_creation_input_tokens", 0)
    read = raw.get("cache_read_input_tokens", 0)
    out = raw.get("output_tokens", 0)
    return (base * p["input"] + write * p["cache_write"]
            + read * p["cached"] + out * p["output"]) / M
  if llm == "gemini":
    inp = raw.get("promptTokenCount", 0)
    cached = raw.get("cachedContentTokenCount", 0)
    out = raw.get("candidatesTokenCount", 0) + raw.get("thoughtsTokenCount", 0)
    return ((inp - cached) * p["input"] + cached * p["cached"]
            + out * p["output"]) / M
  if llm == "deepseek":
    hit = raw.get("prompt_cache_hit_tokens", 0)
    miss = raw.get("prompt_cache_miss_tokens",
                   raw.get("prompt_tokens", 0) - hit)
    out = raw.get("completion_tokens", 0)
    return (miss * p["input"] + hit * p["cached"] + out * p["output"]) / M
  # gpt (responses or chat-completions API)
  inp = raw.get("input_tokens", raw.get("prompt_tokens", 0))
  details = raw.get("input_tokens_details", raw.get("prompt_tokens_details", {})) or {}
  cached = details.get("cached_tokens", 0)
  out = raw.get("output_tokens", raw.get("completion_tokens", 0))
  return ((inp - cached) * p["input"] + cached * p["cached"]
          + out * p["output"]) / M


def usage_totals(cases):
  """Aggregate llm_usage over {case_id: case_dict}: returns dict with api
  calls, input/cached/output token sums and list-price USD cost."""
  tot = {"api_calls": 0, "input_tokens": 0, "cached_input_tokens": 0,
         "output_tokens": 0, "usd": 0.0, "cases_with_usage": 0}
  for c in cases.values():
    recs = c.get("llm_usage") or []
    if recs:
      tot["cases_with_usage"] += 1
    for r in recs:
      tot["api_calls"] += 1
      tot["input_tokens"] += r.get("input_tokens", 0)
      tot["cached_input_tokens"] += r.get("cached_input_tokens", 0)
      tot["output_tokens"] += r.get("output_tokens", 0)
      tot["usd"] += call_cost_usd(r)
  return tot
