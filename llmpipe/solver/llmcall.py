# LLM API call functions for the nlpsolver: GPT, Claude, Gemini, DeepSeek.
#
# Primary entry point: call_llm(sysprompt, input_text)
# Returns the result string on success, or None on error (error is printed).
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

import time
import sys
import json
import os
import http.client

# Absolute path to llmpipe/ so secrets files are found from any working directory.
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# LLM response cache (same SQLite db used for prover and parse caches).
# Import is conditional so llmcall.py remains usable stand-alone for testing.
try:
  import cache as _cache
except ImportError:
  _cache = None

import utils

# ======== configuration ========

# Which LLM to use: "gpt", "claude", "gemini", or "deepseek"
use_llm = "claude"
use_llm = "gemini"

# Model versions
gptversion = "gpt-5.1"
claudeversion = "claude-sonnet-4-6"
geminiversion = "gemini-2.0-flash"
deepseekversion = "deepseek-chat"          # V3.2; use "deepseek-reasoner" for thinking

# API key files (absolute paths relative to llmpipe/)
gpt_secrets_file = os.path.join(_root, "../gpt/gpt_secrets.js")
claude_secrets_file = os.path.join(_root, "../gpt/claude_secrets.js")
gemini_secrets_file = os.path.join(_root, "../gpt/gemini_secrets.js")
deepseek_secrets_file = os.path.join(_root, "../gpt/deepseek_secrets.txt")

# Call parameters
temperature = 0
seed = 1234
default_max_tokens = 8000
sleepseconds = 2
timeout = 60
max_retries = 3

# Debug output
debug = False
calldebug = False

# ======== main entry point ========

def call_llm(sysprompt, input_text, llm=None, version=None, max_tokens=None, think=False):
  """Call the configured LLM with a system prompt and input text.

  llm, version, max_tokens, think override module-level configuration when given.
  think=True enables medium reasoning mode (GPT: reasoning_effort=medium;
  Claude: extended thinking with budget_tokens=8000; Gemini: thinkingConfig
  if the model supports it).  think can also be an int, interpreted as the
  thinking budget in tokens (Claude budget_tokens, Gemini thinkingBudget).
  Returns the result string on success, or None on error (error is printed).

  LLM responses are cached by default.  The cache key encodes the provider,
  version, temperature, seed, max_tokens, think, sysprompt and input text, so a
  cached result is only reused when every one of these is identical.
  Caching is controlled by globals.options["use_llm_cache_flag"] (default
  True) and can be disabled per-run via -nollmcache in solve.py.
  """
  llm = llm or use_llm
  max_tokens = max_tokens or default_max_tokens

  # Resolve the actual version here so the cache key is fully deterministic.
  if llm == "claude":
    ver = version or claudeversion
  elif llm == "gemini":
    ver = version or geminiversion
  elif llm == "deepseek":
    ver = version or deepseekversion
  else:
    ver = version or gptversion

  # --- check cache ---
  cached = _get_llm_cached(llm, ver, max_tokens, think, sysprompt, input_text)
  if cached is not None:
    if debug:
      print("cache hit (" + llm + " " + ver + ")")
    return cached

  # --- call the LLM ---
  if debug:
    print("calling " + llm + " " + ver + " ...")
  try:
    if llm == "claude":
      result = call_claude(ver, input_text, sysprompt, max_tokens, think=think)
    elif llm == "gemini":
      result = call_gemini(ver, input_text, sysprompt, max_tokens, think=think)
    elif llm == "deepseek":
      result = call_deepseek(ver, input_text, sysprompt, max_tokens, think=think)
    else:
      result = call_gpt(ver, input_text, sysprompt, max_tokens, think=think)
  except KeyboardInterrupt:
    raise
  except Exception as e:
    return llm_error("unexpected error calling LLM: " + str(e))

  # --- store to cache ---
  _store_llm_cached(llm, ver, max_tokens, think, sysprompt, input_text, result)

  return result


def _get_llm_cached(llm, ver, max_tokens, think, sysprompt, input_text):
  """Return a cached LLM result, or None if not cached / cache disabled."""
  if _cache is None:
    return None
  try:
    key = _cache.make_llm_cache_key(llm, ver, temperature, seed, max_tokens, think, sysprompt, input_text)
    return _cache.get_llm_from_cache(key)
  except Exception:
    return None


def _store_llm_cached(llm, ver, max_tokens, think, sysprompt, input_text, result):
  """Store result in the LLM cache (silently ignored on any error)."""
  if _cache is None or result is None:
    return
  try:
    key = _cache.make_llm_cache_key(llm, ver, temperature, seed, max_tokens, think, sysprompt, input_text)
    _cache.add_llm_to_cache(key, result)
  except Exception:
    pass


# ======== gemini ========

# https://ai.google.dev/gemini-api/docs/text-generation

def _gemini_supports_thinking(version):
  """Return True if this Gemini model version supports thinkingConfig.
  Thinking is supported by models with 'thinking' in the name and by
  Gemini 2.5+ series (which have built-in thinking capability)."""
  v = version.lower()
  if "thinking" in v:
    return True
  # gemini-2.5-* and any future major version (3+) support thinking
  import re
  m = re.match(r"gemini-(\d+)[\.-]", v)
  if m and int(m.group(1)) >= 3:
    return True
  if v.startswith("gemini-2.5"):
    return True
  return False

def call_gemini(version, sentences, sysprompt, max_tokens, think=False):
  try:
    sf = open(gemini_secrets_file, "r")
    key = sf.read().strip()
    sf.close()
  except:
    return llm_error("Could not read Gemini API key file: " + str(gemini_secrets_file))

  baseurl = "/v1beta/models/" + version + ":generateContent"
  genconfig = {
    "maxOutputTokens": max_tokens,
    "temperature": temperature
  }
  if think and _gemini_supports_thinking(version):
    budget = think if isinstance(think, int) else 8000
    genconfig["thinkingConfig"] = {"thinkingBudget": budget}
  call = {
    "contents": [{"parts": [{"text": sentences}]}],
    "generationConfig": genconfig
  }
  if sysprompt:
    call["system_instruction"] = {"parts": [{"text": sysprompt}]}

  utils.debug_print("gemini call", call, flag=calldebug)
  calltxt = json.dumps(call)

  trycount = 0
  while True:
    host = "generativelanguage.googleapis.com"
    conn = http.client.HTTPSConnection(host, timeout=timeout)
    try:
      conn.request("POST", baseurl, calltxt,
                   headers={"content-Type": "application/json", "x-goog-api-key": key})
      response = conn.getresponse()
    except KeyboardInterrupt:
      raise
    except:
      trycount += 1
      if conn: conn.close()
      if trycount > max_retries:
        return llm_error("Gemini connection failed after " + str(max_retries) + " retries")
      print("Gemini connection failure, retrying...")
      time.sleep(sleepseconds * trycount)
      continue
    if response.status != 200 or response.reason != "OK":
      message = ""
      try:
        data = json.loads(response.read())
        if "error" in data and "message" in data["error"]:
          message = ": " + data["error"]["message"]
      except:
        pass
      trycount += 1
      if conn: conn.close()
      if trycount > max_retries:
        return llm_error("Gemini API error " + str(response.status) + " " + str(response.reason) + message)
      print("Gemini API failure, retrying:", str(response.status), str(response.reason) + message)
      time.sleep(sleepseconds * trycount)
    else:
      break

  rawdata = response.read()
  conn.close()
  try:
    data = json.loads(rawdata)
  except KeyboardInterrupt:
    raise
  except:
    return llm_error("Gemini response is not valid JSON: " + str(rawdata))

  if "candidates" not in data:
    return llm_error("Gemini response has no candidates: " + str(rawdata))
  data = data["candidates"][0]
  if "content" not in data:
    return llm_error("Gemini response has no content: " + str(data))
  data = data["content"]
  if "parts" not in data:
    return llm_error("Gemini response has no parts: " + str(data))

  utils.debug_print("gemini response:", data, flag=debug)
  res = ""
  for el in data["parts"]:
    if "text" in el:
      res += el["text"].strip()
  return res


# ======== claude ========

def call_claude(version, sentences, sysprompt, max_tokens, think=False):
  try:
    sf = open(claude_secrets_file, "r")
    key = sf.read().strip()
    sf.close()
  except:
    return llm_error("Could not read Claude API key file: " + str(claude_secrets_file))

  messages = [{"role": "user", "content": sentences}]
  call = {
    "model": version,
    "messages": messages,
    "temperature": 1 if think else temperature,
    "max_tokens": max_tokens
  }
  if think:
    budget = think if isinstance(think, int) else 8000
    call["thinking"] = {"type": "enabled", "budget_tokens": budget}
  if sysprompt:
    call["system"] = [{"type": "text", "text": sysprompt, "cache_control": {"type": "ephemeral"}}]

  utils.debug_print("claude call", call, flag=calldebug)
  calltxt = json.dumps(call)

  trycount = 0
  while True:
    host = "api.anthropic.com"
    conn = http.client.HTTPSConnection(host, timeout=timeout)
    try:
      conn.request("POST", "/v1/messages", calltxt,
                   headers={
                     "content-Type": "application/json",
                     "anthropic-version": "2023-06-01",
                     "x-api-key": key
                   })
      response = conn.getresponse()
    except KeyboardInterrupt:
      raise
    except:
      trycount += 1
      if conn: conn.close()
      if trycount > max_retries:
        return llm_error("Claude connection failed after " + str(max_retries) + " retries")
      print("Claude connection failure, retrying...")
      time.sleep(sleepseconds * trycount)
      continue
    if response.status != 200 or response.reason != "OK":
      message = ""
      try:
        data = json.loads(response.read())
        if "error" in data and "message" in data["error"]:
          message = ": " + data["error"]["message"]
      except:
        pass
      trycount += 1
      if conn: conn.close()
      if trycount > max_retries:
        return llm_error("Claude API error " + str(response.status) + " " + str(response.reason) + message)
      print("Claude API failure, retrying:", str(response.status), str(response.reason) + message)
      time.sleep(sleepseconds * trycount)
    else:
      break

  rawdata = response.read()
  conn.close()
  try:
    data = json.loads(rawdata)
  except KeyboardInterrupt:
    raise
  except:
    return llm_error("Claude response is not valid JSON: " + str(rawdata))

  if "content" not in data:
    return llm_error("Claude response has no content: " + str(rawdata))

  utils.debug_print("claude response:", data, flag=debug)
  res = ""
  for el in data["content"]:
    if "text" in el:
      res += el["text"].strip()
  return res


# ======== gpt ========

def call_gpt(version, sentences, sysprompt, max_tokens, think=False):
  try:
    sf = open(gpt_secrets_file, "r")
    txt = sf.read()
    sf.close()
  except:
    return llm_error("Could not read GPT API key file: " + str(gpt_secrets_file))
  try:
    data = json.loads(txt)
  except:
    return llm_error("Could not parse JSON in GPT API key file: " + str(gpt_secrets_file))
  if "gpt_key" not in data or not data["gpt_key"]:
    return llm_error("Could not find 'gpt_key' in: " + str(gpt_secrets_file))
  key = data["gpt_key"]

  if version.startswith("gpt-5"):
    baseurl = "/v1/responses"
    messages = []
    if sysprompt:
      messages.append({"role": "system", "content": [{"type": "input_text", "text": sysprompt}]})
    messages.append({"role": "user", "content": [{"type": "input_text", "text": sentences}]})
    effort = "medium" if think else "none"
    call = {
      "model": version,
      "input": messages,
      "text": {"verbosity": "low", "format": {"type": "text"}},
      "reasoning": {"effort": effort}
    }
    if max_tokens:
      call["max_output_tokens"] = max_tokens
  else:
    baseurl = "/v1/chat/completions"
    messages = []
    if sysprompt:
      messages.append({"role": "system", "content": sysprompt})
    messages.append({"role": "user", "content": sentences})
    call = {
      "model": version,
      "messages": messages,
      "seed": seed,
      "temperature": temperature
    }
    if max_tokens:
      call["max_tokens"] = max_tokens

  utils.debug_print("gpt call", call, flag=calldebug)
  calltxt = json.dumps(call)

  trycount = 0
  while True:
    host = "api.openai.com"
    conn = http.client.HTTPSConnection(host, timeout=timeout)
    try:
      conn.request("POST", baseurl, calltxt,
                   headers={
                     "Host": host,
                     "Content-Type": "application/json",
                     "Authorization": "Bearer " + key
                   })
      response = conn.getresponse()
    except KeyboardInterrupt:
      raise
    except:
      trycount += 1
      if conn: conn.close()
      if trycount > max_retries:
        return llm_error("GPT connection failed after " + str(max_retries) + " retries")
      print("GPT connection failure, retrying...")
      time.sleep(sleepseconds * trycount)
      continue
    if response.status != 200 or response.reason != "OK":
      message = ""
      try:
        data = json.loads(response.read())
        if "error" in data and "message" in data["error"]:
          message = ": " + data["error"]["message"]
      except:
        pass
      trycount += 1
      if conn: conn.close()
      if trycount > max_retries:
        return llm_error("GPT API error " + str(response.status) + " " + str(response.reason) + message)
      print("GPT API failure, retrying:", str(response.status), str(response.reason) + message)
      time.sleep(sleepseconds * trycount)
    else:
      break

  rawdata = response.read()
  conn.close()
  try:
    data = json.loads(rawdata)
  except KeyboardInterrupt:
    raise
  except:
    return llm_error("GPT response is not valid JSON: " + str(rawdata))

  utils.debug_print("gpt response:", data, flag=debug)

  if version.startswith("gpt-5"):
    if "output" not in data:
      return llm_error("GPT response has no 'output'")
    for el in data["output"]:
      if "content" in el and el.get("type") == "message":
        for cel in el["content"]:
          if "text" in cel and cel.get("type") == "output_text":
            return cel["text"]
    return llm_error("GPT response structure not understood: " + str(data))
  else:
    if "choices" not in data:
      return llm_error("GPT response has no 'choices'")
    res = ""
    for el in data["choices"]:
      if "message" in el:
        msg = el["message"]
        if "content" in msg:
          res += msg["content"]
      elif "text" in el:
        if res: res += "\n"
        res += el["text"].strip()
    return res


# ======== deepseek ========

# https://api-docs.deepseek.com/
# DeepSeek uses an OpenAI-compatible chat completions API.

def call_deepseek(version, sentences, sysprompt, max_tokens, think=False):
  try:
    sf = open(deepseek_secrets_file, "r")
    key = sf.read().strip()
    sf.close()
  except:
    return llm_error("Could not read DeepSeek API key file: " + str(deepseek_secrets_file))

  # Switch to reasoning model when think is requested.
  if think and version == "deepseek-chat":
    version = "deepseek-reasoner"

  messages = []
  if sysprompt:
    messages.append({"role": "system", "content": sysprompt})
  messages.append({"role": "user", "content": sentences})
  call = {
    "model": version,
    "messages": messages,
    "stream": False
  }
  # deepseek-reasoner does not support temperature or max_tokens.
  if version != "deepseek-reasoner":
    call["temperature"] = temperature
    if max_tokens:
      call["max_tokens"] = max_tokens

  utils.debug_print("deepseek call", call, flag=calldebug)
  calltxt = json.dumps(call)

  trycount = 0
  while True:
    host = "api.deepseek.com"
    conn = http.client.HTTPSConnection(host, timeout=timeout)
    try:
      conn.request("POST", "/v1/chat/completions", calltxt,
                   headers={
                     "Content-Type": "application/json",
                     "Authorization": "Bearer " + key
                   })
      response = conn.getresponse()
    except KeyboardInterrupt:
      raise
    except:
      trycount += 1
      if conn: conn.close()
      if trycount > max_retries:
        return llm_error("DeepSeek connection failed after " + str(max_retries) + " retries")
      print("DeepSeek connection failure, retrying...")
      time.sleep(sleepseconds * trycount)
      continue
    if response.status != 200 or response.reason != "OK":
      message = ""
      try:
        data = json.loads(response.read())
        if "error" in data and "message" in data["error"]:
          message = ": " + data["error"]["message"]
      except:
        pass
      trycount += 1
      if conn: conn.close()
      if trycount > max_retries:
        return llm_error("DeepSeek API error " + str(response.status) + " " + str(response.reason) + message)
      print("DeepSeek API failure, retrying:", str(response.status), str(response.reason) + message)
      time.sleep(sleepseconds * trycount)
    else:
      break

  rawdata = response.read()
  conn.close()
  try:
    data = json.loads(rawdata)
  except KeyboardInterrupt:
    raise
  except:
    return llm_error("DeepSeek response is not valid JSON: " + str(rawdata))

  utils.debug_print("deepseek response:", data, flag=debug)

  if "choices" not in data:
    return llm_error("DeepSeek response has no 'choices': " + str(rawdata))
  res = ""
  for el in data["choices"]:
    if "message" in el:
      msg = el["message"]
      if "content" in msg and msg["content"]:
        res += msg["content"]
  return res


# ======== utilities ========

def llm_error(msg):
  print("LLM error:", msg)
  return None


# =========== the end ==========
