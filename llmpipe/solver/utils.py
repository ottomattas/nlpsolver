# Small utilities for the nlpsolver.
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

import json
import globals


def debug_print(label, format="placeholder1", data="placeholder2"):
  if not globals.options["debug_print_flag"]: return
  print()
  print(label, end='')
  if format != "placeholder1" and data == "placeholder2":
    data = format
    format = "placeholder1"
  if data == "placeholder2":
    print()
    return
  if format and type(data) == list:
    print(":")
    for el in data:
      if el and type(el) == list:
        print("  [")
        for subel in el:
          print("   ", subel)
        print("  ]")
      else:
        print(" ", el)
  elif type(data) == list:
    print(":")
    for el in data:
      print(" ", el)
  elif type(data) == dict:
    print(":")
    for key in data:
      print(" ", key, ":", data[key])
  else:
    print(" :", data)


def clause_list_to_json(clauselist):
  reslst = []
  for clause in clauselist:
    clauserep = []
    if "@logic" in clause: logic = clause["@logic"]
    if "@question" in clause: logic = clause["@question"]
    if not logic: continue
    if logic[0] in ["or", "and"]:
      newlogic = []
      for atom in logic:
        newatom = json.dumps(atom, separators=(',', ':'))
        newlogic.append(newatom)
      if len(logic) > 3:
        logicstr = ",\n    ".join(newlogic)
      else:
        logicstr = ", ".join(newlogic)
      logicstr = ("[" + logicstr + "]")
    else:
      newlogic = json.dumps(logic, separators=(',', ':'))
      logicstr = newlogic
    clauserep.append("{")
    count = 0
    if "@logic" in clause: clauserep.append("\"@logic\": " + logicstr)
    if "@question" in clause: clauserep.append("\"@question\": " + logicstr)
    for key in clause:
      if not (key in ["@logic", "@question", "@askvars", "@where_query"]):
        clauserep.append(",\n " + json.dumps(key) + ": " + json.dumps(clause[key]))
        count += 1
    clauserep.append("}")
    clausestr = "".join(clauserep)
    reslst.append(clausestr)
  res = "[\n" + ",\n".join(reslst) + "\n]"
  return res


# =========== the end ==========
