# Proof result processing for the llm-based nlpsolver.
#
# Entry point: process_proof(proof_result, text=None, logic=None, options=None)
# Called by solve.py after the theorem prover returns its raw result.
# Currently a pass-through stub; real implementations go here.
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


def process_proof(proof_result, text=None, logic=None, options=None):
  """Post-process the raw prover result into a final answer string.

  Arguments:
    proof_result -- raw string returned by prover.call_prover()
    text         -- the original English input (for context)
    logic        -- the logic list that was sent to the prover (for context)
    options      -- the options dict (e.g. to check prover_explain_flag)

  Currently a pass-through stub.  Future implementations may:
    - Parse the raw prover JSON and extract the answer value
    - Convert the answer to a natural-language sentence
    - Produce an English explanation / proof trace when -explain is set
    - Handle multiple answers and rank or format them
    - Distinguish "Unknown" from genuine proof failures

  Returns the final answer string.
  """
  return proof_result


# =========== the end ==========
