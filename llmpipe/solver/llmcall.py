# LLM API call functions for the nlpsolver: GPT, Claude, Gemini.
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
import http.client

# ======== configuration ========

# Which LLM to use: "gpt", "claude", or "gemini"
use_llm = "claude"

# Model versions
gptversion = "gpt-5.1"
claudeversion = "claude-sonnet-4-6"
geminiversion = "gemini-2.0-flash"

# API key files (paths relative to the llmpipe/ working directory)
gpt_secrets_file = "../gpt/gpt_secrets.js"
claude_secrets_file = "../gpt/claude_secrets.js"
gemini_secrets_file = "../gpt/gemini_secrets.js"

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

def call_llm(sysprompt, input_text, llm=None, version=None, max_tokens=None):
  """Call the configured LLM with a system prompt and input text.
  llm, version, max_tokens override module-level configuration when given.
  Returns the result string on success, or None on error (error is printed)."""
  llm = llm or use_llm
  max_tokens = max_tokens or default_max_tokens
  try:
    if llm == "claude":
      ver = version or claudeversion
      return call_claude(ver, input_text, sysprompt, max_tokens)
    elif llm == "gemini":
      ver = version or geminiversion
      return call_gemini(ver, input_text, sysprompt, max_tokens)
    else:
      ver = version or gptversion
      return call_gpt(ver, input_text, sysprompt, max_tokens)
  except KeyboardInterrupt:
    raise
  except Exception as e:
    return llm_error("unexpected error calling LLM: " + str(e))


# ======== gemini ========

# https://ai.google.dev/gemini-api/docs/text-generation

def call_gemini(version, sentences, sysprompt, max_tokens):
  try:
    sf = open(gemini_secrets_file, "r")
    key = sf.read().strip()
    sf.close()
  except:
    return llm_error("Could not read Gemini API key file: " + str(gemini_secrets_file))

  baseurl = "/v1beta/models/" + version + ":generateContent"
  call = {
    "contents": [{"parts": [{"text": sentences}]}],
    "generationConfig": {
      "maxOutputTokens": max_tokens,
      "thinkingConfig": {"thinkingLevel": "medium"},
      "temperature": temperature
    }
  }
  if sysprompt:
    call["system_instruction"] = {"parts": [{"text": sysprompt}]}

  calldebug_print("gemini call", call)
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

  debug_print("gemini response:", data)
  res = ""
  for el in data["parts"]:
    if "text" in el:
      res += el["text"].strip()
  return res


# ======== claude ========

def call_claude(version, sentences, sysprompt, max_tokens):
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
    "temperature": temperature,
    "max_tokens": max_tokens
  }
  if sysprompt:
    call["system"] = [{"type": "text", "text": sysprompt, "cache_control": {"type": "ephemeral"}}]

  calldebug_print("claude call", call)
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

  debug_print("claude response:", data)
  res = ""
  for el in data["content"]:
    if "text" in el:
      res += el["text"].strip()
  return res


# ======== gpt ========

def call_gpt(version, sentences, sysprompt, max_tokens):
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
    effort = "none"
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

  calldebug_print("gpt call", call)
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

  debug_print("gpt response:", data)

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


# ======== utilities ========

def debug_print(a, b=""):
  if debug:
    print(a, b)

def calldebug_print(a, b=""):
  if calldebug:
    print(a, b)

def llm_error(msg):
  print("LLM error:", msg)
  return None


# =========== the end ==========
