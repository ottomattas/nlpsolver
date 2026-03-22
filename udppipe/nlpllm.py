# The llm connections parts of nlpsolver
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

# ==== standard libraries ====

import sys
import os
import time
import json
import http.client

# ==== import other source files ====

# configuration and other globals are in nlpglobals.py
from nlpglobals import *

# small utilities are in nlputils.py
from nlputils import *

# proper logic part is in nlpproperlogic
#from nlpproperlogic import *

# question special handling is in nlpquestion
from nlpquestion import *

# prover calling and prover result conversion parts are in nlpprover.py
from nlpprover import *

# logic simplification is in nlpsimplify
#from nlpsimplify import *

# uncertainty analysis and encoding is in nlpuncertain
#from nlpuncertain import *

#from nlpanswer import *

#from nlpsolver import server_parse

# ======= llm configuration ===

# Which LLM to use: "gpt", "claude", "gemini", or "deepseek"
use_llm = "gpt"

# Model versions
gptversion = "gpt-5.1"
claudeversion = "claude-sonnet-4-6"
geminiversion = "gemini-2.5-flash-lite"
deepseekversion = "deepseek-chat"

# API key files (plain text, one key per file)
_secrets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "secrets")
gpt_secrets_file = os.path.join(_secrets_dir, "gpt_secrets.txt")
claude_secrets_file = os.path.join(_secrets_dir, "claude_secrets.txt")
gemini_secrets_file = os.path.join(_secrets_dir, "gemini_secrets.txt")
deepseek_secrets_file = os.path.join(_secrets_dir, "deepseek_secrets.txt")

# Call parameters
temperature = 0
seed = 1234
default_max_tokens = 4000
sleepseconds = 2
llm_timeout = 60
max_retries = 3

# ======= other configuration globals ===


debug=True # set to True to get a printout of data, call and result


gpt_simplify_prompt="""Simplify, maximally shorten and split the sentence after colon to shortest possible separate subsentences, to make it understandable for children. 
Replace pronouns like 'they','it','he' etc in the result with nouns and proper nouns present in the result, like 'Birds can fly. Birds have feathers' instead of 
'Birds can fly. They have feathers.'. Prepend the character star * to concrete objects and the character plus + to general nouns, 
like 'Birds+ can fly. A stork* ate a frog*.':  """

#gpt_model="gpt-3.5-turbo"
gpt_simplify_prompt="""Simplify, maximally shorten and split the sentence after colon to shortest possible separate subsentences, to make it understandable for children. 
Replace pronouns like 'they','it','he','she' in the result with nouns and proper nouns present in the result, 
like 'Birds can fly. Birds have feathers' instead of 
'Birds can fly. They have feathers':  """

gpt_simplify_prompt="""Simplify, maximally shorten and split the sentence after colon to shortest possible separate subsentences, to make it understandable for children. 
Replace pronouns like 'they','it','he','she' in the result with nouns and proper nouns present in the result. For example,
instead of 'Birds can fly. They have feathers.' say 'Birds can fly. Birds have feathers.' : """


# --- direct solving prompts ----

gpt_solve_boolean_prompt_assumptions="""Answer the question with either "True" or "False" or "Unknown", without giving any explanations
or additional information. 

Base your answer only on these assumptions: %assumptions% 
"""

gpt_solve_boolean_prompt_assumptions="""Answer the question with either "True" or "False" or "Unknown", without giving any explanations
or additional information. Base your answer only on the assumption sentences given before the question at the end.
"""
gpt_solve_boolean_prompt_assumptions="""You have to find whether the question is logically derivable from the given assumptions.
Answer the question with either "True" or "False" or "Unknown", without giving any explanations or additional information. 
Base your answer only on the assumption sentences given before the question at the end."""

#Question: """

#gpt_solve_prompt_noassumptions="""Answer the question maximally shortly.  
#
#If the question asks for truth value, answer either "True" or "False" or "Unknown", without any explanations
#or additional information. If the question asks for an object or a conjunction or disjunction of objects, just give the proper objects as given in the text, 
#optionally separated by "and" or "or". Do not insert any other words except "and" and "or" into the answer.
#Examples of answers: "John", "John and Mike", "The red car", "A box or a ball". 
#"""

gpt_solve_boolean_prompt_noassumptions="""Answer the question with either "True" or "False" or "Unknown", without any explanations
or additional information. 
"""
gpt_solve_boolean_prompt_noassumptions="""You have to find whether the question is logically true, false or uncertain. 
Answer the question with either "True" or "False" or "Unknown", without giving any explanations or additional information. 
"""


gpt_solve_prompt_assumptions="""Answer the question maximally shortly, without any explanations
or additional information.  

If the question asks for an object or a conjunction or a disjunction of objects, just give the proper objects exactly as given in the text, 
optionally separated by "and" or "or". 

Do not insert any other words except "and" and "or" into the answer.

Examples of answers: "John", "John and Mike", "The red car", "A box or a ball". 

Base your answer only on these assumptions: %assumptions% 
"""

#gpt_solve_prompt="""Answer the question maximally shortly. If the question asks for truth value, answer either "True" or "False" or "Unknown", without any explanations
#or additional information. If the question asks for an object or a conjunction or disjunction of objects, just give the proper objects as given in the text, 
#optionally separated by "and" or "or". Examples of answers: "John", "John and Mike", "The red car", "A box or a ball". 
#
#Question: """




min_simplification_length = 6

# ======= globals used and changed during work ===


#constant_nr=0 # new constants created add a numeric suffic, incremented
#definition_nr=0 # new definitions created add a numeric suffic, incremented

# ========= llm connection =========

def llm_simplify(text):
  debug_print("=== llm simplification ===")  
  parsed = server_parse(text)
  if not parsed or "doc" not in parsed:
    show_error("ud parsing failed")
    sys.exit(0)
  doc=parsed["doc"]  
  sentlist=[]
  for sentence in doc: 
    sentencetext=doc_to_original_sentence(sentence) 
    if is_question_sentence(sentence):
      sentlist.append([sentencetext,sentencetext])
      debug_print("not simplified",sentencetext)
    elif len(sentence)<min_simplification_length:
      sentlist.append([sentencetext,sentencetext])
      debug_print("not simplified",sentencetext)  
    else:         
      debug_print("original sentence",sentencetext)
      newtext=call_llm(gpt_simplify_prompt,sentencetext)
      sentlist.append([sentencetext,newtext])
      debug_print("simplified sentence",newtext)  
  res=""
  for el in sentlist:
    res+=el[1]+" "
  debug_print("final simplification result",res)  
  return [res,sentlist]


def old_llm_solve(text):
  origtext=text
  debug_print("=== pure llm solving ===")  
  #result=call_gpt(text,gpt_solve_prompt)
  splitted=text.split(".")
  print(splitted)
  if len(splitted)<2:
    sysprompt=gpt_solve_boolean_prompt_noassumptions    
  else:      
    assumptions=splitted[:-1]
    assumptionstext=".".join(assumptions)    
    text=splitted[-1].strip()
    words=text.split(" ")
    firstword=words[0].strip().lower()
    if firstword in ["who","whom","which","what","where","how","when"]:
      sysprompt=gpt_solve_prompt_assumptions.replace("%assumptions%",assumptionstext+".")
    else:
      sysprompt=gpt_solve_boolean_prompt_assumptions.replace("%assumptions%",assumptionstext+".")        
  text=origtext    
  #print("sysprompt:",sysprompt)
  #print("text:",text)
  #exit(0)
  result=call_llm(sysprompt,text)
  return result

def llm_solve(text):
  origtext=text
  debug_print("=== pure llm solving ===")  
  #result=call_gpt(text,gpt_solve_prompt)
  splitted=text.split(".")
  #print(splitted)
  if len(splitted)<2:
    #sysprompt=gpt_solve_boolean_prompt_noassumptions 
    assumptionstext=""
    sysprompt=""
    text=origtext
  else:      
    assumptions=splitted[:-1]
    assumptionstext=".".join(assumptions)    
    text=splitted[-1].strip()
    words=text.split(" ")
    firstword=words[0].strip().lower()
    if firstword in ["who","whom","which","what","where","how","when"]:
      sysprompt=gpt_solve_prompt_assumptions.replace("%assumptions%",assumptionstext+".")
    else:
      sysprompt=gpt_solve_boolean_prompt_assumptions.replace("%assumptions%",assumptionstext+".")        
  #text=origtext
  text=text[0].lower()+text[1:]    
  #print("text","!"+text+"!")
  #sys.exit(0)

  # used for hans and Allen:
  """
  newtext="You have to check whether a question is logically derivable from the assumption. "
  newtext=newtext+"Answer True, False or Unknown, without any additional explanations or information. "+"Assume the following: "
  newtext=newtext+assumptionstext+". Based on only this knowledge, is it true, false or unknown that "
  newtext=newtext+text# +" Answer True, False or Unknown, without any additional explanations or information." 
  """

  # used for core:
  if assumptionstext:
    newtext="You have to check whether a question is logically derivable from the assumptions. "
    newtext=newtext+"Answer True, False or Unknown, without any additional explanations or information. "+"Assume only the following: ' "
    newtext=newtext+assumptionstext+"'. Based on only this knowledge, is it true, false or unknown that "
    newtext=newtext+text# +" Answer True, False or Unknown, without any additional explanations or information." 
  else:
    newtext="You have to check whether a question is logically true. "
    newtext=newtext+"Answer True, False or Unknown, without any additional explanations or information. Is it true, false or unknown that "
    newtext=newtext+text# +" Answer True, False or Unknown, without any additional explanations or information." 


  sysprompt=""
  #print("sysprompt:",sysprompt)
  #print("newtext:",newtext)
  #exit(0)
  result=call_llm(sysprompt,newtext)
  return result


def llm_parse_solve(text):
  origtext=text
  debug_print("=== parse llm solving ===")    
  sysprompt=logifyprompt
  #debug_print("sysprompt:",sysprompt)
  #debug_print("text:",text)
  #exit(0)
  result=call_llm(sysprompt,text)
  debug_print("result:",result)
  try:
    jresult=json.loads(result)
  except:  
    return "Json parse error"
  debug_print("jresult:",jresult)
  result=llm_parsed_solve(jresult)
  return result


def llm_parsed_solve(logic): 
  #print("logic",logic)
  if type(logic)==str:
    try:
      jresult=json.loads(logic)
    except:  
      return "Json parse error"
  else:
    jresult=logic  
  debug_print("jresult",jresult)
  clauses=make_clause_list_from_llm(jresult)
  debug_print("clauses",clauses)
  rawresult=call_prover(clauses)
  debug_print("rawresult",rawresult)
  try:
    jresult=json.loads(rawresult)
  except:
    return "Unknown"  
  if type(jresult)!=dict:
    return "Unknown"
  if "result" not in jresult:
    return "Unknown"
  if jresult["result"]!="answer found":
    return "Unknown"
  if "answers" not in jresult:
    return "Unknown"
  for answer in jresult["answers"]:
    return answer["answer"]


def make_clause_list_from_llm(jresult):
  #print("jresult 2",jresult)
  if type(jresult)!=list:
    return None
  if len(jresult)<2:
    return None
  if jresult[0] in ["xor"] and not logic_contains_el(jresult,"question"):
    jresult=["or"]+jresult[1:]
  if jresult[0] in ["or","xor","forall","exists"] and not logic_contains_el(jresult,"question"):
    jresult=["question",jresult]
  if jresult[0]=='question':
    jresult=["and",jresult]
  elif jresult[0]!='and':
    return None
  clauses=[]
  pureclauses=[]
  question=[]
  definition=None
  finalquestion=None
  #print("jresult 3",jresult)
  for el in jresult[1:]:
    #debug_print("el",el)
    if type(el)!=list: continue
    if len(el)<2: continue
    if el[0]=="question":
      #tmp=process_llm_question(el[1])      
      definition={"@logic":[["$defquestion"],"<=>",el[1]]}      
      finalquestion={"@question": ["$defquestion"]}
    else:
      clause={"@logic": el}
      clauses.append(clause)
      pureclauses.append(el)
  if not finalquestion:
    nclauses=clauses[0]["@logic"]
    if type(pureclauses[0])==list:
      pureclauses=["and"]+pureclauses
    definition={"@logic":[["$defquestion"],"<=>",pureclauses]}
    finalquestion={"@question": ["$defquestion"]}
    clauses=[definition,finalquestion] 
  else:  
    clauses.append(definition)    
    clauses.append(finalquestion)
  #print("** clauses cp1",clauses)  
  clauses=fix_llm_logic(clauses)
  #print("** clauses cp2",clauses)
  classes=get_isa_classes(clauses,[])
  if classes:
    for el in classes:
      tmp={"@logic":["exists",["S"],["isa",el,"S"]]}
      clauses=[tmp]+clauses
  #print("** clauses cp3",clauses)
  #print("** classes",classes)
  #print()
  return clauses

def get_isa_classes(logic,classes):
  if type(logic)==dict: 
    for key in logic:
      tmp=get_isa_classes(logic[key],classes) 
      for x in tmp:
        if x not in classes: classes=[x]+classes
    return classes    
  if type(logic)!=list: return classes
  if len(logic)>2 and logic[0]=="isa" and type(logic[1]==str):
    if logic[1] in classes: return classes
    else: return [logic[1]]+classes
  for el in logic:
    tmp=get_isa_classes(el,classes) 
    for x in tmp:
      if x not in classes: classes=[x]+classes
  return classes

#def process_llm_question(question):
#  if 
"""
text:  The student who the senators thanked stopped the scientist . The scientist stopped the student ?
result: ["and",   ["exists", "S1", ["and",     ["isa", "student", "S1"],     ["exists", "A1", ["and",       ["isa", "activity", "A1"],       ["has type", "A1", "thank"],       ["has actor", "A1", "senators"],       ["has target", "A1", "S1"]     ]],     ["exists", "A2", ["and",       ["isa", "activity", "A2"],       ["has type", "A2", "stop"],       ["has actor", "A2", "S1"],       ["has target", "A2", "scientist"]     ]]   ]],   ["question", ["exists", "A3", ["and",     ["isa", "activity", "A3"],     ["has type", "A3", "stop"],     ["has actor", "A3", "scientist"],     ["has target", "A3", "student"]   ]]] ] 
jresult: ['and', ['exists', 'S1', ['and', ['isa', 'student', 'S1'], ['exists', 'A1', ['and', ['isa', 'activity', 'A1'], ['has type', 'A1', 'thank'], ['has actor', 'A1', 'senators'], ['has target', 'A1', 'S1']]], ['exists', 'A2', ['and', ['isa', 'activity', 'A2'], ['has type', 'A2', 'stop'], ['has actor', 'A2', 'S1'], ['has target', 'A2', 'scientist']]]]], ['question', ['exists', 'A3', ['and', ['isa', 'activity', 'A3'], ['has type', 'A3', 'stop'], ['has actor', 'A3', 'scientist'], ['has target', 'A3', 'student']]]]]
clauses: [{'@logic': ['exists', ['S1'], ['and', ['isa', 'student', 'S1'], ['exists', ['A1'], ['and', ['isa', 'activity', 'A1'], ['has type', 'A1', 'thank'], ['has actor', 'A1', 'senators'], ['has target', 'A1', 'S1']]], ['exists', ['A2'], ['and', ['isa', 'activity', 'A2'], ['has type', 'A2', 'stop'], ['has actor', 'A2', 'S1'], ['has target', 'A2', 'scientist']]]]]}, {'@question': ['exists', ['A3'], ['and', ['isa', 'activity', 'A3'], ['has type', 'A3', 'stop'], ['has actor', 'A3', 'scientist'], ['has target', 'A3', 'student']]]}]
clauselist [{'@logic': ['exists', ['S1'], ['and', ['isa', 'student', 'S1'], ['exists', ['A1'], ['and', ['isa', 'activity', 'A1'], ['has type', 'A1', 'thank'], ['has actor', 'A1', 'senators'], ['has target', 'A1', 'S1']]], ['exists', ['A2'], ['and', ['isa', 'activity', 'A2'], ['has type', 'A2', 'stop'], ['has actor', 'A2', 'S1'], ['has target', 'A2', 'scientist']]]]]}, 
{'@question': ['exists', ['A3'], ['and', ['isa', 'activity', 'A3'], ['has type', 'A3', 'stop'], ['has actor', 'A3', 'scientist'], ['has target', 'A3', 'student']]]}]
rawresult: {"error": "the question contains explicit quantifiers"}
"""
"""
text:  The student stopped the scientist . The student stopped the scientist ?
result: 
["and", 
    ["exists", "A", ["and", ["isa", "activity", "A"], ["has type", "A", "stop"], ["has time", "A", "past"], 
                            ["has actor", "A", "student"], ["has target", "A", "scientist"]]],   
  ["question", 
    ["exists", "A", ["and", ["isa", "activity", "A"], ["has type", "A", "stop"], ["has time", "A", "past"], 
                            ["has actor", "A", "student"], ["has target", "A", "scientist"]]] ] 
"""

def fix_llm_logic(logic):
  if type(logic)==dict:
    if "@logic" in logic:
      res={"@logic": fix_llm_logic_freevars(fix_llm_logic(logic["@logic"]))}
    elif "@question" in logic:
      res={"@question": fix_llm_logic_freevars(fix_llm_logic(logic["@question"]))}  
    else:
      return None
    return res        
  if type(logic)!=list: return logic
  if logic[0]=="question":
    res={"@question": fix_llm_logic_freevars(fix_llm_logic(logic[1]))} 
    return res
  if len(logic)<2: return logic
  if logic[0] in ["forall","exists"]:
    tmp=fix_llm_logic(logic[2])
    res=[logic[0],[logic[1]],tmp]
    return res
  elif logic[0] in ["implies"]:
    tmp=[fix_llm_logic(x) for x in logic[1:]]
    res=[tmp[0],"=>",tmp[1]]
    return res
  else:
    res=[fix_llm_logic(x) for x in logic]
    return res 

def fix_llm_logic_freevars(logic):
  tmpres=collect_replace_llm_logic_freevars(logic,[],[])
  if tmpres[0]:
    freevars=tmpres[0]
    result=["exists",[x + "fixed" for x in freevars],tmpres[1]]
    return result
  else:
    return logic
      
  #print("freevars",freevars)
  #sys.exit(0)

def collect_replace_llm_logic_freevars(logic,boundvars,freevars):  
  if type(logic)==str:
    #print("cp",logic,boundvars,freevars)
    if (logic in boundvars):
      return [freevars,logic]
    elif (logic in freevars):
      return [freevars,logic]
    elif len(logic)==1 and logic.isalpha() and logic.isupper():
      return [[logic]+freevars,logic+"fixed"]
    else:
      return [freevars,logic]
  elif type(logic)!=list: 
    return [freevars,logic]
  else:
    res=[]
    if logic[0] in ["forall","exists"]:
      boundvars=boundvars+logic[1]
    for el in logic:
      tmpres=collect_replace_llm_logic_freevars(el,boundvars,freevars)
      res.append(tmpres[1])
      freevars=tmpres[0]
    return [freevars,res]
  

    


# ======= solving pre-parsed text (assumed to be parsed by llm) ====

def solve_parsed(logic):
  debug_print("input logic",logic)
  result=llm_parsed_solve(logic)
  return result

# ======== multi-provider LLM calling ========

def call_llm(sysprompt, input_text, llm=None, version=None, max_tokens=None):
  """Call the configured LLM with a system prompt and input text.
  Returns the result string on success, or None on error (error is printed)."""
  llm = llm or use_llm
  max_tokens = max_tokens or default_max_tokens
  if llm == "claude":
    ver = version or claudeversion
  elif llm == "gemini":
    ver = version or geminiversion
  elif llm == "deepseek":
    ver = version or deepseekversion
  else:
    ver = version or gptversion
  debug_print("calling " + llm + " " + ver + " ...")
  try:
    if llm == "claude":
      result = call_claude(ver, input_text, sysprompt, max_tokens)
    elif llm == "gemini":
      result = call_gemini(ver, input_text, sysprompt, max_tokens)
    elif llm == "deepseek":
      result = call_deepseek(ver, input_text, sysprompt, max_tokens)
    else:
      result = call_gpt(ver, input_text, sysprompt, max_tokens)
  except KeyboardInterrupt:
    raise
  except Exception as e:
    return llm_error("unexpected error calling LLM: " + str(e))
  return result


# ======== shared helpers ========

def _read_api_key(filepath, provider):
  """Read an API key from a plain-text file. Returns the key or None on error."""
  try:
    with open(filepath, "r") as f:
      return f.read().strip()
  except:
    llm_error("Could not read " + provider + " API key file: " + str(filepath))
    return None


def _post_with_retry(host, url, body, headers, provider):
  """POST JSON body to host/url with retries. Returns parsed response dict or None."""
  trycount = 0
  while True:
    conn = http.client.HTTPSConnection(host, timeout=llm_timeout)
    try:
      conn.request("POST", url, body, headers=headers)
      response = conn.getresponse()
    except KeyboardInterrupt:
      raise
    except:
      trycount += 1
      if conn: conn.close()
      if trycount > max_retries:
        return llm_error(provider + " connection failed after " + str(max_retries) + " retries")
      print(provider + " connection failure, retrying...")
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
      conn.close()
      # Don't retry on client errors (4xx) — these won't succeed on retry
      if 400 <= response.status < 500:
        return llm_error(provider + " API error " + str(response.status) + " " + str(response.reason) + message)
      trycount += 1
      if trycount > max_retries:
        return llm_error(provider + " API error " + str(response.status) + " " + str(response.reason) + message)
      print(provider + " API failure, retrying:", str(response.status), str(response.reason) + message)
      time.sleep(sleepseconds * trycount)
    else:
      break
  rawdata = response.read()
  conn.close()
  try:
    return json.loads(rawdata)
  except KeyboardInterrupt:
    raise
  except:
    return llm_error(provider + " response is not valid JSON: " + str(rawdata))


# ======== gpt ========

def call_gpt(version, sentences, sysprompt, max_tokens):
  key = _read_api_key(gpt_secrets_file, "GPT")
  if key is None: return None

  if version.startswith("gpt-5"):
    url = "/v1/responses"
    messages = []
    if sysprompt:
      messages.append({"role": "system", "content": [{"type": "input_text", "text": sysprompt}]})
    messages.append({"role": "user", "content": [{"type": "input_text", "text": sentences}]})
    call = {
      "model": version,
      "input": messages,
      "text": {"verbosity": "low", "format": {"type": "text"}},
      "reasoning": {"effort": "none"}
    }
    if max_tokens:
      call["max_output_tokens"] = max_tokens
  else:
    url = "/v1/chat/completions"
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

  debug_print("gpt call", call)
  host = "api.openai.com"
  data = _post_with_retry(host, url, json.dumps(call),
                          {"Host": host, "Content-Type": "application/json",
                           "Authorization": "Bearer " + key},
                          "GPT")
  if data is None: return None
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


# ======== claude ========

def call_claude(version, sentences, sysprompt, max_tokens):
  key = _read_api_key(claude_secrets_file, "Claude")
  if key is None: return None

  messages = [{"role": "user", "content": sentences}]
  call = {
    "model": version,
    "messages": messages,
    "temperature": temperature,
    "max_tokens": max_tokens
  }
  if sysprompt:
    call["system"] = [{"type": "text", "text": sysprompt}]

  debug_print("claude call", call)
  data = _post_with_retry("api.anthropic.com", "/v1/messages",
                          json.dumps(call),
                          {"content-Type": "application/json",
                           "anthropic-version": "2023-06-01",
                           "x-api-key": key},
                          "Claude")
  if data is None: return None
  if "content" not in data:
    return llm_error("Claude response has no content: " + str(data))
  debug_print("claude response:", data)
  res = ""
  for el in data["content"]:
    if "text" in el:
      res += el["text"].strip()
  return res


# ======== gemini ========

def call_gemini(version, sentences, sysprompt, max_tokens):
  key = _read_api_key(gemini_secrets_file, "Gemini")
  if key is None: return None

  genconfig = {
    "maxOutputTokens": max_tokens,
    "temperature": temperature
  }
  call = {
    "contents": [{"parts": [{"text": sentences}]}],
    "generationConfig": genconfig
  }
  if sysprompt:
    call["system_instruction"] = {"parts": [{"text": sysprompt}]}

  debug_print("gemini call", call)
  url = "/v1beta/models/" + version + ":generateContent"
  data = _post_with_retry("generativelanguage.googleapis.com", url,
                          json.dumps(call),
                          {"content-Type": "application/json", "x-goog-api-key": key},
                          "Gemini")
  if data is None: return None
  if "candidates" not in data:
    return llm_error("Gemini response has no candidates: " + str(data))
  cand = data["candidates"][0]
  if "content" not in cand:
    return llm_error("Gemini response has no content: " + str(cand))
  if "parts" not in cand["content"]:
    return llm_error("Gemini response has no parts: " + str(cand))
  debug_print("gemini response:", data)
  res = ""
  for el in cand["content"]["parts"]:
    if "text" in el:
      res += el["text"].strip()
  return res


# ======== deepseek ========

def call_deepseek(version, sentences, sysprompt, max_tokens):
  key = _read_api_key(deepseek_secrets_file, "DeepSeek")
  if key is None: return None

  messages = []
  if sysprompt:
    messages.append({"role": "system", "content": sysprompt})
  messages.append({"role": "user", "content": sentences})
  call = {
    "model": version,
    "messages": messages,
    "stream": False,
    "temperature": temperature
  }
  if max_tokens:
    call["max_tokens"] = max_tokens

  debug_print("deepseek call", call)
  data = _post_with_retry("api.deepseek.com", "/v1/chat/completions",
                          json.dumps(call),
                          {"Content-Type": "application/json",
                           "Authorization": "Bearer " + key},
                          "DeepSeek")
  if data is None: return None
  debug_print("deepseek response:", data)
  if "choices" not in data:
    return llm_error("DeepSeek response has no 'choices': " + str(data))
  res = ""
  for el in data["choices"]:
    if "message" in el:
      msg = el["message"]
      if "content" in msg and msg["content"]:
        res += msg["content"]
  return res


# ======== llm error reporting ========

def llm_error(msg):
  print("LLM error:", msg)
  return None

# ========== big prompt ============

logifyprompt="""
You are a semantic parser from English to first order predicate logic (FOL).
Convert input sentences to logic, represented in json using lists for predicates and formulas like this:
["forall","X", ...] for universal quantification of a variable X,
["exists","X", ...] for existential quantification of a variable X,
["and", ...] for conjunction,
["or", ...] for disjunction,
["xor", ...] for exclusive or,
["implies", ...] for implication,
["not", ...] for negation,
["=", ...] for equality
[">", ...] for greater
["<", ...] for smaller
["question" ...] for wrapping a logic of the question with a yes/no answer
["ask","X", ...] for wrapping a logic of the question where the value of X is asked

Use ["rel2",relation,object1,object2] for a generic relation between two objects.
Wrap physically active verbs like eating, jumping with the ["isa","activity",...] and attitude indicating verbs like liking, preferring, wanting with ["has attitude",...].
If a verb indicates a typical activity in a rule sentence like "Birds fly", wrap the action with ["typical activity",...].
All variables must be bound by an existential or universal quantifier.

If a proper name is present in English Wikipedia, replace it with the Wikipedia url appended to the name like this: 
"Barack Obama" => "Barack Obama https://en.wikipedia.org/wiki/Barack_Obama"
"USA" => "USA https://en.wikipedia.org/wiki/United_States"
"Apple" => "Apple https://en.wikipedia.org/wiki/Apple_Inc"

Do not use curly braces, i.e. json objects!
Do not insert newlines into the answer!

Examples:  

"John is a person" => ["isa","person","John"]
"There was a car." => ["exists","X", ["isa","car","X"]]
"A bear is an animal" => ["forall","X", ["implies",["isa","bear","X"], ["isa","X","animal]]]

"All green things are rough" => ["forall","X", ["implies",["and",["has property","X","green"], ["isa","thing","X"]],["has property","X","rough"]]]
"Some animals are small" =>   ["exists","X",["and",["isa","animal","X"], ["has property","X","small"]]] 
"Dinosaurs were heavy animals" =>   ["forall","X", ["implies",["isa","dinosaur","X"], ["has property","X","heavy"]]] 

"Dogs have paws" =>  ["forall","X", ["implies",["isa","dog","X"], ["exists","Y",["and",["isa","paws","Y"],["have","X","Y"]]]]]
"Dogs had paws" =>  ["exists","X", ["and",["isa","dogs","X"], ["exists","Y",["and",["isa","paws","Y"],["had","X","Y"]]]]
"A car has wheels" =>   ["forall","X", ["implies",["isa","car","X"], ["exists","Y",["and",["isa","wheels","Y"],["has","X","Y"]]]]]
"Bears have a tail" => ["forall","X", ["implies",["isa","bear","X"], ["exists","Y",["and",["isa","tail","Y"],["have","X","Y"]]]]]
"Bears had a tail" => ["exists","X", ["and",["isa","bears","X"],["exists","Y",["and",["isa","tail","Y"],["had","X","Y"]]]]]
"The bear had a berry" => ["exists","X", ["and",["isa","bear","X"],["exists","Y",["and",["isa","Y","berry"],["had","X","Y"]]]]]
"Dinosaurs had big heads" =>    ["forall","X", ["implies",["isa","dinosaur","X"], ["exists","Y",["and",["isa","head","Y"],["has property","Y","big"],["had","X","Y"]]]]]
"Americans have a capital" =>  ["exists","Y", ["and",["isa","capital","Y"], ["forall","X", ["implies",["isa","american","X"], ["have","X","Y"]]]]]
"Chinese had a capital" => ["exists","Y", ["and",["isa","capital","Y"], ["forall","X", ["implies",["isa","chinese","X"], ["had","X","Y"]]]]]
"The dog had a bone" =>   ["exists","X", ["and",["isa","dog","X"],["exists","Y",["and",["isa","bone","Y"],["had","X","Y"]]]]]

"Pete is not a man" => ["not",["isa","Pete","man"]]
"Pete is not a bad man" => ["not",["and",["has property","Pete","bad"],["isa","man","Pete"]]]
"John does not have a car" => ["not",["exists","X", ["and",["isa","car","X"],["have","John","X"]]]]
"White objects are not black" => ["forall","X", ["implies",["and",["has property","X","white"], ["isa","object","X"]],["not",["has property","X","black"]]]]
"Elephants have no wings" => ["forall","X", ["implies",["isa","elephant","X"],["not",["exists","Z",["and",["isa","wing","Z"],["have","X","Z"]]]]]]

"John has a car or a bike" => ["xor",["exists","X", ["and",["isa","car","X"],["has","John","X"]]],["exists","Y", ["and",["isa","bike","Y"],["has","John","Y"]]]]
"Alice is either good or bad" => ["xor", ["has property","good","Alice"], ["has property","bad","Alice"]]
"John or Mary has a car" => ["or",["exists","X", ["and",["isa","car","X"],["has","John","X"]]],["exists","Y", ["and",["isa","car","Y"],["has","Mary","Y"]]]]

"John is a brother of Mike" => ["rel2","brother","John","Mike"]
"Obama was a president of USA" =>  ["rel2","president","USA https://en.wikipedia.org/wiki/United_States","Obama https://en.wikipedia.org/wiki/Barack_Obama"]
"USA's president was Obama" =>  ["rel2","president","USA https://en.wikipedia.org/wiki/United_States","Obama https://en.wikipedia.org/wiki/Barack_Obama"]
"Tallinn is north of Riga" => ["rel2","north","Tallinn https://en.wikipedia.org/wiki/Tallinn","Riga https://en.wikipedia.org/wiki/Riga"]
"Tallinn is near Riga" => ["rel2","near","Tallinn https://en.wikipedia.org/wiki/Tallinn","Riga https://en.wikipedia.org/wiki/Riga"]
"Point A is connected to point B." ["rel2","connected","A","B"]
"Tallinn is on the seacoast" => ["exists","X",["and",["isa","seacoast","X"]["rel2","on","Tallinn https://en.wikipedia.org/wiki/Tallinn","X"]]]
"John and Mike are in a small room" => ["exists","X",["and",["isa","room","X"],["has property","X","small"],["rel2","in","John","X"],["rel2","in","Mike","X"]]]
"Ceilings are above doors" => ["forall","X",["forall","Y",["implies",["and",["isa","ceiling","X"],["isa","door","Y"]],["rel2","above","X","Y"]]]]
"Dole was defeated by Clinton" => ["rel2","defeated","Clinton https://en.wikipedia.org/wiki/Bill_Clinton","Dole https://en.wikipedia.org/wiki/Bob_Dole"]
"John defeated Mike" => ["rel2","defeated","John","Mike"]

"John is stronger than Mike" => [">",["$value",["property of","John","strength"]], ["$value", ["property of", "Mike", "strength"]]]
"Eve is as nice as Mike" => ["=",["$value",["property of","Eve","nice"]], ["$value", ["property of", "Mike", "nice"]]]

"Michael likes Eve" => ["has attitude","like","Michael","Eve"]
"Bears like honey" => ["forall","X", ["implies",["isa","bear","X"], ["forall","Y",["implies",["isa","Y","honey"],["has attitude","like","X","Y"]]]]]
"Bears liked cakes" => ["exists","X", ["and",["isa","bears","X"],["exists","Y",["and",["isa","Y","cake"],["had attitude","like","X","Y"]]]]]
"Dogs like meat" =>  ["forall","X", ["implies",["isa","dog","X"], ["forall","Y",["implies",["isa","Y","meat"],["has attitude","like","X","Y"]]]]]
"The dog liked berries" =>  ["exists","X", ["and",["isa","dog","X"],["exists","Y",["and",["isa","Y","berry"],["had attitude","like","X","Y"]]]]]
"The dog wanted meat" =>  ["exists","X", ["and",["isa","dog","X"],["forall","Y",["implies",["isa","Y","meat"],["had attitude","want","X","Y"]]]]]
"The bear likes berries" => ["exists","X", ["and",["isa","bear","X"],["forall","Y",["implies",["isa","Y","berry"],["has attitude","like","X","Y"]]]]]
"John does not like cakes" => ["forall","Y",["implies",["isa","Y","cake"],["not",["has attitude","like","John","Y"]]]]

"Mike notices Eve" => ["exists","A",["and",["isa","activity","A"],["has type","A","notice"],["has time","A","present"],["has actor","A","John"],["has target","A","Eve"]]]
"John ran quickly" => ["exists","A",["and",["isa","activity","A"],["has type","A","run"],["has time","A","past"],["has manner","A","quickly"],["has actor","A","John"]]]
"John ate a sandwich" => ["exists","A",["exists","Y",["and",["isa","activity","A"],["isa","sandwitch","Y"]["has type","A","eat"],["has time","A","past"],["has actor","A","John"],["has target","A","Y"]]]]
"The bear ate berries" =>  ["exists","X", ["and",["isa","bear","X"],["exists","Y",["and",["isa","Y","berries"],["exists","A",["and",["isa","activity","A"],["has type","A","eat"],["has time","A","past"],["has actor","A","X"],["has target","A","Y"]]]]]]]
"Titanic sank in the Atlantic" => ["exists","A",["and",["isa","activity","A"],["has type","A","sink"],["has time","A","past"],["has location","A","Atlantic https://en.wikipedia.org/wiki/Atlantic_Ocean"],["has actor","A","Titanic https://en.wikipedia.org/wiki/RMS_Titanic"]]]

"A big dog likes to bark" => ["exists","X", ["and",["isa","dog","X"],["has property","X","big"],["forall","A",["implies",["and",["isa","activity","A"],["has type","A","bark"],["has actor","A","X"]],["has attitude","like","X","A"]]]]]
"A dog likes to howl" =>  ["forall","X", ["implies",["isa","dog","X"], ["forall","A",["implies",["and",["isa","activity","A"],["has type","A","howl"],["has actor","A","X"]],["has attitude","like","X","A"]]]]]
"A big dog ate a carrot" =>   ["exists","X", ["and",["isa","dog","X"],["has property","X","big"],["exists","Y",["and",["isa","carrot","Y"],["exists","A",["and",["isa","activity","A"],["has type","A","eat"],["has time","A","past"],["has actor","A","X"],["has target","A","Y"]]]]]]]
"The dog ate bones" =>  ["exists","X",["and",["isa","dog","X"],["exists","Y",["and",["isa","bones","Y"],["exists","A",["and",["isa","activity","A"],["has type","A","eat"],["has time","A","past"],["has actor","A","X"],["has target","A","Y"]]]]]]]
"A red bear likes to sleep" =>  ["exists","X", ["and",["isa","bear","X"], ["has property","X","red"], ["forall","A",["implies",["and",["isa","activity","A"],["has type","A","sleep"],["has actor","A","X"]],["has attitude","like","X","A"]]]]]
"A bear likes to sleep" =>  ["forall","X", ["implies",["isa","bear","X"], ["forall","A",["implies",["and",["isa","activity","A"],["has type","A","sleep"],["has actor","A","X"]],["has attitude","like","X","A"]]]]   
"A bear liked to sleep" =>  ["exists","X", ["implies",["isa","bear","X"], ["forall","A",["implies",["and",["isa","activity","A"],["has type","A","sleep"],["has actor","A","X"]],["had attitude","like","X","A"]]]]
"Bears liked to sleep" => ["exists","X", ["and",["isa","bears","X"],["forall","A",["implies",["and",["isa","activity","A"],["has type","A","sleep"],["has actor","A","X"]],["had attitude","like","X","A"]]]]]

"John was a teacher at a school" =>   ["exists","Y", ["and",["isa","school","Y"], ["exists","X",["isa","job","X"], ["had","John","X"],["has location","X","Y"],["has type","X","teacher"]]]]
"A man lives in a red house" =>  ["exists","X", ["and",["isa","man","X"],["exists","Y",["and",["isa","house","Y"],["has property","Y","red"], ["exists","Z",["isa","activity","Z"],["has type","Z","live"],["has location","Z","Y"],["has time","Z","present"],["has actor","Z","X"]]]]]]
"Teachers work at a school" =>  ["forall","X", ["implies",["isa","teacher","X"], ["exists","Y",["and",["isa","school","Y"],["exists","Z",["isa","activity","Z"],["has type","Z","work"],["has location","Z","Y"],["has actor","Z","X"]]]]]]
"John goes to New York for fun" =>  ["exists","Z",["isa","activity","Z"],["has type","Z","go"],["has target","Z","New York https://en.wikipedia.org/wiki/New_York_City"],["has goal","Z","fun"],["has actor","Z","John"]]

"John walked in Mary's house" => ["exists","A",["and",["isa","activity","A"],["has type","A","walk"],["has time","A","past"],["has actor","A","John"],["exists","X",["and",["isa","house","X"],["have","Mary","X"],["rel2","in","A","X"]]]]]

"Birds can fly" => ["forall","X", ["implies",["isa","bird","X"], ["and",["exists","Y",["and",["isa","activity","Y"],["has type","Y","flying"],["has actor","Y","X"]]],["is able","X","Y"]]]]
"Birds fly" => ["forall","X", ["implies",["isa","bird","X"], ["and",["exists","Y",["and",["isa","activity","Y"],["has type","Y","flying"],["has actor","Y","X"]]],["typical activity","X","Y"]]]]
"Dogs bark" => ["forall","X", ["implies",["isa","dog","X"], ["and",["exists","Y",["and",["isa","activity","Y"],["has type","Y","barking"],["has actor","Y","X"]]],["typical activity","X","Y"]]]]
"Penguins cannot fly" => ["forall","X", ["implies",["isa","bird","X"], ["forall","Y",["implies",["and",["isa","activity","Y"],["has type","Y","flying"],["has actor","Y","X"]],["not",["is able","X","Y"]]]]]]

"John has five apples" => ["exist","X",["and",["is set of","apple","X"],["=",5,["$count","X"]],["has","John","X"],["forall","Y",["implies",["and",["isa","apple","Y"],["has","John","Y"]],["member","Y","X"]]]]]
"John has several apples" => ["exist","X",["and",["is set of","apple","X"],[">",["$count","X"],1],["has","John","X"]]]
"John has two red and three green apples" => ["and",["exist","X",["and",["is set of",["and",["isa","apple","X"],["has property","X","red"]]],["=",["$count","X"],2],["has","John","X"]]],["exist","Y",["and",["is set of",["and",["isa","apple","Y"],["has property","Y","green"]]],["=",["$count","X"],3],["has","John","Y"]]]]

"The length of Emajogi is 80 kilometers" => ["and",["has property","Emajogi https://en.wikipedia.org/wiki/Emaj%C3%B5gi",["$measure1","length","Emajogi","kilometer"]],["=",80,["$value",["$measure1","length","Emajogi","kilometer"]]]]
"The price of the red car is 2 dollars" => ["exists","X",["and",["isa","car,"X"],["has property","X","red"],["=",2,["$value",["$measure1","price","X","dollar"]]]]]
"Bikes are lighter than cars" => ["forall","X",["forall","Y",["implies",["and",["isa","bike,"X"],["isa","car","Y"]],["<",["$value",["$measure1","weight","X","kilograms"]],["$value",["$measure1","weight","Y","kilograms"]]]]]]

"John is nice. Eve is a woman. He has a car." => ["and",["has property","John","nice"],["isa","woman","Eve"],["exists","X",["isa","car","X"],["has","John","X"]]]
"The bear is big. The animal is thirsty." => ["exists","X",["and",["isa","bear","X"],["has property","X","big"],["has property","X","thirsty"]]]
"The cup is small. The engine is strong." => ["and",["exists","X",["and",["isa","cup","X"],["has property","X","small"]]],["exists","Y",["isa","engine","Y"],["has property","Y","strong"]]]

"Is John strong?" => ["question",["has property","John","strong"]]
"Five is not smaller than three?" => ["question",["not",["<",5,3]]]
"Who likes Mike?" => ["ask","Y",["has attitude","like","Mike","Y"]]
"Which man is big?" => ["ask","X",["and"["isa","man","X"],["has property","X","big"]]]
"Where did John go?" => ["ask","Y",["exists","X",["and",["isa","activity","X"],["has type","X","go"],["has actor","X","John"]["has target","X","Y"]]]]
"Mike is an elephant. Mary is a cat. Who is an elephant?" => ["and",["isa","elephant","Mike"],["isa","cat","Mary"], ["ask","X",["isa","elephant","X"]]]
"""

# =========== the end ==========

"""
./nlpsolver.py "John had five apples. Pete had one apple less than John. Pete had three apples ?" -llmparseall
./nlpsolver.py "John had five apples. Pete had one apple less than John. Pete had three apples ?" -llmparseall
"""