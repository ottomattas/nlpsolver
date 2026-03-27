# Proof rendering facade — re-exports from proof_utils, proof_english, proof_logic.
#
# External modules (procproofs.py, proof_explain.py, utils.py, solve.py) import
# from this module.  The actual implementations live in:
#   proof_utils.py   — entity naming, Skolem resolution, render context
#   proof_english.py — atom/clause to English rendering
#   proof_logic.py   — traditional/JSON logic syntax rendering
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
#-----------------------------------------------------------------

# --- proof_utils: entity naming, Skolem resolution, render context ---
from proof_utils import (                                # noqa: F401
  RenderContext, _ctx,
  set_entity_map, get_entity_display,
  get_skolem_type, get_skolem_fn_type,
  compute_ambiguity, compute_skolem_types,
  entity_name,
  _is_skolem_fn, _degree_parts, _is_var_display,
  _indef_article, _ans_display_args,
)

# --- proof_english: atom/clause → English ---
from proof_english import (                              # noqa: F401
  ans_atom_name,
  clause_to_str, block_to_english,
  _atom_to_english, _atom_to_english_negated,
)

# --- proof_logic: traditional/JSON logic syntax ---
from proof_logic import (                                # noqa: F401
  format_clause_logic, format_clause_traditional,
  formula_to_logic,
)
