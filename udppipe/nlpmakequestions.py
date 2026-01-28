#!/usr/bin/env python3

# Creating questions from question-preparing material
#
# Run the program and it will print out the questions, to be piped to a file.
#
#-----------------------------------------------------------------
# Copyright 2024 Tanel Tammet (tanel.tammet@gmail.com)
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

source_file="tests_wikipedia_source.py"

big_merge=True

# ======== testing program ======


def main():  
  try:
    f=open(source_file,"r")
    s=f.read()
  except:
    print("Could not read source file",source_file)  
    return
  try:  
    tests=eval(s)
  except BaseException as err:
    print("Error parsing source file",source_file," err "+str(err))
    print()
    return
  #print(tests) 
  converted=[]
  for test in tests:
    if (not test) or len(test)<2: continue
    head=test[0]
    questions=test[1:]
    for question in questions:
      if big_merge:
        head=merge_into(test[0],tests)
      text=head+" "+question[0]
      res=question[1] 
      newtest=[text,res]
      converted.append(newtest)
  print("[")    
  #f.write("[\n")
  count=0    
  for el in converted:
    count+=1
    #print("el",el)
    #print("[\""+el[0]+"\""+","+str(el[1])+","+str(json.dumps(el[2]))+"]",end="")
    #s="[\"\"\""+el[0]+"\"\"\""+","+str(el[1])+","+str(json.dumps(el[2]))+"]"
    s="[\"\"\""+el[0]+"\"\"\""+","+str(el[1])+"]"
    print(s,end="")
    #f.write(s)
    if count<len(converted):
      print(",")
      #f.write(",\n")
    else:
      print()  
      #f.write("\n")
  print("]")    
  #f.write("]\n")    

def merge_into(head,tests):
  txt=""
  l=len(tests)
  mid=int(l/2)
  for i in range(0,l):
    store=True
    s=tests[i][0]
    if i==mid:      
      if s!=head:
        s=s+" "+head
      else:
        pass
    elif s==head:
      store=False
      #print("***",i,"***")
    if store:  
      if txt: txt+=" "
      txt+=s
  #print(txt)
  #sys.exit(0)  
  return txt  

# ========= run the program ======

if __name__ == "__main__":        
  main()  


# ========= the end =============
