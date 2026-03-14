#!/usr/bin/env python3
#
# Call an LLM with optional system prompt(s) and input text.
# Uses the same LLM providers, config, and caching as solver/llmcall.py.
#
# Usage examples:
#   python3 ask.py "What is 2+2?"
#   python3 ask.py -llm claude "What is 2+2?"
#   python3 ask.py -p prompt.txt "Some input text"
#   python3 ask.py -p instructions.txt -p examples.txt -f input.txt
#   python3 ask.py -llm deepseek -tokens 4000 -debug "Explain logic."
#
# Flags:
#   -p FILE        System prompt file (repeatable; concatenated in order)
#   -f FILE        Read input text from file instead of command line
#   -llm NAME      LLM provider: gpt, claude, gemini, deepseek
#   -version VER   Model version override
#   -tokens N      Max output tokens
#   -debug         Print prompt/response details
#   -nollmcache    Bypass LLM response cache
#
#-----------------------------------------------------------------
# Copyright 2025 Tanel Tammet (tanel.tammet@gmail.com)
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'solver'))
import llmcall
import globals as g

def main():
  if len(sys.argv) < 2:
    print(__doc__ or "Usage: python3 ask.py [flags] \"input text\"")
    # Print the usage block from the top of this file.
    print("Usage examples:")
    print("  python3 ask.py \"What is 2+2?\"")
    print("  python3 ask.py -llm claude \"What is 2+2?\"")
    print("  python3 ask.py -p prompt.txt \"Some input text\"")
    print("  python3 ask.py -p instructions.txt -p examples.txt -f input.txt")
    print()
    print("Flags:")
    print("  -p FILE        System prompt file (repeatable; concatenated)")
    print("  -f FILE        Read input text from file")
    print("  -llm NAME      Provider: gpt, claude, gemini, deepseek")
    print("  -version VER   Model version override")
    print("  -tokens N      Max output tokens")
    print("  -debug         Print prompt/response details")
    print("  -nollmcache    Bypass LLM response cache")
    return

  # Parse arguments.
  prompt_files = []
  input_file = None
  llm = None
  version = None
  max_tokens = None
  debug = False
  nollmcache = False
  texts = []

  args = sys.argv[1:]
  i = 0
  while i < len(args):
    a = args[i]
    if a in ("-p", "--p", "-prompt", "--prompt"):
      i += 1
      if i >= len(args):
        print("Error: -p requires a file argument.")
        return
      prompt_files.append(args[i])
    elif a in ("-f", "--f", "-file", "--file"):
      i += 1
      if i >= len(args):
        print("Error: -f requires a file argument.")
        return
      input_file = args[i]
    elif a in ("-llm", "--llm"):
      i += 1
      if i >= len(args):
        print("Error: -llm requires a provider name.")
        return
      llm = args[i]
    elif a in ("-version", "--version"):
      i += 1
      if i >= len(args):
        print("Error: -version requires a version string.")
        return
      version = args[i]
    elif a in ("-tokens", "--tokens"):
      i += 1
      if i >= len(args):
        print("Error: -tokens requires a number.")
        return
      max_tokens = int(args[i])
    elif a in ("-debug", "--debug"):
      debug = True
    elif a in ("-nollmcache", "--nollmcache"):
      nollmcache = True
    else:
      texts.append(a)
    i += 1

  # Build system prompt from -p files.
  sysprompt = ""
  if prompt_files:
    parts = []
    for pf in prompt_files:
      try:
        with open(pf, "r") as f:
          parts.append(f.read().strip())
      except Exception as e:
        print("Error: could not read prompt file " + pf + ": " + str(e))
        return
    sysprompt = "\n\n".join(parts)

  # Build input text from -f file or bare arguments.
  if input_file:
    try:
      with open(input_file, "r") as f:
        input_text = f.read().strip()
    except Exception as e:
      print("Error: could not read input file " + input_file + ": " + str(e))
      return
  elif texts:
    input_text = " ".join(texts)
  else:
    print("Error: no input text. Provide text as argument or use -f FILE.")
    return

  # Configure globals.
  if nollmcache:
    g.set_global_options({"use_llm_cache_flag": False})

  # Debug output.
  if debug:
    llmcall.debug = True
    provider = llm or llmcall.use_llm
    print("--- LLM:", provider)
    if version:
      print("--- version:", version)
    if sysprompt:
      print("--- sysprompt:", sysprompt[:200] + ("..." if len(sysprompt) > 200 else ""))
    print("--- input:", input_text[:200] + ("..." if len(input_text) > 200 else ""))
    print()

  # Call the LLM.
  result = llmcall.call_llm(sysprompt, input_text, llm=llm, version=version,
                            max_tokens=max_tokens)
  if result is None:
    print("Error: LLM returned no response.")
  else:
    print(result)

if __name__ == "__main__":
  main()

# =========== the end ==========
