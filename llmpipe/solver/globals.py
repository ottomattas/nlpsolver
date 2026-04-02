# Configuration and other globals for the nlpsolver.
#
#-----------------------------------------------------------------
# Copyright 2022 Tanel Tammet (tanel.tammet@gmail.com)
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

# Absolute path to llmpipe/ (parent of this file's directory), so that all
# data-file paths work regardless of the working directory at runtime.
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ======= configuration globals ======

# global vars changed by command line options

options={
  "debug_print_flag":False, # if True, print a lot of details of the parsing process (turn on by -debug)
  "prover_print_flag":False, # if True, print prover logic input and output
  "prover_nosolve_flag":False, # if True, attempt to solve the question, if False, just output logic
  "use_cache_flag":False, # if True, use cache for GK, if False, do not use cache
  "prover_rawresult_flag":False, # if True, give a raw json result (handled by procproofs.py)
  "prover_explain_flag":False, # if True, output nlp explanation
  "show_logic_flag":False, # if True, output also conventional logic for sentences and nlp explanation
  "show_prover_flag":False, # if True, show prover input and output
  "usekb_flag": False, #if True, use shared memory kb
  "forward_flag":False, # if True, use forward search
  "backward_flag":False, # if True, use backward search
  "nocontext_flag":False, # if True, do not insert context information (time, situation) into logic
  "noexceptions_flag":False, # if True, do not insert exception information (blockers) into logic
  "noproptypes_flag":False,  # if True, remove prop strength and type information
  "nokb_flag":True,  # if True, do not use the shared memory knowledge base
  "prover_axiomfiles":False,  # if not False, use these as axioms instead of the default prover_axiomfile below
  "prover_print":False,  # if not False, use the argument integer for gk printout level, instead of the default
  "prover_strategy":False,  # if not False, use the argument as a gk strategy file, instead of the default
  "prover_seconds":2,  # give the prover this many seconds, instead of the default 1
  "prover_seconds_cli":False,  # True when -seconds was given on CLI (disables auto-estimation)
  # LLM response caching: ON by default.
  # The cache key covers provider, version, temperature, seed, max_tokens,
  # sysprompt and input text, so a cached result is only reused when every
  # call parameter is identical.  Set to False or pass -nollmcache to disable.
  "use_llm_cache_flag": True,
  # Semantic normalisation: ON by default.
  # Applies antonym folding and canonical word substitution to GK clauses
  # before they are passed to the prover.  Set to True or pass -nosemnormal
  # to disable.
  "nosemnormal_flag": False,
  # LLM reasoning/thinking mode: OFF by default.
  # When True, enables medium reasoning effort (GPT: reasoning_effort=medium;
  # Claude: extended thinking; Gemini: thinkingConfig, requires 2.5+ model).
  "think_flag": False,
  "json_flag": False,   # if True, show logic in raw JSON; if False, use traditional syntax
  "show_details_flag": False, # if True, show stage-1/2 JSON and prover input/output
  "gkin_file": None,          # if set, save GK input to this file
}

# cache

cache_db_name=os.path.join(_root, "cache.db")

# solving logic with a prover
prover_fname=os.path.join(_root, "../gk/gk")  # gk binary
prover_datafolder=os.path.join(_root, "../gk")  # where gk_name_number.txt etc are located
memkb_name="1000"  # in-memory knowledge base name (number)
prover_infile="gk_infile.js"
prover_axiomfile=os.path.join(_root, "axioms_std.js")
prover_params=["-defaults","-confidence","0.1","-keepconfidence","0.1"] # additional prover params, always appended
usekb_prover_params=["-usekb","-confidence","0.1","-keepconfidence","0.1"] # additional prover params, always appended


def set_global_options(newoptions):
  global options
  for key in newoptions:
    if key in options:
      options[key]=newoptions[key]
    else:
      print("Error: option",key,"is not recognized.")
      sys.exit(0)


# =========== the end ==========
