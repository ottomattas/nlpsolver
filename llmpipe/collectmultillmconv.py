#!/usr/bin/env python3

# Tools for working on prompts
#
# Run the program and it will call LLMs and collect the output
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

# ======== configuration ======

syspromptfile="prompts/logifyprompt7_stage1.txt"
promptfile="prompts/logifyprompt6.txt"

show_tests=True # set to False to suppress printing of all tests during work
show_compact=True # if show_tests is False, set to True to get 0/1 char for each test

debug=False

result_file_suffix="_promptresults.txt"

linestart="|!!|"
separator=" |$$| "

sleepseconds=2

use_llm="claude"
#use_llm="gpt"
#use_llm="gemini"

#gpt5="gpt-5-nano-2025-08-07"
#gpt5="gpt-5-mini-2025-08-07"
#gpt5="gpt-5-2025-08-07"
gptversion="gpt-5.2"

#claudeversion="claude-3-7-sonnet-20250219"
# claude-3-7-sonnet-20250219 old
# claude-haiku-4-5  cheaper
# claude-sonnet-4-5  middling, coding etc
# claude-opus-4-1 expensive
claudeversion="claude-haiku-4-5"
geminiversion="gemini-3-flash-preview"

debug=True # set to True to get a printout of data, call and result
calldebug=False

# =======specific llm configuration ===

gpt_secrets_file="gpt_secrets.js"
claude_secrets_file="claude_secrets.js"
gemini_secrets_file="gemini_secrets.js"

temperature=0
seed=1234
default_max_tokens=8000

sleepseconds=2
timeout=60

# ======== testing program ======


def main():
  try:
    f=open(promptfile,"r")
    lines=f.readlines()      
  except:
    print("Could not read prompt file",promptfile)  
    return
  f.close()
  inexamples=False
  tests=[]
  for line in lines:
    if line.startswith("Examples:"):
      inexamples=True
      continue
    if not inexamples: continue
    line=line.strip()
    if not line: continue
    sline=line.split("=>")
    intxt=sline[0].strip()
    if intxt.startswith('"'): intxt=intxt[1:]
    if intxt.endswith('"'): intxt=intxt[:-1]
    intxt=intxt.strip()

    print(intxt)
    tests.append(intxt)
  single_run_tests(promptfile,tests)    



def single_run_tests(testfile, tests, lower=0, upper=0, options={}):
  okresults=[]
  failedresults=[]
  testcount=0-1
  realtestcount=0
  print("Starting to run",len(tests),"tests")
  options["use_cache_flag"]=False
  if show_tests: print()
  if upper==0: 
    upper=len(tests)  
  start_time = time.time() 
  tmp=testfile.split(".")  
  outfilename=tmp[0]+"_"+use_llm+result_file_suffix
  outfile=open(outfilename,"w")

  max_tokens=default_max_tokens

  sysprompt="" 
  pfile=syspromptfile
  if pfile:
    try:
      f=open(pfile, "r")
      sysprompt=f.read().strip()
      f.close()
    except:
      show_error("could not read sysprompt file "+pfile)  

  for test in tests:    
    testcount+=1
    if testcount<lower: continue
    if testcount>=upper: break
    realtestcount+=1
    if show_tests: print("Input:",test)
    prompt=test

    debug_print("prompt:",prompt)
    if not prompt:
      show_error("no prompt given")    
    
    try:
      if use_llm=="claude": 
        debug_print("claude",claudeversion)
        result=call_claude(claudeversion,prompt,sysprompt,max_tokens) 
      elif use_llm=="gemini": 
        debug_print("gemini",geminiversion)
        result=call_gemini(geminiversion,prompt,sysprompt,max_tokens)     
      else:
        debug_print("gpt",gptversion)
        result=call_gpt(gptversion,prompt,sysprompt,max_tokens)  
    except KeyboardInterrupt:
      sys.exit(0)  
    #except:
    #  result="Software error."          
    print("result",result)  
    #sys.exit(0)  

    time.sleep(sleepseconds)
    """
    try:
      if gptversion==claudeversion:
        result=call_claude(claudeversion,prompt,sysprompt,max_tokens)  
      else:
        result=call_gpt(gptversion,prompt,sysprompt,max_tokens)
    except KeyboardInterrupt:
      sys.exit(0)  
    except:
      result="Software error."  
    """  
 
    if show_tests: print("Received:",result) 
    if show_tests: print()   
    outtext=linestart+prompt+separator+str(result)+"\n"
    outfile.write(outtext)
    outfile.flush()
    #print("result:",result)    
    if True:
      okresults.append([test,result])
      if not show_tests and show_compact: print("1",end="",flush=True)    

  outfile.close()  
  if not show_tests and show_compact: print()
  print("Testing finished in "+str(round(time.time() - start_time,3))+" seconds")
  print("Tests run:",realtestcount)
  print("OK tests:",len(okresults))
  print("Failed tests:",len(failedresults))
  if len(failedresults)>0:
    print()
    print("Tests which failed:")
    for result in failedresults:
      print("Input:",result[0][0])
      print("Expected:",result[0][1])
      print("Received:",result[1])
  results=[realtestcount,len(okresults),failedresults]
  return results


# ========= llm connection for gemini =========


# https://ai.google.dev/gemini-api/docs/text-generation
# https://ai.google.dev/api/generate-content#v1beta.GenerationConfig

def call_gemini(version,sentences,sysprompt,max_tokens):
  try:
    sf=open(gemini_secrets_file,"r")
    txt=sf.read()
  except:
    show_error("Could not read file containing gemini api key: "+str(gemini_secrets_file)) 
  key=txt  
  # key found ok    
  #sentences="A fork is a tool you use in the kitchen or when you eat."  
  textcontent=sysprompt+"\n"+sentences
 
  baseurl="/v1beta/models/"+version+":generateContent"
  call={       
        "contents": [{
              "parts": [{"text": sentences}]
            }],
        "generationConfig": {
          "maxOutputTokens": max_tokens,          
          "thinkingConfig": {
            "thinkingLevel": "medium" # minimal,low,medium,high
          },
          "temperature": 0
        }
  }    
  if sysprompt:
    call["system_instruction"]={"parts": [{"text": sysprompt}]}     
  #if max_tokens:
  #  call["max_tokens"]=max_tokens

  #debug_print("gemini call",call)
  calltxt=json.dumps(call) 
  #debug_print("gemini calltxt:",calltxt)

  trycount=0
  while True:
    host = "generativelanguage.googleapis.com"
    conn = http.client.HTTPSConnection(host, timeout=timeout)
    conn.request("POST", baseurl, calltxt, 
                headers={
      "content-Type": "application/json", 
      "x-goog-api-key": key
    })    
    try:
      response = conn.getresponse()
    except:
      print("connection failure, trying again ")  
      trycount+=1
      if conn: conn.close()
      time.sleep(sleepseconds*(trycount+1))
      continue  
    if response.status!=200 or response.reason!="OK":
      try:
        data=json.loads(response.read())    
        if "error" in data and "message" in data["error"]:
          message=": "+data["error"]["message"]
      except:
        message=""      
      print("api failure, trying again: ",str(response.status),str(response.reason)+message)  
      trycount+=1
      if conn: conn.close()
      time.sleep(sleepseconds*(trycount+1))
    else:
      break  
    if trycount>3:
      show_error("after several tries claude responded with error "+str(response.status)+" "+str(response.reason)+message)
  rawdata = response.read()
  #print("rawdata",rawdata)
  try:
    data=json.loads(rawdata)
  except KeyboardInterrupt:
    raise  
  except:
    show_error("gemini response is not a correct json: "+  str(rawdata))

  if "candidates" not in data:
    show_error("gemini response does not contain candidates:"+ str(rawdata))  
  data=data["candidates"]
  
  data=data[0]

  if "content" not in data:
    show_error("gemini response does not contain content:"+ str(data))
  data=data["content"]

  if "parts" not in data:
    show_error("gemini response does not contain parts:"+ str(data))  
  data=data["parts"]  
  
  # OK answer received  
  debug_print("gemini response:",data)  
 
  res=""
  for el in data:
    if "text" in el:    
      res+=el["text"].strip()                    
  conn.close()
  #debug_print("res",res)  
  return res

# ========= llm connection for claude =========

def call_claude(version,sentences,sysprompt,max_tokens):
  try:
    sf=open(claude_secrets_file,"r")
    txt=sf.read()
  except:
    show_error("Could not read file containing claude api key: "+str(claude_secrets_file))
  key=txt  
  # key found ok    
  #sentences="A fork is a tool you use in the kitchen or when you eat."
  messages=[]  
  message={"role": "user", "content": sentences}
  messages.append(message) 
 
  baseurl="/v1/messages"
  call={
       "model": version,
       "messages": messages,
       "temperature": temperature,
       "max_tokens": max_tokens
       #"reasoning_effort": "low"
    }
  #if sysprompt:
  #  sysprompt=sysprompt+"""\nFinally, wrap the answer as a json value of the key "result" like this:
  #    {"result":actual_result}\n"""
  if sysprompt:
    call["system"]=[{"type":"text", "text":sysprompt, "cache_control": {"type": "ephemeral"}}]
  if max_tokens:
    call["max_tokens"]=max_tokens
  #call["output_format"]={"type": "json_schema", "schema": {"type": "object","required": ["result"], "additionalProperties": False}}

  calldebug_print("claude call",call)
  calltxt=json.dumps(call) 
  #calldebug_print("claude calltxt:",calltxt)

  trycount=0
  while True:
    host = "api.anthropic.com" 
    conn = http.client.HTTPSConnection(host,timeout=timeout)   
    conn.request("POST", baseurl, calltxt,
                headers={
      "content-Type": "application/json", 
      "anthropic-version": "2023-06-01",
      "x-api-key": key
      #"anthropic-beta": "structured-outputs-2025-11-13"
    })          
    try:
      response = conn.getresponse()
    except:
      print("connection failure, trying again ")  
      trycount+=1
      if conn: conn.close()
      time.sleep(sleepseconds*(trycount+1))
      continue  
    if response.status!=200 or response.reason!="OK":
      try:
        data=json.loads(response.read())    
        if "error" in data and "message" in data["error"]:
          message=": "+data["error"]["message"]
      except:
        message=""      
      print("api failure, trying again: ",str(response.status),str(response.reason)+message)  
      trycount+=1
      if conn: conn.close()
      time.sleep(sleepseconds*(trycount+1))
    else:
      break  
    if trycount>3:
      show_error("after several tries claude responded with error "+str(response.status)+" "+str(response.reason)+message)  
  rawdata = response.read()

  try:
    data=json.loads(rawdata)
  except KeyboardInterrupt:
    raise  
  except:
    show_error("claude response is not a correct json: "+  str(rawdata))
  if "content" not in data:
    show_error("claude response does not contain content:"+ str(rawdata))

  # OK answer received  
  debug_print("claude response:",data)  
  part=data["content"]  
  res=""
  for el in part:
    if "text" in el:    
      res+=el["text"].strip()      
              
  conn.close()
  #debug_print("res",res)  
  return res


# ========= llm connection =========


def call_gpt(gptversion,sentences,sysprompt,max_tokens):
  try:
    sf=open(gpt_secrets_file,"r")
    txt=sf.read()
  except:
    show_error("Could not read file containing gpt api key: "+str(gpt_secrets_file))
  try:  
    data=json.loads(txt)
  except:
    show_error("Could not parse json text containing gpt api key in: "+str(gpt_secrets_file))  
  if "gpt_key" not in data or not (data["gpt_key"]):
    show_error("Could not find gpt api key in: "+str(gpt_secrets_file))
  else:    
    key=data["gpt_key"]
  # key found ok    
  #sentences="A fork is a tool you use in the kitchen or when you eat."
  messages=[]
  if sysprompt:
    message1={"role": "system", "content": sysprompt}
    messages.append(message1)   
  message2={"role": "user", "content": sentences}
  messages.append(message2)  

  
  if gptversion.startswith("gpt-5"): #gptversion in [gpt5]:
    baseurl="/v1/responses"
    if sysprompt:
      sysprompt=sysprompt+""""\nFinally, wrap the answer as a json value of the key "result" like this:
      {"result":actual_result}\n
"""      
      messages=[
        {"role": "system", "content": [{"type": "input_text", "text": sysprompt}]},
        {"role": "user",   "content": [{"type": "input_text", "text": sentences}]}
      ]  
    else:
      messages=[      
        {"role": "user",   "content": [{"type": "input_text", "text": sentences}]}
      ]  
    effort="none"
    if gptversion.startswith("gpt-5.1"):
      effort="none" # "none" | "low" | "medium" | "high"
    elif gptversion.startswith("gpt-5.2"):
      effort="none" # "none" | "low" | "medium" | "high"  
    else:
      effort="minimal" # 'minimal', 'low', 'medium', 'high'.
    call={
      "model": gptversion,
      "input": messages,
      "text": {
          "verbosity": "low",
          "format": { "type": "json_object" }  
      }, 
      
      "reasoning": {
        "effort": effort
      }
    }    
  else:  
    baseurl="/v1/chat/completions"
    call={
       "model": gptversion,
       "messages": messages,
       "seed": seed,
       "logprobs": False,
       "temperature": temperature
       #"type": "json_object"       
    }  
  if max_tokens:
    if gptversion.startswith("gpt-5"):
      call["max_output_tokens"]=max_tokens
    else:
      call["max_tokens"]=max_tokens 

  calldebug_print("gpt call",call)
  calltxt=json.dumps(call) 
  #calldebug_print("gpt call:",calltxt)
 
  host = "api.openai.com"
  conn = http.client.HTTPSConnection(host,timeout=timeout)
  conn.request("POST", baseurl, calltxt,
               headers={
    "Host": host, "Content-Type": "application/json", "Authorization": "Bearer "+key 
  })
  response = conn.getresponse()
  """
  try:
    response = conn.getresponse()
  except:
    print("connection failure, trying again ")  
    trycount+=1
    if conn: conn.close()
    time.sleep(sleepseconds*(trycount+1))
    continue
  """  
  if response.status!=200 or response.reason!="OK":
    try:
      data=json.loads(response.read())    
      if "error" in data and "message" in data["error"]:
        message=": "+data["error"]["message"]
    except:
      message=""      
    show_error("gpt responded with error "+str(response.status)+" "+str(response.reason)+message)
  rawdata = response.read()
  try:
    data=json.loads(rawdata)
  except KeyboardInterrupt:
    raise  
  except:
    show_error("gpt response is not a correct json: "+  str(rawdata))

  if gptversion.startswith("gpt-5"): 
    found=False
    debug_print("gpt response:",data)  
    if "output" not in data:
      show_error("gpt response does not contain 'output'")
    o=data["output"]
    for el in o:
      if "content" in el and "type" in el and el["type"]=="message":
        c=el["content"]
        for cel in c:
          if "text" in cel and "type" in cel and cel["type"]=="output_text":
            found=True
            res=cel["text"]
            if sysprompt and '"result":' in sysprompt:
              parsedok=True
              try:  
                tmp=json.loads(res)
              except:
                parsedok=False
                show_error("gpt response is not a json_object")
              if parsedok and "result" in tmp:
                res=tmp["result"]
                res=json.dumps(res)
              else:
                show_error("gpt response as a json_object does not contain 'result'") 
            break
      if found:
        break 
    if not found:
      show_error("gpt response structure not understood")           
  else:
    if "choices" not in data:
      show_error("gpt response does not contain choices")
    # OK answer received  
    debug_print("gpt response:",data)  
    part=data["choices"]  
    res=""
    for el in part:
      if "message" in el:
        msg=el["message"]
        if "content" in msg:
          tmp=msg["content"]
          if len(tmp)>2 and tmp[0] in ["\"","'"] and tmp[-1] in ["\"","'"]:
            tmp=tmp[1:-1]
          tmp2=tmp.split("\n")
          if len(tmp2)>1:
            tmp3=""
            for line in tmp2:
              if len(line)>3 and (line[0].isnumeric() or line[0] in ["*","-"]) and line[1] in [".",":"," "]:
                tmp3+=line[2:]+" "
              else:
                tmp3+=line+" "  
            tmp=tmp3    
          res+=tmp
      elif "text" in el:
        if res: res+="\n"
        res+=el["text"].strip()      
                
  conn.close()
  #debug_print("res",res)  
  return res


def debug_print(a,b):    
  if debug:
    print(a,b)

def calldebug_print(a,b):  
  if calldebug:
    print(a,b)    

def show_error(a):
  print("Error:",a)
  #sys.exit(0)  



# ========= run the program ======

if __name__ == "__main__":        
  main()  


# ========= the end =============
