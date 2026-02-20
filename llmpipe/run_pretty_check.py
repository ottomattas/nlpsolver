#!/usr/bin/env python3
import sys
sys.path.insert(0, "solver")
import pretty
pretty.noquotes = True
from logconvert import rawlogic_convert

examples = [
  ("John is a person",
   ["and",["@id","S1",["holds","W0",["isa","person","John 1"]]]]),

  ("John is in Paris or London",
   ["and",["@id","S1",["holds","W0",
     ["or",
       ["is rel2","in","John 1","https://en.wikipedia.org/wiki/Paris"],
       ["is rel2","in","John 1","https://en.wikipedia.org/wiki/London"]
     ]
   ]]]),

  ("Eve does not have a bike",
   ["and",["@id","S1",["holds","W0",
     ["not",["exists","X",["and",["isa","bike","X"],["have","Eve 1","X"]]]]
   ]]]),

  ("All green things are rough (strict rule)",
   ["and",["@id","S1",["holds","W0",
     ["forall","X",["implies",
       ["and",["isa","thing","X"],["has property","green","X"]],
       ["has property","rough","X"]
     ]]
   ]]]),

  ("Dogs have tails (normal rule, confidence 0.99)",
   ["and",["@id","S1",
     ["and",
       ["holds","W0",["forall","X",["implies",
         ["isa","dog","X"],
         ["normally",["exists","Y",["and",["isa","tail","Y"],["have","X","Y"]]]]
       ]]],
       ["@p","S1",0.99]
     ]
   ]]),

  ("Dogs do not have tails (strict negation rule)",
   ["and",["@id","S1",["holds","W0",
     ["forall","X",["implies",
       ["isa","dog","X"],
       ["not",["exists","Y",["and",["isa","tail","Y"],["have","X","Y"]]]]
     ]]
   ]]]),

  ("Transitivity: X connected Y, Y connected Z => X connected Z",
   ["and",["@id","S1",["holds","W0",
     ["forall","X",["forall","Y",["forall","Z",
       ["implies",
         ["and",["is rel2","connected to","X","Y"],["is rel2","connected to","Y","Z"]],
         ["is rel2","connected to","X","Z"]
       ]
     ]]]
   ]]]),

  ("Chinese have a capital (exists outside forall, Skolem function)",
   ["and",["@id","S1",
     ["and",
       ["holds","W0",["exists","Y",["and",
         ["isa","capital","Y"],
         ["forall","X",["implies",["isa","chinese","X"],["have","X","Y"]]]
       ]]],
       ["@p","S1",0.99]
     ]
   ]]),

  ("John has a car? (question)",
   ["and",["@id","S1",
     ["question",["exists","X",["and",["isa","car","X"],["have","John 1","X"]]]]
   ]]),

  ("Who likes Mike? (ask query)",
   ["and",["@id","S1",
     ["ask","X",["and",
       ["isa","person","X"],
       ["has degree rel2","like","X","Mike 1","none","person"]
     ]]
   ]]),
]

for i, (label, inp) in enumerate(examples, 1):
    print("=" * 70)
    print(f"EXAMPLE {i}: {label}")
    print("-" * 70)
    print("INPUT:")
    print(pretty.pp_str(inp))
    print()
    result = rawlogic_convert(inp)
    print("OUTPUT:")
    print(pretty.pp_str(result))
    print()
