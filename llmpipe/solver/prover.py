# Prover calling and prover result conversion parts of nlpsolver
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
import subprocess
import tempfile
import os
#import json

# ==== import other source files ====

# configuration and other globals are in globals.py
import globals

# making a nice nlp answer from json answer is in answer.py
from answer import *

# small utilities are in utils.py
from utils import *

from cache import *

# === calling the prover ===
 
def call_prover(logic):     
  if globals.options["debug_print_flag"]: 
    print("solve logic:")
    print("[")
    for i in range(len(logic)):
      s="  "+json.dumps(logic[i])
      if i<len(logic)-1: s+=","
      print(s)
    print("]")  
  #js=json.dumps(question,indent=2)
  #print("js:",js)  
  #pp = pprint.pformat(logic,width=80,indent=2,sort_dicts=False)   
  #instr=pp.replace("'","\"")
  instr=clause_list_to_json(logic)
  #debug_print("ppnice",ppnice)
  if (options["prover_print_flag"] or options["show_prover_flag"]) and not options["prover_nosolve_flag"]:
    print("\n=== prover input: === \n")
    print(instr)
  if options["prover_nosolve_flag"]:
    return(instr)    
  try:  
    infile,infilename=tempfile.mkstemp() 
  except:
    return("Error: failed to make a temporary file to write input to. ")  
  #print("infilename",infilename) 
  try:
    #infile=open(globals.prover_infile,"w")    
    #infile=open(infilename,"w")
    os.write(infile,str.encode(instr))
    os.close(infile)
    #infile.close()
  except KeyboardInterrupt:
    raise  
  except:
    os.remove(infilename)
    return("Error: failed to write prover infile "+infilename)     
  path=globals.prover_fname
  #decodedd=data.decode('ascii')
  #print("capi called with data",decodedd)
  params=[path]
  if not options["nokb_flag"]: 
    params=params+["-usekb",memkb_name]
  if options["prover_axiomfiles"]==False:
    params.append(globals.prover_axiomfile)
  else:
    for el in options["prover_axiomfiles"]:
      params.append(el)
  if options["prover_print"]:
    params=params+["-print",str(options["prover_print"])]
  if options["prover_strategy"]:
    params=params+["-strategy",options["prover_strategy"]]
  if options["prover_seconds"]:
    params=params+["-seconds",str(options["prover_seconds"])]    
  params.append(infilename)
  if options["usekb_flag"]: params=params+globals.usekb_prover_params
  else: params=params+globals.prover_params
  params=params+["--datafolder",prover_datafolder]
  if options["prover_print_flag"] or options["show_prover_flag"]:
    print("\n=== prover params: === \n\n"," ".join(params))

  sres=get_proof_from_cache(None,params)
  if not sres:
    try:
      calc=subprocess.Popen(params, stdout=subprocess.PIPE).communicate()[0]
    except KeyboardInterrupt:
      raise  
    except:
      return "Error: prover gk is not available or crashed: check nlpgobals.py for gk path."  
    sres=calc.decode('ascii') 
    add_proof_to_cache(params,sres)  
  os.remove(infilename)
  if options["prover_print_flag"] or options["show_prover_flag"]:  
    print("\n=== prover output: === \n\n",sres)
    print("\n=== end of prover output === \n\n")   
  return sres


# =========== the end ==========