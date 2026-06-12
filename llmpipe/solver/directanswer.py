# Direct-answer mode for the llmpipe solver.
#
# Answer a case with a SINGLE LLM call: the given prompt file is the system
# prompt, the case text is the user message, and the LLM's reply is returned
# verbatim as the answer -- bypassing the parse -> logic -> prover pipeline.
#
# This is test-set agnostic: the prompt file decides the answer form (e.g. the
# FOLIO prompt yields True/False/Unknown; a wh-style prompt would yield a phrase).
# Enabled via -directanswer FILE (solve.py / runtests.py).

import re
import llmcall

# prompt_path -> composed system-prompt text (loaded once per process)
_prompt_cache = {}

# Reasoning-capable models often ignore "output only one word" and write a
# chain-of-thought ending in the verdict.  When the reply contains a
# True/False/Unknown/Uncertain verdict, take the LAST one and normalise it; this
# makes the verdict robustly recoverable for FOLIO-style yes/no/unknown tasks.
# For phrase-answer prompts that produce no such token, the raw reply is kept.
_VERDICT_RE = re.compile(r"\b(true|false|unknown|uncertain)\b", re.IGNORECASE)
_VERDICT_NORM = {"true": "True.", "false": "False.",
                 "unknown": "Unknown.", "uncertain": "Unknown."}


def _extract_verdict(reply):
  """If the reply ends with / contains a True/False/Unknown/Uncertain verdict,
  return it normalised ('True.'/'False.'/'Unknown.'); otherwise the stripped reply."""
  reply = reply.strip()
  matches = _VERDICT_RE.findall(reply)
  if matches:
    return _VERDICT_NORM[matches[-1].lower()]
  return reply


def _load_prompt(path):
  if path in _prompt_cache:
    return _prompt_cache[path]
  txt = ""
  try:
    with open(path, "r") as f:
      txt = f.read().strip()
  except OSError as e:
    print("Error: could not read direct-answer prompt '" + str(path) + "': " + str(e))
    txt = ""
  _prompt_cache[path] = txt
  return txt


def answer_directly(text, prompt_path, llm=None, version=None, tokens=None, think=None):
  """One LLM call: prompt_path as system prompt, text as user message.

  Returns the LLM reply stripped to a single trimmed string, or "" on error.
  Caching is the normal llmcall SQLite cache (a distinct key per prompt)."""
  sysprompt = _load_prompt(prompt_path)
  if not sysprompt:
    return ""
  th = think if think is not None else False
  reply = llmcall.call_llm(sysprompt, text, llm=llm, version=version,
                           max_tokens=tokens, think=th)
  if not isinstance(reply, str):
    return ""
  return _extract_verdict(reply)
