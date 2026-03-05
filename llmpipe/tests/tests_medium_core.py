# core tests used by the nlptest.py

[
 
  # first basic test

  ["""Elephants are animals. Elephants are animals?""",True],

  # other nine basic tests

  ["""Elephants are animals. John is an elephant. John is an animal?""",True],
  ["""Elephants are not birds. John is an elephant. John is not a bird?""",True],
  ["""Elephants are animals. John is an elephant. Who is an animal?""","""John."""],
  ["""Elephants are not birds. John is an elephant. John is a bird?""",False],
  ["""Elephants are animals. Who is an animal?""","""An elephant."""],
  ["""Elephants are grey animals. John is an elephant. Who is grey?""","""John."""],
  ["""Elephants are big animals. John is an elephant. Who is nice?""",None],
  ["""Elephants have long trunks. John is an elephant. Who has a trunk?""","""John."""],
  
  ["""If X1 is a father of Y1, Y1 is a child of X1. John is a father of Mike. Who is a child of John?""","""Mike."""],

  # basic questions with no rules

  ["""John is a tall man or not a tall man?""",True],
  ["""John has a car or does not have a car?""",True],
  ["""John has a car and does not have a car?""",False],
  ["""John has a car?""",None],
  
  # questions with basic combos of names and non-names

  ["John was yellow. John was yellow?",True],
  ["John was yellow. John was nice?",None],
  
  # basic quantifiers

  ["""Elephants are animals. Elephants are animals?""",True],
  ["""Elephants are animals. Some elephant is an animal?""",True],
  ["""Elephants are animals. All elephants are animals?""",True],
  ["""Elephants are animals. John is an animal?""",None],
  
  ["""No elephant is an animal. No elephant is an animal?""",True],
  ["""No elephant is an animal. Some elephant is an animal?""",False],

  # more complex quantifier uses

  ["It is not true that all big yellow cats are strong. Some yellow cats are not strong?",True],
  ["It is not true that all big yellow cats are strong. Some red cats are not strong?",None],  
  ["John likes all boxers. Mike is a boxer. John likes Mike?",True],
  ["John likes some boxers. Mike is a boxer. John likes Mike?",None],

  # "A" in the question is interpreted as "some" in case this kind of object has been recently talked about

  ["The red square has a nail. A blue square has a hole. A square has a nail?",True], 
  ["The red square has a nail. A blue square has a hole. A square has a dot?",None],
   
  #["""It is false that some cats are strong. Strong cats are not weak. Weak cats are not strong. 
  #    All cats are weak?""",True] # Err since "It is false" applied to strong, and not whole sentence


  # sentences with and-or-nor-xor combos

  ["""Elephants, foxes and rabbits are nice animals and good toys. John is an elephant. John is a toy?""",True], 
  ["""Elephants, foxes and rabbits are neither birds nor small fish. John is a rabbit. John is a bird?""",False],
  
  ["""If animal or bird is nice and simple, it is cute. John is cute?""",None],
  ["""If animal or bird is nice and simple, it is cute. John is a nice and simple animal. John is cute?""",True],
 
  ["Elephants are animals. Birds are animals?",None],
 
  ["John is a red or black elephant. John is an elephant. John is red. John is black?",False],

  # sentences with subject property logic

  ["""Big or strong elephants are nice. John is a big elephant. John is nice?""",True], 
  ["""Big or strong elephants are nice. John is an elephant. John is nice?""",None],
 
  # sentences with "have"

  ["""Elephants have trunks. Elephants have trunks?""",True],
  ["""No elephant has wings. No elephant has wings?""",True],
  ["""No elephants have wings. Some elephant has wings?""",False],
  ["""Elephants have no wings. Some elephant has wings?""",False],
 
  ["""Elephants have long trunks and short tails. John is an elephant. Who has a trunk and a tail?""","""John."""],
  ["""Elephants have long trunks and short tails. John is an elephant. Who has a long trunk and a short tail?""","""John."""],
  ["""Elephants have long trunks and no wings. John is an elephant. John has a wing?""",False],
 

  ["""Elephants have long trunks. John is an elephant. John has a trunk?""",True],
  ["""Elephants have no trunks. John is an elephant. John has a trunk?""",False],
  ["""Elephants have long grey trunks. John is an elephant. Who has a trunk?""","""John."""],
 
  ["""If an animal has a trunk, it is an elephant. John has a long trunk. John is an animal. 
      John is an elephant?""",True],
  ["""If an animal has a trunk, it is an elephant. John has a long trunk.  
      John is an elephant?""",None],    

  # if-then rules with a general left side

  ["If cars are red, elephants are nice. Cars are red. Elephants are nice?",True],
  ["If cars are red, elephants are nice. Elephants are nice?",None],
 

  # simple if-then rules with variables

  ["If X is cool then X is red. John is cool. Mike is red?",None], 
  ["If X is cool then X is red. John is cool. John is red?",True], 

  # if-then rules with variables and lists and or-s

  ["""If X1 is a father of Y1, Y1 is a child of X1. John is a father of Mike. Who is a child of John?""","""Mike."""],
  ["""If X1 is a father of Y1, Y1 is a child of X1. John is a father of Mike and Mary. 
      Who is a child of John?""","""Mike and Mary"""], 

  # more complex if-then rules combos with variables 

  ["""If X1 is a grandfather of Y1, Y1 is not a child of X1. John is a grandfather of Mike. Who is not a child of John?""","""Mike."""],
 
  ["""If X1 is a father of Y1, Y1 is a child of X1. 
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1. 
      John is a father of Mike. Luke is a father of John. 
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1. 
      If X1 is male and X1 is a grandchild of Y1, X1 is a grandson of Y1. 
      Mike is male. Mike is a grandson of Luke?""",True],
  ["""If X1 is a father of Y1, Y1 is a child of X1. 
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1. 
      John is a father of Mike and Mickey. Luke is a father of John. 
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1. 
      If X1 is male and X1 is a grandchild of Y1, X1 is a grandson of Y1. 
      Mike and Mickey are male. Who is a grandson of Luke?""","""Mike and Mickey."""],
  

   # comparisons

   ["""John is nicer than Mike. Mike is nicer than Eve. Who is nicer than Eve?""",
     """John and Mike."""],
   ["""John is nicer than Mike. Mike is nicer than Eve. Who is nicer than John?""",
     None], 


   # containment 

   ["""Tallinn is in Estonia. Estonia is not outside Europe. Earth contains Europe.  
       Estonia contains Tartu. Riga is not in Estonia. Tallinn is in what?""",
    """Earth, Europe and Estonia."""],
 
   ["""Tallinn is in Estonia. Estonia is not outside Europe. Earth contains Europe.  
       Estonia contains Tartu. Riga is not in Estonia. Riga is in Estonia?""",
    False], 
   [""""Riga is outside America. Riga is not in what?""","""America."""], 
   [""""Riga is not in America. What is not in America?""","""Riga."""],


   ["""If a city is in Estonia, it is an Estonian city. Tallinn is in Estonia. Tallinn is a city. 
     What is an Estonian city?""","""Tallinn."""],
   
   # Numeric uncertainty  

   ["""Elephants are probably animals. John is an elephant. John is an animal?""","""Probably true."""],
     ["""It is unlikely that elephants are animals. John is an elephant. John is an animal?""","""Probably false."""],

   ["""It is true that John is a child of Mike. John is a child of Mike?""",True],
   ["""It is false that John is a child of Mike. John is a child of Mike?""",False],
  
  ["""Probably elephants have long trunks. John is an elephant. John has a trunk?""","""Probably true."""],
  ["""Probably elephants have no trunks. John is an elephant. John has a trunk?""","""Probably false."""],
  
  
   ["""Tallinn is probably in Estonia. Tallinn is in Estonia?""", """Probably true."""],
   ["""Tallinn is hardly in Latvia. Tallinn is in Latvia?""", """Likely false."""],
  
   ["""John is an elephant with a probability 100 percent. John is an elephant?""", True],
   ["""John is an elephant with a probability 0 percent. John is an elephant?""", False],
 
   ["""If X1 is a father of Y1, Y1 is a child of X1. 
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1. 
      John is a father of Mike and Mickey. Luke is a father of John. 
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1. 
      If X1 is male and X1 is a grandchild of Y1, X1 is a grandson of Y1. 
      Mike and Mickey are not female. Any person is male or female. 
      Who is a grandson of Luke?""","""Mickey and Mike."""],
  ["""If X1 is a father of Y1, Y1 is a child of X1. 
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1. 
      John is a father of Mike and Mickey. Luke is a father of John. 
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1. 
      If X1 is male and X1 is a grandchild of Y1, X1 is a grandson of Y1. 
      Mike or Mickey are not female. Any person is male or female. 
      Who is a grandson of Luke?""","""Mike or Mickey."""],

  # numerically uncertain quantors

  ["""Most bears are big. John is a bear. John is big?""","""Probably true."""],
  ["""Many bears are big. John is a bear. John is big?""","""Perhaps true."""],
  ["""Few bears are big. John is a bear. John is big?""","""Likely false."""],

  # basic default rules
   
  ["""Elephants are big. Young elephants are not big. 
      Mike is an elephant. John is a young elephant. Mike is big?""",True,["default"]],
  ["""Elephants are big. Young elephants are not big. 
      Mike is an elephant. John is a young elephant. John is big?""",False,["default"]],    
  ["""Elephants are big. Young elephants are not big. 
      Mike is an elephant. John is a young elephant. Who is big?""","""Mike.""",["default"]],
  ["""Elephants are big. Young elephants are not big. 
      Mike is an elephant. John is a young elephant. Who is not big?""","""John.""",["default"]],   
  ["""Elephants are big. Young elephants are not big. 
      Who is big?""","""An elephant.""",["default"]],      
  ["""Elephants are big. Young elephants are not big. 
      Who is not big?""","""A young elephant.""",["default"]], 

  ["Penguins are birds who do not fly. Birds fly. John is a penguin. John flies?",False,["default"]],
  ["Penguins are birds. Penguins do not fly. Birds fly. John is a penguin. John flies?",False,["default"]],
  ["Penguins are birds who do not fly. Birds fly. John is a bird. John flies?",True,["default"]],
  ["Penguins are birds. Penguins do not fly. Birds fly. John is a bird. John flies?",True,["default"]],


  # default rules with a (mostly) general-noun question

  ["Cars are nice. Cars are nice?",True],      # no defaults here, just basic
  ["Cars are nice. Cars are not nice?",False], # no defaults here, just basic
  ["Red cars are not nice. Cars are nice. Cars are nice?",True,["default"]],
  ["Red cars are not nice. Cars are nice. Cars are not nice?",False,["default"]],
  ["Red cars are not nice. Cars are nice. Red cars are nice?",False,["default"]],
  ["Red cars are not nice. Cars are nice. Red cars are not nice?",True,["default"]],
 
  ["Penguins are birds. Penguins do not fly. Birds fly. Who flies?","A bird.",["default"]],
  ["Penguins are birds. Penguins do not fly. Birds fly. Who does not fly?","A penguin.",["default"]],
  
  # do-actions

  ["""If a bear eats red berries, it is big. John eats berries. John is a bear. 
     John is big?""",None],
  ["""If a bear eats red berries, it is big. John eats red berries. John is a bear. 
     John is big?""",True],   
  ["""If X1 eats berries, it is a bear. John eats red berries. John is a bear?""",
     True],
  ["""Bears eat berries. John is a bear. John eats berries?""", True],   
  ["""Bears eat berries. John is a bear. John eats some berries?""", True],
  ["""Bears eat berries. John is a bear. John eats all berries?""", None],
  ["""Bears eat all berries. John is a bear. John eats all berries?""", True],
  

  # default rules and do-actions 

  ["""Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike is a bird. 
    John does not fly?""",True,["default"]],
  ["""Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike is a bird. 
    Mike flies?""",True,["default"]],  
  ["""Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike is a bird. 
    John runs?""",None,["default"]],  
 
  # default rules and can-actions

  ["""Birds can fly. Baby birds can not fly. John is a baby bird. Mike and Eve are birds. 
      Who can fly?""","""Mike and Eve.""",["default"]],
   
  # default rules and can-do mix-actions

  ["""Birds fly. No penguin can fly. Penguins are birds. John is a penguin. John can fly?""",False,["default"]],
  ["""Birds fly. No penguin can fly. Penguins are birds. John is a penguin. John flies?""",False,["default"]],

  # action properties

  ["Bears eat berries in a forest. Bears eat berries in forest?",True],
  ["Bears eat berries in a forest. Bears do not eat berries in forest?",False],
  ["Bears eat berries in a forest. Bears eat berries in a field?",None],
  ["Bears eat berries in a forest. Bears eat berries?",True],
 
  ["Bears eat red berries in a deep forest. John is a bear. John eats red berries in a deep forest?",True],
  ["Bears eat red berries in a deep forest. John is a bear. John eats no berries?",False],
  ["Bears eat berries in a deep forest. John is a bear. John eats berries in a shallow forest?",None],
  ["Bears quickly eat berries in a deep forest. John is a bear. John quickly eats berries in a deep forest?",True],

   ["""If a bear quickly eats berries in a deep forest, it is hungry. John is a bear.
     John quickly eats berries in a deep forest. John is hungry?""",True],
  
  ["""If a bear eats berries in a forest, it is hungry. John is a brown bear. 
      John quickly eats berries in a deep forest. Who is hungry?""","""John."""],

  # determinants a and the

  ["""A big bear was strong. The bear was nice. Who was nice and strong?""","""The big bear."""],  
  ["""A big bear was strong. The small bear was nice. Who was nice and strong?""",None],
  ["""A big bear was strong. The small bear was nice. Who was nice?""","""The small bear."""],
 
  ["John does not eat a carrot. Mike eats carrots. Who eats carrots?","Mike"],
  ["John does not eat a carrot. Mike eats carrots. Who does not eat carrots?","John"],

  # using "who"

  ["""Big bears who have a trunk have a tail. John is a big bear. John has a trunk. John has a tail?""",True],
 
  ["""Bears who have a trunk are nice. John is a bear. John has a trunk. John is nice?""",True],
  ["""Bears who have a trunk are nice. John is a bear. John has a nose. John is nice?""",None],
  
  ["""Bears who are nice and eat berries have a tail. John is a nice big bear. John eats berries. John has a tail?""",True],
  ["""Bears who are nice and who eat berries have a tail. John is a nice big bear. John eats berries. John has a tail?""",True],
  ["""Bears who are nice and who eat berries have a tail. John is a nice big bear. John eats fish. John has a tail?""",None],

  ["Bears who are big are strong. John is a big nice bear. John is strong?",True],
  ["Bears who are big are strong. John is a bear. John is strong?",None],
 

  ["If a bear who is big is strong, it is nice. John is a big strong bear. John is nice?",True],
 
  [" The white mouse is strong. The mouse is white?",True], 
  [" The big mouse is strong. The mouse is a big mouse?",True],

   ["The bear who was white and ate a big fish was cool. The white bear who ate a strong fish was cool? ", None],
  ["The nice bear who was white and ate a big fish was cool. The white nice bear who ate a big fish was cool? ", True],


  # qualified property: very and somewhat
  
  ["John is very big. John is extremely big?",True],
  
  ["John is very big. John is big?",True],
  ["John is very big. John is somewhat big?",False],
 
  ["John is a big mouse. John is big?", True],
  ["John is a big mouse. John is a big mouse?", True],
  ["John is a big mouse. John is a big thing?", None],

  # more subsentences

  ["John had a car which Eve bought. John had a car which Eve bought?",True],
  ["John had a car which Eve bought. John had a car which Eve saw?",None],
  
  ["John had a car Eve bought. John had a car which Eve bought?",True],
  ["John had a car Eve bought. John had a car which Eve saw?",None],
  ["John had a car Eve bought. John had a car which Mike bought?",None],

  ["John had a car Eve bought. Eve bought a car?",True], # had a problem with PROPN and not NER for Eve
 
  ["John had a car Eve bought. John bought a car?",None],

  ["John had a car Eve bought. John had a car which Eve bought?",True],
 
  ["John drove a car which Eve bought. John drove a car which Eve bought?",True],
  ["John drove a car which Eve bought. John drove a car which Eve saw?",None],
  
  ["John is a man Eve liked. John is a man whom Eve saw?",None],
  ["John is a man Eve liked. John is a man whom Mike liked?",None],

  ["John is a man Eve liked. John is a man whom Eve liked?",True],
  ["John is a man whom Eve liked. John is a man Eve liked?",True],
 
  ["A man had a car a woman bought. A man bought a car?",None],
  ["A man had a car a woman bought. The man did not have a car?",False],



  ["A man drove a car which a woman bought. A woman bought a car?",True],
  ["A man drove a car which a woman bought. A woman bought the car?",True],

  ["A man had a car which a woman bought. A man had a car?",True],
  ["A man had a car which a woman bought. A man had the car?",True],
  ["A man had a car which a woman bought. A woman had the car?",None],
  ["A man had a car which a woman bought. A woman bought a car?",True], 
  ["A man had a car which a woman bought. A woman bought the car?",True],
  ["A man had a car which a woman bought. A man bought the car?",None],


  # capitalization of first noun word

  ["Cars are old. Cars are old?",True], 

  # questions about several objects

  ["A red car is big. A new car is small. A car is red?",True],
 
  ["A red car is big. A new car is nice. The car is new?",True],
  ["A red car is big. A new car is nice. The car is red?",None],
  ["A red car is big. A new car is nice. The red car is big?",True],
  ["A red car is big. A new car is nice. The new car is nice?",True],

  ["A red car is big. The red car is strong. The car is red and strong?",True],
  ["A red car is big. The car is strong. The car is red and strong?",True],
  ["A red car is big. The car is strong. The car is black?",None],
  ["A red car is big. The car is strong. A car is black?",None],

   # understanding and questions about non-subject objects

  ["A man had a car which a woman bought. The car was red. A man had a car?",True],
  ["A man had a car which a woman bought. The car was red. The man had the car?",True],
  
  ["""A man who ate breakfast had a car which a woman bought. The car was red.
     A man who ate breakfast had a red car which a woman bought?""",True],
  ["""A man who ate breakfast had a car.
     The man ate breakfast?""",True],   
  
  # Past with did+verb 

  ["A man did have a car. A man had a car?",True],
  ["A man had a car. A man did have a car?",True],


  # Name gender tests
  ["Mary saw John. She was nice. Who was nice?","Mary"],
  ["Mary saw John. He was nice. Who was nice?","John"],
  ["John saw Mary. She was nice. Who was nice?","Mary"],
  ["John saw Mary. He was nice. Who was nice?","John"],
  # Word gender tests
  ["A mother saw a man. She was nice. Who was nice?","The mother"],
  ["A mother saw a man. He was nice. Who was nice?","The man"],
  ["A boy saw a girl. She was nice. Who was nice?","The girl"],
  ["A boy saw a girl. He was nice. Who was nice?","The boy"],
  # Single/plural tests
  ["The elephants saw a fox. They were nice. The elephants were nice?",True],
  ["The elephants saw a fox. They were nice. The fox was nice?",None],
 
  # These/they
  ["The aunts saw shoes. These were nice. What was nice?","The shoes",["nochange"]],
   ["The foxes saw aunts. These were nice. What was nice?","The foxes",["nochange"]],
  
  ["A car had a dent. This was deep. What was deep?","A dent",["nochange"]],
  ["A car had a dent. It was fast. What was fast?","The car",["nochange"]],

   # subclass tests
  ["An elephant was strong. The animal lifted a stone. Who lifted the stone?","The elephant",["nochange"]],
  ["An elephant was strong. An animal lifted a stone. Who lifted the stone?","The animal",["nochange"]],
  

   # More pronoun tests

  ["Mary was in a room. She was in the room?",True,["nochange"]], 
 
  ["John was bad. She was in a room. John was in a room?",None,["nochange"]],
  ["She was in a room. Who was in the room?","She",["nochange"]],

  # Set sizes

  # core set size
  ["John has three cars. John has three cars?",True],
  ["If John has three cars, John has three cars?",True],
  ["John has three cars. John has two cars?",False],
  
  ["Animals have two legs. Animals have three legs?",False],

   # superset size cannot be smaller
  ["John has three nice cars. John has two cars?",False],
 

  # used in condition
 
  ["John has cars. John has cars?", True],
  ["John has blue cars. John has a car?", True],
 
  # qualifiers of do-actions

  ["Penguins live in the water. Penguins live in water?", True],
  #["Penguins live in water. Penguins live in the water?", True],
 
  ["Penguins happily live in cold water. Penguins live in cold water?", True],
  ["Penguins happily live in cold water. Penguins live in hot water?", None],
  
  # .. of .. and ... the ... of ... examples

  ["The head of Mary is clean. The head of Mary is clean?",True],
 
  ["The car of Mary is clean. Mary has a car?",True],
 
  ["Mary's head is clean. A head of Mary is clean?",True],
 

  ["Elephant's head is green. John is an elephant. John has a head. John has a green head?", True],

 
  ["John saw the head of Mary. John saw a head of Mary?",True],
  ["John saw the head of Mary. John saw the head of Mike?",None],
  ["John saw the head of Mary. John saw a head?",True],
 
  ["John saw a twig of an elephant. The elephant had a twig?",True],
  ["John saw a twig of an elephant. The elephant had a spoon?",None],
 
  ["The hand of a man moved a wheel. The hand of a man moved a wheel?",True],
  ["The hand of a man moved a wheel. The man had a hand?",True],
  
  ["A blue hand of a man moved a wheel of a large wheelbarrow. A hand moved a wheel?",True],
  ["A blue hand of a man moved a wheel of a large wheelbarrow. A hand moved a wheelbarrow?",None],

  ["The blue hand of a man moved the wheel of the large wheelbarrow. Mary is a man?",None,[{"mary":"a tall object"}]],
  ["The blue hand of a man moved a wheel of the large wheelbarrow. Mary is a man?",None,[{"mary":"a tall object"}]],
 
  ["John ate berries with the edge of a spoon. John ate berries with the edge of a spoon?",True],
   ["John ate berries with the edge of a spoon. John ate berries with the edge of a fork?",None],
  ["John ate berries with the edge of a spoon. John ate berries with the tip of a spoon?",None],
 
  # obl and compound sentences
   
  ["Bears eat berries in a forest. Bears eat berries in a forest?",True],
  ["Bears eat berries in a forest. Bears eat berries in a big forest?",None],
  
  ["""John has a car which is nice and red. The car is red and nice?""", True],
  ["""John has a car which is nice and red. The red car is nice?""", True],
  ["""John has a car which is nice and red. The big car is nice?""", None],
 

  # conjunction usage with can, have etc

  ["John and Eve can swim. Mark and John are animals. Who can swim and is an animal?","John"],
  ["John and Eve can swim. Mark and John are animals. Who is an animal and can swim?","John"],
  ["John and Eve can swim. Mark is an animal. Who can swim and is an animal?",None],

  # conjunction usage with have 

  ["Cars are nice. Cars have brakes. Cars are nice and have brakes?", True],
  ["Cars are nice. Cars are nice and have brakes?", None],
 
  # no subject cases; with nsubj:pass and VerbForm=Part 

  ["John is defeated. John defeated?",None],
  ["John is defeated. Mike is defeated?",None],
 
  ["John is defeated. Who is defeated?","John"],
  ["John is defeated. John is not defeated?",False],
 
  ["An apple was eaten. John ate a pear. What was eaten?","The apple and the pear."],
  ["An apple was eaten. John ate a pear. What did eat?","Some unknown and John."], 
  ["""If an animal is cool and defeated then it is green. 
   John is an animal. John is cool. 
   Mike is an animal. Mike is cool. John is defeated. John is green?""",True],
  ["""If an animal is cool and defeated then it is green. 
   John is an animal. John is cool. 
   Mike is an animal. Mike is cool. John is defeated. Who is green?""","John"], 
   
  ["""If an animal is cool and defeated then it is green. 
   John is a defeated animal. 
   Mike is an animal. Mike is cool. John is green?""",None],  
 
  ["""If someone is a nice animal and badly defeated then they are weak. John and Mike are nice animals. 
    John is badly defeated. John is weak?""",True],
  ["""If someone is a nice animal and badly defeated then they are weak. John and Mike are nice animals. 
    John is badly defeated. Mike is weak?""",None],  

  # NER cases sometimes needing NER fixing
   
  ["Muggles cannot disappear. Mr Dursley is a Muggle. Mr Dursley can disappear?",False], 
  ["Muggles can not disappear. Mr Dursley is a Muggle. Mr Dursley can disappear?",False], 

  # Tests inspired by UD web docs examples 

   # nsubj docs examples
  ["Clinton defeated Dole. Clinton defeated Dole?",True],
  ["Clinton defeated Dole. Clinton defeated Mike?",None],
  ["Dole was defeated by Clinton. Dole was defeated by Clinton?",True],
  ["Dole was defeated by Clinton. Dole was defeated by Mike?",None],
 
  ["There is a ghost in the room. A ghost is in the room?",True],  
  ["There is a ghost in the room. There is a lamp in the room?",None],
  ["There is a ghost in the room. There is a ghost in the barn?",None],
 
  ["John is nice. Is it true that John is nice?",True],
    ["John is nice. Is it false that John is nice?",False],

  # What does and related questions

  ["John smokes tobacco with a probability 0.8. What does John smoke?","Likely a tobacco"],
  ["John smokes tobacco with a probability 10 percent. Does John smoke?",None],

  # Who is questions

  ["John Sweeney is a car. John Smith is bad. Who is John?","John Smith is bad."],
  ["John Sweeney is a car. John Smith is bad. Who is Sweeney?","John Sweeney is a car."],
    ["John Sweeney is not a car. Who is John?",None],
  ["John Sweeney is a car. Who is Mary?",None],
    # Who/Whom is_of questions

  ["Ellen is afraid of John. What is Ellen afraid of?","John"],
  ["Ellen is afraid of John. Who is Ellen afraid of?","John"],
  
  ["Ellen is fond of John. Whom is Ellen afraid of?",None],
  ["Ellen is fond of John. Ellen is afraid of who?",None],

  # Which questions
   
  ["""John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear. 
      Which man has an apple?""","John"],
  ["""John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear. 
      Which has a pear?""","Mike"],    
 
  ["""Squirrels can fly. Foxes cannot fly. Squirrels and foxes are animals. 
      Which table can fly?""",None],    
  
  # Where questions

  ["John is in a box. Mark is in a house. Where is John?","In the box."],
  ["John is in a box. Mark is in a house. Where is Mark?","In the house."],
  ["John is on a box. Mark is on a house. Where is John?","On the box."],
 
  ["A car is in a box and in a house. Where is the car?","In the house and in the box."],
  ["A car was in a box and in a house. Where was the car?","In the house and in the box."],
 
  # Complex location indication sentences plus where questions

  ["John is in the box which is in the red house. Where is John?","In the box and in the red house."],
  
  ["John is in the box at a red house. The box is at a house?",True],
  ["John is in the box at a red house. The red box is at a house?",None],
 
  # Location of general terms 
   
  # ["""Birds are in the box. Where are the birds?""","In the box."], # fails; maybe should fail? 
  ["""Birds are in the box. Where are birds?""","In the box."],
  ["""The birds are in the box. Where are the birds?""","In the box."],
  ["""The birds are in the box. Where are birds?""","In the box."],
  ["Birds near Tallinn are nice. John is near Tallinn. What is near Tallinn?","A bird near Tallinn"],
  ["Birds near Tallinn are nice. John is near Tallinn. Who is near Tallinn?","John"],
 
  # Simple confidences combined with the location

  ["Probably John is in a cave. Where is John?","Probably in the cave"],
   ["John is in a cave with a probability 90%. Where is John?","Likely in the cave"],
  ["John is in a cave with a probability 10%. Where is John?",None],

  # Location of actions

  ["""John ate candy in a house. John ate meat in a room. Where did John eat candy?""","In a house"],
   ["""John jumped high in a room. John jumped low near the garage. Where did John jump low?""","Near the garage"],  
  ["""John jumped high in a room. John jumped low near the garage. Where did John jump quickly?""",None],
  
  # Basic when questions
  
  ["During 1800, John jumped in a house. During 1800, John jumped?",True],
  ["During 1800, John jumped in a house. During 1801, John jumped?",None],
  ["During 1800, John jumped in a house. When did John jump?","During the year 1800"],
  ["During 1800, John jumped in a house. Where did John jump?","In a house"],
  

  # Basic measures and what questions

  ["Nile's length is 80 kilometers. The length of Nile is 80 kilometers?",True],
  ["Nile's length is 80 kilometers. The length of Nile is 90 kilometers?",False],
  ["Nile's length is 80 kilometers. Amazon's length is 20 kilometers. What is 80 kilometers long?","Nile"],
  ["Nile's length is 80 kilometers. Amazon's length is 20 kilometers. What has the length 20 kilometers?","Amazon"],   
  
  ["Nile is 10 meters long. Emajogi is 20 meters long. The nice river is 100 meters long. What is 100 meters long?", "The nice river"],
  ["The red straw is 10 meters long. The red straw is 10 meters long?",True],
  ["The red straw is 10 meters long. The red straw is 20 meters long?",False], 
  ["The red straw is 10 meters long. The blue straw is 5 meters long. What is 5 meters long?","The blue straw"], 
 
  ["The red car has the price two dollars. The blue car costs three dollars. What has the price 3 dollars?","The blue car"],
  ["The red car has the price two dollars. The blue car costs three dollars. The red car costs 3 dollars?",False],

  ["The red car has the price two dollars. The blue car costs three dollars. The price of the red car equals the price of the blue car?",False],
  ["The red car has the price two dollars. The blue car costs three dollars. The price of the red car equals the price of the red car?",True],


  # babi qa15_basic-deduction_test.txt

  ['Wolves are afraid of mice. Sheep are afraid of mice. Winona is a sheep. Mice are afraid of cats. Cats are afraid of wolves. Jessica is a mouse. Emily is a cat. Gertrude is a wolf. What is emily afraid of?', 'wolf', ['babi', 6, 4]],
  ['Wolves are afraid of mice. Sheep are afraid of mice. Winona is a sheep. Mice are afraid of cats. Cats are afraid of wolves. Jessica is a mouse. Emily is a cat. Gertrude is a wolf. What is winona afraid of?', 'mouse', ['babi', 2, 1]],
 
  # babi qa1_single-supporting-fact_test.txt
  
  ['John travelled to the hallway. Mary journeyed to the bathroom. Where is John?', 'In the hallway', ['babi', 0]],
  ['John travelled to the hallway. Mary journeyed to the bathroom. Daniel went back to the bathroom. John moved to the bedroom. Where is Mary?', 'In the bathroom', ['babi', 1]],
    
  # functional vs nonfunctional properties
  #["The color of the car is red. The car is red?", True],          


      
  # the following requires measure equality unit fix to var    
  #["""The length of the red car is 3 meters. The length of the black car equals the length of the red car. 
  #    The length of the black car is over 2 meters?""",True],    
  
  # next two require these axioms:
  #
  #{"@logic": ["or",  ["-$greater","?:X","?:Y"], ["-$greater","?:Y","?:Z"], ["$greater","?:X","?:Z"]]},
  #{"@logic": ["or",  ["-$less","?:X","?:Y"], ["-$less","?:Y","?:Z"], ["$less","?:X","?:Z"]]},  
  #
  #{"@logic": ["or",  ["-$greater","?:X","?:Y"], ["$less","?:Z","?:Y"]]},
  #{"@logic": ["or",  ["$greater","?:X","?:Y"], ["-$less","?:Z","?:Y"]]}
  #
  # ["""The length of the red car is more than 3 meters. The length of the black car is 5 meters. 
  #    The length of the red car is over 2 meters?""",True],   
  #["""The length of the red car is more than 3 meters. The length of the black car is 5 meters. 
  #    The length of the red car is less than 2 meters?""",False],       
   
  # modified babi qa15_basic-deduction_test.txt

 

   ["""Wolves are afraid of mice.
    Sheep are afraid of mice.
    Winona is a sheep.
    Mice are afraid of cats.
    Cats are afraid of wolves.
    Jessica is a mouse.
    Emily is a cat.
    Gertrude is a wolf.
    What is Emily afraid of?""","Probably a wolf"],
  ["""Wolves are afraid of mice.
    Sheep are afraid of mice.
    Winona is a sheep.
    Mice are afraid of cats.
    Cats are afraid of wolves.
    Jessica is a mouse.
    Emily is a cat.
    Gertrude is a wolf.
    Who is Emily afraid of?""","Probably Gertrude"]
 

]