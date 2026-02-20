# Pretty-printing for stage-1 ASU JSON, stage-2 logic JSON, and GK clause lists.
#
# Primary entry points:
#   pp_stage1(obj, file=None)  -- print pretty stage-1 output
#   pp_stage2(obj, file=None)  -- print pretty stage-2 output
#   pp_logic(obj, file=None)   -- print pretty GK clause list
#   pp_str(obj)                -- return pretty string (used by all three above)
#
# Style B layout:
#   - A list or dict is kept on one line when it fits within 100 columns.
#   - When it must expand, the opening bracket [ or { is NOT on its own line:
#     the first element / first key follows immediately after the bracket.
#   - Subsequent list elements are indented at (depth+1)*2 columns.
#   - Subsequent dict keys are indented to align with the first key
#     (one column right of the opening {).
#   - Closing brackets ] and } go on their own line at depth*2, but
#     consecutive closing-bracket-only lines are merged into one line.
#
# Global flag:
#   noquotes = False  (default) -- standard JSON-style quoted strings
#   noquotes = True             -- no quotation marks; spaces in strings
#                                  replaced with underscores (more readable)
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

import json

# Global mode flag.  Set to True to suppress quotes and replace spaces with _.
noquotes = False


# ======== public API ========

def pp_stage1(obj, file=None):
  """Pretty-print a stage-1 ASU JSON object."""
  print(pp_str(obj), file=file)


def pp_stage2(obj, file=None):
  """Pretty-print a stage-2 logic JSON object."""
  print(pp_str(obj), file=file)


def pp_logic(obj, file=None):
  """Pretty-print a GK clause list (output of rawlogic_convert)."""
  print(pp_str(obj), file=file)


def pp_str(obj):
  """Return a pretty-printed string for obj, using the global noquotes setting."""
  raw = _pp(obj, 0, noquotes)
  return _merge_closing(raw)


# ======== core recursive formatter ========

def _pp(obj, depth, nq, col=None):
  """Return a formatted string for obj (no leading indent — caller adds it).

  depth  -- current nesting depth (controls closing-bracket indent)
  nq     -- noquotes mode flag
  col    -- column at which this value starts; used for the 100-char line check.
             Defaults to depth*2 (the natural indentation column for this depth).
  """
  if col is None:
    col = depth * 2

  # Try the compact (single-line) form first.
  compact = _compact(obj, nq)
  if col + len(compact) <= 100:
    return compact

  ind       = "  " * depth        # indentation for closing bracket / brace
  child_ind = "  " * (depth + 1)  # indentation for child elements (items 2..n)

  if isinstance(obj, list):
    if not obj:
      return "[]"
    # First element on the same line as [; subsequent at child_ind.
    first_str = _pp(obj[0], depth + 1, nq, col=col + 1)
    if len(obj) == 1:
      return "[" + first_str + "\n" + ind + "]"
    rest = [child_ind + _pp(item, depth + 1, nq) for item in obj[1:]]
    return "[" + first_str + ",\n" + ",\n".join(rest) + "\n" + ind + "]"

  elif isinstance(obj, dict):
    if not obj:
      return "{}"
    # First key starts right after { (no space); subsequent keys aligned below it.
    key_col = col + 1
    key_ind = " " * key_col
    pairs   = list(obj.items())
    parts   = []
    for i, (k, v) in enumerate(pairs):
      kp = _fmtkey(k, nq)
      vs = _pp(v, depth + 1, nq, col=key_col + len(kp))
      if i == 0:
        parts.append(kp + vs)
      else:
        parts.append(key_ind + kp + vs)
    return "{" + parts[0] + ",\n" + ",\n".join(parts[1:]) + "\n" + ind + "}"

  else:
    # Scalar that didn't fit on one line (very long string); return as-is.
    return compact


# ======== closing-bracket merger ========

def _merge_closing(s):
  """Merge consecutive lines that consist only of closing brackets ] and }.

  Turns e.g.
    ...last element
    ]
  }
  ]
  into
    ...last element
    ]}]
  which saves lines without losing structure information.
  Only merges when BOTH the current line and the previous result line are
  pure closing-bracket lines (so inner ] lines are left on their own).
  """
  lines  = s.split("\n")
  result = []
  for line in lines:
    stripped = line.strip()
    is_closing = bool(stripped) and all(c in "]}," for c in stripped) and any(c in "]}" for c in stripped) and "," not in stripped
    if is_closing and result:
      prev = result[-1].strip()
      prev_is_closing = bool(prev) and all(c in "]}" for c in prev)
      if prev_is_closing:
        result[-1] = result[-1] + stripped
        continue
    result.append(line)
  return "\n".join(result)


# ======== compact (single-line) renderer ========

def _compact(obj, nq):
  """Render obj as a compact single-line string."""
  if isinstance(obj, bool):        # bool before int — bool is subclass of int
    return "true" if obj else "false"
  elif obj is None:
    return "null"
  elif isinstance(obj, str):
    return obj.replace(" ", "_") if nq else json.dumps(obj)
  elif isinstance(obj, (int, float)):
    return json.dumps(obj)          # handles int/float precision correctly
  elif isinstance(obj, list):
    sep = ", " if any(isinstance(x, (list, dict)) for x in obj) else ","
    return "[" + sep.join(_compact(x, nq) for x in obj) + "]"
  elif isinstance(obj, dict):
    pairs = [_fmtkey(k, nq) + _compact(v, nq) for k, v in obj.items()]
    return "{" + ", ".join(pairs) + "}"
  else:
    return str(obj)


def _fmtkey(k, nq):
  """Return 'key: ' formatted according to the nq flag."""
  if nq:
    return str(k).replace(" ", "_") + ": "
  else:
    return json.dumps(str(k)) + ": "


# =========== the end ==========
