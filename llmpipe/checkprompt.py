#!/usr/bin/env python3

# Verifying syntax of a system prompt
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
import json


# ======== configuration ======

testfile="logifyprompt6.txt"

# ======== testing program ======

varstrings=["X","Y","Z","U","V","W","A","B","T","S"]
errs=0

def main(): 
  global errs
  errs=0
  prefixes={}
  try:
    f=open(testfile,"r")
    lines=f.readlines()      
  except:
    print("Could not read test file",testfile)  
    return
  f.close()
  for line in lines:
    if not("=>" in line and "[" in line and "]" in line):
      continue
    spl=line.split("=>")
    if len(spl)!=2:
      print("** weird line, skipping the line:",line)
      errs+=1
      continue
    #print(spl) 
    part=spl[1]
    try:
      parsed=json.loads(part)
    except:
      print("** failed parsing json in the line:",line)  
      errs+=1
    #print(parsed) 
    collect_prefixed(parsed,prefixes,[],line)
  lst=[]  
  for key in prefixes:
    lst.append([key,prefixes[key]])
  lst.sort(reverse=True, key=lambda x: x[1])
  print("** issues found and reported above: ",errs)
  print("** prefixes found with counts:")
  for el in lst:
    print(el[0],el[1])
  #for key in prefixes:
  #  print(key,prefixes[key])  

def collect_prefixed(x,prefixes,boundvars,line):
  global errs
  if type(x)!=list:
    if x in varstrings:
      if x not in boundvars:
        print("** unbound var in line:",line)
        errs+=1
    return
  head=x[0]
  if type(head)==list:
    print("** wrong json logic structure in line:",line)
    errs+=1
    return
  if head in ["exists","forall","ask"]:
    if x[1] not in varstrings:
      print("** weird quantified object in line:",line)
      errs+=1
    else:
      if x[1] not in boundvars:
        boundvars.append(x[1])  
  if head in prefixes:
    prefixes[head]=prefixes[head]+1
  else:
    prefixes[head]=1
  for el in x:
    collect_prefixed(el,prefixes,boundvars,line)   


  

# ========= run the program ======

if __name__ == "__main__":        
  main()  


# ========= the end =============    