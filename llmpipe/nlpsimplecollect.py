#!/usr/bin/env python3

# Collecting gpt results for data
#
# Run the program and it will collect the output
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
import http.client

# ======== configuration ======

test_files=["try160.py"]

show_tests=True # set to False to suppress printing of all tests during work
show_compact=True # if show_tests is False, set to True to get 0/1 char for each test

debug=False

result_file_suffix="_llmresults.txt"

linestart="|!!|"
separator=" |$$| "

sleepseconds=2

use_llm="claude"
use_llm="gpt"


#syspromptfile="nlpsimpleprompt1.txt"
syspromptfile="logifyprompt6.txt"

#gptversion="gpt-4.1-2025-04-14" 
#gpt5="gpt-5-nano-2025-08-07"
#gpt5="gpt-5-mini-2025-08-07"
#gpt5="gpt-5-2025-08-07"
gptversion="gpt-5.1"

#claudeversion="claude-3-7-sonnet-20250219"
# claude-3-7-sonnet-20250219 old
# claude-haiku-4-5  cheaper
# claude-sonnet-4-5  middling, coding etc
# claude-opus-4-1 expensive
claudeversion="claude-sonnet-4-5"

debug=True # set to True to get a printout of data, call and result
calldebug=False

# =======specific llm configuration ===

secrets_file="secrets.js"
claude_secrets_file="claude_secrets.js"

temperature=0
seed=1234
default_max_tokens=2000

sleepseconds=2


# ======== testing program ======


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
    print("\n=== running test "+test[0]+" ===\n")
    results=single_run_tests(test[0],test[1],0,len(test[1]),options)
    allresults.append(results)

  if len(alltests)>1:
    sum_realtestcount=0
    sum_lenokresults=0
    sum_failedresults=[]
    for result in allresults:
      sum_realtestcount+=result[0]
      sum_lenokresults+=result[1]
      sum_failedresults+=result[2]
    print("\n=== Summary for all tests ===\n")
    print("Tests run:",sum_realtestcount)
    print("OK tests:",sum_lenokresults)
    print("Failed tests:",len(sum_failedresults))
    if len(sum_failedresults)>0:
      print()
      print("Tests which failed:")
      for result in sum_failedresults:
        print("Input:",result[0][0])
        print("Expected:",result[0][1])
        print("Received:",result[1])


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
    if show_tests: print("Input:",test[0])
    prompt=test[0]

    debug_print("prompt:",prompt)
    if not prompt:
      show_error("no prompt given")    
    
    try:
      if use_llm=="claude": 
        debug_print("claude",claudeversion)
        result=call_claude(claudeversion,prompt,sysprompt,max_tokens)  
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
    outtext=linestart+prompt+separator+str(test[1])+separator+str(result)+"\n"
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
    conn = http.client.HTTPSConnection(host)   
    conn.request("POST", baseurl, calltxt,
                headers={
      "content-Type": "application/json", 
      "anthropic-version": "2023-06-01",
      "x-api-key": key
      #"anthropic-beta": "structured-outputs-2025-11-13"
    })    
    response = conn.getresponse()  
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
    sf=open(secrets_file,"r")
    txt=sf.read()
  except:
    show_error("Could not read file containing gpt api key: "+str(secrets_file))
  try:  
    data=json.loads(txt)
  except:
    show_error("Could not parse json text containing gpt api key in: "+str(secrets_file))  
  if "gpt_key" not in data or not (data["gpt_key"]):
    show_error("Could not find gpt api key in: "+str(secrets_file))
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
  conn = http.client.HTTPSConnection(host)
  conn.request("POST", baseurl, calltxt,
               headers={
    "Host": host, "Content-Type": "application/json", "Authorization": "Bearer "+key 
  })
  
  response = conn.getresponse()
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
