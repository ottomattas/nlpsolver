#!/usr/bin/env python3

# Analyzing gpt parsing results
#
# Run the program and it will run all the tests
# here and return the results.
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

import time
import sys
import json


# ======== configuration ======

test_files=["tests_wikipedia_parseresults_converted.py"]
#test_files=["llm_tests_hans_results_converted.py"]
#test_files=["llm_tests_allen_results_converted.py"]
#test_files=["llm_tests_core1_results_converted.py"]
#test_files=["gpt/promptdata.py"]

known_connectives=['forall', 'exists', 'implies', 'and', 'not', 'or', 'xor','question','ask']
known_preds=['isa','has type','has actor','rel2','has property', 'have', 'had', 'has', 
    'property of', 'has target','<','>','=','$value', 
    'has attitude', 'had attitude', 'has time', 'has manner', 'has location', 'has goal',
    'is able', 'typical activity', 'exist', 'is set of', '$count', 'member', '$measure1']

debug=True

# ======== testing program ======

collected_preds=[]


def main():
  global test_files
  options={}
  alltests=[]
  for testfile in test_files:
    try:
      f=open(testfile,"r")
      s=f.read()      
    except:
      print("Could not read test file",testfile)  
      return
    f.close()
    try:  
      tests=eval(s)
    except BaseException as err:
      print("Error parsing test file",testfile)
      print()
      raise(err)
      return
    alltests.append([testfile,tests])  
  allresults=[] 
  for test in alltests:  
    print("\n=== running analysis "+test[0]+" ===\n")
    results=single_run_tests(test[1])
    allresults.append(results)



def single_run_tests(tests):
  global collected_preds
  print("Starting to run",len(tests),"tests")
  testcount=0
  for test in tests:    
    testcount+=1
    print("test",test)
    if len(test)<3: continue
    data=test[2]
    if not data: continue
    #collected_preds=[]
    analyze_logic(data)
    print("collected_preds",collected_preds)

def analyze_logic(data,interm=False):
  global collected_preds
  if not data: return
  if type(data)!=list: return
  #if interm and data[0] in known_connectives:
  #   print("***",data)      
  #   sys.exit(0)
  if data[0] in known_connectives:
    for el in data[1:]:
      analyze_logic(el,interm)
  else:
    if (data[0] not in known_preds) and (data[0] not in collected_preds):
      collected_preds.append(data[0])
    for el in data[1:]:
      analyze_logic(el,True)    




# ========= llm connection =========


def debug_print(a,b):  
  if debug:
    print(a,b)

def show_error(a):
  print("Error:",a)
  sys.exit(0)  



# ========= run the program ======

if __name__ == "__main__":        
  main()  


# ========= the end =============

# new preds collected from core1
# ['$probability', 'A', 'Y', 'somewhat', 'very', 'bought', 'set of', 'part of', 'has name', 'has instrument']

# new preds collected from allen
# ['activity', 'pay', 'most']

# new preds collected from hans
# ['has beneficiary', 'has intermediary', 'has means', 'has object', 'has instrument', 'knew']

# new preds collected from wiki
# 
# ['set of', 'part of', 'coextensive with', 'has direction', 'has name', 'flows direction', 
# 'branch', 'made of', 'found in', 'usually', 'has material', 'can', 'to', 'jet engine', 'perkistant',
#  'rocket engine', 'range', 'lays', '>=', '<=', 'use', 'has result']

# ['part of', 'coextensive with', 'set of', 'has name', 'made of', 'found in', 'usually', 'has material', 'can',
#  'has time period', 'has part', 'can do', 'set', 'Z', 'lays', 'range', '5.5 cm bee hummingbird', '2.8 m common ostrich', 
# 'activity', '>=', '<=', 'use', 'has ability']

# pred instead of isa like ["jet engine", "Y"]

# """An askele or aeskele, informally askel, is a fixed-wing calestene that is propelled forward by thrust from a jet engine, perkistant, or rocket engine. 
# Askeles come in a variety of sizes, shapes, and wing configurations. 
# Askeles are not red. Askeles can do different things. Calestenes are propelled somehow. Serkisenes are black. Askele can swim?""",None,
# ["and", ["forall", "X", ["implies", ["isa", "askele", "X"], ["and", ["isa", "fixed-wing calestene", "X"], 
# ["exists", "Y", ["or", ["rel2", "propelled by", "X", ["jet engine", "Y"]], ["rel2", "propelled by", "X", ["perkistant", "Y"]], 
# ["rel2", "propelled by", "X", ["rocket engine", "Y"]]]]]]],
 # ["forall", "X", ["implies", ["isa", "askele", "X"],
# ["exists", "Y", ["and", ["isa", "size", "Y"], ["isa", "shape", "Y"], ["isa", "wing configuration", "Y"]]]]], 
 #["forall", "X", ["implies", ["isa", "askele", "X"], ["not", ["has property", "X", "red"]]]], 
 # ["forall", "X", ["implies", ["isa", "askele", "X"], ["exists", "Y", ["and", ["isa", "activity", "Y"],
 # ["has actor", "Y", "X"]]]]], ["forall", "X", ["implies", ["isa", "calestene", "X"], 
 # ["exists", "Y", ["rel2", "propelled by", "X", "Y"]]]], 
 # ["forall", "X", ["implies", ["isa", "serkisene", "X"], ["has property", "X", "black"]]], ["question", 
 # ["exists", "X", ["and", ["isa", "askele", "X"], ["exists", "Y", ["and", ["isa", "activity", "Y"], ["has type", "Y", "swim"], ["has actor", "Y", "X"]]]]]]]],