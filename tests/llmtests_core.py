
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

  ["""John is a man or not a man?""",True],
  ["""John is a man and not a man?""",False],
  ["""John is tall or not tall?""",True],
  ["""John is tall and not tall?""",False],
  ["""John is a tall man and not a tall man?""",False],
  ["""John is a tall man or not a tall man?""",None],
  ["""John has a car or does not have a car?""",True],
  ["""John has a car and does not have a car?""",False],
  ["""John has a car?""",None],
  ["""John is in Estonia or is not in Estonia?""",True],
  ["""John is in Estonia and is not in Estonia?""",False],
  ["""John is in Estonia?""",None],

  # questions with basic combos of names and non-names

  ["John was yellow. John was yellow?",True],
  ["John was yellow. John was nice?",None],
  ["John was yellow. A man was nice?",None],
  ["A man was yellow. A man was yellow?",True],
  ["A man was yellow. A man was nice?",None],
  ["A man was yellow. John was nice?",None],
  
  # basic quantifiers

  ["""Elephants are animals. Elephants are animals?""",True],
  ["""Elephants are animals. Some elephant is an animal?""",True],
  ["""Elephants are animals. All elephants are animals?""",True],
  ["""Elephants are animals. John is an animal?""",None],
  ["""Elephants are animals. Elephants are not animals?""",False],
  ["""Elephants are animals. Some elephants are not animals?""",False],
  ["""Elephants are animals. All elephants are not animals?""",False],

  ["The bear who is big is strong. The bear is strong?",True],
  ["The bear who is big is strong. The big bear is strong?",True],
  ["The bear who is big is strong. The big bear is white?",None],
  ["The bear who is big is strong. Who is strong?","The big bear"],

  ["The bear who is big eats fish. The bear who is big eats fish?",True],

  ["The nice bear who was white and ate a big fish also ate blue berries. The bear ate berries? ", True],
  ["The nice bear who was white and ate a big fish also ate blue berries. The bear ate bread? ", None],

   ["John drove a red car which Eve bought. John drove a car Eve bought?",True],
  ["John drove a red car Eve bought. John drove a black car which Eve bought?",None],

  ["A blue hand of a man moved a wheel of a large wheelbarrow. A leg moved a wheel?",None],
  ["A blue hand of a man moved a wheel of a large wheelbarrow. A hand moved a wheel of a small wheelbarrow?",None],
  ["A blue hand of a man moved a wheel of a large wheelbarrow. The man had a hand?",True],
  ["A blue hand of a man moved a wheel of a large wheelbarrow. The man had a blue hand?",True],
  ["A blue hand of a man moved a wheel of a large wheelbarrow. The man had a red hand?",None],
  ["A blue hand of a man moved a wheel of a large wheelbarrow. The man had a wheel?",None],

   ["Bears ate berries in the forest which was bought by Mary. Bears ate berries in the forest which was bought by John?",None],
  ["Bears ate berries in the forest which was bought by Mary. Bears ate berries in the forest bought by Mary?",True],

   ["Clinton defeated Dole. Clinton defeated Dole?",True],
  ["Clinton defeated Dole. Clinton defeated Mike?",None],
  ["Dole was defeated by Clinton. Dole was defeated by Clinton?",True],
  ["Dole was defeated by Clinton. Dole was defeated by Mike?",None],

   ["The length of Emajogi is 80 kilometers. Emajogi is 80 kilometers long?",True],
  ["The length of Emajogi is 80 kilometers. Emajogi is 90 kilometers long?",False],

   ['Sandra travelled to the kitchen. Sandra travelled to the hallway. Mary went to the bathroom. Sandra moved to the garden. Sandra travelled to the office. Daniel journeyed to the hallway. Daniel journeyed to the office. John moved to the hallway. Where is Sandra?', 'office', ['babi', 4]],
  ['Sandra travelled to the kitchen. Sandra travelled to the hallway. Mary went to the bathroom. Sandra moved to the garden. Sandra travelled to the office. Daniel journeyed to the hallway. Daniel journeyed to the office. John moved to the hallway. John travelled to the bathroom. John journeyed to the office. Where is Daniel?', 'office', ['babi', 6]],

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
    Who is Emily afraid of?""","Probably Gertrude"],

  ["Penguins are birds who do not fly. Birds fly. John is a penguin. John flies?",False],
  ["Penguins are birds. Penguins do not fly. Birds fly. John is a penguin. John flies?",False],
  ["Penguins are birds who do not fly. Birds fly. John is a bird. John flies?",True],
  ["Penguins are birds. Penguins do not fly. Birds fly. John is a bird. John flies?",True],  

    ["""Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike and Eve are birds. 
    Who eats?""","""John, Mike and Eve."""],
  ["""Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike and Eve are birds. 
    Who flies and eats?""","""Mike and Eve."""]

]