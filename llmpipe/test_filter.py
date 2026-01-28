#!/usr/bin/env python3

# Convert and filter parsing tests to make them neutral to world knowledge
#
# Run the program with one or more test files as arguments: 
# it will output a neutralized and filtered version of the tests
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

# ====== configuration =========

show_tests=False # set to False to suppress printing of all tests during work

# ====== globals ========

test_files=[]

# ======== replacements =======

replacements={
  "elephant": "elgant",
  "elephants": "elgants",
  "animal": "anserl",
  "animals": "anserls",
  "bird": "birrid",
  "birds": "birrids",
  "fox": "fornex", 
  "foxes": "fornexes",
  "rabbit": "ralgot",
  "rabbits": "ralgots",
  "sparrow": "sporex",
  "sparrows": "sporexes",
  "penguin": "penstun",
  "penguins": "penstuns",
  "mice": "mirks", 
  "mouse": "mirk", 
  "squirrel": "squntel",
  "squirrels": "squntels",
  "cat": "canlot",
  "cats": "canlots",
  "bear": "berkir", 
  "bears": "berkirs", 
  "boxer": "bonter",
  "boxers": "bonters",
  "father": "falgor",
  "fathers": "falgors",
  "child": "chormod", 
  "children": "chormods",
  "grandfather": "grentir",
  "grandfathers": "grentirs",
  "parent": "palkot",
  "parents": "palkots",
  "male": "marke", 
  "female": "ferke", 
  "grandson": "grelkon", 
  "grandsons": "grelkons",
  "granddaughter": "griltor",
  "granddaughters": "griltors",
  "car": "calpor",
  "cars": "calpors",
  "bike": "biste",
  "bikes": "bistes",
  "toy": "torky",
  "toys": "torkys",
  "tail": "tastol", 
  "tails": "tastols", 
  "trunk": "trenpok",
  "trunks": "trenpoks",
  "spoon": "spelkon", 
  "spoons": "spelkons", 
  "fork": "folkok",
  "forks": "folkoks",
  "wheelbarrow":"whartow",
  "wheelbarrows":"whartows",

  # locations 

  "tallinn": "tasmertin", 
  "riga": "rimalka", 
  "estonia": "eslenidia", 
  "latvia": "laskonia", 
  "europe": "eukemine", 
  "earth": "ealinh", 
  "america": "amastia",
  "estonian": "eslenidian",
  "emajogi": "emoskeni", 
  "nile": "nirtome",

  # allen-inspired examples

  "France": "Frelke",
  "UK": "Ukelmia", 
  "French": "Frelkish",

  "ostrich": "ostendich",
  "ostriches": "ostendiches",
  "eagle": "eastre",
  "eagles": "eastres",
  "Fiona": "Filenia",
  "Muggle": "Murtine",
  "Mr Dursley": "Mr Dolminy", 
  "American": "Amandian", 
  "Americans": "Amandians",
  "Catholic": "Carothic",
  "Catholics": "Carothics",


  "Clinton": "Sullivan", 
  "Dole": "Linster",

  "yellow": "roundish"
}
"""
Elephant, animal, bird, fox, rabbit, sparrow, penguin, mice, mouse, squirrel
cat
bear, boxer
father, child (*), grandfather, parent, male, female, grandson, granddaughter
car
tail, trunk
spoon fork

Tallinn, Riga, Estonia, Latvia, Europe, Earth, America
Estonian
Emajogi, Nile,

France, UK, French
ostrich, eagle
Fiona

Muggle, Mr Dursley, American, Catholic

Clinton, Dole


yellow 

"""

# ======== testing program ======

new_tests=[]

def main():  
  global test_files, new_tests
  if len(sys.argv)<2:    
    print("Please give test files as arguments")
    return
  for el in sys.argv[1:]:
    test_files.append(el)  
  #print("test files",test_files)
  for testfile in test_files:
    new_tests=[]
    process_test_file(testfile)
    print_tests(new_tests)   

def print_tests(tests):
  print("[")
  l=len(tests)
  i=0
  for test in tests:
    i+=1
    print_test(test)
    if i==l:
      print()
    else:
      print(",") 
  print("]")    

def print_test(test):
  print(" [",end="")
  j=0
  for el in test:
    j+=1
    if type(el)==str:
      print('"""',end="")
      print(el,end="")
      print('"""',end="")
    else:
      print(el,end="")
    if j!=len(test):
      print(", ",end="")    
  print("]",end="")

def process_test_file(testfile):
  global new_tests
  try:
    f=open(testfile,"r")
    s=f.read()
  except:
    print("Could not read test file",testfile)  
    return
  try:  
    tests=eval(s)
  except BaseException as err:
    print("Error parsing test file",testfile)
    sys.exit(0)        
  results=[]  
  for test in tests:
    if (not test) or (type(test)!=list) or len(test)<2 or type(test[0])!=str:       
      continue
    if type(test[1])==str:
      continue    
    if "Who " in test[0]: continue
    if "What " in test[0]: continue
    if "When " in test[0]: continue
    if "Where " in test[0]: continue
    if "Whom " in test[0]: continue

    new_test=test    
    new_tests.append(new_test)
    #print(test,new_test)

def process_test_text(txt):
  origtxt=txt
  for symb in [",",".","?","!","-"]:
    txt=txt.replace(symb," &"+symb+" ")  
  #print("txt",txt)  
  spl=txt.split(" ")  
  splres=[]
  #print("spl",spl)
  for word in spl:
    if word=="":
      splres.append("")
      continue
    if word[0].isupper():
      uppercase=True
      newword=word[0].lower()+word[1:]   
    else:
      uppercase=False  
      newword=word
    if len(word)>2 and word[-2:]=="'s":
      suffix=True
      newword=newword[:-2]
    else:    
      suffix=False
    #print("newword",newword)  
    if newword in replacements:
      newword=replacements[newword]      
    if uppercase:
      newword=newword[0].upper()+newword[1:]
    if suffix:
      newword=newword+word[-2:]  
    splres.append(newword)
  res=" ".join(splres)
  for symb in [",",".","?","!","-","?"]:
    res=res.replace(" &"+symb+" ",symb)
  return res    

    

# ========= run the program ======

if __name__ == "__main__":        
  main()  


# ========= the end =============
